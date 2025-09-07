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
        self.properties_page: Dict[int, int] = {i: 0 for i in range(8)}
        
        self.buy_prompt: Dict = {}
        self.buy_prompt_hover: Dict[str, float] = {}
        self.buy_prompt_hover_pos: Dict[str, Tuple[int, int]] = {}

        self.dice_state: Dict = {"rolling": False, "start": 0.0, "end": 0.0, "d1": 0, "d2": 0, "pid": None}
        self.last_roll = (0, 0)
        self.player_has_rolled = False
        self._last_button_rects: Dict[int, Dict[str, pygame.Rect]] = {}
        self._board_geom = self._get_board_geom()

    def _compute_board_rect(self) -> pygame.Rect:
        w, h = self.screen.get_size()
        top_panel_h = int(h * 0.10)
        side_panel_w = int(w * 0.12)
        padding = 16
        avail_x = side_panel_w + padding
        avail_y = top_panel_h + padding
        avail_w = w - 2 * side_panel_w - 2 * padding
        avail_h = h - 2 * top_panel_h - 2 * padding
        size = max(0, min(avail_w, avail_h))
        board_x = avail_x + (avail_w - size) // 2
        board_y = avail_y + (avail_h - size) // 2
        return pygame.Rect(int(board_x), int(board_y), int(size), int(size))

    def _get_board_geom(self):
        board_rect = self._compute_board_rect()
        ratio = 1.6
        num_side_props = 9
        total_units = num_side_props + 2 * ratio
        short_side = board_rect.width / total_units
        long_side = short_side * ratio
        return {
            "board_rect": board_rect,
            "short": short_side,
            "long": long_side,
            "corner": long_side,
        }

    def _index_to_grid(self, idx: int) -> Tuple[int, int]:
        if 0 <= idx <= 10: return 10 - idx, 10
        if 11 <= idx <= 20: return 0, 10 - (idx - 10)
        if 21 <= idx <= 30: return idx - 20, 0
        if 31 <= idx <= 39: return 10, idx - 30
        return 0, 0

    def _space_rect_for(self, idx: int) -> pygame.Rect:
        geom = self._board_geom
        board, short, long, corner = geom["board_rect"], geom["short"], geom["long"], geom["corner"]
        gx, gy = self._index_to_grid(idx)
        is_corner = (gx in (0, 10) and gy in (0, 10))
        if is_corner:
            w, h = corner, corner
            x = board.left if gx == 0 else board.right - corner
            y = board.top if gy == 0 else board.bottom - corner
        elif gy in (0, 10):
            w, h = short, long
            x = board.left + corner + (gx - 1) * short
            y = board.top if gy == 0 else board.bottom - long
        else:
            w, h = long, short
            y = board.top + corner + (gy - 1) * short
            x = board.left if gx == 0 else board.right - long
        return pygame.Rect(x, y, w, h)

    def _space_coords_for(self, idx: int) -> Tuple[int, int]:
        r = self._space_rect_for(idx)
        return r.centerx, r.centery

    def _get_panel_orientation(self, pid: int) -> int:
        w, h = self.screen.get_size()
        x, y = self.selection_ui.positions[pid]
        if y == 0: return 180
        if x == 0: return 270
        if x == w: return 90
        return 0

    def _get_grid_rect(self, panel_rect: pygame.Rect, grid_pos: Tuple[int, int, int, int], grid_dims: Tuple[int, int] = (12, 4)) -> pygame.Rect:
        """Calculates a screen rect from grid coordinates within a panel."""
        gx, gy, gw, gh = grid_pos
        grid_w, grid_h = grid_dims
        
        cell_w = panel_rect.width / grid_w
        cell_h = panel_rect.height / grid_h
        
        x = panel_rect.left + gx * cell_w
        y = panel_rect.top + gy * cell_h
        w = gw * cell_w
        h = gh * cell_h
        
        return pygame.Rect(x, y, w, h)

    def _player_button_rects(self, pid: int) -> Dict[str, pygame.Rect]:
        panel_rect = self.selection_ui.slot_rect(pid)
        angle = self._get_panel_orientation(pid)
        is_vertical = angle in (90, 270)
        
        rects = {}
        if is_vertical:
            grid_dims = (4, 12)
            rects["roll"] = self._get_grid_rect(panel_rect, (0.5, 1, 3, 2), grid_dims)
            rects["end_turn"] = self._get_grid_rect(panel_rect, (0.5, 3.5, 3, 2), grid_dims)
            rects["props"] = self._get_grid_rect(panel_rect, (0.5, 6, 3, 2), grid_dims)
            rects["mortgage"] = self._get_grid_rect(panel_rect, (0.5, 8.5, 3, 2), grid_dims)
        else:
            grid_dims = (12, 4)
            rects["roll"] = self._get_grid_rect(panel_rect, (1, 1, 2, 2), grid_dims)
            rects["end_turn"] = self._get_grid_rect(panel_rect, (3.5, 1, 2, 2), grid_dims)
            rects["props"] = self._get_grid_rect(panel_rect, (6.5, 1, 2, 2), grid_dims)
            rects["mortgage"] = self._get_grid_rect(panel_rect, (9, 1, 2, 2), grid_dims)
            
        self._last_button_rects[pid] = rects
        return rects

    def _get_buy_prompt_button_rects(self, pid: int) -> Dict[str, pygame.Rect]:
        panel_rect = self.selection_ui.slot_rect(pid)
        angle = self._get_panel_orientation(pid)
        is_vertical = angle in (90, 270)
        
        if is_vertical:
            grid_dims = (4, 12)
            return {
                "yes": self._get_grid_rect(panel_rect, (0.5, 7, 3, 2), grid_dims),
                "no": self._get_grid_rect(panel_rect, (0.5, 9.5, 3, 2), grid_dims)
            }
        else:
            grid_dims = (12, 4)
            if angle == 0: # Bottom
                return {
                    "yes": self._get_grid_rect(panel_rect, (2, 2.5, 3, 1), grid_dims),
                    "no": self._get_grid_rect(panel_rect, (7, 2.5, 3, 1), grid_dims)
                }
            else: # Top
                return {
                    "yes": self._get_grid_rect(panel_rect, (2, 0.5, 3, 1), grid_dims),
                    "no": self._get_grid_rect(panel_rect, (7, 0.5, 3, 1), grid_dims)
                }

    def _advance_turn(self):
        if self.players_selected:
            try:
                idx_in = self.players_selected.index(self.current)
                self.current = self.players_selected[(idx_in + 1) % len(self.players_selected)]
            except ValueError:
                self.current = self.players_selected[0] if self.players_selected else 0
        self.player_has_rolled = False
        self.dice_state = {"rolling": False, "d1": 0, "d2": 0}

    def update(self, fingertip_meta: List[Dict]):
        now = time.time()

        # --- Handle User Input ---
        if self.buy_prompt:
            pid = self.buy_prompt.get("pid")
            prop_idx = self.buy_prompt.get("prop_idx")
            action = None
            for meta in fingertip_meta:
                pos, hand = meta.get("pos"), meta.get("hand")
                if not pos: continue
                for key_name, r in self.buy_prompt["buttons"].items():
                    hkey = f"buy:{pid}:{key_name}:{hand}"
                    if r.collidepoint(pos):
                        if hkey not in self.buy_prompt_hover: self.buy_prompt_hover[hkey] = now
                        self.buy_prompt_hover_pos[hkey] = pos
                        if (now - self.buy_prompt_hover[hkey]) >= HOVER_TIME_THRESHOLD: action = key_name
                    else:
                        self.buy_prompt_hover.pop(hkey, None); self.buy_prompt_hover_pos.pop(hkey, None)
            
            if action:
                if action == "yes":
                    player = self.players[pid]
                    prop = self.properties[prop_idx]
                    price = prop.get("price", 0)
                    if player.money >= price:
                        player.money -= price
                        player.properties.append(prop_idx)
                        self.owners[prop_idx] = pid
                self.buy_prompt = {}; self.buy_prompt_hover.clear(); self.buy_prompt_hover_pos.clear()
                return

        self.selection_ui.update_with_fingertips(fingertip_meta)
        
        for pid in list(self.players_selected):
            if self.properties_open.get(pid) or self.buy_prompt.get("pid") == pid:
                if self.properties_open.get(pid):
                    self._handle_properties_popup_input(pid, fingertip_meta, now)
                continue

            rects = self._player_button_rects(pid)
            is_current_player = pid == self.current
            allowed = {"props", "mortgage"}
            if is_current_player and not self.player_has_rolled and not self.dice_state["rolling"]:
                allowed.add("roll")
            if is_current_player and self.player_has_rolled and not self.buy_prompt:
                allowed.add("end_turn")

            for meta in fingertip_meta:
                pos, hand = meta.get("pos"), meta.get("hand")
                if not pos: continue
                for key_name, r in rects.items():
                    if key_name not in allowed:
                        for k in [k for k in list(self.button_hover.keys()) if k.startswith(f"{pid}:{key_name}:")]:
                            self.button_hover.pop(k, None); self.button_hover_pos.pop(k, None)
                        continue
                    hkey = f"{pid}:{key_name}:{hand}"
                    if r.collidepoint(pos):
                        if hkey not in self.button_hover: self.button_hover[hkey] = now
                        self.button_hover_pos[hkey] = pos
                        if (now - self.button_hover[hkey]) >= HOVER_TIME_THRESHOLD:
                            if key_name == "roll":
                                dur = random.uniform(1.5, 2.5)
                                self.dice_state.update({"rolling": True, "start": now, "end": now + dur, "pid": pid})
                            elif key_name == "end_turn": self._advance_turn()
                            elif key_name in ["props", "mortgage"]: self.properties_open[pid] = True
                            for k in list(self.button_hover.keys()):
                                if k.startswith(f"{pid}:"): self.button_hover.pop(k, None); self.button_hover_pos.pop(k, None)
                    else:
                        if hkey in self.button_hover: self.button_hover.pop(hkey, None)
                        if hkey in self.button_hover_pos: self.button_hover_pos.pop(hkey, None)

        # --- Update Game State from Timed Events ---
        if self.dice_state.get("rolling") and now >= self.dice_state["end"]:
            d1, d2 = random.randint(1, 6), random.randint(1, 6)
            self.dice_state.update({"d1": d1, "d2": d2, "rolling": False})
            self.player_has_rolled = True
            pid = self.dice_state["pid"]
            if pid is not None:
                steps = d1 + d2
                p = self.players[pid]
                p.move_path = [(p.pos + i) % self.board_spaces for i in range(1, steps + 1)]
                p.move_start, p.move_from = now, p.pos
                target = p.move_path[-1]
                spec = self.properties[target]
                p._open_after_move = spec.get("price") and self.owners[target] is None
                self.last_roll = (d1, d2)

        for p in self.players:
            if p.move_path and now - p.move_start >= p.move_per_space * len(p.move_path):
                p.pos = p.move_path[-1]
                p.move_path, p.move_start = [], 0.0
                if p._open_after_move:
                    p._open_after_move = False
                    prop_idx = p.pos
                    spec = self.properties[prop_idx]
                    self.buy_prompt = {
                        "pid": p.idx, "prop_idx": prop_idx,
                        "buttons": self._get_buy_prompt_button_rects(p.idx),
                        "can_afford": p.money >= spec.get("price", 9999)
                    }

    def _handle_properties_popup_input(self, pid, fingertip_meta, now):
        panel_rect = self.selection_ui.slot_rect(pid)
        
        # Pagination buttons
        page_buttons = self._get_properties_popup_pagination_rects(pid)
        player_props = self.players[pid].properties
        props_per_page = 6
        max_page = (len(player_props) - 1) // props_per_page
        
        action = None
        for meta in fingertip_meta:
            pos, hand = meta.get("pos"), meta.get("hand")
            if not pos: continue
            
            # Check pagination buttons
            for btn_name, r in page_buttons.items():
                if r and r.collidepoint(pos):
                    hkey = f"prop_page:{pid}:{btn_name}:{hand}"
                    if hkey not in self.popup_hover: self.popup_hover[hkey] = now
                    elif (now - self.popup_hover[hkey]) >= HOVER_TIME_THRESHOLD:
                        action = btn_name
                        self.popup_hover.pop(hkey, None) # Consume action
            
            # Check close popup
            hkey = f"popup_close:{pid}:{hand}"
            if panel_rect.collidepoint(pos) and not any(r.collidepoint(pos) for r in page_buttons.values() if r):
                if hkey not in self.popup_hover: self.popup_hover[hkey] = now
                elif (now - self.popup_hover[hkey]) >= HOVER_TIME_THRESHOLD:
                    action = "close"
                    self.popup_hover.pop(hkey, None)
            else:
                self.popup_hover.pop(hkey, None)

        if action == "next" and self.properties_page[pid] < max_page:
            self.properties_page[pid] += 1
        elif action == "prev" and self.properties_page[pid] > 0:
            self.properties_page[pid] -= 1
        elif action == "close":
            self.properties_open[pid] = False
            self.properties_page[pid] = 0
            for k in list(self.popup_hover.keys()):
                if k.startswith(f"prop_page:{pid}:") or k.startswith(f"popup_close:{pid}:"):
                    self.popup_hover.pop(k, None)

    def _draw_rotated_text(self, text, font, color, center, angle, max_width=None):
        if max_width:
            if font.size(text)[0] > max_width:
                text = text[:int(len(text) * max_width / font.size(text)[0])] + "..."
        text_surf = font.render(text, True, color)
        rotated_surf = pygame.transform.rotate(text_surf, angle)
        self.screen.blit(rotated_surf, rotated_surf.get_rect(center=center))

    def _get_properties_popup_pagination_rects(self, pid):
        panel_rect = self.selection_ui.slot_rect(pid)
        angle = self._get_panel_orientation(pid)
        is_vertical = angle in (90, 270)
        
        if is_vertical:
            grid_dims = (4, 12)
            prev_rect = self._get_grid_rect(panel_rect, (0.5, 10, 1.5, 1.5), grid_dims)
            next_rect = self._get_grid_rect(panel_rect, (2, 10, 1.5, 1.5), grid_dims)
        else:
            grid_dims = (12, 4)
            if angle == 0: # Bottom
                prev_rect = self._get_grid_rect(panel_rect, (0.5, 2.75, 2, 1), grid_dims)
                next_rect = self._get_grid_rect(panel_rect, (9.5, 2.75, 2, 1), grid_dims)
            else: # Top
                prev_rect = self._get_grid_rect(panel_rect, (0.5, 0.25, 2, 1), grid_dims)
                next_rect = self._get_grid_rect(panel_rect, (9.5, 0.25, 2, 1), grid_dims)
        return {"prev": prev_rect, "next": next_rect}

    def _draw_properties_popup_in_panel(self, pid: int, panel_rect: pygame.Rect):
        inner = panel_rect.inflate(-8, -8)
        pygame.draw.rect(self.screen, (28, 28, 28), inner, border_radius=8)
        pygame.draw.rect(self.screen, (180, 180, 180), inner, width=2, border_radius=8)
        
        angle = self._get_panel_orientation(pid)
        is_vertical = angle in (90, 270)
        grid_dims = (4, 12) if is_vertical else (12, 4)
        
        font_size = int(panel_rect.height * 0.08) if is_vertical else int(panel_rect.height * 0.18)
        font = pygame.font.SysFont(None, max(12, font_size))
        prop_font = pygame.font.SysFont(None, max(10, int(font_size * 0.85)))

        # --- Draw Title and Money ---
        if is_vertical:
            title_rect = self._get_grid_rect(panel_rect, (0, 0.5, 4, 1), grid_dims)
            money_rect = self._get_grid_rect(panel_rect, (0, 1.5, 4, 1), grid_dims)
        else:
            y_pos = 0.25 if angle == 0 else 2.75
            title_rect = self._get_grid_rect(panel_rect, (0, y_pos, 12, 1), grid_dims)
            money_rect = self._get_grid_rect(panel_rect, (0, y_pos + 0.75, 12, 1), grid_dims)

        self._draw_rotated_text(f"Player {pid + 1}'s Properties", font, (255, 255, 255), title_rect.center, angle)
        self._draw_rotated_text(f"Money: ${self.players[pid].money}", font, (255, 255, 255), money_rect.center, angle)

        # --- Draw Properties in a Grid ---
        player_props = self.players[pid].properties
        props_per_page = 6
        page = self.properties_page[pid]
        start_idx = page * props_per_page
        end_idx = start_idx + props_per_page
        
        prop_grid_origin_y = 3 if is_vertical else (1.25 if angle == 0 else 0.25)
        prop_grid_h = 6 if is_vertical else 1.5
        
        for i, prop_idx in enumerate(player_props[start_idx:end_idx]):
            p = self.properties[prop_idx]
            color = p.get("color") or ((150,150,150) if "Railroad" in p["name"] else (200,200,200))
            
            col = i % 2
            row = i // 2
            
            if is_vertical:
                prop_rect = self._get_grid_rect(panel_rect, (0.5 + col * 1.75, prop_grid_origin_y + row * 2, 1.5, 1.8), grid_dims)
            else:
                prop_rect = self._get_grid_rect(panel_rect, (0.5 + col * 5.75, prop_grid_origin_y, 5.5, 1.5), grid_dims)
                prop_grid_origin_y += 0.5 if col == 1 else 0 # Stagger rows for horizontal
            
            color_bar_h = prop_rect.height * 0.2
            color_bar = pygame.Rect(prop_rect.left, prop_rect.top, prop_rect.width, color_bar_h)
            pygame.draw.rect(self.screen, color, color_bar)
            
            text_center = (prop_rect.centerx, prop_rect.top + color_bar_h + (prop_rect.height - color_bar_h) / 2)
            self._draw_rotated_text(p.get("name", ""), prop_font, (255, 255, 255), text_center, angle, prop_rect.width * 0.9)

        # --- Draw Pagination ---
        page_buttons = self._get_properties_popup_pagination_rects(pid)
        max_page = (len(player_props) - 1) // props_per_page
        
        if page > 0:
            pygame.draw.rect(self.screen, (100, 180, 250), page_buttons["prev"], border_radius=6)
            self._draw_rotated_text("Prev", font, (0,0,0), page_buttons["prev"].center, angle)
        if page < max_page:
            pygame.draw.rect(self.screen, (100, 180, 250), page_buttons["next"], border_radius=6)
            self._draw_rotated_text("Next", font, (0,0,0), page_buttons["next"].center, angle)

    def _draw_buy_prompt(self):
        pid = self.buy_prompt.get("pid")
        if pid is None: return
        panel_rect = self.selection_ui.slot_rect(pid)
        inner = panel_rect.inflate(-8, -8)
        pygame.draw.rect(self.screen, (28, 28, 28), inner, border_radius=8)
        pygame.draw.rect(self.screen, (255, 215, 0), inner, width=2, border_radius=8)
        
        prop = self.properties[self.buy_prompt["prop_idx"]]
        angle = self._get_panel_orientation(pid)
        is_vertical = angle in (90, 270)
        grid_dims = (4, 12) if is_vertical else (12, 4)

        font_size = int(panel_rect.height * 0.1) if is_vertical else int(panel_rect.height * 0.22)
        title_font = pygame.font.SysFont(None, max(16, font_size))
        price_font = pygame.font.SysFont(None, max(14, int(font_size * 0.8)))
        btn_font = pygame.font.SysFont(None, max(14, int(font_size * 0.9)))
        
        if is_vertical:
            title_rect = self._get_grid_rect(panel_rect, (0, 1, 4, 2), grid_dims)
            price_rect = self._get_grid_rect(panel_rect, (0, 3, 4, 1), grid_dims)
        else:
            y_pos = 0.5 if angle == 0 else 1.5
            title_rect = self._get_grid_rect(panel_rect, (1, y_pos, 10, 1), grid_dims)
            price_rect = self._get_grid_rect(panel_rect, (1, y_pos + 1, 10, 1), grid_dims)

        self._draw_rotated_text(f"Buy {prop['name']}?", title_font, (255, 255, 255), title_rect.center, angle, title_rect.width * 0.95)
        self._draw_rotated_text(f"Price: ${prop['price']}", price_font, (200, 200, 200), price_rect.center, angle)

        can_afford = self.buy_prompt["can_afford"]
        for name, rect in self.buy_prompt["buttons"].items():
            is_yes = name == "yes"
            enabled = can_afford if is_yes else True
            color = (100,180,250) if enabled else (80,80,80)
            txt_color = (255,255,255) if enabled else (160,160,160)
            
            pygame.draw.rect(self.screen, (10,10,10), rect.move(4,6), border_radius=12)
            pygame.draw.rect(self.screen, color, rect, border_radius=12)
            self._draw_rotated_text(name.capitalize(), btn_font, txt_color, rect.center, angle)

        now = time.time()
        for key, start_time in list(self.buy_prompt_hover.items()):
            pos = self.buy_prompt_hover_pos.get(key)
            if not pos: continue
            progress = min(1.0, max(0.0, (now - start_time) / HOVER_TIME_THRESHOLD))
            draw_circular_progress(self.screen, (pos[0] + 28, pos[1] - 28), 20, progress)

    def _draw_text_in_space(self, text: str, rect: pygame.Rect, angle: int):
        font_name = pygame.font.get_default_font()
        padding = 5
        is_vertical = angle in [90, 270]
        max_w = rect.height - 2 * padding if is_vertical else rect.width - 2 * padding
        max_h = rect.width - 2 * padding if is_vertical else rect.height - 2 * padding
        words = text.split(' ')
        longest_word_len = max(len(word) for word in words) if words else 0
        font_size = 19
        if longest_word_len >= 11: font_size = 11
        elif longest_word_len >= 9: font_size = 13
        elif longest_word_len >= 7: font_size = 15
        elif longest_word_len >= 5: font_size = 17
        font = pygame.font.Font(font_name, font_size)
        lines, current_line = [], ''
        for word in words:
            test_line = f"{current_line} {word}" if current_line else word
            if font.size(test_line)[0] <= max_w: current_line = test_line
            else:
                if current_line: lines.append(current_line)
                current_line = word
        if current_line: lines.append(current_line)
        while len(lines) * font.get_linesize() > max_h and font_size > 8:
            font_size -= 1
            font = pygame.font.Font(font_name, font_size)
            lines, current_line = [], ''
            for word in words:
                test_line = f"{current_line} {word}" if current_line else word
                if font.size(test_line)[0] <= max_w: current_line = test_line
                else:
                    if current_line: lines.append(current_line)
                    current_line = word
            if current_line: lines.append(current_line)
        line_height = font.get_linesize()
        text_block_h = len(lines) * line_height
        text_block_w = max(font.size(line)[0] for line in lines) if lines else 0
        text_surface = pygame.Surface((text_block_w, text_block_h), pygame.SRCALPHA)
        for i, line in enumerate(lines):
            line_surf = font.render(line, True, (0,0,0))
            text_surface.blit(line_surf, ((text_block_w - line_surf.get_width()) / 2, i * line_height))
        rotated_surface = pygame.transform.rotate(text_surface, angle)
        self.screen.blit(rotated_surface, rotated_surface.get_rect(center=rect.center))

    def draw_board(self):
        sw, sh = self.screen.get_size()
        pygame.draw.rect(self.screen, (20, 80, 30), pygame.Rect(0, 0, sw, sh))
        board_rect = self._board_geom["board_rect"]
        inner_rect = board_rect.inflate(-self._board_geom["long"], -self._board_geom["long"])
        pygame.draw.rect(self.screen, (200, 225, 210), board_rect)
        pygame.draw.rect(self.screen, (24, 24, 24), inner_rect, border_radius=8)
        for idx, spec in enumerate(self.properties):
            r = self._space_rect_for(idx)
            pygame.draw.rect(self.screen, (200, 225, 210), r)
            pygame.draw.rect(self.screen, (0,0,0), r, width=1)
            gcolor = spec.get("color")
            gx, gy = self._index_to_grid(idx)
            is_corner = (gx in (0, 10) and gy in (0, 10))
            if gcolor and not is_corner:
                thickness = max(3, int(self._board_geom["short"] * 0.25))
                if gy == 10: bar = pygame.Rect(r.left, r.top, r.width, thickness)
                elif gx == 0: bar = pygame.Rect(r.right - thickness, r.top, thickness, r.height)
                elif gy == 0: bar = pygame.Rect(r.left, r.bottom - thickness, r.width, thickness)
                else: bar = pygame.Rect(r.left, r.top, thickness, r.height)
                pygame.draw.rect(self.screen, gcolor, bar)
            name = spec.get("name", "")
            angle = 45 if idx in (10, 30) else (-45 if is_corner else (180 if gy == 0 else (0 if gy == 10 else (270 if gx == 0 else 90))))
            self._draw_text_in_space(name, r, angle)

    def draw_tokens(self):
        static_by_space: Dict[int, List[Player]] = {}
        moving_players: List[Player] = []
        for p in self.players:
            if self.players_selected and p.idx not in self.players_selected: continue
            if p.move_path: moving_players.append(p)
            else: static_by_space.setdefault(p.pos, []).append(p)
        for space, plist in static_by_space.items():
            cx, cy = self._space_coords_for(space)
            n = len(plist)
            token_radius = self._board_geom["short"] * 0.1
            if n == 1:
                p = plist[0]
                pygame.draw.circle(self.screen, (0, 0, 0), (cx + 2, cy + 3), token_radius * 1.2)
                pygame.draw.circle(self.screen, p.color, (cx, cy), token_radius)
            else:
                placement_radius = self._board_geom["short"] * 0.25
                for k, p in enumerate(plist):
                    ang = 2 * math.pi * k / n
                    px, py = int(cx + math.cos(ang) * placement_radius), int(cy + math.sin(ang) * placement_radius)
                    pygame.draw.circle(self.screen, (0, 0, 0), (px + 2, py + 3), token_radius * 1.1)
                    pygame.draw.circle(self.screen, p.color, (px, py), token_radius * 0.9)
        for p in moving_players:
            elapsed = time.time() - p.move_start
            per = p.move_per_space
            step = int(elapsed // per)
            frac = (elapsed % per) / per if per > 0 else 1.0
            if step >= len(p.move_path):
                sx, sy = self._space_coords_for(p.move_path[-1])
            else:
                prev_space = p.move_from if step == 0 else p.move_path[step - 1]
                sx, sy = self._space_coords_for(prev_space)
                ex, ey = self._space_coords_for(p.move_path[step])
                sx, sy = int(sx * (1 - frac) + ex * frac), int(sy * (1 - frac) + ey * frac)
            jump = math.sin(frac * math.pi) * self._board_geom["short"] * 0.2
            px, py = sx, int(sy - jump)
            token_radius = self._board_geom["short"] * 0.12
            pygame.draw.circle(self.screen, (0, 0, 0), (px + 2, py + 3), token_radius * 1.2)
            pygame.draw.circle(self.screen, p.color, (px, py), token_radius)

    def draw_player_boards_and_buttons(self):
        sw, sh = self.screen.get_size()
        font = pygame.font.SysFont(None, max(12, int(sh * 0.025)))
        for pid in list(self.players_selected):
            rect = self.selection_ui.slot_rect(pid)
            base_col = self.players[pid].color
            washed = tuple(min(255, int(c * 0.75 + 180 * 0.25)) for c in base_col)
            pygame.draw.rect(self.screen, washed, rect.inflate(8, 8), border_radius=8)
            
            angle = self._get_panel_orientation(pid)
            is_vertical = angle in (90, 270)
            
            if pid == self.current:
                pygame.draw.rect(self.screen, (255, 215, 0), rect.inflate(6, 6), width=max(2, int(sw * 0.0025)), border_radius=8)
                y_off = rect.height / 2 - font.get_height() / 2 if is_vertical else 12
                x_off = rect.width / 2 - font.get_height() / 2 if not is_vertical else 12
                
                center_pos = (rect.centerx, rect.top + y_off) if angle == 180 else \
                             (rect.right - x_off, rect.centery) if angle == 270 else \
                             (rect.left + x_off, rect.centery) if angle == 90 else \
                             (rect.centerx, rect.top + y_off)
                self._draw_rotated_text("CURRENT", font, (0,0,0), center_pos, angle)

            if self.properties_open.get(pid):
                self._draw_properties_popup_in_panel(pid, rect)
                continue
            if self.buy_prompt.get("pid") == pid:
                continue
                
            rects = self._player_button_rects(pid)
            for key_name, brect in rects.items():
                is_roll = key_name == "roll"
                is_end_turn = key_name == "end_turn"
                
                enabled = True
                if is_roll: enabled = pid == self.current and not self.player_has_rolled and not self.dice_state["rolling"]
                elif is_end_turn: enabled = pid == self.current and self.player_has_rolled and not self.buy_prompt
                
                color = tuple(min(255, int(c * 0.7 + 220 * 0.3)) for c in base_col) if enabled else (80,80,80)
                pygame.draw.rect(self.screen, color, brect, border_radius=8)
                pygame.draw.rect(self.screen, (60, 60, 60), brect, width=1, border_radius=8)
                label_text = "End Turn" if is_end_turn else key_name.capitalize()
                self._draw_rotated_text(label_text, font, (0,0,0), brect.center, angle)

        now = time.time()
        for key, start in list(self.button_hover.items()):
            pos = self.button_hover_pos.get(key)
            if not pos: continue
            progress = min(1.0, max(0.0, (now - start) / HOVER_TIME_THRESHOLD))
            draw_circular_progress(self.screen, (pos[0] + 28, pos[1] - 28), 20, progress, thickness=max(3, int(self._board_geom["short"] * 0.06)))
        
        board_rect = self._board_geom["board_rect"]
        cx, cy = board_rect.centerx, board_rect.centery
        die_size = max(28, int(self._board_geom["short"] * 0.9))
        font_small = pygame.font.SysFont(None, max(10, int(die_size * 0.45)))
        if self.dice_state.get("rolling"):
            for i in range(2):
                face = random.randint(1, 6)
                dr = pygame.Rect(cx + (i * (die_size + 8)) - (die_size // 2 + 4) - die_size // 2, cy - die_size // 2, die_size, die_size)
                pygame.draw.rect(self.screen, (255, 255, 255), dr, border_radius=max(6, die_size // 6))
                ftxt = font_small.render(str(face), True, (0, 0, 0))
                self.screen.blit(ftxt, ftxt.get_rect(center=dr.center))
        elif self.dice_state.get("d1", 0):
            for i, val in enumerate([self.dice_state["d1"], self.dice_state["d2"]]):
                dr = pygame.Rect(cx + (i * (die_size + 8)) - (die_size // 2 + 4) - die_size // 2, cy - die_size // 2, die_size, die_size)
                pygame.draw.rect(self.screen, (255, 255, 255), dr, border_radius=max(6, die_size // 6))
                ftxt = font_small.render(str(val), True, (0, 0, 0))
                self.screen.blit(ftxt, ftxt.get_rect(center=dr.center))

    def draw(self):
        self.draw_board()
        self.draw_tokens()
        self.draw_player_boards_and_buttons()
        if self.buy_prompt:
            self._draw_buy_prompt()
        try:
            pts = set()
            for v in getattr(self.selection_ui, "hover_pos", {}).values():
                if v: pts.add((int(v[0]), int(v[1])))
            for v in self.button_hover_pos.values():
                if v: pts.add((int(v[0]), int(v[1])))
            for v in self.buy_prompt_hover_pos.values():
                if v: pts.add((int(v[0]), int(v[1])))
            for (px, py) in pts:
                pygame.draw.circle(self.screen, (255, 255, 255), (px, py), 20)
                col = self.selection_ui.closest_player_color((px, py))
                pygame.draw.circle(self.screen, col, (px, py), 14)
                pygame.draw.circle(self.screen, (0, 0, 0), (px, py), 4)
        except Exception: pass