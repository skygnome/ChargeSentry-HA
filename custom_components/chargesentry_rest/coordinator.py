from __future__ import annotations
from datetime import timedelta
import logging
from typing import Any
from urllib.parse import urlencode, urlsplit, urlunsplit

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DEFAULT_SCAN_INTERVAL, CONF_SERIAL, CONF_TOKEN, CONF_SCAN_INTERVAL,
    CONF_AUTH_MODE, CONF_AUTH_QUERY_NAME,
    ENERGY_URL, LIVE_URL
)

_LOGGER = logging.getLogger(__name__)

# If your API is case-sensitive for serials, flip this to False.
LOWERCASE_SERIAL = True

class ChargeSentryCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, entry):
        self.hass = hass
        self.entry = entry

        serial = entry.data[CONF_SERIAL]
        self.serial = serial.lower() if LOWERCASE_SERIAL else serial

        # Read editable values from options (token, auth), with data as fallback
        opt = entry.options
        self.token = (opt.get(CONF_TOKEN) or entry.data.get(CONF_TOKEN) or "").strip()
        self.auth_mode = opt.get(CONF_AUTH_MODE, "bearer")
        self.auth_query_name = opt.get(CONF_AUTH_QUERY_NAME, "token")

        # HARD-CODE the scan interval to 120s (ignore any option or default)
        fixed_secs = 120

        super().__init__(
            hass,
            logger=_LOGGER,
            name=f"ChargeSentry {self.serial}",
            update_interval=timedelta(seconds=fixed_secs),
        )

        # For future split polling you could cache totals here
        self._last_totals: dict[str, Any] | None = None

    def _build_headers_and_urls(self):
        headers = {
            "Accept": "application/json",
            "User-Agent": "ha-chargesentry-rest/0.1.x",
        }

        token = self.token
        # Header-based auth
        if token:
            if self.auth_mode == "bearer":
                headers["Authorization"] = f"Bearer {token}"
            elif self.auth_mode == "token":
                headers["Authorization"] = f"Token {token}"
            elif self.auth_mode == "x-api-key":
                headers["X-API-Key"] = token
            # "query" handled below

        live_url = LIVE_URL.format(serial=self.serial)
        totals_url = ENERGY_URL.format(serial=self.serial)

        # Query-string auth mode
        if self.auth_mode == "query" and token:
            def add_q(url: str) -> str:
                parts = urlsplit(url)
                q = dict([kv.split("=", 1) for kv in parts.query.split("&") if kv]) if parts.query else {}
                q[self.auth_query_name] = token
                return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(q), parts.fragment))
            live_url = add_q(live_url)
            totals_url = add_q(totals_url)

        _LOGGER.debug(
            "Requesting live & energy. auth=%s token_in_header=%s urls=(%s , %s)",
            self.auth_mode,
            "yes" if ("Authorization" in headers or "X-API-Key" in headers) else "no",
            live_url, totals_url
        )
        return headers, live_url, totals_url

    async def _async_update_data(self) -> dict[str, Any]:
        headers, live_url, totals_url = self._build_headers_and_urls()
        session = async_get_clientsession(self.hass)

        try:
            # --- LIVE ---
            async with session.get(live_url, headers=headers, timeout=8) as r1:
                if r1.status != 200:
                    body = await r1.text()
                    _LOGGER.debug("LIVE error %s: %s", r1.status, body[:300])
                    raise UpdateFailed(f"Live HTTP {r1.status}")
                live = await r1.json(content_type=None)

            # --- ENERGY/TOTALS ---
            async with session.get(totals_url, headers=headers, timeout=8) as r2:
                if r2.status != 200:
                    body = await r2.text()
                    _LOGGER.debug("ENERGY error %s: %s", r2.status, body[:300])
                    raise UpdateFailed(f"Energy HTTP {r2.status}")
                totals = await r2.json(content_type=None)

            # Normalise keys (be forgiving with field names)
            power_w = float(live.get("power_w") or live.get("power") or 0.0)
            status = (live.get("status") or "unknown").lower()
            lifetime_kwh = float(
                totals.get("lifetime_kwh")
                or totals.get("lifetime")
                or 0.0
            )

            return {
                "live": live,
                "totals": totals,
                "power_w": power_w,
                "status": status,
                "lifetime_kwh": lifetime_kwh,
            }

        except UpdateFailed:
            raise
        except Exception as exc:
            _LOGGER.debug("Unexpected error: %r", exc)
            raise UpdateFailed(str(exc)) from exc
