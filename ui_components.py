"""UI components with proper rotation support for all orientations."""
import time
import pygame
import math
from typing import List, Dict, Tuple, Optional
from config import HOVER_TIME_THRESHOLD, Colors


class HoverButton:
    """Button that activates on sustained hover with modern styling."""
    
    def __init__(self, rect: pygame.Rect, text: str, font: pygame.font.Font, 
                 radius: int = 8, orientation: int = 0):
        self.rect = rect
        self.text = text
        self.font = font
        self.radius = radius
        self.orientation = orientation  # 0, 90, 180, 270
        self.hover_start: Dict[str, float] = {}
        self.clicked = False
        self.enabled = True
    
    def update(self, fingertip_meta: List[Dict], enabled: bool = True) -> bool:
        """Update hover state and return True if clicked."""
        self.enabled = enabled
        
        if not enabled:
            self.hover_start.clear()
            return False
            
        now = time.time()
        active_keys = set()
        
        for meta in fingertip_meta:
            pos = meta.get("pos")
            if not pos or not self.rect.collidepoint(pos):
                continue
                
            hand = meta.get("hand")
            name = meta.get("name", "")
            key = f"{hand}:{name}" if hand is not None else f"pos:{pos[0]}_{pos[1]}"
            active_keys.add(key)
            
            if key not in self.hover_start:
                self.hover_start[key] = now
            elif (now - self.hover_start[key]) >= HOVER_TIME_THRESHOLD:
                self.clicked = True
                self.hover_start.clear()
                return True
        
        for key in list(self.hover_start.keys()):
            if key not in active_keys:
                self.hover_start.pop(key)
        
        return False
    
    def draw(self, surface: pygame.Surface):
        """Draw the button with modern styling."""
        # Determine colors
        if not self.enabled:
            bg_color = (60, 60, 60)
            text_color = (120, 120, 120)
            border_color = (40, 40, 40)
        elif self.hover_start:
            bg_color = (80, 160, 240)
            text_color = Colors.WHITE
            border_color = (100, 180, 255)
        else:
            bg_color = (50, 100, 180)
            text_color = (220, 220, 220)
            border_color = (40, 80, 140)
        
        # Shadow
        shadow_rect = self.rect.move(3, 3)
        shadow_surf = pygame.Surface((shadow_rect.width, shadow_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(shadow_surf, (0, 0, 0, 60), shadow_surf.get_rect(), border_radius=self.radius)
        surface.blit(shadow_surf, shadow_rect)
        
        # Background
        pygame.draw.rect(surface, bg_color, self.rect, border_radius=self.radius)
        
        # Highlight
        if self.enabled:
            highlight_rect = self.rect.inflate(-4, -4)
            highlight_rect.height = highlight_rect.height // 3
            pygame.draw.rect(surface, tuple(min(255, c + 30) for c in bg_color), 
                           highlight_rect, border_radius=self.radius)
        
        # Border
        pygame.draw.rect(surface, border_color, self.rect, width=2, border_radius=self.radius)
        
        # Draw text - render normally first
        text_surf = self.font.render(self.text, True, text_color)
        
        # Rotate based on orientation
        if self.orientation == 90:
            text_surf = pygame.transform.rotate(text_surf, -90)  # Clockwise
        elif self.orientation == 180:
            text_surf = pygame.transform.rotate(text_surf, 180)
        elif self.orientation == 270:
            text_surf = pygame.transform.rotate(text_surf, 90)  # Counter-clockwise
        
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)
    
    def get_hover_progress(self) -> List[Dict]:
        """Get hover progress for visualization."""
        now = time.time()
        result = []
        for key, start_time in self.hover_start.items():
            progress = min(1.0, (now - start_time) / HOVER_TIME_THRESHOLD)
            result.append({
                "key": key,
                "progress": progress,
                "rect": self.rect
            })
        return result
    
    def reset(self):
        """Reset button state."""
        self.clicked = False
        self.hover_start.clear()


class RotatedText:
    """Helper for drawing text with proper rotation for each player orientation."""
    
    @staticmethod
    def draw(surface: pygame.Surface, text: str, font: pygame.font.Font, 
            color: Tuple[int, int, int], pos: Tuple[int, int], 
            orientation: int, max_width: Optional[int] = None):
        """
        Draw text at position with given orientation.
        
        Args:
            surface: Surface to draw on
            text: Text to render
            font: Font to use
            color: Text color
            pos: (x, y) center position
            orientation: 0=bottom, 90=left, 180=top, 270=right
            max_width: Maximum width before truncating
        """
        # Truncate if needed
        display_text = text
        if max_width:
            while display_text and font.size(display_text)[0] > max_width:
                display_text = display_text[:-4] + "..."
                if len(display_text) <= 3:
                    break
        
        # Render text normally first
        text_surf = font.render(display_text, True, color)
        
        # Apply rotation based on orientation
        # orientation 0 = bottom panels (no rotation)
        # orientation 90 = left panel (rotate so text reads vertically from their view)
        # orientation 180 = top panels (upside down)
        # orientation 270 = right panel (rotate so text reads vertically from their view)
        
        if orientation == 90:
            # Left side: rotate -90 degrees (clockwise) so it reads bottom-to-top from left
            text_surf = pygame.transform.rotate(text_surf, -90)
        elif orientation == 180:
            # Top: rotate 180 degrees
            text_surf = pygame.transform.rotate(text_surf, 180)
        elif orientation == 270:
            # Right side: rotate 90 degrees (counter-clockwise) so it reads top-to-bottom from right
            text_surf = pygame.transform.rotate(text_surf, 90)
        
        # Center at position
        text_rect = text_surf.get_rect(center=pos)
        surface.blit(text_surf, text_rect)
    
    @staticmethod
    def draw_wrapped(surface: pygame.Surface, text: str, font: pygame.font.Font,
                    color: Tuple[int, int, int], rect: pygame.Rect, 
                    orientation: int = 0):
        """
        Draw word-wrapped text within a rectangle.
        
        Args:
            surface: Surface to draw on
            text: Text to wrap and render
            font: Font to use
            color: Text color
            rect: Rectangle to draw within
            orientation: 0, 90, 180, or 270
        """
        # For vertical orientations, we need to wrap based on height dimension
        if orientation in (90, 270):
            wrap_width = rect.height - 40
        else:
            wrap_width = rect.width - 40
        
        # Word wrap
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            test_line = f"{current_line} {word}".strip()
            if font.size(test_line)[0] <= wrap_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        
        # Calculate line spacing
        line_height = font.get_linesize() + 6
        total_height = len(lines) * line_height
        
        # Draw each line
        start_y = rect.centery - total_height // 2
        for i, line in enumerate(lines):
            y_pos = start_y + i * line_height
            RotatedText.draw(surface, line, font, color, 
                           (rect.centerx, y_pos), orientation)


def draw_circular_progress(surface: pygame.Surface, center: Tuple[int, int], 
                          radius: int, progress: float, color: Tuple[int, int, int],
                          thickness: int = 4):
    """Draw a circular progress indicator."""
    if progress <= 0:
        return
    
    # Background circle
    pygame.draw.circle(surface, (40, 40, 40), center, radius, thickness)
    
    # Progress arc
    if progress >= 0.01:
        angle = int(360 * progress)
        points = [center]
        for i in range(angle + 1):
            rad = math.radians(i - 90)
            x = center[0] + int(radius * math.cos(rad))
            y = center[1] + int(radius * math.sin(rad))
            points.append((x, y))
        
        if len(points) > 2:
            pygame.draw.polygon(surface, color + (128,), points)
    
    pygame.draw.circle(surface, color, center, radius, thickness)


def draw_cursor(surface: pygame.Surface, pos: Tuple[int, int], 
               color: Tuple[int, int, int] = Colors.WHITE):
    """Draw a cursor at position."""
    pygame.draw.circle(surface, Colors.WHITE, pos, 18)
    pygame.draw.circle(surface, color, pos, 12)
    pygame.draw.circle(surface, Colors.BLACK, pos, 4)