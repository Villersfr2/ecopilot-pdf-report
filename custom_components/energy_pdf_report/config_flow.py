"""Flux de configuration pour l'intégration Energy PDF Report."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from homeassistant.helpers import config_validation as cv


from .const import (
    CONF_DEFAULT_REPORT_TYPE,
    CONF_FILENAME_PATTERN,
    CONF_OUTPUT_DIR,
    CONF_PERIOD,
    DEFAULT_FILENAME_PATTERN,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_REPORT_TYPE,
    DOMAIN,
    VALID_REPORT_TYPES,
)


class EnergyPDFReportConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Energy PDF Report."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Gérer l'étape initiale lancée par l'utilisateur."""

        if self._async_current_entries():
            return await self.async_step_reinstall_confirm(user_input)

        if user_input is not None:
            return self.async_create_entry(title="Rapport PDF Énergie", data={})

        return self.async_show_form(step_id="user", data_schema=vol.Schema({}))

    async def async_step_reinstall_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Confirmer la réinstallation en supprimant l'entrée existante."""

        existing_entries = self._async_current_entries()
        if not existing_entries:
            return await self.async_step_user(user_input)

        if user_input is not None:
            removed = await self.hass.config_entries.async_remove(
                existing_entries[0].entry_id
            )
            if not removed:
                return self.async_abort(reason="remove_failed")

            return await self.async_step_user({})

        return self.async_show_form(
            step_id="reinstall_confirm",
            data_schema=vol.Schema({}),
            description_placeholders={
                "title": existing_entries[0].title,
            },
        )

    async def async_step_import(
        self, user_input: dict[str, Any]
    ) -> config_entries.ConfigFlowResult:
        """Gérer une importation depuis YAML."""


        if self._async_current_entries():
            return self.async_abort(reason="already_configured")

        return self.async_create_entry(title="Rapport PDF Énergie", data={})



class EnergyPDFReportOptionsFlowHandler(config_entries.OptionsFlow):
    """Gérer le flux d'options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialiser la classe."""

        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:

        """Gérer l'étape initiale du flux d'options."""


        options = dict(self.config_entry.options or {})

        legacy_period = options.get(CONF_PERIOD)

        if user_input is not None:
            cleaned = {
                CONF_OUTPUT_DIR: user_input[CONF_OUTPUT_DIR].strip(),
                CONF_FILENAME_PATTERN: user_input[CONF_FILENAME_PATTERN].strip(),
            }
            default_report_type = user_input.get(CONF_DEFAULT_REPORT_TYPE)
            if default_report_type:
                cleaned[CONF_DEFAULT_REPORT_TYPE] = default_report_type
            return self.async_create_entry(title="", data=cleaned)

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_OUTPUT_DIR,
                    default=options.get(CONF_OUTPUT_DIR, DEFAULT_OUTPUT_DIR),
                ): cv.string,
                vol.Required(
                    CONF_FILENAME_PATTERN,
                    default=options.get(
                        CONF_FILENAME_PATTERN, DEFAULT_FILENAME_PATTERN
                    ),
                ): vol.All(cv.string, vol.Match(r".*\S.*")),
                vol.Optional(
                    CONF_DEFAULT_REPORT_TYPE,
                    default=options.get(
                        CONF_DEFAULT_REPORT_TYPE,
                        legacy_period if legacy_period in VALID_REPORT_TYPES else DEFAULT_REPORT_TYPE,
                    ),
                ): vol.In(VALID_REPORT_TYPES),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
        )


async def async_get_options_flow(config_entry: config_entries.ConfigEntry):
    """Return the options flow handler for this config entry."""

    return EnergyPDFReportOptionsFlowHandler(config_entry)
