using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using ARPi2.Sharp.Core;

namespace ARPi2.Sharp.Games.DnD;

// ════════════════════════════════════════════════════════════════
//  Data — Races, Classes, Names, Monsters, Items, Spells
// ════════════════════════════════════════════════════════════════

#region Data Constants

public static class DnDData
{
    public static readonly string[] Races = { "Human", "Elf", "Dwarf", "Halfling", "Orc", "Tiefling" };
    public static readonly string[] Classes = { "Fighter", "Wizard", "Rogue", "Cleric", "Ranger", "Paladin" };
    public static readonly string[] Alignments =
    {
        "Lawful Good", "Neutral Good", "Chaotic Good",
        "Lawful Neutral", "True Neutral", "Chaotic Neutral",
        "Lawful Evil", "Neutral Evil", "Chaotic Evil"
    };
    public static readonly string[] AbilityScores = { "Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma" };

    public static readonly Dictionary<string, int> ClassHp = new()
    {
        ["Fighter"] = 10, ["Wizard"] = 6, ["Rogue"] = 8,
        ["Cleric"] = 8, ["Ranger"] = 10, ["Paladin"] = 10,
    };

    public static readonly Dictionary<string, string[]> ClassSkills = new()
    {
        ["Fighter"] = new[] { "Athletics", "Intimidation", "Survival" },
        ["Wizard"] = new[] { "Arcana", "History", "Investigation" },
        ["Rogue"] = new[] { "Stealth", "Sleight of Hand", "Acrobatics" },
        ["Cleric"] = new[] { "Medicine", "Insight", "Religion" },
        ["Ranger"] = new[] { "Nature", "Survival", "Animal Handling" },
        ["Paladin"] = new[] { "Religion", "Persuasion", "Athletics" },
    };

    // ── Name tables ────────────────────────────────────────────

    public static readonly Dictionary<string, (string[] First, string[] Last)> RaceNames = new()
    {
        ["Human"] = (
            new[] { "Aldric", "Brenna", "Cedric", "Diana", "Erik", "Fiona", "Gareth", "Helena", "Ivan", "Jade" },
            new[] { "Ironheart", "Stormwind", "Blackwood", "Silverstone", "Goldleaf", "Brightblade", "Darkwater", "Swiftarrow" }),
        ["Elf"] = (
            new[] { "Aelrindel", "Sylvari", "Thranduil", "Elaria", "Caladrel", "Liriel", "Galadon", "Aria", "Eldrin", "Mirial" },
            new[] { "Moonwhisper", "Starweaver", "Leafdancer", "Sunfire", "Nightbreeze", "Dawnstrider", "Shadowleaf", "Skysong" }),
        ["Dwarf"] = (
            new[] { "Thorin", "Gimli", "Balin", "Dwalin", "Bombur", "Bofur", "Grilda", "Helga", "Kathra", "Vistra" },
            new[] { "Ironforge", "Stonefist", "Hammerstrike", "Axebreaker", "Goldbeard", "Rockhelm", "Steelshield", "Fireborn" }),
        ["Halfling"] = (
            new[] { "Pippin", "Merry", "Bilbo", "Rosie", "Daisy", "Willow", "Bramble", "Clover", "Finnegan", "Poppy" },
            new[] { "Goodbarrel", "Lightfoot", "Underbough", "Tealeaf", "Thornburrow", "Greenbottle", "Hilltopple", "Meadowbrook" }),
        ["Orc"] = (
            new[] { "Grommash", "Thrall", "Durotan", "Garrosh", "Grok", "Urzul", "Shakara", "Zugra", "Gorza", "Krazh" },
            new[] { "Bloodfang", "Skullcrusher", "Warmaker", "Bonegrinder", "Ironclaw", "Thunderfist", "Blacktooth", "Ashbringer" }),
        ["Tiefling"] = (
            new[] { "Zariel", "Mephistopheles", "Ashlyn", "Brimstone", "Crimson", "Ember", "Inferno", "Raven", "Sable", "Vesper" },
            new[] { "Hellfire", "Soulforge", "Darkflame", "Shadowhorn", "Crimsonwing", "Nightfall", "Doomcaller", "Voidwalker" }),
    };

    public static readonly Dictionary<string, string[]> ClassTitles = new()
    {
        ["Fighter"] = new[] { "the Bold", "the Brave", "the Mighty", "the Valiant", "the Fearless", "the Champion" },
        ["Wizard"] = new[] { "the Wise", "the Arcane", "the Mystic", "the Enlightened", "the Scholarly", "the Spellweaver" },
        ["Rogue"] = new[] { "the Swift", "the Shadow", "the Cunning", "the Silent", "the Sly", "the Phantom" },
        ["Cleric"] = new[] { "the Blessed", "the Faithful", "the Divine", "the Holy", "the Righteous", "the Devoted" },
        ["Ranger"] = new[] { "the Tracker", "the Hunter", "the Wild", "the Wanderer", "the Scout", "the Pathfinder" },
        ["Paladin"] = new[] { "the Just", "the Defender", "the Noble", "the Crusader", "the Guardian", "the Lightbringer" },
    };

    // ── Monsters ───────────────────────────────────────────────

    public static readonly Dictionary<string, MonsterTemplate> Monsters = new()
    {
        ["Goblin"] = new("Goblin", 0.25, 7, 15,
            new() { ["Strength"] = 8, ["Dexterity"] = 14, ["Constitution"] = 10, ["Intelligence"] = 10, ["Wisdom"] = 8, ["Charisma"] = 8 },
            new[] { new AttackTemplate("Scimitar", 4, "1d6+2", "slashing"), new AttackTemplate("Shortbow", 4, "1d6+2", "piercing", true) }, 50),
        ["Orc"] = new("Orc", 0.5, 15, 13,
            new() { ["Strength"] = 16, ["Dexterity"] = 12, ["Constitution"] = 16, ["Intelligence"] = 7, ["Wisdom"] = 11, ["Charisma"] = 10 },
            new[] { new AttackTemplate("Greataxe", 5, "1d12+3", "slashing"), new AttackTemplate("Javelin", 5, "1d6+3", "piercing", true) }, 100),
        ["Skeleton"] = new("Skeleton", 0.25, 13, 13,
            new() { ["Strength"] = 10, ["Dexterity"] = 14, ["Constitution"] = 15, ["Intelligence"] = 6, ["Wisdom"] = 8, ["Charisma"] = 5 },
            new[] { new AttackTemplate("Shortsword", 4, "1d6+2", "piercing"), new AttackTemplate("Shortbow", 4, "1d6+2", "piercing", true) }, 50),
        ["Wolf"] = new("Wolf", 0.25, 11, 13,
            new() { ["Strength"] = 12, ["Dexterity"] = 15, ["Constitution"] = 12, ["Intelligence"] = 3, ["Wisdom"] = 12, ["Charisma"] = 6 },
            new[] { new AttackTemplate("Bite", 4, "2d4+2", "piercing") }, 50),
        ["Ogre"] = new("Ogre", 2, 59, 11,
            new() { ["Strength"] = 19, ["Dexterity"] = 8, ["Constitution"] = 16, ["Intelligence"] = 5, ["Wisdom"] = 7, ["Charisma"] = 7 },
            new[] { new AttackTemplate("Greatclub", 6, "2d8+4", "bludgeoning"), new AttackTemplate("Javelin", 6, "2d6+4", "piercing", true) }, 450),
        ["Troll"] = new("Troll", 5, 84, 15,
            new() { ["Strength"] = 18, ["Dexterity"] = 13, ["Constitution"] = 20, ["Intelligence"] = 7, ["Wisdom"] = 9, ["Charisma"] = 7 },
            new[] { new AttackTemplate("Claw", 7, "2d6+4", "slashing"), new AttackTemplate("Bite", 7, "2d6+4", "piercing") }, 1800, "Regeneration: 10 HP per turn"),
        ["Dragon Wyrmling"] = new("Dragon Wyrmling", 4, 75, 17,
            new() { ["Strength"] = 19, ["Dexterity"] = 10, ["Constitution"] = 17, ["Intelligence"] = 12, ["Wisdom"] = 11, ["Charisma"] = 15 },
            new[] { new AttackTemplate("Bite", 6, "1d10+4", "piercing"), new AttackTemplate("Breath Weapon", 0, "7d6", "fire", Aoe: true) }, 1100),
    };

    // ── XP thresholds ──────────────────────────────────────────
    public static readonly Dictionary<int, int> XpThresholds = new()
    {
        [1] = 0, [2] = 300, [3] = 900, [4] = 2700, [5] = 6500,
        [6] = 14000, [7] = 23000, [8] = 34000, [9] = 48000, [10] = 64000,
    };

    // ── Skill → ability mapping ────────────────────────────────
    public static readonly Dictionary<string, string> SkillAbilities = new()
    {
        ["Acrobatics"] = "Dexterity",
        ["Animal Handling"] = "Wisdom",
        ["Arcana"] = "Intelligence",
        ["Athletics"] = "Strength",
        ["Deception"] = "Charisma",
        ["History"] = "Intelligence",
        ["Insight"] = "Wisdom",
        ["Intimidation"] = "Charisma",
        ["Investigation"] = "Intelligence",
        ["Medicine"] = "Wisdom",
        ["Nature"] = "Intelligence",
        ["Perception"] = "Wisdom",
        ["Performance"] = "Charisma",
        ["Persuasion"] = "Charisma",
        ["Religion"] = "Intelligence",
        ["Sleight of Hand"] = "Dexterity",
        ["Stealth"] = "Dexterity",
        ["Survival"] = "Wisdom",
    };

    // ── Background questions ───────────────────────────────────
    public static List<Dictionary<string, object?>> BackgroundQuestions()
    {
        var qs = new List<(string Id, string Prompt, string[]? Options)>
        {
            ("origin", "Where did you grow up?", new[] { "City alleys", "Quiet village", "Frontier outpost", "Monastery", "Noble estate", "Wilderness camp" }),
            ("family", "What was your family like?", new[] { "Loving but poor", "Strict and demanding", "Large and chaotic", "Absent/unknown", "Respectable and stable", "Feared by others" }),
            ("mentor", "Who taught you your most important lesson?", new[] { "A veteran", "A scholar", "A priest", "A thief", "A rival", "No one" }),
            ("turning_point", "What pushed you into adventure?", new[] { "A debt", "A prophecy", "Revenge", "Curiosity", "A lost loved one", "A call to duty" }),
            ("virtue", "What do you value most?", new[] { "Honor", "Freedom", "Knowledge", "Compassion", "Power", "Loyalty" }),
            ("flaw", "What trips you up most often?", new[] { "Pride", "Impulsiveness", "Suspicion", "Mercy", "Greed", "Stubbornness" }),
            ("fear", "What scares you more than you admit?", new[] { "Being powerless", "Being forgotten", "Hurting others", "Losing control", "The dark", "Betrayal" }),
            ("bond", "What keeps you going when things get ugly?", new[] { "A promise", "A person", "A cause", "A debt repaid", "A secret", "A dream" }),
            ("style", "How do you approach problems?", new[] { "Plan carefully", "Charge in", "Talk first", "Use tricks", "Follow instinct", "Let others lead" }),
            ("reputation", "What is your reputation back home?", new[] { "Reliable", "Troublemaker", "Odd but brilliant", "Blessed", "Dangerous", "Unknown" }),
            ("secret", "What kind of secret do you carry?", new[] { "A crime", "A lineage", "A bargain", "A forbidden truth", "A hidden talent", "No secret" }),
            ("magic", "How do you feel about magic?", new[] { "I study it", "I distrust it", "I respect it", "I fear it", "I use it", "I envy it" }),
            ("faith", "What is your relationship with faith?", new[] { "Devout", "Skeptical", "Curious", "Rebellious", "Pragmatic", "Haunted" }),
            ("social", "In a crowd, you are usually...", new[] { "A leader", "A listener", "A performer", "A watcher", "A negotiator", "An outsider" }),
            ("travel", "Why do you travel?", new[] { "To prove myself", "To learn", "To protect", "To escape", "To hunt", "To serve" }),
            ("weapon", "What feels most natural in your hands?", new[] { "Blade", "Bow", "Hammer", "Staff", "Daggers", "My words" }),
            ("keepsake", "You carry a keepsake that is...", new[] { "A letter", "A token", "A map", "A charm", "A broken weapon", "A small book" }),
            ("scar", "You gained a scar from...", new[] { "A duel", "A monster", "A fire", "A betrayal", "Hard labor", "A ritual" }),
            ("goal", "Your next big goal is...", new[] { "Find someone", "Find something", "Earn status", "Pay a debt", "Break a curse", "Build a home" }),
            ("companions", "What do you expect from companions?", new[] { "Honesty", "Competence", "Kindness", "Loyalty", "Respect", "Nothing" }),
            ("conflict", "When conflict rises, you...", new[] { "De-escalate", "Intimidate", "Outwit", "End it fast", "Protect the weak", "Disappear" }),
            ("craft", "A non-combat talent you're proud of:", new[] { "Cooking", "Woodcraft", "Tales & songs", "Herbalism", "Cartography", "Languages" }),
            ("hook", "One unique detail about you:", null),
        };

        var result = new List<Dictionary<string, object?>>();
        foreach (var (id, prompt, options) in qs)
        {
            var d = new Dictionary<string, object?>
            {
                ["id"] = id,
                ["kind"] = options != null ? "choice" : "text",
                ["prompt"] = prompt,
            };
            if (options != null) d["options"] = options.ToList();
            result.Add(d);
        }
        return result;
    }

    // ── Name generation ────────────────────────────────────────
    public static string GenerateCharacterName(string race, string charClass, Random rng)
    {
        if (!RaceNames.TryGetValue(race, out var names))
            return "Unknown Hero";

        string firstName = names.First[rng.Next(names.First.Length)];

        if (rng.NextDouble() > 0.5 && ClassTitles.TryGetValue(charClass, out var titles))
            return $"{firstName} {titles[rng.Next(titles.Length)]}";

        return $"{firstName} {names.Last[rng.Next(names.Last.Length)]}";
    }
}

public record AttackTemplate(string Name, int Bonus, string Damage, string Type, bool Range = false, bool Aoe = false);

public record MonsterTemplate(
    string Name, double Cr, int Hp, int Ac,
    Dictionary<string, int> Abilities,
    AttackTemplate[] Attacks, int Xp,
    string? Special = null);

#endregion

// ════════════════════════════════════════════════════════════════
//  Models — Character, Enemy, InventoryItem
// ════════════════════════════════════════════════════════════════

#region Models

public class InventoryItem
{
    public string Id { get; set; } = "";
    public string Name { get; set; } = "";
    public string Kind { get; set; } = "misc"; // misc, gear, consumable
    public string? Slot { get; set; }
    public int AcBonus { get; set; }
    public Dictionary<string, int>? AbilityBonuses { get; set; }
    public ItemEffect? Effect { get; set; }

    public Dictionary<string, object?> ToDict() => new()
    {
        ["id"] = Id,
        ["name"] = Name,
        ["kind"] = Kind,
        ["slot"] = Slot,
        ["ac_bonus"] = AcBonus,
        ["ability_bonuses"] = AbilityBonuses != null ? new Dictionary<string, object?>(AbilityBonuses.ToDictionary(k => k.Key, k => (object?)k.Value)) : null,
        ["effect"] = Effect != null ? new Dictionary<string, object?> { ["type"] = Effect.Type, ["amount"] = Effect.Amount } : null,
    };

    public static InventoryItem? FromDict(Dictionary<string, object?>? raw)
    {
        if (raw == null) return null;
        string name = raw.GetValueOrDefault("name")?.ToString()?.Trim() ?? "";
        if (string.IsNullOrEmpty(name)) return null;

        var item = new InventoryItem
        {
            Id = raw.GetValueOrDefault("id")?.ToString()?.Trim() ?? NewItemId(),
            Name = name,
            Kind = raw.GetValueOrDefault("kind")?.ToString()?.Trim() ?? "misc",
        };
        if (string.IsNullOrEmpty(item.Kind)) item.Kind = "misc";

        if (item.Kind == "gear")
        {
            item.Slot = raw.GetValueOrDefault("slot")?.ToString()?.Trim();
            if (raw.TryGetValue("ac_bonus", out var acb)) int.TryParse(acb?.ToString(), out var ab); else ab = 0;
            item.AcBonus = ab;
        }
        else if (item.Kind == "consumable" && raw.TryGetValue("effect", out var eff) && eff is Dictionary<string, object?> effD)
        {
            item.Effect = new ItemEffect
            {
                Type = effD.GetValueOrDefault("type")?.ToString()?.Trim() ?? "heal",
                Amount = int.TryParse(effD.GetValueOrDefault("amount")?.ToString(), out var ea) ? ea : 0,
            };
        }
        return item;
    }

    public static string NewItemId() => $"{DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()}_{Random.Shared.Next(1000, 9999)}";

    // Parse ac_bonus helper
    private static int ab;
}

public class ItemEffect
{
    public string Type { get; set; } = "heal";
    public int Amount { get; set; }
}

public class DnDCharacter
{
    public string Name { get; set; } = "";
    public string Race { get; set; } = "";
    public string CharClass { get; set; } = "";
    public int Level { get; set; } = 1;
    public string Alignment { get; set; } = "";
    public Dictionary<string, int> Abilities { get; set; } = new()
    {
        ["Strength"] = 10, ["Dexterity"] = 10, ["Constitution"] = 10,
        ["Intelligence"] = 10, ["Wisdom"] = 10, ["Charisma"] = 10,
    };
    public int MaxHp { get; set; } = 10;
    public int CurrentHp { get; set; } = 10;
    public int ArmorClass { get; set; } = 10;
    public List<string> Skills { get; set; } = new();
    public List<InventoryItem> Inventory { get; set; } = new();
    public Dictionary<string, string> Equipment { get; set; } = new(); // slot → item id
    public int Gold { get; set; }
    public int Experience { get; set; }
    public string Background { get; set; } = "";
    public Dictionary<string, string> BackgroundAnswers { get; set; } = new();
    public List<string> Feats { get; set; } = new();
    public List<string> Features { get; set; } = new();

    public int GetAbilityModifier(string ability)
    {
        int score = GetEffectiveAbilityScore(ability);
        return (score - 10) / 2;
    }

    public int GetEffectiveAbilityScore(string ability)
    {
        int baseVal = Abilities.GetValueOrDefault(ability, 10);
        int bonus = 0;
        foreach (var kv in Equipment)
        {
            var item = GetItemById(kv.Value);
            if (item?.Kind != "gear" || item.AbilityBonuses == null) continue;
            bonus += item.AbilityBonuses.GetValueOrDefault(ability, 0);
        }
        return baseVal + bonus;
    }

    public void CalculateHp(bool resetCurrent = true)
    {
        int baseHp = DnDData.ClassHp.GetValueOrDefault(CharClass, 8);
        int conMod = GetAbilityModifier("Constitution");
        MaxHp = Math.Max(1, baseHp + conMod);
        if (resetCurrent)
            CurrentHp = MaxHp;
        else
            CurrentHp = Math.Clamp(CurrentHp, 0, MaxHp);
    }

    public void CalculateAc()
    {
        int dexMod = GetAbilityModifier("Dexterity");
        int bonusAc = 0;
        foreach (var kv in Equipment)
        {
            var item = GetItemById(kv.Value);
            if (item?.Kind == "gear") bonusAc += item.AcBonus;
        }
        ArmorClass = 10 + dexMod + bonusAc;
    }

    public void UpdateDerivedStats(bool resetCurrentHp = false)
    {
        CalculateAc();
        CalculateHp(resetCurrent: resetCurrentHp);
    }

    public InventoryItem? GetItemById(string? itemId)
    {
        if (string.IsNullOrEmpty(itemId)) return null;
        return Inventory.FirstOrDefault(it => it.Id == itemId);
    }

    public InventoryItem? AddItem(string name, string kind = "misc", string? slot = null, int acBonus = 0, ItemEffect? effect = null)
    {
        var item = new InventoryItem
        {
            Id = InventoryItem.NewItemId(),
            Name = name,
            Kind = kind,
            Slot = slot,
            AcBonus = acBonus,
            Effect = effect,
        };
        Inventory.Add(item);
        return item;
    }

    public bool EquipItem(string itemId)
    {
        var item = GetItemById(itemId);
        if (item?.Kind != "gear" || string.IsNullOrEmpty(item.Slot)) return false;
        Equipment[item.Slot] = item.Id;
        UpdateDerivedStats(resetCurrentHp: false);
        return true;
    }

    public bool UnequipSlot(string slot)
    {
        if (string.IsNullOrEmpty(slot) || !Equipment.ContainsKey(slot)) return false;
        Equipment.Remove(slot);
        UpdateDerivedStats(resetCurrentHp: false);
        return true;
    }

    public bool UseItem(string itemId)
    {
        var item = GetItemById(itemId);
        if (item?.Kind != "consumable" || item.Effect == null) return false;
        if (item.Effect.Type != "heal" || item.Effect.Amount <= 0) return false;
        CurrentHp = Math.Min(MaxHp, CurrentHp + item.Effect.Amount);
        Inventory.RemoveAll(it => it.Id == itemId);
        // Clean equipment refs
        foreach (var slot in Equipment.Where(kv => kv.Value == itemId).Select(kv => kv.Key).ToList())
            Equipment.Remove(slot);
        return true;
    }

    // ── Serialization ──────────────────────────────────────────

    public Dictionary<string, object?> ToDict() => new()
    {
        ["name"] = Name,
        ["race"] = Race,
        ["char_class"] = CharClass,
        ["level"] = Level,
        ["alignment"] = Alignment,
        ["abilities"] = new Dictionary<string, object?>(Abilities.ToDictionary(k => k.Key, k => (object?)k.Value)),
        ["max_hp"] = MaxHp,
        ["current_hp"] = CurrentHp,
        ["armor_class"] = ArmorClass,
        ["skills"] = Skills.ToList(),
        ["inventory"] = Inventory.Select(it => (object?)it.ToDict()).ToList(),
        ["equipment"] = new Dictionary<string, object?>(Equipment.ToDictionary(k => k.Key, k => (object?)k.Value)),
        ["gold"] = Gold,
        ["experience"] = Experience,
        ["background"] = Background,
        ["background_answers"] = new Dictionary<string, object?>(BackgroundAnswers.ToDictionary(k => k.Key, k => (object?)k.Value)),
        ["feats"] = Feats.ToList(),
        ["features"] = Features.ToList(),
    };

    public static DnDCharacter FromJson(JsonElement el)
    {
        var ch = new DnDCharacter
        {
            Name = el.TryGetProperty("name", out var n) ? n.GetString() ?? "" : "",
            Race = el.TryGetProperty("race", out var r) ? r.GetString() ?? "" : "",
            CharClass = el.TryGetProperty("char_class", out var cc) ? cc.GetString() ?? "" : "",
            Level = el.TryGetProperty("level", out var lv) ? lv.GetInt32() : 1,
            Alignment = el.TryGetProperty("alignment", out var al) ? al.GetString() ?? "" : "",
            MaxHp = el.TryGetProperty("max_hp", out var mh) ? mh.GetInt32() : 10,
            CurrentHp = el.TryGetProperty("current_hp", out var ch2) ? ch2.GetInt32() : 10,
            ArmorClass = el.TryGetProperty("armor_class", out var ac) ? ac.GetInt32() : 10,
            Gold = el.TryGetProperty("gold", out var g) ? g.GetInt32() : 0,
            Experience = el.TryGetProperty("experience", out var xp) ? xp.GetInt32() : 0,
            Background = el.TryGetProperty("background", out var bg) ? bg.GetString() ?? "" : "",
        };

        if (el.TryGetProperty("abilities", out var abs) && abs.ValueKind == JsonValueKind.Object)
            foreach (var prop in abs.EnumerateObject())
                if (prop.Value.TryGetInt32(out int v)) ch.Abilities[prop.Name] = v;

        if (el.TryGetProperty("skills", out var sk) && sk.ValueKind == JsonValueKind.Array)
            ch.Skills = sk.EnumerateArray().Select(s => s.GetString() ?? "").Where(s => s.Length > 0).ToList();

        if (el.TryGetProperty("feats", out var feats) && feats.ValueKind == JsonValueKind.Array)
            ch.Feats = feats.EnumerateArray().Select(s => s.GetString() ?? "").Where(s => s.Length > 0).ToList();

        if (el.TryGetProperty("features", out var features) && features.ValueKind == JsonValueKind.Array)
            ch.Features = features.EnumerateArray().Select(s => s.GetString() ?? "").Where(s => s.Length > 0).ToList();

        if (el.TryGetProperty("background_answers", out var ba) && ba.ValueKind == JsonValueKind.Object)
            foreach (var prop in ba.EnumerateObject())
                ch.BackgroundAnswers[prop.Name] = prop.Value.GetString() ?? "";

        if (el.TryGetProperty("inventory", out var inv) && inv.ValueKind == JsonValueKind.Array)
        {
            foreach (var it in inv.EnumerateArray())
            {
                if (it.ValueKind == JsonValueKind.String)
                {
                    string iname = it.GetString()?.Trim() ?? "";
                    if (iname.Length > 0)
                        ch.Inventory.Add(new InventoryItem { Id = InventoryItem.NewItemId(), Name = iname, Kind = "misc" });
                }
                else if (it.ValueKind == JsonValueKind.Object)
                {
                    var parsed = ParseInventoryItemJson(it);
                    if (parsed != null) ch.Inventory.Add(parsed);
                }
            }
        }

        if (el.TryGetProperty("equipment", out var eq) && eq.ValueKind == JsonValueKind.Object)
            foreach (var prop in eq.EnumerateObject())
                ch.Equipment[prop.Name] = prop.Value.GetString() ?? "";

        try { ch.UpdateDerivedStats(resetCurrentHp: false); } catch { /* ignore */ }
        return ch;
    }

    private static InventoryItem? ParseInventoryItemJson(JsonElement el)
    {
        string name = el.TryGetProperty("name", out var n) ? n.GetString()?.Trim() ?? "" : "";
        if (name.Length == 0) return null;
        var item = new InventoryItem
        {
            Id = el.TryGetProperty("id", out var id) ? id.GetString()?.Trim() ?? InventoryItem.NewItemId() : InventoryItem.NewItemId(),
            Name = name,
            Kind = el.TryGetProperty("kind", out var k) ? k.GetString()?.Trim() ?? "misc" : "misc",
        };
        if (string.IsNullOrEmpty(item.Kind)) item.Kind = "misc";

        if (item.Kind == "gear")
        {
            item.Slot = el.TryGetProperty("slot", out var s) ? s.GetString()?.Trim() : null;
            item.AcBonus = el.TryGetProperty("ac_bonus", out var acb) && acb.TryGetInt32(out int abv) ? abv : 0;
            if (el.TryGetProperty("ability_bonuses", out var abons) && abons.ValueKind == JsonValueKind.Object)
            {
                item.AbilityBonuses = new();
                foreach (var p in abons.EnumerateObject())
                    if (p.Value.TryGetInt32(out int bv)) item.AbilityBonuses[p.Name] = bv;
            }
        }
        else if (item.Kind == "consumable" && el.TryGetProperty("effect", out var eff) && eff.ValueKind == JsonValueKind.Object)
        {
            item.Effect = new ItemEffect
            {
                Type = eff.TryGetProperty("type", out var et) ? et.GetString()?.Trim() ?? "heal" : "heal",
                Amount = eff.TryGetProperty("amount", out var ea) && ea.TryGetInt32(out int eav) ? eav : 0,
            };
        }
        return item;
    }

    // ── Save / Load ────────────────────────────────────────────

    public void SaveToFile(int playerIdx)
    {
        Directory.CreateDirectory("dnd_saves");
        string path = $"dnd_saves/character_{playerIdx}.json";
        string json = JsonSerializer.Serialize(ToDict(), new JsonSerializerOptions { WriteIndented = true });
        File.WriteAllText(path, json);
    }

    public static DnDCharacter? LoadFromFile(int playerIdx)
    {
        string path = $"dnd_saves/character_{playerIdx}.json";
        if (!File.Exists(path)) return null;
        try
        {
            string text = File.ReadAllText(path);
            using var doc = JsonDocument.Parse(text);
            return FromJson(doc.RootElement);
        }
        catch { return null; }
    }

    public static bool CharacterExists(int playerIdx) => File.Exists($"dnd_saves/character_{playerIdx}.json");
}

public class DnDEnemy
{
    public string Name { get; set; } = "";
    public int MaxHp { get; set; }
    public int CurrentHp { get; set; }
    public int ArmorClass { get; set; }
    public Dictionary<string, int> Abilities { get; set; } = new();
    public AttackTemplate[] Attacks { get; set; } = Array.Empty<AttackTemplate>();
    public double Cr { get; set; }
    public int Xp { get; set; }
    public string? Special { get; set; }

    public DnDEnemy() { }

    public DnDEnemy(MonsterTemplate t)
    {
        Name = t.Name;
        MaxHp = t.Hp;
        CurrentHp = t.Hp;
        ArmorClass = t.Ac;
        Abilities = new Dictionary<string, int>(t.Abilities);
        Attacks = t.Attacks;
        Cr = t.Cr;
        Xp = t.Xp;
        Special = t.Special;
    }

    public bool IsAlive => CurrentHp > 0;
    public void TakeDamage(int amount) => CurrentHp = Math.Max(0, CurrentHp - amount);
    public void Heal(int amount) => CurrentHp = Math.Min(MaxHp, CurrentHp + amount);
    public int GetAbilityModifier(string ability) => (Abilities.GetValueOrDefault(ability, 10) - 10) / 2;
}

#endregion

// ════════════════════════════════════════════════════════════════
//  Logic — DiceRoller, CombatManager
// ════════════════════════════════════════════════════════════════

#region Logic

public static class DiceRoller
{
    public static int Roll(int numDice, int sides, int modifier, Random rng)
    {
        int total = 0;
        for (int i = 0; i < numDice; i++) total += rng.Next(1, sides + 1);
        return total + modifier;
    }

    public static int RollD20(Random rng, int modifier = 0) => Roll(1, 20, modifier, rng);

    public static int RollAbilityScore(Random rng)
    {
        var rolls = new int[4];
        for (int i = 0; i < 4; i++) rolls[i] = rng.Next(1, 7);
        Array.Sort(rolls);
        return rolls[1] + rolls[2] + rolls[3]; // drop lowest
    }

    /// <summary>Parse dice notation like "2d6+3" and roll it.</summary>
    public static int RollDiceNotation(string notation, Random rng)
    {
        // format: NdS or NdS+M or NdS-M
        int modifier = 0;
        string corePart = notation;
        int plusIdx = notation.IndexOf('+');
        int minusIdx = notation.LastIndexOf('-');
        if (plusIdx > 0)
        {
            corePart = notation[..plusIdx];
            int.TryParse(notation[(plusIdx + 1)..], out modifier);
        }
        else if (minusIdx > 0)
        {
            corePart = notation[..minusIdx];
            if (int.TryParse(notation[(minusIdx + 1)..], out int m)) modifier = -m;
        }

        int dIdx = corePart.IndexOf('d');
        if (dIdx < 0) { int.TryParse(corePart, out int flat); return flat + modifier; }

        int.TryParse(corePart[..dIdx], out int numDice);
        int.TryParse(corePart[(dIdx + 1)..], out int sides);
        if (numDice <= 0) numDice = 1;
        if (sides <= 0) sides = 6;
        return Roll(numDice, sides, modifier, rng);
    }
}

public class InitiativeEntry
{
    public object Entity { get; set; } = null!; // DnDCharacter or DnDEnemy
    public int Initiative { get; set; }
    public bool IsEnemy { get; set; }
    public int SeatOrIndex { get; set; } // seat for player, index in enemies for enemy
}

public class CombatManager
{
    public List<InitiativeEntry> InitiativeOrder { get; private set; } = new();
    public int CurrentTurn { get; set; }
    public int RoundNumber { get; set; } = 1;

    public void RollInitiative(Dictionary<int, DnDCharacter> characters, List<DnDEnemy> enemies, Random rng)
    {
        InitiativeOrder.Clear();
        foreach (var kv in characters)
        {
            int dexMod = kv.Value.GetAbilityModifier("Dexterity");
            int init = DiceRoller.RollD20(rng, dexMod);
            InitiativeOrder.Add(new InitiativeEntry { Entity = kv.Value, Initiative = init, IsEnemy = false, SeatOrIndex = kv.Key });
        }
        for (int i = 0; i < enemies.Count; i++)
        {
            int init = DiceRoller.RollD20(rng);
            InitiativeOrder.Add(new InitiativeEntry { Entity = enemies[i], Initiative = init, IsEnemy = true, SeatOrIndex = i });
        }
        InitiativeOrder = InitiativeOrder.OrderByDescending(e => e.Initiative).ToList();
        CurrentTurn = 0;
        RoundNumber = 1;
    }

    public void NextTurn()
    {
        if (InitiativeOrder.Count == 0) return;
        CurrentTurn = (CurrentTurn + 1) % InitiativeOrder.Count;
        if (CurrentTurn == 0) RoundNumber++;
    }

    public InitiativeEntry? GetCurrentEntry() =>
        InitiativeOrder.Count > 0 ? InitiativeOrder[CurrentTurn] : null;
}

#endregion

// ════════════════════════════════════════════════════════════════
//  Character creation helpers (ported from dnd_character_creation.py)
// ════════════════════════════════════════════════════════════════

#region Character Creation Helpers

public static class DnDCharacterCreation
{
    private static long StableRngSeed(params string[] parts)
    {
        string raw = string.Join("|", parts.Select(p => p ?? ""));
        byte[] hash = SHA256.HashData(Encoding.UTF8.GetBytes(raw));
        return Math.Abs(BitConverter.ToInt64(hash, 0));
    }

    public static List<string> PickAdditionalSkills(string charClass, Dictionary<string, string> answers, Random rng)
    {
        var allSkills = DnDData.SkillAbilities.Keys.ToList();
        var baseSkills = DnDData.ClassSkills.GetValueOrDefault(charClass)?.ToList() ?? new List<string>();
        var pool = allSkills.Where(s => !baseSkills.Contains(s)).ToList();

        var bias = new List<string>();
        string origin = answers.GetValueOrDefault("origin", "");
        if (origin.Contains("City")) bias.AddRange(new[] { "Stealth", "Sleight of Hand", "Deception", "Investigation" });
        if (origin.Contains("Wilderness") || origin.Contains("Frontier")) bias.AddRange(new[] { "Survival", "Nature", "Perception", "Animal Handling" });
        if (origin.Contains("Monastery")) bias.AddRange(new[] { "Insight", "Medicine", "Religion" });
        if (origin.Contains("Noble")) bias.AddRange(new[] { "Persuasion", "History", "Performance" });

        string style = answers.GetValueOrDefault("style", "");
        if (style.Contains("Plan")) bias.AddRange(new[] { "Investigation", "History" });
        if (style.Contains("Talk") || answers.GetValueOrDefault("social", "").Contains("negotiator"))
            bias.AddRange(new[] { "Persuasion", "Insight", "Deception" });
        if (style.Contains("tricks") || answers.GetValueOrDefault("social", "").Contains("watcher"))
            bias.AddRange(new[] { "Stealth", "Sleight of Hand", "Perception" });

        string faith = answers.GetValueOrDefault("faith", "");
        if (faith is "Devout" or "Haunted") bias.AddRange(new[] { "Religion", "Insight", "Medicine" });
        string magic = answers.GetValueOrDefault("magic", "");
        if (magic is "I study it" or "I use it" or "I envy it") bias.AddRange(new[] { "Arcana", "Investigation", "History" });

        var picks = new List<string>();
        for (int attempt = 0; attempt < 8 && picks.Count < 2; attempt++)
        {
            var candidates = bias.Where(s => pool.Contains(s) && !picks.Contains(s)).ToList();
            if (candidates.Count > 0)
                picks.Add(candidates[rng.Next(candidates.Count)]);
            else
            {
                var remaining = pool.Where(s => !picks.Contains(s)).ToList();
                if (remaining.Count > 0) picks.Add(remaining[rng.Next(remaining.Count)]);
            }
        }
        return picks.Take(2).ToList();
    }

    public static (List<InventoryItem> Items, Dictionary<string, string> EquipMap) StartingLoadout(string charClass)
    {
        var items = new List<InventoryItem>();
        var equip = new Dictionary<string, string>();

        InventoryItem Gear(string name, string slot, int acBonus = 0) =>
            new() { Id = InventoryItem.NewItemId(), Name = name, Kind = "gear", Slot = slot, AcBonus = acBonus };
        InventoryItem Misc(string name) =>
            new() { Id = InventoryItem.NewItemId(), Name = name, Kind = "misc" };
        InventoryItem Heal(int amount = 6) =>
            new() { Id = InventoryItem.NewItemId(), Name = "Healing Potion", Kind = "consumable", Effect = new ItemEffect { Type = "heal", Amount = amount } };

        switch (charClass)
        {
            case "Fighter":
                items.AddRange(new[] { Gear("Chain Mail", "chest", 6), Misc("Longsword"), Misc("Adventurer's Pack"), Heal(6) });
                equip["chest"] = "__auto:Chain Mail"; equip["sword"] = "__auto:Longsword"; break;
            case "Rogue":
                items.AddRange(new[] { Gear("Leather Armor", "chest", 1), Misc("Dagger"), Misc("Thieves' Tools"), Misc("Shortbow"), Heal(6) });
                equip["chest"] = "__auto:Leather Armor"; equip["knife"] = "__auto:Dagger"; equip["bow"] = "__auto:Shortbow"; break;
            case "Wizard":
                items.AddRange(new[] { Gear("Padded Robes", "chest", 0), Misc("Staff"), Misc("Spellbook"), Misc("Component Pouch"), Heal(6) });
                equip["chest"] = "__auto:Padded Robes"; equip["staff"] = "__auto:Staff"; break;
            case "Cleric":
                items.AddRange(new[] { Gear("Chain Mail", "chest", 6), Misc("Warhammer"), Misc("Holy Symbol"), Misc("Healer's Kit"), Heal(8) });
                equip["chest"] = "__auto:Chain Mail"; equip["sword"] = "__auto:Warhammer"; break;
            case "Ranger":
                items.AddRange(new[] { Gear("Leather Armor", "chest", 1), Misc("Longbow"), Misc("Dagger"), Misc("Trail Rations"), Heal(6) });
                equip["chest"] = "__auto:Leather Armor"; equip["bow"] = "__auto:Longbow"; equip["knife"] = "__auto:Dagger"; break;
            case "Paladin":
                items.AddRange(new[] { Gear("Chain Mail", "chest", 6), Misc("Longsword"), Misc("Oath Token"), Misc("Traveler's Pack"), Heal(8) });
                equip["chest"] = "__auto:Chain Mail"; equip["sword"] = "__auto:Longsword"; break;
            default:
                items.AddRange(new[] { Gear("Leather Armor", "chest", 1), Misc("Dagger"), Misc("Adventurer's Pack"), Heal(6) });
                equip["chest"] = "__auto:Leather Armor"; equip["knife"] = "__auto:Dagger"; break;
        }
        return (items, equip);
    }

    public static (string Background, List<string> Feats, List<string> Features) GenerateBackgroundText(
        string name, string race, string charClass, Dictionary<string, string> answers, string seedHint)
    {
        string answersJson;
        try { answersJson = JsonSerializer.Serialize(answers.OrderBy(k => k.Key).ToDictionary(k => k.Key, k => k.Value)); }
        catch { answersJson = ""; }

        long seed = StableRngSeed(name, race, charClass, seedHint, answersJson);
        var rng = new Random((int)(seed & int.MaxValue));

        string origin = answers.GetValueOrDefault("origin") ?? rng.Next(4) switch
        {
            0 => "a quiet village", 1 => "city alleys", 2 => "a frontier outpost", _ => "the wilderness"
        };
        string turning = answers.GetValueOrDefault("turning_point") ?? "curiosity";
        string virtue = answers.GetValueOrDefault("virtue") ?? "honor";
        string flaw = answers.GetValueOrDefault("flaw") ?? "pride";
        string bond = answers.GetValueOrDefault("bond") ?? "a promise";
        string keepsake = answers.GetValueOrDefault("keepsake") ?? "a token";
        string? hook = answers.GetValueOrDefault("hook");
        if (!string.IsNullOrEmpty(hook) && hook!.Length > 140) hook = hook[..140];

        string[] openers = {
            "You learned early that the world rarely offers clean choices.",
            "You grew up with one foot in trouble and the other in duty.",
            "You were shaped by long nights, short tempers, and longer roads.",
            "You found comfort in routines\u2014until adventure broke them.",
            "You learned to read people before you learned to read books.",
        };
        string[] twists = {
            "A single night changed everything.",
            "A quiet moment became a vow.",
            "A mistake became a lesson you refuse to forget.",
            "A stranger's words lodged in your mind like a splinter.",
            "An old debt still casts a long shadow.",
        };
        string[] closers = {
            "You don't seek glory\u2014only a reason to believe you can make things right.",
            "You keep moving because standing still feels like losing.",
            "You measure your life in promises kept, not battles won.",
            "You've decided your story won't be written by fear.",
        };

        string opener = openers[rng.Next(openers.Length)];
        string twist = twists[rng.Next(twists.Length)];
        string closer = closers[rng.Next(closers.Length)];

        var bg = new StringBuilder();
        bg.Append($"{opener}\n\n");
        bg.Append($"You grew up in {origin.ToLower()}, and you learned to lean on {virtue.ToLower()}\u2014even when it made you stubborn. ");
        bg.Append($"When {turning.ToLower()} pulled you onto the road, you didn't hesitate for long. {twist}");
        bg.Append($"\n\nYour greatest flaw is {flaw.ToLower()}, and you're not proud of the damage it's caused. ");
        bg.Append($"Still, {bond.ToLower()} keeps you standing when the odds turn. You carry {keepsake.ToLower()} as a reminder of who you were before you became a {charClass.ToLower()}.");
        if (!string.IsNullOrEmpty(hook))
            bg.Append($"\n\nUnique detail: {hook}");
        bg.Append($"\n\n{closer}");

        // Feats
        var classFeatures = new Dictionary<string, string[]>
        {
            ["Fighter"] = new[] { "Combat Training", "Steel Nerve" },
            ["Wizard"] = new[] { "Arcane Study", "Ritual Habit" },
            ["Rogue"] = new[] { "Quick Hands", "Shadow Sense" },
            ["Cleric"] = new[] { "Sacred Channel", "Vow of Mercy" },
            ["Ranger"] = new[] { "Trailcraft", "Keen Aim" },
            ["Paladin"] = new[] { "Oathbound", "Radiant Presence" },
        };
        string[] traitPool = { "Silver Tongue", "Battle Instinct", "Keen Observer", "Iron Stomach",
            "Steady Hands", "Unshakable Focus", "Lucky Breaks", "Streetwise", "Wilderness Blood", "Bookish" };

        var biasFeat = new List<string>();
        if (origin.Contains("City")) biasFeat.AddRange(new[] { "Streetwise", "Steady Hands", "Silver Tongue" });
        if (origin.Contains("Wilderness") || origin.Contains("Frontier")) biasFeat.AddRange(new[] { "Wilderness Blood", "Keen Observer", "Battle Instinct" });
        string magicAnswer = answers.GetValueOrDefault("magic", "");
        if (magicAnswer is "I study it" or "I use it") biasFeat.AddRange(new[] { "Bookish", "Unshakable Focus" });

        var feats = new List<string>();
        var featPool = new List<string>(biasFeat);
        featPool.AddRange(traitPool);
        for (int attempt = 0; attempt < 8 && feats.Count < 1; attempt++)
        {
            if (featPool.Count == 0) break;
            string f = featPool[rng.Next(featPool.Count)];
            if (!feats.Contains(f)) feats.Add(f);
            featPool.RemoveAll(x => x == f);
        }

        var features = classFeatures.GetValueOrDefault(charClass)?.ToList() ?? new List<string> { "Adventurer" };
        string[] extraFeatures = { "Resourceful", "Calm Under Pressure", "Hard to Read", "People Person", "Tinkerer's Touch", "Uncanny Luck" };
        string extra = extraFeatures[rng.Next(extraFeatures.Length)];
        if (!features.Contains(extra)) features.Add(extra);

        return (bg.ToString(), feats, features);
    }
}

#endregion

// ════════════════════════════════════════════════════════════════
//  DnDGameSharp — main game class
// ════════════════════════════════════════════════════════════════

public class DnDGameSharp : BaseGame
{
    public override string ThemeName => "dnd";

    // ── Game state ─────────────────────────────────────────────
    private string _phase = "player_select"; // player_select, char_creation, gameplay, combat
    private int? _dmSeat;

    /// <summary>Public accessor so the server can auto-assign DM before auto-start.</summary>
    public int? DmSeat
    {
        get => _dmSeat;
        set => _dmSeat = value;
    }

    // Characters per seat
    private readonly Dictionary<int, DnDCharacter> _characters = new();

    // Enemies on the field
    private readonly List<DnDEnemy> _enemies = new();

    // Combat
    private readonly CombatManager _combatManager = new();
    private bool _inCombat;

    // Combat log
    private readonly List<string> _combatLog = new();

    // Background (image filename from dnd/backgrounds/)
    private string? _background;

    // Buttons per player
    private readonly Dictionary<int, Dictionary<string, (string Text, bool Enabled)>> _buttons = new();

    // Animations
    private readonly ParticleSystem _particles = new();
    private readonly List<TextPopAnim> _textPops = new();
    private readonly List<ScreenFlash> _flashes = new();
    private readonly List<PulseRing> _pulseRings = new();
    private double _animTime;

    // ── Constructor ────────────────────────────────────────────
    public DnDGameSharp(int w, int h, Renderer renderer) : base(w, h, renderer) { }

    // ── Start game ─────────────────────────────────────────────
    public override void StartGame(List<int> players)
    {
        ActivePlayers = new List<int>(players.OrderBy(x => x));
        _characters.Clear();
        _enemies.Clear();
        _combatLog.Clear();
        _inCombat = false;
        _buttons.Clear();

        // If DM is not in selected players, clear it
        if (_dmSeat.HasValue && !ActivePlayers.Contains(_dmSeat.Value))
            _dmSeat = null;

        _phase = "char_creation";
        State = "playing";
        RefreshAllButtons();
    }

    // ── HandleClick (web UI) ───────────────────────────────────
    public override void HandleClick(int playerIdx, string buttonId)
    {
        // Game-specific messages from server passthrough
        if (buttonId.StartsWith("__msg__:"))
        {
            var parts = buttonId.Split(':', 3);
            if (parts.Length >= 2)
            {
                string msgType = parts[1];
                string json = parts.Length > 2 ? parts[2] : "";
                HandleMessage(playerIdx, msgType, json);
            }
            return;
        }

        // Regular button presses
        HandleButtonPress(playerIdx, buttonId);
    }

    public override void HandleMessage(int playerIdx, string type, string json)
    {
        Dictionary<string, JsonElement>? data = null;
        if (!string.IsNullOrEmpty(json))
        {
            try { data = JsonSerializer.Deserialize<Dictionary<string, JsonElement>>(json); } catch { /* ignore */ }
        }

        switch (type)
        {
            case "dnd_set_dm":
                HandleSetDm(playerIdx);
                break;
            case "dnd_load_character":
                HandleLoadCharacter(playerIdx);
                break;
            case "dnd_create_character":
                HandleCreateCharacter(playerIdx, data);
                break;
            case "dnd_roll_dice":
                HandleRollDice(playerIdx, data);
                break;
            case "dnd_dm_give_item":
                HandleDmGiveItem(playerIdx, data);
                break;
            case "dnd_use_item":
                HandleUseItem(playerIdx, data);
                break;
            case "dnd_equip_item":
                HandleEquipItem(playerIdx, data);
                break;
            case "dnd_unequip_slot":
                HandleUnequipSlot(playerIdx, data);
                break;
            case "dnd_dm_spawn_enemy":
                HandleDmSpawnEnemy(playerIdx, data);
                break;
            case "dnd_dm_adjust_enemy_hp":
                HandleDmAdjustEnemyHp(playerIdx, data);
                break;
            case "dnd_dm_remove_enemy":
                HandleDmRemoveEnemy(playerIdx, data);
                break;
            case "dnd_dm_set_background_file":
                HandleDmSetBackgroundFile(playerIdx, data);
                break;
        }
    }

    // ── Message handlers ───────────────────────────────────────

    private void HandleSetDm(int seat)
    {
        if (_phase != "player_select") return;
        if (!ActivePlayers.Contains(seat) && seat >= 0 && seat <= 7)
        {
            // Not yet started — allow pre-setting
        }
        _dmSeat = seat;
        AddCombatLog($"{PlayerName(seat)} set as DM");
        RefreshAllButtons();
    }

    private void HandleLoadCharacter(int seat)
    {
        if (_phase != "char_creation") return;
        if (_dmSeat.HasValue && seat == _dmSeat.Value) return;
        var ch = DnDCharacter.LoadFromFile(seat);
        if (ch == null) return;
        _characters[seat] = ch;
        AddCombatLog($"{PlayerName(seat)} loaded character: {ch.Name}");
        MaybeAdvanceFromCharCreation();
        RefreshAllButtons();
    }

    private void HandleCreateCharacter(int playerIdx, Dictionary<string, JsonElement>? data)
    {
        if (_phase != "char_creation") return;
        if (_dmSeat.HasValue && playerIdx == _dmSeat.Value) return;
        if (data == null) return;

        string race = data.GetValueOrDefault("race").GetString()?.Trim() ?? "";
        string charClass = data.GetValueOrDefault("char_class").GetString()?.Trim() ?? "";
        string name = data.GetValueOrDefault("name").GetString()?.Trim() ?? "";
        if (!DnDData.Races.Contains(race) || !DnDData.Classes.Contains(charClass)) return;

        // Parse optional abilities (point-buy)
        Dictionary<string, int>? abilities = null;
        if (data.TryGetValue("abilities", out var abEl) && abEl.ValueKind == JsonValueKind.Object)
        {
            try
            {
                var parsed = new Dictionary<string, int>();
                var costMap = new Dictionary<int, int>
                {
                    [8] = 0, [9] = 1, [10] = 2, [11] = 3, [12] = 4, [13] = 5, [14] = 7, [15] = 9,
                };
                int totalCost = 0;
                foreach (string a in DnDData.AbilityScores)
                {
                    if (!abEl.TryGetProperty(a, out var v)) throw new Exception("missing");
                    int val = v.GetInt32();
                    if (val < 8 || val > 15) throw new Exception("range");
                    if (!costMap.TryGetValue(val, out int c)) throw new Exception("cost");
                    totalCost += c;
                    parsed[a] = val;
                }
                if (totalCost > 27) throw new Exception("budget");
                abilities = parsed;
            }
            catch { abilities = null; }
        }

        if (abilities == null)
        {
            abilities = new Dictionary<string, int>();
            foreach (string a in DnDData.AbilityScores)
                abilities[a] = DiceRoller.RollAbilityScore(Rng);
        }

        if (string.IsNullOrEmpty(name))
            name = DnDData.GenerateCharacterName(race, charClass, Rng);

        // Parse background answers
        var bgAnswers = new Dictionary<string, string>();
        if (data.TryGetValue("background_answers", out var baEl) && baEl.ValueKind == JsonValueKind.Object)
        {
            foreach (var prop in baEl.EnumerateObject())
            {
                string kid = prop.Name.Trim();
                if (kid.Length > 0)
                    bgAnswers[kid] = prop.Value.GetString()?.Trim() ?? "";
            }
        }

        var ch = new DnDCharacter
        {
            Name = name,
            Race = race,
            CharClass = charClass,
            Level = 1,
            Alignment = DnDData.Alignments[Rng.Next(DnDData.Alignments.Length)],
            Abilities = abilities,
        };

        // Skills
        var baseSkills = DnDData.ClassSkills.GetValueOrDefault(charClass)?.Take(2).ToList() ?? new List<string>();
        string seedHint = $"seat:{playerIdx}";
        var seedVal = (int)(Math.Abs(seedHint.GetHashCode()) & int.MaxValue);
        var extraSkills = DnDCharacterCreation.PickAdditionalSkills(charClass, bgAnswers, new Random(seedVal));
        var merged = new List<string>();
        foreach (string s in baseSkills.Concat(extraSkills))
            if (s.Length > 0 && !merged.Contains(s)) merged.Add(s);
        ch.Skills = merged;

        // Starting gear
        var (loadoutItems, equipMap) = DnDCharacterCreation.StartingLoadout(charClass);
        foreach (var it in loadoutItems) ch.Inventory.Add(it);

        // Resolve __auto: references
        var nameToId = new Dictionary<string, string>();
        foreach (var it in ch.Inventory)
            if (!nameToId.ContainsKey(it.Name)) nameToId[it.Name] = it.Id;

        foreach (var kv in equipMap)
        {
            string slot = kv.Key;
            string r = kv.Value;
            if (r.StartsWith("__auto:"))
            {
                string nm = r["__auto:".Length..].Trim();
                if (nameToId.TryGetValue(nm, out string? iid))
                    ch.Equipment[slot] = iid;
            }
            else if (r.Length > 0)
                ch.Equipment[slot] = r;
        }

        // Background text
        var (bgText, feats, features) = DnDCharacterCreation.GenerateBackgroundText(name, race, charClass, bgAnswers, seedHint);
        ch.Background = bgText;
        ch.BackgroundAnswers = bgAnswers;
        ch.Feats = feats;
        ch.Features = features;

        ch.Gold = 100;
        ch.UpdateDerivedStats(resetCurrentHp: true);
        ch.SaveToFile(playerIdx);

        _characters[playerIdx] = ch;
        AddCombatLog($"{PlayerName(playerIdx)} created {name} ({race} {charClass})");
        MaybeAdvanceFromCharCreation();
        RefreshAllButtons();
    }

    private void HandleRollDice(int playerIdx, Dictionary<string, JsonElement>? data)
    {
        if (data == null) return;
        if (!data.TryGetValue("sides", out var sidesEl)) return;
        int sides = sidesEl.GetInt32();
        if (sides is not (4 or 6 or 8 or 10 or 12 or 20)) return;

        int result = Rng.Next(1, sides + 1);
        AddCombatLog($"{PlayerName(playerIdx)} rolled d{sides}: {result}");

        // Visual feedback
        int cx = ScreenW / 2, cy = ScreenH / 2;
        _textPops.Add(new TextPopAnim($"d{sides}: {result}", cx, cy - 40, (255, 235, 120), fontSize: 32));
        _particles.EmitSparkle(cx, cy, (255, 235, 120), 12);

        RefreshAllButtons();
    }

    private void HandleDmGiveItem(int playerIdx, Dictionary<string, JsonElement>? data)
    {
        if (!IsDm(playerIdx) || data == null) return;
        if (!data.TryGetValue("target_player_idx", out var tEl)) return;
        int target = tEl.GetInt32();
        if (!_characters.TryGetValue(target, out var ch)) return;

        string itemName = "Item";
        string kind = "misc";
        string? slot = null;
        int acBonus = 0;
        ItemEffect? effect = null;

        if (data.TryGetValue("item", out var itemEl))
        {
            if (itemEl.ValueKind == JsonValueKind.String)
            {
                itemName = itemEl.GetString()?.Trim() ?? "Item";
            }
            else if (itemEl.ValueKind == JsonValueKind.Object)
            {
                itemName = itemEl.TryGetProperty("name", out var n) ? n.GetString()?.Trim() ?? "Item" : "Item";
                kind = itemEl.TryGetProperty("kind", out var k) ? k.GetString()?.Trim() ?? "misc" : "misc";
                if (kind == "gear")
                {
                    slot = itemEl.TryGetProperty("slot", out var s) ? s.GetString()?.Trim() : null;
                    acBonus = itemEl.TryGetProperty("ac_bonus", out var ab) && ab.TryGetInt32(out int abv) ? abv : 0;
                }
                else if (kind == "consumable" && itemEl.TryGetProperty("effect", out var eff) && eff.ValueKind == JsonValueKind.Object)
                {
                    effect = new ItemEffect
                    {
                        Type = eff.TryGetProperty("type", out var et) ? et.GetString()?.Trim() ?? "heal" : "heal",
                        Amount = eff.TryGetProperty("amount", out var ea) && ea.TryGetInt32(out int eav) ? eav : 0,
                    };
                }
            }
        }

        ch.AddItem(itemName, kind, slot, acBonus, effect);
        ch.SaveToFile(target);
        AddCombatLog($"DM gave {itemName} to {PlayerName(target)}");
        RefreshAllButtons();
    }

    private void HandleUseItem(int seat, Dictionary<string, JsonElement>? data)
    {
        if (data == null) return;
        string itemId = data.GetValueOrDefault("item_id").GetString()?.Trim() ?? "";
        if (itemId.Length == 0) return;
        if (!_characters.TryGetValue(seat, out var ch)) return;
        if (ch.UseItem(itemId))
        {
            ch.SaveToFile(seat);
            AddCombatLog($"{PlayerName(seat)} used an item");
        }
        RefreshAllButtons();
    }

    private void HandleEquipItem(int seat, Dictionary<string, JsonElement>? data)
    {
        if (data == null) return;
        string itemId = data.GetValueOrDefault("item_id").GetString()?.Trim() ?? "";
        if (itemId.Length == 0) return;
        if (!_characters.TryGetValue(seat, out var ch)) return;
        if (ch.EquipItem(itemId))
        {
            ch.SaveToFile(seat);
            AddCombatLog($"{PlayerName(seat)} equipped gear");
        }
        RefreshAllButtons();
    }

    private void HandleUnequipSlot(int seat, Dictionary<string, JsonElement>? data)
    {
        if (data == null) return;
        string slot = data.GetValueOrDefault("slot").GetString()?.Trim() ?? "";
        if (slot.Length == 0) return;
        if (!_characters.TryGetValue(seat, out var ch)) return;
        if (ch.UnequipSlot(slot))
        {
            ch.SaveToFile(seat);
            AddCombatLog($"{PlayerName(seat)} unequipped {slot}");
        }
        RefreshAllButtons();
    }

    private void HandleDmSpawnEnemy(int playerIdx, Dictionary<string, JsonElement>? data)
    {
        if (!IsDm(playerIdx)) return;
        string monsterName = data?.GetValueOrDefault("monster").GetString()?.Trim() ?? "";
        if (monsterName.Length == 0)
        {
            var keys = DnDData.Monsters.Keys.ToList();
            if (keys.Count == 0) return;
            monsterName = keys[Rng.Next(keys.Count)];
        }
        if (!DnDData.Monsters.TryGetValue(monsterName, out var template)) return;

        var enemy = new DnDEnemy(template);
        _enemies.Add(enemy);
        AddCombatLog($"DM spawned {monsterName}!");

        // Start combat if not already
        if (!_inCombat && _characters.Count > 0)
        {
            _combatManager.RollInitiative(_characters, _enemies, Rng);
            _inCombat = true;
            _phase = "combat";
            AddCombatLog("Combat started!");
        }

        // Visual feedback
        int cx = ScreenW / 2, cy = ScreenH / 2;
        _flashes.Add(new ScreenFlash((200, 80, 80), 40, 0.6f));
        _textPops.Add(new TextPopAnim($"{monsterName} appears!", cx, cy - 50, (255, 100, 100), fontSize: 28));
        _particles.EmitSparkle(cx, cy, (255, 100, 100), 15);

        RefreshAllButtons();
    }

    private void HandleDmAdjustEnemyHp(int playerIdx, Dictionary<string, JsonElement>? data)
    {
        if (!IsDm(playerIdx) || data == null) return;
        if (!data.TryGetValue("enemy_idx", out var idxEl) || !data.TryGetValue("delta", out var deltaEl)) return;
        int idx = idxEl.GetInt32();
        int delta = deltaEl.GetInt32();
        if (delta == 0 || idx < 0 || idx >= _enemies.Count) return;

        var enemy = _enemies[idx];
        if (delta < 0)
            enemy.TakeDamage(Math.Abs(delta));
        else
            enemy.Heal(delta);
        AddCombatLog($"DM adjusted {enemy.Name} HP ({delta:+0})");
        RefreshAllButtons();
    }

    private void HandleDmRemoveEnemy(int playerIdx, Dictionary<string, JsonElement>? data)
    {
        if (!IsDm(playerIdx) || data == null) return;
        if (!data.TryGetValue("enemy_idx", out var idxEl)) return;
        int idx = idxEl.GetInt32();
        if (idx < 0 || idx >= _enemies.Count) return;

        string ename = _enemies[idx].Name;
        _enemies.RemoveAt(idx);
        AddCombatLog($"DM removed {ename}");

        if (_enemies.Count == 0)
        {
            _inCombat = false;
            if (_phase == "combat") _phase = "gameplay";
            AddCombatLog("Combat ended");
        }
        RefreshAllButtons();
    }

    private void HandleDmSetBackgroundFile(int playerIdx, Dictionary<string, JsonElement>? data)
    {
        if (!IsDm(playerIdx) || data == null) return;
        string bgFile = data.GetValueOrDefault("background_file").GetString()?.Trim() ?? "";
        if (bgFile.Length == 0) return;
        // Could validate against available files, but for now just store it
        _background = bgFile;
        AddCombatLog($"DM set background: {bgFile}");
    }

    // ── Regular button press handler ───────────────────────────
    private void HandleButtonPress(int playerIdx, string buttonId)
    {
        if (_phase == "gameplay" || _phase == "combat")
        {
            if (!_characters.TryGetValue(playerIdx, out var ch)) return;
            switch (buttonId)
            {
                case "btn_attack":
                    HandlePlayerAttack(playerIdx, ch);
                    break;
                case "btn_defend":
                    HandlePlayerDefend(playerIdx, ch);
                    break;
                case "btn_roll_d20":
                    HandleRollDice(playerIdx, new Dictionary<string, JsonElement>
                    {
                        ["sides"] = JsonDocument.Parse("20").RootElement,
                    });
                    break;
            }
        }
        RefreshAllButtons();
    }

    private void HandlePlayerAttack(int seat, DnDCharacter ch)
    {
        if (!_inCombat || _enemies.Count == 0) return;

        // Find first living enemy
        var target = _enemies.FirstOrDefault(e => e.IsAlive);
        if (target == null) return;

        int strMod = ch.GetAbilityModifier("Strength");
        int attackRoll = DiceRoller.RollD20(Rng, strMod);
        if (attackRoll >= target.ArmorClass)
        {
            // Hit
            int damage = DiceRoller.Roll(1, 8, strMod, Rng); // 1d8 + str
            damage = Math.Max(1, damage);
            target.TakeDamage(damage);
            AddCombatLog($"{ch.Name} hits {target.Name} for {damage} damage! (Roll: {attackRoll})");

            int cx = ScreenW / 2, cy = ScreenH / 2;
            _textPops.Add(new TextPopAnim($"-{damage}", cx + 80, cy, (255, 80, 80), fontSize: 28));
            _particles.EmitSparkle(cx + 80, cy, (255, 80, 80), 8);

            if (!target.IsAlive)
            {
                AddCombatLog($"{target.Name} is defeated! (+{target.Xp} XP)");
                ch.Experience += target.Xp;

                // Monster defeated animation
                try
                {
                    _textPops.Add(new TextPopAnim($"💀 {target.Name} defeated!", cx, cy - 40, (255, 200, 60), fontSize: 24));
                    _textPops.Add(new TextPopAnim($"+{target.Xp} XP", cx + 80, cy + 30, (100, 255, 100), fontSize: 22));
                    _pulseRings.Add(new PulseRing(cx + 80, cy, (255, 200, 60), maxRadius: 60, duration: 0.6f));
                }
                catch { }

                CheckLevelUp(ch, seat);
            }
        }
        else
        {
            AddCombatLog($"{ch.Name} misses {target.Name}! (Roll: {attackRoll} vs AC {target.ArmorClass})");

            // Miss animation
            try
            {
                int cx = ScreenW / 2, cy = ScreenH / 2;
                _textPops.Add(new TextPopAnim("MISS!", cx + 80, cy, (160, 160, 160), fontSize: 24));
            }
            catch { }
        }

        // Remove dead enemies and check combat end
        _enemies.RemoveAll(e => !e.IsAlive);
        if (_enemies.Count == 0)
        {
            _inCombat = false;
            _phase = "gameplay";
            AddCombatLog("All enemies defeated! Combat ended.");
            _flashes.Add(new ScreenFlash((100, 255, 100), 40, 0.5f));
        }

        // Advance combat turn
        if (_inCombat && _combatManager.InitiativeOrder.Count > 0)
        {
            _combatManager.NextTurn();
            ProcessEnemyTurns();
        }
    }

    private void HandlePlayerDefend(int seat, DnDCharacter ch)
    {
        AddCombatLog($"{ch.Name} takes the Dodge action (disadvantage on attacks against them).");
    }

    private void ProcessEnemyTurns()
    {
        // Process all enemy turns until it's a player's turn again
        int maxIter = 50; // safety
        while (maxIter-- > 0 && _inCombat)
        {
            var entry = _combatManager.GetCurrentEntry();
            if (entry == null || !entry.IsEnemy) break;

            if (entry.Entity is DnDEnemy enemy && enemy.IsAlive)
            {
                // Enemy attacks a random player character
                var targets = _characters.Where(kv => kv.Value.CurrentHp > 0).ToList();
                if (targets.Count > 0)
                {
                    var (targetSeat, targetCh) = targets[Rng.Next(targets.Count)];
                    var attack = enemy.Attacks.Length > 0 ? enemy.Attacks[0] : null;
                    if (attack != null)
                    {
                        int attackRoll = DiceRoller.RollD20(Rng, attack.Bonus);
                        if (attackRoll >= targetCh.ArmorClass)
                        {
                            int damage = DiceRoller.RollDiceNotation(attack.Damage, Rng);
                            damage = Math.Max(1, damage);
                            targetCh.CurrentHp = Math.Max(0, targetCh.CurrentHp - damage);
                            AddCombatLog($"{enemy.Name}'s {attack.Name} hits {targetCh.Name} for {damage}! (Roll: {attackRoll})");

                            // Enemy hit animation
                            try
                            {
                                int cx = ScreenW / 2, cy = ScreenH / 2;
                                _flashes.Add(new ScreenFlash((200, 40, 40), 30, 0.3f));
                                _textPops.Add(new TextPopAnim($"-{damage}", cx - 80, cy, (255, 80, 80), fontSize: 26));
                                _particles.EmitSparkle(cx - 80, cy, (255, 80, 80), 6);
                            }
                            catch { }

                            if (targetCh.CurrentHp <= 0)
                            {
                                AddCombatLog($"{targetCh.Name} falls unconscious!");

                                // Unconscious animation
                                try
                                {
                                    int cx2 = ScreenW / 2, cy2 = ScreenH / 2;
                                    _flashes.Add(new ScreenFlash((100, 0, 0), 50, 0.5f));
                                    _textPops.Add(new TextPopAnim($"💔 {targetCh.Name} DOWN!", cx2, cy2 - 40, (200, 50, 50), fontSize: 28));
                                    _pulseRings.Add(new PulseRing(cx2, cy2, (200, 50, 50), maxRadius: 80, duration: 0.7f));
                                }
                                catch { }
                            }
                        }
                        else
                        {
                            AddCombatLog($"{enemy.Name}'s {attack.Name} misses {targetCh.Name}! (Roll: {attackRoll})");
                        }
                    }
                }

                // Troll regeneration
                if (enemy.Special != null && enemy.Special.Contains("Regeneration"))
                {
                    int regenAmount = 10;
                    enemy.Heal(regenAmount);
                    AddCombatLog($"{enemy.Name} regenerates {regenAmount} HP");
                }
            }

            _combatManager.NextTurn();
        }
    }

    private void CheckLevelUp(DnDCharacter ch, int seat)
    {
        for (int lvl = ch.Level + 1; lvl <= 10; lvl++)
        {
            if (DnDData.XpThresholds.TryGetValue(lvl, out int needed) && ch.Experience >= needed)
            {
                ch.Level = lvl;
                ch.UpdateDerivedStats(resetCurrentHp: true);
                AddCombatLog($"{ch.Name} reached level {lvl}!");
                ch.SaveToFile(seat);

                // Level-up celebration
                try
                {
                    int cx = ScreenW / 2, cy = ScreenH / 2;
                    _flashes.Add(new ScreenFlash((255, 215, 0), 55, 0.6f));
                    _textPops.Add(new TextPopAnim($"⬆ LEVEL {lvl}! ⬆", cx, cy - 60, (255, 215, 0), fontSize: 36));
                    _pulseRings.Add(new PulseRing(cx, cy, (255, 215, 0), maxRadius: 120, duration: 1.0f));
                    _particles.EmitFirework(cx - 60, cy - 30, new[] { (255, 215, 0), (255, 180, 0), (255, 255, 150) });
                    _particles.EmitFirework(cx + 60, cy - 30, new[] { (255, 215, 0), (255, 180, 0), (255, 255, 150) });
                }
                catch { }
            }
            else break;
        }
    }

    // ── Helpers ─────────────────────────────────────────────────

    private bool IsDm(int seat) => _dmSeat.HasValue && _dmSeat.Value == seat;

    private void AddCombatLog(string msg)
    {
        _combatLog.Add(msg);
        if (_combatLog.Count > 50) _combatLog.RemoveAt(0);
    }

    private void MaybeAdvanceFromCharCreation()
    {
        if (_phase != "char_creation") return;
        if (ActivePlayers.Count == 0) return;
        foreach (int seat in ActivePlayers)
        {
            if (_dmSeat.HasValue && seat == _dmSeat.Value) continue;
            if (!_characters.ContainsKey(seat)) return;
        }
        _phase = "gameplay";
        AddCombatLog("All characters created! Adventure begins.");
        RefreshAllButtons();
    }

    // ── Button management ──────────────────────────────────────
    private void RefreshAllButtons()
    {
        _buttons.Clear();
        foreach (int seat in ActivePlayers)
            _buttons[seat] = BuildButtonsForSeat(seat);
    }

    private Dictionary<string, (string Text, bool Enabled)> BuildButtonsForSeat(int seat)
    {
        var btns = new Dictionary<string, (string Text, bool Enabled)>();

        if (_phase == "gameplay" || _phase == "combat")
        {
            bool hasChar = _characters.ContainsKey(seat);
            bool isDm = IsDm(seat);

            if (!isDm && hasChar)
            {
                bool inCombat = _inCombat && _enemies.Count > 0;
                btns["btn_attack"] = ("Attack", inCombat);
                btns["btn_defend"] = ("Defend", inCombat);
                btns["btn_roll_d20"] = ("Roll d20", true);
            }
        }

        return btns;
    }

    // ── Snapshot ────────────────────────────────────────────────
    public override Dictionary<string, object?> GetSnapshot(int playerIdx)
    {
        // Build players array (all 8 seats, matching Python snapshot format)
        var players = new List<object?>();
        for (int seat = 0; seat < 8; seat++)
        {
            bool hasSaved = DnDCharacter.CharacterExists(seat);
            _characters.TryGetValue(seat, out var ch);

            var stats = new Dictionary<string, object?>();
            if (ch != null)
            {
                foreach (var kv in ch.Abilities)
                {
                    string shortKey = kv.Key switch
                    {
                        "Strength" => "str", "Dexterity" => "dex", "Constitution" => "con",
                        "Intelligence" => "int", "Wisdom" => "wis", "Charisma" => "cha",
                        _ => kv.Key.ToLower(),
                    };
                    stats[shortKey] = kv.Value;
                }
            }

            // Build portrait emoji
            string portraitEmoji = ch?.Race switch
            {
                "Human" => "\U0001F464", // 👤
                "Elf" => "\U0001F9DD",   // 🧝
                "Dwarf" => "\u26CF\uFE0F", // ⛏️
                "Orc" => "\U0001F4AA",   // 💪
                "Halfling" => "\U0001F33E", // 🌾
                "Tiefling" => "\U0001F608", // 😈
                _ => "\U0001F464",
            };

            var charDict = ch != null ? new Dictionary<string, object?>
            {
                ["name"] = ch.Name,
                ["race"] = ch.Race,
                ["class"] = ch.CharClass,
                ["level"] = ch.Level,
                ["hp"] = ch.CurrentHp,
                ["max_hp"] = ch.MaxHp,
                ["ac"] = ch.ArmorClass,
                ["stats"] = stats,
                ["inventory"] = ch.Inventory.Select(it => (object?)it.Name).ToList(),
                ["gold"] = ch.Gold,
                ["abilities"] = ch.Skills.ToList(),
                ["backstory"] = ch.Background,
                ["portrait_emoji"] = portraitEmoji,
            } : null;

            players.Add(new Dictionary<string, object?>
            {
                ["seat"] = seat,
                ["name"] = ch != null ? ch.Name : PlayerName(seat),
                ["character"] = (object?)charDict,
                ["player_idx"] = seat,
                ["selected"] = ActivePlayers.Contains(seat),
                ["is_dm"] = IsDm(seat),
                ["has_saved"] = hasSaved,
                ["has_character"] = ch != null,
                ["race"] = ch?.Race ?? "",
                ["char_class"] = ch?.CharClass ?? "",
                ["hp"] = ch?.CurrentHp ?? 0,
                ["ac"] = ch?.ArmorClass ?? 0,
                ["abilities"] = ch != null
                    ? new Dictionary<string, object?>(ch.Abilities.ToDictionary(k => k.Key, k => (object?)k.Value))
                    : new Dictionary<string, object?>(),
                ["skills"] = ch?.Skills.ToList() ?? new List<string>(),
                ["background"] = ch?.Background ?? "",
                ["feats"] = ch?.Feats.ToList() ?? new List<string>(),
                ["features"] = ch?.Features.ToList() ?? new List<string>(),
                ["inventory"] = ch?.Inventory.Select(it => (object?)it.ToDict()).ToList() ?? new List<object?>(),
                ["equipment"] = ch != null
                    ? new Dictionary<string, object?>(ch.Equipment.ToDictionary(k => k.Key, k => (object?)k.Value))
                    : new Dictionary<string, object?>(),
            });
        }

        // Build enemies array
        var enemiesArr = _enemies.Select((e, idx) => (object?)new Dictionary<string, object?>
        {
            ["enemy_idx"] = idx,
            ["name"] = e.Name,
            ["hp"] = e.CurrentHp,
            ["max_hp"] = e.MaxHp,
            ["ac"] = e.ArmorClass,
            ["cr"] = e.Cr,
            ["emoji"] = e.Name switch
            {
                "Goblin" => "\U0001F47A",  // 👺
                "Orc" => "\U0001F479",     // 👹
                "Skeleton" => "\U0001F480", // 💀
                "Wolf" => "\U0001F43A",    // 🐺
                "Ogre" => "\U0001F479",    // 👹
                "Troll" => "\U0001F9CC",   // 🧌
                "Dragon Wyrmling" => "\U0001F409", // 🐉
                _ => "\U0001F47E",         // 👾
            },
        }).ToList();

        // Current turn info
        object? currentTurn = null;
        if (_inCombat && _combatManager.InitiativeOrder.Count > 0)
        {
            var entry = _combatManager.GetCurrentEntry();
            if (entry != null)
            {
                string turnName = entry.Entity switch
                {
                    DnDCharacter c => c.Name,
                    DnDEnemy e => e.Name,
                    _ => "Unknown",
                };
                currentTurn = new Dictionary<string, object?>
                {
                    ["name"] = turnName,
                    ["is_enemy"] = entry.IsEnemy,
                    ["seat_or_index"] = entry.SeatOrIndex,
                    ["round"] = _combatManager.RoundNumber,
                };
            }
        }

        // List available monsters for DM
        var monsterNames = DnDData.Monsters.Keys.OrderBy(k => k).ToList();

        var snap = new Dictionary<string, object?>
        {
            ["state"] = _phase,
            ["phase"] = _phase,
            ["dm_seat"] = _dmSeat,
            ["dm_player_idx"] = _dmSeat,
            ["your_seat"] = playerIdx,
            ["background"] = _background,
            ["background_questions"] = DnDData.BackgroundQuestions(),
            ["in_combat"] = _inCombat,
            ["races"] = DnDData.Races.ToList(),
            ["classes"] = DnDData.Classes.ToList(),
            ["monsters"] = monsterNames,
            ["players"] = players,
            ["enemies"] = enemiesArr,
            ["combat_log"] = _combatLog.TakeLast(10).ToList(),
            ["current_turn"] = currentTurn,
        };

        return new Dictionary<string, object?> { ["dnd"] = snap };
    }

    public override Dictionary<string, object?> GetPopupSnapshot(int playerIdx) =>
        new() { ["active"] = false };

    public override List<Dictionary<string, object?>> GetPanelButtons(int playerIdx)
    {
        if (!_buttons.TryGetValue(playerIdx, out var btns)) return new();
        return btns.Select(kv => new Dictionary<string, object?>
        {
            ["id"] = kv.Key,
            ["text"] = kv.Value.Text,
            ["enabled"] = kv.Value.Enabled,
        }).ToList();
    }

    // ── Update / Draw ──────────────────────────────────────────

    public override void Update(double dt)
    {
        float d = Math.Clamp((float)dt, 0f, 0.2f);
        _animTime += dt;
        _particles.Update(d);
        for (int i = _textPops.Count - 1; i >= 0; i--) { _textPops[i].Update(d); if (_textPops[i].Done) _textPops.RemoveAt(i); }
        for (int i = _flashes.Count - 1; i >= 0; i--) { _flashes[i].Update(d); if (_flashes[i].Done) _flashes.RemoveAt(i); }
        for (int i = _pulseRings.Count - 1; i >= 0; i--) { _pulseRings[i].Update(d); if (_pulseRings[i].Done) _pulseRings.RemoveAt(i); }
    }

    public override void Draw(Renderer r, int width, int height, double dt)
    {
        if (State == "player_select")
        {
            base.Draw(r, width, height, dt);
            return;
        }

        CardRendering.DrawGameBackground(r, width, height, "dnd");
        RainbowTitle.Draw(r, "D&D", width);

        string subtitle = _phase switch
        {
            "char_creation" => "Character Creation — use Web UI to create characters",
            "gameplay" => $"Adventure Mode — {_characters.Count} heroes" + (_dmSeat.HasValue ? $" — DM: {PlayerName(_dmSeat.Value)}" : ""),
            "combat" => $"Combat! Round {_combatManager.RoundNumber} — {_enemies.Count} enemies",
            _ => "Select players in Web UI",
        };
        r.DrawText(subtitle, 16, 50, 14, (200, 200, 200), anchorX: "left", anchorY: "top");

        // Draw combat log on screen
        if (_combatLog.Count > 0)
        {
            int logX = 16, logY = 80;
            int maxLines = Math.Min(8, _combatLog.Count);
            for (int i = 0; i < maxLines; i++)
            {
                int idx = _combatLog.Count - maxLines + i;
                float alpha = (float)(i + 1) / maxLines;
                var color = ((int)(200 * alpha), (int)(200 * alpha), (int)(200 * alpha));
                r.DrawText(_combatLog[idx], logX, logY + i * 20, 11, color, anchorX: "left", anchorY: "top");
            }
        }

        // Draw enemies in center area
        if (_enemies.Count > 0)
        {
            int ex = width / 2, ey = height / 2;
            for (int i = 0; i < _enemies.Count; i++)
            {
                var enemy = _enemies[i];
                int exi = ex + (i - _enemies.Count / 2) * 120;
                float hpPct = enemy.MaxHp > 0 ? (float)enemy.CurrentHp / enemy.MaxHp : 0;

                // Name
                r.DrawText(enemy.Name, exi, ey - 30, 14, (255, 100, 100), anchorX: "center", anchorY: "center");
                // HP bar
                int barW = 80, barH = 8;
                r.DrawRect((60, 20, 20), (exi - barW / 2, ey - 10, barW, barH));
                r.DrawRect((200, 50, 50), (exi - barW / 2, ey - 10, (int)(barW * hpPct), barH));
                // HP text
                r.DrawText($"{enemy.CurrentHp}/{enemy.MaxHp}", exi, ey + 5, 10, (200, 200, 200), anchorX: "center", anchorY: "center");
            }
        }

        // Draw characters summary
        int charY = height - 120;
        foreach (var kv in _characters)
        {
            int seat = kv.Key;
            var ch = kv.Value;
            var pc = GameConfig.PlayerColors[seat % GameConfig.PlayerColors.Length];
            int charX = 200 + ActivePlayers.IndexOf(seat) * 180;
            if (charX < 0) charX = 200;

            r.DrawText(ch.Name, charX, charY, 12, pc, anchorX: "center", anchorY: "center");
            r.DrawText($"{ch.Race} {ch.CharClass} Lv{ch.Level}", charX, charY + 16, 10, (180, 180, 180), anchorX: "center", anchorY: "center");

            float hpp = ch.MaxHp > 0 ? (float)ch.CurrentHp / ch.MaxHp : 0;
            var hpColor = hpp > 0.5 ? (50, 200, 50) : hpp > 0.25 ? (200, 200, 50) : (200, 50, 50);
            r.DrawRect((40, 20, 20), (charX - 40, charY + 30, 80, 6));
            r.DrawRect(hpColor, (charX - 40, charY + 30, (int)(80 * hpp), 6));
            r.DrawText($"{ch.CurrentHp}/{ch.MaxHp}", charX, charY + 44, 9, (200, 200, 200), anchorX: "center", anchorY: "center");
        }

        // Draw animations
        _particles.Draw(r);
        foreach (var pr in _pulseRings) pr.Draw(r);
        foreach (var tp in _textPops) tp.Draw(r);
        foreach (var fl in _flashes) fl.Draw(r, width, height);
    }
}
