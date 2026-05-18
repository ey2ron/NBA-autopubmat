"""Facebook page publisher — real Graph API post, with a dry-run mode."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import requests

GRAPH_BASE = "https://graph.facebook.com"


def _endpoint(api_version: str, page_id: str) -> str:
    return f"{GRAPH_BASE}/{api_version}/{page_id}/photos"


def publish_live(
    caption: str,
    image_path: Path,
    page_id: str,
    access_token: str,
    api_version: str = "v19.0",
) -> dict[str, Any]:
    """POST the image + caption to the Facebook Page. Raises on HTTP error."""
    url = _endpoint(api_version, page_id)
    with open(image_path, "rb") as fh:
        files = {"source": (image_path.name, fh, "image/png")}
        data = {
            "caption": caption,
            "published": "true",
            "access_token": access_token,
        }
        r = requests.post(url, files=files, data=data, timeout=60)
    if r.status_code >= 400:
        try:
            err = r.json()
        except ValueError:
            err = {"raw": r.text}
        raise RuntimeError(f"Facebook Graph API error ({r.status_code}): {err}")
    return r.json()


def publish_dry_run(
    caption: str,
    image_path: Path,
    game_id: str,
    page_id: str,
    api_version: str = "v19.0",
    output_dir: Path | None = None,
) -> dict[str, Any]:
    """Write the would-be payload to disk; do not call the Graph API."""
    output_dir = output_dir or image_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    payload_path = output_dir / f"{game_id}.post.json"
    payload = {
        "mode": "DRY_RUN",
        "would_call": f"POST {_endpoint(api_version, page_id)}",
        "form_fields": {"caption": caption, "published": True},
        "file_field": {"source": str(image_path)},
    }
    payload_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print("─" * 60)
    print("[DRY RUN] Would post to Facebook page")
    print(f"  page_id : {page_id}")
    print(f"  image   : {image_path}")
    print(f"  payload : {payload_path}")
    print("  caption :")
    for line in caption.splitlines():
        print(f"    {line}")
    print("─" * 60)
    return payload


def publish(
    caption: str,
    image_path: Path,
    game_id: str,
    page_id: str,
    access_token: str = "",
    api_version: str = "v19.0",
    dry_run: bool = False,
) -> dict[str, Any]:
    if dry_run or not access_token:
        return publish_dry_run(caption, image_path, game_id, page_id, api_version)
    print(f"Posting to Facebook page {page_id}…")
    result = publish_live(caption, image_path, page_id, access_token, api_version)
    print(f"[OK] Post created: id={result.get('post_id') or result.get('id')}")
    return result
