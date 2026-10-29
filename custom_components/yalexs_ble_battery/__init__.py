"""The Yale Access Bluetooth Battery integration."""

from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN, OWNER_DOMAIN
from .models import YaleXSBLEBatteryData

if TYPE_CHECKING:
    from homeassistant.components.yalexs_ble import YALEXSBLEConfigEntry

type YaleXSBLEBatteryConfigEntry = ConfigEntry[YaleXSBLEBatteryData]


async def async_setup_entry(
    hass: HomeAssistant, entry: YaleXSBLEBatteryConfigEntry
) -> bool:
    """Set up the battery entry for a lock that core's yalexs_ble has loaded."""
    address = entry.data[CONF_ADDRESS]
    owner: YALEXSBLEConfigEntry | None = next(
        (
            owner
            for owner in hass.config_entries.async_loaded_entries(OWNER_DOMAIN)
            if owner.data[CONF_ADDRESS] == address
        ),
        None,
    )
    if owner is None:
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN, translation_key="owner_not_loaded"
        )
    entry.runtime_data = YaleXSBLEBatteryData(address, owner.runtime_data.lock)

    @callback
    def _async_owner_changed() -> None:
        """Schedule this entry's reload when core's entry changes state."""
        # A reload started inside the listener loop of core's entry can remove this
        # listener while the loop runs, and the loop then skips the listener after it.
        hass.loop.call_soon(hass.config_entries.async_schedule_reload, entry.entry_id)

    entry.async_on_unload(owner.async_on_state_change(_async_owner_changed))
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: YaleXSBLEBatteryConfigEntry
) -> bool:
    """Unload a config entry."""
    return True
