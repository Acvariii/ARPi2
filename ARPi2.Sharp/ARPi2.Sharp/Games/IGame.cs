using System;
using System.Collections.Generic;
using ARPi2.Sharp.Core;

namespace ARPi2.Sharp.Games;

/// <summary>
/// Common interface every game must implement.
/// Mirrors the Python game pattern: state machine, selection UI, draw/update, buttons.
/// </summary>
public interface IGame
{
    /// <summary>Current state: "player_select", "playing", "game_over", etc.</summary>
    string State { get; set; }

    /// <summary>Player selection UI instance.</summary>
    PlayerSelectionUI SelectionUI { get; }

    /// <summary>Active player indices (set after player selection).</summary>
    List<int> ActivePlayers { get; set; }

    /// <summary>Draw the game each frame. Called inside BeginFrame/EndFrame.</summary>
    void Draw(Renderer r, int width, int height, double dt);

    /// <summary>Update game logic (called once per tick at FPS rate).</summary>
    void Update(double dt);

    /// <summary>Start the game with the selected players.</summary>
    void StartGame(List<int> players);

    /// <summary>Get current buttons for the UI overlay (web UI).</summary>
    List<WebUIButton> GetButtons();

    /// <summary>Handle a button press from the web UI (legacy).</summary>
    void HandleButton(int playerIdx, string action, string? value = null);

    /// <summary>Handle a click_button press from the web UI (by button ID).</summary>
    void HandleClick(int playerIdx, string buttonId);

    /// <summary>Handle a game-specific message from the web UI (e.g. blackjack_bet, uno_play_card).</summary>
    void HandleMessage(int playerIdx, string type, string json);

    /// <summary>Get game-specific state for web UI JSON broadcast (legacy, non-per-player).</summary>
    Dictionary<string, object?> GetWebUIState();

    /// <summary>Get per-player game state snapshot for web UI broadcast.</summary>
    Dictionary<string, object?> GetSnapshot(int playerIdx);

    /// <summary>Get popup snapshot for a specific player.</summary>
    Dictionary<string, object?> GetPopupSnapshot(int playerIdx);

    /// <summary>Get panel buttons for a specific player.</summary>
    List<Dictionary<string, object?>> GetPanelButtons(int playerIdx);

    /// <summary>The game's popup instance (if any).</summary>
    UniversalPopup? Popup { get; }

    /// <summary>Background theme name for card_rendering backgrounds.</summary>
    string ThemeName { get; }

    /// <summary>Whether this game is running in board-only mode (no panels).</summary>
    bool BoardOnlyMode { get; set; }

    /// <summary>Whether player selection is web-UI only.</summary>
    bool WebUIOnlyPlayerSelect { get; set; }

    /// <summary>Optional: inject a name provider callback.</summary>
    void SetNameProvider(Func<int, string>? provider);
}

/// <summary>
/// Represents a button displayed in the web UI for a specific player.
/// Different from Core.GameButton which is the interactive on-screen button.
/// </summary>
public class WebUIButton
{
    public string Label { get; set; } = "";
    public string Action { get; set; } = "";
    public string? Value { get; set; }
    public int PlayerIdx { get; set; } = -1;
    public bool Enabled { get; set; } = true;
    public bool Visible { get; set; } = true;
}

/// <summary>
/// Abstract base class with common game boilerplate.
/// </summary>
public abstract class BaseGame : IGame
{
    public string State { get; set; } = "player_select";
    public PlayerSelectionUI SelectionUI { get; protected set; }
    public List<int> ActivePlayers { get; set; } = new();
    public bool BoardOnlyMode { get; set; }
    public bool WebUIOnlyPlayerSelect { get; set; }
    public abstract string ThemeName { get; }
    public virtual UniversalPopup? Popup => null;

    protected Renderer Renderer;
    protected int ScreenW, ScreenH;
    protected Func<int, string>? NameProvider;
    protected Random Rng = new();

    protected BaseGame(int w, int h, Renderer renderer)
    {
        ScreenW = w;
        ScreenH = h;
        Renderer = renderer;
        SelectionUI = new PlayerSelectionUI(w, h);
    }

    public void SetNameProvider(Func<int, string>? provider) => NameProvider = provider;

    protected string PlayerName(int idx)
    {
        if (NameProvider != null) return NameProvider(idx);
        return $"Player {idx + 1}";
    }

    public virtual void Draw(Renderer r, int width, int height, double dt)
    {
        if (State == "player_select")
        {
            CardRendering.DrawGameBackground(r, width, height, ThemeName);
            SelectionUI.Draw(r);
        }
    }

    public virtual void Update(double dt) { }

    public abstract void StartGame(List<int> players);

    public virtual List<WebUIButton> GetButtons() => new();

    public virtual void HandleButton(int playerIdx, string action, string? value = null) { }

    public virtual void HandleClick(int playerIdx, string buttonId) { }

    public virtual void HandleMessage(int playerIdx, string type, string json) { }

    public virtual Dictionary<string, object?> GetWebUIState() => new()
    {
        ["state"] = State,
        ["active_players"] = ActivePlayers,
    };

    public virtual Dictionary<string, object?> GetSnapshot(int playerIdx) => new();

    public virtual Dictionary<string, object?> GetPopupSnapshot(int playerIdx) => new()
    {
        ["active"] = false,
    };

    public virtual List<Dictionary<string, object?>> GetPanelButtons(int playerIdx) => new();
}
