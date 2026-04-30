"""AI-powered product idea and content generator using OpenAI API."""

import json
import random
from openai import OpenAI

from src.config import OPENAI_API_KEY, NICHES, COLOR_PALETTES


client = OpenAI(api_key=OPENAI_API_KEY)


PRODUCT_TYPES = [
    "weekly planner",
    "monthly planner",
    "daily planner",
    "habit tracker",
    "mood tracker",
    "budget tracker",
    "expense tracker",
    "savings tracker",
    "meal planner",
    "grocery list",
    "fitness tracker",
    "workout log",
    "reading tracker",
    "goal setting worksheet",
    "project planner",
    "to-do list",
    "gratitude journal page",
    "self-care checklist",
    "cleaning schedule",
    "travel planner",
    "wedding checklist",
    "wedding budget tracker",
    "baby milestone tracker",
    "study planner",
    "exam preparation schedule",
    "social media content planner",
    "business expense tracker",
    "invoice template",
    "client tracker",
    "password log",
]


def generate_product_idea(niche: str | None = None) -> dict:
    """Generate a product idea with full content structure using AI."""
    if niche is None:
        niche = random.choice(NICHES)

    product_type = random.choice(PRODUCT_TYPES)
    palette = random.choice(COLOR_PALETTES)

    prompt = f"""Generate a digital printable product idea for Etsy.

Niche: {niche}
Product type: {product_type}
Color palette: {palette['name']}

Return a JSON object with:
- "title": catchy product name (max 60 chars, no quotes in title)
- "subtitle": short tagline (max 40 chars)
- "description": what this product helps with (1-2 sentences)
- "sections": array of 4-8 section objects, each with:
  - "heading": section title
  - "type": one of "lined", "grid", "checklist", "table", "blank"
  - "rows": number of rows (4-20)
  - "columns": number of columns (1-4, only for grid/table)
  - "column_headers": array of header strings (only for table type)
- "target_audience": who buys this
- "use_case": when/how they use it

Make it practical, attractive, and something people would pay $5 for.
Return ONLY valid JSON, no markdown."""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
        max_tokens=1000,
    )

    content = response.choices[0].message.content.strip()
    # Remove markdown code fences if present
    if content.startswith("```"):
        content = content.split("\n", 1)[1]
        content = content.rsplit("```", 1)[0]

    product = json.loads(content)
    product["niche"] = niche
    product["product_type"] = product_type
    product["palette"] = palette

    return product


def generate_etsy_listing(product: dict) -> dict:
    """Generate optimized Etsy listing copy for a product."""
    prompt = f"""Create an Etsy listing for this digital printable product:

Product: {product['title']}
Description: {product['description']}
Target audience: {product['target_audience']}
Use case: {product['use_case']}
Niche: {product['niche']}

Return a JSON object with:
- "etsy_title": SEO-optimized title (max 140 chars, include keywords buyers search for)
- "description": full Etsy description (300-500 words, include features, what's included, how to use, file format info). Use line breaks.
- "tags": array of exactly 13 tags (each max 20 chars, mix of broad and specific keywords)
- "price": suggested price in USD (between 2.99 and 9.99)
- "category": best Etsy category path

Return ONLY valid JSON, no markdown."""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=1500,
    )

    content = response.choices[0].message.content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1]
        content = content.rsplit("```", 1)[0]

    return json.loads(content)


def generate_pinterest_copy(product: dict) -> dict:
    """Generate Pinterest pin title and description."""
    prompt = f"""Create a Pinterest pin description for this digital product:

Product: {product['title']}
Description: {product['description']}
Target audience: {product['target_audience']}

Return a JSON object with:
- "pin_title": engaging title (max 100 chars, include keywords)
- "pin_description": Pinterest-optimized description (150-300 chars, include relevant keywords and hashtags)
- "board_name": suggested Pinterest board name

Return ONLY valid JSON, no markdown."""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=500,
    )

    content = response.choices[0].message.content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1]
        content = content.rsplit("```", 1)[0]

    return json.loads(content)
