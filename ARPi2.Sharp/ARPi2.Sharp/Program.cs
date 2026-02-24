using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Microsoft.Xna.Framework;
using Microsoft.Xna.Framework.Graphics;
using Microsoft.Xna.Framework.Input;
using FontStashSharp;
using ARPi2.Sharp.Core;
using ARPi2.Sharp.Games;
using ARPi2.Sharp.Games.Blackjack;
using ARPi2.Sharp.Games.Catan;
using ARPi2.Sharp.Games.Cluedo;
using ARPi2.Sharp.Games.DnD;
using ARPi2.Sharp.Games.ExplodingKittens;
using ARPi2.Sharp.Games.Monopoly;
using ARPi2.Sharp.Games.Risk;
using ARPi2.Sharp.Games.TexasHoldem;
using ARPi2.Sharp.Games.UnstableUnicorns;
using ARPi2.Sharp.Games.TicketToRide;
using ARPi2.Sharp.Games.Uno;
using ARPi2.Sharp.Server;

namespace ARPi2.Sharp;

/// <summary>
/// MonoGame entry point — replaces Pyglet's window/draw loop.
/// </summary>
public class ARPi2Game : Game
{
    private readonly GraphicsDeviceManager _graphics;
    private SpriteBatch? _spriteBatch;
    private Renderer? _renderer;
    private GameServer? _server;

    // ─── State machine (mirrors Python) ────────────────────────────
    public string State { get; set; } = "menu";

    // ─── Game instances ────────────────────────────────────────────
    private readonly Dictionary<string, IGame> _games = new();
    private FontSystem? _fontSystem;

    // ─── Timing ────────────────────────────────────────────────────
    private double _elapsed;
    private int _frameCount;
    private double _fpsTimer;
    public double CurrentFPS { get; private set; }

    // ─── Frame capture for WebSocket broadcast ─────────────────────
    private RenderTarget2D? _captureTarget;

    // ─── Input ─────────────────────────────────────────────────────
    private KeyboardState _prevKb;

    public ARPi2Game()
    {
        _graphics = new GraphicsDeviceManager(this)
        {
            PreferredBackBufferWidth = GameConfig.ScreenWidth,
            PreferredBackBufferHeight = GameConfig.ScreenHeight,
            SynchronizeWithVerticalRetrace = true,   // vsync
            PreferMultiSampling = false,
            GraphicsProfile = GraphicsProfile.HiDef,
        };
        Content.RootDirectory = "Content";
        IsMouseVisible = true;
        IsFixedTimeStep = false; // unlocked update rate, let vsync handle cadence
        Window.Title = "ARPi2 Game Server — MonoGame (C#)";
    }

    protected override void Initialize()
    {
        // Try borderless fullscreen on the primary monitor
        try
        {
            _graphics.HardwareModeSwitch = false;
            _graphics.IsFullScreen = true;
            _graphics.ApplyChanges();
        }
        catch
        {
            // Fall back to windowed
            _graphics.IsFullScreen = false;
            _graphics.ApplyChanges();
        }
        base.Initialize();
    }

    protected override void LoadContent()
    {
        _spriteBatch = new SpriteBatch(GraphicsDevice);
        _renderer = new Renderer(GraphicsDevice,
            _graphics.PreferredBackBufferWidth,
            _graphics.PreferredBackBufferHeight);

        // Build FontSystem from system Arial TTF.
        _fontSystem = LoadFontSystem();
        _renderer.SetFontSystem(_fontSystem);
        _renderer.LoadEmojiTypeface();

        // Capture render-target for WebSocket frame broadcast
        _captureTarget = new RenderTarget2D(GraphicsDevice,
            _graphics.PreferredBackBufferWidth,
            _graphics.PreferredBackBufferHeight,
            false, SurfaceFormat.Color, DepthFormat.None);

        // ─── Instantiate games ────────────────────────────────
        int w = _graphics.PreferredBackBufferWidth;
        int h = _graphics.PreferredBackBufferHeight;

        RegisterGame("monopoly",          new MonopolyGameSharp(w, h, _renderer));
        RegisterGame("blackjack",         new BlackjackGameSharp(w, h, _renderer));
        RegisterGame("uno",               new UnoGameSharp(w, h, _renderer));
        RegisterGame("exploding_kittens", new ExplodingKittensGameSharp(w, h, _renderer));
        RegisterGame("texas_holdem",      new TexasHoldemGameSharp(w, h, _renderer));
        RegisterGame("unstable_unicorns", new UnstableUnicornsGameSharp(w, h, _renderer));
        RegisterGame("cluedo",            new CluedoGameSharp(w, h, _renderer));
        RegisterGame("risk",              new RiskGameSharp(w, h, _renderer));
        RegisterGame("catan",             new CatanGameSharp(w, h, _renderer));
        RegisterGame("ticket_to_ride",    new TicketToRideGameSharp(w, h, _renderer));
        RegisterGame("dnd_creation",      new DnDGameSharp(w, h, _renderer));

        // ─── Start networking ─────────────────────────────────
        _server = new GameServer(this);
        _server.Start();

        // Inject name provider so games resolve player names from the server
        foreach (var g in _games.Values)
            g.SetNameProvider(idx => _server.PlayerDisplayName(idx));
    }

    private void RegisterGame(string key, IGame game)
    {
        game.BoardOnlyMode = true;
        game.WebUIOnlyPlayerSelect = true;
        _games[key] = game;
    }

    public IGame? GetActiveGame()
    {
        if (State == "menu") return null;
        _games.TryGetValue(State, out var g);
        return g;
    }

    public IGame? GetGame(string key)
    {
        _games.TryGetValue(key, out var g);
        return g;
    }

    public IEnumerable<string> GameKeys => _games.Keys;

    protected override void Dispose(bool disposing)
    {
        if (disposing)
            _server?.Stop();
        base.Dispose(disposing);
    }

    // ───────────────────────────────────────────────────────────────
    //  Update
    // ───────────────────────────────────────────────────────────────
    protected override void Update(GameTime gameTime)
    {
        double dt = gameTime.ElapsedGameTime.TotalSeconds;
        _elapsed += dt;

        // FPS counter
        _frameCount++;
        _fpsTimer += dt;
        if (_fpsTimer >= 1.0)
        {
            CurrentFPS = _frameCount / _fpsTimer;
            _frameCount = 0;
            _fpsTimer = 0;
        }

        // ESC to quit
        var kb = Keyboard.GetState();
        if (kb.IsKeyDown(Keys.Escape) && !_prevKb.IsKeyDown(Keys.Escape))
        {
            if (State != "menu")
                State = "menu";
            else
                Exit();
        }
        _prevKb = kb;

        // Update active game
        var game = GetActiveGame();
        game?.Update(dt);

        // Tick the server (WebSocket polling, audio, etc.)
        _server?.Update(dt);

        base.Update(gameTime);
    }

    // ───────────────────────────────────────────────────────────────
    //  Draw
    // ───────────────────────────────────────────────────────────────
    protected override void Draw(GameTime gameTime)
    {
        double dt = gameTime.ElapsedGameTime.TotalSeconds;
        int w = _graphics.PreferredBackBufferWidth;
        int h = _graphics.PreferredBackBufferHeight;

        // Draw to the capture render-target so we can broadcast frames
        GraphicsDevice.SetRenderTarget(_captureTarget);
        GraphicsDevice.Clear(Color.Black);

        _renderer!.BeginFrame();

        if (State == "menu")
            DrawMenu(w, h);
        else
        {
            var game = GetActiveGame();
            if (game != null)
                game.Draw(_renderer!, w, h, dt);
            else
                _renderer!.DrawRect(GameConfig.Colors.DarkBg, (0, 0, w, h));
        }

        // Draw web cursors on top of everything
        DrawCursors(_renderer!, w, h);

        _renderer!.EndFrame();

        // Blit to screen
        GraphicsDevice.SetRenderTarget(null);
        _spriteBatch!.Begin(SpriteSortMode.Immediate, BlendState.Opaque);
        _spriteBatch.Draw(_captureTarget!, GraphicsDevice.Viewport.Bounds, Color.White);
        _spriteBatch.End();

        // Notify server of a new frame available for broadcast
        _server?.OnFrameReady(_captureTarget!);

        base.Draw(gameTime);
    }

    // ───────────────────────────────────────────────────────────────
    //  Cursor overlay (web UI pointers drawn on top of game)
    // ───────────────────────────────────────────────────────────────
    private void DrawCursors(Renderer r, int w, int h)
    {
        var cursors = _server?.GetCursors();
        if (cursors == null || cursors.Count == 0) return;
        foreach (var (seat, cx, cy) in cursors)
        {
            var col = GameConfig.PlayerColors[seat % GameConfig.PlayerColors.Length];
            // Outer glow
            r.DrawCircle(col, (cx, cy), 14, alpha: 60);
            // Solid dot
            r.DrawCircle(col, (cx, cy), 7);
            // Border
            r.DrawCircle((255, 255, 255), (cx, cy), 7, width: 2, alpha: 200);
        }
    }

    // ───────────────────────────────────────────────────────────────
    //  Menu drawing
    // ───────────────────────────────────────────────────────────────
    private void DrawMenu(int w, int h)
    {
        var r = _renderer!;
        r.DrawRect(GameConfig.Colors.DarkBg, (-4, -4, w + 8, h + 8));
        // Accent washes
        r.DrawRect(GameConfig.Colors.Accent, (-4, -4, w + 8, h * 22 / 100 + 8), alpha: 10);
        r.DrawRect(GameConfig.Colors.White, (-4, h * 78 / 100, w + 8, h * 22 / 100 + 8), alpha: 5);
        r.DrawCircle(GameConfig.Colors.Accent, (w * 18 / 100, h * 30 / 100), Math.Min(w, h) * 24 / 100, alpha: 8);
        r.DrawCircle(GameConfig.Colors.Accent, (w * 84 / 100, h * 70 / 100), Math.Min(w, h) * 30 / 100, alpha: 6);

        int cx = w / 2;
        int titleY = h * 14 / 100;
        r.DrawText("ARPi2 Game Launcher", cx, titleY, 64, GameConfig.Colors.White, anchorX: "center", anchorY: "center");
        r.DrawText("Scan the QR code or use the Web UI to join", cx, titleY + 56, 24, (200, 200, 200), anchorX: "center", anchorY: "center");

        // ── Left side: QR code panel ──
        int contentTop = h * 32 / 100;
        int qrSize = Math.Clamp(Math.Min(w, h) * 24 / 100, 140, 260);
        int qrX = w * 30 / 100;
        int qrY = contentTop + qrSize / 2 + 30;
        QRCodeRenderer.DrawQRPanel(r, qrX, qrY, qrSize,
            title: "📱 SCAN TO JOIN",
            accentColor: (100, 180, 255));

        // ── Right side: Lobby + player list ──
        int rightCx = w * 70 / 100;
        int lobbyY = contentTop;
        r.DrawText("Lobby", rightCx, lobbyY, 26, GameConfig.Colors.White, anchorX: "center", anchorY: "center", bold: true);

        // Divider line
        int divW = w * 24 / 100;
        r.DrawRect((120, 120, 140), (rightCx - divW / 2, lobbyY + 20, divW, 2), alpha: 80);

        // Player list
        var players = _server?.GetLobbyPlayers() ?? new List<LobbyPlayer>();
        int startY = lobbyY + 48;
        for (int i = 0; i < Math.Min(players.Count, 8); i++)
        {
            var p = players[i];
            if (p.Seat < 0 || p.Seat > 7) continue;
            var col = GameConfig.PlayerColors[p.Seat % GameConfig.PlayerColors.Length];
            string label = $"{p.Name}  ({(p.Ready ? "Ready" : "Not ready")})";
            int y = startY + i * 30;
            r.DrawCircle(col, (rightCx - 160, y), 8);
            r.DrawCircle(GameConfig.Colors.White, (rightCx - 160, y), 8, width: 2);
            r.DrawText(label, rightCx, y, 18, col, anchorX: "center", anchorY: "center");
        }

        if (players.Count == 0)
            r.DrawText("Waiting for players to join…", rightCx, startY + 20, 20, (200, 200, 200), anchorX: "center", anchorY: "center");
    }

    // ───────────────────────────────────────────────────────────────
    //  Font loading (uses FontStashSharp to load system TTF at runtime)
    // ───────────────────────────────────────────────────────────────
    private FontSystem LoadFontSystem()
    {
        var fontSystem = new FontSystem(new FontSystemSettings { PremultiplyAlpha = false });

        // Try common system font paths (prefer Arial to match Python version)
        string[] candidates =
        {
            @"C:\Windows\Fonts\arial.ttf",
            @"C:\Windows\Fonts\segoeui.ttf",
            @"C:\Windows\Fonts\calibri.ttf",
            @"C:\Windows\Fonts\tahoma.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",    // Linux
            "/usr/share/fonts/TTF/DejaVuSans.ttf",                 // Arch
            "/System/Library/Fonts/Helvetica.ttc",                  // macOS
        };

        bool loaded = false;
        foreach (var path in candidates)
        {
            if (File.Exists(path))
            {
                fontSystem.AddFont(File.ReadAllBytes(path));
                System.Diagnostics.Debug.WriteLine($"[Font] Loaded: {path}");
                loaded = true;
                break;
            }
        }

        if (!loaded)
        {
            System.Diagnostics.Debug.WriteLine("[Font] WARNING: No system font found!");
            throw new FileNotFoundException(
                "Could not find a system TrueType font (arial.ttf, segoeui.ttf, etc.). " +
                "Place a .ttf file in the application directory or install Windows fonts.");
        }

        // Add emoji fallback font so emoji glyphs render instead of boxes
        string[] emojiFonts =
        {
            @"C:\Windows\Fonts\seguiemj.ttf",                           // Windows 10/11 Segoe UI Emoji
            "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",         // Ubuntu/Debian
            "/usr/share/fonts/noto/NotoColorEmoji.ttf",                  // Fedora
            "/usr/share/fonts/google-noto-emoji/NotoColorEmoji.ttf",     // CentOS/RHEL
            "/System/Library/Fonts/Apple Color Emoji.ttc",               // macOS
        };
        foreach (var path in emojiFonts)
        {
            if (File.Exists(path))
            {
                try
                {
                    fontSystem.AddFont(File.ReadAllBytes(path));
                    System.Diagnostics.Debug.WriteLine($"[Font] Emoji fallback loaded: {path}");
                }
                catch (Exception ex)
                {
                    System.Diagnostics.Debug.WriteLine($"[Font] Emoji fallback failed ({path}): {ex.Message}");
                }
                break;
            }
        }

        // Also try Segoe UI Symbol as secondary fallback (has many symbols/emoji outlines)
        string symbolFont = @"C:\Windows\Fonts\seguisym.ttf";
        if (File.Exists(symbolFont))
        {
            try
            {
                fontSystem.AddFont(File.ReadAllBytes(symbolFont));
                System.Diagnostics.Debug.WriteLine($"[Font] Symbol fallback loaded: {symbolFont}");
            }
            catch { /* non-critical */ }
        }

        return fontSystem;
    }
}

// ───────────────────────────────────────────────────────────────────────
//  Entry point
// ───────────────────────────────────────────────────────────────────────
public static class Program
{
    [STAThread]
    public static void Main()
    {
        using var game = new ARPi2Game();
        game.Run();
    }
}
