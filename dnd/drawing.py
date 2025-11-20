import pygame
from typing import List, Tuple, Dict
from config import Colors
from ui_components import RotatedText


class CharacterSheetDrawer:
    
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
    
    def draw_character_sheet(self, character, rect: pygame.Rect, orientation: int):
        if not character or not character.name:
            return
        
        overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
        overlay.fill((20, 20, 30, 240))
        self.screen.blit(overlay, rect)
        
        pygame.draw.rect(self.screen, character.player_color, rect, 3, border_radius=8)
        
        margin = 10
        content_rect = pygame.Rect(rect.x + margin, rect.y + margin, rect.width - 2*margin, rect.height - 2*margin)
        
        font_title = pygame.font.SysFont("Arial", 18, bold=True)
        font_text = pygame.font.SysFont("Arial", 14)
        font_small = pygame.font.SysFont("Arial", 12)
        
        if orientation in [0, 180]:
            lines = [
                (character.name, font_title, character.player_color),
                (f"{character.race} {character.char_class}", font_text, Colors.WHITE),
                (f"Level {character.level} | {character.alignment}", font_small, (200, 200, 200)),
                ("", font_small, Colors.WHITE),
                (f"HP: {character.current_hp}/{character.max_hp}", font_text, (100, 255, 100) if character.current_hp > character.max_hp//2 else (255, 100, 100)),
                (f"AC: {character.armor_class}", font_text, (200, 200, 255)),
                ("", font_small, Colors.WHITE),
            ]
            
            for ability, score in character.abilities.items():
                mod = (score - 10) // 2
                mod_str = f"+{mod}" if mod >= 0 else str(mod)
                lines.append((f"{ability[:3]}: {score} ({mod_str})", font_small, (220, 220, 220)))
            
            RotatedText.draw_block(self.screen, lines, content_rect, orientation, line_spacing=14, wrap=False)
        else:
            lines = [
                (character.name, font_title, character.player_color),
                (f"{character.race} {character.char_class}", font_text, Colors.WHITE),
                (f"Lvl {character.level}", font_small, (200, 200, 200)),
                ("", font_small, Colors.WHITE),
                (f"HP: {character.current_hp}/{character.max_hp}", font_text, (100, 255, 100) if character.current_hp > character.max_hp//2 else (255, 100, 100)),
                (f"AC: {character.armor_class}", font_text, (200, 200, 255)),
                ("", font_small, Colors.WHITE),
            ]
            
            for ability, score in character.abilities.items():
                mod = (score - 10) // 2
                mod_str = f"+{mod}" if mod >= 0 else str(mod)
                lines.append((f"{ability[:3]} {score}({mod_str})", font_small, (220, 220, 220)))
            
            RotatedText.draw_block(self.screen, lines, content_rect, orientation, line_spacing=20, wrap=False)


class DiceVisualizer:
    
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
    
    def draw_dice_result(self, center: Tuple[int, int], value: int, size: int = 60):
        pygame.draw.rect(self.screen, Colors.WHITE, 
                        (center[0] - size//2, center[1] - size//2, size, size), 
                        border_radius=8)
        pygame.draw.rect(self.screen, Colors.BLACK, 
                        (center[0] - size//2, center[1] - size//2, size, size), 
                        2, border_radius=8)
        
        font = pygame.font.SysFont("Arial", size//2, bold=True)
        text = font.render(str(value), True, Colors.BLACK)
        text_rect = text.get_rect(center=center)
        self.screen.blit(text, text_rect)
    
    def draw_d20_roll(self, center: Tuple[int, int], value: int, modifier: int = 0):
        total = value + modifier
        
        color = Colors.WHITE
        if value == 20:
            color = (100, 255, 100)
        elif value == 1:
            color = (255, 100, 100)
        
        size = 80
        pygame.draw.circle(self.screen, color, center, size//2)
        pygame.draw.circle(self.screen, Colors.BLACK, center, size//2, 3)
        
        font_big = pygame.font.SysFont("Arial", 36, bold=True)
        font_small = pygame.font.SysFont("Arial", 18)
        
        text_roll = font_big.render(str(value), True, Colors.BLACK)
        text_rect = text_roll.get_rect(center=(center[0], center[1] - 10))
        self.screen.blit(text_roll, text_rect)
        
        if modifier != 0:
            mod_str = f"+{modifier}" if modifier > 0 else str(modifier)
            text_mod = font_small.render(f"({mod_str}) = {total}", True, (50, 50, 50))
            text_rect = text_mod.get_rect(center=(center[0], center[1] + 20))
            self.screen.blit(text_mod, text_rect)


class CombatDisplay:
    
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
    
    def draw_initiative_tracker(self, combat_manager, rect: pygame.Rect):
        pygame.draw.rect(self.screen, (30, 30, 40, 230), rect, border_radius=8)
        pygame.draw.rect(self.screen, (255, 215, 0), rect, 2, border_radius=8)
        
        font_title = pygame.font.SysFont("Arial", 16, bold=True)
        font_text = pygame.font.SysFont("Arial", 14)
        
        title = font_title.render(f"Initiative - Round {combat_manager.round_number}", True, (255, 215, 0))
        self.screen.blit(title, (rect.x + 10, rect.y + 5))
        
        y_offset = rect.y + 30
        for i, entry in enumerate(combat_manager.initiative_order):
            entity = entry["entity"]
            initiative = entry["initiative"]
            is_current = (i == combat_manager.current_turn)
            
            if is_current:
                pygame.draw.rect(self.screen, (80, 80, 100), 
                               (rect.x + 5, y_offset - 2, rect.width - 10, 20), border_radius=4)
            
            name = entity.name if hasattr(entity, 'name') else "Enemy"
            color = entity.player_color if hasattr(entity, 'player_color') else Colors.WHITE
            
            text = font_text.render(f"{initiative}: {name}", True, color)
            self.screen.blit(text, (rect.x + 10, y_offset))
            
            y_offset += 22
