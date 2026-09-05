"""Tests for the charging switch and control services."""

from __future__ import annotations

import pytest
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TURN_OFF, SERVICE_TURN_ON
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from custom_components.chargesentry_rest.const import (
    DOMAIN,
    SERVICE_CANCEL_DELAY,
    SERVICE_DELAY_START,
    SERVICE_START_CHARGE,
)

from .conftest import BASE, CHARGER_ID, setup_integration

SWITCH = "switch.home_charger_charging"


def _call_to(mock_api, path: str):
    """Return the URL of the last request made to ``path``.

    Every command triggers a refresh once it returns, so the command itself is
    not the last call recorded.
    """
    matches = [
        url for _method, url, _data, _headers in mock_api.mock_calls if url.path == path
    ]
    assert matches, f"no request was made to {path}"
    return matches[-1]


async def test_switch_reflects_status(
    hass: HomeAssistant, mock_api, config_entry
) -> None:
    """The switch is on while the connector is charging."""
    await setup_integration(hass, config_entry)
    assert hass.states.get(SWITCH).state == "on"


async def test_turn_on_calls_startcharge(
    hass: HomeAssistant, mock_api, config_entry
) -> None:
    """Turning the switch on hits startcharge for the live connector."""
    await setup_integration(hass, config_entry)
    mock_api.get(
        f"{BASE}/v1/account/startcharge/{CHARGER_ID}/1",
        json={"success": True, "message": "Command accepted by charger"},
    )

    await hass.services.async_call(
        "switch", SERVICE_TURN_ON, {ATTR_ENTITY_ID: SWITCH}, blocking=True
    )

    url = _call_to(mock_api, f"/v1/account/startcharge/{CHARGER_ID}/1")
    assert url.query["type"] == "0"


async def test_turn_off_calls_stopcharge(
    hass: HomeAssistant, mock_api, config_entry
) -> None:
    """Turning the switch off hits stopcharge for the live connector."""
    await setup_integration(hass, config_entry)
    mock_api.get(
        f"{BASE}/v1/account/stopcharge/{CHARGER_ID}/1",
        json={"success": True, "message": "Command accepted by charger"},
    )

    await hass.services.async_call(
        "switch", SERVICE_TURN_OFF, {ATTR_ENTITY_ID: SWITCH}, blocking=True
    )

    _call_to(mock_api, f"/v1/account/stopcharge/{CHARGER_ID}/1")


async def test_start_charge_service_with_limit(
    hass: HomeAssistant, mock_api, config_entry
) -> None:
    """An energy limit is sent as type=1 plus limit."""
    await setup_integration(hass, config_entry)
    mock_api.get(
        f"{BASE}/v1/account/startcharge/{CHARGER_ID}/2", json={"success": True}
    )

    await hass.services.async_call(
        DOMAIN,
        SERVICE_START_CHARGE,
        {ATTR_ENTITY_ID: SWITCH, "connector": 2, "limit_kwh": 20},
        blocking=True,
    )

    url = _call_to(mock_api, f"/v1/account/startcharge/{CHARGER_ID}/2")
    assert url.query["type"] == "1"
    assert url.query["limit"] == "20.0"


async def test_delay_start_service(hass: HomeAssistant, mock_api, config_entry) -> None:
    """delay_start passes the delay and run-for windows through."""
    await setup_integration(hass, config_entry)
    mock_api.get(
        f"{BASE}/v1/account/delaystart/{CHARGER_ID}/1",
        json={"success": True, "delayed_charge_id": 12},
    )

    await hass.services.async_call(
        DOMAIN,
        SERVICE_DELAY_START,
        {
            ATTR_ENTITY_ID: SWITCH,
            "delay_seconds": 3600,
            "run_for_seconds": 25200,
        },
        blocking=True,
    )

    url = _call_to(mock_api, f"/v1/account/delaystart/{CHARGER_ID}/1")
    assert url.query["delay_seconds"] == "3600"
    assert url.query["run_for_seconds"] == "25200"


async def test_delay_seconds_is_range_checked(
    hass: HomeAssistant, mock_api, config_entry
) -> None:
    """A delay outside the API's 1-86400 window is rejected before the call."""
    await setup_integration(hass, config_entry)

    with pytest.raises(Exception):  # noqa: B017 - vol.Invalid wrapped by HA
        await hass.services.async_call(
            DOMAIN,
            SERVICE_DELAY_START,
            {ATTR_ENTITY_ID: SWITCH, "delay_seconds": 999999},
            blocking=True,
        )


async def test_cancel_delay_service(
    hass: HomeAssistant, mock_api, config_entry
) -> None:
    """cancel_delay hits delaycancel for the live connector."""
    await setup_integration(hass, config_entry)
    mock_api.get(
        f"{BASE}/v1/account/delaycancel/{CHARGER_ID}/1",
        json={"success": True, "delayed_charge_id": 12},
    )

    await hass.services.async_call(
        DOMAIN, SERVICE_CANCEL_DELAY, {ATTR_ENTITY_ID: SWITCH}, blocking=True
    )

    _call_to(mock_api, f"/v1/account/delaycancel/{CHARGER_ID}/1")


async def test_rejected_command_raises(
    hass: HomeAssistant, mock_api, config_entry
) -> None:
    """A 402/409/502 from the API surfaces as a HomeAssistantError."""
    await setup_integration(hass, config_entry)
    mock_api.get(
        f"{BASE}/v1/account/startcharge/{CHARGER_ID}/1",
        status=402,
        json={"success": False, "message": "Insufficient credit"},
    )

    with pytest.raises(HomeAssistantError, match="Insufficient credit"):
        await hass.services.async_call(
            "switch", SERVICE_TURN_ON, {ATTR_ENTITY_ID: SWITCH}, blocking=True
        )
