from __future__ import annotations
from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DEFAULT_SCAN_INTERVAL, CONF_SERIAL, CONF_TOKEN,
    ENERGY_URL, LIVE_URL
)

_LOGGER = logging.getLogger(__name__)

class ChargeSentryCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, entry):
        self.hass = hass
        self.entry = entry
        self.serial = entry.data[CONF_SERIAL].lower()
        self.token = entry.data.get(CONF_TOKEN)

        super().__init__(
            hass,
            logger=_LOGGER,
            name=f"ChargeSentry {self.serial}",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

        # cache for energy if you later want different polling cadences
        self._last_totals: dict[str, Any] | None = None

    async def _async_update_data(self) -> dict[str, Any]:
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        live_url = LIVE_URL.format(serial=self.serial)
        totals_url = ENERGY_URL.format(serial=self.serial)

        session = async_get_clientsession(self.hass)

        try:
            async with session.get(live_url, headers=headers, timeout=8) as r1:
                if r1.status != 200:
                    raise UpdateFailed(f"Live HTTP {r1.status}")
                live = await r1.json()

            async with session.get(totals_url, headers=headers, timeout=8) as r2:
                if r2.status != 200:
                    raise UpdateFailed(f"Energy HTTP {r2.status}")
                totals = await r2.json()

            # Normalise / guard keys
            power_w = float(live.get("power_w") or live.get("power") or 0.0)
            status = (live.get("status") or "unknown").lower()
            lifetime_kwh = float(
                totals.get("lifetime_kwh")
                or totals.get("lifetime")
                or 0.0
            )

            data = {
                "live": live,
                "totals": totals,
                "power_w": power_w,
                "status": status,
                "lifetime_kwh": lifetime_kwh,
            }

            return data

        except UpdateFailed:
            # re-raise untouched so HA shows the right reason
            raise
        except Exception as exc:
            raise UpdateFailed(str(exc)) from exc
