"""Binary sensor platform for ChargeSentry."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ACTIVE_CHARGING_STATUSES,
    DELAY_ACTIVE_STATES,
    DOMAIN,
    STATUS_FAULTED,
)
from .coordinator import ChargeSentryData, ChargeSentryDataUpdateCoordinator
from .entity import ChargeSentryEntity


def _plugged_in(data: ChargeSentryData) -> bool | None:
    """Return whether a vehicle is plugged into the connector."""
    value = data.live.get("plugged_in")
    return bool(value) if value is not None else None


def _charging(data: ChargeSentryData) -> bool | None:
    """Return whether the connector is actively delivering energy."""
    status = data.status
    return status in ACTIVE_CHARGING_STATUSES if status else None


def _faulted(data: ChargeSentryData) -> bool | None:
    """Return whether the connector is reporting a fault."""
    status = data.status
    return status == STATUS_FAULTED if status else None


def _online(data: ChargeSentryData) -> bool | None:
    """Return whether the charge point is connected to the OCPP server."""
    return data.online


def _delay_armed(data: ChargeSentryData) -> bool | None:
    """Return whether a delayed charge is armed or running on the connector."""
    if data.delay is None:
        return None
    if not data.delay.get("active"):
        return False
    state = data.delay.get("state")
    return state in DELAY_ACTIVE_STATES if state else True


@dataclass(frozen=True, kw_only=True)
class ChargeSentryBinarySensorDescription(BinarySensorEntityDescription):
    """Describes a ChargeSentry binary sensor."""

    value_fn: Callable[[ChargeSentryData], bool | None]


BINARY_SENSORS: tuple[ChargeSentryBinarySensorDescription, ...] = (
    ChargeSentryBinarySensorDescription(
        key="plugged_in",
        translation_key="plugged_in",
        device_class=BinarySensorDeviceClass.PLUG,
        value_fn=_plugged_in,
    ),
    ChargeSentryBinarySensorDescription(
        key="charging",
        translation_key="charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        value_fn=_charging,
    ),
    ChargeSentryBinarySensorDescription(
        key="delay_armed",
        translation_key="delay_armed",
        value_fn=_delay_armed,
    ),
    ChargeSentryBinarySensorDescription(
        key="fault",
        translation_key="fault",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_faulted,
    ),
    ChargeSentryBinarySensorDescription(
        key="online",
        translation_key="online",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_online,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ChargeSentry binary sensors from a config entry."""
    coordinator: ChargeSentryDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        ChargeSentryBinarySensor(coordinator, description)
        for description in BINARY_SENSORS
    )


class ChargeSentryBinarySensor(ChargeSentryEntity, BinarySensorEntity):
    """A boolean derived from the live feed."""

    entity_description: ChargeSentryBinarySensorDescription

    def __init__(
        self,
        coordinator: ChargeSentryDataUpdateCoordinator,
        description: ChargeSentryBinarySensorDescription,
    ) -> None:
        """Initialise the binary sensor from its description."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return the current boolean state."""
        data = self.data
        if data is None:
            return None
        return self.entity_description.value_fn(data)
