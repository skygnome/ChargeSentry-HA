from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed

from .const import DOMAIN, CONF_TOKEN
from .coordinator import ChargeSentryDataUpdateCoordinator

PLATFORMS: list[str] = ["sensor"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Prefer options (mutable), fallback to data (initial setup)
    token = entry.options.get(CONF_TOKEN, entry.data.get(CONF_TOKEN, "")).strip()

    coordinator = ChargeSentryDataUpdateCoordinator(hass, token=token)
    await coordinator.async_config_entry_first_refresh()

    if coordinator.last_status_code == 401:
        raise ConfigEntryAuthFailed("Token rejected, reauth required")

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok
