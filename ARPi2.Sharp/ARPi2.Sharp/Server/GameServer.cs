using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Net.WebSockets;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Xna.Framework;
using Microsoft.Xna.Framework.Graphics;
using ARPi2.Sharp.Core;
using ARPi2.Sharp.Games;
using ARPi2.Sharp.Games.DnD;

namespace ARPi2.Sharp.Server;

/// <summary>Lobby player snapshot for menu rendering.</summary>
public class LobbyPlayer
{
    public string ClientId { get; set; } = "";
    public int Seat { get; set; } = -1;
    public string Name { get; set; } = "";
    public bool Ready { get; set; }
    public string? Vote { get; set; }
    public bool Connected { get; set; } = true;
}

/// <summary>
/// Networking layer — WebSocket server (frame stream + UI JSON) and HTTP static-file server.
/// Speaks the exact same protocol as the Python PygletGameServer so the existing web UI
/// connects without modification.
/// </summary>
public class GameServer
{
    private readonly ARPi2Game _app;

    // ─── Audio ─────────────────────────────────────────────────────
    private readonly AudioManager _audio = new();
    private string? _prevAudioState;
    private readonly Dictionary<string, int> _prevDeckCounts = new();

    // ─── WebSocket clients ─────────────────────────────────────────
    private readonly ConcurrentDictionary<string, WebSocket> _frameClients = new();
    private readonly ConcurrentDictionary<string, WebSocket> _uiClients    = new();
    private readonly ConcurrentDictionary<string, int>    _uiClientSeat    = new();
    private readonly ConcurrentDictionary<string, string> _uiClientName    = new();
    private readonly ConcurrentDictionary<string, bool>   _uiClientReady   = new();
    private readonly ConcurrentDictionary<string, string> _uiClientVote    = new();
    private readonly ConcurrentDictionary<string, bool>   _uiClientEndGame = new();
    public readonly ConcurrentDictionary<int, string>    PlayerNames       = new();

    // ─── Web cursor tracking (pointer / tap from Web UI) ───────
    private readonly ConcurrentDictionary<int, WebCursor> _webCursors = new();
    private struct WebCursor
    {
        public int X;      // pixels on game screen
        public int Y;
        public bool Click; // true on tap / click frame
        public double Time; // _elapsed when updated
    }

    // ─── History log ───────────────────────────────────────────────
    private readonly List<string> _history = new();
    private readonly object _historyLock = new();

    // ─── Game menu buttons (matches Python _create_game_buttons) ──
    private static readonly List<Dictionary<string, string>> GameButtonsList = new()
    {
        new() { ["key"] = "monopoly",          ["label"] = "Monopoly" },
        new() { ["key"] = "blackjack",         ["label"] = "Blackjack" },
        new() { ["key"] = "uno",               ["label"] = "UNO" },
        new() { ["key"] = "exploding_kittens", ["label"] = "Exploding Kittens" },
        new() { ["key"] = "texas_holdem",      ["label"] = "Texas Hold'em" },
        new() { ["key"] = "unstable_unicorns", ["label"] = "Unstable Unicorns" },
        new() { ["key"] = "cluedo",            ["label"] = "Cluedo" },
        new() { ["key"] = "risk",              ["label"] = "Risk" },
        new() { ["key"] = "catan",             ["label"] = "Catan" },
        new() { ["key"] = "ticket_to_ride",    ["label"] = "Ticket to Ride" },
        new() { ["key"] = "d&d",               ["label"] = "D&D" },
    };

    // Python palette hex colours sent in every snapshot
    private static readonly List<string> PaletteColors = new()
    {
        "#ff4d4d", "#4d79ff", "#4dff88", "#ffd24d",
        "#b84dff", "#4dfff0", "#ff4dd2", "#c7ff4d",
    };

    // ─── HTTP ──────────────────────────────────────────────────────
    private HttpListener? _httpListener;
    private HttpListener? _wsListener;
    private readonly CancellationTokenSource _cts = new();

    // ─── Frame broadcast ───────────────────────────────────────────
    private double _broadcastTimer;
    private const double BroadcastInterval = 1.0 / 60.0;

    // ─── Connect info cache ────────────────────────────────────────
    private string[]? _connectLinesCache;
    private double _connectCacheAge;

    // ─── Vite dev server process ───────────────────────────────────
    private Process? _npmProcess;

    public GameServer(ARPi2Game app) => _app = app;

    // ═══════════════════════════════════════════════════════════════
    //  Start servers on background threads
    // ═══════════════════════════════════════════════════════════════
    public void Start()
    {
        Task.Run(() => RunHttpServer(_cts.Token));
        Task.Run(() => RunWebSocketServer(_cts.Token));
        Task.Run(() => UIBroadcastLoop(_cts.Token));
        StartViteDevServer();

        Console.WriteLine($"Web UI:  http://0.0.0.0:{GameConfig.HttpPort}");
        Console.WriteLine($"WS:     ws://0.0.0.0:{GameConfig.ServerPort}");
    }

    // ═══════════════════════════════════════════════════════════════
    //  Vite dev server (npm run dev) for Web UI
    // ═══════════════════════════════════════════════════════════════
    private void StartViteDevServer()
    {
        try
        {
            string? webUiDir = FindWebUiDirectory();
            if (webUiDir == null)
            {
                Console.WriteLine("Vite: web_ui directory not found — skipping npm dev server.");
                return;
            }

            // Check that node_modules exists; if not, skip (user needs to npm install first)
            if (!Directory.Exists(Path.Combine(webUiDir, "node_modules")))
            {
                Console.WriteLine($"Vite: node_modules not found in {webUiDir} — run 'npm install' first.");
                return;
            }

            _npmProcess = new Process
            {
                StartInfo = new ProcessStartInfo
                {
                    FileName = "cmd.exe",
                    Arguments = "/c npm run dev -- --host",
                    WorkingDirectory = webUiDir,
                    UseShellExecute = false,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    CreateNoWindow = true,
                },
                EnableRaisingEvents = true,
            };

            _npmProcess.OutputDataReceived += (_, e) =>
            {
                if (!string.IsNullOrEmpty(e.Data))
                    Console.WriteLine($"[Vite] {e.Data}");
            };
            _npmProcess.ErrorDataReceived += (_, e) =>
            {
                if (!string.IsNullOrEmpty(e.Data))
                    Console.WriteLine($"[Vite] {e.Data}");
            };

            _npmProcess.Start();
            _npmProcess.BeginOutputReadLine();
            _npmProcess.BeginErrorReadLine();

            Console.WriteLine($"Vite dev server started (PID {_npmProcess.Id}) from {webUiDir}");
            Console.WriteLine("Web UI (dev): http://localhost:5173");
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Vite: Failed to start npm dev server: {ex.Message}");
        }
    }

    private string? FindWebUiDirectory()
    {
        string baseDir = AppDomain.CurrentDomain.BaseDirectory;
        var dir = new DirectoryInfo(baseDir);
        while (dir != null)
        {
            string candidate = Path.Combine(dir.FullName, "web_ui");
            if (Directory.Exists(candidate) && File.Exists(Path.Combine(candidate, "package.json")))
                return candidate;
            dir = dir.Parent;
        }
        return null;
    }

    /// <summary>
    /// Create and start an HttpListener on all interfaces (http://+:port/).
    /// If that fails (needs admin/URL ACL on Windows), fall back to http://localhost:port/.
    /// </summary>
    private static HttpListener CreateAndStartListener(int port, string label)
    {
        // Attempt 1: listen on all interfaces (requires admin or URL ACL)
        string allPrefix = $"http://+:{port}/";
        try
        {
            var listener = new HttpListener();
            listener.Prefixes.Add(allPrefix);
            listener.Start();
            Console.WriteLine($"{label} listening on {allPrefix}");
            return listener;
        }
        catch (HttpListenerException)
        {
            Console.WriteLine($"{label}: Cannot bind {allPrefix} (no admin rights).");
        }

        // Attempt 2: try to auto-register URL ACL via elevated netsh
        try
        {
            var psi = new ProcessStartInfo
            {
                FileName = "netsh",
                Arguments = $"http add urlacl url=http://+:{port}/ user=Everyone",
                Verb = "runas",
                UseShellExecute = true,
                CreateNoWindow = true,
                WindowStyle = ProcessWindowStyle.Hidden,
            };
            var proc = Process.Start(psi);
            if (proc != null && proc.WaitForExit(15_000) && proc.ExitCode == 0)
            {
                var listener = new HttpListener();
                listener.Prefixes.Add(allPrefix);
                listener.Start();
                Console.WriteLine($"{label} listening on {allPrefix} (URL ACL registered)");
                return listener;
            }
        }
        catch
        {
            Console.WriteLine($"{label}: URL ACL registration was declined or failed.");
        }

        // Attempt 3: localhost only (always works without admin)
        string localPrefix = $"http://localhost:{port}/";
        Console.WriteLine($"{label}: Falling back to {localPrefix} (localhost only).");
        Console.WriteLine($"{label}: To allow network access, run once as Administrator or execute:");
        Console.WriteLine($"  netsh http add urlacl url=http://+:{port}/ user=Everyone");
        var fallback = new HttpListener();
        fallback.Prefixes.Add(localPrefix);
        fallback.Start();
        Console.WriteLine($"{label} listening on {localPrefix}");
        return fallback;
    }

    //  HTTP static file server
    // ═══════════════════════════════════════════════════════════════
    private async Task RunHttpServer(CancellationToken ct)
    {
        try
        {
            _httpListener = CreateAndStartListener(GameConfig.HttpPort, "HTTP");
            string webRoot = FindWebRoot();
            Console.WriteLine($"HTTP serving: {webRoot}");
            while (!ct.IsCancellationRequested)
            {
                var ctx = await _httpListener.GetContextAsync();
                _ = Task.Run(() => HandleHttpRequest(ctx, webRoot));
            }
        }
        catch (Exception ex) { Console.WriteLine($"HTTP server error: {ex.Message}"); }
    }

    private string FindWebRoot()
    {
        string baseDir = AppDomain.CurrentDomain.BaseDirectory;
        var dir = new DirectoryInfo(baseDir);
        while (dir != null)
        {
            string distPath = Path.Combine(dir.FullName, "web_ui", "dist");
            if (Directory.Exists(distPath) && File.Exists(Path.Combine(distPath, "index.html")))
                return distPath;
            string rawPath = Path.Combine(dir.FullName, "web_ui");
            if (Directory.Exists(rawPath) && File.Exists(Path.Combine(rawPath, "index.html")))
                return rawPath;
            dir = dir.Parent;
        }
        return Path.Combine(baseDir, "web_ui");
    }

    private async Task HandleHttpRequest(HttpListenerContext ctx, string webRoot)
    {
        try
        {
            string reqPath = ctx.Request.Url?.AbsolutePath ?? "/";
            if (reqPath == "/") reqPath = "/index.html";
            string filePath = Path.Combine(webRoot, reqPath.TrimStart('/').Replace('/', Path.DirectorySeparatorChar));
            filePath = Path.GetFullPath(filePath);
            if (!filePath.StartsWith(webRoot, StringComparison.OrdinalIgnoreCase) || !File.Exists(filePath))
            {
                ctx.Response.StatusCode = 404;
                ctx.Response.Close();
                return;
            }
            string ext = Path.GetExtension(filePath).ToLowerInvariant();
            ctx.Response.ContentType = ext switch
            {
                ".html" => "text/html", ".js" => "application/javascript", ".css" => "text/css",
                ".json" => "application/json", ".png" => "image/png",
                ".jpg" or ".jpeg" => "image/jpeg", ".svg" => "image/svg+xml",
                ".woff" or ".woff2" => "font/woff2", _ => "application/octet-stream"
            };
            byte[] data = await File.ReadAllBytesAsync(filePath);
            ctx.Response.ContentLength64 = data.Length;
            await ctx.Response.OutputStream.WriteAsync(data);
            ctx.Response.Close();
        }
        catch { ctx.Response.Abort(); }
    }

    // ═══════════════════════════════════════════════════════════════
    //  WebSocket server
    // ═══════════════════════════════════════════════════════════════
    private async Task RunWebSocketServer(CancellationToken ct)
    {
        try
        {
            _wsListener = CreateAndStartListener(GameConfig.ServerPort, "WebSocket");
            while (!ct.IsCancellationRequested)
            {
                var ctx = await _wsListener.GetContextAsync();
                if (ctx.Request.IsWebSocketRequest)
                {
                    var wsCtx = await ctx.AcceptWebSocketAsync(null);
                    string path = ctx.Request.Url?.AbsolutePath ?? "/";
                    string clientId = $"{ctx.Request.RemoteEndPoint}";
                    if (path == "/ui")
                        _ = Task.Run(() => HandleUIClient(clientId, wsCtx.WebSocket, ct));
                    else
                        _ = Task.Run(() => HandleFrameClient(clientId, wsCtx.WebSocket, ct));
                }
                else
                {
                    ctx.Response.StatusCode = 400;
                    ctx.Response.Close();
                }
            }
        }
        catch (Exception ex) { Console.WriteLine($"WebSocket server error: {ex.Message}"); }
    }

    private async Task HandleFrameClient(string id, WebSocket ws, CancellationToken ct)
    {
        _frameClients[id] = ws;
        Console.WriteLine($"Frame client connected: {id}");
        try
        {
            var buf = new byte[1024];
            while (ws.State == WebSocketState.Open && !ct.IsCancellationRequested)
            {
                var result = await ws.ReceiveAsync(buf, ct);
                if (result.MessageType == WebSocketMessageType.Close) break;
            }
        }
        catch { }
        finally { _frameClients.TryRemove(id, out _); }
    }

    private async Task HandleUIClient(string id, WebSocket ws, CancellationToken ct)
    {
        _uiClients[id] = ws;
        _uiClientSeat[id] = -1;
        _uiClientReady[id] = false;
        _uiClientEndGame[id] = false;
        Console.WriteLine($"UI client connected: {id}");
        try
        {
            var buf = new byte[16384];
            while (ws.State == WebSocketState.Open && !ct.IsCancellationRequested)
            {
                var result = await ws.ReceiveAsync(buf, ct);
                if (result.MessageType == WebSocketMessageType.Close) break;
                if (result.MessageType != WebSocketMessageType.Text) continue;
                string json = Encoding.UTF8.GetString(buf, 0, result.Count);
                ProcessUIMessage(id, json);
            }
        }
        catch { }
        finally
        {
            _uiClients.TryRemove(id, out _);
            _uiClientSeat.TryRemove(id, out _);
            _uiClientName.TryRemove(id, out _);
            _uiClientReady.TryRemove(id, out _);
            _uiClientVote.TryRemove(id, out _);
            _uiClientEndGame.TryRemove(id, out _);
            _audio.RemoveVoter(id);
            Console.WriteLine($"UI client disconnected: {id}");
        }
    }

    // ═══════════════════════════════════════════════════════════════
    //  UI message processing (matches Python _apply_ui_action)
    // ═══════════════════════════════════════════════════════════════
    private void ProcessUIMessage(string clientId, string json)
    {
        try
        {
            using var doc = JsonDocument.Parse(json);
            var root = doc.RootElement;
            string type = root.GetProperty("type").GetString() ?? "";

            switch (type)
            {
                case "hello":                HandleHello(clientId, root); break;
                case "set_seat":             HandleSetSeat(clientId, root); break;
                case "set_ready":            HandleSetReady(clientId, root); break;
                case "vote_game":            HandleVoteGame(clientId, root); break;
                case "click_button":         HandleClickButton(clientId, root); break;
                case "start_game":           HandleStartGame(); break;
                case "set_player_selected":  HandleSetPlayerSelected(root); break;
                case "end_game":             HandleEndGame(clientId, root); break;
                case "quit":                 HandleQuit(clientId); break;
                case "vote_music_mute":
                    // Toggle: if already voted mute, un-vote; otherwise vote mute
                    bool currentlyVoted = _audio.HasVotedMute(clientId);
                    _audio.SetMuteVote(clientId, !currentlyVoted);
                    break;
                case "set_volume":
                    if (root.TryGetProperty("volume", out var volProp))
                    {
                        // UI sends 0-100, server stores 0.0-1.0
                        float vol = (float)(volProp.GetDouble() / 100.0);
                        _audio.SetClientVolume(clientId, vol);
                    }
                    break;
                case "pointer": case "tap":  HandlePointerOrTap(clientId, type, root); break;
                case "esc": case "back":     break; // Escape request

                // Game-specific passthrough
                default:
                    HandleGameSpecific(clientId, type, root, json);
                    break;
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine($"UI message error: {ex.Message}");
        }
    }

    private void HandleHello(string clientId, JsonElement root)
    {
        string name = "";
        if (root.TryGetProperty("name", out var np))
            name = (np.GetString() ?? "").Trim();
        if (name.Length > 24) name = name[..24];
        if (!string.IsNullOrEmpty(name))
            _uiClientName[clientId] = name;

        if (root.TryGetProperty("player_idx", out var pidxProp))
        {
            try
            {
                int desired = pidxProp.GetInt32();
                if (desired >= 0 && desired <= 7 && TrySetSeat(clientId, desired))
                {
                    if (!string.IsNullOrEmpty(name)) PlayerNames[desired] = name;
                    _uiClientEndGame[clientId] = false;
                    return;
                }
            }
            catch { }
        }

        // Reconnect-by-name: if a seat's previous occupant had the same name
        // and that seat is no longer held by a connected client, reclaim it.
        if (!string.IsNullOrEmpty(name))
        {
            foreach (var (seat, prevName) in PlayerNames)
            {
                if (!string.Equals(prevName, name, StringComparison.OrdinalIgnoreCase)) continue;
                // Verify no connected client currently holds this seat
                bool occupied = false;
                foreach (var (cid, s) in _uiClientSeat)
                {
                    if (s == seat && _uiClients.ContainsKey(cid))
                    { occupied = true; break; }
                }
                if (!occupied && TrySetSeat(clientId, seat))
                {
                    PlayerNames[seat] = name;
                    _uiClientEndGame[clientId] = false;
                    Console.WriteLine($"Reconnect: '{name}' reclaimed seat {seat}");
                    return;
                }
            }
        }

        TryAutoAssignSeat(clientId);
        int assignedSeat = _uiClientSeat.GetValueOrDefault(clientId, -1);
        if (assignedSeat >= 0 && !string.IsNullOrEmpty(name))
            PlayerNames[assignedSeat] = name;
        _uiClientEndGame[clientId] = false;
    }

    private void HandleSetSeat(string clientId, JsonElement root)
    {
        int desired = root.GetProperty("player_idx").GetInt32();
        if (TrySetSeat(clientId, desired))
        {
            string name = "";
            if (root.TryGetProperty("name", out var np))
                name = (np.GetString() ?? "").Trim();
            if (string.IsNullOrEmpty(name))
                name = _uiClientName.GetValueOrDefault(clientId, "");
            if (!string.IsNullOrEmpty(name))
                PlayerNames[desired] = name;
        }
    }

    private void HandleSetReady(string clientId, JsonElement root)
    {
        bool ready = root.TryGetProperty("ready", out var rp) && rp.GetBoolean();
        _uiClientReady[clientId] = ready;
    }

    private void HandleVoteGame(string clientId, JsonElement root)
    {
        if (_app.State != "menu") return;
        if (!LobbyAllReady()) return;

        string key = (root.GetProperty("key").GetString() ?? "").Trim();
        if (key == "dnd") key = "d&d";

        int seat = _uiClientSeat.GetValueOrDefault(clientId, -1);
        if (seat < 0) return;
        if (!_uiClientReady.GetValueOrDefault(clientId, false)) return;

        if (!GameButtonsList.Any(b => b["key"] == key)) return;

        _uiClientVote[clientId] = key;
        MaybeApplyVote();
    }

    private void HandleClickButton(string clientId, JsonElement root)
    {
        string btnId = root.GetProperty("id").GetString() ?? "";
        int seat = _uiClientSeat.GetValueOrDefault(clientId, -1);
        if (seat < 0) return;
        var game = _app.GetActiveGame();
        if (game == null) return;

        // Special: return to lobby (any game)
        if (btnId == "return_to_lobby")
        {
            _app.State = "menu";
            ResetLobby();
            LogHistory($"Returned to lobby from seat {seat}");
            return;
        }

        // Play SFX based on button action
        PlayButtonSfx(btnId, _app.State);

        game.HandleClick(seat, btnId);
    }

    private void HandleStartGame()
    {
        var game = _app.GetActiveGame();
        if (game == null || game.State != "player_select") return;

        var sel = game.SelectionUI.GetSelectedIndices();
        string state = _app.State;

        bool valid = state switch
        {
            "blackjack" => sel.Count >= 1,
            "cluedo" => sel.Count >= 3 && sel.Count <= 6,
            "catan" => sel.Count >= 2 && sel.Count <= 8,
            _ => sel.Count >= 2,
        };

        if (!valid) return;
        game.StartGame(sel);
        LogHistory($"Game started: {state} with {sel.Count} players");
    }

    private void HandleSetPlayerSelected(JsonElement root)
    {
        var game = _app.GetActiveGame();
        if (game == null || game.State != "player_select") return;

        int pidx = root.GetProperty("player_idx").GetInt32();
        bool selected = root.GetProperty("selected").GetBoolean();
        if (pidx >= 0 && pidx < game.SelectionUI.Selected.Length)
            game.SelectionUI.Selected[pidx] = selected;
    }

    private void HandleEndGame(string clientId, JsonElement root)
    {
        if (_app.State == "menu") return;
        int seat = _uiClientSeat.GetValueOrDefault(clientId, -1);
        if (seat < 0) return;
        bool pressed = !root.TryGetProperty("pressed", out var pp) || pp.GetBoolean();
        _uiClientEndGame[clientId] = pressed;
        MaybeEndGame();
    }

    private void HandleQuit(string clientId)
    {
        int seat = _uiClientSeat.GetValueOrDefault(clientId, -1);
        _uiClientSeat[clientId] = -1;
        _uiClientReady[clientId] = false;
        _uiClientVote.TryRemove(clientId, out _);
        _uiClientEndGame[clientId] = false;
        if (seat >= 0) LogHistory($"{PlayerDisplayName(seat)} quit");
        SyncPlayerSelectFromSeats();
    }

    private void HandleGameSpecific(string clientId, string type, JsonElement root, string rawJson)
    {
        int seat = _uiClientSeat.GetValueOrDefault(clientId, -1);
        if (seat < 0) return;
        var game = _app.GetActiveGame();
        if (game == null) return;

        try
        {
            game.HandleMessage(seat, type, rawJson);
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Game-specific handler error ({type}): {ex.Message}");
        }
    }

    private void LogHistory(string msg)
    {
        lock (_historyLock)
        {
            _history.Add(msg);
            if (_history.Count > 200) _history.RemoveAt(0);
        }
    }

    // ═══════════════════════════════════════════════════════════════
    //  Pointer / tap (web cursor relay)
    // ═══════════════════════════════════════════════════════════════
    private void HandlePointerOrTap(string clientId, string type, JsonElement root)
    {
        int seat = _uiClientSeat.GetValueOrDefault(clientId, -1);
        if (seat < 0) return;

        double x = 0, y = 0;
        try
        {
            if (root.TryGetProperty("x", out var xp)) x = xp.GetDouble();
            if (root.TryGetProperty("y", out var yp)) y = yp.GetDouble();
        }
        catch { return; }

        // Web UI sends normalised 0..1 coords (top-left origin)
        x = Math.Clamp(x, 0.0, 1.0);
        y = Math.Clamp(y, 0.0, 1.0);
        int px = (int)(x * GameConfig.ScreenWidth);
        int py = (int)(y * GameConfig.ScreenHeight);

        bool click = false;
        if (type == "tap") click = true;
        else if (root.TryGetProperty("click", out var cp))
        {
            try { click = cp.GetBoolean(); } catch { }
        }

        _webCursors[seat] = new WebCursor { X = px, Y = py, Click = click, Time = _elapsed };
    }

    /// <summary>Dispatch pending cursor clicks to the active game each frame.</summary>
    private void DispatchCursorClicks()
    {
        // Expire stale cursors (>10s)
        foreach (var (seat, cur) in _webCursors)
        {
            if (_elapsed - cur.Time > 10.0)
                _webCursors.TryRemove(seat, out _);
        }

        var game = _app.GetActiveGame();
        if (game == null) return;

        foreach (var (seat, cur) in _webCursors)
        {
            if (!cur.Click) continue;
            try
            {
                game.HandleMessage(seat, "catan_pointer_click", $"{{\"x\":{cur.X},\"y\":{cur.Y}}}");
            }
            catch { }
            // Consume the click
            _webCursors[seat] = new WebCursor { X = cur.X, Y = cur.Y, Click = false, Time = cur.Time };
        }
    }

    /// <summary>Get cursor data for on-screen rendering.</summary>
    public List<(int seat, int x, int y)> GetCursors()
    {
        var result = new List<(int, int, int)>();
        foreach (var (seat, cur) in _webCursors)
        {
            if (_elapsed - cur.Time < 10.0)
                result.Add((seat, cur.X, cur.Y));
        }
        return result;
    }

    // ═══════════════════════════════════════════════════════════════
    //  Seat management
    // ═══════════════════════════════════════════════════════════════
    private bool TryAutoAssignSeat(string clientId)
    {
        var available = GetAvailableSlots();
        return available.Count > 0 && TrySetSeat(clientId, available[0]);
    }

    private bool TrySetSeat(string clientId, int slot)
    {
        if (slot < 0 || slot > 7) return false;
        foreach (var (cid, s) in _uiClientSeat)
        {
            if (cid == clientId) continue;
            if (s == slot) return false;
        }
        _uiClientSeat[clientId] = slot;
        string name = _uiClientName.GetValueOrDefault(clientId, $"Player {slot + 1}");
        PlayerNames[slot] = name;
        return true;
    }

    private List<int> GetTakenSlots()
    {
        var taken = new HashSet<int>();
        foreach (var (cid, s) in _uiClientSeat)
            if (s >= 0 && s <= 7 && _uiClients.ContainsKey(cid))
                taken.Add(s);
        return taken.OrderBy(x => x).ToList();
    }

    private List<int> GetAvailableSlots()
    {
        var taken = new HashSet<int>(GetTakenSlots());
        return Enumerable.Range(0, 8).Where(i => !taken.Contains(i)).ToList();
    }

    private void SyncPlayerSelectFromSeats()
    {
        var game = _app.GetActiveGame();
        if (game == null || game.State != "player_select") return;
        Array.Fill(game.SelectionUI.Selected, false);
        foreach (var (cid, seat) in _uiClientSeat)
            if (seat >= 0 && seat < game.SelectionUI.Selected.Length && _uiClients.ContainsKey(cid))
                game.SelectionUI.Selected[seat] = true;
    }

    // ═══════════════════════════════════════════════════════════════
    //  Vote / game selection
    // ═══════════════════════════════════════════════════════════════
    private bool LobbyAllReady()
    {
        var seated = _uiClientSeat
            .Where(kv => kv.Value >= 0 && _uiClients.ContainsKey(kv.Key))
            .Select(kv => kv.Key).ToList();
        if (seated.Count < GameConfig.MinPlayers) return false;
        return seated.All(cid => _uiClientReady.GetValueOrDefault(cid, false));
    }

    private void MaybeApplyVote()
    {
        if (_app.State != "menu" || !LobbyAllReady()) return;

        var seated = _uiClientSeat
            .Where(kv => kv.Value >= 0 && _uiClients.ContainsKey(kv.Key))
            .Select(kv => kv.Key).ToList();

        var counts = new Dictionary<string, int>();
        int voters = 0;
        foreach (var cid in seated)
        {
            if (!_uiClientReady.GetValueOrDefault(cid, false)) continue;
            voters++;
            if (_uiClientVote.TryGetValue(cid, out var v) && !string.IsNullOrEmpty(v))
                counts[v] = counts.GetValueOrDefault(v, 0) + 1;
        }
        if (voters <= 0) return;

        foreach (var (key, n) in counts)
        {
            if (n > voters / 2.0)
            {
                ApplyGameSelection(key);
                _uiClientVote.Clear();
                break;
            }
        }
    }

    private void ApplyGameSelection(string key)
    {
        string gameKey = key switch { "d&d" => "dnd_creation", _ => key };

        var game = _app.GetGame(gameKey);
        if (game == null) return;

        _app.State = gameKey;
        game.State = "player_select";
        game.SelectionUI.Reset();
        _uiClientVote.Clear();
        SyncPlayerSelectFromSeats();
        LogHistory($"Game selected: {key}");
    }

    private void MaybeEndGame()
    {
        if (_app.State == "menu") return;
        var required = _uiClientSeat
            .Where(kv => kv.Value >= 0 && _uiClients.ContainsKey(kv.Key))
            .Select(kv => kv.Key).ToList();
        if (required.Count == 0) return;
        if (required.All(cid => _uiClientEndGame.GetValueOrDefault(cid, false)))
        {
            _app.State = "menu";
            ResetLobby();
            LogHistory("Game ended by vote");
        }
    }

    private void ResetLobby()
    {
        foreach (var cid in _uiClientReady.Keys.ToList()) _uiClientReady[cid] = false;
        _uiClientVote.Clear();
        foreach (var cid in _uiClientEndGame.Keys.ToList()) _uiClientEndGame[cid] = false;
    }

    // ═══════════════════════════════════════════════════════════════
    //  Snapshot building (per-player, matches Python get_ui_snapshot)
    // ═══════════════════════════════════════════════════════════════
    private Dictionary<string, object?> BuildSnapshot(string clientId)
    {
        int playerIdx = _uiClientSeat.GetValueOrDefault(clientId, -1);

        List<string> historyCopy;
        lock (_historyLock) { historyCopy = new List<string>(_history); }

        var snap = new Dictionary<string, object?>
        {
            ["server_state"] = _app.State,
            ["history"] = historyCopy,
            ["audio"] = new Dictionary<string, object?>
            {
                ["music_muted"] = _audio.IsMuted,
                ["mute_votes"] = _audio.MuteVotes,
                ["mute_required"] = _audio.MuteRequired,
                ["you_voted_mute"] = _audio.HasVotedMute(clientId),
                ["volume"] = (int)(_audio.GetClientVolume(clientId) * 100),
            },
            ["palette"] = new Dictionary<string, object?>
            {
                ["player_colors"] = PaletteColors,
            },
            ["available_player_slots"] = GetAvailableSlots(),
            ["taken_player_slots"] = GetTakenSlots(),
            ["your_player_slot"] = playerIdx,
            ["lobby"] = BuildLobbySnapshot(),
            ["cursors"] = BuildCursorSnapshot(),
        };

        if (_app.State == "menu")
        {
            snap["menu_games"] = GameButtonsList;
            return snap;
        }

        // End-game consensus
        var requiredIds = _uiClientSeat
            .Where(kv => kv.Value >= 0 && _uiClients.ContainsKey(kv.Key))
            .Select(kv => kv.Key).ToList();

        bool pressed = false;
        foreach (var (cid, seat) in _uiClientSeat)
        {
            if (!_uiClients.ContainsKey(cid)) continue;
            if (seat == playerIdx) { pressed = _uiClientEndGame.GetValueOrDefault(cid, false); break; }
        }

        snap["end_game"] = new Dictionary<string, object?>
        {
            ["pressed"] = pressed,
            ["pressed_count"] = requiredIds.Count(cid => _uiClientEndGame.GetValueOrDefault(cid, false)),
            ["required_count"] = requiredIds.Count,
        };

        var game = _app.GetActiveGame();
        if (game != null)
        {
            if (game.State == "player_select")
                snap["player_select"] = BuildPlayerSelectSnapshot(game);

            snap["popup"] = game.GetPopupSnapshot(playerIdx);

            var popupSnap = snap["popup"] as Dictionary<string, object?>;
            bool popupActive = popupSnap != null
                && popupSnap.TryGetValue("active", out var av) && av is true;

            snap["panel_buttons"] = popupActive
                ? new List<Dictionary<string, object?>>()
                : game.GetPanelButtons(playerIdx);

            var gameSnap = game.GetSnapshot(playerIdx);
            foreach (var (k, v) in gameSnap)
                snap[k] = v;
        }

        return snap;
    }

    private List<Dictionary<string, object?>> BuildCursorSnapshot()
    {
        var list = new List<Dictionary<string, object?>>();
        foreach (var (seat, cur) in _webCursors)
        {
            if (_elapsed - cur.Time > 10.0) continue;
            float nx = cur.X / (float)GameConfig.ScreenWidth;
            float ny = cur.Y / (float)GameConfig.ScreenHeight;
            var col = GameConfig.PlayerColors[seat % GameConfig.PlayerColors.Length];
            list.Add(new Dictionary<string, object?>
            {
                ["player_idx"] = seat,
                ["name"] = PlayerDisplayName(seat),
                ["color"] = new[] { col.R, col.G, col.B },
                ["x"] = nx,
                ["y"] = ny,
                ["age_ms"] = (int)((_elapsed - cur.Time) * 1000),
            });
        }
        return list;
    }

    private Dictionary<string, object?> BuildLobbySnapshot()
    {
        var players = GetLobbyPlayersSnapshot();
        var seated = _uiClientSeat
            .Where(kv => kv.Value >= 0 && _uiClients.ContainsKey(kv.Key)).ToList();

        var votes = new Dictionary<string, int>();
        if (_app.State == "menu")
        {
            foreach (var (cid, key) in _uiClientVote)
            {
                if (string.IsNullOrEmpty(key)) continue;
                if (!_uiClientReady.GetValueOrDefault(cid, false)) continue;
                votes[key] = votes.GetValueOrDefault(key, 0) + 1;
            }
        }

        return new Dictionary<string, object?>
        {
            ["players"] = players,
            ["all_ready"] = LobbyAllReady(),
            ["votes"] = votes,
            ["seated_count"] = seated.Count,
            ["min_players"] = GameConfig.MinPlayers,
        };
    }

    private List<Dictionary<string, object?>> GetLobbyPlayersSnapshot()
    {
        var list = new List<Dictionary<string, object?>>();
        foreach (var (cid, _) in _uiClients)
        {
            int seat = _uiClientSeat.GetValueOrDefault(cid, -1);
            list.Add(new Dictionary<string, object?>
            {
                ["client_id"] = cid,
                ["seat"] = seat,
                ["name"] = _uiClientName.GetValueOrDefault(cid, seat >= 0 ? $"Player {seat + 1}" : ""),
                ["ready"] = _uiClientReady.GetValueOrDefault(cid, false),
                ["vote"] = _uiClientVote.TryGetValue(cid, out var v) ? v : null,
                ["connected"] = true,
            });
        }
        list.Sort((a, b) =>
        {
            int sa = (int)(a["seat"] ?? -1), sb = (int)(b["seat"] ?? -1);
            int c = (sa < 0 ? 1 : 0).CompareTo(sb < 0 ? 1 : 0);
            return c != 0 ? c : sa.CompareTo(sb);
        });
        return list;
    }

    private Dictionary<string, object?> BuildPlayerSelectSnapshot(IGame game)
    {
        var selected = game.SelectionUI.Selected;
        int slotCount = _app.State == "cluedo" ? 6 : 8;
        var slots = new List<Dictionary<string, object?>>();

        for (int i = 0; i < slotCount; i++)
        {
            slots.Add(new Dictionary<string, object?>
            {
                ["player_idx"] = i,
                ["label"] = PlayerDisplayName(i),
                ["selected"] = i < selected.Length && selected[i],
            });
        }

        int selCount = slots.Count(s => s["selected"] is true);
        bool startEnabled = _app.State switch
        {
            "blackjack" => selCount >= 1,
            "cluedo" => selCount >= 3 && selCount <= 6,
            "catan" => selCount >= 2 && selCount <= 8,
            "dnd_creation" => selCount >= 2,
            _ => selCount >= 2,
        };

        return new Dictionary<string, object?>
        {
            ["slots"] = slots,
            ["start_enabled"] = startEnabled,
        };
    }

    // ═══════════════════════════════════════════════════════════════
    //  Public accessors (for menu drawing and game name resolution)
    // ═══════════════════════════════════════════════════════════════
    public List<LobbyPlayer> GetLobbyPlayers()
    {
        var list = new List<LobbyPlayer>();
        foreach (var (cid, _) in _uiClients)
        {
            int seat = _uiClientSeat.GetValueOrDefault(cid, -1);
            list.Add(new LobbyPlayer
            {
                ClientId = cid, Seat = seat,
                Name = _uiClientName.GetValueOrDefault(cid, seat >= 0 ? $"Player {seat + 1}" : ""),
                Ready = _uiClientReady.GetValueOrDefault(cid, false),
                Vote = _uiClientVote.TryGetValue(cid, out var v) ? v : null,
                Connected = true,
            });
        }
        list.Sort((a, b) =>
        {
            int c = (a.Seat < 0 ? 1 : 0).CompareTo(b.Seat < 0 ? 1 : 0);
            return c != 0 ? c : a.Seat.CompareTo(b.Seat);
        });
        return list;
    }

    public string[] GetLobbyConnectLines()
    {
        if (_connectLinesCache != null && _connectCacheAge < 5.0)
            return _connectLinesCache;

        var lines = new List<string>();
        try
        {
            using var s = new Socket(AddressFamily.InterNetwork, SocketType.Dgram, ProtocolType.Udp);
            s.Connect("8.8.8.8", 80);
            string? localIp = (s.LocalEndPoint as IPEndPoint)?.Address.ToString();
            if (!string.IsNullOrEmpty(localIp))
                lines.Add($"Local Web UI:  http://{localIp}:{GameConfig.HttpPort}");
        }
        catch { }
        if (lines.Count == 0)
            lines.Add($"Web UI:  http://0.0.0.0:{GameConfig.HttpPort}");

        _connectLinesCache = lines.ToArray();
        _connectCacheAge = 0;
        return _connectLinesCache;
    }

    public string PlayerDisplayName(int idx)
    {
        if (PlayerNames.TryGetValue(idx, out var n) && !string.IsNullOrWhiteSpace(n))
            return n;
        return $"Player {idx + 1}";
    }

    // ═══════════════════════════════════════════════════════════════
    //  Per-frame update
    // ═══════════════════════════════════════════════════════════════
    public void Update(double dt)
    {
        _broadcastTimer += dt;
        _connectCacheAge += dt;
        _elapsed += dt;
        MaybeAutoStartActiveGame();
        DispatchCursorClicks();
        AudioTick();
    }

    private double _elapsed;

    /// <summary>Sync background music with game state, detect SFX triggers.</summary>
    private void AudioTick()
    {
        // Sync BG music to current game state
        _audio.SyncBgMusic(_app.State);
        _prevAudioState = _app.State;
    }

    /// <summary>Play a sound effect (called from game event handlers).</summary>
    public void PlaySfx(string filename) => _audio.PlaySfx(filename);

    /// <summary>Play SFX based on button click action (mirrors Python event-driven SFX).</summary>
    private void PlayButtonSfx(string btnId, string gameState)
    {
        switch (btnId)
        {
            // Card-related actions
            case "draw" or "draw_card" or "hit" or "deal" or "next_hand" or "play_again":
                _audio.PlaySfx("FlipCard.mp3");
                break;

            // Dice-related actions
            case "roll_dice" or "roll":
                _audio.PlaySfx("RollDice.mp3");
                break;

            // Attack/combat actions
            case "attack" or "resolve_attack":
                if (gameState == "risk")
                    _audio.PlaySfx("SwordSlice.mp3");
                else
                    _audio.PlaySfx("Swoosh.mp3");
                break;

            // Ready/confirmation
            case "ready" or "start":
                _audio.PlaySfx("HeartbeatReady.mp3");
                break;

            // Movement
            case var id when id.StartsWith("move_"):
                _audio.PlaySfx("MovePlayer.mp3");
                break;

            // Stand / pass / skip
            case "stand" or "pass" or "skip" or "end_turn" or "check" or "fold":
                _audio.PlaySfx("Swoosh.mp3");
                break;

            // Betting actions
            case "call" or "raise" or "double_down" or "split" or "bet":
                _audio.PlaySfx("MovePlayer.mp3");
                break;

            // Nope / Neigh (counter-play)
            case "nope" or "uu_react_neigh" or "uu_react_super" or "uu_react_pass":
                _audio.PlaySfx("SwordSlice.mp3");
                break;

            // Generic card plays (covers uu_play:X, ek_play:X, uno_play:X, play_X, card_X)
            case var id when id.StartsWith("play_") || id.StartsWith("card_")
                          || id.StartsWith("uu_play:") || id.StartsWith("uu_discard:")
                          || id.StartsWith("ek_play:") || id.StartsWith("uno_play:"):
                _audio.PlaySfx("FlipCard.mp3");
                break;

            default:
                // Many buttons are game-specific; only play SFX for known actions
                break;
        }
    }

    /// <summary>
    /// Skip redundant in-game player selection — auto-start using seated clients.
    /// Mirrors Python _maybe_auto_start_active_game.
    /// </summary>
    private void MaybeAutoStartActiveGame()
    {
        if (_app.State == "menu") return;

        var game = _app.GetActiveGame();
        if (game == null || game.State != "player_select") return;

        var seats = ActiveConnectedSeats();
        if (seats.Count == 0) return;

        // Per-game minimums (matching Python)
        int minPlayers = _app.State switch
        {
            "blackjack" => 1,
            "cluedo" => 3,
            "dnd_creation" => 2,
            _ => 2,
        };

        if (seats.Count < minPlayers) return;

        // D&D: choose a default DM (lowest seat) if not set
        if (_app.State == "dnd_creation" && game is DnDGameSharp dnd)
        {
            if (!dnd.DmSeat.HasValue || !seats.Contains(dnd.DmSeat.Value))
                dnd.DmSeat = seats[0];
        }

        try
        {
            game.StartGame(new List<int>(seats));
            LogHistory($"Auto-started {_app.State} with {seats.Count} players");
        }
        catch { /* ignore start errors */ }
    }

    /// <summary>Return sorted list of seats occupied by connected clients.</summary>
    private List<int> ActiveConnectedSeats()
    {
        var seats = new HashSet<int>();
        foreach (var (cid, seat) in _uiClientSeat)
        {
            if (!_uiClients.ContainsKey(cid)) continue;
            if (seat >= 0 && seat <= 7)
                seats.Add(seat);
        }
        return seats.OrderBy(s => s).ToList();
    }

    // ═══════════════════════════════════════════════════════════════
    //  UI broadcast loop (10 Hz per-player snapshots to /ui clients)
    // ═══════════════════════════════════════════════════════════════
    private async Task UIBroadcastLoop(CancellationToken ct)
    {
        while (!ct.IsCancellationRequested)
        {
            try { await Task.Delay(100, ct); }
            catch (TaskCanceledException) { break; }
            try
            {
                if (_uiClients.IsEmpty) continue;

                // Auto-select seated players in player_select
                var activeGame = _app.GetActiveGame();
                if (activeGame?.State == "player_select")
                {
                    foreach (var (cid, seat) in _uiClientSeat)
                        if (seat >= 0 && seat < activeGame.SelectionUI.Selected.Length && _uiClients.ContainsKey(cid))
                            activeGame.SelectionUI.Selected[seat] = true;
                }

                var dead = new List<string>();
                var tasks = new List<(string id, Task task)>();

                foreach (var (clientId, ws) in _uiClients)
                {
                    try
                    {
                        if (ws.State != WebSocketState.Open) { dead.Add(clientId); continue; }

                        var snapshot = BuildSnapshot(clientId);
                        var payload = new Dictionary<string, object?>
                        {
                            ["type"] = "snapshot",
                            ["data"] = snapshot,
                        };
                        string json = JsonSerializer.Serialize(payload);
                        byte[] data = Encoding.UTF8.GetBytes(json);
                        tasks.Add((clientId, ws.SendAsync(data, WebSocketMessageType.Text, true, ct)));
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine($"Broadcast error for {clientId}: {ex}");
                        dead.Add(clientId);
                    }
                }

                foreach (var (id, t) in tasks)
                {
                    try { await t; }
                    catch { dead.Add(id); }
                }

                foreach (var id in dead.Distinct())
                {
                    _uiClients.TryRemove(id, out _);
                    _uiClientSeat.TryRemove(id, out _);
                    _uiClientName.TryRemove(id, out _);
                    _uiClientReady.TryRemove(id, out _);
                    _uiClientVote.TryRemove(id, out _);
                    _uiClientEndGame.TryRemove(id, out _);
                }
            }
            catch { }
        }
    }

    // ═══════════════════════════════════════════════════════════════
    //  Frame broadcast
    // ═══════════════════════════════════════════════════════════════
    public void OnFrameReady(RenderTarget2D target)
    {
        if (_broadcastTimer < BroadcastInterval) return;
        if (_frameClients.IsEmpty) return;
        _broadcastTimer = 0;

        byte[] jpeg;
        try
        {
            using var ms = new MemoryStream();
            target.SaveAsJpeg(ms, target.Width, target.Height);
            jpeg = ms.ToArray();
        }
        catch { return; }

        Task.Run(() => BroadcastBytes(jpeg));
    }

    private async void BroadcastBytes(byte[] data)
    {
        var dead = new List<string>();
        foreach (var (id, ws) in _frameClients)
        {
            try
            {
                if (ws.State == WebSocketState.Open)
                    await ws.SendAsync(data, WebSocketMessageType.Binary, true, CancellationToken.None);
                else dead.Add(id);
            }
            catch { dead.Add(id); }
        }
        foreach (var id in dead)
            _frameClients.TryRemove(id, out _);
    }

    public void Stop()
    {
        _cts.Cancel();
        _audio.Dispose();
        try { _httpListener?.Stop(); } catch { }
        try { _wsListener?.Stop(); } catch { }

        // Kill the Vite dev server process tree
        if (_npmProcess != null && !_npmProcess.HasExited)
        {
            try
            {
                // Kill process tree (cmd.exe + node child)
                using var kill = Process.Start(new ProcessStartInfo
                {
                    FileName = "taskkill",
                    Arguments = $"/T /F /PID {_npmProcess.Id}",
                    UseShellExecute = false,
                    CreateNoWindow = true,
                });
                kill?.WaitForExit(3000);
            }
            catch { /* best-effort */ }
            finally { _npmProcess = null; }
        }
    }
}
