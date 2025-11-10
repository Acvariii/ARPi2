"""Reusable UI components for ARPi2."""
import pygame
import time
import math
from typing import Tuple, List, Dict, Optional, Callable
from config import HOVER_TIME_THRESHOLD, Colors

class HoverButton:
    """Button that activates on sustained hover."""
    
    def __init__(self, rect: pygame.Rect, text: str, font: pygame.font.Font, 
                 radius: int = 12, orientation: int = 0):
        self.rect = rect
        self.text = text
        self.font = font
        self.radius = radius
        self.orientation = orientation  # 0, 90, 180, 270 degrees
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
        
        # Remove stale hover keys
        for key in list(self.hover_start.keys()):
            if key not in active_keys:
                self.hover_start.pop(key)
        
        return False
    
    def draw(self, surface: pygame.Surface):
        """Draw the button."""
        # Determine colors based on state
        if not self.enabled:
            bg_color = Colors.DISABLED
            text_color = Colors.DISABLED_TEXT
        elif self.hover_start:
            bg_color = (100, 180, 250)
            text_color = Colors.WHITE
        else:
            bg_color = (60, 120, 200)
            text_color = Colors.WHITE
        
        # Draw shadow
        shadow_rect = self.rect.move(4, 6)
        pygame.draw.rect(surface, Colors.SHADOW, shadow_rect, border_radius=self.radius)
        
        # Draw button background
        pygame.draw.rect(surface, bg_color, self.rect, border_radius=self.radius)
        
        # Draw text (rotated if needed)
        text_surf = self.font.render(self.text, True, text_color)
        if self.orientation != 0:
            text_surf = pygame.transform.rotate(text_surf, self.orientation)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)
    
    def get_hover_progress(self) -> List[Dict]:
        """Get hover progress for all active hovers."""
        now = time.time()
        progress_list = []
        
        for key, start_time in self.hover_start.items():
            elapsed = now - start_time
            progress = min(1.0, elapsed / HOVER_TIME_THRESHOLD)
            progress_list.append({
                "key": key,
                "progress": progress,
                "rect": self.rect
            })
        
        return progress_list
    
    def reset(self):
        """Reset button state."""
        self.clicked = False
        self.hover_start.clear()


class RotatedText:
    """Helper for drawing rotated text."""
    
    @staticmethod
    def draw(surface: pygame.Surface, text: str, font: pygame.font.Font, 
            color: Tuple[int, int, int], center: Tuple[int, int], 
            angle: int, max_width: Optional[int] = None):
        """Draw text rotated by angle (in degrees) around center point."""
        # Truncate text if needed
        if max_width:
            original_width = font.size(text)[0]
            if original_width > max_width:
                short_text = text
                while font.size(short_text + "...")[0] > max_width and len(short_text) > 0:
                    short_text = short_text[:-1]
                text = short_text + "..."
        
        # Render and rotate
        text_surf = font.render(text, True, color)
        if angle != 0:
            text_surf = pygame.transform.rotate(text_surf, angle)
        text_rect = text_surf.get_rect(center=center)
        surface.blit(text_surf, text_rect)
    
    @staticmethod
    def draw_wrapped(surface: pygame.Surface, text: str, font: pygame.font.Font,
                    color: Tuple[int, int, int], rect: pygame.Rect, 
                    angle: int = 0, align: str = "center"):
        """Draw word-wrapped text within a rect, optionally rotated."""
        words = text.split(' ')
        lines = []
        current_line = ""
        
        # Word wrap
        for word in words:
            test_line = f"{current_line} {word}".strip()
            if font.size(test_line)[0] <= rect.width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        
        # Calculate total height
        line_height = font.get_linesize()
        total_height = len(lines) * line_height
        
        # Draw lines
        start_y = rect.centery - total_height // 2
        for i, line in enumerate(lines):
            line_surf = font.render(line, True, color)
            if angle != 0:
                line_surf = pygame.transform.rotate(line_surf, angle)
            
            y_pos = start_y + i * line_height
            
            if align == "center":
                x_pos = rect.centerx - line_surf.get_width() // 2
            elif align == "left":
                x_pos = rect.left
            else:  # right
                x_pos = rect.right - line_surf.get_width()
            
            surface.blit(line_surf, (x_pos, y_pos))


def draw_cursor(surface: pygame.Surface, pos: Tuple[int, int], color: Tuple[int, int, int]):
    """Draw a fingertip cursor."""
    pygame.draw.circle(surface, Colors.WHITE, pos, 20)
    pygame.draw.circle(surface, color, pos, 14)
    pygame.draw.circle(surface, Colors.BLACK, pos, 4)


def draw_circular_progress(surface: pygame.Surface, center: Tuple[int, int], 
                        radius: int, progress: float, 
                        color: Tuple[int, int, int] = Colors.ACCENT, 
                        bg_color: Tuple[int, int, int] = (60, 60, 60),
                        thickness: int = 6):
    """Draw a circular progress indicator."""
    # Background circle
    pygame.draw.circle(surface, bg_color, center, radius, thickness)
    
    # Progress arc
    if progress > 0:
        start_angle = -math.pi / 2
        end_angle = start_angle + (progress * 2 * math.pi)
        
        rect = pygame.Rect(
            center[0] - radius,
            center[1] - radius,
            radius * 2,
            radius * 2
        )
        
        pygame.draw.arc(surface, color, rect, start_angle, end_angle, thickness)


class ProgressBar:
    """Horizontal or vertical progress bar."""
    
    def __init__(self, rect: pygame.Rect, orientation: str = "horizontal"):
        self.rect = rect
        self.orientation = orientation  # "horizontal" or "vertical"
        self.progress = 0.0  # 0.0 to 1.0
        
    def set_progress(self, progress: float):
        """Set progress (0.0 to 1.0)."""
        self.progress = max(0.0, min(1.0, progress))
    
    def draw(self, surface: pygame.Surface, 
            fg_color: Tuple[int, int, int] = Colors.ACCENT,
            bg_color: Tuple[int, int, int] = (40, 40, 40)):
        """Draw the progress bar."""
        # Background
        pygame.draw.rect(surface, bg_color, self.rect, border_radius=4)
        
        # Foreground (progress)
        if self.progress > 0:
            if self.orientation == "horizontal":
                progress_width = int(self.rect.width * self.progress)
                progress_rect = pygame.Rect(
                    self.rect.x, self.rect.y,
                    progress_width, self.rect.height
                )
            else:  # vertical
                progress_height = int(self.rect.height * self.progress)
                progress_rect = pygame.Rect(
                    self.rect.x,
                    self.rect.y + (self.rect.height - progress_height),
                    self.rect.width,
                    progress_height
                )
            
            pygame.draw.rect(surface, fg_color, progress_rect, border_radius=4)