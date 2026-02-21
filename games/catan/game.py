from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from core.player_selection import PlayerSelectionUI
from core.animation import (
    ParticleSystem, CardFlyAnim, TextPopAnim, PulseRing, ScreenFlash,
    _RAINBOW_PALETTE as _FW_COLORS, draw_rainbow_title,
)


class _WebButton:
    def __init__(self, text: str, enabled: bool = True):
        self.text = text
        self.enabled = enabled


@dataclass(frozen=True)
class HexTile:
    q: int
    r: int
    kind: str  # wood|brick|sheep|wheat|ore|desert|water|gold|volcano
    number: Optional[int]  # 2..12 excluding 7; None for water/desert/volcano


@dataclass(frozen=True)
class Port:
    q: int
    r: int
    kind: str  # any|wood|brick|sheep|wheat|ore


_RESOURCE = ["wood", "brick", "sheep", "wheat", "ore"]
_KIND_EMOJI = {
    "wood": "🌲",
    "brick": "🧱",
    "sheep": "🐑",
    "wheat": "🌾",
    "ore": "⛰️",
    "desert": "🏜️",
    "water": "🌊",
    "gold": "🪙",
    "volcano": "🌋",
}
_KIND_COLOR = {
    "wood": (72, 150, 72),
    "brick": (170, 90, 70),
    "sheep": (120, 190, 110),
    "wheat": (200, 180, 90),
    "ore": (110, 110, 130),
    "desert": (200, 170, 120),
    "water": (70, 120, 200),
    "gold": (200, 175, 70),
    "volcano": (140, 70, 70),
}

_PORT_EMOJI = {
    "any": "⚓",
    "wood": "🌲⚓",
    "brick": "🧱⚓",
    "sheep": "🐑⚓",
    "wheat": "🌾⚓",
    "ore": "⛰️⚓",
}


@dataclass(frozen=True)
class ExpansionConfig:
    name: str
    radius: int
    water_ring: bool
    island_count: int
    island_radius: int
    ports: int
    extra_water_prob: float
    gold_tiles: int
    volcano_tiles: int


def _clamp_int(v: int, lo: int, hi: int) -> int:
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


def _axial_hexes(radius: int) -> List[Tuple[int, int]]:
    out: List[Tuple[int, int]] = []
    r = int(radius)
    for q in range(-r, r + 1):
        r1 = max(-r, -q - r)
        r2 = min(r, -q + r)
        for rr in range(r1, r2 + 1):
            out.append((int(q), int(rr)))
    return out


def _axial_dist(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    aq, ar = a
    bq, br = b
    # cube coords (q, r, s=-q-r)
    return int((abs(aq - bq) + abs(ar - br) + abs((-aq - ar) - (-bq - br))) // 2)


class CatanGame:
    """Catan (visual MVP).

    Goals for this first pass:
    - Add a scalable hex map (2..8 players) with emoji resource tiles.
    - Render it on the Pyglet wall display.
    - Provide minimal turn loop + buttons for the Web UI.

    This intentionally does NOT implement full Catan building/trading rules yet.
    """

    def __init__(self, width: int, height: int, renderer=None):
        self.width = int(width)
        self.height = int(height)
        self.renderer = renderer

        self.state = "player_select"  # player_select|playing
        self.selection_ui = PlayerSelectionUI(width, height)

        self.active_players: List[int] = []
        self.current_turn_seat: Optional[int] = None

        self.phase: str = "player_select"  # player_select|initial_settlement|initial_road|main|discard|robber_move|robber_steal|trade_bank|trade_player_*
        self._initial_order: List[int] = []
        self._initial_step: int = 0
        self._initial_last_settlement_vertex: Optional[int] = None

        self._rolled_this_turn: bool = False

        self._turn_number: int = 0

        # Robber / 7 handling
        self.robber_tile_idx: Optional[int] = None
        self._robber_pending_tile_idx: Optional[int] = None
        self._robber_candidates: List[int] = []

        # Multi-player discard selection (7)
        self._discard_need: Dict[int, int] = {}
        self._discard_remaining: Dict[int, int] = {}

        self.expansion_mode: str = "base"  # base|extended|seafarers|mega
        self.tiles: List[HexTile] = []
        self.ports: List[Port] = []
        self._map_radius: int = 3

        # Graph + builds
        self._vertices: List[Dict] = []  # {id,x,y,adj_tiles:[tile_idx],nbrs:[vid]}
        self._edges: List[Dict] = []  # {id,a,b}
        self._vertex_by_key: Dict[Tuple[int, int], int] = {}
        self._edge_by_key: Dict[Tuple[int, int], int] = {}

        # vertex_id -> {owner:int, kind:'settlement'|'city'}
        self._buildings: Dict[int, Dict] = {}
        # edge_id -> owner seat
        self._roads: Dict[int, int] = {}

        # player -> resource counts
        self._res: Dict[int, Dict[str, int]] = {i: {k: 0 for k in _RESOURCE} for i in range(8)}

        # Bank (classic base game: 19 of each resource)
        self._bank: Dict[str, int] = {k: 19 for k in _RESOURCE}

        # Dev cards
        self._dev_deck: List[str] = []
        self._dev_hand: Dict[int, Dict[str, int]] = {i: {} for i in range(8)}
        self._dev_bought_turn: Dict[int, int] = {i: -999 for i in range(8)}
        self._knights_played: Dict[int, int] = {i: 0 for i in range(8)}

        # Awards
        self._largest_army_holder: Optional[int] = None
        self._longest_road_holder: Optional[int] = None

        # Bank trade selection
        self._trade_give: Optional[str] = None
        self._trade_get: Optional[str] = None

        # Dev-action transient state
        self._free_roads_left: int = 0
        self._yop_left: int = 0
        self._monopoly_pending: bool = False
        self._dev_played_this_turn: bool = False

        self.winner: Optional[int] = None

        self._pending_build: Optional[str] = None  # 'settlement'|'road'|'city'

        self.last_event: str = ""
        self.last_roll: Optional[int] = None
        self._last_dice: Optional[Tuple[int, int]] = None
        self._last_roll_time: float = 0.0

        # Monopoly-style dice animation
        self.dice_rolling: bool = False
        self._dice_roll_start: float = 0.0
        self._pending_dice: Optional[Tuple[int, int]] = None
        self._pending_roll_seat: Optional[int] = None
        self._dice_roll_duration: float = 1.2

        # Player-to-player trade (simple 1-for-1 offers)
        self._p2p_offer: Optional[Dict[str, object]] = None
        self._p2p_give: Optional[str] = None
        self._p2p_get: Optional[str] = None

        self.buttons: Dict[int, Dict[str, _WebButton]] = {i: {} for i in range(8)}

        # Optional: server can provide human-friendly player names.
        self.player_names: Dict[int, str] = {}

        # Map layout cache
        self._hex_size: float = 28.0
        self._map_center: Tuple[int, int] = (self.width // 2, self.height // 2)
        self._draw_off_x: float = 0.0
        self._draw_off_y: float = 0.0
        self._draw_size: float = 28.0

        # Compatibility with server flags
        self.web_ui_only_player_select = True
        self.board_only_mode = True

        # ── Particle animations ─────────────────────────────────────────
        self._particles = ParticleSystem()
        self._anim_card_flips: list = []
        self._text_pops: list = []
        self._pulse_rings: list = []
        self._flashes: list = []
        self._anim_prev_winner: object = None
        self._anim_fw_timer: float = 0.0
        self._anim_prev_turn: object = None

    def _seat_label(self, seat: int) -> str:
        try:
            name = (self.player_names or {}).get(int(seat))
            name = str(name or '').strip()
            if name:
                return name
        except Exception:
            pass
        return f"Player {int(seat) + 1}"

    def _is_my_turn(self, seat: int) -> bool:
        return isinstance(self.current_turn_seat, int) and int(seat) == int(self.current_turn_seat)

    def start_game(self, selected_indices: List[int]) -> None:
        seats = [int(i) for i in selected_indices if isinstance(i, int) or str(i).isdigit()]
        seats = [s for s in seats if 0 <= s <= 7]
        seats = sorted(dict.fromkeys(seats))
        if len(seats) < 2:
            return

        self.active_players = seats
        self.current_turn_seat = int(seats[0])

        n = len(seats)
        self.expansion_mode = self._expansion_for_player_count(n)
        self.tiles, self.ports, self._map_radius = self._generate_map(n)

        self._build_graph()
        self._buildings.clear()
        self._roads.clear()
        for s in self.active_players:
            self._res[s] = {k: 0 for k in _RESOURCE}

        self._bank = {k: 19 for k in _RESOURCE}
        self._turn_number = 0
        self._discard_need = {}
        self._discard_remaining = {}

        self._dev_hand = {i: {} for i in range(8)}
        self._dev_bought_turn = {i: -999 for i in range(8)}
        self._knights_played = {i: 0 for i in range(8)}
        self._largest_army_holder = None
        self._longest_road_holder = None
        self._init_dev_deck()

        self._trade_give = None
        self._trade_get = None
        self._free_roads_left = 0
        self._yop_left = 0
        self._monopoly_pending = False
        self._dev_played_this_turn = False

        self.winner = None

        # Robber starts on desert if present, else None.
        self.robber_tile_idx = None
        try:
            for ti, t in enumerate(self.tiles or []):
                if str(t.kind) == "desert":
                    self.robber_tile_idx = int(ti)
                    break
        except Exception:
            self.robber_tile_idx = None
        self._robber_pending_tile_idx = None
        self._robber_candidates = []

        # Initial placement: snake draft, each player places 2 settlements + 2 roads.
        order1 = list(self.active_players)
        order2 = list(reversed(self.active_players))
        self._initial_order = order1 + order2
        self._initial_step = 0
        self.current_turn_seat = int(self._initial_order[0])
        self.phase = "initial_settlement"
        self._initial_last_settlement_vertex = None
        self._rolled_this_turn = False
        self._pending_build = None

        self.state = "playing"
        self.last_event = f"Catan started ({n} players, {self.expansion_mode})"
        self.last_roll = None
        self._last_roll_time = 0.0

        self.dice_rolling = False
        self._dice_roll_start = 0.0
        self._pending_dice = None
        self._pending_roll_seat = None
        self._p2p_offer = None
        self._p2p_give = None
        self._p2p_get = None
        self._refresh_buttons()

    # --- Graph building ---

    def _tile_resource(self, kind: str) -> Optional[str]:
        k = str(kind)
        if k in _RESOURCE:
            return k
        if k == "gold":
            # gold yields "any"; handled specially
            return "gold"
        return None

    def _hex_corner_offsets(self) -> List[Tuple[float, float]]:
        # pointy-top corners relative to center for size=1
        out: List[Tuple[float, float]] = []
        for i in range(6):
            ang = math.radians(60 * i - 30)
            out.append((math.cos(ang), math.sin(ang)))
        return out

    def _vkey(self, x: float, y: float) -> Tuple[int, int]:
        # Quantize to stable integer key.
        return (int(round(x * 10000)), int(round(y * 10000)))

    def _build_graph(self) -> None:
        self._vertices = []
        self._edges = []
        self._vertex_by_key = {}
        self._edge_by_key = {}

        tiles = list(self.tiles or [])
        # Use logical size = 1.0 for graph geometry.
        corner = self._hex_corner_offsets()

        for ti, t in enumerate(tiles):
            if str(t.kind) == "water":
                continue
            cx, cy = self._axial_to_pixel(int(t.q), int(t.r), 1.0)
            vids: List[int] = []
            for (ox, oy) in corner:
                vx = float(cx + ox)
                vy = float(cy + oy)
                key = self._vkey(vx, vy)
                vid = self._vertex_by_key.get(key)
                if vid is None:
                    vid = len(self._vertices)
                    self._vertex_by_key[key] = vid
                    self._vertices.append({"id": vid, "x": vx, "y": vy, "adj_tiles": [], "nbrs": []})
                self._vertices[vid]["adj_tiles"].append(int(ti))
                vids.append(int(vid))

            # Edges around hex
            for i in range(6):
                a = vids[i]
                b = vids[(i + 1) % 6]
                ka, kb = (a, b) if a < b else (b, a)
                ekey = (int(ka), int(kb))
                eid = self._edge_by_key.get(ekey)
                if eid is None:
                    eid = len(self._edges)
                    self._edge_by_key[ekey] = eid
                    self._edges.append({"id": eid, "a": int(ka), "b": int(kb)})
                    # adjacency
                    self._vertices[ka]["nbrs"].append(int(kb))
                    self._vertices[kb]["nbrs"].append(int(ka))

        # Dedup neighbor lists
        for v in self._vertices:
            try:
                v["nbrs"] = sorted(dict.fromkeys(v.get("nbrs") or []))
                v["adj_tiles"] = sorted(dict.fromkeys(v.get("adj_tiles") or []))
            except Exception:
                pass

    def _expansion_for_player_count(self, n: int) -> str:
        n = int(n)
        if n <= 4:
            return "base" if n <= 3 else "extended"
        if n <= 6:
            return "seafarers"
        return "mega"

    def _config_for(self, n_players: int) -> ExpansionConfig:
        # "As big as possible" within reason: keep it performant on the wall display.
        n = int(n_players)
        mode = str(self.expansion_mode)
        if mode == "base":
            return ExpansionConfig(
                name="base",
                radius=4,
                # Always keep an ocean border so the island reads clearly.
                water_ring=True,
                island_count=0,
                island_radius=0,
                ports=8,
                extra_water_prob=0.0,
                gold_tiles=0,
                volcano_tiles=0,
            )
        if mode == "extended":
            return ExpansionConfig(
                name="extended",
                radius=5,
                # Always keep an ocean border so the island reads clearly.
                water_ring=True,
                island_count=0,
                island_radius=0,
                ports=10,
                extra_water_prob=0.03,
                gold_tiles=1,
                volcano_tiles=0,
            )
        if mode == "seafarers":
            # Big main island + 1-2 extra islands inside the water ring.
            return ExpansionConfig(
                name="seafarers",
                radius=5 if n >= 6 else 4,
                water_ring=True,
                island_count=2 if n >= 5 else 1,
                island_radius=2,
                ports=10,
                extra_water_prob=0.06,
                gold_tiles=2,
                volcano_tiles=0,
            )
        # mega
        return ExpansionConfig(
            name="mega",
            radius=6 if n >= 8 else 5,
            water_ring=True,
            island_count=3,
            island_radius=2,
            ports=12,
            extra_water_prob=0.09,
            gold_tiles=3,
            volcano_tiles=1,
        )

    def _rng_for_map(self, n_players: int) -> random.Random:
        # Stable-ish per session but different between runs.
        seed = int(time.time() * 1000) ^ (n_players * 0x9E3779B1)
        return random.Random(seed)

    def _pick_island_centers(self, rng: random.Random, radius: int, count: int) -> List[Tuple[int, int]]:
        centers: List[Tuple[int, int]] = []
        tries = 0
        while len(centers) < count and tries < 500:
            tries += 1
            q = rng.randint(-(radius - 2), radius - 2)
            r = rng.randint(-(radius - 2), radius - 2)
            if _axial_dist((q, r), (0, 0)) > max(2, radius - 2):
                continue
            if any(_axial_dist((q, r), c) <= 2 for c in centers):
                continue
            centers.append((q, r))
        return centers

    def _generate_map(self, n_players: int) -> Tuple[List[HexTile], List[Port], int]:
        cfg = self._config_for(n_players)
        rng = self._rng_for_map(n_players)
        radius = int(cfg.radius)

        all_coords = _axial_hexes(radius)

        # Start with everything as water for seafarers/mega; otherwise all land.
        land: set[Tuple[int, int]] = set()
        water: set[Tuple[int, int]] = set()
        if cfg.water_ring:
            for (q, r) in all_coords:
                d = _axial_dist((q, r), (0, 0))
                if d >= radius:
                    water.add((q, r))
                else:
                    land.add((q, r))
        else:
            land = set(all_coords)

        # If we have a water ring, carve extra water pockets and sprinkle islands.
        if cfg.water_ring:
            # Add extra water pockets near the outer ring.
            for (q, r) in list(land):
                d = _axial_dist((q, r), (0, 0))
                if d >= max(2, radius - 2) and rng.random() < float(cfg.extra_water_prob):
                    land.discard((q, r))
                    water.add((q, r))

            # Add a few islands in the sea (keep them away from the center).
            centers = self._pick_island_centers(rng, radius, int(cfg.island_count))
            for (cq, cr) in centers:
                for (q, r) in all_coords:
                    if _axial_dist((q, r), (cq, cr)) <= int(cfg.island_radius):
                        # Only place islands where it's currently water.
                        if (q, r) in water and _axial_dist((q, r), (0, 0)) >= 2:
                            water.discard((q, r))
                            land.add((q, r))

        # Assign land kinds.
        land_coords = list(land)
        rng.shuffle(land_coords)

        land_kinds: List[str] = []
        for _ in range(len(land_coords)):
            land_kinds.append(rng.choice(_RESOURCE))

        # Special tiles.
        if land_kinds:
            land_kinds[0] = "desert"

        # Add gold + volcano as configured.
        for _ in range(int(cfg.gold_tiles)):
            if len(land_kinds) >= 6:
                land_kinds[rng.randrange(0, len(land_kinds))] = "gold"
        for _ in range(int(cfg.volcano_tiles)):
            if len(land_kinds) >= 10:
                land_kinds[rng.randrange(0, len(land_kinds))] = "volcano"

        # Token numbers: scale pool with number of land tiles.
        base_numbers = [2, 3, 3, 4, 4, 5, 5, 6, 6, 8, 8, 9, 9, 10, 10, 11, 11, 12]
        numbers_pool: List[int] = []
        while len(numbers_pool) < max(0, len(land_coords) - 1):
            numbers_pool.extend(base_numbers)
        rng.shuffle(numbers_pool)

        tiles: List[HexTile] = []
        desert_assigned = False
        for (q, r), kind in zip(land_coords, land_kinds):
            num: Optional[int] = None
            kind = str(kind)
            if kind == "desert":
                desert_assigned = True
            if kind in ("wood", "brick", "sheep", "wheat", "ore", "gold"):
                if numbers_pool:
                    num = int(numbers_pool.pop())
            tiles.append(HexTile(int(q), int(r), kind, num))

        if tiles and not desert_assigned:
            # Safety: force one desert.
            t0 = tiles[0]
            tiles[0] = HexTile(int(t0.q), int(t0.r), "desert", None)

        for (q, r) in sorted(water):
            tiles.append(HexTile(int(q), int(r), "water", None))

        ports = self._generate_ports(rng, tiles, want=int(cfg.ports))
        return tiles, ports, radius

    def _generate_ports(self, rng: random.Random, tiles: List[HexTile], want: int) -> List[Port]:
        # Ports are assigned to some coastal water hexes adjacent to land.
        if want <= 0:
            return []

        land = {(t.q, t.r) for t in tiles if t.kind != "water"}
        water = {(t.q, t.r) for t in tiles if t.kind == "water"}

        neighbors = [(+1, 0), (+1, -1), (0, -1), (-1, 0), (-1, +1), (0, +1)]
        coastal_water: List[Tuple[int, int]] = []
        for (q, r) in water:
            for dq, dr in neighbors:
                if (q + dq, r + dr) in land:
                    coastal_water.append((q, r))
                    break

        rng.shuffle(coastal_water)
        coastal_water = coastal_water[: max(0, min(len(coastal_water), want))]

        port_kinds = ["any", "any", "any", "wood", "brick", "sheep", "wheat", "ore"]
        out: List[Port] = []
        for i, (q, r) in enumerate(coastal_water):
            kind = rng.choice(port_kinds)
            out.append(Port(int(q), int(r), str(kind)))
        return out

    def handle_click(self, player_idx: int, btn_id: str) -> None:
        if self.state != "playing":
            return
        if not isinstance(player_idx, int):
            return
        if player_idx not in self.active_players:
            return

        if isinstance(self.winner, int):
            return

        # Lock inputs while dice animation is running.
        if bool(self.dice_rolling):
            return

        # Discard selection (7): affected players discard via buttons even when it's not their turn.
        if self.phase == "discard":
            if isinstance(btn_id, str) and btn_id.startswith("discard:"):
                res = str(btn_id.split(":", 1)[1]) if ":" in str(btn_id) else ""
                if res not in _RESOURCE:
                    return
                if int(self._discard_remaining.get(int(player_idx), 0)) <= 0:
                    return
                if int(self._res[int(player_idx)].get(res, 0)) <= 0:
                    return
                self._res[int(player_idx)][res] = int(self._res[int(player_idx)].get(res, 0)) - 1
                self._bank[res] = int(self._bank.get(res, 0)) + 1
                self._discard_remaining[int(player_idx)] = int(self._discard_remaining.get(int(player_idx), 0)) - 1
                if all(int(v) <= 0 for v in (self._discard_remaining or {}).values()):
                    self.phase = "robber_move"
                    self.last_event = f"Discards complete. {self._seat_label(int(self.current_turn_seat))}: move the robber (tap a land tile)."
                self._refresh_buttons()
                return

            # Ignore other buttons while discarding.
            self._refresh_buttons()
            return

        if btn_id == "roll":
            if not self._is_my_turn(player_idx):
                return
            if self.phase != "main":
                return
            if self._rolled_this_turn:
                return
            a = random.randint(1, 6)
            b = random.randint(1, 6)
            self._pending_dice = (int(a), int(b))
            self._pending_roll_seat = int(player_idx)
            self.dice_rolling = True
            self._dice_roll_start = float(time.time())
            self.last_event = f"{self._seat_label(player_idx)} is rolling…"
        elif btn_id == "end_turn":
            if not self._is_my_turn(player_idx):
                return
            if self.phase.startswith("initial_"):
                return
            if self.phase != "main":
                return
            alive = list(self.active_players)
            if not alive:
                return
            i = alive.index(int(player_idx))
            self.current_turn_seat = int(alive[(i + 1) % len(alive)])
            self.last_event = f"Turn: {self._seat_label(int(self.current_turn_seat))}"
            self._rolled_this_turn = False
            self._pending_build = None
            self._robber_pending_tile_idx = None
            self._robber_candidates = []

            self._trade_give = None
            self._trade_get = None
            self._p2p_offer = None
            self._p2p_give = None
            self._p2p_get = None
            self._free_roads_left = 0
            self._yop_left = 0
            self._monopoly_pending = False
            self._dev_played_this_turn = False
            self._turn_number += 1
        elif btn_id == "build_settlement":
            if not self._is_my_turn(player_idx) or self.phase != "main" or not self._rolled_this_turn:
                return
            if not self._can_afford(player_idx, {"wood": 1, "brick": 1, "sheep": 1, "wheat": 1}):
                return
            self._pending_build = "settlement"
            self.last_event = f"{self._seat_label(player_idx)}: tap a vertex for a settlement"
        elif btn_id == "build_road":
            if not self._is_my_turn(player_idx) or self.phase != "main" or not self._rolled_this_turn:
                return
            if self._free_roads_left <= 0 and not self._can_afford(player_idx, {"wood": 1, "brick": 1}):
                return
            self._pending_build = "road"
            self.last_event = f"{self._seat_label(player_idx)}: tap an edge for a road"
        elif btn_id == "build_city":
            if not self._is_my_turn(player_idx) or self.phase != "main" or not self._rolled_this_turn:
                return
            if not self._can_afford(player_idx, {"ore": 3, "wheat": 2}):
                return
            self._pending_build = "city"
            self.last_event = f"{self._seat_label(player_idx)}: tap your settlement to upgrade"
        elif btn_id == "cancel_build":
            if not self._is_my_turn(player_idx):
                return
            self._pending_build = None
            self._free_roads_left = 0

        elif btn_id == "trade_bank":
            if not self._is_my_turn(player_idx) or self.phase != "main" or not self._rolled_this_turn or self._pending_build is not None:
                return
            self.phase = "trade_bank"
            self._trade_give = self._trade_give or "wood"
            self._trade_get = self._trade_get or "brick"
            self.last_event = f"{self._seat_label(player_idx)}: bank trade"
        elif btn_id == "trade_player":
            if not self._is_my_turn(player_idx) or self.phase != "main" or not self._rolled_this_turn or self._pending_build is not None:
                return
            self.phase = "trade_player_select"
            self._p2p_give = self._p2p_give or "wood"
            self._p2p_get = self._p2p_get or "brick"
            self._p2p_offer = None
            self.last_event = f"{self._seat_label(player_idx)}: pick a trade partner"
        elif btn_id == "trade_cancel":
            if not self._is_my_turn(player_idx):
                return
            if self.phase == "trade_bank":
                self.phase = "main"
            if self.phase.startswith("trade_player"):
                self.phase = "main"
                self._p2p_offer = None
            self._trade_give = None
            self._trade_get = None
            self._p2p_give = None
            self._p2p_get = None
        elif isinstance(btn_id, str) and btn_id.startswith("trade_to:"):
            if not self._is_my_turn(player_idx) or self.phase != "trade_player_select":
                return
            try:
                to_seat = int(str(btn_id.split(":", 1)[1]))
            except Exception:
                return
            if to_seat == int(player_idx) or to_seat not in (self.active_players or []):
                return
            self.phase = "trade_player_offer"
            self._p2p_offer = {"from": int(player_idx), "to": int(to_seat)}
            self.last_event = f"{self._seat_label(player_idx)}: offering trade to {self._seat_label(int(to_seat))}"
        elif isinstance(btn_id, str) and btn_id.startswith("p2p_give:"):
            if not self._is_my_turn(player_idx) or self.phase != "trade_player_offer":
                return
            res = str(btn_id.split(":", 1)[1])
            if res in _RESOURCE:
                self._p2p_give = res
        elif isinstance(btn_id, str) and btn_id.startswith("p2p_get:"):
            if not self._is_my_turn(player_idx) or self.phase != "trade_player_offer":
                return
            res = str(btn_id.split(":", 1)[1])
            if res in _RESOURCE:
                self._p2p_get = res
        elif btn_id == "p2p_offer":
            if not self._is_my_turn(player_idx) or self.phase != "trade_player_offer":
                return
            if not isinstance(self._p2p_offer, dict):
                return
            try:
                to_seat = int(self._p2p_offer.get("to"))  # type: ignore[arg-type]
            except Exception:
                return
            give = str(self._p2p_give or "")
            get = str(self._p2p_get or "")
            if give not in _RESOURCE or get not in _RESOURCE or give == get:
                return
            if int((self._res.get(int(player_idx)) or {}).get(give, 0)) <= 0:
                return
            self._p2p_offer = {"from": int(player_idx), "to": int(to_seat), "give": give, "get": get}
            self.phase = "trade_player_wait"
            self.last_event = f"Trade offer sent to {self._seat_label(int(to_seat))}: you give 1 {give} for 1 {get}"
        elif btn_id == "p2p_accept":
            if not isinstance(self._p2p_offer, dict) or not self.phase.startswith("trade_player"):
                return
            try:
                frm = int(self._p2p_offer.get("from"))  # type: ignore[arg-type]
                to = int(self._p2p_offer.get("to"))  # type: ignore[arg-type]
                give = str(self._p2p_offer.get("give"))
                get = str(self._p2p_offer.get("get"))
            except Exception:
                return
            if int(player_idx) != int(to):
                return
            if give not in _RESOURCE or get not in _RESOURCE:
                return
            if int((self._res.get(int(frm)) or {}).get(give, 0)) <= 0:
                return
            if int((self._res.get(int(to)) or {}).get(get, 0)) <= 0:
                return
            self._res[int(frm)][give] = int(self._res[int(frm)].get(give, 0)) - 1
            self._res[int(to)][give] = int(self._res[int(to)].get(give, 0)) + 1
            self._res[int(to)][get] = int(self._res[int(to)].get(get, 0)) - 1
            self._res[int(frm)][get] = int(self._res[int(frm)].get(get, 0)) + 1
            self.last_event = f"Trade completed: {self._seat_label(int(frm))} gave 1 {give} for 1 {get} from {self._seat_label(int(to))}"
            self._p2p_offer = None
            self._p2p_give = None
            self._p2p_get = None
            self.phase = "main"
        elif btn_id == "p2p_decline":
            if not isinstance(self._p2p_offer, dict) or not self.phase.startswith("trade_player"):
                return
            try:
                to = int(self._p2p_offer.get("to"))  # type: ignore[arg-type]
                frm = int(self._p2p_offer.get("from"))  # type: ignore[arg-type]
            except Exception:
                return
            if int(player_idx) != int(to):
                return
            self.last_event = f"{self._seat_label(int(to))} declined trade offer from {self._seat_label(int(frm))}"
            self._p2p_offer = None
            self._p2p_give = None
            self._p2p_get = None
            self.phase = "main"
        elif isinstance(btn_id, str) and btn_id.startswith("trade_give:"):
            if not self._is_my_turn(player_idx) or self.phase != "trade_bank":
                return
            res = str(btn_id.split(":", 1)[1])
            if res in _RESOURCE:
                self._trade_give = res
        elif isinstance(btn_id, str) and btn_id.startswith("trade_get:"):
            if not self._is_my_turn(player_idx) or self.phase != "trade_bank":
                return
            res = str(btn_id.split(":", 1)[1])
            if res in _RESOURCE:
                self._trade_get = res
        elif btn_id == "trade_confirm":
            if not self._is_my_turn(player_idx) or self.phase != "trade_bank":
                return
            if (self._trade_give not in _RESOURCE) or (self._trade_get not in _RESOURCE):
                return
            if str(self._trade_give) == str(self._trade_get):
                return
            self._do_bank_trade(int(player_idx), str(self._trade_give), str(self._trade_get))

        elif btn_id == "buy_dev":
            if not self._is_my_turn(player_idx) or self.phase != "main" or not self._rolled_this_turn or self._pending_build is not None:
                return
            if not self._dev_deck:
                return
            if not self._can_afford(player_idx, {"sheep": 1, "wheat": 1, "ore": 1}):
                return
            self._spend(player_idx, {"sheep": 1, "wheat": 1, "ore": 1})
            self._bank["sheep"] += 1
            self._bank["wheat"] += 1
            self._bank["ore"] += 1
            card = self._dev_deck.pop()
            self._dev_hand[int(player_idx)][card] = int(self._dev_hand[int(player_idx)].get(card, 0)) + 1
            self._dev_bought_turn[int(player_idx)] = int(self._turn_number)
            self.last_event = f"{self._seat_label(player_idx)} bought a development card"
            self._update_awards_and_winner()

        elif isinstance(btn_id, str) and btn_id.startswith("play_dev:"):
            if not self._is_my_turn(player_idx) or self.phase != "main" or not self._rolled_this_turn or self._pending_build is not None:
                return
            card = str(btn_id.split(":", 1)[1])
            if int((self._dev_hand.get(int(player_idx)) or {}).get(card, 0)) <= 0:
                return
            if int(self._dev_bought_turn.get(int(player_idx), -999)) == int(self._turn_number) and card != "vp":
                return
            if self._dev_played_this_turn and card != "vp":
                return

            if card == "knight":
                self._dev_hand[int(player_idx)][card] -= 1
                self._knights_played[int(player_idx)] = int(self._knights_played.get(int(player_idx), 0)) + 1
                self._dev_played_this_turn = True
                self.phase = "robber_move"
                self.last_event = f"{self._seat_label(player_idx)} played Knight: move the robber (tap a land tile)."
                self._update_awards_and_winner()
            elif card == "road_building":
                self._dev_hand[int(player_idx)][card] -= 1
                self._dev_played_this_turn = True
                self._free_roads_left = 2
                self._pending_build = "road"
                self.last_event = f"{self._seat_label(player_idx)} played Road Building: place 2 free roads"
            elif card == "year_of_plenty":
                self._dev_hand[int(player_idx)][card] -= 1
                self._dev_played_this_turn = True
                self._yop_left = 2
                self.last_event = f"{self._seat_label(player_idx)} played Year of Plenty: pick 2 resources"
            elif card == "monopoly":
                self._dev_hand[int(player_idx)][card] -= 1
                self._dev_played_this_turn = True
                self._monopoly_pending = True
                self.last_event = f"{self._seat_label(player_idx)} played Monopoly: pick a resource"
            else:
                return

        elif isinstance(btn_id, str) and btn_id.startswith("yop:"):
            if not self._is_my_turn(player_idx) or self.phase != "main" or self._yop_left <= 0:
                return
            res = str(btn_id.split(":", 1)[1])
            if res not in _RESOURCE:
                return
            if int(self._bank.get(res, 0)) <= 0:
                return
            self._bank[res] = int(self._bank.get(res, 0)) - 1
            self._res[int(player_idx)][res] = int(self._res[int(player_idx)].get(res, 0)) + 1
            self._yop_left -= 1
            if self._yop_left <= 0:
                self.last_event = f"{self._seat_label(player_idx)} finished Year of Plenty"

        elif isinstance(btn_id, str) and btn_id.startswith("mono:"):
            if not self._is_my_turn(player_idx) or self.phase != "main" or not self._monopoly_pending:
                return
            res = str(btn_id.split(":", 1)[1])
            if res not in _RESOURCE:
                return
            taken = 0
            for seat in (self.active_players or []):
                if int(seat) == int(player_idx):
                    continue
                n = int(self._res[int(seat)].get(res, 0))
                if n <= 0:
                    continue
                self._res[int(seat)][res] = 0
                taken += n
            self._res[int(player_idx)][res] = int(self._res[int(player_idx)].get(res, 0)) + taken
            self._monopoly_pending = False
            self.last_event = f"{self._seat_label(player_idx)} monopolized {res} (+{taken})"

        # Robber steal selection buttons
        elif isinstance(btn_id, str) and btn_id.startswith("steal:"):
            if not self._is_my_turn(player_idx):
                return
            if self.phase != "robber_steal":
                return
            try:
                target = int(btn_id.split(":", 1)[1])
            except Exception:
                return
            if target not in (self._robber_candidates or []):
                return
            self._robber_do_steal(int(player_idx), int(target))
        elif btn_id == "skip_steal":
            if not self._is_my_turn(player_idx):
                return
            if self.phase != "robber_steal":
                return
            self.phase = "main"
            self._robber_candidates = []
            self._robber_pending_tile_idx = None
            self.last_event = f"{self._seat_label(player_idx)} skipped stealing"
        
        # Initial placement explicit buttons (optional, mostly to show in UI)
        elif btn_id == "initial_hint":
            pass

        self._refresh_buttons()

    # --- Pointer/tap board placement ---

    def handle_pointer_click(self, player_idx: int, x_px: int, y_px: int) -> None:
        if self.state != "playing":
            return
        if player_idx not in (self.active_players or []):
            return
        if not self._is_my_turn(player_idx):
            return

        # Need a valid draw transform.
        size = float(self._draw_size or self._hex_size or 28.0)
        off_x = float(self._draw_off_x)
        off_y = float(self._draw_off_y)
        if size <= 0:
            return

        # Convert screen px to logical coords (graph space uses size=1).
        lx = (float(x_px) - off_x) / size
        ly = (float(y_px) - off_y) / size

        # Robber move phase: tap a land tile
        if self.phase == "robber_move":
            ti = self._nearest_land_tile(lx, ly)
            if ti is None:
                return
            if isinstance(self.robber_tile_idx, int) and int(self.robber_tile_idx) == int(ti):
                return
            self.robber_tile_idx = int(ti)
            self._robber_pending_tile_idx = None
            # Determine candidates to steal from (adjacent to tile)
            cand = self._players_adjacent_to_tile(int(ti), exclude_seat=int(player_idx))
            self._robber_candidates = cand
            if not cand:
                self.phase = "main"
                self.last_event = f"{self._seat_label(player_idx)} moved the robber"
                self._update_awards_and_winner()
                self._refresh_buttons()
                return
            if len(cand) == 1:
                self._robber_do_steal(int(player_idx), int(cand[0]))
                return
            self.phase = "robber_steal"
            self.last_event = f"{self._seat_label(player_idx)}: choose someone to steal from"
            self._refresh_buttons()
            return

        if self.phase == "initial_settlement":
            vid = self._nearest_vertex(lx, ly)
            if vid is None:
                return
            if not self._can_place_settlement(player_idx, vid, initial=True):
                return
            self._place_building(player_idx, vid, "settlement")

            # Second settlement (snake pass) grants starting resources.
            try:
                if int(self._initial_step) >= len(self.active_players or []):
                    self._grant_starting_resources_for_settlement(int(player_idx), int(vid))
            except Exception:
                pass

            self._initial_last_settlement_vertex = int(vid)
            self.phase = "initial_road"
            self.last_event = f"{self._seat_label(player_idx)} placed a settlement; now place an adjacent road"
            self._refresh_buttons()
            return

        if self.phase == "initial_road":
            eid = self._nearest_edge(lx, ly)
            if eid is None:
                return
            if not self._can_place_road(player_idx, eid, initial=True):
                return
            self._roads[int(eid)] = int(player_idx)
            self.last_event = f"{self._seat_label(player_idx)} placed a road"
            # Advance snake turn
            self._advance_initial_turn_after_road()
            self._refresh_buttons()
            return

        # Main game builds
        if self.phase == "main" and self._pending_build:
            kind = str(self._pending_build)
            if kind == "settlement":
                vid = self._nearest_vertex(lx, ly)
                if vid is None:
                    return
                if not self._can_place_settlement(player_idx, vid, initial=False):
                    return
                self._spend(player_idx, {"wood": 1, "brick": 1, "sheep": 1, "wheat": 1})
                self._bank["wood"] += 1
                self._bank["brick"] += 1
                self._bank["sheep"] += 1
                self._bank["wheat"] += 1
                self._place_building(player_idx, vid, "settlement")
                self._pending_build = None
                self.last_event = f"{self._seat_label(player_idx)} built a settlement"
                self._update_awards_and_winner()
                self._refresh_buttons()
                # 🏠 Settlement animation
                try:
                    _pal = [(255,70,70),(70,145,255),(70,255,150),(255,220,70),(210,90,255),(70,255,245),(255,90,210),(210,255,90)]
                    _pcol = _pal[int(player_idx) % len(_pal)]
                    _v = self._vertices[int(vid)]
                    _vx = float(_v["x"]) * self._draw_size + self._draw_off_x
                    _vy = float(_v["y"]) * self._draw_size + self._draw_off_y
                    self._text_pops.append(TextPopAnim("\U0001f3e0 Settlement!", _vx, _vy - 30, _pcol, font_size=18))
                    self._pulse_rings.append(PulseRing(_vx, _vy, _pcol, max_radius=38, duration=0.6))
                    self._particles.emit_sparkle(_vx, _vy, _pcol, count=16)
                except Exception:
                    pass
                return
            if kind == "road":
                eid = self._nearest_edge(lx, ly)
                if eid is None:
                    return
                if not self._can_place_road(player_idx, eid, initial=False):
                    return
                if self._free_roads_left > 0:
                    self._free_roads_left -= 1
                else:
                    self._spend(player_idx, {"wood": 1, "brick": 1})
                    self._bank["wood"] += 1
                    self._bank["brick"] += 1
                self._roads[int(eid)] = int(player_idx)
                if self._free_roads_left <= 0:
                    self._pending_build = None
                self.last_event = f"{self._seat_label(player_idx)} built a road"
                self._update_awards_and_winner()
                self._refresh_buttons()
                # 🛤 Road animation (midpoint of edge)
                try:
                    _pal = [(255,70,70),(70,145,255),(70,255,150),(255,220,70),(210,90,255),(70,255,245),(255,90,210),(210,255,90)]
                    _pcol = _pal[int(player_idx) % len(_pal)]
                    _e = self._edges[int(eid)]
                    _va = self._vertices[int(_e["a"])]
                    _vb = self._vertices[int(_e["b"])]
                    _ex = (float(_va["x"]) + float(_vb["x"])) / 2 * self._draw_size + self._draw_off_x
                    _ey = (float(_va["y"]) + float(_vb["y"])) / 2 * self._draw_size + self._draw_off_y
                    self._text_pops.append(TextPopAnim("\U0001f6e4 Road!", _ex, _ey - 25, _pcol, font_size=16))
                    self._pulse_rings.append(PulseRing(_ex, _ey, _pcol, max_radius=28, duration=0.5))
                    self._particles.emit_sparkle(_ex, _ey, _pcol, count=12)
                except Exception:
                    pass
                return
            if kind == "city":
                vid = self._nearest_vertex(lx, ly)
                if vid is None:
                    return
                if not self._can_upgrade_city(player_idx, vid):
                    return
                self._spend(player_idx, {"ore": 3, "wheat": 2})
                self._bank["ore"] += 3
                self._bank["wheat"] += 2
                self._buildings[int(vid)] = {"owner": int(player_idx), "kind": "city"}
                self._pending_build = None
                self.last_event = f"{self._seat_label(player_idx)} upgraded to a city"
                self._update_awards_and_winner()
                self._refresh_buttons()
                # 🏙 City upgrade animation
                try:
                    _pal = [(255,70,70),(70,145,255),(70,255,150),(255,220,70),(210,90,255),(70,255,245),(255,90,210),(210,255,90)]
                    _pcol = _pal[int(player_idx) % len(_pal)]
                    _v = self._vertices[int(vid)]
                    _vx = float(_v["x"]) * self._draw_size + self._draw_off_x
                    _vy = float(_v["y"]) * self._draw_size + self._draw_off_y
                    self._text_pops.append(TextPopAnim("\U0001f3d9 City!", _vx, _vy - 30, _pcol, font_size=20))
                    self._pulse_rings.append(PulseRing(_vx, _vy, _pcol, max_radius=50, duration=0.7))
                    self._particles.emit_sparkle(_vx, _vy, _pcol)
                except Exception:
                    pass
                return

    def _advance_initial_turn_after_road(self) -> None:
        self._initial_last_settlement_vertex = None
        self._initial_step += 1
        if self._initial_step >= len(self._initial_order):
            # Enter main phase; first player in normal order starts.
            self.phase = "main"
            self.current_turn_seat = int(self.active_players[0])
            self._rolled_this_turn = False
            self._pending_build = None
            self.last_event = f"Main phase: {self._seat_label(int(self.current_turn_seat))} to roll"
            self._update_awards_and_winner()
            return

        self.current_turn_seat = int(self._initial_order[self._initial_step])
        self.phase = "initial_settlement"
        self.last_event = f"Initial placement: {self._seat_label(int(self.current_turn_seat))} place a settlement"

    def _nearest_vertex(self, lx: float, ly: float) -> Optional[int]:
        best = None
        best_d2 = 1e9
        for v in (self._vertices or []):
            dx = float(v["x"]) - float(lx)
            dy = float(v["y"]) - float(ly)
            d2 = dx * dx + dy * dy
            if d2 < best_d2:
                best_d2 = d2
                best = int(v["id"])
        # threshold: within ~0.55 of a corner in logical units
        if best is None:
            return None
        if best_d2 > 0.55 * 0.55:
            return None
        return int(best)

    def _dist_point_to_seg2(self, px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
        vx = bx - ax
        vy = by - ay
        wx = px - ax
        wy = py - ay
        c1 = vx * wx + vy * wy
        if c1 <= 0:
            dx = px - ax
            dy = py - ay
            return dx * dx + dy * dy
        c2 = vx * vx + vy * vy
        if c2 <= c1:
            dx = px - bx
            dy = py - by
            return dx * dx + dy * dy
        t = c1 / c2
        projx = ax + t * vx
        projy = ay + t * vy
        dx = px - projx
        dy = py - projy
        return dx * dx + dy * dy

    def _nearest_edge(self, lx: float, ly: float) -> Optional[int]:
        best = None
        best_d2 = 1e9
        for e in (self._edges or []):
            a = self._vertices[int(e["a"])]
            b = self._vertices[int(e["b"])]
            d2 = self._dist_point_to_seg2(float(lx), float(ly), float(a["x"]), float(a["y"]), float(b["x"]), float(b["y"]))
            if d2 < best_d2:
                best_d2 = d2
                best = int(e["id"])
        if best is None:
            return None
        if best_d2 > 0.35 * 0.35:
            return None
        return int(best)

    def _nearest_land_tile(self, lx: float, ly: float) -> Optional[int]:
        tiles = list(self.tiles or [])
        best = None
        best_d2 = 1e9
        for ti, t in enumerate(tiles):
            if str(t.kind) == "water":
                continue
            cx, cy = self._axial_to_pixel(int(t.q), int(t.r), 1.0)
            dx = float(cx) - float(lx)
            dy = float(cy) - float(ly)
            d2 = dx * dx + dy * dy
            if d2 < best_d2:
                best_d2 = d2
                best = int(ti)
        if best is None:
            return None
        # threshold: within ~0.95 of center
        if best_d2 > 0.95 * 0.95:
            return None
        return int(best)

    def _can_afford(self, seat: int, cost: Dict[str, int]) -> bool:
        inv = self._res.get(int(seat)) or {}
        for k, v in (cost or {}).items():
            if int(inv.get(k, 0)) < int(v):
                return False
        return True

    def _spend(self, seat: int, cost: Dict[str, int]) -> None:
        inv = self._res.get(int(seat))
        if inv is None:
            return
        for k, v in (cost or {}).items():
            inv[k] = max(0, int(inv.get(k, 0)) - int(v))

    def _place_building(self, seat: int, vid: int, kind: str) -> None:
        self._buildings[int(vid)] = {"owner": int(seat), "kind": str(kind)}

    def _grant_starting_resources_for_settlement(self, seat: int, vid: int) -> None:
        """Base-game rule: after placing your 2nd initial settlement, gain 1 resource
        from each adjacent producing hex (subject to bank availability).
        """
        try:
            v = self._vertices[int(vid)]
        except Exception:
            return
        for ti in (v.get("adj_tiles") or []):
            try:
                t = self.tiles[int(ti)]
            except Exception:
                continue
            if str(t.kind) in ("water", "desert", "volcano"):
                continue
            rk = self._tile_resource(str(t.kind))
            if rk is None:
                continue
            # gold: simplified as wheat
            if rk == "gold":
                rk = "wheat"
            if int(self._bank.get(rk, 0)) <= 0:
                continue
            self._bank[rk] = int(self._bank.get(rk, 0)) - 1
            self._res[int(seat)][rk] = int(self._res[int(seat)].get(rk, 0)) + 1

    def _init_dev_deck(self) -> None:
        deck: List[str] = []
        deck += ["knight"] * 14
        deck += ["vp"] * 5
        deck += ["road_building"] * 2
        deck += ["year_of_plenty"] * 2
        deck += ["monopoly"] * 2
        random.shuffle(deck)
        self._dev_deck = deck

    def _vp_for(self, seat: int) -> int:
        seat = int(seat)
        vp = 0
        for b in (self._buildings or {}).values():
            if int(b.get("owner")) != seat:
                continue
            vp += 2 if str(b.get("kind")) == "city" else 1
        vp += int((self._dev_hand.get(seat) or {}).get("vp", 0))
        if isinstance(self._largest_army_holder, int) and int(self._largest_army_holder) == seat:
            vp += 2
        if isinstance(self._longest_road_holder, int) and int(self._longest_road_holder) == seat:
            vp += 2
        return int(vp)

    def _update_awards_and_winner(self) -> None:
        # Largest army: >=3 knights and strictly greatest.
        best_army = 0
        best_seat: Optional[int] = None
        for s in (self.active_players or []):
            k = int(self._knights_played.get(int(s), 0))
            if k < 3:
                continue
            if k > best_army:
                best_army = k
                best_seat = int(s)
        self._largest_army_holder = int(best_seat) if best_seat is not None else None

        # Longest road: length>=5
        lr_seat, lr_len = self._compute_longest_road_holder()
        if lr_seat is None or int(lr_len) < 5:
            self._longest_road_holder = None
        else:
            self._longest_road_holder = int(lr_seat)

        # Winner: first to 10+ VP.
        if self.winner is None:
            for s in (self.active_players or []):
                if self._vp_for(int(s)) >= 10:
                    self.winner = int(s)
                    self.last_event = f"{self._seat_label(int(s))} wins!"
                    break

    def _compute_longest_road_holder(self) -> Tuple[Optional[int], int]:
        best_seat: Optional[int] = None
        best_len = 0
        for s in (self.active_players or []):
            l = self._longest_road_for_seat(int(s))
            if l > best_len:
                best_len = int(l)
                best_seat = int(s)
        return best_seat, int(best_len)

    def _longest_road_for_seat(self, seat: int) -> int:
        seat = int(seat)
        seat_edge_ids = [int(eid) for eid, owner in (self._roads or {}).items() if int(owner) == seat]
        if not seat_edge_ids:
            return 0

        blocked_vertices: set[int] = set()
        for vid, b in (self._buildings or {}).items():
            if int(b.get("owner")) != seat:
                blocked_vertices.add(int(vid))

        ep: Dict[int, Tuple[int, int]] = {}
        for eid in seat_edge_ids:
            e = self._edges[int(eid)]
            ep[int(eid)] = (int(e["a"]), int(e["b"]))

        inc: Dict[int, List[int]] = {}
        for eid, (a, b) in ep.items():
            inc.setdefault(a, []).append(int(eid))
            inc.setdefault(b, []).append(int(eid))

        best = 0

        def dfs(prev_v: int, v: int, used: set[int]) -> None:
            nonlocal best
            best = max(best, len(used))
            if v in blocked_vertices and v != prev_v:
                return
            for ne in inc.get(v, []):
                if ne in used:
                    continue
                a, b = ep[ne]
                nv = b if a == v else a
                used.add(ne)
                dfs(v, nv, used)
                used.remove(ne)

        for eid, (a, b) in ep.items():
            used = {int(eid)}
            dfs(a, b, used)
            dfs(b, a, used)

        return int(best)

    def _seat_has_port(self, seat: int, kind: str) -> bool:
        seat = int(seat)
        kind = str(kind)
        if kind not in ("any", *list(_RESOURCE)):
            return False

        # Map port tile index -> kind
        port_tiles: Dict[int, str] = {}
        for p in (self.ports or []):
            for ti, t in enumerate(self.tiles or []):
                if str(t.kind) != "water":
                    continue
                if int(t.q) == int(p.q) and int(t.r) == int(p.r):
                    port_tiles[int(ti)] = str(p.kind)
                    break

        for vid, b in (self._buildings or {}).items():
            if int(b.get("owner")) != seat:
                continue
            v = self._vertices[int(vid)]
            adj = set(v.get("adj_tiles") or [])
            for ti, pk in port_tiles.items():
                if int(ti) in adj:
                    if pk == "any" or pk == kind:
                        return True
        return False

    def _trade_ratio(self, seat: int, give: str) -> int:
        give = str(give)
        if self._seat_has_port(int(seat), give):
            return 2
        if self._seat_has_port(int(seat), "any"):
            return 3
        return 4

    def _do_bank_trade(self, seat: int, give: str, get: str) -> None:
        seat = int(seat)
        give = str(give)
        get = str(get)
        ratio = self._trade_ratio(seat, give)
        if int(self._res[seat].get(give, 0)) < ratio:
            return
        if int(self._bank.get(get, 0)) <= 0:
            return

        self._res[seat][give] = int(self._res[seat].get(give, 0)) - ratio
        self._bank[give] = int(self._bank.get(give, 0)) + ratio
        self._bank[get] = int(self._bank.get(get, 0)) - 1
        self._res[seat][get] = int(self._res[seat].get(get, 0)) + 1

        self.last_event = f"{self._seat_label(seat)} traded {ratio}:1 ({give}→{get})"

    def _can_place_settlement(self, seat: int, vid: int, initial: bool) -> bool:
        vid = int(vid)
        if vid in self._buildings:
            return False
        v = self._vertices[vid]
        # Distance rule: no adjacent vertex may have a building
        for nb in (v.get("nbrs") or []):
            if int(nb) in self._buildings:
                return False
        if initial:
            return True

        # Must connect to your network: adjacent road or your own building
        for eid, owner in (self._roads or {}).items():
            if int(owner) != int(seat):
                continue
            e = self._edges[int(eid)]
            if int(e["a"]) == vid or int(e["b"]) == vid:
                return True
        return False

    def _can_upgrade_city(self, seat: int, vid: int) -> bool:
        b = self._buildings.get(int(vid))
        if not b:
            return False
        if int(b.get("owner")) != int(seat):
            return False
        return str(b.get("kind")) == "settlement"

    def _can_place_road(self, seat: int, eid: int, initial: bool) -> bool:
        eid = int(eid)
        if eid in self._roads:
            return False
        e = self._edges[eid]
        a = int(e["a"])
        b = int(e["b"])

        if initial:
            sv = self._initial_last_settlement_vertex
            if not isinstance(sv, int):
                return False
            return a == int(sv) or b == int(sv)

        # Must connect to existing road/building
        for vid in (a, b):
            bb = self._buildings.get(int(vid))
            if bb and int(bb.get("owner")) == int(seat):
                return True
        for rid, owner in (self._roads or {}).items():
            if int(owner) != int(seat):
                continue
            rr = self._edges[int(rid)]
            if a in (int(rr["a"]), int(rr["b"])) or b in (int(rr["a"]), int(rr["b"])):
                return True
        return False

    def _distribute_resources_for_roll(self, roll: int) -> None:
        roll = int(roll)
        tiles = list(self.tiles or [])
        for ti, t in enumerate(tiles):
            if isinstance(self.robber_tile_idx, int) and int(self.robber_tile_idx) == int(ti):
                continue
            if str(t.kind) in ("water", "desert", "volcano"):
                continue
            if not isinstance(t.number, int):
                continue
            if int(t.number) != roll:
                continue

            res_kind = self._tile_resource(str(t.kind))
            if res_kind is None:
                continue

            # Find all buildings adjacent to this tile.
            for vid, b in (self._buildings or {}).items():
                v = self._vertices[int(vid)]
                if int(ti) not in (v.get("adj_tiles") or []):
                    continue
                owner = int(b.get("owner"))
                mult = 2 if str(b.get("kind")) == "city" else 1

                if res_kind == "gold":
                    # Gold: give wheat by default (simple), scaled by mult.
                    give = min(int(mult), int(self._bank.get("wheat", 0)))
                    if give > 0:
                        self._bank["wheat"] = int(self._bank.get("wheat", 0)) - give
                        self._res[owner]["wheat"] = int(self._res[owner].get("wheat", 0)) + give
                else:
                    give = min(int(mult), int(self._bank.get(res_kind, 0)))
                    if give > 0:
                        self._bank[res_kind] = int(self._bank.get(res_kind, 0)) - give
                        self._res[owner][res_kind] = int(self._res[owner].get(res_kind, 0)) + give

    def _handle_roll_seven(self, roller: int) -> None:
        # Discard half for players with >7 total cards (player-chosen via discard buttons).
        self._discard_need = {}
        self._discard_remaining = {}
        affected: List[str] = []
        for seat in (self.active_players or []):
            inv = self._res.get(int(seat)) or {}
            total = sum(int(inv.get(k, 0)) for k in _RESOURCE)
            if total <= 7:
                continue
            need = total // 2
            if need <= 0:
                continue
            self._discard_need[int(seat)] = int(need)
            self._discard_remaining[int(seat)] = int(need)
            affected.append(f"{self._seat_label(int(seat))} ({need})")

        if affected:
            self.phase = "discard"
            self.last_event = "7 rolled. Discard half: " + ", ".join(affected) + f". Then {self._seat_label(int(roller))} moves the robber."
        else:
            self.phase = "robber_move"
            self.last_event = f"7 rolled. {self._seat_label(int(roller))}: move the robber (tap a land tile)."

        # Cancel any pending build.
        self._pending_build = None
        self._robber_candidates = []
        self._robber_pending_tile_idx = None

    def _discard_random(self, seat: int, count: int) -> None:
        inv = self._res.get(int(seat))
        if inv is None:
            return
        pool: List[str] = []
        for k in _RESOURCE:
            pool.extend([k] * int(inv.get(k, 0)))
        random.shuffle(pool)
        for _ in range(int(count)):
            if not pool:
                break
            k = pool.pop()
            inv[k] = max(0, int(inv.get(k, 0)) - 1)

    def _players_adjacent_to_tile(self, tile_idx: int, exclude_seat: int) -> List[int]:
        tile_idx = int(tile_idx)
        owners: List[int] = []
        for vid, b in (self._buildings or {}).items():
            owner = int(b.get("owner"))
            if owner == int(exclude_seat):
                continue
            v = self._vertices[int(vid)]
            if tile_idx in (v.get("adj_tiles") or []):
                owners.append(owner)
        owners = sorted(dict.fromkeys(owners))
        return owners

    def _robber_do_steal(self, thief: int, target: int) -> None:
        inv = self._res.get(int(target)) or {}
        pool: List[str] = []
        for k in _RESOURCE:
            pool.extend([k] * int(inv.get(k, 0)))
        if not pool:
            self.phase = "main"
            self._robber_candidates = []
            self._robber_pending_tile_idx = None
            self.last_event = f"{self._seat_label(int(thief))} tried to steal from {self._seat_label(int(target))}, but they had nothing"
            self._refresh_buttons()
            return
        k = random.choice(pool)
        # transfer
        inv[k] = max(0, int(inv.get(k, 0)) - 1)
        self._res[int(thief)][k] = int(self._res[int(thief)].get(k, 0)) + 1

        self.phase = "main"
        self._robber_candidates = []
        self._robber_pending_tile_idx = None
        self.last_event = f"{self._seat_label(int(thief))} stole 1 {k} from {self._seat_label(int(target))}"
        self._update_awards_and_winner()
        self._refresh_buttons()

    def _refresh_buttons(self) -> None:
        self.buttons = {i: {} for i in range(8)}
        for seat in self.active_players:
            if self.state != "playing":
                continue

            # Winner lock
            if isinstance(self.winner, int):
                self.buttons[seat]["end_turn"] = _WebButton(f"Winner: {self._seat_label(int(self.winner))}", enabled=False)
                continue

            # Discard phase: affected players can discard even if it's not their turn.
            if self.phase == "discard":
                rem = int(self._discard_remaining.get(int(seat), 0))
                if rem > 0:
                    self.buttons[seat]["initial_hint"] = _WebButton(f"Discard {rem}", enabled=False)
                    inv = self._res.get(int(seat)) or {}
                    for r in _RESOURCE:
                        have = int(inv.get(r, 0))
                        self.buttons[seat][f"discard:{r}"] = _WebButton(f"Discard {r} ({have})", enabled=(have > 0))
                else:
                    self.buttons[seat]["end_turn"] = _WebButton("Waiting (discard)", enabled=False)
                continue

            # Pending player-to-player trade: recipient can accept/decline even if it's not their turn.
            if isinstance(self._p2p_offer, dict) and self.phase.startswith("trade_player"):
                try:
                    frm = int(self._p2p_offer.get("from"))  # type: ignore[arg-type]
                    to = int(self._p2p_offer.get("to"))  # type: ignore[arg-type]
                    give = str(self._p2p_offer.get("give")) if self._p2p_offer.get("give") is not None else ""
                    get = str(self._p2p_offer.get("get")) if self._p2p_offer.get("get") is not None else ""
                except Exception:
                    frm = to = -1
                    give = get = ""

                if int(seat) == int(to) and give in _RESOURCE and get in _RESOURCE:
                    self.buttons[seat]["initial_hint"] = _WebButton(f"Trade offer: give 1 {get} for 1 {give}", enabled=False)
                    can_accept = int((self._res.get(int(seat)) or {}).get(get, 0)) > 0 and int((self._res.get(int(frm)) or {}).get(give, 0)) > 0
                    self.buttons[seat]["p2p_accept"] = _WebButton("Accept", enabled=bool(can_accept))
                    self.buttons[seat]["p2p_decline"] = _WebButton("Decline", enabled=True)
                    continue

                if int(seat) == int(frm) and self._is_my_turn(seat) and self.phase == "trade_player_wait":
                    self.buttons[seat]["initial_hint"] = _WebButton("Waiting for response…", enabled=False)
                    self.buttons[seat]["trade_cancel"] = _WebButton("Cancel Offer", enabled=True)
                    continue

            # Not your turn
            if not self._is_my_turn(seat):
                self.buttons[seat]["end_turn"] = _WebButton("Waiting", enabled=False)
                continue

            # Initial placement
            if self.phase == "initial_settlement":
                self.buttons[seat]["initial_hint"] = _WebButton("Tap: Place Settlement", enabled=False)
                continue
            if self.phase == "initial_road":
                self.buttons[seat]["initial_hint"] = _WebButton("Tap: Place Road", enabled=False)
                continue

            # Robber
            if self.phase == "robber_move":
                self.buttons[seat]["initial_hint"] = _WebButton("Tap: Move Robber", enabled=False)
                continue
            if self.phase == "robber_steal":
                for cand in (self._robber_candidates or []):
                    self.buttons[seat][f"steal:{int(cand)}"] = _WebButton(f"Steal from {self._seat_label(int(cand))}", enabled=True)
                self.buttons[seat]["skip_steal"] = _WebButton("Skip Steal", enabled=True)
                continue

            # Bank trade sub-mode
            if self.phase == "trade_bank":
                give = self._trade_give or "wood"
                get = self._trade_get or "brick"
                ratio = self._trade_ratio(int(seat), str(give))
                self.buttons[seat]["initial_hint"] = _WebButton(f"Bank trade {ratio}:1", enabled=False)
                for r in _RESOURCE:
                    self.buttons[seat][f"trade_give:{r}"] = _WebButton(f"Give: {r}{' ✓' if r == give else ''}", enabled=True)
                for r in _RESOURCE:
                    self.buttons[seat][f"trade_get:{r}"] = _WebButton(f"Get: {r}{' ✓' if r == get else ''}", enabled=True)
                can = (
                    give != get
                    and int((self._res.get(int(seat)) or {}).get(str(give), 0)) >= int(ratio)
                    and int(self._bank.get(str(get), 0)) > 0
                )
                self.buttons[seat]["trade_confirm"] = _WebButton("Confirm Trade", enabled=bool(can))
                self.buttons[seat]["trade_cancel"] = _WebButton("Back", enabled=True)
                continue

            # Player trade sub-modes
            if self.phase == "trade_player_select":
                self.buttons[seat]["initial_hint"] = _WebButton("Pick a trade partner", enabled=False)
                for other in (self.active_players or []):
                    if int(other) == int(seat):
                        continue
                    self.buttons[seat][f"trade_to:{int(other)}"] = _WebButton(f"Trade with {self._seat_label(int(other))}", enabled=True)
                self.buttons[seat]["trade_cancel"] = _WebButton("Back", enabled=True)
                continue
            if self.phase == "trade_player_offer":
                to_seat = None
                try:
                    if isinstance(self._p2p_offer, dict):
                        to_seat = int(self._p2p_offer.get("to"))  # type: ignore[arg-type]
                except Exception:
                    to_seat = None
                self.buttons[seat]["initial_hint"] = _WebButton(
                    f"Offer 1-for-1 to {self._seat_label(int(to_seat))}" if isinstance(to_seat, int) else "Offer 1-for-1",
                    enabled=False,
                )
                give = self._p2p_give or "wood"
                get = self._p2p_get or "brick"
                for r in _RESOURCE:
                    self.buttons[seat][f"p2p_give:{r}"] = _WebButton(f"You give: {r}{' ✓' if r == give else ''}", enabled=True)
                for r in _RESOURCE:
                    self.buttons[seat][f"p2p_get:{r}"] = _WebButton(f"You get: {r}{' ✓' if r == get else ''}", enabled=True)
                can_offer = give != get and int((self._res.get(int(seat)) or {}).get(str(give), 0)) > 0
                self.buttons[seat]["p2p_offer"] = _WebButton("Send Offer", enabled=bool(can_offer))
                self.buttons[seat]["trade_cancel"] = _WebButton("Back", enabled=True)
                continue

            # Main phase
            self.buttons[seat]["roll"] = _WebButton("Roll Dice", enabled=(not self._rolled_this_turn and (not self.dice_rolling) and self._pending_build is None))

            can_road = self._rolled_this_turn and self._pending_build in (None, "road") and (
                self._free_roads_left > 0 or self._can_afford(seat, {"wood": 1, "brick": 1})
            )
            self.buttons[seat]["build_road"] = _WebButton("Build Road", enabled=bool(can_road))
            self.buttons[seat]["build_settlement"] = _WebButton(
                "Build Settlement",
                enabled=(
                    self._rolled_this_turn
                    and self._pending_build in (None, "settlement")
                    and self._can_afford(seat, {"wood": 1, "brick": 1, "sheep": 1, "wheat": 1})
                ),
            )
            self.buttons[seat]["build_city"] = _WebButton(
                "Build City",
                enabled=(self._rolled_this_turn and self._pending_build in (None, "city") and self._can_afford(seat, {"ore": 3, "wheat": 2})),
            )
            self.buttons[seat]["trade_bank"] = _WebButton("Trade (Bank)", enabled=(self._rolled_this_turn and self._pending_build is None))
            self.buttons[seat]["trade_player"] = _WebButton("Trade (Player)", enabled=(self._rolled_this_turn and self._pending_build is None))
            self.buttons[seat]["buy_dev"] = _WebButton(
                "Buy Dev",
                enabled=(
                    self._rolled_this_turn
                    and self._pending_build is None
                    and bool(self._dev_deck)
                    and self._can_afford(seat, {"sheep": 1, "wheat": 1, "ore": 1})
                ),
            )

            # Dev play
            hand = self._dev_hand.get(int(seat)) or {}
            bought_this_turn = int(self._dev_bought_turn.get(int(seat), -999)) == int(self._turn_number)
            if int(hand.get("knight", 0)) > 0:
                self.buttons[seat]["play_dev:knight"] = _WebButton("Play Knight", enabled=(not bought_this_turn and not self._dev_played_this_turn))
            if int(hand.get("road_building", 0)) > 0:
                self.buttons[seat]["play_dev:road_building"] = _WebButton("Play Road Building", enabled=(not bought_this_turn and not self._dev_played_this_turn))
            if int(hand.get("year_of_plenty", 0)) > 0:
                self.buttons[seat]["play_dev:year_of_plenty"] = _WebButton("Play Year of Plenty", enabled=(not bought_this_turn and not self._dev_played_this_turn))
            if int(hand.get("monopoly", 0)) > 0:
                self.buttons[seat]["play_dev:monopoly"] = _WebButton("Dev: Monopoly", enabled=(not bought_this_turn and not self._dev_played_this_turn))

            # Year of Plenty selections
            if self._yop_left > 0:
                self.buttons[seat]["initial_hint"] = _WebButton(f"Pick {self._yop_left} resource(s)", enabled=False)
                for r in _RESOURCE:
                    self.buttons[seat][f"yop:{r}"] = _WebButton(f"Pick {r} ({self._bank.get(r, 0)})", enabled=(int(self._bank.get(r, 0)) > 0))

            # Monopoly selection
            if bool(self._monopoly_pending):
                self.buttons[seat]["initial_hint"] = _WebButton("Pick Monopoly resource", enabled=False)
                for r in _RESOURCE:
                    self.buttons[seat][f"mono:{r}"] = _WebButton(f"Monopoly {r}", enabled=True)

            if self._pending_build is not None:
                self.buttons[seat]["cancel_build"] = _WebButton("Cancel Build", enabled=True)

            end_ok = self._rolled_this_turn and self._pending_build is None and self._yop_left <= 0 and (not self._monopoly_pending)
            self.buttons[seat]["end_turn"] = _WebButton("End Turn", enabled=bool(end_ok))

    def get_public_state(self, player_idx: int) -> Dict:
        tiles = [
            {
                "q": int(t.q),
                "r": int(t.r),
                "kind": str(t.kind),
                "number": (int(t.number) if isinstance(t.number, int) else None),
            }
            for t in (self.tiles or [])
        ]
        ports = [{"q": int(p.q), "r": int(p.r), "kind": str(p.kind)} for p in (self.ports or [])]
        is_active_player = isinstance(player_idx, int) and player_idx in (self.active_players or [])
        your_res = None
        try:
            if is_active_player:
                your_res = dict(self._res.get(int(player_idx)) or {})
        except Exception:
            your_res = None
        return {
            "state": str(self.state),
            "active_players": list(self.active_players),
            "current_turn_seat": self.current_turn_seat,
            "expansion_mode": str(self.expansion_mode),
            "map_radius": int(self._map_radius),
            "ports": ports,
            "phase": str(self.phase),
            "rolled": bool(self._rolled_this_turn),
            "pending_build": self._pending_build,
            "your_resources": your_res,
            "robber_tile_idx": self.robber_tile_idx,
            "robber_candidates": list(self._robber_candidates or []) if self.phase == "robber_steal" else [],
            "bank": dict(self._bank),
            "dev": dict(self._dev_hand.get(int(player_idx), {}) or {}) if is_active_player else {},
            "knights_played": int(self._knights_played.get(int(player_idx), 0)) if is_active_player else 0,
            "vp": self._vp_for(int(player_idx)) if is_active_player else 0,
            "largest_army_holder": self._largest_army_holder,
            "longest_road_holder": self._longest_road_holder,
            "winner": self.winner,
            "last_event": self.last_event or None,
            "last_roll": self.last_roll,
            "dice_rolling": bool(self.dice_rolling),
            "tiles": tiles,
        }

    def _draw_pips(self, cx: int, cy: int, size: int, value: int, *, layer: int) -> None:
        # Bigger pips for wall visibility.
        r = max(3, size // 8)
        off = size // 4
        pips = {
            1: [(0, 0)],
            2: [(-off, -off), (off, off)],
            3: [(-off, -off), (0, 0), (off, off)],
            4: [(-off, -off), (off, -off), (-off, off), (off, off)],
            5: [(-off, -off), (off, -off), (0, 0), (-off, off), (off, off)],
            6: [(-off, -off), (off, -off), (-off, 0), (off, 0), (-off, off), (off, off)],
        }
        for dx, dy in pips.get(int(value), []):
            self.renderer.draw_circle_immediate((0, 0, 0), (int(cx + dx), int(cy + dy)), int(r), width=0, alpha=255, layer=layer)

    def _draw_dice_overlay(self) -> None:
        now = float(time.time())
        # Show while rolling OR whenever a roll result is available (persistent until next round).
        show = bool(self.dice_rolling) or isinstance(self.last_roll, int)
        if not show:
            return

        w = int(self.width)
        # Position under the header, top-right.
        cx = int(w - 180)
        cy = 122
        # Bigger dice so pips are visible from a distance.
        dice_size = 86
        gap = 16

        if self.dice_rolling:
            display_values = (random.randint(1, 6), random.randint(1, 6))
        else:
            try:
                if isinstance(self._last_dice, tuple) and len(self._last_dice) == 2:
                    display_values = (int(self._last_dice[0]), int(self._last_dice[1]))
                else:
                    display_values = (1, 1)
            except Exception:
                display_values = (1, 1)

        for i, value in enumerate(display_values):
            # Simple animation: slight jitter while rolling (Monopoly-like feel).
            jx = 0
            jy = 0
            if self.dice_rolling:
                try:
                    jx = int(6 * math.sin(now * 38.0 + i * 1.7))
                    jy = int(6 * math.cos(now * 41.0 + i * 2.3))
                except Exception:
                    jx = jy = 0

            dx = int(cx + (i - 0.5) * (dice_size + gap)) + jx
            dy = int(cy) + jy
            half = int(dice_size // 2)
            shadow = 3

            # Shadow
            self.renderer.draw_polygon_immediate(
                (100, 100, 100),
                [(dx - half + shadow, dy - half + shadow), (dx + half + shadow, dy - half + shadow), (dx + half + shadow, dy + half + shadow), (dx - half + shadow, dy + half + shadow)],
                alpha=180,
                layer=200,
            )
            # Face
            self.renderer.draw_polygon_immediate(
                (255, 255, 255),
                [(dx - half, dy - half), (dx + half, dy - half), (dx + half, dy + half), (dx - half, dy + half)],
                alpha=255,
                layer=210,
            )
            # Border
            self.renderer.draw_polyline_immediate(
                (0, 0, 0),
                [(dx - half, dy - half), (dx + half, dy - half), (dx + half, dy + half), (dx - half, dy + half)],
                width=3,
                alpha=255,
                closed=True,
                layer=220,
            )
            self._draw_pips(int(dx), int(dy), int(dice_size), int(value), layer=230)

        if isinstance(self.last_roll, int) and not self.dice_rolling:
            # Shadow
            self.renderer.draw_text_immediate(
                f"= {int(self.last_roll)}",
                int(cx + dice_size + 40),
                int(cy) + 4,
                font_size=22,
                color=(30, 20, 10),
                anchor_x="left",
                anchor_y="center",
                alpha=160,
                layer=239,
            )
            self.renderer.draw_text_immediate(
                f"= {int(self.last_roll)}",
                int(cx + dice_size + 38),
                int(cy) + 2,
                font_size=22,
                color=(255, 235, 80),
                anchor_x="left",
                anchor_y="center",
                alpha=255,
                layer=240,
            )

    # --- Drawing ---

    def _axial_to_pixel(self, q: int, r: int, size: float) -> Tuple[float, float]:
        # pointy-top axial coords
        x = size * math.sqrt(3) * (q + r / 2.0)
        y = size * 1.5 * r
        return x, y

    def _hex_points(self, cx: float, cy: float, size: float) -> List[Tuple[int, int]]:
        pts: List[Tuple[int, int]] = []
        for i in range(6):
            ang = math.radians(60 * i - 30)  # pointy-top
            px = cx + size * math.cos(ang)
            py = cy + size * math.sin(ang)
            pts.append((int(px), int(py)))
        return pts

    def _recompute_layout(self) -> None:
        # Compute hex size to fit all tiles in the available area.
        w = int(self.width)
        h = int(self.height)
        pad = 10
        header_h = 54
        avail_w = max(100, w - pad * 2)
        avail_h = max(100, h - header_h - pad)

        # Estimate bounds from current tile set.
        tiles = list(self.tiles or [])
        if not tiles:
            self._hex_size = 28.0
            self._map_center = (w // 2, (h + header_h) // 2)
            return

        # Compute ideal size by measuring extents at size=1 and scaling to fit.
        centers_unit = [self._axial_to_pixel(int(t.q), int(t.r), 1.0) for t in tiles]
        xs_u = [c[0] for c in centers_unit]
        ys_u = [c[1] for c in centers_unit]

        # The +2.* term approximates the extra half-hex margin on both sides.
        # Keep it a bit tight so the board fills the wall display.
        span_x_u = (max(xs_u) - min(xs_u)) + 2.0
        span_y_u = (max(ys_u) - min(ys_u)) + 2.0
        size = min(avail_w / max(1.0, span_x_u), avail_h / max(1.0, span_y_u))
        size *= 0.995  # tiny padding
        size = max(14.0, min(80.0, float(size)))

        # Sanity check the fit with the chosen size.
        centers = [self._axial_to_pixel(int(t.q), int(t.r), float(size)) for t in tiles]
        xs = [c[0] for c in centers]
        ys = [c[1] for c in centers]
        span_x = (max(xs) - min(xs)) + float(size) * 2.0
        span_y = (max(ys) - min(ys)) + float(size) * 2.0
        scale = min(avail_w / max(1.0, span_x), avail_h / max(1.0, span_y), 1.0)
        size = float(size) * float(scale)
        size = max(14.0, min(80.0, float(size)))

        self._hex_size = float(size)
        self._map_center = (w // 2, (header_h + avail_h // 2))

    def draw(self) -> None:
        if self.renderer is None:
            return

        self._recompute_layout()
        cx0, cy0 = self._map_center
        size = float(self._hex_size)

        # Background (tropical ocean-ish gradient)
        w = int(self.width)
        h = int(self.height)
        self.renderer.draw_rect((6, 34, 52), (0, 0, w, h))
        # subtle water bands (lighter towards the top) — more steps reduces visible banding
        try:
            steps = 64
            for i in range(steps):
                t = i / float(max(1, steps - 1))
                a = 10 + int(40 * t)
                self.renderer.draw_rect(
                    (8, 70 + int(75 * t), 90 + int(95 * t)),
                    (0, int(h * (i / float(steps + 6))), w, int(h / float(steps + 6)) + 2),
                    alpha=a,
                )
        except Exception:
            pass

        # Sand strip at the bottom for a "shore" feel
        try:
            sand_h = max(18, int(h * 0.085))
            self.renderer.draw_rect((194, 170, 120), (0, h - sand_h, w, sand_h), alpha=225)
            self.renderer.draw_rect((176, 154, 108), (0, h - sand_h, w, max(1, sand_h // 3)), alpha=140)
            # Foam line
            self.renderer.draw_rect((220, 210, 180), (0, h - sand_h - 2, w, 2), alpha=60)
        except Exception:
            pass

        # Header
        title = "Catan"
        if self.state == "playing":
            turn = self._seat_label(int(self.current_turn_seat)) if isinstance(self.current_turn_seat, int) else "—"
            subtitle = f"Turn: {turn}  ·  Expansion: {self.expansion_mode}  ·  Players: {len(self.active_players)}"
        else:
            subtitle = "Select players in Web UI"

        draw_rainbow_title(self.renderer, "CATAN", w)
        self.renderer.draw_text(subtitle, 16, 50, font_size=14, color=(200, 200, 200), anchor_x="left", anchor_y="top")

        if self.state != "playing":
            return

        # Draw hex tiles
        tiles = list(self.tiles or [])
        # Sort: water first so land is on top
        tiles.sort(key=lambda t: 0 if t.kind == "water" else 1)

        # Determine pixel offset so the map is centered.
        centers = [self._axial_to_pixel(int(t.q), int(t.r), size) for t in tiles]
        xs = [c[0] for c in centers]
        ys = [c[1] for c in centers]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        off_x = float(cx0) - (min_x + max_x) / 2.0
        off_y = float(cy0) - (min_y + max_y) / 2.0

        # Store for pointer mapping.
        self._draw_off_x = float(off_x)
        self._draw_off_y = float(off_y)
        self._draw_size = float(size)

        # Ports lookup
        port_by_coord: Dict[Tuple[int, int], str] = {}
        for p in (self.ports or []):
            port_by_coord[(int(p.q), int(p.r))] = str(p.kind)

        for t in tiles:
            px, py = self._axial_to_pixel(int(t.q), int(t.r), size)
            cx = px + off_x
            cy = py + off_y

            col = _KIND_COLOR.get(str(t.kind), (180, 180, 180))
            # Bevel/shading: outer darker + inner lighter
            pts_outer = self._hex_points(cx, cy, size * 1.00)
            dark = (max(0, int(col[0] * 0.72)), max(0, int(col[1] * 0.72)), max(0, int(col[2] * 0.72)))
            light = (min(255, int(col[0] * 1.08)), min(255, int(col[1] * 1.08)), min(255, int(col[2] * 1.08)))
            self.renderer.draw_polygon_immediate(dark, pts_outer, alpha=235 if t.kind != "water" else 190, layer=10)
            pts_inner = self._hex_points(cx, cy, size * 0.94)
            self.renderer.draw_polygon_immediate(light, pts_inner, alpha=235 if t.kind != "water" else 170, layer=11)
            # outline
            self.renderer.draw_polyline_immediate((15, 18, 22), pts_outer, width=2, alpha=150, closed=True, layer=12)

            pk = port_by_coord.get((int(t.q), int(t.r))) if t.kind == "water" else None

            emoji = _KIND_EMOJI.get(str(t.kind), "")
            # If this is a port water tile, skip the water emoji so the port icon reads clearly.
            if emoji and not (t.kind == "water" and pk):
                self.renderer.draw_text_immediate(
                    emoji,
                    int(cx),
                    int(cy) - 2,
                    font_size=int(max(14, size * 0.60)),
                    # White preserves emoji's internal color on most platforms.
                    color=(255, 255, 255),
                    anchor_x="center",
                    anchor_y="center",
                    layer=20,
                )

            if isinstance(t.number, int) and t.kind not in ("water", "desert", "volcano"):
                self.renderer.draw_circle_immediate((245, 235, 210), (int(cx), int(cy) + int(size * 0.35)), int(max(10, size * 0.26)), width=0, alpha=220, layer=30)
                self.renderer.draw_circle_immediate((0, 0, 0), (int(cx), int(cy) + int(size * 0.35)), int(max(10, size * 0.26) + 1), width=0, alpha=70, layer=31)
                self.renderer.draw_text_immediate(str(int(t.number)), int(cx), int(cy) + int(size * 0.35), font_size=int(max(12, size * 0.32)), color=(30, 30, 30), anchor_x="center", anchor_y="center", layer=32)

            # Robber overlay
            try:
                if isinstance(self.robber_tile_idx, int):
                    # We sorted tiles; need to compare to original index by matching coords+kind+number.
                    # Use coord match: robber always refers to the underlying self.tiles index.
                    pass
            except Exception:
                pass

            # Ports on coastal water tiles
            if t.kind == "water" and pk:
                pe = _PORT_EMOJI.get(str(pk), "⚓")
                self.renderer.draw_text_immediate(
                    pe,
                    int(cx),
                    int(cy) - int(size * 0.05),
                    font_size=int(max(12, size * 0.40)),
                    color=(255, 255, 255),
                    anchor_x="center",
                    anchor_y="center",
                    layer=40,
                )

        # Draw roads
        for eid, owner in (self._roads or {}).items():
            try:
                e = self._edges[int(eid)]
                va = self._vertices[int(e["a"])]
                vb = self._vertices[int(e["b"])]
                ax = float(va["x"]) * size + off_x
                ay = float(va["y"]) * size + off_y
                bx = float(vb["x"]) * size + off_x
                by = float(vb["y"]) * size + off_y
                col = (200, 200, 200)
                if isinstance(owner, int) and 0 <= owner < 8:
                    try:
                        # Use a bright-ish palette (fallback)
                        pal = [
                            (255, 70, 70),
                            (70, 145, 255),
                            (70, 255, 150),
                            (255, 220, 70),
                            (210, 90, 255),
                            (70, 255, 245),
                            (255, 90, 210),
                            (210, 255, 90),
                        ]
                        col = pal[int(owner) % len(pal)]
                    except Exception:
                        pass

                # NOTE: On many OpenGL core-profile drivers, wide line widths are clamped to 1px.
                # To guarantee visible roads, draw them as filled quads (polygons).
                dx = float(bx) - float(ax)
                dy = float(by) - float(ay)
                ln = math.hypot(dx, dy)
                if ln <= 1e-6:
                    continue
                nx = -dy / ln
                ny = dx / ln

                half_glow = float(max(10.0, size * 0.20))
                half_outer = float(max(7.0, size * 0.14))
                half_inner = float(max(5.0, size * 0.10))

                def _quad(half_w: float) -> List[Tuple[int, int]]:
                    return [
                        (int(ax + nx * half_w), int(ay + ny * half_w)),
                        (int(bx + nx * half_w), int(by + ny * half_w)),
                        (int(bx - nx * half_w), int(by - ny * half_w)),
                        (int(ax - nx * half_w), int(ay - ny * half_w)),
                    ]

                self.renderer.draw_polygon_immediate((255, 255, 255), _quad(half_glow), alpha=70, layer=60)
                self.renderer.draw_polygon_immediate((0, 0, 0), _quad(half_outer), alpha=220, layer=61)
                self.renderer.draw_polygon_immediate(col, _quad(half_inner), alpha=255, layer=62)
            except Exception:
                continue

        # Draw settlements/cities
        for vid, b in (self._buildings or {}).items():
            try:
                v = self._vertices[int(vid)]
                cx = float(v["x"]) * size + off_x
                cy = float(v["y"]) * size + off_y
                owner = int(b.get("owner"))
                kind = str(b.get("kind"))
                pal = [
                    (255, 70, 70),
                    (70, 145, 255),
                    (70, 255, 150),
                    (255, 220, 70),
                    (210, 90, 255),
                    (70, 255, 245),
                    (255, 90, 210),
                    (210, 255, 90),
                ]
                col = pal[int(owner) % len(pal)]

                # Strong ownership cue: a colored halo behind the building emoji.
                halo_r = int(max(10, size * 0.22))
                self.renderer.draw_circle_immediate(col, (int(cx), int(cy)), halo_r, width=0, alpha=155, layer=68)
                self.renderer.draw_circle_immediate((0, 0, 0), (int(cx), int(cy)), halo_r, width=0, alpha=120, layer=69)
                # Emoji marker (keeps the friendly look) + a colored ownership dot.
                em = "🏠" if kind == "settlement" else "🏰"
                self.renderer.draw_text_immediate(
                    em,
                    int(cx),
                    int(cy) - 1,
                    font_size=int(max(14, size * 0.48)),
                    color=(255, 255, 255),
                    anchor_x="center",
                    anchor_y="center",
                    alpha=255,
                    layer=70,
                )

                dot_r = int(max(7, size * 0.13))
                # Place dot closer to the top edge so it's not lost in the emoji glyph.
                dot_x = int(cx)
                dot_y = int(cy - size * 0.32)
                self.renderer.draw_circle_immediate((255, 255, 255), (dot_x, dot_y), dot_r + 4, width=0, alpha=220, layer=79)
                self.renderer.draw_circle_immediate((0, 0, 0), (dot_x, dot_y), dot_r + 3, width=0, alpha=255, layer=80)
                self.renderer.draw_circle_immediate(col, (dot_x, dot_y), dot_r, width=0, alpha=255, layer=81)
            except Exception:
                continue

        # Dice overlay (Monopoly-style)
        self._draw_dice_overlay()

        # Event line
        if self.last_event:
            ev = str(self.last_event)
            ew = max(200, len(ev) * 8)
            eh = 24
            self.renderer.draw_rect((0, 0, 0), (12, 68, ew, eh), alpha=130)
            self.renderer.draw_rect((80, 160, 200), (12, 68, ew, eh), width=1, alpha=50)
            self.renderer.draw_text(
                ev, 20, 80,
                font_size=12, color=(200, 210, 220),
                anchor_x="left", anchor_y="center",
            )

        # Footer hint
        try:
            self.renderer.draw_text(
                f"Map radius: {int(self._map_radius)}  ·  Ports: {len(self.ports or [])}",
                int(self.width) - 16,
                int(self.height) - 16,
                font_size=11,
                color=(190, 190, 190),
                anchor_x="right",
                anchor_y="bottom",
            )
        except Exception:
            pass

        # Draw robber last (on top). Use self.tiles index coords.
        if isinstance(self.robber_tile_idx, int):
            try:
                rt = (self.tiles or [])[int(self.robber_tile_idx)]
                if rt is not None and str(getattr(rt, "kind", "")) != "water":
                    rpx, rpy = self._axial_to_pixel(int(rt.q), int(rt.r), size)
                    rcx = float(rpx) + off_x
                    rcy = float(rpy) + off_y
                    self.renderer.draw_circle_immediate((0, 0, 0), (int(rcx), int(rcy)), int(max(10, size * 0.32)), width=0, alpha=90, layer=180)
                    self.renderer.draw_text_immediate("🦹", int(rcx), int(rcy) - 1, font_size=int(max(14, size * 0.55)), color=(235, 235, 235), anchor_x="center", anchor_y="center", layer=181)
            except Exception:
                pass

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

    def update(self, dt: float) -> None:
        # ── Tick animations ──────────────────────────────────────────────────
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
                for _ in range(10):
                    self._particles.emit_firework(
                        _cx + random.randint(-150, 150), _cy + random.randint(-100, 100),
                        _FW_COLORS)
                self._flashes.append(ScreenFlash((255, 220, 80), 80, 1.2))
                self._text_pops.append(TextPopAnim(
                    f"🏆 {self._seat_label(self.winner)} wins!", _cx, _cy - 70,
                    (255, 220, 80), font_size=40))
                self._anim_fw_timer = 8.0
            if self._anim_fw_timer > 0:
                self._anim_fw_timer = max(0.0, self._anim_fw_timer - dt)
                if int(self._anim_fw_timer * 3) % 2 == 0:
                    _cx, _cy = self.width // 2, self.height // 2
                    self._particles.emit_firework(
                        _cx + random.randint(-150, 150), _cy + random.randint(-100, 100),
                        _FW_COLORS)
        except Exception:
            pass

        if not bool(self.dice_rolling):
            return

        now = float(time.time())
        if (now - float(self._dice_roll_start or 0.0)) < float(self._dice_roll_duration):
            return

        # Resolve the pending roll after animation completes.
        self.dice_rolling = False
        a, b = (None, None)
        try:
            if isinstance(self._pending_dice, tuple) and len(self._pending_dice) == 2:
                a = int(self._pending_dice[0])
                b = int(self._pending_dice[1])
        except Exception:
            a, b = (None, None)
        if not (isinstance(a, int) and isinstance(b, int)):
            self._pending_dice = None
            self._pending_roll_seat = None
            return

        self._last_dice = (int(a), int(b))
        self.last_roll = int(a + b)
        self._last_roll_time = float(time.time())

        # ── Dice result visual feedback ─────────────────────────────────────
        try:
            _cx, _cy = self.width // 2, self.height // 2
            if self.last_roll == 7:
                self._flashes.append(ScreenFlash((200, 80, 255), 40, 0.6))
                self._text_pops.append(TextPopAnim(
                    "\U0001f6a8 ROBBER!", _cx, _cy - 50, (200, 80, 255), font_size=32))
                self._particles.emit_sparkle(_cx, _cy, (200, 80, 255), count=20)
            else:
                self._text_pops.append(TextPopAnim(
                    f"\U0001f3b2 {self.last_roll}", _cx, _cy - 50, (255, 235, 120), font_size=28))
                self._particles.emit_sparkle(_cx, _cy, (255, 235, 120), count=12)
        except Exception:
            pass

        seat = int(self._pending_roll_seat) if isinstance(self._pending_roll_seat, int) else int(self.current_turn_seat or 0)
        self._pending_dice = None
        self._pending_roll_seat = None

        self.last_event = f"{self._seat_label(seat)} rolled {int(self.last_roll)} ({a}+{b})"
        self._rolled_this_turn = True
        if int(self.last_roll) == 7:
            self._handle_roll_seven(int(seat))
        else:
            self._distribute_resources_for_roll(int(self.last_roll))
            self._update_awards_and_winner()
        self._refresh_buttons()
