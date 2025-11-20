import time
import random
import pygame
from typing import List, Dict, Tuple, Optional, Callable

from config import PLAYER_COLORS, Colors
from monopoly_data import (
    BOARD_SPACES, PROPERTY_GROUPS, STARTING_MONEY, PASSING_GO_MONEY,
    LUXURY_TAX, INCOME_TAX, JAIL_POSITION, GO_TO_JAIL_POSITION,
    JAIL_FINE, MAX_JAIL_TURNS
)
from constants import COMMUNITY_CHEST_CARDS, CHANCE_CARDS
from player_panel import calculate_all_panels
from ui_components import HoverButton

from monopoly2.property import Property
from monopoly2.player import Player
from monopoly2.game_logic import GameLogic
from monopoly2.drawing import BoardDrawer, TokenDrawer, DiceDrawer
from monopoly2.popups import PopupDrawer


class MonopolyGame:
    
    def __init__(self, screen: pygame.Surface, fingertip_callback: Callable):
        self.screen = screen
        self.get_fingertips = fingertip_callback
        self.screen_size = screen.get_size()
        
        self.properties = [Property(data) if data else Property({"name": "", "type": "none"}) 
                          for data in BOARD_SPACES]
        self.players = [Player(i, PLAYER_COLORS[i]) for i in range(8)]
        self.active_players: List[int] = []
        self.current_player_idx = 0
        
        self.community_chest_deck = list(COMMUNITY_CHEST_CARDS)
        self.chance_deck = list(CHANCE_CARDS)
        random.shuffle(self.community_chest_deck)
        random.shuffle(self.chance_deck)
        
        self.panels = calculate_all_panels(self.screen_size)
        self.buttons: Dict[int, Dict[str, HoverButton]] = {}
        
        self.phase = "roll"
        self.can_roll = True
        self.dice_values = (0, 0)
        self.dice_rolling = False
        self.dice_roll_start = 0.0
        self.dice_roll_duration = 1.2
        
        self.active_popup: Optional[str] = None
        self.popup_data: Dict = {}
        self.popup_buttons: List[HoverButton] = []
        self.property_scroll = 0
        
        self._calculate_board_geometry()
        
        self.board_drawer = BoardDrawer(self.screen, self.board_rect, self.space_positions)
        self.token_drawer = TokenDrawer(self.screen, self.space_positions)
        self.dice_drawer = DiceDrawer(self.screen, self.board_rect)
        self.popup_drawer = PopupDrawer(self.screen)
        
        self._init_buttons()
    
    def _calculate_board_geometry(self):
        w, h = self.screen_size
        
        horizontal_panel_height = int(h * 0.10)
        vertical_panel_width = int(w * 0.12)
        
        margin = 20
        available_width = w - (2 * vertical_panel_width) - (2 * margin)
        available_height = h - (2 * horizontal_panel_height) - (2 * margin)
        
        board_size = min(available_width, available_height)
        
        board_x = vertical_panel_width + margin + (available_width - board_size) // 2
        board_y = horizontal_panel_height + margin + (available_height - board_size) // 2
        
        self.board_rect = pygame.Rect(board_x, board_y, board_size, board_size)
        self.space_positions = self._calculate_space_positions()
    
    def _calculate_space_positions(self) -> List[Tuple[int, int, int, int]]:
        positions = []
        board_x = self.board_rect.x
        board_y = self.board_rect.y
        board_size = self.board_rect.width
        
        space_size = board_size // 11
        
        for i in range(11):
            x = board_x + board_size - ((i + 1) * space_size)
            y = board_y + board_size - space_size
            positions.append((x, y, space_size, space_size))
        
        for i in range(1, 10):
            x = board_x
            y = board_y + board_size - ((i + 1) * space_size)
            positions.append((x, y, space_size, space_size))
        
        for i in range(11):
            x = board_x + (i * space_size)
            y = board_y
            positions.append((x, y, space_size, space_size))
        
        for i in range(1, 10):
            x = board_x + board_size - space_size
            y = board_y + (i * space_size)
            positions.append((x, y, space_size, space_size))
        
        return positions
    
    def _init_buttons(self):
        font = pygame.font.SysFont(None, 26)
        for idx in range(8):
            panel = self.panels[idx]
            margin = 10
            gap = 8
            
            if panel.orientation == 0:
                info_height_frac = 0.45
                button_area_height = int(panel.rect.height * (1 - info_height_frac))
                y = panel.rect.y + panel.rect.height - button_area_height
                x = panel.rect.x + margin
                avail_w = panel.rect.width - 2 * margin
                btn_w = (avail_w - 2 * gap) // 3
                btn_h = button_area_height - 2 * margin
                r_roll = pygame.Rect(x, y + margin, btn_w, btn_h)
                r_props = pygame.Rect(x + btn_w + gap, y + margin, btn_w, btn_h)
                r_build = pygame.Rect(x + 2 * (btn_w + gap), y + margin, btn_w, btn_h)
            
            elif panel.orientation == 180:
                info_height_frac = 0.45
                button_area_height = int(panel.rect.height * (1 - info_height_frac))
                info_area_height = int(panel.rect.height * info_height_frac)
                y = panel.rect.y + info_area_height
                x = panel.rect.x + margin
                avail_w = panel.rect.width - 2 * margin
                btn_w = (avail_w - 2 * gap) // 3
                btn_h = button_area_height - 2 * margin
                r_roll = pygame.Rect(x, y + margin, btn_w, btn_h)
                r_props = pygame.Rect(x + btn_w + gap, y + margin, btn_w, btn_h)
                r_build = pygame.Rect(x + 2 * (btn_w + gap), y + margin, btn_w, btn_h)
            
            elif panel.orientation == 90:
                info_width_frac = 0.35
                button_area_width = int(panel.rect.width * (1 - info_width_frac))
                x = panel.rect.x
                y = panel.rect.y + margin
                avail_h = panel.rect.height - 2 * margin
                btn_h = (avail_h - 2 * gap) // 3
                btn_w = button_area_width - 2 * margin
                r_roll = pygame.Rect(x + margin, y, btn_w, btn_h)
                r_props = pygame.Rect(x + margin, y + btn_h + gap, btn_w, btn_h)
                r_build = pygame.Rect(x + margin, y + 2 * (btn_h + gap), btn_w, btn_h)
            
            else:
                info_width_frac = 0.35
                button_area_width = int(panel.rect.width * (1 - info_width_frac))
                info_area_width = int(panel.rect.width * info_width_frac)
                x = panel.rect.x + info_area_width
                y = panel.rect.y + margin
                avail_h = panel.rect.height - 2 * margin
                btn_h = (avail_h - 2 * gap) // 3
                btn_w = button_area_width - 2 * margin
                r_roll = pygame.Rect(x + margin, y, btn_w, btn_h)
                r_props = pygame.Rect(x + margin, y + btn_h + gap, btn_w, btn_h)
                r_build = pygame.Rect(x + margin, y + 2 * (btn_h + gap), btn_w, btn_h)
            
            self.buttons[idx] = {
                "action": HoverButton(r_roll, "Roll", font, orientation=panel.orientation),
                "props": HoverButton(r_props, "Props", font, orientation=panel.orientation),
                "build": HoverButton(r_build, "Build", font, orientation=panel.orientation)
            }

    def _popup_button_column(self, panel, count: int, small: bool = False) -> list:
        margin = 8
        gap = 10
        
        if panel.orientation == 0:
            col_w = int(panel.rect.width * 0.28)
            col_h = panel.rect.height - 2 * margin
            x = panel.rect.x + margin
            y = panel.rect.y + margin
            btn_h = (col_h - (count - 1) * gap) // count
            btn_w = col_w
            rects = [pygame.Rect(x, y + i * (btn_h + gap), btn_w, btn_h) for i in range(count)]
        elif panel.orientation == 180:
            col_w = int(panel.rect.width * 0.28)
            col_h = panel.rect.height - 2 * margin
            x = panel.rect.x + margin
            y_bottom = panel.rect.bottom - margin
            btn_h = (col_h - (count - 1) * gap) // count
            btn_w = col_w
            rects = [pygame.Rect(x, y_bottom - (i + 1) * btn_h - i * gap, btn_w, btn_h) for i in range(count)]
        elif panel.orientation == 90:
            col_h = int(panel.rect.height * 0.28)
            col_w = panel.rect.width - 2 * margin
            y = panel.rect.y + margin
            x = panel.rect.x + margin
            btn_w = (col_w - (count - 1) * gap) // count
            btn_h = col_h
            rects = [pygame.Rect(x + i * (btn_w + gap), y, btn_w, btn_h) for i in range(count)]
        else:
            col_h = int(panel.rect.height * 0.28)
            col_w = panel.rect.width - 2 * margin
            y = panel.rect.y + margin
            x_right = panel.rect.right - margin
            btn_w = (col_w - (count - 1) * gap) // count
            btn_h = col_h
            rects = [pygame.Rect(x_right - (i + 1) * btn_w - i * gap, y, btn_w, btn_h) for i in range(count)]
        
        if small:
            for r in rects:
                if panel.is_vertical():
                    r.height = int(r.height * 0.7)
                else:
                    r.height = int(r.height * 0.7)
        
        return rects

    def _show_buy_prompt(self, player: Player, position: int):
        space = self.properties[position]
        price = space.data.get("price", 0)
        self.active_popup = "buy_prompt"
        self.popup_data = {"player": player, "position": position, "price": price, "space": space}
        panel = self.panels[player.idx]
        font = pygame.font.SysFont(None, 24)
        rects = self._popup_button_column(panel, 2)
        self.popup_buttons = [
            HoverButton(rects[0], "Buy", font, orientation=panel.orientation),
            HoverButton(rects[1], "Pass", font, orientation=panel.orientation)
        ]

    def _show_card_popup(self, player: Player, card: Dict, deck_type: str):
        self.active_popup = "card"
        self.popup_data = {"player": player, "card": card, "deck_type": deck_type}
        panel = self.panels[player.idx]
        font = pygame.font.SysFont(None, 22)
        rects = self._popup_button_column(panel, 1, small=True)
        self.popup_buttons = [
            HoverButton(rects[0], "OK", font, orientation=panel.orientation)
        ]

    def _show_properties_popup(self, player: Player):
        self.active_popup = "properties"
        self.popup_data = {"player": player}
        self.property_scroll = 0
        panel = self.panels[player.idx]
        font = pygame.font.SysFont(None, 22)
        rects = self._popup_button_column(panel, 3, small=True)
        self.popup_buttons = [
            HoverButton(rects[0], "◀", font, orientation=panel.orientation),
            HoverButton(rects[1], "▶", font, orientation=panel.orientation),
            HoverButton(rects[2], "✕", font, orientation=panel.orientation)
        ]

    def _show_build_popup(self, player: Player):
        self.active_popup = "build"
        self.popup_data = {"player": player}
        panel = self.panels[player.idx]
        font = pygame.font.SysFont(None, 22)
        rects = self._popup_button_column(panel, 1, small=True)
        self.popup_buttons = [
            HoverButton(rects[0], "✕ Close", font, orientation=panel.orientation)
        ]
    
    def _buy_property(self, player: Player, position: int):
        space = self.properties[position]
        price = space.data.get("price", 0)
        
        if player.remove_money(price):
            space.owner = player.idx
            player.properties.append(position)
        
        self.active_popup = None
        self.popup_buttons = []
        self._finish_turn_or_allow_double()
    
    def _pay_rent(self, player: Player, position: int):
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
        GameLogic.send_to_jail(player)
    
    def _handle_bankruptcy(self, player: Player, owed_to: Optional[Player] = None):
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
    
    def _execute_card_action(self, player: Player, card: Dict):
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
        
        elif action_type == "advance":
            target_position = action[1]
            collect_go = action[2] if len(action) > 2 else False
            
            if target_position >= player.position:
                spaces = target_position - player.position
            else:
                spaces = (40 - player.position) + target_position
            
            self.move_player(player, spaces)
            
            if collect_go and target_position < player.position:
                player.add_money(PASSING_GO_MONEY)
        
        elif action_type == "advance_relative":
            spaces = action[1]
            self.move_player(player, spaces)
        
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
            
            if nearest >= current_pos:
                spaces = nearest - current_pos
            else:
                spaces = (40 - current_pos) + nearest
            
            self.move_player(player, spaces)
        
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
    
    def update(self, fingertip_meta: List[Dict]):
        current_player = self.get_current_player()
        
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
        
        if current_player.is_moving:
            elapsed = time.time() - current_player.move_start
            move_duration = 0.3 * len(current_player.move_path)
            
            if elapsed >= move_duration:
                current_player.is_moving = False
                current_player.position = current_player.move_path[-1]
                current_player.move_path = []
                self.land_on_space(current_player)
        
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
                        btn.text = "Roll" if self.can_roll else "End Turn"
                elif btn_name in ("props", "build"):
                    enabled = is_current and not current_player.is_moving and self.active_popup is None
                
                if btn.update(fingertip_meta, enabled):
                    self._handle_button_click(player_idx, btn_name)
                    btn.reset()
        
        if self.active_popup:
            for i, btn in enumerate(self.popup_buttons):
                if btn.update(fingertip_meta):
                    self._handle_popup_button(i)
                    btn.reset()
    
    def _handle_button_click(self, player_idx: int, button_name: str):
        player = self.players[player_idx]
        
        if button_name == "action":
            if self.phase == "roll" and self.can_roll and not self.dice_rolling:
                self.roll_dice()
            elif self.phase == "roll" and not self.can_roll:
                self.advance_turn()
        
        elif button_name == "props":
            self._show_properties_popup(player)
        
        elif button_name == "build":
            self._show_build_popup(player)
    
    def _handle_popup_button(self, button_idx: int):
        if self.active_popup == "buy_prompt":
            player = self.popup_data["player"]
            position = self.popup_data["position"]
            
            if button_idx == 0:
                self._buy_property(player, position)
            else:
                self.active_popup = None
                self.popup_buttons = []
                self._finish_turn_or_allow_double()
        
        elif self.active_popup == "card":
            self.active_popup = None
            self.popup_buttons = []
            if not self.get_current_player().is_moving:
                self._finish_turn_or_allow_double()
        
        elif self.active_popup == "properties":
            player = self.popup_data["player"]
            
            if button_idx == 0:
                if player.properties:
                    self.property_scroll = (self.property_scroll - 1) % len(player.properties)
            elif button_idx == 1:
                if player.properties:
                    self.property_scroll = (self.property_scroll + 1) % len(player.properties)
            else:
                self.active_popup = None
                self.popup_buttons = []
        
        elif self.active_popup == "build":
            self.active_popup = None
            self.popup_buttons = []
    
    def draw(self):
        self.screen.fill((32, 96, 36))
        
        self._draw_all_panels()
        
        self.board_drawer.draw_board()
        
        for i in range(40):
            self.board_drawer.draw_space(i, self.properties[i].data)
            if self.properties[i].houses > 0:
                self.board_drawer.draw_houses(i, self.properties[i].houses)
        
        self.token_drawer.draw_tokens(
            [self.players[i] for i in self.active_players],
            lambda p: p.is_moving,
            self._get_animated_token_pos
        )
        
        if self.dice_rolling or self.dice_values != (0, 0):
            self.dice_drawer.draw_dice(self.dice_rolling, self.dice_values)
        
        if self.active_popup:
            self._draw_popup()
        
        self._draw_cursors()
    
    def _draw_all_panels(self):
        from ui_components import RotatedText
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
                font = pygame.font.SysFont("Arial", 18, bold=True)
                
                if panel.orientation == 0:
                    info_rect = pygame.Rect(
                        panel.rect.x + 10,
                        panel.rect.y + 10,
                        panel.rect.width - 20,
                        int(panel.rect.height * 0.35)
                    )
                    RotatedText.draw(self.screen,
                                     f"${player.money} | {len(player.properties)}p",
                                     font, Colors.BLACK,
                                     info_rect.center,
                                     panel.orientation)
                elif panel.orientation == 180:
                    info_height = int(panel.rect.height * 0.45)
                    info_rect = pygame.Rect(
                        panel.rect.x + 10,
                        panel.rect.y + 10,
                        panel.rect.width - 20,
                        info_height - 20
                    )
                    RotatedText.draw(self.screen,
                                     f"${player.money} | {len(player.properties)}p",
                                     font, Colors.BLACK,
                                     info_rect.center,
                                     panel.orientation)
                elif panel.orientation == 90:
                    info_width_frac = 0.35
                    button_area_width = int(panel.rect.width * (1 - info_width_frac))
                    info_width = int(panel.rect.width * info_width_frac)
                    info_rect = pygame.Rect(
                        panel.rect.x + button_area_width,
                        panel.rect.y + 10,
                        info_width - 10,
                        panel.rect.height - 20
                    )
                    RotatedText.draw_block(
                        self.screen,
                        [(f"${player.money}", font, Colors.BLACK),
                         (f"{len(player.properties)}p", font, Colors.BLACK)],
                        info_rect,
                        panel.orientation,
                        line_spacing=12
                    )
                else:
                    info_width = int(panel.rect.width * 0.35)
                    info_rect = pygame.Rect(
                        panel.rect.x + 10,
                        panel.rect.y + 10,
                        info_width - 10,
                        panel.rect.height - 20
                    )
                    RotatedText.draw_block(
                        self.screen,
                        [(f"${player.money}", font, Colors.BLACK),
                         (f"{len(player.properties)}p", font, Colors.BLACK)],
                        info_rect,
                        panel.orientation,
                        line_spacing=12
                    )
                
                for btn in self.buttons[idx].values():
                    btn.draw(self.screen)
            else:
                font = pygame.font.SysFont("Arial", 36, bold=True)
                label = f"P{idx + 1}"
                text_surf = font.render(label, True, (100, 100, 100))
                if panel.orientation != 0:
                    text_surf = pygame.transform.rotate(text_surf, panel.orientation)
                text_rect = text_surf.get_rect(center=panel.rect.center)
                self.screen.blit(text_surf, text_rect)
    
    def _get_animated_token_pos(self, player: Player) -> Tuple[int, int]:
        elapsed = time.time() - player.move_start
        move_duration = 0.3 * len(player.move_path)
        progress = min(1.0, elapsed / move_duration)
        
        path_progress = progress * len(player.move_path)
        path_idx = int(path_progress)
        path_frac = path_progress - path_idx
        
        if path_idx >= len(player.move_path):
            pos = player.move_path[-1]
        else:
            current_space = player.move_path[path_idx]
            next_space = player.move_path[path_idx + 1] if path_idx + 1 < len(player.move_path) else current_space
            
            x1, y1, w1, h1 = self.space_positions[current_space]
            x2, y2, w2, h2 = self.space_positions[next_space]
            
            cx1, cy1 = x1 + w1 // 2, y1 + h1 // 2
            cx2, cy2 = x2 + w2 // 2, y2 + h2 // 2
            
            x = int(cx1 + (cx2 - cx1) * path_frac)
            y = int(cy1 + (cy2 - cy1) * path_frac)
            return (x, y)
        
        x, y, w, h = self.space_positions[pos]
        return (x + w // 2, y + h // 2)
    
    def _draw_popup(self):
        player = self.popup_data.get("player")
        if not player:
            return
        
        panel = self.panels[player.idx]
        
        if self.active_popup == "buy_prompt":
            self.popup_drawer.draw_buy_prompt(self.popup_data, panel, self.popup_buttons)
        elif self.active_popup == "card":
            self.popup_drawer.draw_card_popup(self.popup_data, panel, self.popup_buttons)
        elif self.active_popup == "properties":
            self.popup_drawer.draw_properties_popup(
                self.popup_data, panel, self.properties, 
                self.property_scroll, self.popup_buttons
            )
        elif self.active_popup == "build":
            self.popup_drawer.draw_build_popup(panel, self.popup_buttons)
    
    def _draw_cursors(self):
        from ui_components import draw_cursor
        import math
        
        fingertips = self.get_fingertips(*self.screen_size)
        for meta in fingertips:
            pos = meta["pos"]
            
            min_dist = float('inf')
            closest_color = Colors.WHITE
            
            for idx in self.active_players:
                panel = self.panels[idx]
                center = panel.rect.center
                dist = math.sqrt((pos[0] - center[0])**2 + (pos[1] - center[1])**2)
                if dist < min_dist:
                    min_dist = dist
                    closest_color = panel.color
            
            draw_cursor(self.screen, pos, closest_color)
    
    def start_game(self, player_indices: List[int]):
        self.active_players = sorted(player_indices)
        self.current_player_idx = 0

        for i in self.active_players:
            p = self.players[i]
            p.money = STARTING_MONEY
            p.position = 0
            p.properties = []
            p.in_jail = False
            p.jail_turns = 0
            p.get_out_of_jail_cards = 0
            p.consecutive_doubles = 0
            p.is_bankrupt = False
            p.move_path = []
            p.move_start = 0.0
            p.move_from = 0
            p.is_moving = False

        self.phase = "roll"
        self.can_roll = True
        self.dice_values = (0, 0)
        self.dice_rolling = False
        self.active_popup = None
        self.popup_data = {}
        self.popup_buttons = []
        self.property_scroll = 0

    def get_current_player(self) -> "Player":
        return self.players[self.active_players[self.current_player_idx]]
    
    def roll_dice(self):
        if not self.can_roll or self.dice_rolling:
            return
        self.dice_rolling = True
        self.dice_roll_start = time.time()
        self.can_roll = False

    def move_player(self, player: "Player", spaces: int):
        GameLogic.move_player(player, spaces)
        self.phase = "moving"

    def land_on_space(self, player: "Player"):
        if GameLogic.check_passed_go(player):
            player.add_money(PASSING_GO_MONEY)

        position = player.position
        space = self.properties[position]
        space_type = space.data.get("type")

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
        current = self.get_current_player()
        if current.consecutive_doubles > 0:
            self.phase = "roll"
            self.can_roll = True
        else:
            self.advance_turn()

    def advance_turn(self):
        if not self.active_players:
            return

        player = self.get_current_player()
        player.consecutive_doubles = 0

        original_idx = self.current_player_idx
        while True:
            self.current_player_idx = (self.current_player_idx + 1) % len(self.active_players)
            next_player = self.get_current_player()
            if not next_player.is_bankrupt or self.current_player_idx == original_idx:
                break

        self.phase = "roll"
        self.can_roll = True
        self.dice_values = (0, 0)
        self.dice_rolling = False
