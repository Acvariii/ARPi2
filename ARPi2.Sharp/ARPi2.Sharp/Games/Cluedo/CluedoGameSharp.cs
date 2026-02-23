using System;
using System.Collections.Generic;
using System.Linq;
using ARPi2.Sharp.Core;

namespace ARPi2.Sharp.Games.Cluedo;

// ════════════════════════════════════════════════════════════════
//  Data types
// ════════════════════════════════════════════════════════════════

public class CluedoCard
{
    public string Kind { get; set; } = ""; // "suspect" | "weapon" | "room"
    public string Name { get; set; } = "";

    public string Key() => $"{Kind}:{Name}";
}

// ════════════════════════════════════════════════════════════════
//  CluedoGameSharp — full port from Python
// ════════════════════════════════════════════════════════════════

public class CluedoGameSharp : BaseGame
{
    public override string ThemeName => "cluedo";

    // ── Static data ────────────────────────────────────────────

    public static readonly (string Emoji, string Name)[] Suspects =
    {
        ("🔴", "Miss Scarlett"),
        ("🟡", "Colonel Mustard"),
        ("⚪", "Mrs. White"),
        ("🟢", "Mr. Green"),
        ("🔵", "Mrs. Peacock"),
        ("🟣", "Professor Plum"),
    };

    public static readonly (string Emoji, string Name)[] Weapons =
    {
        ("🕯️", "Candlestick"),
        ("🗡️", "Dagger"),
        ("🔧", "Wrench"),
        ("🪢", "Rope"),
        ("🔫", "Revolver"),
        ("🧪", "Lead Pipe"),
    };

    public static readonly (string Emoji, string Name)[] Rooms =
    {
        ("🍳", "Kitchen"),
        ("💃", "Ballroom"),
        ("🌿", "Conservatory"),
        ("🍽️", "Dining Room"),
        ("🏛️", "Hall"),
        ("🛋️", "Lounge"),
        ("📚", "Study"),
        ("📖", "Library"),
        ("🎱", "Billiard Room"),
    };

    private static readonly Dictionary<string, (int R, int G, int B)> RoomColors = new()
    {
        ["Kitchen"] = (255, 160, 160),
        ["Ballroom"] = (255, 230, 140),
        ["Conservatory"] = (170, 255, 180),
        ["Dining Room"] = (255, 190, 120),
        ["Hall"] = (180, 220, 255),
        ["Lounge"] = (210, 170, 255),
        ["Study"] = (170, 255, 245),
        ["Library"] = (255, 200, 235),
        ["Billiard Room"] = (210, 255, 170),
        ["Accusation"] = (255, 236, 160),
    };

    private const int BoardSize = 25;
    private const string TileHall = "hall";
    private const string TileRoom = "room";
    private const string TileAccusation = "accusation";
    private const string TileStart = "start";

    // ── Board caches (class-level, built once) ─────────────────

    private static bool _boardBuilt;
    private static string?[][] _gridKind = Array.Empty<string?[]>();
    private static string?[][] _gridLabel = Array.Empty<string?[]>();
    private static Dictionary<string, (int R0, int R1, int C0, int C1)> _roomRects = new();
    private static List<(int R, int C)> _startPositions = new();
    private static Dictionary<(int R, int C), (string Arrow, string RoomName)> _staticDoors = new();
    private static List<(int R0, int R1, int C0, int C1)> _accusationRects = new();
    private static List<(int R, int C)> _outsideStarts = new();
    private static Dictionary<string, (int R, int C)> _roomAnchors = new();
    private static Dictionary<string, Dictionary<string, (int R, int C)>> _staticRoomExits = new();

    // ── Per-game randomized doors/exits ────────────────────────

    private Dictionary<(int R, int C), (string Arrow, string RoomName)> _doors = new();
    private Dictionary<string, Dictionary<string, (int R, int C)>> _roomExits = new();

    // ── Game state ─────────────────────────────────────────────

    private int _currentTurnIdx;
    private readonly List<int> _eliminated = new();
    private int? _winner;

    private readonly Dictionary<int, List<CluedoCard>> _hands = new();
    private string? _solutionSuspect;
    private string? _solutionWeapon;
    private string? _solutionRoom;

    private readonly Dictionary<int, (int R, int C)> _playerPos = new();

    private int? _lastRoll;
    private int _stepsRemaining;
    private (int D1, int D2)? _lastDice;
    private bool _suggestedThisTurn;

    private int? _pendingRevealSuggester;
    private int? _pendingRevealRevealer;
    private List<(string Kind, string Name)> _pendingRevealOptions = new();
    private bool _endTurnAfterSuggestion;

    private bool _diceRolling;
    private double _diceRollStart;
    private double _diceShowUntil;

    private string _mode = "need_roll"; // need_roll | moving | in_room | suggest_pick_suspect | suggest_pick_weapon | accuse_pick_suspect | accuse_pick_weapon | accuse_pick_room | reveal_pick
    private string? _pendingPickSuspect;
    private string? _pendingPickWeapon;

    private string _lastEvent = "";
    private double _lastEventTime;
    private readonly Dictionary<int, string> _lastPrivateEvent = new();
    private readonly Dictionary<int, double> _lastPrivateEventTime = new();

    private (string Suspect, string Weapon, string Room)? _lastSuggestion;
    private readonly HashSet<int> _envelopePeekAllowed = new();

    private int _gameId;

    // ── Buttons ────────────────────────────────────────────────

    private readonly Dictionary<int, Dictionary<string, (string Text, bool Enabled)>> _buttons = new();

    // ── Animations ─────────────────────────────────────────────

    private readonly ParticleSystem _particles = new();
    private readonly List<TextPopAnim> _textPops = new();
    private readonly List<PulseRing> _pulseRings = new();
    private readonly List<ScreenFlash> _flashes = new();
    private readonly AmbientSystem _ambient;
    private readonly LightBeamSystem _lightBeams = LightBeamSystem.ForTheme("cluedo");
    private readonly VignettePulse _vignette = new();
    private readonly Starfield _starfield;
    private readonly FloatingIconSystem _floatingIcons = FloatingIconSystem.ForTheme("cluedo");
    private readonly WaveBand _waveBand = WaveBand.ForTheme("cluedo");
    private readonly HeatShimmer _heatShimmer = HeatShimmer.ForTheme("cluedo");
    private int? _animPrevTurn;
    private int? _animPrevWinner;
    private double _animFwTimer;

    // Track elapsed for dice/show-until since we don't use wall-clock time
    private double _elapsedTime;

    // ════════════════════════════════════════════════════════════
    //  Constructor
    // ════════════════════════════════════════════════════════════

    public CluedoGameSharp(int w, int h, Renderer renderer) : base(w, h, renderer)
    {
        WebUIOnlyPlayerSelect = true;
        BoardOnlyMode = true;
        _ambient = AmbientSystem.ForTheme("cluedo", w, h);
        _starfield = Starfield.ForTheme("cluedo", w, h);
        EnsureBoard();
        _doors = new Dictionary<(int R, int C), (string Arrow, string RoomName)>(_staticDoors);
        _roomExits = DeepCopyExits(_staticRoomExits);
    }

    // ════════════════════════════════════════════════════════════
    //  Board building (class-level, once)
    // ════════════════════════════════════════════════════════════

    private static void EnsureBoard()
    {
        if (_boardBuilt) return;

        var kind = new string?[BoardSize][];
        var label = new string?[BoardSize][];
        for (int r = 0; r < BoardSize; r++)
        {
            kind[r] = new string?[BoardSize];
            label[r] = new string?[BoardSize];
            for (int c = 0; c < BoardSize; c++)
            {
                kind[r][c] = TileHall;
                label[r][c] = "Hallway";
            }
        }

        void FillRect(string tileKind, string tileLabel, int r0, int r1, int c0, int c1)
        {
            int rr0 = Math.Min(r0, r1), rr1 = Math.Max(r0, r1);
            int cc0 = Math.Min(c0, c1), cc1 = Math.Max(c0, c1);
            for (int r = rr0; r <= rr1; r++)
                for (int c = cc0; c <= cc1; c++)
                    if (r >= 0 && r < BoardSize && c >= 0 && c < BoardSize)
                    {
                        kind[r][c] = tileKind;
                        label[r][c] = tileLabel;
                    }
        }

        void FillHall(int r, int c)
        {
            if (r < 0 || r >= BoardSize || c < 0 || c >= BoardSize) return;
            if (kind[r][c] is TileRoom or TileAccusation) return;
            kind[r][c] = TileHall;
            label[r][c] = "Hallway";
        }

        // Room layout
        int leftC0 = 0, leftC1 = 6;
        int midC0 = 9, midC1 = 15;
        int rightC0 = 18, rightC1 = 24;

        var rooms = new Dictionary<string, (int R0, int R1, int C0, int C1)>
        {
            ["Kitchen"] = (0, 6, leftC0, leftC1),
            ["Dining Room"] = (9, 15, leftC0, leftC1),
            ["Lounge"] = (18, 24, leftC0, leftC1),
            ["Ballroom"] = (0, 6, midC0, midC1),
            ["Hall"] = (18, 24, midC0, midC1),
            ["Conservatory"] = (0, 4, rightC0, rightC1),
            ["Billiard Room"] = (7, 11, rightC0, rightC1),
            ["Library"] = (14, 18, rightC0, rightC1),
            ["Study"] = (21, 24, rightC0, rightC1),
        };

        foreach (var (roomName, (r0, r1, c0, c1)) in rooms)
            FillRect(TileRoom, roomName, r0, r1, c0, c1);

        // Accusation room
        var accusationRect = (R0: 10, R1: 14, C0: 10, C1: 14);
        FillRect(TileAccusation, "Accusation", accusationRect.R0, accusationRect.R1, accusationRect.C0, accusationRect.C1);

        // Corridor gaps
        foreach (int r in new[] { 7, 8, 16, 17 })
            for (int c = 0; c < BoardSize; c++)
                FillHall(r, c);
        foreach (int c in new[] { 7, 8, 16, 17 })
            for (int r = 0; r < BoardSize; r++)
                FillHall(r, c);

        // Doors
        var doors = new Dictionary<(int R, int C), (string Arrow, string RoomName)>();

        void AddDoor(int hr, int hc, string arrow, string roomName)
        {
            if (hr < 0 || hr >= BoardSize || hc < 0 || hc >= BoardSize) return;
            FillHall(hr, hc);
            doors[(hr, hc)] = (arrow, roomName);
        }

        AddDoor(7, 3, "↑", "Kitchen");
        AddDoor(16, 3, "↑", "Dining Room");
        AddDoor(17, 3, "↓", "Lounge");
        AddDoor(7, 12, "↑", "Ballroom");
        AddDoor(3, 16, "←", "Ballroom");
        AddDoor(2, 17, "→", "Conservatory");
        AddDoor(9, 17, "→", "Billiard Room");
        AddDoor(16, 17, "→", "Library");
        AddDoor(20, 21, "↓", "Study");
        AddDoor(17, 12, "↓", "Hall");

        // Start squares (outside the 25x25 grid)
        var starts = new (int R, int C)[]
        {
            (-1, 7), (-1, 16),
            (BoardSize, 7), (BoardSize, 16),
            (7, -1), (16, -1),
            (6, BoardSize), (13, BoardSize),
        };

        var outsideStarts = new List<(int, int)>();
        foreach (var (sr, sc) in starts)
        {
            outsideStarts.Add((sr, sc));
            if (sr == -1 && sc >= 0 && sc < BoardSize) FillHall(0, sc);
            else if (sr == BoardSize && sc >= 0 && sc < BoardSize) FillHall(BoardSize - 1, sc);
            else if (sc == -1 && sr >= 0 && sr < BoardSize) FillHall(sr, 0);
            else if (sc == BoardSize && sr >= 0 && sr < BoardSize) FillHall(sr, BoardSize - 1);
        }

        // Room anchors + exits
        var anchors = new Dictionary<string, (int R, int C)>();
        foreach (var (roomName, (r0, r1, c0, c1)) in rooms)
            anchors[roomName] = ((r0 + r1) / 2, (c0 + c1) / 2);

        var arrowToDir = new Dictionary<string, string> { ["↑"] = "up", ["↓"] = "down", ["←"] = "left", ["→"] = "right" };
        var opposite = new Dictionary<string, string> { ["up"] = "down", ["down"] = "up", ["left"] = "right", ["right"] = "left" };

        var exits = new Dictionary<string, Dictionary<string, (int R, int C)>>();
        foreach (var ((hr, hc), (arrow, roomName)) in doors)
        {
            if (!arrowToDir.TryGetValue(arrow, out var entryDir)) continue;
            if (!opposite.TryGetValue(entryDir, out var exitDir)) continue;
            if (!exits.ContainsKey(roomName)) exits[roomName] = new();
            exits[roomName][exitDir] = (hr, hc);
        }

        _gridKind = kind;
        _gridLabel = label;
        _roomRects = rooms;
        _staticDoors = doors;
        _startPositions = new List<(int, int)>(outsideStarts);
        _accusationRects = new List<(int, int, int, int)> { (accusationRect.R0, accusationRect.R1, accusationRect.C0, accusationRect.C1) };
        _outsideStarts = outsideStarts;
        _roomAnchors = anchors;
        _staticRoomExits = exits;
        _boardBuilt = true;
    }

    // ════════════════════════════════════════════════════════════
    //  Helpers
    // ════════════════════════════════════════════════════════════

    private static Dictionary<string, Dictionary<string, (int R, int C)>> DeepCopyExits(
        Dictionary<string, Dictionary<string, (int R, int C)>> src)
    {
        var copy = new Dictionary<string, Dictionary<string, (int R, int C)>>();
        foreach (var (k, v) in src)
            copy[k] = new Dictionary<string, (int R, int C)>(v);
        return copy;
    }

    private static void ShuffleList<T>(Random rng, List<T> list)
    {
        for (int i = list.Count - 1; i > 0; i--)
        {
            int j = rng.Next(i + 1);
            (list[i], list[j]) = (list[j], list[i]);
        }
    }

    private void SetEvent(string msg)
    {
        _lastEvent = msg ?? "";
        _lastEventTime = _elapsedTime;
    }

    private void SetPrivateEvent(int seat, string msg)
    {
        _lastPrivateEvent[seat] = msg ?? "";
        _lastPrivateEventTime[seat] = _elapsedTime;
    }

    private int? CurrentTurnSeat
    {
        get
        {
            if (ActivePlayers.Count == 0) return null;
            if (_currentTurnIdx < 0 || _currentTurnIdx >= ActivePlayers.Count)
                _currentTurnIdx = 0;
            return ActivePlayers[_currentTurnIdx];
        }
    }

    private void AdvanceTurn()
    {
        if (ActivePlayers.Count == 0) return;
        if (_winner != null) return;

        int start = _currentTurnIdx;
        for (int step = 1; step <= ActivePlayers.Count; step++)
        {
            int idx = (start + step) % ActivePlayers.Count;
            int seat = ActivePlayers[idx];
            if (!_eliminated.Contains(seat))
            {
                _currentTurnIdx = idx;
                _lastRoll = null;
                _stepsRemaining = 0;
                _lastDice = null;
                _suggestedThisTurn = false;
                _pendingRevealSuggester = null;
                _pendingRevealRevealer = null;
                _pendingRevealOptions.Clear();
                _endTurnAfterSuggestion = false;
                _mode = "need_roll";
                _pendingPickSuspect = null;
                _pendingPickWeapon = null;
                return;
            }
        }
    }

    private (string? Kind, string? Label) TileInfo((int R, int C)? pos)
    {
        if (pos == null) return (null, null);
        int r = pos.Value.R, c = pos.Value.C;
        if (_outsideStarts.Contains((r, c))) return (TileStart, "Start");
        if (r < 0 || c < 0 || r >= BoardSize || c >= BoardSize) return (null, null);
        return (_gridKind[r][c], _gridLabel[r][c]);
    }

    private static bool ArrowMatchesDelta(string arrow, (int DR, int DC) delta)
    {
        return arrow switch
        {
            "↑" => delta.DR == -1 && delta.DC == 0,
            "↓" => delta.DR == 1 && delta.DC == 0,
            "←" => delta.DR == 0 && delta.DC == -1,
            "→" => delta.DR == 0 && delta.DC == 1,
            _ => false,
        };
    }

    private static (int DR, int DC) OppositeDelta((int DR, int DC) d) => (-d.DR, -d.DC);

    private bool CanMove((int R, int C) pos, (int DR, int DC) delta)
    {
        int r = pos.R, c = pos.C;
        int dr = delta.DR, dc = delta.DC;
        var nxt = (R: r + dr, C: c + dc);

        if (_outsideStarts.Contains(nxt)) return false;

        // From outside start
        if (_outsideStarts.Contains((r, c)))
        {
            if (nxt.R < 0 || nxt.R >= BoardSize || nxt.C < 0 || nxt.C >= BoardSize) return false;
            var (k, _) = TileInfo(nxt);
            return k is TileHall or TileStart;
        }

        var (kindNext, labelNext) = TileInfo(nxt);
        if (kindNext == null) return false;

        var (kindCur, labelCur) = TileInfo((r, c));

        // Accusation: can enter from corridor, cannot leave
        if (kindCur == TileAccusation) return false;
        if (kindNext == TileAccusation)
            return (kindCur is TileHall or TileStart) && Math.Abs(dr) + Math.Abs(dc) == 1;

        // Room: uses exits
        if (kindCur == TileRoom && labelCur != null)
        {
            string? exitDir = (dr, dc) switch
            {
                (-1, 0) => "up",
                (1, 0) => "down",
                (0, -1) => "left",
                (0, 1) => "right",
                _ => null,
            };
            if (exitDir == null) return false;
            return _roomExits.TryGetValue(labelCur, out var re) && re.ContainsKey(exitDir);
        }

        bool curIsHall = kindCur is TileHall or TileStart;
        bool nxtIsHall = kindNext is TileHall or TileStart;
        bool nxtIsRoomish = kindNext is TileRoom or TileAccusation;
        bool curIsRoomish = kindCur is TileRoom or TileAccusation;

        // Hall -> Room: need a door at current pos pointing into room
        if (curIsHall && nxtIsRoomish)
        {
            if (!_doors.TryGetValue((r, c), out var door)) return false;
            if (door.RoomName != labelNext) return false;
            return ArrowMatchesDelta(door.Arrow, (dr, dc));
        }

        // Room -> Hall: need a door at nxt pos pointing into current room
        if (curIsRoomish && nxtIsHall)
        {
            if (!_doors.TryGetValue(nxt, out var door)) return false;
            if (door.RoomName != labelCur) return false;
            return ArrowMatchesDelta(door.Arrow, OppositeDelta((dr, dc)));
        }

        // Hall -> Hall
        if (curIsHall && nxtIsHall) return true;

        return false;
    }

    private void MovePos(int seat, string direction)
    {
        if (!_playerPos.TryGetValue(seat, out var current)) return;

        var (curKind, curLabel) = TileInfo(current);
        var delta = direction switch
        {
            "up" => (DR: -1, DC: 0),
            "down" => (DR: 1, DC: 0),
            "left" => (DR: 0, DC: -1),
            "right" => (DR: 0, DC: 1),
            _ => (DR: 0, DC: 0),
        };

        if (!CanMove(current, delta)) return;

        // Room: teleport to exit door
        if (curKind == TileRoom && curLabel != null)
        {
            if (_roomExits.TryGetValue(curLabel, out var re) && re.TryGetValue(direction, out var doorPos))
                _playerPos[seat] = doorPos;
            return;
        }

        var nxt = (R: current.R + delta.DR, C: current.C + delta.DC);
        var (nxtKind, nxtLabel) = TileInfo(nxt);

        // Hall -> Room: snap to anchor
        if ((curKind is TileHall or TileStart) && nxtKind == TileRoom && nxtLabel != null)
        {
            if (_roomAnchors.TryGetValue(nxtLabel, out var anchor))
            {
                _playerPos[seat] = anchor;
                return;
            }
        }

        _playerPos[seat] = nxt;
    }

    // ════════════════════════════════════════════════════════════
    //  Start game
    // ════════════════════════════════════════════════════════════

    public override void StartGame(List<int> players)
    {
        EnsureBoard();
        var seats = players.Where(s => s >= 0 && s <= 5).Distinct().OrderBy(x => x).ToList();
        if (seats.Count < 3) return;

        _gameId++;
        ActivePlayers = seats;
        _currentTurnIdx = Rng.Next(seats.Count);
        _eliminated.Clear();
        _winner = null;

        // Choose solution
        _solutionSuspect = Suspects[Rng.Next(Suspects.Length)].Name;
        _solutionWeapon = Weapons[Rng.Next(Weapons.Length)].Name;
        _solutionRoom = Rooms[Rng.Next(Rooms.Length)].Name;

        // Build + deal deck
        var deck = new List<CluedoCard>();
        foreach (var (_, n) in Suspects)
            if (n != _solutionSuspect) deck.Add(new CluedoCard { Kind = "suspect", Name = n });
        foreach (var (_, n) in Weapons)
            if (n != _solutionWeapon) deck.Add(new CluedoCard { Kind = "weapon", Name = n });
        foreach (var (_, n) in Rooms)
            if (n != _solutionRoom) deck.Add(new CluedoCard { Kind = "room", Name = n });

        ShuffleList(Rng, deck);
        _hands.Clear();
        foreach (var s in seats) _hands[s] = new List<CluedoCard>();
        for (int i = 0; i < deck.Count; i++)
            _hands[seats[i % seats.Count]].Add(deck[i]);

        // Start positions
        var starts = new List<(int R, int C)>(_startPositions);
        ShuffleList(Rng, starts);
        _playerPos.Clear();
        for (int i = 0; i < seats.Count; i++)
            _playerPos[seats[i]] = starts[i % starts.Count];

        // Reset turn state
        _lastRoll = null;
        _stepsRemaining = 0;
        _lastDice = null;
        _suggestedThisTurn = false;
        _pendingRevealSuggester = null;
        _pendingRevealRevealer = null;
        _pendingRevealOptions.Clear();
        _endTurnAfterSuggestion = false;
        _diceRolling = false;
        _diceRollStart = 0;
        _diceShowUntil = 0;
        _mode = "need_roll";
        _pendingPickSuspect = null;
        _pendingPickWeapon = null;
        _envelopePeekAllowed.Clear();
        _lastSuggestion = null;

        State = "playing";
        SetEvent("Cluedo started. Find the culprit!");

        RandomizeDoors();
        RebuildButtonsAll();
    }

    // ── Handle player quit ─────────────────────────────────────

    public void HandlePlayerQuit(int seat)
    {
        if (State != "playing") return;
        if (_winner != null) return;
        if (!ActivePlayers.Contains(seat)) return;

        bool wasTurn = CurrentTurnSeat == seat;

        if (_mode == "reveal_pick")
        {
            if (_pendingRevealRevealer == seat || _pendingRevealSuggester == seat)
            {
                _pendingRevealSuggester = null;
                _pendingRevealRevealer = null;
                _pendingRevealOptions.Clear();
                _endTurnAfterSuggestion = false;
                _mode = "in_room";
            }
        }

        // Redistribute cards
        var quitterHand = new List<CluedoCard>(_hands.GetValueOrDefault(seat) ?? new());
        _hands.Remove(seat);
        var remaining = ActivePlayers.Where(x => x != seat).ToList();
        if (remaining.Count > 0 && quitterHand.Count > 0)
        {
            ShuffleList(Rng, quitterHand);
            for (int i = 0; i < quitterHand.Count; i++)
            {
                int tgt = remaining[i % remaining.Count];
                if (!_hands.ContainsKey(tgt)) _hands[tgt] = new();
                _hands[tgt].Add(quitterHand[i]);
            }
        }

        ActivePlayers = remaining;
        _playerPos.Remove(seat);
        if (!_eliminated.Contains(seat)) _eliminated.Add(seat);

        if (ActivePlayers.Count == 0)
        {
            State = "player_select";
            SetEvent("All players left");
            RebuildButtonsAll();
            return;
        }

        // Last non-eliminated wins
        var remainingLive = ActivePlayers.Where(x => !_eliminated.Contains(x)).ToList();
        if (remainingLive.Count == 1)
        {
            _winner = remainingLive[0];
            SetEvent($"{PlayerName(_winner.Value)} wins! (Last remaining)");
            RebuildButtonsAll();
            return;
        }

        if (_currentTurnIdx >= ActivePlayers.Count)
            _currentTurnIdx = 0;

        if (wasTurn) AdvanceTurn();

        SetEvent($"{PlayerName(seat)} quit");
        RebuildButtonsAll();
    }

    // ── Door randomization ─────────────────────────────────────

    private void RandomizeDoors()
    {
        if (_roomRects.Count == 0) return;

        var allowed = new Dictionary<string, string[]>
        {
            ["Kitchen"] = new[] { "bottom" },
            ["Dining Room"] = new[] { "bottom" },
            ["Lounge"] = new[] { "top" },
            ["Hall"] = new[] { "top" },
            ["Ballroom"] = new[] { "bottom", "right" },
            ["Conservatory"] = new[] { "left" },
            ["Billiard Room"] = new[] { "left" },
            ["Library"] = new[] { "left" },
            ["Study"] = new[] { "top" },
        };

        var used = new HashSet<(int, int)>();
        var doors = new Dictionary<(int R, int C), (string Arrow, string RoomName)>();

        bool IsCorridor((int R, int C) rc)
        {
            var (k, _) = TileInfo(rc);
            return k is TileHall or TileStart;
        }

        List<(int R, int C, string Arrow)> CandidatesFor(string roomName, string side)
        {
            if (!_roomRects.TryGetValue(roomName, out var rect)) return new();
            var (r0, r1, c0, c1) = rect;
            var result = new List<(int, int, string)>();

            switch (side)
            {
                case "bottom":
                    for (int cc = c0; cc <= c1; cc++) result.Add((r1 + 1, cc, "↑"));
                    break;
                case "top":
                    for (int cc = c0; cc <= c1; cc++) result.Add((r0 - 1, cc, "↓"));
                    break;
                case "left":
                    for (int rr = r0; rr <= r1; rr++) result.Add((rr, c0 - 1, "→"));
                    break;
                case "right":
                    for (int rr = r0; rr <= r1; rr++) result.Add((rr, c1 + 1, "←"));
                    break;
            }

            return result.Where(t => t.Item1 >= 0 && t.Item1 < BoardSize
                                  && t.Item2 >= 0 && t.Item2 < BoardSize
                                  && IsCorridor((t.Item1, t.Item2))).ToList();
        }

        foreach (var (roomName, sides) in allowed)
        {
            if (!_roomRects.ContainsKey(roomName)) continue;
            foreach (var side in sides)
            {
                var cand = CandidatesFor(roomName, side).Where(t => !used.Contains((t.R, t.C))).ToList();
                if (cand.Count == 0)
                    cand = CandidatesFor(roomName, side);
                if (cand.Count == 0) continue;
                var pick = cand[Rng.Next(cand.Count)];
                used.Add((pick.R, pick.C));
                doors[(pick.R, pick.C)] = (pick.Arrow, roomName);
            }
        }

        // Build exits
        var arrowToDir = new Dictionary<string, string> { ["↑"] = "up", ["↓"] = "down", ["←"] = "left", ["→"] = "right" };
        var opposite = new Dictionary<string, string> { ["up"] = "down", ["down"] = "up", ["left"] = "right", ["right"] = "left" };
        var exits = new Dictionary<string, Dictionary<string, (int R, int C)>>();
        foreach (var ((hr, hc), (arrow, roomName)) in doors)
        {
            if (!arrowToDir.TryGetValue(arrow, out var entryDir)) continue;
            if (!opposite.TryGetValue(entryDir, out var exitDir)) continue;
            if (!exits.ContainsKey(roomName)) exits[roomName] = new();
            exits[roomName][exitDir] = (hr, hc);
        }

        _doors = doors;
        _roomExits = exits;
    }

    // ════════════════════════════════════════════════════════════
    //  Buttons
    // ════════════════════════════════════════════════════════════

    private void RebuildButtonsAll()
    {
        _buttons.Clear();
        for (int seat = 0; seat < 8; seat++)
            _buttons[seat] = BuildButtonsForPlayer(seat);
    }

    private Dictionary<string, (string Text, bool Enabled)> BuildButtonsForPlayer(int seat)
    {
        var btns = new Dictionary<string, (string, bool)>();
        if (State != "playing") return btns;

        // Reveal pick mode: only the revealer gets buttons
        if (_mode == "reveal_pick")
        {
            if (_pendingRevealRevealer == null || _pendingRevealSuggester == null) return btns;
            if (seat != _pendingRevealRevealer) return btns;

            foreach (var (kind, name) in _pendingRevealOptions)
            {
                var kid = $"reveal:{kind}:{name}";
                btns[kid] = ($"Reveal {Capitalize(kind)} — {name}", true);
            }
            return btns;
        }

        var turnSeat = CurrentTurnSeat;
        bool isTurn = turnSeat != null && seat == turnSeat && !_eliminated.Contains(seat);

        btns["roll"] = ("Roll", isTurn && _lastRoll == null && !_diceRolling);
        if (_envelopePeekAllowed.Contains(seat))
            btns["envelope"] = ("Envelope", !_diceRolling);
        btns["end_turn"] = ("End Turn", isTurn && _lastRoll != null);

        // Movement
        var curPos = isTurn && turnSeat.HasValue ? _playerPos.GetValueOrDefault(turnSeat.Value) : default;
        bool hasCurPos = isTurn && turnSeat.HasValue && _playerPos.ContainsKey(turnSeat.Value);
        bool moveEnabled = isTurn && _stepsRemaining > 0 && hasCurPos;

        btns["move:up"] = ("↑", moveEnabled && CanMove(curPos, (-1, 0)));
        btns["move:down"] = ("↓", moveEnabled && CanMove(curPos, (1, 0)));
        btns["move:left"] = ("←", moveEnabled && CanMove(curPos, (0, -1)));
        btns["move:right"] = ("→", moveEnabled && CanMove(curPos, (0, 1)));

        var (tileKind, tileLabel) = hasCurPos ? TileInfo(curPos) : (null, null);
        bool inSuggestRoom = tileKind == TileRoom && tileLabel != null && tileLabel != "Accusation";
        bool suggestEnabled = isTurn && !_diceRolling && !_suggestedThisTurn && _stepsRemaining == 0 && inSuggestRoom;
        bool inAccuseRoom = tileKind == TileAccusation;
        bool accuseEnabled = isTurn && !_diceRolling && _winner == null && inAccuseRoom;

        btns["suggest"] = ("Suggest", suggestEnabled);
        btns["accuse"] = ("Accuse", accuseEnabled);

        // Selection modes
        if (isTurn && _mode is "suggest_pick_suspect" or "accuse_pick_suspect")
            foreach (var (emoji, name) in Suspects)
                btns[$"pick_suspect:{name}"] = ($"{emoji} {name}", true);

        if (isTurn && _mode is "suggest_pick_weapon" or "accuse_pick_weapon")
            foreach (var (emoji, name) in Weapons)
                btns[$"pick_weapon:{name}"] = ($"{emoji} {name}", true);

        if (isTurn && _mode == "accuse_pick_room")
            foreach (var (emoji, name) in Rooms)
                btns[$"pick_room:{name}"] = ($"{emoji} {name}", true);

        return btns;
    }

    private static string Capitalize(string s) =>
        string.IsNullOrEmpty(s) ? s : char.ToUpper(s[0]) + s[1..];

    // ════════════════════════════════════════════════════════════
    //  HandleClick (web UI)
    // ════════════════════════════════════════════════════════════

    public override void HandleClick(int playerIdx, string buttonId)
    {
        // Game-specific messages from server passthrough
        if (buttonId.StartsWith("__msg__:"))
        {
            // No custom messages yet for Cluedo, but parse for future use
            return;
        }

        if (State != "playing") return;

        int seat = playerIdx;

        // Envelope peek
        if (buttonId == "envelope")
        {
            if (!_envelopePeekAllowed.Contains(seat)) return;
            if (_solutionSuspect != null && _solutionWeapon != null && _solutionRoom != null)
                SetPrivateEvent(seat, $"Case File: {_solutionSuspect} · {_solutionWeapon} · {_solutionRoom}");
            else
                SetPrivateEvent(seat, "Case File is empty? (not initialized)");
            RebuildButtonsAll();
            return;
        }

        if (_winner != null) return;

        // Reveal pick mode
        if (_mode == "reveal_pick")
        {
            if (_pendingRevealRevealer == null || _pendingRevealSuggester == null)
            {
                _pendingRevealSuggester = null;
                _pendingRevealRevealer = null;
                _pendingRevealOptions.Clear();
                _mode = "in_room";
                RebuildButtonsAll();
                return;
            }
            if (seat != _pendingRevealRevealer) return;
            if (!buttonId.StartsWith("reveal:")) return;

            var parts = buttonId.Split(':', 3);
            if (parts.Length < 3) return;
            string kind = parts[1], name = parts[2];

            if (!_pendingRevealOptions.Any(o => o.Kind == kind && o.Name == name)) return;

            int suggester = _pendingRevealSuggester.Value;
            int revealer = _pendingRevealRevealer.Value;

            SetPrivateEvent(suggester, $"Revealed by {PlayerName(revealer)}: {Capitalize(kind)} — {name}");
            SetPrivateEvent(revealer, $"You revealed: {Capitalize(kind)} — {name}");

            _pendingRevealSuggester = null;
            _pendingRevealRevealer = null;
            _pendingRevealOptions.Clear();
            _mode = "in_room";

            if (_endTurnAfterSuggestion)
            {
                _endTurnAfterSuggestion = false;
                AdvanceTurn();
            }

            RebuildButtonsAll();
            return;
        }

        var turnSeat = CurrentTurnSeat;
        if (turnSeat == null || seat != turnSeat) return;
        if (_eliminated.Contains(seat)) return;

        if (buttonId == "roll")
        {
            if (_lastRoll != null || _diceRolling) return;
            _diceRolling = true;
            _diceRollStart = _elapsedTime;
            SetEvent($"{PlayerName(seat)} is rolling…");
            RebuildButtonsAll();
            return;
        }

        if (buttonId.StartsWith("move:"))
        {
            if (_stepsRemaining <= 0) return;
            string direction = buttonId.Split(':', 2)[1];
            var (beforeKind, beforeLabel) = TileInfo(_playerPos.GetValueOrDefault(seat));
            MovePos(seat, direction);
            var (afterKind, afterLabel) = TileInfo(_playerPos.GetValueOrDefault(seat));

            _stepsRemaining = Math.Max(0, _stepsRemaining - 1);

            if ((afterKind is TileRoom or TileAccusation) && (afterKind != beforeKind || afterLabel != beforeLabel))
                _stepsRemaining = 0;

            if (_stepsRemaining == 0)
                _mode = "in_room";
            RebuildButtonsAll();
            return;
        }

        if (buttonId == "suggest")
        {
            if (_stepsRemaining != 0) return;
            if (_suggestedThisTurn) return;
            var (kind, label) = TileInfo(_playerPos.GetValueOrDefault(seat));
            if (!(kind == TileRoom && label != null && label != "Accusation")) return;
            _mode = "suggest_pick_suspect";
            _pendingPickSuspect = null;
            _pendingPickWeapon = null;
            RebuildButtonsAll();
            return;
        }

        if (buttonId == "accuse")
        {
            var (kind, _) = TileInfo(_playerPos.GetValueOrDefault(seat));
            if (kind != TileAccusation) return;
            _mode = "accuse_pick_suspect";
            _pendingPickSuspect = null;
            _pendingPickWeapon = null;
            RebuildButtonsAll();
            return;
        }

        if (buttonId.StartsWith("pick_suspect:"))
        {
            string name = buttonId.Split(':', 2)[1];
            _pendingPickSuspect = name;
            if (_mode == "suggest_pick_suspect") _mode = "suggest_pick_weapon";
            else if (_mode == "accuse_pick_suspect") _mode = "accuse_pick_weapon";
            RebuildButtonsAll();
            return;
        }

        if (buttonId.StartsWith("pick_weapon:"))
        {
            string weapon = buttonId.Split(':', 2)[1];
            string? suspect = _pendingPickSuspect;
            if (suspect == null) return;
            _pendingPickWeapon = weapon;

            var pos = _playerPos.GetValueOrDefault(seat);
            var (tk, tl) = TileInfo(pos);
            string? room = tk == TileRoom && tl != null ? tl : null;

            if (_mode == "suggest_pick_weapon")
            {
                if (room == null) return;
                _suggestedThisTurn = true;
                _endTurnAfterSuggestion = _lastRoll == null;

                ResolveSuggestion(seat, suspect, weapon, room);
                if (_mode != "reveal_pick") _mode = "in_room";
                _pendingPickSuspect = null;
                _pendingPickWeapon = null;

                if (_endTurnAfterSuggestion && _mode != "reveal_pick")
                {
                    _endTurnAfterSuggestion = false;
                    AdvanceTurn();
                }
                RebuildButtonsAll();
                return;
            }

            if (_mode == "accuse_pick_weapon")
            {
                _mode = "accuse_pick_room";
                RebuildButtonsAll();
                return;
            }
        }

        if (buttonId.StartsWith("pick_room:"))
        {
            string roomPick = buttonId.Split(':', 2)[1];
            if (_pendingPickSuspect == null || _pendingPickWeapon == null) return;
            if (_mode != "accuse_pick_room") return;
            ResolveAccusation(seat, _pendingPickSuspect, _pendingPickWeapon, roomPick);
            _mode = "in_room";
            _pendingPickSuspect = null;
            _pendingPickWeapon = null;
            RebuildButtonsAll();
            return;
        }

        if (buttonId == "end_turn")
        {
            if (_lastRoll == null) return;
            AdvanceTurn();
            RebuildButtonsAll();
            return;
        }
    }

    // ── Suggestion / Accusation ────────────────────────────────

    private void ResolveSuggestion(int seat, string suspect, string weapon, string room)
    {
        string msg = $"{PlayerName(seat)} suggests {suspect} with the {weapon} in the {room}.";
        SetEvent(msg);

        // Animation
        int cx = ScreenW / 2, cy = ScreenH / 2;
        _flashes.Add(new ScreenFlash((60, 100, 200), 40, 0.4f));
        _textPops.Add(new TextPopAnim("🔍 Suggestion!", cx, cy - 50, (120, 170, 255), 26));
        _particles.EmitSparkle(cx, cy, (120, 170, 255), 14);

        _lastSuggestion = (suspect, weapon, room);

        int? revealer = null;
        var matchesForRevealer = new List<CluedoCard>();
        var ap = new List<int>(ActivePlayers);
        int start = ap.Contains(seat) ? ap.IndexOf(seat) : 0;

        var wanted = new HashSet<string> { $"suspect:{suspect}", $"weapon:{weapon}", $"room:{room}" };
        for (int step = 1; step <= ap.Count; step++)
        {
            int other = ap[(start + step) % ap.Count];
            if (other == seat) continue;
            var cards = _hands.GetValueOrDefault(other) ?? new();
            var matches = cards.Where(c => wanted.Contains(c.Key())).ToList();
            if (matches.Count > 0)
            {
                revealer = other;
                matchesForRevealer = matches;
                break;
            }
        }

        if (revealer == null || matchesForRevealer.Count == 0)
        {
            SetPrivateEvent(seat, "No one could reveal a matching card.");
            return;
        }

        _pendingRevealSuggester = seat;
        _pendingRevealRevealer = revealer.Value;
        _pendingRevealOptions = matchesForRevealer.Select(c => (c.Kind, c.Name)).ToList();
        _mode = "reveal_pick";

        SetPrivateEvent(seat, $"Waiting for {PlayerName(revealer.Value)} to reveal a card…");
        SetPrivateEvent(revealer.Value, $"Choose a card to reveal to {PlayerName(seat)}.");
    }

    private void ResolveAccusation(int seat, string suspect, string weapon, string room)
    {
        string msg = $"{PlayerName(seat)} accuses {suspect} with the {weapon} in the {room}.";
        SetEvent(msg);

        bool correct = suspect == _solutionSuspect && weapon == _solutionWeapon && room == _solutionRoom;

        int cx = ScreenW / 2, cy = ScreenH / 2;

        if (correct)
        {
            _winner = seat;
            _flashes.Add(new ScreenFlash((220, 200, 60), 60, 0.6f));
            _textPops.Add(new TextPopAnim($"🔍 SOLVED! {PlayerName(seat)}", cx, cy - 60, (255, 220, 50), 34));
            for (int i = 0; i < 6; i++)
                _particles.EmitFirework(
                    cx + Rng.Next(-120, 121), cy + Rng.Next(-80, 81),
                    new[] { (255, 220, 50), (80, 220, 120), (100, 180, 255) });
            SetEvent($"{PlayerName(seat)} wins! Case File: {_solutionSuspect} · {_solutionWeapon} · {_solutionRoom}");
            _envelopePeekAllowed.Add(seat);
            return;
        }

        // Wrong accusation
        _flashes.Add(new ScreenFlash((180, 40, 40), 50, 0.45f));
        _textPops.Add(new TextPopAnim($"❌ WRONG! {PlayerName(seat)}", cx, cy - 40, (255, 80, 80), 30));
        _particles.EmitSparkle(cx, cy, (255, 60, 60), 20);

        if (!_eliminated.Contains(seat)) _eliminated.Add(seat);
        _envelopePeekAllowed.Add(seat);
        SetPrivateEvent(seat, "Wrong accusation — you are eliminated. You may now check the Envelope.");

        var remaining = ActivePlayers.Where(s => !_eliminated.Contains(s)).ToList();
        if (remaining.Count == 1)
        {
            _winner = remaining[0];
            SetEvent($"{PlayerName(_winner.Value)} wins! (Last remaining)");
            return;
        }

        AdvanceTurn();
    }

    // ════════════════════════════════════════════════════════════
    //  Snapshot (web UI state)
    // ════════════════════════════════════════════════════════════

    public override Dictionary<string, object?> GetSnapshot(int playerIdx)
    {
        int seat = playerIdx;
        double now = _elapsedTime;

        // Private hand
        var yourHand = new List<Dictionary<string, object?>>();
        foreach (var c in _hands.GetValueOrDefault(seat) ?? new())
        {
            string emoji = "";
            if (c.Kind == "suspect") emoji = Suspects.FirstOrDefault(x => x.Name == c.Name).Emoji ?? "";
            else if (c.Kind == "weapon") emoji = Weapons.FirstOrDefault(x => x.Name == c.Name).Emoji ?? "";
            else if (c.Kind == "room") emoji = Rooms.FirstOrDefault(x => x.Name == c.Name).Emoji ?? "";
            yourHand.Add(new Dictionary<string, object?>
            {
                ["kind"] = c.Kind,
                ["name"] = c.Name,
                ["emoji"] = emoji,
                ["text"] = $"{emoji} {c.Name}".Trim(),
            });
        }

        // Hand counts
        var handCounts = new Dictionary<string, object?>();
        foreach (var s in ActivePlayers)
            handCounts[s.ToString()] = (_hands.GetValueOrDefault(s)?.Count ?? 0);

        // Players info
        var players = new List<Dictionary<string, object?>>();
        foreach (var s in ActivePlayers)
        {
            var (kind, label) = TileInfo(_playerPos.GetValueOrDefault(s));
            string loc = kind switch
            {
                TileRoom when label != null => label,
                TileStart => "Start",
                TileAccusation => "Accusation",
                _ => "Hallway",
            };
            players.Add(new Dictionary<string, object?>
            {
                ["seat"] = s,
                ["name"] = PlayerName(s),
                ["eliminated"] = _eliminated.Contains(s),
                ["room"] = loc,
                ["hand_count"] = _hands.GetValueOrDefault(s)?.Count ?? 0,
            });
        }

        double lastEventAge = !string.IsNullOrEmpty(_lastEvent) ? (now - _lastEventTime) * 1000 : 0;
        string priv = _lastPrivateEvent.GetValueOrDefault(seat, "");
        double privAge = !string.IsNullOrEmpty(priv) ? (now - _lastPrivateEventTime.GetValueOrDefault(seat, now)) * 1000 : 0;

        Dictionary<string, object?>? solutionRevealed = null;
        if (_winner != null && _solutionSuspect != null && _solutionWeapon != null && _solutionRoom != null)
        {
            solutionRevealed = new Dictionary<string, object?>
            {
                ["suspect"] = _solutionSuspect,
                ["weapon"] = _solutionWeapon,
                ["room"] = _solutionRoom,
            };
        }

        var snap = new Dictionary<string, object?>
        {
            ["game_id"] = _gameId,
            ["state"] = State,
            ["active_players"] = new List<int>(ActivePlayers),
            ["current_turn_seat"] = CurrentTurnSeat,
            ["dice"] = _lastDice.HasValue ? new List<int> { _lastDice.Value.D1, _lastDice.Value.D2 } : null,
            ["last_roll"] = _lastRoll,
            ["steps_remaining"] = _stepsRemaining,
            ["mode"] = _mode,
            ["winner"] = _winner,
            ["hand_counts"] = handCounts,
            ["players"] = players,
            ["your_hand"] = yourHand,
            ["last_event"] = string.IsNullOrEmpty(_lastEvent) ? null : _lastEvent,
            ["last_event_age_ms"] = (int)lastEventAge,
            ["private_event"] = string.IsNullOrEmpty(priv) ? null : priv,
            ["private_event_age_ms"] = (int)privAge,
            ["solution_revealed"] = solutionRevealed,
        };

        return new Dictionary<string, object?> { ["cluedo"] = snap };
    }

    public override Dictionary<string, object?> GetPopupSnapshot(int playerIdx) => new() { ["active"] = false };

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

    // ════════════════════════════════════════════════════════════
    //  Update
    // ════════════════════════════════════════════════════════════

    public override void Update(double dt)
    {
        _elapsedTime += dt;

        if (State != "playing") return;

        // Tick animations
        _particles.Update((float)dt);
        for (int i = _textPops.Count - 1; i >= 0; i--)
        {
            _textPops[i].Update((float)dt);
            if (_textPops[i].Done) _textPops.RemoveAt(i);
        }
        for (int i = _pulseRings.Count - 1; i >= 0; i--)
        {
            _pulseRings[i].Update((float)dt);
            if (_pulseRings[i].Done) _pulseRings.RemoveAt(i);
        }
        for (int i = _flashes.Count - 1; i >= 0; i--)
        {
            _flashes[i].Update((float)dt);
            if (_flashes[i].Done) _flashes.RemoveAt(i);
        }
        _ambient.Update((float)dt, ScreenW, ScreenH);
        _lightBeams.Update((float)dt, ScreenW, ScreenH);
        _vignette.Update((float)dt);
        _starfield.Update((float)dt);
        _floatingIcons.Update((float)dt, ScreenW, ScreenH);
        _waveBand.Update((float)dt);
        _heatShimmer.Update((float)dt);

        // Turn-change pulse
        var currTurn = CurrentTurnSeat;
        if (State == "playing" && currTurn != null && _animPrevTurn != null && currTurn != _animPrevTurn)
        {
            int cx = ScreenW / 2, cy = ScreenH / 2;
            var col = GameConfig.PlayerColors[currTurn.Value % GameConfig.PlayerColors.Length];
            _pulseRings.Add(new PulseRing(cx, cy, col, Math.Min(ScreenW, ScreenH) / 5, 0.8f));
            _particles.EmitSparkle(cx, cy, col, 18);
            _flashes.Add(new ScreenFlash(col, 40, 0.3f));
        }
        _animPrevTurn = currTurn;

        // Winner fireworks
        if (_winner != null && _winner != _animPrevWinner)
        {
            _animPrevWinner = _winner;
            int cx = ScreenW / 2, cy = ScreenH / 2;
            for (int i = 0; i < 8; i++)
                _particles.EmitFirework(
                    cx + Rng.Next(-120, 121), cy + Rng.Next(-80, 81),
                    GameConfig.PlayerColors.Select(c => (c.R, c.G, c.B)).ToArray());
            _flashes.Add(new ScreenFlash((255, 220, 80), 70, 1.0f));
            _textPops.Add(new TextPopAnim($"🏆 {PlayerName(_winner.Value)} wins!",
                cx, cy - 60, (255, 220, 80), 36));
            _animFwTimer = 6.0;
        }
        if (_animFwTimer > 0)
        {
            _animFwTimer = Math.Max(0, _animFwTimer - dt);
            if ((int)(_animFwTimer * 3) % 2 == 0)
            {
                int cx = ScreenW / 2, cy = ScreenH / 2;
                _particles.EmitFirework(
                    cx + Rng.Next(-150, 151), cy + Rng.Next(-100, 101),
                    GameConfig.PlayerColors.Select(c => (c.R, c.G, c.B)).ToArray());
            }
        }

        // Dice animation resolution
        if (_diceRolling)
        {
            double elapsed = _elapsedTime - _diceRollStart;
            if (elapsed >= 1.2)
            {
                _diceRolling = false;
                var turnSeat = CurrentTurnSeat;
                if (turnSeat != null && !_eliminated.Contains(turnSeat.Value) && _winner == null)
                {
                    int d1 = Rng.Next(1, 7), d2 = Rng.Next(1, 7);
                    _lastDice = (d1, d2);
                    _lastRoll = d1 + d2;
                    _stepsRemaining = _lastRoll.Value;
                    _mode = _stepsRemaining > 0 ? "moving" : "in_room";
                    SetEvent($"{PlayerName(turnSeat.Value)} rolled {d1}+{d2} = {_lastRoll}.");
                    _diceShowUntil = _elapsedTime + 2.2;

                    int cx = ScreenW / 2, cy = (int)(ScreenH * 0.35);
                    _textPops.Add(new TextPopAnim($"🎲 {d1} + {d2} = {_lastRoll}", cx, cy, (255, 235, 120), 34));
                    _particles.EmitSparkle(cx, cy, (255, 235, 120));
                }
                RebuildButtonsAll();
            }
        }

        // Keep buttons in sync
        RebuildButtonsAll();
    }

    // ════════════════════════════════════════════════════════════
    //  Draw
    // ════════════════════════════════════════════════════════════

    private (int D1, int D2) DicePreviewValues()
    {
        double elapsed = Math.Max(0, _elapsedTime - _diceRollStart);
        int d1 = (int)(elapsed * 20 % 6) + 1;
        int d2 = (int)((elapsed * 17 + 2.5) % 6) + 1;
        return (d1, d2);
    }

    public override void Draw(Renderer r, int width, int height, double dt)
    {
        if (State == "player_select")
        {
            // Show a simple waiting screen instead of seat selection UI
            // MaybeAutoStartActiveGame in GameServer will auto-start with 3+ seated players
            CardRendering.DrawGameBackground(r, width, height, "cluedo");
            RainbowTitle.Draw(r, "CLUEDO", width, y: (int)(height * 0.04), fontSize: 28, charWidth: 22);
            r.DrawText("Waiting for players... (3 required)", width / 2, height / 2, 20,
                (200, 200, 200), anchorX: "center", anchorY: "center");
            return;
        }

        // Background
        CardRendering.DrawGameBackground(r, width, height, "cluedo");
        _ambient.Draw(r);
        _lightBeams.Draw(r, width, height);
        _starfield.Draw(r);
        _floatingIcons.Draw(r);

        // Title
        RainbowTitle.Draw(r, "CLUEDO", width, y: (int)(height * 0.04), fontSize: 28, charWidth: 22);

        // Board area
        int margin = (int)(Math.Min(width, height) * 0.02);
        int boardW = width - 2 * margin;
        int headerPad = (int)(height * 0.06);
        int footerPad = (int)(height * 0.12);
        int boardY = margin + headerPad;
        int boardH = height - boardY - footerPad - margin;
        if (boardH < 3 * 140) boardH = Math.Max(3 * 120, boardH);

        int cell = Math.Min(boardW, boardH) / BoardSize;
        if (cell <= 0) return;
        int boardPx = cell * BoardSize;
        int boardX = margin + (boardW - boardPx) / 2;
        int boardY2 = boardY + (boardH - boardPx) / 2;
        int cellW = cell, cellH = cell;

        int tokenR = Math.Max(4, (int)(cell * 0.28));
        int tokenStep = Math.Max(10, (int)(tokenR * 2.2));

        (int X, int Y, int W, int H) CellRect(int cr, int cc, int inset = 2)
        {
            int x = boardX + cc * cellW;
            int y = boardY2 + cr * cellH;
            return (x + inset, y + inset, cellW - 2 * inset, cellH - 2 * inset);
        }

        // Draw corridor grid
        for (int cr = 0; cr < BoardSize; cr++)
            for (int cc = 0; cc < BoardSize; cc++)
            {
                var (k, _) = TileInfo((cr, cc));
                if (k == null) continue;
                if (k is not (TileHall or TileStart)) continue;
                var rect = CellRect(cr, cc, 2);
                r.DrawRect((0, 0, 0), (rect.X + 1, rect.Y + 1, rect.W, rect.H), alpha: 40);
                r.DrawRect((50, 50, 58), (rect.X, rect.Y, rect.W, rect.H), alpha: 185);
                r.DrawRect((80, 80, 90), (rect.X, rect.Y + rect.H - 2, rect.W, 2), alpha: 40);
                r.DrawRect((0, 0, 0), (rect.X, rect.Y, rect.W, rect.H), width: 1, alpha: 50);
            }

        // Draw rooms
        foreach (var (roomName, (r0, r1, c0, c1)) in _roomRects)
        {
            (int R, int G, int B) col = RoomColors.GetValueOrDefault(roomName, (200, 200, 200));
            int rx = boardX + c0 * cellW;
            int ry = boardY2 + r0 * cellH;
            int rw = (c1 - c0 + 1) * cellW;
            int rh = (r1 - r0 + 1) * cellH;
            var rect = (rx + 2, ry + 2, rw - 4, rh - 4);
            r.DrawRect((0, 0, 0), (rect.Item1 + 3, rect.Item2 + 3, rect.Item3, rect.Item4), alpha: 60);
            r.DrawRect(col, rect, alpha: 230);
            (int R, int G, int B) hl = (Math.Min(255, col.R + 40), Math.Min(255, col.G + 40), Math.Min(255, col.B + 40));
            r.DrawRect(hl, (rect.Item1 + 2, rect.Item2 + rect.Item4 - 4, rect.Item3 - 4, 3), alpha: 60);
            r.DrawRect((20, 20, 20), rect, width: 2, alpha: 140);
        }

        // Accusation block
        foreach (var (ar0, ar1, ac0, ac1) in _accusationRects)
        {
            (int R, int G, int B) col = RoomColors.GetValueOrDefault("Accusation", (255, 236, 160));
            int rx = boardX + ac0 * cellW;
            int ry = boardY2 + ar0 * cellH;
            int rw = (ac1 - ac0 + 1) * cellW;
            int rh = (ar1 - ar0 + 1) * cellH;
            var rect = (rx + 2, ry + 2, rw - 4, rh - 4);
            r.DrawRect(col, rect, alpha: 240);
            r.DrawRect((0, 0, 0), rect, width: 2, alpha: 140);
        }

        // Room labels
        foreach (var (roomName, (r0, r1, c0, c1)) in _roomRects)
        {
            int cx = boardX + ((c0 + c1 + 1) * cellW) / 2;
            int cy = boardY2 + ((r0 + r1 + 1) * cellH) / 2;
            string emoji = Rooms.FirstOrDefault(x => x.Name == roomName).Emoji ?? "";
            if (!string.IsNullOrEmpty(emoji))
                r.DrawText(emoji, cx, cy - (int)(cellH * 1.0),
                    Math.Max(18, (int)(cell * 1.2)), (255, 255, 255), anchorX: "center", anchorY: "center");
            r.DrawText(roomName, cx, cy + (int)(cellH * 0.6),
                Math.Max(12, (int)(cell * 0.55)), (20, 20, 20), anchorX: "center", anchorY: "center", bold: true);
        }

        // Accusation label
        foreach (var (ar0, ar1, ac0, ac1) in _accusationRects)
        {
            int cx = boardX + ((ac0 + ac1 + 1) * cellW) / 2;
            int cy = boardY2 + ((ar0 + ar1 + 1) * cellH) / 2;
            r.DrawText("⚖️", cx, cy - (int)(cellH * 0.6),
                Math.Max(18, (int)(cell * 1.2)), (255, 255, 255), anchorX: "center", anchorY: "center");
            r.DrawText("Accusation", cx, cy + (int)(cellH * 0.6),
                Math.Max(12, (int)(cell * 0.50)), (20, 20, 20), anchorX: "center", anchorY: "center", bold: true);
        }

        // Door arrows
        foreach (var ((dr, dc), (arrow, _)) in _doors)
        {
            var rect = CellRect(dr, dc, 2);
            int cx = rect.X + rect.W / 2;
            int cy = rect.Y + rect.H / 2;
            r.DrawText(arrow, cx, cy, Math.Max(12, (int)(cell * 0.70)),
                GameConfig.Colors.Accent, anchorX: "center", anchorY: "center", bold: true);
        }

        // Outside start pads
        foreach (var (sr, sc) in _outsideStarts)
        {
            int x0 = boardX + sc * cellW;
            int y0 = boardY2 + sr * cellH;
            var pad = (x0 + 6, y0 + 6, cellW - 12, cellH - 12);
            if (pad.Item1 + pad.Item3 < -20 || pad.Item2 + pad.Item4 < -20 || pad.Item1 > width + 20 || pad.Item2 > height + 20)
                continue;
            r.DrawRect((45, 45, 55), pad, alpha: 180);
            r.DrawRect(GameConfig.Colors.Accent, pad, width: 3, alpha: 150);
            r.DrawText("START", pad.Item1 + pad.Item3 / 2, pad.Item2 + pad.Item4 / 2,
                Math.Max(10, (int)(cell * 0.45)), (240, 240, 240), anchorX: "center", anchorY: "center", bold: true);
        }

        // Player tokens
        var byPos = new Dictionary<(int, int), List<int>>();
        foreach (var s in ActivePlayers)
        {
            if (!_playerPos.TryGetValue(s, out var pos)) continue;
            var key = (pos.R, pos.C);
            if (!byPos.ContainsKey(key)) byPos[key] = new();
            byPos[key].Add(s);
        }

        foreach (var (pos, seats) in byPos)
        {
            int pr = pos.Item1, pc = pos.Item2;
            int x0 = boardX + pc * cellW;
            int y0 = boardY2 + pr * cellH;

            if (pr == -1) y0 = boardY2 - cellH;
            else if (pr == BoardSize) y0 = boardY2 + BoardSize * cellH;
            if (pc == -1) x0 = boardX - cellW;
            else if (pc == BoardSize) x0 = boardX + BoardSize * cellW;

            var sorted = seats.OrderBy(x => x).ToList();
            for (int j = 0; j < sorted.Count; j++)
            {
                int seat = sorted[j];
                int cx = x0 + Math.Max(tokenR + 4, (int)(cellW * 0.30));
                int cy = y0 + Math.Max(tokenR + 6, (int)(cellH * 0.34)) + j * tokenStep;
                if (cy > y0 + cellH - (tokenR + 6))
                    cy = y0 + cellH - (tokenR + 6);

                var color = GameConfig.PlayerColors[seat % GameConfig.PlayerColors.Length];
                int alpha = _eliminated.Contains(seat) ? 90 : 255;

                r.DrawCircle((0, 0, 0), (cx + 2, cy + 2), (int)(tokenR * 1.2), alpha: Math.Max(40, alpha - 120));
                r.DrawCircle(color, (cx, cy), tokenR, alpha: alpha);
                var hlc = (Math.Min(255, color.R + 80), Math.Min(255, color.G + 80), Math.Min(255, color.B + 80));
                r.DrawCircle(hlc, (cx - 2, cy - 2), Math.Max(2, (int)(tokenR * 0.3)), alpha: Math.Min(alpha, 90));
                r.DrawCircle((0, 0, 0), (cx, cy), tokenR, width: 1, alpha: Math.Max(60, alpha - 60));

                if (CurrentTurnSeat == seat && _winner == null)
                {
                    r.DrawCircle(GameConfig.Colors.Gold, (cx, cy), (int)(tokenR * 1.8), alpha: 50);
                    r.DrawCircle(GameConfig.Colors.Gold, (cx, cy), (int)(tokenR * 1.8), width: 2, alpha: 80);
                }
            }
        }

        // Footer panel
        int footerY = height - footerPad + 8;
        var fpRect = (margin, footerY, width - 2 * margin, footerPad - 16);
        r.DrawRect((0, 0, 0), (fpRect.Item1 + 3, fpRect.Item2 + 3, fpRect.Item3, fpRect.Item4), alpha: 70);
        r.DrawRect((12, 12, 18), fpRect, alpha: 190);
        r.DrawRect((30, 20, 40), (fpRect.Item1 + 3, fpRect.Item2 + 3, fpRect.Item3 - 6, fpRect.Item4 - 6), alpha: 40);
        r.DrawRect((180, 150, 80), fpRect, width: 2, alpha: 120);

        // Dice in footer
        bool showDice = _diceRolling || (_lastRoll != null && _elapsedTime < _diceShowUntil);
        if (showDice && _winner == null)
        {
            int d1, d2;
            if (_diceRolling)
                (d1, d2) = DicePreviewValues();
            else if (_lastDice.HasValue)
                (d1, d2) = (_lastDice.Value.D1, _lastDice.Value.D2);
            else
                (d1, d2) = (_lastRoll ?? 0, 0);

            int dieS = 38, dieGap = 10;
            int diceCx = margin + 18 + dieS;
            int diceCy = footerY + (footerPad - 16) * 44 / 100;

            double dGlow = 0;
            if (!_diceRolling && _lastDice.HasValue)
            {
                double dSince = _elapsedTime - (_diceRollStart + 1.2);
                if (dSince >= 0 && dSince < 0.55) dGlow = 1.0 - dSince / 0.55;
            }

            for (int di = 0; di < 2; di++)
            {
                int dv = di == 0 ? d1 : d2;
                int djx = 0, djy = 0, db = 0;
                if (_diceRolling)
                {
                    double dph = _elapsedTime * 34 + di * 2.3;
                    djx = (int)(4 * Math.Sin(dph));
                    djy = (int)(3 * Math.Cos(dph * 1.35 + 0.8));
                }
                if (dGlow > 0.25)
                    db = (int)(6 * Math.Sin(Math.PI * (dGlow - 0.25) / 0.75));

                int ddx = (int)(diceCx + (di - 0.5) * (dieS + dieGap)) + djx;
                int ddy = diceCy + djy - db;
                int dhx = ddx - dieS / 2;
                int dhy = ddy - dieS / 2;

                r.DrawRect((0, 0, 0), (dhx + 4, dhy + 4, dieS, dieS), alpha: 50);
                r.DrawRect((0, 0, 0), (dhx + 2, dhy + 2, dieS, dieS), alpha: 70);
                r.DrawRect((250, 250, 255), (dhx, dhy, dieS, dieS), alpha: 255);
                r.DrawRect((255, 255, 255), (dhx + 2, dhy + 2, dieS - 4, 5), alpha: 130);
                r.DrawRect((40, 40, 48), (dhx, dhy, dieS, dieS), width: 2, alpha: 230);
                r.DrawRect((180, 180, 195), (dhx + 3, dhy + 3, dieS - 6, dieS - 6), width: 1, alpha: 50);

                if (dGlow > 0)
                    r.DrawRect((255, 215, 0), (dhx - 3, dhy - 3, dieS + 6, dieS + 6), width: 2, alpha: (int)(80 * dGlow));

                // Pips
                int pipR = Math.Max(2, dieS / 10);
                int pipOff = dieS / 4;
                var pipMap = new Dictionary<int, (int, int)[]>
                {
                    [1] = new[] { (0, 0) },
                    [2] = new[] { (-pipOff, -pipOff), (pipOff, pipOff) },
                    [3] = new[] { (-pipOff, -pipOff), (0, 0), (pipOff, pipOff) },
                    [4] = new[] { (-pipOff, -pipOff), (pipOff, -pipOff), (-pipOff, pipOff), (pipOff, pipOff) },
                    [5] = new[] { (-pipOff, -pipOff), (pipOff, -pipOff), (0, 0), (-pipOff, pipOff), (pipOff, pipOff) },
                    [6] = new[] { (-pipOff, -pipOff), (pipOff, -pipOff), (-pipOff, 0), (pipOff, 0), (-pipOff, pipOff), (pipOff, pipOff) },
                };

                if (pipMap.TryGetValue(dv, out var pips))
                    foreach (var (pdx, pdy) in pips)
                    {
                        int ppx = ddx + pdx, ppy = ddy + pdy;
                        r.DrawCircle((0, 0, 0), (ppx + 1, ppy + 1), pipR, alpha: 45);
                        r.DrawCircle((15, 15, 22), (ppx, ppy), pipR, alpha: 245);
                    }
            }
        }

        // Footer info text
        var turnSeatDraw = CurrentTurnSeat;
        string tname = turnSeatDraw != null ? PlayerName(turnSeatDraw.Value) : "—";
        string info = $"Turn: {tname}";
        if (_diceRolling)
            info += "  ·  Rolling…";
        else if (_lastRoll != null)
        {
            if (_lastDice.HasValue)
                info += $"  ·  Roll: {_lastDice.Value.D1}+{_lastDice.Value.D2}={_lastRoll}  ·  Steps: {_stepsRemaining}";
            else
                info += $"  ·  Roll: {_lastRoll}  ·  Steps: {_stepsRemaining}";
        }
        if (_winner != null)
            info = $"🏆 Winner: {PlayerName(_winner.Value)} 🏆";

        var infoColor = _winner != null ? (255, 230, 140) : (235, 235, 235);
        r.DrawText(info, width / 2, footerY + (footerPad - 16) * 38 / 100,
            18, infoColor, anchorX: "center", anchorY: "center", bold: true);

        // Last event
        if (!string.IsNullOrEmpty(_lastEvent))
            r.DrawText(_lastEvent, width / 2, footerY + (footerPad - 16) * 72 / 100,
                14, (200, 200, 200), anchorX: "center", anchorY: "center");

        // Animations
        _particles.Draw(r);
        foreach (var pr in _pulseRings) pr.Draw(r);
        foreach (var fl in _flashes) fl.Draw(r, width, height);
        foreach (var tp in _textPops) tp.Draw(r);
        _waveBand.Draw(r, width, height);
        _heatShimmer.Draw(r, width, height);
        _vignette.Draw(r, width, height);
    }
}
