from __future__ import annotations
import logging
from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
import aiohttp

from .const import LIVE_URL, ENERGY_URL  # your existing constants

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(seconds=120)

class ChargeSentryDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, *, token: str, serial: str):
        super().__init__(hass, logger=_LOGGER, name="ChargeSentry", update_interval=SCAN_INTERVAL)
        self._token = token
        self._serial = serial
        self.last_status_code: int | None = None

    async def _async_update_data(self):
        headers = {"Authorization": f"Bearer {self._token}"}
        try:
            async with aiohttp.ClientSession() as session:
                # If your endpoints require the serial as a query/path param, add it as you already do.
                # Examples (PSEUDO — keep your real URLs untouched):
                # live_url = f"{LIVE_URL}?serial={self._serial}"
                # energy_url = f"{ENERGY_URL}?serial={self._serial}"
                live_url = LIVE_URL
                energy_url = ENERGY_URL

                async with session.get(live_url, headers=headers, timeout=20) as resp:
                    self.last_status_code = resp.status
                    if resp.status == 401:
                        raise UpdateFailed("Unauthorized")
                    resp.raise_for_status()
                    live = await resp.json()

                async with session.get(energy_url, headers=headers, timeout=20) as resp:
                    resp.raise_for_status()
                    energy = await resp.json()

                # If you need serial downstream, include it in the return
                return {"serial": self._serial, "live": live, "energy": energy}

        except Exception as err:
            raise UpdateFailed(str(err)) from err
