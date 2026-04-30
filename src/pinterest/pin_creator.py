"""Pinterest pin image generator."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import textwrap

from src.config import PIN_WIDTH, PIN_HEIGHT


def create_pin_image(product: dict, output_dir: Path) -> Path:
    """Generate a Pinterest pin image (1000x1500px) for a product."""
    palette = product["palette"]
    primary = _hex_to_rgb(palette["primary"])
    secondary = _hex_to_rgb(palette["secondary"])
    accent = _hex_to_rgb(palette["accent"])

    # Create image with secondary (light) background
    img = Image.new("RGB", (PIN_WIDTH, PIN_HEIGHT), secondary)
    draw = ImageDraw.Draw(img)

    # Top accent bar
    draw.rectangle([(0, 0), (PIN_WIDTH, 80)], fill=accent)

    # Bottom accent bar
    draw.rectangle([(0, PIN_HEIGHT - 60), (PIN_WIDTH, PIN_HEIGHT)], fill=primary)

    # Decorative elements
    _draw_decorative_elements(draw, accent, primary)

    # Title text
    title = product["title"]
    _draw_centered_text(draw, title, y=200, max_width=800,
                        font_size=64, color=primary, bold=True)

    # Subtitle
    subtitle = product.get("subtitle", "")
    if subtitle:
        _draw_centered_text(draw, subtitle, y=400, max_width=700,
                            font_size=36, color=accent, bold=False)

    # Product type badge
    product_type = product.get("product_type", "Digital Download")
    _draw_badge(draw, product_type.upper(), y=550, color=accent)

    # Features/sections preview
    sections = product.get("sections", [])[:4]
    if sections:
        _draw_feature_list(draw, sections, y=700, color=primary, accent=accent)

    # Call to action
    _draw_centered_text(draw, "INSTANT DOWNLOAD", y=PIN_HEIGHT - 200,
                        max_width=600, font_size=32, color=accent, bold=True)
    _draw_centered_text(draw, "Print at home \u2022 A4 & Letter size", y=PIN_HEIGHT - 140,
                        max_width=600, font_size=24, color=primary, bold=False)

    # Save
    safe_name = "".join(c if c.isalnum() or c in " -_" else "" for c in product["title"])
    safe_name = safe_name.strip().replace(" ", "_")[:50]
    output_path = output_dir / f"{safe_name}_pin.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "PNG", quality=95)

    return output_path


def _draw_decorative_elements(draw: ImageDraw.Draw, accent, primary):
    """Add decorative geometric elements."""
    # Corner accents
    draw.rectangle([(40, 120), (60, 160)], fill=accent)
    draw.rectangle([(PIN_WIDTH - 60, 120), (PIN_WIDTH - 40, 160)], fill=accent)
    # Divider line
    y_div = 480
    draw.line([(150, y_div), (PIN_WIDTH - 150, y_div)], fill=accent, width=2)


def _draw_centered_text(draw: ImageDraw.Draw, text: str, y: int, max_width: int,
                        font_size: int, color: tuple, bold: bool):
    """Draw centered text, wrapping if needed."""
    try:
        weight = "Bold" if bold else "Regular"
        font = ImageFont.truetype(f"arial{'bd' if bold else ''}.ttf", font_size)
    except (OSError, IOError):
        font = ImageFont.load_default()

    # Wrap text
    wrapped = textwrap.wrap(text, width=max(10, max_width // (font_size // 2)))

    for i, line in enumerate(wrapped):
        bbox = draw.textbbox((0, 0), line, font=font)
        text_width = bbox[2] - bbox[0]
        x = (PIN_WIDTH - text_width) // 2
        draw.text((x, y + i * (font_size + 10)), line, font=font, fill=color)


def _draw_badge(draw: ImageDraw.Draw, text: str, y: int, color: tuple):
    """Draw a badge/pill shape with text."""
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except (OSError, IOError):
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    padding = 20
    badge_width = text_width + padding * 2
    x = (PIN_WIDTH - badge_width) // 2

    draw.rounded_rectangle(
        [(x, y), (x + badge_width, y + 40)],
        radius=20, fill=color
    )
    draw.text((x + padding, y + 8), text, font=font, fill=(255, 255, 255))


def _draw_feature_list(draw: ImageDraw.Draw, sections: list, y: int,
                       color: tuple, accent: tuple):
    """Draw a list of product features/sections."""
    try:
        font = ImageFont.truetype("arial.ttf", 24)
    except (OSError, IOError):
        font = ImageFont.load_default()

    for i, section in enumerate(sections):
        item_y = y + i * 55
        # Bullet
        draw.ellipse([(120, item_y + 8), (135, item_y + 23)], fill=accent)
        # Text
        heading = section.get("heading", "")[:35]
        draw.text((155, item_y), heading, font=font, fill=color)


def _hex_to_rgb(hex_color: str) -> tuple:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
