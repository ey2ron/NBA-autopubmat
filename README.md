# NBA Final-Score Pubmat Generator

Automation that, once a day, scrapes ESPN for the followed team's final score,
picks the player-of-the-game by Hollinger Game Score, renders a portrait
pubmat with Pillow, and saves it to `output/<game_id>.png`.

Followed team is configurable in [config.json](config.json) (default: `TOR`).

---

## Quick start

1. **Install Python deps**
   ```powershell
   pip install -r requirements.txt
   ```

2. **Set the team** in [config.json](config.json):
   ```json
   { "team_abbrev": "TOR" }
   ```

3. **Smoke test (fixture replay)**
   ```powershell
   python -m nba_post.main --fixture tests/fixtures/raptors_bucks_2019_g6.json
   ```

4. **Live run (manual)**
   ```powershell
   python -m nba_post.main
   ```

5. **Schedule it** (Windows) — from an elevated PowerShell:
   ```powershell
   .\scripts\Install-ScheduledTask.ps1
   ```
   The task fires daily at 03:00 local. Change the time with
   `-Time 02:30` etc.

6. **(Optional) Launch the dashboard UI**
   ```powershell
   streamlit run app.py
   ```
   Then open <http://localhost:8501>. The dashboard lets you pick a game,
   preview the pubmat, and edit the caption — without touching the CLI.

---

## CLI flags

| Flag | Purpose |
| --- | --- |
| `--date YYYY-MM-DD` | Target a specific date (default: today). |
| `--game-id ID` | Pick a specific ESPN game id, skipping the team filter. |
| `--team ABBR` | Override `config.json` team for this run. |
| `--all-games` | Generate pubmats for every finished game (not just the followed team). |
| `--fixture path.json` | Replay a saved fixture for offline testing. |

---

## How it works

| File | Responsibility |
| --- | --- |
| [nba_post/scraper.py](nba_post/scraper.py) | ESPN scoreboard + box-score fetchers |
| [nba_post/mvp.py](nba_post/mvp.py) | Hollinger Game Score + MVP picker |
| [nba_post/pubmat.py](nba_post/pubmat.py) | Pillow pubmat composer |
| [nba_post/config.py](nba_post/config.py) | Loads config.json |
| [nba_post/main.py](nba_post/main.py) | CLI orchestrator |
| [app.py](app.py) | Streamlit dashboard (preview + download) |
| [scripts/Install-ScheduledTask.ps1](scripts/Install-ScheduledTask.ps1) | Windows Task Scheduler installer |

The Game Score formula used for MVP:

```
PTS + 0.4·FGM − 0.7·FGA − 0.4·(FTA − FTM)
    + 0.7·OREB + 0.3·DREB
    + STL + 0.7·AST + 0.7·BLK
    − 0.4·PF − TO
```

The highest score on the **winning** team becomes the player of the game.

---

## Scheduled-task lifecycle

```powershell
# Install / replace the task
.\scripts\Install-ScheduledTask.ps1

# Trigger it on demand (for testing)
Start-ScheduledTask -TaskName NBA-Pubmat

# Watch the log
Get-Content scripts\logs\auto-pubmat.log -Tail 40 -Wait

# Remove the task
Unregister-ScheduledTask -TaskName NBA-Pubmat -Confirm:$false
```

The task runs as your interactive user, so your PC must be powered on (or
woken) at the trigger time. If you'd rather have it run on a server or in
the cloud, see the Alternative schedulers section below.

---

## Dashboard UI (Streamlit)

For manual previewing, there's a Streamlit dashboard:

```powershell
streamlit run app.py
```

Opens at <http://localhost:8501>. Features:

- **Pick a game** by today / specific date / ESPN game ID / saved fixture
- **Preview the pubmat** (full-size image render)
- **Edit the caption** in a text area for copy/paste
- **Download button** for the generated PNG

The dashboard is **independent** of the scheduled task — the daily
auto-generation still happens in the background regardless of whether the
dashboard is open. Use the dashboard for *ad-hoc* previews.

---

## Alternative schedulers

- **GitHub Actions cron** — push the repo to GitHub, add a
   `.github/workflows/post.yml` with `on: schedule: cron: "0 8 * * *"`
   (08:00 UTC ≈ 03:00 ET) running `pip install -r requirements.txt &&
   python -m nba_post.main`.
- **Linux/macOS cron** — `0 3 * * * cd /path/to/NBA && python -m nba_post.main >> logs/run.log 2>&1`

---

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| Same game generated twice | The output file is overwritten for the same game id. |
| Pubmat shows wrong "GAME N" | ESPN's series.wins are wrong (live data) → fix by waiting until the box score is final. |
| Task runs but nothing happens | Open `scripts/logs/auto-pubmat.log` — every run is appended there. |
