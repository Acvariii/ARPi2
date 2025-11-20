from typing import List, Tuple
from monopoly_data import STARTING_MONEY, PROPERTY_GROUPS


class Player:
    
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
