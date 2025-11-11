"""Reusable UI components for ARPi2."""
import pygame
import time
import math
from typing import Tuple, List, Dict, Optional, Callable
from config import HOVER_TIME_THRESHOLD, Colors

class HoverButton:
    """Button that activates on sustained hover with modern styling."""
    
    def __init__(self, rect: pygame.Rect, text: str, font: pygame.font.Font, 
                 radius: int = 8, orientation: int = 0):
        self.rect = rect
        self.text = text
        self.font = font
        self.radius = radius
        self.orientation = orientation
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
        """Draw the button with modern styling."""
        # Determine colors based on state
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
        
        # Modern drop shadow
        shadow_rect = self.rect.move(3, 3)
        shadow_surf = pygame.Surface((shadow_rect.width, shadow_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(shadow_surf, (0, 0, 0, 60), shadow_surf.get_rect(), border_radius=self.radius)
        surface.blit(shadow_surf, shadow_rect)
        
        # Button background
        pygame.draw.rect(surface, bg_color, self.rect, border_radius=self.radius)
        
        # Subtle inner highlight
        if self.enabled:
            highlight_rect = self.rect.inflate(-4, -4)
            highlight_rect.height = highlight_rect.height // 3
            pygame.draw.rect(surface, tuple(min(255, c + 30) for c in bg_color), 
                           highlight_rect, border_radius=self.radius)
        
        # Border
        pygame.draw.rect(surface, border_color, self.rect, width=2, border_radius=self.radius)
        
        # Draw text with rotation
        text_surf = self.font.render(self.text, True, text_color)
        
        # Simply rotate by orientation angle
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
            while text and font.size(text)[0] > max_width:
                text = text[:-4] + "..."
                if len(text) <= 3:
                    break
        
        # Render text horizontally first
        text_surf = font.render(text, True, color)
        
        # Simply rotate by the angle (pygame rotates counter-clockwise)
        if angle != 0:
            text_surf = pygame.transform.rotate(text_surf, angle)
        
        # Center the rotated text at the given point
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
        
        # For vertical orientations, use height as constraint
        if angle in (90, 270):
            max_width = rect.height - 40
        else:
            max_width = rect.width - 40
        
        # Word wrap
        for word in words:
            test_line = f"{current_line} {word}".strip()
            if font.size(test_line)[0] <= max_width:
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
        
        # Draw each line with proper spacing
        start_y = rect.centery - total_height // 2
        for i, line in enumerate(lines):
            y_pos = start_y + i * line_height
            RotatedText.draw(surface, line, font, color, 
                           (rect.centerx, y_pos), angle)


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