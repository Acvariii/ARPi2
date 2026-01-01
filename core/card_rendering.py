from __future__ import annotations

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
        try:
            renderer.draw_text(str(emoji or ""), cx + 1, cy + 1, font_size=max(18, int(h * 0.36)), color=(0, 0, 0), alpha=90, anchor_x="center", anchor_y="center")
        except Exception:
            pass
        renderer.draw_text(str(emoji or ""), cx, cy, font_size=max(18, int(h * 0.36)), color=(255, 255, 255), alpha=255, anchor_x="center", anchor_y="center")

        # Title
        name = (title or "").strip()
        if name:
            renderer.draw_text(name[:18], cx, int(y + h * 0.18), font_size=max(10, int(h * 0.14)), color=(35, 35, 35), bold=True, anchor_x="center", anchor_y="center")
    except Exception:
        return
