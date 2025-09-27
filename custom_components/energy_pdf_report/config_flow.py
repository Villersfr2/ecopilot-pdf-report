"""Flux de configuration pour l'intégration Energy PDF Report."""

from __future__ import annotations
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
try:
    from homeassistant.data_entry_flow import FlowResult
except ImportError:  # pragma: no cover - compat with older versions
    FlowResult = dict[str, Any]
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

CO2_SENSOR_DEFAULTS: tuple[tuple[str, str], ...] = (
    (CONF_CO2_ELECTRICITY, DEFAULT_CO2_ELECTRICITY_SENSOR),
    (CONF_CO2_GAS, DEFAULT_CO2_GAS_SENSOR),
    (CONF_CO2_WATER, DEFAULT_CO2_WATER_SENSOR),
    (CONF_CO2_SAVINGS, DEFAULT_CO2_SAVINGS_SENSOR),
)


class EnergyPDFReportConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Energy PDF Report."""

    VERSION = 1

    _ENTITY_OR_EMPTY = vol.Any(cv.entity_id, vol.In([""]))

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""

        errors: dict[str, str] = {}

        if user_input is not None:
            return self.async_create_entry(
                title="Energy PDF Report",
                data=user_input,  # 👉 valeurs stockées directement dans data
            )

        # Première installation → afficher formulaire avec valeurs par défaut
        schema_dict: dict[Any, Any] = {
            vol.Required(CONF_OUTPUT_DIR, default=DEFAULT_OUTPUT_DIR): cv.string,
            vol.Required(CONF_FILENAME_PATTERN, default=DEFAULT_FILENAME_PATTERN): cv.string,
            vol.Required(CONF_DEFAULT_REPORT_TYPE, default=DEFAULT_REPORT_TYPE): vol.In(VALID_REPORT_TYPES),
            vol.Required(CONF_LANGUAGE, default=DEFAULT_LANGUAGE): vol.In(SUPPORTED_LANGUAGES),
        }

        for option_key, default in CO2_SENSOR_DEFAULTS:
            schema_dict[vol.Required(option_key, default=default)] = cv.entity_id

        data_schema = vol.Schema(schema_dict)

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

        schema_dict = {
            vol.Required(
                CONF_OUTPUT_DIR,
                default=data.get(CONF_OUTPUT_DIR, DEFAULT_OUTPUT_DIR),
            ): cv.string,
            vol.Required(
                CONF_FILENAME_PATTERN,
                default=data.get(CONF_FILENAME_PATTERN, DEFAULT_FILENAME_PATTERN),
            ): cv.string,
            vol.Required(
                CONF_DEFAULT_REPORT_TYPE,
                default=data.get(CONF_DEFAULT_REPORT_TYPE, DEFAULT_REPORT_TYPE),
            ): vol.In(VALID_REPORT_TYPES),
            vol.Required(
                CONF_LANGUAGE,
                default=data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE),
            ): vol.In(SUPPORTED_LANGUAGES),
        }

        for option_key, default in CO2_SENSOR_DEFAULTS:
            schema_dict[
                vol.Required(
                    option_key,
                    default=data.get(option_key, default),
                )
            ] = cv.entity_id

        data_schema = vol.Schema(schema_dict)

        return self.async_show_form(step_id="init", data_schema=data_schema)


async def async_get_options_flow(config_entry: config_entries.ConfigEntry):
    """Return the options flow handler."""
    return EnergyPDFReportOptionsFlowHandler(config_entry)
