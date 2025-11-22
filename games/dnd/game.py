"""
D&D Game - Complete gameplay system with beautiful character creation
Wrapper for the main game launcher
"""

from core.renderer import PygletRenderer
from games.dnd.gameplay_new import DnDGameSession


class DnDCharacterCreation:
    """Compatibility wrapper - forwards to DnDGameSession"""
    
    def __init__(self, width: int, height: int, renderer: PygletRenderer):
        # Create the actual game session
        self.game = DnDGameSession(width, height, renderer)
        self.width = width
        self.height = height
        self.renderer = renderer
    
    def handle_input(self, fingertips):
        """Forward input handling to game session"""
        return self.game.handle_input(fingertips)
    
    def update(self, dt: float):
        """Forward update to game session"""
        self.game.update(dt)
    
    def draw(self):
        """Forward draw to game session"""
        self.game.draw()
    
    def draw_immediate(self):
        """Forward immediate draw to game session"""
        self.game.draw_immediate()

