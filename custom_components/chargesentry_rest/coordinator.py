from __future__ import annotations
from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
import aiohttp

from .const import CONF_TOKEN  # for clarity if needed
from .const import LIVE_URL, ENERGY_URL  # your existing constants

SCAN_INTERVAL = timedelta(seconds=120)

class ChargeSentryDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, *, token: str):
        super().__init__(hass, logger=hass.logger, name="ChargeSentry", update_interval=SCAN_INTERVAL)
        self._token = token
        self.last_status_code: int | None = None

    async def _async_update_data(self):
        headers = {"Authorization": f"Bearer {self._token}"}
        try:
            async with aiohttp.ClientSession() as session:
                # Example: fetch live first; you can keep your existing sequence/logic
                async with session.get(LIVE_URL, headers=headers, timeout=20) as resp:
                    self.last_status_code = resp.status
                    if resp.status == 401:
                        raise UpdateFailed("Unauthorized")
                    resp.raise_for_status()
                    live = await resp.json()

                # If you also fetch energy_url here, keep doing so as before
                async with session.get(ENERGY_URL, headers=headers, timeout=20) as resp:
                    resp.raise_for_status()
                    energy = await resp.json()

                return {"live": live, "energy": energy}

        except Exception as err:
            raise UpdateFailed(str(err)) from err
