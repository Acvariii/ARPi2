using System;
using System.Collections.Generic;

namespace ARPi2.Sharp.Core;

/// <summary>
/// Reusable UI components — buttons, panels, hover indicators.
/// Port of Python core/ui_components.py.
/// </summary>
/// 
// ═══════════════════════════════════════════════════════════════════════════
//  Button
// ═══════════════════════════════════════════════════════════════════════════
public class GameButton
{
    public int X, Y, Width, Height;
    public string Text;
    public int Orientation;
    public bool Enabled = true;
    public float HoverStart;
    public bool Hovering;

    public GameButton(int x, int y, int w, int h, string text, int orientation = 0)
    {
        X = x; Y = y; Width = w; Height = h; Text = text; Orientation = orientation;
    }

    public (bool Clicked, float Progress) Update(List<(int X, int Y, bool Click)> inputs, float currentTime)
    {
        if (!Enabled) { Hovering = false; HoverStart = 0; return (false, 0f); }

        foreach (var (ix, iy, click) in inputs)
        {
            if (ix >= X && ix <= X + Width && iy >= Y && iy <= Y + Height)
            {
                if (click) { Hovering = false; HoverStart = 0; return (true, 1f); }
                if (!Hovering) { HoverStart = currentTime; Hovering = true; }
                float progress = (currentTime - HoverStart) / GameConfig.HoverTimeThreshold;
                if (progress >= 1f) { Hovering = false; HoverStart = 0; return (true, 1f); }
                return (false, progress);
            }
        }

        Hovering = false;
        HoverStart = 0;
        return (false, 0f);
    }

    public void Draw(Renderer r, float hoverProgress = 0f)
    {
        var bg = !Enabled ? (100, 100, 100) : hoverProgress > 0 ? (255, 255, 255) : (200, 200, 200);
        var textCol = !Enabled ? (160, 160, 160) : (0, 0, 0);

        r.DrawRect(bg, (X, Y, Width, Height));
        r.DrawRect((200, 200, 200), (X, Y, Width, Height), width: 2);

        if (hoverProgress > 0 && Enabled)
        {
            if (Orientation is 90 or 270)
            {
                int barH = (int)(Height * hoverProgress);
                int barX = Orientation == 270 ? X + Width - 4 : X;
                r.DrawRect((255, 215, 0), (barX, Y, 4, barH));
            }
            else
            {
                int barW = (int)(Width * hoverProgress);
                r.DrawRect((255, 215, 0), (X, Y + Height - 4, barW, 4));
            }
        }

        int cx = X + Width / 2, cy = Y + Height / 2;
        float rot = Orientation switch { 270 => 90, 90 => 270, _ => Orientation };
        r.DrawText(Text, cx, cy, fontSize: 18, color: textCol,
                   anchorX: "center", anchorY: "center", rotation: rot);
    }
}

// ═══════════════════════════════════════════════════════════════════════════
//  Player Panel
// ═══════════════════════════════════════════════════════════════════════════
public class PlayerPanel
{
    /// <summary>
    /// Panel positions: bottom (0-2), top (3-5), left (6), right (7).
    /// (side, slot, orientation)
    /// </summary>
    public static readonly (string Side, int Slot, int Orientation)[] Positions =
    {
        ("bottom", 0,   0), ("bottom", 1,   0), ("bottom", 2,   0),
        ("top",    0, 180), ("top",    1, 180), ("top",    2, 180),
        ("left",   0, 270), ("right",  0,  90),
    };

    public int PlayerIdx;
    public int ScreenWidth, ScreenHeight;
    public (int R, int G, int B) Color;
    public string Side;
    public int Slot, Orientation;
    public (int X, int Y, int W, int H) Rect;

    public PlayerPanel(int playerIdx, int screenW, int screenH)
    {
        PlayerIdx = playerIdx;
        ScreenWidth = screenW;
        ScreenHeight = screenH;
        Color = GameConfig.PlayerColors[playerIdx];
        var pos = Positions[playerIdx];
        Side = pos.Side; Slot = pos.Slot; Orientation = pos.Orientation;
        Rect = CalculateRect();
    }

    private (int, int, int, int) CalculateRect()
    {
        int w = ScreenWidth, h = ScreenHeight;
        int panelH = (int)(h * 0.10);
        int panelWSide = (int)(w * 0.12);

        return Side switch
        {
            "bottom" => (Slot * (w / 3), h - panelH, w / 3, panelH),
            "top"    => (Slot * (w / 3), 0, w / 3, panelH),
            "left"   => (0, panelH, panelWSide, h - 2 * panelH),
            "right"  => (w - panelWSide, panelH, panelWSide, h - 2 * panelH),
            _ => (0, 0, 0, 0),
        };
    }

    public void DrawBackground(Renderer r, bool isCurrent = false)
    {
        var (rx, ry, rw, rh) = Rect;
        var sat = (Math.Min(255, (int)(Color.R * 1.1)),
                   Math.Min(255, (int)(Color.G * 1.1)),
                   Math.Min(255, (int)(Color.B * 1.1)));

        int layers = 40;
        if (Orientation is 0 or 180)
        {
            float layerH = rh / (float)layers;
            for (int i = 0; i < layers; i++)
            {
                float dist = MathF.Abs((i - layers / 2f) / (layers / 2f));
                float gauss = MathF.Exp(-(dist * 3f) * (dist * 3f) / 2f);
                float shine = 60 * gauss;
                var sc = (Math.Min(255, (int)(sat.Item1 * 0.8f + shine)),
                          Math.Min(255, (int)(sat.Item2 * 0.8f + shine)),
                          Math.Min(255, (int)(sat.Item3 * 0.8f + shine)));
                r.DrawRect(sc, (rx, ry + (int)(i * layerH), rw, (int)layerH + 1));
            }
        }
        else
        {
            float layerW = rw / (float)layers;
            for (int i = 0; i < layers; i++)
            {
                float dist = MathF.Abs((i - layers / 2f) / (layers / 2f));
                float gauss = MathF.Exp(-(dist * 3f) * (dist * 3f) / 2f);
                float shine = 60 * gauss;
                var sc = (Math.Min(255, (int)(sat.Item1 * 0.8f + shine)),
                          Math.Min(255, (int)(sat.Item2 * 0.8f + shine)),
                          Math.Min(255, (int)(sat.Item3 * 0.8f + shine)));
                r.DrawRect(sc, (rx + (int)(i * layerW), ry, (int)layerW + 1, rh));
            }
        }

        var border = isCurrent ? (255, 215, 0) : (180, 190, 200);
        int bw = isCurrent ? 4 : 2;
        r.DrawRect(border, (rx, ry, rw, rh), width: bw);
    }

    public void DrawTextOriented(Renderer r, string text, float xOff, float yOff,
                                  int fontSize, (int, int, int) color)
    {
        var (rx, ry, rw, rh) = Rect;
        int tx, ty;
        float rot;

        switch (Orientation)
        {
            case 0:   tx = rx + (int)(rw * xOff); ty = ry + (int)(rh * yOff); rot = 0; break;
            case 180: tx = rx + (int)(rw * xOff); ty = ry + (int)(rh * (1 - yOff)); rot = 180; break;
            case 270: tx = rx + (int)(rw * (1 - yOff)); ty = ry + (int)(rh * xOff); rot = 90; break;
            default:  tx = rx + (int)(rw * yOff); ty = ry + (int)(rh * (1 - xOff)); rot = 270; break;
        }

        r.DrawText(text, tx, ty, fontSize: fontSize, color: color,
                   anchorX: "center", anchorY: "center", rotation: rot);
    }

    public List<(int X, int Y, int W, int H)> GetButtonLayout(int maxButtons = 3)
    {
        var (rx, ry, rw, rh) = Rect;
        int margin = 10, gap = 8;
        var buttons = new List<(int, int, int, int)>();

        if (Orientation is 0 or 180)
        {
            int infoH = (int)(rh * 0.45);
            int btnH = rh - infoH - 2 * margin;
            int btnW = (rw - 2 * margin - 2 * gap) / 3;
            int btnY = Orientation == 0 ? ry + infoH + margin : ry + margin;

            for (int i = 0; i < Math.Min(maxButtons, 3); i++)
                buttons.Add((rx + margin + i * (btnW + gap), btnY, btnW, btnH));
        }
        else // left/right
        {
            int btnAreaW = (int)(rw * 0.70);
            int btnH = (rh - 2 * margin - (maxButtons - 1) * gap) / maxButtons;
            int btnX = Orientation == 270 ? rx + margin : rx + rw - btnAreaW + margin;
            int btnW = btnAreaW - 2 * margin;

            for (int i = 0; i < maxButtons; i++)
                buttons.Add((btnX, ry + margin + i * (btnH + gap), btnW, btnH));
        }

        return buttons;
    }
}

// ═══════════════════════════════════════════════════════════════════════════
//  Helpers
// ═══════════════════════════════════════════════════════════════════════════
public static class PanelHelpers
{
    public static List<PlayerPanel> CalculateAllPanels(int w, int h)
    {
        var list = new List<PlayerPanel>(8);
        for (int i = 0; i < 8; i++) list.Add(new PlayerPanel(i, w, h));
        return list;
    }

    public static void DrawHoverIndicators(Renderer r,
        Dictionary<int, Dictionary<string, GameButton>> buttons,
        List<int> activePlayers, float currentTime)
    {
        foreach (int idx in activePlayers)
        {
            if (!buttons.TryGetValue(idx, out var bmap)) continue;
            foreach (var btn in bmap.Values)
            {
                if (!btn.Hovering || btn.HoverStart <= 0) continue;
                float progress = MathF.Min(1f, (currentTime - btn.HoverStart) / GameConfig.HoverTimeThreshold);
                int cx = btn.X + btn.Width / 2, cy = btn.Y + btn.Height / 2;
                r.DrawCircularProgress((cx, cy), 30, progress, (100, 200, 255), 5);
            }
        }
    }
}
