using System;
using System.Collections.Generic;
using ARPi2.Sharp.Core;

namespace ARPi2.Sharp.Games;

/// <summary>
/// Placeholder game used for the 9 non-Monopoly games until they are fully ported.
/// Draws the themed background and a "Coming Soon" message.
/// </summary>
public class StubGame : BaseGame
{
    private readonly string _displayName;
    private readonly string _theme;
    public override string ThemeName => _theme;

    public StubGame(int w, int h, Renderer renderer, string displayName, string themeName)
        : base(w, h, renderer)
    {
        _displayName = displayName;
        _theme = themeName;
    }

    public override void StartGame(List<int> players)
    {
        ActivePlayers = new List<int>(players);
        State = "playing";
    }

    public override void Draw(Renderer r, int width, int height, double dt)
    {
        if (State == "player_select")
        {
            base.Draw(r, width, height, dt);
            return;
        }

        // Draw themed background
        CardRendering.DrawGameBackground(r, width, height, ThemeName);

        // Coming soon overlay
        int cx = width / 2, cy = height / 2;
        r.DrawRect((0, 0, 0), (cx - 260, cy - 60, 520, 120), alpha: 180);
        r.DrawRect((255, 215, 0), (cx - 260, cy - 60, 520, 120), width: 3, alpha: 200);
        r.DrawText(_displayName, cx, cy - 18, 42, (255, 255, 255),
                   anchorX: "center", anchorY: "center");
        r.DrawText("Coming Soon", cx, cy + 24, 22, (200, 200, 200),
                   anchorX: "center", anchorY: "center");
    }
}
