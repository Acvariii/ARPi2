from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

import pyglet
from pyglet import gl
import time
import math
from pathlib import Path

from config import PLAYER_COLORS
from core.player_selection import PlayerSelectionUI


class _WebButton:
    def __init__(self, text: str, enabled: bool = True):
        self.text = text
        self.enabled = enabled


@dataclass(frozen=True)
class TerritoryDef:
    tid: int
    name: str
    continent: str
    seed: Tuple[int, int]  # (x,y) in map pixel coords, origin bottom-left
    label_pos: Tuple[int, int]  # (x,y) in map pixel coords, origin bottom-left


def _clamp_int(v: int, lo: int, hi: int) -> int:
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


class RiskGame:
    """Risk (MVP) with a pixel map and owner-colored territory borders.

    Notes:
    - The map is raster-based (pixel-by-pixel). Territories are regions within a small pixel grid.
    - The wall board shows the map and highlights the *border pixels* of each territory
      using the owning player's color.
    - The Web UI is driven via `buttons` + `handle_click()` like other games.

    Gameplay loop (minimal but playable):
    - Turns: Reinforce -> Attack -> Fortify -> End Turn
    - Reinforcements: max(3, territories_owned // 3 + continent bonuses)
    - Attacks use Risk dice rules (defender wins ties).
    - Win condition: last remaining player.
    """

    # Ultra-HD raster for the wall display.
    # Note: this is heavier to build, but only rebuilds on ownership/border changes.
    MAP_W = 1920
    MAP_H = 1080

    def __init__(self, width: int, height: int, renderer=None):
        self.width = width
        self.height = height
        self.renderer = renderer

        self.state = "player_select"  # player_select | playing
        self.selection_ui = PlayerSelectionUI(width, height)

        self.active_players: List[int] = []
        self.eliminated_players: List[int] = []
        self.current_turn_seat: Optional[int] = None

        self.phase: str = "reinforce"  # reinforce|attack|fortify
        self.reinforcements_left: int = 0

        self.territories: List[TerritoryDef] = []
        self.adj: Dict[int, List[int]] = {}
        self.continent_bonus: Dict[str, int] = {}

        self.owner: Dict[int, int] = {}  # tid -> seat
        self.troops: Dict[int, int] = {}  # tid -> troops

        self.selected_from: Optional[int] = None
        self.selected_to: Optional[int] = None

        self.last_event: str = ""
        self.last_event_time: float = 0.0

        self.winner: Optional[int] = None

        self.buttons: Dict[int, Dict[str, _WebButton]] = {}

        self._seat_name_provider: Optional[Callable[[int], str]] = None

        # Pixel-map rendering caches
        self._map_tid: List[List[int]] = []  # [y][x] tid or -1 for water (origin bottom-left)
        self._land_mask: List[List[int]] = []  # [y][x] 1=land 0=water (origin bottom-left)
        self._border_pixels: Dict[int, List[Tuple[int, int]]] = {}
        self._tid_center: Dict[int, Tuple[int, int]] = {}

        self._base_image: Optional[pyglet.image.ImageData] = None
        self._base_sprite: Optional[pyglet.sprite.Sprite] = None

        self._fill_image: Optional[pyglet.image.ImageData] = None
        self._fill_sprite: Optional[pyglet.sprite.Sprite] = None
        self._fill_dirty: bool = True
        self._fill_last_hash: str = ""

        self._border_image: Optional[pyglet.image.ImageData] = None
        self._border_sprite: Optional[pyglet.sprite.Sprite] = None
        self._border_dirty: bool = True
        self._border_last_hash: str = ""

        # Visual FX / animations (map-coordinates, origin bottom-left)
        self._fx: List[Dict] = []
        self._last_attack_roll: Optional[Tuple[List[int], List[int], int, int]] = None  # (a_roll, d_roll, a_losses, d_losses)
        self._selection_pulse_t: float = 0.0

        # Immediate-drawn background (avoid covering sprites drawn earlier)
        self._bg_rect: Optional[pyglet.shapes.Rectangle] = None

        self._ensure_map()

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

    # --- Map definition ---

    def _tid_point(self, tid: int) -> Tuple[int, int]:
        p = self._tid_center.get(int(tid))
        if isinstance(p, tuple) and len(p) == 2:
            return int(p[0]), int(p[1])
        td = next((x for x in self.territories if int(x.tid) == int(tid)), None)
        if td is not None:
            return int(td.label_pos[0]), int(td.label_pos[1])
        return 0, 0

    def _lonlat_to_map_xy_bottom(self, lon: float, lat: float) -> Tuple[int, int]:
        """Equirectangular lon/lat -> map pixel coords (origin bottom-left)."""
        w, h = int(self.MAP_W), int(self.MAP_H)
        lat = max(-89.9999, min(89.9999, float(lat)))
        lon = float(lon)
        while lon < -180.0:
            lon += 360.0
        while lon >= 180.0:
            lon -= 360.0
        x = int((lon + 180.0) / 360.0 * (w - 1))
        y_top = int((90.0 - lat) / 180.0 * (h - 1))
        y = (h - 1) - y_top
        return _clamp_int(x, 0, w - 1), _clamp_int(y, 0, h - 1)

    def _ensure_map(self) -> None:
        if self.territories:
            return

        # Procedurally-generated, pixel-by-pixel "world" map:
        # - We draw continent silhouettes (landmask) using simple blobs.
        # - Territories are generated within each continent via nearest-seed assignment
        #   (Voronoi-like), which gives organic-looking internal borders.
        tid = 0
        t: List[TerritoryDef] = []

        def add_ll(name: str, continent: str, lon: float, lat: float):
            nonlocal tid
            seed = self._lonlat_to_map_xy_bottom(float(lon), float(lat))
            t.append(TerritoryDef(tid=tid, name=name, continent=continent, seed=seed, label_pos=seed))
            tid += 1

        # Seeds now come from lon/lat so they match the real map coastline.
        # (Approximate points near territory centers; gameplay-oriented, not exact borders.)
        # --- North America (9) ---
        add_ll("Alaska", "North America", -150, 64)
        add_ll("NW Territory", "North America", -115, 64)
        add_ll("Greenland", "North America", -42, 72)
        add_ll("Alberta", "North America", -113, 54)
        add_ll("Ontario", "North America", -85, 50)
        add_ll("Quebec", "North America", -71, 52)
        add_ll("Western US", "North America", -118, 39)
        add_ll("Eastern US", "North America", -82, 38)
        add_ll("Central America", "North America", -90, 15)

        # --- South America (4) ---
        add_ll("Venezuela", "South America", -66, 7)
        add_ll("Peru", "South America", -75, -10)
        add_ll("Brazil", "South America", -52, -10)
        add_ll("Argentina", "South America", -64, -38)

        # --- Europe (7) ---
        add_ll("Iceland", "Europe", -18, 65)
        add_ll("Great Britain", "Europe", -2, 54)
        add_ll("Scandinavia", "Europe", 16, 63)
        add_ll("Northern Europe", "Europe", 16, 52)
        add_ll("Western Europe", "Europe", 2, 46)
        add_ll("Southern Europe", "Europe", 18, 41)
        add_ll("Ukraine", "Europe", 32, 49)

        # --- Africa (6) ---
        add_ll("North Africa", "Africa", 2, 28)
        add_ll("Egypt", "Africa", 30, 27)
        add_ll("East Africa", "Africa", 38, 0)
        add_ll("Congo", "Africa", 18, -2)
        add_ll("South Africa", "Africa", 24, -29)
        add_ll("Madagascar", "Africa", 47, -19)

        # --- Asia (12) ---
        add_ll("Ural", "Asia", 60, 58)
        add_ll("Siberia", "Asia", 100, 62)
        add_ll("Yakutsk", "Asia", 130, 62)
        add_ll("Kamchatka", "Asia", 160, 58)
        add_ll("Japan", "Asia", 138, 37)
        add_ll("Afghanistan", "Asia", 66, 33)
        add_ll("Middle East", "Asia", 45, 29)
        add_ll("India", "Asia", 78, 21)
        add_ll("China", "Asia", 105, 34)
        add_ll("SE Asia", "Asia", 105, 12)
        add_ll("Irkutsk", "Asia", 105, 52)
        add_ll("Mongolia", "Asia", 104, 46)

        # --- Australia (4) ---
        add_ll("Indonesia", "Australia", 113, -2)
        add_ll("New Guinea", "Australia", 145, -6)
        add_ll("Western Australia", "Australia", 121, -25)
        add_ll("Eastern Australia", "Australia", 149, -27)

        self.territories = t

        # Classic-ish continent bonuses (kept simple).
        self.continent_bonus = {
            "North America": 5,
            "South America": 2,
            "Europe": 5,
            "Africa": 3,
            "Asia": 7,
            "Australia": 2,
        }

        # Rasterize world and derive adjacency from the pixel map.
        self._rasterize_map()

    def _rasterize_map(self) -> None:
        w, h = int(self.MAP_W), int(self.MAP_H)

        # Prefer Natural Earth 10m shapefiles if present (real world coastline).
        if self._try_rasterize_natural_earth(w, h):
            self._build_base_image()
            self._border_dirty = True
            self._fill_dirty = True
            return

        # Scale helpers for the old 320x180-authored blob parameters.
        sx = float(w) / 320.0
        sy = float(h) / 180.0

        def _sx(v: float) -> float:
            return float(v) * sx

        def _sy(v: float) -> float:
            return float(v) * sy

        # Build continent masks (bytearrays for speed). Origin bottom-left (y=0 is bottom).
        masks: Dict[str, List[bytearray]] = {}

        def _new_mask() -> List[bytearray]:
            return [bytearray(w) for _ in range(h)]

        def _paint_ellipse(mask: List[bytearray], cx: float, cy: float, rx: float, ry: float, val: int = 1) -> None:
            if rx <= 0 or ry <= 0:
                return
            x0 = _clamp_int(int(cx - rx - 1), 0, w - 1)
            x1 = _clamp_int(int(cx + rx + 1), 0, w - 1)
            y0 = _clamp_int(int(cy - ry - 1), 0, h - 1)
            y1 = _clamp_int(int(cy + ry + 1), 0, h - 1)
            inv_rx2 = 1.0 / float(rx * rx)
            inv_ry2 = 1.0 / float(ry * ry)
            for yy in range(y0, y1 + 1):
                dy = float(yy) - float(cy)
                dy2 = dy * dy * inv_ry2
                row = mask[yy]
                for xx in range(x0, x1 + 1):
                    dx = float(xx) - float(cx)
                    if dx * dx * inv_rx2 + dy2 <= 1.0:
                        row[xx] = int(val)

        def _smooth(mask: List[bytearray], iters: int = 2) -> List[bytearray]:
            cur = mask
            for _ in range(max(0, int(iters))):
                nxt = _new_mask()
                for yy in range(h):
                    for xx in range(w):
                        # Count 8-neighborhood
                        cnt = 0
                        for oy in (-1, 0, 1):
                            ny = yy + oy
                            if ny < 0 or ny >= h:
                                continue
                            row = cur[ny]
                            for ox in (-1, 0, 1):
                                nx = xx + ox
                                if nx < 0 or nx >= w:
                                    continue
                                if row[nx]:
                                    cnt += 1
                        # Threshold keeps blobby, coast-like edges
                        if cnt >= 5:
                            nxt[yy][xx] = 1
                cur = nxt
            return cur

        # Build a more world-like silhouette:
        # - Americas separate landmasses
        # - Eurasia is one continuous landmass
        # - Africa connects to Eurasia at the north-east
        # - Australia + island chains
        # - Antarctica strip
        masks["North America"] = _new_mask()
        # Alaska + Canada
        _paint_ellipse(masks["North America"], _sx(48), _sy(150), _sx(58), _sy(34))
        _paint_ellipse(masks["North America"], _sx(86), _sy(154), _sx(70), _sy(36))
        _paint_ellipse(masks["North America"], _sx(110), _sy(136), _sx(64), _sy(34))
        # USA bulk + Mexico
        _paint_ellipse(masks["North America"], _sx(106), _sy(112), _sx(56), _sy(28))
        _paint_ellipse(masks["North America"], _sx(118), _sy(92), _sx(22), _sy(18))
        # Florida-ish
        _paint_ellipse(masks["North America"], _sx(132), _sy(92), _sx(10), _sy(12))
        # Greenland-ish island
        _paint_ellipse(masks["North America"], _sx(154), _sy(164), _sx(26), _sy(14))
        # Hudson bay carve
        _paint_ellipse(masks["North America"], _sx(112), _sy(142), _sx(18), _sy(12), val=0)
        masks["North America"] = _smooth(masks["North America"], iters=3)

        masks["South America"] = _new_mask()
        _paint_ellipse(masks["South America"], _sx(148), _sy(66), _sx(28), _sy(38))
        _paint_ellipse(masks["South America"], _sx(150), _sy(40), _sx(22), _sy(28))
        _paint_ellipse(masks["South America"], _sx(142), _sy(24), _sx(18), _sy(22))
        # east bulge
        _paint_ellipse(masks["South America"], _sx(162), _sy(58), _sx(16), _sy(20))
        # taper southern tip
        _paint_ellipse(masks["South America"], _sx(160), _sy(16), _sx(12), _sy(10), val=0)
        masks["South America"] = _smooth(masks["South America"], iters=3)

        # Eurasia landmass (used for both Europe and Asia continent assignment)
        masks["Eurasia"] = _new_mask()
        # Europe core
        _paint_ellipse(masks["Eurasia"], _sx(214), _sy(140), _sx(42), _sy(20))
        _paint_ellipse(masks["Eurasia"], _sx(236), _sy(146), _sx(48), _sy(22))
        # Scandinavia bump
        _paint_ellipse(masks["Eurasia"], _sx(232), _sy(160), _sx(24), _sy(18))
        # Western Russia bridge to Asia
        _paint_ellipse(masks["Eurasia"], _sx(268), _sy(142), _sx(46), _sy(24))
        # Asia bulk
        _paint_ellipse(masks["Eurasia"], _sx(296), _sy(136), _sx(86), _sy(54))
        _paint_ellipse(masks["Eurasia"], _sx(316), _sy(162), _sx(54), _sy(28))
        # China / SE Asia peninsula
        _paint_ellipse(masks["Eurasia"], _sx(304), _sy(108), _sx(52), _sy(26))
        _paint_ellipse(masks["Eurasia"], _sx(296), _sy(92), _sx(24), _sy(18))  # India-ish
        # Japan-ish island chain will be handled as Asia islands below
        # carve Mediterranean + Black Sea-ish water bands
        _paint_ellipse(masks["Eurasia"], _sx(244), _sy(112), _sx(56), _sy(12), val=0)
        _paint_ellipse(masks["Eurasia"], _sx(262), _sy(124), _sx(14), _sy(10), val=0)
        masks["Eurasia"] = _smooth(masks["Eurasia"], iters=3)

        masks["Africa"] = _new_mask()
        # North Africa + Sahara
        _paint_ellipse(masks["Africa"], _sx(238), _sy(88), _sx(42), _sy(30))
        # West Africa
        _paint_ellipse(masks["Africa"], _sx(226), _sy(64), _sx(34), _sy(34))
        # East Africa + horn
        _paint_ellipse(masks["Africa"], _sx(258), _sy(66), _sx(30), _sy(40))
        _paint_ellipse(masks["Africa"], _sx(270), _sy(66), _sx(18), _sy(22))
        # South Africa
        _paint_ellipse(masks["Africa"], _sx(246), _sy(30), _sx(34), _sy(26))
        # Madagascar
        _paint_ellipse(masks["Africa"], _sx(276), _sy(28), _sx(10), _sy(12))
        masks["Africa"] = _smooth(masks["Africa"], iters=3)

        masks["Australia"] = _new_mask()
        _paint_ellipse(masks["Australia"], _sx(304), _sy(34), _sx(28), _sy(18))
        _paint_ellipse(masks["Australia"], _sx(318), _sy(32), _sx(20), _sy(16))
        _paint_ellipse(masks["Australia"], _sx(312), _sy(60), _sx(18), _sy(12))  # New Guinea-ish
        # Indonesia arc
        _paint_ellipse(masks["Australia"], _sx(292), _sy(70), _sx(18), _sy(10))
        _paint_ellipse(masks["Australia"], _sx(304), _sy(72), _sx(16), _sy(10))
        masks["Australia"] = _smooth(masks["Australia"], iters=2)

        # Additional small islands (Asia/Japan/UK) as their own masks, then assigned by continent rules.
        masks["Islands"] = _new_mask()
        # UK / Ireland-ish
        _paint_ellipse(masks["Islands"], _sx(200), _sy(136), _sx(10), _sy(8))
        # Japan-ish
        _paint_ellipse(masks["Islands"], _sx(304), _sy(126), _sx(12), _sy(10))
        _paint_ellipse(masks["Islands"], _sx(312), _sy(120), _sx(10), _sy(8))
        masks["Islands"] = _smooth(masks["Islands"], iters=1)

        # Antarctica strip
        masks["Antarctica"] = _new_mask()
        _paint_ellipse(masks["Antarctica"], _sx(160), _sy(6), _sx(220), _sy(8))
        _paint_ellipse(masks["Antarctica"], _sx(240), _sy(7), _sx(240), _sy(7))
        masks["Antarctica"] = _smooth(masks["Antarctica"], iters=1)

        # Assemble global land and continent assignment.
        land = _new_mask()
        cont_at: List[List[Optional[str]]] = [[None for _ in range(w)] for _ in range(h)]

        def _apply_mask(mask: List[bytearray], cont_name: Optional[str]) -> None:
            for yy in range(h):
                row_m = mask[yy]
                row_land = land[yy]
                row_cont = cont_at[yy]
                for xx in range(w):
                    if row_m[xx] and not row_land[xx]:
                        row_land[xx] = 1
                        row_cont[xx] = cont_name

        # Base landmasses
        _apply_mask(masks["North America"], "North America")
        _apply_mask(masks["South America"], "South America")
        _apply_mask(masks["Eurasia"], "Eurasia")
        _apply_mask(masks["Africa"], "Africa")
        _apply_mask(masks["Australia"], "Australia")
        _apply_mask(masks["Islands"], "Eurasia")
        _apply_mask(masks["Antarctica"], None)  # land but no continent/territories

        # Enforce key ocean gaps so continents don't visually touch.
        # This intentionally creates clear water separation similar to an atlas projection.
        atl_x0 = int(_sx(170))
        atl_x1 = int(_sx(208))
        ber_x0 = int(_sx(306))
        ber_x1 = int(_sx(318))
        y_min = int(_sy(18))
        y_max = int(_sy(176))

        def _carve_vertical_channel(x0: int, x1: int, y0: int, y1: int) -> None:
            x0 = _clamp_int(int(x0), 0, w - 1)
            x1 = _clamp_int(int(x1), 0, w - 1)
            y0 = _clamp_int(int(y0), 0, h - 1)
            y1 = _clamp_int(int(y1), 0, h - 1)
            if x1 < x0:
                x0, x1 = x1, x0
            if y1 < y0:
                y0, y1 = y1, y0
            for yy in range(y0, y1 + 1):
                row_land = land[yy]
                row_cont = cont_at[yy]
                for xx in range(x0, x1 + 1):
                    row_land[xx] = 0
                    row_cont[xx] = None

        # Atlantic: separates Americas from Europe/Africa.
        _carve_vertical_channel(atl_x0, atl_x1, int(_sy(34)), y_max)
        # Bering: keeps Alaska from visually touching Asia; adjacency remains via manual link.
        _carve_vertical_channel(ber_x0, ber_x1, int(_sy(120)), y_max)

        # Fix up Eurasia pixels into Europe vs Asia using a rough longitudinal split.
        # (Still continuous land, but different continent bonuses/territory pools.)
        euro_split = int(_sx(252))
        for yy in range(h):
            row_cont = cont_at[yy]
            for xx in range(w):
                if row_cont[xx] != "Eurasia":
                    continue
                # Europe higher latitudes and west side.
                if xx < euro_split and yy > int(_sy(98)):
                    row_cont[xx] = "Europe"
                else:
                    row_cont[xx] = "Asia"

        # Antarctica: keep as land (for ice caps), but not selectable.
        for yy in range(h):
            row_m = masks["Antarctica"][yy]
            row_land = land[yy]
            for xx in range(w):
                if row_m[xx]:
                    row_land[xx] = 1

        # Voronoi-like assignment: within each continent, assign each land pixel to the nearest seed.
        seeds_by_cont: Dict[str, List[Tuple[int, int, int]]] = {}
        for td in self.territories:
            seeds_by_cont.setdefault(td.continent, []).append((int(td.tid), int(td.seed[0]), int(td.seed[1])))

        tid_map = [[-1 for _ in range(w)] for _ in range(h)]
        for yy in range(h):
            row_cont = cont_at[yy]
            for xx in range(w):
                cont = row_cont[xx]
                if cont is None:
                    continue
                seeds = seeds_by_cont.get(cont) or []
                if not seeds:
                    continue
                best_tid = -1
                best_d2 = 10**18
                for tid0, sx, sy in seeds:
                    dx = int(xx) - int(sx)
                    dy = int(yy) - int(sy)
                    d2 = dx * dx + dy * dy
                    if d2 < best_d2:
                        best_d2 = d2
                        best_tid = int(tid0)
                tid_map[yy][xx] = int(best_tid)

        self._map_tid = tid_map

        # In the procedural fallback, treat any non-negative tid pixel as land.
        self._land_mask = [[1 if tid_map[y][x] >= 0 else 0 for x in range(w)] for y in range(h)]

        # Compute territory centers from assigned pixels.
        sums: Dict[int, Tuple[int, int, int]] = {}  # tid -> (sx, sy, n)
        for td in self.territories:
            sums[int(td.tid)] = (0, 0, 0)
        for yy in range(h):
            row = tid_map[yy]
            for xx in range(w):
                t0 = int(row[xx])
                if t0 < 0:
                    continue
                sx, sy, n = sums.get(t0, (0, 0, 0))
                sums[t0] = (sx + int(xx), sy + int(yy), n + 1)
        # First pass: centroid.
        centroids: Dict[int, Tuple[int, int]] = {}
        for td in self.territories:
            t0 = int(td.tid)
            sx0, sy0, n = sums.get(t0, (0, 0, 0))
            if n > 0:
                centroids[t0] = (int(sx0 // n), int(sy0 // n))
            else:
                centroids[t0] = (int(td.seed[0]), int(td.seed[1]))

        # Second pass: choose an interior pixel nearest the centroid.
        # This prevents markers from landing in a neighboring territory due to
        # centroid drift toward thin borders/coastlines.
        best_pos: Dict[int, Tuple[int, int]] = {int(td.tid): (int(td.seed[0]), int(td.seed[1])) for td in self.territories}
        best_d2: Dict[int, int] = {int(td.tid): 10**18 for td in self.territories}

        for yy in range(h):
            row = tid_map[yy]
            for xx in range(w):
                t0 = int(row[xx])
                if t0 < 0:
                    continue
                cx, cy = centroids.get(t0, (xx, yy))
                dx = int(xx) - int(cx)
                dy = int(yy) - int(cy)
                d2 = dx * dx + dy * dy

                # Penalize border pixels to prefer interior placement.
                border = False
                for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = xx + ox, yy + oy
                    if nx < 0 or nx >= w or ny < 0 or ny >= h:
                        border = True
                        break
                    if int(tid_map[ny][nx]) != t0:
                        border = True
                        break
                if border:
                    d2 += 5000

                if d2 < best_d2.get(t0, 10**18):
                    best_d2[t0] = int(d2)
                    best_pos[t0] = (int(xx), int(yy))

        self._tid_center = {int(k): (int(v[0]), int(v[1])) for k, v in best_pos.items()}

        # Internal border pixels per territory (for owner-colored overlay).
        borders: Dict[int, List[Tuple[int, int]]] = {td.tid: [] for td in self.territories}
        for yy in range(h):
            for xx in range(w):
                here = int(tid_map[yy][xx])
                if here < 0:
                    continue
                is_border = False
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = xx + dx, yy + dy
                    if nx < 0 or nx >= w or ny < 0 or ny >= h:
                        continue
                    oth = int(tid_map[ny][nx])
                    if oth >= 0 and oth != here:
                        is_border = True
                        break
                if is_border:
                    borders[here].append((int(xx), int(yy)))
        self._border_pixels = borders

        # Derive adjacency from raster borders.
        adj_sets: Dict[int, set] = {int(td.tid): set() for td in self.territories}
        for yy in range(h):
            row = tid_map[yy]
            for xx in range(w):
                here = int(row[xx])
                if here < 0:
                    continue
                if xx + 1 < w:
                    oth = int(row[xx + 1])
                    if oth >= 0 and oth != here:
                        adj_sets[here].add(oth)
                        adj_sets[oth].add(here)
                if yy + 1 < h:
                    oth = int(tid_map[yy + 1][xx])
                    if oth >= 0 and oth != here:
                        adj_sets[here].add(oth)
                        adj_sets[oth].add(here)

        # Add a few classic cross-ocean links explicitly.
        name_to_tid: Dict[str, int] = {str(td.name): int(td.tid) for td in self.territories}

        def _link_by_name(a: str, b: str) -> None:
            ta = name_to_tid.get(a)
            tb = name_to_tid.get(b)
            if isinstance(ta, int) and isinstance(tb, int):
                adj_sets[int(ta)].add(int(tb))
                adj_sets[int(tb)].add(int(ta))

        _link_by_name("Alaska", "Kamchatka")
        _link_by_name("Greenland", "Iceland")
        _link_by_name("Brazil", "North Africa")
        _link_by_name("Southern Europe", "Egypt")
        _link_by_name("Southern Europe", "North Africa")
        _link_by_name("Middle East", "Egypt")
        _link_by_name("Middle East", "East Africa")
        _link_by_name("Middle East", "India")
        _link_by_name("Middle East", "Afghanistan")
        _link_by_name("Middle East", "Southern Europe")
        _link_by_name("Indonesia", "SE Asia")
        _link_by_name("Indonesia", "New Guinea")
        _link_by_name("New Guinea", "Eastern Australia")

        self.adj = {int(k): sorted(int(x) for x in v) for k, v in adj_sets.items()}

        self._build_base_image()
        self._border_dirty = True
        self._fill_dirty = True

    def _try_rasterize_natural_earth(self, w: int, h: int) -> bool:
        """Rasterize a real-world land mask + continent regions from Natural Earth shapefiles.

        Expected files (from the user's 10m_physical.zip):
        - games/risk/ne_10m_physical/ne_10m_ocean.shp
        - games/risk/ne_10m_physical/ne_10m_geography_regions_polys.shp
        - games/risk/ne_10m_physical/ne_10m_lakes.shp (optional; treated as land)

        Returns True on success; False falls back to procedural map.
        """

        base = (Path(__file__).parent / "ne_10m_physical").resolve()
        ocean_shp = (base / "ne_10m_ocean.shp")
        lakes_candidates = [base / "ne_10m_lakes.shp"]
        regions_shp = base / "ne_10m_geography_regions_polys.shp"
        if (not ocean_shp.exists()) or (not regions_shp.exists()):
            return False

        try:
            import numpy as np
            import cv2
            import shapefile  # pyshp
        except Exception:
            return False

        # Arrays in image coordinates (origin TOP-left) for cv2.
        # Rasterize into a 3×-wide canvas to safely handle dateline-crossing polygons,
        # then fold back to width w.
        cw = int(w * 3)
        land_img3 = np.zeros((h, cw), dtype=np.uint8)
        cont_img3 = np.zeros((h, cw), dtype=np.uint8)

        # Projection: equirectangular (longitude unwrapped before mapping).
        def lonlat_to_xy_top_canvas(lon_unwrapped: float, lat: float) -> Tuple[int, int]:
            lat = max(-89.9999, min(89.9999, float(lat)))
            lon_unwrapped = float(lon_unwrapped)
            # Map [-180..180] to the middle third [w..2w), allowing spill into [0..w) and [2w..3w)
            x = int(((lon_unwrapped + 180.0) / 360.0) * (w - 1) + w)
            y = int(((90.0 - lat) / 180.0) * (h - 1))
            return _clamp_int(x, 0, cw - 1), _clamp_int(y, 0, h - 1)

        def _unwrap_ring_longitudes(ring: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
            # Convert lon sequence into a continuous (unwrapped) series so dateline crossings
            # don't create huge jumps that cause fill chords across the map.
            if not ring:
                return ring
            out: List[Tuple[float, float]] = []
            offset = 0.0
            prev: Optional[float] = None
            for lon, lat in ring:
                lon = float(lon)
                lat = float(lat)
                adj = lon + offset
                if prev is not None:
                    while (adj - prev) > 180.0:
                        offset -= 360.0
                        adj = lon + offset
                    while (adj - prev) < -180.0:
                        offset += 360.0
                        adj = lon + offset
                prev = adj
                out.append((adj, lat))
            # Recentre to keep the polygon close to [-180, 180] overall.
            try:
                lons = [p[0] for p in out]
                lons_sorted = sorted(lons)
                med = float(lons_sorted[len(lons_sorted) // 2])
                k = int(round(med / 360.0))
                if k != 0:
                    shift = 360.0 * float(k)
                    out = [(float(lon) - shift, float(lat)) for lon, lat in out]
            except Exception:
                pass
            return out

        def shape_parts_to_rings(s) -> List[List[Tuple[float, float]]]:
            # Returns list of rings (each a list of lon/lat points).
            pts = list(s.points or [])
            parts = list(s.parts or [0])
            parts.append(len(pts))
            out: List[List[Tuple[float, float]]] = []
            for a, b in zip(parts, parts[1:]):
                ring = pts[a:b]
                if len(ring) >= 3:
                    out.append([(float(p[0]), float(p[1])) for p in ring])
            return out

        def rings_to_cv_polys(rings: List[List[Tuple[float, float]]]) -> List[np.ndarray]:
            polys: List[np.ndarray] = []
            for ring in rings:
                # Convert to pixel coords.
                unr = _unwrap_ring_longitudes(ring)
                arr = np.array([lonlat_to_xy_top_canvas(lon, lat) for lon, lat in unr], dtype=np.int32)
                if arr.shape[0] >= 3:
                    polys.append(arr)
            return polys

        def _signed_area(poly: "np.ndarray") -> float:
            # poly: Nx2 int32
            if poly is None or len(poly) < 3:
                return 0.0
            x = poly[:, 0].astype(np.float64)
            y = poly[:, 1].astype(np.float64)
            return float(0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))

        def _classify_outers_and_holes(polys: List["np.ndarray"]) -> Tuple[List["np.ndarray"], List["np.ndarray"]]:
            # Natural Earth polygon parts may not have consistent winding.
            # Determine holes by containment (a ring inside any already-accepted outer is a hole).
            if not polys:
                return [], []
            areas = [abs(_signed_area(p)) for p in polys]
            order = sorted(range(len(polys)), key=lambda i: areas[i], reverse=True)
            outers: List[np.ndarray] = []
            holes: List[np.ndarray] = []
            for idx in order:
                p = polys[idx]
                if p is None or len(p) < 3:
                    continue
                if not outers:
                    outers.append(p)
                    continue
                # Use the first vertex as a representative point.
                pt = (float(p[0][0]), float(p[0][1]))
                inside_any = False
                for outer in outers:
                    try:
                        # pointPolygonTest expects contour in Nx1x2 or Nx2.
                        res = cv2.pointPolygonTest(outer, pt, False)
                        if res >= 0:
                            inside_any = True
                            break
                    except Exception:
                        continue
                if inside_any:
                    holes.append(p)
                else:
                    outers.append(p)
            return outers, holes

        # 1) Build land mask from ocean polygons.
        # Per user request, lakes should be treated as land, so we OR lakes into the land mask.
        land_img: Optional["np.ndarray"] = None
        try:
            r_ocean = shapefile.Reader(str(ocean_shp))
            if int(getattr(r_ocean, "shapeType", 0) or 0) not in (5, 15, 25):
                return False
            ocean_img3 = np.zeros((h, cw), dtype=np.uint8)
            for shp in r_ocean.shapes():
                rings = shape_parts_to_rings(shp)
                polys = rings_to_cv_polys(rings)
                if not polys:
                    continue
                outers, holes = _classify_outers_and_holes(polys)
                if outers:
                    cv2.fillPoly(ocean_img3, outers, 255)
                if holes:
                    cv2.fillPoly(ocean_img3, holes, 0)

            # Fold ocean to the real map width, then land is wherever ocean is NOT present.
            oc_center = ocean_img3[:, w : 2 * w]
            oc_left = ocean_img3[:, 0:w]
            oc_right = ocean_img3[:, 2 * w : 3 * w]
            ocean_img = np.maximum(oc_center, np.maximum(oc_left, oc_right))
            land_img = (ocean_img == 0).astype(np.uint8) * 255

            # Lakes as land (optional file).
            lp = lakes_candidates[0]
            if lp.exists():
                lakes_img3 = np.zeros((h, cw), dtype=np.uint8)
                try:
                    r_lake = shapefile.Reader(str(lp))
                    if int(getattr(r_lake, "shapeType", 0) or 0) in (5, 15, 25):
                        for shp in r_lake.shapes():
                            rings = shape_parts_to_rings(shp)
                            polys = rings_to_cv_polys(rings)
                            if not polys:
                                continue
                            outers, holes = _classify_outers_and_holes(polys)
                            if outers:
                                cv2.fillPoly(lakes_img3, outers, 255)
                            if holes:
                                cv2.fillPoly(lakes_img3, holes, 0)
                except Exception:
                    pass
                lk_center = lakes_img3[:, w : 2 * w]
                lk_left = lakes_img3[:, 0:w]
                lk_right = lakes_img3[:, 2 * w : 3 * w]
                lakes_img = np.maximum(lk_center, np.maximum(lk_left, lk_right))
                land_img[lakes_img != 0] = 255
        except Exception:
            return False

        # 2) Rasterize continent regions (REGION field)
        try:
            r_reg = shapefile.Reader(str(regions_shp))
            # Field indices
            fields = [f[0] for f in r_reg.fields[1:]]
            try:
                region_idx = fields.index("REGION")
            except ValueError:
                region_idx = None

            if region_idx is None:
                return False

            # Map Natural Earth REGION -> our continents
            region_to_cont = {
                "North America": "North America",
                "South America": "South America",
                "Europe": "Europe",
                "Africa": "Africa",
                "Asia": "Asia",
                "Oceania": "Australia",
            }
            cont_code = {
                "North America": 1,
                "South America": 2,
                "Europe": 3,
                "Africa": 4,
                "Asia": 5,
                "Australia": 6,
            }

            for shp, rec in zip(r_reg.shapes(), r_reg.records()):
                try:
                    reg = str(rec[region_idx] or "").strip()
                except Exception:
                    reg = ""
                cont = region_to_cont.get(reg)
                if not cont:
                    continue
                code = int(cont_code[cont])
                rings = shape_parts_to_rings(shp)
                polys = rings_to_cv_polys(rings)
                if not polys:
                    continue
                outers, holes = _classify_outers_and_holes(polys)
                if outers:
                    cv2.fillPoly(cont_img3, outers, code)
                if holes:
                    cv2.fillPoly(cont_img3, holes, 0)
        except Exception:
            return False

        # Fold 3× canvas back to width w.
        if land_img is None:
            land_center = land_img3[:, w : 2 * w]
            land_left = land_img3[:, 0:w]
            land_right = land_img3[:, 2 * w : 3 * w]
            land_img = np.maximum(land_center, np.maximum(land_left, land_right))

        cont_center = cont_img3[:, w : 2 * w]
        cont_left = cont_img3[:, 0:w]
        cont_right = cont_img3[:, 2 * w : 3 * w]
        cont_img = cont_center.copy()
        m = cont_img == 0
        cont_img[m] = cont_left[m]
        m = cont_img == 0
        cont_img[m] = cont_right[m]

        # Convert images (top-left origin) to our internal bottom-left row ordering.
        land_bottom = land_img[::-1, :]
        cont_bottom = cont_img[::-1, :]

        # Assign pixels to territories within their continent via nearest seed.
        # First, nudge any seed that ended up in water / wrong continent to the nearest valid pixel.
        cont_code_for = {
            "North America": 1,
            "South America": 2,
            "Europe": 3,
            "Africa": 4,
            "Asia": 5,
            "Australia": 6,
        }

        def _find_nearest_valid_seed(x0: int, y0: int, need_code: int) -> Tuple[int, int]:
            x0 = _clamp_int(int(x0), 0, w - 1)
            y0 = _clamp_int(int(y0), 0, h - 1)
            if int(land_bottom[y0][x0]) != 0 and int(cont_bottom[y0][x0]) == int(need_code):
                return x0, y0
            max_r = 180
            for r in range(1, max_r + 1):
                x_min = max(0, x0 - r)
                x_max = min(w - 1, x0 + r)
                y_min = max(0, y0 - r)
                y_max = min(h - 1, y0 + r)
                # scan perimeter
                for x in range(x_min, x_max + 1):
                    for y in (y_min, y_max):
                        if int(land_bottom[y][x]) != 0 and int(cont_bottom[y][x]) == int(need_code):
                            return int(x), int(y)
                for y in range(y_min + 1, y_max):
                    for x in (x_min, x_max):
                        if int(land_bottom[y][x]) != 0 and int(cont_bottom[y][x]) == int(need_code):
                            return int(x), int(y)
            return x0, y0

        def _find_nearest_free_valid_seed(x0: int, y0: int, need_code: int, used: "set") -> Tuple[int, int]:
            x0, y0 = _find_nearest_valid_seed(x0, y0, need_code)
            if (int(x0), int(y0)) not in used:
                return int(x0), int(y0)
            max_r = 260
            for r in range(1, max_r + 1):
                x_min = max(0, int(x0) - r)
                x_max = min(w - 1, int(x0) + r)
                y_min = max(0, int(y0) - r)
                y_max = min(h - 1, int(y0) + r)
                for x in range(x_min, x_max + 1):
                    for y in (y_min, y_max):
                        if (int(x), int(y)) in used:
                            continue
                        if int(land_bottom[y][x]) != 0 and int(cont_bottom[y][x]) == int(need_code):
                            return int(x), int(y)
                for y in range(y_min + 1, y_max):
                    for x in (x_min, x_max):
                        if (int(x), int(y)) in used:
                            continue
                        if int(land_bottom[y][x]) != 0 and int(cont_bottom[y][x]) == int(need_code):
                            return int(x), int(y)
            return int(x0), int(y0)

        seeds_by_cont: Dict[str, List[Tuple[int, int, int]]] = {}
        used_by_cont: Dict[str, set] = {}
        for td in self.territories:
            need = int(cont_code_for.get(td.continent, 0) or 0)
            sx0, sy0 = int(td.seed[0]), int(td.seed[1])
            if need:
                used = used_by_cont.setdefault(str(td.continent), set())
                sx1, sy1 = _find_nearest_free_valid_seed(sx0, sy0, need, used)
                used.add((int(sx1), int(sy1)))
            else:
                sx1, sy1 = (sx0, sy0)
            seeds_by_cont.setdefault(td.continent, []).append((int(td.tid), int(sx1), int(sy1)))

        code_to_cont = {
            1: "North America",
            2: "South America",
            3: "Europe",
            4: "Africa",
            5: "Asia",
            6: "Australia",
        }

        tid_map: List[List[int]] = [[-1 for _ in range(w)] for _ in range(h)]
        land_mask: List[List[int]] = [[0 for _ in range(w)] for _ in range(h)]

        # Precompute seed lists for faster loop.
        for y in range(h):
            land_row = land_bottom[y]
            cont_row = cont_bottom[y]
            out_row = tid_map[y]
            lm_row = land_mask[y]
            for x in range(w):
                if int(land_row[x]) == 0:
                    continue
                lm_row[x] = 1
                cont = code_to_cont.get(int(cont_row[x]))
                if cont is None:
                    # land (e.g. Antarctica) but no Risk territory
                    continue
                seeds = seeds_by_cont.get(cont) or []
                if not seeds:
                    continue
                best_tid = -1
                best_d2 = 10**18
                for tid0, sx0, sy0 in seeds:
                    dx = int(x) - int(sx0)
                    dy = int(y) - int(sy0)
                    d2 = dx * dx + dy * dy
                    if d2 < best_d2:
                        best_d2 = d2
                        best_tid = int(tid0)
                out_row[x] = int(best_tid)

        self._map_tid = tid_map
        self._land_mask = land_mask

        # Internal borders per territory.
        borders: Dict[int, List[Tuple[int, int]]] = {td.tid: [] for td in self.territories}
        for yy in range(h):
            for xx in range(w):
                here = int(tid_map[yy][xx])
                if here < 0:
                    continue
                is_border = False
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = xx + dx, yy + dy
                    if nx < 0 or nx >= w or ny < 0 or ny >= h:
                        continue
                    oth = int(tid_map[ny][nx])
                    if oth >= 0 and oth != here:
                        is_border = True
                        break
                if is_border:
                    borders[here].append((int(xx), int(yy)))
        self._border_pixels = borders

        # Territory label points: interior pixel nearest centroid (reuse existing logic).
        sums: Dict[int, Tuple[int, int, int]] = {int(td.tid): (0, 0, 0) for td in self.territories}
        for yy in range(h):
            row = tid_map[yy]
            for xx in range(w):
                t0 = int(row[xx])
                if t0 < 0:
                    continue
                sx0, sy0, n0 = sums.get(t0, (0, 0, 0))
                sums[t0] = (sx0 + int(xx), sy0 + int(yy), n0 + 1)

        centroids: Dict[int, Tuple[int, int]] = {}
        for td in self.territories:
            t0 = int(td.tid)
            sx0, sy0, n0 = sums.get(t0, (0, 0, 0))
            if n0 > 0:
                centroids[t0] = (int(sx0 // n0), int(sy0 // n0))
            else:
                centroids[t0] = (int(td.seed[0]), int(td.seed[1]))

        best_pos: Dict[int, Tuple[int, int]] = {int(td.tid): (int(td.seed[0]), int(td.seed[1])) for td in self.territories}
        best_d2: Dict[int, int] = {int(td.tid): 10**18 for td in self.territories}

        for yy in range(h):
            row = tid_map[yy]
            for xx in range(w):
                t0 = int(row[xx])
                if t0 < 0:
                    continue
                cx, cy = centroids.get(t0, (xx, yy))
                dx = int(xx) - int(cx)
                dy = int(yy) - int(cy)
                d2 = dx * dx + dy * dy
                # Penalize border pixels.
                border = False
                for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = xx + ox, yy + oy
                    if nx < 0 or nx >= w or ny < 0 or ny >= h:
                        border = True
                        break
                    if int(tid_map[ny][nx]) != t0:
                        border = True
                        break
                if border:
                    d2 += 5000
                if d2 < best_d2.get(t0, 10**18):
                    best_d2[t0] = int(d2)
                    best_pos[t0] = (int(xx), int(yy))
        self._tid_center = {int(k): (int(v[0]), int(v[1])) for k, v in best_pos.items()}

        # Derive adjacency from raster borders.
        adj_sets: Dict[int, set] = {int(td.tid): set() for td in self.territories}
        for yy in range(h):
            row = tid_map[yy]
            for xx in range(w):
                here = int(row[xx])
                if here < 0:
                    continue
                if xx + 1 < w:
                    oth = int(row[xx + 1])
                    if oth >= 0 and oth != here:
                        adj_sets[here].add(oth)
                        adj_sets[oth].add(here)
                if yy + 1 < h:
                    oth = int(tid_map[yy + 1][xx])
                    if oth >= 0 and oth != here:
                        adj_sets[here].add(oth)
                        adj_sets[oth].add(here)

        # Add classic cross-ocean links explicitly.
        name_to_tid: Dict[str, int] = {str(td.name): int(td.tid) for td in self.territories}

        def _link_by_name(a: str, b: str) -> None:
            ta = name_to_tid.get(a)
            tb = name_to_tid.get(b)
            if isinstance(ta, int) and isinstance(tb, int):
                adj_sets[int(ta)].add(int(tb))
                adj_sets[int(tb)].add(int(ta))

        _link_by_name("Alaska", "Kamchatka")
        _link_by_name("Greenland", "Iceland")
        _link_by_name("Brazil", "North Africa")
        _link_by_name("Southern Europe", "Egypt")
        _link_by_name("Southern Europe", "North Africa")
        _link_by_name("Middle East", "Egypt")
        _link_by_name("Middle East", "East Africa")
        _link_by_name("Middle East", "India")
        _link_by_name("Middle East", "Afghanistan")
        _link_by_name("Middle East", "Southern Europe")
        _link_by_name("Indonesia", "SE Asia")
        _link_by_name("Indonesia", "New Guinea")
        _link_by_name("New Guinea", "Eastern Australia")

        self.adj = {int(k): sorted(int(x) for x in v) for k, v in adj_sets.items()}
        return True

    def _build_base_image(self) -> None:
        w, h = int(self.MAP_W), int(self.MAP_H)
        # RGBA bytes, origin bottom-left (row 0 is bottom)
        # Draw a simple "world map" look: ocean gradient + land shading + coastline + neutral borders.
        buf = bytearray(w * h * 4)

        def _noise(x: int, y: int) -> int:
            # tiny deterministic noise in [-6..6]
            v = (x * 374761393 + y * 668265263) & 0xFFFFFFFF
            v = (v ^ (v >> 13)) & 0xFFFFFFFF
            v = (v * 1274126177) & 0xFFFFFFFF
            return int((v >> 28) - 8)  # [-8..7]

        i = 0
        for y in range(h):
            row = self._map_tid[y]
            land_row = (self._land_mask[y] if (self._land_mask and len(self._land_mask) == h) else None)
            lat = float(y) / float(max(1, h - 1))
            for x in range(w):
                tid = int(row[x])
                is_land = False
                if land_row is not None:
                    try:
                        is_land = bool(int(land_row[x]) != 0)
                    except Exception:
                        is_land = False
                else:
                    is_land = tid >= 0

                if not is_land:
                    # Ocean: vertical gradient + a hint of noise.
                    n = _noise(x, y)
                    r = int(10 + 12 * lat + n)
                    g = int(24 + 34 * lat + n)
                    b = int(56 + 40 * lat + n)
                    r = _clamp_int(r, 0, 255)
                    g = _clamp_int(g, 0, 255)
                    b = _clamp_int(b, 0, 255)
                    buf[i + 0] = r
                    buf[i + 1] = g
                    buf[i + 2] = b
                    buf[i + 3] = 255
                    i += 4
                    continue

                # Land: simple flat color (no snow/ice caps) per user request.
                n = _noise(x, y)
                base_r = 70
                base_g = 105
                base_b = 74

                r = _clamp_int(base_r + (n // 2), 0, 255)
                g = _clamp_int(base_g + (n // 2), 0, 255)
                b = _clamp_int(base_b + (n // 2), 0, 255)

                # Neutral internal borders (dark).
                is_internal_border = False
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if nx < 0 or nx >= w or ny < 0 or ny >= h:
                        continue
                    # Internal border only between two real territories.
                    oth_tid = int(self._map_tid[ny][nx])
                    if oth_tid >= 0 and oth_tid != tid and tid >= 0:
                        is_internal_border = True
                if is_internal_border:
                    # subtle dark line so borders are visible even when unowned
                    r = int(r * 0.55)
                    g = int(g * 0.55)
                    b = int(b * 0.55)

                buf[i + 0] = int(r)
                buf[i + 1] = int(g)
                buf[i + 2] = int(b)
                buf[i + 3] = 255
                i += 4

        self._base_image = pyglet.image.ImageData(w, h, "RGBA", bytes(buf), pitch=w * 4)
        self._base_sprite = pyglet.sprite.Sprite(self._base_image)
        # Smooth scaling on the wall display (reduce pixelation).
        try:
            tex = self._base_sprite.image.get_texture()
            tex.min_filter = gl.GL_LINEAR
            tex.mag_filter = gl.GL_LINEAR
        except Exception:
            pass

    def _ownership_only_hash(self) -> str:
        parts = []
        for td in self.territories:
            o = self.owner.get(td.tid, -1)
            parts.append(f"{td.tid}:{o}")
        return "|".join(parts)

    def _rebuild_fill_overlay_if_needed(self) -> None:
        # Rebuild only when ownership changes.
        cur = self._ownership_only_hash()
        if (not self._fill_dirty) and cur == self._fill_last_hash:
            return

        w, h = int(self.MAP_W), int(self.MAP_H)
        buf = bytearray(w * h * 4)

        # Semi-transparent territory fill by owner color.
        # Only land pixels (tid >= 0) get a tint.
        alpha = 70
        i = 0
        for y in range(h):
            row = self._map_tid[y]
            for x in range(w):
                tid = row[x]
                if tid < 0:
                    # water: transparent
                    buf[i + 0] = 0
                    buf[i + 1] = 0
                    buf[i + 2] = 0
                    buf[i + 3] = 0
                    i += 4
                    continue

                seat = self.owner.get(int(tid))
                if not isinstance(seat, int):
                    buf[i + 0] = 0
                    buf[i + 1] = 0
                    buf[i + 2] = 0
                    buf[i + 3] = 0
                    i += 4
                    continue

                col = PLAYER_COLORS[int(seat) % len(PLAYER_COLORS)]
                buf[i + 0] = int(col[0])
                buf[i + 1] = int(col[1])
                buf[i + 2] = int(col[2])
                buf[i + 3] = int(alpha)
                i += 4

        self._fill_image = pyglet.image.ImageData(w, h, "RGBA", bytes(buf), pitch=w * 4)
        self._fill_sprite = pyglet.sprite.Sprite(self._fill_image)
        try:
            tex = self._fill_sprite.image.get_texture()
            tex.min_filter = gl.GL_LINEAR
            tex.mag_filter = gl.GL_LINEAR
        except Exception:
            pass
        self._fill_last_hash = cur
        self._fill_dirty = False

    def _ownership_hash(self) -> str:
        parts = []
        for td in self.territories:
            o = self.owner.get(td.tid, -1)
            t = self.troops.get(td.tid, 0)
            parts.append(f"{td.tid}:{o}:{t}")
        return "|".join(parts)

    def _rebuild_border_overlay_if_needed(self) -> None:
        if not self._border_dirty:
            cur = self._ownership_hash()
            if cur == self._border_last_hash:
                return

        w, h = int(self.MAP_W), int(self.MAP_H)
        buf = bytearray(w * h * 4)

        # Border pixels colored by owning player's color.
        for td in self.territories:
            tid = int(td.tid)
            seat = self.owner.get(tid)
            if not isinstance(seat, int):
                continue
            col = PLAYER_COLORS[int(seat) % len(PLAYER_COLORS)]
            r, g, b = int(col[0]), int(col[1]), int(col[2])
            for x, y in self._border_pixels.get(tid, []):
                idx = (int(y) * w + int(x)) * 4
                buf[idx] = r
                buf[idx + 1] = g
                buf[idx + 2] = b
                buf[idx + 3] = 255

        self._border_image = pyglet.image.ImageData(w, h, "RGBA", bytes(buf), pitch=w * 4)
        self._border_sprite = pyglet.sprite.Sprite(self._border_image)
        try:
            tex = self._border_sprite.image.get_texture()
            tex.min_filter = gl.GL_LINEAR
            tex.mag_filter = gl.GL_LINEAR
        except Exception:
            pass
        self._border_last_hash = self._ownership_hash()
        self._border_dirty = False

    def _fx_add(self, kind: str, **kw) -> None:
        now = time.time()
        d = {"kind": str(kind), "t0": float(now)}
        d.update(kw)
        self._fx.append(d)

    def _fx_prune(self) -> None:
        now = time.time()
        keep = []
        for fx in self._fx:
            dur = float(fx.get("dur", 0.8) or 0.8)
            if now - float(fx.get("t0", now)) <= dur:
                keep.append(fx)
        self._fx = keep

    # --- Gameplay ---

    def start_game(self, selected_indices: List[int]) -> None:
        seats = [int(i) for i in selected_indices if isinstance(i, int) or str(i).isdigit()]
        seats = [s for s in seats if 0 <= s <= 7]
        seats = sorted(dict.fromkeys(seats))
        if len(seats) < 2:
            return

        self.active_players = seats
        self.eliminated_players = []
        self.winner = None

        # Randomly assign territories evenly.
        tids = [td.tid for td in self.territories]
        random.shuffle(tids)
        self.owner = {}
        self.troops = {}
        for i, tid in enumerate(tids):
            seat = seats[i % len(seats)]
            self.owner[int(tid)] = int(seat)
            self.troops[int(tid)] = 1

        # Choose first turn.
        self.current_turn_seat = int(seats[0])
        self.phase = "reinforce"
        self.selected_from = None
        self.selected_to = None
        self.reinforcements_left = self._calc_reinforcements(self.current_turn_seat)

        self.state = "playing"
        self.last_event = "Risk started"
        self._border_dirty = True
        self._refresh_buttons()

    def handle_player_quit(self, seat: int) -> None:
        """Handle a player disconnecting mid-game.

        Risk can freeze if the current-turn player leaves; also their territories must
        be reassigned or the game becomes unwinnable.
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

        was_turn = bool(isinstance(self.current_turn_seat, int) and int(self.current_turn_seat) == s)

        remaining = [int(x) for x in self.active_players if int(x) != s]

        # Reassign all territories owned by the quitter.
        owned = [int(tid) for tid, owner in (self.owner or {}).items() if int(owner) == s]
        if remaining and owned:
            random.shuffle(owned)
            for i, tid in enumerate(owned):
                self.owner[int(tid)] = int(remaining[i % len(remaining)])
            self._border_dirty = True
            self._fill_dirty = True

        # Remove from turn order.
        self.active_players = remaining
        if s in self.eliminated_players:
            try:
                self.eliminated_players = [int(x) for x in self.eliminated_players if int(x) != s]
            except Exception:
                pass

        if not remaining:
            self.state = "player_select"
            self.current_turn_seat = None
            self.last_event = "All players left"
            self._refresh_buttons()
            return

        # If their removal ends the game, set winner.
        self._check_eliminations()
        if self.winner is not None:
            self._refresh_buttons()
            return

        # If it was their turn, advance to the next remaining seat.
        if was_turn:
            self.current_turn_seat = int(remaining[0])
            self.phase = "reinforce"
            self.selected_from = None
            self.selected_to = None
            self.reinforcements_left = self._calc_reinforcements(int(self.current_turn_seat))
            self.last_event = f"Turn: {self._seat_label(int(self.current_turn_seat))}"

        self.last_event = f"{self._seat_label(s)} quit"
        self._refresh_buttons()

    def update(self, dt: float) -> None:
        return

    def _calc_reinforcements(self, seat: int) -> int:
        owned = [td.tid for td in self.territories if self.owner.get(td.tid) == seat]
        base = max(3, len(owned) // 3)

        # continent bonuses
        bonus = 0
        by_cont: Dict[str, List[int]] = {}
        for td in self.territories:
            by_cont.setdefault(td.continent, []).append(td.tid)
        for cont, tids in by_cont.items():
            if tids and all(self.owner.get(tid) == seat for tid in tids):
                bonus += int(self.continent_bonus.get(cont, 0) or 0)

        return int(base + bonus)

    def _alive_players(self) -> List[int]:
        alive = []
        for s in self.active_players:
            if s in self.eliminated_players:
                continue
            alive.append(int(s))
        return alive

    def _check_eliminations(self) -> None:
        # A player is eliminated if they own no territories.
        alive = self._alive_players()
        for s in list(alive):
            owns_any = any(self.owner.get(td.tid) == s for td in self.territories)
            if not owns_any and s not in self.eliminated_players:
                self.eliminated_players.append(int(s))
                self.last_event = f"{self._seat_label(s)} eliminated"

        alive = self._alive_players()
        if len(alive) == 1:
            self.winner = int(alive[0])
            self.last_event = f"{self._seat_label(self.winner)} wins!"

    def _is_my_turn(self, seat: int) -> bool:
        return isinstance(self.current_turn_seat, int) and int(seat) == int(self.current_turn_seat)

    def _can_select(self, tid: int) -> bool:
        return any(td.tid == tid for td in self.territories)

    def handle_click(self, player_idx: int, btn_id: str) -> None:
        if self.state != "playing":
            return
        if not isinstance(player_idx, int):
            return

        # Territory picks from UI list.
        if btn_id.startswith("pick:"):
            try:
                tid = int(btn_id.split(":", 1)[1])
            except Exception:
                return
            if not self._can_select(tid):
                return
            self._handle_pick(player_idx, tid)
            self._refresh_buttons()
            return

        if btn_id == "add_troop":
            self._handle_add_troop(player_idx)
        elif btn_id == "to_attack":
            if self._is_my_turn(player_idx) and self.phase == "reinforce" and self.reinforcements_left <= 0:
                self.phase = "attack"
                self.selected_to = None
        elif btn_id == "attack":
            self._handle_attack(player_idx)
        elif btn_id == "end_attack":
            if self._is_my_turn(player_idx) and self.phase == "attack":
                self.phase = "fortify"
                self.selected_to = None
        elif btn_id == "move_1":
            self._handle_fortify_move(player_idx)
        elif btn_id == "end_turn":
            self._handle_end_turn(player_idx)

        self._refresh_buttons()

    def _handle_pick(self, seat: int, tid: int) -> None:
        if not self._is_my_turn(seat):
            # Allow non-turn players to inspect selection in their UI only.
            # But keep server-side selection per seat (simpler): ignore.
            return

        if self.winner is not None:
            return

        if self.phase == "reinforce":
            if self.owner.get(tid) == seat:
                self.selected_from = tid
                self.selected_to = None
        elif self.phase == "attack":
            if self.selected_from is None:
                if self.owner.get(tid) == seat and int(self.troops.get(tid, 0) or 0) > 1:
                    self.selected_from = tid
                    self.selected_to = None
                return
            # If clicking another owned territory, switch attacker.
            if self.owner.get(tid) == seat:
                if int(self.troops.get(tid, 0) or 0) > 1:
                    self.selected_from = tid
                    self.selected_to = None
                return
            # Otherwise, set defender if adjacent.
            if tid in (self.adj.get(self.selected_from) or []):
                self.selected_to = tid
        elif self.phase == "fortify":
            if self.selected_from is None:
                if self.owner.get(tid) == seat and int(self.troops.get(tid, 0) or 0) > 1:
                    self.selected_from = tid
                    self.selected_to = None
                return
            # set destination (must be owned and adjacent)
            if self.owner.get(tid) == seat and tid in (self.adj.get(self.selected_from) or []):
                self.selected_to = tid
            # clicking another source switches
            if self.owner.get(tid) == seat and int(self.troops.get(tid, 0) or 0) > 1 and tid != self.selected_to:
                self.selected_from = tid
                self.selected_to = None

    def _handle_add_troop(self, seat: int) -> None:
        if not self._is_my_turn(seat):
            return
        if self.winner is not None:
            return
        if self.phase != "reinforce":
            return
        if self.reinforcements_left <= 0:
            return
        if self.selected_from is None:
            return
        if self.owner.get(self.selected_from) != seat:
            return

        self.troops[self.selected_from] = int(self.troops.get(self.selected_from, 0) or 0) + 1
        self.reinforcements_left -= 1
        self.last_event = f"{self._seat_label(seat)} placed 1 troop"
        self._border_dirty = True

        # Visual: troop walks in from "reserve" to the territory.
        if self.selected_from is not None:
            col = PLAYER_COLORS[int(seat) % len(PLAYER_COLORS)]
            sx, sy = self._tid_point(int(self.selected_from))
            self._fx_add(
                "move",
                dur=0.55,
                color=(int(col[0]), int(col[1]), int(col[2])),
                a=(20, int(self.MAP_H) + 22),
                b=(int(sx), int(sy)),
                r0=3,
                r1=5,
            )
            self._fx_add(
                "pulse",
                dur=0.6,
                color=(int(col[0]), int(col[1]), int(col[2])),
                p=(int(sx), int(sy)),
                r0=7,
                r1=20,
            )

    def _roll_dice(self, n: int) -> List[int]:
        n = _clamp_int(int(n), 0, 3)
        return sorted([random.randint(1, 6) for _ in range(n)], reverse=True)

    def _handle_attack(self, seat: int) -> None:
        if not self._is_my_turn(seat):
            return
        if self.winner is not None:
            return
        if self.phase != "attack":
            return
        if self.selected_from is None or self.selected_to is None:
            return
        a_tid = int(self.selected_from)
        d_tid = int(self.selected_to)
        if self.owner.get(a_tid) != seat:
            return
        if self.owner.get(d_tid) == seat:
            return
        if d_tid not in (self.adj.get(a_tid) or []):
            return
        a_troops = int(self.troops.get(a_tid, 0) or 0)
        d_troops = int(self.troops.get(d_tid, 0) or 0)
        if a_troops <= 1 or d_troops <= 0:
            return

        a_dice = min(3, a_troops - 1)
        d_dice = min(2, d_troops)
        a_roll = self._roll_dice(a_dice)
        d_roll = self._roll_dice(d_dice)

        comps = min(len(a_roll), len(d_roll))
        a_losses = 0
        d_losses = 0
        for i in range(comps):
            if a_roll[i] > d_roll[i]:
                d_losses += 1
            else:
                a_losses += 1  # defender wins ties

        self.troops[a_tid] = max(1, a_troops - a_losses)
        self.troops[d_tid] = max(0, d_troops - d_losses)

        self._last_attack_roll = (list(a_roll), list(d_roll), int(a_losses), int(d_losses))

        # Visual: projectile + impact flash.
        if a_tid is not None and d_tid is not None:
            col = PLAYER_COLORS[int(seat) % len(PLAYER_COLORS)]
            ax, ay = self._tid_point(int(a_tid))
            dx, dy = self._tid_point(int(d_tid))
            self._fx_add(
                "projectile",
                dur=0.45,
                color=(int(col[0]), int(col[1]), int(col[2])),
                a=(int(ax), int(ay)),
                b=(int(dx), int(dy)),
                r0=3,
                r1=2,
            )
            self._fx_add(
                "impact",
                dur=0.55,
                color=(255, 220, 120),
                p=(int(dx), int(dy)),
                r0=6,
                r1=26,
            )

        # conquest
        if self.troops[d_tid] <= 0:
            prev_owner = self.owner.get(d_tid)
            self.owner[d_tid] = seat
            # move 1 troop in automatically
            self.troops[d_tid] = 1
            self.troops[a_tid] = max(1, int(self.troops.get(a_tid, 1)) - 1)
            self.last_event = (
                f"{self._seat_label(seat)} conquered {self._tid_name(d_tid)} "
                f"({a_roll} vs {d_roll})"
            )
            if isinstance(prev_owner, int):
                self._check_eliminations()
            self._border_dirty = True
            self._fill_dirty = True

            # Visual: conquest burst.
            if d_tid is not None:
                col = PLAYER_COLORS[int(seat) % len(PLAYER_COLORS)]
                dx, dy = self._tid_point(int(d_tid))
                for k in range(10):
                    ang = (k / 10.0) * (math.pi * 2.0)
                    self._fx_add(
                        "spark",
                        dur=0.7,
                        color=(int(col[0]), int(col[1]), int(col[2])),
                        p=(int(dx), int(dy)),
                        v=(math.cos(ang) * 22.0, math.sin(ang) * 22.0),
                    )
            # After conquest, keep attacker selected; let them pick a new target.
            self.selected_to = None
            return

        self.last_event = f"Attack: {a_roll} vs {d_roll} (A-{a_losses}, D-{d_losses})"
        self._border_dirty = True

    def _handle_fortify_move(self, seat: int) -> None:
        if not self._is_my_turn(seat):
            return
        if self.winner is not None:
            return
        if self.phase != "fortify":
            return
        if self.selected_from is None or self.selected_to is None:
            return
        a_tid = int(self.selected_from)
        b_tid = int(self.selected_to)
        if self.owner.get(a_tid) != seat or self.owner.get(b_tid) != seat:
            return
        if b_tid not in (self.adj.get(a_tid) or []):
            return
        a_troops = int(self.troops.get(a_tid, 0) or 0)
        if a_troops <= 1:
            return
        self.troops[a_tid] = a_troops - 1
        self.troops[b_tid] = int(self.troops.get(b_tid, 0) or 0) + 1
        self.last_event = f"{self._seat_label(seat)} fortified 1 troop"
        self._border_dirty = True

        # Visual: troop walks from source to destination.
        if a_tid is not None and b_tid is not None:
            col = PLAYER_COLORS[int(seat) % len(PLAYER_COLORS)]
            ax, ay = self._tid_point(int(a_tid))
            bx, by = self._tid_point(int(b_tid))
            self._fx_add(
                "move",
                dur=0.55,
                color=(int(col[0]), int(col[1]), int(col[2])),
                a=(int(ax), int(ay)),
                b=(int(bx), int(by)),
                r0=4,
                r1=5,
            )
            self._fx_add(
                "pulse",
                dur=0.55,
                color=(int(col[0]), int(col[1]), int(col[2])),
                p=(int(bx), int(by)),
                r0=7,
                r1=18,
            )

    def _handle_end_turn(self, seat: int) -> None:
        if not self._is_my_turn(seat):
            return
        if self.winner is not None:
            return

        alive = self._alive_players()
        if not alive:
            return
        if seat not in alive:
            # Shouldn't happen, but advance.
            seat = alive[0]

        # Next alive seat
        i = alive.index(seat)
        nxt = alive[(i + 1) % len(alive)]
        self.current_turn_seat = int(nxt)
        self.phase = "reinforce"
        self.selected_from = None
        self.selected_to = None
        self.reinforcements_left = self._calc_reinforcements(int(nxt))
        self.last_event = f"Turn: {self._seat_label(int(nxt))}"
        self._last_attack_roll = None
        self._refresh_buttons()

    def _tid_name(self, tid: int) -> str:
        for td in self.territories:
            if td.tid == tid:
                return td.name
        return f"T{tid}"

    # --- Web UI state ---

    def _refresh_buttons(self) -> None:
        self.buttons = {}
        for seat in range(8):
            self.buttons[seat] = {}

        for seat in self._alive_players():
            is_turn = self._is_my_turn(seat)
            if self.winner is not None:
                self.buttons[seat]["end_turn"] = _WebButton("Game Over", enabled=False)
                continue

            if not is_turn:
                self.buttons[seat]["end_turn"] = _WebButton("Waiting", enabled=False)
                continue

            if self.phase == "reinforce":
                can_add = (
                    self.reinforcements_left > 0
                    and self.selected_from is not None
                    and self.owner.get(self.selected_from) == seat
                )
                self.buttons[seat]["add_troop"] = _WebButton(f"Add Troop (+1) ({self.reinforcements_left})", enabled=can_add)
                self.buttons[seat]["to_attack"] = _WebButton("To Attack", enabled=self.reinforcements_left <= 0)
            elif self.phase == "attack":
                can_attack = (
                    self.selected_from is not None
                    and self.selected_to is not None
                    and self.owner.get(self.selected_from) == seat
                    and self.owner.get(self.selected_to) != seat
                    and self.selected_to in (self.adj.get(self.selected_from) or [])
                    and int(self.troops.get(self.selected_from, 0) or 0) > 1
                )
                self.buttons[seat]["attack"] = _WebButton("Attack", enabled=can_attack)
                self.buttons[seat]["end_attack"] = _WebButton("End Attack", enabled=True)
            elif self.phase == "fortify":
                can_move = (
                    self.selected_from is not None
                    and self.selected_to is not None
                    and self.owner.get(self.selected_from) == seat
                    and self.owner.get(self.selected_to) == seat
                    and self.selected_to in (self.adj.get(self.selected_from) or [])
                    and int(self.troops.get(self.selected_from, 0) or 0) > 1
                )
                self.buttons[seat]["move_1"] = _WebButton("Move 1", enabled=can_move)
                self.buttons[seat]["end_turn"] = _WebButton("End Turn", enabled=True)

    def get_public_state(self, player_idx: int) -> Dict:
        # Minimal public snapshot for UI.
        terr = []
        for td in self.territories:
            terr.append(
                {
                    "tid": int(td.tid),
                    "name": td.name,
                    "continent": td.continent,
                    "owner": self.owner.get(td.tid, None),
                    "troops": int(self.troops.get(td.tid, 0) or 0),
                }
            )

        return {
            "state": str(self.state),
            "active_players": list(self._alive_players()),
            "eliminated_players": list(self.eliminated_players),
            "current_turn_seat": self.current_turn_seat,
            "phase": self.phase,
            "reinforcements_left": int(self.reinforcements_left),
            "selected_from": self.selected_from,
            "selected_to": self.selected_to,
            "winner": self.winner,
            "last_event": self.last_event or None,
            "territories": terr,
        }

    # --- Pyglet drawing ---

    def draw(self) -> None:
        if self.renderer is None:
            return

        # Background
        # NOTE: The main renderer draws its batch *after* game.draw() returns.
        # If we add a full-screen rect to that batch, it will cover our sprites.
        w = int(self.width)
        h = int(self.height)
        if self._bg_rect is None:
            self._bg_rect = pyglet.shapes.Rectangle(0, 0, w, h, color=(10, 10, 14))
        else:
            self._bg_rect.width = w
            self._bg_rect.height = h
            self._bg_rect.color = (10, 10, 14)
        self._bg_rect.opacity = 255
        self._bg_rect.draw()

        if self.state == "player_select":
            self.renderer.draw_text(
                "Risk",
                24,
                24,
                font_size=28,
                color=(235, 235, 235),
                anchor_x="left",
                anchor_y="top",
            )
            self.renderer.draw_text(
                "Select players in Web UI",
                24,
                58,
                font_size=16,
                color=(200, 200, 200),
                anchor_x="left",
                anchor_y="top",
            )
            return

        # Map placement in pygame coords (top-left origin): reserve top header.
        pad = 24
        header_h = 78
        map_x = pad
        map_y = header_h
        avail_w = int(self.width) - pad * 2
        avail_h = int(self.height) - header_h - pad

        img_w, img_h = int(self.MAP_W), int(self.MAP_H)
        scale = min(avail_w / max(1, img_w), avail_h / max(1, img_h))
        draw_w = int(img_w * scale)
        draw_h = int(img_h * scale)

        # Convert pygame coords -> OpenGL bottom-left for sprite placement.
        y_bottom = int(self.renderer.flip_y(map_y) - draw_h)

        # Base map sprite
        if self._base_sprite is not None:
            self._base_sprite.x = int(map_x)
            self._base_sprite.y = int(y_bottom)
            self._base_sprite.scale_x = scale
            self._base_sprite.scale_y = scale
            self._base_sprite.draw()

        # Owner fill overlay (rebuild when ownership changes)
        self._rebuild_fill_overlay_if_needed()
        if self._fill_sprite is not None:
            self._fill_sprite.x = int(map_x)
            self._fill_sprite.y = int(y_bottom)
            self._fill_sprite.scale_x = scale
            self._fill_sprite.scale_y = scale
            self._fill_sprite.draw()

        # Border overlay sprite (rebuild when ownership/troops change)
        self._rebuild_border_overlay_if_needed()
        if self._border_sprite is not None:
            self._border_sprite.x = int(map_x)
            self._border_sprite.y = int(y_bottom)
            self._border_sprite.scale_x = scale
            self._border_sprite.scale_y = scale
            self._border_sprite.draw()

        # Header text
        turn = self._seat_label(self.current_turn_seat)
        self.renderer.draw_text(
            "Risk",
            pad,
            22,
            font_size=24,
            color=(235, 235, 235),
            anchor_x="left",
            anchor_y="top",
        )
        self.renderer.draw_text(
            f"Turn: {turn}  ·  Phase: {self.phase}  ·  Reinforcements: {self.reinforcements_left}",
            pad,
            48,
            font_size=14,
            color=(200, 200, 200),
            anchor_x="left",
            anchor_y="top",
        )
        if self.winner is not None:
            self.renderer.draw_text(
                f"Winner: {self._seat_label(self.winner)}",
                pad,
                68,
                font_size=14,
                color=(255, 220, 140),
                anchor_x="left",
                anchor_y="top",
            )

        # Attack roll info (brief, visual feedback)
        if self._last_attack_roll is not None:
            a_roll, d_roll, a_losses, d_losses = self._last_attack_roll
            self.renderer.draw_text(
                f"Dice: A {a_roll} vs D {d_roll}  (A-{a_losses}, D-{d_losses})",
                pad,
                86,
                font_size=12,
                color=(190, 190, 190),
                anchor_x="left",
                anchor_y="top",
            )

        # Selection highlights + troop markers (tokens)
        def _map_to_screen(px: float, py: float) -> Tuple[int, int]:
            sx = float(map_x) + float(px) * float(scale)
            sy = float(map_y) + (float(img_h) - float(py)) * float(scale)
            return int(sx), int(sy)

        # Simple pulsing to make selections stand out
        now = time.time()
        pulse = 0.5 + 0.5 * math.sin(now * 5.0)

        if isinstance(self.selected_from, int):
            px, py = self._tid_point(int(self.selected_from))
            sx, sy = _map_to_screen(px, py)
            self.renderer.draw_circle((255, 255, 255), (sx, sy), int(16 + pulse * 6), width=0, alpha=40)

        if isinstance(self.selected_to, int):
            px, py = self._tid_point(int(self.selected_to))
            sx, sy = _map_to_screen(px, py)
            self.renderer.draw_circle((255, 220, 120), (sx, sy), int(16 + pulse * 6), width=0, alpha=35)

        # If both selected, draw a subtle line between them
        if isinstance(self.selected_from, int) and isinstance(self.selected_to, int):
            apx, apy = self._tid_point(int(self.selected_from))
            bpx, bpy = self._tid_point(int(self.selected_to))
            ax, ay = _map_to_screen(apx, apy)
            bx, by = _map_to_screen(bpx, bpy)
            self.renderer.draw_line((210, 210, 210), (ax, ay), (bx, by), width=2, alpha=70)

        # Draw troop markers
        for td in self.territories:
            seat = self.owner.get(td.tid)
            troops = int(self.troops.get(td.tid, 0) or 0)
            if troops <= 0:
                continue
            px, py = self._tid_point(int(td.tid))
            sx, sy = _map_to_screen(px, py)

            if isinstance(seat, int):
                pc = PLAYER_COLORS[int(seat) % len(PLAYER_COLORS)]
                token_col = (int(pc[0]), int(pc[1]), int(pc[2]))
            else:
                token_col = (230, 230, 230)

            # token body + outline
            self.renderer.draw_circle(token_col, (sx, sy), 10, width=0, alpha=220)
            self.renderer.draw_circle((0, 0, 0), (sx, sy), 11, width=0, alpha=70)
            # number
            self.renderer.draw_text(
                str(troops),
                sx + 1,
                sy + 1,
                font_size=12,
                color=(0, 0, 0),
                anchor_x="center",
                anchor_y="center",
            )
            self.renderer.draw_text(
                str(troops),
                sx,
                sy,
                font_size=12,
                color=(245, 245, 245),
                anchor_x="center",
                anchor_y="center",
            )

        # FX / animations (projectiles, moving troops, pulses, sparks)
        self._fx_prune()
        for fx in list(self._fx):
            kind = str(fx.get("kind", ""))
            t0 = float(fx.get("t0", now))
            dur = float(fx.get("dur", 0.6) or 0.6)
            t = max(0.0, min(1.0, (now - t0) / max(0.001, dur)))

            col = fx.get("color", (255, 255, 255))
            if not (isinstance(col, tuple) and len(col) >= 3):
                col = (255, 255, 255)
            col = (int(col[0]), int(col[1]), int(col[2]))

            if kind in ("move", "projectile"):
                ax, ay = fx.get("a", (0, 0))
                bx, by = fx.get("b", (0, 0))
                ax, ay = float(ax), float(ay)
                bx, by = float(bx), float(by)
                # ease
                tt = t * t * (3.0 - 2.0 * t)
                px = ax + (bx - ax) * tt
                py = ay + (by - ay) * tt
                sx, sy = _map_to_screen(px, py)
                r0 = float(fx.get("r0", 3) or 3)
                r1 = float(fx.get("r1", 5) or 5)
                rr = int(r0 + (r1 - r0) * tt)
                alpha = int(220 if kind == "move" else 240)
                self.renderer.draw_circle(col, (sx, sy), rr, width=0, alpha=alpha)
                if kind == "projectile":
                    # faint trail
                    sx0, sy0 = _map_to_screen(ax, ay)
                    self.renderer.draw_line(col, (sx0, sy0), (sx, sy), width=2, alpha=90)

            elif kind == "pulse":
                px, py = fx.get("p", (0, 0))
                px, py = float(px), float(py)
                sx, sy = _map_to_screen(px, py)
                r0 = float(fx.get("r0", 6) or 6)
                r1 = float(fx.get("r1", 22) or 22)
                rr = int(r0 + (r1 - r0) * t)
                alpha = int(120 * (1.0 - t))
                self.renderer.draw_circle(col, (sx, sy), rr, width=0, alpha=alpha)

            elif kind == "impact":
                px, py = fx.get("p", (0, 0))
                px, py = float(px), float(py)
                sx, sy = _map_to_screen(px, py)
                r0 = float(fx.get("r0", 6) or 6)
                r1 = float(fx.get("r1", 30) or 30)
                rr = int(r0 + (r1 - r0) * t)
                alpha = int(140 * (1.0 - t))
                self.renderer.draw_circle(col, (sx, sy), rr, width=0, alpha=alpha)

            elif kind == "spark":
                px, py = fx.get("p", (0, 0))
                vx, vy = fx.get("v", (0.0, 0.0))
                px, py = float(px), float(py)
                vx, vy = float(vx), float(vy)
                # ballistic-ish outward
                px2 = px + vx * t
                py2 = py + vy * t
                sx, sy = _map_to_screen(px2, py2)
                alpha = int(220 * (1.0 - t))
                self.renderer.draw_circle(col, (sx, sy), 2, width=0, alpha=alpha)

        # Last event (bottom-left)
        if self.last_event:
            self.renderer.draw_text(
                str(self.last_event),
                pad,
                int(self.height) - 18,
                font_size=12,
                color=(190, 190, 190),
                anchor_x="left",
                anchor_y="top",
            )


# Compatibility alias (some codebases expect Game class names here)
Risk = RiskGame
