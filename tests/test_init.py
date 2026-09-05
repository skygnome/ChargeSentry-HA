"""Tests for setup, entities and error handling."""

from __future__ import annotations

from datetime import timedelta

from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.chargesentry_rest.const import DOMAIN

from .conftest import (
    BASE,
    CHARGER_ID,
    CONNECTED_PAYLOAD,
    DELAY_PAYLOAD,
    LIVE_PAYLOAD,
    SERIAL,
    mock_api_with_live,
    setup_integration,
)


async def test_setup_and_unload(hass: HomeAssistant, mock_api, config_entry) -> None:
    """The entry sets up and tears down cleanly."""
    await setup_integration(hass, config_entry)
    assert config_entry.state is ConfigEntryState.LOADED

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.NOT_LOADED


async def test_device_metadata(hass: HomeAssistant, mock_api, config_entry) -> None:
    """Vendor, model and firmware from charger/details land on the device."""
    await setup_integration(hass, config_entry)

    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, SERIAL)})
    assert device is not None
    assert device.name == "Home Charger"
    assert device.manufacturer == "Acme"
    assert device.model == "EVC-2"
    assert device.sw_version == "1.2.3"
    assert device.serial_number == SERIAL


async def test_sensor_states(hass: HomeAssistant, mock_api, config_entry) -> None:
    """The live and energy payloads are mapped onto sensor states."""
    await setup_integration(hass, config_entry)

    assert hass.states.get("sensor.home_charger_status").state == "charging"
    assert hass.states.get("sensor.home_charger_power").state == "7360.0"
    assert hass.states.get("sensor.home_charger_current").state == "32.0"
    assert hass.states.get("sensor.home_charger_total_energy").state == "1234.567"
    assert hass.states.get("sensor.home_charger_energy_today").state == "3.2"
    assert (
        hass.states.get("sensor.home_charger_session_started").state
        == "2026-08-07T09:00:00+00:00"
    )


async def test_binary_sensor_states(
    hass: HomeAssistant, mock_api, config_entry
) -> None:
    """Plug, charging, fault and connectivity states are derived correctly."""
    await setup_integration(hass, config_entry)

    assert hass.states.get("binary_sensor.home_charger_plugged_in").state == STATE_ON
    assert hass.states.get("binary_sensor.home_charger_charging").state == STATE_ON
    assert hass.states.get("binary_sensor.home_charger_fault").state == STATE_OFF
    assert (
        hass.states.get("binary_sensor.home_charger_charger_online").state == STATE_ON
    )
    assert (
        hass.states.get("binary_sensor.home_charger_delayed_charge_armed").state
        == STATE_OFF
    )


async def test_power_zeroed_when_idle(
    hass: HomeAssistant, aioclient_mock, config_entry
) -> None:
    """A stale meter reading on an idle charger is reported as zero, not stale.

    ha/details.php returns the newest meter value in the last 30 days with no
    freshness filter, so an idle charger keeps echoing its last power draw.
    """
    mock_api_with_live(
        aioclient_mock,
        status="available",
        plugged_in=False,
        session_id=None,
        started_at=None,
    )

    await setup_integration(hass, config_entry)

    assert hass.states.get("sensor.home_charger_power").state == "0.0"
    assert hass.states.get("sensor.home_charger_current").state == "0.0"
    assert hass.states.get("binary_sensor.home_charger_charging").state == STATE_OFF
    assert hass.states.get("switch.home_charger_charging").state == STATE_OFF


async def test_paused_session_is_still_on(
    hass: HomeAssistant, aioclient_mock, config_entry
) -> None:
    """A plugged-in car that has paused keeps its session, and so the switch.

    ha/details.php reports the connector status, which drops to suspendedev
    while the vehicle pauses even though the session is still open. Keying the
    switch on the status left it off mid-charge.
    """
    mock_api_with_live(aioclient_mock, status="suspendedev", power_w=0.0)

    await setup_integration(hass, config_entry)

    assert hass.states.get("switch.home_charger_charging").state == STATE_ON
    assert hass.states.get("binary_sensor.home_charger_charging").state == STATE_ON
    assert hass.states.get("sensor.home_charger_status").state == "suspendedev"
    # The meter reading is trusted while the session is open, not flattened.
    assert hass.states.get("sensor.home_charger_power").state == "0.0"


async def test_missing_meter_data_is_tolerated(
    hass: HomeAssistant, aioclient_mock, config_entry
) -> None:
    """A 404 from the energy endpoint leaves energy unknown but keeps the rest."""
    aioclient_mock.get(f"{BASE}/v1/charger/{SERIAL}/connected", json=CONNECTED_PAYLOAD)
    aioclient_mock.get(
        f"{BASE}/v1/charger/{CHARGER_ID}/details",
        json={"success": True, "charger": {"id": CHARGER_ID, "name": "Home Charger"}},
    )
    aioclient_mock.get(f"{BASE}/v1/live/details/{SERIAL}", json=LIVE_PAYLOAD)
    aioclient_mock.get(
        f"{BASE}/v1/live/energy/{SERIAL}",
        status=404,
        json={"success": False, "message": "Charger or meter data not found"},
    )
    aioclient_mock.get(
        f"{BASE}/v1/account/delaystatus/{CHARGER_ID}/1", json=DELAY_PAYLOAD
    )

    await setup_integration(hass, config_entry)

    assert config_entry.state is ConfigEntryState.LOADED
    assert hass.states.get("sensor.home_charger_status").state == "charging"
    assert hass.states.get("sensor.home_charger_total_energy").state == "unknown"


async def test_expired_token_triggers_reauth(
    hass: HomeAssistant, aioclient_mock, config_entry
) -> None:
    """A 401 puts the entry into the reauth flow rather than retrying forever."""
    aioclient_mock.get(
        f"{BASE}/v1/charger/{SERIAL}/connected",
        status=401,
        json={"success": False, "message": "Token invalid or expired"},
    )

    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress()
    assert any(flow["context"].get("source") == "reauth" for flow in flows)


async def test_entities_go_unavailable_on_api_failure(
    hass: HomeAssistant,
    mock_api,
    config_entry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """When a poll fails the entities report unavailable."""
    await setup_integration(hass, config_entry)
    assert hass.states.get("sensor.home_charger_status").state == "charging"

    mock_api.clear_requests()
    mock_api.get(f"{BASE}/v1/live/details/{SERIAL}", status=500)
    mock_api.get(f"{BASE}/v1/live/energy/{SERIAL}", status=500)
    mock_api.get(f"{BASE}/v1/charger/{SERIAL}/connected", status=500)

    freezer.tick(timedelta(seconds=120))
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)

    assert hass.states.get("sensor.home_charger_status").state == STATE_UNAVAILABLE


async def test_unique_ids_are_serial_scoped(
    hass: HomeAssistant, mock_api, config_entry
) -> None:
    """Unique ids include the serial so two chargers can coexist."""
    await setup_integration(hass, config_entry)

    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get("sensor.home_charger_power")
    assert entry is not None
    assert entry.unique_id == f"{DOMAIN}_{SERIAL}_power"


async def test_energy_unique_id_is_migrated(
    hass: HomeAssistant, mock_api, config_entry
) -> None:
    """An entity created by 0.1.x keeps its statistics history."""
    config_entry.add_to_hass(hass)
    entity_registry = er.async_get(hass)
    old = entity_registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"{DOMAIN}_{SERIAL}_energy",
        config_entry=config_entry,
        suggested_object_id="home_charger_energy",
    )

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    migrated = entity_registry.async_get(old.entity_id)
    assert migrated is not None
    assert migrated.unique_id == f"{DOMAIN}_{SERIAL}_energy_total"


async def test_device_link_points_at_the_site_not_the_api(
    hass: HomeAssistant, mock_api, config_entry
) -> None:
    """The device's Visit link goes to the customer site, not the JSON API."""
    await setup_integration(hass, config_entry)

    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, SERIAL)})
    assert device is not None
    assert device.configuration_url == "https://chargesentry.uk"
