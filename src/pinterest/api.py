"""Pinterest API integration for automatic pin posting."""

import httpx
from pathlib import Path

from src.config import PINTEREST_ACCESS_TOKEN

BASE_URL = "https://api.pinterest.com/v5"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {PINTEREST_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }


def get_boards() -> list[dict]:
    """Get all boards for the authenticated user."""
    response = httpx.get(f"{BASE_URL}/boards", headers=_headers(), timeout=30)
    response.raise_for_status()
    return response.json().get("items", [])


def find_or_create_board(board_name: str) -> str:
    """Find existing board by name, or create it. Returns board ID."""
    boards = get_boards()
    for board in boards:
        if board["name"].lower() == board_name.lower():
            return board["id"]

    # Create new board
    response = httpx.post(
        f"{BASE_URL}/boards",
        headers=_headers(),
        json={"name": board_name, "privacy": "PUBLIC"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["id"]


def upload_pin_image(image_path: Path) -> str:
    """Upload an image to Pinterest media. Returns media ID."""
    # Register media upload
    response = httpx.post(
        f"{BASE_URL}/media",
        headers=_headers(),
        json={"media_type": "image"},
        timeout=30,
    )
    response.raise_for_status()
    upload_data = response.json()

    # Upload to the provided URL
    upload_url = upload_data["upload_url"]
    upload_params = upload_data.get("upload_parameters", {})

    with open(image_path, "rb") as f:
        files = {"file": (image_path.name, f, "image/png")}
        upload_response = httpx.post(
            upload_url,
            data=upload_params,
            files=files,
            timeout=60,
        )
        upload_response.raise_for_status()

    return upload_data["media_id"]


def create_pin(
    board_id: str,
    title: str,
    description: str,
    image_path: Path,
    link: str | None = None,
) -> dict:
    """Create a pin on Pinterest with an image.

    Uses direct image upload via base64 for simplicity.
    """
    import base64

    image_data = image_path.read_bytes()
    image_b64 = base64.b64encode(image_data).decode("utf-8")

    pin_data = {
        "board_id": board_id,
        "title": title[:100],
        "description": description[:500],
        "media_source": {
            "source_type": "image_base64",
            "content_type": "image/png",
            "data": image_b64,
        },
    }

    if link:
        pin_data["link"] = link

    response = httpx.post(
        f"{BASE_URL}/pins",
        headers=_headers(),
        json=pin_data,
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def post_pin(
    image_path: Path,
    title: str,
    description: str,
    board_name: str,
    link: str | None = None,
) -> dict | None:
    """High-level: post a pin to a board (creates board if needed).

    Returns pin data on success, None if Pinterest is not configured.
    """
    if not PINTEREST_ACCESS_TOKEN:
        print("[Pinterest] No access token configured, skipping pin posting.")
        return None

    board_id = find_or_create_board(board_name)
    result = create_pin(
        board_id=board_id,
        title=title,
        description=description,
        image_path=image_path,
        link=link,
    )
    print(f"[Pinterest] Pin created: {result.get('id', 'unknown')}")
    return result
