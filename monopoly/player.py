"""Player class for Monopoly game."""
from typing import List, Tuple
from monopoly_data import STARTING_MONEY, PROPERTY_GROUPS


class Player:
    """Represents a player in the game."""
    
    def __init__(self, idx: int, color: Tuple[int, int, int]):
        self.idx = idx
        self.color = color
        self.money = STARTING_MONEY
        self.position = 0
        self.properties: List[int] = []  # Indices of owned properties
        self.in_jail = False
        self.jail_turns = 0
        self.get_out_of_jail_cards = 0
        self.consecutive_doubles = 0
        self.is_bankrupt = False
        
        # Animation state
        self.move_path: List[int] = []
        self.move_start = 0.0
        self.move_from = 0
        self.is_moving = False
    
    def add_money(self, amount: int):
        """Add money to player."""
        self.money += amount
    
    def remove_money(self, amount: int) -> bool:
        """Remove money from player. Returns False if can't afford."""
        if self.money >= amount:
            self.money -= amount
            return True
        return False
    
    def owns_property_at(self, position: int) -> bool:
        """Check if player owns property at position."""
        return position in self.properties
    
    def get_properties_in_group(self, group: str, all_properties: List) -> List[int]:
        """Get all owned properties in a color group."""
        return [idx for idx in self.properties 
                if all_properties[idx].data.get("group") == group]
    
    def has_monopoly(self, group: str, all_properties: List) -> bool:
        """Check if player has monopoly on a color group."""
        owned = self.get_properties_in_group(group, all_properties)
        required = len(PROPERTY_GROUPS.get(group, []))
        return len(owned) == required
    
    def get_total_houses(self, all_properties: List) -> int:
        """Count total houses owned."""
        return sum(all_properties[idx].houses for idx in self.properties 
                if all_properties[idx].houses < 5)
    
    def get_total_hotels(self, all_properties: List) -> int:
        """Count total hotels owned."""
        return sum(1 for idx in self.properties if all_properties[idx].houses == 5)