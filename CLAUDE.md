# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Run the Streamlit dashboard (primary UI):**
```
streamlit run app.py
```

**Run the CLI generator:**
```
python -m nba_post.main
python -m nba_post.main --date 2025-06-01
python -m nba_post.main --all-games
python -m nba_post.main --fixture tests/fixtures/raptors_bucks_2019_g6.json
```

**Install Windows Scheduled Task (runs CLI daily at 03:00):**
```powershell
.\scripts\Install-ScheduledTask.ps1
.\scripts\Install-ScheduledTask.ps1 -Time 02:30
```

**Install dependencies** (no requirements.txt; install manually):
```
pip install streamlit requests pillow
```

## Architecture

Two entry points share the same `nba_post` package:

- **`app.py`** — Streamlit dashboard. Lets users pick a game, preview the generated pubmat, edit the caption, and download the PNG. No Facebook posting from the UI.
- **`nba_post/main.py`** — CLI. Scrapes, filters by team, builds pubmat(s), and optionally posts to Facebook.

### Data flow

```
scraper.fetch_finished_games()   →  list[Game]
scraper.fetch_box_score(game_id) →  summary dict (ESPN JSON)
mvp.pick_mvp(summary, winner_id) →  PlayerLine (Hollinger Game Score)
pubmat.build_pubmat(game, mvp)   →  output/<game_id>.png
publisher.publish(...)           →  Facebook Graph API (CLI only)
```

### Key modules

| Module | Responsibility |
|--------|---------------|
| `scraper.py` | ESPN public API calls; `Game`/`Team` dataclasses; `load_fixture()` for offline replay |
| `mvp.py` | Parses ESPN box-score JSON into `PlayerLine` structs; computes Hollinger Game Score |
| `pubmat.py` | Pillow image renderer; 1280×1600 PNG with hero photo + score rows + MVP credit |
| `publisher.py` | Facebook Graph API photo post; supports `dry_run=True` mode |
| `state.py` | Tracks posted game IDs in `.posted/posted.json` to prevent duplicate posts |
| `config.py` | Loads `config.json` from repo root (`team_abbrev`, `post_all_finished_games`) |

### Configuration

Create `config.json` at the repo root (optional; all fields have defaults):
```json
{
  "team_abbrev": "LAL",
  "post_all_finished_games": false
}
```

Facebook credentials go in a `.env` file (not loaded automatically — caller must pass `page_id` and `access_token` to `publisher.publish()`).

### Assets & generated files

- `assets/logos/` — team logo PNGs, downloaded on first use and cached (gitignored)
- `assets/heroes/<game_id>.{jpg,png}` — optional local drop-in hero images (override ESPN recap photo)
- `assets/logo.svg` — navbar logo for the Streamlit UI
- `output/` — generated pubmat PNGs (gitignored)
- `.posted/posted.json` — deduplication state (gitignored)

### Hero image priority

`pubmat._build_hero()` picks the background photo in this order:
1. `assets/heroes/<game_id>.*` (local drop-in)
2. ESPN summary recap photo (widest available)
3. Gradient + large team logo fallback (no network needed)

### Offline / fixture testing

Fixtures are `{event: <scoreboard_event>, summary: <box_score_summary>}` JSON bundles. The only fixture in the repo is `tests/fixtures/raptors_bucks_2019_g6.json`. Use `--fixture <path>` with the CLI or `load_fixture()` in code to replay without hitting ESPN.
