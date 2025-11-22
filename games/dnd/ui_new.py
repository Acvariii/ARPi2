"""
D&D UI System - Complete standalone UI with relative positioning
Does NOT use ui_components - rebuilt from scratch for D&D
All positions use percentages (0-1) within panels, not absolute pixels
"""

import time
import math
import random
from typing import List, Dict, Tuple, Optional
from core.renderer import PygletRenderer
from config import PLAYER_COLORS, Colors, HOVER_TIME_THRESHOLD


class DnDPlayerPanel:
    """
    D&D-specific player panel - completely standalone
    Uses relative positioning (0-1) for everything
    """
    
    # Panel positions matching original system
    POSITIONS = {
        0: ("bottom", 0, 0),      # Bottom left
        1: ("bottom", 1, 0),      # Bottom center
        2: ("bottom", 2, 0),      # Bottom right
        3: ("top", 0, 180),       # Top left - upside down
        4: ("top", 1, 180),       # Top center - upside down
        5: ("top", 2, 180),       # Top right - upside down
        6: ("left", 0, 270),      # Left - rotated 270
        7: ("right", 0, 90),      # Right - rotated 90
    }
    
    def __init__(self, player_idx: int, screen_width: int, screen_height: int):
        self.player_idx = player_idx
        self.width = screen_width
        self.height = screen_height
        self.color = PLAYER_COLORS[player_idx]
        
        side, slot, orientation = self.POSITIONS[player_idx]
        self.side = side
        self.slot = slot
        self.orientation = orientation
        
        self.rect = self._calculate_rect()
    
    def _calculate_rect(self) -> Tuple[int, int, int, int]:
        """Calculate panel rectangle based on position"""
        w, h = self.width, self.height
        panel_h = int(h * 0.10)
        panel_w_side = int(w * 0.12)
        
        if self.side == "bottom":
            panel_w = w // 3
            x = self.slot * panel_w
            y = h - panel_h
            return (x, y, panel_w, panel_h)
        
        elif self.side == "top":
            panel_w = w // 3
            x = self.slot * panel_w
            y = 0
            return (x, y, panel_w, panel_h)
        
        elif self.side == "left":
            x = 0
            y = panel_h
            panel_height = h - 2 * panel_h
            return (x, y, panel_w_side, panel_height)
        
        else:  # right
            x = w - panel_w_side
            y = panel_h
            panel_height = h - 2 * panel_h
            return (x, y, panel_w_side, panel_height)
    
    def draw_background(self, renderer: PygletRenderer, is_current: bool = False):
        """Draw panel background with gradient"""
        x, y, w, h = self.rect
        
        # Vibrant base color
        saturated = tuple(min(255, int(c * 1.1)) for c in self.color)
        
        # Smooth gradient
        if self.orientation in [0, 180]:  # Horizontal panels
            num_layers = 40
            for i in range(num_layers):
                layer_h = h / num_layers
                layer_y = y + i * layer_h
                
                dist_from_center = abs((i - num_layers/2) / (num_layers/2))
                position = dist_from_center * 3
                gaussian = math.exp(-(position ** 2) / 2)
                
                shine_intensity = 60 * gaussian
                shine_color = tuple(min(255, int(saturated[c] * 0.8 + shine_intensity)) for c in range(3))
                renderer.draw_rect(shine_color, (x, int(layer_y), w, int(layer_h) + 1))
        else:  # Vertical panels
            num_layers = 40
            for i in range(num_layers):
                layer_w = w / num_layers
                layer_x = x + i * layer_w
                
                dist_from_center = abs((i - num_layers/2) / (num_layers/2))
                position = dist_from_center * 3
                gaussian = math.exp(-(position ** 2) / 2)
                
                shine_intensity = 60 * gaussian
                shine_color = tuple(min(255, int(saturated[c] * 0.8 + shine_intensity)) for c in range(3))
                renderer.draw_rect(shine_color, (int(layer_x), y, int(layer_w) + 1, h))
        
        # Border
        border_color = (255, 215, 0) if is_current else (180, 190, 200)
        border_w = 4 if is_current else 2
        renderer.draw_rect(border_color, (x, y, w, h), width=border_w)
    
    def draw_text_oriented(self, renderer: PygletRenderer, text: str, 
                          rel_x: float, rel_y: float, font_size: int, color: Tuple[int, int, int]):
        """
        Draw text with proper orientation using relative positioning (0-1)
        rel_x, rel_y are percentages within the panel
        """
        x, y, w, h = self.rect
        
        # Convert relative to absolute
        tx = x + int(w * rel_x)
        ty = y + int(h * rel_y)
        
        # Adjust rotation for side panels
        rotation = self.orientation
        if self.orientation in [90, 270]:
            rotation = (rotation + 180) % 360
        
        renderer.draw_text(
            text, tx, ty,
            font_size=font_size, color=color,
            anchor_x='center', anchor_y='center',
            rotation=rotation
        )


class DnDCard:
    """Card that displays with proper orientation for any player"""
    
    def __init__(self, panel: DnDPlayerPanel, rel_x: float, rel_y: float, rel_w: float, rel_h: float):
        """
        Args:
            panel: The player panel this card belongs to
            rel_x, rel_y: Position within panel (0-1)
            rel_w, rel_h: Size relative to panel (0-1)
        """
        self.panel = panel
        self.rel_x = rel_x
        self.rel_y = rel_y
        self.rel_w = rel_w
        self.rel_h = rel_h
        
        self.hover_start = 0.0
        self.hovering = False
    
    def get_absolute_rect(self) -> Tuple[int, int, int, int]:
        """Convert relative position to absolute screen coordinates"""
        px, py, pw, ph = self.panel.rect
        
        x = int(px + pw * self.rel_x)
        y = int(py + ph * self.rel_y)
        w = int(pw * self.rel_w)
        h = int(ph * self.rel_h)
        
        return (x, y, w, h)
    
    def contains_point(self, screen_x: int, screen_y: int) -> bool:
        """Check if screen coordinates are within this card"""
        cx, cy, cw, ch = self.get_absolute_rect()
        return cx <= screen_x <= cx + cw and cy <= screen_y <= cy + ch
    
    def update(self, fingertips: List[Dict], current_time: float) -> bool:
        """Returns True if card was clicked (hovered long enough)"""
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
    
    def draw_text_in_card(self, renderer: PygletRenderer, text: str, 
                          rel_x: float, rel_y: float, font_size: int, color: Tuple[int, int, int]):
        """
        Draw text within the card using relative positioning
        rel_x, rel_y are relative to the CARD (0-1), not the panel
        
        For orientation-aware positioning:
        - 0° (bottom): rel_y=0 is bottom, rel_y=1 is top
        - 180° (top): rel_y=0 is top, rel_y=1 is bottom (from their view)
        - 270° (left): rel_x becomes their vertical axis
        - 90° (right): rel_x becomes their vertical axis
        """
        cx, cy, cw, ch = self.get_absolute_rect()
        
        # Calculate position within card
        if self.panel.orientation in [90, 270]:  # Side panels
            # For side panels, swap interpretation of x/y for their perspective
            # Their "vertical" is our horizontal (X axis)
            # Their "horizontal" is our vertical (Y axis)
            text_x = int(cx + cw * rel_y)  # Their horizontal = our Y within card
            text_y = int(cy + ch * rel_x)  # Their vertical = our X within card
        else:  # Top/bottom panels
            text_x = int(cx + cw * rel_x)
            text_y = int(cy + ch * rel_y)
        
        # Adjust rotation for side panels - they need 180° additional rotation
        rotation = self.panel.orientation
        if self.panel.orientation in [90, 270]:
            rotation = (rotation + 180) % 360
        
        renderer.draw_text(
            text, text_x, text_y,
            font_size=font_size, color=color,
            anchor_x='center', anchor_y='center',
            rotation=rotation
        )
    
    def draw_background(self, renderer: PygletRenderer, bg_color: Tuple[int, int, int], 
                       border_color: Tuple[int, int, int] = None, border_width: int = 2,
                       glow: bool = False, glow_color: Tuple[int, int, int] = None):
        """Draw card background with optional glow and border"""
        cx, cy, cw, ch = self.get_absolute_rect()
        
        # Glow effect
        if glow and glow_color:
            renderer.draw_rect(glow_color, (cx - 2, cy - 2, cw + 4, ch + 4))
        
        # Background
        renderer.draw_rect(bg_color, (cx, cy, cw, ch))
        
        # Border
        if border_color:
            renderer.draw_rect(border_color, (cx, cy, cw, ch), width=border_width)
    
    def draw_hover_progress(self, renderer: PygletRenderer, current_time: float):
        """Draw hover progress bar"""
        if self.hovering and self.hover_start > 0:
            progress = min(1.0, (current_time - self.hover_start) / HOVER_TIME_THRESHOLD)
            cx, cy, cw, ch = self.get_absolute_rect()
            
            # Progress bar at bottom of card
            bar_h = 3
            bar_w = int(cw * progress)
            renderer.draw_rect(Colors.ACCENT, (cx, cy + ch - bar_h, bar_w, bar_h))


class DnDCardGrid:
    """Grid of cards that automatically positions based on panel orientation"""
    
    def __init__(self, panel: DnDPlayerPanel, num_cards: int, margin: float = 0.05):
        """
        Args:
            panel: Player panel
            num_cards: Number of cards to display
            margin: Margin as percentage of panel size
        """
        self.panel = panel
        self.num_cards = num_cards
        self.margin = margin
        self.cards: List[DnDCard] = []
        
        self._create_cards()
    
    def _create_cards(self):
        """Create cards with proper positioning based on orientation"""
        self.cards = []
        
        spacing = 0.02  # 2% spacing between cards
        
        if self.panel.orientation in [90, 270]:  # Side panels - stack vertically
            # Cards stack from their perspective's top to bottom
            card_width = 0.70  # Reduced from full width to make room for title
            available_height = 1.0 - 2 * self.margin
            card_height = (available_height - (self.num_cards - 1) * spacing) / self.num_cards
            card_height = max(0.10, min(card_height, 0.14))  # Slightly smaller cards
            
            # Center cards horizontally
            card_x = (1.0 - card_width) / 2
            # Center cards vertically
            total_height = self.num_cards * card_height + (self.num_cards - 1) * spacing
            start_y = (1.0 - total_height) / 2
            
            for i in range(self.num_cards):
                rel_y = start_y + i * (card_height + spacing)
                card = DnDCard(self.panel, card_x, rel_y, card_width, card_height)
                self.cards.append(card)
        
        elif self.panel.orientation == 0:  # Bottom - cards near player
            # Reduced height to make room for title at top
            card_height = 0.70  # Leave room for title
            available_width = 1.0 - 2 * self.margin
            card_width = (available_width - (self.num_cards - 1) * spacing) / self.num_cards
            card_width = max(0.1, min(card_width, 0.25))
            
            total_width = self.num_cards * card_width + (self.num_cards - 1) * spacing
            start_x = (1.0 - total_width) / 2
            # Cards at bottom of panel (near player) = high Y value
            rel_y = 1.0 - self.margin - card_height
            
            for i in range(self.num_cards):
                rel_x = start_x + i * (card_width + spacing)
                card = DnDCard(self.panel, rel_x, rel_y, card_width, card_height)
                self.cards.append(card)
        
        else:  # Top panel - cards near player (which is top of panel from app view)
            # Reduced height to make room for title at their top (our bottom)
            card_height = 0.70  # Leave room for title
            available_width = 1.0 - 2 * self.margin
            card_width = (available_width - (self.num_cards - 1) * spacing) / self.num_cards
            card_width = max(0.1, min(card_width, 0.25))
            
            total_width = self.num_cards * card_width + (self.num_cards - 1) * spacing
            start_x = (1.0 - total_width) / 2
            # Cards at top of panel from app view, but leave room at bottom for title (which is their top)
            rel_y = self.margin
            
            for i in range(self.num_cards):
                rel_x = start_x + i * (card_width + spacing)
                card = DnDCard(self.panel, rel_x, rel_y, card_width, card_height)
                self.cards.append(card)


class DnDSelectionCard(DnDCard):
    """Card for race/class selection with icon and text"""
    
    def __init__(self, panel: DnDPlayerPanel, rel_x: float, rel_y: float, rel_w: float, rel_h: float,
                 name: str, icon: str, theme: Dict):
        super().__init__(panel, rel_x, rel_y, rel_w, rel_h)
        self.name = name
        self.icon = icon
        self.theme = theme
        self.selected = False
    
    def draw(self, renderer: PygletRenderer, current_time: float):
        """Draw the selection card with icon above text"""
        # Background with glow if selected or hovering
        bg_color = self.theme["bg_colors"][0]
        if self.hovering:
            bg_color = tuple(min(255, c + 30) for c in bg_color)
        
        self.draw_background(
            renderer, bg_color, 
            border_color=self.theme["accent"],
            glow=self.selected or self.hovering,
            glow_color=self.theme["accent"]
        )
        
        # For ALL orientations, text should appear above emoji from player's perspective
        # In relative card coordinates:
        # - Top player sees 0,0 at bottom-left, 1,1 at top-right (rotated 180°)
        # - Bottom player sees 0,0 at bottom-left, 1,1 at top-right (normal)
        # - Left player sees 0,0 at bottom-left, 1,1 at top-right BUT rotated 270°
        #   So their "up" is our "right" (positive X in card space)
        # - Right player sees 0,0 at bottom-left, 1,1 at top-right BUT rotated 90°
        #   So their "up" is our "left" (negative X... but we handle with rotation)
        
        # Key insight: With proper rotation, we always use the same relative positions
        # Text "higher" = larger Y value = closer to 1.0
        # Emoji "lower" = smaller Y value = closer to 0.0
        
        cx, cy, cw, ch = self.get_absolute_rect()
        icon_size = max(16, min(28, ch // 3))
        text_size = max(8, min(12, ch // 6))
        
        # Draw text higher (0.65) and emoji lower (0.35)
        self.draw_text_in_card(renderer, self.name, 0.5, 0.65, text_size, Colors.WHITE)
        self.draw_text_in_card(renderer, self.icon, 0.5, 0.35, icon_size, self.theme["accent"])
        
        # Hover progress
        self.draw_hover_progress(renderer, current_time)


class DnDCharacterCreator:
    """Character creation UI using relative positioning"""
    
    def __init__(self, panel: DnDPlayerPanel, player_idx: int, player_color: Tuple[int, int, int]):
        self.panel = panel
        self.player_idx = player_idx
        self.player_color = player_color
        
        self.stage = "race"  # race, class, rolling, done
        self.selected_race = None
        self.selected_class = None
        self.character = None
        self.rolling_stats = False
        self.roll_timer = 0.0
        
        # Race themes
        self.RACE_THEMES = {
            "Human": {"icon": "👤", "accent": (255, 215, 0), "bg_colors": [(40, 40, 60), (60, 60, 80)]},
            "Elf": {"icon": "🧝", "accent": (144, 238, 144), "bg_colors": [(20, 60, 40), (40, 80, 60)]},
            "Dwarf": {"icon": "⛏️", "accent": (205, 133, 63), "bg_colors": [(60, 40, 30), (80, 60, 50)]},
            "Orc": {"icon": "💪", "accent": (34, 139, 34), "bg_colors": [(40, 60, 30), (60, 80, 50)]},
            "Halfling": {"icon": "🌾", "accent": (255, 182, 193), "bg_colors": [(60, 50, 40), (80, 70, 60)]},
            "Tiefling": {"icon": "😈", "accent": (220, 20, 60), "bg_colors": [(60, 20, 40), (80, 40, 60)]}
        }
        
        self.CLASS_THEMES = {
            "Fighter": {"symbol": "⚔️", "accent": (220, 20, 60), "bg_colors": [(60, 30, 30), (80, 50, 50)]},
            "Wizard": {"symbol": "🔮", "accent": (138, 43, 226), "bg_colors": [(40, 20, 60), (60, 40, 80)]},
            "Rogue": {"symbol": "🗡️", "accent": (105, 105, 105), "bg_colors": [(30, 30, 40), (50, 50, 60)]},
            "Cleric": {"symbol": "✨", "accent": (255, 215, 0), "bg_colors": [(50, 50, 30), (70, 70, 50)]},
            "Ranger": {"symbol": "🏹", "accent": (34, 139, 34), "bg_colors": [(30, 50, 30), (50, 70, 50)]},
            "Paladin": {"symbol": "🛡️", "accent": (70, 130, 180), "bg_colors": [(40, 50, 60), (60, 70, 80)]}
        }
        
        # Create card grids
        from games.dnd.models import RACES, CLASSES
        self.races = RACES
        self.classes = CLASSES
        
        self.race_grid = DnDCardGrid(panel, len(RACES))
        self.class_grid = DnDCardGrid(panel, len(CLASSES))
        
        # Create selection cards
        self.race_cards = []
        for i, race in enumerate(RACES):
            if i < len(self.race_grid.cards):
                card_data = self.race_grid.cards[i]
                theme = self.RACE_THEMES.get(race, self.RACE_THEMES["Human"])
                sel_card = DnDSelectionCard(
                    panel, card_data.rel_x, card_data.rel_y, card_data.rel_w, card_data.rel_h,
                    race, theme["icon"], theme
                )
                self.race_cards.append(sel_card)
        
        self.class_cards = []
        for i, cls in enumerate(CLASSES):
            if i < len(self.class_grid.cards):
                card_data = self.class_grid.cards[i]
                theme = self.CLASS_THEMES[cls]
                sel_card = DnDSelectionCard(
                    panel, card_data.rel_x, card_data.rel_y, card_data.rel_w, card_data.rel_h,
                    cls, theme["symbol"], theme
                )
                self.class_cards.append(sel_card)
        
        self.particles = []
    
    def handle_input(self, fingertips: List[Dict], current_time: float) -> bool:
        """Handle input, returns True when character creation complete"""
        if self.stage == "race":
            for card in self.race_cards:
                if card.update(fingertips, current_time):
                    self.selected_race = card.name
                    for c in self.race_cards:
                        c.selected = (c.name == card.name)
                    self.stage = "class"
                    return False
        
        elif self.stage == "class":
            for card in self.class_cards:
                if card.update(fingertips, current_time):
                    self.selected_class = card.name
                    for c in self.class_cards:
                        c.selected = (c.name == card.name)
                    self.stage = "rolling"
                    self.rolling_stats = True
                    self.roll_timer = 0.0
                    return False
        
        return self.stage == "done"
    
    def update(self, dt: float):
        """Update animations"""
        # Rolling animation
        if self.rolling_stats:
            self.roll_timer += dt
            if self.roll_timer >= 1.5:
                self.finalize_character()
                self.rolling_stats = False
                self.stage = "done"
        
        # Update particles
        self.particles = [p for p in self.particles if p.update(dt)]
        
        # Spawn particles
        if random.random() < 0.3 and self.selected_race:
            theme = self.RACE_THEMES.get(self.selected_race, self.RACE_THEMES["Human"])
            color = theme["accent"]
            px, py, pw, ph = self.panel.rect
            center_x = px + pw // 2
            center_y = py + ph // 2
            angle = random.random() * math.pi * 2
            speed = random.randint(30, 60)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            
            from games.dnd.gameplay_new import PygletParticle
            self.particles.append(PygletParticle(
                center_x, center_y, vx, vy, color, random.uniform(1.0, 2.0)
            ))
    
    def finalize_character(self):
        """Create the final character"""
        from games.dnd.models import Character, generate_character_name
        from games.dnd.logic import DiceRoller
        
        name = generate_character_name(self.selected_race, self.selected_class)
        char = Character(name, self.player_color)
        char.race = self.selected_race
        char.char_class = self.selected_class
        char.level = 1
        char.alignment = "Neutral Good"
        
        # Roll ability scores
        for ability in char.abilities:
            char.abilities[ability] = DiceRoller.roll_ability_score()
        
        char.calculate_hp()
        char.calculate_ac()
        
        self.character = char
    
    def draw(self, renderer: PygletRenderer, current_time: float):
        """Draw character creator"""
        # Draw particles
        for particle in self.particles:
            particle.draw(renderer)
        
        # Calculate title position - always "above" cards from player's perspective
        if self.panel.orientation == 0:  # Bottom players
            title_x, title_y = 0.5, 0.08  # Centered horizontally, near top
        elif self.panel.orientation == 180:  # Top players  
            title_x, title_y = 0.5, 0.92  # Centered horizontally, near their top (our bottom)
        elif self.panel.orientation == 270:  # Left player
            title_x, title_y = 0.92, 0.5  # Near their top (right side of screen), centered vertically
        else:  # orientation == 90, Right player
            title_x, title_y = 0.08, 0.5  # Near their top (left side of screen), centered vertically
        
        if self.stage == "race":
            # Title
            self.panel.draw_text_oriented(renderer, "Choose Your Race", title_x, title_y, 14, (255, 255, 220))
            
            # Draw race cards
            for card in self.race_cards:
                card.draw(renderer, current_time)
        
        elif self.stage == "class":
            # Title
            self.panel.draw_text_oriented(renderer, "Choose Your Class", title_x, title_y, 14, (255, 255, 220))
            
            # Draw class cards
            for card in self.class_cards:
                card.draw(renderer, current_time)
        
        elif self.stage == "rolling":
            theme = self.RACE_THEMES.get(self.selected_race, self.RACE_THEMES["Human"])
            self.panel.draw_text_oriented(renderer, "Rolling Stats...", 0.5, 0.5, 20, theme["accent"])
            dots = "." * (int(self.roll_timer * 3) % 4)
            self.panel.draw_text_oriented(renderer, dots, 0.5, 0.4, 28, Colors.WHITE)
        
        elif self.stage == "done":
            if self.character:
                theme = self.RACE_THEMES.get(self.selected_race, self.RACE_THEMES["Human"])
                self.panel.draw_text_oriented(renderer, self.character.name, 0.5, 0.5, 24, theme["accent"])
                self.panel.draw_text_oriented(renderer, f"{self.character.race} {self.character.char_class}", 0.5, 0.4, 18, Colors.WHITE)
                self.panel.draw_text_oriented(renderer, f"Level {self.character.level}", 0.5, 0.3, 16, (200, 200, 200))
                self.panel.draw_text_oriented(renderer, "Ready!", 0.5, 0.2, 20, (100, 255, 100))


class DnDActionButton(DnDCard):
    """Action button using relative positioning"""
    
    def __init__(self, panel: DnDPlayerPanel, rel_x: float, rel_y: float, rel_w: float, rel_h: float,
                 text: str, icon: str = "", color: Tuple[int, int, int] = (80, 120, 160)):
        super().__init__(panel, rel_x, rel_y, rel_w, rel_h)
        self.text = text
        self.icon = icon
        self.color = color
        self.hover_start = 0.0
        self.hovering = False
        self.enabled = True
    
    def update(self, fingertips: List[Dict], current_time: float) -> bool:
        """Returns True if clicked"""
        if not self.enabled:
            self.hovering = False
            return False
        
        clicked = False
        is_hovered = False
        
        for meta in fingertips:
            if meta == 'ESC':
                continue
            px, py = meta["pos"]
            if self.contains_point(px, py):
                is_hovered = True
                if not self.hovering:
                    self.hover_start = current_time
                    self.hovering = True
                
                hover_duration = current_time - self.hover_start
                if hover_duration >= HOVER_TIME_THRESHOLD:
                    clicked = True
                    self.hovering = False
                break
        
        if not is_hovered:
            self.hovering = False
            self.hover_start = 0.0
        
        return clicked
    
    def draw(self, renderer: PygletRenderer, current_time: float):
        """Draw button with relative positioning"""
        x, y, w, h = self.get_absolute_rect()
        
        # Background
        bg_color = self.color if self.enabled else (60, 60, 60)
        renderer.draw_rect(bg_color, (x, y, w, h))
        
        # Border
        border_color = Colors.ACCENT if self.hovering else (150, 150, 150)
        renderer.draw_rect(border_color, (x, y, w, h), width=2)
        
        # Hover progress bar
        if self.hovering:
            progress = min(1.0, (current_time - self.hover_start) / HOVER_TIME_THRESHOLD)
            if self.panel.orientation in [90, 270]:
                bar_h = int(h * progress)
                renderer.draw_rect(Colors.ACCENT, (x, y, 4, bar_h))
            else:
                bar_w = int(w * progress)
                renderer.draw_rect(Colors.ACCENT, (x, y + h - 4, bar_w, 4))
        
        # Text and icon using panel's rotation
        text_color = Colors.WHITE if self.enabled else (120, 120, 120)
        display_text = f"{self.icon} {self.text}" if self.icon else self.text
        
        # Draw text at center of button
        cx = (self.rel_x + self.rel_w / 2)
        cy = (self.rel_y + self.rel_h / 2)
        self.panel.draw_text_oriented(renderer, display_text, cx, cy, 14, text_color)


class DnDDMControlPanel:
    """DM Control Panel using relative positioning"""
    
    def __init__(self, panel: DnDPlayerPanel):
        self.panel = panel
        
        # Button configurations
        button_configs = [
            ("spawn_enemy", "👹", "Enemy", (120, 40, 40)),
            ("spawn_boss", "💀", "Boss", (160, 20, 20)),
            ("add_npc", "👤", "NPC", (40, 80, 120)),
            ("add_merchant", "💰", "Merchant", (200, 160, 40)),
            ("change_bg", "🎨", "Scene", (80, 40, 120)),
            ("weather", "🌧️", "Weather", (100, 100, 140)),
            ("give_item", "💎", "Item", (120, 100, 40)),
            ("spawn_trap", "⚠️", "Trap", (200, 100, 20))
        ]
        
        self.buttons = {}
        self._create_buttons(button_configs)
    
    def _create_buttons(self, configs):
        """Create buttons with relative positioning"""
        margin = 0.05
        gap = 0.02
        num_buttons = len(configs)
        
        if self.panel.orientation in [90, 270]:  # Vertical panels - stack vertically
            btn_width = 0.70  # Leave room for margins
            btn_height = (1.0 - 2 * margin - (num_buttons - 1) * gap) / num_buttons
            btn_height = min(btn_height, 0.12)  # Cap button height
            
            btn_x = (1.0 - btn_width) / 2  # Center horizontally
            total_height = num_buttons * btn_height + (num_buttons - 1) * gap
            start_y = (1.0 - total_height) / 2  # Center vertically
            
            for i, (key, emoji, text, color) in enumerate(configs):
                btn_y = start_y + i * (btn_height + gap)
                btn = DnDActionButton(self.panel, btn_x, btn_y, btn_width, btn_height, text, emoji, color)
                btn.key = key
                btn.emoji = emoji
                self.buttons[key] = btn
                
        else:  # Horizontal panels - 2 rows of 4
            btn_width = (1.0 - 2 * margin - 3 * gap) / 4
            btn_height = (1.0 - 2 * margin - gap) / 2
            
            for i, (key, emoji, text, color) in enumerate(configs):
                row = i // 4
                col = i % 4
                btn_x = margin + col * (btn_width + gap)
                btn_y = margin + row * (btn_height + gap)
                
                btn = DnDActionButton(self.panel, btn_x, btn_y, btn_width, btn_height, text, emoji, color)
                btn.key = key
                btn.emoji = emoji
                self.buttons[key] = btn
    
    def update(self, fingertips: List[Dict], current_time: float) -> Optional[str]:
        """Returns button key if clicked"""
        for button in self.buttons.values():
            if button.update(fingertips, current_time):
                return button.key
        return None
    
    def draw(self, renderer: PygletRenderer, current_time: float):
        """Draw all DM control buttons"""
        for button in self.buttons.values():
            # Draw button background and border
            x, y, w, h = button.get_absolute_rect()
            renderer.draw_rect(button.color, (x, y, w, h))
            renderer.draw_rect(Colors.WHITE, (x, y, w, h), width=2)
            
            # Hover progress
            if button.hovering and button.hover_start > 0:
                progress = min(1.0, (current_time - button.hover_start) / HOVER_TIME_THRESHOLD)
                if self.panel.orientation in [90, 270]:
                    bar_h = int(h * progress)
                    renderer.draw_rect(Colors.ACCENT, (x, y, 4, bar_h))
                else:
                    bar_w = int(w * progress)
                    renderer.draw_rect(Colors.ACCENT, (x, y + h - 4, bar_w, 4))
            
            # Calculate center and text positions
            cx_rel = button.rel_x + button.rel_w / 2
            cy_rel = button.rel_y + button.rel_h / 2
            
            # Position emoji and text based on orientation
            if self.panel.orientation in [90, 270]:  # Vertical panels - separate on X axis
                if self.panel.orientation == 90:  # Right panel
                    emoji_x = cx_rel + button.rel_w * 0.25
                    text_x = cx_rel - button.rel_w * 0.25
                else:  # Left panel (270)
                    emoji_x = cx_rel - button.rel_w * 0.25
                    text_x = cx_rel + button.rel_w * 0.25
                emoji_y = text_y = cy_rel
            else:  # Horizontal panels - separate on Y axis
                emoji_x = text_x = cx_rel
                emoji_y = cy_rel - button.rel_h * 0.25  # Emoji above
                text_y = cy_rel + button.rel_h * 0.25    # Text below
            
            # Draw emoji and text
            self.panel.draw_text_oriented(renderer, button.emoji, emoji_x, emoji_y, 18, Colors.WHITE)
            self.panel.draw_text_oriented(renderer, button.text, text_x, text_y, 8, Colors.WHITE)


class DnDCharacterSheet:
    """Character sheet using relative positioning with action buttons"""
    
    def __init__(self, panel: DnDPlayerPanel):
        self.panel = panel
        
        # Create action buttons based on panel orientation
        self._create_action_buttons()
    
    def _create_action_buttons(self):
        """Create action buttons for player actions"""
        button_configs = [
            ("attack", "⚔️", "Attack", (180, 40, 40)),
            ("cast_spell", "🔮", "Spell", (100, 40, 180)),
            ("use_item", "💎", "Item", (40, 140, 140)),
            ("defend", "🛡️", "Defend", (40, 100, 180))
        ]
        
        self.action_buttons = {}
        margin = 0.05
        gap = 0.02
        num_buttons = len(button_configs)
        
        # Single consistent 2x2 button grid layout: Attack | Spell / Defend | Item
        # Buttons in right half - rotation handles player perspective
        btn_gap = 0.04
        btn_width = 0.22
        btn_height = 0.44
        grid_start_x = 0.52
        grid_start_y = 0.05
        
        # Button mapping: Attack(0), Spell(1), Item(2), Defend(3)
        # Reorder to match layout: Attack | Spell / Defend | Item
        button_order = [0, 1, 3, 2]  # attack, cast_spell, defend, use_item
        
        # Create 2x2 grid in right half
        positions = [
            (grid_start_x, grid_start_y + btn_height + btn_gap),  # Top-left: Attack
            (grid_start_x + btn_width + btn_gap, grid_start_y + btn_height + btn_gap),  # Top-right: Spell
            (grid_start_x, grid_start_y),  # Bottom-left: Defend
            (grid_start_x + btn_width + btn_gap, grid_start_y)  # Bottom-right: Item
        ]
        
        for i, config_idx in enumerate(button_order):
            key, emoji, text, color = button_configs[config_idx]
            btn_x, btn_y = positions[i]
            btn = DnDActionButton(self.panel, btn_x, btn_y, btn_width, btn_height, text, emoji, color)
            btn.key = key
            self.action_buttons[key] = btn
    
    def update(self, fingertips: List[Dict], current_time: float) -> Optional[str]:
        """Handle button interactions, returns action key if clicked"""
        for button in self.action_buttons.values():
            if button.update(fingertips, current_time):
                return button.key
        return None
    
    def draw(self, renderer: PygletRenderer, character, player_color: Tuple[int, int, int], current_time: float):
        """Draw character sheet - manually handle each orientation"""
        # Background
        x, y, w, h = self.panel.rect
        renderer.draw_rect((40, 40, 50), (x, y, w, h))
        renderer.draw_rect(player_color, (x, y, w, h), width=3)
        
        # Get character info
        info_text = f"{character.race} {character.char_class} | Lvl {character.level} | XP: {character.experience}"
        hp_percentage = character.current_hp / max(character.max_hp, 1)
        hp_value_text = f"{character.current_hp}/{character.max_hp}"
        
        # Calculate mana
        max_mana = 100
        if character.char_class in ["Wizard", "Cleric"]:
            max_mana = 150
        elif character.char_class in ["Paladin", "Ranger"]:
            max_mana = 75
        elif character.char_class in ["Fighter", "Rogue"]:
            max_mana = 50
        current_mana = getattr(character, 'current_mana', max_mana)
        mana_percentage = current_mana / max(max_mana, 1)
        mana_value_text = f"{int(current_mana)}/{int(max_mana)}"
        
        if self.panel.orientation == 0:  # Bottom player
            self._draw_bottom_layout(renderer, x, y, w, h, character.name, info_text, 
                                    hp_percentage, hp_value_text, mana_percentage, mana_value_text)
        elif self.panel.orientation == 180:  # Top player
            self._draw_top_layout(renderer, x, y, w, h, character.name, info_text,
                                 hp_percentage, hp_value_text, mana_percentage, mana_value_text)
        elif self.panel.orientation == 270:  # Left player
            self._draw_left_layout(renderer, x, y, w, h, character.name, info_text,
                                   hp_percentage, hp_value_text, mana_percentage, mana_value_text)
        
        # Draw buttons with special handling for left player
        for button in self.action_buttons.values():
            if self.panel.orientation == 270:
                # Custom draw for left player to avoid double rotation
                self._draw_button_left(button, renderer, current_time)
            else:
                button.draw(renderer, current_time)
    
    def _draw_bottom_layout(self, renderer, x, y, w, h, name, info, hp_pct, hp_val, mana_pct, mana_val):
        """Draw for bottom player (0°) - Left=Info, Right=Buttons"""
        # Text in left half - spread from 0.05 to 0.90
        name_x = int(x + w * 0.225)
        name_y = int(y + h * 0.05)
        renderer.draw_text(name, name_x, name_y, font_size=14, color=Colors.WHITE, 
                          anchor_x='center', anchor_y='center', rotation=0)
        
        info_x = int(x + w * 0.225)
        info_y = int(y + h * 0.20)
        renderer.draw_text(info, info_x, info_y, font_size=9, color=(200, 200, 200),
                          anchor_x='center', anchor_y='center', rotation=0)
        
        hp_text_x = int(x + w * 0.225)
        hp_text_y = int(y + h * 0.40)
        renderer.draw_text("HP", hp_text_x, hp_text_y, font_size=10, color=Colors.WHITE,
                          anchor_x='center', anchor_y='center', rotation=0)
        
        # HP bar in left half
        hp_bar_x = int(x + w * 0.03)
        hp_bar_y = int(y + h * 0.48)
        hp_bar_w = int(w * 0.39)
        hp_bar_h = int(h * 0.06)
        renderer.draw_rect((40, 20, 20), (hp_bar_x, hp_bar_y, hp_bar_w, hp_bar_h))
        hp_fill_w = int(hp_bar_w * hp_pct)
        hp_color = (50, 200, 50) if hp_pct > 0.5 else ((200, 200, 50) if hp_pct > 0.25 else (200, 50, 50))
        renderer.draw_rect(hp_color, (hp_bar_x, hp_bar_y, hp_fill_w, hp_bar_h))
        renderer.draw_text(hp_val, int(x + w * 0.225), int(y + h * 0.51), font_size=8, color=Colors.WHITE,
                          anchor_x='center', anchor_y='center', rotation=0)
        
        mana_text_x = int(x + w * 0.225)
        mana_text_y = int(y + h * 0.70)
        renderer.draw_text("MANA", mana_text_x, mana_text_y, font_size=10, color=Colors.WHITE,
                          anchor_x='center', anchor_y='center', rotation=0)
        
        # Mana bar in left half
        mana_bar_x = int(x + w * 0.03)
        mana_bar_y = int(y + h * 0.78)
        mana_bar_w = int(w * 0.39)
        mana_bar_h = int(h * 0.06)
        renderer.draw_rect((20, 20, 40), (mana_bar_x, mana_bar_y, mana_bar_w, mana_bar_h))
        mana_fill_w = int(mana_bar_w * mana_pct)
        mana_color = (50, 100, 255) if mana_pct > 0.5 else ((100, 150, 255) if mana_pct > 0.25 else (150, 150, 200))
        renderer.draw_rect(mana_color, (mana_bar_x, mana_bar_y, mana_fill_w, mana_bar_h))
        renderer.draw_text(mana_val, int(x + w * 0.225), int(y + h * 0.81), font_size=8, color=Colors.WHITE,
                          anchor_x='center', anchor_y='center', rotation=0)
        
        # Position buttons in right half - 2x2 grid
        self._position_button('attack', 0.52, 0.49)
        self._position_button('cast_spell', 0.76, 0.49)
        self._position_button('defend', 0.52, 0.05)
        self._position_button('use_item', 0.76, 0.05)
    
    def _draw_top_layout(self, renderer, x, y, w, h, name, info, hp_pct, hp_val, mana_pct, mana_val):
        """Draw for top player (180°) - Left=Info, Right=Buttons (from their view)"""
        # Text in left half (from their view = right half from app view) - spread from 0.05 to 0.90
        name_x = int(x + w * 0.775)
        name_y = int(y + h * 0.95)
        renderer.draw_text(name, name_x, name_y, font_size=14, color=Colors.WHITE,
                          anchor_x='center', anchor_y='center', rotation=180)
        
        info_x = int(x + w * 0.775)
        info_y = int(y + h * 0.80)
        renderer.draw_text(info, info_x, info_y, font_size=9, color=(200, 200, 200),
                          anchor_x='center', anchor_y='center', rotation=180)
        
        hp_text_x = int(x + w * 0.775)
        hp_text_y = int(y + h * 0.60)
        renderer.draw_text("HP", hp_text_x, hp_text_y, font_size=10, color=Colors.WHITE,
                          anchor_x='center', anchor_y='center', rotation=180)
        
        # HP bar in left half (from their view)
        hp_bar_x = int(x + w * 0.58)
        hp_bar_y = int(y + h * 0.46)
        hp_bar_w = int(w * 0.39)
        hp_bar_h = int(h * 0.06)
        renderer.draw_rect((40, 20, 20), (hp_bar_x, hp_bar_y, hp_bar_w, hp_bar_h))
        hp_fill_w = int(hp_bar_w * hp_pct)
        hp_color = (50, 200, 50) if hp_pct > 0.5 else ((200, 200, 50) if hp_pct > 0.25 else (200, 50, 50))
        renderer.draw_rect(hp_color, (hp_bar_x, hp_bar_y, hp_fill_w, hp_bar_h))
        renderer.draw_text(hp_val, int(x + w * 0.775), int(y + h * 0.49), font_size=8, color=Colors.WHITE,
                          anchor_x='center', anchor_y='center', rotation=180)
        
        mana_text_x = int(x + w * 0.775)
        mana_text_y = int(y + h * 0.30)
        renderer.draw_text("MANA", mana_text_x, mana_text_y, font_size=10, color=Colors.WHITE,
                          anchor_x='center', anchor_y='center', rotation=180)
        
        # Mana bar in left half (from their view)
        mana_bar_x = int(x + w * 0.58)
        mana_bar_y = int(y + h * 0.16)
        mana_bar_w = int(w * 0.39)
        mana_bar_h = int(h * 0.06)
        renderer.draw_rect((20, 20, 40), (mana_bar_x, mana_bar_y, mana_bar_w, mana_bar_h))
        mana_fill_w = int(mana_bar_w * mana_pct)
        mana_color = (50, 100, 255) if mana_pct > 0.5 else ((100, 150, 255) if mana_pct > 0.25 else (150, 150, 200))
        renderer.draw_rect(mana_color, (mana_bar_x, mana_bar_y, mana_fill_w, mana_bar_h))
        renderer.draw_text(mana_val, int(x + w * 0.775), int(y + h * 0.19), font_size=8, color=Colors.WHITE,
                          anchor_x='center', anchor_y='center', rotation=180)
        
        # Position buttons in right half (from their view = left half from app view) - 2x2 grid
        self._position_button('attack', 0.24, 0.49)
        self._position_button('cast_spell', 0.00, 0.49)
        self._position_button('defend', 0.24, 0.05)
        self._position_button('use_item', 0.00, 0.05)
    
    def _draw_left_layout(self, renderer, x, y, w, h, name, info, hp_pct, hp_val, mana_pct, mana_val):
        """Draw for left player (270°) - Left=Info, Right=Buttons (from their view)"""
        # Note: draw_text_oriented adds +180° for side panels, so we use 90° to get proper 270° orientation
        # Text in left half (from their view = bottom half from app view) - mirrored X positions
        name_x = int(x + w * 0.92)  # Mirrored from 0.08
        name_y = int(y + h * 0.275)
        renderer.draw_text(name, name_x, name_y, font_size=14, color=Colors.WHITE,
                          anchor_x='center', anchor_y='center', rotation=90)
        
        info_x = int(x + w * 0.80)  # Mirrored from 0.20
        info_y = int(y + h * 0.275)
        renderer.draw_text(info, info_x, info_y, font_size=9, color=(200, 200, 200),
                          anchor_x='center', anchor_y='center', rotation=90)
        
        hp_text_x = int(x + w * 0.65)  # Mirrored from 0.35
        hp_text_y = int(y + h * 0.275)
        renderer.draw_text("HP", hp_text_x, hp_text_y, font_size=10, color=Colors.WHITE,
                          anchor_x='center', anchor_y='center', rotation=90)
        
        # HP bar in left half (from their view = bottom, horizontal for them, vertical for app)
        hp_bar_x = int(x + w * 0.54)  # Mirrored from 0.42
        hp_bar_y = int(y + h * 0.03)
        hp_bar_w = int(w * 0.04)  # Thin in app view
        hp_bar_h = int(h * 0.42)  # Long in app view
        renderer.draw_rect((40, 20, 20), (hp_bar_x, hp_bar_y, hp_bar_w, hp_bar_h))
        hp_fill_h = int(hp_bar_h * hp_pct)
        hp_color = (50, 200, 50) if hp_pct > 0.5 else ((200, 200, 50) if hp_pct > 0.25 else (200, 50, 50))
        renderer.draw_rect(hp_color, (hp_bar_x, hp_bar_y, hp_bar_w, hp_fill_h))
        renderer.draw_text(hp_val, int(x + w * 0.56), int(y + h * 0.275), font_size=8, color=Colors.WHITE,
                          anchor_x='center', anchor_y='center', rotation=90)
        
        mana_text_x = int(x + w * 0.40)  # Mirrored from 0.60
        mana_text_y = int(y + h * 0.275)
        renderer.draw_text("MANA", mana_text_x, mana_text_y, font_size=10, color=Colors.WHITE,
                          anchor_x='center', anchor_y='center', rotation=90)
        
        # Mana bar in left half (from their view)
        mana_bar_x = int(x + w * 0.29)  # Mirrored from 0.67
        mana_bar_y = int(y + h * 0.03)
        mana_bar_w = int(w * 0.04)
        mana_bar_h = int(h * 0.42)
        renderer.draw_rect((20, 20, 40), (mana_bar_x, mana_bar_y, mana_bar_w, mana_bar_h))
        mana_fill_h = int(mana_bar_h * mana_pct)
        mana_color = (50, 100, 255) if mana_pct > 0.5 else ((100, 150, 255) if mana_pct > 0.25 else (150, 150, 200))
        renderer.draw_rect(mana_color, (mana_bar_x, mana_bar_y, mana_bar_w, mana_fill_h))
        renderer.draw_text(mana_val, int(x + w * 0.31), int(y + h * 0.275), font_size=8, color=Colors.WHITE,
                          anchor_x='center', anchor_y='center', rotation=90)
        
        # Position buttons in right half (from their view = top half from app view) - 2x2 grid
        # For left player, buttons need swapped dimensions (width becomes height in their view)
        self._position_button_left('attack', 0.05, 0.76, 0.44, 0.22)
        self._position_button_left('cast_spell', 0.49, 0.76, 0.44, 0.22)
        self._position_button_left('defend', 0.05, 0.52, 0.44, 0.22)
        self._position_button_left('use_item', 0.49, 0.52, 0.44, 0.22)
    
    def _position_button(self, button_id: str, rel_x: float, rel_y: float):
        """Position a button at relative coordinates"""
        if button_id in self.action_buttons:
            button = self.action_buttons[button_id]
            button.rel_x = rel_x
            button.rel_y = rel_y
    
    def _position_button_left(self, button_id: str, rel_x: float, rel_y: float, rel_w: float, rel_h: float):
        """Position and resize a button for left player (needs swapped dimensions)"""
        if button_id in self.action_buttons:
            button = self.action_buttons[button_id]
            button.rel_x = rel_x
            button.rel_y = rel_y
            button.rel_w = rel_w
            button.rel_h = rel_h
    
    def _draw_button_left(self, button, renderer: PygletRenderer, current_time: float):
        """Custom button draw for left player - avoids panel.draw_text_oriented double rotation"""
        x, y, w, h = button.get_absolute_rect()
        
        # Background
        bg_color = button.color if button.enabled else (60, 60, 60)
        renderer.draw_rect(bg_color, (x, y, w, h))
        
        # Border
        border_color = Colors.ACCENT if button.hovering else (150, 150, 150)
        renderer.draw_rect(border_color, (x, y, w, h), width=2)
        
        # Hover progress bar
        if button.hovering:
            progress = min(1.0, (current_time - button.hover_start) / HOVER_TIME_THRESHOLD)
            bar_h = int(h * progress)
            renderer.draw_rect(Colors.ACCENT, (x, y, 4, bar_h))
        
        # Text with direct rotation (not using panel.draw_text_oriented)
        text_color = Colors.WHITE if button.enabled else (120, 120, 120)
        display_text = f"{button.icon} {button.text}" if button.icon else button.text
        
        # Calculate center of button
        cx = x + w // 2
        cy = y + h // 2
        
        # Draw text with 90° rotation (correct for left player)
        renderer.draw_text(display_text, cx, cy, font_size=14, color=text_color,
                          anchor_x='center', anchor_y='center', rotation=90)


class DnDCombatTracker:
    """Combat tracker using central screen display"""
    
    def __init__(self, screen_width: int, screen_height: int):
        self.width = screen_width
        self.height = screen_height
        self.x = int(screen_width * 0.35)
        self.y = int(screen_height * 0.1)
        self.panel_width = int(screen_width * 0.3)
        self.panel_height = int(screen_height * 0.8)
    
    def draw(self, renderer: PygletRenderer, initiative_order: List[Dict], current_turn: int, round_num: int):
        """Draw initiative tracker (central, not rotated)"""
        # Background
        renderer.draw_rect((30, 30, 40, 200), (self.x, self.y, self.panel_width, self.panel_height))
        renderer.draw_rect(Colors.ACCENT, (self.x, self.y, self.panel_width, self.panel_height), width=3)
        
        # Title
        renderer.draw_text(
            f"INITIATIVE - Round {round_num}",
            self.x + self.panel_width // 2,
            self.y + self.panel_height - 30,
            font_size=20,
            color=Colors.ACCENT,
            anchor_x='center',
            anchor_y='center'
        )
        
        # Initiative list
        entry_height = 50
        start_y = self.y + self.panel_height - 70
        max_entries = min(len(initiative_order), 12)
        
        for i in range(max_entries):
            entry = initiative_order[i]
            entry_y = start_y - i * entry_height
            is_current = (i == current_turn)
            
            # Entry background
            if is_current:
                renderer.draw_rect((100, 150, 200, 100), (self.x + 10, entry_y, self.panel_width - 20, entry_height - 5))
            
            # Entity info
            entity = entry["entity"]
            entity_name = entity.name if hasattr(entity, 'name') else "Unknown"
            initiative_val = entry["initiative"]
            is_enemy = entry.get("is_enemy", False)
            
            name_color = (255, 100, 100) if is_enemy else Colors.WHITE
            
            renderer.draw_text(
                f"{initiative_val}: {entity_name}",
                self.x + 20,
                entry_y + 25,
                font_size=14,
                color=name_color,
                anchor_x='left',
                anchor_y='center'
            )
            
            # HP if available
            if hasattr(entity, 'current_hp') and hasattr(entity, 'max_hp'):
                hp_text = f"{entity.current_hp}/{entity.max_hp}"
                renderer.draw_text(
                    hp_text,
                    self.x + self.panel_width - 20,
                    entry_y + 25,
                    font_size=12,
                    color=(200, 200, 200),
                    anchor_x='right',
                    anchor_y='center'
                )


class DnDDiceRollDisplay:
    """Animated dice roll display"""
    
    def __init__(self):
        self.active_rolls = []
    
    def add_roll(self, text: str, x: int, y: int, color: Tuple[int, int, int] = Colors.WHITE, duration: float = 2.0):
        self.active_rolls.append({
            "text": text,
            "x": x,
            "y": y,
            "start_time": time.time(),
            "duration": duration,
            "color": color
        })
    
    def update(self, dt: float):
        current_time = time.time()
        self.active_rolls = [roll for roll in self.active_rolls 
                            if current_time - roll["start_time"] < roll["duration"]]
    
    def draw(self, renderer: PygletRenderer):
        current_time = time.time()
        
        for roll in self.active_rolls:
            elapsed = current_time - roll["start_time"]
            progress = elapsed / roll["duration"]
            
            # Fade out and float up
            alpha = int(255 * (1 - progress))
            offset_y = int(80 * progress)
            
            renderer.draw_text(
                roll["text"],
                roll["x"],
                roll["y"] + offset_y,
                font_size=28,
                color=roll["color"],
                anchor_x='center',
                anchor_y='center',
                alpha=alpha
            )


def draw_status_condition(renderer: PygletRenderer, x: int, y: int, condition: str):
    """Draw status condition badge"""
    renderer.draw_rect((100, 50, 50), (x, y, 80, 25))
    renderer.draw_text(condition, x + 40, y + 12, font_size=10, color=Colors.WHITE, anchor_x='center', anchor_y='center')


def draw_damage_number(renderer: PygletRenderer, x: int, y: int, damage: int, is_heal: bool = False):
    """Draw floating damage/heal number"""
    color = (100, 255, 100) if is_heal else (255, 100, 100)
    text = f"+{damage}" if is_heal else f"-{damage}"
    renderer.draw_text(text, x, y, font_size=28, color=color, anchor_x='center', anchor_y='center')
