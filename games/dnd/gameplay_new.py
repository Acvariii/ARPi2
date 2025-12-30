"""
D&D Game with Beautiful Character Creator
Combines the visual character creation with full gameplay
"""

import time
import random
import math
import os
from typing import List, Dict, Tuple, Optional
from core.renderer import PygletRenderer
from core.player_selection import PlayerSelectionUI
from core.ui_components import calculate_all_panels, PygletButton
from config import PLAYER_COLORS, Colors, HOVER_TIME_THRESHOLD
from games.dnd.models import Character, Enemy, CLASSES, RACES, generate_character_name, CLASS_SKILLS
from games.dnd.logic import DiceRoller, CombatManager, SkillChecker
from games.dnd.data import MONSTERS, ITEMS, SPELLS, DIFFICULTY_CLASSES, XP_THRESHOLDS, AI_BACKGROUND_PROMPTS
from games.dnd.ui_new import (DnDCharacterCreator, DnDPlayerPanel, DnDActionButton, 
                               DnDCharacterSheet, DnDCombatTracker, DnDDiceRollDisplay, 
                               DnDDMControlPanel, draw_status_condition, draw_damage_number)


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


class OrientedButton:
    """Button that can be rotated for different player positions"""
    def __init__(self, x: int, y: int, width: int, height: int, text: str, orientation: int, color: Tuple[int, int, int] = (80, 120, 200)):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.text = text
        self.orientation = orientation
        self.color = color
        self.hovering = False
        self.hover_start = 0.0
    
    def contains_point(self, px: int, py: int) -> bool:
        """Check if point is inside button"""
        return self.x <= px <= self.x + self.width and self.y <= py <= self.y + self.height
    
    def update(self, fingertips: List[Dict], current_time: float) -> bool:
        """Returns True if button was clicked"""
        self.hovering = False
        for tip in fingertips:
            if isinstance(tip, dict) and "pos" in tip:
                if self.contains_point(tip["pos"][0], tip["pos"][1]):
                    self.hovering = True
                    if self.hover_start == 0:
                        self.hover_start = current_time
                    elif current_time - self.hover_start >= HOVER_TIME_THRESHOLD:
                        self.hover_start = 0
                        return True
                    break
        if not self.hovering:
            self.hover_start = 0
        return False
    
    def draw(self, renderer: PygletRenderer, current_time: float):
        """Draw button with proper orientation"""
        # Background
        renderer.draw_rect(self.color, (self.x, self.y, self.width, self.height))
        renderer.draw_rect(Colors.WHITE, (self.x, self.y, self.width, self.height), width=2)
        
        # Hover progress
        if self.hovering and self.hover_start > 0:
            progress = min(1.0, (current_time - self.hover_start) / HOVER_TIME_THRESHOLD)
            bar_height = int(self.height * progress)
            renderer.draw_rect(Colors.ACCENT, (self.x, self.y + self.height - bar_height, self.width, bar_height))
        
        # Text (rotated based on orientation)
        cx = self.x + self.width // 2
        cy = self.y + self.height // 2
        renderer.draw_text(
            self.text, cx, cy,
            font_size=16, color=Colors.WHITE,
            anchor_x='center', anchor_y='center',
            rotation=self.orientation
        )


# Old CharacterCreator removed - now using DnDCharacterCreator from ui_new.py


class DnDGameSession:
    """Complete D&D game session with beautiful character creation"""
    
    def __init__(self, width: int, height: int, renderer: PygletRenderer):
        self.width = width
        self.height = height
        self.renderer = renderer
        
        # Game state
        self.state = "player_select"  # player_select, char_creation, gameplay, combat
        self.selection_ui = PlayerSelectionUI(width, height)
        
        # Players and characters
        self.active_players: List[int] = []
        self.characters: Dict[int, Character] = {}
        self.character_creators: Dict[int, DnDCharacterCreator] = {}
        self.dm_player_idx: Optional[int] = None

        # Web-UI-driven flow flags
        # - web_ui_only_player_select already exists and disables in-window selection.
        # - web_ui_only_char_creation disables the in-window touch character creator.
        self.web_ui_only_char_creation = False
        
        # Panels
        self.panels = {}
        self.player_panels = {}
        
        # Combat
        self.combat_manager = CombatManager()
        self.enemies: List[Enemy] = []
        self.in_combat = False
        
        # UI
        self.char_sheets = {}
        self.dm_panel = None
        self.dice_display = DnDDiceRollDisplay()
        
        # Animation
        self.animation_time = 0.0
        self.damage_numbers = []
    
    def _calculate_cards(self, px: int, py: int, pw: int, ph: int, num_cards: int) -> List[Tuple[int, int, int, int]]:
        """Calculate card positions to FIT WITHIN panel, stack based on orientation"""
        margin = 10
        spacing = 8
        title_space = 25  # Space for title
        
        # Determine if we need horizontal or vertical stacking
        if self.panel.orientation in [90, 270]:  # Side panels - stack vertically
            # Cards stack vertically
            card_width = pw - 2 * margin
            available_h = ph - 2 * margin - title_space
            card_height = (available_h - (num_cards - 1) * spacing) // num_cards
            # Clamp card height
            card_height = max(40, min(card_height, 80))
            
            cards = []
            total_height = num_cards * card_height + (num_cards - 1) * spacing
            start_y = py + title_space + (available_h - total_height) // 2
            for i in range(num_cards):
                card_y = start_y + i * (card_height + spacing)
                card_x = px + margin
                cards.append((card_x, card_y, card_width, card_height))
        
        elif self.panel.orientation == 0:  # Bottom panel - cards near player (at bottom of panel)
            card_height = min(ph - 2 * margin - title_space, 80)
            available_w = pw - 2 * margin
            card_width = (available_w - (num_cards - 1) * spacing) // num_cards
            card_width = max(60, min(card_width, 120))
            
            cards = []
            total_width = num_cards * card_width + (num_cards - 1) * spacing
            start_x = px + (pw - total_width) // 2
            # Position cards near bottom of panel (close to bottom player)
            card_y = py + ph - margin - card_height
            for i in range(num_cards):
                card_x = start_x + i * (card_width + spacing)
                cards.append((card_x, card_y, card_width, card_height))
        
        else:  # Top panel (orientation == 180) - cards near player (at TOP of panel from app's view = bottom from their POV)
            card_height = min(ph - 2 * margin - title_space, 80)
            available_w = pw - 2 * margin
            card_width = (available_w - (num_cards - 1) * spacing) // num_cards
            card_width = max(60, min(card_width, 120))
            
            cards = []
            total_width = num_cards * card_width + (num_cards - 1) * spacing
            start_x = px + (pw - total_width) // 2
            # Position cards at TOP of panel from app's view (near top player from their perspective)
            card_y = py + margin + title_space
            for i in range(num_cards):
                card_x = start_x + i * (card_width + spacing)
                cards.append((card_x, card_y, card_width, card_height))
        
        return cards
    
    def update(self, dt: float):
        """Update particles and rolling animation"""
        self.particles = [p for p in self.particles if p.update(dt)]
        
        # Spawn particles when selected
        if random.random() < 0.3 and self.selected_race:
            theme = self.RACE_THEMES.get(self.selected_race, self.RACE_THEMES["Human"])
            color = theme["particle_color"]
            x, y, w, h = self.panel.rect
            center_x = x + w // 2
            center_y = y + h // 2
            angle = random.random() * math.pi * 2
            speed = random.randint(30, 60)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            self.particles.append(PygletParticle(
                center_x, center_y, vx, vy, color, random.uniform(1.0, 2.0)
            ))
        
        # Rolling animation
        if self.rolling_stats:
            self.roll_timer += dt
            if self.roll_timer >= 1.5:
                self.finalize_character()
                self.rolling_stats = False
                self.stage = "done"
    
    def handle_input(self, fingertips: List[Dict], current_time: float) -> bool:
        """Handle input with hoverable CARDS"""
        if self.stage == "race":
            # Check hover on race cards
            for i, (cx, cy, cw, ch) in enumerate(self.race_cards):
                if i >= len(RACES):
                    break
                    
                race_name = RACES[i]
                hovering = False
                for tip in fingertips:
                    if isinstance(tip, dict) and "pos" in tip:
                        px, py = tip["pos"]
                        if cx <= px <= cx + cw and cy <= py <= cy + ch:
                            hovering = True
                            if race_name not in self.race_hover_states:
                                self.race_hover_states[race_name] = current_time
                            elif current_time - self.race_hover_states[race_name] >= HOVER_TIME_THRESHOLD:
                                # Race selected!
                                self.selected_race = race_name
                                self.stage = "class"
                                self.race_hover_states.clear()
                                return False
                            break
                
                if not hovering and race_name in self.race_hover_states:
                    del self.race_hover_states[race_name]
        
        elif self.stage == "class":
            # Check hover on class cards
            for i, (cx, cy, cw, ch) in enumerate(self.class_cards):
                if i >= len(CLASSES):
                    break
                    
                class_name = CLASSES[i]
                hovering = False
                for tip in fingertips:
                    if isinstance(tip, dict) and "pos" in tip:
                        px, py = tip["pos"]
                        if cx <= px <= cx + cw and cy <= py <= cy + ch:
                            hovering = True
                            if class_name not in self.class_hover_states:
                                self.class_hover_states[class_name] = current_time
                            elif current_time - self.class_hover_states[class_name] >= HOVER_TIME_THRESHOLD:
                                # Class selected!
                                self.selected_class = class_name
                                self.stage = "rolling"
                                self.rolling_stats = True
                                self.roll_timer = 0
                                self.class_hover_states.clear()
                                return False
                            break
                
                if not hovering and class_name in self.class_hover_states:
                    del self.class_hover_states[class_name]
        
        return self.ready
    
    def finalize_character(self):
        """Create the final character"""
        race = self.selected_race
        char_class = self.selected_class
        char = Character(generate_character_name(race, char_class), self.player_color)
        char.race = race
        char.char_class = char_class
        char.level = 1
        char.alignment = "Neutral Good"
        
        # Roll ability scores
        for ability in char.abilities:
            char.abilities[ability] = DiceRoller.roll_ability_score()
        
        char.calculate_hp()
        char.calculate_ac()
        char.skills = CLASS_SKILLS.get(char.char_class, [])[:2]
        char.inventory = ["Backpack", "Rope (50ft)", "Torch (x5)"]
        char.gold = 100
        
        self.character = char
        self.ready = True
        return char
    
    def draw(self, renderer: PygletRenderer, current_time: float):
        """Draw character creation with hoverable CARDS (like rendering.py)"""
        x, y, w, h = self.panel.rect
        
        # Particles
        for particle in self.particles:
            particle.draw(renderer)
        
        if self.stage == "race":
            # Race selection title
            self.panel.draw_text_oriented(renderer, "Choose Your Race", 0.5, 0.02, 14, (255, 255, 220))
            
            # Get rotation for card content
            card_rotation = self.panel.orientation
            
            # Draw race cards
            for i, (cx, cy, cw, ch) in enumerate(self.race_cards):
                if i >= len(RACES):
                    break
                
                race_name = RACES[i]
                race_theme = self.RACE_THEMES[race_name]
                is_selected = race_name == self.selected_race
                is_hovered = race_name in self.race_hover_states
                
                # Card background with glow
                if is_selected or is_hovered:
                    glow_color = race_theme["accent"]
                    renderer.draw_rect(glow_color, (cx - 2, cy - 2, cw + 4, ch + 4))
                
                card_color = race_theme["bg_colors"][0]
                if is_hovered:
                    card_color = tuple(min(255, c + 30) for c in card_color)
                renderer.draw_rect(card_color, (cx, cy, cw, ch))
                renderer.draw_rect(race_theme["accent"], (cx, cy, cw, ch), width=2)
                
                # Scale text based on card size
                icon_size = max(16, min(28, ch // 3))
                text_size = max(8, min(12, ch // 6))
                
                # Calculate card center for text positioning
                card_center_x = cx + cw // 2
                card_center_y = cy + ch // 2
                
                # Position text and emoji - emoji BELOW text for all orientations
                # Use card dimensions to create proper spacing
                if self.panel.orientation in [90, 270]:  # Vertical panels
                    spacing = cw // 6
                else:  # Horizontal panels
                    spacing = ch // 6
                
                # For all orientations, text at positive offset, emoji at negative offset
                # The rotation will handle the visual appearance
                text_y = card_center_y + spacing
                emoji_y = card_center_y - spacing
                
                # Draw text
                renderer.draw_text(race_name, card_center_x, text_y, 
                                 font_size=text_size, color=Colors.WHITE,
                                 anchor_x='center', anchor_y='center', rotation=card_rotation)
                
                # Draw emoji
                renderer.draw_text(race_theme["icon"], card_center_x, emoji_y, 
                                 font_size=icon_size, color=race_theme["accent"],
                                 anchor_x='center', anchor_y='center', rotation=card_rotation)
                
                # Hover progress bar
                if is_hovered:
                    hover_progress = min(1.0, (current_time - self.race_hover_states[race_name]) / HOVER_TIME_THRESHOLD)
                    bar_w = int(cw * hover_progress)
                    renderer.draw_rect(Colors.ACCENT, (cx, cy + ch - 3, bar_w, 3))
        
        elif self.stage == "class":
            # Class selection title
            self.panel.draw_text_oriented(renderer, "Choose Your Class", 0.5, 0.02, 14, (255, 255, 220))
            
            # Get rotation for card content
            card_rotation = self.panel.orientation
            
            # Draw class cards
            for i, (cx, cy, cw, ch) in enumerate(self.class_cards):
                if i >= len(CLASSES):
                    break
                
                class_name = CLASSES[i]
                class_theme = self.CLASS_THEMES[class_name]
                is_selected = class_name == self.selected_class
                is_hovered = class_name in self.class_hover_states
                
                # Card background with glow
                if is_selected or is_hovered:
                    glow_color = class_theme["accent"]
                    renderer.draw_rect(glow_color, (cx - 2, cy - 2, cw + 4, ch + 4))
                
                card_color = class_theme["bg_colors"][0]
                if is_hovered:
                    card_color = tuple(min(255, c + 30) for c in card_color)
                renderer.draw_rect(card_color, (cx, cy, cw, ch))
                renderer.draw_rect(class_theme["accent"], (cx, cy, cw, ch), width=2)
                
                # Scale text based on card size
                icon_size = max(16, min(28, ch // 3))
                text_size = max(8, min(12, ch // 6))
                
                # Calculate card center for text positioning
                card_center_x = cx + cw // 2
                card_center_y = cy + ch // 2
                
                # Position text and emoji - emoji BELOW text for all orientations
                # Use card dimensions to create proper spacing
                if self.panel.orientation in [90, 270]:  # Vertical panels
                    spacing = cw // 6
                else:  # Horizontal panels
                    spacing = ch // 6
                
                # For all orientations, text at positive offset, emoji at negative offset
                # The rotation will handle the visual appearance
                text_y = card_center_y + spacing
                emoji_y = card_center_y - spacing
                
                # Draw text
                renderer.draw_text(class_name, card_center_x, text_y, 
                                 font_size=text_size, color=Colors.WHITE,
                                 anchor_x='center', anchor_y='center', rotation=card_rotation)
                
                # Draw emoji
                renderer.draw_text(class_theme["symbol"], card_center_x, emoji_y, 
                                 font_size=icon_size, color=class_theme["accent"],
                                 anchor_x='center', anchor_y='center', rotation=card_rotation)
                
                # Hover progress bar
                if is_hovered:
                    hover_progress = min(1.0, (current_time - self.class_hover_states[class_name]) / HOVER_TIME_THRESHOLD)
                    bar_w = int(cw * hover_progress)
                    renderer.draw_rect(Colors.ACCENT, (cx, cy + ch - 3, bar_w, 3))
        
        elif self.stage == "rolling":
            # Rolling stats animation
            theme = self.RACE_THEMES.get(self.selected_race if self.selected_race else "Human", self.RACE_THEMES["Human"])
            self.panel.draw_text_oriented(renderer, "Rolling Stats...", 0.5, 0.5, 20, theme["accent"])
            dots = "." * (int(self.roll_timer * 3) % 4)
            self.panel.draw_text_oriented(renderer, dots, 0.5, 0.4, 28, Colors.WHITE)
        
        elif self.stage == "done":
            # Show final character
            if self.character:
                theme = self.RACE_THEMES.get(self.selected_race if self.selected_race else "Human", self.RACE_THEMES["Human"])
                char = self.character
                self.panel.draw_text_oriented(renderer, char.name, 0.5, 0.5, 24, theme["accent"])
                self.panel.draw_text_oriented(renderer, f"{char.race} {char.char_class}", 0.5, 0.4, 18, Colors.WHITE)
                self.panel.draw_text_oriented(renderer, f"Level {char.level}", 0.5, 0.3, 16, (200, 200, 200))
                self.panel.draw_text_oriented(renderer, "Ready!", 0.5, 0.2, 20, (100, 255, 100))


class DnDGameSession:
    """Complete D&D game session with beautiful character creation"""
    
    def __init__(self, width: int, height: int, renderer: PygletRenderer):
        self.width = width
        self.height = height
        self.renderer = renderer
        
        # Game state
        self.state = "player_select"  # player_select, char_creation, gameplay, combat
        self.selection_ui = PlayerSelectionUI(width, height)
        
        # Players and characters
        self.active_players: List[int] = []
        self.characters: Dict[int, Character] = {}
        self.character_creators: Dict[int, DnDCharacterCreator] = {}
        self.dm_player_idx = None  # Player 8 (index 7)
        
        # Panels
        self.panels = {}
        self.player_panels = {}
        
        # Combat
        self.combat_manager = CombatManager()
        self.enemies: List[Enemy] = []
        self.in_combat = False
        
        # UI
        self.char_sheets = {}
        self.dm_panel = None
        self.dice_display = DnDDiceRollDisplay()
        
        # Animation
        self.animation_time = 0.0
        self.damage_numbers = []
    
    def start_game(self, selected_players: List[int]):
        """Initialize game"""
        self.active_players = selected_players

        # DM is chosen externally (e.g., via Web UI). If the chosen DM is not in the
        # selected players, clear it.
        if self.dm_player_idx is not None and self.dm_player_idx not in selected_players:
            self.dm_player_idx = None
        
        # Setup panels
        all_panels = calculate_all_panels(self.width, self.height)
        for i in self.active_players:
            panel = all_panels[i]
            self.player_panels[i] = panel
            x, y, w, h = panel.rect
            self.panels[i] = {"x": x, "y": y, "width": w, "height": h, "orientation": panel.orientation}
        
        # Move to character creation
        self.state = "char_creation"
        if not getattr(self, "web_ui_only_char_creation", False):
            self._init_character_creators()

    def handle_player_quit(self, seat: int) -> None:
        """Handle a player disconnecting mid-session.

        D&D character creation/gameplay can become stuck if we keep waiting on a
        seat's character inputs. We drop the seat from `active_players` and clear
        any per-seat state.
        """
        try:
            s = int(seat)
        except Exception:
            return

        if s not in (self.active_players or []):
            return

        try:
            self.active_players = [int(x) for x in (self.active_players or []) if int(x) != s]
        except Exception:
            self.active_players = [x for x in (self.active_players or []) if x != s]

        try:
            self.characters.pop(int(s), None)
            self.character_creators.pop(int(s), None)
            self.player_panels.pop(int(s), None)
            self.panels.pop(int(s), None)
        except Exception:
            pass

        if self.dm_player_idx is not None and int(self.dm_player_idx) == s:
            self.dm_player_idx = None

        if not self.active_players:
            self.state = "player_select"
            try:
                if hasattr(self, "selection_ui"):
                    self.selection_ui.reset()
            except Exception:
                pass
            return

        # If we are in char creation, re-check if we can advance.
        try:
            self.maybe_advance_from_char_creation()
        except Exception:
            pass

    def set_dm_player_idx(self, player_idx: Optional[int]) -> None:
        try:
            if player_idx is None:
                self.dm_player_idx = None
                return
            pidx = int(player_idx)
        except Exception:
            return
        if 0 <= pidx <= 7:
            self.dm_player_idx = pidx

    def set_character(self, player_idx: int, character: Character) -> None:
        try:
            pidx = int(player_idx)
        except Exception:
            return
        if not (0 <= pidx <= 7):
            return
        if self.dm_player_idx is not None and pidx == self.dm_player_idx:
            # DM doesn't need a character
            return
        self.characters[pidx] = character

    def maybe_advance_from_char_creation(self) -> None:
        if self.state != "char_creation":
            return
        if not self.active_players:
            return
        for player_idx in self.active_players:
            if self.dm_player_idx is not None and player_idx == self.dm_player_idx:
                continue
            if player_idx not in self.characters:
                return
        self.state = "gameplay"
        self._setup_gameplay_ui()
    
    def _init_character_creators(self):
        """Initialize character creators for non-DM players"""
        for player_idx in self.active_players:
            if player_idx == self.dm_player_idx:
                # DM doesn't need a character
                continue
            
            # Create character creator using new UI system with DnDPlayerPanel
            panel = DnDPlayerPanel(player_idx, self.width, self.height)
            creator = DnDCharacterCreator(panel, player_idx, PLAYER_COLORS[player_idx % len(PLAYER_COLORS)])
            self.character_creators[player_idx] = creator
    
    def handle_input(self, fingertips: List[Dict]) -> bool:
        """Handle input"""
        try:
            if 'ESC' in fingertips:
                if self.state == "player_select":
                    return True
                else:
                    self._show_exit_confirm()
                return False
            
            current_time = time.time()
            
            if self.state == "player_select":
                # Web UI drives player selection; disable hover/tap selection in the game window.
                if not getattr(self, "web_ui_only_player_select", False):
                    self._handle_player_select(fingertips)
            elif self.state == "char_creation":
                if not getattr(self, "web_ui_only_char_creation", False):
                    self._handle_char_creation(fingertips, current_time)
                else:
                    # Web UI handles character creation. Just wait.
                    self.maybe_advance_from_char_creation()
            elif self.state == "gameplay":
                self._handle_gameplay(fingertips, current_time)
            elif self.state == "combat":
                self._handle_combat(fingertips, current_time)
            
            return False
        except Exception as e:
            print(f"Error in handle_input ({self.state}): {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _handle_player_select(self, fingertips: List[Dict]):
        """Handle player selection"""
        self.selection_ui.update_with_fingertips(fingertips)
        
        if self.selection_ui.start_ready:
            selected = [i for i, s in enumerate(self.selection_ui.selected) if s]
            if len(selected) >= 2 and self.dm_player_idx is not None and self.dm_player_idx in selected:
                self.start_game(selected)
                self.selection_ui.start_ready = False
    
    def _handle_char_creation(self, fingertips: List[Dict], current_time: float):
        """Handle character creation with proper button interaction"""
        all_ready = True
        for player_idx in self.active_players:
            if player_idx == self.dm_player_idx:
                continue  # DM doesn't create character
            if player_idx not in self.characters:
                if player_idx in self.character_creators:
                    creator = self.character_creators[player_idx]
                    # Let creator handle input
                    if creator.handle_input(fingertips, current_time):
                        # Creator finished, save character
                        char = creator.character
                        if char:
                            char.save_to_file(player_idx)
                            self.characters[player_idx] = char
                            del self.character_creators[player_idx]
                    else:
                        all_ready = False
        
        if all_ready:
            self.state = "gameplay"
            self._setup_gameplay_ui()
    
    def _setup_gameplay_ui(self):
        """Setup UI for gameplay mode"""
        # Character sheets for players (not DM)
        for player_idx in self.characters:
            if player_idx in self.panels and player_idx != self.dm_player_idx:
                panel = DnDPlayerPanel(player_idx, self.width, self.height)
                self.char_sheets[player_idx] = DnDCharacterSheet(panel)
        
        # DM gets their full control panel
        if self.dm_player_idx is not None and self.dm_player_idx in self.panels:
            dm_panel_obj = DnDPlayerPanel(self.dm_player_idx, self.width, self.height)
            self.dm_panel = DnDDMControlPanel(dm_panel_obj)
    
    def _handle_gameplay(self, fingertips: List[Dict], current_time: float):
        """Handle gameplay mode"""
        # Player action buttons
        for player_idx, sheet in self.char_sheets.items():
            if player_idx in self.characters:
                action = sheet.update(fingertips, current_time)
                if action:
                    # Handle player action
                    char = self.characters[player_idx]
                    print(f"{char.name} used action: {action}")
                    # TODO: Implement action handlers (attack, cast spell, use item, defend)
        
        # DM controls
        if self.dm_panel and self.dm_player_idx is not None:
            dm_action = self.dm_panel.update(fingertips, current_time)
            if dm_action:
                self._handle_dm_action(dm_action)
    
    def _handle_combat(self, fingertips: List[Dict], current_time: float):
        """Handle combat"""
        # Similar to gameplay for now
        self._handle_gameplay(fingertips, current_time)
    
    def _handle_dm_action(self, action: str):
        """Handle DM actions"""
        if action == "spawn_enemy":
            # Spawn a random enemy directly
            monster_name = random.choice(list(MONSTERS.keys()))
            self._spawn_enemy(monster_name)
        elif action == "add_npc":
            print("Add NPC - Coming soon!")
        elif action == "change_bg":
            print("Change background - Coming soon!")
        elif action == "give_item":
            print("Give item - Coming soon!")
    

    
    def _spawn_enemy(self, monster_name: str):
        """Spawn enemy and start combat"""
        if monster_name in MONSTERS:
            enemy = Enemy(MONSTERS[monster_name])
            self.enemies.append(enemy)
            
            characters_list = list(self.characters.values())
            self.combat_manager.roll_initiative(characters_list, self.enemies)
            self.in_combat = True
            self.state = "combat"
            print(f"Combat started! {monster_name} appears!")
    
    def _show_exit_confirm(self):
        """Show exit confirmation - for now just print"""
        print("Exit requested - press ESC again to confirm")
    
    def update(self, dt: float):
        """Update game"""
        self.animation_time += dt
        self.dice_display.update(dt)
        
        # Update character creators
        for creator in self.character_creators.values():
            creator.update(dt)
    
    def draw(self):
        """Draw game"""
        self.renderer.draw_rect((20, 20, 30), (0, 0, self.width, self.height))
        
        if self.state == "player_select":
            if getattr(self, "web_ui_only_player_select", False):
                self.renderer.draw_text(
                    "Waiting for players…",
                    self.width // 2,
                    self.height // 2,
                    font_size=44,
                    color=Colors.WHITE,
                    anchor_x='center',
                    anchor_y='center'
                )
                self.renderer.draw_text(
                    "Use the Web Controller to select slots and start",
                    self.width // 2,
                    self.height // 2 + 50,
                    font_size=18,
                    color=(200, 200, 200),
                    anchor_x='center',
                    anchor_y='center'
                )
            else:
                self._draw_player_select()
        elif self.state == "char_creation":
            self._draw_char_creation()
        elif self.state == "gameplay":
            self._draw_gameplay()
        elif self.state == "combat":
            self._draw_combat()
    
    def _draw_player_select(self):
        """Draw player selection"""
        current_time = time.time()
        
        # Draw slots
        for i, slot in enumerate(self.selection_ui.slots):
            slot_x, slot_y, slot_w, slot_h = slot
            cx = slot_x + slot_w // 2
            cy = slot_y + slot_h // 2
            radius = slot_w // 2
            
            color = PLAYER_COLORS[i] if self.selection_ui.selected[i] else (80, 80, 80)
            self.renderer.draw_circle(color, (cx, cy), radius)
            self.renderer.draw_circle(Colors.WHITE, (cx, cy), radius, width=2)
            
            # Special indicator for Player 8 (DM)
            if i == 7:
                self.renderer.draw_text(
                    "DM",
                    cx, cy - 20,
                    font_size=16,
                    color=Colors.ACCENT,
                    anchor_x='center',
                    anchor_y='center'
                )
            
            self.renderer.draw_text(
                f"P{i+1}",
                cx, cy + (20 if i == 7 else 0),
                font_size=24,
                color=Colors.WHITE,
                anchor_x='center',
                anchor_y='center'
            )
        
        # Hover indicators
        for key, state in self.selection_ui.hover_states.items():
            if key.startswith("slot_"):
                slot_idx = int(key.split("_")[1])
                slot = self.selection_ui.slots[slot_idx]
                slot_x, slot_y, slot_w, slot_h = slot
                cx = slot_x + slot_w // 2
                cy = slot_y + slot_h // 2
                radius = slot_w // 2
                
                hover_duration = current_time - state["start_time"]
                progress = min(1.0, hover_duration / HOVER_TIME_THRESHOLD)
                
                pulse_size = int(5 * (1 + progress * 0.3))
                self.renderer.draw_circle(
                    Colors.ACCENT,
                    (cx, cy),
                    radius + pulse_size,
                    width=4,
                    alpha=int(255 * progress)
                )
        
        # Start button
        if self.selection_ui.selected_count() >= 2 and self.selection_ui.selected[7]:
            cx, cy = self.selection_ui.start_button_pos
            radius = self.selection_ui.start_button_radius
            
            self.renderer.draw_circle((50, 150, 50), (cx, cy), radius)
            self.renderer.draw_circle(Colors.WHITE, (cx, cy), radius, width=3)
            
            self.renderer.draw_text(
                "START",
                cx, cy,
                font_size=28,
                color=Colors.WHITE,
                anchor_x='center',
                anchor_y='center'
            )
            
            if "start_button" in self.selection_ui.hover_states:
                state = self.selection_ui.hover_states["start_button"]
                hover_duration = current_time - state["start_time"]
                progress = min(1.0, hover_duration / HOVER_TIME_THRESHOLD)
                
                pulse_size = int(8 * (1 + progress * 0.5))
                self.renderer.draw_circle(
                    Colors.ACCENT,
                    (cx, cy),
                    radius + pulse_size,
                    width=6,
                    alpha=int(255 * progress)
                )
        
        # Title
        self.renderer.draw_text(
            "D&D Game - Select Players",
            self.width // 2,
            self.height - 50,
            font_size=36,
            color=Colors.ACCENT,
            anchor_x='center',
            anchor_y='center'
        )
        
        selected_count = sum(self.selection_ui.selected)
        self.renderer.draw_text(
            f"{selected_count} players selected (Player 8 = DM)",
            self.width // 2,
            self.height - 100,
            font_size=20,
            color=Colors.WHITE,
            anchor_x='center',
            anchor_y='center'
        )
        
        self.renderer.draw_text(
            "Minimum 2 players (Need Player 8 as DM)",
            self.width // 2,
            self.height - 130,
            font_size=16,
            color=(200, 200, 200) if not self.selection_ui.selected[7] else Colors.ACCENT,
            anchor_x='center',
            anchor_y='center'
        )
    
    def _draw_char_creation(self):
        """Draw character creation"""
        current_time = time.time()
        
        # Draw panel backgrounds for all active players
        for player_idx in self.active_players:
            if player_idx in self.panels:
                # Create a DnDPlayerPanel for background drawing
                temp_panel = DnDPlayerPanel(player_idx, self.width, self.height)
                temp_panel.draw_background(self.renderer, is_current=False)
        
        # Draw all character creators
        for creator in self.character_creators.values():
            creator.draw(self.renderer, current_time)
        
        # Draw already created characters
        for player_idx, char in self.characters.items():
            if player_idx in self.panels:
                panel_data = self.panels[player_idx]
                x, y, w, h = panel_data["x"], panel_data["y"], panel_data["width"], panel_data["height"]
                
                # Simple display
                self.renderer.draw_rect((40, 40, 50), (x, y, w, h))
                self.renderer.draw_rect(PLAYER_COLORS[player_idx % len(PLAYER_COLORS)], (x, y, w, h), width=3)
                
                cx = x + w // 2
                cy = y + h // 2
                
                self.renderer.draw_text(
                    f"Player {player_idx + 1}",
                    cx, y + h - 30,
                    font_size=20,
                    color=PLAYER_COLORS[player_idx % len(PLAYER_COLORS)],
                    anchor_x='center',
                    anchor_y='center'
                )
                
                self.renderer.draw_text(
                    char.name,
                    cx, cy + 20,
                    font_size=18,
                    color=Colors.WHITE,
                    anchor_x='center',
                    anchor_y='center'
                )
                
                self.renderer.draw_text(
                    f"{char.race} {char.char_class}",
                    cx, cy - 20,
                    font_size=14,
                    color=(200, 200, 200),
                    anchor_x='center',
                    anchor_y='center'
                )
        
        # Title
        self.renderer.draw_text(
            "Creating Characters...",
            self.width // 2,
            self.height // 2,
            font_size=32,
            color=Colors.ACCENT,
            anchor_x='center',
            anchor_y='center'
        )
    
    def _draw_gameplay(self):
        """Draw gameplay"""
        # Draw panel backgrounds for all active players
        for player_idx in self.active_players:
            if player_idx in self.panels:
                # Create a DnDPlayerPanel for background drawing
                temp_panel = DnDPlayerPanel(player_idx, self.width, self.height)
                temp_panel.draw_background(self.renderer, is_current=False)
        
        # Character sheets
        for player_idx, sheet in self.char_sheets.items():
            if player_idx in self.characters:
                char = self.characters[player_idx]
                sheet.draw(self.renderer, char, PLAYER_COLORS[player_idx % len(PLAYER_COLORS)], time.time())
        
        # DM panel
        if self.dm_panel:
            self.dm_panel.draw(self.renderer, time.time())
        
        # Dice display
        self.dice_display.draw(self.renderer)
    
    def _draw_combat(self):
        """Draw combat"""
        self._draw_gameplay()  # Same for now
    
    def draw_immediate(self):
        """Draw immediate mode"""
        pass
