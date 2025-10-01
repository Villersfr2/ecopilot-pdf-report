"""Legacy config flow that delegates to the EcoPilot implementation."""

from __future__ import annotations

from typing import Any

from homeassistant import config_entries

from ..ecopilot_pdf_report.config_flow import (
    EcoPilotPDFReportConfigFlow as EcoPilotConfigFlow,
    EcoPilotPDFReportOptionsFlowHandler,
    FlowResult,
)

DOMAIN = "energy_pdf_report"


class EnergyPDFReportConfigFlow(EcoPilotConfigFlow, domain=DOMAIN):
    """Config flow that keeps the legacy domain available for existing entries."""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Abort new installations but keep legacy entries editable."""
        if not self._async_current_entries():
            return self.async_abort(reason="integration_migrated")
        return await super().async_step_user(user_input)


async def async_get_options_flow(config_entry: config_entries.ConfigEntry):
    """Return the EcoPilot options flow handler for legacy entries."""
    return EcoPilotPDFReportOptionsFlowHandler(config_entry)

