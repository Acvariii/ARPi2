import pygame
from typing import List, Dict, Callable
from config import PLAYER_COLORS, Colors
from player_panel import calculate_all_panels
from ui_components import HoverButton, RotatedText
from blackjack.player import BlackjackPlayer
from blackjack.game_logic import BlackjackLogic
from blackjack.drawing import CardDrawer, ChipDrawer


class BlackjackGame:
    
    def __init__(self, screen: pygame.Surface, fingertip_callback: Callable):
        self.screen = screen
        self.get_fingertips = fingertip_callback
        self.screen_size = screen.get_size()
        
        self.players = [BlackjackPlayer(i, PLAYER_COLORS[i]) for i in range(8)]
        self.active_players: List[int] = []
        self.current_player_idx = 0
        
        self.deck = []
        self.dealer_hand = []
        self.dealer_reveal = False
        
        self.phase = "betting"
        self.round_active = False
        
        self.panels = calculate_all_panels(self.screen_size)
        self.buttons: Dict[int, Dict[str, HoverButton]] = {}
        
        self._calculate_table_geometry()
        self._init_buttons()
    
    def _calculate_table_geometry(self):
        w, h = self.screen_size
        horizontal_panel_height = int(h * 0.10)
        vertical_panel_width = int(w * 0.12)
        margin = 20
        
        available_width = w - (2 * vertical_panel_width) - (2 * margin)
        available_height = h - (2 * horizontal_panel_height) - (2 * margin)
        
        table_size = min(available_width, available_height)
        table_x = vertical_panel_width + margin + (available_width - table_size) // 2
        table_y = horizontal_panel_height + margin + (available_height - table_size) // 2
        
        self.table_rect = pygame.Rect(table_x, table_y, table_size, table_size)
        
        self.dealer_area = pygame.Rect(
            self.table_rect.centerx - 150,
            self.table_rect.centery - 60,
            300, 120
        )
    
    def _init_buttons(self):
        font = pygame.font.SysFont(None, 24)
        for idx in range(8):
            panel = self.panels[idx]
            margin = 10
            gap = 8
            
            if panel.orientation == 0:
                btn_area_height = int(panel.rect.height * 0.55)
                y = panel.rect.y + panel.rect.height - btn_area_height
                x = panel.rect.x + margin
                avail_w = panel.rect.width - 2 * margin
                btn_w = (avail_w - 3 * gap) // 4
                btn_h = btn_area_height - 2 * margin
                
                r_hit = pygame.Rect(x, y + margin, btn_w, btn_h)
                r_stand = pygame.Rect(x + btn_w + gap, y + margin, btn_w, btn_h)
                r_double = pygame.Rect(x + 2 * (btn_w + gap), y + margin, btn_w, btn_h)
                r_split = pygame.Rect(x + 3 * (btn_w + gap), y + margin, btn_w, btn_h)
            
            elif panel.orientation == 180:
                info_height_frac = 0.45
                button_area_height = int(panel.rect.height * (1 - info_height_frac))
                info_area_height = int(panel.rect.height * info_height_frac)
                y = panel.rect.y + info_area_height
                x = panel.rect.x + margin
                avail_w = panel.rect.width - 2 * margin
                btn_w = (avail_w - 3 * gap) // 4
                btn_h = button_area_height - 2 * margin
                
                r_hit = pygame.Rect(x, y + margin, btn_w, btn_h)
                r_stand = pygame.Rect(x + btn_w + gap, y + margin, btn_w, btn_h)
                r_double = pygame.Rect(x + 2 * (btn_w + gap), y + margin, btn_w, btn_h)
                r_split = pygame.Rect(x + 3 * (btn_w + gap), y + margin, btn_w, btn_h)
            
            elif panel.orientation == 90:
                info_width_frac = 0.35
                button_area_width = int(panel.rect.width * (1 - info_width_frac))
                x = panel.rect.x
                y = panel.rect.y + margin
                avail_h = panel.rect.height - 2 * margin
                btn_h = (avail_h - 3 * gap) // 4
                btn_w = button_area_width - 2 * margin
                
                r_hit = pygame.Rect(x + margin, y, btn_w, btn_h)
                r_stand = pygame.Rect(x + margin, y + btn_h + gap, btn_w, btn_h)
                r_double = pygame.Rect(x + margin, y + 2 * (btn_h + gap), btn_w, btn_h)
                r_split = pygame.Rect(x + margin, y + 3 * (btn_h + gap), btn_w, btn_h)
            
            else:
                info_width_frac = 0.35
                button_area_width = int(panel.rect.width * (1 - info_width_frac))
                info_area_width = int(panel.rect.width * info_width_frac)
                x = panel.rect.x + info_area_width
                y = panel.rect.y + margin
                avail_h = panel.rect.height - 2 * margin
                btn_h = (avail_h - 3 * gap) // 4
                btn_w = button_area_width - 2 * margin
                
                r_hit = pygame.Rect(x + margin, y, btn_w, btn_h)
                r_stand = pygame.Rect(x + margin, y + btn_h + gap, btn_w, btn_h)
                r_double = pygame.Rect(x + margin, y + 2 * (btn_h + gap), btn_w, btn_h)
                r_split = pygame.Rect(x + margin, y + 3 * (btn_h + gap), btn_w, btn_h)
            
            self.buttons[idx] = {
                "hit": HoverButton(r_hit, "Hit", font, orientation=panel.orientation),
                "stand": HoverButton(r_stand, "Stand", font, orientation=panel.orientation),
                "double": HoverButton(r_double, "Double", font, orientation=panel.orientation),
                "split": HoverButton(r_split, "Split", font, orientation=panel.orientation),
                "bet5": HoverButton(r_hit, "$5", font, orientation=panel.orientation),
                "bet25": HoverButton(r_stand, "$25", font, orientation=panel.orientation),
                "bet100": HoverButton(r_double, "$100", font, orientation=panel.orientation),
                "ready": HoverButton(r_split, "Ready", font, orientation=panel.orientation)
            }
    
    def start_game(self, player_indices: List[int]):
        self.active_players = sorted(player_indices)
        
        for i in self.active_players:
            p = self.players[i]
            p.chips = 1000
            p.is_active = True
            p.is_ready = False
        
        self.phase = "betting"
        self.round_active = False
    
    def _new_round(self):
        self.deck = BlackjackLogic.create_deck()
        self.dealer_hand = []
        self.dealer_reveal = False
        
        playing_players = [i for i in self.active_players if not self.players[i].is_sitting_out()]
        
        if not playing_players:
            self.phase = "betting"
            for idx in self.active_players:
                self.players[idx].current_bet = 0
            return
        
        for idx in playing_players:
            player = self.players[idx]
            player.reset_hand()
        
        for idx in playing_players:
            player = self.players[idx]
            player.add_card(self.deck.pop())
        
        self.dealer_hand.append(self.deck.pop())
        
        for idx in playing_players:
            player = self.players[idx]
            player.add_card(self.deck.pop())
        
        self.dealer_hand.append(self.deck.pop())
        
        self.phase = "playing"
        self.round_active = True
    
    def _hit(self, player: BlackjackPlayer):
        if len(self.deck) > 0:
            card = self.deck.pop()
            player.add_card(card)
            
            hand = player.get_current_hand()
            if BlackjackLogic.hand_value(hand) > 21:
                player.is_busted = True
    
    def _double_down(self, player: BlackjackPlayer):
        hand = player.get_current_hand()
        if BlackjackLogic.can_double_down(hand) and player.chips >= player.current_bet:
            player.chips -= player.current_bet
            player.current_bet *= 2
            self._hit(player)
            if not player.is_busted:
                player.is_standing = True
    
    def _split(self, player: BlackjackPlayer):
        hand = player.get_current_hand()
        if BlackjackLogic.can_split(hand) and player.chips >= player.current_bet:
            card1 = hand[0]
            card2 = hand[1]
            player.hands = [[card1], [card2]]
            player.current_hand_idx = 0
            player.chips -= player.current_bet
    
    def _dealer_turn(self):
        self.dealer_reveal = True
        
        while BlackjackLogic.hand_value(self.dealer_hand) < 17:
            if len(self.deck) > 0:
                self.dealer_hand.append(self.deck.pop())
        
        self._resolve_round()
    
    def _resolve_round(self):
        dealer_value = BlackjackLogic.hand_value(self.dealer_hand)
        dealer_busted = dealer_value > 21
        
        for idx in self.active_players:
            player = self.players[idx]
            
            if player.is_sitting_out():
                player.current_bet = 0
                player.is_ready = False
                continue
            
            hand = player.get_current_hand()
            player_value = BlackjackLogic.hand_value(hand)
            
            if player.is_busted:
                player.lose_bet()
            elif dealer_busted:
                if BlackjackLogic.is_blackjack(hand):
                    player.win_bet(2.5)
                else:
                    player.win_bet(2.0)
            elif player_value > dealer_value:
                if BlackjackLogic.is_blackjack(hand):
                    player.win_bet(2.5)
                else:
                    player.win_bet(2.0)
            elif player_value == dealer_value:
                player.push_bet()
            else:
                player.lose_bet()
            
            player.is_ready = False
        
        self.phase = "betting"
        self.round_active = False
    
    def update(self, fingertip_meta: List[Dict]):
        if self.phase == "betting":
            for idx in self.active_players:
                player = self.players[idx]
                buttons = self.buttons[idx]
                
                if not player.is_ready:
                    if buttons["bet5"].update(fingertip_meta, enabled=player.chips >= 5 and not player.is_sitting_out()):
                        player.place_bet(5)
                        buttons["bet5"].reset()
                    
                    if buttons["bet25"].update(fingertip_meta, enabled=player.chips >= 25 and not player.is_sitting_out()):
                        player.place_bet(25)
                        buttons["bet25"].reset()
                    
                    if buttons["bet100"].update(fingertip_meta, enabled=player.chips >= 100 and not player.is_sitting_out()):
                        player.place_bet(100)
                        buttons["bet100"].reset()
                    
                    ready_enabled = True
                    if buttons["ready"].update(fingertip_meta, enabled=ready_enabled):
                        if player.current_bet == 0:
                            player.skip_round()
                        player.is_ready = True
                        buttons["ready"].reset()
            
            all_ready = all(self.players[i].is_ready for i in self.active_players)
            if all_ready and not self.round_active:
                self._new_round()
        elif self.phase == "playing":
            for idx in self.active_players:
                player = self.players[idx]
                
                if player.is_sitting_out() or player.is_standing or player.is_busted:
                    continue
                
                hand = player.get_current_hand()
                buttons = self.buttons[idx]
                
                can_double = BlackjackLogic.can_double_down(hand) and player.chips >= player.current_bet
                can_split = BlackjackLogic.can_split(hand) and player.chips >= player.current_bet
                
                if buttons["hit"].update(fingertip_meta):
                    self._hit(player)
                    buttons["hit"].reset()
                
                if buttons["stand"].update(fingertip_meta):
                    player.is_standing = True
                    buttons["stand"].reset()
                
                if buttons["double"].update(fingertip_meta, enabled=can_double):
                    self._double_down(player)
                    buttons["double"].reset()
                
                if buttons["split"].update(fingertip_meta, enabled=can_split):
                    self._split(player)
                    buttons["split"].reset()
            
            all_done = all(self.players[i].is_sitting_out() or self.players[i].is_standing or self.players[i].is_busted 
                          for i in self.active_players)
            if all_done:
                self._dealer_turn()
    
    def draw(self):
        pygame.draw.ellipse(self.screen, (20, 80, 40), self.table_rect)
        pygame.draw.ellipse(self.screen, (255, 215, 0), self.table_rect, width=3)
        
        self._draw_dealer()
        self._draw_panels()
        self._draw_player_areas()
    
    def _draw_dealer(self):
        pygame.draw.rect(self.screen, (30, 90, 50), self.dealer_area, border_radius=10)
        pygame.draw.rect(self.screen, (255, 215, 0), self.dealer_area, width=2, border_radius=10)
        
        font_label = pygame.font.SysFont(None, 24, bold=True)
        if self.phase == "betting":
            label = font_label.render("PLACE YOUR BETS", True, (255, 255, 100))
        else:
            label = font_label.render("DEALER", True, Colors.WHITE)
        self.screen.blit(label, (self.dealer_area.centerx - label.get_width() // 2, self.dealer_area.top + 5))
        
        if len(self.dealer_hand) > 0:
            hand_width = CardDrawer.get_hand_width(len(self.dealer_hand), 20)
            start_x = self.dealer_area.centerx - hand_width // 2
            CardDrawer.draw_hand(self.screen, self.dealer_hand, start_x, self.dealer_area.top + 30, 
                               dealer_hidden=not self.dealer_reveal)
        
        if self.dealer_reveal:
            dealer_value = BlackjackLogic.hand_value(self.dealer_hand)
            font_value = pygame.font.SysFont(None, 28, bold=True)
            value_color = (255, 100, 100) if dealer_value > 21 else Colors.WHITE
            value_text = font_value.render(str(dealer_value), True, value_color)
            self.screen.blit(value_text, (self.dealer_area.right - value_text.get_width() - 10, 
                                         self.dealer_area.bottom - value_text.get_height() - 5))
    
    def _draw_panels(self):
        for idx in range(8):
            player = self.players[idx]
            panel = self.panels[idx]
            is_active = idx in self.active_players
            
            if is_active:
                panel.draw_background(self.screen, False)
            else:
                washed = tuple(min(255, int(c * 0.3 + 60 * 0.7)) for c in panel.color)
                pygame.draw.rect(self.screen, washed, panel.rect, border_radius=8)
                pygame.draw.rect(self.screen, (40, 40, 40), panel.rect, width=1, border_radius=8)
            
            if is_active:
                font = pygame.font.SysFont("Arial", 18, bold=True)
                
                bet_display = "Sitting Out" if player.is_sitting_out() else f"Bet: ${player.current_bet}"
                
                if panel.orientation == 0:
                    info_rect = pygame.Rect(panel.rect.x + 10, panel.rect.y + 10,
                                           panel.rect.width - 20, int(panel.rect.height * 0.35))
                    RotatedText.draw(self.screen, f"${player.chips} | {bet_display}",
                                   font, Colors.BLACK, info_rect.center, panel.orientation)
                elif panel.orientation == 180:
                    info_height = int(panel.rect.height * 0.45)
                    info_rect = pygame.Rect(panel.rect.x + 10, panel.rect.y + 10,
                                           panel.rect.width - 20, info_height - 20)
                    RotatedText.draw(self.screen, f"${player.chips} | {bet_display}",
                                   font, Colors.BLACK, info_rect.center, panel.orientation)
                elif panel.orientation == 90:
                    info_width_frac = 0.35
                    button_area_width = int(panel.rect.width * (1 - info_width_frac))
                    info_width = int(panel.rect.width * info_width_frac)
                    info_rect = pygame.Rect(panel.rect.x + button_area_width, panel.rect.y + 10,
                                           info_width - 10, panel.rect.height - 20)
                    RotatedText.draw_block(self.screen,
                                         [(f"${player.chips}", font, Colors.BLACK),
                                          (bet_display, font, Colors.BLACK)],
                                         info_rect, panel.orientation, line_spacing=12)
                else:
                    info_width = int(panel.rect.width * 0.35)
                    info_rect = pygame.Rect(panel.rect.x + 10, panel.rect.y + 10,
                                           info_width - 10, panel.rect.height - 20)
                    RotatedText.draw_block(self.screen,
                                         [(f"${player.chips}", font, Colors.BLACK),
                                          (bet_display, font, Colors.BLACK)],
                                         info_rect, panel.orientation, line_spacing=12)
                
                if self.phase == "betting":
                    if player.is_ready:
                        font_status = pygame.font.SysFont("Arial", 18, bold=True)
                        status_text = "Ready!" if not player.is_sitting_out() else "Sitting Out"
                        status_color = (100, 255, 100) if not player.is_sitting_out() else (150, 150, 150)
                        if panel.orientation in [0, 180]:
                            status_rect = pygame.Rect(panel.rect.x + 10, panel.rect.centery - 10, panel.rect.width - 20, 20)
                            RotatedText.draw(self.screen, status_text, font_status, status_color, status_rect.center, panel.orientation)
                        else:
                            status_rect = pygame.Rect(panel.rect.centerx - 10, panel.rect.y + 10, 20, panel.rect.height - 20)
                            RotatedText.draw(self.screen, status_text, font_status, status_color, status_rect.center, panel.orientation)
                    else:
                        bet_buttons = ["bet5", "bet25", "bet100", "ready"]
                        for btn_key in bet_buttons:
                            self.buttons[idx][btn_key].draw(self.screen)
                elif self.phase == "playing" and not player.is_sitting_out():
                    if player.is_standing:
                        font_status = pygame.font.SysFont("Arial", 18, bold=True)
                        if panel.orientation in [0, 180]:
                            status_rect = pygame.Rect(panel.rect.x + 10, panel.rect.centery - 10, panel.rect.width - 20, 20)
                            RotatedText.draw(self.screen, "Standing", font_status, (255, 215, 0), status_rect.center, panel.orientation)
                        else:
                            status_rect = pygame.Rect(panel.rect.centerx - 10, panel.rect.y + 10, 20, panel.rect.height - 20)
                            RotatedText.draw(self.screen, "Standing", font_status, (255, 215, 0), status_rect.center, panel.orientation)
                    elif player.is_busted:
                        font_status = pygame.font.SysFont("Arial", 18, bold=True)
                        if panel.orientation in [0, 180]:
                            status_rect = pygame.Rect(panel.rect.x + 10, panel.rect.centery - 10, panel.rect.width - 20, 20)
                            RotatedText.draw(self.screen, "Busted!", font_status, (255, 100, 100), status_rect.center, panel.orientation)
                        else:
                            status_rect = pygame.Rect(panel.rect.centerx - 10, panel.rect.y + 10, 20, panel.rect.height - 20)
                            RotatedText.draw(self.screen, "Busted!", font_status, (255, 100, 100), status_rect.center, panel.orientation)
                    else:
                        game_buttons = ["hit", "stand", "double", "split"]
                        for btn_key in game_buttons:
                            self.buttons[idx][btn_key].draw(self.screen)
            else:
                font = pygame.font.SysFont("Arial", 36, bold=True)
                label = f"P{idx + 1}"
                text_surf = font.render(label, True, (100, 100, 100))
                if panel.orientation != 0:
                    text_surf = pygame.transform.rotate(text_surf, panel.orientation)
                text_rect = text_surf.get_rect(center=panel.rect.center)
                self.screen.blit(text_surf, text_rect)
    
    def _draw_player_areas(self):
        if not self.round_active:
            return
        
        positions = [
            (self.table_rect.centerx - 200, self.table_rect.bottom - 80),
            (self.table_rect.centerx, self.table_rect.bottom - 80),
            (self.table_rect.centerx + 200, self.table_rect.bottom - 80),
            (self.table_rect.centerx - 200, self.table_rect.top + 80),
            (self.table_rect.centerx, self.table_rect.top + 80),
            (self.table_rect.centerx + 200, self.table_rect.top + 80),
            (self.table_rect.left + 80, self.table_rect.centery),
            (self.table_rect.right - 80, self.table_rect.centery),
        ]
        
        for idx in self.active_players:
            player = self.players[idx]
            
            if player.is_sitting_out():
                continue
            
            hand = player.get_current_hand()
            
            if len(hand) > 0:
                px, py = positions[idx]
                hand_width = CardDrawer.get_hand_width(len(hand), 25)
                start_x = px - hand_width // 2
                
                bg_rect = pygame.Rect(start_x - 10, py - 35, hand_width + 20, CardDrawer.CARD_HEIGHT + 50)
                pygame.draw.rect(self.screen, (*player.color, 100), bg_rect, border_radius=8)
                pygame.draw.rect(self.screen, player.color, bg_rect, width=3, border_radius=8)
                
                CardDrawer.draw_hand(self.screen, hand, start_x, py, spacing=25, outline_color=player.color)
                
                hand_value = BlackjackLogic.hand_value(hand)
                font_value = pygame.font.SysFont(None, 24, bold=True)
                value_color = (255, 100, 100) if hand_value > 21 else Colors.WHITE
                value_text = font_value.render(str(hand_value), True, value_color)
                self.screen.blit(value_text, (px - value_text.get_width() // 2, py - 25))
                
                if player.current_bet > 0:
                    ChipDrawer.draw_chip_stack(self.screen, player.current_bet, px, py + 100)
