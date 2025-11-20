"""
Enhanced Monopoly Game - Pyglet/OpenGL Implementation
Full game logic with proper UI matching original Pygame version
"""

import time
import random
from typing import List, Dict, Tuple, Optional
from pyglet_renderer import PygletRenderer
from config import PLAYER_COLORS, Colors, HOVER_TIME_THRESHOLD
from monopoly_data import BOARD_SPACES, PROPERTY_GROUPS, STARTING_MONEY, PASSING_GO_MONEY


class MonopolyPlayer:
    def __init__(self, idx: int, color: Tuple[int, int, int]):
        self.idx = idx
        self.color = color
        self.money = STARTING_MONEY
        self.position = 0
        self.properties = []
        self.is_bankrupt = False
        self.in_jail = False
        self.jail_turns = 0


class MonopolyProperty:
    def __init__(self, data: Dict):
        self.name = data.get("name", "")
        self.type = data.get("type", "none")
        self.color = data.get("color", (200, 200, 200))
        self.price = data.get("price", 0)
        self.rent = data.get("rent", 0)
        self.owner = None
        self.houses = 0


class MonopolyPygletEnhanced:
    """Full Monopoly implementation with OpenGL rendering"""
    
    def __init__(self, width: int, height: int, renderer: PygletRenderer):
        self.width = width
        self.height = height
        self.renderer = renderer
        
        self.players = []
        self.active_players = []
        self.current_player_idx = 0
        self.properties = [MonopolyProperty(data) if data else MonopolyProperty({"name": "", "type": "none"}) 
                          for data in BOARD_SPACES]
        
        self.phase = "roll"  # roll, move, buy, end_turn
        self.dice_values = (0, 0)
        self.dice_rolling = False
        self.dice_roll_start = 0
        self.hover_states = {}
        
        # Calculate board geometry
        self._calculate_board_geometry()
        self._calculate_space_positions()
    
    def _calculate_board_geometry(self):
        """Calculate board size and position"""
        horizontal_panel_height = int(self.height * 0.10)
        vertical_panel_width = int(self.width * 0.12)
        margin = 20
        
        available_width = self.width - (2 * vertical_panel_width) - (2 * margin)
        available_height = self.height - (2 * horizontal_panel_height) - (2 * margin)
        
        board_size = min(available_width, available_height)
        board_x = vertical_panel_width + margin + (available_width - board_size) // 2
        board_y = horizontal_panel_height + margin + (available_height - board_size) // 2
        
        self.board_rect = (board_x, board_y, board_size, board_size)
        self.corner_size = board_size // 11
        self.edge_size = board_size // 11
    
    def _calculate_space_positions(self):
        """Calculate all 40 board space positions"""
        board_x, board_y, board_size, _ = self.board_rect
        positions = []
        
        # Bottom row (0-10): right to left
        for i in range(11):
            w = self.corner_size if i in [0, 10] else self.edge_size
            x = board_x + board_size - sum([self.corner_size if j in [0, 10] else self.edge_size for j in range(i+1)])
            y = board_y + board_size - self.corner_size
            positions.append((x, y, w, self.corner_size))
        
        # Left column (11-19): bottom to top
        for i in range(1, 10):
            y = board_y + board_size - sum([self.corner_size if j in [0, 10] else self.edge_size for j in range(i+1)])
            positions.append((board_x, y, self.corner_size, self.edge_size))
        
        # Top row (20-30): left to right
        for i in range(11):
            w = self.corner_size if i in [0, 10] else self.edge_size
            x = board_x + sum([self.corner_size if j in [0, 10] else self.edge_size for j in range(i)])
            positions.append((x, board_y, w, self.corner_size))
        
        # Right column (31-39): top to bottom
        for i in range(1, 10):
            y = board_y + sum([self.corner_size if j in [0, 10] else self.edge_size for j in range(i)])
            positions.append((board_x + board_size - self.corner_size, y, self.corner_size, self.edge_size))
        
        self.space_positions = positions
    
    def start_game(self, player_indices: List[int]):
        """Initialize game with selected players"""
        self.active_players = player_indices
        self.players = [MonopolyPlayer(i, PLAYER_COLORS[i]) for i in player_indices]
        self.current_player_idx = 0
        self.phase = "roll"
    
    def update(self, dt: float):
        """Update game state"""
        current_time = time.time()
        
        # Update dice rolling animation
        if self.dice_rolling:
            if current_time - self.dice_roll_start > 1.0:
                self.dice_rolling = False
                self._move_player()
    
    def _roll_dice(self):
        """Roll dice"""
        self.dice_values = (random.randint(1, 6), random.randint(1, 6))
        self.dice_rolling = True
        self.dice_roll_start = time.time()
    
    def _move_player(self):
        """Move current player"""
        player = self.players[self.current_player_idx]
        steps = sum(self.dice_values)
        
        old_position = player.position
        player.position = (player.position + steps) % 40
        
        # Check if passed GO
        if player.position < old_position:
            player.money += PASSING_GO_MONEY
        
        self.phase = "buy"
    
    def _next_player(self):
        """Move to next player"""
        self.current_player_idx = (self.current_player_idx + 1) % len(self.players)
        while self.players[self.current_player_idx].is_bankrupt:
            self.current_player_idx = (self.current_player_idx + 1) % len(self.players)
        self.phase = "roll"
    
    def handle_input(self, fingertip_meta: List[Dict]) -> bool:
        """Handle player input, returns True if exiting to menu"""
        current_time = time.time()
        active_hovers = set()
        
        # Back button
        back_rect = (self.width // 2 - 100, 50, 200, 60)
        key = "back_btn"
        
        for meta in fingertip_meta:
            pos = meta["pos"]
            
            # Check back button
            if (back_rect[0] <= pos[0] <= back_rect[0] + back_rect[2] and
                back_rect[1] <= pos[1] <= back_rect[1] + back_rect[3]):
                active_hovers.add(key)
                
                if key not in self.hover_states:
                    self.hover_states[key] = {"start_time": current_time, "pos": pos}
                
                hover_duration = current_time - self.hover_states[key]["start_time"]
                if hover_duration >= HOVER_TIME_THRESHOLD:
                    self.hover_states = {}
                    return True
            
            # Check roll button
            if self.phase == "roll" and not self.dice_rolling:
                roll_btn_rect = (self.board_rect[0] + self.board_rect[2] // 2 - 100, 
                               self.board_rect[1] + self.board_rect[3] // 2 - 40,
                               200, 80)
                if (roll_btn_rect[0] <= pos[0] <= roll_btn_rect[0] + roll_btn_rect[2] and
                    roll_btn_rect[1] <= pos[1] <= roll_btn_rect[1] + roll_btn_rect[3]):
                    roll_key = "roll_btn"
                    active_hovers.add(roll_key)
                    
                    if roll_key not in self.hover_states:
                        self.hover_states[roll_key] = {"start_time": current_time, "pos": pos}
                    
                    hover_duration = current_time - self.hover_states[roll_key]["start_time"]
                    if hover_duration >= HOVER_TIME_THRESHOLD:
                        self._roll_dice()
                        if roll_key in self.hover_states:
                            del self.hover_states[roll_key]
            
            # Check end turn button
            if self.phase == "buy":
                end_btn_rect = (self.board_rect[0] + self.board_rect[2] // 2 - 100,
                              self.board_rect[1] + self.board_rect[3] // 2 + 50,
                              200, 60)
                if (end_btn_rect[0] <= pos[0] <= end_btn_rect[0] + end_btn_rect[2] and
                    end_btn_rect[1] <= pos[1] <= end_btn_rect[1] + end_btn_rect[3]):
                    end_key = "end_btn"
                    active_hovers.add(end_key)
                    
                    if end_key not in self.hover_states:
                        self.hover_states[end_key] = {"start_time": current_time, "pos": pos}
                    
                    hover_duration = current_time - self.hover_states[end_key]["start_time"]
                    if hover_duration >= HOVER_TIME_THRESHOLD:
                        self._next_player()
                        if end_key in self.hover_states:
                            del self.hover_states[end_key]
        
        # Remove stale hover states
        for key in list(self.hover_states.keys()):
            if key not in active_hovers:
                del self.hover_states[key]
        
        return False
    
    def draw(self):
        """Draw the complete Monopoly game"""
        # Background
        self.renderer.draw_rect((25, 35, 25), (0, 0, self.width, self.height))
        
        # Draw board
        self._draw_board()
        
        # Draw properties
        self._draw_properties()
        
        # Draw players
        self._draw_players()
        
        # Draw center area with game info
        self._draw_center_info()
        
        # Draw dice
        if self.dice_values[0] > 0:
            self._draw_dice()
        
        # Draw player info panels
        self._draw_player_panels()
        
        # Back button
        self._draw_back_button()
        
        # Draw hover indicators
        self._draw_hover_indicators()
    
    def _draw_board(self):
        """Draw the monopoly board"""
        board_x, board_y, board_size, _ = self.board_rect
        
        # Board background
        self.renderer.draw_rect((220, 240, 220), self.board_rect)
        self.renderer.draw_rect(Colors.BLACK, self.board_rect, width=3)
        
        # Center area
        center_x = board_x + self.corner_size
        center_y = board_y + self.corner_size
        center_size = self.corner_size * 9
        center_rect = (center_x, center_y, center_size, center_size)
        self.renderer.draw_rect((240, 250, 240), center_rect)
        self.renderer.draw_rect(Colors.BLACK, center_rect, width=2)
        
        # Monopoly title
        self.renderer.draw_text(
            "MONOPOLY",
            board_x + board_size // 2, board_y + board_size // 2,
            font_name='Arial', font_size=int(center_size * 0.12),
            color=(180, 40, 40),
            anchor_x='center', anchor_y='center'
        )
    
    def _draw_properties(self):
        """Draw all property spaces"""
        for idx, space_data in enumerate(BOARD_SPACES):
            if not space_data or space_data.get("type") == "none":
                continue
            
            x, y, w, h = self.space_positions[idx]
            space_type = space_data.get("type")
            
            if space_type in ("property", "railroad", "utility"):
                color = space_data.get("color", (200, 200, 200))
                strip_height = h // 4
                
                # Color strip
                self.renderer.draw_rect(color, (x, y, w, strip_height))
                
                # Main area
                self.renderer.draw_rect((248, 248, 248), (x, y + strip_height, w, h - strip_height))
                
                # Border
                self.renderer.draw_rect((50, 50, 50), (x, y, w, h), width=1)
                
                # Property name
                name = space_data.get("name", "")
                if name:
                    font_size = max(8, min(11, w // 5))
                    # Split name into words for wrapping
                    words = name.split()
                    lines = []
                    for i in range(0, len(words), 2):
                        lines.append(" ".join(words[i:i+2]))
                    
                    y_offset = y + strip_height + (h - strip_height) // 2 - (len(lines) * font_size) // 2
                    for i, line in enumerate(lines[:2]):
                        self.renderer.draw_text(
                            line, x + w // 2, y_offset + i * (font_size + 2),
                            font_name='Arial', font_size=font_size,
                            color=(40, 40, 40),
                            anchor_x='center', anchor_y='top'
                        )
            else:
                # Special spaces (GO, Jail, etc.)
                self.renderer.draw_rect((245, 245, 240), (x, y, w, h))
                self.renderer.draw_rect((80, 80, 80), (x, y, w, h), width=1)
                
                # Space name
                name = space_data.get("name", "")
                if name:
                    font_size = max(10, min(14, w // 4))
                    self.renderer.draw_text(
                        name, x + w // 2, y + h // 2,
                        font_name='Arial', font_size=font_size,
                        color=(40, 40, 40),
                        anchor_x='center', anchor_y='center'
                    )
    
    def _draw_players(self):
        """Draw player tokens on board"""
        for player in self.players:
            if player.is_bankrupt:
                continue
            
            x, y, w, h = self.space_positions[player.position]
            center_x = x + w // 2
            center_y = y + h // 2
            
            # Draw token (circle)
            token_radius = 12
            self.renderer.draw_circle(Colors.BLACK, (center_x + 1, center_y + 2), token_radius + 1)
            self.renderer.draw_circle(player.color, (center_x, center_y), token_radius)
    
    def _draw_center_info(self):
        """Draw game info in center of board"""
        board_x, board_y, board_size, _ = self.board_rect
        
        if self.players:
            current_player = self.players[self.current_player_idx]
            
            # Current player indicator
            info_y = board_y + board_size // 2 - 80
            self.renderer.draw_text(
                f"Player {current_player.idx + 1}'s Turn",
                board_x + board_size // 2, info_y,
                font_name='Arial', font_size=24,
                color=current_player.color,
                anchor_x='center', anchor_y='center'
            )
            
            # Money
            self.renderer.draw_text(
                f"${current_player.money}",
                board_x + board_size // 2, info_y + 35,
                font_name='Arial', font_size=20,
                color=(60, 120, 60),
                anchor_x='center', anchor_y='center'
            )
            
            # Roll button
            if self.phase == "roll" and not self.dice_rolling:
                roll_btn = (board_x + board_size // 2 - 100, 
                          board_y + board_size // 2 - 40,
                          200, 80)
                self.renderer.draw_rect((80, 150, 80), roll_btn)
                self.renderer.draw_rect((120, 200, 120), roll_btn, width=3)
                self.renderer.draw_text(
                    "Roll Dice",
                    board_x + board_size // 2, board_y + board_size // 2,
                    font_name='Arial', font_size=32,
                    color=(255, 255, 255),
                    anchor_x='center', anchor_y='center'
                )
            
            # End turn button
            if self.phase == "buy":
                end_btn = (board_x + board_size // 2 - 100,
                         board_y + board_size // 2 + 50,
                         200, 60)
                self.renderer.draw_rect((150, 80, 80), end_btn)
                self.renderer.draw_rect((200, 120, 120), end_btn, width=2)
                self.renderer.draw_text(
                    "End Turn",
                    board_x + board_size // 2, board_y + board_size // 2 + 80,
                    font_name='Arial', font_size=24,
                    color=(255, 255, 255),
                    anchor_x='center', anchor_y='center'
                )
    
    def _draw_dice(self):
        """Draw dice in center"""
        board_x, board_y, board_size, _ = self.board_rect
        dice_size = 50
        spacing = 20
        
        for i, value in enumerate(self.dice_values):
            dice_x = board_x + board_size // 2 - dice_size - spacing // 2 + i * (dice_size + spacing)
            dice_y = board_y + board_size // 2 - dice_size // 2 - 150
            
            # Dice background
            self.renderer.draw_rect((255, 255, 255), (dice_x, dice_y, dice_size, dice_size))
            self.renderer.draw_rect((0, 0, 0), (dice_x, dice_y, dice_size, dice_size), width=2)
            
            # Draw dots based on value
            self._draw_dice_dots(dice_x, dice_y, dice_size, value)
    
    def _draw_dice_dots(self, x: int, y: int, size: int, value: int):
        """Draw dots on a dice"""
        dot_radius = size // 10
        cx = x + size // 2
        cy = y + size // 2
        offset = size // 4
        
        dots = {
            1: [(cx, cy)],
            2: [(x + offset, y + offset), (x + size - offset, y + size - offset)],
            3: [(x + offset, y + offset), (cx, cy), (x + size - offset, y + size - offset)],
            4: [(x + offset, y + offset), (x + size - offset, y + offset),
                (x + offset, y + size - offset), (x + size - offset, y + size - offset)],
            5: [(x + offset, y + offset), (x + size - offset, y + offset),
                (cx, cy),
                (x + offset, y + size - offset), (x + size - offset, y + size - offset)],
            6: [(x + offset, y + offset), (x + size - offset, y + offset),
                (x + offset, cy), (x + size - offset, cy),
                (x + offset, y + size - offset), (x + size - offset, y + size - offset)]
        }
        
        for dot_x, dot_y in dots.get(value, []):
            self.renderer.draw_circle((0, 0, 0), (dot_x, dot_y), dot_radius)
    
    def _draw_player_panels(self):
        """Draw player info panels at screen edges"""
        # Simple info display for now
        pass
    
    def _draw_back_button(self):
        """Draw back to menu button"""
        back_rect = (self.width // 2 - 100, 50, 200, 60)
        self.renderer.draw_rect((120, 60, 60), back_rect)
        self.renderer.draw_rect((200, 100, 100), back_rect, width=2)
        self.renderer.draw_text(
            "Back to Menu",
            self.width // 2, 80,
            font_name='Arial', font_size=24,
            color=(255, 255, 255),
            anchor_x='center', anchor_y='center'
        )
    
    def _draw_hover_indicators(self):
        """Draw circular progress indicators for hover states"""
        current_time = time.time()
        
        for key, state in self.hover_states.items():
            hover_duration = current_time - state["start_time"]
            progress = min(1.0, hover_duration / HOVER_TIME_THRESHOLD)
            pos = state["pos"]
            self.renderer.draw_circular_progress(pos, 25, progress, Colors.ACCENT, thickness=6)
