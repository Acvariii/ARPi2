"""Property class for Monopoly game."""
from typing import Dict, List, Optional


class Property:
    """Represents a property with houses/hotels."""
    
    def __init__(self, data: Dict):
        self.data = data
        self.houses = 0  # 0-4 houses, 5 = hotel
        self.is_mortgaged = False
        self.owner: Optional[int] = None
    
    def get_rent(self, dice_roll: Optional[int] = None, owned_in_group: int = 1) -> int:
        """Calculate rent based on houses and ownership."""
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
            # Utilities: 4x dice if 1 owned, 10x dice if both owned
            multiplier = 4 if owned_in_group == 1 else 10
            return (dice_roll or 0) * multiplier
        
        return 0
    
    def can_build_house(self, has_monopoly: bool, all_props_in_group: List['Property']) -> bool:
        """Check if can build a house on this property."""
        if not has_monopoly or self.is_mortgaged:
            return False
        
        # Can't build hotels if already have one
        if self.houses >= 5:
            return False
        
        # Must build evenly across monopoly
        for prop in all_props_in_group:
            if prop.houses < self.houses:
                return False
        
        return True
    
    def can_sell_house(self) -> bool:
        """Check if can sell a house."""
        return self.houses > 0 and not self.is_mortgaged
    
    def mortgage(self) -> int:
        """Mortgage the property and return cash received."""
        if self.is_mortgaged or self.houses > 0:
            return 0
        self.is_mortgaged = True
        return self.data.get("mortgage_value", 0)
    
    def unmortgage(self, player_money: int) -> bool:
        """Unmortgage if player has enough money."""
        if not self.is_mortgaged:
            return False
        cost = int(self.data.get("mortgage_value", 0) * 1.1)  # 10% interest
        if player_money >= cost:
            self.is_mortgaged = False
            return True
        return False