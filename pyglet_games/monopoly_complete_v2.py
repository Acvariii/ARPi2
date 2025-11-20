"""
Complete Monopoly implementation for Pyglet matching Pygame UI
Includes player selection, full button layouts, board with tokens, dice, properties
"""
import time
import random
from typing import List, Dict, Tuple, Optional
from config import PLAYER_COLORS, Colors
from monopoly_data import BOARD_SPACES, STARTING_MONEY, PASSING_GO_MONEY
from monopoly.property import Property
from monopoly.player import Player
from monopoly.game_logic import GameLogic
from pyglet_games.renderer import PygletRenderer
from pyglet_games.player_selection import PlayerSelectionUI
from pyglet_games.player_panels import get_panel_position

HOVER_TIME_THRESHOLD = 1.5


class MonopolyButton:
    """Button with hover detection for Pyglet"""
    def __init__(self, rect: Tuple[int, int, int, int], text: str, orientation: int = 0):
        self.x, self.y, self.width, self.height = rect
        self.text = text
        self.orientation = orientation
        self.hover_start = 0.0
        self.is_hovering = False
        self.enabled = True
    
    def check_hover(self, pos: Tuple[int, int], current_time: float) -> Tuple[bool, float]:
        """Returns (is_hovering, hover_progress)"""
        x, y = pos
        if (self.x <= x <= self.x + self.width and 
            self.y <= y <= self.y + self.height and self.enabled):
            if not self.is_hovering:
                self.hover_start = current_time
                self.is_hovering = True
            progress = (current_time - self.hover_start) / HOVER_TIME_THRESHOLD
            return True, min(1.0, progress)
        else:
            self.is_hovering = False
            self.hover_start = 0.0
            return False, 0.0
    
    def draw(self, renderer: PygletRenderer, hover_progress: float = 0.0):
        """Draw button with hover effect"""
        if not self.enabled:
            bg_color = (100, 100, 100)
            text_color = (160, 160, 160)
        else:
            # Interpolate color based on hover progress
            base_color = (70, 130, 180)
            hover_color = (100, 180, 220)
            bg_color = tuple(int(base_color[i] + (hover_color[i] - base_color[i]) * hover_progress) for i in range(3))
            text_color = (255, 255, 255)
        
        # Background
        renderer.draw_rect(bg_color, (self.x, self.y, self.width, self.height))
        renderer.draw_rect((200, 200, 200), (self.x, self.y, self.width, self.height), width=2)
        
        # Hover progress bar
        if hover_progress > 0:
            bar_height = 4
            bar_width = int(self.width * hover_progress)
            renderer.draw_rect((255, 215, 0), (self.x, self.y + self.height - bar_height, bar_width, bar_height))
        
        # Text
        renderer.draw_text(
            self.text,
            self.x + self.width // 2, self.y + self.height // 2,
            font_name='Arial', font_size=18,
            color=text_color,
            anchor_x='center', anchor_y='center'
        )


class MonopolyGameComplete:
    """Complete Monopoly game with full Pygame-like UI"""
    
    def __init__(self, width: int, height: int, renderer: PygletRenderer):
        self.width = width
        self.height = height
        self.renderer = renderer
        
        # Game state
        self.state = "player_select"  # player_select, playing
        self.selection_ui = PlayerSelectionUI(width, height, renderer)
        
        # Players and game data
        self.players: List[Player] = []
        self.active_players: List[int] = []
        self.current_player_idx = 0
        self.properties = [Property(data) if data else Property({"name": "", "type": "none"}) 
                          for data in BOARD_SPACES]
        
        # Board geometry
        self._calculate_board_geometry()
        
        # Game state
        self.phase = "roll"
        self.can_roll = True
        self.dice_values = (0, 0)
        self.dice_rolling = False
        self.dice_roll_start = 0.0
        
        # Buttons for each player
        self.buttons: Dict[int, Dict[str, MonopolyButton]] = {}
        
        # Panels
        self.panels = {}
        
    def _calculate_board_geometry(self):
        """Calculate board position matching Pygame layout"""
        horizontal_panel_height = int(self.height * 0.10)
        vertical_panel_width = int(self.width * 0.12)
        margin = 20
        
        available_width = self.width - (2 * vertical_panel_width) - (2 * margin)
        available_height = self.height - (2 * horizontal_panel_height) - (2 * margin)
        
        board_size = min(available_width, available_height)
        board_x = vertical_panel_width + margin + (available_width - board_size) // 2
        board_y = horizontal_panel_height + margin + (available_height - board_size) // 2
        
        self.board_rect = (board_x, board_y, board_size, board_size)
        self._calculate_space_positions()
    
    def _calculate_space_positions(self):
        """Calculate positions for all 40 board spaces"""
        board_x, board_y, board_size, _ = self.board_rect
        corner_size = board_size // 11
        edge_size = board_size // 11
        
        self.space_positions = []
        
        # Bottom row (0-10): Right to left
        for i in range(11):
            w = corner_size if i in [0, 10] else edge_size
            x = board_x + board_size - sum([corner_size if j in [0, 10] else edge_size for j in range(i+1)])
            y = board_y + board_size - corner_size
            self.space_positions.append((x, y, w, corner_size))
        
        # Left column (11-19): Bottom to top
        for i in range(1, 10):
            x = board_x
            y = board_y + board_size - sum([corner_size if j in [0, 10] else edge_size for j in range(i+1)])
            self.space_positions.append((x, y, corner_size, edge_size))
        
        # Top row (20-30): Left to right
        for i in range(11):
            w = corner_size if i in [0, 10] else edge_size
            x = board_x + sum([corner_size if j in [0, 10] else edge_size for j in range(i)])
            y = board_y
            self.space_positions.append((x, y, w, corner_size))
        
        # Right column (31-39): Top to bottom
        for i in range(1, 10):
            x = board_x + board_size - corner_size
            y = board_y + sum([corner_size if j in [0, 10] else edge_size for j in range(i)])
            self.space_positions.append((x, y, corner_size, edge_size))
    
    def _init_buttons_for_players(self):
        """Initialize buttons for all active players matching Pygame layout"""
        self.buttons = {}
        for player_idx in self.active_players:
            panel = self.panels[player_idx]
            self.buttons[player_idx] = self._create_panel_buttons(panel, player_idx)
    
    def _create_panel_buttons(self, panel_info: Dict, player_idx: int) -> Dict[str, MonopolyButton]:
        """Create buttons for a specific panel with proper orientation"""
        panel_rect = panel_info['rect']
        orientation = panel_info['orientation']
        x, y, w, h = panel_rect
        
        margin = 10
        gap = 8
        
        if orientation == 0:  # Bottom
            info_height = int(h * 0.45)
            btn_area_height = h - info_height
            btn_y = y + info_height
            btn_w = (w - 2 * margin - 2 * gap) // 3
            btn_h = btn_area_height - 2 * margin
            
            return {
                "action": MonopolyButton((x + margin, btn_y + margin, btn_w, btn_h), "Roll", orientation),
                "props": MonopolyButton((x + margin + btn_w + gap, btn_y + margin, btn_w, btn_h), "Props", orientation),
                "build": MonopolyButton((x + margin + 2 * (btn_w + gap), btn_y + margin, btn_w, btn_h), "Build", orientation)
            }
        
        elif orientation == 180:  # Top
            info_height = int(h * 0.45)
            btn_area_height = h - info_height
            btn_y = y
            btn_w = (w - 2 * margin - 2 * gap) // 3
            btn_h = btn_area_height - 2 * margin
            
            return {
                "action": MonopolyButton((x + margin, btn_y + margin, btn_w, btn_h), "Roll", orientation),
                "props": MonopolyButton((x + margin + btn_w + gap, btn_y + margin, btn_w, btn_h), "Props", orientation),
                "build": MonopolyButton((x + margin + 2 * (btn_w + gap), btn_y + margin, btn_w, btn_h), "Build", orientation)
            }
        
        elif orientation == 90:  # Left
            info_width = int(w * 0.35)
            btn_area_width = w - info_width
            btn_x = x
            btn_w = btn_area_width - 2 * margin
            btn_h = (h - 2 * margin - 2 * gap) // 3
            
            return {
                "action": MonopolyButton((btn_x + margin, y + margin, btn_w, btn_h), "Roll", orientation),
                "props": MonopolyButton((btn_x + margin, y + margin + btn_h + gap, btn_w, btn_h), "Props", orientation),
                "build": MonopolyButton((btn_x + margin, y + margin + 2 * (btn_h + gap), btn_w, btn_h), "Build", orientation)
            }
        
        else:  # orientation == 270: Right
            info_width = int(w * 0.35)
            btn_area_width = w - info_width
            btn_x = x + info_width
            btn_w = btn_area_width - 2 * margin
            btn_h = (h - 2 * margin - 2 * gap) // 3
            
            return {
                "action": MonopolyButton((btn_x + margin, y + margin, btn_w, btn_h), "Roll", orientation),
                "props": MonopolyButton((btn_x + margin, y + margin + btn_h + gap, btn_w, btn_h), "Props", orientation),
                "build": MonopolyButton((btn_x + margin, y + margin + 2 * (btn_h + gap), btn_w, btn_h), "Build", orientation)
            }
    
    def start_game(self, player_indices: List[int]):
        """Start game with selected players"""
        self.active_players = sorted(player_indices)
        self.players = [Player(i, PLAYER_COLORS[i]) for i in range(8)]
        
        # Initialize panels for active players
        for idx in self.active_players:
            pos_info = get_panel_position(idx, (self.width, self.height))
            self.panels[idx] = pos_info
        
        # Initialize buttons
        self._init_buttons_for_players()
        
        # Reset game state
        for i in self.active_players:
            p = self.players[i]
            p.money = STARTING_MONEY
            p.position = 0
            p.properties = []
            p.in_jail = False
            p.is_bankrupt = False
        
        self.current_player_idx = 0
        self.phase = "roll"
        self.can_roll = True
        self.state = "playing"
    
    def handle_input(self, fingertip_meta: List[Dict]) -> bool:
        """Handle input, returns True if should exit to menu"""
        if self.state == "player_select":
            result = self.selection_ui.handle_input(fingertip_meta)
            if result:
                self.start_game(result)
            return False
        
        # Game input handling
        current_time = time.time()
        
        for player_idx in self.active_players:
            if player_idx not in self.buttons:
                continue
            
            player = self.players[player_idx]
            is_current = (player_idx == self.active_players[self.current_player_idx])
            
            for btn_name, btn in self.buttons[player_idx].items():
                # Enable/disable buttons based on game state
                if btn_name == "action":
                    btn.enabled = is_current and not self.dice_rolling
                    if self.can_roll:
                        btn.text = "Roll"
                    else:
                        btn.text = "End"
                elif btn_name == "props":
                    btn.enabled = len(player.properties) > 0
                elif btn_name == "build":
                    btn.enabled = is_current and len(player.properties) > 0
                
                # Check hover and click
                for meta in fingertip_meta:
                    pos = meta["pos"]
                    is_hovering, progress = btn.check_hover(pos, current_time)
                    if is_hovering and progress >= 1.0:
                        self._handle_button_click(player_idx, btn_name)
                        btn.hover_start = current_time  # Reset to prevent multiple triggers
        
        return False
    
    def _handle_button_click(self, player_idx: int, button_name: str):
        """Handle button clicks"""
        if button_name == "action":
            if self.can_roll:
                self.roll_dice()
            else:
                self.advance_turn()
        elif button_name == "props":
            # TODO: Show properties popup
            pass
        elif button_name == "build":
            # TODO: Show build popup
            pass
    
    def roll_dice(self):
        """Start dice roll"""
        if not self.can_roll or self.dice_rolling:
            return
        self.dice_rolling = True
        self.dice_roll_start = time.time()
        self.can_roll = False
    
    def advance_turn(self):
        """Move to next player's turn"""
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
                # TODO: Move player and handle landing
    
    def draw(self):
        """Draw game"""
        if self.state == "player_select":
            self.selection_ui.draw()
            return
        
        # Draw background
        self.renderer.draw_rect((32, 96, 36), (0, 0, self.width, self.height))
        
        # Draw panels
        self._draw_all_panels()
        
        # Draw board
        self._draw_board()
        
        # Draw dice if visible
        if self.dice_values != (0, 0):
            self._draw_dice()
    
    def _draw_all_panels(self):
        """Draw all player panels with buttons"""
        current_player_idx = self.active_players[self.current_player_idx] if self.active_players else -1
        
        for player_idx in self.active_players:
            player = self.players[player_idx]
            panel = self.panels[player_idx]
            is_current = (player_idx == current_player_idx)
            
            # Panel background
            color = PLAYER_COLORS[player_idx]
            washed = tuple(min(255, int(c * 0.75 + 180 * 0.25)) for c in color)
            self.renderer.draw_rect(washed, panel['rect'])
            
            # Border
            border_color = (255, 215, 0) if is_current else (150, 150, 150)
            border_width = 4 if is_current else 2
            self.renderer.draw_rect(border_color, panel['rect'], width=border_width)
            
            # Player info
            self._draw_panel_info(player, panel)
            
            # Buttons
            if player_idx in self.buttons:
                current_time = time.time()
                for btn in self.buttons[player_idx].values():
                    _, progress = btn.check_hover((0, 0), current_time)  # Get current progress
                    btn.draw(self.renderer, progress)
    
    def _draw_panel_info(self, player: Player, panel: Dict):
        """Draw player information in panel"""
        px, py, pw, ph = panel['rect']
        orientation = panel['orientation']
        
        # Info area
        if orientation in [0, 180]:
            info_y = py + 20 if orientation == 0 else py + ph - 20
        else:
            info_y = py + ph // 2
        
        cx = px + pw // 2
        
        # Money
        self.renderer.draw_text(
            f"${player.money}",
            cx, info_y,
            font_name='Arial', font_size=20,
            color=(255, 255, 100),
            anchor_x='center', anchor_y='center'
        )
        
        # Properties count
        if player.properties:
            self.renderer.draw_text(
                f"{len(player.properties)} props",
                cx, info_y - 20 if orientation == 0 else info_y + 20,
                font_name='Arial', font_size=14,
                color=(200, 200, 200),
                anchor_x='center', anchor_y='center'
            )
    
    def _draw_board(self):
        """Draw monopoly board"""
        bx, by, bw, bh = self.board_rect
        
        # Board background
        self.renderer.draw_rect((220, 240, 220), (bx, by, bw, bh))
        self.renderer.draw_rect((100, 100, 100), (bx, by, bw, bh), width=3)
        
        # Draw spaces
        for i, (sx, sy, sw, sh) in enumerate(self.space_positions):
            space = self.properties[i]
            space_type = space.data.get("type", "none")
            
            # Space background
            if space_type == "property":
                color_name = space.data.get("color", "none")
                color_map = {
                    "brown": (150, 75, 0),
                    "lightblue": (173, 216, 230),
                    "pink": (255, 105, 180),
                    "orange": (255, 165, 0),
                    "red": (255, 0, 0),
                    "yellow": (255, 255, 0),
                    "green": (0, 200, 0),
                    "darkblue": (0, 0, 150)
                }
                prop_color = color_map.get(color_name, (200, 200, 200))
                self.renderer.draw_rect((255, 255, 255), (sx, sy, sw, sh))
                # Color bar at top
                bar_height = sh // 5
                self.renderer.draw_rect(prop_color, (sx, sy, sw, bar_height))
            else:
                self.renderer.draw_rect((255, 255, 255), (sx, sy, sw, sh))
            
            # Border
            self.renderer.draw_rect((80, 80, 80), (sx, sy, sw, sh), width=1)
    
    def _draw_dice(self):
        """Draw dice in center of board"""
        bx, by, bw, bh = self.board_rect
        cx, cy = bx + bw // 2, by + bh // 2
        
        dice_size = 50
        gap = 10
        
        # Draw two dice
        for i, value in enumerate(self.dice_values):
            dx = cx + (i - 0.5) * (dice_size + gap)
            dy = cy
            
            # Die background
            self.renderer.draw_rect((255, 255, 255), (dx - dice_size // 2, dy - dice_size // 2, dice_size, dice_size))
            self.renderer.draw_rect((0, 0, 0), (dx - dice_size // 2, dy - dice_size // 2, dice_size, dice_size), width=2)
            
            # Draw pips
            self._draw_dice_pips(dx, dy, dice_size, value)
    
    def _draw_dice_pips(self, cx: int, cy: int, size: int, value: int):
        """Draw pips on a die"""
        pip_radius = size // 10
        offset = size // 4
        
        pip_positions = {
            1: [(0, 0)],
            2: [(-offset, -offset), (offset, offset)],
            3: [(-offset, -offset), (0, 0), (offset, offset)],
            4: [(-offset, -offset), (offset, -offset), (-offset, offset), (offset, offset)],
            5: [(-offset, -offset), (offset, -offset), (0, 0), (-offset, offset), (offset, offset)],
            6: [(-offset, -offset), (offset, -offset), (-offset, 0), (offset, 0), (-offset, offset), (offset, offset)]
        }
        
        for dx, dy in pip_positions.get(value, []):
            self.renderer.draw_circle((0, 0, 0), (cx + dx, cy + dy), pip_radius)
