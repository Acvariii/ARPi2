import asyncio
import json
import math
import threading
import time
import pygame
import websockets

# CONFIG
SERVER_WS = "ws://192.168.1.79:8765"  # <-- replace SERVER_IP with your Windows machine IP
WINDOW_SIZE = (1280, 720)
FPS = 60
HOVER_TIME_THRESHOLD = 0.8  # seconds required to trigger a hover "click"

# Colors
WHITE = (255, 255, 255)
GRAY = (30, 30, 30)
BUTTON_COLOR = (60, 120, 200)
BUTTON_HOVER = (100, 180, 250)
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

# Utility: normalized -> screen coords
def norm_to_screen(x, y, screen_w, screen_h):
    return int(x * screen_w), int(y * screen_h)

# Button UI element with hover detection by fingertip points
class HoverButton:
    def __init__(self, rect, text, font):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font
        self.hover_start = {}
        self.clicked = False

    def draw(self, surf, fingertip_points):
        # fingertip_points: list of (x,y)
        mouse_near = any(self.rect.collidepoint(p) for p in fingertip_points)
        color = BUTTON_HOVER if mouse_near else BUTTON_COLOR
        pygame.draw.rect(surf, color, self.rect, border_radius=8)
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

    def calculate_positions(self, size):
        w, h = size
        positions = []
        # top 3
        top_y = int(h * 0.08)
        for i in range(3):
            x = int((i + 1) * w / 4)
            positions.append((x, top_y))
        # bottom 3
        bot_y = int(h * 0.92)
        for i in range(3):
            x = int((i + 1) * w / 4)
            positions.append((x, bot_y))
        # left middle
        positions.append((int(w * 0.06), int(h / 2)))
        # right middle
        positions.append((int(w * 0.94), int(h / 2)))
        return positions

    def draw(self, fingertip_points):
        # draw table
        w, h = self.screen.get_size()
        table_rect = pygame.Rect(int(w*0.12), int(h*0.12), int(w*0.76), int(h*0.76))
        pygame.draw.rect(self.screen, (34,139,34), table_rect)  # green table

        # draw player slots
        for idx, pos in enumerate(self.positions):
            color = PLAYER_COLORS[idx]
            sel = self.selected[idx]
            radius = 40
            rect = pygame.Rect(pos[0]-radius, pos[1]-radius, radius*2, radius*2)
            pygame.draw.rect(self.screen, color if sel else (80,80,80), rect, border_radius=8)
            # label
            font = pygame.font.SysFont(None, 24)
            label = font.render(f"P{idx+1}", True, WHITE)
            self.screen.blit(label, label.get_rect(center=rect.center))

            # check hover selection by fingertips
            for p in fingertip_points:
                if rect.collidepoint(p):
                    # toggle selection after hover threshold handled by caller
                    self.selected[idx] = True

    def closest_player_color(self, point):
        # return color of nearest player slot to point
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
    screen = pygame.display.set_mode(WINDOW_SIZE)
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 48)

    # UI
    btn_w, btn_h = 280, 80
    center = (WINDOW_SIZE[0]//2, WINDOW_SIZE[1]//2)
    btn_monopoly = HoverButton((center[0]-btn_w-20, center[1]-btn_h//2, btn_w, btn_h), "Monopoly", font)
    btn_blackjack = HoverButton((center[0]+20, center[1]-btn_h//2, btn_w, btn_h), "Blackjack", font)

    state = "menu"  # menu, monopoly_select, blackjack (not implemented)
    selection = PlayerSelection(screen)

    # start websocket receiver thread
    t = threading.Thread(target=start_ws_receiver, daemon=True)
    t.start()

    running = True
    while running:
        fingertip_points = []
        # fetch latest hands
        with shared_lock:
            hands = shared_hands.get("hands", [])
            sw = shared_hands.get("w", WINDOW_SIZE[0])
            sh = shared_hands.get("h", WINDOW_SIZE[1])
        for h in hands:
            # fingertips are in hand['fingertips'] with normalized coords
            fps = h.get("fingertips", {})
            for k, v in fps.items():
                x, y = v[0], v[1]
                sx = int(x * WINDOW_SIZE[0])
                sy = int(y * WINDOW_SIZE[1])
                fingertip_points.append((sx, sy))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        screen.fill(GRAY)

        # draw fingertips
        for p in fingertip_points:
            pygame.draw.circle(screen, (255,255,255), p, 8)
            pygame.draw.circle(screen, (0,0,0), p, 4)

        if state == "menu":
            btn_monopoly.draw(screen, fingertip_points)
            btn_blackjack.draw(screen, fingertip_points)
            if btn_monopoly.clicked:
                state = "monopoly_select"
                btn_monopoly.reset()
            if btn_blackjack.clicked:
                state = "blackjack"  # placeholder: implement blackjack view
                btn_blackjack.reset()
        elif state == "monopoly_select":
            # Draw UI for selection
            selection.draw(fingertip_points)

            # color fingertips based on nearest player
            for p in fingertip_points:
                col = selection.closest_player_color(p)
                pygame.draw.circle(screen, col, p, 10)

            # draw status and start button
            font_small = pygame.font.SysFont(None, 28)
            selected_count = sum(selection.selected)
            status = font_small.render(f"Players selected: {selected_count} (min {selection.min_players})", True, WHITE)
            screen.blit(status, (20, 20))
            # simple start button
            start_btn = HoverButton((WINDOW_SIZE[0]-200, 20, 180, 50), "Start", font_small)
            start_btn.draw(screen, fingertip_points)
            if start_btn.clicked and selected_count >= selection.min_players:
                print("Starting Monopoly with players:", selected_count)
                # Here you'd launch the actual game app
                start_btn.reset()
        else:
            # placeholder for blackjack or other states
            txt = font.render("Game screen (not implemented)", True, WHITE)
            screen.blit(txt, txt.get_rect(center=(WINDOW_SIZE[0]//2, WINDOW_SIZE[1]//2)))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

if __name__ == "__main__":
    run_pygame()