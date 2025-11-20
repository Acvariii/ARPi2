"""
D&D Character Creation - Pyglet/OpenGL Implementation
Optimized for 60 FPS at 1920x1080
"""

import time
import random
import math
from typing import List, Dict, Tuple, Optional
import pyglet
from pyglet_games.renderer import PygletRenderer
from config import PLAYER_COLORS, Colors, HOVER_TIME_THRESHOLD
from dnd.character import Character, RACES, CLASSES, generate_character_name, CLASS_SKILLS


class PygletParticle:
    """Optimized particle for OpenGL rendering"""
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
    
    def draw(self, renderer: PygletRenderer):
        size = max(1, int(self.size * (self.lifetime / self.max_lifetime)))
        if size > 0:
            alpha = int(255 * (self.lifetime / self.max_lifetime))
            renderer.draw_circle(self.color, (int(self.x), int(self.y)), size, alpha=alpha)


class DnDCharacterCreation:
    """Full-screen D&D character creation with OpenGL rendering"""
    
    RACE_THEMES = {
        "Human": {
            "bg_colors": [(70, 80, 90), (50, 60, 80)],
            "particle_color": (200, 200, 220),
            "accent": (180, 160, 140),
            "icon": "⚔"
        },
        "Elf": {
            "bg_colors": [(40, 70, 50), (30, 80, 60)],
            "particle_color": (150, 255, 150),
            "accent": (120, 255, 120),
            "icon": "🍃"
        },
        "Dwarf": {
            "bg_colors": [(80, 60, 50), (70, 55, 45)],
            "particle_color": (255, 200, 100),
            "accent": (200, 150, 100),
            "icon": "⚒"
        },
        "Halfling": {
            "bg_colors": [(90, 85, 60), (80, 75, 50)],
            "particle_color": (255, 230, 150),
            "accent": (220, 200, 120),
            "icon": "🌾"
        },
        "Orc": {
            "bg_colors": [(60, 40, 40), (70, 45, 35)],
            "particle_color": (200, 50, 50),
            "accent": (180, 60, 60),
            "icon": "⚡"
        },
        "Tiefling": {
            "bg_colors": [(60, 30, 50), (70, 35, 60)],
            "particle_color": (255, 100, 150),
            "accent": (200, 50, 100),
            "icon": "🔥"
        }
    }
    
    CLASS_THEMES = {
        "Fighter": {
            "bg_colors": [(80, 50, 50), (90, 55, 55)],
            "particle_color": (255, 150, 100),
            "accent": (220, 100, 80),
            "symbol": "⚔️"
        },
        "Wizard": {
            "bg_colors": [(30, 40, 70), (35, 50, 90)],
            "particle_color": (150, 150, 255),
            "accent": (180, 150, 255),
            "symbol": "✨"
        },
        "Rogue": {
            "bg_colors": [(40, 40, 50), (50, 50, 60)],
            "particle_color": (150, 150, 180),
            "accent": (120, 120, 150),
            "symbol": "🗡️"
        },
        "Cleric": {
            "bg_colors": [(70, 70, 80), (80, 80, 90)],
            "particle_color": (255, 255, 200),
            "accent": (230, 230, 150),
            "symbol": "✝️"
        },
        "Ranger": {
            "bg_colors": [(50, 70, 50), (60, 80, 60)],
            "particle_color": (150, 200, 120),
            "accent": (120, 180, 100),
            "symbol": "🏹"
        },
        "Paladin": {
            "bg_colors": [(80, 70, 60), (90, 80, 70)],
            "particle_color": (255, 220, 150),
            "accent": (240, 200, 120),
            "symbol": "🛡️"
        }
    }
    
    def __init__(self, width: int, height: int, renderer: PygletRenderer):
        self.width = width
        self.height = height
        self.renderer = renderer
        
        self.particles: List[PygletParticle] = []
        self.hover_states: Dict[str, Dict] = {}
        
        # Character creation state
        self.creation_step = "race"  # race, class, abilities, complete
        self.temp_character: Optional[Character] = None
        self.current_player_idx = 0
        self.ability_points_remaining = 27
        self.selected_ability = None
        
        # Pre-rendered background cache
        self._bg_cache = {}
        self._bg_cache_theme = None
        
    def start_creation(self, player_idx: int):
        """Start character creation for a player"""
        self.current_player_idx = player_idx
        self.temp_character = Character("", PLAYER_COLORS[player_idx])
        self.temp_character.abilities = {"STR": 8, "DEX": 8, "CON": 8, "INT": 8, "WIS": 8, "CHA": 8}
        self.creation_step = "race"
        self.ability_points_remaining = 27
        self.selected_ability = None
        self.hover_states = {}
        self.particles = []
    
    def update(self, dt: float):
        """Update particles"""
        alive_particles = []
        for p in self.particles:
            if p.update(dt):
                alive_particles.append(p)
        self.particles = alive_particles
    
    def spawn_particles(self, center: Tuple[int, int], color: Tuple[int, int, int], count: int = 5):
        """Spawn particles at a location"""
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(50, 120)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed - 100
            self.particles.append(PygletParticle(center[0], center[1], vx, vy, color, random.uniform(0.8, 1.5)))
    
    def handle_input(self, fingertip_meta: List[Dict]) -> bool:
        """
        Handle input for character creation
        Returns True when creation is complete
        """
        current_time = time.time()
        
        if self.creation_step == "race":
            return self._handle_race_selection(fingertip_meta, current_time)
        elif self.creation_step == "class":
            return self._handle_class_selection(fingertip_meta, current_time)
        elif self.creation_step == "abilities":
            return self._handle_ability_scores(fingertip_meta, current_time)
        elif self.creation_step == "complete":
            return self._handle_complete(fingertip_meta, current_time)
        
        return False
    
    def _handle_race_selection(self, fingertip_meta: List[Dict], current_time: float) -> bool:
        card_width = 280
        card_height = 380
        spacing = 30
        total_width = len(RACES) * card_width + (len(RACES) - 1) * spacing
        start_x = (self.width - total_width) // 2
        card_y = self.height // 2 - card_height // 2 + 50
        
        active_hovers = set()
        
        for i, race in enumerate(RACES):
            x = start_x + i * (card_width + spacing)
            card_rect = (x, card_y, card_width, card_height)
            key = f"race_{race}"
            
            for meta in fingertip_meta:
                pos = meta["pos"]
                if (card_rect[0] <= pos[0] <= card_rect[0] + card_rect[2] and
                    card_rect[1] <= pos[1] <= card_rect[1] + card_rect[3]):
                    active_hovers.add(key)
                    
                    if key not in self.hover_states:
                        self.hover_states[key] = {"start_time": current_time, "pos": pos}
                    
                    hover_duration = current_time - self.hover_states[key]["start_time"]
                    if hover_duration >= HOVER_TIME_THRESHOLD:
                        self.temp_character.race = race
                        self.spawn_particles(pos, self.RACE_THEMES[race]["particle_color"], 3)
                        self.creation_step = "class"
                        self.hover_states = {}
                        return False
                    break
        
        # Remove stale hover states
        for key in list(self.hover_states.keys()):
            if key not in active_hovers:
                del self.hover_states[key]
        
        return False
    
    def _handle_class_selection(self, fingertip_meta: List[Dict], current_time: float) -> bool:
        card_width = 280
        card_height = 380
        spacing = 30
        total_width = len(CLASSES) * card_width + (len(CLASSES) - 1) * spacing
        start_x = (self.width - total_width) // 2
        card_y = self.height // 2 - card_height // 2 + 50
        
        active_hovers = set()
        
        for i, cls in enumerate(CLASSES):
            x = start_x + i * (card_width + spacing)
            card_rect = (x, card_y, card_width, card_height)
            key = f"class_{cls}"
            
            for meta in fingertip_meta:
                pos = meta["pos"]
                if (card_rect[0] <= pos[0] <= card_rect[0] + card_rect[2] and
                    card_rect[1] <= pos[1] <= card_rect[1] + card_rect[3]):
                    active_hovers.add(key)
                    
                    if key not in self.hover_states:
                        self.hover_states[key] = {"start_time": current_time, "pos": pos}
                    
                    hover_duration = current_time - self.hover_states[key]["start_time"]
                    if hover_duration >= HOVER_TIME_THRESHOLD:
                        self.temp_character.char_class = cls
                        self.temp_character.name = generate_character_name(self.temp_character.race, cls)
                        self.temp_character.skills = CLASS_SKILLS.get(cls, [])
                        self.spawn_particles(pos, self.CLASS_THEMES[cls]["particle_color"], 3)
                        self.creation_step = "abilities"
                        self.hover_states = {}
                        return False
                    break
        
        for key in list(self.hover_states.keys()):
            if key not in active_hovers:
                del self.hover_states[key]
        
        return False
    
    def _handle_ability_scores(self, fingertip_meta: List[Dict], current_time: float) -> bool:
        ability_names = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]
        card_width = 220
        card_height = 180
        spacing = 40
        cols = 3
        rows = 2
        
        total_width = cols * card_width + (cols - 1) * spacing
        total_height = rows * card_height + (rows - 1) * spacing
        start_x = (self.width - total_width) // 2
        start_y = (self.height - total_height) // 2 + 80
        
        active_hovers = set()
        
        for i, ability in enumerate(ability_names):
            row = i // cols
            col = i % cols
            x = start_x + col * (card_width + spacing)
            y = start_y + row * (card_height + spacing)
            card_rect = (x, y, card_width, card_height)
            key = f"ability_{ability}"
            
            for meta in fingertip_meta:
                pos = meta["pos"]
                if (card_rect[0] <= pos[0] <= card_rect[0] + card_rect[2] and
                    card_rect[1] <= pos[1] <= card_rect[1] + card_rect[3]):
                    if self.temp_character.abilities[ability] < 15 and self.ability_points_remaining > 0:
                        cost = 1 if self.temp_character.abilities[ability] < 13 else 2
                        if cost <= self.ability_points_remaining:
                            active_hovers.add(key)
                            
                            if key not in self.hover_states:
                                self.hover_states[key] = {"start_time": current_time, "pos": pos}
                            
                            hover_duration = current_time - self.hover_states[key]["start_time"]
                            if hover_duration >= HOVER_TIME_THRESHOLD:
                                self.temp_character.abilities[ability] += 1
                                self.ability_points_remaining -= cost
                                self.selected_ability = ability
                                self.spawn_particles(pos, (100, 255, 100), 3)
                                del self.hover_states[key]
                    break
        
        # Check proceed button
        if self.ability_points_remaining == 0:
            proceed_rect = (self.width // 2 - 150, self.height - 120, 300, 80)
            key = "proceed_abilities"
            
            for meta in fingertip_meta:
                pos = meta["pos"]
                if (proceed_rect[0] <= pos[0] <= proceed_rect[0] + proceed_rect[2] and
                    proceed_rect[1] <= pos[1] <= proceed_rect[1] + proceed_rect[3]):
                    active_hovers.add(key)
                    
                    if key not in self.hover_states:
                        self.hover_states[key] = {"start_time": current_time, "pos": pos}
                    
                    hover_duration = current_time - self.hover_states[key]["start_time"]
                    if hover_duration >= HOVER_TIME_THRESHOLD:
                        self.temp_character.calculate_hp()
                        self.temp_character.calculate_ac()
                        self.creation_step = "complete"
                        self.spawn_particles((self.width // 2, self.height // 2), PLAYER_COLORS[self.current_player_idx], 5)
                        self.hover_states = {}
                        return False
                    break
        
        for key in list(self.hover_states.keys()):
            if key not in active_hovers:
                del self.hover_states[key]
        
        return False
    
    def _handle_complete(self, fingertip_meta: List[Dict], current_time: float) -> bool:
        proceed_rect = (self.width // 2 - 150, self.height - 120, 300, 80)
        key = "proceed_complete"
        
        active_hovers = set()
        
        for meta in fingertip_meta:
            pos = meta["pos"]
            if (proceed_rect[0] <= pos[0] <= proceed_rect[0] + proceed_rect[2] and
                proceed_rect[1] <= pos[1] <= proceed_rect[1] + proceed_rect[3]):
                active_hovers.add(key)
                
                if key not in self.hover_states:
                    self.hover_states[key] = {"start_time": current_time, "pos": pos}
                
                hover_duration = current_time - self.hover_states[key]["start_time"]
                if hover_duration >= HOVER_TIME_THRESHOLD:
                    # Save character
                    self.temp_character.save_to_file(self.current_player_idx)
                    self.hover_states = {}
                    return True  # Creation complete
                break
        
        for key in list(self.hover_states.keys()):
            if key not in active_hovers:
                del self.hover_states[key]
        
        return False
    
    def draw(self):
        """Draw the current creation step"""
        if self.creation_step == "race":
            self._draw_race_selection()
        elif self.creation_step == "class":
            self._draw_class_selection()
        elif self.creation_step == "abilities":
            self._draw_ability_scores()
        elif self.creation_step == "complete":
            self._draw_complete()
        
        # Draw particles
        for p in self.particles:
            p.draw(self.renderer)
        
        # Draw hover progress indicators
        self._draw_hover_indicators()
    
    def _draw_static_background(self, theme_colors: List[Tuple[int, int, int]]):
        """Draw solid background for maximum performance"""
        # Use the average of the two theme colors for a solid background
        avg_color = tuple((theme_colors[0][i] + theme_colors[1][i]) // 2 for i in range(3))
        self.renderer.draw_rect(avg_color, (0, 0, self.width, self.height))
    
    def _draw_race_selection(self):
        theme = self.RACE_THEMES.get(self.temp_character.race or "Human")
        self._draw_static_background(theme["bg_colors"])
        
        # Title
        self.renderer.draw_text("Choose Your Race", self.width // 2, self.height - 100, 
                               "Arial", 72, (255, 255, 220), anchor_x="center", anchor_y="center")
        
        # Cards
        card_width = 280
        card_height = 380
        spacing = 30
        total_width = len(RACES) * card_width + (len(RACES) - 1) * spacing
        start_x = (self.width - total_width) // 2
        card_y = self.height // 2 - card_height // 2 + 50
        
        for i, race in enumerate(RACES):
            x = start_x + i * (card_width + spacing)
            is_selected = race == self.temp_character.race
            
            race_theme = self.RACE_THEMES[race]
            
            # Glow effect
            if is_selected:
                self.renderer.draw_rect(race_theme["accent"], (x - 6, card_y - 6, card_width + 12, card_height + 12), width=3)
            
            # Card background
            bg_color = race_theme["bg_colors"][0] if not is_selected else tuple(min(255, c + 30) for c in race_theme["bg_colors"][0])
            self.renderer.draw_rect(bg_color, (x, card_y, card_width, card_height))
            self.renderer.draw_rect(race_theme["accent"], (x, card_y, card_width, card_height), width=4 if is_selected else 2)
            
            # Icon
            icon_text = race_theme.get("icon", "★")
            self.renderer.draw_text(icon_text, x + card_width // 2, card_y + card_height - 100,
                                   "Segoe UI Emoji", 80, race_theme["accent"], anchor_x="center", anchor_y="center")
            
            # Name
            self.renderer.draw_text(race, x + card_width // 2, card_y + card_height - 200,
                                   "Arial", 36, Colors.WHITE, anchor_x="center", anchor_y="center")
            
            # Selected badge
            if is_selected:
                badge_y = card_y + 40
                self.renderer.draw_rect(race_theme["accent"], (x + card_width // 2 - 50, badge_y, 100, 30))
                self.renderer.draw_text("SELECTED", x + card_width // 2, badge_y + 15,
                                       "Arial", 18, (255, 255, 255), anchor_x="center", anchor_y="center")
    
    def _draw_class_selection(self):
        theme = self.CLASS_THEMES.get(self.temp_character.char_class or "Fighter")
        self._draw_static_background(theme["bg_colors"])
        
        # Title
        self.renderer.draw_text("Choose Your Class", self.width // 2, self.height - 100,
                               "Arial", 72, (255, 255, 220), anchor_x="center", anchor_y="center")
        
        # Cards
        card_width = 280
        card_height = 380
        spacing = 30
        total_width = len(CLASSES) * card_width + (len(CLASSES) - 1) * spacing
        start_x = (self.width - total_width) // 2
        card_y = self.height // 2 - card_height // 2 + 50
        
        for i, cls in enumerate(CLASSES):
            x = start_x + i * (card_width + spacing)
            is_selected = cls == self.temp_character.char_class
            
            class_theme = self.CLASS_THEMES[cls]
            
            # Glow effect
            if is_selected:
                self.renderer.draw_rect(class_theme["accent"], (x - 6, card_y - 6, card_width + 12, card_height + 12), width=3)
            
            # Card background
            bg_color = class_theme["bg_colors"][0] if not is_selected else tuple(min(255, c + 30) for c in class_theme["bg_colors"][0])
            self.renderer.draw_rect(bg_color, (x, card_y, card_width, card_height))
            self.renderer.draw_rect(class_theme["accent"], (x, card_y, card_width, card_height), width=4 if is_selected else 2)
            
            # Symbol
            symbol_text = class_theme.get("symbol", "⚔")
            self.renderer.draw_text(symbol_text, x + card_width // 2, card_y + card_height - 100,
                                   "Segoe UI Emoji", 80, class_theme["accent"], anchor_x="center", anchor_y="center")
            
            # Name
            self.renderer.draw_text(cls, x + card_width // 2, card_y + card_height - 200,
                                   "Arial", 36, Colors.WHITE, anchor_x="center", anchor_y="center")
            
            # Selected badge
            if is_selected:
                badge_y = card_y + 40
                self.renderer.draw_rect(class_theme["accent"], (x + card_width // 2 - 50, badge_y, 100, 30))
                self.renderer.draw_text("SELECTED", x + card_width // 2, badge_y + 15,
                                       "Arial", 18, (255, 255, 255), anchor_x="center", anchor_y="center")
    
    def _draw_ability_scores(self):
        bg_colors = [(40, 50, 60), (50, 60, 70)]
        self._draw_static_background(bg_colors)
        
        # Title
        self.renderer.draw_text("Set Ability Scores", self.width // 2, self.height - 100,
                               "Arial", 72, (255, 255, 220), anchor_x="center", anchor_y="center")
        
        # Points remaining
        points_color = (100, 255, 100) if self.ability_points_remaining == 0 else (255, 200, 100) if self.ability_points_remaining < 10 else Colors.WHITE
        self.renderer.draw_text(f"Points Remaining: {self.ability_points_remaining}", self.width // 2, self.height - 200,
                               "Arial", 48, points_color, anchor_x="center", anchor_y="center")
        
        # Ability cards
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
        start_x = (self.width - total_width) // 2
        start_y = (self.height - total_height) // 2 + 80
        
        for i, ability in enumerate(ability_names):
            row = i // cols
            col = i % cols
            x = start_x + col * (card_width + spacing)
            y = start_y + row * (card_height + spacing)
            
            score = self.temp_character.abilities.get(ability, 8)
            modifier = (score - 10) // 2
            
            is_selected = ability == self.selected_ability
            
            # Glow
            if is_selected:
                self.renderer.draw_rect((255, 200, 100), (x - 5, y - 5, card_width + 10, card_height + 10), width=3)
            
            # Card background
            bg_color = (60, 70, 80) if not is_selected else (80, 90, 100)
            self.renderer.draw_rect(bg_color, (x, y, card_width, card_height))
            self.renderer.draw_rect((200, 180, 120), (x, y, card_width, card_height), width=3 if is_selected else 2)
            
            # Ability name
            self.renderer.draw_text(ability, x + card_width // 2, y + card_height - 15,
                                   "Arial", 28, (255, 220, 150), anchor_x="center", anchor_y="center")
            
            # Full name
            self.renderer.draw_text(ability_full[ability], x + card_width // 2, y + card_height - 48,
                                   "Arial", 16, (200, 200, 200), anchor_x="center", anchor_y="center")
            
            # Score
            self.renderer.draw_text(str(score), x + card_width // 2, y + card_height - 105,
                                   "Arial", 56, Colors.WHITE, anchor_x="center", anchor_y="center")
            
            # Modifier
            mod_str = f"+{modifier}" if modifier >= 0 else str(modifier)
            mod_color = (100, 255, 100) if modifier > 0 else (255, 100, 100) if modifier < 0 else (200, 200, 200)
            self.renderer.draw_text(f"({mod_str})", x + card_width // 2, y + 40,
                                   "Arial", 24, mod_color, anchor_x="center", anchor_y="center")
        
        # Continue button
        if self.ability_points_remaining == 0:
            proceed_rect = (self.width // 2 - 150, self.height - 120, 300, 80)
            self.renderer.draw_rect((100, 200, 100), proceed_rect)
            self.renderer.draw_rect((150, 255, 150), proceed_rect, width=4)
            self.renderer.draw_text("Continue", self.width // 2, self.height - 80,
                                   "Arial", 32, Colors.WHITE, anchor_x="center", anchor_y="center")
    
    def _draw_complete(self):
        # Merge race and class themes
        race_theme = self.RACE_THEMES.get(self.temp_character.race, self.RACE_THEMES["Human"])
        class_theme = self.CLASS_THEMES.get(self.temp_character.char_class, self.CLASS_THEMES["Fighter"])
        
        combined_colors = [
            tuple((race_theme["bg_colors"][0][i] + class_theme["bg_colors"][0][i]) // 2 for i in range(3)),
            tuple((race_theme["bg_colors"][1][i] + class_theme["bg_colors"][1][i]) // 2 for i in range(3))
        ]
        self._draw_static_background(combined_colors)
        
        # Title
        self.renderer.draw_text("Hero Created!", self.width // 2, self.height - 150,
                               "Arial", 84, (255, 255, 100), anchor_x="center", anchor_y="center")
        
        # Character name with shadow
        player_color = PLAYER_COLORS[self.current_player_idx]
        self.renderer.draw_text(self.temp_character.name, self.width // 2 + 3, self.height // 2 - 53,
                               "Arial", 64, (0, 0, 0), anchor_x="center", anchor_y="center")
        self.renderer.draw_text(self.temp_character.name, self.width // 2, self.height // 2 - 50,
                               "Arial", 64, player_color, anchor_x="center", anchor_y="center")
        
        # Race and class
        desc_text = f"{self.temp_character.race} {self.temp_character.char_class}"
        self.renderer.draw_text(desc_text, self.width // 2, self.height // 2 + 30,
                               "Arial", 42, (220, 220, 220), anchor_x="center", anchor_y="center")
        
        # Finish button
        proceed_rect = (self.width // 2 - 150, self.height - 120, 300, 80)
        self.renderer.draw_rect((100, 200, 100), proceed_rect)
        self.renderer.draw_rect((150, 255, 150), proceed_rect, width=4)
        self.renderer.draw_text("Finish", self.width // 2, self.height - 80,
                               "Arial", 32, Colors.WHITE, anchor_x="center", anchor_y="center")
    
    def _draw_hover_indicators(self):
        """Draw circular progress indicators for hover states"""
        current_time = time.time()
        
        for key, state in self.hover_states.items():
            hover_duration = current_time - state["start_time"]
            progress = min(1.0, hover_duration / HOVER_TIME_THRESHOLD)
            pos = state["pos"]
            self.renderer.draw_circular_progress(pos, 25, progress, Colors.ACCENT, thickness=6)

