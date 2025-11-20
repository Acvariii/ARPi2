"""
Monopoly Game - Pyglet/OpenGL Implementation
Optimized for 60 FPS at 1920x1080
"""

import time
import random
from typing import List, Dict, Tuple, Optional
from pyglet_renderer import PygletRenderer
from config import PLAYER_COLORS, Colors, HOVER_TIME_THRESHOLD
from monopoly_data import BOARD_SPACES


class MonopolyPyglet:
    """Simplified Monopoly game using OpenGL rendering"""
    
    def __init__(self, width: int, height: int, renderer: PygletRenderer):
        self.width = width
        self.height = height
        self.renderer = renderer
        
        self.active_players = []
        self.current_player = 0
        self.dice_values = (0, 0)
        self.phase = "roll"  # roll, move, end_turn
        self.hover_states = {}
        
        # Calculate board geometry
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
    
    def start_game(self, player_indices: List[int]):
        """Initialize game with selected players"""
        self.active_players = player_indices
        self.current_player = 0
        self.phase = "roll"
    
    def update(self, dt: float):
        """Update game state"""
        pass
    
    def handle_input(self, fingertip_meta: List[Dict]) -> bool:
        """Handle player input, returns True if exiting to menu"""
        current_time = time.time()
        
        # Back button
        back_rect = (self.width // 2 - 100, 50, 200, 60)
        key = "back_btn"
        
        active_hovers = set()
        
        for meta in fingertip_meta:
            pos = meta["pos"]
            if (back_rect[0] <= pos[0] <= back_rect[0] + back_rect[2] and
                back_rect[1] <= pos[1] <= back_rect[1] + back_rect[3]):
                active_hovers.add(key)
                
                if key not in self.hover_states:
                    self.hover_states[key] = {"start_time": current_time, "pos": pos}
                
                hover_duration = current_time - self.hover_states[key]["start_time"]
                if hover_duration >= HOVER_TIME_THRESHOLD:
                    self.hover_states = {}
                    return True  # Exit to menu
                break
        
        # Remove stale hover states
        for key in list(self.hover_states.keys()):
            if key not in active_hovers:
                del self.hover_states[key]
        
        return False
    
    def draw(self):
        """Draw the Monopoly board and game state"""
        # Background
        self.renderer.draw_rect((25, 35, 25), (0, 0, self.width, self.height))
        
        # Board background
        self.renderer.draw_rect((240, 220, 180), self.board_rect)
        self.renderer.draw_rect((100, 80, 60), self.board_rect, width=4)
        
        # Title
        self.renderer.draw_text(
            "Monopoly",
            self.width // 2, self.height - 30,
            font_name='Arial', font_size=48,
            color=(255, 255, 255),
            anchor_x='center', anchor_y='top'
        )
        
        # Draw simplified board spaces
        self._draw_board_spaces()
        
        # Game info
        info_text = f"Player {self.current_player + 1}'s Turn - Phase: {self.phase.title()}"
        self.renderer.draw_text(
            info_text,
            self.width // 2, self.board_rect[1] - 20,
            font_name='Arial', font_size=24,
            color=(255, 255, 255),
            anchor_x='center', anchor_y='bottom'
        )
        
        # Back button
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
        
        # Draw hover indicators
        self._draw_hover_indicators()
    
    def _draw_board_spaces(self):
        """Draw simplified board spaces"""
        board_x, board_y, board_size, _ = self.board_rect
        corner_size = board_size // 11
        
        # Draw 4 corners
        corners = [
            (board_x, board_y, corner_size, corner_size, "GO"),
            (board_x + board_size - corner_size, board_y, corner_size, corner_size, "Jail"),
            (board_x + board_size - corner_size, board_y + board_size - corner_size, corner_size, corner_size, "Free"),
            (board_x, board_y + board_size - corner_size, corner_size, corner_size, "Go Jail")
        ]
        
        for cx, cy, cw, ch, label in corners:
            self.renderer.draw_rect((200, 180, 140), (cx, cy, cw, ch))
            self.renderer.draw_rect((80, 60, 40), (cx, cy, cw, ch), width=2)
            self.renderer.draw_text(
                label,
                cx + cw // 2, cy + ch // 2,
                font_name='Arial', font_size=14,
                color=(50, 50, 50),
                anchor_x='center', anchor_y='center'
            )
        
        # Draw simplified edge spaces
        edge_size = corner_size
        
        # Bottom edge
        for i in range(1, 10):
            x = board_x + board_size - corner_size - i * edge_size
            y = board_y
            self.renderer.draw_rect((220, 200, 160), (x, y, edge_size, corner_size))
            self.renderer.draw_rect((80, 60, 40), (x, y, edge_size, corner_size), width=1)
        
        # Left edge
        for i in range(1, 10):
            x = board_x
            y = board_y + i * edge_size
            self.renderer.draw_rect((220, 200, 160), (x, y, corner_size, edge_size))
            self.renderer.draw_rect((80, 60, 40), (x, y, corner_size, edge_size), width=1)
        
        # Top edge
        for i in range(1, 10):
            x = board_x + i * edge_size
            y = board_y + board_size - corner_size
            self.renderer.draw_rect((220, 200, 160), (x, y, edge_size, corner_size))
            self.renderer.draw_rect((80, 60, 40), (x, y, edge_size, corner_size), width=1)
        
        # Right edge
        for i in range(1, 10):
            x = board_x + board_size - corner_size
            y = board_y + board_size - corner_size - i * edge_size
            self.renderer.draw_rect((220, 200, 160), (x, y, corner_size, edge_size))
            self.renderer.draw_rect((80, 60, 40), (x, y, corner_size, edge_size), width=1)
    
    def _draw_hover_indicators(self):
        """Draw circular progress indicators for hover states"""
        current_time = time.time()
        
        for key, state in self.hover_states.items():
            hover_duration = current_time - state["start_time"]
            progress = min(1.0, hover_duration / HOVER_TIME_THRESHOLD)
            pos = state["pos"]
            self.renderer.draw_circular_progress(pos, 25, progress, Colors.ACCENT, thickness=6)
