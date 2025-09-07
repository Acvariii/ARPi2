import threading
import time
import pygame
from hand_tracking import start_ws_thread, fingertip_meta_for_screen
from ui_elements import HoverButton, PlayerSelectionUI
from monopoly import MonopolyGame

WINDOW_SIZE = (1280, 720)
FPS = 60

def run_launcher():
    pygame.init()
    pygame.mouse.set_visible(False)
    screen = pygame.display.set_mode(WINDOW_SIZE)
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 48)

    # start websocket hand receiver thread
    start_ws_thread()

    # UI elements
    center = (WINDOW_SIZE[0]//2, WINDOW_SIZE[1]//2)
    btn_monopoly = HoverButton((center[0]-320, center[1]-70, 280, 90), "Monopoly", font)
    btn_blackjack = HoverButton((center[0]+40, center[1]-70, 280, 90), "Blackjack", font)

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

            btn_monopoly.draw(screen, fingertip_points)
            btn_blackjack.draw(screen, fingertip_points)
            # show slot previews fill screen
            selection_ui.draw_slots()

            if btn_monopoly.clicked:
                state = "monopoly"
                btn_monopoly.reset()
            if btn_blackjack.clicked:
                state = "blackjack"
                btn_blackjack.reset()

        elif state == "monopoly":
            # ensure selection UI updates (players selection persists)
            selection_ui.update_with_fingertips(fingertip_meta)
            selection_ui.draw_slots()
            # update and draw monopoly board
            monopoly_game.update(fingertip_meta)
            monopoly_game.draw()

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