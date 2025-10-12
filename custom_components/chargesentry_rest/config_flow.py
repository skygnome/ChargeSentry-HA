from __future__ import annotations
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from .const import DOMAIN, CONF_BASE_URL, CONF_SERIAL, CONF_TOKEN

DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_BASE_URL): str,  # e.g. http://server:8000
    vol.Required(CONF_SERIAL): str,    # charger serial as your API expects
    vol.Optional(CONF_TOKEN): str
})

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, user_input=None):
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA)

        await self.async_set_unique_id(f"{user_input[CONF_BASE_URL]}_{user_input[CONF_SERIAL]}")
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=f"ChargeSentry {user_input[CONF_SERIAL]}",
            data=user_input
        )
