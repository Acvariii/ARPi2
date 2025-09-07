import asyncio
import json
import math
import threading
import time
import pygame
import websockets

# CONFIG
SERVER_WS = "ws://192.168.1.79:8765"
WINDOW_SIZE = (1280, 720)
FPS = 60
HOVER_TIME_THRESHOLD = 0.9  # seconds required to trigger a hover "click"
TOGGLE_COOLDOWN = 0.8       # cooldown after toggling a slot

# Colors
WHITE = (255, 255, 255)
GRAY = (30, 30, 30)
DARK_BG = (18, 18, 28)
PANEL = (24, 24, 34)
BUTTON_COLOR = (60, 120, 200)
BUTTON_HOVER = (100, 180, 250)
ACCENT = (240, 200, 80)
PLAYER_COLORS = [
    (255, 77, 77),
    (77, 255, 77),
    (77, 77, 255),
    (255, 200, 77),
    (200, 77, 255),
    (77, 255, 200),
    (255, 120, 120),
    (180, 180, 80),
]

# Global shared state populated by websocket receiver
shared_hands = {"hands": [], "ts": 0.0}
shared_lock = threading.Lock()

# WebSocket client running in separate thread
def start_ws_receiver():
    async def recv_loop():
        async with websockets.connect(SERVER_WS, max_size=None) as ws:
            await ws.send("viewer")
            async for msg in ws:
                try:
                    data = json.loads(msg)
                    if data.get("type") == "hands":
                        with shared_lock:
                            shared_hands["hands"] = data.get("hands", [])
                            shared_hands["w"] = data.get("width")
                            shared_hands["h"] = data.get("height")
                            shared_hands["ts"] = time.time()
                except Exception:
                    pass

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(recv_loop())

# Button UI element with hover detection by fingertip points
class HoverButton:
    def __init__(self, rect, text, font, radius=12):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font
        self.hover_start = {}
        self.clicked = False
        self.radius = radius

    def draw(self, surf, fingertip_points):
        mouse_near = any(self.rect.collidepoint(p) for p in fingertip_points)
        color = BUTTON_HOVER if mouse_near else BUTTON_COLOR

        # shadow
        shadow_rect = self.rect.move(4, 6)
        pygame.draw.rect(surf, (10, 10, 10), shadow_rect, border_radius=self.radius)

        pygame.draw.rect(surf, color, self.rect, border_radius=self.radius)
        txt = self.font.render(self.text, True, WHITE)
        surf.blit(txt, txt.get_rect(center=self.rect.center))

        now = time.time()
        for p in fingertip_points:
            key = f"{p[0]}_{p[1]}"
            if self.rect.collidepoint(p):
                if key not in self.hover_start:
                    self.hover_start[key] = now
                elif (now - self.hover_start[key]) >= HOVER_TIME_THRESHOLD:
                    self.clicked = True
            else:
                self.hover_start.pop(key, None)

    def reset(self):
        self.clicked = False
        self.hover_start.clear()

# Player selection screen
class PlayerSelection:
    def __init__(self, screen):
        self.screen = screen
        self.selected = [False] * 8
        self.positions = self.calculate_positions(screen.get_size())
        self.min_players = 2
        self.max_players = 8
        # hover keyed by (slot_idx, hand_id) so progress follows the same hand as it moves.
        self.hover_start = {}      # key -> start_time, key format: "{idx}:{hand_id}"
        self.hover_pos = {}        # key -> last (x,y) of that hand while hovering that slot
        self.toggle_cooldown = {}  # slot_idx -> last_toggle_time

    def calculate_positions(self, size):
        # 3 top, 3 bottom, left middle, right middle
        w, h = size
        positions = []
        # top three (x locations)
        for i in range(3):
            x = int((i + 0.5) * (w / 3))
            positions.append((x, 0))
        # bottom three
        for i in range(3):
            x = int((i + 0.5) * (w / 3))
            positions.append((x, h))
        # left middle, right middle
        positions.append((0, int(h / 2)))
        positions.append((w, int(h / 2)))
        return positions

    def slot_rect(self, idx):
        # Top/bottom: wide, short. Sides: FILL remaining vertical space between top and bottom, same dimension family.
        w, h = self.screen.get_size()
        # top/bottom sizes
        top_slot_w = int(w / 3)      # each top/bottom slot spans 1/3 width
        top_slot_h = int(h * 0.18)   # short height
        # side slots: take remaining vertical space between top and bottom slots
        vertical_margin = int(h * 0.04)
        side_slot_h = max(80, h - (2 * top_slot_h) - vertical_margin)  # fill rest
        side_slot_w = int(w * 0.14)  # keep reasonable width for side players

        x, y = self.positions[idx]
        # top row (y==0)
        if y == 0:
            rect = pygame.Rect(x - top_slot_w // 2, 0, top_slot_w, top_slot_h)
        # bottom row (y==h)
        elif y == h:
            rect = pygame.Rect(x - top_slot_w // 2, h - top_slot_h, top_slot_w, top_slot_h)
        # left side (x==0) - tall vertical rect hugging left edge, now fills gap
        elif x == 0:
            rect = pygame.Rect(0, int(top_slot_h + vertical_margin // 2), side_slot_w, side_slot_h)
        # right side (x==w) - tall vertical rect hugging right edge, now fills gap
        else:
            rect = pygame.Rect(w - side_slot_w, int(top_slot_h + vertical_margin // 2), side_slot_w, side_slot_h)
        return rect

    def update_with_fingertips(self, fingertip_meta):
        """fingertip_meta: list of {'pos':(x,y), 'hand':hand_id}
        Hover keys use (slot_idx, hand_id) so progress follows the same hand.
        """
        now = time.time()
        # build mapping from slot_idx -> list of (hand_id, pos)
        slot_hits = {i: [] for i in range(len(self.positions))}
        for meta in fingertip_meta:
            px, py = meta["pos"]
            hand = meta.get("hand", 0)
            for idx in range(len(self.positions)):
                rect = self.slot_rect(idx)
                if rect.collidepoint((px, py)):
                    slot_hits[idx].append((hand, (px, py)))

        # update hover timers/positions per (slot,hand)
        active_keys = set()
        for idx, hits in slot_hits.items():
            if hits:
                for hand, pos in hits:
                    key = f"{idx}:{hand}"
                    active_keys.add(key)
                    if key not in self.hover_start:
                        self.hover_start[key] = now
                        self.hover_pos[key] = pos
                    else:
                        # update last position so the progress indicator follows
                        self.hover_pos[key] = pos
                        progress = (now - self.hover_start[key]) / HOVER_TIME_THRESHOLD
                        if progress >= 1.0:
                            last = self.toggle_cooldown.get(idx, 0)
                            if now - last >= TOGGLE_COOLDOWN:
                                # toggle selection (allow deselect)
                                self.selected[idx] = not self.selected[idx]
                                self.toggle_cooldown[idx] = now
                                # clear hover entries for this slot to avoid immediate re-trigger
                                self.hover_start = {k: v for k, v in self.hover_start.items() if not k.startswith(f"{idx}:")}
                                self.hover_pos = {k: v for k, v in self.hover_pos.items() if not k.startswith(f"{idx}:")}
            else:
                pass

        # Clear hover keys that are no longer active (hand moved away)
        keys_to_remove = [k for k in self.hover_start.keys() if k not in active_keys]
        for k in keys_to_remove:
            self.hover_start.pop(k, None)
            self.hover_pos.pop(k, None)

    def get_hover_progress(self):
        """Return list of {slot, pos, progress} using hover_pos so indicator follows hand."""
        now = time.time()
        out = []
        for key, start in list(self.hover_start.items()):
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

    def draw(self):
        # draw table background filling entire screen
        w, h = self.screen.get_size()
        pygame.draw.rect(self.screen, (20, 80, 30), pygame.Rect(0, 0, w, h))

        # slight inner panel for contrast
        inner = pygame.Rect(int(w*0.02), int(h*0.02), int(w*0.96), int(h*0.96))
        pygame.draw.rect(self.screen, (32, 96, 36), inner, border_radius=12)

        # draw player slots with same dimensions, flush to edges
        font = pygame.font.SysFont(None, 30)
        for idx, pos in enumerate(self.positions):
            rect = self.slot_rect(idx)
            sel = self.selected[idx]
            color = PLAYER_COLORS[idx]
            if sel:
                pygame.draw.rect(self.screen, color, rect.inflate(6, 6), border_radius=10)
                pygame.draw.rect(self.screen, color, rect, border_radius=8)
                pygame.draw.rect(self.screen, ACCENT, rect, width=4, border_radius=8)
            else:
                bg = tuple(max(12, c//5) for c in color)
                pygame.draw.rect(self.screen, bg, rect, border_radius=8)
                pygame.draw.rect(self.screen, (18,18,18), rect, width=2, border_radius=8)

            # label rotated toward player
            label = font.render(f"P{idx+1}", True, WHITE)

            # rotation per-slot so text faces the player at that edge
            x, y = pos
            angle = 0
            # top players (y==0) should read upside-down for players standing above table
            if y == 0:
                angle = 180
            # bottom players (y==h) read normally
            elif y == h:
                angle = 0
            # left side (index 6): rotate so it faces left-side player (use 270)
            elif x == 0:
                angle = 270
            # right side (index 7): rotate so it faces right-side player (use 90)
            else:
                angle = 90

            lbl = pygame.transform.rotate(label, angle)
            lbl_rect = lbl.get_rect(center=rect.center)
            self.screen.blit(lbl, lbl_rect)

    def closest_player_color(self, point):
        min_d = 1e9
        idx_min = 0
        for i, pos in enumerate(self.positions):
            dx = pos[0] - point[0]
            dy = pos[1] - point[1]
            d = dx * dx + dy * dy
            if d < min_d:
                min_d = d
                idx_min = i
        return PLAYER_COLORS[idx_min]

def run_pygame():
    pygame.init()
    pygame.mouse.set_visible(False)  # hide physical cursor for projection UI
    screen = pygame.display.set_mode(WINDOW_SIZE)
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 48)

    # UI - main menu buttons
    btn_w, btn_h = 300, 90
    center = (WINDOW_SIZE[0] // 2, WINDOW_SIZE[1] // 2)
    btn_monopoly = HoverButton((center[0] - btn_w - 30, center[1] - btn_h // 2, btn_w, btn_h), "Monopoly", font)
    btn_blackjack = HoverButton((center[0] + 30, center[1] - btn_h // 2, btn_w, btn_h), "Blackjack", font)

    # central start button for selection screen (centered)
    start_btn = HoverButton((center[0] - 140, center[1] - 45, 280, 90), "Start", font)

    state = "menu"  # menu, monopoly_select, blackjack (not implemented)
    selection = PlayerSelection(screen)

    # start websocket receiver thread
    t = threading.Thread(target=start_ws_receiver, daemon=True)
    t.start()

    running = True
    while running:
        fingertip_points = []
        fingertip_meta = []
        # fetch latest hands
        with shared_lock:
            hands = shared_hands.get("hands", [])
        screen_w, screen_h = screen.get_size()
        for h in hands:
            hand_id = h.get("hand_id", 0)
            fps = h.get("fingertips", {})
            for name, v in fps.items():
                x, y = v[0], v[1]
                sx = int(x * screen_w)
                sy = int(y * screen_h)
                fingertip_points.append((sx, sy))
                fingertip_meta.append({"pos": (sx, sy), "hand": hand_id})

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # ---- draw UI first ----
        screen.fill(DARK_BG)

        if state == "menu":
            panel = pygame.Rect(80, 60, WINDOW_SIZE[0] - 160, WINDOW_SIZE[1] - 120)
            pygame.draw.rect(screen, PANEL, panel, border_radius=14)
            title = pygame.font.SysFont(None, 64).render("Game Launcher", True, WHITE)
            screen.blit(title, (panel.centerx - title.get_width() // 2, panel.top + 24))

            btn_monopoly.draw(screen, fingertip_points)
            btn_blackjack.draw(screen, fingertip_points)
            if btn_monopoly.clicked:
                state = "monopoly_select"
                btn_monopoly.reset()
            if btn_blackjack.clicked:
                state = "blackjack"
                btn_blackjack.reset()

        elif state == "monopoly_select":
            # Update selection logic (hover -> toggle), pass fingertip_meta so hover keys track hand IDs
            selection.update_with_fingertips(fingertip_meta)
            # Draw selection table and slots (fills entire screen)
            selection.draw()

            # draw central start button (use fingertip hover)
            start_btn.draw(screen, fingertip_points)
            # only allow start if >= min players
            selected_count = sum(selection.selected)
            label_small = pygame.font.SysFont(None, 26).render(f"{selected_count} players selected", True, WHITE)
            screen.blit(label_small, (start_btn.rect.centerx - label_small.get_width()//2, start_btn.rect.bottom + 8))
            if start_btn.clicked and selected_count >= selection.min_players:
                print("Starting Monopoly with players:", selected_count)
                start_btn.reset()

        else:
            panel = pygame.Rect(80, 60, WINDOW_SIZE[0] - 160, WINDOW_SIZE[1] - 120)
            pygame.draw.rect(screen, PANEL, panel, border_radius=14)
            txt = font.render("Game screen (not implemented)", True, WHITE)
            screen.blit(txt, txt.get_rect(center=(WINDOW_SIZE[0] // 2, WINDOW_SIZE[1] // 2)))

        # ---- render hover progress indicators above UI but below fingertips ----
        hover_list = selection.get_hover_progress()
        for h in hover_list:
            px, py = h["pos"]
            progress = h["progress"]
            # position the indicator slightly offset from fingertip to avoid overlap
            off_x, off_y = 28, -28
            arc_rect = pygame.Rect(px + off_x - 20, py + off_y - 20, 40, 40)
            start_ang = -math.pi / 2
            end_ang = start_ang + progress * 2 * math.pi
            # background ring
            pygame.draw.circle(screen, (60, 60, 60), arc_rect.center, 20)
            # progress arc
            pygame.draw.arc(screen, ACCENT, arc_rect, start_ang, end_ang, 6)

        # ---- render fingertips last so they are always on top ----
        for meta in fingertip_meta:
            px, py = meta["pos"]
            col = selection.closest_player_color((px, py))
            # outer glow
            pygame.draw.circle(screen, (255, 255, 255), (px, py), 20)
            # colored core
            pygame.draw.circle(screen, col, (px, py), 14)
            # small black center
            pygame.draw.circle(screen, (0, 0, 0), (px, py), 4)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

# expose entry for main.py to import
def run_launcher():
    run_pygame()

if __name__ == "__main__":
    run_pygame()