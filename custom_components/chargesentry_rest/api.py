"""Thin async client for the ChargeSentry REST API.

Endpoint reference lives in the API repo under ``docs/ha`` and
``docs/account``. Everything here is a plain authenticated ``GET`` returning
a JSON envelope with a ``success`` flag.
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote

import aiohttp

from .const import (
    PATH_CHARGER_BY_SERIAL,
    PATH_CHARGER_DETAILS,
    PATH_DELAY_CANCEL,
    PATH_DELAY_START,
    PATH_DELAY_STATUS,
    PATH_LIVE_DETAILS,
    PATH_LIVE_ENERGY,
    PATH_START_CHARGE,
    PATH_STOP_CHARGE,
    REQUEST_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)


class ChargeSentryError(Exception):
    """Base error for every failure this client raises."""


class ChargeSentryConnectionError(ChargeSentryError):
    """The API host could not be reached, or the response was unreadable."""


class ChargeSentryAuthError(ChargeSentryError):
    """The bearer token was missing, invalid or expired (HTTP 401)."""


class ChargeSentryForbiddenError(ChargeSentryError):
    """The token is valid but the account does not administer this charger (403).

    ``ha/details.php`` and ``ha/energy.php`` are gated on
    ``requireChargerAdmin()`` — being an ordinary member of a public site is
    not enough.
    """


class ChargeSentryNotFoundError(ChargeSentryError):
    """No such charger, or no data recorded for it yet (HTTP 404)."""


class ChargeSentryCommandError(ChargeSentryError):
    """A control command was rejected (402/409/502 and friends)."""


class ChargeSentryApiClient:
    """Minimal client over the handful of endpoints this integration uses."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        token: str,
        base_url: str,
    ) -> None:
        """Store the shared aiohttp session, token and API base URL."""
        self._session = session
        self._token = token
        self._base_url = base_url.rstrip("/")

    @property
    def base_url(self) -> str:
        """Return the API base URL, without a trailing slash."""
        return self._base_url

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict:
        """Perform an authenticated GET and return the decoded JSON body."""
        url = f"{self._base_url}{path}"
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/json",
        }

        try:
            async with self._session.get(
                url,
                headers=headers,
                params=params,
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
            ) as resp:
                # Read the body before branching: the API puts a human-readable
                # "message" on its error envelopes and it is the most useful
                # thing to surface to the user.
                try:
                    payload = await resp.json(content_type=None)
                except (ValueError, aiohttp.ClientError):
                    payload = None

                message = None
                if isinstance(payload, dict):
                    message = payload.get("message")

                if resp.status == 401:
                    raise ChargeSentryAuthError(message or "Token invalid or expired")
                if resp.status == 403:
                    raise ChargeSentryForbiddenError(
                        message or "This account does not administer that charger"
                    )
                if resp.status == 404:
                    raise ChargeSentryNotFoundError(message or "Not found")
                if resp.status >= 400:
                    raise ChargeSentryCommandError(
                        message or f"API returned HTTP {resp.status}"
                    )

                if not isinstance(payload, dict):
                    raise ChargeSentryConnectionError(
                        f"Unexpected response body from {path}"
                    )
                if payload.get("success") is False:
                    raise ChargeSentryCommandError(
                        payload.get("message") or "Request was not successful"
                    )
                return payload

        except TimeoutError as err:
            raise ChargeSentryConnectionError(f"Timeout calling {path}") from err
        except aiohttp.ClientError as err:
            raise ChargeSentryConnectionError(f"Error calling {path}: {err}") from err

    @staticmethod
    def _quote(value: Any) -> str:
        """URL-encode a path segment."""
        return quote(str(value), safe="")

    # -- Read-only -----------------------------------------------------------

    async def async_get_live_details(self, serial: str) -> dict:
        """Return live connector status, power/voltage/current and session id."""
        return await self._get(PATH_LIVE_DETAILS.format(serial=self._quote(serial)))

    async def async_get_energy(self, serial: str) -> dict:
        """Return lifetime and today's delivered energy for a charger."""
        return await self._get(PATH_LIVE_ENERGY.format(serial=self._quote(serial)))

    async def async_get_charger_by_serial(self, serial: str) -> dict:
        """Resolve a serial to its charger row (id, name, online flag)."""
        payload = await self._get(
            PATH_CHARGER_BY_SERIAL.format(serial=self._quote(serial))
        )
        charger = payload.get("charger")
        if not isinstance(charger, dict):
            raise ChargeSentryNotFoundError(f"No charger with serial {serial}")
        return charger

    async def async_get_charger_details(self, charger_id: int) -> dict:
        """Return the full charger record: vendor, model, firmware, sockets."""
        payload = await self._get(
            PATH_CHARGER_DETAILS.format(charger_id=self._quote(charger_id))
        )
        charger = payload.get("charger")
        if not isinstance(charger, dict):
            raise ChargeSentryNotFoundError(f"No charger with id {charger_id}")
        return charger

    async def async_get_delay_status(self, charger_id: int, connector: int) -> dict:
        """Return the delayed charge armed or running on a connector."""
        return await self._get(
            PATH_DELAY_STATUS.format(
                charger_id=self._quote(charger_id), connector=self._quote(connector)
            )
        )

    # -- Control -------------------------------------------------------------

    async def async_start_charge(
        self,
        charger_id: int,
        connector: int,
        limit_kwh: float | None = None,
    ) -> dict:
        """Remote-start a charge, optionally capped at ``limit_kwh``."""
        params: dict[str, Any] = {"type": "1" if limit_kwh else "0"}
        if limit_kwh:
            params["limit"] = limit_kwh
        return await self._get(
            PATH_START_CHARGE.format(
                charger_id=self._quote(charger_id), connector=self._quote(connector)
            ),
            params=params,
        )

    async def async_stop_charge(self, charger_id: int, connector: int) -> dict:
        """Remote-stop the account's own active session on a connector."""
        return await self._get(
            PATH_STOP_CHARGE.format(
                charger_id=self._quote(charger_id), connector=self._quote(connector)
            )
        )

    async def async_delay_start(
        self,
        charger_id: int,
        connector: int,
        delay_seconds: int,
        run_for_seconds: int | None = None,
        limit_kwh: float | None = None,
    ) -> dict:
        """Arm a delayed charge on a connector the vehicle is plugged into."""
        params: dict[str, Any] = {
            "delay_seconds": delay_seconds,
            "type": "1" if limit_kwh else "0",
        }
        if run_for_seconds:
            params["run_for_seconds"] = run_for_seconds
        if limit_kwh:
            params["limit"] = limit_kwh
        return await self._get(
            PATH_DELAY_START.format(
                charger_id=self._quote(charger_id), connector=self._quote(connector)
            ),
            params=params,
        )

    async def async_cancel_delay(self, charger_id: int, connector: int) -> dict:
        """Cancel a delayed charge that has not started yet."""
        return await self._get(
            PATH_DELAY_CANCEL.format(
                charger_id=self._quote(charger_id), connector=self._quote(connector)
            )
        )
