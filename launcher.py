import asyncio
import json
import math
import threading
import time
import pygame
from typing import List, Dict
from ui_components import HoverButton, draw_cursor, draw_circular_progress
from ui_elements import PlayerSelectionUI
from monopoly import MonopolyGame
from hand_tracking import HandTracker

# CONFIG
SERVER_WS = "ws://192.168.1.79:8765"
WINDOW_SIZE = (1920, 1080)
FPS = 60
HOVER_TIME_THRESHOLD = 0.9

# Colors
WHITE = (255, 255, 255)
DARK_BG = (18, 18, 28)
PANEL = (24, 24, 34)
ACCENT = (240, 200, 80)


class GameLauncher:
    """Main game launcher application."""
    
    def __init__(self):
        pygame.init()
        pygame.mouse.set_visible(False)
        self.screen = pygame.display.set_mode(WINDOW_SIZE, pygame.FULLSCREEN | pygame.NOFRAME)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, max(32, int(WINDOW_SIZE[1] * 0.05)))
        
        # Hand tracking
        self.hand_tracker = HandTracker(SERVER_WS)
        self.hand_tracker.start()
        
        # UI state
        self.state = "menu"
        self.selection_ui = PlayerSelectionUI(self.screen)
        self.current_game = None
        
        # Menu buttons
        self.game_buttons = self._create_game_buttons()
        self.start_button = self._create_start_button()

    def _create_game_buttons(self) -> List[HoverButton]:
        """Create game selection buttons."""
        games = ["Monopoly"]
        buttons = []
        for i, game in enumerate(games):
            btn_rect = pygame.Rect(
                WINDOW_SIZE[0] // 2 - 150,
                WINDOW_SIZE[1] // 2 - 60 + i * 120,
                300, 90
            )
            buttons.append(HoverButton(btn_rect, game, self.font))
        return buttons

    def _create_start_button(self) -> HoverButton:
        """Create start game button."""
        btn_rect = pygame.Rect(
            WINDOW_SIZE[0] // 2 - 140,
            WINDOW_SIZE[1] // 2 - 45,
            280, 90
        )
        return HoverButton(btn_rect, "Start", self.font)

    def get_fingertip_meta(self) -> List[Dict]:
        """Get fingertip positions including mouse (for testing)."""
        screen_w, screen_h = self.screen.get_size()
        meta = self.hand_tracker.get_fingertips_for_screen(screen_w, screen_h)
        
        # Add mouse for testing
        mouse_pos = pygame.mouse.get_pos()
        meta.append({"pos": mouse_pos, "hand": -1, "name": "mouse"})
        
        return meta

    def handle_menu_state(self, fingertip_meta: List[Dict]):
        """Handle game menu screen."""
        panel = pygame.Rect(80, 60, WINDOW_SIZE[0] - 160, WINDOW_SIZE[1] - 120)
        pygame.draw.rect(self.screen, PANEL, panel, border_radius=14)
        
        title = pygame.font.SysFont(None, 64).render("Game Launcher", True, WHITE)
        self.screen.blit(title, (panel.centerx - title.get_width() // 2, panel.top + 24))

        for btn in self.game_buttons:
            btn.draw(self.screen, fingertip_meta)
            self._draw_button_progress(btn, fingertip_meta)
            
            if btn.clicked:
                self.state = "player_select"
                btn.reset()

    def handle_player_select_state(self, fingertip_meta: List[Dict]):
        """Handle player selection screen."""
        self.selection_ui.update_with_fingertips(fingertip_meta)
        self.selection_ui.draw_slots()

        # Draw hover progress for slots
        for h in self.selection_ui.get_hover_progress():
            px, py = h["pos"]
            progress = h["progress"]
            draw_circular_progress(
                self.screen, (px + 28, py - 28), 20, progress, 
                ACCENT, thickness=6
            )

        # Draw start button
        selected_count = self.selection_ui.selected_count()
        self.start_button.draw(self.screen, fingertip_meta, enabled=selected_count >= 2)
        self._draw_button_progress(self.start_button, fingertip_meta)

        # Draw labels
        label_small = pygame.font.SysFont(None, 26).render(
            f"{selected_count} players selected", True, WHITE
        )
        self.screen.blit(
            label_small,
            (self.start_button.rect.centerx - label_small.get_width() // 2,
             self.start_button.rect.bottom + 8)
        )
        
        label_min = pygame.font.SysFont(None, 28).render(
            "Minimum 2 players to start", True, WHITE
        )
        self.screen.blit(
            label_min,
            (self.start_button.rect.centerx - label_min.get_width() // 2,
             self.start_button.rect.top - 30)
        )

        # Start game if button clicked
        if self.start_button.clicked and selected_count >= 2:
            self._start_monopoly()
            self.start_button.reset()

    def _start_monopoly(self):
        """Initialize and start Monopoly game."""
        selected_indices = [i for i, s in enumerate(self.selection_ui.selected) if s]
        self.current_game = MonopolyGame(
            self.screen,
            lambda w, h: self.get_fingertip_meta()
        )
        self.current_game.players_selected = selected_indices
        for i in range(8):
            self.current_game.selection_ui.selected[i] = (i in selected_indices)
        self.current_game.current = selected_indices[0] if selected_indices else 0
        self.state = "monopoly_playing"

    def handle_game_state(self, fingertip_meta: List[Dict]):
        """Handle active game screen."""
        if self.current_game is not None:
            self.current_game.update(fingertip_meta)
            self.current_game.draw()
        else:
            # Fallback if game not initialized
            panel = pygame.Rect(80, 60, WINDOW_SIZE[0] - 160, WINDOW_SIZE[1] - 120)
            pygame.draw.rect(self.screen, PANEL, panel, border_radius=14)
            txt = self.font.render("Game initializing...", True, WHITE)
            self.screen.blit(txt, txt.get_rect(center=(WINDOW_SIZE[0] // 2, WINDOW_SIZE[1] // 2)))

    def _draw_button_progress(self, button: HoverButton, fingertip_meta: List[Dict]):
        """Draw circular progress for a button's hover state."""
        for meta in fingertip_meta:
            pos = meta.get("pos")
            hand = meta.get("hand")
            name = meta.get("name", "")
            key = f"{hand}:{name}" if hand is not None else f"coord:{pos[0]}_{pos[1]}"
            
            if pos and button.rect.collidepoint(pos):
                start = button.hover_start.get(key)
                if start:
                    elapsed = time.time() - start
                    progress = min(1.0, max(0.0, elapsed / HOVER_TIME_THRESHOLD))
                    draw_circular_progress(
                        self.screen, (pos[0] + 28, pos[1] - 28), 20,
                        progress, ACCENT, thickness=6
                    )

    def draw_cursors(self, fingertip_meta: List[Dict]):
        """Draw cursor for each fingertip."""
        for meta in fingertip_meta:
            px, py = meta["pos"]
            col = self.selection_ui.closest_player_color((px, py))
            draw_cursor(self.screen, (px, py), col)

    def run(self):
        """Main game loop."""
        running = True
        while running:
            fingertip_meta = self.get_fingertip_meta()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False

            self.screen.fill(DARK_BG)

            # Handle current state
            if self.state == "menu":
                self.handle_menu_state(fingertip_meta)
            elif self.state == "player_select":
                self.handle_player_select_state(fingertip_meta)
            elif self.state == "monopoly_playing":
                self.handle_game_state(fingertip_meta)

            # Draw cursors
            self.draw_cursors(fingertip_meta)

            pygame.display.flip()
            self.clock.tick(FPS)

        self.cleanup()

    def cleanup(self):
        """Clean up resources."""
        self.hand_tracker.stop()
        pygame.quit()


def run_pygame():
    """Entry point for launcher."""
    launcher = GameLauncher()
    launcher.run()


if __name__ == "__main__":
    run_pygame()