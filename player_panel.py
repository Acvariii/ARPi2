"""Player panel positioning and orientation system."""
from typing import Tuple
import pygame
from config import PLAYER_COLORS, Colors


class PlayerPanel:
    """Represents a player's panel with orientation."""
    
    # Panel positions around the table
    # Orientation angles for text rotation
    POSITIONS = {
        0: ("bottom", 0, 0),      # Bottom left - normal
        1: ("bottom", 1, 0),      # Bottom center - normal
        2: ("bottom", 2, 0),      # Bottom right - normal
        3: ("top", 0, 180),       # Top left - upside down
        4: ("top", 1, 180),       # Top center - upside down
        5: ("top", 2, 180),       # Top right - upside down
        6: ("left", 0, 90),       # Left - rotated left
        7: ("right", 0, 270),     # Right - rotated right
    }
    
    def __init__(self, player_idx: int, screen_size: Tuple[int, int]):
        self.player_idx = player_idx
        self.screen_size = screen_size
        self.color = PLAYER_COLORS[player_idx]
        
        side, slot, orientation = self.POSITIONS[player_idx]
        self.side = side
        self.slot = slot
        self.orientation = orientation
        
        self.rect = self._calculate_rect()
    
    def _calculate_rect(self) -> pygame.Rect:
        """Calculate panel rectangle based on position."""
        w, h = self.screen_size
        
        if self.side == "bottom":
            panel_w = w // 3
            panel_h = int(h * 0.10)
            x = self.slot * panel_w
            y = h - panel_h
            return pygame.Rect(x, y, panel_w, panel_h)
        
        elif self.side == "top":
            panel_w = w // 3
            panel_h = int(h * 0.10)
            x = self.slot * panel_w
            y = 0
            return pygame.Rect(x, y, panel_w, panel_h)
        
        elif self.side == "left":
            panel_w = int(w * 0.12)
            panel_h = h - int(h * 0.20)
            x = 0
            y = int(h * 0.10)
            return pygame.Rect(x, y, panel_w, panel_h)
        
        else:  # right
            panel_w = int(w * 0.12)
            panel_h = h - int(h * 0.20)
            x = w - panel_w
            y = int(h * 0.10)
            return pygame.Rect(x, y, panel_w, panel_h)
    
    def is_vertical(self) -> bool:
        """Check if panel is vertically oriented."""
        return self.side in ("left", "right")
    
    def get_grid_rect(self, col: float, row: float, width: float, height: float, 
                     total_cols: int, total_rows: int) -> pygame.Rect:
        """Get a rect within the panel using grid coordinates."""
        cell_w = self.rect.width / total_cols
        cell_h = self.rect.height / total_rows
        
        x = self.rect.x + int(col * cell_w)
        y = self.rect.y + int(row * cell_h)
        w = int(width * cell_w)
        h = int(height * cell_h)
        
        return pygame.Rect(x, y, w, h)
    
    def draw_background(self, surface: pygame.Surface, is_current: bool = False):
        """Draw panel background."""
        washed = tuple(min(255, int(c * 0.75 + 180 * 0.25)) for c in self.color)
        pygame.draw.rect(surface, washed, self.rect.inflate(8, 8), border_radius=8)
        
        if is_current:
            border_width = max(2, int(self.screen_size[0] * 0.0025))
            pygame.draw.rect(surface, Colors.GOLD, self.rect.inflate(6, 6), 
                           width=border_width, border_radius=8)


def calculate_all_panels(screen_size: Tuple[int, int]):
    """Calculate all 8 player panels."""
    return [PlayerPanel(i, screen_size) for i in range(8)]