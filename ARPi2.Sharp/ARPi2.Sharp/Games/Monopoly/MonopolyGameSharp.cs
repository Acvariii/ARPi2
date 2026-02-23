using System;
using System.Collections.Generic;
using System.Linq;
using ARPi2.Sharp.Core;

namespace ARPi2.Sharp.Games.Monopoly;

// ═══════════════════════════════════════════════════════════════════════════
//  Toast & Sparkle helpers
// ═══════════════════════════════════════════════════════════════════════════
internal sealed class ToastEntry
{
    public string Text = "";
    public (int R, int G, int B) Color = (255, 255, 255);
    public double Ts;
    public double Ttl = 3.0;
}

internal sealed class ToastSparkle
{
    public double X0, Y0, Vx, Vy, Ts, Ttl, Size;
    public (int R, int G, int B) Color;
}

// ═══════════════════════════════════════════════════════════════════════════
//  Token animation data
// ═══════════════════════════════════════════════════════════════════════════
internal sealed class TokenAnim
{
    public List<int> Path = new();
    public int StartPos;
    public double StartTime;
    public double SegmentDuration = 0.5;
}

/// <summary>
/// Full-fidelity C# / MonoGame port of the Python MonopolyGame class.
/// Board rendering, 3D dice, toast system, popups, trade, auction, debt — everything.
/// </summary>
public sealed class MonopolyGameSharp : BaseGame
{
    public override string ThemeName => "monopoly";
    public override UniversalPopup? Popup => _popup;

    // ─── Board geometry ────────────────────────────────────────────────
    private (int X, int Y, int W, int H) _boardRect;
    private readonly List<(int X, int Y, int W, int H)> _spaces = new();

    // ─── Domain objects ────────────────────────────────────────────────
    private readonly List<Property> _properties = new();
    private readonly List<MonopolyPlayer> _players = new();
    private List<CardData> _communityDeck = new();
    private List<CardData> _chanceDeck = new();

    // ─── Turn state ────────────────────────────────────────────────────
    private int _currentPlayerIdx;
    private string _phase = "roll";   // roll, buying, paying_rent, building, action
    private bool _canRoll = true;
    private (int D1, int D2) _diceValues = (0, 0);
    private bool _diceRolling;
    private double _diceRollStart;
    private int? _pendingLandIdx;
    private int? _pendingPostCardLandIdx;
    private int? _winnerIdx;

    // ─── Dice fly-in ───────────────────────────────────────────────────
    private (int X, int Y) _diceFlyFrom;
    private double _diceFlyStart;

    // ─── UI chrome ─────────────────────────────────────────────────────
    private readonly Dictionary<int, PlayerPanel> _panels = new();
    private readonly Dictionary<int, Dictionary<string, GameButton>> _buttons = new();
    private UniversalPopup _popup = new();
    private int _mortgageScrollIndex;

    // ─── Toasts ────────────────────────────────────────────────────────
    private readonly List<ToastEntry> _toasts = new();
    private readonly List<ToastSparkle> _sparkles = new();

    // ─── Card banner ───────────────────────────────────────────────────
    private string? _cardBannerDeck;
    private string? _cardBannerText;
    private double _cardBannerTs;
    private double? _cardPopupAutoCloseAt;

    // ─── Token animation ───────────────────────────────────────────────
    private readonly Dictionary<int, TokenAnim> _tokenAnims = new();

    // ─── Auction ───────────────────────────────────────────────────────
    private bool _auctionActive;
    private int _auctionProperty;
    private int? _auctionBidder;
    private int _auctionBid;
    private int _auctionBidderIndex;
    private List<int> _auctionActiveBidders = new();

    // ─── Trade ─────────────────────────────────────────────────────────
    private int? _tradeInitiator, _tradePartner;
    private int _tradeOfferMoney, _tradeRequestMoney;
    private List<int> _tradeOfferProps = new(), _tradeRequestProps = new();
    private int _tradeScrollIndex;
    private string? _tradeMode;   // select_partner, build_offer, await_response
    private string _tradeViewMode = "money";
    private int _tradeGiveScroll, _tradeGetScroll;

    // ─── Debt ──────────────────────────────────────────────────────────
    private bool _debtActive;
    private int? _debtPlayerIdx;
    private int _debtAmount;
    private int? _debtOwedTo;
    private bool _debtToFreeParking = true;
    private string _debtAfter = "";
    private Dictionary<string, object> _debtAfterData = new();

    // ─── Supply ────────────────────────────────────────────────────────
    private int _housesRemaining = 32;
    private int _hotelsRemaining = 12;
    private int _freeParkingPot;

    // ─── Animations ────────────────────────────────────────────────────
    private readonly ParticleSystem _particles = new();
    private readonly List<TextPopAnim> _textPops = new();
    private readonly List<PulseRing> _pulseRings = new();
    private readonly List<ScreenFlash> _flashes = new();
    private readonly List<CardFlipInPlace> _cardFlips = new();
    private readonly AmbientSystem _ambient;
    private readonly LightBeamSystem _lightBeams = LightBeamSystem.ForTheme("monopoly");
    private readonly VignettePulse _vignette = new();
    private readonly Starfield _starfield;
    private readonly FloatingIconSystem _floatingIcons = FloatingIconSystem.ForTheme("monopoly");
    private readonly WaveBand _waveBand = WaveBand.ForTheme("monopoly");
    private readonly HeatShimmer _heatShimmer = HeatShimmer.ForTheme("monopoly");
    private bool _animPrevGameOver;
    private float _animFwTimer;

    // ─── Clock ─────────────────────────────────────────────────────────
    private double _clock; // monotonic seconds since game start

    // ═══════════════════════════════════════════════════════════════════════
    //  Constructor
    // ═══════════════════════════════════════════════════════════════════════
    public MonopolyGameSharp(int w, int h, Renderer renderer) : base(w, h, renderer)
    {
        // Build property data for all 40 spaces
        var board = MonopolyData.BuildBoard();
        for (int i = 0; i < 40; i++)
            _properties.Add(new Property(board.TryGetValue(i, out var d) ? d : new SpaceData { Name = "", Type = "none" }));

        _communityDeck = new List<CardData>(MonopolyData.GetCommunityChestCards());
        _chanceDeck = new List<CardData>(MonopolyData.GetChanceCards());
        MonopolyLogic.Shuffle(_communityDeck, Rng);
        MonopolyLogic.Shuffle(_chanceDeck, Rng);

        for (int i = 0; i < 8; i++)
            _players.Add(new MonopolyPlayer(i, GameConfig.PlayerColors[i]));

        _ambient = AmbientSystem.ForTheme("monopoly", w, h);
        _starfield = Starfield.ForTheme("monopoly", w, h);

        CalculateBoardGeometry();
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  Board geometry
    // ═══════════════════════════════════════════════════════════════════════
    private void CalculateBoardGeometry()
    {
        int hPanel = (int)(ScreenH * 0.10);
        int vPanel = (int)(ScreenW * 0.12);
        int margin = 20;
        int availW = ScreenW - 2 * vPanel - 2 * margin;
        int availH = ScreenH - 2 * hPanel - 2 * margin;
        int size = Math.Min(availW, availH);
        int x = vPanel + margin + (availW - size) / 2;
        int y = hPanel + margin + (availH - size) / 2;
        _boardRect = (x, y, size, size);
        CalculateSpaces();
    }

    private void CalculateSpaces()
    {
        _spaces.Clear();
        var (bx, by, size, _) = _boardRect;
        int corner = size / 11;
        int edge = size / 11;

        int SpaceW(int idx, bool isCorner) => isCorner ? corner : edge;

        // Bottom row (0–10): right → left
        for (int i = 0; i <= 10; i++)
        {
            bool c = i == 0 || i == 10;
            int w = SpaceW(i, c);
            int sx = bx + size;
            for (int j = 0; j <= i; j++)
                sx -= SpaceW(j, j == 0 || j == 10);
            _spaces.Add((sx, by + size - corner, w, corner));
        }
        // Left column (11–19)
        for (int i = 1; i <= 9; i++)
        {
            int sy = bx + size; // same formula as Python
            sy = by + size;
            for (int j = 0; j <= i; j++)
                sy -= SpaceW(j, j == 0 || j == 10);
            _spaces.Add((bx, sy, corner, edge));
        }
        // Top row (20–30): left → right
        for (int i = 0; i <= 10; i++)
        {
            bool c = i == 0 || i == 10;
            int w = SpaceW(i, c);
            int sx = bx;
            for (int j = 0; j < i; j++)
                sx += SpaceW(j, j == 0 || j == 10);
            _spaces.Add((sx, by, w, corner));
        }
        // Right column (31–39)
        for (int i = 1; i <= 9; i++)
        {
            int sy = by;
            for (int j = 0; j < i; j++)
                sy += SpaceW(j, j == 0 || j == 10);
            _spaces.Add((bx + size - corner, sy, corner, edge));
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  Start / Reset
    // ═══════════════════════════════════════════════════════════════════════
    public override void StartGame(List<int> players)
    {
        // Reset properties
        foreach (var p in _properties) { p.Houses = 0; p.Owner = -1; p.IsMortgaged = false; }
        _housesRemaining = 32; _hotelsRemaining = 12; _freeParkingPot = 0;

        _communityDeck = new List<CardData>(MonopolyData.GetCommunityChestCards());
        _chanceDeck = new List<CardData>(MonopolyData.GetChanceCards());
        MonopolyLogic.Shuffle(_communityDeck, Rng);
        MonopolyLogic.Shuffle(_chanceDeck, Rng);

        _auctionActive = false; _tradeMode = null;
        _popup.Hide();
        _pendingLandIdx = null; _pendingPostCardLandIdx = null;
        _tokenAnims.Clear();
        _diceValues = (0, 0); _diceRolling = false;
        _debtActive = false;

        ActivePlayers = new List<int>(players);
        ActivePlayers.Sort();

        for (int i = 0; i < 8; i++)
        {
            var pl = _players[i];
            pl.Money = ActivePlayers.Contains(i) ? MonopolyData.StartingMoney : 0;
            pl.Position = 0;
            pl.Properties.Clear();
            pl.InJail = false; pl.JailTurns = 0;
            pl.IsBankrupt = false;
            pl.ConsecutiveDoubles = 0;
            pl.GetOutOfJailCards = 0;
        }

        var allPanels = PanelHelpers.CalculateAllPanels(ScreenW, ScreenH);
        _panels.Clear();
        foreach (int idx in ActivePlayers)
            _panels[idx] = allPanels[idx];

        InitButtons();
        _currentPlayerIdx = 0;
        _phase = "roll"; _canRoll = true;
        State = "playing";
    }

    // ─── Helpers ───────────────────────────────────────────────────────
    private MonopolyPlayer CurrentPlayer => _players[ActivePlayers[_currentPlayerIdx]];
    private int CurrentSeat => ActivePlayers.Count > 0 ? ActivePlayers[_currentPlayerIdx % ActivePlayers.Count] : -1;

    private string SeatLabel(int seat)
    {
        if (seat < 0 || seat > 7) return "—";
        return PlayerName(seat);
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  Buttons
    // ═══════════════════════════════════════════════════════════════════════
    private void InitButtons()
    {
        _buttons.Clear();
        foreach (int idx in ActivePlayers)
            RestoreDefaultButtons(idx);
    }

    private void RestoreDefaultButtons(int playerIdx)
    {
        if (!_panels.TryGetValue(playerIdx, out var panel)) return;
        var rects = panel.GetButtonLayout();
        int orient = panel.Orientation;
        var player = _players[playerIdx];

        var btns = new Dictionary<string, GameButton>();
        if (player.InJail)
        {
            bool canPay = player.Money >= 50;
            bool hasCard = player.GetOutOfJailCards > 0;
            btns["action"] = new GameButton(rects[0].X, rects[0].Y, rects[0].W, rects[0].H, "Roll", orient);
            btns["props"]  = new GameButton(rects[1].X, rects[1].Y, rects[1].W, rects[1].H, canPay ? "Pay $50" : "No $", orient) { Enabled = canPay };
            btns["build"]  = new GameButton(rects[2].X, rects[2].Y, rects[2].W, rects[2].H, hasCard ? "Use Card" : "", orient) { Enabled = hasCard };
        }
        else
        {
            string actionText = _canRoll ? "Roll" : "End Turn";
            btns["action"] = new GameButton(rects[0].X, rects[0].Y, rects[0].W, rects[0].H, actionText, orient);
            btns["props"]  = new GameButton(rects[1].X, rects[1].Y, rects[1].W, rects[1].H, "Deeds", orient);
            btns["build"]  = new GameButton(rects[2].X, rects[2].Y, rects[2].W, rects[2].H, "Trade", orient);
        }
        _buttons[playerIdx] = btns;
    }

    private void SetPopupButtons(int playerIdx, string[] texts, bool[] enabled)
    {
        if (!_panels.TryGetValue(playerIdx, out var panel)) return;
        var rects = panel.GetButtonLayout();
        int orient = panel.Orientation;
        var btns = new Dictionary<string, GameButton>();
        for (int i = 0; i < Math.Min(texts.Length, rects.Count); i++)
        {
            if (!string.IsNullOrEmpty(texts[i]))
            {
                var btn = new GameButton(rects[i].X, rects[i].Y, rects[i].W, rects[i].H, texts[i], orient)
                    { Enabled = enabled[i] };
                btns[$"popup_{i}"] = btn;
            }
        }
        _buttons[playerIdx] = btns;
    }

    private void SyncActionButtonText()
    {
        foreach (int idx in ActivePlayers)
        {
            if (!_buttons.TryGetValue(idx, out var btns) || !btns.TryGetValue("action", out var btn)) continue;
            btn.Text = _players[idx].InJail ? "Roll" : (_canRoll ? "Roll" : "End Turn");
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  Update
    // ═══════════════════════════════════════════════════════════════════════
    public override void Update(double dt)
    {
        _clock += dt;
        float fdt = (float)dt;

        // Tick animations
        _particles.Update(fdt);
        foreach (var a in _cardFlips) a.Update(fdt);
        _cardFlips.RemoveAll(a => a.Done);
        foreach (var a in _textPops) a.Update(fdt);
        _textPops.RemoveAll(a => a.Done);
        foreach (var a in _pulseRings) a.Update(fdt);
        _pulseRings.RemoveAll(a => a.Done);
        foreach (var a in _flashes) a.Update(fdt);
        _flashes.RemoveAll(a => a.Done);
        _ambient.Update(fdt, ScreenW, ScreenH);
        _lightBeams.Update(fdt, ScreenW, ScreenH);
        _vignette.Update(fdt);
        _starfield.Update(fdt);
        _floatingIcons.Update(fdt, ScreenW, ScreenH);
        _waveBand.Update(fdt);
        _heatShimmer.Update(fdt);

        // Winner fireworks
        bool isWin = State == "winner";
        if (isWin && !_animPrevGameOver)
        {
            _animPrevGameOver = true;
            int cx = ScreenW / 2, cy = ScreenH / 2;
            for (int i = 0; i < 10; i++)
                _particles.EmitFirework(cx + Rng.Next(-150, 150), cy + Rng.Next(-100, 100), AnimPalette.Rainbow);
            _flashes.Add(new ScreenFlash((255, 220, 80), 80, 1.2f));
            if (_winnerIdx is int wi)
                _textPops.Add(new TextPopAnim($"🏆 {SeatLabel(wi)} wins!", cx, cy - 70, (255, 220, 80), 40));
            _animFwTimer = 8f;
        }
        if (!isWin) _animPrevGameOver = false;
        if (_animFwTimer > 0)
        {
            _animFwTimer = MathF.Max(0, _animFwTimer - fdt);
            if ((int)(_animFwTimer * 3) % 2 == 0)
            {
                int cx = ScreenW / 2, cy = ScreenH / 2;
                _particles.EmitFirework(cx + Rng.Next(-150, 150), cy + Rng.Next(-100, 100), AnimPalette.Rainbow);
            }
        }

        // Auto-close card popup
        if (_popup.Active && _popup.PopupType == "card" && _cardPopupAutoCloseAt.HasValue && _clock >= _cardPopupAutoCloseAt.Value)
        {
            int? pidx = _popup.PlayerIdx;
            _cardPopupAutoCloseAt = null;
            _popup.Hide();
            if (pidx.HasValue) RestoreDefaultButtons(pidx.Value);
            if (_pendingPostCardLandIdx is int pcIdx)
            {
                _pendingPostCardLandIdx = null;
                LandOnSpace(_players[pcIdx]);
            }
            else FinishTurnOrAllowDouble();
        }

        // Resolve pending landing after token animation
        if (_pendingLandIdx is int pli && !_diceRolling)
        {
            if (_tokenAnims.TryGetValue(pli, out var anim))
            {
                double totalDur = anim.Path.Count * anim.SegmentDuration;
                if (_clock - anim.StartTime >= totalDur)
                    _tokenAnims.Remove(pli);
            }
            if (!_tokenAnims.ContainsKey(pli) && !_popup.Active)
            {
                _pendingLandIdx = null;
                LandOnSpace(_players[pli]);
            }
        }

        // Dice roll resolve
        if (_diceRolling)
        {
            double elapsed = _clock - _diceRollStart;
            if (elapsed >= 1.2)
            {
                _diceRolling = false;
                _diceValues = (Rng.Next(1, 7), Rng.Next(1, 7));
                int d1 = _diceValues.D1, d2 = _diceValues.D2;

                var current = CurrentPlayer;
                bool isDoubles = d1 == d2;

                if (current.InJail)
                {
                    HandleJailRoll(current, isDoubles);
                    return;
                }

                // Normal roll
                if (isDoubles)
                {
                    current.ConsecutiveDoubles++;
                    if (current.ConsecutiveDoubles >= 3)
                    {
                        current.Position = MonopolyData.JailPosition;
                        current.InJail = true; current.JailTurns = 0; current.ConsecutiveDoubles = 0;
                        var (sx, sy, sw, sh) = _spaces[MonopolyData.JailPosition];
                        _textPops.Add(new TextPopAnim("🔒 3× DOUBLES!", sx + sw / 2, sy + sh / 2 - 30, (255, 80, 80), 24));
                        _flashes.Add(new ScreenFlash((200, 60, 60), 40, 0.4f));
                        AdvanceTurn();
                        return;
                    }
                }
                else current.ConsecutiveDoubles = 0;

                int spaces = d1 + d2;
                int oldPos = current.Position;
                int newPos = (current.Position + spaces) % 40;
                StartTokenAnimation(current.Idx, oldPos, newPos);
                current.Position = newPos;
                if (newPos < oldPos) { current.AddMoney(MonopolyData.PassingGoMoney); PushToast($"{SeatLabel(current.Idx)} received ${MonopolyData.PassingGoMoney} (Go)"); }
                _pendingLandIdx = current.Idx;
                SyncActionButtonText();
            }
        }
    }

    private void HandleJailRoll(MonopolyPlayer current, bool isDoubles)
    {
        int d1 = _diceValues.D1, d2 = _diceValues.D2;
        if (isDoubles)
        {
            current.InJail = false; current.JailTurns = 0; current.ConsecutiveDoubles = 0;
            RestoreDefaultButtons(current.Idx);
            var (sx, sy, sw, sh) = _spaces[MonopolyData.JailPosition];
            _textPops.Add(new TextPopAnim("🔓 FREE!", sx + sw / 2, sy + sh / 2 - 30, (80, 220, 120), 24));
            _pulseRings.Add(new PulseRing(sx + sw / 2, sy + sh / 2, (80, 220, 120), 55, 0.5f));

            int spaces = d1 + d2;
            int oldPos = current.Position;
            int newPos = (oldPos + spaces) % 40;
            StartTokenAnimation(current.Idx, oldPos, newPos);
            current.Position = newPos;
            if (newPos < oldPos) current.AddMoney(MonopolyData.PassingGoMoney);
            _pendingLandIdx = current.Idx;
        }
        else
        {
            current.JailTurns++;
            if (current.JailTurns >= 3)
            {
                if (current.Money >= 50)
                {
                    current.RemoveMoney(50);
                    current.InJail = false; current.JailTurns = 0;
                    RestoreDefaultButtons(current.Idx);
                    int spaces = d1 + d2;
                    int oldPos = current.Position;
                    int newPos = (oldPos + spaces) % 40;
                    StartTokenAnimation(current.Idx, oldPos, newPos);
                    current.Position = newPos;
                    if (newPos < oldPos) current.AddMoney(MonopolyData.PassingGoMoney);
                    _pendingLandIdx = current.Idx;
                }
                else
                {
                    StartDebt(current, 50, null, true, "jail_release_move", new() { ["spaces"] = d1 + d2 });
                }
            }
            else AdvanceTurn();
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  Turn management
    // ═══════════════════════════════════════════════════════════════════════
    private void RollDice()
    {
        if (!_canRoll || _diceRolling) return;
        _diceValues = (0, 0);
        _diceRolling = true;
        _diceRollStart = _clock;
        _canRoll = false;

        // Fly-in origin
        var (bx, by, bw, bh) = _boardRect;
        int cxB = bx + bw / 2, cyB = by + bh / 2;
        int pidx = CurrentSeat;
        string side = _panels.TryGetValue(pidx, out var panel) ? panel.Side : "bottom";
        _diceFlyFrom = side switch
        {
            "top" => (cxB, by - 60),
            "left" => (bx - 60, cyB),
            "right" => (bx + bw + 60, cyB),
            _ => (cxB, by + bh + 60),
        };
        _diceFlyStart = _clock;
        SyncActionButtonText();
    }

    private void AdvanceTurn()
    {
        CurrentPlayer.ConsecutiveDoubles = 0;
        _currentPlayerIdx = (_currentPlayerIdx + 1) % ActivePlayers.Count;
        _phase = "roll"; _canRoll = true;
        SyncActionButtonText();
    }

    private void FinishTurnOrAllowDouble()
    {
        if (CurrentPlayer.ConsecutiveDoubles > 0) { _phase = "roll"; _canRoll = true; }
        else AdvanceTurn();
        SyncActionButtonText();
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  Token animation
    // ═══════════════════════════════════════════════════════════════════════
    private void StartTokenAnimation(int playerIdx, int from, int to)
    {
        var path = new List<int>();
        int cur = from;
        while (cur != to) { cur = (cur + 1) % 40; path.Add(cur); }
        _tokenAnims[playerIdx] = new TokenAnim { Path = path, StartPos = from, StartTime = _clock };
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  Landing
    // ═══════════════════════════════════════════════════════════════════════
    private void LandOnSpace(MonopolyPlayer player)
    {
        if (MonopolyLogic.CheckPassedGo(player))
        {
            player.AddMoney(MonopolyData.PassingGoMoney);
            PushToast($"{SeatLabel(player.Idx)} received ${MonopolyData.PassingGoMoney} (Go)");
        }

        int pos = player.Position;
        var space = _properties[pos];
        string type = space.Data.Type;

        switch (type)
        {
            case "go":
                player.AddMoney(MonopolyData.PassingGoMoney);
                PushToast($"{SeatLabel(player.Idx)} received ${MonopolyData.PassingGoMoney} (Go)");
                FinishTurnOrAllowDouble();
                break;

            case "property":
            case "railroad":
            case "utility":
                if (space.Owner < 0)
                {
                    _phase = "buying";
                    ShowBuyPrompt(player, pos);
                }
                else if (space.Owner != player.Idx)
                {
                    _phase = "paying_rent";
                    PayRent(player, pos);
                }
                else
                {
                    if (type == "property" && HasMonopoly(player.Idx, pos))
                    {
                        _phase = "building";
                        ShowBuildPrompt(player, pos);
                    }
                    else
                    {
                        if (player.ConsecutiveDoubles > 0) { _phase = "roll"; _canRoll = true; }
                        else { _phase = "action"; _canRoll = false; }
                    }
                }
                break;

            case "go_to_jail":
                SendToJail(player);
                break;

            case "chance":
            {
                var card = MonopolyLogic.DrawCard("chance", _chanceDeck, _communityDeck, Rng);
                ExecuteCardAction(player, card);
                ShowCardPopup(player, card, "chance");
                break;
            }
            case "community_chest":
            {
                var card = MonopolyLogic.DrawCard("community_chest", _chanceDeck, _communityDeck, Rng);
                ExecuteCardAction(player, card);
                ShowCardPopup(player, card, "community_chest");
                break;
            }
            case "income_tax":
                HandleTax(player, pos, MonopolyData.IncomeTax);
                break;
            case "luxury_tax":
                HandleTax(player, pos, MonopolyData.LuxuryTax);
                break;
            case "free_parking":
                if (_freeParkingPot > 0)
                {
                    int pot = _freeParkingPot;
                    player.AddMoney(pot);
                    _freeParkingPot = 0;
                    PushToast($"{SeatLabel(player.Idx)} received ${pot} (Free Parking)");
                    var (sx, sy, sw, sh) = _spaces[pos];
                    _textPops.Add(new TextPopAnim($"🎉 FREE PARKING ${pot}!", sx + sw / 2, sy + sh / 2 - 30, (255, 200, 50), 24));
                    _particles.EmitFirework(sx + sw / 2, sy + sh / 2, AnimPalette.Rainbow);
                }
                FinishTurnOrAllowDouble();
                break;
            default:
                FinishTurnOrAllowDouble();
                break;
        }

        SyncActionButtonText();
        if (player.Money < 0) HandleBankruptcy(player);
    }

    private void HandleTax(MonopolyPlayer player, int pos, int taxAmount)
    {
        if (player.Money >= taxAmount && player.RemoveMoney(taxAmount))
        {
            _freeParkingPot += taxAmount;
            PushToast($"{SeatLabel(player.Idx)} paid ${taxAmount} (Tax)");
            var (sx, sy, sw, sh) = _spaces[pos];
            _textPops.Add(new TextPopAnim($"💸 Tax -${taxAmount}", sx + sw / 2, sy + sh / 2 - 30, (255, 80, 80), 22));
            _flashes.Add(new ScreenFlash((180, 50, 50), 30, 0.3f));
            FinishTurnOrAllowDouble();
        }
        else
        {
            StartDebt(player, taxAmount, null, true, "finish_turn");
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  Property buying
    // ═══════════════════════════════════════════════════════════════════════
    private void BuyProperty(MonopolyPlayer player, int position)
    {
        var space = _properties[position];
        int price = space.Data.Price;
        if (player.RemoveMoney(price))
        {
            space.Owner = player.Idx;
            player.Properties.Add(position);
            PushToast($"{SeatLabel(player.Idx)} bought {space.Data.Name} for ${price}");
            var (sx, sy, sw, sh) = _spaces[position];
            _pulseRings.Add(new PulseRing(sx + sw / 2, sy + sh / 2, GameConfig.PlayerColors[player.Idx], 70, 0.8f));
            _textPops.Add(new TextPopAnim($"🏠 {space.Data.Name}!", sx + sw / 2, sy + sh / 2 - 25, GameConfig.PlayerColors[player.Idx], 20));
        }
        _popup.Hide();
        if (player.ConsecutiveDoubles > 0) { _phase = "roll"; _canRoll = true; }
        else { _phase = "action"; _canRoll = false; }
        RestoreDefaultButtons(player.Idx);
        SyncActionButtonText();
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  Rent
    // ═══════════════════════════════════════════════════════════════════════
    private void PayRent(MonopolyPlayer player, int position)
    {
        var space = _properties[position];
        var owner = _players[space.Owner];
        int? diceSum = space.Data.Type == "utility" ? _diceValues.D1 + _diceValues.D2 : null;
        int rent = MonopolyLogic.CalculateRent(space, diceSum, owner, _properties);

        if (player.Money >= rent && player.RemoveMoney(rent))
        {
            owner.AddMoney(rent);
            PushToast($"{SeatLabel(player.Idx)} paid ${rent} to {SeatLabel(owner.Idx)}");
            var (sx, sy, sw, sh) = _spaces[position];
            _textPops.Add(new TextPopAnim($"➖ ${rent}", sx + sw / 2, sy + sh / 2 - 30, (255, 80, 80), 22));
            _textPops.Add(new TextPopAnim($"➕ ${rent}", sx + sw / 2, sy + sh / 2 + 20, GameConfig.PlayerColors[owner.Idx], 18));
            FinishTurnOrAllowDouble();
        }
        else
        {
            StartDebt(player, rent, owner, false, "finish_turn");
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  Jail
    // ═══════════════════════════════════════════════════════════════════════
    private void SendToJail(MonopolyPlayer player)
    {
        MonopolyLogic.SendToJail(player);
        var (sx, sy, sw, sh) = _spaces[player.Position];
        _textPops.Add(new TextPopAnim("🔒 TO JAIL!", sx + sw / 2, sy + sh / 2 - 30, (255, 80, 80), 26));
        _flashes.Add(new ScreenFlash((200, 60, 60), 45, 0.45f));
        RestoreDefaultButtons(player.Idx);
        AdvanceTurn();
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  Monopoly / building checks
    // ═══════════════════════════════════════════════════════════════════════
    private bool HasMonopoly(int playerIdx, int position)
    {
        var prop = _properties[position];
        string? group = prop.Data.Group;
        if (string.IsNullOrEmpty(group) || !MonopolyData.PropertyGroups.ContainsKey(group)) return false;
        return MonopolyData.PropertyGroups[group].All(p => _players[playerIdx].Properties.Contains(p));
    }

    private bool CanBuildOnProperty(int playerIdx, int position)
    {
        var prop = _properties[position];
        string? group = prop.Data.Group;
        if (string.IsNullOrEmpty(group) || !MonopolyData.PropertyGroups.ContainsKey(group)) return false;
        var gp = MonopolyData.PropertyGroups[group];
        if (gp.Any(p => _properties[p].IsMortgaged)) return false;
        int curH = prop.Houses;
        return gp.All(p => p == position || _properties[p].Houses >= curH);
    }

    private bool GroupHasBuildings(int position)
    {
        var prop = _properties[position];
        string? group = prop.Data.Group;
        if (string.IsNullOrEmpty(group) || !MonopolyData.PropertyGroups.ContainsKey(group)) return false;
        return MonopolyData.PropertyGroups[group].Any(p => _properties[p].Houses > 0);
    }

    private bool CanSellOnProperty(int playerIdx, int position)
    {
        if (position < 0 || position >= _properties.Count) return false;
        var prop = _properties[position];
        if (prop.Owner != playerIdx || prop.IsMortgaged || prop.Houses <= 0) return false;
        string? group = prop.Data.Group;
        if (string.IsNullOrEmpty(group) || !MonopolyData.PropertyGroups.ContainsKey(group)) return true;
        int maxH = MonopolyData.PropertyGroups[group].Max(p => _properties[p].Houses);
        return prop.Houses >= maxH;
    }

    private bool SellHouse(MonopolyPlayer player, int position)
    {
        if (!CanSellOnProperty(player.Idx, position)) return false;
        var prop = _properties[position];
        int houseCost = prop.Data.HouseCost;
        int sellPrice = houseCost / 2;
        if (prop.Houses == 5) { prop.Houses = 4; _hotelsRemaining++; if (_housesRemaining >= 4) _housesRemaining -= 4; else { prop.Houses = 0; player.AddMoney(sellPrice); return true; } }
        else if (prop.Houses > 0) { prop.Houses--; _housesRemaining++; }
        player.AddMoney(sellPrice);
        return true;
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  Debt system
    // ═══════════════════════════════════════════════════════════════════════
    private void StartDebt(MonopolyPlayer player, int amount, MonopolyPlayer? owedTo, bool toFP, string after, Dictionary<string, object>? data = null)
    {
        if (amount <= 0) return;
        _debtActive = true; _debtPlayerIdx = player.Idx; _debtAmount = amount;
        _debtOwedTo = owedTo?.Idx; _debtToFreeParking = toFP;
        _debtAfter = after; _debtAfterData = data ?? new();

        if (!PlayerCanRaiseFunds(player)) { HandleBankruptcy(player, owedTo); return; }
        ShowPropertiesPopup(player);
    }

    private bool PlayerCanRaiseFunds(MonopolyPlayer player)
    {
        foreach (int pi in player.Properties)
        {
            var prop = _properties[pi];
            if (prop.Houses > 0) return true;
            if (!prop.IsMortgaged && prop.Houses == 0 && !GroupHasBuildings(pi) && prop.Data.MortgageValue > 0) return true;
        }
        return false;
    }

    private bool PayDebtIfPossible()
    {
        if (!_debtActive || _debtPlayerIdx is not int pidx) return false;
        var player = _players[pidx];
        if (player.Money < _debtAmount) return false;
        player.RemoveMoney(_debtAmount);

        if (_debtOwedTo is int oi && oi >= 0 && oi < _players.Count)
            _players[oi].AddMoney(_debtAmount);
        else if (_debtToFreeParking)
            _freeParkingPot += _debtAmount;

        string after = _debtAfter;
        var afterData = _debtAfterData;
        _debtActive = false; _debtPlayerIdx = null; _debtAmount = 0;

        if (after == "jail_release_move")
        {
            player.InJail = false; player.JailTurns = 0;
            int spaces = afterData.TryGetValue("spaces", out var sv) ? Convert.ToInt32(sv) : 0;
            if (spaces > 0)
            {
                int old = player.Position;
                int np = (old + spaces) % 40;
                StartTokenAnimation(player.Idx, old, np);
                player.Position = np;
                if (np < old) player.AddMoney(MonopolyData.PassingGoMoney);
                _pendingLandIdx = player.Idx;
            }
            else FinishTurnOrAllowDouble();
            return true;
        }
        FinishTurnOrAllowDouble();
        return true;
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  Bankruptcy
    // ═══════════════════════════════════════════════════════════════════════
    private void HandleBankruptcy(MonopolyPlayer player, MonopolyPlayer? owedTo = null)
    {
        player.IsBankrupt = true;
        int active = ActivePlayers.Count(i => !_players[i].IsBankrupt);
        if (active == 1)
        {
            int winner = ActivePlayers.First(i => !_players[i].IsBankrupt);
            _winnerIdx = winner;
            State = "winner";
            return;
        }
        // Return properties
        foreach (int pi in player.Properties.ToList())
        {
            var prop = _properties[pi];
            if (prop.Houses >= 5) { _hotelsRemaining++; _housesRemaining += 4; }
            else if (prop.Houses > 0) _housesRemaining += prop.Houses;
            prop.Houses = 0;
            if (owedTo != null) { prop.Owner = owedTo.Idx; owedTo.Properties.Add(pi); }
            else { prop.Owner = -1; prop.IsMortgaged = false; }
        }
        player.Properties.Clear();
        if (ActivePlayers.Contains(player.Idx))
        {
            int pos = ActivePlayers.IndexOf(player.Idx);
            ActivePlayers.Remove(player.Idx);
            if (_currentPlayerIdx >= ActivePlayers.Count) _currentPlayerIdx = 0;
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  Card execution
    // ═══════════════════════════════════════════════════════════════════════
    private void ExecuteCardAction(MonopolyPlayer player, CardData card)
    {
        var a = card.Action;
        if (a == null) return;

        switch (a.Type)
        {
            case "money":
                if (a.Amount > 0) { player.AddMoney(a.Amount); PushToast($"{SeatLabel(player.Idx)} received ${a.Amount} (Card)"); }
                else { player.RemoveMoney(-a.Amount); _freeParkingPot += -a.Amount; PushToast($"{SeatLabel(player.Idx)} paid ${-a.Amount} (Card)"); }
                break;
            case "advance":
                { int old = player.Position;
                  if (a.PassGo && a.Target < old) { player.AddMoney(MonopolyData.PassingGoMoney); PushToast($"{SeatLabel(player.Idx)} received ${MonopolyData.PassingGoMoney} (Go)"); }
                  StartTokenAnimation(player.Idx, old, a.Target);
                  player.Position = a.Target;
                  _pendingPostCardLandIdx = player.Idx;
                } break;
            case "advance_relative":
                { int old = player.Position; int np = (old + a.Amount) % 40; if (np < 0) np += 40;
                  StartTokenAnimation(player.Idx, old, np); player.Position = np;
                  _pendingPostCardLandIdx = player.Idx;
                } break;
            case "go_to_jail": SendToJail(player); break;
            case "jail_free": player.GetOutOfJailCards++; break;
            case "advance_nearest":
                {
                    int cur = player.Position;
                    int nearest;
                    if (a.Nearest == "railroad")
                    {
                        int[] rr = { 5, 15, 25, 35 };
                        nearest = rr.OrderBy(r => ((r - cur) % 40 + 40) % 40).First();
                    }
                    else
                    {
                        int[] ut = { 12, 28 };
                        nearest = ut.OrderBy(u => ((u - cur) % 40 + 40) % 40).First();
                    }
                    int old = player.Position;
                    if (nearest < old) { player.AddMoney(MonopolyData.PassingGoMoney); PushToast($"{SeatLabel(player.Idx)} received ${MonopolyData.PassingGoMoney} (Go)"); }
                    StartTokenAnimation(player.Idx, old, nearest); player.Position = nearest;
                    _pendingPostCardLandIdx = player.Idx;
                } break;
            case "collect_from_each":
                { int total = 0;
                  foreach (int oi in ActivePlayers.Where(i => i != player.Idx))
                  { int t = Math.Min(a.Amount, _players[oi].Money); _players[oi].RemoveMoney(t); player.AddMoney(t); total += t; }
                  if (total > 0) PushToast($"{SeatLabel(player.Idx)} received ${total} (from players)");
                } break;
            case "pay_each_player":
                { int total = 0;
                  foreach (int oi in ActivePlayers.Where(i => i != player.Idx))
                  { int pay = Math.Min(a.Amount, player.Money); player.RemoveMoney(pay); _players[oi].AddMoney(pay); total += pay; }
                  if (total > 0) PushToast($"{SeatLabel(player.Idx)} paid ${total} (to players)");
                } break;
            case "pay_per_house_hotel":
                { int tc = 0;
                  foreach (int pi in player.Properties)
                  { var prop = _properties[pi]; if (prop.Houses == 5) tc += a.RepairHotel; else if (prop.Houses > 0) tc += prop.Houses * a.RepairHouse; }
                  player.RemoveMoney(tc); _freeParkingPot += tc;
                  if (tc > 0) PushToast($"{SeatLabel(player.Idx)} paid ${tc} (Repairs)");
                } break;
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  Popup helpers
    // ═══════════════════════════════════════════════════════════════════════
    private void ShowBuyPrompt(MonopolyPlayer player, int pos)
    {
        if (!_panels.TryGetValue(player.Idx, out var panel)) return;
        var space = _properties[pos];
        int price = space.Data.Price;

        var lines = new List<(string, int, (int, int, int))>
        {
            ("BUY PROPERTY?", 14, (255, 255, 255)),
            (space.Data.Name, 12, (255, 255, 255)),
            ($"Price: ${price}", 10, (255, 255, 100)),
            ($"Your money: ${player.Money}", 9, (100, 255, 100)),
        };

        _popup.Show(player.Idx, panel.Rect, panel.Orientation, "buy_prompt", lines, new() { ["position"] = pos });
        bool canAfford = player.Money >= price;
        SetPopupButtons(player.Idx, new[] { canAfford ? "Buy" : "Can't Buy", "Pass", "" }, new[] { canAfford, true, false });
    }

    private void ShowBuildPrompt(MonopolyPlayer player, int pos)
    {
        if (!_panels.TryGetValue(player.Idx, out var panel)) return;
        var space = _properties[pos];
        int hc = space.Data.HouseCost;
        int houses = space.Houses;
        string status = houses == 5 ? "Hotel built!" : houses > 0 ? $"{houses} Houses" : "No houses";
        var lines = new List<(string, int, (int, int, int))>
        {
            (space.Data.Name, 14, (255, 255, 255)),
            (status, 10, houses == 5 ? (255, 215, 0) : (200, 200, 200)),
            ($"Cost: ${hc}", 9, (255, 255, 100)),
            ($"Bank: {_housesRemaining}H {_hotelsRemaining}Ho", 8, (180, 180, 180)),
        };
        _popup.Show(player.Idx, panel.Rect, panel.Orientation, "build_prompt", lines, new() { ["position"] = pos });
        bool canBuild = houses < 5 && player.Money >= hc && !space.IsMortgaged;
        if (houses == 4) canBuild = canBuild && _hotelsRemaining > 0;
        else canBuild = canBuild && _housesRemaining > 0;
        bool canSell = houses > 0 && CanSellOnProperty(player.Idx, pos);
        SetPopupButtons(player.Idx, new[] { "Pass", canBuild ? "Buy" : "No $", canSell ? "Sell" : "" }, new[] { true, canBuild, canSell });
    }

    private void ShowCardPopup(MonopolyPlayer player, CardData card, string deckType)
    {
        if (!_panels.TryGetValue(player.Idx, out var panel)) return;
        string title = deckType == "chance" ? "❓ Chance" : "🎁 Community Chest";
        var lines = new List<(string, int, (int, int, int))>
        {
            (title, 14, deckType == "chance" ? (255, 200, 50) : (50, 200, 255)),
            (card.Text, 10, (255, 255, 255)),
        };
        _cardBannerDeck = deckType; _cardBannerText = card.Text; _cardBannerTs = _clock;
        _cardPopupAutoCloseAt = _clock + 3.5;
        _popup.Show(player.Idx, panel.Rect, panel.Orientation, "card", lines, null);
        SetPopupButtons(player.Idx, new[] { "OK", "", "" }, new[] { true, false, false });
    }

    private void ShowPropertiesPopup(MonopolyPlayer player)
    {
        if (player.Properties.Count == 0) return;
        _mortgageScrollIndex = 0;
        ShowMortgageDetail(player);
    }

    private void ShowMortgageDetail(MonopolyPlayer player)
    {
        if (player.Properties.Count == 0) return;
        if (!_panels.TryGetValue(player.Idx, out var panel)) return;
        _mortgageScrollIndex = Math.Clamp(_mortgageScrollIndex, 0, player.Properties.Count - 1);
        int propIdx = player.Properties[_mortgageScrollIndex];
        var prop = _properties[propIdx];
        int mv = prop.Data.MortgageValue;
        int umc = (int)(mv * 1.1);

        var lines = new List<(string, int, (int, int, int))>
        {
            (prop.Data.Name, 14, (255, 255, 255)),
            ($"Property {_mortgageScrollIndex + 1}/{player.Properties.Count}", 10, (200, 200, 200)),
        };
        if (prop.IsMortgaged) { lines.Add(("MORTGAGED", 12, (255, 100, 100))); lines.Add(($"Unmortgage: ${umc}", 10, (255, 255, 100))); }
        else if (prop.Houses > 0) { lines.Add(($"Houses: {prop.Houses}", 10, (100, 255, 100))); lines.Add(("Sell houses", 9, (255, 200, 100))); }
        else lines.Add(($"Mortgage Value: ${mv}", 10, (100, 255, 100)));

        _popup.Show(player.Idx, panel.Rect, panel.Orientation, "mortgage", lines, new() { ["prop_idx"] = propIdx });

        bool canPrev = _mortgageScrollIndex > 0;
        bool canNext = _mortgageScrollIndex < player.Properties.Count - 1;
        string leftBtn = canPrev ? "◄" : "Close";
        string rightBtn = canNext ? "►" : "Done";

        if (prop.IsMortgaged)
        {
            bool canUm = player.Money >= umc;
            SetPopupButtons(player.Idx, new[] { leftBtn, canUm ? "Unmortgage" : "No $", rightBtn }, new[] { true, canUm, true });
        }
        else if (prop.Houses > 0)
        {
            bool canSell = CanSellOnProperty(player.Idx, propIdx);
            SetPopupButtons(player.Idx, new[] { leftBtn, canSell ? "Sell" : "Even Rule", rightBtn }, new[] { true, canSell, true });
        }
        else
        {
            bool gb = GroupHasBuildings(propIdx);
            SetPopupButtons(player.Idx, new[] { leftBtn, gb ? "Group Built" : "Mortgage", rightBtn }, new[] { true, !gb, true });
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  Auction
    // ═══════════════════════════════════════════════════════════════════════
    private void StartAuction(int propIdx)
    {
        _auctionActive = true; _auctionProperty = propIdx;
        _auctionBid = 0; _auctionBidder = null;
        _auctionActiveBidders = ActivePlayers.Where(i => !_players[i].IsBankrupt).ToList();
        if (_auctionActiveBidders.Count == 0) { EndAuction(); return; }
        int startIdx = ActivePlayers[(_currentPlayerIdx + 1) % ActivePlayers.Count];
        _auctionBidderIndex = _auctionActiveBidders.Contains(startIdx) ? _auctionActiveBidders.IndexOf(startIdx) : 0;
        ShowAuctionPopup();
    }

    private void ShowAuctionPopup()
    {
        if (_auctionActiveBidders.Count == 0) { EndAuction(); return; }
        if (_auctionBidder.HasValue && _auctionBid > 0 && _auctionActiveBidders.Count == 1 && _auctionActiveBidders.Contains(_auctionBidder.Value))
        { EndAuction(); return; }

        _auctionBidderIndex = Math.Clamp(_auctionBidderIndex, 0, _auctionActiveBidders.Count - 1);
        int bidIdx = _auctionActiveBidders[_auctionBidderIndex];
        var bidder = _players[bidIdx];
        if (bidder.IsBankrupt) { _auctionActiveBidders.Remove(bidIdx); _auctionBidderIndex %= Math.Max(1, _auctionActiveBidders.Count); ShowAuctionPopup(); return; }
        if (!_panels.TryGetValue(bidIdx, out var panel)) return;

        int minBid = _auctionBid + 10;
        var prop = _properties[_auctionProperty];
        var lines = new List<(string, int, (int, int, int))>
        {
            ($"AUCTION: {prop.Data.Name}", 14, (255, 255, 255)),
            (_auctionBid > 0 ? $"High bid: ${_auctionBid}" : "No bids yet", 10, (255, 215, 0)),
            ($"Min bid: ${minBid}", 10, (200, 200, 200)),
            ($"Your money: ${bidder.Money}", 9, (100, 255, 100)),
        };
        bool canBid = bidder.Money >= minBid;
        _popup.Show(bidIdx, panel.Rect, panel.Orientation, "auction", lines, new() { ["min_bid"] = minBid });
        SetPopupButtons(bidIdx, new[] { canBid ? "Bid" : "No $", "Pass", "" }, new[] { canBid, true, false });
    }

    private void EndAuction()
    {
        if (_auctionBidder is int winner)
        {
            var w = _players[winner];
            w.RemoveMoney(_auctionBid);
            _properties[_auctionProperty].Owner = winner;
            w.Properties.Add(_auctionProperty);
            PushToast($"{SeatLabel(winner)} bought {_properties[_auctionProperty].Data.Name} for ${_auctionBid}");
        }
        _auctionActive = false;
        FinishTurnOrAllowDouble();
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  Toast system
    // ═══════════════════════════════════════════════════════════════════════
    private void PushToast(string text, (int R, int G, int B)? color = null, double ttl = 3.0)
    {
        _toasts.Add(new ToastEntry { Text = text, Color = color ?? (255, 255, 255), Ts = _clock, Ttl = ttl });
        if (_toasts.Count > 5) _toasts.RemoveRange(0, _toasts.Count - 5);
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  Button handling (Web UI)
    // ═══════════════════════════════════════════════════════════════════════
    public override void HandleButton(int playerIdx, string action, string? value = null)
    {
        if (State != "playing") return;
        int currSeat = CurrentSeat;

        switch (action)
        {
            case "roll":
                if (playerIdx == currSeat && _canRoll) RollDice();
                break;
            case "end_turn":
                if (playerIdx == currSeat && !_canRoll && !_diceRolling && !_tokenAnims.ContainsKey(playerIdx) && _pendingLandIdx == null && !_popup.Active)
                    AdvanceTurn();
                break;
            case "deeds":
                if (_players[playerIdx].Properties.Count > 0)
                    ShowPropertiesPopup(_players[playerIdx]);
                break;
            case "pay_jail":
                if (playerIdx == currSeat && _players[playerIdx].InJail && _players[playerIdx].Money >= 50)
                {
                    _players[playerIdx].RemoveMoney(50);
                    _players[playerIdx].InJail = false; _players[playerIdx].JailTurns = 0;
                    _canRoll = true; _phase = "roll";
                    RestoreDefaultButtons(playerIdx);
                }
                break;
            case "use_card":
                if (playerIdx == currSeat && _players[playerIdx].InJail && _players[playerIdx].GetOutOfJailCards > 0)
                {
                    _players[playerIdx].GetOutOfJailCards--;
                    _players[playerIdx].InJail = false; _players[playerIdx].JailTurns = 0;
                    _canRoll = true; _phase = "roll";
                    RestoreDefaultButtons(playerIdx);
                }
                break;
            case "popup_0": case "popup_1": case "popup_2":
                HandlePopupButton(action);
                break;
        }
    }

    private void HandlePopupButton(string btnName)
    {
        string pt = _popup.PopupType ?? "";
        int? pidx = _popup.PlayerIdx;

        if (btnName == "popup_0")
        {
            switch (pt)
            {
                case "buy_prompt":
                    if (pidx.HasValue) BuyProperty(_players[pidx.Value], (int)_popup.Data!["position"]);
                    break;
                case "card":
                    _cardPopupAutoCloseAt = null;
                    if (pidx.HasValue) { _popup.Hide(); RestoreDefaultButtons(pidx.Value); }
                    if (_pendingPostCardLandIdx is int pcl) { _pendingPostCardLandIdx = null; LandOnSpace(_players[pcl]); }
                    else FinishTurnOrAllowDouble();
                    break;
                case "auction":
                    if (pidx.HasValue)
                    {
                        int minBid = _popup.Data != null && _popup.Data.TryGetValue("min_bid", out var mb) ? Convert.ToInt32(mb) : _auctionBid + 10;
                        if (_players[pidx.Value].Money >= minBid)
                        {
                            _auctionBid = minBid; _auctionBidder = pidx.Value;
                            _popup.Hide(); RestoreDefaultButtons(pidx.Value);
                            _auctionBidderIndex = (_auctionBidderIndex + 1) % Math.Max(1, _auctionActiveBidders.Count);
                            ShowAuctionPopup();
                        }
                    }
                    break;
                case "build_prompt":
                    if (pidx.HasValue) { _popup.Hide(); RestoreDefaultButtons(pidx.Value); FinishTurnOrAllowDouble(); }
                    break;
                case "properties": case "mortgage":
                    if (pidx.HasValue)
                    {
                        if (pt == "mortgage" && _mortgageScrollIndex > 0) { _mortgageScrollIndex--; ShowMortgageDetail(_players[pidx.Value]); }
                        else if (!_debtActive || _debtPlayerIdx != pidx) { _popup.Hide(); RestoreDefaultButtons(pidx.Value); }
                    }
                    break;
                case "trade_select":
                    if (pidx.HasValue)
                    {
                        var prev = FindPrevTradePartner();
                        if (prev.HasValue) { _tradeScrollIndex = prev.Value; ShowTradePartnerSelect(); }
                        else { _popup.Hide(); RestoreDefaultButtons(pidx.Value); _tradeMode = null; }
                    }
                    break;
                case "trade_web_edit":
                    if (pidx.HasValue) { _popup.Hide(); RestoreDefaultButtons(pidx.Value); _tradeMode = null; }
                    break;
                case "trade_web_response":
                    if (pidx.HasValue && _tradeInitiator.HasValue)
                    {
                        _popup.Hide(); RestoreDefaultButtons(pidx.Value); RestoreDefaultButtons(_tradeInitiator.Value); _tradeMode = null;
                    }
                    break;
                case "trade_build":
                    if (pidx.HasValue) { _popup.Hide(); RestoreDefaultButtons(pidx.Value); _tradeMode = null; }
                    break;
                case "trade_response": case "trade_detail":
                    if (pidx.HasValue && _tradeInitiator.HasValue)
                    {
                        _popup.Hide(); RestoreDefaultButtons(pidx.Value); RestoreDefaultButtons(_tradeInitiator.Value); _tradeMode = null;
                    }
                    break;
                case "info":
                    if (pidx.HasValue) { _popup.Hide(); RestoreDefaultButtons(pidx.Value); }
                    break;
            }
        }
        else if (btnName == "popup_1")
        {
            switch (pt)
            {
                case "buy_prompt":
                    if (pidx.HasValue) { int pos = (int)_popup.Data!["position"]; _popup.Hide(); RestoreDefaultButtons(pidx.Value); StartAuction(pos); }
                    break;
                case "auction":
                    if (pidx.HasValue)
                    {
                        if (_auctionActiveBidders.Contains(pidx.Value)) _auctionActiveBidders.Remove(pidx.Value);
                        _popup.Hide(); RestoreDefaultButtons(pidx.Value);
                        _auctionBidderIndex %= Math.Max(1, _auctionActiveBidders.Count);
                        ShowAuctionPopup();
                    }
                    break;
                case "build_prompt":
                    if (pidx.HasValue)
                    {
                        int pos = (int)_popup.Data!["position"];
                        var prop = _properties[pos];
                        int hc = prop.Data.HouseCost;
                        if (prop.Houses < 5 && _players[pidx.Value].Money >= hc && CanBuildOnProperty(pidx.Value, pos))
                        {
                            if (prop.Houses == 4 && _hotelsRemaining > 0)
                            { _players[pidx.Value].RemoveMoney(hc); prop.Houses = 5; _hotelsRemaining--; _housesRemaining += 4; }
                            else if (prop.Houses < 4 && _housesRemaining > 0)
                            { _players[pidx.Value].RemoveMoney(hc); prop.Houses++; _housesRemaining--; }
                            ShowBuildPrompt(_players[pidx.Value], pos);
                        }
                    }
                    break;
                case "mortgage":
                    if (pidx.HasValue)
                    {
                        var player = _players[pidx.Value];
                        int propIdx = (int)_popup.Data!["prop_idx"];
                        var prop = _properties[propIdx];
                        if (prop.IsMortgaged)
                        {
                            int umc = (int)(prop.Data.MortgageValue * 1.1);
                            if (player.Money >= umc) { player.RemoveMoney(umc); prop.IsMortgaged = false; ShowMortgageDetail(player); }
                        }
                        else if (prop.Houses > 0)
                        {
                            bool sold = SellHouse(player, propIdx);
                            if (sold) { if (!PayDebtIfPossible()) ShowMortgageDetail(player); }
                        }
                        else if (!GroupHasBuildings(propIdx))
                        {
                            player.AddMoney(prop.Data.MortgageValue); prop.IsMortgaged = true;
                            if (!PayDebtIfPossible()) ShowMortgageDetail(player);
                        }
                    }
                    break;
                case "trade_select":
                    if (pidx.HasValue && _popup.Data.TryGetValue("partner_idx", out var piObj))
                    {
                        int partnerIdx = Convert.ToInt32(piObj);
                        _tradePartner = partnerIdx;
                        _tradeMode = "build_offer";
                        ShowTradeWebEdit();
                    }
                    break;
                case "trade_web_edit":
                    if (pidx.HasValue && _tradeInitiator.HasValue)
                    {
                        _tradeMode = "await_response";
                        _popup.Hide(); RestoreDefaultButtons(_tradeInitiator.Value);
                        ShowTradeWebResponse();
                    }
                    break;
                case "trade_build":
                    if (pidx.HasValue) ShowTradeModify();
                    break;
                case "trade_response":
                    if (pidx.HasValue) ShowTradeDetailView();
                    break;
            }
        }
        else if (btnName == "popup_2")
        {
            switch (pt)
            {
                case "build_prompt":
                    if (pidx.HasValue)
                    {
                        int pos = (int)_popup.Data!["position"];
                        if (_properties[pos].Houses > 0 && SellHouse(_players[pidx.Value], pos))
                        { if (!PayDebtIfPossible()) ShowBuildPrompt(_players[pidx.Value], pos); }
                    }
                    break;
                case "mortgage":
                    if (pidx.HasValue)
                    {
                        var player = _players[pidx.Value];
                        if (_mortgageScrollIndex < player.Properties.Count - 1) { _mortgageScrollIndex++; ShowMortgageDetail(player); }
                        else if (!_debtActive || _debtPlayerIdx != pidx) { _popup.Hide(); RestoreDefaultButtons(pidx.Value); }
                    }
                    break;
                case "trade_select":
                    if (pidx.HasValue)
                    {
                        var next = FindNextTradePartner();
                        if (next.HasValue) { _tradeScrollIndex = next.Value; ShowTradePartnerSelect(); }
                    }
                    break;
                case "trade_web_response":
                    if (pidx.HasValue && _tradeInitiator.HasValue && _tradePartner.HasValue)
                    {
                        bool ok = ExecuteTrade();
                        if (ok)
                        {
                            _popup.Hide();
                            RestoreDefaultButtons(_tradeInitiator.Value);
                            RestoreDefaultButtons(_tradePartner.Value);
                            _tradeMode = null;
                        }
                        else
                        {
                            if (_panels.TryGetValue(pidx.Value, out var failPanel))
                            {
                                var failLines = new List<(string, int, (int, int, int))>
                                {
                                    ("Trade Failed", 14, (255, 100, 100)),
                                    ("Offer no longer valid", 10, (200, 200, 200)),
                                };
                                _popup.Show(pidx.Value, failPanel.Rect, failPanel.Orientation, "info", failLines);
                                SetPopupButtons(pidx.Value, new[] { "OK", "", "" }, new[] { true, false, false });
                            }
                            RestoreDefaultButtons(_tradeInitiator.Value);
                            _tradeMode = null;
                        }
                    }
                    break;
                case "trade_build":
                    if (pidx.HasValue && _tradeInitiator.HasValue)
                    {
                        _tradeMode = "await_response";
                        ShowTradeProposal();
                    }
                    break;
                case "trade_response": case "trade_detail":
                    if (pidx.HasValue && _tradeInitiator.HasValue && _tradePartner.HasValue)
                    {
                        bool ok2 = ExecuteTrade();
                        if (ok2)
                        {
                            _popup.Hide();
                            RestoreDefaultButtons(_tradeInitiator.Value);
                            RestoreDefaultButtons(_tradePartner.Value);
                            _tradeMode = null;
                        }
                        else
                        {
                            if (_panels.TryGetValue(pidx.Value, out var failPanel2))
                            {
                                var failLines2 = new List<(string, int, (int, int, int))>
                                {
                                    ("Trade Failed", 14, (255, 100, 100)),
                                    ("Offer no longer valid", 10, (200, 200, 200)),
                                };
                                _popup.Show(pidx.Value, failPanel2.Rect, failPanel2.Orientation, "info", failLines2);
                                SetPopupButtons(pidx.Value, new[] { "OK", "", "" }, new[] { true, false, false });
                            }
                            RestoreDefaultButtons(_tradeInitiator.Value);
                            _tradeMode = null;
                        }
                    }
                    break;
            }
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  Web UI state
    // ═══════════════════════════════════════════════════════════════════════
    public override List<WebUIButton> GetButtons()
    {
        var list = new List<WebUIButton>();
        if (State != "playing") return list;

        int curr = CurrentSeat;
        foreach (int idx in ActivePlayers)
        {
            var p = _players[idx];
            bool isCurr = idx == curr;
            bool locked = _diceRolling || _popup.Active || _tokenAnims.ContainsKey(idx) || _pendingLandIdx == idx;

            if (_popup.Active && _popup.PlayerIdx == idx)
            {
                // Popup buttons
                if (_buttons.TryGetValue(idx, out var pBtns))
                    foreach (var kv in pBtns)
                        list.Add(new WebUIButton { Label = kv.Value.Text, Action = kv.Key, PlayerIdx = idx, Enabled = kv.Value.Enabled });
            }
            else
            {
                if (p.InJail)
                {
                    list.Add(new WebUIButton { Label = "Roll", Action = "roll", PlayerIdx = idx, Enabled = isCurr && !locked });
                    list.Add(new WebUIButton { Label = p.Money >= 50 ? "Pay $50" : "No $", Action = "pay_jail", PlayerIdx = idx, Enabled = p.Money >= 50 });
                    list.Add(new WebUIButton { Label = p.GetOutOfJailCards > 0 ? "Use Card" : "", Action = "use_card", PlayerIdx = idx, Enabled = p.GetOutOfJailCards > 0 });
                }
                else
                {
                    list.Add(new WebUIButton { Label = _canRoll ? "Roll" : "End Turn", Action = _canRoll ? "roll" : "end_turn", PlayerIdx = idx, Enabled = isCurr && !locked });
                    list.Add(new WebUIButton { Label = "Deeds", Action = "deeds", PlayerIdx = idx, Enabled = p.Properties.Count > 0 });
                    list.Add(new WebUIButton { Label = "Trade", Action = "trade", PlayerIdx = idx, Enabled = isCurr && p.Properties.Count > 0 });
                }
            }
        }
        return list;
    }

    public override Dictionary<string, object?> GetWebUIState()
    {
        var state = base.GetWebUIState();
        state["phase"] = _phase;
        state["current_player"] = CurrentSeat;
        state["dice"] = new[] { _diceValues.D1, _diceValues.D2 };
        state["free_parking_pot"] = _freeParkingPot;
        return state;
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  HandleClick (web UI button ID routing)
    // ═══════════════════════════════════════════════════════════════════════
    public override void HandleClick(int playerIdx, string buttonId)
    {
        if (buttonId.StartsWith("__msg__:"))
        {
            var parts = buttonId.Split(':', 3);
            if (parts.Length >= 2)
                HandleMessage(playerIdx, parts[1], parts.Length > 2 ? parts[2] : "");
            return;
        }

        if (State != "playing") return;

        switch (buttonId)
        {
            case "action":
                HandleButton(playerIdx, _players[playerIdx].InJail ? "roll" : (_canRoll ? "roll" : "end_turn"));
                break;
            case "props":
                if (_players[playerIdx].InJail)
                    HandleButton(playerIdx, "pay_jail");
                else
                    HandleButton(playerIdx, "deeds");
                break;
            case "build":
                if (_players[playerIdx].InJail)
                    HandleButton(playerIdx, "use_card");
                else
                {
                    int currSeat = CurrentSeat;
                    if (playerIdx == currSeat && _players[playerIdx].Properties.Count > 0)
                        StartTrade(_players[playerIdx]);
                }
                break;
            case "popup_0": case "popup_1": case "popup_2":
                HandlePopupButton(buttonId);
                break;
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  HandleMessage (game-specific messages from web UI)
    // ═══════════════════════════════════════════════════════════════════════
    public override void HandleMessage(int playerIdx, string type, string json)
    {
        if (type == "trade_adjust_money")
        {
            if (!_popup.Active || _popup.PopupType != "trade_web_edit") return;
            if (!_tradeInitiator.HasValue || !_tradePartner.HasValue) return;
            if (playerIdx != _tradeInitiator.Value) return;

            try
            {
                using var doc = System.Text.Json.JsonDocument.Parse(json);
                var root = doc.RootElement;
                string side = root.GetProperty("side").GetString() ?? "";
                int delta = root.GetProperty("delta").GetInt32();

                if (side == "offer")
                {
                    int cur = _tradeOfferMoney;
                    int next = Math.Max(0, cur + delta);
                    next = Math.Min(next, Math.Max(0, _players[_tradeInitiator.Value].Money));
                    _tradeOfferMoney = next;
                }
                else if (side == "request")
                {
                    int cur = _tradeRequestMoney;
                    int next = Math.Max(0, cur + delta);
                    next = Math.Min(next, Math.Max(0, _players[_tradePartner.Value].Money));
                    _tradeRequestMoney = next;
                }
                ShowTradeWebEdit();
            }
            catch { }
        }
        else if (type == "trade_set_property")
        {
            if (!_popup.Active || _popup.PopupType != "trade_web_edit") return;
            if (!_tradeInitiator.HasValue || !_tradePartner.HasValue) return;
            if (playerIdx != _tradeInitiator.Value) return;

            try
            {
                using var doc = System.Text.Json.JsonDocument.Parse(json);
                var root = doc.RootElement;
                string side = root.GetProperty("side").GetString() ?? "";
                int propIdx = root.GetProperty("prop_idx").GetInt32();
                bool included = root.GetProperty("included").GetBoolean();

                if (propIdx < 0 || propIdx >= _properties.Count) return;
                var prop = _properties[propIdx];
                if (prop.IsMortgaged || prop.Houses > 0) return;

                var initiator = _players[_tradeInitiator.Value];
                var partner = _players[_tradePartner.Value];

                if (side == "offer")
                {
                    if (!initiator.Properties.Contains(propIdx)) return;
                    if (included && !_tradeOfferProps.Contains(propIdx)) _tradeOfferProps.Add(propIdx);
                    if (!included && _tradeOfferProps.Contains(propIdx)) _tradeOfferProps.Remove(propIdx);
                }
                else if (side == "request")
                {
                    if (!partner.Properties.Contains(propIdx)) return;
                    if (included && !_tradeRequestProps.Contains(propIdx)) _tradeRequestProps.Add(propIdx);
                    if (!included && _tradeRequestProps.Contains(propIdx)) _tradeRequestProps.Remove(propIdx);
                }
                ShowTradeWebEdit();
            }
            catch { }
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  GetSnapshot (per-player game state for web UI)
    // ═══════════════════════════════════════════════════════════════════════
    public override Dictionary<string, object?> GetSnapshot(int playerIdx)
    {
        var players = new List<Dictionary<string, object?>>();
        foreach (int pidx in ActivePlayers)
        {
            var p = _players[pidx];
            var props = new List<Dictionary<string, object?>>();
            foreach (int pi in p.Properties)
            {
                if (pi < 0 || pi >= _properties.Count) continue;
                var prop = _properties[pi];
                props.Add(new Dictionary<string, object?>
                {
                    ["idx"] = pi,
                    ["name"] = prop.Data.Name,
                });
            }
            players.Add(new Dictionary<string, object?>
            {
                ["player_idx"] = pidx,
                ["name"] = PlayerName(pidx),
                ["money"] = p.Money,
                ["jail_free_cards"] = p.GetOutOfJailCards,
                ["properties"] = props,
                ["position"] = p.Position,
                ["in_jail"] = p.InJail,
            });
        }

        var ownership = new Dictionary<string, int>();
        for (int i = 0; i < _properties.Count; i++)
        {
            if (_properties[i].Owner >= 0)
                ownership[i.ToString()] = _properties[i].Owner;
        }

        int? currentTurnSeat = null;
        string? currentTurnName = null;
        if (ActivePlayers.Count > 0 && _currentPlayerIdx >= 0 && _currentPlayerIdx < ActivePlayers.Count)
        {
            currentTurnSeat = ActivePlayers[_currentPlayerIdx];
            currentTurnName = PlayerName(currentTurnSeat.Value);
        }

        return new Dictionary<string, object?>
        {
            ["monopoly"] = new Dictionary<string, object?>
            {
                ["players"] = players,
                ["ownership"] = ownership,
                ["current_turn_seat"] = currentTurnSeat,
                ["current_turn_name"] = currentTurnName,
            }
        };
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  GetPopupSnapshot (popup state for web UI)
    // ═══════════════════════════════════════════════════════════════════════
    public override Dictionary<string, object?> GetPopupSnapshot(int playerIdx)
    {
        if (!_popup.Active)
            return new Dictionary<string, object?> { ["active"] = false };

        if (_popup.PlayerIdx.HasValue && _popup.PlayerIdx.Value != playerIdx)
            return new Dictionary<string, object?> { ["active"] = false };

        static string? RgbToHex((int R, int G, int B) c) => $"#{c.R:x2}{c.G:x2}{c.B:x2}";

        var lines = _popup.TextLines.Select(l => l.Text).ToList();
        var lineItems = _popup.TextLines.Select(l => new Dictionary<string, object?>
        {
            ["text"] = l.Text,
            ["color"] = RgbToHex(l.Color),
        }).ToList();

        var buttons = new List<Dictionary<string, object?>>();
        if (_buttons.TryGetValue(playerIdx, out var btns))
        {
            foreach (var (id, btn) in btns)
            {
                if (!string.IsNullOrEmpty(btn.Text) && id.StartsWith("popup_"))
                    buttons.Add(new Dictionary<string, object?>
                    {
                        ["id"] = id,
                        ["text"] = btn.Text,
                        ["enabled"] = btn.Enabled,
                    });
            }
        }

        Dictionary<string, object?>? trade = null;
        Dictionary<string, object?>? tradeSelect = null;
        Dictionary<string, object?>? deedDetail = null;
        string popupType = _popup.PopupType ?? "";

        // ── Trade popup data ──
        if (popupType.StartsWith("trade_") && _tradeInitiator.HasValue && _tradePartner.HasValue)
        {
            var initiator = _players[_tradeInitiator.Value];
            var partner = _players[_tradePartner.Value];

            trade = new Dictionary<string, object?>
            {
                ["initiator"] = _tradeInitiator.Value,
                ["partner"] = _tradePartner.Value,
                ["offer"] = new Dictionary<string, object?>
                {
                    ["money"] = _tradeOfferMoney,
                    ["properties"] = _tradeOfferProps.Select(x => (object)x).ToList(),
                },
                ["request"] = new Dictionary<string, object?>
                {
                    ["money"] = _tradeRequestMoney,
                    ["properties"] = _tradeRequestProps.Select(x => (object)x).ToList(),
                },
                ["initiator_assets"] = new Dictionary<string, object?>
                {
                    ["money"] = initiator.Money,
                    ["properties"] = BuildPropCards(initiator),
                },
                ["partner_assets"] = new Dictionary<string, object?>
                {
                    ["money"] = partner.Money,
                    ["properties"] = BuildPropCards(partner),
                },
            };
        }

        // ── Trade partner selection data ──
        if (popupType == "trade_select" && _tradeInitiator.HasValue)
        {
            var candidates = new List<int>();
            for (int i = 0; i < ActivePlayers.Count; i++)
            {
                int seat = ActivePlayers[i];
                if (seat == _tradeInitiator.Value || _players[seat].IsBankrupt) continue;
                candidates.Add(i);
            }

            if (candidates.Count > 0)
            {
                int scrollPos = _tradeScrollIndex;
                if (!candidates.Contains(scrollPos) && candidates.Count > 0)
                    scrollPos = candidates[0];
                int partnerSeat = ActivePlayers[scrollPos];
                var partner = _players[partnerSeat];

                tradeSelect = new Dictionary<string, object?>
                {
                    ["initiator"] = _tradeInitiator.Value,
                    ["partner"] = partnerSeat,
                    ["partner_name"] = PlayerName(partnerSeat),
                    ["choice_index"] = candidates.IndexOf(scrollPos) + 1,
                    ["choice_count"] = candidates.Count,
                    ["partner_assets"] = new Dictionary<string, object?>
                    {
                        ["money"] = partner.Money,
                        ["properties"] = BuildPropCards(partner),
                    },
                };
            }
        }

        // ── Deed/mortgage detail ──
        if (popupType == "mortgage" && _popup.Data.TryGetValue("prop_idx", out var propIdxObj))
        {
            int dPropIdx = Convert.ToInt32(propIdxObj);
            if (dPropIdx >= 0 && dPropIdx < _properties.Count)
            {
                var dProp = _properties[dPropIdx];
                var dData = dProp.Data;
                int mortgageValue = dData.MortgageValue;
                int unmortgageCost = (int)(mortgageValue * 1.1);

                int? ownedInGroup = null;
                int? scrollIndex = null;
                int? scrollTotal = null;
                int? playerMoney = null;

                if (_popup.PlayerIdx.HasValue)
                {
                    var viewPlayer = _players[_popup.PlayerIdx.Value];
                    playerMoney = viewPlayer.Money;
                    scrollTotal = viewPlayer.Properties.Count;
                    scrollIndex = _mortgageScrollIndex + 1;
                    if (!string.IsNullOrEmpty(dData.Group))
                    {
                        ownedInGroup = viewPlayer.Properties.Count(pi =>
                            pi >= 0 && pi < _properties.Count && _properties[pi].Data.Group == dData.Group);
                    }
                }

                deedDetail = new Dictionary<string, object?>
                {
                    ["idx"] = dPropIdx,
                    ["name"] = dData.Name,
                    ["type"] = dData.Type,
                    ["group"] = dData.Group,
                    ["color"] = dData.Color != default ? RgbToHex(dData.Color) : null,
                    ["price"] = dData.Price,
                    ["mortgage_value"] = mortgageValue,
                    ["unmortgage_cost"] = unmortgageCost,
                    ["house_cost"] = dData.HouseCost,
                    ["rent_tiers"] = dData.Rent?.Select(x => (object)x).ToList(),
                    ["mortgaged"] = dProp.IsMortgaged,
                    ["houses"] = dProp.Houses,
                    ["owned_in_group"] = ownedInGroup,
                    ["scroll_index"] = scrollIndex,
                    ["scroll_total"] = scrollTotal,
                    ["player_money"] = playerMoney,
                };
            }
        }

        return new Dictionary<string, object?>
        {
            ["active"] = true,
            ["popup_type"] = popupType,
            ["lines"] = lines,
            ["line_items"] = lineItems,
            ["buttons"] = buttons,
            ["trade"] = trade,
            ["trade_select"] = tradeSelect,
            ["deed_detail"] = deedDetail,
        };
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  GetPanelButtons (per-player panel buttons for web UI)
    // ═══════════════════════════════════════════════════════════════════════
    public override List<Dictionary<string, object?>> GetPanelButtons(int playerIdx)
    {
        if (!_buttons.TryGetValue(playerIdx, out var btns)) return new();

        int? currTurnSeat = null;
        if (ActivePlayers.Count > 0 && _currentPlayerIdx >= 0 && _currentPlayerIdx < ActivePlayers.Count)
            currTurnSeat = ActivePlayers[_currentPlayerIdx];

        var result = new List<Dictionary<string, object?>>();
        foreach (var (id, btn) in btns)
        {
            if (id.StartsWith("popup_")) continue;
            string text = btn.Text;
            bool enabled = btn.Enabled;

            // Monopoly UX gating: non-current players get disabled action/build
            if (!currTurnSeat.HasValue)
            {
                if (id == "action") { text = "Roll"; enabled = false; }
                else if (id == "build") enabled = false;
            }
            else if (playerIdx != currTurnSeat.Value)
            {
                if (id == "action") { text = "Roll"; enabled = false; }
                else if (id == "build") enabled = false;
            }

            if (!string.IsNullOrEmpty(text))
            {
                result.Add(new Dictionary<string, object?>
                {
                    ["id"] = id,
                    ["text"] = text,
                    ["enabled"] = enabled,
                });
            }
        }
        return result;
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  Trade system
    // ═══════════════════════════════════════════════════════════════════════
    private void StartTrade(MonopolyPlayer player)
    {
        if (_popup.Active)
        {
            int? oldPidx = _popup.PlayerIdx;
            _popup.Hide();
            if (oldPidx.HasValue) RestoreDefaultButtons(oldPidx.Value);
        }

        _tradeInitiator = player.Idx;
        _tradePartner = null;
        _tradeOfferMoney = 0;
        _tradeRequestMoney = 0;
        _tradeOfferProps.Clear();
        _tradeRequestProps.Clear();
        _tradeScrollIndex = 0;
        _tradeMode = "select_partner";
        _tradeViewMode = "money";
        _tradeGiveScroll = 0;
        _tradeGetScroll = 0;

        foreach (int idx in ActivePlayers)
        {
            if (idx != player.Idx && !_players[idx].IsBankrupt)
            {
                _tradeScrollIndex = ActivePlayers.IndexOf(idx);
                break;
            }
        }

        ShowTradePartnerSelect();
    }

    private void ShowTradePartnerSelect()
    {
        if (!_tradeInitiator.HasValue) return;
        var initiator = _players[_tradeInitiator.Value];
        int partnerIdx = ActivePlayers[_tradeScrollIndex];
        var partner = _players[partnerIdx];

        if (!_panels.TryGetValue(initiator.Idx, out var panel)) return;

        var lines = new List<(string, int, (int, int, int))>
        {
            ("Select Trade Partner", 14, (255, 255, 255)),
            (SeatLabel(partnerIdx), 12, GameConfig.PlayerColors[partnerIdx]),
            ($"${partner.Money}", 10, (100, 255, 100)),
            ($"{partner.Properties.Count} Properties", 10, (200, 200, 200)),
        };

        _popup.Show(initiator.Idx, panel.Rect, panel.Orientation, "trade_select", lines,
            new() { ["partner_idx"] = partnerIdx });

        bool canPrev = FindPrevTradePartner().HasValue;
        bool canNext = FindNextTradePartner().HasValue;
        SetPopupButtons(initiator.Idx,
            new[] { canPrev ? "◄" : "Cancel", "Select", canNext ? "►" : "" },
            new[] { true, partnerIdx != initiator.Idx, canNext });
    }

    private int? FindPrevTradePartner()
    {
        for (int i = _tradeScrollIndex - 1; i >= 0; i--)
        {
            int idx = ActivePlayers[i];
            if (idx != _tradeInitiator && !_players[idx].IsBankrupt) return i;
        }
        return null;
    }

    private int? FindNextTradePartner()
    {
        for (int i = _tradeScrollIndex + 1; i < ActivePlayers.Count; i++)
        {
            int idx = ActivePlayers[i];
            if (idx != _tradeInitiator && !_players[idx].IsBankrupt) return i;
        }
        return null;
    }

    private void ShowTradeWebEdit()
    {
        if (!_tradeInitiator.HasValue || !_tradePartner.HasValue) return;
        var initiator = _players[_tradeInitiator.Value];
        var partner = _players[_tradePartner.Value];

        if (!_panels.TryGetValue(initiator.Idx, out var panel)) return;

        var lines = new List<(string, int, (int, int, int))>
        {
            ($"Trade with {SeatLabel(partner.Idx)}", 14, GameConfig.PlayerColors[partner.Idx]),
            ("Use the Web UI to edit the trade", 9, (200, 200, 200)),
        };
        _popup.Show(initiator.Idx, panel.Rect, panel.Orientation, "trade_web_edit", lines,
            new() { ["initiator_idx"] = initiator.Idx, ["partner_idx"] = partner.Idx });
        SetPopupButtons(initiator.Idx, new[] { "Cancel", "Send", "" }, new[] { true, true, false });
    }

    private void ShowTradeWebResponse()
    {
        if (!_tradeInitiator.HasValue || !_tradePartner.HasValue) return;
        var initiator = _players[_tradeInitiator.Value];
        var partner = _players[_tradePartner.Value];

        if (!_panels.TryGetValue(partner.Idx, out var panel)) return;

        var lines = new List<(string, int, (int, int, int))>
        {
            ($"{SeatLabel(initiator.Idx)} offers a trade", 14, GameConfig.PlayerColors[initiator.Idx]),
            ("Review in the Web UI", 9, (200, 200, 200)),
        };
        _popup.Show(partner.Idx, panel.Rect, panel.Orientation, "trade_web_response", lines,
            new() { ["initiator_idx"] = initiator.Idx, ["partner_idx"] = partner.Idx });
        SetPopupButtons(partner.Idx, new[] { "Decline", "", "Accept" }, new[] { true, false, true });
    }

    private void ShowTradeProposal()
    {
        if (!_tradeInitiator.HasValue || !_tradePartner.HasValue) return;
        var initiator = _players[_tradeInitiator.Value];
        var partner = _players[_tradePartner.Value];

        if (!_panels.TryGetValue(partner.Idx, out var panel)) return;

        string getting = _tradeOfferMoney > 0 ? $"${_tradeOfferMoney}" : "Nothing";
        if (_tradeOfferProps.Count > 0) getting += $" + {_tradeOfferProps.Count} prop(s)";
        string giving = _tradeRequestMoney > 0 ? $"${_tradeRequestMoney}" : "Nothing";
        if (_tradeRequestProps.Count > 0) giving += $" + {_tradeRequestProps.Count} prop(s)";

        var lines = new List<(string, int, (int, int, int))>
        {
            ($"{SeatLabel(initiator.Idx)} offers trade", 14, GameConfig.PlayerColors[initiator.Idx]),
            ($"You get: {getting}", 10, (100, 255, 100)),
            ($"You give: {giving}", 10, (255, 100, 100)),
            ("Accept or Decline?", 9, (200, 200, 200)),
        };
        _popup.Show(partner.Idx, panel.Rect, panel.Orientation, "trade_response", lines,
            new() { ["initiator_idx"] = initiator.Idx, ["partner_idx"] = partner.Idx });
        SetPopupButtons(partner.Idx, new[] { "Decline", "View", "Accept" }, new[] { true, true, true });
    }

    private void ShowTradeDetailView()
    {
        if (!_tradeInitiator.HasValue || !_tradePartner.HasValue) return;
        var initiator = _players[_tradeInitiator.Value];
        var partner = _players[_tradePartner.Value];

        if (!_panels.TryGetValue(partner.Idx, out var panel)) return;

        var lines = new List<(string, int, (int, int, int))>
        {
            ($"{SeatLabel(initiator.Idx)}'s Offer", 12, GameConfig.PlayerColors[initiator.Idx]),
            ($"${_tradeOfferMoney}", 10, (100, 255, 100)),
        };
        foreach (int pi in _tradeOfferProps.Take(3))
        {
            if (pi >= 0 && pi < _properties.Count)
                lines.Add((_properties[pi].Data.Name, 9, _properties[pi].Data.Color != default ? _properties[pi].Data.Color : (200, 200, 200)));
        }
        if (_tradeOfferProps.Count > 3) lines.Add(($"+{_tradeOfferProps.Count - 3} more", 9, (200, 200, 200)));
        if (_tradeOfferProps.Count == 0) lines.Add(("(no properties)", 9, (200, 200, 200)));

        lines.Add(("For:", 10, (255, 255, 100)));
        lines.Add(($"${_tradeRequestMoney}", 10, (255, 100, 100)));
        foreach (int pi in _tradeRequestProps.Take(3))
        {
            if (pi >= 0 && pi < _properties.Count)
                lines.Add((_properties[pi].Data.Name, 9, _properties[pi].Data.Color != default ? _properties[pi].Data.Color : (200, 200, 200)));
        }
        if (_tradeRequestProps.Count > 3) lines.Add(($"+{_tradeRequestProps.Count - 3} more", 9, (200, 200, 200)));
        if (_tradeRequestProps.Count == 0) lines.Add(("(no properties)", 9, (200, 200, 200)));

        _popup.Show(partner.Idx, panel.Rect, panel.Orientation, "trade_detail", lines,
            new() { ["initiator_idx"] = initiator.Idx, ["partner_idx"] = partner.Idx });
        SetPopupButtons(partner.Idx, new[] { "Decline", "Back", "Accept" }, new[] { true, true, true });
    }

    private void ShowTradeModify()
    {
        if (!_tradeInitiator.HasValue || !_tradePartner.HasValue) return;
        var initiator = _players[_tradeInitiator.Value];
        var partner = _players[_tradePartner.Value];

        if (!_panels.TryGetValue(initiator.Idx, out var panel)) return;

        var lines = new List<(string, int, (int, int, int))>();
        if (_tradeViewMode == "money")
        {
            lines.Add(($"Trade with {SeatLabel(partner.Idx)}", 14, GameConfig.PlayerColors[partner.Idx]));
            lines.Add(("--- YOU GIVE ---", 11, (255, 100, 100)));
            lines.Add(($"${_tradeOfferMoney}", 10, (255, 150, 150)));
            lines.Add(($"{_tradeOfferProps.Count} Props", 9, (255, 180, 180)));
            lines.Add(("--- YOU GET ---", 11, (100, 255, 100)));
            lines.Add(($"${_tradeRequestMoney}", 10, (150, 255, 150)));
            lines.Add(($"{_tradeRequestProps.Count} Props", 9, (180, 255, 180)));
            SetPopupButtons(initiator.Idx, new[] { "Give $", "Get $", "Done" }, new[] { true, true, true });
        }
        else if (_tradeViewMode == "give_props")
        {
            var yourProps = initiator.Properties.Where(p => !_properties[p].IsMortgaged && _properties[p].Houses == 0).ToList();
            if (yourProps.Count > 0)
            {
                _tradeGiveScroll = Math.Clamp(_tradeGiveScroll, 0, yourProps.Count - 1);
                int pIdx = yourProps[_tradeGiveScroll];
                var prop = _properties[pIdx];
                bool isSel = _tradeOfferProps.Contains(pIdx);
                lines.Add(("YOUR PROPERTIES", 14, (255, 100, 100)));
                lines.Add(($"{_tradeGiveScroll + 1}/{yourProps.Count}", 10, (200, 200, 200)));
                lines.Add((prop.Data.Name, 12, prop.Data.Color != default ? prop.Data.Color : (255, 255, 255)));
                lines.Add((isSel ? "✓ Selected" : "Not selected", 10, isSel ? (100, 255, 100) : (150, 150, 150)));
                bool canPrev = _tradeGiveScroll > 0;
                SetPopupButtons(initiator.Idx, new[] { canPrev ? "◄" : "Back", "Toggle", "►" }, new[] { true, true, true });
            }
            else
            {
                lines.Add(("No properties", 12, (200, 200, 200)));
                SetPopupButtons(initiator.Idx, new[] { "Back", "", "" }, new[] { true, false, false });
            }
        }
        else if (_tradeViewMode == "get_props")
        {
            var theirProps = partner.Properties.Where(p => !_properties[p].IsMortgaged && _properties[p].Houses == 0).ToList();
            if (theirProps.Count > 0)
            {
                _tradeGetScroll = Math.Clamp(_tradeGetScroll, 0, theirProps.Count - 1);
                int pIdx = theirProps[_tradeGetScroll];
                var prop = _properties[pIdx];
                bool isSel = _tradeRequestProps.Contains(pIdx);
                lines.Add(("THEIR PROPERTIES", 14, (100, 255, 100)));
                lines.Add(($"{_tradeGetScroll + 1}/{theirProps.Count}", 10, (200, 200, 200)));
                lines.Add((prop.Data.Name, 12, prop.Data.Color != default ? prop.Data.Color : (255, 255, 255)));
                lines.Add((isSel ? "✓ Selected" : "Not selected", 10, isSel ? (100, 255, 100) : (150, 150, 150)));
                bool canPrev = _tradeGetScroll > 0;
                SetPopupButtons(initiator.Idx, new[] { canPrev ? "◄" : "Back", "Toggle", "►" }, new[] { true, true, true });
            }
            else
            {
                lines.Add(("No properties", 12, (200, 200, 200)));
                SetPopupButtons(initiator.Idx, new[] { "Back", "", "" }, new[] { true, false, false });
            }
        }
        _popup.Show(initiator.Idx, panel.Rect, panel.Orientation, "trade_modify", lines,
            new() { ["initiator_idx"] = initiator.Idx, ["partner_idx"] = partner.Idx });
    }

    private void ShowTradeBuildOffer()
    {
        if (!_tradeInitiator.HasValue || !_tradePartner.HasValue) return;
        var initiator = _players[_tradeInitiator.Value];
        var partner = _players[_tradePartner.Value];

        if (!_panels.TryGetValue(initiator.Idx, out var panel)) return;

        string offering = _tradeOfferMoney > 0 ? $"${_tradeOfferMoney}" : "Nothing";
        if (_tradeOfferProps.Count > 0) offering += $" + {_tradeOfferProps.Count} prop(s)";
        string requesting = _tradeRequestMoney > 0 ? $"${_tradeRequestMoney}" : "Nothing";
        if (_tradeRequestProps.Count > 0) requesting += $" + {_tradeRequestProps.Count} prop(s)";

        var lines = new List<(string, int, (int, int, int))>
        {
            ($"Trade with {SeatLabel(partner.Idx)}", 14, GameConfig.PlayerColors[partner.Idx]),
            ($"Offering: {offering}", 10, (100, 255, 100)),
            ($"For: {requesting}", 10, (255, 255, 100)),
            ("Build your offer", 9, (200, 200, 200)),
        };
        _popup.Show(initiator.Idx, panel.Rect, panel.Orientation, "trade_build", lines,
            new() { ["initiator_idx"] = initiator.Idx, ["partner_idx"] = partner.Idx });
        SetPopupButtons(initiator.Idx, new[] { "Cancel", "Modify", "Send" }, new[] { true, true, true });
    }

    private bool ExecuteTrade()
    {
        if (!_tradeInitiator.HasValue || !_tradePartner.HasValue) return false;
        var initiator = _players[_tradeInitiator.Value];
        var partner = _players[_tradePartner.Value];

        if (initiator.Idx == partner.Idx || initiator.IsBankrupt || partner.IsBankrupt) return false;
        if (_tradeOfferMoney < 0 || _tradeRequestMoney < 0) return false;
        if (initiator.Money < _tradeOfferMoney) return false;
        if (partner.Money < _tradeRequestMoney) return false;

        foreach (int propIdx in _tradeOfferProps)
        {
            if (!initiator.Properties.Contains(propIdx)) return false;
            var prop = _properties[propIdx];
            if (prop.IsMortgaged || prop.Houses > 0 || GroupHasBuildings(propIdx)) return false;
        }
        foreach (int propIdx in _tradeRequestProps)
        {
            if (!partner.Properties.Contains(propIdx)) return false;
            var prop = _properties[propIdx];
            if (prop.IsMortgaged || prop.Houses > 0 || GroupHasBuildings(propIdx)) return false;
        }

        if (_tradeOfferMoney > 0)
        {
            if (!initiator.RemoveMoney(_tradeOfferMoney)) return false;
            partner.AddMoney(_tradeOfferMoney);
        }
        if (_tradeRequestMoney > 0)
        {
            if (!partner.RemoveMoney(_tradeRequestMoney)) return false;
            initiator.AddMoney(_tradeRequestMoney);
        }

        foreach (int propIdx in _tradeOfferProps.ToList())
        {
            if (initiator.Properties.Contains(propIdx))
            {
                initiator.Properties.Remove(propIdx);
                partner.Properties.Add(propIdx);
                _properties[propIdx].Owner = partner.Idx;
            }
        }
        foreach (int propIdx in _tradeRequestProps.ToList())
        {
            if (partner.Properties.Contains(propIdx))
            {
                partner.Properties.Remove(propIdx);
                initiator.Properties.Add(propIdx);
                _properties[propIdx].Owner = initiator.Idx;
            }
        }

        PushToast($"🤝 {SeatLabel(initiator.Idx)} traded with {SeatLabel(partner.Idx)}", (120, 255, 180), 4.0);
        var (bx, by, bw, bh) = _boardRect;
        int tcx = bx + bw / 2, tcy = by + bh / 2;
        _textPops.Add(new TextPopAnim("🤝 Trade!", tcx, tcy - 30, (120, 255, 180), 26));
        _pulseRings.Add(new PulseRing(tcx, tcy, (120, 255, 180), 80, 0.7f));
        _particles.EmitSparkle(tcx, tcy, (120, 255, 180));

        return true;
    }

    private List<Dictionary<string, object?>> BuildPropCards(MonopolyPlayer player)
    {
        var result = new List<Dictionary<string, object?>>();
        foreach (int pi in player.Properties)
        {
            if (pi < 0 || pi >= _properties.Count) continue;
            var prop = _properties[pi];
            var data = prop.Data;
            bool groupHasBuildings = false;
            if (!string.IsNullOrEmpty(data.Group) && MonopolyData.PropertyGroups.TryGetValue(data.Group, out var gp))
                groupHasBuildings = gp.Any(p => _properties[p].Houses > 0);

            string? colorHex = data.Color != default ? $"#{data.Color.R:x2}{data.Color.G:x2}{data.Color.B:x2}" : null;
            result.Add(new Dictionary<string, object?>
            {
                ["idx"] = pi,
                ["name"] = data.Name,
                ["color"] = colorHex,
                ["mortgaged"] = prop.IsMortgaged,
                ["houses"] = prop.Houses,
                ["tradable"] = !prop.IsMortgaged && prop.Houses == 0 && !groupHasBuildings,
            });
        }
        return result;
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  Draw — Main entry
    // ═══════════════════════════════════════════════════════════════════════
    public override void Draw(Renderer r, int width, int height, double dt)
    {
        if (State == "player_select") { base.Draw(r, width, height, dt); return; }
        if (State == "winner") { DrawWinnerScreen(r, width, height); return; }

        if (BoardOnlyMode)
        {
            // Full-screen board, no panels
            CardRendering.DrawGameBackground(r, width, height, "monopoly");
            _ambient.Draw(r);
            _lightBeams.Draw(r, width, height);
            _starfield.Draw(r);
            _floatingIcons.Draw(r);
            int margin = 10;
            int size = Math.Max(200, Math.Min(width - 2 * margin, height - 2 * margin));
            int bx = margin + (width - 2 * margin - size) / 2;
            int by = margin + (height - 2 * margin - size) / 2;
            _boardRect = (bx, by, size, size);
            CalculateSpaces();
            DrawBoard(r);
            DrawTokens(r);
            if (_diceRolling || _diceValues != (0, 0)) DrawDice(r);
            DrawToasts(r, width, height);
            DrawAnimations(r, width, height);
            return;
        }

        // Background
        CardRendering.DrawGameBackground(r, width, height, "monopoly");
        _ambient.Draw(r);
        _lightBeams.Draw(r, width, height);
        _starfield.Draw(r);
        _floatingIcons.Draw(r);

        // Panels
        DrawPanels(r);

        // Board
        DrawBoard(r);

        // Tokens
        DrawTokens(r);

        // Dice
        if (_diceRolling || _diceValues != (0, 0)) DrawDice(r);

        // Toasts
        DrawToasts(r, width, height);

        // Popups
        if (_popup.Active)
        {
            r.DrawRect((0, 0, 0), (0, 0, width, height), alpha: 50);
            _popup.Draw(r);
        }

        // Animations
        DrawAnimations(r, width, height);
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  Draw — Panels
    // ═══════════════════════════════════════════════════════════════════════
    private void DrawPanels(Renderer r)
    {
        int currIdx = CurrentSeat;
        foreach (int idx in ActivePlayers)
        {
            var player = _players[idx];
            var panel = _panels[idx];
            bool isCurrent = idx == currIdx;
            panel.DrawBackground(r, isCurrent);

            // Balance text
            string jailInd = player.GetOutOfJailCards > 0 ? " 🔑" : "";
            string moneyText = $"${player.Money}{jailInd}";
            panel.DrawTextOriented(r, moneyText, 0.5f, 0.30f, 20, (0, 0, 0));

            // Draw name
            panel.DrawTextOriented(r, SeatLabel(idx), 0.5f, 0.12f, 14, (255, 255, 255));

            // Buttons
            if (_buttons.TryGetValue(idx, out var btns))
                foreach (var btn in btns.Values)
                    btn.Draw(r);
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  Draw — Board
    // ═══════════════════════════════════════════════════════════════════════
    private void DrawBoard(Renderer r)
    {
        var (bx, by, bw, bh) = _boardRect;

        // Shadow
        r.DrawRect((0, 0, 0), (bx + 5, by + 5, bw, bh), alpha: 80);
        // Board base
        r.DrawRect((215, 235, 215), (bx, by, bw, bh));
        // Inner fill
        r.DrawRect((230, 245, 228), (bx + 4, by + 4, bw - 8, bh - 8), alpha: 120);
        // Gold border
        r.DrawRect((160, 140, 80), (bx, by, bw, bh), width: 3);

        // Draw each space
        for (int i = 0; i < _spaces.Count && i < _properties.Count; i++)
        {
            var (sx, sy, sw, sh) = _spaces[i];
            var space = _properties[i];
            string spaceType = space.Data.Type;

            // Shadow + background
            r.DrawRect((0, 0, 0), (sx + 2, sy + 2, sw, sh), alpha: 30);
            r.DrawRect((248, 248, 245), (sx, sy, sw, sh));

            // Color bar
            if (space.Data.Color != default)
            {
                var pc = space.Data.Color;
                int barH = Math.Max(12, sh / 3);
                r.DrawRect(pc, (sx + 1, sy + 1, sw - 2, barH));
                var hl = (Math.Min(255, pc.R + 60), Math.Min(255, pc.G + 60), Math.Min(255, pc.B + 60));
                r.DrawRect(hl, (sx + 1, sy + barH - 2, sw - 2, 2), alpha: 100);
            }

            // Owner glow
            if (space.Owner >= 0 && (spaceType == "property" || spaceType == "railroad" || spaceType == "utility"))
            {
                var oc = GameConfig.PlayerColors[space.Owner];
                r.DrawRect(oc, (sx - 1, sy - 1, sw + 2, sh + 2), width: 4, alpha: 100);
                r.DrawRect(oc, (sx + 2, sy + 2, sw - 4, sh - 4), width: 3);
            }

            // Houses/Hotels
            if (space.Houses > 0 && spaceType == "property")
            {
                if (space.Houses == 5)
                {
                    int hx = sx + sw / 2 - 10, hy = sy + sh - 16;
                    r.DrawRect((200, 0, 0), (hx, hy, 20, 14));
                    r.DrawText("H", hx + 10, hy + 7, 10, (255, 255, 255), anchorX: "center", anchorY: "center");
                }
                else
                {
                    int hw = 9, hh = 9, gap = 3;
                    int totalW = space.Houses * hw + (space.Houses - 1) * gap;
                    int sx0 = sx + (sw - totalW) / 2;
                    int hy = sy + sh - 14;
                    for (int j = 0; j < space.Houses; j++)
                    {
                        int hx = sx0 + j * (hw + gap);
                        r.DrawRect((20, 180, 20), (hx, hy, hw, hh));
                        r.DrawRect((10, 120, 10), (hx, hy, hw, hh), width: 1);
                    }
                }
            }

            // Space name (word-wrapped, always horizontal)
            string name = space.Data.Name;
            if (!string.IsNullOrEmpty(name) && (!_popup.Active || BoardOnlyMode))
            {
                int cx = sx + sw / 2, cy = sy + sh / 2;

                // Free Parking special
                if (i == 20 && spaceType == "free_parking" && _freeParkingPot > 0)
                {
                    r.DrawText("Free", cx, cy - 8, 11, (0, 0, 0), anchorX: "center", anchorY: "center");
                    r.DrawText("Parking", cx, cy + 4, 11, (0, 0, 0), anchorX: "center", anchorY: "center");
                    r.DrawText($"${_freeParkingPot}", cx, cy + 16, 10, (255, 215, 0), anchorX: "center", anchorY: "center");
                }
                else
                {
                    var words = name.Split(' ');
                    int fs = name.Length > 12 ? 10 : name.Length > 10 ? 11 : 12;
                    if (words.Length > 1)
                    {
                        // Multi-line
                        var lines = new List<string>();
                        string cur = "";
                        foreach (string w in words)
                        {
                            string test = string.IsNullOrEmpty(cur) ? w : cur + " " + w;
                            if (test.Length <= 9) cur = test;
                            else { if (cur.Length > 0) lines.Add(cur); cur = w; }
                        }
                        if (cur.Length > 0) lines.Add(cur);
                        int lh = fs + 2;
                        int totalH = lines.Count * lh;
                        int startY = cy - totalH / 2 + lh / 2;
                        for (int li = 0; li < lines.Count; li++)
                            r.DrawText(lines[li], cx, startY + li * lh, fs, (0, 0, 0), anchorX: "center", anchorY: "center");
                    }
                    else
                    {
                        r.DrawText(name, cx, cy, fs, (0, 0, 0), anchorX: "center", anchorY: "center");
                    }
                }
            }

            // Border
            r.DrawRect((80, 80, 80), (sx, sy, sw, sh), width: 1);
        }

        // Card banner
        if (_cardBannerText != null && _cardBannerTs > 0 && _clock - _cardBannerTs <= 10.0)
        {
            string title = _cardBannerDeck == "chance" ? "❓ Chance" : "🎁 Community Chest";
            string raw = _cardBannerText;
            var lines = new List<string>();
            string cur2 = "";
            foreach (string w in raw.Split(' '))
            {
                string nxt = string.IsNullOrEmpty(cur2) ? w : cur2 + " " + w;
                if (nxt.Length <= 34) cur2 = nxt;
                else { if (cur2.Length > 0) lines.Add(cur2); cur2 = w; }
            }
            if (cur2.Length > 0) lines.Add(cur2);
            if (lines.Count > 4) lines = lines.Take(4).ToList();

            int bw2 = (int)(bw * 0.56), bh2 = (int)(bh * 0.15);
            int x2 = bx + (bw - bw2) / 2;
            int y2 = by + (int)(bh * 0.22) + bh2 / 2;
            r.DrawRect((255, 255, 240), (x2, y2, bw2, bh2), alpha: 235);
            r.DrawRect((80, 80, 80), (x2, y2, bw2, bh2), width: 2);
            r.DrawText(title, x2 + bw2 / 2, y2 + (int)(bh2 * 0.70), 14, (20, 20, 20), bold: true, anchorX: "center", anchorY: "center");
            int baseY = y2 + (int)(bh2 * 0.48);
            for (int li = 0; li < lines.Count; li++)
                r.DrawText(lines[li], x2 + bw2 / 2, baseY - li * 16, 11, (20, 20, 20), anchorX: "center", anchorY: "center");
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  Draw — Tokens
    // ═══════════════════════════════════════════════════════════════════════
    private void DrawTokens(Renderer r)
    {
        foreach (int idx in ActivePlayers)
        {
            var player = _players[idx];
            if (player.IsBankrupt) continue;

            int cx, cy;
            if (_tokenAnims.TryGetValue(idx, out var anim))
            {
                double totalElapsed = _clock - anim.StartTime;
                int seg = (int)(totalElapsed / anim.SegmentDuration);
                if (seg >= anim.Path.Count)
                {
                    _tokenAnims.Remove(idx);
                    var (sx2, sy2, sw2, sh2) = _spaces[player.Position];
                    cx = sx2 + sw2 / 2; cy = sy2 + sh2 / 2;
                }
                else
                {
                    double segProgress = (totalElapsed - seg * anim.SegmentDuration) / anim.SegmentDuration;
                    int startPos = seg == 0 ? anim.StartPos : anim.Path[seg - 1];
                    int endPos = anim.Path[seg];
                    var (sx1, sy1, sw1, sh1) = _spaces[startPos];
                    var (ex1, ey1, ew1, eh1) = _spaces[endPos];
                    int scx = sx1 + sw1 / 2, scy = sy1 + sh1 / 2;
                    int ecx = ex1 + ew1 / 2, ecy = ey1 + eh1 / 2;
                    cx = (int)(scx + (ecx - scx) * segProgress);
                    cy = (int)(scy + (ecy - scy) * segProgress);
                    double jumpH = 40 * (1 - Math.Pow(2 * segProgress - 1, 2));
                    cy -= (int)jumpH;
                }
            }
            else
            {
                var (sx, sy, sw, sh) = _spaces[player.Position];
                cx = sx + sw / 2; cy = sy + sh / 2;
            }

            // Offset for multiple players
            int oIdx = ActivePlayers.IndexOf(idx);
            if (ActivePlayers.Count > 1)
            {
                double angle = (double)oIdx / ActivePlayers.Count * 6.28;
                cx += (int)(12 * Math.Cos(angle));
                cy += (int)(12 * Math.Sin(angle));
            }

            var color = GameConfig.PlayerColors[idx];
            // Shadow
            r.DrawCircle((0, 0, 0), (cx + 3, cy + 3), 16, alpha: 60);
            // Glow for current
            if (idx == CurrentSeat) r.DrawCircle(color, (cx, cy), 22, alpha: 40);
            // Body
            r.DrawCircle(color, (cx, cy), 16);
            // Highlight
            var hl = (Math.Min(255, color.R + 70), Math.Min(255, color.G + 70), Math.Min(255, color.B + 70));
            r.DrawCircle(hl, (cx - 4, cy - 4), 6, alpha: 90);
            // Outline
            r.DrawCircle((0, 0, 0), (cx, cy), 16, width: 2);
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  Draw — Dice
    // ═══════════════════════════════════════════════════════════════════════
    private void DrawDice(Renderer r)
    {
        var (bx, by, bw, bh) = _boardRect;
        int cx = bx + bw / 2, cy = by + bh / 2;
        int diceSize = 64, gap = 18;

        var display = _diceRolling ? (Rng.Next(1, 7), Rng.Next(1, 7)) : _diceValues;

        // Fly-in
        double flyT = 1.0;
        double flyDur = 0.35;
        if (_diceFlyStart > 0 && _clock - _diceFlyStart < flyDur)
        {
            double raw = (_clock - _diceFlyStart) / flyDur;
            flyT = 1.0 - Math.Pow(1.0 - raw, 3);
        }
        int flyCx = (int)(_diceFlyFrom.X + (cx - _diceFlyFrom.X) * flyT);
        int flyCy = (int)(_diceFlyFrom.Y + (cy - _diceFlyFrom.Y) * flyT);

        // Glow
        double glow = 0;
        if (!_diceRolling && _diceValues != (0, 0))
        {
            double since = _clock - (_diceRollStart + 1.2);
            if (since >= 0 && since < 0.55) glow = 1.0 - since / 0.55;
        }

        for (int i = 0; i < 2; i++)
        {
            int val = i == 0 ? display.Item1 : display.Item2;
            int jx = 0, jy = 0, bounce = 0;
            if (_diceRolling)
            {
                double ph = _clock * 34 + i * 2.3;
                jx = (int)(6 * Math.Sin(ph));
                jy = (int)(5 * Math.Cos(ph * 1.35 + 0.8));
            }
            if (glow > 0.25) bounce = (int)(10 * Math.Sin(Math.PI * (glow - 0.25) / 0.75));

            int dx = (int)(flyCx + (i - 0.5) * (diceSize + gap)) + jx;
            int dy = flyCy + jy - bounce;
            int hx = dx - diceSize / 2, hy = dy - diceSize / 2;

            // Shadow layers
            r.DrawRect((0, 0, 0), (hx + 6, hy + 6, diceSize, diceSize), alpha: 45);
            r.DrawRect((0, 0, 0), (hx + 3, hy + 3, diceSize, diceSize), alpha: 70);
            // Face
            r.DrawRect((250, 250, 255), (hx, hy, diceSize, diceSize));
            // Bottom shade
            r.DrawRect((210, 210, 220), (hx + 2, hy + diceSize * 2 / 3, diceSize - 4, diceSize / 3 - 2), alpha: 35);
            // Top highlight
            r.DrawRect((255, 255, 255), (hx + 3, hy + 2, diceSize - 6, 7), alpha: 140);
            // Border
            r.DrawRect((40, 40, 48), (hx, hy, diceSize, diceSize), width: 2, alpha: 230);
            // Inner bevel
            r.DrawRect((180, 180, 195), (hx + 4, hy + 4, diceSize - 8, diceSize - 8), width: 1, alpha: 55);
            // Glow
            if (glow > 0)
            {
                int ga = (int)(90 * glow);
                r.DrawRect((255, 215, 0), (hx - 4, hy - 4, diceSize + 8, diceSize + 8), width: 3, alpha: ga);
            }
            // Pips
            DiePips.Draw(r, dx, dy, diceSize, val);
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  Draw — Toasts
    // ═══════════════════════════════════════════════════════════════════════
    private void DrawToasts(Renderer r, int width, int height)
    {
        // Prune expired
        _toasts.RemoveAll(t => _clock - t.Ts > t.Ttl);
        _sparkles.RemoveAll(s => _clock - s.Ts >= s.Ttl);
        if (_toasts.Count == 0 && _sparkles.Count == 0) return;

        var (bx, by, bw, bh) = _boardRect;
        int cx = bx + bw / 2, cy = by + bh / 2;

        // Dark overlay
        if (_toasts.Count > 0)
        {
            double newestAge = _toasts.Min(t => _clock - t.Ts);
            double oldestRemain = _toasts.Min(t => t.Ttl - (_clock - t.Ts));
            double dimIn = Math.Min(1.0, newestAge / 0.12);
            double dimOut = oldestRemain < 0.4 ? Math.Min(1.0, oldestRemain / 0.4) : 1.0;
            int dimAlpha = (int)(100 * dimIn * dimOut);
            if (dimAlpha > 1) r.DrawRect((0, 0, 0), (0, 0, width, height), alpha: dimAlpha);
        }

        int baseY = cy + 55;
        int maxVisible = 4;
        int rowH = 22;
        int fontSize = 20;
        double slideInDur = 0.28, slideOutDur = 0.35;
        int slideDist = width / 2 + 120;

        var visible = _toasts.AsEnumerable().Reverse().Take(maxVisible).ToList();
        for (int i = 0; i < visible.Count; i++)
        {
            var t = visible[i];
            double age = _clock - t.Ts;
            double remain = t.Ttl - age;

            double slideX = 0;
            double alphaMult = 1.0;
            if (age < slideInDur)
            {
                double raw = age / slideInDur;
                double ease = 1.0 - Math.Pow(1.0 - raw, 3);
                slideX = -(1.0 - ease) * slideDist;
            }
            else if (remain < slideOutDur)
            {
                double raw = 1.0 - Math.Max(0, remain / slideOutDur);
                double ease = raw * raw;
                slideX = ease * slideDist;
                alphaMult = Math.Max(0, 1.0 - raw);
            }

            int y = baseY + i * rowH;
            int tw = (int)(bw * 0.92);
            int th = 18;
            int tx = cx - tw / 2 + (int)slideX;
            int aBg = (int)(200 * alphaMult);
            int aBorder = (int)(90 * alphaMult);
            int aGlow = (int)(45 * alphaMult);
            int aText = (int)(255 * alphaMult);

            // Outer glow
            r.DrawRect((255, 200, 50), (tx - 2, y - th / 2 - 2, tw + 4, th + 4), alpha: Math.Max(1, aGlow));
            // Shadow
            r.DrawRect((0, 0, 0), (tx + 3, y - th / 2 + 3, tw, th), alpha: Math.Max(1, aBg / 2));
            // Background
            r.DrawRect((15, 12, 8), (tx, y - th / 2, tw, th), alpha: aBg);
            // Top highlight
            r.DrawRect((255, 220, 100), (tx + 2, y - th / 2, tw - 4, 1), alpha: Math.Max(1, aBorder));
            // Border
            r.DrawRect((200, 170, 40), (tx, y - th / 2, tw, th), width: 1, alpha: aBorder);
            // Text
            r.DrawText(t.Text, cx + (int)slideX, y, fontSize, t.Color, bold: true, anchorX: "center", anchorY: "center", alpha: aText);

            // Sparkles
            if (alphaMult > 0.3 && Rng.NextDouble() < 0.45)
            {
                _sparkles.Add(new ToastSparkle { X0 = tx + Rng.Next(-12, 6), Y0 = y + Rng.Next(-th / 2 - 8, th / 2 + 8),
                    Vx = Rng.NextDouble() * -14 - 4, Vy = Rng.NextDouble() * 44 - 22, Ts = _clock, Ttl = Rng.NextDouble() * 0.4 + 0.3,
                    Size = Rng.NextDouble() * 3 + 2, Color = SparkleColor() });
            }
            if (alphaMult > 0.3 && Rng.NextDouble() < 0.45)
            {
                _sparkles.Add(new ToastSparkle { X0 = tx + tw + Rng.Next(-6, 12), Y0 = y + Rng.Next(-th / 2 - 8, th / 2 + 8),
                    Vx = Rng.NextDouble() * 14 + 4, Vy = Rng.NextDouble() * 44 - 22, Ts = _clock, Ttl = Rng.NextDouble() * 0.4 + 0.3,
                    Size = Rng.NextDouble() * 3 + 2, Color = SparkleColor() });
            }
        }

        // Draw sparkles
        foreach (var s in _sparkles)
        {
            double sAge = _clock - s.Ts;
            double sLife = sAge / s.Ttl;
            if (sLife >= 1.0) continue;
            int px = (int)(s.X0 + s.Vx * sAge);
            int py = (int)(s.Y0 + s.Vy * sAge);
            int sAlpha = (int)(220 * (1.0 - sLife));
            int sSize = Math.Max(1, (int)(s.Size * (1.0 - sLife * 0.6)));
            r.DrawCircle(s.Color, (px, py), sSize, alpha: sAlpha);
            if (sSize > 2) r.DrawCircle((255, 255, 255), (px, py), Math.Max(1, sSize / 2), alpha: Math.Min(255, sAlpha + 40));
        }
        if (_sparkles.Count > 80) _sparkles.RemoveRange(0, _sparkles.Count - 60);
    }

    private (int R, int G, int B) SparkleColor()
    {
        return Rng.Next(4) switch
        {
            0 => (255, 230, 80), 1 => (255, 200, 50), 2 => (255, 255, 180), _ => (255, 180, 40),
        };
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  Draw — Winner screen
    // ═══════════════════════════════════════════════════════════════════════
    private void DrawWinnerScreen(Renderer r, int w, int h)
    {
        r.DrawRect((10, 10, 18), (0, 0, w, h), alpha: 230);
        // Rainbow title would go here (simplified)
        r.DrawText("MONOPOLY", w / 2, 50, 48, (255, 220, 80), bold: true, anchorX: "center", anchorY: "center");

        if (_winnerIdx is not int wi) return;
        int cx = w / 2, cy = h / 2;
        int bw2 = Math.Min(800, (int)(w * 0.7)), bh2 = 360;
        int bx = cx - bw2 / 2, by = cy - bh2 / 2;
        var wc = GameConfig.PlayerColors[wi];

        r.DrawRect((0, 0, 0), (bx + 6, by + 6, bw2, bh2), alpha: 100);
        r.DrawRect(wc, (bx, by, bw2, bh2));
        r.DrawRect((0, 0, 0), (bx + 8, by + 8, bw2 - 16, bh2 - 16), alpha: 100);
        r.DrawRect((255, 215, 0), (bx, by, bw2, bh2), width: 5);
        r.DrawCircle(wc, (cx, cy), (int)(Math.Min(bw2, bh2) * 0.28), alpha: 25);

        r.DrawText($"{SeatLabel(wi)} WINS!", cx + 3, cy - 47, 56, (0, 0, 0), bold: true, anchorX: "center", anchorY: "center", alpha: 120);
        r.DrawText($"{SeatLabel(wi)} WINS!", cx, cy - 50, 56, (255, 255, 255), bold: true, anchorX: "center", anchorY: "center");
        r.DrawText("MONOPOLY CHAMPION", cx, cy + 20, 36, (255, 255, 200), bold: true, anchorX: "center", anchorY: "center");
        r.DrawText($"Final Balance: ${_players[wi].Money}", cx, cy + 80, 26, (255, 255, 255), anchorX: "center", anchorY: "center");

        DrawAnimations(r, w, h);
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  Draw — Animations
    // ═══════════════════════════════════════════════════════════════════════
    private void DrawAnimations(Renderer r, int w, int h)
    {
        _particles.Draw(r);
        foreach (var pr in _pulseRings) pr.Draw(r);
        foreach (var cf in _cardFlips) cf.Draw(r);
        foreach (var fl in _flashes) fl.Draw(r, w, h);
        foreach (var tp in _textPops) tp.Draw(r);
        _waveBand.Draw(r, w, h);
        _heatShimmer.Draw(r, w, h);
        _vignette.Draw(r, w, h);
    }
}
