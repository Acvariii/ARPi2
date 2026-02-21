using System;
using System.Collections.Generic;
using System.Linq;
using ARPi2.Sharp.Core;

namespace ARPi2.Sharp.Games.Catan;

// ════════════════════════════════════════════════════════════════
//  Data types
// ════════════════════════════════════════════════════════════════

public sealed class HexTile
{
    public int Q { get; }
    public int R { get; }
    public string Kind { get; } // wood|brick|sheep|wheat|ore|desert|water|gold|volcano
    public int? Number { get; } // 2..12 excluding 7; null for water/desert/volcano

    public HexTile(int q, int r, string kind, int? number)
    {
        Q = q; R = r; Kind = kind; Number = number;
    }
}

public sealed class Port
{
    public int Q { get; }
    public int R { get; }
    public string Kind { get; } // any|wood|brick|sheep|wheat|ore

    public Port(int q, int r, string kind) { Q = q; R = r; Kind = kind; }
}

public sealed class ExpansionConfig
{
    public string Name { get; init; } = "base";
    public int Radius { get; init; } = 4;
    public bool WaterRing { get; init; } = true;
    public int IslandCount { get; init; }
    public int IslandRadius { get; init; }
    public int Ports { get; init; } = 8;
    public double ExtraWaterProb { get; init; }
    public int GoldTiles { get; init; }
    public int VolcanoTiles { get; init; }
}

// ════════════════════════════════════════════════════════════════
//  CatanGameSharp — full port from Python
// ════════════════════════════════════════════════════════════════
public class CatanGameSharp : BaseGame
{
    public override string ThemeName => "catan";

    // ── Constants ──────────────────────────────────────────────
    private static readonly string[] Resource = { "wood", "brick", "sheep", "wheat", "ore" };

    private static readonly Dictionary<string, string> KindEmoji = new()
    {
        ["wood"] = "🌲", ["brick"] = "🧱", ["sheep"] = "🐑", ["wheat"] = "🌾", ["ore"] = "⛰️",
        ["desert"] = "🏜️", ["water"] = "🌊", ["gold"] = "🪙", ["volcano"] = "🌋",
    };

    private static readonly Dictionary<string, string> PortEmoji = new()
    {
        ["any"] = "⚓", ["wood"] = "🌲⚓", ["brick"] = "🧱⚓",
        ["sheep"] = "🐑⚓", ["wheat"] = "🌾⚓", ["ore"] = "⛰️⚓",
    };

    private static readonly Dictionary<string, (int R, int G, int B)> KindColor = new()
    {
        ["wood"] = (72, 150, 72),
        ["brick"] = (170, 90, 70),
        ["sheep"] = (120, 190, 110),
        ["wheat"] = (200, 180, 90),
        ["ore"] = (110, 110, 130),
        ["desert"] = (200, 170, 120),
        ["water"] = (70, 120, 200),
        ["gold"] = (200, 175, 70),
        ["volcano"] = (140, 70, 70),
    };

    private static readonly (int R, int G, int B)[] PlayerPalette =
    {
        (255, 70, 70), (70, 145, 255), (70, 255, 150), (255, 220, 70),
        (210, 90, 255), (70, 255, 245), (255, 90, 210), (210, 255, 90),
    };

    // ── Game state ─────────────────────────────────────────────
    private int? _currentTurnSeat;
    private string _phase = "player_select";
    private List<int> _initialOrder = new();
    private int _initialStep;
    private int? _initialLastSettlementVertex;

    private bool _rolledThisTurn;
    private int _turnNumber;

    // Robber / 7
    private int? _robberTileIdx;
    private int? _robberPendingTileIdx;
    private List<int> _robberCandidates = new();

    // Discard
    private Dictionary<int, int> _discardNeed = new();
    private Dictionary<int, int> _discardRemaining = new();

    // Map
    private string _expansionMode = "base";
    private List<HexTile> _tiles = new();
    private List<Port> _ports = new();
    private int _mapRadius = 3;

    // Graph
    private readonly List<GraphVertex> _vertices = new();
    private readonly List<GraphEdge> _edges = new();
    private readonly Dictionary<(int, int), int> _vertexByKey = new();
    private readonly Dictionary<(int, int), int> _edgeByKey = new();

    // Buildings & roads
    private readonly Dictionary<int, Building> _buildings = new();
    private readonly Dictionary<int, int> _roads = new(); // edge_id -> owner seat

    // Player resources
    private readonly Dictionary<int, Dictionary<string, int>> _res = new();

    // Bank
    private Dictionary<string, int> _bank = new();

    // Dev cards
    private List<string> _devDeck = new();
    private readonly Dictionary<int, Dictionary<string, int>> _devHand = new();
    private readonly Dictionary<int, int> _devBoughtTurn = new();
    private readonly Dictionary<int, int> _knightsPlayed = new();

    // Awards
    private int? _largestArmyHolder;
    private int? _longestRoadHolder;

    // Bank trade selection
    private string? _tradeGive;
    private string? _tradeGet;

    // Dev-action transient state
    private int _freeRoadsLeft;
    private int _yopLeft;
    private bool _monopolyPending;
    private bool _devPlayedThisTurn;

    private int? _winner;
    private string? _pendingBuild;

    private string _lastEvent = "";
    private int? _lastRoll;
    private (int, int)? _lastDice;

    // Dice animation
    private bool _diceRolling;
    private double _diceRollStart;
    private (int, int)? _pendingDice;
    private int? _pendingRollSeat;
    private const double DiceRollDuration = 1.2;
    private double _diceRollElapsed;

    // Player-to-player trade
    private Dictionary<string, object?>? _p2pOffer;
    private string? _p2pGive;
    private string? _p2pGet;

    // Buttons per player
    private readonly Dictionary<int, Dictionary<string, (string Text, bool Enabled)>> _buttons = new();

    // Drawing
    private float _hexSize = 28f;
    private float _drawOffX;
    private float _drawOffY;
    private float _drawSize = 28f;
    private double _totalElapsed;

    // Animations
    private readonly ParticleSystem _particles = new();
    private readonly List<TextPopAnim> _textPops = new();
    private readonly List<PulseRing> _pulseRings = new();
    private readonly List<ScreenFlash> _flashes = new();
    private readonly DiceRollAnimation _diceAnim = new(dieSize: 58, gap: 16, rollDuration: 1.2f, showDuration: 3.5f);
    private int? _animPrevTurn;
    private int? _animPrevWinner;
    private double _animFwTimer;

    // ── Constructor ────────────────────────────────────────────
    public CatanGameSharp(int w, int h, Renderer renderer) : base(w, h, renderer)
    {
        WebUIOnlyPlayerSelect = true;
        BoardOnlyMode = true;
        for (int i = 0; i < 8; i++)
        {
            _res[i] = NewResDict();
            _devHand[i] = new Dictionary<string, int>();
            _devBoughtTurn[i] = -999;
            _knightsPlayed[i] = 0;
        }
        _bank = NewBankDict();
    }

    // ═══════════════════════════════════════════════════════════
    //  Start game
    // ═══════════════════════════════════════════════════════════
    public override void StartGame(List<int> players)
    {
        var seats = players.Where(s => s >= 0 && s <= 7).Distinct().OrderBy(x => x).ToList();
        if (seats.Count < 2) return;

        ActivePlayers = seats;
        _currentTurnSeat = seats[0];

        int n = seats.Count;
        _expansionMode = ExpansionForPlayerCount(n);

        var (tiles, ports, radius) = GenerateMap(n);
        _tiles = tiles;
        _ports = ports;
        _mapRadius = radius;

        BuildGraph();

        _buildings.Clear();
        _roads.Clear();
        foreach (var s in ActivePlayers)
            _res[s] = NewResDict();

        _bank = NewBankDict();
        _turnNumber = 0;
        _discardNeed.Clear();
        _discardRemaining.Clear();

        for (int i = 0; i < 8; i++)
        {
            _devHand[i] = new Dictionary<string, int>();
            _devBoughtTurn[i] = -999;
            _knightsPlayed[i] = 0;
        }
        _largestArmyHolder = null;
        _longestRoadHolder = null;
        InitDevDeck();

        _tradeGive = null;
        _tradeGet = null;
        _freeRoadsLeft = 0;
        _yopLeft = 0;
        _monopolyPending = false;
        _devPlayedThisTurn = false;

        _winner = null;

        // Robber starts on desert if present
        _robberTileIdx = null;
        for (int ti = 0; ti < _tiles.Count; ti++)
        {
            if (_tiles[ti].Kind == "desert") { _robberTileIdx = ti; break; }
        }
        _robberPendingTileIdx = null;
        _robberCandidates.Clear();

        // Initial placement: snake draft
        var order1 = new List<int>(ActivePlayers);
        var order2 = new List<int>(ActivePlayers);
        order2.Reverse();
        _initialOrder = new List<int>(order1);
        _initialOrder.AddRange(order2);
        _initialStep = 0;
        _currentTurnSeat = _initialOrder[0];
        _phase = "initial_settlement";
        _initialLastSettlementVertex = null;
        _rolledThisTurn = false;
        _pendingBuild = null;

        State = "playing";
        _lastEvent = $"Catan started ({n} players, {_expansionMode})";
        _lastRoll = null;

        _diceRolling = false;
        _diceRollStart = 0;
        _diceRollElapsed = 0;
        _pendingDice = null;
        _pendingRollSeat = null;
        _p2pOffer = null;
        _p2pGive = null;
        _p2pGet = null;

        RefreshButtons();
    }

    // ═══════════════════════════════════════════════════════════
    //  HandleClick (web UI)
    // ═══════════════════════════════════════════════════════════
    public override void HandleClick(int playerIdx, string buttonId)
    {
        // Game-specific messages (pointer clicks, etc.)
        if (buttonId.StartsWith("__msg__:"))
        {
            var parts = buttonId.Split(':', 3);
            if (parts.Length >= 2)
            {
                string msgType = parts[1];
                string payload = parts.Length > 2 ? parts[2] : "";

                if (msgType == "catan_pointer")
                {
                    HandlePointerMessage(playerIdx, payload);
                    return;
                }
            }
        }

        if (State != "playing") return;
        if (!ActivePlayers.Contains(playerIdx)) return;
        if (_winner is not null) return;
        if (_diceRolling) return;

        // Discard phase
        if (_phase == "discard")
        {
            if (buttonId.StartsWith("discard:"))
            {
                string res = buttonId.Split(':', 2).Last();
                if (!IsResource(res)) return;
                if (_discardRemaining.GetValueOrDefault(playerIdx) <= 0) return;
                if (GetRes(playerIdx, res) <= 0) return;

                AddRes(playerIdx, res, -1);
                AddBank(res, 1);
                _discardRemaining[playerIdx] = _discardRemaining.GetValueOrDefault(playerIdx) - 1;

                if (_discardRemaining.Values.All(v => v <= 0))
                {
                    _phase = "robber_move";
                    _lastEvent = $"Discards complete. {SeatLabel(_currentTurnSeat ?? 0)}: move the robber.";
                }
            }
            RefreshButtons();
            return;
        }

        if (buttonId == "roll")
        {
            if (!IsMyTurn(playerIdx) || _phase != "main" || _rolledThisTurn) return;
            int a = Rng.Next(1, 7), b = Rng.Next(1, 7);
            _pendingDice = (a, b);
            _pendingRollSeat = playerIdx;
            _diceRolling = true;
            _diceRollStart = 0;
            _diceRollElapsed = 0;
            _diceAnim.Start(new[] { a, b });
            _lastEvent = $"{SeatLabel(playerIdx)} is rolling...";
        }
        else if (buttonId == "end_turn")
        {
            if (!IsMyTurn(playerIdx) || _phase.StartsWith("initial_") || _phase != "main") return;
            AdvanceTurn(playerIdx);
        }
        else if (buttonId == "build_settlement")
        {
            if (!IsMyTurn(playerIdx) || _phase != "main" || !_rolledThisTurn) return;
            if (!CanAfford(playerIdx, new() { ["wood"] = 1, ["brick"] = 1, ["sheep"] = 1, ["wheat"] = 1 })) return;
            _pendingBuild = "settlement";
            _lastEvent = $"{SeatLabel(playerIdx)}: tap a vertex for a settlement";
        }
        else if (buttonId == "build_road")
        {
            if (!IsMyTurn(playerIdx) || _phase != "main" || !_rolledThisTurn) return;
            if (_freeRoadsLeft <= 0 && !CanAfford(playerIdx, new() { ["wood"] = 1, ["brick"] = 1 })) return;
            _pendingBuild = "road";
            _lastEvent = $"{SeatLabel(playerIdx)}: tap an edge for a road";
        }
        else if (buttonId == "build_city")
        {
            if (!IsMyTurn(playerIdx) || _phase != "main" || !_rolledThisTurn) return;
            if (!CanAfford(playerIdx, new() { ["ore"] = 3, ["wheat"] = 2 })) return;
            _pendingBuild = "city";
            _lastEvent = $"{SeatLabel(playerIdx)}: tap your settlement to upgrade";
        }
        else if (buttonId == "cancel_build")
        {
            if (!IsMyTurn(playerIdx)) return;
            _pendingBuild = null;
            _freeRoadsLeft = 0;
        }
        else if (buttonId == "trade_bank")
        {
            if (!IsMyTurn(playerIdx) || _phase != "main" || !_rolledThisTurn || _pendingBuild != null) return;
            _phase = "trade_bank";
            _tradeGive ??= "wood";
            _tradeGet ??= "brick";
            _lastEvent = $"{SeatLabel(playerIdx)}: bank trade";
        }
        else if (buttonId == "trade_player")
        {
            if (!IsMyTurn(playerIdx) || _phase != "main" || !_rolledThisTurn || _pendingBuild != null) return;
            _phase = "trade_player_select";
            _p2pGive ??= "wood";
            _p2pGet ??= "brick";
            _p2pOffer = null;
            _lastEvent = $"{SeatLabel(playerIdx)}: pick a trade partner";
        }
        else if (buttonId == "trade_cancel")
        {
            if (!IsMyTurn(playerIdx)) return;
            if (_phase == "trade_bank") _phase = "main";
            if (_phase.StartsWith("trade_player")) { _phase = "main"; _p2pOffer = null; }
            _tradeGive = null; _tradeGet = null;
            _p2pGive = null; _p2pGet = null;
        }
        else if (buttonId.StartsWith("trade_to:"))
        {
            if (!IsMyTurn(playerIdx) || _phase != "trade_player_select") return;
            if (!int.TryParse(buttonId.AsSpan(9), out int toSeat)) return;
            if (toSeat == playerIdx || !ActivePlayers.Contains(toSeat)) return;
            _phase = "trade_player_offer";
            _p2pOffer = new() { ["from"] = playerIdx, ["to"] = toSeat };
            _lastEvent = $"{SeatLabel(playerIdx)}: offering trade to {SeatLabel(toSeat)}";
        }
        else if (buttonId.StartsWith("p2p_give:"))
        {
            if (!IsMyTurn(playerIdx) || _phase != "trade_player_offer") return;
            string res = buttonId[9..];
            if (IsResource(res)) _p2pGive = res;
        }
        else if (buttonId.StartsWith("p2p_get:"))
        {
            if (!IsMyTurn(playerIdx) || _phase != "trade_player_offer") return;
            string res = buttonId[8..];
            if (IsResource(res)) _p2pGet = res;
        }
        else if (buttonId == "p2p_offer")
        {
            if (!IsMyTurn(playerIdx) || _phase != "trade_player_offer" || _p2pOffer == null) return;
            int toSeat = OfferInt("to");
            string give = _p2pGive ?? "";
            string get2 = _p2pGet ?? "";
            if (!IsResource(give) || !IsResource(get2) || give == get2) return;
            if (GetRes(playerIdx, give) <= 0) return;
            _p2pOffer = new() { ["from"] = playerIdx, ["to"] = toSeat, ["give"] = give, ["get"] = get2 };
            _phase = "trade_player_wait";
            _lastEvent = $"Trade offer sent to {SeatLabel(toSeat)}: you give 1 {give} for 1 {get2}";
        }
        else if (buttonId == "p2p_accept")
        {
            if (_p2pOffer == null || !_phase.StartsWith("trade_player")) return;
            int frm = OfferInt("from"), to = OfferInt("to");
            string give = OfferStr("give"), get2 = OfferStr("get");
            if (playerIdx != to || !IsResource(give) || !IsResource(get2)) return;
            if (GetRes(frm, give) <= 0 || GetRes(to, get2) <= 0) return;
            AddRes(frm, give, -1); AddRes(to, give, 1);
            AddRes(to, get2, -1); AddRes(frm, get2, 1);
            _lastEvent = $"Trade completed: {SeatLabel(frm)} gave 1 {give} for 1 {get2} from {SeatLabel(to)}";

            // Trade animation
            try
            {
                int cx = ScreenW / 2, cy = ScreenH / 2;
                _textPops.Add(new TextPopAnim("🤝 TRADE!", cx, cy - 40, (100, 255, 180), fontSize: 28));
                _pulseRings.Add(new PulseRing(cx, cy, (100, 255, 180), maxRadius: 60, duration: 0.6f));
                _particles.EmitSparkle(cx, cy, (100, 255, 180), 12);
            }
            catch { }

            _p2pOffer = null; _p2pGive = null; _p2pGet = null;
            _phase = "main";
        }
        else if (buttonId == "p2p_decline")
        {
            if (_p2pOffer == null || !_phase.StartsWith("trade_player")) return;
            int to = OfferInt("to"), frm = OfferInt("from");
            if (playerIdx != to) return;
            _lastEvent = $"{SeatLabel(to)} declined trade offer from {SeatLabel(frm)}";
            _p2pOffer = null; _p2pGive = null; _p2pGet = null;
            _phase = "main";
        }
        else if (buttonId.StartsWith("trade_give:"))
        {
            if (!IsMyTurn(playerIdx) || _phase != "trade_bank") return;
            string res = buttonId[11..];
            if (IsResource(res)) _tradeGive = res;
        }
        else if (buttonId.StartsWith("trade_get:"))
        {
            if (!IsMyTurn(playerIdx) || _phase != "trade_bank") return;
            string res = buttonId[10..];
            if (IsResource(res)) _tradeGet = res;
        }
        else if (buttonId == "trade_confirm")
        {
            if (!IsMyTurn(playerIdx) || _phase != "trade_bank") return;
            if (!IsResource(_tradeGive) || !IsResource(_tradeGet) || _tradeGive == _tradeGet) return;
            DoBankTrade(playerIdx, _tradeGive!, _tradeGet!);
        }
        else if (buttonId == "buy_dev")
        {
            if (!IsMyTurn(playerIdx) || _phase != "main" || !_rolledThisTurn || _pendingBuild != null) return;
            if (_devDeck.Count == 0) return;
            if (!CanAfford(playerIdx, new() { ["sheep"] = 1, ["wheat"] = 1, ["ore"] = 1 })) return;
            Spend(playerIdx, new() { ["sheep"] = 1, ["wheat"] = 1, ["ore"] = 1 });
            AddBank("sheep", 1); AddBank("wheat", 1); AddBank("ore", 1);
            string card = _devDeck[^1]; _devDeck.RemoveAt(_devDeck.Count - 1);
            _devHand[playerIdx][card] = _devHand[playerIdx].GetValueOrDefault(card) + 1;
            _devBoughtTurn[playerIdx] = _turnNumber;
            _lastEvent = $"{SeatLabel(playerIdx)} bought a development card";
            UpdateAwardsAndWinner();
        }
        else if (buttonId.StartsWith("play_dev:"))
        {
            if (!IsMyTurn(playerIdx) || _phase != "main" || !_rolledThisTurn || _pendingBuild != null) return;
            string card = buttonId[9..];
            if (_devHand[playerIdx].GetValueOrDefault(card) <= 0) return;
            if (_devBoughtTurn.GetValueOrDefault(playerIdx, -999) == _turnNumber && card != "vp") return;
            if (_devPlayedThisTurn && card != "vp") return;

            switch (card)
            {
                case "knight":
                    _devHand[playerIdx][card]--;
                    _knightsPlayed[playerIdx] = _knightsPlayed.GetValueOrDefault(playerIdx) + 1;
                    _devPlayedThisTurn = true;
                    _phase = "robber_move";
                    _lastEvent = $"{SeatLabel(playerIdx)} played Knight: move the robber.";
                    UpdateAwardsAndWinner();

                    // Knight animation
                    try { int cx = ScreenW / 2, cy = ScreenH / 2; _textPops.Add(new TextPopAnim("⚔️ KNIGHT!", cx, cy - 40, (200, 80, 255), fontSize: 28)); _flashes.Add(new ScreenFlash((200, 80, 255), 30, 0.3f)); }
                    catch { }
                    break;
                case "road_building":
                    _devHand[playerIdx][card]--;
                    _devPlayedThisTurn = true;
                    _freeRoadsLeft = 2;
                    _pendingBuild = "road";
                    _lastEvent = $"{SeatLabel(playerIdx)} played Road Building: place 2 free roads";

                    try { int cx = ScreenW / 2, cy = ScreenH / 2; _textPops.Add(new TextPopAnim("🛤️ ROAD BUILDING!", cx, cy - 40, (180, 140, 80), fontSize: 26)); }
                    catch { }
                    break;
                case "year_of_plenty":
                    _devHand[playerIdx][card]--;
                    _devPlayedThisTurn = true;
                    _yopLeft = 2;
                    _lastEvent = $"{SeatLabel(playerIdx)} played Year of Plenty: pick 2 resources";

                    try { int cx = ScreenW / 2, cy = ScreenH / 2; _textPops.Add(new TextPopAnim("🌾 YEAR OF PLENTY!", cx, cy - 40, (200, 220, 80), fontSize: 26)); _particles.EmitSparkle(cx, cy, (200, 220, 80), 10); }
                    catch { }
                    break;
                case "monopoly":
                    _devHand[playerIdx][card]--;
                    _devPlayedThisTurn = true;
                    _monopolyPending = true;
                    _lastEvent = $"{SeatLabel(playerIdx)} played Monopoly: pick a resource";

                    try { int cx = ScreenW / 2, cy = ScreenH / 2; _textPops.Add(new TextPopAnim("💰 MONOPOLY!", cx, cy - 40, (255, 200, 60), fontSize: 28)); _flashes.Add(new ScreenFlash((255, 200, 60), 35, 0.3f)); }
                    catch { }
                    break;
                default: return;
            }
        }
        else if (buttonId.StartsWith("yop:"))
        {
            if (!IsMyTurn(playerIdx) || _phase != "main" || _yopLeft <= 0) return;
            string res = buttonId[4..];
            if (!IsResource(res) || _bank.GetValueOrDefault(res) <= 0) return;
            AddBank(res, -1);
            AddRes(playerIdx, res, 1);
            _yopLeft--;
            if (_yopLeft <= 0) _lastEvent = $"{SeatLabel(playerIdx)} finished Year of Plenty";
        }
        else if (buttonId.StartsWith("mono:"))
        {
            if (!IsMyTurn(playerIdx) || _phase != "main" || !_monopolyPending) return;
            string res = buttonId[5..];
            if (!IsResource(res)) return;
            int taken = 0;
            foreach (int seat in ActivePlayers)
            {
                if (seat == playerIdx) continue;
                int have = GetRes(seat, res);
                if (have <= 0) continue;
                SetRes(seat, res, 0);
                taken += have;
            }
            AddRes(playerIdx, res, taken);
            _monopolyPending = false;
            _lastEvent = $"{SeatLabel(playerIdx)} monopolized {res} (+{taken})";
        }
        else if (buttonId.StartsWith("steal:"))
        {
            if (!IsMyTurn(playerIdx) || _phase != "robber_steal") return;
            if (!int.TryParse(buttonId.AsSpan(6), out int target)) return;
            if (!_robberCandidates.Contains(target)) return;
            DoRobberSteal(playerIdx, target);
        }
        else if (buttonId == "skip_steal")
        {
            if (!IsMyTurn(playerIdx) || _phase != "robber_steal") return;
            _phase = "main";
            _robberCandidates.Clear();
            _robberPendingTileIdx = null;
            _lastEvent = $"{SeatLabel(playerIdx)} skipped stealing";
        }

        RefreshButtons();
    }

    // ── HandleMessage (pointer clicks from web) ────────────────
    public override void HandleMessage(int playerIdx, string type, string json)
    {
        if (type is "catan_pointer" or "catan_pointer_click")
        {
            HandlePointerMessage(playerIdx, json);
        }
    }

    private void HandlePointerMessage(int playerIdx, string payload)
    {
        if (State != "playing" || !ActivePlayers.Contains(playerIdx) || !IsMyTurn(playerIdx)) return;

        // payload expected: JSON {"x":..,"y":..} or plain "x,y"
        int xPx = 0, yPx = 0;
        try
        {
            var trimmed = payload.Trim();
            if (trimmed.StartsWith('{'))
            {
                using var doc = System.Text.Json.JsonDocument.Parse(trimmed);
                xPx = doc.RootElement.GetProperty("x").GetInt32();
                yPx = doc.RootElement.GetProperty("y").GetInt32();
            }
            else if (trimmed.Contains(','))
            {
                var xy = trimmed.Split(',');
                xPx = int.Parse(xy[0].Trim());
                yPx = int.Parse(xy[1].Trim());
            }
            else return;
        }
        catch { return; }

        HandlePointerClick(playerIdx, xPx, yPx);
    }

    private void HandlePointerClick(int playerIdx, int xPx, int yPx)
    {
        if (State != "playing" || !ActivePlayers.Contains(playerIdx) || !IsMyTurn(playerIdx)) return;
        float size = _drawSize;
        if (size <= 0) return;

        float lx = (xPx - _drawOffX) / size;
        float ly = (yPx - _drawOffY) / size;

        // Robber move phase
        if (_phase == "robber_move")
        {
            int? ti = NearestLandTile(lx, ly);
            if (ti == null) return;
            if (_robberTileIdx is int rt && rt == ti.Value) return;
            _robberTileIdx = ti.Value;
            _robberPendingTileIdx = null;
            var cand = PlayersAdjacentToTile(ti.Value, playerIdx);
            _robberCandidates = cand;
            if (cand.Count == 0)
            {
                _phase = "main";
                _lastEvent = $"{SeatLabel(playerIdx)} moved the robber";
                UpdateAwardsAndWinner();
                RefreshButtons();
                return;
            }
            if (cand.Count == 1) { DoRobberSteal(playerIdx, cand[0]); return; }
            _phase = "robber_steal";
            _lastEvent = $"{SeatLabel(playerIdx)}: choose someone to steal from";
            RefreshButtons();
            return;
        }

        // Initial settlement
        if (_phase == "initial_settlement")
        {
            int? vid = NearestVertex(lx, ly);
            if (vid == null || !CanPlaceSettlement(playerIdx, vid.Value, initial: true)) return;
            PlaceBuilding(playerIdx, vid.Value, "settlement");

            if (_initialStep >= ActivePlayers.Count)
                GrantStartingResources(playerIdx, vid.Value);

            _initialLastSettlementVertex = vid.Value;
            _phase = "initial_road";
            _lastEvent = $"{SeatLabel(playerIdx)} placed a settlement; now place an adjacent road";
            RefreshButtons();
            return;
        }

        // Initial road
        if (_phase == "initial_road")
        {
            int? eid = NearestEdge(lx, ly);
            if (eid == null || !CanPlaceRoad(playerIdx, eid.Value, initial: true)) return;
            _roads[eid.Value] = playerIdx;
            _lastEvent = $"{SeatLabel(playerIdx)} placed a road";
            AdvanceInitialTurn();
            RefreshButtons();
            return;
        }

        // Main game builds
        if (_phase == "main" && _pendingBuild != null)
        {
            string kind = _pendingBuild;
            if (kind == "settlement")
            {
                int? vid = NearestVertex(lx, ly);
                if (vid == null || !CanPlaceSettlement(playerIdx, vid.Value, initial: false)) return;
                Spend(playerIdx, new() { ["wood"] = 1, ["brick"] = 1, ["sheep"] = 1, ["wheat"] = 1 });
                foreach (var r in new[] { "wood", "brick", "sheep", "wheat" }) AddBank(r, 1);
                PlaceBuilding(playerIdx, vid.Value, "settlement");
                _pendingBuild = null;
                _lastEvent = $"{SeatLabel(playerIdx)} built a settlement";
                UpdateAwardsAndWinner();
                RefreshButtons();
                EmitBuildAnimation(playerIdx, vid.Value, "Settlement!");
                return;
            }
            if (kind == "road")
            {
                int? eid = NearestEdge(lx, ly);
                if (eid == null || !CanPlaceRoad(playerIdx, eid.Value, initial: false)) return;
                if (_freeRoadsLeft > 0) _freeRoadsLeft--;
                else
                {
                    Spend(playerIdx, new() { ["wood"] = 1, ["brick"] = 1 });
                    AddBank("wood", 1); AddBank("brick", 1);
                }
                _roads[eid.Value] = playerIdx;
                if (_freeRoadsLeft <= 0) _pendingBuild = null;
                _lastEvent = $"{SeatLabel(playerIdx)} built a road";
                UpdateAwardsAndWinner();
                RefreshButtons();
                EmitEdgeBuildAnimation(playerIdx, eid.Value, "Road!");
                return;
            }
            if (kind == "city")
            {
                int? vid = NearestVertex(lx, ly);
                if (vid == null || !CanUpgradeCity(playerIdx, vid.Value)) return;
                Spend(playerIdx, new() { ["ore"] = 3, ["wheat"] = 2 });
                AddBank("ore", 3); AddBank("wheat", 2);
                _buildings[vid.Value] = new Building(playerIdx, "city");
                _pendingBuild = null;
                _lastEvent = $"{SeatLabel(playerIdx)} upgraded to a city";
                UpdateAwardsAndWinner();
                RefreshButtons();
                EmitBuildAnimation(playerIdx, vid.Value, "City!");
                return;
            }
        }
    }

    // ═══════════════════════════════════════════════════════════
    //  Snapshot / Buttons
    // ═══════════════════════════════════════════════════════════

    public override Dictionary<string, object?> GetSnapshot(int playerIdx)
    {
        var tilesList = _tiles.Select(t => (object?)new Dictionary<string, object?>
        {
            ["q"] = t.Q, ["r"] = t.R, ["kind"] = t.Kind,
            ["number"] = t.Number.HasValue ? (object?)t.Number.Value : null,
        }).ToList();

        var portsList = _ports.Select(p => (object?)new Dictionary<string, object?>
        {
            ["q"] = p.Q, ["r"] = p.R, ["kind"] = p.Kind,
        }).ToList();

        bool isActive = ActivePlayers.Contains(playerIdx);
        Dictionary<string, int>? yourRes = null;
        if (isActive && _res.TryGetValue(playerIdx, out var rv))
            yourRes = new Dictionary<string, int>(rv);

        var snap = new Dictionary<string, object?>
        {
            ["state"] = State,
            ["active_players"] = ActivePlayers.ToList(),
            ["current_turn_seat"] = _currentTurnSeat,
            ["expansion_mode"] = _expansionMode,
            ["map_radius"] = _mapRadius,
            ["ports"] = portsList,
            ["phase"] = _phase,
            ["rolled"] = _rolledThisTurn,
            ["pending_build"] = _pendingBuild,
            ["your_resources"] = (object?)yourRes,
            ["robber_tile_idx"] = _robberTileIdx,
            ["robber_candidates"] = _phase == "robber_steal" ? _robberCandidates.ToList() : new List<int>(),
            ["bank"] = new Dictionary<string, int>(_bank),
            ["dev"] = isActive ? new Dictionary<string, int>(_devHand.GetValueOrDefault(playerIdx, new())) : new Dictionary<string, int>(),
            ["knights_played"] = isActive ? _knightsPlayed.GetValueOrDefault(playerIdx) : 0,
            ["vp"] = isActive ? VpFor(playerIdx) : 0,
            ["largest_army_holder"] = _largestArmyHolder,
            ["longest_road_holder"] = _longestRoadHolder,
            ["winner"] = _winner,
            ["last_event"] = string.IsNullOrEmpty(_lastEvent) ? null : _lastEvent,
            ["last_roll"] = _lastRoll,
            ["dice_rolling"] = _diceRolling,
            ["tiles"] = tilesList,
        };

        return new Dictionary<string, object?> { ["catan"] = snap };
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

    // ═══════════════════════════════════════════════════════════
    //  Update / Draw
    // ═══════════════════════════════════════════════════════════

    public override void Update(double dt)
    {
        float d = Math.Clamp((float)dt, 0f, 0.2f);

        // Animations
        _particles.Update(d);
        _diceAnim.Update((float)_totalElapsed);
        for (int i = _textPops.Count - 1; i >= 0; i--) { _textPops[i].Update(d); if (_textPops[i].Done) _textPops.RemoveAt(i); }
        for (int i = _pulseRings.Count - 1; i >= 0; i--) { _pulseRings[i].Update(d); if (_pulseRings[i].Done) _pulseRings.RemoveAt(i); }
        for (int i = _flashes.Count - 1; i >= 0; i--) { _flashes[i].Update(d); if (_flashes[i].Done) _flashes.RemoveAt(i); }

        // Turn-change pulse
        var currTurn = _currentTurnSeat;
        if (State == "playing" && currTurn is int ct && _animPrevTurn is int pt && ct != pt)
        {
            int cx = ScreenW / 2, cy = ScreenH / 2;
            var col = AnimPalette.Rainbow[ct % AnimPalette.Rainbow.Length];
            _pulseRings.Add(new PulseRing(cx, cy, col, maxRadius: Math.Min(ScreenW, ScreenH) / 5, duration: 0.8f));
            _particles.EmitSparkle(cx, cy, col, 18);
            _flashes.Add(new ScreenFlash(col, 40, 0.3f));
        }
        _animPrevTurn = currTurn;

        // Winner fireworks
        if (_winner is int w && w != (_animPrevWinner ?? -1))
        {
            _animPrevWinner = w;
            int cx = ScreenW / 2, cy = ScreenH / 2;
            for (int i2 = 0; i2 < 10; i2++)
                _particles.EmitFirework(cx + Rng.Next(-150, 151), cy + Rng.Next(-100, 101), AnimPalette.Rainbow);
            _flashes.Add(new ScreenFlash((255, 220, 80), 80, 1.2f));
            _textPops.Add(new TextPopAnim($"Winner: {SeatLabel(w)}!", cx, cy - 70, (255, 220, 80), fontSize: 40));
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

        // Dice animation
        if (!_diceRolling) return;
        _diceRollElapsed += dt;
        if (_diceRollElapsed < DiceRollDuration) return;

        // Resolve roll
        _diceRolling = false;
        if (_pendingDice is not (int da, int db)) { _pendingDice = null; _pendingRollSeat = null; return; }

        _lastDice = (da, db);
        _lastRoll = da + db;

        // Dice result feedback
        int fcx = ScreenW / 2, fcy = ScreenH / 2;
        if (_lastRoll == 7)
        {
            _flashes.Add(new ScreenFlash((200, 80, 255), 40, 0.6f));
            _textPops.Add(new TextPopAnim("ROBBER!", fcx, fcy - 50, (200, 80, 255), fontSize: 32));
            _particles.EmitSparkle(fcx, fcy, (200, 80, 255), 20);
        }
        else
        {
            _textPops.Add(new TextPopAnim($"Rolled {_lastRoll}", fcx, fcy - 50, (255, 235, 120), fontSize: 28));
            _particles.EmitSparkle(fcx, fcy, (255, 235, 120), 12);
        }

        int seat = _pendingRollSeat ?? _currentTurnSeat ?? 0;
        _pendingDice = null;
        _pendingRollSeat = null;
        _lastEvent = $"{SeatLabel(seat)} rolled {_lastRoll} ({da}+{db})";
        _rolledThisTurn = true;

        if (_lastRoll == 7)
            HandleRollSeven(seat);
        else
        {
            DistributeResourcesForRoll(_lastRoll.Value);
            UpdateAwardsAndWinner();
        }
        RefreshButtons();
    }

    public override void Draw(Renderer r, int width, int height, double dt)
    {
        _totalElapsed += dt;
        if (State == "player_select") { base.Draw(r, width, height, dt); return; }

        CardRendering.DrawGameBackground(r, width, height, "catan");
        RainbowTitle.Draw(r, "CATAN", width);

        string subtitle = State == "playing"
            ? $"Expansion: {_expansionMode}  |  Players: {ActivePlayers.Count}"
            : "Select players in Web UI";
        r.DrawText(subtitle, 16, 50, 14, (200, 200, 200), anchorX: "left", anchorY: "top");

        if (State != "playing") return;

        RecomputeLayout(width, height);

        int headerH = 54;
        int cy0 = (headerH + (height - headerH) / 2);
        int cx0 = width / 2;
        float size = _hexSize;

        // Sort tiles: water first
        var sortedTiles = _tiles.OrderBy(t => t.Kind == "water" ? 0 : 1).ToList();

        // Compute draw offset from center
        var centers = _tiles.Select(t => AxialToPixel(t.Q, t.R, size)).ToList();
        if (centers.Count == 0) return;
        float minX = centers.Min(c => c.x), maxX = centers.Max(c => c.x);
        float minY = centers.Min(c => c.y), maxY = centers.Max(c => c.y);
        float offX = cx0 - (minX + maxX) / 2f;
        float offY = cy0 - (minY + maxY) / 2f;
        _drawOffX = offX;
        _drawOffY = offY;
        _drawSize = size;

        // Port lookup
        var portByCoord = new Dictionary<(int, int), string>();
        foreach (var p in _ports) portByCoord[(p.Q, p.R)] = p.Kind;

        // Draw tiles as hexagons (pointy-top)
        foreach (var t in sortedTiles)
        {
            var (px, py) = AxialToPixel(t.Q, t.R, size);
            float tcx = px + offX, tcy = py + offY;

            var col = KindColor.GetValueOrDefault(t.Kind, (180, 180, 180));
            var dark = (Math.Max(0, (int)(col.Item1 * 0.72)), Math.Max(0, (int)(col.Item2 * 0.72)), Math.Max(0, (int)(col.Item3 * 0.72)));
            var light = (Math.Min(255, (int)(col.Item1 * 1.08)), Math.Min(255, (int)(col.Item2 * 1.08)), Math.Min(255, (int)(col.Item3 * 1.08)));

            int alpha = t.Kind != "water" ? 235 : 190;
            var outerHex = HexPoints(tcx, tcy, size * 0.95f);
            var innerHex = HexPoints(tcx, tcy, size * 0.85f);
            r.DrawPolygon(dark, outerHex, alpha: alpha);
            r.DrawPolygon(light, innerHex, alpha: alpha);
            r.DrawPolygon((15, 18, 22), outerHex, width: 2, alpha: 200);

            bool isPort = t.Kind == "water" && portByCoord.ContainsKey((t.Q, t.R));
            string label = KindEmoji.GetValueOrDefault(t.Kind, "?");
            if (!isPort || t.Kind != "water")
            {
                r.DrawText(label, (int)tcx, (int)tcy - 2, Math.Max(14, (int)(size * 0.45)),
                    (255, 255, 255), anchorX: "center", anchorY: "center");
            }

            if (t.Number is int num && t.Kind is not "water" and not "desert" and not "volcano")
            {
                r.DrawCircle((245, 235, 210), ((int)tcx, (int)(tcy + size * 0.35)), Math.Max(10, (int)(size * 0.26)), alpha: 220);
                r.DrawText(num.ToString(), (int)tcx, (int)(tcy + size * 0.35), Math.Max(12, (int)(size * 0.32)),
                    (30, 30, 30), anchorX: "center", anchorY: "center");
            }

            if (isPort)
            {
                string pk = portByCoord[(t.Q, t.R)];
                string portLabel = PortEmoji.GetValueOrDefault(pk, "⚓");
                r.DrawText(portLabel, (int)tcx, (int)(tcy - size * 0.05), Math.Max(12, (int)(size * 0.35)),
                    (255, 255, 255), anchorX: "center", anchorY: "center");
            }
        }

        // Draw vertex/edge indicators so players can see clickable intersections
        bool showVertices = _phase == "initial_settlement" || (_phase == "main" && _pendingBuild is "settlement" or "city");
        bool showEdges = _phase == "initial_road" || (_phase == "main" && _pendingBuild == "road");
        if (showVertices)
        {
            foreach (var v in _vertices)
            {
                float vx = v.X * size + offX, vy = v.Y * size + offY;
                // Pulsing alpha for visibility
                int pulseAlpha = 40 + (int)(25 * MathF.Sin((float)(_totalElapsed * 3.0 + v.Id * 0.5)));
                r.DrawCircle((255, 255, 255), ((int)vx, (int)vy), Math.Max(4, (int)(size * 0.12)), alpha: pulseAlpha);
            }
        }
        if (showEdges)
        {
            foreach (var e in _edges)
            {
                if (e.A < 0 || e.A >= _vertices.Count || e.B < 0 || e.B >= _vertices.Count) continue;
                var va = _vertices[e.A];
                var vb = _vertices[e.B];
                float ax2 = va.X * size + offX, ay2 = va.Y * size + offY;
                float bx2 = vb.X * size + offX, by2 = vb.Y * size + offY;
                float mx = (ax2 + bx2) / 2, my = (ay2 + by2) / 2;
                int pulseAlpha = 30 + (int)(20 * MathF.Sin((float)(_totalElapsed * 3.0 + e.Id * 0.5)));
                r.DrawCircle((220, 180, 100), ((int)mx, (int)my), Math.Max(3, (int)(size * 0.08)), alpha: pulseAlpha);
            }
        }

        // Draw roads
        foreach (var (eid, owner) in _roads)
        {
            if (eid < 0 || eid >= _edges.Count) continue;
            var e = _edges[eid];
            if (e.A < 0 || e.A >= _vertices.Count || e.B < 0 || e.B >= _vertices.Count) continue;
            var va = _vertices[e.A];
            var vb = _vertices[e.B];
            float ax = va.X * size + offX, ay = va.Y * size + offY;
            float bx = vb.X * size + offX, by = vb.Y * size + offY;
            var roadCol = PlayerPalette[owner % PlayerPalette.Length];
            r.DrawLine(roadCol, ((int)ax, (int)ay), ((int)bx, (int)by), width: Math.Max(3, (int)(size * 0.12)));
        }

        // Draw buildings
        foreach (var (vid, b) in _buildings)
        {
            if (vid < 0 || vid >= _vertices.Count) continue;
            var v = _vertices[vid];
            float bx = v.X * size + offX, by = v.Y * size + offY;
            var bCol = PlayerPalette[b.Owner % PlayerPalette.Length];
            int bRad = b.Kind == "city" ? Math.Max(8, (int)(size * 0.22)) : Math.Max(6, (int)(size * 0.16));
            r.DrawCircle(bCol, ((int)bx, (int)by), bRad, alpha: 220);
            r.DrawCircle((0, 0, 0), ((int)bx, (int)by), bRad, width: 2, alpha: 180);
            string em = b.Kind == "city" ? "C" : "S";
            r.DrawText(em, (int)bx, (int)by, Math.Max(10, (int)(size * 0.3)),
                (255, 255, 255), anchorX: "center", anchorY: "center");
        }

        // Robber
        if (_robberTileIdx is int rbi && rbi >= 0 && rbi < _tiles.Count)
        {
            var rt = _tiles[rbi];
            if (rt.Kind != "water")
            {
                var (rpx, rpy) = AxialToPixel(rt.Q, rt.R, size);
                float rcx = rpx + offX, rcy2 = rpy + offY;
                r.DrawCircle((0, 0, 0), ((int)rcx, (int)rcy2), Math.Max(10, (int)(size * 0.32)), alpha: 140);
                r.DrawText("R", (int)rcx, (int)rcy2, Math.Max(14, (int)(size * 0.45)),
                    (235, 235, 235), anchorX: "center", anchorY: "center");
            }
        }

        // Dice display (animated)
        if (_diceAnim.Visible)
        {
            _diceAnim.Draw(r, width - 100, 80, _lastRoll is int lr2 ? $"= {lr2}" : "");
        }

        // Event line
        if (!string.IsNullOrEmpty(_lastEvent))
        {
            int ew = Math.Max(200, _lastEvent.Length * 8);
            r.DrawRect((0, 0, 0), (12, 68, ew, 24), alpha: 130);
            r.DrawText(_lastEvent, 20, 80, 12, (200, 210, 220), anchorX: "left", anchorY: "center");
        }

        // Seat info
        DrawSeatInfo(r, width, height);

        // Winner overlay
        if (_winner is int wi)
        {
            r.DrawRect((0, 0, 0), (0, 0, width, height), alpha: 150);
            int bw = Math.Min(600, width * 55 / 100), bh = 160;
            int bxc = width / 2 - bw / 2, byc = height / 2 - bh / 2;
            r.DrawRect((10, 10, 18), (bxc, byc, bw, bh), alpha: 220);
            r.DrawRect((255, 215, 0), (bxc, byc, bw, bh), width: 4, alpha: 200);
            r.DrawText($"Winner: {SeatLabel(wi)}", width / 2, height / 2, 36, (255, 240, 180), anchorX: "center", anchorY: "center");
        }

        // Footer
        r.DrawText($"Map radius: {_mapRadius}  |  Ports: {_ports.Count}", width - 16, height - 16,
            11, (190, 190, 190), anchorX: "right", anchorY: "bottom");

        // Animations
        _particles.Draw(r);
        foreach (var pr in _pulseRings) pr.Draw(r);
        foreach (var fl in _flashes) fl.Draw(r, width, height);
        foreach (var tp in _textPops) tp.Draw(r);
    }

    private void DrawSeatInfo(Renderer r, int w, int h)
    {
        int y = 100;
        foreach (var seat in ActivePlayers)
        {
            var pcol = GameConfig.PlayerColors[seat % GameConfig.PlayerColors.Length];
            bool isTurn = _currentTurnSeat == seat;
            var nameCol = isTurn ? (255, 240, 100) : pcol;
            int vp = VpFor(seat);
            string info = $"{PlayerName(seat)} VP:{vp}";
            if (_res.TryGetValue(seat, out var res))
            {
                int total = res.Values.Sum();
                info += $" R:{total}";
            }
            r.DrawCircle(pcol, (16, y + 6), 5, alpha: 200);
            r.DrawText(info, 28, y, 11, nameCol, anchorX: "left", anchorY: "top");
            y += 16;
        }
    }

    // ═══════════════════════════════════════════════════════════
    //  Internal helpers
    // ═══════════════════════════════════════════════════════════

    private string SeatLabel(int seat) => PlayerName(seat);
    private bool IsMyTurn(int seat) => _currentTurnSeat is int ct && ct == seat;
    private static bool IsResource(string? s) => s is "wood" or "brick" or "sheep" or "wheat" or "ore";

    private static Dictionary<string, int> NewResDict() =>
        new() { ["wood"] = 0, ["brick"] = 0, ["sheep"] = 0, ["wheat"] = 0, ["ore"] = 0 };

    private static Dictionary<string, int> NewBankDict() =>
        new() { ["wood"] = 19, ["brick"] = 19, ["sheep"] = 19, ["wheat"] = 19, ["ore"] = 19 };

    private int GetRes(int seat, string res) => _res.GetValueOrDefault(seat)?.GetValueOrDefault(res) ?? 0;

    private void SetRes(int seat, string res, int val)
    {
        if (!_res.ContainsKey(seat)) _res[seat] = NewResDict();
        _res[seat][res] = val;
    }

    private void AddRes(int seat, string res, int delta)
    {
        if (!_res.ContainsKey(seat)) _res[seat] = NewResDict();
        _res[seat][res] = Math.Max(0, _res[seat].GetValueOrDefault(res) + delta);
    }

    private void AddBank(string res, int delta) => _bank[res] = Math.Max(0, _bank.GetValueOrDefault(res) + delta);

    private int OfferInt(string key)
    {
        if (_p2pOffer != null && _p2pOffer.TryGetValue(key, out var v) && v is int i) return i;
        return -1;
    }

    private string OfferStr(string key)
    {
        if (_p2pOffer != null && _p2pOffer.TryGetValue(key, out var v) && v is string s) return s;
        return "";
    }

    private void AdvanceTurn(int playerIdx)
    {
        int i = ActivePlayers.IndexOf(playerIdx);
        if (i < 0) return;
        _currentTurnSeat = ActivePlayers[(i + 1) % ActivePlayers.Count];
        _lastEvent = $"Turn: {SeatLabel(_currentTurnSeat.Value)}";
        _rolledThisTurn = false;
        _pendingBuild = null;
        _robberPendingTileIdx = null;
        _robberCandidates.Clear();
        _tradeGive = null; _tradeGet = null;
        _p2pOffer = null; _p2pGive = null; _p2pGet = null;
        _freeRoadsLeft = 0; _yopLeft = 0;
        _monopolyPending = false; _devPlayedThisTurn = false;
        _turnNumber++;
    }

    // ── Resource helpers ───────────────────────────────────────

    private bool CanAfford(int seat, Dictionary<string, int> cost)
    {
        foreach (var (k, v) in cost)
            if (GetRes(seat, k) < v) return false;
        return true;
    }

    private void Spend(int seat, Dictionary<string, int> cost)
    {
        foreach (var (k, v) in cost)
            AddRes(seat, k, -v);
    }

    // ── Placement / building ───────────────────────────────────

    private void PlaceBuilding(int seat, int vid, string kind) =>
        _buildings[vid] = new Building(seat, kind);

    private bool CanPlaceSettlement(int seat, int vid, bool initial)
    {
        if (_buildings.ContainsKey(vid)) return false;
        if (vid < 0 || vid >= _vertices.Count) return false;
        var v = _vertices[vid];
        foreach (int nb in v.Neighbors)
            if (_buildings.ContainsKey(nb)) return false;

        if (initial) return true;

        // Must connect to own network
        foreach (var (eid, owner) in _roads)
        {
            if (owner != seat) continue;
            var e = _edges[eid];
            if (e.A == vid || e.B == vid) return true;
        }
        return false;
    }

    private bool CanUpgradeCity(int seat, int vid)
    {
        if (!_buildings.TryGetValue(vid, out var b)) return false;
        return b.Owner == seat && b.Kind == "settlement";
    }

    private bool CanPlaceRoad(int seat, int eid, bool initial)
    {
        if (_roads.ContainsKey(eid)) return false;
        if (eid < 0 || eid >= _edges.Count) return false;
        var e = _edges[eid];
        int a = e.A, b = e.B;

        if (initial)
        {
            if (_initialLastSettlementVertex is not int sv) return false;
            return a == sv || b == sv;
        }

        // Must connect to existing road/building
        foreach (int vid2 in new[] { a, b })
        {
            if (_buildings.TryGetValue(vid2, out var bb) && bb.Owner == seat) return true;
        }
        foreach (var (rid, owner) in _roads)
        {
            if (owner != seat) continue;
            var rr = _edges[rid];
            if (a == rr.A || a == rr.B || b == rr.A || b == rr.B) return true;
        }
        return false;
    }

    private void AdvanceInitialTurn()
    {
        _initialLastSettlementVertex = null;
        _initialStep++;
        if (_initialStep >= _initialOrder.Count)
        {
            _phase = "main";
            _currentTurnSeat = ActivePlayers[0];
            _rolledThisTurn = false;
            _pendingBuild = null;
            _lastEvent = $"Main phase: {SeatLabel(_currentTurnSeat.Value)} to roll";
            UpdateAwardsAndWinner();
            return;
        }
        _currentTurnSeat = _initialOrder[_initialStep];
        _phase = "initial_settlement";
        _lastEvent = $"Initial placement: {SeatLabel(_currentTurnSeat.Value)} place a settlement";
    }

    private void GrantStartingResources(int seat, int vid)
    {
        if (vid < 0 || vid >= _vertices.Count) return;
        var v = _vertices[vid];
        foreach (int ti in v.AdjacentTiles)
        {
            if (ti < 0 || ti >= _tiles.Count) continue;
            var t = _tiles[ti];
            if (t.Kind is "water" or "desert" or "volcano") continue;
            string? rk = TileResource(t.Kind);
            if (rk == null) continue;
            if (rk == "gold") rk = "wheat";
            if (_bank.GetValueOrDefault(rk) <= 0) continue;
            AddBank(rk, -1);
            AddRes(seat, rk, 1);
        }
    }

    // ── Distribution / Robber ──────────────────────────────────

    private void DistributeResourcesForRoll(int roll)
    {
        for (int ti = 0; ti < _tiles.Count; ti++)
        {
            if (_robberTileIdx is int rbi && rbi == ti) continue;
            var t = _tiles[ti];
            if (t.Kind is "water" or "desert" or "volcano") continue;
            if (t.Number is not int num || num != roll) continue;

            string? resKind = TileResource(t.Kind);
            if (resKind == null) continue;

            foreach (var (vid, b) in _buildings)
            {
                if (vid < 0 || vid >= _vertices.Count) continue;
                var v = _vertices[vid];
                if (!v.AdjacentTiles.Contains(ti)) continue;
                int owner = b.Owner;
                int mult = b.Kind == "city" ? 2 : 1;

                if (resKind == "gold")
                {
                    int give = Math.Min(mult, _bank.GetValueOrDefault("wheat"));
                    if (give > 0) { AddBank("wheat", -give); AddRes(owner, "wheat", give); }
                }
                else
                {
                    int give = Math.Min(mult, _bank.GetValueOrDefault(resKind));
                    if (give > 0) { AddBank(resKind, -give); AddRes(owner, resKind, give); }
                }
            }
        }
    }

    private void HandleRollSeven(int roller)
    {
        _discardNeed.Clear();
        _discardRemaining.Clear();
        var affected = new List<string>();
        foreach (int seat in ActivePlayers)
        {
            int total = _res.GetValueOrDefault(seat)?.Values.Sum() ?? 0;
            if (total <= 7) continue;
            int need = total / 2;
            if (need <= 0) continue;
            _discardNeed[seat] = need;
            _discardRemaining[seat] = need;
            affected.Add($"{SeatLabel(seat)} ({need})");
        }

        _pendingBuild = null;
        _robberCandidates.Clear();
        _robberPendingTileIdx = null;

        if (affected.Count > 0)
        {
            _phase = "discard";
            _lastEvent = "7 rolled. Discard half: " + string.Join(", ", affected) + $". Then {SeatLabel(roller)} moves the robber.";
        }
        else
        {
            _phase = "robber_move";
            _lastEvent = $"7 rolled. {SeatLabel(roller)}: move the robber.";
        }
    }

    private List<int> PlayersAdjacentToTile(int tileIdx, int excludeSeat)
    {
        var owners = new HashSet<int>();
        foreach (var (vid, b) in _buildings)
        {
            if (b.Owner == excludeSeat) continue;
            if (vid < 0 || vid >= _vertices.Count) continue;
            if (_vertices[vid].AdjacentTiles.Contains(tileIdx))
                owners.Add(b.Owner);
        }
        return owners.OrderBy(x => x).ToList();
    }

    private void DoRobberSteal(int thief, int target)
    {
        var inv = _res.GetValueOrDefault(target);
        if (inv == null) { FinishRobberNoSteal(thief, target); return; }
        var pool = new List<string>();
        foreach (var r2 in Resource)
        {
            int have = inv.GetValueOrDefault(r2);
            for (int i = 0; i < have; i++) pool.Add(r2);
        }
        if (pool.Count == 0) { FinishRobberNoSteal(thief, target); return; }

        string k = pool[Rng.Next(pool.Count)];
        AddRes(target, k, -1);
        AddRes(thief, k, 1);
        _phase = "main";
        _robberCandidates.Clear();
        _robberPendingTileIdx = null;
        _lastEvent = $"{SeatLabel(thief)} stole 1 {k} from {SeatLabel(target)}";
        UpdateAwardsAndWinner();
        RefreshButtons();
    }

    private void FinishRobberNoSteal(int thief, int target)
    {
        _phase = "main";
        _robberCandidates.Clear();
        _robberPendingTileIdx = null;
        _lastEvent = $"{SeatLabel(thief)} tried to steal from {SeatLabel(target)}, but they had nothing";
        RefreshButtons();
    }

    // ── Dev cards ──────────────────────────────────────────────

    private void InitDevDeck()
    {
        var deck = new List<string>();
        for (int i = 0; i < 14; i++) deck.Add("knight");
        for (int i = 0; i < 5; i++) deck.Add("vp");
        for (int i = 0; i < 2; i++) deck.Add("road_building");
        for (int i = 0; i < 2; i++) deck.Add("year_of_plenty");
        for (int i = 0; i < 2; i++) deck.Add("monopoly");
        ShuffleList(deck);
        _devDeck = deck;
    }

    private void ShuffleList<T>(List<T> list)
    {
        for (int i = list.Count - 1; i > 0; i--)
        {
            int j = Rng.Next(i + 1);
            (list[i], list[j]) = (list[j], list[i]);
        }
    }

    // ── Victory points ─────────────────────────────────────────

    private int VpFor(int seat)
    {
        int vp = 0;
        foreach (var b in _buildings.Values)
        {
            if (b.Owner != seat) continue;
            vp += b.Kind == "city" ? 2 : 1;
        }
        vp += _devHand.GetValueOrDefault(seat)?.GetValueOrDefault("vp") ?? 0;
        if (_largestArmyHolder == seat) vp += 2;
        if (_longestRoadHolder == seat) vp += 2;
        return vp;
    }

    private void UpdateAwardsAndWinner()
    {
        // Largest army: >= 3 knights, strictly greatest
        int bestArmy = 0; int? bestSeat = null;
        foreach (int s in ActivePlayers)
        {
            int k = _knightsPlayed.GetValueOrDefault(s);
            if (k >= 3 && k > bestArmy) { bestArmy = k; bestSeat = s; }
        }
        _largestArmyHolder = bestSeat;

        // Longest road: >= 5
        var (lrSeat, lrLen) = ComputeLongestRoadHolder();
        _longestRoadHolder = lrLen >= 5 ? lrSeat : null;

        // Winner: first to 10+ VP
        if (_winner == null)
        {
            foreach (int s in ActivePlayers)
            {
                if (VpFor(s) >= 10)
                {
                    _winner = s;
                    _lastEvent = $"{SeatLabel(s)} wins!";
                    break;
                }
            }
        }
    }

    private (int? Seat, int Length) ComputeLongestRoadHolder()
    {
        int? bestSeat = null;
        int bestLen = 0;
        foreach (int s in ActivePlayers)
        {
            int ln = LongestRoadForSeat(s);
            if (ln > bestLen) { bestLen = ln; bestSeat = s; }
        }
        return (bestSeat, bestLen);
    }

    private int LongestRoadForSeat(int seat)
    {
        var seatEdgeIds = _roads.Where(kv => kv.Value == seat).Select(kv => kv.Key).ToList();
        if (seatEdgeIds.Count == 0) return 0;

        var blockedVertices = new HashSet<int>();
        foreach (var (vid, b) in _buildings)
            if (b.Owner != seat) blockedVertices.Add(vid);

        var ep = new Dictionary<int, (int A, int B)>();
        foreach (int eid in seatEdgeIds)
        {
            var e = _edges[eid];
            ep[eid] = (e.A, e.B);
        }

        var inc = new Dictionary<int, List<int>>();
        foreach (var (eid, (a, b)) in ep)
        {
            if (!inc.ContainsKey(a)) inc[a] = new();
            if (!inc.ContainsKey(b)) inc[b] = new();
            inc[a].Add(eid);
            inc[b].Add(eid);
        }

        int best = 0;

        void Dfs(int prevV, int v, HashSet<int> used)
        {
            best = Math.Max(best, used.Count);
            if (v != prevV && blockedVertices.Contains(v)) return;
            if (!inc.TryGetValue(v, out var adj)) return;
            foreach (int ne in adj)
            {
                if (used.Contains(ne)) continue;
                var (a2, b2) = ep[ne];
                int nv = a2 == v ? b2 : a2;
                used.Add(ne);
                Dfs(v, nv, used);
                used.Remove(ne);
            }
        }

        foreach (var (eid, (a, b)) in ep)
        {
            var used = new HashSet<int> { eid };
            Dfs(a, b, used);
            Dfs(b, a, used);
        }

        return best;
    }

    // ── Ports / trading ────────────────────────────────────────

    private bool SeatHasPort(int seat, string kind)
    {
        // Map port tile coords → kind
        var portTiles = new Dictionary<int, string>();
        foreach (var p in _ports)
        {
            for (int ti = 0; ti < _tiles.Count; ti++)
            {
                var t = _tiles[ti];
                if (t.Kind == "water" && t.Q == p.Q && t.R == p.R) { portTiles[ti] = p.Kind; break; }
            }
        }

        foreach (var (vid, b) in _buildings)
        {
            if (b.Owner != seat) continue;
            if (vid < 0 || vid >= _vertices.Count) continue;
            var adj = _vertices[vid].AdjacentTiles;
            foreach (var (ti2, pk) in portTiles)
            {
                if (adj.Contains(ti2))
                    if (pk == "any" || pk == kind) return true;
            }
        }
        return false;
    }

    private int TradeRatio(int seat, string give)
    {
        if (SeatHasPort(seat, give)) return 2;
        if (SeatHasPort(seat, "any")) return 3;
        return 4;
    }

    private void DoBankTrade(int seat, string give, string get2)
    {
        int ratio = TradeRatio(seat, give);
        if (GetRes(seat, give) < ratio) return;
        if (_bank.GetValueOrDefault(get2) <= 0) return;

        AddRes(seat, give, -ratio);
        AddBank(give, ratio);
        AddBank(get2, -1);
        AddRes(seat, get2, 1);
        _lastEvent = $"{SeatLabel(seat)} traded {ratio}:1 ({give}→{get2})";
    }

    // ── Graph queries ──────────────────────────────────────────

    private int? NearestVertex(float lx, float ly)
    {
        int? best = null;
        float bestD2 = float.MaxValue;
        foreach (var v in _vertices)
        {
            float dx = v.X - lx, dy = v.Y - ly;
            float d2 = dx * dx + dy * dy;
            if (d2 < bestD2) { bestD2 = d2; best = v.Id; }
        }
        return best.HasValue && bestD2 <= 0.55f * 0.55f ? best : null;
    }

    private int? NearestEdge(float lx, float ly)
    {
        int? best = null;
        float bestD2 = float.MaxValue;
        foreach (var e in _edges)
        {
            var a = _vertices[e.A];
            var b = _vertices[e.B];
            float d2 = DistPointToSeg2(lx, ly, a.X, a.Y, b.X, b.Y);
            if (d2 < bestD2) { bestD2 = d2; best = e.Id; }
        }
        return best.HasValue && bestD2 <= 0.35f * 0.35f ? best : null;
    }

    private int? NearestLandTile(float lx, float ly)
    {
        int? best = null;
        float bestD2 = float.MaxValue;
        for (int ti = 0; ti < _tiles.Count; ti++)
        {
            var t = _tiles[ti];
            if (t.Kind == "water") continue;
            var (cx, cy) = AxialToPixel(t.Q, t.R, 1.0f);
            float dx = cx - lx, dy = cy - ly;
            float d2 = dx * dx + dy * dy;
            if (d2 < bestD2) { bestD2 = d2; best = ti; }
        }
        return best.HasValue && bestD2 <= 0.95f * 0.95f ? best : null;
    }

    private static float DistPointToSeg2(float px, float py, float ax, float ay, float bx, float by)
    {
        float vx = bx - ax, vy = by - ay;
        float wx = px - ax, wy = py - ay;
        float c1 = vx * wx + vy * wy;
        if (c1 <= 0) { float dx = px - ax, dy = py - ay; return dx * dx + dy * dy; }
        float c2 = vx * vx + vy * vy;
        if (c2 <= c1) { float dx = px - bx, dy = py - by; return dx * dx + dy * dy; }
        float t = c1 / c2;
        float projx = ax + t * vx, projy = ay + t * vy;
        float dx2 = px - projx, dy2 = py - projy;
        return dx2 * dx2 + dy2 * dy2;
    }

    // ── Tile resource mapping ──────────────────────────────────

    private static string? TileResource(string kind) => kind switch
    {
        "wood" or "brick" or "sheep" or "wheat" or "ore" => kind,
        "gold" => "gold",
        _ => null,
    };

    // ═══════════════════════════════════════════════════════════
    //  Map generation
    // ═══════════════════════════════════════════════════════════

    private static string ExpansionForPlayerCount(int n) => n switch
    {
        <= 3 => "base",
        4 => "extended",
        <= 6 => "seafarers",
        _ => "mega",
    };

    private ExpansionConfig ConfigFor(int nPlayers)
    {
        string mode = _expansionMode;
        return mode switch
        {
            "base" => new ExpansionConfig { Name = "base", Radius = 4, WaterRing = true, Ports = 8 },
            "extended" => new ExpansionConfig { Name = "extended", Radius = 5, WaterRing = true, Ports = 10, ExtraWaterProb = 0.03, GoldTiles = 1 },
            "seafarers" => new ExpansionConfig
            {
                Name = "seafarers",
                Radius = nPlayers >= 6 ? 5 : 4,
                WaterRing = true,
                IslandCount = nPlayers >= 5 ? 2 : 1,
                IslandRadius = 2,
                Ports = 10,
                ExtraWaterProb = 0.06,
                GoldTiles = 2,
            },
            _ => new ExpansionConfig
            {
                Name = "mega",
                Radius = nPlayers >= 8 ? 6 : 5,
                WaterRing = true,
                IslandCount = 3,
                IslandRadius = 2,
                Ports = 12,
                ExtraWaterProb = 0.09,
                GoldTiles = 3,
                VolcanoTiles = 1,
            },
        };
    }

    private static List<(int Q, int R)> AxialHexes(int radius)
    {
        var result = new List<(int, int)>();
        for (int q = -radius; q <= radius; q++)
        {
            int r1 = Math.Max(-radius, -q - radius);
            int r2 = Math.Min(radius, -q + radius);
            for (int r = r1; r <= r2; r++)
                result.Add((q, r));
        }
        return result;
    }

    private static int AxialDist((int Q, int R) a, (int Q, int R) b)
    {
        return (Math.Abs(a.Q - b.Q) + Math.Abs(a.R - b.R) + Math.Abs((-a.Q - a.R) - (-b.Q - b.R))) / 2;
    }

    private (List<HexTile>, List<Port>, int) GenerateMap(int nPlayers)
    {
        var cfg = ConfigFor(nPlayers);
        var rng = new Random((int)(DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() ^ (nPlayers * 0x9E3779B1L)));
        int radius = cfg.Radius;

        var allCoords = AxialHexes(radius);
        var land = new HashSet<(int, int)>();
        var water = new HashSet<(int, int)>();

        if (cfg.WaterRing)
        {
            foreach (var (q, r) in allCoords)
            {
                if (AxialDist((q, r), (0, 0)) >= radius) water.Add((q, r));
                else land.Add((q, r));
            }
        }
        else
        {
            land = new HashSet<(int, int)>(allCoords);
        }

        // Extra water pockets
        if (cfg.WaterRing)
        {
            foreach (var (q, r) in new List<(int, int)>(land))
            {
                if (AxialDist((q, r), (0, 0)) >= Math.Max(2, radius - 2) && rng.NextDouble() < cfg.ExtraWaterProb)
                {
                    land.Remove((q, r));
                    water.Add((q, r));
                }
            }

            // Islands
            var islandCenters = PickIslandCenters(rng, radius, cfg.IslandCount);
            foreach (var (cq, cr) in islandCenters)
            {
                foreach (var (q, r) in allCoords)
                {
                    if (AxialDist((q, r), (cq, cr)) <= cfg.IslandRadius &&
                        water.Contains((q, r)) && AxialDist((q, r), (0, 0)) >= 2)
                    {
                        water.Remove((q, r));
                        land.Add((q, r));
                    }
                }
            }
        }

        // Assign land kinds
        var landCoords = land.ToList();
        Shuffle(rng, landCoords);

        var landKinds = new List<string>();
        for (int i = 0; i < landCoords.Count; i++)
            landKinds.Add(Resource[rng.Next(Resource.Length)]);

        if (landKinds.Count > 0) landKinds[0] = "desert";

        for (int i = 0; i < cfg.GoldTiles; i++)
            if (landKinds.Count >= 6) landKinds[rng.Next(landKinds.Count)] = "gold";
        for (int i = 0; i < cfg.VolcanoTiles; i++)
            if (landKinds.Count >= 10) landKinds[rng.Next(landKinds.Count)] = "volcano";

        // Token numbers
        int[] baseNumbers = { 2, 3, 3, 4, 4, 5, 5, 6, 6, 8, 8, 9, 9, 10, 10, 11, 11, 12 };
        var numbersPool = new List<int>();
        while (numbersPool.Count < Math.Max(0, landCoords.Count - 1))
            numbersPool.AddRange(baseNumbers);
        Shuffle(rng, numbersPool);

        var tiles = new List<HexTile>();
        int numIdx = 0;
        bool desertAssigned = false;
        for (int i = 0; i < landCoords.Count; i++)
        {
            var (q, r) = landCoords[i];
            string kind = landKinds[i];
            int? number = null;
            if (kind == "desert") desertAssigned = true;
            if (kind is "wood" or "brick" or "sheep" or "wheat" or "ore" or "gold")
            {
                if (numIdx < numbersPool.Count) number = numbersPool[numIdx++];
            }
            tiles.Add(new HexTile(q, r, kind, number));
        }

        if (tiles.Count > 0 && !desertAssigned)
        {
            var t0 = tiles[0];
            tiles[0] = new HexTile(t0.Q, t0.R, "desert", null);
        }

        foreach (var (q, r) in water.OrderBy(c => c))
            tiles.Add(new HexTile(q, r, "water", null));

        var ports = GeneratePorts(rng, tiles, cfg.Ports);
        return (tiles, ports, radius);
    }

    private List<(int Q, int R)> PickIslandCenters(Random rng, int radius, int count)
    {
        var centers = new List<(int, int)>();
        int tries = 0;
        while (centers.Count < count && tries < 500)
        {
            tries++;
            int q = rng.Next(-(radius - 2), radius - 1);
            int r = rng.Next(-(radius - 2), radius - 1);
            if (AxialDist((q, r), (0, 0)) > Math.Max(2, radius - 2)) continue;
            if (centers.Any(c => AxialDist((q, r), c) <= 2)) continue;
            centers.Add((q, r));
        }
        return centers;
    }

    private List<Port> GeneratePorts(Random rng, List<HexTile> tiles, int want)
    {
        if (want <= 0) return new();
        var landSet = tiles.Where(t => t.Kind != "water").Select(t => (t.Q, t.R)).ToHashSet();
        var waterSet = tiles.Where(t => t.Kind == "water").Select(t => (t.Q, t.R)).ToHashSet();

        int[][] neighbors = { new[] { 1, 0 }, new[] { 1, -1 }, new[] { 0, -1 }, new[] { -1, 0 }, new[] { -1, 1 }, new[] { 0, 1 } };
        var coastal = new List<(int, int)>();
        foreach (var (q, r) in waterSet)
        {
            foreach (var d in neighbors)
                if (landSet.Contains((q + d[0], r + d[1]))) { coastal.Add((q, r)); break; }
        }

        Shuffle(rng, coastal);
        coastal = coastal.Take(Math.Min(coastal.Count, want)).ToList();

        string[] portKinds = { "any", "any", "any", "wood", "brick", "sheep", "wheat", "ore" };
        return coastal.Select(c => new Port(c.Item1, c.Item2, portKinds[rng.Next(portKinds.Length)])).ToList();
    }

    // ═══════════════════════════════════════════════════════════
    //  Graph building
    // ═══════════════════════════════════════════════════════════

    private (float x, float y) AxialToPixel(int q, int r, float size)
    {
        float x = size * MathF.Sqrt(3) * (q + r / 2.0f);
        float y = size * 1.5f * r;
        return (x, y);
    }

    /// <summary>Compute 6 hex vertices (pointy-top) for the given center and size.</summary>
    private static (float X, float Y)[] HexPoints(float cx, float cy, float size)
    {
        var pts = new (float X, float Y)[6];
        for (int i = 0; i < 6; i++)
        {
            float ang = MathF.PI / 180f * (60 * i - 30); // pointy-top
            pts[i] = (cx + size * MathF.Cos(ang), cy + size * MathF.Sin(ang));
        }
        return pts;
    }

    private static (int, int) VKey(float x, float y) => ((int)MathF.Round(x * 10000), (int)MathF.Round(y * 10000));

    private void BuildGraph()
    {
        _vertices.Clear();
        _edges.Clear();
        _vertexByKey.Clear();
        _edgeByKey.Clear();

        // Hex corner offsets for pointy-top, size=1
        var corners = new (float dx, float dy)[6];
        for (int i = 0; i < 6; i++)
        {
            float ang = MathF.PI / 180f * (60f * i - 30f);
            corners[i] = (MathF.Cos(ang), MathF.Sin(ang));
        }

        for (int ti = 0; ti < _tiles.Count; ti++)
        {
            var t = _tiles[ti];
            if (t.Kind == "water") continue;
            var (cx, cy) = AxialToPixel(t.Q, t.R, 1.0f);
            var vids = new int[6];

            for (int c = 0; c < 6; c++)
            {
                float vx = cx + corners[c].dx;
                float vy = cy + corners[c].dy;
                var key = VKey(vx, vy);
                if (!_vertexByKey.TryGetValue(key, out int vid))
                {
                    vid = _vertices.Count;
                    _vertexByKey[key] = vid;
                    _vertices.Add(new GraphVertex(vid, vx, vy));
                }
                _vertices[vid].AdjacentTiles.Add(ti);
                vids[c] = vid;
            }

            // Edges around hex
            for (int c = 0; c < 6; c++)
            {
                int a = vids[c], b = vids[(c + 1) % 6];
                int ka = Math.Min(a, b), kb = Math.Max(a, b);
                var ekey = (ka, kb);
                if (!_edgeByKey.ContainsKey(ekey))
                {
                    int eid = _edges.Count;
                    _edgeByKey[ekey] = eid;
                    _edges.Add(new GraphEdge(eid, ka, kb));
                    if (!_vertices[ka].Neighbors.Contains(kb)) _vertices[ka].Neighbors.Add(kb);
                    if (!_vertices[kb].Neighbors.Contains(ka)) _vertices[kb].Neighbors.Add(ka);
                }
            }
        }

        // Dedup adjacency & neighbors
        foreach (var v in _vertices)
        {
            v.AdjacentTiles = v.AdjacentTiles.Distinct().OrderBy(x => x).ToList();
            v.Neighbors = v.Neighbors.Distinct().OrderBy(x => x).ToList();
        }
    }

    // ═══════════════════════════════════════════════════════════
    //  Drawing helpers
    // ═══════════════════════════════════════════════════════════

    private void RecomputeLayout(int w, int h)
    {
        int pad = 10, headerH = 54;
        int availW = Math.Max(100, w - pad * 2);
        int availH = Math.Max(100, h - headerH - pad);

        if (_tiles.Count == 0) { _hexSize = 28f; return; }

        var centersUnit = _tiles.Select(t2 => AxialToPixel(t2.Q, t2.R, 1.0f)).ToList();
        float minXu = centersUnit.Min(c => c.x), maxXu = centersUnit.Max(c => c.x);
        float minYu = centersUnit.Min(c => c.y), maxYu = centersUnit.Max(c => c.y);
        float spanXu = (maxXu - minXu) + 2.0f;
        float spanYu = (maxYu - minYu) + 2.0f;

        float size = Math.Min(availW / Math.Max(1f, spanXu), availH / Math.Max(1f, spanYu));
        size *= 0.995f;
        size = Math.Clamp(size, 14f, 80f);

        // Final fit check
        var centers2 = _tiles.Select(t2 => AxialToPixel(t2.Q, t2.R, size)).ToList();
        float minX2 = centers2.Min(c => c.x), maxX2 = centers2.Max(c => c.x);
        float minY2 = centers2.Min(c => c.y), maxY2 = centers2.Max(c => c.y);
        float spanX2 = (maxX2 - minX2) + size * 2f;
        float spanY2 = (maxY2 - minY2) + size * 2f;
        float scale2 = Math.Min(availW / Math.Max(1f, spanX2), availH / Math.Max(1f, spanY2));
        scale2 = Math.Min(scale2, 1f);
        size *= scale2;
        size = Math.Clamp(size, 14f, 80f);

        _hexSize = size;
    }

    private void EmitBuildAnimation(int playerIdx, int vid, string label)
    {
        if (vid < 0 || vid >= _vertices.Count) return;
        var v = _vertices[vid];
        float vx = v.X * _drawSize + _drawOffX;
        float vy = v.Y * _drawSize + _drawOffY;
        var col = PlayerPalette[playerIdx % PlayerPalette.Length];
        _textPops.Add(new TextPopAnim(label, (int)vx, (int)vy - 30, col, fontSize: 18));
        _pulseRings.Add(new PulseRing((int)vx, (int)vy, col, maxRadius: 38, duration: 0.6f));
        _particles.EmitSparkle((int)vx, (int)vy, col, 16);
    }

    private void EmitEdgeBuildAnimation(int playerIdx, int eid, string label)
    {
        if (eid < 0 || eid >= _edges.Count) return;
        var e = _edges[eid];
        if (e.A < 0 || e.A >= _vertices.Count || e.B < 0 || e.B >= _vertices.Count) return;
        var va = _vertices[e.A]; var vb = _vertices[e.B];
        float ex = (va.X + vb.X) / 2f * _drawSize + _drawOffX;
        float ey = (va.Y + vb.Y) / 2f * _drawSize + _drawOffY;
        var col = PlayerPalette[playerIdx % PlayerPalette.Length];
        _textPops.Add(new TextPopAnim(label, (int)ex, (int)ey - 25, col, fontSize: 16));
        _pulseRings.Add(new PulseRing((int)ex, (int)ey, col, maxRadius: 28, duration: 0.5f));
        _particles.EmitSparkle((int)ex, (int)ey, col, 12);
    }

    // ═══════════════════════════════════════════════════════════
    //  Buttons
    // ═══════════════════════════════════════════════════════════

    private void RefreshButtons()
    {
        _buttons.Clear();
        foreach (int seat in ActivePlayers)
        {
            if (State != "playing") continue;
            var btns = new Dictionary<string, (string, bool)>();

            // Winner lock
            if (_winner is int w)
            {
                btns["end_turn"] = ($"Winner: {SeatLabel(w)}", false);
                _buttons[seat] = btns;
                continue;
            }

            // Discard phase
            if (_phase == "discard")
            {
                int rem = _discardRemaining.GetValueOrDefault(seat);
                if (rem > 0)
                {
                    btns["initial_hint"] = ($"Discard {rem}", false);
                    var inv = _res.GetValueOrDefault(seat) ?? NewResDict();
                    foreach (var r2 in Resource)
                    {
                        int have = inv.GetValueOrDefault(r2);
                        btns[$"discard:{r2}"] = ($"Discard {r2} ({have})", have > 0);
                    }
                }
                else
                {
                    btns["end_turn"] = ("Waiting (discard)", false);
                }
                _buttons[seat] = btns;
                continue;
            }

            // P2P trade pending
            if (_p2pOffer != null && _phase.StartsWith("trade_player"))
            {
                int frm = OfferInt("from"), to = OfferInt("to");
                string give = OfferStr("give"), get2 = OfferStr("get");

                if (seat == to && IsResource(give) && IsResource(get2))
                {
                    btns["initial_hint"] = ($"Trade offer: give 1 {get2} for 1 {give}", false);
                    bool canAccept = GetRes(seat, get2) > 0 && GetRes(frm, give) > 0;
                    btns["p2p_accept"] = ("Accept", canAccept);
                    btns["p2p_decline"] = ("Decline", true);
                    _buttons[seat] = btns;
                    continue;
                }

                if (seat == frm && IsMyTurn(seat) && _phase == "trade_player_wait")
                {
                    btns["initial_hint"] = ("Waiting for response...", false);
                    btns["trade_cancel"] = ("Cancel Offer", true);
                    _buttons[seat] = btns;
                    continue;
                }
            }

            // Not your turn
            if (!IsMyTurn(seat))
            {
                btns["end_turn"] = ("Waiting", false);
                _buttons[seat] = btns;
                continue;
            }

            // Initial placement
            if (_phase == "initial_settlement")
            {
                btns["initial_hint"] = ("Tap: Place Settlement", false);
                _buttons[seat] = btns;
                continue;
            }
            if (_phase == "initial_road")
            {
                btns["initial_hint"] = ("Tap: Place Road", false);
                _buttons[seat] = btns;
                continue;
            }

            // Robber
            if (_phase == "robber_move")
            {
                btns["initial_hint"] = ("Tap: Move Robber", false);
                _buttons[seat] = btns;
                continue;
            }
            if (_phase == "robber_steal")
            {
                foreach (int cand in _robberCandidates)
                    btns[$"steal:{cand}"] = ($"Steal from {SeatLabel(cand)}", true);
                btns["skip_steal"] = ("Skip Steal", true);
                _buttons[seat] = btns;
                continue;
            }

            // Bank trade
            if (_phase == "trade_bank")
            {
                string give = _tradeGive ?? "wood";
                string get2 = _tradeGet ?? "brick";
                int ratio = TradeRatio(seat, give);
                btns["initial_hint"] = ($"Bank trade {ratio}:1", false);
                foreach (var r2 in Resource)
                    btns[$"trade_give:{r2}"] = ($"Give: {r2}{(r2 == give ? " *" : "")}", true);
                foreach (var r2 in Resource)
                    btns[$"trade_get:{r2}"] = ($"Get: {r2}{(r2 == get2 ? " *" : "")}", true);
                bool can = give != get2 && GetRes(seat, give) >= ratio && _bank.GetValueOrDefault(get2) > 0;
                btns["trade_confirm"] = ("Confirm Trade", can);
                btns["trade_cancel"] = ("Back", true);
                _buttons[seat] = btns;
                continue;
            }

            // Player trade select
            if (_phase == "trade_player_select")
            {
                btns["initial_hint"] = ("Pick a trade partner", false);
                foreach (int other in ActivePlayers)
                    if (other != seat) btns[$"trade_to:{other}"] = ($"Trade with {SeatLabel(other)}", true);
                btns["trade_cancel"] = ("Back", true);
                _buttons[seat] = btns;
                continue;
            }
            if (_phase == "trade_player_offer")
            {
                int? toSeat2 = _p2pOffer != null ? OfferInt("to") : null;
                btns["initial_hint"] = (toSeat2 is int ts ? $"Offer 1-for-1 to {SeatLabel(ts)}" : "Offer 1-for-1", false);
                string give = _p2pGive ?? "wood";
                string get2 = _p2pGet ?? "brick";
                foreach (var r2 in Resource)
                    btns[$"p2p_give:{r2}"] = ($"You give: {r2}{(r2 == give ? " *" : "")}", true);
                foreach (var r2 in Resource)
                    btns[$"p2p_get:{r2}"] = ($"You get: {r2}{(r2 == get2 ? " *" : "")}", true);
                bool canOffer = give != get2 && GetRes(seat, give) > 0;
                btns["p2p_offer"] = ("Send Offer", canOffer);
                btns["trade_cancel"] = ("Back", true);
                _buttons[seat] = btns;
                continue;
            }

            // Main phase
            btns["roll"] = ("Roll Dice", !_rolledThisTurn && !_diceRolling && _pendingBuild == null);

            bool canRoad = _rolledThisTurn && _pendingBuild is null or "road" &&
                (_freeRoadsLeft > 0 || CanAfford(seat, new() { ["wood"] = 1, ["brick"] = 1 }));
            btns["build_road"] = ("Build Road", canRoad);
            btns["build_settlement"] = ("Build Settlement",
                _rolledThisTurn && _pendingBuild is null or "settlement" &&
                CanAfford(seat, new() { ["wood"] = 1, ["brick"] = 1, ["sheep"] = 1, ["wheat"] = 1 }));
            btns["build_city"] = ("Build City",
                _rolledThisTurn && _pendingBuild is null or "city" &&
                CanAfford(seat, new() { ["ore"] = 3, ["wheat"] = 2 }));
            btns["trade_bank"] = ("Trade (Bank)", _rolledThisTurn && _pendingBuild == null);
            btns["trade_player"] = ("Trade (Player)", _rolledThisTurn && _pendingBuild == null);
            btns["buy_dev"] = ("Buy Dev",
                _rolledThisTurn && _pendingBuild == null && _devDeck.Count > 0 &&
                CanAfford(seat, new() { ["sheep"] = 1, ["wheat"] = 1, ["ore"] = 1 }));

            // Dev play
            var hand = _devHand.GetValueOrDefault(seat) ?? new();
            bool boughtThisTurn = _devBoughtTurn.GetValueOrDefault(seat, -999) == _turnNumber;
            if (hand.GetValueOrDefault("knight") > 0)
                btns["play_dev:knight"] = ("Play Knight", !boughtThisTurn && !_devPlayedThisTurn);
            if (hand.GetValueOrDefault("road_building") > 0)
                btns["play_dev:road_building"] = ("Play Road Building", !boughtThisTurn && !_devPlayedThisTurn);
            if (hand.GetValueOrDefault("year_of_plenty") > 0)
                btns["play_dev:year_of_plenty"] = ("Play Year of Plenty", !boughtThisTurn && !_devPlayedThisTurn);
            if (hand.GetValueOrDefault("monopoly") > 0)
                btns["play_dev:monopoly"] = ("Dev: Monopoly", !boughtThisTurn && !_devPlayedThisTurn);

            // Year of Plenty
            if (_yopLeft > 0)
            {
                btns["initial_hint"] = ($"Pick {_yopLeft} resource(s)", false);
                foreach (var r2 in Resource)
                    btns[$"yop:{r2}"] = ($"Pick {r2} ({_bank.GetValueOrDefault(r2)})", _bank.GetValueOrDefault(r2) > 0);
            }

            // Monopoly
            if (_monopolyPending)
            {
                btns["initial_hint"] = ("Pick Monopoly resource", false);
                foreach (var r2 in Resource)
                    btns[$"mono:{r2}"] = ($"Monopoly {r2}", true);
            }

            if (_pendingBuild != null)
                btns["cancel_build"] = ("Cancel Build", true);

            bool endOk = _rolledThisTurn && _pendingBuild == null && _yopLeft <= 0 && !_monopolyPending;
            btns["end_turn"] = ("End Turn", endOk);

            _buttons[seat] = btns;
        }
    }

    // ── Collection helpers ─────────────────────────────────────

    private static void Shuffle<T>(Random rng, List<T> list)
    {
        for (int i = list.Count - 1; i > 0; i--)
        {
            int j = rng.Next(i + 1);
            (list[i], list[j]) = (list[j], list[i]);
        }
    }
}

// ════════════════════════════════════════════════════════════════
//  Supporting types (internal to Catan)
// ════════════════════════════════════════════════════════════════

internal sealed class Building
{
    public int Owner { get; }
    public string Kind { get; }
    public Building(int owner, string kind) { Owner = owner; Kind = kind; }
}

internal sealed class GraphVertex
{
    public int Id { get; }
    public float X { get; }
    public float Y { get; }
    public List<int> AdjacentTiles { get; set; } = new();
    public List<int> Neighbors { get; set; } = new();

    public GraphVertex(int id, float x, float y) { Id = id; X = x; Y = y; }
}

internal sealed class GraphEdge
{
    public int Id { get; }
    public int A { get; }
    public int B { get; }

    public GraphEdge(int id, int a, int b) { Id = id; A = a; B = b; }
}
