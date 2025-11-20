"""
Complete Monopoly Game - Pyglet/OpenGL Implementation
Full game with player selection, player panels, and complete UI
"""

import time
import random
from typing import List, Dict, Tuple, Optional
from pyglet_games.renderer import PygletRenderer
from config import PLAYER_COLORS, Colors, HOVER_TIME_THRESHOLD
from monopoly_data import BOARD_SPACES, PROPERTY_GROUPS, STARTING_MONEY, PASSING_GO_MONEY
from pyglet_games.player_panels import calculate_all_panels, PlayerPanel
from pyglet_games.player_selection import PlayerSelectionUI


class MonopolyPlayer:
    def __init__(self, idx: int, color: Tuple[int, int, int]):
        self.idx = idx
        self.color = color
        self.money = STARTING_MONEY
        self.position = 0
        self.properties = []
        self.bankrupt = False
        self.in_jail = False
        self.jail_turns = 0


class MonopolyProperty:
    def __init__(self, space_data: Dict):
        self.name = space_data.get("name", "")
        self.type = space_data.get("type", "none")
        self.color = space_data.get("color", "")
        self.price = space_data.get("price", 0)
        self.rent = space_data.get("rent", [])
        self.owner = None
        self.houses = 0  # 0-4 houses, 5 = hotel


class MonopolyGame:
    """Complete Monopoly implementation with OpenGL rendering"""
    
    def __init__(self, width: int, height: int, renderer: PygletRenderer):
        self.width = width
        self.height = height
        self.renderer = renderer
        
        # Game state
        self.state = "player_select"  # player_select, playing
        self.selection_ui = PlayerSelectionUI(width, height)
        
        # Players and panels
        self.players = []
        self.active_players = []
        self.current_player_idx = 0
        self.panels = calculate_all_panels(width, height)
        
        # Properties
        self.properties = [MonopolyProperty(data) if data else MonopolyProperty({"name": "", "type": "none"}) 
                          for data in BOARD_SPACES]
        
        # Game mechanics
        self.phase = "roll"  # roll, move, buy, end_turn
        self.dice_values = (0, 0)
        self.dice_rolling = False
        self.dice_roll_start = 0.0
        self.dice_roll_duration = 1.0
        
        # Hover states
        self.hover_states = {}
        
        # Calculate geometry
        self._calculate_board_geometry()
    
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
        self._calculate_space_positions()
    
    def _calculate_space_positions(self):
        """Calculate positions for all 40 board spaces"""
        board_x, board_y, board_size, _ = self.board_rect
        corner_size = int(board_size / 11)
        edge_size = int(board_size / 11)
        
        self.space_positions = []
        
        # Bottom row (0-10): GO to Just Visiting
        for i in range(11):
            w = corner_size if i in [0, 10] else edge_size
            x = board_x + board_size - sum([corner_size if j in [0, 10] else edge_size for j in range(i+1)])
            y = board_y + board_size - corner_size
            self.space_positions.append((x, y, w, corner_size))
        
        # Left column (11-19)
        for i in range(1, 10):
            x = board_x
            y = board_y + board_size - corner_size - sum([edge_size for _ in range(i)])
            self.space_positions.append((x, y, corner_size, edge_size))
        
        # Top row (20-30): Free Parking to GO TO JAIL
        for i in range(11):
            w = corner_size if i in [0, 10] else edge_size
            x = board_x + sum([corner_size if j in [0, 10] else edge_size for j in range(i)])
            y = board_y
            self.space_positions.append((x, y, w, corner_size))
        
        # Right column (31-39)
        for i in range(1, 10):
            x = board_x + board_size - corner_size
            y = board_y + corner_size + sum([edge_size for _ in range(i-1)])
            self.space_positions.append((x, y, corner_size, edge_size))
    
    def start_game(self, player_indices: List[int]):
        """Initialize game with selected players"""
        self.active_players = sorted(player_indices)
        self.players = [MonopolyPlayer(i, PLAYER_COLORS[i]) for i in player_indices]
        self.current_player_idx = 0
        self.phase = "roll"
        self.state = "playing"
    
    def _roll_dice(self):
        """Roll two dice"""
        self.dice_values = (random.randint(1, 6), random.randint(1, 6))
        self.dice_rolling = True
        self.dice_roll_start = time.time()
    
    def _move_player(self, player: MonopolyPlayer, steps: int):
        """Move player by steps, handle passing GO"""
        old_pos = player.position
        player.position = (player.position + steps) % 40
        
        # Check if passed GO
        if player.position < old_pos:
            player.money += PASSING_GO_MONEY
    
    def _next_player(self):
        """Move to next player"""
        self.current_player_idx = (self.current_player_idx + 1) % len(self.players)
        self.phase = "roll"
    
    def update(self, dt: float):
        """Update game state"""
        if self.state == "playing":
            # Handle dice animation
            if self.dice_rolling:
                if time.time() - self.dice_roll_start >= self.dice_roll_duration:
                    self.dice_rolling = False
                    # Auto-move player after dice animation
                    if self.phase == "roll":
                        total = self.dice_values[0] + self.dice_values[1]
                        self._move_player(self.players[self.current_player_idx], total)
                        self.phase = "end_turn"  # Simplified: skip buy phase for now
    
    def handle_input(self, fingertip_meta: List[Dict]) -> bool:
        """Handle player input, returns True if exiting to menu"""
        if self.state == "player_select":
            return self._handle_player_select_input(fingertip_meta)
        elif self.state == "playing":
            return self._handle_playing_input(fingertip_meta)
        return False
    
    def _handle_player_select_input(self, fingertip_meta: List[Dict]) -> bool:
        """Handle player selection input"""
        current_time = time.time()
        active_hovers = set()
        
        # Update selection UI
        self.selection_ui.update_with_fingertips(fingertip_meta)
        
        # Check back button
        back_rect = (self.width // 2 - 100, 50, 200, 60)
        for meta in fingertip_meta:
            pos = meta["pos"]
            if (back_rect[0] <= pos[0] <= back_rect[0] + back_rect[2] and
                back_rect[1] <= pos[1] <= back_rect[1] + back_rect[3]):
                key = "back_btn"
                active_hovers.add(key)
                if key not in self.hover_states:
                    self.hover_states[key] = {"start_time": current_time, "pos": pos}
                if current_time - self.hover_states[key]["start_time"] >= HOVER_TIME_THRESHOLD:
                    self.hover_states = {}
                    return True
            
            # Check start button
            start_rect = (self.width // 2 - 140, self.height // 2 - 45, 280, 90)
            if (start_rect[0] <= pos[0] <= start_rect[0] + start_rect[2] and
                start_rect[1] <= pos[1] <= start_rect[1] + start_rect[3]):
                if self.selection_ui.selected_count() >= 2:
                    key = "start_btn"
                    active_hovers.add(key)
                    if key not in self.hover_states:
                        self.hover_states[key] = {"start_time": current_time, "pos": pos}
                    if current_time - self.hover_states[key]["start_time"] >= HOVER_TIME_THRESHOLD:
                        self.start_game(self.selection_ui.get_selected_indices())
                        self.hover_states = {}
        
        # Remove stale hovers
        for key in list(self.hover_states.keys()):
            if key not in active_hovers:
                del self.hover_states[key]
        
        return False
    
    def _handle_playing_input(self, fingertip_meta: List[Dict]) -> bool:
        """Handle playing state input"""
        current_time = time.time()
        active_hovers = set()
        
        # Back button
        back_rect = (self.width // 2 - 100, 50, 200, 60)
        for meta in fingertip_meta:
            pos = meta["pos"]
            
            if (back_rect[0] <= pos[0] <= back_rect[0] + back_rect[2] and
                back_rect[1] <= pos[1] <= back_rect[1] + back_rect[3]):
                key = "back_btn"
                active_hovers.add(key)
                if key not in self.hover_states:
                    self.hover_states[key] = {"start_time": current_time, "pos": pos}
                if current_time - self.hover_states[key]["start_time"] >= HOVER_TIME_THRESHOLD:
                    self.hover_states = {}
                    return True
            
            # Roll dice button
            if self.phase == "roll" and not self.dice_rolling:
                board_x, board_y, board_size, _ = self.board_rect
                roll_rect = (board_x + board_size // 2 - 80, board_y + board_size // 2 - 60, 160, 50)
                if (roll_rect[0] <= pos[0] <= roll_rect[0] + roll_rect[2] and
                    roll_rect[1] <= pos[1] <= roll_rect[1] + roll_rect[3]):
                    key = "roll_btn"
                    active_hovers.add(key)
                    if key not in self.hover_states:
                        self.hover_states[key] = {"start_time": current_time, "pos": pos}
                    if current_time - self.hover_states[key]["start_time"] >= HOVER_TIME_THRESHOLD:
                        self._roll_dice()
                        del self.hover_states[key]
            
            # End turn button
            if self.phase == "end_turn":
                board_x, board_y, board_size, _ = self.board_rect
                end_rect = (board_x + board_size // 2 - 80, board_y + board_size // 2 + 20, 160, 50)
                if (end_rect[0] <= pos[0] <= end_rect[0] + end_rect[2] and
                    end_rect[1] <= pos[1] <= end_rect[1] + end_rect[3]):
                    key = "end_btn"
                    active_hovers.add(key)
                    if key not in self.hover_states:
                        self.hover_states[key] = {"start_time": current_time, "pos": pos}
                    if current_time - self.hover_states[key]["start_time"] >= HOVER_TIME_THRESHOLD:
                        self._next_player()
                        del self.hover_states[key]
        
        # Remove stale hovers
        for key in list(self.hover_states.keys()):
            if key not in active_hovers:
                del self.hover_states[key]
        
        return False
    
    def draw(self):
        """Draw the complete Monopoly game"""
        if self.state == "player_select":
            self._draw_player_select()
        elif self.state == "playing":
            self._draw_playing()
    
    def _draw_player_select(self):
        """Draw player selection screen"""
        # Background
        self.renderer.draw_rect((25, 35, 25), (0, 0, self.width, self.height))
        
        # Panel
        panel_rect = (80, 60, self.width - 160, self.height - 120)
        self.renderer.draw_rect(Colors.PANEL, panel_rect)
        
        # Title
        self.renderer.draw_text(
            "Select Players (2-8)",
            self.width // 2, self.height - 90,
            font_name='Arial', font_size=48,
            color=Colors.WHITE,
            anchor_x='center', anchor_y='center'
        )
        
        # Draw player slots
        for i, (x, y, w, h) in enumerate(self.selection_ui.slots):
            color = PLAYER_COLORS[i]
            washed = tuple(min(255, int(c * 0.7 + 180 * 0.3)) for c in color)
            
            # Slot background
            if self.selection_ui.selected[i]:
                self.renderer.draw_rect(color, (x, y, w, h))
                self.renderer.draw_rect((255, 255, 255), (x, y, w, h), width=4)
            else:
                self.renderer.draw_rect(washed, (x, y, w, h))
                self.renderer.draw_rect((150, 150, 150), (x, y, w, h), width=2)
            
            # Player number
            self.renderer.draw_text(
                f"Player {i + 1}",
                x + w // 2, y + h // 2,
                font_name='Arial', font_size=32,
                color=(255, 255, 255),
                anchor_x='center', anchor_y='center'
            )
            
            # Status
            status = "SELECTED" if self.selection_ui.selected[i] else "Touch to Select"
            self.renderer.draw_text(
                status,
                x + w // 2, y + 30,
                font_name='Arial', font_size=18,
                color=(255, 255, 255),
                anchor_x='center', anchor_y='center'
            )
        
        # Start button
        start_rect = (self.width // 2 - 140, self.height // 2 - 45, 280, 90)
        selected_count = self.selection_ui.selected_count()
        can_start = selected_count >= 2
        btn_color = (80, 150, 80) if can_start else (100, 100, 100)
        
        self.renderer.draw_rect(btn_color, start_rect)
        self.renderer.draw_rect((200, 200, 200), start_rect, width=3)
        self.renderer.draw_text(
            "Start Game",
            self.width // 2, self.height // 2,
            font_name='Arial', font_size=36,
            color=(255, 255, 255),
            anchor_x='center', anchor_y='center'
        )
        
        # Player count
        self.renderer.draw_text(
            f"{selected_count} players selected",
            self.width // 2, self.height // 2 - 100,
            font_name='Arial', font_size=24,
            color=(255, 255, 255),
            anchor_x='center', anchor_y='center'
        )
        
        if selected_count < 2:
            self.renderer.draw_text(
                "Minimum 2 players required",
                self.width // 2, self.height // 2 - 130,
                font_name='Arial', font_size=20,
                color=(255, 200, 200),
                anchor_x='center', anchor_y='center'
            )
        
        # Back button
        self._draw_back_button()
        
        # Hover indicators
        self._draw_hover_indicators()
    
    def _draw_playing(self):
        """Draw playing screen"""
        # Background
        self.renderer.draw_rect((25, 35, 25), (0, 0, self.width, self.height))
        
        # Draw player panels
        self._draw_player_panels()
        
        # Draw board
        self._draw_board()
        
        # Draw properties
        self._draw_properties()
        
        # Draw players on board
        self._draw_players()
        
        # Draw dice
        if self.dice_values[0] > 0:
            self._draw_dice()
        
        # Draw center info
        self._draw_center_info()
        
        # Back button
        self._draw_back_button()
        
        # Hover indicators
        self._draw_hover_indicators()
    
    def _draw_player_panels(self):
        """Draw all player panels"""
        for player in self.players:
            panel = self.panels[player.idx]
            
            # Panel background
            washed = tuple(min(255, int(c * 0.75 + 180 * 0.25)) for c in player.color)
            self.renderer.draw_rect(washed, (panel.x, panel.y, panel.width, panel.height))
            
            # Current player border
            if player.idx == self.active_players[self.current_player_idx]:
                self.renderer.draw_rect(Colors.GOLD, (panel.x, panel.y, panel.width, panel.height), width=4)
            else:
                self.renderer.draw_rect((150, 150, 150), (panel.x, panel.y, panel.width, panel.height), width=2)
            
            # Player info at top of panel
            cx, cy = panel.get_center()
            info_y = panel.y + 30 if panel.side in ['bottom', 'left', 'right'] else panel.y + panel.height - 30
            
            self.renderer.draw_text(
                f"P{player.idx + 1}",
                cx, info_y,
                font_name='Arial', font_size=18,
                color=(255, 255, 255),
                anchor_x='center', anchor_y='center'
            )
            self.renderer.draw_text(
                f"${player.money}",
                cx, info_y - 25 if panel.side == 'bottom' else info_y + 25,
                font_name='Arial', font_size=20,
                color=(255, 255, 100),
                anchor_x='center', anchor_y='center'
            )
            
            # Properties count
            if player.properties:
                props_text = f"{len(player.properties)} props"
                props_y = info_y - 45 if panel.side == 'bottom' else info_y + 45
                self.renderer.draw_text(
                    props_text,
                    cx, props_y,
                    font_name='Arial', font_size=14,
                    color=(200, 200, 200),
                    anchor_x='center', anchor_y='center'
                )
    
    def _draw_board(self):
        """Draw Monopoly board"""
        board_x, board_y, board_size, _ = self.board_rect
        
        # Board background
        self.renderer.draw_rect((220, 240, 220), self.board_rect)
        self.renderer.draw_rect((100, 100, 100), self.board_rect, width=3)
        
        # Center "MONOPOLY" text
        self.renderer.draw_text(
            "MONOPOLY",
            board_x + board_size // 2, board_y + board_size // 2 + 100,
            font_name='Arial', font_size=48,
            color=(200, 50, 50),
            anchor_x='center', anchor_y='center'
        )
    
    def _draw_properties(self):
        """Draw all 40 board spaces"""
        for i, (x, y, w, h) in enumerate(self.space_positions):
            # Space background
            self.renderer.draw_rect((230, 250, 230), (x, y, w, h))
            self.renderer.draw_rect((80, 80, 80), (x, y, w, h), width=2)
            
            # Color strip for properties
            prop = self.properties[i]
            if prop.type == "property" and prop.color:
                color_map = {
                    "brown": (139, 69, 19),
                    "light_blue": (135, 206, 250),
                    "pink": (255, 192, 203),
                    "orange": (255, 140, 0),
                    "red": (220, 20, 60),
                    "yellow": (255, 215, 0),
                    "green": (34, 139, 34),
                    "dark_blue": (0, 0, 139)
                }
                strip_color = color_map.get(prop.color, (128, 128, 128))
                strip_height = 15
                self.renderer.draw_rect(strip_color, (x, y + h - strip_height, w, strip_height))
    
    def _draw_players(self):
        """Draw player tokens on board"""
        for player in self.players:
            if player.position < len(self.space_positions):
                x, y, w, h = self.space_positions[player.position]
                
                # Draw token as colored circle
                token_x = x + w // 2
                token_y = y + h // 2
                self.renderer.draw_circle(player.color, (token_x, token_y), 12)
                self.renderer.draw_circle((255, 255, 255), (token_x, token_y), 12, width=2)
    
    def _draw_dice(self):
        """Draw two dice"""
        board_x, board_y, board_size, _ = self.board_rect
        dice_x = board_x + board_size // 2 - 50
        dice_y = board_y + board_size // 2 - 120
        
        for i, value in enumerate(self.dice_values):
            dx = dice_x + i * 60
            
            # Dice background
            self.renderer.draw_rect((255, 255, 255), (dx, dice_y, 40, 40))
            self.renderer.draw_rect((100, 100, 100), (dx, dice_y, 40, 40), width=2)
            
            # Draw dots
            dot_positions = {
                1: [(20, 20)],
                2: [(10, 10), (30, 30)],
                3: [(10, 10), (20, 20), (30, 30)],
                4: [(10, 10), (30, 10), (10, 30), (30, 30)],
                5: [(10, 10), (30, 10), (20, 20), (10, 30), (30, 30)],
                6: [(10, 10), (30, 10), (10, 20), (30, 20), (10, 30), (30, 30)]
            }
            
            for dot_x, dot_y in dot_positions.get(value, []):
                self.renderer.draw_circle((0, 0, 0), (dx + dot_x, dice_y + dot_y), 3)
    
    def _draw_center_info(self):
        """Draw center game info and buttons"""
        board_x, board_y, board_size, _ = self.board_rect
        center_x = board_x + board_size // 2
        center_y = board_y + board_size // 2
        
        if self.players:
            current_player = self.players[self.current_player_idx]
            
            # Current player info
            self.renderer.draw_text(
                f"Player {current_player.idx + 1}'s Turn",
                center_x, center_y - 20,
                font_name='Arial', font_size=28,
                color=current_player.color,
                anchor_x='center', anchor_y='center'
            )
            
            # Phase-specific buttons
            if self.phase == "roll" and not self.dice_rolling:
                roll_rect = (center_x - 80, center_y - 60, 160, 50)
                self.renderer.draw_rect((80, 150, 80), roll_rect)
                self.renderer.draw_rect((200, 200, 200), roll_rect, width=2)
                self.renderer.draw_text(
                    "Roll Dice",
                    center_x, center_y - 35,
                    font_name='Arial', font_size=24,
                    color=(255, 255, 255),
                    anchor_x='center', anchor_y='center'
                )
            
            elif self.phase == "end_turn":
                end_rect = (center_x - 80, center_y + 20, 160, 50)
                self.renderer.draw_rect((150, 80, 80), end_rect)
                self.renderer.draw_rect((200, 200, 200), end_rect, width=2)
                self.renderer.draw_text(
                    "End Turn",
                    center_x, center_y + 45,
                    font_name='Arial', font_size=24,
                    color=(255, 255, 255),
                    anchor_x='center', anchor_y='center'
                )
    
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
        
        # Player selection hovers
        if self.state == "player_select":
            for hover_info in self.selection_ui.get_hover_progress():
                x, y = hover_info["pos"]
                self.renderer.draw_circular_progress((x + 28, y - 28), 20, hover_info["progress"], Colors.ACCENT, thickness=6)
