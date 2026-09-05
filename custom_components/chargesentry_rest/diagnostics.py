"""Diagnostics support for ChargeSentry."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_SERIAL, CONF_TOKEN, DOMAIN
from .coordinator import ChargeSentryDataUpdateCoordinator

TO_REDACT = {CONF_TOKEN, CONF_SERIAL, "serial"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: ChargeSentryDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    return {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": dict(entry.options),
        },
        "charger": {
            "id": coordinator.charger_id,
            "name": coordinator.charger_name,
            "vendor": coordinator.vendor,
            "model": coordinator.model,
            "firmware": coordinator.firmware,
        },
        "last_update_success": coordinator.last_update_success,
        "data": async_redact_data(
            asdict(coordinator.data) if coordinator.data else {}, TO_REDACT
        ),
    }
