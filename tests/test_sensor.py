"""Tests for the Yale Access Bluetooth Battery sensor."""

from unittest.mock import MagicMock

import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    mock_restore_cache_with_extra_data,
)
from pytest_homeassistant_custom_component.typing import WebSocketGenerator

from custom_components.yalexs_ble_battery.const import (
    CONF_READ_ACTIVITY_LOG,
    OWNER_DOMAIN,
)
from homeassistant.components.config import device_registry as config_device_registry
from homeassistant.components.sensor import SensorStateClass
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNKNOWN, EntityCategory
from homeassistant.core import HomeAssistant, State
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr, entity_registry as er

from . import ADDRESS, TITLE

ENTITY_ID = "sensor.back_door_battery_voltage_activity_log"
UNIQUE_ID = f"{ADDRESS}_battery_voltage"

# Captured GetLog replies.
INSIDE_BUTTON_LOCKED = bytes.fromhex("bb2d00d4000c0500a7eedd6a1914190f0200")
AUTO_RELOCK_LOCKED = bytes.fromhex("bb2d000e000505007baddd6a2017193f0200")
KEYPAD_LOCK_BUTTON = bytes.fromhex("bb2d0056000b0500a0a176a3df14194a0200")
END_OF_LOG = bytes.fromhex("bb2d00de800200009aa176a3a8a176a30200")
KEYPAD_UNLOCK_SLOT_205 = bytes.fromhex("bb2d0072079aa176a333004bea14cd000200")
KEYPAD_INFO = bytes.fromhex("bb2d00c404922fe06ac30000008000000200")

# The time stamp of INSIDE_BUTTON_LOCKED, bytes 8 to 11 of the frame.
INSIDE_BUTTON_LOCKED_TIME_STAMP = 0x6ADDEEA7


@pytest.fixture
def read_activity_log() -> bool:
    """Return the activity log option of the battery entry."""
    return True


async def _async_set_option(
    hass: HomeAssistant, entry: MockConfigEntry, read_activity_log: bool
) -> None:
    """Change the activity log option through the options flow."""
    result = await hass.config_entries.options.async_init(entry.entry_id)
    (field,) = result["data_schema"].schema
    assert field.default() is not read_activity_log
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_READ_ACTIVITY_LOG: read_activity_log}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()


async def _async_deliver(lock: MagicMock, raw: bytes, backlog: bool) -> None:
    """Hand a GetLog reply to the registered reader, as the library's drain does."""
    callback = lock.register_log_record_callback.call_args.args[0]
    await callback(raw, backlog)


@pytest.mark.parametrize("read_activity_log", [False])
async def test_option_on_adds_sensor_on_linked_device(
    hass: HomeAssistant,
    caplog: pytest.LogCaptureFixture,
    hass_ws_client: WebSocketGenerator,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    owner_entry: MockConfigEntry,
    config_entry: MockConfigEntry,
) -> None:
    """Turning the option on adds the sensor on a device linked to core's."""
    lock = owner_entry.runtime_data.lock
    # A lower-case lock.address fails the test if the device connection
    # takes the entry's address, which core's device connection does not use.
    lock.address = ADDRESS.lower()
    core_device = device_registry.async_get_or_create(
        config_entry_id=owner_entry.entry_id,
        connections={(dr.CONNECTION_BLUETOOTH, lock.address)},
        identifiers={(OWNER_DOMAIN, "serial")},
    )
    assert await hass.config_entries.async_setup(config_entry.entry_id)

    await _async_set_option(hass, config_entry, True)

    assert config_entry.state is ConfigEntryState.LOADED
    assert "Ignored unload request" not in caplog.text
    lock.register_log_record_callback.assert_called_once()
    entity = entity_registry.async_get(ENTITY_ID)
    assert entity is not None
    assert entity.unique_id == UNIQUE_ID
    assert entity.options["sensor"]["suggested_display_precision"] == 3
    assert entity.entity_category is EntityCategory.DIAGNOSTIC
    state = hass.states.get(ENTITY_ID)
    assert state.state == STATE_UNKNOWN
    assert state.attributes["state_class"] == SensorStateClass.MEASUREMENT
    device = device_registry.async_get(entity.device_id)
    assert device is not None
    assert device.config_entry_id == config_entry.entry_id
    assert device.connections == {(dr.CONNECTION_BLUETOOTH, lock.address)}
    assert device.name == TITLE

    config_device_registry.async_setup(hass)
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {
            "type": "config/device_registry/list_linked_devices",
            "device_id": core_device.id,
        }
    )
    msg = await client.receive_json()
    assert msg["result"]["linked_devices"] == [device.id]


@pytest.mark.parametrize(
    "records",
    [
        pytest.param([(INSIDE_BUTTON_LOCKED, False)], id="lock_operation"),
        pytest.param(
            [
                (KEYPAD_LOCK_BUTTON, True),
                (AUTO_RELOCK_LOCKED, True),
                (INSIDE_BUTTON_LOCKED, True),
            ],
            id="backlog_last_delivered_shown",
        ),
        pytest.param(
            [
                (INSIDE_BUTTON_LOCKED, True),
                (END_OF_LOG, False),
                (KEYPAD_UNLOCK_SLOT_205, False),
            ],
            id="get_log_error_and_code_operation_ignored",
        ),
        pytest.param(
            [(INSIDE_BUTTON_LOCKED, False), (KEYPAD_INFO, False)],
            id="keypad_info_ignored",
        ),
    ],
)
async def test_sensor_shows_the_last_lock_operation(
    hass: HomeAssistant,
    owner_entry: MockConfigEntry,
    config_entry: MockConfigEntry,
    records: list[tuple[bytes, bool]],
) -> None:
    """The sensor shows the voltage and time stamp of the last LockOperation."""
    assert await hass.config_entries.async_setup(config_entry.entry_id)

    for raw, backlog in records:
        await _async_deliver(owner_entry.runtime_data.lock, raw, backlog)

    state = hass.states.get(ENTITY_ID)
    assert state.state == "5.145"
    assert state.attributes["unit_of_measurement"] == "V"
    assert state.attributes["time_stamp"] == INSIDE_BUTTON_LOCKED_TIME_STAMP


async def test_sensor_restores_the_last_reading(
    hass: HomeAssistant, owner_entry: MockConfigEntry, config_entry: MockConfigEntry
) -> None:
    """After a restart, the sensor shows its last reading before any record."""
    mock_restore_cache_with_extra_data(
        hass,
        [
            (
                State(
                    ENTITY_ID,
                    "5.145",
                    {"time_stamp": INSIDE_BUTTON_LOCKED_TIME_STAMP},
                ),
                {"native_value": 5145, "native_unit_of_measurement": "mV"},
            )
        ],
    )

    assert await hass.config_entries.async_setup(config_entry.entry_id)

    state = hass.states.get(ENTITY_ID)
    assert state.state == "5.145"
    assert state.attributes["time_stamp"] == INSIDE_BUTTON_LOCKED_TIME_STAMP
    owner_entry.runtime_data.lock.register_log_record_callback.assert_called_once()


async def test_option_off_removes_reader_and_leaves_sensor_unavailable(
    hass: HomeAssistant, owner_entry: MockConfigEntry, config_entry: MockConfigEntry
) -> None:
    """Turning the option off removes the reader and leaves the sensor unavailable."""
    lock = owner_entry.runtime_data.lock
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    remove_reader = lock.register_log_record_callback.return_value

    await _async_set_option(hass, config_entry, False)

    assert config_entry.state is ConfigEntryState.LOADED
    remove_reader.assert_called_once()
    lock.register_log_record_callback.assert_called_once()
    assert hass.states.get(ENTITY_ID).state == "unavailable"


async def test_disabled_sensor_registers_no_reader(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    owner_entry: MockConfigEntry,
    config_entry: MockConfigEntry,
) -> None:
    """A sensor disabled in the entity registry registers no reader."""
    lock = owner_entry.runtime_data.lock
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    remove_reader = lock.register_log_record_callback.return_value

    entity_registry.async_update_entity(
        ENTITY_ID, disabled_by=er.RegistryEntryDisabler.USER
    )
    assert await hass.config_entries.async_reload(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED
    remove_reader.assert_called_once()
    lock.register_log_record_callback.assert_called_once()
    assert hass.states.get(ENTITY_ID) is None


async def test_entry_removal_removes_reader(
    hass: HomeAssistant, owner_entry: MockConfigEntry, config_entry: MockConfigEntry
) -> None:
    """Removing the entry removes its reader."""
    lock = owner_entry.runtime_data.lock
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    remove_reader = lock.register_log_record_callback.return_value

    await hass.config_entries.async_remove(config_entry.entry_id)

    lock.register_log_record_callback.assert_called_once()
    remove_reader.assert_called_once()
