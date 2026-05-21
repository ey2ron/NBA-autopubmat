"""Streamlit dashboard for the NBA pubmat generator.

Run with:
    streamlit run app.py
"""
from __future__ import annotations

import base64
import html
from datetime import date, datetime
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from nba_post.main import build_caption
from nba_post.mvp import pick_mvp
from nba_post.pubmat import build_pubmat
from nba_post.scraper import Game, fetch_box_score, fetch_finished_games

ROOT = Path(__file__).resolve().parent

st.set_page_config(
  page_title="NBA Pubmat Generator",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================== custom theme


CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Barlow+Condensed:wght@400;500;600;700;800&family=Inter:wght@300;400;500;600;700&display=swap');

:root {
  --bg-base: #0a0a0f;
  --bg-elev: #14141c;
  --bg-glass: rgba(255, 255, 255, 0.04);
  --bg-glass-strong: rgba(255, 255, 255, 0.07);
  --border-glass: rgba(255, 255, 255, 0.08);
  --nba-red: #C9082A;
  --nba-red-deep: #8b0620;
  --nba-gold: #FDB927;
  --electric: #00C2FF;
  --text-primary: #ffffff;
  --text-dim: rgba(255, 255, 255, 0.65);
  --text-muted: rgba(255, 255, 255, 0.4);
  --success: #1DB954;
  --fb-blue: #1877F2;
  --fb-blue-deep: #0d3a8a;
}

/* ---------- App shell ---------- */
.stApp {
  background:
    radial-gradient(circle at 0% 0%, rgba(201, 8, 42, 0.10) 0%, transparent 45%),
    radial-gradient(circle at 100% 100%, rgba(253, 185, 39, 0.06) 0%, transparent 45%),
    linear-gradient(180deg, #0a0a0f 0%, #0d0d14 100%);
  background-attachment: fixed;
  color: var(--text-primary);
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}
.stApp::before {
  content: '';
  position: fixed;
  inset: 0;
  background-image:
    repeating-linear-gradient(30deg,
      rgba(255,255,255,0.018) 0,
      rgba(255,255,255,0.018) 1px,
      transparent 1px,
      transparent 42px),
    repeating-linear-gradient(-30deg,
      rgba(255,255,255,0.012) 0,
      rgba(255,255,255,0.012) 1px,
      transparent 1px,
      transparent 42px);
  pointer-events: none;
  z-index: 0;
}
.block-container {
  padding-top: 0.5rem !important;
  max-width: 1280px !important;
}
#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; height: 0; }

/* ---------- Typography ---------- */
h1, h2, h3, h4, h5, h6 {
  font-family: 'Barlow Condensed', sans-serif !important;
  font-weight: 700 !important;
  letter-spacing: 0.02em;
  color: var(--text-primary) !important;
}
.stMarkdown p, .stMarkdown li, .stMarkdown span {
  font-family: 'Inter', sans-serif;
  color: var(--text-dim);
}

/* ---------- Navbar ---------- */
.nba-navbar {
  position: sticky;
  top: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 22px;
  background: rgba(10, 10, 15, 0.85);
  backdrop-filter: blur(22px);
  -webkit-backdrop-filter: blur(22px);
  border: 1px solid var(--border-glass);
  border-radius: 16px;
  margin-bottom: 22px;
}
.nba-brand { display: flex; align-items: center; gap: 14px; }
.nba-brand-logo {
  width: 42px; height: 42px;
  border-radius: 11px;
  display: block;
  box-shadow: 0 0 24px rgba(201, 8, 42, 0.45);
}
.nba-brand-name {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 24px;
  letter-spacing: 0.10em;
  color: white;
  line-height: 1;
}
.nba-brand-name .accent { color: var(--nba-gold); }
.nba-brand-sub {
  font-family: 'Inter', sans-serif;
  font-size: 11px;
  letter-spacing: 0.18em;
  color: var(--text-muted);
  text-transform: uppercase;
  margin-top: 3px;
}
.nba-nav-meta {
  display: flex; align-items: center; gap: 14px;
  font-size: 12px; color: var(--text-dim);
  font-family: 'Inter', sans-serif;
  letter-spacing: 0.05em;
}
.nba-nav-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: var(--success);
  box-shadow: 0 0 10px var(--success);
}

/* ---------- Hero ---------- */
.nba-hero {
  padding: 8px 4px 14px;
}
.nba-hero h1 {
  font-family: 'Bebas Neue', sans-serif !important;
  font-size: 52px !important;
  letter-spacing: 0.04em;
  margin: 0 !important;
  line-height: 1.05;
}
.nba-hero h1 .accent {
  background: linear-gradient(135deg, var(--nba-red), var(--nba-gold));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.nba-hero p {
  color: var(--text-dim);
  font-size: 14px;
  margin: 6px 0 0;
  letter-spacing: 0.02em;
}

/* ---------- Section labels ---------- */
.section-label {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 13px; letter-spacing: 0.22em;
  color: var(--nba-gold);
  text-transform: uppercase;
  font-weight: 600;
  display: flex; align-items: center; gap: 12px;
  margin: 28px 0 14px;
}
.section-label::before {
  content: '';
  width: 26px; height: 2px;
  background: var(--nba-red);
}
.section-label .num {
  display: inline-grid; place-items: center;
  width: 22px; height: 22px; border-radius: 6px;
  background: rgba(253,185,39,0.12);
  color: var(--nba-gold);
  font-family: 'Bebas Neue', sans-serif;
  font-size: 13px;
}


/* ---------- Status badges ---------- */
.badge {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 5px 12px; border-radius: 999px;
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 12px; font-weight: 700;
  letter-spacing: 0.14em; text-transform: uppercase;
}
.badge-final {
  background: rgba(255,255,255,0.06);
  color: var(--text-dim);
  border: 1px solid rgba(255,255,255,0.10);
}
.badge-live {
  background: rgba(201,8,42,0.18);
  color: #ff7088;
  border: 1px solid rgba(201,8,42,0.55);
  box-shadow: 0 0 16px rgba(201,8,42,0.35);
}
.badge-live::before {
  content: '';
  width: 7px; height: 7px; border-radius: 50%;
  background: #ff3355;
  animation: pulse-dot 1.4s infinite;
}
.badge-scheduled {
  background: transparent;
  color: var(--electric);
  border: 1px solid rgba(0,194,255,0.55);
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); box-shadow: 0 0 0 0 rgba(255,51,85,0.6); }
  50%      { opacity: 0.55; transform: scale(1.35); box-shadow: 0 0 0 7px rgba(255,51,85,0); }
}
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(14px); }
  to   { opacity: 1; transform: translateY(0); }
}
@keyframes spin-slow { to { transform: rotate(360deg); } }

/* ---------- POTG card ---------- */
.potg-card {
  background: linear-gradient(135deg, rgba(253,185,39,0.08), rgba(201,8,42,0.04));
  border: 1px solid rgba(253,185,39,0.20);
  border-radius: 16px;
  padding: 20px 24px;
  margin-top: 18px;
  animation: fadeInUp 0.5s ease 0.05s both;
}
.potg-label {
  font-size: 11px; letter-spacing: 0.20em;
  color: var(--nba-gold); text-transform: uppercase;
  font-weight: 700;
  font-family: 'Barlow Condensed', sans-serif;
}
.potg-name {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 32px; color: white;
  letter-spacing: 0.03em; margin-top: 4px;
  line-height: 1.1;
}
.potg-team {
  display: inline-block;
  padding: 2px 9px; border-radius: 6px;
  background: rgba(255,255,255,0.06);
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 11px; letter-spacing: 0.15em;
  color: var(--text-dim); margin-left: 10px;
  vertical-align: middle;
}
.potg-stats {
  display: flex; gap: 22px; flex-wrap: wrap;
  margin-top: 14px;
}
.potg-stat {
  display: flex; flex-direction: column;
  font-family: 'Inter', sans-serif;
}
.potg-stat .val {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 28px; color: white;
  line-height: 1;
}
.potg-stat .key {
  font-size: 10px; letter-spacing: 0.18em;
  color: var(--text-muted);
  text-transform: uppercase;
  margin-top: 4px;
}
.potg-gs {
  margin-top: 12px;
  font-size: 11px; letter-spacing: 0.12em;
  color: var(--text-muted);
  text-transform: uppercase;
  font-family: 'Barlow Condensed', sans-serif;
}

/* ---------- Publish header ---------- */
.publish-header {
  background: linear-gradient(135deg, rgba(13,58,138,0.14), rgba(24,119,242,0.05));
  border: 1px solid rgba(24,119,242,0.25);
  border-radius: 16px;
  padding: 18px 22px;
  margin: 4px 0 14px;
}
.publish-header-title {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 22px;
  letter-spacing: 0.06em;
  color: white;
  margin-bottom: 4px;
}
.publish-header-sub {
  font-size: 13px;
  color: var(--text-dim);
  font-family: 'Inter', sans-serif;
}
.publish-header-sub code {
  background: rgba(0,194,255,0.10);
  color: var(--electric);
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 12px;
}

/* ---------- Streamlit widget overrides ---------- */
.stButton > button {
  background: linear-gradient(135deg, var(--nba-red), var(--nba-red-deep)) !important;
  color: white !important;
  border: none !important;
  border-radius: 11px !important;
  padding: 10px 22px !important;
  font-family: 'Barlow Condensed', sans-serif !important;
  font-weight: 600 !important;
  font-size: 15px !important;
  letter-spacing: 0.10em !important;
  text-transform: uppercase !important;
  transition: all 200ms ease !important;
  box-shadow: 0 4px 16px rgba(201,8,42,0.25) !important;
}
.stButton > button:hover:not(:disabled) {
  transform: scale(1.02);
  box-shadow: 0 8px 28px rgba(201,8,42,0.45) !important;
}
.stButton > button:active:not(:disabled) { transform: scale(0.99); }
.stButton > button:disabled {
  background: rgba(255,255,255,0.05) !important;
  color: var(--text-muted) !important;
  box-shadow: none !important;
  cursor: not-allowed;
}

/* Inputs */
.stTextInput input, .stTextArea textarea, .stDateInput input,
[data-baseweb="input"] input {
  background: var(--bg-glass) !important;
  border: 1px solid var(--border-glass) !important;
  border-radius: 10px !important;
  color: white !important;
  font-family: 'Inter', sans-serif !important;
  transition: all 200ms ease;
}
.stTextInput input:focus, .stTextArea textarea:focus, .stDateInput input:focus {
  border-color: var(--nba-gold) !important;
  box-shadow: 0 0 0 3px rgba(253,185,39,0.15) !important;
  outline: none !important;
}

/* Selectbox */
.stSelectbox [data-baseweb="select"] > div {
  background: var(--bg-glass) !important;
  border: 1px solid var(--border-glass) !important;
  border-radius: 10px !important;
  color: white !important;
}
.stSelectbox [data-baseweb="select"] > div:hover {
  border-color: rgba(253,185,39,0.4) !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
  gap: 6px;
  background: var(--bg-glass);
  padding: 6px;
  border-radius: 12px;
  border: 1px solid var(--border-glass);
}
.stTabs [data-baseweb="tab"] {
  background: transparent !important;
  border-radius: 8px !important;
  color: var(--text-dim) !important;
  font-family: 'Barlow Condensed', sans-serif !important;
  font-weight: 600 !important;
  font-size: 14px !important;
  letter-spacing: 0.10em !important;
  text-transform: uppercase !important;
  padding: 8px 18px !important;
  transition: all 200ms ease;
}
.stTabs [data-baseweb="tab"]:hover { color: white !important; }
.stTabs [aria-selected="true"] {
  background: rgba(201,8,42,0.18) !important;
  color: white !important;
  box-shadow: inset 0 0 0 1px rgba(201,8,42,0.4) !important;
}
.stTabs [data-baseweb="tab-highlight"] { background: transparent !important; }

/* Sidebar */
section[data-testid="stSidebar"] {
  background: rgba(8, 8, 12, 0.92) !important;
  border-right: 1px solid var(--border-glass);
  backdrop-filter: blur(20px);
}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
  font-family: 'Bebas Neue', sans-serif !important;
  letter-spacing: 0.08em;
  color: var(--nba-gold) !important;
}

/* Alerts */
.stAlert {
  background: var(--bg-glass) !important;
  border: 1px solid var(--border-glass) !important;
  border-radius: 12px !important;
  backdrop-filter: blur(12px);
}
.stAlert [data-testid="stMarkdownContainer"] p { color: var(--text-primary) !important; }

/* Divider */
hr { border-color: var(--border-glass) !important; opacity: 1; }

/* Image */
.stImage > img {
  border-radius: 16px;
  border: 1px solid var(--border-glass);
  box-shadow: 0 10px 40px rgba(0,0,0,0.5);
}

/* Dataframe */
[data-testid="stDataFrame"] {
  background: var(--bg-glass) !important;
  border-radius: 12px;
  border: 1px solid var(--border-glass);
  overflow: hidden;
}

/* Metric */
[data-testid="stMetric"] {
  background: var(--bg-glass);
  border: 1px solid var(--border-glass);
  border-radius: 12px;
  padding: 14px 16px;
  backdrop-filter: blur(12px);
}
[data-testid="stMetricValue"] {
  font-family: 'Bebas Neue', sans-serif !important;
  color: var(--nba-gold) !important;
  font-size: 36px !important;
  line-height: 1 !important;
}
[data-testid="stMetricLabel"] {
  font-family: 'Barlow Condensed', sans-serif !important;
  letter-spacing: 0.12em !important;
  text-transform: uppercase;
}

/* Toggle / checkbox */
.stCheckbox label, [data-testid="stWidgetLabel"] {
  color: var(--text-dim) !important;
  font-family: 'Inter', sans-serif !important;
}

/* Spinner color */
.stSpinner > div > div {
  border-top-color: var(--nba-red) !important;
  border-right-color: rgba(201,8,42,0.3) !important;
  border-bottom-color: rgba(201,8,42,0.3) !important;
  border-left-color: rgba(201,8,42,0.3) !important;
}

/* Caption text under labels */
.stCaption, [data-testid="stCaptionContainer"] {
  color: var(--text-muted) !important;
  font-size: 12px !important;
  letter-spacing: 0.04em;
}

/* Responsive */
@media (max-width: 640px) {
  .score-value { font-size: 44px; }
  .score-team { font-size: 17px; }
  .score-team .abbrev { min-width: 42px; height: 42px; font-size: 16px; }
  .nba-navbar { padding: 11px 14px; flex-wrap: wrap; gap: 10px; }
  .nba-brand-name { font-size: 19px; }
  .nba-hero h1 { font-size: 36px !important; }
  .potg-name { font-size: 26px; }
  .potg-stats { gap: 14px; }
}
</style>
"""

LANDING_CSS = """
<style>
section[data-testid="stSidebar"],
button[data-testid="stSidebarCollapsedControl"],
button[data-testid="collapsedControl"] { display: none !important; }
.landing-wrap {
  min-height: 88vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 40px 24px 0;
}
.landing-eyebrow {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 12px;
  letter-spacing: 0.36em;
  color: var(--nba-gold);
  text-transform: uppercase;
  margin-bottom: 32px;
  animation: fadeInUp 0.6s ease both;
}
.landing-title {
  font-family: 'Bebas Neue', sans-serif !important;
  font-size: clamp(60px, 9.5vw, 116px) !important;
  line-height: 0.88 !important;
  letter-spacing: 0.04em;
  color: white !important;
  margin: 0 0 34px !important;
  animation: fadeInUp 0.6s ease 0.08s both;
}
.landing-title .grad {
  background: linear-gradient(135deg, var(--nba-red) 10%, var(--nba-gold) 90%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.landing-divider {
  width: 52px; height: 3px;
  background: linear-gradient(90deg, var(--nba-red), var(--nba-gold));
  border-radius: 2px;
  margin: 0 auto 30px;
  animation: fadeInUp 0.6s ease 0.14s both;
}
.landing-creators {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  align-items: center;
  gap: 8px 16px;
  animation: fadeInUp 0.6s ease 0.20s both;
}
.landing-creator {
  font-family: 'Inter', sans-serif;
  font-size: 15px;
  font-weight: 400;
  color: rgba(255,255,255,0.68);
  letter-spacing: 0.05em;
}
.landing-dot {
  color: var(--nba-gold);
  font-size: 20px;
  opacity: 0.70;
  line-height: 1;
}
.landing-tap-hint {
  margin-top: 56px;
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 12px;
  letter-spacing: 0.32em;
  color: var(--text-muted);
  text-transform: uppercase;
  animation: fadeInUp 0.6s ease 0.40s both, pulse-opacity 2.4s ease-in-out 1.2s infinite;
}
@keyframes pulse-opacity {
  0%, 100% { opacity: 0.35; }
  50%       { opacity: 0.85; }
}
@media (max-width: 640px) {
  .landing-title { font-size: 58px !important; }
  .landing-creator { font-size: 13px; }
}
</style>
"""


def _render_landing() -> None:
    st.markdown(LANDING_CSS, unsafe_allow_html=True)
    st.markdown(
        """
        <div class="landing-wrap">
          <div class="landing-eyebrow">BSCS-3A</div>
          <h1 class="landing-title">
            PYTHON<br><span class="grad">AUTOMATION</span><br>PROJECT
          </h1>
          <div class="landing-divider"></div>
          <div class="landing-creators">
            <span class="landing-creator">Aaron Clyde Guiruela</span>
            <span class="landing-dot">&middot;</span>
            <span class="landing-creator">Gian Dimaranan</span>
            <span class="landing-dot">&middot;</span>
            <span class="landing-creator">Scheza Mae Fernando</span>
          </div>
          <div class="landing-tap-hint"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    # Invisible Streamlit button — JS fires it when anywhere on screen is tapped
    if st.button("enter", key="enter_btn"):
        st.session_state.entered = True
        st.rerun()
    st.markdown(
        """
        <style>
        [data-testid="stButton"] {
          position: absolute !important;
          left: -9999px !important;
          top: -9999px !important;
          pointer-events: none !important;
        }
        .stApp { cursor: pointer !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    # components.html runs in an iframe and can reach window.parent —
    # the only reliable way to execute JS in Streamlit.
    components.html(
        """
        <script>
        (function () {
          function attach() {
            var btn = window.parent.document.querySelector('[data-testid="stButton"] button');
            if (!btn) { setTimeout(attach, 80); return; }
            window.parent.document.body.addEventListener('click', function handler() {
              window.parent.document.body.removeEventListener('click', handler);
              btn.click();
            }, { once: true });
          }
          attach();
        })();
        </script>
        """,
        height=0,
    )


st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

if not st.session_state.get("entered", False):
    _render_landing()
    st.stop()


# ============================================================== HTML helpers


def _status_badge(label: str = "FINAL") -> str:
    cls = {"LIVE": "badge-live", "SCHEDULED": "badge-scheduled"}.get(
        label.upper(), "badge-final"
    )
    return f'<span class="badge {cls}">{html.escape(label.upper())}</span>'


def _render_navbar() -> None:
    logo_path = ROOT / "assets" / "logo.svg"
    logo_uri = ""
    if logo_path.exists():
        svg_bytes = logo_path.read_bytes()
        svg_b64 = base64.b64encode(svg_bytes).decode("ascii")
        logo_uri = f"data:image/svg+xml;base64,{svg_b64}"
    now = datetime.now().strftime("%b %d, %Y · %I:%M %p")
    st.markdown(
        f"""
        <div class="nba-navbar">
          <div class="nba-brand">
            <img class="nba-brand-logo" src="{logo_uri}" alt="NBA Pubmat logo" />
            <div>
              <div class="nba-brand-name">NBA <span class="accent">PUBMAT</span></div>
              <div class="nba-brand-sub">Scores · Pubmat · Generator</div>
            </div>
          </div>
          <div class="nba-nav-meta">
            <span class="nba-nav-dot"></span>
            <span>LAST UPDATED · {now}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_hero() -> None:
    st.markdown(
        """
        <div class="nba-hero">
          <h1>FINAL SCORES <span class="accent">PUBMAT</span></h1>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_section_label(num: int, title: str) -> None:
    st.markdown(
        f'<div class="section-label"><span class="num">{num}</span>{html.escape(title)}</div>',
        unsafe_allow_html=True,
    )


def _render_score_card(game: Game, status: str = "FINAL") -> None:
    winner = game.winner
    loser = game.loser
    away = game.away
    home = game.home
    header_bits = []
    if game.header:
        header_bits.append(html.escape(game.header.upper()))
    if game.game_label:
      header_bits.append(html.escape(game.game_label.upper()))

    if header_bits:
        st.caption(" · ".join(header_bits))
    st.caption(f"STATUS · {status.upper()}")

    def _render_line(team, label: str) -> None:
        suffix = " (W)" if team.is_winner else ""
        st.write(f"{label} {team.abbrev} {team.name} — {team.score}{suffix}")

    _render_line(away, "AWAY:")
    _render_line(home, "HOME:")

    footer = None
    if winner.series_wins is not None and loser.series_wins is not None:
        if winner.series_wins >= 4:
            series_txt = f"{winner.abbrev} WINS SERIES {winner.series_wins}–{loser.series_wins}"
        elif winner.series_wins > loser.series_wins:
            series_txt = f"{winner.abbrev} LEADS {winner.series_wins}–{loser.series_wins}"
        else:
            series_txt = f"SERIES TIED {winner.series_wins}–{loser.series_wins}"
        footer = f"{series_txt} · WINNER {winner.name.upper()}"

    if footer:
        st.caption(footer)


def _render_potg_card(mvp) -> None:
    if mvp is None:
        return
    stats = [
        ("PTS", mvp.pts),
        ("REB", mvp.reb),
        ("AST", mvp.ast),
        ("STL", mvp.stl),
        ("BLK", mvp.blk),
    ]
    stat_html = "".join(
        f'<div class="potg-stat"><span class="val">{v}</span><span class="key">{k}</span></div>'
        for k, v in stats
    )
    st.markdown(
        f"""
        <div class="potg-card">
          <div class="potg-label">★ Player of the Game</div>
          <div class="potg-name">{html.escape(mvp.name)}<span class="potg-team">{html.escape(mvp.team_abbrev)}</span></div>
          <div class="potg-stats">{stat_html}</div>
          <div class="potg-gs">Hollinger Game Score · {mvp.game_score:.1f}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================== session state


def _clear_preview() -> None:
    for k in ("game", "summary", "mvp", "caption_edit", "image_path"):
        st.session_state.pop(k, None)


def _generate_preview(game: Game, summary: dict) -> None:
    mvp = pick_mvp(summary, game.winner.team_id)
    caption = build_caption(game, mvp)
    image_path = build_pubmat(game, mvp, summary)
    st.session_state.game = game
    st.session_state.summary = summary
    st.session_state.mvp = mvp
    st.session_state.caption_edit = caption
    st.session_state.image_path = image_path


# ============================================================== sidebar

with st.sidebar:
  st.markdown("### 🧾 Pubmat output")
  st.caption("Generated PNGs are saved to the output/ folder.")


# ============================================================== top of page

_render_navbar()
_render_hero()


# ============================================================== source picker

_render_section_label(1, "Pick a Game")

tab_today, tab_date = st.tabs(
  ["Today", "Specific date"]
)


def _games_for(target: date | None, abbrev: str | None) -> list[Game]:
    games = fetch_finished_games(target)
    if abbrev:
        games = [g for g in games if abbrev in (g.home.abbrev, g.away.abbrev)]
    return games


def _render_multi_game_picker(games: list[Game], key_prefix: str) -> None:
    labels = [
        f"{g.away.name} {g.away.score} @ {g.home.name} {g.home.score}"
        for g in games
    ]
    idx = st.selectbox(
        "Multiple games found — pick one:",
        range(len(games)),
        format_func=lambda i: labels[i],
        key=f"{key_prefix}_game_select",
    )
    if st.button("Generate Pubmat", key=f"{key_prefix}_gen_btn", type="primary"):
        with st.spinner("Fetching box score & building pubmat..."):
            summary = fetch_box_score(games[idx].game_id)
            _generate_preview(games[idx], summary)


with tab_today:
    if st.button("Fetch today's finished games", type="primary", key="today_btn"):
        _clear_preview()
        st.session_state.pop("today_games", None)
        with st.spinner("Calling ESPN scoreboard..."):
            fetched = _games_for(None, None)
        if not fetched:
            st.warning("No finished NBA games today.")
        elif len(fetched) == 1:
            st.info(f"One game found: **{fetched[0].away.name}** @ **{fetched[0].home.name}**")
            with st.spinner("Fetching box score & building pubmat..."):
                summary = fetch_box_score(fetched[0].game_id)
                _generate_preview(fetched[0], summary)
        else:
            st.session_state.today_games = fetched

    if "today_games" in st.session_state:
        _render_multi_game_picker(st.session_state.today_games, "today")


with tab_date:
    d = st.date_input("Date", value=date.today(), key="date_picker")
    if st.button("Fetch games for date", type="primary", key="date_btn"):
        _clear_preview()
        st.session_state.pop("date_games", None)
        with st.spinner(f"Calling ESPN scoreboard for {d}..."):
            fetched = _games_for(d, None)
        if not fetched:
            st.warning(f"No finished games on {d}.")
        elif len(fetched) == 1:
            st.info(f"One game found: **{fetched[0].away.name}** @ **{fetched[0].home.name}**")
            with st.spinner("Fetching box score & building pubmat..."):
                summary = fetch_box_score(fetched[0].game_id)
                _generate_preview(fetched[0], summary)
        else:
            st.session_state.date_games = fetched

    if "date_games" in st.session_state:
        _render_multi_game_picker(st.session_state.date_games, "date")




# ============================================================== preview pane

_render_section_label(2, "Preview")

if "game" not in st.session_state:
    st.info("Pick a game above to generate a preview.")
else:
    game: Game = st.session_state.game
    mvp = st.session_state.mvp
    image_path: Path = st.session_state.image_path

    col_img, col_meta = st.columns([1, 1])

    with col_img:
        st.image(str(image_path), caption=image_path.name, width="stretch")

    with col_meta:
        _render_score_card(game, status="FINAL")
        _render_potg_card(mvp)

        st.markdown(
            '<div class="section-label" style="margin-top:24px;">'
            '<span class="num">✎</span>Caption</div>',
            unsafe_allow_html=True,
        )
        edited_caption = st.text_area(
            "caption",
            height=200,
            label_visibility="collapsed",
            key="caption_edit",
        )

    # ------------------------------------------------------------ save
    _render_section_label(3, "Save")

    with open(image_path, "rb") as fh:
        st.download_button(
            "⬇️ Save pubmat PNG — download the image for sharing",
            data=fh,
            file_name=image_path.name,
            mime="image/png",
            use_container_width=True,
        )


# ============================================================== history pane

