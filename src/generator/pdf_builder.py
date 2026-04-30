"""PDF product builder - generates printable digital products."""

from pathlib import Path
from fpdf import FPDF

from src.config import PDF_FORMATS


class ProductPDF(FPDF):
    """Custom PDF class for generating printable products."""

    def __init__(self, product: dict, page_format: str = "A4"):
        width, height = PDF_FORMATS[page_format]
        super().__init__(orientation="P", unit="mm", format=(width, height))
        self.product = product
        self.palette = product["palette"]
        self.page_width = width
        self.page_height = height
        self._setup_colors()

    def _setup_colors(self):
        """Parse hex colors to RGB tuples."""
        self.color_primary = self._hex_to_rgb(self.palette["primary"])
        self.color_secondary = self._hex_to_rgb(self.palette["secondary"])
        self.color_accent = self._hex_to_rgb(self.palette["accent"])

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> tuple:
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def header(self):
        """Draw page header with product title."""
        # Background accent bar
        self.set_fill_color(*self.color_accent)
        self.rect(0, 0, self.page_width, 2, "F")

        # Title
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(*self.color_primary)
        self.set_y(10)
        self.cell(0, 10, self.product["title"], align="C", new_x="LMARGIN", new_y="NEXT")

        # Subtitle
        if self.product.get("subtitle"):
            self.set_font("Helvetica", "", 10)
            self.set_text_color(*self.color_accent)
            self.cell(0, 6, self.product["subtitle"], align="C", new_x="LMARGIN", new_y="NEXT")

        self.ln(5)

    def footer(self):
        """Draw page footer."""
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

    def _draw_section_heading(self, heading: str):
        """Draw a section heading."""
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(*self.color_primary)
        self.cell(0, 8, heading, new_x="LMARGIN", new_y="NEXT")
        # Underline
        self.set_draw_color(*self.color_accent)
        self.set_line_width(0.5)
        y = self.get_y()
        self.line(self.l_margin, y, self.page_width - self.r_margin, y)
        self.ln(3)

    def _draw_lined_section(self, section: dict):
        """Draw lined rows for writing."""
        rows = section.get("rows", 10)
        self.set_draw_color(200, 200, 200)
        self.set_line_width(0.2)
        usable_width = self.page_width - self.l_margin - self.r_margin
        line_height = 8

        for i in range(rows):
            y = self.get_y() + line_height
            if y > self.page_height - 25:
                self.add_page()
                self._draw_section_heading(section["heading"] + " (continued)")
                y = self.get_y() + line_height
            self.line(self.l_margin, y, self.l_margin + usable_width, y)
            self.set_y(y)

        self.ln(5)

    def _draw_checklist_section(self, section: dict):
        """Draw checklist with checkboxes."""
        rows = section.get("rows", 10)
        self.set_draw_color(*self.color_primary)
        self.set_line_width(0.3)
        box_size = 4
        line_height = 8

        for i in range(rows):
            y = self.get_y()
            if y + line_height > self.page_height - 25:
                self.add_page()
                self._draw_section_heading(section["heading"] + " (continued)")
                y = self.get_y()
            # Checkbox
            self.rect(self.l_margin, y + 1, box_size, box_size)
            # Line after checkbox
            self.set_draw_color(200, 200, 200)
            line_start = self.l_margin + box_size + 3
            usable_width = self.page_width - self.r_margin - line_start
            self.line(line_start, y + box_size + 1, line_start + usable_width, y + box_size + 1)
            self.set_draw_color(*self.color_primary)
            self.set_y(y + line_height)

        self.ln(5)

    def _draw_grid_section(self, section: dict):
        """Draw a grid layout."""
        rows = section.get("rows", 5)
        cols = section.get("columns", 3)
        usable_width = self.page_width - self.l_margin - self.r_margin
        col_width = usable_width / cols
        row_height = 10

        self.set_draw_color(200, 200, 200)
        self.set_line_width(0.2)

        for r in range(rows):
            y = self.get_y()
            if y + row_height > self.page_height - 25:
                self.add_page()
                self._draw_section_heading(section["heading"] + " (continued)")
                y = self.get_y()
            for c in range(cols):
                x = self.l_margin + c * col_width
                self.rect(x, y, col_width, row_height)
            self.set_y(y + row_height)

        self.ln(5)

    def _draw_table_section(self, section: dict):
        """Draw a table with headers."""
        rows = section.get("rows", 8)
        headers = section.get("column_headers", ["Column 1", "Column 2", "Column 3"])
        cols = len(headers)
        usable_width = self.page_width - self.l_margin - self.r_margin
        col_width = usable_width / cols
        row_height = 8

        # Header row
        self.set_fill_color(*self.color_accent)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 9)
        for i, header in enumerate(headers):
            x = self.l_margin + i * col_width
            self.set_xy(x, self.get_y())
            self.cell(col_width, row_height, header, border=1, fill=True, align="C")
        self.ln(row_height)

        # Data rows
        self.set_text_color(*self.color_primary)
        self.set_font("Helvetica", "", 9)
        self.set_draw_color(200, 200, 200)

        for r in range(rows):
            y = self.get_y()
            if y + row_height > self.page_height - 25:
                self.add_page()
                self._draw_section_heading(section["heading"] + " (continued)")
                y = self.get_y()
            for c in range(cols):
                x = self.l_margin + c * col_width
                self.rect(x, y, col_width, row_height)
            self.set_y(y + row_height)

        self.ln(5)

    def _draw_blank_section(self, section: dict):
        """Draw a blank box area for notes/drawing."""
        height = section.get("rows", 8) * 6
        usable_width = self.page_width - self.l_margin - self.r_margin

        if self.get_y() + height > self.page_height - 25:
            self.add_page()
            self._draw_section_heading(section["heading"] + " (continued)")

        self.set_draw_color(200, 200, 200)
        self.set_line_width(0.3)
        self.rect(self.l_margin, self.get_y(), usable_width, height)
        self.set_y(self.get_y() + height + 5)

    def build(self) -> "ProductPDF":
        """Build the full PDF from product data."""
        self.set_auto_page_break(auto=True, margin=20)
        self.add_page()

        sections = self.product.get("sections", [])
        for section in sections:
            # Check if we need a new page
            if self.get_y() > self.page_height - 60:
                self.add_page()

            self._draw_section_heading(section["heading"])

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

        return self

    def save(self, output_path: Path) -> Path:
        """Save the PDF to disk."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self.output(str(output_path))
        return output_path


def create_product_pdf(product: dict, output_dir: Path, page_format: str = "A4") -> Path:
    """Create a PDF product file from product data."""
    # Create safe filename
    safe_name = "".join(c if c.isalnum() or c in " -_" else "" for c in product["title"])
    safe_name = safe_name.strip().replace(" ", "_")[:50]
    filename = f"{safe_name}_{page_format}.pdf"

    output_path = output_dir / filename

    pdf = ProductPDF(product, page_format)
    pdf.build()
    pdf.save(output_path)

    return output_path
