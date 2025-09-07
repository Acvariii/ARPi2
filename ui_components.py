import pygame
import time
from typing import Tuple, List, Dict

HOVER_TIME_THRESHOLD = 0.9

def draw_circular_progress(surf, center, radius, progress, color=(240,200,80), bg=(60,60,60), thickness=6):
    pygame.draw.circle(surf, bg, center, radius)
    start_ang = -3.14159 / 2
    end_ang = start_ang + progress * 2 * 3.14159
    rect = pygame.Rect(center[0]-radius, center[1]-radius, radius*2, radius*2)
    pygame.draw.arc(surf, color, rect, start_ang, end_ang, thickness)

class HoverButton:
    def __init__(self, rect, text, font, radius=12):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font
        self.hover_start = {}
        self.clicked = False
        self.radius = radius

    def draw(self, surf, fingertip_meta, enabled=True):
        mouse_near = False
        now = time.time()
        active_keys = set()
        for meta in fingertip_meta:
            pos = meta.get("pos")
            if pos and self.rect.collidepoint(pos):
                mouse_near = True
                hand = meta.get("hand")
                name = meta.get("name", "")
                key = f"{hand}:{name}" if hand is not None else f"coord:{pos[0]}_{pos[1]}"
                active_keys.add(key)
                if key not in self.hover_start:
                    self.hover_start[key] = now
                else:
                    if (now - self.hover_start[key]) >= HOVER_TIME_THRESHOLD:
                        self.clicked = True
            else:
                # Remove hover timer for this key if not colliding
                hand = meta.get("hand")
                name = meta.get("name", "")
                key = f"{hand}:{name}" if hand is not None else f"coord:{pos[0]}_{pos[1]}"
                self.hover_start.pop(key, None)
        # Remove stale keys
        for k in list(self.hover_start.keys()):
            if k not in active_keys:
                self.hover_start.pop(k, None)
        color = (100,180,250) if mouse_near and enabled else (60,120,200)
        txt_color = (255,255,255) if enabled else (160,160,160)
        shadow_rect = self.rect.move(4, 6)
        pygame.draw.rect(surf, (10,10,10), shadow_rect, border_radius=self.radius)
        pygame.draw.rect(surf, color, self.rect, border_radius=self.radius)
        txt = self.font.render(self.text, True, txt_color)
        surf.blit(txt, txt.get_rect(center=self.rect.center))

    def reset(self):
        self.clicked = False
        self.hover_start.clear()

def draw_cursor(surf, pos, color):
    pygame.draw.circle(surf, (255,255,255), pos, 20)
    pygame.draw.circle(surf, color, pos, 14)
    pygame.draw.circle(surf, (0,0,0), pos, 4)

def get_closest_player_color(pos, player_panels):
    min_dist = float('inf')
    closest_color = (200,200,200)
    for panel in player_panels:
        cx, cy = panel['rect'].center
        dist = (cx-pos[0])**2 + (cy-pos[1])**2
        if dist < min_dist:
            min_dist = dist
            closest_color = panel['color']
    return closest_color