from __future__ import annotations
from datetime import timedelta
import aiohttp
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.core import HomeAssistant
from .const import (
    DEFAULT_SCAN_INTERVAL, CONF_SERIAL, CONF_TOKEN,
    ENERGY_URL, LIVE_URL
)

class ChargeSentryCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, entry):
        self.hass = hass
        self.entry = entry
        self.serial = entry.data[CONF_SERIAL].lower()
        self.token = entry.data.get(CONF_TOKEN)
        super().__init__(
            hass,
            logger=hass.helpers.logger.logger.getChild("chargesentry_rest"),
            name=f"ChargeSentry {self.serial}",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL)
        )

    async def _async_update_data(self):
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        live_url = LIVE_URL.format(serial=self.serial)
        totals_url = ENERGY_URL.format(serial=self.serial)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(live_url, headers=headers, timeout=8) as r1:
                    if r1.status != 200:
                        raise UpdateFailed(f"Live {r1.status}")
                    live = await r1.json()

                async with session.get(totals_url, headers=headers, timeout=8) as r2:
                    if r2.status != 200:
                        raise UpdateFailed(f"Energy {r2.status}")
                    totals = await r2.json()

            # Map to what sensors expect
            power_w = float(live.get("power_w") or live.get("power") or 0.0)
            status = (live.get("status") or "unknown").lower()
            lifetime_kwh = float(totals.get("lifetime_kwh") or totals.get("lifetime") or 0.0)

            return {
                "live": live,
                "totals": totals,
                "power_w": power_w,
                "status": status,
                "lifetime_kwh": lifetime_kwh
            }
        except Exception as exc:
            raise UpdateFailed(str(exc)) from exc
