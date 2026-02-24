using System;
using System.Collections.Generic;
using System.Linq;
using ARPi2.Sharp.Core;

namespace ARPi2.Sharp.Games.TicketToRide;

// ════════════════════════════════════════════════════════════════
//  Data types
// ════════════════════════════════════════════════════════════════

public sealed class CityData
{
    public string Name { get; }
    public float X { get; } // 0-1 normalised
    public float Y { get; } // 0-1 normalised

    public CityData(string name, float x, float y) { Name = name; X = x; Y = y; }
}

public sealed class RouteData
{
    public string CityA { get; }
    public string CityB { get; }
    public int Length { get; }
    public string Color { get; } // "gray" = any
    public int Parallel { get; } // 0 or 1

    public RouteData(string a, string b, int len, string color, int par = 0)
    {
        CityA = a; CityB = b; Length = len; Color = color; Parallel = par;
    }
}

public sealed class TicketData
{
    public string CityA { get; }
    public string CityB { get; }
    public int Points { get; }

    public TicketData(string a, string b, int pts) { CityA = a; CityB = b; Points = pts; }
}

// ════════════════════════════════════════════════════════════════
//  TicketToRideGameSharp — full game logic + MonoGame renderer
// ════════════════════════════════════════════════════════════════
public class TicketToRideGameSharp : BaseGame
{
    public override string ThemeName => "ticket_to_ride";

    // ── Constants ──
    private const int InitialHand = 4;
    private const int InitialTickets = 3;
    private const int InitialTrains = 45;
    private const int FaceUpCount = 5;

    // ── Static map data ──
    private static readonly string[] TrainColors =
        { "red", "orange", "yellow", "green", "blue", "purple", "black", "white" };

    private static readonly Dictionary<string, (float X, float Y)> Cities = new()
    {
        ["Vancouver"]        = (0.06f, 0.08f),
        ["Seattle"]          = (0.07f, 0.14f),
        ["Portland"]         = (0.05f, 0.21f),
        ["San Francisco"]    = (0.04f, 0.43f),
        ["Los Angeles"]      = (0.09f, 0.60f),
        ["Las Vegas"]        = (0.14f, 0.52f),
        ["Salt Lake City"]   = (0.20f, 0.38f),
        ["Phoenix"]          = (0.17f, 0.65f),
        ["El Paso"]          = (0.24f, 0.72f),
        ["Santa Fe"]         = (0.26f, 0.58f),
        ["Denver"]           = (0.30f, 0.42f),
        ["Helena"]           = (0.24f, 0.18f),
        ["Calgary"]          = (0.17f, 0.05f),
        ["Winnipeg"]         = (0.40f, 0.06f),
        ["Duluth"]           = (0.50f, 0.18f),
        ["Omaha"]            = (0.45f, 0.35f),
        ["Kansas City"]      = (0.48f, 0.42f),
        ["Oklahoma City"]    = (0.44f, 0.55f),
        ["Dallas"]           = (0.44f, 0.67f),
        ["Houston"]          = (0.47f, 0.76f),
        ["New Orleans"]      = (0.58f, 0.75f),
        ["Little Rock"]      = (0.52f, 0.58f),
        ["Saint Louis"]      = (0.53f, 0.44f),
        ["Chicago"]          = (0.57f, 0.28f),
        ["Sault Ste. Marie"] = (0.60f, 0.14f),
        ["Toronto"]          = (0.70f, 0.16f),
        ["Montreal"]         = (0.78f, 0.09f),
        ["Boston"]           = (0.88f, 0.16f),
        ["New York"]         = (0.85f, 0.24f),
        ["Pittsburgh"]       = (0.73f, 0.28f),
        ["Washington"]       = (0.82f, 0.34f),
        ["Raleigh"]          = (0.77f, 0.44f),
        ["Nashville"]        = (0.62f, 0.48f),
        ["Atlanta"]          = (0.67f, 0.56f),
        ["Charleston"]       = (0.76f, 0.55f),
        ["Miami"]            = (0.78f, 0.78f),
        ["Minneapolis"]      = (0.48f, 0.20f),
    };

    private static readonly List<RouteData> Routes = new()
    {
        new("Vancouver","Seattle",1,"gray",0), new("Vancouver","Seattle",1,"gray",1),
        new("Seattle","Portland",1,"gray",0), new("Seattle","Portland",1,"gray",1),
        new("Portland","San Francisco",5,"green",0), new("Portland","San Francisco",5,"purple",1),
        new("San Francisco","Los Angeles",3,"yellow",0), new("San Francisco","Los Angeles",3,"purple",1),
        new("Los Angeles","Las Vegas",2,"gray"), new("Los Angeles","Phoenix",3,"gray"),
        new("Los Angeles","El Paso",6,"black"),
        new("Las Vegas","Salt Lake City",3,"orange"),
        new("Phoenix","El Paso",3,"gray"), new("Phoenix","Santa Fe",3,"gray"),
        new("Phoenix","Denver",5,"white"),
        new("Seattle","Helena",6,"yellow"), new("Seattle","Calgary",4,"gray"),
        new("Calgary","Vancouver",3,"gray"), new("Calgary","Helena",4,"gray"),
        new("Calgary","Winnipeg",6,"white"),
        new("Helena","Salt Lake City",3,"purple"), new("Helena","Denver",4,"green"),
        new("Helena","Omaha",5,"red"), new("Helena","Duluth",6,"orange"),
        new("Helena","Winnipeg",4,"blue"),
        new("Salt Lake City","Denver",3,"red",0), new("Salt Lake City","Denver",3,"yellow",1),
        new("Salt Lake City","San Francisco",5,"orange",0), new("Salt Lake City","San Francisco",5,"white",1),
        new("El Paso","Santa Fe",2,"gray"), new("El Paso","Oklahoma City",5,"yellow"),
        new("El Paso","Dallas",4,"red"), new("El Paso","Houston",6,"green"),
        new("Santa Fe","Denver",2,"gray"), new("Santa Fe","Oklahoma City",3,"blue"),
        new("Denver","Kansas City",4,"black",0), new("Denver","Kansas City",4,"orange",1),
        new("Denver","Omaha",4,"purple"), new("Denver","Oklahoma City",4,"red"),
        new("Winnipeg","Duluth",4,"black"), new("Winnipeg","Sault Ste. Marie",6,"gray"),
        new("Duluth","Omaha",2,"gray",0), new("Duluth","Omaha",2,"gray",1),
        new("Duluth","Chicago",3,"red"), new("Duluth","Toronto",6,"purple"),
        new("Duluth","Sault Ste. Marie",3,"gray"),
        new("Omaha","Kansas City",1,"gray",0), new("Omaha","Kansas City",1,"gray",1),
        new("Omaha","Chicago",4,"blue"),
        new("Kansas City","Saint Louis",2,"blue",0), new("Kansas City","Saint Louis",2,"purple",1),
        new("Kansas City","Oklahoma City",2,"gray",0), new("Kansas City","Oklahoma City",2,"gray",1),
        new("Oklahoma City","Dallas",2,"gray",0), new("Oklahoma City","Dallas",2,"gray",1),
        new("Oklahoma City","Little Rock",2,"gray"),
        new("Dallas","Houston",1,"gray",0), new("Dallas","Houston",1,"gray",1),
        new("Dallas","Little Rock",2,"gray"), new("Houston","New Orleans",2,"gray"),
        new("Chicago","Saint Louis",2,"green",0), new("Chicago","Saint Louis",2,"white",1),
        new("Chicago","Pittsburgh",3,"orange",0), new("Chicago","Pittsburgh",3,"black",1),
        new("Chicago","Toronto",4,"white"),
        new("Saint Louis","Nashville",2,"gray"), new("Saint Louis","Little Rock",2,"gray"),
        new("Saint Louis","Pittsburgh",5,"green"),
        new("Little Rock","Nashville",3,"white"), new("Little Rock","New Orleans",3,"green"),
        new("Nashville","Atlanta",1,"gray"), new("Nashville","Raleigh",3,"black"),
        new("Nashville","Pittsburgh",4,"yellow"),
        new("New Orleans","Atlanta",4,"yellow",0), new("New Orleans","Atlanta",4,"orange",1),
        new("New Orleans","Miami",6,"red"),
        new("Sault Ste. Marie","Toronto",2,"gray"),
        new("Sault Ste. Marie","Montreal",5,"black"),
        new("Toronto","Montreal",3,"gray"), new("Toronto","Pittsburgh",2,"gray"),
        new("Montreal","Boston",2,"gray",0), new("Montreal","Boston",2,"gray",1),
        new("Montreal","New York",3,"blue"),
        new("Boston","New York",2,"yellow",0), new("Boston","New York",2,"red",1),
        new("New York","Pittsburgh",2,"white",0), new("New York","Pittsburgh",2,"green",1),
        new("New York","Washington",2,"orange",0), new("New York","Washington",2,"black",1),
        new("Pittsburgh","Washington",2,"gray"), new("Pittsburgh","Raleigh",2,"gray"),
        new("Washington","Raleigh",2,"gray",0), new("Washington","Raleigh",2,"gray",1),
        new("Raleigh","Atlanta",2,"gray",0), new("Raleigh","Atlanta",2,"gray",1),
        new("Raleigh","Charleston",2,"gray"), new("Atlanta","Charleston",2,"gray"),
        new("Atlanta","Miami",5,"blue"), new("Charleston","Miami",4,"purple"),
    };

    private static readonly List<TicketData> AllTickets = new()
    {
        new("Los Angeles", "New York", 21),
        new("Duluth", "Houston", 8),
        new("Sault Ste. Marie", "Nashville", 8),
        new("New York", "Atlanta", 6),
        new("Portland", "Nashville", 17),
        new("Vancouver", "Montreal", 20),
        new("Duluth", "El Paso", 10),
        new("Toronto", "Miami", 10),
        new("Portland", "Phoenix", 11),
        new("Dallas", "New York", 11),
        new("Calgary", "Salt Lake City", 7),
        new("Calgary", "Phoenix", 13),
        new("Los Angeles", "Miami", 20),
        new("Winnipeg", "Little Rock", 11),
        new("San Francisco", "Atlanta", 17),
        new("Kansas City", "Houston", 5),
        new("Los Angeles", "Chicago", 16),
        new("Denver", "Pittsburgh", 11),
        new("Chicago", "Santa Fe", 9),
        new("Vancouver", "Santa Fe", 13),
        new("Boston", "Miami", 12),
        new("Chicago", "New Orleans", 7),
        new("Montreal", "Atlanta", 9),
        new("Seattle", "New York", 22),
        new("Denver", "El Paso", 4),
        new("Helena", "Los Angeles", 8),
        new("Winnipeg", "Houston", 12),
        new("Montreal", "New Orleans", 13),
        new("Sault Ste. Marie", "Oklahoma City", 9),
        new("Seattle", "Los Angeles", 9),
    };

    private static readonly Dictionary<string, (int R, int G, int B)> ColorRgb = new()
    {
        ["red"]    = (200, 50, 50),
        ["orange"] = (220, 140, 40),
        ["yellow"] = (220, 200, 50),
        ["green"]  = (50, 170, 70),
        ["blue"]   = (50, 100, 200),
        ["purple"] = (140, 60, 180),
        ["black"]  = (50, 50, 55),
        ["white"]  = (230, 230, 235),
        ["gray"]   = (140, 140, 145),
        ["locomotive"] = (180, 160, 60),
    };

    private static readonly (int R, int G, int B)[] PlayerPalette =
    {
        (255, 77, 77),   // red
        (77, 121, 255),  // blue
        (77, 255, 136),  // green
        (255, 210, 77),  // yellow
        (184, 77, 255),  // purple
    };

    private static readonly Dictionary<int, int> RouteScores = new()
    {
        [1] = 1, [2] = 2, [3] = 4, [4] = 7, [5] = 10, [6] = 15,
    };

    // ── Game state ──
    private readonly Dictionary<int, List<string>> _hands = new();
    private readonly Dictionary<int, List<TicketData>> _tickets = new();
    private readonly Dictionary<int, int> _trainsLeft = new();
    private readonly Dictionary<int, int> _scores = new();
    private readonly Dictionary<int, List<int>> _playerRoutes = new();   // seat → [route indices]
    private readonly List<string> _drawPile = new();
    private readonly List<string> _discardPile = new();
    private List<string> _faceUp = new();
    private readonly List<TicketData> _ticketPile = new();
    private readonly Dictionary<int, int> _claimedRoutes = new();        // route_idx → owner seat
    private readonly Dictionary<int, List<TicketData>> _pendingTickets = new();
    private readonly Dictionary<int, int> _pendingKeepMin = new();
    private readonly Dictionary<int, Dictionary<string, (string Text, bool Enabled)>> _buttons = new();

    private string _phase = "";
    private int _currentTurnIdx;
    private bool _drewFirstCard;
    private bool _lastRoundStarted;
    private int? _lastRoundTriggerSeat;
    private int? _winner;
    private string _lastEvent = "";

    private int CurrentTurnSeat =>
        ActivePlayers.Count > 0
            ? ActivePlayers[_currentTurnIdx % ActivePlayers.Count]
            : -1;

    // ── Animation state ──
    private double _totalElapsed;
    private readonly AmbientSystem _ambient;
    private readonly Starfield _starfield;
    private readonly ParticleSystem _particles = new();
    private readonly List<PulseRing> _pulseRings = new();

    // ═════════════════════════════════════════════════════════════
    //  Constructor
    // ═════════════════════════════════════════════════════════════
    public TicketToRideGameSharp(int w, int h, Renderer renderer) : base(w, h, renderer)
    {
        _ambient = AmbientSystem.ForTheme("ticket_to_ride", w, h);
        _starfield = Starfield.ForTheme("ticket_to_ride", w, h);
        WebUIOnlyPlayerSelect = true;
        BoardOnlyMode = true;
    }

    // ═════════════════════════════════════════════════════════════
    //  StartGame
    // ═════════════════════════════════════════════════════════════
    public override void StartGame(List<int> players)
    {
        var seats = players.Where(s => s >= 0 && s <= 7).Distinct().OrderBy(x => x).ToList();
        if (seats.Count < 2 || seats.Count > 5) return;
        ActivePlayers = seats;
        State = "playing";
        _phase = "play";
        _currentTurnIdx = 0;
        _winner = null;
        _lastRoundStarted = false;
        _lastRoundTriggerSeat = null;
        _drewFirstCard = false;
        _lastEvent = "";

        // Build draw pile (12 of each colour + 14 locomotives = 110 cards)
        _drawPile.Clear();
        _discardPile.Clear();
        foreach (var color in TrainColors)
            for (int i = 0; i < 12; i++) _drawPile.Add(color);
        for (int i = 0; i < 14; i++) _drawPile.Add("locomotive");
        ShuffleList(_drawPile);

        // Face-up cards
        _faceUp = new List<string>();
        for (int i = 0; i < FaceUpCount && _drawPile.Count > 0; i++)
            _faceUp.Add(PopLast(_drawPile));
        CheckFaceUpLocomotives();

        // Destination ticket pile
        _ticketPile.Clear();
        _ticketPile.AddRange(AllTickets);
        ShuffleList(_ticketPile);

        // Per-player init
        _claimedRoutes.Clear();
        _hands.Clear();
        _tickets.Clear();
        _trainsLeft.Clear();
        _scores.Clear();
        _playerRoutes.Clear();
        _pendingTickets.Clear();
        _pendingKeepMin.Clear();
        _buttons.Clear();
        foreach (var seat in seats)
        {
            _hands[seat] = new List<string>();
            for (int i = 0; i < InitialHand; i++) _hands[seat].Add(DrawCardFromPile());
            _tickets[seat] = new List<TicketData>();
            _trainsLeft[seat] = InitialTrains;
            _scores[seat] = 0;
            _playerRoutes[seat] = new List<int>();
        }

        // Initial ticket draw (3 per player, must keep >= 2)
        foreach (var seat in seats)
        {
            _pendingTickets[seat] = DrawTickets(InitialTickets);
            _pendingKeepMin[seat] = 2;
        }

        _phase = "pick_tickets";
        SetEvent($"Game started! {seats.Count} players. Pick initial tickets.");
        RefreshButtons();
    }

    // ═════════════════════════════════════════════════════════════
    //  HandleClick
    // ═════════════════════════════════════════════════════════════
    public override void HandleClick(int playerIdx, string buttonId)
    {
        int seat = playerIdx;
        if (!ActivePlayers.Contains(seat)) return;

        // ── Ticket selection phase ──
        if (_phase == "pick_tickets" && _pendingTickets.ContainsKey(seat))
        {
            if (buttonId.StartsWith("keep_ticket:"))
            {
                if (!int.TryParse(buttonId.AsSpan(buttonId.IndexOf(':') + 1), out int idx)) return;
                if (!_pendingTickets.TryGetValue(seat, out var pending)) return;
                if (idx < 0 || idx >= pending.Count) return;
                var ticket = pending[idx];
                _tickets[seat].Add(ticket);
                pending.RemoveAt(idx);
                RefreshButtons();
                return;
            }

            if (buttonId == "done_tickets")
            {
                // Return unkept pending tickets to the bottom of the pile
                if (_pendingTickets.TryGetValue(seat, out var pending))
                    foreach (var t in pending)
                        _ticketPile.Insert(0, t);

                _pendingTickets.Remove(seat);
                _pendingKeepMin.Remove(seat);

                // If all players are done with initial tickets, start playing
                if (_pendingTickets.Count == 0)
                    _phase = "play";

                RefreshButtons();
                return;
            }
        }

        // Not your turn (except during ticket picking)
        if (_phase == "pick_tickets") return;
        if (seat != CurrentTurnSeat) return;

        // ── Draw from face-up ──
        if (buttonId.StartsWith("draw_faceup:"))
        {
            if (!int.TryParse(buttonId.AsSpan(buttonId.IndexOf(':') + 1), out int idx)) return;
            if (idx < 0 || idx >= _faceUp.Count) return;

            string card = _faceUp[idx];

            if (_drewFirstCard)
            {
                // Second draw — cannot take locomotive
                if (card == "locomotive") return;
                _hands[seat].Add(card);
                ReplaceAndRefill(idx);
                SetEvent($"🃏 {PlayerName(seat)} drew a {card} card");
                _drewFirstCard = false;
                AdvanceTurn();
            }
            else
            {
                // First draw
                _hands[seat].Add(card);
                ReplaceAndRefill(idx);

                if (card == "locomotive")
                {
                    // Locomotive counts as both draws
                    SetEvent($"🚂 {PlayerName(seat)} drew a locomotive!");
                    AdvanceTurn();
                }
                else
                {
                    _drewFirstCard = true;
                    _phase = "draw_second";
                    SetEvent($"🃏 {PlayerName(seat)} drew a {card} card (1 more)");
                    RefreshButtons();
                }
            }
            return;
        }

        // ── Draw from deck ──
        if (buttonId == "draw_deck")
        {
            if (_drawPile.Count == 0 && _discardPile.Count == 0) return;
            string card = DrawCardFromPile();
            _hands[seat].Add(card);

            if (_drewFirstCard)
            {
                SetEvent($"🃏 {PlayerName(seat)} drew from deck");
                _drewFirstCard = false;
                AdvanceTurn();
            }
            else
            {
                _drewFirstCard = true;
                _phase = "draw_second";
                SetEvent($"🃏 {PlayerName(seat)} drew from deck (1 more)");
                RefreshButtons();
            }
            return;
        }

        // ── Claim route ──
        if (buttonId.StartsWith("claim_route:"))
        {
            if (_drewFirstCard) return; // can't claim after drawing
            if (!int.TryParse(buttonId.AsSpan(buttonId.IndexOf(':') + 1), out int ri)) return;
            if (ClaimRoute(seat, ri))
                AdvanceTurn();
            return;
        }

        // ── Draw tickets ──
        if (buttonId == "draw_tickets")
        {
            if (_drewFirstCard) return;
            var drawn = DrawTickets(3);
            if (drawn.Count == 0) return;
            _pendingTickets[seat] = drawn;
            _pendingKeepMin[seat] = 1; // must keep at least 1 during game
            _phase = "pick_tickets";
            SetEvent($"🎫 {PlayerName(seat)} is choosing destination tickets");
            RefreshButtons();
            return;
        }

        // ── Pass turn (when stuck with no actions) ──
        if (buttonId == "pass_turn")
        {
            SetEvent($"⏭️ {PlayerName(seat)} passed (no actions available)");
            _drewFirstCard = false;
            AdvanceTurn();
        }
    }

    public override void HandleMessage(int playerIdx, string type, string json) { }

    // ═════════════════════════════════════════════════════════════
    //  GetSnapshot
    // ═════════════════════════════════════════════════════════════
    public override Dictionary<string, object?> GetSnapshot(int playerIdx)
    {
        int seat = playerIdx;
        var hand = _hands.GetValueOrDefault(seat, new List<string>());

        // Hand counts
        var handCounts = new Dictionary<string, object?>();
        foreach (var c in hand)
        {
            int cur = handCounts.TryGetValue(c, out var v) && v is int iv ? iv : 0;
            handCounts[c] = cur + 1;
        }

        // My tickets (with completion status)
        var myTickets = new List<object?>();
        foreach (var t in _tickets.GetValueOrDefault(seat, new List<TicketData>()))
        {
            myTickets.Add(new Dictionary<string, object?>
            {
                ["city_a"] = t.CityA,
                ["city_b"] = t.CityB,
                ["points"] = t.Points,
                ["complete"] = IsTicketComplete(seat, t),
            });
        }

        // Pending tickets (for selection)
        var pendingList = new List<object?>();
        if (_pendingTickets.TryGetValue(seat, out var pend))
        {
            foreach (var t in pend)
                pendingList.Add(new Dictionary<string, object?>
                {
                    ["city_a"] = t.CityA,
                    ["city_b"] = t.CityB,
                    ["points"] = t.Points,
                });
        }

        // All players summary
        var players = new List<object?>();
        foreach (var s in ActivePlayers)
        {
            players.Add(new Dictionary<string, object?>
            {
                ["seat"] = s,
                ["hand_count"] = _hands.GetValueOrDefault(s)?.Count ?? 0,
                ["ticket_count"] = _tickets.GetValueOrDefault(s)?.Count ?? 0,
                ["trains_left"] = _trainsLeft.GetValueOrDefault(s, 0),
                ["score"] = _scores.GetValueOrDefault(s, 0),
                ["routes_claimed"] = _playerRoutes.GetValueOrDefault(s)?.Count ?? 0,
            });
        }

        // Claimed routes for rendering
        var claimed = new Dictionary<string, object?>();
        foreach (var (ri, owner) in _claimedRoutes)
            claimed[ri.ToString()] = owner;

        // Scores dict
        var scoresDict = new Dictionary<string, object?>();
        foreach (var s in ActivePlayers)
            scoresDict[s.ToString()] = _scores.GetValueOrDefault(s, 0);

        return new Dictionary<string, object?>
        {
            ["ticket_to_ride"] = new Dictionary<string, object?>
            {
                ["phase"] = _phase,
                ["current_turn_seat"] = CurrentTurnSeat,
                ["hand"] = hand.Cast<object?>().ToList(),
                ["hand_counts"] = handCounts,
                ["my_tickets"] = myTickets,
                ["pending_tickets"] = pendingList,
                ["players"] = players,
                ["face_up"] = _faceUp.Cast<object?>().ToList(),
                ["draw_pile_count"] = _drawPile.Count,
                ["ticket_pile_count"] = _ticketPile.Count,
                ["claimed_routes"] = claimed,
                ["winner"] = _winner,
                ["last_event"] = _lastEvent,
                ["scores"] = scoresDict,
            },
        };
    }

    // ═════════════════════════════════════════════════════════════
    //  GetPanelButtons
    // ═════════════════════════════════════════════════════════════
    public override List<Dictionary<string, object?>> GetPanelButtons(int playerIdx)
    {
        if (!_buttons.TryGetValue(playerIdx, out var btns))
            return new List<Dictionary<string, object?>>();

        var result = new List<Dictionary<string, object?>>();
        foreach (var (id, (text, enabled)) in btns)
        {
            result.Add(new Dictionary<string, object?>
            {
                ["id"] = id,
                ["text"] = text,
                ["enabled"] = enabled,
            });
        }
        return result;
    }

    // ═════════════════════════════════════════════════════════════
    //  Card drawing helpers
    // ═════════════════════════════════════════════════════════════

    private string DrawCardFromPile()
    {
        if (_drawPile.Count == 0) ReshuffleDiscard();
        if (_drawPile.Count > 0) return PopLast(_drawPile);
        return "locomotive"; // fallback
    }

    private void ReshuffleDiscard()
    {
        if (_discardPile.Count == 0) return;
        _drawPile.AddRange(_discardPile);
        _discardPile.Clear();
        ShuffleList(_drawPile);
    }

    private List<TicketData> DrawTickets(int n)
    {
        var result = new List<TicketData>();
        for (int i = 0; i < n && _ticketPile.Count > 0; i++)
            result.Add(PopLast(_ticketPile));
        return result;
    }

    private void CheckFaceUpLocomotives()
    {
        for (int attempt = 0; attempt < 10; attempt++)
        {
            int locos = _faceUp.Count(c => c == "locomotive");
            if (locos < 3) return;
            _discardPile.AddRange(_faceUp);
            _faceUp.Clear();
            for (int i = 0; i < FaceUpCount && _drawPile.Count > 0; i++)
                _faceUp.Add(PopLast(_drawPile));
            if (_drawPile.Count == 0) return;
        }
    }

    private void RefillFaceUp()
    {
        while (_faceUp.Count < FaceUpCount && _drawPile.Count > 0)
            _faceUp.Add(PopLast(_drawPile));
        CheckFaceUpLocomotives();
    }

    private void ReplaceAndRefill(int idx)
    {
        if (_drawPile.Count > 0)
            _faceUp[idx] = PopLast(_drawPile);
        else
            _faceUp.RemoveAt(idx);
        _faceUp.RemoveAll(string.IsNullOrEmpty);
        RefillFaceUp();
    }

    // ═════════════════════════════════════════════════════════════
    //  Route claiming
    // ═════════════════════════════════════════════════════════════

    private List<string>? CanClaimRoute(int seat, int ri)
    {
        if (ri < 0 || ri >= Routes.Count) return null;
        var route = Routes[ri];

        // Already claimed?
        if (_claimedRoutes.ContainsKey(ri)) return null;

        // Parallel route rules
        if (ActivePlayers.Count <= 3)
        {
            // 2-3 players: only one of a double pair can be claimed by anyone
            for (int other = 0; other < Routes.Count; other++)
            {
                if (other == ri) continue;
                var r = Routes[other];
                if ((r.CityA == route.CityA && r.CityB == route.CityB) ||
                    (r.CityA == route.CityB && r.CityB == route.CityA))
                {
                    if (_claimedRoutes.ContainsKey(other)) return null;
                }
            }
        }
        else
        {
            // 4-5 players: same player can't claim both parallels
            for (int other = 0; other < Routes.Count; other++)
            {
                if (other == ri) continue;
                var r = Routes[other];
                if ((r.CityA == route.CityA && r.CityB == route.CityB) ||
                    (r.CityA == route.CityB && r.CityB == route.CityA))
                {
                    if (_claimedRoutes.TryGetValue(other, out int owner) && owner == seat)
                        return null;
                }
            }
        }

        // Enough trains?
        if (_trainsLeft.GetValueOrDefault(seat, 0) < route.Length) return null;

        var hand = _hands.GetValueOrDefault(seat, new List<string>());
        if (route.Color == "gray")
        {
            // Try each colour, pick best (fewest locomotives)
            List<string>? best = null;
            foreach (var tryColor in TrainColors)
            {
                var cards = PickCardsForRoute(hand, tryColor, route.Length);
                if (cards != null)
                {
                    if (best == null ||
                        cards.Count(c => c == "locomotive") < best.Count(c => c == "locomotive"))
                        best = cards;
                }
            }
            return best;
        }
        return PickCardsForRoute(hand, route.Color, route.Length);
    }

    private static List<string>? PickCardsForRoute(List<string> hand, string color, int needed)
    {
        int colorCount = hand.Count(c => c == color);
        int locoCount = hand.Count(c => c == "locomotive");
        if (colorCount + locoCount < needed) return null;

        var cards = new List<string>();
        int remaining = needed;
        // Use coloured cards first, then locomotives
        foreach (var c in hand)
        {
            if (remaining <= 0) break;
            if (c == color) { cards.Add(c); remaining--; }
        }
        foreach (var c in hand)
        {
            if (remaining <= 0) break;
            if (c == "locomotive") { cards.Add(c); remaining--; }
        }
        return cards.Count == needed ? cards : null;
    }

    private bool ClaimRoute(int seat, int ri)
    {
        var cards = CanClaimRoute(seat, ri);
        if (cards == null) return false;

        var route = Routes[ri];
        var hand = _hands[seat];
        foreach (var c in cards) hand.Remove(c);
        _discardPile.AddRange(cards);

        _claimedRoutes[ri] = seat;
        _playerRoutes[seat].Add(ri);
        _trainsLeft[seat] -= route.Length;

        int pts = RouteScores.GetValueOrDefault(route.Length, route.Length);
        _scores[seat] += pts;

        SetEvent($"🛤️ {PlayerName(seat)} claimed {route.CityA}→{route.CityB} (+{pts}pts)");
        return true;
    }

    // ═════════════════════════════════════════════════════════════
    //  Ticket completion (BFS)
    // ═════════════════════════════════════════════════════════════

    private bool IsTicketComplete(int seat, TicketData ticket)
    {
        var adj = new Dictionary<string, HashSet<string>>();
        foreach (int ri in _playerRoutes.GetValueOrDefault(seat, new List<int>()))
        {
            var r = Routes[ri];
            if (!adj.ContainsKey(r.CityA)) adj[r.CityA] = new HashSet<string>();
            if (!adj.ContainsKey(r.CityB)) adj[r.CityB] = new HashSet<string>();
            adj[r.CityA].Add(r.CityB);
            adj[r.CityB].Add(r.CityA);
        }

        if (!adj.ContainsKey(ticket.CityA)) return false;

        var visited = new HashSet<string>();
        var queue = new Queue<string>();
        queue.Enqueue(ticket.CityA);
        while (queue.Count > 0)
        {
            var city = queue.Dequeue();
            if (city == ticket.CityB) return true;
            if (!visited.Add(city)) continue;
            if (adj.TryGetValue(city, out var neighbors))
                foreach (var n in neighbors)
                    if (!visited.Contains(n)) queue.Enqueue(n);
        }
        return false;
    }

    // ═════════════════════════════════════════════════════════════
    //  Longest continuous path (DFS with backtracking)
    // ═════════════════════════════════════════════════════════════

    private int LongestPath(int seat)
    {
        var routes = _playerRoutes.GetValueOrDefault(seat, new List<int>());
        if (routes.Count == 0) return 0;

        // Build edge list
        var edges = new List<(string A, string B, int Length)>();
        foreach (int ri in routes)
        {
            var r = Routes[ri];
            edges.Add((r.CityA, r.CityB, r.Length));
        }

        // Build adjacency
        var adj = new Dictionary<string, List<(string Neighbor, int Length, int EdgeIdx)>>();
        for (int i = 0; i < edges.Count; i++)
        {
            var (a, b, l) = edges[i];
            if (!adj.ContainsKey(a)) adj[a] = new();
            if (!adj.ContainsKey(b)) adj[b] = new();
            adj[a].Add((b, l, i));
            adj[b].Add((a, l, i));
        }

        int best = 0;
        var used = new HashSet<int>();

        void Dfs(string city, int total)
        {
            if (total > best) best = total;
            if (!adj.TryGetValue(city, out var neighbors)) return;
            foreach (var (neighbor, length, edgeIdx) in neighbors)
            {
                if (used.Contains(edgeIdx)) continue;
                used.Add(edgeIdx);
                Dfs(neighbor, total + length);
                used.Remove(edgeIdx);
            }
        }

        foreach (var city in adj.Keys)
            Dfs(city, 0);

        return best;
    }

    // ═════════════════════════════════════════════════════════════
    //  Turn management
    // ═════════════════════════════════════════════════════════════

    private void AdvanceTurn()
    {
        _currentTurnIdx = (_currentTurnIdx + 1) % ActivePlayers.Count;
        _drewFirstCard = false;

        // Check last-round end
        if (_lastRoundStarted)
        {
            if (CurrentTurnSeat == _lastRoundTriggerSeat)
            {
                EndGame();
                return;
            }
        }

        // Check if someone triggered last round
        int turnSeat = CurrentTurnSeat;
        if (_trainsLeft.GetValueOrDefault(turnSeat, 99) <= 2 && !_lastRoundStarted)
        {
            _lastRoundStarted = true;
            _lastRoundTriggerSeat = turnSeat;
            SetEvent($"⚠️ {PlayerName(turnSeat)} has ≤2 trains! Last round!");
        }

        _phase = "play";
        RefreshButtons();
    }

    // ═════════════════════════════════════════════════════════════
    //  End game scoring
    // ═════════════════════════════════════════════════════════════

    private void EndGame()
    {
        _phase = "game_over";

        // Add ticket bonuses / penalties
        foreach (var seat in ActivePlayers)
        {
            foreach (var ticket in _tickets.GetValueOrDefault(seat, new List<TicketData>()))
            {
                if (IsTicketComplete(seat, ticket))
                    _scores[seat] += ticket.Points;
                else
                    _scores[seat] -= ticket.Points;
            }
        }

        // Longest path bonus (10 pts to each player tied for longest)
        var longest = new Dictionary<int, int>();
        foreach (var seat in ActivePlayers)
            longest[seat] = LongestPath(seat);

        int maxPath = longest.Values.DefaultIfEmpty(0).Max();
        if (maxPath >= 1)
        {
            foreach (var seat in ActivePlayers)
                if (longest[seat] == maxPath)
                    _scores[seat] += 10;
        }

        // Determine winner
        int bestScore = _scores.Values.DefaultIfEmpty(0).Max();
        foreach (var seat in ActivePlayers)
        {
            if (_scores[seat] == bestScore)
            {
                _winner = seat;
                break;
            }
        }

        SetEvent($"🏆 {PlayerName(_winner ?? 0)} wins with {bestScore} points!");
        RefreshButtons();
    }

    // ═════════════════════════════════════════════════════════════
    //  Buttons
    // ═════════════════════════════════════════════════════════════

    private void RefreshButtons()
    {
        _buttons.Clear();
        foreach (var seat in ActivePlayers)
        {
            var btns = new Dictionary<string, (string Text, bool Enabled)>();

            // Ticket selection
            if (_phase == "pick_tickets" && _pendingTickets.TryGetValue(seat, out var pending))
            {
                for (int i = 0; i < pending.Count; i++)
                {
                    var t = pending[i];
                    btns[$"keep_ticket:{i}"] = ($"Keep: {t.CityA} → {t.CityB} ({t.Points}pts)", true);
                }
                btns["done_tickets"] = ("✅ Done choosing tickets", true);
                _buttons[seat] = btns;
                continue;
            }

            // Not your turn or game over
            if (seat != CurrentTurnSeat || _phase == "game_over")
            {
                _buttons[seat] = btns;
                continue;
            }

            if (_phase == "draw_second")
            {
                // Must draw second card (no locomotive from face-up)
                for (int i = 0; i < _faceUp.Count; i++)
                {
                    var card = _faceUp[i];
                    if (!string.IsNullOrEmpty(card) && card != "locomotive")
                        btns[$"draw_faceup:{i}"] = ($"🃏 Take {card}", true);
                }
                if (_drawPile.Count > 0 || _discardPile.Count > 0)
                    btns["draw_deck"] = ("🎴 Draw from deck", true);
                // If nothing to draw, let player pass
                if (btns.Count == 0)
                    btns["pass_turn"] = ("⏭️ End turn (no cards left)", true);
                _buttons[seat] = btns;
                continue;
            }

            // Normal turn: 3 action types
            // Face-up cards
            for (int i = 0; i < _faceUp.Count; i++)
            {
                var card = _faceUp[i];
                if (!string.IsNullOrEmpty(card))
                {
                    string emoji = card == "locomotive" ? "🚂" : "🃏";
                    btns[$"draw_faceup:{i}"] = ($"{emoji} Take {card}", true);
                }
            }
            // Draw from deck
            if (_drawPile.Count > 0 || _discardPile.Count > 0)
                btns["draw_deck"] = ("🎴 Draw from deck", true);

            // Claimable routes
            for (int ri = 0; ri < Routes.Count; ri++)
            {
                if (CanClaimRoute(seat, ri) != null)
                {
                    var route = Routes[ri];
                    btns[$"claim_route:{ri}"] = ($"🛤️ {route.CityA} → {route.CityB} ({route.Length})", true);
                }
            }

            // Draw tickets
            if (_ticketPile.Count > 0)
                btns["draw_tickets"] = ("🎫 Draw tickets", true);

            // If completely stuck (no cards, no routes, no tickets), let player pass
            if (btns.Count == 0)
                btns["pass_turn"] = ("⏭️ Pass turn (no actions)", true);

            _buttons[seat] = btns;
        }
    }

    private void SetEvent(string msg) => _lastEvent = msg;

    // ═════════════════════════════════════════════════════════════
    //  Update
    // ═════════════════════════════════════════════════════════════
    public override void Update(double dt)
    {
        float f = (float)dt;
        _particles.Update(f);
        for (int i = _pulseRings.Count - 1; i >= 0; i--)
        {
            _pulseRings[i].Update(f);
            if (_pulseRings[i].Done) _pulseRings.RemoveAt(i);
        }
        _ambient.Update(f, ScreenW, ScreenH);
        _starfield.Update(f);
    }

    // ═════════════════════════════════════════════════════════════
    //  Draw
    // ═════════════════════════════════════════════════════════════
    public override void Draw(Renderer r, int width, int height, double dt)
    {
        _totalElapsed += dt;
        if (State == "player_select") { base.Draw(r, width, height, dt); return; }

        CardRendering.DrawGameBackground(r, width, height, "ticket_to_ride");
        _ambient.Draw(r);
        _starfield.Draw(r);
        RainbowTitle.Draw(r, "TICKET TO RIDE", width);

        // ── Subtitle status bar ──
        string subtitle = State == "playing"
            ? $"🚂 Phase: {PhaseLabel(_phase)}  |  Players: {ActivePlayers.Count}"
            : "Select players in Web UI";
        {
            int sw = width - 32, sh = 28, sx = 16, sy = 48;
            r.DrawRect((0, 0, 0), (sx + 2, sy + 2, sw, sh), alpha: 50);
            r.DrawRect((18, 22, 32), (sx, sy, sw, sh), alpha: 200);
            r.DrawRect((60, 140, 200), (sx, sy, sw, 3), alpha: 80);
            r.DrawRect((40, 100, 160), (sx, sy, sw, sh), width: 1, alpha: 150);
            r.DrawText(subtitle, sx + 12, sy + sh / 2, 13, (190, 210, 230), anchorX: "left", anchorY: "center");
        }

        if (State != "playing") return;

        // ── Layout constants ──
        int headerH = 84;
        int footerH = 30;
        int sidePanel = 240; // right panel for face-up cards + scores
        int mapW = width - sidePanel - 32;
        int mapH = height - headerH - footerH;
        int mapX = 16;
        int mapY = headerH;

        // ── Map background ──
        r.DrawRect((0, 0, 0), (mapX + 2, mapY + 2, mapW, mapH), alpha: 40);
        r.DrawRect((10, 14, 20), (mapX, mapY, mapW, mapH), alpha: 230);
        r.DrawRect((40, 80, 130), (mapX, mapY, mapW, 3), alpha: 70);
        r.DrawRect((30, 60, 100), (mapX, mapY, mapW, mapH), width: 1, alpha: 130);

        // Convert normalised city coords to pixel coords
        float padX = mapW * 0.06f, padY = mapH * 0.06f;
        float drawW = mapW - 2 * padX;
        float drawH = mapH - 2 * padY;

        (int, int) CityPixel(string name)
        {
            if (!Cities.TryGetValue(name, out var c))
                return (mapX + mapW / 2, mapY + mapH / 2);
            return (mapX + (int)(padX + c.X * drawW), mapY + (int)(padY + c.Y * drawH));
        }

        // ── Draw routes ──
        for (int ri = 0; ri < Routes.Count; ri++)
        {
            var route = Routes[ri];
            var (ax, ay) = CityPixel(route.CityA);
            var (bx, by) = CityPixel(route.CityB);

            // Offset parallel routes perpendicular
            if (route.Parallel != 0)
            {
                float dx2 = bx - ax, dy2 = by - ay;
                float len2 = MathF.Sqrt(dx2 * dx2 + dy2 * dy2);
                if (len2 > 0)
                {
                    float nx = -dy2 / len2 * 6, ny = dx2 / len2 * 6;
                    int sign = route.Parallel == 0 ? -1 : 1;
                    ax += (int)(nx * sign); ay += (int)(ny * sign);
                    bx += (int)(nx * sign); by += (int)(ny * sign);
                }
            }

            bool claimed = _claimedRoutes.ContainsKey(ri);
            if (claimed)
            {
                int owner = _claimedRoutes[ri];
                var pCol = PlayerPalette[owner % PlayerPalette.Length];
                // Glow behind claimed route
                r.DrawLine(pCol, (ax, ay), (bx, by), width: 8, alpha: 35);
                r.DrawLine(pCol, (ax, ay), (bx, by), width: 4, alpha: 230);
                // Draw train car pips along claimed route
                float dx = bx - ax, dy = by - ay;
                float segLen = MathF.Sqrt(dx * dx + dy * dy);
                if (segLen > 10 && route.Length > 0)
                {
                    float step = segLen / (route.Length + 1);
                    for (int d = 1; d <= route.Length; d++)
                    {
                        float t = d * step / segLen;
                        int mx = ax + (int)(dx * t), my = ay + (int)(dy * t);
                        r.DrawCircle(pCol, (mx, my), 4, alpha: 255);
                        r.DrawCircle((255, 255, 255), (mx, my), 2, alpha: 180);
                    }
                }
            }
            else
            {
                var rCol = ColorRgb.GetValueOrDefault(route.Color, (140, 140, 145));
                r.DrawLine(rCol, (ax, ay), (bx, by), width: 2, alpha: 70);
                // Draw empty car slots
                float dx = bx - ax, dy = by - ay;
                float segLen = MathF.Sqrt(dx * dx + dy * dy);
                if (segLen > 10 && route.Length > 0)
                {
                    float step = segLen / (route.Length + 1);
                    for (int d = 1; d <= route.Length; d++)
                    {
                        float t = d * step / segLen;
                        int mx = ax + (int)(dx * t), my = ay + (int)(dy * t);
                        r.DrawCircle((0, 0, 0), (mx, my), 4, alpha: 50);
                        r.DrawCircle(rCol, (mx, my), 3, alpha: 80);
                    }
                }
                // Show route length number at midpoint for routes ≥ 3
                if (segLen > 30 && route.Length >= 3 && route.Parallel == 0)
                {
                    int midX = (ax + bx) / 2, midY = (ay + by) / 2;
                    r.DrawCircle((0, 0, 0), (midX, midY + 1), 7, alpha: 120);
                    r.DrawCircle((20, 24, 32), (midX, midY), 7, alpha: 200);
                    r.DrawText(route.Length.ToString(), midX, midY, 8, rCol,
                        anchorX: "center", anchorY: "center", bold: true, alpha: 220);
                }
            }
        }

        // ── Draw cities ──
        foreach (var (name, _) in Cities)
        {
            var (cx, cy) = CityPixel(name);
            // City dot with subtle glow
            r.DrawCircle((120, 180, 255), (cx, cy), 10, alpha: 20);
            r.DrawCircle((200, 220, 240), (cx, cy), 6, alpha: 200);
            r.DrawCircle((255, 255, 255), (cx, cy), 3, alpha: 255);

            // City name with dark background pill for readability
            int fs = Math.Max(8, Math.Min(11, mapW / 100));
            int lblW = name.Length * (fs - 2) + 8;
            int lblH = fs + 6;
            int lblX = cx - lblW / 2, lblY = cy - 14 - lblH;
            r.DrawRect((0, 0, 0), (lblX, lblY, lblW, lblH), alpha: 140);
            r.DrawRect((20, 28, 40), (lblX, lblY, lblW, lblH), width: 1, alpha: 80);
            r.DrawText(name, cx, lblY + lblH / 2, fs, (220, 230, 240),
                anchorX: "center", anchorY: "center", alpha: 230);
        }

        // ── Current turn / phase indicator (bottom of map) ──
        int turnSeat = CurrentTurnSeat;
        if (turnSeat >= 0)
        {
            var turnCol = PlayerPalette[turnSeat % PlayerPalette.Length];
            string turnName = PlayerName(turnSeat);
            string phaseEmoji = _phase switch
            {
                "draw_second" => "🃏",
                "pick_tickets" => "🎫",
                "last_round" => "⚠️",
                "game_over" => "🏆",
                _ => "🚂",
            };
            string turnLabel = $"{phaseEmoji}  {turnName}'s Turn  —  {PhaseLabel(_phase)}";
            int tw = Math.Max(260, turnLabel.Length * 8 + 40);
            int tx = mapX + mapW / 2 - tw / 2, ty = mapY + mapH - 34;
            r.DrawRect((0, 0, 0), (tx + 2, ty + 2, tw, 28), alpha: 50);
            r.DrawRect((10, 14, 20), (tx, ty, tw, 28), alpha: 220);
            r.DrawRect(turnCol, (tx, ty, tw, 3), alpha: 200);
            r.DrawRect(turnCol, (tx, ty, tw, 28), width: 1, alpha: 120);
            r.DrawText(turnLabel, tx + tw / 2, ty + 14, 12, turnCol,
                anchorX: "center", anchorY: "center", bold: true);

            // Last-round warning bar
            if (_lastRoundStarted && _phase != "game_over")
            {
                int warnW = Math.Max(200, 200);
                int warnX = mapX + mapW / 2 - warnW / 2, warnY = ty - 26;
                int pulseAlpha = 140 + (int)(40 * MathF.Sin((float)(_totalElapsed * 3)));
                r.DrawRect((120, 40, 20), (warnX, warnY, warnW, 22), alpha: pulseAlpha);
                r.DrawRect((200, 80, 40), (warnX, warnY, warnW, 22), width: 1, alpha: 180);
                r.DrawText("⚠️ LAST ROUND!", warnX + warnW / 2, warnY + 11, 11,
                    (255, 220, 100), anchorX: "center", anchorY: "center", bold: true);
            }
        }

        // ── Right panel: Face-up cards + Player scores ──
        int rpX = width - sidePanel - 8;
        int rpY = headerH;
        int rpW = sidePanel;
        int rpH = mapH;

        // Panel background
        r.DrawRect((0, 0, 0), (rpX + 2, rpY + 2, rpW, rpH), alpha: 40);
        r.DrawRect((12, 16, 22), (rpX, rpY, rpW, rpH), alpha: 220);
        r.DrawRect((50, 120, 190), (rpX, rpY, rpW, 3), alpha: 90);
        r.DrawRect((30, 60, 100), (rpX, rpY, rpW, rpH), width: 1, alpha: 130);

        int panelY = rpY + 12;

        // ── Face-up cards section ──
        r.DrawText("FACE-UP CARDS", rpX + rpW / 2, panelY, 11, (140, 160, 180),
            anchorX: "center", anchorY: "top", bold: true);
        panelY += 20;

        int cardW = (rpW - 40) / 5;
        int cardH = Math.Max(28, cardW * 3 / 2);
        int cardsStartX = rpX + (rpW - (5 * cardW + 4 * 4)) / 2;
        for (int i = 0; i < FaceUpCount; i++)
        {
            int cx = cardsStartX + i * (cardW + 4);
            if (i < _faceUp.Count)
            {
                var cCol = ColorRgb.GetValueOrDefault(_faceUp[i], (140, 140, 145));
                // Card shadow
                r.DrawRect((0, 0, 0), (cx + 2, panelY + 2, cardW, cardH), alpha: 70);
                // Card body with gradient feel
                r.DrawRect(cCol, (cx, panelY, cardW, cardH), alpha: 230);
                // Top highlight line
                r.DrawRect((255, 255, 255), (cx + 2, panelY + 1, cardW - 4, 1), alpha: 50);
                // Border
                r.DrawRect((255, 255, 255), (cx, panelY, cardW, cardH), width: 1, alpha: 60);
                // Card type label
                bool isLoco = _faceUp[i] == "locomotive";
                string cardLabel = isLoco ? "🚂" : "";
                if (!isLoco)
                {
                    // Show a coloured pip
                    r.DrawCircle(cCol, (cx + cardW / 2, panelY + cardH / 2), 5, alpha: 255);
                    r.DrawCircle((255, 255, 255), (cx + cardW / 2, panelY + cardH / 2), 3, alpha: 120);
                }
                else
                {
                    r.DrawText(cardLabel, cx + cardW / 2, panelY + cardH / 2, 11,
                        (255, 255, 255), anchorX: "center", anchorY: "center");
                }
            }
            else
            {
                // Empty slot
                r.DrawRect((30, 34, 44), (cx, panelY, cardW, cardH), alpha: 100);
                r.DrawRect((50, 60, 70), (cx, panelY, cardW, cardH), width: 1, alpha: 50);
            }
        }
        panelY += cardH + 6;

        // Deck + ticket info row
        {
            int infoX = rpX + 10;
            // Draw pile with visual indicator
            var deckCol = _drawPile.Count > 0 ? (100, 160, 220) : (100, 60, 60);
            r.DrawText($"🃏 Deck: {_drawPile.Count}", infoX, panelY, 10, deckCol,
                anchorX: "left", anchorY: "top");
            r.DrawText($"🎫 Tickets: {_ticketPile.Count}", rpX + rpW / 2, panelY, 10, (140, 170, 190),
                anchorX: "left", anchorY: "top");
            panelY += 18;
        }

        // Divider
        r.DrawRect((50, 90, 140), (rpX + 8, panelY, rpW - 16, 1), alpha: 50);
        panelY += 8;

        // ── Player panels ──
        r.DrawText("PLAYERS", rpX + rpW / 2, panelY, 11, (140, 160, 180),
            anchorX: "center", anchorY: "top", bold: true);
        panelY += 20;

        foreach (var seat in ActivePlayers)
        {
            int score = _scores.GetValueOrDefault(seat, 0);
            int handCount = _hands.GetValueOrDefault(seat)?.Count ?? 0;
            int ticketCount = _tickets.GetValueOrDefault(seat)?.Count ?? 0;
            int trainsLeft = _trainsLeft.GetValueOrDefault(seat, 0);
            int routesCnt = _playerRoutes.GetValueOrDefault(seat)?.Count ?? 0;
            bool isCurrentTurn = seat == turnSeat;

            var pCol = PlayerPalette[seat % PlayerPalette.Length];
            int pHeight = 64;
            int px = rpX + 6, pw = rpW - 12;

            // Pulsing highlight for current player
            if (isCurrentTurn)
            {
                int pulseA = 18 + (int)(14 * MathF.Sin((float)(_totalElapsed * 2.5)));
                r.DrawRect(pCol, (px - 2, panelY - 2, pw + 4, pHeight + 4), alpha: pulseA);
            }

            // Player card background
            r.DrawRect((0, 0, 0), (px + 1, panelY + 1, pw, pHeight), alpha: 40);
            r.DrawRect((16, 20, 28), (px, panelY, pw, pHeight), alpha: 210);
            r.DrawRect(pCol, (px, panelY, pw, 3), alpha: 180);
            r.DrawRect(pCol, (px, panelY, pw, pHeight), width: 1, alpha: isCurrentTurn ? 120 : 50);

            // Name + colour dot
            string pName = PlayerName(seat);
            r.DrawCircle(pCol, (px + 12, panelY + 14), 5, alpha: 220);
            r.DrawText(pName, px + 24, panelY + 7, 11, pCol,
                anchorX: "left", anchorY: "top", bold: true);

            // Score prominently on the right
            r.DrawText($"{score}", px + pw - 8, panelY + 7, 13, (255, 255, 255),
                anchorX: "right", anchorY: "top", bold: true, alpha: 240);
            r.DrawText("pts", px + pw - 8, panelY + 22, 8, (120, 130, 145),
                anchorX: "right", anchorY: "top");

            // Train count with visual bar
            float trainPct = trainsLeft / (float)InitialTrains;
            int barW = pw - 20, barH = 4;
            int barX = px + 10, barY = panelY + 28;
            r.DrawRect((30, 34, 44), (barX, barY, barW, barH), alpha: 120);
            int fillW = (int)(barW * trainPct);
            var barCol = trainPct > 0.3f ? (60, 180, 100) : trainPct > 0.1f ? (220, 160, 40) : (200, 50, 50);
            if (fillW > 0)
                r.DrawRect(barCol, (barX, barY, fillW, barH), alpha: 200);

            // Stats: trains, cards, tickets, routes — spread across two rows
            r.DrawText($"🚂 {trainsLeft}", px + 8, panelY + 36, 9, (170, 185, 200),
                anchorX: "left", anchorY: "top");
            r.DrawText($"🃏 {handCount}", px + 60, panelY + 36, 9, (170, 185, 200),
                anchorX: "left", anchorY: "top");
            r.DrawText($"🎫 {ticketCount}", px + 108, panelY + 36, 9, (170, 185, 200),
                anchorX: "left", anchorY: "top");
            r.DrawText($"📍 {routesCnt}", px + 156, panelY + 36, 9, (170, 185, 200),
                anchorX: "left", anchorY: "top");

            // Completed ticket count
            int completedTickets = 0;
            foreach (var t in _tickets.GetValueOrDefault(seat, new List<TicketData>()))
                if (IsTicketComplete(seat, t)) completedTickets++;
            int totalTickets = _tickets.GetValueOrDefault(seat)?.Count ?? 0;
            if (totalTickets > 0)
            {
                var tCol = completedTickets == totalTickets ? (80, 220, 120) : (180, 180, 100);
                r.DrawText($"✅ {completedTickets}/{totalTickets} tickets done", px + 8, panelY + 50, 8,
                    tCol, anchorX: "left", anchorY: "top");
            }

            panelY += pHeight + 4;
        }

        // ── Event line (below subtitle bar) ──
        if (!string.IsNullOrEmpty(_lastEvent))
        {
            int evY = mapY - 2;
            int ew = mapW + rpW + 16;
            int esh = 22;
            r.DrawRect((0, 0, 0), (mapX + 1, evY + 1, ew, esh), alpha: 40);
            r.DrawRect((14, 18, 26), (mapX, evY, ew, esh), alpha: 195);
            r.DrawRect((80, 160, 220), (mapX, evY, ew, 2), alpha: 70);
            r.DrawText($"📢  {_lastEvent}", mapX + 10, evY + esh / 2, 10, (180, 200, 215),
                anchorX: "left", anchorY: "center");
        }

        // ── Winner overlay ──
        if (_winner is int wi)
        {
            r.DrawRect((0, 0, 0), (0, 0, width, height), alpha: 160);
            int bw = Math.Min(620, width * 55 / 100), bh = 180;
            int bxc = width / 2 - bw / 2, byc = height / 2 - bh / 2;
            var wCol = PlayerPalette[wi % PlayerPalette.Length];
            r.DrawRect((0, 0, 0), (bxc + 4, byc + 4, bw, bh), alpha: 70);
            r.DrawRect((8, 8, 14), (bxc, byc, bw, bh), alpha: 240);
            r.DrawRect(wCol, (bxc, byc, bw, 5), alpha: 220);
            r.DrawRect(wCol, (bxc, byc, bw, bh), width: 3, alpha: 220);
            int ins = 8;
            r.DrawRect(wCol, (bxc + ins, byc + ins, bw - 2 * ins, bh - 2 * ins), width: 1, alpha: 30);
            r.DrawText("🏆", width / 2, byc + 30, 32,
                (255, 215, 0), anchorX: "center", anchorY: "center");
            r.DrawText($"Winner: {PlayerName(wi)}", width / 2, height / 2, 30,
                wCol, anchorX: "center", anchorY: "center", bold: true);
            r.DrawText($"{_scores.GetValueOrDefault(wi, 0)} points", width / 2, height / 2 + 36, 16,
                (200, 210, 220), anchorX: "center", anchorY: "center");
        }

        // ── Footer ──
        r.DrawText($"🗺️ {Routes.Count} routes  |  {Cities.Count} cities", width - 16, height - 12,
            9, (100, 110, 120), anchorX: "right", anchorY: "bottom");

        // Animations
        _particles.Draw(r);
        foreach (var pr in _pulseRings) pr.Draw(r);
    }

    // ═════════════════════════════════════════════════════════════
    //  Utility helpers
    // ═════════════════════════════════════════════════════════════

    private static string PhaseLabel(string phase) => phase switch
    {
        "play" => "Main Turn",
        "draw_second" => "Draw Second Card",
        "pick_tickets" => "Picking Tickets",
        "last_round" => "Last Round!",
        "game_over" => "Game Over",
        _ => phase,
    };

    private void ShuffleList<T>(List<T> list)
    {
        for (int i = list.Count - 1; i > 0; i--)
        {
            int j = Rng.Next(i + 1);
            (list[i], list[j]) = (list[j], list[i]);
        }
    }

    private static T PopLast<T>(List<T> list)
    {
        int idx = list.Count - 1;
        T item = list[idx];
        list.RemoveAt(idx);
        return item;
    }

    private static int ToInt(object? v, int fallback)
    {
        if (v is int i) return i;
        if (v is long l) return (int)l;
        if (v is double d) return (int)d;
        if (v is float f) return (int)f;
        if (v is string s && int.TryParse(s, out int r)) return r;
        return fallback;
    }
}
