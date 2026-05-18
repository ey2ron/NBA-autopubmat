"""CLI entry point: scrape -> filter -> pick MVP -> build pubmat."""
from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
from pathlib import Path

# Ensure UTF-8 stdout on Windows.
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from .config import load as load_config
from .mvp import PlayerLine, pick_mvp
from .pubmat import build_pubmat
from .scraper import Game, fetch_box_score, fetch_finished_games, load_fixture


def build_caption(game: Game, mvp: PlayerLine | None) -> str:
    winner = game.winner
    loser = game.loser

    lines = []
    if game.header:
        prefix = f"{game.header}"
        if game.game_label:
            prefix += f" · {game.game_label}"
        lines.append(prefix)
    lines.append(f"{winner.name} defeat the {loser.name} {winner.score}-{loser.score} — FINAL")

    if mvp is not None:
        lines.append("")
        lines.append(f"Player of the Game: {mvp.name} ({mvp.team_abbrev})")
        lines.append(
            f"  {mvp.pts} PTS · {mvp.reb} REB · {mvp.ast} AST · "
            f"{mvp.stl} STL · {mvp.blk} BLK  (GameScore {mvp.game_score:.1f})"
        )

    lines.append("")
    lines.append(f"#NBA #{game.away.abbrev}vs{game.home.abbrev}")
    return "\n".join(lines)


def _matches_team(game: Game, abbrev: str) -> bool:
    abbrev = abbrev.upper()
    return game.home.abbrev == abbrev or game.away.abbrev == abbrev


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="NBA final-score pubmat generator.")
    p.add_argument("--date", help="YYYY-MM-DD (default: today)", default=None)
    p.add_argument("--game-id", help="Pick a specific ESPN game id", default=None)
    p.add_argument("--fixture", help="Path to a saved {event, summary} JSON", default=None)
    p.add_argument(
        "--team",
        help="Override team abbreviation from config.json (e.g. TOR, LAL).",
        default=None,
    )
    p.add_argument(
        "--all-games",
        action="store_true",
        help="Generate pubmats for every finished game (overrides team filter).",
    )
    return p.parse_args(argv)


def _gather_games(args: argparse.Namespace) -> list[tuple[Game, dict]]:
    """Return [(game, summary), ...] respecting the CLI flags."""
    if args.fixture:
        fixture_path = Path(args.fixture)
        if not fixture_path.exists():
            print(f"Fixture not found: {fixture_path}", file=sys.stderr)
            sys.exit(2)
        game, summary = load_fixture(fixture_path)
        return [(game, summary)]

    target: date | None = None
    if args.date:
        try:
            target = datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            print(f"Bad --date (need YYYY-MM-DD): {args.date}", file=sys.stderr)
            sys.exit(2)

    print(f"Fetching ESPN scoreboard for {target or 'today'}...")
    games = fetch_finished_games(target)

    if args.game_id:
        games = [g for g in games if g.game_id == args.game_id]

    return [(g, None) for g in games]  # summaries fetched lazily per game


def _process_one(
    game: Game,
    summary: dict | None,
) -> bool:
    """Build one pubmat. Returns True on success."""
    if summary is None:
        print(f"Fetching box score for game_id={game.game_id}...")
        summary = fetch_box_score(game.game_id)

    mvp = pick_mvp(summary, game.winner.team_id)
    if mvp is not None:
        print(f"MVP: {mvp.name} — {mvp.pts}p / {mvp.reb}r / {mvp.ast}a  (GS {mvp.game_score:.1f})")
    else:
        print("MVP: (could not determine)")

    print("Building pubmat...")
    image_path = build_pubmat(game, mvp, summary)
    print(f"Pubmat saved: {image_path}")
    return True


def run(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    cfg = load_config()

    team_abbrev = (args.team or cfg.team_abbrev).upper()
    post_all = args.all_games or cfg.post_all_finished_games

    pairs = _gather_games(args)
    if not pairs:
        print("No finished NBA games for that date.")
        return 0

    if not post_all and not args.fixture and not args.game_id:
        pairs = [(g, s) for (g, s) in pairs if _matches_team(g, team_abbrev)]
        if not pairs:
            print(f"No finished game for team {team_abbrev} on that date.")
            return 0

    posted = 0
    for game, summary in pairs:
        print()
        print(f"[GAME] {game.away.name} {game.away.score} @ "
              f"{game.home.name} {game.home.score}  (id={game.game_id})")
        if _process_one(game, summary):
            posted += 1

    print()
    print(f"Done. {posted} pubmat(s) generated.")
    return 0


if __name__ == "__main__":
    sys.exit(run())
