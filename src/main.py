"""Main orchestrator - generates products, listings, and pins."""

import json
import sys
from datetime import datetime
from pathlib import Path

from src.config import OUTPUT_DIR, PRODUCTS_PER_RUN, NICHES
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

    generated = []

    for i in range(PRODUCTS_PER_RUN):
        print(f"--- Product {i + 1}/{PRODUCTS_PER_RUN} ---")

        # Step 1: Generate product idea
        print("[1/5] Generating product idea...")
        if dry_run:
            product = _dummy_product()
        else:
            product = generate_product_idea(niche=niche)
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
            listing = generate_etsy_listing(product)
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
            pinterest_copy = generate_pinterest_copy(product)
            pin_result = post_pin(
                image_path=pin_image_path,
                title=pinterest_copy["pin_title"],
                description=pinterest_copy["pin_description"],
                board_name=pinterest_copy.get("board_name", "Digital Planners"),
            )

        generated.append({
            "title": product["title"],
            "pdf": str(pdf_path),
            "listing": str(listing_path),
            "pin_image": str(pin_image_path),
            "pinterest_posted": pin_result is not None,
        })

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

    return generated


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


def _dummy_product() -> dict:
    """Generate a dummy product for dry-run testing."""
    return {
        "title": "Weekly Productivity Planner",
        "subtitle": "Plan your week with intention",
        "description": "A comprehensive weekly planner to boost productivity.",
        "sections": [
            {"heading": "Weekly Goals", "type": "checklist", "rows": 5},
            {"heading": "Daily Schedule", "type": "table", "rows": 7,
             "columns": 4, "column_headers": ["Time", "Task", "Priority", "Done"]},
            {"heading": "Notes", "type": "lined", "rows": 8},
            {"heading": "Habit Tracker", "type": "grid", "rows": 4, "columns": 7},
            {"heading": "Reflection", "type": "blank", "rows": 6},
        ],
        "target_audience": "Busy professionals and students",
        "use_case": "Weekly planning and goal setting",
        "niche": "productivity",
        "product_type": "weekly planner",
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
                       "FEATURES:\n- Clean, minimal design\n- Printer-friendly\n- Instant download",
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
