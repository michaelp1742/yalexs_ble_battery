"""Tests for the Yale Access Bluetooth Battery setup and lifecycle."""

from datetime import timedelta
from unittest.mock import Mock

from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er


async def test_option_off_registers_no_reader(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    owner_entry: MockConfigEntry,
    config_entry: MockConfigEntry,
) -> None:
    """With the option off, the entry loads with no entity and no reader."""
    lock = owner_entry.runtime_data.lock
    assert await hass.config_entries.async_setup(config_entry.entry_id)

    assert config_entry.state is ConfigEntryState.LOADED
    assert config_entry.runtime_data.lock is lock
    assert (
        er.async_entries_for_config_entry(entity_registry, config_entry.entry_id) == []
    )
    lock.register_log_record_callback.assert_not_called()

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    core_listener = Mock()
    owner_entry.async_on_state_change(core_listener)
    assert await hass.config_entries.async_unload(owner_entry.entry_id)
    await hass.async_block_till_done()

    core_listener.assert_called()
    assert config_entry.state is ConfigEntryState.NOT_LOADED


async def test_core_unload_reloads_entry_until_core_loads(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    owner_entry: MockConfigEntry,
    config_entry: MockConfigEntry,
) -> None:
    """Core's unload reloads the entry, which waits for core's next load."""
    old_lock = owner_entry.runtime_data.lock
    assert await hass.config_entries.async_setup(config_entry.entry_id)

    assert await hass.config_entries.async_unload(owner_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_RETRY
    assert config_entry.reason == "Yale Access Bluetooth has not loaded this lock"

    assert await hass.config_entries.async_setup(owner_entry.entry_id)
    freezer.tick(timedelta(seconds=6))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED
    assert config_entry.runtime_data.lock is owner_entry.runtime_data.lock
    assert config_entry.runtime_data.lock is not old_lock


async def test_core_change_reaches_the_next_listener(
    hass: HomeAssistant, owner_entry: MockConfigEntry, config_entry: MockConfigEntry
) -> None:
    """The entry's reload waits until core's entry has called every listener."""
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    seen: list[ConfigEntryState] = []
    owner_entry.async_on_state_change(lambda: seen.append(owner_entry.state))

    assert await hass.config_entries.async_unload(owner_entry.entry_id)
    await hass.async_block_till_done()

    assert seen == [ConfigEntryState.UNLOAD_IN_PROGRESS, ConfigEntryState.NOT_LOADED]
    assert config_entry.state is ConfigEntryState.SETUP_RETRY
