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
        
        # UI
        self.panels = calculate_all_panels(self.screen_size)
        self.buttons: Dict[int, Dict[str, HoverButton]] = {}
        
        # Game flow
        self.phase = "roll"  # "roll", "moving", "landed", "buying", "paying_rent"
        self.can_roll = True
        self.dice_values = (0, 0)
        self.dice_rolling = False
        self.dice_roll_start = 0.0
        self.dice_roll_duration = 1.2
        
        # UI popups
        self.active_popup: Optional[str] = None  # "properties", "trade", "buy_prompt"
        self.popup_data: Dict = {}
        self.popup_buttons: List[HoverButton] = []
        
        # Board geometry
        self._calculate_board_geometry()
        
        # Initialize buttons after geometry is set
        self._init_buttons()
    
    def _calculate_board_geometry(self):
        """Calculate board layout with proper spacing."""
        w, h = self.screen_size
        
        # Panel sizes
        horizontal_panel_height = int(h * 0.10)
        vertical_panel_width = int(w * 0.12)
        
        # Board takes remaining space in center
        available_width = w - (2 * vertical_panel_width)
        available_height = h - (2 * horizontal_panel_height)
        
        # Make board square, using smaller dimension
        board_size = min(available_width, available_height)
        
        # Center the board
        board_x = vertical_panel_width + (available_width - board_size) // 2
        board_y = horizontal_panel_height + (available_height - board_size) // 2
        
        self.board_rect = pygame.Rect(board_x, board_y, board_size, board_size)
        self.space_size = board_size // 11  # 11 spaces per side (including corners)
    
    def _init_buttons(self):
        """Initialize player panel buttons with proper sizing."""
        for panel in self.panels:
            player_idx = panel.player_idx
            font_size = 24 if panel.is_vertical() else 28
            button_font = pygame.font.SysFont(None, font_size)
            
            if panel.is_vertical():
                # Vertical panels - stack buttons vertically
                action_rect = panel.get_grid_rect(0.5, 2, 3, 2, 4, 12)
                props_rect = panel.get_grid_rect(0.5, 5, 3, 2, 4, 12)
                build_rect = panel.get_grid_rect(0.5, 8, 3, 2, 4, 12)
            else:
                # Horizontal panels - arrange buttons horizontally
                action_rect = panel.get_grid_rect(1, 1, 3, 2, 12, 4)
                props_rect = panel.get_grid_rect(4.5, 1, 3, 2, 12, 4)
                build_rect = panel.get_grid_rect(8, 1, 3, 2, 12, 4)
            
            action_btn = HoverButton(
                action_rect, "Roll", 
                button_font,
                orientation=panel.orientation
            )
            
            props_btn = HoverButton(
                props_rect, "Props",
                button_font,
                orientation=panel.orientation
            )
            
            build_btn = HoverButton(
                build_rect, "Build",
                button_font,
                orientation=panel.orientation
            )
            
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
        for i in range(1, spaces + 1):
            player.move_path.append((old_pos + i) % 40)
        
        player.is_moving = True
        player.move_start = time.time()
        self.phase = "moving"
    
    def land_on_space(self, player: Player):
        """Handle landing on a space."""
        position = player.position
        space = self.properties[position]
        space_type = space.data.get("type")
        
        # Check if passed GO
        if player.move_from > player.position or (player.move_from == 0 and player.position != 0):
            player.add_money(PASSING_GO_MONEY)
        
        # Handle different space types
        if space_type == "go":
            player.add_money(PASSING_GO_MONEY)
            self.phase = "roll"
            
        elif space_type in ("property", "railroad", "utility"):
            if space.owner is None:
                # Unowned property - offer to buy
                self.phase = "buying"
                self._show_buy_prompt(player, position)
            elif space.owner != player.idx:
                # Owned by another player - pay rent
                self.phase = "paying_rent"
                self._pay_rent(player, position)
            else:
                self.phase = "roll"
                
        elif space_type == "go_to_jail":
            self._send_to_jail(player)
            self.phase = "roll"
            
        elif space_type == "income_tax":
            player.remove_money(INCOME_TAX)
            self.phase = "roll"
            
        elif space_type == "luxury_tax":
            player.remove_money(LUXURY_TAX)
            self.phase = "roll"
            
        elif space_type in ("chance", "community_chest"):
            # TODO: Implement card drawing
            self.phase = "roll"
            
        else:
            # Free parking, jail (just visiting), etc.
            self.phase = "roll"
        
        # Check if bankrupt
        if player.money < 0:
            self._handle_bankruptcy(player)
    
    def _show_buy_prompt(self, player: Player, position: int):
        """Show popup to buy property."""
        space = self.properties[position]
        price = space.data.get("price", 0)
        
        self.active_popup = "buy_prompt"
        self.popup_data = {
            "player": player,
            "position": position,
            "price": price
        }
        
        # Create Yes/No buttons centered in board
        center_x = self.board_rect.centerx
        center_y = self.board_rect.centery
        button_width = 120
        button_height = 50
        button_spacing = 20
        
        yes_rect = pygame.Rect(
            center_x - button_width - button_spacing // 2,
            center_y + 40,
            button_width,
            button_height
        )
        no_rect = pygame.Rect(
            center_x + button_spacing // 2,
            center_y + 40,
            button_width,
            button_height
        )
        
        self.popup_buttons = [
            HoverButton(yes_rect, "Buy", pygame.font.SysFont(None, 32)),
            HoverButton(no_rect, "Pass", pygame.font.SysFont(None, 32))
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
        
        # If didn't roll doubles, end turn
        if player.consecutive_doubles == 0:
            self.advance_turn()
        else:
            self.phase = "roll"
            self.can_roll = True
    
    def _pay_rent(self, player: Player, position: int):
        """Pay rent to property owner."""
        space = self.properties[position]
        owner = self.players[space.owner]
        
        # Calculate rent
        dice_sum = sum(self.dice_values) if space.data.get("type") == "utility" else None
        
        # Count properties in group for railroads/utilities
        group = space.data.get("group")
        owned_in_group = 1
        if group in ("Railroad", "Utility"):
            owned_in_group = sum(1 for idx in owner.properties 
                                if self.properties[idx].data.get("group") == group)
        
        rent = space.get_rent(dice_sum, owned_in_group)
        
        # Double rent if monopoly and no houses
        if group and group not in ("Railroad", "Utility"):
            if owner.has_monopoly(group, self.properties) and space.houses == 0:
                rent *= 2
        
        # Transfer money
        if player.remove_money(rent):
            owner.add_money(rent)
        else:
            # Can't afford - handle bankruptcy
            self._handle_bankruptcy(player, owed_to=owner)
        
        # End turn or allow another roll
        if player.consecutive_doubles == 0:
            self.advance_turn()
        else:
            self.phase = "roll"
            self.can_roll = True
    
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
        
        # Transfer properties to creditor or bank
        if owed_to:
            for prop_idx in player.properties:
                self.properties[prop_idx].owner = owed_to.idx
                owed_to.properties.append(prop_idx)
        else:
            # Properties go back to bank
            for prop_idx in player.properties:
                prop = self.properties[prop_idx]
                prop.owner = None
                prop.houses = 0
                prop.is_mortgaged = False
        
        player.properties = []
        
        # Check if game over
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
                # Dice finished rolling
                self.dice_rolling = False
                self.dice_values = (random.randint(1, 6), random.randint(1, 6))
                
                # Check for doubles
                is_doubles = self.dice_values[0] == self.dice_values[1]
                if is_doubles:
                    current_player.consecutive_doubles += 1
                    if current_player.consecutive_doubles >= 3:
                        # Three doubles - go to jail
                        self._send_to_jail(current_player)
                        return
                else:
                    current_player.consecutive_doubles = 0
                
                # Move player
                spaces = sum(self.dice_values)
                self.move_player(current_player, spaces)
        
        # Update player movement
        if current_player.is_moving:
            elapsed = time.time() - current_player.move_start
            move_duration = 0.3 * len(current_player.move_path)
            
            if elapsed >= move_duration:
                # Finished moving
                current_player.is_moving = False
                current_player.position = current_player.move_path[-1]
                current_player.move_path = []
                self.land_on_space(current_player)
        
        # Update buttons for ALL players (active and inactive)
        for player_idx in range(8):
            player = self.players[player_idx]
            is_active = player_idx in self.active_players
            
            if not is_active:
                continue
            
            if player.is_bankrupt:
                continue
            
            is_current = (player_idx == self.active_players[self.current_player_idx])
            
            for btn_name, btn in self.buttons[player_idx].items():
                enabled = False
                
                if btn_name == "action":
                    if is_current and self.phase == "roll" and not current_player.is_moving:
                        enabled = True
                        if current_player.consecutive_doubles > 0:
                            btn.text = "Roll"
                        else:
                            btn.text = "Roll" if self.can_roll else "End"
                
                elif btn_name == "props":
                    enabled = len(player.properties) > 0
                
                elif btn_name == "build":
                    # Can build if have monopoly
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
            if self.phase == "roll" and self.can_roll:
                self.roll_dice()
            elif player.consecutive_doubles == 0:
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
                if player.consecutive_doubles == 0:
                    self.advance_turn()
                else:
                    self.phase = "roll"
                    self.can_roll = True
    
    def _show_properties_popup(self, player: Player):
        """Show player's properties."""
        self.active_popup = "properties"
        self.popup_data = {"player": player}
        # TODO: Implement property list UI
    
    def _show_build_popup(self, player: Player):
        """Show building options."""
        self.active_popup = "build"
        self.popup_data = {"player": player}
        # TODO: Implement building UI
    
    def _get_space_position(self, space_idx: int) -> Tuple[int, int]:
        """Get screen position for board space."""
        # Bottom row: 0-10 (right to left)
        # Left column: 11-19 (bottom to top)
        # Top row: 20-30 (left to right)
        # Right column: 31-39 (top to bottom)
        
        board_x = self.board_rect.x
        board_y = self.board_rect.y
        size = self.board_rect.width
        space = self.space_size
        
        if space_idx <= 10:  # Bottom
            x = board_x + size - (space_idx * space) - space // 2
            y = board_y + size - space // 2
        elif space_idx <= 19:  # Left
            x = board_x + space // 2
            y = board_y + size - ((space_idx - 10) * space) - space // 2
        elif space_idx <= 30:  # Top
            x = board_x + ((space_idx - 20) * space) + space // 2
            y = board_y + space // 2
        else:  # Right
            x = board_x + size - space // 2
            y = board_y + ((space_idx - 30) * space) + space // 2
        
        return (x, y)
    
    def draw(self):
        """Draw the game."""
        # Draw background
        self.screen.fill((32, 96, 36))
        
        # Draw ALL player panels (even inactive ones, just dimmed)
        self._draw_all_panels()
        
        # Draw board
        self._draw_board()
        
        # Draw player tokens
        self._draw_tokens()
        
        # Draw dice
        if self.dice_rolling or self.dice_values != (0, 0):
            self._draw_dice()
        
        # Draw popups
        if self.active_popup:
            self._draw_popup()
        
        # Draw cursors
        self._draw_cursors()
    
    def _draw_all_panels(self):
        """Draw all 8 player panels, highlighting active players."""
        current_player_idx = self.active_players[self.current_player_idx] if self.active_players else -1
        
        for idx in range(8):
            player = self.players[idx]
            panel = self.panels[idx]
            is_active = idx in self.active_players
            is_current = (idx == current_player_idx)
            
            # Draw panel background (dimmed if not active)
            if is_active and not player.is_bankrupt:
                panel.draw_background(self.screen, is_current)
            else:
                # Draw dimmed panel for inactive players
                washed = tuple(min(255, int(c * 0.3 + 60 * 0.7)) for c in panel.color)
                pygame.draw.rect(self.screen, washed, panel.rect, border_radius=8)
                pygame.draw.rect(self.screen, (40, 40, 40), panel.rect, width=1, border_radius=8)
            
            # Only draw content for active players
            if is_active and not player.is_bankrupt:
                # Draw player info (money, properties)
                if panel.is_vertical():
                    info_rect = panel.get_grid_rect(0.5, 0.5, 3, 1.5, 4, 12)
                else:
                    info_rect = panel.get_grid_rect(0.5, 0.2, 2, 0.8, 12, 4)
                
                font_size = 18 if panel.is_vertical() else 20
                font = pygame.font.SysFont(None, font_size)
                
                money_text = f"${player.money}"
                props_text = f"{len(player.properties)}p"
                
                if panel.is_vertical():
                    RotatedText.draw(self.screen, money_text, font, Colors.BLACK,
                                (info_rect.centerx, info_rect.centery - 10), panel.orientation)
                    RotatedText.draw(self.screen, props_text, font, Colors.BLACK,
                                (info_rect.centerx, info_rect.centery + 10), panel.orientation)
                else:
                    combined = f"{money_text} | {props_text}"
                    RotatedText.draw(self.screen, combined, font, Colors.BLACK,
                                (info_rect.centerx, info_rect.centery), panel.orientation)
                
                # Draw buttons
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
                font = pygame.font.SysFont(None, 36)
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
        center_size = self.space_size * 9
        center_x = self.board_rect.x + self.space_size
        center_y = self.board_rect.y + self.space_size
        center_rect = pygame.Rect(center_x, center_y, center_size, center_size)
        pygame.draw.rect(self.screen, (240, 250, 240), center_rect)
        pygame.draw.rect(self.screen, Colors.BLACK, center_rect, 2)
        
        # Draw "MONOPOLY" in center
        font = pygame.font.SysFont(None, int(center_size * 0.15), bold=True)
        text = font.render("MONOPOLY", True, (180, 40, 40))
        text_rect = text.get_rect(center=center_rect.center)
        self.screen.blit(text, text_rect)
        
        # Draw spaces
        for i in range(40):
            self._draw_space(i)
    
    def _draw_space(self, idx: int):
        """Draw a single board space."""
        if idx >= len(self.properties):
            return
            
        space = self.properties[idx]
        if space.data.get("type") == "none":
            return
            
        x, y = self._get_space_position(idx)
        
        # Determine if corner
        is_corner = idx in (0, 10, 20, 30)
        size = int(self.space_size * 1.4) if is_corner else self.space_size
        
        rect = pygame.Rect(x - size//2, y - size//2, size, size)
        
        # Draw space background
        space_type = space.data.get("type")
        if space_type in ("property", "railroad", "utility"):
            # Color strip at top
            color = space.data.get("color", (200, 200, 200))
            strip_height = size // 4
            strip_rect = pygame.Rect(rect.x, rect.y, rect.width, strip_height)
            pygame.draw.rect(self.screen, color, strip_rect)
            
            # White background
            main_rect = pygame.Rect(rect.x, rect.y + strip_height, rect.width, rect.height - strip_height)
            pygame.draw.rect(self.screen, Colors.WHITE, main_rect)
            pygame.draw.rect(self.screen, Colors.BLACK, rect, 1)
            
            # Draw houses/hotel
            if space.houses > 0 and space_type == "property":
                house_size = max(4, size // 8)
                num_houses = min(space.houses, 4)
                for h in range(num_houses):
                    house_x = rect.x + 2 + h * (house_size + 1)
                    house_y = rect.y + 2
                    house_rect = pygame.Rect(house_x, house_y, house_size, house_size)
                    house_color = (200, 0, 0) if space.houses == 5 else (0, 150, 0)
                    pygame.draw.rect(self.screen, house_color, house_rect)
        else:
            # Special spaces
            bg_color = (240, 240, 230)
            pygame.draw.rect(self.screen, bg_color, rect)
            pygame.draw.rect(self.screen, Colors.BLACK, rect, 2)
        
        # Draw space name (smaller font)
        name = space.data.get("name", "")
        if name and not is_corner:
            font_size = max(8, size // 8)
            font = pygame.font.SysFont(None, font_size)
            
            # Truncate if too long
            if len(name) > 12:
                name = name[:10] + ".."
            
            text_surf = font.render(name, True, Colors.BLACK)
            text_rect = text_surf.get_rect(center=(x, y + size // 4))
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
        """Draw dice in center of board without background."""
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
        """Create a die face surface with transparency."""
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
    
    def _draw_buy_prompt(self):
        """Draw property purchase prompt in center of board."""
        player = self.popup_data["player"]
        position = self.popup_data["position"]
        price = self.popup_data["price"]
        space = self.properties[position]
        
        # Draw semi-transparent overlay over entire board
        overlay_rect = self.board_rect.inflate(20, 20)
        overlay = pygame.Surface(overlay_rect.size, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, overlay_rect)
        
        # Draw property info
        font_title = pygame.font.SysFont(None, 40, bold=True)
        font_info = pygame.font.SysFont(None, 32)
        
        center_x = self.board_rect.centerx
        center_y = self.board_rect.centery - 40
        
        name = space.data.get("name", "")
        name_surf = font_title.render(name, True, Colors.WHITE)
        name_rect = name_surf.get_rect(center=(center_x, center_y - 60))
        self.screen.blit(name_surf, name_rect)
        
        price_text = f"Price: ${price}"
        price_surf = font_info.render(price_text, True, Colors.WHITE)
        price_rect = price_surf.get_rect(center=(center_x, center_y - 10))
        self.screen.blit(price_surf, price_rect)
        
        afford_text = "Can afford" if player.money >= price else "Cannot afford!"
        color = Colors.ACCENT if player.money >= price else (255, 100, 100)
        afford_surf = font_info.render(afford_text, True, color)
        afford_rect = afford_surf.get_rect(center=(center_x, center_y + 20))
        self.screen.blit(afford_surf, afford_rect)
        
        # Draw buttons
        for btn in self.popup_buttons:
            btn.draw(self.screen)
            
            for progress_info in btn.get_hover_progress():
                center_x = progress_info["rect"].centerx + 20
                center_y = progress_info["rect"].top - 20
                draw_circular_progress(
                    self.screen, (center_x, center_y), 18,
                    progress_info["progress"], Colors.ACCENT, thickness=5
                )
    
    def _draw_cursors(self):
        """Draw cursors for all fingertips."""
        fingertips = self.get_fingertips(*self.screen_size)
        for meta in fingertips:
            pos = meta["pos"]
            # Find closest active player color
            min_dist = float('inf')
            closest_color = Colors.WHITE
            
            for idx in self.active_players:
                panel = self.panels[idx]
                center = panel.rect.center
                dist = math.sqrt((pos[0] - center[0])**2 + (pos[1] - center[1])**2)
                if dist < min_dist:
                    min_dist = dist
                    closest_color = panel.color
            
            # Draw cursor
            pygame.draw.circle(self.screen, Colors.WHITE, pos, 18)
            pygame.draw.circle(self.screen, closest_color, pos, 12)
            pygame.draw.circle(self.screen, Colors.BLACK, pos, 4)