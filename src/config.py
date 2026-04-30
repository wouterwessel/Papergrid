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

# Product families (presentation PDFs intentionally excluded)
PRODUCT_FAMILIES = {
    "printable_bundle": [
        "weekly planner system",
        "habit tracker bundle",
        "budget tracker pack",
        "wedding binder pack",
        "study planner bundle",
    ],
    "guide_workbook": [
        "beginner guide workbook",
        "step-by-step action guide",
        "30-day challenge workbook",
        "self-assessment workbook",
        "implementation workbook",
    ],
    "starter_kit": [
        "small business starter kit",
        "job search starter kit",
        "freelancer admin starter kit",
        "home management starter kit",
        "finance reset starter kit",
    ],
    "business_system": [
        "content planning system",
        "client onboarding system",
        "service delivery system",
        "lead tracking system",
        "operations checklist system",
    ],
}

# Diversity and deduplication settings
IDEA_RETRY_LIMIT = int(os.getenv("IDEA_RETRY_LIMIT", "5"))
RECENT_DUPLICATE_WINDOW = int(os.getenv("RECENT_DUPLICATE_WINDOW", "30"))
MAX_HISTORY_ITEMS = int(os.getenv("MAX_HISTORY_ITEMS", "500"))

# Quality-first generation settings
QUALITY_MODE = os.getenv("QUALITY_MODE", "strict").lower()
MIN_SECTION_COUNT = int(os.getenv("MIN_SECTION_COUNT", "10"))
MIN_GUIDE_CHAPTERS = int(os.getenv("MIN_GUIDE_CHAPTERS", "4"))
MIN_CHAPTER_WORDS = int(os.getenv("MIN_CHAPTER_WORDS", "160"))

# Launch pricing strategy: conversion-first
LAUNCH_PRICE_MIN = float(os.getenv("LAUNCH_PRICE_MIN", "4.99"))
LAUNCH_PRICE_MAX = float(os.getenv("LAUNCH_PRICE_MAX", "8.99"))

# Paths
ROOT_DIR = Path(__file__).parent.parent
OUTPUT_DIR = ROOT_DIR / "output"
TEMPLATES_DIR = ROOT_DIR / "templates"
FONTS_DIR = TEMPLATES_DIR / "fonts"
HISTORY_FILE = ROOT_DIR / "data" / "product_history.json"

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
