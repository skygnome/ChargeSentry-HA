"""Shared entity base for ChargeSentry."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ChargeSentryData, ChargeSentryDataUpdateCoordinator


class ChargeSentryEntity(CoordinatorEntity[ChargeSentryDataUpdateCoordinator]):
    """Base entity: one device per charger, keyed on its serial."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: ChargeSentryDataUpdateCoordinator, key: str
    ) -> None:
        """Bind the entity to its coordinator and give it a stable unique id."""
        super().__init__(coordinator)
        self._key = key
        self._attr_unique_id = f"{DOMAIN}_{coordinator.serial}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.serial)},
            name=coordinator.charger_name or coordinator.serial,
            manufacturer=coordinator.vendor or "ChargeSentry",
            model=coordinator.model or "OCPP charge point",
            sw_version=coordinator.firmware,
            serial_number=coordinator.serial,
            configuration_url=coordinator.web_url,
        )

    @property
    def available(self) -> bool:
        """Return True while the last poll succeeded and returned data."""
        return bool(self.coordinator.last_update_success and self.coordinator.data)

    @property
    def data(self) -> ChargeSentryData | None:
        """Return the latest poll result."""
        return self.coordinator.data
