"""The ChargeSentry integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er

from .const import CONF_SERIAL, DOMAIN, PLATFORMS
from .coordinator import ChargeSentryDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Entity keys renamed since 0.1.x, old suffix -> new suffix. Migrating the
# unique id keeps the entity id and, more importantly, the long-term
# statistics already recorded against it.
_RENAMED_KEYS = {"energy": "energy_total"}


async def _async_migrate_unique_ids(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Carry entities created by 0.1.x over to their new unique ids."""
    serial = str(entry.data.get(CONF_SERIAL, "")).strip()
    if not serial:
        return

    prefix = f"{DOMAIN}_{serial}_"
    renames = {f"{prefix}{old}": f"{prefix}{new}" for old, new in _RENAMED_KEYS.items()}

    @callback
    def _migrate(entity: er.RegistryEntry) -> dict[str, str] | None:
        new_unique_id = renames.get(entity.unique_id)
        if new_unique_id is None:
            return None
        _LOGGER.debug(
            "Migrating %s from unique id %s to %s",
            entity.entity_id,
            entity.unique_id,
            new_unique_id,
        )
        return {"new_unique_id": new_unique_id}

    await er.async_migrate_entries(hass, entry.entry_id, _migrate)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ChargeSentry from a config entry."""
    await _async_migrate_unique_ids(hass, entry)

    coordinator = ChargeSentryDataUpdateCoordinator(hass, entry)

    # Raises ConfigEntryAuthFailed (bad token, triggers reauth) or
    # ConfigEntryNotReady (anything transient) on its own.
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)
