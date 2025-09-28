"""Flux de configuration pour l'intégration Energy PDF Report."""

from __future__ import annotations

from collections.abc import Mapping
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
    CONF_LANGUAGE,
    CONF_OUTPUT_DIR,
    DEFAULT_CO2_ELECTRICITY_SENSOR,
    DEFAULT_CO2_GAS_SENSOR,
    DEFAULT_CO2_SAVINGS_SENSOR,
    DEFAULT_CO2_WATER_SENSOR,
    DEFAULT_FILENAME_PATTERN,
    DEFAULT_LANGUAGE,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_REPORT_TYPE,
    DOMAIN,
    SUPPORTED_LANGUAGES,
    VALID_REPORT_TYPES,
)

CO2_SENSOR_DEFAULTS: tuple[tuple[str, str], ...] = (
    (CONF_CO2_ELECTRICITY, DEFAULT_CO2_ELECTRICITY_SENSOR),
    (CONF_CO2_GAS, DEFAULT_CO2_GAS_SENSOR),
    (CONF_CO2_WATER, DEFAULT_CO2_WATER_SENSOR),
    (CONF_CO2_SAVINGS, DEFAULT_CO2_SAVINGS_SENSOR),
)

BASE_DEFAULTS: dict[str, Any] = {
    CONF_OUTPUT_DIR: DEFAULT_OUTPUT_DIR,
    CONF_FILENAME_PATTERN: DEFAULT_FILENAME_PATTERN,
    CONF_DEFAULT_REPORT_TYPE: DEFAULT_REPORT_TYPE,
    CONF_LANGUAGE: DEFAULT_LANGUAGE,
}
for option_key, default in CO2_SENSOR_DEFAULTS:
    BASE_DEFAULTS[option_key] = default


def _merge_defaults(existing: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Return config values merged with defaults."""

    merged: dict[str, Any] = dict(BASE_DEFAULTS)
    if existing:
        for key, value in existing.items():
            if value is not None:
                merged[key] = value

    return merged


def _build_schema(defaults: Mapping[str, Any]) -> vol.Schema:
    """Build the voluptuous schema for the flow."""

    schema_dict: dict[Any, Any] = {
        vol.Required(CONF_OUTPUT_DIR, default=defaults[CONF_OUTPUT_DIR]): cv.string,
        vol.Required(CONF_FILENAME_PATTERN, default=defaults[CONF_FILENAME_PATTERN]): cv.string,
        vol.Required(
            CONF_DEFAULT_REPORT_TYPE,
            default=defaults[CONF_DEFAULT_REPORT_TYPE],
        ): vol.In(VALID_REPORT_TYPES),
        vol.Required(CONF_LANGUAGE, default=defaults[CONF_LANGUAGE]): vol.In(
            SUPPORTED_LANGUAGES
        ),
    }

    for option_key, _ in CO2_SENSOR_DEFAULTS:
        schema_dict[vol.Required(option_key, default=defaults[option_key])] = cv.entity_id

    return vol.Schema(schema_dict)


class EnergyPDFReportConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Energy PDF Report."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""

        self._reconfigure_entry: config_entries.ConfigEntry | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""

        if self._reconfigure_entry is None and not user_input:
            existing_entries = self._async_current_entries()
            if existing_entries:
                self._reconfigure_entry = existing_entries[0]
                return await self.async_step_reconfigure()

        if user_input is not None:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title="Energy PDF Report",
                data=user_input,
            )

        defaults = _merge_defaults()

        return self.async_show_form(
            step_id="user",
            data_schema=_build_schema(defaults),
            errors={},
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reconfiguration when an entry already exists."""

        if self._reconfigure_entry is None:
            return await self.async_step_user(user_input)

        entry = self._reconfigure_entry

        if entry.unique_id is None:
            self.hass.config_entries.async_update_entry(entry, unique_id=DOMAIN)

        defaults = _merge_defaults(
            {
                **dict(entry.data),
                **dict(entry.options),
            }
        )

        if user_input is not None:
            self._reconfigure_entry = None
            return self.async_update_reload_and_abort(
                entry,
                data_updates=user_input,
            )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_build_schema(defaults),
            errors={},
        )


class EnergyPDFReportOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for Energy PDF Report."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage Energy PDF Report options."""

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        defaults = _merge_defaults(
            {
                **self.config_entry.data,
                **self.config_entry.options,
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=_build_schema(defaults),
        )


async def async_get_options_flow(config_entry: config_entries.ConfigEntry):
    """Return the options flow handler."""
    return EnergyPDFReportOptionsFlowHandler(config_entry)
