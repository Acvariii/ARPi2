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
        self.orientation = orientation
        self.hover_start: Dict[str, float] = {}
        self.clicked = False
        self.enabled = True
    
    def update(self, fingertip_meta: List[Dict], enabled: bool = True) -> bool:
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
        
        shadow_rect = self.rect.move(3, 3)
        shadow_surf = pygame.Surface((shadow_rect.width, shadow_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(shadow_surf, (0, 0, 0, 60), shadow_surf.get_rect(), border_radius=self.radius)
        surface.blit(shadow_surf, shadow_rect)
        
        pygame.draw.rect(surface, bg_color, self.rect, border_radius=self.radius)
        
        if self.enabled:
            highlight_rect = self.rect.inflate(-4, -4)
            highlight_rect.height = highlight_rect.height // 3
            pygame.draw.rect(surface, tuple(min(255, c + 30) for c in bg_color), 
                           highlight_rect, border_radius=self.radius)
        
        pygame.draw.rect(surface, border_color, self.rect, width=2, border_radius=self.radius)
        
        text_surf = self.font.render(self.text, True, text_color)
        
        if self.orientation == 90:
            text_surf = pygame.transform.rotate(text_surf, -90)
        elif self.orientation == 180:
            text_surf = pygame.transform.rotate(text_surf, 180)
        elif self.orientation == 270:
            text_surf = pygame.transform.rotate(text_surf, 90)
        
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)
    
    def get_hover_progress(self) -> List[Dict]:
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
        self.clicked = False
        self.hover_start.clear()


class RotatedText:
    
    @staticmethod
    def draw(surface: pygame.Surface, text: str, font: pygame.font.Font, 
            color: Tuple[int, int, int], pos: Tuple[int, int], 
            orientation: int, max_width: Optional[int] = None):
        display_text = text
        if max_width:
            while display_text and font.size(display_text)[0] > max_width:
                display_text = display_text[:-4] + "..."
                if len(display_text) <= 3:
                    break
        
        text_surf = font.render(display_text, True, color)
        
        if orientation == 90:
            text_surf = pygame.transform.rotate(text_surf, -90)
        elif orientation == 180:
            text_surf = pygame.transform.rotate(text_surf, 180)
        elif orientation == 270:
            text_surf = pygame.transform.rotate(text_surf, 90)
        
        text_rect = text_surf.get_rect(center=pos)
        surface.blit(text_surf, text_rect)
    
    @staticmethod
    def draw_wrapped(surface: pygame.Surface, text: str, font: pygame.font.Font,
                    color: Tuple[int, int, int], rect: pygame.Rect, 
                    orientation: int = 0):
        
        if orientation in (90, 270):
            available_space = rect.height
        else:
            available_space = rect.width
        
        wrap_width = available_space - 80
        
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            test_line = current_line + (" " if current_line else "") + word
            text_width = font.size(test_line)[0]
            
            if text_width <= wrap_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
        
        line_height = font.get_height()
        vertical_spacing = max(12, int(line_height * 0.4))
        total_line_height = line_height + vertical_spacing
        
        total_text_height = len(lines) * line_height + (len(lines) - 1) * vertical_spacing
        
        start_y = rect.centery - (total_text_height // 2)
        
        for i, line in enumerate(lines):
            line_y = start_y + (i * total_line_height)
            RotatedText.draw(surface, line, font, color, 
                           (rect.centerx, line_y), orientation)
    
    @staticmethod
    def draw_stacked(surface: pygame.Surface, lines: List[str], font: pygame.font.Font,
                     color: Tuple[int, int, int], panel_rect: pygame.Rect,
                     orientation: int, top_offset: int = 40, spacing: int = 14):
        """Draw multiple lines for vertical panels without overlap."""
        y = panel_rect.top + top_offset
        cx = panel_rect.centerx
        for line in lines:
            surf = font.render(line, True, color)
            if orientation == 90:
                surf = pygame.transform.rotate(surf, -90)
            elif orientation == 180:
                surf = pygame.transform.rotate(surf, 180)
            elif orientation == 270:
                surf = pygame.transform.rotate(surf, 90)
            rect = surf.get_rect(center=(cx, y + surf.get_height() / 2))
            surface.blit(surf, rect)
            y += surf.get_height() + spacing
    
    @staticmethod
    def draw_stacked_in_rect(surface: pygame.Surface,
                             lines: List[str],
                             font: pygame.font.Font,
                             color: Tuple[int, int, int],
                             rect: pygame.Rect,
                             orientation: int,
                             spacing: int = 14,
                             top_padding: int = 10,
                             center: bool = True):
        """Stack multiple lines inside rect with rotation, no overlap."""
        rendered = []
        max_w = rect.width - 12
        max_v = rect.height - 12
        # For vertical orientations, width constraint uses rect.height due to rotation
        constraint = max_v if orientation in (90, 270) else max_w
        for raw in lines:
            txt = raw
            while txt and font.size(txt)[0] > constraint:
                if len(txt) <= 4:
                    break
                txt = txt[:-4] + "..."
            rendered.append(txt)
        heights = []
        for line in rendered:
            h = font.size(line)[1]
            heights.append(h)
        total_height = sum(heights) + spacing * (len(rendered) - 1)
        if center:
            start_y = rect.top + (rect.height - total_height) // 2
        else:
            start_y = rect.top + top_padding
        cy = start_y
        cx = rect.centerx
        for i, line in enumerate(rendered):
            surf = font.render(line, True, color)
            if orientation == 90:
                surf = pygame.transform.rotate(surf, -90)
            elif orientation == 180:
                surf = pygame.transform.rotate(surf, 180)
            elif orientation == 270:
                surf = pygame.transform.rotate(surf, 90)
            r = surf.get_rect(center=(cx, cy + heights[i] // 2))
            surface.blit(surf, r)
            cy += heights[i] + spacing
    
    @staticmethod
    def draw_block(surface: pygame.Surface,
                   lines: List[Tuple[str, pygame.font.Font, Tuple[int,int,int]]],
                   rect: pygame.Rect,
                   orientation: int,
                   line_spacing: int = 8,
                   padding: int = 8,
                   wrap: bool = False):
        """
        Render multiple lines (optionally wrapped) inside rect, rotate once.
        lines: list of (text, font, color)
        For wrap=True only the FIRST tuple's font/color are used; text is wrapped.
        """
        if not lines:
            return

        # Determine base drawing surface BEFORE rotation
        if orientation in (90, 270):
            base_w, base_h = rect.height, rect.width
        else:
            base_w, base_h = rect.width, rect.height

        block_surf = pygame.Surface((base_w, base_h), pygame.SRCALPHA)

        def wrap_text(text: str, font: pygame.font.Font, max_w: int) -> List[str]:
            words = text.split()
            out, cur = [], ""
            for w in words:
                test = (cur + " " + w).strip()
                if font.size(test)[0] <= max_w:
                    cur = test
                else:
                    if cur:
                        out.append(cur)
                    cur = w
            if cur:
                out.append(cur)
            return out

        rendered: List[pygame.Surface] = []

        if wrap and lines:
            txt, fnt, col = lines[0]
            max_w = base_w - 2 * padding
            for seg in wrap_text(txt, fnt, max_w):
                rendered.append(fnt.render(seg, True, col))
        else:
            for txt, fnt, col in lines:
                # Truncate if too wide
                max_w = base_w - 2 * padding
                if fnt.size(txt)[0] > max_w:
                    t = txt
                    while t and fnt.size(t + "...")[0] > max_w:
                        t = t[:-1]
                    if t:
                        txt = t + "..."
                rendered.append(fnt.render(txt, True, col))

        total_h = sum(s.get_height() for s in rendered) + line_spacing * (len(rendered) - 1)
        y = (base_h - total_h) // 2
        for surf_line in rendered:
            block_surf.blit(surf_line, ( (base_w - surf_line.get_width()) // 2, y ))
            y += surf_line.get_height() + line_spacing

        # Rotate final block once
        if orientation == 90:
            block_surf = pygame.transform.rotate(block_surf, -90)
        elif orientation == 180:
            block_surf = pygame.transform.rotate(block_surf, 180)
        elif orientation == 270:
            block_surf = pygame.transform.rotate(block_surf, 90)

        block_rect = block_surf.get_rect(center=rect.center)
        surface.blit(block_surf, block_rect)


def draw_circular_progress(surface: pygame.Surface, center: Tuple[int, int], 
                          radius: int, progress: float, color: Tuple[int, int, int],
                          thickness: int = 4):
    if progress <= 0:
        return
    
    pygame.draw.circle(surface, (40, 40, 40), center, radius, thickness)
    
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
    pygame.draw.circle(surface, Colors.WHITE, pos, 18)
    pygame.draw.circle(surface, color, pos, 12)
    pygame.draw.circle(surface, Colors.BLACK, pos, 4)


class PlayerSelectionUI:
    
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.screen_w, self.screen_h = screen.get_size()
        self.selected = [False] * 8
        self.hover_start: Dict[int, float] = {}
        
        slot_size = 70
        spacing_x = self.screen_w // 4
        spacing_y = self.screen_h // 3
        
        self.slot_positions = []
        
        self.slot_positions.append((spacing_x * 1, self.screen_h - spacing_y // 2))
        self.slot_positions.append((spacing_x * 2, self.screen_h - spacing_y // 2))
        self.slot_positions.append((spacing_x * 3, self.screen_h - spacing_y // 2))
        
        self.slot_positions.append((spacing_x * 1, spacing_y // 2))
        self.slot_positions.append((spacing_x * 2, spacing_y // 2))
        self.slot_positions.append((spacing_x * 3, spacing_y // 2))
        
        self.slot_positions.append((spacing_x // 2, self.screen_h // 2))
        
        self.slot_positions.append((self.screen_w - spacing_x // 2, self.screen_h // 2))
    
    def update_with_fingertips(self, fingertip_meta: List[Dict]):
        now = time.time()
        active_slots = set()
        
        for meta in fingertip_meta:
            pos = meta["pos"]
            
            for i, (sx, sy) in enumerate(self.slot_positions):
                dist = math.sqrt((pos[0] - sx)**2 + (pos[1] - sy)**2)
                if dist < 60:
                    active_slots.add(i)
                    
                    if i not in self.hover_start:
                        self.hover_start[i] = now
                    elif (now - self.hover_start[i]) >= HOVER_TIME_THRESHOLD:
                        self.selected[i] = not self.selected[i]
                        self.hover_start.pop(i)
                    break
        
        for slot in list(self.hover_start.keys()):
            if slot not in active_slots:
                self.hover_start.pop(slot)
    
    def draw_slots(self):
        from config import PLAYER_COLORS
        
        for i, (x, y) in enumerate(self.slot_positions):
            color = PLAYER_COLORS[i]
            
            if self.selected[i]:
                pygame.draw.circle(self.screen, color, (x, y), 55)
                pygame.draw.circle(self.screen, Colors.WHITE, (x, y), 55, 5)
            else:
                pygame.draw.circle(self.screen, (80, 80, 80), (x, y), 55, 3)
            
            font = pygame.font.SysFont(None, 36, bold=True)
            text_color = Colors.WHITE if self.selected[i] else (150, 150, 150)
            text = font.render(f"P{i+1}", True, text_color)
            text_rect = text.get_rect(center=(x, y))
            self.screen.blit(text, text_rect)
    
    def get_hover_progress(self) -> List[Dict]:
        now = time.time()
        result = []
        for slot, start_time in self.hover_start.items():
            progress = min(1.0, (now - start_time) / HOVER_TIME_THRESHOLD)
            x, y = self.slot_positions[slot]
            result.append({
                "slot": slot,
                "progress": progress,
                "pos": (x, y)
            })
        return result
    
    def selected_count(self) -> int:
        return sum(self.selected)
    
    def closest_player_color(self, pos: Tuple[int, int]):
        from config import PLAYER_COLORS
        
        min_dist = float('inf')
        closest_idx = 0
        
        for i, (sx, sy) in enumerate(self.slot_positions):
            dist = math.sqrt((pos[0] - sx)**2 + (pos[1] - sy)**2)
            if dist < min_dist:
                min_dist = dist
                closest_idx = i
        
        return PLAYER_COLORS[closest_idx]