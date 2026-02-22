using System;

namespace ARPi2.Sharp.Core;

/// <summary>
/// Procedural game backgrounds and card drawing — full port of Python core/card_rendering.py.
/// All backgrounds are drawn purely with primitives (no texture assets).
/// </summary>
public static class CardRendering
{
    // ───── Playing-card parsing ─────
    public static (string rank, string suit, bool isRed) ParsePlayingCard(string card)
    {
        string t = (card ?? "").Trim();
        if (t.Length == 0) return ("", "", false);
        string suitRaw = t[^1..];
        string rankRaw = t.Length >= 2 ? t[..^1] : t;
        string suit = suitRaw switch {
            "S" => "♠", "H" => "♥", "D" => "♦", "C" => "♣",
            "♠" => "♠", "♥" => "♥", "♦" => "♦", "♣" => "♣",
            _ => suitRaw
        };
        string rank = rankRaw == "T" ? "10" : rankRaw;
        bool isRed = suit is "♥" or "♦";
        return (rank, suit, isRed);
    }

    // ───── Draw a playing card (poker/blackjack) ─────
    public static void DrawPlayingCard(Renderer r,
        (int x, int y, int w, int h) rect, string card = "",
        bool faceUp = true,
        (int r, int g, int b)? borderRgb = null,
        int borderWidth = 2)
    {
        var bdr = borderRgb ?? (30, 30, 30);
        int x = rect.x, y = rect.y, cw = rect.w, ch = rect.h;

        // Shadow
        r.DrawRect((0, 0, 0), (x + 3, y + 3, cw, ch), alpha: 55);

        if (!faceUp)
        {
            r.DrawRect((50, 70, 150), (x, y, cw, ch));
            r.DrawRect((230, 230, 230), (x, y, cw, ch), width: 2);
            for (int i = 0; i < 5; i++)
                r.DrawLine((200, 200, 240), (x + 6, y + 10 + i * 18), (x + cw - 6, y + 2 + i * 18), width: 2, alpha: 70);
            return;
        }

        // Face-up base
        r.DrawRect((248, 248, 248), (x, y, cw, ch));
        r.DrawRect(bdr, (x, y, cw, ch), width: borderWidth);
        r.DrawRect((210, 210, 210), (x + 3, y + 3, cw - 6, ch - 6), width: 1);

        if (string.IsNullOrWhiteSpace(card)) return;
        var (rank, suit, isRed) = ParsePlayingCard(card);
        var color = isRed ? (220, 20, 20) : (20, 20, 20);

        int cornerFs = Math.Max(11, Math.Min(16, cw * 20 / 100));
        int centerFs = Math.Max(18, Math.Min(30, ch * 30 / 100));
        int cornerPad = Math.Max(7, cw * 12 / 100);
        string corner = $"{rank}{suit}";

        r.DrawText(corner, x + cornerPad, y + cornerPad, cornerFs, color, bold: true, anchorX: "left", anchorY: "top");
        r.DrawText(corner, x + cw - cornerPad, y + ch - cornerPad, cornerFs, color, bold: true, anchorX: "right", anchorY: "bottom");
        r.DrawText(suit, x + cw / 2, y + ch / 2, centerFs, color, anchorX: "center", anchorY: "center");
    }

    // ───── Draw a label card ─────
    public static void DrawLabelCard(Renderer r,
        (int x, int y, int w, int h) rect, string text,
        (int r, int g, int b)? faceColor = null,
        (int r, int g, int b)? borderColor = null)
    {
        var fc = faceColor ?? (160, 160, 160);
        var bc = borderColor ?? (20, 20, 25);
        r.DrawRect(fc, (rect.x, rect.y, rect.w, rect.h), alpha: 235);
        r.DrawRect(bc, (rect.x, rect.y, rect.w, rect.h), width: 2, alpha: 240);
        r.DrawText(text ?? "", rect.x + rect.w / 2, rect.y + rect.h / 2, 14, (15, 15, 15), anchorX: "center", anchorY: "center");
    }

    // ───── Draw a card styled like a real Uno card ─────
    public static void DrawUnoCard(Renderer r,
        (int x, int y, int w, int h) rect,
        string? color, string value,
        (int R, int G, int B) faceRgb)
    {
        int x2 = rect.x, y2 = rect.y, w2 = rect.w, h2 = rect.h;
        int cx = x2 + w2 / 2, cy = y2 + h2 / 2;
        bool isWild = value is "wild" or "wild_draw4";

        // Card shadow
        r.DrawRect((0, 0, 0), (x2 + 3, y2 + 3, w2, h2), alpha: 60);

        if (isWild)
        {
            // Wild card: 4-color quadrant background
            int hw = w2 / 2, hh = h2 / 2;
            r.DrawRect((220, 70, 70), (x2, y2, hw, hh));           // Red top-left
            r.DrawRect((80, 140, 235), (x2 + hw, y2, w2 - hw, hh));  // Blue top-right
            r.DrawRect((235, 210, 80), (x2, y2 + hh, hw, h2 - hh));  // Yellow bottom-left
            r.DrawRect((70, 200, 110), (x2 + hw, y2 + hh, w2 - hw, h2 - hh)); // Green bottom-right
        }
        else
        {
            // Solid color background
            r.DrawRect(faceRgb, (x2, y2, w2, h2));
        }

        // White inner oval (approximated with polygon ellipse — slightly tilted)
        int ovalSegments = 24;
        float ovalRx = w2 * 0.38f;
        float ovalRy = h2 * 0.42f;
        float tilt = -0.18f; // slight counter-clockwise tilt in radians
        var ovalPts = new (float X, float Y)[ovalSegments];
        for (int i = 0; i < ovalSegments; i++)
        {
            float angle = MathF.PI * 2 * i / ovalSegments;
            float px = ovalRx * MathF.Cos(angle);
            float py = ovalRy * MathF.Sin(angle);
            // Apply tilt rotation
            float rx = px * MathF.Cos(tilt) - py * MathF.Sin(tilt);
            float ry = px * MathF.Sin(tilt) + py * MathF.Cos(tilt);
            ovalPts[i] = (cx + rx, cy + ry);
        }
        r.DrawPolygon((255, 255, 255), ovalPts, alpha: 220);

        // Center text
        string centerText;
        int centerFs = Math.Max(14, h2 * 35 / 100);
        (int R, int G, int B) centerCol = isWild ? (40, 40, 40) : faceRgb;

        switch (value)
        {
            case "skip":
                centerText = "⊘";
                centerFs = Math.Max(16, h2 * 40 / 100);
                break;
            case "reverse":
                centerText = "↻";
                centerFs = Math.Max(16, h2 * 42 / 100);
                break;
            case "draw2":
                centerText = "+2";
                centerFs = Math.Max(14, h2 * 30 / 100);
                break;
            case "wild":
                centerText = "W";
                centerFs = Math.Max(14, h2 * 34 / 100);
                centerCol = (40, 40, 40);
                break;
            case "wild_draw4":
                centerText = "+4";
                centerFs = Math.Max(14, h2 * 30 / 100);
                centerCol = (40, 40, 40);
                break;
            default:
                centerText = value; // number 0-9
                break;
        }

        // Center text shadow + text
        r.DrawText(centerText, cx + 1, cy + 1, centerFs, (0, 0, 0), anchorX: "center", anchorY: "center", alpha: 80, bold: true);
        r.DrawText(centerText, cx, cy, centerFs, centerCol, anchorX: "center", anchorY: "center", bold: true);

        // Corner text (top-left and bottom-right)
        string cornerText = value switch
        {
            "skip" => "⊘",
            "reverse" => "↻",
            "draw2" => "+2",
            "wild" => "W",
            "wild_draw4" => "+4",
            _ => value,
        };
        int cornerFs = Math.Max(8, h2 * 14 / 100);
        var cornerCol = isWild ? (255, 255, 255) : (255, 255, 255);

        // Top-left corner
        r.DrawText(cornerText, x2 + w2 * 12 / 100, y2 + h2 * 10 / 100, cornerFs, cornerCol,
            anchorX: "center", anchorY: "center", bold: true);
        // Bottom-right corner
        r.DrawText(cornerText, x2 + w2 * 88 / 100, y2 + h2 * 90 / 100, cornerFs, cornerCol,
            anchorX: "center", anchorY: "center", bold: true);

        // Card border
        r.DrawRect((20, 20, 25), (x2, y2, w2, h2), width: 2, alpha: 220);

        // Inner white edge line
        r.DrawRect((255, 255, 255), (x2 + 3, y2 + 3, w2 - 6, h2 - 6), width: 1, alpha: 120);
    }

    // ───── Draw an emoji card ─────
    public static void DrawEmojiCard(Renderer r,
        (int x, int y, int w, int h) rect,
        string emoji, string title,
        (int r, int g, int b)? accentRgb = null,
        string corner = "", int maxTitleFontSize = 0)
    {
        var ac = accentRgb ?? (140, 140, 140);
        int x2 = rect.x, y2 = rect.y, w2 = rect.w, h2 = rect.h;

        // Shadow
        r.DrawRect((0, 0, 0), (x2 + 4, y2 + 4, w2, h2), alpha: 80);

        // Card face — off-white parchment
        r.DrawRect((248, 245, 238), (x2, y2, w2, h2), alpha: 250);

        // Accent header band (top 28%)
        r.DrawRect(ac, (x2, y2, w2, h2 * 28 / 100), alpha: 55);
        // Subtle tint on rest of card
        r.DrawRect(ac, (x2, y2 + h2 * 28 / 100, w2, h2 * 72 / 100), alpha: 12);

        // Inner inset line for premium look
        int inset = Math.Max(3, w2 * 6 / 100);
        r.DrawRect(ac, (x2 + inset, y2 + inset, w2 - 2 * inset, h2 - 2 * inset), width: 1, alpha: 45);

        // Accent outer border
        r.DrawRect(ac, (x2, y2, w2, h2), width: 3, alpha: 220);

        // Corner labels
        if (!string.IsNullOrEmpty(corner))
        {
            int cornerFs = Math.Max(9, h2 * 9 / 100);
            r.DrawText(corner, x2 + 8, y2 + 8, cornerFs, ac, bold: true, anchorX: "left", anchorY: "top");
            r.DrawText(corner, x2 + w2 - 8, y2 + h2 - 8, cornerFs, ac, bold: true, anchorX: "right", anchorY: "bottom");
        }

        // Emoji — large, centered higher
        int cx = x2 + w2 / 2, cy = y2 + h2 * 48 / 100;
        int nEmoji = 0;
        foreach (char ch in emoji ?? "")
            if (ch > 0x2000 && ch != 0xFE0F && ch != 0x200D) nEmoji++;
        nEmoji = Math.Max(1, nEmoji);
        int baseFs = Math.Max(20, h2 * 38 / 100);
        int emojiFs = Math.Min(baseFs, Math.Max(16, w2 * 78 / 100 / nEmoji));
        r.DrawText(emoji ?? "", cx + 1, cy + 1, emojiFs, (0, 0, 0), alpha: 60, anchorX: "center", anchorY: "center");
        r.DrawText(emoji ?? "", cx, cy, emojiFs, (255, 255, 255), anchorX: "center", anchorY: "center");

        // Title below emoji — accent colored
        string name = (title ?? "").Trim();
        if (name.Length > 0)
        {
            int fsz = Math.Max(10, h2 * 13 / 100);
            if (maxTitleFontSize > 0) fsz = Math.Min(fsz, maxTitleFontSize);
            string display = name.Length > 18 ? name[..18] : name;
            // Pill background behind title
            int pillW = display.Length * (fsz * 55 / 100) + 12;
            int pillH = fsz + 6;
            int pillX = cx - pillW / 2;
            int pillY = y2 + h2 * 82 / 100 - pillH / 2;
            r.DrawRect(ac, (pillX, pillY, pillW, pillH), alpha: 30);
            r.DrawText(display, cx, y2 + h2 * 82 / 100, fsz, (25, 25, 25), bold: true, anchorX: "center", anchorY: "center");
        }
    }

    // ───── Background dispatch ─────
    public static void DrawGameBackground(Renderer r, int w, int h, string theme)
    {
        string key = (theme ?? "").ToLowerInvariant().Replace(" ", "_").Replace("'", "");
        switch (key)
        {
            case "blackjack": BgBlackjack(r, w, h); break;
            case "texas_holdem":
            case "texas_holdem_poker": BgTexasHoldem(r, w, h); break;
            case "uno": BgUno(r, w, h); break;
            case "exploding_kittens": BgExplodingKittens(r, w, h); break;
            case "monopoly": BgMonopoly(r, w, h); break;
            case "unstable_unicorns": BgUnstableUnicorns(r, w, h); break;
            case "catan": BgCatan(r, w, h); break;
            case "risk": BgRisk(r, w, h); break;
            case "cluedo": BgCluedo(r, w, h); break;
            case "dnd":
            case "d&d": BgDnd(r, w, h); break;
            default: BgDefault(r, w, h); break;
        }
    }

    // ─────────────────────────────────────────────────────────────
    // Per-game backgrounds — full-fidelity port from Python
    // ─────────────────────────────────────────────────────────────

    private static void BgDefault(Renderer r, int w, int h)
    {
        r.DrawRect((10, 10, 14), (0, 0, w, h));
        r.DrawCircle((80, 80, 120), (w / 2, h / 2), Math.Min(w, h) * 40 / 100, alpha: 8);
    }

    private static void BgBlackjack(Renderer r, int w, int h)
    {
        r.DrawRect((3, 12, 22), (0, 0, w, h));
        int pad = Math.Min(w, h) * 5 / 100;
        int fw = w - 2 * pad, fh = h - 2 * pad;
        r.DrawRect((6, 88, 28), (pad, pad, fw, fh), alpha: 240);
        r.DrawRect((10, 110, 40), (pad + 6, pad + 6, fw - 12, fh - 12), alpha: 80);
        // Gold outer rail
        r.DrawRect((200, 158, 18), (pad / 4, pad / 4, w - pad / 2, h - pad / 2), width: 8, alpha: 200);
        r.DrawRect((240, 200, 50), (pad * 55 / 100, pad * 55 / 100, w - pad * 110 / 100, h - pad * 110 / 100), width: 2, alpha: 80);
        // Chip stacks
        (int cx, int cy, (int, int, int) col)[] chips = [
            (w * 10 / 100, h * 82 / 100, (200, 30, 30)),
            (w * 90 / 100, h * 18 / 100, (30, 30, 200)),
            (w * 10 / 100, h * 18 / 100, (200, 175, 0)),
            (w * 90 / 100, h * 82 / 100, (20, 175, 30)),
        ];
        foreach (var (cx2, cy2, col) in chips)
        {
            for (int i = 0; i < 3; i++)
            {
                r.DrawCircle(col, (cx2, cy2 - i * 5), 13, alpha: 55);
                r.DrawCircle((255, 255, 255), (cx2, cy2 - i * 5), 13, width: 1, alpha: 28);
            }
        }
    }

    private static void BgTexasHoldem(Renderer r, int w, int h)
    {
        r.DrawRect((18, 10, 6), (0, 0, w, h));
        r.DrawRect((80, 48, 16), (0, 0, w, h));
        // Wood grain
        for (int i = 0; i < 7; i++)
        {
            int yp = h * (2 * i + 1) / 14;
            r.DrawLine((100, 65, 22), (0, yp), (w, yp), width: 1, alpha: 16);
        }
        int rail = Math.Min(w, h) * 10 / 100;
        r.DrawRect((8, 82, 30), (rail, rail, w - 2 * rail, h - 2 * rail));
        r.DrawCircle((12, 100, 38), (w / 2, h / 2), Math.Min(w, h) * 33 / 100, alpha: 35);
        r.DrawRect((130, 90, 28), (0, 0, w, h), width: 4, alpha: 140);
        r.DrawRect((48, 30, 10), (rail - 4, rail - 4, w - 2 * rail + 8, h - 2 * rail + 8), width: 3, alpha: 180);
        // Community card placeholders
        int cw2 = Math.Max(48, w * 62 / 1000), ch2 = Math.Max(68, h * 135 / 1000);
        int totalCw = 5 * cw2 + 4 * 8;
        int cx0 = w / 2 - totalCw / 2, cy0 = h / 2 - ch2 / 2;
        for (int i = 0; i < 5; i++)
            r.DrawRect((20, 110, 45), (cx0 + i * (cw2 + 8), cy0, cw2, ch2), width: 2, alpha: 55);
        // Pot marker
        r.DrawCircle((200, 160, 28), (w / 2, h * 62 / 100), 16, alpha: 65);
        r.DrawCircle((240, 200, 60), (w / 2, h * 62 / 100), 16, width: 2, alpha: 80);
    }

    private static void BgUno(Renderer r, int w, int h)
    {
        r.DrawRect((6, 6, 22), (0, 0, w, h));
        r.DrawRect((180, 20, 20), (0, 0, w / 2, h / 2), alpha: 22);
        r.DrawRect((20, 160, 20), (w / 2, h / 2, w / 2, h / 2), alpha: 22);
        r.DrawRect((20, 60, 200), (w / 2, 0, w / 2, h / 2), alpha: 22);
        r.DrawRect((220, 180, 0), (0, h / 2, w / 2, h / 2), alpha: 22);
        (int, int, int)[] stripeColors = [(220, 40, 40), (40, 180, 40), (40, 80, 220), (230, 190, 0)];
        for (int i = 0; i < stripeColors.Length; i++)
        {
            int offset = w * 14 * i / 100;
            r.DrawLine(stripeColors[i], (offset, 0), (offset + h * 85 / 100, h), width: 38, alpha: 7);
        }
        // Centre oval
        r.DrawCircle((10, 10, 30), (w / 2, h / 2), Math.Min(w, h) * 30 / 100, alpha: 180);
        r.DrawCircle((8, 8, 26), (w / 2, h / 2), Math.Min(w, h) * 27 / 100);
        // Colour ring
        foreach (var col in stripeColors)
            r.DrawCircle(col, (w / 2, h / 2), Math.Min(w, h) * 30 / 100, width: 4, alpha: 110);
    }

    private static void BgExplodingKittens(Renderer r, int w, int h)
    {
        r.DrawRect((8, 4, 16), (0, 0, w, h));
        // Hot orange edges
        r.DrawRect((180, 60, 0), (0, 0, w, 4), alpha: 200);
        r.DrawRect((180, 60, 0), (0, h - 4, w, 4), alpha: 200);
        r.DrawRect((180, 60, 0), (0, 0, 4, h), alpha: 110);
        r.DrawRect((180, 60, 0), (w - 4, 0, 4, h), alpha: 110);
        // Explosion bursts in corners
        (int bx, int by)[] corners = [
            (w * 8 / 100, h * 12 / 100), (w * 92 / 100, h * 12 / 100),
            (w * 8 / 100, h * 88 / 100), (w * 92 / 100, h * 88 / 100)
        ];
        foreach (var (bx, by) in corners)
        {
            r.DrawCircle((200, 80, 0), (bx, by), Math.Min(w, h) * 12 / 100, alpha: 20);
            r.DrawCircle((240, 140, 0), (bx, by), Math.Min(w, h) * 7 / 100, alpha: 28);
            r.DrawCircle((255, 220, 0), (bx, by), Math.Min(w, h) * 3 / 100, alpha: 55);
        }
        r.DrawCircle((12, 6, 20), (w / 2, h / 2), Math.Min(w, h) * 35 / 100, alpha: 90);
    }

    private static void BgMonopoly(Renderer r, int w, int h)
    {
        r.DrawRect((222, 212, 178), (0, 0, w, h));
        r.DrawRect((22, 116, 56), (0, 0, w, h), width: 14);
        r.DrawRect((200, 188, 138), (10, 10, w - 20, h - 20), width: 3, alpha: 180);
        // Paper texture
        for (int i = 0; i < 20; i++)
            r.DrawLine((185, 175, 145), (0, h * i / 20), (w, h * i / 20), width: 1, alpha: 10);
        // Corner dots
        foreach (var (cx, cy) in new[] { (18, 18), (w - 18, 18), (18, h - 18), (w - 18, h - 18) })
            r.DrawCircle((22, 116, 56), (cx, cy), 10, alpha: 150);
    }

    private static void BgUnstableUnicorns(Renderer r, int w, int h)
    {
        r.DrawRect((14, 6, 30), (0, 0, w, h));
        // Rainbow bands
        (int, int, int)[] rainbow = [(255, 60, 60), (255, 150, 0), (255, 230, 0), (60, 210, 60), (60, 100, 255), (190, 0, 255)];
        int bw = Math.Max(1, w / rainbow.Length), bh = Math.Max(1, h / rainbow.Length);
        for (int i = 0; i < rainbow.Length; i++)
        {
            int x0 = i * bw, y0 = i * bh;
            int extra = i == rainbow.Length - 1 ? w - rainbow.Length * bw : 0;
            r.DrawRect(rainbow[i], (x0, 0, bw + extra, 5), alpha: 155);
            r.DrawRect(rainbow[i], (x0, h - 5, bw + extra, 5), alpha: 155);
            r.DrawRect(rainbow[i], (0, y0, 5, bh), alpha: 75);
            r.DrawRect(rainbow[i], (w - 5, y0, 5, bh), alpha: 75);
        }
        // Magic circles
        r.DrawCircle((180, 80, 240), (w / 2, h / 2), Math.Min(w, h) * 40 / 100, alpha: 10);
        r.DrawCircle((255, 180, 100), (w / 2, h / 2), Math.Min(w, h) * 26 / 100, alpha: 7);
        r.DrawCircle((200, 100, 255), (w / 2, h / 2), Math.Min(w, h) * 12 / 100, alpha: 9);
    }

    private static void BgCatan(Renderer r, int w, int h)
    {
        // Deep ocean base
        r.DrawRect((4, 28, 58), (0, 0, w, h));

        // Animated-look wave bands — lighter turquoise towards center
        int steps = 48;
        for (int i = 0; i < steps; i++)
        {
            float t = i / (float)Math.Max(1, steps - 1);
            int bandY = (int)(h * (i / (float)(steps + 4)));
            int bandH = (int)(h / (float)(steps + 4)) + 2;
            r.DrawRect((6, 55 + (int)(65 * t), 95 + (int)(85 * t)),
                       (0, bandY, w, bandH), alpha: 12 + (int)(35 * t));
        }

        // Diagonal subtle wave streaks
        for (int i = 0; i < 8; i++)
        {
            int sy = h * i / 8;
            int sx = -(w / 4) + (i * w / 12);
            r.DrawRect((30, 90, 140), (sx, sy, w / 3, 2), alpha: 15);
        }

        // Warm sandy shoreline at the bottom
        int sandH = Math.Max(24, h * 10 / 100);
        // Sand gradient (3 layers)
        r.DrawRect((210, 185, 135), (0, h - sandH, w, sandH), alpha: 210);
        r.DrawRect((195, 168, 118), (0, h - sandH, w, sandH * 2 / 5), alpha: 160);
        r.DrawRect((180, 152, 105), (0, h - sandH, w, sandH / 6), alpha: 120);

        // Foam line (two passes for layered look)
        r.DrawRect((240, 240, 230), (0, h - sandH - 3, w, 3), alpha: 50);
        r.DrawRect((200, 230, 240), (0, h - sandH - 1, w, 1), alpha: 35);

        // Top sky/horizon strip — subtle warm glow on horizon
        int skyH = Math.Max(20, h * 6 / 100);
        r.DrawRect((15, 35, 62), (0, 0, w, skyH), alpha: 60);
        r.DrawRect((25, 50, 80), (0, 0, w, skyH / 2), alpha: 40);

        // Palm tree silhouettes on shore edges
        int palmFs = Math.Max(14, h / 35);
        r.DrawText("🌴", (int)(w * 0.03), h - sandH - palmFs / 2, palmFs, (255, 255, 255), anchorX: "center", anchorY: "center");
        r.DrawText("🌴", (int)(w * 0.10), h - sandH - palmFs / 3, (int)(palmFs * 0.8), (255, 255, 255), anchorX: "center", anchorY: "center");
        r.DrawText("🌴", (int)(w * 0.92), h - sandH - palmFs / 2, palmFs, (255, 255, 255), anchorX: "center", anchorY: "center");
        r.DrawText("🌴", (int)(w * 0.97), h - sandH - palmFs / 3, (int)(palmFs * 0.75), (255, 255, 255), anchorX: "center", anchorY: "center");

        // Small wave emoji accents in ocean corners
        int waveFs = Math.Max(10, h / 55);
        r.DrawText("🌊", (int)(w * 0.02), (int)(h * 0.15), waveFs, (255, 255, 255), anchorX: "center", anchorY: "center");
        r.DrawText("🌊", (int)(w * 0.95), (int)(h * 0.25), waveFs, (255, 255, 255), anchorX: "center", anchorY: "center");
        r.DrawText("🌊", (int)(w * 0.06), (int)(h * 0.55), waveFs, (255, 255, 255), anchorX: "center", anchorY: "center");
    }

    private static void BgRisk(Renderer r, int w, int h)
    {
        r.DrawRect((8, 22, 60), (0, 0, w, h));
        ((int, int, int, int) rect, (int, int, int) col)[] regions = [
            ((w * 5 / 100, h * 15 / 100, w * 22 / 100, h * 35 / 100), (200, 100, 40)),
            ((w * 12 / 100, h * 55 / 100, w * 14 / 100, h * 26 / 100), (190, 90, 35)),
            ((w * 38 / 100, h * 12 / 100, w * 28 / 100, h * 28 / 100), (175, 78, 28)),
            ((w * 38 / 100, h * 44 / 100, w * 20 / 100, h * 38 / 100), (120, 158, 38)),
            ((w * 56 / 100, h * 12 / 100, w * 30 / 100, h * 44 / 100), (158, 118, 58)),
            ((w * 68 / 100, h * 60 / 100, w * 16 / 100, h * 17 / 100), (38, 138, 78)),
        ];
        foreach (var (rect, col) in regions)
        {
            r.DrawRect(col, rect, alpha: 88);
            r.DrawRect((255, 255, 255), rect, width: 1, alpha: 18);
        }
        for (int i = 0; i < 8; i++)
            r.DrawLine((100, 140, 200), (0, h * i / 8), (w, h * i / 8), width: 1, alpha: 18);
        for (int i = 0; i < 12; i++)
            r.DrawLine((100, 140, 200), (w * i / 12, 0), (w * i / 12, h), width: 1, alpha: 18);
        r.DrawRect((178, 138, 58), (0, 0, w, h), width: 6, alpha: 145);
    }

    private static void BgCluedo(Renderer r, int w, int h)
    {
        r.DrawRect((22, 8, 8), (0, 0, w, h));
        r.DrawRect((15, 5, 5), (w * 5 / 100, h * 5 / 100, w * 90 / 100, h * 90 / 100), alpha: 200);
        r.DrawRect((200, 158, 28), (0, 0, w, h), width: 8, alpha: 200);
        r.DrawRect((148, 108, 18), (8, 8, w - 16, h - 16), width: 3, alpha: 140);
        r.DrawRect((218, 178, 48), (13, 13, w - 26, h - 26), width: 1, alpha: 75);
        // Room grid
        int pw3 = w / 3, ph3 = h / 3;
        for (int row = 0; row < 3; row++)
            for (int col = 0; col < 3; col++)
                r.DrawRect((30, 10, 10), (col * pw3, row * ph3, pw3, ph3), width: 1, alpha: 38);
        // Corner ornaments
        foreach (var (cx, cy) in new[] { (w * 7 / 100, h * 7 / 100), (w * 93 / 100, h * 7 / 100), (w * 7 / 100, h * 93 / 100), (w * 93 / 100, h * 93 / 100) })
        {
            r.DrawCircle((200, 158, 28), (cx, cy), 11, alpha: 115);
            r.DrawCircle((240, 198, 58), (cx, cy), 7, alpha: 95);
        }
    }

    private static void BgDnd(Renderer r, int w, int h)
    {
        r.DrawRect((8, 6, 22), (0, 0, w, h));
        r.DrawRect((60, 20, 120), (0, 0, w, h * 12 / 100), alpha: 28);
        r.DrawRect((60, 20, 120), (0, h - h * 12 / 100, w, h * 12 / 100), alpha: 28);
        int cx = w / 2, cy = h / 2;
        (float frac, int a, int wd)[] rings = [(0.40f, 55, 2), (0.32f, 38, 1), (0.24f, 48, 2), (0.16f, 35, 1)];
        foreach (var (frac, a, wd) in rings)
            r.DrawCircle((120, 60, 200), (cx, cy), (int)(Math.Min(w, h) * frac), width: wd, alpha: a);
        // Rune points
        for (int i = 0; i < 8; i++)
        {
            double ang = i * Math.PI / 4;
            int rx = (int)(cx + Math.Cos(ang) * Math.Min(w, h) * 0.38);
            int ry = (int)(cy + Math.Sin(ang) * Math.Min(w, h) * 0.38);
            r.DrawCircle((148, 78, 218), (rx, ry), 5, alpha: 88);
        }
    }
}
