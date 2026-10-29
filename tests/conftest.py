"""Fixtures for the Yale Access Bluetooth Battery tests."""

from collections.abc import Iterator
from unittest.mock import Mock

import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    MockModule,
    mock_config_flow,
    mock_integration,
    mock_platform,
)

from custom_components.yalexs_ble_battery.const import (
    CONF_READ_ACTIVITY_LOG,
    DOMAIN,
    OWNER_DOMAIN,
)
from homeassistant.config_entries import ConfigEntry, ConfigFlow
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant

from . import ADDRESS, TITLE, async_setup_owner, mock_push_lock


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable custom integrations in every test."""


async def _async_setup_owner_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Load core's entry with a new PushLock, as core does on every load."""
    entry.runtime_data = Mock(lock=mock_push_lock(entry.data[CONF_ADDRESS]))
    return True


async def _async_unload_owner_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload core's entry."""
    return True


class _OwnerConfigFlow(ConfigFlow):
    """Stand in for the config flow of core's yalexs_ble."""


@pytest.fixture(autouse=True)
def mock_owner_integration(hass: HomeAssistant) -> Iterator[None]:
    """Stand in for core's yalexs_ble, which needs Bluetooth."""
    mock_integration(
        hass,
        MockModule(
            OWNER_DOMAIN,
            async_setup_entry=_async_setup_owner_entry,
            async_unload_entry=_async_unload_owner_entry,
        ),
    )
    mock_platform(hass, f"{OWNER_DOMAIN}.config_flow")
    with mock_config_flow(OWNER_DOMAIN, _OwnerConfigFlow):
        yield


@pytest.fixture
async def owner_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Return a loaded entry of core's yalexs_ble."""
    return await async_setup_owner(hass)


@pytest.fixture
def read_activity_log() -> bool:
    """Return the activity log option of the battery entry."""
    return False


@pytest.fixture
def config_entry(hass: HomeAssistant, read_activity_log: bool) -> MockConfigEntry:
    """Return the battery entry for the lock, not yet set up."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=TITLE,
        data={CONF_ADDRESS: ADDRESS},
        options={CONF_READ_ACTIVITY_LOG: read_activity_log},
        unique_id=ADDRESS,
    )
    entry.add_to_hass(hass)
    return entry
