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
    public Dictionary<string, JsonElement> Effect { get; }

    public UUCardDef(string id, string name, string kind, string emoji, string color, int count,
                     Dictionary<string, JsonElement> effect)
    {
        Id = id; Name = name; Kind = kind; Emoji = emoji; Color = color; Count = count;
        Effect = effect;
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

    // Reaction window (Neigh stack)
    private bool _reactionActive;
    private int? _reactionActor;
    private string? _reactionCardId;
    private Dictionary<string, object?>? _reactionTarget;
    private List<int> _reactionOrder = new();
    private int _reactionIdx;
    private List<string> _reactionStack = new();

    // Prompting (target selection etc.)
    private Dictionary<string, object?>? _prompt;

    // Win
    private int? _winner;
    private int _goalUnicorns = 7;

    // Buttons per player
    private readonly Dictionary<int, Dictionary<string, (string Text, bool Enabled)>> _buttons = new();

    // Animations
    private readonly ParticleSystem _particles = new();
    private readonly List<CardFlyAnim> _cardFlips = new();
    private readonly List<CardShowcaseAnim> _showcases = new();
    private readonly List<TextPopAnim> _textPops = new();
    private readonly List<PulseRing> _pulseRings = new();
    private readonly List<ScreenFlash> _flashes = new();
    private readonly Dictionary<int, (int X, int Y)> _zoneCenters = new();
    private int? _animPrevTurn;
    private bool _animPrevReaction;
    private int? _animPrevWinner;
    private double _animFwTimer;

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

                        _cards[cid] = new UUCardDef(cid, name, kind, emoji, color, count, effect);
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

        int drawN = 1 + Math.Max(0, DrawBonus(s));
        DrawToHand(s, drawN);
        _turnPhase = (_hands.GetValueOrDefault(s)?.Count ?? 0) > HandLimit(s) ? "discard" : "action";
    }

    private void EndTurn()
    {
        if (ActivePlayers.Count == 0) return;
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
        int count = 0;
        foreach (var cid in _stables.GetValueOrDefault(seat, new List<string>()))
        {
            var kind = _cards.GetValueOrDefault(cid)?.Kind ?? "";
            if (kind is "baby_unicorn" or "unicorn")
                count++;
        }
        return count;
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
        _reactionOrder = ActivePlayers.Where(s => s != actor).ToList();
        _reactionIdx = 0;
        _turnPhase = "reaction";
    }

    private void ClearReaction()
    {
        _reactionActive = false;
        _reactionActor = null;
        _reactionCardId = null;
        _reactionTarget = null;
        _reactionOrder = new List<int>();
        _reactionIdx = 0;
        _reactionStack = new List<string>();
    }

    private int? CurrentReactionSeat
    {
        get
        {
            if (!_reactionActive) return null;
            if (_reactionIdx < 0 || _reactionIdx >= _reactionOrder.Count) return null;
            return _reactionOrder[_reactionIdx];
        }
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
            var expected = CurrentReactionSeat;
            if (seat != expected) return;

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
                }

                _reactionIdx++;
                if (_reactionIdx >= _reactionOrder.Count)
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
            if ((_hands.GetValueOrDefault(seat)?.Count ?? 0) <= HandLimit(seat))
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
            (int, int, int) cardRgb = (160, 80, 200);
            if (hand != null && idx >= 0 && idx < hand.Count)
            {
                var cid = hand[idx];
                var cd = _cards.GetValueOrDefault(cid);
                if (cd != null)
                {
                    cardEmoji = cd.Emoji;
                    cardKind = cd.Kind;
                    cardRgb = HexToRgb(cd.Color, (160, 80, 200));
                }
            }

            PlayFromHand(seat, idx);
            // Animate card flying to play area
            var src = _zoneCenters.GetValueOrDefault(seat, (ScreenW / 2, ScreenH / 2));
            var dst = (ScreenW / 2, ScreenH / 3);
            var col = SeatColors[seat % SeatColors.Length];
            _cardFlips.Add(new CardFlyAnim(src, dst, color: col));

            // Showcase the card face-up at center with sparkles
            if (cardEmoji != null)
            {
                string corner = (cardKind?.Length ?? 0) > 4
                    ? cardKind![..4].ToUpperInvariant()
                    : (cardKind ?? "").ToUpperInvariant();
                _showcases.Add(new CardShowcaseAnim(
                    ScreenW / 2, ScreenH / 2,
                    cardEmoji, "", accentColor: cardRgb, corner: corner,
                    src: (src.Item1, src.Item2)));
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

        // Remove from hand now
        hand.RemoveAt(idx);

        // Some effects require target selection
        var effectType = c.EffectType;
        if (effectType is "STEAL_UNICORN" or "DESTROY_STABLE_CARD" or "SWAP_UNICORN")
        {
            _prompt = new Dictionary<string, object?>
            {
                ["kind"] = effectType,
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

        if (kind is "STEAL_UNICORN" or "DESTROY_STABLE_CARD" or "SWAP_UNICORN")
        {
            var step = PromptString("step");
            if (step == "pick_player")
            {
                int t = PromptInt("target_player", -1);
                if (t < 0 || !ActivePlayers.Contains(t) || t == actor) return;
                _prompt["step"] = "pick_card";
                return;
            }

            if (step == "pick_card")
            {
                int t = PromptInt("target_player", -1);
                int idx = PromptInt("target_index", -1);
                var targetStable = _stables.GetValueOrDefault(t, new List<string>()).ToList();

                if (kind is "STEAL_UNICORN" or "SWAP_UNICORN")
                {
                    var eligible = new List<int>();
                    for (int i = 0; i < targetStable.Count; i++)
                    {
                        var ck = _cards.GetValueOrDefault(targetStable[i])?.Kind ?? "";
                        if (ck is "baby_unicorn" or "unicorn") eligible.Add(i);
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

        // Discard the played card either way
        _discardPile.Add(cardId);
        _prompt = null;
        _actionTaken = true;
        _turnPhase = (_hands.GetValueOrDefault(actor)?.Count ?? 0) > HandLimit(actor) ? "discard" : "action";
        CheckWin();
    }

    private void ResolveEffect(int actor, string cardId, Dictionary<string, object?>? target = null)
    {
        var c = _cards.GetValueOrDefault(cardId);
        if (c == null) return;
        var typ = c.EffectType;

        if (typ == "NONE") return;

        if (typ == "STABLE_ADD_SELF")
        {
            if (!_stables.ContainsKey(actor)) _stables[actor] = new List<string>();
            _stables[actor].Add(cardId);
            return;
        }

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
            if (!_stables.ContainsKey(actor)) _stables[actor] = new List<string>();
            _stables[actor].Add(moved);
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
            var moved = src[idx];
            src.RemoveAt(idx);
            _discardPile.Add(moved);
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
                    _discardPile.Add(mine[i]);
                    mine.RemoveAt(i);
                }
            }
            int n = c.EffectInt("amount");
            DrawToHand(actor, Math.Max(0, n));
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
            ["id"] = c.Id, ["name"] = c.Name, ["kind"] = c.Kind, ["emoji"] = c.Emoji, ["color"] = c.Color,
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
                if (seat != CurrentReactionSeat) return false;
                return c.Kind is "neigh" or "super_neigh";
            }
            if (_prompt != null) return false;
            if (c.Kind == "instant") return true;
            if (c.Kind is "neigh" or "super_neigh") return false;
            if (!isTurn || _turnPhase != "action" || _actionTaken) return false;
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
                ["awaiting_seat"] = CurrentReactionSeat,
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
            ["reaction"] = reaction,
            ["prompt"] = promptSnap,
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

        // Reaction-only buttons
        if (_reactionActive)
        {
            var reacting = CurrentReactionSeat;
            if (reacting is int rs && ActivePlayers.Contains(rs))
            {
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
                    foreach (var t in ActivePlayers)
                    {
                        if (t == actor) continue;
                        _buttons[actor][$"uu_target_player:{t}"] = ($"Target: {PlayerName(t)}", true);
                    }
                }
                else if (step == "pick_card")
                {
                    int t = PromptInt("target_player", -1);
                    var stable = _stables.GetValueOrDefault(t, new List<string>()).ToList();
                    List<int> eligible;
                    if (kind is "STEAL_UNICORN" or "SWAP_UNICORN")
                    {
                        eligible = new List<int>();
                        for (int i = 0; i < stable.Count; i++)
                        {
                            var ck = _cards.GetValueOrDefault(stable[i])?.Kind ?? "";
                            if (ck is "baby_unicorn" or "unicorn") eligible.Add(i);
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
            _buttons[turnSeat][$"uu_play:{i}"] = ($"Play: {c.Name}", true);
        }
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

        // Detect turn change
        var currTurn = CurrentTurnSeat;
        if (State == "playing" && currTurn is int ct && _animPrevTurn is int pt && ct != pt)
        {
            var center = _zoneCenters.GetValueOrDefault(ct, (ScreenW / 2, ScreenH / 2));
            var col = SeatColors[ct % SeatColors.Length];
            _pulseRings.Add(new PulseRing(center.Item1, center.Item2, col,
                maxRadius: Math.Min(ScreenW, ScreenH) / 5, duration: 0.8f));
            _particles.EmitSparkle(center.Item1, center.Item2, col, 18);
        }
        _animPrevTurn = currTurn;

        // Detect reaction window opening
        if (_reactionActive && !_animPrevReaction)
        {
            int cx = ScreenW / 2, cy = ScreenH / 2;
            _flashes.Add(new ScreenFlash((220, 30, 30), 90, 0.4f));
            _textPops.Add(new TextPopAnim("NEIGH? \ud83d\udeab", cx, cy + 55,
                (255, 90, 80), fontSize: 44, duration: 1.8f));
        }
        _animPrevReaction = _reactionActive;

        // Detect winner
        if (_winner != null && _animPrevWinner == null)
        {
            int cx = ScreenW / 2, cy = ScreenH / 2;
            string name = PlayerName(_winner.Value);
            _textPops.Add(new TextPopAnim($"\ud83e\udd84 {name} WINS! \ud83e\udd84", cx, cy,
                (255, 220, 50), fontSize: 50, duration: 5.0f));
            _flashes.Add(new ScreenFlash((255, 255, 180), 140, 0.65f));

            var fwPositions = new[] { (0.25f, 0.30f), (0.50f, 0.20f), (0.75f, 0.30f),
                                      (0.38f, 0.55f), (0.62f, 0.55f), (0.50f, 0.70f) };
            foreach (var (fx, fy) in fwPositions)
                _particles.EmitFirework((int)(ScreenW * fx), (int)(ScreenH * fy), AnimPalette.Rainbow, 70);
            _animFwTimer = 0.85;
        }
        _animPrevWinner = _winner;

        // Ongoing winner fireworks
        if (_winner != null)
        {
            _animFwTimer -= d;
            if (_animFwTimer <= 0.0)
            {
                float fx = (float)(Rng.NextDouble() * 0.76 + 0.12);
                float fy = (float)(Rng.NextDouble() * 0.55 + 0.15);
                _particles.EmitFirework((int)(ScreenW * fx), (int)(ScreenH * fy), AnimPalette.Rainbow, 55);
                _animFwTimer = Rng.NextDouble() * 0.50 + 0.70;
            }
        }
    }

    public override void Draw(Renderer r, int width, int height, double dt)
    {
        if (State == "player_select")
        {
            base.Draw(r, width, height, dt);
            return;
        }

        CardRendering.DrawGameBackground(r, width, height, "unstable_unicorns");

        // Title
        string title = _winner is int w ? $"WINNER: {PlayerName(w)}" : "UNSTABLE UNICORNS";
        RainbowTitle.Draw(r, title, width);

        // Layout: grid of player stables
        var seats = ActivePlayers.ToList();
        if (seats.Count == 0) return;

        int cols = seats.Count > 2 ? 2 : 1;
        int rows = (seats.Count + cols - 1) / cols;
        int pad = 18;
        int top = 48;
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
            int zy = height - top - pad - (row + 1) * zoneH - row * pad;

            r.DrawRect((255, 255, 255), (zx, zy, zoneW, zoneH), alpha: 10);
            r.DrawRect((255, 255, 255), (zx, zy, zoneW, zoneH), width: 2, alpha: 40);

            // Player label
            var pcol = GameConfig.PlayerColors[s % GameConfig.PlayerColors.Length];
            bool isTurn = s == CurrentTurnSeat;
            var nameCol = isTurn ? (255, 240, 100) : pcol;
            r.DrawText(PlayerName(s), zx + 6, zy + 6, 13, nameCol, bold: isTurn, anchorX: "left", anchorY: "top");

            // Zone center for animations
            _zoneCenters[s] = (zx + zoneW / 2, zy + zoneH / 2);

            // Draw stable cards
            var stable = _stables.GetValueOrDefault(s, new List<string>());
            int cx2 = zx + 10;
            int cy2 = zy + 28;
            for (int ci = 0; ci < Math.Min(stable.Count, cardsPerRow * 2); ci++)
            {
                int x = cx2 + (ci % cardsPerRow) * (cardW + gap);
                int y = cy2 + (ci / cardsPerRow) * (cardH + gap);
                if (x + cardW > zx + zoneW - 6 || y + cardH > zy + zoneH - 6) break;
                DrawCardFace(r, (x, y, cardW, cardH), stable[ci]);
            }
        }

        // Animation layers
        _particles.Draw(r);
        foreach (var ring in _pulseRings) ring.Draw(r);
        foreach (var fly in _cardFlips) fly.Draw(r);
        foreach (var sc in _showcases) sc.Draw(r);
        foreach (var flash in _flashes) flash.Draw(r, width, height);
        foreach (var pop in _textPops) pop.Draw(r);

        // Reaction overlay
        if (_reactionActive)
        {
            r.DrawRect((0, 0, 0), (0, 0, width, height), alpha: 120);
            var awaiting = CurrentReactionSeat;
            string txt = awaiting is int aw ? $"Reaction: {PlayerName(aw)}" : "Reaction...";
            r.DrawText(txt, width / 2, height / 2, 34, (245, 245, 245), anchorX: "center", anchorY: "center");
        }
    }

    private void DrawCardFace(Renderer r, (int x, int y, int w, int h) rect, string cid)
    {
        var c = _cards.GetValueOrDefault(cid);
        if (c == null) return;
        var rgb = HexToRgb(c.Color, (140, 140, 140));
        CardRendering.DrawEmojiCard(r, rect, c.Emoji, "", accentRgb: rgb,
            corner: c.Kind.Length > 4 ? c.Kind[..4].ToUpperInvariant() : c.Kind.ToUpperInvariant(),
            maxTitleFontSize: 11);
    }
}
