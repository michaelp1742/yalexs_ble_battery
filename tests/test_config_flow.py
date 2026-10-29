"""Tests for the Yale Access Bluetooth Battery config flow."""

from typing import Any

from custom_components.yalexs_ble_battery.const import CONF_READ_ACTIVITY_LOG, DOMAIN
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from . import ADDRESS, FRONT_ADDRESS, FRONT_TITLE, TITLE, async_setup_owner


def _listed_locks(result: dict[str, Any]) -> list[dict[str, str]]:
    """Return the locks the form offers."""
    return result["data_schema"].schema[CONF_ADDRESS].config["options"]


async def test_user_flow_lists_each_loaded_lock_once(hass: HomeAssistant) -> None:
    """Each loaded lock gets one entry, and none left aborts the flow."""
    await async_setup_owner(hass)
    await async_setup_owner(hass, FRONT_ADDRESS, FRONT_TITLE)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert _listed_locks(result) == [
        {"value": ADDRESS, "label": TITLE},
        {"value": FRONT_ADDRESS, "label": FRONT_TITLE},
    ]

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_ADDRESS: ADDRESS}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == TITLE
    assert result["data"] == {CONF_ADDRESS: ADDRESS}
    assert result["options"] == {CONF_READ_ACTIVITY_LOG: False}
    assert result["result"].unique_id == ADDRESS

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert _listed_locks(result) == [{"value": FRONT_ADDRESS, "label": FRONT_TITLE}]
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_ADDRESS: FRONT_ADDRESS}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_locks"


async def test_user_flow_aborts_for_a_lock_whose_entry_another_flow_added(
    hass: HomeAssistant,
) -> None:
    """A flow submitted after another flow added the lock's entry aborts."""
    await async_setup_owner(hass)
    first = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    second = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        first["flow_id"], {CONF_ADDRESS: ADDRESS}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    result = await hass.config_entries.flow.async_configure(
        second["flow_id"], {CONF_ADDRESS: ADDRESS}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
