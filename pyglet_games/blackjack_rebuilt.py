"""
Complete Blackjack Game - Pyglet Implementation
Carbon copy of Pygame version with full UI and game logic
"""

import time
import random
from typing import List, Dict, Tuple
from pyglet_games.renderer import PygletRenderer
from config import PLAYER_COLORS, Colors
from blackjack.player import BlackjackPlayer
from blackjack.game_logic import BlackjackLogic
from pyglet_games.player_selection import PlayerSelectionUI
from pyglet_games.player_panels import calculate_all_panels

HOVER_TIME = 1.5


class PygletButton:
    """Button with hover progress"""
    def __init__(self, rect: Tuple[int, int, int, int], text: str, orientation: int = 0):
        self.x, self.y, self.width, self.height = rect
        self.text = text
        self.orientation = orientation
        self.enabled = True
        self.hover_start = 0.0
        self.hovering = False
    
    def update(self, fingertips: List[Dict], current_time: float) -> Tuple[bool, float]:
        """Returns (clicked, hover_progress)"""
        if not self.enabled:
            self.hovering = False
            return False, 0.0
        
        for meta in fingertips:
            x, y = meta["pos"]
            if (self.x <= x <= self.x + self.width and 
                self.y <= y <= self.y + self.height):
                if not self.hovering:
                    self.hover_start = current_time
                    self.hovering = True
                
                progress = (current_time - self.hover_start) / HOVER_TIME
                if progress >= 1.0:
                    self.hovering = False
                    return True, 1.0
                return False, progress
        
        self.hovering = False
        return False, 0.0
    
    def draw(self, renderer: PygletRenderer, hover_progress: float = 0.0):
        """Draw button"""
        if not self.enabled:
            bg = (100, 100, 100)
            text_color = (160, 160, 160)
        else:
            base = (70, 130, 180)
            hover = (100, 180, 220)
            bg = tuple(int(base[i] + (hover[i] - base[i]) * hover_progress) for i in range(3))
            text_color = (255, 255, 255)
        
        renderer.draw_rect(bg, (self.x, self.y, self.width, self.height))
        renderer.draw_rect((200, 200, 200), (self.x, self.y, self.width, self.height), width=2)
        
        if hover_progress > 0:
            bar_w = int(self.width * hover_progress)
            renderer.draw_rect((255, 215, 0), (self.x, self.y + self.height - 4, bar_w, 4))
        
        renderer.draw_text(
            self.text, self.x + self.width // 2, self.y + self.height // 2,
            'Arial', 16, text_color, anchor_x='center', anchor_y='center'
        )


class BlackjackGame:
    """Complete Blackjack game matching Pygame version"""
    
    def __init__(self, width: int, height: int, renderer: PygletRenderer):
        self.width = width
        self.height = height
        self.renderer = renderer
        
        self.state = "player_select"
        self.selection_ui = PlayerSelectionUI(width, height)
        
        self.players: List[BlackjackPlayer] = []
        self.active_players: List[int] = []
        self.current_player_idx = 0
        
        self.deck = []
        self.dealer_hand = []
        self.dealer_reveal = False
        
        self.phase = "betting"  # betting, playing, dealer, done
        self.round_active = False
        
        self.panels = {}
        self.buttons: Dict[int, Dict[str, PygletButton]] = {}
        
        self._calculate_table_geometry()
    
    def _calculate_table_geometry(self):
        """Calculate table position"""
        h_panel = int(self.height * 0.10)
        v_panel = int(self.width * 0.12)
        margin = 20
        
        avail_w = self.width - (2 * v_panel) - (2 * margin)
        avail_h = self.height - (2 * h_panel) - (2 * margin)
        
        size = min(avail_w, avail_h)
        x = v_panel + margin + (avail_w - size) // 2
        y = h_panel + margin + (avail_h - size) // 2
        
        self.table_rect = (x, y, size, size)
        
        # Dealer area at top center
        self.dealer_area = (
            x + size // 2 - 150,
            y + size - 120,
            300, 120
        )
    
    def _init_buttons(self):
        """Initialize buttons for all players"""
        self.buttons = {}
        for idx in self.active_players:
            panel = self.panels[idx]
            self.buttons[idx] = self._create_buttons(panel, idx)
    
    def _create_buttons(self, panel: Dict, idx: int) -> Dict[str, PygletButton]:
        """Create 4 buttons per panel (betting or playing)"""
        x, y, w, h = panel['rect']
        orient = panel['orientation']
        margin = 10
        gap = 8
        
        if orient == 0:  # Bottom
            info_h = int(h * 0.45)
            btn_h = h - info_h - 2 * margin
            btn_w = (w - 2 * margin - 3 * gap) // 4
            btn_y = y + info_h + margin
            
            return {
                # Playing buttons
                "hit": PygletButton((x + margin, btn_y, btn_w, btn_h), "Hit", orient),
                "stand": PygletButton((x + margin + btn_w + gap, btn_y, btn_w, btn_h), "Stand", orient),
                "double": PygletButton((x + margin + 2*(btn_w+gap), btn_y, btn_w, btn_h), "Double", orient),
                "split": PygletButton((x + margin + 3*(btn_w+gap), btn_y, btn_w, btn_h), "Split", orient),
                # Betting buttons (reuse positions)
                "bet5": PygletButton((x + margin, btn_y, btn_w, btn_h), "$5", orient),
                "bet25": PygletButton((x + margin + btn_w + gap, btn_y, btn_w, btn_h), "$25", orient),
                "bet100": PygletButton((x + margin + 2*(btn_w+gap), btn_y, btn_w, btn_h), "$100", orient),
                "ready": PygletButton((x + margin + 3*(btn_w+gap), btn_y, btn_w, btn_h), "Ready", orient)
            }
        
        elif orient == 180:  # Top
            info_h = int(h * 0.45)
            btn_h = h - info_h - 2 * margin
            btn_w = (w - 2 * margin - 3 * gap) // 4
            btn_y = y + margin
            
            return {
                "hit": PygletButton((x + margin, btn_y, btn_w, btn_h), "Hit", orient),
                "stand": PygletButton((x + margin + btn_w + gap, btn_y, btn_w, btn_h), "Stand", orient),
                "double": PygletButton((x + margin + 2*(btn_w+gap), btn_y, btn_w, btn_h), "Double", orient),
                "split": PygletButton((x + margin + 3*(btn_w+gap), btn_y, btn_w, btn_h), "Split", orient),
                "bet5": PygletButton((x + margin, btn_y, btn_w, btn_h), "$5", orient),
                "bet25": PygletButton((x + margin + btn_w + gap, btn_y, btn_w, btn_h), "$25", orient),
                "bet100": PygletButton((x + margin + 2*(btn_w+gap), btn_y, btn_w, btn_h), "$100", orient),
                "ready": PygletButton((x + margin + 3*(btn_w+gap), btn_y, btn_w, btn_h), "Ready", orient)
            }
        
        elif orient == 90:  # Left
            info_w = int(w * 0.35)
            btn_w = w - info_w - 2 * margin
            btn_h = (h - 2 * margin - 3 * gap) // 4
            btn_x = x + margin
            
            return {
                "hit": PygletButton((btn_x, y + margin, btn_w, btn_h), "Hit", orient),
                "stand": PygletButton((btn_x, y + margin + btn_h + gap, btn_w, btn_h), "Stand", orient),
                "double": PygletButton((btn_x, y + margin + 2*(btn_h+gap), btn_w, btn_h), "Double", orient),
                "split": PygletButton((btn_x, y + margin + 3*(btn_h+gap), btn_w, btn_h), "Split", orient),
                "bet5": PygletButton((btn_x, y + margin, btn_w, btn_h), "$5", orient),
                "bet25": PygletButton((btn_x, y + margin + btn_h + gap, btn_w, btn_h), "$25", orient),
                "bet100": PygletButton((btn_x, y + margin + 2*(btn_h+gap), btn_w, btn_h), "$100", orient),
                "ready": PygletButton((btn_x, y + margin + 3*(btn_h+gap), btn_w, btn_h), "Ready", orient)
            }
        
        else:  # 270 - Right
            info_w = int(w * 0.35)
            btn_w = w - info_w - 2 * margin
            btn_h = (h - 2 * margin - 3 * gap) // 4
            btn_x = x + info_w + margin
            
            return {
                "hit": PygletButton((btn_x, y + margin, btn_w, btn_h), "Hit", orient),
                "stand": PygletButton((btn_x, y + margin + btn_h + gap, btn_w, btn_h), "Stand", orient),
                "double": PygletButton((btn_x, y + margin + 2*(btn_h+gap), btn_w, btn_h), "Double", orient),
                "split": PygletButton((btn_x, y + margin + 3*(btn_h+gap), btn_w, btn_h), "Split", orient),
                "bet5": PygletButton((btn_x, y + margin, btn_w, btn_h), "$5", orient),
                "bet25": PygletButton((btn_x, y + margin + btn_h + gap, btn_w, btn_h), "$25", orient),
                "bet100": PygletButton((btn_x, y + margin + 2*(btn_h+gap), btn_w, btn_h), "$100", orient),
                "ready": PygletButton((btn_x, y + margin + 3*(btn_h+gap), btn_w, btn_h), "Ready", orient)
            }
    
    def start_game(self, player_indices: List[int]):
        """Start game with selected players"""
        self.active_players = sorted(player_indices)
        self.players = [BlackjackPlayer(i, PLAYER_COLORS[i]) for i in range(8)]
        
        all_panels = calculate_all_panels(self.width, self.height)
        for idx in self.active_players:
            panel = all_panels[idx]
            self.panels[idx] = {
                'rect': (panel.x, panel.y, panel.width, panel.height),
                'orientation': panel.orientation,
                'side': panel.side
            }
            p = self.players[idx]
            p.chips = 1000
            p.is_active = True
        
        self._init_buttons()
        self.phase = "betting"
        self.state = "playing"
    
    def handle_input(self, fingertips: List[Dict]) -> bool:
        """Handle input"""
        # Check for ESC key
        if fingertips and isinstance(fingertips[0], str) and fingertips[0] == 'ESC':
            return True  # Return to menu
        
        if self.state == "player_select":
            self.selection_ui.update_with_fingertips(fingertips, min_players=2)
            if self.selection_ui.start_ready:
                selected_indices = self.selection_ui.get_selected_indices()
                if selected_indices:
                    self.start_game(selected_indices)
            return False
        
        current_time = time.time()
        
        if self.phase == "betting":
            self._handle_betting_input(fingertips, current_time)
        elif self.phase == "playing":
            self._handle_playing_input(fingertips, current_time)
        
        return False
    
    def _handle_betting_input(self, fingertips: List[Dict], current_time: float):
        """Handle betting phase input"""
        for idx in self.active_players:
            if idx not in self.buttons:
                continue
            
            player = self.players[idx]
            btns = self.buttons[idx]
            
            if not player.is_ready:
                # Betting buttons
                btns["bet5"].enabled = player.chips >= 5
                btns["bet25"].enabled = player.chips >= 25
                btns["bet100"].enabled = player.chips >= 100
                btns["ready"].enabled = True
                
                if btns["bet5"].update(fingertips, current_time)[0]:
                    player.place_bet(5)
                if btns["bet25"].update(fingertips, current_time)[0]:
                    player.place_bet(25)
                if btns["bet100"].update(fingertips, current_time)[0]:
                    player.place_bet(100)
                if btns["ready"].update(fingertips, current_time)[0]:
                    if player.current_bet == 0:
                        player.skip_round()
                    player.is_ready = True
        
        # Check if all ready
        if all(self.players[i].is_ready for i in self.active_players):
            self._new_round()
    
    def _handle_playing_input(self, fingertips: List[Dict], current_time: float):
        """Handle playing phase input"""
        for idx in self.active_players:
            if idx not in self.buttons:
                continue
            
            player = self.players[idx]
            if player.is_sitting_out() or player.is_standing or player.is_busted:
                continue
            
            btns = self.buttons[idx]
            hand = player.get_current_hand()
            
            can_double = BlackjackLogic.can_double_down(hand) and player.chips >= player.current_bet
            can_split = BlackjackLogic.can_split(hand) and player.chips >= player.current_bet
            
            btns["hit"].enabled = True
            btns["stand"].enabled = True
            btns["double"].enabled = can_double
            btns["split"].enabled = can_split
            
            if btns["hit"].update(fingertips, current_time)[0]:
                self._hit(player)
            if btns["stand"].update(fingertips, current_time)[0]:
                player.is_standing = True
                self._check_round_done()
            if can_double and btns["double"].update(fingertips, current_time)[0]:
                self._double_down(player)
                self._check_round_done()
            if can_split and btns["split"].update(fingertips, current_time)[0]:
                self._split(player)
    
    def _new_round(self):
        """Start new round"""
        self.deck = BlackjackLogic.create_deck()
        self.dealer_hand = []
        self.dealer_reveal = False
        
        playing = [i for i in self.active_players if not self.players[i].is_sitting_out()]
        
        if not playing:
            self.phase = "betting"
            return
        
        for idx in playing:
            self.players[idx].reset_hand()
        
        # Deal cards
        for idx in playing:
            self.players[idx].add_card(self.deck.pop())
        self.dealer_hand.append(self.deck.pop())
        
        for idx in playing:
            self.players[idx].add_card(self.deck.pop())
        self.dealer_hand.append(self.deck.pop())
        
        self.phase = "playing"
        self.round_active = True
    
    def _hit(self, player: BlackjackPlayer):
        """Hit - add card"""
        if self.deck:
            player.add_card(self.deck.pop())
            hand = player.get_current_hand()
            if BlackjackLogic.hand_value(hand) > 21:
                player.is_busted = True
                self._check_round_done()
    
    def _double_down(self, player: BlackjackPlayer):
        """Double down"""
        hand = player.get_current_hand()
        if BlackjackLogic.can_double_down(hand) and player.chips >= player.current_bet:
            player.chips -= player.current_bet
            player.current_bet *= 2
            self._hit(player)
            if not player.is_busted:
                player.is_standing = True
    
    def _split(self, player: BlackjackPlayer):
        """Split hand"""
        hand = player.get_current_hand()
        if BlackjackLogic.can_split(hand) and player.chips >= player.current_bet:
            player.hands = [[hand[0]], [hand[1]]]
            player.current_hand_idx = 0
            player.chips -= player.current_bet
    
    def _check_round_done(self):
        """Check if all players done"""
        all_done = True
        for idx in self.active_players:
            player = self.players[idx]
            if not player.is_sitting_out() and not player.is_standing and not player.is_busted:
                all_done = False
                break
        
        if all_done:
            self._dealer_turn()
    
    def _dealer_turn(self):
        """Dealer plays"""
        self.dealer_reveal = True
        
        while BlackjackLogic.hand_value(self.dealer_hand) < 17:
            if self.deck:
                self.dealer_hand.append(self.deck.pop())
        
        self._resolve_round()
    
    def _resolve_round(self):
        """Resolve bets"""
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
    
    def update(self, dt: float):
        """Update game"""
        pass
    
    def draw(self):
        """Draw game"""
        if self.state == "player_select":
            self._draw_player_select()
            return
        
        # Background
        self.renderer.draw_rect((0, 100, 50), (0, 0, self.width, self.height))
        
        # Panels
        self._draw_panels()
        
        # Table
        self._draw_table()
        
        # Dealer cards
        self._draw_dealer()
        
        # Player cards
        self._draw_player_cards()
    
    def _draw_panels(self):
        """Draw player panels"""
        current_time = time.time()
        
        for idx in self.active_players:
            player = self.players[idx]
            panel = self.panels[idx]
            
            # Background
            color = PLAYER_COLORS[idx]
            washed = tuple(min(255, int(c * 0.75 + 180 * 0.25)) for c in color)
            self.renderer.draw_rect(washed, panel['rect'])
            self.renderer.draw_rect((150, 150, 150), panel['rect'], width=2)
            
            # Info
            self._draw_panel_info(player, panel)
            
            # Buttons
            if idx in self.buttons:
                btns = self.buttons[idx]
                if self.phase == "betting":
                    for name in ["bet5", "bet25", "bet100", "ready"]:
                        _, progress = btns[name].update([], current_time)
                        btns[name].draw(self.renderer, progress)
                elif self.phase == "playing":
                    for name in ["hit", "stand", "double", "split"]:
                        _, progress = btns[name].update([], current_time)
                        btns[name].draw(self.renderer, progress)
    
    def _draw_panel_info(self, player: BlackjackPlayer, panel: Dict):
        """Draw player info"""
        x, y, w, h = panel['rect']
        cx = x + w // 2
        cy = y + 25 if panel['orientation'] == 0 else y + h - 25
        
        self.renderer.draw_text(
            f"${player.chips}", cx, cy,
            'Arial', 18, (255, 255, 100),
            anchor_x='center', anchor_y='center'
        )
        
        if player.current_bet > 0:
            bet_y = cy - 22 if panel['orientation'] == 0 else cy + 22
            self.renderer.draw_text(
                f"Bet: ${player.current_bet}", cx, bet_y,
                'Arial', 14, (100, 255, 100),
                anchor_x='center', anchor_y='center'
            )
        
        if player.is_ready and self.phase == "betting":
            self.renderer.draw_text(
                "READY", cx, cy - 40 if panel['orientation'] == 0 else cy + 40,
                'Arial', 16, (100, 255, 100),
                anchor_x='center', anchor_y='center'
            )
    
    def _draw_table(self):
        """Draw blackjack table"""
        tx, ty, tw, th = self.table_rect
        self.renderer.draw_rect((0, 150, 50), (tx, ty, tw, th))
        self.renderer.draw_rect((200, 200, 0), (tx, ty, tw, th), width=3)
    
    def _draw_dealer(self):
        """Draw dealer cards"""
        if not self.dealer_hand:
            return
        
        dx, dy, dw, dh = self.dealer_area
        
        # Label
        self.renderer.draw_text(
            "Dealer", dx + dw // 2, dy + dh + 10,
            'Arial', 20, (255, 255, 255),
            anchor_x='center', anchor_y='bottom'
        )
        
        # Cards
        card_w, card_h = 60, 90
        start_x = dx + dw // 2 - (len(self.dealer_hand) * (card_w + 5)) // 2
        
        for i, card in enumerate(self.dealer_hand):
            cx = start_x + i * (card_w + 5)
            
            if i == 1 and not self.dealer_reveal:
                # Face down
                self.renderer.draw_rect((100, 100, 200), (cx, dy, card_w, card_h))
                self.renderer.draw_rect((255, 255, 255), (cx, dy, card_w, card_h), width=2)
            else:
                # Face up
                self._draw_card(card, cx, dy, card_w, card_h)
        
        # Value
        if self.dealer_reveal:
            value = BlackjackLogic.hand_value(self.dealer_hand)
            self.renderer.draw_text(
                str(value), dx + dw // 2, dy - 10,
                'Arial', 24, (255, 255, 255),
                anchor_x='center', anchor_y='top'
            )
    
    def _draw_player_cards(self):
        """Draw player cards on table"""
        card_w, card_h = 50, 75
        tx, ty, tw, th = self.table_rect
        
        # Position cards around table
        positions = [
            (tx + tw // 2, ty + 20),  # Bottom center
            (tx + tw - 100, ty + 80),  # Bottom right
            (tx + tw - 80, ty + th // 2),  # Right
            (tx + tw - 100, ty + th - 100),  # Top right
            (tx + tw // 2, ty + th - 20),  # Top center
            (tx + 100, ty + th - 100),  # Top left
            (tx + 80, ty + th // 2),  # Left
            (tx + 100, ty + 80)  # Bottom left
        ]
        
        for idx in self.active_players:
            player = self.players[idx]
            if player.is_sitting_out():
                continue
            
            pos_idx = self.active_players.index(idx) % len(positions)
            px, py = positions[pos_idx]
            
            hand = player.get_current_hand()
            start_x = px - (len(hand) * (card_w + 3)) // 2
            
            for i, card in enumerate(hand):
                cx = start_x + i * (card_w + 3)
                self._draw_card(card, cx, py, card_w, card_h)
            
            # Hand value
            if not player.is_busted:
                value = BlackjackLogic.hand_value(hand)
                self.renderer.draw_text(
                    str(value), px, py - 10,
                    'Arial', 18, (255, 255, 255),
                    anchor_x='center', anchor_y='top'
                )
    
    def _draw_card(self, card: Tuple[str, str], x: int, y: int, w: int, h: int):
        """Draw a card"""
        rank, suit = card
        
        # Card background
        self.renderer.draw_rect((255, 255, 255), (x, y, w, h))
        self.renderer.draw_rect((0, 0, 0), (x, y, w, h), width=2)
        
        # Suit color
        color = (255, 0, 0) if suit in ['♥', '♦'] else (0, 0, 0)
        
        # Rank
        self.renderer.draw_text(
            rank, x + w // 2, y + h // 2 + 10,
            'Arial', 16, color,
            anchor_x='center', anchor_y='center'
        )
        
        # Suit
        self.renderer.draw_text(
            suit, x + w // 2, y + h // 2 - 10,
            'Arial', 20, color,
            anchor_x='center', anchor_y='center'
        )
    
    def _draw_player_select(self):
        """Draw player selection screen"""
        # Background
        self.renderer.draw_rect((0, 50, 25), (0, 0, self.width, self.height))
        
        # Title at top
        self.renderer.draw_text(
            "Select Players - Blackjack",
            self.width // 2, 40,
            'Arial', 48, Colors.WHITE,
            anchor_x='center', anchor_y='center'
        )
        
        # Draw circular player slots
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
                f"P{i+1}",
                cx, cy,
                'Arial', 36, text_color,
                anchor_x='center', anchor_y='center'
            )
        
        # Start button in center
        btn_size = 160
        cx = self.width // 2
        cy = self.height // 2
        count = self.selection_ui.selected_count()
        
        if count >= 2:
            self.renderer.draw_circle((70, 130, 180), (cx, cy), btn_size // 2)
            self.renderer.draw_circle((200, 200, 200), (cx, cy), btn_size // 2, width=3)
        else:
            self.renderer.draw_circle((100, 100, 100), (cx, cy), btn_size // 2)
            self.renderer.draw_circle((80, 80, 80), (cx, cy), btn_size // 2, width=2)
        
        self.renderer.draw_text(
            "Start",
            cx, cy - 10,
            'Arial', 36, (255, 255, 255),
            anchor_x='center', anchor_y='center'
        )
        self.renderer.draw_text(
            f"{count} players",
            cx, cy + 25,
            'Arial', 18, (200, 200, 200),
            anchor_x='center', anchor_y='center'
        )
