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
    MIN_SECTION_COUNT,
    MIN_GUIDE_CHAPTERS,
    MIN_CHAPTER_WORDS,
    LAUNCH_PRICE_MIN,
    LAUNCH_PRICE_MAX,
    QUALITY_MODE,
)


client = OpenAI(api_key=OPENAI_API_KEY)

AI_DISCLOSURE = (
    "This digital product was created with AI assistance and then reviewed, "
    "curated, and formatted by the shop owner."
)

CONTENT_HEAVY_FAMILIES = {"guide_workbook", "starter_kit", "business_system"}

def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", "", text.lower())).strip()


def _extract_json(content: str) -> dict:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1]
        cleaned = cleaned.rsplit("```", 1)[0]
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Fallback for model responses that wrap JSON with extra text.
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(cleaned[start:end + 1])
        raise


def _chat_json(prompt: str, *, temperature: float, max_tokens: int, retries: int = 3) -> dict:
    last_error = None
    for _ in range(retries):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content or "{}"
            return _extract_json(content)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
    if last_error:
        raise last_error
    raise RuntimeError("AI call failed without a specific error")


def _weighted_pick(options: list[str], counts: dict[str, int]) -> str:
    weights = [1.0 / (1 + counts.get(opt, 0)) for opt in options]
    return random.choices(options, weights=weights, k=1)[0]


def _weighted_pick_with_priority(
    options: list[str],
    counts: dict[str, int],
    priority_weights: dict[str, float],
) -> str:
    weights = []
    for opt in options:
        base = 1.0 / (1 + counts.get(opt, 0))
        weights.append(base * priority_weights.get(opt, 1.0))
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

    family_priority = {
        "guide_workbook": 2.2,
        "starter_kit": 1.7,
        "business_system": 1.5,
        "printable_bundle": 1.0,
    }
    if QUALITY_MODE == "strict":
        family = _weighted_pick_with_priority(list(PRODUCT_FAMILIES.keys()), family_counts, family_priority)
    else:
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
    chapter_sig = "|".join(
        _normalize(chapter.get("heading", ""))
        for chapter in product.get("chapters", [])
    )
    section_sig = "|".join(
        f"{_normalize(s.get('heading', ''))}:{s.get('type', '')}:{s.get('rows', 0)}:{s.get('columns', 0)}"
        for s in product.get("sections", [])
    )
    base = "::".join([
        _normalize(product.get("title", "")),
        product.get("product_family", ""),
        product.get("niche", ""),
        product.get("product_subtype", ""),
        chapter_sig,
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


def _chapter_word_count(chapter: dict) -> int:
    paragraphs = chapter.get("body_paragraphs", [])
    text = " ".join(paragraphs)
    text = f"{chapter.get('objective', '')} {chapter.get('example', '')} {text}".strip()
    return len(text.split())


def _quality_score(product: dict) -> tuple[int, list[str]]:
    notes: list[str] = []
    score = 100

    sections = product.get("sections", [])
    if len(sections) < MIN_SECTION_COUNT:
        score -= 28
        notes.append(f"too few sections ({len(sections)})")

    if product.get("product_family") in CONTENT_HEAVY_FAMILIES:
        chapters = product.get("chapters", [])
        if len(chapters) < MIN_GUIDE_CHAPTERS:
            score -= 35
            notes.append(f"too few chapters ({len(chapters)})")
        for chapter in chapters:
            wc = _chapter_word_count(chapter)
            if wc < MIN_CHAPTER_WORDS:
                score -= 9
                notes.append(f"short chapter: {chapter.get('heading', 'untitled')}")
            if len(chapter.get("key_takeaways", [])) < 3:
                score -= 4
                notes.append(f"weak takeaways: {chapter.get('heading', 'untitled')}")

    if len(product.get("deliverables", [])) < 4:
        score -= 10
        notes.append("deliverables list too short")

    return max(0, score), notes


def _passes_quality_gate(product: dict) -> tuple[bool, int, list[str]]:
    score, notes = _quality_score(product)
    threshold = 80 if QUALITY_MODE == "strict" else 65
    return score >= threshold, score, notes


def _normalize_product_schema(product: dict) -> dict:
    # Keep one canonical section list for PDF rendering.
    if not product.get("sections") and product.get("worksheets"):
        product["sections"] = product["worksheets"]

    normalized_sections = []
    for section in product.get("sections", []):
        normalized = {
            "heading": section.get("heading", "Worksheet"),
            "type": section.get("type", "lined"),
            "rows": int(section.get("rows", 10)),
        }
        if normalized["type"] in {"grid", "table"}:
            normalized["columns"] = max(1, int(section.get("columns", 2)))
        if normalized["type"] == "table":
            normalized["column_headers"] = section.get("column_headers", ["Item", "Notes", "Status"])
        normalized_sections.append(normalized)

    product["sections"] = normalized_sections
    product.setdefault("chapters", [])
    product.setdefault("guide_intro", "")
    product.setdefault("deliverables", [])
    return product


def _build_generation_prompt(plan: dict, palette: dict, exclusions: dict) -> str:
    common_intro = f"""Generate a digital product concept for Etsy.

Product family: {plan['product_family']}
Product subtype: {plan['product_subtype']}
Niche: {plan['niche']}
Color palette: {palette['name']}

IMPORTANT:
- Do NOT generate presentation/slide deck products.
- Must be materially different from recent products.
- Avoid title or section similarities to these recent titles: {exclusions['recent_titles']}
- Avoid repeating these recent combinations: {exclusions['recent_combos']}
- Avoid these recent section headings: {exclusions['recent_sections']}
- Write commercially strong but useful content. No vague fluff.
"""

    if plan["product_family"] in CONTENT_HEAVY_FAMILIES:
        return common_intro + """
Return ONLY valid JSON with this exact schema:
- "title": strong benefit-driven title (max 70 chars)
- "subtitle": premium commercial tagline (max 60 chars)
- "description": 3-4 sentence value summary with clear outcome
- "target_audience": specific buyer profile
- "use_case": when/how buyers apply it
- "buyer_outcome": one sentence transformation promise
- "guide_intro": 2 short paragraphs introducing the method and expected results
- "chapters": array with 4-7 chapters, each containing:
  - "heading"
  - "objective" (1-2 sentences)
  - "body_paragraphs" (3-5 paragraphs, each ~70-110 words)
  - "example" (practical concrete example)
  - "key_takeaways" (array of exactly 3 concise bullet strings)
- "worksheets": array of 8-12 worksheet sections with:
  - "heading"
  - "type" one of "lined", "grid", "checklist", "table", "blank"
  - "rows" (8-26)
  - "columns" (1-4 for grid/table)
  - "column_headers" for tables only
- "sections": same array as worksheets
- "deliverables": array of 5-10 included files/features

Return ONLY JSON, no markdown.
"""

    return common_intro + """
Return ONLY valid JSON with this exact schema:
- "title": strong benefit-driven title (max 70 chars)
- "subtitle": premium commercial tagline (max 60 chars)
- "description": 3-4 sentence value summary with clear outcome
- "target_audience": specific buyer profile
- "use_case": when/how buyers apply it
- "sections": array of 10-16 functional planner sections with:
  - "heading"
  - "type" one of "lined", "grid", "checklist", "table", "blank"
  - "rows" (8-26)
  - "columns" (1-4 for grid/table)
  - "column_headers" for tables only
- "deliverables": array of 5-10 included files/features

Return ONLY JSON, no markdown.
"""


def _generate_product_from_ai(plan: dict, palette: dict, exclusions: dict) -> dict:
    prompt = _build_generation_prompt(plan, palette, exclusions)

    product = _chat_json(prompt, temperature=1.0, max_tokens=1400)
    product["niche"] = plan["niche"]
    product["product_family"] = plan["product_family"]
    product["product_subtype"] = plan["product_subtype"]
    product["product_type"] = plan["product_subtype"]
    product["palette"] = palette
    product = _normalize_product_schema(product)
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
        passed_quality, quality_score, quality_notes = _passes_quality_gate(product)
        if not is_dup:
            if passed_quality:
                product["novelty_score"] = _novelty_score(product, history)
                product["quality_score"] = quality_score
                product["quality_notes"] = quality_notes
                product["dedupe_retry_count"] = _
                return product
            last_reason = f"quality gate: {'; '.join(quality_notes)}"
            last_product = product
            continue

        last_product = product
        last_reason = reason

    if not last_product:
        raise RuntimeError("Failed to generate product idea")

    # Fallback: force a unique title variant if retries are exhausted.
    suffix = random.randint(100, 999)
    last_product["title"] = f"{last_product['title']} Vol. {suffix}"
    last_product["fingerprint"] = _fingerprint(last_product)
    last_product["novelty_score"] = _novelty_score(last_product, history)
    quality_score, quality_notes = _quality_score(last_product)
    last_product["quality_score"] = quality_score
    last_product["quality_notes"] = quality_notes
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
Goal: maximize first sales while keeping premium perceived value.

Return a JSON object with:
- "etsy_title": SEO-optimized title (max 140 chars, include keywords buyers search for)
- "description": full Etsy description (450-700 words) with sections: Outcome Promise, What's Included, How To Use, Who It's For, and Notes.
- "tags": array of exactly 13 tags (each max 20 chars, mix of broad and specific keywords)
- "price": suggested launch price in USD (between 4.99 and 8.99)
- "category": best Etsy category path

Return ONLY valid JSON, no markdown."""

    listing = _chat_json(prompt, temperature=0.7, max_tokens=1500)
    listing["description"] = _ensure_ai_disclosure(listing.get("description", ""))
    try:
        suggested = float(listing.get("price", LAUNCH_PRICE_MIN))
    except (TypeError, ValueError):
        suggested = LAUNCH_PRICE_MIN
    listing["price"] = round(min(max(suggested, LAUNCH_PRICE_MIN), LAUNCH_PRICE_MAX), 2)

    tags = listing.get("tags", [])
    if not isinstance(tags, list):
        tags = []
    cleaned_tags = []
    for tag in tags:
        t = str(tag).strip()[:20]
        if t and t.lower() not in {x.lower() for x in cleaned_tags}:
            cleaned_tags.append(t)
    fallback_tags = [
        "digital workbook", "printable guide", "instant download", "planner bundle",
        "self improvement", "business planner", "goal setting", "productivity tool",
        "workbook pdf", "action planner", "organization kit", "print at home", "A4 letter"
    ]
    for tag in fallback_tags:
        if len(cleaned_tags) >= 13:
            break
        if tag.lower() not in {x.lower() for x in cleaned_tags}:
            cleaned_tags.append(tag[:20])
    listing["tags"] = cleaned_tags[:13]
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

    return _chat_json(prompt, temperature=0.7, max_tokens=500)
