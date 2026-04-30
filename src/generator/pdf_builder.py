"""Premium PDF product builder with family-aware templates."""

import hashlib
from pathlib import Path

from fpdf import FPDF

from src.config import PDF_FORMATS


def _lighten(rgb: tuple[int, int, int], factor: float = 0.85) -> tuple[int, int, int]:
    return tuple(min(255, int(c + (255 - c) * factor)) for c in rgb)


def _darken(rgb: tuple[int, int, int], factor: float = 0.75) -> tuple[int, int, int]:
    return tuple(max(0, int(c * factor)) for c in rgb)


def _mix(a: tuple[int, int, int], b: tuple[int, int, int], ratio_to_b: float) -> tuple[int, int, int]:
    ratio_to_b = max(0.0, min(1.0, ratio_to_b))
    ratio_to_a = 1.0 - ratio_to_b
    return (
        int(a[0] * ratio_to_a + b[0] * ratio_to_b),
        int(a[1] * ratio_to_a + b[1] * ratio_to_b),
        int(a[2] * ratio_to_a + b[2] * ratio_to_b),
    )


THEMES: dict[str, dict] = {
    "editorial_bold": {
        "stripe_h": 3.0,
        "title_radius": 2.0,
        "chapter_badge_radius": 3.5,
        "worksheet_card_radius": 2.5,
        "bullet_style": "square",
        "cover_motif": "diagonal",
        "backdrop": "grid",
        "title_size": 35,
        "chapter_size": 21,
        "palette": {
            "accent_target": (20, 150, 255),
            "accent_ratio": 0.30,
            "secondary_target": (249, 248, 245),
            "secondary_ratio": 0.58,
            "primary_target": (25, 25, 25),
            "primary_ratio": 0.10,
        },
    },
    "soft_luxe": {
        "stripe_h": 2.1,
        "title_radius": 6.0,
        "chapter_badge_radius": 8.0,
        "worksheet_card_radius": 7.5,
        "bullet_style": "circle",
        "cover_motif": "circles",
        "backdrop": "dots",
        "title_size": 33,
        "chapter_size": 20,
        "palette": {
            "accent_target": (236, 122, 160),
            "accent_ratio": 0.25,
            "secondary_target": (255, 247, 251),
            "secondary_ratio": 0.72,
            "primary_target": (54, 45, 70),
            "primary_ratio": 0.18,
        },
    },
    "playful_modern": {
        "stripe_h": 3.2,
        "title_radius": 7.0,
        "chapter_badge_radius": 5.5,
        "worksheet_card_radius": 5.0,
        "bullet_style": "diamond",
        "cover_motif": "blobs",
        "backdrop": "waves",
        "title_size": 36,
        "chapter_size": 22,
        "palette": {
            "accent_target": (255, 138, 58),
            "accent_ratio": 0.27,
            "secondary_target": (246, 252, 255),
            "secondary_ratio": 0.66,
            "primary_target": (22, 63, 97),
            "primary_ratio": 0.18,
        },
    },
}


class ProductPDF(FPDF):
    """Custom PDF class for generating premium printable and workbook products."""

    MARGIN = 14.0

    def __init__(self, product: dict, page_format: str = "A4"):
        width, height = PDF_FORMATS[page_format]
        super().__init__(orientation="P", unit="mm", format=(width, height))
        self.set_margins(self.MARGIN, self.MARGIN, self.MARGIN)
        self.product = product
        self.palette = product["palette"]
        self.page_width = width
        self.page_height = height
        self.content_width = width - 2 * self.MARGIN
        self._setup_theme()
        self._setup_colors()
        self._cover_page_no = 1

    def _setup_theme(self):
        seed = self.product.get("fingerprint") or self.product.get("title", "")
        idx = int(hashlib.sha256(seed.encode("utf-8")).hexdigest(), 16) % len(THEMES)
        self.theme_name = list(THEMES.keys())[idx]
        self.theme = THEMES[self.theme_name]

    def _setup_colors(self):
        base_primary = self._hex_to_rgb(self.palette["primary"])
        base_secondary = self._hex_to_rgb(self.palette["secondary"])
        base_accent = self._hex_to_rgb(self.palette["accent"])

        p = self.theme["palette"]
        self.color_primary = _mix(base_primary, p["primary_target"], p["primary_ratio"])
        self.color_secondary = _mix(base_secondary, p["secondary_target"], p["secondary_ratio"])
        self.color_accent = _mix(base_accent, p["accent_target"], p["accent_ratio"])

        self.color_accent_light = _lighten(self.color_accent, 0.82)
        self.color_primary_light = _lighten(self.color_primary, 0.90)
        self.color_text = _mix(self.color_primary, (28, 28, 28), 0.65)
        self.color_muted = _mix(self.color_primary, (130, 130, 130), 0.75)
        self.color_page_bg = _mix(self.color_secondary, (255, 255, 255), 0.42)
        self.color_pattern = _mix(self.color_page_bg, self.color_primary, 0.16)

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))

    def _rrect(self, x: float, y: float, w: float, h: float, r: float = 3.0, style: str = "F"):
        self.rect(x, y, w, h, style, round_corners=True, corner_radius=r)

    def _add_content_page(self, backdrop_variant: int = 0):
        self.add_page()
        self._draw_page_backdrop(backdrop_variant)

    def _draw_page_backdrop(self, variant: int = 0):
        area_y = 13.0
        area_h = self.page_height - 26.0

        self.set_fill_color(*self.color_page_bg)
        self.rect(self.MARGIN, area_y, self.content_width, area_h, "F")

        mode = self.theme["backdrop"]
        if mode == "grid":
            self.set_draw_color(*_lighten(self.color_pattern, 0.55))
            self.set_line_width(0.18)
            x = self.MARGIN + 6
            while x < self.page_width - self.MARGIN:
                self.line(x, area_y + 3, x, area_y + area_h - 3)
                x += 12
            y = area_y + 6
            while y < area_y + area_h:
                self.line(self.MARGIN + 3, y, self.page_width - self.MARGIN - 3, y)
                y += 16
        elif mode == "dots":
            dot = _lighten(self.color_pattern, 0.45)
            self.set_fill_color(*dot)
            y = area_y + 7 + (variant % 3)
            while y < area_y + area_h - 6:
                x = self.MARGIN + 8
                while x < self.page_width - self.MARGIN - 6:
                    self.ellipse(x, y, 1.15, 1.15, "F")
                    x += 13
                y += 12
        else:
            soft = _lighten(self.color_pattern, 0.58)
            self.set_fill_color(*soft)
            self.ellipse(self.page_width - 70, area_y - 14 + (variant % 4) * 2, 95, 45, "F")
            self.ellipse(self.MARGIN - 25, area_y + area_h - 28 - (variant % 3) * 2, 90, 46, "F")

    def header(self):
        if self.page_no() == self._cover_page_no:
            return

        self.set_fill_color(*self.color_accent)
        self.rect(0, 0, self.page_width, self.theme["stripe_h"], "F")

        self.set_font("Helvetica", "", 7.5)
        self.set_text_color(*self.color_muted)
        self.set_xy(self.MARGIN, 4)
        self.cell(self.content_width * 0.68, 5, self.product["title"][:80], align="L")

        self.set_xy(self.MARGIN + self.content_width * 0.68, 4)
        family_label = self.product.get("product_family", "").replace("_", " ").title()
        self.cell(self.content_width * 0.32, 5, family_label, align="R")

        self.set_xy(self.MARGIN, 7.3)
        self.set_font("Helvetica", "", 6.8)
        self.cell(self.content_width, 4.2, self.theme_name.replace("_", " ").title(), align="R")

        self.set_y(13)

    def footer(self):
        if self.page_no() == self._cover_page_no:
            return

        self.set_y(-11)
        self.set_fill_color(*_lighten(self.color_accent, 0.66))
        self.rect(self.MARGIN, self.page_height - 11, self.content_width, 0.5, "F")

        self.set_font("Helvetica", "", 7.5)
        self.set_text_color(*self.color_muted)
        self.cell(0, 6, f"  {self.page_no()}  ", align="C")

    def _draw_cover_page(self):
        self.add_page()

        self.set_fill_color(*self.color_primary)
        self.rect(0, 0, self.page_width, self.page_height, "F")

        motif = self.theme["cover_motif"]
        if motif == "circles":
            self.set_fill_color(*_darken(self.color_primary, 0.80))
            self.ellipse(self.page_width - 48, -28, 76, 76, "F")
            self.set_fill_color(*_darken(self.color_primary, 0.84))
            self.ellipse(-22, self.page_height - 52, 72, 72, "F")
        elif motif == "diagonal":
            self.set_fill_color(*_darken(self.color_primary, 0.80))
            self.polygon(
                [
                    (self.page_width * 0.58, 0),
                    (self.page_width, 0),
                    (self.page_width, self.page_height * 0.34),
                ],
                style="F",
            )
            self.set_fill_color(*_darken(self.color_primary, 0.88))
            self.polygon(
                [
                    (0, self.page_height * 0.72),
                    (self.page_width * 0.45, self.page_height),
                    (0, self.page_height),
                ],
                style="F",
            )
        else:
            self.set_fill_color(*_darken(self.color_primary, 0.80))
            self.ellipse(self.page_width - 60, -18, 92, 54, "F")
            self.set_fill_color(*_darken(self.color_primary, 0.86))
            self.ellipse(-30, self.page_height - 36, 86, 52, "F")

        self.set_fill_color(*self.color_accent)
        self.rect(0, 0, self.page_width, 10, "F")
        self.rect(0, self.page_height - 22, self.page_width, 22, "F")

        family_raw = self.product.get("product_family", "Digital Product")
        family_label = family_raw.replace("_", " ").upper()
        badge_w = 66
        badge_x = (self.page_width - badge_w) / 2

        self.set_fill_color(*_darken(self.color_accent, 0.80))
        self._rrect(badge_x, 20.5, badge_w, 9, r=self.theme["title_radius"], style="F")
        self.set_font("Helvetica", "B", 7)
        self.set_text_color(255, 255, 255)
        self.set_xy(badge_x, 21.5)
        self.cell(badge_w, 7, family_label[:40], align="C")

        self.set_font("Helvetica", "", 8.5)
        self.set_text_color(*_lighten(self.color_accent, 0.52))
        self.set_xy(self.MARGIN, 34)
        self.cell(self.content_width, 6, "IMPLEMENTATION WORKBOOK", align="C")

        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", self.theme["title_size"])
        self.set_y(42)
        self.multi_cell(0, 12.5, self.product["title"], align="C")

        subtitle = self.product.get("subtitle", "")
        if subtitle:
            self.ln(4)
            card_w = self.content_width * 0.84
            card_x = (self.page_width - card_w) / 2
            card_y = self.get_y()
            self.set_fill_color(*_darken(self.color_primary, 0.70))
            self._rrect(card_x, card_y, card_w, 15.5, r=self.theme["title_radius"], style="F")
            self.set_font("Helvetica", "", 12)
            self.set_text_color(*_lighten(self.color_accent, 0.64))
            self.set_xy(card_x + 5, card_y + 4.2)
            self.multi_cell(card_w - 10, 6, subtitle, align="C")

        outcome = self.product.get("buyer_outcome", self.product.get("description", ""))
        self.set_y(self.page_height - 58)
        self.set_font("Helvetica", "", 10.5)
        self.set_text_color(*_lighten(self.color_primary, 0.90))
        self.multi_cell(0, 6.3, outcome[:250], align="C")

        self.set_y(self.page_height - 17)
        self.set_font("Helvetica", "B", 9.8)
        self.set_text_color(255, 255, 255)
        self.cell(0, 6, "INSTANT DIGITAL DOWNLOAD", align="C")

    def _draw_quick_start_page(self):
        self._add_content_page(backdrop_variant=1)
        self._page_title_band("Quick Start Guide")

        intro = self.product.get("guide_intro", "")
        if not intro:
            intro = (
                "This workbook is designed to move you from planning to execution. "
                "Work through each chapter, then complete the matching worksheet."
            )
        self._paragraph(intro)

        self._callout_box(
            "How to Use This Workbook",
            [
                "1. Read one chapter at a time and complete the matching worksheet.",
                "2. Keep your answers practical and specific to your situation.",
                "3. Use the final Action Plan to lock in your next 30 days.",
            ],
            use_accent=True,
        )

        self.ln(3)

        deliverables = self.product.get("deliverables", [])[:8]
        if deliverables:
            self._subheader("What's Included")
            self._bullets(deliverables)

    def _draw_chapter_page(self, chapter: dict, chapter_index: int):
        self._add_content_page(backdrop_variant=chapter_index)

        badge_size = 22
        badge_x = self.MARGIN
        badge_y = self.get_y()

        self.set_fill_color(*self.color_accent)
        self._rrect(
            badge_x,
            badge_y,
            badge_size,
            badge_size,
            r=self.theme["chapter_badge_radius"],
            style="F",
        )
        self.set_font("Helvetica", "B", 15)
        self.set_text_color(255, 255, 255)
        self.set_xy(badge_x, badge_y + 4)
        self.cell(badge_size, 14, str(chapter_index), align="C")

        heading_x = self.MARGIN + badge_size + 6
        heading_w = self.content_width - badge_size - 6
        self.set_font("Helvetica", "B", self.theme["chapter_size"])
        self.set_text_color(*self.color_primary)
        self.set_xy(heading_x, badge_y + 2)
        self.multi_cell(heading_w, 8.6, chapter.get("heading", "Chapter"), align="L")

        self.set_y(badge_y + badge_size + 4)
        self.set_fill_color(*self.color_accent)
        self.rect(self.MARGIN, self.get_y() - 2, self.content_width, 1.5, "F")
        self.ln(5)

        objective = chapter.get("objective", "")
        if objective:
            self._callout_box("Chapter Objective", [objective], compact=True, use_accent=False)

        for para in chapter.get("body_paragraphs", []):
            self._paragraph(para)

        example = chapter.get("example", "")
        if example:
            self._callout_box("Practical Example", [example], use_accent=True)

        takeaways = chapter.get("key_takeaways", [])
        if takeaways:
            self._subheader("Key Takeaways")
            self._bullets(takeaways)

    def _page_title_band(self, text: str):
        y = self.get_y()
        self.set_fill_color(*self.color_accent)
        self._rrect(self.MARGIN, y, self.content_width, 14, r=self.theme["title_radius"], style="F")

        self.set_fill_color(*_lighten(self.color_accent, 0.40))
        self._rrect(
            self.MARGIN,
            y + 9.8,
            self.content_width,
            4.2,
            r=self.theme["title_radius"],
            style="F",
        )

        self.set_font("Helvetica", "B", 14)
        self.set_text_color(255, 255, 255)
        self.set_xy(self.MARGIN + 7, y + 3.5)
        self.cell(self.content_width - 14, 7, text, align="L")
        self.set_y(y + 20)

    def _subheader(self, text: str):
        if self.get_y() > self.page_height - 40:
            self._add_content_page(backdrop_variant=7)

        self.set_font("Helvetica", "B", 12)
        self.set_text_color(*self.color_primary)
        self.set_x(self.MARGIN)
        self.multi_cell(self.content_width, 7, text)

        y = self.get_y()
        self.set_fill_color(*self.color_accent)
        self.rect(self.MARGIN, y, self.content_width * 0.35, 1.2, "F")
        self.ln(4)

    def _paragraph(self, text: str):
        if self.get_y() > self.page_height - 40:
            self._add_content_page(backdrop_variant=9)

        self.set_font("Helvetica", "", 11)
        self.set_text_color(*self.color_text)
        self.set_x(self.MARGIN)
        self.multi_cell(self.content_width, 6.5, text.strip())
        self.ln(4)

    def _callout_box(self, title: str, lines: list[str], compact: bool = False, use_accent: bool = True):
        # Overflow-safe callout: fill=True on multi_cell means height auto-expands with text.
        if self.get_y() > self.page_height - 55:
            self._add_content_page(backdrop_variant=11)

        line_h = 5.6 if compact else 6.2
        title_bg = self.color_accent if use_accent else self.color_primary
        content_bg = self.color_accent_light if use_accent else self.color_primary_light

        self.set_fill_color(*title_bg)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 10)
        self.set_x(self.MARGIN)
        self.multi_cell(self.content_width, 8, f"   {title}", fill=True, new_x="LMARGIN", new_y="NEXT")

        self.set_fill_color(*content_bg)
        self.set_text_color(*self.color_text)
        self.set_font("Helvetica", "", 10)
        for line in lines:
            self.set_x(self.MARGIN)
            self.multi_cell(self.content_width, line_h, f"   {line}", fill=True, new_x="LMARGIN", new_y="NEXT")

        self.set_fill_color(*content_bg)
        self.set_x(self.MARGIN)
        self.cell(self.content_width, 2.5, "", fill=True)
        self.ln(6)

    def _bullets(self, lines: list[str], bullet_color: tuple[int, int, int] | None = None):
        if bullet_color is None:
            bullet_color = self.color_accent

        self.set_font("Helvetica", "", 10.5)
        self.set_text_color(*self.color_text)
        for line in lines:
            if self.get_y() > self.page_height - 22:
                self._add_content_page(backdrop_variant=13)

            y = self.get_y()
            self.set_fill_color(*bullet_color)
            style = self.theme["bullet_style"]
            if style == "square":
                self._rrect(self.MARGIN + 1.2, y + 3.0, 2.8, 2.8, r=0.8, style="F")
            elif style == "diamond":
                cx = self.MARGIN + 2.6
                cy = y + 4.5
                self.polygon([(cx, cy - 1.8), (cx + 1.8, cy), (cx, cy + 1.8), (cx - 1.8, cy)], style="F")
            else:
                self.ellipse(self.MARGIN + 1.2, y + 3.2, 2.8, 2.8, "F")

            self.set_x(self.MARGIN + 6.5)
            self.multi_cell(self.content_width - 6.5, 6.5, str(line).strip(), new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def _draw_worksheet_section(self, section: dict):
        needed = 85 if section.get("type") in ("table", "grid") else 65
        if self.get_y() > self.page_height - needed:
            self._add_content_page(backdrop_variant=15)

        y = self.get_y()
        self.set_fill_color(*self.color_primary)
        self._rrect(self.MARGIN, y, self.content_width, 13, r=self.theme["worksheet_card_radius"], style="F")

        type_label = section.get("type", "lined").upper()
        badge_w = 24
        self.set_fill_color(*self.color_accent)
        self._rrect(
            self.MARGIN + self.content_width - badge_w - 3,
            y + 2.5,
            badge_w,
            8,
            r=max(2.0, self.theme["worksheet_card_radius"] - 1.0),
            style="F",
        )

        self.set_font("Helvetica", "B", 7)
        self.set_text_color(255, 255, 255)
        self.set_xy(self.MARGIN + self.content_width - badge_w - 3, y + 4)
        self.cell(badge_w, 5, type_label, align="C")

        self.set_font("Helvetica", "B", 11)
        self.set_text_color(255, 255, 255)
        self.set_xy(self.MARGIN + 5, y + 3)
        self.cell(self.content_width - badge_w - 12, 7, section["heading"], align="L")
        self.set_y(y + 16)

        section_type = section.get("type", "lined")
        if section_type == "lined":
            self._draw_lined_section(section)
        elif section_type == "checklist":
            self._draw_checklist_section(section)
        elif section_type == "grid":
            self._draw_grid_section(section)
        elif section_type == "table":
            self._draw_table_section(section)
        elif section_type == "blank":
            self._draw_blank_section(section)
        else:
            self._draw_lined_section(section)

        self.ln(5)

    def _draw_lined_section(self, section: dict):
        rows = section.get("rows", 12)
        line_h = 7.5

        for i in range(rows):
            if self.get_y() + line_h > self.page_height - 18:
                self._add_content_page(backdrop_variant=17)

            y_start = self.get_y()
            if i % 2 == 0:
                self.set_fill_color(*self.color_primary_light)
                self.rect(self.MARGIN, y_start, self.content_width, line_h, "F")

            self.set_draw_color(205, 205, 205)
            self.set_line_width(0.2)
            self.line(self.MARGIN, y_start + line_h - 1, self.MARGIN + self.content_width, y_start + line_h - 1)
            self.set_y(y_start + line_h)

    def _draw_checklist_section(self, section: dict):
        rows = section.get("rows", 12)
        line_h = 8.5
        box_size = 5

        for i in range(rows):
            y = self.get_y()
            if y + line_h > self.page_height - 18:
                self._add_content_page(backdrop_variant=19)
                y = self.get_y()

            if i % 2 == 0:
                self.set_fill_color(*self.color_primary_light)
                self.rect(self.MARGIN, y, self.content_width, line_h, "F")

            self.set_draw_color(*self.color_accent)
            self.set_line_width(0.6)
            self._rrect(self.MARGIN + 2, y + 1.8, box_size, box_size, r=1.5, style="D")

            self.set_draw_color(200, 200, 200)
            self.set_line_width(0.2)
            self.line(self.MARGIN + 11, y + line_h - 1.5, self.MARGIN + self.content_width - 2, y + line_h - 1.5)
            self.set_y(y + line_h)

    def _draw_grid_section(self, section: dict):
        rows = section.get("rows", 8)
        cols = max(1, section.get("columns", 3))
        col_w = self.content_width / cols
        row_h = 9

        for row_i in range(rows):
            y = self.get_y()
            if y + row_h > self.page_height - 18:
                self._add_content_page(backdrop_variant=21)
                y = self.get_y()

            for c in range(cols):
                bg = self.color_primary_light if (row_i + c) % 2 == 0 else (255, 255, 255)
                self.set_fill_color(*bg)
                self.set_draw_color(205, 205, 205)
                self.set_line_width(0.25)
                self.rect(self.MARGIN + c * col_w, y, col_w, row_h, "DF")

            self.set_y(y + row_h)

    def _draw_table_section(self, section: dict):
        rows = section.get("rows", 10)
        headers = section.get("column_headers", ["Task", "Owner", "Status"])
        cols = max(1, len(headers))
        col_w = self.content_width / cols
        header_h = 9
        row_h = 8

        start_y = self.get_y()
        self.set_fill_color(*self.color_primary)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 9)
        for i, hdr in enumerate(headers):
            x = self.MARGIN + i * col_w
            self.set_xy(x, start_y)
            self.cell(col_w, header_h, str(hdr)[:22], border=0, fill=True, align="C")
            if i < cols - 1:
                self.set_fill_color(*self.color_accent)
                self.rect(x + col_w - 0.4, start_y, 0.8, header_h, "F")
                self.set_fill_color(*self.color_primary)

        self.set_y(start_y + header_h)
        self.set_font("Helvetica", "", 9)
        for row_i in range(rows):
            y = self.get_y()
            if y + row_h > self.page_height - 18:
                self._add_content_page(backdrop_variant=23)
                y = self.get_y()

            for c in range(cols):
                bg = self.color_primary_light if row_i % 2 == 0 else (255, 255, 255)
                self.set_fill_color(*bg)
                self.set_draw_color(205, 205, 205)
                self.set_line_width(0.2)
                self.rect(self.MARGIN + c * col_w, y, col_w, row_h, "DF")

            self.set_y(y + row_h)

    def _draw_blank_section(self, section: dict):
        height = max(24, section.get("rows", 12) * 5.2)
        if self.get_y() + height > self.page_height - 18:
            self._add_content_page(backdrop_variant=25)

        self.set_fill_color(*self.color_primary_light)
        self.set_draw_color(*self.color_muted)
        self.set_line_width(0.3)
        self._rrect(self.MARGIN, self.get_y(), self.content_width, height, r=self.theme["worksheet_card_radius"], style="DF")
        self.set_y(self.get_y() + height + 3)

    def build(self) -> "ProductPDF":
        self.set_auto_page_break(auto=True, margin=18)

        self._draw_cover_page()
        self._draw_quick_start_page()

        chapters = self.product.get("chapters", [])
        for idx, chapter in enumerate(chapters, start=1):
            self._draw_chapter_page(chapter, idx)

        sections = self.product.get("sections", [])
        if sections:
            self._add_content_page(backdrop_variant=3)
            self._page_title_band("Workbook Templates & Worksheets")
            self.ln(2)

        for section in sections:
            self._draw_worksheet_section(section)

        self._add_content_page(backdrop_variant=5)
        self._page_title_band("30-Day Action Plan")
        self.ln(2)
        self._callout_box(
            "Your Execution Sprint",
            [
                "Week 1: Define priorities and lock your core goals.",
                "Week 2: Execute key actions and track blockers daily.",
                "Week 3: Optimize your workflow using lessons learned.",
                "Week 4: Review results and set the next growth cycle.",
            ],
            use_accent=True,
        )
        self._draw_worksheet_section(
            {
                "heading": "Action Tracker",
                "type": "table",
                "rows": 14,
                "columns": 4,
                "column_headers": ["Action", "Owner", "Deadline", "Status"],
            }
        )

        return self

    def save(self, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self.output(str(output_path))
        return output_path


def create_product_pdf(product: dict, output_dir: Path, page_format: str = "A4") -> Path:
    safe_name = "".join(c if c.isalnum() or c in " -_" else "" for c in product["title"])
    safe_name = safe_name.strip().replace(" ", "_")[:50]
    filename = f"{safe_name}_{page_format}.pdf"
    output_path = output_dir / filename

    pdf = ProductPDF(product, page_format)
    pdf.build()
    pdf.save(output_path)

    return output_path
