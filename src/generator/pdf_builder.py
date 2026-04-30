"""Premium PDF product builder with family-aware templates."""

from pathlib import Path
from fpdf import FPDF

from src.config import PDF_FORMATS


class ProductPDF(FPDF):
    """Custom PDF class for generating premium printable and workbook products."""

    def __init__(self, product: dict, page_format: str = "A4"):
        width, height = PDF_FORMATS[page_format]
        super().__init__(orientation="P", unit="mm", format=(width, height))
        self.product = product
        self.palette = product["palette"]
        self.page_width = width
        self.page_height = height
        self.content_width = self.page_width - self.l_margin - self.r_margin
        self._setup_colors()
        self._cover_page_no = 1

    def _setup_colors(self):
        self.color_primary = self._hex_to_rgb(self.palette["primary"])
        self.color_secondary = self._hex_to_rgb(self.palette["secondary"])
        self.color_accent = self._hex_to_rgb(self.palette["accent"])

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> tuple:
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))

    def header(self):
        if self.page_no() == self._cover_page_no:
            return

        self.set_fill_color(*self.color_secondary)
        self.rect(0, 0, self.page_width, 14, "F")

        self.set_draw_color(*self.color_accent)
        self.set_line_width(0.8)
        self.line(self.l_margin, 14, self.page_width - self.r_margin, 14)

        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*self.color_primary)
        self.set_xy(self.l_margin, 4)
        self.cell(self.content_width, 6, self.product["title"][:90], align="L")

        self.set_font("Helvetica", "", 8)
        self.set_xy(self.l_margin, 8)
        family_label = self.product.get("product_family", "digital product").replace("_", " ").title()
        self.cell(self.content_width, 4, family_label, align="L")
        self.set_y(20)

    def footer(self):
        if self.page_no() == self._cover_page_no:
            return

        self.set_y(-12)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(140, 140, 140)
        self.cell(0, 6, f"Page {self.page_no()}", align="C")

    def _draw_cover_page(self):
        self.add_page()
        self.set_fill_color(*self.color_primary)
        self.rect(0, 0, self.page_width, self.page_height, "F")

        self.set_fill_color(*self.color_accent)
        self.rect(0, 0, self.page_width, 18, "F")
        self.rect(0, self.page_height - 18, self.page_width, 18, "F")

        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 28)
        self.set_y(58)
        self.multi_cell(0, 13, self.product["title"], align="C")

        subtitle = self.product.get("subtitle", "")
        if subtitle:
            self.set_font("Helvetica", "", 14)
            self.ln(6)
            self.multi_cell(0, 8, subtitle, align="C")

        self.set_font("Helvetica", "", 11)
        self.set_y(self.page_height - 60)
        outcome = self.product.get("buyer_outcome", self.product.get("description", ""))
        self.multi_cell(0, 6, outcome[:220], align="C")

        self.set_font("Helvetica", "B", 11)
        self.set_y(self.page_height - 34)
        self.cell(0, 6, "INSTANT DIGITAL DOWNLOAD", align="C")

    def _draw_quick_start_page(self):
        self.add_page()
        self._section_header("Quick Start")

        intro = self.product.get("guide_intro", "")
        if not intro:
            intro = (
                "This workbook is built to move you from planning to execution. "
                "Use the chapters first, then complete the worksheets in order."
            )
        self._draw_paragraph_block(intro)

        self._callout_box(
            "How to Use This",
            [
                "1. Read one chapter at a time and complete the matching worksheet.",
                "2. Keep your answers practical and specific.",
                "3. Use the final action plan to lock in your next 30 days.",
            ],
        )

        deliverables = self.product.get("deliverables", [])[:8]
        if deliverables:
            self._section_subheader("What's Included")
            self._draw_bullets(deliverables)

    def _draw_chapter_page(self, chapter: dict, chapter_index: int):
        self.add_page()
        self._section_header(f"Chapter {chapter_index}: {chapter.get('heading', 'Workbook Chapter')}")

        objective = chapter.get("objective", "")
        if objective:
            self._callout_box("Chapter Objective", [objective], compact=True)

        paragraphs = chapter.get("body_paragraphs", [])
        for paragraph in paragraphs:
            self._draw_paragraph_block(paragraph)

        example = chapter.get("example", "")
        if example:
            self._callout_box("Practical Example", [example])

        takeaways = chapter.get("key_takeaways", [])
        if takeaways:
            self._section_subheader("Key Takeaways")
            self._draw_bullets(takeaways)

    def _section_header(self, text: str):
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(*self.color_primary)
        self.multi_cell(0, 9, text)
        self.ln(1)

        self.set_draw_color(*self.color_accent)
        self.set_line_width(0.7)
        y = self.get_y()
        self.line(self.l_margin, y, self.page_width - self.r_margin, y)
        self.ln(6)

    def _section_subheader(self, text: str):
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(*self.color_primary)
        self.multi_cell(0, 7, text)
        self.ln(2)

    def _draw_paragraph_block(self, text: str):
        if self.get_y() > self.page_height - 45:
            self.add_page()

        self.set_font("Helvetica", "", 11)
        self.set_text_color(40, 40, 40)
        self.multi_cell(0, 6.5, text.strip())
        self.ln(4)

    def _callout_box(self, title: str, lines: list[str], compact: bool = False):
        line_h = 5.6 if compact else 6.2
        box_h = 12 + len(lines) * line_h
        if self.get_y() + box_h > self.page_height - 18:
            self.add_page()

        x = self.l_margin
        y = self.get_y()
        w = self.content_width

        self.set_fill_color(*self.color_secondary)
        self.set_draw_color(*self.color_accent)
        self.set_line_width(0.4)
        self.rect(x, y, w, box_h, "DF")

        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*self.color_primary)
        self.set_xy(x + 4, y + 3)
        self.cell(w - 8, 6, title)

        self.set_font("Helvetica", "", 10)
        self.set_text_color(50, 50, 50)
        self.set_xy(x + 4, y + 10)
        for line in lines:
            self.multi_cell(w - 8, line_h, line)

        self.set_y(y + box_h + 4)

    def _draw_bullets(self, lines: list[str]):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(50, 50, 50)
        for line in lines:
            if self.get_y() > self.page_height - 22:
                self.add_page()
            self.set_x(self.l_margin)
            self.cell(4, 6, "-", new_x="RIGHT", new_y="TOP")
            self.multi_cell(self.content_width - 4, 6, str(line).strip())
        self.ln(2)

    def _draw_worksheet_section(self, section: dict):
        if self.get_y() > self.page_height - 70:
            self.add_page()

        card_h = 14
        self.set_fill_color(*self.color_secondary)
        self.set_draw_color(225, 225, 225)
        self.rect(self.l_margin, self.get_y(), self.content_width, card_h, "DF")

        self.set_font("Helvetica", "B", 12)
        self.set_text_color(*self.color_primary)
        self.set_xy(self.l_margin + 4, self.get_y() + 4)
        self.cell(self.content_width - 8, 6, section["heading"])
        self.set_y(self.get_y() + card_h)
        self.ln(2)

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

    def _draw_lined_section(self, section: dict):
        rows = section.get("rows", 12)
        self.set_draw_color(210, 210, 210)
        self.set_line_width(0.25)
        line_height = 7

        for _ in range(rows):
            y = self.get_y() + line_height
            if y > self.page_height - 22:
                self.add_page()
                y = self.get_y() + line_height
            self.line(self.l_margin, y, self.page_width - self.r_margin, y)
            self.set_y(y)
        self.ln(4)

    def _draw_checklist_section(self, section: dict):
        rows = section.get("rows", 12)
        box_size = 4
        line_height = 7.5

        for _ in range(rows):
            y = self.get_y()
            if y + line_height > self.page_height - 20:
                self.add_page()
                y = self.get_y()
            self.set_draw_color(*self.color_primary)
            self.rect(self.l_margin, y + 1.2, box_size, box_size)
            self.set_draw_color(205, 205, 205)
            self.line(self.l_margin + 8, y + 5, self.page_width - self.r_margin, y + 5)
            self.set_y(y + line_height)
        self.ln(3)

    def _draw_grid_section(self, section: dict):
        rows = section.get("rows", 8)
        cols = max(1, section.get("columns", 3))
        col_width = self.content_width / cols
        row_height = 8

        self.set_draw_color(210, 210, 210)
        self.set_line_width(0.25)

        for _ in range(rows):
            y = self.get_y()
            if y + row_height > self.page_height - 20:
                self.add_page()
                y = self.get_y()
            for c in range(cols):
                self.rect(self.l_margin + c * col_width, y, col_width, row_height)
            self.set_y(y + row_height)
        self.ln(3)

    def _draw_table_section(self, section: dict):
        rows = section.get("rows", 10)
        headers = section.get("column_headers", ["Task", "Owner", "Status"])
        cols = max(1, len(headers))
        col_width = self.content_width / cols
        row_height = 7.5

        self.set_fill_color(*self.color_accent)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 9)
        start_y = self.get_y()
        for i, header in enumerate(headers):
            self.set_xy(self.l_margin + i * col_width, start_y)
            self.cell(col_width, row_height, str(header)[:24], border=1, fill=True, align="C")
        self.ln(row_height)

        self.set_draw_color(210, 210, 210)
        self.set_text_color(40, 40, 40)
        self.set_font("Helvetica", "", 9)
        for _ in range(rows):
            y = self.get_y()
            if y + row_height > self.page_height - 20:
                self.add_page()
                y = self.get_y()
            for c in range(cols):
                self.rect(self.l_margin + c * col_width, y, col_width, row_height)
            self.set_y(y + row_height)
        self.ln(3)

    def _draw_blank_section(self, section: dict):
        height = section.get("rows", 12) * 5.2
        if self.get_y() + height > self.page_height - 20:
            self.add_page()

        self.set_draw_color(210, 210, 210)
        self.rect(self.l_margin, self.get_y(), self.content_width, height)
        self.set_y(self.get_y() + height + 3)

    def build(self) -> "ProductPDF":
        self.set_auto_page_break(auto=True, margin=16)

        self._draw_cover_page()
        self._draw_quick_start_page()

        chapters = self.product.get("chapters", [])
        for idx, chapter in enumerate(chapters, start=1):
            self._draw_chapter_page(chapter, idx)

        sections = self.product.get("sections", [])
        if sections:
            self.add_page()
            self._section_header("Workbook Templates & Worksheets")

        for section in sections:
            self._draw_worksheet_section(section)

        # Final action plan page to increase practical value.
        self.add_page()
        self._section_header("30-Day Action Plan")
        self._callout_box(
            "Execution Sprint",
            [
                "Week 1: Define priorities and lock your core goals.",
                "Week 2: Execute key actions and track blockers daily.",
                "Week 3: Optimize your workflow using lessons learned.",
                "Week 4: Review results and set the next growth cycle.",
            ],
        )
        self._draw_worksheet_section({
            "heading": "Action Tracker",
            "type": "table",
            "rows": 14,
            "columns": 4,
            "column_headers": ["Action", "Owner", "Deadline", "Status"],
        })

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
