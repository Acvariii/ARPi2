from __future__ import annotations

import hashlib
import json
import random
import re
from typing import Dict, List


def _stable_rng_seed(*parts: str) -> int:
    raw = "|".join([str(p or "") for p in parts])
    h = hashlib.sha256(raw.encode("utf-8", errors="ignore")).hexdigest()
    return int(h[:12], 16)


def _dnd_background_questions() -> List[Dict]:
    """Return a stable list of 20-30 character background questions."""
    # Keep these short for UI; the generator will turn them into richer prose.
    return [
        {
            "id": "origin",
            "kind": "choice",
            "prompt": "Where did you grow up?",
            "options": ["City alleys", "Quiet village", "Frontier outpost", "Monastery", "Noble estate", "Wilderness camp"],
        },
        {
            "id": "family",
            "kind": "choice",
            "prompt": "What was your family like?",
            "options": ["Loving but poor", "Strict and demanding", "Large and chaotic", "Absent/unknown", "Respectable and stable", "Feared by others"],
        },
        {
            "id": "mentor",
            "kind": "choice",
            "prompt": "Who taught you your most important lesson?",
            "options": ["A veteran", "A scholar", "A priest", "A thief", "A rival", "No one"],
        },
        {
            "id": "turning_point",
            "kind": "choice",
            "prompt": "What pushed you into adventure?",
            "options": ["A debt", "A prophecy", "Revenge", "Curiosity", "A lost loved one", "A call to duty"],
        },
        {"id": "virtue", "kind": "choice", "prompt": "What do you value most?", "options": ["Honor", "Freedom", "Knowledge", "Compassion", "Power", "Loyalty"]},
        {"id": "flaw", "kind": "choice", "prompt": "What trips you up most often?", "options": ["Pride", "Impulsiveness", "Suspicion", "Mercy", "Greed", "Stubbornness"]},
        {
            "id": "fear",
            "kind": "choice",
            "prompt": "What scares you more than you admit?",
            "options": ["Being powerless", "Being forgotten", "Hurting others", "Losing control", "The dark", "Betrayal"],
        },
        {
            "id": "bond",
            "kind": "choice",
            "prompt": "What keeps you going when things get ugly?",
            "options": ["A promise", "A person", "A cause", "A debt repaid", "A secret", "A dream"],
        },
        {
            "id": "style",
            "kind": "choice",
            "prompt": "How do you approach problems?",
            "options": ["Plan carefully", "Charge in", "Talk first", "Use tricks", "Follow instinct", "Let others lead"],
        },
        {
            "id": "reputation",
            "kind": "choice",
            "prompt": "What is your reputation (or rumor) back home?",
            "options": ["Reliable", "Troublemaker", "Odd but brilliant", "Blessed", "Dangerous", "Unknown"],
        },
        {
            "id": "secret",
            "kind": "choice",
            "prompt": "What kind of secret do you carry?",
            "options": ["A crime", "A lineage", "A bargain", "A forbidden truth", "A hidden talent", "No secret"],
        },
        {
            "id": "magic",
            "kind": "choice",
            "prompt": "How do you feel about magic?",
            "options": ["I study it", "I distrust it", "I respect it", "I fear it", "I use it", "I envy it"],
        },
        {
            "id": "faith",
            "kind": "choice",
            "prompt": "What is your relationship with faith/tradition?",
            "options": ["Devout", "Skeptical", "Curious", "Rebellious", "Pragmatic", "Haunted"],
        },
        {
            "id": "social",
            "kind": "choice",
            "prompt": "In a crowd, you are usually…",
            "options": ["A leader", "A listener", "A performer", "A watcher", "A negotiator", "An outsider"],
        },
        {
            "id": "travel",
            "kind": "choice",
            "prompt": "Why do you travel?",
            "options": ["To prove myself", "To learn", "To protect", "To escape", "To hunt", "To serve"],
        },
        {
            "id": "weapon",
            "kind": "choice",
            "prompt": "What feels most natural in your hands?",
            "options": ["Blade", "Bow", "Hammer", "Staff", "Daggers", "My words"],
        },
        {
            "id": "keepsake",
            "kind": "choice",
            "prompt": "You carry a keepsake that is…",
            "options": ["A letter", "A token", "A map", "A charm", "A broken weapon", "A small book"],
        },
        {"id": "scar", "kind": "choice", "prompt": "You gained a scar from…", "options": ["A duel", "A monster", "A fire", "A betrayal", "Hard labor", "A ritual"]},
        {
            "id": "goal",
            "kind": "choice",
            "prompt": "Your next big goal is…",
            "options": ["Find someone", "Find something", "Earn status", "Pay a debt", "Break a curse", "Build a home"],
        },
        {
            "id": "companions",
            "kind": "choice",
            "prompt": "What do you expect from companions?",
            "options": ["Honesty", "Competence", "Kindness", "Loyalty", "Respect", "Nothing"],
        },
        {
            "id": "conflict",
            "kind": "choice",
            "prompt": "When conflict rises, you…",
            "options": ["De-escalate", "Intimidate", "Outwit", "End it fast", "Protect the weak", "Disappear"],
        },
        {
            "id": "craft",
            "kind": "choice",
            "prompt": "A non-combat talent you’re proud of:",
            "options": ["Cooking", "Woodcraft", "Tales & songs", "Herbalism", "Cartography", "Languages"],
        },
        {"id": "hook", "kind": "text", "prompt": "One unique detail about you (a quirk, vow, motto, etc.):"},
    ]


def _dnd_pick_additional_skills(char_class: str, answers: Dict[str, str], rng: random.Random) -> List[str]:
    # Use the canonical skill list from D&D logic.
    try:
        from games.dnd.logic import SkillChecker

        all_skills = list(getattr(SkillChecker, "SKILLS", {}).keys())
    except Exception:
        all_skills = [
            "Acrobatics",
            "Animal Handling",
            "Arcana",
            "Athletics",
            "Deception",
            "History",
            "Insight",
            "Intimidation",
            "Investigation",
            "Medicine",
            "Nature",
            "Perception",
            "Performance",
            "Persuasion",
            "Religion",
            "Sleight of Hand",
            "Stealth",
            "Survival",
        ]

    try:
        from games.dnd.models import CLASS_SKILLS as _CLASS_SKILLS

        base = list((_CLASS_SKILLS or {}).get(str(char_class), []) or [])
    except Exception:
        base = []
    pool = [s for s in all_skills if s not in set(base)]

    # Bias by answers.
    bias: List[str] = []
    a = {k: str(v or "") for k, v in (answers or {}).items()}
    origin = a.get("origin", "")
    if "City" in origin:
        bias += ["Stealth", "Sleight of Hand", "Deception", "Investigation"]
    if "Wilderness" in origin or "Frontier" in origin:
        bias += ["Survival", "Nature", "Perception", "Animal Handling"]
    if "Monastery" in origin:
        bias += ["Insight", "Medicine", "Religion"]
    if "Noble" in origin:
        bias += ["Persuasion", "History", "Performance"]

    style = a.get("style", "")
    if "Plan" in style:
        bias += ["Investigation", "History"]
    if "Talk" in style or "negotiator" in a.get("social", ""):
        bias += ["Persuasion", "Insight", "Deception"]
    if "tricks" in style or "watcher" in a.get("social", ""):
        bias += ["Stealth", "Sleight of Hand", "Perception"]

    faith = a.get("faith", "")
    if faith in ("Devout", "Haunted"):
        bias += ["Religion", "Insight", "Medicine"]
    if a.get("magic", "") in ("I study it", "I use it", "I envy it"):
        bias += ["Arcana", "Investigation", "History"]

    # Pick 2 distinct.
    picks: List[str] = []
    for _ in range(8):
        if len(picks) >= 2:
            break
        candidate_pool = [s for s in bias if s in pool and s not in picks]
        if candidate_pool:
            picks.append(rng.choice(candidate_pool))
        elif pool:
            picks.append(rng.choice([s for s in pool if s not in picks]))
    return picks[:2]


def _dnd_starting_loadout(char_class: str) -> tuple[List[Dict], Dict[str, str]]:
    """Return (items, equipment_map) where items are Character.add_item()-ready dicts."""
    cc = str(char_class or "").strip()

    def gear(name: str, slot: str, ac_bonus: int = 0) -> Dict:
        it: Dict = {"name": name, "kind": "gear", "slot": slot, "ac_bonus": int(ac_bonus)}
        return it

    def misc(name: str) -> Dict:
        return {"name": name, "kind": "misc"}

    def heal_potion(amount: int = 6) -> Dict:
        return {"name": "Healing Potion", "kind": "consumable", "effect": {"type": "heal", "amount": int(amount)}}

    items: List[Dict] = []
    equip: Dict[str, str] = {}

    if cc == "Fighter":
        items += [gear("Chain Mail", "chest", ac_bonus=6), misc("Longsword"), misc("Adventurer's Pack"), heal_potion(6)]
        equip["chest"] = "__auto:Chain Mail"
        equip["sword"] = "__auto:Longsword"
    elif cc == "Rogue":
        items += [gear("Leather Armor", "chest", ac_bonus=1), misc("Dagger"), misc("Thieves' Tools"), misc("Shortbow"), heal_potion(6)]
        equip["chest"] = "__auto:Leather Armor"
        equip["knife"] = "__auto:Dagger"
        equip["bow"] = "__auto:Shortbow"
    elif cc == "Wizard":
        items += [gear("Padded Robes", "chest", ac_bonus=0), misc("Staff"), misc("Spellbook"), misc("Component Pouch"), heal_potion(6)]
        equip["chest"] = "__auto:Padded Robes"
        equip["staff"] = "__auto:Staff"
    elif cc == "Cleric":
        items += [gear("Chain Mail", "chest", ac_bonus=6), misc("Warhammer"), misc("Holy Symbol"), misc("Healer's Kit"), heal_potion(8)]
        equip["chest"] = "__auto:Chain Mail"
        equip["sword"] = "__auto:Warhammer"
    elif cc == "Ranger":
        items += [gear("Leather Armor", "chest", ac_bonus=1), misc("Longbow"), misc("Dagger"), misc("Trail Rations"), heal_potion(6)]
        equip["chest"] = "__auto:Leather Armor"
        equip["bow"] = "__auto:Longbow"
        equip["knife"] = "__auto:Dagger"
    elif cc == "Paladin":
        items += [gear("Chain Mail", "chest", ac_bonus=6), misc("Longsword"), misc("Oath Token"), misc("Traveler's Pack"), heal_potion(8)]
        equip["chest"] = "__auto:Chain Mail"
        equip["sword"] = "__auto:Longsword"
    else:
        items += [gear("Leather Armor", "chest", ac_bonus=1), misc("Dagger"), misc("Adventurer's Pack"), heal_potion(6)]
        equip["chest"] = "__auto:Leather Armor"
        equip["knife"] = "__auto:Dagger"

    return items, equip


def _dnd_generate_background_text(
    name: str,
    race: str,
    char_class: str,
    answers: Dict[str, str],
    seed_hint: str,
) -> tuple[str, List[str], List[str]]:
    """Return (background_text, feats, features)."""
    a = {k: str(v or "").strip() for k, v in (answers or {}).items()}
    seed = _stable_rng_seed(name, race, char_class, seed_hint, json.dumps(a, sort_keys=True))
    rng = random.Random(seed)

    origin = a.get("origin") or rng.choice(["a quiet village", "city alleys", "a frontier outpost", "the wilderness"])
    turning = a.get("turning_point") or rng.choice(["a debt", "a prophecy", "revenge", "curiosity"])
    virtue = a.get("virtue") or rng.choice(["honor", "freedom", "knowledge", "compassion"])
    flaw = a.get("flaw") or rng.choice(["pride", "impulsiveness", "suspicion", "stubbornness"])
    bond = a.get("bond") or rng.choice(["a promise", "a person", "a cause", "a dream"])
    keepsake = a.get("keepsake") or rng.choice(["a letter", "a token", "a map", "a charm"])
    hook = a.get("hook")
    if hook:
        hook = re.sub(r"\s+", " ", hook).strip()
        hook = hook[:140]

    opener_pool = [
        "You learned early that the world rarely offers clean choices.",
        "You grew up with one foot in trouble and the other in duty.",
        "You were shaped by long nights, short tempers, and longer roads.",
        "You found comfort in routines—until adventure broke them.",
        "You learned to read people before you learned to read books.",
    ]
    twist_pool = [
        "A single night changed everything.",
        "A quiet moment became a vow.",
        "A mistake became a lesson you refuse to forget.",
        "A stranger’s words lodged in your mind like a splinter.",
        "An old debt still casts a long shadow.",
    ]
    closer_pool = [
        "You don’t seek glory—only a reason to believe you can make things right.",
        "You keep moving because standing still feels like losing.",
        "You measure your life in promises kept, not battles won.",
        "You’ve decided your story won’t be written by fear.",
    ]

    opener = rng.choice(opener_pool)
    twist = rng.choice(twist_pool)
    closer = rng.choice(closer_pool)

    bg = (
        f"{opener}\n\n"
        f"You grew up in {origin.lower()}, and you learned to lean on {virtue.lower()}—even when it made you stubborn. "
        f"When {turning.lower()} pulled you onto the road, you didn’t hesitate for long. {twist}"
        f"\n\nYour greatest flaw is {flaw.lower()}, and you’re not proud of the damage it’s caused. "
        f"Still, {bond.lower()} keeps you standing when the odds turn. You carry {keepsake.lower()} as a reminder of who you were before you became a {char_class.lower()}."
    )
    if hook:
        bg += f"\n\nUnique detail: {hook}"
    bg += f"\n\n{closer}"

    # Feats/features: original names to avoid copying SRD text.
    class_features = {
        "Fighter": ["Combat Training", "Steel Nerve"],
        "Wizard": ["Arcane Study", "Ritual Habit"],
        "Rogue": ["Quick Hands", "Shadow Sense"],
        "Cleric": ["Sacred Channel", "Vow of Mercy"],
        "Ranger": ["Trailcraft", "Keen Aim"],
        "Paladin": ["Oathbound", "Radiant Presence"],
    }
    trait_pool = [
        "Silver Tongue",
        "Battle Instinct",
        "Keen Observer",
        "Iron Stomach",
        "Steady Hands",
        "Unshakable Focus",
        "Lucky Breaks",
        "Streetwise",
        "Wilderness Blood",
        "Bookish",
    ]

    # Bias feats by some answers
    bias: List[str] = []
    if "City" in str(a.get("origin", "")):
        bias += ["Streetwise", "Steady Hands", "Silver Tongue"]
    if "Wilderness" in str(a.get("origin", "")) or "Frontier" in str(a.get("origin", "")):
        bias += ["Wilderness Blood", "Keen Observer", "Battle Instinct"]
    if str(a.get("magic", "")) in ("I study it", "I use it"):
        bias += ["Bookish", "Unshakable Focus"]

    feats: List[str] = []
    feat_pool = bias + trait_pool
    while feat_pool and len(feats) < 1:
        f = rng.choice(feat_pool)
        if f not in feats:
            feats.append(f)
        feat_pool = [x for x in feat_pool if x != f]

    features = list(class_features.get(str(char_class), ["Adventurer"]))[:]
    # Add one extra feature influenced by answers
    extra = rng.choice(
        [
            "Resourceful",
            "Calm Under Pressure",
            "Hard to Read",
            "People Person",
            "Tinkerer's Touch",
            "Uncanny Luck",
        ]
    )
    if extra not in features:
        features.append(extra)

    return bg, feats, features
