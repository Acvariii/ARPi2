import threading
import time
import pygame
from hand_tracking import start_ws_thread, fingertip_meta_for_screen
from ui_elements import HoverButton, PlayerSelectionUI
from monopoly import MonopolyGame

WINDOW_SIZE = (1280, 720)
FPS = 60
MENU_LOCKOUT_SECONDS = 0.6  # ignore menu clicks for this period after startup
SELECTION_LOCKOUT_SECONDS = 0.35  # brief lockout when entering selection screen

def run_launcher():
    pygame.init()
    pygame.mouse.set_visible(False)
    screen = pygame.display.set_mode(WINDOW_SIZE)
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 48)

    # start websocket hand receiver thread
    start_ws_thread()

    # ignore menu clicks for a short time on startup to avoid accidental auto-advance
    menu_lockout_until = time.time() + MENU_LOCKOUT_SECONDS
    selection_lockout_until = 0.0

    # UI elements
    center = (WINDOW_SIZE[0]//2, WINDOW_SIZE[1]//2)
    btn_monopoly = HoverButton((center[0]-320, center[1]-70, 280, 90), "Monopoly", font)
    btn_blackjack = HoverButton((center[0]+40, center[1]-70, 280, 90), "Blackjack", font)
    # Start and Back buttons used on player selection screen
    start_btn = HoverButton((center[0]-140, center[1]-45, 280, 90), "Start", font)
    back_btn = HoverButton((20, 20, 120, 48), "Back", pygame.font.SysFont(None, 28), radius=10)

    state = "menu"
    selection_ui = PlayerSelectionUI(screen)
    monopoly_game = MonopolyGame(screen, fingertip_meta_for_screen)

    running = True
    while running:
        fingertip_meta = fingertip_meta_for_screen(*screen.get_size())
        fingertip_points = [m["pos"] for m in fingertip_meta]

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        screen.fill((18,18,28))

        if state == "menu":
            # draw big panel
            panel = pygame.Rect(80, 60, WINDOW_SIZE[0]-160, WINDOW_SIZE[1]-120)
            pygame.draw.rect(screen, (24,24,34), panel, border_radius=14)
            title = pygame.font.SysFont(None, 64).render("Game Launcher", True, (255,255,255))
            screen.blit(title, (panel.centerx - title.get_width()//2, panel.top + 24))

            # draw menu buttons
            btn_monopoly.draw(screen, fingertip_points)
            btn_blackjack.draw(screen, fingertip_points)
            # show slot previews (non-interactive preview)
            selection_ui.draw_slots()

            # only accept menu clicks after the initial lockout to avoid auto-advance
            # while still in the lockout period, clear menu button hover state every frame
            # so no stale hover timers cause immediate clicks
            if time.time() <= menu_lockout_until:
                btn_monopoly.reset()
                btn_blackjack.reset()
            else:
                if btn_monopoly.clicked:
                    # reset hover state for selection screen to avoid immediate toggles
                    selection_ui.hover_start.clear()
                    selection_ui.hover_pos.clear()
                    start_btn.reset()
                    back_btn.reset()
                    btn_monopoly.reset()
                    # set a short lockout so selection doesn't immediately toggle
                    selection_lockout_until = time.time() + SELECTION_LOCKOUT_SECONDS
                    state = "monopoly_select"
                if btn_blackjack.clicked:
                    btn_blackjack.reset()
                    state = "blackjack"

        elif state == "monopoly_select":
            # Player selection screen: briefly ignore selection updates if we just entered
            if time.time() > selection_lockout_until:
                selection_ui.update_with_fingertips(fingertip_meta)
            # always draw slots
            selection_ui.draw_slots()

            # draw monopoly preview under selection
            monopoly_game.draw_board()

            # Draw and handle Start button
            selected_count = selection_ui.selected_count()
            start_enabled = (selected_count >= selection_ui.min_players)
            # draw Back button
            back_btn.draw(screen, fingertip_points)
            if back_btn.clicked:
                state = "menu"
                back_btn.reset()

            # draw Start (disabled until enough players)
            # draw start after board to ensure visibility; pass enabled flag
            # draw it last (just before hover indicators) so it's clearly visible
            start_btn.draw(screen, fingertip_points, enabled=start_enabled)

            # only allow starting when enough players selected
            hint_font = pygame.font.SysFont(None, 22)
            hint = hint_font.render(f"{selected_count} selected (min {selection_ui.min_players})", True, (200,200,200))
            screen.blit(hint, (start_btn.rect.centerx - hint.get_width()//2, start_btn.rect.bottom + 8))
            if start_btn.clicked and start_enabled:
                # assign selection state to the game and transition to playing
                monopoly_game.selection_ui = selection_ui
                monopoly_game.players_selected = [i for i, s in enumerate(selection_ui.selected) if s]
                monopoly_game.started = True
                state = "monopoly_playing"
                start_btn.reset()

            # hover progress indicators from selection_ui
            hover_list = selection_ui.get_hover_progress()
            for h in hover_list:
                px, py = h["pos"]
                prog = h["progress"]
                off_x, off_y = 28, -28
                arc_rect = pygame.Rect(px + off_x - 20, py + off_y - 20, 40, 40)
                start_ang = -3.1415/2
                end_ang = start_ang + prog * 2 * 3.1415
                pygame.draw.circle(screen, (60,60,60), arc_rect.center, 20)
                pygame.draw.arc(screen, (240,200,80), arc_rect, start_ang, end_ang, 6)

        elif state == "monopoly_playing":
            # Running game: update & draw game logic; selection UI remains for reference (no selection updates)
            monopoly_game.update(fingertip_meta)
            monopoly_game.draw()

        else:
            txt = font.render("Other game (not implemented)", True, (255,255,255))
            screen.blit(txt, txt.get_rect(center=(WINDOW_SIZE[0]//2, WINDOW_SIZE[1]//2)))

        # draw fingertips on top
        for meta in fingertip_meta:
            px, py = meta["pos"]
            # nearest player color via selection_ui
            col = selection_ui.closest_player_color((px,py))
            pygame.draw.circle(screen, (255,255,255), (px,py), 20)
            pygame.draw.circle(screen, col, (px,py), 14)
            pygame.draw.circle(screen, (0,0,0), (px,py), 4)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()