"""
Blackjack Game - Pyglet/OpenGL Implementation
Optimized for 60 FPS at 1920x1080
"""

import time
import random
from typing import List, Dict, Tuple
from pyglet_renderer import PygletRenderer
from config import PLAYER_COLORS, Colors, HOVER_TIME_THRESHOLD


class BlackjackPyglet:
    """Simplified Blackjack game using OpenGL rendering"""
    
    SUITS = ['♠', '♥', '♦', '♣']
    RANKS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
    
    def __init__(self, width: int, height: int, renderer: PygletRenderer):
        self.width = width
        self.height = height
        self.renderer = renderer
        
        self.active_players = []
        self.phase = "betting"  # betting, playing, dealing, results
        self.hover_states = {}
        
        self.dealer_hand = []
        self.player_hands = {}
        
        # Calculate table geometry
        self._calculate_table_geometry()
    
    def _calculate_table_geometry(self):
        """Calculate table size and position"""
        horizontal_panel_height = int(self.height * 0.10)
        vertical_panel_width = int(self.width * 0.12)
        margin = 20
        
        available_width = self.width - (2 * vertical_panel_width) - (2 * margin)
        available_height = self.height - (2 * horizontal_panel_height) - (2 * margin)
        
        table_size = min(available_width, available_height)
        table_x = vertical_panel_width + margin + (available_width - table_size) // 2
        table_y = horizontal_panel_height + margin + (available_height - table_size) // 2
        
        self.table_rect = (table_x, table_y, table_size, table_size)
    
    def start_game(self, player_indices: List[int]):
        """Initialize game with selected players"""
        self.active_players = player_indices
        self.phase = "betting"
        self.dealer_hand = []
        self.player_hands = {p: [] for p in player_indices}
    
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
        """Draw the Blackjack table and game state"""
        # Background
        self.renderer.draw_rect((25, 35, 25), (0, 0, self.width, self.height))
        
        # Table (green felt)
        self.renderer.draw_rect((20, 80, 40), self.table_rect)
        self.renderer.draw_rect((100, 150, 100), self.table_rect, width=4)
        
        # Title
        self.renderer.draw_text(
            "Blackjack",
            self.width // 2, self.height - 30,
            font_name='Arial', font_size=48,
            color=(255, 255, 255),
            anchor_x='center', anchor_y='top'
        )
        
        # Dealer area
        dealer_x = self.table_rect[0] + self.table_rect[2] // 2
        dealer_y = self.table_rect[1] + self.table_rect[3] // 4
        
        self.renderer.draw_text(
            "Dealer",
            dealer_x, dealer_y - 40,
            font_name='Arial', font_size=32,
            color=(255, 255, 200),
            anchor_x='center', anchor_y='center'
        )
        
        # Draw dealer cards (placeholder)
        self._draw_card(dealer_x - 35, dealer_y, "A", "♠")
        self._draw_card(dealer_x + 35, dealer_y, "K", "♥")
        
        # Game phase indicator
        phase_text = f"Phase: {self.phase.title()}"
        self.renderer.draw_text(
            phase_text,
            self.width // 2, self.table_rect[1] - 20,
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
    
    def _draw_card(self, x: int, y: int, rank: str, suit: str):
        """Draw a playing card"""
        card_width = 60
        card_height = 90
        
        # Card background
        self.renderer.draw_rect((255, 255, 255), (x - card_width // 2, y - card_height // 2, card_width, card_height))
        self.renderer.draw_rect((0, 0, 0), (x - card_width // 2, y - card_height // 2, card_width, card_height), width=2)
        
        # Rank
        rank_color = (255, 0, 0) if suit in ['♥', '♦'] else (0, 0, 0)
        self.renderer.draw_text(
            rank,
            x - card_width // 4, y - card_height // 4,
            font_name='Arial', font_size=16,
            color=rank_color,
            anchor_x='center', anchor_y='center'
        )
        
        # Suit
        self.renderer.draw_text(
            suit,
            x, y + 10,
            font_name='Arial', font_size=32,
            color=rank_color,
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
