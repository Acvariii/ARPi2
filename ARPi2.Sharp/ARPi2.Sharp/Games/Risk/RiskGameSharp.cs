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
    private readonly AmbientSystem _ambient;
    private readonly LightBeamSystem _lightBeams = LightBeamSystem.ForTheme("risk");
    private readonly VignettePulse _vignette = new();
    private readonly Starfield _starfield;
    private readonly FloatingIconSystem _floatingIcons = FloatingIconSystem.ForTheme("risk");
    private readonly WaveBand _waveBand = WaveBand.ForTheme("risk");
    private readonly HeatShimmer _heatShimmer = HeatShimmer.ForTheme("risk");
    private int? _animPrevWinner;
    private double _animFwTimer;
    private double _totalElapsed;

    // ── World-map rendering ────────────────────────────────────
    private const int MapW = 1920, MapH = 1080;
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
        _ambient = AmbientSystem.ForTheme("risk", w, h);
        _starfield = Starfield.ForTheme("risk", w, h);
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
        _ambient.Update(d, ScreenW, ScreenH);
        _lightBeams.Update(d, ScreenW, ScreenH);
        _vignette.Update(d);
        _starfield.Update(d);
        _floatingIcons.Update(d, ScreenW, ScreenH);
        _waveBand.Update(d);
        _heatShimmer.Update(d);

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
        _ambient.Draw(r);
        _lightBeams.Draw(r, width, height);
        _starfield.Draw(r);
        _floatingIcons.Draw(r);
        RainbowTitle.Draw(r, "RISK", width);

        int cx = width / 2;
        int pad = 10;

        // ── Status bar ──
        {
            int sw = width - 2 * pad - 12, sh = 28, sx = pad + 6, sy = 46;
            r.DrawRect((0, 0, 0), (sx + 2, sy + 2, sw, sh), alpha: 50);
            r.DrawRect((18, 16, 24), (sx, sy, sw, sh), alpha: 200);
            r.DrawRect((160, 80, 60), (sx, sy, sw, 3), alpha: 80);
            r.DrawRect((120, 70, 50), (sx, sy, sw, sh), width: 1, alpha: 150);

            string statusText;
            if (_phase == "initial_deploy")
            {
                int poolSum = _initialDeployPools.Values.Sum();
                statusText = $"🪖 Initial Deploy: all players  ·  Unassigned: {poolSum}";
            }
            else
            {
                string turn = SeatLabel(_currentTurnSeat);
                statusText = $"⚔️ Turn: {turn}  ·  Phase: {_phase}  ·  Reinforcements: {_reinforcementsLeft}";
            }
            r.DrawText(statusText, sx + 12, sy + sh / 2, 13, (210, 200, 180), anchorX: "left", anchorY: "center");
        }

        // Selected territory info
        if (_phase != "initial_deploy" && _selectedFrom is int sf)
        {
            int ix = pad + 6, iy = 80, iw = 220, ih = 22;
            r.DrawRect((15, 14, 20), (ix, iy, iw, ih), alpha: 180);
            r.DrawRect((100, 90, 70), (ix, iy, iw, ih), width: 1, alpha: 100);
            r.DrawText($"📍 Selected: {TidName(sf)}", ix + 8, iy + ih / 2, 11, (200, 210, 200), anchorX: "left", anchorY: "center");
        }

        // Draw simplified territory map as a text-based grid
        DrawTerritoryMap(r, width, height);

        // ── Last attack roll ──
        if (_lastAttackRoll is var (aRoll, dRoll, aL, dL))
        {
            string rollText = $"⚔️ Last Roll: {FormatRoll(aRoll)} vs {FormatRoll(dRoll)} (A-{aL}, D-{dL})";
            int rw = Math.Max(280, rollText.Length * 9 + 40), rh = 30;
            int rx = cx - rw / 2, ry = height - 76;
            r.DrawRect((0, 0, 0), (rx + 2, ry + 2, rw, rh), alpha: 50);
            r.DrawRect((20, 16, 14), (rx, ry, rw, rh), alpha: 195);
            r.DrawRect((200, 160, 60), (rx, ry, rw, 3), alpha: 75);
            r.DrawRect((180, 140, 50), (rx, ry, rw, rh), width: 1, alpha: 140);
            r.DrawText(rollText, cx, ry + rh / 2, 13, (255, 225, 150), anchorX: "center", anchorY: "center", bold: true);
        }

        // ── Winner overlay ──
        if (_winner is int w)
        {
            r.DrawRect((0, 0, 0), (0, 0, width, height), alpha: 150);
            int bw2 = Math.Min(600, width * 55 / 100), bh2 = 180;
            int bx2 = cx - bw2 / 2, by2 = height / 2 - bh2 / 2;
            r.DrawRect((0, 0, 0), (bx2 + 3, by2 + 3, bw2, bh2), alpha: 60);
            r.DrawRect((10, 10, 18), (bx2, by2, bw2, bh2), alpha: 230);
            r.DrawRect((255, 215, 0), (bx2, by2, bw2, 4), alpha: 200);
            r.DrawRect((255, 215, 0), (bx2, by2, bw2, bh2), width: 3, alpha: 200);
            int ins = 6;
            r.DrawRect((255, 215, 0), (bx2 + ins, by2 + ins, bw2 - 2 * ins, bh2 - 2 * ins), width: 1, alpha: 22);
            var wCol = GameConfig.PlayerColors[w % GameConfig.PlayerColors.Length];
            r.DrawText("🏆", cx, height / 2 + 30, 50, (255, 215, 0), anchorX: "center", anchorY: "center");
            r.DrawText($"{SeatLabel(w)} WINS!", cx, height / 2 - 24, 40, wCol, anchorX: "center", anchorY: "center", bold: true);
            r.DrawText("Mission Complete", cx, height / 2 + 6, 18, wCol, anchorX: "center", anchorY: "center");
        }

        // ── Defend-choose banner ──
        if (_phase == "defend_choose" && _defendPendingSeat is int defSeat)
        {
            var dcol = GameConfig.PlayerColors[defSeat % GameConfig.PlayerColors.Length];
            int ow = 380, oh = 60;
            int ox = (width - ow) / 2, oy = height / 2 - oh / 2;
            r.DrawRect((0, 0, 0), (ox + 3, oy + 3, ow, oh), alpha: 55);
            r.DrawRect((10, 10, 18), (ox, oy, ow, oh), alpha: 230);
            r.DrawRect(dcol, (ox, oy, ow, 3), alpha: 90);
            r.DrawRect(dcol, (ox, oy, ow, oh), width: 2, alpha: 180);
            int dins = 4;
            r.DrawRect(dcol, (ox + dins, oy + dins, ow - 2 * dins, oh - 2 * dins), width: 1, alpha: 18);
            r.DrawText($"⚔️  {SeatLabel(defSeat)}: Choose Defense Dice",
                ox + ow / 2, oy + oh / 2, 16, dcol, anchorX: "center", anchorY: "center", bold: true);
        }

        // ── Last event ──
        if (!string.IsNullOrEmpty(_lastEvent) && _lastEventAge < 6.0)
        {
            int ew = Math.Max(240, _lastEvent.Length * 8 + 32), eh = 26;
            r.DrawRect((0, 0, 0), (pad + 2, height - 34, ew, eh), alpha: 50);
            r.DrawRect((14, 12, 18), (pad, height - 36, ew, eh), alpha: 185);
            r.DrawRect((140, 100, 60), (pad, height - 36, ew, 3), alpha: 65);
            r.DrawRect((100, 80, 50), (pad, height - 36, ew, eh), width: 1, alpha: 120);
            r.DrawText($"📢 {_lastEvent}", pad + 10, height - 36 + eh / 2, 11, (200, 205, 210), anchorX: "left", anchorY: "center");
        }

        // Animations
        _particles.Draw(r);
        foreach (var pr in _pulseRings) pr.Draw(r);
        foreach (var fl in _flashes) fl.Draw(r, width, height);
        foreach (var tp in _textPops) tp.Draw(r);
        _waveBand.Draw(r, width, height);
        _heatShimmer.Draw(r, width, height);
        _vignette.Draw(r, width, height);

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

        var land = new bool[h, w];
        var contAt = new string?[h, w];

        // ── Helpers ──

        // Lon/lat → pixel (equirectangular, top-left origin)
        int LLx(double lon) => Clamp((int)((lon + 180.0) / 360.0 * (w - 1)), 0, w - 1);
        int LLy(double lat) => Clamp((int)((90.0 - lat) / 180.0 * (h - 1)), 0, h - 1);
        float DegX(float d) => d * w / 360f;
        float DegY(float d) => d * h / 180f;

        // Scanline polygon fill (even-odd rule). coords = flat [lon0,lat0, lon1,lat1, ...]
        void FillPoly(bool[,] mask, double[] c, bool val = true)
        {
            int n = c.Length / 2;
            if (n < 3) return;
            var vx = new float[n]; var vy = new float[n];
            for (int i = 0; i < n; i++)
            {
                vx[i] = (float)((c[i * 2] + 180.0) / 360.0 * (w - 1));
                vy[i] = (float)((90.0 - c[i * 2 + 1]) / 180.0 * (h - 1));
            }
            float minY = vy[0], maxY = vy[0];
            for (int i = 1; i < n; i++) { if (vy[i] < minY) minY = vy[i]; if (vy[i] > maxY) maxY = vy[i]; }
            int y0 = Math.Max(0, (int)minY), y1 = Math.Min(h - 1, (int)maxY);
            var xs = new List<float>();
            for (int y = y0; y <= y1; y++)
            {
                xs.Clear();
                for (int i = 0, j = n - 1; i < n; j = i++)
                {
                    float yi = vy[i], yj = vy[j];
                    if ((yi <= y && yj > y) || (yj <= y && yi > y))
                        xs.Add(vx[i] + (y - yi) / (yj - yi) * (vx[j] - vx[i]));
                }
                xs.Sort();
                for (int k = 0; k + 1 < xs.Count; k += 2)
                {
                    int x0s = Math.Max(0, (int)xs[k]);
                    int x1s = Math.Min(w - 1, (int)xs[k + 1]);
                    for (int x = x0s; x <= x1s; x++) mask[y, x] = val;
                }
            }
        }

        // Ellipse fill (pixel coords) for small islands
        void PaintEllipse(bool[,] mask, float cx, float cy, float rx, float ry, bool val = true)
        {
            if (rx <= 0 || ry <= 0) return;
            int x0 = Clamp((int)(cx - rx - 1), 0, w - 1), x1 = Clamp((int)(cx + rx + 1), 0, w - 1);
            int y0 = Clamp((int)(cy - ry - 1), 0, h - 1), y1 = Clamp((int)(cy + ry + 1), 0, h - 1);
            float irx2 = 1f / (rx * rx), iry2 = 1f / (ry * ry);
            for (int yy = y0; yy <= y1; yy++)
                for (int xx = x0; xx <= x1; xx++)
                {
                    float dx = xx - cx, dy = yy - cy;
                    if (dx * dx * irx2 + dy * dy * iry2 <= 1f) mask[yy, xx] = val;
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

        // ── NORTH AMERICA ── (detailed polygon coastline)
        var mNA = new bool[h, w];
        FillPoly(mNA, new double[] {
            // NW Alaska, clockwise
            -168,66, -165,69, -162,71, -158,72, -155,72,
            // Arctic coast Alaska / Canada
            -150,71, -145,70, -142,70, -138,69, -135,71,
            -130,74, -125,75, -120,75, -115,74, -110,74,
            // Central Arctic / Baffin
            -105,73, -100,73, -95,72, -90,70, -85,68,
            // Hudson Strait / Labrador
            -80,66, -77,65, -73,63, -68,61, -63,58, -59,54,
            // Newfoundland / Maritimes
            -55,49, -53,47, -56,45, -59,44, -63,44,
            // New England coast
            -66,44, -68,43, -70,42, -72,41,
            // Mid-Atlantic
            -74,40, -75,39, -76,37, -77,35,
            // Carolinas / Georgia
            -79,34, -80,33, -81,31,
            // Florida east coast & tip
            -81,28, -81,26, -80,25,
            // Florida west coast & Gulf Coast
            -82,26, -84,29, -86,30, -88,30,
            -90,29, -92,30, -94,30, -96,29, -97,27,
            // Mexico east coast
            -97,24, -97,22, -96,20,  -94,19,
            // Yucatan Peninsula
            -91,18, -89,20, -87,21, -87,19,
            // South into Central America
            -88,16, -86,14, -84,11, -83,9, -80,8,
            // Central America Pacific side going north
            -80,7, -83,10, -86,12, -90,14,
            // Mexico Pacific coast
            -95,16, -98,17, -101,19,
            // Baja California
            -104,22, -107,24, -109,23, -110,23,
            // Gulf of California / US SW
            -112,28, -114,30, -117,33,
            // California coast
            -119,35, -121,37, -122,39,
            // Oregon / Washington
            -123,42, -124,44, -124,47,
            // British Columbia
            -126,50, -128,53, -131,55,
            // Alaska Panhandle
            -134,57, -138,58, -142,60,
            // Alaska south coast (Gulf of Alaska)
            -148,61, -152,60, -155,59, -158,58,
            // Alaska Peninsula / back to start
            -160,60, -163,63, -166,65, -168,66
        });
        // Greenland
        FillPoly(mNA, new double[] {
            -55,60, -50,60, -45,61, -40,63, -35,65,
            -28,68, -22,72, -18,76, -20,80,
            -28,82, -37,83, -45,83, -52,82,
            -56,78, -58,74, -60,70, -58,65, -55,60
        });
        // Cuba
        FillPoly(mNA, new double[] {
            -85,22, -83,23, -80,23, -77,22, -75,20,
            -77,20, -80,21, -84,21, -85,22
        });
        // Carve Hudson Bay
        FillPoly(mNA, new double[] {
            -95,67, -92,64, -88,61, -84,58, -80,56, -78,57,
            -78,59, -80,62, -83,64, -87,66, -91,67, -95,67
        }, false);
        // Carve Great Lakes (simplified)
        PaintEllipse(mNA, LLx(-84), LLy(45), DegX(5), DegY(2.2f), false);
        mNA = Smooth(mNA, 2);

        // ── SOUTH AMERICA ──
        var mSA = new bool[h, w];
        FillPoly(mSA, new double[] {
            // Northern coast (Colombia → Venezuela → Guianas)
            -80,10, -77,11, -75,12, -73,12, -70,12, -67,11,
            -64,10, -62,10, -59,8, -56,6, -53,4, -50,2,
            // Brazilian coast (Amazon to bulge)
            -48,0, -45,-1, -43,-2, -40,-3, -37,-5,
            // Brazil eastern bulge (Natal)
            -35,-6, -35,-9, -35,-12,
            // Brazil south coast
            -37,-15, -38,-17, -40,-20, -41,-23,
            // Uruguay / Argentina coast
            -43,-24, -47,-27, -50,-30, -53,-32,
            // Patagonia
            -57,-36, -60,-39, -63,-42, -65,-46,
            // Tierra del Fuego
            -67,-50, -68,-53, -70,-55,
            // Chilean coast going north
            -74,-53, -75,-49, -75,-46, -74,-42,
            -73,-38, -72,-34, -71,-30,
            // Peru / northern Chile coast
            -71,-25, -70,-20, -71,-17,
            -74,-14, -76,-12, -78,-8,
            // Ecuador / Colombia Pacific
            -80,-4, -80,0, -79,3, -78,6, -77,8, -80,10
        });
        mSA = Smooth(mSA, 2);

        // ── EURASIA ── (detailed outer coastline, clockwise from Iberian SW)
        var mEU = new bool[h, w];
        FillPoly(mEU, new double[] {
            // Portugal / Spain south coast (Gibraltar)
            -10,37, -8,36, -6,36, -3,36,
            // Spain Mediterranean coast
            -1,37, 0,38, 2,39, 3,42,
            // French Riviera
            5,43, 7,44,
            // Italian west coast (going south)
            8,44, 10,43, 12,42, 14,41, 15,40,
            // Southern Italy (toe/heel)
            16,38, 17,38,
            // Italy east coast (going north)
            16,39, 15,41, 14,42, 13,44, 13,46,
            // Adriatic head → Slovenia / Croatian coast
            15,46, 17,44, 19,42, 20,40,
            // Greek peninsula (Peloponnese)
            22,38, 22,37, 24,36,
            // Aegean → Turkey west coast
            26,37, 27,39, 29,38,
            // Turkey south coast / Eastern Mediterranean
            31,37, 33,36, 35,35, 36,34,
            // Levant (Syria → Israel → Sinai)
            36,33, 36,31, 35,30, 34,29,
            // Red Sea coast of Arabia → Yemen
            36,27, 38,24, 40,21, 42,18, 44,14,
            // Aden → Oman
            46,12, 49,12, 52,14, 55,17,
            // Oman → Strait of Hormuz
            57,21, 58,24,
            // Persian Gulf south → Iran → Pakistan
            60,25, 62,26, 64,26, 66,25, 68,23,
            // India west coast
            70,20, 72,17, 73,14, 74,10, 76,8,
            // India south tip
            78,8, 80,8,
            // India east coast
            80,10, 82,13, 84,16, 86,19, 88,21, 90,22,
            // Bangladesh / Myanmar
            92,22, 94,20, 96,17,
            // Thailand / Indochina west
            99,15, 100,12, 101,8, 102,4,
            // Malay Peninsula tip
            103,2, 104,1,
            // Indochina east coast (Vietnam → China)
            105,3, 106,8, 107,10, 108,14, 110,16,
            // China south coast
            112,19, 114,21, 117,23, 119,25, 121,28,
            // China east coast
            122,30, 124,32,
            // Korean Peninsula
            126,34, 127,36, 129,38, 128,39,
            // Sea of Japan → Russian Pacific
            130,36, 132,35, 135,38, 138,40,
            141,43, 144,46, 148,49, 152,52,
            // Kamchatka Peninsula
            155,54, 158,57, 162,59, 160,62,
            // NE Siberia → Arctic coast
            162,64, 170,65, 175,68, 170,70,
            // Siberian Arctic coast (east to west)
            160,69, 150,68, 140,72, 130,74,
            120,75, 110,75, 100,74, 90,73,
            80,72, 70,70, 60,68,
            // Novaya Zemlya area / Barents
            55,70, 50,67, 45,69, 40,70,
            // White Sea / Kola
            35,70, 30,71, 25,71, 20,70,
            // North Cape → Norwegian coast south
            17,69, 14,67, 12,65, 10,63,
            8,62, 6,61, 5,60, 6,58,
            // Denmark / Jutland
            10,58, 12,57, 10,55, 9,54,
            // North Sea / Netherlands
            7,54, 5,52, 4,51, 2,50,
            // English Channel → France
            0,49, -2,48, -3,47,
            // Bay of Biscay
            -5,44, -8,44, -9,43,
            // Spain north coast → Portugal
            -10,42, -10,39, -10,37
        });
        // Carve Black Sea
        FillPoly(mEU, new double[] {
            28,41, 30,42, 33,43, 36,43, 39,42, 41,41,
            40,44, 37,45, 34,46, 31,45, 28,43, 28,41
        }, false);
        // Carve Caspian Sea
        PaintEllipse(mEU, LLx(51), LLy(42), DegX(3), DegY(6), false);
        // Carve Persian Gulf
        PaintEllipse(mEU, LLx(52), LLy(27), DegX(4.5f), DegY(2.5f), false);
        mEU = Smooth(mEU, 2);

        // ── AFRICA ──
        var mAF = new bool[h, w];
        FillPoly(mAF, new double[] {
            // NW coast (Morocco → Western Sahara → Senegal)
            -17,35, -17,32, -17,28, -17,24, -17,20, -17,16,
            // Guinea coast (Senegal → Ivory Coast)
            -16,12, -15,10, -12,8, -8,5, -5,5,
            // Gulf of Guinea
            0,5, 3,5, 6,4, 8,4, 10,4, 10,2,
            // Gabon / Congo / Angola coast
            10,0, 9,-2, 10,-4, 12,-8,
            // Angola / Namibia
            13,-12, 14,-16, 16,-20, 17,-24,
            // Namibia / SW Africa
            16,-28, 18,-32,
            // Cape of Good Hope
            20,-34, 25,-34, 28,-33,
            // SE coast (Mozambique)
            30,-30, 32,-27, 34,-24, 36,-20,
            // Tanzania / Kenya coast
            38,-14, 40,-8, 42,-4, 44,-1,
            // Horn of Africa (Somalia)
            46,2, 48,6, 50,10, 48,12,
            // Gulf of Aden coast
            44,12, 42,14,
            // Red Sea coast (Eritrea / Sudan / Egypt)
            40,16, 38,19, 36,22, 34,26, 33,28, 32,30,
            // Egypt Mediterranean coast
            31,31, 28,31, 25,32, 22,33,
            // Libya coast
            18,33, 15,33,
            // Tunisia – northernmost point
            11,37, 10,37,
            // Algeria coast
            8,37, 5,37, 3,36, 0,36,
            // Morocco
            -2,35, -5,35, -8,34, -13,35, -17,35
        });
        // Madagascar
        FillPoly(mAF, new double[] {
            45,-12, 47,-14, 49,-17, 50,-20,
            50,-24, 48,-26, 46,-25,
            44,-21, 43,-17, 44,-14, 45,-12
        });
        mAF = Smooth(mAF, 2);

        // ── AUSTRALIA ── (detailed coastline)
        var mAU = new bool[h, w];
        FillPoly(mAU, new double[] {
            // NW coast (Kimberley)
            115,-14, 118,-14, 122,-14, 125,-14,
            // Top End (Arnhem Land) → Gulf of Carpentaria west
            128,-12, 131,-12, 133,-12,
            // Cape York Peninsula (east side of GoC)
            136,-12, 138,-14, 141,-15, 143,-14,
            // East coast (Queensland)
            145,-16, 147,-19, 149,-22,
            // NSW
            150,-24, 152,-27, 153,-29,
            // Victoria / Bass Strait
            153,-34, 151,-37, 148,-38,
            // Great Australian Bight
            142,-38, 137,-36, 133,-34, 129,-33,
            // SW coast (Western Australia)
            126,-34, 122,-34, 118,-34, 115,-33, 114,-30,
            // Western Australia coast north
            114,-26, 113,-22, 113,-18, 114,-15, 115,-14
        });
        // Carve Gulf of Carpentaria
        FillPoly(mAU, new double[] {
            133,-13, 135,-15, 137,-17, 139,-17, 141,-15,
            140,-13, 137,-12, 134,-12, 133,-13
        }, false);
        // New Guinea
        FillPoly(mAU, new double[] {
            132,-1, 135,-2, 138,-3, 141,-4, 144,-5, 147,-6, 150,-8,
            148,-10, 145,-8, 141,-7, 137,-5, 133,-3, 130,-2, 132,-1
        });
        // Tasmania
        FillPoly(mAU, new double[] {
            145,-40, 147,-40, 148,-41, 148,-43,
            146,-44, 144,-43, 144,-41, 145,-40
        });
        // Sumatra (diagonal NW–SE island)
        FillPoly(mAU, new double[] {
            95,6, 97,5, 99,3, 101,1, 103,-1, 105,-4, 106,-6,
            105,-7, 103,-4, 101,-1, 99,1, 97,3, 95,4, 95,6
        });
        // Java
        FillPoly(mAU, new double[] {
            105,-6, 108,-6, 111,-7, 114,-8,
            114,-9, 111,-8, 108,-8, 105,-7, 105,-6
        });
        // Borneo
        FillPoly(mAU, new double[] {
            108,5, 111,4, 114,3, 117,1, 118,-1, 118,-3,
            116,-4, 114,-3, 112,-1, 110,1, 108,3, 108,5
        });
        // Sulawesi / minor islands
        PaintEllipse(mAU, LLx(121), LLy(-2), DegX(2.5f), DegY(4), true);
        mAU = Smooth(mAU, 1);

        // ── ISLANDS (assigned to Eurasia) ──
        var mIs = new bool[h, w];
        // Great Britain
        FillPoly(mIs, new double[] {
            -6,50, -3,50, -1,51, 0,52, 1,53, 2,55,
            1,57, 0,58, -2,59, -4,58, -6,57, -7,55,
            -6,53, -5,51, -6,50
        });
        // Ireland
        FillPoly(mIs, new double[] {
            -10,52, -8,51, -6,52, -6,54, -7,55,
            -9,55, -10,54, -10,52
        });
        // Iceland
        FillPoly(mIs, new double[] {
            -24,64, -20,63, -16,63, -13,64, -13,66,
            -16,67, -20,67, -24,66, -24,64
        });
        // Japan (thickened arc: Kyushu → Hokkaido)
        FillPoly(mIs, new double[] {
            128,31, 130,33, 133,35, 136,36, 139,38, 141,41, 143,44, 145,46,
            146,45, 144,43, 142,40, 139,37, 136,35, 133,33, 131,31, 128,31
        });
        // Sicily
        PaintEllipse(mIs, LLx(14), LLy(37.5f), DegX(1.8f), DegY(1.2f), true);
        // Sardinia
        PaintEllipse(mIs, LLx(9), LLy(40), DegX(1.3f), DegY(1.8f), true);
        // Sri Lanka
        PaintEllipse(mIs, LLx(81), LLy(8), DegX(1.5f), DegY(2.5f), true);
        // Taiwan
        PaintEllipse(mIs, LLx(121), LLy(24), DegX(1.5f), DegY(2.5f), true);
        // Philippines (Luzon + Mindanao crescent)
        FillPoly(mIs, new double[] {
            120,18, 122,16, 124,13, 126,9, 125,7,
            123,9, 121,12, 119,15, 120,18
        });
        // New Zealand – North Island
        FillPoly(mIs, new double[] {
            174,-36, 177,-37, 178,-39, 176,-41,
            174,-40, 173,-38, 174,-36
        });
        // New Zealand – South Island
        FillPoly(mIs, new double[] {
            170,-42, 172,-42, 174,-44, 173,-46,
            170,-47, 168,-46, 169,-44, 170,-42
        });
        mIs = Smooth(mIs, 1);

        // ── ANTARCTICA ──
        var mAnt = new bool[h, w];
        FillPoly(mAnt, new double[] {
            -170,-65, -140,-67, -120,-68, -90,-70, -60,-70,
            -30,-68, 0,-68, 30,-70, 60,-70, 90,-68,
            120,-68, 150,-67, 170,-65,
            170,-90, -170,-90, -170,-65
        });
        mAnt = Smooth(mAnt, 1);

        // ── Apply masks ──
        void ApplyMask(bool[,] mask, string? cont)
        {
            for (int yy = 0; yy < h; yy++)
                for (int xx = 0; xx < w; xx++)
                    if (mask[yy, xx] && !land[yy, xx])
                    { land[yy, xx] = true; contAt[yy, xx] = cont; }
        }

        ApplyMask(mNA, "North America");
        ApplyMask(mSA, "South America");
        ApplyMask(mEU, "Eurasia");
        ApplyMask(mAF, "Africa");
        ApplyMask(mAU, "Australia");
        ApplyMask(mIs, "Eurasia");
        ApplyMask(mAnt, null);

        // Split Eurasia → Europe / Asia
        // Europe = west of ~42°E AND north of ~35°N (captures UK, Scandinavia, Ukraine; excludes Ural, Middle East)
        int euroSplitX = LLx(42);
        int euroSplitY = LLy(35);
        for (int yy = 0; yy < h; yy++)
            for (int xx = 0; xx < w; xx++)
            {
                if (contAt[yy, xx] != "Eurasia") continue;
                contAt[yy, xx] = (xx < euroSplitX && yy < euroSplitY) ? "Europe" : "Asia";
            }

        // ── Territory seeds, Voronoi assignment, label computation ──
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
        // Second pass: pick an interior pixel nearest the centroid to avoid border/coast drift
        var bestPos = new Dictionary<int, (int X, int Y)>();
        var bestLabelD2 = new Dictionary<int, long>();
        foreach (var td in _territories)
        {
            bestPos[td.Tid] = seedByTid.GetValueOrDefault(td.Tid, (w / 2, h / 2));
            bestLabelD2[td.Tid] = long.MaxValue;
        }

        // Compute centroids first
        var centroids = new Dictionary<int, (int X, int Y)>();
        foreach (var td in _territories)
        {
            var (accX, accY, n) = sums.GetValueOrDefault(td.Tid, (0, 0, 0));
            centroids[td.Tid] = n > 0
                ? ((int)(accX / n), (int)(accY / n))
                : seedByTid.GetValueOrDefault(td.Tid, (w / 2, h / 2));
        }

        for (int yy = 0; yy < h; yy++)
            for (int xx = 0; xx < w; xx++)
            {
                int t2 = _tidMap[yy, xx];
                if (t2 < 0) continue;
                var (ccx, ccy) = centroids.GetValueOrDefault(t2, (xx, yy));
                long ddx = xx - ccx, ddy = yy - ccy;
                long d2 = ddx * ddx + ddy * ddy;
                // Penalize border pixels to prefer interior placement
                bool border = false;
                for (int d = 0; d < 4; d++)
                {
                    int nx = xx + (d == 0 ? 1 : d == 1 ? -1 : 0);
                    int ny = yy + (d == 2 ? 1 : d == 3 ? -1 : 0);
                    if (nx < 0 || nx >= w || ny < 0 || ny >= h) { border = true; break; }
                    if (_tidMap[ny, nx] != t2) { border = true; break; }
                }
                if (border) d2 += 5000;
                if (d2 < bestLabelD2.GetValueOrDefault(t2, long.MaxValue))
                {
                    bestLabelD2[t2] = d2;
                    bestPos[t2] = (xx, yy);
                }
            }

        foreach (var td in _territories)
            _tidCenter[td.Tid] = bestPos.GetValueOrDefault(td.Tid,
                seedByTid.GetValueOrDefault(td.Tid, (w / 2, h / 2)));
    }

    private void BuildBaseTexture(Renderer r)
    {
        int w = MapW, h = MapH;
        var pixels = new Color[w * h];

        // Deterministic hash-based noise (matches Python)
        static int Noise(int x, int y)
        {
            uint v = (uint)((x * 374761393 + y * 668265263)) & 0xFFFFFFFF;
            v = (v ^ (v >> 13)) & 0xFFFFFFFF;
            v = (v * 1274126177) & 0xFFFFFFFF;
            return (int)(v >> 28) - 8; // [-8..7]
        }

        // Precompute thick continent-boundary mask
        var contBorder = new bool[h, w];
        var tidToCont = new Dictionary<int, string>();
        foreach (var td in _territories) tidToCont[td.Tid] = td.Continent;

        // Base pass: find continent border pixels
        var baseBorder = new bool[h, w];
        for (int yy = 0; yy < h; yy++)
            for (int xx = 0; xx < w; xx++)
            {
                int here = _tidMap![yy, xx];
                if (here < 0) continue;
                if (!tidToCont.TryGetValue(here, out var c0)) continue;
                for (int d = 0; d < 4; d++)
                {
                    int nx = xx + (d == 0 ? 1 : d == 1 ? -1 : 0);
                    int ny = yy + (d == 2 ? 1 : d == 3 ? -1 : 0);
                    if (nx < 0 || nx >= w || ny < 0 || ny >= h) continue;
                    int oth = _tidMap[ny, nx];
                    if (oth < 0 || oth == here) continue;
                    if (tidToCont.TryGetValue(oth, out var c1) && c1 != c0)
                    {
                        baseBorder[yy, xx] = true;
                        break;
                    }
                }
            }

        // Dilate by 1 pixel
        for (int yy = 0; yy < h; yy++)
            for (int xx = 0; xx < w; xx++)
            {
                if (!baseBorder[yy, xx]) continue;
                for (int dy = -1; dy <= 1; dy++)
                    for (int dx = -1; dx <= 1; dx++)
                    {
                        int ny = yy + dy, nx = xx + dx;
                        if (ny >= 0 && ny < h && nx >= 0 && nx < w)
                            contBorder[ny, nx] = true;
                    }
            }

        // Render pixels
        for (int yy = 0; yy < h; yy++)
            for (int xx = 0; xx < w; xx++)
            {
                int tid = _tidMap![yy, xx];
                bool isLand = _landMask![yy, xx];

                if (!isLand)
                {
                    // Ocean: gradient + noise (matching Python bottom-left: t=0 south, t=1 north)
                    float t = (float)(h - 1 - yy) / Math.Max(1, h - 1);
                    int n = Noise(xx, yy);
                    int oR = Math.Clamp((int)(10 + 12 * t) + n, 0, 255);
                    int oG = Math.Clamp((int)(24 + 34 * t) + n, 0, 255);
                    int oB = Math.Clamp((int)(56 + 40 * t) + n, 0, 255);
                    pixels[yy * w + xx] = new Color(oR, oG, oB);
                    continue;
                }

                // Land: flat green + noise
                int ln = Noise(xx, yy) / 2; // [-4..3] like Python's n//2
                int lR = Math.Clamp(70 + ln, 0, 255);
                int lG = Math.Clamp(105 + ln, 0, 255);
                int lB = Math.Clamp(74 + ln, 0, 255);

                // Internal border darkening
                if (tid >= 0)
                {
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
                    {
                        lR = (int)(lR * 0.55f);
                        lG = (int)(lG * 0.55f);
                        lB = (int)(lB * 0.55f);
                    }
                }

                // Continent border (thicker, darker)
                if (contBorder[yy, xx])
                {
                    lR = (int)(lR * 0.25f);
                    lG = (int)(lG * 0.25f);
                    lB = (int)(lB * 0.25f);
                }

                pixels[yy * w + xx] = new Color(lR, lG, lB);
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

        // Fit map texture to nearly the full screen
        int mapTop = 62, pad = 4;
        int mapBottom = height - 30;
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

        // Draw all cross-ocean adjacency links
        var nameToTid = new Dictionary<string, int>();
        foreach (var td in _territories) nameToTid[td.Name] = td.Tid;

        var crossLinks = new (string A, string B)[]
        {
            ("Alaska", "Kamchatka"),
            ("Greenland", "Iceland"),
            ("Central America", "Venezuela"),
            ("Brazil", "North Africa"),
            ("Southern Europe", "Egypt"),
            ("Southern Europe", "North Africa"),
            ("Western Europe", "North Africa"),
            ("Ukraine", "Afghanistan"),
            ("Middle East", "Egypt"),
            ("Middle East", "East Africa"),
            ("Middle East", "India"),
            ("Middle East", "Afghanistan"),
            ("Middle East", "Southern Europe"),
            ("Indonesia", "SE Asia"),
            ("Indonesia", "New Guinea"),
            ("New Guinea", "Eastern Australia"),
        };

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

        // Selection pulsing
        float pulse = 0.5f + 0.5f * MathF.Sin((float)_totalElapsed * 5f);

        foreach (var td in _territories)
        {
            if (!_tidCenter.TryGetValue(td.Tid, out var center)) continue;
            int sx = drawX + (int)(center.X * scaleX);
            int sy = drawY + (int)(center.Y * scaleY);

            int owner = _owner.GetValueOrDefault(td.Tid, -1);
            int troops = _troops.GetValueOrDefault(td.Tid, 0);

            // Selection highlight (pulsing)
            bool isSelected = (_phase == "initial_deploy"
                ? _deploySelected.Values.Contains(td.Tid)
                : (_selectedFrom == td.Tid || _selectedTo == td.Tid));

            if (isSelected)
            {
                int pulseR = (int)(16 + pulse * 6);
                r.DrawCircle((255, 255, 255), (sx, sy), pulseR, alpha: (int)(80 + 60 * pulse));
            }

            // Token shadow
            r.DrawCircle((0, 0, 0), (sx + 2, sy + 2), 14, alpha: 80);

            // Current-turn glow
            if (_currentTurnSeat is int ct && owner == ct)
                r.DrawCircle((255, 255, 200), (sx, sy), 20, alpha: (int)(30 + 25 * pulse));

            // Troop token (colored disc)
            var tokenCol = owner >= 0
                ? GameConfig.PlayerColors[owner % GameConfig.PlayerColors.Length]
                : (80, 80, 80);
            r.DrawCircle(tokenCol, (sx, sy), 14, alpha: 200);

            // Highlight on top half
            r.DrawCircle((255, 255, 255), (sx, sy - 2), 10, alpha: 25);

            // Outline
            r.DrawCircle((0, 0, 0), (sx, sy), 14, width: 1, alpha: 100);

            // Troop count
            r.DrawText(troops.ToString(), sx, sy, 13, (255, 255, 255),
                anchorX: "center", anchorY: "center", bold: true);

            // Territory name (below token)
            r.DrawText(td.Name, sx, sy + 20, 11, (220, 220, 220),
                anchorX: "center", anchorY: "top");
        }
    }
}
