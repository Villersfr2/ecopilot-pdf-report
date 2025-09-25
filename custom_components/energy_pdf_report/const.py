"""Constantes de l'intégration energy_pdf_report."""

from __future__ import annotations

DOMAIN = "energy_pdf_report"
SERVICE_GENERATE_REPORT = "generate"
DEFAULT_PERIOD = "day"
VALID_PERIODS: tuple[str, ...] = ("day", "week", "month")
DEFAULT_OUTPUT_DIR = "www/energy_reports"
DEFAULT_FILENAME_PATTERN = "energy_report_{start}_{end}.pdf"

CONF_START_DATE = "start_date"
CONF_END_DATE = "end_date"
CONF_PERIOD = "period"
CONF_OUTPUT_DIR = "output_dir"
CONF_DASHBOARD = "dashboard"
CONF_FILENAME_PATTERN = "filename_pattern"

PDF_TITLE = "Rapport énergie"
