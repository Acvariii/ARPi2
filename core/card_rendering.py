from __future__ import annotations

import math
from typing import Optional, Tuple


def parse_playing_card(card: str) -> Tuple[str, str, bool]:
    """Parse a card like 'AS' or 'TD' into (rank, suit_symbol, is_red)."""
    t = (card or "").strip()
    if not t:
        return ("", "", False)
    suit_raw = t[-1:]
    rank_raw = t[:-1] if len(t) >= 2 else t

    suit_map = {"S": "♠", "H": "♥", "D": "♦", "C": "♣", "♠": "♠", "♥": "♥", "♦": "♦", "♣": "♣"}
    suit = suit_map.get(suit_raw, suit_raw)
    rank = "10" if rank_raw == "T" else rank_raw
    is_red = suit in ("♥", "♦")
    return (rank, suit, is_red)


def draw_playing_card(
    renderer,
    rect: Tuple[int, int, int, int],
    card: str = "",
    *,
    face_up: bool = True,
    border_rgb: Tuple[int, int, int] = (30, 30, 30),
    border_width: int = 2,
    inner_border_rgb: Tuple[int, int, int] = (210, 210, 210),
    inner_border_width: int = 1,
) -> None:
    """Draw a standard playing card face/back in a Texas Hold'em style."""
    x, y, cw, ch = rect
    try:
        # Subtle shadow
        renderer.draw_rect((0, 0, 0), (int(x + 3), int(y + 3), int(cw), int(ch)), alpha=55)

        if not face_up:
            # Card back
            renderer.draw_rect((50, 70, 150), (int(x), int(y), int(cw), int(ch)))
            renderer.draw_rect((230, 230, 230), (int(x), int(y), int(cw), int(ch)), width=2)
            # Simple pattern
            for i in range(5):
                renderer.draw_line(
                    (200, 200, 240),
                    (int(x + 6), int(y + 10 + i * 18)),
                    (int(x + cw - 6), int(y + 2 + i * 18)),
                    width=2,
                    alpha=70,
                )
            try:
                renderer.draw_text("🂠", int(x + cw / 2), int(y + ch / 2), font_size=22, color=(235, 235, 235), anchor_x="center", anchor_y="center")
            except Exception:
                pass
            return

        # Face-up base
        renderer.draw_rect((248, 248, 248), (int(x), int(y), int(cw), int(ch)))
        renderer.draw_rect(tuple(int(v) for v in border_rgb), (int(x), int(y), int(cw), int(ch)), width=int(border_width))
        renderer.draw_rect(
            tuple(int(v) for v in inner_border_rgb),
            (int(x + 3), int(y + 3), int(cw - 6), int(ch - 6)),
            width=int(inner_border_width),
        )

        if not card:
            return

        rank, suit, is_red = parse_playing_card(card)
        color = (220, 20, 20) if is_red else (20, 20, 20)

        # Scale text based on card size to avoid overlaps.
        corner_fs = max(11, min(16, int(cw * 0.20)))
        center_fs = max(22, min(42, int(ch * 0.42)))
        corner_pad = max(7, int(cw * 0.12))
        corner = f"{rank}{suit}"

        renderer.draw_text(corner, int(x + corner_pad), int(y + corner_pad), font_size=corner_fs, color=color, bold=True, anchor_x="left", anchor_y="top")
        renderer.draw_text(corner, int(x + cw - corner_pad), int(y + ch - corner_pad), font_size=corner_fs, color=color, bold=True, anchor_x="right", anchor_y="bottom")
        renderer.draw_text(suit, int(x + cw / 2), int(y + ch / 2), font_size=center_fs, color=color, anchor_x="center", anchor_y="center")
    except Exception:
        return


def draw_label_card(
    renderer,
    rect: Tuple[int, int, int, int],
    text: str,
    *,
    face_color: Tuple[int, int, int] = (160, 160, 160),
    border_color: Tuple[int, int, int] = (20, 20, 25),
) -> None:
    """Draw a generic colored card with centered text."""
    x, y, w, h = rect
    try:
        renderer.draw_rect(tuple(int(v) for v in face_color), (int(x), int(y), int(w), int(h)), alpha=235)
        renderer.draw_rect(tuple(int(v) for v in border_color), (int(x), int(y), int(w), int(h)), width=2, alpha=240)
        renderer.draw_text(str(text or ""), int(x + w / 2), int(y + h / 2), font_size=14, color=(15, 15, 15), anchor_x="center", anchor_y="center")
    except Exception:
        return


def draw_emoji_card(
    renderer,
    rect: Tuple[int, int, int, int],
    *,
    emoji: str,
    title: str,
    accent_rgb: Tuple[int, int, int] = (140, 140, 140),
    corner: str = "",
    max_title_font_size: int = 0,
) -> None:
    """Draw a clean emoji+title card used for non-standard decks."""
    x, y, w, h = rect
    try:
        # Face base
        renderer.draw_rect((255, 255, 255), (int(x), int(y), int(w), int(h)), alpha=245)
        renderer.draw_rect(tuple(int(v) for v in accent_rgb), (int(x), int(y), int(w), int(h)), width=3, alpha=200)
        # Soft inner tint
        renderer.draw_rect(tuple(int(v) for v in accent_rgb), (int(x), int(y), int(w), int(h)), alpha=28)

        if corner:
            renderer.draw_text(str(corner), int(x + 10), int(y + 10), font_size=12, color=(35, 35, 35), bold=True, anchor_x="left", anchor_y="top")
            renderer.draw_text(str(corner), int(x + w - 10), int(y + h - 10), font_size=12, color=(35, 35, 35), bold=True, anchor_x="right", anchor_y="bottom")

        # Emoji shadow then emoji
        cx = int(x + w / 2)
        cy = int(y + h * 0.58)
        # Count visible emoji/characters (skip variation selectors & ZWJ so e.g. 🛡️ counts as 1)
        _vis = [_c for _c in str(emoji or "") if ord(_c) > 0x2000 and ord(_c) not in (0xFE0F, 0x200D)]
        _n_emoji = max(1, len(_vis)) if _vis else max(1, len(str(emoji or "")))
        _base_fs = max(18, int(h * 0.36))
        # Scale down font if multiple emoji would overflow the card width
        _emoji_fs = min(_base_fs, max(14, int(w * 0.78 / _n_emoji)))
        try:
            renderer.draw_text(str(emoji or ""), cx + 1, cy + 1, font_size=_emoji_fs, color=(0, 0, 0), alpha=90, anchor_x="center", anchor_y="center")
        except Exception:
            pass
        renderer.draw_text(str(emoji or ""), cx, cy, font_size=_emoji_fs, color=(255, 255, 255), alpha=255, anchor_x="center", anchor_y="center")

        # Title
        name = (title or "").strip()
        if name:
            fsz = max(10, int(h * 0.14))
            if max_title_font_size > 0:
                fsz = min(fsz, max_title_font_size)
            renderer.draw_text(name[:18], cx, int(y + h * 0.18), font_size=fsz, color=(35, 35, 35), bold=True, anchor_x="center", anchor_y="center")
    except Exception:
        return


# ---------------------------------------------------------------------------
# Per-game themed Pyglet backgrounds
# ---------------------------------------------------------------------------

def draw_game_background(renderer, w: int, h: int, theme: str) -> None:
    """Draw a rich, game-specific background. Falls back to a generic dark BG on error."""
    t = (theme or "").lower().replace(" ", "_").replace("'", "")
    try:
        _BG_DISPATCH.get(t, _bg_default)(renderer, w, h)
    except Exception:
        try:
            renderer.draw_rect((10, 10, 14), (0, 0, w, h))
        except Exception:
            pass


def _bg_blackjack(r, w: int, h: int) -> None:
    """Casino green felt table with gold rail and chip decorations."""
    r.draw_rect((3, 12, 22), (0, 0, w, h))
    pad = int(min(w, h) * 0.05)
    fw, fh = w - 2 * pad, h - 2 * pad
    # Felt surface
    r.draw_rect((6, 88, 28), (pad, pad, fw, fh), alpha=240)
    r.draw_rect((10, 110, 40), (pad + 6, pad + 6, fw - 12, fh - 12), alpha=80)
    # Gold outer rail
    r.draw_rect((200, 158, 18), (int(pad * 0.25), int(pad * 0.25), w - int(pad * 0.5), h - int(pad * 0.5)), width=8, alpha=200)
    r.draw_rect((240, 200, 50), (int(pad * 0.55), int(pad * 0.55), w - int(pad * 1.1), h - int(pad * 1.1)), width=2, alpha=80)
    # Chip stacks
    for cx2, cy2, col in [
        (int(w * 0.10), int(h * 0.82), (200, 30, 30)),
        (int(w * 0.90), int(h * 0.18), (30, 30, 200)),
        (int(w * 0.10), int(h * 0.18), (200, 175, 0)),
        (int(w * 0.90), int(h * 0.82), (20, 175, 30)),
    ]:
        for i in range(3):
            r.draw_circle(col, (cx2, cy2 - i * 5), 13, alpha=55)
            r.draw_circle((255, 255, 255), (cx2, cy2 - i * 5), 13, width=1, alpha=28)


def _bg_texas_holdem(r, w: int, h: int) -> None:
    """Poker table with wooden rail, green felt, and community card outlines."""
    # Dark wood base
    r.draw_rect((18, 10, 6), (0, 0, w, h))
    # Wooden rail
    r.draw_rect((80, 48, 16), (0, 0, w, h), alpha=255)
    # Wood grain lines
    for i in range(7):
        y_pos = int(h * (i + 0.5) / 7)
        r.draw_line((100, 65, 22), (0, y_pos), (w, y_pos), width=1, alpha=16)
    # Felt oval interior
    rail = int(min(w, h) * 0.10)
    r.draw_rect((8, 82, 30), (rail, rail, w - 2 * rail, h - 2 * rail), alpha=255)
    r.draw_circle((12, 100, 38), (w // 2, h // 2), int(min(w, h) * 0.33), alpha=35)
    # Rail borders
    r.draw_rect((130, 90, 28), (0, 0, w, h), width=4, alpha=140)
    r.draw_rect((48, 30, 10), (rail - 4, rail - 4, w - 2 * rail + 8, h - 2 * rail + 8), width=3, alpha=180)
    # Community card placeholder outlines
    cw2, ch2 = max(48, int(w * 0.062)), max(68, int(h * 0.135))
    total_cw = 5 * cw2 + 4 * 8
    cx0 = w // 2 - total_cw // 2
    cy0 = h // 2 - ch2 // 2
    for i in range(5):
        r.draw_rect((20, 110, 45), (cx0 + i * (cw2 + 8), cy0, cw2, ch2), width=2, alpha=55)
    # Pot marker
    r.draw_circle((200, 160, 28), (w // 2, int(h * 0.62)), 16, alpha=65)
    r.draw_circle((240, 200, 60), (w // 2, int(h * 0.62)), 16, width=2, alpha=80)


def _bg_uno(r, w: int, h: int) -> None:
    """Dark base with vibrant RGBY corner tints and a central UNO oval."""
    r.draw_rect((6, 6, 22), (0, 0, w, h))
    # Corner quadrant tints
    r.draw_rect((180, 20, 20), (0, 0, w // 2, h // 2), alpha=22)
    r.draw_rect((20, 160, 20), (w // 2, h // 2, w // 2, h // 2), alpha=22)
    r.draw_rect((20, 60, 200), (w // 2, 0, w // 2, h // 2), alpha=22)
    r.draw_rect((220, 180, 0), (0, h // 2, w // 2, h // 2), alpha=22)
    # Diagonal stripes
    stripe_colors = [(220, 40, 40), (40, 180, 40), (40, 80, 220), (230, 190, 0)]
    for i, col in enumerate(stripe_colors):
        offset = int(i * w * 0.14)
        r.draw_line(col, (offset, 0), (offset + int(h * 0.85), h), width=38, alpha=7)
    # Centre oval
    r.draw_circle((10, 10, 30), (w // 2, h // 2), int(min(w, h) * 0.30), alpha=180)
    r.draw_circle((8, 8, 26), (w // 2, h // 2), int(min(w, h) * 0.27), alpha=255)
    # Colour ring
    for col in [(220, 40, 40), (40, 180, 40), (40, 80, 220), (230, 190, 0)]:
        r.draw_circle(col, (w // 2, h // 2), int(min(w, h) * 0.30), width=4, alpha=110)


def _bg_exploding_kittens(r, w: int, h: int) -> None:
    """Dark purple base with orange explosion bursts and cat decorations."""
    r.draw_rect((8, 4, 16), (0, 0, w, h))
    # Hot orange edge bars
    for rect, al in [((0, 0, w, 4), 200), ((0, h - 4, w, 4), 200), ((0, 0, 4, h), 110), ((w - 4, 0, 4, h), 110)]:
        r.draw_rect((180, 60, 0), rect, alpha=al)
    # Explosion burst circles in each corner
    for bx, by in [(int(w * 0.08), int(h * 0.12)), (int(w * 0.92), int(h * 0.12)),
                   (int(w * 0.08), int(h * 0.88)), (int(w * 0.92), int(h * 0.88))]:
        r.draw_circle((200, 80, 0), (bx, by), int(min(w, h) * 0.12), alpha=20)
        r.draw_circle((240, 140, 0), (bx, by), int(min(w, h) * 0.07), alpha=28)
        r.draw_circle((255, 220, 0), (bx, by), int(min(w, h) * 0.03), alpha=55)
    # Centre dark zone
    r.draw_circle((12, 6, 20), (w // 2, h // 2), int(min(w, h) * 0.35), alpha=90)


def _bg_monopoly(r, w: int, h: int) -> None:
    """Classic warm cream base with Monopoly green border and subtle paper texture."""
    r.draw_rect((222, 212, 178), (0, 0, w, h))
    r.draw_rect((22, 116, 56), (0, 0, w, h), width=14, alpha=255)
    r.draw_rect((200, 188, 138), (10, 10, w - 20, h - 20), width=3, alpha=180)
    # Paper texture horizontal lines
    for i in range(20):
        r.draw_line((185, 175, 145), (0, int(h * i / 20)), (w, int(h * i / 20)), width=1, alpha=10)
    # Corner dots
    for cx2, cy2 in [(18, 18), (w - 18, 18), (18, h - 18), (w - 18, h - 18)]:
        r.draw_circle((22, 116, 56), (cx2, cy2), 10, alpha=150)


def _bg_unstable_unicorns(r, w: int, h: int) -> None:
    """Deep purple base with rainbow edges, magic circles, and star sparkles."""
    r.draw_rect((14, 6, 30), (0, 0, w, h))
    # Rainbow bands top + bottom + sides
    rainbow = [(255, 60, 60), (255, 150, 0), (255, 230, 0), (60, 210, 60), (60, 100, 255), (190, 0, 255)]
    bw = max(1, w // len(rainbow))
    bh = max(1, h // len(rainbow))
    for i, col in enumerate(rainbow):
        x0 = i * bw
        y0 = i * bh
        r.draw_rect(col, (x0, 0, bw + (w - len(rainbow) * bw if i == len(rainbow) - 1 else 0), 5), alpha=155)
        r.draw_rect(col, (x0, h - 5, bw + (w - len(rainbow) * bw if i == len(rainbow) - 1 else 0), 5), alpha=155)
        r.draw_rect(col, (0, y0, 5, bh), alpha=75)
        r.draw_rect(col, (w - 5, y0, 5, bh), alpha=75)
    # Magic circles
    r.draw_circle((180, 80, 240), (w // 2, h // 2), int(min(w, h) * 0.40), alpha=10)
    r.draw_circle((255, 180, 100), (w // 2, h // 2), int(min(w, h) * 0.26), alpha=7)
    r.draw_circle((200, 100, 255), (w // 2, h // 2), int(min(w, h) * 0.12), alpha=9)


def _bg_catan(r, w: int, h: int) -> None:
    """Ocean border, sandy land interior with hex grid hints."""
    r.draw_rect((20, 55, 125), (0, 0, w, h))
    r.draw_rect((28, 78, 155), (0, 0, w, h), width=22, alpha=220)
    land_pad = 24
    r.draw_rect((182, 148, 78), (land_pad, land_pad, w - 2 * land_pad, h - 2 * land_pad), alpha=200)
    # Hex grid hints
    hs = max(38, int(min(w, h) * 0.08))
    for row in range(-2, 5):
        for col in range(-1, 6):
            hx = int(w * 0.25 + col * hs * 1.78 + (row % 2) * hs * 0.89)
            hy = int(h * 0.25 + row * hs * 1.54)
            if 0 < hx < w and 0 < hy < h:
                r.draw_circle((158, 128, 58), (hx, hy), hs - 2, width=1, alpha=28)


def _bg_risk(r, w: int, h: int) -> None:
    """Dark ocean with land-mass colour patches and a map grid."""
    r.draw_rect((8, 22, 60), (0, 0, w, h))
    land_regions = [
        ((int(w * 0.05), int(h * 0.15), int(w * 0.22), int(h * 0.35)), (200, 100, 40)),
        ((int(w * 0.12), int(h * 0.55), int(w * 0.14), int(h * 0.26)), (190, 90, 35)),
        ((int(w * 0.38), int(h * 0.12), int(w * 0.28), int(h * 0.28)), (175, 78, 28)),
        ((int(w * 0.38), int(h * 0.44), int(w * 0.20), int(h * 0.38)), (120, 158, 38)),
        ((int(w * 0.56), int(h * 0.12), int(w * 0.30), int(h * 0.44)), (158, 118, 58)),
        ((int(w * 0.68), int(h * 0.60), int(w * 0.16), int(h * 0.17)), (38, 138, 78)),
    ]
    for rect, col in land_regions:
        r.draw_rect(col, rect, alpha=88)
        r.draw_rect((255, 255, 255), rect, width=1, alpha=18)
    # Map grid
    for i in range(8):
        r.draw_line((100, 140, 200), (0, int(h * i / 8)), (w, int(h * i / 8)), width=1, alpha=18)
    for i in range(12):
        r.draw_line((100, 140, 200), (int(w * i / 12), 0), (int(w * i / 12), h), width=1, alpha=18)
    r.draw_rect((178, 138, 58), (0, 0, w, h), width=6, alpha=145)


def _bg_cluedo(r, w: int, h: int) -> None:
    """Victorian dark burgundy with gold ornate border and room grid."""
    r.draw_rect((22, 8, 8), (0, 0, w, h))
    r.draw_rect((15, 5, 5), (int(w * 0.05), int(h * 0.05), int(w * 0.90), int(h * 0.90)), alpha=200)
    r.draw_rect((200, 158, 28), (0, 0, w, h), width=8, alpha=200)
    r.draw_rect((148, 108, 18), (8, 8, w - 16, h - 16), width=3, alpha=140)
    r.draw_rect((218, 178, 48), (13, 13, w - 26, h - 26), width=1, alpha=75)
    # Room grid
    cols3, rows3 = 3, 3
    pw3, ph3 = w // cols3, h // rows3
    for row in range(rows3):
        for col in range(cols3):
            r.draw_rect((30, 10, 10), (col * pw3, row * ph3, pw3, ph3), width=1, alpha=38)
    # Corner ornaments
    for cx2, cy2 in [(int(w * 0.07), int(h * 0.07)), (int(w * 0.93), int(h * 0.07)),
                     (int(w * 0.07), int(h * 0.93)), (int(w * 0.93), int(h * 0.93))]:
        r.draw_circle((200, 158, 28), (cx2, cy2), 11, alpha=115)
        r.draw_circle((240, 198, 58), (cx2, cy2), 7, alpha=95)


def _bg_dnd(r, w: int, h: int) -> None:
    """Deep indigo with concentric magic circles and rune points."""
    r.draw_rect((8, 6, 22), (0, 0, w, h))
    r.draw_rect((60, 20, 120), (0, 0, w, int(h * 0.12)), alpha=28)
    r.draw_rect((60, 20, 120), (0, h - int(h * 0.12), w, int(h * 0.12)), alpha=28)
    cx, cy = w // 2, h // 2
    # Concentric circles
    for radius_frac, alpha_val, width_val in [(0.40, 55, 2), (0.32, 38, 1), (0.24, 48, 2), (0.16, 35, 1)]:
        r.draw_circle((120, 60, 200), (cx, cy), int(min(w, h) * radius_frac), width=width_val, alpha=alpha_val)
    # Rune points
    for i in range(8):
        angle_rad = math.radians(i * 45)
        rx = int(cx + math.cos(angle_rad) * min(w, h) * 0.38)
        ry = int(cy + math.sin(angle_rad) * min(w, h) * 0.38)
        r.draw_circle((148, 78, 218), (rx, ry), 5, alpha=88)


def _bg_default(r, w: int, h: int) -> None:
    r.draw_rect((10, 10, 14), (0, 0, w, h))
    r.draw_circle((80, 80, 120), (w // 2, h // 2), int(min(w, h) * 0.40), alpha=8)


_BG_DISPATCH = {
    "blackjack": _bg_blackjack,
    "texas_holdem": _bg_texas_holdem,
    "texas_holdem_poker": _bg_texas_holdem,
    "uno": _bg_uno,
    "exploding_kittens": _bg_exploding_kittens,
    "monopoly": _bg_monopoly,
    "unstable_unicorns": _bg_unstable_unicorns,
    "catan": _bg_catan,
    "risk": _bg_risk,
    "cluedo": _bg_cluedo,
    "dnd": _bg_dnd,
    "d&d": _bg_dnd,
}
