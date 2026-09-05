"""Fixtures for the ChargeSentry tests."""

from __future__ import annotations

from typing import Any

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.chargesentry_rest.const import (
    CONF_BASE_URL,
    CONF_SERIAL,
    CONF_TOKEN,
    DEFAULT_BASE_URL,
    DOMAIN,
)

SERIAL = "CS-0001"
CHARGER_ID = 14
BASE = DEFAULT_BASE_URL

CONNECTED_PAYLOAD: dict[str, Any] = {
    "success": True,
    "charger": {
        "id": CHARGER_ID,
        "name": "Home Charger",
        "serial": SERIAL,
        "online": "1",
        "updatetime": "2026-08-06 08:00:00",
    },
}

DETAILS_PAYLOAD: dict[str, Any] = {
    "success": True,
    "charger": {
        "id": CHARGER_ID,
        "name": "Home Charger",
        "serial": SERIAL,
        "vendor": "Acme",
        "model": "EVC-2",
        "firmware": "1.2.3",
    },
}

LIVE_PAYLOAD: dict[str, Any] = {
    "success": True,
    "serial": SERIAL,
    "status": "charging",
    "connector": 1,
    "plugged_in": True,
    "power_w": 7360.0,
    "voltage_v": 230.1,
    "current_a": 32.0,
    "session_id": 512,
    "started_at": "2026-08-07T09:00:00+00:00",
    "last_meter_wh": 1234567,
}

ENERGY_PAYLOAD: dict[str, Any] = {
    "success": True,
    "serial": SERIAL,
    "lifetime_kwh": 1234.567,
    "today_kwh": 3.2,
}

DELAY_PAYLOAD: dict[str, Any] = {"success": True, "active": False}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Load custom_components/ in every test."""
    return


@pytest.fixture
def mock_api(aioclient_mock: AiohttpClientMocker) -> AiohttpClientMocker:
    """Mock a healthy ChargeSentry API."""
    aioclient_mock.get(f"{BASE}/v1/charger/{SERIAL}/connected", json=CONNECTED_PAYLOAD)
    aioclient_mock.get(f"{BASE}/v1/charger/{CHARGER_ID}/details", json=DETAILS_PAYLOAD)
    aioclient_mock.get(f"{BASE}/v1/live/details/{SERIAL}", json=LIVE_PAYLOAD)
    aioclient_mock.get(f"{BASE}/v1/live/energy/{SERIAL}", json=ENERGY_PAYLOAD)
    aioclient_mock.get(
        f"{BASE}/v1/account/delaystatus/{CHARGER_ID}/1", json=DELAY_PAYLOAD
    )
    return aioclient_mock


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """Return a config entry for one charger."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Home Charger",
        unique_id=SERIAL.lower(),
        data={
            CONF_TOKEN: "test-token",
            CONF_SERIAL: SERIAL,
            CONF_BASE_URL: BASE,
        },
    )


async def setup_integration(hass: HomeAssistant, entry: MockConfigEntry) -> ConfigEntry:
    """Add and set up a config entry."""
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry
