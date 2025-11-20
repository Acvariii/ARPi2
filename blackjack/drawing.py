import pygame
from typing import List, Tuple
from config import Colors

class CardDrawer:
    
    CARD_WIDTH = 60
    CARD_HEIGHT = 85
    
    @staticmethod
    def draw_card(screen: pygame.Surface, card: Tuple[str, str], x: int, y: int, face_down: bool = False, outline_color: tuple = None):
        card_rect = pygame.Rect(x, y, CardDrawer.CARD_WIDTH, CardDrawer.CARD_HEIGHT)
        
        if face_down:
            pygame.draw.rect(screen, (50, 80, 150), card_rect, border_radius=5)
            border_color = outline_color if outline_color else Colors.WHITE
            pygame.draw.rect(screen, border_color, card_rect, width=3, border_radius=5)
            
            for i in range(5):
                for j in range(7):
                    cx = x + 10 + i * 10
                    cy = y + 10 + j * 10
                    pygame.draw.circle(screen, (80, 110, 180), (cx, cy), 2)
        else:
            rank, suit = card
            is_red = suit in ['H', 'D']
            card_color = (220, 50, 50) if is_red else (30, 30, 30)
            
            suit_names = {'S': 'Spade', 'H': 'Heart', 'D': 'Diam', 'C': 'Club'}
            suit_display = suit_names.get(suit, suit)
            
            pygame.draw.rect(screen, Colors.WHITE, card_rect, border_radius=5)
            border_color = outline_color if outline_color else (200, 200, 200)
            border_width = 3 if outline_color else 2
            pygame.draw.rect(screen, border_color, card_rect, width=border_width, border_radius=5)
            
            font_rank = pygame.font.SysFont(None, 32, bold=True)
            font_suit = pygame.font.SysFont(None, 20, bold=True)
            
            rank_surf = font_rank.render(rank, True, card_color)
            suit_surf = font_suit.render(suit_display, True, card_color)
            
            screen.blit(rank_surf, (x + 5, y + 5))
            screen.blit(suit_surf, (x + CardDrawer.CARD_WIDTH // 2 - suit_surf.get_width() // 2, 
                                   y + CardDrawer.CARD_HEIGHT // 2 - suit_surf.get_height() // 2))
            
            rank_surf_bottom = font_rank.render(rank, True, card_color)
            rank_surf_bottom = pygame.transform.rotate(rank_surf_bottom, 180)
            screen.blit(rank_surf_bottom, (x + CardDrawer.CARD_WIDTH - rank_surf_bottom.get_width() - 5, 
                                           y + CardDrawer.CARD_HEIGHT - rank_surf_bottom.get_height() - 5))
    
    @staticmethod
    def draw_hand(screen: pygame.Surface, hand: List[Tuple[str, str]], x: int, y: int, 
                  spacing: int = 20, dealer_hidden: bool = False, outline_color: tuple = None):
        for i, card in enumerate(hand):
            face_down = dealer_hidden and i == 1
            CardDrawer.draw_card(screen, card, x + i * spacing, y, face_down, outline_color)
    
    @staticmethod
    def get_hand_width(hand_size: int, spacing: int = 20) -> int:
        if hand_size == 0:
            return 0
        return CardDrawer.CARD_WIDTH + (hand_size - 1) * spacing


class ChipDrawer:
    
    CHIP_COLORS = {
        1: (255, 255, 255),
        5: (255, 100, 100),
        25: (100, 255, 100),
        100: (50, 50, 50),
        500: (150, 100, 255),
    }
    
    @staticmethod
    def draw_chip(screen: pygame.Surface, value: int, x: int, y: int, radius: int = 20):
        color = ChipDrawer.CHIP_COLORS.get(value, (128, 128, 128))
        
        pygame.draw.circle(screen, color, (x, y), radius)
        pygame.draw.circle(screen, Colors.WHITE, (x, y), radius, width=3)
        pygame.draw.circle(screen, color, (x, y), radius - 5, width=2)
        
        font = pygame.font.SysFont(None, 20, bold=True)
        text = font.render(str(value), True, Colors.WHITE if value == 100 else Colors.BLACK)
        screen.blit(text, (x - text.get_width() // 2, y - text.get_height() // 2))
    
    @staticmethod
    def draw_chip_stack(screen: pygame.Surface, amount: int, x: int, y: int):
        denominations = [500, 100, 25, 5, 1]
        remaining = amount
        offset = 0
        
        for denom in denominations:
            count = remaining // denom
            if count > 0:
                for i in range(min(count, 5)):
                    ChipDrawer.draw_chip(screen, denom, x, y - offset, 18)
                    offset += 4
                remaining -= count * denom
                if remaining <= 0:
                    break
