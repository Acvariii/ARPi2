using System;
using System.Collections.Generic;

namespace ARPi2.Sharp.Core;

/// <summary>
/// Universal popup system — floating text box above player panels.
/// Port of Python core/popup_system.py.
/// </summary>
public class UniversalPopup
{
    public bool Active;
    public int? PlayerIdx;
    public (int X, int Y, int W, int H)? PanelRect;
    public (int X, int Y, int W, int H)? PopupRect;
    public int Orientation;
    public string PopupType = "";
    public Dictionary<string, object> Data = new();
    public List<(string Text, int FontSize, (int R, int G, int B) Color)> TextLines = new();

    public void Show(int playerIdx, (int, int, int, int) panelRect, int orientation,
                     string popupType, List<(string, int, (int, int, int))> textLines,
                     Dictionary<string, object>? data = null)
    {
        Active = true;
        PlayerIdx = playerIdx;
        PanelRect = panelRect;
        Orientation = orientation;
        PopupType = popupType;
        TextLines = textLines;
        Data = data ?? new();
        CalculatePopupRect();
    }

    public void Hide()
    {
        Active = false;
        PlayerIdx = null;
        PanelRect = null;
        PopupRect = null;
        TextLines.Clear();
        Data.Clear();
    }

    private void CalculatePopupRect()
    {
        if (PanelRect == null) return;
        var (px, py, pw, ph) = PanelRect.Value;
        int numLines = Math.Max(1, TextLines.Count);
        int maxFS = 16;
        foreach (var tl in TextLines) if (tl.FontSize > maxFS) maxFS = tl.FontSize;

        int lineH = maxFS + 15;
        int popupW, popupH;

        if (Orientation is 90 or 270)
        {
            popupH = Math.Max(350, numLines * 70 + 140);
            popupW = Math.Max(140, Math.Min(320, maxFS * 7 / 2));
        }
        else
        {
            popupW = Math.Max(240, numLines * 14 + 100); // simplified
            popupH = Math.Max(120, numLines * lineH + 70);
        }

        int ox, oy;
        switch (Orientation)
        {
            case 0:   ox = px - (popupW - pw) / 2; oy = py - popupH - 10; break;
            case 180: ox = px - (popupW - pw) / 2; oy = py + ph + 10; break;
            case 270: ox = px + pw + 10; oy = py + (ph - popupH) / 2; break;
            default:  ox = px - popupW - 10; oy = py + (ph - popupH) / 2; break;
        }
        PopupRect = (ox, oy, popupW, popupH);
    }

    public void Draw(Renderer r)
    {
        if (!Active || PopupRect == null || PlayerIdx == null || TextLines.Count == 0) return;
        var (px, py, pw, ph) = PopupRect.Value;

        // Solid background
        r.DrawRect((20, 25, 30), (px, py, pw, ph));
        r.DrawRect((25, 30, 35), (px + 1, py + 1, pw - 2, ph - 2));

        // Player colour border
        var borderCol = GameConfig.PlayerColors[PlayerIdx.Value];
        r.DrawRect(borderCol, (px, py, pw, ph), width: 5);
        r.DrawRect((60, 65, 75), (px + 6, py + 6, pw - 12, ph - 12), width: 2);

        // Text lines
        int n = TextLines.Count;
        if (Orientation is 90 or 270)
        {
            float lineW = (pw - 20f) / n;
            for (int i = 0; i < n; i++)
            {
                int posIdx = Orientation == 270 ? n - 1 - i : i;
                int cx = px + (int)((posIdx + 0.5f) * lineW) + 10;
                int cy = py + ph / 2;
                DrawOrientedText(r, TextLines[i].Text, cx, cy,
                                 TextLines[i].FontSize, TextLines[i].Color);
            }
        }
        else
        {
            float lineH2 = (ph - 20f) / n;
            for (int i = 0; i < n; i++)
            {
                int cx = px + pw / 2;
                int cy = Orientation == 0
                    ? py + (int)((i + 0.5f) * lineH2) + 10
                    : py + ph - (int)((i + 0.5f) * lineH2) - 10;
                DrawOrientedText(r, TextLines[i].Text, cx, cy,
                                 TextLines[i].FontSize, TextLines[i].Color);
            }
        }
    }

    private void DrawOrientedText(Renderer r, string text, int x, int y,
                                  int fontSize, (int, int, int) color)
    {
        float rot = Orientation switch { 0 => 0, 180 => 180, 270 => 90, _ => 270 };
        r.DrawText(text, x, y, fontSize: fontSize, color: color,
                   anchorX: "center", anchorY: "center", rotation: rot);
    }
}

// ═══════════════════════════════════════════════════════════════════════════
//  Popup factory helpers
// ═══════════════════════════════════════════════════════════════════════════
public static class PopupFactory
{
    public static List<(string, int, (int, int, int))> BuyProperty(int money, string name, int price) => new()
    {
        ("BUY PROPERTY", 14, (180, 180, 180)),
        (name, 18, (255, 255, 255)),
        ($"Price: ${price}", 16, (100, 255, 100)),
        ($"Balance: ${money}", 14, (255, 255, 100)),
    };

    /// <summary>Alias for BuyProperty, used by MonopolyGameSharp.</summary>
    public static List<(string, int, (int, int, int))> CreateMonopolyBuyPopup(int money, string name, int price) =>
        BuyProperty(money, name, price);

    public static List<(string, int, (int, int, int))> Card(string text, string deckType) => new()
    {
        (deckType == "chance" ? "CHANCE" : "COMMUNITY CHEST", 16, (255, 215, 0)),
        (text, 14, (255, 255, 255)),
    };

    public static List<(string, int, (int, int, int))> Info(string title, string msg) => new()
    {
        (title, 16, (255, 215, 0)),
        (msg, 14, (255, 255, 255)),
    };
}
