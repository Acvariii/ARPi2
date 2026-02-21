using System;
using System.Collections.Generic;
using System.Linq;

namespace ARPi2.Sharp.Games.Monopoly;

/// <summary>Monopoly Property — mirrors Python models.py Property class.</summary>
public class Property
{
    public SpaceData Data { get; }
    public int Houses { get; set; }
    public bool IsMortgaged { get; set; }
    public int Owner { get; set; } = -1;  // -1 = unowned

    public Property(SpaceData data)
    {
        Data = data;
    }

    public int GetRent(int? diceRoll = null, int ownedInGroup = 1)
    {
        if (IsMortgaged) return 0;

        return Data.Type switch
        {
            "property" => Data.Rent != null && Houses < Data.Rent.Length ? Data.Rent[Houses] : 0,
            "railroad" => Data.Rent != null ? Data.Rent[Math.Min(ownedInGroup - 1, Data.Rent.Length - 1)] : 25,
            "utility"  => (diceRoll ?? 0) * (ownedInGroup == 1 ? 4 : 10),
            _ => 0
        };
    }

    public bool CanBuildHouse(bool hasMonopoly, List<Property> groupProps)
    {
        if (!hasMonopoly || IsMortgaged) return false;
        if (Houses >= 5) return false;
        return !groupProps.Any(p => p.Houses < Houses);
    }

    public bool CanSellHouse() => Houses > 0 && !IsMortgaged;

    public int Mortgage()
    {
        if (IsMortgaged || Houses > 0) return 0;
        IsMortgaged = true;
        return Data.MortgageValue;
    }

    public bool Unmortgage(int playerMoney)
    {
        if (!IsMortgaged) return false;
        int cost = (int)(Data.MortgageValue * 1.1);
        if (playerMoney < cost) return false;
        IsMortgaged = false;
        return true;
    }
}

/// <summary>Monopoly Player — mirrors Python models.py Player class.</summary>
public class MonopolyPlayer
{
    public int Idx { get; }
    public (int R, int G, int B) Color { get; }
    public int Money { get; set; }
    public int Position { get; set; }
    public List<int> Properties { get; set; } = new();
    public bool InJail { get; set; }
    public int JailTurns { get; set; }
    public int GetOutOfJailCards { get; set; }
    public int ConsecutiveDoubles { get; set; }
    public bool IsBankrupt { get; set; }

    // Animation state
    public List<int> MovePath { get; set; } = new();
    public double MoveStart { get; set; }
    public int MoveFrom { get; set; }
    public bool IsMoving { get; set; }

    public MonopolyPlayer(int idx, (int R, int G, int B) color)
    {
        Idx = idx;
        Color = color;
        Money = MonopolyData.StartingMoney;
    }

    public void AddMoney(int amount) => Money += amount;

    public bool RemoveMoney(int amount)
    {
        if (Money < amount) return false;
        Money -= amount;
        return true;
    }

    public List<int> GetPropertiesInGroup(string group, List<Property> allProps) =>
        Properties.Where(idx => idx >= 0 && idx < allProps.Count && allProps[idx].Data.Group == group).ToList();

    public bool HasMonopoly(string group, List<Property> allProps)
    {
        int owned = GetPropertiesInGroup(group, allProps).Count;
        if (!MonopolyData.PropertyGroups.TryGetValue(group, out var positions)) return false;
        return owned == positions.Length;
    }

    public int GetTotalHouses(List<Property> allProps) =>
        Properties.Where(i => i >= 0 && i < allProps.Count && allProps[i].Houses is > 0 and < 5).Sum(i => allProps[i].Houses);

    public int GetTotalHotels(List<Property> allProps) =>
        Properties.Count(i => i >= 0 && i < allProps.Count && allProps[i].Houses == 5);
}
