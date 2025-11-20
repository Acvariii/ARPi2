import pygame
import time
from typing import List, Dict, Optional, Callable, Tuple

from config import PLAYER_COLORS, Colors
from player_panel import calculate_all_panels
from ui_components import HoverButton, RotatedText

from dnd.character import Character, RACES, CLASSES, ALIGNMENTS, ABILITY_SCORES, CLASS_SKILLS
from dnd.game_logic import DiceRoller, CombatManager, SkillChecker
from dnd.drawing import CharacterSheetDrawer, DiceVisualizer, CombatDisplay


class DnDGame:
    
    def __init__(self, screen: pygame.Surface, fingertip_callback: Callable):
        self.screen = screen
        self.get_fingertips = fingertip_callback
        self.screen_size = screen.get_size()
        
        self.characters = [None] * 8
        self.active_players: List[int] = []
        self.dm_player = 7
        
        self.panels = calculate_all_panels(self.screen_size)
        self.buttons: Dict[int, Dict[str, HoverButton]] = {}
        
        self.phase = "load_create"
        self.current_player_idx = 0
        
        self.creation_step = "name"
        self.temp_character = None
        self.input_text = ""
        self.ability_points_remaining = 27
        
        self.dice_roller = DiceRoller()
        self.combat_manager = CombatManager()
        self.char_drawer = CharacterSheetDrawer(self.screen)
        self.dice_viz = DiceVisualizer(self.screen)
        self.combat_display = CombatDisplay(self.screen)
        
        self.last_roll_result = None
        self.last_roll_time = 0
        
        self.dm_text = "Welcome to the adventure!"
        self.dm_text_scroll = 0
        
        self._init_buttons()
    
    def _init_buttons(self):
        font = pygame.font.SysFont(None, 24)
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
                
                r1 = pygame.Rect(x, y + margin, btn_w, btn_h)
                r2 = pygame.Rect(x + btn_w + gap, y + margin, btn_w, btn_h)
                r3 = pygame.Rect(x + 2 * (btn_w + gap), y + margin, btn_w, btn_h)
            
            elif panel.orientation == 180:
                info_height_frac = 0.45
                button_area_height = int(panel.rect.height * (1 - info_height_frac))
                info_area_height = int(panel.rect.height * info_height_frac)
                y = panel.rect.y + info_area_height
                x = panel.rect.x + margin
                avail_w = panel.rect.width - 2 * margin
                btn_w = (avail_w - 2 * gap) // 3
                btn_h = button_area_height - 2 * margin
                
                r1 = pygame.Rect(x, y + margin, btn_w, btn_h)
                r2 = pygame.Rect(x + btn_w + gap, y + margin, btn_w, btn_h)
                r3 = pygame.Rect(x + 2 * (btn_w + gap), y + margin, btn_w, btn_h)
            
            elif panel.orientation == 90:
                info_width_frac = 0.35
                button_area_width = int(panel.rect.width * (1 - info_width_frac))
                x = panel.rect.x
                y = panel.rect.y + margin
                avail_h = panel.rect.height - 2 * margin
                btn_h = (avail_h - 2 * gap) // 3
                btn_w = button_area_width - 2 * margin
                
                r1 = pygame.Rect(x + margin, y, btn_w, btn_h)
                r2 = pygame.Rect(x + margin, y + btn_h + gap, btn_w, btn_h)
                r3 = pygame.Rect(x + margin, y + 2 * (btn_h + gap), btn_w, btn_h)
            
            else:
                info_width_frac = 0.35
                button_area_width = int(panel.rect.width * (1 - info_width_frac))
                info_area_width = int(panel.rect.width * info_width_frac)
                x = panel.rect.x + info_area_width
                y = panel.rect.y + margin
                avail_h = panel.rect.height - 2 * margin
                btn_h = (avail_h - 2 * gap) // 3
                btn_w = button_area_width - 2 * margin
                
                r1 = pygame.Rect(x + margin, y, btn_w, btn_h)
                r2 = pygame.Rect(x + margin, y + btn_h + gap, btn_w, btn_h)
                r3 = pygame.Rect(x + margin, y + 2 * (btn_h + gap), btn_w, btn_h)
            
            self.buttons[idx] = {
                "btn1": HoverButton(r1, "Load", font, orientation=panel.orientation),
                "btn2": HoverButton(r2, "Create", font, orientation=panel.orientation),
                "btn3": HoverButton(r3, "Roll", font, orientation=panel.orientation)
            }
    
    def start_game(self, player_indices: List[int]):
        self.active_players = sorted(player_indices)
        if 7 not in self.active_players:
            self.active_players.append(7)
        
        for idx in self.active_players:
            if idx == 7:
                self.characters[idx] = Character("Dungeon Master", PLAYER_COLORS[idx])
                self.characters[idx].name = "DM"
            else:
                if Character.character_exists(idx):
                    self.characters[idx] = None
                else:
                    self.characters[idx] = None
        
        self.phase = "load_create"
        self.current_player_idx = 0
    
    def update(self, fingertip_meta: List[Dict]):
        if self.phase == "load_create":
            self._update_load_create_phase(fingertip_meta)
        elif self.phase == "character_creation":
            self._update_character_creation(fingertip_meta)
        elif self.phase == "playing":
            self._update_playing_phase(fingertip_meta)
    
    def _update_load_create_phase(self, fingertip_meta: List[Dict]):
        for idx in self.active_players:
            if idx == 7:
                continue
            
            buttons = self.buttons[idx]
            has_save = Character.character_exists(idx)
            
            if buttons["btn1"].update(fingertip_meta, enabled=has_save):
                self.characters[idx] = Character.load_from_file(idx)
                buttons["btn1"].reset()
            
            if buttons["btn2"].update(fingertip_meta):
                self._start_character_creation(idx)
                buttons["btn2"].reset()
        
        all_ready = all(self.characters[i] is not None for i in self.active_players if i != 7)
        if all_ready:
            self.phase = "playing"
    
    def _start_character_creation(self, player_idx: int):
        self.current_player_idx = player_idx
        self.temp_character = Character("", PLAYER_COLORS[player_idx])
        self.creation_step = "name"
        self.input_text = ""
        self.ability_points_remaining = 27
        self.phase = "character_creation"
    
    def _update_character_creation(self, fingertip_meta: List[Dict]):
        idx = self.current_player_idx
        buttons = self.buttons[idx]
        
        if self.creation_step == "name":
            buttons["btn1"].text = "Next"
            if buttons["btn1"].update(fingertip_meta, enabled=len(self.input_text) > 0):
                self.temp_character.name = self.input_text
                self.creation_step = "race"
                buttons["btn1"].reset()
        
        elif self.creation_step == "race":
            buttons["btn1"].text = "Prev"
            buttons["btn2"].text = "Next"
            if buttons["btn1"].update(fingertip_meta):
                self.creation_step = "name"
                buttons["btn1"].reset()
            if buttons["btn2"].update(fingertip_meta, enabled=self.temp_character.race != ""):
                self.creation_step = "class"
                buttons["btn2"].reset()
        
        elif self.creation_step == "class":
            buttons["btn1"].text = "Prev"
            buttons["btn2"].text = "Next"
            if buttons["btn1"].update(fingertip_meta):
                self.creation_step = "race"
                buttons["btn1"].reset()
            if buttons["btn2"].update(fingertip_meta, enabled=self.temp_character.char_class != ""):
                self.creation_step = "abilities"
                buttons["btn2"].reset()
        
        elif self.creation_step == "abilities":
            buttons["btn1"].text = "Prev"
            buttons["btn2"].text = "Next"
            if buttons["btn1"].update(fingertip_meta):
                self.creation_step = "class"
                buttons["btn1"].reset()
            if buttons["btn2"].update(fingertip_meta, enabled=self.ability_points_remaining == 0):
                self.temp_character.skills = CLASS_SKILLS.get(self.temp_character.char_class, [])
                self.temp_character.calculate_hp()
                self.temp_character.calculate_ac()
                self.creation_step = "alignment"
                buttons["btn2"].reset()
        
        elif self.creation_step == "alignment":
            buttons["btn1"].text = "Prev"
            buttons["btn2"].text = "Finish"
            if buttons["btn1"].update(fingertip_meta):
                self.creation_step = "abilities"
                buttons["btn1"].reset()
            if buttons["btn2"].update(fingertip_meta, enabled=self.temp_character.alignment != ""):
                self.characters[idx] = self.temp_character
                self.characters[idx].save_to_file(idx)
                self.temp_character = None
                self.phase = "load_create"
                buttons["btn2"].reset()
    
    def _update_playing_phase(self, fingertip_meta: List[Dict]):
        for idx in self.active_players:
            buttons = self.buttons[idx]
            
            buttons["btn1"].text = "Sheet"
            buttons["btn2"].text = "Roll"
            buttons["btn3"].text = "Action"
            
            if buttons["btn2"].update(fingertip_meta, enabled=idx != 7):
                roll = self.dice_roller.roll_d20()
                self.last_roll_result = {"player": idx, "value": roll, "modifier": 0}
                self.last_roll_time = time.time()
                buttons["btn2"].reset()
    
    def draw(self):
        self.screen.fill((25, 35, 25))
        
        self._draw_center_area()
        self._draw_panels()
        
        if self.last_roll_result and time.time() - self.last_roll_time < 3:
            center = (self.screen_size[0] // 2, self.screen_size[1] // 2)
            self.dice_viz.draw_d20_roll(center, self.last_roll_result["value"], 
                                        self.last_roll_result["modifier"])
        
        self._draw_cursors()
    
    def _draw_center_area(self):
        w, h = self.screen_size
        horizontal_panel_height = int(h * 0.10)
        vertical_panel_width = int(w * 0.12)
        margin = 20
        
        center_width = w - (2 * vertical_panel_width) - (2 * margin)
        center_height = h - (2 * horizontal_panel_height) - (2 * margin)
        center_x = vertical_panel_width + margin
        center_y = horizontal_panel_height + margin
        
        center_rect = pygame.Rect(center_x, center_y, center_width, center_height)
        pygame.draw.rect(self.screen, (40, 50, 40), center_rect, border_radius=10)
        pygame.draw.rect(self.screen, (200, 180, 100), center_rect, 3, border_radius=10)
        
        if self.phase == "playing":
            font_title = pygame.font.SysFont("Arial", 24, bold=True)
            font_text = pygame.font.SysFont("Arial", 16)
            
            title = font_title.render("D&D Adventure", True, (220, 200, 150))
            self.screen.blit(title, (center_rect.centerx - title.get_width()//2, center_rect.y + 20))
            
            text_area = pygame.Rect(center_rect.x + 20, center_rect.y + 60, 
                                    center_rect.width - 40, center_rect.height - 100)
            
            words = self.dm_text.split()
            lines = []
            current_line = ""
            
            for word in words:
                test_line = f"{current_line} {word}".strip()
                if font_text.size(test_line)[0] <= text_area.width:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)
            
            y_offset = text_area.y
            for line in lines:
                text_surf = font_text.render(line, True, Colors.WHITE)
                self.screen.blit(text_surf, (text_area.x, y_offset))
                y_offset += font_text.get_linesize() + 5
        
        elif self.phase == "load_create":
            font = pygame.font.SysFont("Arial", 28, bold=True)
            text = font.render("Load or Create Your Character", True, (220, 200, 150))
            self.screen.blit(text, (center_rect.centerx - text.get_width()//2, center_rect.centery))
    
    def _draw_panels(self):
        for idx in range(8):
            panel = self.panels[idx]
            is_active = idx in self.active_players
            
            if is_active:
                if idx == 7:
                    pygame.draw.rect(self.screen, (180, 150, 50), panel.rect, border_radius=8)
                    pygame.draw.rect(self.screen, (255, 215, 0), panel.rect, 3, border_radius=8)
                    
                    font = pygame.font.SysFont("Arial", 20, bold=True)
                    label = font.render("DUNGEON MASTER", True, (255, 215, 0))
                    if panel.orientation != 0:
                        label = pygame.transform.rotate(label, panel.orientation)
                    label_rect = label.get_rect(center=panel.rect.center)
                    self.screen.blit(label, label_rect)
                else:
                    character = self.characters[idx]
                    if character and character.name:
                        panel.draw_background(self.screen, False)
                        self._draw_character_info(idx, panel)
                    else:
                        panel.draw_background(self.screen, False)
                        
                        if self.phase == "load_create":
                            for btn in self.buttons[idx].values():
                                btn.draw(self.screen)
                        elif self.phase == "character_creation" and idx == self.current_player_idx:
                            self._draw_creation_ui(panel)
                        elif self.phase == "playing":
                            for btn in self.buttons[idx].values():
                                btn.draw(self.screen)
            else:
                washed = tuple(min(255, int(c * 0.3 + 60 * 0.7)) for c in panel.color)
                pygame.draw.rect(self.screen, washed, panel.rect, border_radius=8)
                pygame.draw.rect(self.screen, (40, 40, 40), panel.rect, width=1, border_radius=8)
    
    def _draw_character_info(self, idx: int, panel):
        character = self.characters[idx]
        font = pygame.font.SysFont("Arial", 16, bold=True)
        font_small = pygame.font.SysFont("Arial", 12)
        
        if panel.orientation == 0:
            info_rect = pygame.Rect(panel.rect.x + 10, panel.rect.y + 10,
                                   panel.rect.width - 20, int(panel.rect.height * 0.35))
            RotatedText.draw_block(self.screen, [
                (character.name, font, character.player_color),
                (f"{character.race} {character.char_class}", font_small, Colors.WHITE),
                (f"HP: {character.current_hp}/{character.max_hp}", font_small, Colors.WHITE)
            ], info_rect, panel.orientation, line_spacing=12)
        elif panel.orientation == 180:
            info_height = int(panel.rect.height * 0.45)
            info_rect = pygame.Rect(panel.rect.x + 10, panel.rect.y + 10,
                                   panel.rect.width - 20, info_height - 20)
            RotatedText.draw_block(self.screen, [
                (character.name, font, character.player_color),
                (f"{character.race} {character.char_class}", font_small, Colors.WHITE),
                (f"HP: {character.current_hp}/{character.max_hp}", font_small, Colors.WHITE)
            ], info_rect, panel.orientation, line_spacing=12)
        elif panel.orientation == 90:
            info_width_frac = 0.35
            button_area_width = int(panel.rect.width * (1 - info_width_frac))
            info_width = int(panel.rect.width * info_width_frac)
            info_rect = pygame.Rect(panel.rect.x + button_area_width, panel.rect.y + 10,
                                   info_width - 10, panel.rect.height - 20)
            RotatedText.draw_block(self.screen, [
                (character.name, font, character.player_color),
                (f"{character.race} {character.char_class}", font_small, Colors.WHITE),
                (f"HP:{character.current_hp}/{character.max_hp}", font_small, Colors.WHITE)
            ], info_rect, panel.orientation, line_spacing=16)
        else:
            info_width = int(panel.rect.width * 0.35)
            info_rect = pygame.Rect(panel.rect.x + 10, panel.rect.y + 10,
                                   info_width - 10, panel.rect.height - 20)
            RotatedText.draw_block(self.screen, [
                (character.name, font, character.player_color),
                (f"{character.race} {character.char_class}", font_small, Colors.WHITE),
                (f"HP:{character.current_hp}/{character.max_hp}", font_small, Colors.WHITE)
            ], info_rect, panel.orientation, line_spacing=16)
        
        if self.phase == "playing":
            for btn in self.buttons[idx].values():
                btn.draw(self.screen)
    
    def _draw_creation_ui(self, panel):
        overlay = pygame.Surface(panel.rect.size, pygame.SRCALPHA)
        overlay.fill((10, 10, 20, 240))
        self.screen.blit(overlay, panel.rect)
        
        font_title = pygame.font.SysFont("Arial", 18, bold=True)
        font_text = pygame.font.SysFont("Arial", 14)
        
        content_rect = pygame.Rect(panel.rect.x + 10, panel.rect.y + 10,
                                   panel.rect.width - 20, panel.rect.height - 80)
        
        if self.creation_step == "name":
            lines = [
                ("Enter Name:", font_title, (255, 215, 0)),
                (self.input_text + "_", font_text, Colors.WHITE)
            ]
        elif self.creation_step == "race":
            lines = [("Select Race:", font_title, (255, 215, 0))]
            for race in RACES:
                color = (100, 255, 100) if self.temp_character.race == race else Colors.WHITE
                lines.append((race, font_text, color))
        elif self.creation_step == "class":
            lines = [("Select Class:", font_title, (255, 215, 0))]
            for cls in CLASSES:
                color = (100, 255, 100) if self.temp_character.char_class == cls else Colors.WHITE
                lines.append((cls, font_text, color))
        elif self.creation_step == "abilities":
            lines = [
                ("Set Abilities:", font_title, (255, 215, 0)),
                (f"Points: {self.ability_points_remaining}", font_text, (255, 215, 0))
            ]
            for ability, score in self.temp_character.abilities.items():
                lines.append((f"{ability}: {score}", font_text, Colors.WHITE))
        elif self.creation_step == "alignment":
            lines = [("Select Alignment:", font_title, (255, 215, 0))]
            for alignment in ALIGNMENTS[:6]:
                color = (100, 255, 100) if self.temp_character.alignment == alignment else Colors.WHITE
                lines.append((alignment, font_text, color))
        else:
            lines = []
        
        RotatedText.draw_block(self.screen, lines, content_rect, panel.orientation, 
                             line_spacing=14, wrap=False)
        
        for btn in self.buttons[self.current_player_idx].values():
            btn.draw(self.screen)
    
    def _draw_cursors(self):
        from ui_components import draw_cursor
        
        fingertips = self.get_fingertips(*self.screen_size)
        for meta in fingertips:
            pos = meta["pos"]
            
            closest_color = Colors.WHITE
            min_dist = float('inf')
            
            for idx in self.active_players:
                panel = self.panels[idx]
                center = panel.rect.center
                dist = ((pos[0] - center[0])**2 + (pos[1] - center[1])**2)**0.5
                if dist < min_dist:
                    min_dist = dist
                    closest_color = PLAYER_COLORS[idx]
            
            draw_cursor(self.screen, pos, closest_color)
    
    def handle_text_input(self, event):
        if self.phase == "character_creation" and self.creation_step == "name":
            if event.key == pygame.K_BACKSPACE:
                self.input_text = self.input_text[:-1]
            elif event.key == pygame.K_RETURN:
                pass
            elif len(self.input_text) < 20:
                self.input_text += event.unicode
