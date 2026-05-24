from __future__ import annotations

import io
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps

from .mvp import PlayerLine
from .scraper import Game, Team, fetch_hero_image_url

CANVAS = (1280, 1600)
PHOTO_BOTTOM = 900
WHITE = (255, 255, 255)
WHITE_DIM = (255, 255, 255, 165)
BLACK = (0, 0, 0)

LOGO_CDN = "https://a.espncdn.com/i/teamlogos/nba/500/{abbrev}.png"

ASSETS = Path(__file__).resolve().parent.parent / "assets"
LOGOS_DIR = ASSETS / "logos"
HEROES_DIR = ASSETS / "heroes"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


# --------------------------------------------------------------------- fonts


def _try_font(candidates: list[str], size: int) -> ImageFont.ImageFont:
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def _display(size: int) -> ImageFont.ImageFont:
    """Massive condensed sans for the score numerals."""
    return _try_font(
        ["impact.ttf", "Impact.ttf", "BebasNeue-Regular.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"],
        size,
    )


def _bold(size: int) -> ImageFont.ImageFont:
    return _try_font(["arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf"], size)


def _regular(size: int) -> ImageFont.ImageFont:
    return _try_font(["arial.ttf", "Arial.ttf", "DejaVuSans.ttf"], size)


# ----------------------------------------------------------------- helpers


def _hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    s = hex_str.lstrip("#")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


def _luminance(rgb: tuple[int, int, int]) -> float:
    r, g, b = (c / 255.0 for c in rgb)
    return 0.299 * r + 0.587 * g + 0.114 * b


def _readable_on(bg: tuple[int, int, int]) -> tuple[int, int, int]:
    """Return white or near-black depending on what reads better on `bg`."""
    return (255, 255, 255) if _luminance(bg) < 0.55 else (15, 15, 15)


def _download(url: str, dest: Path | None = None) -> Image.Image | None:
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        if dest is not None:
            dest.write_bytes(r.content)
        return Image.open(io.BytesIO(r.content))
    except Exception:
        return None


def get_logo(team: Team) -> Image.Image | None:
    LOGOS_DIR.mkdir(parents=True, exist_ok=True)
    path = LOGOS_DIR / f"{team.abbrev.lower()}.png"
    if not path.exists():
        url = team.logo_url or LOGO_CDN.format(abbrev=team.abbrev.lower())
        if _download(url, path) is None:
            return None
    try:
        return Image.open(path).convert("RGBA")
    except Exception:
        return None


def _draw_centered(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, font, fill=WHITE) -> None:
    bb = draw.textbbox((0, 0), text, font=font)
    w = bb[2] - bb[0]
    h = bb[3] - bb[1]
    draw.text((xy[0] - w // 2, xy[1] - bb[1] - h // 2), text, font=font, fill=fill)


def _draw_tracked(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font,
    spacing: int = 8,
    fill=WHITE,
    anchor_left: bool = True,
) -> int:
    """Draw text with letter-spacing. Returns total drawn width."""
    widths = [draw.textbbox((0, 0), c, font=font)[2] for c in text]
    total = sum(widths) + spacing * max(0, len(text) - 1)
    x = xy[0] if anchor_left else xy[0] - total // 2
    for ch, w in zip(text, widths):
        draw.text((x, xy[1]), ch, font=font, fill=fill)
        x += w + spacing
    return total


# ------------------------------------------------------------------- hero


def _load_local_hero(game_id: str) -> Image.Image | None:
    """If user dropped assets/heroes/<game_id>.{jpg,png}, use it."""
    if not HEROES_DIR.exists():
        return None
    for ext in ("jpg", "jpeg", "png", "webp"):
        p = HEROES_DIR / f"{game_id}.{ext}"
        if p.exists():
            try:
                return Image.open(p).convert("RGB")
            except Exception:
                continue
    return None


def _build_logo_hero(winner: Team, height: int) -> Image.Image:
    """Fallback hero: gradient from winner.color → winner.alt_color, big logo center."""
    w = CANVAS[0]
    base = Image.new("RGB", (w, height), _hex_to_rgb(winner.color))
    alt_rgb = _hex_to_rgb(winner.alt_color)
    # Diagonal-ish gradient using a luminance mask.
    mask = Image.new("L", (w, height), 0)
    md = ImageDraw.Draw(mask)
    for y in range(height):
        a = int(180 * (y / height))
        md.line((0, y, w, y), fill=a)
    alt_layer = Image.new("RGB", (w, height), alt_rgb)
    base = Image.composite(alt_layer, base, mask)

    # Subtle large logo, semi-transparent.
    logo = get_logo(winner)
    if logo is not None:
        target = int(height * 0.85)
        logo = ImageOps.contain(logo, (target, target))
        # Reduce opacity by manipulating alpha.
        alpha = logo.split()[3].point(lambda a: int(a * 0.85))
        logo.putalpha(alpha)
        base.paste(
            logo,
            ((w - logo.size[0]) // 2, (height - logo.size[1]) // 2 - 20),
            logo,
        )
    return base


def _build_hero(game: Game, summary: dict | None) -> Image.Image:
    """Composite hero zone. Priority: local drop-in → ESPN recap → logo fallback."""
    height = PHOTO_BOTTOM
    w = CANVAS[0]

    # 1. Local drop-in
    src = _load_local_hero(game.game_id)
    # 2. ESPN recap photo
    if src is None and summary is not None:
        url = fetch_hero_image_url(summary)
        if url:
            dl = _download(url)
            if dl is not None:
                src = dl.convert("RGB")
    # 3. Logo fallback
    if src is None:
        return _build_logo_hero(game.winner, height)

    # Cover the hero zone (resize, then center-crop, biased up for faces)
    sw, sh = src.size
    scale = max(w / sw, height / sh)
    new_size = (int(sw * scale), int(sh * scale))
    src = src.resize(new_size, Image.LANCZOS)
    left = (src.size[0] - w) // 2
    top = (src.size[1] - height) // 3   # bias upward
    src = src.crop((left, top, left + w, top + height))

    # Gradient overlay (transparent top → opaque winner-color bottom) so text reads
    overlay = Image.new("RGBA", (w, height), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    winner_rgb = _hex_to_rgb(game.winner.color)
    for y in range(height):
        # Stronger overlay near the bottom edge so it blends into the color band.
        frac = (y / height) ** 1.8
        a = int(220 * frac)
        od.line((0, y, w, y), fill=(*winner_rgb, a))
    out = src.convert("RGBA")
    out.alpha_composite(overlay)
    return out.convert("RGB")


# ------------------------------------------------------------------ panel


def _build_color_band(winner: Team, height: int) -> Image.Image:
    """Solid winner color with a subtle dark band along the top edge."""
    rgb = _hex_to_rgb(winner.color)
    band = Image.new("RGB", (CANVAS[0], height), rgb)
    # Subtle vertical darkening so the bottom isn't too flat
    overlay = Image.new("L", band.size, 0)
    od = ImageDraw.Draw(overlay)
    for y in range(height):
        od.line((0, y, band.size[0], y), fill=int(50 * (y / height)))
    dark = Image.new("RGB", band.size, (
        max(rgb[0] - 25, 0),
        max(rgb[1] - 25, 0),
        max(rgb[2] - 25, 0),
    ))
    return Image.composite(dark, band, overlay)


def _paste_team_logo(canvas: Image.Image, team: Team, anchor: tuple[int, int], box: int) -> None:
    logo = get_logo(team)
    if logo is None:
        return
    logo = ImageOps.contain(logo, (box, box))
    x = anchor[0] - logo.size[0] // 2
    y = anchor[1] - logo.size[1] // 2
    canvas.paste(logo, (x, y), logo)


# ----------------------------------------------------------------- public


def build_pubmat(game: Game, mvp: PlayerLine | None, summary: dict | None = None,
                 out_path: Path | None = None) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = out_path or (OUTPUT_DIR / f"{game.game_id}.png")

    winner = game.winner
    loser = game.loser
    fg = _readable_on(_hex_to_rgb(winner.color))

    # Compose top hero + bottom color band
    canvas = Image.new("RGB", CANVAS, _hex_to_rgb(winner.color))
    hero = _build_hero(game, summary)
    canvas.paste(hero, (0, 0))
    band_h = CANVAS[1] - PHOTO_BOTTOM
    canvas.paste(_build_color_band(winner, band_h), (0, PHOTO_BOTTOM))

    draw = ImageDraw.Draw(canvas, "RGBA")

    # --------- 1. small header (CONFERENCE FINALS · GAME 6)
    header_parts: list[str] = []
    if game.header:
        header_parts.append(game.header.upper())
    if game.game_label:
        header_parts.append(game.game_label.upper())
    header_text = "   ·   ".join(header_parts) or "NBA"

    pad_x = 80
    header_y = PHOTO_BOTTOM + 40
    _draw_tracked(draw, (pad_x, header_y), header_text, _bold(26), spacing=4, fill=fg)

    # Thin rule beneath the header
    rule_y = header_y + 60
    draw.line((pad_x, rule_y, CANVAS[0] - pad_x, rule_y), fill=(*fg, 90), width=2)

    # --------- 2. Stat-card score rows
    # Layout: team name on the LEFT, score on the RIGHT, two rows (winner first).
    row1_y = rule_y + 50
    row_gap = 140

    score_font = _display(136)
    name_font = _bold(52)
    abbrev_font = _bold(80)

    # Right-edge for scores
    right_edge = CANVAS[0] - pad_x

    # Max width the team label can occupy before the score starts
    _score_reserve = 320  # enough for a 3-digit score at 136pt

    def _draw_row(y: int, team: Team, *, dim: bool) -> None:
        text_alpha = 165 if dim else 255
        color = (*fg, text_alpha)

        # Score (right-aligned) — draw first so we know exact left edge
        score_str = str(team.score)
        sbb = draw.textbbox((0, 0), score_str, font=score_font)
        sw = sbb[2] - sbb[0]
        score_x = right_edge - sw
        draw.text((score_x, y - 20), score_str, font=score_font, fill=color)

        # Team label: use abbreviation if full name would overlap score
        max_name_w = score_x - pad_x - 40
        full_name = team.name.upper()
        # Measure full name
        trial_w = sum(
            draw.textbbox((0, 0), c, font=name_font)[2]
            for c in full_name
        ) + 3 * max(0, len(full_name) - 1)
        if trial_w > max_name_w:
            # Fall back to abbreviation drawn larger
            _draw_centered(draw, (pad_x + max_name_w // 2, y + 50), team.abbrev.upper(), abbrev_font, fill=color)
        else:
            _draw_tracked(draw, (pad_x, y + 30), full_name, name_font, spacing=3, fill=color)

        # Underline beneath the winner's score only
        if not dim:
            draw.line(
                (score_x, y + (sbb[3] - sbb[1]) + 5,
                 right_edge, y + (sbb[3] - sbb[1]) + 5),
                fill=(*fg, 220), width=6,
            )

    _draw_row(row1_y, winner, dim=False)
    _draw_row(row1_y + row_gap, loser, dim=True)

    # --------- 3. Series state (if a playoff series exists), small + right-aligned
    if winner.series_wins is not None and loser.series_wins is not None:
        if winner.series_wins >= 4:
            wins_str = f"{winner.abbrev} WINS SERIES {winner.series_wins}–{loser.series_wins}"
        elif winner.series_wins > loser.series_wins:
            wins_str = f"{winner.abbrev} LEADS {winner.series_wins}–{loser.series_wins}"
        else:
            wins_str = f"SERIES TIED {winner.series_wins}–{loser.series_wins}"
        series_y = row1_y + row_gap + 190
        series_font = _bold(28)
        sbb = draw.textbbox((0, 0), wins_str, font=series_font)
        sw = sbb[2] - sbb[0]
        # Clamp so it never bleeds off the left edge
        sx = max(pad_x, right_edge - sw - 30)
        _draw_tracked(
            draw, (sx, series_y), wins_str,
            series_font, spacing=3, fill=(*fg, 215),
        )

    # --------- 4. MVP credit at the bottom
    if mvp is not None:
        mvp_top = CANVAS[1] - 260
        draw.line((pad_x, mvp_top, pad_x + 220, mvp_top), fill=(*fg, 220), width=4)

        _draw_tracked(
            draw, (pad_x, mvp_top + 18), "PLAYER OF THE GAME",
            _bold(24), spacing=5, fill=(*fg, 220),
        )
        draw.text(
            (pad_x, mvp_top + 58),
            mvp.name.upper(),
            font=_bold(52),
            fill=fg,
        )
        # Split stat line into two rows so it fits on any screen size
        row_a = f"{mvp.pts} PTS   ·   {mvp.reb} REB   ·   {mvp.ast} AST"
        row_b = f"{mvp.stl} STL   ·   {mvp.blk} BLK"
        stat_font = _regular(30)
        draw.text((pad_x, mvp_top + 128), row_a, font=stat_font, fill=(*fg, 220))
        draw.text((pad_x, mvp_top + 168), row_b, font=stat_font, fill=(*fg, 180))

    # --------- 5. Tiny "FINAL" badge in the top-right of the color band
    badge_text = "FINAL"
    badge_font = _bold(26)
    bb = draw.textbbox((0, 0), badge_text, font=badge_font)
    bw = bb[2] - bb[0] + 36
    bh = bb[3] - bb[1] + 18
    bx = CANVAS[0] - pad_x - bw
    by = header_y - 6
    draw.rounded_rectangle((bx, by, bx + bw, by + bh), radius=6, fill=(*fg, 230))
    bg_rgb = _hex_to_rgb(winner.color)
    draw.text((bx + 18, by + 4), badge_text, font=badge_font, fill=bg_rgb)

    canvas.save(out_path, "PNG")
    return out_path
