"""Tests for the Yale Access Bluetooth Battery integration."""

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.yalexs_ble_battery.const import OWNER_DOMAIN
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant

ADDRESS = "AA:BB:CC:DD:EE:FF"
TITLE = "Back Door"


async def async_setup_owner(
    hass: HomeAssistant, address: str = ADDRESS, title: str = TITLE
) -> MockConfigEntry:
    """Add and load an entry of core's yalexs_ble for one lock."""
    owner = MockConfigEntry(
        domain=OWNER_DOMAIN,
        title=title,
        data={CONF_ADDRESS: address},
        unique_id=address,
    )
    owner.add_to_hass(hass)
    assert await hass.config_entries.async_setup(owner.entry_id)
    return owner
