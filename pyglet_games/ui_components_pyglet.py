"""
Reusable UI Components for Pyglet Games
Includes buttons, panels, and text rendering with proper orientations
"""

import time
from typing import List, Dict, Tuple, Optional
from pyglet_games.renderer import PygletRenderer
from config import PLAYER_COLORS, HOVER_TIME_THRESHOLD


class PygletButton:
    """Button with hover progress tracking and orientation support"""
    
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
            self.hover_start = 0.0
            return False, 0.0
        
        for meta in fingertips:
            x, y = meta["pos"]
            if (self.x <= x <= self.x + self.width and 
                self.y <= y <= self.y + self.height):
                if not self.hovering:
                    self.hover_start = current_time
                    self.hovering = True
                
                progress = (current_time - self.hover_start) / HOVER_TIME_THRESHOLD
                if progress >= 1.0:
                    self.hovering = False
                    self.hover_start = 0.0
                    return True, 1.0
                return False, progress
        
        self.hovering = False
        if self.hover_start > 0:
            self.hover_start = 0.0
        return False, 0.0
    
    def draw(self, renderer: PygletRenderer, hover_progress: float = 0.0):
        """Draw button with orientation-aware text"""
        if not self.enabled:
            bg = (100, 100, 100)
            text_color = (160, 160, 160)
        else:
            base = (70, 130, 180)
            hover = (100, 180, 220)
            bg = tuple(int(base[i] + (hover[i] - base[i]) * hover_progress) for i in range(3))
            text_color = (255, 255, 255)
        
        # Draw button background
        renderer.draw_rect(bg, (self.x, self.y, self.width, self.height))
        renderer.draw_rect((200, 200, 200), (self.x, self.y, self.width, self.height), width=2)
        
        # Draw progress bar oriented correctly for vertical/horizontal panels
        if hover_progress > 0:
            if self.orientation in [90, 270]:  # Vertical panels
                bar_h = int(self.height * hover_progress)
                if self.orientation == 270:  # Left - bar at right edge from player view
                    renderer.draw_rect((255, 215, 0), (self.x + self.width - 4, self.y, 4, bar_h))
                else:  # Right - bar at left edge from player view
                    renderer.draw_rect((255, 215, 0), (self.x, self.y, 4, bar_h))
            else:  # Horizontal panels
                bar_w = int(self.width * hover_progress)
                renderer.draw_rect((255, 215, 0), (self.x, self.y + self.height - 4, bar_w, 4))
        
        # Draw text with proper rotation based on orientation
        cx = self.x + self.width // 2
        cy = self.y + self.height // 2
        
        # Match the rotation swap we do in draw_text_oriented
        # Left panel (270) should show text at 90° to face left player
        # Right panel (90) should show text at 270° to face right player
        text_rotation = self.orientation
        if self.orientation == 270:  # Left panel
            text_rotation = 90
        elif self.orientation == 90:  # Right panel
            text_rotation = 270
        
        renderer.draw_text(
            self.text, cx, cy,
            'Arial', 18, text_color, anchor_x='center', anchor_y='center',
            rotation=text_rotation
        )


class PlayerPanel:
    """Player panel with orientation-aware rendering"""
    
    # Panel positions matching player_panel.py
    POSITIONS = {
        0: ("bottom", 0, 0),      # Bottom left - normal
        1: ("bottom", 1, 0),      # Bottom center - normal
        2: ("bottom", 2, 0),      # Bottom right - normal
        3: ("top", 0, 180),       # Top left - upside down
        4: ("top", 1, 180),       # Top center - upside down
        5: ("top", 2, 180),       # Top right - upside down
        6: ("left", 0, 270),      # Left - rotated 270 (text faces right)
        7: ("right", 0, 90),      # Right - rotated 90 (text faces left)
    }
    
    def __init__(self, player_idx: int, screen_width: int, screen_height: int):
        self.player_idx = player_idx
        self.width = screen_width
        self.height = screen_height
        self.color = PLAYER_COLORS[player_idx]
        
        side, slot, orientation = self.POSITIONS[player_idx]
        self.side = side
        self.slot = slot
        self.orientation = orientation
        
        self.rect = self._calculate_rect()
    
    def _calculate_rect(self) -> Tuple[int, int, int, int]:
        """Calculate panel rectangle based on position"""
        w, h = self.width, self.height
        panel_h = int(h * 0.10)
        panel_w_side = int(w * 0.12)
        
        if self.side == "bottom":
            panel_w = w // 3
            x = self.slot * panel_w
            y = h - panel_h
            return (x, y, panel_w, panel_h)
        
        elif self.side == "top":
            panel_w = w // 3
            x = self.slot * panel_w
            y = 0
            return (x, y, panel_w, panel_h)
        
        elif self.side == "left":
            x = 0
            y = panel_h
            panel_height = h - 2 * panel_h
            return (x, y, panel_w_side, panel_height)
        
        else:  # right
            x = w - panel_w_side
            y = panel_h
            panel_height = h - 2 * panel_h
            return (x, y, panel_w_side, panel_height)
    
    def draw_background(self, renderer: PygletRenderer, is_current: bool = False):
        """Draw panel background"""
        x, y, w, h = self.rect
        
        # Washed color
        washed = tuple(min(255, int(c * 0.75 + 180 * 0.25)) for c in self.color)
        renderer.draw_rect(washed, (x, y, w, h))
        
        # Border
        border_color = (255, 215, 0) if is_current else (150, 150, 150)
        border_w = 4 if is_current else 2
        renderer.draw_rect(border_color, (x, y, w, h), width=border_w)
    
    def draw_text_oriented(self, renderer: PygletRenderer, text: str, 
                          x_offset: float, y_offset: float, font_size: int, color: Tuple[int, int, int]):
        """Draw text with proper orientation and rotation for the panel"""
        x, y, w, h = self.rect
        
        # Calculate position based on orientation
        if self.orientation == 0:  # Bottom - normal
            tx = x + int(w * x_offset)
            ty = y + int(h * y_offset)
            anchor_x, anchor_y = 'center', 'center'
            rotation = 0
        
        elif self.orientation == 180:  # Top - upside down
            # For top players, text should be rotated 180 degrees
            tx = x + int(w * x_offset)
            ty = y + int(h * (1 - y_offset))  # Flip position
            anchor_x, anchor_y = 'center', 'center'
            rotation = 180
        
        elif self.orientation == 270:  # Left - text should face left player (rotate 90)
            # For left panel, rotate text 90 degrees to face the left side
            tx = x + int(w * (1 - y_offset))
            ty = y + int(h * x_offset)
            anchor_x, anchor_y = 'center', 'center'
            rotation = 90
        
        else:  # orientation == 90, Right - text should face right player (rotate 270)
            # For right panel, rotate text 270 degrees to face the right side
            tx = x + int(w * y_offset)
            ty = y + int(h * (1 - x_offset))
            anchor_x, anchor_y = 'center', 'center'
            rotation = 270
        
        renderer.draw_text(text, tx, ty, 'Arial', font_size, color, 
                          anchor_x=anchor_x, anchor_y=anchor_y, rotation=rotation)
    
    def get_button_layout(self) -> List[Tuple[int, int, int, int]]:
        """Get button rectangles for this panel's orientation"""
        x, y, w, h = self.rect
        margin = 10
        gap = 8
        
        if self.orientation == 0:  # Bottom
            info_h = int(h * 0.45)
            btn_h = h - info_h - 2 * margin
            btn_w = (w - 2 * margin - 2 * gap) // 3
            btn_y = y + info_h + margin
            
            return [
                (x + margin, btn_y, btn_w, btn_h),
                (x + margin + btn_w + gap, btn_y, btn_w, btn_h),
                (x + margin + 2*(btn_w+gap), btn_y, btn_w, btn_h)
            ]
        
        elif self.orientation == 180:  # Top
            info_h = int(h * 0.45)
            btn_h = h - info_h - 2 * margin
            btn_w = (w - 2 * margin - 2 * gap) // 3
            btn_y = y + margin
            
            return [
                (x + margin, btn_y, btn_w, btn_h),
                (x + margin + btn_w + gap, btn_y, btn_w, btn_h),
                (x + margin + 2*(btn_w+gap), btn_y, btn_w, btn_h)
            ]
        
        elif self.orientation in [90, 270]:  # Left/Right - vertical layout
            # Grid system: 70% buttons (close to player), 30% info (far from player)
            btn_area_w = int(w * 0.70)
            info_area_w = w - btn_area_w
            btn_h = (h - 2 * margin - 2 * gap) // 3
            
            if self.orientation == 270:  # Left panel: buttons CLOSE to left player (on left), info on right
                btn_x = x + margin
                btn_w = btn_area_w - 2 * margin
            else:  # Right panel (90): buttons CLOSE to right player (on right), info on left
                btn_x = x + info_area_w + margin
                btn_w = btn_area_w - 2 * margin
            
            return [
                (btn_x, y + margin, btn_w, btn_h),
                (btn_x, y + margin + btn_h + gap, btn_w, btn_h),
                (btn_x, y + margin + 2*(btn_h+gap), btn_w, btn_h)
            ]
        
        return []


def calculate_all_panels(screen_width: int, screen_height: int) -> List[PlayerPanel]:
    """Calculate all 8 player panels"""
    return [PlayerPanel(i, screen_width, screen_height) for i in range(8)]


def draw_hover_indicators(renderer: PygletRenderer, buttons: Dict[int, Dict[str, PygletButton]], 
                         active_players: List[int], current_time: float):
    """Draw circular progress indicators for all hovering buttons"""
    for idx in active_players:
        if idx not in buttons:
            continue
        for btn in buttons[idx].values():
            if btn.hovering and btn.hover_start > 0:
                progress = min(1.0, (current_time - btn.hover_start) / HOVER_TIME_THRESHOLD)
                cx = btn.x + btn.width // 2
                cy = btn.y + btn.height // 2
                renderer.draw_circular_progress((cx, cy), 30, progress, (100, 200, 255), thickness=5)
