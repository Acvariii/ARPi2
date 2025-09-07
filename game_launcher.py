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
HOVER_TIME_THRESHOLD = 0.8  # seconds required to trigger a hover "click"
TOGGLE_COOLDOWN = 1.0      # cooldown after toggling a slot

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
        # fingertip_points: list of (x,y)
        mouse_near = any(self.rect.collidepoint(p) for p in fingertip_points)
        color = BUTTON_HOVER if mouse_near else BUTTON_COLOR

        # shadow
        shadow = (0, 0, 0, 60)
        shadow_rect = self.rect.move(4, 6)
        pygame.draw.rect(surf, (10, 10, 10), shadow_rect, border_radius=self.radius)

        pygame.draw.rect(surf, color, self.rect, border_radius=self.radius)
        txt = self.font.render(self.text, True, WHITE)
        surf.blit(txt, txt.get_rect(center=self.rect.center))

        # handle hover timers per fingertip (using coords as keys)
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
        self.hover_start = {}      # (slot_idx, fingertip_key) -> timestamp
        self.toggle_cooldown = {}  # slot_idx -> last_toggle_time

    def calculate_positions(self, size):
        # place 3 top, 3 bottom, left middle, right middle on full-screen table edges
        w, h = size
        positions = []
        margin_x = int(w * 0.08)
        margin_y = int(h * 0.06)
        # top 3
        top_y = margin_y
        for i in range(3):
            x = int(margin_x + (i + 1) * (w - 2 * margin_x) / 4)
            positions.append((x, top_y))
        # bottom 3
        bot_y = h - margin_y
        for i in range(3):
            x = int(margin_x + (i + 1) * (w - 2 * margin_x) / 4)
            positions.append((x, bot_y))
        # left middle
        positions.append((margin_x, int(h / 2)))
        # right middle
        positions.append((w - margin_x, int(h / 2)))
        return positions

    def slot_rect(self, idx):
        # full-space slots: make them larger, hugging the edges
        w, h = self.screen.get_size()
        base = int(min(w, h) * 0.18)  # dynamic size
        x, y = self.positions[idx]
        # enlarge along edge if on top/bottom
        if y < h * 0.2 or y > h * 0.8:
            rect = pygame.Rect(x - base, y - base//2, base*2, base)
        else:
            rect = pygame.Rect(x - base//2, y - base, base, base*2)
        return rect

    def update_with_fingertips(self, fingertip_points):
        now = time.time()
        for idx in range(len(self.positions)):
            rect = self.slot_rect(idx)
            # collect whether any fingertip is inside
            inside = [p for p in fingertip_points if rect.collidepoint(p)]
            if inside:
                # use a simple key per fingertip coordinate
                for p in inside:
                    key = f"{idx}:{p[0]}_{p[1]}"
                    if key not in self.hover_start:
                        self.hover_start[key] = now
                    elif now - self.hover_start[key] >= HOVER_TIME_THRESHOLD:
                        last = self.toggle_cooldown.get(idx, 0)
                        if now - last >= TOGGLE_COOLDOWN:
                            # toggle selection (allow deselect)
                            self.selected[idx] = not self.selected[idx]
                            self.toggle_cooldown[idx] = now
                            # clear any hover entries for this slot to avoid immediate re-toggle
                            self.hover_start = {k: v for k, v in self.hover_start.items() if not k.startswith(f"{idx}:")}
            else:
                # remove hover entries for this slot
                self.hover_start = {k: v for k, v in self.hover_start.items() if not k.startswith(f"{idx}:")}

    def draw(self):
        # draw full-screen table / panel
        w, h = self.screen.get_size()
        table_rect = pygame.Rect(0, 0, w, h)
        pygame.draw.rect(self.screen, (20, 80, 30), table_rect)  # richer green

        # interior slightly darker panel for clarity
        inner = table_rect.inflate(-int(w * 0.06), -int(h * 0.06))
        pygame.draw.rect(self.screen, (32, 96, 36), inner, border_radius=12)

        # draw player slots
        for idx, pos in enumerate(self.positions):
            rect = self.slot_rect(idx)
            sel = self.selected[idx]
            color = PLAYER_COLORS[idx]
            # selected slots are bright and raised
            if sel:
                pygame.draw.rect(self.screen, color, rect.inflate(6, 6), border_radius=10)
                pygame.draw.rect(self.screen, color, rect, border_radius=8)
                # highlight border
                pygame.draw.rect(self.screen, ACCENT, rect, width=4, border_radius=8)
            else:
                # unselected darker
                bg = tuple(max(12, c//4) for c in color)
                pygame.draw.rect(self.screen, bg, rect, border_radius=8)
                pygame.draw.rect(self.screen, (20,20,20), rect, width=2, border_radius=8)

            # index label on slot
            font = pygame.font.SysFont(None, 28)
            label = font.render(f"P{idx+1}", True, WHITE)
            self.screen.blit(label, label.get_rect(center=rect.center))

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
    pygame.mouse.set_visible(False)  # hide real mouse for projection UI
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
                fingertip_meta.append({"pos": (sx, sy), "hand": hand_id, "name": name})

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # ---- draw UI first ----
        screen.fill(DARK_BG)

        if state == "menu":
            # nice backdrop panel
            panel = pygame.Rect(80, 60, WINDOW_SIZE[0] - 160, WINDOW_SIZE[1] - 120)
            pygame.draw.rect(screen, PANEL, panel, border_radius=14)
            # headline
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
            # Update selection logic (hover -> toggle)
            selection.update_with_fingertips(fingertip_points)
            # Draw selection table and slots (fills entire screen)
            selection.draw()

            # draw central start button (use fingertip hover)
            start_btn.draw(screen, fingertip_points)
            # only allow start if >= min players
            selected_count = sum(selection.selected)
            # small helper label under the button
            label_small = pygame.font.SysFont(None, 26).render(f"{selected_count} players selected", True, WHITE)
            screen.blit(label_small, (start_btn.rect.centerx - label_small.get_width()//2, start_btn.rect.bottom + 8))
            if start_btn.clicked and selected_count >= selection.min_players:
                print("Starting Monopoly with players:", selected_count)
                start_btn.reset()

        else:
            # placeholder for other game screens
            panel = pygame.Rect(80, 60, WINDOW_SIZE[0] - 160, WINDOW_SIZE[1] - 120)
            pygame.draw.rect(screen, PANEL, panel, border_radius=14)
            txt = font.render("Game screen (not implemented)", True, WHITE)
            screen.blit(txt, txt.get_rect(center=(WINDOW_SIZE[0] // 2, WINDOW_SIZE[1] // 2)))

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
            # don't display finger name per request

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

if __name__ == "__main__":
    run_pygame()