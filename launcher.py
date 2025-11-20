import pygame
from typing import List, Dict
from ui_components import HoverButton, draw_cursor, draw_circular_progress, PlayerSelectionUI
from monopoly import MonopolyGame
from monopoly2 import MonopolyGame as Monopoly2Game
from blackjack import BlackjackGame
from hand_tracking import HandTracker
from config import SERVER_WS, WINDOW_SIZE, FPS, HOVER_TIME_THRESHOLD, Colors

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
        self.selected_game = None
        
        # Menu buttons
        self.game_buttons = self._create_game_buttons()
        self.start_button = self._create_start_button()

    def _create_game_buttons(self) -> List[HoverButton]:
        """Create game selection buttons."""
        games = ["Monopoly", "Monopoly2", "Blackjack"]
        buttons = []
        for i, game in enumerate(games):
            btn_rect = pygame.Rect(
                WINDOW_SIZE[0] // 2 - 150,
                WINDOW_SIZE[1] // 2 - 180 + i * 120,
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
        pygame.draw.rect(self.screen, Colors.PANEL, panel, border_radius=14)
        
        title = pygame.font.SysFont(None, 64).render("Game Launcher", True, Colors.WHITE)
        self.screen.blit(title, (panel.centerx - title.get_width() // 2, panel.top + 24))

        for i, btn in enumerate(self.game_buttons):
            if btn.update(fingertip_meta):
                self.selected_game = ["monopoly", "monopoly2", "blackjack"][i]
                self.state = "player_select"
                btn.reset()
            
            btn.draw(self.screen)
            
            for progress_info in btn.get_hover_progress():
                center_x = progress_info["rect"].centerx + 28
                center_y = progress_info["rect"].top - 28
                draw_circular_progress(
                    self.screen, (center_x, center_y), 20,
                    progress_info["progress"], Colors.ACCENT, thickness=6
                )

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
                Colors.ACCENT, thickness=6
            )

        # Draw start button
        selected_count = self.selection_ui.selected_count()
        
        if self.start_button.update(fingertip_meta, enabled=selected_count >= 2):
            if selected_count >= 2:
                self._start_selected_game()
                self.start_button.reset()
        
        self.start_button.draw(self.screen)
        
        # Draw hover progress
        for progress_info in self.start_button.get_hover_progress():
            center_x = progress_info["rect"].centerx + 28
            center_y = progress_info["rect"].top - 28
            draw_circular_progress(
                self.screen, (center_x, center_y), 20,
                progress_info["progress"], Colors.ACCENT, thickness=6
            )

        # Draw labels
        label_small = pygame.font.SysFont(None, 26).render(
            f"{selected_count} players selected", True, Colors.WHITE
        )
        self.screen.blit(
            label_small,
            (self.start_button.rect.centerx - label_small.get_width() // 2,
             self.start_button.rect.bottom + 8)
        )
        
        label_min = pygame.font.SysFont(None, 28).render(
            "Minimum 2 players to start", True, Colors.WHITE
        )
        self.screen.blit(
            label_min,
            (self.start_button.rect.centerx - label_min.get_width() // 2,
             self.start_button.rect.top - 30)
        )

    def _start_selected_game(self):
        """Initialize and start the selected game."""
        selected_indices = [i for i, s in enumerate(self.selection_ui.selected) if s]
        
        if self.selected_game == "monopoly":
            self.current_game = MonopolyGame(
                self.screen,
                lambda w, h: self.get_fingertip_meta()
            )
            self.current_game.start_game(selected_indices)
            self.state = "monopoly_playing"
        elif self.selected_game == "monopoly2":
            self.current_game = Monopoly2Game(
                self.screen,
                lambda w, h: self.get_fingertip_meta()
            )
            self.current_game.start_game(selected_indices)
            self.state = "monopoly2_playing"
        elif self.selected_game == "blackjack":
            self.current_game = BlackjackGame(
                self.screen,
                lambda w, h: self.get_fingertip_meta()
            )
            self.current_game.start_game(selected_indices)
            self.state = "blackjack_playing"

    def handle_game_state(self, fingertip_meta: List[Dict]):
        """Handle active game screen."""
        if self.current_game is not None:
            if hasattr(self.current_game, 'should_return_to_menu') and self.current_game.should_return_to_menu():
                self.state = "menu"
                self.current_game = None
                return
            self.current_game.update(fingertip_meta)
            self.current_game.draw()
        else:
            # Fallback if game not initialized
            panel = pygame.Rect(80, 60, WINDOW_SIZE[0] - 160, WINDOW_SIZE[1] - 120)
            pygame.draw.rect(self.screen, Colors.PANEL, panel, border_radius=14)
            txt = self.font.render("Game initializing...", True, Colors.WHITE)
            self.screen.blit(txt, txt.get_rect(center=(WINDOW_SIZE[0] // 2, WINDOW_SIZE[1] // 2)))

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

            self.screen.fill(Colors.DARK_BG)

            if self.state == "menu":
                self.handle_menu_state(fingertip_meta)
            elif self.state == "player_select":
                self.handle_player_select_state(fingertip_meta)
            elif self.state in ["monopoly_playing", "monopoly2_playing", "blackjack_playing"]:
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