"""Legacy compatibility shim for the Energy PDF Report domain."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from ..ecopilot_pdf_report import (
    async_setup as ecopilot_async_setup,
    async_setup_entry as ecopilot_async_setup_entry,
    async_unload_entry as ecopilot_async_unload_entry,
)
from ..ecopilot_pdf_report.const import DOMAIN as ECOPILOT_DOMAIN

DOMAIN = "energy_pdf_report"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the legacy integration by delegating to the EcoPilot implementation."""
    return await ecopilot_async_setup(hass, config)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Load a legacy config entry using the EcoPilot implementation."""
    if entry.domain == DOMAIN and entry.unique_id is None:
        hass.config_entries.async_update_entry(entry, unique_id=ECOPILOT_DOMAIN)
    return await ecopilot_async_setup_entry(hass, entry)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a legacy config entry using the EcoPilot implementation."""
    return await ecopilot_async_unload_entry(hass, entry)
