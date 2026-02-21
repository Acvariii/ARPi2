from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

from core.player_selection import PlayerSelectionUI
from core.card_rendering import draw_label_card, draw_game_background
from config import PLAYER_COLORS
from core.animation import (
    ParticleSystem, CardFlyAnim, TextPopAnim, PulseRing, ScreenFlash,
    _RAINBOW_PALETTE as _FW_COLORS, draw_rainbow_title,
)


@dataclass(frozen=True)
class UnoCard:
    color: Optional[str]  # 'R','G','B','Y' or None for wild
    value: str  # '0'-'9' or 'skip'|'reverse'|'draw2'|'wild'|'wild_draw4'

    def short(self) -> str:
        if self.value == "wild":
            return "WILD"
        if self.value == "wild_draw4":
            return "WILD+4"
        if self.color is None:
            return str(self.value)
        sym = {
            "skip": "SKIP",
            "reverse": "REV",
            "draw2": "+2",
        }.get(self.value, self.value)
        return f"{self.color}{sym}"


class _WebButton:
    def __init__(self, text: str, enabled: bool = True):
        self.text = text
        self.enabled = enabled


@dataclass
class _Anim:
    kind: str  # 'draw' | 'play' | 'flip'
    from_rect: Tuple[float, float, float, float]
    to_rect: Tuple[float, float, float, float]
    duration: float
    elapsed: float = 0.0
    delay: float = 0.0
    label: str = ""
    face_color: Optional[Tuple[int, int, int]] = None


class UnoGame:
    """Uno (web-UI-first) game.

    The Pyglet server uses `buttons` for Web UI actions, and `selection_ui` for player select.
    This implementation keeps rules simple and playable:
    - No stacking draw cards.
    - Wild Draw 4 is always allowed (no "must not have matching color" enforcement).
    """

    def __init__(self, width: int, height: int, renderer=None):
        self.width = width
        self.height = height
        self.renderer = renderer

        self.state = "player_select"
        self.selection_ui = PlayerSelectionUI(width, height)

        self.active_players: List[int] = []
        self.current_player_idx: int = 0
        self.direction: int = 1

        self.hands: Dict[int, List[UnoCard]] = {}
        self.draw_pile: List[UnoCard] = []
        self.discard_pile: List[UnoCard] = []

        self.current_color: Optional[str] = None
        self.drew_this_turn: bool = False

        self.awaiting_color_choice: bool = False
        self.awaiting_color_player: Optional[int] = None

        self.winner: Optional[int] = None

        # Round reset / rematch readiness
        self._next_round_ready: Dict[int, bool] = {}

        # per-player pagination (for large hands)
        self._hand_page: Dict[int, int] = {}

        # Pyglet-board animation state
        self._anims: List[_Anim] = []
        self._last_event: str = ""
        self._last_event_age: float = 999.0

        # Web UI buttons
        self.buttons: Dict[int, Dict[str, _WebButton]] = {}

        # Optional callback for rendering real player names in the Pyglet board.
        # Signature: (seat:int) -> display name.
        self._seat_name_provider: Optional[Callable[[int], str]] = None

        # ── Particle animations ─────────────────────────────────────────────
        self._particles = ParticleSystem()
        self._anim_card_flips: list = []
        self._text_pops: list = []
        self._pulse_rings: list = []
        self._flashes: list = []
        self._anim_prev_winner: object = None
        self._anim_fw_timer: float = 0.0
        self._anim_prev_turn: object = None

    def set_name_provider(self, provider: Optional[Callable[[int], str]]) -> None:
        self._seat_name_provider = provider

    # --- Lifecycle ---

    def start_game(self, selected_indices: List[int]) -> None:
        seats = [int(i) for i in selected_indices if isinstance(i, int) or str(i).isdigit()]
        seats = [s for s in seats if 0 <= s <= 7]
        if len(seats) < 2:
            return

        self.active_players = seats
        self.current_player_idx = 0
        self.direction = 1
        self.hands = {s: [] for s in seats}
        self._hand_page = {s: 0 for s in seats}

        self.draw_pile = self._build_deck()
        random.shuffle(self.draw_pile)
        self.discard_pile = []
        self.current_color = None
        self.drew_this_turn = False
        self.awaiting_color_choice = False
        self.awaiting_color_player = None
        self.winner = None
        self._next_round_ready = {}

        # Deal 7 each (animate quickly in the Pyglet window)
        deal_delay = 0.0
        for _ in range(7):
            for s in seats:
                self._draw_to_hand(s, 1, animate=True, delay=deal_delay)
                deal_delay += 0.03

        # Flip start card (avoid wilds for first card) (animate face to discard)
        top = self._draw_pile_pop_nonwild(animate=True, delay=max(0.0, deal_delay + 0.08))
        if top is None:
            top = UnoCard("R", "0")
        self.discard_pile.append(top)
        self.current_color = top.color

        self._note_event(f"Start: {top.short()}")

        # Apply first card effect if action (simple handling)
        self._apply_card_effect(top, played_by=None)

        self.state = "playing"
        self._rebuild_buttons()

    def handle_player_quit(self, seat: int) -> None:
        """Handle a player disconnecting mid-game.

        Removes the seat from turn order and returns their hand to the draw pile so
        the game cannot get stuck waiting on a missing player.
        """
        try:
            s = int(seat)
        except Exception:
            return

        if self.state != "playing":
            return

        if self.winner is not None:
            return

        if s not in self.active_players:
            return

        was_turn = bool(self.current_turn_seat == s)

        # If we're waiting on a color selection from this seat, pick a color and continue.
        if bool(self.awaiting_color_choice) and int(self.awaiting_color_player or -1) == s:
            self.awaiting_color_choice = False
            self.awaiting_color_player = None
            # Choose something valid; prefer not None.
            self.current_color = random.choice(["R", "G", "B", "Y"])

        # Return their hand to the draw pile.
        hand = list(self.hands.pop(s, []) or [])
        if hand:
            self.draw_pile.extend(hand)
            random.shuffle(self.draw_pile)

        # Remove from turn order, keeping current_player_idx stable.
        try:
            removed_idx = self.active_players.index(s)
        except Exception:
            removed_idx = None

        self.active_players = [int(x) for x in self.active_players if int(x) != s]
        self._next_round_ready.pop(s, None)
        self._hand_page.pop(s, None)

        if not self.active_players:
            self.state = "player_select"
            self.current_player_idx = 0
            self._note_event("All players left")
            self._rebuild_buttons()
            return

        if len(self.active_players) == 1:
            self.winner = int(self.active_players[0])
            self._note_event(f"Winner: {self._seat_label(self.winner)}")
            self._rebuild_buttons()
            return

        if isinstance(removed_idx, int):
            if removed_idx < int(self.current_player_idx):
                self.current_player_idx = max(0, int(self.current_player_idx) - 1)
            if was_turn:
                self.current_player_idx = int(removed_idx) % len(self.active_players)

        if self.current_player_idx >= len(self.active_players):
            self.current_player_idx = 0

        # If they quit on their turn, ensure the game advances immediately.
        if was_turn:
            self.drew_this_turn = False

        self._note_event(f"{self._seat_label(s)} quit")
        self._rebuild_buttons()

    def update(self, dt: float) -> None:
        # Advance Pyglet-board animations.
        try:
            delta = float(dt)
        except Exception:
            delta = 0.0
        if delta < 0:
            delta = 0.0
        if delta > 0.2:
            delta = 0.2

        if self._last_event_age < 999.0:
            self._last_event_age += delta

        # ── Tick particle animations ──────────────────────────────────
        try:
            self._particles.update(delta)
            for _a in list(self._anim_card_flips): _a.update(delta)
            self._anim_card_flips = [_a for _a in self._anim_card_flips if not _a.done]
            for _a in list(self._text_pops): _a.update(delta)
            self._text_pops = [_a for _a in self._text_pops if not _a.done]
            for _a in list(self._pulse_rings): _a.update(delta)
            self._pulse_rings = [_a for _a in self._pulse_rings if not _a.done]
            for _a in list(self._flashes): _a.update(delta)
            self._flashes = [_a for _a in self._flashes if not _a.done]
            # Turn-change pulse + sparkle
            _curr_turn = getattr(self, 'current_turn_seat', None)
            if (
                self.state == "playing"
                and isinstance(_curr_turn, int)
                and _curr_turn != self._anim_prev_turn
                and isinstance(self._anim_prev_turn, int)
            ):
                _cx, _cy = self.width // 2, self.height // 2
                _col = _FW_COLORS[int(_curr_turn) % len(_FW_COLORS)]
                self._pulse_rings.append(PulseRing(_cx, _cy, _col, max_radius=min(self.width, self.height) // 5, duration=0.8))
                self._particles.emit_sparkle(_cx, _cy, _col, count=18)
            self._anim_prev_turn = _curr_turn
            if isinstance(self.winner, int) and self.winner is not self._anim_prev_winner:
                self._anim_prev_winner = self.winner
                _cx, _cy = self.width // 2, self.height // 2
                for _ in range(8):
                    self._particles.emit_firework(
                        _cx + random.randint(-120, 120), _cy + random.randint(-80, 80),
                        _FW_COLORS)
                self._flashes.append(ScreenFlash((255, 220, 80), 60, 1.0))
                self._text_pops.append(TextPopAnim(
                    f"🎉 {self._seat_label(self.winner)} wins!", _cx, _cy - 70,
                    (255, 220, 80), font_size=36))
                self._anim_fw_timer = 6.0
            if self._anim_fw_timer > 0:
                self._anim_fw_timer = max(0.0, self._anim_fw_timer - delta)
                if int(self._anim_fw_timer * 3) % 2 == 0:
                    _cx, _cy = self.width // 2, self.height // 2
                    self._particles.emit_firework(
                        _cx + random.randint(-150, 150), _cy + random.randint(-100, 100),
                        _FW_COLORS)
        except Exception:
            pass

        if not self._anims:
            return
        alive: List[_Anim] = []
        for a in self._anims:
            a.elapsed += delta
            # Keep until finished (including delay)
            if (a.elapsed - a.delay) < a.duration:
                alive.append(a)
        self._anims = alive

    def draw(self) -> None:
        # Render a simple Uno board (piles + per-seat zones) and animations.
        if not self.renderer:
            return
        try:
            w, h = int(getattr(self.renderer, "width", self.width)), int(getattr(self.renderer, "height", self.height))
        except Exception:
            w, h = self.width, self.height
        self._draw_background(w, h)

        title = "UNO"
        top = self.top_card
        turn = self.current_turn_seat
        status = f"Turn: {self._seat_label(turn)}" if isinstance(turn, int) else "Turn: —"
        tc = top.short() if top else "—"
        col = self.current_color or "—"

        # Header
        try:
            draw_rainbow_title(self.renderer, title, w)
            self.renderer.draw_text(
                f"Top: {tc}  ·  Color: {col}  ·  {status}",
                24,
                54,
                font_size=14,
                color=(200, 200, 200),
                anchor_x="left",
                anchor_y="top",
            )
        except Exception:
            pass

        # Board layout
        draw_rect, discard_rect = self._piles_rects(w, h)
        draw_cx, draw_cy = self._rect_center(draw_rect)
        disc_cx, disc_cy = self._rect_center(discard_rect)

        # Piles
        # Avoid newline rendering quirks (some backends ignore '\n' and concatenate).
        self._draw_card_back(draw_rect, label=f"DRAW {len(self.draw_pile)}")
        self._draw_discard(discard_rect)

        # Turn + direction indicator near center
        try:
            arrow = "⟳" if self.direction >= 0 else "⟲"
            acx = int((draw_cx + disc_cx) / 2)
            acy = int((draw_cy + disc_cy) / 2 - 70)
            # Glow ring
            self.renderer.draw_circle((255, 255, 255), (acx, acy), 22, alpha=15)
            self.renderer.draw_circle((255, 255, 255), (acx, acy), 22, width=2, alpha=60)
            self.renderer.draw_text(
                arrow, acx, acy,
                font_size=30, color=(255, 255, 255),
                anchor_x="center", anchor_y="center",
            )
        except Exception:
            pass

    def _draw_background(self, w: int, h: int) -> None:
        """Draw the colourful UNO background."""
        draw_game_background(self.renderer, w, h, "uno")

        # Seat zones + counts
        for seat in self.active_players:
            self._draw_seat_zone(int(seat), w, h)

        # Winner overlay
        if isinstance(self.winner, int):
            try:
                self.renderer.draw_rect((0, 0, 0), (0, 0, w, h), alpha=150)
                bw2, bh2 = min(600, int(w * 0.55)), 180
                bx2, by2 = w // 2 - bw2 // 2, h // 2 - bh2 // 2
                self.renderer.draw_rect((0, 0, 0), (bx2 + 5, by2 + 5, bw2, bh2), alpha=100)
                self.renderer.draw_rect((10, 10, 18), (bx2, by2, bw2, bh2), alpha=220)
                self.renderer.draw_rect((255, 215, 0), (bx2, by2, bw2, bh2), width=4, alpha=200)
                self.renderer.draw_circle((255, 215, 0), (w // 2, h // 2), int(min(bw2, bh2) * 0.3), alpha=12)
                self.renderer.draw_text(
                    "🏆", w // 2, h // 2 + 30, font_size=50,
                    color=(255, 215, 0), anchor_x="center", anchor_y="center",
                )
                self.renderer.draw_text(
                    f"Winner: {self._seat_label(self.winner)}",
                    w // 2 + 2, h // 2 - 22,
                    font_size=40, color=(0, 0, 0),
                    anchor_x="center", anchor_y="center", alpha=100,
                )
                self.renderer.draw_text(
                    f"Winner: {self._seat_label(self.winner)}",
                    w // 2, h // 2 - 24,
                    font_size=40, color=(255, 240, 180),
                    anchor_x="center", anchor_y="center",
                )
            except Exception:
                pass

        # Color choice prompt
        if self.awaiting_color_choice and isinstance(self.awaiting_color_player, int):
            try:
                self.renderer.draw_text(
                    f"{self._seat_label(self.awaiting_color_player)}: choose a color (Web UI)",
                    w // 2,
                    84,
                    font_size=14,
                    color=(210, 210, 210),
                    anchor_x="center",
                    anchor_y="top",
                )
            except Exception:
                pass

        # Last event (brief)
        if self._last_event and self._last_event_age < 4.5:
            try:
                ev = self._last_event
                ew = max(180, len(ev) * 8)
                eh = 22
                self.renderer.draw_rect((0, 0, 0), (20, 74, ew, eh), alpha=120)
                self.renderer.draw_text(
                    ev, 28, 85,
                    font_size=12, color=(200, 200, 200),
                    anchor_x="left", anchor_y="center",
                )
            except Exception:
                pass

        # Animations on top
        if self._anims:
            for a in list(self._anims):
                self._draw_anim(a)

        # ── Animation render layer ──────────────────────────────────────────
        try:
            if self.renderer:
                self._particles.draw(self.renderer)
                for _r in self._pulse_rings: _r.draw(self.renderer)
                for _f in self._anim_card_flips: _f.draw(self.renderer)
                for _fl in self._flashes: _fl.draw(self.renderer, self.width, self.height)
                for _p in self._text_pops: _p.draw(self.renderer)
        except Exception:
            pass

    # --- Snapshot helpers ---

    @property
    def top_card(self) -> Optional[UnoCard]:
        return self.discard_pile[-1] if self.discard_pile else None

    @property
    def current_turn_seat(self) -> Optional[int]:
        if not self.active_players:
            return None
        idx = self.current_player_idx % len(self.active_players)
        return int(self.active_players[idx])

    def get_public_state(self, player_idx: int) -> Dict:
        seat = int(player_idx) if isinstance(player_idx, int) else -1
        hand = list(self.hands.get(seat, []))
        counts = {int(s): int(len(self.hands.get(int(s), []))) for s in self.active_players}
        is_turn = bool(seat == self.current_turn_seat and self.winner is None)
        ready_map = {str(int(s)): bool(self._next_round_ready.get(int(s), False)) for s in self.active_players}
        ready_count = sum(1 for s in self.active_players if self._next_round_ready.get(int(s), False))
        return {
            "state": str(self.state),
            "active_players": list(self.active_players),
            "current_turn_seat": self.current_turn_seat,
            "direction": int(self.direction),
            "current_color": self.current_color,
            "top_card": self.top_card.short() if self.top_card else None,
            "hand_counts": counts,
            "your_hand": [
                {"idx": int(i), "text": c.short(), "playable": bool(is_turn and self._is_playable(c))}
                for i, c in enumerate(hand)
            ],
            "winner": self.winner,
            "awaiting_color": bool(self.awaiting_color_choice and self.awaiting_color_player == seat),
            "next_round_ready": ready_map,
            "next_round_ready_count": int(ready_count),
            "next_round_total": int(len(self.active_players)),
        }

    # --- Click handling ---

    def handle_click(self, player_idx: int, btn_id: str) -> None:
        if self.state != "playing":
            return
        if self.winner is not None:
            seat = int(player_idx)
            if seat not in self.active_players:
                return
            if btn_id == "play_again":
                # Mark this seat as ready for the next round.
                if seat not in self._next_round_ready:
                    self._next_round_ready[seat] = False
                self._next_round_ready[seat] = True
                self._note_event(f"{self._seat_label(seat)} is ready")
                # Auto-start when everyone is ready.
                if self.active_players and all(self._next_round_ready.get(int(s), False) for s in self.active_players):
                    self.start_game(list(self.active_players))
                    return
                self._rebuild_buttons()
                return
            if btn_id == "force_start":
                ready_seats = [int(s) for s in self.active_players if self._next_round_ready.get(int(s), False)]
                if len(ready_seats) >= 2:
                    self._note_event("Force start")
                    self.start_game(ready_seats)
                else:
                    self._rebuild_buttons()
                return
            return

        seat = int(player_idx)
        if seat not in self.active_players:
            return

        if self.awaiting_color_choice:
            if seat != self.awaiting_color_player:
                return
            if btn_id.startswith("color:"):
                col = btn_id.split(":", 1)[1]
                if col not in ("R", "G", "B", "Y"):
                    return
                self.current_color = col
                self.awaiting_color_choice = False
                self.awaiting_color_player = None
                self._note_event(f"{self._seat_label(seat)} chose {col}")
                self._end_turn()
                self._rebuild_buttons()
            return

        # Only current player can act
        if seat != self.current_turn_seat:
            return

        if btn_id == "draw":
            if self.drew_this_turn:
                return
            self._note_event(f"{self._seat_label(seat)} drew")
            self._draw_to_hand(seat, 1, animate=True)
            self.drew_this_turn = True
            # If no playable cards after drawing, allow ending.
            self._rebuild_buttons()
            return

        if btn_id == "end":
            # Must have drawn before ending; and must have no playable card left.
            if not self.drew_this_turn:
                return
            if self._has_playable_card(seat):
                return
            self._note_event(f"{self._seat_label(seat)} ended turn")
            self._end_turn()
            self._rebuild_buttons()
            return

        if btn_id == "page_prev":
            self._hand_page[seat] = max(0, int(self._hand_page.get(seat, 0)) - 1)
            self._rebuild_buttons()
            return

        if btn_id == "page_next":
            self._hand_page[seat] = int(self._hand_page.get(seat, 0)) + 1
            self._rebuild_buttons()
            return

        if btn_id.startswith("play:"):
            try:
                idx = int(btn_id.split(":", 1)[1])
            except Exception:
                return
            hand = self.hands.get(seat, [])
            if idx < 0 or idx >= len(hand):
                return
            card = hand[idx]
            if not self._is_playable(card):
                return

            self._note_event(f"{self._seat_label(seat)} played {card.short()}")
            self._queue_play_anim(seat, card)
            try:
                self._particles.emit_sparkle(self.width // 2, self.height // 2,
                                             _FW_COLORS[int(seat) % len(_FW_COLORS)], count=14)
            except Exception:
                pass

            # Remove from hand and discard
            hand.pop(idx)
            self.discard_pile.append(card)

            # Update current color/top
            if card.value in ("wild", "wild_draw4"):
                self.current_color = None
                self.awaiting_color_choice = True
                self.awaiting_color_player = seat
            else:
                self.current_color = card.color

            # Win check
            if not hand:
                self.winner = seat
                # Initialize next-round readiness for currently active seats.
                self._next_round_ready = {int(s): False for s in self.active_players}
                self._rebuild_buttons()
                return

            # UNO! alert when player drops to exactly 1 card
            if len(hand) == 1:
                try:
                    _cx, _cy = self.width // 2, self.height // 2
                    from config import PLAYER_COLORS as _PC
                    _col = _PC[int(seat) % len(_PC)]
                    self._text_pops.append(TextPopAnim("\U0001f6a8 UNO!", _cx, _cy - 50, _col, font_size=40))
                    self._flashes.append(ScreenFlash((220, 60, 60), 45, 0.4))
                    self._pulse_rings.append(PulseRing(_cx, _cy, _col, max_radius=90, duration=0.8))
                except Exception:
                    pass

            # Apply effects (may advance turn)
            self._apply_card_effect(card, played_by=seat)

            # If not awaiting color, end the turn by default
            if not self.awaiting_color_choice:
                self._end_turn()

            self.drew_this_turn = False
            self._rebuild_buttons()
            return

    # --- Internals ---

    def _build_deck(self) -> List[UnoCard]:
        deck: List[UnoCard] = []
        colors = ["R", "G", "B", "Y"]
        for c in colors:
            deck.append(UnoCard(c, "0"))
            for n in range(1, 10):
                deck.append(UnoCard(c, str(n)))
                deck.append(UnoCard(c, str(n)))
            for _ in range(2):
                deck.append(UnoCard(c, "skip"))
                deck.append(UnoCard(c, "reverse"))
                deck.append(UnoCard(c, "draw2"))
        for _ in range(4):
            deck.append(UnoCard(None, "wild"))
            deck.append(UnoCard(None, "wild_draw4"))
        return deck

    def _refill_from_discard(self) -> None:
        if len(self.discard_pile) <= 1:
            return
        top = self.discard_pile[-1]
        rest = self.discard_pile[:-1]
        self.discard_pile = [top]
        random.shuffle(rest)
        self.draw_pile.extend(rest)

    def _draw_pile_pop(self) -> Optional[UnoCard]:
        if not self.draw_pile:
            self._refill_from_discard()
        if not self.draw_pile:
            return None
        return self.draw_pile.pop()

    def _draw_pile_pop_nonwild(self, animate: bool = False, delay: float = 0.0) -> Optional[UnoCard]:
        for _ in range(200):
            c = self._draw_pile_pop()
            if c is None:
                return None
            if c.value not in ("wild", "wild_draw4"):
                if animate:
                    self._queue_flip_to_discard(c, delay=delay)
                return c
            # Put wilds back and try again later
            self.draw_pile.insert(0, c)
        c2 = self._draw_pile_pop()
        if c2 is not None and animate:
            self._queue_flip_to_discard(c2, delay=delay)
        return c2

    def _draw_to_hand(self, seat: int, n: int, animate: bool = False, delay: float = 0.0) -> None:
        hand = self.hands.setdefault(seat, [])
        for i in range(int(n)):
            c = self._draw_pile_pop()
            if c is None:
                break
            hand.append(c)
            if animate:
                self._queue_draw_anim(seat, delay=delay + i * 0.06)

    def _advance_index(self, steps: int = 1) -> None:
        if not self.active_players:
            return
        self.current_player_idx = (self.current_player_idx + (steps * self.direction)) % len(self.active_players)

    def _end_turn(self) -> None:
        self.drew_this_turn = False
        self._advance_index(1)

    def _is_playable(self, card: UnoCard) -> bool:
        top = self.top_card
        if top is None:
            return True
        if card.value in ("wild", "wild_draw4"):
            return True
        if self.current_color and card.color == self.current_color:
            return True
        if card.value == top.value and card.color is not None:
            return True
        return False

    def _has_playable_card(self, seat: int) -> bool:
        for c in self.hands.get(seat, []):
            if self._is_playable(c):
                return True
        return False

    def _apply_card_effect(self, card: UnoCard, played_by: Optional[int]) -> None:
        # Effects are applied immediately; turn advancement handled by caller.
        _cx, _cy = self.width // 2, self.height // 2
        if card.value == "reverse":
            if len(self.active_players) == 2:
                # In 2-player games reverse acts like skip
                self._advance_index(1)
            else:
                self.direction *= -1
            try:
                arrow = "→" if self.direction >= 0 else "←"
                self._text_pops.append(TextPopAnim(
                    f"🔄 REVERSE {arrow}", _cx, _cy - 30, (255, 175, 60), font_size=28))
                self._flashes.append(ScreenFlash((255, 175, 60), peak_alpha=45, duration=0.35))
                self._particles.emit_sparkle(_cx, _cy, (255, 175, 60), count=16)
            except Exception:
                pass
        elif card.value == "skip":
            self._advance_index(1)
            try:
                self._text_pops.append(TextPopAnim(
                    "⏭ SKIP!", _cx, _cy - 30, (230, 80, 80), font_size=28))
                self._flashes.append(ScreenFlash((230, 80, 80), peak_alpha=45, duration=0.35))
            except Exception:
                pass
        elif card.value == "draw2":
            # Next player draws 2 and is skipped
            self._advance_index(1)
            victim = self.current_turn_seat
            if isinstance(victim, int):
                self._note_event(f"{self._seat_label(victim)} drew +2")
                self._draw_to_hand(victim, 2, animate=True)
                self._advance_index(1)
            try:
                self._text_pops.append(TextPopAnim(
                    "+2 Cards! 🃏", _cx, _cy - 30, (80, 160, 235), font_size=28))
                self._flashes.append(ScreenFlash((80, 140, 230), 40, 0.35))
                self._particles.emit_sparkle(_cx, _cy, (80, 160, 235), count=16)
            except Exception:
                pass
        elif card.value == "wild_draw4":
            # Next player draws 4 and is skipped
            self._advance_index(1)
            victim = self.current_turn_seat
            if isinstance(victim, int):
                self._note_event(f"{self._seat_label(victim)} drew +4")
                self._draw_to_hand(victim, 4, animate=True)
                self._advance_index(1)
            try:
                self._text_pops.append(TextPopAnim(
                    "+4 Cards! 🃏", _cx, _cy - 30, (200, 90, 220), font_size=28))
                self._flashes.append(ScreenFlash((160, 60, 200), 40, 0.35))
                self._particles.emit_sparkle(_cx, _cy, (200, 90, 220), count=22)
            except Exception:
                pass

    def _rebuild_buttons(self) -> None:
        self.buttons = {}
        if self.state != "playing":
            return

        for seat in self.active_players:
            self.buttons[int(seat)] = self._build_player_buttons(int(seat))

    def _build_player_buttons(self, seat: int) -> Dict[str, _WebButton]:
        btns: Dict[str, _WebButton] = {}

        # Winner view: end-of-game flow is handled by the server/Web UI.
        if self.winner is not None:
            return btns

        is_turn = seat == self.current_turn_seat

        if self.awaiting_color_choice:
            if seat == self.awaiting_color_player:
                btns["color:R"] = _WebButton("Choose Red", True)
                btns["color:G"] = _WebButton("Choose Green", True)
                btns["color:B"] = _WebButton("Choose Blue", True)
                btns["color:Y"] = _WebButton("Choose Yellow", True)
            return btns

        # Primary actions
        btns["draw"] = _WebButton("Draw", enabled=bool(is_turn and not self.drew_this_turn))

        # Can only end your turn after you've drawn (or played a card, which auto-ends).
        can_end = bool(is_turn and self.drew_this_turn and not self._has_playable_card(seat))
        btns["end"] = _WebButton("End Turn", enabled=can_end)
        return btns

    def _seat_label(self, seat: int) -> str:
        try:
            s = int(seat)
        except Exception:
            return "Player"
        prov = getattr(self, "_seat_name_provider", None)
        if callable(prov):
            try:
                name = str(prov(s) or "").strip()
            except Exception:
                name = ""
            if name:
                return name
        return f"P{s + 1}"

    # --- Pyglet-board helpers ---

    def _note_event(self, text: str) -> None:
        t = (text or "").strip()
        if not t:
            return
        self._last_event = t
        self._last_event_age = 0.0

    def _color_rgb(self, c: Optional[str]) -> Tuple[int, int, int]:
        if c == "R":
            return (220, 70, 70)
        if c == "G":
            return (70, 200, 110)
        if c == "B":
            return (80, 140, 235)
        if c == "Y":
            return (235, 210, 80)
        return (180, 180, 180)

    def _card_rect(self, x: float, y: float, w: float, h: float) -> Tuple[float, float, float, float]:
        return (float(x), float(y), float(w), float(h))

    def _rect_center(self, r: Tuple[float, float, float, float]) -> Tuple[float, float]:
        x, y, w, h = r
        return (x + w / 2.0, y + h / 2.0)

    def _piles_rects(self, w: int, h: int) -> Tuple[Tuple[float, float, float, float], Tuple[float, float, float, float]]:
        cw = max(78, min(110, int(w * 0.09)))
        ch = int(cw * 1.42)
        cx = w // 2
        cy = h // 2
        gap = int(cw * 0.9)
        draw_rect = self._card_rect(cx - gap - cw, cy - ch / 2, cw, ch)
        discard_rect = self._card_rect(cx + gap, cy - ch / 2, cw, ch)
        return draw_rect, discard_rect

    def _seat_anchor(self, seat: int, w: int, h: int) -> Tuple[float, float]:
        # Top-left origin coordinates (matching renderer conventions).
        if seat in (0, 1, 2):
            xs = {0: 0.25, 1: 0.50, 2: 0.75}[seat]
            return (w * xs, h * 0.88)
        if seat in (3, 4, 5):
            xs = {3: 0.25, 4: 0.50, 5: 0.75}[seat]
            return (w * xs, h * 0.12)
        if seat == 6:
            return (w * 0.10, h * 0.50)
        if seat == 7:
            return (w * 0.90, h * 0.50)
        return (w * 0.5, h * 0.5)

    def _seat_card_target_rect(self, seat: int, w: int, h: int) -> Tuple[float, float, float, float]:
        cw = max(58, min(90, int(w * 0.07)))
        ch = int(cw * 1.42)
        ax, ay = self._seat_anchor(seat, w, h)
        return self._card_rect(ax - cw / 2, ay - ch / 2, cw, ch)

    def _queue_draw_anim(self, seat: int, delay: float = 0.0) -> None:
        try:
            w = int(getattr(self.renderer, "width", self.width))
            h = int(getattr(self.renderer, "height", self.height))
        except Exception:
            w, h = int(self.width), int(self.height)
        draw_rect, _ = self._piles_rects(w, h)
        to_rect = self._seat_card_target_rect(seat, w, h)
        self._anims.append(
            _Anim(
                kind="draw",
                from_rect=draw_rect,
                to_rect=to_rect,
                duration=0.28,
                elapsed=0.0,
                delay=max(0.0, float(delay)),
                label="",
                face_color=None,
            )
        )

    def _queue_play_anim(self, seat: int, card: UnoCard) -> None:
        try:
            w = int(getattr(self.renderer, "width", self.width))
            h = int(getattr(self.renderer, "height", self.height))
        except Exception:
            w, h = int(self.width), int(self.height)
        _, discard_rect = self._piles_rects(w, h)
        from_rect = self._seat_card_target_rect(seat, w, h)
        to_rect = discard_rect
        self._anims.append(
            _Anim(
                kind="play",
                from_rect=from_rect,
                to_rect=to_rect,
                duration=0.24,
                elapsed=0.0,
                delay=0.0,
                label=card.short(),
                face_color=self._color_rgb(card.color) if card.color is not None else (120, 120, 120),
            )
        )

    def _queue_flip_to_discard(self, card: UnoCard, delay: float = 0.0) -> None:
        try:
            w = int(getattr(self.renderer, "width", self.width))
            h = int(getattr(self.renderer, "height", self.height))
        except Exception:
            w, h = int(self.width), int(self.height)
        draw_rect, discard_rect = self._piles_rects(w, h)
        self._anims.append(
            _Anim(
                kind="flip",
                from_rect=draw_rect,
                to_rect=discard_rect,
                duration=0.26,
                elapsed=0.0,
                delay=max(0.0, float(delay)),
                label=card.short(),
                face_color=self._color_rgb(card.color) if card.color is not None else (120, 120, 120),
            )
        )

    def _draw_card_back(self, rect: Tuple[float, float, float, float], label: str = "") -> None:
        x, y, w, h = rect
        try:
            # Shadow
            self.renderer.draw_rect((0, 0, 0), (int(x + 4), int(y - 4), int(w), int(h)), alpha=70)
            # Body — dark red/maroon UNO back
            self.renderer.draw_rect((40, 10, 15), (int(x), int(y), int(w), int(h)), alpha=240)
            # Inner lighter stripe
            ip = max(4, int(min(w, h) * 0.08))
            self.renderer.draw_rect((70, 20, 25), (int(x + ip), int(y + ip), int(w - 2 * ip), int(h - 2 * ip)), alpha=100)
            # Border
            self.renderer.draw_rect((200, 50, 50), (int(x), int(y), int(w), int(h)), width=2, alpha=220)
            # Cross lines
            self.renderer.draw_line((180, 60, 50), (int(x + 8), int(y + 10)), (int(x + w - 8), int(y + h - 10)), width=2, alpha=120)
            self.renderer.draw_line((180, 60, 50), (int(x + w - 8), int(y + 10)), (int(x + 8), int(y + h - 10)), width=2, alpha=120)
            if label:
                self.renderer.draw_text(label, int(x + w / 2), int(y + h / 2), font_size=12, color=(255, 240, 200), anchor_x="center", anchor_y="center")
        except Exception:
            return

    def _draw_card_face(self, rect: Tuple[float, float, float, float], text: str, face_color: Tuple[int, int, int]) -> None:
        x, y, w, h = rect
        if not self.renderer:
            return
        draw_label_card(
            self.renderer,
            (int(x), int(y), int(w), int(h)),
            str(text or ""),
            face_color=tuple(int(v) for v in (face_color or (160, 160, 160))),
        )

    def _draw_discard(self, rect: Tuple[float, float, float, float]) -> None:
        top = self.top_card
        if top is None:
            self._draw_card_back(rect, label="DISCARD")
            return
        face = self._color_rgb(top.color)
        if top.value in ("wild", "wild_draw4"):
            # neutral face for wilds
            face = (120, 120, 120)
        self._draw_card_face(rect, top.short(), face)

    def _draw_seat_zone(self, seat: int, w: int, h: int) -> None:
        ax, ay = self._seat_anchor(seat, w, h)
        count = int(len(self.hands.get(seat, [])))
        is_turn = bool(self.current_turn_seat == seat)
        try:
            # Player colour
            pcol = PLAYER_COLORS[seat % len(PLAYER_COLORS)] if seat < len(PLAYER_COLORS) else (200, 200, 200)
            # Badge panel — wider & taller to avoid overlap
            bw, bh = 116, 46
            bx = int(ax) - bw // 2
            offset_y = 30 if seat in (3, 4, 5) else -30
            by = int(ay) + offset_y - bh // 2
            bg = (18, 18, 28)
            # Use player's own colour for turn ring
            border = pcol if is_turn else (140, 140, 150)
            self.renderer.draw_rect((0, 0, 0), (bx + 2, by + 2, bw, bh), alpha=60)
            self.renderer.draw_rect(bg, (bx, by, bw, bh), alpha=190)
            if is_turn:
                self.renderer.draw_rect(border, (bx - 3, by - 3, bw + 6, bh + 6), width=2, alpha=55)
            self.renderer.draw_rect(border, (bx, by, bw, bh), width=2 if is_turn else 1, alpha=200)
            # Player colour dot
            self.renderer.draw_circle(pcol, (bx + 10, by + 12), 4, alpha=180)
            # Name — top row
            name_col = (255, 240, 100) if is_turn else (210, 210, 210)
            self.renderer.draw_text(
                self._seat_label(seat),
                bx + 20, by + 6,
                font_size=11, color=name_col,
                anchor_x="left", anchor_y="top",
            )
            # Card count — bottom row, clearly separated
            self.renderer.draw_text(
                f"🃏 {count}", bx + 10, by + bh - 8,
                font_size=10, color=(200, 200, 200),
                anchor_x="left", anchor_y="bottom",
            )
        except Exception:
            pass

    def _draw_anim(self, a: _Anim) -> None:
        # Interpolate between rects; top-left origin
        t = (a.elapsed - a.delay)
        if t < 0:
            return
        if a.duration <= 0:
            u = 1.0
        else:
            u = max(0.0, min(1.0, t / a.duration))
        # ease-out cubic
        u2 = 1.0 - (1.0 - u) ** 3

        x0, y0, w0, h0 = a.from_rect
        x1, y1, w1, h1 = a.to_rect
        x = x0 + (x1 - x0) * u2
        y = y0 + (y1 - y0) * u2
        w = w0 + (w1 - w0) * u2
        h = h0 + (h1 - h0) * u2
        rect = self._card_rect(x, y, w, h)

        if a.kind == "draw":
            self._draw_card_back(rect)
        else:
            self._draw_card_face(rect, a.label or "", a.face_color or (160, 160, 160))
