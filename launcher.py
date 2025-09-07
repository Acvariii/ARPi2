import asyncio
import json
import math
import threading
import time
import pygame
import websockets
from ui_components import HoverButton, draw_cursor, draw_circular_progress
from monopoly import MonopolyGame
from ui_elements import PlayerSelectionUI

# CONFIG
SERVER_WS = "ws://192.168.1.79:8765"
WINDOW_SIZE = (1920, 1080)
FPS = 60
HOVER_TIME_THRESHOLD = 0.9
TOGGLE_COOLDOWN = 0.8

# Colors
WHITE = (255, 255, 255)
DARK_BG = (18, 18, 28)
PANEL = (24, 24, 34)
ACCENT = (240, 200, 80)

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

class PlayerSelection:
    """Wrapper that uses PlayerSelectionUI for visuals and hover toggling."""
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.ui = PlayerSelectionUI(screen)

    def update_with_fingertips(self, fingertip_meta):
        self.ui.update_with_fingertips(fingertip_meta)

    def draw(self):
        self.ui.draw_slots()

    def get_hover_progress(self):
        return self.ui.get_hover_progress()

    def closest_player_color(self, point):
        return self.ui.closest_player_color(point)

    @property
    def selected(self):
        return self.ui.selected

def run_pygame():
    pygame.init()
    pygame.mouse.set_visible(False)
    screen = pygame.display.set_mode((1920, 1080), pygame.FULLSCREEN | pygame.NOFRAME)
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, max(32, int(WINDOW_SIZE[1]*0.05)))

    # selection UI instance (used in both selection and in-game for cursors/progress)
    selection = PlayerSelection(screen)

    # Game selection screen
    games = ["Monopoly"]
    buttons = []
    for i, game in enumerate(games):
        btn_rect = pygame.Rect(WINDOW_SIZE[0]//2 - 150, WINDOW_SIZE[1]//2 - 60 + i*120, 300, 90)
        buttons.append(HoverButton(btn_rect, game, font))

    state = "menu"
    selected_game = None
    current_game = None

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

        screen.fill(DARK_BG)

        # --- Game Selection Screen ---
        if state == "menu":
            panel = pygame.Rect(80, 60, WINDOW_SIZE[0] - 160, WINDOW_SIZE[1] - 120)
            pygame.draw.rect(screen, PANEL, panel, border_radius=14)
            title = pygame.font.SysFont(None, 64).render("Game Launcher", True, WHITE)
            screen.blit(title, (panel.centerx - title.get_width() // 2, panel.top + 24))

            # Draw buttons and track hover progress
            for btn in buttons:
                btn.draw(screen, fingertip_meta)
                # Draw circular progress for any hovered button
                for meta in fingertip_meta:
                    pos = meta.get("pos")
                    hand = meta.get("hand")
                    name = meta.get("name", "")
                    key = f"{hand}:{name}" if hand is not None else f"coord:{pos[0]}_{pos[1]}"
                    if pos and btn.rect.collidepoint(pos):
                        start = btn.hover_start.get(key)
                        if start:
                            elapsed = time.time() - start
                            progress = min(1.0, max(0.0, elapsed / HOVER_TIME_THRESHOLD))
                            off_x, off_y = 28, -28
                            draw_circular_progress(screen, (pos[0]+off_x, pos[1]+off_y), 20, progress, ACCENT, thickness=6)
                if btn.clicked:
                    selected_game = btn.text
                    state = "player_select"
                    btn.reset()

        # --- Player Selection Screen ---
        elif state == "player_select":
            # update and draw selection UI
            selection.update_with_fingertips(fingertip_meta)
            selection.draw()

            # Draw hover progress for player slots
            for h in selection.get_hover_progress():
                px, py = h["pos"]
                progress = h["progress"]
                off_x, off_y = 28, -28
                draw_circular_progress(screen, (px+off_x, py+off_y), 20, progress, ACCENT, thickness=6)

            # Start button logic
            start_btn = HoverButton(pygame.Rect(WINDOW_SIZE[0]//2-140, WINDOW_SIZE[1]//2-45, 280, 90), "Start", font)
            start_btn.draw(screen, fingertip_meta, enabled=sum(selection.selected) >= 2)
            # Draw circular progress for start button
            for meta in fingertip_meta:
                pos = meta.get("pos")
                hand = meta.get("hand")
                name = meta.get("name", "")
                key = f"{hand}:{name}" if hand is not None else f"coord:{pos[0]}_{pos[1]}"
                if pos and start_btn.rect.collidepoint(pos):
                    start = start_btn.hover_start.get(key)
                    if start:
                        elapsed = time.time() - start
                        progress = min(1.0, max(0.0, elapsed / HOVER_TIME_THRESHOLD))
                        off_x, off_y = 28, -28
                        draw_circular_progress(screen, (pos[0]+off_x, pos[1]+off_y), 20, progress, ACCENT, thickness=6)

            selected_count = sum(selection.selected)
            label_small = pygame.font.SysFont(None, 26).render(f"{selected_count} players selected", True, WHITE)
            screen.blit(label_small, (start_btn.rect.centerx - label_small.get_width()//2, start_btn.rect.bottom + 8))
            label_min_players = pygame.font.SysFont(None, 28).render("Minimum 2 players to start", True, WHITE)
            screen.blit(label_min_players, (start_btn.rect.centerx - label_min_players.get_width()//2, start_btn.rect.top - 30))

            # Only start game if button is clicked and enough players selected
            if start_btn.clicked and selected_count >= 2:
                print("Starting Monopoly with players:", selected_count)
                selected_indices = [i for i, s in enumerate(selection.selected) if s]
                current_game = MonopolyGame(screen, lambda w, h: fingertip_meta)
                # Set selected players in both the game and its selection UI
                current_game.players_selected = selected_indices
                for i in range(8):
                    current_game.selection_ui.selected[i] = (i in selected_indices)
                # Set current to first selected player
                current_game.current = selected_indices[0] if selected_indices else 0
                state = "monopoly_playing"
                start_btn.reset()

        # --- Monopoly Game Screen ---
        elif state == "monopoly_playing":
            if current_game is not None:
                current_game.update(fingertip_meta)
                current_game.draw()
            else:
                panel = pygame.Rect(80, 60, WINDOW_SIZE[0] - 160, WINDOW_SIZE[1] - 120)
                pygame.draw.rect(screen, PANEL, panel, border_radius=14)
                txt = font.render("Monopoly (initializing...)", True, WHITE)
                screen.blit(txt, txt.get_rect(center=(WINDOW_SIZE[0] // 2, WINDOW_SIZE[1] // 2)))

        # Draw cursors for each hand
        for meta in fingertip_meta:
            px, py = meta["pos"]
            col = selection.closest_player_color((px, py))
            draw_cursor(screen, (px, py), col)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

if __name__ == "__main__":
    run_pygame()