import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
PINTEREST_ACCESS_TOKEN = os.getenv("PINTEREST_ACCESS_TOKEN", "")
ETSY_SHOP_NAME = os.getenv("ETSY_SHOP_NAME", "")

# Product settings
PRODUCTS_PER_RUN = int(os.getenv("PRODUCTS_PER_RUN", "1"))
DEFAULT_PRICE = float(os.getenv("DEFAULT_PRICE", "4.99"))
NICHES = os.getenv("NICHES", "productivity,budget,wedding,teacher,small-business").split(",")

# Paths
ROOT_DIR = Path(__file__).parent.parent
OUTPUT_DIR = ROOT_DIR / "output"
TEMPLATES_DIR = ROOT_DIR / "templates"
FONTS_DIR = TEMPLATES_DIR / "fonts"

# PDF settings
PDF_FORMATS = {
    "A4": (210, 297),
    "Letter": (215.9, 279.4),
    "A5": (148, 210),
}

# Pinterest settings
PIN_WIDTH = 1000
PIN_HEIGHT = 1500

# Color palettes for products
COLOR_PALETTES = [
    {"name": "Minimal", "primary": "#2C3E50", "secondary": "#ECF0F1", "accent": "#3498DB"},
    {"name": "Warm", "primary": "#6B4226", "secondary": "#FFF8F0", "accent": "#E67E22"},
    {"name": "Sage", "primary": "#2D5016", "secondary": "#F5F9F0", "accent": "#7CB342"},
    {"name": "Blush", "primary": "#6B2D5B", "secondary": "#FFF0F5", "accent": "#E91E63"},
    {"name": "Ocean", "primary": "#1A3A4A", "secondary": "#F0F8FF", "accent": "#00ACC1"},
    {"name": "Lavender", "primary": "#4A2D6B", "secondary": "#F8F0FF", "accent": "#9C27B0"},
    {"name": "Terracotta", "primary": "#8B4513", "secondary": "#FFF5EE", "accent": "#D2691E"},
    {"name": "Forest", "primary": "#1B4332", "secondary": "#F0FFF0", "accent": "#2E8B57"},
]
