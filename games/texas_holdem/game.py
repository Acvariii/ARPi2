from __future__ import annotations

import itertools
import random
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

from core.player_selection import PlayerSelectionUI
from config import PLAYER_COLORS


@dataclass(frozen=True)
class HoldemCard:
    rank: int  # 2..14 (14 = Ace)
    suit: str  # 'S','H','D','C'

    def short(self) -> str:
        r = self.rank
        rs = {14: "A", 13: "K", 12: "Q", 11: "J", 10: "T"}.get(r, str(r))
        return f"{rs}{self.suit}"


class _WebButton:
    def __init__(self, text: str, enabled: bool = True):
        self.text = text
        self.enabled = enabled


def _rank_counts(ranks: List[int]) -> Dict[int, int]:
    out: Dict[int, int] = {}
    for r in ranks:
        out[r] = out.get(r, 0) + 1
    return out


def _is_straight(ranks: List[int]) -> Optional[int]:
    """Return high card of straight, or None. Input ranks are ints."""
    uniq = sorted(set(ranks), reverse=True)
    if len(uniq) < 5:
        return None

    # Wheel straight: A-5
    if 14 in uniq:
        uniq.append(1)

    # Scan windows of 5 in sorted descending unique list
    for i in range(0, len(uniq) - 4):
        window = uniq[i : i + 5]
        if window[0] - window[4] == 4 and len(set(window)) == 5:
            return window[0]
    return None


def _hand_rank_5(cards: List[HoldemCard]) -> Tuple[int, Tuple[int, ...]]:
    """Return (category, tiebreak) where higher is better.

    Categories:
      8 straight flush
      7 four of a kind
      6 full house
      5 flush
      4 straight
      3 three of a kind
      2 two pair
      1 one pair
      0 high card
    """
    ranks = sorted([c.rank for c in cards], reverse=True)
    suits = [c.suit for c in cards]
    is_flush = len(set(suits)) == 1
    straight_high = _is_straight(ranks)

    counts = _rank_counts(ranks)
    # Sort by (count, rank) to find groups
    groups = sorted(((cnt, r) for r, cnt in counts.items()), reverse=True)
    # groups is sorted like [(4, rank), (1, kicker)] etc

    if is_flush and straight_high is not None:
        return (8, (straight_high,))

    if groups[0][0] == 4:
        four_rank = groups[0][1]
        kicker = max(r for r in ranks if r != four_rank)
        return (7, (four_rank, kicker))

    if groups[0][0] == 3 and groups[1][0] == 2:
        trips = groups[0][1]
        pair = groups[1][1]
        return (6, (trips, pair))

    if is_flush:
        return (5, tuple(sorted(ranks, reverse=True)))

    if straight_high is not None:
        return (4, (straight_high,))

    if groups[0][0] == 3:
        trips = groups[0][1]
        kickers = sorted((r for r in ranks if r != trips), reverse=True)
        return (3, (trips, *kickers))

    if groups[0][0] == 2 and groups[1][0] == 2:
        pair_hi = max(groups[0][1], groups[1][1])
        pair_lo = min(groups[0][1], groups[1][1])
        kicker = max(r for r in ranks if r != pair_hi and r != pair_lo)
        return (2, (pair_hi, pair_lo, kicker))

    if groups[0][0] == 2:
        pair = groups[0][1]
        kickers = sorted((r for r in ranks if r != pair), reverse=True)
        return (1, (pair, *kickers))

    return (0, tuple(sorted(ranks, reverse=True)))


def _best_rank_7(cards: List[HoldemCard]) -> Tuple[int, Tuple[int, ...]]:
    best: Optional[Tuple[int, Tuple[int, ...]]] = None
    for combo in itertools.combinations(cards, 5):
        r = _hand_rank_5(list(combo))
        if best is None or r > best:
            best = r
    return best or (0, ())


def _describe_rank(rank: Tuple[int, Tuple[int, ...]]) -> str:
    cat, tb = rank
    if cat == 8:
        return "Straight Flush"
    if cat == 7:
        return "Four of a Kind"
    if cat == 6:
        return "Full House"
    if cat == 5:
        return "Flush"
    if cat == 4:
        return "Straight"
    if cat == 3:
        return "Three of a Kind"
    if cat == 2:
        return "Two Pair"
    if cat == 1:
        return "One Pair"
    return "High Card"


class TexasHoldemGame:
    """Texas Hold'em (web-UI-first) game.

    This is an MVP playable hold'em loop:
    - 2+ players
    - Blinds (SB/BB)
    - Betting rounds (fixed raise size)
    - Flop/Turn/River
    - Showdown hand evaluation

    The Web UI uses `buttons` and `get_public_state()`.
    The Pyglet window renders a clean wall-friendly board.
    """

    def __init__(self, width: int, height: int, renderer=None):
        self.width = width
        self.height = height
        self.renderer = renderer

        self.state = "player_select"  # player_select | playing | showdown
        self.selection_ui = PlayerSelectionUI(width, height)

        self.active_players: List[int] = []
        self.stacks: Dict[int, int] = {}

        # Hand state
        self.hand_id: int = 0
        self.dealer_seat: Optional[int] = None
        self.small_blind: int = 5
        self.big_blind: int = 10
        self.pot: int = 0

        self.deck: List[HoldemCard] = []
        self.community: List[HoldemCard] = []
        self.hole: Dict[int, List[HoldemCard]] = {}
        self.in_hand: Dict[int, bool] = {}

        # Betting
        self.street: str = "preflop"  # preflop|flop|turn|river
        self.current_bet: int = 0
        self.bet_in_round: Dict[int, int] = {}
        self.acted: set[int] = set()
        self.turn_seat: Optional[int] = None

        # Showdown
        self.last_showdown: Optional[Dict] = None

        # Per-seat reveal toggle (show your hole cards to everyone at showdown)
        self.reveal_hole: Dict[int, bool] = {}

        # Web UI buttons
        self.buttons: Dict[int, Dict[str, _WebButton]] = {}

        # Next-hand gating (require all in-hand players to confirm before dealing a new hand)
        self.next_hand_ready: Dict[int, bool] = {}
        self.next_hand_ready_hand_id: int = 0

        # Optional name provider for board rendering
        self._seat_name_provider: Optional[Callable[[int], str]] = None

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

    # --- Lifecycle ---

    def start_game(self, selected_indices: List[int]) -> None:
        seats = [int(i) for i in selected_indices if isinstance(i, int) or str(i).isdigit()]
        seats = [s for s in seats if 0 <= s <= 7]
        seats = sorted(dict.fromkeys(seats))
        if len(seats) < 2:
            return

        self.active_players = seats
        self.stacks = {s: 1000 for s in seats}
        self.state = "playing"
        self.dealer_seat = None
        self.last_showdown = None
        self._start_new_hand()

    def handle_player_quit(self, seat: int) -> None:
        """Handle a player disconnecting mid-game.

        - If they are in the current hand, treat as a fold.
        - Remove them from active_players so turn progression can't target them.
        - Redistribute their remaining stack evenly among remaining players.
        """
        try:
            s = int(seat)
        except Exception:
            return

        if self.state == "player_select":
            return

        if s not in self.active_players:
            return

        # If they are in-hand, fold them first while they're still in active_players.
        try:
            if self.state == "playing" and bool(self.in_hand.get(s, False)):
                self.in_hand[s] = False
                self.acted.add(s)
                self._after_action(s)
        except Exception:
            pass

        # Remove from active list.
        remaining = [int(x) for x in self.active_players if int(x) != s]
        self.active_players = remaining

        # Remove their per-hand state.
        try:
            self.hole.pop(s, None)
            self.in_hand.pop(s, None)
            self.bet_in_round.pop(s, None)
            self.reveal_hole.pop(s, None)
        except Exception:
            pass
        try:
            self.acted.discard(s)
        except Exception:
            pass

        # Redistribute chips/resources.
        stack = int(self.stacks.pop(s, 0) or 0)
        if remaining and stack > 0:
            share = int(stack) // int(len(remaining))
            if share > 0:
                for r in remaining:
                    self.stacks[int(r)] = int(self.stacks.get(int(r), 0) or 0) + share

        # Keep dealer/turn seats valid.
        if self.dealer_seat == s:
            self.dealer_seat = int(remaining[0]) if remaining else None

        if self.turn_seat == s:
            in_players = [p for p in (self.hole or {}).keys() if bool(self.in_hand.get(p, False))]
            if in_players:
                nxt = self._next_seat(s, predicate=lambda x: bool(self.in_hand.get(x, False)))
                self.turn_seat = int(nxt) if isinstance(nxt, int) else int(in_players[0])
            else:
                self.turn_seat = None

        # If not enough players remain to continue, let the normal loop mark showdown.
        try:
            seats_with_chips = [p for p in self.active_players if int(self.stacks.get(int(p), 0) or 0) > 0]
            if self.state == "playing" and len(seats_with_chips) < 2:
                self._start_new_hand()
                return
        except Exception:
            pass

        self._rebuild_buttons()

    def update(self, dt: float) -> None:
        # No animations yet; keep for interface parity.
        return

    # --- Dealing / rounds ---

    def _build_deck(self) -> List[HoldemCard]:
        suits = ["S", "H", "D", "C"]
        ranks = list(range(2, 15))
        return [HoldemCard(r, s) for s in suits for r in ranks]

    def _next_seat(self, start: int, predicate=None) -> Optional[int]:
        if not self.active_players:
            return None
        n = len(self.active_players)
        try:
            start_i = self.active_players.index(int(start))
        except Exception:
            start_i = 0
        for step in range(1, n + 1):
            seat = int(self.active_players[(start_i + step) % n])
            if predicate is None or predicate(seat):
                return seat
        return None

    def _start_new_hand(self) -> None:
        # Filter out busted players (keep them seated but not active in hand)
        seats = [s for s in self.active_players if int(self.stacks.get(int(s), 0) or 0) > 0]
        if len(seats) < 2:
            # Game effectively over.
            self.state = "showdown"
            self.last_showdown = {
                "winners": seats,
                "reason": "Not enough players with chips",
            }
            self._rebuild_buttons()
            return

        self.hand_id += 1
        self._reset_next_hand_ready()
        self.pot = 0
        self.community = []
        self.hole = {s: [] for s in seats}
        self.in_hand = {s: True for s in seats}
        self.bet_in_round = {s: 0 for s in seats}
        self.acted = set()
        self.last_showdown = None
        self.reveal_hole = {int(s): False for s in seats}

        # Rotate dealer
        if self.dealer_seat is None:
            self.dealer_seat = int(seats[0])
        else:
            nxt = self._next_seat(self.dealer_seat, predicate=lambda s: s in seats)
            self.dealer_seat = int(nxt) if isinstance(nxt, int) else int(seats[0])

        # Shuffle and deal
        self.deck = self._build_deck()
        random.shuffle(self.deck)
        for _ in range(2):
            for s in seats:
                self.hole[s].append(self.deck.pop())

        # Post blinds
        sb_seat = self._next_seat(self.dealer_seat, predicate=lambda s: s in seats)
        bb_seat = self._next_seat(int(sb_seat) if isinstance(sb_seat, int) else self.dealer_seat, predicate=lambda s: s in seats)

        self.street = "preflop"
        self.current_bet = 0

        self._post_blind(int(sb_seat), self.small_blind)
        self._post_blind(int(bb_seat), self.big_blind)

        self.current_bet = int(self.big_blind)

        # Action starts left of big blind
        first = self._next_seat(
            int(bb_seat),
            predicate=lambda s: s in seats and self.in_hand.get(s, False) and int(self.stacks.get(s, 0) or 0) > 0,
        )
        self.turn_seat = int(first) if isinstance(first, int) else None

        # If nobody has chips to act (everyone all-in), auto-run out the board.
        if self.turn_seat is None:
            self._advance_street()
            return

        self._rebuild_buttons()

    def _reset_next_hand_ready(self) -> None:
        """Reset per-hand next-hand readiness flags."""
        try:
            self.next_hand_ready_hand_id = int(self.hand_id)
        except Exception:
            self.next_hand_ready_hand_id = 0
        self.next_hand_ready = {}

    def _post_blind(self, seat: int, amount: int) -> None:
        if seat not in self.bet_in_round:
            return
        stack = int(self.stacks.get(seat, 0) or 0)
        pay = min(int(amount), stack)
        self.stacks[seat] = stack - pay
        self.bet_in_round[seat] = int(self.bet_in_round.get(seat, 0) or 0) + pay
        self.pot += pay

    def _burn(self) -> None:
        if self.deck:
            self.deck.pop()

    def _deal_flop(self) -> None:
        self._burn()
        for _ in range(3):
            if self.deck:
                self.community.append(self.deck.pop())

    def _deal_turn(self) -> None:
        self._burn()
        if self.deck:
            self.community.append(self.deck.pop())

    def _advance_street(self) -> None:
        # Reset betting
        for s in list(self.bet_in_round.keys()):
            self.bet_in_round[s] = 0
        self.current_bet = 0
        self.acted = set()

        if self.street == "preflop":
            self.street = "flop"
            self._deal_flop()
        elif self.street == "flop":
            self.street = "turn"
            self._deal_turn()
        elif self.street == "turn":
            self.street = "river"
            self._deal_turn()
        else:
            # river -> showdown
            self._resolve_showdown()
            return

        # Next action starts left of dealer
        seats = [s for s in self.hole.keys() if self.in_hand.get(s, False)]
        first = self._next_seat(
            int(self.dealer_seat),
            predicate=lambda s: s in seats and self.in_hand.get(s, False) and int(self.stacks.get(s, 0) or 0) > 0,
        )
        self.turn_seat = int(first) if isinstance(first, int) else None

        # If nobody can act (all remaining players are all-in), auto-run out to showdown.
        if self.turn_seat is None and self.state == "playing":
            # Max recursion depth is tiny here (preflop->flop->turn->river->showdown)
            self._advance_street()
            return

        self._rebuild_buttons()

    # --- Actions ---

    def handle_click(self, player_idx: int, btn_id: str) -> None:
        seat = int(player_idx) if isinstance(player_idx, int) else -1
        if self.state == "player_select":
            return

        if btn_id == "toggle_reveal":
            if self.state == "showdown" and seat in self.active_players:
                self.reveal_hole[int(seat)] = not bool(self.reveal_hole.get(int(seat), False))
                self._rebuild_buttons()
            return

        if btn_id == "next_hand":
            if self.state in ("showdown", "playing") and self._is_hand_over():
                # Mark this seat as ready; only start when all seated players are ready.
                if int(self.next_hand_ready_hand_id) != int(self.hand_id):
                    self._reset_next_hand_ready()

                required = [int(s) for s in (self.active_players or [])]

                self.next_hand_ready[int(seat)] = True

                if all(bool(self.next_hand_ready.get(int(s), False)) for s in required):
                    self.state = "playing"
                    self._start_new_hand()
                else:
                    self._rebuild_buttons()
            return

        if btn_id == "all_in":
            if self.state == "playing" and isinstance(self.turn_seat, int) and seat == self.turn_seat and self.in_hand.get(seat, False):
                self._do_all_in(seat)
                self._after_action(seat)
            return

        if self.state != "playing":
            return

        if not isinstance(self.turn_seat, int) or seat != self.turn_seat:
            return
        if not self.in_hand.get(seat, False):
            return
        if int(self.stacks.get(seat, 0) or 0) <= 0:
            return

        if btn_id == "fold":
            self.in_hand[seat] = False
            self.acted.add(seat)
            self._after_action(seat)
            return

        if btn_id == "check_call":
            self._do_check_call(seat)
            self._after_action(seat)
            return

        if btn_id == "bet_raise":
            self._do_bet_raise(seat)
            self._after_action(seat)
            return

    def _do_check_call(self, seat: int) -> None:
        need = max(0, int(self.current_bet) - int(self.bet_in_round.get(seat, 0) or 0))
        if need <= 0:
            self.acted.add(seat)
            return
        stack = int(self.stacks.get(seat, 0) or 0)
        pay = min(need, stack)
        self.stacks[seat] = stack - pay
        self.bet_in_round[seat] = int(self.bet_in_round.get(seat, 0) or 0) + pay
        self.pot += pay
        self.acted.add(seat)

    def _raise_size(self) -> int:
        # MVP: fixed raise size.
        return int(self.big_blind)

    def _do_bet_raise(self, seat: int) -> None:
        raise_amt = self._raise_size()
        target = int(self.current_bet + raise_amt) if self.current_bet > 0 else int(raise_amt)
        required = max(0, target - int(self.bet_in_round.get(seat, 0) or 0))
        stack = int(self.stacks.get(seat, 0) or 0)

        # If they can't complete the raise, treat as check/call.
        if required <= 0 or stack < required:
            self._do_check_call(seat)
            return

        self.stacks[seat] = stack - required
        self.bet_in_round[seat] = int(self.bet_in_round.get(seat, 0) or 0) + required
        self.pot += required
        self.current_bet = target
        # New raise resets acted (others must respond)
        self.acted = {seat}

    def _do_all_in(self, seat: int) -> None:
        """Move entire remaining stack in as a bet/raise (MVP: no side pots)."""
        stack = int(self.stacks.get(seat, 0) or 0)
        if stack <= 0:
            self.acted.add(seat)
            return

        self.stacks[seat] = 0
        self.bet_in_round[seat] = int(self.bet_in_round.get(seat, 0) or 0) + int(stack)
        self.pot += int(stack)

        # If this exceeds the current bet, treat as a raise.
        if int(self.bet_in_round.get(seat, 0) or 0) > int(self.current_bet):
            self.current_bet = int(self.bet_in_round.get(seat, 0) or 0)
            self.acted = {seat}
            return

        # Otherwise it's an all-in call/check.
        self.acted.add(seat)

    def _after_action(self, seat: int) -> None:
        # If only one player remains, award pot and end.
        remaining = [s for s, alive in self.in_hand.items() if alive]
        if len(remaining) <= 1:
            winner = remaining[0] if remaining else seat
            self.stacks[winner] = int(self.stacks.get(winner, 0) or 0) + int(self.pot)
            self.last_showdown = {
                "winners": [int(winner)],
                "descriptions": {str(int(winner)): "Uncontested"},
                "pot": int(self.pot),
            }
            self.pot = 0
            self.state = "showdown"
            self.turn_seat = None
            self._rebuild_buttons()
            return

        # Betting round complete?
        # MVP rule: players who are all-in (stack == 0) never block action progression.
        in_players = [s for s in self.hole.keys() if self.in_hand.get(s, False)]
        active_bettors = [s for s in in_players if int(self.stacks.get(s, 0) or 0) > 0]
        if all(int(self.bet_in_round.get(s, 0) or 0) == int(self.current_bet) for s in active_bettors) and all(s in self.acted for s in active_bettors):
            self._advance_street()
            return

        # Advance turn to next active seat that still needs to act.
        def needs_action(s: int) -> bool:
            if not bool(self.in_hand.get(s, False)):
                return False
            # All-in players cannot act.
            if int(self.stacks.get(s, 0) or 0) <= 0:
                return False
            # Needs action if they haven't acted since last raise, or they haven't matched the current bet.
            if s not in self.acted:
                return True
            return int(self.bet_in_round.get(s, 0) or 0) != int(self.current_bet)

        nxt = self._next_seat(seat, predicate=needs_action)
        if isinstance(nxt, int):
            self.turn_seat = int(nxt)
        else:
            # Fallback: pick any actionable seat.
            fallback = next((s for s in in_players if needs_action(int(s))), None)
            self.turn_seat = int(fallback) if isinstance(fallback, int) else None
        self._rebuild_buttons()

    def _is_hand_over(self) -> bool:
        return bool(self.state == "showdown" or self.last_showdown is not None)

    def _resolve_showdown(self) -> None:
        seats = [s for s in self.hole.keys() if self.in_hand.get(s, False)]
        if not seats:
            self.last_showdown = {"winners": [], "pot": int(self.pot)}
            self.pot = 0
            self.state = "showdown"
            self.turn_seat = None
            self._rebuild_buttons()
            return

        ranks: Dict[int, Tuple[int, Tuple[int, ...]]] = {}
        desc: Dict[str, str] = {}
        for s in seats:
            seven = list(self.hole.get(s, [])) + list(self.community)
            r = _best_rank_7(seven)
            ranks[int(s)] = r
            desc[str(int(s))] = _describe_rank(r)

        best = max(ranks.values())
        winners = [s for s, r in ranks.items() if r == best]

        # Split pot evenly (integer chips)
        if winners:
            share = int(self.pot) // int(len(winners))
            for w in winners:
                self.stacks[int(w)] = int(self.stacks.get(int(w), 0) or 0) + share
            # Remainder stays on table (ignored) for MVP

        self.last_showdown = {
            "winners": [int(w) for w in winners],
            "descriptions": desc,
            "pot": int(self.pot),
        }
        self.pot = 0
        self.state = "showdown"
        self.turn_seat = None
        self._rebuild_buttons()

    # --- Public state for Web UI ---

    def get_public_state(self, player_idx: int) -> Dict:
        seat = int(player_idx) if isinstance(player_idx, int) else -1
        players = []
        for s in self.active_players:
            stack = int(self.stacks.get(int(s), 0) or 0)
            if stack <= 0 and bool(self.in_hand.get(int(s), False)):
                status = "all-in"
            elif stack <= 0:
                status = "bust"
            else:
                status = "in" if self.in_hand.get(int(s), False) else "fold"
            players.append(
                {
                    "seat": int(s),
                    "name": self._seat_label(int(s)),
                    "stack": int(self.stacks.get(int(s), 0) or 0),
                    "status": status,
                    "bet": int(self.bet_in_round.get(int(s), 0) or 0),
                }
            )

        my_hole = [c.short() for c in self.hole.get(seat, [])] if seat in self.hole else []
        comm = [c.short() for c in self.community]

        revealed_holes: Dict[str, List[str]] = {}
        if self.state == "showdown":
            for s in self.active_players:
                ss = int(s)
                if bool(self.reveal_hole.get(ss, False)) and self.hole.get(ss):
                    revealed_holes[str(ss)] = [c.short() for c in (self.hole.get(ss) or [])]

        call_amount = None
        if isinstance(self.turn_seat, int) and seat == self.turn_seat and self.state == "playing" and self.in_hand.get(seat, False):
            need = max(0, int(self.current_bet) - int(self.bet_in_round.get(seat, 0) or 0))
            call_amount = int(need)

        return {
            "state": str(self.state),
            "street": str(self.street),
            "hand_id": int(self.hand_id),
            "dealer_seat": self.dealer_seat,
            "turn_seat": self.turn_seat,
            "pot": int(self.pot),
            "current_bet": int(self.current_bet),
            "call_amount": call_amount,
            "community": comm,
            "your_hole": my_hole,
            "revealed_holes": revealed_holes,
            "players": players,
            "showdown": self.last_showdown,
        }

    # --- Buttons ---

    def _rebuild_buttons(self) -> None:
        self.buttons = {}
        for s in self.active_players:
            self.buttons[int(s)] = {}

        if self.state == "showdown" and self._is_hand_over():
            for s in self.active_players:
                already = bool(self.next_hand_ready.get(int(s), False)) if int(self.next_hand_ready_hand_id) == int(self.hand_id) else False
                self.buttons[int(s)]["next_hand"] = _WebButton("Next Hand", enabled=not already)
                show = bool(self.reveal_hole.get(int(s), False))
                self.buttons[int(s)]["toggle_reveal"] = _WebButton("Hide Cards" if show else "Show Cards", enabled=True)
            return

        if self.state != "playing":
            return

        # Only current-turn player gets enabled actions (others disabled).
        for s in self.active_players:
            s = int(s)
            is_turn = isinstance(self.turn_seat, int) and s == int(self.turn_seat)
            alive = bool(self.in_hand.get(s, False))
            has_chips = int(self.stacks.get(s, 0) or 0) > 0
            can_act = bool(is_turn and alive and has_chips)

            call_amt = max(0, int(self.current_bet) - int(self.bet_in_round.get(s, 0) or 0))
            if call_amt <= 0:
                cc_text = "Check"
            else:
                cc_text = f"Call {call_amt}"

            self.buttons[s]["check_call"] = _WebButton(cc_text, enabled=can_act)
            self.buttons[s]["bet_raise"] = _WebButton("Bet/Raise", enabled=can_act and int(self.stacks.get(s, 0) or 0) > call_amt)
            self.buttons[s]["all_in"] = _WebButton("All-in", enabled=can_act and int(self.stacks.get(s, 0) or 0) > 0)
            self.buttons[s]["fold"] = _WebButton("Fold", enabled=can_act)

    # --- Rendering (Pyglet board) ---

    def draw(self) -> None:
        if not self.renderer:
            return
        try:
            w, h = int(getattr(self.renderer, "width", self.width)), int(getattr(self.renderer, "height", self.height))
        except Exception:
            w, h = self.width, self.height

        self._draw_background(w, h)

        # Title + status
        try:
            title = "Texas Hold'em"
            self.renderer.draw_text(title, 24, 24, font_size=24, color=(235, 235, 235), anchor_x="left", anchor_y="top")
            if self.state != "player_select":
                turn = self._seat_label(self.turn_seat)
                self.renderer.draw_text(
                    f"Hand {self.hand_id}  ·  Street: {self.street}  ·  Turn: {turn}",
                    24,
                    54,
                    font_size=14,
                    color=(200, 200, 200),
                    anchor_x="left",
                    anchor_y="top",
                )
        except Exception:
            pass

        # Table felt
        try:
            pad = int(min(w, h) * 0.10)
            tx, ty = pad, pad
            tw, th = w - pad * 2, h - pad * 2
            self.renderer.draw_rect((0, 65, 40), (tx, ty, tw, th), alpha=180)
            self.renderer.draw_rect((220, 200, 120), (tx, ty, tw, th), width=3, alpha=90)
        except Exception:
            pass

        # Community cards
        cx = w // 2
        cy = h // 2
        card_w, card_h = 78, 110
        gap = 14
        total = 5 * card_w + 4 * gap
        start_x = int(cx - total / 2)
        for i in range(5):
            x = start_x + i * (card_w + gap)
            y = int(cy - card_h / 2)
            label = self.community[i].short() if i < len(self.community) else ""
            self._draw_card((x, y, card_w, card_h), label=label, face=bool(label))

        # Pot
        try:
            self.renderer.draw_text(
                f"Pot: {self.pot}",
                cx,
                int(cy + card_h / 2 + 26),
                font_size=16,
                color=(240, 240, 240),
                anchor_x="center",
                anchor_y="bottom",
            )
        except Exception:
            pass

        # Showdown winners
        if isinstance(self.last_showdown, dict) and self.last_showdown.get("winners"):
            try:
                winners = [self._seat_label(int(s)) for s in (self.last_showdown.get("winners") or [])]
                msg = "Winners: " + ", ".join(winners)
                self.renderer.draw_text(msg, cx, int(cy - card_h / 2 - 24), font_size=16, color=(235, 235, 235), anchor_x="center", anchor_y="top")
            except Exception:
                pass

        # Revealed hole cards (board-friendly) — horizontal: bottom row, overflow to top row.
        if self.state == "showdown":
            try:
                revealed_seats: List[Tuple[int, str, List[str]]] = []
                for s in self.active_players:
                    ss = int(s)
                    if bool(self.reveal_hole.get(ss, False)) and self.hole.get(ss):
                        cards = [c.short() for c in (self.hole.get(ss) or [])][:2]
                        if cards:
                            revealed_seats.append((ss, self._seat_label(ss), cards))

                if revealed_seats:
                    # Size cards relative to window so rank/suit remain readable.
                    rw = max(78, min(110, int(w * 0.090)))
                    rh = int(rw * 1.38)
                    rgap = max(12, int(rw * 0.14))
                    pad_x = 16
                    pad_y = 14
                    label_h = 18
                    box_gap = 16

                    box_h = rh + label_h + pad_y * 2
                    box_w = int(pad_x * 2 + 2 * rw + rgap)

                    # Compute safe vertical regions to avoid overlapping the community cards.
                    community_top = int(cy - card_h / 2)
                    community_bottom = int(cy + card_h / 2)
                    min_bottom_top = community_bottom + 24
                    bottom_margin = 22

                    # Bottom row y
                    bottom_top = int(h - bottom_margin - box_h)
                    can_draw_bottom = bottom_top >= min_bottom_top

                    # Top row y (below title/status area)
                    top_top = 86
                    can_draw_top = (top_top + box_h) <= (community_top - 18)

                    # Determine capacity per row
                    available_w = max(0, int(w - 32))
                    per_row = max(1, int((available_w + box_gap) // (box_w + box_gap)))

                    # Split into bottom + overflow
                    bottom_items = []
                    top_items = []
                    if can_draw_bottom:
                        bottom_items = revealed_seats[:per_row]
                        overflow = revealed_seats[per_row:]
                    else:
                        overflow = revealed_seats

                    if overflow and can_draw_top:
                        top_items = overflow[:per_row]

                    def _draw_reveal_row(items: List[Tuple[int, str, List[str]]], top: int) -> None:
                        if not items:
                            return
                        row_w = len(items) * box_w + (len(items) - 1) * box_gap
                        left0 = int((w - row_w) / 2)
                        for idx, (seat, name, cards) in enumerate(items):
                            left = int(left0 + idx * (box_w + box_gap))
                            try:
                                color = PLAYER_COLORS[int(seat) % len(PLAYER_COLORS)]
                                border = tuple(int(v) for v in color)
                            except Exception:
                                border = (200, 200, 200)

                            self.renderer.draw_rect((10, 10, 12), (left, top, box_w, box_h), alpha=160)
                            self.renderer.draw_rect(border, (left, top, box_w, box_h), width=3, alpha=220)
                            self.renderer.draw_text(name, left + box_w // 2, top + pad_y, font_size=14, color=(235, 235, 235), anchor_x="center", anchor_y="top")

                            cards_y = top + pad_y + label_h
                            cards_x = left + pad_x
                            for j, c in enumerate(cards[:2]):
                                self._draw_card((int(cards_x + j * (rw + rgap)), int(cards_y), int(rw), int(rh)), label=str(c), face=True)

                    # Draw bottom row first, then top overflow row.
                    if can_draw_bottom:
                        _draw_reveal_row(bottom_items, bottom_top)
                    if can_draw_top:
                        _draw_reveal_row(top_items, top_top)
            except Exception:
                pass

    def _draw_background(self, w: int, h: int) -> None:
        try:
            self.renderer.draw_rect((10, 10, 12), (0, 0, w, h))
            self.renderer.draw_rect((180, 80, 235), (0, int(h * 0.78), w, int(h * 0.22)), alpha=10)
            self.renderer.draw_rect((240, 180, 90), (0, 0, w, int(h * 0.18)), alpha=6)

            r = int(min(w, h) * 0.40)
            self.renderer.draw_circle((100, 60, 160), (int(w * 0.50), int(h * 0.52)), r, alpha=7)
            self.renderer.draw_circle((60, 140, 235), (int(w * 0.50), int(h * 0.52)), int(r * 0.70), alpha=6)

            self.renderer.draw_line((200, 200, 220), (int(w * 0.08), int(h * 0.88)), (int(w * 0.30), int(h * 0.68)), width=3, alpha=22)
            self.renderer.draw_line((200, 200, 220), (int(w * 0.92), int(h * 0.12)), (int(w * 0.70), int(h * 0.32)), width=3, alpha=18)
        except Exception:
            try:
                self.renderer.draw_rect((10, 10, 12), (0, 0, w, h))
            except Exception:
                pass

    def _draw_card(self, rect: Tuple[int, int, int, int], label: str = "", face: bool = True) -> None:
        x, y, cw, ch = rect
        try:
            # Subtle shadow
            self.renderer.draw_rect((0, 0, 0), (x + 3, y + 3, cw, ch), alpha=55)

            if not face:
                # Card back
                self.renderer.draw_rect((50, 70, 150), (x, y, cw, ch))
                self.renderer.draw_rect((230, 230, 230), (x, y, cw, ch), width=2)
                # Simple pattern
                for i in range(5):
                    self.renderer.draw_line((200, 200, 240), (x + 6, y + 10 + i * 18), (x + cw - 6, y + 2 + i * 18), width=2, alpha=70)
                try:
                    self.renderer.draw_text("🂠", x + cw // 2, y + ch // 2, font_size=22, color=(235, 235, 235), anchor_x="center", anchor_y="center")
                except Exception:
                    pass
                return

            # Face-up
            self.renderer.draw_rect((248, 248, 248), (x, y, cw, ch))
            self.renderer.draw_rect((30, 30, 30), (x, y, cw, ch), width=2)
            self.renderer.draw_rect((210, 210, 210), (x + 3, y + 3, cw - 6, ch - 6), width=1)

            if not label:
                return

            t = str(label).strip()
            suit_raw = t[-1:] if t else ""
            rank_raw = t[:-1] if len(t) >= 2 else t
            suit_map = {"S": "♠", "H": "♥", "D": "♦", "C": "♣", "♠": "♠", "♥": "♥", "♦": "♦", "♣": "♣"}
            suit = suit_map.get(suit_raw, suit_raw)
            rank = "10" if rank_raw == "T" else rank_raw
            is_red = suit in ("♥", "♦")
            color = (220, 20, 20) if is_red else (20, 20, 20)

            # Scale text based on card size to avoid overlaps.
            corner_fs = max(11, min(16, int(cw * 0.20)))
            center_fs = max(22, min(42, int(ch * 0.42)))
            corner_pad = max(7, int(cw * 0.12))
            corner = f"{rank}{suit}"

            # Corners (keep fully inside)
            self.renderer.draw_text(corner, x + corner_pad, y + corner_pad, font_size=corner_fs, color=color, bold=True, anchor_x="left", anchor_y="top")
            self.renderer.draw_text(corner, x + cw - corner_pad, y + ch - corner_pad, font_size=corner_fs, color=color, bold=True, anchor_x="right", anchor_y="bottom")

            # Center suit
            self.renderer.draw_text(suit, x + cw // 2, y + ch // 2, font_size=center_fs, color=color, anchor_x="center", anchor_y="center")
        except Exception:
            return
