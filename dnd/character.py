import json
import os
from typing import Dict, List, Optional

RACES = ["Human", "Elf", "Dwarf", "Halfling", "Orc", "Tiefling"]
CLASSES = ["Fighter", "Wizard", "Rogue", "Cleric", "Ranger", "Paladin"]
ALIGNMENTS = ["Lawful Good", "Neutral Good", "Chaotic Good", "Lawful Neutral", "True Neutral", "Chaotic Neutral", "Lawful Evil", "Neutral Evil", "Chaotic Evil"]

ABILITY_SCORES = ["Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma"]

CLASS_HP = {
    "Fighter": 10,
    "Wizard": 6,
    "Rogue": 8,
    "Cleric": 8,
    "Ranger": 10,
    "Paladin": 10
}

CLASS_SKILLS = {
    "Fighter": ["Athletics", "Intimidation", "Survival"],
    "Wizard": ["Arcana", "History", "Investigation"],
    "Rogue": ["Stealth", "Sleight of Hand", "Acrobatics"],
    "Cleric": ["Medicine", "Insight", "Religion"],
    "Ranger": ["Nature", "Survival", "Animal Handling"],
    "Paladin": ["Religion", "Persuasion", "Athletics"]
}


class Character:
    
    def __init__(self, name: str = "", player_color: tuple = (255, 255, 255)):
        self.name = name
        self.player_color = player_color
        self.race = ""
        self.char_class = ""
        self.level = 1
        self.alignment = ""
        
        self.abilities = {
            "Strength": 10,
            "Dexterity": 10,
            "Constitution": 10,
            "Intelligence": 10,
            "Wisdom": 10,
            "Charisma": 10
        }
        
        self.max_hp = 10
        self.current_hp = 10
        self.armor_class = 10
        
        self.skills = []
        self.inventory = []
        self.gold = 0
        
        self.experience = 0
        self.background = ""
    
    def get_ability_modifier(self, ability: str) -> int:
        score = self.abilities.get(ability, 10)
        return (score - 10) // 2
    
    def calculate_hp(self):
        base_hp = CLASS_HP.get(self.char_class, 8)
        con_mod = self.get_ability_modifier("Constitution")
        self.max_hp = base_hp + con_mod
        self.current_hp = self.max_hp
    
    def calculate_ac(self):
        dex_mod = self.get_ability_modifier("Dexterity")
        self.armor_class = 10 + dex_mod
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "player_color": self.player_color,
            "race": self.race,
            "char_class": self.char_class,
            "level": self.level,
            "alignment": self.alignment,
            "abilities": self.abilities,
            "max_hp": self.max_hp,
            "current_hp": self.current_hp,
            "armor_class": self.armor_class,
            "skills": self.skills,
            "inventory": self.inventory,
            "gold": self.gold,
            "experience": self.experience,
            "background": self.background
        }
    
    @staticmethod
    def from_dict(data: Dict) -> 'Character':
        char = Character(data.get("name", ""), tuple(data.get("player_color", (255, 255, 255))))
        char.race = data.get("race", "")
        char.char_class = data.get("char_class", "")
        char.level = data.get("level", 1)
        char.alignment = data.get("alignment", "")
        char.abilities = data.get("abilities", {})
        char.max_hp = data.get("max_hp", 10)
        char.current_hp = data.get("current_hp", 10)
        char.armor_class = data.get("armor_class", 10)
        char.skills = data.get("skills", [])
        char.inventory = data.get("inventory", [])
        char.gold = data.get("gold", 0)
        char.experience = data.get("experience", 0)
        char.background = data.get("background", "")
        return char
    
    def save_to_file(self, player_idx: int):
        os.makedirs("dnd_saves", exist_ok=True)
        filename = f"dnd_saves/character_{player_idx}.json"
        with open(filename, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @staticmethod
    def load_from_file(player_idx: int) -> Optional['Character']:
        filename = f"dnd_saves/character_{player_idx}.json"
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                data = json.load(f)
                return Character.from_dict(data)
        return None
    
    @staticmethod
    def character_exists(player_idx: int) -> bool:
        filename = f"dnd_saves/character_{player_idx}.json"
        return os.path.exists(filename)
