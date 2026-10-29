"""Tests for the Yale Access Bluetooth Battery setup and lifecycle."""

from datetime import timedelta
from unittest.mock import Mock, patch

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from . import FRONT_ADDRESS, FRONT_TITLE, async_setup_owner


@pytest.fixture
def read_activity_log() -> bool:
    """Return the activity log option of the battery entry."""
    return True


@pytest.mark.parametrize("read_activity_log", [False])
async def test_option_off_leaves_entry_idle(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    config_entry: MockConfigEntry,
) -> None:
    """With the option off, the entry loads and runs nothing for the lock."""
    assert await hass.config_entries.async_setup(config_entry.entry_id)

    # No entry of core's exists yet; with the option on, this setup would retry.
    assert config_entry.state is ConfigEntryState.LOADED
    assert config_entry.runtime_data is None

    owner_entry = await async_setup_owner(hass)
    lock = owner_entry.runtime_data.lock
    core_listener = Mock()
    owner_entry.async_on_state_change(core_listener)
    entry_listener = Mock()
    config_entry.async_on_state_change(entry_listener)
    assert await hass.config_entries.async_unload(owner_entry.entry_id)
    await hass.async_block_till_done()

    core_listener.assert_called()
    entry_listener.assert_not_called()
    assert (
        er.async_entries_for_config_entry(entity_registry, config_entry.entry_id) == []
    )
    lock.register_log_record_callback.assert_not_called()
    assert await hass.config_entries.async_unload(config_entry.entry_id)


async def test_setup_takes_the_lock_of_core_entry_for_its_address(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """Setup takes the PushLock of the loaded core entry with the entry's address."""
    await async_setup_owner(hass, FRONT_ADDRESS, FRONT_TITLE)
    owner_entry = await async_setup_owner(hass)

    assert await hass.config_entries.async_setup(config_entry.entry_id)

    assert config_entry.runtime_data.lock is owner_entry.runtime_data.lock


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
    seen: list[tuple[ConfigEntryState, ConfigEntryState]] = []
    owner_entry.async_on_state_change(
        lambda: seen.append((owner_entry.state, config_entry.state))
    )

    assert await hass.config_entries.async_unload(owner_entry.entry_id)
    await hass.async_block_till_done()

    assert seen == [
        (ConfigEntryState.UNLOAD_IN_PROGRESS, ConfigEntryState.LOADED),
        (ConfigEntryState.NOT_LOADED, ConfigEntryState.LOADED),
    ]
    assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_core_change_reloads_entry_once(
    hass: HomeAssistant, owner_entry: MockConfigEntry, config_entry: MockConfigEntry
) -> None:
    """Each reload or unload of core's entry reloads the entry once."""
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    reloads: list[str] = []
    async_reload = hass.config_entries.async_reload

    async def _async_counting_reload(entry_id: str) -> bool:
        reloads.append(entry_id)
        return await async_reload(entry_id)

    with patch.object(hass.config_entries, "async_reload", _async_counting_reload):
        assert await hass.config_entries.async_reload(owner_entry.entry_id)
        await hass.async_block_till_done()

        assert reloads.count(config_entry.entry_id) == 1
        assert config_entry.state is ConfigEntryState.LOADED
        new_lock = owner_entry.runtime_data.lock
        assert config_entry.runtime_data.lock is new_lock
        new_lock.register_log_record_callback.assert_called_once()

        assert await hass.config_entries.async_unload(owner_entry.entry_id)
        await hass.async_block_till_done()

    assert reloads.count(config_entry.entry_id) == 2
    assert config_entry.state is ConfigEntryState.SETUP_RETRY
