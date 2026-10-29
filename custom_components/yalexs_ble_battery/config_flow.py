"""Config flow for the Yale Access Bluetooth Battery integration."""

from typing import Any, override

import probatio

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ADDRESS
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
)

from .const import CONF_READ_ACTIVITY_LOG, DOMAIN, OWNER_DOMAIN


class YaleXSBLEBatteryConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Yale Access Bluetooth Battery."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._titles: dict[str, str] = {}

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the user step to pick a lock that core's yalexs_ble has loaded."""
        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(address)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=self._titles[address],
                data={CONF_ADDRESS: address},
                options={CONF_READ_ACTIVITY_LOG: False},
            )

        current_addresses = self._async_current_ids()
        self._titles = {
            owner.data[CONF_ADDRESS]: owner.title
            for owner in self.hass.config_entries.async_loaded_entries(OWNER_DOMAIN)
            if owner.data[CONF_ADDRESS] not in current_addresses
        }
        if not self._titles:
            return self.async_abort(reason="no_locks")

        return self.async_show_form(
            step_id="user",
            data_schema=probatio.Schema(
                {
                    probatio.Required(CONF_ADDRESS): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                SelectOptionDict(value=address, label=title)
                                for address, title in self._titles.items()
                            ]
                        )
                    )
                }
            ),
        )
