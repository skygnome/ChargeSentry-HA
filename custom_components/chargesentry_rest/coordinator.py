from __future__ import annotations
import logging
from datetime import timedelta
from urllib.parse import quote  # <-- add this
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
import aiohttp

from .const import LIVE_URL, ENERGY_URL

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(seconds=120)

class ChargeSentryDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, *, token: str, serial: str):
        super().__init__(hass, logger=_LOGGER, name="ChargeSentry", update_interval=SCAN_INTERVAL)
        self._token = token
        self._serial = serial
        self.last_status_code: int | None = None

    @property
    def serial(self) -> str:
        return self._serial

    def _fmt(self, template: str) -> str:
        """Replace {serial} if present; leave as-is otherwise. URL-encode serial."""
        if "{serial}" in template:
            return template.format(serial=quote(self._serial, safe=""))
        return template

    async def _async_update_data(self):
        headers = {"Authorization": f"Bearer {self._token}"}
        try:
            async with aiohttp.ClientSession() as session:
                live_url = self._fmt(LIVE_URL)
                energy_url = self._fmt(ENERGY_URL)

                async with session.get(live_url, headers=headers, timeout=20) as resp:
                    self.last_status_code = resp.status
                    if resp.status == 401:
                        raise UpdateFailed("Unauthorized (401) — token invalid or expired")
                    if resp.status == 404:
                        raise UpdateFailed(f"Live URL not found (404): {live_url}")
                    resp.raise_for_status()
                    live = await resp.json()

                async with session.get(energy_url, headers=headers, timeout=20) as resp:
                    if resp.status == 404:
                        raise UpdateFailed(f"Energy URL not found (404): {energy_url}")
                    resp.raise_for_status()
                    energy = await resp.json()

                return {"serial": self._serial, "live": live, "energy": energy}

        except Exception as err:
            raise UpdateFailed(str(err)) from err
