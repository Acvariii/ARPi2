using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using ARPi2.Sharp.Core;
using ARPi2.Sharp.Games.Blackjack; // for ListShuffleExt

namespace ARPi2.Sharp.Games.UnstableUnicorns;

// ════════════════════════════════════════════════════════════════
//  Data types
// ════════════════════════════════════════════════════════════════

/// <summary>Immutable card definition loaded from JSON.</summary>
public class UUCardDef
{
    public string Id { get; }
    public string Name { get; }
    /// <summary>baby_unicorn|unicorn|upgrade|downgrade|magic|instant|neigh|super_neigh</summary>
    public string Kind { get; }
    public string Emoji { get; }
    public string Color { get; }
    public int Count { get; }
    public string Desc { get; }
    public Dictionary<string, JsonElement> Effect { get; }

    public UUCardDef(string id, string name, string kind, string emoji, string color, int count,
                     Dictionary<string, JsonElement> effect, string desc = "")
    {
        Id = id; Name = name; Kind = kind; Emoji = emoji; Color = color; Count = count;
        Effect = effect; Desc = desc;
    }

    public string EffectType => Effect.TryGetValue("type", out var v) ? v.GetString() ?? "NONE" : "NONE";

    public int EffectInt(string key, int fallback = 0)
    {
        if (!Effect.TryGetValue(key, out var v)) return fallback;
        if (v.ValueKind == JsonValueKind.Number && v.TryGetInt32(out int n)) return n;
        return fallback;
    }
}

// ════════════════════════════════════════════════════════════════
//  UnstableUnicornsGame — full port from Python
// ════════════════════════════════════════════════════════════════
public class UnstableUnicornsGameSharp : BaseGame
{
    public override string ThemeName => "unstable_unicorns";

    // Card registry / piles
    private Dictionary<string, UUCardDef> _cards = new();
    private List<string> _drawPile = new();
    private List<string> _discardPile = new();

    // Per-player zones
    private readonly Dictionary<int, List<string>> _hands = new();
    private readonly Dictionary<int, List<string>> _stables = new();
    private readonly Dictionary<int, int> _protectedTurns = new();

    // Turn / phase
    private int _currentPlayerIdx;
    private string _turnPhase = "begin"; // begin|action|discard|reaction|prompt
    private bool _actionTaken;
    private int _forcedDiscardCount; // e.g. Good Deal forces discarding 1 card of choice

    // Reaction window (Neigh stack) — simultaneous: all non-actor players choose at once
    private bool _reactionActive;
    private int? _reactionActor;
    private string? _reactionCardId;
    private Dictionary<string, object?>? _reactionTarget;
    private HashSet<int> _reactionPending = new();   // seats that haven't responded yet
    private List<string> _reactionStack = new();

    // Prompting (target selection etc.)
    private Dictionary<string, object?>? _prompt;

    // Win
    private int? _winner;
    private int _goalUnicorns = 7;

    // Unicorn Lasso tracking
    private string? _lassoStolenCard;
    private int _lassoStolenFrom = -1;

    // Buttons per player
    private readonly Dictionary<int, Dictionary<string, (string Text, bool Enabled)>> _buttons = new();

    // Animations
    private readonly ParticleSystem _particles = new();
    private readonly List<CardFlyAnim> _cardFlips = new();
    private readonly List<CardShowcaseAnim> _showcases = new();
    private readonly List<TextPopAnim> _textPops = new();
    private readonly List<PulseRing> _pulseRings = new();
    private readonly List<ScreenFlash> _flashes = new();
    private AmbientSystem _ambient;
    private readonly LightBeamSystem _lightBeams = LightBeamSystem.ForTheme("unstable_unicorns");
    private readonly VignettePulse _vignette = new();
    private Starfield _starfield;
    private readonly FloatingIconSystem _floatingIcons = FloatingIconSystem.ForTheme("unstable_unicorns");
    private readonly WaveBand _waveBand = WaveBand.ForTheme("unstable_unicorns");
    private readonly HeatShimmer _heatShimmer = HeatShimmer.ForTheme("unstable_unicorns");
    private readonly Dictionary<int, (int X, int Y)> _zoneCenters = new();
    private int? _animPrevTurn;
    private bool _animPrevReaction;
    private int? _animPrevWinner;
    private double _animFwTimer;

    // Premium visual systems (EK-quality)
    private readonly SpotlightCone _spotlight = new();
    private readonly FireEdge _fireEdge = new();
    private readonly CardBreathEffect _cardBreath = new();
    private readonly List<ExplosionBurst> _explosions = new();
    private float _screenShakeX, _screenShakeY;
    private float _screenShakeTimer;
    private float _sparkleTimer;
    private string _lastEvent = "";
    private double _lastEventAge = 999.0;

    private static readonly (int R, int G, int B)[] SeatColors =
    {
        (255, 80,  80),
        (80,  180, 255),
        (80,  255, 130),
        (255, 200, 50),
        (200, 80,  255),
        (255, 140, 50),
    };

    public UnstableUnicornsGameSharp(int w, int h, Renderer renderer) : base(w, h, renderer)
    {
        _ambient = AmbientSystem.ForTheme("unstable_unicorns", w, h);
        _starfield = Starfield.ForTheme("unstable_unicorns", w, h);
        LoadCardSets(includeExpansions: true);
        RebuildButtons();
    }

    // ─── Helpers ───────────────────────────────────────────────

    private int? CurrentTurnSeat
    {
        get
        {
            if (ActivePlayers.Count == 0) return null;
            int idx = ((_currentPlayerIdx % ActivePlayers.Count) + ActivePlayers.Count) % ActivePlayers.Count;
            return ActivePlayers[idx];
        }
    }

    private static (int R, int G, int B) HexToRgb(string? hex, (int, int, int)? def = null)
    {
        var d = def ?? (160, 160, 160);
        var h = (hex ?? "").Trim().TrimStart('#');
        if (h.Length != 6) return d;
        try
        {
            int r = Convert.ToInt32(h[0..2], 16);
            int g = Convert.ToInt32(h[2..4], 16);
            int b = Convert.ToInt32(h[4..6], 16);
            return (r, g, b);
        }
        catch { return d; }
    }

    // ─── Card set loading ──────────────────────────────────────

    private static string CardsDir()
    {
        // Look for cards dir relative to the executable, then fall back to known project locations.
        var candidates = new List<string>();

        // Relative to current directory
        var cur = Path.GetFullPath("games/unstable_unicorns/cards");
        candidates.Add(cur);

        // Relative to assembly
        var asmDir = Path.GetDirectoryName(typeof(UnstableUnicornsGameSharp).Assembly.Location) ?? ".";
        candidates.Add(Path.Combine(asmDir, "games", "unstable_unicorns", "cards"));

        // Walk up from assembly dir looking for the cards directory
        var dir = asmDir;
        for (int i = 0; i < 8; i++)
        {
            var test = Path.Combine(dir, "games", "unstable_unicorns", "cards");
            candidates.Add(test);
            var parent = Directory.GetParent(dir);
            if (parent == null) break;
            dir = parent.FullName;
        }

        foreach (var c in candidates)
            if (Directory.Exists(c)) return c;

        return cur; // fallback
    }

    private void LoadCardSets(bool includeExpansions)
    {
        _cards = new Dictionary<string, UUCardDef>();
        var baseDir = CardsDir();
        var files = new List<string>();

        try
        {
            if (Directory.Exists(baseDir))
            {
                foreach (var fp in Directory.GetFiles(baseDir, "*.json").OrderBy(f => f))
                {
                    if (!includeExpansions && !fp.EndsWith("base.json", StringComparison.OrdinalIgnoreCase))
                        continue;
                    files.Add(fp);
                }
            }
        }
        catch { /* ignore */ }

        foreach (var fp in files)
        {
            try
            {
                var text = File.ReadAllText(fp);
                using var doc = JsonDocument.Parse(text);
                if (!doc.RootElement.TryGetProperty("cards", out var cardsArr))
                    continue;

                foreach (var raw in cardsArr.EnumerateArray())
                {
                    try
                    {
                        string cid = raw.TryGetProperty("id", out var idEl) ? (idEl.GetString() ?? "").Trim() : "";
                        if (string.IsNullOrEmpty(cid)) continue;
                        if (_cards.ContainsKey(cid)) continue;

                        string name = raw.TryGetProperty("name", out var nEl) ? nEl.GetString() ?? cid : cid;
                        string kind = raw.TryGetProperty("kind", out var kEl) ? (kEl.GetString() ?? "").Trim() : "";
                        string emoji = raw.TryGetProperty("emoji", out var eEl) ? eEl.GetString() ?? "" : "";
                        string color = raw.TryGetProperty("color", out var cEl) ? cEl.GetString() ?? "#a0a0a0" : "#a0a0a0";
                        int count = raw.TryGetProperty("count", out var cnEl) && cnEl.TryGetInt32(out int cn) ? cn : 0;

                        var effect = new Dictionary<string, JsonElement>();
                        if (raw.TryGetProperty("effect", out var effEl) && effEl.ValueKind == JsonValueKind.Object)
                        {
                            foreach (var prop in effEl.EnumerateObject())
                                effect[prop.Name] = prop.Value.Clone();
                        }
                        else
                        {
                            // Parse a dummy NONE effect
                            using var noneDoc = JsonDocument.Parse("{\"type\":\"NONE\"}");
                            foreach (var prop in noneDoc.RootElement.EnumerateObject())
                                effect[prop.Name] = prop.Value.Clone();
                        }
                        string desc = raw.TryGetProperty("desc", out var dEl) ? dEl.GetString() ?? "" : "";

                        _cards[cid] = new UUCardDef(cid, name, kind, emoji, color, count, effect, desc);
                    }
                    catch { /* skip bad card */ }
                }
            }
            catch { /* skip bad file */ }
        }

        // Safety: ensure baby_unicorn exists
        if (!_cards.ContainsKey("baby_unicorn"))
        {
            using var noneDoc = JsonDocument.Parse("{\"type\":\"NONE\"}");
            var eff = new Dictionary<string, JsonElement>();
            foreach (var p in noneDoc.RootElement.EnumerateObject())
                eff[p.Name] = p.Value.Clone();

            _cards["baby_unicorn"] = new UUCardDef(
                "baby_unicorn", "Baby Unicorn", "baby_unicorn", "\ud83e\udd84", "#f3a6ff", 0, eff);
        }
    }

    private List<string> BuildDeck()
    {
        var deck = new List<string>();
        foreach (var (cid, c) in _cards)
        {
            if (cid == "baby_unicorn") continue;
            int n = Math.Max(0, c.Count);
            for (int i = 0; i < n; i++)
                deck.Add(cid);
        }
        ShuffleList(deck);
        return deck;
    }

    // ─── Lifecycle ─────────────────────────────────────────────

    public override void StartGame(List<int> players)
    {
        var seats = players.Where(s => s >= 0 && s <= 7).Distinct().OrderBy(x => x).ToList();
        if (seats.Count < 2) return;

        ActivePlayers = seats;
        _currentPlayerIdx = 0;
        _drawPile = BuildDeck();
        _discardPile = new List<string>();
        _hands.Clear();
        _stables.Clear();
        _protectedTurns.Clear();

        foreach (var s in seats)
        {
            _hands[s] = new List<string>();
            _stables[s] = new List<string> { "baby_unicorn" };
            _protectedTurns[s] = 0;
        }

        // Deal 5
        for (int round = 0; round < 5; round++)
            foreach (var s in seats)
                DrawToHand(s, 1);

        State = "playing";
        _winner = null;
        _turnPhase = "begin";
        _actionTaken = false;
        _prompt = null;
        ClearReaction();
        BeginTurn();
        RebuildButtons();
    }

    public void HandlePlayerQuit(int seat)
    {
        if (!ActivePlayers.Contains(seat)) return;
        ActivePlayers = ActivePlayers.Where(p => p != seat).ToList();
        _hands.Remove(seat);
        _stables.Remove(seat);
        _protectedTurns.Remove(seat);

        if (ActivePlayers.Count < 2)
        {
            State = "player_select";
            SelectionUI.Reset();
        }
        else
        {
            if (_currentPlayerIdx >= ActivePlayers.Count)
                _currentPlayerIdx = 0;
        }
        RebuildButtons();
    }

    // ─── Core rules ────────────────────────────────────────────

    private int HandLimit(int seat)
    {
        int baseLimit = 7;
        int mod = 0;
        foreach (var cid in _stables.GetValueOrDefault(seat, new List<string>()))
        {
            var c = _cards.GetValueOrDefault(cid);
            if (c == null) continue;
            if (c.EffectType == "PASSIVE_HAND_LIMIT_MOD")
                mod += c.EffectInt("amount");
        }
        return Math.Max(0, baseLimit + mod);
    }

    private int DrawBonus(int seat)
    {
        int bonus = 0;
        foreach (var cid in _stables.GetValueOrDefault(seat, new List<string>()))
        {
            var c = _cards.GetValueOrDefault(cid);
            if (c == null) continue;
            if (c.EffectType == "PASSIVE_DRAW_BONUS")
                bonus += c.EffectInt("amount");
        }
        return bonus;
    }

    private void BeginTurn()
    {
        if (State != "playing") return;
        var seat = CurrentTurnSeat;
        if (seat is not int s) return;

        // Decrement protection counters
        foreach (var key in _protectedTurns.Keys.ToList())
            _protectedTurns[key] = Math.Max(0, _protectedTurns.GetValueOrDefault(key, 0) - 1);

        _turnPhase = "begin";
        _actionTaken = false;
        _forcedDiscardCount = 0;

        // ─── Beginning-of-turn stable effects ──────────────
        ProcessBeginningOfTurnEffects(s);

        int drawN = 1 + Math.Max(0, DrawBonus(s));
        DrawToHand(s, drawN);
        _turnPhase = (_hands.GetValueOrDefault(s)?.Count ?? 0) > HandLimit(s) ? "discard" : "action";
    }

    /// <summary>Process all beginning-of-turn card effects for the active player.</summary>
    private void ProcessBeginningOfTurnEffects(int seat)
    {
        var stable = _stables.GetValueOrDefault(seat);
        if (stable == null) return;
        bool blinded = HasBlindingLight(seat);

        // Iterate a copy since effects may modify stable
        var stableSnapshot = stable.ToList();
        foreach (var cid in stableSnapshot)
        {
            // Skip if the card was removed from stable by a previous effect this turn
            if (!stable.Contains(cid)) continue;
            var c = _cards.GetValueOrDefault(cid);
            if (c == null) continue;
            var typ = c.EffectType;

            // Blinding Light suppresses unicorn effects
            if (blinded && c.Kind is "unicorn" or "baby_unicorn") continue;

            // ── Sadistic Ritual (forced): sacrifice a unicorn, draw 1 ──
            if (typ == "PASSIVE_SADISTIC")
            {
                var unicornIdxs = new List<int>();
                for (int i = 0; i < stable.Count; i++)
                {
                    var ck = _cards.GetValueOrDefault(stable[i])?.Kind ?? "";
                    if (ck is "baby_unicorn" or "unicorn") unicornIdxs.Add(i);
                }
                if (unicornIdxs.Count > 0)
                {
                    int ri = unicornIdxs[Rng.Next(unicornIdxs.Count)];
                    TrySacrificeStableCard(seat, ri);
                    DrawToHand(seat, 1);
                }
            }

            // ── Extremely Fertile Unicorn: discard a card → get baby unicorn ──
            if (typ == "PASSIVE_FERTILE")
            {
                var hand = _hands.GetValueOrDefault(seat);
                if (hand != null && hand.Count > 0)
                {
                    int ri = Rng.Next(hand.Count);
                    _discardPile.Add(hand[ri]);
                    hand.RemoveAt(ri);
                    AddToStable(seat, "baby_unicorn");
                }
            }

            // ── Zombie Unicorn: discard a unicorn-kind card → rescue unicorn from discard ──
            if (typ == "PASSIVE_ZOMBIE")
            {
                var hand = _hands.GetValueOrDefault(seat);
                if (hand != null)
                {
                    var handUnicornIdxs = new List<int>();
                    for (int i = 0; i < hand.Count; i++)
                    {
                        var ck = _cards.GetValueOrDefault(hand[i])?.Kind ?? "";
                        if (ck is "baby_unicorn" or "unicorn") handUnicornIdxs.Add(i);
                    }
                    if (handUnicornIdxs.Count > 0)
                    {
                        int ri = handUnicornIdxs[Rng.Next(handUnicornIdxs.Count)];
                        _discardPile.Add(hand[ri]);
                        hand.RemoveAt(ri);
                        // Rescue a random unicorn from discard
                        var discUnicornIdxs = new List<int>();
                        for (int i = 0; i < _discardPile.Count; i++)
                        {
                            var ck = _cards.GetValueOrDefault(_discardPile[i])?.Kind ?? "";
                            if (ck is "baby_unicorn" or "unicorn") discUnicornIdxs.Add(i);
                        }
                        if (discUnicornIdxs.Count > 0)
                        {
                            int di = discUnicornIdxs[Rng.Next(discUnicornIdxs.Count)];
                            var rescued = _discardPile[di];
                            _discardPile.RemoveAt(di);
                            AddToStable(seat, rescued);
                        }
                    }
                }
            }

            // ── Rhinocorn: destroy random unicorn from any opponent → each other player discards ──
            if (typ == "PASSIVE_RHINOCORN")
            {
                // Pick a random opponent with unicorns
                var opponents = ActivePlayers.Where(p => p != seat).ToList();
                var withUnicorns = opponents.Where(p =>
                {
                    var st = _stables.GetValueOrDefault(p, new List<string>());
                    return st.Any(ci => (_cards.GetValueOrDefault(ci)?.Kind ?? "") is "baby_unicorn" or "unicorn");
                }).ToList();
                if (withUnicorns.Count > 0)
                {
                    int t = withUnicorns[Rng.Next(withUnicorns.Count)];
                    var tStable = _stables[t];
                    var uIdxs = new List<int>();
                    for (int i = 0; i < tStable.Count; i++)
                    {
                        var ck = _cards.GetValueOrDefault(tStable[i])?.Kind ?? "";
                        if (ck is "baby_unicorn" or "unicorn") uIdxs.Add(i);
                    }
                    if (uIdxs.Count > 0)
                    {
                        int ui = uIdxs[Rng.Next(uIdxs.Count)];
                        TryDestroyStableCard(t, ui);
                        // Each other player discards 1
                        foreach (var op in ActivePlayers)
                        {
                            if (op == seat) continue;
                            var h = _hands.GetValueOrDefault(op);
                            if (h != null && h.Count > 0)
                            {
                                int hi = Rng.Next(h.Count);
                                _discardPile.Add(h[hi]);
                                h.RemoveAt(hi);
                            }
                        }
                        try { EmitDestroyFx(t); } catch { }
                    }
                }
            }

            // ── Glitter Bomb: sacrifice a card from your stable → destroy a card in another stable ──
            if (typ == "PASSIVE_GLITTER_BOMB")
            {
                if (stable.Count > 1) // need at least 1 card + the glitter bomb itself
                {
                    // Sacrifice a random card (but not the Glitter Bomb itself)
                    var sacrificeIdxs = new List<int>();
                    for (int i = 0; i < stable.Count; i++)
                    {
                        if (stable[i] != cid) sacrificeIdxs.Add(i);
                    }
                    if (sacrificeIdxs.Count > 0)
                    {
                        int si = sacrificeIdxs[Rng.Next(sacrificeIdxs.Count)];
                        TrySacrificeStableCard(seat, si);

                        // Destroy a random card from a random opponent's stable
                        var opponents = ActivePlayers.Where(p => p != seat).ToList();
                        var withCards = opponents.Where(p => (_stables.GetValueOrDefault(p)?.Count ?? 0) > 0).ToList();
                        if (withCards.Count > 0)
                        {
                            int t = withCards[Rng.Next(withCards.Count)];
                            var tStable = _stables[t];
                            if (tStable.Count > 0)
                            {
                                int di = Rng.Next(tStable.Count);
                                TryDestroyStableCard(t, di);
                                try { EmitDestroyFx(t); } catch { }
                            }
                        }
                    }
                }
            }

            // ── Summoning Ritual: sacrifice 2 cards → rescue unicorn from discard ──
            if (typ == "PASSIVE_SUMMONING")
            {
                // Need at least 2 other cards in stable to sacrifice
                int otherCount = stable.Count(ci => ci != cid);
                if (otherCount >= 2)
                {
                    // Sacrifice 2 random cards (not the summoning ritual itself)
                    for (int d = 0; d < 2; d++)
                    {
                        var sacIdxs = new List<int>();
                        for (int i = 0; i < stable.Count; i++)
                        {
                            if (stable[i] != cid) sacIdxs.Add(i);
                        }
                        if (sacIdxs.Count > 0)
                        {
                            int si = sacIdxs[Rng.Next(sacIdxs.Count)];
                            TrySacrificeStableCard(seat, si);
                        }
                    }
                    // Rescue a random unicorn from discard
                    var discUnicornIdxs = new List<int>();
                    for (int i = 0; i < _discardPile.Count; i++)
                    {
                        var ck = _cards.GetValueOrDefault(_discardPile[i])?.Kind ?? "";
                        if (ck is "baby_unicorn" or "unicorn") discUnicornIdxs.Add(i);
                    }
                    if (discUnicornIdxs.Count > 0)
                    {
                        int ri = discUnicornIdxs[Rng.Next(discUnicornIdxs.Count)];
                        var rescued = _discardPile[ri];
                        _discardPile.RemoveAt(ri);
                        AddToStable(seat, rescued);
                    }
                }
            }

            // ── Unicorn Lasso: steal a random unicorn, return at end of turn ──
            if (typ == "PASSIVE_LASSO")
            {
                var opponents = ActivePlayers.Where(p => p != seat).ToList();
                var withUnicorns = opponents.Where(p =>
                {
                    var st = _stables.GetValueOrDefault(p, new List<string>());
                    return st.Any(ci => (_cards.GetValueOrDefault(ci)?.Kind ?? "") is "baby_unicorn" or "unicorn");
                }).ToList();
                if (withUnicorns.Count > 0)
                {
                    int t = withUnicorns[Rng.Next(withUnicorns.Count)];
                    var tStable = _stables[t];
                    var uIdxs = new List<int>();
                    for (int i = 0; i < tStable.Count; i++)
                    {
                        var ck = _cards.GetValueOrDefault(tStable[i])?.Kind ?? "";
                        if (ck is "baby_unicorn" or "unicorn") uIdxs.Add(i);
                    }
                    if (uIdxs.Count > 0)
                    {
                        int ui = uIdxs[Rng.Next(uIdxs.Count)];
                        var stolen = tStable[ui];
                        tStable.RemoveAt(ui);
                        TriggerBarbedWire(t); // left source
                        AddToStable(seat, stolen);
                        _lassoStolenCard = stolen;
                        _lassoStolenFrom = t;
                        try { EmitStealFx(seat, t); } catch { }
                    }
                }
            }
        }

        // Enforce Tiny Stable after beginning-of-turn effects
        EnforceTinyStable();
        CheckWin();
    }

    private void EndTurn()
    {
        if (ActivePlayers.Count == 0) return;

        // Unicorn Lasso: return stolen unicorn at end of turn
        if (_lassoStolenCard != null && _lassoStolenFrom >= 0)
        {
            var seat = CurrentTurnSeat;
            if (seat is int s)
            {
                var myStable = _stables.GetValueOrDefault(s);
                if (myStable != null)
                {
                    int li = myStable.IndexOf(_lassoStolenCard);
                    if (li >= 0)
                    {
                        myStable.RemoveAt(li);
                        TriggerBarbedWire(s); // unicorn leaving
                        if (ActivePlayers.Contains(_lassoStolenFrom))
                            AddToStable(_lassoStolenFrom, _lassoStolenCard);
                        else
                            _discardPile.Add(_lassoStolenCard);
                    }
                }
            }
            _lassoStolenCard = null;
            _lassoStolenFrom = -1;
        }

        _currentPlayerIdx = (_currentPlayerIdx + 1) % ActivePlayers.Count;
        _prompt = null;
        ClearReaction();
        BeginTurn();
    }

    private void DrawToHand(int seat, int n)
    {
        if (!_hands.ContainsKey(seat))
            _hands[seat] = new List<string>();

        for (int i = 0; i < Math.Max(0, n); i++)
        {
            if (_drawPile.Count == 0) RefillFromDiscard();
            if (_drawPile.Count == 0) return;
            _hands[seat].Add(_drawPile[^1]);
            _drawPile.RemoveAt(_drawPile.Count - 1);
        }
    }

    private void RefillFromDiscard()
    {
        if (_discardPile.Count == 0) return;
        _drawPile.AddRange(_discardPile);
        _discardPile.Clear();
        ShuffleList(_drawPile);
    }

    private void ShuffleList<T>(List<T> list)
    {
        for (int i = list.Count - 1; i > 0; i--)
        {
            int j = Rng.Next(i + 1);
            (list[i], list[j]) = (list[j], list[i]);
        }
    }

    private int UnicornCount(int seat)
    {
        // Check for Pandamonium downgrade — unicorns don't count
        bool hasPanda = false;
        int extraUnicorns = 0;
        foreach (var cid in _stables.GetValueOrDefault(seat, new List<string>()))
        {
            var c = _cards.GetValueOrDefault(cid);
            if (c == null) continue;
            if (c.EffectType == "PASSIVE_PANDAMONIUM") hasPanda = true;
            if (c.EffectType == "PASSIVE_EXTRA_UNICORN") extraUnicorns += c.EffectInt("amount");
        }
        if (hasPanda) return Math.Max(0, extraUnicorns);

        int count = 0;
        foreach (var cid in _stables.GetValueOrDefault(seat, new List<string>()))
        {
            var kind = _cards.GetValueOrDefault(cid)?.Kind ?? "";
            if (kind is "baby_unicorn" or "unicorn")
                count++;
        }
        return count + extraUnicorns;
    }

    /// <summary>Check if a player has the "Yay" (PASSIVE_CANNOT_DESTROY) upgrade in their stable.</summary>
    private bool HasCannotDestroy(int seat)
    {
        foreach (var cid in _stables.GetValueOrDefault(seat, new List<string>()))
        {
            var c = _cards.GetValueOrDefault(cid);
            if (c != null && c.EffectType == "PASSIVE_CANNOT_DESTROY") return true;
        }
        return false;
    }

    /// <summary>Check if a player has Blinding Light (all unicorns treated as basic, no effects).</summary>
    private bool HasBlindingLight(int seat)
    {
        foreach (var cid in _stables.GetValueOrDefault(seat, new List<string>()))
            if (cid.StartsWith("blinding_light")) return true;
        return false;
    }

    /// <summary>Check if any player owns Queen Bee. Returns the owner seat or -1.</summary>
    private int QueenBeeOwner()
    {
        foreach (var s in ActivePlayers)
        {
            if (HasBlindingLight(s)) continue; // Blinding Light neutralises unicorn abilities
            foreach (var cid in _stables.GetValueOrDefault(s, new List<string>()))
                if (cid.StartsWith("queen_bee_unicorn")) return s;
        }
        return -1;
    }

    /// <summary>Check if a player has Unicorn Phoenix in stable (and it's not suppressed by Blinding Light).</summary>
    private bool HasPhoenix(int seat)
    {
        if (HasBlindingLight(seat)) return false;
        foreach (var cid in _stables.GetValueOrDefault(seat, new List<string>()))
            if (cid.StartsWith("unicorn_phoenix")) return true;
        return false;
    }

    /// <summary>Check if a player has Black Knight Unicorn in stable (and it's not suppressed by Blinding Light).</summary>
    private bool HasBlackKnight(int seat)
    {
        if (HasBlindingLight(seat)) return false;
        foreach (var cid in _stables.GetValueOrDefault(seat, new List<string>()))
            if (cid.StartsWith("black_knight_unicorn")) return true;
        return false;
    }

    /// <summary>Check if a player has Barbed Wire in their stable.</summary>
    private bool HasBarbedWire(int seat)
    {
        foreach (var cid in _stables.GetValueOrDefault(seat, new List<string>()))
            if (cid.StartsWith("barbed_wire")) return true;
        return false;
    }

    /// <summary>Trigger Barbed Wire: each player discards 1 random card.</summary>
    private void TriggerBarbedWire(int seat)
    {
        if (!HasBarbedWire(seat)) return;
        foreach (var s in ActivePlayers)
        {
            var h = _hands.GetValueOrDefault(s);
            if (h != null && h.Count > 0)
            {
                int ri = Rng.Next(h.Count);
                _discardPile.Add(h[ri]);
                h.RemoveAt(ri);
            }
        }
    }

    /// <summary>
    /// Try to destroy a card in a player's stable. Handles Yay, Black Knight substitution,
    /// and Unicorn Phoenix indestructibility. Returns true if the card was actually removed.
    /// </summary>
    private bool TryDestroyStableCard(int seat, int idx)
    {
        var stable = _stables.GetValueOrDefault(seat);
        if (stable == null || idx < 0 || idx >= stable.Count) return false;
        if (HasCannotDestroy(seat)) return false;

        var cardId = stable[idx];
        var ck = _cards.GetValueOrDefault(cardId)?.Kind ?? "";

        // Unicorn Phoenix: indestructible — stays in stable
        if (cardId.StartsWith("unicorn_phoenix") && !HasBlindingLight(seat))
            return false;

        // Black Knight: if a unicorn would be destroyed and we have Black Knight, sacrifice BK instead
        if (ck is "baby_unicorn" or "unicorn" && HasBlackKnight(seat))
        {
            int bkIdx = stable.FindIndex(c => c.StartsWith("black_knight_unicorn"));
            if (bkIdx >= 0 && bkIdx != idx)
            {
                _discardPile.Add(stable[bkIdx]);
                stable.RemoveAt(bkIdx);
                TriggerBarbedWire(seat); // BK leaving = unicorn leaving
                return false; // original card stays
            }
        }

        _discardPile.Add(stable[idx]);
        stable.RemoveAt(idx);

        // Barbed Wire trigger if a unicorn left
        if (ck is "baby_unicorn" or "unicorn")
            TriggerBarbedWire(seat);

        return true;
    }

    /// <summary>
    /// Try to sacrifice a card from a player's stable. Handles Unicorn Phoenix.
    /// Returns true if the card was actually removed.
    /// </summary>
    private bool TrySacrificeStableCard(int seat, int idx)
    {
        var stable = _stables.GetValueOrDefault(seat);
        if (stable == null || idx < 0 || idx >= stable.Count) return false;

        var cardId = stable[idx];
        var ck = _cards.GetValueOrDefault(cardId)?.Kind ?? "";

        // Unicorn Phoenix: cannot be sacrificed — stays in stable
        if (cardId.StartsWith("unicorn_phoenix") && !HasBlindingLight(seat))
            return false;

        _discardPile.Add(stable[idx]);
        stable.RemoveAt(idx);

        // Barbed Wire trigger if a unicorn left
        if (ck is "baby_unicorn" or "unicorn")
            TriggerBarbedWire(seat);

        return true;
    }

    /// <summary>Add a unicorn to a player's stable and trigger Barbed Wire if applicable.</summary>
    private void AddToStable(int seat, string cardId)
    {
        if (!_stables.ContainsKey(seat)) _stables[seat] = new List<string>();
        _stables[seat].Add(cardId);
        var ck = _cards.GetValueOrDefault(cardId)?.Kind ?? "";
        if (ck is "baby_unicorn" or "unicorn")
            TriggerBarbedWire(seat);
    }

    private void CheckWin()
    {
        foreach (var s in ActivePlayers)
        {
            if (UnicornCount(s) >= _goalUnicorns)
            {
                _winner = s;
                State = "game_over";
                _turnPhase = "action";
                _prompt = null;
                ClearReaction();
                return;
            }
        }
    }

    // ─── Reaction (Neigh) ──────────────────────────────────────

    private bool IsNeighable(string cardId)
    {
        var c = _cards.GetValueOrDefault(cardId);
        if (c == null) return false;
        if (c.Kind is "neigh" or "super_neigh") return false;
        return true;
    }

    private void OpenReaction(int actor, string cardId, Dictionary<string, object?>? target)
    {
        _reactionActive = true;
        _reactionActor = actor;
        _reactionCardId = cardId;
        _reactionTarget = target != null ? new Dictionary<string, object?>(target) : new();
        _reactionStack = new List<string>();
        _reactionPending = new HashSet<int>(ActivePlayers.Where(s => s != actor));
        _turnPhase = "reaction";
    }

    private void ClearReaction()
    {
        _reactionActive = false;
        _reactionActor = null;
        _reactionCardId = null;
        _reactionTarget = null;
        _reactionPending = new HashSet<int>();
        _reactionStack = new List<string>();
    }

    private bool ReactionResultAllowsResolve()
    {
        // If last reaction is SUPER_NEIGH => card is negated unconditionally
        if (_reactionStack.Count > 0)
        {
            var last = _reactionStack[^1];
            var c = _cards.GetValueOrDefault(last);
            if (c != null && c.Kind == "super_neigh") return false;
        }

        int neighCount = 0;
        foreach (var cid in _reactionStack)
        {
            var kind = _cards.GetValueOrDefault(cid)?.Kind ?? "";
            if (kind is "neigh" or "super_neigh")
                neighCount++;
        }
        return (neighCount % 2) == 0;
    }

    // ─── Click handling ────────────────────────────────────────

    public override void HandleClick(int playerIdx, string buttonId)
    {
        // Game-specific messages from server passthrough
        if (buttonId.StartsWith("__msg__:"))
        {
            // No game-specific messages for UU currently
            return;
        }

        int seat = playerIdx;
        if (State == "player_select") return;
        if (_winner != null) return;
        if (!ActivePlayers.Contains(seat)) return;

        // Reaction buttons
        if (_reactionActive)
        {
            // Simultaneous: any pending (non-actor) player can respond
            if (!_reactionPending.Contains(seat)) return;

            // Allow clicking a Neigh/Super Neigh card directly from hand (uu_play:{idx})
            if (buttonId.StartsWith("uu_play:"))
            {
                if (!int.TryParse(buttonId.AsSpan(8), out int idx)) return;
                var hand = _hands.GetValueOrDefault(seat);
                if (hand == null || idx < 0 || idx >= hand.Count) return;
                var cid = hand[idx];
                var c = _cards.GetValueOrDefault(cid);
                if (c == null) return;
                if (c.Kind == "neigh")
                    buttonId = "uu_react_neigh";
                else if (c.Kind == "super_neigh")
                    buttonId = "uu_react_super";
                else
                    return; // Only neigh cards during reaction
            }

            if (buttonId is "uu_react_pass" or "uu_react_neigh" or "uu_react_super")
            {
                if (buttonId == "uu_react_neigh")
                {
                    if (!RemoveOneByKind(seat, "neigh")) return;
                    _discardPile.Add("neigh");
                    _reactionStack.Add("neigh");
                }
                else if (buttonId == "uu_react_super")
                {
                    if (!RemoveOneByKind(seat, "super_neigh")) return;
                    _discardPile.Add("super_neigh");
                    _reactionStack.Add("super_neigh");
                }

                // Animate the neigh card flying to centre
                if (buttonId is "uu_react_neigh" or "uu_react_super")
                {
                    int cx = ScreenW / 2, cy = ScreenH / 2;
                    var src = _zoneCenters.GetValueOrDefault(seat, (cx, cy));
                    _cardFlips.Add(new CardFlyAnim(src, (cx, cy), color: (220, 30, 30)));
                    _flashes.Add(new ScreenFlash((220, 30, 30), 110, 0.38f));
                    _textPops.Add(new TextPopAnim("NEIGH! \ud83d\udeab", cx, cy - 20,
                        (255, 80, 60), fontSize: 52, duration: 1.6f));
                    _screenShakeTimer = 0.3f;
                    NoteEvent($"{PlayerName(seat)} played Neigh!");

                    // A Neigh/Super Neigh immediately ends the reaction window
                    _reactionPending.Clear();
                    ResolveReaction();
                    RebuildButtons();
                    return;
                }

                // Pass: mark this player as responded
                _reactionPending.Remove(seat);
                if (_reactionPending.Count == 0)
                    ResolveReaction();
                RebuildButtons();
            }
            return;
        }

        // Prompt targeting
        if (_prompt != null && !PromptKindIs("PLAY"))
        {
            int actor = PromptInt("actor", -1);
            if (seat != actor) return;

            if (buttonId.StartsWith("uu_target_player:"))
            {
                if (!int.TryParse(buttonId.AsSpan(17), out int t)) return;
                _prompt["target_player"] = t;
                AdvancePrompt();
                RebuildButtons();
            }
            else if (buttonId == "uu_cancel_prompt")
            {
                // Cancel the prompt: return the card to hand and reset
                var cardId = PromptString("card_id");
                if (!string.IsNullOrEmpty(cardId))
                {
                    if (!_hands.ContainsKey(actor)) _hands[actor] = new List<string>();
                    _hands[actor].Add(cardId);
                }
                _prompt = null;
                _turnPhase = "action";
                _actionTaken = false;
                RebuildButtons();
            }
            else if (buttonId.StartsWith("uu_target_card:"))
            {
                var rest = buttonId[15..];
                var parts = rest.Split(':', 2);
                if (parts.Length < 2) return;
                if (!int.TryParse(parts[0], out int t) || !int.TryParse(parts[1], out int idx)) return;
                _prompt["target_player"] = t;
                _prompt["target_index"] = idx;
                AdvancePrompt();
                RebuildButtons();
            }
            return;
        }

        // Normal turn actions
        bool isTurn = seat == CurrentTurnSeat;

        if (buttonId == "uu_draw_action")
        {
            if (!isTurn || _turnPhase != "action" || _actionTaken) return;
            DrawToHand(seat, 1);
            _actionTaken = true;
            _turnPhase = (_hands.GetValueOrDefault(seat)?.Count ?? 0) > HandLimit(seat) ? "discard" : "action";
            NoteEvent($"{PlayerName(seat)} drew a card");

            var ctr = _zoneCenters.GetValueOrDefault(seat, (ScreenW / 2, ScreenH / 2));
            var col = SeatColors[seat % SeatColors.Length];
            _particles.EmitSparkle(ctr.Item1, ctr.Item2, col, 14);
            RebuildButtons();
            return;
        }

        if (buttonId == "uu_end_turn")
        {
            if (!isTurn) return;
            if (_turnPhase == "discard") return;
            if (!_actionTaken) return;
            EndTurn();
            RebuildButtons();
            return;
        }

        if (buttonId.StartsWith("uu_discard:"))
        {
            if (!isTurn || _turnPhase != "discard") return;
            if (!int.TryParse(buttonId.AsSpan(11), out int idx)) return;
            DiscardFromHand(seat, idx);
            if (_forcedDiscardCount > 0) _forcedDiscardCount--;
            if (_forcedDiscardCount <= 0 && (_hands.GetValueOrDefault(seat)?.Count ?? 0) <= HandLimit(seat))
                _turnPhase = "action";
            RebuildButtons();
            return;
        }

        if (buttonId.StartsWith("uu_play:"))
        {
            if (!int.TryParse(buttonId.AsSpan(8), out int idx)) return;

            // Capture card info before PlayFromHand removes it
            var hand = _hands.GetValueOrDefault(seat);
            string? cardEmoji = null, cardKind = null;
            string cardName = "a card";
            string? cardDesc = null;
            (int, int, int) cardRgb = (160, 80, 200);
            if (hand != null && idx >= 0 && idx < hand.Count)
            {
                var cid = hand[idx];
                var cd = _cards.GetValueOrDefault(cid);
                if (cd != null)
                {
                    cardEmoji = cd.Emoji;
                    cardKind = cd.Kind;
                    cardName = cd.Name;
                    cardDesc = cd.Desc;
                    cardRgb = HexToRgb(cd.Color, (160, 80, 200));
                }
            }

            PlayFromHand(seat, idx);
            // Animate card flying to play area
            var src = _zoneCenters.GetValueOrDefault(seat, (ScreenW / 2, ScreenH / 2));
            var dst = (ScreenW / 2, ScreenH / 3);
            var col = SeatColors[seat % SeatColors.Length];
            _cardFlips.Add(new CardFlyAnim(src, dst, color: col));
            NoteEvent($"{PlayerName(seat)} played {cardName}");

            // Showcase the card face-up at center with sparkles
            if (cardEmoji != null)
            {
                string corner = (cardKind?.Length ?? 0) > 4
                    ? cardKind![..4].ToUpperInvariant()
                    : (cardKind ?? "").ToUpperInvariant();
                _showcases.Add(new CardShowcaseAnim(
                    ScreenW / 2, ScreenH / 2,
                    cardEmoji, "", accentColor: cardRgb, corner: corner,
                    src: (src.Item1, src.Item2),
                    kind: cardKind, cardName: cardName, desc: cardDesc));
            }

            _particles.EmitSparkle(dst.Item1, dst.Item2, col, 20);
            RebuildButtons();
            return;
        }
    }

    // ─── Prompt helpers ────────────────────────────────────────

    private bool PromptKindIs(string kind)
    {
        if (_prompt == null) return false;
        return _prompt.TryGetValue("kind", out var v) && v is string s && s == kind;
    }

    private int PromptInt(string key, int fallback)
    {
        if (_prompt == null) return fallback;
        if (!_prompt.TryGetValue(key, out var v)) return fallback;
        if (v is int i) return i;
        if (v is long l) return (int)l;
        return fallback;
    }

    private string PromptString(string key, string fallback = "")
    {
        if (_prompt == null) return fallback;
        if (!_prompt.TryGetValue(key, out var v)) return fallback;
        return v?.ToString() ?? fallback;
    }

    // ─── Internal methods ──────────────────────────────────────

    private bool RemoveOneByKind(int seat, string kind)
    {
        var hand = _hands.GetValueOrDefault(seat);
        if (hand == null) return false;
        for (int i = 0; i < hand.Count; i++)
        {
            var c = _cards.GetValueOrDefault(hand[i]);
            if (c != null && c.Kind == kind)
            {
                hand.RemoveAt(i);
                return true;
            }
        }
        return false;
    }

    private void DiscardFromHand(int seat, int idx)
    {
        var hand = _hands.GetValueOrDefault(seat);
        if (hand == null || idx < 0 || idx >= hand.Count) return;
        var cid = hand[idx];
        hand.RemoveAt(idx);
        _discardPile.Add(cid);
    }

    /// <summary>Check if a player has Broken Stable in their stable (cannot play upgrades).</summary>
    private bool HasBrokenStable(int seat)
    {
        foreach (var cid in _stables.GetValueOrDefault(seat, new List<string>()))
        {
            if (cid.StartsWith("broken_stable")) return true;
        }
        return false;
    }

    /// <summary>Count raw unicorns (baby + unicorn kind) in stable, ignoring extras.</summary>
    private int RawUnicornCount(int seat)
    {
        int count = 0;
        foreach (var cid in _stables.GetValueOrDefault(seat, new List<string>()))
        {
            var kind = _cards.GetValueOrDefault(cid)?.Kind ?? "";
            if (kind is "baby_unicorn" or "unicorn") count++;
        }
        return count;
    }

    /// <summary>Check if a player has Tiny Stable in their stable.</summary>
    private bool HasTinyStable(int seat)
    {
        foreach (var cid in _stables.GetValueOrDefault(seat, new List<string>()))
        {
            if (cid.StartsWith("tiny_stable")) return true;
        }
        return false;
    }

    /// <summary>Enforce Tiny Stable: if a player has Tiny Stable and more than 5 unicorns, sacrifice excess randomly.</summary>
    private void EnforceTinyStable()
    {
        foreach (var s in ActivePlayers)
        {
            if (!HasTinyStable(s)) continue;
            while (RawUnicornCount(s) > 5)
            {
                var stable = _stables.GetValueOrDefault(s);
                if (stable == null) break;
                var unicornIdxs = new List<int>();
                for (int i = 0; i < stable.Count; i++)
                {
                    var kind = _cards.GetValueOrDefault(stable[i])?.Kind ?? "";
                    if (kind is "baby_unicorn" or "unicorn") unicornIdxs.Add(i);
                }
                if (unicornIdxs.Count == 0) break;
                int ri = unicornIdxs[Rng.Next(unicornIdxs.Count)];
                _discardPile.Add(stable[ri]);
                stable.RemoveAt(ri);
            }
        }
    }

    private void PlayFromHand(int seat, int idx)
    {
        if (State != "playing") return;
        var hand = _hands.GetValueOrDefault(seat);
        if (hand == null || idx < 0 || idx >= hand.Count) return;
        var cid = hand[idx];
        var c = _cards.GetValueOrDefault(cid);
        if (c == null) return;

        // Instants can be played any time (outside reaction window)
        if (c.Kind == "instant")
        {
            hand.RemoveAt(idx);
            ResolveEffect(seat, cid);
            _discardPile.Add(cid);
            CheckWin();
            return;
        }

        // Neigh cards are only meaningful during reaction, handled elsewhere
        if (c.Kind is "neigh" or "super_neigh") return;

        // Non-instant: only on your turn, once per turn
        if (seat != CurrentTurnSeat) return;
        if (_turnPhase != "action") return;
        if (_actionTaken) return;

        // Broken Stable: cannot play upgrade cards
        if (c.Kind == "upgrade" && HasBrokenStable(seat)) return;

        // Queen Bee: basic unicorns cannot enter any other player's stable
        if (c.Kind == "unicorn" && c.Id.StartsWith("unicorn_basic"))
        {
            int qbOwner = QueenBeeOwner();
            if (qbOwner >= 0 && qbOwner != seat) return; // blocked by Queen Bee
        }

        // Remove from hand now
        hand.RemoveAt(idx);

        // Some effects require target selection
        var effectType = c.EffectType;
        bool needsPickPlayerAndCard = effectType is "STEAL_UNICORN" or "DESTROY_STABLE_CARD" or "SWAP_UNICORN"
            or "DESTROY_UD_ON_ENTER" or "RETURN_CARD_ON_ENTER" or "RETURN_UNICORN_ON_ENTER" or "DESTROY_UNICORN_ON_ENTER"
            or "BACK_KICK" or "TARGETED_DESTRUCTION" or "STEAL_ON_ENTER";
        bool needsPickPlayerOnly = effectType is "FORCE_DISCARD_ON_ENTER" or "BLATANT_THIEVERY"
            or "TWO_FOR_ONE" or "TRADE_HANDS" or "SHRINK_RAY";

        // Downgrades always target another player's stable
        if (c.Kind == "downgrade" && !needsPickPlayerAndCard && !needsPickPlayerOnly)
            needsPickPlayerOnly = true;

        if (needsPickPlayerAndCard || needsPickPlayerOnly)
        {
            // Downgrades that weren't already in a specific targeting flow use generic kind
            string promptKind = effectType;
            if (c.Kind == "downgrade" && effectType is not "FORCE_DISCARD_ON_ENTER"
                and not "BLATANT_THIEVERY" and not "TWO_FOR_ONE" and not "TRADE_HANDS")
                promptKind = "DOWNGRADE_TARGET";

            _prompt = new Dictionary<string, object?>
            {
                ["kind"] = promptKind,
                ["actor"] = seat,
                ["card_id"] = cid,
                ["step"] = "pick_player",
            };
            _turnPhase = "prompt";
            return;
        }

        // Neigh window for neighable cards
        if (IsNeighable(cid))
        {
            OpenReaction(actor: seat, cardId: cid, target: null);
            _prompt = new Dictionary<string, object?>
            {
                ["kind"] = "PLAY",
                ["actor"] = seat,
                ["card_id"] = cid,
            };
            return;
        }

        // Otherwise resolve immediately
        ResolveEffect(seat, cid);
        _actionTaken = true;
        _discardPile.Add(cid);
        CheckWin();
    }

    private void AdvancePrompt()
    {
        if (_prompt == null) return;
        var kind = PromptString("kind");
        int actor = PromptInt("actor", -1);
        string cardId = PromptString("card_id");

        if (kind == "PLAY") return;

        if (kind is "STEAL_UNICORN" or "DESTROY_STABLE_CARD" or "SWAP_UNICORN"
            or "DESTROY_UD_ON_ENTER" or "RETURN_CARD_ON_ENTER" or "RETURN_UNICORN_ON_ENTER" or "DESTROY_UNICORN_ON_ENTER"
            or "BACK_KICK" or "TARGETED_DESTRUCTION" or "STEAL_ON_ENTER"
            or "FORCE_DISCARD_ON_ENTER" or "BLATANT_THIEVERY" or "TWO_FOR_ONE" or "TRADE_HANDS"
            or "DOWNGRADE_TARGET" or "SHRINK_RAY")
        {
            var step = PromptString("step");
            if (step == "pick_player")
            {
                int t = PromptInt("target_player", -1);
                if (t < 0 || !ActivePlayers.Contains(t)) return;

                // Effects that must NOT target self (steal/swap/thievery/downgrades etc.)
                bool noSelfTarget = kind is "STEAL_UNICORN" or "SWAP_UNICORN"
                    or "FORCE_DISCARD_ON_ENTER" or "BLATANT_THIEVERY"
                    or "TWO_FOR_ONE" or "TRADE_HANDS" or "DOWNGRADE_TARGET"
                    or "STEAL_ON_ENTER" or "SHRINK_RAY";
                if (noSelfTarget && t == actor) return;

                // Types that only need pick_player go straight to reaction
                bool pickPlayerOnly = kind is "FORCE_DISCARD_ON_ENTER" or "BLATANT_THIEVERY"
                    or "TWO_FOR_ONE" or "TRADE_HANDS" or "DOWNGRADE_TARGET" or "SHRINK_RAY";
                if (pickPlayerOnly)
                {
                    OpenReaction(actor: actor, cardId: cardId,
                        target: new Dictionary<string, object?>
                        {
                            ["target_player"] = t,
                            ["kind"] = kind,
                        });
                    _prompt = new Dictionary<string, object?>
                    {
                        ["kind"] = "PLAY",
                        ["actor"] = actor,
                        ["card_id"] = cardId,
                        ["target"] = new Dictionary<string, object?>
                        {
                            ["target_player"] = t,
                            ["kind"] = kind,
                        },
                    };
                    _turnPhase = "reaction";
                    return;
                }

                _prompt["step"] = "pick_card";
                return;
            }

            if (step == "pick_card")
            {
                int t = PromptInt("target_player", -1);
                int idx = PromptInt("target_index", -1);
                var targetStable = _stables.GetValueOrDefault(t, new List<string>()).ToList();

                if (kind is "STEAL_UNICORN" or "SWAP_UNICORN" or "DESTROY_UNICORN_ON_ENTER" or "STEAL_ON_ENTER"
                    or "RETURN_UNICORN_ON_ENTER")
                {
                    var eligible = new List<int>();
                    for (int i = 0; i < targetStable.Count; i++)
                    {
                        var ck = _cards.GetValueOrDefault(targetStable[i])?.Kind ?? "";
                        if (ck is "baby_unicorn" or "unicorn") eligible.Add(i);
                    }
                    if (!eligible.Contains(idx)) return;
                }
                else if (kind is "DESTROY_UD_ON_ENTER" or "TARGETED_DESTRUCTION")
                {
                    var eligible = new List<int>();
                    for (int i = 0; i < targetStable.Count; i++)
                    {
                        var ck = _cards.GetValueOrDefault(targetStable[i])?.Kind ?? "";
                        if (ck is "upgrade" or "downgrade") eligible.Add(i);
                    }
                    if (!eligible.Contains(idx)) return;
                }
                else
                {
                    if (idx < 0 || idx >= targetStable.Count) return;
                }

                // Neigh window for the magic card
                OpenReaction(actor: actor, cardId: cardId,
                    target: new Dictionary<string, object?>
                    {
                        ["target_player"] = t,
                        ["target_index"] = idx,
                        ["kind"] = kind,
                    });
                _prompt = new Dictionary<string, object?>
                {
                    ["kind"] = "PLAY",
                    ["actor"] = actor,
                    ["card_id"] = cardId,
                    ["target"] = new Dictionary<string, object?>
                    {
                        ["target_player"] = t,
                        ["target_index"] = idx,
                        ["kind"] = kind,
                    },
                };
                _turnPhase = "reaction";
            }
        }
    }

    private void ResolveReaction()
    {
        if (_prompt == null || !PromptKindIs("PLAY"))
        {
            ClearReaction();
            _turnPhase = "action";
            return;
        }

        int actor = PromptInt("actor", -1);
        string cardId = PromptString("card_id");

        Dictionary<string, object?>? target = null;
        if (_prompt.TryGetValue("target", out var tObj) && tObj is Dictionary<string, object?> td)
            target = td;

        bool resolves = ReactionResultAllowsResolve();
        ClearReaction();

        if (resolves)
            ResolveEffect(actor, cardId, target);

        // Enforce Tiny Stable limit for all players after effect resolution
        EnforceTinyStable();

        // Discard the played card (magic/instant cards); stable cards were already placed by ResolveEffect
        var rc = _cards.GetValueOrDefault(cardId);
        bool placedInStable = rc != null && rc.Kind is not "magic" and not "instant" and not "neigh" and not "super_neigh";
        if (!placedInStable)
            _discardPile.Add(cardId);
        _prompt = null;
        _actionTaken = true;
        bool needsDiscard = (_hands.GetValueOrDefault(actor)?.Count ?? 0) > HandLimit(actor) || _forcedDiscardCount > 0;
        _turnPhase = needsDiscard ? "discard" : "action";
        CheckWin();
    }

    private void ResolveEffect(int actor, string cardId, Dictionary<string, object?>? target = null)
    {
        var c = _cards.GetValueOrDefault(cardId);
        if (c == null) return;
        var typ = c.EffectType;

        if (typ == "NONE") return;

        // ─── Cards that go into the player's stable ──────
        if (typ == "STABLE_ADD_SELF")
        {
            // Downgrades go into the target player's stable
            int stableSeat = actor;
            if (c.Kind == "downgrade" && target != null)
            {
                int ts = TargetInt(target, "target_player", -1);
                if (ts >= 0 && ActivePlayers.Contains(ts)) stableSeat = ts;
            }
            if (!_stables.ContainsKey(stableSeat)) _stables[stableSeat] = new List<string>();
            _stables[stableSeat].Add(cardId);
            return;
        }

        // ─── Passive stable effects (upgrade/downgrade) ──
        if (typ is "PASSIVE_DRAW_BONUS" or "PASSIVE_HAND_LIMIT_MOD"
            or "PASSIVE_EXTRA_UNICORN" or "PASSIVE_PANDAMONIUM"
            or "PASSIVE_CANNOT_DESTROY"
            or "PASSIVE_BLACK_KNIGHT" or "PASSIVE_QUEEN_BEE"
            or "PASSIVE_PHOENIX" or "PASSIVE_FERTILE"
            or "PASSIVE_RHINOCORN" or "PASSIVE_ZOMBIE"
            or "PASSIVE_GLITTER_BOMB" or "PASSIVE_LASSO"
            or "PASSIVE_SUMMONING" or "PASSIVE_SADISTIC"
            or "PASSIVE_BLINDING_LIGHT" or "PASSIVE_BARBED_WIRE")
        {
            // Downgrades go into the target player's stable; upgrades into the actor's
            int stableSeat = actor;
            if (c.Kind == "downgrade" && target != null)
            {
                int ts = TargetInt(target, "target_player", -1);
                if (ts >= 0 && ActivePlayers.Contains(ts)) stableSeat = ts;
            }
            if (!_stables.ContainsKey(stableSeat)) _stables[stableSeat] = new List<string>();
            _stables[stableSeat].Add(cardId);
            return;
        }

        // ─── Enter-stable effects (unicorn goes to stable + bonus) ──

        // Blinding Light suppression: if actor has Blinding Light, unicorn enter effects are neutralised
        bool enterSuppressed = (c.Kind is "unicorn" or "baby_unicorn") && HasBlindingLight(actor);

        if (typ == "DRAW_ON_ENTER")
        {
            AddToStable(actor, cardId);
            if (!enterSuppressed)
            {
                int n = c.EffectInt("amount", 1);
                DrawToHand(actor, Math.Max(0, n));
            }
            return;
        }

        if (typ == "STEAL_RANDOM_ON_ENTER")
        {
            AddToStable(actor, cardId);
            if (!enterSuppressed)
            {
                // Steal a random card from a random opponent's hand
                var opponents = ActivePlayers.Where(s => s != actor).ToList();
                var withCards = opponents.Where(s => (_hands.GetValueOrDefault(s)?.Count ?? 0) > 0).ToList();
                if (withCards.Count > 0)
                {
                    int t = withCards[Rng.Next(withCards.Count)];
                    var h = _hands[t];
                    int ri = Rng.Next(h.Count);
                    var stolen = h[ri];
                    h.RemoveAt(ri);
                    if (!_hands.ContainsKey(actor)) _hands[actor] = new List<string>();
                    _hands[actor].Add(stolen);
                    try { EmitStealFx(actor, t); } catch { }
                }
            }
            return;
        }

        if (typ == "SEARCH_DECK_ON_ENTER")
        {
            AddToStable(actor, cardId);
            if (!enterSuppressed)
            {
                // Search draw pile for a card matching criteria
                string? searchKind = null;
                string? searchName = null;
                if (c.Effect.TryGetValue("search_kind", out var skEl))
                    searchKind = skEl.GetString();
                if (c.Effect.TryGetValue("search_name", out var snEl))
                    searchName = snEl.GetString();

                int foundIdx = -1;
                for (int i = 0; i < _drawPile.Count; i++)
                {
                    var dc = _cards.GetValueOrDefault(_drawPile[i]);
                    if (dc == null) continue;
                    if (searchKind != null && dc.Kind != searchKind) continue;
                    if (searchName != null && !dc.Name.Contains(searchName, StringComparison.OrdinalIgnoreCase)) continue;
                    foundIdx = i;
                    break;
                }
                if (foundIdx >= 0)
                {
                    var found = _drawPile[foundIdx];
                    _drawPile.RemoveAt(foundIdx);
                    if (!_hands.ContainsKey(actor)) _hands[actor] = new List<string>();
                    _hands[actor].Add(found);
                    ShuffleList(_drawPile);
                    var fname = _cards.GetValueOrDefault(found)?.Name ?? found;
                    try
                    {
                        _textPops.Add(new TextPopAnim($"Found: {fname}!", ScreenW / 2, ScreenH / 2 - 30,
                            (180, 220, 255), fontSize: 20, duration: 1.6f));
                    }
                    catch { }
                }
            }
            return;
        }

        if (typ == "DRAW_AND_DISCARD_ON_ENTER")
        {
            AddToStable(actor, cardId);
            if (!enterSuppressed)
            {
                int drawN = c.EffectInt("draw", 2);
                int discN = c.EffectInt("discard", 1);
                DrawToHand(actor, Math.Max(0, drawN));
                _forcedDiscardCount += Math.Max(0, discN);
            }
            return;
        }

        if (typ == "ALL_DISCARD_ON_ENTER")
        {
            AddToStable(actor, cardId);
            if (!enterSuppressed)
            {
                foreach (var s in ActivePlayers)
                {
                    if (s == actor) continue;
                    var h = _hands.GetValueOrDefault(s);
                    if (h != null && h.Count > 0)
                    {
                        int ri = Rng.Next(h.Count);
                        _discardPile.Add(h[ri]);
                        h.RemoveAt(ri);
                    }
                }
            }
            return;
        }

        if (typ == "FORCE_DISCARD_ON_ENTER")
        {
            AddToStable(actor, cardId);
            if (!enterSuppressed)
            {
                int t = TargetInt(target, "target_player", -1);
                if (ActivePlayers.Contains(t))
                {
                    var h = _hands.GetValueOrDefault(t);
                    if (h != null && h.Count > 0)
                    {
                        int ri = Rng.Next(h.Count);
                        _discardPile.Add(h[ri]);
                        h.RemoveAt(ri);
                    }
                }
            }
            return;
        }

        if (typ == "DESTROY_UD_ON_ENTER")
        {
            AddToStable(actor, cardId);
            if (!enterSuppressed)
            {
                int t = TargetInt(target, "target_player", -1);
                int idx = TargetInt(target, "target_index", -1);
                if (!ActivePlayers.Contains(t)) return;
                var src = _stables.GetValueOrDefault(t);
                if (src == null || idx < 0 || idx >= src.Count) return;
                var ck = _cards.GetValueOrDefault(src[idx])?.Kind ?? "";
                if (ck is not ("upgrade" or "downgrade")) return;
                TryDestroyStableCard(t, idx);
                try { EmitDestroyFx(t); } catch { }
            }
            return;
        }

        if (typ is "RETURN_CARD_ON_ENTER" or "RETURN_UNICORN_ON_ENTER")
        {
            AddToStable(actor, cardId);
            if (!enterSuppressed)
            {
                int t = TargetInt(target, "target_player", -1);
                int idx = TargetInt(target, "target_index", -1);
                if (!ActivePlayers.Contains(t)) return;
                var src = _stables.GetValueOrDefault(t);
                if (src == null || idx < 0 || idx >= src.Count) return;
                var moved = src[idx];
                src.RemoveAt(idx);
                if (!_hands.ContainsKey(t)) _hands[t] = new List<string>();
                _hands[t].Add(moved);
                // Barbed Wire: unicorn left target's stable
                var mvk = _cards.GetValueOrDefault(moved)?.Kind ?? "";
                if (mvk is "baby_unicorn" or "unicorn") TriggerBarbedWire(t);
            }
            return;
        }

        if (typ == "DESTROY_UNICORN_ON_ENTER")
        {
            AddToStable(actor, cardId);
            if (!enterSuppressed)
            {
                int t = TargetInt(target, "target_player", -1);
                int idx = TargetInt(target, "target_index", -1);
                if (!ActivePlayers.Contains(t)) return;
                var src = _stables.GetValueOrDefault(t);
                if (src == null || idx < 0 || idx >= src.Count) return;
                if (TryDestroyStableCard(t, idx))
                    try { EmitDestroyFx(t); } catch { }
                // Narwhal Torpedo: sacrifice self after destroying
                if (cardId.StartsWith("narwhal_torpedo"))
                {
                    var myStable = _stables.GetValueOrDefault(actor);
                    if (myStable != null)
                    {
                        int si = myStable.IndexOf(cardId);
                        if (si >= 0) TrySacrificeStableCard(actor, si);
                    }
                }
            }
            return;
        }

        if (typ == "STEAL_ON_ENTER")
        {
            AddToStable(actor, cardId);
            if (!enterSuppressed)
            {
                int t = TargetInt(target, "target_player", -1);
                int idx = TargetInt(target, "target_index", -1);
                if (!ActivePlayers.Contains(t)) return;
                if (_protectedTurns.GetValueOrDefault(t, 0) > 0) return;
                var src = _stables.GetValueOrDefault(t);
                if (src == null || idx < 0 || idx >= src.Count) return;
                var moved = src[idx];
                src.RemoveAt(idx);
                TriggerBarbedWire(t); // unicorn left target's stable
                AddToStable(actor, moved);
                try { EmitStealFx(actor, t); } catch { }
            }
            return;
        }

        if (typ == "RESCUE_FROM_DISCARD")
        {
            AddToStable(actor, cardId);
            if (!enterSuppressed)
            {
                // Find a random unicorn in the discard pile and move it to actor's stable
                var unicornIdxs = new List<int>();
                for (int i = 0; i < _discardPile.Count; i++)
                {
                    var ck = _cards.GetValueOrDefault(_discardPile[i])?.Kind ?? "";
                    if (ck is "baby_unicorn" or "unicorn") unicornIdxs.Add(i);
                }
                if (unicornIdxs.Count > 0)
                {
                    int ri = unicornIdxs[Rng.Next(unicornIdxs.Count)];
                    var rescued = _discardPile[ri];
                    _discardPile.RemoveAt(ri);
                    AddToStable(actor, rescued);
                }
            }
            return;
        }

        // ─── Standard effects ────────────────────────────

        if (typ == "DRAW")
        {
            int n = c.EffectInt("amount");
            DrawToHand(actor, Math.Max(0, n));
            return;
        }

        if (typ == "PROTECT_SELF")
        {
            int turns = c.EffectInt("turns", 1);
            _protectedTurns[actor] = Math.Max(_protectedTurns.GetValueOrDefault(actor, 0), Math.Max(0, turns));
            return;
        }

        if (typ == "STEAL_UNICORN")
        {
            int t = TargetInt(target, "target_player", -1);
            int idx = TargetInt(target, "target_index", -1);
            if (!ActivePlayers.Contains(t)) return;
            if (_protectedTurns.GetValueOrDefault(t, 0) > 0) return;
            var src = _stables.GetValueOrDefault(t);
            if (src == null || idx < 0 || idx >= src.Count) return;
            var moved = src[idx];
            src.RemoveAt(idx);
            TriggerBarbedWire(t); // unicorn left
            AddToStable(actor, moved);
            try { EmitStealFx(actor, t); } catch { }
            return;
        }

        if (typ == "DESTROY_STABLE_CARD")
        {
            int t = TargetInt(target, "target_player", -1);
            int idx = TargetInt(target, "target_index", -1);
            if (!ActivePlayers.Contains(t)) return;
            if (_protectedTurns.GetValueOrDefault(t, 0) > 0) return;
            var src = _stables.GetValueOrDefault(t);
            if (src == null || idx < 0 || idx >= src.Count) return;
            if (TryDestroyStableCard(t, idx))
                try { EmitDestroyFx(t); } catch { }
            return;
        }

        if (typ == "SWAP_UNICORN")
        {
            int t = TargetInt(target, "target_player", -1);
            int idx = TargetInt(target, "target_index", -1);
            if (!ActivePlayers.Contains(t)) return;
            if (_protectedTurns.GetValueOrDefault(t, 0) > 0) return;

            var their = _stables.GetValueOrDefault(t);
            if (their == null || idx < 0 || idx >= their.Count) return;

            var mine = _stables.GetValueOrDefault(actor);
            if (mine == null) return;

            var myUnicornIdxs = new List<int>();
            for (int i = 0; i < mine.Count; i++)
            {
                var ck = _cards.GetValueOrDefault(mine[i])?.Kind ?? "";
                if (ck is "baby_unicorn" or "unicorn") myUnicornIdxs.Add(i);
            }
            if (myUnicornIdxs.Count == 0) return;
            int myI = myUnicornIdxs[Rng.Next(myUnicornIdxs.Count)];

            (mine[myI], their[idx]) = (their[idx], mine[myI]);
            TriggerBarbedWire(actor); // unicorn swap triggers barbed wire
            TriggerBarbedWire(t);
            try
            {
                int cx = ScreenW / 2, cy = ScreenH / 2;
                _flashes.Add(new ScreenFlash((180, 120, 255), 40, 0.3f));
                _pulseRings.Add(new PulseRing(cx, cy, (180, 160, 255), maxRadius: Math.Min(ScreenW, ScreenH) / 5, duration: 0.5f));
                _textPops.Add(new TextPopAnim("🔄 SWAP!", cx, cy - 30, (200, 180, 255), fontSize: 26));
            }
            catch { }
            return;
        }

        if (typ == "SACRIFICE_ONE_DRAW")
        {
            var mine = _stables.GetValueOrDefault(actor);
            if (mine != null)
            {
                var unicornIdxs = new List<int>();
                for (int i = 0; i < mine.Count; i++)
                {
                    var ck = _cards.GetValueOrDefault(mine[i])?.Kind ?? "";
                    if (ck is "baby_unicorn" or "unicorn") unicornIdxs.Add(i);
                }
                if (unicornIdxs.Count > 0)
                {
                    int i = unicornIdxs[Rng.Next(unicornIdxs.Count)];
                    TrySacrificeStableCard(actor, i);
                }
            }
            int n = c.EffectInt("amount");
            DrawToHand(actor, Math.Max(0, n));
            return;
        }

        // ─── New magic card effects ──────────────────────

        if (typ == "BACK_KICK")
        {
            int t = TargetInt(target, "target_player", -1);
            int idx = TargetInt(target, "target_index", -1);
            if (!ActivePlayers.Contains(t)) return;
            var src = _stables.GetValueOrDefault(t);
            if (src == null || idx < 0 || idx >= src.Count) return;
            var moved = src[idx];
            src.RemoveAt(idx);
            if (!_hands.ContainsKey(t)) _hands[t] = new List<string>();
            _hands[t].Add(moved);
            return;
        }

        if (typ == "BLATANT_THIEVERY")
        {
            int t = TargetInt(target, "target_player", -1);
            if (!ActivePlayers.Contains(t)) return;
            var h = _hands.GetValueOrDefault(t);
            if (h == null || h.Count == 0)
            {
                _textPops.Add(new TextPopAnim("No cards to steal!", ScreenW / 2, ScreenH / 2 - 30,
                    (200, 200, 200), fontSize: 20, duration: 1.4f));
                return;
            }
            int ri = Rng.Next(h.Count);
            var stolen = h[ri];
            h.RemoveAt(ri);
            if (!_hands.ContainsKey(actor)) _hands[actor] = new List<string>();
            _hands[actor].Add(stolen);
            var stolenName = _cards.GetValueOrDefault(stolen)?.Name ?? stolen;
            try
            {
                EmitStealFx(actor, t);
                _textPops.Add(new TextPopAnim($"Stole {stolenName}!", ScreenW / 2, ScreenH / 2 + 20,
                    (180, 255, 180), fontSize: 20, duration: 1.6f));
            }
            catch { }
            return;
        }

        if (typ == "CHANGE_OF_LUCK")
        {
            var h = _hands.GetValueOrDefault(actor);
            if (h == null) return;
            int count = h.Count;
            foreach (var cid in h) _discardPile.Add(cid);
            h.Clear();
            DrawToHand(actor, count);
            return;
        }

        if (typ == "GOOD_DEAL")
        {
            DrawToHand(actor, 3);
            // Player must choose 1 card to discard (handled via forced discard phase)
            _forcedDiscardCount += 1;
            return;
        }

        if (typ == "GLITTER_TORNADO")
        {
            foreach (var s in ActivePlayers)
            {
                var stable = _stables.GetValueOrDefault(s);
                if (stable == null || stable.Count == 0) continue;
                int ri = Rng.Next(stable.Count);
                var returned = stable[ri];
                stable.RemoveAt(ri);
                if (!_hands.ContainsKey(s)) _hands[s] = new List<string>();
                _hands[s].Add(returned);
            }
            try
            {
                int cx = ScreenW / 2, cy = ScreenH / 2;
                _flashes.Add(new ScreenFlash((180, 255, 220), 50, 0.35f));
                _textPops.Add(new TextPopAnim("🌪️ GLITTER TORNADO!", cx, cy - 30, (120, 255, 200), fontSize: 28));
                for (int sp = 0; sp < 8; sp++)
                {
                    float sx = cx + (float)(Rng.NextDouble() * 300 - 150);
                    float sy = cy + (float)(Rng.NextDouble() * 200 - 100);
                    _particles.EmitSparkle((int)sx, (int)sy, (150, 255, 220), 6);
                }
                _pulseRings.Add(new PulseRing(cx, cy, (120, 255, 180), maxRadius: Math.Min(ScreenW, ScreenH) / 3, duration: 0.6f));
            }
            catch { }
            return;
        }

        if (typ == "MYSTICAL_VORTEX")
        {
            foreach (var s in ActivePlayers)
            {
                var h = _hands.GetValueOrDefault(s);
                if (h != null && h.Count > 0)
                {
                    int ri = Rng.Next(h.Count);
                    _discardPile.Add(h[ri]);
                    h.RemoveAt(ri);
                }
            }
            _drawPile.AddRange(_discardPile);
            _discardPile.Clear();
            ShuffleList(_drawPile);
            try
            {
                int cx = ScreenW / 2, cy = ScreenH / 2;
                _flashes.Add(new ScreenFlash((80, 60, 180), 70, 0.4f));
                _textPops.Add(new TextPopAnim("🌀 MYSTICAL VORTEX!", cx, cy - 30, (160, 140, 255), fontSize: 28));
                _pulseRings.Add(new PulseRing(cx, cy, (130, 100, 255), maxRadius: Math.Min(ScreenW, ScreenH) / 4, duration: 0.7f));
                _particles.EmitSparkle(cx, cy, (160, 120, 255), 35);
            }
            catch { }
            return;
        }

        if (typ == "RESET_BUTTON")
        {
            foreach (var s in ActivePlayers)
            {
                var h = _hands.GetValueOrDefault(s);
                if (h != null)
                {
                    _drawPile.AddRange(h);
                    h.Clear();
                }
            }
            ShuffleList(_drawPile);
            foreach (var s in ActivePlayers)
                DrawToHand(s, 5);
            try
            {
                int cx = ScreenW / 2, cy = ScreenH / 2;
                _flashes.Add(new ScreenFlash((255, 255, 255), 90, 0.5f));
                _textPops.Add(new TextPopAnim("🔄 RESET!", cx, cy - 30, (255, 255, 200), fontSize: 32));
                _pulseRings.Add(new PulseRing(cx, cy, (255, 240, 100), maxRadius: Math.Min(ScreenW, ScreenH) / 3, duration: 0.6f));
                _particles.EmitSparkle(cx, cy, (255, 255, 180), 40);
            }
            catch { }
            return;
        }

        if (typ == "SHAKE_UP")
        {
            var allCards = new List<string>();
            foreach (var s in ActivePlayers)
            {
                var h = _hands.GetValueOrDefault(s);
                if (h != null) { allCards.AddRange(h); h.Clear(); }
            }
            ShuffleList(allCards);
            int idx2 = 0;
            while (idx2 < allCards.Count)
            {
                foreach (var s in ActivePlayers)
                {
                    if (idx2 >= allCards.Count) break;
                    if (!_hands.ContainsKey(s)) _hands[s] = new List<string>();
                    _hands[s].Add(allCards[idx2++]);
                }
            }
            try
            {
                int cx = ScreenW / 2, cy = ScreenH / 2;
                _flashes.Add(new ScreenFlash((255, 200, 100), 55, 0.35f));
                _textPops.Add(new TextPopAnim("🃏 SHAKE UP!", cx, cy - 30, (255, 220, 130), fontSize: 28));
                _particles.EmitSparkle(cx, cy, (255, 200, 100), 25);
            }
            catch { }
            return;
        }

        if (typ == "TARGETED_DESTRUCTION")
        {
            int t = TargetInt(target, "target_player", -1);
            int idx = TargetInt(target, "target_index", -1);
            if (!ActivePlayers.Contains(t)) return;
            if (t != actor && _protectedTurns.GetValueOrDefault(t, 0) > 0) return;
            var src = _stables.GetValueOrDefault(t);
            if (src == null || idx < 0 || idx >= src.Count) return;
            var ck = _cards.GetValueOrDefault(src[idx])?.Kind ?? "";
            if (ck is not ("upgrade" or "downgrade")) return;
            if (TryDestroyStableCard(t, idx))
                try { EmitDestroyFx(t); } catch { }
            return;
        }

        if (typ == "TWO_FOR_ONE")
        {
            // Sacrifice a random card from actor's stable
            var mine = _stables.GetValueOrDefault(actor);
            if (mine != null && mine.Count > 0)
            {
                int ri = Rng.Next(mine.Count);
                TrySacrificeStableCard(actor, ri);
            }
            // Destroy up to 2 from target's stable
            int t = TargetInt(target, "target_player", -1);
            if (!ActivePlayers.Contains(t)) return;
            var their = _stables.GetValueOrDefault(t);
            if (their == null) return;
            for (int d = 0; d < 2 && their.Count > 0; d++)
            {
                int ri = Rng.Next(their.Count);
                TryDestroyStableCard(t, ri);
            }
            try { EmitDestroyFx(t); } catch { }
            return;
        }

        if (typ == "SHRINK_RAY")
        {
            int t = TargetInt(target, "target_player", -1);
            if (!ActivePlayers.Contains(t)) return;
            var stable = _stables.GetValueOrDefault(t);
            if (stable == null) return;
            // Replace all non-baby unicorns with baby unicorns
            int replaced = 0;
            for (int i = stable.Count - 1; i >= 0; i--)
            {
                var ck = _cards.GetValueOrDefault(stable[i])?.Kind ?? "";
                if (ck == "unicorn")
                {
                    _discardPile.Add(stable[i]);
                    stable[i] = "baby_unicorn";
                    replaced++;
                }
            }
            if (replaced > 0)
            {
                try
                {
                    int cx = ScreenW / 2, cy = ScreenH / 2;
                    _flashes.Add(new ScreenFlash((160, 100, 255), 50, 0.35f));
                    _textPops.Add(new TextPopAnim($"🔫 SHRINK! ({replaced} unicorns)", cx, cy - 30, (180, 140, 255), fontSize: 24));
                    _particles.EmitSparkle(cx, cy, (200, 160, 255), 20);
                }
                catch { }
            }
            return;
        }

        if (typ == "TRADE_HANDS")
        {
            int t = TargetInt(target, "target_player", -1);
            if (!ActivePlayers.Contains(t)) return;
            var myHand = _hands.GetValueOrDefault(actor, new List<string>());
            var theirHand = _hands.GetValueOrDefault(t, new List<string>());
            _hands[actor] = theirHand;
            _hands[t] = myHand;
            try
            {
                int cx = ScreenW / 2, cy = ScreenH / 2;
                _flashes.Add(new ScreenFlash((200, 160, 255), 45, 0.3f));
                _textPops.Add(new TextPopAnim("🤝 TRADE HANDS!", cx, cy - 30, (220, 190, 255), fontSize: 26));
                _pulseRings.Add(new PulseRing(cx, cy, (190, 160, 255), maxRadius: Math.Min(ScreenW, ScreenH) / 5, duration: 0.5f));
            }
            catch { }
            return;
        }
    }

    private static int TargetInt(Dictionary<string, object?>? target, string key, int fallback)
    {
        if (target == null) return fallback;
        if (!target.TryGetValue(key, out var v)) return fallback;
        if (v is int i) return i;
        if (v is long l) return (int)l;
        return fallback;
    }

    // ─── Animation FX helpers ──────────────────────────────────

    private void EmitDestroyFx(int targetSeat)
    {
        var pos = _zoneCenters.GetValueOrDefault(targetSeat, (ScreenW / 2, ScreenH / 2));
        _flashes.Add(new ScreenFlash((220, 50, 50), 60, 0.3f));
        _particles.EmitSparkle(pos.Item1, pos.Item2, (255, 80, 60), 20);
        _textPops.Add(new TextPopAnim("💥 DESTROYED!", ScreenW / 2, ScreenH / 2 - 30, (255, 100, 80), fontSize: 26));
        _screenShakeTimer = 0.2f;
        var eb = new ExplosionBurst(pos.Item1, pos.Item2, 140, 0.9f);
        eb.CoreColor = (255, 200, 60);
        eb.RingColor = (255, 80, 60);
        _explosions.Add(eb);
        NoteEvent($"Card destroyed in {PlayerName(targetSeat)}'s stable!");
    }

    private void EmitStealFx(int thief, int victim)
    {
        var from = _zoneCenters.GetValueOrDefault(victim, (ScreenW / 2, ScreenH / 2));
        var to = _zoneCenters.GetValueOrDefault(thief, (ScreenW / 2, ScreenH / 2));
        _flashes.Add(new ScreenFlash((200, 100, 255), 40, 0.25f));
        _particles.EmitSparkle(from.Item1, from.Item2, (220, 160, 255), 12);
        _particles.EmitSparkle(to.Item1, to.Item2, (180, 255, 180), 12);
        _textPops.Add(new TextPopAnim("🦄 STOLEN!", ScreenW / 2, ScreenH / 2 - 30, (220, 180, 255), fontSize: 26));
        _cardFlips.Add(new CardFlyAnim((from.Item1, from.Item2), (to.Item1, to.Item2), color: SeatColors[thief % SeatColors.Length]));
        _screenShakeTimer = 0.15f;
        NoteEvent($"{PlayerName(thief)} stole from {PlayerName(victim)}!");
    }

    // ─── Card summary for snapshot ─────────────────────────────

    private Dictionary<string, object?> CardSummary(string cid)
    {
        var c = _cards.GetValueOrDefault(cid);
        if (c == null)
            return new Dictionary<string, object?>
            {
                ["id"] = cid, ["name"] = cid, ["kind"] = "", ["emoji"] = "", ["color"] = "#a0a0a0",
            };
        return new Dictionary<string, object?>
        {
            ["id"] = c.Id, ["name"] = c.Name, ["kind"] = c.Kind, ["emoji"] = c.Emoji, ["color"] = c.Color, ["desc"] = c.Desc,
        };
    }

    // ─── Snapshot ──────────────────────────────────────────────

    public override Dictionary<string, object?> GetSnapshot(int playerIdx)
    {
        int seat = playerIdx;
        var myHand = _hands.GetValueOrDefault(seat, new List<string>()).ToList();
        bool isTurn = seat == CurrentTurnSeat && State == "playing";

        bool IsPlayable(string cid)
        {
            var c = _cards.GetValueOrDefault(cid);
            if (c == null) return false;
            if (_winner != null) return false;
            if (_reactionActive)
            {
                if (!_reactionPending.Contains(seat)) return false;
                return c.Kind is "neigh" or "super_neigh";
            }
            if (_prompt != null) return false;
            if (c.Kind == "instant") return true;
            if (c.Kind is "neigh" or "super_neigh") return false;
            if (!isTurn || _turnPhase != "action" || _actionTaken) return false;
            // Broken Stable: cannot play upgrade cards
            if (c.Kind == "upgrade" && HasBrokenStable(seat)) return false;
            // Queen Bee: basic unicorns can't enter other players' stables
            if (c.Kind == "unicorn" && c.Id.StartsWith("unicorn_basic"))
            {
                int qbOwner = QueenBeeOwner();
                if (qbOwner >= 0 && qbOwner != seat) return false;
            }
            return true;
        }

        var stablesSnap = new Dictionary<string, object?>();
        foreach (var s in ActivePlayers)
        {
            var stable = _stables.GetValueOrDefault(s, new List<string>());
            stablesSnap[s.ToString()] = stable.Select(cid => CardSummary(cid)).ToList();
        }

        Dictionary<string, object?>? reaction = null;
        if (_reactionActive)
        {
            reaction = new Dictionary<string, object?>
            {
                ["actor"] = _reactionActor,
                ["card"] = CardSummary(_reactionCardId ?? ""),
                ["awaiting_seats"] = _reactionPending.ToList(),
                ["stack"] = _reactionStack.Select(cid => CardSummary(cid)).ToList(),
            };
        }

        Dictionary<string, object?>? promptSnap = null;
        if (_prompt != null && !PromptKindIs("PLAY"))
            promptSnap = new Dictionary<string, object?>(_prompt);

        var yourHand = myHand.Select((cid, i) =>
        {
            var cs = CardSummary(cid);
            cs["idx"] = i;
            cs["playable"] = IsPlayable(cid);
            return cs;
        }).ToList();

        var protSnap = new Dictionary<string, object?>();
        foreach (var s in ActivePlayers)
            protSnap[s.ToString()] = _protectedTurns.GetValueOrDefault(s, 0);

        var handCounts = new Dictionary<string, object?>();
        foreach (var s in ActivePlayers)
            handCounts[s.ToString()] = _hands.GetValueOrDefault(s)?.Count ?? 0;

        // Nanny Cam: reveal hands of players who have nanny_cam in their stable (to other players)
        var revealedHands = new Dictionary<string, object?>();
        foreach (var s in ActivePlayers)
        {
            if (s == seat) continue; // don't include your own hand again
            var stable = _stables.GetValueOrDefault(s, new List<string>());
            bool hasNannyCam = stable.Any(cid => cid.StartsWith("nanny_cam"));
            if (hasNannyCam)
            {
                var hand = _hands.GetValueOrDefault(s, new List<string>());
                revealedHands[s.ToString()] = hand.Select(cid => CardSummary(cid)).ToList();
            }
        }

        var snap = new Dictionary<string, object?>
        {
            ["state"] = State,
            ["active_players"] = ActivePlayers.ToList(),
            ["current_turn_seat"] = CurrentTurnSeat,
            ["turn_phase"] = _turnPhase,
            ["action_taken"] = _actionTaken,
            ["deck_count"] = _drawPile.Count,
            ["discard_count"] = _discardPile.Count,
            ["goal_unicorns"] = _goalUnicorns,
            ["winner"] = _winner,
            ["your_hand"] = yourHand,
            ["stables"] = stablesSnap,
            ["protected_turns"] = protSnap,
            ["hand_counts"] = handCounts,
            ["revealed_hands"] = revealedHands,
            ["reaction"] = reaction,
            ["prompt"] = promptSnap,
            ["last_event"] = !string.IsNullOrEmpty(_lastEvent) && _lastEventAge < 6.0 ? _lastEvent : null,
        };

        return new Dictionary<string, object?> { ["unstable_unicorns"] = snap };
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

    // ─── Buttons ───────────────────────────────────────────────

    private void RebuildButtons()
    {
        _buttons.Clear();
        foreach (var s in ActivePlayers)
            _buttons[s] = new Dictionary<string, (string, bool)>();

        if (_winner != null) return;

        // Reaction-only buttons — simultaneous for all pending players
        if (_reactionActive)
        {
            foreach (var rs in _reactionPending)
            {
                if (!ActivePlayers.Contains(rs)) continue;
                var rHand = _hands.GetValueOrDefault(rs, new List<string>());
                bool canNeigh = rHand.Any(cid => (_cards.GetValueOrDefault(cid)?.Kind ?? "") == "neigh");
                bool canSuper = rHand.Any(cid => (_cards.GetValueOrDefault(cid)?.Kind ?? "") == "super_neigh");
                _buttons[rs]["uu_react_neigh"] = ("Neigh", canNeigh);
                _buttons[rs]["uu_react_super"] = ("Super Neigh", canSuper);
                _buttons[rs]["uu_react_pass"] = ("Pass", true);
            }
            return;
        }

        // Prompt targeting buttons
        if (_prompt != null && !PromptKindIs("PLAY"))
        {
            int actor = PromptInt("actor", -1);
            if (ActivePlayers.Contains(actor))
            {
                var kind = PromptString("kind");
                var step = PromptString("step");

                if (step == "pick_player")
                {
                    // Effects that must NOT target self
                    bool noSelfTarget = kind is "STEAL_UNICORN" or "SWAP_UNICORN"
                        or "FORCE_DISCARD_ON_ENTER" or "BLATANT_THIEVERY"
                        or "TWO_FOR_ONE" or "TRADE_HANDS" or "DOWNGRADE_TARGET"
                        or "STEAL_ON_ENTER" or "SHRINK_RAY";
                    int targetCount = 0;
                    foreach (var t in ActivePlayers)
                    {
                        if (noSelfTarget && t == actor) continue;
                        _buttons[actor][$"uu_target_player:{t}"] = ($"Target: {PlayerName(t)}", true);
                        targetCount++;
                    }
                    // Always allow cancel during targeting to prevent soft-lock
                    _buttons[actor]["uu_cancel_prompt"] = ("Cancel", true);
                }
                else if (step == "pick_card")
                {
                    int t = PromptInt("target_player", -1);
                    var stable = _stables.GetValueOrDefault(t, new List<string>()).ToList();
                    List<int> eligible;
                    if (kind is "STEAL_UNICORN" or "SWAP_UNICORN" or "DESTROY_UNICORN_ON_ENTER" or "STEAL_ON_ENTER"
                        or "RETURN_UNICORN_ON_ENTER")
                    {
                        eligible = new List<int>();
                        for (int i = 0; i < stable.Count; i++)
                        {
                            var ck = _cards.GetValueOrDefault(stable[i])?.Kind ?? "";
                            if (ck is "baby_unicorn" or "unicorn") eligible.Add(i);
                        }
                    }
                    else if (kind is "DESTROY_UD_ON_ENTER" or "TARGETED_DESTRUCTION")
                    {
                        eligible = new List<int>();
                        for (int i = 0; i < stable.Count; i++)
                        {
                            var ck = _cards.GetValueOrDefault(stable[i])?.Kind ?? "";
                            if (ck is "upgrade" or "downgrade") eligible.Add(i);
                        }
                    }
                    else
                    {
                        eligible = Enumerable.Range(0, stable.Count).ToList();
                    }

                    foreach (var i in eligible)
                    {
                        var label = _cards.GetValueOrDefault(stable[i])?.Name ?? stable[i];
                        _buttons[actor][$"uu_target_card:{t}:{i}"] = ($"Pick: {label}", true);
                    }

                    // If no eligible cards, show a Cancel button to prevent soft-lock
                    if (eligible.Count == 0)
                    {
                        _buttons[actor]["uu_cancel_prompt"] = ("Cancel (no valid targets)", true);
                    }
                }
            }
            return;
        }

        // Normal turn buttons
        var turn = CurrentTurnSeat;
        if (turn is not int turnSeat || !ActivePlayers.Contains(turnSeat)) return;

        // Discard phase
        if (_turnPhase == "discard")
        {
            var hand = _hands.GetValueOrDefault(turnSeat, new List<string>());
            for (int i = 0; i < hand.Count; i++)
            {
                var label = _cards.GetValueOrDefault(hand[i])?.Name ?? hand[i];
                _buttons[turnSeat][$"uu_discard:{i}"] = ($"Discard: {label}", true);
            }
            return;
        }

        _buttons[turnSeat]["uu_draw_action"] = ("Draw (action)", _turnPhase == "action" && !_actionTaken);
        _buttons[turnSeat]["uu_end_turn"] = ("End Turn", _turnPhase == "action" && _actionTaken);

        // Hand play buttons
        var turnHand = _hands.GetValueOrDefault(turnSeat, new List<string>()).ToList();
        for (int i = 0; i < turnHand.Count; i++)
        {
            var c = _cards.GetValueOrDefault(turnHand[i]);
            if (c == null) continue;
            if (c.Kind is "neigh" or "super_neigh") continue;
            if (c.Kind != "instant" && _actionTaken) continue;
            // Broken Stable: cannot play upgrade cards
            if (c.Kind == "upgrade" && HasBrokenStable(turnSeat)) continue;
            // Queen Bee: basic unicorns blocked for non-owners
            if (c.Kind == "unicorn" && c.Id.StartsWith("unicorn_basic"))
            {
                int qbOwner = QueenBeeOwner();
                if (qbOwner >= 0 && qbOwner != turnSeat) continue;
            }
            _buttons[turnSeat][$"uu_play:{i}"] = ($"Play: {c.Name}", true);
        }
    }

    // ─── Event tracking ──────────────────────────────────────

    private void NoteEvent(string msg)
    {
        _lastEvent = msg;
        _lastEventAge = 0;
    }

    // ─── Update / Draw ─────────────────────────────────────────

    public override void Update(double dt)
    {
        float d = Math.Clamp((float)dt, 0f, 0.2f);

        _particles.Update(d);
        for (int i = _cardFlips.Count - 1; i >= 0; i--) { _cardFlips[i].Update(d); if (_cardFlips[i].Done) _cardFlips.RemoveAt(i); }
        for (int i = _showcases.Count - 1; i >= 0; i--) { _showcases[i].Update(d, _particles); if (_showcases[i].Done) _showcases.RemoveAt(i); }
        for (int i = _textPops.Count - 1; i >= 0; i--) { _textPops[i].Update(d); if (_textPops[i].Done) _textPops.RemoveAt(i); }
        for (int i = _pulseRings.Count - 1; i >= 0; i--) { _pulseRings[i].Update(d); if (_pulseRings[i].Done) _pulseRings.RemoveAt(i); }
        for (int i = _flashes.Count - 1; i >= 0; i--) { _flashes[i].Update(d); if (_flashes[i].Done) _flashes.RemoveAt(i); }
        for (int i = _explosions.Count - 1; i >= 0; i--) { _explosions[i].Update(d); if (_explosions[i].Done) _explosions.RemoveAt(i); }

        _ambient.Update(d, ScreenW, ScreenH);
        _lightBeams.Update(d, ScreenW, ScreenH);
        _vignette.Update(d);
        _starfield.Update(d);
        _floatingIcons.Update(d, ScreenW, ScreenH);
        _waveBand.Update(d);
        _heatShimmer.Update(d);

        // Premium systems
        _spotlight.Update(d);
        _fireEdge.Update(d);
        _cardBreath.Update(d);

        // Last event age
        _lastEventAge += d;

        // Screen shake decay
        if (_screenShakeTimer > 0)
        {
            _screenShakeTimer -= d;
            float intensity = Math.Clamp(_screenShakeTimer * 18f, 0f, 14f);
            _screenShakeX = (float)(Rng.NextDouble() * 2 - 1) * intensity;
            _screenShakeY = (float)(Rng.NextDouble() * 2 - 1) * intensity;
        }
        else
        {
            _screenShakeX = 0; _screenShakeY = 0;
        }

        // Ambient sparkle particles — from edges
        if (State == "playing" && _winner == null)
        {
            _sparkleTimer -= d;
            if (_sparkleTimer <= 0f)
            {
                _sparkleTimer = 0.12f;
                // Floating sparkles from bottom edge
                float sx = (float)(Rng.NextDouble() * ScreenW);
                _particles.Emit(sx, ScreenH + 5, (200, 140, 255), count: 1,
                    speed: 18f, gravity: -25f, life: 3.5f, radius: 1.2f);
                // Occasional side sparkle
                if (Rng.NextDouble() < 0.15)
                {
                    bool leftSide = Rng.NextDouble() < 0.5;
                    float sparkX = leftSide ? -5 : ScreenW + 5;
                    float sparkY = (float)(Rng.NextDouble() * ScreenH);
                    _particles.Emit(sparkX, sparkY, (180, 120, 255), count: 1,
                        speed: 12f, gravity: -18f, life: 3f, radius: 1.5f);
                }
            }
        }

        // Detect turn change
        var currTurn = CurrentTurnSeat;
        if (State == "playing" && currTurn is int ct && _animPrevTurn is int pt && ct != pt)
        {
            var center = _zoneCenters.GetValueOrDefault(ct, (ScreenW / 2, ScreenH / 2));
            var col = SeatColors[ct % SeatColors.Length];
            _pulseRings.Add(new PulseRing(center.Item1, center.Item2, col,
                maxRadius: Math.Min(ScreenW, ScreenH) / 5, duration: 0.8f));
            _particles.EmitSparkle(center.Item1, center.Item2, col, 18);
            _flashes.Add(new ScreenFlash(col, 35, 0.25f));
        }
        _animPrevTurn = currTurn;

        // Detect reaction window opening
        if (_reactionActive && !_animPrevReaction)
        {
            int cx = ScreenW / 2, cy = ScreenH / 2;
            _flashes.Add(new ScreenFlash((220, 30, 30), 90, 0.4f));
            _textPops.Add(new TextPopAnim("NEIGH? \ud83d\udeab", cx, cy + 55,
                (255, 90, 80), fontSize: 44, duration: 1.8f));
            _screenShakeTimer = 0.25f;
        }
        _animPrevReaction = _reactionActive;

        // Detect winner
        if (_winner != null && _animPrevWinner == null)
        {
            int cx = ScreenW / 2, cy = ScreenH / 2;
            _flashes.Add(new ScreenFlash((255, 255, 180), 140, 0.65f));
            for (int i = 0; i < 10; i++)
                _particles.EmitFirework(Rng.Next(ScreenW * 10 / 100, ScreenW * 90 / 100),
                    Rng.Next(ScreenH * 10 / 100, ScreenH * 90 / 100), AnimPalette.Rainbow);
            _animFwTimer = 6.0;
        }
        _animPrevWinner = _winner;

        // Ongoing winner fireworks
        if (_winner != null)
        {
            _animFwTimer -= d;
            if (_animFwTimer > 0 && (int)(_animFwTimer * 3) % 2 == 0)
            {
                _particles.EmitFirework(
                    Rng.Next(ScreenW * 5 / 100, ScreenW * 95 / 100),
                    Rng.Next(ScreenH * 5 / 100, ScreenH * 95 / 100), AnimPalette.Rainbow);
            }
        }
    }

    public override void Draw(Renderer r, int width, int height, double dt)
    {
        if (State == "player_select")
        {
            // ═══════════════════════════════════════════════════════════
            //  LOBBY — premium themed lobby with QR code
            // ═══════════════════════════════════════════════════════════
            CardRendering.DrawGameBackground(r, width, height, "unstable_unicorns");
            _ambient.Draw(r);
            _lightBeams.Draw(r, width, height);
            _starfield.Draw(r);
            _floatingIcons.Draw(r);

            // Title
            RainbowTitle.Draw(r, "UNSTABLE UNICORNS", width);

            // Subtitle
            r.DrawText("SELECT PLAYERS & SCAN TO JOIN", width / 2, 52, 13,
                (200, 140, 255), anchorX: "center", anchorY: "center", bold: true);

            // Player selection circles
            SelectionUI.Draw(r);

            // QR Code panel
            int qrSize = Math.Clamp(Math.Min(width, height) * 18 / 100, 100, 200);
            int qrX = width - qrSize / 2 - 60;
            int qrY = height / 2;
            QRCodeRenderer.DrawQRPanel(r, qrX, qrY, qrSize,
                title: "📱 SCAN TO JOIN",
                accentColor: (180, 80, 255));

            // Ambient particles for lobby
            _particles.Draw(r);
            _waveBand.Draw(r, width, height);
            _vignette.Draw(r, width, height);
            return;
        }

        // ═══════════════════════════════════════════════════════════════
        //  IN-GAME — EK-quality production renderer
        // ═══════════════════════════════════════════════════════════════

        int shX = (int)_screenShakeX, shY = (int)_screenShakeY;

        CardRendering.DrawGameBackground(r, width, height, "unstable_unicorns");
        _ambient.Draw(r);
        _lightBeams.Draw(r, width, height);
        _starfield.Draw(r);
        _floatingIcons.Draw(r);

        // Sparkle/rainbow edge effect  
        _fireEdge.Draw(r, width, height);

        int cx = width / 2 + shX, cy = height / 2 + shY;

        // ─── Title ─────────────────────────────────────────────
        RainbowTitle.Draw(r, "UNSTABLE UNICORNS", width);

        // ─── HUD Bar — premium frosted dark-glass panel ──────
        var turn = CurrentTurnSeat;
        int hudH = 40;
        int hudY = 48;
        int hudW = Math.Min(width - 40, 820);
        int hudX = (width - hudW) / 2;

        // HUD multi-layer shadow
        r.DrawRect((0, 0, 0), (hudX + 5, hudY + 5, hudW, hudH), alpha: 60);
        r.DrawRect((0, 0, 0), (hudX + 3, hudY + 3, hudW, hudH), alpha: 90);

        // HUD background — dark glass
        r.DrawRect((16, 10, 28), (hudX, hudY, hudW, hudH), alpha: 230);
        r.DrawRect((24, 16, 36), (hudX + 2, hudY + 2, hudW - 4, hudH / 3), alpha: 30);

        // Accent top and bottom lines — purple theme
        r.DrawRect((180, 80, 255), (hudX, hudY, hudW, 3), alpha: 150);
        r.DrawRect((200, 100, 255), (hudX, hudY + 3, hudW, 1), alpha: 40);
        r.DrawRect((0, 0, 0), (hudX, hudY + hudH - 2, hudW, 2), alpha: 60);

        // Border with highlights
        r.DrawRect((80, 60, 120), (hudX, hudY, hudW, hudH), width: 1, alpha: 60);
        r.DrawRect((255, 255, 255), (hudX + 1, hudY + 4, hudW - 2, 1), alpha: 8);

        // HUD content
        int hudCy = hudY + hudH / 2;
        int seg = hudW / 4;

        // Segment separators
        for (int sep = 1; sep < 4; sep++)
        {
            int sx = hudX + sep * seg;
            r.DrawLine((80, 60, 100), (sx, hudY + 6), (sx, hudY + hudH - 6), width: 1, alpha: 30);
        }

        // ── Deck count with icon ──
        string deckIcon = _drawPile.Count <= 3 ? "⚡" : "🃏";
        var deckCol = _drawPile.Count <= 3 ? (255, 80, 40) : _drawPile.Count <= 8 ? (255, 180, 40) : (200, 200, 210);
        if (_drawPile.Count <= 3)
            r.DrawCircle((255, 40, 0), (hudX + seg / 2 - 40, hudCy), 10, alpha: 12);
        r.DrawText($"{deckIcon} Deck: {_drawPile.Count}", hudX + seg / 2 + 1, hudCy + 1, 13, (0, 0, 0),
            anchorX: "center", anchorY: "center", bold: true, alpha: 60);
        r.DrawText($"{deckIcon} Deck: {_drawPile.Count}", hudX + seg / 2, hudCy, 13, deckCol,
            anchorX: "center", anchorY: "center", bold: true);

        // ── Discard count ──
        r.DrawText($"Discard: {_discardPile.Count}", hudX + seg + seg / 2 + 1, hudCy + 1, 13, (0, 0, 0),
            anchorX: "center", anchorY: "center", alpha: 50);
        r.DrawText($"Discard: {_discardPile.Count}", hudX + seg + seg / 2, hudCy, 13, (180, 170, 190),
            anchorX: "center", anchorY: "center");

        // ── Turn indicator with player color pip ──
        if (turn is int tt)
        {
            var tcol = GameConfig.PlayerColors[tt % GameConfig.PlayerColors.Length];
            r.DrawCircle(tcol, (hudX + 2 * seg + 12, hudCy), 6, alpha: 220);
            r.DrawCircle(tcol, (hudX + 2 * seg + 12, hudCy), 10, alpha: 14);
            r.DrawCircle((255, 255, 255), (hudX + 2 * seg + 11, hudCy - 1), 2, alpha: 30);
            r.DrawText($"{PlayerName(tt)}'s Turn", hudX + 2 * seg + 22 + 1, hudCy + 1, 13, (0, 0, 0),
                anchorX: "left", anchorY: "center", bold: true, alpha: 50);
            r.DrawText($"{PlayerName(tt)}'s Turn", hudX + 2 * seg + 22, hudCy, 13, (255, 220, 100),
                anchorX: "left", anchorY: "center", bold: true);
        }
        else
        {
            r.DrawText("Turn: —", hudX + 2 * seg + seg / 2, hudCy, 13, (140, 140, 150),
                anchorX: "center", anchorY: "center");
        }

        // ── Phase / goal info ──
        string phaseStr = _turnPhase switch
        {
            "begin" => "🌅 Begin",
            "action" => _actionTaken ? "✅ Done" : "🎯 Action",
            "discard" => "♻ Discard",
            "reaction" => "🚫 Neigh!",
            "prompt" => "🎯 Target",
            _ => "",
        };
        r.DrawText($"🦄 Goal: {_goalUnicorns}  {phaseStr}", hudX + 3 * seg + seg / 2 + 1, hudCy + 1, 12, (0, 0, 0),
            anchorX: "center", anchorY: "center", alpha: 50);
        r.DrawText($"🦄 Goal: {_goalUnicorns}  {phaseStr}", hudX + 3 * seg + seg / 2, hudCy, 12, (200, 180, 230),
            anchorX: "center", anchorY: "center");

        // ─── Neigh window overlay — premium red banner ──────────
        if (_reactionActive)
        {
            int nopeY = hudY + hudH + 8;
            int nopeW = Math.Min(420, width * 32 / 100);
            int nopeH = 38;
            int nopeX = cx - nopeW / 2;

            SoftShadow.Draw(r, nopeX + 3, nopeY + 4, nopeW, nopeH, layers: 4, maxAlpha: 90);
            BeveledRect.Draw(r, nopeX, nopeY, nopeW, nopeH, (60, 6, 6), bevelSize: 3);

            r.DrawRect((220, 40, 40), (nopeX, nopeY, nopeW, nopeH), width: 2, alpha: 220);
            r.DrawRect((255, 80, 80), (nopeX, nopeY, nopeW, 3), alpha: 200);
            r.DrawRect((255, 120, 80), (nopeX + 1, nopeY + 3, nopeW - 2, 1), alpha: 40);

            // Pulsing side danger indicators
            int pulseA = (int)(40 + 30 * Math.Sin(dt * 6));
            r.DrawCircle((255, 40, 20), (nopeX + 10, nopeY + nopeH / 2), 4, alpha: pulseA);
            r.DrawCircle((255, 40, 20), (nopeX + nopeW - 10, nopeY + nopeH / 2), 4, alpha: pulseA);

            string neighLabel = _reactionStack.Count > 0
                ? $"🚫 NEIGH WINDOW ({_reactionStack.Count} played)"
                : "🚫 NEIGH WINDOW — react now!";
            string waitNames = _reactionPending.Count > 0
                ? string.Join(", ", _reactionPending.Select(s => PlayerName(s)))
                : "...";
            r.DrawText(neighLabel, cx + 1, nopeY + nopeH / 2 - 1, 12, (0, 0, 0),
                anchorX: "center", anchorY: "center", bold: true, alpha: 60);
            r.DrawText(neighLabel, cx, nopeY + nopeH / 2 - 2, 12, (255, 170, 160),
                anchorX: "center", anchorY: "center", bold: true);
        }

        // ─── Table center glow — slow breathing radial ──────────
        int minDim = Math.Min(width, height);
        float breathPhase = _cardBreath.Scale;
        float slowBreath = MathF.Sin(breathPhase * 4.2f);
        float breathScale = 1f + slowBreath * 0.08f;

        // Purple/pink circles
        int pr1 = (int)(minDim * 28 / 100 * breathScale);
        int pr2 = (int)(minDim * 22 / 100 * breathScale);
        int pr3 = (int)(minDim * 16 / 100 * breathScale);
        r.DrawCircle((50, 10, 80), (cx, cy), pr1, alpha: 7);
        r.DrawCircle((70, 20, 100), (cx, cy), pr2, alpha: 12);
        r.DrawCircle((100, 30, 140), (cx, cy), pr3, alpha: 14);
        r.DrawCircle((130, 50, 170), (cx, cy), (int)(minDim * 10 / 100 * breathScale), alpha: 10);

        // Warm inner circles — counter-phase
        float warmBreath = 1f + MathF.Sin(breathPhase * 4.2f + 1.8f) * 0.06f;
        int yr1 = (int)(minDim * 8 / 100 * warmBreath);
        int yr2 = (int)(minDim * 4 / 100 * warmBreath);
        r.DrawCircle((180, 80, 220), (cx, cy), yr1, alpha: 14);
        r.DrawCircle((220, 120, 255), (cx, cy), yr2, alpha: 8);
        r.DrawCircle((240, 160, 255), (cx, cy), (int)(minDim * 2 / 100 * warmBreath), alpha: 5);

        // Corner accents
        int cornerSize = Math.Min(60, minDim * 6 / 100);
        int cornerA = 10;
        r.DrawLine((160, 80, 200), (20, 20), (20 + cornerSize, 20), width: 1, alpha: cornerA);
        r.DrawLine((160, 80, 200), (20, 20), (20, 20 + cornerSize), width: 1, alpha: cornerA);
        r.DrawLine((160, 80, 200), (width - 20, 20), (width - 20 - cornerSize, 20), width: 1, alpha: cornerA);
        r.DrawLine((160, 80, 200), (width - 20, 20), (width - 20, 20 + cornerSize), width: 1, alpha: cornerA);
        r.DrawLine((160, 80, 200), (20, height - 20), (20 + cornerSize, height - 20), width: 1, alpha: cornerA);
        r.DrawLine((160, 80, 200), (20, height - 20), (20, height - 20 - cornerSize), width: 1, alpha: cornerA);
        r.DrawLine((160, 80, 200), (width - 20, height - 20), (width - 20 - cornerSize, height - 20), width: 1, alpha: cornerA);
        r.DrawLine((160, 80, 200), (width - 20, height - 20), (width - 20, height - 20 - cornerSize), width: 1, alpha: cornerA);

        // ─── Spotlight on active player ────────────────────────
        if (turn is int spotSeat && _zoneCenters.TryGetValue(spotSeat, out var spotPos))
        {
            _spotlight.DrawAt(r, spotPos.X, spotPos.Y, width, height, Math.Max(40, minDim * 10 / 100));
        }

        // ─── Player stable zones — premium beveled panels ─────
        var seats = ActivePlayers.ToList();
        if (seats.Count == 0) return;

        int cols = seats.Count > 2 ? 2 : 1;
        int rows = (seats.Count + cols - 1) / cols;
        int pad = 18;
        int top = 100; // more space for HUD
        int zoneW = (width - pad * (cols + 1)) / cols;
        int zoneH = (height - top - pad * (rows + 1)) / Math.Max(1, rows);

        int gap = 10;
        int cardsPerRow = 5;
        int cardW = Math.Max(92, Math.Min(130, (zoneW - 10 - gap * (cardsPerRow - 1)) / cardsPerRow));
        int cardH = (int)(cardW * 1.35);

        for (int si = 0; si < seats.Count; si++)
        {
            int s = seats[si];
            int row = si / cols;
            int col = si % cols;
            int zx = pad + col * (zoneW + pad);
            int zy = top + pad + row * (zoneH + pad);

            bool isTurn = s == CurrentTurnSeat;
            var pcol = GameConfig.PlayerColors[s % GameConfig.PlayerColors.Length];
            int uCount = UnicornCount(s);

            // Turn glow aura
            if (isTurn && _winner == null)
            {
                r.DrawRect((255, 180, 40), (zx - 10, zy - 10, zoneW + 20, zoneH + 20), width: 1, alpha: 12);
                r.DrawRect((255, 200, 60), (zx - 6, zy - 6, zoneW + 12, zoneH + 12), width: 2, alpha: 28);
                r.DrawRect((255, 220, 80), (zx - 3, zy - 3, zoneW + 6, zoneH + 6), width: 3, alpha: 50);
                // Corner glow spots
                r.DrawCircle((255, 200, 60), (zx - 4, zy - 4), 6, alpha: 20);
                r.DrawCircle((255, 200, 60), (zx + zoneW + 4, zy - 4), 6, alpha: 20);
                r.DrawCircle((255, 200, 60), (zx - 4, zy + zoneH + 4), 6, alpha: 20);
                r.DrawCircle((255, 200, 60), (zx + zoneW + 4, zy + zoneH + 4), 6, alpha: 20);
            }

            // Panel shadow
            SoftShadow.Draw(r, zx + 3, zy + 4, zoneW, zoneH, layers: 4, maxAlpha: 80);

            // Panel body — dark glass beveled
            var bg = isTurn ? (28, 18, 12) : (16, 12, 22);
            BeveledRect.Draw(r, zx, zy, zoneW, zoneH, bg, bevelSize: 3);

            // Subtle gradient inside
            r.DrawRect(pcol, (zx + 2, zy + 2, zoneW - 4, zoneH / 6), alpha: 8);
            r.DrawRect((0, 0, 0), (zx + 2, zy + zoneH - zoneH / 6, zoneW - 4, zoneH / 6), alpha: 12);

            // Top accent band — player color gradient
            r.DrawRect(pcol, (zx, zy, zoneW, 5), alpha: 160);
            r.DrawRect(pcol, (zx + 2, zy + 5, zoneW - 4, 2), alpha: 50);
            r.DrawRect(pcol, (zx + 4, zy + 7, zoneW - 8, 1), alpha: 20);

            // Border — layered with 3D depth
            var outline = isTurn ? (255, 180, 40) : (100, 80, 130);
            r.DrawRect(outline, (zx, zy, zoneW, zoneH), width: isTurn ? 2 : 1, alpha: 200);
            r.DrawRect((255, 255, 255), (zx + 1, zy + 1, zoneW - 2, 1), alpha: 15);
            r.DrawRect((0, 0, 0), (zx + 1, zy + zoneH - 2, zoneW - 2, 2), alpha: 35);
            r.DrawRect((0, 0, 0), (zx + zoneW - 2, zy + 1, 2, zoneH - 2), alpha: 25);

            // Near-win glow
            if (uCount >= _goalUnicorns - 1 && _winner == null)
            {
                int glowAlpha = uCount >= _goalUnicorns ? 45 : 25;
                var glowCol = uCount >= _goalUnicorns ? (255, 215, 0) : (255, 180, 80);
                r.DrawRect(glowCol, (zx + 2, zy + 2, zoneW - 4, zoneH - 4), alpha: glowAlpha);
                r.DrawRect(glowCol, (zx, zy, zoneW, zoneH), width: 3, alpha: 120);
            }

            // Protected shield indicator
            if (_protectedTurns.GetValueOrDefault(s, 0) > 0)
            {
                r.DrawRect((60, 180, 255), (zx, zy, zoneW, zoneH), width: 2, alpha: 80);
                r.DrawText("🛡️", zx + zoneW - 20, zy + 10, 14, (120, 200, 255), anchorX: "center", anchorY: "top");
            }

            // ── Player name pill — beveled and polished ──
            var nameCol = isTurn ? (255, 220, 80) : pcol;
            string pName = PlayerName(s);
            int pillW = Math.Max(72, pName.Length * 8 + 32);
            int pillH = 24;
            int pillX2 = zx + 6;
            int pillY2 = zy + 10;

            r.DrawRect((0, 0, 0), (pillX2 + 2, pillY2 + 2, pillW, pillH), alpha: 80);
            var namePillBg = isTurn ? (34, 24, 12) : (12, 10, 18);
            BeveledRect.Draw(r, pillX2, pillY2, pillW, pillH, namePillBg, bevelSize: 2);
            r.DrawRect(outline, (pillX2, pillY2, pillW, pillH), width: 1, alpha: 70);
            r.DrawRect((255, 255, 255), (pillX2 + 2, pillY2 + 1, pillW - 4, 1), alpha: 12);

            // Player color dot
            r.DrawCircle(pcol, (pillX2 + 11, pillY2 + pillH / 2), 5, alpha: 220);
            r.DrawCircle((255, 255, 255), (pillX2 + 10, pillY2 + pillH / 2 - 1), 2, alpha: 30);

            // Name text — shadowed
            string marker = isTurn ? " ★" : "";
            r.DrawText($"{pName}{marker}", pillX2 + 20 + 1, pillY2 + pillH / 2 + 1, 11, (0, 0, 0),
                anchorX: "left", anchorY: "center", bold: isTurn, alpha: 80);
            r.DrawText($"{pName}{marker}", pillX2 + 20, pillY2 + pillH / 2, 11, nameCol,
                anchorX: "left", anchorY: "center", bold: isTurn);

            // ── Unicorn count badge — embossed ──
            int badgeX = zx + zoneW - 55;
            int badgeY = zy + 12;
            int badgeW = 48;
            int badgeH = 20;
            r.DrawRect((0, 0, 0), (badgeX + 1, badgeY + 1, badgeW, badgeH), alpha: 60);
            r.DrawRect((20, 12, 30), (badgeX, badgeY, badgeW, badgeH), alpha: 200);
            r.DrawRect((140, 100, 180), (badgeX, badgeY, badgeW, badgeH), width: 1, alpha: 40);
            string countLabel = $"🦄 {uCount}/{_goalUnicorns}";
            r.DrawText(countLabel, badgeX + badgeW / 2 + 1, badgeY + badgeH / 2 + 1, 10, (0, 0, 0),
                anchorX: "center", anchorY: "center", bold: true, alpha: 60);
            var cntCol = uCount >= _goalUnicorns - 1 ? (255, 220, 80) : (200, 180, 220);
            r.DrawText(countLabel, badgeX + badgeW / 2, badgeY + badgeH / 2, 10, cntCol,
                anchorX: "center", anchorY: "center", bold: true);

            // Zone center for animations
            _zoneCenters[s] = (zx + zoneW / 2, zy + zoneH / 2);

            // Draw stable cards
            var stable = _stables.GetValueOrDefault(s, new List<string>());
            int cx2 = zx + 10;
            int cy2 = zy + 40;
            for (int ci = 0; ci < Math.Min(stable.Count, cardsPerRow * 2); ci++)
            {
                int x = cx2 + (ci % cardsPerRow) * (cardW + gap);
                int y = cy2 + (ci / cardsPerRow) * (cardH + gap);
                if (x + cardW > zx + zoneW - 6 || y + cardH > zy + zoneH - 6) break;
                DrawCardFace(r, (x, y, cardW, cardH), stable[ci]);
            }

            // Card fan hint at bottom (# in hand)
            int handCount = _hands.GetValueOrDefault(s)?.Count ?? 0;
            if (handCount > 0)
            {
                int fanCount = Math.Min(handCount, 8);
                int fanTotalW = Math.Min(zoneW - 20, fanCount * 9);
                int fanStartX = zx + zoneW / 2 - fanTotalW / 2;
                for (int fi = 0; fi < fanCount; fi++)
                {
                    int fx = fanStartX + fi * (fanTotalW / Math.Max(1, fanCount));
                    int fy = zy + zoneH - 16;
                    r.DrawRect((0, 0, 0), (fx + 1, fy + 1, 7, 10), alpha: 30);
                    r.DrawRect((180, 120, 220), (fx, fy, 7, 10), alpha: 40);
                    r.DrawRect((200, 140, 240), (fx, fy, 7, 1), alpha: 20);
                    r.DrawRect((140, 80, 180), (fx, fy, 7, 10), width: 1, alpha: 30);
                }
                r.DrawText($"{handCount} in hand", zx + zoneW / 2, zy + zoneH - 6, 8, (130, 120, 150),
                    anchorX: "center", anchorY: "center");
            }
        }

        // ─── Last event toast — premium notification ──────────
        if (!string.IsNullOrEmpty(_lastEvent) && _lastEventAge < 4.5 && _winner == null)
        {
            float eventFade = (float)(_lastEventAge < 0.3 ? _lastEventAge / 0.3
                : _lastEventAge > 3.5 ? 1.0 - (_lastEventAge - 3.5) / 1.0
                : 1.0);
            int eventAlpha = (int)(eventFade * 230);
            int ew = Math.Min(width - 40, Math.Max(240, _lastEvent.Length * 9 + 50));
            int eH = 30;
            int ex = cx - ew / 2;
            int ey = hudY + hudH + (_reactionActive ? 54 : 10);

            // Toast shadow
            r.DrawRect((0, 0, 0), (ex + 3, ey + 3, ew, eH), alpha: (int)(eventFade * 100));
            r.DrawRect((0, 0, 0), (ex + 1, ey + 1, ew, eH), alpha: (int)(eventFade * 60));

            // Toast background — dark glass with purple/amber accent
            r.DrawRect((12, 8, 18), (ex, ey, ew, eH), alpha: (int)(eventFade * 220));
            r.DrawRect((180, 120, 255), (ex, ey, ew, 2), alpha: (int)(eventFade * 160));
            r.DrawRect((200, 140, 255), (ex + 1, ey + 2, ew - 2, 1), alpha: (int)(eventFade * 30));
            r.DrawRect((60, 40, 80), (ex, ey, ew, eH), width: 1, alpha: (int)(eventFade * 50));

            // Icon glow
            r.DrawCircle((180, 120, 255), (ex + 16, ey + eH / 2), 8, alpha: (int)(eventFade * 12));

            // Text with shadow
            r.DrawText($"⚡ {_lastEvent}", cx + 1, ey + eH / 2 + 1, 11, (0, 0, 0),
                anchorX: "center", anchorY: "center", alpha: (int)(eventFade * 80));
            r.DrawText($"⚡ {_lastEvent}", cx, ey + eH / 2, 11, (230, 210, 240),
                anchorX: "center", anchorY: "center", alpha: eventAlpha);
        }

        // ─── Winner overlay — cinematic celebration ───────────
        if (_winner is int w)
        {
            // Full-screen dim with vignette
            r.DrawRect((0, 0, 0), (0, 0, width, height), alpha: 180);
            r.DrawRect((0, 0, 0), (0, 0, width, height / 6), alpha: 40);
            r.DrawRect((0, 0, 0), (0, height - height / 6, width, height / 6), alpha: 40);
            r.DrawRect((0, 0, 0), (0, 0, width / 6, height), alpha: 30);
            r.DrawRect((0, 0, 0), (width - width / 6, 0, width / 6, height), alpha: 30);

            // Purple/golden radial burst
            for (int i = 0; i < 16; i++)
            {
                double ang = i * Math.PI / 8;
                int rayLen = Math.Min(width, height) * 40 / 100;
                int rx = cx + (int)(Math.Cos(ang) * rayLen);
                int ry = cy + (int)(Math.Sin(ang) * rayLen);
                r.DrawLine((200, 140, 255), (cx, cy), (rx, ry), width: 2, alpha: 12);
            }
            r.DrawCircle((200, 140, 255), (cx, cy), Math.Min(width, height) * 35 / 100, alpha: 6);
            r.DrawCircle((220, 160, 255), (cx, cy), Math.Min(width, height) * 22 / 100, alpha: 8);

            int bw2 = Math.Min(660, width * 55 / 100), bh2 = 240;
            int bx2 = cx - bw2 / 2, by2 = cy - bh2 / 2;

            // Panel shadow — deep multi-layer
            r.DrawRect((0, 0, 0), (bx2 + 12, by2 + 12, bw2, bh2), alpha: 100);
            r.DrawRect((0, 0, 0), (bx2 + 8, by2 + 8, bw2, bh2), alpha: 60);
            r.DrawRect((0, 0, 0), (bx2 + 4, by2 + 4, bw2, bh2), alpha: 40);

            // Panel background — dark beveled
            BeveledRect.Draw(r, bx2, by2, bw2, bh2, (18, 10, 26), bevelSize: 4);

            // Purple/gold accent double border
            r.DrawRect((200, 140, 255), (bx2, by2, bw2, bh2), width: 3, alpha: 220);
            r.DrawRect((180, 120, 240), (bx2 + 5, by2 + 5, bw2 - 10, bh2 - 10), width: 1, alpha: 80);
            r.DrawRect((220, 180, 255), (bx2, by2, bw2, 4), alpha: 180);
            r.DrawRect((200, 160, 240), (bx2 + 1, by2 + 4, bw2 - 2, 2), alpha: 60);

            // Inner glow
            r.DrawCircle((200, 140, 255), (cx, cy), Math.Min(bw2, bh2) * 40 / 100, alpha: 10);
            r.DrawCircle((180, 120, 240), (cx, cy), Math.Min(bw2, bh2) * 25 / 100, alpha: 8);

            // Trophy emoji with halo
            r.DrawCircle((200, 140, 255), (cx, by2 + 55), 24, alpha: 14);
            r.DrawText("🏆", cx + 2, by2 + 55 + 2, 52, (0, 0, 0),
                anchorX: "center", anchorY: "center", alpha: 80);
            r.DrawText("🏆", cx, by2 + 55, 52, (255, 220, 80),
                anchorX: "center", anchorY: "center");

            // Winner name — large, embossed
            int nameFs = 38;
            r.DrawText(PlayerName(w), cx + 2, by2 + 112 + 2, nameFs, (0, 0, 0),
                anchorX: "center", anchorY: "center", bold: true, alpha: 140);
            r.DrawText(PlayerName(w), cx - 1, by2 + 112 - 1, nameFs, (255, 255, 240),
                anchorX: "center", anchorY: "center", bold: true, alpha: 80);
            r.DrawText(PlayerName(w), cx, by2 + 112, nameFs, (255, 245, 200),
                anchorX: "center", anchorY: "center", bold: true);

            // Subtitle
            r.DrawCircle((200, 140, 255), (cx, by2 + 152), 40, alpha: 6);
            r.DrawText("🦄 UNICORN CHAMPION! 🦄", cx + 1, by2 + 155 + 1, 20, (0, 0, 0),
                anchorX: "center", anchorY: "center", alpha: 80);
            r.DrawText("🦄 UNICORN CHAMPION! 🦄", cx, by2 + 155, 20, (220, 160, 255),
                anchorX: "center", anchorY: "center");

            // Decorative separators
            int lineW = bw2 * 60 / 100;
            r.DrawLine((200, 140, 255), (cx - lineW / 2, by2 + 88), (cx + lineW / 2, by2 + 88), width: 1, alpha: 40);
            r.DrawLine((200, 140, 255), (cx - lineW / 2, by2 + 175), (cx + lineW / 2, by2 + 175), width: 1, alpha: 35);

            // Corner ornaments
            for (int ci = 0; ci < 4; ci++)
            {
                int ccx = ci < 2 ? bx2 + 10 : bx2 + bw2 - 10;
                int ccy = ci % 2 == 0 ? by2 + 10 : by2 + bh2 - 10;
                r.DrawCircle((200, 140, 255), (ccx, ccy), 8, width: 1, alpha: 35);
                r.DrawCircle((220, 160, 255), (ccx, ccy), 4, alpha: 25);
            }

            // Bottom unicorn emoji row
            r.DrawText("🦄", cx - 40, by2 + bh2 - 22, 20, (220, 180, 255),
                anchorX: "center", anchorY: "center");
            r.DrawText("✨", cx, by2 + bh2 - 22, 20, (220, 180, 255),
                anchorX: "center", anchorY: "center");
            r.DrawText("🦄", cx + 40, by2 + bh2 - 22, 20, (220, 180, 255),
                anchorX: "center", anchorY: "center");
        }

        // ─── Animation overlay layers ─────────────────────────
        _particles.Draw(r);
        foreach (var ring in _pulseRings) ring.Draw(r);
        foreach (var fly in _cardFlips) fly.Draw(r);
        foreach (var sc in _showcases) sc.Draw(r);
        foreach (var flash in _flashes) flash.Draw(r, width, height);
        foreach (var pop in _textPops) pop.Draw(r);
        foreach (var expl in _explosions) expl.Draw(r);
        _waveBand.Draw(r, width, height);
        _heatShimmer.Draw(r, width, height);
        _vignette.Draw(r, width, height);

        // ─── Reaction full-screen dim ─────────────────────────
        if (_reactionActive)
        {
            r.DrawRect((0, 0, 0), (0, 0, width, height), alpha: 80);
        }
    }

    private void DrawCardFace(Renderer r, (int x, int y, int w, int h) rect, string cid)
    {
        var c = _cards.GetValueOrDefault(cid);
        if (c == null) return;
        var rgb = HexToRgb(c.Color, (140, 140, 140));
        CardRendering.DrawUUCard(r, rect, c.Emoji, c.Name, c.Kind, rgb, c.Desc);
    }
}
