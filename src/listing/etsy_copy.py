"""Etsy listing generator - creates listing copy and bulk CSV."""

import csv
import json
from pathlib import Path
from datetime import datetime


def save_listing(product: dict, listing: dict, output_dir: Path) -> Path:
    """Save individual listing data as JSON."""
    safe_name = "".join(c if c.isalnum() or c in " -_" else "" for c in product["title"])
    safe_name = safe_name.strip().replace(" ", "_")[:50]

    listing_data = {
        "product_title": product["title"],
        "etsy_title": listing["etsy_title"],
        "description": listing["description"],
        "tags": listing["tags"],
        "price": listing["price"],
        "category": listing.get("category", ""),
        "generated_at": datetime.now().isoformat(),
    }

    output_path = output_dir / f"{safe_name}_listing.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(listing_data, indent=2, ensure_ascii=False), encoding="utf-8")

    return output_path


def generate_bulk_csv(listings_dir: Path, output_path: Path) -> Path:
    """Generate Etsy bulk upload CSV from all listing JSONs in a directory."""
    listings = []
    for json_file in sorted(listings_dir.glob("*_listing.json")):
        data = json.loads(json_file.read_text(encoding="utf-8"))
        listings.append(data)

    if not listings:
        return output_path

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Etsy CSV headers
        headers = [
            "Title",
            "Description",
            "Price",
            "Quantity",
            "Tags",
            "Materials",
            "Type",
            "Who Made",
            "When Made",
            "Category",
            "Renewal",
            "Language",
        ]
        writer.writerow(headers)

        for listing in listings:
            tags = ",".join(listing["tags"][:13])
            row = [
                listing["etsy_title"],
                listing["description"],
                listing["price"],
                999,  # Digital = unlimited
                tags,
                "",  # Materials (N/A for digital)
                "digital",
                "i_did",
                "2020_2026",
                listing.get("category", ""),
                "automatic",
                "en",
            ]
            writer.writerow(row)

    return output_path
