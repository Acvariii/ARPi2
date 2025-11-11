"""Complete American Monopoly game implementation with player-oriented UI."""
import time
import math
import random
import pygame
from typing import List, Dict, Tuple, Optional, Callable
from config import PLAYER_COLORS, HOVER_TIME_THRESHOLD, Colors
from monopoly_data import (
    BOARD_SPACES, PROPERTY_GROUPS, STARTING_MONEY, PASSING_GO_MONEY,
    LUXURY_TAX, INCOME_TAX, JAIL_POSITION, GO_TO_JAIL_POSITION,
    JAIL_FINE, MAX_JAIL_TURNS, MAX_HOUSES_PER_PROPERTY
)
from constants import COMMUNITY_CHEST_CARDS, CHANCE_CARDS
from player_panel import PlayerPanel, calculate_all_panels
from ui_components import HoverButton, RotatedText, draw_circular_progress


class Property:
    """Represents a property with houses/hotels."""
    
    def __init__(self, data: Dict):
        self.data = data
        self.houses = 0  # 0-4 houses, 5 = hotel
        self.is_mortgaged = False
        self.owner: Optional[int] = None
    
    def get_rent(self, dice_roll: Optional[int] = None, owned_in_group: int = 1) -> int:
        """Calculate rent based on houses and ownership."""
        if self.is_mortgaged:
            return 0
        
        prop_type = self.data.get("type")
        
        if prop_type == "property":
            rent_array = self.data.get("rent", [0])
            return rent_array[self.houses] if self.houses < len(rent_array) else 0
        
        elif prop_type == "railroad":
            rent_array = self.data.get("rent", [25, 50, 100, 200])
            idx = min(owned_in_group - 1, len(rent_array) - 1)
            return rent_array[idx]
        
        elif prop_type == "utility":
            # Utilities: 4x dice if 1 owned, 10x dice if both owned
            multiplier = 4 if owned_in_group == 1 else 10
            return (dice_roll or 0) * multiplier
        
        return 0
    
    def can_build_house(self, has_monopoly: bool, all_props_in_group: List['Property']) -> bool:
        """Check if can build a house on this property."""
        if not has_monopoly or self.is_mortgaged:
            return False
        
        # Can't build hotels if already have one
        if self.houses >= 5:
            return False
        
        # Must build evenly across monopoly
        for prop in all_props_in_group:
            if prop.houses < self.houses:
                return False
        
        return True
    
    def can_sell_house(self) -> bool:
        """Check if can sell a house."""
        return self.houses > 0 and not self.is_mortgaged
    
    def mortgage(self) -> int:
        """Mortgage the property and return cash received."""
        if self.is_mortgaged or self.houses > 0:
            return 0
        self.is_mortgaged = True
        return self.data.get("mortgage_value", 0)
    
    def unmortgage(self, player_money: int) -> bool:
        """Unmortgage if player has enough money."""
        if not self.is_mortgaged:
            return False
        cost = int(self.data.get("mortgage_value", 0) * 1.1)  # 10% interest
        if player_money >= cost:
            self.is_mortgaged = False
            return True
        return False


class Player:
    """Represents a player in the game."""
    
    def __init__(self, idx: int, color: Tuple[int, int, int]):
        self.idx = idx
        self.color = color
        self.money = STARTING_MONEY
        self.position = 0
        self.properties: List[int] = []  # Indices of owned properties
        self.in_jail = False
        self.jail_turns = 0
        self.get_out_of_jail_cards = 0
        self.consecutive_doubles = 0
        self.is_bankrupt = False
        
        # Animation state
        self.move_path: List[int] = []
        self.move_start = 0.0
        self.move_from = 0
        self.is_moving = False
    
    def add_money(self, amount: int):
        """Add money to player."""
        self.money += amount
    
    def remove_money(self, amount: int) -> bool:
        """Remove money from player. Returns False if can't afford."""
        if self.money >= amount:
            self.money -= amount
            return True
        return False
    
    def owns_property_at(self, position: int) -> bool:
        """Check if player owns property at position."""
        return position in self.properties
    
    def get_properties_in_group(self, group: str, all_properties: List[Property]) -> List[int]:
        """Get all owned properties in a color group."""
        return [idx for idx in self.properties 
                if all_properties[idx].data.get("group") == group]
    
    def has_monopoly(self, group: str, all_properties: List[Property]) -> bool:
        """Check if player has monopoly on a color group."""
        owned = self.get_properties_in_group(group, all_properties)
        required = len(PROPERTY_GROUPS.get(group, []))
        return len(owned) == required
    
    def get_total_houses(self, all_properties: List[Property]) -> int:
        """Count total houses owned."""
        return sum(all_properties[idx].houses for idx in self.properties 
                if all_properties[idx].houses < 5)
    
    def get_total_hotels(self, all_properties: List[Property]) -> int:
        """Count total hotels owned."""
        return sum(1 for idx in self.properties if all_properties[idx].houses == 5)


class MonopolyGame:
    """Main Monopoly game with complete rules implementation."""
    
    def __init__(self, screen: pygame.Surface, fingertip_callback: Callable):
        self.screen = screen
        self.get_fingertips = fingertip_callback
        self.screen_size = screen.get_size()
        
        # Game state
        self.properties = [Property(data) if data else Property({"name": "", "type": "none"}) 
                        for data in BOARD_SPACES]
        self.players = [Player(i, PLAYER_COLORS[i]) for i in range(8)]
        self.active_players: List[int] = []  # Indices of players in game
        self.current_player_idx = 0
        
        # Card decks
        self.community_chest_deck = list(COMMUNITY_CHEST_CARDS)
        self.chance_deck = list(CHANCE_CARDS)
        random.shuffle(self.community_chest_deck)
        random.shuffle(self.chance_deck)
        
        # UI
        self.panels = calculate_all_panels(self.screen_size)
        self.buttons: Dict[int, Dict[str, HoverButton]] = {}
        
        # Game flow
        self.phase = "roll"  # "roll", "moving", "landed", "buying", "paying_rent", "card"
        self.can_roll = True
        self.dice_values = (0, 0)
        self.dice_rolling = False
        self.dice_roll_start = 0.0
        self.dice_roll_duration = 1.2
        
        # UI popups
        self.active_popup: Optional[str] = None  # "properties", "build", "buy_prompt", "card"
        self.popup_data: Dict = {}
        self.popup_buttons: List[HoverButton] = []
        self.property_scroll = 0  # For scrolling through properties
        
        # Board geometry
        self._calculate_board_geometry()
        
        # Initialize buttons after geometry is set
        self._init_buttons()
    
    def _calculate_board_geometry(self):
        """Calculate board layout ensuring it doesn't overlap player panels."""
        w, h = self.screen_size
        
        # Panel sizes
        horizontal_panel_height = int(h * 0.10)
        vertical_panel_width = int(w * 0.12)
        
        # Board must fit within the space between panels
        # Add some margin for safety
        margin = 20
        available_width = w - (2 * vertical_panel_width) - (2 * margin)
        available_height = h - (2 * horizontal_panel_height) - (2 * margin)
        
        # Make board square, using smaller dimension
        board_size = min(available_width, available_height)
        
        # Center the board in available space
        board_x = vertical_panel_width + margin + (available_width - board_size) // 2
        board_y = horizontal_panel_height + margin + (available_height - board_size) // 2
        
        self.board_rect = pygame.Rect(board_x, board_y, board_size, board_size)
        
        # Calculate space positions with NO GAPS
        self.space_positions = self._calculate_space_positions()
    
    def _calculate_space_positions(self) -> List[Tuple[int, int, int, int]]:
        """Calculate exact positions for all 40 spaces with no gaps."""
        positions = []
        board_x = self.board_rect.x
        board_y = self.board_rect.y
        board_size = self.board_rect.width
        
        # Each side has 11 spaces (including corners)
        space_size = board_size // 11
        
        # Bottom row: spaces 0-10 (GO to Just Visiting, right to left)
        for i in range(11):
            x = board_x + board_size - ((i + 1) * space_size)
            y = board_y + board_size - space_size
            positions.append((x, y, space_size, space_size))
        
        # Left column: spaces 11-19 (9 spaces, bottom to top)
        for i in range(1, 10):
            x = board_x
            y = board_y + board_size - ((i + 1) * space_size)
            positions.append((x, y, space_size, space_size))
        
        # Top row: spaces 20-30 (Free Parking to Go To Jail, left to right)
        for i in range(11):
            x = board_x + (i * space_size)
            y = board_y
            positions.append((x, y, space_size, space_size))
        
        # Right column: spaces 31-39 (9 spaces, top to bottom)
        for i in range(1, 10):
            x = board_x + board_size - space_size
            y = board_y + (i * space_size)
            positions.append((x, y, space_size, space_size))
        
        return positions
    
    def _init_buttons(self):
        """Initialize player panel buttons with proper sizing."""
        for panel in self.panels:
            player_idx = panel.player_idx
            font_size = 22 if panel.is_vertical() else 26
            button_font = pygame.font.SysFont(None, font_size)
            
            if panel.is_vertical():
                action_rect = panel.get_grid_rect(0.5, 3, 3, 1.8, 4, 12)
                props_rect = panel.get_grid_rect(0.5, 5.5, 3, 1.8, 4, 12)
                build_rect = panel.get_grid_rect(0.5, 8, 3, 1.8, 4, 12)
            else:
                action_rect = panel.get_grid_rect(1, 1.2, 3, 1.6, 12, 4)
                props_rect = panel.get_grid_rect(4.5, 1.2, 3, 1.6, 12, 4)
                build_rect = panel.get_grid_rect(8, 1.2, 3, 1.6, 12, 4)
            
            action_btn = HoverButton(action_rect, "Roll", button_font, orientation=panel.orientation)
            props_btn = HoverButton(props_rect, "Props", button_font, orientation=panel.orientation)
            build_btn = HoverButton(build_rect, "Build", button_font, orientation=panel.orientation)
            
            self.buttons[player_idx] = {
                "action": action_btn,
                "props": props_btn,
                "build": build_btn
            }
    
    def start_game(self, player_indices: List[int]):
        """Start game with selected players."""
        self.active_players = sorted(player_indices)
        self.current_player_idx = 0
        
        # Reset all players
        for i in self.active_players:
            self.players[i].money = STARTING_MONEY
            self.players[i].position = 0
            self.players[i].properties = []
            self.players[i].in_jail = False
            self.players[i].is_bankrupt = False
            self.players[i].get_out_of_jail_cards = 0
    
    def get_current_player(self) -> Player:
        """Get the current active player."""
        return self.players[self.active_players[self.current_player_idx]]
    
    def advance_turn(self):
        """Move to next player's turn."""
        player = self.get_current_player()
        player.consecutive_doubles = 0
        
        # Move to next non-bankrupt player
        original_idx = self.current_player_idx
        while True:
            self.current_player_idx = (self.current_player_idx + 1) % len(self.active_players)
            next_player = self.get_current_player()
            
            if not next_player.is_bankrupt or self.current_player_idx == original_idx:
                break
        
        self.phase = "roll"
        self.can_roll = True
        self.dice_values = (0, 0)
    
    def roll_dice(self):
        """Initiate dice roll."""
        if not self.can_roll or self.dice_rolling:
            return
        
        self.dice_rolling = True
        self.dice_roll_start = time.time()
        self.can_roll = False
    
    def move_player(self, player: Player, spaces: int):
        """Move player forward by spaces."""
        old_pos = player.position
        player.move_from = old_pos
        
        # Create path
        player.move_path = []
        for i in range(1, abs(spaces) + 1):
            if spaces > 0:
                player.move_path.append((old_pos + i) % 40)
            else:
                player.move_path.append((old_pos - i) % 40)
        
        player.is_moving = True
        player.move_start = time.time()
        self.phase = "moving"
    
    def land_on_space(self, player: Player):
        """Handle landing on a space."""
        position = player.position
        space = self.properties[position]
        space_type = space.data.get("type")
        
        # Check if passed GO
        if player.move_from > player.position and len(player.move_path) > 0:
            player.add_money(PASSING_GO_MONEY)
        
        # Handle different space types
        if space_type == "go":
            player.add_money(PASSING_GO_MONEY)
            self._finish_turn_or_allow_double()
            
        elif space_type in ("property", "railroad", "utility"):
            if space.owner is None:
                self.phase = "buying"
                self._show_buy_prompt(player, position)
            elif space.owner != player.idx:
                self.phase = "paying_rent"
                self._pay_rent(player, position)
            else:
                self._finish_turn_or_allow_double()
                
        elif space_type == "go_to_jail":
            self._send_to_jail(player)
            
        elif space_type == "income_tax":
            player.remove_money(INCOME_TAX)
            self._finish_turn_or_allow_double()
            
        elif space_type == "luxury_tax":
            player.remove_money(LUXURY_TAX)
            self._finish_turn_or_allow_double()
            
        elif space_type == "chance":
            self._draw_card(player, "chance")
            
        elif space_type == "community_chest":
            self._draw_card(player, "community_chest")
            
        else:
            self._finish_turn_or_allow_double()
        
        # Check if bankrupt
        if player.money < 0:
            self._handle_bankruptcy(player)
    
    def _draw_card(self, player: Player, deck_type: str):
        """Draw a card from deck."""
        if deck_type == "chance":
            if not self.chance_deck:
                self.chance_deck = list(CHANCE_CARDS)
                random.shuffle(self.chance_deck)
            card = self.chance_deck.pop(0)
        else:
            if not self.community_chest_deck:
                self.community_chest_deck = list(COMMUNITY_CHEST_CARDS)
                random.shuffle(self.community_chest_deck)
            card = self.community_chest_deck.pop(0)
        
        self.phase = "card"
        self._show_card_popup(player, card, deck_type)
    
    def _execute_card_action(self, player: Player, card: Dict):
        """Execute the action from a card."""
        action = card.get("action")
        if not action:
            return
        
        action_type = action[0]
        
        if action_type == "money":
            amount = action[1]
            if amount > 0:
                player.add_money(amount)
            else:
                player.remove_money(abs(amount))
        
        elif action_type == "jail_free":
            player.get_out_of_jail_cards += 1
        
        elif action_type == "go_to_jail":
            self._send_to_jail(player)
            return  # Don't finish turn
        
        elif action_type == "advance":
            target_pos = action[1]
            collect_go = action[2] if len(action) > 2 else False
            
            if collect_go and target_pos < player.position:
                player.add_money(PASSING_GO_MONEY)
            
            player.position = target_pos
            self.land_on_space(player)
            return  # Don't finish turn (land_on_space will handle it)
        
        elif action_type == "collect_from_each":
            amount = action[1]
            for idx in self.active_players:
                if idx != player.idx and not self.players[idx].is_bankrupt:
                    if self.players[idx].remove_money(amount):
                        player.add_money(amount)
        
        elif action_type == "pay_each_player":
            amount = action[1]
            for idx in self.active_players:
                if idx != player.idx and not self.players[idx].is_bankrupt:
                    if player.remove_money(amount):
                        self.players[idx].add_money(amount)
        
        elif action_type == "pay_per_house_hotel":
            house_cost, hotel_cost = action[1]
            houses = player.get_total_houses(self.properties)
            hotels = player.get_total_hotels(self.properties)
            total = houses * house_cost + hotels * hotel_cost
            player.remove_money(total)
        
        self._finish_turn_or_allow_double()
    
    def _finish_turn_or_allow_double(self):
        """Either end turn or allow rolling again if doubles."""
        player = self.get_current_player()
        if player.consecutive_doubles > 0:
            self.phase = "roll"
            self.can_roll = True
        else:
            self.phase = "roll"
    
    def _show_buy_prompt(self, player: Player, position: int):
        """Show popup to buy property in player's panel."""
        space = self.properties[position]
        price = space.data.get("price", 0)
        
        self.active_popup = "buy_prompt"
        self.popup_data = {
            "player": player,
            "position": position,
            "price": price
        }
        
        panel = self.panels[player.idx]
        
        # Place buttons consistently to the right from player's perspective
        if panel.is_vertical():
            # For vertical panels, buttons go in the bottom right area
            yes_rect = panel.get_grid_rect(2, 9, 1.8, 1.2, 4, 12)
            no_rect = panel.get_grid_rect(2, 10.5, 1.8, 1.2, 4, 12)
        else:
            # For horizontal panels, buttons go on the right side
            yes_rect = panel.get_grid_rect(9, 1.5, 2.5, 1, 12, 4)
            no_rect = panel.get_grid_rect(9, 2.7, 2.5, 1, 12, 4)
        
        font = pygame.font.SysFont(None, 26)
        self.popup_buttons = [
            HoverButton(yes_rect, "Buy", font, orientation=panel.orientation),
            HoverButton(no_rect, "Pass", font, orientation=panel.orientation)
        ]
    
    def _show_card_popup(self, player: Player, card: Dict, deck_type: str):
        """Show card text popup."""
        self.active_popup = "card"
        self.popup_data = {
            "player": player,
            "card": card,
            "deck_type": deck_type
        }
        
        panel = self.panels[player.idx]
        
        # Consistent button placement
        if panel.is_vertical():
            ok_rect = panel.get_grid_rect(1, 10.5, 2, 1.2, 4, 12)
        else:
            ok_rect = panel.get_grid_rect(9.5, 2.5, 2, 1, 12, 4)
        
        font = pygame.font.SysFont(None, 26)
        self.popup_buttons = [
            HoverButton(ok_rect, "OK", font, orientation=panel.orientation)
        ]
    
    def _show_properties_popup(self, player: Player):
        """Show player's properties popup."""
        self.active_popup = "properties"
        self.popup_data = {"player": player}
        self.property_scroll = 0
        
        panel = self.panels[player.idx]
        
        # Consistent button placement - all to the right
        if panel.is_vertical():
            prev_rect = panel.get_grid_rect(2, 8.5, 1.8, 1, 4, 12)
            next_rect = panel.get_grid_rect(2, 9.7, 1.8, 1, 4, 12)
            close_rect = panel.get_grid_rect(2, 10.9, 1.8, 1, 4, 12)
        else:
            prev_rect = panel.get_grid_rect(9, 0.5, 2.5, 1, 12, 4)
            next_rect = panel.get_grid_rect(9, 1.7, 2.5, 1, 12, 4)
            close_rect = panel.get_grid_rect(9, 2.9, 2.5, 1, 12, 4)
        
        font = pygame.font.SysFont(None, 24)
        self.popup_buttons = [
            HoverButton(prev_rect, "◀ Prev", font, orientation=panel.orientation),
            HoverButton(next_rect, "Next ▶", font, orientation=panel.orientation),
            HoverButton(close_rect, "✕ Close", font, orientation=panel.orientation)
        ]
    
    def _show_build_popup(self, player: Player):
        """Show building options popup."""
        self.active_popup = "build"
        self.popup_data = {"player": player, "selected_group": None}
        self.property_scroll = 0
        
        panel = self.panels[player.idx]
        
        # Consistent button placement
        if panel.is_vertical():
            close_rect = panel.get_grid_rect(2, 10.9, 1.8, 1, 4, 12)
        else:
            close_rect = panel.get_grid_rect(9, 2.9, 2.5, 1, 12, 4)
        
        font = pygame.font.SysFont(None, 24)
        self.popup_buttons = [
            HoverButton(close_rect, "✕ Close", font, orientation=panel.orientation)
        ]
    
    def start_game(self, player_indices: List[int]):
        """Start game with selected players."""
        self.active_players = sorted(player_indices)
        self.current_player_idx = 0
        
        # Reset all players
        for i in self.active_players:
            self.players[i].money = STARTING_MONEY
            self.players[i].position = 0
            self.players[i].properties = []
            self.players[i].in_jail = False
            self.players[i].is_bankrupt = False
            self.players[i].get_out_of_jail_cards = 0
    
    def get_current_player(self) -> Player:
        """Get the current active player."""
        return self.players[self.active_players[self.current_player_idx]]
    
    def advance_turn(self):
        """Move to next player's turn."""
        player = self.get_current_player()
        player.consecutive_doubles = 0
        
        # Move to next non-bankrupt player
        original_idx = self.current_player_idx
        while True:
            self.current_player_idx = (self.current_player_idx + 1) % len(self.active_players)
            next_player = self.get_current_player()
            
            if not next_player.is_bankrupt or self.current_player_idx == original_idx:
                break
        
        self.phase = "roll"
        self.can_roll = True
        self.dice_values = (0, 0)
    
    def roll_dice(self):
        """Initiate dice roll."""
        if not self.can_roll or self.dice_rolling:
            return
        
        self.dice_rolling = True
        self.dice_roll_start = time.time()
        self.can_roll = False
    
    def move_player(self, player: Player, spaces: int):
        """Move player forward by spaces."""
        old_pos = player.position
        player.move_from = old_pos
        
        # Create path
        player.move_path = []
        for i in range(1, abs(spaces) + 1):
            if spaces > 0:
                player.move_path.append((old_pos + i) % 40)
            else:
                player.move_path.append((old_pos - i) % 40)
        
        player.is_moving = True
        player.move_start = time.time()
        self.phase = "moving"
    
    def land_on_space(self, player: Player):
        """Handle landing on a space."""
        position = player.position
        space = self.properties[position]
        space_type = space.data.get("type")
        
        # Check if passed GO
        if player.move_from > player.position and len(player.move_path) > 0:
            player.add_money(PASSING_GO_MONEY)
        
        # Handle different space types
        if space_type == "go":
            player.add_money(PASSING_GO_MONEY)
            self._finish_turn_or_allow_double()
            
        elif space_type in ("property", "railroad", "utility"):
            if space.owner is None:
                self.phase = "buying"
                self._show_buy_prompt(player, position)
            elif space.owner != player.idx:
                self.phase = "paying_rent"
                self._pay_rent(player, position)
            else:
                self._finish_turn_or_allow_double()
                
        elif space_type == "go_to_jail":
            self._send_to_jail(player)
            
        elif space_type == "income_tax":
            player.remove_money(INCOME_TAX)
            self._finish_turn_or_allow_double()
            
        elif space_type == "luxury_tax":
            player.remove_money(LUXURY_TAX)
            self._finish_turn_or_allow_double()
            
        elif space_type == "chance":
            self._draw_card(player, "chance")
            
        elif space_type == "community_chest":
            self._draw_card(player, "community_chest")
            
        else:
            self._finish_turn_or_allow_double()
        
        # Check if bankrupt
        if player.money < 0:
            self._handle_bankruptcy(player)
    
    def _draw_card(self, player: Player, deck_type: str):
        """Draw a card from deck."""
        if deck_type == "chance":
            if not self.chance_deck:
                self.chance_deck = list(CHANCE_CARDS)
                random.shuffle(self.chance_deck)
            card = self.chance_deck.pop(0)
        else:
            if not self.community_chest_deck:
                self.community_chest_deck = list(COMMUNITY_CHEST_CARDS)
                random.shuffle(self.community_chest_deck)
            card = self.community_chest_deck.pop(0)
        
        self.phase = "card"
        self._show_card_popup(player, card, deck_type)
    
    def _execute_card_action(self, player: Player, card: Dict):
        """Execute the action from a card."""
        action = card.get("action")
        if not action:
            return
        
        action_type = action[0]
        
        if action_type == "money":
            amount = action[1]
            if amount > 0:
                player.add_money(amount)
            else:
                player.remove_money(abs(amount))
        
        elif action_type == "jail_free":
            player.get_out_of_jail_cards += 1
        
        elif action_type == "go_to_jail":
            self._send_to_jail(player)
            return  # Don't finish turn
        
        elif action_type == "advance":
            target_pos = action[1]
            collect_go = action[2] if len(action) > 2 else False
            
            if collect_go and target_pos < player.position:
                player.add_money(PASSING_GO_MONEY)
            
            player.position = target_pos
            self.land_on_space(player)
            return  # Don't finish turn (land_on_space will handle it)
        
        elif action_type == "collect_from_each":
            amount = action[1]
            for idx in self.active_players:
                if idx != player.idx and not self.players[idx].is_bankrupt:
                    if self.players[idx].remove_money(amount):
                        player.add_money(amount)
        
        elif action_type == "pay_each_player":
            amount = action[1]
            for idx in self.active_players:
                if idx != player.idx and not self.players[idx].is_bankrupt:
                    if player.remove_money(amount):
                        self.players[idx].add_money(amount)
        
        elif action_type == "pay_per_house_hotel":
            house_cost, hotel_cost = action[1]
            houses = player.get_total_houses(self.properties)
            hotels = player.get_total_hotels(self.properties)
            total = houses * house_cost + hotels * hotel_cost
            player.remove_money(total)
        
        self._finish_turn_or_allow_double()
    
    def _finish_turn_or_allow_double(self):
        """Either end turn or allow rolling again if doubles."""
        player = self.get_current_player()
        if player.consecutive_doubles > 0:
            self.phase = "roll"
            self.can_roll = True
        else:
            self.phase = "roll"
    
    def _show_buy_prompt(self, player: Player, position: int):
        """Show popup to buy property in player's panel."""
        space = self.properties[position]
        price = space.data.get("price", 0)
        
        self.active_popup = "buy_prompt"
        self.popup_data = {
            "player": player,
            "position": position,
            "price": price
        }
        
        panel = self.panels[player.idx]
        
        # Place buttons consistently to the right from player's perspective
        if panel.is_vertical():
            # For vertical panels, buttons go in the bottom right area
            yes_rect = panel.get_grid_rect(2, 9, 1.8, 1.2, 4, 12)
            no_rect = panel.get_grid_rect(2, 10.5, 1.8, 1.2, 4, 12)
        else:
            # For horizontal panels, buttons go on the right side
            yes_rect = panel.get_grid_rect(9, 1.5, 2.5, 1, 12, 4)
            no_rect = panel.get_grid_rect(9, 2.7, 2.5, 1, 12, 4)
        
        font = pygame.font.SysFont(None, 26)
        self.popup_buttons = [
            HoverButton(yes_rect, "Buy", font, orientation=panel.orientation),
            HoverButton(no_rect, "Pass", font, orientation=panel.orientation)
        ]
    
    def _show_card_popup(self, player: Player, card: Dict, deck_type: str):
        """Show card text popup."""
        self.active_popup = "card"
        self.popup_data = {
            "player": player,
            "card": card,
            "deck_type": deck_type
        }
        
        panel = self.panels[player.idx]
        
        # Consistent button placement
        if panel.is_vertical():
            ok_rect = panel.get_grid_rect(1, 10.5, 2, 1.2, 4, 12)
        else:
            ok_rect = panel.get_grid_rect(9.5, 2.5, 2, 1, 12, 4)
        
        font = pygame.font.SysFont(None, 26)
        self.popup_buttons = [
            HoverButton(ok_rect, "OK", font, orientation=panel.orientation)
        ]
    
    def _show_properties_popup(self, player: Player):
        """Show player's properties popup."""
        self.active_popup = "properties"
        self.popup_data = {"player": player}
        self.property_scroll = 0
        
        panel = self.panels[player.idx]
        
        # Consistent button placement - all to the right
        if panel.is_vertical():
            prev_rect = panel.get_grid_rect(2, 8.5, 1.8, 1, 4, 12)
            next_rect = panel.get_grid_rect(2, 9.7, 1.8, 1, 4, 12)
            close_rect = panel.get_grid_rect(2, 10.9, 1.8, 1, 4, 12)
        else:
            prev_rect = panel.get_grid_rect(9, 0.5, 2.5, 1, 12, 4)
            next_rect = panel.get_grid_rect(9, 1.7, 2.5, 1, 12, 4)
            close_rect = panel.get_grid_rect(9, 2.9, 2.5, 1, 12, 4)
        
        font = pygame.font.SysFont(None, 24)
        self.popup_buttons = [
            HoverButton(prev_rect, "◀ Prev", font, orientation=panel.orientation),
            HoverButton(next_rect, "Next ▶", font, orientation=panel.orientation),
            HoverButton(close_rect, "✕ Close", font, orientation=panel.orientation)
        ]
    
    def _show_build_popup(self, player: Player):
        """Show building options popup."""
        self.active_popup = "build"
        self.popup_data = {"player": player, "selected_group": None}
        self.property_scroll = 0
        
        panel = self.panels[player.idx]
        
        # Consistent button placement
        if panel.is_vertical():
            close_rect = panel.get_grid_rect(2, 10.9, 1.8, 1, 4, 12)
        else:
            close_rect = panel.get_grid_rect(9, 2.9, 2.5, 1, 12, 4)
        
        font = pygame.font.SysFont(None, 24)
        self.popup_buttons = [
            HoverButton(close_rect, "✕ Close", font, orientation=panel.orientation)
        ]
    
    def start_game(self, player_indices: List[int]):
        """Start game with selected players."""
        self.active_players = sorted(player_indices)
        self.current_player_idx = 0
        
        # Reset all players
        for i in self.active_players:
            self.players[i].money = STARTING_MONEY
            self.players[i].position = 0
            self.players[i].properties = []
            self.players[i].in_jail = False
            self.players[i].is_bankrupt = False
            self.players[i].get_out_of_jail_cards = 0
    
    def get_current_player(self) -> Player:
        """Get the current active player."""
        return self.players[self.active_players[self.current_player_idx]]
    
    def advance_turn(self):
        """Move to next player's turn."""
        player = self.get_current_player()
        player.consecutive_doubles = 0
        
        # Move to next non-bankrupt player
        original_idx = self.current_player_idx
        while True:
            self.current_player_idx = (self.current_player_idx + 1) % len(self.active_players)
            next_player = self.get_current_player()
            
            if not next_player.is_bankrupt or self.current_player_idx == original_idx:
                break
        
        self.phase = "roll"
        self.can_roll = True
        self.dice_values = (0, 0)
    
    def roll_dice(self):
        """Initiate dice roll."""
        if not self.can_roll or self.dice_rolling:
            return
        
        self.dice_rolling = True
        self.dice_roll_start = time.time()
        self.can_roll = False
    
    def move_player(self, player: Player, spaces: int):
        """Move player forward by spaces."""
        old_pos = player.position
        player.move_from = old_pos
        
        # Create path
        player.move_path = []
        for i in range(1, abs(spaces) + 1):
            if spaces > 0:
                player.move_path.append((old_pos + i) % 40)
            else:
                player.move_path.append((old_pos - i) % 40)
        
        player.is_moving = True
        player.move_start = time.time()
        self.phase = "moving"
    
    def land_on_space(self, player: Player):
        """Handle landing on a space."""
        position = player.position
        space = self.properties[position]
        space_type = space.data.get("type")
        
        # Check if passed GO
        if player.move_from > player.position and len(player.move_path) > 0:
            player.add_money(PASSING_GO_MONEY)
        
        # Handle different space types
        if space_type == "go":
            player.add_money(PASSING_GO_MONEY)
            self._finish_turn_or_allow_double()
            
        elif space_type in ("property", "railroad", "utility"):
            if space.owner is None:
                self.phase = "buying"
                self._show_buy_prompt(player, position)
            elif space.owner != player.idx:
                self.phase = "paying_rent"
                self._pay_rent(player, position)
            else:
                self._finish_turn_or_allow_double()
                
        elif space_type == "go_to_jail":
            self._send_to_jail(player)
            
        elif space_type == "income_tax":
            player.remove_money(INCOME_TAX)
            self._finish_turn_or_allow_double()
            
        elif space_type == "luxury_tax":
            player.remove_money(LUXURY_TAX)
            self._finish_turn_or_allow_double()
            
        elif space_type == "chance":
            self._draw_card(player, "chance")
            
        elif space_type == "community_chest":
            self._draw_card(player, "community_chest")
            
        else:
            self._finish_turn_or_allow_double()
        
        # Check if bankrupt
        if player.money < 0:
            self._handle_bankruptcy(player)
    
    def _draw_card(self, player: Player, deck_type: str):
        """Draw a card from deck."""
        if deck_type == "chance":
            if not self.chance_deck:
                self.chance_deck = list(CHANCE_CARDS)
                random.shuffle(self.chance_deck)
            card = self.chance_deck.pop(0)
        else:
            if not self.community_chest_deck:
                self.community_chest_deck = list(COMMUNITY_CHEST_CARDS)
                random.shuffle(self.community_chest_deck)
            card = self.community_chest_deck.pop(0)
        
        self.phase = "card"
        self._show_card_popup(player, card, deck_type)
    
    def _execute_card_action(self, player: Player, card: Dict):
        """Execute the action from a card."""
        action = card.get("action")
        if not action:
            return
        
        action_type = action[0]
        
        if action_type == "money":
            amount = action[1]
            if amount > 0:
                player.add_money(amount)
            else:
                player.remove_money(abs(amount))
        
        elif action_type == "jail_free":
            player.get_out_of_jail_cards += 1
        
        elif action_type == "go_to_jail":
            self._send_to_jail(player)
            return  # Don't finish turn
        
        elif action_type == "advance":
            target_pos = action[1]
            collect_go = action[2] if len(action) > 2 else False
            
            if collect_go and target_pos < player.position:
                player.add_money(PASSING_GO_MONEY)
            
            player.position = target_pos
            self.land_on_space(player)
            return  # Don't finish turn (land_on_space will handle it)
        
        elif action_type == "collect_from_each":
            amount = action[1]
            for idx in self.active_players:
                if idx != player.idx and not self.players[idx].is_bankrupt:
                    if self.players[idx].remove_money(amount):
                        player.add_money(amount)
        
        elif action_type == "pay_each_player":
            amount = action[1]
            for idx in self.active_players:
                if idx != player.idx and not self.players[idx].is_bankrupt:
                    if player.remove_money(amount):
                        self.players[idx].add_money(amount)
        
        elif action_type == "pay_per_house_hotel":
            house_cost, hotel_cost = action[1]
            houses = player.get_total_houses(self.properties)
            hotels = player.get_total_hotels(self.properties)
            total = houses * house_cost + hotels * hotel_cost
            player.remove_money(total)
        
        self._finish_turn_or_allow_double()
    
    def _finish_turn_or_allow_double(self):
        """Either end turn or allow rolling again if doubles."""
        player = self.get_current_player()
        if player.consecutive_doubles > 0:
            self.phase = "roll"
            self.can_roll = True
        else:
            self.phase = "roll"
    
    def _show_buy_prompt(self, player: Player, position: int):
        """Show popup to buy property in player's panel."""
        space = self.properties[position]
        price = space.data.get("price", 0)
        
        self.active_popup = "buy_prompt"
        self.popup_data = {
            "player": player,
            "position": position,
            "price": price
        }
        
        panel = self.panels[player.idx]
        
        # Place buttons consistently to the right from player's perspective
        if panel.is_vertical():
            # For vertical panels, buttons go in the bottom right area
            yes_rect = panel.get_grid_rect(2, 9, 1.8, 1.2, 4, 12)
            no_rect = panel.get_grid_rect(2, 10.5, 1.8, 1.2, 4, 12)
        else:
            # For horizontal panels, buttons go on the right side
            yes_rect = panel.get_grid_rect(9, 1.5, 2.5, 1, 12, 4)
            no_rect = panel.get_grid_rect(9, 2.7, 2.5, 1, 12, 4)
        
        font = pygame.font.SysFont(None, 26)
        self.popup_buttons = [
            HoverButton(yes_rect, "Buy", font, orientation=panel.orientation),
            HoverButton(no_rect, "Pass", font, orientation=panel.orientation)
        ]
    
    def _show_card_popup(self, player: Player, card: Dict, deck_type: str):
        """Show card text popup."""
        self.active_popup = "card"
        self.popup_data = {
            "player": player,
            "card": card,
            "deck_type": deck_type
        }
        
        panel = self.panels[player.idx]
        
        # Consistent button placement
        if panel.is_vertical():
            ok_rect = panel.get_grid_rect(1, 10.5, 2, 1.2, 4, 12)
        else:
            ok_rect = panel.get_grid_rect(9.5, 2.5, 2, 1, 12, 4)
        
        font = pygame.font.SysFont(None, 26)
        self.popup_buttons = [
            HoverButton(ok_rect, "OK", font, orientation=panel.orientation)
        ]
    
    def _show_properties_popup(self, player: Player):
        """Show player's properties popup."""
        self.active_popup = "properties"
        self.popup_data = {"player": player}
        self.property_scroll = 0
        
        panel = self.panels[player.idx]
        
        # Consistent button placement - all to the right
        if panel.is_vertical():
            prev_rect = panel.get_grid_rect(2, 8.5, 1.8, 1, 4, 12)
            next_rect = panel.get_grid_rect(2, 9.7, 1.8, 1, 4, 12)
            close_rect = panel.get_grid_rect(2, 10.9, 1.8, 1, 4, 12)
        else:
            prev_rect = panel.get_grid_rect(9, 0.5, 2.5, 1, 12, 4)
            next_rect = panel.get_grid_rect(9, 1.7, 2.5, 1, 12, 4)
            close_rect = panel.get_grid_rect(9, 2.9, 2.5, 1, 12, 4)
        
        font = pygame.font.SysFont(None, 24)
        self.popup_buttons = [
            HoverButton(prev_rect, "◀ Prev", font, orientation=panel.orientation),
            HoverButton(next_rect, "Next ▶", font, orientation=panel.orientation),
            HoverButton(close_rect, "✕ Close", font, orientation=panel.orientation)
        ]
    
    def _show_build_popup(self, player: Player):
        """Show building options popup."""
        self.active_popup = "build"
        self.popup_data = {"player": player, "selected_group": None}
        self.property_scroll = 0
        
        panel = self.panels[player.idx]
        
        # Consistent button placement
        if panel.is_vertical():
            close_rect = panel.get_grid_rect(2, 10.9, 1.8, 1, 4, 12)
        else:
            close_rect = panel.get_grid_rect(9, 2.9, 2.5, 1, 12, 4)
        
        font = pygame.font.SysFont(None, 24)
        self.popup_buttons = [
            HoverButton(close_rect, "✕ Close", font, orientation=panel.orientation)
        ]
    
    def start_game(self, player_indices: List[int]):
        """Start game with selected players."""
        self.active_players = sorted(player_indices)
        self.current_player_idx = 0
        
        # Reset all players
        for i in self.active_players:
            self.players[i].money = STARTING_MONEY
            self.players[i].position = 0
            self.players[i].properties = []
            self.players[i].in_jail = False
            self.players[i].is_bankrupt = False
            self.players[i].get_out_of_jail_cards = 0
    
    def get_current_player(self) -> Player:
        """Get the current active player."""
        return self.players[self.active_players[self.current_player_idx]]
    
    def advance_turn(self):
        """Move to next player's turn."""
        player = self.get_current_player()
        player.consecutive_doubles = 0
        
        # Move to next non-bankrupt player
        original_idx = self.current_player_idx
        while True:
            self.current_player_idx = (self.current_player_idx + 1) % len(self.active_players)
            next_player = self.get_current_player()
            
            if not next_player.is_bankrupt or self.current_player_idx == original_idx:
                break
        
        self.phase = "roll"
        self.can_roll = True
        self.dice_values = (0, 0)
    
    def roll_dice(self):
        """Initiate dice roll."""
        if not self.can_roll or self.dice_rolling:
            return
        
        self.dice_rolling = True
        self.dice_roll_start = time.time()
        self.can_roll = False
    
    def move_player(self, player: Player, spaces: int):
        """Move player forward by spaces."""
        old_pos = player.position
        player.move_from = old_pos
        
        # Create path
        player.move_path = []
        for i in range(1, abs(spaces) + 1):
            if spaces > 0:
                player.move_path.append((old_pos + i) % 40)
            else:
                player.move_path.append((old_pos - i) % 40)
        
        player.is_moving = True
        player.move_start = time.time()
        self.phase = "moving"
    
    def land_on_space(self, player: Player):
        """Handle landing on a space."""
        position = player.position
        space = self.properties[position]
        space_type = space.data.get("type")
        
        # Check if passed GO
        if player.move_from > player.position and len(player.move_path) > 0:
            player.add_money(PASSING_GO_MONEY)
        
        # Handle different space types
        if space_type == "go":
            player.add_money(PASSING_GO_MONEY)
            self._finish_turn_or_allow_double()
            
        elif space_type in ("property", "railroad", "utility"):
            if space.owner is None:
                self.phase = "buying"
                self._show_buy_prompt(player, position)
            elif space.owner != player.idx:
                self.phase = "paying_rent"
                self._pay_rent(player, position)
            else:
                self._finish_turn_or_allow_double()
                
        elif space_type == "go_to_jail":
            self._send_to_jail(player)
            
        elif space_type == "income_tax":
            player.remove_money(INCOME_TAX)
            self._finish_turn_or_allow_double()
            
        elif space_type == "luxury_tax":
            player.remove_money(LUXURY_TAX)
            self._finish_turn_or_allow_double()
            
        elif space_type == "chance":
            self._draw_card(player, "chance")
            
        elif space_type == "community_chest":
            self._draw_card(player, "community_chest")
            
        else:
            self._finish_turn_or_allow_double()
        
        # Check if bankrupt
        if player.money < 0:
            self._handle_bankruptcy(player)
    
    def _draw_card(self, player: Player, deck_type: str):
        """Draw a card from deck."""
        if deck_type == "chance":
            if not self.chance_deck:
                self.chance_deck = list(CHANCE_CARDS)
                random.shuffle(self.chance_deck)
            card = self.chance_deck.pop(0)
        else:
            if not self.community_chest_deck:
                self.community_chest_deck = list(COMMUNITY_CHEST_CARDS)
                random.shuffle(self.community_chest_deck)
            card = self.community_chest_deck.pop(0)
        
        self.phase = "card"
        self._show_card_popup(player, card, deck_type)
    
    def _execute_card_action(self, player: Player, card: Dict):
        """Execute the action from a card."""
        action = card.get("action")
        if not action:
            return
        
        action_type = action[0]
        
        if action_type == "money":
            amount = action[1]
            if amount > 0:
                player.add_money(amount)
            else:
                player.remove_money(abs(amount))
        
        elif action_type == "jail_free":
            player.get_out_of_jail_cards += 1
        
        elif action_type == "go_to_jail":
            self._send_to_jail(player)
            return  # Don't finish turn
        
        elif action_type == "advance":
            target_pos = action[1]
            collect_go = action[2] if len(action) > 2 else False
            
            if collect_go and target_pos < player.position:
                player.add_money(PASSING_GO_MONEY)
            
            player.position = target_pos
            self.land_on_space(player)
            return  # Don't finish turn (land_on_space will handle it)
        
        elif action_type == "collect_from_each":
            amount = action[1]
            for idx in self.active_players:
                if idx != player.idx and not self.players[idx].is_bankrupt:
                    if self.players[idx].remove_money(amount):
                        player.add_money(amount)
        
        elif action_type == "pay_each_player":
            amount = action[1]
            for idx in self.active_players:
                if idx != player.idx and not self.players[idx].is_bankrupt:
                    if player.remove_money(amount):
                        self.players[idx].add_money(amount)
        
        elif action_type == "pay_per_house_hotel":
            house_cost, hotel_cost = action[1]
            houses = player.get_total_houses(self.properties)
            hotels = player.get_total_hotels(self.properties)
            total = houses * house_cost + hotels * hotel_cost
            player.remove_money(total)
        
        self._finish_turn_or_allow_double()
    
    def _finish_turn_or_allow_double(self):
        """Either end turn or allow rolling again if doubles."""
        player = self.get_current_player()
        if player.consecutive_doubles > 0:
            self.phase = "roll"
            self.can_roll = True
        else:
            self.phase = "roll"
    
    def _show_buy_prompt(self, player: Player, position: int):
        """Show popup to buy property in player's panel."""
        space = self.properties[position]
        price = space.data.get("price", 0)
        
        self.active_popup = "buy_prompt"
        self.popup_data = {
            "player": player,
            "position": position,
            "price": price
        }
        
        panel = self.panels[player.idx]
        
        # Place buttons consistently to the right from player's perspective
        if panel.is_vertical():
            # For vertical panels, buttons go in the bottom right area
            yes_rect = panel.get_grid_rect(2, 9, 1.8, 1.2, 4, 12)
            no_rect = panel.get_grid_rect(2, 10.5, 1.8, 1.2, 4, 12)
        else:
            # For horizontal panels, buttons go on the right side
            yes_rect = panel.get_grid_rect(9, 1.5, 2.5, 1, 12, 4)
            no_rect = panel.get_grid_rect(9, 2.7, 2.5, 1, 12, 4)
        
        font = pygame.font.SysFont(None, 26)
        self.popup_buttons = [
            HoverButton(yes_rect, "Buy", font, orientation=panel.orientation),
            HoverButton(no_rect, "Pass", font, orientation=panel.orientation)
        ]
    
    def _show_card_popup(self, player: Player, card: Dict, deck_type: str):
        """Show card text popup."""
        self.active_popup = "card"
        self.popup_data = {
            "player": player,
            "card": card,
            "deck_type": deck_type
        }
        
        panel = self.panels[player.idx]
        
        # Consistent button placement
        if panel.is_vertical():
            ok_rect = panel.get_grid_rect(1, 10.5, 2, 1.2, 4, 12)
        else:
            ok_rect = panel.get_grid_rect(9.5, 2.5, 2, 1, 12, 4)
        
        font = pygame.font.SysFont(None, 26)
        self.popup_buttons = [
            HoverButton(ok_rect, "OK", font, orientation=panel.orientation)
        ]
    
    def _show_properties_popup(self, player: Player):
        """Show player's properties popup."""
        self.active_popup = "properties"
        self.popup_data = {"player": player}
        self.property_scroll = 0
        
        panel = self.panels[player.idx]
        
        # Consistent button placement - all to the right
        if panel.is_vertical():
            prev_rect = panel.get_grid_rect(2, 8.5, 1.8, 1, 4, 12)
            next_rect = panel.get_grid_rect(2, 9.7, 1.8, 1, 4, 12)
            close_rect = panel.get_grid_rect(2, 10.9, 1.8, 1, 4, 12)
        else:
            prev_rect = panel.get_grid_rect(9, 0.5, 2.5, 1, 12, 4)
            next_rect = panel.get_grid_rect(9, 1.7, 2.5, 1, 12, 4)
            close_rect = panel.get_grid_rect(9, 2.9, 2.5, 1, 12, 4)
        
        font = pygame.font.SysFont(None, 24)
        self.popup_buttons = [
            HoverButton(prev_rect, "◀ Prev", font, orientation=panel.orientation),
            HoverButton(next_rect, "Next ▶", font, orientation=panel.orientation),
            HoverButton(close_rect, "✕ Close", font, orientation=panel.orientation)
        ]
    
    def _show_build_popup(self, player: Player):
        """Show building options popup."""
        self.active_popup = "build"
        self.popup_data = {"player": player, "selected_group": None}
        self.property_scroll = 0
        
        panel = self.panels[player.idx]
        
        # Consistent button placement
        if panel.is_vertical():
            close_rect = panel.get_grid_rect(2, 10.9, 1.8, 1, 4, 12)
        else:
            close_rect = panel.get_grid_rect(9, 2.9, 2.5, 1, 12, 4)
        
        font = pygame.font.SysFont(None, 24)
        self.popup_buttons = [
            HoverButton(close_rect, "✕ Close", font, orientation=panel.orientation)
        ]
    
    def start_game(self, player_indices: List[int]):
        """Start game with selected players."""
        self.active_players = sorted(player_indices)
        self.current_player_idx = 0
        
        # Reset all players
        for i in self.active_players:
            self.players[i].money = STARTING_MONEY
            self.players[i].position = 0
            self.players[i].properties = []
            self.players[i].in_jail = False
            self.players[i].is_bankrupt = False
            self.players[i].get_out_of_jail_cards = 0
    
    def get_current_player(self) -> Player:
        """Get the current active player."""
        return self.players[self.active_players[self.current_player_idx]]
    
    def advance_turn(self):
        """Move to next player's turn."""
        player = self.get_current_player()
        player.consecutive_doubles = 0
        
        # Move to next non-bankrupt player
        original_idx = self.current_player_idx
        while True:
            self.current_player_idx = (self.current_player_idx + 1) % len(self.active_players)
            next_player = self.get_current_player()
            
            if not next_player.is_bankrupt or self.current_player_idx == original_idx:
                break
        
        self.phase = "roll"
        self.can_roll = True
        self.dice_values = (0, 0)
    
    def roll_dice(self):
        """Initiate dice roll."""
        if not self.can_roll or self.dice_rolling:
            return
        
        self.dice_rolling = True
        self.dice_roll_start = time.time()
        self.can_roll = False
    
    def move_player(self, player: Player, spaces: int):
        """Move player forward by spaces."""
        old_pos = player.position
        player.move_from = old_pos
        
        # Create path
        player.move_path = []
        for i in range(1, abs(spaces) + 1):
            if spaces > 0:
                player.move_path.append((old_pos + i) % 40)
            else:
                player.move_path.append((old_pos - i) % 40)
        
        player.is_moving = True
        player.move_start = time.time()
        self.phase = "moving"
    
    def land_on_space(self, player: Player):
        """Handle landing on a space."""
        position = player.position
        space = self.properties[position]
        space_type = space.data.get("type")
        
        # Check if passed GO
        if player.move_from > player.position and len(player.move_path) > 0:
            player.add_money(PASSING_GO_MONEY)
        
        # Handle different space types
        if space_type == "go":
            player.add_money(PASSING_GO_MONEY)
            self._finish_turn_or_allow_double()
            
        elif space_type in ("property", "railroad", "utility"):
            if space.owner is None:
                self.phase = "buying"
                self._show_buy_prompt(player, position)
            elif space.owner != player.idx:
                self.phase = "paying_rent"
                self._pay_rent(player, position)
            else:
                self._finish_turn_or_allow_double()
                
        elif space_type == "go_to_jail":
            self._send_to_jail(player)
            
        elif space_type == "income_tax":
            player.remove_money(INCOME_TAX)
            self._finish_turn_or_allow_double()
            
        elif space_type == "luxury_tax":
            player.remove_money(LUXURY_TAX)
            self._finish_turn_or_allow_double()
            
        elif space_type == "chance":
            self._draw_card(player, "chance")
            
        elif space_type == "community_chest":
            self._draw_card(player, "community_chest")
            
        else:
            self._finish_turn_or_allow_double()
        
        # Check if bankrupt
        if player.money < 0:
            self._handle_bankruptcy(player)
    
    def _draw_card(self, player: Player, deck_type: str):
        """Draw a card from deck."""
        if deck_type == "chance":
            if not self.chance_deck:
                self.chance_deck = list(CHANCE_CARDS)
                random.shuffle(self.chance_deck)
            card = self.chance_deck.pop(0)
        else:
            if not self.community_chest_deck:
                self.community_chest_deck = list(COMMUNITY_CHEST_CARDS)
                random.shuffle(self.community_chest_deck)
            card = self.community_chest_deck.pop(0)
        
        self.phase = "card"
        self._show_card_popup(player, card, deck_type)
    
    def _execute_card_action(self, player: Player, card: Dict):
        """Execute the action from a card."""
        action = card.get("action")
        if not action:
            return
        
        action_type = action[0]
        
        if action_type == "money":
            amount = action[1]
            if amount > 0:
                player.add_money(amount)
            else:
                player.remove_money(abs(amount))
        
        elif action_type == "jail_free":
            player.get_out_of_jail_cards += 1
        
        elif action_type == "go_to_jail":
            self._send_to_jail(player)
            return  # Don't finish turn
        
        elif action_type == "advance":
            target_pos = action[1]
            collect_go = action[2] if len(action) > 2 else False
            
            if collect_go and target_pos < player.position:
                player.add_money(PASSING_GO_MONEY)
            
            player.position = target_pos
            self.land_on_space(player)
            return  # Don't finish turn (land_on_space will handle it)
        
        elif action_type == "collect_from_each":
            amount = action[1]
            for idx in self.active_players:
                if idx != player.idx and not self.players[idx].is_bankrupt:
                    if self.players[idx].remove_money(amount):
                        player.add_money(amount)
        
        elif action_type == "pay_each_player":
            amount = action[1]
            for idx in self.active_players:
                if idx != player.idx and not self.players[idx].is_bankrupt:
                    if player.remove_money(amount):
                        self.players[idx].add_money(amount)
        
        elif action_type == "pay_per_house_hotel":
            house_cost, hotel_cost = action[1]
            houses = player.get_total_houses(self.properties)
            hotels = player.get_total_hotels(self.properties)
            total = houses * house_cost + hotels * hotel_cost
            player.remove_money(total)
        
        self._finish_turn_or_allow_double()
    
    def _finish_turn_or_allow_double(self):
        """Either end turn or allow rolling again if doubles."""
        player = self.get_current_player()
        if player.consecutive_doubles > 0:
            self.phase = "roll"
            self.can_roll = True
        else:
            self.phase = "roll"
    
    def _show_buy_prompt(self, player: Player, position: int):
        """Show popup to buy property in player's panel."""
        space = self.properties[position]
        price = space.data.get("price", 0)
        
        self.active_popup = "buy_prompt"
        self.popup_data = {
            "player": player,
            "position": position,
            "price": price
        }
        
        panel = self.panels[player.idx]
        
        # Place buttons consistently to the right from player's perspective
        if panel.is_vertical():
            # For vertical panels, buttons go in the bottom right area
            yes_rect = panel.get_grid_rect(2, 9, 1.8, 1.2, 4, 12)
            no_rect = panel.get_grid_rect(2, 10.5, 1.8, 1.2, 4, 12)
        else:
            # For horizontal panels, buttons go on the right side
            yes_rect = panel.get_grid_rect(9, 1.5, 2.5, 1, 12, 4)
            no_rect = panel.get_grid_rect(9, 2.7, 2.5, 1, 12, 4)
        
        font = pygame.font.SysFont(None, 26)
        self.popup_buttons = [
            HoverButton(yes_rect, "Buy", font, orientation=panel.orientation),
            HoverButton(no_rect, "Pass", font, orientation=panel.orientation)
        ]
    
    def _show_card_popup(self, player: Player, card: Dict, deck_type: str):
        """Show card text popup."""
        self.active_popup = "card"
        self.popup_data = {
            "player": player,
            "card": card,
            "deck_type": deck_type
        }
        
        panel = self.panels[player.idx]
        
        # Consistent button placement
        if panel.is_vertical():
            ok_rect = panel.get_grid_rect(1, 10.5, 2, 1.2, 4, 12)
        else:
            ok_rect = panel.get_grid_rect(9.5, 2.5, 2, 1, 12, 4)
        
        font = pygame.font.SysFont(None, 26)
        self.popup_buttons = [
            HoverButton(ok_rect, "OK", font, orientation=panel.orientation)
        ]
    
    def _show_properties_popup(self, player: Player):
        """Show player's properties popup."""
        self.active_popup = "properties"
        self.popup_data = {"player": player}
        self.property_scroll = 0
        
        panel = self.panels[player.idx]
        
        # Consistent button placement - all to the right
        if panel.is_vertical():
            prev_rect = panel.get_grid_rect(2, 8.5, 1.8, 1, 4, 12)
            next_rect = panel.get_grid_rect(2, 9.7, 1.8, 1, 4, 12)
            close_rect = panel.get_grid_rect(2, 10.9, 1.8, 1, 4, 12)
        else:
            prev_rect = panel.get_grid_rect(9, 0.5, 2.5, 1, 12, 4)
            next_rect = panel.get_grid_rect(9, 1.7, 2.5, 1, 12, 4)
            close_rect = panel.get_grid_rect(9, 2.9, 2.5, 1, 12, 4)
        
        font = pygame.font.SysFont(None, 24)
        self.popup_buttons = [
            HoverButton(prev_rect, "◀ Prev", font, orientation=panel.orientation),
            HoverButton(next_rect, "Next ▶", font, orientation=panel.orientation),
            HoverButton(close_rect, "✕ Close", font, orientation=panel.orientation)
        ]
    
    def _show_build_popup(self, player: Player):
        """Show building options popup."""
        self.active_popup = "build"
        self.popup_data = {"player": player, "selected_group": None}
        self.property_scroll = 0
        
        panel = self.panels[player.idx]
        
        # Consistent button placement
        if panel.is_vertical():
            close_rect = panel.get_grid_rect(2, 10.9, 1.8, 1, 4, 12)
        else:
            close_rect = panel.get_grid_rect(9, 2.9, 2.5, 1, 12, 4)
        
        font = pygame.font.SysFont(None, 24)
        self.popup_buttons = [
            HoverButton(close_rect, "✕ Close", font, orientation=panel.orientation)
        ]
    
    def start_game(self, player_indices: List[int]):
        """Start game with selected players."""
        self.active_players = sorted(player_indices)
        self.current_player_idx = 0
        
        # Reset all players
        for i in self.active_players:
            self.players[i].money = STARTING_MONEY
            self.players[i].position = 0
            self.players[i].properties = []
            self.players[i].in_jail = False
            self.players[i].is_bankrupt = False
            self.players[i].get_out_of_jail_cards = 0
    
    def get_current_player(self) -> Player:
        """Get the current active player."""
        return self.players[self.active_players[self.current_player_idx]]
    
    def advance_turn(self):
        """Move to next player's turn."""
        player = self.get_current_player()
        player.consecutive_doubles = 0
        
        # Move to next non-bankrupt player
        original_idx = self.current_player_idx
        while True:
            self.current_player_idx = (self.current_player_idx + 1) % len(self.active_players)
            next_player = self.get_current_player()
            
            if not next_player.is_bankrupt or self.current_player_idx == original_idx:
                break
        
        self.phase = "roll"
        self.can_roll = True
        self.dice_values = (0, 0)
    
    def roll_dice(self):
        """Initiate dice roll."""
        if not self.can_roll or self.dice_rolling:
            return
        
        self.dice_rolling = True
        self.dice_roll_start = time.time()
        self.can_roll = False
    
    def move_player(self, player: Player, spaces: int):
        """Move player forward by spaces."""
        old_pos = player.position
        player.move_from = old_pos
        
        # Create path
        player.move_path = []
        for i in range(1, abs(spaces) + 1):
            if spaces > 0:
                player.move_path.append((old_pos + i) % 40)
            else:
                player.move_path.append((old_pos - i) % 40)
        
        player.is_moving = True
        player.move_start = time.time()
        self.phase = "moving"
    
    def land_on_space(self, player: Player):
        """Handle landing on a space."""
        position = player.position
        space = self.properties[position]
        space_type = space.data.get("type")
        
        # Check if passed GO
        if player.move_from > player.position and len(player.move_path) > 0:
            player.add_money(PASSING_GO_MONEY)
        
        # Handle different space types
        if space_type == "go":
            player.add_money(PASSING_GO_MONEY)
            self._finish_turn_or_allow_double()
            
        elif space_type in ("property", "railroad", "utility"):
            if space.owner is None:
                self.phase = "buying"
                self._show_buy_prompt(player, position)
            elif space.owner != player.idx:
                self.phase = "paying_rent"
                self._pay_rent(player, position)
            else:
                self._finish_turn_or_allow_double()
                
        elif space_type == "go_to_jail":
            self._send_to_jail(player)
            
        elif space_type == "income_tax":
            player.remove_money(INCOME_TAX)
            self._finish_turn_or_allow_double()
            
        elif space_type == "luxury_tax":
            player.remove_money(LUXURY_TAX)
            self._finish_turn_or_allow_double()
            
        elif space_type == "chance":
            self._draw_card(player, "chance")
            
        elif space_type == "community_chest":
            self._draw_card(player, "community_chest")
            
        else:
            self._finish_turn_or_allow_double()
        
        # Check if bankrupt
        if player.money < 0:
            self._handle_bankruptcy(player)
    
    def _draw_card(self, player: Player, deck_type: str):
        """Draw a card from deck."""
        if deck_type == "chance":
            if not self.chance_deck:
                self.chance_deck = list(CHANCE_CARDS)
                random.shuffle(self.chance_deck)
            card = self.chance_deck.pop(0)
        else:
            if not self.community_chest_deck:
                self.community_chest_deck = list(COMMUNITY_CHEST_CARDS)
                random.shuffle(self.community_chest_deck)
            card = self.community_chest_deck.pop(0)
        
        self.phase = "card"
        self._show_card_popup(player, card, deck_type)
    
    def _execute_card_action(self, player: Player, card: Dict):
        """Execute the action from a card."""
        action = card.get("action")
        if not action:
            return
        
        action_type = action[0]
        
        if action_type == "money":
            amount = action[1]
            if amount > 0:
                player.add_money(amount)
            else:
                player.remove_money(abs(amount))
        
        elif action_type == "jail_free":
            player.get_out_of_jail_cards += 1
        
        elif action_type == "go_to_jail":
            self._send_to_jail(player)
            return  # Don't finish turn
        
        elif action_type == "advance":
            target_pos = action[1]
            collect_go = action[2] if len(action) > 2 else False
            
            if collect_go and target_pos < player.position:
                player.add_money(PASSING_GO_MONEY)
            
            player.position = target_pos
            self.land_on_space(player)
            return  # Don't finish turn (land_on_space will handle it)
        
        elif action_type == "collect_from_each":
            amount = action[1]
            for idx in self.active_players:
                if idx != player.idx and not self.players[idx].is_bankrupt:
                    if self.players[idx].remove_money(amount):
                        player.add_money(amount)
        
        elif action_type == "pay_each_player":
            amount = action[1]
            for idx in self.active_players:
                if idx != player.idx and not self.players[idx].is_bankrupt:
                    if player.remove_money(amount):
                        self.players[idx].add_money(amount)
        
        elif action_type == "pay_per_house_hotel":
            house_cost, hotel_cost = action[1]
            houses = player.get_total_houses(self.properties)
            hotels = player.get_total_hotels(self.properties)
            total = houses * house_cost + hotels * hotel_cost
            player.remove_money(total)
        
        self._finish_turn_or_allow_double()
    
    def _finish_turn_or_allow_double(self):
        """Either end turn or allow rolling again if doubles."""
        player = self.get_current_player()
        if player.consecutive_doubles > 0:
            self.phase = "roll"
            self.can_roll = True
        else:
            self.phase = "roll"
    
    def _show_buy_prompt(self, player: Player, position: int):
        """Show popup to buy property in player's panel."""
        space = self.properties[position]
        price = space.data.get("price", 0)
        
        self.active_popup = "buy_prompt"
        self.popup_data = {
            "player": player,
            "position": position,
            "price": price
        }
        
        panel = self.panels[player.idx]
        
        # Place buttons consistently to the right from player's perspective
        if panel.is_vertical():
            # For vertical panels, buttons go in the bottom right area
            yes_rect = panel.get_grid_rect(2, 9, 1.8, 1.2, 4, 12)
            no_rect = panel.get_grid_rect(2, 10.5, 1.8, 1.2, 4, 12)
        else:
            # For horizontal panels, buttons go on the right side
            yes_rect = panel.get_grid_rect(9, 1.5, 2.5, 1, 12, 4)
            no_rect = panel.get_grid_rect(9, 2.7, 2.5, 1, 12, 4)
        
        font = pygame.font.SysFont(None, 26)
        self.popup_buttons = [
            HoverButton(yes_rect, "Buy", font, orientation=panel.orientation),
            HoverButton(no_rect, "Pass", font, orientation=panel.orientation)
        ]
    
    def _show_card_popup(self, player: Player, card: Dict, deck_type: str):
        """Show card text popup."""
        self.active_popup = "card"
        self.popup_data = {
            "player": player,
            "card": card,
            "deck_type": deck_type
        }
        
        panel = self.panels[player.idx]
        
        # Consistent button placement
        if panel.is_vertical():
            ok_rect = panel.get_grid_rect(1, 10.5, 2, 1.2, 4, 12)
        else:
            ok_rect = panel.get_grid_rect(9.5, 2.5, 2, 1, 12, 4)
        
        font = pygame.font.SysFont(None, 26)
        self.popup_buttons = [
            HoverButton(ok_rect, "OK", font, orientation=panel.orientation)
        ]
    
    def _show_properties_popup(self, player: Player):
        """Show player's properties popup."""
        self.active_popup = "properties"
        self.popup_data = {"player": player}
        self.property_scroll = 0
        
        panel = self.panels[player.idx]
        
        # Consistent button placement - all to the right
        if panel.is_vertical():
            prev_rect = panel.get_grid_rect(2, 8.5, 1.8, 1, 4, 12)
            next_rect = panel.get_grid_rect(2, 9.7, 1.8, 1, 4, 12)
            close_rect = panel.get_grid_rect(2, 10.9, 1.8, 1, 4, 12)
        else:
            prev_rect = panel.get_grid_rect(9, 0.5, 2.5, 1, 12, 4)
            next_rect = panel.get_grid_rect(9, 1.7, 2.5, 1, 12, 4)
            close_rect = panel.get_grid_rect(9, 2.9, 2.5, 1, 12, 4)
        
        font = pygame.font.SysFont(None, 24)
        self.popup_buttons = [
            HoverButton(prev_rect, "◀ Prev", font, orientation=panel.orientation),
            HoverButton(next_rect, "Next ▶", font, orientation=panel.orientation),
            HoverButton(close_rect, "✕ Close", font, orientation=panel.orientation)
        ]
    
    def _show_build_popup(self, player: Player):
        """Show building options popup."""
        self.active_popup = "build"
        self.popup_data = {"player": player, "selected_group": None}
        self.property_scroll = 0
        
        panel = self.panels[player.idx]
        
        # Consistent button placement
        if panel.is_vertical():
            close_rect = panel.get_grid_rect(2, 10.9, 1.8, 1, 4, 12)
        else:
            close_rect = panel.get_grid_rect(9, 2.9, 2.5, 1, 12, 4)
        
        font = pygame.font.SysFont(None, 24)
        self.popup_buttons = [
            HoverButton(close_rect, "✕ Close", font, orientation=panel.orientation)
        ]
    
    def _buy_property(self, player: Player, position: int):
        """Player buys property."""
        space = self.properties[position]
        price = space.data.get("price", 0)
        
        if player.remove_money(price):
            space.owner = player.idx
            player.properties.append(position)
        
        self.active_popup = None
        self.popup_buttons = []
        self._finish_turn_or_allow_double()
    
    def _pay_rent(self, player: Player, position: int):
        """Pay rent to property owner."""
        space = self.properties[position]
        owner = self.players[space.owner]
        
        dice_sum = sum(self.dice_values) if space.data.get("type") == "utility" else None
        
        group = space.data.get("group")
        owned_in_group = 1
        if group in ("Railroad", "Utility"):
            owned_in_group = sum(1 for idx in owner.properties 
                                if self.properties[idx].data.get("group") == group)
        
        rent = space.get_rent(dice_sum, owned_in_group)
        
        if group and group not in ("Railroad", "Utility"):
            if owner.has_monopoly(group, self.properties) and space.houses == 0:
                rent *= 2
        
        if player.remove_money(rent):
            owner.add_money(rent)
        else:
            self._handle_bankruptcy(player, owed_to=owner)
        
        self._finish_turn_or_allow_double()
    
    def _send_to_jail(self, player: Player):
        """Send player to jail."""
        player.position = JAIL_POSITION
        player.in_jail = True
        player.jail_turns = 0
        player.consecutive_doubles = 0
        player.move_path = []
        self.advance_turn()
    
    def _handle_bankruptcy(self, player: Player, owed_to: Optional[Player] = None):
        """Handle player bankruptcy."""
        player.is_bankrupt = True
        
        if owed_to:
            for prop_idx in player.properties:
                self.properties[prop_idx].owner = owed_to.idx
                owed_to.properties.append(prop_idx)
        else:
            for prop_idx in player.properties:
                prop = self.properties[prop_idx]
                prop.owner = None
                prop.houses = 0
                prop.is_mortgaged = False
        
        player.properties = []
        
        active_count = sum(1 for idx in self.active_players 
                        if not self.players[idx].is_bankrupt)
        if active_count <= 1:
            self.phase = "game_over"
    
    def update(self, fingertip_meta: List[Dict]):
        """Update game state."""
        current_player = self.get_current_player()
        
        # Update dice rolling
        if self.dice_rolling:
            elapsed = time.time() - self.dice_roll_start
            if elapsed >= self.dice_roll_duration:
                self.dice_rolling = False
                self.dice_values = (random.randint(1, 6), random.randint(1, 6))
                
                is_doubles = self.dice_values[0] == self.dice_values[1]
                if is_doubles:
                    current_player.consecutive_doubles += 1
                    if current_player.consecutive_doubles >= 3:
                        self._send_to_jail(current_player)
                        return
                else:
                    current_player.consecutive_doubles = 0
                
                spaces = sum(self.dice_values)
                self.move_player(current_player, spaces)
        
        # Update player movement
        if current_player.is_moving:
            elapsed = time.time() - current_player.move_start
            move_duration = 0.3 * len(current_player.move_path)
            
            if elapsed >= move_duration:
                current_player.is_moving = False
                current_player.position = current_player.move_path[-1]
                current_player.move_path = []
                self.land_on_space(current_player)
        
        # Update buttons for ALL players
        for player_idx in range(8):
            player = self.players[player_idx]
            is_active = player_idx in self.active_players
            
            if not is_active or player.is_bankrupt:
                continue
            
            is_current = (player_idx == self.active_players[self.current_player_idx])
            
            for btn_name, btn in self.buttons[player_idx].items():
                enabled = False
                
                if btn_name == "action":
                    if is_current and self.phase == "roll" and not current_player.is_moving and not self.dice_rolling:
                        enabled = True
                        if self.can_roll:
                            btn.text = "Roll Again" if current_player.consecutive_doubles > 0 else "Roll"
                        else:
                            btn.text = "End Turn"
                
                elif btn_name == "props":
                    enabled = len(player.properties) > 0
                
                elif btn_name == "build":
                    enabled = any(player.has_monopoly(group, self.properties) 
                                for group in PROPERTY_GROUPS.keys() 
                                if group not in ("Railroad", "Utility"))
                
                if btn.update(fingertip_meta, enabled):
                    self._handle_button_click(player_idx, btn_name)
        
        # Update popup buttons
        for i, btn in enumerate(self.popup_buttons):
            if btn.update(fingertip_meta, True):
                self._handle_popup_button(i)
    
    def _handle_button_click(self, player_idx: int, button_name: str):
        """Handle button click."""
        player = self.players[player_idx]
        
        if button_name == "action":
            if self.phase == "roll" and self.can_roll and not self.dice_rolling:
                # Roll dice
                self.roll_dice()
            elif self.phase == "roll" and not self.can_roll:
                # End turn
                self.advance_turn()
        
        elif button_name == "props":
            self._show_properties_popup(player)
        
        elif button_name == "build":
            self._show_build_popup(player)
    
    def _handle_popup_button(self, button_idx: int):
        """Handle popup button click."""
        if self.active_popup == "buy_prompt":
            player = self.popup_data["player"]
            position = self.popup_data["position"]
            
            if button_idx == 0:  # Buy
                self._buy_property(player, position)
            else:  # Pass
                self.active_popup = None
                self.popup_buttons = []
                self._finish_turn_or_allow_double()
        
        elif self.active_popup == "card":
            player = self.popup_data["player"]
            card = self.popup_data["card"]
            
            self.active_popup = None
            self.popup_buttons = []
            self._execute_card_action(player, card)
        
        elif self.active_popup == "properties":
            if button_idx == 0:  # Prev
                self.property_scroll = max(0, self.property_scroll - 1)
            elif button_idx == 1:  # Next
                player = self.popup_data["player"]
                max_scroll = max(0, len(player.properties) - 1)
                self.property_scroll = min(max_scroll, self.property_scroll + 1)
            else:  # Close
                self.active_popup = None
                self.popup_buttons = []
        
        elif self.active_popup == "build":
            # Close
            self.active_popup = None
            self.popup_buttons = []
    
    def _get_space_position(self, space_idx: int) -> Tuple[int, int]:
        """Get screen position (center) for board space."""
        if space_idx >= len(self.space_positions):
            return (0, 0)
        
        x, y, w, h = self.space_positions[space_idx]
        return (x + w // 2, y + h // 2)
    
    def draw(self):
        """Draw the game."""
        # Draw background
        self.screen.fill((32, 96, 36))
        
        # Draw ALL player panels first (so board goes on top)
        self._draw_all_panels()
        
        # Draw board
        self._draw_board()
        
        # Draw player tokens
        self._draw_tokens()
        
        # Draw dice
        if self.dice_rolling or self.dice_values != (0, 0):
            self._draw_dice()
        
        # Draw popups (on top of everything)
        if self.active_popup:
            self._draw_popup()
        
        # Draw cursors (always on top)
        self._draw_cursors()
    
    def _draw_all_panels(self):
        """Draw all 8 player panels."""
        current_player_idx = self.active_players[self.current_player_idx] if self.active_players else -1
        
        for idx in range(8):
            player = self.players[idx]
            panel = self.panels[idx]
            is_active = idx in self.active_players
            is_current = (idx == current_player_idx)
            
            if is_active and not player.is_bankrupt:
                panel.draw_background(self.screen, is_current)
            else:
                washed = tuple(min(255, int(c * 0.3 + 60 * 0.7)) for c in panel.color)
                pygame.draw.rect(self.screen, washed, panel.rect, border_radius=8)
                pygame.draw.rect(self.screen, (40, 40, 40), panel.rect, width=1, border_radius=8)
            
            if is_active and not player.is_bankrupt:
                if panel.is_vertical():
                    # Vertical panels - stack info vertically with more space
                    info_rect = panel.get_grid_rect(0.5, 0.5, 3, 2.5, 4, 12)
                    font = pygame.font.SysFont("Arial", 18, bold=True)
                    
                    money_text = f"${player.money}"
                    props_text = f"{len(player.properties)}p"
                    
                    # Draw money at top of info area
                    RotatedText.draw(self.screen, money_text, font, Colors.BLACK,
                                   (info_rect.centerx, info_rect.top + 20), panel.orientation)
                    # Draw properties below with more spacing
                    RotatedText.draw(self.screen, props_text, font, Colors.BLACK,
                                   (info_rect.centerx, info_rect.top + 45), panel.orientation)
                else:
                    # Horizontal panels - single line
                    info_rect = panel.get_grid_rect(0.3, 0.2, 2.5, 0.8, 12, 4)
                    font = pygame.font.SysFont("Arial", 18, bold=True)
                    
                    combined = f"${player.money} | {len(player.properties)}p"
                    RotatedText.draw(self.screen, combined, font, Colors.BLACK,
                                   (info_rect.centerx, info_rect.centery), panel.orientation)
                
                for btn in self.buttons[idx].values():
                    btn.draw(self.screen)
                    
                    # Draw hover progress
                    for progress_info in btn.get_hover_progress():
                        center_x = progress_info["rect"].centerx + 20
                        center_y = progress_info["rect"].top - 20
                        draw_circular_progress(
                            self.screen, (center_x, center_y), 16,
                            progress_info["progress"], Colors.ACCENT, thickness=4
                        )
            else:
                # Draw player number for inactive slots
                font = pygame.font.SysFont("Arial", 36, bold=True)
                label = f"P{idx + 1}"
                text_surf = font.render(label, True, (100, 100, 100))
                if panel.orientation != 0:
                    text_surf = pygame.transform.rotate(text_surf, panel.orientation)
                text_rect = text_surf.get_rect(center=panel.rect.center)
                self.screen.blit(text_surf, text_rect)
    
    def _draw_board(self):
        """Draw the Monopoly board."""
        # Board background
        pygame.draw.rect(self.screen, (220, 240, 220), self.board_rect)
        pygame.draw.rect(self.screen, Colors.BLACK, self.board_rect, 3)
        
        # Center area with Monopoly logo
        space_size = self.space_positions[0][2]  # Get size from first space
        center_size = space_size * 9
        center_x = self.board_rect.x + space_size
        center_y = self.board_rect.y + space_size
        center_rect = pygame.Rect(center_x, center_y, center_size, center_size)
        pygame.draw.rect(self.screen, (240, 250, 240), center_rect)
        pygame.draw.rect(self.screen, Colors.BLACK, center_rect, 2)
        
        # Draw "MONOPOLY" in center
        font = pygame.font.SysFont(None, int(center_size * 0.12), bold=True)
        text = font.render("MONOPOLY", True, (180, 40, 40))
        text_rect = text.get_rect(center=center_rect.center)
        self.screen.blit(text, text_rect)
        
        # Draw spaces
        for i in range(40):
            self._draw_space(i)
    
    def _draw_space(self, idx: int):
        """Draw a single board space with modern styling."""
        if idx >= len(self.properties) or idx >= len(self.space_positions):
            return
            
        space = self.properties[idx]
        if space.data.get("type") == "none":
            return
        
        x, y, w, h = self.space_positions[idx]
        rect = pygame.Rect(x, y, w, h)
        
        space_type = space.data.get("type")
        if space_type in ("property", "railroad", "utility"):
            # Modern gradient-like color strip
            color = space.data.get("color", (200, 200, 200))
            strip_height = h // 4
            
            # Main strip
            strip_rect = pygame.Rect(rect.x, rect.y, rect.width, strip_height)
            pygame.draw.rect(self.screen, color, strip_rect)
            
            # Subtle shadow under strip
            shadow_rect = pygame.Rect(rect.x, rect.y + strip_height, rect.width, 2)
            shadow_color = tuple(max(0, c - 40) for c in color)
            pygame.draw.rect(self.screen, shadow_color, shadow_rect)
            
            # Clean white background
            main_rect = pygame.Rect(rect.x, rect.y + strip_height, rect.width, rect.height - strip_height)
            pygame.draw.rect(self.screen, (248, 248, 248), main_rect)
            
            # Sleek border
            pygame.draw.rect(self.screen, (50, 50, 50), rect, 1)
            
            # Draw houses/hotel with modern styling
            if space.houses > 0 and space_type == "property":
                house_size = max(4, w // 8)
                num_houses = min(space.houses, 4)
                spacing = 2
                total_width = num_houses * house_size + (num_houses - 1) * spacing
                start_x = rect.x + (rect.width - total_width) // 2
                
                for h_idx in range(num_houses):
                    house_x = start_x + h_idx * (house_size + spacing)
                    house_y = rect.y + 3
                    house_rect = pygame.Rect(house_x, house_y, house_size, house_size)
                    
                    if space.houses == 5:
                        # Hotel - red with white H
                        pygame.draw.rect(self.screen, (220, 40, 40), house_rect, border_radius=2)
                    else:
                        # House - green
                        pygame.draw.rect(self.screen, (60, 180, 60), house_rect, border_radius=2)
                    
                    # Subtle shadow
                    pygame.draw.rect(self.screen, (30, 30, 30), house_rect, 1, border_radius=2)
        else:
            # Special spaces with gradient background
            bg_color = (245, 245, 240)
            pygame.draw.rect(self.screen, bg_color, rect)
            
            # Subtle border
            pygame.draw.rect(self.screen, (80, 80, 80), rect, 1)
        
        # Draw space name with better typography
        name = space.data.get("name", "")
        if name:
            font_size = max(8, min(12, w // 5))
            font = pygame.font.SysFont("Arial", font_size, bold=False)
            
            # Word wrap
            words = name.split()
            lines = []
            current_line = ""
            max_width = w - 8
            
            for word in words:
                test_line = f"{current_line} {word}".strip()
                if font.size(test_line)[0] <= max_width:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)
            
            # Center text vertically
            line_height = font.get_linesize()
            center_x = x + w // 2
            
            # Calculate starting Y for vertical centering
            if space_type in ("property", "railroad", "utility"):
                # Text goes in the white area below the color strip
                available_height = h - (h // 4)
                center_y = y + (h // 4) + available_height // 2
            else:
                center_y = y + h // 2
            
            start_y = center_y - (len(lines[:3]) * line_height) // 2
            
            for i, line in enumerate(lines[:3]):
                text_surf = font.render(line, True, (40, 40, 40))
                text_rect = text_surf.get_rect(center=(center_x, start_y + i * line_height))
                self.screen.blit(text_surf, text_rect)

    def _draw_tokens(self):
        """Draw player tokens on board."""
        # Group players by position
        positions: Dict[int, List[Player]] = {}
        for idx in self.active_players:
            player = self.players[idx]
            if player.is_bankrupt:
                continue
            
            # Handle moving animation
            if player.is_moving:
                elapsed = time.time() - player.move_start
                move_duration = 0.3 * len(player.move_path)
                progress = min(1.0, elapsed / move_duration)
                
                # Calculate position along path
                path_progress = progress * len(player.move_path)
                path_idx = int(path_progress)
                path_frac = path_progress - path_idx
                
                if path_idx >= len(player.move_path):
                    pos = player.move_path[-1]
                else:
                    current_space = player.move_path[path_idx]
                    next_space = player.move_path[path_idx + 1] if path_idx + 1 < len(player.move_path) else current_space
                    
                    # Interpolate position
                    x1, y1 = self._get_space_position(current_space)
                    x2, y2 = self._get_space_position(next_space)
                    
                    x = int(x1 + (x2 - x1) * path_frac)
                    y = int(y1 + (y2 - y1) * path_frac)
                    
                    # Add bounce
                    bounce = math.sin(path_frac * math.pi) * 20
                    y -= int(bounce)
                    
                    # Draw moving token
                    pygame.draw.circle(self.screen, Colors.BLACK, (x+2, y+3), 12)
                    pygame.draw.circle(self.screen, player.color, (x, y), 10)
                    continue
            
            positions.setdefault(player.position, []).append(player)
        
        # Draw stationary tokens
        token_radius = 10
        for pos, players in positions.items():
            x, y = self._get_space_position(pos)
            
            if len(players) == 1:
                player = players[0]
                pygame.draw.circle(self.screen, Colors.BLACK, (x+1, y+2), token_radius + 1)
                pygame.draw.circle(self.screen, player.color, (x, y), token_radius)
            else:
                # Multiple tokens - arrange in circle
                angle_step = 2 * math.pi / len(players)
                radius = 18
                for i, player in enumerate(players):
                    angle = i * angle_step
                    px = x + int(math.cos(angle) * radius)
                    py = y + int(math.sin(angle) * radius)
                    pygame.draw.circle(self.screen, Colors.BLACK, (px+1, py+2), token_radius + 1)
                    pygame.draw.circle(self.screen, player.color, (px, py), token_radius)
    
    def _draw_dice(self):
        """Draw dice in center of board."""
        center_x = self.board_rect.centerx
        center_y = self.board_rect.centery + 60  # Below center
        die_size = 50
        
        if self.dice_rolling:
            # Animated rolling
            for i in range(2):
                x = center_x - die_size - 10 + i * (die_size + 20)
                
                # Random rotation while rolling
                angle = random.randint(-15, 15)
                value = random.randint(1, 6)
                
                die_surf = self._create_die_surface(value, die_size)
                rotated = pygame.transform.rotate(die_surf, angle)
                rect = rotated.get_rect(center=(x, center_y))
                self.screen.blit(rotated, rect)
        else:
            # Static dice showing result
            for i, value in enumerate(self.dice_values):
                if value == 0:
                    continue
                x = center_x - die_size - 10 + i * (die_size + 20)
                die_surf = self._create_die_surface(value, die_size)
                rect = die_surf.get_rect(center=(x, center_y))
                self.screen.blit(die_surf, rect)
    
    def _create_die_surface(self, value: int, size: int) -> pygame.Surface:
        """Create a die face surface."""
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        
        # White die with rounded corners effect
        pygame.draw.rect(surf, Colors.WHITE, surf.get_rect(), border_radius=8)
        pygame.draw.rect(surf, Colors.BLACK, surf.get_rect(), 2, border_radius=8)
        
        # Dot positions for each value
        dot_radius = size // 10
        positions = {
            1: [(0.5, 0.5)],
            2: [(0.25, 0.25), (0.75, 0.75)],
            3: [(0.25, 0.25), (0.5, 0.5), (0.75, 0.75)],
            4: [(0.25, 0.25), (0.75, 0.25), (0.25, 0.75), (0.75, 0.75)],
            5: [(0.25, 0.25), (0.75, 0.25), (0.5, 0.5), (0.25, 0.75), (0.75, 0.75)],
            6: [(0.25, 0.25), (0.75, 0.25), (0.25, 0.5), (0.75, 0.5), (0.25, 0.75), (0.75, 0.75)]
        }
        
        for px, py in positions.get(value, []):
            x = int(px * size)
            y = int(py * size)
            pygame.draw.circle(surf, Colors.BLACK, (x, y), dot_radius)
        
        return surf
    
    def _draw_popup(self):
        """Draw active popup."""
        if self.active_popup == "buy_prompt":
            self._draw_buy_prompt()
        elif self.active_popup == "card":
            self._draw_card_popup()
        elif self.active_popup == "properties":
            self._draw_properties_popup()
        elif self.active_popup == "build":
            self._draw_build_popup()
    
    def _draw_buy_prompt(self):
        """Draw property purchase prompt with modern styling."""
        player = self.popup_data["player"]
        position = self.popup_data["position"]
        price = self.popup_data["price"]
        space = self.properties[position]
        
        panel = self.panels[player.idx]
        
        # Modern semi-transparent overlay with blur effect
        overlay = pygame.Surface(panel.rect.size, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, panel.rect)
        
        # Modern fonts
        font_title = pygame.font.SysFont("Arial", 26, bold=True)
        font_info = pygame.font.SysFont("Arial", 20)
        font_price = pygame.font.SysFont("Arial", 32, bold=True)
        
        name = space.data.get("name", "")
        price_text = f"${price}"
        
        if panel.is_vertical():
            # Content area on the left, buttons on the right
            content_rect = panel.get_grid_rect(0.2, 2, 1.6, 8, 4, 12)
            
            # Property color indicator
            color = space.data.get("color", (200, 200, 200))
            color_bar = pygame.Rect(content_rect.x, content_rect.y, content_rect.width, 8)
            pygame.draw.rect(self.screen, color, color_bar, border_radius=4)
            
            # Property name
            y_pos = content_rect.y + 25
            RotatedText.draw(self.screen, name, font_title, Colors.WHITE,
                        (content_rect.centerx, y_pos), panel.orientation, 
                        max_width=content_rect.width - 10)
            
            # Price with modern styling
            y_pos += 60
            RotatedText.draw(self.screen, "Price", font_info, (180, 180, 180),
                        (content_rect.centerx, y_pos), panel.orientation)
            y_pos += 30
            RotatedText.draw(self.screen, price_text, font_price, Colors.ACCENT,
                        (content_rect.centerx, y_pos), panel.orientation)
            
            # Affordability indicator
            y_pos += 50
            if player.money >= price:
                status_text = "✓ Can afford"
                status_color = (100, 220, 100)
            else:
                status_text = "✗ Cannot afford"
                status_color = (255, 100, 100)
            
            RotatedText.draw(self.screen, status_text, font_info, status_color,
                        (content_rect.centerx, y_pos), panel.orientation)
            
            # Balance info
            y_pos += 40
            balance_text = f"Your balance: ${player.money}"
            RotatedText.draw(self.screen, balance_text, font_info, (200, 200, 200),
                        (content_rect.centerx, y_pos), panel.orientation)
        else:
            # Horizontal layout - content on left, buttons on right
            content_rect = panel.get_grid_rect(0.5, 0.5, 7.5, 3, 12, 4)
            
            # Property color indicator
            color = space.data.get("color", (200, 200, 200))
            color_bar = pygame.Rect(content_rect.x, content_rect.y, content_rect.width, 6)
            pygame.draw.rect(self.screen, color, color_bar, border_radius=3)
            
            # Two column layout
            left_x = content_rect.x + 20
            right_x = content_rect.centerx + 20
            y_pos = content_rect.y + 30
            
            # Left column - property info
            RotatedText.draw(self.screen, name, font_title, Colors.WHITE,
                        (left_x, y_pos), panel.orientation)
            
            y_pos += 35
            RotatedText.draw(self.screen, f"Price: {price_text}", font_info, Colors.ACCENT,
                        (left_x, y_pos), panel.orientation)
            
            # Right column - player status
            y_pos = content_rect.y + 30
            RotatedText.draw(self.screen, f"Balance: ${player.money}", font_info, (200, 200, 200),
                        (right_x, y_pos), panel.orientation)
            
            y_pos += 35
            if player.money >= price:
                status_text = "✓ Can afford"
                status_color = (100, 220, 100)
            else:
                status_text = "✗ Cannot afford"
                status_color = (255, 100, 100)
            
            RotatedText.draw(self.screen, status_text, font_info, status_color,
                        (right_x, y_pos), panel.orientation)
        
        # Draw modern buttons
        for btn in self.popup_buttons:
            btn.draw(self.screen)
            
            for progress_info in btn.get_hover_progress():
                center_x = progress_info["rect"].centerx + 20
                center_y = progress_info["rect"].top - 20
                draw_circular_progress(
                    self.screen, (center_x, center_y), 16,
                    progress_info["progress"], Colors.ACCENT, thickness=4
                )
    
    def _draw_card_popup(self):
        """Draw card text popup with modern styling."""
        player = self.popup_data["player"]
        card = self.popup_data["card"]
        deck_type = self.popup_data["deck_type"]
        
        panel = self.panels[player.idx]
        
        # Modern overlay
        overlay = pygame.Surface(panel.rect.size, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, panel.rect)
        
        # Modern fonts
        font_title = pygame.font.SysFont("Arial", 24, bold=True)
        font_text = pygame.font.SysFont("Arial", 16)
        
        title = "CHANCE" if deck_type == "chance" else "COMMUNITY CHEST"
        card_text = card.get("text", "")
        
        # Title color based on deck type
        title_color = (255, 200, 60) if deck_type == "chance" else (100, 180, 255)
        
        if panel.is_vertical():
            content_rect = panel.get_grid_rect(0.2, 1.5, 1.6, 6.5, 4, 12)
            
            # Decorative top bar
            top_bar = pygame.Rect(content_rect.x, content_rect.y, content_rect.width, 4)
            pygame.draw.rect(self.screen, title_color, top_bar, border_radius=2)
            
            # Title
            RotatedText.draw(self.screen, title, font_title, title_color,
                        (content_rect.centerx, content_rect.y + 25), panel.orientation)
            
            # Card text area with padding
            text_area = content_rect.inflate(-20, -60)
            text_area.y += 40
            
            RotatedText.draw_wrapped(self.screen, card_text, font_text, Colors.WHITE,
                                text_area, panel.orientation)
        else:
            content_rect = panel.get_grid_rect(0.5, 0.3, 8, 3.4, 12, 4)
            
            # Decorative top bar
            top_bar = pygame.Rect(content_rect.x, content_rect.y, content_rect.width, 3)
            pygame.draw.rect(self.screen, title_color, top_bar, border_radius=2)
            
            # Title
            RotatedText.draw(self.screen, title, font_title, title_color,
                        (content_rect.centerx, content_rect.y + 20), panel.orientation)
            
            # Card text
            text_area = content_rect.inflate(-30, -50)
            text_area.y += 30
            
            RotatedText.draw_wrapped(self.screen, card_text, font_text, Colors.WHITE,
                                text_area, panel.orientation)
        
        # Draw button
        for btn in self.popup_buttons:
            btn.draw(self.screen)
            
            for progress_info in btn.get_hover_progress():
                center_x = progress_info["rect"].centerx + 20
                center_y = progress_info["rect"].top - 20
                draw_circular_progress(
                    self.screen, (center_x, center_y), 16,
                    progress_info["progress"], Colors.ACCENT, thickness=4
                )
    
    def _draw_properties_popup(self):
        """Draw properties list popup with modern styling."""
        player = self.popup_data["player"]
        panel = self.panels[player.idx]
        
        # Modern overlay
        overlay = pygame.Surface(panel.rect.size, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, panel.rect)
        
        # Modern fonts
        font_title = pygame.font.SysFont("Arial", 22, bold=True)
        font_text = pygame.font.SysFont("Arial", 16)
        font_small = pygame.font.SysFont("Arial", 14)
        
        if not player.properties:
            no_props = font_text.render("No properties owned", True, (180, 180, 180))
            self.screen.blit(no_props, no_props.get_rect(center=panel.rect.center))
        else:
            # Show one property at a time
            prop_idx = player.properties[self.property_scroll]
            prop = self.properties[prop_idx]
            
            if panel.is_vertical():
                content_rect = panel.get_grid_rect(0.2, 1.5, 1.6, 6.5, 4, 12)
            else:
                content_rect = panel.get_grid_rect(0.5, 0.3, 8, 3.4, 12, 4)
            
            # Property color bar
            color = prop.data.get("color", (200, 200, 200))
            color_bar = pygame.Rect(content_rect.x, content_rect.y, content_rect.width, 6)
            pygame.draw.rect(self.screen, color, color_bar, border_radius=3)
            
            # Property name
            name = prop.data.get("name", "")
            RotatedText.draw(self.screen, name, font_title, Colors.WHITE,
                        (content_rect.centerx, content_rect.y + 25), panel.orientation,
                        max_width=content_rect.width - 20)
            
            # Property details in clean layout
            y_offset = 60
            details = [
                ("Type", prop.data.get("type", "property").title()),
                ("Value", f"${prop.data.get('price', 0)}"),
            ]
            
            if prop.data.get("type") == "property":
                details.append(("Houses", str(prop.houses)))
                if prop.houses > 0:
                    rent = prop.data.get("rent", [0])[prop.houses]
                    details.append(("Rent", f"${rent}"))
            
            details.append(("Status", "Mortgaged" if prop.is_mortgaged else "Active"))
            
            for label, value in details:
                # Label on left, value on right
                label_x = content_rect.x + 15
                value_x = content_rect.right - 15
                y = content_rect.y + y_offset
                
                RotatedText.draw(self.screen, label, font_small, (150, 150, 150),
                            (label_x, y), panel.orientation)
                RotatedText.draw(self.screen, value, font_text, Colors.WHITE,
                            (value_x, y), panel.orientation)
                y_offset += 28
            
            # Page indicator
            page_text = f"Property {self.property_scroll + 1} of {len(player.properties)}"
            RotatedText.draw(self.screen, page_text, font_small, (120, 120, 120),
                        (content_rect.centerx, content_rect.bottom - 20), panel.orientation)
        
        # Draw navigation buttons
        for btn in self.popup_buttons:
            btn.draw(self.screen)
            
            for progress_info in btn.get_hover_progress():
                center_x = progress_info["rect"].centerx + 20
                center_y = progress_info["rect"].top - 20
                draw_circular_progress(
                    self.screen, (center_x, center_y), 16,
                    progress_info["progress"], Colors.ACCENT, thickness=4
                )
    
    def _draw_build_popup(self):
        """Draw building options popup."""
        player = self.popup_data["player"]
        panel = self.panels[player.idx]
        
        # Modern overlay
        overlay = pygame.Surface(panel.rect.size, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, panel.rect)
        
        # Modern fonts
        font_title = pygame.font.SysFont("Arial", 24, bold=True)
        title_text = "Building (Coming Soon)"
        RotatedText.draw(self.screen, title_text, font_title, Colors.ACCENT,
                       (panel.rect.centerx, panel.rect.centery), panel.orientation)
        
        for btn in self.popup_buttons:
            btn.draw(self.screen)
            
            for progress_info in btn.get_hover_progress():
                center_x = progress_info["rect"].centerx + 20
                center_y = progress_info["rect"].top - 20
                draw_circular_progress(
                    self.screen, (center_x, center_y), 16,
                    progress_info["progress"], Colors.ACCENT, thickness=4
                )
    
    def _draw_cursors(self):
        """Draw cursors for all fingertips."""
        fingertips = self.get_fingertips(*self.screen_size)
        for meta in fingertips:
            pos = meta["pos"]
            
            # Find closest player panel to color the cursor
            min_dist = float('inf')
            closest_color = Colors.WHITE
            
            for idx in self.active_players:
                panel = self.panels[idx]
                center = panel.rect.center
                dist = math.sqrt((pos[0] - center[0])**2 + (pos[1] - center[1])**2)
                if dist < min_dist:
                    min_dist = dist
                    closest_color = panel.color
            
            # Draw cursor with player color
            pygame.draw.circle(self.screen, Colors.WHITE, pos, 18)
            pygame.draw.circle(self.screen, closest_color, pos, 12)
            pygame.draw.circle(self.screen, Colors.BLACK, pos, 4)
