"""Flux de configuration pour l'intégration Energy PDF Report."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries

from .const import DOMAIN


class EnergyPDFReportConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Gérer le flux de configuration."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Gérer l'étape initiale lancée par l'utilisateur."""

        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(title="Rapport PDF Énergie", data={})

        return self.async_show_form(step_id="user", data_schema=vol.Schema({}))

    async def async_step_import(
        self, user_input: dict[str, Any]
    ) -> config_entries.ConfigFlowResult:
        """Gérer une importation depuis YAML."""

        return await self.async_step_user(user_input)


class EnergyPDFReportOptionsFlowHandler(config_entries.OptionsFlow):
    """Gérer le flux d'options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialiser la classe."""

        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Gérer l'étape initiale du flux d'options."""

        if user_input is not None:
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({}),
        )


async def async_get_options_flow(
    config_entry: config_entries.ConfigEntry,
) -> EnergyPDFReportOptionsFlowHandler:
    """Obtenir le gestionnaire du flux d'options."""

    return EnergyPDFReportOptionsFlowHandler(config_entry)
