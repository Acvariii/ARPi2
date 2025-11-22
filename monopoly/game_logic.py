import time
import random
from typing import Dict, Optional
from monopoly_data import (
    PASSING_GO_MONEY, INCOME_TAX, LUXURY_TAX, 
    JAIL_POSITION, GO_TO_JAIL_POSITION, JAIL_FINE, MAX_JAIL_TURNS,
    COMMUNITY_CHEST_CARDS, CHANCE_CARDS
)


class GameLogic:
    
    @staticmethod
    def move_player(player, spaces: int):
        old_pos = player.position
        player.move_from = old_pos
        
        player.move_path = []
        for i in range(1, abs(spaces) + 1):
            if spaces > 0:
                player.move_path.append((old_pos + i) % 40)
            else:
                player.move_path.append((old_pos - i) % 40)
        
        player.is_moving = True
        player.move_start = time.time()
    
    @staticmethod
    def check_passed_go(player) -> bool:
        if player.move_from > player.position and len(player.move_path) > 0:
            return True
        return False
    
    @staticmethod
    def send_to_jail(player):
        player.position = JAIL_POSITION
        player.in_jail = True
        player.jail_turns = 0
        player.consecutive_doubles = 0
        player.move_path = []
    
    @staticmethod
    def draw_card(deck_type: str, chance_deck: list, community_chest_deck: list) -> Dict:
        if deck_type == "chance":
            if not chance_deck:
                chance_deck.extend(CHANCE_CARDS)
                random.shuffle(chance_deck)
            return chance_deck.pop(0)
        else:
            if not community_chest_deck:
                community_chest_deck.extend(COMMUNITY_CHEST_CARDS)
                random.shuffle(community_chest_deck)
            return community_chest_deck.pop(0)
    
    @staticmethod
    def calculate_rent(space, dice_roll: Optional[int], owner, properties) -> int:
        group = space.data.get("group")
        owned_in_group = 1
        
        if group in ("Railroad", "Utility"):
            owned_in_group = sum(1 for idx in owner.properties 
                                if properties[idx].data.get("group") == group)
        
        rent = space.get_rent(dice_roll, owned_in_group)
        
        if group and group not in ("Railroad", "Utility"):
            if owner.has_monopoly(group, properties) and space.houses == 0:
                rent *= 2
        
        return rent
