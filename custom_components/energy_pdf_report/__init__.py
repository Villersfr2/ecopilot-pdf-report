"""Intégration personnalisée pour générer un rapport énergie en PDF."""

from __future__ import annotations

import calendar
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
import logging
from pathlib import Path
from typing import Any, Iterable, TYPE_CHECKING

import voluptuous as vol

from homeassistant.components import persistent_notification, recorder
from homeassistant.components.recorder import statistics as recorder_statistics
from homeassistant.components.recorder.models.statistics import StatisticMetaData
from homeassistant.components.recorder.statistics import StatisticsRow
from homeassistant.const import CONF_FILENAME
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util

from homeassistant.components.energy.data import async_get_manager

from .const import (
    DEFAULT_OUTPUT_DIR,
    DEFAULT_PERIOD,
    DOMAIN,
    PDF_TITLE,
    SERVICE_GENERATE_REPORT,
)
from .pdf import EnergyPDFBuilder, TableConfig

if TYPE_CHECKING:
    from homeassistant.components.energy.data import EnergyPreferences

_LOGGER = logging.getLogger(__name__)

CONF_START_DATE = "start_date"
CONF_END_DATE = "end_date"
CONF_PERIOD = "period"
CONF_OUTPUT_DIR = "output_dir"

VALID_PERIODS: tuple[str, ...] = ("day", "week", "month")

SERVICE_GENERATE_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_START_DATE): cv.date,
        vol.Optional(CONF_END_DATE): cv.date,
        vol.Optional(CONF_PERIOD, default=DEFAULT_PERIOD): vol.In(VALID_PERIODS),
        vol.Optional(CONF_FILENAME): cv.string,
        vol.Optional(CONF_OUTPUT_DIR, default=DEFAULT_OUTPUT_DIR): cv.string,
    }
)


DATA_SERVICES_REGISTERED = "services_registered"
DATA_CONFIG_ENTRY_IDS = "entry_ids"


@dataclass(slots=True)
class MetricDefinition:
    """Représentation d'une statistique à inclure dans le rapport."""

    category: str
    statistic_id: str


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Initialiser les structures de données du domaine."""

    hass.data.setdefault(DOMAIN, {})
    domain_data = hass.data[DOMAIN]
    domain_data.setdefault(DATA_CONFIG_ENTRY_IDS, set())

    if DOMAIN in config:
        _async_register_services(hass)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configurer une entrée de configuration."""

    domain_data = hass.data.setdefault(DOMAIN, {})
    entry_ids: set[str] = domain_data.setdefault(DATA_CONFIG_ENTRY_IDS, set())
    entry_ids.add(entry.entry_id)

    _async_register_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Décharger l'intégration lors de la suppression de l'entrée."""

    domain_data = hass.data.get(DOMAIN)
    if not domain_data:
        return True

    entry_ids: set[str] = domain_data.setdefault(DATA_CONFIG_ENTRY_IDS, set())
    entry_ids.discard(entry.entry_id)

    if not entry_ids:
        hass.services.async_remove(DOMAIN, SERVICE_GENERATE_REPORT)
        domain_data.pop(DATA_SERVICES_REGISTERED, None)
        hass.data.pop(DOMAIN, None)

    return True


def _async_register_services(hass: HomeAssistant) -> None:
    """Enregistrer les services si nécessaire."""

    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get(DATA_SERVICES_REGISTERED):
        return

    domain_data[DATA_SERVICES_REGISTERED] = True

    async def _async_generate(call: ServiceCall) -> None:
        await _async_handle_generate(hass, call)

    hass.services.async_register(
        DOMAIN,
        SERVICE_GENERATE_REPORT,
        _async_generate,
        schema=SERVICE_GENERATE_SCHEMA,
    )


async def _async_handle_generate(hass: HomeAssistant, call: ServiceCall) -> None:
    """Exécuter la génération d'un rapport PDF."""

    manager = await async_get_manager(hass)
    if not manager.data:
        raise HomeAssistantError(
            "Le tableau de bord énergie n'est pas encore configuré."
        )

    start, end, display_start, display_end, bucket = _resolve_period(call.data)
    metrics = _build_metrics(manager.data)

    if not metrics:
        raise HomeAssistantError(
            "Aucune statistique n'a été trouvée dans les préférences énergie."
        )

    stats_map, metadata = await _collect_statistics(hass, metrics, start, end, bucket)
    totals = _calculate_totals(metrics, stats_map)

    output_dir_input = call.data.get(CONF_OUTPUT_DIR, DEFAULT_OUTPUT_DIR)
    output_dir = Path(output_dir_input)
    if not output_dir.is_absolute():
        output_dir = Path(hass.config.path(output_dir_input))

    filename: str | None = call.data.get(CONF_FILENAME)
    generated_at = dt_util.now()

    pdf_path = await hass.async_add_executor_job(
        _build_pdf,
        metrics,
        totals,
        metadata,
        display_start,
        display_end,
        bucket,
        output_dir,
        filename,
        generated_at,
    )

    message = (
        "Rapport énergie généré pour la période du "
        f"{display_start.date().isoformat()} au {display_end.date().isoformat()}.\n"
        f"Fichier : {pdf_path}"
    )
    persistent_notification.async_create(
        hass,
        message,
        title="Rapport énergie",
        notification_id=f"{DOMAIN}_last_report",
    )
    _LOGGER.info("Rapport énergie généré: %s", pdf_path)


def _resolve_period(call_data: dict[str, Any]) -> tuple[datetime, datetime, datetime, datetime, str]:
    """Calculer les dates de début et fin en tenant compte de la granularité."""

    period: str = call_data.get(CONF_PERIOD, DEFAULT_PERIOD)
    start_date: date | None = call_data.get(CONF_START_DATE)
    end_date: date | None = call_data.get(CONF_END_DATE)

    now_local = dt_util.now()

    if start_date is None:
        if period == "day":
            start_date = now_local.date()
        elif period == "week":
            start_date = (now_local - timedelta(days=now_local.weekday())).date()
        elif period == "month":
            start_date = now_local.replace(day=1).date()
        else:
            raise HomeAssistantError("Période non supportée")

    if end_date is None:
        if period == "day":
            end_date = start_date
        elif period == "week":
            end_date = start_date + timedelta(days=6)
        elif period == "month":
            _, last_day = calendar.monthrange(start_date.year, start_date.month)
            end_date = start_date.replace(day=last_day)
    if end_date is None:
        end_date = start_date

    if end_date < start_date:
        raise HomeAssistantError("La date de fin doit être postérieure à la date de début.")

    start_local = datetime.combine(start_date, time.min, tzinfo=dt_util.DEFAULT_TIME_ZONE)
    # on travaille avec une fin exclusive (lendemain à 00:00)
    end_local_exclusive = datetime.combine(
        end_date + timedelta(days=1), time.min, tzinfo=dt_util.DEFAULT_TIME_ZONE
    )

    start_utc = dt_util.as_utc(start_local)
    end_utc = dt_util.as_utc(end_local_exclusive)
    display_end = end_local_exclusive - timedelta(seconds=1)

    return start_utc, end_utc, start_local, display_end, period


def _build_metrics(preferences: "EnergyPreferences" | dict[str, Any]) -> list[MetricDefinition]:
    """Lister les statistiques à inclure dans le rapport."""

    metrics: list[MetricDefinition] = []
    seen: set[str] = set()

    def _add(statistic_id: str | None, category: str) -> None:
        if not statistic_id or statistic_id in seen:
            return
        seen.add(statistic_id)
        metrics.append(MetricDefinition(category, statistic_id))

    for source in preferences.get("energy_sources", []):
        source_type = source.get("type")
        if source_type == "grid":
            for flow in source.get("flow_from", []):
                _add(flow.get("stat_energy_from"), "Import réseau")
                _add(flow.get("stat_cost"), "Coût réseau")
            for flow in source.get("flow_to", []):
                _add(flow.get("stat_energy_to"), "Export réseau")
                _add(flow.get("stat_compensation"), "Compensation réseau")
        elif source_type == "solar":
            _add(source.get("stat_energy_from"), "Production solaire")
        elif source_type == "battery":
            _add(source.get("stat_energy_from"), "Décharge batterie")
            _add(source.get("stat_energy_to"), "Charge batterie")
        elif source_type == "gas":
            _add(source.get("stat_energy_from"), "Consommation gaz")
            _add(source.get("stat_cost"), "Coût gaz")
        elif source_type == "water":
            _add(source.get("stat_energy_from"), "Consommation eau")
            _add(source.get("stat_cost"), "Coût eau")

    for device in preferences.get("device_consumption", []):
        _add(device.get("stat_consumption"), "Consommation appareils")

    return metrics


async def _collect_statistics(
    hass: HomeAssistant,
    metrics: Iterable[MetricDefinition],
    start: datetime,
    end: datetime,
    bucket: str,
) -> tuple[dict[str, list[StatisticsRow]], dict[str, tuple[int, StatisticMetaData]]]:
    """Récupérer les statistiques depuis recorder."""

    statistic_ids = {metric.statistic_id for metric in metrics}
    if not statistic_ids:
        return {}, {}

    try:
        instance = recorder.get_instance(hass)
    except RuntimeError as err:
        raise HomeAssistantError(
            "Le composant recorder doit être actif pour générer le rapport."
        ) from err

    metadata = await instance.async_add_executor_job(
        recorder_statistics.get_metadata,
        hass,
        statistic_ids=statistic_ids,
    )

    stats_map = await instance.async_add_executor_job(
        recorder_statistics.statistics_during_period,
        hass,
        start,
        end,
        statistic_ids,
        bucket,
        None,
        {"sum", "change"},
    )

    return stats_map, metadata


def _calculate_totals(
    metrics: Iterable[MetricDefinition],
    stats: dict[str, list[StatisticsRow]],
) -> dict[str, float]:
    """Additionner les valeurs sur la période pour chaque statistique."""

    totals: dict[str, float] = {metric.statistic_id: 0.0 for metric in metrics}

    for statistic_id, rows in stats.items():
        total = 0.0
        for row in rows:
            value = row.get("change")
            if value is None:
                value = row.get("sum")
            if value is None:
                continue
            total += float(value)
        totals[statistic_id] = total

    return totals


def _build_pdf(
    metrics: list[MetricDefinition],
    totals: dict[str, float],
    metadata: dict[str, tuple[int, StatisticMetaData]],
    display_start: datetime,
    display_end: datetime,
    bucket: str,
    output_dir: Path,
    filename: str | None,
    generated_at: datetime,
) -> str:
    """Assembler le PDF et le sauvegarder sur disque."""

    output_dir.mkdir(parents=True, exist_ok=True)

    if not filename:
        filename = (
            f"energy_report_{display_start.date().isoformat()}_"
            f"{display_end.date().isoformat()}.pdf"
        )
    elif not filename.lower().endswith(".pdf"):
        filename = f"{filename}.pdf"

    file_path = output_dir / filename

    builder = EnergyPDFBuilder(PDF_TITLE)
    builder.add_paragraph(
        (
            "Période analysée : "
            f"{display_start.strftime('%d/%m/%Y')} → {display_end.strftime('%d/%m/%Y')}"
        ),
        bold=True,
    )
    builder.add_paragraph(f"Granularité des statistiques : {bucket}")
    builder.add_paragraph(
        f"Rapport généré le : {generated_at.strftime('%d/%m/%Y %H:%M')}"
    )
    builder.add_paragraph(
        "Les totaux correspondent à la somme des données issues du tableau de bord"
        " énergie pour la période sélectionnée."
    )
    builder.add_paragraph(
        "Les valeurs négatives indiquent un flux exporté ou une compensation."
    )
    builder.add_paragraph(
        f"Nombre de statistiques utilisées : {len(metrics)}"
    )

    summary_rows = _prepare_summary_rows(metrics, totals, metadata)
    builder.add_table(
        TableConfig(
            title="Synthèse par catégorie",
            headers=("Catégorie", "Total", "Unité"),
            rows=summary_rows,
        )
    )

    detail_rows = _prepare_detail_rows(metrics, totals, metadata)
    builder.add_table(
        TableConfig(
            title="Détail des statistiques",
            headers=("Catégorie", "Statistique", "Total", "Unité"),
            rows=detail_rows,
        )
    )

    builder.add_footer(f"Chemin du fichier : {file_path}")
    builder.output(str(file_path))

    return str(file_path)


def _prepare_summary_rows(
    metrics: Iterable[MetricDefinition],
    totals: dict[str, float],
    metadata: dict[str, tuple[int, StatisticMetaData]],
) -> list[tuple[str, str, str]]:
    """Préparer les lignes du tableau de synthèse."""

    summary: dict[tuple[str, str], float] = defaultdict(float)

    for metric in metrics:
        total = totals.get(metric.statistic_id)
        if total is None:
            continue
        unit = _extract_unit(metadata.get(metric.statistic_id))
        key = (metric.category, unit)
        summary[key] += total

    rows: list[tuple[str, str, str]] = []
    for (category, unit), value in sorted(
        summary.items(), key=lambda item: (-abs(item[1]), item[0])
    ):
        if abs(value) < 1e-6:
            continue
        rows.append((category, _format_number(value), unit))

    return rows


def _prepare_detail_rows(
    metrics: Iterable[MetricDefinition],
    totals: dict[str, float],
    metadata: dict[str, tuple[int, StatisticMetaData]],
) -> list[tuple[str, str, str, str]]:
    """Préparer les lignes détaillées du rapport."""

    details: list[tuple[str, str, float, str]] = []
    for metric in metrics:
        total = totals.get(metric.statistic_id, 0.0)
        meta_entry = metadata.get(metric.statistic_id)
        name = _extract_name(meta_entry, metric.statistic_id)
        unit = _extract_unit(meta_entry)
        details.append((metric.category, name, total, unit))

    details.sort(key=lambda item: (item[0], -abs(item[2]), item[1]))

    rows: list[tuple[str, str, str, str]] = []
    for category, name, value, unit in details:
        rows.append((category, name, _format_number(value), unit))

    return rows


def _extract_unit(metadata: tuple[int, StatisticMetaData] | None) -> str:
    """Récupérer l'unité depuis les métadonnées."""

    if metadata and metadata[1].get("unit_of_measurement"):
        return str(metadata[1]["unit_of_measurement"])
    return ""


def _extract_name(
    metadata: tuple[int, StatisticMetaData] | None, fallback: str
) -> str:
    """Récupérer le nom lisible d'une statistique."""

    if metadata and metadata[1].get("name"):
        return str(metadata[1]["name"])
    return fallback


def _format_number(value: float) -> str:
    """Formater une valeur numérique de manière lisible."""

    if abs(value) < 0.0005:
        value = 0.0

    if abs(value) >= 1000:
        formatted = f"{value:,.0f}"
    elif abs(value) >= 10:
        formatted = f"{value:,.1f}"
    else:
        formatted = f"{value:,.3f}"

    return formatted.replace(",", " ")


__all__ = ["async_setup", "async_setup_entry", "async_unload_entry"]
