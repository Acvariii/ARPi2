from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

from config import Colors, PLAYER_COLORS
from core.player_selection import PlayerSelectionUI
from core.animation import (
    ParticleSystem, CardFlyAnim, TextPopAnim, PulseRing, ScreenFlash,
    _RAINBOW_PALETTE as _FW_COLORS, draw_rainbow_title,
)


@dataclass(frozen=True)
class CluedoCard:
    kind: str  # 'suspect' | 'weapon' | 'room'
    name: str

    def key(self) -> str:
        return f"{self.kind}:{self.name}"


class _WebButton:
    def __init__(self, text: str, enabled: bool = True):
        self.text = text
        self.enabled = enabled


class CluedoGame:
    """Cluedo (web-UI-first) with a colourful wall/board view.

    Simplified rules (MVP):
    - Random solution envelope (suspect/weapon/room).
    - Deal remaining cards to active players.
    - Turn loop: Roll -> Move (optional) -> Suggest (in room) OR Accuse (in room) -> End turn.
    - Suggestion: first next player who can show a matching card reveals one (to suggester only).
    - Wrong accusation eliminates the accuser.

    The Pyglet window is board-only; the Web UI drives actions via `buttons`.
    """

    SUSPECTS: List[Tuple[str, str]] = [
        ("🔴", "Miss Scarlett"),
        ("🟡", "Colonel Mustard"),
        ("⚪", "Mrs. White"),
        ("🟢", "Mr. Green"),
        ("🔵", "Mrs. Peacock"),
        ("🟣", "Professor Plum"),
    ]

    WEAPONS: List[Tuple[str, str]] = [
        ("🕯️", "Candlestick"),
        ("🗡️", "Dagger"),
        ("🔧", "Wrench"),
        ("🪢", "Rope"),
        ("🔫", "Revolver"),
        ("🧪", "Lead Pipe"),
    ]

    ROOMS: List[Tuple[str, str]] = [
        ("🍳", "Kitchen"),
        ("💃", "Ballroom"),
        ("🌿", "Conservatory"),
        ("🍽️", "Dining Room"),
        ("🏛️", "Hall"),
        ("🛋️", "Lounge"),
        ("📚", "Study"),
        ("📖", "Library"),
        ("🎱", "Billiard Room"),
    ]

    # Classic-style board (larger): bigger rooms + lots of corridor/empty space + explicit door markers.
    # Note: we intentionally avoid a 1:1 copy of the original copyrighted board layout.
    BOARD_SIZE = 25

    # Tile types: None (empty), "hall", "room", "accusation", "start"
    _TILE_HALL = "hall"
    _TILE_ROOM = "room"
    _TILE_ACCUSATION = "accusation"
    _TILE_START = "start"

    # Board caches (class-level, built once)
    _BOARD_BUILT: bool = False
    _GRID_KIND: List[List[Optional[str]]] = []
    _GRID_LABEL: List[List[Optional[str]]] = []
    _ROOM_RECTS: Dict[str, Tuple[int, int, int, int]] = {}  # name -> (r0,r1,c0,c1)
    _START_POSITIONS: List[Tuple[int, int]] = []
    _DOORS: Dict[Tuple[int, int], Tuple[str, str]] = {}  # (r,c) hall-pos -> (arrow, room_name)
    _ACCUSATION_RECTS: List[Tuple[int, int, int, int]] = []
    _OUTSIDE_STARTS: List[Tuple[int, int]] = []
    _ROOM_ANCHORS: Dict[str, Tuple[int, int]] = {}
    _ROOM_EXITS: Dict[str, Dict[str, Tuple[int, int]]] = {}

    ROOM_COLORS: Dict[str, Tuple[int, int, int]] = {
        "Kitchen": (255, 160, 160),
        "Ballroom": (255, 230, 140),
        "Conservatory": (170, 255, 180),
        "Dining Room": (255, 190, 120),
        "Hall": (180, 220, 255),
        "Lounge": (210, 170, 255),
        "Study": (170, 255, 245),
        "Library": (255, 200, 235),
        "Billiard Room": (210, 255, 170),
        "Accusation": (255, 236, 160),
    }

    def __init__(self, width: int, height: int, renderer=None):
        self.width = width
        self.height = height
        self.renderer = renderer

        self._ensure_board()

        # Per-game randomized doors/exits (defaults to the static layout, then randomized on start_game).
        self._doors: Dict[Tuple[int, int], Tuple[str, str]] = dict(getattr(self, "_DOORS", {}) or {})
        self._room_exits: Dict[str, Dict[str, Tuple[int, int]]] = dict(getattr(self, "_ROOM_EXITS", {}) or {})

        self.state = "player_select"
        self.selection_ui = PlayerSelectionUI(width, height)

        self.active_players: List[int] = []
        self.current_turn_idx: int = 0
        self.eliminated: List[int] = []
        self.winner: Optional[int] = None

        # Private hands
        self.hands: Dict[int, List[CluedoCard]] = {}

        # Solution envelope
        self.solution_suspect: Optional[str] = None
        self.solution_weapon: Optional[str] = None
        self.solution_room: Optional[str] = None

        # Positions (grid coordinates)
        self.player_pos: Dict[int, Tuple[int, int]] = {}

        # Turn action state
        self.last_roll: Optional[int] = None
        self.steps_remaining: int = 0

        # Dice details (2d6). last_roll remains the total for UI/buttons.
        self.last_dice: Optional[Tuple[int, int]] = None

        # Turn rule: at most one suggestion per turn.
        self.suggested_this_turn: bool = False

        # Suggestion reveal flow: if a player can disprove a suggestion, they choose which matching card to reveal.
        self._pending_reveal_suggester: Optional[int] = None
        self._pending_reveal_revealer: Optional[int] = None
        self._pending_reveal_options: List[Tuple[str, str]] = []  # (kind, name)

        # If a player suggests without rolling (starts turn already in a room), end their turn after the reveal completes.
        self._end_turn_after_suggestion: bool = False

        # Dice roll animation (board)
        self.dice_rolling: bool = False
        self.dice_roll_start: float = 0.0
        self._dice_show_until: float = 0.0

        # Interaction modes
        self._mode: str = "need_roll"  # need_roll | moving | in_room | suggest_pick_suspect | suggest_pick_weapon | accuse_pick_suspect | accuse_pick_weapon | accuse_pick_room
        self._pending_pick_suspect: Optional[str] = None
        self._pending_pick_weapon: Optional[str] = None

        # Events
        self._last_event: str = ""
        self._last_event_time: float = 0.0
        self._last_private_event: Dict[int, str] = {}
        self._last_private_event_time: Dict[int, float] = {}

        # Last suggestion (for UI/board hints)
        self._last_suggestion: Optional[Tuple[str, str, str]] = None  # (suspect, weapon, room)

        # Envelope peek is only allowed for a player after they have made a final accusation
        # and have either won (correct) or lost (eliminated by wrong accusation).
        self._envelope_peek_allowed: set[int] = set()

        # Web UI buttons
        self.buttons: Dict[int, Dict[str, _WebButton]] = {}

        # Incremented each time a new game starts (used by clients for per-game UI resets)
        self.game_id: int = 0

        self._seat_name_provider: Optional[Callable[[int], str]] = None

        # Opt-in flags used by the server
        self.web_ui_only_player_select = True
        self.board_only_mode = True

        # ── Particle animations ─────────────────────────────────────────────
        self._particles = ParticleSystem()
        self._anim_card_flips: list = []
        self._text_pops: list = []
        self._pulse_rings: list = []
        self._flashes: list = []
        self._anim_prev_winner: object = None
        self._anim_fw_timer: float = 0.0
        self._anim_prev_turn: object = None

    @classmethod
    def _ensure_board(cls) -> None:
        if bool(getattr(cls, "_BOARD_BUILT", False)):
            return

        size = int(getattr(cls, "BOARD_SIZE", 0) or 0)
        if size <= 0:
            size = 25

        # No empty spaces: everything starts as corridor, rooms overwrite.
        kind: List[List[Optional[str]]] = [[cls._TILE_HALL for _ in range(size)] for _ in range(size)]
        label: List[List[Optional[str]]] = [["Hallway" for _ in range(size)] for _ in range(size)]

        def in_bounds(r: int, c: int) -> bool:
            return 0 <= r < size and 0 <= c < size

        def fill_rect(tile_kind: str, tile_label: str, r0: int, r1: int, c0: int, c1: int) -> None:
            rr0, rr1 = min(r0, r1), max(r0, r1)
            cc0, cc1 = min(c0, c1), max(c0, c1)
            for r in range(rr0, rr1 + 1):
                for c in range(cc0, cc1 + 1):
                    if not in_bounds(r, c):
                        continue
                    kind[r][c] = str(tile_kind)
                    label[r][c] = str(tile_label)

        def fill_hall(r: int, c: int) -> None:
            if not in_bounds(r, c):
                return
            # Do not overwrite rooms.
            if kind[r][c] in (cls._TILE_ROOM, cls._TILE_ACCUSATION):
                return
            kind[r][c] = cls._TILE_HALL
            label[r][c] = "Hallway"

        # Layout rules:
        # - Rooms are <= 7x7
        # - Minimum 2 tiles of corridor between rooms horizontally/vertically
        # - Every room touches a board border (except Accusation, centered)
        # - No empty spaces: everything else is corridor
        # 3 columns of border-touching rooms, with 2-column corridor gaps.
        left_c0, left_c1 = 0, 6
        mid_c0, mid_c1 = 9, 15
        right_c0, right_c1 = 18, 24

        rooms: Dict[str, Tuple[int, int, int, int]] = {
            # Left border column (7-high rooms with 2-row gaps)
            "Kitchen": (0, 6, left_c0, left_c1),
            "Dining Room": (9, 15, left_c0, left_c1),
            "Lounge": (18, 24, left_c0, left_c1),

            # Middle column (touch top and bottom borders)
            "Ballroom": (0, 6, mid_c0, mid_c1),
            "Hall": (18, 24, mid_c0, mid_c1),

            # Right border column (fit 4 rooms with 2-row gaps; total 25)
            "Conservatory": (0, 4, right_c0, right_c1),
            "Billiard Room": (7, 11, right_c0, right_c1),
            "Library": (14, 18, right_c0, right_c1),
            "Study": (21, 24, right_c0, right_c1),
        }

        # Fill all rooms (blocks).
        for room_name, (r0, r1, c0, c1) in rooms.items():
            fill_rect(cls._TILE_ROOM, room_name, r0, r1, c0, c1)

        # Accusation room: centered and not touching borders.
        accusation_rect = (10, 14, 10, 14)  # 5x5 centered-ish
        fill_rect(cls._TILE_ACCUSATION, "Accusation", *accusation_rect)

        # Corridors already fill all remaining spaces by default.
        # Ensure corridor in the explicit inter-room gaps too (defensive, and avoids accidental overwrite).
        for r in [7, 8, 16, 17]:
            for c in range(size):
                fill_hall(int(r), int(c))
        for c in [7, 8, 16, 17]:
            for r in range(size):
                fill_hall(int(r), int(c))

        # Door markers (on hallway tiles). Movement between hall<->room is only allowed via these.
        doors: Dict[Tuple[int, int], Tuple[str, str]] = {}

        def add_door(hall_pos: Tuple[int, int], arrow: str, room_name: str) -> None:
            hr, hc = int(hall_pos[0]), int(hall_pos[1])
            if not in_bounds(hr, hc):
                return
            fill_hall(hr, hc)
            doors[(hr, hc)] = (str(arrow), str(room_name))

        # Entrances (exact constraints from user):
        # Kitchen: only from bottom
        add_door((7, 3), "↑", "Kitchen")
        # Dining: only from bottom
        add_door((16, 3), "↑", "Dining Room")
        # Lounge: only from top
        add_door((17, 3), "↓", "Lounge")

        # Ballroom: from bottom and right
        add_door((7, 12), "↑", "Ballroom")
        add_door((3, 16), "←", "Ballroom")

        # Conservatory: only one entrance (choose left)
        add_door((2, 17), "→", "Conservatory")

        # Billiard: from left
        add_door((9, 17), "→", "Billiard Room")

        # Library: from left
        add_door((16, 17), "→", "Library")

        # Study: from top
        add_door((20, 21), "↓", "Study")

        # Hall: from top
        add_door((17, 12), "↓", "Hall")

        # Accusation: no explicit doors needed; can be entered from any adjacent corridor.

        # Start squares: outside the 25x25 grid. They sit "between rooms" around the perimeter,
        # and once a player steps onto the board, they cannot step back out.
        # Starts must be next to an empty (hall) space.
        starts = [
            (-1, 7),
            (-1, 16),
            (size, 7),
            (size, 16),
            (7, -1),
            (16, -1),
            (6, size),
            (13, size),
        ]
        # Ensure the adjacent "entry" tiles are corridors (and not rooms).
        outside_starts: List[Tuple[int, int]] = []
        for r, c in starts:
            rr, cc = int(r), int(c)
            outside_starts.append((rr, cc))
            # Adjacent entry into board
            if rr == -1 and 0 <= cc < size:
                fill_hall(0, cc)
            elif rr == size and 0 <= cc < size:
                fill_hall(size - 1, cc)
            elif cc == -1 and 0 <= rr < size:
                fill_hall(rr, 0)
            elif cc == size and 0 <= rr < size:
                fill_hall(rr, size - 1)

        start_positions: List[Tuple[int, int]] = list(outside_starts)

        cls._GRID_KIND = kind
        cls._GRID_LABEL = label
        cls._ROOM_RECTS = {k: tuple(v) for k, v in rooms.items()}
        cls._DOORS = doors
        cls._START_POSITIONS = list(start_positions)
        cls._ACCUSATION_RECTS = [tuple(accusation_rect)]
        cls._OUTSIDE_STARTS = list(outside_starts)

        # Room anchors (center points) and exits (for "room counts as one space" movement).
        anchors: Dict[str, Tuple[int, int]] = {}
        for room_name, (r0, r1, c0, c1) in rooms.items():
            anchors[str(room_name)] = (int((int(r0) + int(r1)) // 2), int((int(c0) + int(c1)) // 2))
        exits: Dict[str, Dict[str, Tuple[int, int]]] = {}
        arrow_to_dir = {"↑": "up", "↓": "down", "←": "left", "→": "right"}
        opposite = {"up": "down", "down": "up", "left": "right", "right": "left"}
        for (hr, hc), (arrow, room_name) in doors.items():
            entry_dir = arrow_to_dir.get(str(arrow))
            if not entry_dir:
                continue
            exit_dir = opposite.get(entry_dir)
            if not exit_dir:
                continue
            rn = str(room_name)
            exits.setdefault(rn, {})[exit_dir] = (int(hr), int(hc))
        cls._ROOM_ANCHORS = anchors
        cls._ROOM_EXITS = exits
        cls._BOARD_BUILT = True

    def set_name_provider(self, provider: Optional[Callable[[int], str]]) -> None:
        self._seat_name_provider = provider

    def _seat_name(self, seat: int) -> str:
        if self._seat_name_provider is not None:
            try:
                return str(self._seat_name_provider(int(seat)))
            except Exception:
                pass
        return f"Player {int(seat) + 1}"

    def _set_event(self, msg: str) -> None:
        self._last_event = str(msg or "")
        self._last_event_time = time.time()

    def _set_private_event(self, seat: int, msg: str) -> None:
        self._last_private_event[int(seat)] = str(msg or "")
        self._last_private_event_time[int(seat)] = time.time()

    def _current_turn_seat(self) -> Optional[int]:
        if not self.active_players:
            return None
        # Clamp
        if self.current_turn_idx < 0 or self.current_turn_idx >= len(self.active_players):
            self.current_turn_idx = 0
        return int(self.active_players[self.current_turn_idx])

    def _advance_turn(self) -> None:
        if not self.active_players:
            return
        if self.winner is not None:
            return

        # Find next non-eliminated
        start = self.current_turn_idx
        for step in range(1, len(self.active_players) + 1):
            idx = (start + step) % len(self.active_players)
            seat = int(self.active_players[idx])
            if seat not in set(self.eliminated):
                self.current_turn_idx = idx
                self.last_roll = None
                self.steps_remaining = 0
                self.last_dice = None
                self.suggested_this_turn = False
                self._pending_reveal_suggester = None
                self._pending_reveal_revealer = None
                self._pending_reveal_options = []
                self._end_turn_after_suggestion = False
                self._mode = "need_roll"
                self._pending_pick_suspect = None
                self._pending_pick_weapon = None
                return

        # Everyone eliminated (shouldn't happen)
        self.winner = None

    def start_game(self, selected_indices: List[int]) -> None:
        self._ensure_board()
        seats = [int(i) for i in selected_indices if isinstance(i, int) or str(i).isdigit()]
        # Cluedo supports 3..6 players (seats 0..5).
        seats = [s for s in seats if 0 <= s <= 5]
        if len(seats) < 3:
            return

        self.game_id = int(self.game_id) + 1

        self.active_players = seats
        self.current_turn_idx = random.randrange(len(seats))
        self.eliminated = []
        self.winner = None

        # Choose solution
        self.solution_suspect = random.choice([n for _, n in self.SUSPECTS])
        self.solution_weapon = random.choice([n for _, n in self.WEAPONS])
        self.solution_room = random.choice([n for _, n in self.ROOMS])

        # Build deck excluding solution
        deck: List[CluedoCard] = []
        for _, n in self.SUSPECTS:
            if n != self.solution_suspect:
                deck.append(CluedoCard("suspect", n))
        for _, n in self.WEAPONS:
            if n != self.solution_weapon:
                deck.append(CluedoCard("weapon", n))
        for _, n in self.ROOMS:
            if n != self.solution_room:
                deck.append(CluedoCard("room", n))

        random.shuffle(deck)
        self.hands = {s: [] for s in seats}
        for i, card in enumerate(deck):
            seat = seats[i % len(seats)]
            self.hands[seat].append(card)

        # Start positions (distinct start squares)
        starts = list(self._START_POSITIONS or [])
        try:
            random.shuffle(starts)
        except Exception:
            pass
        self.player_pos = {}
        for i, s in enumerate(seats):
            self.player_pos[int(s)] = starts[i % len(starts)]

        # Turn action state
        self.last_roll = None
        self.steps_remaining = 0
        self.last_dice = None
        self.suggested_this_turn = False
        self._pending_reveal_suggester = None
        self._pending_reveal_revealer = None
        self._pending_reveal_options = []
        self._end_turn_after_suggestion = False
        self.dice_rolling = False
        self.dice_roll_start = 0.0
        self._dice_show_until = 0.0
        self._mode = "need_roll"
        self._pending_pick_suspect = None
        self._pending_pick_weapon = None
        self._envelope_peek_allowed = set()

        self.state = "playing"
        self._set_event("Cluedo started. Find the culprit!")

        # Randomize door positions each game while keeping the same allowed sides.
        self._randomize_doors()
        self._rebuild_buttons_all()

    def handle_player_quit(self, seat: int) -> None:
        """Handle a player disconnecting mid-game.

        Cluedo can freeze if the current-turn player leaves or if a pending reveal is
        waiting for a seat that no longer has a Web UI client.

        We also redistribute the quitter's hand to keep the game playable.
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

        was_turn = bool(self._current_turn_seat() == s)

        # If a reveal is pending and either suggester or revealer quits, cancel it.
        if self._mode == "reveal_pick":
            if int(self._pending_reveal_revealer or -1) == s or int(self._pending_reveal_suggester or -1) == s:
                self._pending_reveal_suggester = None
                self._pending_reveal_revealer = None
                self._pending_reveal_options = []
                self._end_turn_after_suggestion = False
                self._mode = "in_room"

        # Redistribute their cards to remaining players so suggestions remain resolvable.
        quitter_hand = list(self.hands.pop(s, []) or [])
        remaining = [int(x) for x in self.active_players if int(x) != s]
        if remaining and quitter_hand:
            random.shuffle(quitter_hand)
            for i, card in enumerate(quitter_hand):
                tgt = int(remaining[i % len(remaining)])
                self.hands.setdefault(tgt, []).append(card)

        # Remove from the game.
        self.active_players = remaining
        try:
            self.player_pos.pop(s, None)
        except Exception:
            pass
        if s not in set(self.eliminated):
            self.eliminated.append(int(s))

        if not self.active_players:
            self.state = "player_select"
            self._set_event("All players left")
            self._rebuild_buttons_all()
            return

        # Winner if only one non-eliminated remains.
        remaining_live = [x for x in self.active_players if int(x) not in set(self.eliminated)]
        if len(remaining_live) == 1:
            self.winner = int(remaining_live[0])
            self._set_event(f"{self._seat_name(self.winner)} wins! (Last remaining)")
            self._rebuild_buttons_all()
            return

        # Keep the turn index valid.
        if self.current_turn_idx >= len(self.active_players):
            self.current_turn_idx = 0

        if was_turn:
            # Reset turn state and advance to the next available seat.
            self._advance_turn()

        self._set_event(f"{self._seat_name(s)} quit")
        self._rebuild_buttons_all()

    def _randomize_doors(self) -> None:
        """Randomize door positions along the same allowed room sides.

        This keeps the 'which side' constraints stable, but changes the exact door coordinate
        along that side for variety.
        """

        rects = dict(self._ROOM_RECTS or {})
        if not rects:
            return

        # Allowed door sides per room.
        # side: 'top'|'bottom'|'left'|'right'
        allowed: Dict[str, List[str]] = {
            "Kitchen": ["bottom"],
            "Dining Room": ["bottom"],
            "Lounge": ["top"],
            "Hall": ["top"],
            "Ballroom": ["bottom", "right"],
            "Conservatory": ["left"],
            "Billiard Room": ["left"],
            "Library": ["left"],
            "Study": ["top"],
        }

        used: set[Tuple[int, int]] = set()
        doors: Dict[Tuple[int, int], Tuple[str, str]] = {}

        def is_corridor(rc: Tuple[int, int]) -> bool:
            k, _ = self._tile_info(rc)
            return bool(k in (self._TILE_HALL, self._TILE_START))

        def candidates_for(room_name: str, side: str) -> List[Tuple[int, int, str]]:
            r0, r1, c0, c1 = rects[room_name]
            r0, r1, c0, c1 = int(r0), int(r1), int(c0), int(c1)
            out: List[Tuple[int, int, str]] = []
            if side == "bottom":
                rr = r1 + 1
                for cc in range(c0, c1 + 1):
                    out.append((rr, cc, "↑"))
            elif side == "top":
                rr = r0 - 1
                for cc in range(c0, c1 + 1):
                    out.append((rr, cc, "↓"))
            elif side == "left":
                cc = c0 - 1
                for rr in range(r0, r1 + 1):
                    out.append((rr, cc, "→"))
            elif side == "right":
                cc = c1 + 1
                for rr in range(r0, r1 + 1):
                    out.append((rr, cc, "←"))
            # Filter to valid in-bounds corridor tiles.
            out2: List[Tuple[int, int, str]] = []
            for rr, cc, arrow in out:
                if 0 <= int(rr) < self.BOARD_SIZE and 0 <= int(cc) < self.BOARD_SIZE and is_corridor((int(rr), int(cc))):
                    out2.append((int(rr), int(cc), str(arrow)))
            return out2

        # Pick a random tile on the allowed side(s) for each room.
        for room_name, sides in allowed.items():
            if room_name not in rects:
                continue
            for side in list(sides or []):
                cand = [c for c in candidates_for(room_name, side) if (c[0], c[1]) not in used]
                if not cand:
                    # Fallback: allow collisions if we must.
                    cand = candidates_for(room_name, side)
                if not cand:
                    continue
                rr, cc, arrow = random.choice(cand)
                used.add((rr, cc))
                doors[(rr, cc)] = (arrow, str(room_name))

        # Build exits for "room counts as one space" movement.
        exits: Dict[str, Dict[str, Tuple[int, int]]] = {}
        arrow_to_dir = {"↑": "up", "↓": "down", "←": "left", "→": "right"}
        opposite = {"up": "down", "down": "up", "left": "right", "right": "left"}
        for (hr, hc), (arrow, room_name) in doors.items():
            entry_dir = arrow_to_dir.get(str(arrow))
            if not entry_dir:
                continue
            exit_dir = opposite.get(entry_dir)
            if not exit_dir:
                continue
            exits.setdefault(str(room_name), {})[exit_dir] = (int(hr), int(hc))

        self._doors = doors
        self._room_exits = exits

    def _rebuild_buttons_all(self) -> None:
        self.buttons = {}
        for seat in range(8):
            self.buttons[seat] = self._build_buttons_for_player(seat)

    def _build_buttons_for_player(self, seat: int) -> Dict[str, _WebButton]:
        btns: Dict[str, _WebButton] = {}
        if self.state != "playing":
            return btns

        # Special case: suggestion reveal selection is made by the revealer (even though it's not their turn).
        if self._mode == "reveal_pick":
            revealer = self._pending_reveal_revealer
            suggester = self._pending_reveal_suggester
            if revealer is None or suggester is None:
                return btns
            if int(seat) != int(revealer):
                return btns

            # Present only the matching cards as choices.
            for kind, name in (self._pending_reveal_options or []):
                kid = f"reveal:{str(kind)}:{str(name)}"
                btns[kid] = _WebButton(f"Reveal {str(kind).title()} — {str(name)}", enabled=True)
            return btns

        turn_seat = self._current_turn_seat()
        is_turn = (turn_seat is not None and int(seat) == int(turn_seat) and int(seat) not in set(self.eliminated))

        # Always show (disabled) to non-turn players for clarity
        btns["roll"] = _WebButton("Roll", enabled=is_turn and (self.last_roll is None) and (not bool(self.dice_rolling)))
        # Only show Envelope when this seat is allowed to peek.
        if int(seat) in set(self._envelope_peek_allowed or set()):
            btns["envelope"] = _WebButton("Envelope", enabled=(not bool(self.dice_rolling)))
        btns["end_turn"] = _WebButton("End Turn", enabled=is_turn and self.last_roll is not None)

        # Movement (enable only if target tile exists)
        cur_pos = self.player_pos.get(int(turn_seat)) if is_turn else None
        move_enabled = is_turn and self.steps_remaining > 0 and cur_pos is not None
        btns["move:up"] = _WebButton("↑", enabled=bool(move_enabled and self._can_move(cur_pos, (-1, 0))))
        btns["move:down"] = _WebButton("↓", enabled=bool(move_enabled and self._can_move(cur_pos, (1, 0))))
        btns["move:left"] = _WebButton("←", enabled=bool(move_enabled and self._can_move(cur_pos, (0, -1))))
        btns["move:right"] = _WebButton("→", enabled=bool(move_enabled and self._can_move(cur_pos, (0, 1))))

        tile_kind, tile_label = self._tile_info(cur_pos) if cur_pos is not None else (None, None)
        in_suggest_room = bool(tile_kind == self._TILE_ROOM and isinstance(tile_label, str) and tile_label not in ("Accusation",))
        # Suggest: must be in the room you're suggesting, and after movement ends.
        suggest_enabled = is_turn and (not bool(self.dice_rolling)) and (not bool(self.suggested_this_turn)) and self.steps_remaining == 0 and in_suggest_room
        # Accuse: only from the Accusation room.
        in_accuse_room = bool(tile_kind == self._TILE_ACCUSATION)
        accuse_enabled = is_turn and (not bool(self.dice_rolling)) and self.winner is None and in_accuse_room
        btns["suggest"] = _WebButton("Suggest", enabled=suggest_enabled)
        btns["accuse"] = _WebButton("Accuse", enabled=accuse_enabled)

        # Selection modes
        if is_turn and self._mode in ("suggest_pick_suspect", "accuse_pick_suspect"):
            for emoji, name in self.SUSPECTS:
                btns[f"pick_suspect:{name}"] = _WebButton(f"{emoji} {name}", enabled=True)
        if is_turn and self._mode in ("suggest_pick_weapon", "accuse_pick_weapon"):
            for emoji, name in self.WEAPONS:
                btns[f"pick_weapon:{name}"] = _WebButton(f"{emoji} {name}", enabled=True)
        if is_turn and self._mode == "accuse_pick_room":
            for emoji, name in self.ROOMS:
                btns[f"pick_room:{name}"] = _WebButton(f"{emoji} {name}", enabled=True)

        return btns

    def handle_click(self, player_idx: int, btn_id: str) -> None:
        if self.state != "playing":
            return

        seat = int(player_idx)

        # Envelope peeks are allowed even when it's not your turn and even after the game ends,
        # but only for players who earned the right to peek (after their final accusation).
        if btn_id == "envelope":
            if seat not in set(self._envelope_peek_allowed or set()):
                return
            if self.solution_suspect and self.solution_weapon and self.solution_room:
                self._set_private_event(seat, f"Case File: {self.solution_suspect} · {self.solution_weapon} · {self.solution_room}")
            else:
                self._set_private_event(seat, "Case File is empty? (not initialized)")
            self._rebuild_buttons_all()
            return

        if self.winner is not None:
            return

        # If we're waiting for a reveal choice, only the designated revealer may act.
        if self._mode == "reveal_pick":
            revealer = self._pending_reveal_revealer
            suggester = self._pending_reveal_suggester
            if revealer is None or suggester is None:
                # Safety: clear bad pending state.
                self._pending_reveal_suggester = None
                self._pending_reveal_revealer = None
                self._pending_reveal_options = []
                self._mode = "in_room"
                self._rebuild_buttons_all()
                return
            if int(seat) != int(revealer):
                return
            if not btn_id.startswith("reveal:"):
                return

            try:
                _, kind, name = btn_id.split(":", 2)
            except Exception:
                return

            opts = list(self._pending_reveal_options or [])
            if (str(kind), str(name)) not in [(str(k), str(n)) for (k, n) in opts]:
                return

            self._set_private_event(int(suggester), f"Revealed by {self._seat_name(int(revealer))}: {str(kind).title()} — {str(name)}")
            self._set_private_event(int(revealer), f"You revealed: {str(kind).title()} — {str(name)}")

            self._pending_reveal_suggester = None
            self._pending_reveal_revealer = None
            self._pending_reveal_options = []

            # Return control to the suggester's turn.
            self._mode = "in_room"

            # If the suggester started the turn in the room and used their "free" suggestion, end their turn now.
            if bool(self._end_turn_after_suggestion):
                self._end_turn_after_suggestion = False
                self._advance_turn()

            self._rebuild_buttons_all()
            return

        turn_seat = self._current_turn_seat()
        if turn_seat is None or seat != int(turn_seat):
            return
        if seat in set(self.eliminated):
            return

        if btn_id == "roll":
            if self.last_roll is not None or bool(self.dice_rolling):
                return
            self.dice_rolling = True
            self.dice_roll_start = time.time()
            self._set_event(f"{self._seat_name(seat)} is rolling…")
            self._rebuild_buttons_all()
            return

        if btn_id.startswith("move:"):
            if self.steps_remaining <= 0:
                return
            direction = btn_id.split(":", 1)[1]
            before_kind, before_label = self._tile_info(self.player_pos.get(seat))
            self._move_pos(seat, direction)
            after_kind, after_label = self._tile_info(self.player_pos.get(seat))

            # Consume one step for the attempted move.
            self.steps_remaining = max(0, int(self.steps_remaining) - 1)

            # If you enter a room/accusation, movement ends immediately.
            if after_kind in (self._TILE_ROOM, self._TILE_ACCUSATION) and (after_kind != before_kind or after_label != before_label):
                self.steps_remaining = 0

            if self.steps_remaining == 0:
                self._mode = "in_room"
            self._rebuild_buttons_all()
            return

        if btn_id == "suggest":
            if self.steps_remaining != 0:
                return
            if bool(self.suggested_this_turn):
                return
            # Must be in a room; room is taken from your current location.
            kind, label = self._tile_info(self.player_pos.get(seat))
            if not (kind == self._TILE_ROOM and isinstance(label, str) and label not in ("Accusation",)):
                return
            self._mode = "suggest_pick_suspect"
            self._pending_pick_suspect = None
            self._pending_pick_weapon = None
            self._rebuild_buttons_all()
            return

        if btn_id == "accuse":
            # Accuse only from the Accusation room.
            kind, _ = self._tile_info(self.player_pos.get(seat))
            if kind != self._TILE_ACCUSATION:
                return
            self._mode = "accuse_pick_suspect"
            self._pending_pick_suspect = None
            self._pending_pick_weapon = None
            self._rebuild_buttons_all()
            return

        if btn_id.startswith("pick_suspect:"):
            name = btn_id.split(":", 1)[1]
            self._pending_pick_suspect = name
            if self._mode == "suggest_pick_suspect":
                self._mode = "suggest_pick_weapon"
            elif self._mode == "accuse_pick_suspect":
                self._mode = "accuse_pick_weapon"
            self._rebuild_buttons_all()
            return

        if btn_id.startswith("pick_weapon:"):
            weapon = btn_id.split(":", 1)[1]
            suspect = self._pending_pick_suspect
            if not suspect:
                return
            self._pending_pick_weapon = weapon

            # Suggestion room is the player's current room tile.
            pos = self.player_pos.get(seat)
            kind, label = self._tile_info(pos)
            room = label if (kind == self._TILE_ROOM and isinstance(label, str)) else None

            if self._mode == "suggest_pick_weapon":
                if not room:
                    return
                self.suggested_this_turn = True
                self._end_turn_after_suggestion = (self.last_roll is None)

                self._resolve_suggestion(seat, suspect, weapon, room)
                if self._mode != "reveal_pick":
                    self._mode = "in_room"
                self._pending_pick_suspect = None
                self._pending_pick_weapon = None

                # If the suggestion resolved immediately (no reveal needed), end turn now when applicable.
                if bool(self._end_turn_after_suggestion) and self._mode != "reveal_pick":
                    self._end_turn_after_suggestion = False
                    self._advance_turn()
                self._rebuild_buttons_all()
                return

            if self._mode == "accuse_pick_weapon":
                # In the Accusation room, you choose the room as part of the accusation.
                self._mode = "accuse_pick_room"
                self._rebuild_buttons_all()
                return

        if btn_id.startswith("pick_room:"):
            room_pick = btn_id.split(":", 1)[1]
            suspect = self._pending_pick_suspect
            weapon = self._pending_pick_weapon
            if not suspect or not weapon:
                return
            if self._mode != "accuse_pick_room":
                return
            self._resolve_accusation(seat, suspect, weapon, room_pick)
            self._mode = "in_room"
            self._pending_pick_suspect = None
            self._pending_pick_weapon = None
            self._rebuild_buttons_all()
            return

        if btn_id == "end_turn":
            if self.last_roll is None:
                return
            self._advance_turn()
            self._rebuild_buttons_all()
            return

    def _tile_info(self, pos: Optional[Tuple[int, int]]):
        if pos is None:
            return None, None
        r, c = int(pos[0]), int(pos[1])
        if (r, c) in set(self._OUTSIDE_STARTS or []):
            return self._TILE_START, "Start"
        if r < 0 or c < 0 or r >= self.BOARD_SIZE or c >= self.BOARD_SIZE:
            return None, None

        try:
            kind = self._GRID_KIND[r][c]
            lab = self._GRID_LABEL[r][c]
        except Exception:
            kind, lab = None, None
        return kind, lab

    @staticmethod
    def _arrow_matches_delta(arrow: str, delta: Tuple[int, int]) -> bool:
        dr, dc = int(delta[0]), int(delta[1])
        if arrow == "↑":
            return dr == -1 and dc == 0
        if arrow == "↓":
            return dr == 1 and dc == 0
        if arrow == "←":
            return dr == 0 and dc == -1
        if arrow == "→":
            return dr == 0 and dc == 1
        return False

    @staticmethod
    def _opposite_delta(delta: Tuple[int, int]) -> Tuple[int, int]:
        return (-int(delta[0]), -int(delta[1]))

    def _can_move(self, pos: Tuple[int, int], delta: Tuple[int, int]) -> bool:
        r, c = int(pos[0]), int(pos[1])
        dr, dc = int(delta[0]), int(delta[1])
        nxt = (r + dr, c + dc)
        # Cannot move onto outside start squares from the board (one-way start).
        if nxt in set(self._OUTSIDE_STARTS or []):
            return False

        # From outside start, you can only step into the adjacent in-bounds hall tile.
        if (r, c) in set(self._OUTSIDE_STARTS or []):
            nr, nc = int(nxt[0]), int(nxt[1])
            if not (0 <= nr < self.BOARD_SIZE and 0 <= nc < self.BOARD_SIZE):
                return False
            k, _ = self._tile_info((nr, nc))
            return bool(k in (self._TILE_HALL, self._TILE_START))
        kind_next, label_next = self._tile_info(nxt)
        if kind_next is None:
            return False

        kind_cur, label_cur = self._tile_info((r, c))

        # Accusation: can be entered from any adjacent corridor/start, but can never be left (or moved within).
        if kind_cur == self._TILE_ACCUSATION:
            return False
        if kind_next == self._TILE_ACCUSATION:
            return bool(kind_cur in (self._TILE_HALL, self._TILE_START) and abs(dr) + abs(dc) == 1)

        # Rooms count as one space: if in a room, directional moves take you out via that room's exit (if present).
        if kind_cur == self._TILE_ROOM and isinstance(label_cur, str):
            exit_dir = None
            if (dr, dc) == (-1, 0):
                exit_dir = "up"
            elif (dr, dc) == (1, 0):
                exit_dir = "down"
            elif (dr, dc) == (0, -1):
                exit_dir = "left"
            elif (dr, dc) == (0, 1):
                exit_dir = "right"
            if not exit_dir:
                return False
            return bool((self._room_exits or {}).get(str(label_cur), {}).get(exit_dir) is not None)

        # Enforce room entrances/exits via explicit door markers.
        cur_is_hall = bool(kind_cur in (self._TILE_HALL, self._TILE_START))
        nxt_is_hall = bool(kind_next in (self._TILE_HALL, self._TILE_START))
        cur_is_roomish = bool(kind_cur in (self._TILE_ROOM, self._TILE_ACCUSATION))
        nxt_is_roomish = bool(kind_next in (self._TILE_ROOM, self._TILE_ACCUSATION))

        if cur_is_hall and nxt_is_roomish:
            door = (self._doors or {}).get((r, c))
            if not door:
                return False
            arrow, door_room = door
            if str(door_room) != str(label_next):
                return False
            return bool(self._arrow_matches_delta(str(arrow), (dr, dc)))

        if cur_is_roomish and nxt_is_hall:
            door = (self._doors or {}).get((int(nxt[0]), int(nxt[1])))
            if not door:
                return False
            arrow, door_room = door
            if str(door_room) != str(label_cur):
                return False
            return bool(self._arrow_matches_delta(str(arrow), self._opposite_delta((dr, dc))))

        # Normal movement within halls.
        if cur_is_hall and nxt_is_hall:
            return True
        # Do not allow stepping around inside rooms; they count as a single space.
        return False

    def _move_pos(self, seat: int, direction: str) -> None:
        current = self.player_pos.get(seat)
        if current is None:
            return
        # Room movement uses exits (teleport from room anchor to the corridor door tile).
        cur_kind, cur_label = self._tile_info(current)
        delta = (0, 0)
        if direction == "up":
            delta = (-1, 0)
        elif direction == "down":
            delta = (1, 0)
        elif direction == "left":
            delta = (0, -1)
        elif direction == "right":
            delta = (0, 1)
        if not self._can_move(current, delta):
            return

        if cur_kind == self._TILE_ROOM and isinstance(cur_label, str):
            exit_dir = direction
            door_pos = (self._room_exits or {}).get(str(cur_label), {}).get(str(exit_dir))
            if door_pos is not None:
                self.player_pos[seat] = (int(door_pos[0]), int(door_pos[1]))
            return

        nxt = (int(current[0]) + int(delta[0]), int(current[1]) + int(delta[1]))
        nxt_kind, nxt_label = self._tile_info(nxt)
        # Hall -> Room: snap to the room anchor to behave like "one space".
        if cur_kind in (self._TILE_HALL, self._TILE_START) and nxt_kind == self._TILE_ROOM and isinstance(nxt_label, str):
            anchor = (self._ROOM_ANCHORS or {}).get(str(nxt_label))
            if anchor is not None:
                self.player_pos[seat] = (int(anchor[0]), int(anchor[1]))
                return

        # Normal adjacent move.
        self.player_pos[seat] = nxt

    def _resolve_suggestion(self, seat: int, suspect: str, weapon: str, room: str) -> None:
        suggester = int(seat)
        msg = f"{self._seat_name(suggester)} suggests {suspect} with the {weapon} in the {room}."
        self._set_event(msg)
        # 🔍 Suggestion animation
        try:
            _cx, _cy = self.width // 2, self.height // 2
            self._flashes.append(ScreenFlash((60, 100, 200), peak_alpha=40, duration=0.4))
            self._text_pops.append(TextPopAnim(
                "🔍 Suggestion!", _cx, _cy - 50, (120, 170, 255), font_size=26))
            self._particles.emit_sparkle(_cx, _cy, (120, 170, 255), count=14)
        except Exception:
            pass

        self._last_suggestion = (str(suspect), str(weapon), str(room))

        revealer = None
        matches_for_revealer: List[CluedoCard] = []
        ap = list(self.active_players)
        if suggester in ap:
            start = ap.index(suggester)
        else:
            start = 0

        wanted = {f"suspect:{suspect}", f"weapon:{weapon}", f"room:{room}"}
        for step in range(1, len(ap) + 1):
            other = int(ap[(start + step) % len(ap)])
            if other == suggester:
                continue
            # Eliminated players still must show cards to disprove suggestions.
            cards = self.hands.get(other, [])
            matches = [c for c in cards if c.key() in wanted]
            if matches:
                revealer = other
                matches_for_revealer = list(matches)
                break

        if revealer is None or not matches_for_revealer:
            self._set_private_event(suggester, "No one could reveal a matching card.")
            return

        # Ask the revealer which matching card to show.
        self._pending_reveal_suggester = int(suggester)
        self._pending_reveal_revealer = int(revealer)
        self._pending_reveal_options = [(str(c.kind), str(c.name)) for c in matches_for_revealer]
        self._mode = "reveal_pick"

        self._set_private_event(suggester, f"Waiting for {self._seat_name(int(revealer))} to reveal a card…")
        self._set_private_event(int(revealer), f"Choose a card to reveal to {self._seat_name(int(suggester))}.")

    def _resolve_accusation(self, seat: int, suspect: str, weapon: str, room: str) -> None:
        accuser = int(seat)
        msg = f"{self._seat_name(accuser)} accuses {suspect} with the {weapon} in the {room}."
        self._set_event(msg)

        correct = (
            suspect == self.solution_suspect
            and weapon == self.solution_weapon
            and room == self.solution_room
        )

        if correct:
            self.winner = accuser
            # ✨ Correct accusation — fireworks!
            try:
                import random as _rnd
                _cx, _cy = self.width // 2, self.height // 2
                self._flashes.append(ScreenFlash((220, 200, 60), 60, 0.6))
                self._text_pops.append(TextPopAnim(
                    f"\U0001f50d SOLVED! {self._seat_name(accuser)}",
                    _cx, _cy - 60, (255, 220, 50), font_size=34))
                for _ in range(6):
                    self._particles.emit_firework(
                        _cx + _rnd.randint(-120, 120), _cy + _rnd.randint(-80, 80),
                        [(255, 220, 50), (80, 220, 120), (100, 180, 255)])
            except Exception:
                pass
            # Correct: show to everyone.
            self._set_event(
                f"{self._seat_name(accuser)} wins! Case File: {self.solution_suspect} · {self.solution_weapon} · {self.solution_room}"
            )
            self._envelope_peek_allowed.add(accuser)
            return

        # ❌ Wrong accusation — red flash
        try:
            _cx, _cy = self.width // 2, self.height // 2
            self._flashes.append(ScreenFlash((180, 40, 40), 50, 0.45))
            self._text_pops.append(TextPopAnim(
                f"\u274c WRONG! {self._seat_name(accuser)}",
                _cx, _cy - 40, (255, 80, 80), font_size=30))
            self._particles.emit_sparkle(_cx, _cy, (255, 60, 60), count=20)
        except Exception:
            pass

        if accuser not in set(self.eliminated):
            self.eliminated.append(accuser)
        self._set_private_event(accuser, "Wrong accusation — you are eliminated.")
        self._envelope_peek_allowed.add(accuser)
        self._set_private_event(accuser, "Wrong accusation — you are eliminated. You may now check the Envelope.")

        # If only one player remains, they win.
        remaining = [s for s in self.active_players if s not in set(self.eliminated)]
        if len(remaining) == 1:
            self.winner = int(remaining[0])
            self._set_event(f"{self._seat_name(self.winner)} wins! (Last remaining)")
            return

        # End their turn immediately.
        self._advance_turn()

    def get_public_state(self, player_idx: int) -> Dict:
        seat = int(player_idx) if isinstance(player_idx, int) else -1
        now = time.time()

        # Private hand for this seat
        your_hand = []
        for c in (self.hands.get(seat, []) or []):
            emoji = ""
            if c.kind == "suspect":
                emoji = next((e for e, n in self.SUSPECTS if n == c.name), "")
            elif c.kind == "weapon":
                emoji = next((e for e, n in self.WEAPONS if n == c.name), "")
            elif c.kind == "room":
                emoji = next((e for e, n in self.ROOMS if n == c.name), "")
            your_hand.append({"kind": c.kind, "name": c.name, "emoji": emoji, "text": f"{emoji} {c.name}".strip()})

        hand_counts: Dict[str, int] = {}
        for s in self.active_players:
            hand_counts[str(int(s))] = int(len(self.hands.get(int(s), []) or []))

        players = []
        for s in self.active_players:
            s2 = int(s)
            kind, label = self._tile_info(self.player_pos.get(s2))
            if kind == self._TILE_ROOM and isinstance(label, str):
                loc = label
            elif kind == self._TILE_START:
                loc = "Start"
            elif kind == self._TILE_ACCUSATION:
                loc = "Accusation"
            else:
                loc = "Hallway"
            players.append({
                "seat": s2,
                "name": self._seat_name(s2),
                "eliminated": bool(s2 in set(self.eliminated)),
                "room": loc,
                "hand_count": int(len(self.hands.get(s2, []) or [])),
            })

        last_event_age_ms = int((now - float(self._last_event_time or now)) * 1000) if self._last_event else 0
        priv = self._last_private_event.get(seat, "")
        priv_age_ms = int((now - float(self._last_private_event_time.get(seat, now))) * 1000) if priv else 0

        solution_revealed = None
        # Only revealed publicly on a correct accusation (winner exists).
        if self.winner is not None and self.solution_suspect and self.solution_weapon and self.solution_room:
            solution_revealed = {
                "suspect": self.solution_suspect,
                "weapon": self.solution_weapon,
                "room": self.solution_room,
            }

        return {
            "game_id": int(self.game_id),
            "state": str(self.state),
            "active_players": list(self.active_players),
            "current_turn_seat": self._current_turn_seat(),
            "dice": [int(self.last_dice[0]), int(self.last_dice[1])] if self.last_dice else None,
            "last_roll": self.last_roll,
            "steps_remaining": int(self.steps_remaining),
            "mode": str(self._mode),
            "winner": self.winner,
            "hand_counts": hand_counts,
            "players": players,
            "your_hand": your_hand,
            "last_event": self._last_event or None,
            "last_event_age_ms": last_event_age_ms,
            "private_event": priv or None,
            "private_event_age_ms": priv_age_ms,
            "solution_revealed": solution_revealed,
        }

    def update(self, dt: float) -> None:
        if self.state != "playing":
            return

        # ── Tick animations ─────────────────────────────────────────────
        try:
            self._particles.update(dt)
            for _a in list(self._anim_card_flips): _a.update(dt)
            self._anim_card_flips = [_a for _a in self._anim_card_flips if not _a.done]
            for _a in list(self._text_pops): _a.update(dt)
            self._text_pops = [_a for _a in self._text_pops if not _a.done]
            for _a in list(self._pulse_rings): _a.update(dt)
            self._pulse_rings = [_a for _a in self._pulse_rings if not _a.done]
            for _a in list(self._flashes): _a.update(dt)
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
                self._flashes.append(ScreenFlash((255, 220, 80), 70, 1.0))
                self._text_pops.append(TextPopAnim(
                    f"🏆 {self._seat_name(self.winner)} wins!", _cx, _cy - 60,
                    (255, 220, 80), font_size=36))
                self._anim_fw_timer = 6.0
            if self._anim_fw_timer > 0:
                self._anim_fw_timer = max(0.0, self._anim_fw_timer - dt)
                if int(self._anim_fw_timer * 3) % 2 == 0:
                    _cx, _cy = self.width // 2, self.height // 2
                    self._particles.emit_firework(
                        _cx + random.randint(-150, 150), _cy + random.randint(-100, 100),
                        _FW_COLORS)
        except Exception:
            pass

        # Resolve dice animation
        if bool(self.dice_rolling):
            elapsed = time.time() - float(self.dice_roll_start or time.time())
            if elapsed >= 1.2:
                self.dice_rolling = False

                turn_seat = self._current_turn_seat()
                if turn_seat is not None and int(turn_seat) not in set(self.eliminated) and self.winner is None:
                    d1 = random.randint(1, 6)
                    d2 = random.randint(1, 6)
                    self.last_dice = (int(d1), int(d2))
                    self.last_roll = int(d1) + int(d2)
                    self.steps_remaining = int(self.last_roll)
                    self._mode = "moving" if self.steps_remaining > 0 else "in_room"
                    self._set_event(f"{self._seat_name(int(turn_seat))} rolled {d1}+{d2} = {self.last_roll}.")
                    self._dice_show_until = time.time() + 2.2
                    # ── Dice result pop-up ────────────────────────────────────
                    try:
                        _cx, _cy = self.width // 2, int(self.height * 0.35)
                        self._text_pops.append(TextPopAnim(
                            f"🎲 {d1} + {d2} = {self.last_roll}", _cx, _cy,
                            (255, 235, 120), font_size=34))
                        self._particles.emit_sparkle(_cx, _cy, (255, 235, 120))
                    except Exception:
                        pass

                self._rebuild_buttons_all()
                return

        # Keep buttons in sync (low-cost).
        self._rebuild_buttons_all()

    def _dice_preview_value(self) -> int:
        try:
            elapsed = max(0.0, time.time() - float(self.dice_roll_start or time.time()))
        except Exception:
            elapsed = 0.0
        return int((elapsed * 20) % 6) + 1

    def _dice_preview_values(self) -> Tuple[int, int]:
        try:
            elapsed = max(0.0, time.time() - float(self.dice_roll_start or time.time()))
        except Exception:
            elapsed = 0.0
        d1 = int((elapsed * 20) % 6) + 1
        d2 = int((elapsed * 17 + 2.5) % 6) + 1
        return (int(d1), int(d2))

    def draw(self) -> None:
        if self.renderer is None:
            return

        w = int(getattr(self, "width", 0) or 0)
        h = int(getattr(self, "height", 0) or 0)
        if w <= 0 or h <= 0:
            return

        # Background (match the "shapes" vibe used elsewhere)
        self.renderer.draw_rect(Colors.DARK_BG, (-4, -4, w + 8, h + 8))
        self.renderer.draw_rect(Colors.ACCENT, (-4, -4, w + 8, int(h * 0.22) + 8), alpha=10)
        self.renderer.draw_rect(Colors.WHITE, (-4, int(h * 0.78), w + 8, int(h * 0.22) + 8), alpha=5)
        self.renderer.draw_circle(Colors.ACCENT, (int(w * 0.18), int(h * 0.30)), int(min(w, h) * 0.24), alpha=8)
        self.renderer.draw_circle(Colors.ACCENT, (int(w * 0.84), int(h * 0.70)), int(min(w, h) * 0.30), alpha=6)

        # Title
        draw_rainbow_title(self.renderer, "CLUEDO", w, y=int(h * 0.04), font_size=28, char_width=22)

        # Board area (bigger + less padding)
        margin = int(min(w, h) * 0.02)
        board_w = w - 2 * margin
        # Slight top padding for header
        header_pad = int(h * 0.06)
        footer_pad = int(h * 0.12)
        board_y = margin + header_pad
        board_h = h - board_y - footer_pad - margin
        if board_h < 3 * 140:
            # Ensure we always keep a footer; shrink board gracefully.
            board_h = max(3 * 120, board_h)

        # Ensure tiles are squares.
        cell = int(min(board_w, board_h) // self.BOARD_SIZE)
        if cell <= 0:
            return
        board_px = int(cell) * int(self.BOARD_SIZE)
        board_x = int(margin + (board_w - board_px) // 2)
        board_y2 = int(board_y + (board_h - board_px) // 2)

        cell_w = cell
        cell_h = cell

        token_r = max(4, int(cell * 0.28))
        token_step = max(10, int(token_r * 2.2))

        def _cell_rect(rc: Tuple[int, int], inset: int = 2) -> Tuple[int, int, int, int]:
            rr, cc = int(rc[0]), int(rc[1])
            x = board_x + cc * cell_w
            y = board_y2 + rr * cell_h
            return (x + inset, y + inset, cell_w - 2 * inset, cell_h - 2 * inset)

        # Draw corridor grid as squares.
        for r in range(self.BOARD_SIZE):
            for c in range(self.BOARD_SIZE):
                k, lab = self._tile_info((r, c))
                if k is None:
                    continue
                rect = _cell_rect((r, c), inset=2)
                if k in (self._TILE_HALL, self._TILE_START):
                    # Shadow
                    self.renderer.draw_rect((0, 0, 0), (rect[0] + 1, rect[1] + 1, rect[2], rect[3]), alpha=40)
                    # Body
                    self.renderer.draw_rect((50, 50, 58), rect, alpha=185)
                    # Subtle top highlight
                    self.renderer.draw_rect((80, 80, 90), (rect[0], rect[1] + rect[3] - 2, rect[2], 2), alpha=40)
                    self.renderer.draw_rect((0, 0, 0), rect, width=1, alpha=50)

        # Render rooms as single blocks (one big rectangle per room).
        for room_name, (r0, r1, c0, c1) in (self._ROOM_RECTS or {}).items():
            col = self.ROOM_COLORS.get(str(room_name), (200, 200, 200))
            x = int(board_x + int(c0) * cell_w)
            y = int(board_y2 + int(r0) * cell_h)
            ww = int((int(c1) - int(c0) + 1) * cell_w)
            hh = int((int(r1) - int(r0) + 1) * cell_h)
            rect = (x + 2, y + 2, ww - 4, hh - 4)
            # Shadow
            self.renderer.draw_rect((0, 0, 0), (rect[0] + 3, rect[1] + 3, rect[2], rect[3]), alpha=60)
            # Room body
            self.renderer.draw_rect(col, rect, alpha=230)
            # Inner top highlight
            hl = tuple(min(255, c + 40) for c in col)
            self.renderer.draw_rect(hl, (rect[0] + 2, rect[1] + rect[3] - 4, rect[2] - 4, 3), alpha=60)
            # Border
            self.renderer.draw_rect((20, 20, 20), rect, width=2, alpha=140)

        # Accusation block
        for (r0, r1, c0, c1) in (self._ACCUSATION_RECTS or []):
            col = self.ROOM_COLORS.get("Accusation", (255, 236, 160))
            x = int(board_x + int(c0) * cell_w)
            y = int(board_y2 + int(r0) * cell_h)
            ww = int((int(c1) - int(c0) + 1) * cell_w)
            hh = int((int(r1) - int(r0) + 1) * cell_h)
            rect = (x + 2, y + 2, ww - 4, hh - 4)
            self.renderer.draw_rect(col, rect, alpha=240)
            self.renderer.draw_rect((0, 0, 0), rect, width=2, alpha=140)

        # Room labels/icons (draw once per room, centered)
        for room_name, (r0, r1, c0, c1) in (self._ROOM_RECTS or {}).items():
            cx = int(board_x + ((int(c0) + int(c1) + 1) * cell_w) // 2)
            cy = int(board_y2 + ((int(r0) + int(r1) + 1) * cell_h) // 2)
            emoji = next((e for e, n in self.ROOMS if n == str(room_name)), "")
            if emoji:
                try:
                    self.renderer.draw_text(
                        emoji,
                        int(cx),
                        int(cy) - int(cell_h * 1.0),
                        font_name="Segoe UI Emoji",
                        font_size=max(18, int(cell * 1.2)),
                        color=(255, 255, 255),
                        anchor_x="center",
                        anchor_y="center",
                    )
                except Exception:
                    pass
            self.renderer.draw_text(
                str(room_name),
                int(cx),
                int(cy) + int(cell_h * 0.6),
                font_size=max(12, int(cell * 0.55)),
                color=(20, 20, 20),
                anchor_x="center",
                anchor_y="center",
                bold=True,
            )

        # Accusation label/icon
        for (r0, r1, c0, c1) in (self._ACCUSATION_RECTS or []):
            cx = int(board_x + ((int(c0) + int(c1) + 1) * cell_w) // 2)
            cy = int(board_y2 + ((int(r0) + int(r1) + 1) * cell_h) // 2)
            self.renderer.draw_text(
                "⚖️",
                int(cx),
                int(cy) - int(cell_h * 0.6),
                font_name="Segoe UI Emoji",
                font_size=max(18, int(cell * 1.2)),
                color=(255, 255, 255),
                anchor_x="center",
                anchor_y="center",
            )
            self.renderer.draw_text(
                "Accusation",
                int(cx),
                int(cy) + int(cell_h * 0.6),
                font_size=max(12, int(cell * 0.50)),
                color=(20, 20, 20),
                anchor_x="center",
                anchor_y="center",
                bold=True,
            )

        # Door arrows (show entrances)
        for (dr, dc), (arrow, room_name) in (self._doors or {}).items():
            rect = _cell_rect((dr, dc), inset=2)
            cx = rect[0] + rect[2] // 2
            cy = rect[1] + rect[3] // 2
            self.renderer.draw_text(
                str(arrow),
                int(cx),
                int(cy),
                font_size=max(12, int(cell * 0.70)),
                color=Colors.ACCENT,
                anchor_x="center",
                anchor_y="center",
                bold=True,
            )

        # Outside start pads (drawn just outside the board)
        for (sr, sc) in (self._OUTSIDE_STARTS or []):
            # Only render if it lands in visible area
            x0 = board_x + sc * cell_w
            y0 = board_y2 + sr * cell_h
            rect = (int(x0) + 6, int(y0) + 6, int(cell_w) - 12, int(cell_h) - 12)
            # Skip if completely off-screen
            if rect[0] + rect[2] < -20 or rect[1] + rect[3] < -20 or rect[0] > (w + 20) or rect[1] > (h + 20):
                continue
            self.renderer.draw_rect((45, 45, 55), rect, alpha=180)
            self.renderer.draw_rect(Colors.ACCENT, rect, width=3, alpha=150)
            self.renderer.draw_text(
                "START",
                int(rect[0] + rect[2] // 2),
                int(rect[1] + rect[3] // 2),
                font_size=max(10, int(cell * 0.45)),
                color=(240, 240, 240),
                anchor_x="center",
                anchor_y="center",
                bold=True,
            )

        # Tokens (per-tile; stacks inside same cell)
        ap = list(self.active_players)
        by_pos: Dict[Tuple[int, int], List[int]] = {}
        for s in ap:
            seat = int(s)
            pos = self.player_pos.get(seat)
            if pos is None:
                continue
            by_pos.setdefault((int(pos[0]), int(pos[1])), []).append(seat)

        for pos, seats in by_pos.items():
            r, c = int(pos[0]), int(pos[1])
            x0 = board_x + c * cell_w
            y0 = board_y2 + r * cell_h

            # Outside starts are outside the in-bounds grid; keep them aligned with the board edge.
            if r == -1:
                y0 = board_y2 - cell_h
            elif r == self.BOARD_SIZE:
                y0 = board_y2 + self.BOARD_SIZE * cell_h
            if c == -1:
                x0 = board_x - cell_w
            elif c == self.BOARD_SIZE:
                x0 = board_x + self.BOARD_SIZE * cell_w

            seats_sorted = list(seats)
            try:
                seats_sorted.sort()
            except Exception:
                pass

            for j, seat in enumerate(seats_sorted):
                # Stack from top-left downward (pygame-style Y).
                cx = x0 + max(token_r + 4, int(cell_w * 0.30))
                cy = y0 + max(token_r + 6, int(cell_h * 0.34)) + j * token_step
                if cy > (y0 + cell_h - (token_r + 6)):
                    cy = y0 + cell_h - (token_r + 6)

                color = PLAYER_COLORS[seat % len(PLAYER_COLORS)]
                alpha = 255 if seat not in set(self.eliminated) else 90
                # Shadow
                self.renderer.draw_circle((0, 0, 0), (int(cx) + 2, int(cy) + 2), int(token_r * 1.2), alpha=max(40, alpha - 120))
                # Token body
                self.renderer.draw_circle(color, (int(cx), int(cy)), int(token_r), alpha=alpha)
                # Highlight dot
                hl = tuple(min(255, c + 80) for c in color)
                self.renderer.draw_circle(hl, (int(cx) - 2, int(cy) - 2), max(2, int(token_r * 0.3)), alpha=min(alpha, 90))
                # Outline
                self.renderer.draw_circle((0, 0, 0), (int(cx), int(cy)), int(token_r), width=1, alpha=max(60, alpha - 60))

                if self._current_turn_seat() == seat and self.winner is None:
                    self.renderer.draw_circle(Colors.GOLD, (int(cx), int(cy)), int(token_r * 1.8), width=0, alpha=50)
                    self.renderer.draw_circle(Colors.GOLD, (int(cx), int(cy)), int(token_r * 1.8), width=2, alpha=80)

        # Footer panel (reserve space so it never overlaps rooms)
        footer_y = h - footer_pad + 8
        fp_rect = (margin, footer_y, w - 2 * margin, footer_pad - 16)
        # Shadow
        self.renderer.draw_rect((0, 0, 0), (fp_rect[0] + 3, fp_rect[1] + 3, fp_rect[2], fp_rect[3]), alpha=70)
        # Body
        self.renderer.draw_rect((12, 12, 18), fp_rect, alpha=190)
        # Inner accent
        self.renderer.draw_rect((30, 20, 40), (fp_rect[0] + 3, fp_rect[1] + 3, fp_rect[2] - 6, fp_rect[3] - 6), alpha=40)
        # Gold border
        self.renderer.draw_rect((180, 150, 80), fp_rect, width=2, alpha=120)

        # Dice in footer-left (keep result visible briefly after rolling)
        show_dice = bool(self.dice_rolling) or (self.last_roll is not None and time.time() < float(self._dice_show_until or 0.0))
        if show_dice and self.winner is None:
            if bool(self.dice_rolling):
                d1, d2 = self._dice_preview_values()
            else:
                d1, d2 = (int(self.last_dice[0]), int(self.last_dice[1])) if self.last_dice else (int(self.last_roll or 0), 0)
            dx = margin + 18
            dy = footer_y + int((footer_pad - 16) * 0.44)
            self.renderer.draw_text(
                f"🎲 {d1}  🎲 {d2}",
                int(dx) + 2,
                int(dy) + 2,
                font_name="Segoe UI Emoji",
                font_size=28,
                color=(0, 0, 0),
                anchor_x="left",
                anchor_y="center",
                alpha=140,
            )
            self.renderer.draw_text(
                f"🎲 {d1}  🎲 {d2}",
                int(dx),
                int(dy),
                font_name="Segoe UI Emoji",
                font_size=28,
                color=(255, 255, 255),
                anchor_x="left",
                anchor_y="center",
            )

        # Footer info
        turn_seat = self._current_turn_seat()
        if turn_seat is not None:
            tname = self._seat_name(turn_seat)
        else:
            tname = "—"
        info = f"Turn: {tname}"
        if bool(self.dice_rolling):
            info += "  ·  Rolling…"
        elif self.last_roll is not None:
            if self.last_dice is not None:
                info += f"  ·  Roll: {int(self.last_dice[0])}+{int(self.last_dice[1])}={self.last_roll}  ·  Steps: {self.steps_remaining}"
            else:
                info += f"  ·  Roll: {self.last_roll}  ·  Steps: {self.steps_remaining}"
        if self.winner is not None:
            info = f"\U0001F3C6 Winner: {self._seat_name(self.winner)} \U0001F3C6"

        self.renderer.draw_text(
            info,
            int(w * 0.5),
            footer_y + int((footer_pad - 16) * 0.38),
            font_size=18,
            color=(255, 230, 140) if self.winner is not None else (235, 235, 235),
            anchor_x="center",
            anchor_y="center",
            bold=True,
        )

        # Last event
        if self._last_event:
            self.renderer.draw_text(
                self._last_event,
                int(w * 0.5),
                footer_y + int((footer_pad - 16) * 0.72),
                font_size=14,
                color=(200, 200, 200),
                anchor_x="center",
                anchor_y="center",
            )

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
