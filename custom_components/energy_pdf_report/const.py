"""Constantes de l'intégration energy_pdf_report."""

from __future__ import annotations

DOMAIN = "energy_pdf_report"
SERVICE_GENERATE_REPORT = "generate"
DEFAULT_PERIOD = "day"
VALID_PERIODS: tuple[str, ...] = ("day", "week", "month")

DEFAULT_REPORT_TYPE = "week"

VALID_REPORT_TYPES = VALID_PERIODS
DEFAULT_OUTPUT_DIR = "www/energy_reports"
DEFAULT_FILENAME_PATTERN = "energy_report_{start}_{end}.pdf"
DEFAULT_LANGUAGE = "fr"
SUPPORTED_LANGUAGES: tuple[str, ...] = ("fr", "nl", "en")

CONF_START_DATE = "start_date"
CONF_END_DATE = "end_date"
CONF_PERIOD = "period"
CONF_OUTPUT_DIR = "output_dir"
CONF_DASHBOARD = "dashboard"
CONF_FILENAME_PATTERN = "filename_pattern"
CONF_DEFAULT_REPORT_TYPE = "default_report_type"

CONF_LANGUAGE = "language"


PDF_TITLE = "Rapport énergie"
