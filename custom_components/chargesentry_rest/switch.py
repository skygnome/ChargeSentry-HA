"""Switch platform for ChargeSentry, plus the charger control services."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import (
    AddEntitiesCallback,
    async_get_current_platform,
)

from .api import ChargeSentryError
from .const import (
    ATTR_CONNECTOR,
    ATTR_DELAY_SECONDS,
    ATTR_LIMIT_KWH,
    ATTR_RUN_FOR_SECONDS,
    DOMAIN,
    SERVICE_CANCEL_DELAY,
    SERVICE_DELAY_START,
    SERVICE_START_CHARGE,
    SERVICE_STOP_CHARGE,
)
from .coordinator import ChargeSentryDataUpdateCoordinator
from .entity import ChargeSentryEntity

_CONNECTOR_SCHEMA = {
    vol.Optional(ATTR_CONNECTOR): vol.All(vol.Coerce(int), vol.Range(min=1)),
}
_LIMIT_SCHEMA = {
    vol.Optional(ATTR_LIMIT_KWH): vol.All(vol.Coerce(float), vol.Range(min=0.1)),
}
_SECONDS = vol.All(vol.Coerce(int), vol.Range(min=1, max=86400))


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the charging switch and register the control services."""
    coordinator: ChargeSentryDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ChargeSentryChargingSwitch(coordinator)])

    platform = async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_START_CHARGE,
        {**_CONNECTOR_SCHEMA, **_LIMIT_SCHEMA},
        "async_start_charge",
    )
    platform.async_register_entity_service(
        SERVICE_STOP_CHARGE,
        {**_CONNECTOR_SCHEMA},
        "async_stop_charge",
    )
    platform.async_register_entity_service(
        SERVICE_DELAY_START,
        {
            vol.Required(ATTR_DELAY_SECONDS): _SECONDS,
            vol.Optional(ATTR_RUN_FOR_SECONDS): _SECONDS,
            **_CONNECTOR_SCHEMA,
            **_LIMIT_SCHEMA,
        },
        "async_delay_start",
    )
    platform.async_register_entity_service(
        SERVICE_CANCEL_DELAY,
        {**_CONNECTOR_SCHEMA},
        "async_cancel_delay",
    )


class ChargeSentryChargingSwitch(ChargeSentryEntity, SwitchEntity):
    """Start and stop a charge session on the charger's active connector.

    On means a session is open — the charger reports a ``session_id`` with no
    finish time. That is deliberately not the same as "current is flowing":
    a plugged-in car that has paused (``suspendedev``) or a charge waiting on
    a schedule still has its session open, and turning the switch off is still
    what ends it. Look at the Status sensor for the connector's OCPP state.

    The state can lag a command by up to one poll while the charge point
    acknowledges it.
    """

    _attr_translation_key = "charging"

    def __init__(self, coordinator: ChargeSentryDataUpdateCoordinator) -> None:
        """Initialise the charging switch."""
        super().__init__(coordinator, "charging")

    @property
    def is_on(self) -> bool | None:
        """Return whether a charge session is currently open."""
        data = self.data
        if data is None:
            return None
        return data.session_active

    def _resolve_connector(self, connector: int | None) -> int:
        """Return the connector to act on, defaulting to the live one."""
        if connector is not None:
            return connector
        data = self.data
        if data is not None and data.connector is not None:
            return data.connector
        return 1

    def _charger_id(self) -> int:
        """Return the numeric charger id, or raise if it never resolved."""
        if self.coordinator.charger_id is None:
            raise HomeAssistantError(
                f"Charger id for {self.coordinator.serial} is not known yet; "
                "the integration could not resolve the serial."
            )
        return self.coordinator.charger_id

    async def _async_command(self, description: str, coro: Any) -> None:
        """Await a control call, surfacing API errors to the user."""
        try:
            await coro
        except ChargeSentryError as err:
            raise HomeAssistantError(
                f"{description} failed for {self.coordinator.serial}: {err}"
            ) from err
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Start a charge on the active connector."""
        await self.async_start_charge()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Stop the charge in progress on the active connector."""
        await self.async_stop_charge()

    async def async_start_charge(
        self, connector: int | None = None, limit_kwh: float | None = None
    ) -> None:
        """Remote-start a charge, optionally capped at a kWh limit."""
        await self._async_command(
            "Start charge",
            self.coordinator.client.async_start_charge(
                self._charger_id(), self._resolve_connector(connector), limit_kwh
            ),
        )

    async def async_stop_charge(self, connector: int | None = None) -> None:
        """Remote-stop the account's own charge on a connector."""
        await self._async_command(
            "Stop charge",
            self.coordinator.client.async_stop_charge(
                self._charger_id(), self._resolve_connector(connector)
            ),
        )

    async def async_delay_start(
        self,
        delay_seconds: int,
        run_for_seconds: int | None = None,
        connector: int | None = None,
        limit_kwh: float | None = None,
    ) -> None:
        """Arm a delayed charge on a connector the vehicle is plugged into."""
        await self._async_command(
            "Delay start",
            self.coordinator.client.async_delay_start(
                self._charger_id(),
                self._resolve_connector(connector),
                delay_seconds,
                run_for_seconds,
                limit_kwh,
            ),
        )

    async def async_cancel_delay(self, connector: int | None = None) -> None:
        """Cancel a delayed charge that has not started yet."""
        await self._async_command(
            "Cancel delayed charge",
            self.coordinator.client.async_cancel_delay(
                self._charger_id(), self._resolve_connector(connector)
            ),
        )
