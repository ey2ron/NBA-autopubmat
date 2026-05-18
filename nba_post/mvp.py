"""Hollinger Game Score MVP picker."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class PlayerLine:
    player_id: str
    name: str
    short_name: str
    team_id: str
    team_abbrev: str
    headshot_url: str
    # Box-score stats
    minutes: int
    pts: int
    reb: int
    oreb: int
    dreb: int
    ast: int
    stl: int
    blk: int
    to: int
    pf: int
    fgm: int
    fga: int
    ftm: int
    fta: int
    tpm: int
    tpa: int
    game_score: float = 0.0


# Column order per ESPN summary.boxscore.players[*].statistics[0]:
# ["MIN","FG","3PT","FT","OREB","DREB","REB","AST","STL","BLK","TO","PF","+/-","PTS"]
_STAT_KEYS = ["MIN", "FG", "3PT", "FT", "OREB", "DREB", "REB", "AST", "STL", "BLK", "TO", "PF", "+/-", "PTS"]


def _split_made_att(token: str) -> tuple[int, int]:
    """Parse '8-15' into (8, 15). Returns (0,0) on junk."""
    if not token or "-" not in token:
        return 0, 0
    a, b = token.split("-", 1)
    try:
        return int(a), int(b)
    except ValueError:
        return 0, 0


def _to_int(token: str) -> int:
    if token in ("", "--", None):
        return 0
    try:
        return int(token)
    except (ValueError, TypeError):
        return 0


def parse_player(
    athlete_row: dict[str, Any],
    stat_keys: list[str],
    team_id: str,
    team_abbrev: str,
) -> PlayerLine | None:
    athlete = athlete_row.get("athlete") or {}
    stats = athlete_row.get("stats") or []
    if not stats or len(stats) != len(stat_keys):
        return None

    by_key = dict(zip(stat_keys, stats))

    fgm, fga = _split_made_att(by_key.get("FG", ""))
    ftm, fta = _split_made_att(by_key.get("FT", ""))
    tpm, tpa = _split_made_att(by_key.get("3PT", ""))

    headshot = (athlete.get("headshot") or {})
    headshot_url = headshot.get("href", "") if isinstance(headshot, dict) else ""

    return PlayerLine(
        player_id=str(athlete.get("id", "")),
        name=athlete.get("displayName", ""),
        short_name=athlete.get("shortName", athlete.get("displayName", "")),
        team_id=team_id,
        team_abbrev=team_abbrev,
        headshot_url=headshot_url,
        minutes=_to_int(by_key.get("MIN")),
        pts=_to_int(by_key.get("PTS")),
        reb=_to_int(by_key.get("REB")),
        oreb=_to_int(by_key.get("OREB")),
        dreb=_to_int(by_key.get("DREB")),
        ast=_to_int(by_key.get("AST")),
        stl=_to_int(by_key.get("STL")),
        blk=_to_int(by_key.get("BLK")),
        to=_to_int(by_key.get("TO")),
        pf=_to_int(by_key.get("PF")),
        fgm=fgm,
        fga=fga,
        ftm=ftm,
        fta=fta,
        tpm=tpm,
        tpa=tpa,
    )


def game_score(p: PlayerLine) -> float:
    """Hollinger Game Score."""
    return (
        p.pts
        + 0.4 * p.fgm
        - 0.7 * p.fga
        - 0.4 * (p.fta - p.ftm)
        + 0.7 * p.oreb
        + 0.3 * p.dreb
        + p.stl
        + 0.7 * p.ast
        + 0.7 * p.blk
        - 0.4 * p.pf
        - p.to
    )


def pick_mvp(summary: dict[str, Any], winning_team_id: str) -> PlayerLine | None:
    """Find the highest-Game-Score player on the winning team."""
    boxscore = summary.get("boxscore") or {}
    team_blocks = boxscore.get("players") or []

    candidates: list[PlayerLine] = []
    for block in team_blocks:
        team = block.get("team") or {}
        if str(team.get("id")) != str(winning_team_id):
            continue

        team_abbrev = (team.get("abbreviation") or "").upper()
        statistics = block.get("statistics") or []
        if not statistics:
            continue

        stat_set = statistics[0]
        # ESPN's real API exposes:
        #   - `keys`  = long camelCase ("minutes", "fieldGoalsMade-fieldGoalsAttempted")
        #   - `names` = short abbreviations ("MIN", "FG", "3PT") <- what we want
        # Our offline fixture only carries the short forms in `keys`.
        # Prefer `names`, fall back to `keys` if the keys look like the short form.
        names = stat_set.get("names") or []
        keys_raw = stat_set.get("keys") or []
        if names and all(len(n) <= 5 for n in names):
            keys = [k.upper() for k in names]
        elif keys_raw and all(len(k) <= 5 for k in keys_raw):
            keys = [k.upper() for k in keys_raw]
        else:
            keys = _STAT_KEYS

        for row in stat_set.get("athletes") or []:
            # Skip DNP rows that have no stats payload
            if not row.get("stats"):
                continue
            line = parse_player(row, keys, str(team.get("id")), team_abbrev)
            if line is None:
                continue
            if line.minutes <= 0:
                continue
            line.game_score = game_score(line)
            candidates.append(line)

    if not candidates:
        return None
    return max(candidates, key=lambda p: p.game_score)
