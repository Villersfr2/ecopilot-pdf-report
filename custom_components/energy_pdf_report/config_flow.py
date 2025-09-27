"""Flux de configuration pour l'intégration Energy PDF Report."""

from __future__ import annotations
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_CO2_ELECTRICITY,
    CONF_CO2_GAS,
    CONF_CO2_SAVINGS,
    CONF_CO2_WATER,
    CONF_DEFAULT_REPORT_TYPE,
    CONF_FILENAME_PATTERN,
    CONF_OUTPUT_DIR,
    CONF_LANGUAGE,
    DEFAULT_CO2_ELECTRICITY_SENSOR,
    DEFAULT_CO2_GAS_SENSOR,
    DEFAULT_CO2_SAVINGS_SENSOR,
    DEFAULT_CO2_WATER_SENSOR,
    DEFAULT_FILENAME_PATTERN,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_REPORT_TYPE,
    DEFAULT_LANGUAGE,
    DOMAIN,
    VALID_REPORT_TYPES,
    SUPPORTED_LANGUAGES,
)


class EnergyPDFReportConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Energy PDF Report."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""

        errors: dict[str, str] = {}

        if user_input is not None:
            return self.async_create_entry(
                title="Rapport PDF Énergie",
                data=user_input,  # 👉 valeurs stockées directement dans data
            )

        # Première installation → afficher formulaire avec valeurs par défaut
        data_schema = vol.Schema(
            {
                vol.Required(CONF_OUTPUT_DIR, default=DEFAULT_OUTPUT_DIR): cv.string,
                vol.Required(CONF_FILENAME_PATTERN, default=DEFAULT_FILENAME_PATTERN): cv.string,
                vol.Required(CONF_DEFAULT_REPORT_TYPE, default=DEFAULT_REPORT_TYPE): vol.In(VALID_REPORT_TYPES),
                vol.Required(CONF_LANGUAGE, default=DEFAULT_LANGUAGE): vol.In(SUPPORTED_LANGUAGES),
                vol.Required(CONF_CO2_ELECTRICITY, default=DEFAULT_CO2_ELECTRICITY_SENSOR): cv.entity_id,
                vol.Required(CONF_CO2_GAS, default=DEFAULT_CO2_GAS_SENSOR): cv.entity_id,
                vol.Required(CONF_CO2_WATER, default=DEFAULT_CO2_WATER_SENSOR): cv.entity_id,
                vol.Required(CONF_CO2_SAVINGS, default=DEFAULT_CO2_SAVINGS_SENSOR): cv.entity_id,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )


class EnergyPDFReportOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for Energy PDF Report."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:

        data = dict(self.config_entry.data)  # 👉 récupérer les valeurs de base
        data.update(self.config_entry.options)

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        data_schema = vol.Schema(
            {
                vol.Required(CONF_OUTPUT_DIR, default=data.get(CONF_OUTPUT_DIR, DEFAULT_OUTPUT_DIR)): cv.string,
                vol.Required(CONF_FILENAME_PATTERN, default=data.get(CONF_FILENAME_PATTERN, DEFAULT_FILENAME_PATTERN)): cv.string,
                vol.Required(CONF_DEFAULT_REPORT_TYPE, default=data.get(CONF_DEFAULT_REPORT_TYPE, DEFAULT_REPORT_TYPE)): vol.In(VALID_REPORT_TYPES),
                vol.Required(CONF_LANGUAGE, default=data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)): vol.In(SUPPORTED_LANGUAGES),
                vol.Required(CONF_CO2_ELECTRICITY, default=data.get(CONF_CO2_ELECTRICITY, DEFAULT_CO2_ELECTRICITY_SENSOR)): cv.entity_id,
                vol.Required(CONF_CO2_GAS, default=data.get(CONF_CO2_GAS, DEFAULT_CO2_GAS_SENSOR)): cv.entity_id,
                vol.Required(CONF_CO2_WATER, default=data.get(CONF_CO2_WATER, DEFAULT_CO2_WATER_SENSOR)): cv.entity_id,
                vol.Required(CONF_CO2_SAVINGS, default=data.get(CONF_CO2_SAVINGS, DEFAULT_CO2_SAVINGS_SENSOR)): cv.entity_id,
            }
        )

        return self.async_show_form(step_id="init", data_schema=data_schema)


async def async_get_options_flow(config_entry: config_entries.ConfigEntry):
    """Return the options flow handler."""
    return EnergyPDFReportOptionsFlowHandler(config_entry)
