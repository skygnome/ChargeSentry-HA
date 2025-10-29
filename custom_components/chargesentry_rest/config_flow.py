from __future__ import annotations
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, CONF_TOKEN, CONF_SERIAL


class ChargeSentryConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_TOKEN): str,   # Bearer token only
                        vol.Required(CONF_SERIAL): str,  # Charger serial (e.g. AE0007A1…)
                    }
                ),
            )

        await self.async_set_unique_id(DOMAIN)  # single entry; change to serial if you want multiples
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title="ChargeSentry",
            data={
                CONF_TOKEN: user_input[CONF_TOKEN].strip(),
                CONF_SERIAL: user_input[CONF_SERIAL].strip(),
            },
        )

    async def async_step_reauth(self, user_input=None) -> FlowResult:
        return await self._start_options_for_entry(self.context["entry_id"])

    async def _start_options_for_entry(self, entry_id: str) -> FlowResult:
        entry = self.hass.config_entries.async_get_entry(entry_id)
        return await self.hass.config_entries.options.async_init(entry.entry_id)

    @staticmethod
    def async_get_options_flow(config_entry):
        return ChargeSentryOptionsFlow(config_entry)


class ChargeSentryOptionsFlow(config_entries.OptionsFlowWithReload):
    """Allow changing token and serial; auto-reload on save."""

    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self.entry = entry

    async def async_step_init(self, user_input=None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(
                title="",
                data={
                    CONF_TOKEN: user_input[CONF_TOKEN].strip(),
                    CONF_SERIAL: user_input[CONF_SERIAL].strip(),
                },
            )

        current_token = self.entry.options.get(CONF_TOKEN) or self.entry.data.get(CONF_TOKEN, "")
        current_serial = self.entry.options.get(CONF_SERIAL) or self.entry.data.get(CONF_SERIAL, "")
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_TOKEN, default=current_token): str,
                    vol.Required(CONF_SERIAL, default=current_serial): str,
                }
            ),
        )
