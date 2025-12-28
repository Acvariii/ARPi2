import json
import os
import random
import time
from typing import Any, Dict, List, Optional, Tuple

RACES = ["Human", "Elf", "Dwarf", "Halfling", "Orc", "Tiefling"]
CLASSES = ["Fighter", "Wizard", "Rogue", "Cleric", "Ranger", "Paladin"]

RACE_NAMES = {
    "Human": {
        "first": ["Aldric", "Brenna", "Cedric", "Diana", "Erik", "Fiona", "Gareth", "Helena", "Ivan", "Jade"],
        "last": ["Ironheart", "Stormwind", "Blackwood", "Silverstone", "Goldleaf", "Brightblade", "Darkwater", "Swiftarrow"]
    },
    "Elf": {
        "first": ["Aelrindel", "Sylvari", "Thranduil", "Elaria", "Caladrel", "Liriel", "Galadon", "Aria", "Eldrin", "Mirial"],
        "last": ["Moonwhisper", "Starweaver", "Leafdancer", "Sunfire", "Nightbreeze", "Dawnstrider", "Shadowleaf", "Skysong"]
    },
    "Dwarf": {
        "first": ["Thorin", "Gimli", "Balin", "Dwalin", "Bombur", "Bofur", "Grilda", "Helga", "Kathra", "Vistra"],
        "last": ["Ironforge", "Stonefist", "Hammerstrike", "Axebreaker", "Goldbeard", "Rockhelm", "Steelshield", "Fireborn"]
    },
    "Halfling": {
        "first": ["Pippin", "Merry", "Bilbo", "Rosie", "Daisy", "Willow", "Bramble", "Clover", "Finnegan", "Poppy"],
        "last": ["Goodbarrel", "Lightfoot", "Underbough", "Tealeaf", "Thornburrow", "Greenbottle", "Hilltopple", "Meadowbrook"]
    },
    "Orc": {
        "first": ["Grommash", "Thrall", "Durotan", "Garrosh", "Grok", "Urzul", "Shakara", "Zugra", "Gorza", "Krazh"],
        "last": ["Bloodfang", "Skullcrusher", "Warmaker", "Bonegrinder", "Ironclaw", "Thunderfist", "Blacktooth", "Ashbringer"]
    },
    "Tiefling": {
        "first": ["Zariel", "Mephistopheles", "Ashlyn", "Brimstone", "Crimson", "Ember", "Inferno", "Raven", "Sable", "Vesper"],
        "last": ["Hellfire", "Soulforge", "Darkflame", "Shadowhorn", "Crimsonwing", "Nightfall", "Doomcaller", "Voidwalker"]
    }
}

CLASS_TITLES = {
    "Fighter": ["the Bold", "the Brave", "the Mighty", "the Valiant", "the Fearless", "the Champion"],
    "Wizard": ["the Wise", "the Arcane", "the Mystic", "the Enlightened", "the Scholarly", "the Spellweaver"],
    "Rogue": ["the Swift", "the Shadow", "the Cunning", "the Silent", "the Sly", "the Phantom"],
    "Cleric": ["the Blessed", "the Faithful", "the Divine", "the Holy", "the Righteous", "the Devoted"],
    "Ranger": ["the Tracker", "the Hunter", "the Wild", "the Wanderer", "the Scout", "the Pathfinder"],
    "Paladin": ["the Just", "the Defender", "the Noble", "the Crusader", "the Guardian", "the Lightbringer"]
}

def generate_character_name(race: str, char_class: str) -> str:
    if race not in RACE_NAMES:
        return "Unknown Hero"
    
    first_name = random.choice(RACE_NAMES[race]["first"])
    
    use_title = random.random() > 0.5
    if use_title and char_class in CLASS_TITLES:
        title = random.choice(CLASS_TITLES[char_class])
        return f"{first_name} {title}"
    else:
        last_name = random.choice(RACE_NAMES[race]["last"])
        return f"{first_name} {last_name}"
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
        # Inventory items are dicts (back-compat: old saves may contain strings).
        self.inventory: List[Dict[str, Any]] = []
        # Equipment: slot -> item_id
        self.equipment: Dict[str, str] = {}
        self.gold = 0
        
        self.experience = 0
        self.background = ""
        # Extended character flavor/build metadata
        self.background_answers: Dict[str, str] = {}
        self.feats: List[str] = []
        self.features: List[str] = []

    @staticmethod
    def _new_item_id() -> str:
        return f"{int(time.time() * 1000)}_{random.randint(1000, 9999)}"

    @staticmethod
    def _normalize_item(raw: Any) -> Optional[Dict[str, Any]]:
        if raw is None:
            return None
        if isinstance(raw, str):
            name = raw.strip()
            if not name:
                return None
            return {"id": Character._new_item_id(), "name": name, "kind": "misc"}
        if isinstance(raw, dict):
            name = str(raw.get("name") or "").strip()
            if not name:
                return None
            kind = str(raw.get("kind") or "misc").strip() or "misc"
            item_id = str(raw.get("id") or "").strip() or Character._new_item_id()
            item: Dict[str, Any] = {"id": item_id, "name": name, "kind": kind}
            if kind == "gear":
                slot = str(raw.get("slot") or "").strip()
                if slot:
                    item["slot"] = slot
                try:
                    item["ac_bonus"] = int(raw.get("ac_bonus", 0) or 0)
                except Exception:
                    item["ac_bonus"] = 0
                ability_bonuses = raw.get("ability_bonuses")
                if isinstance(ability_bonuses, dict):
                    cleaned: Dict[str, int] = {}
                    for k, v in ability_bonuses.items():
                        try:
                            cleaned[str(k)] = int(v)
                        except Exception:
                            continue
                    if cleaned:
                        item["ability_bonuses"] = cleaned
            elif kind == "consumable":
                effect = raw.get("effect")
                if isinstance(effect, dict):
                    etype = str(effect.get("type") or "").strip() or "heal"
                    try:
                        amount = int(effect.get("amount", 0) or 0)
                    except Exception:
                        amount = 0
                    item["effect"] = {"type": etype, "amount": amount}
            return item
        return None

    def normalize_inventory(self):
        items: List[Dict[str, Any]] = []
        for raw in list(self.inventory or []):
            item = Character._normalize_item(raw)
            if item is not None:
                items.append(item)
        self.inventory = items

        # Remove equipped references that no longer exist.
        valid_ids = {str(it.get("id")) for it in self.inventory if isinstance(it, dict) and it.get("id")}
        eq = dict(self.equipment or {})
        for slot, item_id in list(eq.items()):
            if not item_id or str(item_id) not in valid_ids:
                eq.pop(slot, None)
        self.equipment = eq

    def get_item_by_id(self, item_id: str) -> Optional[Dict[str, Any]]:
        if not item_id:
            return None
        for it in list(self.inventory or []):
            try:
                if str(it.get("id")) == str(item_id):
                    return it
            except Exception:
                continue
        return None

    def add_item(self, raw: Any) -> Optional[Dict[str, Any]]:
        item = Character._normalize_item(raw)
        if item is None:
            return None
        self.normalize_inventory()
        self.inventory.append(item)
        return item

    def get_equipped_ability_bonuses(self) -> Dict[str, int]:
        bonuses: Dict[str, int] = {}
        self.normalize_inventory()
        for slot, item_id in (self.equipment or {}).items():
            it = self.get_item_by_id(str(item_id))
            if not it or str(it.get("kind")) != "gear":
                continue
            ab = it.get("ability_bonuses")
            if not isinstance(ab, dict):
                continue
            for k, v in ab.items():
                try:
                    bonuses[str(k)] = int(bonuses.get(str(k), 0) or 0) + int(v)
                except Exception:
                    continue
        return bonuses

    def get_effective_ability_score(self, ability: str) -> int:
        base = int(self.abilities.get(ability, 10) or 10)
        bonuses = self.get_equipped_ability_bonuses()
        bonus = int(bonuses.get(ability, 0) or 0)
        return base + bonus
    
    def get_ability_modifier(self, ability: str) -> int:
        score = self.get_effective_ability_score(ability)
        return (score - 10) // 2
    
    def calculate_hp(self, reset_current: bool = True):
        base_hp = CLASS_HP.get(self.char_class, 8)
        con_mod = self.get_ability_modifier("Constitution")
        self.max_hp = max(1, int(base_hp + con_mod))
        if reset_current:
            self.current_hp = self.max_hp
        else:
            try:
                self.current_hp = max(0, min(int(self.current_hp or 0), int(self.max_hp or 1)))
            except Exception:
                self.current_hp = self.max_hp
    
    def calculate_ac(self):
        dex_mod = self.get_ability_modifier("Dexterity")
        bonus_ac = 0
        self.normalize_inventory()
        for slot, item_id in (self.equipment or {}).items():
            it = self.get_item_by_id(str(item_id))
            if not it or str(it.get("kind")) != "gear":
                continue
            try:
                bonus_ac += int(it.get("ac_bonus", 0) or 0)
            except Exception:
                continue
        self.armor_class = int(10 + dex_mod + bonus_ac)

    def update_derived_stats(self, reset_current_hp: bool = False):
        # Recalculate AC/HP based on equipped bonuses.
        try:
            self.calculate_ac()
        except Exception:
            pass
        try:
            self.calculate_hp(reset_current=bool(reset_current_hp))
        except Exception:
            pass

    def equip_item(self, item_id: str) -> bool:
        self.normalize_inventory()
        it = self.get_item_by_id(str(item_id))
        if not it or str(it.get("kind")) != "gear":
            return False
        slot = str(it.get("slot") or "").strip()
        if not slot:
            return False
        self.equipment = dict(self.equipment or {})
        self.equipment[slot] = str(it.get("id"))
        self.update_derived_stats(reset_current_hp=False)
        return True

    def unequip_slot(self, slot: str) -> bool:
        slot = str(slot or "").strip()
        if not slot:
            return False
        eq = dict(self.equipment or {})
        if slot not in eq:
            return False
        eq.pop(slot, None)
        self.equipment = eq
        self.update_derived_stats(reset_current_hp=False)
        return True

    def use_item(self, item_id: str) -> bool:
        self.normalize_inventory()
        it = self.get_item_by_id(str(item_id))
        if not it or str(it.get("kind")) != "consumable":
            return False
        effect = it.get("effect")
        if not isinstance(effect, dict):
            return False
        etype = str(effect.get("type") or "").strip() or "heal"
        if etype != "heal":
            return False
        try:
            amount = int(effect.get("amount", 0) or 0)
        except Exception:
            amount = 0
        if amount <= 0:
            return False
        try:
            self.current_hp = min(int(self.max_hp or 1), int(self.current_hp or 0) + amount)
        except Exception:
            pass
        # Remove item after use.
        self.inventory = [x for x in (self.inventory or []) if str(x.get("id")) != str(item_id)]
        # Clean equipment if it somehow referenced this id.
        self.normalize_inventory()
        return True
    
    def to_dict(self) -> Dict:
        self.normalize_inventory()
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
            "equipment": self.equipment,
            "gold": self.gold,
            "experience": self.experience,
            "background": self.background,
            "background_answers": self.background_answers,
            "feats": self.feats,
            "features": self.features,
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
        char.equipment = data.get("equipment", {}) or {}
        char.gold = data.get("gold", 0)
        char.experience = data.get("experience", 0)
        char.background = data.get("background", "")
        ba = data.get("background_answers", {})
        char.background_answers = ba if isinstance(ba, dict) else {}
        feats = data.get("feats", [])
        char.feats = list(feats) if isinstance(feats, list) else []
        features = data.get("features", [])
        char.features = list(features) if isinstance(features, list) else []
        try:
            char.normalize_inventory()
            char.update_derived_stats(reset_current_hp=False)
        except Exception:
            pass
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


class Enemy:
    """Monster/NPC enemy for combat encounters"""
    
    def __init__(self, template: Dict):
        self.name = template["name"]
        self.max_hp = template["hp"]
        self.current_hp = template["hp"]
        self.armor_class = template["ac"]
        self.abilities = template["abilities"]
        self.attacks = template["attacks"]
        self.cr = template["cr"]
        self.xp = template["xp"]
        self.special = template.get("special", None)
        self.conditions = []
        self.initiative = 0
    
    def get_ability_modifier(self, ability: str) -> int:
        score = self.abilities.get(ability, 10)
        return (score - 10) // 2
    
    def is_alive(self) -> bool:
        return self.current_hp > 0
    
    def take_damage(self, amount: int):
        self.current_hp = max(0, self.current_hp - amount)
    
    def heal(self, amount: int):
        self.current_hp = min(self.max_hp, self.current_hp + amount)
