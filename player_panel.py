"""Player panel management with orientation support."""
import pygame
from typing import Tuple, Dict, List, Optional
from config import PLAYER_COLORS, Colors

class PlayerPanel:
    """Represents a player's panel with orientation."""
    
    # Panel positions around the table
    POSITIONS = {
        0: ("bottom", 0, 0),      # Bottom left - normal orientation
        1: ("bottom", 1, 0),      # Bottom center - normal orientation
        2: ("bottom", 2, 0),      # Bottom right - normal orientation
        3: ("top", 0, 180),       # Top left - upside down
        4: ("top", 1, 180),       # Top center - upside down
        5: ("top", 2, 180),       # Top right - upside down
        6: ("left", 0, 90),       # Left - rotated 90° (clockwise from their view)
        7: ("right", 0, 270),     # Right - rotated 270° (counter-clockwise from their view)
    }
    
    def __init__(self, player_idx: int, screen_size: Tuple[int, int]):
        self.player_idx = player_idx
        self.screen_size = screen_size
        self.color = PLAYER_COLORS[player_idx]
        
        # Get position info
        edge, slot, orientation = self.POSITIONS[player_idx]
        self.edge = edge
        self.slot = slot
        self.orientation = orientation
        
        # Calculate rect
        self.rect = self._calculate_rect()
        
    def _calculate_rect(self) -> pygame.Rect:
        """Calculate the panel rectangle based on position."""
        w, h = self.screen_size
        
        if self.edge in ("top", "bottom"):
            # Horizontal panels
            panel_w = w // 3
            panel_h = int(h * 0.10)
            x = self.slot * panel_w
            y = 0 if self.edge == "top" else h - panel_h
            return pygame.Rect(x, y, panel_w, panel_h)
        
        else:  # left or right
            # Vertical panels
            panel_w = int(w * 0.12)
            panel_h = h - int(h * 0.20)  # Leave space for top/bottom panels
            x = 0 if self.edge == "left" else w - panel_w
            y = int(h * 0.10)
            return pygame.Rect(x, y, panel_w, panel_h)
    
    def is_vertical(self) -> bool:
        """Check if panel is vertically oriented."""
        return self.orientation in (90, 270)
    
    def get_grid_rect(self, grid_x: float, grid_y: float, 
                    grid_w: float, grid_h: float,
                    grid_cols: int = None, grid_rows: int = None) -> pygame.Rect:
        """
        Get a rect within the panel using grid coordinates.
        Grid coordinates are in logical space (as if panel was not rotated).
        """
        # Default grid size based on orientation
        if grid_cols is None or grid_rows is None:
            if self.is_vertical():
                grid_cols, grid_rows = 4, 12
            else:
                grid_cols, grid_rows = 12, 4
        
        # Calculate cell size
        cell_w = self.rect.width / grid_cols
        cell_h = self.rect.height / grid_rows
        
        # Calculate rect
        x = self.rect.left + grid_x * cell_w
        y = self.rect.top + grid_y * cell_h
        w = grid_w * cell_w
        h = grid_h * cell_h
        
        return pygame.Rect(int(x), int(y), int(w), int(h))
    
    def draw_background(self, surface: pygame.Surface, is_current: bool = False):
        """Draw panel background."""
        # Washed color background
        washed = tuple(min(255, int(c * 0.75 + 180 * 0.25)) for c in self.color)
        pygame.draw.rect(surface, washed, self.rect.inflate(8, 8), border_radius=8)
        
        # Current player gold border
        if is_current:
            border_width = max(2, int(self.screen_size[0] * 0.0025))
            pygame.draw.rect(surface, Colors.GOLD, self.rect.inflate(6, 6), 
                        width=border_width, border_radius=8)


def calculate_all_panels(screen_size: Tuple[int, int]) -> List[PlayerPanel]:
    """Create all 8 player panels."""
    return [PlayerPanel(i, screen_size) for i in range(8)]