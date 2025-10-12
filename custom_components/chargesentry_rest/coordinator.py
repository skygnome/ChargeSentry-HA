from __future__ import annotations
from datetime import timedelta
import aiohttp
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.core import HomeAssistant
from .const import DEFAULT_SCAN_INTERVAL, CONF_BASE_URL, CONF_SERIAL, CONF_TOKEN

class ChargeSentryCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, entry):
        self.hass = hass
        self.entry = entry
        self.base = entry.data[CONF_BASE_URL].rstrip("/")
        self.serial = entry.data[CONF_SERIAL]
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

        live_url = f"{self.base}/ha/charger/{self.serial}/live"
        totals_url = f"{self.base}/ha/charger/{self.serial}/totals"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(live_url, headers=headers, timeout=8) as r1:
                    if r1.status != 200:
                        raise UpdateFailed(f"Live {r1.status}")
                    live = await r1.json()

                async with session.get(totals_url, headers=headers, timeout=8) as r2:
                    if r2.status != 200:
                        raise UpdateFailed(f"Totals {r2.status}")
                    totals = await r2.json()

            # Normalise / guard
            power_w = float(live.get("power_w") or 0.0)
            status = (live.get("status") or "unknown").lower()
            lifetime_kwh = float(totals.get("lifetime_kwh") or 0.0)

            return {
                "live": live,
                "totals": totals,
                "power_w": power_w,
                "status": status,
                "lifetime_kwh": lifetime_kwh
            }
        except Exception as exc:
            raise UpdateFailed(str(exc)) from exc
