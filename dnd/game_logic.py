import random
from typing import Dict, List, Optional


class DiceRoller:
    
    @staticmethod
    def roll(num_dice: int, dice_sides: int, modifier: int = 0) -> int:
        total = sum(random.randint(1, dice_sides) for _ in range(num_dice))
        return total + modifier
    
    @staticmethod
    def roll_d20(modifier: int = 0) -> int:
        return DiceRoller.roll(1, 20, modifier)
    
    @staticmethod
    def roll_advantage() -> int:
        return max(random.randint(1, 20), random.randint(1, 20))
    
    @staticmethod
    def roll_disadvantage() -> int:
        return min(random.randint(1, 20), random.randint(1, 20))
    
    @staticmethod
    def roll_ability_score() -> int:
        rolls = [random.randint(1, 6) for _ in range(4)]
        rolls.remove(min(rolls))
        return sum(rolls)


class CombatManager:
    
    def __init__(self):
        self.initiative_order = []
        self.current_turn = 0
        self.round_number = 1
    
    def roll_initiative(self, characters: List, enemies: List = None):
        self.initiative_order = []
        
        for char in characters:
            if char:
                dex_mod = (char.abilities.get("Dexterity", 10) - 10) // 2
                initiative = DiceRoller.roll_d20(dex_mod)
                self.initiative_order.append({"entity": char, "initiative": initiative, "is_enemy": False})
        
        if enemies:
            for enemy in enemies:
                initiative = DiceRoller.roll_d20()
                self.initiative_order.append({"entity": enemy, "initiative": initiative, "is_enemy": True})
        
        self.initiative_order.sort(key=lambda x: x["initiative"], reverse=True)
        self.current_turn = 0
        self.round_number = 1
    
    def next_turn(self):
        self.current_turn = (self.current_turn + 1) % len(self.initiative_order)
        if self.current_turn == 0:
            self.round_number += 1
    
    def get_current_entity(self):
        if self.initiative_order:
            return self.initiative_order[self.current_turn]["entity"]
        return None


class SkillChecker:
    
    SKILLS = {
        "Acrobatics": "Dexterity",
        "Animal Handling": "Wisdom",
        "Arcana": "Intelligence",
        "Athletics": "Strength",
        "Deception": "Charisma",
        "History": "Intelligence",
        "Insight": "Wisdom",
        "Intimidation": "Charisma",
        "Investigation": "Intelligence",
        "Medicine": "Wisdom",
        "Nature": "Intelligence",
        "Perception": "Wisdom",
        "Performance": "Charisma",
        "Persuasion": "Charisma",
        "Religion": "Intelligence",
        "Sleight of Hand": "Dexterity",
        "Stealth": "Dexterity",
        "Survival": "Wisdom"
    }
    
    @staticmethod
    def check_skill(character, skill_name: str, dc: int) -> Dict:
        ability = SkillChecker.SKILLS.get(skill_name, "Strength")
        ability_mod = (character.abilities.get(ability, 10) - 10) // 2
        proficiency = 2 if skill_name in character.skills else 0
        
        roll = DiceRoller.roll_d20()
        total = roll + ability_mod + proficiency
        
        success = total >= dc
        
        return {
            "roll": roll,
            "modifier": ability_mod + proficiency,
            "total": total,
            "dc": dc,
            "success": success,
            "skill": skill_name
        }
    
    @staticmethod
    def saving_throw(character, ability: str, dc: int) -> Dict:
        ability_mod = (character.abilities.get(ability, 10) - 10) // 2
        roll = DiceRoller.roll_d20()
        total = roll + ability_mod
        
        success = total >= dc
        
        return {
            "roll": roll,
            "modifier": ability_mod,
            "total": total,
            "dc": dc,
            "success": success,
            "ability": ability
        }
