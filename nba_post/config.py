"""Load runtime config from config.json (no third-party deps)."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.json"


@dataclass
class Config:
    team_abbrev: str
    post_all_finished_games: bool


def load() -> Config:
    if CONFIG_PATH.exists():
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    else:
        data = {}

    return Config(
        team_abbrev=str(data.get("team_abbrev", "TOR")).upper(),
        post_all_finished_games=bool(data.get("post_all_finished_games", False)),
    )
