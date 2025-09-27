"""Traductions statiques pour la génération des rapports PDF."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .const import DEFAULT_LANGUAGE


@dataclass(frozen=True)
class ReportTranslations:
    """Regroupe les chaînes localisées utilisées dans le rapport."""

    language: str
    pdf_title: str
    cover_subtitle: str
    cover_period: str
    cover_dashboard: str
    cover_bucket: str
    cover_stats: str
    cover_generated: str
    summary_title: str
    summary_intro: str
    summary_table_title: str
    summary_headers: tuple[str, str, str]
    summary_note_totals: str
    summary_note_negative: str
    detail_title: str
    detail_intro: str
    detail_table_title: str
    detail_headers: tuple[str, str, str, str]
    chart_intro: str
    chart_title: str
    chart_units: str
    co2_section_title: str
    co2_section_intro: str
    co2_table_title: str
    co2_table_headers: tuple[str, str, str]
    co2_emission_label: str
    co2_savings_label: str
    co2_balance_sentence: str
    co2_sensor_labels: Mapping[str, str]
    conclusion_title: str
    conclusion_total: str
    conclusion_dominant: str
    conclusion_hint: str
    footer_path: str
    footer_page: str
    footer_generated: str
    table_empty: str
    bucket_labels: Mapping[str, str]
    period_labels: Mapping[str, str]
    notification_title: str
    notification_line_period: str
    notification_line_dashboard: str
    notification_line_file: str


_TRANSLATIONS: dict[str, ReportTranslations] = {
    "fr": ReportTranslations(
        language="fr",
        pdf_title="Rapport énergie",
        cover_subtitle="Rapport énergie du {start} au {end}",
        cover_period="Période : {period}",
        cover_dashboard="Tableau d'énergie : {dashboard}",
        cover_bucket="Granularité des statistiques : {bucket}",
        cover_stats="Statistiques incluses : {count}",
        cover_generated="Rapport généré le : {timestamp}",
        summary_title="Résumé global",
        summary_intro="Cette section présente les totaux consolidés sur la période analysée.",
        summary_table_title="Synthèse par catégorie",
        summary_headers=("Catégorie", "Total", "Unité"),
        summary_note_totals="Les totaux correspondent à la variation mesurée dans le tableau de bord énergie sur la période sélectionnée.",
        summary_note_negative="Les valeurs négatives indiquent un flux exporté ou une compensation.",
        detail_title="Analyse par catégorie / source",
        detail_intro="Chaque statistique suivie est listée avec sa contribution précise afin de faciliter l'analyse fine par origine ou type de consommation.",
        detail_table_title="Détail des statistiques",
        detail_headers=("Catégorie", "Statistique", "Total", "Unité"),
        chart_intro="La visualisation suivante met en avant la répartition des flux pour chaque catégorie suivie et matérialise l'équilibre production / consommation.",
        chart_title="Répartition par catégorie",
        chart_units="Unités : {unit}",
        co2_section_title="CO₂",
        co2_section_intro="Cette section met en lumière les émissions et économies de CO₂ enregistrées par les différents postes.",
        co2_table_title="Émissions et économies de CO₂",
        co2_table_headers=("Source", "Total (kgCO₂e)", "Impact"),
        co2_emission_label="Émission",
        co2_savings_label="Économie",
        co2_balance_sentence="Émissions totales : {emissions} • Économies : {savings} • Bilan net : {balance}.",
        co2_sensor_labels={
            "co2_electricity": "Électricité",
            "co2_mazout": "Mazout",
            "co2_water": "Eau chaude sanitaire",
            "co2_savings": "Économies / compensation",
        },
        conclusion_title="Conclusion",
        conclusion_total="Le flux net observé sur la période atteint {total}.",
        conclusion_dominant="La catégorie la plus significative est {category} avec {value}.",
        conclusion_hint="Pour approfondir l'évolution temporelle et comparer les périodes, référez-vous au tableau de bord Énergie de Home Assistant.",
        footer_path="Chemin du fichier : {path}",
        footer_page="Page {current} sur {total}",
        footer_generated="Généré le {timestamp}",
        table_empty="Aucune donnée disponible",
        bucket_labels={"hour": "heure", "day": "jour", "month": "mois"},
        period_labels={"day": "jour", "week": "semaine", "month": "mois"},
        notification_title="Rapport énergie",
        notification_line_period="Rapport énergie généré pour la période du {start} au {end}.",
        notification_line_dashboard="Tableau de bord : {dashboard}",
        notification_line_file="Fichier : {path}",
    ),
    "en": ReportTranslations(
        language="en",
        pdf_title="Energy Report",
        cover_subtitle="Energy report from {start} to {end}",
        cover_period="Period: {period}",
        cover_dashboard="Energy dashboard: {dashboard}",
        cover_bucket="Statistics granularity: {bucket}",
        cover_stats="Included statistics: {count}",
        cover_generated="Report generated on: {timestamp}",
        summary_title="Overall summary",
        summary_intro="This section presents the consolidated totals for the analysed period.",
        summary_table_title="Summary by category",
        summary_headers=("Category", "Total", "Unit"),
        summary_note_totals="Totals correspond to the variation measured in the Energy dashboard over the selected period.",
        summary_note_negative="Negative values indicate exported energy or compensation.",
        detail_title="Breakdown by category/source",
        detail_intro="Each tracked statistic is listed with its contribution to help analyse the data by origin or consumption type.",
        detail_table_title="Statistic details",
        detail_headers=("Category", "Statistic", "Total", "Unit"),
        chart_intro="The following chart highlights the distribution of flows per category and illustrates the production versus consumption balance.",
        chart_title="Breakdown by category",
        chart_units="Units: {unit}",
        co2_section_title="CO₂",
        co2_section_intro="This section summarises the CO₂ emissions and savings reported by your sensors.",
        co2_table_title="CO₂ emissions and savings",
        co2_table_headers=("Source", "Total (kgCO₂e)", "Impact"),
        co2_emission_label="Emission",
        co2_savings_label="Saving",
        co2_balance_sentence="Total emissions: {emissions} • Savings: {savings} • Net balance: {balance}.",
        co2_sensor_labels={
            "co2_electricity": "Electricity",
            "co2_mazout": "Heating oil",
            "co2_water": "Domestic hot water",
            "co2_savings": "Savings / offset",
        },
        conclusion_title="Conclusion",
        conclusion_total="The net flow observed over the period is {total}.",
        conclusion_dominant="The most significant category is {category} with {value}.",
        conclusion_hint="For deeper time-based analysis and comparisons, refer to Home Assistant's Energy dashboard.",
        footer_path="File path: {path}",
        footer_page="Page {current} of {total}",
        footer_generated="Generated on {timestamp}",
        table_empty="No data available",
        bucket_labels={"hour": "hour", "day": "day", "month": "month"},
        period_labels={"day": "day", "week": "week", "month": "month"},
        notification_title="Energy report",
        notification_line_period="Energy report generated for {start} to {end}.",
        notification_line_dashboard="Dashboard: {dashboard}",
        notification_line_file="File: {path}",
    ),
    "nl": ReportTranslations(
        language="nl",
        pdf_title="Energiarapport",
        cover_subtitle="Energiarapport van {start} tot {end}",
        cover_period="Periode: {period}",
        cover_dashboard="Energiadashboard: {dashboard}",
        cover_bucket="Granulariteit van statistieken: {bucket}",
        cover_stats="Aantal statistieken: {count}",
        cover_generated="Rapport gegenereerd op: {timestamp}",
        summary_title="Samenvatting",
        summary_intro="Deze sectie toont de totale waarden voor de geanalyseerde periode.",
        summary_table_title="Overzicht per categorie",
        summary_headers=("Categorie", "Totaal", "Eenheid"),
        summary_note_totals="De totalen komen overeen met de verandering die in het Energiadashboard is gemeten tijdens de geselecteerde periode.",
        summary_note_negative="Negatieve waarden geven geëxporteerde energie of compensatie weer.",
        detail_title="Analyse per categorie / bron",
        detail_intro="Elke gevolgde statistiek wordt getoond met zijn bijdrage om een gedetailleerde analyse per oorsprong of verbruikstype te vergemakkelijken.",
        detail_table_title="Statistiekdetails",
        detail_headers=("Categorie", "Statistiek", "Totaal", "Eenheid"),
        chart_intro="De volgende visualisatie toont de verdeling van de stromen per categorie en beeldt het evenwicht tussen productie en verbruik uit.",
        chart_title="Verdeling per categorie",
        chart_units="Eenheden: {unit}",
        co2_section_title="CO₂",
        co2_section_intro="Deze sectie toont de door uw sensoren geregistreerde CO₂-uitstoot en besparingen.",
        co2_table_title="CO₂-uitstoot en besparingen",
        co2_table_headers=("Bron", "Totaal (kgCO₂e)", "Impact"),
        co2_emission_label="Uitstoot",
        co2_savings_label="Besparing",
        co2_balance_sentence="Totale uitstoot: {emissions} • Besparingen: {savings} • Nettoresultaat: {balance}.",
        co2_sensor_labels={
            "co2_electricity": "Elektriciteit",
            "co2_mazout": "Stookolie",
            "co2_water": "Sanitair warm water",
            "co2_savings": "Besparingen / compensatie",
        },
        conclusion_title="Conclusie",
        conclusion_total="De netto stroom over de periode bedraagt {total}.",
        conclusion_dominant="De meest bepalende categorie is {category} met {value}.",
        conclusion_hint="Raadpleeg het Energiadashboard van Home Assistant voor een diepere tijdsanalyse en vergelijkingen.",
        footer_path="Bestandspad: {path}",
        footer_page="Pagina {current} van {total}",
        footer_generated="Gegenereerd op {timestamp}",
        table_empty="Geen gegevens beschikbaar",
        bucket_labels={"hour": "uur", "day": "dag", "month": "maand"},
        period_labels={"day": "dag", "week": "week", "month": "maand"},
        notification_title="Energiarapport",
        notification_line_period="Energiarapport gegenereerd voor {start} tot {end}.",
        notification_line_dashboard="Dashboard: {dashboard}",
        notification_line_file="Bestand: {path}",
    ),
}


def get_report_translations(language: str) -> ReportTranslations:
    """Retourner les traductions associées à la langue demandée."""

    return _TRANSLATIONS.get(language, _TRANSLATIONS[DEFAULT_LANGUAGE])


__all__ = ["ReportTranslations", "get_report_translations"]
