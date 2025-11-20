"""
Enhanced Blackjack Game - Pyglet/OpenGL Implementation
Full game logic with proper UI matching original Pygame version
"""

import time
import random
from typing import List, Dict, Tuple
from pyglet_renderer import PygletRenderer
from config import PLAYER_COLORS, Colors, HOVER_TIME_THRESHOLD


class BlackjackPlayerEnhanced:
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


class BlackjackPygletEnhanced:
    """Full Blackjack implementation with OpenGL rendering"""
    
    SUITS = ['S', 'H', 'D', 'C']  # Spades, Hearts, Diamonds, Clubs
    RANKS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
    SUIT_SYMBOLS = {'S': '♠', 'H': '♥', 'D': '♦', 'C': '♣'}
    
    def __init__(self, width: int, height: int, renderer: PygletRenderer):
        self.width = width
        self.height = height
        self.renderer = renderer
        
        self.players = []
        self.active_players = []
        self.dealer_hand = []
        self.dealer_reveal = False
        self.deck = []
        
        self.phase = "betting"  # betting, playing, dealer, results
        self.hover_states = {}
        
        # Calculate table geometry
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
        self.active_players = player_indices
        self.players = [BlackjackPlayerEnhanced(i, PLAYER_COLORS[i]) for i in player_indices]
        self.phase = "betting"
        self.dealer_hand = []
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
        
        # Adjust for aces
        while value > 21 and aces > 0:
            value -= 10
            aces -= 1
        
        return value
    
    def _deal_initial_cards(self):
        """Deal initial 2 cards to each player and dealer"""
        # Deal first card to each player
        for player in self.players:
            if player.current_bet > 0:
                player.hand = [self.deck.pop()]
        
        # Deal first card to dealer
        self.dealer_hand = [self.deck.pop()]
        
        # Deal second card to each player
        for player in self.players:
            if player.current_bet > 0:
                player.hand.append(self.deck.pop())
                
                # Check for blackjack
                if self._hand_value(player.hand) == 21:
                    player.is_blackjack = True
                    player.is_standing = True
        
        # Deal second card to dealer
        self.dealer_hand.append(self.deck.pop())
    
    def _hit(self, player: BlackjackPlayerEnhanced):
        """Player takes a card"""
        if len(self.deck) > 0:
            player.hand.append(self.deck.pop())
            if self._hand_value(player.hand) > 21:
                player.is_busted = True
                player.is_standing = True
    
    def _dealer_play(self):
        """Dealer plays according to rules (hit until 17+)"""
        self.dealer_reveal = True
        while self._hand_value(self.dealer_hand) < 17:
            if len(self.deck) > 0:
                self.dealer_hand.append(self.deck.pop())
    
    def update(self, dt: float):
        """Update game state"""
        pass
    
    def handle_input(self, fingertip_meta: List[Dict]) -> bool:
        """Handle player input, returns True if exiting to menu"""
        current_time = time.time()
        active_hovers = set()
        
        # Back button
        back_rect = (self.width // 2 - 100, 50, 200, 60)
        key = "back_btn"
        
        for meta in fingertip_meta:
            pos = meta["pos"]
            
            # Check back button
            if (back_rect[0] <= pos[0] <= back_rect[0] + back_rect[2] and
                back_rect[1] <= pos[1] <= back_rect[1] + back_rect[3]):
                active_hovers.add(key)
                
                if key not in self.hover_states:
                    self.hover_states[key] = {"start_time": current_time, "pos": pos}
                
                hover_duration = current_time - self.hover_states[key]["start_time"]
                if hover_duration >= HOVER_TIME_THRESHOLD:
                    self.hover_states = {}
                    return True
            
            # Betting phase buttons
            if self.phase == "betting":
                self._handle_betting_input(pos, active_hovers, current_time)
            
            # Playing phase buttons
            elif self.phase == "playing":
                self._handle_playing_input(pos, active_hovers, current_time)
            
            # Results phase button
            elif self.phase == "results":
                self._handle_results_input(pos, active_hovers, current_time)
        
        # Remove stale hover states
        for key in list(self.hover_states.keys()):
            if key not in active_hovers:
                del self.hover_states[key]
        
        return False
    
    def _handle_betting_input(self, pos: Tuple[int, int], active_hovers: set, current_time: float):
        """Handle input during betting phase"""
        table_x, table_y, table_size, _ = self.table_rect
        btn_y = table_y + table_size - 150
        
        # Bet $5 button
        bet5_rect = (table_x + table_size // 2 - 250, btn_y, 100, 60)
        if (bet5_rect[0] <= pos[0] <= bet5_rect[0] + bet5_rect[2] and
            bet5_rect[1] <= pos[1] <= bet5_rect[1] + bet5_rect[3]):
            key = "bet5"
            active_hovers.add(key)
            if key not in self.hover_states:
                self.hover_states[key] = {"start_time": current_time, "pos": pos}
            if current_time - self.hover_states[key]["start_time"] >= HOVER_TIME_THRESHOLD:
                if self.players and self.players[0].chips >= 5:
                    self.players[0].chips -= 5
                    self.players[0].current_bet += 5
                del self.hover_states[key]
        
        # Bet $25 button
        bet25_rect = (table_x + table_size // 2 - 120, btn_y, 100, 60)
        if (bet25_rect[0] <= pos[0] <= bet25_rect[0] + bet25_rect[2] and
            bet25_rect[1] <= pos[1] <= bet25_rect[1] + bet25_rect[3]):
            key = "bet25"
            active_hovers.add(key)
            if key not in self.hover_states:
                self.hover_states[key] = {"start_time": current_time, "pos": pos}
            if current_time - self.hover_states[key]["start_time"] >= HOVER_TIME_THRESHOLD:
                if self.players and self.players[0].chips >= 25:
                    self.players[0].chips -= 25
                    self.players[0].current_bet += 25
                del self.hover_states[key]
        
        # Bet $100 button
        bet100_rect = (table_x + table_size // 2 + 20, btn_y, 100, 60)
        if (bet100_rect[0] <= pos[0] <= bet100_rect[0] + bet100_rect[2] and
            bet100_rect[1] <= pos[1] <= bet100_rect[1] + bet100_rect[3]):
            key = "bet100"
            active_hovers.add(key)
            if key not in self.hover_states:
                self.hover_states[key] = {"start_time": current_time, "pos": pos}
            if current_time - self.hover_states[key]["start_time"] >= HOVER_TIME_THRESHOLD:
                if self.players and self.players[0].chips >= 100:
                    self.players[0].chips -= 100
                    self.players[0].current_bet += 100
                del self.hover_states[key]
        
        # Deal button
        deal_rect = (table_x + table_size // 2 + 150, btn_y, 100, 60)
        if (deal_rect[0] <= pos[0] <= deal_rect[0] + deal_rect[2] and
            deal_rect[1] <= pos[1] <= deal_rect[1] + deal_rect[3]):
            key = "deal"
            active_hovers.add(key)
            if key not in self.hover_states:
                self.hover_states[key] = {"start_time": current_time, "pos": pos}
            if current_time - self.hover_states[key]["start_time"] >= HOVER_TIME_THRESHOLD:
                if self.players and self.players[0].current_bet > 0:
                    self._deal_initial_cards()
                    self.phase = "playing"
                del self.hover_states[key]
    
    def _handle_playing_input(self, pos: Tuple[int, int], active_hovers: set, current_time: float):
        """Handle input during playing phase"""
        table_x, table_y, table_size, _ = self.table_rect
        btn_y = table_y + table_size - 150
        
        if self.players and not self.players[0].is_standing:
            # Hit button
            hit_rect = (table_x + table_size // 2 - 180, btn_y, 100, 60)
            if (hit_rect[0] <= pos[0] <= hit_rect[0] + hit_rect[2] and
                hit_rect[1] <= pos[1] <= hit_rect[1] + hit_rect[3]):
                key = "hit"
                active_hovers.add(key)
                if key not in self.hover_states:
                    self.hover_states[key] = {"start_time": current_time, "pos": pos}
                if current_time - self.hover_states[key]["start_time"] >= HOVER_TIME_THRESHOLD:
                    self._hit(self.players[0])
                    del self.hover_states[key]
            
            # Stand button
            stand_rect = (table_x + table_size // 2 - 50, btn_y, 100, 60)
            if (stand_rect[0] <= pos[0] <= stand_rect[0] + stand_rect[2] and
                stand_rect[1] <= pos[1] <= stand_rect[1] + stand_rect[3]):
                key = "stand"
                active_hovers.add(key)
                if key not in self.hover_states:
                    self.hover_states[key] = {"start_time": current_time, "pos": pos}
                if current_time - self.hover_states[key]["start_time"] >= HOVER_TIME_THRESHOLD:
                    self.players[0].is_standing = True
                    self._dealer_play()
                    self._calculate_results()
                    self.phase = "results"
                    del self.hover_states[key]
    
    def _handle_results_input(self, pos: Tuple[int, int], active_hovers: set, current_time: float):
        """Handle input during results phase"""
        table_x, table_y, table_size, _ = self.table_rect
        
        # New Round button
        new_round_rect = (table_x + table_size // 2 - 100, table_y + table_size - 150, 200, 60)
        if (new_round_rect[0] <= pos[0] <= new_round_rect[0] + new_round_rect[2] and
            new_round_rect[1] <= pos[1] <= new_round_rect[1] + new_round_rect[3]):
            key = "new_round"
            active_hovers.add(key)
            if key not in self.hover_states:
                self.hover_states[key] = {"start_time": current_time, "pos": pos}
            if current_time - self.hover_states[key]["start_time"] >= HOVER_TIME_THRESHOLD:
                self._new_round()
                del self.hover_states[key]
    
    def _calculate_results(self):
        """Calculate and apply results"""
        dealer_value = self._hand_value(self.dealer_hand)
        dealer_busted = dealer_value > 21
        
        for player in self.players:
            if player.current_bet == 0:
                continue
            
            player_value = self._hand_value(player.hand)
            
            if player.is_busted:
                # Player loses bet (already deducted)
                pass
            elif player.is_blackjack and not (len(self.dealer_hand) == 2 and self._hand_value(self.dealer_hand) == 21):
                # Player wins 3:2
                player.chips += int(player.current_bet * 2.5)
            elif dealer_busted or player_value > dealer_value:
                # Player wins 1:1
                player.chips += player.current_bet * 2
            elif player_value == dealer_value:
                # Push - return bet
                player.chips += player.current_bet
            # else player loses (bet already deducted)
    
    def _new_round(self):
        """Start a new round"""
        for player in self.players:
            player.hand = []
            player.current_bet = 0
            player.is_standing = False
            player.is_busted = False
            player.is_blackjack = False
        
        self.dealer_hand = []
        self.dealer_reveal = False
        self.phase = "betting"
        
        if len(self.deck) < 20:
            self._create_deck()
    
    def draw(self):
        """Draw the complete Blackjack game"""
        # Background
        self.renderer.draw_rect((25, 35, 25), (0, 0, self.width, self.height))
        
        # Table (green felt)
        self.renderer.draw_rect((20, 80, 40), self.table_rect)
        self.renderer.draw_rect((100, 150, 100), self.table_rect, width=4)
        
        # Draw dealer area
        self._draw_dealer_area()
        
        # Draw player area
        self._draw_player_area()
        
        # Draw buttons based on phase
        self._draw_phase_buttons()
        
        # Back button
        self._draw_back_button()
        
        # Draw hover indicators
        self._draw_hover_indicators()
    
    def _draw_dealer_area(self):
        """Draw dealer's cards and info"""
        table_x, table_y, table_size, _ = self.table_rect
        dealer_x = table_x + table_size // 2
        dealer_y = table_y + 150
        
        # Dealer label
        self.renderer.draw_text(
            "Dealer",
            dealer_x, dealer_y - 50,
            font_name='Arial', font_size=32,
            color=(255, 255, 200),
            anchor_x='center', anchor_y='center'
        )
        
        # Draw dealer cards
        if self.dealer_hand:
            card_spacing = 25
            start_x = dealer_x - (len(self.dealer_hand) * card_spacing) // 2
            
            for i, card in enumerate(self.dealer_hand):
                face_down = (i == 1 and not self.dealer_reveal)
                self._draw_card(card, start_x + i * card_spacing, dealer_y, face_down)
            
            # Show dealer's hand value if revealed
            if self.dealer_reveal:
                dealer_value = self._hand_value(self.dealer_hand)
                value_color = (255, 100, 100) if dealer_value > 21 else (200, 255, 200)
                self.renderer.draw_text(
                    str(dealer_value),
                    dealer_x, dealer_y + 60,
                    font_name='Arial', font_size=28,
                    color=value_color,
                    anchor_x='center', anchor_y='center'
                )
    
    def _draw_player_area(self):
        """Draw player's cards and info"""
        if not self.players:
            return
        
        player = self.players[0]
        table_x, table_y, table_size, _ = self.table_rect
        player_x = table_x + table_size // 2
        player_y = table_y + table_size - 250
        
        # Player info
        self.renderer.draw_text(
            f"Player 1 - ${player.chips}",
            player_x, player_y - 50,
            font_name='Arial', font_size=24,
            color=player.color,
            anchor_x='center', anchor_y='center'
        )
        
        if player.current_bet > 0:
            self.renderer.draw_text(
                f"Bet: ${player.current_bet}",
                player_x, player_y - 80,
                font_name='Arial', font_size=20,
                color=(255, 255, 100),
                anchor_x='center', anchor_y='center'
            )
        
        # Draw player cards
        if player.hand:
            card_spacing = 25
            start_x = player_x - (len(player.hand) * card_spacing) // 2
            
            for i, card in enumerate(player.hand):
                self._draw_card(card, start_x + i * card_spacing, player_y, False)
            
            # Show player's hand value
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
                font_name='Arial', font_size=28,
                color=value_color,
                anchor_x='center', anchor_y='center'
            )
    
    def _draw_card(self, card: Tuple[str, str], x: int, y: int, face_down: bool):
        """Draw a playing card"""
        card_width = 60
        card_height = 85
        
        if face_down:
            # Card back
            self.renderer.draw_rect((50, 80, 150), (x, y, card_width, card_height))
            self.renderer.draw_rect((255, 255, 255), (x, y, card_width, card_height), width=3)
            
            # Pattern on back
            for i in range(3):
                for j in range(4):
                    dot_x = x + 15 + i * 15
                    dot_y = y + 15 + j * 18
                    self.renderer.draw_circle((80, 110, 180), (dot_x, dot_y), 3)
        else:
            rank, suit = card
            is_red = suit in ['H', 'D']
            card_color = (220, 50, 50) if is_red else (30, 30, 30)
            
            # Card face
            self.renderer.draw_rect((255, 255, 255), (x, y, card_width, card_height))
            self.renderer.draw_rect((200, 200, 200), (x, y, card_width, card_height), width=2)
            
            # Rank (top-left)
            self.renderer.draw_text(
                rank, x + 8, y + card_height - 10,
                font_name='Arial', font_size=24,
                color=card_color,
                anchor_x='left', anchor_y='top'
            )
            
            # Suit (center)
            suit_symbol = self.SUIT_SYMBOLS[suit]
            self.renderer.draw_text(
                suit_symbol, x + card_width // 2, y + card_height // 2,
                font_name='Arial', font_size=36,
                color=card_color,
                anchor_x='center', anchor_y='center'
            )
    
    def _draw_phase_buttons(self):
        """Draw buttons based on current phase"""
        table_x, table_y, table_size, _ = self.table_rect
        btn_y = table_y + table_size - 150
        
        if self.phase == "betting":
            # Bet buttons
            self.renderer.draw_rect((80, 80, 150), (table_x + table_size // 2 - 250, btn_y, 100, 60))
            self.renderer.draw_text("$5", table_x + table_size // 2 - 200, btn_y + 30,
                                   font_name='Arial', font_size=24, color=(255, 255, 255),
                                   anchor_x='center', anchor_y='center')
            
            self.renderer.draw_rect((80, 80, 150), (table_x + table_size // 2 - 120, btn_y, 100, 60))
            self.renderer.draw_text("$25", table_x + table_size // 2 - 70, btn_y + 30,
                                   font_name='Arial', font_size=24, color=(255, 255, 255),
                                   anchor_x='center', anchor_y='center')
            
            self.renderer.draw_rect((80, 80, 150), (table_x + table_size // 2 + 20, btn_y, 100, 60))
            self.renderer.draw_text("$100", table_x + table_size // 2 + 70, btn_y + 30,
                                   font_name='Arial', font_size=24, color=(255, 255, 255),
                                   anchor_x='center', anchor_y='center')
            
            # Deal button
            deal_active = self.players and self.players[0].current_bet > 0
            deal_color = (80, 150, 80) if deal_active else (100, 100, 100)
            self.renderer.draw_rect(deal_color, (table_x + table_size // 2 + 150, btn_y, 100, 60))
            self.renderer.draw_text("Deal", table_x + table_size // 2 + 200, btn_y + 30,
                                   font_name='Arial', font_size=24, color=(255, 255, 255),
                                   anchor_x='center', anchor_y='center')
        
        elif self.phase == "playing":
            if self.players and not self.players[0].is_standing:
                # Hit button
                self.renderer.draw_rect((80, 150, 80), (table_x + table_size // 2 - 180, btn_y, 100, 60))
                self.renderer.draw_text("Hit", table_x + table_size // 2 - 130, btn_y + 30,
                                       font_name='Arial', font_size=24, color=(255, 255, 255),
                                       anchor_x='center', anchor_y='center')
                
                # Stand button
                self.renderer.draw_rect((150, 80, 80), (table_x + table_size // 2 - 50, btn_y, 100, 60))
                self.renderer.draw_text("Stand", table_x + table_size // 2, btn_y + 30,
                                       font_name='Arial', font_size=24, color=(255, 255, 255),
                                       anchor_x='center', anchor_y='center')
        
        elif self.phase == "results":
            # New Round button
            self.renderer.draw_rect((80, 120, 180), (table_x + table_size // 2 - 100, btn_y, 200, 60))
            self.renderer.draw_text("New Round", table_x + table_size // 2, btn_y + 30,
                                   font_name='Arial', font_size=24, color=(255, 255, 255),
                                   anchor_x='center', anchor_y='center')
    
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
