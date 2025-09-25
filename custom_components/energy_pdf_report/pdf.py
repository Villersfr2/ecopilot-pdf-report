"""Génération de rapports PDF pour l'intégration energy_pdf_report."""

from __future__ import annotations

import base64
import zlib
from dataclasses import dataclass

from pathlib import Path
from tempfile import TemporaryDirectory

from typing import Iterable, Sequence

from fpdf import FPDF

from .font_data import FONT_DATA


FONT_FAMILY = "DejaVuSans"
_FONT_FILES: dict[str, str] = {
    "": "DejaVuSans.ttf",
    "B": "DejaVuSans-Bold.ttf",
}


def _decode_font(encoded: str) -> bytes:
    """Décoder un flux de police compressé en bytes TTF."""

    return zlib.decompress(base64.b64decode(encoded))


class _TemporaryFontCache:
    """Stockage temporaire des polices nécessaires à FPDF."""

    def __init__(self) -> None:
        self._tempdir = TemporaryDirectory(prefix="energy_pdf_report_fonts_")
        self.directory = Path(self._tempdir.name)
        self._populate()

    def _populate(self) -> None:
        for filename, encoded in FONT_DATA.items():
            (self.directory / filename).write_bytes(_decode_font(encoded))

    def cleanup(self) -> None:
        self._tempdir.cleanup()


def _register_unicode_fonts(pdf: FPDF) -> _TemporaryFontCache | None:
    """Enregistrer les polices Unicode sur le PDF et retourner le cache."""

    missing_styles = [
        style for style in _FONT_FILES if f"{FONT_FAMILY.lower()}{style}" not in pdf.fonts
    ]

    if not missing_styles:
        return None

    cache = _TemporaryFontCache()

    for style, filename in _FONT_FILES.items():
        font_key = f"{FONT_FAMILY.lower()}{style}"
        if font_key in pdf.fonts:
            continue

        pdf.add_font(FONT_FAMILY, style, str(cache.directory / filename), uni=True)

    return cache



@dataclass(slots=True)
class TableConfig:
    """Configuration d'un tableau à insérer dans le PDF."""

    title: str
    headers: Sequence[str]
    rows: Iterable[Sequence[str]]
    column_widths: Sequence[float] | None = None


class EnergyPDFBuilder:
    """Constructeur simplifié de rapports PDF."""

    def __init__(self, title: str) -> None:
        """Initialiser le générateur de PDF."""
        self._font_cache = _TemporaryFontCache()
        self._pdf = FPDF()
        self._pdf.set_auto_page_break(auto=True, margin=15)
        self._pdf.add_page()

        self._font_cache = _register_unicode_fonts(self._pdf)

        self._pdf.set_title(title)
        self._pdf.set_creator("Home Assistant")
        self._pdf.set_author("energy_pdf_report")
        self._pdf.set_font(FONT_FAMILY, "B", 16)
        self._pdf.cell(0, 10, title, ln=True)
        self._pdf.ln(2)

    @property
    def _available_width(self) -> float:
        """Retourner la largeur disponible pour le contenu."""
        return self._pdf.w - self._pdf.l_margin - self._pdf.r_margin

    def add_paragraph(self, text: str, bold: bool = False, size: int = 11) -> None:
        """Ajouter un paragraphe simple."""
        font_style = "B" if bold else ""
        self._pdf.set_font(FONT_FAMILY, font_style, size)
        self._ensure_space(6)
        self._pdf.multi_cell(0, 6, text)
        self._pdf.ln(1)

    def compute_column_widths(self, weights: Sequence[float]) -> list[float]:
        """Convertir des poids relatifs en largeurs exploitables par FPDF."""

        if not weights:
            raise ValueError("Les poids de colonne ne peuvent pas être vides")

        total_weight = sum(weights)
        if total_weight <= 0:
            raise ValueError("Les poids de colonne doivent avoir une somme positive")

        available = self._available_width
        return [(weight / total_weight) * available for weight in weights]

    def add_table(self, config: TableConfig) -> None:
        """Ajouter un tableau structuré."""
        headers = list(config.headers)
        rows = list(config.rows)
        if not headers:
            return

        if config.column_widths is not None:
            column_widths = list(config.column_widths)
        else:
            column_widths = [self._available_width / len(headers)] * len(headers)

        header_height = 7
        row_height = 6

        self._pdf.set_font(FONT_FAMILY, "B", 12)
        self._ensure_space(header_height + 4)
        self._pdf.cell(0, 8, config.title, ln=True)

        self._pdf.set_font(FONT_FAMILY, "B", 10)
        self._draw_row(headers, column_widths, header_height)

        self._pdf.set_font(FONT_FAMILY, "", 10)
        if not rows:
            empty_row = ["Aucune donnée disponible"] + [""] * (len(headers) - 1)
            self._draw_row(empty_row, column_widths, row_height)
            return

        for row in rows:
            str_row = ["" if value is None else str(value) for value in row]
            self._draw_row(str_row, column_widths, row_height)

        self._pdf.ln(1)

    def add_footer(self, text: str) -> None:
        """Ajouter un texte de bas de page léger."""
        self._pdf.set_font(FONT_FAMILY, "", 9)
        self._ensure_space(5)
        self._pdf.multi_cell(0, 5, text)

    def output(self, path: str) -> None:
        """Sauvegarder le PDF."""
        try:
            self._pdf.output(path)
        finally:
            self._cleanup_fonts()

    def _cleanup_fonts(self) -> None:
        """Nettoyer le répertoire temporaire de polices."""

        cache = getattr(self, "_font_cache", None)
        if cache is not None:
            cache.cleanup()
            self._font_cache = None

    def __del__(self) -> None:  # pragma: no cover - best effort cleanup
        self._cleanup_fonts()

    def _draw_row(
        self, row: Sequence[str], column_widths: Sequence[float], height: float
    ) -> None:
        """Dessiner une ligne du tableau."""
        self._ensure_space(height)
        for index, (value, width) in enumerate(zip(row, column_widths)):
            align = "R" if index == len(row) - 1 else "L"
            self._pdf.cell(width, height, value, border=1, align=align)
        self._pdf.ln(height)

    def _ensure_space(self, height: float) -> None:
        """Ajouter une page si besoin."""
        if self._pdf.get_y() + height > self._pdf.page_break_trigger:
            self._pdf.add_page()


__all__ = ["EnergyPDFBuilder", "TableConfig"]
