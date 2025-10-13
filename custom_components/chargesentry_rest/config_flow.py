from __future__ import annotations
import voluptuous as vol
from homeassistant import config_entries
from .const import DOMAIN, CONF_SERIAL, CONF_TOKEN

# First-time setup (serial + optional token)
DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_SERIAL): str,
    vol.Optional(CONF_TOKEN): str,
})

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, user_input=None):
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA)

        serial = user_input[CONF_SERIAL]
        await self.async_set_unique_id(f"{DOMAIN}_{serial.lower()}")
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=f"ChargeSentry {serial}",
            data=user_input,
        )

# Options: allow changing the token later via “Configure”
class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self.entry = entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        opt = self.entry.options
        data = self.entry.data

        schema = vol.Schema({
            vol.Optional(CONF_TOKEN, default=opt.get(CONF_TOKEN, data.get(CONF_TOKEN, ""))): str,
        })
        return self.async_show_form(step_id="init", data_schema=schema)

async def async_get_options_flow(config_entry):
    return OptionsFlowHandler(config_entry)
