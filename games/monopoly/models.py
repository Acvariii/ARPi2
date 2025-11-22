"""Monopoly game data models - Property and Player classes"""
from typing import Dict, List, Optional, Tuple
from games.monopoly.data import STARTING_MONEY, PROPERTY_GROUPS


class Property:
    """Property space on the board"""
    
    def __init__(self, data: Dict):
        self.data = data
        self.houses = 0
        self.is_mortgaged = False
        self.owner: Optional[int] = None
    
    def get_rent(self, dice_roll: Optional[int] = None, owned_in_group: int = 1) -> int:
        if self.is_mortgaged:
            return 0
        
        prop_type = self.data.get("type")
        
        if prop_type == "property":
            rent_array = self.data.get("rent", [0])
            return rent_array[self.houses] if self.houses < len(rent_array) else 0
        
        elif prop_type == "railroad":
            rent_array = self.data.get("rent", [25, 50, 100, 200])
            idx = min(owned_in_group - 1, len(rent_array) - 1)
            return rent_array[idx]
        
        elif prop_type == "utility":
            multiplier = 4 if owned_in_group == 1 else 10
            return (dice_roll or 0) * multiplier
        
        return 0
    
    def can_build_house(self, has_monopoly: bool, all_props_in_group: List['Property']) -> bool:
        if not has_monopoly or self.is_mortgaged:
            return False
        
        if self.houses >= 5:
            return False
        
        for prop in all_props_in_group:
            if prop.houses < self.houses:
                return False
        
        return True
    
    def can_sell_house(self) -> bool:
        return self.houses > 0 and not self.is_mortgaged
    
    def mortgage(self) -> int:
        if self.is_mortgaged or self.houses > 0:
            return 0
        self.is_mortgaged = True
        return self.data.get("mortgage_value", 0)
    
    def unmortgage(self, player_money: int) -> bool:
        if not self.is_mortgaged:
            return False
        cost = int(self.data.get("mortgage_value", 0) * 1.1)
        if player_money >= cost:
            self.is_mortgaged = False
            return True
        return False


class Player:
    """Monopoly player"""
    
    def __init__(self, idx: int, color: Tuple[int, int, int]):
        self.idx = idx
        self.color = color
        self.money = STARTING_MONEY
        self.position = 0
        self.properties: List[int] = []
        self.in_jail = False
        self.jail_turns = 0
        self.get_out_of_jail_cards = 0
        self.consecutive_doubles = 0
        self.is_bankrupt = False
        
        self.move_path: List[int] = []
        self.move_start = 0.0
        self.move_from = 0
        self.is_moving = False
    
    def add_money(self, amount: int):
        self.money += amount
    
    def remove_money(self, amount: int) -> bool:
        if self.money >= amount:
            self.money -= amount
            return True
        return False
    
    def owns_property_at(self, position: int) -> bool:
        return position in self.properties
    
    def get_properties_in_group(self, group: str, all_properties: List) -> List[int]:
        return [idx for idx in self.properties 
                if all_properties[idx].data.get("group") == group]
    
    def has_monopoly(self, group: str, all_properties: List) -> bool:
        owned = self.get_properties_in_group(group, all_properties)
        required = len(PROPERTY_GROUPS.get(group, []))
        return len(owned) == required
    
    def get_total_houses(self, all_properties: List) -> int:
        return sum(all_properties[idx].houses for idx in self.properties 
                if all_properties[idx].houses < 5)
    
    def get_total_hotels(self, all_properties: List) -> int:
        return sum(1 for idx in self.properties if all_properties[idx].houses == 5)
