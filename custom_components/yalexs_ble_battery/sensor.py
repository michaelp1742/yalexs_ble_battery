"""Battery voltage sensor for the Yale Access Bluetooth Battery integration."""

from typing import override

from yalexs_ble import LockOperation, parse_log_event_packet

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfElectricPotential
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import YaleXSBLEBatteryConfigEntry
from .models import YaleXSBLEBatteryData

ATTR_TIME_STAMP = "time_stamp"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: YaleXSBLEBatteryConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the battery voltage sensor."""
    async_add_entities([YaleXSBLEBatteryVoltageSensor(entry.runtime_data)])


class YaleXSBLEBatteryVoltageSensor(RestoreSensor):
    """The battery voltage from the lock's activity log records."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_translation_key = "battery_voltage_activity_log"
    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfElectricPotential.MILLIVOLT
    _attr_suggested_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_suggested_display_precision = 3
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, data: YaleXSBLEBatteryData) -> None:
        """Initialize the sensor."""
        self._lock = data.lock
        self._attr_unique_id = f"{data.address}_battery_voltage"
        self._attr_device_info = DeviceInfo(
            connections={(CONNECTION_BLUETOOTH, data.lock.address)}
        )

    @override
    async def async_added_to_hass(self) -> None:
        """Restore the last reading, then register the activity log reader."""
        await super().async_added_to_hass()
        if (last_data := await self.async_get_last_sensor_data()) is not None:
            self._attr_native_value = last_data.native_value
        if (last_state := await self.async_get_last_state()) is not None and (
            time_stamp := last_state.attributes.get(ATTR_TIME_STAMP)
        ) is not None:
            self._attr_extra_state_attributes = {ATTR_TIME_STAMP: time_stamp}
        self.async_on_remove(
            self._lock.register_log_record_callback(self._async_log_record)
        )

    async def _async_log_record(self, raw: bytes, backlog: bool) -> None:
        """Publish the battery voltage of each LockOperation record."""
        record = parse_log_event_packet(raw)
        if isinstance(record, LockOperation):
            self._attr_native_value = record.battery_level
            self._attr_extra_state_attributes = {ATTR_TIME_STAMP: record.time_stamp}
            self.async_write_ha_state()
