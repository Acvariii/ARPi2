"""Player panel system for Pyglet games - matching Pygame layout."""
from typing import Tuple, List
from config import PLAYER_COLORS


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
    
    def __init__(self, player_idx: int, screen_width: int, screen_height: int):
        self.player_idx = player_idx
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.color = PLAYER_COLORS[player_idx]
        
        side, slot, orientation = self.POSITIONS[player_idx]
        self.side = side
        self.slot = slot
        self.orientation = orientation
        
        self.x, self.y, self.width, self.height = self._calculate_rect()
    
    def _calculate_rect(self) -> Tuple[int, int, int, int]:
        """Calculate panel rectangle based on position (x, y, width, height)."""
        w, h = self.screen_width, self.screen_height
        
        if self.side == "bottom":
            panel_w = w // 3
            panel_h = int(h * 0.10)
            x = self.slot * panel_w
            y = h - panel_h
            return (x, y, panel_w, panel_h)
        
        elif self.side == "top":
            panel_w = w // 3
            panel_h = int(h * 0.10)
            x = self.slot * panel_w
            y = 0
            return (x, y, panel_w, panel_h)
        
        elif self.side == "left":
            panel_w = int(w * 0.12)
            panel_h = h - int(h * 0.20)
            x = 0
            y = int(h * 0.10)
            return (x, y, panel_w, panel_h)
        
        else:  # right
            panel_w = int(w * 0.12)
            panel_h = h - int(h * 0.20)
            x = w - panel_w
            y = int(h * 0.10)
            return (x, y, panel_w, panel_h)
    
    def is_vertical(self) -> bool:
        """Check if panel is vertically oriented."""
        return self.side in ("left", "right")
    
    def get_center(self) -> Tuple[int, int]:
        """Get center point of panel."""
        return (self.x + self.width // 2, self.y + self.height // 2)


def calculate_all_panels(screen_width: int, screen_height: int) -> List[PlayerPanel]:
    """Calculate all 8 player panels."""
    return [PlayerPanel(i, screen_width, screen_height) for i in range(8)]
