import time
import math
import random
import pygame
import pygame.freetype
from typing import List, Dict, Tuple, Optional

from ui_elements import PlayerSelectionUI, HOVER_TIME_THRESHOLD
from ui_components import draw_circular_progress
from constants import (
    PLAYER_COLORS, PROPERTIES, RAILROADS, UTILITIES,
    COMMUNITY_CHEST_CARDS, CHANCE_CARDS, PROPERTY_SPACE_INDICES
)

# Build full board spaces list (40 spaces, US Monopoly order)
BOARD_SPACES = [
    {"name": "Go", "type": "go"},
    PROPERTIES[0],  # Mediterranean Avenue
    {"name": "Community Chest", "type": "community"},
    PROPERTIES[1],  # Baltic Avenue
    {"name": "Income Tax", "type": "tax"},
    RAILROADS[0],   # Reading Railroad
    PROPERTIES[2],  # Oriental Avenue
    {"name": "Chance", "type": "chance"},
    PROPERTIES[3],  # Vermont Avenue
    PROPERTIES[4],  # Connecticut Avenue
    {"name": "Jail / Just Visiting", "type": "jail"},
    PROPERTIES[5],  # St. Charles Place
    UTILITIES[0],   # Electric Company
    PROPERTIES[6],  # States Avenue
    PROPERTIES[7],  # Virginia Avenue
    RAILROADS[1],   # Pennsylvania Railroad
    PROPERTIES[8],  # St. James Place
    {"name": "Community Chest", "type": "community"},
    PROPERTIES[9],  # Tennessee Avenue
    PROPERTIES[10], # New York Avenue
    {"name": "Free Parking", "type": "parking"},
    PROPERTIES[11], # Kentucky Avenue
    {"name": "Chance", "type": "chance"},
    PROPERTIES[12], # Indiana Avenue
    PROPERTIES[13], # Illinois Avenue
    RAILROADS[2],   # B. & O. Railroad
    PROPERTIES[14], # Atlantic Avenue
    PROPERTIES[15], # Ventnor Avenue
    UTILITIES[1],   # Water Works
    PROPERTIES[16], # Marvin Gardens
    {"name": "Go To Jail", "type": "go_to_jail"},
    PROPERTIES[17], # Pacific Avenue
    PROPERTIES[18], # North Carolina Avenue
    {"name": "Community Chest", "type": "community"},
    PROPERTIES[19], # Pennsylvania Avenue
    RAILROADS[3],   # Short Line Railroad
    {"name": "Chance", "type": "chance"},
    PROPERTIES[20], # Park Place
    {"name": "Luxury Tax", "type": "tax"},
    PROPERTIES[21], # Boardwalk
]

class Player:
    def __init__(self, idx: int, color: Tuple[int, int, int]):
        self.idx = idx
        self.color = color
        self.money = 1500
        self.pos = 0
        self.properties: List[int] = []
        self.move_path: List[int] = []
        self.move_start: float = 0.0
        self.move_per_space: float = 0.25
        self.move_from: Optional[int] = None
        self._open_after_move = False

class MonopolyGame:
    def __init__(self, screen: pygame.Surface, hand_to_screen_fn):
        self.screen = screen
        self.hand_to_screen = hand_to_screen_fn
        self.selection_ui = PlayerSelectionUI(screen)
        self.players = [Player(i, PLAYER_COLORS[i]) for i in range(8)]
        self.players_selected: List[int] = []
        self.current = 0
        self.board_spaces = 40
        self.owners: List[Optional[int]] = [None] * self.board_spaces
        self.properties = BOARD_SPACES.copy()

        self.button_hover: Dict[str, float] = {}
        self.button_hover_pos: Dict[str, Tuple[int, int]] = {}
        self.popup_hover: Dict[str, float] = {}
        self.properties_open: Dict[int, bool] = {i: False for i in range(8)}

        self.dice_state: Dict = {"rolling": False, "start": 0.0, "end": 0.0, "d1": 0, "d2": 0, "pid": None}
        self.last_roll = (0, 0)
        self._last_button_rects: Dict[int, Dict[str, pygame.Rect]] = {}

    def _compute_board_rect(self) -> pygame.Rect:
        w, h = self.screen.get_size()
        top_h = int(h * 0.10) + 16
        bot_h = int(h * 0.10) + 16
        side_w = int(w * 0.12) + 16
        avail_x = side_w
        avail_y = top_h
        avail_w = w - side_w * 2
        avail_h = h - top_h - bot_h
        size = max(0, min(avail_w, avail_h))
        bx = avail_x + (avail_w - size) // 2
        by = avail_y + (avail_h - size) // 2
        return pygame.Rect(int(bx), int(by), int(size), int(size))

    def _grid_cell(self) -> float:
        board = self._compute_board_rect()
        return board.width / 10.0

    def _index_to_grid(self, idx: int) -> Tuple[int, int]:
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

    def _space_rect_for(self, idx: int) -> pygame.Rect:
        board = self._compute_board_rect()
        cell = self._grid_cell()
        gx, gy = self._index_to_grid(idx)
        left = board.left + gx * cell
        top = board.top + gy * cell
        return pygame.Rect(int(round(left)), int(round(top)), int(math.ceil(cell)), int(math.ceil(cell)))

    def _space_coords_for(self, idx: int) -> Tuple[int, int]:
        r = self._space_rect_for(idx)
        return r.centerx, r.centery

    def _player_button_rects(self, pid: int) -> Dict[str, pygame.Rect]:
        rect = self.selection_ui.slot_rect(pid)
        w, h = self.screen.get_size()
        x, y = self.selection_ui.positions[pid]
        gap = max(6, int(min(rect.width, rect.height) * 0.06))
        xpad = max(6, int(rect.width * 0.06))
        ypad = max(6, int(rect.height * 0.06))
        rects: Dict[str, pygame.Rect] = {}
        if y == 0 or y == h:
            total_w = rect.width - xpad * 2
            btn_w = max(48, (total_w - gap * 2) // 3)
            btn_h = max(28, rect.height - ypad * 2)
            start_x = rect.left + xpad + (total_w - (btn_w * 3 + gap * 2)) // 2
            yy = rect.top + ypad
            for i, key in enumerate(["roll", "props", "buy"]):
                bx = start_x + i * (btn_w + gap)
                rects[key] = pygame.Rect(bx, yy, btn_w, btn_h)
        else:
            btn_w = max(48, rect.width - xpad * 2)
            total_btn_h = rect.height - (gap * 4)
            btn_h = max(26, total_btn_h // 3)
            xx = rect.left + xpad
            yy = rect.top + gap
            rects["roll"] = pygame.Rect(xx, yy, btn_w, btn_h)
            rects["props"] = pygame.Rect(xx, yy + btn_h + gap, btn_w, btn_h)
            rects["buy"] = pygame.Rect(xx, yy + 2 * (btn_h + gap), btn_w, btn_h)
        self._last_button_rects[pid] = rects
        return rects

    def update(self, fingertip_meta: List[Dict]):
        self.selection_ui.update_with_fingertips(fingertip_meta)
        now = time.time()
        for pid in list(self.players_selected):
            if self.properties_open.get(pid):
                panel_rect = self.selection_ui.slot_rect(pid)
                for meta in fingertip_meta:
                    pos = meta.get("pos")
                    hand = meta.get("hand")
                    if not pos:
                        continue
                    key = f"popup:{pid}:{hand}"
                    if panel_rect.collidepoint(pos):
                        if key not in self.popup_hover:
                            self.popup_hover[key] = now
                        else:
                            if (now - self.popup_hover[key]) >= HOVER_TIME_THRESHOLD:
                                self.properties_open[pid] = False
                                for k in list(self.popup_hover.keys()):
                                    if k.startswith(f"popup:{pid}:"):
                                        self.popup_hover.pop(k, None)
                    else:
                        if key in self.popup_hover:
                            self.popup_hover.pop(key, None)
                continue

            rects = self._player_button_rects(pid)
            allowed = {"props"} if pid != self.current else {"roll", "props", "buy"}

            for meta in fingertip_meta:
                pos = meta.get("pos")
                hand = meta.get("hand")
                if not pos:
                    continue
                for key_name, r in rects.items():
                    if key_name not in allowed:
                        for stale_k in [k for k in list(self.button_hover.keys()) if k.startswith(f"{pid}:{key_name}:")]:
                            self.button_hover.pop(stale_k, None)
                            self.button_hover_pos.pop(stale_k, None)
                        continue
                    hkey = f"{pid}:{key_name}:{hand}"
                    if r.collidepoint(pos):
                        if hkey not in self.button_hover:
                            self.button_hover[hkey] = now
                            self.button_hover_pos[hkey] = pos
                        else:
                            self.button_hover_pos[hkey] = pos
                            elapsed = now - self.button_hover[hkey]
                            if elapsed >= HOVER_TIME_THRESHOLD:
                                if key_name == "roll" and pid == self.current and not self.dice_state["rolling"]:
                                    dur = random.uniform(2.0, 4.0)
                                    self.dice_state.update({"rolling": True, "start": now, "end": now + dur, "d1": 0, "d2": 0, "pid": pid})
                                elif key_name == "buy":
                                    if pid == self.current:
                                        self.properties_open[pid] = True
                                elif key_name == "props":
                                    self.properties_open[pid] = True
                                if self.properties_open.get(pid):
                                    for k in list(self.button_hover.keys()):
                                        if k.startswith(f"{pid}:"):
                                            self.button_hover.pop(k, None)
                                            self.button_hover_pos.pop(k, None)
                                if hkey in self.button_hover:
                                    self.button_hover.pop(hkey, None)
                                if hkey in self.button_hover_pos:
                                    self.button_hover_pos.pop(hkey, None)
                    else:
                        if hkey in self.button_hover:
                            self.button_hover.pop(hkey, None)
                        if hkey in self.button_hover_pos:
                            self.button_hover_pos.pop(hkey, None)

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
                    target = path[-1]
                    self.players[pid]._open_after_move = False
                    if 0 <= target < len(self.properties):
                        spec = self.properties[target]
                        if spec.get("color") is not None and self.owners[target] is None:
                            self.players[pid]._open_after_move = True
                    self.last_roll = (d1, d2)
                    if self.players_selected:
                        try:
                            idx_in = self.players_selected.index(pid)
                            self.current = self.players_selected[(idx_in + 1) % len(self.players_selected)]
                        except ValueError:
                            pass

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

    def _draw_rotated_text(self, surf: pygame.Surface, text: str, rect: pygame.Rect, angle: int, font: pygame.font.Font, color=(255, 255, 255)):
        txt = font.render(text, True, color)
        if angle != 0:
            txt = pygame.transform.rotate(txt, angle)
        trect = txt.get_rect(center=rect.center)
        surf.blit(txt, trect)

    def _draw_properties_popup_in_panel(self, pid: int, panel_rect: pygame.Rect):
        inner = panel_rect.inflate(-8, -8)
        pygame.draw.rect(self.screen, (28, 28, 28), inner, border_radius=8)
        pygame.draw.rect(self.screen, (180, 180, 180), inner, width=2, border_radius=8)
        font = pygame.font.SysFont(None, max(12, int(panel_rect.height * 0.18)))
        x0, y0 = inner.left + 12, inner.top + 10
        self.screen.blit(font.render(f"Player {pid + 1}", True, (255, 255, 255)), (x0, y0))
        self.screen.blit(font.render(f"Money: ${self.players[pid].money}", True, (255, 255, 255)), (x0, y0 + 24))
        y = y0 + 52
        row_h = max(20, int(panel_rect.height * 0.22))
        for prop_idx in self.players[pid].properties[:5]:
            if prop_idx < len(self.properties):
                p = self.properties[prop_idx]
                color = p.get("color", (120, 120, 120))
                name = p.get("name", "")
                pygame.draw.rect(self.screen, color, pygame.Rect(x0, y, 20, 14))
                self.screen.blit(font.render(name, True, (255, 255, 255)), (x0 + 26, y - 2))
                y += row_h
        now = time.time()
        for k, start in list(self.popup_hover.items()):
            try:
                prefix, spid, hand = k.split(":")
                if prefix != "popup" or int(spid) != pid:
                    continue
                hover_pos = None
                for meta in self.selection_ui.get_hover_progress():
                    if meta.get("slot") == pid:
                        hover_pos = meta.get("pos")
                        break
                px, py = hover_pos if hover_pos else inner.center
                progress = min(1.0, max(0.0, (now - start) / HOVER_TIME_THRESHOLD))
                center = (px + 24, py - 24)
                draw_circular_progress(self.screen, center, radius=18, progress=progress, thickness=max(3, int(panel_rect.height * 0.08)))
            except Exception:
                pass

    @staticmethod
    def _fit_text_to_rect(text, rect, min_font=8, max_font=22, color=(0,0,0), pad=4):
        font_name = pygame.font.get_default_font()
        width, height = rect.width - pad*2, rect.height - pad*2
        for font_size in range(max_font, min_font-1, -1):
            font = pygame.freetype.SysFont(font_name, font_size)
            words = text.split()
            lines = []
            current = ""
            for word in words:
                test = current + (" " if current else "") + word
                rect_test = font.get_rect(test)
                if rect_test.width > width and current:
                    lines.append(current)
                    current = word
                else:
                    current = test
            if current:
                lines.append(current)
            total_height = sum(font.get_rect(line).height for line in lines)
            if total_height <= height and all(font.get_rect(line).width <= width for line in lines):
                surfaces = []
                y = rect.top + pad + (height - total_height)//2
                for line in lines:
                    surf, _ = font.render(line, color)
                    surf_rect = surf.get_rect(centerx=rect.centerx)
                    surf_rect.top = y
                    surfaces.append((surf, surf_rect.topleft))
                    y += surf.get_height()
                return surfaces
        font = pygame.freetype.SysFont(font_name, min_font)
        surf, _ = font.render(text, color)
        surf_rect = surf.get_rect(center=rect.center)
        return [(surf, surf_rect.topleft)]

    def draw_board(self):
        sw, sh = self.screen.get_size()
        pygame.draw.rect(self.screen, (20, 80, 30), pygame.Rect(0, 0, sw, sh))
        board_rect = self._compute_board_rect()
        pygame.draw.rect(self.screen, (200, 200, 200), board_rect, width=max(2, int(sw * 0.002)), border_radius=8)
        inner = board_rect.inflate(-max(8, int(sw * 0.01)), -max(8, int(sh * 0.01)))
        pygame.draw.rect(self.screen, (24, 24, 24), inner, border_radius=6)
        for idx, spec in enumerate(self.properties):
            r = self._space_rect_for(idx)
            pad = max(2, int(self._grid_cell() * 0.06))
            rr = r.inflate(-pad, -pad)
            color_bg = (180, 180, 180) if idx % 2 == 0 else (200, 200, 200)
            pygame.draw.rect(self.screen, color_bg, rr, border_radius=3)
            gcolor = spec.get("color")
            gx, gy = self._index_to_grid(idx)
            thickness = max(3, int(self._grid_cell() * 0.16))
            if gcolor:
                if gy == 9:
                    bar = pygame.Rect(rr.left + 2, rr.top + 2, rr.width - 4, thickness)
                elif gx == 0:
                    bar = pygame.Rect(rr.right - thickness - 2, rr.top + 2, thickness, rr.height - 4)
                elif gy == 0:
                    bar = pygame.Rect(rr.left + 2, rr.bottom - thickness - 2, rr.width - 4, thickness)
                else:
                    bar = pygame.Rect(rr.left + 2, rr.top + 2, thickness, rr.height - 4)
                pygame.draw.rect(self.screen, gcolor, bar, border_radius=2)
            # --- Text rendering logic inside the loop ---
            name = spec.get("name", "")
            if idx == 0:
                name = "Go"
            angle = 0 if gy == 9 else (90 if gx == 0 else (180 if gy == 0 else 270))
            surfaces = self._fit_text_to_rect(name, rr, min_font=8, max_font=22, color=(0,0,0), pad=6)
            for surf, pos in surfaces:
                if angle != 0:
                    surf = pygame.transform.rotate(surf, angle)
                    if angle == 180:
                        surf = pygame.transform.flip(surf, True, True)
                    elif angle == 270:
                        surf = pygame.transform.flip(surf, True, False)
                self.screen.blit(surf, pos)

    def draw_tokens(self):
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
                pygame.draw.circle(self.screen, (0, 0, 0), (cx + 2, cy + 3), max(6, int(self._grid_cell() * 0.12)))
                pygame.draw.circle(self.screen, p.color, (cx, cy), max(4, int(self._grid_cell() * 0.08)))
            else:
                radius = max(10, int(self._grid_cell() * 0.18))
                for k, p in enumerate(plist):
                    ang = 2 * math.pi * k / n
                    px = int(cx + math.cos(ang) * radius)
                    py = int(cy + math.sin(ang) * radius)
                    pygame.draw.circle(self.screen, (0, 0, 0), (px + 2, py + 3), max(6, int(self._grid_cell() * 0.10)))
                    pygame.draw.circle(self.screen, p.color, (px, py), max(4, int(self._grid_cell() * 0.07)))
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
            rect = self.selection_ui.slot_rect(pid)
            x, y = self.selection_ui.positions[pid]
            base_col = self.players[pid].color
            washed = tuple(min(255, int(c * 0.75 + 180 * 0.25)) for c in base_col)
            pygame.draw.rect(self.screen, washed, rect.inflate(8, 8), border_radius=8)
            if pid == self.current:
                pygame.draw.rect(self.screen, (255, 215, 0), rect.inflate(6, 6), width=max(2, int(sw * 0.0025)), border_radius=8)
                lbl = font.render("CURRENT", True, (0, 0, 0))
                self.screen.blit(lbl, (rect.centerx - lbl.get_width() // 2, rect.top + 6))
            if self.properties_open.get(pid):
                self._draw_properties_popup_in_panel(pid, rect)
                continue
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
                angle_text = 0 if y == sh else (180 if y == 0 else (270 if x == 0 else 90))
                if angle_text != 0:
                    txtsurf = pygame.transform.rotate(txtsurf, angle_text)
                self.screen.blit(txtsurf, txtsurf.get_rect(center=brect.center))
        now = time.time()
        for key, start in list(self.button_hover.items()):
            pos = self.button_hover_pos.get(key)
            if not pos:
                continue
            elapsed = now - start
            progress = min(1.0, max(0.0, elapsed / HOVER_TIME_THRESHOLD))
            px, py = pos
            off_x = int(min(48, sw * 0.03))
            off_y = -int(min(48, sh * 0.03))
            center = (px + off_x, py + off_y)
            draw_circular_progress(self.screen, center, radius=20, progress=progress, thickness=max(3, int(self._grid_cell() * 0.06)))
        board_rect = self._compute_board_rect()
        cx, cy = board_rect.centerx, board_rect.centery
        die_size = max(28, int(self._grid_cell() * 0.9))
        font_small = pygame.font.SysFont(None, max(10, int(die_size * 0.45)))
        if self.dice_state.get("rolling"):
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

    def draw(self):
        self.draw_board()
        self.draw_tokens()
        self.draw_player_boards_and_buttons()
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