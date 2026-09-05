"""Data update coordinator for ChargeSentry."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any
from urllib.parse import urlparse

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    ChargeSentryApiClient,
    ChargeSentryAuthError,
    ChargeSentryConnectionError,
    ChargeSentryError,
    ChargeSentryForbiddenError,
    ChargeSentryNotFoundError,
)
from .const import (
    CONF_BASE_URL,
    CONF_SCAN_INTERVAL,
    CONF_SERIAL,
    CONF_TOKEN,
    DEFAULT_BASE_URL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_WEB_URL,
    DOMAIN,
    TRANSACTION_STATUSES,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class ChargeSentryData:
    """One poll's worth of state for a single charger."""

    live: dict[str, Any] = field(default_factory=dict)
    energy: dict[str, Any] | None = None
    delay: dict[str, Any] | None = None
    online: bool | None = None

    @property
    def status(self) -> str | None:
        """Return the connector status, lower-cased."""
        status = self.live.get("status")
        return str(status).lower() if status else None

    @property
    def connector(self) -> int | None:
        """Return the connector the live feed is reporting on."""
        connector = self.live.get("connector")
        return int(connector) if connector is not None else None

    @property
    def transaction_active(self) -> bool:
        """Return whether a charge is actually running on the connector.

        The connector status decides this, not ``session_id``. Two API quirks
        rule the session id out as the signal:

        ``ha/details.php`` selects the newest session with ``finishtime IS
        NULL``, where every other endpoint in the API uses ``status = '0'``. A
        session that ended without its finish time being written therefore
        stays "open" forever, and the charger reports a months-old session id
        while sitting idle.

        And there is no upper bound on that lookup, so the stale row is
        returned even when the connector is plainly ``available`` or
        ``preparing``.

        The status is unambiguous by comparison: an OCPP transaction is open in
        ``charging`` and in both suspended states, and in nothing else.
        ``preparing`` means plugged in and waiting to be started — which is
        exactly when a charge needs starting, not when one is running.
        """
        return self.status in TRANSACTION_STATUSES

    @property
    def session_id(self) -> int | None:
        """Return the id of the session in progress, or None if none is.

        Suppressed unless a transaction is actually running, so a stale row
        left behind by the ``finishtime`` quirk above is not reported as a live
        session.
        """
        if not self.transaction_active:
            return None
        value = self.live.get("session_id")
        return int(value) if value is not None else None

    @property
    def session_started(self) -> str | None:
        """Return when the running session started, if one is running."""
        if not self.transaction_active:
            return None
        value = self.live.get("started_at")
        return str(value) if value else None

    @property
    def power_is_live(self) -> bool:
        """Return whether the reported meter values describe right now.

        ``ha/details.php`` returns the newest meter value within the last 30
        days with no freshness check, so an idle charger keeps echoing the last
        power it ever drew. Only a running transaction makes that reading
        trustworthy.
        """
        return self.transaction_active


def _option(entry: ConfigEntry, key: str, default: Any = None) -> Any:
    """Read a value from entry options, falling back to entry data."""
    if key in entry.options:
        return entry.options[key]
    return entry.data.get(key, default)


class ChargeSentryDataUpdateCoordinator(DataUpdateCoordinator[ChargeSentryData]):
    """Poll the live endpoints for one charger."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Set up the coordinator from a config entry."""
        self.serial: str = str(_option(entry, CONF_SERIAL, "")).strip()
        self._base_url: str = str(_option(entry, CONF_BASE_URL, DEFAULT_BASE_URL))
        scan_interval = int(_option(entry, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))

        self.client = ChargeSentryApiClient(
            async_get_clientsession(hass),
            str(_option(entry, CONF_TOKEN, "")).strip(),
            self._base_url,
        )

        # Slow-moving charger metadata, resolved once and reused for DeviceInfo.
        self.charger_id: int | None = None
        self.charger_name: str | None = None
        self.vendor: str | None = None
        self.model: str | None = None
        self.firmware: str | None = None

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {self.serial}",
            update_interval=timedelta(seconds=scan_interval),
            config_entry=entry,
        )

    @property
    def base_url(self) -> str:
        """Return the API base URL in use."""
        return self._base_url

    @property
    def web_url(self) -> str:
        """Return the customer-facing site, for the device's "Visit" link.

        The API lives on an ``api.`` subdomain that serves JSON and nothing a
        person can use, so the device link drops that label: api.example.com
        becomes example.com. A base URL that is not an ``api.`` host is left
        alone, since there is nothing to infer from it.
        """
        parsed = urlparse(self._base_url)
        if not parsed.hostname:
            return DEFAULT_WEB_URL
        if not parsed.hostname.startswith("api."):
            return self._base_url
        port = f":{parsed.port}" if parsed.port else ""
        return f"{parsed.scheme}://{parsed.hostname.removeprefix('api.')}{port}"

    async def _async_resolve_charger(self) -> None:
        """Resolve the serial to a charger id and pull its metadata.

        The live endpoints are keyed by serial, but every control endpoint
        (start/stop/delay) is keyed by the numeric charger id, so this has to
        happen before the switch and services can do anything.
        """
        charger = await self.client.async_get_charger_by_serial(self.serial)
        self.charger_id = int(charger["id"])
        self.charger_name = charger.get("name") or self.serial

        try:
            details = await self.client.async_get_charger_details(self.charger_id)
        except ChargeSentryError as err:
            # details.php is gated on requireAccessOrPublic(); losing it only
            # costs us the vendor/model/firmware labels, so carry on without.
            _LOGGER.debug("Could not read charger details for %s: %s", self.serial, err)
            return

        self.vendor = details.get("vendor") or None
        self.model = details.get("model") or None
        self.firmware = details.get("firmware") or None
        self.charger_name = details.get("name") or self.charger_name

    async def _async_update_data(self) -> ChargeSentryData:
        """Fetch the live feed, energy totals and any armed delayed charge."""
        try:
            if self.charger_id is None:
                await self._async_resolve_charger()

            live_task = self.client.async_get_live_details(self.serial)
            energy_task = self.client.async_get_energy(self.serial)
            connected_task = self.client.async_get_charger_by_serial(self.serial)

            live_res, energy_res, connected_res = await asyncio.gather(
                live_task, energy_task, connected_task, return_exceptions=True
            )

            # The live feed is the one that has to succeed.
            if isinstance(live_res, BaseException):
                raise live_res
            live: dict[str, Any] = live_res

            energy: dict[str, Any] | None = None
            if isinstance(energy_res, ChargeSentryNotFoundError):
                # "no meter data recorded" — normal on a charger that has never
                # delivered a kWh. Leave the energy sensors unknown.
                _LOGGER.debug("No meter data yet for %s", self.serial)
            elif isinstance(energy_res, BaseException):
                if isinstance(
                    energy_res, (ChargeSentryAuthError, ChargeSentryForbiddenError)
                ):
                    raise energy_res
                _LOGGER.debug("Energy fetch failed for %s: %s", self.serial, energy_res)
            else:
                energy = energy_res

            online: bool | None = None
            if not isinstance(connected_res, BaseException):
                online = str(connected_res.get("online", "")) == "1"

            delay = await self._async_fetch_delay(live)

            return ChargeSentryData(
                live=live, energy=energy, delay=delay, online=online
            )

        except ChargeSentryAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except ChargeSentryForbiddenError as err:
            raise UpdateFailed(
                f"{self.serial}: this account does not administer the charger ({err})"
            ) from err
        except ChargeSentryNotFoundError as err:
            raise UpdateFailed(f"{self.serial}: {err}") from err
        except ChargeSentryConnectionError as err:
            raise UpdateFailed(str(err)) from err
        except ChargeSentryError as err:
            raise UpdateFailed(str(err)) from err

    async def _async_fetch_delay(self, live: dict[str, Any]) -> dict[str, Any] | None:
        """Return the delayed-charge status for the live connector, if readable."""
        if self.charger_id is None:
            return None
        connector = live.get("connector")
        if connector is None:
            return None
        try:
            return await self.client.async_get_delay_status(
                self.charger_id, int(connector)
            )
        except (ChargeSentryAuthError, ChargeSentryForbiddenError):
            raise
        except ChargeSentryError as err:
            _LOGGER.debug("Delay status unavailable for %s: %s", self.serial, err)
            return None
