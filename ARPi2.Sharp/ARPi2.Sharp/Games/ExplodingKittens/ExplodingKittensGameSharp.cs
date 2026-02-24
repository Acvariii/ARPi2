using System;
using System.Collections.Generic;
using System.Linq;
using ARPi2.Sharp.Core;
using ARPi2.Sharp.Games.Blackjack;

namespace ARPi2.Sharp.Games.ExplodingKittens;

// ════════════════════════════════════════════════════════════════
//  Data types
// ════════════════════════════════════════════════════════════════
public class EKCard
{
    private static int _nextId;

    /// <summary>Card kind: EK, DEF, ATK, SKIP, SHUF, FUT, FAV, NOPE</summary>
    public string Kind { get; }

    /// <summary>Unique card instance ID — used to select illustration variant.</summary>
    public int Id { get; }

    /// <summary>Stable illustration variant (0-3) assigned at creation.</summary>
    public int Variant { get; }

    public EKCard(string kind)
    {
        Kind = kind;
        Id = _nextId++;
        Variant = Math.Abs(Id * 2654435761.GetHashCode() ^ kind.GetHashCode()) % 4;
    }

    public string Short() => Kind;
}

// ════════════════════════════════════════════════════════════════
//  ExplodingKittensGame — full port from Python
// ════════════════════════════════════════════════════════════════
public class ExplodingKittensGameSharp : BaseGame
{
    public override string ThemeName => "exploding_kittens";

    // Game state
    private int _currentPlayerIdx;
    private readonly Dictionary<int, List<EKCard>> _hands = new();
    private List<EKCard> _drawPile = new();
    private readonly List<EKCard> _discardPile = new();
    private readonly List<int> _eliminatedPlayers = new();

    /// <summary>How many draws remaining for the current player before turn ends.</summary>
    private int _pendingDraws = 1;

    // Favor target selection
    private bool _awaitingFavorTarget;
    private int? _favorActor;

    // Nope window
    private bool _nopeActive;
    private double _nopeDeadline;
    private int? _nopeActor;
    private (string Kind, Dictionary<string, object> Payload)? _nopeAction;
    private int _nopeCount;

    private int? _winner;

    // Buttons per player
    private readonly Dictionary<int, Dictionary<string, (string Text, bool Enabled)>> _buttons = new();

    // See the Future — private per-player data
    private List<string>? _futureCards;
    private int? _futureViewer;
    private double _futureAge = 999.0;

    // Animations
    private readonly ParticleSystem _particles = new();
    private readonly List<TextPopAnim> _textPops = new();
    private readonly List<PulseRing> _pulseRings = new();
    private readonly List<ScreenFlash> _flashes = new();

    private AmbientSystem _ambient;
    private LightBeamSystem _lightBeams = LightBeamSystem.ForTheme("exploding_kittens");
    private VignettePulse _vignette = new();
    private Starfield _starfield;
    private FloatingIconSystem _floatingIcons = FloatingIconSystem.ForTheme("exploding_kittens");
    private WaveBand _waveBand = WaveBand.ForTheme("exploding_kittens");
    private HeatShimmer _heatShimmer = HeatShimmer.ForTheme("exploding_kittens");
    private string _lastEvent = "";
    private double _lastEventAge = 999.0;
    private int? _animPrevTurn;
    private int? _animPrevWinner;
    private double _animFwTimer;
    private float _screenShakeX, _screenShakeY;
    private float _screenShakeTimer;
    private float _emberTimer;

    // Simple card-fly animations (draw/play)
    private readonly List<CardAnim> _anims = new();

    // 3D animation systems
    private readonly List<ExplosionBurst> _explosions = new();
    private readonly SpotlightCone _spotlight = new();
    private readonly FireEdge _fireEdge = new();
    private readonly CardBreathEffect _cardBreath = new();

    public ExplodingKittensGameSharp(int w, int h, Renderer renderer) : base(w, h, renderer)
    {
        _ambient = AmbientSystem.ForTheme("exploding_kittens", w, h);
        _starfield = Starfield.ForTheme("exploding_kittens", w, h);
    }

    // ─── Current turn seat ─────────────────────────────────────
    private int? CurrentTurnSeat
    {
        get
        {
            if (ActivePlayers.Count == 0) return null;
            int idx = ((_currentPlayerIdx % ActivePlayers.Count) + ActivePlayers.Count) % ActivePlayers.Count;
            return ActivePlayers[idx];
        }
    }

    // ─── Start game ────────────────────────────────────────────
    public override void StartGame(List<int> players)
    {
        var seats = players.Where(s => s >= 0 && s <= 7).Distinct().OrderBy(x => x).ToList();
        if (seats.Count < 2) return;

        ActivePlayers = seats;
        _eliminatedPlayers.Clear();
        _currentPlayerIdx = 0;
        _pendingDraws = 1;
        _awaitingFavorTarget = false;
        _favorActor = null;
        ClearNope();
        _winner = null;

        _hands.Clear();
        _discardPile.Clear();

        // Build deck WITHOUT EKs, shuffle, deal
        _drawPile = BuildDeck(seats.Count, includeEk: false);
        Rng.Shuffle(_drawPile);

        // Deal: 1 Defuse + 7 random cards
        foreach (var s in seats)
        {
            _hands[s] = new List<EKCard> { new EKCard("DEF") };
        }
        for (int round = 0; round < 7; round++)
        {
            foreach (var s in seats)
            {
                var c = DrawCardRaw();
                if (c != null) _hands[s].Add(c);
            }
        }

        // Add EKs (players-1), shuffle
        int ekCount = Math.Max(1, seats.Count - 1);
        for (int i = 0; i < ekCount; i++)
            _drawPile.Add(new EKCard("EK"));
        Rng.Shuffle(_drawPile);

        NoteEvent("Exploding Kittens: start");
        State = "playing";
        RebuildButtons();
    }

    // ─── Handle player quit ────────────────────────────────────
    public void HandlePlayerQuit(int seat)
    {
        if (State != "playing" || _winner != null) return;
        if (!ActivePlayers.Contains(seat)) return;

        // Return hand to draw pile
        if (_hands.TryGetValue(seat, out var hand) && hand.Count > 0)
        {
            _drawPile.AddRange(hand);
            Rng.Shuffle(_drawPile);
            _hands.Remove(seat);
        }

        int removedIdx = ActivePlayers.IndexOf(seat);
        bool wasTurn = CurrentTurnSeat == seat;

        ActivePlayers.Remove(seat);
        if (!_eliminatedPlayers.Contains(seat))
            _eliminatedPlayers.Add(seat);

        // Cancel favor if waiting on quitter
        if (_awaitingFavorTarget && _favorActor == seat)
        {
            _awaitingFavorTarget = false;
            _favorActor = null;
        }

        // Cancel any active nope window
        if (_nopeActive) ClearNope();

        // Nobody left
        if (ActivePlayers.Count == 0)
        {
            _pendingDraws = 1;
            _currentPlayerIdx = 0;
            _awaitingFavorTarget = false;
            _favorActor = null;
            ClearNope();
            State = "player_select";
            NoteEvent("All players left");
            RebuildButtons();
            return;
        }

        // Winner if only one remains
        if (ActivePlayers.Count == 1)
        {
            _winner = ActivePlayers[0];
            _pendingDraws = 1;
            NoteEvent($"Winner: {PlayerName(_winner.Value)}");
            RebuildButtons();
            return;
        }

        // Keep current_player_idx consistent
        if (removedIdx >= 0)
        {
            if (removedIdx < _currentPlayerIdx)
                _currentPlayerIdx = Math.Max(0, _currentPlayerIdx - 1);
            if (wasTurn)
                _currentPlayerIdx = removedIdx % ActivePlayers.Count;
        }

        if (_currentPlayerIdx >= ActivePlayers.Count)
            _currentPlayerIdx = 0;

        if (wasTurn)
            _pendingDraws = 1;

        NoteEvent($"{PlayerName(seat)} quit");
        RebuildButtons();
    }

    // ─── HandleClick (web UI) ──────────────────────────────────
    public override void HandleClick(int playerIdx, string buttonId)
    {
        // Game-specific messages from server passthrough
        if (buttonId.StartsWith("__msg__:"))
        {
            var parts = buttonId.Split(':', 3);
            if (parts.Length >= 2)
            {
                // No game-specific messages defined for EK yet; placeholder for future use
            }
            return;
        }

        if (State != "playing") return;
        if (_winner != null) return;

        int seat = playerIdx;
        if (!ActivePlayers.Contains(seat)) return;

        // Nope window: other players may respond
        if (_nopeActive && seat != _nopeActor)
        {
            if (buttonId == "ek_nope")
            {
                if (!HasCard(seat, "NOPE")) return;
                RemoveOne(seat, "NOPE");
                _discardPile.Add(new EKCard("NOPE"));
                _nopeCount++;
                NoteEvent($"{PlayerName(seat)} played NOPE");
                try
                {
                    int cx = ScreenW / 2, cy = ScreenH / 2;
                    _flashes.Add(new ScreenFlash((200, 80, 20), 55, 0.3f));
                    _textPops.Add(new TextPopAnim("\U0001f6ab NOPE!", cx, cy - 40, (230, 100, 50), fontSize: 32));
                }
                catch { }
                RebuildButtons();
            }
            else if (buttonId.StartsWith("ek_play:"))
            {
                // UX convenience: allow clicking the NOPE card itself
                if (!int.TryParse(buttonId.AsSpan(8), out int idx)) return;
                var h = _hands.GetValueOrDefault(seat);
                if (h == null || idx < 0 || idx >= h.Count) return;
                if (h[idx].Kind != "NOPE") return;
                h.RemoveAt(idx);
                _discardPile.Add(new EKCard("NOPE"));
                _nopeCount++;
                NoteEvent($"{PlayerName(seat)} played NOPE");
                try
                {
                    int cx = ScreenW / 2, cy = ScreenH / 2;
                    _flashes.Add(new ScreenFlash((200, 80, 20), 55, 0.3f));
                    _textPops.Add(new TextPopAnim("\U0001f6ab NOPE!", cx, cy - 40, (230, 100, 50), fontSize: 32));
                }
                catch { }
                RebuildButtons();
            }
            return;
        }

        // Favor target selection
        if (_awaitingFavorTarget)
        {
            if (seat != _favorActor) return;
            if (buttonId.StartsWith("favor_target:"))
            {
                if (!int.TryParse(buttonId.AsSpan(13), out int target)) return;
                if (!ActivePlayers.Contains(target) || target == seat) return;
                ExecuteFavor(seat, target);
                _awaitingFavorTarget = false;
                _favorActor = null;
                RebuildButtons();
            }
            return;
        }

        // Only current player can act
        if (seat != CurrentTurnSeat) return;

        if (buttonId == "ek_draw")
        {
            DoDraw(seat);
            return;
        }

        if (buttonId.StartsWith("ek_play:"))
        {
            if (!int.TryParse(buttonId.AsSpan(8), out int cardIdx)) return;
            var hand = _hands.GetValueOrDefault(seat);
            if (hand == null || cardIdx < 0 || cardIdx >= hand.Count) return;
            var card = hand[cardIdx];
            if (card.Kind is not ("ATK" or "SKIP" or "SHUF" or "FUT" or "FAV")) return;

            // Remove from hand, discard
            hand.RemoveAt(cardIdx);
            _discardPile.Add(card);
            QueuePlayAnim(seat, card);

            // Action card sparkle + flash + text
            try
            {
                int cx = ScreenW / 2, cy = ScreenH / 2;
                var acol = card.Kind switch
                {
                    "ATK" => ((int, int, int))(230, 60, 60),
                    "SKIP" => (255, 200, 50),
                    "SHUF" => (100, 180, 255),
                    "FUT" => (150, 100, 255),
                    "FAV" => (255, 130, 200),
                    _ => (200, 200, 200),
                };
                var actionLabel = card.Kind switch
                {
                    "ATK" => "⚔️ ATTACK!",
                    "SKIP" => "⏭️ SKIP!",
                    "SHUF" => "🔀 SHUFFLE!",
                    "FUT" => "🔮 SEE THE FUTURE",
                    "FAV" => "🎁 FAVOR",
                    _ => card.Kind,
                };
                _particles.EmitSparkle(cx, cy, acol, 16);
                _flashes.Add(new ScreenFlash(acol, 35, 0.3f));
                _textPops.Add(new TextPopAnim(actionLabel, cx, cy - 40, acol, fontSize: 28));
                _pulseRings.Add(new PulseRing(cx, cy, acol, maxRadius: 70, duration: 0.6f));
            }
            catch { }

            // Execute card (some open a nope window)
            PlayAction(seat, card);
            RebuildButtons();
        }
    }

    // ─── Snapshot ──────────────────────────────────────────────
    public override Dictionary<string, object?> GetSnapshot(int playerIdx)
    {
        int seat = playerIdx;
        var hand = _hands.GetValueOrDefault(seat, new List<EKCard>());
        var counts = new Dictionary<string, object?>();
        foreach (var s in ActivePlayers)
            counts[s.ToString()] = _hands.GetValueOrDefault(s)?.Count ?? 0;

        bool isTurn = seat == CurrentTurnSeat && _winner == null;
        bool canNope = _nopeActive && seat != _nopeActor && HasCard(seat, "NOPE");

        var yourHand = hand.Select((c, i) =>
        {
            bool playable;
            if (_winner != null)
                playable = false;
            else if (canNope)
                playable = c.Kind == "NOPE";
            else if (!isTurn)
                playable = false;
            else
                playable = c.Kind is "ATK" or "SKIP" or "SHUF" or "FUT" or "FAV";

            return (Dictionary<string, object?>)new Dictionary<string, object?>
            {
                ["idx"] = i,
                ["text"] = c.Short(),
                ["playable"] = playable,
            };
        }).ToList();

        var snap = new Dictionary<string, object?>
        {
            ["state"] = State,
            ["active_players"] = ActivePlayers.ToList(),
            ["eliminated_players"] = _eliminatedPlayers.ToList(),
            ["current_turn_seat"] = CurrentTurnSeat,
            ["pending_draws"] = _pendingDraws,
            ["deck_count"] = _drawPile.Count,
            ["discard_top"] = _discardPile.Count > 0 ? _discardPile[^1].Short() : null,
            ["last_event"] = !string.IsNullOrEmpty(_lastEvent) && _lastEventAge < 6.0 ? _lastEvent : null,
            ["last_event_age_ms"] = (int)(_lastEventAge * 1000),
            ["hand_counts"] = counts,
            ["your_hand"] = yourHand,
            ["awaiting_favor_target"] = _awaitingFavorTarget && _favorActor == seat,
            ["nope_active"] = _nopeActive,
            ["nope_count"] = _nopeCount,
            ["winner"] = _winner,
            // Only the player who played See the Future sees the cards
            ["future_cards"] = (_futureViewer == seat && _futureCards != null && _futureAge < 6.0) ? _futureCards : null,
        };

        return new Dictionary<string, object?> { ["exploding_kittens"] = snap };
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

    // ─── Internals: deck & cards ───────────────────────────────
    private List<EKCard> BuildDeck(int playerCount, bool includeEk)
    {
        var deck = new List<EKCard>();

        if (includeEk)
        {
            for (int i = 0; i < Math.Max(1, playerCount - 1); i++)
                deck.Add(new EKCard("EK"));
        }

        // Extra defuses
        for (int i = 0; i < 2; i++)
            deck.Add(new EKCard("DEF"));

        // Action cards
        (string kind, int count)[] actions =
        {
            ("ATK", 4), ("SKIP", 4), ("SHUF", 4),
            ("FUT", 5), ("FAV", 4), ("NOPE", 5),
        };
        foreach (var (kind, count) in actions)
            for (int i = 0; i < count; i++)
                deck.Add(new EKCard(kind));

        return deck;
    }

    private bool HasCard(int seat, string kind)
    {
        var hand = _hands.GetValueOrDefault(seat);
        return hand != null && hand.Any(c => c.Kind == kind);
    }

    private bool RemoveOne(int seat, string kind)
    {
        var hand = _hands.GetValueOrDefault(seat);
        if (hand == null) return false;
        for (int i = 0; i < hand.Count; i++)
        {
            if (hand[i].Kind == kind)
            {
                hand.RemoveAt(i);
                return true;
            }
        }
        return false;
    }

    private EKCard? DrawCardRaw()
    {
        if (_drawPile.Count == 0) RefillDrawPileFromDiscard();
        if (_drawPile.Count == 0) return null;
        var c = _drawPile[^1];
        _drawPile.RemoveAt(_drawPile.Count - 1);
        return c;
    }

    private void RefillDrawPileFromDiscard()
    {
        if (_discardPile.Count <= 1) return;
        var top = _discardPile[^1];
        var refill = _discardPile.GetRange(0, _discardPile.Count - 1);
        _discardPile.Clear();
        _discardPile.Add(top);
        Rng.Shuffle(refill);
        _drawPile.AddRange(refill);
    }

    private void ReinsertRandom(EKCard card)
    {
        if (_drawPile.Count == 0)
        {
            _drawPile.Add(card);
            return;
        }
        int pos = Rng.Next(0, _drawPile.Count + 1);
        _drawPile.Insert(pos, card);
    }

    // ─── Internals: drawing & turns ────────────────────────────
    private void DoDraw(int seat)
    {
        if (_awaitingFavorTarget) return; // Can't draw while selecting favor target
        if (_nopeActive) return;          // Can't draw during nope window
        if (_pendingDraws <= 0) return;

        var c = DrawCardRaw();
        if (c == null)
        {
            NoteEvent("Deck empty");
            if (_winner == null && ActivePlayers.Count == 1)
            {
                _winner = ActivePlayers[0];
                NoteEvent($"Winner: {PlayerName(_winner.Value)}");
                RebuildButtons();
                return;
            }
            _pendingDraws = 0;
            AdvanceTurnIfDone();
            RebuildButtons();
            return;
        }

        QueueDrawAnim(seat);
        NoteEvent($"{PlayerName(seat)} drew");

        if (c.Kind == "EK")
        {
            // Resolve explosion
            if (HasCard(seat, "DEF"))
            {
                RemoveOne(seat, "DEF");
                _discardPile.Add(new EKCard("DEF"));
                ReinsertRandom(new EKCard("EK"));
                NoteEvent($"{PlayerName(seat)} defused!");
                try
                {
                    int cx = ScreenW / 2, cy = ScreenH / 2;
                    _flashes.Add(new ScreenFlash((60, 200, 100), 60, 0.4f));
                    _flashes.Add(new ScreenFlash((180, 255, 180), 30, 0.15f));
                    _textPops.Add(new TextPopAnim($"\U0001f9f0 DEFUSED! {PlayerName(seat)}", cx, cy - 40, (80, 230, 130), fontSize: 30));
                    _particles.EmitSparkle(cx, cy, (80, 230, 130), 30);
                    _particles.EmitSparkle(cx, cy, (200, 255, 200), 15);
                    _pulseRings.Add(new PulseRing(cx, cy, (80, 230, 130), maxRadius: Math.Min(ScreenW, ScreenH) / 4, duration: 0.6f));
                    // Cascade sparkles from top
                    for (int sp = 0; sp < 6; sp++)
                    {
                        float sx = cx + (float)(Rng.NextDouble() * 200 - 100);
                        _particles.Emit(sx, cy - 60, (120, 255, 160), count: 3, speed: 40f, gravity: 80f,
                            life: 1.2f, radius: 2.5f);
                    }
                }
                catch { }
            }
            else
            {
                Explode(seat);
                return;
            }
        }
        else
        {
            // Normal card drawn into hand
            if (!_hands.ContainsKey(seat)) _hands[seat] = new List<EKCard>();
            _hands[seat].Add(c);
        }

        _pendingDraws--;
        AdvanceTurnIfDone();
        RebuildButtons();
    }

    private void Explode(int seat)
    {
        ActivePlayers.Remove(seat);
        if (!_eliminatedPlayers.Contains(seat))
            _eliminatedPlayers.Add(seat);

        NoteEvent($"{PlayerName(seat)} player exploded");

        // Explosion animations
        try
        {
            int cx = ScreenW / 2, cy = ScreenH / 2;
            _flashes.Add(new ScreenFlash((255, 80, 30), 80, 0.5f));
            _flashes.Add(new ScreenFlash((255, 255, 200), 130, 0.15f)); // bright initial flash
            _textPops.Add(new TextPopAnim($"\U0001f4a5 KABOOM! {PlayerName(seat)}", cx, cy - 200, (255, 90, 40), fontSize: 36));
            _pulseRings.Add(new PulseRing(cx, cy, (255, 120, 0), maxRadius: Math.Min(ScreenW, ScreenH) / 3, duration: 0.9f));
            _pulseRings.Add(new PulseRing(cx, cy, (255, 60, 0), maxRadius: Math.Min(ScreenW, ScreenH) / 4, duration: 0.6f));
            // Screen shake
            _screenShakeTimer = 0.8f;
            for (int i = 0; i < 8; i++)
            {
                _particles.EmitFirework(
                    cx + Rng.Next(-140, 141), cy + Rng.Next(-90, 91),
                    new[] { (220, 60, 20), (255, 140, 0), (255, 220, 0) });
            }
            // Dramatic multi-ring explosion burst
            _explosions.Add(new ExplosionBurst(cx, cy, maxRadius: Math.Min(ScreenW, ScreenH) / 3, duration: 1.4f));
            _explosions.Add(new ExplosionBurst(cx - 80, cy - 40, maxRadius: 120, duration: 1.0f));
            _explosions.Add(new ExplosionBurst(cx + 80, cy + 30, maxRadius: 100, duration: 0.9f));
        }
        catch { }

        // Winner if only one remains
        if (ActivePlayers.Count == 1)
        {
            _winner = ActivePlayers[0];
            NoteEvent($"Winner: {PlayerName(_winner.Value)}");
            RebuildButtons();
            return;
        }

        // Keep turn index in range
        if (_currentPlayerIdx >= ActivePlayers.Count)
            _currentPlayerIdx = 0;
        _pendingDraws = 1;
        ClearNope();
        _awaitingFavorTarget = false;
        _favorActor = null;
        RebuildButtons();
    }

    private void AdvanceTurnIfDone()
    {
        if (_winner != null) return;
        if (_pendingDraws > 0) return;
        // Clear any lingering favor state before advancing turn
        _awaitingFavorTarget = false;
        _favorActor = null;
        AdvanceIndex(1);
        _pendingDraws = 1;
    }

    private void AdvanceIndex(int steps)
    {
        if (ActivePlayers.Count == 0) return;
        _currentPlayerIdx = (_currentPlayerIdx + steps) % ActivePlayers.Count;
    }

    // ─── Internals: action cards ───────────────────────────────
    private void PlayAction(int seat, EKCard card)
    {
        NoteEvent($"{PlayerName(seat)} played {card.Kind}");

        // All action cards are noppable
        if (card.Kind is "ATK" or "SKIP" or "SHUF" or "FUT" or "FAV")
            OpenNopeWindow(seat, card.Kind, new Dictionary<string, object>());
        else
            ApplyAction(card.Kind, new Dictionary<string, object>());
    }

    private void OpenNopeWindow(int actor, string actionKind, Dictionary<string, object> payload)
    {
        _nopeActive = true;
        _nopeDeadline = 3.0;
        _nopeActor = actor;
        _nopeAction = (actionKind, payload);
        _nopeCount = 0;
    }

    private void ResolveNopeWindow()
    {
        if (!_nopeActive || _nopeAction == null)
        {
            ClearNope();
            return;
        }

        var (kind, payload) = _nopeAction.Value;
        bool canceled = _nopeCount % 2 == 1;
        if (canceled)
            NoteEvent("NOPE!");
        else
            ApplyAction(kind, payload);

        ClearNope();
        RebuildButtons();
    }

    private void ClearNope()
    {
        _nopeActive = false;
        _nopeDeadline = 0.0;
        _nopeActor = null;
        _nopeAction = null;
        _nopeCount = 0;
    }

    private void ApplyAction(string kind, Dictionary<string, object> payload)
    {
        int? seat = CurrentTurnSeat;
        if (seat == null) return;

        switch (kind)
        {
            case "SHUF":
                Rng.Shuffle(_drawPile);
                NoteEvent("Shuffled");
                break;

            case "FUT":
                // Store top 3 privately – only the player who played FUT should see them
                var top3 = _drawPile.AsEnumerable().Reverse().Take(3).Select(c => c.Short()).ToList();
                if (top3.Count > 0)
                {
                    _futureCards = top3;
                    _futureViewer = seat.Value;
                    _futureAge = 0.0;
                    NoteEvent($"{PlayerName(seat.Value)} sees the future…");
                }
                break;

            case "FAV":
                _awaitingFavorTarget = true;
                _favorActor = seat.Value;
                NoteEvent("Choose a target");
                break;

            case "SKIP":
                _pendingDraws = 0;
                AdvanceTurnIfDone();
                break;

            case "ATK":
                // End your turn without drawing; next player takes 2 draws
                _pendingDraws = 0;
                AdvanceTurnIfDone();
                _pendingDraws = 2;
                NoteEvent("Attack!");
                break;
        }
    }

    private void ExecuteFavor(int actor, int target)
    {
        var tHand = _hands.GetValueOrDefault(target);
        if (tHand == null || tHand.Count == 0)
        {
            NoteEvent("Favor: no cards");
            return;
        }
        int takeIdx = Rng.Next(tHand.Count);
        var take = tHand[takeIdx];
        tHand.RemoveAt(takeIdx);
        if (!_hands.ContainsKey(actor)) _hands[actor] = new List<EKCard>();
        _hands[actor].Add(take);
        NoteEvent($"Favor: {PlayerName(actor)} took a card");
    }

    // ─── Web UI buttons ────────────────────────────────────────
    private void RebuildButtons()
    {
        _buttons.Clear();
        if (State != "playing") return;

        foreach (var s in ActivePlayers)
            _buttons[s] = BuildPlayerButtons(s);

        // Also allow NOPE for non-actors while a nope window is active
        if (_nopeActive)
        {
            foreach (var s in ActivePlayers)
            {
                if (s == _nopeActor) continue;
                if (HasCard(s, "NOPE"))
                {
                    if (!_buttons.ContainsKey(s))
                        _buttons[s] = new Dictionary<string, (string Text, bool Enabled)>();
                    _buttons[s]["ek_nope"] = ("NOPE", true);
                }
            }
        }
    }

    private Dictionary<string, (string Text, bool Enabled)> BuildPlayerButtons(int seat)
    {
        var btns = new Dictionary<string, (string Text, bool Enabled)>();

        if (_winner != null) return btns;

        // Favor targeting: only actor gets target buttons
        if (_awaitingFavorTarget && seat == _favorActor)
        {
            foreach (var t in ActivePlayers)
            {
                if (t == seat) continue;
                btns[$"favor_target:{t}"] = ($"Favor: {PlayerName(t)}", true);
            }
            return btns;
        }

        bool isTurn = seat == CurrentTurnSeat;
        bool canDraw = isTurn && _pendingDraws > 0 && !_nopeActive && !_awaitingFavorTarget;
        btns["ek_draw"] = ("Draw", canDraw);
        return btns;
    }

    private void NoteEvent(string text)
    {
        _lastEvent = (text ?? "").Trim();
        _lastEventAge = 0.0;
    }

    // ─── Update / Draw ─────────────────────────────────────────
    public override void Update(double dt)
    {
        float d = Math.Clamp((float)dt, 0f, 0.2f);
        if (_lastEventAge < 999.0) _lastEventAge += d;

        // Tick See-the-Future display timer and auto-clear
        if (_futureAge < 999.0) _futureAge += d;
        if (_futureCards != null && _futureAge >= 6.0)
        {
            _futureCards = null;
            _futureViewer = null;
        }

        // Nope window countdown
        if (_nopeActive)
        {
            _nopeDeadline -= d;
            if (_nopeDeadline <= 0)
                ResolveNopeWindow();
        }

        // Tick animations
        _particles.Update(d);
        for (int i = _textPops.Count - 1; i >= 0; i--) { _textPops[i].Update(d); if (_textPops[i].Done) _textPops.RemoveAt(i); }
        for (int i = _pulseRings.Count - 1; i >= 0; i--) { _pulseRings[i].Update(d); if (_pulseRings[i].Done) _pulseRings.RemoveAt(i); }
        for (int i = _flashes.Count - 1; i >= 0; i--) { _flashes[i].Update(d); if (_flashes[i].Done) _flashes.RemoveAt(i); }

        _ambient.Update((float)d, ScreenW, ScreenH);
        _lightBeams.Update((float)d, ScreenW, ScreenH);
        _vignette.Update((float)d);
        _starfield.Update((float)d);
        _floatingIcons.Update((float)d, ScreenW, ScreenH);
        _waveBand.Update((float)d);
        _heatShimmer.Update((float)d);

        // 3D animation systems
        _spotlight.Update((float)d);
        _fireEdge.Update((float)d);
        _cardBreath.Update((float)d);
        for (int i = _explosions.Count - 1; i >= 0; i--)
        {
            _explosions[i].Update((float)d);
            if (_explosions[i].Done) _explosions.RemoveAt(i);
        }

        // Card fly animations
        for (int i = _anims.Count - 1; i >= 0; i--)
        {
            _anims[i].Elapsed += d;
            if (_anims[i].Elapsed - _anims[i].Delay >= _anims[i].TotalDuration)
                _anims.RemoveAt(i);
        }

        // Screen shake decay
        if (_screenShakeTimer > 0)
        {
            _screenShakeTimer -= d;
            float intensity = _screenShakeTimer * 12f;
            _screenShakeX = (float)(Rng.NextDouble() * 2 - 1) * intensity;
            _screenShakeY = (float)(Rng.NextDouble() * 2 - 1) * intensity;
        }
        else
        {
            _screenShakeX = 0; _screenShakeY = 0;
        }

        // Ambient embers — spawn from all edges and across screen for full coverage
        _emberTimer += d;
        if (_emberTimer > 0.08f && State == "playing" && _winner == null)
        {
            _emberTimer -= 0.08f;
            var emberColors = new (int, int, int)[] { (200, 90, 20), (255, 140, 20), (180, 50, 10), (255, 180, 40), (255, 100, 10) };
            var eCol = emberColors[Rng.Next(emberColors.Length)];
            float eSize = 1.2f + (float)(Rng.NextDouble() * 2.5);
            float eLife = 2f + (float)(Rng.NextDouble() * 2.5);

            // 70% from bottom, 15% from left, 15% from right
            double src = Rng.NextDouble();
            if (src < 0.7)
            {
                // Bottom — full width
                float ex = (float)(Rng.NextDouble() * ScreenW);
                _particles.Emit(ex, ScreenH + 10, eCol, count: 1, speed: 15f + (float)(Rng.NextDouble() * 35), gravity: -45f,
                    life: eLife, radius: eSize);
            }
            else if (src < 0.85)
            {
                // Left edge — random height
                float ey = (float)(Rng.NextDouble() * ScreenH);
                _particles.Emit(-5, ey, eCol, count: 1, speed: 12f + (float)(Rng.NextDouble() * 20), gravity: -25f,
                    life: eLife, radius: eSize * 0.8f);
            }
            else
            {
                // Right edge
                float ey = (float)(Rng.NextDouble() * ScreenH);
                _particles.Emit(ScreenW + 5, ey, eCol, count: 1, speed: 12f + (float)(Rng.NextDouble() * 20), gravity: -25f,
                    life: eLife, radius: eSize * 0.8f);
            }
        }

        // Occasional floating side sparks — drift from edges
        if (State == "playing" && _winner == null && Rng.NextDouble() < 0.015)
        {
            bool leftSide = Rng.NextDouble() < 0.5;
            float sparkX = leftSide ? -5 : ScreenW + 5;
            float sparkY = (float)(Rng.NextDouble() * ScreenH);
            float sparkDir = leftSide ? 20f : -20f;
            _particles.Emit(sparkX, sparkY, (255, 200, 60), count: 1, speed: 15f, gravity: -20f,
                life: 3f, radius: 1.5f);
        }

        // Turn change pulse
        var currTurn = CurrentTurnSeat;
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
            // Scatter fireworks across the whole board
            for (int i = 0; i < 12; i++)
                _particles.EmitFirework(Rng.Next(ScreenW * 10 / 100, ScreenW * 90 / 100),
                    Rng.Next(ScreenH * 10 / 100, ScreenH * 90 / 100), AnimPalette.Rainbow);
            _flashes.Add(new ScreenFlash((255, 220, 80), 60, 1.0f));
            _textPops.Add(new TextPopAnim($"\U0001f3c6 {PlayerName(w)} wins!", cx, cy - 60, (255, 220, 80), fontSize: 36));
            _animFwTimer = 6.0;
        }
        if (_animFwTimer > 0)
        {
            _animFwTimer = Math.Max(0, _animFwTimer - d);
            if ((int)(_animFwTimer * 3) % 2 == 0)
            {
                // Scatter fireworks randomly across the board
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
            //  LOBBY — EK2 / Amazon Luna style with QR code
            // ═══════════════════════════════════════════════════════════
            CardRendering.DrawGameBackground(r, width, height, "exploding_kittens");
            _ambient.Draw(r);
            _lightBeams.Draw(r, width, height);
            _starfield.Draw(r);
            _floatingIcons.Draw(r);

            // Title
            RainbowTitle.Draw(r, "EXPLODING KITTENS", width);

            // Subtitle
            r.DrawText("SELECT PLAYERS & SCAN TO JOIN", width / 2, 52, 13,
                (220, 160, 60), anchorX: "center", anchorY: "center", bold: true);

            // Player selection circles
            SelectionUI.Draw(r);

            // QR Code panel — right side of screen
            int qrSize = Math.Clamp(Math.Min(width, height) * 18 / 100, 100, 200);
            int qrX = width - qrSize / 2 - 60;
            int qrY = height / 2;
            QRCodeRenderer.DrawQRPanel(r, qrX, qrY, qrSize,
                title: "📱 SCAN TO JOIN",
                accentColor: (255, 140, 0));

            // Ambient embers for lobby too
            _particles.Draw(r);
            _waveBand.Draw(r, width, height);
            _vignette.Draw(r, width, height);
            return;
        }

        // ═══════════════════════════════════════════════════════════════
        //  IN-GAME — EK2 / Amazon Luna production-quality renderer
        // ═══════════════════════════════════════════════════════════════

        // Apply screen shake offset
        int shX = (int)_screenShakeX, shY = (int)_screenShakeY;

        CardRendering.DrawGameBackground(r, width, height, "exploding_kittens");
        _ambient.Draw(r);
        _lightBeams.Draw(r, width, height);
        _starfield.Draw(r);
        _floatingIcons.Draw(r);

        // Animated fire edges — Luna-style screen border flames
        _fireEdge.Draw(r, width, height);

        int cx = width / 2 + shX, cy = height / 2 + shY;

        // ─── Title ─────────────────────────────────────────────
        RainbowTitle.Draw(r, "EXPLODING KITTENS", width);

        // ─── HUD Bar — premium frosted dark-glass panel ──────
        var turn = CurrentTurnSeat;
        int hudH = 40;
        int hudY = 48;
        int hudW = Math.Min(width - 40, 820);
        int hudX = (width - hudW) / 2;

        // HUD multi-layer shadow
        r.DrawRect((0, 0, 0), (hudX + 5, hudY + 5, hudW, hudH), alpha: 60);
        r.DrawRect((0, 0, 0), (hudX + 3, hudY + 3, hudW, hudH), alpha: 90);

        // HUD background — dark glass with subtle gradient
        r.DrawRect((16, 12, 26), (hudX, hudY, hudW, hudH), alpha: 230);
        r.DrawRect((24, 18, 34), (hudX + 2, hudY + 2, hudW - 4, hudH / 3), alpha: 30); // top lighter band

        // Accent top and bottom lines
        r.DrawRect((255, 140, 0), (hudX, hudY, hudW, 3), alpha: 150);
        r.DrawRect((255, 160, 20), (hudX, hudY + 3, hudW, 1), alpha: 40);
        r.DrawRect((0, 0, 0), (hudX, hudY + hudH - 2, hudW, 2), alpha: 60);

        // Border with highlights
        r.DrawRect((90, 70, 110), (hudX, hudY, hudW, hudH), width: 1, alpha: 60);
        r.DrawRect((255, 255, 255), (hudX + 1, hudY + 4, hudW - 2, 1), alpha: 8);

        // HUD content
        int hudCy = hudY + hudH / 2;
        int seg = hudW / 4;

        // ── Segment separators ──
        for (int sep = 1; sep < 4; sep++)
        {
            int sx = hudX + sep * seg;
            r.DrawLine((80, 60, 100), (sx, hudY + 6), (sx, hudY + hudH - 6), width: 1, alpha: 30);
        }

        // ── Deck count with icon and danger coloring ──
        string deckIcon = _drawPile.Count <= 3 ? "🔥" : "🃏";
        var deckCol = _drawPile.Count <= 3 ? (255, 80, 40) : _drawPile.Count <= 8 ? (255, 180, 40) : (200, 200, 210);
        // Deck icon glow if danger
        if (_drawPile.Count <= 3)
            r.DrawCircle((255, 40, 0), (hudX + seg / 2 - 40, hudCy), 10, alpha: 12);
        r.DrawText($"{deckIcon} Deck: {_drawPile.Count}", hudX + seg / 2, hudCy + 1, 13, (0, 0, 0),
            anchorX: "center", anchorY: "center", bold: true, alpha: 60);
        r.DrawText($"{deckIcon} Deck: {_drawPile.Count}", hudX + seg / 2, hudCy, 13, deckCol,
            anchorX: "center", anchorY: "center", bold: true);

        // ── Discard top ──
        string topDiscard = _discardPile.Count > 0 ? _discardPile[^1].Short() : "—";
        r.DrawText($"Discard: {topDiscard}", hudX + seg + seg / 2, hudCy + 1, 13, (0, 0, 0),
            anchorX: "center", anchorY: "center", alpha: 50);
        r.DrawText($"Discard: {topDiscard}", hudX + seg + seg / 2, hudCy, 13, (180, 170, 190),
            anchorX: "center", anchorY: "center");

        // ── Turn indicator with player color pip ──
        if (turn is int t)
        {
            var tcol = GameConfig.PlayerColors[t % GameConfig.PlayerColors.Length];
            // Player color dot with glow
            r.DrawCircle(tcol, (hudX + 2 * seg + 12, hudCy), 6, alpha: 220);
            r.DrawCircle(tcol, (hudX + 2 * seg + 12, hudCy), 10, alpha: 14);
            r.DrawCircle((255, 255, 255), (hudX + 2 * seg + 11, hudCy - 1), 2, alpha: 30);
            r.DrawText($"{PlayerName(t)}'s Turn", hudX + 2 * seg + 22, hudCy + 1, 13, (0, 0, 0),
                anchorX: "left", anchorY: "center", bold: true, alpha: 50);
            r.DrawText($"{PlayerName(t)}'s Turn", hudX + 2 * seg + 22, hudCy, 13, (255, 220, 100),
                anchorX: "left", anchorY: "center", bold: true);
        }
        else
        {
            r.DrawText("Turn: —", hudX + 2 * seg + seg / 2, hudCy, 13, (140, 140, 150),
                anchorX: "center", anchorY: "center");
        }

        // ── Pending draws warning ──
        if (_pendingDraws > 1)
        {
            // Warning glow behind
            r.DrawCircle((255, 40, 0), (hudX + 3 * seg + seg / 2, hudCy), 16, alpha: 14);
            r.DrawText($"⚠ DRAW {_pendingDraws}×", hudX + 3 * seg + seg / 2, hudCy + 1, 14, (0, 0, 0),
                anchorX: "center", anchorY: "center", bold: true, alpha: 60);
            r.DrawText($"⚠ DRAW {_pendingDraws}×", hudX + 3 * seg + seg / 2, hudCy, 14, (255, 80, 40),
                anchorX: "center", anchorY: "center", bold: true);
        }

        // ─── Nope window overlay — premium red banner ──────────
        if (_nopeActive)
        {
            int nopeY = hudY + hudH + 8;
            int nopeW = Math.Min(420, width * 32 / 100);
            int nopeH = 38;
            int nopeX = cx - nopeW / 2;

            // Multi-layer shadow for depth
            SoftShadow.Draw(r, nopeX + 3, nopeY + 4, nopeW, nopeH, layers: 4, maxAlpha: 90);

            // Dark red glass panel
            BeveledRect.Draw(r, nopeX, nopeY, nopeW, nopeH, (60, 6, 6), bevelSize: 3);

            // Red accent border
            r.DrawRect((220, 40, 40), (nopeX, nopeY, nopeW, nopeH), width: 2, alpha: 220);
            r.DrawRect((255, 80, 80), (nopeX, nopeY, nopeW, 3), alpha: 200);
            r.DrawRect((255, 120, 80), (nopeX + 1, nopeY + 3, nopeW - 2, 1), alpha: 40);

            // Countdown bar — glowing progressively
            float nopeProgress = Math.Clamp((float)_nopeDeadline / 3f, 0f, 1f);
            int barW = (int)((nopeW - 10) * nopeProgress);
            r.DrawRect((0, 0, 0), (nopeX + 5, nopeY + nopeH - 8, nopeW - 10, 4), alpha: 50);
            var barCol = nopeProgress > 0.5f ? (220, 60, 40) : nopeProgress > 0.2f ? (255, 120, 30) : (255, 40, 20);
            r.DrawRect(barCol, (nopeX + 5, nopeY + nopeH - 8, barW, 4), alpha: 200);
            // Bar glow
            r.DrawRect(barCol, (nopeX + 5, nopeY + nopeH - 9, barW, 1), alpha: 40);

            // Pulsing side danger indicators
            int pulseA = (int)(40 + 30 * Math.Sin(_nopeDeadline * 6));
            r.DrawCircle((255, 40, 20), (nopeX + 10, nopeY + nopeH / 2), 4, alpha: pulseA);
            r.DrawCircle((255, 40, 20), (nopeX + nopeW - 10, nopeY + nopeH / 2), 4, alpha: pulseA);

            string nopeLabel = _nopeCount > 0
                ? $"🚫 NOPE WINDOW ({_nopeCount} played)"
                : "🚫 NOPE WINDOW — react now!";
            r.DrawText(nopeLabel, cx + 1, nopeY + nopeH / 2 - 1, 12, (0, 0, 0),
                anchorX: "center", anchorY: "center", bold: true, alpha: 60);
            r.DrawText(nopeLabel, cx, nopeY + nopeH / 2 - 2, 12, (255, 170, 160),
                anchorX: "center", anchorY: "center", bold: true);
        }

        // ─── Table center glow — slow breathing radial gradient ──
        int minDim = Math.Min(width, height);
        // Use _cardBreath phase for a slow, visible breathing effect
        float breathPhase = _cardBreath.Scale; // oscillates around 1.0
        float slowBreath = MathF.Sin(breathPhase * 4.2f); // map to smooth sin wave
        float breathScale = 1f + slowBreath * 0.08f; // ±8% size variation

        // Purple circles — breathe in size
        int pr1 = (int)(minDim * 28 / 100 * breathScale);
        int pr2 = (int)(minDim * 22 / 100 * breathScale);
        int pr3 = (int)(minDim * 16 / 100 * breathScale);
        r.DrawCircle((40, 10, 60), (cx, cy), pr1, alpha: 7);
        r.DrawCircle((60, 20, 80), (cx, cy), pr2, alpha: 12);
        r.DrawCircle((80, 30, 100), (cx, cy), pr3, alpha: 14);
        r.DrawCircle((100, 40, 130), (cx, cy), (int)(minDim * 10 / 100 * breathScale), alpha: 10);

        // Yellow/warm inner circles — counter-phase breathing for organic feel
        float warmBreath = 1f + MathF.Sin(breathPhase * 4.2f + 1.8f) * 0.06f;
        int yr1 = (int)(minDim * 8 / 100 * warmBreath);
        int yr2 = (int)(minDim * 4 / 100 * warmBreath);
        r.DrawCircle((140, 60, 180), (cx, cy), yr1, alpha: 14);
        r.DrawCircle((180, 80, 220), (cx, cy), yr2, alpha: 8);
        r.DrawCircle((200, 120, 240), (cx, cy), (int)(minDim * 2 / 100 * warmBreath), alpha: 5);

        // Decorative corner accents — subtle design elements
        int cornerSize = Math.Min(60, minDim * 6 / 100);
        int cornerA = 10;
        r.DrawLine((120, 60, 160), (20, 20), (20 + cornerSize, 20), width: 1, alpha: cornerA);
        r.DrawLine((120, 60, 160), (20, 20), (20, 20 + cornerSize), width: 1, alpha: cornerA);
        r.DrawLine((120, 60, 160), (width - 20, 20), (width - 20 - cornerSize, 20), width: 1, alpha: cornerA);
        r.DrawLine((120, 60, 160), (width - 20, 20), (width - 20, 20 + cornerSize), width: 1, alpha: cornerA);
        r.DrawLine((120, 60, 160), (20, height - 20), (20 + cornerSize, height - 20), width: 1, alpha: cornerA);
        r.DrawLine((120, 60, 160), (20, height - 20), (20, height - 20 - cornerSize), width: 1, alpha: cornerA);
        r.DrawLine((120, 60, 160), (width - 20, height - 20), (width - 20 - cornerSize, height - 20), width: 1, alpha: cornerA);
        r.DrawLine((120, 60, 160), (width - 20, height - 20), (width - 20, height - 20 - cornerSize), width: 1, alpha: cornerA);

        // ─── Spotlight on active player ────────────────────────
        if (turn is int spotSeat)
        {
            var (spotX, spotY) = SeatAnchor(spotSeat, width, height);
            _spotlight.DrawAt(r, spotX, spotY, width, height, Math.Max(40, minDim * 10 / 100));
        }

        // ─── Pile layout — centered draw + discard ────────────
        var (drawRect, discRect) = PilesRects(width, height);

        // Draw pile label with shadow & glow
        r.DrawCircle((200, 160, 80), (drawRect.x + drawRect.w / 2, drawRect.y - 20), 18, alpha: 6);
        r.DrawText("DRAW", drawRect.x + drawRect.w / 2 + 1, drawRect.y - 20 + 1, 11, (0, 0, 0),
            anchorX: "center", anchorY: "center", bold: true, alpha: 60);
        r.DrawText("DRAW", drawRect.x + drawRect.w / 2, drawRect.y - 20, 11, (210, 190, 150),
            anchorX: "center", anchorY: "center", bold: true);

        // Discard pile label
        r.DrawText("DISCARD", discRect.x + discRect.w / 2 + 1, discRect.y - 20 + 1, 11, (0, 0, 0),
            anchorX: "center", anchorY: "center", bold: true, alpha: 60);
        r.DrawText("DISCARD", discRect.x + discRect.w / 2, discRect.y - 20, 11, (210, 190, 150),
            anchorX: "center", anchorY: "center", bold: true);

        // Draw pile — static (no breathing, cleaner look)
        DrawCardBack(r, drawRect, $"🂠 {_drawPile.Count}");

        // Discard pile
        DrawDiscard(r, discRect);

        // ─── Seat zones (player panels) ───────────────────────
        foreach (var s in ActivePlayers)
            DrawSeatZone(r, s, width, height);

        // ─── Last event — premium notification toast ─────────
        if (!string.IsNullOrEmpty(_lastEvent) && _lastEventAge < 4.5 && _winner == null)
        {
            float eventFade = (float)(_lastEventAge < 0.3 ? _lastEventAge / 0.3
                : _lastEventAge > 3.5 ? 1.0 - (_lastEventAge - 3.5) / 1.0
                : 1.0);
            int eventAlpha = (int)(eventFade * 230);
            int ew = Math.Min(width - 40, Math.Max(240, _lastEvent.Length * 9 + 50));
            int eH = 30;
            int ex = cx - ew / 2;
            int ey = hudY + hudH + (_nopeActive ? 50 : 10);

            // Toast shadow
            r.DrawRect((0, 0, 0), (ex + 3, ey + 3, ew, eH), alpha: (int)(eventFade * 100));
            r.DrawRect((0, 0, 0), (ex + 1, ey + 1, ew, eH), alpha: (int)(eventFade * 60));

            // Toast background — dark glass with amber accent
            r.DrawRect((12, 8, 18), (ex, ey, ew, eH), alpha: (int)(eventFade * 220));
            r.DrawRect((255, 180, 40), (ex, ey, ew, 2), alpha: (int)(eventFade * 160));
            r.DrawRect((255, 200, 60), (ex + 1, ey + 2, ew - 2, 1), alpha: (int)(eventFade * 30));
            r.DrawRect((60, 40, 70), (ex, ey, ew, eH), width: 1, alpha: (int)(eventFade * 50));

            // Icon glow
            r.DrawCircle((255, 180, 40), (ex + 16, ey + eH / 2), 8, alpha: (int)(eventFade * 12));

            // Text with shadow
            r.DrawText($"⚡ {_lastEvent}", cx + 1, ey + eH / 2 + 1, 11, (0, 0, 0),
                anchorX: "center", anchorY: "center", alpha: (int)(eventFade * 80));
            r.DrawText($"⚡ {_lastEvent}", cx, ey + eH / 2, 11, (235, 215, 185),
                anchorX: "center", anchorY: "center", alpha: eventAlpha);
        }

        // ─── Winner overlay — cinematic celebration ───────────
        if (_winner is int w)
        {
            // Full-screen dim with vignette
            r.DrawRect((0, 0, 0), (0, 0, width, height), alpha: 180);
            // Edge vignette darkening
            r.DrawRect((0, 0, 0), (0, 0, width, height / 6), alpha: 40);
            r.DrawRect((0, 0, 0), (0, height - height / 6, width, height / 6), alpha: 40);
            r.DrawRect((0, 0, 0), (0, 0, width / 6, height), alpha: 30);
            r.DrawRect((0, 0, 0), (width - width / 6, 0, width / 6, height), alpha: 30);

            // Golden radial burst
            for (int i = 0; i < 16; i++)
            {
                double ang = i * Math.PI / 8;
                int rayLen = Math.Min(width, height) * 40 / 100;
                int rx = cx + (int)(Math.Cos(ang) * rayLen);
                int ry = cy + (int)(Math.Sin(ang) * rayLen);
                r.DrawLine((255, 200, 40), (cx, cy), (rx, ry), width: 2, alpha: 12);
            }
            r.DrawCircle((255, 200, 40), (cx, cy), Math.Min(width, height) * 35 / 100, alpha: 6);
            r.DrawCircle((255, 220, 80), (cx, cy), Math.Min(width, height) * 22 / 100, alpha: 8);

            int bw2 = Math.Min(660, width * 55 / 100), bh2 = 240;
            int bx2 = cx - bw2 / 2, by2 = cy - bh2 / 2;

            // Panel shadow — deep multi-layer
            r.DrawRect((0, 0, 0), (bx2 + 12, by2 + 12, bw2, bh2), alpha: 100);
            r.DrawRect((0, 0, 0), (bx2 + 8, by2 + 8, bw2, bh2), alpha: 60);
            r.DrawRect((0, 0, 0), (bx2 + 4, by2 + 4, bw2, bh2), alpha: 40);

            // Panel background — dark beveled
            BeveledRect.Draw(r, bx2, by2, bw2, bh2, (20, 12, 28), bevelSize: 4);

            // Gold accent double border
            r.DrawRect((255, 200, 40), (bx2, by2, bw2, bh2), width: 3, alpha: 220);
            r.DrawRect((255, 180, 30), (bx2 + 5, by2 + 5, bw2 - 10, bh2 - 10), width: 1, alpha: 80);
            // Top highlight sheen
            r.DrawRect((255, 240, 100), (bx2, by2, bw2, 4), alpha: 180);
            r.DrawRect((255, 220, 80), (bx2 + 1, by2 + 4, bw2 - 2, 2), alpha: 60);

            // Inner glow
            r.DrawCircle((255, 200, 40), (cx, cy), Math.Min(bw2, bh2) * 40 / 100, alpha: 10);
            r.DrawCircle((255, 180, 20), (cx, cy), Math.Min(bw2, bh2) * 25 / 100, alpha: 8);

            // Trophy emoji with glow halo
            r.DrawCircle((255, 220, 80), (cx, by2 + 55), 24, alpha: 14);
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

            // Subtitle with glow
            r.DrawCircle((255, 160, 40), (cx, by2 + 152), 40, alpha: 6);
            r.DrawText("🐱 SURVIVOR! 🐱", cx + 1, by2 + 155 + 1, 20, (0, 0, 0),
                anchorX: "center", anchorY: "center", alpha: 80);
            r.DrawText("🐱 SURVIVOR! 🐱", cx, by2 + 155, 20, (255, 180, 60),
                anchorX: "center", anchorY: "center");

            // Decorative line separators
            int lineW = bw2 * 60 / 100;
            r.DrawLine((255, 200, 40), (cx - lineW / 2, by2 + 88), (cx + lineW / 2, by2 + 88), width: 1, alpha: 40);
            r.DrawLine((255, 200, 40), (cx - lineW / 2, by2 + 175), (cx + lineW / 2, by2 + 175), width: 1, alpha: 35);

            // Corner ornaments on winner panel
            int corSz = 8;
            for (int ci = 0; ci < 4; ci++)
            {
                int ccx = ci < 2 ? bx2 + 10 : bx2 + bw2 - 10;
                int ccy = ci % 2 == 0 ? by2 + 10 : by2 + bh2 - 10;
                r.DrawCircle((255, 200, 40), (ccx, ccy), corSz, width: 1, alpha: 35);
                r.DrawCircle((255, 220, 80), (ccx, ccy), corSz / 2, alpha: 25);
            }

            // Bottom cat emoji row
            r.DrawText("😸", cx - 40, by2 + bh2 - 22, 20, (255, 200, 100),
                anchorX: "center", anchorY: "center");
            r.DrawText("😺", cx, by2 + bh2 - 22, 20, (255, 200, 100),
                anchorX: "center", anchorY: "center");
            r.DrawText("😸", cx + 40, by2 + bh2 - 22, 20, (255, 200, 100),
                anchorX: "center", anchorY: "center");
        }

        // ─── Card fly animations ──────────────────────────────
        foreach (var a in _anims)
            DrawAnim(r, a);



        // ─── Animation overlay layers ─────────────────────────
        _particles.Draw(r);
        foreach (var pr in _pulseRings) pr.Draw(r);
        foreach (var fl in _flashes) fl.Draw(r, width, height);
        foreach (var tp in _textPops) tp.Draw(r);
        foreach (var expl in _explosions) expl.Draw(r);
        _waveBand.Draw(r, width, height);
        _heatShimmer.Draw(r, width, height);
        _vignette.Draw(r, width, height);
    }

    // ─── Drawing helpers ───────────────────────────────────────
    private ((int x, int y, int w, int h), (int x, int y, int w, int h)) PilesRects(int width, int height)
    {
        int cw = Math.Clamp(width * 9 / 100, 78, 110);
        int ch = (int)(cw * 1.42);
        int cxP = width / 2;
        int cyP = height / 2;
        int gap = (int)(cw * 0.9);
        var drawR = (cxP - gap - cw, cyP - ch / 2, cw, ch);
        var discR = (cxP + gap, cyP - ch / 2, cw, ch);
        return (drawR, discR);
    }

    private static (int, int, int) ColorRgb(string kind) => kind switch
    {
        "EK" => (220, 80, 80),
        "DEF" => (80, 200, 130),
        "NOPE" => (120, 120, 120),
        _ => (90, 160, 235),
    };

    private void DrawCardBack(Renderer r, (int x, int y, int w, int h) rect, string label = "")
    {
        int x = rect.x, y = rect.y, w = rect.w, h = rect.h;
        int cx2 = x + w / 2, cy2 = y + h / 2;

        // ── Multi-layer soft shadow — deep 3D float ──
        SoftShadow.Draw(r, x + 5, y + 7, w, h, layers: 6, maxAlpha: 100);

        // ── Card base — 3D beveled ──
        BeveledRect.Draw(r, x, y, w, h, (28, 16, 36), bevelSize: Math.Max(3, w / 22));

        // ── Rich gradient panel — dark velvet base ──
        int bandH = Math.Max(1, h / 16);
        for (int b = 0; b < 16; b++)
        {
            float t = (float)b / 16;
            if (t < 0.25f)
                r.DrawRect((60, 30, 10), (x + 3, y + b * bandH, w - 6, bandH), alpha: (int)(30 * (1f - t / 0.25f)));
            if (t > 0.65f)
                r.DrawRect((0, 0, 0), (x + 3, y + b * bandH, w - 6, bandH), alpha: (int)(30 * ((t - 0.65f) / 0.35f)));
        }

        // ── Subtle noise texture — linen card surface ──
        for (int tx = x + 4; tx < x + w - 4; tx += 5)
            for (int ty = y + 4; ty < y + h - 4; ty += 7)
            {
                int seed = (tx * 71 + ty * 131) & 0xFF;
                if (seed < 35)
                    r.DrawRect((255, 200, 100), (tx, ty, 1, 1), alpha: 3 + (seed & 3));
            }

        // ── Ornate diamond lattice pattern ──
        int dSize = Math.Min(w, h) / 3;
        for (int d = 4; d >= 1; d--)
        {
            int ds = dSize * d / 4;
            var cDiam = d % 2 == 0 ? (240, 170, 50) : (200, 140, 30);
            int dAlpha = 16 + d * 4;
            r.DrawLine(cDiam, (cx2, cy2 - ds), (cx2 + ds, cy2), width: 1, alpha: dAlpha);
            r.DrawLine(cDiam, (cx2 + ds, cy2), (cx2, cy2 + ds), width: 1, alpha: dAlpha);
            r.DrawLine(cDiam, (cx2, cy2 + ds), (cx2 - ds, cy2), width: 1, alpha: dAlpha);
            r.DrawLine(cDiam, (cx2 - ds, cy2), (cx2, cy2 - ds), width: 1, alpha: dAlpha);
        }

        // ── Cross-hatch weave — two layers ──
        for (int i = 0; i < 10; i++)
        {
            int yOff = y + 6 + i * (h - 12) / 9;
            r.DrawLine((240, 180, 60), (x + 6, yOff), (x + w - 6, yOff + (h - 12) / 10), width: 1, alpha: 18);
            r.DrawLine((200, 140, 40), (x + w - 6, yOff), (x + 6, yOff + (h - 12) / 10), width: 1, alpha: 12);
        }

        // ── Central medallion — ornate circle with inner detail ──
        int medR = Math.Max(12, Math.Min(w, h) * 28 / 100);
        r.DrawCircle((0, 0, 0), (cx2 + 2, cy2 + 2), medR, alpha: 30); // shadow
        r.DrawCircle((180, 80, 20), (cx2, cy2), medR, alpha: 45);
        r.DrawCircle((220, 120, 40), (cx2, cy2), medR * 80 / 100, alpha: 25);
        r.DrawCircle((240, 160, 60), (cx2, cy2), medR, width: 2, alpha: 60);
        r.DrawCircle((200, 100, 30), (cx2, cy2), medR * 60 / 100, width: 1, alpha: 35);
        // Inner cat silhouette paw print
        r.DrawCircle((60, 30, 10), (cx2, cy2 - medR / 6), Math.Max(3, medR * 30 / 100), alpha: 35);
        r.DrawCircle((60, 30, 10), (cx2 - medR / 4, cy2 + medR / 6), Math.Max(2, medR / 5), alpha: 30);
        r.DrawCircle((60, 30, 10), (cx2 + medR / 4, cy2 + medR / 6), Math.Max(2, medR / 5), alpha: 30);
        r.DrawCircle((60, 30, 10), (cx2 - medR * 40 / 100, cy2 - medR / 8), Math.Max(2, medR / 6), alpha: 28);
        r.DrawCircle((60, 30, 10), (cx2 + medR * 40 / 100, cy2 - medR / 8), Math.Max(2, medR / 6), alpha: 28);

        // ── Corner ornaments — small accent flourishes ──
        int co = Math.Max(6, w / 8);
        r.DrawCircle((220, 160, 40), (x + co, y + co), Math.Max(2, co / 3), alpha: 35);
        r.DrawCircle((220, 160, 40), (x + w - co, y + co), Math.Max(2, co / 3), alpha: 35);
        r.DrawCircle((220, 160, 40), (x + co, y + h - co), Math.Max(2, co / 3), alpha: 35);
        r.DrawCircle((220, 160, 40), (x + w - co, y + h - co), Math.Max(2, co / 3), alpha: 35);

        // ── Premium border — thick accent with 3D bevel ──
        r.DrawRect((220, 120, 20), (x, y, w, h), width: 3, alpha: 220);
        r.DrawRect((180, 90, 10), (x + 4, y + 4, w - 8, h - 8), width: 1, alpha: 40);
        r.DrawRect((255, 200, 60), (x + 1, y + 1, w - 2, 2), alpha: 55);
        r.DrawRect((255, 180, 40), (x + 1, y + 1, 2, h - 2), alpha: 35);
        r.DrawRect((0, 0, 0), (x + 1, y + h - 3, w - 2, 3), alpha: 50);
        r.DrawRect((0, 0, 0), (x + w - 3, y + 1, 3, h - 2), alpha: 40);

        // ── Glossy shine ──
        GlossyReflection.Draw(r, x, y, w, h, alpha: 16);

        // ── Label text with glow ──
        if (!string.IsNullOrEmpty(label))
        {
            int fs = Math.Max(10, Math.Min(14, h * 10 / 100));
            r.DrawText(label, cx2 + 1, cy2 + h / 4 + 1, fs, (0, 0, 0),
                anchorX: "center", anchorY: "center", bold: true, alpha: 90);
            r.DrawText(label, cx2, cy2 + h / 4, fs, (240, 220, 180),
                anchorX: "center", anchorY: "center", bold: true);
        }
    }

    private void DrawCardFace(Renderer r, (int x, int y, int w, int h) rect, string text, (int, int, int) faceColor, int variant = -1)
    {
        string t = (text ?? "").Trim().ToUpperInvariant();
        CardRendering.DrawEKCard(r, rect, t, fixedVariant: variant);
    }

    private void DrawDiscard(Renderer r, (int x, int y, int w, int h) rect)
    {
        if (_discardPile.Count == 0)
        {
            DrawCardBack(r, rect, "DISCARD");
            return;
        }
        var top = _discardPile[^1];
        DrawCardFace(r, rect, top.Short(), ColorRgb(top.Kind), variant: top.Variant);
    }

    private void DrawSeatZone(Renderer r, int seat, int w, int h)
    {
        var (ax, ay) = SeatAnchor(seat, w, h);
        int count = _hands.GetValueOrDefault(seat)?.Count ?? 0;
        bool isTurn = CurrentTurnSeat == seat;
        bool alive = !_eliminatedPlayers.Contains(seat);
        var pcol = GameConfig.PlayerColors[seat % GameConfig.PlayerColors.Length];

        // Card placeholder rect
        var (rx, ry, rw, rh) = SeatCardTargetRect(seat, w, h);

        // Turn glow — layered warm pulse aura
        if (isTurn && alive)
        {
            // Outer pulse ring
            r.DrawRect((255, 140, 10), (rx - 14, ry - 14, rw + 28, rh + 28), width: 1, alpha: 12);
            r.DrawRect((255, 160, 20), (rx - 10, ry - 10, rw + 20, rh + 20), width: 2, alpha: 28);
            r.DrawRect((255, 180, 40), (rx - 6, ry - 6, rw + 12, rh + 12), width: 3, alpha: 50);
            r.DrawRect((255, 220, 80), (rx - 3, ry - 3, rw + 6, rh + 6), width: 1, alpha: 35);
            // Corner glow spots — bright
            r.DrawCircle((255, 200, 60), (rx - 6, ry - 6), 8, alpha: 25);
            r.DrawCircle((255, 200, 60), (rx + rw + 6, ry - 6), 8, alpha: 25);
            r.DrawCircle((255, 200, 60), (rx - 6, ry + rh + 6), 8, alpha: 25);
            r.DrawCircle((255, 200, 60), (rx + rw + 6, ry + rh + 6), 8, alpha: 25);
        }

        // Dead player dim
        int alphaOverall = alive ? 240 : 100;

        // Panel shadow — deeper
        SoftShadow.Draw(r, rx + 3, ry + 4, rw, rh, layers: 4, maxAlpha: 80);

        // Panel body — dark glass with 3D bevel
        var bg = isTurn ? (32, 20, 14) : (18, 16, 24);
        BeveledRect.Draw(r, rx, ry, rw, rh, bg, bevelSize: 3, alpha: alphaOverall);

        // Subtle gradient inside
        if (alive)
        {
            r.DrawRect(pcol, (rx + 2, ry + 2, rw - 4, rh / 5), alpha: 8);
            r.DrawRect((0, 0, 0), (rx + 2, ry + rh - rh / 5, rw - 4, rh / 5), alpha: 12);
        }

        // Top accent band — player color gradient
        r.DrawRect(pcol, (rx, ry, rw, 6), alpha: alive ? 160 : 35);
        r.DrawRect(pcol, (rx + 2, ry + 6, rw - 4, 2), alpha: alive ? 50 : 12);
        r.DrawRect(pcol, (rx + 4, ry + 8, rw - 8, 1), alpha: alive ? 20 : 5);

        // Border — layered with 3D depth
        var outline = isTurn ? (255, 180, 40) : (alive ? (110, 100, 130) : (55, 50, 65));
        r.DrawRect(outline, (rx, ry, rw, rh), width: isTurn ? 2 : 1, alpha: alphaOverall);
        if (alive)
        {
            r.DrawRect((255, 255, 255), (rx + 1, ry + 1, rw - 2, 1), alpha: 15);
            r.DrawRect((0, 0, 0), (rx + 1, ry + rh - 2, rw - 2, 2), alpha: 35);
            r.DrawRect((0, 0, 0), (rx + rw - 2, ry + 1, 2, rh - 2), alpha: 25);
        }

        // State display
        if (alive)
        {
            // Card count — large embossed number
            int countFs = Math.Max(16, rh * 28 / 100);
            // Shadow
            r.DrawText($"{count}", rx + rw / 2 + 2, ry + rh / 2 - 6 + 2, countFs, (0, 0, 0),
                bold: true, anchorX: "center", anchorY: "center", alpha: 90);
            // Highlight offset
            r.DrawText($"{count}", rx + rw / 2 - 1, ry + rh / 2 - 6 - 1, countFs, (255, 255, 255),
                bold: true, anchorX: "center", anchorY: "center", alpha: 20);
            // Main
            r.DrawText($"{count}", rx + rw / 2, ry + rh / 2 - 6, countFs,
                isTurn ? (255, 220, 100) : (240, 230, 210),
                bold: true, anchorX: "center", anchorY: "center", alpha: alphaOverall);

            // "cards" label
            r.DrawText("cards", rx + rw / 2, ry + rh / 2 + countFs / 2 + 2, 9, (140, 130, 120),
                anchorX: "center", anchorY: "center", alpha: alphaOverall);

            // Card fan with metallic mini-cards
            if (count > 0)
            {
                int fanCount = Math.Min(count, 6);
                int fanTotalW = Math.Min(rw - 16, fanCount * 9);
                int fanStartX = rx + rw / 2 - fanTotalW / 2;
                for (int fi = 0; fi < fanCount; fi++)
                {
                    int fx = fanStartX + fi * (fanTotalW / Math.Max(1, fanCount));
                    int fy = ry + rh - 16;
                    // Mini-card shadow
                    r.DrawRect((0, 0, 0), (fx + 1, fy + 1, 7, 10), alpha: 30);
                    // Mini-card
                    r.DrawRect((220, 160, 40), (fx, fy, 7, 10), alpha: 40);
                    r.DrawRect((240, 180, 60), (fx, fy, 7, 1), alpha: 20);
                    r.DrawRect((180, 120, 20), (fx, fy, 7, 10), width: 1, alpha: 30);
                }
            }
        }
        else
        {
            // Eliminated — skull with red glow
            r.DrawCircle((160, 30, 30), (rx + rw / 2, ry + rh / 2), Math.Max(10, rh * 16 / 100), alpha: 18);
            r.DrawText("💀", rx + rw / 2 + 1, ry + rh / 2 + 1, Math.Max(18, rh * 24 / 100), (0, 0, 0),
                anchorX: "center", anchorY: "center", alpha: 60);
            r.DrawText("💀", rx + rw / 2, ry + rh / 2, Math.Max(18, rh * 24 / 100), (180, 60, 60),
                anchorX: "center", anchorY: "center", alpha: alphaOverall);
        }

        // Player name pill — beveled and polished
        var nameCol = isTurn ? (255, 220, 80) : (alive ? pcol : (80, 70, 90));
        int nameY = seat is 3 or 4 or 5 ? ay + 54 : ay - 54;

        string pName = PlayerName(seat);
        int pillW = Math.Max(64, pName.Length * 8 + 28);
        int pillH = 26;
        int pillX2 = ax - pillW / 2;
        int pillY2 = nameY - pillH / 2;

        // Pill shadows
        r.DrawRect((0, 0, 0), (pillX2 + 3, pillY2 + 3, pillW, pillH), alpha: alive ? 90 : 40);
        r.DrawRect((0, 0, 0), (pillX2 + 2, pillY2 + 2, pillW, pillH), alpha: alive ? 50 : 20);

        // Pill body beveled
        var namePillBg = isTurn ? (34, 24, 12) : (14, 12, 20);
        BeveledRect.Draw(r, pillX2, pillY2, pillW, pillH, namePillBg,
            bevelSize: 2, alpha: alive ? 230 : 100);
        r.DrawRect(outline, (pillX2, pillY2, pillW, pillH), width: 1, alpha: alive ? 90 : 30);
        // Highlight sheen
        r.DrawRect((255, 255, 255), (pillX2 + 2, pillY2 + 1, pillW - 4, 1), alpha: alive ? 15 : 5);

        // Player color indicator
        r.DrawCircle(pcol, (pillX2 + 11, nameY), 5, alpha: alive ? 220 : 70);
        r.DrawCircle((255, 255, 255), (pillX2 + 10, nameY - 1), 2, alpha: alive ? 30 : 10);

        // Name text — shadowed
        string marker = isTurn ? " ★" : "";
        r.DrawText($"{pName}{marker}", ax + 5 + 1, nameY + 1, 11, (0, 0, 0),
            anchorX: "center", anchorY: "center", bold: isTurn, alpha: 80);
        r.DrawText($"{pName}{marker}", ax + 5, nameY, 11, nameCol,
            anchorX: "center", anchorY: "center", bold: isTurn, alpha: alphaOverall);
    }

    private (int x, int y) SeatAnchor(int seat, int w, int h) => seat switch
    {
        0 => (w * 25 / 100, h * 88 / 100),
        1 => (w * 50 / 100, h * 88 / 100),
        2 => (w * 75 / 100, h * 88 / 100),
        3 => (w * 25 / 100, h * 12 / 100),
        4 => (w * 50 / 100, h * 12 / 100),
        5 => (w * 75 / 100, h * 12 / 100),
        6 => (w * 10 / 100, h * 50 / 100),
        7 => (w * 90 / 100, h * 50 / 100),
        _ => (w / 2, h / 2),
    };

    private (int x, int y, int w, int h) SeatCardTargetRect(int seat, int w, int h)
    {
        int cw = Math.Clamp(w * 7 / 100, 58, 90);
        int ch = (int)(cw * 1.42);
        var (ax, ay) = SeatAnchor(seat, w, h);
        return (ax - cw / 2, ay - ch / 2, cw, ch);
    }

    // ─── Card fly animation ────────────────────────────────────
    private void QueueDrawAnim(int seat, float delay = 0f)
    {
        var (drawR, _) = PilesRects(ScreenW, ScreenH);
        var toR = SeatCardTargetRect(seat, ScreenW, ScreenH);
        _anims.Add(new CardAnim("draw", drawR, toR, 0.28f, delay: delay));
    }

    private void QueuePlayAnim(int seat, EKCard card)
    {
        var (_, discR) = PilesRects(ScreenW, ScreenH);
        var fromR = SeatCardTargetRect(seat, ScreenW, ScreenH);
        int stableVariant = card.Variant;

        // Phase 1: fly from seat to center screen and enlarge (showcase)
        int showW = Math.Min(ScreenW * 18 / 100, 180);
        int showH = (int)(showW * 1.42);
        int showX = ScreenW / 2 - showW / 2;
        int showY = ScreenH / 2 - showH / 2;
        var showRect = (showX, showY, showW, showH);
        _anims.Add(new CardAnim("play", fromR, showRect, 0.3f,
            label: card.Short(), faceColor: ColorRgb(card.Kind), variant: stableVariant,
            holdTime: 0.7f, finalRect: discR));
    }

    private void DrawAnim(Renderer r, CardAnim a)
    {
        float rawT = a.Elapsed - a.Delay;
        if (rawT < 0) return;

        if (a.Kind == "draw")
        {
            float u = a.Duration <= 0 ? 1f : Math.Clamp(rawT / a.Duration, 0f, 1f);
            float u2 = 1f - (1f - u) * (1f - u) * (1f - u);
            int dx = (int)(a.FromRect.x + (a.ToRect.x - a.FromRect.x) * u2);
            int dy = (int)(a.FromRect.y + (a.ToRect.y - a.FromRect.y) * u2);
            int dw = (int)(a.FromRect.w + (a.ToRect.w - a.FromRect.w) * u2);
            int dh = (int)(a.FromRect.h + (a.ToRect.h - a.FromRect.h) * u2);
            DrawCardBack(r, (dx, dy, dw, dh));
            return;
        }

        // Play animation: 3 phases — fly to center, hold, fly to discard
        float phase1Dur = a.Duration;  // fly to showcase position
        float phase2Dur = a.HoldTime;  // hold at center
        float phase3Dur = 0.25f;       // fly to discard pile

        if (rawT < phase1Dur)
        {
            // Phase 1: fly from seat to center, ease-out
            float u = Math.Clamp(rawT / phase1Dur, 0f, 1f);
            float u2 = 1f - (1f - u) * (1f - u) * (1f - u);
            int px = (int)(a.FromRect.x + (a.ToRect.x - a.FromRect.x) * u2);
            int py = (int)(a.FromRect.y + (a.ToRect.y - a.FromRect.y) * u2);
            int pw = (int)(a.FromRect.w + (a.ToRect.w - a.FromRect.w) * u2);
            int ph = (int)(a.FromRect.h + (a.ToRect.h - a.FromRect.h) * u2);

            // Background dim during flight toward showcase
            int dimA = (int)(60 * u2);
            r.DrawRect((0, 0, 0), (0, 0, ScreenW, ScreenH), alpha: dimA);

            DrawCardFace(r, (px, py, pw, ph), a.Label, a.FaceColor, variant: a.Variant);
        }
        else if (rawT < phase1Dur + phase2Dur)
        {
            // Phase 2: hold at showcase size — dim background, show card
            r.DrawRect((0, 0, 0), (0, 0, ScreenW, ScreenH), alpha: 60);

            // Subtle glow behind the held card
            int gcx = a.ToRect.x + a.ToRect.w / 2;
            int gcy = a.ToRect.y + a.ToRect.h / 2;
            r.DrawCircle(a.FaceColor, (gcx, gcy), a.ToRect.w, alpha: 8);
            r.DrawCircle(a.FaceColor, (gcx, gcy), a.ToRect.w * 70 / 100, alpha: 6);

            DrawCardFace(r, a.ToRect, a.Label, a.FaceColor, variant: a.Variant);
        }
        else
        {
            // Phase 3: fly from showcase to discard pile, ease-in
            float u = Math.Clamp((rawT - phase1Dur - phase2Dur) / phase3Dur, 0f, 1f);
            float u2 = u * u; // ease-in quadratic

            var fin = a.FinalRect ?? a.ToRect;
            int px = (int)(a.ToRect.x + (fin.x - a.ToRect.x) * u2);
            int py = (int)(a.ToRect.y + (fin.y - a.ToRect.y) * u2);
            int pw = (int)(a.ToRect.w + (fin.w - a.ToRect.w) * u2);
            int ph = (int)(a.ToRect.h + (fin.h - a.ToRect.h) * u2);

            // Fade out the dim
            int dimA = (int)(60 * (1f - u2));
            if (dimA > 0) r.DrawRect((0, 0, 0), (0, 0, ScreenW, ScreenH), alpha: dimA);

            DrawCardFace(r, (px, py, pw, ph), a.Label, a.FaceColor, variant: a.Variant);
        }
    }

    // ─── Animation data class ──────────────────────────────────
    private class CardAnim
    {
        public string Kind;
        public (int x, int y, int w, int h) FromRect;
        public (int x, int y, int w, int h) ToRect;
        public float Duration;
        public float Elapsed;
        public float Delay;
        public string Label;
        public (int, int, int) FaceColor;
        public int Variant;
        public float HoldTime;  // time to hold at showcase position
        public (int x, int y, int w, int h)? FinalRect; // final destination after hold

        public float TotalDuration => Duration + HoldTime + (FinalRect.HasValue ? 0.25f : 0f);

        public CardAnim(string kind,
            (int x, int y, int w, int h) from,
            (int x, int y, int w, int h) to,
            float duration,
            float delay = 0f,
            string label = "",
            (int, int, int)? faceColor = null,
            int variant = -1,
            float holdTime = 0f,
            (int, int, int, int)? finalRect = null)
        {
            Kind = kind;
            FromRect = from;
            ToRect = to;
            Duration = duration;
            Elapsed = 0f;
            Delay = delay;
            Label = label;
            FaceColor = faceColor ?? (160, 160, 160);
            Variant = variant;
            HoldTime = holdTime;
            FinalRect = finalRect;
        }
    }
}
