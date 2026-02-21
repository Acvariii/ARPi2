using System;
using System.Collections.Generic;

namespace ARPi2.Sharp.Games.Monopoly;

// ═══════════════════════════════════════════════════════════════════════════
//  Top-level domain types
// ═══════════════════════════════════════════════════════════════════════════

/// <summary>One of the 40 board positions.</summary>
public class SpaceData
{
    public string Name      { get; init; } = "";
    public string Type      { get; init; } = "";  // go, property, railroad, utility, chance, community_chest, income_tax, luxury_tax, jail, go_to_jail, free_parking
    public int    Position   { get; init; }
    public int    Price      { get; init; }
    public int[]? Rent       { get; init; }         // property: [base,1h,2h,3h,4h,hotel]  railroad: [1,2,3,4 owned]
    public int    HouseCost  { get; init; }
    public int    MortgageValue { get; init; }
    public (int R, int G, int B) Color { get; init; }
    public string? Group     { get; init; }
}

/// <summary>Effect of a Chance / Community Chest card.</summary>
public class CardAction
{
    public string Type { get; init; } = "";      // money, jail_free, go_to_jail, advance, advance_relative, advance_nearest, collect_from_each, pay_each_player, pay_per_house_hotel
    public int    Amount { get; init; }
    public int    Target { get; init; }
    public bool   PassGo { get; init; }
    public string? Nearest { get; init; }         // "railroad" or "utility"
    public int    RepairHouse { get; init; }
    public int    RepairHotel { get; init; }
}

/// <summary>One Chance or Community Chest card.</summary>
public class CardData
{
    public string Id   { get; init; } = "";
    public string Text { get; init; } = "";
    public CardAction Action { get; init; } = new();
}

/// <summary>Complete American Monopoly board data — direct port of data.py.</summary>
public static class MonopolyData
{
    // ─── Constants ─────────────────────────────────────────────────
    public const int StartingMoney       = 1500;
    public const int PassingGoMoney      = 200;
    public const int LuxuryTax           = 100;
    public const int IncomeTax           = 200;
    public const int JailPosition        = 10;
    public const int GoToJailPosition    = 30;
    public const int JailFine            = 50;
    public const int MaxJailTurns        = 3;
    public const int MaxHousesPerProp    = 4;

    // ─── Property groups → board positions ─────────────────────────
    public static readonly Dictionary<string, int[]> PropertyGroups = new()
    {
        ["Brown"]      = [1, 3],
        ["Light Blue"] = [6, 8, 9],
        ["Pink"]       = [11, 13, 14],
        ["Orange"]     = [16, 18, 19],
        ["Red"]        = [21, 23, 24],
        ["Yellow"]     = [26, 27, 29],
        ["Green"]      = [31, 32, 34],
        ["Dark Blue"]  = [37, 39],
        ["Railroad"]   = [5, 15, 25, 35],
        ["Utility"]    = [12, 28],
    };

    // ─── Build the 40-space board ──────────────────────────────────
    public static Dictionary<int, SpaceData> BuildBoard()
    {
        var board = new Dictionary<int, SpaceData>();

        // Special spaces
        board[0]  = new() { Name = "GO",              Type = "go",              Position = 0 };
        board[2]  = new() { Name = "Community Chest",  Type = "community_chest", Position = 2 };
        board[4]  = new() { Name = "Income Tax",       Type = "income_tax",      Position = 4 };
        board[7]  = new() { Name = "Chance",            Type = "chance",          Position = 7 };
        board[10] = new() { Name = "Jail",              Type = "jail",            Position = 10 };
        board[17] = new() { Name = "Community Chest",  Type = "community_chest", Position = 17 };
        board[20] = new() { Name = "Free Parking",     Type = "free_parking",    Position = 20 };
        board[22] = new() { Name = "Chance",            Type = "chance",          Position = 22 };
        board[30] = new() { Name = "Go To Jail",        Type = "go_to_jail",      Position = 30 };
        board[33] = new() { Name = "Community Chest",  Type = "community_chest", Position = 33 };
        board[36] = new() { Name = "Chance",            Type = "chance",          Position = 36 };
        board[38] = new() { Name = "Luxury Tax",        Type = "luxury_tax",      Position = 38 };

        // Properties
        void AddProp(int pos, string name, int price, int[] rent, int hc, int mv, (int,int,int) col, string grp) =>
            board[pos] = new SpaceData { Name=name, Type="property", Position=pos, Price=price, Rent=rent, HouseCost=hc, MortgageValue=mv, Color=col, Group=grp };

        // Brown
        AddProp(1, "Mediterranean Avenue", 60, [2,10,30,90,160,250], 50, 30, (149,84,54), "Brown");
        AddProp(3, "Baltic Avenue",        60, [4,20,60,180,320,450], 50, 30, (149,84,54), "Brown");
        // Light Blue
        AddProp(6, "Oriental Avenue",     100, [6,30,90,270,400,550], 50, 50, (170,224,250), "Light Blue");
        AddProp(8, "Vermont Avenue",      100, [6,30,90,270,400,550], 50, 50, (170,224,250), "Light Blue");
        AddProp(9, "Connecticut Avenue",  120, [8,40,100,300,450,600], 50, 60, (170,224,250), "Light Blue");
        // Pink
        AddProp(11, "St. Charles Place", 140, [10,50,150,450,625,750], 100, 70, (217,58,150), "Pink");
        AddProp(13, "States Avenue",     140, [10,50,150,450,625,750], 100, 70, (217,58,150), "Pink");
        AddProp(14, "Virginia Avenue",   160, [12,60,180,500,700,900], 100, 80, (217,58,150), "Pink");
        // Orange
        AddProp(16, "St. James Place",   180, [14,70,200,550,750,950], 100, 90, (247,148,29), "Orange");
        AddProp(18, "Tennessee Avenue",  180, [14,70,200,550,750,950], 100, 90, (247,148,29), "Orange");
        AddProp(19, "New York Avenue",   200, [16,80,220,600,800,1000], 100, 100, (247,148,29), "Orange");
        // Red
        AddProp(21, "Kentucky Avenue",   220, [18,90,250,700,875,1050], 150, 110, (237,27,36), "Red");
        AddProp(23, "Indiana Avenue",    220, [18,90,250,700,875,1050], 150, 110, (237,27,36), "Red");
        AddProp(24, "Illinois Avenue",   240, [20,100,300,750,925,1100], 150, 120, (237,27,36), "Red");
        // Yellow
        AddProp(26, "Atlantic Avenue",   260, [22,110,330,800,975,1150], 150, 130, (254,242,0), "Yellow");
        AddProp(27, "Ventnor Avenue",    260, [22,110,330,800,975,1150], 150, 130, (254,242,0), "Yellow");
        AddProp(29, "Marvin Gardens",    280, [24,120,360,850,1025,1200], 150, 140, (254,242,0), "Yellow");
        // Green
        AddProp(31, "Pacific Avenue",    300, [26,130,390,900,1100,1275], 200, 150, (31,178,90), "Green");
        AddProp(32, "North Carolina Ave",300, [26,130,390,900,1100,1275], 200, 150, (31,178,90), "Green");
        AddProp(34, "Pennsylvania Ave",  320, [28,150,450,1000,1200,1400], 200, 160, (31,178,90), "Green");
        // Dark Blue
        AddProp(37, "Park Place",        350, [35,175,500,1100,1300,1500], 200, 175, (0,114,187), "Dark Blue");
        AddProp(39, "Boardwalk",         400, [50,200,600,1400,1700,2000], 200, 200, (0,114,187), "Dark Blue");

        // Railroads
        void AddRR(int pos, string name) =>
            board[pos] = new SpaceData { Name=name, Type="railroad", Position=pos, Price=200, Rent=new[]{25,50,100,200}, MortgageValue=100, Color=(0,0,0), Group="Railroad" };
        AddRR(5, "Reading Railroad");
        AddRR(15, "Pennsylvania Railroad");
        AddRR(25, "B. & O. Railroad");
        AddRR(35, "Short Line");

        // Utilities
        void AddUtil(int pos, string name) =>
            board[pos] = new SpaceData { Name=name, Type="utility", Position=pos, Price=150, MortgageValue=75, Color=(200,200,200), Group="Utility" };
        AddUtil(12, "Electric Company");
        AddUtil(28, "Water Works");

        return board;
    }

    // ─── Community Chest cards ─────────────────────────────────────
    public static List<CardData> GetCommunityChestCards() => new()
    {
        new() { Id="cc_collect_100", Text="You set aside time to hang out with your neighbor. COLLECT $100.", Action=new() { Type="money", Amount=100 } },
        new() { Id="cc_collect_50",  Text="You clean up your town's footpaths. COLLECT $50.", Action=new() { Type="money", Amount=50 } },
        new() { Id="cc_collect_10",  Text="You volunteered at a blood donation. COLLECT $10.", Action=new() { Type="money", Amount=10 } },
        new() { Id="cc_pay_50",      Text="You buy cookies from a school bake sale. PAY $50.", Action=new() { Type="money", Amount=-50 } },
        new() { Id="cc_getout",      Text="GET OUT OF JAIL FREE.", Action=new() { Type="jail_free", Amount=1 } },
        new() { Id="cc_collect_10e", Text="You organize a street party. COLLECT $10 FROM EACH.", Action=new() { Type="collect_from_each", Amount=10 } },
        new() { Id="cc_go_to_jail",  Text="GO TO JAIL. DO NOT PASS GO.", Action=new() { Type="go_to_jail" } },
        new() { Id="cc_collect_20",  Text="You help your neighbor. COLLECT $20.", Action=new() { Type="money", Amount=20 } },
        new() { Id="cc_collect_100b",Text="You help build a playground. COLLECT $100.", Action=new() { Type="money", Amount=100 } },
        new() { Id="cc_collect_100c",Text="You play games with kids at hospital. COLLECT $100.", Action=new() { Type="money", Amount=100 } },
        new() { Id="cc_pay_100",     Text="Car wash fundraiser. PAY $100.", Action=new() { Type="money", Amount=-100 } },
        new() { Id="cc_advance_go",  Text="ADVANCE TO GO. (COLLECT $200)", Action=new() { Type="advance", Target=0, PassGo=true } },
        new() { Id="cc_collect_200", Text="You help clean up after a storm. COLLECT $200.", Action=new() { Type="money", Amount=200 } },
        new() { Id="cc_pay_50b",     Text="Donation to animal shelter. PAY $50.", Action=new() { Type="money", Amount=-50 } },
        new() { Id="cc_repairs",     Text="For each house pay $40. For each hotel pay $115.", Action=new() { Type="pay_per_house_hotel", RepairHouse=40, RepairHotel=115 } },
        new() { Id="cc_collect_25",  Text="You organize a bake sale. COLLECT $25.", Action=new() { Type="money", Amount=25 } },
    };

    // ─── Chance cards ──────────────────────────────────────────────
    public static List<CardData> GetChanceCards() => new()
    {
        new() { Id="ch_boardwalk",  Text="Advance to Boardwalk.", Action=new() { Type="advance", Target=39 } },
        new() { Id="ch_go",         Text="Advance to Go (Collect $200).", Action=new() { Type="advance", Target=0, PassGo=true } },
        new() { Id="ch_illinois",   Text="Advance to Illinois Avenue.", Action=new() { Type="advance", Target=24, PassGo=true } },
        new() { Id="ch_st_charles", Text="Advance to St. Charles Place.", Action=new() { Type="advance", Target=11, PassGo=true } },
        new() { Id="ch_near_rr",    Text="Advance to the nearest Railroad.", Action=new() { Type="advance_nearest", Nearest="railroad" } },
        new() { Id="ch_near_rr_b",  Text="Advance to the nearest Railroad.", Action=new() { Type="advance_nearest", Nearest="railroad" } },
        new() { Id="ch_near_util",  Text="Advance to nearest Utility.", Action=new() { Type="advance_nearest", Nearest="utility" } },
        new() { Id="ch_dividend",   Text="Bank pays you dividend of $50.", Action=new() { Type="money", Amount=50 } },
        new() { Id="ch_getout",     Text="Get Out of Jail Free.", Action=new() { Type="jail_free", Amount=1 } },
        new() { Id="ch_back_3",     Text="Go Back 3 Spaces.", Action=new() { Type="advance_relative", Amount=-3 } },
        new() { Id="ch_go_to_jail", Text="Go to Jail. Do not pass Go.", Action=new() { Type="go_to_jail" } },
        new() { Id="ch_repairs",    Text="For each house pay $25. For each hotel pay $100.", Action=new() { Type="pay_per_house_hotel", RepairHouse=25, RepairHotel=100 } },
        new() { Id="ch_speeding",   Text="Speeding fine $15.", Action=new() { Type="money", Amount=-15 } },
        new() { Id="ch_reading",    Text="Advance to Reading Railroad.", Action=new() { Type="advance", Target=5, PassGo=true } },
        new() { Id="ch_chairman",   Text="Pay each player $50.", Action=new() { Type="pay_each_player", Amount=50 } },
        new() { Id="ch_loan",       Text="Collect $150.", Action=new() { Type="money", Amount=150 } },
    };
}
