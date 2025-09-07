import time
import pygame
from typing import List, Tuple, Dict
from ui_components import draw_cursor, get_closest_player_color

HOVER_TIME_THRESHOLD = 0.9

PLAYER_COLORS = [
    (220,  40,  40),   # vivid red
    (40, 220,  40),    # vivid green
    (40,  70, 220),    # vivid blue
    (255, 200,  60),   # warm yellow
    (200,  40, 200),   # magenta
    (40, 220, 200),    # teal
    (255, 120,  60),   # orange
    (140,  40, 220),   # purple
]


class HoverButton:
    def __init__(self, rect: Tuple[int, int, int, int], text: str, font: pygame.font.Font, radius: int = 12):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font
        self.hover_start: Dict[str, float] = {}
        self.clicked = False
        self.radius = radius

    def draw(self, surf: pygame.Surface, fingertip_meta: List[Dict], enabled: bool = True):
        """
        Draw the button and handle hover by hand identity.
        - fingertip_meta: list of dicts containing at least {'pos': (x,y), 'hand': id, 'name': str}
        - enabled: when False, the button is shown disabled and hover timers are cleared
        Hover state is keyed by '{hand}:{name}' if available, otherwise by hand id only.
        """
        # compute whether any fingertip is inside the rect (for visuals)
        mouse_near = False
        for m in fingertip_meta:
            pos = m.get("pos")
            if pos and self.rect.collidepoint(pos):
                mouse_near = True
                break

        if not enabled:
            color = (80, 80, 80)
            txt_color = (160, 160, 160)
        else:
            color = (100, 180, 250) if mouse_near else (60, 120, 200)
            txt_color = (255, 255, 255)

        # drop shadow + background
        shadow_rect = self.rect.move(4, 6)
        pygame.draw.rect(surf, (10, 10, 10), shadow_rect, border_radius=self.radius)
        pygame.draw.rect(surf, color, self.rect, border_radius=self.radius)
        txt = self.font.render(self.text, True, txt_color)
        surf.blit(txt, txt.get_rect(center=self.rect.center))

        # don't track hover timers while disabled
        if not enabled:
            self.hover_start.clear()
            return

        now = time.time()
        active_keys = set()
        for m in fingertip_meta:
            pos = m.get("pos")
            if not pos:
                continue
            if not self.rect.collidepoint(pos):
                continue
            hand = m.get("hand", None)
            name = m.get("name", "")
            key = f"{hand}:{name}" if hand is not None else f"coord:{pos[0]}_{pos[1]}"
            active_keys.add(key)
            if key not in self.hover_start:
                self.hover_start[key] = now
            else:
                if (now - self.hover_start[key]) >= HOVER_TIME_THRESHOLD:
                    self.clicked = True

        # remove stale hover keys (fingers moved away)
        for k in list(self.hover_start.keys()):
            if k not in active_keys:
                self.hover_start.pop(k, None)

    def reset(self):
        self.clicked = False
        self.hover_start.clear()


class PlayerSelectionUI:
    """Provides slots on table edges for 8 players and hover progress helpers."""

    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.positions = self._calculate_positions(screen.get_size())
        self.selected = [False] * 8
        # hover keyed by (slot_idx, hand_id)
        self.hover_start: Dict[str, float] = {}
        self.hover_pos: Dict[str, Tuple[int, int]] = {}
        self.toggle_cooldown: Dict[int, float] = {}
        self.min_players = 2  # minimum players required to start

    def _calculate_positions(self, size: Tuple[int, int]) -> List[Tuple[int, int]]:
        w, h = size
        positions = []
        # top 3
        for i in range(3):
            positions.append((int((i + 0.5) * (w / 3)), 0))
        # bottom 3
        for i in range(3):
            positions.append((int((i + 0.5) * (w / 3)), h))
        # left middle, right middle
        positions.append((0, int(h / 2)))
        positions.append((w, int(h / 2)))
        return positions

    def slot_rect(self, idx: int) -> pygame.Rect:
        w, h = self.screen.get_size()
        # reduce top/bottom slot height so slots don't dominate the screen at 1080p
        top_slot_w = int(w / 3)
        top_slot_h = int(h * 0.10)
        vertical_margin = int(h * 0.04)
        side_slot_h = max(80, h - (2 * top_slot_h) - vertical_margin)
        side_slot_w = int(w * 0.12)

        x, y = self.positions[idx]
        if y == 0:
            return pygame.Rect(x - top_slot_w // 2, 0, top_slot_w, top_slot_h)
        if y == h:
            return pygame.Rect(x - top_slot_w // 2, h - top_slot_h, top_slot_w, top_slot_h)
        if x == 0:
            return pygame.Rect(0, int(top_slot_h + vertical_margin // 2), side_slot_w, side_slot_h)
        return pygame.Rect(w - side_slot_w, int(top_slot_h + vertical_margin // 2), side_slot_w, side_slot_h)

    def update_with_fingertips(self, fingertip_meta: List[Dict]):
        """Track hover progress keyed by (slot,hand) and toggle selected on completion."""
        now = time.time()
        slot_hits = {i: [] for i in range(len(self.positions))}
        for meta in fingertip_meta:
            px, py = meta["pos"]
            hand = meta.get("hand", 0)
            for idx in range(len(self.positions)):
                rect = self.slot_rect(idx)
                if rect.collidepoint((px, py)):
                    slot_hits[idx].append((hand, (px, py)))

        active_keys = set()
        for idx, hits in slot_hits.items():
            if not hits:
                continue
            for hand, pos in hits:
                key = f"{idx}:{hand}"
                active_keys.add(key)
                if key not in self.hover_start:
                    self.hover_start[key] = now
                    self.hover_pos[key] = pos
                else:
                    self.hover_pos[key] = pos
                    progress = (now - self.hover_start[key]) / HOVER_TIME_THRESHOLD
                    if progress >= 1.0:
                        last = self.toggle_cooldown.get(idx, 0)
                        if now - last >= 0.8:
                            self.selected[idx] = not self.selected[idx]
                            self.toggle_cooldown[idx] = now
                            # clear hover entries for this slot
                            self.hover_start = {k: v for k, v in self.hover_start.items() if not k.startswith(f"{idx}:")}
                            self.hover_pos = {k: v for k, v in self.hover_pos.items() if not k.startswith(f"{idx}:")}

        # remove stale keys
        stale = [k for k in list(self.hover_start.keys()) if k not in active_keys]
        for k in stale:
            self.hover_start.pop(k, None)
            self.hover_pos.pop(k, None)

    def get_hover_progress(self) -> List[Dict]:
        now = time.time()
        out = []
        for key, start in self.hover_start.items():
            try:
                idx_str, hand_str = key.split(":")
                idx = int(idx_str)
                pos = self.hover_pos.get(key)
                if not pos:
                    continue
                progress = min(1.0, max(0.0, (now - start) / HOVER_TIME_THRESHOLD))
                out.append({"slot": idx, "pos": pos, "progress": progress})
            except Exception:
                continue
        return out

    def draw_slots(self):
        # full table background; caller can choose to draw individual slots instead
        w, h = self.screen.get_size()
        inner = pygame.Rect(int(w*0.02), int(h*0.02), int(w*0.96), int(h*0.96))
        pygame.draw.rect(self.screen, (32, 96, 36), inner, border_radius=12)
        # draw all slots by delegating to draw_slot (keeps single-slot draw available)
        for idx in range(len(self.positions)):
            self.draw_slot(idx)

    def draw_slot(self, idx: int, force_selected: bool = None):
        """Draw a single player slot. If force_selected is provided it overrides self.selected[idx]."""
        w, h = self.screen.get_size()
        # font size scales with screen height to remain legible at 720p/1080p
        font = pygame.font.SysFont(None, max(14, int(h * 0.025)))
        pos = self.positions[idx]
        rect = self.slot_rect(idx)
        sel = self.selected[idx] if force_selected is None else force_selected
        color = PLAYER_COLORS[idx]
        if sel:
            pygame.draw.rect(self.screen, color, rect.inflate(6, 6), border_radius=10)
            pygame.draw.rect(self.screen, color, rect, border_radius=8)
        else:
            bg = tuple(max(12, c//5) for c in color)
            pygame.draw.rect(self.screen, bg, rect, border_radius=8)
            pygame.draw.rect(self.screen, (18,18,18), rect, width=2, border_radius=8)
        label = font.render(f"P{idx+1}", True, (255,255,255))
        # rotate label for orientation
        x,y = pos
        angle = 0
        if y == 0: angle = 180
        elif y == h: angle = 0
        elif x == 0: angle = 270
        else: angle = 90
        lbl = pygame.transform.rotate(label, angle)
        self.screen.blit(lbl, lbl.get_rect(center=rect.center))

    def closest_player_color(self, point: Tuple[int, int]):
        """
        Return the nearest player's color for the provided screen point.
        Used by the launcher to color fingertip cursors.
        """
        min_d = float("inf")
        idx_min = 0
        for i in range(len(self.positions)):
            rect = self.slot_rect(i)
            cx, cy = rect.center
            dx = cx - point[0]
            dy = cy - point[1]
            d = dx*dx + dy*dy
            if d < min_d:
                min_d = d
                idx_min = i
        return PLAYER_COLORS[idx_min]

    def selected_count(self) -> int:
        """Return number of currently selected players."""
        return sum(1 for s in self.selected if s)

class PlayerPanel:
    def __init__(self, idx, rect, color, orientation):
        self.idx = idx
        self.rect = rect
        self.color = color
        self.orientation = orientation  # 0=normal, 90=right, 180=upside-down, 270=left

def get_player_panels(screen_size):
    w, h = screen_size
    panels = []
    # Top 3
    for i in range(3):
        x = int((i + 0.5) * (w / 3))
        rect = pygame.Rect(x - w//6, 0, w//3, int(h*0.10))
        panels.append(PlayerPanel(i, rect, PLAYER_COLORS[i], 180))
    # Bottom 3
    for i in range(3):
        x = int((i + 0.5) * (w / 3))
        rect = pygame.Rect(x - w//6, h-int(h*0.10), w//3, int(h*0.10))
        panels.append(PlayerPanel(i+3, rect, PLAYER_COLORS[i+3], 0))
    # Left
    rect = pygame.Rect(0, int(h*0.10), int(w*0.12), h-int(h*0.20))
    panels.append(PlayerPanel(6, rect, PLAYER_COLORS[6], 270))
    # Right
    rect = pygame.Rect(w-int(w*0.12), int(h*0.10), int(w*0.12), h-int(h*0.20))
    panels.append(PlayerPanel(7, rect, PLAYER_COLORS[7], 90))
    return panels