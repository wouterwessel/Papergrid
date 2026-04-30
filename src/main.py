"""Main orchestrator - generates products, listings, and pins."""

import json
import random
import sys
from datetime import datetime
from pathlib import Path

from src.config import OUTPUT_DIR, PRODUCTS_PER_RUN, HISTORY_FILE, MAX_HISTORY_ITEMS
from src.generator.product_ideas import (
    generate_product_idea,
    generate_etsy_listing,
    generate_pinterest_copy,
)
from src.generator.pdf_builder import create_product_pdf
from src.listing.etsy_copy import save_listing, generate_bulk_csv
from src.pinterest.pin_creator import create_pin_image
from src.pinterest.api import post_pin


def run(dry_run: bool = False, niche: str | None = None):
    """Run the full product generation pipeline."""
    # Create dated output directory
    today = datetime.now().strftime("%Y-%m-%d")
    week_num = datetime.now().strftime("%W")
    day_dir = OUTPUT_DIR / f"week-{week_num}" / today
    day_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== Passive Income Generator ===")
    print(f"Output: {day_dir}")
    print(f"Products to generate: {PRODUCTS_PER_RUN}")
    print(f"Dry run: {dry_run}")
    print()

    history = _load_history()
    generated = []

    for i in range(PRODUCTS_PER_RUN):
        print(f"--- Product {i + 1}/{PRODUCTS_PER_RUN} ---")

        # Step 1: Generate product idea
        print("[1/5] Generating product idea...")
        if dry_run:
            product = _dummy_product(i)
        else:
            try:
                product = generate_product_idea(niche=niche, recent_history=history)
            except Exception as exc:  # noqa: BLE001
                print(f"  -> Product generation failed, using fallback template: {exc}")
                product = _dummy_product(i)
        print(f"  -> {product['title']}")

        # Step 2: Create PDF
        print("[2/5] Creating PDF...")
        pdf_path = create_product_pdf(product, day_dir, page_format="A4")
        # Also create Letter size
        pdf_letter = create_product_pdf(product, day_dir, page_format="Letter")
        print(f"  -> {pdf_path.name}")

        # Step 3: Generate Etsy listing
        print("[3/5] Generating Etsy listing...")
        if dry_run:
            listing = _dummy_listing(product)
        else:
            try:
                listing = generate_etsy_listing(product)
            except Exception as exc:  # noqa: BLE001
                print(f"  -> Etsy listing generation failed, using fallback listing: {exc}")
                listing = _dummy_listing(product)
        listing_path = save_listing(product, listing, day_dir)
        print(f"  -> {listing_path.name}")

        # Step 4: Create Pinterest pin image
        print("[4/5] Creating Pinterest pin image...")
        pin_image_path = create_pin_image(product, day_dir)
        print(f"  -> {pin_image_path.name}")

        # Step 5: Post to Pinterest
        print("[5/5] Posting to Pinterest...")
        if dry_run:
            print("  -> [DRY RUN] Skipping Pinterest post")
            pin_result = None
        else:
            try:
                pinterest_copy = generate_pinterest_copy(product)
                pin_result = post_pin(
                    image_path=pin_image_path,
                    title=pinterest_copy.get("pin_title", product["title"]),
                    description=pinterest_copy.get("pin_description", product.get("description", "")),
                    board_name=pinterest_copy.get("board_name", "Digital Planners"),
                )
            except Exception as exc:  # noqa: BLE001
                print(f"  -> Pinterest post failed, continuing without posting: {exc}")
                pin_result = None

        generated.append({
            "title": product["title"],
            "product_family": product.get("product_family", ""),
            "product_subtype": product.get("product_subtype", ""),
            "niche": product.get("niche", ""),
            "fingerprint": product.get("fingerprint", ""),
            "novelty_score": product.get("novelty_score", 0),
            "dedupe_retry_count": product.get("dedupe_retry_count", 0),
            "pdf": str(pdf_path),
            "listing": str(listing_path),
            "pin_image": str(pin_image_path),
            "pinterest_posted": pin_result is not None,
        })

        history.append(_history_entry(product))

        print()

    # Generate weekly bulk CSV if there are listings
    week_dir = day_dir.parent
    csv_path = generate_bulk_csv(week_dir, week_dir / "etsy_bulk_upload.csv")
    # Also check subdirectories
    all_listings = list(week_dir.rglob("*_listing.json"))
    if all_listings:
        _generate_combined_csv(all_listings, week_dir / "etsy_bulk_upload.csv")

    print(f"=== Done! Generated {len(generated)} product(s) ===")
    print(f"Bulk CSV: {week_dir / 'etsy_bulk_upload.csv'}")

    # Save manifest
    manifest_path = day_dir / "manifest.json"
    manifest_path.write_text(json.dumps(generated, indent=2), encoding="utf-8")
    _save_history(history)

    return generated


def _load_history() -> list[dict]:
    """Load persistent product history for deduplication."""
    if not HISTORY_FILE.exists():
        return []

    try:
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def _save_history(history: list[dict]):
    """Save bounded product history list."""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    trimmed = history[-MAX_HISTORY_ITEMS:]
    HISTORY_FILE.write_text(json.dumps(trimmed, indent=2), encoding="utf-8")


def _history_entry(product: dict) -> dict:
    """Extract deduplication metadata from generated product."""
    return {
        "created_at": datetime.now().isoformat(),
        "title": product.get("title", ""),
        "niche": product.get("niche", ""),
        "product_family": product.get("product_family", ""),
        "product_subtype": product.get("product_subtype", ""),
        "product_type": product.get("product_type", ""),
        "fingerprint": product.get("fingerprint", ""),
        "novelty_score": product.get("novelty_score", 0),
        "section_headings": [s.get("heading", "") for s in product.get("sections", [])],
        "target_audience": product.get("target_audience", ""),
        "use_case": product.get("use_case", ""),
    }


def _generate_combined_csv(listing_files: list[Path], output_path: Path):
    """Generate a combined CSV from listing files across subdirectories."""
    import csv

    listings = []
    for f in listing_files:
        data = json.loads(f.read_text(encoding="utf-8"))
        listings.append(data)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        headers = [
            "Title", "Description", "Price", "Quantity", "Tags",
            "Materials", "Type", "Who Made", "When Made", "Category",
            "Renewal", "Language",
        ]
        writer.writerow(headers)
        for listing in listings:
            tags = ",".join(listing["tags"][:13])
            writer.writerow([
                listing["etsy_title"],
                listing["description"],
                listing["price"],
                999,
                tags,
                "",
                "digital",
                "i_did",
                "2020_2026",
                listing.get("category", ""),
                "automatic",
                "en",
            ])


def _dummy_product(index: int = 0) -> dict:
    """Generate a dummy product for dry-run testing."""
    variants = [
        ("Printable System", "weekly planner system", "productivity"),
        ("Guide Workbook", "step-by-step action guide", "small-business"),
        ("Starter Kit", "job search starter kit", "career"),
        ("Business System", "content planning system", "small-business"),
    ]
    label, subtype, niche = variants[index % len(variants)]
    suffix = random.randint(100, 999)

    return {
        "title": f"{label} Pack {suffix}",
        "subtitle": "Premium toolkit for fast implementation",
        "description": "A practical bundle with guided pages, trackers, and actionable worksheets.",
        "sections": [
            {"heading": "Weekly Goals", "type": "checklist", "rows": 5},
            {"heading": "Daily Schedule", "type": "table", "rows": 7,
             "columns": 4, "column_headers": ["Time", "Task", "Priority", "Done"]},
            {"heading": "Notes", "type": "lined", "rows": 8},
            {"heading": "Habit Tracker", "type": "grid", "rows": 4, "columns": 7},
            {"heading": "Reflection", "type": "blank", "rows": 6},
            {"heading": "Action Plan", "type": "table", "rows": 8,
             "columns": 3, "column_headers": ["Step", "Owner", "Deadline"]},
            {"heading": "Weekly Review", "type": "lined", "rows": 10},
            {"heading": "Priority Backlog", "type": "checklist", "rows": 12},
        ],
        "target_audience": "Busy professionals and creators",
        "use_case": "Planning, execution, and weekly review",
        "niche": niche,
        "product_family": label.lower().replace(" ", "_"),
        "product_subtype": subtype,
        "product_type": subtype,
        "fingerprint": f"dryrun-{suffix}",
        "novelty_score": 100,
        "dedupe_retry_count": 0,
        "palette": {
            "name": "Minimal",
            "primary": "#2C3E50",
            "secondary": "#ECF0F1",
            "accent": "#3498DB",
        },
    }


def _dummy_listing(product: dict) -> dict:
    """Generate a dummy listing for dry-run testing."""
    return {
        "etsy_title": f"{product['title']} | Printable PDF | Instant Download | A4 & Letter",
        "description": f"Stay organized with this beautiful {product['title'].lower()}.\n\n"
                       "WHAT'S INCLUDED:\n- 1 PDF file (A4 size)\n- 1 PDF file (Letter size)\n\n"
                       "HOW TO USE:\n1. Purchase and download\n2. Print at home or at a print shop\n3. Start planning!\n\n"
                   "FEATURES:\n- Clean, minimal design\n- Printer-friendly\n- Instant download\n\n"
                   "AI DISCLOSURE\n"
                   "This digital product was created with AI assistance and then reviewed, curated, and formatted by the shop owner.",
        "tags": ["planner", "printable", "productivity", "weekly planner", "digital download",
                 "pdf planner", "minimalist", "organizer", "to do list", "goal planner",
                 "instant download", "A4 planner", "print at home"],
        "price": 4.99,
        "category": "Paper & Party Supplies > Paper > Calendars & Planners",
    }


def main():
    """CLI entry point."""
    dry_run = "--dry-run" in sys.argv
    niche = None
    for arg in sys.argv[1:]:
        if arg.startswith("--niche="):
            niche = arg.split("=", 1)[1]

    run(dry_run=dry_run, niche=niche)


if __name__ == "__main__":
    main()
