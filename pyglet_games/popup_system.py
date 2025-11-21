"""
Universal Popup System for Pyglet Games
Grid-based layout system for clean, readable popups across all player orientations
"""

from typing import Tuple, List, Dict, Optional, Any
from pyglet_games.renderer import PygletRenderer
from config import PLAYER_COLORS


class GridCell:
    """Represents a cell in the popup grid"""
    def __init__(self, row: int, col: int, row_span: int = 1, col_span: int = 1):
        self.row = row
        self.col = col
        self.row_span = row_span
        self.col_span = col_span


class PopupContent:
    """Content item for popup (text, button, etc.)"""
    def __init__(self, content_type: str, text: str, grid_cell: GridCell, 
                 font_size: int = 16, color: Tuple[int, int, int] = (255, 255, 255),
                 callback: Optional[str] = None):
        self.content_type = content_type  # "title", "text", "value", "button"
        self.text = text
        self.grid_cell = grid_cell
        self.font_size = font_size
        self.color = color
        self.callback = callback  # For buttons
        self.enabled = True


class PopupGrid:
    """Grid-based popup layout"""
    def __init__(self, rows: int, cols: int, orientation: int = 0):
        self.rows = rows
        self.cols = cols
        self.orientation = orientation  # 0, 90, 180, 270
        self.contents: List[PopupContent] = []
    
    def add_title(self, text: str, row: int = 0):
        """Add centered title at top"""
        self.contents.append(PopupContent(
            "title", text, GridCell(row, 0, 1, self.cols),
            font_size=14, color=(180, 180, 180)
        ))
    
    def add_text(self, text: str, row: int, col: int = 0, col_span: int = None,
                 font_size: int = 16, color: Tuple[int, int, int] = (255, 255, 255)):
        """Add text content"""
        if col_span is None:
            col_span = self.cols
        self.contents.append(PopupContent(
            "text", text, GridCell(row, col, 1, col_span),
            font_size=font_size, color=color
        ))
    
    def add_value(self, text: str, row: int, col: int = 0, col_span: int = None,
                  font_size: int = 20, color: Tuple[int, int, int] = (100, 255, 100)):
        """Add emphasized value (price, amount, etc.)"""
        if col_span is None:
            col_span = self.cols
        self.contents.append(PopupContent(
            "value", text, GridCell(row, col, 1, col_span),
            font_size=font_size, color=color
        ))
    
    def add_button(self, text: str, row: int, col: int, callback: str,
                   col_span: int = 1, enabled: bool = True):
        """Add button"""
        content = PopupContent(
            "button", text, GridCell(row, col, 1, col_span),
            font_size=16, color=(255, 255, 255), callback=callback
        )
        content.enabled = enabled
        self.contents.append(content)
    
    def calculate_cell_rect(self, panel_rect: Tuple[int, int, int, int],
                           cell: GridCell) -> Tuple[int, int, int, int]:
        """Calculate pixel rectangle for a grid cell"""
        px, py, pw, ph = panel_rect
        
        # Margins around the grid
        margin = 15
        grid_x = px + margin
        grid_y = py + margin
        grid_w = pw - 2 * margin
        grid_h = ph - 2 * margin
        
        # Cell dimensions
        cell_w = grid_w / self.cols
        cell_h = grid_h / self.rows
        
        # Calculate cell position
        x = int(grid_x + cell.col * cell_w)
        y = int(grid_y + cell.row * cell_h)
        w = int(cell_w * cell.col_span)
        h = int(cell_h * cell.row_span)
        
        return (x, y, w, h)


class UniversalPopup:
    """Universal popup system - floating box above panel with text only, buttons in panel"""
    
    def __init__(self):
        self.active = False
        self.player_idx: Optional[int] = None
        self.panel_rect: Optional[Tuple[int, int, int, int]] = None
        self.popup_rect: Optional[Tuple[int, int, int, int]] = None
        self.orientation: int = 0
        self.grid: Optional[PopupGrid] = None
        self.popup_type: str = ""
        self.data: Dict[str, Any] = {}
        self.text_lines: List[Tuple[str, int, Tuple[int, int, int]]] = []  # (text, font_size, color)
    
    def show(self, player_idx: int, panel_rect: Tuple[int, int, int, int],
             orientation: int, popup_type: str, text_lines: List[Tuple[str, int, Tuple[int, int, int]]],
             data: Dict[str, Any] = None):
        """Show popup as floating box above panel"""
        self.active = True
        self.player_idx = player_idx
        self.panel_rect = panel_rect
        self.orientation = orientation
        self.popup_type = popup_type
        self.text_lines = text_lines
        self.data = data or {}
        self._calculate_popup_rect()
    
    def _calculate_popup_rect(self):
        """Calculate floating popup box position above panel based on orientation and content"""
        px, py, pw, ph = self.panel_rect
        
        # Calculate dynamic size based on text content
        num_lines = len(self.text_lines)
        if num_lines == 0:
            num_lines = 1
        
        # Estimate text dimensions with better spacing
        max_font_size = max((fs for _, fs, _ in self.text_lines), default=16)
        line_height = max_font_size + 15  # More padding between lines
        
        # Popup size - dynamic based on content and orientation
        if self.orientation in [90, 270]:  # Left/Right - horizontal spacing from their POV
            # For rotated text, dimensions are swapped from app's perspective:
            # - Text arranged horizontally from player's POV needs HEIGHT from app's POV
            # - Height of text from player's POV needs WIDTH from app's POV
            from pyglet import text as pyglet_text
            
            item_widths = []
            for text_str, fs, _ in self.text_lines:
                # Create a temporary label to measure actual text width (from player's POV)
                temp_label = pyglet_text.Label(
                    text_str,
                    font_name='Arial',
                    font_size=fs
                )
                # Use content_width for accurate measurement
                actual_width = temp_label.content_width
                item_widths.append(actual_width)
            
            # Total width needed from player's POV (becomes HEIGHT from app's POV)
            total_text_width = sum(item_widths)
            spacing_between = 70 * (num_lines - 1) if num_lines > 1 else 0  # Extra space between items
            
            # SWAP: player's horizontal layout needs vertical space from app's view
            popup_h = max(350, int(total_text_width + spacing_between + 140))  # Height = horizontal extent
            popup_w = max(140, min(320, int(max_font_size * 3.5)))  # Width = text height
        else:  # Top/Bottom - vertical stacking
            # Measure actual text width for the longest line
            from pyglet import text as pyglet_text
            
            max_text_width = 0
            for text_str, fs, _ in self.text_lines:
                temp_label = pyglet_text.Label(
                    text_str,
                    font_name='Arial',
                    font_size=fs
                )
                max_text_width = max(max_text_width, temp_label.content_width)
            
            popup_w = max(240, int(max_text_width + 100))  # Width fits longest line with generous margins
            popup_h = max(120, num_lines * line_height + 70)  # Dynamic height with generous padding
        
        # Position above panel based on orientation
        if self.orientation == 0:  # Bottom - popup above panel
            popup_x = px - (popup_w - pw) // 2
            popup_y = py - popup_h - 10
        elif self.orientation == 180:  # Top - popup below panel
            popup_x = px - (popup_w - pw) // 2
            popup_y = py + ph + 10
        elif self.orientation == 270:  # Left - popup to the right
            popup_x = px + pw + 10
            popup_y = py + (ph - popup_h) // 2
        else:  # 90 - Right - popup to the left
            popup_x = px - popup_w - 10
            popup_y = py + (ph - popup_h) // 2
        
        self.popup_rect = (popup_x, popup_y, popup_w, popup_h)
    
    def hide(self):
        """Hide popup"""
        self.active = False
        self.player_idx = None
        self.panel_rect = None
        self.popup_rect = None
        self.text_lines = []
        self.data = {}
    
    def draw(self, renderer: PygletRenderer):
        """Draw floating popup box with text only - fully opaque to cover board"""
        if not self.active or not self.popup_rect or not self.text_lines:
            return
        
        px, py, pw, ph = self.popup_rect
        
        # Solid opaque background - darker and fully covering
        renderer.draw_rect((20, 25, 30), (px, py, pw, ph))
        
        # Second layer for complete coverage
        renderer.draw_rect((25, 30, 35), (px + 1, py + 1, pw - 2, ph - 2))
        
        # Player color border - thicker
        border_color = PLAYER_COLORS[self.player_idx]
        renderer.draw_rect(border_color, (px, py, pw, ph), width=5)
        
        # Inner border for depth
        renderer.draw_rect((60, 65, 75), (px + 6, py + 6, pw - 12, ph - 12), width=2)
        
        # Draw text lines - layout depends on orientation
        num_lines = len(self.text_lines)
        if num_lines == 0:
            return
        
        # For left/right players: horizontal spacing (||||)
        # For top/bottom players: vertical stacking (standard)
        if self.orientation in [90, 270]:  # Left/Right - horizontal from their POV
            text_area_w = pw - 20
            line_w = text_area_w / num_lines
            
            for i, (text, font_size, color) in enumerate(self.text_lines):
                # Left player (270): reverse position so first item is at right (top from their POV)
                # Right player (90): normal order, first item at left (top from their POV)
                if self.orientation == 270:  # Left - start from right side
                    position_index = num_lines - 1 - i
                else:  # Right - normal
                    position_index = i
                
                cx = px + int((position_index + 0.5) * line_w) + 10
                cy = py + ph // 2
                self._draw_oriented_text(renderer, text, cx, cy, font_size, color)
        else:  # Top/Bottom - vertical stacking
            text_area_h = ph - 20
            line_h = text_area_h / num_lines
            
            for i, (text, font_size, color) in enumerate(self.text_lines):
                cx = px + pw // 2
                # Bottom (0): start from top, Top (180): start from bottom
                if self.orientation == 0:  # Bottom - normal order (top to bottom)
                    cy = py + int((i + 0.5) * line_h) + 10
                else:  # Top (180) - reversed (bottom to top from their view)
                    cy = py + ph - (int((i + 0.5) * line_h) + 10)
                self._draw_oriented_text(renderer, text, cx, cy, font_size, color)
    

    
    def _draw_oriented_text(self, renderer: PygletRenderer, text: str,
                           x: int, y: int, font_size: int, color: Tuple[int, int, int]):
        """Draw text with proper rotation based on PLAYER POV"""
        # Rotate text so it faces the player from their perspective
        if self.orientation == 0:  # Bottom player - normal
            rotation = 0
        elif self.orientation == 180:  # Top player - upside down from their view
            rotation = 180
        elif self.orientation == 270:  # Left player - rotate 90° to face them
            rotation = 90
        else:  # 90 - Right player - rotate 270° to face them
            rotation = 270
        
        renderer.draw_text(
            text, x, y, 'Arial', font_size, color,
            anchor_x='center', anchor_y='center',
            rotation=rotation
        )
    



def create_monopoly_buy_popup(player_money: int, property_name: str, price: int) -> List[Tuple[str, int, Tuple[int, int, int]]]:
    """Create buy property popup text lines"""
    return [
        ("BUY PROPERTY", 14, (180, 180, 180)),
        (property_name, 18, (255, 255, 255)),
        (f"Price: ${price}", 16, (100, 255, 100)),
        (f"Balance: ${player_money}", 14, (255, 255, 100))
    ]


def create_monopoly_card_popup(card_text: str, deck_type: str) -> List[Tuple[str, int, Tuple[int, int, int]]]:
    """Create card popup text lines"""
    title = "CHANCE" if deck_type == "chance" else "COMMUNITY CHEST"
    return [
        (title, 16, (255, 215, 0)),
        (card_text, 14, (255, 255, 255))
    ]


def create_monopoly_properties_popup(properties: List[Tuple[str, Tuple[int, int, int]]]) -> List[Tuple[str, int, Tuple[int, int, int]]]:
    """Create properties list popup text lines with color-coded properties
    
    Args:
        properties: List of tuples (property_name, property_color)
    
    Returns:
        List of text lines (text, font_size, color)
    """
    # Title at the very top
    lines = [("YOUR PROPERTIES", 16, (255, 215, 0))]
    
    # List each property with its color
    for prop_name, prop_color in properties:
        # Use the property's color group color for the text
        lines.append((prop_name, 14, prop_color))
    
    return lines


def create_blackjack_bet_popup(chips: int, current_bet: int) -> List[Tuple[str, int, Tuple[int, int, int]]]:
    """Create blackjack betting popup text lines"""
    return [
        ("PLACE YOUR BET", 16, (180, 180, 180)),
        (f"Chips: ${chips}", 16, (255, 255, 100)),
        (f"Current Bet: ${current_bet}", 14, (200, 200, 200))
    ]


def create_info_popup(title: str, message: str) -> List[Tuple[str, int, Tuple[int, int, int]]]:
    """Create generic info popup text lines"""
    return [
        (title, 16, (255, 215, 0)),
        (message, 14, (255, 255, 255))
    ]
