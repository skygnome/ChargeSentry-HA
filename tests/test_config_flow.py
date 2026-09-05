"""Tests for the ChargeSentry config flow."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.chargesentry_rest.const import (
    CONF_BASE_URL,
    CONF_SCAN_INTERVAL,
    CONF_SERIAL,
    CONF_TOKEN,
    DOMAIN,
)

from .conftest import BASE, SERIAL, setup_integration


async def test_user_flow_creates_entry(hass: HomeAssistant, mock_api) -> None:
    """A valid token and serial create an entry titled with the charger name."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_TOKEN: "test-token", CONF_SERIAL: SERIAL, CONF_BASE_URL: BASE},
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Home Charger"
    assert result["data"][CONF_SERIAL] == SERIAL
    assert result["result"].unique_id == SERIAL.lower()


async def test_user_flow_invalid_auth(hass: HomeAssistant, aioclient_mock) -> None:
    """A rejected token is reported on the form rather than raising."""
    aioclient_mock.get(
        f"{BASE}/v1/charger/{SERIAL}/connected",
        status=401,
        json={"success": False, "message": "Invalid token"},
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_TOKEN: "bad", CONF_SERIAL: SERIAL, CONF_BASE_URL: BASE},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_user_flow_unknown_serial(hass: HomeAssistant, aioclient_mock) -> None:
    """An unknown serial is reported on the form."""
    aioclient_mock.get(
        f"{BASE}/v1/charger/NOPE/connected",
        status=404,
        json={"success": False, "message": "No charger with that serial"},
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_TOKEN: "test-token", CONF_SERIAL: "NOPE", CONF_BASE_URL: BASE},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "unknown_serial"}


async def test_user_flow_not_admin(hass: HomeAssistant, aioclient_mock) -> None:
    """A token that can see the charger but not administer it is rejected."""
    aioclient_mock.get(
        f"{BASE}/v1/charger/{SERIAL}/connected",
        json={"success": True, "charger": {"id": 14, "name": "X", "serial": SERIAL}},
    )
    aioclient_mock.get(
        f"{BASE}/v1/live/details/{SERIAL}",
        status=403,
        json={"success": False, "message": "Access denied"},
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_TOKEN: "test-token", CONF_SERIAL: SERIAL, CONF_BASE_URL: BASE},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "not_admin"}


async def test_duplicate_serial_aborts(
    hass: HomeAssistant, mock_api, config_entry
) -> None:
    """Adding the same charger twice aborts."""
    await setup_integration(hass, config_entry)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_TOKEN: "test-token", CONF_SERIAL: SERIAL, CONF_BASE_URL: BASE},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth_updates_token(
    hass: HomeAssistant, mock_api, config_entry
) -> None:
    """Reauth stores a fresh token on the existing entry."""
    await setup_integration(hass, config_entry)

    result = await config_entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_TOKEN: "new-token"}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert config_entry.data[CONF_TOKEN] == "new-token"


async def test_options_flow_sets_scan_interval(
    hass: HomeAssistant, mock_api, config_entry
) -> None:
    """The options flow stores a new polling interval."""
    await setup_integration(hass, config_entry)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_SCAN_INTERVAL: 300}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert config_entry.options[CONF_SCAN_INTERVAL] == 300
