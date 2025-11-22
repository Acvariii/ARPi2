"""
Complete Blackjack Game - Full Redesign with Proper Casino Rules
Features:
- Sequential turn-based gameplay (one player at a time)
- Proper betting with chip denominations ($5, $25, $100, $500)
- Full blackjack rules (hit, stand, double down, split, insurance)
- Dealer follows standard rules (hit on 16, stand on 17)
- Animated card dealing
- Professional casino-style UI
"""

import time
import random
from typing import List, Dict, Tuple, Optional
from pyglet_games.renderer import PygletRenderer
from config import PLAYER_COLORS, Colors, HOVER_TIME_THRESHOLD
from pyglet_games.player_selection import PlayerSelectionUI
from pyglet_games.ui_components_pyglet import PygletButton, PlayerPanel, calculate_all_panels
from pyglet_games.popup_system import UniversalPopup


class Card:
    """Playing card"""
    SUITS = ['♠', '♥', '♦', '♣']
    RANKS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
    
    def __init__(self, rank: str, suit: str):
        self.rank = rank
        self.suit = suit
    
    def value(self, current_total: int = 0) -> int:
        """Get card value for blackjack"""
        if self.rank in ['J', 'Q', 'K']:
            return 10
        elif self.rank == 'A':
            return 11 if current_total + 11 <= 21 else 1
        else:
            return int(self.rank)
    
    def __repr__(self):
        return f"{self.rank}{self.suit}"


class Hand:
    """Blackjack hand"""
    def __init__(self):
        self.cards: List[Card] = []
        self.bet = 0
        self.is_standing = False
        self.is_busted = False
        self.is_doubled = False
        self.is_split = False
    
    def add_card(self, card: Card):
        self.cards.append(card)
    
    def value(self) -> int:
        """Calculate hand value with ace logic"""
        total = 0
        aces = 0
        
        for card in self.cards:
            if card.rank == 'A':
                aces += 1
                total += 11
            elif card.rank in ['J', 'Q', 'K']:
                total += 10
            else:
                total += int(card.rank)
        
        # Adjust for aces
        while total > 21 and aces > 0:
            total -= 10
            aces -= 1
        
        return total
    
    def is_blackjack(self) -> bool:
        """Natural 21 with first 2 cards"""
        return len(self.cards) == 2 and self.value() == 21
    
    def is_soft(self) -> bool:
        """Has an ace counted as 11"""
        total_hard = sum(10 if c.rank in ['J','Q','K'] else (1 if c.rank == 'A' else int(c.rank)) for c in self.cards)
        return any(c.rank == 'A' for c in self.cards) and self.value() != total_hard


class BlackjackPlayer:
    """Player in blackjack game"""
    def __init__(self, idx: int, color: Tuple[int, int, int]):
        self.idx = idx
        self.color = color
        self.chips = 1000
        self.hands: List[Hand] = []
        self.current_hand_idx = 0
        self.is_active = True
        self.insurance_bet = 0
        self.current_bet = 0  # Bet being placed during betting phase
        self.is_ready = False  # Ready state for simultaneous actions
        self.is_bankrupt = False  # Marked when player runs out of chips
    
    def can_bet(self, amount: int) -> bool:
        return self.chips >= amount
    
    def place_bet(self, amount: int) -> bool:
        if self.can_bet(amount):
            self.chips -= amount
            return True
        return False
    
    def get_current_hand(self) -> Optional[Hand]:
        if 0 <= self.current_hand_idx < len(self.hands):
            return self.hands[self.current_hand_idx]
        return None
    
    def next_hand(self) -> bool:
        """Move to next hand, return True if more hands exist"""
        self.current_hand_idx += 1
        return self.current_hand_idx < len(self.hands)
    
    def reset_for_round(self):
        """Reset for new round"""
        self.hands = []
        self.current_hand_idx = 0
        self.insurance_bet = 0
        self.current_bet = 0
        self.is_ready = False


class BlackjackGame:
    """Complete Blackjack game with proper casino rules"""
    
    def __init__(self, width: int, height: int, renderer: PygletRenderer):
        self.width = width
        self.height = height
        self.renderer = renderer
        
        # Game state
        self.state = "player_select"  # player_select, betting, playing, dealer_turn, results
        self.selection_ui = PlayerSelectionUI(width, height)
        
        # Players
        self.players: List[BlackjackPlayer] = []
        self.active_players: List[int] = []
        self.current_player_idx = 0
        
        # Deck and dealer
        self.deck: List[Card] = []
        self.dealer_hand: Hand = Hand()
        self.dealer_reveal = False
        
        # UI
        self.panels: Dict[int, PlayerPanel] = {}
        self.buttons: Dict[int, Dict[str, PygletButton]] = {}
        self.popup = UniversalPopup()
        
        # Input tracking
        self.current_fingertips: List[Dict] = []
        self.current_time = 0.0
        
        # Card animation
        self.dealing_animation = False
        self.deal_start_time = 0.0
        self.deal_phase = 0  # 0=player1, 1=dealer, 2=player2, 3=done
        self.card_animations = []  # List of animating cards with positions
        self.deck_position = (640, 360)  # Center of screen
        self.completed_card_indices = {}  # Track which cards have finished animating {player_idx: {hand_idx: num_completed}}
        
        # Results tracking
        self.result_timers: Dict[int, float] = {}
        self.result_duration = 2.5
        
        self._calculate_geometry()
    
    def _calculate_geometry(self):
        """Calculate table and dealer area"""
        h_panel = int(self.height * 0.10)
        v_panel = int(self.width * 0.12)
        margin = 20
        
        avail_w = self.width - (2 * v_panel) - (2 * margin)
        avail_h = self.height - (2 * h_panel) - (2 * margin)
        
        size = min(avail_w, avail_h)
        x = v_panel + margin + (avail_w - size) // 2
        y = h_panel + margin + (avail_h - size) // 2
        
        self.table_rect = (x, y, size, size)
        
        # Dealer area at center of screen
        self.dealer_area = (
            self.width // 2 - 200,
            self.height // 2 - 65,
            400, 130
        )
    
    def start_game(self, player_indices: List[int]):
        """Start game with selected players"""
        self.active_players = sorted(player_indices)
        self.players = [BlackjackPlayer(i, PLAYER_COLORS[i]) for i in range(8)]
        
        # Initialize panels
        all_panels = calculate_all_panels(self.width, self.height)
        for idx in self.active_players:
            self.panels[idx] = all_panels[idx]
            self.players[idx].is_active = True
        
        # Reset dealer hand and animations
        self.dealer_hand = Hand()
        self.card_animations = []
        self.completed_card_indices = {}
        
        self.state = "betting"
        self.current_player_idx = 0
        self.buttons = {}  # Clear all buttons when starting new round
        self._show_betting_for_all_players()
    
    def _show_betting_for_all_players(self):
        """Show betting buttons for all players simultaneously"""
        # Create betting and ready buttons for all players
        for player_idx in self.active_players:
            player = self.players[player_idx]
            
            # Auto-ready players with no chips (they're broke)
            if player.chips < 5 and not player.is_ready:
                player.is_ready = True
                player.is_bankrupt = True
            
            if player.is_ready:
                # Show only ready indicator (no buttons)
                display_text = "BROKE" if player.is_bankrupt else "Ready ✓"
                self._set_popup_buttons(player_idx, ["", "", "", "", display_text],
                                       [False, False, False, False, False])
            else:
                # Show bet amount buttons and ready button - allow additive betting
                can_5 = player.chips >= (player.current_bet + 5)
                can_25 = player.chips >= (player.current_bet + 25)
                can_100 = player.chips >= (player.current_bet + 100)
                can_500 = player.chips >= (player.current_bet + 500)
                can_ready = player.current_bet > 0
                
                self._set_popup_buttons(player_idx, ["$5", "$25", "$100", "$500", "Ready"],
                                       [can_5, can_25, can_100, can_500, can_ready])
        
        # Check for game end after auto-readying broke players
        if all(self.players[i].is_ready for i in self.active_players):
            # All players are ready (some may be broke)
            players_with_chips = [i for i in self.active_players if self.players[i].chips >= 5]
            if len(players_with_chips) == 0:
                # Game over - all players broke
                self._end_game("All players are broke!")
            elif len(players_with_chips) == 1:
                # Only one player left - they win
                winner_idx = players_with_chips[0]
                self._end_game(f"Player {winner_idx + 1} wins!")
    
    def _set_popup_buttons(self, player_idx: int, texts: List[str], enabled: List[bool]):
        """Create popup buttons in player panel - only creates if not exist, or updates enabled state"""
        panel = self.panels[player_idx]
        # Count actual non-empty buttons needed
        num_buttons = len([t for t in texts if t])
        button_rects = panel.get_button_layout(max_buttons=num_buttons)
        
        # If buttons don't exist for this player, create them
        if player_idx not in self.buttons:
            self.buttons[player_idx] = {}
        
        # Check if we need to recreate (different button set)
        needs_recreate = False
        if len(self.buttons[player_idx]) != len([t for t in texts if t]):
            needs_recreate = True
        else:
            # Check if button texts match
            for i, text in enumerate(texts):
                if text and f"btn_{i}" in self.buttons[player_idx]:
                    if self.buttons[player_idx][f"btn_{i}"].text != text:
                        needs_recreate = True
                        break
        
        if needs_recreate:
            self.buttons[player_idx] = {}
            for i, (text, en) in enumerate(zip(texts, enabled)):
                if i < len(button_rects) and text:
                    btn = PygletButton(button_rects[i], text, panel.orientation)
                    btn.enabled = en
                    self.buttons[player_idx][f"btn_{i}"] = btn
        else:
            # Just update enabled states without recreating
            for i, en in enumerate(enabled):
                if f"btn_{i}" in self.buttons[player_idx]:
                    self.buttons[player_idx][f"btn_{i}"].enabled = en
    
    def _end_game(self, message: str):
        """End the game and show winner"""
        self.state = "game_over"
        self.game_over_message = message
        self.game_over_time = time.time()
    
    def _start_dealing(self):
        """Start card dealing animation"""
        self.deck = self._create_deck()
        self.dealer_hand = Hand()
        
        # Create hands for all players with bets
        for idx in self.active_players:
            player = self.players[idx]
            if player.current_bet > 0 and player.place_bet(player.current_bet):
                hand = Hand()
                hand.bet = player.current_bet
                player.hands.append(hand)
            player.current_bet = 0  # Clear current bet after placing
        
        self.dealing_animation = True
        self.deal_start_time = time.time()
        self.deal_phase = 0
        self.state = "dealing"
    
    def _get_card_base_position(self, player_idx: int, card_index: int) -> Tuple[float, float]:
        """Calculate the target position for a card based on player and card index"""
        panel = self.panels[player_idx]
        positions = self._calculate_player_positions()
        pos_idx = self.active_players.index(player_idx)
        
        if pos_idx >= len(positions):
            return (640, 360)
        
        px, py = positions[pos_idx]
        
        # Use same card dimensions and gap as drawing
        card_w, card_h = 80, 115
        card_gap = 8
        
        # Assume single hand (hand_idx = 0) for simplicity
        if panel.orientation in [0, 180]:  # Bottom/Top - horizontal stacking
            # Calculate position for this specific card
            # For now, assume all cards in hand (will center based on total)
            # Just position based on card index
            cx = px - (card_w // 2) + card_index * (card_w + card_gap)
            cy = py
            return (cx, cy)
        else:  # Left (270) / Right (90) - vertical stacking
            cx = px
            cy = py - (card_w // 2) + card_index * (card_w + card_gap)
            return (cx, cy)
    
    def _create_deck(self) -> List[Card]:
        """Create and shuffle deck"""
        deck = [Card(rank, suit) for suit in Card.SUITS for rank in Card.RANKS]
        random.shuffle(deck)
        return deck
    
    def _deal_initial_cards(self):
        """Set up animated card dealing sequence"""
        current_time = time.time()
        delay = 0.0
        animation_duration = 0.5  # Each card takes 0.5 seconds to travel
        
        # Calculate dealer area for card positioning
        dx, dy, dw, dh = self.dealer_area
        card_w, card_h = 90, 130
        gap = 10
        
        # First card to each player
        for idx in self.active_players:
            player = self.players[idx]
            if player.hands:
                card_index = len(player.hands[0].cards)
                card = self.deck.pop()
                target_x, target_y = self._get_card_base_position(idx, card_index)
                self.card_animations.append({
                    'card': card,
                    'player_idx': idx,
                    'hand_idx': 0,
                    'start_time': current_time + delay,
                    'duration': animation_duration,
                    'start_pos': self.deck_position,
                    'target_pos': (target_x, target_y),
                    'is_dealer': False,
                    'card_num': card_index
                })
                player.hands[0].add_card(card)
                delay += 0.5
        
        # First card to dealer - calculate exact position
        card_index = len(self.dealer_hand.cards)
        card = self.deck.pop()
        # Position for first card (will be 2 cards total, so center them)
        total_width = 2 * (card_w + gap) - gap
        start_x = dx + (dw - total_width) // 2
        dealer_x = start_x + card_index * (card_w + gap)
        dealer_y = dy
        
        self.card_animations.append({
            'card': card,
            'player_idx': -1,
            'hand_idx': -1,
            'start_time': current_time + delay,
            'duration': animation_duration,
            'start_pos': self.deck_position,
            'target_pos': (dealer_x, dealer_y),
            'is_dealer': True,
            'card_num': card_index
        })
        self.dealer_hand.add_card(card)
        delay += 0.5
        
        # Second card to each player
        for idx in self.active_players:
            player = self.players[idx]
            if player.hands:
                card_index = len(player.hands[0].cards)
                card = self.deck.pop()
                target_x, target_y = self._get_card_base_position(idx, card_index)
                self.card_animations.append({
                    'card': card,
                    'player_idx': idx,
                    'hand_idx': 0,
                    'start_time': current_time + delay,
                    'duration': animation_duration,
                    'start_pos': self.deck_position,
                    'target_pos': (target_x, target_y),
                    'is_dealer': False,
                    'card_num': card_index
                })
                player.hands[0].add_card(card)
                delay += 0.5
        
        # Second card to dealer
        card_index = len(self.dealer_hand.cards)
        card = self.deck.pop()
        dealer_x = start_x + card_index * (card_w + gap)
        
        self.card_animations.append({
            'card': card,
            'player_idx': -1,
            'hand_idx': -1,
            'start_time': current_time + delay,
            'duration': animation_duration,
            'start_pos': self.deck_position,
            'target_pos': (dealer_x, dealer_y),
            'is_dealer': True,
            'card_num': card_index
        })
        self.dealer_hand.add_card(card)
        delay += 0.5
        
        self.dealing_animation = False
        self.dealer_reveal = False
        self.animation_end_time = current_time + delay + animation_duration
    
    def _offer_insurance(self):
        """Offer insurance to current player"""
        if self.current_player_idx >= len(self.active_players):
            # Check dealer blackjack
            if self.dealer_hand.is_blackjack():
                self.dealer_reveal = True
                self._resolve_insurance()
                self._check_initial_blackjacks()
            else:
                self._check_initial_blackjacks()
            return
        
        player_idx = self.active_players[self.current_player_idx]
        player = self.players[player_idx]
        
        if not player.hands:
            self.current_player_idx += 1
            self._offer_insurance()
            return
        
        hand = player.hands[0]
        insurance_cost = hand.bet // 2
        
        if player.can_bet(insurance_cost):
            panel = self.panels[player_idx]
            text_lines = [
                ("Insurance?", 16, (255, 255, 255)),
                ("Dealer shows Ace", 12, (255, 100, 100)),
                (f"Cost: ${insurance_cost}", 12, (255, 255, 100)),
                (f"Pays 2:1 if dealer has blackjack", 10, (200, 200, 200)),
            ]
            
            self.popup.show(
                player_idx, panel.rect, panel.orientation,
                "insurance", text_lines, {"player_idx": player_idx, "cost": insurance_cost}
            )
            
            self._set_popup_buttons(player_idx, ["Yes", "No", "", ""], [True, True, False, False])
        else:
            self.current_player_idx += 1
            self._offer_insurance()
    
    def _resolve_insurance(self):
        """Pay out insurance bets"""
        for idx in self.active_players:
            player = self.players[idx]
            if player.insurance_bet > 0:
                # Insurance pays 2:1
                player.chips += player.insurance_bet * 3  # Original bet + 2:1 payout
                player.insurance_bet = 0
    
    def _check_initial_blackjacks(self):
        """Check for player blackjacks and handle them"""
        dealer_bj = self.dealer_hand.is_blackjack()
        
        for idx in self.active_players:
            player = self.players[idx]
            if not player.hands:
                continue
            
            hand = player.hands[0]
            if hand.is_blackjack():
                if dealer_bj:
                    # Push - return original bet
                    player.chips += hand.bet
                    self._show_result(idx, "PUSH", "Both blackjack - tie", hand)
                else:
                    # Player blackjack pays 3:2 - return bet + 1.5x bet
                    winnings = int(hand.bet * 2.5)  # bet + (1.5 * bet)
                    player.chips += winnings
                    profit = int(hand.bet * 1.5)
                    self._show_result(idx, "BLACKJACK!", f"Won ${profit}!", hand)
                hand.is_standing = True
        
        if dealer_bj:
            # Dealer has blackjack, round ends
            self.dealer_reveal = True
            self._resolve_round()
            return
        
        # Start normal play
        self.state = "playing"
        self.current_player_idx = 0
        self._show_player_actions()
    
    def _show_player_actions(self):
        """Show action buttons for all players who need to act"""
        # Check if all players are done (all hands are standing or busted)
        all_done = True
        
        for player_idx in self.active_players:
            player = self.players[player_idx]
            
            if not player.hands:
                continue
            
            # Check if this player has any hands that need action
            player_has_active_hand = False
            for hand in player.hands:
                if not hand.is_standing and not hand.is_busted:
                    player_has_active_hand = True
                    all_done = False
                    break
            
            # If player has an active hand, show action buttons
            if player_has_active_hand:
                hand = player.get_current_hand()
                if hand and not hand.is_standing and not hand.is_busted:
                    panel = self.panels[player_idx]
                    value = hand.value()
                    
                    # Determine available actions
                    can_hit = value < 21
                    can_stand = True
                    can_double = len(hand.cards) == 2 and player.can_bet(hand.bet) and not hand.is_split
                    can_split = (len(hand.cards) == 2 and 
                                hand.cards[0].rank == hand.cards[1].rank and 
                                player.can_bet(hand.bet) and 
                                len(player.hands) < 4)
                    
                    # Create buttons without popup
                    self._set_popup_buttons(player_idx, 
                                           ["Hit", "Stand", "Double" if can_double else "", "Split" if can_split else ""],
                                           [can_hit, can_stand, can_double, can_split])
        
        # All players done, dealer's turn
        if all_done:
            self._dealer_turn()
    
    def _dealer_turn(self):
        """Dealer plays their hand"""
        self.state = "dealer_turn"
        self.dealer_reveal = True
        self.popup.hide()
        
        # Clear any existing buttons
        self.buttons = {}
        
        # Set up dealer drawing cards with animations
        self.dealer_draw_start_time = time.time()
        self.dealer_needs_to_draw = []
        
        # Calculate which cards dealer needs to draw
        # Simulate adding cards to check value
        temp_value = self.dealer_hand.value()
        while temp_value < 17:
            if self.deck and len(self.deck) > 0:
                card = self.deck.pop()
                self.dealer_needs_to_draw.append(card)
                # Add card value to temp calculation
                if card.rank == 'A':
                    temp_value += 11 if temp_value + 11 <= 21 else 1
                elif card.rank in ['J', 'Q', 'K']:
                    temp_value += 10
                else:
                    temp_value += int(card.rank)
            else:
                # Deck empty - dealer stands with what they have
                break
            
            # Safety check - max 5 cards
            if len(self.dealer_needs_to_draw) >= 5:
                break
        
        if len(self.dealer_needs_to_draw) > 0:
            self._start_dealer_draw_animation()
        else:
            # Dealer stands immediately
            if self.dealer_hand.value() > 21:
                self.dealer_hand.is_busted = True
            self._resolve_round()
    
    def _start_dealer_draw_animation(self):
        """Animate dealer drawing cards"""
        if not self.dealer_needs_to_draw:
            # No cards to draw, just resolve
            self._resolve_round()
            return
        
        current_time = time.time()
        delay = 0.5  # Start after brief delay
        
        dx, dy, dw, dh = self.dealer_area
        card_w, card_h = 90, 130
        gap = 10
        
        # Calculate total cards after all draws
        starting_cards = len(self.dealer_hand.cards)
        total_cards = starting_cards + len(self.dealer_needs_to_draw)
        total_width = total_cards * (card_w + gap) - gap
        start_x = dx + (dw - total_width) // 2
        
        for i, card in enumerate(self.dealer_needs_to_draw):
            card_index = starting_cards + i
            
            # Calculate position for this card
            dealer_x = start_x + card_index * (card_w + gap)
            dealer_y = dy
            
            self.card_animations.append({
                'card': card,
                'player_idx': -1,
                'hand_idx': -1,
                'start_time': current_time + delay,
                'duration': 0.5,
                'start_pos': self.deck_position,
                'target_pos': (dealer_x, dealer_y),
                'is_dealer': True,
                'card_num': card_index
            })
            
            self.dealer_hand.add_card(card)
            delay += 0.5  # 0.5s per card
        
        # Set time when dealer animations complete
        self.dealer_draw_complete_time = current_time + delay
        self.dealer_needs_to_draw = []
    
    def _resolve_round(self):
        """Resolve all hands and award winnings"""
        try:
            self.state = "results"
            dealer_value = self.dealer_hand.value()
            dealer_busted = self.dealer_hand.is_busted
            dealer_bj = self.dealer_hand.is_blackjack()
        except Exception as e:
            print(f"Error getting dealer values: {e}")
            # Set safe defaults
            self.state = "results"
            dealer_value = 0
            dealer_busted = True
            dealer_bj = False
        
        for idx in self.active_players:
            player = self.players[idx]
            
            for hand in player.hands:
                player_value = hand.value()
                
                # Skip hands that were already paid out (blackjacks)
                if hand.is_blackjack() and not dealer_bj:
                    # Already paid in _check_initial_blackjacks
                    continue
                
                if hand.is_busted:
                    # Already lost bet
                    self._show_result(idx, "BUST", f"Busted with {player_value}", hand)
                elif dealer_busted:
                    # Dealer busted, player wins - return bet + winnings
                    winnings = hand.bet * 2  # Return original bet + equal amount
                    player.chips += winnings
                    self._show_result(idx, "WIN!", f"Won ${hand.bet}", hand)
                elif player_value > dealer_value:
                    # Player wins - return bet + winnings
                    winnings = hand.bet * 2  # Return original bet + equal amount
                    player.chips += winnings
                    self._show_result(idx, "WIN!", f"Won ${hand.bet}", hand)
                elif player_value == dealer_value:
                    # Push - return original bet
                    player.chips += hand.bet
                    self._show_result(idx, "PUSH", f"Tie at {player_value}", hand)
                else:
                    # Dealer wins - bet already taken
                    self._show_result(idx, "LOSE", f"Lost ${hand.bet}", hand)
        
        # Schedule next round to start after showing results
        self.next_round_time = time.time() + 3.0  # 3 second delay to show results
    
    def _start_new_round(self):
        """Start a new round of blackjack"""
        # Reset all players for new round
        for idx in self.active_players:
            player = self.players[idx]
            player.reset_for_round()
        
        # Reset dealer
        self.dealer_hand = Hand()
        self.dealer_reveal = False
        
        # Clear animations and results
        self.card_animations = []
        self.completed_card_indices = {}
        if hasattr(self, '_player_results'):
            self._player_results = {}
        if hasattr(self, 'next_round_time'):
            delattr(self, 'next_round_time')
        
        # Start betting phase
        self.state = "betting"
        self.current_player_idx = 0
        self.buttons = {}
        self._show_betting_for_all_players()
    
    def _show_result(self, player_idx: int, title: str, message: str, hand: Hand):
        """Show result popup for a hand"""
        panel = self.panels[player_idx]
        text_lines = [
            (title, 18, (255, 255, 100) if "WIN" in title or "BLACKJACK" in title else (255, 100, 100) if "LOSE" in title or "BUST" in title else (200, 200, 200)),
            (message, 12, (255, 255, 255)),
        ]
        
        if len(hand.cards) > 0:
            cards_str = " ".join(str(c) for c in hand.cards[:3])
            if len(hand.cards) > 3:
                cards_str += "..."
            text_lines.append((cards_str, 10, (200, 200, 200)))
        
        # Store for display, don't use popup system for results
        if not hasattr(self, '_player_results'):
            self._player_results = {}
        self._player_results[player_idx] = (title, message, time.time())
    
    def _hit(self, player: BlackjackPlayer):
        """Player hits (with animation)"""
        hand = player.get_current_hand()
        if hand and self.deck:
            card = self.deck.pop()
            hand.add_card(card)
            
            # Add animation for the new card
            player_idx = player.idx
            card_index = len(hand.cards) - 1
            target_x, target_y = self._get_card_base_position(player_idx, card_index)
            current_time = time.time()
            
            self.card_animations.append({
                'card': card,
                'player_idx': player_idx,
                'hand_idx': player.current_hand_idx,
                'start_time': current_time,
                'duration': 0.5,
                'start_pos': self.deck_position,
                'target_pos': (target_x, target_y),
                'is_dealer': False,
                'card_num': card_index
            })
            
            if hand.value() > 21:
                hand.is_busted = True
                hand.is_standing = True
                if not player.next_hand():
                    self.current_player_idx += 1
            
            self._show_player_actions()
    
    def _stand(self, player: BlackjackPlayer):
        """Player stands"""
        hand = player.get_current_hand()
        if hand:
            hand.is_standing = True
            if not player.next_hand():
                self.current_player_idx += 1
        
        self._show_player_actions()
    
    def _double_down(self, player: BlackjackPlayer):
        """Player doubles down"""
        hand = player.get_current_hand()
        if hand and player.place_bet(hand.bet):
            hand.bet *= 2
            hand.is_doubled = True
            
            if self.deck:
                hand.add_card(self.deck.pop())
            
            if hand.value() > 21:
                hand.is_busted = True
            
            hand.is_standing = True
            if not player.next_hand():
                self.current_player_idx += 1
            
            self._show_player_actions()
    
    def _split(self, player: BlackjackPlayer):
        """Player splits their hand"""
        hand = player.get_current_hand()
        if hand and len(hand.cards) == 2 and player.place_bet(hand.bet):
            # Create two new hands
            hand1 = Hand()
            hand1.bet = hand.bet
            hand1.is_split = True
            hand1.add_card(hand.cards[0])
            hand1.add_card(self.deck.pop() if self.deck else Card('2', '♠'))
            
            hand2 = Hand()
            hand2.bet = hand.bet
            hand2.is_split = True
            hand2.add_card(hand.cards[1])
            hand2.add_card(self.deck.pop() if self.deck else Card('2', '♠'))
            
            player.hands[player.current_hand_idx] = hand1
            player.hands.insert(player.current_hand_idx + 1, hand2)
            
            self._show_player_actions()
    
    def handle_input(self, fingertips: List[Dict]) -> bool:
        """Handle input"""
        if fingertips and isinstance(fingertips[0], str) and fingertips[0] == 'ESC':
            return True
        
        if self.state == "player_select":
            self.selection_ui.update_with_fingertips(fingertips, min_players=1)
            if self.selection_ui.start_ready:
                selected = self.selection_ui.get_selected_indices()
                if selected:
                    self.start_game(selected)
            return False
        
        # Store fingertips for button updates in draw
        self.current_fingertips = fingertips
        self.current_time = time.time()
        
        # Handle button interactions for all active players
        for player_idx in self.active_players:
            if player_idx not in self.buttons:
                continue
            
            player = self.players[player_idx]
            
            # Check if this player should have active buttons
            if self.state == "betting" and not player.is_ready:
                # Betting phase - all players can bet
                for name, btn in self.buttons[player_idx].items():
                    clicked, _ = btn.update(fingertips, self.current_time)
                    if clicked:
                        self._handle_popup_click(player_idx, name)
                        break
            elif self.popup.active and self.popup.player_idx == player_idx:
                # Insurance popup
                for name, btn in self.buttons[player_idx].items():
                    clicked, _ = btn.update(fingertips, self.current_time)
                    if clicked:
                        self._handle_popup_click(player_idx, name)
                        break
            elif self.state == "playing":
                # Playing phase - all players can act
                if player.hands and not all(h.is_standing or h.is_busted for h in player.hands):
                    for name, btn in self.buttons[player_idx].items():
                        clicked, _ = btn.update(fingertips, self.current_time)
                        if clicked:
                            self._handle_popup_click(player_idx, name)
                            break
        
        return False
    
    def _handle_popup_click(self, player_idx: int, button_name: str):
        """Handle popup button clicks"""
        popup_type = self.popup.popup_type if self.popup.active else self.state
        player = self.players[player_idx]
        
        if popup_type == "betting":
            # Betting buttons: $5, $25, $100, $500, Ready
            btn_idx = int(button_name.split('_')[1])
            
            if btn_idx == 4:  # Ready button
                if player.current_bet > 0 and not player.is_ready:
                    player.is_ready = True
                    # Refresh buttons to show ready state
                    self._show_betting_for_all_players()
                    
                    # Check if all players are ready
                    if all(self.players[i].is_ready for i in self.active_players):
                        # Check if at least one player has chips to play
                        players_with_chips = [i for i in self.active_players if self.players[i].chips >= 5]
                        if len(players_with_chips) == 0:
                            # Game over - all players broke
                            self._end_game("All players are broke!")
                        elif len(players_with_chips) == 1:
                            # Only one player left - they win
                            winner_idx = players_with_chips[0]
                            self._end_game(f"Player {winner_idx + 1} wins!")
                        else:
                            self._start_dealing()
            else:  # Bet amount buttons - additive
                amounts = [5, 25, 100, 500]
                if btn_idx < len(amounts):
                    amount = amounts[btn_idx]
                    # Add to current bet instead of replacing
                    if player.chips >= (player.current_bet + amount):
                        player.current_bet += amount
                        self._show_betting_for_all_players()
        
        elif popup_type == "insurance":
            if button_name == "btn_0":  # Yes
                cost = self.popup.data.get("cost", 0)
                if player.place_bet(cost):
                    player.insurance_bet = cost
                self.popup.hide()
                self.current_player_idx += 1
                self._offer_insurance()
            elif button_name == "btn_1":  # No
                self.popup.hide()
                self.current_player_idx += 1
                self._offer_insurance()
        
        elif popup_type == "playing":
            if button_name == "btn_0":  # Hit
                self._hit(player)
            elif button_name == "btn_1":  # Stand
                self._stand(player)
            elif button_name == "btn_2":  # Double
                self._double_down(player)
            elif button_name == "btn_3":  # Split
                self._split(player)
    
    def update(self, dt: float):
        """Update game state"""
        current_time = time.time()
        
        if self.dealing_animation:
            elapsed = current_time - self.deal_start_time
            if elapsed > 0.3:  # Short delay before starting animations
                self._deal_initial_cards()
        
        # Clean up finished animations
        if hasattr(self, 'card_animations'):
            self.card_animations = [
                anim for anim in self.card_animations
                if current_time < anim['start_time'] + anim['duration']
            ]
        
        # Check if dealing animations are complete
        if self.state == "dealing" and hasattr(self, 'animation_end_time'):
            if current_time >= self.animation_end_time:
                # All cards dealt, transition to playing
                self._check_initial_blackjacks()
                self.state = "playing"
                self.current_player_idx = 0
                self.buttons = {}
                self._show_player_actions()
                delattr(self, 'animation_end_time')
        
        # Check if dealer drawing animations are complete
        if self.state == "dealer_turn" and hasattr(self, 'dealer_draw_complete_time'):
            if current_time >= self.dealer_draw_complete_time:
                try:
                    if self.dealer_hand.value() > 21:
                        self.dealer_hand.is_busted = True
                    self._resolve_round()
                except Exception as e:
                    print(f"Error in dealer animation completion: {e}")
                    # Force resolve to prevent hanging
                    self._resolve_round()
                finally:
                    delattr(self, 'dealer_draw_complete_time')
        
        # Check if results phase is over and start new round
        if self.state == "results" and hasattr(self, 'next_round_time'):
            if current_time >= self.next_round_time:
                self._start_new_round()
        
        # Auto-return to player selection after game over
        if self.state == "game_over" and hasattr(self, 'game_over_time'):
            if current_time - self.game_over_time > 5.0:
                self.state = "player_select"
                self.selection_ui = PlayerSelectionUI(self.width, self.height)
        
        # Auto-return to player selection after game over
        if self.state == "game_over" and hasattr(self, 'game_over_time'):
            if current_time - self.game_over_time > 5.0:
                self.state = "player_select"
                self.selection_ui = PlayerSelectionUI(self.width, self.height)
    
    def draw(self):
        """Draw game"""
        if self.state == "player_select":
            self._draw_player_select()
            return
        
        if self.state == "game_over":
            self._draw_game_over()
            return
        
        # Background
        self.renderer.draw_rect((0, 80, 40), (0, 0, self.width, self.height))
        
        # Panels
        self._draw_panels()
        
        # Table
        self._draw_table()
        
        # Dealer cards
        self._draw_dealer()
        
        # Player cards
        self._draw_player_cards()
        
        # Draw animating cards on top
        if hasattr(self, 'card_animations') and len(self.card_animations) > 0:
            self._draw_animating_cards()
        
        # Popup without dimming overlay
        if self.popup.active:
            self.popup.draw(self.renderer)
    
    def draw_immediate(self):
        """Draw elements on top (called after batched rendering)"""
        pass
    
    def _draw_panel_info(self, player: BlackjackPlayer, panel: PlayerPanel):
        """Draw player chips, bet, and ready status with rotation"""
        x, y, w, h = panel.rect
        
        # Calculate bet amount
        total_bet = sum(h.bet for h in player.hands)
        if total_bet == 0 and player.current_bet > 0:
            total_bet = player.current_bet
        
        # Build info text - combine balance, bet, and ready on same line
        info_text = f"${player.chips}"
        if total_bet > 0:
            info_text += f" | Bet: ${total_bet}"
        if player.is_ready and self.state in ["betting", "insurance"]:
            info_text += " | Ready"
        
        # Show result during results phase
        if self.state == "results" and hasattr(self, '_player_results'):
            if player.idx in self._player_results:
                result_title, result_msg, result_time = self._player_results[player.idx]
                info_text += f" | {result_title}"
        
        info_lines = [info_text]
        
        # Position and draw based on orientation
        if panel.orientation == 0:  # Bottom
            tx = x + w // 2
            ty = y + int(h * 0.30)
            for i, line in enumerate(info_lines):
                self.renderer.draw_text(
                    line, tx, ty - i * 22, 'Arial', 18, (255, 255, 255),
                    bold=True, anchor_x='center', anchor_y='center', rotation=0
                )
        elif panel.orientation == 180:  # Top
            tx = x + w // 2
            ty = y + int(h * 0.70)
            for i, line in enumerate(info_lines):
                self.renderer.draw_text(
                    line, tx, ty + i * 22, 'Arial', 18, (255, 255, 255),
                    bold=True, anchor_x='center', anchor_y='center', rotation=180
                )
        elif panel.orientation == 270:  # Left
            tx = x + int(w * 0.85)
            ty = y + h // 2
            for i, line in enumerate(info_lines):
                self.renderer.draw_text(
                    line, tx, ty + i * 22, 'Arial', 16, (255, 255, 255),
                    bold=True, anchor_x='center', anchor_y='center', rotation=90
                )
        else:  # 90 - Right
            tx = x + int(w * 0.15)
            ty = y + h // 2
            for i, line in enumerate(info_lines):
                self.renderer.draw_text(
                    line, tx, ty - i * 22, 'Arial', 16, (255, 255, 255),
                    bold=True, anchor_x='center', anchor_y='center', rotation=270
                )
    
    def _draw_panels(self):
        """Draw player panels"""
        current_time = time.time()
        
        for idx in self.active_players:
            player = self.players[idx]
            panel = self.panels[idx]
            
            # Highlight current player
            is_current = (self.state in ["betting", "playing", "insurance"] and 
                         self.current_player_idx < len(self.active_players) and
                         idx == self.active_players[self.current_player_idx])
            
            panel.draw_background(self.renderer, is_current)
            
            # Draw rotated panel info (chips, bet, ready state)
            self._draw_panel_info(player, panel)
            
            # Draw buttons for players during their active phases
            if idx in self.buttons:
                # Show buttons during betting (all players) or playing (all active players)
                show_buttons = False
                if self.state == "betting" and not player.is_ready:
                    show_buttons = True
                elif self.state == "playing" and player.hands and not all(h.is_standing or h.is_busted for h in player.hands):
                    show_buttons = True
                elif self.state == "insurance" and self.popup.active and self.popup.player_idx == idx:
                    show_buttons = True
                
                if show_buttons:
                    # Use stored fingertips from handle_input
                    fingertips = getattr(self, 'current_fingertips', [])
                    for name, btn in self.buttons[idx].items():
                        # Update with actual fingertips so hover works
                        _, progress = btn.update(fingertips, current_time)
                        btn.draw(self.renderer, progress)
    
    def _draw_table(self):
        """Draw casino table"""
        tx, ty, tw, th = self.table_rect
        self.renderer.draw_rect((0, 120, 60), (tx, ty, tw, th))
        self.renderer.draw_rect((255, 215, 0), (tx, ty, tw, th), width=4)
    
    def _draw_animating_cards(self):
        """Draw cards that are currently animating"""
        current_time = time.time()
        
        for anim in self.card_animations:
            if current_time < anim['start_time']:
                continue  # Not started yet
            
            elapsed = current_time - anim['start_time']
            progress = min(1.0, elapsed / anim['duration'])
            
            # Ease-out cubic for smooth deceleration
            progress = 1 - (1 - progress) ** 3
            
            # Calculate current position
            start_x, start_y = anim['start_pos']
            target_x, target_y = anim['target_pos']
            current_x = start_x + (target_x - start_x) * progress
            current_y = start_y + (target_y - start_y) * progress
            
            # Draw the card at its current position
            card = anim['card']
            if anim['is_dealer']:
                # Dealer card - centered, no rotation
                show_face = anim['card_num'] == 0  # Only first card face up
                self._draw_card_at_position(card, int(current_x), int(current_y), show_face)
            else:
                # Player card
                player_idx = anim['player_idx']
                panel = self.panels[player_idx]
                player_color = self.players[player_idx].color
                self._draw_card_at_position(card, int(current_x), int(current_y), True, 
                                          panel.orientation, player_color)
            
            # Mark card as completed if animation finished
            if progress >= 1.0 and not anim.get('marked_complete', False):
                anim['marked_complete'] = True
                if anim['is_dealer']:
                    key = ('dealer', -1)
                else:
                    key = (anim['player_idx'], anim['hand_idx'])
                
                if key not in self.completed_card_indices:
                    self.completed_card_indices[key] = 0
                self.completed_card_indices[key] += 1
    
    def _draw_card_at_position(self, card: Card, x: int, y: int, show_face: bool = True,
                               rotation: int = 0, border_color: Tuple[int, int, int] = None):
        """Draw a single card at specified position (for animations)"""
        card_width = 70
        card_height = 100
        
        # Draw card background
        if show_face:
            self.renderer.draw_rect((255, 255, 255), (x, y, card_width, card_height))
        else:
            self.renderer.draw_rect((50, 50, 150), (x, y, card_width, card_height))
        
        # Draw border
        if border_color:
            self.renderer.draw_rect(border_color, (x, y, card_width, card_height), width=3)
        else:
            self.renderer.draw_rect((0, 0, 0), (x, y, card_width, card_height), width=2)
        
        if show_face:
            # Determine card color
            color = (255, 0, 0) if card.suit in ['♥', '♦'] else (0, 0, 0)
            
            # Draw rank and suit
            self.renderer.draw_text(card.rank, x + 10, y + card_height - 25, 
                                  'Arial', 20, color, bold=True)
            self.renderer.draw_text(card.suit, x + 10, y + card_height - 50, 
                                  'Arial', 24, color, bold=True)
    
    def _draw_dealer(self):
        """Draw dealer's hand in center"""
        dx, dy, dw, dh = self.dealer_area
        
        # Cards
        if not self.dealer_hand.cards:
            return
        
        # During dealing, only draw cards that have completed animating
        num_to_draw = len(self.dealer_hand.cards)
        if self.state == "dealing":
            num_to_draw = self.completed_card_indices.get(('dealer', -1), 0)
        
        card_w, card_h = 90, 130
        gap = 10
        total_width = num_to_draw * (card_w + gap) - gap
        start_x = dx + (dw - total_width) // 2
        
        for i in range(num_to_draw):
            if i >= len(self.dealer_hand.cards):
                break
            card = self.dealer_hand.cards[i]
            cx = start_x + i * (card_w + gap)
            
            if i == 1 and not self.dealer_reveal:
                # Face down
                self._draw_card_back(cx, dy, card_w, card_h)
            else:
                self._draw_card(card, cx, dy, card_w, card_h)  # No color for dealer
        
        # No label or value shown for dealer
    
    def _draw_player_cards(self):
        """Draw player hands next to their panels with proper rotation and stacking"""
        positions = self._calculate_player_positions()
        
        for idx in self.active_players:
            player = self.players[idx]
            if not player.hands:
                continue
            
            pos_idx = self.active_players.index(idx)
            if pos_idx >= len(positions):
                continue
            
            px, py = positions[pos_idx]
            panel = self.panels[idx]
            player_color = PLAYER_COLORS[idx]
            
            # Draw all hands for this player
            card_w, card_h = 80, 115
            hand_gap = 120
            
            for h_idx, hand in enumerate(player.hands):
                # During dealing, only draw cards that have completed animating
                num_cards_to_draw = len(hand.cards)
                if self.state == "dealing":
                    num_cards_to_draw = self.completed_card_indices.get((idx, h_idx), 0)
                
                # Calculate hand position based on orientation
                if panel.orientation in [0, 180]:  # Bottom/Top - horizontal stacking
                    hand_offset = h_idx * hand_gap - (len(player.hands) - 1) * hand_gap // 2
                    hand_x = px + hand_offset
                    hand_y = py
                    
                    # Cards stack horizontally
                    card_gap = 8
                    total_width = num_cards_to_draw * (card_w + card_gap) - card_gap
                    start_x = hand_x - total_width // 2
                    
                    for c_idx in range(num_cards_to_draw):
                        if c_idx >= len(hand.cards):
                            break
                        card = hand.cards[c_idx]
                        cx = start_x + c_idx * (card_w + card_gap)
                        cy = hand_y
                        self._draw_card_rotated(card, cx, cy, card_w, card_h, panel.orientation, player_color)
                    
                    # Draw X through cards if busted
                    if hand.is_busted:
                        self._draw_bust_indicator(start_x, hand_y, total_width, card_h, panel.orientation)
                
                else:  # Left (270) / Right (90) - vertical stacking
                    hand_offset = h_idx * hand_gap - (len(player.hands) - 1) * hand_gap // 2
                    hand_x = px
                    hand_y = py + hand_offset
                    
                    # Cards stack vertically (from app's POV)
                    card_gap = 8
                    total_height = num_cards_to_draw * (card_w + card_gap) - card_gap  # card_w because rotated
                    start_y = hand_y - total_height // 2
                    
                    for c_idx in range(num_cards_to_draw):
                        if c_idx >= len(hand.cards):
                            break
                        card = hand.cards[c_idx]
                        cx = hand_x
                        cy = start_y + c_idx * (card_w + card_gap)
                        self._draw_card_rotated(card, cx, cy, card_h, card_w, panel.orientation, player_color)
                    
                    # Draw X through cards if busted
                    if hand.is_busted:
                        self._draw_bust_indicator(hand_x, start_y, card_h, total_height, panel.orientation)
                
                # No hand values or STAND text - players count their own cards
    
    def _draw_bust_indicator(self, x: int, y: int, w: int, h: int, orientation: int):
        """Draw a large X through busted cards"""
        # Draw thick red X through the cards
        line_color = (255, 50, 50)
        line_width = 5
        
        # Draw two diagonal lines forming an X
        # Line 1: top-left to bottom-right
        x1, y1 = x, y + h
        x2, y2 = x + w, y
        self.renderer.draw_line(line_color, (x1, y1), (x2, y2), line_width)
        
        # Line 2: bottom-left to top-right
        x1, y1 = x, y
        x2, y2 = x + w, y + h
        self.renderer.draw_line(line_color, (x1, y1), (x2, y2), line_width)
    
    def _calculate_player_positions(self) -> List[Tuple[int, int]]:
        """Calculate card positions from player's POV (above their panel from their perspective)"""
        positions = []
        
        for idx in self.active_players:
            panel = self.panels[idx]
            x, y, w, h = panel.rect
            
            # Position cards "above" panel from player's perspective (close to panel like left/right)
            if panel.orientation == 0:  # Bottom - cards just above panel, overlapping slightly
                px = x + w // 2
                py = y - 100  # Above the bottom panel (negative y = up)
            elif panel.orientation == 180:  # Top - cards just below panel
                px = x + w // 2
                py = y + h - 20  # Inside bottom edge of panel
            elif panel.orientation == 90:  # Right - cards to the left (above from their POV)
                px = x - 100
                py = y + h // 2
            else:  # 270 - Left - cards to the right (above from their POV)
                px = x + w - 10  # More to the left (overlapping panel slightly)
                py = y + h // 2
            
            positions.append((px, py))
        
        return positions
    
    def _draw_card_rotated(self, card: Card, x: int, y: int, w: int, h: int, rotation: int, player_color: Tuple[int, int, int] = None):
        """Draw a rotated playing card with rotated content"""
        # Draw card background and border
        self.renderer.draw_rect((255, 255, 255), (x, y, w, h))
        outline_color = player_color if player_color else (0, 0, 0)
        outline_width = 3 if player_color else 2
        self.renderer.draw_rect(outline_color, (x, y, w, h), width=outline_width)
        
        # Suit color
        color = (220, 20, 20) if card.suit in ['♥', '♦'] else (20, 20, 20)
        
        # Calculate center for rotation
        cx = x + w // 2
        cy = y + h // 2
        
        # Draw card content with rotation
        if rotation == 0:  # Bottom player
            # Rank top
            self.renderer.draw_text(
                card.rank, cx, y + h - 20,
                'Arial', 20, color, bold=True, anchor_x='center', anchor_y='center', rotation=0
            )
            # Suit center
            self.renderer.draw_text(
                card.suit, cx, cy,
                'Arial', 40, color, anchor_x='center', anchor_y='center', rotation=0
            )
            # Rank bottom
            self.renderer.draw_text(
                card.rank, cx, y + 20,
                'Arial', 20, color, bold=True, anchor_x='center', anchor_y='center', rotation=0
            )
        elif rotation == 180:  # Top player
            # Everything rotated 180
            self.renderer.draw_text(
                card.rank, cx, y + 20,
                'Arial', 20, color, bold=True, anchor_x='center', anchor_y='center', rotation=180
            )
            self.renderer.draw_text(
                card.suit, cx, cy,
                'Arial', 40, color, anchor_x='center', anchor_y='center', rotation=180
            )
            self.renderer.draw_text(
                card.rank, cx, y + h - 20,
                'Arial', 20, color, bold=True, anchor_x='center', anchor_y='center', rotation=180
            )
        elif rotation == 90:  # Right player (rotated 90 CW)
            # Card is rotated 90 degrees clockwise
            self.renderer.draw_text(
                card.rank, x + w - 20, cy,
                'Arial', 20, color, bold=True, anchor_x='center', anchor_y='center', rotation=270
            )
            self.renderer.draw_text(
                card.suit, cx, cy,
                'Arial', 40, color, anchor_x='center', anchor_y='center', rotation=270
            )
            self.renderer.draw_text(
                card.rank, x + 20, cy,
                'Arial', 20, color, bold=True, anchor_x='center', anchor_y='center', rotation=270
            )
        else:  # rotation == 270, Left player (rotated 90 CCW)
            # Card is rotated 90 degrees counter-clockwise
            self.renderer.draw_text(
                card.rank, x + 20, cy,
                'Arial', 20, color, bold=True, anchor_x='center', anchor_y='center', rotation=90
            )
            self.renderer.draw_text(
                card.suit, cx, cy,
                'Arial', 40, color, anchor_x='center', anchor_y='center', rotation=90
            )
            self.renderer.draw_text(
                card.rank, x + w - 20, cy,
                'Arial', 20, color, bold=True, anchor_x='center', anchor_y='center', rotation=90
            )
    
    def _draw_card(self, card: Card, x: int, y: int, w: int, h: int, player_color: Tuple[int, int, int] = None):
        """Draw a playing card with optional player color outline"""
        # Card background
        self.renderer.draw_rect((255, 255, 255), (x, y, w, h))
        # Colored outline if player card, black if no color specified
        outline_color = player_color if player_color else (0, 0, 0)
        outline_width = 3 if player_color else 2
        self.renderer.draw_rect(outline_color, (x, y, w, h), width=outline_width)
        
        # Suit color
        color = (220, 20, 20) if card.suit in ['♥', '♦'] else (20, 20, 20)
        
        # Rank (top left, inside card)
        self.renderer.draw_text(
            card.rank, x + w // 2, y + h - 20,
            'Arial', 20, color,
            bold=True, anchor_x='center', anchor_y='center'
        )
        
        # Suit (center)
        self.renderer.draw_text(
            card.suit, x + w // 2, y + h // 2,
            'Arial', 40, color,
            anchor_x='center', anchor_y='center'
        )
        
        # Rank (bottom, inside card)
        self.renderer.draw_text(
            card.rank, x + w // 2, y + 20,
            'Arial', 20, color,
            bold=True, anchor_x='center', anchor_y='center'
        )
    
    def _draw_card_back(self, x: int, y: int, w: int, h: int):
        """Draw card back"""
        self.renderer.draw_rect((50, 50, 150), (x, y, w, h))
        self.renderer.draw_rect((200, 200, 200), (x, y, w, h), width=2)
        
        # Pattern
        for i in range(3):
            for j in range(4):
                px = x + 10 + i * 20
                py = y + 10 + j * 20
                self.renderer.draw_rect((100, 100, 200), (px, py, 15, 15))
    
    def _draw_game_over(self):
        """Draw game over screen"""
        # Background
        self.renderer.draw_rect((0, 80, 40), (0, 0, self.width, self.height))
        
        # Draw panels to show final chip counts
        self._draw_panels()
        
        # Game over message in center
        center_x = self.width // 2
        center_y = self.height // 2
        
        self.renderer.draw_text(
            "GAME OVER",
            center_x, center_y + 50,
            'Arial', 48, (255, 215, 0),
            bold=True, anchor_x='center', anchor_y='center'
        )
        
        self.renderer.draw_text(
            self.game_over_message,
            center_x, center_y - 20,
            'Arial', 32, (255, 255, 255),
            bold=True, anchor_x='center', anchor_y='center'
        )
        
        # Show restart instruction after 3 seconds
        if time.time() - self.game_over_time > 3.0:
            self.renderer.draw_text(
                "Returning to player selection...",
                center_x, center_y - 80,
                'Arial', 20, (200, 200, 200),
                anchor_x='center', anchor_y='center'
            )
    
    def _draw_player_select(self):
        """Draw player selection"""
        self.renderer.draw_rect((0, 50, 25), (0, 0, self.width, self.height))
        
        self.renderer.draw_text(
            "Select Players - Blackjack",
            self.width // 2, 50,
            'Arial', 48, Colors.WHITE,
            anchor_x='center', anchor_y='center'
        )
        
        # Draw slots
        for i, (sx, sy, sw, sh) in enumerate(self.selection_ui.slots):
            cx = sx + sw // 2
            cy = sy + sh // 2
            radius = sw // 2
            color = PLAYER_COLORS[i]
            
            if self.selection_ui.selected[i]:
                self.renderer.draw_circle(color, (cx, cy), radius)
                self.renderer.draw_circle((255, 255, 255), (cx, cy), radius, width=5)
            else:
                self.renderer.draw_circle((80, 80, 80), (cx, cy), radius, width=3)
            
            text_color = (255, 255, 255) if self.selection_ui.selected[i] else (150, 150, 150)
            self.renderer.draw_text(
                f"P{i+1}", cx, cy,
                'Arial', 36, text_color,
                anchor_x='center', anchor_y='center'
            )
        
        # Start button
        btn_size = 160
        cx = self.width // 2
        cy = self.height // 2
        count = self.selection_ui.selected_count()
        
        if count >= 1:
            self.renderer.draw_circle((70, 130, 180), (cx, cy), btn_size // 2)
            self.renderer.draw_circle((200, 200, 200), (cx, cy), btn_size // 2, width=3)
        else:
            self.renderer.draw_circle((100, 100, 100), (cx, cy), btn_size // 2)
        
        self.renderer.draw_text(
            "Start", cx, cy - 10,
            'Arial', 36, (255, 255, 255),
            anchor_x='center', anchor_y='center'
        )
        self.renderer.draw_text(
            f"{count} player(s)", cx, cy + 25,
            'Arial', 18, (200, 200, 200),
            anchor_x='center', anchor_y='center'
        )
