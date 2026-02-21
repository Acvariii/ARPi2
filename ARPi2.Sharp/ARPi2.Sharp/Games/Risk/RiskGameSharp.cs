using System;
using System.Collections.Generic;
using System.Linq;
using ARPi2.Sharp.Core;
using Microsoft.Xna.Framework;
using Microsoft.Xna.Framework.Graphics;

namespace ARPi2.Sharp.Games.Risk;

// ════════════════════════════════════════════════════════════════
//  Data types
// ════════════════════════════════════════════════════════════════

/// <summary>Definition of a territory on the map.</summary>
public class TerritoryDef
{
    public int Tid { get; }
    public string Name { get; }
    public string Continent { get; }
    public (int X, int Y) Seed { get; }

    public TerritoryDef(int tid, string name, string continent, (int, int) seed)
    {
        Tid = tid;
        Name = name;
        Continent = continent;
        Seed = seed;
    }
}

// ════════════════════════════════════════════════════════════════
//  RiskGameSharp — full port from Python
// ════════════════════════════════════════════════════════════════
public class RiskGameSharp : BaseGame
{
    public override string ThemeName => "risk";

    // ── Map & territories ──────────────────────────────────────
    private List<TerritoryDef> _territories = new();
    private Dictionary<int, List<int>> _adj = new();
    private Dictionary<string, int> _continentBonus = new();

    // Ownership & troops
    private Dictionary<int, int> _owner = new();      // tid -> seat
    private Dictionary<int, int> _troops = new();     // tid -> count

    // Turn state
    private List<int> _eliminatedPlayers = new();
    private int? _currentTurnSeat;
    private string _phase = "reinforce"; // initial_deploy | reinforce | attack | defend_choose | conquer_move | fortify
    private int _reinforcementsLeft;

    // Initial deployment
    private Dictionary<int, int> _initialDeployPools = new();
    private Dictionary<int, int?> _deploySelected = new();

    // Selection
    private int? _selectedFrom;
    private int? _selectedTo;

    // Attack dice
    private int _attackDiceChoice = 3;
    private int? _defendDiceChoice;

    // Defender choice flow
    private Dictionary<string, object?>? _pendingAttack;
    private int? _defendPendingSeat;

    // Conquest move-in
    private int? _conquerFrom;
    private int? _conquerTo;
    private int _conquerMoveChoice = 1;

    // Fortify
    private int _fortifyMovesLeft = 2;
    private (int A, int B)? _fortifyLock;

    // Missions
    private Dictionary<int, Dictionary<string, object?>> _missionBySeat = new();

    // Winner
    private int? _winner;

    // Event logging
    private string _lastEvent = "";
    private double _lastEventAge = 999.0;

    // Last attack roll (for display)
    private (List<int> ARoll, List<int> DRoll, int ALoss, int DLoss)? _lastAttackRoll;

    // Buttons per player
    private readonly Dictionary<int, Dictionary<string, (string Text, bool Enabled)>> _buttons = new();

    // Animations
    private readonly ParticleSystem _particles = new();
    private readonly List<TextPopAnim> _textPops = new();
    private readonly List<PulseRing> _pulseRings = new();
    private readonly List<ScreenFlash> _flashes = new();
    private readonly DiceRollAnimation _attackDice = new(dieSize: 48, gap: 10, rollDuration: 1.0f, showDuration: 2.5f);
    private readonly DiceRollAnimation _defendDice = new(dieSize: 48, gap: 10, rollDuration: 1.0f, showDuration: 2.5f);
    private int? _animPrevWinner;
    private double _animFwTimer;
    private double _totalElapsed;

    // ── World-map rendering ────────────────────────────────────
    private const int MapW = 640, MapH = 360;
    private int[,]? _tidMap;           // tid at each pixel (-1 = ocean/uninhabited)
    private bool[,]? _landMask;        // is land
    private Dictionary<int, (int X, int Y)>? _tidCenter; // label position per territory
    private Texture2D? _baseMapTex;    // static land/ocean/borders texture
    private Texture2D? _fillOverlayTex; // semi-transparent owner-color overlay
    private Dictionary<int, int>? _prevOwnerSnapshot; // to detect changes
    private bool _mapBuilt;

    // ── Constructor ────────────────────────────────────────────
    public RiskGameSharp(int w, int h, Renderer renderer) : base(w, h, renderer)
    {
        EnsureMap();
    }

    // ── Helpers ────────────────────────────────────────────────
    private static int Clamp(int v, int lo, int hi) => v < lo ? lo : v > hi ? hi : v;

    private void ShuffleList<T>(List<T> list)
    {
        for (int i = list.Count - 1; i > 0; i--)
        {
            int j = Rng.Next(i + 1);
            (list[i], list[j]) = (list[j], list[i]);
        }
    }

    private string SeatLabel(int? seat)
    {
        if (seat is not int s) return "—";
        return PlayerName(s);
    }

    private string TidName(int tid)
    {
        foreach (var td in _territories)
            if (td.Tid == tid) return td.Name;
        return $"T{tid}";
    }

    private List<int> AlivePlayers()
    {
        return ActivePlayers.Where(s => !_eliminatedPlayers.Contains(s)).ToList();
    }

    private bool IsMyTurn(int seat) => _currentTurnSeat is int t && seat == t;

    private void NoteEvent(string text)
    {
        _lastEvent = text;
        _lastEventAge = 0.0;
    }

    // ── Map definition (territories + adjacency) ──────────────
    private (int X, int Y) LonLatToMapXY(double lon, double lat)
    {
        // We don't have a big pixel map in C#; just use a simple mapping for territory positions.
        // Map lon [-180,180] lat [-90,90] to a grid.
        const int w = 1920, h = 1080;
        lat = Math.Max(-89.9999, Math.Min(89.9999, lat));
        while (lon < -180.0) lon += 360.0;
        while (lon >= 180.0) lon -= 360.0;
        int x = (int)((lon + 180.0) / 360.0 * (w - 1));
        int yTop = (int)((90.0 - lat) / 180.0 * (h - 1));
        int y = (h - 1) - yTop;
        return (Clamp(x, 0, w - 1), Clamp(y, 0, h - 1));
    }

    private void EnsureMap()
    {
        if (_territories.Count > 0) return;

        int tid = 0;
        var t = new List<TerritoryDef>();

        void AddLL(string name, string continent, double lon, double lat)
        {
            var seed = LonLatToMapXY(lon, lat);
            t.Add(new TerritoryDef(tid, name, continent, seed));
            tid++;
        }

        // --- North America (9) ---
        AddLL("Alaska", "North America", -150, 64);
        AddLL("NW Territory", "North America", -115, 64);
        AddLL("Greenland", "North America", -42, 72);
        AddLL("Alberta", "North America", -113, 54);
        AddLL("Ontario", "North America", -85, 50);
        AddLL("Quebec", "North America", -71, 52);
        AddLL("Western US", "North America", -118, 39);
        AddLL("Eastern US", "North America", -82, 38);
        AddLL("Central America", "North America", -90, 15);

        // --- South America (4) ---
        AddLL("Venezuela", "South America", -66, 7);
        AddLL("Peru", "South America", -75, -10);
        AddLL("Brazil", "South America", -52, -10);
        AddLL("Argentina", "South America", -64, -38);

        // --- Europe (7) ---
        AddLL("Iceland", "Europe", -18, 65);
        AddLL("Great Britain", "Europe", -2, 54);
        AddLL("Scandinavia", "Europe", 16, 63);
        AddLL("Northern Europe", "Europe", 16, 52);
        AddLL("Western Europe", "Europe", 2, 46);
        AddLL("Southern Europe", "Europe", 18, 41);
        AddLL("Ukraine", "Europe", 32, 49);

        // --- Africa (6) ---
        AddLL("North Africa", "Africa", 2, 28);
        AddLL("Egypt", "Africa", 30, 27);
        AddLL("East Africa", "Africa", 38, 0);
        AddLL("Congo", "Africa", 18, -2);
        AddLL("South Africa", "Africa", 24, -29);
        AddLL("Madagascar", "Africa", 47, -19);

        // --- Asia (12) ---
        AddLL("Ural", "Asia", 60, 58);
        AddLL("Siberia", "Asia", 100, 62);
        AddLL("Yakutsk", "Asia", 130, 62);
        AddLL("Kamchatka", "Asia", 160, 58);
        AddLL("Japan", "Asia", 138, 37);
        AddLL("Afghanistan", "Asia", 66, 33);
        AddLL("Middle East", "Asia", 45, 29);
        AddLL("India", "Asia", 78, 21);
        AddLL("China", "Asia", 105, 34);
        AddLL("SE Asia", "Asia", 105, 12);
        AddLL("Irkutsk", "Asia", 105, 52);
        AddLL("Mongolia", "Asia", 104, 46);

        // --- Australia (4) ---
        AddLL("Indonesia", "Australia", 113, -2);
        AddLL("New Guinea", "Australia", 145, -6);
        AddLL("Western Australia", "Australia", 121, -25);
        AddLL("Eastern Australia", "Australia", 149, -27);

        _territories = t;

        _continentBonus = new Dictionary<string, int>
        {
            ["North America"] = 5,
            ["South America"] = 2,
            ["Europe"] = 5,
            ["Africa"] = 3,
            ["Asia"] = 7,
            ["Australia"] = 2,
        };

        // Build adjacency from classic Risk links.
        BuildClassicAdjacency();
    }

    private void BuildClassicAdjacency()
    {
        var nameToTid = new Dictionary<string, int>();
        foreach (var td in _territories)
            nameToTid[td.Name] = td.Tid;

        var adjSets = new Dictionary<int, HashSet<int>>();
        foreach (var td in _territories)
            adjSets[td.Tid] = new HashSet<int>();

        void Link(string a, string b)
        {
            if (nameToTid.TryGetValue(a, out int ta) && nameToTid.TryGetValue(b, out int tb))
            {
                adjSets[ta].Add(tb);
                adjSets[tb].Add(ta);
            }
        }

        // North America internal
        Link("Alaska", "NW Territory");
        Link("Alaska", "Alberta");
        Link("NW Territory", "Alberta");
        Link("NW Territory", "Ontario");
        Link("NW Territory", "Greenland");
        Link("Alberta", "Ontario");
        Link("Alberta", "Western US");
        Link("Ontario", "Quebec");
        Link("Ontario", "Western US");
        Link("Ontario", "Eastern US");
        Link("Ontario", "Greenland");
        Link("Quebec", "Greenland");
        Link("Quebec", "Eastern US");
        Link("Western US", "Eastern US");
        Link("Western US", "Central America");
        Link("Eastern US", "Central America");

        // South America internal
        Link("Venezuela", "Peru");
        Link("Venezuela", "Brazil");
        Link("Peru", "Brazil");
        Link("Peru", "Argentina");
        Link("Brazil", "Argentina");

        // Europe internal
        Link("Iceland", "Great Britain");
        Link("Iceland", "Scandinavia");
        Link("Great Britain", "Scandinavia");
        Link("Great Britain", "Northern Europe");
        Link("Great Britain", "Western Europe");
        Link("Scandinavia", "Northern Europe");
        Link("Scandinavia", "Ukraine");
        Link("Northern Europe", "Western Europe");
        Link("Northern Europe", "Southern Europe");
        Link("Northern Europe", "Ukraine");
        Link("Western Europe", "Southern Europe");
        Link("Southern Europe", "Ukraine");

        // Africa internal
        Link("North Africa", "Egypt");
        Link("North Africa", "East Africa");
        Link("North Africa", "Congo");
        Link("Egypt", "East Africa");
        Link("East Africa", "Congo");
        Link("East Africa", "South Africa");
        Link("East Africa", "Madagascar");
        Link("Congo", "South Africa");
        Link("South Africa", "Madagascar");

        // Asia internal
        Link("Ural", "Siberia");
        Link("Ural", "Afghanistan");
        Link("Ural", "China");
        Link("Siberia", "Yakutsk");
        Link("Siberia", "Irkutsk");
        Link("Siberia", "Mongolia");
        Link("Siberia", "China");
        Link("Yakutsk", "Kamchatka");
        Link("Yakutsk", "Irkutsk");
        Link("Kamchatka", "Irkutsk");
        Link("Kamchatka", "Mongolia");
        Link("Kamchatka", "Japan");
        Link("Irkutsk", "Mongolia");
        Link("Mongolia", "China");
        Link("Mongolia", "Japan");
        Link("Afghanistan", "China");
        Link("Afghanistan", "India");
        Link("China", "India");
        Link("China", "SE Asia");
        Link("India", "SE Asia");

        // Australia internal
        Link("Indonesia", "New Guinea");
        Link("Indonesia", "Western Australia");
        Link("New Guinea", "Western Australia");
        Link("New Guinea", "Eastern Australia");
        Link("Western Australia", "Eastern Australia");

        // Cross-continent links
        Link("Alaska", "Kamchatka");
        Link("Greenland", "Iceland");
        Link("Central America", "Venezuela");
        Link("Brazil", "North Africa");
        Link("Southern Europe", "Egypt");
        Link("Southern Europe", "North Africa");
        Link("Western Europe", "North Africa");
        Link("Ukraine", "Ural");
        Link("Ukraine", "Afghanistan");
        Link("Ukraine", "Middle East");
        Link("Middle East", "Egypt");
        Link("Middle East", "East Africa");
        Link("Middle East", "India");
        Link("Middle East", "Afghanistan");
        Link("Middle East", "Southern Europe");
        Link("Indonesia", "SE Asia");
        Link("New Guinea", "Eastern Australia");

        _adj = adjSets.ToDictionary(kv => kv.Key, kv => kv.Value.OrderBy(x => x).ToList());
    }

    // ── Game start ─────────────────────────────────────────────
    public override void StartGame(List<int> players)
    {
        var seats = players.Where(s => s >= 0 && s <= 7).Distinct().OrderBy(x => x).ToList();
        if (seats.Count < 2) return;

        ActivePlayers = seats;
        _eliminatedPlayers.Clear();
        _winner = null;
        _missionBySeat.Clear();
        _lastAttackRoll = null;
        _animPrevWinner = null;
        _animFwTimer = 0;

        // Randomly assign territories evenly.
        var tids = _territories.Select(td => td.Tid).ToList();
        ShuffleList(tids);
        _owner.Clear();
        _troops.Clear();
        for (int i = 0; i < tids.Count; i++)
        {
            int seat = seats[i % seats.Count];
            _owner[tids[i]] = seat;
            _troops[tids[i]] = 1;
        }

        AssignMissions();

        // Initial deployment pools.
        _initialDeployPools.Clear();
        foreach (var s in seats)
        {
            int total = InitialArmiesForPlayerCount(seats.Count);
            int ownedCnt = _territories.Count(td => _owner.GetValueOrDefault(td.Tid, -999) == s);
            _initialDeployPools[s] = Math.Max(0, total - ownedCnt);
        }

        _currentTurnSeat = null;
        _phase = "initial_deploy";
        _selectedFrom = null;
        _selectedTo = null;
        _reinforcementsLeft = 0;
        _deploySelected = seats.ToDictionary(s => s, _ => (int?)null);
        _fortifyMovesLeft = 2;
        _fortifyLock = null;
        _conquerFrom = null;
        _conquerTo = null;
        _conquerMoveChoice = 1;
        _pendingAttack = null;
        _defendPendingSeat = null;

        State = "playing";
        NoteEvent("Risk started");
        RefreshButtons();
    }

    private int InitialArmiesForPlayerCount(int n)
    {
        var table = new Dictionary<int, int>
        {
            [2] = 40, [3] = 35, [4] = 30, [5] = 25, [6] = 20, [7] = 15, [8] = 10
        };
        return table.GetValueOrDefault(n, Math.Max(10, 50 - 5 * Math.Max(2, n)));
    }

    // ── Missions ───────────────────────────────────────────────
    private void AssignMissions()
    {
        var seats = AlivePlayers();
        if (seats.Count == 0) return;

        var continentMissions = new List<Dictionary<string, object?>>
        {
            new() { ["type"] = "continents", ["continents"] = new List<string> { "North America", "Africa" } },
            new() { ["type"] = "continents", ["continents"] = new List<string> { "Europe", "South America" } },
            new() { ["type"] = "continents", ["continents"] = new List<string> { "Asia", "Australia" } },
            new() { ["type"] = "continents", ["continents"] = new List<string> { "Europe", "Africa" } },
        };
        var countMissions = new List<Dictionary<string, object?>>
        {
            new() { ["type"] = "territories", ["count"] = 18 },
            new() { ["type"] = "territories", ["count"] = 24 },
        };

        foreach (var s in seats)
        {
            var options = new List<Dictionary<string, object?>>();
            options.AddRange(continentMissions.Select(d => new Dictionary<string, object?>(d)));
            options.AddRange(countMissions.Select(d => new Dictionary<string, object?>(d)));

            var targets = seats.Where(t => t != s).ToList();
            if (targets.Count > 0)
                options.Add(new Dictionary<string, object?> { ["type"] = "eliminate", ["target"] = targets[Rng.Next(targets.Count)] });

            _missionBySeat[s] = options[Rng.Next(options.Count)];
        }
    }

    private string MissionText(int seat)
    {
        if (!_missionBySeat.TryGetValue(seat, out var m)) return "Mission: —";
        var type = m.GetValueOrDefault("type") as string ?? "";
        if (type == "continents")
        {
            var conts = m.GetValueOrDefault("continents") as List<string> ?? new();
            return conts.Count > 0 ? "Mission: Control " + string.Join(" + ", conts) : "Mission: Control continents";
        }
        if (type == "territories")
        {
            int n = m.GetValueOrDefault("count") is int c ? c : 0;
            return $"Mission: Control {n} territories";
        }
        if (type == "eliminate")
        {
            return m.GetValueOrDefault("target") is int tgt
                ? $"Mission: Eliminate {SeatLabel(tgt)}"
                : "Mission: Eliminate a player";
        }
        return "Mission: —";
    }

    private bool MissionSatisfied(int seat)
    {
        if (!_missionBySeat.TryGetValue(seat, out var m)) return false;
        var type = m.GetValueOrDefault("type") as string ?? "";

        if (type == "continents")
        {
            var conts = m.GetValueOrDefault("continents") as List<string> ?? new();
            if (conts.Count == 0) return false;
            var byCont = new Dictionary<string, List<int>>();
            foreach (var td in _territories)
            {
                if (!byCont.ContainsKey(td.Continent)) byCont[td.Continent] = new();
                byCont[td.Continent].Add(td.Tid);
            }
            foreach (var cont in conts)
            {
                if (!byCont.TryGetValue(cont, out var tids)) return false;
                if (!tids.All(tid => _owner.GetValueOrDefault(tid, -999) == seat)) return false;
            }
            return true;
        }

        if (type == "territories")
        {
            int need = m.GetValueOrDefault("count") is int c ? c : 0;
            int owned = _territories.Count(td => _owner.GetValueOrDefault(td.Tid, -999) == seat);
            return need > 0 && owned >= need;
        }

        if (type == "eliminate")
        {
            if (m.GetValueOrDefault("target") is not int tgt) return false;
            bool ownsAny = _territories.Any(td => _owner.GetValueOrDefault(td.Tid, -999) == tgt);
            return !ownsAny;
        }

        return false;
    }

    private void CheckMissionWins()
    {
        if (_winner != null) return;
        foreach (var s in AlivePlayers())
        {
            if (MissionSatisfied(s))
            {
                _winner = s;
                NoteEvent($"{SeatLabel(s)} completed their mission!");
                return;
            }
        }
    }

    // ── Reinforcements ─────────────────────────────────────────
    private int CalcReinforcements(int seat)
    {
        var owned = _territories.Where(td => _owner.GetValueOrDefault(td.Tid, -999) == seat).ToList();
        int @base = Math.Max(3, owned.Count / 3);

        int bonus = 0;
        var byCont = new Dictionary<string, List<int>>();
        foreach (var td in _territories)
        {
            if (!byCont.ContainsKey(td.Continent)) byCont[td.Continent] = new();
            byCont[td.Continent].Add(td.Tid);
        }
        foreach (var (cont, tids) in byCont)
        {
            if (tids.Count > 0 && tids.All(tid => _owner.GetValueOrDefault(tid, -999) == seat))
                bonus += _continentBonus.GetValueOrDefault(cont, 0);
        }

        return @base + bonus;
    }

    // ── Eliminations ───────────────────────────────────────────
    private void CheckEliminations()
    {
        var alive = AlivePlayers();
        foreach (var s in alive.ToList())
        {
            bool ownsAny = _territories.Any(td => _owner.GetValueOrDefault(td.Tid, -999) == s);
            if (!ownsAny && !_eliminatedPlayers.Contains(s))
            {
                _eliminatedPlayers.Add(s);
                NoteEvent($"{SeatLabel(s)} eliminated");

                // Elimination animation
                try
                {
                    var col = GameConfig.PlayerColors[s % GameConfig.PlayerColors.Length];
                    int cx = ScreenW / 2, cy = ScreenH / 2;
                    _flashes.Add(new ScreenFlash((180, 30, 30), 60, 0.6f));
                    _textPops.Add(new TextPopAnim($"💀 {SeatLabel(s)} ELIMINATED!", cx, cy - 50, col, fontSize: 30));
                    _pulseRings.Add(new PulseRing(cx, cy, col, maxRadius: 100, duration: 0.8f));
                    for (int fi = 0; fi < 4; fi++)
                        _particles.EmitFirework(cx + Rng.Next(-120, 121), cy + Rng.Next(-60, 61),
                            new[] { (col.R, col.G, col.B), (200, 60, 60), (255, 100, 50) });
                }
                catch { }
            }
        }

        alive = AlivePlayers();
        if (alive.Count == 1)
        {
            _winner = alive[0];
            NoteEvent($"{SeatLabel(_winner)} wins!");
        }

        CheckMissionWins();
    }

    // ── Initial deployment ─────────────────────────────────────
    private void MaybeFinishInitialDeploy()
    {
        if (_phase != "initial_deploy") return;
        if (_winner != null) return;

        var seats = AlivePlayers();
        if (seats.Count == 0) return;

        if (seats.Any(s => _initialDeployPools.GetValueOrDefault(s, 0) > 0))
            return;

        // Everyone done: begin normal turns.
        _phase = "reinforce";
        _currentTurnSeat = seats[0];
        _reinforcementsLeft = CalcReinforcements(_currentTurnSeat.Value);
        _selectedFrom = null;
        _selectedTo = null;
        _deploySelected = seats.ToDictionary(s => s, _ => (int?)null);
        NoteEvent($"Turn: {SeatLabel(_currentTurnSeat)}");
        RefreshButtons();
    }

    // ── Dice ───────────────────────────────────────────────────
    private List<int> RollDice(int n)
    {
        n = Clamp(n, 0, 3);
        var rolls = new List<int>(n);
        for (int i = 0; i < n; i++)
            rolls.Add(Rng.Next(1, 7));
        rolls.Sort((a, b) => b.CompareTo(a)); // descending
        return rolls;
    }

    // ── Attack resolution ──────────────────────────────────────
    private void ResolveAttackRound(int attackerSeat, int? defenderSeat, int aTid, int dTid, int aDice, int dDice)
    {
        var aRoll = RollDice(aDice);
        var dRoll = RollDice(dDice);

        int comps = Math.Min(aRoll.Count, dRoll.Count);
        int aLosses = 0, dLosses = 0;
        for (int i = 0; i < comps; i++)
        {
            if (aRoll[i] > dRoll[i])
                dLosses++;
            else
                aLosses++; // defender wins ties
        }

        int aTroops = _troops.GetValueOrDefault(aTid, 0);
        int dTroops = _troops.GetValueOrDefault(dTid, 0);
        _troops[aTid] = Math.Max(1, aTroops - aLosses);
        _troops[dTid] = Math.Max(0, dTroops - dLosses);

        _lastAttackRoll = (new List<int>(aRoll), new List<int>(dRoll), aLosses, dLosses);

        // Dice roll animations
        _attackDice.Start(aRoll.ToArray());
        _defendDice.Start(dRoll.ToArray());

        // Animations
        try
        {
            var col = GameConfig.PlayerColors[attackerSeat % GameConfig.PlayerColors.Length];
            int cx = ScreenW / 2, cy = ScreenH / 2;
            _pulseRings.Add(new PulseRing(cx, cy, col, maxRadius: 60, duration: 0.6f));
        }
        catch { /* ignore */ }

        // Conquest
        if (_troops.GetValueOrDefault(dTid, 0) <= 0)
        {
            int? prevOwner = _owner.GetValueOrDefault(dTid, -1);
            _owner[dTid] = attackerSeat;

            if (_troops.GetValueOrDefault(aTid, 0) <= 1)
            {
                _troops[aTid] = Math.Max(1, _troops.GetValueOrDefault(aTid, 0));
                _troops[dTid] = 1;
            }
            else
            {
                _troops[aTid] = _troops.GetValueOrDefault(aTid, 0) - 1;
                _troops[dTid] = 1;
            }

            _phase = "conquer_move";
            _conquerFrom = aTid;
            _conquerTo = dTid;
            _conquerMoveChoice = 1;
            NoteEvent($"{SeatLabel(attackerSeat)} conquered {TidName(dTid)} ({FormatRoll(aRoll)} vs {FormatRoll(dRoll)})");

            // Animations
            try
            {
                var col = GameConfig.PlayerColors[attackerSeat % GameConfig.PlayerColors.Length];
                int cx = ScreenW / 2, cy = ScreenH / 2;
                _textPops.Add(new TextPopAnim($"Conquered {TidName(dTid)}!", cx, cy - 50, col, fontSize: 24));
                _flashes.Add(new ScreenFlash(col, 40, 0.5f));
                _particles.EmitSparkle(cx, cy, col, 20);
            }
            catch { /* ignore */ }

            if (prevOwner is int po && po >= 0)
                CheckEliminations();
            CheckMissionWins();

            _selectedTo = null;
            return;
        }

        NoteEvent($"Attack: {FormatRoll(aRoll)} vs {FormatRoll(dRoll)} (A-{aLosses}, D-{dLosses})");
        CheckEliminations();
        CheckMissionWins();
    }

    private static string FormatRoll(List<int> roll) => "[" + string.Join(",", roll) + "]";

    // ── HandleClick (web UI) ───────────────────────────────────
    public override void HandleClick(int playerIdx, string buttonId)
    {
        if (State != "playing") return;

        // Game-specific messages via __msg__:
        if (buttonId.StartsWith("__msg__:"))
        {
            var parts = buttonId.Split(':', 3);
            if (parts.Length >= 3)
            {
                HandleMessage(playerIdx, parts[1], parts[2]);
            }
            return;
        }

        // Territory picks from UI list.
        if (buttonId.StartsWith("pick:"))
        {
            if (int.TryParse(buttonId.AsSpan(5), out int tid))
            {
                if (_territories.Any(td => td.Tid == tid))
                {
                    HandlePick(playerIdx, tid);
                    RefreshButtons();
                }
            }
            return;
        }

        if (buttonId == "add_troop")
            HandleAddTroop(playerIdx);
        else if (buttonId.StartsWith("deploy_"))
        {
            if (int.TryParse(buttonId.AsSpan(7), out int amt) && amt > 0)
                HandleInitialDeploy(playerIdx, amt);
        }
        else if (buttonId.StartsWith("remove_"))
        {
            if (int.TryParse(buttonId.AsSpan(7), out int amt) && amt > 0)
                HandleInitialDeployRemove(playerIdx, amt);
        }
        else if (buttonId == "to_attack")
        {
            if (IsMyTurn(playerIdx) && _phase == "reinforce" && _reinforcementsLeft <= 0)
            {
                _phase = "attack";
                _selectedTo = null;
            }
        }
        else if (buttonId == "attack_back")
        {
            if (IsMyTurn(playerIdx) && _phase == "attack")
            {
                _selectedFrom = null;
                _selectedTo = null;
                _attackDiceChoice = 3;
                _defendDiceChoice = null;
                _pendingAttack = null;
                _defendPendingSeat = null;
            }
        }
        else if (buttonId == "attack")
            HandleAttack(playerIdx);
        else if (buttonId.StartsWith("attack_dice_"))
        {
            if (IsMyTurn(playerIdx) && _phase == "attack")
            {
                if (int.TryParse(buttonId.AsSpan(12), out int n) && n >= 1 && n <= 3)
                    _attackDiceChoice = n;
            }
        }
        else if (buttonId.StartsWith("defend_dice_"))
        {
            if ((IsMyTurn(playerIdx) && _phase == "attack") ||
                (_phase == "defend_choose" && _defendPendingSeat is int ds && playerIdx == ds))
            {
                if (int.TryParse(buttonId.AsSpan(12), out int n) && n >= 1 && n <= 2)
                    _defendDiceChoice = n;
            }
        }
        else if (buttonId == "defend_confirm")
        {
            if (_phase == "defend_choose" && _defendPendingSeat is int dps && playerIdx == dps)
                HandleDefendConfirm(playerIdx);
        }
        else if (buttonId == "conquer_minus")
        {
            if (IsMyTurn(playerIdx) && _phase == "conquer_move")
                _conquerMoveChoice = Math.Max(1, _conquerMoveChoice - 1);
        }
        else if (buttonId == "conquer_plus")
        {
            if (IsMyTurn(playerIdx) && _phase == "conquer_move")
                _conquerMoveChoice++;
        }
        else if (buttonId == "conquer_all")
        {
            if (IsMyTurn(playerIdx) && _phase == "conquer_move" && _conquerFrom is int caF && _conquerTo is int caT)
            {
                int aT = _troops.GetValueOrDefault(caF, 0);
                int dT = _troops.GetValueOrDefault(caT, 0);
                _conquerMoveChoice = Math.Max(1, aT + dT - 1);
            }
        }
        else if (buttonId == "conquer_confirm")
        {
            if (IsMyTurn(playerIdx) && _phase == "conquer_move")
                HandleConquerConfirm(playerIdx);
        }
        else if (buttonId == "end_attack")
        {
            if (IsMyTurn(playerIdx) && _phase == "attack")
            {
                _phase = "fortify";
                _selectedTo = null;
                _fortifyMovesLeft = 2;
                _fortifyLock = null;
            }
        }
        else if (buttonId == "move_1")
            HandleFortifyMove(playerIdx);
        else if (buttonId == "fortify_clear")
        {
            if (IsMyTurn(playerIdx) && _phase == "fortify")
            {
                _selectedFrom = null;
                _selectedTo = null;
            }
        }
        else if (buttonId == "end_turn")
            HandleEndTurn(playerIdx);

        RefreshButtons();
    }

    // ── Handle territory pick ──────────────────────────────────
    private void HandlePick(int seat, int tid)
    {
        if (_phase == "initial_deploy")
        {
            if (_winner != null) return;
            if (_owner.GetValueOrDefault(tid, -999) != seat) return;
            _deploySelected[seat] = tid;
            NoteEvent($"{SeatLabel(seat)} selected {TidName(tid)}");
            return;
        }

        if (!IsMyTurn(seat)) return;
        if (_winner != null) return;

        if (_phase == "reinforce")
        {
            if (_owner.GetValueOrDefault(tid, -999) == seat)
            {
                _selectedFrom = tid;
                _selectedTo = null;
                NoteEvent($"{SeatLabel(seat)} selected {TidName(tid)}");
            }
        }
        else if (_phase == "attack")
        {
            if (_selectedFrom == null)
            {
                if (_owner.GetValueOrDefault(tid, -999) == seat && _troops.GetValueOrDefault(tid, 0) > 1)
                {
                    _selectedFrom = tid;
                    _selectedTo = null;
                    _attackDiceChoice = Math.Min(3, Math.Max(1, _troops.GetValueOrDefault(tid, 0) - 1));
                    _defendDiceChoice = null;
                    NoteEvent($"{SeatLabel(seat)} attacking from {TidName(tid)}");
                }
                return;
            }
            // If clicking another owned territory, switch attacker.
            if (_owner.GetValueOrDefault(tid, -999) == seat)
            {
                if (_troops.GetValueOrDefault(tid, 0) > 1)
                {
                    if (_selectedFrom == tid)
                    {
                        _selectedFrom = null;
                        _selectedTo = null;
                    }
                    else
                    {
                        _selectedFrom = tid;
                        _selectedTo = null;
                        _attackDiceChoice = Math.Min(3, Math.Max(1, _troops.GetValueOrDefault(tid, 0) - 1));
                        _defendDiceChoice = null;
                    }
                    NoteEvent($"{SeatLabel(seat)} attacking from {TidName(tid)}");
                }
                return;
            }
            // Otherwise, set defender if adjacent.
            if (_adj.GetValueOrDefault(_selectedFrom.Value)?.Contains(tid) == true)
            {
                _selectedTo = (_selectedTo == tid) ? null : tid;
                NoteEvent($"{SeatLabel(seat)} targeting {TidName(tid)}");
            }
        }
        else if (_phase == "conquer_move")
        {
            return; // ignore picks during conquest move-in
        }
        else if (_phase == "fortify")
        {
            if (_selectedFrom == null)
            {
                if (_owner.GetValueOrDefault(tid, -999) == seat && _troops.GetValueOrDefault(tid, 0) > 1)
                {
                    _selectedFrom = tid;
                    _selectedTo = null;
                    NoteEvent($"{SeatLabel(seat)} moving from {TidName(tid)}");
                }
                return;
            }
            // Set destination (must be owned and adjacent)
            if (_owner.GetValueOrDefault(tid, -999) == seat &&
                _adj.GetValueOrDefault(_selectedFrom.Value)?.Contains(tid) == true)
            {
                _selectedTo = (_selectedTo == tid) ? null : tid;
                NoteEvent($"{SeatLabel(seat)} moving to {TidName(tid)}");
            }
            // Clicking another source switches
            if (_owner.GetValueOrDefault(tid, -999) == seat &&
                _troops.GetValueOrDefault(tid, 0) > 1 && tid != _selectedTo)
            {
                if (_selectedFrom == tid)
                {
                    _selectedFrom = null;
                    _selectedTo = null;
                }
                else
                {
                    _selectedFrom = tid;
                    _selectedTo = null;
                }
                NoteEvent($"{SeatLabel(seat)} moving from {TidName(tid)}");
            }
        }
    }

    // ── Add troop (reinforce phase) ────────────────────────────
    private void HandleAddTroop(int seat)
    {
        if (!IsMyTurn(seat) || _winner != null || _phase != "reinforce") return;
        if (_reinforcementsLeft <= 0 || _selectedFrom == null) return;
        if (_owner.GetValueOrDefault(_selectedFrom.Value, -999) != seat) return;

        _troops[_selectedFrom.Value] = _troops.GetValueOrDefault(_selectedFrom.Value, 0) + 1;
        _reinforcementsLeft--;
        NoteEvent($"{SeatLabel(seat)} placed 1 troop");
    }

    // ── Initial deployment ─────────────────────────────────────
    private void HandleInitialDeploy(int seat, int amount)
    {
        if (_winner != null || _phase != "initial_deploy") return;
        if (!_deploySelected.TryGetValue(seat, out int? sel) || sel == null) return;
        if (_owner.GetValueOrDefault(sel.Value, -999) != seat) return;

        int left = _initialDeployPools.GetValueOrDefault(seat, 0);
        int amt = Clamp(amount, 1, left);
        if (amt <= 0) return;

        _troops[sel.Value] = _troops.GetValueOrDefault(sel.Value, 0) + amt;
        _initialDeployPools[seat] = left - amt;
        NoteEvent($"{SeatLabel(seat)} deployed {amt}");

        MaybeFinishInitialDeploy();
    }

    private void HandleInitialDeployRemove(int seat, int amount)
    {
        if (_winner != null || _phase != "initial_deploy") return;
        if (!_deploySelected.TryGetValue(seat, out int? sel) || sel == null) return;
        if (_owner.GetValueOrDefault(sel.Value, -999) != seat) return;

        int cur = _troops.GetValueOrDefault(sel.Value, 0);
        int removable = Math.Max(0, cur - 1); // don't remove the baseline 1
        if (removable <= 0) return;

        int amt = Clamp(amount, 1, removable);
        if (amt <= 0) return;

        _troops[sel.Value] = cur - amt;
        _initialDeployPools[seat] = _initialDeployPools.GetValueOrDefault(seat, 0) + amt;
        NoteEvent($"{SeatLabel(seat)} removed {amt}");
    }

    // ── Attack ─────────────────────────────────────────────────
    private void HandleAttack(int seat)
    {
        if (!IsMyTurn(seat) || _winner != null || _phase != "attack") return;
        if (_selectedFrom == null || _selectedTo == null) return;

        int aTid = _selectedFrom.Value;
        int dTid = _selectedTo.Value;
        if (_owner.GetValueOrDefault(aTid, -999) != seat) return;
        if (_owner.GetValueOrDefault(dTid, -999) == seat) return;
        if (_adj.GetValueOrDefault(aTid)?.Contains(dTid) != true) return;

        int aTroops = _troops.GetValueOrDefault(aTid, 0);
        int dTroops = _troops.GetValueOrDefault(dTid, 0);
        if (aTroops <= 1 || dTroops <= 0) return;

        int maxADice = Math.Min(3, aTroops - 1);
        int maxDDice = Math.Min(2, dTroops);
        if (maxADice <= 0 || maxDDice <= 0) return;

        int aDice = Clamp(_attackDiceChoice, 1, maxADice);
        int? defenderSeat = _owner.GetValueOrDefault(dTid, -1);

        // If defender is a human in-game seat with a choice (2+ troops), let them choose.
        if (defenderSeat is int ds && ds >= 0 && AlivePlayers().Contains(ds))
        {
            if (maxDDice >= 2)
            {
                _phase = "defend_choose";
                _defendPendingSeat = ds;
                _pendingAttack = new Dictionary<string, object?>
                {
                    ["attacker"] = seat,
                    ["a_tid"] = aTid,
                    ["d_tid"] = dTid,
                    ["a_dice"] = aDice,
                    ["max_d"] = maxDDice,
                };
                _defendDiceChoice = maxDDice;
                NoteEvent($"{SeatLabel(ds)}: choose defense dice");
                return;
            }
        }

        // Auto-resolve.
        ResolveAttackRound(seat, defenderSeat is int dd && dd >= 0 ? dd : null, aTid, dTid, aDice, maxDDice);
    }

    // ── Defend confirm ─────────────────────────────────────────
    private void HandleDefendConfirm(int seat)
    {
        if (_phase != "defend_choose" || _winner != null) return;
        if (_defendPendingSeat is not int dps || seat != dps) return;
        if (_pendingAttack == null) return;

        var pend = _pendingAttack;
        if (pend.GetValueOrDefault("attacker") is not int attacker) return;
        if (pend.GetValueOrDefault("a_tid") is not int aTid) return;
        if (pend.GetValueOrDefault("d_tid") is not int dTid) return;
        if (pend.GetValueOrDefault("a_dice") is not int aDiceVal) return;
        if (pend.GetValueOrDefault("max_d") is not int maxD) return;

        if (_owner.GetValueOrDefault(aTid, -999) != attacker) return;
        if (_owner.GetValueOrDefault(dTid, -999) != seat) return;
        if (_adj.GetValueOrDefault(aTid)?.Contains(dTid) != true) return;
        if (_troops.GetValueOrDefault(aTid, 0) <= 1) return;
        if (_troops.GetValueOrDefault(dTid, 0) <= 0) return;

        int dChoice = Clamp(_defendDiceChoice ?? maxD, 1, maxD);

        _phase = "attack";
        _pendingAttack = null;
        _defendPendingSeat = null;

        ResolveAttackRound(attacker, seat, aTid, dTid, aDiceVal, dChoice);
        RefreshButtons();
    }

    // ── Conquer confirm ────────────────────────────────────────
    private void HandleConquerConfirm(int seat)
    {
        if (!IsMyTurn(seat) || _winner != null || _phase != "conquer_move") return;
        if (_conquerFrom == null || _conquerTo == null) return;

        int aTid = _conquerFrom.Value;
        int dTid = _conquerTo.Value;
        if (_owner.GetValueOrDefault(dTid, -999) != seat) return;
        if (_owner.GetValueOrDefault(aTid, -999) != seat) return;

        int aTroops = _troops.GetValueOrDefault(aTid, 0);
        int dTroops = _troops.GetValueOrDefault(dTid, 0);

        int maxTotalIn = Math.Max(1, aTroops + dTroops - 1);
        int desiredTotalIn = Clamp(_conquerMoveChoice, 1, maxTotalIn);
        int additional = desiredTotalIn - dTroops;
        if (additional > 0)
        {
            additional = Math.Min(additional, Math.Max(0, aTroops - 1));
            _troops[aTid] = aTroops - additional;
            _troops[dTid] = dTroops + additional;
        }

        _phase = "attack";
        _selectedFrom = dTid; // continue attacks from conquered territory
        _selectedTo = null;
        _conquerFrom = null;
        _conquerTo = null;
        _conquerMoveChoice = 1;
        NoteEvent($"Moved troops into {TidName(dTid)}");
        RefreshButtons();
    }

    // ── Fortify ────────────────────────────────────────────────
    private void HandleFortifyMove(int seat)
    {
        if (!IsMyTurn(seat) || _winner != null || _phase != "fortify") return;
        if (_fortifyMovesLeft <= 0) return;
        if (_selectedFrom == null || _selectedTo == null) return;

        int aTid = _selectedFrom.Value;
        int bTid = _selectedTo.Value;
        if (_owner.GetValueOrDefault(aTid, -999) != seat || _owner.GetValueOrDefault(bTid, -999) != seat) return;
        if (_adj.GetValueOrDefault(aTid)?.Contains(bTid) != true) return;

        // Lock the fortify route after the first move.
        if (_fortifyLock is (int la, int lb))
        {
            if (aTid != la || bTid != lb) return;
        }
        else
        {
            _fortifyLock = (aTid, bTid);
        }

        int aTroops = _troops.GetValueOrDefault(aTid, 0);
        if (aTroops <= 1) return;

        _troops[aTid] = aTroops - 1;
        _troops[bTid] = _troops.GetValueOrDefault(bTid, 0) + 1;
        _fortifyMovesLeft--;
        NoteEvent($"{SeatLabel(seat)} fortified 1 troop");
    }

    // ── End turn ───────────────────────────────────────────────
    private void HandleEndTurn(int seat)
    {
        if (!IsMyTurn(seat) || _winner != null) return;

        var alive = AlivePlayers();
        if (alive.Count == 0) return;
        if (!alive.Contains(seat)) seat = alive[0];

        int i = alive.IndexOf(seat);
        int nxt = alive[(i + 1) % alive.Count];
        _currentTurnSeat = nxt;
        _phase = "reinforce";
        _selectedFrom = null;
        _selectedTo = null;
        _conquerFrom = null;
        _conquerTo = null;
        _conquerMoveChoice = 1;
        _pendingAttack = null;
        _defendPendingSeat = null;
        _fortifyMovesLeft = 2;
        _fortifyLock = null;
        _reinforcementsLeft = CalcReinforcements(nxt);
        _lastAttackRoll = null;
        NoteEvent($"Turn: {SeatLabel(nxt)}");
        RefreshButtons();
    }

    // ── Player quit ────────────────────────────────────────────
    public void HandlePlayerQuit(int seat)
    {
        if (State != "playing" || _winner != null) return;
        if (!ActivePlayers.Contains(seat)) return;

        bool wasTurn = _currentTurnSeat is int t && t == seat;
        var remaining = ActivePlayers.Where(x => x != seat).ToList();

        // Redistribute initial deploy pools if applicable.
        if (_phase == "initial_deploy")
        {
            int leftover = _initialDeployPools.GetValueOrDefault(seat, 0);
            _initialDeployPools.Remove(seat);
            if (remaining.Count > 0 && leftover > 0)
            {
                int share = leftover / remaining.Count;
                if (share > 0)
                    foreach (var r in remaining)
                        _initialDeployPools[r] = _initialDeployPools.GetValueOrDefault(r, 0) + share;
            }
        }

        // Reassign territories.
        var owned = _owner.Where(kv => kv.Value == seat).Select(kv => kv.Key).ToList();
        if (remaining.Count > 0 && owned.Count > 0)
        {
            ShuffleList(owned);
            for (int i = 0; i < owned.Count; i++)
                _owner[owned[i]] = remaining[i % remaining.Count];
        }

        ActivePlayers = remaining;
        _eliminatedPlayers.Remove(seat);

        if (remaining.Count == 0)
        {
            State = "player_select";
            _currentTurnSeat = null;
            NoteEvent("All players left");
            RefreshButtons();
            return;
        }

        CheckEliminations();
        CheckMissionWins();
        if (_winner != null) { RefreshButtons(); return; }

        if (wasTurn)
        {
            _currentTurnSeat = remaining[0];
            if (_phase == "initial_deploy")
            {
                _currentTurnSeat = null;
                MaybeFinishInitialDeploy();
            }
            else
            {
                _phase = "reinforce";
                _selectedFrom = null;
                _selectedTo = null;
                _reinforcementsLeft = CalcReinforcements(_currentTurnSeat!.Value);
                NoteEvent($"Turn: {SeatLabel(_currentTurnSeat)}");
            }
        }

        if (_phase == "defend_choose")
        {
            if (_currentTurnSeat != null) _phase = "reinforce";
            _pendingAttack = null;
            _defendPendingSeat = null;
        }

        NoteEvent($"{SeatLabel(seat)} quit");
        RefreshButtons();
    }

    // ── Buttons ────────────────────────────────────────────────
    private void RefreshButtons()
    {
        _buttons.Clear();
        for (int s = 0; s < 8; s++)
            _buttons[s] = new Dictionary<string, (string, bool)>();

        foreach (var seat in AlivePlayers())
        {
            if (_winner != null)
            {
                _buttons[seat]["end_turn"] = ("Game Over", false);
                continue;
            }

            // Parallel initial deploy: everyone can act.
            if (_phase == "initial_deploy")
            {
                int pool = _initialDeployPools.GetValueOrDefault(seat, 0);
                int? sel = _deploySelected.GetValueOrDefault(seat);
                bool canPlace = pool > 0 && sel != null && _owner.GetValueOrDefault(sel.Value, -999) == seat;
                bool canRemove = sel != null && _owner.GetValueOrDefault(sel!.Value, -999) == seat && _troops.GetValueOrDefault(sel.Value, 0) > 1;
                _buttons[seat]["deploy_1"] = ($"Deploy +1 ({pool})", canPlace && pool >= 1);
                _buttons[seat]["deploy_5"] = ("Deploy +5", canPlace && pool >= 5);
                _buttons[seat]["deploy_10"] = ("Deploy +10", canPlace && pool >= 10);
                _buttons[seat]["remove_1"] = ("Remove 1", canRemove);
                _buttons[seat]["remove_5"] = ("Remove 5", canRemove && _troops.GetValueOrDefault(sel!.Value, 0) >= 6);
                _buttons[seat]["remove_10"] = ("Remove 10", canRemove && _troops.GetValueOrDefault(sel!.Value, 0) >= 11);
                _buttons[seat]["end_turn"] = ("Deploying", false);
                continue;
            }

            // Defend-choose: defender acts regardless of whose "turn" it is.
            if (_phase == "defend_choose")
            {
                bool isDef = _defendPendingSeat is int dps2 && seat == dps2;
                int maxD2 = 1;
                if (_pendingAttack != null && _pendingAttack.GetValueOrDefault("max_d") is int mx)
                    maxD2 = Math.Max(1, Math.Min(2, mx));
                int dChoice2 = Clamp(_defendDiceChoice ?? maxD2, 1, maxD2);
                _buttons[seat]["defend_dice_1"] = ("D Dice: 1", isDef && maxD2 >= 1);
                _buttons[seat]["defend_dice_2"] = ("D Dice: 2", isDef && maxD2 >= 2);
                _buttons[seat]["defend_confirm"] = ($"Defend ({dChoice2})", isDef);
                if (!isDef)
                    _buttons[seat]["end_turn"] = ("Waiting for Defender", false);
                continue;
            }

            bool isTurn = IsMyTurn(seat);
            if (!isTurn)
            {
                _buttons[seat]["end_turn"] = ("Waiting", false);
                continue;
            }

            if (_phase == "reinforce")
            {
                bool canAdd = _reinforcementsLeft > 0
                    && _selectedFrom != null
                    && _owner.GetValueOrDefault(_selectedFrom.Value, -999) == seat;
                _buttons[seat]["add_troop"] = ($"Add Troop (+1) ({_reinforcementsLeft})", canAdd);
                _buttons[seat]["to_attack"] = ("To Attack", _reinforcementsLeft <= 0);
            }
            else if (_phase == "attack")
            {
                bool canAttack = _selectedFrom != null
                    && _selectedTo != null
                    && _owner.GetValueOrDefault(_selectedFrom.Value, -999) == seat
                    && _owner.GetValueOrDefault(_selectedTo.Value, -999) != seat
                    && (_adj.GetValueOrDefault(_selectedFrom.Value)?.Contains(_selectedTo.Value) == true)
                    && _troops.GetValueOrDefault(_selectedFrom.Value, 0) > 1;

                int maxA2 = 1, maxD3 = 1;
                if (_selectedFrom is int sf && _owner.GetValueOrDefault(sf, -999) == seat)
                    maxA2 = Math.Max(1, Math.Min(3, _troops.GetValueOrDefault(sf, 0) - 1));
                if (_selectedTo is int st && _owner.GetValueOrDefault(st, -999) != seat)
                    maxD3 = Math.Max(1, Math.Min(2, _troops.GetValueOrDefault(st, 0)));

                int aChoice = Clamp(_attackDiceChoice, 1, maxA2);
                int dChoice3 = _defendDiceChoice == null ? maxD3 : Clamp(_defendDiceChoice.Value, 1, maxD3);

                _buttons[seat]["attack_dice_1"] = ("A Dice: 1", maxA2 >= 1);
                _buttons[seat]["attack_dice_2"] = ("A Dice: 2", maxA2 >= 2);
                _buttons[seat]["attack_dice_3"] = ("A Dice: 3", maxA2 >= 3);
                _buttons[seat]["defend_dice_1"] = ("D Dice: 1", maxD3 >= 1);
                _buttons[seat]["defend_dice_2"] = ("D Dice: 2", maxD3 >= 2);
                _buttons[seat]["attack"] = ($"Attack ({aChoice}v{dChoice3})", canAttack);
                _buttons[seat]["attack_back"] = ("Change Attack From", true);
                _buttons[seat]["end_attack"] = ("End Attack", true);
            }
            else if (_phase == "conquer_move")
            {
                bool canConfirm = _conquerFrom is int cf2 && _conquerTo is int ct2
                    && _owner.GetValueOrDefault(ct2, -999) == seat;
                int maxTotalIn2 = 1;
                if (_conquerFrom is int cfv && _conquerTo is int ctv)
                {
                    int aT2 = _troops.GetValueOrDefault(cfv, 0);
                    int dT2 = _troops.GetValueOrDefault(ctv, 0);
                    maxTotalIn2 = Math.Max(1, aT2 + dT2 - 1);
                }
                int choice = Clamp(_conquerMoveChoice, 1, maxTotalIn2);
                _conquerMoveChoice = choice;
                _buttons[seat]["conquer_minus"] = ("Move -1", canConfirm && choice > 1);
                _buttons[seat]["conquer_plus"] = ("Move +1", canConfirm && choice < maxTotalIn2);
                _buttons[seat]["conquer_all"] = ("Move All", canConfirm && maxTotalIn2 > 1);
                _buttons[seat]["conquer_confirm"] = ($"Confirm Move ({choice})", canConfirm);
            }
            else if (_phase == "fortify")
            {
                bool canMove = _selectedFrom != null
                    && _selectedTo != null
                    && _owner.GetValueOrDefault(_selectedFrom.Value, -999) == seat
                    && _owner.GetValueOrDefault(_selectedTo.Value, -999) == seat
                    && (_adj.GetValueOrDefault(_selectedFrom.Value)?.Contains(_selectedTo.Value) == true)
                    && _troops.GetValueOrDefault(_selectedFrom.Value, 0) > 1
                    && _fortifyMovesLeft > 0;
                _buttons[seat]["move_1"] = ($"Move 1 ({_fortifyMovesLeft} left)", canMove);
                _buttons[seat]["fortify_clear"] = ("Clear Selection", true);
                _buttons[seat]["end_turn"] = ("End Turn", true);
            }
        }
    }

    // ── GetSnapshot (web UI state) ─────────────────────────────
    public override Dictionary<string, object?> GetSnapshot(int playerIdx)
    {
        var terr = _territories.Select(td => (Dictionary<string, object?>)new Dictionary<string, object?>
        {
            ["tid"] = td.Tid,
            ["name"] = td.Name,
            ["continent"] = td.Continent,
            ["owner"] = _owner.GetValueOrDefault(td.Tid, -1) >= 0 ? (object?)_owner[td.Tid] : null,
            ["troops"] = _troops.GetValueOrDefault(td.Tid, 0),
        }).ToList();

        // Attack filtering helpers
        var attackFromTids = new List<int>();
        var attackToTids = new List<int>();
        if (_phase == "attack" && AlivePlayers().Contains(playerIdx))
        {
            foreach (var td in _territories)
            {
                if (_owner.GetValueOrDefault(td.Tid, -999) != playerIdx) continue;
                if (_troops.GetValueOrDefault(td.Tid, 0) <= 1) continue;
                var neigh = _adj.GetValueOrDefault(td.Tid, new());
                if (neigh.Any(n => _owner.GetValueOrDefault(n, -999) != playerIdx))
                    attackFromTids.Add(td.Tid);
            }

            if (_selectedFrom is int sf2 && _owner.GetValueOrDefault(sf2, -999) == playerIdx)
            {
                if (_troops.GetValueOrDefault(sf2, 0) > 1)
                {
                    foreach (int n in _adj.GetValueOrDefault(sf2, new()))
                    {
                        if (_owner.GetValueOrDefault(n, -999) != playerIdx)
                            attackToTids.Add(n);
                    }
                }
            }
        }

        var snap = new Dictionary<string, object?>
        {
            ["state"] = State,
            ["active_players"] = AlivePlayers().Cast<object?>().ToList(),
            ["eliminated_players"] = _eliminatedPlayers.Cast<object?>().ToList(),
            ["current_turn_seat"] = _currentTurnSeat,
            ["phase"] = _phase,
            ["reinforcements_left"] = _reinforcementsLeft,
            ["initial_deploy_seat"] = (object?)null,
            ["initial_deploy_pool"] = _initialDeployPools.GetValueOrDefault(playerIdx, 0),
            ["your_mission"] = MissionText(playerIdx),
            ["attack_from_tids"] = attackFromTids.Cast<object?>().ToList(),
            ["attack_to_tids"] = attackToTids.Cast<object?>().ToList(),
            ["selected_from"] = _phase == "initial_deploy"
                ? (object?)_deploySelected.GetValueOrDefault(playerIdx)
                : (object?)_selectedFrom,
            ["selected_to"] = _phase == "initial_deploy" ? null : (object?)_selectedTo,
            ["winner"] = _winner,
            ["last_event"] = string.IsNullOrEmpty(_lastEvent) ? null : _lastEvent,
            ["territories"] = terr,
        };

        return new Dictionary<string, object?> { ["risk"] = snap };
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

    // ── Update ─────────────────────────────────────────────────
    public override void Update(double dt)
    {
        float d = Math.Clamp((float)dt, 0f, 0.2f);
        _totalElapsed += d;
        if (_lastEventAge < 999.0) _lastEventAge += d;

        _particles.Update(d);
        for (int i = _textPops.Count - 1; i >= 0; i--) { _textPops[i].Update(d); if (_textPops[i].Done) _textPops.RemoveAt(i); }
        for (int i = _pulseRings.Count - 1; i >= 0; i--) { _pulseRings[i].Update(d); if (_pulseRings[i].Done) _pulseRings.RemoveAt(i); }
        for (int i = _flashes.Count - 1; i >= 0; i--) { _flashes[i].Update(d); if (_flashes[i].Done) _flashes.RemoveAt(i); }
        _attackDice.Update((float)_totalElapsed);
        _defendDice.Update((float)_totalElapsed);

        // Winner fireworks
        if (_winner is int w && w != (_animPrevWinner ?? -1))
        {
            _animPrevWinner = w;
            int cx = ScreenW / 2, cy = ScreenH / 2;
            for (int i = 0; i < 10; i++)
                _particles.EmitFirework(cx + Rng.Next(-150, 151), cy + Rng.Next(-100, 101), AnimPalette.Rainbow);
            _flashes.Add(new ScreenFlash((255, 220, 80), 80, 1.2f));
            _textPops.Add(new TextPopAnim($"🏆 {SeatLabel(_winner)} wins!", cx, cy - 70, (255, 220, 80), fontSize: 40));
            _animFwTimer = 8.0;
        }
        if (_animFwTimer > 0)
        {
            _animFwTimer = Math.Max(0, _animFwTimer - d);
            if ((int)(_animFwTimer * 3) % 2 == 0)
            {
                int cx = ScreenW / 2, cy = ScreenH / 2;
                _particles.EmitFirework(cx + Rng.Next(-150, 151), cy + Rng.Next(-100, 101), AnimPalette.Rainbow);
            }
        }
    }

    // ── Draw ───────────────────────────────────────────────────
    public override void Draw(Renderer r, int width, int height, double dt)
    {
        if (State == "player_select")
        {
            base.Draw(r, width, height, dt);
            return;
        }

        CardRendering.DrawGameBackground(r, width, height, "risk");
        RainbowTitle.Draw(r, "RISK", width);

        int cx = width / 2;
        int pad = 10;

        // Status text
        if (_phase == "initial_deploy")
        {
            int poolSum = _initialDeployPools.Values.Sum();
            r.DrawText($"Initial Deploy: all players  ·  Unassigned total: {poolSum}",
                pad, 48, 14, (200, 200, 200), anchorX: "left", anchorY: "top");
        }
        else
        {
            string turn = SeatLabel(_currentTurnSeat);
            r.DrawText($"Turn: {turn}  ·  Phase: {_phase}  ·  Reinforcements: {_reinforcementsLeft}",
                pad, 48, 14, (200, 200, 200), anchorX: "left", anchorY: "top");
        }

        // Selected territory info
        if (_phase != "initial_deploy" && _selectedFrom is int sf)
        {
            r.DrawText($"Selected: {TidName(sf)}", pad, 68, 12, (210, 210, 210), anchorX: "left", anchorY: "top");
        }

        // Draw simplified territory map as a text-based grid
        DrawTerritoryMap(r, width, height);

        // Last attack roll display
        if (_lastAttackRoll is var (aRoll, dRoll, aL, dL))
        {
            string rollText = $"Last Roll: {FormatRoll(aRoll)} vs {FormatRoll(dRoll)} (A-{aL}, D-{dL})";
            r.DrawText(rollText, cx, height - 60, 14, (255, 220, 140), anchorX: "center", anchorY: "center");
        }

        // Winner overlay
        if (_winner is int w)
        {
            r.DrawRect((0, 0, 0), (0, 0, width, height), alpha: 150);
            int bw2 = Math.Min(600, width * 55 / 100), bh2 = 180;
            int bx2 = cx - bw2 / 2, by2 = height / 2 - bh2 / 2;
            r.DrawRect((10, 10, 18), (bx2, by2, bw2, bh2), alpha: 220);
            r.DrawRect((255, 215, 0), (bx2, by2, bw2, bh2), width: 4, alpha: 200);
            var wCol = GameConfig.PlayerColors[w % GameConfig.PlayerColors.Length];
            r.DrawText("🏆", cx, height / 2 + 30, 50, (255, 215, 0), anchorX: "center", anchorY: "center");
            r.DrawText($"{SeatLabel(w)} WINS!", cx, height / 2 - 24, 40, wCol, anchorX: "center", anchorY: "center");
            r.DrawText("Mission Complete", cx, height / 2 + 6, 18, wCol, anchorX: "center", anchorY: "center");
        }

        // Defend-choose banner
        if (_phase == "defend_choose" && _defendPendingSeat is int defSeat)
        {
            var dcol = GameConfig.PlayerColors[defSeat % GameConfig.PlayerColors.Length];
            int ow = 360, oh = 56;
            int ox = (width - ow) / 2, oy = height / 2 - oh / 2;
            r.DrawRect((10, 10, 18), (ox, oy, ow, oh), alpha: 225);
            r.DrawRect(dcol, (ox, oy, ow, oh), width: 3, alpha: 180);
            r.DrawText($"⚔️  {SeatLabel(defSeat)}: Choose Defense Dice",
                ox + ow / 2, oy + oh / 2, 16, dcol, anchorX: "center", anchorY: "center");
        }

        // Last event
        if (!string.IsNullOrEmpty(_lastEvent) && _lastEventAge < 6.0)
        {
            int ew = Math.Max(200, _lastEvent.Length * 8);
            r.DrawRect((0, 0, 0), (pad, height - 32, ew, 24), alpha: 140);
            r.DrawText(_lastEvent, pad + 8, height - 20, 12, (200, 200, 210), anchorX: "left", anchorY: "center");
        }

        // Animations
        _particles.Draw(r);
        foreach (var pr in _pulseRings) pr.Draw(r);
        foreach (var fl in _flashes) fl.Draw(r, width, height);
        foreach (var tp in _textPops) tp.Draw(r);

        // Attack dice
        if (_attackDice.Visible)
        {
            int dcy = height - 80;
            _attackDice.Draw(r, width / 2 - 80, dcy, "ATK");
            _defendDice.Draw(r, width / 2 + 80, dcy, "DEF");
        }
    }

    // ── World-map rasterization (ellipse-blob approach ported from Python) ──

    private void EnsureMapTextures(Renderer r)
    {
        if (_mapBuilt) return;
        _mapBuilt = true;
        RasterizeWorldMap();
        BuildBaseTexture(r);
    }

    private void RasterizeWorldMap()
    {
        int w = MapW, h = MapH;
        float sx = w / 320f, sy = h / 180f;
        float SX(float v) => v * sx;
        float SY(float v) => v * sy;

        // Continent masks
        var land = new bool[h, w];
        var contAt = new string?[h, w];

        void PaintEllipse(bool[,] mask, float cx, float cy, float rx, float ry, bool val = true)
        {
            if (rx <= 0 || ry <= 0) return;
            int x0 = Clamp((int)(cx - rx - 1), 0, w - 1);
            int x1 = Clamp((int)(cx + rx + 1), 0, w - 1);
            int y0 = Clamp((int)(cy - ry - 1), 0, h - 1);
            int y1 = Clamp((int)(cy + ry + 1), 0, h - 1);
            float invRx2 = 1f / (rx * rx);
            float invRy2 = 1f / (ry * ry);
            for (int yy = y0; yy <= y1; yy++)
                for (int xx = x0; xx <= x1; xx++)
                {
                    float dx = xx - cx, dy = yy - cy;
                    if (dx * dx * invRx2 + dy * dy * invRy2 <= 1f)
                        mask[yy, xx] = val;
                }
        }

        bool[,] Smooth(bool[,] mask, int iters)
        {
            var cur = mask;
            for (int _ = 0; _ < iters; _++)
            {
                var nxt = new bool[h, w];
                for (int yy = 0; yy < h; yy++)
                    for (int xx = 0; xx < w; xx++)
                    {
                        int cnt = 0;
                        for (int oy = -1; oy <= 1; oy++)
                            for (int ox = -1; ox <= 1; ox++)
                            {
                                int ny = yy + oy, nx = xx + ox;
                                if (ny >= 0 && ny < h && nx >= 0 && nx < w && cur[ny, nx]) cnt++;
                            }
                        nxt[yy, xx] = cnt >= 5;
                    }
                cur = nxt;
            }
            return cur;
        }

        // ── North America ──
        var mNA = new bool[h, w];
        PaintEllipse(mNA, SX(48), SY(150), SX(58), SY(34));
        PaintEllipse(mNA, SX(86), SY(154), SX(70), SY(36));
        PaintEllipse(mNA, SX(110), SY(136), SX(64), SY(34));
        PaintEllipse(mNA, SX(106), SY(112), SX(56), SY(28));
        PaintEllipse(mNA, SX(118), SY(92), SX(22), SY(18));
        PaintEllipse(mNA, SX(132), SY(92), SX(10), SY(12));
        PaintEllipse(mNA, SX(154), SY(164), SX(26), SY(14)); // Greenland
        PaintEllipse(mNA, SX(112), SY(142), SX(18), SY(12), false); // Hudson bay
        mNA = Smooth(mNA, 3);

        // ── South America ──
        var mSA = new bool[h, w];
        PaintEllipse(mSA, SX(148), SY(66), SX(28), SY(38));
        PaintEllipse(mSA, SX(150), SY(40), SX(22), SY(28));
        PaintEllipse(mSA, SX(142), SY(24), SX(18), SY(22));
        PaintEllipse(mSA, SX(162), SY(58), SX(16), SY(20));
        PaintEllipse(mSA, SX(160), SY(16), SX(12), SY(10), false);
        mSA = Smooth(mSA, 3);

        // ── Eurasia ──
        var mEU = new bool[h, w];
        PaintEllipse(mEU, SX(214), SY(140), SX(42), SY(20));
        PaintEllipse(mEU, SX(236), SY(146), SX(48), SY(22));
        PaintEllipse(mEU, SX(232), SY(160), SX(24), SY(18));
        PaintEllipse(mEU, SX(268), SY(142), SX(46), SY(24));
        PaintEllipse(mEU, SX(296), SY(136), SX(86), SY(54));
        PaintEllipse(mEU, SX(316), SY(162), SX(54), SY(28));
        PaintEllipse(mEU, SX(304), SY(108), SX(52), SY(26));
        PaintEllipse(mEU, SX(296), SY(92), SX(24), SY(18));
        PaintEllipse(mEU, SX(244), SY(112), SX(56), SY(12), false); // Med
        PaintEllipse(mEU, SX(262), SY(124), SX(14), SY(10), false); // Black Sea
        mEU = Smooth(mEU, 3);

        // ── Africa ──
        var mAF = new bool[h, w];
        PaintEllipse(mAF, SX(238), SY(88), SX(42), SY(30));
        PaintEllipse(mAF, SX(226), SY(64), SX(34), SY(34));
        PaintEllipse(mAF, SX(258), SY(66), SX(30), SY(40));
        PaintEllipse(mAF, SX(270), SY(66), SX(18), SY(22));
        PaintEllipse(mAF, SX(246), SY(30), SX(34), SY(26));
        PaintEllipse(mAF, SX(276), SY(28), SX(10), SY(12)); // Madagascar
        mAF = Smooth(mAF, 3);

        // ── Australia ──
        var mAU = new bool[h, w];
        PaintEllipse(mAU, SX(304), SY(34), SX(28), SY(18));
        PaintEllipse(mAU, SX(318), SY(32), SX(20), SY(16));
        PaintEllipse(mAU, SX(312), SY(60), SX(18), SY(12)); // New Guinea
        PaintEllipse(mAU, SX(292), SY(70), SX(18), SY(10)); // Indonesia
        PaintEllipse(mAU, SX(304), SY(72), SX(16), SY(10));
        mAU = Smooth(mAU, 2);

        // ── Islands (UK, Japan) ──
        var mIs = new bool[h, w];
        PaintEllipse(mIs, SX(200), SY(136), SX(10), SY(8));
        PaintEllipse(mIs, SX(304), SY(126), SX(12), SY(10));
        PaintEllipse(mIs, SX(312), SY(120), SX(10), SY(8));
        mIs = Smooth(mIs, 1);

        // ── Antarctica ──
        var mAnt = new bool[h, w];
        PaintEllipse(mAnt, SX(160), SY(6), SX(220), SY(8));
        PaintEllipse(mAnt, SX(240), SY(7), SX(240), SY(7));
        mAnt = Smooth(mAnt, 1);

        // Apply masks → land + continent assignment
        void ApplyMask(bool[,] mask, string? cont)
        {
            for (int yy = 0; yy < h; yy++)
                for (int xx = 0; xx < w; xx++)
                    if (mask[yy, xx] && !land[yy, xx])
                    {
                        land[yy, xx] = true;
                        contAt[yy, xx] = cont;
                    }
        }

        ApplyMask(mNA, "North America");
        ApplyMask(mSA, "South America");
        ApplyMask(mEU, "Eurasia");
        ApplyMask(mAF, "Africa");
        ApplyMask(mAU, "Australia");
        ApplyMask(mIs, "Eurasia");
        ApplyMask(mAnt, null); // land but no territories

        // Carve ocean gaps
        void CarveChannel(int x0c, int x1c, int y0c, int y1c)
        {
            x0c = Clamp(x0c, 0, w - 1); x1c = Clamp(x1c, 0, w - 1);
            y0c = Clamp(y0c, 0, h - 1); y1c = Clamp(y1c, 0, h - 1);
            if (x1c < x0c) (x0c, x1c) = (x1c, x0c);
            if (y1c < y0c) (y0c, y1c) = (y1c, y0c);
            for (int yy = y0c; yy <= y1c; yy++)
                for (int xx = x0c; xx <= x1c; xx++)
                {
                    land[yy, xx] = false;
                    contAt[yy, xx] = null;
                }
        }

        // Atlantic
        CarveChannel((int)SX(170), (int)SX(208), (int)SY(34), (int)SY(176));
        // Bering
        CarveChannel((int)SX(306), (int)SX(318), (int)SY(120), (int)SY(176));

        // Split Eurasia → Europe / Asia
        int euroSplit = (int)SX(252);
        for (int yy = 0; yy < h; yy++)
            for (int xx = 0; xx < w; xx++)
            {
                if (contAt[yy, xx] != "Eurasia") continue;
                contAt[yy, xx] = (xx < euroSplit && yy > (int)SY(98)) ? "Europe" : "Asia";
            }

        // Compute territory seed positions in map coordinates
        // The Python code puts y=0 at bottom; our map uses y=0 at top
        // (lon + 180) / 360 * w → x; (90 - lat) / 180 * h → y (top-down)
        var seedByTid = new Dictionary<int, (int X, int Y)>();
        var seedsByCont = new Dictionary<string, List<(int Tid, int X, int Y)>>();

        // Territory lon/lat positions (must match AddLL order)
        var territoryLonLat = new (double Lon, double Lat)[]
        {
            (-150, 64), (-115, 64), (-42, 72), (-113, 54), (-85, 50), (-71, 52),
            (-118, 39), (-82, 38), (-90, 15),
            (-66, 7), (-75, -10), (-52, -10), (-64, -38),
            (-18, 65), (-2, 54), (16, 63), (16, 52), (2, 46), (18, 41), (32, 49),
            (2, 28), (30, 27), (38, 0), (18, -2), (24, -29), (47, -19),
            (60, 58), (100, 62), (130, 62), (160, 58), (138, 37), (66, 33),
            (45, 29), (78, 21), (105, 34), (105, 12), (105, 52), (104, 46),
            (113, -2), (145, -6), (121, -25), (149, -27),
        };

        for (int i = 0; i < _territories.Count && i < territoryLonLat.Length; i++)
        {
            var (lon, lat) = territoryLonLat[i];
            int mx = Clamp((int)((lon + 180.0) / 360.0 * (w - 1)), 0, w - 1);
            int my = Clamp((int)((90.0 - lat) / 180.0 * (h - 1)), 0, h - 1);
            seedByTid[i] = (mx, my);

            string cont = _territories[i].Continent;
            if (!seedsByCont.ContainsKey(cont)) seedsByCont[cont] = new();
            seedsByCont[cont].Add((i, mx, my));
        }

        // Voronoi assignment: each land pixel → nearest territory seed in same continent
        _tidMap = new int[h, w];
        for (int yy = 0; yy < h; yy++)
            for (int xx = 0; xx < w; xx++)
            {
                _tidMap[yy, xx] = -1;
                var cont = contAt[yy, xx];
                if (cont == null) continue;
                if (!seedsByCont.TryGetValue(cont, out var seeds)) continue;

                int bestTid = -1;
                long bestD2 = long.MaxValue;
                foreach (var (tid, seedX, seedY) in seeds)
                {
                    long ddx = xx - seedX, ddy = yy - seedY;
                    long d2 = ddx * ddx + ddy * ddy;
                    if (d2 < bestD2) { bestD2 = d2; bestTid = tid; }
                }
                _tidMap[yy, xx] = bestTid;
            }

        _landMask = land;

        // Compute label positions (centroid within own pixels, biased to interior)
        var sums = new Dictionary<int, (long SX, long SY, int N)>();
        foreach (var td in _territories) sums[td.Tid] = (0, 0, 0);

        for (int yy = 0; yy < h; yy++)
            for (int xx = 0; xx < w; xx++)
            {
                int t = _tidMap[yy, xx];
                if (t < 0) continue;
                var (accX, accY, n) = sums[t];
                sums[t] = (accX + xx, accY + yy, n + 1);
            }

        _tidCenter = new();
        foreach (var td in _territories)
        {
            var (accX, accY, n) = sums.GetValueOrDefault(td.Tid, (0, 0, 0));
            _tidCenter[td.Tid] = n > 0
                ? ((int)(accX / n), (int)(accY / n))
                : seedByTid.GetValueOrDefault(td.Tid, (w / 2, h / 2));
        }
    }

    private void BuildBaseTexture(Renderer r)
    {
        int w = MapW, h = MapH;
        var pixels = new Color[w * h];
        var rng = new Random(42); // deterministic noise

        // Ocean gradient + noise
        for (int yy = 0; yy < h; yy++)
            for (int xx = 0; xx < w; xx++)
            {
                float t = yy / (float)h;
                int oceanR = (int)(12 + 18 * t);
                int oceanG = (int)(30 + 35 * t);
                int oceanB = (int)(60 + 50 * t);
                int noise = rng.Next(-4, 5);
                oceanR = Math.Clamp(oceanR + noise, 0, 255);
                oceanG = Math.Clamp(oceanG + noise, 0, 255);
                oceanB = Math.Clamp(oceanB + noise, 0, 255);
                pixels[yy * w + xx] = new Color(oceanR, oceanG, oceanB);
            }

        // Land base color + noise
        rng = new Random(42);
        for (int yy = 0; yy < h; yy++)
            for (int xx = 0; xx < w; xx++)
            {
                rng.Next(); // keep noise deterministic
                if (_landMask![yy, xx])
                {
                    int noise = rng.Next(-6, 7);
                    pixels[yy * w + xx] = new Color(
                        Math.Clamp(70 + noise, 0, 255),
                        Math.Clamp(105 + noise, 0, 255),
                        Math.Clamp(74 + noise, 0, 255));
                }
            }

        // Territory borders (darken pixels adjacent to different tids)
        for (int yy = 0; yy < h; yy++)
            for (int xx = 0; xx < w; xx++)
            {
                int here = _tidMap![yy, xx];
                if (here < 0) continue;
                bool isBorder = false;
                for (int d = 0; d < 4; d++)
                {
                    int nx = xx + (d == 0 ? 1 : d == 1 ? -1 : 0);
                    int ny = yy + (d == 2 ? 1 : d == 3 ? -1 : 0);
                    if (nx < 0 || nx >= w || ny < 0 || ny >= h) continue;
                    int oth = _tidMap[ny, nx];
                    if (oth >= 0 && oth != here) { isBorder = true; break; }
                }

                if (isBorder)
                {
                    // Check if same continent → internal border, else continent border
                    string? hereCont = null, othCont = null;
                    foreach (var td in _territories)
                    {
                        if (td.Tid == here) hereCont = td.Continent;
                    }

                    bool crossCont = false;
                    for (int d = 0; d < 4; d++)
                    {
                        int nx = xx + (d == 0 ? 1 : d == 1 ? -1 : 0);
                        int ny = yy + (d == 2 ? 1 : d == 3 ? -1 : 0);
                        if (nx < 0 || nx >= w || ny < 0 || ny >= h) continue;
                        int oth = _tidMap[ny, nx];
                        if (oth >= 0 && oth != here)
                        {
                            foreach (var td in _territories)
                                if (td.Tid == oth) { othCont = td.Continent; break; }
                            if (othCont != hereCont) { crossCont = true; break; }
                        }
                    }

                    var px = pixels[yy * w + xx];
                    float dim = crossCont ? 0.25f : 0.55f;
                    pixels[yy * w + xx] = new Color(
                        (int)(px.R * dim), (int)(px.G * dim), (int)(px.B * dim));
                }
            }

        // Coastline darkening (land pixels adjacent to ocean)
        for (int yy = 0; yy < h; yy++)
            for (int xx = 0; xx < w; xx++)
            {
                if (!_landMask![yy, xx]) continue;
                bool coastal = false;
                for (int d = 0; d < 4; d++)
                {
                    int nx = xx + (d == 0 ? 1 : d == 1 ? -1 : 0);
                    int ny = yy + (d == 2 ? 1 : d == 3 ? -1 : 0);
                    if (nx < 0 || nx >= w || ny < 0 || ny >= h) { coastal = true; break; }
                    if (!_landMask[ny, nx]) { coastal = true; break; }
                }
                if (coastal)
                {
                    var px = pixels[yy * w + xx];
                    pixels[yy * w + xx] = new Color(
                        (int)(px.R * 0.6f), (int)(px.G * 0.6f), (int)(px.B * 0.6f));
                }
            }

        _baseMapTex = new Texture2D(r.GraphicsDevice, w, h, false, SurfaceFormat.Color);
        _baseMapTex.SetData(pixels);
    }

    private void RebuildFillOverlay(Renderer r)
    {
        if (_tidMap == null) return;
        int w = MapW, h = MapH;
        var pixels = new Color[w * h];

        for (int yy = 0; yy < h; yy++)
            for (int xx = 0; xx < w; xx++)
            {
                int tid = _tidMap[yy, xx];
                if (tid < 0) { pixels[yy * w + xx] = Color.Transparent; continue; }

                int owner = _owner.GetValueOrDefault(tid, -1);
                if (owner < 0) { pixels[yy * w + xx] = Color.Transparent; continue; }

                var pc = GameConfig.PlayerColors[owner % GameConfig.PlayerColors.Length];

                // Check if border pixel → stronger color
                bool isBorder = false;
                for (int d = 0; d < 4; d++)
                {
                    int nx = xx + (d == 0 ? 1 : d == 1 ? -1 : 0);
                    int ny = yy + (d == 2 ? 1 : d == 3 ? -1 : 0);
                    if (nx < 0 || nx >= w || ny < 0 || ny >= h) continue;
                    int oth = _tidMap[ny, nx];
                    if (oth >= 0 && oth != tid) { isBorder = true; break; }
                }

                if (isBorder)
                    pixels[yy * w + xx] = new Color(pc.R, pc.G, pc.B, 200);
                else
                    pixels[yy * w + xx] = new Color(pc.R, pc.G, pc.B, 70);
            }

        _fillOverlayTex?.Dispose();
        _fillOverlayTex = new Texture2D(r.GraphicsDevice, w, h, false, SurfaceFormat.Color);
        _fillOverlayTex.SetData(pixels);
        _prevOwnerSnapshot = new Dictionary<int, int>(_owner);
    }

    private bool OwnerChanged()
    {
        if (_prevOwnerSnapshot == null) return true;
        if (_prevOwnerSnapshot.Count != _owner.Count) return true;
        foreach (var (tid, owner) in _owner)
            if (!_prevOwnerSnapshot.TryGetValue(tid, out var prev) || prev != owner) return true;
        return false;
    }

    // ── World-map territory rendering ────────────────────────
    private void DrawTerritoryMap(Renderer r, int width, int height)
    {
        EnsureMapTextures(r);
        if (_baseMapTex == null || _tidMap == null || _tidCenter == null) return;

        // Rebuild fill overlay if ownership changed
        if (OwnerChanged()) RebuildFillOverlay(r);

        // Fit map texture to screen area
        int mapTop = 80, pad = 10;
        int mapBottom = height - 44;
        int availH = mapBottom - mapTop;
        int availW = width - pad * 2;

        // Maintain aspect ratio
        float aspect = (float)MapW / MapH;
        int drawW, drawH;
        if (availW / aspect <= availH)
        {
            drawW = availW;
            drawH = (int)(availW / aspect);
        }
        else
        {
            drawH = availH;
            drawW = (int)(availH * aspect);
        }

        int drawX = (width - drawW) / 2;
        int drawY = mapTop + (availH - drawH) / 2;
        var destRect = new Rectangle(drawX, drawY, drawW, drawH);

        // Draw base map
        r.DrawTexture(_baseMapTex, destRect);

        // Draw fill overlay
        if (_fillOverlayTex != null)
            r.DrawTexture(_fillOverlayTex, destRect);

        // Draw territory labels and troop counts
        float scaleX = (float)drawW / MapW;
        float scaleY = (float)drawH / MapH;

        foreach (var td in _territories)
        {
            if (!_tidCenter.TryGetValue(td.Tid, out var center)) continue;
            int sx = drawX + (int)(center.X * scaleX);
            int sy = drawY + (int)(center.Y * scaleY);

            int owner = _owner.GetValueOrDefault(td.Tid, -1);
            int troops = _troops.GetValueOrDefault(td.Tid, 0);

            // Selection highlight
            bool isSelected = (_phase == "initial_deploy"
                ? _deploySelected.Values.Contains(td.Tid)
                : (_selectedFrom == td.Tid || _selectedTo == td.Tid));

            if (isSelected)
                r.DrawCircle((255, 255, 255), (sx, sy), 14, alpha: 100);

            // Troop token
            var tokenCol = owner >= 0
                ? GameConfig.PlayerColors[owner % GameConfig.PlayerColors.Length]
                : (80, 80, 80);
            int tokenR = Math.Max(8, (int)(11 * scaleX));
            r.DrawCircle((0, 0, 0), (sx + 1, sy + 1), tokenR, alpha: 80); // shadow
            r.DrawCircle(tokenCol, (sx, sy), tokenR, alpha: 200);

            // Troop count
            int troopFs = Math.Max(7, (int)(10 * scaleX));
            r.DrawText(troops.ToString(), sx, sy, troopFs, (255, 255, 255),
                anchorX: "center", anchorY: "center", bold: true);

            // Territory name (below token)
            string name = td.Name;
            if (name.Length > 12) name = name[..11] + "…";
            int nameFs = Math.Max(5, (int)(7 * scaleX));
            r.DrawText(name, sx, sy + tokenR + 3, nameFs, (220, 220, 220),
                anchorX: "center", anchorY: "top");
        }

        // Draw adjacency links for cross-ocean connections
        var crossLinks = new (string A, string B)[]
        {
            ("Alaska", "Kamchatka"),
            ("Greenland", "Iceland"),
            ("Central America", "Venezuela"),
            ("Brazil", "North Africa"),
            ("Indonesia", "SE Asia"),
        };

        var nameToTid = new Dictionary<string, int>();
        foreach (var td in _territories) nameToTid[td.Name] = td.Tid;

        foreach (var (nameA, nameB) in crossLinks)
        {
            if (!nameToTid.TryGetValue(nameA, out int tidA)) continue;
            if (!nameToTid.TryGetValue(nameB, out int tidB)) continue;
            if (!_tidCenter.TryGetValue(tidA, out var cA)) continue;
            if (!_tidCenter.TryGetValue(tidB, out var cB)) continue;
            int ax = drawX + (int)(cA.X * scaleX), ay = drawY + (int)(cA.Y * scaleY);
            int bx = drawX + (int)(cB.X * scaleX), by = drawY + (int)(cB.Y * scaleY);
            r.DrawLine((200, 200, 220), (ax, ay), (bx, by), alpha: 50);
        }
    }
}
