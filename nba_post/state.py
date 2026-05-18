"""Track which game_ids have already been generated, to prevent duplicates."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE_DIR = ROOT / ".posted"
STATE_PATH = STATE_DIR / "posted.json"


def _read() -> dict:
    if not STATE_PATH.exists():
        return {"games": {}}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"games": {}}


def _write(data: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def is_posted(game_id: str) -> bool:
    return game_id in _read().get("games", {})


def mark_posted(game_id: str, fb_post_id: str | None = None) -> None:
    data = _read()
    data.setdefault("games", {})[game_id] = {
        "posted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "fb_post_id": fb_post_id,
    }
    _write(data)
