from __future__ import annotations
import voluptuous as vol
from homeassistant import config_entries
from .const import DOMAIN, CONF_SERIAL, CONF_TOKEN

DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_SERIAL): str,   # charger serial (lower/upper both ok)
    vol.Optional(CONF_TOKEN): str     # optional Bearer token if your API requires it
})

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, user_input=None):
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA)

        serial = user_input[CONF_SERIAL].lower()
        await self.async_set_unique_id(f"{DOMAIN}_{serial}")
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=f"ChargeSentry {serial}",
            data=user_input
        )
