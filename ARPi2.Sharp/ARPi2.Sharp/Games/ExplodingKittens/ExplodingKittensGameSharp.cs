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
    /// <summary>Card kind: EK, DEF, ATK, SKIP, SHUF, FUT, FAV, NOPE</summary>
    public string Kind { get; }

    public EKCard(string kind) => Kind = kind;

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
    private string _lastEvent = "";
    private double _lastEventAge = 999.0;
    private int? _animPrevTurn;
    private int? _animPrevWinner;
    private double _animFwTimer;

    // Simple card-fly animations (draw/play)
    private readonly List<CardAnim> _anims = new();

    public ExplodingKittensGameSharp(int w, int h, Renderer renderer) : base(w, h, renderer) { }

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
                    _textPops.Add(new TextPopAnim($"\U0001f9f0 DEFUSED! {PlayerName(seat)}", cx, cy - 40, (80, 230, 130), fontSize: 30));
                    _particles.EmitSparkle(cx, cy, (80, 230, 130), 22);
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
            _textPops.Add(new TextPopAnim($"\U0001f4a5 KABOOM! {PlayerName(seat)}", cx, cy - 50, (255, 90, 40), fontSize: 36));
            for (int i = 0; i < 6; i++)
            {
                _particles.EmitFirework(
                    cx + Rng.Next(-140, 141), cy + Rng.Next(-90, 91),
                    new[] { (220, 60, 20), (255, 140, 0), (255, 220, 0) });
            }
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
        btns["ek_draw"] = ("Draw", isTurn && _pendingDraws > 0);
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

        // Card fly animations
        for (int i = _anims.Count - 1; i >= 0; i--)
        {
            _anims[i].Elapsed += d;
            if (_anims[i].Elapsed - _anims[i].Delay >= _anims[i].Duration)
                _anims.RemoveAt(i);
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
        if (State == "player_select") { base.Draw(r, width, height, dt); return; }

        CardRendering.DrawGameBackground(r, width, height, "exploding_kittens");
        int cx = width / 2, cy = height / 2;

        // Title
        RainbowTitle.Draw(r, "EXPLODING KITTENS", width);

        // Status line
        var turn = CurrentTurnSeat;
        string status = turn is int t
            ? $"Turn: {PlayerName(t)}"
            : "Turn: \u2014";
        string topDiscard = _discardPile.Count > 0 ? _discardPile[^1].Short() : "\u2014";
        r.DrawText($"Deck: {_drawPile.Count}  \u00b7  Discard: {topDiscard}  \u00b7  {status}  \u00b7  Draws: {_pendingDraws}",
            24, 54, 14, (200, 200, 200), anchorX: "left", anchorY: "top");

        // Piles
        var (drawRect, discRect) = PilesRects(width, height);

        // Subtle table highlight
        try
        {
            r.DrawCircle((80, 30, 100), (cx, cy), Math.Min(width, height) * 18 / 100, alpha: 20);
            r.DrawCircle((140, 60, 180), (cx, cy), Math.Min(width, height) * 12 / 100, alpha: 15);
        }
        catch { }

        // Draw pile
        DrawCardBack(r, drawRect, $"DECK {_drawPile.Count}");

        // Discard pile
        DrawDiscard(r, discRect);

        // Seat zones
        foreach (var s in ActivePlayers)
            DrawSeatZone(r, s, width, height);

        // Winner overlay
        if (_winner is int w)
        {
            r.DrawRect((0, 0, 0), (0, 0, width, height), alpha: 150);
            int bw2 = Math.Min(600, width * 55 / 100), bh2 = 160;
            int bx2 = cx - bw2 / 2, by2 = cy - bh2 / 2;
            r.DrawRect((0, 0, 0), (bx2 + 5, by2 + 5, bw2, bh2), alpha: 100);
            r.DrawRect((18, 10, 24), (bx2, by2, bw2, bh2), alpha: 225);
            r.DrawRect((255, 180, 40), (bx2, by2, bw2, bh2), width: 4, alpha: 200);
            r.DrawCircle((255, 180, 40), (cx, cy), Math.Min(bw2, bh2) * 30 / 100, alpha: 12);
            r.DrawText("\U0001f63c", cx, by2 + bh2 - 30, 48, (255, 200, 60), anchorX: "center", anchorY: "center");
            r.DrawText($"Winner: {PlayerName(w)}", cx + 2, by2 + 40, 40, (0, 0, 0),
                anchorX: "center", anchorY: "center", alpha: 100);
            r.DrawText($"Winner: {PlayerName(w)}", cx, by2 + 38, 40, (255, 240, 180),
                anchorX: "center", anchorY: "center");
        }

        // Last event (hide during winner to avoid overlap)
        if (!string.IsNullOrEmpty(_lastEvent) && _lastEventAge < 4.5 && _winner == null)
        {
            int ew = Math.Max(180, _lastEvent.Length * 8);
            r.DrawRect((0, 0, 0), (20, 74, ew, 22), alpha: 120);
            r.DrawRect((200, 140, 255), (20, 74, ew, 22), width: 1, alpha: 40);
            r.DrawText(_lastEvent, 28, 85, 12, (210, 200, 230), anchorX: "left", anchorY: "center");
        }

        // Card fly animations
        foreach (var a in _anims)
            DrawAnim(r, a);

        // Animation layers
        _particles.Draw(r);
        foreach (var pr in _pulseRings) pr.Draw(r);
        foreach (var fl in _flashes) fl.Draw(r, width, height);
        foreach (var tp in _textPops) tp.Draw(r);
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
        // Shadow
        r.DrawRect((0, 0, 0), (x + 4, y - 4, w, h), alpha: 70);
        // Face
        r.DrawRect((28, 20, 38), (x, y, w, h), alpha: 235);
        r.DrawRect((200, 140, 255), (x, y, w, h), width: 2, alpha: 210);
        r.DrawLine((240, 200, 90), (x + 10, y + 12), (x + w - 10, y + h - 12), width: 2, alpha: 160);
        if (!string.IsNullOrEmpty(label))
            r.DrawText(label, x + w / 2, y + h / 2, 12, (230, 230, 230), anchorX: "center", anchorY: "center");
    }

    private void DrawCardFace(Renderer r, (int x, int y, int w, int h) rect, string text, (int, int, int) faceColor)
    {
        string t = (text ?? "").Trim().ToUpperInvariant();

        // Emoji + title mapping
        string emoji = "\U0001f63a";
        string title = t;
        switch (t)
        {
            case "EK":   emoji = "\U0001f4a3\U0001f63c"; title = "EXPLODING"; break;
            case "DEF":  emoji = "\U0001f9ef";           title = "DEFUSE"; break;
            case "ATK":  emoji = "\u2694";               title = "ATTACK"; break;
            case "SKIP": emoji = "\u23ed";               title = "SKIP"; break;
            case "SHUF": emoji = "\U0001f500";           title = "SHUFFLE"; break;
            case "FUT":  emoji = "\U0001f52e";           title = "FUTURE"; break;
            case "FAV":  emoji = "\U0001f381";           title = "FAVOR"; break;
            case "NOPE": emoji = "\U0001f6ab";           title = "NOPE"; break;
        }

        CardRendering.DrawEmojiCard(r, rect, emoji, title, accentRgb: faceColor, corner: string.IsNullOrEmpty(t) ? "EK" : t);
    }

    private void DrawDiscard(Renderer r, (int x, int y, int w, int h) rect)
    {
        if (_discardPile.Count == 0)
        {
            DrawCardBack(r, rect, "DISCARD");
            return;
        }
        var top = _discardPile[^1];
        DrawCardFace(r, rect, top.Short(), ColorRgb(top.Kind));
        r.DrawText("DISCARD", rect.x + rect.w / 2, rect.y - 18, 10, (200, 200, 200),
            anchorX: "center", anchorY: "top");
    }

    private void DrawSeatZone(Renderer r, int seat, int w, int h)
    {
        var (ax, ay) = SeatAnchor(seat, w, h);
        int count = _hands.GetValueOrDefault(seat)?.Count ?? 0;
        bool isTurn = CurrentTurnSeat == seat;
        var pcol = GameConfig.PlayerColors[seat % GameConfig.PlayerColors.Length];

        // Card placeholder
        var (rx, ry, rw, rh) = SeatCardTargetRect(seat, w, h);
        r.DrawRect((0, 0, 0), (rx + 3, ry - 3, rw, rh), alpha: 70);
        var bg = isTurn ? (28, 16, 36) : (18, 18, 24);
        r.DrawRect(bg, (rx, ry, rw, rh), alpha: 190);
        var outline = isTurn ? (250, 200, 70) : (140, 120, 160);
        if (isTurn) r.DrawRect(outline, (rx - 2, ry - 2, rw + 4, rh + 4), width: 2, alpha: 50);
        r.DrawRect(outline, (rx, ry, rw, rh), width: isTurn ? 2 : 1, alpha: 200);
        r.DrawText(count.ToString(), rx + rw / 2, ry + rh / 2 - 4, 16, (240, 240, 240),
            bold: true, anchorX: "center", anchorY: "center");

        // Player name with color dot
        var nameCol = isTurn ? (250, 220, 100) : pcol;
        int nameY = seat is 3 or 4 or 5 ? ay + 42 : ay - 42;
        r.DrawCircle(pcol, (ax - 40, nameY), 4, alpha: 180);
        string marker = isTurn ? "  \u2605" : "";
        r.DrawText($"{PlayerName(seat)}{marker}", ax, nameY, 12, nameCol,
            anchorX: "center", anchorY: "center");
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
        _anims.Add(new CardAnim("play", fromR, discR, 0.24f, label: card.Short(), faceColor: ColorRgb(card.Kind)));
    }

    private void DrawAnim(Renderer r, CardAnim a)
    {
        float t = a.Elapsed - a.Delay;
        if (t < 0) return;
        float u = a.Duration <= 0 ? 1f : Math.Clamp(t / a.Duration, 0f, 1f);
        float u2 = 1f - (1f - u) * (1f - u) * (1f - u); // ease-out cubic

        int x = (int)(a.FromRect.x + (a.ToRect.x - a.FromRect.x) * u2);
        int y = (int)(a.FromRect.y + (a.ToRect.y - a.FromRect.y) * u2);
        int w = (int)(a.FromRect.w + (a.ToRect.w - a.FromRect.w) * u2);
        int h = (int)(a.FromRect.h + (a.ToRect.h - a.FromRect.h) * u2);
        var rect = (x, y, w, h);

        if (a.Kind == "draw")
            DrawCardBack(r, rect);
        else
            DrawCardFace(r, rect, a.Label, a.FaceColor);
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

        public CardAnim(string kind,
            (int x, int y, int w, int h) from,
            (int x, int y, int w, int h) to,
            float duration,
            float delay = 0f,
            string label = "",
            (int, int, int)? faceColor = null)
        {
            Kind = kind;
            FromRect = from;
            ToRect = to;
            Duration = duration;
            Elapsed = 0f;
            Delay = delay;
            Label = label;
            FaceColor = faceColor ?? (160, 160, 160);
        }
    }
}
