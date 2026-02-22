using System;
using System.Collections.Generic;
using System.Linq;
using ARPi2.Sharp.Core;

namespace ARPi2.Sharp.Games.Uno;

// ════════════════════════════════════════════════════════════════
//  Data types
// ════════════════════════════════════════════════════════════════
public class UnoCard
{
    public string? Color { get; set; } // "R","G","B","Y" or null for wild
    public string Value { get; set; } = "0"; // "0"-"9","skip","reverse","draw2","wild","wild_draw4"

    public string Short()
    {
        if (Value == "wild") return "WILD";
        if (Value == "wild_draw4") return "WILD+4";
        if (Color == null) return Value;
        var sym = Value switch
        {
            "skip" => "SKIP",
            "reverse" => "REV",
            "draw2" => "+2",
            _ => Value,
        };
        return $"{Color}{sym}";
    }
}

// ════════════════════════════════════════════════════════════════
//  UnoGame — full port from Python
// ════════════════════════════════════════════════════════════════
public class UnoGameSharp : BaseGame
{
    public override string ThemeName => "uno";

    // Game state
    private int _currentPlayerIdx;
    private int _direction = 1;
    private readonly Dictionary<int, List<UnoCard>> _hands = new();
    private List<UnoCard> _drawPile = new();
    private readonly List<UnoCard> _discardPile = new();
    private string? _currentColor;
    private bool _drewThisTurn;
    private bool _awaitingColorChoice;
    private int? _awaitingColorPlayer;
    private int? _winner;

    // Next-round readiness
    private readonly Dictionary<int, bool> _nextRoundReady = new();

    // Hand pagination
    private readonly Dictionary<int, int> _handPage = new();

    // Buttons per player
    private readonly Dictionary<int, Dictionary<string, (string Text, bool Enabled)>> _buttons = new();

    // Animations
    private readonly ParticleSystem _particles = new();
    private readonly List<TextPopAnim> _textPops = new();
    private readonly List<PulseRing> _pulseRings = new();
    private readonly List<ScreenFlash> _flashes = new();
    private readonly List<CardFlyAnim> _cardFlies = new();
    private string _lastEvent = "";
    private double _lastEventAge = 999.0;
    private int? _animPrevTurn;
    private int? _animPrevWinner;
    private double _animFwTimer;

    public UnoGameSharp(int w, int h, Renderer renderer) : base(w, h, renderer) { }

    // ─── Top card & current turn ───────────────────────────────
    private UnoCard? TopCard => _discardPile.Count > 0 ? _discardPile[^1] : null;

    private int? CurrentTurnSeat
    {
        get
        {
            if (ActivePlayers.Count == 0) return null;
            int idx = (((_currentPlayerIdx % ActivePlayers.Count) + ActivePlayers.Count) % ActivePlayers.Count);
            return ActivePlayers[idx];
        }
    }

    // ─── Start game ────────────────────────────────────────────
    public override void StartGame(List<int> players)
    {
        var seats = players.Where(s => s >= 0 && s <= 7).Distinct().OrderBy(x => x).ToList();
        if (seats.Count < 2) return;

        ActivePlayers = seats;
        _currentPlayerIdx = 0;
        _direction = 1;
        _hands.Clear();
        _handPage.Clear();
        foreach (var s in seats)
        {
            _hands[s] = new List<UnoCard>();
            _handPage[s] = 0;
        }

        _drawPile = BuildDeck();
        ShuffleList(_drawPile);
        _discardPile.Clear();
        _currentColor = null;
        _drewThisTurn = false;
        _awaitingColorChoice = false;
        _awaitingColorPlayer = null;
        _winner = null;
        _nextRoundReady.Clear();

        // Deal 7 each
        for (int round = 0; round < 7; round++)
            foreach (var s in seats)
                DrawToHand(s, 1);

        // Flip start card (non-wild)
        UnoCard? top = DrawPilePopNonWild();
        if (top == null) top = new UnoCard { Color = "R", Value = "0" };
        _discardPile.Add(top);
        _currentColor = top.Color;

        NoteEvent($"Start: {top.Short()}");
        ApplyCardEffect(top, playedBy: null);

        State = "playing";
        RebuildButtons();
    }

    // ─── Handle player quit ────────────────────────────────────
    public void HandlePlayerQuit(int seat)
    {
        if (State != "playing" || _winner != null) return;
        if (!ActivePlayers.Contains(seat)) return;

        bool wasTurn = CurrentTurnSeat == seat;

        if (_awaitingColorChoice && _awaitingColorPlayer == seat)
        {
            _awaitingColorChoice = false;
            _awaitingColorPlayer = null;
            _currentColor = new[] { "R", "G", "B", "Y" }[Rng.Next(4)];
        }

        var hand = _hands.GetValueOrDefault(seat);
        if (hand != null)
        {
            _drawPile.AddRange(hand);
            ShuffleList(_drawPile);
            _hands.Remove(seat);
        }

        int removedIdx = ActivePlayers.IndexOf(seat);
        ActivePlayers.Remove(seat);
        _nextRoundReady.Remove(seat);
        _handPage.Remove(seat);

        if (ActivePlayers.Count == 0)
        {
            State = "player_select";
            _currentPlayerIdx = 0;
            RebuildButtons();
            return;
        }

        if (ActivePlayers.Count == 1)
        {
            _winner = ActivePlayers[0];
            NoteEvent($"Winner: {PlayerName(_winner.Value)}");
            RebuildButtons();
            return;
        }

        if (removedIdx >= 0)
        {
            if (removedIdx < _currentPlayerIdx)
                _currentPlayerIdx = Math.Max(0, _currentPlayerIdx - 1);
            if (wasTurn)
                _currentPlayerIdx = removedIdx % ActivePlayers.Count;
        }

        if (_currentPlayerIdx >= ActivePlayers.Count)
            _currentPlayerIdx = 0;

        if (wasTurn) _drewThisTurn = false;

        NoteEvent($"{PlayerName(seat)} quit");
        RebuildButtons();
    }

    // ─── HandleClick (web UI) ──────────────────────────────────
    public override void HandleClick(int playerIdx, string buttonId)
    {
        if (State != "playing") return;

        // Winner screen: play_again / force_start
        if (_winner != null)
        {
            if (!ActivePlayers.Contains(playerIdx)) return;

            if (buttonId == "play_again")
            {
                _nextRoundReady[playerIdx] = true;
                if (_nextRoundReady.Count(kv => kv.Value && ActivePlayers.Contains(kv.Key)) >= ActivePlayers.Count)
                    StartGame(ActivePlayers);
                return;
            }
            if (buttonId == "force_start")
            {
                var readyPlayers = ActivePlayers.Where(s => _nextRoundReady.GetValueOrDefault(s, false)).ToList();
                if (readyPlayers.Count >= 2) StartGame(readyPlayers);
                return;
            }
            return;
        }

        // Color choice
        if (_awaitingColorChoice)
        {
            if (playerIdx != _awaitingColorPlayer) return;
            if (buttonId.StartsWith("color:") && buttonId.Length > 6)
            {
                string col = buttonId[6..];
                if (col is "R" or "G" or "B" or "Y")
                {
                    _currentColor = col;
                    _awaitingColorChoice = false;
                    _awaitingColorPlayer = null;

                    // Color change flash
                    try
                    {
                        var flashCol = col switch
                        {
                            "R" => ((int, int, int))(220, 50, 50),
                            "B" => (50, 90, 220),
                            "G" => (40, 180, 60),
                            "Y" => (230, 200, 30),
                            _ => (200, 200, 200),
                        };
                        int ccx = ScreenW / 2, ccy = ScreenH / 2;
                        _flashes.Add(new ScreenFlash(flashCol, 35, 0.35f));
                        _pulseRings.Add(new PulseRing(ccx, ccy, flashCol, maxRadius: 70, duration: 0.6f));
                    }
                    catch { }

                    EndTurn();
                    RebuildButtons();
                    return;
                }
            }
            return;
        }

        // Pagination
        if (buttonId == "page_prev")
        {
            _handPage[playerIdx] = Math.Max(0, _handPage.GetValueOrDefault(playerIdx) - 1);
            RebuildButtons();
            return;
        }
        if (buttonId == "page_next")
        {
            _handPage[playerIdx] = _handPage.GetValueOrDefault(playerIdx) + 1;
            RebuildButtons();
            return;
        }

        // Must be this player's turn for play/draw/end
        if (playerIdx != CurrentTurnSeat) return;

        // Play a card
        if (buttonId.StartsWith("play:"))
        {
            if (int.TryParse(buttonId.AsSpan(5), out int cardIdx))
            {
                var hand = _hands.GetValueOrDefault(playerIdx);
                if (hand == null || cardIdx < 0 || cardIdx >= hand.Count) return;
                var card = hand[cardIdx];
                if (!IsPlayable(card)) return;

                // Play it
                hand.RemoveAt(cardIdx);
                _discardPile.Add(card);
                NoteEvent($"{PlayerName(playerIdx)} played {card.Short()}");

                // Card fly animation from player to discard pile
                try
                {
                    var (sx, sy) = SeatAnchor(playerIdx, ScreenW, ScreenH);
                    int dcx = ScreenW / 2 + 10, dcy = ScreenH / 2; // approx discard pile center
                    var cardColor = card.Color switch
                    {
                        "red" => (220, 50, 50),
                        "blue" => (50, 90, 220),
                        "green" => (40, 180, 60),
                        "yellow" => (230, 200, 30),
                        _ => (60, 60, 60),
                    };
                    _cardFlies.Add(new CardFlyAnim((sx, sy), (dcx, dcy), color: cardColor, duration: 0.45f));
                }
                catch { }

                // Set color
                if (card.Value is "wild" or "wild_draw4")
                {
                    _currentColor = null;
                    _awaitingColorChoice = true;
                    _awaitingColorPlayer = playerIdx;
                }
                else
                {
                    _currentColor = card.Color;
                }

                // Win check
                if (hand.Count == 0)
                {
                    _winner = playerIdx;
                    _nextRoundReady.Clear();
                    foreach (var s in ActivePlayers)
                        _nextRoundReady[s] = false;
                    RebuildButtons();
                    return;
                }

                // UNO alert
                if (hand.Count == 1)
                {
                    try
                    {
                        int cx = ScreenW / 2, cy = ScreenH / 2;
                        var col = GameConfig.PlayerColors[playerIdx % GameConfig.PlayerColors.Length];
                        _textPops.Add(new TextPopAnim("\U0001f6a8 UNO!", cx, cy - 50, col, fontSize: 40));
                        _flashes.Add(new ScreenFlash((220, 60, 60), 45, 0.4f));
                        _pulseRings.Add(new PulseRing(cx, cy, col, maxRadius: 90, duration: 0.8f));
                    }
                    catch { }
                }

                // Apply effects
                ApplyCardEffect(card, playedBy: playerIdx);

                if (!_awaitingColorChoice)
                    EndTurn();

                _drewThisTurn = false;
                RebuildButtons();
                return;
            }
        }

        // Draw
        if (buttonId == "draw")
        {
            if (!_drewThisTurn)
            {
                DrawToHand(playerIdx, 1);
                _drewThisTurn = true;
                NoteEvent($"{PlayerName(playerIdx)} drew a card");
                RebuildButtons();
            }
            return;
        }

        // End turn
        if (buttonId == "end")
        {
            if (_drewThisTurn && !HasPlayableCard(playerIdx))
            {
                EndTurn();
                _drewThisTurn = false;
                RebuildButtons();
            }
            return;
        }
    }

    // ─── Snapshot ──────────────────────────────────────────────
    public override Dictionary<string, object?> GetSnapshot(int playerIdx)
    {
        int seat = playerIdx;
        var hand = _hands.GetValueOrDefault(seat, new List<UnoCard>());
        bool isTurn = seat == CurrentTurnSeat && _winner == null;

        var counts = new Dictionary<string, object?>();
        foreach (var s in ActivePlayers)
            counts[s.ToString()] = _hands.GetValueOrDefault(s)?.Count ?? 0;

        var readyMap = new Dictionary<string, object?>();
        foreach (var s in ActivePlayers)
            readyMap[s.ToString()] = _nextRoundReady.GetValueOrDefault(s, false);

        int readyCount = ActivePlayers.Count(s => _nextRoundReady.GetValueOrDefault(s, false));

        var yourHand = hand.Select((c, i) => (Dictionary<string, object?>)new Dictionary<string, object?>
        {
            ["idx"] = i,
            ["text"] = c.Short(),
            ["playable"] = isTurn && IsPlayable(c),
        }).ToList();

        var snap = new Dictionary<string, object?>
        {
            ["state"] = State,
            ["active_players"] = ActivePlayers.ToList(),
            ["current_turn_seat"] = CurrentTurnSeat,
            ["direction"] = _direction,
            ["current_color"] = _currentColor,
            ["top_card"] = TopCard?.Short(),
            ["hand_counts"] = counts,
            ["your_hand"] = yourHand,
            ["winner"] = _winner,
            ["awaiting_color"] = _awaitingColorChoice && _awaitingColorPlayer == seat,
            ["next_round_ready"] = readyMap,
            ["next_round_ready_count"] = readyCount,
            ["next_round_total"] = ActivePlayers.Count,
        };

        return new Dictionary<string, object?> { ["uno"] = snap };
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

    // ─── Internals ─────────────────────────────────────────────
    private List<UnoCard> BuildDeck()
    {
        var deck = new List<UnoCard>();
        var colors = new[] { "R", "G", "B", "Y" };
        foreach (var c in colors)
        {
            deck.Add(new UnoCard { Color = c, Value = "0" });
            for (int n = 1; n <= 9; n++)
            {
                deck.Add(new UnoCard { Color = c, Value = n.ToString() });
                deck.Add(new UnoCard { Color = c, Value = n.ToString() });
            }
            for (int i = 0; i < 2; i++)
            {
                deck.Add(new UnoCard { Color = c, Value = "skip" });
                deck.Add(new UnoCard { Color = c, Value = "reverse" });
                deck.Add(new UnoCard { Color = c, Value = "draw2" });
            }
        }
        for (int i = 0; i < 4; i++)
        {
            deck.Add(new UnoCard { Color = null, Value = "wild" });
            deck.Add(new UnoCard { Color = null, Value = "wild_draw4" });
        }
        return deck;
    }

    private void RefillFromDiscard()
    {
        if (_discardPile.Count <= 1) return;
        var top = _discardPile[^1];
        var rest = _discardPile.GetRange(0, _discardPile.Count - 1);
        _discardPile.Clear();
        _discardPile.Add(top);
        ShuffleList(rest);
        _drawPile.AddRange(rest);
    }

    private UnoCard? DrawPilePop()
    {
        if (_drawPile.Count == 0) RefillFromDiscard();
        if (_drawPile.Count == 0) return null;
        var c = _drawPile[^1];
        _drawPile.RemoveAt(_drawPile.Count - 1);
        return c;
    }

    private UnoCard? DrawPilePopNonWild()
    {
        for (int i = 0; i < 200; i++)
        {
            var c = DrawPilePop();
            if (c == null) return null;
            if (c.Value is not "wild" and not "wild_draw4") return c;
            _drawPile.Insert(0, c);
        }
        return DrawPilePop();
    }

    private void DrawToHand(int seat, int n)
    {
        var hand = _hands.GetValueOrDefault(seat);
        if (hand == null)
        {
            hand = new List<UnoCard>();
            _hands[seat] = hand;
        }
        for (int i = 0; i < n; i++)
        {
            var c = DrawPilePop();
            if (c == null) break;
            hand.Add(c);
        }
    }

    private void AdvanceIndex(int steps = 1)
    {
        if (ActivePlayers.Count == 0) return;
        _currentPlayerIdx = ((_currentPlayerIdx + steps * _direction) % ActivePlayers.Count + ActivePlayers.Count) % ActivePlayers.Count;
    }

    private void EndTurn()
    {
        _drewThisTurn = false;
        AdvanceIndex(1);
    }

    private bool IsPlayable(UnoCard card)
    {
        var top = TopCard;
        if (top == null) return true;
        if (card.Value is "wild" or "wild_draw4") return true;
        if (_currentColor != null && card.Color == _currentColor) return true;
        if (card.Value == top.Value && card.Color != null) return true;
        return false;
    }

    private bool HasPlayableCard(int seat)
    {
        var hand = _hands.GetValueOrDefault(seat);
        if (hand == null) return false;
        return hand.Any(c => IsPlayable(c));
    }

    private void ApplyCardEffect(UnoCard card, int? playedBy)
    {
        int cx = ScreenW / 2, cy = ScreenH / 2;

        if (card.Value == "reverse")
        {
            if (ActivePlayers.Count == 2)
                AdvanceIndex(1); // acts like skip in 2-player
            else
                _direction *= -1;

            try
            {
                string arrow = _direction >= 0 ? "→" : "←";
                _textPops.Add(new TextPopAnim($"🔄 REVERSE {arrow}", cx, cy - 30, (255, 175, 60), fontSize: 28));
                _flashes.Add(new ScreenFlash((255, 175, 60), 45, 0.35f));
                _particles.EmitSparkle(cx, cy, (255, 175, 60), 16);
            }
            catch { }
        }
        else if (card.Value == "skip")
        {
            AdvanceIndex(1);
            try
            {
                _textPops.Add(new TextPopAnim("⏭ SKIP!", cx, cy - 30, (230, 80, 80), fontSize: 28));
                _flashes.Add(new ScreenFlash((230, 80, 80), 45, 0.35f));
            }
            catch { }
        }
        else if (card.Value == "draw2")
        {
            AdvanceIndex(1);
            int? victim = CurrentTurnSeat;
            if (victim is int v)
            {
                NoteEvent($"{PlayerName(v)} drew +2");
                DrawToHand(v, 2);
                AdvanceIndex(1);
            }
            try
            {
                _textPops.Add(new TextPopAnim("+2 Cards! 🃏", cx, cy - 30, (80, 160, 235), fontSize: 28));
                _flashes.Add(new ScreenFlash((80, 140, 230), 40, 0.35f));
                _particles.EmitSparkle(cx, cy, (80, 160, 235), 16);
            }
            catch { }
        }
        else if (card.Value == "wild_draw4")
        {
            AdvanceIndex(1);
            int? victim = CurrentTurnSeat;
            if (victim is int v)
            {
                NoteEvent($"{PlayerName(v)} drew +4");
                DrawToHand(v, 4);
                AdvanceIndex(1);
            }
            try
            {
                _textPops.Add(new TextPopAnim("+4 Cards! 🃏", cx, cy - 30, (200, 90, 220), fontSize: 28));
                _flashes.Add(new ScreenFlash((160, 60, 200), 40, 0.35f));
                _particles.EmitSparkle(cx, cy, (200, 90, 220), 22);
            }
            catch { }
        }
    }

    private void RebuildButtons()
    {
        _buttons.Clear();
        if (State != "playing") return;

        foreach (var seat in ActivePlayers)
            _buttons[seat] = BuildPlayerButtons(seat);
    }

    private Dictionary<string, (string Text, bool Enabled)> BuildPlayerButtons(int seat)
    {
        var btns = new Dictionary<string, (string, bool)>();

        if (_winner != null)
        {
            bool alreadyReady = _nextRoundReady.GetValueOrDefault(seat, false);
            btns["play_again"] = ("Play Again", !alreadyReady);
            int readyCount = _nextRoundReady.Count(kv => kv.Value && ActivePlayers.Contains(kv.Key));
            btns["force_start"] = ($"Force Start ({readyCount}/{ActivePlayers.Count})", readyCount >= 2);
            btns["return_to_lobby"] = ("Return to Lobby", true);
            return btns;
        }

        bool isTurn = seat == CurrentTurnSeat;

        if (_awaitingColorChoice)
        {
            if (seat == _awaitingColorPlayer)
            {
                btns["color:R"] = ("Choose Red", true);
                btns["color:G"] = ("Choose Green", true);
                btns["color:B"] = ("Choose Blue", true);
                btns["color:Y"] = ("Choose Yellow", true);
            }
            return btns;
        }

        btns["draw"] = ("Draw", isTurn && !_drewThisTurn);
        bool canEnd = isTurn && _drewThisTurn && !HasPlayableCard(seat);
        btns["end"] = ("End Turn", canEnd);
        return btns;
    }

    private void NoteEvent(string text)
    {
        _lastEvent = text.Trim();
        _lastEventAge = 0.0;
    }

    private (int R, int G, int B) ColorRgb(string? c) => c switch
    {
        "R" => (220, 70, 70),
        "G" => (70, 200, 110),
        "B" => (80, 140, 235),
        "Y" => (235, 210, 80),
        _ => (180, 180, 180),
    };

    // ─── Update / Draw ─────────────────────────────────────────
    public override void Update(double dt)
    {
        float d = Math.Clamp((float)dt, 0f, 0.2f);
        if (_lastEventAge < 999.0) _lastEventAge += d;

        _particles.Update(d);
        for (int i = _textPops.Count - 1; i >= 0; i--) { _textPops[i].Update(d); if (_textPops[i].Done) _textPops.RemoveAt(i); }
        for (int i = _pulseRings.Count - 1; i >= 0; i--) { _pulseRings[i].Update(d); if (_pulseRings[i].Done) _pulseRings.RemoveAt(i); }
        for (int i = _flashes.Count - 1; i >= 0; i--) { _flashes[i].Update(d); if (_flashes[i].Done) _flashes.RemoveAt(i); }
        for (int i = _cardFlies.Count - 1; i >= 0; i--) { _cardFlies[i].Update(d); if (_cardFlies[i].Done) _cardFlies.RemoveAt(i); }

        // Turn change pulse
        var currTurn = CurrentTurnSeat;
        if (State == "playing" && currTurn is int ct && _animPrevTurn is int pt && ct != pt)
        {
            int cx = ScreenW / 2, cy = ScreenH / 2;
            var col = AnimPalette.Rainbow[ct % AnimPalette.Rainbow.Length];
            _pulseRings.Add(new PulseRing(cx, cy, col, maxRadius: Math.Min(ScreenW, ScreenH) / 5, duration: 0.8f));
            _particles.EmitSparkle(cx, cy, col, 18);
        }
        _animPrevTurn = currTurn;

        // Winner fireworks
        if (_winner is int w && w != (_animPrevWinner ?? -1))
        {
            _animPrevWinner = w;
            int cx = ScreenW / 2, cy = ScreenH / 2;
            for (int i = 0; i < 8; i++)
                _particles.EmitFirework(cx + Rng.Next(-120, 121), cy + Rng.Next(-80, 81), AnimPalette.Rainbow);
            _flashes.Add(new ScreenFlash((255, 220, 80), 60, 1.0f));
            _textPops.Add(new TextPopAnim($"🎉 {PlayerName(w)} wins!", cx, cy - 70, (255, 220, 80), fontSize: 36));
            _animFwTimer = 6.0;
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

    public override void Draw(Renderer r, int width, int height, double dt)
    {
        if (State == "player_select") { base.Draw(r, width, height, dt); return; }

        CardRendering.DrawGameBackground(r, width, height, "uno");
        int cx = width / 2, cy = height / 2;

        // Title
        RainbowTitle.Draw(r, "UNO", width);

        // Status
        var turn = CurrentTurnSeat;
        string status = turn is int t ? $"Top: {TopCard?.Short() ?? "—"}  ·  Color: {_currentColor ?? "—"}  ·  Turn: {PlayerName(t)}" : "Turn: —";
        r.DrawText(status, 24, 54, 14, (200, 200, 200), anchorX: "left", anchorY: "top");

        // Piles
        int cw = Math.Clamp(width * 9 / 100, 78, 110);
        int ch = (int)(cw * 1.42);
        int gap = (int)(cw * 0.9);
        // draw pile
        var drawRect = (cx - gap - cw, cy - ch / 2, cw, ch);
        // Draw pile styled as card back
        r.DrawRect((0, 0, 0), (drawRect.Item1 + 3, drawRect.Item2 + 3, cw, ch), alpha: 60); // shadow
        r.DrawRect((30, 30, 30), drawRect, alpha: 240);
        r.DrawRect((200, 50, 50), (drawRect.Item1 + 4, drawRect.Item2 + 4, cw - 8, ch - 8), alpha: 200);
        // White inner oval on card back
        {
            int ocx = drawRect.Item1 + cw / 2, ocy = drawRect.Item2 + ch / 2;
            float orx = cw * 0.32f, ory = ch * 0.35f;
            var oPts = new (float X, float Y)[20];
            for (int oi = 0; oi < 20; oi++)
            {
                float a = MathF.PI * 2 * oi / 20;
                float px = orx * MathF.Cos(a), py = ory * MathF.Sin(a);
                float tilt = -0.18f;
                oPts[oi] = (ocx + px * MathF.Cos(tilt) - py * MathF.Sin(tilt),
                            ocy + px * MathF.Sin(tilt) + py * MathF.Cos(tilt));
            }
            r.DrawPolygon((255, 255, 255), oPts, alpha: 200);
        }
        r.DrawText("UNO", drawRect.Item1 + cw / 2, drawRect.Item2 + ch / 2, Math.Max(12, ch * 18 / 100),
            (220, 40, 40), anchorX: "center", anchorY: "center", bold: true);
        r.DrawText($"{_drawPile.Count}", drawRect.Item1 + cw / 2, drawRect.Item2 + ch * 75 / 100,
            Math.Max(9, ch * 12 / 100), (200, 200, 200), anchorX: "center", anchorY: "center");
        r.DrawRect((30, 30, 30), drawRect, width: 2, alpha: 220);

        // discard pile
        var discRect = (cx + gap, cy - ch / 2, cw, ch);
        if (TopCard != null)
        {
            var faceCol = TopCard.Value is "wild" or "wild_draw4" ? (120, 120, 120) : ColorRgb(TopCard.Color);
            CardRendering.DrawUnoCard(r, discRect, TopCard.Color, TopCard.Value, faceCol);
        }
        else
        {
            r.DrawRect((40, 10, 15), discRect, alpha: 240);
            r.DrawText("DISCARD", discRect.Item1 + cw / 2, discRect.Item2 + ch / 2, 12, (255, 240, 200), anchorX: "center", anchorY: "center");
        }

        // Direction arrow
        try
        {
            string arrow = _direction >= 0 ? "⟳" : "⟲";
            int acx = (drawRect.Item1 + cw / 2 + discRect.Item1 + cw / 2) / 2;
            int acy = cy - 70;
            r.DrawCircle((255, 255, 255), (acx, acy), 22, alpha: 15);
            r.DrawCircle((255, 255, 255), (acx, acy), 22, width: 2, alpha: 60);
            r.DrawText(arrow, acx, acy, 30, (255, 255, 255), anchorX: "center", anchorY: "center");
        }
        catch { }

        // Seat zones
        foreach (var seat in ActivePlayers)
            DrawSeatZone(r, seat, width, height);

        // Card fly animations (under overlays)
        foreach (var cf in _cardFlies) cf.Draw(r);

        // Particles and pulse rings BEFORE winner overlay so they appear behind it
        _particles.Draw(r);
        foreach (var pr in _pulseRings) pr.Draw(r);
        foreach (var fl in _flashes) fl.Draw(r, width, height);

        // Winner overlay (on top of particles)
        if (_winner is int w)
        {
            r.DrawRect((0, 0, 0), (0, 0, width, height), alpha: 150);
            int bw2 = Math.Min(600, width * 55 / 100), bh2 = 180;
            int bx2 = cx - bw2 / 2, by2 = cy - bh2 / 2;
            r.DrawRect((10, 10, 18), (bx2, by2, bw2, bh2), alpha: 220);
            r.DrawRect((255, 215, 0), (bx2, by2, bw2, bh2), width: 4, alpha: 200);
            r.DrawText("🏆", cx, cy + 30, 50, (255, 215, 0), anchorX: "center", anchorY: "center");
            r.DrawText($"Winner: {PlayerName(w)}", cx, cy - 24, 40, (255, 240, 180), anchorX: "center", anchorY: "center");
        }

        // Color choice prompt
        if (_awaitingColorChoice && _awaitingColorPlayer is int acp)
            r.DrawText($"{PlayerName(acp)}: choose a color (Web UI)", cx, 84, 14, (210, 210, 210), anchorX: "center", anchorY: "top");

        // Last event
        if (!string.IsNullOrEmpty(_lastEvent) && _lastEventAge < 4.5)
        {
            int ew = Math.Max(180, _lastEvent.Length * 8);
            r.DrawRect((0, 0, 0), (20, 74, ew, 22), alpha: 120);
            r.DrawText(_lastEvent, 28, 85, 12, (200, 200, 200), anchorX: "left", anchorY: "center");
        }

        // Text pops on top of everything
        foreach (var tp in _textPops) tp.Draw(r);
    }

    private void DrawSeatZone(Renderer r, int seat, int w, int h)
    {
        var (ax, ay) = SeatAnchor(seat, w, h);
        int count = _hands.GetValueOrDefault(seat)?.Count ?? 0;
        bool isTurn = CurrentTurnSeat == seat;
        var pcol = GameConfig.PlayerColors[seat % GameConfig.PlayerColors.Length];

        int bw = 116, bh = 46;
        int bx = ax - bw / 2;
        int offsetY = seat is 3 or 4 or 5 ? 30 : -30;
        int by = ay + offsetY - bh / 2;
        var border = isTurn ? pcol : (140, 140, 150);

        r.DrawRect((0, 0, 0), (bx + 2, by + 2, bw, bh), alpha: 60);
        r.DrawRect((18, 18, 28), (bx, by, bw, bh), alpha: 190);
        if (isTurn) r.DrawRect(border, (bx - 3, by - 3, bw + 6, bh + 6), width: 2, alpha: 55);
        r.DrawRect(border, (bx, by, bw, bh), width: isTurn ? 2 : 1, alpha: 200);
        r.DrawCircle(pcol, (bx + 10, by + 12), 4, alpha: 180);

        var nameCol = isTurn ? (255, 240, 100) : pcol;
        r.DrawText(PlayerName(seat), bx + 20, by + 6, 11, nameCol, anchorX: "left", anchorY: "top");
        r.DrawText($"🃏 {count}", bx + 10, by + bh - 8, 10, (200, 200, 200), anchorX: "left", anchorY: "bottom");
    }

    private void ShuffleList<T>(List<T> list)
    {
        for (int i = list.Count - 1; i > 0; i--)
        {
            int j = Rng.Next(i + 1);
            (list[i], list[j]) = (list[j], list[i]);
        }
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
}
