"""AI-powered product idea and content generator using OpenAI API."""

import json
import hashlib
import random
import re
from openai import OpenAI

from src.config import (
    OPENAI_API_KEY,
    NICHES,
    COLOR_PALETTES,
    PRODUCT_FAMILIES,
    IDEA_RETRY_LIMIT,
    RECENT_DUPLICATE_WINDOW,
)


client = OpenAI(api_key=OPENAI_API_KEY)

AI_DISCLOSURE = (
    "This digital product was created with AI assistance and then reviewed, "
    "curated, and formatted by the shop owner."
)

def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", "", text.lower())).strip()


def _extract_json(content: str) -> dict:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1]
        cleaned = cleaned.rsplit("```", 1)[0]
    return json.loads(cleaned)


def _weighted_pick(options: list[str], counts: dict[str, int]) -> str:
    weights = [1.0 / (1 + counts.get(opt, 0)) for opt in options]
    return random.choices(options, weights=weights, k=1)[0]


def _choose_product_plan(recent_history: list[dict], forced_niche: str | None) -> dict:
    recent = recent_history[-RECENT_DUPLICATE_WINDOW:]

    family_counts: dict[str, int] = {}
    niche_counts: dict[str, int] = {}
    subtype_counts: dict[str, int] = {}

    for item in recent:
        family_counts[item.get("product_family", "")] = family_counts.get(item.get("product_family", ""), 0) + 1
        niche_counts[item.get("niche", "")] = niche_counts.get(item.get("niche", ""), 0) + 1
        subtype_counts[item.get("product_subtype", "")] = subtype_counts.get(item.get("product_subtype", ""), 0) + 1

    family = _weighted_pick(list(PRODUCT_FAMILIES.keys()), family_counts)
    subtype = _weighted_pick(PRODUCT_FAMILIES[family], subtype_counts)
    niche = forced_niche if forced_niche else _weighted_pick(NICHES, niche_counts)

    return {
        "product_family": family,
        "product_subtype": subtype,
        "niche": niche,
    }


def _build_exclusions(recent_history: list[dict]) -> dict:
    recent = recent_history[-RECENT_DUPLICATE_WINDOW:]
    recent_titles = [item.get("title", "") for item in recent if item.get("title")]
    recent_combos = [
        f"{item.get('product_family', '')}:{item.get('niche', '')}:{item.get('product_subtype', '')}"
        for item in recent
    ]
    recent_sections = []
    for item in recent:
        for section in item.get("section_headings", []):
            if section:
                recent_sections.append(section)

    return {
        "recent_titles": recent_titles[-12:],
        "recent_combos": recent_combos[-12:],
        "recent_sections": list(dict.fromkeys(recent_sections[-30:])),
    }


def _fingerprint(product: dict) -> str:
    section_sig = "|".join(
        f"{_normalize(s.get('heading', ''))}:{s.get('type', '')}:{s.get('rows', 0)}:{s.get('columns', 0)}"
        for s in product.get("sections", [])
    )
    base = "::".join([
        _normalize(product.get("title", "")),
        product.get("product_family", ""),
        product.get("niche", ""),
        product.get("product_subtype", ""),
        section_sig,
    ])
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]


def _is_duplicate(product: dict, recent_history: list[dict]) -> tuple[bool, str]:
    normalized_title = _normalize(product.get("title", ""))
    section_set = {_normalize(s.get("heading", "")) for s in product.get("sections", []) if s.get("heading")}

    for item in recent_history:
        if normalized_title and normalized_title == _normalize(item.get("title", "")):
            return True, "title match"
        if product.get("fingerprint") and product.get("fingerprint") == item.get("fingerprint"):
            return True, "fingerprint match"

    recent = recent_history[-RECENT_DUPLICATE_WINDOW:]
    for item in recent:
        if (
            item.get("product_family") == product.get("product_family")
            and item.get("niche") == product.get("niche")
            and item.get("product_subtype") == product.get("product_subtype")
        ):
            return True, "family+niche+subtype recently used"

        prev_sections = {_normalize(s) for s in item.get("section_headings", []) if s}
        if section_set and prev_sections:
            overlap = len(section_set & prev_sections) / max(len(section_set), len(prev_sections))
            if overlap >= 0.75:
                return True, "section overlap too high"

    return False, ""


def _novelty_score(product: dict, recent_history: list[dict]) -> int:
    score = 100
    recent = recent_history[-RECENT_DUPLICATE_WINDOW:]
    for item in recent:
        if item.get("product_family") == product.get("product_family"):
            score -= 4
        if item.get("niche") == product.get("niche"):
            score -= 3
        if item.get("product_subtype") == product.get("product_subtype"):
            score -= 5
    return max(0, score)


def _generate_product_from_ai(plan: dict, palette: dict, exclusions: dict) -> dict:
    prompt = f"""Generate a digital product concept for Etsy.

Product family: {plan['product_family']}
Product subtype: {plan['product_subtype']}
Niche: {plan['niche']}
Color palette: {palette['name']}

IMPORTANT:
- Do NOT generate presentation/slide deck products.
- Build a bundle-level product, not a one-page printable.
- Must be materially different from recent products.
- Avoid title or section similarities to these recent titles: {exclusions['recent_titles']}
- Avoid repeating these recent combinations: {exclusions['recent_combos']}
- Avoid these recent section headings: {exclusions['recent_sections']}

Return a JSON object with:
- "title": catchy product name (max 70 chars)
- "subtitle": short tagline (max 50 chars)
- "description": what this product helps with (2-3 sentences)
- "sections": array of 8-14 section objects, each with:
  - "heading": section title
  - "type": one of "lined", "grid", "checklist", "table", "blank"
  - "rows": number of rows (6-24)
  - "columns": number of columns (1-4, only for grid/table)
  - "column_headers": array of header strings (only for table type)
- "target_audience": who buys this
- "use_case": when/how they use it
- "deliverables": list of what is included (e.g. guide + worksheets + trackers)

Return ONLY valid JSON, no markdown."""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=1.0,
        max_tokens=1400,
    )

    product = _extract_json(response.choices[0].message.content)
    product["niche"] = plan["niche"]
    product["product_family"] = plan["product_family"]
    product["product_subtype"] = plan["product_subtype"]
    product["product_type"] = plan["product_subtype"]
    product["palette"] = palette
    product["fingerprint"] = _fingerprint(product)

    return product


def generate_product_idea(niche: str | None = None, recent_history: list[dict] | None = None) -> dict:
    """Generate a novel product idea with deduplication and retries."""
    history = recent_history or []
    exclusions = _build_exclusions(history)
    palette = random.choice(COLOR_PALETTES)

    last_product = None
    last_reason = ""

    for _ in range(IDEA_RETRY_LIMIT):
        plan = _choose_product_plan(history, niche)
        product = _generate_product_from_ai(plan, palette, exclusions)
        is_dup, reason = _is_duplicate(product, history)
        if not is_dup:
            product["novelty_score"] = _novelty_score(product, history)
            product["dedupe_retry_count"] = _
            return product

        last_product = product
        last_reason = reason

    if not last_product:
        raise RuntimeError("Failed to generate product idea")

    # Fallback: force a unique title variant if retries are exhausted.
    suffix = random.randint(100, 999)
    last_product["title"] = f"{last_product['title']} Vol. {suffix}"
    last_product["fingerprint"] = _fingerprint(last_product)
    last_product["novelty_score"] = _novelty_score(last_product, history)
    last_product["dedupe_retry_count"] = IDEA_RETRY_LIMIT
    last_product["dedupe_fallback_reason"] = last_reason
    return last_product


def _ensure_ai_disclosure(description: str) -> str:
    if AI_DISCLOSURE.lower() in description.lower():
        return description
    return f"{description.strip()}\n\nAI DISCLOSURE\n{AI_DISCLOSURE}"


def generate_etsy_listing(product: dict) -> dict:
    """Generate optimized Etsy listing copy for a product."""
    prompt = f"""Create an Etsy listing for this digital printable product:

Product: {product['title']}
Description: {product['description']}
Target audience: {product['target_audience']}
Use case: {product['use_case']}
Niche: {product['niche']}

Include a clear AI transparency statement in the description.

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

    listing = _extract_json(content)
    listing["description"] = _ensure_ai_disclosure(listing.get("description", ""))
    return listing


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
