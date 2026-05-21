"""ESPN scoreboard + box-score fetchers."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import requests

SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
SUMMARY_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary"
TIMEOUT = 15


@dataclass
class Team:
    team_id: str
    name: str
    short_name: str
    abbrev: str
    score: int
    logo_url: str
    is_home: bool
    is_winner: bool
    color: str = "#1d428a"        
    alt_color: str = "#c9082a"    
    series_wins: int | None = None


@dataclass
class Game:
    game_id: str
    home: Team
    away: Team
    header: str           
    game_label: str       
    series_summary: str   

    @property
    def winner(self) -> Team:
        return self.home if self.home.is_winner else self.away

    @property
    def loser(self) -> Team:
        return self.away if self.home.is_winner else self.home


def _parse_game(event: dict[str, Any]) -> Game:
    comp = event["competitions"][0]
    competitors = comp["competitors"]

    # ESPN orders [home, away] OR [away, home]; use the explicit homeAway field.
    home_raw = next(c for c in competitors if c["homeAway"] == "home")
    away_raw = next(c for c in competitors if c["homeAway"] == "away")

    series = comp.get("series") or {}
    series_competitors = series.get("competitors") or []
    series_wins_by_id = {sc["id"]: sc.get("wins", 0) for sc in series_competitors}

    def to_team(raw: dict[str, Any], is_home: bool) -> Team:
        t = raw["team"]
        score = int(raw.get("score", 0) or 0)
        return Team(
            team_id=t["id"],
            name=t.get("displayName", t.get("name", "")),
            short_name=t.get("shortDisplayName", t.get("name", "")),
            abbrev=t.get("abbreviation", "").upper(),
            score=score,
            logo_url=t.get("logo") or _fallback_logo(t.get("abbreviation", "")),
            is_home=is_home,
            is_winner=bool(raw.get("winner", False)),
            color=_normalize_hex(t.get("color"), "#1d428a"),
            alt_color=_normalize_hex(t.get("alternateColor"), "#c9082a"),
            series_wins=series_wins_by_id.get(t["id"]),
        )

    home = to_team(home_raw, True)
    away = to_team(away_raw, False)

    # If neither side is flagged as winner (rare), fall back to score comparison.
    if not (home.is_winner or away.is_winner):
        if home.score != away.score:
            home.is_winner = home.score > away.score
            away.is_winner = not home.is_winner

    header, game_label = _derive_header(event, comp, series)

    return Game(
        game_id=str(event["id"]),
        home=home,
        away=away,
        header=header,
        game_label=game_label,
        series_summary=series.get("summary", ""),
    )


def _derive_header(event: dict, comp: dict, series: dict) -> tuple[str, str]:
    notes = comp.get("notes") or event.get("notes") or []
    header_text = ""
    for n in notes:
        text = (n.get("headline") or "").strip()
        if text:
            header_text = text.upper()
            break

    game_label = ""
    if series:
        # For a completed playoff game, ESPN's series.competitors[*].wins are
        # already updated to reflect the result, so the game number is the
        # current sum of wins (not sum+1).
        wins = [c.get("wins", 0) for c in (series.get("competitors") or [])]
        if wins:
            game_label = f"GAME {sum(wins)}"

    # Avoid duplication when the note headline already says "Game N"
    # (e.g. "NBA Finals - Game 1") and we'd otherwise append " · GAME 1".
    if game_label and "game" in header_text.lower():
        game_label = ""

    if not header_text:
        season_type = (event.get("season") or {}).get("slug", "")
        header_text = {
            "regular-season": "REGULAR SEASON",
            "post-season": "PLAYOFFS",
            "preseason": "PRESEASON",
        }.get(season_type, "")

    return header_text, game_label


def _normalize_hex(color: str | None, fallback: str) -> str:
    """ESPN gives hex without '#'. Coerce to '#rrggbb', else return fallback."""
    if not color:
        return fallback
    c = color.strip().lstrip("#")
    if len(c) == 6 and all(ch in "0123456789abcdefABCDEF" for ch in c):
        return f"#{c.lower()}"
    return fallback


def fetch_hero_image_url(summary: dict[str, Any]) -> str | None:
    """Pull a game-recap photo URL from an ESPN summary payload, if one exists.

    Tries (in order):
      1. summary.article.images[0].url      — biggest signal of a real photo
      2. summary.gamepackageJSON.article.images[0].url
      3. summary.gameNote / videos posters  — last resort
    Returns None if nothing usable is found.
    """
    candidates: list[dict[str, Any]] = []

    article = summary.get("article") or {}
    candidates += article.get("images") or []

    gp = summary.get("gamepackageJSON") or {}
    gp_article = gp.get("article") or {}
    candidates += gp_article.get("images") or []

    for v in (summary.get("videos") or []):
        poster = v.get("poster") or v.get("thumbnail")
        if poster:
            candidates.append({"url": poster, "width": 1280})

    best = None
    best_w = 0
    for img in candidates:
        url = (img or {}).get("url")
        if not url:
            continue
        w = int((img or {}).get("width", 0) or 0)
        if best is None or w > best_w:
            best = url
            best_w = w
    return best


def _fallback_logo(abbrev: str) -> str:
    if not abbrev:
        return ""
    return f"https://a.espncdn.com/i/teamlogos/nba/500/{abbrev.lower()}.png"


def fetch_scoreboard(target: date | None = None) -> dict[str, Any]:
    params = {}
    if target is not None:
        params["dates"] = target.strftime("%Y%m%d")
    r = requests.get(SCOREBOARD_URL, params=params, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def fetch_finished_games(target: date | None = None) -> list[Game]:
    payload = fetch_scoreboard(target)
    games: list[Game] = []
    for event in payload.get("events", []):
        status = (event.get("status") or {}).get("type") or {}
        if status.get("completed"):
            games.append(_parse_game(event))
    return games


def fetch_first_final(target: date | None = None) -> Game | None:
    games = fetch_finished_games(target)
    return games[0] if games else None


def fetch_box_score(game_id: str) -> dict[str, Any]:
    r = requests.get(SUMMARY_URL, params={"event": game_id}, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def load_fixture(path: Path) -> tuple[Game, dict[str, Any]]:
    """Load a saved {scoreboard_event, summary} bundle for offline replay."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    event = data["event"]
    summary = data["summary"]
    return _parse_game(event), summary
