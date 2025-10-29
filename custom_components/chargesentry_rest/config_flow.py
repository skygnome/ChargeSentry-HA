from __future__ import annotations
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, CONF_TOKEN


class ChargeSentryConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_TOKEN): str,  # Bearer token value only
                    }
                ),
            )

        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title="ChargeSentry",
            data={CONF_TOKEN: user_input[CONF_TOKEN].strip()},
        )

    async def async_step_reauth(self, user_input=None) -> FlowResult:
        # Route reauth to the options flow so the user can paste a new token
        return await self._start_options_for_entry(self.context["entry_id"])

    async def _start_options_for_entry(self, entry_id: str) -> FlowResult:
        entry = self.hass.config_entries.async_get_entry(entry_id)
        return await self.hass.config_entries.options.async_init(entry.entry_id)

    @staticmethod
    def async_get_options_flow(config_entry):
        return ChargeSentryOptionsFlow(config_entry)


class ChargeSentryOptionsFlow(config_entries.OptionsFlowWithReload):
    """Only allow changing the token; reloads the entry automatically on save."""

    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self.entry = entry

    async def async_step_init(self, user_input=None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(
                title="",
                data={CONF_TOKEN: user_input[CONF_TOKEN].strip()},
            )

        # default value prefers options, then data
        current_token = self.entry.options.get(CONF_TOKEN) or self.entry.data.get(CONF_TOKEN, "")
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({vol.Required(CONF_TOKEN, default=current_token): str}),
        )
