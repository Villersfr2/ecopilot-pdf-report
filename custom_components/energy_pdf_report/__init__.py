"""Intégration personnalisée pour générer un rapport énergie en PDF."""

from __future__ import annotations

import calendar

import inspect
import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, tzinfo

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

_RECORDER_METADATA_REQUIRES_HASS: bool | None = None

CONF_START_DATE = "start_date"
CONF_END_DATE = "end_date"
CONF_PERIOD = "period"
CONF_OUTPUT_DIR = "output_dir"
CONF_DASHBOARD = "dashboard"

VALID_PERIODS: tuple[str, ...] = ("day", "week", "month")

SERVICE_GENERATE_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_START_DATE): cv.date,
        vol.Optional(CONF_END_DATE): cv.date,
        vol.Optional(CONF_PERIOD, default=DEFAULT_PERIOD): vol.In(VALID_PERIODS),
        vol.Optional(CONF_FILENAME): cv.string,
        vol.Optional(CONF_OUTPUT_DIR, default=DEFAULT_OUTPUT_DIR): cv.string,
        vol.Optional(CONF_DASHBOARD): cv.string,
    }
)


DATA_SERVICES_REGISTERED = "services_registered"
DATA_CONFIG_ENTRY_IDS = "entry_ids"

@dataclass(slots=True)
class MetricDefinition:
    """Représentation d'une statistique à inclure dans le rapport."""

    category: str
    statistic_id: str



@dataclass(slots=True)
class DashboardSelection:
    """Informations sur un tableau de bord énergie sélectionné."""

    identifier: str | None
    name: str | None
    preferences: dict[str, Any]


def _recorder_metadata_requires_hass() -> bool:
    """Déterminer si recorder.get_metadata attend l'instance hass."""

    global _RECORDER_METADATA_REQUIRES_HASS

    if _RECORDER_METADATA_REQUIRES_HASS is None:
        try:
            parameters = inspect.signature(recorder_statistics.get_metadata).parameters
        except (TypeError, ValueError):
            _RECORDER_METADATA_REQUIRES_HASS = True
        else:
            _RECORDER_METADATA_REQUIRES_HASS = "hass" in parameters

    return _RECORDER_METADATA_REQUIRES_HASS


def _set_recorder_metadata_requires_hass(value: bool) -> None:
    """Mettre à jour le cache local de compatibilité recorder."""

    global _RECORDER_METADATA_REQUIRES_HASS
    _RECORDER_METADATA_REQUIRES_HASS = value


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
    """Configurer le service de génération de rapport."""

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


    dashboard_requested: str | None = call.data.get(CONF_DASHBOARD)
    selection = await _async_select_dashboard_preferences(
        hass, manager, dashboard_requested
    )
    preferences = selection.preferences

    start, end, display_start, display_end, bucket = _resolve_period(hass, call.data)
    metrics = _build_metrics(preferences)


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

    dashboard_label = _format_dashboard_label(selection)

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
        dashboard_label,
    )

    message_lines = [
        (
            "Rapport énergie généré pour la période du "
            f"{display_start.date().isoformat()} au {display_end.date().isoformat()}."
        )
    ]

    if dashboard_label:
        message_lines.append(f"Tableau de bord : {dashboard_label}")

    message_lines.append(f"Fichier : {pdf_path}")
    message = "\n".join(message_lines)
    persistent_notification.async_create(
        hass,
        message,
        title="Rapport énergie",
        notification_id=f"{DOMAIN}_last_report",
    )
    if dashboard_label:
        _LOGGER.info("Rapport énergie généré (%s): %s", dashboard_label, pdf_path)
    else:
        _LOGGER.info("Rapport énergie généré: %s", pdf_path)


async def _async_select_dashboard_preferences(
    hass: HomeAssistant, manager: Any, requested_dashboard: str | None
) -> DashboardSelection:
    """Sélectionner les préférences énergie pour le tableau demandé."""

    dashboards = _collect_dashboard_preferences(manager)


    if requested_dashboard:
        normalized = _normalize_dashboard_key(requested_dashboard)

        if normalized is not None:
            for selection in dashboards:
                if _match_dashboard_key(selection, normalized):
                    return selection

        fetched = await _async_fetch_dashboard_preferences_via_methods(
            hass, manager, requested_dashboard
        )
        if fetched:
            return fetched

        raise HomeAssistantError(
            f"Aucun tableau de bord énergie nommé '{requested_dashboard}' n'a été trouvé."
        )

    if dashboards:
        return _pick_default_dashboard(manager, dashboards)

    data = getattr(manager, "data", None)
    if _is_energy_preferences(data):
        return DashboardSelection(None, None, data)

    raise HomeAssistantError(
        "Le tableau de bord énergie n'est pas encore configuré."
    )


def _collect_dashboard_preferences(manager: Any) -> list[DashboardSelection]:
    """Extraire les différents tableaux de bord disponibles."""

    selections: list[DashboardSelection] = []

    selections.extend(_extract_named_preferences(getattr(manager, "data", None)))

    for attr in ("dashboards", "dashboard"):
        if hasattr(manager, attr):
            selections.extend(_extract_named_preferences(getattr(manager, attr)))

    data = getattr(manager, "data", None)
    if isinstance(data, dict):
        for key in ("dashboards", "dashboard"):
            if key in data:
                selections.extend(_extract_named_preferences(data[key]))

    deduped: list[DashboardSelection] = []
    for selection in selections:
        if not _is_energy_preferences(selection.preferences):
            continue

        key = (selection.identifier, selection.name)
        existing_index = next(
            (index for index, current in enumerate(deduped) if (current.identifier, current.name) == key),
            None,
        )

        if existing_index is None:
            deduped.append(selection)
            continue

        current = deduped[existing_index]
        replace = False
        if current.identifier is None and selection.identifier is not None:
            replace = True
        elif current.name is None and selection.name is not None:
            replace = True

        if replace:
            deduped[existing_index] = selection

    return deduped


def _extract_named_preferences(
    candidate: Any, fallback_id: str | None = None, fallback_name: str | None = None
) -> list[DashboardSelection]:
    """Parcourir récursivement une structure pour trouver des préférences énergie."""

    selections: list[DashboardSelection] = []

    def _add(preferences: Any, identifier: str | None, name: str | None) -> None:
        if _is_energy_preferences(preferences):
            selections.append(
                DashboardSelection(
                    identifier if identifier else fallback_id,
                    name if name else fallback_name,
                    preferences,
                )
            )

    if candidate is None:
        return selections

    if _is_energy_preferences(candidate):
        _add(candidate, fallback_id, fallback_name)
        return selections

    if isinstance(candidate, dict):
        current_id = fallback_id
        for key in ("dashboard_id", "id", "slug", "key"):
            if key in candidate and candidate[key] is not None:
                value = candidate[key]
                current_id = str(value)
                break

        current_name = fallback_name
        for key in ("name", "title", "label"):
            value = candidate.get(key)
            if isinstance(value, str) and value.strip():
                current_name = value
                break

        if "preferences" in candidate:
            selections.extend(
                _extract_named_preferences(candidate["preferences"], current_id, current_name)
            )
        if "dashboards" in candidate:
            selections.extend(
                _extract_named_preferences(candidate["dashboards"], current_id, current_name)
            )
        if "dashboard" in candidate:
            selections.extend(
                _extract_named_preferences(candidate["dashboard"], current_id, current_name)
            )

        for key, value in candidate.items():
            if key in {"preferences", "dashboards", "dashboard", "energy_sources", "device_consumption"}:
                continue
            if isinstance(value, (dict, list)):
                next_id = current_id
                if isinstance(key, str) and key not in {"name", "title", "label"}:
                    next_id = key
                selections.extend(_extract_named_preferences(value, next_id, current_name))

        return selections

    if isinstance(candidate, list):
        for item in candidate:
            selections.extend(_extract_named_preferences(item, fallback_id, fallback_name))
        return selections

    for attr in ("preferences", "data"):
        if hasattr(candidate, attr):
            sub_candidate = getattr(candidate, attr)
            current_id = fallback_id
            for attr_key in ("dashboard_id", "id", "slug", "key"):
                if hasattr(candidate, attr_key):
                    value = getattr(candidate, attr_key)
                    if value is not None:
                        current_id = str(value)
                        break

            current_name = fallback_name
            for attr_name in ("name", "title", "label"):
                if hasattr(candidate, attr_name):
                    value = getattr(candidate, attr_name)
                    if isinstance(value, str) and value.strip():
                        current_name = value
                        break

            selections.extend(
                _extract_named_preferences(sub_candidate, current_id, current_name)
            )
            break

    return selections


def _is_energy_preferences(candidate: Any) -> bool:
    """Vérifier qu'une structure correspond aux préférences énergie attendues."""

    return (
        isinstance(candidate, dict)
        and "energy_sources" in candidate
        and "device_consumption" in candidate
    )


def _normalize_dashboard_key(value: str | None) -> str | None:
    """Normaliser un identifiant de tableau de bord pour comparaison."""

    if value is None:
        return None

    normalized = str(value).strip()
    if not normalized:
        return None

    return normalized.casefold()


def _match_dashboard_key(selection: DashboardSelection, requested: str) -> bool:
    """Comparer un tableau de bord à une clé normalisée."""

    for candidate in (selection.identifier, selection.name):
        normalized = _normalize_dashboard_key(candidate)
        if normalized and normalized == requested:
            return True

    return False


def _pick_default_dashboard(
    manager: Any, dashboards: list[DashboardSelection]
) -> DashboardSelection:
    """Choisir un tableau par défaut parmi ceux disponibles."""

    def _find_match(value: Any) -> DashboardSelection | None:
        normalized = _normalize_dashboard_key(value if value is None else str(value))
        if not normalized:
            return None
        for item in dashboards:
            if _match_dashboard_key(item, normalized):
                return item
        return None

    data = getattr(manager, "data", None)
    if isinstance(data, dict):
        for key in ("selected_dashboard", "default_dashboard", "active_dashboard"):
            selection = _find_match(data.get(key))
            if selection:
                return selection

    for attr in ("selected_dashboard", "default_dashboard", "active_dashboard"):
        if hasattr(manager, attr):
            selection = _find_match(getattr(manager, attr))
            if selection:
                return selection

    return dashboards[0]


async def _async_fetch_dashboard_preferences_via_methods(
    hass: HomeAssistant, manager: Any, dashboard_id: str
) -> DashboardSelection | None:
    """Tenter de récupérer les préférences via les méthodes du gestionnaire."""

    method_names = (
        "async_get_dashboard",
        "async_get_dashboard_preferences",
        "async_get_dashboard_by_id",
        "async_get_dashboard_by_slug",
        "get_dashboard",
    )

    for name in method_names:
        method = getattr(manager, name, None)
        if not callable(method):
            continue

        for args in ((dashboard_id,), (hass, dashboard_id)):
            try:
                result = method(*args)
            except TypeError:
                continue
            except Exception as err:  # pragma: no cover - best effort logging
                _LOGGER.debug(
                    "Erreur lors de l'appel de %s pour récupérer le tableau '%s': %s",
                    name,
                    dashboard_id,
                    err,
                )
                continue

            result = await _await_if_needed(result)


            selections = _extract_named_preferences(result, dashboard_id)
            if selections:
                requested = _normalize_dashboard_key(dashboard_id)
                if requested:
                    for selection in selections:
                        if _match_dashboard_key(selection, requested):
                            if selection.identifier is None:
                                return DashboardSelection(
                                    dashboard_id, selection.name, selection.preferences
                                )
                            return selection

                primary = selections[0]
                if primary.identifier is None:
                    return DashboardSelection(dashboard_id, primary.name, primary.preferences)
                return primary

            if _is_energy_preferences(result):
                return DashboardSelection(dashboard_id, None, result)

    return None


async def _await_if_needed(result: Any) -> Any:
    """Attendre une valeur si elle est awaitable."""

    if inspect.isawaitable(result):
        return await result
    return result


def _format_dashboard_label(selection: DashboardSelection) -> str | None:
    """Créer une étiquette lisible pour le tableau sélectionné."""

    name = selection.name
    identifier = selection.identifier

    if name and identifier:
        if _normalize_dashboard_key(name) == _normalize_dashboard_key(identifier):
            return name
        return f"{name} ({identifier})"

    return name or identifier


            selections = _extract_named_preferences(result, dashboard_id)
            if selections:
                requested = _normalize_dashboard_key(dashboard_id)
                if requested:
                    for selection in selections:
                        if _match_dashboard_key(selection, requested):
                            if selection.identifier is None:
                                return DashboardSelection(
                                    dashboard_id, selection.name, selection.preferences
                                )
                            return selection


def _resolve_period(
    hass: HomeAssistant, call_data: dict[str, Any]
) -> tuple[datetime, datetime, datetime, datetime, str]:
    """Calculer les dates de début et fin en tenant compte de la granularité."""

    period: str = call_data.get(CONF_PERIOD, DEFAULT_PERIOD)
    start_date = _coerce_service_date(call_data.get(CONF_START_DATE), CONF_START_DATE)
    end_date = _coerce_service_date(call_data.get(CONF_END_DATE), CONF_END_DATE)

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

    timezone = _select_timezone(hass)

    start_local = _localize_date(start_date, timezone)

    # ``end_date`` reste inclusif comme dans le tableau de bord Énergie ;
    # recorder se charge ensuite de convertir ce point de sortie en borne exclusive.
    end_local = _localize_date(end_date, timezone)
    end_local_exclusive = end_local + timedelta(days=1)


    start_utc = dt_util.as_utc(start_local)
    end_utc = dt_util.as_utc(end_local)
    display_end = end_local_exclusive - timedelta(seconds=1)


    return (
        start_utc,
        end_utc,
        start_local,
        display_end,
        _select_bucket(period, start_local, end_local_exclusive),
    )



def _coerce_service_date(value: Any, field: str) -> date | None:
    """Convertir une valeur issue du service en date."""

    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if isinstance(value, str):
        parsed = dt_util.parse_date(value)
        if parsed is not None:
            return parsed

    raise HomeAssistantError(
        f"Impossible d'interpréter {field} comme une date valide (format attendu YYYY-MM-DD)."
    )


def _select_timezone(hass: HomeAssistant) -> tzinfo:
    """Déterminer le fuseau horaire à utiliser pour les conversions locales."""

    if hass.config.time_zone:
        timezone = dt_util.get_time_zone(hass.config.time_zone)
        if timezone is not None:
            return timezone

    return dt_util.DEFAULT_TIME_ZONE


def _select_bucket(period: str, start_local: datetime, end_local_exclusive: datetime) -> str:
    """Choisir une granularité compatible avec recorder pour la période demandée."""

    normalized = period.lower() if isinstance(period, str) else ""

    if normalized == "day":
        return "hour"

    if normalized == "week":
        return "day"

    if normalized == "month":
        return "day"

    span = end_local_exclusive - start_local

    if span <= timedelta(days=2):
        return "hour"

    if span <= timedelta(days=35):
        return "day"

    return "month"


def _localize_date(day: date, timezone: tzinfo) -> datetime:
    """Assembler une date locale en tenant compte des transitions horaires."""

    naive = datetime.combine(day, time.min)
    localize = getattr(timezone, "localize", None)
    if callable(localize):  # pytz support
        return localize(naive)
    return naive.replace(tzinfo=timezone)



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

    metadata_requires_hass = _recorder_metadata_requires_hass()
    metadata: dict[str, tuple[int, StatisticMetaData]]

    try:
        if metadata_requires_hass:
            metadata = await instance.async_add_executor_job(
                _get_recorder_metadata_with_hass,
                hass,
                statistic_ids,
            )
        else:
            metadata = await instance.async_add_executor_job(
                recorder_statistics.get_metadata,
                statistic_ids,
            )
    except TypeError as err:
        err_message = str(err)

        if metadata_requires_hass and _metadata_error_indicates_legacy_signature(err_message):
            _LOGGER.debug(
                "Recorder get_metadata ne supporte pas hass en argument, bascule sur la signature héritée: %s",
                err_message,
            )
            _set_recorder_metadata_requires_hass(False)
            metadata = await instance.async_add_executor_job(
                recorder_statistics.get_metadata,
                statistic_ids,
            )
        elif (
            not metadata_requires_hass
            and _metadata_error_indicates_requires_hass(err_message)
        ):
            _LOGGER.debug(
                "Recorder get_metadata nécessite hass, nouvelle tentative avec la signature actuelle: %s",
                err_message,
            )
            _set_recorder_metadata_requires_hass(True)
            metadata = await instance.async_add_executor_job(
                _get_recorder_metadata_with_hass,
                hass,
                statistic_ids,
            )
        else:
            raise


    stats_map = await instance.async_add_executor_job(
        recorder_statistics.statistics_during_period,
        hass,
        start,
        end,
        statistic_ids,
        bucket,
        None,
        {"change"},
    )

    return stats_map, metadata


def _get_recorder_metadata_with_hass(
    hass: HomeAssistant,
    statistic_ids: set[str],
) -> dict[str, tuple[int, StatisticMetaData]]:
    """Appeler get_metadata avec hass en argument mot-clé."""

    return recorder_statistics.get_metadata(hass, statistic_ids=statistic_ids)


def _metadata_error_indicates_legacy_signature(message: str) -> bool:
    """Détecter les erreurs indiquant l'ancienne signature de get_metadata."""

    lowered = message.lower()
    return any(
        hint in lowered
        for hint in (
            "multiple values",
            "positional argument",
            "unexpected keyword",
        )
    )


def _metadata_error_indicates_requires_hass(message: str) -> bool:
    """Détecter les erreurs montrant que hass est requis."""

    lowered = message.lower()
    return any(
        hint in lowered
        for hint in (
            "missing 1 required positional argument",
            "unhashable type",
            "homeassistant",
        )
    )


def _calculate_totals(
    metrics: Iterable[MetricDefinition],
    stats: dict[str, list[StatisticsRow]],
) -> dict[str, float]:
    """Additionner les valeurs sur la période pour chaque statistique."""

    totals: dict[str, float] = {metric.statistic_id: 0.0 for metric in metrics}

    for statistic_id, rows in stats.items():
        if not rows:
            continue


        change_total = 0.0
        has_change = False

        for row in rows:

            change_value = row.get("change")
            if change_value is None:
                continue
            has_change = True
            change_total += float(change_value)

        if has_change:
            totals[statistic_id] = change_total


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
    dashboard_label: str | None,
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
    if dashboard_label:
        builder.add_paragraph(f"Tableau d'énergie : {dashboard_label}", bold=True)
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
        "Les totaux représentent la variation relevée dans le tableau de bord"
        " énergie sur la période sélectionnée."
    )
    builder.add_paragraph(
        "Les valeurs négatives indiquent un flux exporté ou une compensation."
    )
    builder.add_paragraph(
        (
            "Statistiques incluses selon la configuration du tableau de bord énergie : "
            f"{len(metrics)}"
        )
    )

    summary_rows = _prepare_summary_rows(metrics, totals, metadata)
    summary_widths = builder.compute_column_widths((0.6, 0.25, 0.15))
    builder.add_table(
        TableConfig(
            title="Synthèse par catégorie",
            headers=("Catégorie", "Total", "Unité"),
            rows=summary_rows,
            column_widths=summary_widths,
        )
    )

    detail_rows = _prepare_detail_rows(metrics, totals, metadata)
    detail_widths = builder.compute_column_widths((0.26, 0.45, 0.17, 0.12))
    builder.add_table(
        TableConfig(
            title="Détail des statistiques",
            headers=("Catégorie", "Statistique", "Total", "Unité"),
            rows=detail_rows,
            column_widths=detail_widths,
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

