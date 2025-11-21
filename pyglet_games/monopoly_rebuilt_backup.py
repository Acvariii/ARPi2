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
        
        # Universal popup system
        self.popup = UniversalPopup()
        self.property_scroll = 0
        
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
            panel = self.panels[idx]
            button_rects = panel.get_button_layout()
            orient = panel.orientation
            
            self.buttons[idx] = {
                "action": PygletButton(button_rects[0], "Roll", orient),
                "props": PygletButton(button_rects[1], "Props", orient),
                "build": PygletButton(button_rects[2], "Build", orient)
            }
    
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
        
        current_time = time.time()
        current_player = self.players[self.active_players[self.current_player_idx]]
        
        # Handle popup buttons first
        if self.popup.active:
            callback = self.popup.check_button_click(fingertips, current_time, HOVER_TIME_THRESHOLD)
            if callback:
                self._handle_popup_callback(callback)
            return False
        
        for idx in self.active_players:
            if idx not in self.buttons:
                continue
            
            player = self.players[idx]
            is_current = (idx == self.active_players[self.current_player_idx])
            
            # Update button states - only current player can interact
            btns = self.buttons[idx]
            btns["action"].enabled = is_current and not self.dice_rolling and not self.popup.active
            btns["action"].text = "Roll" if self.can_roll else "End"
            btns["props"].enabled = is_current and len(player.properties) > 0 and not self.popup.active
            btns["build"].enabled = is_current and len(player.properties) > 0 and not self.popup.active
            
            # Only check clicks for current player
            if is_current:
                for name, btn in btns.items():
                    clicked, _ = btn.update(fingertips, current_time)
                    if clicked:
                        self._handle_click(idx, name)
        
        return False
    
    def _handle_click(self, player_idx: int, button: str):
        """Handle button click"""
        if button == "action":
            if self.can_roll:
                self.roll_dice()
            else:
                self.advance_turn()
        elif button == "props":
            player = self.players[player_idx]
            self._show_properties_popup(player)
        elif button == "build":
            player = self.players[player_idx]
            self._show_build_popup(player)
    
    def _handle_popup_callback(self, callback: str):
        """Handle popup button callbacks"""
        if callback == "buy":
            player = self.popup.data["player"]
            position = self.popup.data["position"]
            self._buy_property(player, position)
        
        elif callback == "pass":
            self.popup.hide()
            self._finish_turn_or_allow_double()
        
        elif callback == "ok":
            self.popup.hide()
            self._finish_turn_or_allow_double()
        
        elif callback == "close":
            self.popup.hide()
    
    def roll_dice(self):
        """Roll dice"""
        if not self.can_roll or self.dice_rolling:
            return
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
        self.dice_values = (0, 0)
    
    def update(self, dt: float):
        """Update game state"""
        if self.dice_rolling:
            elapsed = time.time() - self.dice_roll_start
            if elapsed >= 1.2:
                self.dice_rolling = False
                self.dice_values = (random.randint(1, 6), random.randint(1, 6))
                
                current = self.players[self.active_players[self.current_player_idx]]
                is_doubles = self.dice_values[0] == self.dice_values[1]
                
                if is_doubles:
                    current.consecutive_doubles += 1
                    if current.consecutive_doubles >= 3:
                        current.position = JAIL_POSITION
                        current.in_jail = True
                        self.can_roll = False
                        return
                else:
                    current.consecutive_doubles = 0
                
                # Move player
                spaces = sum(self.dice_values)
                old_pos = current.position
                current.position = (current.position + spaces) % 40
                
                if current.position < old_pos:
                    current.add_money(PASSING_GO_MONEY)
                
                self._land_on_space(current)
    
    def _show_buy_prompt(self, player: Player, position: int):
        """Show buy property dialog"""
        space = self.properties[position]
        price = space.data.get("price", 0)
        panel = self.panels[player.idx]
        
        grid = create_monopoly_buy_popup(
            player.money,
            space.data.get("name", ""),
            price,
            panel.orientation
        )
        
        self.popup.show(
            player.idx,
            panel.rect,
            panel.orientation,
            "buy_prompt",
            grid,
            {"player": player, "position": position, "price": price, "space": space}
        )
    
    def _show_card_popup(self, player: Player, card: Dict, deck_type: str):
        """Show card dialog"""
        panel = self.panels[player.idx]
        
        grid = create_monopoly_card_popup(
            card.get("text", ""),
            deck_type,
            panel.orientation
        )
        
        self.popup.show(
            player.idx,
            panel.rect,
            panel.orientation,
            "card",
            grid,
            {"player": player, "card": card, "deck_type": deck_type}
        )
    
    def _show_properties_popup(self, player: Player):
        """Show properties list dialog"""
        panel = self.panels[player.idx]
        
        # Get property names
        prop_names = [self.properties[idx].data.get("name", "") for idx in player.properties]
        
        grid = create_monopoly_properties_popup(
            prop_names,
            panel.orientation
        )
        
        self.popup.show(
            player.idx,
            panel.rect,
            panel.orientation,
            "properties",
            grid,
            {"player": player}
        )
    
    def _show_build_popup(self, player: Player):
        """Show build menu dialog"""
        panel = self.panels[player.idx]
        
        grid = create_info_popup(
            "Building",
            "Coming soon",
            panel.orientation,
            "Close"
        )
        
        self.popup.show(
            player.idx,
            panel.rect,
            panel.orientation,
            "build",
            grid,
            {"player": player}
        )
    
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
                self._finish_turn_or_allow_double()
        
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
            player.remove_money(INCOME_TAX)
            self._finish_turn_or_allow_double()
        
        elif space_type == "luxury_tax":
            player.remove_money(LUXURY_TAX)
            self._finish_turn_or_allow_double()
        
        else:
            self._finish_turn_or_allow_double()
        
        if player.money < 0:
            self._handle_bankruptcy(player)
    
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
        self._finish_turn_or_allow_double()
    
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
    
    def _handle_bankruptcy(self, player: Player, owed_to: Optional[Player] = None):
        """Handle player bankruptcy"""
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
        
        # Remove from active players
        if player.idx in self.active_players:
            idx_pos = self.active_players.index(player.idx)
            self.active_players.remove(player.idx)
            if self.current_player_idx >= len(self.active_players):
                self.current_player_idx = 0
    
    def _execute_card_action(self, player: Player, card: Dict):
        """Execute card action"""
        action = card.get("action")
        if not action:
            return
        
        action_type = action[0]
        
        if action_type == "advance_to":
            position = action[1]
            old_pos = player.position
            player.position = position
            if position < old_pos:
                player.add_money(PASSING_GO_MONEY)
        
        elif action_type == "advance_spaces":
            spaces = action[1]
            old_pos = player.position
            player.position = (player.position + spaces) % 40
            if player.position < old_pos:
                player.add_money(PASSING_GO_MONEY)
        
        elif action_type == "collect":
            amount = action[1]
            player.add_money(amount)
        
        elif action_type == "pay":
            amount = action[1]
            player.remove_money(amount)
        
        elif action_type == "go_to_jail":
            self._send_to_jail(player)
        
        elif action_type == "get_out_of_jail_free":
            player.get_out_of_jail_free_cards += 1
        
        elif action_type == "advance_nearest":
            target_type = action[1]
            current_pos = player.position
            
            if target_type == "railroad":
                railroad_positions = [5, 15, 25, 35]
                nearest = min(railroad_positions, 
                             key=lambda p: (p - current_pos) % 40)
            else:
                utility_positions = [12, 28]
                nearest = min(utility_positions,
                             key=lambda p: (p - current_pos) % 40)
            
            old_pos = player.position
            player.position = nearest
            if nearest < old_pos:
                player.add_money(PASSING_GO_MONEY)
        
        elif action_type == "collect_from_each":
            amount = action[1]
            for other_idx in self.active_players:
                if other_idx != player.idx:
                    other = self.players[other_idx]
                    transfer = min(amount, other.money)
                    other.remove_money(transfer)
                    player.add_money(transfer)
        
        elif action_type == "pay_each_player":
            amount = action[1]
            for other_idx in self.active_players:
                if other_idx != player.idx:
                    other = self.players[other_idx]
                    payment = min(amount, player.money)
                    player.remove_money(payment)
                    other.add_money(payment)
        
        elif action_type == "pay_per_house_hotel":
            house_cost, hotel_cost = action[1]
            total_cost = 0
            for prop_idx in player.properties:
                prop = self.properties[prop_idx]
                if prop.houses == 5:
                    total_cost += hotel_cost
                else:
                    total_cost += prop.houses * house_cost
            player.remove_money(total_cost)
    
    def draw(self):
        """Draw game"""
        if self.state == "player_select":
            self._draw_player_select()
            return
        
        # Background
        self.renderer.draw_rect((32, 96, 36), (0, 0, self.width, self.height))
        
        # Panels
        self._draw_panels()
        
        # Board
        self._draw_board()
        
        # Tokens
        self._draw_tokens()
        
        # Dice - show during roll animation or when values are set
        if self.dice_rolling or self.dice_values != (0, 0):
            self._draw_dice()
        
        # Popups
        if self.popup.active:
            self._draw_popup()
        
        # Hover indicators on top
        self._draw_hover_indicators()
    
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
            
            # Buttons (draw only, input handled in handle_input)
            if idx in self.buttons:
                current_time = time.time()
                for btn in self.buttons[idx].values():
                    # Calculate progress for visual feedback
                    progress = 0.0
                    if btn.hovering and btn.hover_start > 0:
                        progress = min(1.0, (current_time - btn.hover_start) / HOVER_TIME_THRESHOLD)
                    btn.draw(self.renderer, progress)
    
    def _draw_panel_info(self, player: Player, panel: PlayerPanel):
        """Draw player info with proper orientation using grid system"""
        # For vertical panels (left/right), place text in INFO area (30% on FAR side)
        if panel.orientation in [90, 270]:
            # Left panel (270): info on RIGHT side (far from player), buttons on LEFT
            # Right panel (90): info on LEFT side (far from player), buttons on RIGHT
            if panel.orientation == 270:  # Left panel - info on right side
                x_pos = 0.85  # Right side (far from left player)
            else:  # Right panel (90) - info on left side
                x_pos = 0.15  # Left side (far from right player)
            
            # Place at top of panel from player's perspective
            panel.draw_text_oriented(
                self.renderer, f"${player.money}",
                x_pos, 0.90, 16, (255, 255, 100)
            )
            if player.properties:
                panel.draw_text_oriented(
                    self.renderer, f"{len(player.properties)} props",
                    x_pos, 0.80, 11, (200, 200, 200)
                )
        else:
            # Horizontal panels - normal positioning
            panel.draw_text_oriented(
                self.renderer, f"${player.money}",
                0.5, 0.25, 20, (255, 255, 100)
            )
            if player.properties:
                panel.draw_text_oriented(
                    self.renderer, f"{len(player.properties)} props",
                    0.5, 0.12, 14, (200, 200, 200)
                )
    
    def _draw_board(self):
        """Draw monopoly board with property colors and names"""
        bx, by, bw, bh = self.board_rect
        
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
            
            # Draw space name - NO ROTATION, always readable from bottom
            name = space_data.get("name", "")
            if name:
                cx, cy = sx + sw // 2, sy + sh // 2
                # Shorten name if too long
                if len(name) > 12:
                    name = name[:9] + "..."
                
                font_size = 8 if space_type in ["property", "railroad", "utility"] else 7
                self.renderer.draw_text(
                    name, cx, cy,
                    'Arial', font_size, (0, 0, 0),
                    anchor_x='center', anchor_y='center',
                    rotation=0  # Always horizontal for readability
                )
            
            # Border
            self.renderer.draw_rect((80, 80, 80), (sx, sy, sw, sh), width=1)
    
    def _draw_tokens(self):
        """Draw player tokens"""
        for idx in self.active_players:
            player = self.players[idx]
            if player.is_bankrupt:
                continue
            
            sx, sy, sw, sh = self.spaces[player.position]
            cx, cy = sx + sw // 2, sy + sh // 2
            
            # Offset for multiple players
            offset_idx = self.active_players.index(idx)
            num_players = len(self.active_players)
            if num_players > 1:
                angle = (offset_idx / num_players) * 6.28
                offset = 15
                cx += int(offset * (0.5 - abs(0.5 - offset_idx / num_players)))
            
            # Draw token
            color = PLAYER_COLORS[idx]
            self.renderer.draw_circle(color, (cx, cy), 12)
            self.renderer.draw_circle((0, 0, 0), (cx, cy), 12, width=2)
    
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
        """Draw active popup with screen dimming"""
        if not self.popup.active:
            return
        
        # Dim entire screen
        self.renderer.draw_rect((0, 0, 0, 160), (0, 0, self.width, self.height))
        
        # Draw popup using UniversalPopup system
        self.popup.draw(self.renderer)
    
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
