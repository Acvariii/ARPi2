from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

from core.player_selection import PlayerSelectionUI
from core.card_rendering import draw_emoji_card, draw_game_background
from config import PLAYER_COLORS
from core.animation import (
    ParticleSystem, CardFlyAnim, TextPopAnim, PulseRing, ScreenFlash,
    _RAINBOW_PALETTE as _FW_COLORS, draw_rainbow_title,
)


@dataclass(frozen=True)
class EKCard:
    kind: str  # 'EK'|'DEF'|'ATK'|'SKIP'|'SHUF'|'FUT'|'FAV'|'NOPE'

    def short(self) -> str:
        return str(self.kind)


class _WebButton:
    def __init__(self, text: str, enabled: bool = True):
        self.text = text
        self.enabled = enabled


@dataclass
class _Anim:
    kind: str  # 'draw'|'play'
    from_rect: Tuple[float, float, float, float]
    to_rect: Tuple[float, float, float, float]
    duration: float
    elapsed: float = 0.0
    delay: float = 0.0
    label: str = ""
    face_color: Optional[Tuple[int, int, int]] = None


class ExplodingKittensGame:
    """Exploding Kittens (base-ish rules) in a Web-UI-first style.

    Implemented core rules:
    - Players take turns; usually end your turn by drawing.
    - Draw Exploding Kitten -> if you have Defuse, consume it and reinsert EK randomly; else you explode and are eliminated.
    - Action cards (on your turn): Attack, Skip, Shuffle, See the Future, Favor.
    - Nope: during a short window after a noppable action, other players with Nope may cancel (odd nopes cancel).

    Simplifications (kept minimal for this project):
    - Favor target gives a random card (no hand choice UI).
    - Defuse reinserts EK at a random position (no position choice UI).
    """

    def __init__(self, width: int, height: int, renderer=None):
        self.width = width
        self.height = height
        self.renderer = renderer

        self.state = "player_select"
        self.selection_ui = PlayerSelectionUI(width, height)

        self.active_players: List[int] = []
        self.eliminated_players: List[int] = []

        self.current_player_idx: int = 0

        self.hands: Dict[int, List[EKCard]] = {}
        self.draw_pile: List[EKCard] = []
        self.discard_pile: List[EKCard] = []

        # How many draws remaining for the current player before turn ends.
        self.pending_draws: int = 1

        # Favor target selection
        self.awaiting_favor_target: bool = False
        self.favor_actor: Optional[int] = None

        # Nope window
        self._nope_active: bool = False
        self._nope_deadline: float = 0.0
        self._nope_actor: Optional[int] = None
        self._nope_action: Optional[Tuple[str, Dict]] = None  # (action_kind, payload)
        self._nope_count: int = 0

        self.winner: Optional[int] = None

        # Pyglet board
        self._anims: List[_Anim] = []
        self._last_event: str = ""
        self._last_event_age: float = 999.0

        # Web UI buttons (panel_buttons)
        self.buttons: Dict[int, Dict[str, _WebButton]] = {}

        # Seat-name provider for Pyglet labels
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

        self.active_players = list(seats)
        self.eliminated_players = []
        self.current_player_idx = 0
        self.pending_draws = 1
        self.awaiting_favor_target = False
        self.favor_actor = None
        self._clear_nope()
        self.winner = None

        self.hands = {s: [] for s in seats}
        self.discard_pile = []

        # Standard EK dealing: deal all players from a deck WITHOUT EKs,
        # then add EKs (players-1) and shuffle.
        self.draw_pile = self._build_deck(player_count=len(seats), include_ek=False)
        random.shuffle(self.draw_pile)

        # Deal: 1 Defuse + 7 random cards.
        for s in seats:
            self.hands[s].append(EKCard("DEF"))
        for _ in range(7):
            for s in seats:
                c = self._draw_card(raw=True)
                if c is None:
                    break
                self.hands[s].append(c)

        for _ in range(max(1, int(len(seats)) - 1)):
            self.draw_pile.append(EKCard("EK"))
        random.shuffle(self.draw_pile)

        self._note_event("Exploding Kittens: start")
        self.state = "playing"
        self._rebuild_buttons()

    def handle_player_quit(self, seat: int) -> None:
        """Handle a player disconnecting mid-game.

        Goals:
        - Never leave the game waiting on a seat that no longer exists.
        - Return their hand to the draw pile.
        - If they were the current turn / actor for a pending prompt, advance safely.
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

        # Return hand to draw pile.
        hand = list(self.hands.pop(s, []) or [])
        if hand:
            self.draw_pile.extend(hand)
            random.shuffle(self.draw_pile)

        # Remove from active players, tracking their prior index.
        try:
            removed_idx = self.active_players.index(s)
        except Exception:
            removed_idx = None

        was_turn = bool(self.current_turn_seat == s)

        try:
            self.active_players = [int(x) for x in self.active_players if int(x) != s]
        except Exception:
            self.active_players = [x for x in self.active_players if x != s]

        if s not in self.eliminated_players:
            self.eliminated_players.append(int(s))

        # If we were waiting on them for Favor targeting, cancel.
        if bool(self.awaiting_favor_target) and int(self.favor_actor or -1) == s:
            self.awaiting_favor_target = False
            self.favor_actor = None

        # If they were involved in an active NOPE window, cancel it.
        if bool(self._nope_active):
            if int(self._nope_actor or -1) == s:
                self._clear_nope()
            else:
                # Still cancel to avoid awkward "waiting" states around a quit.
                self._clear_nope()

        # If nobody left, reset to player_select.
        if not self.active_players:
            self.pending_draws = 1
            self.current_player_idx = 0
            self.awaiting_favor_target = False
            self.favor_actor = None
            self._clear_nope()
            self.state = "player_select"
            self._note_event("All players left")
            self._rebuild_buttons()
            return

        # Winner if only one remains.
        if len(self.active_players) == 1:
            self.winner = int(self.active_players[0])
            self.pending_draws = 1
            self._note_event(f"Winner: {self._seat_label(self.winner)}")
            self._rebuild_buttons()
            return

        # Keep current_player_idx consistent.
        if isinstance(removed_idx, int):
            if removed_idx < int(self.current_player_idx):
                self.current_player_idx = max(0, int(self.current_player_idx) - 1)
            if was_turn:
                # Next player now occupies the removed index.
                self.current_player_idx = int(removed_idx) % len(self.active_players)

        if self.current_player_idx >= len(self.active_players):
            self.current_player_idx = 0

        # Reset per-turn draw expectation so we don't wait on a quitter's draw.
        if was_turn:
            self.pending_draws = 1

        self._note_event(f"{self._seat_label(s)} quit")
        self._rebuild_buttons()

    def update(self, dt: float) -> None:
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

        if self._nope_active:
            self._nope_deadline -= delta
            if self._nope_deadline <= 0:
                self._resolve_nope_window()

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
                self._flashes.append(ScreenFlash(_col, peak_alpha=40, duration=0.3))
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
                    f"🏆 {self._seat_label(self.winner)} wins!", _cx, _cy - 60,
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
            if (a.elapsed - a.delay) < a.duration:
                alive.append(a)
        self._anims = alive

    # --- Snapshot ---

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
        can_nope = bool(self._nope_active and seat != self._nope_actor and self._has_card(seat, "NOPE"))

        def _card_playable(c: EKCard) -> bool:
            if self.winner is not None:
                return False
            if can_nope:
                return c.kind == "NOPE"
            if not is_turn:
                return False
            # On turn you can always play action cards; DEF only used automatically.
            return c.kind in ("ATK", "SKIP", "SHUF", "FUT", "FAV")

        return {
            "state": str(self.state),
            "active_players": list(self.active_players),
            "eliminated_players": list(self.eliminated_players),
            "current_turn_seat": self.current_turn_seat,
            "pending_draws": int(self.pending_draws),
            "deck_count": int(len(self.draw_pile)),
            "discard_top": self.discard_pile[-1].short() if self.discard_pile else None,
            "last_event": self._last_event if (self._last_event and float(self._last_event_age or 999.0) < 6.0) else None,
            "last_event_age_ms": int(float(self._last_event_age or 999.0) * 1000),
            "hand_counts": counts,
            "your_hand": [
                {"idx": int(i), "text": c.short(), "playable": bool(_card_playable(c))}
                for i, c in enumerate(hand)
            ],
            "awaiting_favor_target": bool(self.awaiting_favor_target and self.favor_actor == seat),
            "nope_active": bool(self._nope_active),
            "nope_count": int(self._nope_count),
            "winner": self.winner,
        }

    # --- Click handling ---

    def handle_click(self, player_idx: int, btn_id: str) -> None:
        if self.state != "playing":
            return
        if self.winner is not None:
            return

        seat = int(player_idx)
        if seat not in self.active_players:
            return

        # Nope window: other players may respond.
        if self._nope_active and seat != self._nope_actor:
            if btn_id == "ek_nope":
                if not self._has_card(seat, "NOPE"):
                    return
                self._remove_one(seat, "NOPE")
                self.discard_pile.append(EKCard("NOPE"))
                self._nope_count += 1
                self._note_event(f"{self._seat_label(seat)} played NOPE")
                try:
                    _cx, _cy = self.width // 2, self.height // 2
                    self._flashes.append(ScreenFlash((200, 80, 20), 55, 0.3))
                    self._text_pops.append(TextPopAnim(
                        "🚫 NOPE!", _cx, _cy - 40, (230, 100, 50), font_size=32))
                except Exception:
                    pass
                self._rebuild_buttons()
            elif btn_id.startswith("ek_play:"):
                # UX convenience: allow clicking the NOPE card itself.
                try:
                    idx = int(btn_id.split(":", 1)[1])
                except Exception:
                    return
                hand = self.hands.get(seat, [])
                if idx < 0 or idx >= len(hand):
                    return
                if hand[idx].kind != "NOPE":
                    return
                hand.pop(idx)
                self.discard_pile.append(EKCard("NOPE"))
                self._nope_count += 1
                self._note_event(f"{self._seat_label(seat)} played NOPE")
                try:
                    _cx, _cy = self.width // 2, self.height // 2
                    self._flashes.append(ScreenFlash((200, 80, 20), 55, 0.3))
                    self._text_pops.append(TextPopAnim(
                        "🚫 NOPE!", _cx, _cy - 40, (230, 100, 50), font_size=32))
                except Exception:
                    pass
                self._rebuild_buttons()
            return

        # Favor target selection
        if self.awaiting_favor_target:
            if seat != self.favor_actor:
                return
            if btn_id.startswith("favor_target:"):
                try:
                    target = int(btn_id.split(":", 1)[1])
                except Exception:
                    return
                if target not in self.active_players or target == seat:
                    return
                self._execute_favor(seat, target)
                self.awaiting_favor_target = False
                self.favor_actor = None
                self._rebuild_buttons()
            return

        # Only current player can act.
        if seat != self.current_turn_seat:
            return

        if btn_id == "ek_draw":
            self._do_draw(seat)
            return

        if btn_id.startswith("ek_play:"):
            try:
                idx = int(btn_id.split(":", 1)[1])
            except Exception:
                return
            hand = self.hands.get(seat, [])
            if idx < 0 or idx >= len(hand):
                return
            card = hand[idx]
            if card.kind not in ("ATK", "SKIP", "SHUF", "FUT", "FAV"):
                return

            # Remove from hand to discard.
            hand.pop(idx)
            self.discard_pile.append(card)
            self._queue_play_anim(seat, card)

            # Action card sparkle + flash
            try:
                _cx, _cy = self.width // 2, self.height // 2
                _action_cols = {'ATK': (230, 60, 60), 'SKIP': (255, 200, 50), 'SHUF': (100, 180, 255), 'FUT': (150, 100, 255), 'FAV': (255, 130, 200)}
                _acol = _action_cols.get(card.kind, (200, 200, 200))
                self._particles.emit_sparkle(_cx, _cy, _acol, count=16)
                self._flashes.append(ScreenFlash(_acol, peak_alpha=35, duration=0.3))
            except Exception:
                pass

            # Execute card (some open a nope window).
            self._play_action(seat, card)
            self._rebuild_buttons()
            return

    # --- Internals: rules ---

    def _build_deck(self, player_count: int, include_ek: bool = True) -> List[EKCard]:
        # Base-ish deck composition (simplified).
        out: List[EKCard] = []

        # Exploding kittens: players-1 (added after dealing)
        if include_ek:
            for _ in range(max(1, int(player_count) - 1)):
                out.append(EKCard("EK"))

        # Extra defuses in deck to keep game playable.
        for _ in range(2):
            out.append(EKCard("DEF"))

        # Action cards
        for kind, count in (
            ("ATK", 4),
            ("SKIP", 4),
            ("SHUF", 4),
            ("FUT", 5),
            ("FAV", 4),
            ("NOPE", 5),
        ):
            for _ in range(count):
                out.append(EKCard(kind))

        return out

    def _has_card(self, seat: int, kind: str) -> bool:
        return any(c.kind == kind for c in self.hands.get(seat, []))

    def _remove_one(self, seat: int, kind: str) -> bool:
        hand = self.hands.get(seat, [])
        for i, c in enumerate(list(hand)):
            if c.kind == kind:
                hand.pop(i)
                return True
        return False

    def _do_draw(self, seat: int) -> None:
        if self.pending_draws <= 0:
            return

        c = self._draw_card(raw=False)
        if c is None:
            # Extremely rare with discard refill; avoid soft-locks.
            self._note_event("Deck empty")
            if self.winner is None and len(self.active_players) == 1:
                self.winner = int(self.active_players[0])
                self._note_event(f"Winner: {self._seat_label(self.winner)}")
                self._rebuild_buttons()
                return
            self.pending_draws = 0
            self._advance_turn_if_done()
            self._rebuild_buttons()
            return

        self._queue_draw_anim(seat)
        self._note_event(f"{self._seat_label(seat)} drew")

        if c.kind == "EK":
            # Immediately resolve explosion.
            if self._has_card(seat, "DEF"):
                self._remove_one(seat, "DEF")
                self.discard_pile.append(EKCard("DEF"))
                # Reinsert EK at random position.
                self._reinsert_random(EKCard("EK"))
                self._note_event(f"{self._seat_label(seat)} defused!")
                # Defuse animation
                try:
                    _cx, _cy = self.width // 2, self.height // 2
                    self._flashes.append(ScreenFlash((60, 200, 100), 60, 0.4))
                    self._text_pops.append(TextPopAnim(
                        f"🧰 DEFUSED! {self._seat_label(seat)}",
                        _cx, _cy - 40, (80, 230, 130), font_size=30))
                    self._particles.emit_sparkle(_cx, _cy, (80, 230, 130), count=22)
                except Exception:
                    pass
            else:
                self._explode(seat)
                return
        else:
            # Normal card drawn into hand.
            self.hands.setdefault(seat, []).append(c)

        self.pending_draws -= 1
        self._advance_turn_if_done()
        self._rebuild_buttons()

    def _draw_card(self, raw: bool) -> Optional[EKCard]:
        # raw=True draws without triggering special resolution (used for dealing).
        if not self.draw_pile:
            self._refill_draw_pile_from_discard()
        if not self.draw_pile:
            return None
        return self.draw_pile.pop()

    def _refill_draw_pile_from_discard(self) -> None:
        """When the draw pile is empty, recycle discard (keeping the top card).

        Exploding Kittens decks typically don't run out in normal play, but this
        prevents deadlocks in a simplified implementation.
        """
        try:
            disc = list(self.discard_pile or [])
        except Exception:
            disc = []
        if len(disc) <= 1:
            return
        top = disc[-1]
        refill = disc[:-1]
        random.shuffle(refill)
        self.draw_pile.extend(refill)
        self.discard_pile = [top]

    def _reinsert_random(self, card: EKCard) -> None:
        if not self.draw_pile:
            self.draw_pile.append(card)
            return
        pos = random.randint(0, len(self.draw_pile))
        self.draw_pile.insert(pos, card)

    def _explode(self, seat: int) -> None:
        # Eliminate a player.
        if seat in self.active_players:
            self.active_players = [s for s in self.active_players if int(s) != int(seat)]
        if seat not in self.eliminated_players:
            self.eliminated_players.append(int(seat))

        self._note_event(f"{self._seat_label(seat)} player exploded")

        # Explosion animations!
        try:
            _cx, _cy = self.width // 2, self.height // 2
            self._flashes.append(ScreenFlash((255, 80, 30), 80, 0.5))
            self._text_pops.append(TextPopAnim(
                f"💥 KABOOM! {self._seat_label(seat)}",
                _cx, _cy - 50, (255, 90, 40), font_size=36))
            for _ in range(6):
                import random as _rnd
                self._particles.emit_firework(
                    _cx + _rnd.randint(-140, 140), _cy + _rnd.randint(-90, 90),
                    [(220, 60, 20), (255, 140, 0), (255, 220, 0)])
        except Exception:
            pass

        # If only one remains, winner.
        if len(self.active_players) == 1:
            self.winner = int(self.active_players[0])
            self._note_event(f"Winner: {self._seat_label(self.winner)}")
            self._rebuild_buttons()
            return

        # Keep turn index in range.
        if self.current_player_idx >= len(self.active_players):
            self.current_player_idx = 0
        self.pending_draws = 1
        self._clear_nope()
        self.awaiting_favor_target = False
        self.favor_actor = None
        self._rebuild_buttons()

    def _advance_turn_if_done(self) -> None:
        if self.winner is not None:
            return
        if self.pending_draws > 0:
            return
        self._advance_index(1)
        self.pending_draws = 1

    def _advance_index(self, steps: int) -> None:
        if not self.active_players:
            return
        self.current_player_idx = (self.current_player_idx + int(steps)) % len(self.active_players)

    def _play_action(self, seat: int, card: EKCard) -> None:
        kind = card.kind
        self._note_event(f"{self._seat_label(seat)} played {kind}")

        # Noppable actions: open a short window for NOPE.
        if kind in ("ATK", "SKIP", "SHUF", "FUT", "FAV"):
            self._open_nope_window(actor=seat, action_kind=kind, payload={})
        else:
            self._apply_action(kind, {})

    def _open_nope_window(self, actor: int, action_kind: str, payload: Dict) -> None:
        self._nope_active = True
        self._nope_deadline = 3.0
        self._nope_actor = int(actor)
        self._nope_action = (str(action_kind), dict(payload or {}))
        self._nope_count = 0

    def _resolve_nope_window(self) -> None:
        if not self._nope_active or not self._nope_action:
            self._clear_nope()
            return
        kind, payload = self._nope_action
        canceled = bool(self._nope_count % 2 == 1)
        if canceled:
            self._note_event("NOPE!")
        else:
            self._apply_action(kind, payload)
        self._clear_nope()
        self._rebuild_buttons()

    def _clear_nope(self) -> None:
        self._nope_active = False
        self._nope_deadline = 0.0
        self._nope_actor = None
        self._nope_action = None
        self._nope_count = 0

    def _apply_action(self, kind: str, payload: Dict) -> None:
        seat = self.current_turn_seat
        if not isinstance(seat, int):
            return

        if kind == "SHUF":
            random.shuffle(self.draw_pile)
            self._note_event("Shuffled")
            return

        if kind == "FUT":
            # No special state; UI will show top 3 in snapshot via an event only.
            top3 = [c.short() for c in list(reversed(self.draw_pile[-3:]))]
            if top3:
                self._note_event("Future: " + ", ".join(top3))
            return

        if kind == "FAV":
            self.awaiting_favor_target = True
            self.favor_actor = int(seat)
            self._note_event("Choose a target")
            return

        if kind == "SKIP":
            self.pending_draws = 0
            self._advance_turn_if_done()
            return

        if kind == "ATK":
            # End your turn without drawing; next player takes 2 draws.
            self.pending_draws = 0
            self._advance_turn_if_done()
            self.pending_draws = 2
            self._note_event("Attack!")
            return

    def _execute_favor(self, actor: int, target: int) -> None:
        t_hand = self.hands.get(int(target), [])
        if not t_hand:
            self._note_event("Favor: no cards")
            return
        take = random.choice(t_hand)
        # remove one instance
        for i, c in enumerate(list(t_hand)):
            if c is take:
                t_hand.pop(i)
                break
        self.hands.setdefault(int(actor), []).append(take)
        self._note_event(f"Favor: {self._seat_label(actor)} took a card")

    # --- Web UI buttons ---

    def _rebuild_buttons(self) -> None:
        self.buttons = {}
        if self.state != "playing":
            return
        for s in self.active_players:
            self.buttons[int(s)] = self._build_player_buttons(int(s))
        # Also allow NOPE for non-actors while a nope window is active.
        if self._nope_active:
            for s in self.active_players:
                seat = int(s)
                if seat == self._nope_actor:
                    continue
                if self._has_card(seat, "NOPE"):
                    self.buttons.setdefault(seat, {})["ek_nope"] = _WebButton("NOPE", True)

    def _build_player_buttons(self, seat: int) -> Dict[str, _WebButton]:
        btns: Dict[str, _WebButton] = {}

        if self.winner is not None:
            return btns

        # Favor targeting: only actor gets target buttons.
        if self.awaiting_favor_target and seat == self.favor_actor:
            for t in self.active_players:
                if int(t) == int(seat):
                    continue
                btns[f"favor_target:{int(t)}"] = _WebButton(f"Favor: {self._seat_label(int(t))}", True)
            return btns

        is_turn = bool(seat == self.current_turn_seat)
        btns["ek_draw"] = _WebButton("Draw", enabled=bool(is_turn and self.pending_draws > 0))
        return btns

    # --- Pyglet board (minimal) ---

    def _draw_background(self, w: int, h: int) -> None:
        """Draw the Exploding Kittens themed background."""
        draw_game_background(self.renderer, w, h, "exploding_kittens")

    def draw(self) -> None:
        if not self.renderer:
            return
        try:
            w, h = int(getattr(self.renderer, "width", self.width)), int(getattr(self.renderer, "height", self.height))
        except Exception:
            w, h = self.width, self.height
        self._draw_background(w, h)

        try:
            title = "EXPLODING KITTENS"
            status = f"Turn: {self._seat_label(self.current_turn_seat)}" if isinstance(self.current_turn_seat, int) else "Turn: —"
            draw_rainbow_title(self.renderer, title, w, font_size=20)
            self.renderer.draw_text(
                f"Deck: {len(self.draw_pile)}  ·  Discard: {self.discard_pile[-1].short() if self.discard_pile else '—'}  ·  {status}  ·  Draws: {self.pending_draws}",
                24,
                54,
                font_size=14,
                color=(200, 200, 200),
                anchor_x="left",
                anchor_y="top",
            )
        except Exception:
            pass

        # Piles
        draw_rect, disc_rect = self._piles_rects(w, h)

        # Subtle table highlight behind piles
        try:
            cx, cy = w // 2, h // 2
            self.renderer.draw_circle((80, 30, 100), (cx, cy), int(min(w, h) * 0.18), alpha=20)
            self.renderer.draw_circle((140, 60, 180), (cx, cy), int(min(w, h) * 0.12), alpha=15)
        except Exception:
            pass
        self._draw_card_back(draw_rect, label=f"DECK {len(self.draw_pile)}")
        self._draw_discard(disc_rect)

        # Seat zones
        for s in self.active_players:
            self._draw_seat_zone(int(s), w, h)

        # Winner overlay
        if isinstance(self.winner, int):
            try:
                self.renderer.draw_rect((0, 0, 0), (0, 0, w, h), alpha=150)
                bw2, bh2 = min(600, int(w * 0.55)), 180
                bx2, by2 = w // 2 - bw2 // 2, h // 2 - bh2 // 2
                self.renderer.draw_rect((0, 0, 0), (bx2 + 5, by2 + 5, bw2, bh2), alpha=100)
                self.renderer.draw_rect((18, 10, 24), (bx2, by2, bw2, bh2), alpha=225)
                self.renderer.draw_rect((255, 180, 40), (bx2, by2, bw2, bh2), width=4, alpha=200)
                self.renderer.draw_circle((255, 180, 40), (w // 2, h // 2), int(min(bw2, bh2) * 0.3), alpha=12)
                self.renderer.draw_text(
                    "😼", w // 2, h // 2 + 30, font_size=48,
                    color=(255, 200, 60), anchor_x="center", anchor_y="center",
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

        if self._last_event and self._last_event_age < 4.5:
            try:
                ev = self._last_event
                ew = max(180, len(ev) * 8)
                eh = 22
                self.renderer.draw_rect((0, 0, 0), (20, 74, ew, eh), alpha=120)
                self.renderer.draw_rect((200, 140, 255), (20, 74, ew, eh), width=1, alpha=40)
                self.renderer.draw_text(
                    ev, 28, 85,
                    font_size=12, color=(210, 200, 230),
                    anchor_x="left", anchor_y="center",
                )
            except Exception:
                pass

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

    def _note_event(self, text: str) -> None:
        t = (text or "").strip()
        if not t:
            return
        self._last_event = t
        self._last_event_age = 0.0

    def _seat_label(self, seat: Optional[int]) -> str:
        if not isinstance(seat, int):
            return "Player"
        prov = getattr(self, "_seat_name_provider", None)
        if callable(prov):
            try:
                name = str(prov(int(seat)) or "").strip()
            except Exception:
                name = ""
            if name:
                return name
        return f"P{int(seat) + 1}"

    def _color_rgb(self, kind: str) -> Tuple[int, int, int]:
        if kind == "EK":
            return (220, 80, 80)
        if kind == "DEF":
            return (80, 200, 130)
        if kind == "NOPE":
            return (120, 120, 120)
        return (90, 160, 235)

    def _card_rect(self, x: float, y: float, w: float, h: float) -> Tuple[float, float, float, float]:
        return (float(x), float(y), float(w), float(h))

    def _piles_rects(self, w: int, h: int) -> Tuple[Tuple[float, float, float, float], Tuple[float, float, float, float]]:
        cw = max(78, min(110, int(w * 0.09)))
        ch = int(cw * 1.42)
        cx = w // 2
        cy = h // 2
        gap = int(cw * 0.9)
        draw_rect = self._card_rect(cx - gap - cw, cy - ch / 2, cw, ch)
        discard_rect = self._card_rect(cx + gap, cy - ch / 2, cw, ch)
        return draw_rect, discard_rect

    def _rect_center(self, r: Tuple[float, float, float, float]) -> Tuple[float, float]:
        x, y, w, h = r
        return (x + w / 2.0, y + h / 2.0)

    def _seat_anchor(self, seat: int, w: int, h: int) -> Tuple[float, float]:
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

    def _queue_play_anim(self, seat: int, card: EKCard) -> None:
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
                face_color=self._color_rgb(card.kind),
            )
        )

    def _draw_card_back(self, rect: Tuple[float, float, float, float], label: str = "") -> None:
        x, y, w, h = rect
        try:
            # Slight shadow
            self.renderer.draw_rect((0, 0, 0), (int(x + 4), int(y - 4), int(w), int(h)), alpha=70)

            # Face
            self.renderer.draw_rect((28, 20, 38), (int(x), int(y), int(w), int(h)), alpha=235)
            self.renderer.draw_rect((200, 140, 255), (int(x), int(y), int(w), int(h)), width=2, alpha=210)
            self.renderer.draw_line(
                (240, 200, 90),
                (int(x + 10), int(y + 12)),
                (int(x + w - 10), int(y + h - 12)),
                width=2,
                alpha=160,
            )
            if label:
                self.renderer.draw_text(label, int(x + w / 2), int(y + h / 2), font_size=12, color=(230, 230, 230), anchor_x="center", anchor_y="center")
        except Exception:
            pass

    def _draw_card_face(self, rect: Tuple[float, float, float, float], text: str, face_color: Tuple[int, int, int]) -> None:
        x, y, w, h = rect
        try:
            t = str(text or "").strip().upper()

            # Emoji + title mapping
            emoji = "😺"
            title = t or ""
            if t == "EK":
                emoji, title = "💣😼", "EXPLODING"
            elif t == "DEF":
                emoji, title = "🧯", "DEFUSE"
            elif t == "ATK":
                emoji, title = "⚔", "ATTACK"
            elif t == "SKIP":
                emoji, title = "⏭", "SKIP"
            elif t == "SHUF":
                emoji, title = "🔀", "SHUFFLE"
            elif t == "FUT":
                emoji, title = "🔮", "FUTURE"
            elif t == "FAV":
                emoji, title = "🎁", "FAVOR"
            elif t == "NOPE":
                emoji, title = "🚫", "NOPE"

            fc = tuple(int(v) for v in (face_color or (160, 160, 160)))
            draw_emoji_card(
                self.renderer,
                (int(x), int(y), int(w), int(h)),
                emoji=str(emoji),
                title="",
                accent_rgb=fc,
                corner=str(t or "EK"),
            )
        except Exception:
            return

    def _draw_discard(self, rect: Tuple[float, float, float, float]) -> None:
        top = self.discard_pile[-1] if self.discard_pile else None
        if top is None:
            self._draw_card_back(rect, label="DISCARD")
            return
        self._draw_card_face(rect, top.short(), self._color_rgb(top.kind))
        try:
            x, y, w, h = rect
            self.renderer.draw_text(
                "DISCARD",
                int(x + w / 2),
                int(y - 18),
                font_size=10,
                color=(200, 200, 200),
                anchor_x="center",
                anchor_y="top",
            )
        except Exception:
            pass

    def _draw_seat_zone(self, seat: int, w: int, h: int) -> None:
        ax, ay = self._seat_anchor(seat, w, h)
        count = int(len(self.hands.get(seat, [])))
        is_turn = bool(self.current_turn_seat == seat)

        try:
            rx, ry, rw, rh = self._seat_card_target_rect(seat, w, h)
            # Shadow
            self.renderer.draw_rect((0, 0, 0), (int(rx + 3), int(ry - 3), int(rw), int(rh)), alpha=70)
            # Card placeholder body
            bg = (28, 16, 36) if is_turn else (18, 18, 24)
            self.renderer.draw_rect(bg, (int(rx), int(ry), int(rw), int(rh)), alpha=190)
            # Turn glow ring
            outline = (250, 200, 70) if is_turn else (140, 120, 160)
            if is_turn:
                self.renderer.draw_rect(outline, (int(rx - 2), int(ry - 2), int(rw + 4), int(rh + 4)), width=2, alpha=50)
            self.renderer.draw_rect(outline, (int(rx), int(ry), int(rw), int(rh)), width=2 if is_turn else 1, alpha=200)
            # Cat emoji watermark
            self.renderer.draw_text(
                "😺", int(rx + rw / 2), int(ry + rh / 2 + 12),
                font_size=18, color=(200, 200, 200), anchor_x="center", anchor_y="center", alpha=40,
            )
            # Count badge
            self.renderer.draw_text(
                str(count), int(rx + rw / 2), int(ry + rh / 2 - 4),
                font_size=16, color=(240, 240, 240), bold=True,
                anchor_x="center", anchor_y="center",
            )
        except Exception:
            pass

        # Player name with colour dot
        try:
            pcol = PLAYER_COLORS[seat % len(PLAYER_COLORS)]
        except Exception:
            pcol = (200, 200, 200)
        name_col = (250, 220, 100) if is_turn else (205, 205, 205)
        try:
            name_y = int(ay + (42 if seat in (3, 4, 5) else -42))
            self.renderer.draw_circle(pcol, (int(ax) - 40, name_y), 4, alpha=180)
            self.renderer.draw_text(
                f"{self._seat_label(seat)}" + ("  ★" if is_turn else ""),
                int(ax), name_y,
                font_size=12, color=name_col,
                anchor_x="center", anchor_y="center",
            )
        except Exception:
            pass

    def _draw_anim(self, a: _Anim) -> None:
        t = (a.elapsed - a.delay)
        if t < 0:
            return
        u = 1.0 if a.duration <= 0 else max(0.0, min(1.0, t / a.duration))
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
