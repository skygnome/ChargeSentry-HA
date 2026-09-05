"""Config flow for ChargeSentry."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from contextlib import suppress
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import (
    ChargeSentryApiClient,
    ChargeSentryAuthError,
    ChargeSentryConnectionError,
    ChargeSentryError,
    ChargeSentryForbiddenError,
    ChargeSentryNotFoundError,
)
from .const import (
    CONF_BASE_URL,
    CONF_SCAN_INTERVAL,
    CONF_SERIAL,
    CONF_TOKEN,
    DEFAULT_BASE_URL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

_TOKEN_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))


def _user_schema(defaults: Mapping[str, Any] | None = None) -> vol.Schema:
    """Build the credentials form, pre-filled from ``defaults``."""
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_TOKEN, default=defaults.get(CONF_TOKEN, vol.UNDEFINED)
            ): _TOKEN_SELECTOR,
            vol.Required(
                CONF_SERIAL, default=defaults.get(CONF_SERIAL, vol.UNDEFINED)
            ): str,
            vol.Optional(
                CONF_BASE_URL, default=defaults.get(CONF_BASE_URL, DEFAULT_BASE_URL)
            ): str,
        }
    )


async def _async_validate(
    hass, token: str, serial: str, base_url: str
) -> tuple[str, str]:
    """Check the credentials and return ``(canonical_serial, charger_name)``.

    Resolving the serial proves the token works; reading the live feed proves
    the account actually administers the charger, which is what the HA
    endpoints require.
    """
    client = ChargeSentryApiClient(async_get_clientsession(hass), token, base_url)
    charger = await client.async_get_charger_by_serial(serial)
    canonical = str(charger.get("serial") or serial)
    name = str(charger.get("name") or canonical)

    # details.php 404s only on an unknown serial, which the lookup above has
    # already ruled out — so a 404 here is not worth failing setup over. A 401
    # or 403 still propagates, which is the point of the call.
    with suppress(ChargeSentryNotFoundError):
        await client.async_get_live_details(canonical)

    return canonical, name


def _error_for(err: Exception) -> str:
    """Map an API error onto a config-flow error key."""
    if isinstance(err, ChargeSentryAuthError):
        return "invalid_auth"
    if isinstance(err, ChargeSentryForbiddenError):
        return "not_admin"
    if isinstance(err, ChargeSentryNotFoundError):
        return "unknown_serial"
    if isinstance(err, ChargeSentryConnectionError):
        return "cannot_connect"
    return "unknown"


class ChargeSentryConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle setup, reauth and reconfiguration of a ChargeSentry charger."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for an API token and a charger serial."""
        errors: dict[str, str] = {}

        if user_input is not None:
            token = user_input[CONF_TOKEN].strip()
            serial = user_input[CONF_SERIAL].strip()
            base_url = (user_input.get(CONF_BASE_URL) or DEFAULT_BASE_URL).strip()

            try:
                canonical, name = await _async_validate(
                    self.hass, token, serial, base_url
                )
            except ChargeSentryError as err:
                errors["base"] = _error_for(err)
            except Exception:
                _LOGGER.exception("Unexpected error validating ChargeSentry setup")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(canonical.lower())
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=name,
                    data={
                        CONF_TOKEN: token,
                        CONF_SERIAL: canonical,
                        CONF_BASE_URL: base_url,
                    },
                )

        return self.async_show_form(
            step_id="user", data_schema=_user_schema(user_input), errors=errors
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Start reauth after the API rejected the stored token."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for a fresh API token for an existing entry."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            token = user_input[CONF_TOKEN].strip()
            serial = str(entry.data.get(CONF_SERIAL, ""))
            base_url = str(entry.data.get(CONF_BASE_URL, DEFAULT_BASE_URL))

            try:
                await _async_validate(self.hass, token, serial, base_url)
            except ChargeSentryError as err:
                errors["base"] = _error_for(err)
            except Exception:
                _LOGGER.exception("Unexpected error validating ChargeSentry token")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_TOKEN: token}
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_TOKEN): _TOKEN_SELECTOR}),
            description_placeholders={"serial": str(entry.data.get(CONF_SERIAL, ""))},
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change the token, serial or API host of an existing entry."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            token = user_input[CONF_TOKEN].strip()
            serial = user_input[CONF_SERIAL].strip()
            base_url = (user_input.get(CONF_BASE_URL) or DEFAULT_BASE_URL).strip()

            try:
                canonical, _name = await _async_validate(
                    self.hass, token, serial, base_url
                )
            except ChargeSentryError as err:
                errors["base"] = _error_for(err)
            except Exception:
                _LOGGER.exception("Unexpected error validating ChargeSentry setup")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(canonical.lower())
                self._abort_if_unique_id_mismatch(reason="wrong_charger")
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={
                        CONF_TOKEN: token,
                        CONF_SERIAL: canonical,
                        CONF_BASE_URL: base_url,
                    },
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_user_schema(user_input or entry.data),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow handler."""
        return ChargeSentryOptionsFlow()


class ChargeSentryOptionsFlow(OptionsFlow):
    """Let the user tune how often the charger is polled."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show and store the polling interval."""
        if user_input is not None:
            return self.async_create_entry(
                data={CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL])}
            )

        current = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SCAN_INTERVAL, default=current): NumberSelector(
                        NumberSelectorConfig(
                            min=MIN_SCAN_INTERVAL,
                            max=MAX_SCAN_INTERVAL,
                            step=5,
                            unit_of_measurement="s",
                            mode=NumberSelectorMode.BOX,
                        )
                    )
                }
            ),
        )
