from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from core.player_selection import PlayerSelectionUI
from core.card_rendering import draw_emoji_card, draw_game_background
from core.animation import (
    ParticleSystem, CardFlyAnim, TextPopAnim, PulseRing, ScreenFlash,
    _RAINBOW_PALETTE as _UU_FW_COLORS, draw_rainbow_title,
)


@dataclass(frozen=True)
class UUCardDef:
    id: str
    name: str
    kind: str  # baby_unicorn|unicorn|upgrade|downgrade|magic|instant|neigh|super_neigh
    emoji: str
    color: str  # hex
    count: int
    effect: Dict


class _WebButton:
    def __init__(self, text: str, enabled: bool = True):
        self.text = text
        self.enabled = enabled


def _hex_to_rgb(hex_color: str, default: Tuple[int, int, int] = (160, 160, 160)) -> Tuple[int, int, int]:
    h = (hex_color or "").strip().lstrip("#")
    if len(h) != 6:
        return default
    try:
        r = int(h[0:2], 16)
        g = int(h[2:4], 16)
        b = int(h[4:6], 16)
        return (r, g, b)
    except Exception:
        return default


class UnstableUnicornsGame:
    """Unstable Unicorns (rules engine + Web UI + Pyglet board).

    Important: This ships with a GENERIC card set (no official card text/art).
    The rules interactions (turn structure + Neigh stack + basic effects) are implemented.
    You can add your own card sets by editing JSON files under games/unstable_unicorns/cards.
    """

    def __init__(self, width: int, height: int, renderer=None):
        self.width = width
        self.height = height
        self.renderer = renderer

        self.state = "player_select"  # player_select|playing|game_over
        self.selection_ui = PlayerSelectionUI(width, height)

        self.active_players: List[int] = []
        self.current_player_idx: int = 0

        # Card registry / piles
        self.cards: Dict[str, UUCardDef] = {}
        self.draw_pile: List[str] = []
        self.discard_pile: List[str] = []

        # Per-player zones
        self.hands: Dict[int, List[str]] = {}
        self.stables: Dict[int, List[str]] = {}
        self.protected_turns: Dict[int, int] = {}

        # Turn/phase
        self.turn_phase: str = "begin"  # begin|action|discard|reaction|prompt
        self.action_taken: bool = False

        # Reaction window (Neigh stack)
        self.reaction_active: bool = False
        self.reaction_actor: Optional[int] = None
        self.reaction_card_id: Optional[str] = None
        self.reaction_target: Optional[Dict] = None
        self.reaction_order: List[int] = []
        self.reaction_idx: int = 0
        self.reaction_stack: List[str] = []  # list of card ids played as reactions (neigh/super_neigh)

        # Prompting (target selection etc.)
        self.prompt: Optional[Dict] = None

        # Win
        self.winner: Optional[int] = None
        self.goal_unicorns: int = 7

        # Web UI buttons
        self.buttons: Dict[int, Dict[str, _WebButton]] = {}

        # Seat-name provider for rendering
        self._seat_name_provider: Optional[Callable[[int], str]] = None

        # --- Animation state ---
        self._particles: ParticleSystem = ParticleSystem()
        self._card_flips: List[CardFlyAnim] = []
        self._text_pops: List[TextPopAnim] = []
        self._pulse_rings: List[PulseRing] = []
        self._flashes: List[ScreenFlash] = []
        # Zone centres updated each draw() frame so animations know where players are
        self._zone_centers: Dict[int, Tuple[int, int]] = {}
        # State-change detection for reactive animations
        self._anim_prev_turn: Optional[int] = None
        self._anim_prev_reaction: bool = False
        self._anim_prev_winner: Optional[int] = None
        self._anim_fw_timer: float = 0.0

        self._load_card_sets(include_expansions=True)
        self._rebuild_buttons()

    def set_name_provider(self, provider: Optional[Callable[[int], str]]) -> None:
        self._seat_name_provider = provider

    def _seat_label(self, seat: Optional[int]) -> str:
        if not isinstance(seat, int):
            return "—"
        if self._seat_name_provider:
            try:
                return str(self._seat_name_provider(int(seat)))
            except Exception:
                pass
        return f"Player {int(seat) + 1}"

    # --- Card set loading ---

    def _cards_dir(self) -> Path:
        return (Path(__file__).parent / "cards").resolve()

    def _load_card_sets(self, include_expansions: bool) -> None:
        self.cards = {}
        base_dir = self._cards_dir()
        files: List[Path] = []
        try:
            if base_dir.exists() and base_dir.is_dir():
                for p in sorted(base_dir.glob("*.json")):
                    if not include_expansions and p.name != "base.json":
                        continue
                    files.append(p)
        except Exception:
            files = []

        for fp in files:
            try:
                data = json.loads(fp.read_text(encoding="utf-8"))
            except Exception:
                continue
            for raw in list(data.get("cards") or []):
                try:
                    cid = str(raw.get("id") or "").strip()
                    if not cid:
                        continue
                    if cid in self.cards:
                        continue
                    c = UUCardDef(
                        id=cid,
                        name=str(raw.get("name") or cid),
                        kind=str(raw.get("kind") or "").strip(),
                        emoji=str(raw.get("emoji") or ""),
                        color=str(raw.get("color") or "#a0a0a0"),
                        count=int(raw.get("count") or 0),
                        effect=dict(raw.get("effect") or {"type": "NONE"}),
                    )
                    self.cards[cid] = c
                except Exception:
                    continue

        # Safety: ensure baby exists.
        if "baby_unicorn" not in self.cards:
            self.cards["baby_unicorn"] = UUCardDef(
                id="baby_unicorn",
                name="Baby Unicorn",
                kind="baby_unicorn",
                emoji="🦄",
                color="#f3a6ff",
                count=0,
                effect={"type": "NONE"},
            )

    def _build_deck(self) -> List[str]:
        deck: List[str] = []
        for cid, c in self.cards.items():
            if cid == "baby_unicorn":
                continue
            n = max(0, int(c.count))
            deck.extend([cid] * n)
        random.shuffle(deck)
        return deck

    # --- Lifecycle ---

    def start_game(self, selected_indices: List[int]) -> None:
        seats = [int(i) for i in selected_indices if isinstance(i, int) or str(i).isdigit()]
        seats = [s for s in seats if 0 <= s <= 7]
        seats = sorted(dict.fromkeys(seats))
        if len(seats) < 2:
            return

        self.active_players = seats
        self.current_player_idx = 0
        self.draw_pile = self._build_deck()
        self.discard_pile = []
        self.hands = {s: [] for s in seats}
        self.stables = {s: ["baby_unicorn"] for s in seats}
        self.protected_turns = {s: 0 for s in seats}

        # Deal 5
        for _ in range(5):
            for s in seats:
                self._draw_to_hand(int(s), 1)

        self.state = "playing"
        self.winner = None
        self.turn_phase = "begin"
        self.action_taken = False
        self._begin_turn()
        self._rebuild_buttons()

    def handle_player_quit(self, seat: int) -> None:
        try:
            s = int(seat)
        except Exception:
            return
        if s not in self.active_players:
            return
        self.active_players = [p for p in self.active_players if int(p) != int(s)]
        self.hands.pop(s, None)
        self.stables.pop(s, None)
        self.protected_turns.pop(s, None)

        if len(self.active_players) < 2:
            self.state = "player_select"
            self.selection_ui.reset()
        else:
            if self.current_player_idx >= len(self.active_players):
                self.current_player_idx = 0
        self._rebuild_buttons()

    _SEAT_COLORS: List[Tuple[int,int,int]] = [
        (255, 80,  80),   # red
        (80,  180, 255),  # blue
        (80,  255, 130),  # green
        (255, 200, 50),   # gold
        (200, 80,  255),  # violet
        (255, 140, 50),   # orange
    ]

    def update(self, dt: float) -> None:
        # --- Tick all animation objects ---
        self._particles.update(dt)

        live_flips: List[CardFlyAnim] = []
        for a in self._card_flips:
            a.update(dt)
            if not a.done:
                live_flips.append(a)
        self._card_flips = live_flips

        live_pops: List[TextPopAnim] = []
        for a in self._text_pops:
            a.update(dt)
            if not a.done:
                live_pops.append(a)
        self._text_pops = live_pops

        live_rings: List[PulseRing] = []
        for a in self._pulse_rings:
            a.update(dt)
            if not a.done:
                live_rings.append(a)
        self._pulse_rings = live_rings

        live_flash: List[ScreenFlash] = []
        for a in self._flashes:
            a.update(dt)
            if not a.done:
                live_flash.append(a)
        self._flashes = live_flash

        # --- Detect turn change ---
        curr_turn = self.current_turn_seat
        if (
            self.state == "playing"
            and isinstance(curr_turn, int)
            and curr_turn != self._anim_prev_turn
            and isinstance(self._anim_prev_turn, int)   # skip game-start
        ):
            center = self._zone_centers.get(curr_turn, (self.width // 2, self.height // 2))
            col = self._SEAT_COLORS[curr_turn % len(self._SEAT_COLORS)]
            self._pulse_rings.append(
                PulseRing(center[0], center[1], col,
                          max_radius=min(self.width, self.height) // 5, duration=0.8)
            )
            # Sparkle at the newly active zone
            self._particles.emit_sparkle(center[0], center[1], col, count=18)
        self._anim_prev_turn = curr_turn

        # --- Detect reaction window opening ---
        if self.reaction_active and not self._anim_prev_reaction:
            cx, cy = self.width // 2, self.height // 2
            self._flashes.append(ScreenFlash((220, 30, 30), peak_alpha=90, duration=0.4))
            self._text_pops.append(
                TextPopAnim("NEIGH? 🚫", cx, cy + 55,
                            color=(255, 90, 80), font_size=44, duration=1.8)
            )
        self._anim_prev_reaction = bool(self.reaction_active)

        # --- Detect winner ---
        if self.winner is not None and self._anim_prev_winner is None:
            cx, cy = self.width // 2, self.height // 2
            name = self._seat_label(self.winner)
            self._text_pops.append(
                TextPopAnim(f"🦄 {name} WINS! 🦄", cx, cy,
                            color=(255, 220, 50), font_size=50, duration=5.0)
            )
            self._flashes.append(ScreenFlash((255, 255, 180), peak_alpha=140, duration=0.65))
            # Initial firework burst
            for fx, fy in [(0.25, 0.30), (0.50, 0.20), (0.75, 0.30),
                           (0.38, 0.55), (0.62, 0.55), (0.50, 0.70)]:
                self._particles.emit_firework(
                    int(self.width * fx), int(self.height * fy),
                    _UU_FW_COLORS, total=70
                )
            self._anim_fw_timer = 0.85
        self._anim_prev_winner = self.winner

        # --- Ongoing winner fireworks ---
        if self.winner is not None:
            self._anim_fw_timer -= dt
            if self._anim_fw_timer <= 0.0:
                fx = random.uniform(0.12, 0.88)
                fy = random.uniform(0.15, 0.70)
                self._particles.emit_firework(
                    int(self.width * fx), int(self.height * fy),
                    _UU_FW_COLORS, total=55
                )
                self._anim_fw_timer = random.uniform(0.70, 1.20)

    @property
    def current_turn_seat(self) -> Optional[int]:
        if not self.active_players:
            return None
        try:
            return int(self.active_players[int(self.current_player_idx) % len(self.active_players)])
        except Exception:
            return None

    # --- Core rules ---

    def _hand_limit(self, seat: int) -> int:
        base = 7
        mod = 0
        for cid in self.stables.get(seat, []):
            c = self.cards.get(cid)
            if not c:
                continue
            if c.effect.get("type") == "PASSIVE_HAND_LIMIT_MOD":
                try:
                    mod += int(c.effect.get("amount") or 0)
                except Exception:
                    pass
        return max(0, base + mod)

    def _draw_bonus(self, seat: int) -> int:
        bonus = 0
        for cid in self.stables.get(seat, []):
            c = self.cards.get(cid)
            if not c:
                continue
            if c.effect.get("type") == "PASSIVE_DRAW_BONUS":
                try:
                    bonus += int(c.effect.get("amount") or 0)
                except Exception:
                    pass
        return bonus

    def _begin_turn(self) -> None:
        if self.state != "playing":
            return
        seat = self.current_turn_seat
        if not isinstance(seat, int):
            return

        # Decrement protection counters.
        for s in list(self.protected_turns.keys()):
            self.protected_turns[s] = max(0, int(self.protected_turns.get(s, 0) or 0) - 1)

        self.turn_phase = "begin"
        self.action_taken = False

        draw_n = 1 + max(0, self._draw_bonus(seat))
        self._draw_to_hand(seat, draw_n)
        self.turn_phase = "discard" if len(self.hands.get(seat, [])) > self._hand_limit(seat) else "action"

    def _end_turn(self) -> None:
        if not self.active_players:
            return
        self.current_player_idx = (int(self.current_player_idx) + 1) % len(self.active_players)
        self.prompt = None
        self._clear_reaction()
        self._begin_turn()

    def _draw_to_hand(self, seat: int, n: int) -> None:
        self.hands.setdefault(seat, [])
        for _ in range(max(0, int(n))):
            if not self.draw_pile:
                self._refill_from_discard()
            if not self.draw_pile:
                return
            self.hands[seat].append(self.draw_pile.pop())

    def _refill_from_discard(self) -> None:
        if not self.discard_pile:
            return
        self.draw_pile.extend(self.discard_pile)
        self.discard_pile = []
        random.shuffle(self.draw_pile)

    def _unicorn_count(self, seat: int) -> int:
        count = 0
        for cid in self.stables.get(seat, []):
            kind = (self.cards.get(cid).kind if self.cards.get(cid) else "")
            if kind in ("baby_unicorn", "unicorn"):
                count += 1
        return count

    def _check_win(self) -> None:
        for s in self.active_players:
            if self._unicorn_count(int(s)) >= int(self.goal_unicorns):
                self.winner = int(s)
                self.state = "game_over"
                self.turn_phase = "action"
                self.prompt = None
                self._clear_reaction()
                return

    # --- Reaction (Neigh) ---

    def _is_neighable(self, card_id: str) -> bool:
        c = self.cards.get(card_id)
        if not c:
            return False
        # Neigh itself is only for reactions.
        if c.kind in ("neigh", "super_neigh"):
            return False
        return True

    def _open_reaction(self, actor: int, card_id: str, target: Optional[Dict]) -> None:
        self.reaction_active = True
        self.reaction_actor = int(actor)
        self.reaction_card_id = str(card_id)
        self.reaction_target = dict(target or {})
        self.reaction_stack = []
        self.reaction_order = [int(s) for s in self.active_players if int(s) != int(actor)]
        self.reaction_idx = 0
        self.turn_phase = "reaction"

    def _clear_reaction(self) -> None:
        self.reaction_active = False
        self.reaction_actor = None
        self.reaction_card_id = None
        self.reaction_target = None
        self.reaction_order = []
        self.reaction_idx = 0
        self.reaction_stack = []

    def _current_reaction_seat(self) -> Optional[int]:
        if not self.reaction_active:
            return None
        if self.reaction_idx < 0 or self.reaction_idx >= len(self.reaction_order):
            return None
        return int(self.reaction_order[self.reaction_idx])

    def _reaction_result_allows_resolve(self) -> bool:
        # If last reaction is SUPER_NEIGH => card is negated unconditionally.
        if self.reaction_stack:
            last = self.reaction_stack[-1]
            if self.cards.get(last) and self.cards[last].kind == "super_neigh":
                return False
        # Otherwise odd number of NEIGH cancels.
        neigh_count = 0
        for cid in self.reaction_stack:
            kind = self.cards.get(cid).kind if self.cards.get(cid) else ""
            if kind in ("neigh", "super_neigh"):
                neigh_count += 1
        return (neigh_count % 2) == 0

    # --- Click handling ---

    def handle_click(self, player_idx: int, btn_id: str) -> None:
        seat = int(player_idx) if isinstance(player_idx, int) else -1
        if self.state == "player_select":
            return

        if self.winner is not None:
            return

        if seat not in self.active_players:
            return

        # Reaction buttons
        if self.reaction_active:
            expected = self._current_reaction_seat()
            if seat != expected:
                return

            if btn_id in ("uu_react_pass", "uu_react_neigh", "uu_react_super"):
                if btn_id == "uu_react_neigh":
                    if not self._remove_one(seat, "neigh"):
                        return
                    self.discard_pile.append("neigh")
                    self.reaction_stack.append("neigh")
                elif btn_id == "uu_react_super":
                    if not self._remove_one(seat, "super_neigh"):
                        return
                    self.discard_pile.append("super_neigh")
                    self.reaction_stack.append("super_neigh")

                # Animate the neigh card flying to centre
                if btn_id in ("uu_react_neigh", "uu_react_super"):
                    cx, cy = self.width // 2, self.height // 2
                    src = self._zone_centers.get(seat, (cx, cy))
                    self._card_flips.append(CardFlyAnim(src, (cx, cy), color=(220, 30, 30)))
                    self._flashes.append(ScreenFlash((220, 30, 30), peak_alpha=110, duration=0.38))
                    self._text_pops.append(
                        TextPopAnim("NEIGH! 🚫", cx, cy - 20,
                                    color=(255, 80, 60), font_size=52, duration=1.6)
                    )

                self.reaction_idx += 1
                if self.reaction_idx >= len(self.reaction_order):
                    self._resolve_reaction()
                self._rebuild_buttons()
            return

        # Prompt targeting
        if self.prompt:
            actor = int(self.prompt.get("actor", -1))
            if seat != actor:
                return

            if btn_id.startswith("uu_target_player:"):
                try:
                    t = int(btn_id.split(":", 1)[1])
                except Exception:
                    return
                self.prompt["target_player"] = int(t)
                self._advance_prompt()
                self._rebuild_buttons()
            elif btn_id.startswith("uu_target_card:"):
                try:
                    rest = btn_id.split(":", 1)[1]
                    p_str, i_str = rest.split(":", 1)
                    t = int(p_str)
                    idx = int(i_str)
                except Exception:
                    return
                self.prompt["target_player"] = int(t)
                self.prompt["target_index"] = int(idx)
                self._advance_prompt()
                self._rebuild_buttons()
            return

        # Normal turn actions
        is_turn = bool(seat == self.current_turn_seat)

        if btn_id == "uu_draw_action":
            if not is_turn or self.turn_phase != "action" or self.action_taken:
                return
            self._draw_to_hand(seat, 1)
            self.action_taken = True
            self.turn_phase = "discard" if len(self.hands.get(seat, [])) > self._hand_limit(seat) else "action"
            # Sparkle at player zone centre
            ctr = self._zone_centers.get(seat, (self.width // 2, self.height // 2))
            col = self._SEAT_COLORS[seat % len(self._SEAT_COLORS)]
            self._particles.emit_sparkle(ctr[0], ctr[1], col, count=14)
            self._rebuild_buttons()
            return

        if btn_id == "uu_end_turn":
            if not is_turn:
                return
            if self.turn_phase == "discard":
                return
            if not self.action_taken:
                return
            self._end_turn()
            self._rebuild_buttons()
            return

        if btn_id.startswith("uu_discard:"):
            if not is_turn or self.turn_phase != "discard":
                return
            try:
                idx = int(btn_id.split(":", 1)[1])
            except Exception:
                return
            self._discard_from_hand(seat, idx)
            if len(self.hands.get(seat, [])) <= self._hand_limit(seat):
                self.turn_phase = "action"
            self._rebuild_buttons()
            return

        if btn_id.startswith("uu_play:"):
            try:
                idx = int(btn_id.split(":", 1)[1])
            except Exception:
                return
            self._play_from_hand(seat, idx)
            # Animate the card flying to the play area (centre top-third)
            src = self._zone_centers.get(seat, (self.width // 2, self.height // 2))
            dst = (self.width // 2, self.height // 3)
            col = self._SEAT_COLORS[seat % len(self._SEAT_COLORS)]
            self._card_flips.append(CardFlyAnim(src, dst, color=col))
            self._particles.emit_sparkle(dst[0], dst[1], col, count=20)
            self._rebuild_buttons()
            return

    def _remove_one(self, seat: int, kind: str) -> bool:
        # Remove a neigh/super_neigh by kind (first match).
        hand = self.hands.get(seat, [])
        for i, cid in enumerate(list(hand)):
            c = self.cards.get(cid)
            if c and c.kind == kind:
                hand.pop(i)
                return True
        return False

    def _discard_from_hand(self, seat: int, idx: int) -> None:
        hand = self.hands.get(seat, [])
        if idx < 0 or idx >= len(hand):
            return
        cid = hand.pop(idx)
        self.discard_pile.append(cid)

    def _play_from_hand(self, seat: int, idx: int) -> None:
        if self.state != "playing":
            return
        hand = self.hands.get(seat, [])
        if idx < 0 or idx >= len(hand):
            return
        cid = hand[idx]
        c = self.cards.get(cid)
        if not c:
            return

        # Instants can be played any time (outside reaction window).
        if c.kind == "instant":
            hand.pop(idx)
            self._resolve_effect(seat, cid)
            self.discard_pile.append(cid)
            self._check_win()
            return

        # Neigh cards are only meaningful during reaction, handled elsewhere.
        if c.kind in ("neigh", "super_neigh"):
            return

        # Non-instant: only on your turn, once per turn.
        if seat != self.current_turn_seat:
            return
        if self.turn_phase != "action":
            return
        if self.action_taken:
            return

        # Remove from hand now.
        hand.pop(idx)

        # Some effects require target selection.
        effect_type = str(c.effect.get("type") or "NONE")
        if effect_type in ("STEAL_UNICORN", "DESTROY_STABLE_CARD", "SWAP_UNICORN"):
            self.prompt = {
                "kind": effect_type,
                "actor": int(seat),
                "card_id": str(cid),
                "step": "pick_player",
            }
            self.turn_phase = "prompt"
            return

        # Neigh window for neighable cards.
        if self._is_neighable(cid):
            self._open_reaction(actor=seat, card_id=cid, target=None)
            # Store the played card in prompt-like storage for later resolution.
            self.prompt = {"kind": "PLAY", "actor": int(seat), "card_id": str(cid)}
            return

        # Otherwise resolve immediately.
        self._resolve_effect(seat, cid)
        self.action_taken = True
        self.discard_pile.append(cid)
        self._check_win()

    def _advance_prompt(self) -> None:
        if not self.prompt:
            return
        kind = str(self.prompt.get("kind") or "")
        actor = int(self.prompt.get("actor", -1))
        card_id = str(self.prompt.get("card_id") or "")

        if kind == "PLAY":
            # Should not happen here.
            return

        if kind in ("STEAL_UNICORN", "DESTROY_STABLE_CARD", "SWAP_UNICORN"):
            step = str(self.prompt.get("step") or "")
            if step == "pick_player":
                t = self.prompt.get("target_player")
                if not isinstance(t, int) or t not in self.active_players or t == actor:
                    return
                # Next step: pick card from target stable.
                self.prompt["step"] = "pick_card"
                return

            if step == "pick_card":
                t = int(self.prompt.get("target_player", -1))
                idx = int(self.prompt.get("target_index", -1))
                target_stable = list(self.stables.get(t, []))
                # Only unicorns are eligible for steal/swap; destroy allows any stable card.
                if kind in ("STEAL_UNICORN", "SWAP_UNICORN"):
                    eligible = [i for i, cid in enumerate(target_stable) if (self.cards.get(cid).kind if self.cards.get(cid) else "") in ("baby_unicorn", "unicorn")]
                    if idx not in eligible:
                        return
                else:
                    if idx < 0 or idx >= len(target_stable):
                        return

                # Neigh window for the magic card.
                self._open_reaction(actor=actor, card_id=card_id, target={"target_player": t, "target_index": idx, "kind": kind})
                self.prompt = {"kind": "PLAY", "actor": int(actor), "card_id": str(card_id), "target": {"target_player": t, "target_index": idx, "kind": kind}}
                self.turn_phase = "reaction"
                return

    def _resolve_reaction(self) -> None:
        # Determine whether the played card resolves or is negated.
        if not self.prompt or str(self.prompt.get("kind")) != "PLAY":
            self._clear_reaction()
            self.turn_phase = "action"
            return

        actor = int(self.prompt.get("actor", -1))
        card_id = str(self.prompt.get("card_id") or "")
        target = dict(self.prompt.get("target") or {})

        resolves = self._reaction_result_allows_resolve()
        self._clear_reaction()

        if resolves:
            # Resolve effect
            self._resolve_effect(actor, card_id, target=target)
        # Discard the played card either way.
        self.discard_pile.append(card_id)
        self.prompt = None

        self.action_taken = True
        self.turn_phase = "discard" if len(self.hands.get(actor, [])) > self._hand_limit(actor) else "action"
        self._check_win()

    def _resolve_effect(self, actor: int, card_id: str, target: Optional[Dict] = None) -> None:
        c = self.cards.get(card_id)
        if not c:
            return
        eff = dict(c.effect or {})
        typ = str(eff.get("type") or "NONE")

        if typ == "NONE":
            return

        if typ == "STABLE_ADD_SELF":
            self.stables.setdefault(actor, []).append(card_id)
            return

        if typ == "DRAW":
            try:
                n = int(eff.get("amount") or 0)
            except Exception:
                n = 0
            self._draw_to_hand(actor, max(0, n))
            return

        if typ == "PROTECT_SELF":
            try:
                turns = int(eff.get("turns") or 1)
            except Exception:
                turns = 1
            self.protected_turns[actor] = max(int(self.protected_turns.get(actor, 0) or 0), max(0, turns))
            return

        if typ == "STEAL_UNICORN":
            t = int((target or {}).get("target_player", -1))
            idx = int((target or {}).get("target_index", -1))
            if t not in self.active_players:
                return
            if int(self.protected_turns.get(t, 0) or 0) > 0:
                return
            src = self.stables.get(t, [])
            if idx < 0 or idx >= len(src):
                return
            moved = src.pop(idx)
            self.stables.setdefault(actor, []).append(moved)
            return

        if typ == "DESTROY_STABLE_CARD":
            t = int((target or {}).get("target_player", -1))
            idx = int((target or {}).get("target_index", -1))
            if t not in self.active_players:
                return
            if int(self.protected_turns.get(t, 0) or 0) > 0:
                return
            src = self.stables.get(t, [])
            if idx < 0 or idx >= len(src):
                return
            moved = src.pop(idx)
            self.discard_pile.append(moved)
            return

        if typ == "SWAP_UNICORN":
            t = int((target or {}).get("target_player", -1))
            idx = int((target or {}).get("target_index", -1))
            if t not in self.active_players:
                return
            if int(self.protected_turns.get(t, 0) or 0) > 0:
                return

            their = self.stables.get(t, [])
            if idx < 0 or idx >= len(their):
                return

            # Pick one of your unicorns to swap: MVP chooses a random unicorn from your stable.
            mine = self.stables.get(actor, [])
            my_unicorn_idxs = [i for i, cid in enumerate(mine) if (self.cards.get(cid).kind if self.cards.get(cid) else "") in ("baby_unicorn", "unicorn")]
            if not my_unicorn_idxs:
                return
            my_i = random.choice(my_unicorn_idxs)

            mine[my_i], their[idx] = their[idx], mine[my_i]
            return

        if typ == "SACRIFICE_ONE_DRAW":
            # Sacrifice a unicorn from your stable (random) then draw N.
            mine = self.stables.get(actor, [])
            unicorn_idxs = [i for i, cid in enumerate(mine) if (self.cards.get(cid).kind if self.cards.get(cid) else "") in ("baby_unicorn", "unicorn")]
            if unicorn_idxs:
                i = random.choice(unicorn_idxs)
                self.discard_pile.append(mine.pop(i))
            try:
                n = int(eff.get("amount") or 0)
            except Exception:
                n = 0
            self._draw_to_hand(actor, max(0, n))
            return

    # --- Snapshot ---

    def get_public_state(self, player_idx: int) -> Dict:
        seat = int(player_idx) if isinstance(player_idx, int) else -1

        def card_summary(cid: str) -> Dict:
            c = self.cards.get(cid)
            if not c:
                return {"id": cid, "name": cid, "kind": "", "emoji": "", "color": "#a0a0a0"}
            return {"id": c.id, "name": c.name, "kind": c.kind, "emoji": c.emoji, "color": c.color}

        my_hand = list(self.hands.get(seat, []))
        is_turn = bool(seat == self.current_turn_seat and self.state == "playing")

        # Determine playability.
        def playable(cid: str) -> bool:
            c = self.cards.get(cid)
            if not c:
                return False
            if self.winner is not None:
                return False
            if self.reaction_active:
                # Only neigh/super_neigh by the reacting seat.
                if seat != self._current_reaction_seat():
                    return False
                return c.kind in ("neigh", "super_neigh")
            if self.prompt:
                return False
            if c.kind == "instant":
                return True
            if c.kind in ("neigh", "super_neigh"):
                return False
            if not is_turn or self.turn_phase != "action" or self.action_taken:
                return False
            return True

        stables = {str(int(s)): [card_summary(cid) for cid in (self.stables.get(int(s), []) or [])] for s in self.active_players}

        reaction = None
        if self.reaction_active:
            reaction = {
                "actor": self.reaction_actor,
                "card": card_summary(self.reaction_card_id or ""),
                "awaiting_seat": self._current_reaction_seat(),
                "stack": [card_summary(cid) for cid in self.reaction_stack],
            }

        prompt = None
        if self.prompt and str(self.prompt.get("kind")) != "PLAY":
            prompt = dict(self.prompt)

        return {
            "state": str(self.state),
            "active_players": list(self.active_players),
            "current_turn_seat": self.current_turn_seat,
            "turn_phase": str(self.turn_phase),
            "action_taken": bool(self.action_taken),
            "deck_count": int(len(self.draw_pile)),
            "discard_count": int(len(self.discard_pile)),
            "goal_unicorns": int(self.goal_unicorns),
            "winner": self.winner,
            "your_hand": [{"idx": int(i), **card_summary(cid), "playable": bool(playable(cid))} for i, cid in enumerate(my_hand)],
            "stables": stables,
            "protected_turns": {str(int(s)): int(self.protected_turns.get(int(s), 0) or 0) for s in self.active_players},
            "hand_counts": {str(int(s)): int(len(self.hands.get(int(s), []) or [])) for s in self.active_players},
            "reaction": reaction,
            "prompt": prompt,
        }

    # --- Buttons ---

    def _rebuild_buttons(self) -> None:
        self.buttons = {int(s): {} for s in self.active_players}

        if self.winner is not None:
            return

        # Reaction-only buttons
        if self.reaction_active:
            reacting = self._current_reaction_seat()
            if isinstance(reacting, int) and reacting in self.active_players:
                can_neigh = any((self.cards.get(cid).kind if self.cards.get(cid) else "") == "neigh" for cid in self.hands.get(reacting, []))
                can_super = any((self.cards.get(cid).kind if self.cards.get(cid) else "") == "super_neigh" for cid in self.hands.get(reacting, []))
                self.buttons[reacting]["uu_react_neigh"] = _WebButton("Neigh", enabled=bool(can_neigh))
                self.buttons[reacting]["uu_react_super"] = _WebButton("Super Neigh", enabled=bool(can_super))
                self.buttons[reacting]["uu_react_pass"] = _WebButton("Pass", enabled=True)
            return

        # Prompt targeting buttons
        if self.prompt and str(self.prompt.get("kind")) != "PLAY":
            actor = int(self.prompt.get("actor", -1))
            if actor in self.active_players:
                kind = str(self.prompt.get("kind") or "")
                step = str(self.prompt.get("step") or "")
                if step == "pick_player":
                    for t in self.active_players:
                        if int(t) == int(actor):
                            continue
                        self.buttons[actor][f"uu_target_player:{int(t)}"] = _WebButton(f"Target: {self._seat_label(int(t))}", True)
                elif step == "pick_card":
                    t = int(self.prompt.get("target_player", -1))
                    stable = list(self.stables.get(t, []) or [])
                    if kind in ("STEAL_UNICORN", "SWAP_UNICORN"):
                        eligible = [i for i, cid in enumerate(stable) if (self.cards.get(cid).kind if self.cards.get(cid) else "") in ("baby_unicorn", "unicorn")]
                    else:
                        eligible = list(range(len(stable)))

                    for i in eligible:
                        c = self.cards.get(stable[i])
                        label = c.name if c else stable[i]
                        self.buttons[actor][f"uu_target_card:{int(t)}:{int(i)}"] = _WebButton(f"Pick: {label}", True)
            return

        # Normal turn buttons
        turn = self.current_turn_seat
        if not isinstance(turn, int) or turn not in self.active_players:
            return

        # Discard phase
        if self.turn_phase == "discard":
            hand = self.hands.get(turn, [])
            for i, cid in enumerate(hand):
                c = self.cards.get(cid)
                label = c.name if c else cid
                self.buttons[turn][f"uu_discard:{int(i)}"] = _WebButton(f"Discard: {label}", True)
            return

        self.buttons[turn]["uu_draw_action"] = _WebButton("Draw (action)", enabled=bool(self.turn_phase == "action" and not self.action_taken))
        self.buttons[turn]["uu_end_turn"] = _WebButton("End Turn", enabled=bool(self.turn_phase == "action" and self.action_taken))

        # Hand play buttons (optional; Web UI mostly clicks cards)
        hand = list(self.hands.get(turn, []))
        for i, cid in enumerate(hand):
            c = self.cards.get(cid)
            if not c:
                continue
            if c.kind in ("neigh", "super_neigh"):
                continue
            if c.kind != "instant" and self.action_taken:
                continue
            self.buttons[turn][f"uu_play:{int(i)}"] = _WebButton(f"Play: {c.name}", enabled=True)

    # --- Rendering (Pyglet board) ---

    def _draw_background(self, w: int, h: int) -> None:
        """Draw the magical Unstable Unicorns background."""
        draw_game_background(self.renderer, w, h, "unstable_unicorns")

    def _card_rect(self, x: float, y: float, w: float, h: float) -> Tuple[int, int, int, int]:
        return (int(x), int(y), int(w), int(h))

    def _draw_card_face(self, rect: Tuple[int, int, int, int], cid: str) -> None:
        c = self.cards.get(cid)
        if not c or not self.renderer:
            return
        rgb = _hex_to_rgb(c.color, default=(140, 140, 140))
        draw_emoji_card(
            self.renderer,
            rect,
            emoji=str(c.emoji or ""),
            title="",
            accent_rgb=rgb,
            corner=str(c.kind or "").upper()[:4],
            max_title_font_size=11,
        )

    def draw(self) -> None:
        if not self.renderer:
            return
        try:
            w, h = int(getattr(self.renderer, "width", self.width)), int(getattr(self.renderer, "height", self.height))
        except Exception:
            w, h = self.width, self.height

        self._draw_background(w, h)

        # --- Rainbow centered title ---
        title = "UNSTABLE UNICORNS"
        if isinstance(self.winner, int):
            title = f"WINNER: {self._seat_label(self.winner)}"
        draw_rainbow_title(self.renderer, title, w)

        # Layout: grid of player stables
        seats = list(self.active_players)
        if not seats:
            return

        cols = 2 if len(seats) > 2 else 1
        rows = (len(seats) + cols - 1) // cols
        pad = 18
        top = 48  # title line height
        zone_w = int((w - pad * (cols + 1)) / cols)
        zone_h = int((h - top - pad * (rows + 1)) / max(1, rows))

        gap = 10
        cards_per_row = 5
        # Size cards to fill the zone nicely — minimum 92 px wide
        card_w = max(92, min(130, (zone_w - 10 - gap * (cards_per_row - 1)) // cards_per_row))
        card_h = int(card_w * 1.35)

        for idx, s in enumerate(seats):
            r = idx // cols
            c = idx % cols
            zx = pad + c * (zone_w + pad)
            zy = h - top - pad - (r + 1) * zone_h - r * pad

            try:
                self.renderer.draw_rect((255, 255, 255), (zx, zy, zone_w, zone_h), alpha=10)
                self.renderer.draw_rect((255, 255, 255), (zx, zy, zone_w, zone_h), width=2, alpha=40)
            except Exception:
                pass

            # Store zone centre for animation system
            self._zone_centers[int(s)] = (zx + zone_w // 2, zy + zone_h // 2)

            stable = list(self.stables.get(int(s), []) or [])
            cx = zx + 10
            cy = zy + 10
            for ci, cid in enumerate(stable[:cards_per_row * 2]):
                x = cx + (ci % cards_per_row) * (card_w + gap)
                y = cy + (ci // cards_per_row) * (card_h + gap)
                if x + card_w > zx + zone_w - 6 or y + card_h > zy + zone_h - 6:
                    break
                self._draw_card_face(self._card_rect(x, y, card_w, card_h), cid)

        # ── Animation layers (drawn on top of cards, below reaction overlay) ──
        try:
            self._particles.draw(self.renderer)
        except Exception:
            pass
        try:
            for ring in self._pulse_rings:
                ring.draw(self.renderer)
        except Exception:
            pass
        try:
            for fly in self._card_flips:
                fly.draw(self.renderer)
        except Exception:
            pass
        try:
            for flash in self._flashes:
                flash.draw(self.renderer, w, h)
        except Exception:
            pass
        try:
            for pop in self._text_pops:
                pop.draw(self.renderer)
        except Exception:
            pass

        if self.reaction_active:
            try:
                self.renderer.draw_rect((0, 0, 0), (0, 0, w, h), alpha=120)
                awaiting = self._current_reaction_seat()
                txt = f"Reaction: {self._seat_label(awaiting)}"
                self.renderer.draw_text(txt, w // 2, h // 2, font_size=34, color=(245, 245, 245), anchor_x="center", anchor_y="center")
            except Exception:
                pass
