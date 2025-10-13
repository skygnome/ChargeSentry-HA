from __future__ import annotations
from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_SERIAL, CONF_TOKEN, DEFAULT_SCAN_INTERVAL,
    ENERGY_URL, LIVE_URL
)

_LOGGER = logging.getLogger(__name__)
LOWERCASE_SERIAL = True  # flip to False if your API is case-sensitive

class ChargeSentryCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, entry):
        self.hass = hass
        self.entry = entry

        serial = entry.data[CONF_SERIAL]
        self.serial = serial.lower() if LOWERCASE_SERIAL else serial

        # Prefer options token; fallback to initial data token
        opt = entry.options
        self.token = (opt.get(CONF_TOKEN) or entry.data.get(CONF_TOKEN) or "").strip()

        super().__init__(
            hass,
            logger=_LOGGER,
            name="ChargeSentry",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "User-Agent": "ha-chargesentry-rest/0.1.x",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def _async_update_data(self) -> dict[str, Any]:
        headers = self._headers()
        live_url = LIVE_URL.format(serial=self.serial)
        totals_url = ENERGY_URL.format(serial=self.serial)
        session = async_get_clientsession(self.hass)

        _LOGGER.debug(
            "Requesting live & energy (120s). token_in_header=%s urls=(%s , %s)",
            "yes" if "Authorization" in headers else "no",
            live_url, totals_url
        )

        try:
            async with session.get(live_url, headers=headers, timeout=8) as r1:
                if r1.status != 200:
                    body = await r1.text()
                    _LOGGER.debug("LIVE error %s: %s", r1.status, body[:300])
                    raise UpdateFailed(f"Live HTTP {r1.status}")
                live = await r1.json(content_type=None)

            async with session.get(totals_url, headers=headers, timeout=8) as r2:
                if r2.status != 200:
                    body = await r2.text()
                    _LOGGER.debug("ENERGY error %s: %s", r2.status, body[:300])
                    raise UpdateFailed(f"Energy HTTP {r2.status}")
                totals = await r2.json(content_type=None)

            power_w = float(live.get("power_w") or live.get("power") or 0.0)
            status = (live.get("status") or "unknown").lower()
            lifetime_kwh = float(totals.get("lifetime_kwh") or totals.get("lifetime") or 0.0)

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
