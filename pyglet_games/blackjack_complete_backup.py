"""
Complete Blackjack Game - Pyglet/OpenGL Implementation
Full game with player selection, player panels, and complete UI
"""

import time
import random
from typing import List, Dict, Tuple
from pyglet_games.renderer import PygletRenderer
from config import PLAYER_COLORS, Colors, HOVER_TIME_THRESHOLD
from pyglet_games.player_panels import calculate_all_panels, PlayerPanel
from pyglet_games.player_selection import PlayerSelectionUI


class BlackjackPlayer:
    def __init__(self, idx: int, color: Tuple[int, int, int]):
        self.idx = idx
        self.color = color
        self.chips = 1000
        self.current_bet = 0
        self.hand = []
        self.is_standing = False
        self.is_busted = False
        self.is_blackjack = False
        self.is_ready = False


class BlackjackGame:
    """Complete Blackjack implementation with OpenGL rendering"""
    
    SUITS = ['S', 'H', 'D', 'C']
    RANKS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
    SUIT_SYMBOLS = {'S': '♠', 'H': '♥', 'D': '♦', 'C': '♣'}
    
    def __init__(self, width: int, height: int, renderer: PygletRenderer):
        self.width = width
        self.height = height
        self.renderer = renderer
        
        # Game state
        self.state = "player_select"  # player_select, betting, playing, dealer, results
        self.selection_ui = PlayerSelectionUI(width, height)
        
        # Players and panels
        self.players = []
        self.active_players = []
        self.current_player_idx = 0
        self.panels = calculate_all_panels(width, height)
        
        # Game data
        self.dealer_hand = []
        self.dealer_reveal = False
        self.deck = []
        
        # Hover states
        self.hover_states = {}
        
        # Calculate geometry
        self._calculate_table_geometry()
    
    def _calculate_table_geometry(self):
        """Calculate table size and position"""
        horizontal_panel_height = int(self.height * 0.10)
        vertical_panel_width = int(self.width * 0.12)
        margin = 20
        
        available_width = self.width - (2 * vertical_panel_width) - (2 * margin)
        available_height = self.height - (2 * horizontal_panel_height) - (2 * margin)
        
        table_size = min(available_width, available_height)
        table_x = vertical_panel_width + margin + (available_width - table_size) // 2
        table_y = horizontal_panel_height + margin + (available_height - table_size) // 2
        
        self.table_rect = (table_x, table_y, table_size, table_size)
    
    def start_game(self, player_indices: List[int]):
        """Initialize game with selected players"""
        self.active_players = sorted(player_indices)
        self.players = [BlackjackPlayer(i, PLAYER_COLORS[i]) for i in player_indices]
        self.current_player_idx = 0
        self.state = "betting"
        self._create_deck()
    
    def _create_deck(self):
        """Create and shuffle a deck of cards"""
        self.deck = [(rank, suit) for suit in self.SUITS for rank in self.RANKS]
        random.shuffle(self.deck)
    
    def _card_value(self, card: Tuple[str, str]) -> int:
        """Get numeric value of a card"""
        rank = card[0]
        if rank in ['J', 'Q', 'K']:
            return 10
        elif rank == 'A':
            return 11
        else:
            return int(rank)
    
    def _hand_value(self, hand: List[Tuple[str, str]]) -> int:
        """Calculate total value of a hand, accounting for aces"""
        value = sum(self._card_value(card) for card in hand)
        aces = sum(1 for card in hand if card[0] == 'A')
        
        while value > 21 and aces > 0:
            value -= 10
            aces -= 1
        
        return value
    
    def _deal_initial_cards(self):
        """Deal initial 2 cards to each player and dealer"""
        # Reset hands
        for player in self.players:
            player.hand = []
            player.is_standing = False
            player.is_busted = False
            player.is_blackjack = False
        
        self.dealer_hand = []
        
        # Deal first card to players with bets
        for player in self.players:
            if player.current_bet > 0:
                player.hand = [self.deck.pop()]
        
        # Dealer first card
        self.dealer_hand = [self.deck.pop()]
        
        # Deal second card
        for player in self.players:
            if player.current_bet > 0:
                player.hand.append(self.deck.pop())
                if self._hand_value(player.hand) == 21:
                    player.is_blackjack = True
                    player.is_standing = True
        
        # Dealer second card
        self.dealer_hand.append(self.deck.pop())
    
    def _hit(self, player: BlackjackPlayer):
        """Player takes a card"""
        if len(self.deck) > 0:
            player.hand.append(self.deck.pop())
            if self._hand_value(player.hand) > 21:
                player.is_busted = True
                player.is_standing = True
    
    def _dealer_play(self):
        """Dealer plays according to rules"""
        self.dealer_reveal = True
        while self._hand_value(self.dealer_hand) < 17:
            if len(self.deck) > 0:
                self.dealer_hand.append(self.deck.pop())
    
    def _calculate_results(self):
        """Calculate and apply results"""
        dealer_value = self._hand_value(self.dealer_hand)
        dealer_busted = dealer_value > 21
        
        for player in self.players:
            if player.current_bet == 0:
                continue
            
            player_value = self._hand_value(player.hand)
            
            if player.is_busted:
                pass  # Lose bet
            elif player.is_blackjack and not (len(self.dealer_hand) == 2 and self._hand_value(self.dealer_hand) == 21):
                player.chips += int(player.current_bet * 2.5)  # 3:2 payout
            elif dealer_busted or player_value > dealer_value:
                player.chips += player.current_bet * 2  # Win
            elif player_value == dealer_value:
                player.chips += player.current_bet  # Push
    
    def _new_round(self):
        """Start a new round"""
        for player in self.players:
            player.hand = []
            player.current_bet = 0
            player.is_standing = False
            player.is_busted = False
            player.is_blackjack = False
            player.is_ready = False
        
        self.dealer_hand = []
        self.dealer_reveal = False
        self.state = "betting"
        
        if len(self.deck) < 20:
            self._create_deck()
    
    def update(self, dt: float):
        """Update game state"""
        pass
    
    def handle_input(self, fingertip_meta: List[Dict]) -> bool:
        """Handle player input, returns True if exiting to menu"""
        if self.state == "player_select":
            return self._handle_player_select_input(fingertip_meta)
        elif self.state in ["betting", "playing", "results"]:
            return self._handle_game_input(fingertip_meta)
        return False
    
    def _handle_player_select_input(self, fingertip_meta: List[Dict]) -> bool:
        """Handle player selection input"""
        current_time = time.time()
        active_hovers = set()
        
        self.selection_ui.update_with_fingertips(fingertip_meta)
        
        for meta in fingertip_meta:
            pos = meta["pos"]
            
            # Back button
            back_rect = (self.width // 2 - 100, 50, 200, 60)
            if (back_rect[0] <= pos[0] <= back_rect[0] + back_rect[2] and
                back_rect[1] <= pos[1] <= back_rect[1] + back_rect[3]):
                key = "back_btn"
                active_hovers.add(key)
                if key not in self.hover_states:
                    self.hover_states[key] = {"start_time": current_time, "pos": pos}
                if current_time - self.hover_states[key]["start_time"] >= HOVER_TIME_THRESHOLD:
                    self.hover_states = {}
                    return True
            
            # Start button
            start_rect = (self.width // 2 - 140, self.height // 2 - 45, 280, 90)
            if (start_rect[0] <= pos[0] <= start_rect[0] + start_rect[2] and
                start_rect[1] <= pos[1] <= start_rect[1] + start_rect[3]):
                if self.selection_ui.selected_count() >= 2:
                    key = "start_btn"
                    active_hovers.add(key)
                    if key not in self.hover_states:
                        self.hover_states[key] = {"start_time": current_time, "pos": pos}
                    if current_time - self.hover_states[key]["start_time"] >= HOVER_TIME_THRESHOLD:
                        self.start_game(self.selection_ui.get_selected_indices())
                        self.hover_states = {}
        
        for key in list(self.hover_states.keys()):
            if key not in active_hovers:
                del self.hover_states[key]
        
        return False
    
    def _handle_game_input(self, fingertip_meta: List[Dict]) -> bool:
        """Handle game input"""
        current_time = time.time()
        active_hovers = set()
        
        table_x, table_y, table_size, _ = self.table_rect
        
        for meta in fingertip_meta:
            pos = meta["pos"]
            
            # Back button
            back_rect = (self.width // 2 - 100, 50, 200, 60)
            if (back_rect[0] <= pos[0] <= back_rect[0] + back_rect[2] and
                back_rect[1] <= pos[1] <= back_rect[1] + back_rect[3]):
                key = "back_btn"
                active_hovers.add(key)
                if key not in self.hover_states:
                    self.hover_states[key] = {"start_time": current_time, "pos": pos}
                if current_time - self.hover_states[key]["start_time"] >= HOVER_TIME_THRESHOLD:
                    self.hover_states = {}
                    return True
            
            # Betting phase buttons
            if self.state == "betting":
                # Check each player's panel for bet buttons
                for player in self.players:
                    panel = self.panels[player.idx]
                    if not player.is_ready:
                        # Simplified: bet buttons in panel area
                        bet_y = panel.y + panel.height // 2
                        
                        # Bet $25 button (simplified to one button)
                        bet_rect = (panel.x + 10, bet_y, panel.width - 20, 40)
                        if (bet_rect[0] <= pos[0] <= bet_rect[0] + bet_rect[2] and
                            bet_rect[1] <= pos[1] <= bet_rect[1] + bet_rect[3]):
                            key = f"bet_{player.idx}"
                            active_hovers.add(key)
                            if key not in self.hover_states:
                                self.hover_states[key] = {"start_time": current_time, "pos": pos}
                            if current_time - self.hover_states[key]["start_time"] >= HOVER_TIME_THRESHOLD:
                                if player.chips >= 25:
                                    player.chips -= 25
                                    player.current_bet += 25
                                    player.is_ready = True
                                del self.hover_states[key]
                
                # Deal button (center)
                if all(p.is_ready for p in self.players):
                    deal_rect = (table_x + table_size // 2 - 80, table_y + table_size - 100, 160, 60)
                    if (deal_rect[0] <= pos[0] <= deal_rect[0] + deal_rect[2] and
                        deal_rect[1] <= pos[1] <= deal_rect[1] + deal_rect[3]):
                        key = "deal_btn"
                        active_hovers.add(key)
                        if key not in self.hover_states:
                            self.hover_states[key] = {"start_time": current_time, "pos": pos}
                        if current_time - self.hover_states[key]["start_time"] >= HOVER_TIME_THRESHOLD:
                            self._deal_initial_cards()
                            self.state = "playing"
                            self.current_player_idx = 0
                            del self.hover_states[key]
            
            # Playing phase buttons
            elif self.state == "playing":
                current_player = self.players[self.current_player_idx]
                if not current_player.is_standing:
                    # Hit/Stand buttons in center
                    hit_rect = (table_x + table_size // 2 - 160, table_y + table_size - 100, 140, 60)
                    stand_rect = (table_x + table_size // 2 + 20, table_y + table_size - 100, 140, 60)
                    
                    if (hit_rect[0] <= pos[0] <= hit_rect[0] + hit_rect[2] and
                        hit_rect[1] <= pos[1] <= hit_rect[1] + hit_rect[3]):
                        key = "hit_btn"
                        active_hovers.add(key)
                        if key not in self.hover_states:
                            self.hover_states[key] = {"start_time": current_time, "pos": pos}
                        if current_time - self.hover_states[key]["start_time"] >= HOVER_TIME_THRESHOLD:
                            self._hit(current_player)
                            if current_player.is_standing or current_player.is_busted:
                                self._advance_to_next_player()
                            del self.hover_states[key]
                    
                    if (stand_rect[0] <= pos[0] <= stand_rect[0] + stand_rect[2] and
                        stand_rect[1] <= pos[1] <= stand_rect[1] + stand_rect[3]):
                        key = "stand_btn"
                        active_hovers.add(key)
                        if key not in self.hover_states:
                            self.hover_states[key] = {"start_time": current_time, "pos": pos}
                        if current_time - self.hover_states[key]["start_time"] >= HOVER_TIME_THRESHOLD:
                            current_player.is_standing = True
                            self._advance_to_next_player()
                            del self.hover_states[key]
            
            # Results phase
            elif self.state == "results":
                new_round_rect = (table_x + table_size // 2 - 100, table_y + table_size - 100, 200, 60)
                if (new_round_rect[0] <= pos[0] <= new_round_rect[0] + new_round_rect[2] and
                    new_round_rect[1] <= pos[1] <= new_round_rect[1] + new_round_rect[3]):
                    key = "new_round_btn"
                    active_hovers.add(key)
                    if key not in self.hover_states:
                        self.hover_states[key] = {"start_time": current_time, "pos": pos}
                    if current_time - self.hover_states[key]["start_time"] >= HOVER_TIME_THRESHOLD:
                        self._new_round()
                        del self.hover_states[key]
        
        for key in list(self.hover_states.keys()):
            if key not in active_hovers:
                del self.hover_states[key]
        
        return False
    
    def _advance_to_next_player(self):
        """Move to next player or dealer"""
        self.current_player_idx += 1
        if self.current_player_idx >= len(self.players):
            # All players done, dealer plays
            self._dealer_play()
            self._calculate_results()
            self.state = "results"
        else:
            # Next player
            if self.players[self.current_player_idx].is_standing:
                self._advance_to_next_player()
    
    def draw(self):
        """Draw the complete Blackjack game"""
        if self.state == "player_select":
            self._draw_player_select()
        else:
            self._draw_game()
    
    def _draw_player_select(self):
        """Draw player selection screen"""
        # Similar to Monopoly player selection
        self.renderer.draw_rect((25, 35, 25), (0, 0, self.width, self.height))
        
        panel_rect = (80, 60, self.width - 160, self.height - 120)
        self.renderer.draw_rect(Colors.PANEL, panel_rect)
        
        self.renderer.draw_text(
            "Select Players (2-8)",
            self.width // 2, self.height - 90,
            font_name='Arial', font_size=48,
            color=Colors.WHITE,
            anchor_x='center', anchor_y='center'
        )
        
        for i, (x, y, w, h) in enumerate(self.selection_ui.slots):
            color = PLAYER_COLORS[i]
            washed = tuple(min(255, int(c * 0.7 + 180 * 0.3)) for c in color)
            
            if self.selection_ui.selected[i]:
                self.renderer.draw_rect(color, (x, y, w, h))
                self.renderer.draw_rect((255, 255, 255), (x, y, w, h), width=4)
            else:
                self.renderer.draw_rect(washed, (x, y, w, h))
                self.renderer.draw_rect((150, 150, 150), (x, y, w, h), width=2)
            
            self.renderer.draw_text(
                f"Player {i + 1}",
                x + w // 2, y + h // 2,
                font_name='Arial', font_size=32,
                color=(255, 255, 255),
                anchor_x='center', anchor_y='center'
            )
            
            status = "SELECTED" if self.selection_ui.selected[i] else "Touch to Select"
            self.renderer.draw_text(
                status,
                x + w // 2, y + 30,
                font_name='Arial', font_size=18,
                color=(255, 255, 255),
                anchor_x='center', anchor_y='center'
            )
        
        start_rect = (self.width // 2 - 140, self.height // 2 - 45, 280, 90)
        selected_count = self.selection_ui.selected_count()
        can_start = selected_count >= 2
        btn_color = (80, 150, 80) if can_start else (100, 100, 100)
        
        self.renderer.draw_rect(btn_color, start_rect)
        self.renderer.draw_rect((200, 200, 200), start_rect, width=3)
        self.renderer.draw_text(
            "Start Game",
            self.width // 2, self.height // 2,
            font_name='Arial', font_size=36,
            color=(255, 255, 255),
            anchor_x='center', anchor_y='center'
        )
        
        self.renderer.draw_text(
            f"{selected_count} players selected",
            self.width // 2, self.height // 2 - 100,
            font_name='Arial', font_size=24,
            color=(255, 255, 255),
            anchor_x='center', anchor_y='center'
        )
        
        if selected_count < 2:
            self.renderer.draw_text(
                "Minimum 2 players required",
                self.width // 2, self.height // 2 - 130,
                font_name='Arial', font_size=20,
                color=(255, 200, 200),
                anchor_x='center', anchor_y='center'
            )
        
        self._draw_back_button()
        self._draw_hover_indicators()
    
    def _draw_game(self):
        """Draw game screen"""
        self.renderer.draw_rect((25, 35, 25), (0, 0, self.width, self.height))
        
        # Draw player panels
        self._draw_player_panels()
        
        # Draw table
        self.renderer.draw_rect((20, 80, 40), self.table_rect)
        self.renderer.draw_rect((100, 150, 100), self.table_rect, width=4)
        
        # Draw dealer area
        self._draw_dealer_area()
        
        # Draw player cards on table
        self._draw_player_cards_on_table()
        
        # Draw game buttons
        self._draw_game_buttons()
        
        self._draw_back_button()
        self._draw_hover_indicators()
    
    def _draw_player_panels(self):
        """Draw all player panels"""
        for player in self.players:
            panel = self.panels[player.idx]
            
            washed = tuple(min(255, int(c * 0.75 + 180 * 0.25)) for c in player.color)
            self.renderer.draw_rect(washed, (panel.x, panel.y, panel.width, panel.height))
            
            if self.state == "playing" and player.idx == self.players[self.current_player_idx].idx:
                self.renderer.draw_rect(Colors.GOLD, (panel.x, panel.y, panel.width, panel.height), width=4)
            else:
                self.renderer.draw_rect((150, 150, 150), (panel.x, panel.y, panel.width, panel.height), width=2)
            
            cx, cy = panel.get_center()
            info_y = panel.y + 25 if panel.side in ['bottom', 'left', 'right'] else panel.y + panel.height - 25
            
            self.renderer.draw_text(
                f"P{player.idx + 1}",
                cx, info_y,
                font_name='Arial', font_size=16,
                color=(255, 255, 255),
                anchor_x='center', anchor_y='center'
            )
            self.renderer.draw_text(
                f"${player.chips}",
                cx, info_y - 20 if panel.side == 'bottom' else info_y + 20,
                font_name='Arial', font_size=18,
                color=(255, 255, 100),
                anchor_x='center', anchor_y='center'
            )
            if player.current_bet > 0:
                self.renderer.draw_text(
                    f"Bet: ${player.current_bet}",
                    cx, info_y - 38 if panel.side == 'bottom' else info_y + 38,
                    font_name='Arial', font_size=14,
                    color=(100, 255, 100),
                    anchor_x='center', anchor_y='center'
                )
            
            # Draw betting buttons in panel for betting phase
            if self.state == "betting" and not player.is_ready:
                btn_y = panel.y + panel.height - 60 if panel.side == 'bottom' else panel.y + 60
                btn_width = min(panel.width - 20, 80)
                btn_x = panel.x + (panel.width - btn_width) // 2
                
                # Bet button
                self.renderer.draw_rect((80, 120, 180), (btn_x, btn_y, btn_width, 35))
                self.renderer.draw_rect((150, 180, 220), (btn_x, btn_y, btn_width, 35), width=2)
                self.renderer.draw_text(
                    "Bet $25",
                    btn_x + btn_width // 2, btn_y + 17,
                    font_name='Arial', font_size=14,
                    color=(255, 255, 255),
                    anchor_x='center', anchor_y='center'
                )
            elif self.state == "betting" and player.is_ready:
                ready_y = panel.y + panel.height - 60 if panel.side == 'bottom' else panel.y + 60
                self.renderer.draw_text(
                    "READY",
                    cx, ready_y,
                    font_name='Arial', font_size=16,
                    color=(100, 255, 100),
                    anchor_x='center', anchor_y='center'
                )
    
    def _draw_dealer_area(self):
        """Draw dealer cards"""
        table_x, table_y, table_size, _ = self.table_rect
        dealer_x = table_x + table_size // 2
        dealer_y = table_y + 120
        
        self.renderer.draw_text(
            "Dealer",
            dealer_x, dealer_y - 40,
            font_name='Arial', font_size=28,
            color=(255, 255, 200),
            anchor_x='center', anchor_y='center'
        )
        
        if self.dealer_hand:
            card_spacing = 25
            start_x = dealer_x - (len(self.dealer_hand) * card_spacing) // 2
            
            for i, card in enumerate(self.dealer_hand):
                face_down = (i == 1 and not self.dealer_reveal)
                self._draw_card(card, start_x + i * card_spacing, dealer_y, face_down)
            
            if self.dealer_reveal:
                dealer_value = self._hand_value(self.dealer_hand)
                value_color = (255, 100, 100) if dealer_value > 21 else (200, 255, 200)
                self.renderer.draw_text(
                    str(dealer_value),
                    dealer_x, dealer_y + 60,
                    font_name='Arial', font_size=24,
                    color=value_color,
                    anchor_x='center', anchor_y='center'
                )
    
    def _draw_player_cards_on_table(self):
        """Draw player hands on table"""
        table_x, table_y, table_size, _ = self.table_rect
        player_y = table_y + table_size - 250
        
        # Simplified: draw current player's hand in center
        if self.state in ["playing", "results"] and self.players:
            if self.state == "playing":
                player = self.players[self.current_player_idx]
            else:
                player = self.players[0]  # Show first player in results
            
            if player.hand:
                player_x = table_x + table_size // 2
                card_spacing = 25
                start_x = player_x - (len(player.hand) * card_spacing) // 2
                
                for i, card in enumerate(player.hand):
                    self._draw_card(card, start_x + i * card_spacing, player_y, False)
                
                player_value = self._hand_value(player.hand)
                if player.is_blackjack:
                    value_text = "BLACKJACK!"
                    value_color = (255, 215, 0)
                elif player.is_busted:
                    value_text = "BUST!"
                    value_color = (255, 100, 100)
                else:
                    value_text = str(player_value)
                    value_color = (200, 255, 200)
                
                self.renderer.draw_text(
                    value_text,
                    player_x, player_y + 60,
                    font_name='Arial', font_size=24,
                    color=value_color,
                    anchor_x='center', anchor_y='center'
                )
    
    def _draw_card(self, card: Tuple[str, str], x: int, y: int, face_down: bool):
        """Draw a playing card"""
        card_width = 60
        card_height = 85
        
        if face_down:
            self.renderer.draw_rect((50, 80, 150), (x, y, card_width, card_height))
            self.renderer.draw_rect((255, 255, 255), (x, y, card_width, card_height), width=3)
            
            for i in range(3):
                for j in range(4):
                    dot_x = x + 15 + i * 15
                    dot_y = y + 15 + j * 18
                    self.renderer.draw_circle((80, 110, 180), (dot_x, dot_y), 3)
        else:
            rank, suit = card
            is_red = suit in ['H', 'D']
            card_color = (220, 50, 50) if is_red else (30, 30, 30)
            
            self.renderer.draw_rect((255, 255, 255), (x, y, card_width, card_height))
            self.renderer.draw_rect((200, 200, 200), (x, y, card_width, card_height), width=2)
            
            self.renderer.draw_text(
                rank, x + 8, y + card_height - 10,
                font_name='Arial', font_size=20,
                color=card_color,
                anchor_x='left', anchor_y='top'
            )
            
            suit_symbol = self.SUIT_SYMBOLS[suit]
            self.renderer.draw_text(
                suit_symbol, x + card_width // 2, y + card_height // 2,
                font_name='Arial', font_size=32,
                color=card_color,
                anchor_x='center', anchor_y='center'
            )
    
    def _draw_game_buttons(self):
        """Draw game phase buttons"""
        table_x, table_y, table_size, _ = self.table_rect
        
        if self.state == "betting":
            # Bet buttons in panels (already handled in input)
            # Show deal button if all ready
            if all(p.is_ready for p in self.players):
                deal_rect = (table_x + table_size // 2 - 80, table_y + table_size - 100, 160, 60)
                self.renderer.draw_rect((80, 150, 80), deal_rect)
                self.renderer.draw_text(
                    "Deal",
                    table_x + table_size // 2, table_y + table_size - 70,
                    font_name='Arial', font_size=24,
                    color=(255, 255, 255),
                    anchor_x='center', anchor_y='center'
                )
        
        elif self.state == "playing":
            if self.players and not self.players[self.current_player_idx].is_standing:
                hit_rect = (table_x + table_size // 2 - 160, table_y + table_size - 100, 140, 60)
                stand_rect = (table_x + table_size // 2 + 20, table_y + table_size - 100, 140, 60)
                
                self.renderer.draw_rect((80, 150, 80), hit_rect)
                self.renderer.draw_text(
                    "Hit",
                    table_x + table_size // 2 - 90, table_y + table_size - 70,
                    font_name='Arial', font_size=24,
                    color=(255, 255, 255),
                    anchor_x='center', anchor_y='center'
                )
                
                self.renderer.draw_rect((150, 80, 80), stand_rect)
                self.renderer.draw_text(
                    "Stand",
                    table_x + table_size // 2 + 90, table_y + table_size - 70,
                    font_name='Arial', font_size=24,
                    color=(255, 255, 255),
                    anchor_x='center', anchor_y='center'
                )
        
        elif self.state == "results":
            new_round_rect = (table_x + table_size // 2 - 100, table_y + table_size - 100, 200, 60)
            self.renderer.draw_rect((80, 120, 180), new_round_rect)
            self.renderer.draw_text(
                "New Round",
                table_x + table_size // 2, table_y + table_size - 70,
                font_name='Arial', font_size=24,
                color=(255, 255, 255),
                anchor_x='center', anchor_y='center'
            )
    
    def _draw_back_button(self):
        """Draw back to menu button"""
        back_rect = (self.width // 2 - 100, 50, 200, 60)
        self.renderer.draw_rect((120, 60, 60), back_rect)
        self.renderer.draw_rect((200, 100, 100), back_rect, width=2)
        self.renderer.draw_text(
            "Back to Menu",
            self.width // 2, 80,
            font_name='Arial', font_size=24,
            color=(255, 255, 255),
            anchor_x='center', anchor_y='center'
        )
    
    def _draw_hover_indicators(self):
        """Draw circular progress indicators for hover states"""
        current_time = time.time()
        
        for key, state in self.hover_states.items():
            hover_duration = current_time - state["start_time"]
            progress = min(1.0, hover_duration / HOVER_TIME_THRESHOLD)
            pos = state["pos"]
            self.renderer.draw_circular_progress(pos, 25, progress, Colors.ACCENT, thickness=6)
        
        if self.state == "player_select":
            for hover_info in self.selection_ui.get_hover_progress():
                x, y = hover_info["pos"]
                self.renderer.draw_circular_progress((x + 28, y - 28), 20, hover_info["progress"], Colors.ACCENT, thickness=6)
