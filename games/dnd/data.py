"""D&D Game Data - Monsters, Items, Spells, and Game Constants"""
from typing import Dict, List, Tuple

# Monster templates for DM to spawn
MONSTERS = {
    "Goblin": {
        "name": "Goblin",
        "cr": 0.25,
        "hp": 7,
        "ac": 15,
        "abilities": {"Strength": 8, "Dexterity": 14, "Constitution": 10, "Intelligence": 10, "Wisdom": 8, "Charisma": 8},
        "attacks": [
            {"name": "Scimitar", "bonus": 4, "damage": "1d6+2", "type": "slashing"},
            {"name": "Shortbow", "bonus": 4, "damage": "1d6+2", "type": "piercing", "range": True}
        ],
        "xp": 50
    },
    "Orc": {
        "name": "Orc",
        "cr": 0.5,
        "hp": 15,
        "ac": 13,
        "abilities": {"Strength": 16, "Dexterity": 12, "Constitution": 16, "Intelligence": 7, "Wisdom": 11, "Charisma": 10},
        "attacks": [
            {"name": "Greataxe", "bonus": 5, "damage": "1d12+3", "type": "slashing"},
            {"name": "Javelin", "bonus": 5, "damage": "1d6+3", "type": "piercing", "range": True}
        ],
        "xp": 100
    },
    "Skeleton": {
        "name": "Skeleton",
        "cr": 0.25,
        "hp": 13,
        "ac": 13,
        "abilities": {"Strength": 10, "Dexterity": 14, "Constitution": 15, "Intelligence": 6, "Wisdom": 8, "Charisma": 5},
        "attacks": [
            {"name": "Shortsword", "bonus": 4, "damage": "1d6+2", "type": "piercing"},
            {"name": "Shortbow", "bonus": 4, "damage": "1d6+2", "type": "piercing", "range": True}
        ],
        "xp": 50
    },
    "Wolf": {
        "name": "Wolf",
        "cr": 0.25,
        "hp": 11,
        "ac": 13,
        "abilities": {"Strength": 12, "Dexterity": 15, "Constitution": 12, "Intelligence": 3, "Wisdom": 12, "Charisma": 6},
        "attacks": [
            {"name": "Bite", "bonus": 4, "damage": "2d4+2", "type": "piercing"}
        ],
        "xp": 50
    },
    "Ogre": {
        "name": "Ogre",
        "cr": 2,
        "hp": 59,
        "ac": 11,
        "abilities": {"Strength": 19, "Dexterity": 8, "Constitution": 16, "Intelligence": 5, "Wisdom": 7, "Charisma": 7},
        "attacks": [
            {"name": "Greatclub", "bonus": 6, "damage": "2d8+4", "type": "bludgeoning"},
            {"name": "Javelin", "bonus": 6, "damage": "2d6+4", "type": "piercing", "range": True}
        ],
        "xp": 450
    },
    "Troll": {
        "name": "Troll",
        "cr": 5,
        "hp": 84,
        "ac": 15,
        "abilities": {"Strength": 18, "Dexterity": 13, "Constitution": 20, "Intelligence": 7, "Wisdom": 9, "Charisma": 7},
        "attacks": [
            {"name": "Claw", "bonus": 7, "damage": "2d6+4", "type": "slashing"},
            {"name": "Bite", "bonus": 7, "damage": "2d6+4", "type": "piercing"}
        ],
        "special": "Regeneration: 10 HP per turn",
        "xp": 1800
    },
    "Dragon Wyrmling": {
        "name": "Dragon Wyrmling",
        "cr": 4,
        "hp": 75,
        "ac": 17,
        "abilities": {"Strength": 19, "Dexterity": 10, "Constitution": 17, "Intelligence": 12, "Wisdom": 11, "Charisma": 15},
        "attacks": [
            {"name": "Bite", "bonus": 6, "damage": "1d10+4", "type": "piercing"},
            {"name": "Breath Weapon", "bonus": 0, "damage": "7d6", "type": "fire", "aoe": True}
        ],
        "xp": 1100
    }
}

# Common items and equipment
ITEMS = {
    "Weapons": {
        "Longsword": {"damage": "1d8", "type": "slashing", "cost": 15, "weight": 3},
        "Greatsword": {"damage": "2d6", "type": "slashing", "cost": 50, "weight": 6},
        "Dagger": {"damage": "1d4", "type": "piercing", "cost": 2, "weight": 1},
        "Shortbow": {"damage": "1d6", "type": "piercing", "cost": 25, "weight": 2, "range": True},
        "Longbow": {"damage": "1d8", "type": "piercing", "cost": 50, "weight": 2, "range": True},
        "Warhammer": {"damage": "1d8", "type": "bludgeoning", "cost": 15, "weight": 2},
        "Staff": {"damage": "1d6", "type": "bludgeoning", "cost": 5, "weight": 4},
        "Rapier": {"damage": "1d8", "type": "piercing", "cost": 25, "weight": 2}
    },
    "Armor": {
        "Leather Armor": {"ac": 11, "cost": 10, "weight": 10},
        "Chain Mail": {"ac": 16, "cost": 75, "weight": 55},
        "Plate Armor": {"ac": 18, "cost": 1500, "weight": 65},
        "Shield": {"ac": 2, "cost": 10, "weight": 6}
    },
    "Consumables": {
        "Healing Potion": {"effect": "heal", "amount": "2d4+2", "cost": 50},
        "Greater Healing Potion": {"effect": "heal", "amount": "4d4+4", "cost": 150},
        "Antidote": {"effect": "cure_poison", "cost": 50},
        "Torch": {"effect": "light", "duration": "1 hour", "cost": 1}
    },
    "Magic Items": {
        "Wand of Magic Missiles": {"charges": 7, "effect": "3d4+3 force damage", "cost": 500},
        "Ring of Protection": {"bonus": "+1 AC and saves", "cost": 1000},
        "Cloak of Elvenkind": {"bonus": "Advantage on Stealth", "cost": 750},
        "Boots of Speed": {"bonus": "Double movement", "cost": 800}
    }
}

# Common spells by level
SPELLS = {
    0: {  # Cantrips
        "Fire Bolt": {"damage": "1d10", "type": "fire", "range": 120},
        "Ray of Frost": {"damage": "1d8", "type": "cold", "range": 60, "effect": "slow"},
        "Sacred Flame": {"damage": "1d8", "type": "radiant", "save": "Dexterity"},
        "Eldritch Blast": {"damage": "1d10", "type": "force", "range": 120}
    },
    1: {
        "Magic Missile": {"damage": "3d4+3", "type": "force", "auto_hit": True},
        "Cure Wounds": {"heal": "1d8+MOD", "touch": True},
        "Shield": {"effect": "+5 AC until start of your next turn", "reaction": True},
        "Burning Hands": {"damage": "3d6", "type": "fire", "aoe": "15ft cone"}
    },
    2: {
        "Scorching Ray": {"damage": "2d6 per ray", "type": "fire", "rays": 3},
        "Hold Person": {"effect": "Paralyzed", "save": "Wisdom"},
        "Invisibility": {"effect": "Target invisible until attacks"},
        "Spiritual Weapon": {"damage": "1d8+MOD", "type": "force", "bonus_action": True}
    },
    3: {
        "Fireball": {"damage": "8d6", "type": "fire", "aoe": "20ft radius"},
        "Lightning Bolt": {"damage": "8d6", "type": "lightning", "aoe": "100ft line"},
        "Counterspell": {"effect": "Cancel enemy spell", "reaction": True},
        "Revivify": {"effect": "Restore life", "cost": "300gp diamond"}
    }
}

# Difficulty classes for checks
DIFFICULTY_CLASSES = {
    "Very Easy": 5,
    "Easy": 10,
    "Medium": 15,
    "Hard": 20,
    "Very Hard": 25,
    "Nearly Impossible": 30
}

# Experience thresholds for leveling
XP_THRESHOLDS = {
    1: 0,
    2: 300,
    3: 900,
    4: 2700,
    5: 6500,
    6: 14000,
    7: 23000,
    8: 34000,
    9: 48000,
    10: 64000
}

# Random encounter tables
ENCOUNTER_THEMES = {
    "forest": ["2d4 Goblins", "1d3 Wolves", "1 Orc", "1d6 Bandits"],
    "dungeon": ["2d4 Skeletons", "1d4 Goblins", "1 Orc", "1 Ogre"],
    "mountains": ["1d4 Orcs", "1 Ogre", "1d6 Goblins", "1 Troll"],
    "urban": ["1d6 Bandits", "1d4 Thugs", "1 Cultist", "1d3 Guards"]
}

# AI Background prompt templates
AI_BACKGROUND_PROMPTS = {
    "tavern": "A cozy medieval fantasy tavern with wooden beams, a crackling fireplace, and adventurers gathered around tables",
    "dungeon": "A dark, ominous dungeon corridor with torches on stone walls, ancient runes, and mysterious shadows",
    "forest": "An enchanted forest clearing with rays of sunlight filtering through ancient trees and mystical fog",
    "castle": "A grand medieval castle throne room with high vaulted ceilings, banners, and royal decorations",
    "cave": "A mysterious underground cave with glowing crystals, stalagmites, and an underground stream",
    "battlefield": "An epic fantasy battlefield with warriors, magical energy, and dramatic storm clouds overhead",
    "temple": "An ancient temple interior with mystical symbols, columns, and divine light streaming through windows",
    "village": "A peaceful medieval fantasy village with thatched roof cottages and a cobblestone square"
}

# Status conditions
CONDITIONS = {
    "Blinded": "Can't see, fail ability checks requiring sight, attack rolls disadvantage",
    "Charmed": "Can't attack charmer, charmer has advantage on social checks",
    "Deafened": "Can't hear, fail ability checks requiring hearing",
    "Frightened": "Disadvantage on checks and attacks while source is in sight",
    "Grappled": "Speed becomes 0, can't benefit from bonuses to speed",
    "Incapacitated": "Can't take actions or reactions",
    "Invisible": "Impossible to see, attack rolls have advantage, attacks against have disadvantage",
    "Paralyzed": "Incapacitated, can't move or speak, auto-fail Str and Dex saves",
    "Petrified": "Transformed to stone, incapacitated, resistance to all damage",
    "Poisoned": "Disadvantage on attack rolls and ability checks",
    "Prone": "Disadvantage on attack rolls, attacks against have advantage if within 5ft",
    "Restrained": "Speed becomes 0, disadvantage on attacks and Dex saves",
    "Stunned": "Incapacitated, can't move, speak only falteringly",
    "Unconscious": "Incapacitated, can't move or speak, unaware of surroundings"
}
