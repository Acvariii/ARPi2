import pygame
import random
import math
from typing import List, Tuple, Dict
from config import Colors


class Particle:
    """Optimized particle with simple circle drawing"""
    def __init__(self, x: float, y: float, vx: float, vy: float, color: Tuple[int, int, int], lifetime: float):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.size = random.randint(2, 4)
    
    def update(self, dt: float) -> bool:
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 100 * dt
        self.lifetime -= dt
        return self.lifetime > 0
    
    def draw(self, screen: pygame.Surface):
        # Fast non-alpha circle drawing
        size = max(1, int(self.size * (self.lifetime / self.max_lifetime)))
        if size > 0:
            pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), size)


class CharacterCreationVisuals:
    
    RACE_THEMES = {
        "Human": {
            "bg_colors": [(70, 80, 90), (50, 60, 80), (60, 70, 85)],
            "particle_color": (200, 200, 220),
            "accent": (180, 160, 140),
            "icon": "⚔"
        },
        "Elf": {
            "bg_colors": [(40, 70, 50), (30, 80, 60), (35, 75, 55)],
            "particle_color": (150, 255, 150),
            "accent": (120, 255, 120),
            "icon": "🍃"
        },
        "Dwarf": {
            "bg_colors": [(80, 60, 50), (70, 55, 45), (75, 58, 48)],
            "particle_color": (255, 200, 100),
            "accent": (200, 150, 100),
            "icon": "⚒"
        },
        "Halfling": {
            "bg_colors": [(90, 85, 60), (80, 75, 50), (85, 80, 55)],
            "particle_color": (255, 230, 150),
            "accent": (220, 200, 120),
            "icon": "🌾"
        },
        "Orc": {
            "bg_colors": [(60, 40, 40), (70, 45, 35), (65, 42, 38)],
            "particle_color": (200, 50, 50),
            "accent": (180, 60, 60),
            "icon": "⚡"
        },
        "Tiefling": {
            "bg_colors": [(60, 30, 50), (70, 35, 60), (65, 32, 55)],
            "particle_color": (255, 100, 150),
            "accent": (200, 50, 100),
            "icon": "🔥"
        }
    }
    
    CLASS_THEMES = {
        "Fighter": {
            "bg_colors": [(80, 50, 50), (90, 55, 55), (85, 52, 52)],
            "particle_color": (255, 150, 100),
            "accent": (220, 100, 80),
            "symbol": "⚔️"
        },
        "Wizard": {
            "bg_colors": [(30, 40, 70), (35, 50, 90), (32, 45, 80)],
            "particle_color": (150, 150, 255),
            "accent": (180, 150, 255),
            "symbol": "✨"
        },
        "Rogue": {
            "bg_colors": [(40, 40, 50), (50, 50, 60), (45, 45, 55)],
            "particle_color": (150, 150, 180),
            "accent": (120, 120, 150),
            "symbol": "🗡️"
        },
        "Cleric": {
            "bg_colors": [(70, 70, 80), (80, 80, 90), (75, 75, 85)],
            "particle_color": (255, 255, 200),
            "accent": (230, 230, 150),
            "symbol": "✝️"
        },
        "Ranger": {
            "bg_colors": [(50, 70, 50), (60, 80, 60), (55, 75, 55)],
            "particle_color": (150, 200, 120),
            "accent": (120, 180, 100),
            "symbol": "🏹"
        },
        "Paladin": {
            "bg_colors": [(80, 70, 60), (90, 80, 70), (85, 75, 65)],
            "particle_color": (255, 220, 150),
            "accent": (240, 200, 120),
            "symbol": "🛡️"
        }
    }
    
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.particles: List[Particle] = []
        self.time = 0.0
        
        # Pre-render cache
        self._card_cache = {}
        self._bg_cache = {}
    
    def update(self, dt: float):
        self.time += dt
        # Update only alive particles
        alive_particles = []
        for p in self.particles:
            if p.update(dt):
                alive_particles.append(p)
        self.particles = alive_particles
    
    def spawn_particles(self, center: Tuple[int, int], color: Tuple[int, int, int], count: int = 2):
        # Reduced particle count for performance
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(50, 120)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed - 100
            self.particles.append(Particle(center[0], center[1], vx, vy, color, random.uniform(0.8, 1.5)))
    
    def _draw_static_background(self, theme_colors: List[Tuple[int, int, int]]):
        """Fast static gradient background (no animation)"""
        width, height = self.screen.get_size()
        
        # Create cache key
        cache_key = tuple(theme_colors[0])
        
        if cache_key not in self._bg_cache:
            # Pre-render gradient
            bg_surf = pygame.Surface((width, height))
            for i in range(height):
                ratio = i / height
                color = tuple(int(theme_colors[0][j] * (1 - ratio) + theme_colors[1][j] * ratio) for j in range(3))
                pygame.draw.line(bg_surf, color, (0, i), (width, i))
            self._bg_cache[cache_key] = bg_surf
        
        self.screen.blit(self._bg_cache[cache_key], (0, 0))
    
    def draw_race_selection(self, selected_race: str, available_races: List[str], player_color: Tuple[int, int, int]):
        width, height = self.screen.get_size()
        
        theme = self.RACE_THEMES.get(selected_race or "Human", self.RACE_THEMES["Human"])
        self._draw_static_background(theme["bg_colors"])
        
        # Cache font rendering
        if "race_title" not in self._card_cache:
            title_font = pygame.font.SysFont("Arial", 72, bold=True)
            title = title_font.render("Choose Your Race", True, (255, 255, 220))
            self._card_cache["race_title"] = title
        
        title = self._card_cache["race_title"]
        self.screen.blit(title, (width//2 - title.get_width()//2, 50))
        
        card_width = 280
        card_height = 380
        spacing = 30
        total_width = len(available_races) * card_width + (len(available_races) - 1) * spacing
        start_x = (width - total_width) // 2
        card_y = height // 2 - card_height // 2 + 50
        
        for i, race in enumerate(available_races):
            x = start_x + i * (card_width + spacing)
            is_selected = race == selected_race
            
            race_theme = self.RACE_THEMES[race]
            
            card_rect = pygame.Rect(x, card_y, card_width, card_height)
            
            # Simple glow effect without alpha
            if is_selected:
                glow_rect = pygame.Rect(x - 6, card_y - 6, card_width + 12, card_height + 12)
                pygame.draw.rect(self.screen, race_theme["accent"], glow_rect, 3)
            
            bg_color = race_theme["bg_colors"][0] if not is_selected else tuple(min(255, c + 30) for c in race_theme["bg_colors"][0])
            pygame.draw.rect(self.screen, bg_color, card_rect)
            pygame.draw.rect(self.screen, race_theme["accent"], card_rect, 4 if is_selected else 2)
            
            icon_font = pygame.font.SysFont("Segoe UI Emoji", 80)
            icon_text = race_theme.get("icon", "★")
            icon_surf = icon_font.render(icon_text, True, race_theme["accent"])
            icon_rect = icon_surf.get_rect(center=(card_rect.centerx, card_rect.y + 100))
            self.screen.blit(icon_surf, icon_rect)
            
            name_font = pygame.font.SysFont("Arial", 36, bold=True)
            name_surf = name_font.render(race, True, Colors.WHITE)
            name_rect = name_surf.get_rect(center=(card_rect.centerx, card_rect.y + 200))
            self.screen.blit(name_surf, name_rect)
            
            if is_selected:
                badge_font = pygame.font.SysFont("Arial", 18, bold=True)
                badge_surf = badge_font.render("SELECTED", True, (255, 255, 255))
                badge_bg = pygame.Rect(0, 0, badge_surf.get_width() + 20, badge_surf.get_height() + 10)
                badge_bg.center = (card_rect.centerx, card_rect.bottom - 40)
                pygame.draw.rect(self.screen, race_theme["accent"], badge_bg)
                badge_rect = badge_surf.get_rect(center=badge_bg.center)
                self.screen.blit(badge_surf, badge_rect)
        
        for p in self.particles:
            p.draw(self.screen)
    
    def draw_class_selection(self, selected_class: str, available_classes: List[str], player_color: Tuple[int, int, int]):
        width, height = self.screen.get_size()
        
        theme = self.CLASS_THEMES.get(selected_class or "Fighter", self.CLASS_THEMES["Fighter"])
        self._draw_static_background(theme["bg_colors"])
        
        # Cache font rendering
        if "class_title" not in self._card_cache:
            title_font = pygame.font.SysFont("Arial", 72, bold=True)
            title = title_font.render("Choose Your Class", True, (255, 255, 220))
            self._card_cache["class_title"] = title
        
        title = self._card_cache["class_title"]
        self.screen.blit(title, (width//2 - title.get_width()//2, 50))
        
        card_width = 280
        card_height = 380
        spacing = 30
        total_width = len(available_classes) * card_width + (len(available_classes) - 1) * spacing
        start_x = (width - total_width) // 2
        card_y = height // 2 - card_height // 2 + 50
        
        for i, cls in enumerate(available_classes):
            x = start_x + i * (card_width + spacing)
            is_selected = cls == selected_class
            
            class_theme = self.CLASS_THEMES[cls]
            
            card_rect = pygame.Rect(x, card_y, card_width, card_height)
            
            # Simple glow effect without alpha
            if is_selected:
                glow_rect = pygame.Rect(x - 6, card_y - 6, card_width + 12, card_height + 12)
                pygame.draw.rect(self.screen, class_theme["accent"], glow_rect, 3)
            
            bg_color = class_theme["bg_colors"][0] if not is_selected else tuple(min(255, c + 30) for c in class_theme["bg_colors"][0])
            pygame.draw.rect(self.screen, bg_color, card_rect)
            pygame.draw.rect(self.screen, class_theme["accent"], card_rect, 4 if is_selected else 2)
            
            icon_font = pygame.font.SysFont("Segoe UI Emoji", 80)
            icon_text = class_theme.get("symbol", "⚔")
            icon_surf = icon_font.render(icon_text, True, class_theme["accent"])
            icon_rect = icon_surf.get_rect(center=(card_rect.centerx, card_rect.y + 100))
            self.screen.blit(icon_surf, icon_rect)
            
            name_font = pygame.font.SysFont("Arial", 36, bold=True)
            name_surf = name_font.render(cls, True, Colors.WHITE)
            name_rect = name_surf.get_rect(center=(card_rect.centerx, card_rect.y + 200))
            self.screen.blit(name_surf, name_rect)
            
            if is_selected:
                badge_font = pygame.font.SysFont("Arial", 18, bold=True)
                badge_surf = badge_font.render("SELECTED", True, (255, 255, 255))
                badge_bg = pygame.Rect(0, 0, badge_surf.get_width() + 20, badge_surf.get_height() + 10)
                badge_bg.center = (card_rect.centerx, card_rect.bottom - 40)
                pygame.draw.rect(self.screen, class_theme["accent"], badge_bg)
                badge_rect = badge_surf.get_rect(center=badge_bg.center)
                self.screen.blit(badge_surf, badge_rect)
        
        for p in self.particles:
            p.draw(self.screen)
    
    def draw_ability_scores(self, abilities: Dict[str, int], points_remaining: int, selected_ability: str = None):
        width, height = self.screen.get_size()
        
        bg_colors = [(40, 50, 60), (50, 60, 70), (45, 55, 65)]
        self._draw_static_background(bg_colors)
        
        # Cache font rendering
        if "ability_title" not in self._card_cache:
            title_font = pygame.font.SysFont("Arial", 72, bold=True)
            title = title_font.render("Set Ability Scores", True, (255, 255, 220))
            self._card_cache["ability_title"] = title
        
        title = self._card_cache["ability_title"]
        self.screen.blit(title, (width//2 - title.get_width()//2, 50))
        
        points_font = pygame.font.SysFont("Arial", 48, bold=True)
        points_color = (100, 255, 100) if points_remaining == 0 else (255, 200, 100) if points_remaining < 10 else Colors.WHITE
        points_text = points_font.render(f"Points Remaining: {points_remaining}", True, points_color)
        self.screen.blit(points_text, (width//2 - points_text.get_width()//2, 150))
        
        ability_names = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]
        ability_full = {
            "STR": "Strength",
            "DEX": "Dexterity",
            "CON": "Constitution",
            "INT": "Intelligence",
            "WIS": "Wisdom",
            "CHA": "Charisma"
        }
        
        card_width = 220
        card_height = 180
        spacing = 40
        cols = 3
        rows = 2
        
        total_width = cols * card_width + (cols - 1) * spacing
        total_height = rows * card_height + (rows - 1) * spacing
        start_x = (width - total_width) // 2
        start_y = (height - total_height) // 2 + 80
        
        for i, ability in enumerate(ability_names):
            row = i // cols
            col = i % cols
            x = start_x + col * (card_width + spacing)
            y = start_y + row * (card_height + spacing)
            
            score = abilities.get(ability, 8)
            modifier = (score - 10) // 2
            
            card_rect = pygame.Rect(x, y, card_width, card_height)
            
            is_selected = ability == selected_ability
            if is_selected:
                glow_rect = pygame.Rect(x - 5, y - 5, card_width + 10, card_height + 10)
                pygame.draw.rect(self.screen, (255, 200, 100), glow_rect, 3)
            
            bg_color = (60, 70, 80) if not is_selected else (80, 90, 100)
            pygame.draw.rect(self.screen, bg_color, card_rect)
            pygame.draw.rect(self.screen, (200, 180, 120), card_rect, 3 if is_selected else 2)
            
            ability_font = pygame.font.SysFont("Arial", 28, bold=True)
            ability_text = ability_font.render(ability, True, (255, 220, 150))
            self.screen.blit(ability_text, (card_rect.centerx - ability_text.get_width()//2, card_rect.y + 15))
            
            full_font = pygame.font.SysFont("Arial", 16)
            full_text = full_font.render(ability_full[ability], True, (200, 200, 200))
            self.screen.blit(full_text, (card_rect.centerx - full_text.get_width()//2, card_rect.y + 48))
            
            score_font = pygame.font.SysFont("Arial", 56, bold=True)
            score_text = score_font.render(str(score), True, Colors.WHITE)
            self.screen.blit(score_text, (card_rect.centerx - score_text.get_width()//2, card_rect.y + 75))
            
            mod_font = pygame.font.SysFont("Arial", 24)
            mod_str = f"+{modifier}" if modifier >= 0 else str(modifier)
            mod_color = (100, 255, 100) if modifier > 0 else (255, 100, 100) if modifier < 0 else (200, 200, 200)
            mod_text = mod_font.render(f"({mod_str})", True, mod_color)
            self.screen.blit(mod_text, (card_rect.centerx - mod_text.get_width()//2, card_rect.y + 140))
        
        for p in self.particles:
            p.draw(self.screen)
    
    def draw_character_complete(self, character_name: str, race: str, char_class: str, player_color: Tuple[int, int, int]):
        width, height = self.screen.get_size()
        
        race_theme = self.RACE_THEMES.get(race, self.RACE_THEMES["Human"])
        class_theme = self.CLASS_THEMES.get(char_class, self.CLASS_THEMES["Fighter"])
        
        combined_colors = [
            tuple((race_theme["bg_colors"][0][i] + class_theme["bg_colors"][0][i]) // 2 for i in range(3)),
            tuple((race_theme["bg_colors"][1][i] + class_theme["bg_colors"][1][i]) // 2 for i in range(3))
        ]
        self._draw_static_background(combined_colors)
        
        # Cache font rendering
        if "complete_title" not in self._card_cache:
            title_font = pygame.font.SysFont("Arial", 84, bold=True)
            title = title_font.render("Hero Created!", True, (255, 255, 100))
            self._card_cache["complete_title"] = title
        
        title = self._card_cache["complete_title"]
        self.screen.blit(title, (width//2 - title.get_width()//2, 100))
        
        name_font = pygame.font.SysFont("Arial", 64, bold=True)
        name_surf = name_font.render(character_name, True, player_color)
        name_shadow = name_font.render(character_name, True, (0, 0, 0))
        self.screen.blit(name_shadow, (width//2 - name_surf.get_width()//2 + 3, height//2 - 53))
        self.screen.blit(name_surf, (width//2 - name_surf.get_width()//2, height//2 - 50))
        
        desc_font = pygame.font.SysFont("Arial", 42)
        desc_text = f"{race} {char_class}"
        desc_surf = desc_font.render(desc_text, True, (220, 220, 220))
        self.screen.blit(desc_surf, (width//2 - desc_surf.get_width()//2, height//2 + 30))
        
        # Draw existing particles only
        for p in self.particles:
            p.draw(self.screen)
