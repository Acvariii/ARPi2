import time
import math
import random
import pygame
from typing import List, Dict, Tuple, Optional

from ui_elements import PlayerSelectionUI, HOVER_TIME_THRESHOLD

# Minimal 40-space description (name + optional display color)
PROPERTY_SPACES = [
    {"name": "Go", "color": None},
    {"name": "Mediterranean Ave", "color": (139, 69, 19)},
    {"name": "Community Chest", "color": None},
    {"name": "Baltic Ave", "color": (139, 69, 19)},
    {"name": "Income Tax", "color": None},
    {"name": "Reading RR", "color": (80, 80, 80)},
    {"name": "Oriental Ave", "color": (173, 216, 230)},
    {"name": "Chance", "color": None},
    {"name": "Vermont Ave", "color": (173, 216, 230)},
    {"name": "Connecticut Ave", "color": (173, 216, 230)},
    {"name": "Jail / Just Visiting", "color": None},
    {"name": "St. Charles Pl", "color": (255, 192, 203)},
    {"name": "Electric Co.", "color": (200, 200, 200)},
    {"name": "States Ave", "color": (255, 192, 203)},
    {"name": "Virginia Ave", "color": (255, 192, 203)},
    {"name": "Pennsylvania RR", "color": (80, 80, 80)},
    {"name": "St. James Pl", "color": (255, 165, 0)},
    {"name": "Community Chest", "color": None},
    {"name": "Tennessee Ave", "color": (255, 165, 0)},
    {"name": "New York Ave", "color": (255, 165, 0)},
    {"name": "Free Parking", "color": None},
    {"name": "Kentucky Ave", "color": (255, 105, 180)},
    {"name": "Chance", "color": None},
    {"name": "Indiana Ave", "color": (255, 105, 180)},
    {"name": "Illinois Ave", "color": (255, 105, 180)},
    {"name": "B. & O. RR", "color": (80, 80, 80)},
    {"name": "Atlantic Ave", "color": (255, 215, 0)},
    {"name": "Ventnor Ave", "color": (255, 215, 0)},
    {"name": "Water Works", "color": (200, 200, 200)},
    {"name": "Marvin Gardens", "color": (255, 215, 0)},
    {"name": "Go To Jail", "color": None},
    {"name": "Pacific Ave", "color": (34, 139, 34)},
    {"name": "North Carolina Ave", "color": (34, 139, 34)},
    {"name": "Community Chest", "color": None},
    {"name": "Pennsylvania Ave", "color": (34, 139, 34)},
    {"name": "Short Line RR", "color": (80, 80, 80)},
    {"name": "Chance", "color": None},
    {"name": "Park Place", "color": (25, 25, 112)},
    {"name": "Luxury Tax", "color": None},
    {"name": "Boardwalk", "color": (25, 25, 112)},
]

# Player container
class Player:
    def __init__(self, idx: int, color: Tuple[int, int, int]):
        self.idx = idx
        self.color = color
        self.money = 1500
        self.pos = 0
        self.properties: List[int] = []
        # movement path: list of target spaces to step through
        self.move_path: List[int] = []
        self.move_start: float = 0.0
        self.move_per_space: float = 0.25  # seconds per space (4 spaces/sec)
        self.move_from: Optional[int] = None
        self._open_after_move = False


class MonopolyGame:
    def __init__(self, screen: pygame.Surface, hand_to_screen_fn):
        self.screen = screen
        self.hand_to_screen = hand_to_screen_fn
        self.selection_ui = PlayerSelectionUI(screen)
        vibrant = [
            (220, 40, 40),
            (40, 220, 40),
            (40, 70, 220),
            (255, 200, 60),
            (200, 40, 200),
            (40, 220, 200),
            (255, 120, 60),
            (140, 40, 220),
        ]
        self.players = [Player(i, vibrant[i]) for i in range(8)]
        self.players_selected: List[int] = []
        self.current = 0
        self.properties = PROPERTY_SPACES.copy()
        self.board_spaces = 40
        self.owners: List[Optional[int]] = [None] * self.board_spaces

        # hover / popup tracking
        self.button_hover: Dict[str, float] = {}
        self.button_hover_pos: Dict[str, Tuple[int, int]] = {}
        self.popup_hover: Dict[str, float] = {}
        self.properties_open: Dict[int, bool] = {i: False for i in range(8)}

        # dice state
        self.dice_state: Dict = {"rolling": False, "start": 0.0, "end": 0.0, "d1": 0, "d2": 0, "pid": None}
        self.last_roll = (0, 0)

        # cached button rects
        self._last_button_rects: Dict[int, Dict[str, pygame.Rect]] = {}

    # ---- geometry: responsive, grid-based 11x11 layout so corners and edges map exactly ----
    def _compute_board_rect(self) -> pygame.Rect:
        w, h = self.screen.get_size()
        # leave comfortable margins relative to screen size
        margin = int(min(w, h) * 0.08)
        size = min(w - 2 * margin, h - 2 * margin)
        bx = (w - size) // 2
        by = (h - size) // 2
        return pygame.Rect(bx, by, size, size)

    def _grid_cell(self) -> float:
        # board is drawn on a 10x10 grid (corners included => 10 spaces per side)
        board = self._compute_board_rect()
        return board.width / 10.0

    def _index_to_grid(self, idx: int) -> Tuple[int, int]:
        """Map monopoly index (0..39) to 10x10 grid coords where (0,0) top-left.
        Standard Monopoly order (clockwise) with index 0 = Go at bottom-right (9,9)."""
        if idx == 0:
            return 9, 9
        if 1 <= idx <= 9:
            return 9 - idx, 9
        if idx == 10:
            return 0, 9
        if 11 <= idx <= 19:
            return 0, 9 - (idx - 10)
        if idx == 20:
            return 0, 0
        if 21 <= idx <= 29:
            return idx - 20, 0
        if idx == 30:
            return 9, 0
        if 31 <= idx <= 39:
            return 9, idx - 30
        return 0, 0

    def _slot_rect_around_board(self, pid: int) -> pygame.Rect:
        """Compute a player slot rect anchored outside the board so it never overlaps the board."""
        sw, sh = self.screen.get_size()
        board = self._compute_board_rect()
        cell = int(self._grid_cell())
        # sizes anchored to board dimensions
        top_h = max(int(sh * 0.10), cell * 2)
        slot_w = max(int(board.width * 0.28), int(sw * 0.12))
        side_w = max(int(sw * 0.12), cell * 2)
        pos_idx = pid
        if pos_idx <= 2:
            x = board.left + int((pos_idx + 0.5) * (board.width / 3) - slot_w / 2)
            y = max(8, board.top - top_h - 8)
            return pygame.Rect(int(x), int(y), int(slot_w), int(top_h))
        if 3 <= pos_idx <= 5:
            idx = pos_idx - 3
            x = board.left + int((idx + 0.5) * (board.width / 3) - slot_w / 2)
            y = min(sh - top_h - 8, board.bottom + 8)
            return pygame.Rect(int(x), int(y), int(slot_w), int(top_h))
        if pos_idx == 6:
            slot_h = max(int(board.height * 0.44), side_w)
            x = max(8, board.left - side_w - 8)
            y = board.top + int((board.height - slot_h) / 2)
            return pygame.Rect(int(x), int(y), int(side_w), int(slot_h))
        slot_h = max(int(board.height * 0.44), side_w)
        x = min(sw - side_w - 8, board.right + 8)
        y = board.top + int((board.height - slot_h) / 2)
        return pygame.Rect(int(x), int(y), int(side_w), int(slot_h))

    # player button rects relative to slot rect; use relative sizes
    def _player_button_rects(self, pid: int, rect_override: Optional[pygame.Rect] = None) -> Dict[str, pygame.Rect]:
        rect = rect_override if rect_override is not None else self.selection_ui.slot_rect(pid)
        pos = self.selection_ui.positions[pid]
        gap = max(6, int(min(rect.width, rect.height) * 0.06))
        xpad = max(6, int(rect.width * 0.06))
        ypad = max(6, int(rect.height * 0.06))
        rects: Dict[str, pygame.Rect] = {}
        if pos[1] == 0 or pos[1] == self.screen.get_height():
            # horizontal layout
            total_w = rect.width - xpad * 2
            btn_w = max(48, (total_w - gap * 2) // 3)
            btn_h = max(28, rect.height - ypad * 2)
            start_x = rect.left + xpad + (total_w - (btn_w * 3 + gap * 2)) // 2
            y = rect.top + ypad
            for i, key in enumerate(["roll", "props", "buy"]):
                bx = start_x + i * (btn_w + gap)
                rects[key] = pygame.Rect(bx, y, btn_w, btn_h)
        else:
            # vertical layout
            btn_w = max(48, rect.width - xpad * 2)
            total_btn_h = rect.height - (gap * 4)
            btn_h = max(26, total_btn_h // 3)
            x = rect.left + xpad
            y = rect.top + gap
            rects["roll"] = pygame.Rect(x, y, btn_w, btn_h)
            rects["props"] = pygame.Rect(x, y + btn_h + gap, btn_w, btn_h)
            rects["buy"] = pygame.Rect(x, y + 2 * (btn_h + gap), btn_w, btn_h)
        self._last_button_rects[pid] = rects
        return rects

    # properties overlay rect anchored to player's slot; size relative to screen
    def _properties_overlay_rect(self, pid: int, ow: Optional[int] = None, oh: Optional[int] = None) -> pygame.Rect:
        sw, sh = self.screen.get_size()
        if ow is None:
            ow = min(int(sw * 0.36), 560)
        if oh is None:
            oh = min(int(sh * 0.48), 520)
        slot = self.selection_ui.slot_rect(pid)
        # try to place overlay adjacent to slot without covering board center
        if slot.top == 0:
            x = max(16, min(sw - ow - 16, slot.centerx - ow // 2))
            y = slot.bottom + 8
        elif slot.bottom == sh:
            x = max(16, min(sw - ow - 16, slot.centerx - ow // 2))
            y = slot.top - oh - 8
        elif slot.left == 0:
            x = slot.right + 8
            y = max(16, min(sh - oh - 16, slot.centery - oh // 2))
        else:
            x = slot.left - ow - 8
            y = max(16, min(sh - oh - 16, slot.centery - oh // 2))
        return pygame.Rect(int(x), int(y), int(ow), int(oh))

    # ---- update loop: fingertip hover -> open/close popups, trigger roll -> animate dice & movement
    def update(self, fingertip_meta: List[Dict]):
        # update selection UI fingertip tracking for slot hover indicators
        self.selection_ui.update_with_fingertips(fingertip_meta)
        now = time.time()

        # first handle popups (hover to close) and block underlying buttons for that player
        for pid in list(self.players_selected):
            if self.properties_open.get(pid):
                orect = self._properties_overlay_rect(pid)
                for meta in fingertip_meta:
                    pos = meta.get("pos")
                    hand = meta.get("hand")
                    if not pos:
                        continue
                    key = f"popup:{pid}:{hand}"
                    if orect.collidepoint(pos):
                        if key not in self.popup_hover:
                            self.popup_hover[key] = now
                        else:
                            if (now - self.popup_hover[key]) >= HOVER_TIME_THRESHOLD:
                                # close popup on hover completion
                                self.properties_open[pid] = False
                                # clear popup hover keys for this pid
                                for k in list(self.popup_hover.keys()):
                                    if k.startswith(f"popup:{pid}:"):
                                        self.popup_hover.pop(k, None)
                    else:
                        if key in self.popup_hover:
                            self.popup_hover.pop(key, None)
                # skip processing buttons for this pid while popup open
                continue

            # determine which keys are allowed to start hover timers:
            # - if pid is active player -> allow all buttons
            # - otherwise only allow the player's own Properties button
            rects = self._player_button_rects(pid)
            allowed_keys = {"props"} if pid != self.current else {"roll", "props", "buy"}

            for meta in fingertip_meta:
                pos = meta.get("pos")
                hand = meta.get("hand")
                if not pos:
                    continue
                for key_name, r in rects.items():
                    if key_name not in allowed_keys:
                        # ensure any stale hover keys for disabled keys are cleared
                        for stale_k in [k for k in list(self.button_hover.keys()) if k.startswith(f"{pid}:{key_name}:")]:
                            self.button_hover.pop(stale_k, None)
                            self.button_hover_pos.pop(stale_k, None)
                        continue

                    hkey = f"{pid}:{key_name}:{hand}"
                    if r.collidepoint(pos):
                        if hkey not in self.button_hover:
                            # start hover only if allowed (see above)
                            self.button_hover[hkey] = now
                            self.button_hover_pos[hkey] = pos
                        else:
                            # update follow position
                            self.button_hover_pos[hkey] = pos
                            elapsed = now - self.button_hover[hkey]
                            if elapsed >= HOVER_TIME_THRESHOLD:
                                # trigger actions
                                if key_name == "roll" and pid == self.current and not self.dice_state["rolling"]:
                                    dur = random.uniform(2.0, 4.0)
                                    self.dice_state.update({"rolling": True, "start": now, "end": now + dur, "d1": 0, "d2": 0, "pid": pid})
                                elif key_name == "buy":
                                    if pid == self.current:
                                        self.properties_open[pid] = True
                                elif key_name == "props":
                                    # open the properties overlay for this player (allowed for any player on their own props)
                                    self.properties_open[pid] = True
                                # when a popup opens, clear button hover timers for that pid to avoid immediate re-trigger
                                if self.properties_open.get(pid):
                                    for k in list(self.button_hover.keys()):
                                        if k.startswith(f"{pid}:"):
                                            self.button_hover.pop(k, None)
                                            self.button_hover_pos.pop(k, None)
                                # clear this hover key (one-shot)
                                if hkey in self.button_hover:
                                    self.button_hover.pop(hkey, None)
                                if hkey in self.button_hover_pos:
                                    self.button_hover_pos.pop(hkey, None)
                    else:
                        # moved away: clear hover state
                        if hkey in self.button_hover:
                            self.button_hover.pop(hkey, None)
                        if hkey in self.button_hover_pos:
                            self.button_hover_pos.pop(hkey, None)

        # handle dice finish: create a move_path that will animate at move_per_space rate
        if self.dice_state.get("rolling"):
            if now >= self.dice_state["end"]:
                d1 = random.randint(1, 6)
                d2 = random.randint(1, 6)
                self.dice_state.update({"d1": d1, "d2": d2, "rolling": False})
                pid = self.dice_state["pid"]
                if pid is not None:
                    steps = d1 + d2
                    start_pos = self.players[pid].pos
                    path = [(start_pos + i) % self.board_spaces for i in range(1, steps + 1)]
                    self.players[pid].move_path = path
                    self.players[pid].move_start = now
                    self.players[pid].move_from = start_pos
                    # open popup after move only if the space is ownable/unowned
                    target = path[-1]
                    self.players[pid]._open_after_move = False
                    if 0 <= target < len(self.properties):
                        spec = self.properties[target]
                        if spec.get("color") is not None and self.owners[target] is None:
                            self.players[pid]._open_after_move = True
                    self.last_roll = (d1, d2)
                    # advance current to next selected player now that roll started
                    if self.players_selected:
                        try:
                            idx_in = self.players_selected.index(pid)
                            self.current = self.players_selected[(idx_in + 1) % len(self.players_selected)]
                        except ValueError:
                            pass

        # animate movement completion at per-space intervals
        for p in self.players:
            if p.move_path:
                elapsed = now - p.move_start
                per = p.move_per_space
                total_time = per * len(p.move_path)
                if elapsed >= total_time:
                    p.pos = p.move_path[-1]
                    p.move_path = []
                    p.move_start = 0.0
                    if getattr(p, "_open_after_move", False):
                        self.properties_open[p.idx] = True
                        p._open_after_move = False

    # ---- drawing helpers (use relative font sizes) ----
    def _draw_rotated_text(self, surf: pygame.Surface, text: str, rect: pygame.Rect, angle: int, font: pygame.font.Font, color=(255, 255, 255)):
        txt = font.render(text, True, color)
        if angle != 0:
            txt = pygame.transform.rotate(txt, angle)
        trect = txt.get_rect(center=rect.center)
        surf.blit(txt, trect)

    def draw_board(self):
        sw, sh = self.screen.get_size()
        # dark background
        pygame.draw.rect(self.screen, (20, 80, 30), pygame.Rect(0, 0, sw, sh))

        board_rect = self._compute_board_rect()
        pygame.draw.rect(self.screen, (200, 200, 200), board_rect, width=max(2, int(sw * 0.002)), border_radius=8)
        inner = board_rect.inflate(-max(8, int(sw * 0.01)), -max(8, int(sh * 0.01)))
        pygame.draw.rect(self.screen, (24, 24, 24), inner, border_radius=6)

        # font size relative to board
        font_small = pygame.font.SysFont(None, max(10, int(inner.height * 0.035)))

        for idx in range(40):
            r = self._space_rect_for(idx)
            # shrink a little for padding
            pad = max(2, int(self._grid_cell() * 0.06))
            rr = r.inflate(-pad, -pad)
            color_bg = (180, 180, 180) if idx % 2 == 0 else (200, 200, 200)
            pygame.draw.rect(self.screen, color_bg, rr, border_radius=3)

            spec = self.properties[idx] if idx < len(self.properties) else {"name": f"Space {idx}", "color": None}
            gcolor = spec.get("color")
            # draw color bar toward center of the board: compute where the inner-facing edge is
            gx, gy = self._index_to_grid(idx)
            # bar thickness relative
            thickness = max(3, int(self._grid_cell() * 0.16))
            if gcolor:
                # bottom row -> gy == 9, top -> gy == 0, left -> gx == 0, right -> gx == 9
                if gy == 9:  # bottom row -> bar near top of cell
                    bar = pygame.Rect(rr.left + 2, rr.top + 2, rr.width - 4, thickness)
                elif gx == 0:  # left col -> bar near right of cell
                    bar = pygame.Rect(rr.right - thickness - 2, rr.top + 2, thickness, rr.height - 4)
                elif gy == 0:  # top row -> bar near bottom of cell
                    bar = pygame.Rect(rr.left + 2, rr.bottom - thickness - 2, rr.width - 4, thickness)
                else:  # gx == 9 right column -> bar near left of cell
                    bar = pygame.Rect(rr.left + 2, rr.top + 2, thickness, rr.height - 4)
                pygame.draw.rect(self.screen, gcolor, bar, border_radius=2)

            # draw name, with rotation to face outward
            name = spec.get("name", "")
            # rotation: bottom row -> 0, left col -> 90, top row -> 180, right col -> 270 (so text faces away from center)
            angle = 0
            if gy == 9:
                angle = 0
            elif gx == 0:
                angle = 90
            elif gy == 0:
                angle = 180
            elif gx == 9:
                angle = 270
            # short label render; wrap if long
            max_chars = max(8, int(rr.width / 8))
            if len(name) > max_chars:
                parts = name.split(" ")
                half = len(parts) // 2
                line1 = " ".join(parts[:half])
                line2 = " ".join(parts[half:])
                surf1 = font_small.render(line1, True, (0, 0, 0))
                surf2 = font_small.render(line2, True, (0, 0, 0))
                combined_h = surf1.get_height() + surf2.get_height()
                combined = pygame.Surface((max(surf1.get_width(), surf2.get_width()), combined_h), pygame.SRCALPHA)
                combined.blit(surf1, (0, 0))
                combined.blit(surf2, (0, surf1.get_height()))
                if angle != 0:
                    combined = pygame.transform.rotate(combined, angle)
                crect = combined.get_rect(center=rr.center)
                self.screen.blit(combined, crect)
            else:
                self._draw_rotated_text(self.screen, name, rr, angle, font_small, color=(0, 0, 0))

        # player slots are rendered in draw_player_boards_and_buttons anchored outside the board
        return

    def draw_tokens(self):
        # group static tokens per space then draw moving tokens on top
        static_by_space: Dict[int, List[Player]] = {}
        moving_players: List[Player] = []
        for p in self.players:
            if self.players_selected and p.idx not in self.players_selected:
                continue
            if p.move_path:
                moving_players.append(p)
            else:
                static_by_space.setdefault(p.pos, []).append(p)

        for space, plist in static_by_space.items():
            cx, cy = self._space_coords_for(space)
            n = len(plist)
            if n == 1:
                p = plist[0]
                # smaller token
                pygame.draw.circle(self.screen, (0, 0, 0), (cx + 2, cy + 3), max(6, int(self._grid_cell() * 0.12)))
                pygame.draw.circle(self.screen, p.color, (cx, cy), max(4, int(self._grid_cell() * 0.08)))
            else:
                radius = max(10, int(self._grid_cell() * 0.18))
                for k, p in enumerate(plist):
                    angle = 2 * math.pi * k / n
                    px = int(cx + math.cos(angle) * radius)
                    py = int(cy + math.sin(angle) * radius)
                    pygame.draw.circle(self.screen, (0, 0, 0), (px + 2, py + 3), max(6, int(self._grid_cell() * 0.10)))
                    pygame.draw.circle(self.screen, p.color, (px, py), max(4, int(self._grid_cell() * 0.07)))

        # moving tokens with per-space interpolation and jump
        for p in moving_players:
            elapsed = time.time() - p.move_start
            per = p.move_per_space
            step = int(elapsed // per)
            frac = (elapsed % per) / per if per > 0 else 1.0
            if step >= len(p.move_path):
                sx, sy = self._space_coords_for(p.move_path[-1])
                px, py = sx, sy
            else:
                prev_space = p.move_from if step == 0 else p.move_path[step - 1]
                next_space = p.move_path[step]
                sx, sy = self._space_coords_for(prev_space)
                ex, ey = self._space_coords_for(next_space)
                jump = math.sin(frac * math.pi) * max(6, int(self._grid_cell() * 0.12))
                px = int(sx * (1 - frac) + ex * frac)
                py = int(sy * (1 - frac) + ey * frac - jump)
            pygame.draw.circle(self.screen, (0, 0, 0), (px + 2, py + 3), max(8, int(self._grid_cell() * 0.14)))
            pygame.draw.circle(self.screen, p.color, (px, py), max(6, int(self._grid_cell() * 0.10)))

    def draw_player_boards_and_buttons(self):
        sw, sh = self.screen.get_size()
        font = pygame.font.SysFont(None, max(12, int(sh * 0.03)))
        for pid in list(self.players_selected):
            rect = self._slot_rect_around_board(pid)
            pos = self.selection_ui.positions[pid]
            base_col = self.players[pid].color
            washed = tuple(min(255, int(c * 0.75 + 180 * 0.25)) for c in base_col)
            pygame.draw.rect(self.screen, washed, rect.inflate(8, 8), border_radius=8)
            if pid == self.current:
                pygame.draw.rect(self.screen, (255, 215, 0), rect.inflate(6, 6), width=max(2, int(sw * 0.0025)), border_radius=8)
                lbl = font.render("CURRENT", True, (0, 0, 0))
                self.screen.blit(lbl, (rect.centerx - lbl.get_width() // 2, rect.top + 6))
            rects = self._player_button_rects(pid)
            for key_name, brect in rects.items():
                if key_name == "roll":
                    col = tuple(min(255, int(c * 0.7 + 220 * 0.3)) for c in base_col) if pid == self.current else tuple(min(255, int(c * 0.6 + 200 * 0.4)) for c in base_col)
                elif key_name == "props":
                    col = tuple(min(255, int(c * 0.8 + 200 * 0.2)) for c in base_col)
                else:
                    col = tuple(min(255, int(c * 0.85 + 190 * 0.15)) for c in base_col)
                pygame.draw.rect(self.screen, col, brect, border_radius=8)
                pygame.draw.rect(self.screen, (60, 60, 60), brect, width=1, border_radius=8)
                label_text = "Roll" if key_name == "roll" else ("Properties" if key_name == "props" else "Buy / Mortg.")
                txtsurf = font.render(label_text, True, (0, 0, 0))
                # compute orientation based on where slot is anchored relative to board
                board = self._compute_board_rect()
                cx, cy = rect.center
                if cy < board.top:
                    angle_text = 180
                elif cy > board.bottom:
                    angle_text = 0
                elif cx < board.left:
                    angle_text = 270
                else:
                    angle_text = 90
                if angle_text != 0:
                    txtsurf = pygame.transform.rotate(txtsurf, angle_text)
                self.screen.blit(txtsurf, txtsurf.get_rect(center=brect.center))

        # draw hover progress arcs for button hovers (only those keys that were allowed to start)
        now = time.time()
        ACCENT = (240, 200, 80)
        for key, start in list(self.button_hover.items()):
            pos = self.button_hover_pos.get(key)
            if not pos:
                continue
            elapsed = now - start
            progress = min(1.0, max(0.0, elapsed / HOVER_TIME_THRESHOLD))
            px, py = pos
            # offset relative to screen
            off_x = int(min(48, sw * 0.03))
            off_y = -int(min(48, sh * 0.03))
            arc_rect = pygame.Rect(px + off_x - 20, py + off_y - 20, 40, 40)
            pygame.draw.circle(self.screen, (60, 60, 60), arc_rect.center, 20)
            start_ang = -math.pi / 2
            end_ang = start_ang + progress * 2 * math.pi
            pygame.draw.arc(self.screen, ACCENT, arc_rect, start_ang, end_ang, max(3, int(self._grid_cell() * 0.06)))

        # dice on board center; sized relative to board
        board_rect = self._compute_board_rect()
        cx, cy = board_rect.centerx, board_rect.centery
        die_size = max(28, int(self._grid_cell() * 0.9))
        font_small = pygame.font.SysFont(None, max(10, int(die_size * 0.45)))
        if self.dice_state.get("rolling"):
            # animated rolling faces
            for i in range(2):
                face = random.randint(1, 6)
                dx = (i * (die_size + 8)) - (die_size // 2 + 4)
                dr = pygame.Rect(cx + dx - die_size // 2, cy - die_size // 2, die_size, die_size)
                pygame.draw.rect(self.screen, (255, 255, 255), dr, border_radius=max(6, die_size // 6))
                ftxt = font_small.render(str(face), True, (0, 0, 0))
                self.screen.blit(ftxt, ftxt.get_rect(center=dr.center))
        elif self.dice_state.get("d1", 0) and self.dice_state.get("d2", 0):
            d1 = self.dice_state.get("d1", 0)
            d2 = self.dice_state.get("d2", 0)
            for i, val in enumerate([d1, d2]):
                dx = (i * (die_size + 8)) - (die_size // 2 + 4)
                dr = pygame.Rect(cx + dx - die_size // 2, cy - die_size // 2, die_size, die_size)
                pygame.draw.rect(self.screen, (255, 255, 255), dr, border_radius=max(6, die_size // 6))
                ftxt = font_small.render(str(val), True, (0, 0, 0))
                self.screen.blit(ftxt, ftxt.get_rect(center=dr.center))

    def draw_properties_overlay(self, pid: int):
        # overlay anchored near player's slot and sized relative to screen
        sw, sh = self.screen.get_size()
        ow = min(int(sw * 0.36), 520)
        oh = min(int(sh * 0.48), 480)
        r = self._properties_overlay_rect(pid, ow=ow, oh=oh)
        pygame.draw.rect(self.screen, (28, 28, 28), r, border_radius=8)
        pygame.draw.rect(self.screen, (180, 180, 180), r, width=max(1, int(sw * 0.0015)), border_radius=8)
        font = pygame.font.SysFont(None, max(12, int(sh * 0.03)))
        x0, y0 = r.left + 16, r.top + 16
        self.screen.blit(font.render(f"Player {pid + 1}", True, (255, 255, 255)), (x0, y0))
        self.screen.blit(font.render(f"Money: ${self.players[pid].money}", True, (255, 255, 255)), (x0, y0 + 28))
        y = y0 + 60
        for prop_idx in self.players[pid].properties:
            if prop_idx < len(self.properties):
                p = self.properties[prop_idx]
                pygame.draw.rect(self.screen, p["color"] or (120, 120, 120), pygame.Rect(x0, y, 24, 16))
                self.screen.blit(font.render(p["name"], True, (255, 255, 255)), (x0 + 32, y))
                y += 28

        # hover-close indicator for this overlay (follow finger)
        now = time.time()
        for k, start in list(self.popup_hover.items()):
            try:
                prefix, spid, hand = k.split(":")
                if prefix != "popup":
                    continue
                if int(spid) != pid:
                    continue
                # try to find finger pos from selection_ui hover positions
                hover_pos = None
                for meta in self.selection_ui.get_hover_progress():
                    if meta.get("slot") == pid:
                        hover_pos = meta.get("pos")
                        break
                if hover_pos:
                    px, py = hover_pos
                else:
                    px, py = r.center
                elapsed = now - start
                progress = min(1.0, max(0.0, elapsed / HOVER_TIME_THRESHOLD))
                arc_rect = pygame.Rect(px + 28 - 20, py - 28 - 20, 40, 40)
                pygame.draw.circle(self.screen, (60, 60, 60), arc_rect.center, 20)
                start_ang = -math.pi / 2
                end_ang = start_ang + progress * 2 * math.pi
                pygame.draw.arc(self.screen, (240, 200, 80), arc_rect, start_ang, end_ang, max(3, int(self._grid_cell() * 0.06)))
            except Exception:
                pass

    def draw(self):
        # draw all layers
        self.draw_board()
        self.draw_tokens()
        self.draw_player_boards_and_buttons()
 
        # draw properties overlays above everything else
        for pid in range(len(self.players)):
            if self.properties_open.get(pid):
                self.draw_properties_overlay(pid)
 
        # NOTE: selection-slot hover progress is drawn by the launcher selection screen only.
        # During gameplay we only draw game-level button hover arcs (tracked in self.button_hover).
        # game-level button hover arcs (follow finger)
        now = time.time()
        ACCENT = (240, 200, 80)
        try:
            for key, start in list(self.button_hover.items()):
                pos = self.button_hover_pos.get(key)
                if not pos:
                    continue
                elapsed = now - start
                progress = min(1.0, max(0.0, elapsed / HOVER_TIME_THRESHOLD))
                px, py = pos
                sw, sh = self.screen.get_size()
                off_x = int(min(48, sw * 0.03))
                off_y = -int(min(48, sh * 0.03))
                arc_rect = pygame.Rect(px + off_x - 20, py + off_y - 20, 40, 40)
                pygame.draw.circle(self.screen, (60, 60, 60), arc_rect.center, 20)
                start_ang = -math.pi / 2
                end_ang = start_ang + progress * 2 * math.pi
                pygame.draw.arc(self.screen, ACCENT, arc_rect, start_ang, end_ang, max(3, int(self._grid_cell() * 0.06)))
        except Exception:
            pass

        # draw fingertips (combine selection_ui.hover_pos and game-level hover_pos)
        try:
            pts = set()
            for v in getattr(self.selection_ui, "hover_pos", {}).values():
                if v:
                    pts.add((int(v[0]), int(v[1])))
            for v in self.button_hover_pos.values():
                if v:
                    pts.add((int(v[0]), int(v[1])))
            for (px, py) in pts:
                pygame.draw.circle(self.screen, (255, 255, 255), (px, py), 20)
                try:
                    col = self.selection_ui.closest_player_color((px, py))
                except Exception:
                    col = (200, 200, 200)
                pygame.draw.circle(self.screen, col, (px, py), 14)
                pygame.draw.circle(self.screen, (0, 0, 0), (px, py), 4)
        except Exception:
            pass