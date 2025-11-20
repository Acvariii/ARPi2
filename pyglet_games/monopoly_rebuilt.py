"""
Complete Monopoly Game - Pyglet Implementation
Carbon copy of Pygame version with full UI and game logic
"""

import time
import random
from typing import List, Dict, Tuple, Optional
from pyglet_games.renderer import PygletRenderer
from config import PLAYER_COLORS, Colors, HOVER_TIME_THRESHOLD
from monopoly_data import (
    BOARD_SPACES, STARTING_MONEY, PASSING_GO_MONEY,
    LUXURY_TAX, INCOME_TAX, JAIL_POSITION, GO_TO_JAIL_POSITION
)
from constants import COMMUNITY_CHEST_CARDS, CHANCE_CARDS
from monopoly.property import Property
from monopoly.player import Player
from monopoly.game_logic import GameLogic
from pyglet_games.player_selection import PlayerSelectionUI
from pyglet_games.player_panels import calculate_all_panels

HOVER_TIME = 1.5


class PygletButton:
    """Button with hover progress tracking"""
    def __init__(self, rect: Tuple[int, int, int, int], text: str, orientation: int = 0):
        self.x, self.y, self.width, self.height = rect
        self.text = text
        self.orientation = orientation
        self.enabled = True
        self.hover_start = 0.0
        self.hovering = False
    
    def update(self, fingertips: List[Dict], current_time: float) -> Tuple[bool, float]:
        """Returns (clicked, hover_progress)"""
        if not self.enabled:
            self.hovering = False
            return False, 0.0
        
        for meta in fingertips:
            x, y = meta["pos"]
            if (self.x <= x <= self.x + self.width and 
                self.y <= y <= self.y + self.height):
                if not self.hovering:
                    self.hover_start = current_time
                    self.hovering = True
                
                progress = (current_time - self.hover_start) / HOVER_TIME
                if progress >= 1.0:
                    self.hovering = False
                    return True, 1.0
                return False, progress
        
        self.hovering = False
        return False, 0.0
    
    def draw(self, renderer: PygletRenderer, hover_progress: float = 0.0):
        """Draw button"""
        if not self.enabled:
            bg = (100, 100, 100)
            text_color = (160, 160, 160)
        else:
            base = (70, 130, 180)
            hover = (100, 180, 220)
            bg = tuple(int(base[i] + (hover[i] - base[i]) * hover_progress) for i in range(3))
            text_color = (255, 255, 255)
        
        renderer.draw_rect(bg, (self.x, self.y, self.width, self.height))
        renderer.draw_rect((200, 200, 200), (self.x, self.y, self.width, self.height), width=2)
        
        if hover_progress > 0:
            bar_w = int(self.width * hover_progress)
            renderer.draw_rect((255, 215, 0), (self.x, self.y + self.height - 4, bar_w, 4))
        
        renderer.draw_text(
            self.text, self.x + self.width // 2, self.y + self.height // 2,
            'Arial', 18, text_color, anchor_x='center', anchor_y='center'
        )


class MonopolyGame:
    """Complete Monopoly game matching Pygame version"""
    
    def __init__(self, width: int, height: int, renderer: PygletRenderer):
        self.width = width
        self.height = height
        self.renderer = renderer
        
        self.state = "player_select"
        self.selection_ui = PlayerSelectionUI(width, height)
        
        self.players: List[Player] = []
        self.active_players: List[int] = []
        self.current_player_idx = 0
        
        self.properties = [Property(data) if data else Property({"name": "", "type": "none"}) 
                          for data in BOARD_SPACES]
        
        self.community_chest_deck = list(COMMUNITY_CHEST_CARDS)
        self.chance_deck = list(CHANCE_CARDS)
        random.shuffle(self.community_chest_deck)
        random.shuffle(self.chance_deck)
        
        self.phase = "roll"
        self.can_roll = True
        self.dice_values = (0, 0)
        self.dice_rolling = False
        self.dice_roll_start = 0.0
        
        self.panels = {}
        self.buttons: Dict[int, Dict[str, PygletButton]] = {}
        
        self._calculate_board_geometry()
    
    def _create_panels(self) -> List[Dict]:
        """Create panel dictionaries matching player_panel.py POSITIONS"""
        panels = []
        w, h = self.width, self.height
        panel_h = int(h * 0.10)
        panel_w_side = int(w * 0.12)
        
        # Match player_panel.py POSITIONS exactly
        # sides and orientations per POSITIONS dict
        positions = [
            # (x, y, w, h, orientation, side)
            (0, h - panel_h, w // 3, panel_h, 0, "bottom"),               # 0: bottom left
            (w // 3, h - panel_h, w // 3, panel_h, 0, "bottom"),          # 1: bottom center
            (2 * w // 3, h - panel_h, w // 3, panel_h, 0, "bottom"),      # 2: bottom right
            (0, 0, w // 3, panel_h, 180, "top"),                          # 3: top left
            (w // 3, 0, w // 3, panel_h, 180, "top"),                     # 4: top center
            (2 * w // 3, 0, w // 3, panel_h, 180, "top"),                 # 5: top right
            (0, panel_h, panel_w_side, h - 2 * panel_h, 270, "left"),     # 6: left
            (w - panel_w_side, panel_h, panel_w_side, h - 2 * panel_h, 90, "right"), # 7: right
        ]
        
        for x, y, pw, ph, orient, side in positions:
            panels.append({'rect': (x, y, pw, ph), 'orientation': orient, 'side': side})
        
        return panels
    
    def _calculate_board_geometry(self):
        """Calculate board position"""
        h_panel = int(self.height * 0.10)
        v_panel = int(self.width * 0.12)
        margin = 20
        
        avail_w = self.width - (2 * v_panel) - (2 * margin)
        avail_h = self.height - (2 * h_panel) - (2 * margin)
        
        size = min(avail_w, avail_h)
        x = v_panel + margin + (avail_w - size) // 2
        y = h_panel + margin + (avail_h - size) // 2
        
        self.board_rect = (x, y, size, size)
        self._calculate_spaces()
    
    def _calculate_spaces(self):
        """Calculate all 40 space positions"""
        bx, by, size, _ = self.board_rect
        corner = size // 11
        edge = size // 11
        
        self.spaces = []
        
        # Bottom (0-10)
        for i in range(11):
            w = corner if i in [0, 10] else edge
            x = bx + size - sum([corner if j in [0, 10] else edge for j in range(i+1)])
            self.spaces.append((x, by + size - corner, w, corner))
        
        # Left (11-19)
        for i in range(1, 10):
            y = by + size - sum([corner if j in [0, 10] else edge for j in range(i+1)])
            self.spaces.append((bx, y, corner, edge))
        
        # Top (20-30)
        for i in range(11):
            w = corner if i in [0, 10] else edge
            x = bx + sum([corner if j in [0, 10] else edge for j in range(i)])
            self.spaces.append((x, by, w, corner))
        
        # Right (31-39)
        for i in range(1, 10):
            y = by + sum([corner if j in [0, 10] else edge for j in range(i)])
            self.spaces.append((bx + size - corner, y, corner, edge))
    
    def _init_buttons(self):
        """Initialize buttons for all players"""
        self.buttons = {}
        for idx in self.active_players:
            panel = self.panels[idx]
            self.buttons[idx] = self._create_buttons(panel, idx)
    
    def _create_buttons(self, panel: Dict, idx: int) -> Dict[str, PygletButton]:
        """Create 3 buttons per panel"""
        x, y, w, h = panel['rect']
        orient = panel['orientation']
        margin = 10
        gap = 8
        
        if orient == 0:  # Bottom
            info_h = int(h * 0.45)
            btn_h = h - info_h - 2 * margin
            btn_w = (w - 2 * margin - 2 * gap) // 3
            btn_y = y + info_h + margin
            
            return {
                "action": PygletButton((x + margin, btn_y, btn_w, btn_h), "Roll", orient),
                "props": PygletButton((x + margin + btn_w + gap, btn_y, btn_w, btn_h), "Props", orient),
                "build": PygletButton((x + margin + 2*(btn_w+gap), btn_y, btn_w, btn_h), "Build", orient)
            }
        
        elif orient == 180:  # Top
            info_h = int(h * 0.45)
            btn_h = h - info_h - 2 * margin
            btn_w = (w - 2 * margin - 2 * gap) // 3
            btn_y = y + margin
            
            return {
                "action": PygletButton((x + margin, btn_y, btn_w, btn_h), "Roll", orient),
                "props": PygletButton((x + margin + btn_w + gap, btn_y, btn_w, btn_h), "Props", orient),
                "build": PygletButton((x + margin + 2*(btn_w+gap), btn_y, btn_w, btn_h), "Build", orient)
            }
        
        elif orient == 90:  # Left
            info_w = int(w * 0.35)
            btn_w = w - info_w - 2 * margin
            btn_h = (h - 2 * margin - 2 * gap) // 3
            btn_x = x + margin
            
            return {
                "action": PygletButton((btn_x, y + margin, btn_w, btn_h), "Roll", orient),
                "props": PygletButton((btn_x, y + margin + btn_h + gap, btn_w, btn_h), "Props", orient),
                "build": PygletButton((btn_x, y + margin + 2*(btn_h+gap), btn_w, btn_h), "Build", orient)
            }
        
        else:  # 270 - Right
            info_w = int(w * 0.35)
            btn_w = w - info_w - 2 * margin
            btn_h = (h - 2 * margin - 2 * gap) // 3
            btn_x = x + info_w + margin
            
            return {
                "action": PygletButton((btn_x, y + margin, btn_w, btn_h), "Roll", orient),
                "props": PygletButton((btn_x, y + margin + btn_h + gap, btn_w, btn_h), "Props", orient),
                "build": PygletButton((btn_x, y + margin + 2*(btn_h+gap), btn_w, btn_h), "Build", orient)
            }
    
    def start_game(self, player_indices: List[int]):
        """Start game with selected players"""
        self.active_players = sorted(player_indices)
        self.players = [Player(i, PLAYER_COLORS[i]) for i in range(8)]
        
        all_panels = self._create_panels()
        for idx in self.active_players:
            self.panels[idx] = all_panels[idx]
            p = self.players[idx]
            p.money = STARTING_MONEY
            p.position = 0
            p.properties = []
            p.in_jail = False
            p.is_bankrupt = False
        
        self._init_buttons()
        self.current_player_idx = 0
        self.phase = "roll"
        self.can_roll = True
        self.state = "playing"
    
    def handle_input(self, fingertips: List[Dict]) -> bool:
        """Handle input, return True to exit"""
        # Check for ESC key
        if fingertips and isinstance(fingertips[0], str) and fingertips[0] == 'ESC':
            return True  # Return to menu
        
        if self.state == "player_select":
            self.selection_ui.update_with_fingertips(fingertips, min_players=2)
            if self.selection_ui.start_ready:
                selected_indices = self.selection_ui.get_selected_indices()
                if selected_indices:
                    self.start_game(selected_indices)
            return False
        
        current_time = time.time()
        current_player = self.players[self.active_players[self.current_player_idx]]
        
        for idx in self.active_players:
            if idx not in self.buttons:
                continue
            
            player = self.players[idx]
            is_current = (idx == self.active_players[self.current_player_idx])
            
            # Update button states
            btns = self.buttons[idx]
            btns["action"].enabled = is_current and not self.dice_rolling
            btns["action"].text = "Roll" if self.can_roll else "End"
            btns["props"].enabled = len(player.properties) > 0
            btns["build"].enabled = is_current and len(player.properties) > 0
            
            # Check clicks
            for name, btn in btns.items():
                clicked, _ = btn.update(fingertips, current_time)
                if clicked:
                    self._handle_click(idx, name)
        
        return False
    
    def _handle_click(self, player_idx: int, button: str):
        """Handle button click"""
        if button == "action":
            if self.can_roll:
                self.roll_dice()
            else:
                self.advance_turn()
        elif button == "props":
            pass  # TODO: Show properties
        elif button == "build":
            pass  # TODO: Show build menu
    
    def roll_dice(self):
        """Roll dice"""
        if not self.can_roll or self.dice_rolling:
            return
        self.dice_rolling = True
        self.dice_roll_start = time.time()
        self.can_roll = False
    
    def advance_turn(self):
        """Next player"""
        self.current_player_idx = (self.current_player_idx + 1) % len(self.active_players)
        self.phase = "roll"
        self.can_roll = True
        self.dice_values = (0, 0)
    
    def update(self, dt: float):
        """Update game state"""
        if self.dice_rolling:
            elapsed = time.time() - self.dice_roll_start
            if elapsed >= 1.2:
                self.dice_rolling = False
                self.dice_values = (random.randint(1, 6), random.randint(1, 6))
                
                current = self.players[self.active_players[self.current_player_idx]]
                is_doubles = self.dice_values[0] == self.dice_values[1]
                
                if is_doubles:
                    current.consecutive_doubles += 1
                    if current.consecutive_doubles >= 3:
                        current.position = JAIL_POSITION
                        current.in_jail = True
                        self.can_roll = False
                        return
                else:
                    current.consecutive_doubles = 0
                
                # Move player
                spaces = sum(self.dice_values)
                old_pos = current.position
                current.position = (current.position + spaces) % 40
                
                if current.position < old_pos:
                    current.add_money(PASSING_GO_MONEY)
                
                self._land_on_space(current)
    
    def _land_on_space(self, player: Player):
        """Handle landing on space"""
        pos = player.position
        space = self.properties[pos]
        space_type = space.data.get("type")
        
        if space_type in ("property", "railroad", "utility"):
            if space.owner is None:
                # TODO: Show buy prompt
                pass
            elif space.owner != player.idx:
                # Pay rent
                owner = self.players[space.owner]
                rent = GameLogic.calculate_rent(space, sum(self.dice_values), owner, self.properties)
                if player.remove_money(rent):
                    owner.add_money(rent)
        
        elif space_type == "go_to_jail":
            player.position = JAIL_POSITION
            player.in_jail = True
        
        elif space_type == "income_tax":
            player.remove_money(INCOME_TAX)
        
        elif space_type == "luxury_tax":
            player.remove_money(LUXURY_TAX)
        
        # Check for doubles
        if player.consecutive_doubles > 0:
            self.can_roll = True
        else:
            self.can_roll = False
    
    def draw(self):
        """Draw game"""
        if self.state == "player_select":
            self._draw_player_select()
            return
        
        # Background
        self.renderer.draw_rect((32, 96, 36), (0, 0, self.width, self.height))
        
        # Panels
        self._draw_panels()
        
        # Board
        self._draw_board()
        
        # Tokens
        self._draw_tokens()
        
        # Dice
        if self.dice_values != (0, 0):
            self._draw_dice()
        
        # Hover indicators on top
        self._draw_hover_indicators()
    
    def _draw_panels(self):
        """Draw all player panels"""
        curr_idx = self.active_players[self.current_player_idx] if self.active_players else -1
        current_time = time.time()
        
        for idx in self.active_players:
            player = self.players[idx]
            panel = self.panels[idx]
            is_current = (idx == curr_idx)
            
            # Background
            color = PLAYER_COLORS[idx]
            washed = tuple(min(255, int(c * 0.75 + 180 * 0.25)) for c in color)
            self.renderer.draw_rect(washed, panel['rect'])
            
            # Border
            border_color = (255, 215, 0) if is_current else (150, 150, 150)
            border_w = 4 if is_current else 2
            self.renderer.draw_rect(border_color, panel['rect'], width=border_w)
            
            # Info
            self._draw_panel_info(player, panel)
            
            # Buttons
            if idx in self.buttons:
                for btn in self.buttons[idx].values():
                    _, progress = btn.update([], current_time)
                    btn.draw(self.renderer, progress)
    
    def _draw_panel_info(self, player: Player, panel: Dict):
        """Draw player info"""
        x, y, w, h = panel['rect']
        orient = panel['orientation']
        cx = x + w // 2
        
        if orient == 0:
            info_y = y + 25
        elif orient == 180:
            info_y = y + h - 25
        else:
            info_y = y + h // 2
        
        self.renderer.draw_text(
            f"${player.money}", cx, info_y,
            'Arial', 20, (255, 255, 100),
            anchor_x='center', anchor_y='center'
        )
        
        if player.properties:
            prop_y = info_y - 22 if orient == 0 else info_y + 22
            self.renderer.draw_text(
                f"{len(player.properties)}p", cx, prop_y,
                'Arial', 14, (200, 200, 200),
                anchor_x='center', anchor_y='center'
            )
    
    def _draw_board(self):
        """Draw monopoly board with property colors and names"""
        bx, by, bw, bh = self.board_rect
        
        # Board background
        self.renderer.draw_rect((220, 240, 220), (bx, by, bw, bh))
        self.renderer.draw_rect((100, 100, 100), (bx, by, bw, bh), width=3)
        
        # Draw spaces with colors and names
        for i, (sx, sy, sw, sh) in enumerate(self.spaces):
            space = self.properties[i]
            space_data = space.data
            
            # Background
            self.renderer.draw_rect((255, 255, 255), (sx, sy, sw, sh))
            
            # Color bar and name for properties
            if "color" in space_data and isinstance(space_data["color"], tuple):
                prop_color = space_data["color"]
                bar_h = max(8, sh // 5)
                self.renderer.draw_rect(prop_color, (sx, sy, sw, bar_h))
                
                # Draw property name (rotated based on position)
                name = space_data.get("name", "")
                if name:
                    cx, cy = sx + sw // 2, sy + sh // 2
                    # Shorten name if too long
                    if len(name) > 15:
                        name = name[:12] + "..."
                    self.renderer.draw_text(
                        name, cx, cy,
                        'Arial', 8, (0, 0, 0),
                        anchor_x='center', anchor_y='center'
                    )
            
            # Border
            self.renderer.draw_rect((80, 80, 80), (sx, sy, sw, sh), width=1)
    
    def _draw_tokens(self):
        """Draw player tokens"""
        for idx in self.active_players:
            player = self.players[idx]
            if player.is_bankrupt:
                continue
            
            sx, sy, sw, sh = self.spaces[player.position]
            cx, cy = sx + sw // 2, sy + sh // 2
            
            # Offset for multiple players
            offset_idx = self.active_players.index(idx)
            num_players = len(self.active_players)
            if num_players > 1:
                angle = (offset_idx / num_players) * 6.28
                offset = 15
                cx += int(offset * (0.5 - abs(0.5 - offset_idx / num_players)))
            
            # Draw token
            color = PLAYER_COLORS[idx]
            self.renderer.draw_circle(color, (cx, cy), 12)
            self.renderer.draw_circle((0, 0, 0), (cx, cy), 12, width=2)
    
    def _draw_dice(self):
        """Draw dice"""
        bx, by, bw, bh = self.board_rect
        cx, cy = bx + bw // 2, by + bh // 2
        
        dice_size = 50
        gap = 10
        
        for i, value in enumerate(self.dice_values):
            dx = cx + (i - 0.5) * (dice_size + gap)
            dy = cy
            
            # Die
            self.renderer.draw_rect((255, 255, 255), 
                (int(dx - dice_size/2), int(dy - dice_size/2), dice_size, dice_size))
            self.renderer.draw_rect((0, 0, 0), 
                (int(dx - dice_size/2), int(dy - dice_size/2), dice_size, dice_size), width=2)
            
            # Pips
            self._draw_pips(int(dx), int(dy), dice_size, value)
    
    def _draw_hover_indicators(self):
        """Draw circular progress indicators for button hovers"""
        current_time = time.time()
        
        for idx in self.active_players:
            if idx not in self.buttons:
                continue
            for btn in self.buttons[idx].values():
                if btn.hovering and btn.hover_start:
                    progress = min(1.0, (current_time - btn.hover_start) / HOVER_TIME)
                    cx = btn.x + btn.width // 2
                    cy = btn.y + btn.height // 2
                    self.renderer.draw_circular_progress((cx, cy), 30, progress, (100, 200, 255), thickness=5)
    
    def _draw_pips(self, cx: int, cy: int, size: int, value: int):
        """Draw dice pips"""
        r = size // 10
        off = size // 4
        
        pips = {
            1: [(0, 0)],
            2: [(-off, -off), (off, off)],
            3: [(-off, -off), (0, 0), (off, off)],
            4: [(-off, -off), (off, -off), (-off, off), (off, off)],
            5: [(-off, -off), (off, -off), (0, 0), (-off, off), (off, off)],
            6: [(-off, -off), (off, -off), (-off, 0), (off, 0), (-off, off), (off, off)]
        }
        
        for dx, dy in pips.get(value, []):
            self.renderer.draw_circle((0, 0, 0), (cx + dx, cy + dy), r)
    
    def _draw_player_select(self):
        """Draw player selection screen"""
        # Background
        self.renderer.draw_rect((25, 35, 25), (0, 0, self.width, self.height))
        
        # Title at top
        self.renderer.draw_text(
            "Select Players - Monopoly",
            self.width // 2, 40,
            'Arial', 48, Colors.WHITE,
            anchor_x='center', anchor_y='center'
        )
        
        # Draw circular player slots
        for i, (sx, sy, sw, sh) in enumerate(self.selection_ui.slots):
            cx = sx + sw // 2
            cy = sy + sh // 2
            radius = sw // 2
            color = PLAYER_COLORS[i]
            
            if self.selection_ui.selected[i]:
                self.renderer.draw_circle(color, (cx, cy), radius)
                self.renderer.draw_circle((255, 255, 255), (cx, cy), radius, width=5)
            else:
                self.renderer.draw_circle((80, 80, 80), (cx, cy), radius, width=3)
            
            text_color = (255, 255, 255) if self.selection_ui.selected[i] else (150, 150, 150)
            self.renderer.draw_text(
                f"P{i+1}",
                cx, cy,
                'Arial', 36, text_color,
                anchor_x='center', anchor_y='center'
            )
        
        # Start button in center
        btn_size = 160
        cx = self.width // 2
        cy = self.height // 2
        count = self.selection_ui.selected_count()
        
        if count >= 2:
            self.renderer.draw_circle((70, 130, 180), (cx, cy), btn_size // 2)
            self.renderer.draw_circle((200, 200, 200), (cx, cy), btn_size // 2, width=3)
        else:
            self.renderer.draw_circle((100, 100, 100), (cx, cy), btn_size // 2)
            self.renderer.draw_circle((80, 80, 80), (cx, cy), btn_size // 2, width=2)
        
        self.renderer.draw_text(
            "Start",
            cx, cy - 10,
            'Arial', 36, (255, 255, 255),
            anchor_x='center', anchor_y='center'
        )
        self.renderer.draw_text(
            f"{count} players",
            cx, cy + 25,
            'Arial', 18, (200, 200, 200),
            anchor_x='center', anchor_y='center'
        )
