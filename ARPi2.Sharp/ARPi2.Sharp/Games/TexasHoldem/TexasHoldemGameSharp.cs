using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using ARPi2.Sharp.Core;
using ARPi2.Sharp.Games.Blackjack; // for ListShuffleExt

namespace ARPi2.Sharp.Games.TexasHoldem;

// ════════════════════════════════════════════════════════════════
//  Data types
// ════════════════════════════════════════════════════════════════

/// <summary>A single card: rank 2..14 (14 = Ace), suit S/H/D/C.</summary>
public readonly struct HoldemCard : IEquatable<HoldemCard>
{
    public int Rank { get; }   // 2..14
    public string Suit { get; } // "S","H","D","C"

    public HoldemCard(int rank, string suit) { Rank = rank; Suit = suit; }

    public string Short()
    {
        string rs = Rank switch
        {
            14 => "A", 13 => "K", 12 => "Q", 11 => "J", 10 => "T",
            _ => Rank.ToString()
        };
        return $"{rs}{Suit}";
    }

    public bool Equals(HoldemCard other) => Rank == other.Rank && Suit == other.Suit;
    public override bool Equals(object? obj) => obj is HoldemCard c && Equals(c);
    public override int GetHashCode() => HashCode.Combine(Rank, Suit);
    public override string ToString() => Short();
}

// ════════════════════════════════════════════════════════════════
//  Hand evaluation helpers
// ════════════════════════════════════════════════════════════════

/// <summary>Comparable poker hand rank: (Category 0-8, tiebreak tuple).</summary>
public readonly struct HandRank : IComparable<HandRank>
{
    public int Category { get; }
    public int[] Tiebreak { get; }

    public HandRank(int category, int[] tiebreak)
    {
        Category = category;
        Tiebreak = tiebreak;
    }

    public int CompareTo(HandRank other)
    {
        int c = Category.CompareTo(other.Category);
        if (c != 0) return c;
        int len = Math.Min(Tiebreak.Length, other.Tiebreak.Length);
        for (int i = 0; i < len; i++)
        {
            int d = Tiebreak[i].CompareTo(other.Tiebreak[i]);
            if (d != 0) return d;
        }
        return Tiebreak.Length.CompareTo(other.Tiebreak.Length);
    }

    public static bool operator >(HandRank a, HandRank b) => a.CompareTo(b) > 0;
    public static bool operator <(HandRank a, HandRank b) => a.CompareTo(b) < 0;
    public static bool operator >=(HandRank a, HandRank b) => a.CompareTo(b) >= 0;
    public static bool operator <=(HandRank a, HandRank b) => a.CompareTo(b) <= 0;
    public static bool operator ==(HandRank a, HandRank b) => a.CompareTo(b) == 0;
    public static bool operator !=(HandRank a, HandRank b) => a.CompareTo(b) != 0;
    public override bool Equals(object? obj) => obj is HandRank r && this == r;
    public override int GetHashCode() => HashCode.Combine(Category, Tiebreak.Length);
}

internal static class PokerEval
{
    private static Dictionary<int, int> RankCounts(int[] ranks)
    {
        var d = new Dictionary<int, int>();
        foreach (int r in ranks)
            d[r] = d.GetValueOrDefault(r, 0) + 1;
        return d;
    }

    /// <summary>Returns the high card of a straight, or -1 if none.</summary>
    private static int IsStraight(int[] ranks)
    {
        var uniq = new SortedSet<int>(ranks);
        if (uniq.Count < 5) return -1;

        // Wheel (A-2-3-4-5): treat Ace as 1
        if (uniq.Contains(14)) uniq.Add(1);

        var desc = uniq.Reverse().ToArray();
        for (int i = 0; i <= desc.Length - 5; i++)
        {
            int hi = desc[i];
            if (hi - desc[i + 4] == 4)
            {
                // Verify 5 consecutive
                bool ok = true;
                for (int j = 1; j < 5; j++)
                    if (desc[i + j] != hi - j) { ok = false; break; }
                if (ok) return hi;
            }
        }
        return -1;
    }

    /// <summary>Evaluate a 5-card hand. Categories: 8=straight flush … 0=high card.</summary>
    public static HandRank Rank5(HoldemCard[] cards)
    {
        int[] ranks = cards.Select(c => c.Rank).OrderByDescending(r => r).ToArray();
        bool isFlush = cards.Select(c => c.Suit).Distinct().Count() == 1;
        int straightHigh = IsStraight(ranks);

        var counts = RankCounts(ranks);
        // groups sorted by (count desc, rank desc)
        var groups = counts.Select(kv => (Count: kv.Value, Rank: kv.Key))
                           .OrderByDescending(g => g.Count)
                           .ThenByDescending(g => g.Rank)
                           .ToArray();

        if (isFlush && straightHigh >= 0)
            return new HandRank(8, new[] { straightHigh });

        if (groups[0].Count == 4)
        {
            int fourRank = groups[0].Rank;
            int kicker = ranks.First(r => r != fourRank);
            return new HandRank(7, new[] { fourRank, kicker });
        }

        if (groups[0].Count == 3 && groups.Length > 1 && groups[1].Count == 2)
            return new HandRank(6, new[] { groups[0].Rank, groups[1].Rank });

        if (isFlush)
            return new HandRank(5, ranks);

        if (straightHigh >= 0)
            return new HandRank(4, new[] { straightHigh });

        if (groups[0].Count == 3)
        {
            int trips = groups[0].Rank;
            int[] kickers = ranks.Where(r => r != trips).OrderByDescending(r => r).ToArray();
            return new HandRank(3, new[] { trips }.Concat(kickers).ToArray());
        }

        if (groups[0].Count == 2 && groups.Length > 1 && groups[1].Count == 2)
        {
            int pairHi = Math.Max(groups[0].Rank, groups[1].Rank);
            int pairLo = Math.Min(groups[0].Rank, groups[1].Rank);
            int kicker = ranks.First(r => r != pairHi && r != pairLo);
            return new HandRank(2, new[] { pairHi, pairLo, kicker });
        }

        if (groups[0].Count == 2)
        {
            int pair = groups[0].Rank;
            int[] kickers = ranks.Where(r => r != pair).OrderByDescending(r => r).ToArray();
            return new HandRank(1, new[] { pair }.Concat(kickers).ToArray());
        }

        return new HandRank(0, ranks);
    }

    /// <summary>Best 5 out of 7 cards.</summary>
    public static HandRank BestRank7(HoldemCard[] cards)
    {
        HandRank best = default;
        bool first = true;
        foreach (var combo in Combinations(cards, 5))
        {
            var r = Rank5(combo);
            if (first || r > best) { best = r; first = false; }
        }
        return best;
    }

    private static IEnumerable<HoldemCard[]> Combinations(HoldemCard[] src, int k)
    {
        int n = src.Length;
        int[] idx = new int[k];
        for (int i = 0; i < k; i++) idx[i] = i;
        while (true)
        {
            var combo = new HoldemCard[k];
            for (int i = 0; i < k; i++) combo[i] = src[idx[i]];
            yield return combo;

            int j = k - 1;
            while (j >= 0 && idx[j] == n - k + j) j--;
            if (j < 0) break;
            idx[j]++;
            for (int m = j + 1; m < k; m++) idx[m] = idx[m - 1] + 1;
        }
    }

    public static string DescribeRank(HandRank rank) => rank.Category switch
    {
        8 => "Straight Flush",
        7 => "Four of a Kind",
        6 => "Full House",
        5 => "Flush",
        4 => "Straight",
        3 => "Three of a Kind",
        2 => "Two Pair",
        1 => "One Pair",
        _ => "High Card",
    };
}

// ════════════════════════════════════════════════════════════════
//  TexasHoldemGameSharp — full port from Python
// ════════════════════════════════════════════════════════════════

public class TexasHoldemGameSharp : BaseGame
{
    public override string ThemeName => "texas_holdem";

    // ── Core game state ────────────────────────────────────────
    private Dictionary<int, int> _stacks = new();
    private int _handId;
    private int? _dealerSeat;
    private const int SmallBlind = 5;
    private const int BigBlind = 10;
    private int _pot;

    private List<HoldemCard> _deck = new();
    private List<HoldemCard> _community = new();
    private Dictionary<int, List<HoldemCard>> _hole = new();
    private Dictionary<int, bool> _inHand = new();

    // ── Betting round ──────────────────────────────────────────
    private string _street = "preflop"; // preflop|flop|turn|river
    private int _currentBet;
    private Dictionary<int, int> _betInRound = new();
    private HashSet<int> _acted = new();
    private int? _turnSeat;

    // ── Showdown ───────────────────────────────────────────────
    private Dictionary<string, object?>? _lastShowdown;
    private Dictionary<int, bool> _revealHole = new();

    // ── Next-hand gating ───────────────────────────────────────
    private Dictionary<int, bool> _nextHandReady = new();
    private int _nextHandReadyHandId;

    // ── Buttons ────────────────────────────────────────────────
    private readonly Dictionary<int, Dictionary<string, (string Text, bool Enabled)>> _buttons = new();

    // ── Animations ─────────────────────────────────────────────
    private readonly ParticleSystem _particles = new();
    private readonly List<CardFlipInPlace> _cardFlips = new();
    private readonly List<CardFlyAnim> _cardFlies = new();
    private readonly List<TextPopAnim> _textPops = new();
    private readonly List<PulseRing> _pulseRings = new();
    private readonly List<ScreenFlash> _flashes = new();
    private object? _animPrevShowdown;
    private int? _animPrevTurnSeat;
    private string _animPrevStreet = "";
    private float _animFwTimer;

    public TexasHoldemGameSharp(int w, int h, Renderer renderer) : base(w, h, renderer) { }

    // ════════════════════════════════════════════════════════════
    //  Lifecycle
    // ════════════════════════════════════════════════════════════

    public override void StartGame(List<int> players)
    {
        var seats = players
            .Where(i => i >= 0 && i <= 7)
            .Distinct()
            .OrderBy(i => i)
            .ToList();
        if (seats.Count < 2) return;

        ActivePlayers = seats;
        _stacks = seats.ToDictionary(s => s, _ => 1000);
        State = "playing";
        _dealerSeat = null;
        _lastShowdown = null;
        StartNewHand();
    }

    // ════════════════════════════════════════════════════════════
    //  Dealing / rounds
    // ════════════════════════════════════════════════════════════

    private List<HoldemCard> BuildDeck()
    {
        var deck = new List<HoldemCard>(52);
        string[] suits = { "S", "H", "D", "C" };
        foreach (var s in suits)
            for (int r = 2; r <= 14; r++)
                deck.Add(new HoldemCard(r, s));
        return deck;
    }

    private void ShuffleList<T>(List<T> list)
    {
        for (int i = list.Count - 1; i > 0; i--)
        {
            int j = Rng.Next(i + 1);
            (list[i], list[j]) = (list[j], list[i]);
        }
    }

    private int? NextSeat(int start, Func<int, bool>? predicate = null)
    {
        if (ActivePlayers.Count == 0) return null;
        int n = ActivePlayers.Count;
        int startI = ActivePlayers.IndexOf(start);
        if (startI < 0) startI = 0;
        for (int step = 1; step <= n; step++)
        {
            int seat = ActivePlayers[(startI + step) % n];
            if (predicate == null || predicate(seat))
                return seat;
        }
        return null;
    }

    private void StartNewHand()
    {
        var seats = ActivePlayers.Where(s => _stacks.GetValueOrDefault(s, 0) > 0).ToList();
        if (seats.Count < 2)
        {
            State = "showdown";
            _lastShowdown = new Dictionary<string, object?>
            {
                ["winners"] = seats.Cast<object>().ToList(),
                ["reason"] = "Not enough players with chips",
            };
            RebuildButtons();
            return;
        }

        _handId++;
        ResetNextHandReady();
        _pot = 0;
        _community = new List<HoldemCard>();
        _hole = seats.ToDictionary(s => s, _ => new List<HoldemCard>());
        _inHand = seats.ToDictionary(s => s, _ => true);
        _betInRound = seats.ToDictionary(s => s, _ => 0);
        _acted = new HashSet<int>();
        _lastShowdown = null;
        _revealHole = seats.ToDictionary(s => s, _ => false);

        // Rotate dealer
        if (_dealerSeat == null)
            _dealerSeat = seats[0];
        else
        {
            var nxt = NextSeat(_dealerSeat.Value, s => seats.Contains(s));
            _dealerSeat = nxt ?? seats[0];
        }

        // Shuffle & deal
        _deck = BuildDeck();
        ShuffleList(_deck);
        for (int round = 0; round < 2; round++)
            foreach (int s in seats)
                _hole[s].Add(PopDeck());

        // Deal card fly animations
        try
        {
            int deckX = ScreenW / 2, deckY = ScreenH / 2 - 40;
            foreach (int s in seats)
            {
                var (sx, sy) = SeatAnchor(s, ScreenW, ScreenH);
                _cardFlies.Add(new CardFlyAnim((deckX, deckY), (sx, sy), color: (30, 80, 30), duration: 0.4f));
            }
        }
        catch { }

        // Post blinds
        int sbSeat = NextSeat(_dealerSeat.Value, s => seats.Contains(s)) ?? _dealerSeat.Value;
        int bbSeat = NextSeat(sbSeat, s => seats.Contains(s)) ?? _dealerSeat.Value;

        _street = "preflop";
        _currentBet = 0;
        PostBlind(sbSeat, SmallBlind);
        PostBlind(bbSeat, BigBlind);
        _currentBet = BigBlind;

        // Action starts left of big blind
        var first = NextSeat(bbSeat,
            s => seats.Contains(s) && _inHand.GetValueOrDefault(s, false) && _stacks.GetValueOrDefault(s, 0) > 0);
        _turnSeat = first;

        if (_turnSeat == null)
        {
            AdvanceStreet();
            return;
        }

        RebuildButtons();
    }

    private void ResetNextHandReady()
    {
        _nextHandReadyHandId = _handId;
        _nextHandReady = new Dictionary<int, bool>();
    }

    private void PostBlind(int seat, int amount)
    {
        if (!_betInRound.ContainsKey(seat)) return;
        int stack = _stacks.GetValueOrDefault(seat, 0);
        int pay = Math.Min(amount, stack);
        _stacks[seat] = stack - pay;
        _betInRound[seat] = _betInRound.GetValueOrDefault(seat, 0) + pay;
        _pot += pay;
    }

    private HoldemCard PopDeck()
    {
        var c = _deck[^1];
        _deck.RemoveAt(_deck.Count - 1);
        return c;
    }

    private void Burn()
    {
        if (_deck.Count > 0) _deck.RemoveAt(_deck.Count - 1);
    }

    private void DealFlop()
    {
        Burn();
        for (int i = 0; i < 3 && _deck.Count > 0; i++)
            _community.Add(PopDeck());

        // Flip animation
        try
        {
            int cw = 78, ch = 110;
            int total = 5 * cw + 4 * 14;
            int sx = ScreenW / 2 - total / 2;
            for (int ci = 0; ci < 3; ci++)
            {
                int fx = sx + ci * (cw + 14) + cw / 2;
                int fy = ScreenH / 2;
                _cardFlips.Add(new CardFlipInPlace(fx, fy, cw, ch, duration: 0.45f));
                _particles.EmitSparkle(fx, fy, (255, 235, 120), 8);
            }
        }
        catch { }
    }

    private void DealTurnRiver()
    {
        Burn();
        if (_deck.Count > 0) _community.Add(PopDeck());

        try
        {
            int ci = _community.Count - 1;
            int cw = 78, ch = 110;
            int total = 5 * cw + 4 * 14;
            int sx = ScreenW / 2 - total / 2;
            int fx = sx + ci * (cw + 14) + cw / 2;
            int fy = ScreenH / 2;
            _cardFlips.Add(new CardFlipInPlace(fx, fy, cw, ch, duration: 0.45f));
            _particles.EmitSparkle(fx, fy, (255, 235, 120), 8);
        }
        catch { }
    }

    private void AdvanceStreet()
    {
        foreach (var s in _betInRound.Keys.ToList())
            _betInRound[s] = 0;
        _currentBet = 0;
        _acted = new HashSet<int>();

        switch (_street)
        {
            case "preflop":
                _street = "flop";
                DealFlop();
                break;
            case "flop":
                _street = "turn";
                DealTurnRiver();
                break;
            case "turn":
                _street = "river";
                DealTurnRiver();
                break;
            default:
                ResolveShowdown();
                return;
        }

        // Next action starts left of dealer
        var seats = _hole.Keys.Where(s => _inHand.GetValueOrDefault(s, false)).ToList();
        var first = NextSeat(
            _dealerSeat ?? 0,
            s => seats.Contains(s) && _inHand.GetValueOrDefault(s, false) && _stacks.GetValueOrDefault(s, 0) > 0);
        _turnSeat = first;

        if (_turnSeat == null && State == "playing")
        {
            AdvanceStreet();
            return;
        }

        RebuildButtons();
    }

    // ════════════════════════════════════════════════════════════
    //  Actions
    // ════════════════════════════════════════════════════════════

    private void DoCheckCall(int seat)
    {
        int need = Math.Max(0, _currentBet - _betInRound.GetValueOrDefault(seat, 0));
        if (need <= 0) { _acted.Add(seat); return; }
        int stack = _stacks.GetValueOrDefault(seat, 0);
        int pay = Math.Min(need, stack);
        _stacks[seat] = stack - pay;
        _betInRound[seat] = _betInRound.GetValueOrDefault(seat, 0) + pay;
        _pot += pay;
        _acted.Add(seat);
    }

    private int RaiseSize() => BigBlind;

    private void DoBetRaise(int seat)
    {
        int raiseAmt = RaiseSize();
        int target = _currentBet > 0 ? _currentBet + raiseAmt : raiseAmt;
        int required = Math.Max(0, target - _betInRound.GetValueOrDefault(seat, 0));
        int stack = _stacks.GetValueOrDefault(seat, 0);

        if (required <= 0 || stack < required) { DoCheckCall(seat); return; }

        _stacks[seat] = stack - required;
        _betInRound[seat] = _betInRound.GetValueOrDefault(seat, 0) + required;
        _pot += required;
        _currentBet = target;
        _acted = new HashSet<int> { seat };

        // Raise animation
        try
        {
            var (sx, sy) = SeatAnchor(seat, ScreenW, ScreenH);
            var col = GameConfig.PlayerColors[seat % GameConfig.PlayerColors.Length];
            _textPops.Add(new TextPopAnim($"RAISE ${required}", sx, sy - 30, col, fontSize: 22));
            _particles.EmitSparkle(sx, sy, col, 8);
        }
        catch { }
    }

    private void DoAllIn(int seat)
    {
        int stack = _stacks.GetValueOrDefault(seat, 0);
        if (stack <= 0) { _acted.Add(seat); return; }

        _stacks[seat] = 0;
        _betInRound[seat] = _betInRound.GetValueOrDefault(seat, 0) + stack;
        _pot += stack;

        if (_betInRound.GetValueOrDefault(seat, 0) > _currentBet)
        {
            _currentBet = _betInRound[seat];
            _acted = new HashSet<int> { seat };
            return;
        }

        _acted.Add(seat);
    }

    private void HandleBetAmount(int seat, int raiseBy)
    {
        if (State != "playing") return;
        if (_turnSeat == null || seat != _turnSeat.Value) return;
        if (!_inHand.GetValueOrDefault(seat, false)) return;

        int stack = _stacks.GetValueOrDefault(seat, 0);
        if (stack <= 0) return;
        if (raiseBy < 0) return;

        int callAmt = Math.Max(0, _currentBet - _betInRound.GetValueOrDefault(seat, 0));
        int pay = Math.Min(stack, callAmt + raiseBy);

        if (pay <= 0)
        {
            _acted.Add(seat);
            AfterAction(seat);
            return;
        }

        _stacks[seat] = stack - pay;
        _betInRound[seat] = _betInRound.GetValueOrDefault(seat, 0) + pay;
        _pot += pay;

        if (_betInRound.GetValueOrDefault(seat, 0) > _currentBet)
        {
            _currentBet = _betInRound[seat];
            _acted = new HashSet<int> { seat };
        }
        else
        {
            _acted.Add(seat);
        }

        AfterAction(seat);
    }

    private void AfterAction(int seat)
    {
        // Only one player left → award pot
        var remaining = _inHand.Where(kv => kv.Value).Select(kv => kv.Key).ToList();
        if (remaining.Count <= 1)
        {
            int winner = remaining.Count > 0 ? remaining[0] : seat;
            _stacks[winner] = _stacks.GetValueOrDefault(winner, 0) + _pot;
            _lastShowdown = new Dictionary<string, object?>
            {
                ["winners"] = new List<object> { winner },
                ["descriptions"] = new Dictionary<string, string> { [winner.ToString()] = "Uncontested" },
                ["pot"] = _pot,
            };
            _pot = 0;
            State = "showdown";
            _turnSeat = null;
            RebuildButtons();
            return;
        }

        // Betting round complete?
        var inPlayers = _hole.Keys.Where(s => _inHand.GetValueOrDefault(s, false)).ToList();
        var activeBettors = inPlayers.Where(s => _stacks.GetValueOrDefault(s, 0) > 0).ToList();
        if (activeBettors.All(s => _betInRound.GetValueOrDefault(s, 0) == _currentBet)
            && activeBettors.All(s => _acted.Contains(s)))
        {
            AdvanceStreet();
            return;
        }

        // Advance turn
        bool NeedsAction(int s)
        {
            if (!_inHand.GetValueOrDefault(s, false)) return false;
            if (_stacks.GetValueOrDefault(s, 0) <= 0) return false;
            if (!_acted.Contains(s)) return true;
            return _betInRound.GetValueOrDefault(s, 0) != _currentBet;
        }

        var nxt = NextSeat(seat, NeedsAction);
        if (nxt.HasValue)
            _turnSeat = nxt.Value;
        else
        {
            var fallback = inPlayers.FirstOrDefault(s => NeedsAction(s), -1);
            _turnSeat = fallback >= 0 ? fallback : null;
        }

        RebuildButtons();
    }

    private bool IsHandOver() => State == "showdown" || _lastShowdown != null;

    private void ResolveShowdown()
    {
        var seats = _hole.Keys.Where(s => _inHand.GetValueOrDefault(s, false)).ToList();
        if (seats.Count == 0)
        {
            _lastShowdown = new Dictionary<string, object?> { ["winners"] = new List<object>(), ["pot"] = _pot };
            _pot = 0;
            State = "showdown";
            _turnSeat = null;
            RebuildButtons();
            return;
        }

        var ranks = new Dictionary<int, HandRank>();
        var desc = new Dictionary<string, string>();
        foreach (int s in seats)
        {
            var seven = (_hole.GetValueOrDefault(s) ?? new List<HoldemCard>())
                .Concat(_community).ToArray();
            var r = PokerEval.BestRank7(seven);
            ranks[s] = r;
            desc[s.ToString()] = PokerEval.DescribeRank(r);
        }

        var best = ranks.Values.Max();
        var winners = ranks.Where(kv => kv.Value == best).Select(kv => kv.Key).ToList();

        if (winners.Count > 0)
        {
            int share = _pot / winners.Count;
            foreach (int w in winners)
                _stacks[w] = _stacks.GetValueOrDefault(w, 0) + share;
        }

        _lastShowdown = new Dictionary<string, object?>
        {
            ["winners"] = winners.Cast<object>().ToList(),
            ["descriptions"] = desc,
            ["pot"] = _pot,
        };
        _pot = 0;
        State = "showdown";
        _turnSeat = null;
        RebuildButtons();
    }

    // ════════════════════════════════════════════════════════════
    //  HandleClick (web UI)
    // ════════════════════════════════════════════════════════════

    public override void HandleClick(int playerIdx, string buttonId)
    {
        int seat = playerIdx;

        // Game-specific messages from server passthrough
        if (buttonId.StartsWith("__msg__:"))
        {
            var parts = buttonId.Split(':', 3);
            if (parts.Length >= 2)
            {
                string msgType = parts[1];
                string json = parts.Length > 2 ? parts[2] : "";

                if (msgType == "texas_holdem_bet")
                {
                    try
                    {
                        using var doc = JsonDocument.Parse(json);
                        int amount = doc.RootElement.GetProperty("amount").GetInt32();
                        HandleBetAmount(seat, amount);
                    }
                    catch { }
                    return;
                }
            }
        }

        if (State == "player_select") return;

        if (buttonId == "toggle_reveal")
        {
            if (State == "showdown" && ActivePlayers.Contains(seat))
            {
                _revealHole[seat] = !_revealHole.GetValueOrDefault(seat, false);
                RebuildButtons();
            }
            return;
        }

        if (buttonId == "next_hand")
        {
            if ((State == "showdown" || State == "playing") && IsHandOver())
            {
                if (_nextHandReadyHandId != _handId) ResetNextHandReady();

                var required = ActivePlayers.ToList();
                _nextHandReady[seat] = true;

                if (required.All(s => _nextHandReady.GetValueOrDefault(s, false)))
                {
                    State = "playing";
                    StartNewHand();
                }
                else
                {
                    RebuildButtons();
                }
            }
            return;
        }

        if (buttonId == "all_in")
        {
            if (State == "playing" && _turnSeat.HasValue && seat == _turnSeat.Value
                && _inHand.GetValueOrDefault(seat, false))
            {
                DoAllIn(seat);

                try
                {
                    int cx = ScreenW / 2, cy = ScreenH / 2;
                    _textPops.Add(new TextPopAnim("\U0001f4a5 ALL IN!", cx, cy - 35, (255, 130, 50), fontSize: 34));
                    _flashes.Add(new ScreenFlash((180, 80, 20), 35, 0.35f));
                    _pulseRings.Add(new PulseRing(cx, cy, (255, 130, 50), 80, 0.7f));
                }
                catch { }

                AfterAction(seat);
            }
            return;
        }

        if (State != "playing") return;
        if (!_turnSeat.HasValue || seat != _turnSeat.Value) return;
        if (!_inHand.GetValueOrDefault(seat, false)) return;
        if (_stacks.GetValueOrDefault(seat, 0) <= 0) return;

        switch (buttonId)
        {
            case "fold":
                _inHand[seat] = false;
                _acted.Add(seat);
                try
                {
                    int cx = ScreenW / 2, cy = ScreenH / 2;
                    _textPops.Add(new TextPopAnim("\U0001f494 Fold", cx, cy - 30, (180, 80, 80), fontSize: 26));
                    _flashes.Add(new ScreenFlash((100, 30, 30), 22, 0.22f));
                }
                catch { }
                AfterAction(seat);
                break;

            case "check_call":
                DoCheckCall(seat);
                AfterAction(seat);
                break;

            case "bet_raise":
                DoBetRaise(seat);
                AfterAction(seat);
                break;
        }
    }

    // ════════════════════════════════════════════════════════════
    //  Player quit
    // ════════════════════════════════════════════════════════════

    public void HandlePlayerQuit(int seat)
    {
        if (State == "player_select") return;
        if (!ActivePlayers.Contains(seat)) return;

        // Fold if in-hand
        try
        {
            if (State == "playing" && _inHand.GetValueOrDefault(seat, false))
            {
                _inHand[seat] = false;
                _acted.Add(seat);
                AfterAction(seat);
            }
        }
        catch { }

        var remaining = ActivePlayers.Where(x => x != seat).ToList();
        ActivePlayers = remaining;

        _hole.Remove(seat);
        _inHand.Remove(seat);
        _betInRound.Remove(seat);
        _revealHole.Remove(seat);
        _acted.Remove(seat);

        int stack = _stacks.GetValueOrDefault(seat, 0);
        _stacks.Remove(seat);
        if (remaining.Count > 0 && stack > 0)
        {
            int share = stack / remaining.Count;
            if (share > 0)
                foreach (int r in remaining)
                    _stacks[r] = _stacks.GetValueOrDefault(r, 0) + share;
        }

        if (_dealerSeat == seat)
            _dealerSeat = remaining.Count > 0 ? remaining[0] : null;
        if (_turnSeat == seat)
        {
            var inPlayers = _hole.Keys.Where(s => _inHand.GetValueOrDefault(s, false)).ToList();
            if (inPlayers.Count > 0)
            {
                var nxt = NextSeat(seat, s => _inHand.GetValueOrDefault(s, false));
                _turnSeat = nxt ?? inPlayers[0];
            }
            else
                _turnSeat = null;
        }

        try
        {
            var seatsWithChips = ActivePlayers.Where(p => _stacks.GetValueOrDefault(p, 0) > 0).ToList();
            if (State == "playing" && seatsWithChips.Count < 2)
            {
                StartNewHand();
                return;
            }
        }
        catch { }

        RebuildButtons();
    }

    // ════════════════════════════════════════════════════════════
    //  Buttons
    // ════════════════════════════════════════════════════════════

    private void RebuildButtons()
    {
        _buttons.Clear();
        foreach (int s in ActivePlayers)
            _buttons[s] = new Dictionary<string, (string, bool)>();

        if (State == "showdown" && IsHandOver())
        {
            foreach (int s in ActivePlayers)
            {
                bool already = _nextHandReadyHandId == _handId && _nextHandReady.GetValueOrDefault(s, false);
                _buttons[s]["next_hand"] = ("Next Hand", !already);
                _buttons[s]["return_to_lobby"] = ("Return to Lobby", true);
                bool show = _revealHole.GetValueOrDefault(s, false);
                _buttons[s]["toggle_reveal"] = (show ? "Hide Cards" : "Show Cards", true);
            }
            return;
        }

        if (State != "playing") return;

        foreach (int s in ActivePlayers)
        {
            bool isTurn = _turnSeat.HasValue && s == _turnSeat.Value;
            bool alive = _inHand.GetValueOrDefault(s, false);
            bool hasChips = _stacks.GetValueOrDefault(s, 0) > 0;
            bool canAct = isTurn && alive && hasChips;

            int callAmt = Math.Max(0, _currentBet - _betInRound.GetValueOrDefault(s, 0));
            string ccText = callAmt <= 0 ? "Check" : $"Call {callAmt}";

            _buttons[s]["check_call"] = (ccText, canAct);
            _buttons[s]["bet_raise"] = ("Bet/Raise", canAct && _stacks.GetValueOrDefault(s, 0) > callAmt);
            _buttons[s]["all_in"] = ("All-in", canAct && _stacks.GetValueOrDefault(s, 0) > 0);
            _buttons[s]["fold"] = ("Fold", canAct);
        }
    }

    // ════════════════════════════════════════════════════════════
    //  Snapshot / State for Web UI
    // ════════════════════════════════════════════════════════════

    public override Dictionary<string, object?> GetSnapshot(int playerIdx)
    {
        int seat = playerIdx;
        var players = new List<Dictionary<string, object?>>();
        foreach (int s in ActivePlayers)
        {
            int stack = _stacks.GetValueOrDefault(s, 0);
            bool alive = _inHand.GetValueOrDefault(s, false);
            string status;
            if (stack <= 0 && alive) status = "all-in";
            else if (stack <= 0) status = "bust";
            else status = alive ? "in" : "fold";

            players.Add(new Dictionary<string, object?>
            {
                ["seat"] = s,
                ["name"] = PlayerName(s),
                ["stack"] = _stacks.GetValueOrDefault(s, 0),
                ["status"] = status,
                ["bet"] = _betInRound.GetValueOrDefault(s, 0),
            });
        }

        var myHole = _hole.ContainsKey(seat)
            ? _hole[seat].Select(c => c.Short()).ToList()
            : new List<string>();

        var comm = _community.Select(c => c.Short()).ToList();

        var revealedHoles = new Dictionary<string, object?>();
        if (State == "showdown")
        {
            foreach (int s in ActivePlayers)
            {
                if (_revealHole.GetValueOrDefault(s, false) && _hole.ContainsKey(s) && _hole[s].Count > 0)
                    revealedHoles[s.ToString()] = _hole[s].Select(c => c.Short()).ToList();
            }
        }

        int? callAmount = null;
        if (_turnSeat.HasValue && seat == _turnSeat.Value && State == "playing" && _inHand.GetValueOrDefault(seat, false))
        {
            callAmount = Math.Max(0, _currentBet - _betInRound.GetValueOrDefault(seat, 0));
        }

        var snap = new Dictionary<string, object?>
        {
            ["state"] = State,
            ["street"] = _street,
            ["hand_id"] = _handId,
            ["dealer_seat"] = _dealerSeat,
            ["turn_seat"] = _turnSeat,
            ["pot"] = _pot,
            ["current_bet"] = _currentBet,
            ["call_amount"] = callAmount,
            ["community"] = comm,
            ["your_hole"] = myHole,
            ["revealed_holes"] = revealedHoles,
            ["players"] = players,
            ["showdown"] = _lastShowdown,
        };

        return new Dictionary<string, object?> { ["texas_holdem"] = snap };
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

    // ════════════════════════════════════════════════════════════
    //  Update & Draw
    // ════════════════════════════════════════════════════════════

    public override void Update(double dt)
    {
        float fdt = (float)dt;
        _particles.Update(fdt);

        for (int i = _cardFlips.Count - 1; i >= 0; i--)
        {
            _cardFlips[i].Update(fdt);
            if (_cardFlips[i].Done) _cardFlips.RemoveAt(i);
        }
        for (int i = _textPops.Count - 1; i >= 0; i--)
        {
            _textPops[i].Update(fdt);
            if (_textPops[i].Done) _textPops.RemoveAt(i);
        }
        for (int i = _pulseRings.Count - 1; i >= 0; i--)
        {
            _pulseRings[i].Update(fdt);
            if (_pulseRings[i].Done) _pulseRings.RemoveAt(i);
        }
        for (int i = _flashes.Count - 1; i >= 0; i--)
        {
            _flashes[i].Update(fdt);
            if (_flashes[i].Done) _flashes.RemoveAt(i);
        }
        for (int i = _cardFlies.Count - 1; i >= 0; i--)
        {
            _cardFlies[i].Update(fdt);
            if (_cardFlies[i].Done) _cardFlies.RemoveAt(i);
        }

        // Fireworks on new showdown
        if (_lastShowdown != null && !ReferenceEquals(_lastShowdown, _animPrevShowdown))
        {
            _animPrevShowdown = _lastShowdown;
            int cx = ScreenW / 2, cy = ScreenH / 2;
            for (int j = 0; j < 8; j++)
                _particles.EmitFirework(
                    cx + Rng.Next(-120, 121), cy + Rng.Next(-80, 81),
                    AnimPalette.Rainbow);
            _flashes.Add(new ScreenFlash((255, 220, 80), 60, 1.0f));

            if (_lastShowdown.TryGetValue("winners", out var wObj) && wObj is List<object> winnersList && winnersList.Count > 0)
            {
                try
                {
                    string names = string.Join(" & ", winnersList.Select(w => PlayerName(Convert.ToInt32(w))));
                    _textPops.Add(new TextPopAnim($"\U0001f3c6 {names}!", cx, cy - 60, (255, 220, 80), fontSize: 32));
                }
                catch { }
            }
            _animFwTimer = 5.0f;
        }

        if (_animFwTimer > 0)
        {
            _animFwTimer = MathF.Max(0f, _animFwTimer - fdt);
            if ((int)(_animFwTimer * 3) % 2 == 0)
            {
                int cx = ScreenW / 2, cy = ScreenH / 2;
                _particles.EmitFirework(
                    cx + Rng.Next(-150, 151), cy + Rng.Next(-100, 101),
                    AnimPalette.Rainbow);
            }
        }

        // Turn-change pulse ring
        if (State == "playing" && _turnSeat.HasValue && _turnSeat != _animPrevTurnSeat)
        {
            _animPrevTurnSeat = _turnSeat;
            try
            {
                var (ax, ay) = SeatAnchor(_turnSeat.Value, ScreenW, ScreenH);
                _pulseRings.Add(new PulseRing(ax, ay, (130, 230, 130), 55, 0.9f));
            }
            catch { }
        }

        // Street-change flash
        if (State == "playing" && _street != _animPrevStreet)
        {
            _animPrevStreet = _street;
            var streetColors = new Dictionary<string, (int, int, int)>
            {
                ["flop"] = (60, 200, 120),
                ["turn"] = (80, 160, 230),
                ["river"] = (230, 200, 60),
            };
            if (streetColors.TryGetValue(_street, out var sc))
            {
                try
                {
                    _flashes.Add(new ScreenFlash(sc, 55, 0.4f));
                    int scx = ScreenW / 2, scy = ScreenH / 2;
                    _textPops.Add(new TextPopAnim(_street.ToUpper(), scx, scy - 80, sc, fontSize: 28));
                }
                catch { }
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

        CardRendering.DrawGameBackground(r, width, height, "texas_holdem");

        // Title + status
        RainbowTitle.Draw(r, "TEXAS HOLD'EM", width);
        if (State != "player_select")
        {
            string turn = _turnSeat.HasValue ? PlayerName(_turnSeat.Value) : "\u2014";
            r.DrawText($"Hand {_handId}  \u00b7  Street: {_street}  \u00b7  Turn: {turn}",
                24, 54, 14, (200, 200, 200), anchorX: "left", anchorY: "top");
        }

        // Table felt
        int pad = Math.Min(width, height) * 10 / 100;
        int tx = pad, ty = pad, tw = width - pad * 2, th = height - pad * 2;
        r.DrawRect((0, 0, 0), (tx + 4, ty + 4, tw, th), alpha: 50);
        r.DrawRect((0, 60, 36), (tx, ty, tw, th), alpha: 200);
        int ip = Math.Max(6, Math.Min(tw, th) * 4 / 100);
        r.DrawRect((6, 85, 45), (tx + ip, ty + ip, tw - 2 * ip, th - 2 * ip), alpha: 80);
        int gcx = tx + tw / 2, gcy = ty + th / 2;
        r.DrawCircle((12, 110, 55), (gcx, gcy), Math.Min(tw, th) * 28 / 100, alpha: 25);
        r.DrawRect((190, 170, 90), (tx, ty, tw, th), width: 4, alpha: 140);
        r.DrawRect((240, 220, 130), (tx + 3, ty + 3, tw - 6, th - 6), width: 1, alpha: 60);

        // Community cards
        int cx = width / 2, cy = height / 2;
        int cardW = 78, cardH = 110, gap = 14;
        int totalW = 5 * cardW + 4 * gap;
        int startX = cx - totalW / 2;
        for (int i = 0; i < 5; i++)
        {
            int x = startX + i * (cardW + gap);
            int y = cy - cardH / 2;
            string label = i < _community.Count ? _community[i].Short() : "";
            bool face = label.Length > 0;
            CardRendering.DrawPlayingCard(r, (x, y, cardW, cardH), label, face);
        }

        // Pot
        string potTxt = $"Pot: {_pot}";
        int pw = Math.Max(100, potTxt.Length * 11);
        int ph = 28;
        int px = cx - pw / 2;
        int py = cy + cardH / 2 + 14;
        r.DrawRect((0, 0, 0), (px, py, pw, ph), alpha: 130);
        r.DrawRect((255, 215, 0), (px, py, pw, ph), width: 1, alpha: 80);
        r.DrawText(potTxt, cx, py + ph / 2, 16, (255, 230, 140), anchorX: "center", anchorY: "center");

        // Showdown winners
        if (_lastShowdown is { } sd && sd.TryGetValue("winners", out var wObj2)
            && wObj2 is List<object> wList && wList.Count > 0)
        {
            string msg = "\U0001f3c6 Winners: " + string.Join(", ", wList.Select(w => PlayerName(Convert.ToInt32(w))));
            int mw = Math.Max(200, msg.Length * 10);
            int mh = 30;
            int mx = cx - mw / 2;
            int my = cy - cardH / 2 - 40;
            r.DrawRect((0, 0, 0), (mx, my, mw, mh), alpha: 160);
            r.DrawRect((255, 215, 0), (mx, my, mw, mh), width: 1, alpha: 100);
            r.DrawText(msg, cx, my + mh / 2, 15, (255, 235, 140), anchorX: "center", anchorY: "center");
        }

        // Revealed hole cards at showdown
        if (State == "showdown")
            DrawRevealedHoles(r, width, height, cx, cy, cardH);

        // Per-seat info zones
        if (State is "playing" or "showdown")
            DrawSeatZones(r, width, height);

        // Animations
        foreach (var cfy in _cardFlies) cfy.Draw(r);
        _particles.Draw(r);
        foreach (var pr in _pulseRings) pr.Draw(r);
        foreach (var cf in _cardFlips) cf.Draw(r);
        foreach (var fl in _flashes) fl.Draw(r, width, height);
        foreach (var tp in _textPops) tp.Draw(r);
    }

    // ── Drawing helpers ────────────────────────────────────────

    private void DrawRevealedHoles(Renderer r, int w, int h, int cx, int cy, int cardH)
    {
        var revealed = new List<(int Seat, string Name, List<string> Cards)>();
        foreach (int s in ActivePlayers)
        {
            if (_revealHole.GetValueOrDefault(s, false) && _hole.ContainsKey(s) && _hole[s].Count > 0)
            {
                var cards = _hole[s].Take(2).Select(c => c.Short()).ToList();
                if (cards.Count > 0) revealed.Add((s, PlayerName(s), cards));
            }
        }
        if (revealed.Count == 0) return;

        int rw = Math.Max(78, Math.Min(110, w * 90 / 1000));
        int rh = (int)(rw * 1.38);
        int rgap = Math.Max(12, rw * 14 / 100);
        int padX = 16, padY = 14, labelH = 18, boxGap = 16;
        int boxH = rh + labelH + padY * 2;
        int boxW = padX * 2 + 2 * rw + rgap;

        int communityTop = cy - cardH / 2;
        int communityBottom = cy + cardH / 2;
        int minBottomTop = communityBottom + 24;
        int bottomMargin = 22;
        int bottomTop = h - bottomMargin - boxH;
        bool canDrawBottom = bottomTop >= minBottomTop;
        int topTop = 86;
        bool canDrawTop = (topTop + boxH) <= (communityTop - 18);

        int availW = Math.Max(0, w - 32);
        int perRow = Math.Max(1, (availW + boxGap) / (boxW + boxGap));

        List<(int, string, List<string>)> bottomItems, topItems;
        if (canDrawBottom)
        {
            bottomItems = revealed.Take(perRow).ToList();
            topItems = canDrawTop ? revealed.Skip(perRow).Take(perRow).ToList() : new();
        }
        else
        {
            bottomItems = new();
            topItems = canDrawTop ? revealed.Take(perRow).ToList() : new();
        }

        void DrawRow(List<(int Seat, string Name, List<string> Cards)> items, int top)
        {
            if (items.Count == 0) return;
            int rowW = items.Count * boxW + (items.Count - 1) * boxGap;
            int left0 = (w - rowW) / 2;
            for (int idx = 0; idx < items.Count; idx++)
            {
                var (seat, name, cards) = items[idx];
                int left = left0 + idx * (boxW + boxGap);
                var col = GameConfig.PlayerColors[seat % GameConfig.PlayerColors.Length];
                r.DrawRect((10, 10, 12), (left, top, boxW, boxH), alpha: 160);
                r.DrawRect(col, (left, top, boxW, boxH), width: 3, alpha: 220);
                r.DrawText(name, left + boxW / 2, top + padY, 14, (235, 235, 235), anchorX: "center", anchorY: "top");
                int cardsY = top + padY + labelH;
                int cardsX = left + padX;
                for (int j = 0; j < Math.Min(2, cards.Count); j++)
                    CardRendering.DrawPlayingCard(r, (cardsX + j * (rw + rgap), cardsY, rw, rh), cards[j], true);
            }
        }

        if (canDrawBottom) DrawRow(bottomItems, bottomTop);
        if (canDrawTop) DrawRow(topItems, topTop);
    }

    private static (int X, int Y) SeatAnchor(int seat, int w, int h)
    {
        return seat switch
        {
            0 => (w * 22 / 100, h * 87 / 100),
            1 => (w * 50 / 100, h * 87 / 100),
            2 => (w * 78 / 100, h * 87 / 100),
            3 => (w * 22 / 100, h * 13 / 100),
            4 => (w * 50 / 100, h * 13 / 100),
            5 => (w * 78 / 100, h * 13 / 100),
            6 => (w * 9 / 100, h * 50 / 100),
            7 => (w * 91 / 100, h * 50 / 100),
            _ => (w / 2, h / 2),
        };
    }

    private void DrawSeatZones(Renderer r, int w, int h)
    {
        foreach (int s in ActivePlayers)
        {
            var (ax, ay) = SeatAnchor(s, w, h);
            bool isTurn = State == "playing" && _turnSeat.HasValue && _turnSeat.Value == s;
            bool alive = State == "playing" ? _inHand.GetValueOrDefault(s, false) : true;
            int stack = _stacks.GetValueOrDefault(s, 0);
            int bet = _betInRound.GetValueOrDefault(s, 0);

            int bw = 120, bh = 54;
            int bx = ax - bw / 2, by = ay - bh / 2;

            var bg = isTurn ? (16, 70, 42) : (14, 22, 32);
            var border = isTurn ? (100, 220, 110) : (alive ? (170, 170, 170) : (80, 80, 80));

            r.DrawRect((0, 0, 0), (bx + 3, by - 3, bw, bh), alpha: 70);
            r.DrawRect(bg, (bx, by, bw, bh), alpha: 210);
            if (isTurn)
                r.DrawRect(border, (bx - 2, by - 2, bw + 4, bh + 4), width: 2, alpha: 50);
            r.DrawRect(border, (bx, by, bw, bh), width: isTurn ? 2 : 1, alpha: 220);

            var pcol = GameConfig.PlayerColors[s % GameConfig.PlayerColors.Length];
            r.DrawCircle(pcol, (bx + 10, by + bh / 2), 4, alpha: 180);

            var nameCol = isTurn ? (100, 255, 100) : (alive ? pcol : (110, 110, 110));
            r.DrawText(PlayerName(s), ax, by + 9, 12, nameCol, anchorX: "center", anchorY: "top");

            string statusTxt;
            if (!alive && State == "playing") statusTxt = "FOLD";
            else if (stack == 0 && alive) statusTxt = "ALL-IN";
            else statusTxt = $"\U0001f4b0${stack}" + (bet > 0 ? $"  \U0001f3b2{bet}" : "");
            r.DrawText(statusTxt, ax, by + bh - 9, 11, (210, 210, 210), anchorX: "center", anchorY: "bottom");
        }
    }
}
