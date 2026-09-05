"""Sensor platform for ChargeSentry."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN, STATUS_OPTIONS
from .coordinator import ChargeSentryData, ChargeSentryDataUpdateCoordinator
from .entity import ChargeSentryEntity


def _status(data: ChargeSentryData) -> str | None:
    """Return the connector status if it is one we publish as an option."""
    status = data.status
    if status is None:
        return None
    return status if status in STATUS_OPTIONS else "unknown"


def _live_power(data: ChargeSentryData) -> float | None:
    """Return live power, forced to zero when nothing is running.

    ``ha/details.php`` reports the most recent meter value within the last 30
    days, with no "is this reading current" filter — so an idle charger keeps
    echoing the last power it ever drew. ``power_is_live`` decides whether the
    reading describes now, which keeps history and the Energy dashboard honest
    without flattening a live session that is merely paused.
    """
    if not data.power_is_live:
        return 0.0
    value = data.live.get("power_w")
    return float(value) if value is not None else None


def _live_current(data: ChargeSentryData) -> float | None:
    """Return live current, zeroed when nothing is running (see :func:`_live_power`)."""
    if not data.power_is_live:
        return 0.0
    value = data.live.get("current_a")
    return float(value) if value is not None else None


def _voltage(data: ChargeSentryData) -> float | None:
    """Return the last reported supply voltage."""
    value = data.live.get("voltage_v")
    return float(value) if value is not None else None


def _energy(key: str) -> Callable[[ChargeSentryData], float | None]:
    """Build a getter for a field on the energy payload."""

    def _get(data: ChargeSentryData) -> float | None:
        if not data.energy:
            return None
        value = data.energy.get(key)
        return float(value) if value is not None else None

    return _get


def _meter_wh(data: ChargeSentryData) -> float | None:
    """Return the raw meter register in watt-hours."""
    value = data.live.get("last_meter_wh")
    return float(value) if value is not None else None


def _session_id(data: ChargeSentryData) -> int | None:
    """Return the id of the session in progress, if any."""
    return data.session_id


def _session_started(data: ChargeSentryData) -> Any:
    """Return when the running session started, as an aware datetime."""
    value = data.session_started
    return dt_util.parse_datetime(value) if value else None


def _connector(data: ChargeSentryData) -> int | None:
    """Return the connector number the live feed is reporting on."""
    return data.connector


def _delay_countdown(data: ChargeSentryData) -> int | None:
    """Return seconds until an armed delayed charge begins."""
    if not data.delay or not data.delay.get("active"):
        return None
    value = data.delay.get("seconds_until_start")
    return int(value) if value is not None else None


@dataclass(frozen=True, kw_only=True)
class ChargeSentrySensorDescription(SensorEntityDescription):
    """Describes a ChargeSentry sensor."""

    value_fn: Callable[[ChargeSentryData], Any]


SENSORS: tuple[ChargeSentrySensorDescription, ...] = (
    ChargeSentrySensorDescription(
        key="status",
        translation_key="status",
        device_class=SensorDeviceClass.ENUM,
        options=STATUS_OPTIONS,
        value_fn=_status,
    ),
    ChargeSentrySensorDescription(
        key="power",
        translation_key="power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=0,
        value_fn=_live_power,
    ),
    ChargeSentrySensorDescription(
        key="voltage",
        translation_key="voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
        value_fn=_voltage,
    ),
    ChargeSentrySensorDescription(
        key="current",
        translation_key="current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=1,
        value_fn=_live_current,
    ),
    ChargeSentrySensorDescription(
        key="energy_total",
        translation_key="energy_total",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=3,
        value_fn=_energy("lifetime_kwh"),
    ),
    ChargeSentrySensorDescription(
        key="energy_today",
        translation_key="energy_today",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=3,
        value_fn=_energy("today_kwh"),
    ),
    ChargeSentrySensorDescription(
        key="session_started",
        translation_key="session_started",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=_session_started,
    ),
    ChargeSentrySensorDescription(
        key="delay_countdown",
        translation_key="delay_countdown",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        value_fn=_delay_countdown,
    ),
    ChargeSentrySensorDescription(
        key="session_id",
        translation_key="session_id",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=_session_id,
    ),
    ChargeSentrySensorDescription(
        key="connector",
        translation_key="connector",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=_connector,
    ),
    ChargeSentrySensorDescription(
        key="meter_reading",
        translation_key="meter_reading",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=_meter_wh,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ChargeSentry sensors from a config entry."""
    coordinator: ChargeSentryDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        ChargeSentrySensor(coordinator, description) for description in SENSORS
    )


class ChargeSentrySensor(ChargeSentryEntity, SensorEntity):
    """A single value read off the live or energy feed."""

    entity_description: ChargeSentrySensorDescription

    def __init__(
        self,
        coordinator: ChargeSentryDataUpdateCoordinator,
        description: ChargeSentrySensorDescription,
    ) -> None:
        """Initialise the sensor from its description."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        """Return the current value, or None when the feed has nothing."""
        data = self.data
        if data is None:
            return None
        return self.entity_description.value_fn(data)
