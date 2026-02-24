using System;
using System.Collections.Generic;
using System.Linq;
using ARPi2.Sharp.Core;

namespace ARPi2.Sharp.Games.Blackjack;

// ════════════════════════════════════════════════════════════════
//  Data types
// ════════════════════════════════════════════════════════════════
public class BjCard
{
    public string Rank { get; set; } = "";
    public string Suit { get; set; } = "";

    public int Value(int currentTotal = 0)
    {
        if (Rank is "J" or "Q" or "K") return 10;
        if (Rank == "A") return currentTotal + 11 <= 21 ? 11 : 1;
        return int.Parse(Rank);
    }

    public override string ToString() => $"{Rank}{Suit}";

    public static readonly string[] Suits = { "♠", "♥", "♦", "♣" };
    public static readonly string[] Ranks = { "A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K" };
}

public class BjHand
{
    public List<BjCard> Cards { get; set; } = new();
    public int Bet { get; set; }
    public bool IsStanding { get; set; }
    public bool IsBusted { get; set; }
    public bool IsDoubled { get; set; }
    public bool IsSplit { get; set; }

    public int Value()
    {
        int total = 0, aces = 0;
        foreach (var c in Cards)
        {
            if (c.Rank == "A") { aces++; total += 11; }
            else if (c.Rank is "J" or "Q" or "K") total += 10;
            else total += int.Parse(c.Rank);
        }
        while (total > 21 && aces > 0) { total -= 10; aces--; }
        return total;
    }

    public bool IsBlackjack() => Cards.Count == 2 && Value() == 21;
}

public class BjPlayer
{
    public int Idx { get; set; }
    public int Chips { get; set; } = 1000;
    public List<BjHand> Hands { get; set; } = new();
    public int CurrentHandIdx { get; set; }
    public int InsuranceBet { get; set; }
    public int CurrentBet { get; set; }
    public bool IsReady { get; set; }
    public bool IsBankrupt { get; set; }
    public bool IsActive { get; set; } = true;

    public BjHand? GetCurrentHand() =>
        CurrentHandIdx >= 0 && CurrentHandIdx < Hands.Count ? Hands[CurrentHandIdx] : null;

    public bool NextHand() { CurrentHandIdx++; return CurrentHandIdx < Hands.Count; }

    public bool PlaceBet(int amount)
    {
        if (Chips < amount) return false;
        Chips -= amount;
        return true;
    }

    public void ResetForRound()
    {
        Hands.Clear();
        CurrentHandIdx = 0;
        InsuranceBet = 0;
        CurrentBet = 0;
        IsReady = false;
    }
}

// ════════════════════════════════════════════════════════════════
//  BlackjackGame — full port from Python
// ════════════════════════════════════════════════════════════════
public class BlackjackGameSharp : BaseGame
{
    public override string ThemeName => "blackjack";

    // Players & deck
    private BjPlayer[] _players = new BjPlayer[8];
    private List<BjCard> _deck = new();
    private BjHand _dealerHand = new();
    private bool _dealerReveal;
    private int _currentPlayerIdx;

    // Buttons per player: Dict<playerIdx, Dict<btnId, (text, enabled)>>
    private readonly Dictionary<int, Dictionary<string, (string Text, bool Enabled)>> _buttons = new();

    // Popup state  
    private UniversalPopup _popup = new();
    public override UniversalPopup? Popup => _popup;

    // Web UI result popups
    private int _webRoundId;
    private readonly Dictionary<int, Dictionary<string, object?>> _webResultPopups = new();
    private readonly Dictionary<int, int> _webResultDismissedRound = new();

    // Timing
    private double _dealTimer;
    private bool _dealing;
    private int _dealPhase;
    private double _resultTimer;
    private string _gameOverMessage = "";

    // Animations
    private readonly ParticleSystem _particles = new();
    private readonly List<TextPopAnim> _textPops = new();
    private readonly List<ScreenFlash> _flashes = new();
    private readonly List<PulseRing> _pulseRings = new();
    private readonly List<CardFlipInPlace> _cardFlips = new();
    private readonly AmbientSystem _ambient;
    private readonly LightBeamSystem _lightBeams = LightBeamSystem.ForTheme("blackjack");
    private readonly VignettePulse _vignette = new();
    private readonly Starfield _starfield;
    private readonly FloatingIconSystem _floatingIcons = FloatingIconSystem.ForTheme("blackjack");
    private readonly WaveBand _waveBand = WaveBand.ForTheme("blackjack");
    private readonly HeatShimmer _heatShimmer = HeatShimmer.ForTheme("blackjack");

    public BlackjackGameSharp(int w, int h, Renderer renderer) : base(w, h, renderer)
    {
        _ambient = AmbientSystem.ForTheme("blackjack", w, h);
        _starfield = Starfield.ForTheme("blackjack", w, h);
    }

    // ─── Start game ────────────────────────────────────────────
    public override void StartGame(List<int> players)
    {
        ActivePlayers = new List<int>(players.OrderBy(x => x));
        _players = new BjPlayer[8];
        for (int i = 0; i < 8; i++)
            _players[i] = new BjPlayer { Idx = i };
        foreach (int i in ActivePlayers)
            _players[i].IsActive = true;

        _dealerHand = new BjHand();
        _buttons.Clear();
        _webResultPopups.Clear();
        _webResultDismissedRound.Clear();
        _webRoundId = 0;
        _currentPlayerIdx = 0;
        State = "betting";
        ShowBettingForAll();
    }

    // ─── Betting ───────────────────────────────────────────────
    private void ShowBettingForAll()
    {
        foreach (int idx in ActivePlayers)
        {
            var p = _players[idx];
            if (p.IsBankrupt) continue;
            var btns = new Dictionary<string, (string, bool)>();
            bool ready = p.IsReady;
            btns["btn_0"] = ("$5", !ready && p.Chips >= p.CurrentBet + 5);
            btns["btn_1"] = ("$25", !ready && p.Chips >= p.CurrentBet + 25);
            btns["btn_2"] = ("$100", !ready && p.Chips >= p.CurrentBet + 100);
            btns["btn_3"] = ("$500", !ready && p.Chips >= p.CurrentBet + 500);
            btns["btn_4"] = ("All In", !ready && p.Chips >= 5);
            btns["btn_5"] = ("Ready", !ready && p.CurrentBet > 0);
            _buttons[idx] = btns;
        }
    }

    // ─── Dealing ───────────────────────────────────────────────
    private void StartDealing()
    {
        _webRoundId++;
        foreach (int idx in ActivePlayers)
        {
            _webResultPopups.Remove(idx);
            _webResultDismissedRound.Remove(idx);
        }

        _deck = CreateDeck();
        _dealerHand = new BjHand();
        _dealerReveal = false;

        // Save bets BEFORE ResetForRound zeroes CurrentBet
        var savedBets = new Dictionary<int, int>();
        foreach (int idx in ActivePlayers)
            savedBets[idx] = _players[idx].CurrentBet;

        foreach (int idx in ActivePlayers)
        {
            var p = _players[idx];
            p.ResetForRound();
        }

        // Place bets from saved amounts
        foreach (int idx in ActivePlayers)
        {
            var p = _players[idx];
            int bet = savedBets.GetValueOrDefault(idx, 0);
            if (bet > 0 && p.PlaceBet(bet))
            {
                var hand = new BjHand { Bet = bet };
                p.Hands.Add(hand);
            }
        }

        // Deal 2 cards to each player + 2 to dealer
        foreach (int idx in ActivePlayers)
        {
            var p = _players[idx];
            if (p.Hands.Count > 0)
            {
                p.Hands[0].Cards.Add(DrawCard());
            }
        }
        _dealerHand.Cards.Add(DrawCard());

        foreach (int idx in ActivePlayers)
        {
            var p = _players[idx];
            if (p.Hands.Count > 0)
                p.Hands[0].Cards.Add(DrawCard());
        }
        _dealerHand.Cards.Add(DrawCard());

        _currentPlayerIdx = 0;
        State = "playing";
        _buttons.Clear();
        ShowPlayerActions();
    }

    // ─── Player actions ────────────────────────────────────────
    private void ShowPlayerActions()
    {
        _buttons.Clear();

        // Check if all players done
        bool allDone = true;
        foreach (int idx in ActivePlayers)
        {
            var p = _players[idx];
            if (p.Hands.Count == 0) continue;
            if (p.Hands.Any(h => !h.IsStanding && !h.IsBusted))
            {
                allDone = false;
                // Show buttons for this player
                var hand = p.GetCurrentHand();
                if (hand != null && !hand.IsStanding && !hand.IsBusted)
                {
                    var btns = new Dictionary<string, (string, bool)>();
                    btns["btn_0"] = ("Hit", true);
                    btns["btn_1"] = ("Stand", true);
                    bool canDouble = hand.Cards.Count == 2 && p.Chips >= hand.Bet;
                    btns["btn_2"] = ("Double", canDouble);
                    bool canSplit = hand.Cards.Count == 2
                        && hand.Cards[0].Rank == hand.Cards[1].Rank
                        && p.Chips >= hand.Bet;
                    btns["btn_3"] = ("Split", canSplit);
                    _buttons[idx] = btns;
                }
            }
        }

        if (allDone)
        {
            DealerPlay();
        }
    }

    private void Hit(BjPlayer player)
    {
        var hand = player.GetCurrentHand();
        if (hand == null || _deck.Count == 0) return;
        hand.Cards.Add(DrawCard());
        if (hand.Value() > 21)
        {
            hand.IsBusted = true;
            hand.IsStanding = true;
            if (!player.NextHand())
                _currentPlayerIdx++;
        }
        ShowPlayerActions();
    }

    private void Stand(BjPlayer player)
    {
        var hand = player.GetCurrentHand();
        if (hand == null) return;
        hand.IsStanding = true;
        if (!player.NextHand())
            _currentPlayerIdx++;
        ShowPlayerActions();
    }

    private void DoubleDown(BjPlayer player)
    {
        var hand = player.GetCurrentHand();
        if (hand == null || !player.PlaceBet(hand.Bet)) return;
        hand.Bet *= 2;
        hand.IsDoubled = true;
        if (_deck.Count > 0) hand.Cards.Add(DrawCard());
        if (hand.Value() > 21) hand.IsBusted = true;
        hand.IsStanding = true;
        if (!player.NextHand())
            _currentPlayerIdx++;
        ShowPlayerActions();
    }

    private void Split(BjPlayer player)
    {
        var hand = player.GetCurrentHand();
        if (hand == null || hand.Cards.Count != 2 || !player.PlaceBet(hand.Bet)) return;

        var h1 = new BjHand { Bet = hand.Bet, IsSplit = true };
        h1.Cards.Add(hand.Cards[0]);
        h1.Cards.Add(DrawCard());

        var h2 = new BjHand { Bet = hand.Bet, IsSplit = true };
        h2.Cards.Add(hand.Cards[1]);
        h2.Cards.Add(DrawCard());

        player.Hands[player.CurrentHandIdx] = h1;
        player.Hands.Insert(player.CurrentHandIdx + 1, h2);
        ShowPlayerActions();
    }

    // ─── Dealer play ───────────────────────────────────────────
    private void DealerPlay()
    {
        State = "dealer_turn";
        _dealerReveal = true;
        _buttons.Clear();

        // Flip animation for the hidden dealer card
        try
        {
            int dcx = ScreenW / 2;
            int dcy = ScreenH * 18 / 100 + 50; // approximate center of dealer card area
            int cardW = 70, cardH = 100, gap = 6;
            int total = _dealerHand.Cards.Count;
            int tw = total * (cardW + gap) - gap;
            int sx = dcx - tw / 2;
            // Second card (index 1) was the hidden one
            _cardFlips.Add(new CardFlipInPlace(sx + 1 * (cardW + gap) + cardW / 2, dcy, cardW: cardW, cardH: cardH, backColor: (40, 80, 40), frontColor: (255, 255, 255)));
        }
        catch { }

        // Dealer hits on 16, stands on 17
        while (_dealerHand.Value() < 17 && _deck.Count > 0)
            _dealerHand.Cards.Add(DrawCard());

        ResolveRound();
    }

    private void ResolveRound()
    {
        State = "results";
        _resultTimer = 0;
        int dealerVal = _dealerHand.Value();
        bool dealerBust = dealerVal > 21;

        foreach (int idx in ActivePlayers)
        {
            var p = _players[idx];
            string resultText = "";
            int totalWin = 0;

            foreach (var hand in p.Hands)
            {
                int hv = hand.Value();
                bool playerBj = hand.IsBlackjack();
                bool dealerBj = _dealerHand.IsBlackjack();

                if (hand.IsBusted)
                {
                    resultText = "Bust!";
                }
                else if (playerBj && !dealerBj)
                {
                    int win = (int)(hand.Bet * 2.5);
                    p.Chips += win;
                    totalWin += win;
                    resultText = "Blackjack!";
                }
                else if (dealerBust || hv > dealerVal)
                {
                    int win = hand.Bet * 2;
                    p.Chips += win;
                    totalWin += win;
                    resultText = "Win!";
                }
                else if (hv == dealerVal)
                {
                    p.Chips += hand.Bet;
                    resultText = "Push";
                }
                else
                {
                    resultText = "Lose";
                }
            }

            // Result animations
            try
            {
                int playerCount = ActivePlayers.Count;
                int pi = ActivePlayers.IndexOf(idx);
                int px = ScreenW * (pi + 1) / (playerCount + 1);
                int py = ScreenH * 60 / 100;
                var pcol = GameConfig.PlayerColors[idx % GameConfig.PlayerColors.Length];

                if (resultText == "Blackjack!")
                {
                    _flashes.Add(new ScreenFlash((255, 215, 0), 50, 0.6f));
                    _textPops.Add(new TextPopAnim("♠ BLACKJACK! ♠", px, py - 60, (255, 215, 0), fontSize: 36));
                    _pulseRings.Add(new PulseRing(px, py, (255, 215, 0), maxRadius: 100, duration: 0.8f));
                    _particles.EmitFirework(px, py - 40, new[] { (255, 215, 0), (255, 180, 0), (255, 255, 150) });
                    _particles.EmitFirework(px - 40, py - 60, new[] { (255, 215, 0), (255, 180, 0), (255, 255, 150) });
                }
                else if (resultText == "Win!")
                {
                    _flashes.Add(new ScreenFlash((60, 200, 80), 30, 0.4f));
                    _textPops.Add(new TextPopAnim($"WIN +${totalWin}", px, py - 60, (80, 255, 120), fontSize: 28));
                    _pulseRings.Add(new PulseRing(px, py, (80, 255, 120), maxRadius: 70, duration: 0.6f));
                    _particles.EmitSparkle(px, py - 40, (80, 255, 120), 14);
                }
                else if (resultText == "Bust!")
                {
                    _flashes.Add(new ScreenFlash((200, 40, 40), 30, 0.35f));
                    _textPops.Add(new TextPopAnim("BUST!", px, py - 60, (255, 80, 80), fontSize: 28));
                }
                else if (resultText == "Push")
                {
                    _textPops.Add(new TextPopAnim("PUSH", px, py - 60, (180, 180, 180), fontSize: 24));
                }
                else if (resultText == "Lose")
                {
                    _textPops.Add(new TextPopAnim("LOSE", px, py - 60, (200, 100, 100), fontSize: 24));
                }
            }
            catch { }
            var dealerCards = _dealerHand.Cards.Select(c => c.ToString()).ToList();
            bool dealerBusted = dealerVal > 21;
            bool dealerBlackjack = _dealerHand.IsBlackjack();

            var hands = new List<Dictionary<string, object?>>();
            foreach (var hand in p.Hands)
            {
                hands.Add(new Dictionary<string, object?>
                {
                    ["title"] = $"Hand {hands.Count + 1}",
                    ["message"] = resultText,
                    ["bet"] = hand.Bet,
                    ["cards"] = hand.Cards.Select(c => c.ToString()).ToList(),
                    ["value"] = hand.Value(),
                    ["busted"] = hand.IsBusted,
                    ["blackjack"] = hand.IsBlackjack(),
                });
            }

            var popup = new Dictionary<string, object?>
            {
                ["round_id"] = _webRoundId,
                ["dealer"] = new Dictionary<string, object?>
                {
                    ["cards"] = dealerCards,
                    ["value"] = dealerVal,
                    ["busted"] = dealerBusted,
                    ["blackjack"] = dealerBlackjack,
                },
                ["hands"] = hands,
            };
            _webResultPopups[idx] = popup;
        }

        // Show Next Hand buttons for all players
        foreach (int idx in ActivePlayers)
        {
            _buttons[idx] = new Dictionary<string, (string, bool)>
            {
                ["btn_0"] = ("Next Hand", true)
            };
        }

        // Check for game over
        var playersWithChips = ActivePlayers.Where(i => _players[i].Chips >= 5).ToList();
        if (playersWithChips.Count == 0)
        {
            EndGame("All players are broke!");
        }
        else if (playersWithChips.Count == 1 && ActivePlayers.Count > 1)
        {
            EndGame($"{PlayerName(playersWithChips[0])} wins!");
        }
    }

    private void EndGame(string message)
    {
        State = "game_over";
        _gameOverMessage = message;
        _buttons.Clear();
    }

    private void StartNewRound()
    {
        foreach (int idx in ActivePlayers)
            _players[idx].ResetForRound();

        // Remove bankrupt players
        var broke = ActivePlayers.Where(i => _players[i].Chips < 5).ToList();
        foreach (int i in broke)
            _players[i].IsBankrupt = true;

        State = "betting";
        _currentPlayerIdx = 0;
        ShowBettingForAll();
    }

    // ─── Deck helpers ──────────────────────────────────────────
    private List<BjCard> CreateDeck()
    {
        var deck = new List<BjCard>();
        foreach (var s in BjCard.Suits)
            foreach (var r in BjCard.Ranks)
                deck.Add(new BjCard { Rank = r, Suit = s });
        Rng.Shuffle(deck);
        return deck;
    }

    private BjCard DrawCard()
    {
        if (_deck.Count == 0) _deck = CreateDeck();
        var c = _deck[^1];
        _deck.RemoveAt(_deck.Count - 1);
        return c;
    }

    // ─── HandleMessage (game-specific messages from Web UI) ───
    public override void HandleMessage(int playerIdx, string type, string json)
    {
        switch (type)
        {
            case "blackjack_close_result":
                CloseWebResult(playerIdx);
                break;
            case "blackjack_adjust_bet":
                HandleAdjustBet(playerIdx, json);
                break;
        }
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
                string msgType = parts[1];
                string json = parts.Length > 2 ? parts[2] : "";

                if (msgType == "blackjack_adjust_bet")
                {
                    HandleAdjustBet(playerIdx, json);
                    return;
                }
                if (msgType == "blackjack_close_result")
                {
                    CloseWebResult(playerIdx);
                    return;
                }
            }
        }

        if (State == "betting")
        {
            HandleBettingClick(playerIdx, buttonId);
            return;
        }

        if (State == "playing")
        {
            HandlePlayingClick(playerIdx, buttonId);
            return;
        }

        if (State == "results")
        {
            // Dismiss this player's result popup
            CloseWebResult(playerIdx);
            // If all results closed, start new round
            if (WebResultsAllClosed())
                StartNewRound();
            return;
        }
    }

    private void HandleBettingClick(int playerIdx, string buttonId)
    {
        if (!ActivePlayers.Contains(playerIdx)) return;
        var player = _players[playerIdx];
        if (player.IsReady || player.IsBankrupt) return;

        int[] amounts = { 5, 25, 100, 500 };

        if (buttonId == "btn_5") // Ready
        {
            if (player.CurrentBet > 0)
            {
                player.IsReady = true;
                ShowBettingForAll();
                if (ActivePlayers.All(i => _players[i].IsReady || _players[i].IsBankrupt))
                    StartDealing();
            }
        }
        else if (buttonId == "btn_4") // All-in
        {
            if (player.Chips >= 5)
            {
                player.CurrentBet = player.Chips;
                ShowBettingForAll();
            }
        }
        else if (buttonId.StartsWith("btn_"))
        {
            if (int.TryParse(buttonId.AsSpan(4), out int idx) && idx >= 0 && idx < amounts.Length)
            {
                int amount = amounts[idx];
                if (player.Chips >= player.CurrentBet + amount)
                {
                    player.CurrentBet += amount;
                    ShowBettingForAll();
                }
            }
        }
    }

    private void HandlePlayingClick(int playerIdx, string buttonId)
    {
        if (!ActivePlayers.Contains(playerIdx)) return;
        var player = _players[playerIdx];
        if (player.Hands.Count == 0) return;
        var hand = player.GetCurrentHand();
        if (hand == null || hand.IsStanding || hand.IsBusted) return;

        switch (buttonId)
        {
            case "btn_0": Hit(player); break;
            case "btn_1": Stand(player); break;
            case "btn_2": DoubleDown(player); break;
            case "btn_3": Split(player); break;
        }
    }

    private void HandleAdjustBet(int playerIdx, string json)
    {
        if (State != "betting") return;
        var player = _players[playerIdx];
        if (player.IsReady) return;

        try
        {
            using var doc = System.Text.Json.JsonDocument.Parse(json);
            int amount = doc.RootElement.GetProperty("amount").GetInt32();
            if (amount > 0)
                player.CurrentBet = Math.Max(0, player.CurrentBet - amount);
            ShowBettingForAll();
        }
        catch { }
    }

    private void CloseWebResult(int playerIdx)
    {
        if (!_webResultPopups.TryGetValue(playerIdx, out var popup)) return;
        var roundId = popup.TryGetValue("round_id", out var rid) ? (int)(rid ?? -1) : -1;
        _webResultDismissedRound[playerIdx] = roundId;

        if (WebResultsAllClosed() && State == "results")
            StartNewRound();
    }

    private bool WebResultsAllClosed()
    {
        if (_webRoundId <= 0) return true;
        foreach (int idx in ActivePlayers)
        {
            if (!_webResultPopups.ContainsKey(idx)) continue;
            int dismissed = _webResultDismissedRound.GetValueOrDefault(idx, -1);
            if (dismissed != _webRoundId) return false;
        }
        return true;
    }

    // ─── Snapshot ──────────────────────────────────────────────
    public override Dictionary<string, object?> GetSnapshot(int playerIdx)
    {
        string phaseText = State switch
        {
            "betting" => $"Waiting for bets: {ActivePlayers.Count(i => _players[i].IsReady)}/{ActivePlayers.Count} ready",
            "dealing" => "Dealing cards",
            "playing" => "Waiting for decisions",
            "dealer_turn" => "Dealer is playing",
            "results" => "Results",
            "game_over" => _gameOverMessage,
            _ => State,
        };

        int readyCount = State == "betting"
            ? ActivePlayers.Count(i => _players[i].IsReady)
            : 0;

        var snap = new Dictionary<string, object?>
        {
            ["state"] = State,
            ["phase_text"] = phaseText,
            ["ready_count"] = readyCount,
            ["required_count"] = ActivePlayers.Count,
            ["your_chips"] = (object?)null,
            ["your_current_bet"] = 0,
            ["your_total_bet"] = 0,
            ["your_hand"] = new List<string>(),
            ["your_hand_value"] = (object?)null,
            ["result_popup"] = (object?)null,
        };

        if (playerIdx >= 0 && playerIdx < 8)
        {
            var p = _players[playerIdx];
            snap["your_chips"] = p.Chips;
            snap["your_current_bet"] = p.CurrentBet;

            int totalBet = p.Hands.Sum(h => h.Bet);
            if (totalBet == 0) totalBet = p.CurrentBet;
            snap["your_total_bet"] = totalBet;

            if (p.Hands.Count > 0)
            {
                var hand = p.GetCurrentHand() ?? p.Hands[0];
                snap["your_hand"] = hand.Cards.Select(c => c.ToString()).ToList();
                snap["your_hand_value"] = hand.Value();
            }

            // Result popup
            if (_webResultPopups.TryGetValue(playerIdx, out var rp))
            {
                int dismissed = _webResultDismissedRound.GetValueOrDefault(playerIdx, -1);
                var roundId = rp.TryGetValue("round_id", out var rid) ? (int)(rid ?? -1) : -1;
                if (dismissed != roundId)
                    snap["result_popup"] = rp;
            }
        }

        return new Dictionary<string, object?> { ["blackjack"] = snap };
    }

    public override Dictionary<string, object?> GetPopupSnapshot(int playerIdx)
    {
        if (!_popup.Active) return new Dictionary<string, object?> { ["active"] = false };
        if (_popup.PlayerIdx != null && _popup.PlayerIdx != playerIdx)
            return new Dictionary<string, object?> { ["active"] = false };

        return new Dictionary<string, object?>
        {
            ["active"] = true,
            ["popup_type"] = _popup.PopupType,
            ["lines"] = _popup.TextLines.Select(l => l.Text).ToList(),
            ["line_items"] = _popup.TextLines.Select(l => new Dictionary<string, object?> { ["text"] = l.Text, ["color"] = $"#{l.Color.R:x2}{l.Color.G:x2}{l.Color.B:x2}" }).ToList(),
            ["buttons"] = GetPopupButtons(playerIdx),
        };
    }

    public override List<Dictionary<string, object?>> GetPanelButtons(int playerIdx)
    {
        if (!_buttons.TryGetValue(playerIdx, out var btns)) return new();
        return btns
            .Where(kv => !kv.Key.StartsWith("popup_"))
            .Select(kv => new Dictionary<string, object?>
            {
                ["id"] = kv.Key,
                ["text"] = kv.Value.Text,
                ["enabled"] = kv.Value.Enabled,
            })
            .ToList();
    }

    private List<Dictionary<string, object?>> GetPopupButtons(int playerIdx)
    {
        if (!_buttons.TryGetValue(playerIdx, out var btns)) return new();
        return btns
            .Where(kv => kv.Key.StartsWith("popup_"))
            .Select(kv => new Dictionary<string, object?>
            {
                ["id"] = kv.Key,
                ["text"] = kv.Value.Text,
                ["enabled"] = kv.Value.Enabled,
            })
            .ToList();
    }

    // ─── Update / Draw ─────────────────────────────────────────
    public override void Update(double dt)
    {
        if (State == "results")
        {
            _resultTimer += dt;
            if (_resultTimer > 4.0 && WebResultsAllClosed())
                StartNewRound();
        }

        _particles.Update((float)dt);
        for (int i = _textPops.Count - 1; i >= 0; i--)
        {
            _textPops[i].Update((float)dt);
            if (_textPops[i].Done) _textPops.RemoveAt(i);
        }
        for (int i = _flashes.Count - 1; i >= 0; i--)
        {
            _flashes[i].Update((float)dt);
            if (_flashes[i].Done) _flashes.RemoveAt(i);
        }
        for (int i = _pulseRings.Count - 1; i >= 0; i--)
        {
            _pulseRings[i].Update((float)dt);
            if (_pulseRings[i].Done) _pulseRings.RemoveAt(i);
        }
        for (int i = _cardFlips.Count - 1; i >= 0; i--)
        {
            _cardFlips[i].Update((float)dt);
            if (_cardFlips[i].Done) _cardFlips.RemoveAt(i);
        }
        _ambient.Update((float)dt, ScreenW, ScreenH);
        _lightBeams.Update((float)dt, ScreenW, ScreenH);
        _vignette.Update((float)dt);
        _starfield.Update((float)dt);
        _floatingIcons.Update((float)dt, ScreenW, ScreenH);
        _waveBand.Update((float)dt);
        _heatShimmer.Update((float)dt);
    }

    public override void Draw(Renderer r, int width, int height, double dt)
    {
        if (State == "player_select")
        {
            base.Draw(r, width, height, dt);
            return;
        }

        CardRendering.DrawGameBackground(r, width, height, "blackjack");
        _ambient.Draw(r);
        _lightBeams.Draw(r, width, height);
        _starfield.Draw(r);
        _floatingIcons.Draw(r);
        int cx = width / 2, cy = height / 2;

        // Title
        RainbowTitle.Draw(r, "BLACKJACK", width, y: 12, fontSize: 22, charWidth: 16);

        // Status bar
        string status = State switch
        {
            "betting" => $"Place your bets! ({ActivePlayers.Count(i => _players[i].IsReady)}/{ActivePlayers.Count} ready)",
            "playing" => "Make your move",
            "dealer_turn" => "Dealer's turn",
            "results" => "Round results",
            "game_over" => _gameOverMessage,
            _ => State,
        };
        {
            int sw = Math.Max(260, status.Length * 10 + 40);
            int sh = 30;
            int sx = cx - sw / 2, sy = 38;
            r.DrawRect((0, 0, 0), (sx + 3, sy + 3, sw, sh), alpha: 60);
            r.DrawRect((14, 22, 32), (sx, sy, sw, sh), alpha: 210);
            r.DrawRect((120, 170, 200), (sx, sy, sw, sh), width: 1, alpha: 60);
            r.DrawText(status, cx, sy + sh / 2, 14, (200, 220, 240), anchorX: "center", anchorY: "center");
        }

        // Dealer panel
        int dY = height * 18 / 100;
        {
            int dpW = Math.Min(500, width * 60 / 100), dpH = 160;
            int dpX = cx - dpW / 2, dpY = dY - 30;
            r.DrawRect((0, 0, 0), (dpX + 3, dpY + 3, dpW, dpH), alpha: 60);
            r.DrawRect((12, 12, 20), (dpX, dpY, dpW, dpH), alpha: 200);
            r.DrawRect((180, 140, 80), (dpX, dpY, dpW, 4), alpha: 80);           // accent header band
            r.DrawRect((180, 140, 80), (dpX, dpY, dpW, dpH), width: 2, alpha: 120);
            // Inset frame
            int ins = Math.Max(3, dpW * 4 / 100);
            r.DrawRect((180, 140, 80), (dpX + ins, dpY + ins, dpW - 2 * ins, dpH - 2 * ins), width: 1, alpha: 35);

            r.DrawText("🃏 Dealer", cx, dpY + 16, 16, (220, 200, 140), anchorX: "center", anchorY: "top", bold: true);
            DrawHand(r, _dealerHand, cx, dpY + 42, !_dealerReveal);
            if (_dealerReveal)
            {
                int val = _dealerHand.Value();
                var valCol = val > 21 ? (255, 80, 80) : val == 21 ? (80, 255, 120) : (255, 255, 255);
                r.DrawText($"Value: {val}", cx, dpY + dpH - 14, 14, valCol, anchorX: "center", anchorY: "bottom", bold: true);
            }
        }

        // Player hand panels
        int playerCount = ActivePlayers.Count;
        for (int i = 0; i < playerCount; i++)
        {
            int pidx = ActivePlayers[i];
            var p = _players[pidx];
            int px = width * (i + 1) / (playerCount + 1);
            int py = height * 58 / 100;

            var col = GameConfig.PlayerColors[pidx % GameConfig.PlayerColors.Length];
            bool isActive = State == "playing" && _currentPlayerIdx >= 0
                && _currentPlayerIdx < ActivePlayers.Count && ActivePlayers[_currentPlayerIdx] == pidx;

            // Panel dimensions
            int pw = Math.Min(200, width / (playerCount + 1) - 10), ph = 190;
            int pxL = px - pw / 2, pyT = py - 36;

            // Near-bust glow (value 17-20)
            if (p.Hands.Count > 0)
            {
                int val = p.Hands[0].Value();
                if (val >= 17 && val <= 20)
                    r.DrawRect((255, 200, 0), (pxL - 4, pyT - 4, pw + 8, ph + 8), width: 2, alpha: 50);
                else if (val > 21)
                    r.DrawRect((255, 50, 50), (pxL - 4, pyT - 4, pw + 8, ph + 8), width: 2, alpha: 70);
            }

            // Active turn glow
            if (isActive)
                r.DrawRect(col, (pxL - 5, pyT - 5, pw + 10, ph + 10), width: 3, alpha: 60);

            // Panel background
            r.DrawRect((0, 0, 0), (pxL + 3, pyT + 3, pw, ph), alpha: 60);
            r.DrawRect((14, 14, 22), (pxL, pyT, pw, ph), alpha: 210);
            r.DrawRect(col, (pxL, pyT, pw, 4), alpha: 100);                      // accent header band
            r.DrawRect(col, (pxL, pyT, pw, ph), width: isActive ? 2 : 1, alpha: isActive ? 200 : 100);
            int ins = Math.Max(3, pw * 5 / 100);
            r.DrawRect(col, (pxL + ins, pyT + ins, pw - 2 * ins, ph - 2 * ins), width: 1, alpha: 25);

            // Player name + chips badge
            r.DrawCircle(col, (pxL + 12, pyT + 16), 4, alpha: 200);
            r.DrawText(PlayerName(pidx), pxL + 22, pyT + 10, 12, isActive ? (255, 240, 100) : col,
                anchorX: "left", anchorY: "top", bold: true);
            // Chips pill
            string chipTxt = $"💰 ${p.Chips}";
            int cpW = chipTxt.Length * 7 + 10, cpH = 16;
            int cpX = pxL + pw - cpW - 6, cpY = pyT + 8;
            r.DrawRect(col, (cpX, cpY, cpW, cpH), alpha: 25);
            r.DrawText(chipTxt, cpX + cpW / 2, cpY + cpH / 2, 10, (220, 220, 220),
                anchorX: "center", anchorY: "center");

            if (State == "betting")
            {
                r.DrawText($"Bet: ${p.CurrentBet}", px, pyT + 50, 14, (255, 215, 0), anchorX: "center", bold: true);
                if (p.IsReady)
                {
                    int rw = 60, rh = 20;
                    r.DrawRect((0, 180, 0), (px - rw / 2, pyT + 72, rw, rh), alpha: 30);
                    r.DrawText("READY ✓", px, pyT + 82, 12, (80, 255, 80), anchorX: "center", anchorY: "center");
                }
            }
            else if (p.Hands.Count > 0)
            {
                DrawHand(r, p.Hands[0], px, pyT + 46, false);
                int val = p.Hands[0].Value();
                var valCol = val > 21 ? (255, 80, 80) : val == 21 ? (80, 255, 120) : (255, 255, 255);
                r.DrawText($"Value: {val}", px, pyT + ph - 10, 12, valCol, anchorX: "center", anchorY: "bottom", bold: true);
            }
        }

        // Animations
        foreach (var cf in _cardFlips) cf.Draw(r);
        _particles.Draw(r);
        foreach (var pr in _pulseRings) pr.Draw(r);
        foreach (var tp in _textPops) tp.Draw(r);
        foreach (var fl in _flashes) fl.Draw(r, width, height);
        _waveBand.Draw(r, width, height);
        _heatShimmer.Draw(r, width, height);
        _vignette.Draw(r, width, height);
    }

    private void DrawHand(Renderer r, BjHand hand, int cx, int y, bool hideSecond)
    {
        int cardW = 70, cardH = 100, gap = 6;
        int total = hand.Cards.Count;
        int tw = total * (cardW + gap) - gap;
        int sx = cx - tw / 2;

        for (int i = 0; i < total; i++)
        {
            bool faceUp = !(hideSecond && i == 1);
            string card = faceUp ? hand.Cards[i].ToString() : "";
            CardRendering.DrawPlayingCard(r, (sx + i * (cardW + gap), y, cardW, cardH), card, faceUp);
        }
    }
}

// Random shuffle extension
public static class ListShuffleExt
{
    public static void Shuffle<T>(this Random rng, List<T> list)
    {
        for (int i = list.Count - 1; i > 0; i--)
        {
            int j = rng.Next(i + 1);
            (list[i], list[j]) = (list[j], list[i]);
        }
    }
}
