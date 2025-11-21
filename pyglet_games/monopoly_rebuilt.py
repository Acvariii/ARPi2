"""
Complete Monopoly Game - Pyglet Implementation
Carbon copy of Pygame version with full UI and game logic
"""

import time
import random
from typing import List, Dict, Tuple, Optional
from pyglet_games.renderer import PygletRenderer
from config import PLAYER_COLORS, Colors, HOVER_TIME_THRESHOLD
from monopoly_data import (
    BOARD_SPACES, STARTING_MONEY, PASSING_GO_MONEY,
    LUXURY_TAX, INCOME_TAX, JAIL_POSITION, GO_TO_JAIL_POSITION
)
from constants import COMMUNITY_CHEST_CARDS, CHANCE_CARDS
from monopoly.property import Property
from monopoly.player import Player
from monopoly.game_logic import GameLogic
from pyglet_games.player_selection import PlayerSelectionUI
from pyglet_games.ui_components_pyglet import (
    PygletButton, PlayerPanel, calculate_all_panels, draw_hover_indicators
)
from pyglet_games.popup_system import (
    UniversalPopup, create_monopoly_buy_popup, create_monopoly_card_popup,
    create_monopoly_properties_popup, create_info_popup
)


class MonopolyGame:
    """Complete Monopoly game matching Pygame version"""
    
    def __init__(self, width: int, height: int, renderer: PygletRenderer):
        self.width = width
        self.height = height
        self.renderer = renderer
        
        self.state = "player_select"
        self.selection_ui = PlayerSelectionUI(width, height)
        self.winner_idx = None
        
        self.players: List[Player] = []
        self.active_players: List[int] = []
        self.current_player_idx = 0
        
        self.properties = [Property(data) if data else Property({"name": "", "type": "none"}) 
                          for data in BOARD_SPACES]
        
        self.community_chest_deck = list(COMMUNITY_CHEST_CARDS)
        self.chance_deck = list(CHANCE_CARDS)
        random.shuffle(self.community_chest_deck)
        random.shuffle(self.chance_deck)
        
        self.phase = "roll"
        self.can_roll = True
        self.dice_values = (0, 0)
        self.dice_rolling = False
        self.dice_roll_start = 0.0
        
        # Token animation tracking
        self.token_animations: Dict[int, Dict] = {}  # player_idx -> {start_pos, end_pos, start_time, duration}
        
        # Universal popup system
        self.popup = UniversalPopup()
        self.property_scroll = 0
        self.mortgage_scroll_index = 0  # Track which property we're viewing in mortgage popup
        
        # Trade system state
        self.trade_initiator = None  # Player who started the trade
        self.trade_partner = None    # Player being traded with
        self.trade_offer = {         # What initiator is offering
            "money": 0,
            "properties": []  # List of property indices
        }
        self.trade_request = {       # What initiator wants
            "money": 0,
            "properties": []  # List of property indices
        }
        self.trade_scroll_index = 0  # For scrolling through properties in trade
        self.trade_mode = None       # "select_partner", "build_offer", "await_response"
        self.trade_view_mode = "money"  # "money", "give_props", "get_props"
        self.trade_give_prop_scroll = 0  # Scroll index for your properties
        self.trade_get_prop_scroll = 0   # Scroll index for their properties
        
        # Auction system
        self.auction_active = False
        self.auction_property = None  # Property index being auctioned
        self.auction_current_bidder = None  # Current high bidder player index
        self.auction_current_bid = 0
        self.auction_bidder_index = 0  # Which player's turn to bid
        self.auction_passed_players = []  # Players who passed
        
        # House/Hotel supply limits (real Monopoly rules)
        self.houses_remaining = 32
        self.hotels_remaining = 12
        
        # Free Parking pot (house rule)
        self.free_parking_pot = 0
        
        self.panels = {}
        self.buttons: Dict[int, Dict[str, PygletButton]] = {}
        
        self._calculate_board_geometry()
    
    def _calculate_board_geometry(self):
        """Calculate board position"""
        h_panel = int(self.height * 0.10)
        v_panel = int(self.width * 0.12)
        margin = 20
        
        avail_w = self.width - (2 * v_panel) - (2 * margin)
        avail_h = self.height - (2 * h_panel) - (2 * margin)
        
        size = min(avail_w, avail_h)
        x = v_panel + margin + (avail_w - size) // 2
        y = h_panel + margin + (avail_h - size) // 2
        
        self.board_rect = (x, y, size, size)
        self._calculate_spaces()
    
    def _calculate_spaces(self):
        """Calculate all 40 space positions"""
        bx, by, size, _ = self.board_rect
        corner = size // 11
        edge = size // 11
        
        self.spaces = []
        
        # Bottom (0-10)
        for i in range(11):
            w = corner if i in [0, 10] else edge
            x = bx + size - sum([corner if j in [0, 10] else edge for j in range(i+1)])
            self.spaces.append((x, by + size - corner, w, corner))
        
        # Left (11-19)
        for i in range(1, 10):
            y = by + size - sum([corner if j in [0, 10] else edge for j in range(i+1)])
            self.spaces.append((bx, y, corner, edge))
        
        # Top (20-30)
        for i in range(11):
            w = corner if i in [0, 10] else edge
            x = bx + sum([corner if j in [0, 10] else edge for j in range(i)])
            self.spaces.append((x, by, w, corner))
        
        # Right (31-39)
        for i in range(1, 10):
            y = by + sum([corner if j in [0, 10] else edge for j in range(i)])
            self.spaces.append((bx + size - corner, y, corner, edge))
    
    def _init_buttons(self):
        """Initialize buttons for all players using PlayerPanel objects"""
        self.buttons = {}
        for idx in self.active_players:
            self._restore_default_buttons(idx)
    
    def _restore_default_buttons(self, player_idx: int):
        """Restore default panel buttons (Roll/End, Props, Build) or Jail options"""
        panel = self.panels[player_idx]
        button_rects = panel.get_button_layout()
        orient = panel.orientation
        
        player = self.players[player_idx]
        
        # Check if player is in jail
        if player.in_jail:
            # Show jail-specific buttons
            can_pay = player.money >= 50
            has_card = player.get_out_of_jail_cards > 0
            
            self.buttons[player_idx] = {
                "action": PygletButton(button_rects[0], "Roll", orient),
                "props": PygletButton(button_rects[1], "Pay $50" if can_pay else "No $", orient),
                "build": PygletButton(button_rects[2], "Use Card" if has_card else "", orient)
            }
            self.buttons[player_idx]["props"].enabled = can_pay
            self.buttons[player_idx]["build"].enabled = has_card
        else:
            # Normal buttons
            action_text = "Roll" if self.can_roll else "End Turn"
            
            self.buttons[player_idx] = {
                "action": PygletButton(button_rects[0], action_text, orient),
                "props": PygletButton(button_rects[1], "Deeds", orient),
                "build": PygletButton(button_rects[2], "Trade", orient)
            }
        # Enabled state will be set in update loop based on player properties
    
    def _set_popup_buttons(self, player_idx: int, button_texts: List[str], enabled_states: List[bool]):
        """Recreate panel buttons for popup context using same layout as default buttons"""
        panel = self.panels[player_idx]
        button_rects = panel.get_button_layout()  # Uses same layout as default buttons
        orient = panel.orientation
        
        # Completely recreate buttons dictionary with same size/position as default
        self.buttons[player_idx] = {}
        for i, (text, enabled) in enumerate(zip(button_texts, enabled_states)):
            if text:  # Only create button if text provided
                btn = PygletButton(button_rects[i], text, orient)
                btn.enabled = enabled
                self.buttons[player_idx][f"popup_{i}"] = btn
    
    def start_game(self, player_indices: List[int]):
        """Start game with selected players"""
        self.active_players = sorted(player_indices)
        self.players = [Player(i, PLAYER_COLORS[i]) for i in range(8)]
        
        all_panels = calculate_all_panels(self.width, self.height)
        for idx in self.active_players:
            self.panels[idx] = all_panels[idx]
            p = self.players[idx]
            p.money = STARTING_MONEY
            p.position = 0
            p.properties = []
            p.in_jail = False
            p.is_bankrupt = False
        
        self._init_buttons()
        self.current_player_idx = 0
        self.phase = "roll"
        self.can_roll = True
        self.state = "playing"
    
    def handle_input(self, fingertips: List[Dict]) -> bool:
        """Handle input, return True to exit"""
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
        
        if self.state == "winner":
            # Check for click on Back to Main Menu button
            if fingertips:
                for tip in fingertips:
                    if isinstance(tip, dict) and tip.get('id') == 1:  # Index finger
                        x, y = int(tip['x'] * self.width), int(tip['y'] * self.height)
                        
                        # Button bounds
                        btn_w = 300
                        btn_h = 60
                        btn_x = (self.width - btn_w) // 2
                        banner_y = (self.height - 400) // 2
                        btn_y = banner_y - 100
                        
                        if btn_x <= x <= btn_x + btn_w and btn_y <= y <= btn_y + btn_h:
                            # Reset to player selection
                            self.state = "player_select"
                            self.winner_idx = None
                            self.selection_ui = PlayerSelectionUI(self.width, self.height)
            return False
        
        current_time = time.time()
        current_player = self.players[self.active_players[self.current_player_idx]]
        
        # Handle all button inputs for ALL players (not just current)
        curr_idx = self.active_players[self.current_player_idx]
        
        for idx in self.active_players:
            if idx not in self.buttons:
                continue
            
            player = self.players[idx]
            is_current = (idx == curr_idx)
            
            btns = self.buttons[idx]
            
            # If popup active for this player, handle popup buttons
            if self.popup.active and self.popup.player_idx == idx:
                for name, btn in btns.items():
                    clicked, _ = btn.update(fingertips, current_time)
                    if clicked:
                        self._handle_popup_button_click(name)
            else:
                # Update and handle default buttons (only if they exist - not replaced by popup)
                # Check if this player has default buttons (not popup buttons)
                has_default_buttons = "action" in btns
                
                if has_default_buttons:
                    # Check if player is in jail - different button logic
                    if player.in_jail:
                        # Jail buttons - action (Roll) enabled for current player
                        # Props (Pay $50) stays as set in _restore_default_buttons
                        # Build (Use Card) stays as set in _restore_default_buttons
                        btns["action"].enabled = is_current and not self.dice_rolling
                        # Don't override props/build enabled states - already set correctly in _restore_default_buttons
                    else:
                        # Normal buttons - Action and Build only enabled for current player
                        # Props enabled for ANY player with properties
                        btns["action"].enabled = is_current and not self.dice_rolling
                        btns["action"].text = "Roll" if self.can_roll else "End"
                        btns["props"].enabled = len(player.properties) > 0  # Enabled for ANY player with properties
                        btns["build"].enabled = is_current and len(player.properties) > 0
                
                for name, btn in btns.items():
                    clicked, _ = btn.update(fingertips, current_time)
                    if clicked and (is_current or name == "props"):  # Only current player OR props button
                        self._handle_click(idx, name)
        
        return False
    
    def _handle_click(self, player_idx: int, button: str):
        """Handle button click"""
        player = self.players[player_idx]
        
        if button == "action":
            if player.in_jail:
                # In jail - just roll (will be handled in update)
                if self.can_roll:
                    self.roll_dice()
            elif self.can_roll:
                self.roll_dice()
            else:
                self.advance_turn()
        elif button == "props":
            if player.in_jail and player.money >= 50:
                # Pay to get out of jail
                player.remove_money(50)
                player.in_jail = False
                player.jail_turns = 0
                self._restore_default_buttons(player_idx)
            else:
                # Prevent non-current players from opening props during game-critical popups
                if self.popup.active and self.popup.popup_type in ["buy_prompt", "card"]:
                    curr_idx = self.active_players[self.current_player_idx]
                    if player_idx != curr_idx:
                        return  # Block non-current players during critical popups
                self._show_properties_popup(player)
        elif button == "build":
            if player.in_jail and player.get_out_of_jail_cards > 0:
                # Use get out of jail free card
                player.get_out_of_jail_cards -= 1
                player.in_jail = False
                player.jail_turns = 0
                self._restore_default_buttons(player_idx)
            else:
                self._start_trade(player)
    
    def _handle_popup_button_click(self, button_name: str):
        """Handle popup context button clicks from panel"""
        popup_type = self.popup.popup_type
        player_idx = self.popup.player_idx
        
        if button_name == "popup_0":  # First button
            if popup_type == "buy_prompt":
                player = self.popup.data["player"]
                position = self.popup.data["position"]
                self._buy_property(player, position)
            elif popup_type == "auction":
                # Bid button
                min_bid = self.popup.data["min_bid"]
                bidder_idx = self.popup.player_idx
                bidder = self.players[bidder_idx]
                
                if bidder.money >= min_bid:
                    self.auction_current_bid = min_bid
                    self.auction_current_bidder = bidder_idx
                    
                    # Reset passed players - everyone gets another chance to bid
                    self.auction_passed_players = []
                    
                    # Move to next bidder
                    self.popup.hide()
                    self._restore_default_buttons(bidder_idx)
                    self.auction_bidder_index = (self.auction_bidder_index + 1) % len(self.active_players)
                    self._show_auction_popup()
            elif popup_type == "build_prompt":
                # Pass button
                self.popup.hide()
                self._restore_default_buttons(player_idx)
                self._finish_turn_or_allow_double()
            elif popup_type in ["card", "properties"]:
                # OK or Close button
                self.popup.hide()
                self._restore_default_buttons(player_idx)
                if popup_type == "card":
                    # After card, check for doubles to allow re-roll
                    self._finish_turn_or_allow_double()
            elif popup_type == "trade_select":
                # Previous partner or Cancel
                prev_pos = self._find_prev_trade_partner()
                if prev_pos is not None:
                    self.trade_scroll_index = prev_pos
                    self._show_trade_partner_select()
                else:
                    # Cancel trade
                    initiator_idx = self.popup.data["initiator"].idx
                    self.popup.hide()
                    self._restore_default_buttons(initiator_idx)
                    self.trade_mode = None
            elif popup_type == "trade_build":
                # Cancel trade
                initiator_idx = self.popup.data["initiator"].idx
                self.popup.hide()
                self._restore_default_buttons(initiator_idx)
                self.trade_mode = None
            elif popup_type == "trade_modify":
                if self.trade_view_mode == "money":
                    # Cycle YOUR money amount (what you're giving)
                    amounts = [0, 50, 100, 200, 500]
                    current = self.trade_offer["money"]
                    try:
                        idx = amounts.index(current)
                        self.trade_offer["money"] = amounts[(idx + 1) % len(amounts)]
                    except ValueError:
                        self.trade_offer["money"] = 50
                    self._show_trade_modify()
                elif self.trade_view_mode == "give_props":
                    # Previous property or Back to money view
                    if self.trade_give_prop_scroll > 0:
                        self.trade_give_prop_scroll -= 1
                        self._show_trade_modify()
                    else:
                        self.trade_view_mode = "money"
                        self._show_trade_modify()
                elif self.trade_view_mode == "get_props":
                    # Previous property or Back to money view
                    if self.trade_get_prop_scroll > 0:
                        self.trade_get_prop_scroll -= 1
                        self._show_trade_modify()
                    else:
                        self.trade_view_mode = "money"
                        self._show_trade_modify()
            elif popup_type == "trade_detail":
                # Decline from detail view
                partner_idx = self.popup.data["partner"].idx
                initiator_idx = self.popup.data["initiator"].idx
                self.popup.hide()
                self._restore_default_buttons(partner_idx)
                self._restore_default_buttons(initiator_idx)
                self.trade_mode = None
            elif popup_type == "trade_response":
                # Decline trade
                partner_idx = self.popup.data["partner"].idx
                initiator_idx = self.popup.data["initiator"].idx
                self.popup.hide()
                self._restore_default_buttons(partner_idx)
                self._restore_default_buttons(initiator_idx)
                self.trade_mode = None
            elif popup_type == "mortgage":
                # Previous property (◄) or Close button
                player = self.popup.data["player"]
                if self.mortgage_scroll_index > 0:
                    # Navigate to previous property
                    self.mortgage_scroll_index -= 1
                    self._show_mortgage_detail(player)
                else:
                    # Close button (when on first property)
                    self.popup.hide()
                    self._restore_default_buttons(player_idx)
        
        elif button_name == "popup_1":  # Second button  
            if popup_type == "buy_prompt":
                # Pass button - start auction
                position = self.popup.data["position"]
                self.popup.hide()
                self._restore_default_buttons(player_idx)
                self._start_auction(position)
            elif popup_type == "auction":
                # Pass button
                bidder_idx = self.popup.player_idx
                self.auction_passed_players.append(bidder_idx)
                
                # Move to next bidder
                self.popup.hide()
                self._restore_default_buttons(bidder_idx)
                self.auction_bidder_index = (self.auction_bidder_index + 1) % len(self.active_players)
                self._show_auction_popup()
            elif popup_type == "build_prompt":
                # Buy house/hotel button
                player = self.popup.data["player"]
                position = self.popup.data["position"]
                prop = self.properties[position]
                house_cost = prop.data.get("house_cost", 0)
                # Safety check: ensure house_cost is an integer
                if isinstance(house_cost, tuple):
                    house_cost = house_cost[0] if house_cost else 0
                
                # Check even building rule and supply limits
                if prop.houses < 5 and player.money >= house_cost and self._can_build_on_property(player.idx, position):
                    # Check if we have houses/hotels available
                    if prop.houses == 4 and self.hotels_remaining > 0:
                        # Building hotel - return 4 houses to bank
                        player.remove_money(house_cost)
                        prop.houses = 5
                        self.hotels_remaining -= 1
                        self.houses_remaining += 4
                    elif prop.houses < 4 and self.houses_remaining > 0:
                        # Building house
                        player.remove_money(house_cost)
                        prop.houses += 1
                        self.houses_remaining -= 1
                    self._show_build_prompt(player, position)  # Refresh popup
            elif popup_type == "mortgage":
                # Mortgage or Unmortgage button
                player = self.popup.data["player"]
                prop_idx = self.popup.data["prop_idx"]
                prop = self.properties[prop_idx]
                
                if prop.is_mortgaged:
                    # Unmortgage
                    unmortgage_cost = int(prop.data.get("mortgage_value", 0) * 1.1)
                    if player.money >= unmortgage_cost:
                        player.remove_money(unmortgage_cost)
                        prop.is_mortgaged = False
                        self._show_mortgage_detail(player)  # Refresh view
                else:
                    # Mortgage (only if no houses)
                    if prop.houses == 0:
                        mortgage_value = prop.data.get("mortgage_value", 0)
                        player.add_money(mortgage_value)
                        prop.is_mortgaged = True
                        self._show_mortgage_detail(player)  # Refresh view
            elif popup_type == "trade_select":
                # Select partner button
                partner_idx = self.popup.data["partner_idx"]
                self.trade_partner = partner_idx
                self.trade_mode = "build_offer"
                self._show_trade_modify()
            elif popup_type == "trade_build":
                # Modify offer
                self._show_trade_modify()
            elif popup_type == "trade_response":
                # View trade details
                self._show_trade_detail_view()
            elif popup_type == "trade_modify":
                if self.trade_view_mode == "money":
                    # Cycle THEIR money amount (what you're requesting)
                    amounts = [0, 50, 100, 200, 500]
                    current = self.trade_request["money"]
                    try:
                        idx = amounts.index(current)
                        self.trade_request["money"] = amounts[(idx + 1) % len(amounts)]
                    except ValueError:
                        self.trade_request["money"] = 50
                    self._show_trade_modify()
                elif self.trade_view_mode == "give_props":
                    # Toggle your property in offer
                    initiator = self.players[self.trade_initiator]
                    if initiator.properties:
                        prop_idx = initiator.properties[self.trade_give_prop_scroll]
                        if prop_idx in self.trade_offer["properties"]:
                            self.trade_offer["properties"].remove(prop_idx)
                        else:
                            self.trade_offer["properties"].append(prop_idx)
                        self._show_trade_modify()
                elif self.trade_view_mode == "get_props":
                    # Toggle their property in request
                    partner = self.players[self.trade_partner]
                    if partner.properties:
                        prop_idx = partner.properties[self.trade_get_prop_scroll]
                        if prop_idx in self.trade_request["properties"]:
                            self.trade_request["properties"].remove(prop_idx)
                        else:
                            self.trade_request["properties"].append(prop_idx)
                        self._show_trade_modify()
            elif popup_type == "trade_detail":
                # Back to response screen
                self._show_trade_proposal()
        
        elif button_name == "popup_2":  # Third button
            if popup_type == "build_prompt":
                # Sell house/hotel button
                player = self.popup.data["player"]
                position = self.popup.data["position"]
                
                if self.properties[position].houses > 0:
                    self._sell_house(player, position)
                    self._show_build_prompt(player, position)  # Refresh popup
            elif popup_type == "mortgage":
                # Next property (►) or Done
                player = self.popup.data["player"]
                if self.mortgage_scroll_index < len(player.properties) - 1:
                    self.mortgage_scroll_index += 1
                    self._show_mortgage_detail(player)
                else:
                    # Done - close popup
                    player_idx = self.popup.player_idx
                    self.popup.hide()
                    self._restore_default_buttons(player_idx)
            elif popup_type == "trade_select":
                # Next partner
                next_pos = self._find_next_trade_partner()
                if next_pos is not None:
                    self.trade_scroll_index = next_pos
                    self._show_trade_partner_select()
            elif popup_type == "trade_build":
                # Send trade proposal
                self.trade_mode = "await_response"
                self._show_trade_proposal()
            elif popup_type == "trade_response":
                # Accept trade
                self._execute_trade()
                self.popup.hide()
                self._restore_default_buttons(self.trade_initiator)
                self._restore_default_buttons(self.trade_partner)
                self.trade_mode = None
            elif popup_type == "trade_modify":
                if self.trade_view_mode == "money":
                    # Switch to property selection - ask which: give or get
                    # For now, cycle through: money -> give_props -> get_props -> done
                    initiator = self.players[self.trade_initiator]
                    partner = self.players[self.trade_partner]
                    if initiator.properties:
                        self.trade_view_mode = "give_props"
                        self.trade_give_prop_scroll = 0
                        self._show_trade_modify()
                    elif partner.properties:
                        self.trade_view_mode = "get_props"
                        self.trade_get_prop_scroll = 0
                        self._show_trade_modify()
                    else:
                        # No properties to trade, go to build screen
                        self._show_trade_build_offer()
                elif self.trade_view_mode == "give_props":
                    # Next property or switch to get_props
                    initiator = self.players[self.trade_initiator]
                    partner = self.players[self.trade_partner]
                    if self.trade_give_prop_scroll < len(initiator.properties) - 1:
                        self.trade_give_prop_scroll += 1
                        self._show_trade_modify()
                    elif partner.properties:
                        self.trade_view_mode = "get_props"
                        self.trade_get_prop_scroll = 0
                        self._show_trade_modify()
                    else:
                        # Done, go back to build
                        self.trade_view_mode = "money"
                        self._show_trade_build_offer()
                elif self.trade_view_mode == "get_props":
                    # Next property or done
                    partner = self.players[self.trade_partner]
                    if self.trade_get_prop_scroll < len(partner.properties) - 1:
                        self.trade_get_prop_scroll += 1
                        self._show_trade_modify()
                    else:
                        # Done, go back to build
                        self.trade_view_mode = "money"
                        self._show_trade_build_offer()
            elif popup_type == "trade_detail":
                # Accept trade from detail view
                self._execute_trade()
                self.popup.hide()
                self._restore_default_buttons(self.trade_initiator)
                self._restore_default_buttons(self.trade_partner)
                self.trade_mode = None
    
    def roll_dice(self):
        """Roll dice"""
        if not self.can_roll or self.dice_rolling:
            return
        self.dice_values = (0, 0)  # Clear previous dice when starting new roll
        self.dice_rolling = True
        self.dice_roll_start = time.time()
        self.can_roll = False
    
    def advance_turn(self):
        """Next player - ensure proper turn order"""
        # Reset current player's consecutive doubles
        current = self.players[self.active_players[self.current_player_idx]]
        current.consecutive_doubles = 0
        
        # Move to next player
        self.current_player_idx = (self.current_player_idx + 1) % len(self.active_players)
        self.phase = "roll"
        self.can_roll = True
        # Don't reset dice - they stay visible until next roll
    
    def update(self, dt: float):
        """Update game state"""
        if self.dice_rolling:
            elapsed = time.time() - self.dice_roll_start
            if elapsed >= 1.2:
                self.dice_rolling = False
                self.dice_values = (random.randint(1, 6), random.randint(1, 6))
                
                current = self.players[self.active_players[self.current_player_idx]]
                is_doubles = self.dice_values[0] == self.dice_values[1]
                
                # Handle jail situation
                if current.in_jail:
                    if is_doubles:
                        # Rolled doubles - get out of jail and move
                        current.in_jail = False
                        current.jail_turns = 0
                        current.consecutive_doubles = 0  # Don't count jail doubles
                        
                        spaces = sum(self.dice_values)
                        old_pos = current.position
                        new_pos = (current.position + spaces) % 40
                        self._start_token_animation(current.idx, old_pos, new_pos)
                        current.position = new_pos
                        
                        if current.position < old_pos:
                            current.add_money(PASSING_GO_MONEY)
                        
                        self._land_on_space(current)
                    else:
                        # Didn't roll doubles - increment jail turns
                        current.jail_turns += 1
                        if current.jail_turns >= 3:
                            # Must pay to get out after 3 turns
                            if current.money >= 50:
                                current.remove_money(50)
                                current.in_jail = False
                                current.jail_turns = 0
                                # Move with the dice roll
                                spaces = sum(self.dice_values)
                                old_pos = current.position
                                new_pos = (current.position + spaces) % 40
                                self._start_token_animation(current.idx, old_pos, new_pos)
                                current.position = new_pos
                                if current.position < old_pos:
                                    current.add_money(PASSING_GO_MONEY)
                                self._land_on_space(current)
                            else:
                                # Can't pay - bankrupt
                                self._handle_bankruptcy(current)
                        else:
                            # Still in jail, turn ends
                            self.advance_turn()
                    return
                
                # Not in jail - normal roll handling
                if is_doubles:
                    current.consecutive_doubles += 1
                    if current.consecutive_doubles >= 3:
                        # Third double - go to jail
                        current.position = JAIL_POSITION
                        current.in_jail = True
                        current.jail_turns = 0
                        current.consecutive_doubles = 0
                        self.advance_turn()
                        return
                else:
                    current.consecutive_doubles = 0
                
                # Move player with animation
                spaces = sum(self.dice_values)
                old_pos = current.position
                new_pos = (current.position + spaces) % 40
                self._start_token_animation(current.idx, old_pos, new_pos)
                current.position = new_pos
                
                if current.position < old_pos:
                    current.add_money(PASSING_GO_MONEY)
                
                self._land_on_space(current)
    
    def _show_buy_prompt(self, player: Player, position: int):
        """Show property purchase prompt as floating text box with panel buttons"""
        # Close any existing popup first
        if self.popup.active:
            old_player_idx = self.popup.player_idx
            self.popup.hide()
            if old_player_idx is not None:
                self._restore_default_buttons(old_player_idx)
        
        panel = self.panels[player.idx]
        space = self.properties[position]
        price = space.data.get("price", 0)
        
        text_lines = create_monopoly_buy_popup(player.money, space.data["name"], price)
        
        self.popup.show(
            player.idx, panel.rect, panel.orientation, "buy_prompt", text_lines,
            {"player": player, "position": position, "price": price}
        )
        
        # Set popup-specific buttons in panel
        can_afford = player.money >= price
        self._set_popup_buttons(player.idx, ["Buy" if can_afford else "Can't Buy", "Pass", ""], 
                               [can_afford, True, False])
    
    def _sell_house(self, player: Player, position: int):
        """Sell house/hotel back to bank for half price"""
        prop = self.properties[position]
        house_cost = prop.data.get("house_cost", 0)
        # Safety check: ensure house_cost is an integer
        if isinstance(house_cost, tuple):
            house_cost = house_cost[0] if house_cost else 0
        sell_price = house_cost // 2
        
        if prop.houses == 5:
            # Selling hotel - return 1 hotel, give 4 houses back (if available)
            prop.houses = 4
            self.hotels_remaining += 1
            if self.houses_remaining >= 4:
                self.houses_remaining -= 4
            else:
                # Not enough houses available, sell to 0
                prop.houses = 0
                player.add_money(sell_price * 5)  # Sell all 5 as houses
                return
        elif prop.houses > 0:
            # Selling house
            prop.houses -= 1
            self.houses_remaining += 1
        
        player.add_money(sell_price)
    
    def _show_build_prompt(self, player: Player, position: int):
        """Show building prompt when landing on own property with monopoly"""
        # Close any existing popup first
        if self.popup.active:
            old_player_idx = self.popup.player_idx
            self.popup.hide()
            if old_player_idx is not None:
                self._restore_default_buttons(old_player_idx)
        
        panel = self.panels[player.idx]
        space = self.properties[position]
        house_cost = space.data.get("house_cost", 0)
        # Safety check: ensure house_cost is an integer
        if isinstance(house_cost, tuple):
            house_cost = house_cost[0] if house_cost else 0
        
        # Check current houses
        houses = space.houses
        
        if houses == 5:
            status = "Hotel built!"
            color = (255, 215, 0)
        elif houses == 4:
            status = f"{houses} Houses"
            color = (100, 255, 100)
        else:
            status = f"{houses} Houses" if houses > 0 else "No houses"
            color = (200, 200, 200)
        
        text_lines = [
            (space.data.get("name", "Property"), 14, (255, 255, 255)),
            (status, 10, color),
            (f"Cost: ${house_cost}", 9, (255, 255, 100)),
            (f"Bank: {self.houses_remaining}🏠 {self.hotels_remaining}🏨", 8, (180, 180, 180)),
        ]
        
        self.popup.show(
            player.idx, panel.rect, panel.orientation, "build_prompt", text_lines,
            {"player": player, "position": position}
        )
        
        # Set build buttons - check supply limits
        can_build = houses < 5 and player.money >= house_cost and not space.is_mortgaged
        if houses == 4:
            # Buying hotel needs 1 hotel available
            can_build = can_build and self.hotels_remaining > 0
        else:
            # Buying house needs 1 house available
            can_build = can_build and self.houses_remaining > 0
        
        can_sell = houses > 0
        
        if houses == 5:
            # Hotel - can only sell
            self._set_popup_buttons(player.idx, ["Pass", "Sell Hotel", ""], [True, can_sell, False])
        else:
            # Houses or empty
            self._set_popup_buttons(player.idx, 
                                   ["Pass", "Buy" if can_build else "No Supply" if (houses < 4 and self.houses_remaining == 0) or (houses == 4 and self.hotels_remaining == 0) else "No $", "Sell" if can_sell else ""],
                                   [True, can_build, can_sell])
    
    def _show_card_popup(self, player: Player, card: Dict, deck_type: str):
        """Show card dialog as floating text box"""
        # Close any existing popup first
        if self.popup.active:
            old_player_idx = self.popup.player_idx
            self.popup.hide()
            if old_player_idx is not None:
                self._restore_default_buttons(old_player_idx)
        
        panel = self.panels[player.idx]
        
        text_lines = create_monopoly_card_popup(card.get("text", ""), deck_type)
        
        self.popup.show(
            player.idx, panel.rect, panel.orientation, "card", text_lines,
            {"player": player, "card": card, "deck_type": deck_type}
        )
        
        # Set OK button in panel
        self._set_popup_buttons(player.idx, ["OK", "", ""], [True, False, False])
    
    def _show_properties_popup(self, player: Player):
        """Show mortgage/property management popup"""
        if not player.properties:
            return
        
        # Close any existing popup first
        if self.popup.active:
            old_player_idx = self.popup.player_idx
            self.popup.hide()
            if old_player_idx is not None:
                self._restore_default_buttons(old_player_idx)
        
        # Reset scroll to first property
        self.mortgage_scroll_index = 0
        self._show_mortgage_detail(player)
    
    def _show_mortgage_detail(self, player: Player):
        """Show detailed view of a single property with mortgage options"""
        if not player.properties:
            return
        
        # Ensure scroll index is valid
        self.mortgage_scroll_index = max(0, min(self.mortgage_scroll_index, len(player.properties) - 1))
        
        prop_idx = player.properties[self.mortgage_scroll_index]
        prop = self.properties[prop_idx]
        prop_data = prop.data
        
        panel = self.panels[player.idx]
        
        # Build text lines for property details
        name = prop_data.get("name", "Unknown")
        mortgage_val = prop_data.get("mortgage_value", 0)
        unmortgage_cost = int(mortgage_val * 1.1)
        
        text_lines = [
            (name, 14, (255, 255, 255)),
            (f"Property {self.mortgage_scroll_index + 1}/{len(player.properties)}", 10, (200, 200, 200)),
        ]
        
        if prop.is_mortgaged:
            text_lines.append(("MORTGAGED", 12, (255, 100, 100)))
            text_lines.append((f"Unmortgage: ${unmortgage_cost}", 10, (255, 255, 100)))
        else:
            if prop.houses > 0:
                text_lines.append((f"Houses: {prop.houses}", 10, (100, 255, 100)))
                text_lines.append(("Sell houses first", 9, (255, 200, 100)))
            else:
                text_lines.append((f"Mortgage Value: ${mortgage_val}", 10, (100, 255, 100)))
        
        self.popup.show(
            player.idx, panel.rect, panel.orientation, "mortgage", text_lines,
            {"player": player, "prop_idx": prop_idx}
        )
        
        # Set navigation and action buttons
        # Layout: [◄/Close] [Mortgage/Unmortgage] [►/Done]
        can_prev = self.mortgage_scroll_index > 0
        can_next = self.mortgage_scroll_index < len(player.properties) - 1
        
        # Left button: ◄ if can go back, otherwise Close
        left_btn = "◄" if can_prev else "Close"
        # Right button: ► if can go forward, otherwise Done
        right_btn = "►" if can_next else "Done"
        left_enabled = True  # Always enabled (either navigate or close)
        right_enabled = True  # Always enabled (either navigate or done)
        
        if prop.is_mortgaged:
            # Can unmortgage if player has enough money
            can_unmortgage = player.money >= unmortgage_cost
            self._set_popup_buttons(player.idx, 
                                   [left_btn, "Unmortgage" if can_unmortgage else "No $", right_btn],
                                   [left_enabled, can_unmortgage, right_enabled])
        elif prop.houses > 0:
            # Property has houses - can't mortgage, show info
            self._set_popup_buttons(player.idx,
                                   [left_btn, "Has Houses", right_btn],
                                   [left_enabled, False, right_enabled])
        else:
            # Can mortgage
            self._set_popup_buttons(player.idx,
                                   [left_btn, "Mortgage", right_btn],
                                   [left_enabled, True, right_enabled])
    
    def _start_trade(self, player: Player):
        """Start trade flow - select partner"""
        # Close any existing popup
        if self.popup.active:
            old_player_idx = self.popup.player_idx
            self.popup.hide()
            if old_player_idx is not None:
                self._restore_default_buttons(old_player_idx)
        
        # Reset trade state
        self.trade_initiator = player.idx
        self.trade_partner = None
        self.trade_offer = {"money": 0, "properties": []}
        self.trade_request = {"money": 0, "properties": []}
        self.trade_scroll_index = 0
        self.trade_mode = "select_partner"
        
        # Find first valid partner
        for idx in self.active_players:
            if idx != player.idx and not self.players[idx].is_bankrupt:
                self.trade_scroll_index = self.active_players.index(idx)
                break
        
        self._show_trade_partner_select()
    
    def _show_trade_partner_select(self):
        """Show partner selection screen"""
        initiator = self.players[self.trade_initiator]
        partner_idx = self.active_players[self.trade_scroll_index]
        partner = self.players[partner_idx]
        
        panel = self.panels[initiator.idx]
        
        text_lines = [
            ("Select Trade Partner", 14, (255, 255, 255)),
            (f"Player {partner_idx + 1}", 12, PLAYER_COLORS[partner_idx]),
            (f"${partner.money}", 10, (100, 255, 100)),
            (f"{len(partner.properties)} Properties", 10, (200, 200, 200)),
        ]
        
        self.popup.show(
            initiator.idx, panel.rect, panel.orientation, "trade_select", text_lines,
            {"initiator": initiator, "partner_idx": partner_idx}
        )
        
        # [◄] [Select] [►]
        can_prev = self._find_prev_trade_partner() is not None
        can_next = self._find_next_trade_partner() is not None
        
        self._set_popup_buttons(initiator.idx,
                               ["◄" if can_prev else "Cancel", "Select", "►" if can_next else ""],
                               [True, partner_idx != initiator.idx, can_next])
    
    def _find_prev_trade_partner(self) -> Optional[int]:
        """Find previous valid trade partner"""
        current_pos = self.trade_scroll_index
        for i in range(current_pos - 1, -1, -1):
            idx = self.active_players[i]
            if idx != self.trade_initiator and not self.players[idx].is_bankrupt:
                return i
        return None
    
    def _find_next_trade_partner(self) -> Optional[int]:
        """Find next valid trade partner"""
        current_pos = self.trade_scroll_index
        for i in range(current_pos + 1, len(self.active_players)):
            idx = self.active_players[i]
            if idx != self.trade_initiator and not self.players[idx].is_bankrupt:
                return i
        return None
    
    def _show_trade_build_offer(self):
        """Show screen to build trade offer"""
        initiator = self.players[self.trade_initiator]
        partner = self.players[self.trade_partner]
        
        panel = self.panels[initiator.idx]
        
        # Build summary
        offering = f"${self.trade_offer['money']}" if self.trade_offer['money'] > 0 else "Nothing"
        if self.trade_offer['properties']:
            offering += f" + {len(self.trade_offer['properties'])} prop(s)"
        
        requesting = f"${self.trade_request['money']}" if self.trade_request['money'] > 0 else "Nothing"
        if self.trade_request['properties']:
            requesting += f" + {len(self.trade_request['properties'])} prop(s)"
        
        text_lines = [
            (f"Trade with P{partner.idx + 1}", 14, PLAYER_COLORS[partner.idx]),
            (f"Offering: {offering}", 10, (100, 255, 100)),
            (f"For: {requesting}", 10, (255, 255, 100)),
            ("Build your offer", 9, (200, 200, 200)),
        ]
        
        self.popup.show(
            initiator.idx, panel.rect, panel.orientation, "trade_build", text_lines,
            {"initiator": initiator, "partner": partner}
        )
        
        # [Add $] [Add Prop] [Send]
        self._set_popup_buttons(initiator.idx,
                               ["Cancel", "Modify", "Send"],
                               [True, True, True])
    
    def _show_trade_proposal(self):
        """Show trade proposal to partner"""
        initiator = self.players[self.trade_initiator]
        partner = self.players[self.trade_partner]
        
        panel = self.panels[partner.idx]
        
        # What they're offering you
        getting = f"${self.trade_offer['money']}" if self.trade_offer['money'] > 0 else "Nothing"
        if self.trade_offer['properties']:
            getting += f" + {len(self.trade_offer['properties'])} prop(s)"
        
        # What they want from you
        giving = f"${self.trade_request['money']}" if self.trade_request['money'] > 0 else "Nothing"
        if self.trade_request['properties']:
            giving += f" + {len(self.trade_request['properties'])} prop(s)"
        
        text_lines = [
            (f"P{initiator.idx + 1} offers trade", 14, PLAYER_COLORS[initiator.idx]),
            (f"You get: {getting}", 10, (100, 255, 100)),
            (f"You give: {giving}", 10, (255, 100, 100)),
            ("Accept or Decline?", 9, (200, 200, 200)),
        ]
        
        self.popup.show(
            partner.idx, panel.rect, panel.orientation, "trade_response", text_lines,
            {"initiator": initiator, "partner": partner}
        )
        
        # [Decline] [Counter] [Accept]
        self._set_popup_buttons(partner.idx,
                               ["Decline", "View", "Accept"],
                               [True, True, True])
    def _show_trade_modify(self):
        """Show interface to modify trade offer (add money/properties)"""
        initiator = self.players[self.trade_initiator]
        partner = self.players[self.trade_partner]
        
        panel = self.panels[initiator.idx]
        
        offer_props_count = len(self.trade_offer["properties"])
        request_props_count = len(self.trade_request["properties"])
        
        if self.trade_view_mode == "money":
            # Money view
            text_lines = [
                (f"Trade with P{partner.idx + 1}", 14, PLAYER_COLORS[partner.idx]),
                ("--- YOU GIVE ---", 11, (255, 100, 100)),
                (f"${self.trade_offer['money']}", 10, (255, 150, 150)),
                (f"{offer_props_count} Props", 9, (255, 180, 180)),
                ("--- YOU GET ---", 11, (100, 255, 100)),
                (f"${self.trade_request['money']}", 10, (150, 255, 150)),
                (f"{request_props_count} Props", 9, (180, 255, 180)),
            ]
            self._set_popup_buttons(initiator.idx,
                                   ["Give $", "Get $", "Done"],
                                   [True, True, True])
        
        elif self.trade_view_mode == "give_props":
            # Your properties view - filter out mortgaged and properties with houses
            your_props = [p for p in initiator.properties 
                         if not self.properties[p].is_mortgaged and self.properties[p].houses == 0]
            if your_props:
                self.trade_give_prop_scroll = max(0, min(self.trade_give_prop_scroll, len(your_props) - 1))
                prop_idx = your_props[self.trade_give_prop_scroll]
                prop = self.properties[prop_idx]
                prop_name = prop.data.get("name", "Unknown")[:15]
                is_selected = prop_idx in self.trade_offer["properties"]
                
                text_lines = [
                    ("YOUR PROPERTIES", 14, (255, 100, 100)),
                    (f"{self.trade_give_prop_scroll + 1}/{len(your_props)}", 10, (200, 200, 200)),
                    (prop_name, 12, (255, 255, 255)),
                    ("✓ Selected" if is_selected else "Not selected", 10, (100, 255, 100) if is_selected else (150, 150, 150)),
                ]
                
                can_prev = self.trade_give_prop_scroll > 0
                can_next = self.trade_give_prop_scroll < len(your_props) - 1
                self._set_popup_buttons(initiator.idx,
                                       ["◄" if can_prev else "Back", "Toggle", "►" if can_next else "Done"],
                                       [True, True, can_next or True])
            else:
                text_lines = [("No properties", 12, (200, 200, 200))]
                self._set_popup_buttons(initiator.idx, ["Back", "", ""], [True, False, False])
        
        elif self.trade_view_mode == "get_props":
            # Their properties view - filter out mortgaged and properties with houses
            their_props = [p for p in partner.properties 
                          if not self.properties[p].is_mortgaged and self.properties[p].houses == 0]
            if their_props:
                self.trade_get_prop_scroll = max(0, min(self.trade_get_prop_scroll, len(their_props) - 1))
                prop_idx = their_props[self.trade_get_prop_scroll]
                prop = self.properties[prop_idx]
                prop_name = prop.data.get("name", "Unknown")[:15]
                is_selected = prop_idx in self.trade_request["properties"]
                
                text_lines = [
                    ("THEIR PROPERTIES", 14, (100, 255, 100)),
                    (f"{self.trade_get_prop_scroll + 1}/{len(their_props)}", 10, (200, 200, 200)),
                    (prop_name, 12, (255, 255, 255)),
                    ("✓ Selected" if is_selected else "Not selected", 10, (100, 255, 100) if is_selected else (150, 150, 150)),
                ]
                
                can_prev = self.trade_get_prop_scroll > 0
                can_next = self.trade_get_prop_scroll < len(their_props) - 1
                self._set_popup_buttons(initiator.idx,
                                       ["◄" if can_prev else "Back", "Toggle", "►" if can_next else "Done"],
                                       [True, True, can_next or True])
            else:
                text_lines = [("No properties", 12, (200, 200, 200))]
                self._set_popup_buttons(initiator.idx, ["Back", "", ""], [True, False, False])
        
        self.popup.show(
            initiator.idx, panel.rect, panel.orientation, "trade_modify", text_lines,
            {"initiator": initiator, "partner": partner}
        )
    
    def _show_trade_detail_view(self):
        """Show detailed view of trade properties for partner"""
        initiator = self.players[self.trade_initiator]
        partner = self.players[self.trade_partner]
        
        panel = self.panels[partner.idx]
        
        # Show what properties are involved
        offer_props = [self.properties[i].data.get("name", "???")[:12] for i in self.trade_offer["properties"][:2]]
        request_props = [self.properties[i].data.get("name", "???")[:12] for i in self.trade_request["properties"][:2]]
        
        text_lines = [
            (f"P{initiator.idx + 1}'s Offer", 12, PLAYER_COLORS[initiator.idx]),
            (f"${self.trade_offer['money']}", 10, (100, 255, 100)),
        ]
        for prop_name in offer_props:
            text_lines.append((prop_name, 9, (200, 200, 200)))
        
        text_lines.append(("For:", 10, (255, 255, 100)))
        text_lines.append((f"${self.trade_request['money']}", 10, (255, 100, 100)))
        for prop_name in request_props:
            text_lines.append((prop_name, 9, (200, 200, 200)))
        
        self.popup.show(
            partner.idx, panel.rect, panel.orientation, "trade_detail", text_lines,
            {"initiator": initiator, "partner": partner}
        )
        
        # [Decline] [] [Accept]
        self._set_popup_buttons(partner.idx,
                               ["Decline", "Back", "Accept"],
                               [True, True, True])
    
    def _execute_trade(self):
        """Execute the trade between initiator and partner"""
        initiator = self.players[self.trade_initiator]
        partner = self.players[self.trade_partner]
        
        # Validate trade - check for mortgaged properties or houses
        for prop_idx in self.trade_offer["properties"] + self.trade_request["properties"]:
            prop = self.properties[prop_idx]
            if prop.is_mortgaged or prop.houses > 0:
                # Invalid trade - show error and cancel
                return
        
        # Transfer money
        if self.trade_offer["money"] > 0:
            initiator.remove_money(self.trade_offer["money"])
            partner.add_money(self.trade_offer["money"])
        
        if self.trade_request["money"] > 0:
            partner.remove_money(self.trade_request["money"])
            initiator.add_money(self.trade_request["money"])
        
        # Transfer properties from initiator to partner
        for prop_idx in self.trade_offer["properties"]:
            if prop_idx in initiator.properties:
                initiator.properties.remove(prop_idx)
                partner.properties.append(prop_idx)
                self.properties[prop_idx].owner = partner.idx
        
        # Transfer properties from partner to initiator
        for prop_idx in self.trade_request["properties"]:
            if prop_idx in partner.properties:
                partner.properties.remove(prop_idx)
                initiator.properties.append(prop_idx)
                self.properties[prop_idx].owner = initiator.idx
    
    def _land_on_space(self, player: Player):
        """Handle landing on space"""
        if GameLogic.check_passed_go(player):
            player.add_money(PASSING_GO_MONEY)
        
        pos = player.position
        space = self.properties[pos]
        space_type = space.data.get("type")
        
        if space_type == "go":
            player.add_money(PASSING_GO_MONEY)
            self._finish_turn_or_allow_double()
        
        elif space_type in ("property", "railroad", "utility"):
            if space.owner is None:
                self.phase = "buying"
                self._show_buy_prompt(player, pos)
            elif space.owner != player.idx:
                self.phase = "paying_rent"
                self._pay_rent(player, pos)
            else:
                # Landed on own property - check if can build
                if space_type == "property" and self._has_monopoly(player.idx, pos):
                    self.phase = "building"
                    self._show_build_prompt(player, pos)
                else:
                    self.phase = "action"
                    self.can_roll = False
        
        elif space_type == "go_to_jail":
            self._send_to_jail(player)
        
        elif space_type == "chance":
            card = GameLogic.draw_card("chance", self.chance_deck, self.community_chest_deck)
            self._execute_card_action(player, card)
            self._show_card_popup(player, card, "chance")
        
        elif space_type == "community_chest":
            card = GameLogic.draw_card("community_chest", self.chance_deck, self.community_chest_deck)
            self._execute_card_action(player, card)
            self._show_card_popup(player, card, "community_chest")
        
        elif space_type == "income_tax":
            tax_amount = INCOME_TAX if isinstance(INCOME_TAX, int) else 200
            player.remove_money(tax_amount)
            self.free_parking_pot += tax_amount
            self._finish_turn_or_allow_double()
        
        elif space_type == "luxury_tax":
            tax_amount = LUXURY_TAX if isinstance(LUXURY_TAX, int) else 100
            player.remove_money(tax_amount)
            self.free_parking_pot += tax_amount
            self._finish_turn_or_allow_double()
        
        elif space_type == "free_parking":
            # Collect Free Parking pot
            if self.free_parking_pot > 0:
                player.add_money(self.free_parking_pot)
                self.free_parking_pot = 0
            self._finish_turn_or_allow_double()
        
        else:
            self._finish_turn_or_allow_double()
        
        if player.money < 0:
            self._handle_bankruptcy(player)
    
    def _has_monopoly(self, player_idx: int, position: int) -> bool:
        """Check if player owns all properties in the group"""
        from monopoly_data import PROPERTY_GROUPS
        
        prop = self.properties[position]
        prop_group = prop.data.get("group")
        
        if not prop_group or prop_group not in PROPERTY_GROUPS:
            return False
        
        # Get all positions in this group
        group_positions = PROPERTY_GROUPS[prop_group]
        
        # Check if player owns all properties in group
        player = self.players[player_idx]
        for pos in group_positions:
            if pos not in player.properties:
                return False
        
        return True
    
    def _can_build_on_property(self, player_idx: int, position: int) -> bool:
        """Check if player can build on this property (even building rule)"""
        from monopoly_data import PROPERTY_GROUPS
        
        prop = self.properties[position]
        prop_group = prop.data.get("group")
        
        if not prop_group or prop_group not in PROPERTY_GROUPS:
            return False
        
        # Can't build if any property in group is mortgaged
        group_positions = PROPERTY_GROUPS[prop_group]
        for pos in group_positions:
            if self.properties[pos].is_mortgaged:
                return False
        
        # Must build evenly - can't build if any property in group has fewer houses
        current_houses = prop.houses
        for pos in group_positions:
            if pos != position and self.properties[pos].houses < current_houses:
                return False
        
        return True
    
    def _start_auction(self, property_index: int):
        """Start an auction for a property"""
        self.auction_active = True
        self.auction_property = property_index
        self.auction_current_bid = 0
        self.auction_current_bidder = None
        self.auction_passed_players = []
        
        # Start with next player after current player who declined
        self.auction_bidder_index = (self.current_player_idx + 1) % len(self.active_players)
        
        # Show auction popup for first bidder
        self._show_auction_popup()
    
    def _show_auction_popup(self):
        """Show auction bidding popup"""
        # Check if auction is over - everyone has passed since last bid
        if len(self.auction_passed_players) >= len(self.active_players):
            # Everyone passed - auction over
            self._end_auction()
            return
        
        # Get current bidder
        bidder_idx = self.active_players[self.auction_bidder_index]
        
        bidder_idx = self.active_players[self.auction_bidder_index]
        bidder = self.players[bidder_idx]
        prop = self.properties[self.auction_property]
        
        panel = self.panels[bidder_idx]
        
        high_bidder_text = f"High bid: ${self.auction_current_bid}" if self.auction_current_bid > 0 else "No bids yet"
        min_bid = self.auction_current_bid + 10
        
        text_lines = [
            (f"AUCTION: {prop.data.get('name', 'Property')}", 14, (255, 255, 255)),
            (high_bidder_text, 10, (255, 215, 0)),
            (f"Min bid: ${min_bid}", 10, (200, 200, 200)),
            (f"Your money: ${bidder.money}", 9, (100, 255, 100)),
        ]
        
        can_bid = bidder.money >= min_bid
        
        self.popup.show(
            bidder_idx, panel.rect, panel.orientation, "auction", text_lines,
            {"property_idx": self.auction_property, "min_bid": min_bid}
        )
        
        self._set_popup_buttons(bidder_idx, ["Bid" if can_bid else "No $", "Pass", ""], 
                               [can_bid, True, False])
    
    def _end_auction(self):
        """End the auction and award property"""
        if self.auction_current_bidder is not None:
            # Someone won the auction
            winner = self.players[self.auction_current_bidder]
            winner.remove_money(self.auction_current_bid)
            self.properties[self.auction_property].owner = self.auction_current_bidder
            winner.properties.append(self.auction_property)
        
        # Reset auction state
        self.auction_active = False
        self.auction_property = None
        self.auction_current_bid = 0
        self.auction_current_bidder = None
        self.auction_passed_players = []
        
        # Continue game
        self._finish_turn_or_allow_double()
    
    def _finish_turn_or_allow_double(self):
        """End turn or allow rolling again for doubles"""
        current = self.get_current_player()
        if current.consecutive_doubles > 0:
            self.phase = "roll"
            self.can_roll = True
        else:
            self.advance_turn()
    
    def get_current_player(self) -> Player:
        """Get current player"""
        return self.players[self.active_players[self.current_player_idx]]
    
    def _buy_property(self, player: Player, position: int):
        """Purchase a property"""
        space = self.properties[position]
        price = space.data.get("price", 0)
        
        if player.remove_money(price):
            space.owner = player.idx
            player.properties.append(position)
        
        self.popup.hide()
        self._restore_default_buttons(player.idx)
        # Allow player to continue their turn (build, trade, etc.)
        self.phase = "action"
        self.can_roll = False
    
    def _pay_rent(self, player: Player, position: int):
        """Pay rent to property owner"""
        space = self.properties[position]
        owner = self.players[space.owner]
        
        dice_sum = sum(self.dice_values) if space.data.get("type") == "utility" else None
        rent = GameLogic.calculate_rent(space, dice_sum, owner, self.properties)
        
        if player.remove_money(rent):
            owner.add_money(rent)
        else:
            self._handle_bankruptcy(player, owed_to=owner)
        
        self._finish_turn_or_allow_double()
    
    def _send_to_jail(self, player: Player):
        """Send player to jail"""
        GameLogic.send_to_jail(player)
        self.advance_turn()
    
    def _show_winner(self, winner_idx: int):
        """Show winner screen"""
        self.state = "winner"
        self.winner_idx = winner_idx
    
    def _handle_bankruptcy(self, player: Player, owed_to: Optional[Player] = None):
        """Handle player bankruptcy"""
        player.is_bankrupt = True
        
        # Check if only one player remains
        active_count = sum(1 for idx in self.active_players if not self.players[idx].is_bankrupt)
        if active_count == 1:
            # Find the winner
            for idx in self.active_players:
                if not self.players[idx].is_bankrupt:
                    self._show_winner(idx)
                    return
        
        # Handle property transfer
        bankrupt_properties = list(player.properties)
        player.properties = []
        
        if owed_to:
            # Owed to another player - transfer all assets
            for prop_idx in bankrupt_properties:
                prop = self.properties[prop_idx]
                prop.owner = owed_to.idx
                owed_to.properties.append(prop_idx)
                # Keep houses and mortgage status
        else:
            # Owed to bank - auction all properties
            for prop_idx in bankrupt_properties:
                prop = self.properties[prop_idx]
                # Remove houses, keep mortgaged status
                prop.houses = 0
                prop.owner = None
                # Properties will be auctioned one by one
                # For now, just return to bank
                prop.is_mortgaged = False
        
        # Remove from active players
        if player.idx in self.active_players:
            idx_pos = self.active_players.index(player.idx)
            self.active_players.remove(player.idx)
            if self.current_player_idx >= len(self.active_players):
                self.current_player_idx = 0
    
    def _execute_card_action(self, player: Player, card: Dict):
        """Execute card action - handles all Community Chest and Chance card actions"""
        action = card.get("action")
        if not action:
            return
        
        action_type = action[0]
        
        # Money actions (positive = collect, negative = pay)
        if action_type == "money":
            amount = action[1]
            if amount > 0:
                player.add_money(amount)
            else:
                player.remove_money(abs(amount))
                # Add fines to Free Parking pot
                self.free_parking_pot += abs(amount)
        
        # Advance to specific position (with optional Go collection)
        elif action_type == "advance":
            position = action[1]
            collect_go = action[2] if len(action) > 2 else False
            old_pos = player.position
            
            # Check if passing Go
            if collect_go and position < old_pos:
                player.add_money(PASSING_GO_MONEY)
            
            self._start_token_animation(player.idx, old_pos, position)
            player.position = position
        
        # Move relative to current position (like "Go Back 3 Spaces")
        elif action_type == "advance_relative":
            spaces = action[1]
            old_pos = player.position
            new_pos = (player.position + spaces) % 40
            self._start_token_animation(player.idx, old_pos, new_pos)
            player.position = new_pos
            # No Go collection for relative moves (even if passing)
        
        # Go to Jail
        elif action_type == "go_to_jail":
            self._send_to_jail(player)
        
        # Get out of jail free card
        elif action_type == "jail_free":
            player.get_out_of_jail_free_cards += 1
        
        # Advance to nearest Railroad or Utility
        elif action_type == "advance_nearest":
            target_type = action[1]
            current_pos = player.position
            
            if target_type == "railroad":
                # Railroad positions: Reading(5), Pennsylvania(15), B&O(25), Short Line(35)
                railroad_positions = [5, 15, 25, 35]
                # Find nearest ahead (wrapping around)
                distances = [(pos - current_pos) % 40 for pos in railroad_positions]
                nearest_idx = distances.index(min(distances))
                nearest = railroad_positions[nearest_idx]
            else:  # utility
                # Utility positions: Electric(12), Water Works(28)
                utility_positions = [12, 28]
                distances = [(pos - current_pos) % 40 for pos in utility_positions]
                nearest_idx = distances.index(min(distances))
                nearest = utility_positions[nearest_idx]
            
            old_pos = player.position
            # Check if passing Go
            if nearest < old_pos:
                player.add_money(PASSING_GO_MONEY)
            
            self._start_token_animation(player.idx, old_pos, nearest)
            player.position = nearest
        
        # Collect from each other player
        elif action_type == "collect_from_each":
            amount = action[1]
            for other_idx in self.active_players:
                if other_idx != player.idx:
                    other = self.players[other_idx]
                    transfer = min(amount, other.money)
                    other.remove_money(transfer)
                    player.add_money(transfer)
        
        # Pay each other player
        elif action_type == "pay_each_player":
            amount = action[1]
            for other_idx in self.active_players:
                if other_idx != player.idx:
                    other = self.players[other_idx]
                    if player.money >= amount:
                        player.remove_money(amount)
                        other.add_money(amount)
                    else:
                        # Player can't afford, pay what they can
                        payment = player.money
                        player.remove_money(payment)
                        other.add_money(payment)
        
        # Pay per house/hotel (repairs)
        elif action_type == "pay_per_house_hotel":
            # Safety check: ensure action[1] is a tuple with costs
            costs = action[1] if len(action) > 1 else (0, 0)
            if isinstance(costs, tuple) and len(costs) >= 2:
                house_cost, hotel_cost = costs[0], costs[1]
            else:
                house_cost, hotel_cost = 0, 0
            
            total_cost = 0
            for prop_idx in player.properties:
                prop = self.properties[prop_idx]
                if prop.houses == 5:  # Hotel
                    total_cost += hotel_cost
                elif prop.houses > 0:  # Houses
                    total_cost += prop.houses * house_cost
            player.remove_money(total_cost)
            # Add to Free Parking pot
            self.free_parking_pot += total_cost
    
    def draw(self):
        """Draw game"""
        if self.state == "player_select":
            self._draw_player_select()
            return
        
        if self.state == "winner":
            self._draw_winner_screen()
            return
        
        # Background
        self.renderer.draw_rect((32, 96, 36), (0, 0, self.width, self.height))
        
        # Panels
        self._draw_panels()
        
        # Board
        self._draw_board()
        
        # Dice - show during roll animation or when values are set
        if self.dice_rolling or self.dice_values != (0, 0):
            self._draw_dice()
        
        # Hover indicators
        self._draw_hover_indicators()
        
        # Popups with dimming (batched, will be drawn after tokens)
        if self.popup.active:
            # Screen dimming to cover board text
            self.renderer.draw_rect((0, 0, 0, 50), (0, 0, self.width, self.height))
            self.popup.draw(self.renderer)
    
    def draw_immediate(self):
        """Draw tokens on top of board text using immediate rendering (called after batch rendering)"""
        if self.state != "player_select":
            self._draw_tokens()
    
    def _draw_panels(self):
        """Draw all player panels"""
        curr_idx = self.active_players[self.current_player_idx] if self.active_players else -1
        
        for idx in self.active_players:
            player = self.players[idx]
            panel = self.panels[idx]
            is_current = (idx == curr_idx)
            
            # Background with border
            panel.draw_background(self.renderer, is_current)
            
            # Info with orientation-aware text
            self._draw_panel_info(player, panel)
            
            # Buttons - show for ALL players (not just current)
            if idx in self.buttons:
                current_time = time.time()
                for btn in self.buttons[idx].values():
                    # Calculate progress for visual feedback
                    progress = 0.0
                    if btn.hovering and btn.hover_start > 0:
                        progress = min(1.0, (current_time - btn.hover_start) / HOVER_TIME_THRESHOLD)
                    btn.draw(self.renderer, progress)
    
    def _draw_panel_info(self, player: Player, panel: PlayerPanel):
        """Draw player balance and jail free card indicator"""
        x, y, w, h = panel.rect
        
        # Add jail free card symbol if player has any
        jail_indicator = " 🔑" if player.get_out_of_jail_cards > 0 else ""
        money_text = f"${player.money}{jail_indicator}"
        
        if panel.orientation == 0:  # Bottom - balance at top of panel
            tx = x + w // 2
            ty = y + int(h * 0.30)
            self.renderer.draw_text(
                money_text, tx, ty, 'Arial', 20, (0, 0, 0),
                bold=True, anchor_x='center', anchor_y='center', rotation=0
            )
        elif panel.orientation == 180:  # Top - balance at bottom of panel
            tx = x + w // 2
            ty = y + int(h * 0.70)
            self.renderer.draw_text(
                money_text, tx, ty, 'Arial', 20, (0, 0, 0),
                bold=True, anchor_x='center', anchor_y='center', rotation=180
            )
        elif panel.orientation == 270:  # Left - buttons left, balance right
            tx = x + int(w * 0.85)
            ty = y + h // 2
            self.renderer.draw_text(
                money_text, tx, ty, 'Arial', 16, (0, 0, 0),
                bold=True, anchor_x='center', anchor_y='center', rotation=90
            )
        else:  # 90 - Right - buttons right, balance left
            tx = x + int(w * 0.15)
            ty = y + h // 2
            self.renderer.draw_text(
                money_text, tx, ty, 'Arial', 16, (0, 0, 0),
                bold=True, anchor_x='center', anchor_y='center', rotation=270
            )
    
    def _draw_board(self):
        """Draw monopoly board with property colors and names"""
        bx, by, bw, bh = self.board_rect
        # Safety check: ensure dimensions are integers
        bx, by, bw, bh = int(bx), int(by), int(bw), int(bh)
        
        # Board background
        self.renderer.draw_rect((220, 240, 220), (bx, by, bw, bh))
        self.renderer.draw_rect((100, 100, 100), (bx, by, bw, bh), width=3)
        
        # Draw spaces with colors and names for ALL spaces
        for i, (sx, sy, sw, sh) in enumerate(self.spaces):
            space = self.properties[i]
            space_data = space.data
            space_type = space_data.get("type", "")
            
            # Background with subtle gradient effect
            self.renderer.draw_rect((250, 250, 250), (sx, sy, sw, sh))
            self.renderer.draw_rect((120, 120, 120), (sx, sy, sw, sh), width=1)
            
            # Color bar for properties (larger and more visible)
            if "color" in space_data and isinstance(space_data["color"], tuple):
                prop_color = space_data["color"]
                bar_h = max(10, sh // 3)
                self.renderer.draw_rect(prop_color, (sx, sy, sw, bar_h))
            
            # Draw owner border if property is owned
            if space.owner is not None and space_type in ["property", "railroad", "utility"]:
                owner_color = PLAYER_COLORS[space.owner]
                # Draw a thicker border on the inside
                self.renderer.draw_rect(owner_color, (sx + 2, sy + 2, sw - 4, sh - 4), width=4)
            
            # Draw house/hotel indicators
            if space.houses > 0 and space_type == "property":
                house_w = 6
                house_h = 6
                house_gap = 2
                
                if space.houses == 5:  # Hotel
                    # Draw single large indicator with H
                    hotel_x = sx + sw // 2 - 8
                    hotel_y = sy + sh - 12
                    self.renderer.draw_rect((255, 0, 0), (hotel_x, hotel_y, 16, 10))
                    self.renderer.draw_text("H", hotel_x + 8, hotel_y + 5, 
                                          'Arial', 8, (255, 255, 255),
                                          anchor_x='center', anchor_y='center')
                else:  # Houses (1-4)
                    total_width = space.houses * house_w + (space.houses - 1) * house_gap
                    start_x = sx + (sw - total_width) // 2
                    house_y = sy + sh - 10
                    
                    for i in range(space.houses):
                        house_x = start_x + i * (house_w + house_gap)
                        self.renderer.draw_rect((0, 200, 0), (house_x, house_y, house_w, house_h))
                        self.renderer.draw_rect((0, 100, 0), (house_x, house_y, house_w, house_h), width=1)
            
            # Draw space name with text wrapping - NO ROTATION, always readable from bottom
            # Hide names when popup is active to prevent overlap
            name = space_data.get("name", "")
            if name and not self.popup.active:
                cx, cy = sx + sw // 2, sy + sh // 2
                
                # Special handling for Free Parking to show pot
                if i == 20 and space_type == "free_parking":  # Free Parking is at position 20
                    # Draw "Free Parking" name
                    words = name.split()
                    lines = []
                    for word in words:
                        lines.append(word)
                    
                    # Add pot amount below
                    if self.free_parking_pot > 0:
                        lines.append(f"Pot: ${self.free_parking_pot}")
                    
                    # Draw multi-line text
                    font_size = 7
                    line_spacing = font_size + 2
                    total_height = len(lines) * line_spacing
                    start_y = cy - total_height // 2 + line_spacing // 2
                    
                    for idx_line, line in enumerate(lines):
                        ly = start_y + idx_line * line_spacing
                        # Pot amount in gold color
                        color = (255, 215, 0) if idx_line == len(lines) - 1 and self.free_parking_pot > 0 else (0, 0, 0)
                        self.renderer.draw_text(
                            line, cx, ly,
                            'Arial', font_size if idx_line < len(lines) - 1 else 6, color,
                            anchor_x='center', anchor_y='center',
                            rotation=0
                        )
                    continue
                
                # Wrap text to fit in space
                words = name.split()
                if len(words) > 1:
                    # Multiple words - split into lines
                    lines = []
                    current_line = ""
                    for word in words:
                        test_line = (current_line + " " + word).strip()
                        if len(test_line) <= 10:  # Max chars per line
                            current_line = test_line
                        else:
                            if current_line:
                                lines.append(current_line)
                            current_line = word
                    if current_line:
                        lines.append(current_line)
                    
                    # Draw multi-line text (reverse order because Y increases downward in pygame coords)
                    font_size = 7 if space_type in ["property", "railroad", "utility"] else 6
                    line_spacing = font_size + 2
                    total_height = len(lines) * line_spacing
                    start_y = cy - total_height // 2 + line_spacing // 2
                    
                    for i, line in enumerate(lines):
                        ly = start_y + i * line_spacing
                        self.renderer.draw_text(
                            line, cx, ly,
                            'Arial', font_size, (0, 0, 0),
                            anchor_x='center', anchor_y='center',
                            rotation=0
                        )
                else:
                    # Single word - adjust size if too long
                    if len(name) > 12:
                        font_size = 6  # Smaller for long words
                    elif len(name) > 10:
                        font_size = 7
                    else:
                        font_size = 8 if space_type in ["property", "railroad", "utility"] else 7
                    
                    self.renderer.draw_text(
                        name, cx, cy,
                        'Arial', font_size, (0, 0, 0),
                        anchor_x='center', anchor_y='center',
                        rotation=0
                    )
            
            # Border
            self.renderer.draw_rect((80, 80, 80), (sx, sy, sw, sh), width=1)
    
    def _start_token_animation(self, player_idx: int, from_pos: int, to_pos: int):
        """Start sequential jumping animation for token movement (one property at a time)"""
        # Calculate path of properties to move through
        path = []
        current = from_pos
        
        # Move one space at a time until reaching destination
        while current != to_pos:
            current = (current + 1) % 40
            path.append(current)
        
        # Each property takes 0.5 seconds
        self.token_animations[player_idx] = {
            'path': path,
            'start_pos': from_pos,  # Remember where we started
            'current_segment': 0,
            'start_time': time.time(),
            'segment_duration': 0.5  # 0.5 seconds per property
        }
    
    def _draw_tokens(self):
        """Draw player tokens with sequential jumping animation through each property"""
        current_time = time.time()
        
        for idx in self.active_players:
            player = self.players[idx]
            if player.is_bankrupt:
                continue
            
            # Check if token is animating
            if idx in self.token_animations:
                anim = self.token_animations[idx]
                path = anim['path']
                segment_duration = anim['segment_duration']
                total_elapsed = current_time - anim['start_time']
                
                # Determine which segment we're on
                current_segment = int(total_elapsed / segment_duration)
                
                if current_segment >= len(path):
                    # Animation complete
                    del self.token_animations[idx]
                    sx, sy, sw, sh = self.spaces[player.position]
                    cx, cy = sx + sw // 2, sy + sh // 2
                else:
                    # Interpolate within current segment
                    segment_progress = (total_elapsed - current_segment * segment_duration) / segment_duration
                    
                    # Get start and end positions for this segment
                    if current_segment == 0:
                        # First segment starts from the original starting position
                        start_pos = anim['start_pos']
                    else:
                        start_pos = path[current_segment - 1]
                    end_pos = path[current_segment]
                    
                    start_x, start_y, start_w, start_h = self.spaces[start_pos]
                    end_x, end_y, end_w, end_h = self.spaces[end_pos]
                    
                    start_cx = start_x + start_w // 2
                    start_cy = start_y + start_h // 2
                    end_cx = end_x + end_w // 2
                    end_cy = end_y + end_h // 2
                    
                    # Linear interpolation for x, y
                    cx = int(start_cx + (end_cx - start_cx) * segment_progress)
                    cy = int(start_cy + (end_cy - start_cy) * segment_progress)
                    
                    # Add jump height (parabolic: peaks at 0.5 progress)
                    jump_height = 40 * (1 - (2 * segment_progress - 1) ** 2)  # Max 40 pixels up
                    cy -= int(jump_height)
            else:
                # No animation - static position
                sx, sy, sw, sh = self.spaces[player.position]
                cx, cy = sx + sw // 2, sy + sh // 2
            
            # Offset for multiple players at same position
            offset_idx = self.active_players.index(idx)
            num_players = len(self.active_players)
            if num_players > 1:
                angle = (offset_idx / num_players) * 6.28
                offset = 15
                cx += int(offset * (0.5 - abs(0.5 - offset_idx / num_players)))
            
            # Draw token using immediate rendering to ensure it's on top of board text
            color = PLAYER_COLORS[idx]
            self.renderer.draw_circle_immediate(color, (cx, cy), 12)
            self.renderer.draw_circle_immediate((0, 0, 0), (cx, cy), 12, width=2)
    
    def _draw_dice(self):
        """Draw dice with animation during roll"""
        bx, by, bw, bh = self.board_rect
        cx, cy = bx + bw // 2, by + bh // 2
        
        dice_size = 60
        gap = 15
        
        # Show dice values (animated if rolling)
        if self.dice_rolling:
            # Show random values during roll animation
            import random
            display_values = (random.randint(1, 6), random.randint(1, 6))
        else:
            display_values = self.dice_values
        
        for i, value in enumerate(display_values):
            dx = cx + (i - 0.5) * (dice_size + gap)
            dy = cy
            
            # Die background with shadow
            shadow_offset = 3
            self.renderer.draw_rect((100, 100, 100, 180), 
                (int(dx - dice_size/2 + shadow_offset), int(dy - dice_size/2 + shadow_offset), dice_size, dice_size))
            
            # Die face
            self.renderer.draw_rect((255, 255, 255), 
                (int(dx - dice_size/2), int(dy - dice_size/2), dice_size, dice_size))
            self.renderer.draw_rect((0, 0, 0), 
                (int(dx - dice_size/2), int(dy - dice_size/2), dice_size, dice_size), width=3)
            
            # Pips
            self._draw_pips(int(dx), int(dy), dice_size, value)
    
    def _draw_hover_indicators(self):
        """Draw circular progress indicators for button hovers"""
        current_time = time.time()
        draw_hover_indicators(self.renderer, self.buttons, self.active_players, current_time)
    
    def _draw_popup(self):
        """Draw floating popup box (text only, buttons are in panel) - dimming done in main draw"""
        # Note: Screen dimming is now handled in main draw() method
        pass  # This method is deprecated but kept for compatibility
    
    def _draw_pips(self, cx: int, cy: int, size: int, value: int):
        """Draw dice pips"""
        r = size // 10
        off = size // 4
        
        pips = {
            1: [(0, 0)],
            2: [(-off, -off), (off, off)],
            3: [(-off, -off), (0, 0), (off, off)],
            4: [(-off, -off), (off, -off), (-off, off), (off, off)],
            5: [(-off, -off), (off, -off), (0, 0), (-off, off), (off, off)],
            6: [(-off, -off), (off, -off), (-off, 0), (off, 0), (-off, off), (off, off)]
        }
        
        for dx, dy in pips.get(value, []):
            self.renderer.draw_circle((0, 0, 0), (cx + dx, cy + dy), r)
    
    def _draw_winner_screen(self):
        """Draw winner celebration screen"""
        # Background
        self.renderer.draw_rect((20, 20, 30), (0, 0, self.width, self.height))
        
        # Winner banner
        banner_w = 800
        banner_h = 400
        banner_x = (self.width - banner_w) // 2
        banner_y = (self.height - banner_h) // 2
        
        winner_color = PLAYER_COLORS[self.winner_idx]
        
        # Banner background with winner's color
        self.renderer.draw_rect(winner_color, (banner_x, banner_y, banner_w, banner_h))
        self.renderer.draw_rect((255, 255, 255), (banner_x, banner_y, banner_w, banner_h), width=8)
        
        # Winner text
        cx = self.width // 2
        cy = self.height // 2
        
        self.renderer.draw_text(
            f"PLAYER {self.winner_idx + 1} WINS!",
            cx, cy - 50,
            'Arial', 60, (255, 255, 255),
            anchor_x='center', anchor_y='center',
            bold=True
        )
        
        self.renderer.draw_text(
            "MONOPOLY CHAMPION",
            cx, cy + 50,
            'Arial', 40, (255, 255, 200),
            anchor_x='center', anchor_y='center',
            bold=True
        )
        
        # Player's final money
        winner = self.players[self.winner_idx]
        self.renderer.draw_text(
            f"Final Balance: ${winner.money}",
            cx, cy + 120,
            'Arial', 30, (255, 255, 255),
            anchor_x='center', anchor_y='center'
        )
        
        # Back to Main Menu button
        btn_w = 300
        btn_h = 60
        btn_x = (self.width - btn_w) // 2
        btn_y = banner_y - 100
        
        self.renderer.draw_rect((80, 80, 80), (btn_x, btn_y, btn_w, btn_h))
        self.renderer.draw_rect((200, 200, 200), (btn_x, btn_y, btn_w, btn_h), width=3)
        
        self.renderer.draw_text(
            "Back to Main Menu",
            cx, btn_y + btn_h // 2,
            'Arial', 24, (255, 255, 255),
            anchor_x='center', anchor_y='center',
            bold=True
        )
    
    def _draw_player_select(self):
        """Draw player selection screen"""
        # Background
        self.renderer.draw_rect((25, 35, 25), (0, 0, self.width, self.height))
        
        # Title at top
        self.renderer.draw_text(
            "Select Players - Monopoly",
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
