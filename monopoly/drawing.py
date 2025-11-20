import pygame
import math
import random
from typing import List, Tuple, Dict
from config import Colors
from ui_components import RotatedText, draw_circular_progress


class BoardDrawer:
    
    def __init__(self, screen: pygame.Surface, board_rect: pygame.Rect, 
                 space_positions: List[Tuple[int, int, int, int]]):
        self.screen = screen
        self.board_rect = board_rect
        self.space_positions = space_positions
    
    def draw_board(self):
        pygame.draw.rect(self.screen, (220, 240, 220), self.board_rect)
        pygame.draw.rect(self.screen, Colors.BLACK, self.board_rect, 3)
        
        space_size = self.space_positions[0][2]
        center_size = space_size * 9
        center_x = self.board_rect.x + space_size
        center_y = self.board_rect.y + space_size
        center_rect = pygame.Rect(center_x, center_y, center_size, center_size)
        pygame.draw.rect(self.screen, (240, 250, 240), center_rect)
        pygame.draw.rect(self.screen, Colors.BLACK, center_rect, 2)
        
        font = pygame.font.SysFont(None, int(center_size * 0.12), bold=True)
        text = font.render("MONOPOLY", True, (180, 40, 40))
        text_rect = text.get_rect(center=center_rect.center)
        self.screen.blit(text, text_rect)
    
    def draw_space(self, idx: int, space_data: Dict):
        if idx >= len(self.space_positions):
            return
            
        if space_data.get("type") == "none":
            return
        
        x, y, w, h = self.space_positions[idx]
        rect = pygame.Rect(x, y, w, h)
        
        space_type = space_data.get("type")
        if space_type in ("property", "railroad", "utility"):
            color = space_data.get("color", (200, 200, 200))
            strip_height = h // 4
            
            strip_rect = pygame.Rect(rect.x, rect.y, rect.width, strip_height)
            pygame.draw.rect(self.screen, color, strip_rect)
            
            shadow_rect = pygame.Rect(rect.x, rect.y + strip_height, rect.width, 2)
            shadow_color = tuple(max(0, c - 40) for c in color)
            pygame.draw.rect(self.screen, shadow_color, shadow_rect)
            
            main_rect = pygame.Rect(rect.x, rect.y + strip_height, rect.width, rect.height - strip_height)
            pygame.draw.rect(self.screen, (248, 248, 248), main_rect)
            
            pygame.draw.rect(self.screen, (50, 50, 50), rect, 1)
        else:
            bg_color = (245, 245, 240)
            pygame.draw.rect(self.screen, bg_color, rect)
            pygame.draw.rect(self.screen, (80, 80, 80), rect, 1)
        
        name = space_data.get("name", "")
        if name:
            font_size = max(8, min(12, w // 5))
            font = pygame.font.SysFont("Arial", font_size, bold=False)
            
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
            
            line_height = font.get_linesize()
            center_x = x + w // 2
            
            if space_type in ("property", "railroad", "utility"):
                available_height = h - (h // 4)
                center_y = y + (h // 4) + available_height // 2
            else:
                center_y = y + h // 2
            
            start_y = center_y - (len(lines[:3]) * line_height) // 2
            
            for i, line in enumerate(lines[:3]):
                text_surf = font.render(line, True, (40, 40, 40))
                text_rect = text_surf.get_rect(center=(center_x, start_y + i * line_height))
                self.screen.blit(text_surf, text_rect)
    
    def draw_houses(self, idx: int, houses: int):
        if idx >= len(self.space_positions) or houses <= 0:
            return
        
        x, y, w, h = self.space_positions[idx]
        house_size = max(4, w // 8)
        num_houses = min(houses, 4)
        spacing = 2
        total_width = num_houses * house_size + (num_houses - 1) * spacing
        start_x = x + (w - total_width) // 2
        
        for h_idx in range(num_houses):
            house_x = start_x + h_idx * (house_size + spacing)
            house_y = y + 3
            house_rect = pygame.Rect(house_x, house_y, house_size, house_size)
            
            if houses == 5:
                pygame.draw.rect(self.screen, (220, 40, 40), house_rect, border_radius=2)
            else:
                pygame.draw.rect(self.screen, (60, 180, 60), house_rect, border_radius=2)
            
            pygame.draw.rect(self.screen, (30, 30, 30), house_rect, 1, border_radius=2)


class TokenDrawer:
    
    def __init__(self, screen: pygame.Surface, space_positions: List[Tuple[int, int, int, int]]):
        self.screen = screen
        self.space_positions = space_positions
    
    def get_space_center(self, space_idx: int) -> Tuple[int, int]:
        if space_idx >= len(self.space_positions):
            return (0, 0)
        x, y, w, h = self.space_positions[space_idx]
        return (x + w // 2, y + h // 2)
    
    def draw_tokens(self, active_players: List, is_moving_func, get_animated_pos_func):
        positions: Dict[int, List] = {}
        
        for player in active_players:
            if player.is_bankrupt:
                continue
            
            if is_moving_func(player):
                x, y = get_animated_pos_func(player)
                token_radius = 15
                pygame.draw.circle(self.screen, Colors.BLACK, (x+1, y+2), token_radius + 1)
                pygame.draw.circle(self.screen, player.color, (x, y), token_radius)
            else:
                pos = player.position
                if pos not in positions:
                    positions[pos] = []
                positions[pos].append(player)
        
        token_radius = 12
        for pos, players in positions.items():
            x, y = self.get_space_center(pos)
            
            if len(players) == 1:
                player = players[0]
                pygame.draw.circle(self.screen, Colors.BLACK, (x+1, y+2), token_radius + 1)
                pygame.draw.circle(self.screen, player.color, (x, y), token_radius)
            else:
                angle_step = 2 * math.pi / len(players)
                radius = 18
                for i, player in enumerate(players):
                    angle = i * angle_step
                    px = x + int(math.cos(angle) * radius)
                    py = y + int(math.sin(angle) * radius)
                    pygame.draw.circle(self.screen, Colors.BLACK, (px+1, py+2), token_radius + 1)
                    pygame.draw.circle(self.screen, player.color, (px, py), token_radius)


class DiceDrawer:
    
    def __init__(self, screen: pygame.Surface, board_rect: pygame.Rect):
        self.screen = screen
        self.board_rect = board_rect
    
    def create_die_surface(self, value: int, size: int) -> pygame.Surface:
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        
        pygame.draw.rect(surf, Colors.WHITE, surf.get_rect(), border_radius=8)
        pygame.draw.rect(surf, Colors.BLACK, surf.get_rect(), 2, border_radius=8)
        
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
    
    def draw_dice(self, dice_rolling: bool, dice_values: Tuple[int, int]):
        center_x = self.board_rect.centerx
        center_y = self.board_rect.centery + 60
        die_size = 50
        
        if dice_rolling:
            for i in range(2):
                x = center_x - die_size - 10 + i * (die_size + 20)
                angle = random.randint(-15, 15)
                value = random.randint(1, 6)
                
                die_surf = self.create_die_surface(value, die_size)
                rotated = pygame.transform.rotate(die_surf, angle)
                rect = rotated.get_rect(center=(x, center_y))
                self.screen.blit(rotated, rect)
        else:
            for i, value in enumerate(dice_values):
                if value == 0:
                    continue
                x = center_x - die_size - 10 + i * (die_size + 20)
                die_surf = self.create_die_surface(value, die_size)
                rect = die_surf.get_rect(center=(x, center_y))
                self.screen.blit(die_surf, rect)
