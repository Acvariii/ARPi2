using System;
using Microsoft.Xna.Framework;
using Microsoft.Xna.Framework.Graphics;
using SkiaSharp;

namespace ARPi2.Sharp.Core;

// ════════════════════════════════════════════════════════════════
//  UUCardArt — Procedural card illustrations for Unstable Unicorns
//
//  Each card kind has 4 distinct illustration variants drawn
//  entirely from layered 2D primitives (rects, circles, lines).
//  Visual density: ~40-80 draw calls per card for
//  production-quality procedural art.
// ════════════════════════════════════════════════════════════════

public static class UUCardArt
{
    /// <summary>Draw a rich illustration for the given UU card kind.</summary>
    /// <param name="variant">0-3 for the visual variant.</param>
    /// <param name="area">The inner drawable area for the illustration.</param>
    public static void DrawIllustration(Renderer r, string kind, int variant,
        (int x, int y, int w, int h) area, string? cardName = null)
    {
        int x = area.x, y = area.y, w = area.w, h = area.h;
        int cx = x + w / 2, cy = y + h / 2;
        int v = ((variant % 4) + 4) % 4;

        // ── SkiaSharp-rendered atmospheric background (anti-aliased, cached) ──
        DrawSkiaBackground(r, kind, v, x, y, w, h, cardName);

        switch (kind.ToLowerInvariant())
        {
            case "baby_unicorn":  DrawBabyUnicorn(r, v, x, y, w, h, cx, cy); break;
            case "unicorn":       DrawUnicorn(r, v, x, y, w, h, cx, cy, cardName); break;
            case "upgrade":       DrawUpgrade(r, v, x, y, w, h, cx, cy); break;
            case "downgrade":     DrawDowngrade(r, v, x, y, w, h, cx, cy); break;
            case "magic":         DrawMagic(r, v, x, y, w, h, cx, cy); break;
            case "instant":       DrawInstant(r, v, x, y, w, h, cx, cy); break;
            case "neigh":         DrawNeigh(r, v, x, y, w, h, cx, cy); break;
            case "super_neigh":   DrawSuperNeigh(r, v, x, y, w, h, cx, cy); break;
            default:              DrawGenericUU(r, x, y, w, h, cx, cy); break;
        }
    }

    // ════════════════════════════════════════════════════════════════
    //  SkiaSharp Rendered Backgrounds — smooth anti-aliased vector art
    // ════════════════════════════════════════════════════════════════

    private static void DrawSkiaBackground(Renderer r, string kind, int variant, int x, int y, int w, int h, string? cardName = null)
    {
        string suffix = string.IsNullOrEmpty(cardName) ? "" : $"_{cardName.GetHashCode():X8}";
        string key = $"uuart_{kind}_{variant}_{w}_{h}{suffix}";
        var tex = r.GetOrCreateSkiaTexture(key, w, h, (canvas, cw, ch) =>
        {
            RenderSkiaBg(canvas, kind, variant, cw, ch, cardName);
        });
        r.DrawTexture(tex, new Rectangle(x, y, w, h));
    }

    private static void RenderSkiaBg(SKCanvas c, string kind, int variant, int w, int h, string? cardName = null)
    {
        float cx = w / 2f, cy = h / 2f;
        float s = MathF.Min(w, h);
        string k = kind.ToLowerInvariant();

        var (bgDark, bgMid, bgLight, glow, accent) = k switch
        {
            "baby_unicorn" => (new SKColor(38, 12, 42),  new SKColor(70, 25, 80),  new SKColor(130, 60, 150), new SKColor(243, 166, 255), new SKColor(255, 210, 255)),
            "unicorn"      => (new SKColor(12, 8, 42),   new SKColor(30, 20, 80),  new SKColor(60, 50, 150),  new SKColor(140, 120, 255), new SKColor(184, 230, 255)),
            "upgrade"      => (new SKColor(6, 28, 14),   new SKColor(14, 55, 30),  new SKColor(30, 100, 60),  new SKColor(80, 220, 130),  new SKColor(180, 255, 200)),
            "downgrade"    => (new SKColor(38, 8, 8),    new SKColor(70, 16, 16),  new SKColor(130, 30, 30),  new SKColor(240, 70, 70),   new SKColor(255, 160, 160)),
            "magic"        => (new SKColor(10, 10, 42),  new SKColor(22, 22, 80),  new SKColor(50, 50, 150),  new SKColor(100, 140, 255), new SKColor(180, 200, 255)),
            "instant"      => (new SKColor(35, 25, 6),   new SKColor(65, 48, 12),  new SKColor(110, 85, 25),  new SKColor(245, 200, 60),  new SKColor(255, 240, 160)),
            "neigh"        => (new SKColor(18, 18, 18),  new SKColor(35, 35, 35),  new SKColor(65, 65, 65),   new SKColor(180, 180, 180), new SKColor(220, 220, 220)),
            "super_neigh"  => (new SKColor(18, 8, 28),   new SKColor(35, 16, 55),  new SKColor(60, 30, 90),   new SKColor(180, 80, 255),  new SKColor(220, 160, 255)),
            _              => (new SKColor(14, 10, 28),  new SKColor(28, 20, 55),  new SKColor(55, 40, 100),  new SKColor(150, 120, 255), new SKColor(200, 180, 255)),
        };

        // Per-card palette override for unicorn kind
        if (k == "unicorn" && !string.IsNullOrEmpty(cardName))
        {
            string cn = cardName.ToLowerInvariant();
            if (cn.Contains("zombie")) { bgDark = new SKColor(10, 22, 8); bgMid = new SKColor(25, 50, 18); bgLight = new SKColor(50, 100, 35); glow = new SKColor(80, 220, 60); accent = new SKColor(140, 255, 100); }
            else if (cn.Contains("phoenix")) { bgDark = new SKColor(38, 10, 4); bgMid = new SKColor(70, 22, 8); bgLight = new SKColor(140, 50, 15); glow = new SKColor(255, 140, 40); accent = new SKColor(255, 200, 80); }
            else if (cn.Contains("shark")) { bgDark = new SKColor(4, 14, 28); bgMid = new SKColor(10, 30, 55); bgLight = new SKColor(20, 55, 100); glow = new SKColor(60, 140, 220); accent = new SKColor(140, 200, 255); }
            else if (cn.Contains("mermaid")) { bgDark = new SKColor(4, 20, 28); bgMid = new SKColor(10, 45, 60); bgLight = new SKColor(25, 90, 120); glow = new SKColor(80, 200, 200); accent = new SKColor(160, 255, 230); }
            else if (cn.Contains("llama")) { bgDark = new SKColor(32, 18, 8); bgMid = new SKColor(60, 38, 16); bgLight = new SKColor(110, 75, 35); glow = new SKColor(235, 180, 100); accent = new SKColor(255, 220, 160); }
            else if (cn.Contains("rhino")) { bgDark = new SKColor(20, 20, 22); bgMid = new SKColor(40, 40, 45); bgLight = new SKColor(80, 80, 90); glow = new SKColor(160, 160, 180); accent = new SKColor(200, 200, 220); }
            else if (cn.Contains("black_knight")) { bgDark = new SKColor(8, 4, 14); bgMid = new SKColor(18, 10, 30); bgLight = new SKColor(35, 20, 60); glow = new SKColor(100, 50, 160); accent = new SKColor(160, 100, 220); }
            else if (cn.Contains("stabby")) { bgDark = new SKColor(30, 4, 4); bgMid = new SKColor(60, 10, 10); bgLight = new SKColor(120, 20, 20); glow = new SKColor(255, 50, 50); accent = new SKColor(255, 120, 120); }
            else if (cn.Contains("chainsaw")) { bgDark = new SKColor(28, 14, 4); bgMid = new SKColor(55, 28, 8); bgLight = new SKColor(100, 55, 18); glow = new SKColor(240, 160, 40); accent = new SKColor(255, 200, 80); }
            else if (cn.Contains("dark_angel")) { bgDark = new SKColor(10, 6, 18); bgMid = new SKColor(22, 14, 38); bgLight = new SKColor(45, 28, 70); glow = new SKColor(120, 80, 200); accent = new SKColor(180, 140, 255); }
            else if (cn.Contains("queen_bee")) { bgDark = new SKColor(28, 22, 4); bgMid = new SKColor(55, 45, 8); bgLight = new SKColor(100, 85, 15); glow = new SKColor(240, 200, 40); accent = new SKColor(255, 230, 100); }
            else if (cn.Contains("cob") || cn.Contains("corn")) { bgDark = new SKColor(28, 24, 6); bgMid = new SKColor(55, 48, 12); bgLight = new SKColor(100, 88, 28); glow = new SKColor(240, 210, 60); accent = new SKColor(255, 240, 120); }
            else if (cn.Contains("seductive")) { bgDark = new SKColor(32, 4, 14); bgMid = new SKColor(65, 10, 28); bgLight = new SKColor(120, 20, 50); glow = new SKColor(255, 60, 120); accent = new SKColor(255, 140, 180); }
            else if (cn.Contains("americorn")) { bgDark = new SKColor(10, 8, 24); bgMid = new SKColor(22, 18, 50); bgLight = new SKColor(45, 35, 95); glow = new SKColor(100, 80, 200); accent = new SKColor(200, 180, 255); }
            else if (cn.Contains("torpedo")) { bgDark = new SKColor(6, 14, 24); bgMid = new SKColor(14, 30, 50); bgLight = new SKColor(28, 60, 95); glow = new SKColor(80, 160, 240); accent = new SKColor(160, 210, 255); }
            else if (cn.Contains("narwhal")) { bgDark = new SKColor(4, 16, 28); bgMid = new SKColor(10, 35, 55); bgLight = new SKColor(22, 70, 105); glow = new SKColor(60, 180, 230); accent = new SKColor(140, 220, 255); }
            else if (cn.Contains("fertile")) { bgDark = new SKColor(28, 10, 24); bgMid = new SKColor(55, 22, 48); bgLight = new SKColor(100, 45, 88); glow = new SKColor(235, 130, 200); accent = new SKColor(255, 180, 230); }
            else if (cn.Contains("flying")) { bgDark = new SKColor(6, 12, 30); bgMid = new SKColor(14, 25, 60); bgLight = new SKColor(30, 50, 115); glow = new SKColor(100, 160, 255); accent = new SKColor(180, 210, 255); }
        }

        // 1. Deep radial gradient background
        using (var paint = new SKPaint { IsAntialias = true })
        {
            float r = s * 0.7f;
            paint.Shader = SKShader.CreateRadialGradient(
                new SKPoint(cx, cy), r,
                new[] { bgLight, bgMid, bgDark, new SKColor(0, 0, 0) },
                new float[] { 0f, 0.35f, 0.7f, 1f },
                SKShaderTileMode.Clamp);
            c.DrawRect(0, 0, w, h, paint);
        }

        // 2. Central glow — soft radial
        using (var paint = new SKPaint { IsAntialias = true })
        {
            paint.Shader = SKShader.CreateRadialGradient(
                new SKPoint(cx, cy * 0.85f), s * 0.38f,
                new[] { glow.WithAlpha(255), glow.WithAlpha(255), SKColors.Transparent },
                new float[] { 0f, 0.45f, 1f },
                SKShaderTileMode.Clamp);
            c.DrawRect(0, 0, w, h, paint);
        }

        // 3. Flowing energy arcs — magical unicorn theme
        using (var paint = new SKPaint { IsAntialias = true, Style = SKPaintStyle.Stroke, StrokeWidth = 1.2f })
        {
            int arcCount = Math.Max(6, w / 12);
            for (int i = 0; i < arcCount; i++)
            {
                float t = (float)i / arcCount;
                byte a = (byte)(60 + (i % 5) * 20);
                paint.Color = (i % 3 == 0) ? accent.WithAlpha(a) : glow.WithAlpha(a);

                using var path = new SKPath();
                // Graceful S-curves (more magical than straight lines)
                float startX = w * t;
                float startY = 0;
                float endX = w * (1f - t);
                float endY = h;
                float ctrl1X = cx + MathF.Sin(i * 1.2f + variant * 0.5f) * s * 0.25f;
                float ctrl1Y = cy * 0.4f;
                float ctrl2X = cx - MathF.Cos(i * 0.9f + variant * 0.8f) * s * 0.25f;
                float ctrl2Y = cy * 1.5f;
                path.MoveTo(startX, startY);
                path.CubicTo(ctrl1X, ctrl1Y, ctrl2X, ctrl2Y, endX, endY);
                c.DrawPath(path, paint);
            }
        }

        // 4. Magical sparkle clouds — scattered soft circles
        using (var paint = new SKPaint { IsAntialias = true, MaskFilter = SKMaskFilter.CreateBlur(SKBlurStyle.Normal, s * 0.025f) })
        {
            int cloudCount = 5 + variant;
            for (int i = 0; i < cloudCount; i++)
            {
                float fx = cx + MathF.Cos(i * 2.3f + variant * 0.6f) * s * 0.35f;
                float fy = cy + MathF.Sin(i * 1.8f + variant * 1.1f) * s * 0.3f;
                float fr = s * (0.07f + (i % 3) * 0.035f);

                paint.Shader = SKShader.CreateRadialGradient(
                    new SKPoint(fx, fy), fr,
                    new[] { accent.WithAlpha(240), glow.WithAlpha(230), SKColors.Transparent },
                    new float[] { 0f, 0.5f, 1f },
                    SKShaderTileMode.Clamp);
                c.DrawCircle(fx, fy, fr, paint);
                paint.Shader = null;
            }
        }

        // 5. Soft spotlight cone from top
        using (var paint = new SKPaint { IsAntialias = true })
        {
            using var path = new SKPath();
            float spotCx = cx + (variant % 2 == 0 ? -1 : 1) * w * 0.08f;
            path.MoveTo(spotCx - w * 0.05f, 0);
            path.LineTo(spotCx - w * 0.22f, h);
            path.LineTo(spotCx + w * 0.22f, h);
            path.LineTo(spotCx + w * 0.05f, 0);
            path.Close();

            paint.Shader = SKShader.CreateLinearGradient(
                new SKPoint(spotCx, 0), new SKPoint(spotCx, h),
                new[] { accent.WithAlpha(200), glow.WithAlpha(190), SKColors.Transparent },
                new float[] { 0f, 0.55f, 1f },
                SKShaderTileMode.Clamp);
            c.DrawPath(path, paint);
        }

        // 6. Edge vignette
        using (var paint = new SKPaint { IsAntialias = true })
        {
            paint.Shader = SKShader.CreateLinearGradient(
                new SKPoint(0, 0), new SKPoint(0, h * 0.22f),
                new[] { new SKColor(0, 0, 0, 45), SKColors.Transparent },
                SKShaderTileMode.Clamp);
            c.DrawRect(0, 0, w, h * 0.22f, paint);

            paint.Shader = SKShader.CreateLinearGradient(
                new SKPoint(0, h * 0.78f), new SKPoint(0, h),
                new[] { SKColors.Transparent, new SKColor(0, 0, 0, 55) },
                SKShaderTileMode.Clamp);
            c.DrawRect(0, h * 0.78f, w, h * 0.22f, paint);

            paint.Shader = SKShader.CreateLinearGradient(
                new SKPoint(0, 0), new SKPoint(w * 0.18f, 0),
                new[] { new SKColor(0, 0, 0, 35), SKColors.Transparent },
                SKShaderTileMode.Clamp);
            c.DrawRect(0, 0, w * 0.18f, h, paint);

            paint.Shader = SKShader.CreateLinearGradient(
                new SKPoint(w * 0.82f, 0), new SKPoint(w, 0),
                new[] { SKColors.Transparent, new SKColor(0, 0, 0, 35) },
                SKShaderTileMode.Clamp);
            c.DrawRect(w * 0.82f, 0, w * 0.18f, h, paint);
        }

        // 7. Film grain
        using (var paint = new SKPaint { IsAntialias = false })
        {
            for (int tx = 0; tx < w; tx += 5)
                for (int ty = 0; ty < h; ty += 5)
                {
                    int seed = ((tx * 31 + ty * 97 + variant * 17) & 0x3FF);
                    if (seed < 14)
                    {
                        paint.Color = new SKColor(255, 255, 255, (byte)(35 + (seed & 3) * 12));
                        c.DrawPoint(tx, ty, paint);
                    }
                    else if (seed > 1012)
                    {
                        paint.Color = new SKColor(0, 0, 0, (byte)(40 + (seed & 3) * 12));
                        c.DrawPoint(tx, ty, paint);
                    }
                }
        }

        // 8. Floating dust motes
        using (var paint = new SKPaint { IsAntialias = true })
        {
            int moteCount = 7 + variant;
            for (int i = 0; i < moteCount; i++)
            {
                float mx = (((i * 131 + variant * 37) % w) + w) % w;
                float my = (((i * 83 + variant * 47) % h) + h) % h;
                float mr = 0.5f + (i % 3) * 0.35f;
                byte ma = (byte)(18 + (i % 5) * 7);
                paint.Color = accent.WithAlpha(ma);
                c.DrawCircle(mx, my, mr, paint);
            }
        }
    }

    // ═══════════════════════════════════════════════════════════
    //  BABY UNICORN — cute, innocent, pastel sparkle
    // ═══════════════════════════════════════════════════════════

    private static void DrawBabyUnicorn(Renderer r, int v, int x, int y, int w, int h, int cx, int cy)
    {
        switch (v)
        {
            case 0: DrawBaby_SleepingFoal(r, x, y, w, h, cx, cy); break;
            case 1: DrawBaby_StarCradle(r, x, y, w, h, cx, cy); break;
            case 2: DrawBaby_RainbowBubble(r, x, y, w, h, cx, cy); break;
            case 3: DrawBaby_FlowerField(r, x, y, w, h, cx, cy); break;
        }
    }

    // Variant 0: Sleeping baby unicorn curled up
    private static void DrawBaby_SleepingFoal(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Moon crescent in corner
        int moonR = s * 18 / 100;
        int moonCx = x + w * 80 / 100, moonCy = y + h * 18 / 100;
        r.DrawCircle((255, 240, 180), (moonCx, moonCy), moonR, alpha: 220);
        r.DrawCircle((40, 20, 60), (moonCx + moonR / 3, moonCy - moonR / 4), moonR * 85 / 100, alpha: 255); // shadow bite
        // Moon glow
        r.DrawCircle((255, 240, 150), (moonCx, moonCy), moonR + s * 4 / 100, width: 1, alpha: 60);

        // Stars
        DrawSparkle4(r, x + w * 20 / 100, y + h * 12 / 100, s * 3 / 100, (255, 245, 200), 180);
        DrawSparkle4(r, x + w * 60 / 100, y + h * 8 / 100, s * 2 / 100, (255, 240, 220), 150);
        DrawSparkle4(r, x + w * 35 / 100, y + h * 22 / 100, s * 2 / 100, (230, 200, 255), 130);

        // Body — curled oval
        int bodyW = s * 40 / 100, bodyH = s * 24 / 100;
        int bodyCx = cx, bodyCy = cy + s * 10 / 100;
        r.DrawCircle((220, 180, 240), (bodyCx, bodyCy), bodyW * 55 / 100, alpha: 255);
        // Body highlight
        r.DrawCircle((240, 210, 255), (bodyCx - bodyW / 5, bodyCy - bodyH / 4), bodyW * 25 / 100, alpha: 200);

        // Head — smaller circle tucked into body
        int headR = s * 14 / 100;
        int headCx = bodyCx - bodyW / 4, headCy = bodyCy - bodyH * 60 / 100;
        r.DrawCircle((230, 195, 250), (headCx, headCy), headR, alpha: 255);
        r.DrawCircle((245, 220, 255), (headCx - headR / 3, headCy - headR / 3), headR / 2, alpha: 180);

        // Horn — small, pink
        int hornH = s * 10 / 100;
        DrawHorn(r, headCx, headCy - headR, hornH, (255, 180, 220), (255, 220, 240));

        // Ears
        DrawEar(r, headCx - headR * 6 / 10, headCy - headR * 8 / 10, s * 5 / 100, (215, 175, 235), (255, 200, 230));
        DrawEar(r, headCx + headR * 2 / 10, headCy - headR * 9 / 10, s * 5 / 100, (215, 175, 235), (255, 200, 230));

        // Closed eyes — sleeping lines
        int eyeY = headCy - headR / 5;
        r.DrawLine((120, 80, 140), (headCx - headR * 4 / 10, eyeY), (headCx - headR * 1 / 10, eyeY + 2), width: 1, alpha: 220);
        r.DrawLine((120, 80, 140), (headCx + headR * 1 / 10, eyeY), (headCx + headR * 4 / 10, eyeY + 2), width: 1, alpha: 220);

        // Zzz floating text
        r.DrawText("z", cx + s * 12 / 100, cy - s * 22 / 100, Math.Max(8, s * 8 / 100), (200, 180, 255), alpha: 150, anchorX: "center", anchorY: "center");
        r.DrawText("z", cx + s * 18 / 100, cy - s * 30 / 100, Math.Max(7, s * 6 / 100), (180, 160, 240), alpha: 120, anchorX: "center", anchorY: "center");
        r.DrawText("z", cx + s * 22 / 100, cy - s * 36 / 100, Math.Max(6, s * 5 / 100), (160, 140, 220), alpha: 90, anchorX: "center", anchorY: "center");

        // Tail — curled
        for (int i = 0; i < 8; i++)
        {
            double ang = Math.PI * 0.3 + i * 0.35;
            int tailR = s * (8 + i) / 100;
            int tx = bodyCx + bodyW * 35 / 100 + (int)(Math.Cos(ang) * tailR / 3);
            int ty = bodyCy - (int)(Math.Sin(ang) * tailR / 2);
            r.DrawCircle((200 + i * 4, 160 + i * 6, 220 + i * 3), (tx, ty), Math.Max(1, s * 2 / 100 - i / 3), alpha: 200 - i * 10);
        }

        // Pastel sparkles around body
        DrawSparkle4(r, bodyCx - bodyW / 2 - s * 4 / 100, bodyCy, s * 2 / 100, (255, 200, 255), 120);
        DrawSparkle4(r, bodyCx + bodyW / 2 + s * 3 / 100, bodyCy - bodyH / 2, s * 2 / 100, (200, 220, 255), 110);
    }

    // Variant 1: Baby in star cradle
    private static void DrawBaby_StarCradle(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Background stars scattered
        for (int i = 0; i < 12; i++)
        {
            int sx = x + ((i * 67 + 13) % w);
            int sy = y + ((i * 43 + 7) % h);
            int ss = Math.Max(2, s * (1 + i % 3) / 100);
            var sc = i % 3 == 0 ? (255, 240, 200) : i % 3 == 1 ? (220, 200, 255) : (200, 230, 255);
            DrawSparkle4(r, sx, sy, ss, sc, 100 + (i % 5) * 20);
        }

        // Crescent moon cradle
        int cradleW = s * 50 / 100, cradleH = s * 20 / 100;
        int cradleY = cy + s * 12 / 100;
        // Arc base
        for (int i = 0; i < 6; i++)
        {
            int arcY = cradleY + i * 2;
            r.DrawCircle((200, 180, 240), (cx, arcY + cradleH), cradleW / 2, width: 2, alpha: 180 - i * 15);
        }
        // Cradle bowl — filled arc
        r.DrawCircle((180, 150, 220), (cx, cradleY + cradleH + s * 2 / 100), cradleW * 40 / 100, alpha: 100);

        // Baby unicorn body in cradle
        int babyCy = cradleY - s * 2 / 100;
        r.DrawCircle((230, 200, 250), (cx, babyCy), s * 12 / 100, alpha: 255);
        // Head
        int headR = s * 8 / 100;
        r.DrawCircle((235, 210, 255), (cx - s * 4 / 100, babyCy - s * 10 / 100), headR, alpha: 255);
        // Horn
        DrawHorn(r, cx - s * 4 / 100, babyCy - s * 10 / 100 - headR, s * 7 / 100, (255, 190, 230), (255, 230, 245));
        // Closed eyes
        r.DrawLine((140, 100, 160), (cx - s * 7 / 100, babyCy - s * 11 / 100), (cx - s * 4 / 100, babyCy - s * 10 / 100), width: 1, alpha: 200);

        // Blanket / cloud draped
        r.DrawCircle((180, 170, 220), (cx + s * 5 / 100, babyCy + s * 5 / 100), s * 8 / 100, alpha: 180);
        r.DrawCircle((190, 180, 230), (cx - s * 5 / 100, babyCy + s * 6 / 100), s * 7 / 100, alpha: 170);

        // Star dangling from above
        DrawStar5(r, cx + s * 8 / 100, y + h * 10 / 100, s * 5 / 100, (255, 245, 180), 200);
        r.DrawLine((200, 190, 230), (cx + s * 8 / 100, y + h * 10 / 100 + s * 4 / 100), (cx + s * 8 / 100, cradleY - s * 5 / 100), width: 1, alpha: 100);
    }

    // Variant 2: Rainbow bubble
    private static void DrawBaby_RainbowBubble(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Big iridescent bubble
        int bubR = s * 30 / 100;
        // Rainbow ring layers
        var rainbow = new[] { (255, 80, 80), (255, 160, 40), (255, 240, 60), (80, 220, 80), (80, 160, 255), (160, 80, 255) };
        for (int i = 0; i < rainbow.Length; i++)
        {
            r.DrawCircle(rainbow[i], (cx, cy), bubR - i * 2, width: 2, alpha: 120 - i * 8);
        }
        // Bubble highlight
        r.DrawCircle((255, 255, 255), (cx - bubR / 3, cy - bubR / 3), bubR / 4, alpha: 80);
        r.DrawCircle((255, 255, 255), (cx - bubR / 4, cy - bubR / 4), bubR / 8, alpha: 140);

        // Baby unicorn inside bubble
        int bodyR = s * 10 / 100;
        r.DrawCircle((220, 190, 240), (cx, cy + s * 2 / 100), bodyR, alpha: 230);
        // Head
        int headR = s * 7 / 100;
        r.DrawCircle((230, 200, 250), (cx, cy - s * 7 / 100), headR, alpha: 240);
        // Horn
        DrawHorn(r, cx, cy - s * 7 / 100 - headR, s * 6 / 100, (255, 180, 220), (255, 220, 240));
        // Eyes — big cute
        r.DrawCircle((60, 30, 80), (cx - headR / 2, cy - s * 8 / 100), Math.Max(2, headR / 3), alpha: 240);
        r.DrawCircle((60, 30, 80), (cx + headR / 2, cy - s * 8 / 100), Math.Max(2, headR / 3), alpha: 240);
        r.DrawCircle((255, 255, 255), (cx - headR / 2 - 1, cy - s * 9 / 100), Math.Max(1, headR / 6), alpha: 255);
        r.DrawCircle((255, 255, 255), (cx + headR / 2 - 1, cy - s * 9 / 100), Math.Max(1, headR / 6), alpha: 255);

        // Floating mini bubbles
        for (int i = 0; i < 6; i++)
        {
            int bx = cx + (int)(Math.Cos(i * 1.1) * s * 35 / 100);
            int by = cy + (int)(Math.Sin(i * 1.3 + 0.5) * s * 30 / 100);
            int br = Math.Max(2, s * (2 + i % 3) / 100);
            r.DrawCircle((200, 180, 255), (bx, by), br, width: 1, alpha: 100 + i * 10);
            r.DrawCircle((255, 255, 255), (bx - 1, by - 1), Math.Max(1, br / 3), alpha: 100);
        }
    }

    // Variant 3: Flower field
    private static void DrawBaby_FlowerField(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Ground with grass blades
        int groundY = y + h * 65 / 100;
        r.DrawRect((30, 80, 30), (x, groundY, w, h - (groundY - y)), alpha: 120);
        for (int i = 0; i < 20; i++)
        {
            int gx = x + i * w / 20 + (i * 7) % 5;
            int gh = s * (5 + i % 8) / 100;
            r.DrawLine((40, 120 + i % 30, 30), (gx, groundY), (gx + (i % 3 - 1) * 3, groundY - gh), width: 1, alpha: 160);
        }

        // Flowers
        var flowerColors = new[] { (255, 140, 180), (180, 140, 255), (140, 200, 255), (255, 200, 100), (255, 160, 120) };
        for (int i = 0; i < 7; i++)
        {
            int fx = x + w * (10 + i * 12) / 100;
            int fy = groundY - s * (1 + i % 3) / 100;
            var fc = flowerColors[i % flowerColors.Length];
            // Stem
            r.DrawLine((40, 100, 30), (fx, fy), (fx, fy + s * 5 / 100), width: 1, alpha: 160);
            // Petals
            int pr = Math.Max(2, s * 3 / 100);
            for (int p = 0; p < 5; p++)
            {
                double pa = p * Math.PI * 2 / 5;
                int px = fx + (int)(Math.Cos(pa) * pr);
                int py = fy + (int)(Math.Sin(pa) * pr);
                r.DrawCircle(fc, (px, py), Math.Max(1, pr * 6 / 10), alpha: 180);
            }
            r.DrawCircle((255, 240, 100), (fx, fy), Math.Max(1, pr / 2), alpha: 220);
        }

        // Baby unicorn standing in flowers
        int bodyCy = cy + s * 5 / 100;
        // Body
        r.DrawCircle((225, 195, 245), (cx, bodyCy), s * 13 / 100, alpha: 250);
        r.DrawCircle((240, 215, 255), (cx - s * 3 / 100, bodyCy - s * 4 / 100), s * 6 / 100, alpha: 200);
        // Head
        int headR = s * 9 / 100;
        r.DrawCircle((230, 200, 250), (cx, bodyCy - s * 14 / 100), headR, alpha: 255);
        // Horn
        DrawHorn(r, cx, bodyCy - s * 14 / 100 - headR, s * 8 / 100, (255, 180, 220), (255, 220, 240));
        // Ears
        DrawEar(r, cx - headR * 7 / 10, bodyCy - s * 14 / 100 - headR * 8 / 10, s * 4 / 100, (215, 180, 240), (255, 200, 230));
        DrawEar(r, cx + headR * 2 / 10, bodyCy - s * 14 / 100 - headR * 9 / 10, s * 4 / 100, (215, 180, 240), (255, 200, 230));
        // Eyes — happy
        r.DrawCircle((80, 40, 100), (cx - headR / 3, bodyCy - s * 15 / 100), Math.Max(2, headR / 3), alpha: 240);
        r.DrawCircle((80, 40, 100), (cx + headR / 3, bodyCy - s * 15 / 100), Math.Max(2, headR / 3), alpha: 240);
        r.DrawCircle((255, 255, 255), (cx - headR / 3 - 1, bodyCy - s * 16 / 100), Math.Max(1, headR / 7), alpha: 255);
        r.DrawCircle((255, 255, 255), (cx + headR / 3 - 1, bodyCy - s * 16 / 100), Math.Max(1, headR / 7), alpha: 255);
        // Smile
        r.DrawCircle((180, 100, 130), (cx, bodyCy - s * 12 / 100), Math.Max(2, headR / 3), width: 1, alpha: 120);

        // Legs
        for (int leg = -1; leg <= 1; leg += 2)
        {
            int lx = cx + leg * s * 6 / 100;
            r.DrawRect((210, 180, 235), (lx - 2, bodyCy + s * 8 / 100, 4, s * 10 / 100), alpha: 240);
            r.DrawCircle((200, 170, 225), (lx, bodyCy + s * 18 / 100), Math.Max(2, s * 2 / 100), alpha: 230);
        }

        // Butterfly
        DrawButterfly(r, cx + s * 25 / 100, cy - s * 20 / 100, s * 4 / 100, (255, 180, 220), 200);
    }

    // ═══════════════════════════════════════════════════════════
    //  UNICORN — majestic, powerful, luminous
    // ═══════════════════════════════════════════════════════════

    private static void DrawUnicorn(Renderer r, int v, int x, int y, int w, int h, int cx, int cy, string? cardName = null)
    {
        string cn = (cardName ?? "").ToLowerInvariant();

        // Per-card unique illustrations
        if (cn.Contains("zombie")) { DrawUni_Zombie(r, x, y, w, h, cx, cy); return; }
        if (cn.Contains("phoenix")) { DrawUni_Phoenix(r, x, y, w, h, cx, cy); return; }
        if (cn.Contains("shark")) { DrawUni_Shark(r, x, y, w, h, cx, cy); return; }
        if (cn.Contains("mermaid")) { DrawUni_Mermaid(r, x, y, w, h, cx, cy); return; }
        if (cn.Contains("llama")) { DrawUni_Llamacorn(r, x, y, w, h, cx, cy); return; }
        if (cn.Contains("rhino")) { DrawUni_Rhinocorn(r, x, y, w, h, cx, cy); return; }
        if (cn.Contains("black_knight")) { DrawUni_BlackKnight(r, x, y, w, h, cx, cy); return; }
        if (cn.Contains("stabby")) { DrawUni_Stabby(r, x, y, w, h, cx, cy); return; }
        if (cn.Contains("chainsaw")) { DrawUni_Chainsaw(r, x, y, w, h, cx, cy); return; }
        if (cn.Contains("dark_angel")) { DrawUni_DarkAngel(r, x, y, w, h, cx, cy); return; }
        if (cn.Contains("queen_bee")) { DrawUni_QueenBee(r, x, y, w, h, cx, cy); return; }
        if (cn.Contains("cob")) { DrawUni_CornCob(r, x, y, w, h, cx, cy); return; }
        if (cn.Contains("seductive")) { DrawUni_Seductive(r, x, y, w, h, cx, cy); return; }
        if (cn.Contains("americorn")) { DrawUni_Americorn(r, x, y, w, h, cx, cy); return; }
        if (cn.Contains("torpedo")) { DrawUni_NarwhalTorpedo(r, x, y, w, h, cx, cy); return; }
        if (cn.Contains("great_narwhal")) { DrawUni_GreatNarwhal(r, x, y, w, h, cx, cy); return; }
        if (cn.Contains("classy")) { DrawUni_ClassyNarwhal(r, x, y, w, h, cx, cy); return; }
        if (cn.Contains("alluring")) { DrawUni_AlluringNarwhal(r, x, y, w, h, cx, cy); return; }
        if (cn.Contains("narwhal")) { DrawUni_AlluringNarwhal(r, x, y, w, h, cx, cy); return; } // generic narwhal fallback
        if (cn.Contains("fertile")) { DrawUni_Fertile(r, x, y, w, h, cx, cy); return; }
        if (cn.Contains("annoying") && cn.Contains("flying")) { DrawUni_AnnoyingFlying(r, x, y, w, h, cx, cy); return; }
        if (cn.Contains("swift") && cn.Contains("flying")) { DrawUni_SwiftFlying(r, x, y, w, h, cx, cy); return; }
        if (cn.Contains("greedy") && cn.Contains("flying")) { DrawUni_GreedyFlying(r, x, y, w, h, cx, cy); return; }
        if (cn.Contains("magical") && cn.Contains("flying")) { DrawUni_MagicalFlying(r, x, y, w, h, cx, cy); return; }
        if (cn.Contains("majestic") && cn.Contains("flying")) { DrawUni_MajesticFlying(r, x, y, w, h, cx, cy); return; }
        if (cn.Contains("flying")) { DrawUni_MajesticFlying(r, x, y, w, h, cx, cy); return; } // generic flying fallback

        // Default generic variants for basic/glitter unicorns
        switch (v)
        {
            case 0: DrawUni_MajesticProfile(r, x, y, w, h, cx, cy); break;
            case 1: DrawUni_CosmicHorn(r, x, y, w, h, cx, cy); break;
            case 2: DrawUni_RainbowGallop(r, x, y, w, h, cx, cy); break;
            case 3: DrawUni_StardustPortal(r, x, y, w, h, cx, cy); break;
        }
    }

    // Variant 0: Majestic side profile with glowing mane
    private static void DrawUni_MajesticProfile(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Radiating aura behind head
        for (int ring = 0; ring < 5; ring++)
        {
            int rr = s * (25 + ring * 6) / 100;
            int ra = 60 - ring * 10;
            r.DrawCircle((140, 120, 255), (cx - s * 5 / 100, cy - s * 5 / 100), rr, width: 2, alpha: ra);
        }

        // Mane — flowing rainbow energy trails
        var maneColors = new[] { (255, 80, 120), (255, 160, 60), (255, 230, 70), (80, 220, 120), (80, 140, 255), (180, 80, 255) };
        for (int i = 0; i < maneColors.Length; i++)
        {
            int mx = cx - s * 15 / 100 - i * s * 2 / 100;
            int my = cy - s * 20 / 100 + i * s * 3 / 100;
            for (int j = 0; j < 6; j++)
            {
                int px = mx - j * s * 4 / 100 + (int)(Math.Sin(j * 0.8 + i * 0.5) * s * 4 / 100);
                int py = my + j * s * 5 / 100;
                r.DrawCircle(maneColors[i], (px, py), Math.Max(2, s * (4 - j / 2) / 100), alpha: 180 - j * 20);
            }
        }

        // Head shape — elongated
        int headW = s * 18 / 100, headH = s * 28 / 100;
        int headCx = cx, headCy = cy - s * 5 / 100;
        // Neck blending
        r.DrawCircle((200, 190, 240), (headCx - s * 2 / 100, headCy + headH * 6 / 10), headW * 8 / 10, alpha: 220);
        // Head
        r.DrawCircle((215, 205, 250), (headCx, headCy), headW, alpha: 255);
        r.DrawCircle((220, 210, 255), (headCx + headW / 4, headCy - headH / 6), headW * 85 / 100, alpha: 255);
        // Snout
        r.DrawCircle((210, 200, 245), (headCx + headW * 7 / 10, headCy + headH / 6), headW * 55 / 100, alpha: 255);
        // Highlight
        r.DrawCircle((240, 235, 255), (headCx - headW / 4, headCy - headH / 4), headW / 3, alpha: 160);

        // Horn — spiral with glow
        int hornH = s * 18 / 100;
        int hornX = headCx + headW / 4, hornY = headCy - headH * 55 / 100;
        DrawHorn(r, hornX, hornY, hornH, (200, 180, 255), (255, 240, 255));
        // Horn glow
        r.DrawCircle((200, 180, 255), (hornX, hornY - hornH / 2), hornH / 3, alpha: 60);

        // Eye — large, expressive
        int eyeR = Math.Max(3, s * 5 / 100);
        int eyeX = headCx + headW / 5, eyeY = headCy - headH / 8;
        r.DrawCircle((60, 40, 120), (eyeX, eyeY), eyeR, alpha: 255);
        r.DrawCircle((100, 80, 200), (eyeX, eyeY), eyeR * 7 / 10, alpha: 255);
        r.DrawCircle((255, 255, 255), (eyeX - 1, eyeY - 1), Math.Max(1, eyeR / 3), alpha: 255);
        // Lashes
        r.DrawLine((60, 40, 100), (eyeX - eyeR, eyeY - eyeR / 2), (eyeX - eyeR - s * 1 / 100, eyeY - eyeR), width: 1, alpha: 200);

        // Nostril
        r.DrawCircle((160, 140, 200), (headCx + headW + s * 1 / 100, headCy + headH / 5), Math.Max(1, s * 1 / 100), alpha: 180);

        // Ear
        DrawEar(r, headCx - headW / 3, headCy - headH * 5 / 10, s * 6 / 100, (205, 195, 240), (230, 200, 255));

        // Sparkles around horn
        DrawSparkle4(r, hornX + s * 8 / 100, hornY - s * 5 / 100, s * 3 / 100, (220, 200, 255), 180);
        DrawSparkle4(r, hornX - s * 6 / 100, hornY - hornH + s * 2 / 100, s * 2 / 100, (255, 230, 255), 150);
        DrawSparkle4(r, hornX + s * 3 / 100, hornY - hornH - s * 2 / 100, s * 2 / 100, (180, 200, 255), 130);
    }

    // Variant 1: Cosmic horn radiating energy
    private static void DrawUni_CosmicHorn(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Massive horn at center — glowing crystal
        int hornH = s * 45 / 100;
        int hornBase = s * 8 / 100;
        int hornTip = cx;
        int hornTipY = cy - hornH / 2;

        // Energy rings around horn
        for (int ring = 0; ring < 8; ring++)
        {
            int ry = hornTipY + ring * hornH / 8;
            int rr = hornBase * (8 - ring) / 8 + s * 4 / 100;
            byte ra = (byte)(80 - ring * 8);
            r.DrawCircle((160, 140, 255), (cx, ry), rr, width: 1, alpha: ra);
        }

        // Horn body — layered crystal facets
        for (int layer = 0; layer < hornH; layer += 2)
        {
            float t = (float)layer / hornH;
            int lw = (int)(hornBase * (1f - t * 0.9f));
            int ly = hornTipY + hornH - layer;
            int r2 = (int)(160 + 80 * (1f - t));
            int g2 = (int)(140 + 60 * (1f - t));
            int b2 = 255;
            r.DrawRect((r2, g2, b2), (cx - lw / 2, ly, lw, 2), alpha: (int)(200 + 40 * t));
        }
        // Crystal highlight line
        for (int i = 0; i < hornH; i += 3)
        {
            float t = (float)i / hornH;
            int hlX = cx - (int)(hornBase * (1f - t * 0.9f) * 0.3f);
            int hlY = hornTipY + hornH - i;
            r.DrawRect((255, 255, 255), (hlX, hlY, 1, 2), alpha: (int)(60 + 40 * t));
        }

        // Tip glow
        r.DrawCircle((255, 240, 255), (cx, hornTipY), s * 6 / 100, alpha: 150);
        r.DrawCircle((200, 180, 255), (cx, hornTipY), s * 10 / 100, alpha: 60);

        // Energy beams radiating from tip
        for (int beam = 0; beam < 8; beam++)
        {
            double ang = beam * Math.PI * 2 / 8 - Math.PI / 2;
            int bLen = s * (15 + beam * 3 % 10) / 100;
            int bx = cx + (int)(Math.Cos(ang) * bLen);
            int by = hornTipY + (int)(Math.Sin(ang) * bLen);
            var bcol = beam % 2 == 0 ? (180, 160, 255) : (255, 200, 255);
            r.DrawLine(bcol, (cx, hornTipY), (bx, by), width: beam % 3 == 0 ? 2 : 1, alpha: 120 - beam * 5);
        }

        // Small unicorn silhouette beneath horn
        r.DrawCircle((180, 170, 220), (cx, cy + s * 18 / 100), s * 10 / 100, alpha: 150);
        r.DrawCircle((190, 180, 230), (cx, cy + s * 10 / 100), s * 7 / 100, alpha: 160);

        // Orbiting sparkles
        for (int i = 0; i < 10; i++)
        {
            double ang = i * Math.PI * 2 / 10;
            int dist = s * 38 / 100;
            int sx = cx + (int)(Math.Cos(ang) * dist);
            int sy = cy + (int)(Math.Sin(ang) * dist * 0.6);
            DrawSparkle4(r, sx, sy, Math.Max(2, s * 2 / 100), (200, 190, 255), 120);
        }
    }

    // Variant 2: Rainbow gallop — running across rainbow bridge
    private static void DrawUni_RainbowGallop(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Rainbow arc bridge
        var rainbow = new[] { (255, 60, 60), (255, 140, 40), (255, 220, 40), (60, 200, 60), (60, 140, 255), (140, 60, 220) };
        int arcCy = cy + s * 20 / 100;
        for (int i = 0; i < rainbow.Length; i++)
        {
            int arcR = s * (50 - i * 3) / 100;
            r.DrawCircle(rainbow[i], (cx, arcCy + s * 20 / 100), arcR, width: 3, alpha: 180);
        }

        // Unicorn body — galloping pose
        int bodyCy = cy - s * 2 / 100;
        int bodyCx = cx + s * 3 / 100;
        // Body
        r.DrawCircle((220, 210, 250), (bodyCx, bodyCy), s * 12 / 100, alpha: 255);
        r.DrawCircle((230, 220, 255), (bodyCx - s * 3 / 100, bodyCy - s * 3 / 100), s * 6 / 100, alpha: 200);

        // Front legs — extended
        r.DrawLine((200, 190, 235), (bodyCx + s * 6 / 100, bodyCy + s * 6 / 100), (bodyCx + s * 16 / 100, bodyCy + s * 16 / 100), width: 3, alpha: 240);
        r.DrawLine((200, 190, 235), (bodyCx + s * 4 / 100, bodyCy + s * 8 / 100), (bodyCx + s * 10 / 100, bodyCy + s * 20 / 100), width: 3, alpha: 240);
        // Back legs — kicked back
        r.DrawLine((200, 190, 235), (bodyCx - s * 8 / 100, bodyCy + s * 6 / 100), (bodyCx - s * 18 / 100, bodyCy + s * 14 / 100), width: 3, alpha: 240);
        r.DrawLine((200, 190, 235), (bodyCx - s * 6 / 100, bodyCy + s * 8 / 100), (bodyCx - s * 14 / 100, bodyCy + s * 20 / 100), width: 3, alpha: 240);

        // Neck
        r.DrawCircle((215, 205, 248), (bodyCx + s * 8 / 100, bodyCy - s * 8 / 100), s * 7 / 100, alpha: 255);
        // Head
        int headR = s * 8 / 100;
        int headCx = bodyCx + s * 14 / 100, headCy = bodyCy - s * 14 / 100;
        r.DrawCircle((220, 210, 250), (headCx, headCy), headR, alpha: 255);
        r.DrawCircle((210, 200, 245), (headCx + headR * 6 / 10, headCy + headR / 4), headR * 45 / 100, alpha: 255);

        // Horn
        DrawHorn(r, headCx + headR / 3, headCy - headR, s * 12 / 100, (200, 180, 255), (255, 240, 255));

        // Eye
        r.DrawCircle((60, 40, 120), (headCx + headR / 4, headCy - headR / 5), Math.Max(2, headR / 3), alpha: 250);
        r.DrawCircle((255, 255, 255), (headCx + headR / 4, headCy - headR / 4), Math.Max(1, headR / 7), alpha: 255);

        // Flowing mane and tail — rainbow streaks
        for (int i = 0; i < rainbow.Length; i++)
        {
            // Mane
            int mx = bodyCx + s * 6 / 100 - i * s * 3 / 100;
            int my = bodyCy - s * 12 / 100 + i * s * 1 / 100;
            r.DrawLine(rainbow[i], (mx, my), (mx - s * 8 / 100, my + s * 3 / 100), width: 2, alpha: 160);
            // Tail
            int tx = bodyCx - s * 12 / 100 - i * s * 2 / 100;
            int ty = bodyCy - s * 2 / 100 + i * s * 1 / 100;
            r.DrawLine(rainbow[i], (bodyCx - s * 10 / 100, bodyCy), (tx, ty), width: 2, alpha: 140);
        }

        // Speed lines
        for (int i = 0; i < 5; i++)
        {
            int ly = bodyCy - s * 8 / 100 + i * s * 5 / 100;
            int lx = bodyCx - s * 25 / 100 - i * s * 3 / 100;
            r.DrawLine((200, 200, 255), (lx, ly), (lx - s * 12 / 100, ly), width: 1, alpha: 100 - i * 10);
        }

        // Sparkles at hooves
        DrawSparkle4(r, bodyCx + s * 16 / 100, bodyCy + s * 17 / 100, s * 3 / 100, (255, 240, 200), 180);
        DrawSparkle4(r, bodyCx - s * 18 / 100, bodyCy + s * 15 / 100, s * 2 / 100, (255, 220, 180), 150);
    }

    // Variant 3: Stardust portal — unicorn emerging from magic portal
    private static void DrawUni_StardustPortal(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Portal — concentric ellipses with energy
        for (int ring = 8; ring >= 0; ring--)
        {
            int rw = s * (20 + ring * 4) / 100;
            int rh = s * (12 + ring * 2) / 100;
            int ry = cy + s * 5 / 100;
            byte ra = (byte)(100 - ring * 8);
            var col = ring % 2 == 0 ? (140, 100, 255) : (200, 140, 255);
            r.DrawCircle(col, (cx, ry), (rw + rh) / 2, width: 2, alpha: ra);
        }

        // Portal swirl lines
        for (int i = 0; i < 12; i++)
        {
            double ang = i * Math.PI * 2 / 12;
            int innerR = s * 8 / 100;
            int outerR = s * (20 + i * 2 % 8) / 100;
            int px1 = cx + (int)(Math.Cos(ang) * innerR);
            int py1 = cy + s * 5 / 100 + (int)(Math.Sin(ang) * innerR * 6 / 10);
            int px2 = cx + (int)(Math.Cos(ang + 0.3) * outerR);
            int py2 = cy + s * 5 / 100 + (int)(Math.Sin(ang + 0.3) * outerR * 6 / 10);
            r.DrawLine((180, 140, 255), (px1, py1), (px2, py2), width: 1, alpha: 80);
        }

        // Unicorn silhouette emerging upward
        int uniBody = cy - s * 8 / 100;
        r.DrawCircle((220, 210, 255), (cx, uniBody), s * 10 / 100, alpha: 240);
        // Head
        int headR = s * 7 / 100;
        r.DrawCircle((230, 220, 255), (cx, uniBody - s * 12 / 100), headR, alpha: 250);
        // Horn — tall and bright
        DrawHorn(r, cx, uniBody - s * 12 / 100 - headR, s * 14 / 100, (180, 160, 255), (255, 240, 255));
        // Horn tip sparkle
        r.DrawCircle((255, 255, 255), (cx, uniBody - s * 12 / 100 - headR - s * 12 / 100), s * 3 / 100, alpha: 200);

        // Stardust rising from portal
        for (int i = 0; i < 20; i++)
        {
            int dx = cx + (int)(Math.Sin(i * 0.7) * s * 18 / 100);
            int dy = cy + s * 5 / 100 - i * s * 4 / 100;
            int dr = Math.Max(1, s * (3 - i / 7) / 100);
            byte da = (byte)Math.Max(30, 180 - i * 8);
            var dc = i % 3 == 0 ? (255, 220, 255) : i % 3 == 1 ? (200, 200, 255) : (255, 255, 220);
            r.DrawCircle(dc, (dx, dy), dr, alpha: da);
        }
    }

    // ═══════════════════════════════════════════════════════════
    //  PER-CARD UNIQUE UNICORN ILLUSTRATIONS
    // ═══════════════════════════════════════════════════════════

    // Zombie Unicorn — undead skull, hollow eyes, bone fragments, green decay
    private static void DrawUni_Zombie(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Eerie green glow behind skull
        for (int ring = 0; ring < 4; ring++)
            r.DrawCircle((40, 180, 30), (cx, cy - s * 5 / 100), s * (30 + ring * 6) / 100, width: 2, alpha: 50 - ring * 10);

        // Skull shape
        int skullR = s * 18 / 100;
        r.DrawCircle((80, 100, 60), (cx, cy - s * 8 / 100), skullR, alpha: 240);
        r.DrawCircle((90, 115, 70), (cx, cy - s * 10 / 100), skullR * 9 / 10, alpha: 250);

        // Hollow eye sockets with eerie green glow
        r.DrawCircle((10, 20, 8), (cx - s * 7 / 100, cy - s * 12 / 100), s * 5 / 100, alpha: 255);
        r.DrawCircle((10, 20, 8), (cx + s * 7 / 100, cy - s * 12 / 100), s * 5 / 100, alpha: 255);
        r.DrawCircle((80, 255, 50), (cx - s * 7 / 100, cy - s * 12 / 100), s * 2 / 100, alpha: 200);
        r.DrawCircle((80, 255, 50), (cx + s * 7 / 100, cy - s * 12 / 100), s * 2 / 100, alpha: 200);

        // Nose hole
        DrawFilledTriangleDown(r, cx - s * 2 / 100, cy - s * 6 / 100, s * 4 / 100, s * 3 / 100, (10, 20, 8), 240);

        // Jaw with teeth
        r.DrawRect((80, 100, 60), (cx - s * 12 / 100, cy - s * 2 / 100, s * 24 / 100, s * 6 / 100), alpha: 230);
        for (int t = 0; t < 6; t++)
        {
            int tx = cx - s * 10 / 100 + t * s * 4 / 100;
            r.DrawRect((200, 210, 180), (tx, cy - s * 2 / 100, s * 2 / 100, s * 4 / 100), alpha: 240);
        }

        // Stitches across forehead
        for (int st = 0; st < 4; st++)
        {
            int sx2 = cx - s * 14 / 100 + st * s * 9 / 100;
            int sy2 = cy - s * 4 / 100;
            r.DrawLine((40, 60, 30), (sx2, sy2 - s * 2 / 100), (sx2, sy2 + s * 2 / 100), width: 1, alpha: 180);
        }

        // Decaying horn with green glow
        DrawHorn(r, cx, cy - s * 8 / 100 - skullR, s * 12 / 100, (50, 80, 40), (80, 255, 50));
        r.DrawCircle((80, 255, 50), (cx, cy - s * 8 / 100 - skullR - s * 10 / 100), s * 3 / 100, alpha: 160);

        // Tattered ears
        DrawEar(r, cx - s * 14 / 100, cy - s * 20 / 100, s * 5 / 100, (70, 90, 55), (40, 60, 30));
        DrawEar(r, cx + s * 10 / 100, cy - s * 20 / 100, s * 5 / 100, (70, 90, 55), (40, 60, 30));

        // Bone fragments scattered
        for (int b = 0; b < 6; b++)
        {
            int bx = cx + (int)(Math.Cos(b * 1.1) * s * 28 / 100);
            int by = cy + s * 15 / 100 + (int)(Math.Sin(b * 1.5) * s * 8 / 100);
            r.DrawLine((200, 200, 180), (bx - s * 3 / 100, by), (bx + s * 3 / 100, by), width: 2, alpha: 150);
            r.DrawCircle((200, 200, 180), (bx - s * 3 / 100, by), s * 1 / 100, alpha: 150);
            r.DrawCircle((200, 200, 180), (bx + s * 3 / 100, by), s * 1 / 100, alpha: 150);
        }

        // Decaying mane drips
        for (int d = 0; d < 5; d++)
        {
            int dx = cx - s * 18 / 100 + d * s * 5 / 100;
            int dy2 = cy - s * 5 / 100 + d * s * 3 / 100;
            r.DrawLine((50, 120, 30), (dx, dy2), (dx + s * 1 / 100, dy2 + s * 8 / 100), width: 2, alpha: 140 - d * 15);
        }
    }

    // Phoenix Unicorn — fiery wings, flames, rising from ashes
    private static void DrawUni_Phoenix(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Ash pile at bottom
        r.DrawCircle((50, 40, 35), (cx, cy + s * 25 / 100), s * 20 / 100, alpha: 180);
        r.DrawCircle((40, 32, 28), (cx - s * 8 / 100, cy + s * 28 / 100), s * 12 / 100, alpha: 160);
        r.DrawCircle((40, 32, 28), (cx + s * 10 / 100, cy + s * 27 / 100), s * 14 / 100, alpha: 160);

        // Fiery wings — layered flame triangles (left wing)
        for (int f = 0; f < 5; f++)
        {
            int fw = s * (28 - f * 4) / 100;
            int fh = s * (22 - f * 3) / 100;
            int fx = cx - s * 20 / 100 - f * s * 3 / 100;
            int fy = cy - s * 8 / 100 + f * s * 2 / 100;
            var fc = f < 2 ? (255, 220, 60) : f < 4 ? (255, 140, 30) : (200, 60, 20);
            byte fa = (byte)(220 - f * 25);
            DrawFilledTriangleUp(r, fx - fw / 2, fy, fw, fh, fc, fa);
        }
        // Right wing
        for (int f = 0; f < 5; f++)
        {
            int fw = s * (28 - f * 4) / 100;
            int fh = s * (22 - f * 3) / 100;
            int fx = cx + s * 20 / 100 + f * s * 3 / 100;
            int fy = cy - s * 8 / 100 + f * s * 2 / 100;
            var fc = f < 2 ? (255, 220, 60) : f < 4 ? (255, 140, 30) : (200, 60, 20);
            byte fa = (byte)(220 - f * 25);
            DrawFilledTriangleUp(r, fx - fw / 2, fy, fw, fh, fc, fa);
        }

        // Fiery body glow
        r.DrawCircle((255, 100, 20), (cx, cy), s * 12 / 100, alpha: 120);
        r.DrawCircle((255, 180, 50), (cx, cy - s * 5 / 100), s * 9 / 100, alpha: 200);

        // Head
        r.DrawCircle((255, 200, 80), (cx, cy - s * 14 / 100), s * 7 / 100, alpha: 250);
        // Glowing orange horn
        DrawHorn(r, cx, cy - s * 21 / 100, s * 12 / 100, (255, 120, 20), (255, 240, 100));
        r.DrawCircle((255, 255, 150), (cx, cy - s * 31 / 100), s * 2 / 100, alpha: 220);

        // Flames licking upward
        for (int fl = 0; fl < 8; fl++)
        {
            int flx = cx + (int)(Math.Sin(fl * 0.9) * s * 16 / 100);
            int fly = cy + s * 10 / 100 - fl * s * 6 / 100;
            int flr = Math.Max(2, s * (4 - fl / 3) / 100);
            var flc = fl % 3 == 0 ? (255, 240, 80) : fl % 3 == 1 ? (255, 160, 30) : (255, 80, 20);
            r.DrawCircle(flc, (flx, fly), flr, alpha: (byte)(200 - fl * 15));
        }

        // Ember particles
        for (int e = 0; e < 10; e++)
        {
            int ex = cx + (int)(Math.Cos(e * 2.1) * s * 30 / 100);
            int ey = cy - s * 15 / 100 + (int)(Math.Sin(e * 1.7) * s * 20 / 100);
            r.DrawCircle((255, 200, 60), (ex, ey), Math.Max(1, s * 1 / 100), alpha: (byte)(160 - e * 10));
        }
        DrawSparkle4(r, cx + s * 15 / 100, cy - s * 25 / 100, s * 3 / 100, (255, 240, 100), 180);
    }

    // Shark Unicorn — dorsal fin, rows of teeth, underwater
    private static void DrawUni_Shark(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Water surface
        r.DrawRect((30, 80, 140), (x, cy + s * 10 / 100, w, h - (cy + s * 10 / 100 - y)), alpha: 100);
        for (int wave = 0; wave < 8; wave++)
        {
            int wx = x + wave * w / 8;
            int wy = cy + s * 10 / 100 + (int)(Math.Sin(wave * 1.2) * s * 2 / 100);
            r.DrawCircle((80, 160, 220), (wx, wy), s * 4 / 100, alpha: 80);
        }

        // Shark body silhouette — elongated
        r.DrawCircle((60, 80, 110), (cx, cy + s * 5 / 100), s * 14 / 100, alpha: 230);
        r.DrawCircle((60, 80, 110), (cx + s * 8 / 100, cy + s * 6 / 100), s * 10 / 100, alpha: 230);
        r.DrawCircle((60, 80, 110), (cx - s * 10 / 100, cy + s * 5 / 100), s * 10 / 100, alpha: 220);

        // Dorsal fin
        DrawFilledTriangleUp(r, cx - s * 5 / 100, cy - s * 8 / 100, s * 10 / 100, s * 18 / 100, (70, 90, 120), 240);

        // Tail fin
        DrawFilledTriangleUp(r, cx - s * 24 / 100, cy - s * 2 / 100, s * 8 / 100, s * 10 / 100, (65, 85, 115), 220);
        DrawFilledTriangleDown(r, cx - s * 24 / 100, cy + s * 8 / 100, s * 8 / 100, s * 8 / 100, (65, 85, 115), 220);

        // Horn on top of head
        DrawHorn(r, cx + s * 12 / 100, cy - s * 4 / 100, s * 10 / 100, (100, 140, 200), (180, 220, 255));

        // Menacing eye
        r.DrawCircle((220, 220, 60), (cx + s * 10 / 100, cy + s * 2 / 100), s * 3 / 100, alpha: 255);
        r.DrawCircle((10, 10, 10), (cx + s * 10 / 100, cy + s * 2 / 100), s * 1 / 100, alpha: 255);

        // Rows of teeth (open jaw)
        r.DrawCircle((40, 55, 80), (cx + s * 14 / 100, cy + s * 8 / 100), s * 6 / 100, alpha: 200);
        for (int t = 0; t < 7; t++)
        {
            int tx = cx + s * 9 / 100 + t * s * 2 / 100;
            DrawFilledTriangleDown(r, tx, cy + s * 5 / 100, s * 2 / 100, s * 3 / 100, (230, 230, 230), 240);
            DrawFilledTriangleUp(r, tx, cy + s * 10 / 100, s * 2 / 100, s * 3 / 100, (230, 230, 230), 230);
        }

        // Underwater bubbles
        for (int b = 0; b < 8; b++)
        {
            int bx = cx + (int)(Math.Cos(b * 1.6) * s * 22 / 100);
            int by = cy + s * 18 / 100 + (int)(Math.Sin(b * 2.1) * s * 6 / 100);
            r.DrawCircle((120, 180, 240), (bx, by), Math.Max(1, s * (2 - b / 4) / 100), width: 1, alpha: 140);
        }

        // Water splash at surface
        DrawSparkle4(r, cx, cy + s * 10 / 100, s * 5 / 100, (140, 200, 255), 150);
    }

    // Mermaid Unicorn — fish tail, seashells, flowing hair, coral
    private static void DrawUni_Mermaid(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Ocean waves at bottom
        for (int wave = 0; wave < 6; wave++)
        {
            int wy = cy + s * 20 / 100 + wave * s * 3 / 100;
            for (int seg = 0; seg < 10; seg++)
            {
                int wx = x + seg * w / 10 + (wave % 2) * w / 20;
                r.DrawCircle((40, 140, 180), (wx, wy), s * 5 / 100, alpha: (byte)(80 - wave * 8));
            }
        }

        // Fish tail — scaled pattern
        int tailCx = cx, tailCy = cy + s * 12 / 100;
        r.DrawCircle((60, 180, 160), (tailCx, tailCy), s * 10 / 100, alpha: 220);
        r.DrawCircle((50, 170, 150), (tailCx, tailCy + s * 8 / 100), s * 7 / 100, alpha: 210);
        // Tail fin
        DrawFilledTriangleDown(r, tailCx - s * 8 / 100, tailCy + s * 14 / 100, s * 16 / 100, s * 8 / 100, (80, 200, 180), 200);
        // Scale pattern
        for (int row = 0; row < 3; row++)
            for (int col = -2; col <= 2; col++)
            {
                int scx = tailCx + col * s * 4 / 100 + (row % 2) * s * 2 / 100;
                int scy = tailCy + row * s * 4 / 100;
                r.DrawCircle((100, 210, 200), (scx, scy), s * 2 / 100, width: 1, alpha: 140);
            }

        // Upper body
        r.DrawCircle((220, 190, 200), (cx, cy - s * 5 / 100), s * 9 / 100, alpha: 240);

        // Seashell bra
        r.DrawCircle((255, 180, 200), (cx - s * 5 / 100, cy + s * 1 / 100), s * 3 / 100, alpha: 220);
        r.DrawCircle((255, 180, 200), (cx + s * 5 / 100, cy + s * 1 / 100), s * 3 / 100, alpha: 220);

        // Head
        r.DrawCircle((225, 195, 210), (cx, cy - s * 15 / 100), s * 7 / 100, alpha: 250);
        // Long flowing wavy hair
        var hairColors = new[] { (80, 200, 200), (60, 180, 220), (100, 220, 200), (80, 160, 200) };
        for (int i = 0; i < hairColors.Length; i++)
        {
            for (int j = 0; j < 5; j++)
            {
                int hx = cx - s * 12 / 100 + i * s * 5 / 100 + (int)(Math.Sin(j * 0.7 + i) * s * 3 / 100);
                int hy = cy - s * 18 / 100 + j * s * 6 / 100;
                r.DrawCircle(hairColors[i], (hx, hy), Math.Max(2, s * 3 / 100), alpha: (byte)(180 - j * 20));
            }
        }

        // Horn
        DrawHorn(r, cx, cy - s * 22 / 100, s * 10 / 100, (80, 200, 200), (180, 255, 240));

        // Coral
        for (int c2 = 0; c2 < 3; c2++)
        {
            int corx = cx + s * 20 / 100 + c2 * s * 4 / 100;
            int cory = cy + s * 22 / 100;
            r.DrawLine((255, 100, 120), (corx, cory), (corx - s * 2 / 100, cory - s * 10 / 100), width: 2, alpha: 160);
            r.DrawLine((255, 100, 120), (corx, cory), (corx + s * 2 / 100, cory - s * 8 / 100), width: 2, alpha: 140);
        }

        // Bubbles
        for (int b = 0; b < 6; b++)
        {
            int bx = cx + (int)(Math.Cos(b * 1.3) * s * 25 / 100);
            int by = cy + (int)(Math.Sin(b * 1.9) * s * 15 / 100);
            r.DrawCircle((160, 230, 255), (bx, by), Math.Max(1, s * 2 / 100), width: 1, alpha: 120);
        }
    }

    // Llamacorn — fluffy llama body, rainbow horn, Andean poncho
    private static void DrawUni_Llamacorn(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Aura glow
        r.DrawCircle((235, 180, 100), (cx, cy), s * 28 / 100, alpha: 40);

        // Fluffy round body
        int bodyCx = cx, bodyCy = cy + s * 5 / 100;
        for (int f = 0; f < 8; f++)
        {
            int fx = bodyCx + (int)(Math.Cos(f * Math.PI / 4) * s * 10 / 100);
            int fy = bodyCy + (int)(Math.Sin(f * Math.PI / 4) * s * 8 / 100);
            r.DrawCircle((240, 225, 200), (fx, fy), s * 8 / 100, alpha: 220);
        }
        r.DrawCircle((245, 230, 210), (bodyCx, bodyCy), s * 10 / 100, alpha: 240);

        // Andean poncho stripes across body
        var ponchoColors = new[] { (255, 60, 60), (255, 180, 40), (255, 240, 60), (80, 200, 80), (80, 120, 255), (180, 80, 255) };
        for (int p = 0; p < ponchoColors.Length; p++)
        {
            int py = bodyCy - s * 6 / 100 + p * s * 2 / 100;
            r.DrawRect(ponchoColors[p], (bodyCx - s * 10 / 100, py, s * 20 / 100, s * 2 / 100), alpha: 180);
        }

        // Long neck
        r.DrawCircle((245, 230, 210), (cx, cy - s * 10 / 100), s * 5 / 100, alpha: 240);
        r.DrawCircle((245, 230, 210), (cx, cy - s * 16 / 100), s * 5 / 100, alpha: 240);

        // Head
        r.DrawCircle((248, 235, 215), (cx, cy - s * 22 / 100), s * 6 / 100, alpha: 250);
        // Cute googly eyes
        r.DrawCircle((255, 255, 255), (cx - s * 3 / 100, cy - s * 23 / 100), s * 3 / 100, alpha: 255);
        r.DrawCircle((255, 255, 255), (cx + s * 3 / 100, cy - s * 23 / 100), s * 3 / 100, alpha: 255);
        r.DrawCircle((20, 20, 20), (cx - s * 2 / 100, cy - s * 23 / 100), s * 2 / 100, alpha: 255);
        r.DrawCircle((20, 20, 20), (cx + s * 4 / 100, cy - s * 23 / 100), s * 2 / 100, alpha: 255);
        r.DrawCircle((255, 255, 255), (cx - s * 2 / 100 + 1, cy - s * 24 / 100), s * 1 / 100, alpha: 255);
        r.DrawCircle((255, 255, 255), (cx + s * 4 / 100 + 1, cy - s * 24 / 100), s * 1 / 100, alpha: 255);

        // Fluffy ears
        DrawEar(r, cx - s * 8 / 100, cy - s * 28 / 100, s * 5 / 100, (245, 225, 200), (255, 200, 180));
        DrawEar(r, cx + s * 4 / 100, cy - s * 28 / 100, s * 5 / 100, (245, 225, 200), (255, 200, 180));

        // Rainbow horn
        DrawHorn(r, cx, cy - s * 28 / 100, s * 12 / 100, (255, 180, 100), (255, 100, 200));

        // Legs
        for (int leg = -1; leg <= 1; leg += 2)
        {
            r.DrawRect((230, 215, 190), (bodyCx + leg * s * 7 / 100 - 2, bodyCy + s * 10 / 100, 5, s * 10 / 100), alpha: 230);
            r.DrawCircle((220, 200, 180), (bodyCx + leg * s * 7 / 100, bodyCy + s * 20 / 100), s * 2 / 100, alpha: 220);
        }

        DrawSparkle4(r, cx + s * 18 / 100, cy - s * 15 / 100, s * 3 / 100, (255, 220, 100), 160);
    }

    // Rhinocorn — armored rhino build, hexagon plates, rainbow horn
    private static void DrawUni_Rhinocorn(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Dust cloud at bottom
        for (int d = 0; d < 6; d++)
        {
            int dx = cx - s * 20 / 100 + d * s * 8 / 100;
            int dy = cy + s * 25 / 100 + (int)(Math.Sin(d * 1.4) * s * 3 / 100);
            r.DrawCircle((140, 130, 120), (dx, dy), s * 5 / 100, alpha: (byte)(100 - d * 10));
        }

        // Heavy body
        int bodyCx2 = cx - s * 2 / 100, bodyCy2 = cy + s * 5 / 100;
        r.DrawCircle((100, 100, 110), (bodyCx2, bodyCy2), s * 16 / 100, alpha: 240);
        r.DrawCircle((110, 110, 120), (bodyCx2 + s * 8 / 100, bodyCy2 - s * 2 / 100), s * 12 / 100, alpha: 230);

        // Armored plates — hexagons
        for (int p = 0; p < 5; p++)
        {
            int px = bodyCx2 - s * 10 / 100 + p * s * 6 / 100;
            int py = bodyCy2 - s * 4 / 100 + (p % 2) * s * 4 / 100;
            DrawHexagon(r, px, py, s * 4 / 100, (140, 140, 160), 160);
        }

        // Thick legs
        for (int leg = -1; leg <= 1; leg += 2)
        {
            int lx = bodyCx2 + leg * s * 10 / 100;
            r.DrawRect((90, 90, 100), (lx - s * 3 / 100, bodyCy2 + s * 10 / 100, s * 6 / 100, s * 12 / 100), alpha: 230);
            r.DrawRect((80, 80, 90), (lx - s * 4 / 100, bodyCy2 + s * 20 / 100, s * 8 / 100, s * 3 / 100), alpha: 240);
        }

        // Head — blocky
        int headCx2 = cx + s * 14 / 100, headCy2 = cy - s * 5 / 100;
        r.DrawCircle((120, 120, 130), (headCx2, headCy2), s * 9 / 100, alpha: 250);
        // Eye
        r.DrawCircle((60, 60, 60), (headCx2 + s * 3 / 100, headCy2 - s * 2 / 100), s * 2 / 100, alpha: 240);
        r.DrawCircle((255, 255, 255), (headCx2 + s * 3 / 100 + 1, headCy2 - s * 3 / 100), s * 1 / 100, alpha: 220);

        // Rainbow spiral horn
        DrawHorn(r, headCx2 + s * 6 / 100, headCy2 - s * 8 / 100, s * 14 / 100, (200, 100, 255), (255, 200, 255));
        // Rainbow spiral lines on horn
        for (int sp = 0; sp < 5; sp++)
        {
            int spx = headCx2 + s * 6 / 100;
            int spy = headCy2 - s * 8 / 100 - sp * s * 3 / 100;
            var spc = sp % 3 == 0 ? (255, 100, 100) : sp % 3 == 1 ? (100, 255, 100) : (100, 100, 255);
            r.DrawLine(spc, (spx - s * 2 / 100, spy), (spx + s * 2 / 100, spy - s * 1 / 100), width: 1, alpha: 180);
        }

        // Charge dust
        for (int c3 = 0; c3 < 4; c3++)
        {
            DrawSparkle4(r, cx - s * 25 / 100 + c3 * s * 3 / 100, cy + s * 20 / 100, s * 2 / 100, (180, 170, 150), 100);
        }
    }

    // Black Knight Unicorn — dark armor, sword, shield, helmet
    private static void DrawUni_BlackKnight(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Dark cape behind
        DrawFilledTriangleDown(r, cx - s * 18 / 100, cy - s * 10 / 100, s * 36 / 100, s * 35 / 100, (30, 15, 45), 200);
        r.DrawRect((25, 12, 40), (cx - s * 16 / 100, cy - s * 10 / 100, s * 32 / 100, s * 5 / 100), alpha: 180);

        // Armored body
        r.DrawCircle((45, 40, 55), (cx, cy + s * 3 / 100), s * 13 / 100, alpha: 240);
        r.DrawCircle((55, 50, 65), (cx, cy - s * 2 / 100), s * 10 / 100, alpha: 230);
        // Armor plate lines
        r.DrawLine((80, 70, 100), (cx - s * 8 / 100, cy - s * 5 / 100), (cx - s * 8 / 100, cy + s * 12 / 100), width: 1, alpha: 140);
        r.DrawLine((80, 70, 100), (cx + s * 8 / 100, cy - s * 5 / 100), (cx + s * 8 / 100, cy + s * 12 / 100), width: 1, alpha: 140);
        r.DrawLine((80, 70, 100), (cx - s * 12 / 100, cy + s * 5 / 100), (cx + s * 12 / 100, cy + s * 5 / 100), width: 1, alpha: 120);

        // Helmet
        int helmCy = cy - s * 14 / 100;
        r.DrawCircle((50, 45, 60), (cx, helmCy), s * 8 / 100, alpha: 250);
        r.DrawRect((50, 45, 60), (cx - s * 9 / 100, helmCy - s * 2 / 100, s * 18 / 100, s * 4 / 100), alpha: 240);
        // Visor slit
        r.DrawRect((120, 60, 160), (cx - s * 5 / 100, helmCy + s * 1 / 100, s * 10 / 100, s * 2 / 100), alpha: 200);
        // Horn through helmet
        DrawHorn(r, cx, helmCy - s * 8 / 100, s * 12 / 100, (60, 40, 80), (140, 100, 200));

        // Shield with unicorn crest (left side)
        int shX = cx - s * 22 / 100, shY = cy - s * 5 / 100;
        r.DrawRect((60, 50, 70), (shX, shY, s * 10 / 100, s * 14 / 100), alpha: 230);
        DrawFilledTriangleDown(r, shX, shY + s * 14 / 100, s * 10 / 100, s * 5 / 100, (60, 50, 70), 230);
        // Crest — small unicorn head
        r.DrawCircle((120, 100, 160), (shX + s * 5 / 100, shY + s * 5 / 100), s * 3 / 100, alpha: 200);
        DrawHorn(r, shX + s * 5 / 100, shY + s * 2 / 100, s * 4 / 100, (160, 130, 200), (200, 180, 255));

        // Sword in right hoof
        int swX = cx + s * 18 / 100;
        r.DrawRect((160, 160, 180), (swX - 1, cy - s * 22 / 100, 3, s * 30 / 100), alpha: 240);
        r.DrawRect((120, 100, 140), (swX - s * 4 / 100, cy - s * 6 / 100, s * 8 / 100, s * 2 / 100), alpha: 230);
        // Blade glint
        r.DrawLine((220, 220, 255), (swX, cy - s * 22 / 100), (swX, cy - s * 10 / 100), width: 1, alpha: 100);

        // Battle-worn scratches
        for (int sc = 0; sc < 3; sc++)
        {
            int scx = cx - s * 5 / 100 + sc * s * 5 / 100;
            int scy = cy + sc * s * 3 / 100;
            r.DrawLine((100, 80, 120), (scx, scy), (scx + s * 4 / 100, scy + s * 2 / 100), width: 1, alpha: 120);
        }
    }

    // Stabby Unicorn — knives/daggers, blood drops, aggressive
    private static void DrawUni_Stabby(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Red glow behind
        r.DrawCircle((255, 30, 30), (cx, cy), s * 25 / 100, alpha: 50);

        // Small unicorn body (aggressive stance)
        r.DrawCircle((180, 160, 180), (cx, cy + s * 2 / 100), s * 10 / 100, alpha: 230);
        // Head — forward lean
        r.DrawCircle((190, 170, 190), (cx + s * 6 / 100, cy - s * 8 / 100), s * 7 / 100, alpha: 245);
        // Angry eyes
        r.DrawLine((255, 40, 40), (cx + s * 3 / 100, cy - s * 10 / 100), (cx + s * 7 / 100, cy - s * 11 / 100), width: 2, alpha: 240);
        r.DrawCircle((255, 50, 50), (cx + s * 4 / 100, cy - s * 9 / 100), s * 2 / 100, alpha: 230);
        r.DrawCircle((255, 50, 50), (cx + s * 8 / 100, cy - s * 9 / 100), s * 2 / 100, alpha: 230);
        r.DrawCircle((10, 10, 10), (cx + s * 4 / 100, cy - s * 9 / 100), s * 1 / 100, alpha: 255);
        r.DrawCircle((10, 10, 10), (cx + s * 8 / 100, cy - s * 9 / 100), s * 1 / 100, alpha: 255);

        // Horn — sharp and red-tipped
        DrawHorn(r, cx + s * 6 / 100, cy - s * 15 / 100, s * 10 / 100, (200, 180, 200), (255, 60, 60));

        // Collection of daggers arranged around
        var daggerAngles = new[] { 0.0, 0.7, 1.4, 2.1, 2.8, 3.5, 4.2, 4.9 };
        foreach (double ang in daggerAngles)
        {
            int dx1 = cx + (int)(Math.Cos(ang) * s * 20 / 100);
            int dy1 = cy + (int)(Math.Sin(ang) * s * 18 / 100);
            int dx2 = cx + (int)(Math.Cos(ang) * s * 30 / 100);
            int dy2 = cy + (int)(Math.Sin(ang) * s * 28 / 100);
            // Blade
            r.DrawLine((200, 200, 220), (dx1, dy1), (dx2, dy2), width: 2, alpha: 220);
            // Handle
            r.DrawLine((120, 80, 40), (dx1, dy1), (dx1 - (int)(Math.Cos(ang) * s * 3 / 100), dy1 - (int)(Math.Sin(ang) * s * 3 / 100)), width: 3, alpha: 200);
            // Blade glint
            r.DrawCircle((255, 255, 255), (dx2, dy2), s * 1 / 100, alpha: 140);
        }

        // Bandolier across body
        r.DrawLine((100, 60, 30), (cx - s * 10 / 100, cy - s * 5 / 100), (cx + s * 6 / 100, cy + s * 8 / 100), width: 3, alpha: 200);
        // Small daggers on bandolier
        for (int bd = 0; bd < 3; bd++)
        {
            int bx = cx - s * 6 / 100 + bd * s * 5 / 100;
            int by2 = cy - s * 2 / 100 + bd * s * 3 / 100;
            r.DrawLine((180, 180, 200), (bx, by2), (bx, by2 + s * 3 / 100), width: 1, alpha: 180);
        }

        // Blood drops
        for (int bd = 0; bd < 5; bd++)
        {
            int bx = cx + (int)(Math.Cos(bd * 1.3 + 0.5) * s * 25 / 100);
            int by2 = cy + s * 10 / 100 + bd * s * 3 / 100;
            r.DrawCircle((200, 20, 20), (bx, by2), Math.Max(2, s * 2 / 100), alpha: 180);
            r.DrawCircle((180, 10, 10), (bx, by2 + s * 2 / 100), Math.Max(1, s * 1 / 100), alpha: 150);
        }
    }

    // Chainsaw Unicorn — chainsaw silhouette, sawdust, motion lines
    private static void DrawUni_Chainsaw(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Destructive energy aura
        for (int ring = 0; ring < 3; ring++)
            r.DrawCircle((240, 160, 40), (cx, cy), s * (20 + ring * 8) / 100, width: 2, alpha: (byte)(60 - ring * 15));

        // Chainsaw body — rectangular
        int sawX = cx - s * 20 / 100, sawY = cy - s * 6 / 100;
        int sawW = s * 40 / 100, sawH = s * 12 / 100;
        r.DrawRect((180, 100, 30), (sawX, sawY, sawW, sawH), alpha: 230);
        r.DrawRect((200, 120, 40), (sawX + 2, sawY + 2, sawW - 4, sawH - 4), alpha: 220);

        // Blade extension
        int bladeX = sawX + sawW, bladeY = sawY + s * 2 / 100;
        r.DrawRect((160, 160, 170), (bladeX, bladeY, s * 12 / 100, s * 8 / 100), alpha: 230);
        // Rounded tip
        r.DrawCircle((160, 160, 170), (bladeX + s * 12 / 100, bladeY + s * 4 / 100), s * 4 / 100, alpha: 230);

        // Chain teeth along blade edge
        for (int t = 0; t < 10; t++)
        {
            int tx = sawX + s * 5 / 100 + t * s * 5 / 100;
            DrawFilledTriangleDown(r, tx, sawY + sawH, s * 3 / 100, s * 3 / 100, (100, 100, 110), 220);
            DrawFilledTriangleUp(r, tx, sawY - s * 3 / 100, s * 3 / 100, s * 3 / 100, (100, 100, 110), 220);
        }

        // Handle
        r.DrawRect((80, 50, 20), (sawX - s * 4 / 100, sawY + s * 2 / 100, s * 6 / 100, s * 8 / 100), alpha: 220);
        r.DrawRect((100, 60, 20), (sawX - s * 3 / 100, sawY + s * 3 / 100, s * 4 / 100, s * 6 / 100), alpha: 210);

        // Horn integrated as blade tip
        DrawHorn(r, bladeX + s * 15 / 100, bladeY + s * 2 / 100, s * 8 / 100, (200, 180, 160), (255, 240, 200));

        // Sawdust particles flying
        for (int sd = 0; sd < 12; sd++)
        {
            int px = cx + (int)(Math.Cos(sd * 0.8) * s * (25 + sd) / 100);
            int py = cy + s * 8 / 100 + (int)(Math.Sin(sd * 1.3) * s * 12 / 100);
            r.DrawCircle((210, 180, 120), (px, py), Math.Max(1, s * 1 / 100), alpha: (byte)(180 - sd * 12));
        }

        // Revving motion lines
        for (int ml = 0; ml < 5; ml++)
        {
            int mx = sawX - s * 5 / 100 - ml * s * 3 / 100;
            int my = sawY + s * 3 / 100 + ml * s * 2 / 100;
            r.DrawLine((255, 200, 80), (mx, my), (mx - s * 6 / 100, my), width: 1, alpha: (byte)(150 - ml * 25));
        }

        // Destructive sparks
        DrawSparkle4(r, bladeX + s * 10 / 100, sawY - s * 4 / 100, s * 3 / 100, (255, 220, 80), 200);
        DrawSparkle4(r, bladeX + s * 8 / 100, sawY + sawH + s * 4 / 100, s * 2 / 100, (255, 200, 60), 170);
    }

    // Dark Angel Unicorn — dark wings, cracked halo, graveyard crosses
    private static void DrawUni_DarkAngel(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Ethereal mist at bottom
        for (int m = 0; m < 8; m++)
        {
            int mx = x + m * w / 8;
            int my = cy + s * 25 / 100 + (int)(Math.Sin(m * 0.9) * s * 2 / 100);
            r.DrawCircle((80, 60, 120), (mx, my), s * 6 / 100, alpha: 60);
        }

        // Graveyard crosses at bottom
        for (int gc = 0; gc < 3; gc++)
        {
            int gx = cx - s * 22 / 100 + gc * s * 18 / 100;
            int gy = cy + s * 18 / 100;
            r.DrawRect((50, 40, 60), (gx - 1, gy, 3, s * 10 / 100), alpha: 180);
            r.DrawRect((50, 40, 60), (gx - s * 3 / 100, gy + s * 2 / 100, s * 6 / 100, 3), alpha: 180);
        }

        // Large dark wings — left
        for (int f = 0; f < 6; f++)
        {
            int fx = cx - s * 10 / 100 - f * s * 5 / 100;
            int fy = cy - s * 5 / 100 + f * s * 2 / 100;
            int fh = s * (20 - f * 2) / 100;
            r.DrawLine((40, 25, 60), (cx - s * 5 / 100, cy - s * 3 / 100), (fx, fy - fh / 2), width: 2, alpha: (byte)(200 - f * 20));
            r.DrawLine((40, 25, 60), (fx, fy - fh / 2), (fx, fy + fh / 2), width: 1, alpha: (byte)(160 - f * 15));
        }
        // Right wing
        for (int f = 0; f < 6; f++)
        {
            int fx = cx + s * 10 / 100 + f * s * 5 / 100;
            int fy = cy - s * 5 / 100 + f * s * 2 / 100;
            int fh = s * (20 - f * 2) / 100;
            r.DrawLine((40, 25, 60), (cx + s * 5 / 100, cy - s * 3 / 100), (fx, fy - fh / 2), width: 2, alpha: (byte)(200 - f * 20));
            r.DrawLine((40, 25, 60), (fx, fy - fh / 2), (fx, fy + fh / 2), width: 1, alpha: (byte)(160 - f * 15));
        }

        // Body — dark silhouette
        r.DrawCircle((60, 45, 80), (cx, cy + s * 2 / 100), s * 10 / 100, alpha: 230);
        // Head
        r.DrawCircle((70, 55, 90), (cx, cy - s * 10 / 100), s * 7 / 100, alpha: 245);
        // Glowing eyes
        r.DrawCircle((160, 100, 255), (cx - s * 3 / 100, cy - s * 11 / 100), s * 2 / 100, alpha: 200);
        r.DrawCircle((160, 100, 255), (cx + s * 3 / 100, cy - s * 11 / 100), s * 2 / 100, alpha: 200);

        // Horn
        DrawHorn(r, cx, cy - s * 17 / 100, s * 10 / 100, (80, 50, 120), (180, 120, 255));

        // Cracked glowing halo above
        int haloY2 = cy - s * 24 / 100;
        r.DrawCircle((200, 160, 255), (cx, haloY2), s * 8 / 100, width: 2, alpha: 180);
        // Cracks in halo
        r.DrawLine((120, 80, 180), (cx - s * 5 / 100, haloY2), (cx - s * 7 / 100, haloY2 - s * 3 / 100), width: 1, alpha: 150);
        r.DrawLine((120, 80, 180), (cx + s * 4 / 100, haloY2 + s * 1 / 100), (cx + s * 6 / 100, haloY2 + s * 4 / 100), width: 1, alpha: 150);
        r.DrawLine((120, 80, 180), (cx, haloY2 - s * 6 / 100), (cx + s * 2 / 100, haloY2 - s * 9 / 100), width: 1, alpha: 130);

        DrawSparkle4(r, cx - s * 20 / 100, cy - s * 18 / 100, s * 2 / 100, (150, 100, 220), 120);
        DrawSparkle4(r, cx + s * 22 / 100, cy - s * 14 / 100, s * 3 / 100, (150, 100, 220), 100);
    }

    // Queen Bee Unicorn — honeycomb, bee stripes, crown, honey drips
    private static void DrawUni_QueenBee(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Honeycomb pattern background
        for (int row = 0; row < 5; row++)
            for (int col = 0; col < 5; col++)
            {
                int hx = x + s * 5 / 100 + col * s * 10 / 100 + (row % 2) * s * 5 / 100;
                int hy = y + s * 5 / 100 + row * s * 9 / 100;
                DrawHexagon(r, hx, hy, s * 5 / 100, (200, 170, 40), 60);
            }

        // Bee-striped body
        int bodyCx3 = cx, bodyCy3 = cy + s * 5 / 100;
        r.DrawCircle((240, 200, 40), (bodyCx3, bodyCy3), s * 12 / 100, alpha: 230);
        // Black stripes
        for (int stripe = 0; stripe < 4; stripe++)
        {
            int sy2 = bodyCy3 - s * 6 / 100 + stripe * s * 4 / 100;
            r.DrawRect((20, 20, 20), (bodyCx3 - s * 11 / 100, sy2, s * 22 / 100, s * 2 / 100), alpha: 180);
        }

        // Transparent wings
        for (int side = -1; side <= 1; side += 2)
        {
            int wCx = bodyCx3 + side * s * 14 / 100;
            int wCy = bodyCy3 - s * 8 / 100;
            r.DrawCircle((255, 255, 255), (wCx, wCy), s * 8 / 100, alpha: 60);
            r.DrawCircle((255, 255, 255), (wCx, wCy), s * 8 / 100, width: 1, alpha: 120);
            r.DrawCircle((255, 255, 255), (wCx + side * s * 3 / 100, wCy - s * 4 / 100), s * 5 / 100, alpha: 50);
            r.DrawCircle((255, 255, 255), (wCx + side * s * 3 / 100, wCy - s * 4 / 100), s * 5 / 100, width: 1, alpha: 100);
        }

        // Head
        r.DrawCircle((240, 200, 40), (cx, cy - s * 10 / 100), s * 7 / 100, alpha: 250);
        // Cute eyes
        r.DrawCircle((20, 20, 20), (cx - s * 3 / 100, cy - s * 11 / 100), s * 2 / 100, alpha: 240);
        r.DrawCircle((20, 20, 20), (cx + s * 3 / 100, cy - s * 11 / 100), s * 2 / 100, alpha: 240);
        r.DrawCircle((255, 255, 255), (cx - s * 3 / 100 + 1, cy - s * 12 / 100), s * 1 / 100, alpha: 220);
        r.DrawCircle((255, 255, 255), (cx + s * 3 / 100 + 1, cy - s * 12 / 100), s * 1 / 100, alpha: 220);

        // Crown
        int crownY = cy - s * 17 / 100;
        r.DrawRect((255, 215, 0), (cx - s * 7 / 100, crownY, s * 14 / 100, s * 4 / 100), alpha: 230);
        DrawFilledTriangleUp(r, cx - s * 7 / 100, crownY - s * 4 / 100, s * 5 / 100, s * 4 / 100, (255, 215, 0), 230);
        DrawFilledTriangleUp(r, cx - s * 2 / 100, crownY - s * 5 / 100, s * 4 / 100, s * 5 / 100, (255, 215, 0), 230);
        DrawFilledTriangleUp(r, cx + s * 3 / 100, crownY - s * 4 / 100, s * 5 / 100, s * 4 / 100, (255, 215, 0), 230);

        // Horn through crown
        DrawHorn(r, cx, crownY - s * 5 / 100, s * 8 / 100, (255, 200, 40), (255, 240, 100));

        // Honey drips
        for (int hd = 0; hd < 4; hd++)
        {
            int hdx = cx - s * 10 / 100 + hd * s * 7 / 100;
            int hdy = bodyCy3 + s * 12 / 100;
            r.DrawLine((220, 180, 30), (hdx, hdy), (hdx, hdy + s * 6 / 100 + hd * s * 1 / 100), width: 2, alpha: 200);
            r.DrawCircle((220, 180, 30), (hdx, hdy + s * 7 / 100 + hd * s * 1 / 100), s * 2 / 100, alpha: 200);
        }

        // Small bees orbiting
        for (int be = 0; be < 4; be++)
        {
            double ang = be * Math.PI / 2 + 0.3;
            int bex = cx + (int)(Math.Cos(ang) * s * 28 / 100);
            int bey = cy + (int)(Math.Sin(ang) * s * 22 / 100);
            r.DrawCircle((240, 200, 40), (bex, bey), s * 2 / 100, alpha: 200);
            r.DrawCircle((20, 20, 20), (bex, bey + s * 1 / 100), s * 1 / 100, alpha: 180);
            r.DrawLine((255, 255, 255), (bex - s * 2 / 100, bey - s * 1 / 100), (bex - s * 4 / 100, bey - s * 3 / 100), width: 1, alpha: 120);
            r.DrawLine((255, 255, 255), (bex + s * 2 / 100, bey - s * 1 / 100), (bex + s * 4 / 100, bey - s * 3 / 100), width: 1, alpha: 120);
        }
    }

    // Corn Cob Unicorn — ear of corn body, corn silk mane, butter melting
    private static void DrawUni_CornCob(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Husk leaves as wings
        for (int side = -1; side <= 1; side += 2)
        {
            for (int leaf = 0; leaf < 3; leaf++)
            {
                int lx = cx + side * (s * 12 / 100 + leaf * s * 5 / 100);
                int ly = cy + leaf * s * 5 / 100;
                int lw = s * 10 / 100, lh = s * 18 / 100;
                r.DrawCircle((100, 160, 50), (lx, ly), lw, alpha: (byte)(160 - leaf * 30));
            }
        }

        // Corn cob body — elongated oval
        int cobW = s * 14 / 100, cobH = s * 32 / 100;
        r.DrawCircle((240, 210, 60), (cx, cy), cobW, alpha: 240);
        r.DrawCircle((240, 210, 60), (cx, cy - s * 5 / 100), cobW * 9 / 10, alpha: 240);
        r.DrawCircle((240, 210, 60), (cx, cy + s * 5 / 100), cobW * 9 / 10, alpha: 240);
        r.DrawCircle((240, 210, 60), (cx, cy + s * 10 / 100), cobW * 8 / 10, alpha: 230);
        r.DrawCircle((240, 210, 60), (cx, cy - s * 10 / 100), cobW * 8 / 10, alpha: 230);

        // Kernel grid pattern
        for (int row = -4; row <= 4; row++)
            for (int col = -2; col <= 2; col++)
            {
                int kx = cx + col * s * 4 / 100 + (row % 2) * s * 2 / 100;
                int ky = cy + row * s * 4 / 100;
                r.DrawCircle((255, 230, 80), (kx, ky), s * 2 / 100, alpha: 200);
                r.DrawCircle((245, 220, 60), (kx, ky), s * 2 / 100, width: 1, alpha: 140);
            }

        // Corn silk as mane — wispy lines from top
        for (int silk = 0; silk < 8; silk++)
        {
            int sx2 = cx - s * 8 / 100 + silk * s * 2 / 100;
            int sy2 = cy - s * 16 / 100;
            int endX = sx2 + (int)(Math.Sin(silk * 0.7) * s * 8 / 100);
            int endY = sy2 - s * 12 / 100 - silk * s * 1 / 100;
            r.DrawLine((220, 200, 120), (sx2, sy2), (endX, endY), width: 1, alpha: (byte)(180 - silk * 12));
        }

        // Cute face
        r.DrawCircle((20, 20, 20), (cx - s * 4 / 100, cy - s * 7 / 100), s * 2 / 100, alpha: 220);
        r.DrawCircle((20, 20, 20), (cx + s * 4 / 100, cy - s * 7 / 100), s * 2 / 100, alpha: 220);
        r.DrawCircle((255, 255, 255), (cx - s * 4 / 100 + 1, cy - s * 8 / 100), s * 1 / 100, alpha: 200);
        r.DrawCircle((255, 255, 255), (cx + s * 4 / 100 + 1, cy - s * 8 / 100), s * 1 / 100, alpha: 200);
        // Smile
        r.DrawCircle((200, 120, 80), (cx, cy - s * 4 / 100), s * 2 / 100, width: 1, alpha: 150);

        // Butter melting on top
        r.DrawRect((255, 230, 80), (cx - s * 5 / 100, cy - s * 15 / 100, s * 10 / 100, s * 4 / 100), alpha: 200);
        r.DrawCircle((255, 240, 100), (cx - s * 5 / 100, cy - s * 12 / 100), s * 2 / 100, alpha: 180);
        r.DrawLine((255, 230, 80), (cx - s * 5 / 100, cy - s * 12 / 100), (cx - s * 6 / 100, cy - s * 8 / 100), width: 2, alpha: 170);

        // Horn from top
        DrawHorn(r, cx, cy - s * 17 / 100, s * 10 / 100, (240, 210, 60), (255, 240, 120));
    }

    // Seductive Unicorn — hearts, kiss mark, rose, pink glow
    private static void DrawUni_Seductive(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Red/pink glow behind
        r.DrawCircle((255, 60, 120), (cx, cy), s * 30 / 100, alpha: 40);
        r.DrawCircle((255, 100, 150), (cx, cy - s * 5 / 100), s * 20 / 100, alpha: 50);

        // Unicorn silhouette — elegant pose
        r.DrawCircle((230, 200, 220), (cx, cy + s * 3 / 100), s * 11 / 100, alpha: 235);
        r.DrawCircle((220, 190, 210), (cx - s * 3 / 100, cy + s * 10 / 100), s * 6 / 100, alpha: 220);

        // Head with heavy lashes
        int headCy3 = cy - s * 10 / 100;
        r.DrawCircle((235, 210, 225), (cx, headCy3), s * 8 / 100, alpha: 250);
        // Bedroom eyes — half-closed with heavy lashes
        r.DrawCircle((80, 40, 120), (cx - s * 4 / 100, headCy3), s * 2 / 100, alpha: 230);
        r.DrawCircle((80, 40, 120), (cx + s * 4 / 100, headCy3), s * 2 / 100, alpha: 230);
        // Lashes
        for (int lash = 0; lash < 3; lash++)
        {
            r.DrawLine((40, 20, 40), (cx - s * 4 / 100 + lash * s * 1 / 100 - 1, headCy3 - s * 2 / 100), (cx - s * 5 / 100 + lash * s * 1 / 100, headCy3 - s * 4 / 100), width: 1, alpha: 200);
            r.DrawLine((40, 20, 40), (cx + s * 3 / 100 + lash * s * 1 / 100, headCy3 - s * 2 / 100), (cx + s * 2 / 100 + lash * s * 1 / 100, headCy3 - s * 4 / 100), width: 1, alpha: 200);
        }

        // Red lipstick kiss mark
        int kissX = cx + s * 16 / 100, kissY = cy - s * 18 / 100;
        r.DrawCircle((220, 30, 60), (kissX - s * 2 / 100, kissY), s * 3 / 100, alpha: 200);
        r.DrawCircle((220, 30, 60), (kissX + s * 2 / 100, kissY), s * 3 / 100, alpha: 200);
        r.DrawCircle((220, 30, 60), (kissX, kissY + s * 2 / 100), s * 2 / 100, alpha: 190);

        // Horn — pink
        DrawHorn(r, cx, headCy3 - s * 8 / 100, s * 10 / 100, (255, 100, 160), (255, 200, 220));

        // Rose
        int roseX = cx - s * 16 / 100, roseY = cy + s * 5 / 100;
        r.DrawCircle((200, 30, 50), (roseX, roseY), s * 4 / 100, alpha: 220);
        r.DrawCircle((220, 40, 60), (roseX + s * 1 / 100, roseY - s * 1 / 100), s * 3 / 100, alpha: 210);
        r.DrawCircle((180, 20, 40), (roseX - s * 1 / 100, roseY + s * 1 / 100), s * 3 / 100, alpha: 200);
        // Stem
        r.DrawLine((40, 120, 40), (roseX, roseY + s * 4 / 100), (roseX + s * 2 / 100, roseY + s * 14 / 100), width: 2, alpha: 180);
        // Leaf
        r.DrawCircle((60, 140, 50), (roseX + s * 3 / 100, roseY + s * 10 / 100), s * 2 / 100, alpha: 160);

        // Hearts floating everywhere
        for (int heart = 0; heart < 8; heart++)
        {
            int hx = cx + (int)(Math.Cos(heart * 0.8 + 0.5) * s * 28 / 100);
            int hy = cy - s * 20 / 100 + (int)(Math.Sin(heart * 1.1) * s * 18 / 100);
            int hs = Math.Max(2, s * (4 - heart / 3) / 100);
            byte ha = (byte)(200 - heart * 18);
            // Heart shape from two circles + triangle
            r.DrawCircle((255, 80, 120), (hx - hs / 2, hy - hs / 3), hs * 6 / 10, alpha: ha);
            r.DrawCircle((255, 80, 120), (hx + hs / 2, hy - hs / 3), hs * 6 / 10, alpha: ha);
            DrawFilledTriangleDown(r, hx - hs, hy - hs / 4, hs * 2, hs, (255, 80, 120), ha);
        }

        // Perfume bottle
        int perfX = cx + s * 20 / 100, perfY = cy + s * 12 / 100;
        r.DrawRect((200, 160, 220), (perfX - s * 2 / 100, perfY, s * 4 / 100, s * 6 / 100), alpha: 180);
        r.DrawRect((220, 180, 240), (perfX - s * 1 / 100, perfY - s * 2 / 100, s * 2 / 100, s * 2 / 100), alpha: 180);
        DrawSparkle4(r, perfX, perfY - s * 4 / 100, s * 2 / 100, (255, 200, 255), 140);
    }

    // Americorn — stars and stripes, liberty torch, eagle silhouette
    private static void DrawUni_Americorn(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Eagle silhouette above
        int eagleY = cy - s * 28 / 100;
        r.DrawLine((180, 160, 120), (cx, eagleY), (cx - s * 15 / 100, eagleY + s * 8 / 100), width: 2, alpha: 160);
        r.DrawLine((180, 160, 120), (cx, eagleY), (cx + s * 15 / 100, eagleY + s * 8 / 100), width: 2, alpha: 160);
        r.DrawLine((180, 160, 120), (cx - s * 15 / 100, eagleY + s * 8 / 100), (cx - s * 20 / 100, eagleY + s * 5 / 100), width: 1, alpha: 140);
        r.DrawLine((180, 160, 120), (cx + s * 15 / 100, eagleY + s * 8 / 100), (cx + s * 20 / 100, eagleY + s * 5 / 100), width: 1, alpha: 140);
        r.DrawCircle((180, 160, 120), (cx, eagleY + s * 2 / 100), s * 3 / 100, alpha: 150);

        // Unicorn body with stripes
        int bodyCx4 = cx, bodyCy4 = cy + s * 5 / 100;
        r.DrawCircle((220, 210, 230), (bodyCx4, bodyCy4), s * 12 / 100, alpha: 230);
        // Red and white stripes
        for (int stripe = 0; stripe < 6; stripe++)
        {
            int sy2 = bodyCy4 - s * 8 / 100 + stripe * s * 3 / 100;
            var sc = stripe % 2 == 0 ? (200, 40, 40) : (240, 240, 240);
            r.DrawRect(sc, (bodyCx4 - s * 11 / 100, sy2, s * 22 / 100, s * 2 / 100), alpha: 170);
        }

        // Blue canton with stars
        r.DrawRect((30, 40, 100), (bodyCx4 - s * 11 / 100, bodyCy4 - s * 8 / 100, s * 10 / 100, s * 8 / 100), alpha: 180);
        for (int star = 0; star < 5; star++)
        {
            int stx = bodyCx4 - s * 9 / 100 + (star % 3) * s * 4 / 100;
            int sty = bodyCy4 - s * 6 / 100 + (star / 3) * s * 4 / 100;
            DrawStar5(r, stx, sty, s * 2 / 100, (255, 255, 255), 200);
        }

        // Head
        r.DrawCircle((230, 220, 240), (cx, cy - s * 10 / 100), s * 7 / 100, alpha: 250);

        // Horn — red/white/blue spiral
        DrawHorn(r, cx, cy - s * 17 / 100, s * 12 / 100, (200, 40, 40), (30, 40, 120));

        // Liberty torch in hoof
        int torchX = cx + s * 18 / 100, torchY = cy;
        r.DrawRect((160, 140, 80), (torchX - 2, torchY - s * 10 / 100, 4, s * 16 / 100), alpha: 220);
        // Flame glow
        r.DrawCircle((255, 200, 40), (torchX, torchY - s * 12 / 100), s * 4 / 100, alpha: 200);
        r.DrawCircle((255, 240, 100), (torchX, torchY - s * 13 / 100), s * 3 / 100, alpha: 220);
        r.DrawCircle((255, 255, 200), (torchX, torchY - s * 14 / 100), s * 2 / 100, alpha: 240);

        // Stars scattered
        for (int st = 0; st < 6; st++)
        {
            int stx = cx + (int)(Math.Cos(st * 1.1) * s * 30 / 100);
            int sty = cy + (int)(Math.Sin(st * 1.5) * s * 22 / 100);
            DrawStar5(r, stx, sty, s * 2 / 100, (255, 255, 200), (byte)(160 - st * 15));
        }
    }

    // Narwhal Torpedo — torpedo body with narwhal horn, exhaust flames, explosion
    private static void DrawUni_NarwhalTorpedo(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Water spray
        for (int sp = 0; sp < 6; sp++)
        {
            int spx = cx + (int)(Math.Cos(sp * 1.0 + 2) * s * 28 / 100);
            int spy = cy + s * 8 / 100 + (int)(Math.Sin(sp * 1.4) * s * 5 / 100);
            r.DrawCircle((100, 180, 240), (spx, spy), s * 3 / 100, alpha: (byte)(80 - sp * 8));
        }

        // Torpedo/missile body — elongated horizontal
        int torpY = cy;
        r.DrawCircle((80, 90, 100), (cx, torpY), s * 8 / 100, alpha: 240);
        r.DrawCircle((80, 90, 100), (cx - s * 8 / 100, torpY), s * 7 / 100, alpha: 235);
        r.DrawCircle((80, 90, 100), (cx + s * 8 / 100, torpY), s * 6 / 100, alpha: 235);
        r.DrawCircle((80, 90, 100), (cx - s * 14 / 100, torpY), s * 5 / 100, alpha: 220);

        // Tail fins
        DrawFilledTriangleUp(r, cx - s * 20 / 100, torpY - s * 10 / 100, s * 8 / 100, s * 8 / 100, (70, 80, 90), 220);
        DrawFilledTriangleDown(r, cx - s * 20 / 100, torpY + s * 2 / 100, s * 8 / 100, s * 8 / 100, (70, 80, 90), 220);

        // Narwhal horn as warhead — pointing right
        r.DrawLine((200, 200, 220), (cx + s * 14 / 100, torpY), (cx + s * 30 / 100, torpY), width: 3, alpha: 240);
        // Spiral lines on horn
        for (int sp = 0; sp < 6; sp++)
        {
            int spx = cx + s * 16 / 100 + sp * s * 3 / 100;
            r.DrawLine((180, 220, 255), (spx, torpY - s * 1 / 100), (spx + s * 1 / 100, torpY + s * 1 / 100), width: 1, alpha: 160);
        }

        // Narwhal eye
        r.DrawCircle((20, 20, 20), (cx + s * 6 / 100, torpY - s * 3 / 100), s * 2 / 100, alpha: 240);
        r.DrawCircle((255, 255, 255), (cx + s * 6 / 100 + 1, torpY - s * 4 / 100), s * 1 / 100, alpha: 220);

        // Exhaust flames behind
        for (int ef = 0; ef < 6; ef++)
        {
            int fx = cx - s * 22 / 100 - ef * s * 4 / 100;
            int fy = torpY + (int)(Math.Sin(ef * 1.2) * s * 3 / 100);
            var fc = ef < 2 ? (255, 240, 80) : ef < 4 ? (255, 160, 30) : (255, 80, 20);
            r.DrawCircle(fc, (fx, fy), Math.Max(2, s * (5 - ef) / 100), alpha: (byte)(200 - ef * 25));
        }

        // Explosion / impact star at horn tip
        DrawSparkle4(r, cx + s * 30 / 100, torpY, s * 5 / 100, (255, 255, 200), 200);
        DrawStar5(r, cx + s * 30 / 100, torpY, s * 7 / 100, (255, 200, 80), 140);

        // Bubbles
        for (int b = 0; b < 5; b++)
        {
            int bx = cx + (int)(Math.Cos(b * 1.8) * s * 20 / 100);
            int by = torpY + s * 12 / 100 + b * s * 2 / 100;
            r.DrawCircle((140, 200, 255), (bx, by), Math.Max(1, s * 2 / 100), width: 1, alpha: 100);
        }
    }

    // Great Narwhal — massive majestic narwhal, crown, ocean waves
    private static void DrawUni_GreatNarwhal(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Ocean waves at bottom
        for (int wave = 0; wave < 8; wave++)
        {
            int wx = x + wave * w / 8;
            int wy = cy + s * 22 / 100 + (int)(Math.Sin(wave * 1.0) * s * 2 / 100);
            r.DrawCircle((30, 80, 140), (wx, wy), s * 6 / 100, alpha: 90);
        }

        // Massive narwhal body
        int bodyCx5 = cx, bodyCy5 = cy + s * 5 / 100;
        r.DrawCircle((80, 110, 140), (bodyCx5, bodyCy5), s * 16 / 100, alpha: 235);
        r.DrawCircle((80, 110, 140), (bodyCx5 - s * 10 / 100, bodyCy5 + s * 2 / 100), s * 12 / 100, alpha: 225);
        r.DrawCircle((80, 110, 140), (bodyCx5 + s * 8 / 100, bodyCy5 - s * 2 / 100), s * 12 / 100, alpha: 225);
        // Whale-scale pattern
        for (int row = 0; row < 3; row++)
            for (int col = -2; col <= 2; col++)
            {
                int scx = bodyCx5 + col * s * 6 / 100 + (row % 2) * s * 3 / 100;
                int scy = bodyCy5 + row * s * 5 / 100 - s * 2 / 100;
                r.DrawCircle((100, 130, 160), (scx, scy), s * 3 / 100, width: 1, alpha: 80);
            }

        // Tail fin
        DrawFilledTriangleUp(r, bodyCx5 - s * 25 / 100, bodyCy5 - s * 2 / 100, s * 10 / 100, s * 10 / 100, (70, 100, 130), 200);
        DrawFilledTriangleDown(r, bodyCx5 - s * 25 / 100, bodyCy5 + s * 8 / 100, s * 10 / 100, s * 8 / 100, (70, 100, 130), 200);

        // Head
        r.DrawCircle((90, 120, 150), (bodyCx5 + s * 14 / 100, bodyCy5 - s * 3 / 100), s * 9 / 100, alpha: 240);
        // Eye
        r.DrawCircle((20, 30, 40), (bodyCx5 + s * 16 / 100, bodyCy5 - s * 5 / 100), s * 2 / 100, alpha: 240);
        r.DrawCircle((255, 255, 255), (bodyCx5 + s * 16 / 100 + 1, bodyCy5 - s * 6 / 100), s * 1 / 100, alpha: 220);

        // Large spiraling tusk
        r.DrawLine((220, 220, 240), (bodyCx5 + s * 22 / 100, bodyCy5 - s * 4 / 100), (bodyCx5 + s * 40 / 100, bodyCy5 - s * 6 / 100), width: 3, alpha: 230);
        for (int sp = 0; sp < 8; sp++)
        {
            int spx = bodyCx5 + s * 24 / 100 + sp * s * 2 / 100;
            int spy = bodyCy5 - s * 4 / 100 - sp * s * 1 / 200;
            r.DrawLine((200, 230, 255), (spx, spy - s * 1 / 100), (spx + s * 1 / 100, spy + s * 1 / 100), width: 1, alpha: 150);
        }

        // Crown atop head
        int crownX2 = bodyCx5 + s * 12 / 100;
        int crownY2 = bodyCy5 - s * 14 / 100;
        r.DrawRect((255, 215, 0), (crownX2 - s * 5 / 100, crownY2, s * 10 / 100, s * 3 / 100), alpha: 220);
        DrawFilledTriangleUp(r, crownX2 - s * 5 / 100, crownY2 - s * 3 / 100, s * 3 / 100, s * 3 / 100, (255, 215, 0), 220);
        DrawFilledTriangleUp(r, crownX2 - s * 1 / 100, crownY2 - s * 4 / 100, s * 3 / 100, s * 4 / 100, (255, 215, 0), 220);
        DrawFilledTriangleUp(r, crownX2 + s * 3 / 100, crownY2 - s * 3 / 100, s * 3 / 100, s * 3 / 100, (255, 215, 0), 220);

        DrawSparkle4(r, bodyCx5 + s * 38 / 100, bodyCy5 - s * 8 / 100, s * 3 / 100, (200, 230, 255), 180);
    }

    // Classy Narwhal — top hat, monocle, bow tie, cane, mustache
    private static void DrawUni_ClassyNarwhal(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Narwhal body
        r.DrawCircle((80, 110, 150), (cx, cy + s * 5 / 100), s * 13 / 100, alpha: 235);
        r.DrawCircle((80, 110, 150), (cx - s * 8 / 100, cy + s * 7 / 100), s * 9 / 100, alpha: 220);

        // Tail fin
        DrawFilledTriangleUp(r, cx - s * 20 / 100, cy + s * 2 / 100, s * 8 / 100, s * 8 / 100, (70, 100, 140), 200);
        DrawFilledTriangleDown(r, cx - s * 20 / 100, cy + s * 10 / 100, s * 8 / 100, s * 6 / 100, (70, 100, 140), 200);

        // Head
        r.DrawCircle((90, 120, 160), (cx + s * 8 / 100, cy - s * 5 / 100), s * 9 / 100, alpha: 245);

        // Top hat
        int hatX = cx + s * 8 / 100, hatY = cy - s * 18 / 100;
        r.DrawRect((20, 20, 30), (hatX - s * 8 / 100, hatY, s * 16 / 100, s * 2 / 100), alpha: 240);
        r.DrawRect((30, 30, 40), (hatX - s * 5 / 100, hatY - s * 12 / 100, s * 10 / 100, s * 12 / 100), alpha: 230);
        r.DrawRect((60, 40, 40), (hatX - s * 5 / 100, hatY - s * 4 / 100, s * 10 / 100, s * 2 / 100), alpha: 180);

        // Monocle on right eye
        int monX = cx + s * 12 / 100, monY = cy - s * 5 / 100;
        r.DrawCircle((200, 200, 220), (monX, monY), s * 4 / 100, width: 2, alpha: 200);
        r.DrawCircle((255, 255, 255), (monX, monY), s * 3 / 100, alpha: 30);
        // Chain
        r.DrawLine((200, 200, 180), (monX, monY + s * 4 / 100), (monX + s * 2 / 100, cy + s * 3 / 100), width: 1, alpha: 150);

        // Fancy mustache
        int mustY = cy - s * 2 / 100;
        for (int side = -1; side <= 1; side += 2)
        {
            r.DrawLine((30, 20, 10), (cx + s * 8 / 100, mustY), (cx + s * 8 / 100 + side * s * 6 / 100, mustY - s * 2 / 100), width: 2, alpha: 220);
            r.DrawCircle((30, 20, 10), (cx + s * 8 / 100 + side * s * 6 / 100, mustY - s * 2 / 100), s * 1 / 100, alpha: 200);
        }

        // Bow tie
        int bowX = cx + s * 2 / 100, bowY = cy + s * 4 / 100;
        DrawFilledTriangleUp(r, bowX - s * 5 / 100, bowY - s * 2 / 100, s * 5 / 100, s * 4 / 100, (180, 30, 30), 210);
        DrawFilledTriangleUp(r, bowX, bowY - s * 2 / 100, s * 5 / 100, s * 4 / 100, (180, 30, 30), 210);
        r.DrawCircle((200, 40, 40), (bowX, bowY), s * 1 / 100, alpha: 220);

        // Walking cane
        int caneX = cx - s * 15 / 100;
        r.DrawRect((120, 80, 30), (caneX - 1, cy - s * 10 / 100, 3, s * 28 / 100), alpha: 220);
        r.DrawCircle((140, 100, 40), (caneX, cy - s * 10 / 100), s * 2 / 100, alpha: 210);

        // Tusk/horn
        r.DrawLine((220, 220, 240), (cx + s * 16 / 100, cy - s * 6 / 100), (cx + s * 30 / 100, cy - s * 8 / 100), width: 2, alpha: 220);

        // Left eye
        r.DrawCircle((20, 30, 40), (cx + s * 5 / 100, cy - s * 6 / 100), s * 2 / 100, alpha: 230);
        r.DrawCircle((255, 255, 255), (cx + s * 5 / 100 + 1, cy - s * 7 / 100), s * 1 / 100, alpha: 210);

        DrawSparkle4(r, cx + s * 28 / 100, cy - s * 12 / 100, s * 2 / 100, (220, 220, 240), 140);
    }

    // Alluring Narwhal — bioluminescent, flowing fins, underwater sparkles
    private static void DrawUni_AlluringNarwhal(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Underwater sparkles background
        for (int sp = 0; sp < 12; sp++)
        {
            int spx = cx + (int)(Math.Cos(sp * 0.8 + 0.3) * s * 35 / 100);
            int spy = cy + (int)(Math.Sin(sp * 1.1 + 0.5) * s * 28 / 100);
            DrawSparkle4(r, spx, spy, s * 2 / 100, (80, 200, 255), (byte)(100 - sp * 5));
        }

        // Narwhal body — elegant shape
        r.DrawCircle((60, 130, 170), (cx, cy + s * 3 / 100), s * 14 / 100, alpha: 230);
        r.DrawCircle((60, 130, 170), (cx - s * 8 / 100, cy + s * 5 / 100), s * 10 / 100, alpha: 220);
        r.DrawCircle((70, 140, 180), (cx + s * 6 / 100, cy), s * 10 / 100, alpha: 225);

        // Bioluminescent glow spots
        for (int gs = 0; gs < 8; gs++)
        {
            int gx = cx - s * 10 / 100 + gs * s * 4 / 100;
            int gy = cy + s * 3 / 100 + (int)(Math.Sin(gs * 0.8) * s * 3 / 100);
            r.DrawCircle((100, 220, 255), (gx, gy), s * 2 / 100, alpha: (byte)(180 - gs * 12));
            r.DrawCircle((160, 240, 255), (gx, gy), s * 1 / 100, alpha: (byte)(220 - gs * 12));
        }

        // Flowing fins — ethereal
        for (int fin = 0; fin < 4; fin++)
        {
            int fx = cx - s * 5 / 100 + fin * s * 4 / 100;
            int fy = cy + s * 12 / 100;
            int endX = fx + (int)(Math.Sin(fin * 0.8) * s * 6 / 100);
            int endY = fy + s * 12 / 100;
            r.DrawLine((80, 180, 220), (fx, fy), (endX, endY), width: 2, alpha: (byte)(150 - fin * 20));
            r.DrawCircle((100, 200, 240), (endX, endY), s * 2 / 100, alpha: (byte)(100 - fin * 15));
        }

        // Tail
        DrawFilledTriangleUp(r, cx - s * 20 / 100, cy + s * 1 / 100, s * 8 / 100, s * 8 / 100, (50, 110, 150), 200);
        DrawFilledTriangleDown(r, cx - s * 20 / 100, cy + s * 9 / 100, s * 8 / 100, s * 6 / 100, (50, 110, 150), 200);

        // Head
        r.DrawCircle((80, 140, 185), (cx + s * 12 / 100, cy - s * 3 / 100), s * 8 / 100, alpha: 245);
        // Eye — alluring glow
        r.DrawCircle((160, 240, 255), (cx + s * 14 / 100, cy - s * 5 / 100), s * 3 / 100, alpha: 200);
        r.DrawCircle((220, 255, 255), (cx + s * 14 / 100, cy - s * 5 / 100), s * 2 / 100, alpha: 240);
        r.DrawCircle((40, 60, 80), (cx + s * 14 / 100, cy - s * 5 / 100), s * 1 / 100, alpha: 250);

        // Alluring spiral horn
        r.DrawLine((180, 230, 255), (cx + s * 18 / 100, cy - s * 5 / 100), (cx + s * 34 / 100, cy - s * 7 / 100), width: 3, alpha: 230);
        for (int sp = 0; sp < 7; sp++)
        {
            int spx = cx + s * 20 / 100 + sp * s * 2 / 100;
            int spy = cy - s * 5 / 100 - sp * s * 1 / 200;
            r.DrawCircle((200, 240, 255), (spx, spy), s * 1 / 100, alpha: (byte)(200 - sp * 15));
        }

        // Trailing glow particles
        for (int p = 0; p < 5; p++)
        {
            int px = cx - s * 20 / 100 - p * s * 5 / 100;
            int py = cy + s * 5 / 100 + (int)(Math.Sin(p * 1.2) * s * 4 / 100);
            r.DrawCircle((80, 200, 255), (px, py), Math.Max(1, s * (3 - p) / 100), alpha: (byte)(120 - p * 18));
        }
    }

    // Fertile Unicorn — baby unicorns, baby bottles, stork carrying bundle
    private static void DrawUni_Fertile(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Soft pink/lavender glow
        r.DrawCircle((235, 130, 200), (cx, cy), s * 28 / 100, alpha: 40);

        // Mother unicorn body — round and nurturing
        r.DrawCircle((220, 200, 235), (cx, cy), s * 13 / 100, alpha: 235);
        // Head
        r.DrawCircle((225, 205, 240), (cx, cy - s * 14 / 100), s * 7 / 100, alpha: 250);
        // Gentle eyes
        r.DrawCircle((100, 60, 140), (cx - s * 3 / 100, cy - s * 15 / 100), s * 2 / 100, alpha: 220);
        r.DrawCircle((100, 60, 140), (cx + s * 3 / 100, cy - s * 15 / 100), s * 2 / 100, alpha: 220);
        // Horn
        DrawHorn(r, cx, cy - s * 21 / 100, s * 8 / 100, (220, 180, 240), (255, 200, 255));

        // Multiple baby unicorn silhouettes (small circles with tiny horns)
        var babyPositions = new[] { (-18, 12), (-8, 18), (8, 16), (18, 10), (0, 22) };
        for (int b = 0; b < babyPositions.Length; b++)
        {
            int bx = cx + babyPositions[b].Item1 * s / 100;
            int by = cy + babyPositions[b].Item2 * s / 100;
            // Baby body
            r.DrawCircle((230, 210, 245), (bx, by), s * 4 / 100, alpha: 210);
            // Baby head
            r.DrawCircle((235, 215, 250), (bx, by - s * 4 / 100), s * 3 / 100, alpha: 220);
            // Tiny horn
            DrawHorn(r, bx, by - s * 7 / 100, s * 3 / 100, (240, 200, 255), (255, 230, 255));
        }

        // Baby bottles
        for (int bt = 0; bt < 2; bt++)
        {
            int btx = cx + (bt == 0 ? -s * 24 / 100 : s * 22 / 100);
            int bty = cy + s * 10 / 100;
            r.DrawRect((220, 220, 240), (btx - s * 2 / 100, bty, s * 4 / 100, s * 8 / 100), alpha: 180);
            r.DrawRect((240, 200, 160), (btx - s * 1 / 100, bty - s * 2 / 100, s * 2 / 100, s * 3 / 100), alpha: 180);
            r.DrawCircle((240, 200, 160), (btx, bty - s * 2 / 100), s * 1 / 100, alpha: 200);
        }

        // Hearts
        for (int ht = 0; ht < 6; ht++)
        {
            int hx = cx + (int)(Math.Cos(ht * 1.0 + 0.3) * s * 30 / 100);
            int hy = cy - s * 15 / 100 + (int)(Math.Sin(ht * 1.3) * s * 10 / 100);
            r.DrawCircle((255, 120, 180), (hx - s * 1 / 100, hy), s * 2 / 100, alpha: (byte)(160 - ht * 15));
            r.DrawCircle((255, 120, 180), (hx + s * 1 / 100, hy), s * 2 / 100, alpha: (byte)(160 - ht * 15));
            DrawFilledTriangleDown(r, hx - s * 2 / 100, hy, s * 4 / 100, s * 3 / 100, (255, 120, 180), (byte)(150 - ht * 15));
        }

        // Stork carrying bundle (top right)
        int storkX = cx + s * 22 / 100, storkY = cy - s * 22 / 100;
        // Bird body
        r.DrawCircle((240, 240, 240), (storkX, storkY), s * 4 / 100, alpha: 180);
        // Wings
        r.DrawLine((220, 220, 220), (storkX, storkY), (storkX - s * 6 / 100, storkY - s * 3 / 100), width: 2, alpha: 160);
        r.DrawLine((220, 220, 220), (storkX, storkY), (storkX + s * 6 / 100, storkY - s * 3 / 100), width: 2, alpha: 160);
        // Beak
        r.DrawLine((255, 160, 60), (storkX + s * 3 / 100, storkY + s * 1 / 100), (storkX + s * 6 / 100, storkY + s * 3 / 100), width: 2, alpha: 180);
        // Bundle
        r.DrawCircle((255, 220, 220), (storkX + s * 6 / 100, storkY + s * 5 / 100), s * 3 / 100, alpha: 160);
        r.DrawLine((200, 180, 180), (storkX + s * 5 / 100, storkY + s * 2 / 100), (storkX + s * 6 / 100, storkY + s * 5 / 100), width: 1, alpha: 140);
    }

    // Annoying Flying Unicorn — wings, buzzing circles, zigzag lines, sweat drops
    private static void DrawUni_AnnoyingFlying(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Buzzing motion circles (like a fly)
        for (int bz = 0; bz < 6; bz++)
        {
            int bzr = s * (12 + bz * 3) / 100;
            r.DrawCircle((200, 200, 100), (cx, cy), bzr, width: 1, alpha: (byte)(80 - bz * 10));
        }

        // Small annoying unicorn body
        r.DrawCircle((200, 190, 160), (cx, cy + s * 2 / 100), s * 9 / 100, alpha: 230);
        // Head
        r.DrawCircle((210, 200, 170), (cx, cy - s * 8 / 100), s * 6 / 100, alpha: 245);
        // Annoyed expression — cross eyes
        r.DrawLine((60, 40, 20), (cx - s * 4 / 100, cy - s * 10 / 100), (cx - s * 2 / 100, cy - s * 8 / 100), width: 2, alpha: 230);
        r.DrawLine((60, 40, 20), (cx - s * 2 / 100, cy - s * 10 / 100), (cx - s * 4 / 100, cy - s * 8 / 100), width: 2, alpha: 230);
        r.DrawLine((60, 40, 20), (cx + s * 2 / 100, cy - s * 10 / 100), (cx + s * 4 / 100, cy - s * 8 / 100), width: 2, alpha: 230);
        r.DrawLine((60, 40, 20), (cx + s * 4 / 100, cy - s * 10 / 100), (cx + s * 2 / 100, cy - s * 8 / 100), width: 2, alpha: 230);

        // Horn
        DrawHorn(r, cx, cy - s * 14 / 100, s * 8 / 100, (200, 190, 140), (240, 230, 180));

        // Small buzzy wings
        for (int side = -1; side <= 1; side += 2)
        {
            int wCx2 = cx + side * s * 12 / 100;
            int wCy2 = cy - s * 3 / 100;
            r.DrawCircle((220, 220, 180), (wCx2, wCy2), s * 6 / 100, alpha: 80);
            r.DrawCircle((220, 220, 180), (wCx2, wCy2), s * 6 / 100, width: 1, alpha: 140);
            // Blur lines for rapid movement
            r.DrawLine((220, 220, 180), (wCx2, wCy2 - s * 5 / 100), (wCx2, wCy2 + s * 5 / 100), width: 1, alpha: 60);
        }

        // Zigzag annoyed lines around head
        for (int z = 0; z < 4; z++)
        {
            double ang = z * Math.PI / 2 + Math.PI / 4;
            int zx1 = cx + (int)(Math.Cos(ang) * s * 14 / 100);
            int zy1 = cy - s * 8 / 100 + (int)(Math.Sin(ang) * s * 10 / 100);
            int zx2 = zx1 + s * 3 / 100;
            int zy2 = zy1 - s * 3 / 100;
            int zx3 = zx2 + s * 3 / 100;
            int zy3 = zy2 + s * 3 / 100;
            r.DrawLine((255, 200, 60), (zx1, zy1), (zx2, zy2), width: 2, alpha: 180);
            r.DrawLine((255, 200, 60), (zx2, zy2), (zx3, zy3), width: 2, alpha: 180);
        }

        // Sweat drops
        for (int sd = 0; sd < 3; sd++)
        {
            int sdx = cx + (sd - 1) * s * 8 / 100;
            int sdy = cy - s * 16 / 100 - sd * s * 2 / 100;
            r.DrawCircle((140, 180, 255), (sdx, sdy), s * 2 / 100, alpha: 160);
            r.DrawCircle((180, 210, 255), (sdx, sdy - s * 1 / 100), s * 1 / 100, alpha: 180);
        }

        // Flies buzzing around
        for (int fl = 0; fl < 4; fl++)
        {
            int fx = cx + (int)(Math.Cos(fl * 1.5 + 1) * s * 24 / 100);
            int fy = cy + (int)(Math.Sin(fl * 1.8) * s * 18 / 100);
            r.DrawCircle((40, 40, 20), (fx, fy), s * 1 / 100, alpha: 180);
            r.DrawLine((80, 80, 60), (fx - s * 2 / 100, fy - s * 1 / 100), (fx + s * 2 / 100, fy - s * 1 / 100), width: 1, alpha: 100);
        }
    }

    // Swift Flying Unicorn — sleek wings, speed lines, wind trail, blur effect
    private static void DrawUni_SwiftFlying(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Blur effect — repeated fading silhouettes behind
        for (int blur = 3; blur >= 1; blur--)
        {
            int bx = cx - blur * s * 8 / 100;
            byte ba = (byte)(60 - blur * 15);
            r.DrawCircle((160, 180, 220), (bx, cy + s * 2 / 100), s * 8 / 100, alpha: ba);
            r.DrawCircle((160, 180, 220), (bx, cy - s * 7 / 100), s * 5 / 100, alpha: ba);
        }

        // Speed lines
        for (int sl = 0; sl < 8; sl++)
        {
            int sly = cy - s * 15 / 100 + sl * s * 4 / 100;
            int slx1 = x + s * 2 / 100;
            int slx2 = cx - s * 15 / 100 - sl * s * 2 / 100;
            r.DrawLine((180, 210, 255), (slx1, sly), (slx2, sly), width: 1, alpha: (byte)(120 - sl * 10));
        }

        // Sleek body
        r.DrawCircle((180, 200, 240), (cx, cy + s * 2 / 100), s * 10 / 100, alpha: 240);
        r.DrawCircle((180, 200, 240), (cx + s * 5 / 100, cy), s * 7 / 100, alpha: 235);

        // Head — aerodynamic forward lean
        r.DrawCircle((190, 210, 245), (cx + s * 10 / 100, cy - s * 6 / 100), s * 6 / 100, alpha: 250);
        // Eyes — focused
        r.DrawCircle((40, 60, 120), (cx + s * 12 / 100, cy - s * 7 / 100), s * 2 / 100, alpha: 240);

        // Horn — aerodynamic
        DrawHorn(r, cx + s * 10 / 100, cy - s * 12 / 100, s * 12 / 100, (160, 200, 255), (220, 240, 255));

        // Sleek wings swept back
        for (int side = -1; side <= 1; side += 2)
        {
            int wCx3 = cx - s * 5 / 100;
            int wCy3 = cy + side * s * 5 / 100;
            // Swept wing shape
            r.DrawLine((140, 180, 240), (cx, cy), (wCx3 - s * 20 / 100, wCy3 + side * s * 12 / 100), width: 3, alpha: 200);
            r.DrawLine((140, 180, 240), (wCx3 - s * 20 / 100, wCy3 + side * s * 12 / 100), (wCx3 - s * 10 / 100, wCy3 + side * s * 3 / 100), width: 2, alpha: 160);
            // Wing surface
            for (int f = 0; f < 4; f++)
            {
                int fx = cx - s * 3 / 100 - f * s * 5 / 100;
                int fy = cy + side * (s * 3 / 100 + f * s * 3 / 100);
                r.DrawLine((160, 200, 250), (fx, fy), (fx - s * 3 / 100, fy + side * s * 2 / 100), width: 1, alpha: (byte)(140 - f * 20));
            }
        }

        // Wind trail behind
        for (int wt = 0; wt < 5; wt++)
        {
            int wx = cx - s * 15 / 100 - wt * s * 5 / 100;
            int wy = cy + (int)(Math.Sin(wt * 1.2) * s * 3 / 100);
            r.DrawCircle((200, 220, 255), (wx, wy), Math.Max(1, s * (3 - wt) / 100), alpha: (byte)(100 - wt * 15));
        }

        DrawSparkle4(r, cx + s * 18 / 100, cy - s * 14 / 100, s * 2 / 100, (200, 230, 255), 160);
    }

    // Greedy Flying Unicorn — wings, gold coins showering down, money bag
    private static void DrawUni_GreedyFlying(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Gold coins showering down
        for (int coin = 0; coin < 12; coin++)
        {
            int coinX = cx + (int)(Math.Cos(coin * 0.9 + 0.3) * s * 28 / 100);
            int coinY = cy + s * 5 / 100 + coin * s * 3 / 100;
            r.DrawCircle((255, 215, 0), (coinX, coinY), s * 3 / 100, alpha: (byte)(200 - coin * 10));
            r.DrawCircle((220, 180, 0), (coinX, coinY), s * 3 / 100, width: 1, alpha: (byte)(180 - coin * 10));
            r.DrawText("$", coinX, coinY, Math.Max(6, s * 3 / 100), (180, 140, 0), alpha: (byte)(160 - coin * 10), anchorX: "center", anchorY: "center");
        }

        // Unicorn body — clutching
        r.DrawCircle((200, 190, 160), (cx, cy - s * 5 / 100), s * 10 / 100, alpha: 235);
        // Head
        r.DrawCircle((210, 200, 170), (cx, cy - s * 16 / 100), s * 7 / 100, alpha: 250);
        // Greedy gem eyes
        r.DrawCircle((80, 200, 80), (cx - s * 3 / 100, cy - s * 17 / 100), s * 3 / 100, alpha: 230);
        r.DrawCircle((80, 200, 80), (cx + s * 3 / 100, cy - s * 17 / 100), s * 3 / 100, alpha: 230);
        // Dollar sign pupils
        r.DrawText("$", cx - s * 3 / 100, cy - s * 17 / 100, Math.Max(5, s * 2 / 100), (20, 80, 20), alpha: 240, anchorX: "center", anchorY: "center");
        r.DrawText("$", cx + s * 3 / 100, cy - s * 17 / 100, Math.Max(5, s * 2 / 100), (20, 80, 20), alpha: 240, anchorX: "center", anchorY: "center");

        // Horn
        DrawHorn(r, cx, cy - s * 23 / 100, s * 10 / 100, (200, 180, 100), (255, 240, 120));

        // Wings
        for (int side = -1; side <= 1; side += 2)
        {
            for (int f = 0; f < 5; f++)
            {
                int fx = cx + side * (s * 12 / 100 + f * s * 4 / 100);
                int fy = cy - s * 10 / 100 + f * s * 2 / 100;
                int fh = s * (14 - f * 2) / 100;
                r.DrawLine((220, 210, 160), (cx + side * s * 5 / 100, cy - s * 5 / 100), (fx, fy - fh / 2), width: 2, alpha: (byte)(200 - f * 25));
                r.DrawLine((220, 210, 160), (fx, fy - fh / 2), (fx, fy + fh / 2), width: 1, alpha: (byte)(150 - f * 20));
            }
        }

        // Money bag clutched
        int bagX = cx, bagY = cy + s * 3 / 100;
        r.DrawCircle((160, 130, 60), (bagX, bagY), s * 7 / 100, alpha: 220);
        r.DrawRect((140, 110, 50), (bagX - s * 2 / 100, bagY - s * 8 / 100, s * 4 / 100, s * 3 / 100), alpha: 210);
        r.DrawText("$", bagX, bagY, Math.Max(8, s * 6 / 100), (100, 80, 20), alpha: 230, anchorX: "center", anchorY: "center");

        // Dollar signs floating
        for (int ds = 0; ds < 4; ds++)
        {
            int dsx = cx + (int)(Math.Cos(ds * 1.5) * s * 20 / 100);
            int dsy = cy - s * 25 / 100 + ds * s * 4 / 100;
            r.DrawText("$", dsx, dsy, Math.Max(6, s * 4 / 100), (255, 215, 0), alpha: (byte)(180 - ds * 25), anchorX: "center", anchorY: "center");
        }
    }

    // Magical Flying Unicorn — wings, magic wand, sparkle trail, spell circles
    private static void DrawUni_MagicalFlying(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Spell circles / runes around
        for (int sc = 0; sc < 3; sc++)
        {
            int scx = cx + (int)(Math.Cos(sc * 2.1 + 0.5) * s * 25 / 100);
            int scy = cy + (int)(Math.Sin(sc * 2.1 + 0.5) * s * 20 / 100);
            r.DrawCircle((120, 80, 220), (scx, scy), s * 6 / 100, width: 1, alpha: 120);
            DrawRuneGlyph(r, scx, scy, s * 4 / 100, (140, 100, 240), 140);
        }

        // Unicorn body
        r.DrawCircle((200, 190, 230), (cx, cy + s * 2 / 100), s * 10 / 100, alpha: 235);
        // Head
        r.DrawCircle((210, 200, 240), (cx, cy - s * 10 / 100), s * 7 / 100, alpha: 250);
        // Magical eyes — glowing
        r.DrawCircle((140, 100, 255), (cx - s * 3 / 100, cy - s * 11 / 100), s * 2 / 100, alpha: 230);
        r.DrawCircle((140, 100, 255), (cx + s * 3 / 100, cy - s * 11 / 100), s * 2 / 100, alpha: 230);
        r.DrawCircle((200, 180, 255), (cx - s * 3 / 100, cy - s * 11 / 100), s * 1 / 100, alpha: 250);
        r.DrawCircle((200, 180, 255), (cx + s * 3 / 100, cy - s * 11 / 100), s * 1 / 100, alpha: 250);

        // Horn — magical glow
        DrawHorn(r, cx, cy - s * 17 / 100, s * 10 / 100, (140, 100, 240), (220, 200, 255));

        // Wings — ethereal magical
        for (int side = -1; side <= 1; side += 2)
        {
            for (int f = 0; f < 5; f++)
            {
                int fx = cx + side * (s * 10 / 100 + f * s * 5 / 100);
                int fy = cy - s * 4 / 100 + f * s * 2 / 100;
                int fh = s * (16 - f * 2) / 100;
                r.DrawLine((160, 140, 255), (cx + side * s * 4 / 100, cy - s * 3 / 100), (fx, fy - fh / 2), width: 2, alpha: (byte)(180 - f * 20));
                r.DrawLine((160, 140, 255), (fx, fy - fh / 2), (fx + side * s * 1 / 100, fy + fh / 2), width: 1, alpha: (byte)(140 - f * 15));
            }
        }

        // Magic wand with star tip
        int wandX = cx + s * 16 / 100, wandY = cy - s * 5 / 100;
        r.DrawLine((180, 140, 100), (wandX, wandY), (wandX + s * 8 / 100, wandY - s * 14 / 100), width: 2, alpha: 220);
        DrawStar5(r, wandX + s * 8 / 100, wandY - s * 16 / 100, s * 4 / 100, (255, 240, 100), 230);
        r.DrawCircle((255, 255, 200), (wandX + s * 8 / 100, wandY - s * 16 / 100), s * 2 / 100, alpha: 180);

        // Sparkle trail from wand
        for (int sp = 0; sp < 8; sp++)
        {
            int spx = wandX + s * 8 / 100 + (int)(Math.Cos(sp * 0.8 + 1) * s * (6 + sp) / 100);
            int spy = wandY - s * 16 / 100 + (int)(Math.Sin(sp * 1.1) * s * (4 + sp) / 100);
            DrawSparkle4(r, spx, spy, Math.Max(1, s * (3 - sp / 3) / 100), (200, 180, 255), (byte)(180 - sp * 15));
        }

        // Magical dust particles
        for (int md = 0; md < 6; md++)
        {
            int mx = cx + (int)(Math.Cos(md * 1.0) * s * 22 / 100);
            int my = cy + s * 10 / 100 + md * s * 2 / 100;
            r.DrawCircle((180, 160, 255), (mx, my), Math.Max(1, s * 1 / 100), alpha: (byte)(140 - md * 15));
        }
    }

    // Majestic Flying Unicorn — large feathered wings, crown, clouds, sunrays, rainbow trail
    private static void DrawUni_MajesticFlying(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Sunrays from behind
        for (int ray = 0; ray < 12; ray++)
        {
            double ang = ray * Math.PI / 6;
            int rx1 = cx + (int)(Math.Cos(ang) * s * 10 / 100);
            int ry1 = cy - s * 5 / 100 + (int)(Math.Sin(ang) * s * 8 / 100);
            int rx2 = cx + (int)(Math.Cos(ang) * s * 38 / 100);
            int ry2 = cy - s * 5 / 100 + (int)(Math.Sin(ang) * s * 30 / 100);
            r.DrawLine((255, 240, 180), (rx1, ry1), (rx2, ry2), width: 2, alpha: (byte)(80 - ray % 3 * 15));
        }

        // Clouds beneath
        for (int cl = 0; cl < 4; cl++)
        {
            int clx = cx - s * 20 / 100 + cl * s * 12 / 100;
            int cly = cy + s * 20 / 100 + (int)(Math.Sin(cl * 1.2) * s * 3 / 100);
            r.DrawCircle((220, 225, 240), (clx, cly), s * 7 / 100, alpha: 100);
            r.DrawCircle((230, 235, 248), (clx + s * 3 / 100, cly - s * 1 / 100), s * 5 / 100, alpha: 90);
        }

        // Rainbow trail behind
        var rainbowColors = new[] { (255, 60, 60), (255, 160, 40), (255, 240, 60), (60, 220, 80), (60, 140, 255), (160, 80, 255) };
        for (int rc = 0; rc < rainbowColors.Length; rc++)
        {
            int ry = cy + s * 8 / 100 + rc * s * 2 / 100;
            r.DrawLine(rainbowColors[rc], (x + s * 2 / 100, ry), (cx - s * 8 / 100, ry), width: 2, alpha: 120);
        }

        // Unicorn body — celestial
        r.DrawCircle((220, 215, 245), (cx, cy + s * 2 / 100), s * 11 / 100, alpha: 240);
        // Head
        r.DrawCircle((230, 225, 250), (cx, cy - s * 10 / 100), s * 7 / 100, alpha: 250);
        // Regal eyes
        r.DrawCircle((80, 60, 160), (cx - s * 3 / 100, cy - s * 11 / 100), s * 2 / 100, alpha: 240);
        r.DrawCircle((80, 60, 160), (cx + s * 3 / 100, cy - s * 11 / 100), s * 2 / 100, alpha: 240);
        r.DrawCircle((255, 255, 255), (cx - s * 3 / 100 + 1, cy - s * 12 / 100), s * 1 / 100, alpha: 220);
        r.DrawCircle((255, 255, 255), (cx + s * 3 / 100 + 1, cy - s * 12 / 100), s * 1 / 100, alpha: 220);

        // Crown atop head
        int crY = cy - s * 18 / 100;
        r.DrawRect((255, 215, 0), (cx - s * 6 / 100, crY, s * 12 / 100, s * 3 / 100), alpha: 230);
        DrawFilledTriangleUp(r, cx - s * 6 / 100, crY - s * 3 / 100, s * 4 / 100, s * 3 / 100, (255, 215, 0), 230);
        DrawFilledTriangleUp(r, cx - s * 1 / 100, crY - s * 4 / 100, s * 3 / 100, s * 4 / 100, (255, 215, 0), 230);
        DrawFilledTriangleUp(r, cx + s * 3 / 100, crY - s * 3 / 100, s * 4 / 100, s * 3 / 100, (255, 215, 0), 230);

        // Horn through crown
        DrawHorn(r, cx, crY - s * 4 / 100, s * 12 / 100, (200, 190, 240), (255, 240, 255));

        // Large feathered wings — spread wide (left)
        for (int f = 0; f < 7; f++)
        {
            int fx = cx - s * 10 / 100 - f * s * 4 / 100;
            int fy = cy - s * 6 / 100 + f * s * 2 / 100;
            int fh = s * (18 - f * 2) / 100;
            r.DrawLine((230, 230, 255), (cx - s * 5 / 100, cy - s * 2 / 100), (fx, fy - fh / 2), width: 2, alpha: (byte)(210 - f * 20));
            // Feather lines
            r.DrawLine((220, 220, 250), (fx, fy - fh / 2), (fx + s * 1 / 100, fy + fh / 2), width: 1, alpha: (byte)(170 - f * 15));
        }
        // Right wing
        for (int f = 0; f < 7; f++)
        {
            int fx = cx + s * 10 / 100 + f * s * 4 / 100;
            int fy = cy - s * 6 / 100 + f * s * 2 / 100;
            int fh = s * (18 - f * 2) / 100;
            r.DrawLine((230, 230, 255), (cx + s * 5 / 100, cy - s * 2 / 100), (fx, fy - fh / 2), width: 2, alpha: (byte)(210 - f * 20));
            r.DrawLine((220, 220, 250), (fx, fy - fh / 2), (fx - s * 1 / 100, fy + fh / 2), width: 1, alpha: (byte)(170 - f * 15));
        }

        // Celestial sparkles
        DrawSparkle4(r, cx + s * 25 / 100, cy - s * 20 / 100, s * 3 / 100, (255, 240, 200), 180);
        DrawSparkle4(r, cx - s * 28 / 100, cy - s * 15 / 100, s * 2 / 100, (255, 230, 200), 150);
        DrawStar5(r, cx, cy - s * 32 / 100, s * 3 / 100, (255, 255, 220), 160);
    }

    // ═══════════════════════════════════════════════════════════
    //  UPGRADE — growth, empowerment, ascending
    // ═══════════════════════════════════════════════════════════

    private static void DrawUpgrade(Renderer r, int v, int x, int y, int w, int h, int cx, int cy)
    {
        switch (v)
        {
            case 0: DrawUp_ShieldCrest(r, x, y, w, h, cx, cy); break;
            case 1: DrawUp_RisingArrows(r, x, y, w, h, cx, cy); break;
            case 2: DrawUp_CrystalGem(r, x, y, w, h, cx, cy); break;
            case 3: DrawUp_GoldenCrown(r, x, y, w, h, cx, cy); break;
        }
    }

    // Variant 0: Ornate shield crest
    private static void DrawUp_ShieldCrest(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Radial glow behind shield
        r.DrawCircle((60, 180, 80), (cx, cy), s * 35 / 100, alpha: 50);

        // Shield body — pointed bottom
        int shW = s * 36 / 100, shH = s * 45 / 100;
        int sx = cx - shW / 2, sy = cy - shH * 4 / 10;

        // Shield layers (3D depth)
        r.DrawRect((20, 70, 30), (sx - 2, sy - 2, shW + 4, shH * 65 / 100 + 4), alpha: 255);
        r.DrawRect((40, 130, 55), (sx, sy, shW, shH * 65 / 100), alpha: 255);
        r.DrawRect((60, 170, 80), (sx + 3, sy + 3, shW - 6, shH * 65 / 100 - 6), alpha: 255);
        // Shield point
        DrawFilledTriangleDown(r, sx, sy + shH * 65 / 100, shW, shH * 35 / 100, (40, 130, 55), 255);
        DrawFilledTriangleDown(r, sx + 3, sy + shH * 65 / 100, shW - 6, shH * 32 / 100, (60, 170, 80), 255);

        // Shield highlight streak
        r.DrawRect((120, 220, 140), (sx + shW / 4, sy + 4, shW / 10, shH * 50 / 100), alpha: 60);

        // Central emblem — upward arrow
        int arrowH = shH * 30 / 100;
        int arrowW = shW * 25 / 100;
        r.DrawRect((220, 255, 220), (cx - arrowW / 6, cy - arrowH / 4, arrowW / 3, arrowH * 6 / 10), alpha: 240);
        DrawFilledTriangleUp(r, cx - arrowW / 2, cy - arrowH / 4, arrowW, arrowH * 4 / 10, (220, 255, 220), 240);

        // Decorative scrollwork
        r.DrawCircle((80, 190, 100), (sx + shW / 4, sy + shH * 20 / 100), s * 3 / 100, width: 1, alpha: 100);
        r.DrawCircle((80, 190, 100), (sx + shW * 3 / 4, sy + shH * 20 / 100), s * 3 / 100, width: 1, alpha: 100);

        // Sparkles
        DrawSparkle4(r, cx - shW / 2 - s * 6 / 100, cy - shH / 3, s * 3 / 100, (120, 255, 160), 150);
        DrawSparkle4(r, cx + shW / 2 + s * 5 / 100, cy - shH / 4, s * 2 / 100, (180, 255, 200), 130);
    }

    // Variant 1: Rising arrows / chevrons
    private static void DrawUp_RisingArrows(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Multiple stacked chevrons rising
        for (int i = 0; i < 6; i++)
        {
            int chevY = cy + s * 25 / 100 - i * s * 10 / 100;
            int chevW = s * (40 - i * 4) / 100;
            int chevH = s * 6 / 100;
            byte a = (byte)(100 + i * 25);
            var col = i < 3 ? (40 + i * 30, 160 + i * 20, 60 + i * 15) : (120 + (i - 3) * 30, 220, 140);
            r.DrawLine(col, (cx - chevW / 2, chevY + chevH), (cx, chevY), width: 3, alpha: a);
            r.DrawLine(col, (cx, chevY), (cx + chevW / 2, chevY + chevH), width: 3, alpha: a);

            // Glow behind top chevrons
            if (i >= 4)
                r.DrawCircle(col, (cx, chevY), s * 5 / 100, alpha: 40);
        }

        // Top sparkle burst
        int topY = cy - s * 28 / 100;
        r.DrawCircle((180, 255, 200), (cx, topY), s * 8 / 100, alpha: 80);
        DrawSparkle4(r, cx, topY, s * 5 / 100, (220, 255, 220), 200);

        // Side decorative dots
        for (int side = -1; side <= 1; side += 2)
            for (int i = 0; i < 4; i++)
            {
                int dx = cx + side * s * (25 + i * 3) / 100;
                int dy = cy + s * (10 - i * 8) / 100;
                r.DrawCircle((80, 200, 100), (dx, dy), Math.Max(1, s * 2 / 100), alpha: 80 + i * 15);
            }
    }

    // Variant 2: Crystal gem — faceted emerald
    private static void DrawUp_CrystalGem(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Outer glow
        r.DrawCircle((60, 200, 100), (cx, cy), s * 30 / 100, alpha: 40);
        r.DrawCircle((80, 230, 120), (cx, cy), s * 22 / 100, alpha: 50);

        // Gem body — hexagonal via overlapping rects
        int gemW = s * 26 / 100, gemH = s * 38 / 100;
        // Main body
        r.DrawRect((30, 140, 60), (cx - gemW / 2, cy - gemH / 3, gemW, gemH * 2 / 3), alpha: 255);
        // Top facet
        DrawFilledTriangleUp(r, cx - gemW / 2, cy - gemH / 3, gemW, gemH / 3, (50, 180, 80), 255);
        // Bottom facet
        DrawFilledTriangleDown(r, cx - gemW / 2, cy + gemH / 3, gemW, gemH / 3, (25, 110, 45), 255);

        // Internal facet lines
        r.DrawLine((80, 200, 100), (cx, cy - gemH * 2 / 3), (cx - gemW / 2, cy - gemH / 3), width: 1, alpha: 100);
        r.DrawLine((80, 200, 100), (cx, cy - gemH * 2 / 3), (cx + gemW / 2, cy - gemH / 3), width: 1, alpha: 100);
        r.DrawLine((80, 200, 100), (cx, cy - gemH * 2 / 3), (cx, cy + gemH / 3), width: 1, alpha: 60);
        r.DrawLine((80, 200, 100), (cx - gemW / 2, cy - gemH / 3), (cx, cy + gemH / 3), width: 1, alpha: 60);
        r.DrawLine((80, 200, 100), (cx + gemW / 2, cy - gemH / 3), (cx, cy + gemH / 3), width: 1, alpha: 60);

        // Highlight facet
        r.DrawRect((120, 240, 160), (cx - gemW / 4, cy - gemH / 4, gemW / 3, gemH / 5), alpha: 50);

        // Sparkle on top
        r.DrawCircle((200, 255, 220), (cx - gemW / 5, cy - gemH / 3), Math.Max(2, s * 2 / 100), alpha: 180);

        // Scattered light rays
        for (int i = 0; i < 6; i++)
        {
            double ang = i * Math.PI * 2 / 6 - Math.PI / 2;
            int rd = s * 28 / 100;
            r.DrawLine((100, 220, 130), (cx + (int)(Math.Cos(ang) * s * 15 / 100), cy + (int)(Math.Sin(ang) * s * 18 / 100)),
                (cx + (int)(Math.Cos(ang) * rd), cy + (int)(Math.Sin(ang) * rd)), width: 1, alpha: 50);
        }
    }

    // Variant 3: Golden crown
    private static void DrawUp_GoldenCrown(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Radiant glow behind crown
        r.DrawCircle((200, 180, 60), (cx, cy - s * 5 / 100), s * 25 / 100, alpha: 40);

        // Crown base band
        int crW = s * 44 / 100, crH = s * 14 / 100;
        int crX = cx - crW / 2, crY = cy;
        r.DrawRect((180, 140, 30), (crX, crY, crW, crH), alpha: 255);
        r.DrawRect((220, 180, 50), (crX + 2, crY + 2, crW - 4, crH - 4), alpha: 255);
        // Gold highlight on band
        r.DrawRect((255, 230, 100), (crX + 2, crY + 2, crW - 4, 3), alpha: 120);

        // Crown points — 5 triangles upward
        int pointW = crW / 5;
        for (int i = 0; i < 5; i++)
        {
            int px = crX + i * pointW;
            int ph = s * (12 + (i == 2 ? 6 : i % 2 == 0 ? 3 : 0)) / 100;
            var pcol = i == 2 ? (255, 220, 80) : (220, 180, 50);
            DrawFilledTriangleUp(r, px, crY, pointW, ph, pcol, 255);
            // Point tip gem
            int gemR = Math.Max(1, s * 2 / 100);
            var gemCol = i == 2 ? (180, 40, 40) : i % 2 == 0 ? (40, 100, 180) : (40, 160, 60);
            r.DrawCircle(gemCol, (px + pointW / 2, crY - ph + gemR), gemR, alpha: 240);
            r.DrawCircle((255, 255, 255), (px + pointW / 2 - 1, crY - ph + gemR - 1), Math.Max(1, gemR / 3), alpha: 200);
        }

        // Center large gem
        int mainGemR = Math.Max(3, s * 4 / 100);
        r.DrawCircle((200, 40, 40), (cx, crY + crH / 2), mainGemR, alpha: 255);
        r.DrawCircle((240, 80, 80), (cx, crY + crH / 2), mainGemR * 6 / 10, alpha: 255);
        r.DrawCircle((255, 180, 180), (cx - 1, crY + crH / 2 - 1), Math.Max(1, mainGemR / 3), alpha: 200);

        // Light rays from crown
        for (int i = 0; i < 8; i++)
        {
            double ang = -Math.PI * 0.8 + i * Math.PI * 1.6 / 7;
            int rd = s * (25 + i * 2 % 8) / 100;
            r.DrawLine((255, 220, 80), (cx + (int)(Math.Cos(ang) * s * 12 / 100), crY - s * 10 / 100 + (int)(Math.Sin(ang) * s * 5 / 100)),
                (cx + (int)(Math.Cos(ang) * rd), crY - s * 10 / 100 + (int)(Math.Sin(ang) * rd * 7 / 10)), width: 1, alpha: 60);
        }

        // Sparkles
        DrawSparkle4(r, cx - crW / 2 - s * 3 / 100, crY - s * 5 / 100, s * 2 / 100, (255, 240, 160), 160);
        DrawSparkle4(r, cx + crW / 2 + s * 4 / 100, crY - s * 8 / 100, s * 3 / 100, (255, 230, 120), 140);
    }

    // ═══════════════════════════════════════════════════════════
    //  DOWNGRADE — danger, decay, restriction
    // ═══════════════════════════════════════════════════════════

    private static void DrawDowngrade(Renderer r, int v, int x, int y, int w, int h, int cx, int cy)
    {
        switch (v)
        {
            case 0: DrawDown_BrokenChain(r, x, y, w, h, cx, cy); break;
            case 1: DrawDown_CrackedShield(r, x, y, w, h, cx, cy); break;
            case 2: DrawDown_PoisonVial(r, x, y, w, h, cx, cy); break;
            case 3: DrawDown_StormCloud(r, x, y, w, h, cx, cy); break;
        }
    }

    // Variant 0: Broken chain links
    private static void DrawDown_BrokenChain(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Chain links — broken in middle
        int linkW = s * 10 / 100, linkH = s * 16 / 100;
        for (int i = 0; i < 5; i++)
        {
            int lx = cx - s * 24 / 100 + i * s * 12 / 100;
            int ly = cy - linkH / 2 + (int)(Math.Sin(i * 0.8) * s * 3 / 100);
            var col = (160 - i * 10, 140 - i * 10, 130 - i * 8);

            if (i == 2) // broken center link
            {
                // Left half
                r.DrawCircle(col, (lx - linkW / 3, ly), linkW / 2, width: 3, alpha: 240);
                // Right half — offset and rotated
                r.DrawCircle(col, (lx + linkW / 2, ly + linkH / 4), linkW / 2, width: 3, alpha: 240);
                // Debris sparks
                for (int sp = 0; sp < 4; sp++)
                {
                    int spx = lx + (sp * 7 - 10) % 15;
                    int spy = ly + (sp * 5 - 8) % 12;
                    r.DrawCircle((255, 200, 100), (spx, spy), Math.Max(1, s * 1 / 100), alpha: 180);
                }
            }
            else
            {
                // Intact link
                r.DrawCircle(col, (lx, ly), linkW / 2, width: 3, alpha: 220);
                r.DrawCircle(col, (lx, ly), linkW / 2 + 1, width: 1, alpha: 100);
                // Metallic highlight
                r.DrawCircle((200, 200, 200), (lx - linkW / 5, ly - linkH / 6), Math.Max(1, linkW / 5), alpha: 60);
            }
        }

        // Red warning X behind break
        int xSize = s * 15 / 100;
        r.DrawLine((200, 40, 40), (cx - xSize, cy - xSize), (cx + xSize, cy + xSize), width: 3, alpha: 100);
        r.DrawLine((200, 40, 40), (cx + xSize, cy - xSize), (cx - xSize, cy + xSize), width: 3, alpha: 100);

        // Danger stripes at bottom
        DrawDangerStripesUU(r, x + s * 5 / 100, y + h - s * 7 / 100, w - s * 10 / 100, s * 5 / 100, 140);
    }

    // Variant 1: Cracked shield — protection failing
    private static void DrawDown_CrackedShield(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Shield body
        int shW = s * 34 / 100, shH = s * 42 / 100;
        int sx = cx - shW / 2, sy = cy - shH * 4 / 10;
        r.DrawRect((100, 40, 40), (sx, sy, shW, shH * 65 / 100), alpha: 240);
        DrawFilledTriangleDown(r, sx, sy + shH * 65 / 100, shW, shH * 35 / 100, (100, 40, 40), 240);
        // Darker inner
        r.DrawRect((80, 30, 30), (sx + 4, sy + 4, shW - 8, shH * 60 / 100), alpha: 255);

        // Crack lines zigzagging across
        var crackCol = (180, 80, 80);
        r.DrawLine(crackCol, (cx - s * 2 / 100, sy + s * 2 / 100), (cx + s * 3 / 100, cy), width: 2, alpha: 240);
        r.DrawLine(crackCol, (cx + s * 3 / 100, cy), (cx - s * 1 / 100, cy + s * 8 / 100), width: 2, alpha: 240);
        r.DrawLine(crackCol, (cx - s * 1 / 100, cy + s * 8 / 100), (cx + s * 2 / 100, sy + shH * 60 / 100), width: 2, alpha: 240);
        // Branch cracks
        r.DrawLine(crackCol, (cx + s * 3 / 100, cy), (cx + s * 10 / 100, cy - s * 4 / 100), width: 1, alpha: 180);
        r.DrawLine(crackCol, (cx - s * 1 / 100, cy + s * 8 / 100), (cx - s * 8 / 100, cy + s * 12 / 100), width: 1, alpha: 180);

        // Red glow from cracks
        r.DrawCircle((255, 60, 40), (cx + s * 1 / 100, cy), s * 8 / 100, alpha: 30);

        // Falling fragments
        r.DrawRect((120, 50, 40), (cx + s * 14 / 100, cy + s * 10 / 100, s * 4 / 100, s * 3 / 100), alpha: 200);
        r.DrawRect((90, 35, 30), (cx - s * 16 / 100, cy + s * 15 / 100, s * 3 / 100, s * 2 / 100), alpha: 180);

        // Down arrow overlay
        int arrowY = cy - s * 3 / 100;
        r.DrawRect((240, 80, 60), (cx - s * 2 / 100, arrowY - s * 5 / 100, s * 4 / 100, s * 10 / 100), alpha: 100);
        DrawFilledTriangleDown(r, cx - s * 5 / 100, arrowY + s * 5 / 100, s * 10 / 100, s * 6 / 100, (240, 80, 60), 100);
    }

    // Variant 2: Poison vial
    private static void DrawDown_PoisonVial(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Toxic fume clouds
        for (int i = 0; i < 5; i++)
        {
            int fx = cx + (int)(Math.Sin(i * 1.3) * s * 12 / 100);
            int fy = cy - s * 18 / 100 - i * s * 4 / 100;
            int fr = s * (5 + i * 2) / 100;
            r.DrawCircle((100, 180, 40), (fx, fy), fr, alpha: 60 - i * 8);
        }

        // Vial body
        int vialW = s * 18 / 100, vialH = s * 30 / 100;
        int vx = cx - vialW / 2, vy = cy - vialH / 3;
        // Glass
        r.DrawRect((60, 80, 40), (vx, vy, vialW, vialH), alpha: 200);
        // Liquid fill
        int fillH = vialH * 60 / 100;
        r.DrawRect((80, 200, 50), (vx + 2, vy + vialH - fillH, vialW - 4, fillH - 2), alpha: 220);
        r.DrawRect((100, 230, 70), (vx + 2, vy + vialH - fillH, vialW - 4, 3), alpha: 150); // meniscus
        // Glass highlight
        r.DrawRect((180, 200, 160), (vx + vialW / 5, vy + 2, 2, vialH - 4), alpha: 60);

        // Neck
        int neckW = vialW * 45 / 100;
        r.DrawRect((60, 80, 40), (cx - neckW / 2, vy - s * 6 / 100, neckW, s * 6 / 100), alpha: 200);

        // Cork
        r.DrawRect((160, 120, 60), (cx - neckW * 6 / 10, vy - s * 9 / 100, neckW * 12 / 10, s * 4 / 100), alpha: 240);

        // Skull symbol on vial
        int skullR = Math.Max(2, s * 4 / 100);
        r.DrawCircle((200, 255, 100), (cx, vy + vialH * 40 / 100), skullR, alpha: 180);
        // Skull eyes
        r.DrawCircle((40, 60, 20), (cx - skullR / 2, vy + vialH * 38 / 100), Math.Max(1, skullR / 3), alpha: 200);
        r.DrawCircle((40, 60, 20), (cx + skullR / 2, vy + vialH * 38 / 100), Math.Max(1, skullR / 3), alpha: 200);

        // Bubbles in liquid
        for (int i = 0; i < 4; i++)
        {
            int bx = vx + 4 + ((i * 13 + 3) % (vialW - 8));
            int by = vy + vialH - fillH + 5 + ((i * 17) % (fillH - 10));
            r.DrawCircle((140, 240, 80), (bx, by), Math.Max(1, s * (1 + i % 2) / 100), width: 1, alpha: 140);
        }

        // Drip from vial
        r.DrawCircle((80, 200, 50), (cx + vialW / 3, vy + vialH + s * 2 / 100), Math.Max(1, s * 2 / 100), alpha: 180);
    }

    // Variant 3: Storm cloud with lightning
    private static void DrawDown_StormCloud(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Dark cloud body — layered circles
        r.DrawCircle((60, 50, 55), (cx - s * 12 / 100, cy - s * 10 / 100), s * 16 / 100, alpha: 250);
        r.DrawCircle((70, 58, 60), (cx + s * 4 / 100, cy - s * 14 / 100), s * 18 / 100, alpha: 250);
        r.DrawCircle((55, 45, 48), (cx + s * 16 / 100, cy - s * 8 / 100), s * 14 / 100, alpha: 250);
        r.DrawCircle((65, 55, 58), (cx, cy - s * 6 / 100), s * 20 / 100, alpha: 240);
        // Cloud bottom
        r.DrawRect((60, 50, 55), (cx - s * 24 / 100, cy - s * 6 / 100, s * 48 / 100, s * 8 / 100), alpha: 240);

        // Lightning bolts
        var boltCol = (255, 240, 100);
        // Main bolt
        DrawLightningBolt(r, cx - s * 3 / 100, cy + s * 2 / 100, cx + s * 2 / 100, cy + s * 30 / 100, s, boltCol, 240);
        // Secondary bolt
        DrawLightningBolt(r, cx + s * 10 / 100, cy + s * 2 / 100, cx + s * 15 / 100, cy + s * 22 / 100, s * 7 / 10, boltCol, 180);

        // Rain drops
        for (int i = 0; i < 10; i++)
        {
            int rx = cx - s * 22 / 100 + i * s * 5 / 100;
            int ry = cy + s * 5 / 100 + (i * 17 + 5) % (s * 20 / 100);
            r.DrawLine((100, 120, 180), (rx, ry), (rx - 1, ry + s * 4 / 100), width: 1, alpha: 120);
        }

        // Red danger glow
        r.DrawCircle((200, 40, 40), (cx, cy + s * 20 / 100), s * 12 / 100, alpha: 30);
    }

    // ═══════════════════════════════════════════════════════════
    //  MAGIC — mystical, arcane, powerful spells
    // ═══════════════════════════════════════════════════════════

    private static void DrawMagic(Renderer r, int v, int x, int y, int w, int h, int cx, int cy)
    {
        switch (v)
        {
            case 0: DrawMag_SpellCircle(r, x, y, w, h, cx, cy); break;
            case 1: DrawMag_WandSpark(r, x, y, w, h, cx, cy); break;
            case 2: DrawMag_PotionCauldron(r, x, y, w, h, cx, cy); break;
            case 3: DrawMag_RuneStone(r, x, y, w, h, cx, cy); break;
        }
    }

    // Variant 0: Arcane spell circle
    private static void DrawMag_SpellCircle(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Outer glow rings
        for (int ring = 0; ring < 4; ring++)
        {
            int rr = s * (36 - ring * 4) / 100;
            r.DrawCircle((80, 100, 255), (cx, cy), rr, width: 2, alpha: 60 + ring * 15);
        }

        // Inner circle — solid dark
        r.DrawCircle((15, 20, 45), (cx, cy), s * 22 / 100, alpha: 200);

        // Pentagram inside
        int pentR = s * 18 / 100;
        for (int i = 0; i < 5; i++)
        {
            double a1 = (i * 2 % 5) * Math.PI * 2 / 5 - Math.PI / 2;
            double a2 = ((i * 2 + 2) % 5) * Math.PI * 2 / 5 - Math.PI / 2;
            int px1 = cx + (int)(Math.Cos(a1) * pentR);
            int py1 = cy + (int)(Math.Sin(a1) * pentR);
            int px2 = cx + (int)(Math.Cos(a2) * pentR);
            int py2 = cy + (int)(Math.Sin(a2) * pentR);
            r.DrawLine((120, 140, 255), (px1, py1), (px2, py2), width: 2, alpha: 200);
        }

        // Rune symbols at perimeter
        for (int i = 0; i < 6; i++)
        {
            double ang = i * Math.PI * 2 / 6;
            int rx = cx + (int)(Math.Cos(ang) * s * 28 / 100);
            int ry = cy + (int)(Math.Sin(ang) * s * 28 / 100);
            DrawRuneGlyph(r, rx, ry, s * 3 / 100, (140, 160, 255), 180);
        }

        // Central glow
        r.DrawCircle((160, 180, 255), (cx, cy), s * 6 / 100, alpha: 100);
        r.DrawCircle((200, 220, 255), (cx, cy), s * 3 / 100, alpha: 160);

        // Floating particles
        for (int i = 0; i < 8; i++)
        {
            double ang = i * Math.PI * 2 / 8 + 0.3;
            int dist = s * (15 + i * 2 % 8) / 100;
            int px = cx + (int)(Math.Cos(ang) * dist);
            int py = cy + (int)(Math.Sin(ang) * dist);
            r.DrawCircle((140, 180, 255), (px, py), Math.Max(1, s * 1 / 100), alpha: 120 + i * 8);
        }
    }

    // Variant 1: Magic wand with sparks
    private static void DrawMag_WandSpark(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Wand body — diagonal
        int wx1 = cx + s * 15 / 100, wy1 = cy + s * 25 / 100;
        int wx2 = cx - s * 12 / 100, wy2 = cy - s * 20 / 100;
        // Wand shadow
        r.DrawLine((0, 0, 0), (wx1 + 3, wy1 + 3), (wx2 + 3, wy2 + 3), width: 5, alpha: 80);
        // Dark wood
        r.DrawLine((80, 50, 30), (wx1, wy1), (wx2, wy2), width: 5, alpha: 255);
        r.DrawLine((100, 70, 40), (wx1, wy1), (wx2, wy2), width: 3, alpha: 255);
        // Highlight stripe
        r.DrawLine((140, 100, 60), (wx1 - 1, wy1 - 1), (wx2 - 1, wy2 - 1), width: 1, alpha: 120);
        // Gold band near tip
        int bandX = (wx1 + wx2 * 2) / 3, bandY = (wy1 + wy2 * 2) / 3;
        r.DrawCircle((220, 180, 60), (bandX, bandY), Math.Max(3, s * 3 / 100), alpha: 220);

        // Tip star/glow
        r.DrawCircle((180, 200, 255), (wx2, wy2), s * 8 / 100, alpha: 80);
        r.DrawCircle((220, 230, 255), (wx2, wy2), s * 5 / 100, alpha: 120);
        DrawSparkle4(r, wx2, wy2, s * 6 / 100, (200, 220, 255), 220);

        // Sparks radiating from tip
        for (int i = 0; i < 10; i++)
        {
            double ang = i * Math.PI * 2 / 10;
            int dist = s * (8 + i * 3 % 10) / 100;
            int spx = wx2 + (int)(Math.Cos(ang) * dist);
            int spy = wy2 + (int)(Math.Sin(ang) * dist);
            DrawSparkle4(r, spx, spy, Math.Max(1, s * (2 - i / 5) / 100), (160 + i * 8, 200, 255), 140 - i * 8);
        }

        // Trailing magic dust along wand path
        for (int i = 0; i < 6; i++)
        {
            float t = (i + 1) / 7f;
            int tx = (int)(wx1 + (wx2 - wx1) * t);
            int ty = (int)(wy1 + (wy2 - wy1) * t) + (int)(Math.Sin(i * 1.5) * s * 3 / 100);
            r.DrawCircle((140, 180, 255), (tx, ty), Math.Max(1, s * (3 - i / 2) / 100), alpha: 80 + i * 10);
        }
    }

    // Variant 2: Bubbling cauldron
    private static void DrawMag_PotionCauldron(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Rising magical vapors
        for (int i = 0; i < 6; i++)
        {
            int vx = cx + (int)(Math.Sin(i * 1.1 + 0.5) * s * 10 / 100);
            int vy = cy - s * 12 / 100 - i * s * 5 / 100;
            int vr = s * (4 + i * 2) / 100;
            var vc = i % 2 == 0 ? (100, 120, 255) : (160, 100, 255);
            r.DrawCircle(vc, (vx, vy), vr, alpha: 70 - i * 8);
        }

        // Cauldron body — black iron pot
        int potW = s * 36 / 100, potH = s * 26 / 100;
        int potX = cx - potW / 2, potY = cy - potH / 4;
        // Pot shadow
        r.DrawCircle((0, 0, 0), (cx, potY + potH + s * 2 / 100), potW / 2, alpha: 60);
        // Pot body
        r.DrawRect((30, 28, 35), (potX, potY, potW, potH), alpha: 255);
        r.DrawCircle((30, 28, 35), (cx, potY + potH), potW / 2, alpha: 255);
        r.DrawCircle((35, 33, 40), (cx, potY + potH), potW * 45 / 100, alpha: 255);
        // Rim
        r.DrawRect((50, 46, 55), (potX - 3, potY - 3, potW + 6, 6), alpha: 255);
        // Highlight
        r.DrawRect((80, 75, 85), (potX + potW / 6, potY + 2, 3, potH - 4), alpha: 50);

        // Liquid surface — glowing blue/purple
        int liqY = potY + 4;
        r.DrawRect((40, 60, 180), (potX + 4, liqY, potW - 8, s * 3 / 100), alpha: 200);
        r.DrawRect((60, 80, 220), (potX + 4, liqY, potW - 8, 2), alpha: 150);

        // Bubbles
        for (int i = 0; i < 5; i++)
        {
            int bx = potX + 8 + ((i * 19 + 3) % (potW - 16));
            int by = liqY - s * (1 + i * 2) / 100;
            int br = Math.Max(1, s * (2 + i % 2) / 100);
            r.DrawCircle((100, 140, 255), (bx, by), br, width: 1, alpha: 150 - i * 15);
        }

        // Fire underneath
        for (int i = 0; i < 7; i++)
        {
            int fx = cx - s * 12 / 100 + i * s * 4 / 100;
            int fh = s * (4 + (i * 5 + 3) % 5) / 100;
            int fy = potY + potH + s * 2 / 100;
            var fc = i % 3 == 0 ? (255, 80, 20) : i % 3 == 1 ? (255, 160, 40) : (255, 220, 80);
            r.DrawRect(fc, (fx, fy - fh / 2, s * 3 / 100, fh), alpha: 200);
        }

        // Handles on sides
        r.DrawCircle((50, 48, 55), (potX - 3, potY + potH / 3), s * 4 / 100, width: 2, alpha: 200);
        r.DrawCircle((50, 48, 55), (potX + potW + 3, potY + potH / 3), s * 4 / 100, width: 2, alpha: 200);
    }

    // Variant 3: Glowing rune stone
    private static void DrawMag_RuneStone(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Stone glow
        r.DrawCircle((80, 100, 255), (cx, cy), s * 28 / 100, alpha: 40);

        // Stone body — rough rectangle
        int stW = s * 28 / 100, stH = s * 36 / 100;
        int stX = cx - stW / 2, stY = cy - stH / 2;
        r.DrawRect((60, 55, 70), (stX, stY, stW, stH), alpha: 255);
        r.DrawRect((80, 75, 90), (stX + 2, stY + 2, stW - 4, stH - 4), alpha: 255);
        // Stone texture
        for (int i = 0; i < 6; i++)
        {
            int tx = stX + 4 + ((i * 13) % (stW - 8));
            int ty = stY + 4 + ((i * 17) % (stH - 8));
            r.DrawCircle((90, 85, 100), (tx, ty), Math.Max(1, s * 1 / 100), alpha: 60);
        }

        // Carved rune — glowing
        DrawRuneGlyph(r, cx, cy, s * 10 / 100, (140, 180, 255), 240);
        // Rune glow halo
        r.DrawCircle((120, 160, 255), (cx, cy), s * 12 / 100, alpha: 40);

        // Additional carved lines
        r.DrawLine((120, 150, 220), (stX + stW / 6, stY + stH / 5), (stX + stW * 5 / 6, stY + stH / 5), width: 1, alpha: 100);
        r.DrawLine((120, 150, 220), (stX + stW / 6, stY + stH * 4 / 5), (stX + stW * 5 / 6, stY + stH * 4 / 5), width: 1, alpha: 100);

        // Floating rune particles
        for (int i = 0; i < 8; i++)
        {
            double ang = i * Math.PI * 2 / 8 + 0.2;
            int dist = s * 22 / 100 + (i % 3) * s * 3 / 100;
            int px = cx + (int)(Math.Cos(ang) * dist);
            int py = cy + (int)(Math.Sin(ang) * dist);
            r.DrawCircle((140, 180, 255), (px, py), Math.Max(1, s * 1 / 100), alpha: 100 + i * 10);
        }

        // Corner ornaments on stone
        r.DrawRect((120, 150, 200), (stX, stY, s * 3 / 100, s * 3 / 100), width: 1, alpha: 120);
        r.DrawRect((120, 150, 200), (stX + stW - s * 3 / 100, stY, s * 3 / 100, s * 3 / 100), width: 1, alpha: 120);
        r.DrawRect((120, 150, 200), (stX, stY + stH - s * 3 / 100, s * 3 / 100, s * 3 / 100), width: 1, alpha: 120);
        r.DrawRect((120, 150, 200), (stX + stW - s * 3 / 100, stY + stH - s * 3 / 100, s * 3 / 100, s * 3 / 100), width: 1, alpha: 120);
    }

    // ═══════════════════════════════════════════════════════════
    //  INSTANT — quick reaction, shield/protection
    // ═══════════════════════════════════════════════════════════

    private static void DrawInstant(Renderer r, int v, int x, int y, int w, int h, int cx, int cy)
    {
        switch (v)
        {
            case 0: DrawInst_ShieldFlash(r, x, y, w, h, cx, cy); break;
            case 1: DrawInst_HourglassFreeze(r, x, y, w, h, cx, cy); break;
            case 2: DrawInst_MagicBarrier(r, x, y, w, h, cx, cy); break;
            case 3: DrawInst_LightningShield(r, x, y, w, h, cx, cy); break;
        }
    }

    // Variant 0: Shield with flash burst
    private static void DrawInst_ShieldFlash(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Radiant burst from behind
        for (int i = 0; i < 12; i++)
        {
            double ang = i * Math.PI * 2 / 12;
            int innerR = s * 18 / 100;
            int outerR = s * (30 + i * 2 % 8) / 100;
            r.DrawLine((255, 220, 80), (cx + (int)(Math.Cos(ang) * innerR), cy + (int)(Math.Sin(ang) * innerR)),
                (cx + (int)(Math.Cos(ang) * outerR), cy + (int)(Math.Sin(ang) * outerR)), width: 2, alpha: 120 - i * 5);
        }

        // Shield — golden
        int shW = s * 30 / 100, shH = s * 38 / 100;
        int sx = cx - shW / 2, sy = cy - shH * 4 / 10;
        r.DrawRect((180, 150, 40), (sx, sy, shW, shH * 65 / 100), alpha: 255);
        DrawFilledTriangleDown(r, sx, sy + shH * 65 / 100, shW, shH * 35 / 100, (180, 150, 40), 255);
        // Inner highlight
        r.DrawRect((220, 200, 80), (sx + 3, sy + 3, shW - 6, shH * 58 / 100), alpha: 200);
        // Central star
        DrawStar5(r, cx, cy - s * 2 / 100, s * 6 / 100, (255, 240, 160), 220);

        // Glow
        r.DrawCircle((255, 220, 100), (cx, cy), s * 20 / 100, alpha: 40);
    }

    // Variant 1: Frozen hourglass — time freeze
    private static void DrawInst_HourglassFreeze(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Ice crystals around
        for (int i = 0; i < 6; i++)
        {
            double ang = i * Math.PI * 2 / 6 + 0.3;
            int dist = s * 35 / 100;
            int ix = cx + (int)(Math.Cos(ang) * dist);
            int iy = cy + (int)(Math.Sin(ang) * dist);
            DrawSparkle4(r, ix, iy, Math.Max(2, s * 3 / 100), (180, 220, 255), 140);
        }

        // Hourglass frame
        int hgW = s * 22 / 100, hgH = s * 38 / 100;
        int topY = cy - hgH / 2, botY = cy + hgH / 2;
        // Top and bottom plates
        r.DrawRect((200, 180, 120), (cx - hgW / 2 - 3, topY - 3, hgW + 6, 6), alpha: 240);
        r.DrawRect((200, 180, 120), (cx - hgW / 2 - 3, botY - 3, hgW + 6, 6), alpha: 240);

        // Glass body — top bulb
        DrawFilledTriangleDown(r, cx - hgW / 2, topY, hgW, hgH / 2, (140, 180, 220), 120);
        // Glass body — bottom bulb
        DrawFilledTriangleUp(r, cx - hgW / 2, cy, hgW, hgH / 2, (140, 180, 220), 120);

        // Sand/sparkle in top
        DrawFilledTriangleDown(r, cx - hgW / 3, topY + hgH / 8, hgW * 2 / 3, hgH / 4, (255, 220, 100), 160);
        // Sand stream
        r.DrawRect((255, 220, 100), (cx - 1, cy - hgH / 8, 2, hgH / 4), alpha: 140);
        // Sand pile in bottom
        DrawFilledTriangleUp(r, cx - hgW / 3, botY - hgH / 4, hgW * 2 / 3, hgH / 6, (255, 220, 100), 160);

        // Frozen effect — ice cracks
        r.DrawLine((180, 220, 255), (cx - hgW / 3, cy - hgH / 4), (cx, cy), width: 1, alpha: 100);
        r.DrawLine((180, 220, 255), (cx + hgW / 4, cy - hgH / 5), (cx, cy), width: 1, alpha: 100);
        r.DrawLine((180, 220, 255), (cx, cy), (cx - hgW / 5, cy + hgH / 3), width: 1, alpha: 100);

        // Blue glow
        r.DrawCircle((100, 180, 255), (cx, cy), s * 14 / 100, alpha: 40);
    }

    // Variant 2: Magic barrier dome
    private static void DrawInst_MagicBarrier(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Barrier dome — concentric arcs
        for (int ring = 0; ring < 6; ring++)
        {
            int rr = s * (18 + ring * 5) / 100;
            byte a = (byte)(140 - ring * 18);
            r.DrawCircle((240, 200, 60), (cx, cy + s * 8 / 100), rr, width: 2, alpha: a);
        }

        // Hex pattern on dome
        for (int i = 0; i < 8; i++)
        {
            double ang = i * Math.PI / 4;
            int hx = cx + (int)(Math.Cos(ang) * s * 20 / 100);
            int hy = cy + s * 8 / 100 + (int)(Math.Sin(ang) * s * 16 / 100);
            if (hy < cy + s * 8 / 100)
                DrawHexagon(r, hx, hy, s * 5 / 100, (255, 220, 80), 80);
        }

        // Small unicorn silhouette inside barrier
        r.DrawCircle((200, 190, 230), (cx, cy + s * 5 / 100), s * 8 / 100, alpha: 160);
        r.DrawCircle((210, 200, 240), (cx, cy - s * 2 / 100), s * 5 / 100, alpha: 170);
        // Horn
        DrawHorn(r, cx, cy - s * 7 / 100, s * 5 / 100, (255, 220, 100), (255, 240, 180));

        // Impact effects hitting barrier
        r.DrawLine((255, 100, 60), (x + w * 10 / 100, y + h * 15 / 100), (cx - s * 18 / 100, cy - s * 2 / 100), width: 2, alpha: 120);
        DrawSparkle4(r, cx - s * 18 / 100, cy - s * 2 / 100, s * 4 / 100, (255, 200, 80), 200);
    }

    // Variant 3: Lightning shield
    private static void DrawInst_LightningShield(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Electric field
        for (int i = 0; i < 8; i++)
        {
            double ang = i * Math.PI * 2 / 8;
            int innerR = s * 14 / 100;
            int outerR = s * 28 / 100;
            int x1 = cx + (int)(Math.Cos(ang) * innerR);
            int y1 = cy + (int)(Math.Sin(ang) * innerR);
            int x2 = cx + (int)(Math.Cos(ang + 0.15) * outerR);
            int y2 = cy + (int)(Math.Sin(ang + 0.15) * outerR);
            r.DrawLine((255, 240, 100), (x1, y1), (x2, y2), width: 2, alpha: 140 - i * 8);
            // Zig mid point
            int mx = (x1 + x2) / 2 + (i % 2 == 0 ? 1 : -1) * s * 3 / 100;
            int my = (y1 + y2) / 2;
            r.DrawLine((255, 240, 100), (x1, y1), (mx, my), width: 1, alpha: 120);
            r.DrawLine((255, 240, 100), (mx, my), (x2, y2), width: 1, alpha: 120);
        }

        // Central shield glyph
        int shR = s * 14 / 100;
        r.DrawCircle((200, 180, 60), (cx, cy), shR, alpha: 180);
        r.DrawCircle((240, 220, 80), (cx, cy), shR * 8 / 10, alpha: 200);
        // Lightning bolt inside
        int boltH = s * 12 / 100;
        r.DrawRect((255, 240, 100), (cx - s * 2 / 100, cy - boltH / 2, s * 4 / 100, boltH / 3), alpha: 240);
        r.DrawRect((255, 240, 100), (cx - s * 3 / 100, cy - boltH / 6, s * 5 / 100, boltH / 3), alpha: 240);
        r.DrawRect((255, 240, 100), (cx - s * 1 / 100, cy + boltH / 6, s * 4 / 100, boltH / 3), alpha: 240);

        // Glow
        r.DrawCircle((255, 220, 80), (cx, cy), s * 20 / 100, alpha: 35);

        // Spark particles
        for (int i = 0; i < 6; i++)
        {
            double ang = i * Math.PI * 2 / 6 + 0.4;
            int dist = s * 32 / 100;
            DrawSparkle4(r, cx + (int)(Math.Cos(ang) * dist), cy + (int)(Math.Sin(ang) * dist),
                Math.Max(2, s * 2 / 100), (255, 240, 160), 130);
        }
    }

    // ═══════════════════════════════════════════════════════════
    //  NEIGH — cancellation, stop, denial
    // ═══════════════════════════════════════════════════════════

    private static void DrawNeigh(Renderer r, int v, int x, int y, int w, int h, int cx, int cy)
    {
        switch (v)
        {
            case 0: DrawNeigh_StopSign(r, x, y, w, h, cx, cy); break;
            case 1: DrawNeigh_CrossedOut(r, x, y, w, h, cx, cy); break;
            case 2: DrawNeigh_BrickWall(r, x, y, w, h, cx, cy); break;
            case 3: DrawNeigh_HorseshoeNo(r, x, y, w, h, cx, cy); break;
        }
    }

    // Variant 0: Stop sign / prohibition
    private static void DrawNeigh_StopSign(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Octagonal stop sign
        int signR = s * 28 / 100;
        // Shadow
        DrawOctagon(r, cx + 3, cy + 3, signR, (0, 0, 0), 120);
        // Red body
        DrawOctagon(r, cx, cy, signR, (180, 40, 40), 255);
        DrawOctagon(r, cx, cy, signR * 88 / 100, (200, 50, 50), 255);

        // White border ring
        DrawOctagon(r, cx, cy, signR, (220, 220, 220), 200, outlineOnly: true);
        DrawOctagon(r, cx, cy, signR * 85 / 100, (220, 220, 220), 120, outlineOnly: true);

        // "NO" text concept — circle with slash
        int noR = signR * 50 / 100;
        r.DrawCircle((255, 255, 255), (cx, cy), noR, width: 3, alpha: 240);
        r.DrawLine((255, 255, 255), (cx - noR * 7 / 10, cy + noR * 7 / 10), (cx + noR * 7 / 10, cy - noR * 7 / 10), width: 3, alpha: 240);

        // Impact sparkles
        DrawSparkle4(r, cx + signR + s * 3 / 100, cy - signR / 2, s * 3 / 100, (255, 180, 180), 160);
        DrawSparkle4(r, cx - signR - s * 2 / 100, cy + signR / 3, s * 2 / 100, (255, 160, 160), 130);
    }

    // Variant 1: Crossed out card
    private static void DrawNeigh_CrossedOut(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Faded card shape underneath
        int cardW = s * 28 / 100, cardH = s * 40 / 100;
        r.DrawRect((50, 50, 55), (cx - cardW / 2, cy - cardH / 2, cardW, cardH), alpha: 160);
        r.DrawRect((60, 60, 65), (cx - cardW / 2, cy - cardH / 2, cardW, cardH), width: 2, alpha: 120);
        // Card content hint
        r.DrawCircle((70, 70, 75), (cx, cy - cardH / 6), s * 5 / 100, alpha: 80);
        r.DrawRect((65, 65, 70), (cx - cardW / 3, cy + cardH / 6, cardW * 2 / 3, 3), alpha: 60);

        // Big red X
        int xSize = s * 28 / 100;
        r.DrawLine((220, 50, 50), (cx - xSize, cy - xSize), (cx + xSize, cy + xSize), width: 5, alpha: 240);
        r.DrawLine((220, 50, 50), (cx + xSize, cy - xSize), (cx - xSize, cy + xSize), width: 5, alpha: 240);
        // X shadow
        r.DrawLine((0, 0, 0), (cx - xSize + 2, cy - xSize + 2), (cx + xSize + 2, cy + xSize + 2), width: 3, alpha: 60);
        r.DrawLine((0, 0, 0), (cx + xSize + 2, cy - xSize + 2), (cx - xSize + 2, cy + xSize + 2), width: 3, alpha: 60);

        // Red glow at center
        r.DrawCircle((220, 60, 40), (cx, cy), s * 12 / 100, alpha: 40);
    }

    // Variant 2: Brick wall
    private static void DrawNeigh_BrickWall(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Wall
        int wallW = s * 50 / 100, wallH = s * 40 / 100;
        int wx = cx - wallW / 2, wy = cy - wallH / 2;

        // Mortar background
        r.DrawRect((80, 70, 60), (wx, wy, wallW, wallH), alpha: 255);

        // Brick pattern
        int brickH = wallH / 6;
        int brickW = wallW / 4;
        for (int row = 0; row < 6; row++)
        {
            int offset = row % 2 == 0 ? 0 : brickW / 2;
            for (int col = -1; col < 5; col++)
            {
                int bx = wx + col * brickW + offset;
                int by = wy + row * brickH;
                if (bx >= wx && bx + brickW <= wx + wallW)
                {
                    int shade = 140 + ((row * 3 + col * 7) % 30);
                    r.DrawRect((shade, shade * 55 / 100, shade * 35 / 100), (bx + 1, by + 1, brickW - 2, brickH - 2), alpha: 255);
                }
            }
        }

        // Wall shadow
        r.DrawRect((0, 0, 0), (wx, wy + wallH, wallW, s * 3 / 100), alpha: 60);

        // Impact cracks on wall
        r.DrawLine((120, 100, 80), (cx - s * 3 / 100, cy), (cx, cy - s * 5 / 100), width: 1, alpha: 160);
        r.DrawLine((120, 100, 80), (cx, cy - s * 5 / 100), (cx + s * 4 / 100, cy - s * 2 / 100), width: 1, alpha: 160);
        r.DrawLine((120, 100, 80), (cx, cy - s * 5 / 100), (cx - s * 2 / 100, cy - s * 8 / 100), width: 1, alpha: 140);

        // "DENIED" stamp feel — X on wall
        r.DrawLine((255, 80, 60), (cx - s * 10 / 100, cy - s * 8 / 100), (cx + s * 10 / 100, cy + s * 8 / 100), width: 3, alpha: 150);
        r.DrawLine((255, 80, 60), (cx + s * 10 / 100, cy - s * 8 / 100), (cx - s * 10 / 100, cy + s * 8 / 100), width: 3, alpha: 150);
    }

    // Variant 3: Horseshoe with no symbol
    private static void DrawNeigh_HorseshoeNo(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Horseshoe
        int hR = s * 22 / 100;
        // Arc (draw upper half circle)
        r.DrawCircle((160, 150, 140), (cx, cy - s * 2 / 100), hR, width: 5, alpha: 240);
        // Block bottom half to make horseshoe shape
        r.DrawRect((0, 0, 0), (cx - hR - 5, cy + s * 2 / 100, hR * 2 + 10, hR), alpha: 0); // conceptual
        // Legs
        r.DrawRect((160, 150, 140), (cx - hR, cy - s * 2 / 100, 5, hR * 7 / 10), alpha: 240);
        r.DrawRect((160, 150, 140), (cx + hR - 5, cy - s * 2 / 100, 5, hR * 7 / 10), alpha: 240);
        // Metallic highlight
        r.DrawCircle((200, 195, 185), (cx - hR / 3, cy - s * 6 / 100), hR / 4, alpha: 60);

        // Nail holes
        r.DrawCircle((100, 95, 90), (cx - hR * 6 / 10, cy - s * 4 / 100), Math.Max(1, s * 2 / 100), alpha: 180);
        r.DrawCircle((100, 95, 90), (cx + hR * 6 / 10, cy - s * 4 / 100), Math.Max(1, s * 2 / 100), alpha: 180);
        r.DrawCircle((100, 95, 90), (cx, cy - s * 2 / 100 - hR * 8 / 10), Math.Max(1, s * 2 / 100), alpha: 180);

        // Red prohibition circle overlaid
        int noR = s * 30 / 100;
        r.DrawCircle((200, 50, 50), (cx, cy), noR, width: 3, alpha: 180);
        r.DrawLine((200, 50, 50), (cx - noR * 7 / 10, cy + noR * 7 / 10), (cx + noR * 7 / 10, cy - noR * 7 / 10), width: 3, alpha: 180);
    }

    // ═══════════════════════════════════════════════════════════
    //  SUPER NEIGH — ultimate denial, electric power
    // ═══════════════════════════════════════════════════════════

    private static void DrawSuperNeigh(Renderer r, int v, int x, int y, int w, int h, int cx, int cy)
    {
        switch (v)
        {
            case 0: DrawSNeigh_ThunderStop(r, x, y, w, h, cx, cy); break;
            case 1: DrawSNeigh_VoidSeal(r, x, y, w, h, cx, cy); break;
            case 2: DrawSNeigh_ShatterBurst(r, x, y, w, h, cx, cy); break;
            case 3: DrawSNeigh_EyeOfDenial(r, x, y, w, h, cx, cy); break;
        }
    }

    // Variant 0: Thunder stop — electrified prohibition
    private static void DrawSNeigh_ThunderStop(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Electric field background
        for (int i = 0; i < 12; i++)
        {
            double ang = i * Math.PI * 2 / 12;
            int dist = s * 38 / 100;
            int ex = cx + (int)(Math.Cos(ang) * dist);
            int ey = cy + (int)(Math.Sin(ang) * dist);
            r.DrawLine((180, 80, 255), (cx, cy), (ex, ey), width: 1, alpha: 50);
        }

        // Central stop circle — purple electric
        int stopR = s * 24 / 100;
        for (int ring = 0; ring < 3; ring++)
        {
            r.DrawCircle((160, 60, 220), (cx, cy), stopR + ring * 3, width: 3, alpha: 200 - ring * 40);
        }
        r.DrawCircle((120, 40, 180), (cx, cy), stopR * 85 / 100, alpha: 240);

        // Lightning bolt slash through circle
        DrawLightningBolt(r, cx - stopR * 7 / 10, cy - stopR * 7 / 10, cx + stopR * 7 / 10, cy + stopR * 7 / 10, s, (255, 200, 255), 240);

        // Inner glow
        r.DrawCircle((200, 120, 255), (cx, cy), stopR / 2, alpha: 60);

        // Sparks at cardinal points
        for (int i = 0; i < 4; i++)
        {
            double ang = i * Math.PI / 2;
            int sx = cx + (int)(Math.Cos(ang) * stopR);
            int sy = cy + (int)(Math.Sin(ang) * stopR);
            DrawSparkle4(r, sx, sy, s * 3 / 100, (220, 160, 255), 180);
        }
    }

    // Variant 1: Void seal — dark energy sealing
    private static void DrawSNeigh_VoidSeal(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Dark vortex swirl
        for (int ring = 0; ring < 8; ring++)
        {
            double angOff = ring * 0.3;
            int rr = s * (5 + ring * 4) / 100;
            for (int seg = 0; seg < 12; seg++)
            {
                double a = seg * Math.PI * 2 / 12 + angOff;
                int px = cx + (int)(Math.Cos(a) * rr);
                int py = cy + (int)(Math.Sin(a) * rr);
                r.DrawCircle((100 + ring * 10, 40 + ring * 5, 180 + ring * 8), (px, py), Math.Max(1, s * 2 / 100), alpha: 80 - ring * 6);
            }
        }

        // Central seal — dark orb
        r.DrawCircle((20, 10, 40), (cx, cy), s * 14 / 100, alpha: 250);
        r.DrawCircle((40, 20, 60), (cx, cy), s * 12 / 100, alpha: 255);
        // Seal rune
        DrawRuneGlyph(r, cx, cy, s * 6 / 100, (200, 140, 255), 220);

        // Chains of denial — crossing the seal
        for (int i = 0; i < 4; i++)
        {
            double ang = i * Math.PI / 4 + Math.PI / 8;
            int lx1 = cx + (int)(Math.Cos(ang) * s * 28 / 100);
            int ly1 = cy + (int)(Math.Sin(ang) * s * 28 / 100);
            int lx2 = cx - (int)(Math.Cos(ang) * s * 28 / 100);
            int ly2 = cy - (int)(Math.Sin(ang) * s * 28 / 100);
            r.DrawLine((140, 80, 220), (lx1, ly1), (lx2, ly2), width: 2, alpha: 120);
        }

        // Purple energy pulse
        r.DrawCircle((180, 100, 255), (cx, cy), s * 18 / 100, width: 2, alpha: 100);
        r.DrawCircle((160, 80, 240), (cx, cy), s * 24 / 100, width: 1, alpha: 60);
    }

    // Variant 2: Shatter burst — destruction of incoming spell
    private static void DrawSNeigh_ShatterBurst(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Shattered glass shards radiating outward
        for (int i = 0; i < 16; i++)
        {
            double ang = i * Math.PI * 2 / 16;
            int innerR = s * 6 / 100;
            int outerR = s * (18 + i * 2 % 10) / 100;
            int ix = cx + (int)(Math.Cos(ang) * innerR);
            int iy = cy + (int)(Math.Sin(ang) * innerR);
            int ox = cx + (int)(Math.Cos(ang) * outerR);
            int oy = cy + (int)(Math.Sin(ang) * outerR);
            // Shard - line with width variation
            var shardCol = i % 3 == 0 ? (200, 160, 255) : i % 3 == 1 ? (160, 120, 220) : (255, 200, 255);
            r.DrawLine(shardCol, (ix, iy), (ox, oy), width: i % 2 == 0 ? 3 : 2, alpha: 180 - i * 4);
        }

        // Central impact flash
        r.DrawCircle((255, 230, 255), (cx, cy), s * 8 / 100, alpha: 200);
        r.DrawCircle((220, 180, 255), (cx, cy), s * 12 / 100, alpha: 100);
        r.DrawCircle((180, 140, 240), (cx, cy), s * 16 / 100, alpha: 50);

        // Debris particles
        for (int i = 0; i < 10; i++)
        {
            double ang = i * 0.63;
            int dist = s * (20 + i * 3) / 100;
            int dx = cx + (int)(Math.Cos(ang) * dist);
            int dy = cy + (int)(Math.Sin(ang) * dist * 0.8);
            int ds = Math.Max(1, s * (2 + i % 2) / 100);
            r.DrawRect((180, 140, 220), (dx, dy, ds, ds), alpha: 140 - i * 8);
        }

        // Text impact — "!" shape
        r.DrawRect((255, 200, 255), (cx - 2, cy - s * 12 / 100, 4, s * 15 / 100), alpha: 200);
        r.DrawCircle((255, 200, 255), (cx, cy + s * 6 / 100), Math.Max(2, s * 2 / 100), alpha: 200);
    }

    // Variant 3: Eye of denial — all-seeing rejection eye
    private static void DrawSNeigh_EyeOfDenial(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Radiating dark energy lines
        for (int i = 0; i < 10; i++)
        {
            double ang = i * Math.PI * 2 / 10;
            int rLen = s * 36 / 100;
            r.DrawLine((120, 60, 180), (cx + (int)(Math.Cos(ang) * s * 15 / 100), cy + (int)(Math.Sin(ang) * s * 10 / 100)),
                (cx + (int)(Math.Cos(ang) * rLen), cy + (int)(Math.Sin(ang) * rLen * 6 / 10)), width: 1, alpha: 60);
        }

        // Eye shape — almond/lenticular via overlapping circles
        int eyeW = s * 30 / 100, eyeH = s * 16 / 100;
        // Upper lid arc
        for (int i = -eyeW; i <= eyeW; i += 2)
        {
            float t = (float)i / eyeW;
            int ly = cy - (int)(eyeH * (1f - t * t));
            r.DrawRect((160, 100, 220), (cx + i, ly, 2, 2), alpha: 220);
        }
        // Lower lid arc
        for (int i = -eyeW; i <= eyeW; i += 2)
        {
            float t = (float)i / eyeW;
            int ly = cy + (int)(eyeH * (1f - t * t));
            r.DrawRect((160, 100, 220), (cx + i, ly, 2, 2), alpha: 220);
        }

        // Iris
        int irisR = s * 10 / 100;
        r.DrawCircle((180, 80, 255), (cx, cy), irisR, alpha: 240);
        r.DrawCircle((200, 120, 255), (cx, cy), irisR * 7 / 10, alpha: 255);
        // Pupil
        r.DrawCircle((20, 10, 40), (cx, cy), irisR * 4 / 10, alpha: 255);
        // Specular
        r.DrawCircle((255, 255, 255), (cx - irisR / 4, cy - irisR / 4), Math.Max(1, irisR / 4), alpha: 200);

        // Red slash — NO
        r.DrawLine((220, 40, 40), (cx - s * 20 / 100, cy + s * 12 / 100), (cx + s * 20 / 100, cy - s * 12 / 100), width: 3, alpha: 200);

        // Mystic symbols around eye
        for (int i = 0; i < 4; i++)
        {
            double ang = Math.PI / 4 + i * Math.PI / 2;
            int rx = cx + (int)(Math.Cos(ang) * s * 28 / 100);
            int ry = cy + (int)(Math.Sin(ang) * s * 22 / 100);
            DrawRuneGlyph(r, rx, ry, s * 3 / 100, (140, 80, 200), 120);
        }
    }

    // ═══════════════════════════════════════════════════════════
    //  GENERIC fallback
    // ═══════════════════════════════════════════════════════════

    private static void DrawGenericUU(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);
        // Magic sparkle ring
        for (int i = 0; i < 8; i++)
        {
            double ang = i * Math.PI * 2 / 8;
            int dist = s * 25 / 100;
            DrawSparkle4(r, cx + (int)(Math.Cos(ang) * dist), cy + (int)(Math.Sin(ang) * dist),
                s * 3 / 100, (200, 180, 255), 150);
        }
        // Central unicorn silhouette
        r.DrawCircle((180, 160, 220), (cx, cy + s * 4 / 100), s * 12 / 100, alpha: 180);
        r.DrawCircle((190, 170, 230), (cx, cy - s * 6 / 100), s * 8 / 100, alpha: 190);
        DrawHorn(r, cx, cy - s * 14 / 100, s * 10 / 100, (200, 180, 255), (240, 220, 255));
    }

    // ═══════════════════════════════════════════════════════════
    //  HELPERS
    // ═══════════════════════════════════════════════════════════

    /// <summary>Draw a spiraling unicorn horn.</summary>
    private static void DrawHorn(Renderer r, int cx, int topY, int height,
        (int R, int G, int B) baseCol, (int R, int G, int B) tipCol)
    {
        for (int i = height; i >= 0; i -= 2)
        {
            float t = 1f - (float)i / height; // 0 at base, 1 at tip
            int w = Math.Max(1, (int)(height * 0.2f * (1f - t)));
            int hy = topY + i;
            int r2 = (int)(baseCol.R + (tipCol.R - baseCol.R) * t);
            int g = (int)(baseCol.G + (tipCol.G - baseCol.G) * t);
            int b = (int)(baseCol.B + (tipCol.B - baseCol.B) * t);
            r.DrawRect((r2, g, b), (cx - w / 2, hy, w, 2), alpha: (int)(200 + 55 * t));

            // Spiral groove
            if (i % 6 < 2)
            {
                r.DrawRect((Math.Max(0, r2 - 30), Math.Max(0, g - 30), Math.Max(0, b - 20)),
                    (cx - w / 2, hy, w, 1), alpha: 80);
            }
        }

        // Tip sparkle
        r.DrawCircle(tipCol, (cx, topY), Math.Max(1, height / 8), alpha: 200);
    }

    /// <summary>Draw a unicorn ear (pointed upward triangle with inner pink).</summary>
    private static void DrawEar(Renderer r, int x, int y, int size,
        (int R, int G, int B) outerCol, (int R, int G, int B) innerCol)
    {
        // Outer ear
        for (int row = 0; row < size; row++)
        {
            int rowW = Math.Max(1, (size - row) * 2 * size / (size * 2));
            int rx = x + size / 2 - rowW / 2;
            r.DrawRect(outerCol, (rx, y + size - row, rowW, 1), alpha: 240);
        }
        // Inner ear (smaller)
        int inSize = size * 6 / 10;
        int inX = x + (size - inSize) / 2;
        int inY = y + size / 3;
        for (int row = 0; row < inSize; row++)
        {
            int rowW = Math.Max(1, (inSize - row) * 2 * inSize / (inSize * 2));
            int rx = inX + inSize / 2 - rowW / 2;
            r.DrawRect(innerCol, (rx, inY + inSize - row, rowW, 1), alpha: 160);
        }
    }

    /// <summary>Draw a 4-pointed sparkle star.</summary>
    private static void DrawSparkle4(Renderer r, int cx, int cy, int size,
        (int R, int G, int B) col, int alpha)
    {
        r.DrawLine(col, (cx - size, cy), (cx + size, cy), width: 1, alpha: alpha);
        r.DrawLine(col, (cx, cy - size), (cx, cy + size), width: 1, alpha: alpha);
        int ds = size * 6 / 10;
        r.DrawLine(col, (cx - ds, cy - ds), (cx + ds, cy + ds), width: 1, alpha: alpha * 6 / 10);
        r.DrawLine(col, (cx + ds, cy - ds), (cx - ds, cy + ds), width: 1, alpha: alpha * 6 / 10);
        r.DrawCircle(col, (cx, cy), Math.Max(1, size / 3), alpha: alpha);
    }

    /// <summary>Draw a simple 5-pointed star shape.</summary>
    private static void DrawStar5(Renderer r, int cx, int cy, int outerR,
        (int R, int G, int B) col, int alpha)
    {
        for (int i = 0; i < 5; i++)
        {
            double a1 = i * Math.PI * 2 / 5 - Math.PI / 2;
            double a2 = (i + 2) * Math.PI * 2 / 5 - Math.PI / 2;
            int x1 = cx + (int)(Math.Cos(a1) * outerR);
            int y1 = cy + (int)(Math.Sin(a1) * outerR);
            int x2 = cx + (int)(Math.Cos(a2) * outerR);
            int y2 = cy + (int)(Math.Sin(a2) * outerR);
            r.DrawLine(col, (x1, y1), (x2, y2), width: 2, alpha: alpha);
        }
        r.DrawCircle(col, (cx, cy), Math.Max(1, outerR / 3), alpha: alpha * 7 / 10);
    }

    /// <summary>Draw a simple butterfly shape.</summary>
    private static void DrawButterfly(Renderer r, int cx, int cy, int size,
        (int R, int G, int B) col, int alpha)
    {
        // Wings
        r.DrawCircle(col, (cx - size, cy - size / 2), size, alpha: alpha);
        r.DrawCircle(col, (cx + size, cy - size / 2), size, alpha: alpha);
        r.DrawCircle(col, (cx - size * 7 / 10, cy + size / 2), size * 7 / 10, alpha: alpha * 8 / 10);
        r.DrawCircle(col, (cx + size * 7 / 10, cy + size / 2), size * 7 / 10, alpha: alpha * 8 / 10);
        // Body
        r.DrawRect((60, 40, 40), (cx - 1, cy - size, 2, size * 2), alpha: alpha);
        // Antennae
        r.DrawLine((60, 40, 40), (cx, cy - size), (cx - size / 2, cy - size * 3 / 2), width: 1, alpha: alpha * 7 / 10);
        r.DrawLine((60, 40, 40), (cx, cy - size), (cx + size / 2, cy - size * 3 / 2), width: 1, alpha: alpha * 7 / 10);
    }

    /// <summary>Draw a filled triangle pointing up.</summary>
    private static void DrawFilledTriangleUp(Renderer r, int x, int y, int w, int h,
        (int R, int G, int B) col, int alpha)
    {
        for (int row = 0; row < h; row++)
        {
            float t = (float)row / Math.Max(1, h);
            int rw = (int)(w * t);
            int rx = x + (w - rw) / 2;
            r.DrawRect(col, (rx, y + h - row, Math.Max(1, rw), 1), alpha: alpha);
        }
    }

    /// <summary>Draw a filled triangle pointing down.</summary>
    private static void DrawFilledTriangleDown(Renderer r, int x, int y, int w, int h,
        (int R, int G, int B) col, int alpha)
    {
        for (int row = 0; row < h; row++)
        {
            float t = (float)row / Math.Max(1, h);
            int rw = (int)(w * (1f - t));
            int rx = x + (w - rw) / 2;
            r.DrawRect(col, (rx, y + row, Math.Max(1, rw), 1), alpha: alpha);
        }
    }

    /// <summary>Draw an octagon shape (filled or outline).</summary>
    private static void DrawOctagon(Renderer r, int cx, int cy, int radius,
        (int R, int G, int B) col, int alpha, bool outlineOnly = false)
    {
        // Approximate octagon with rect + trimmed corners
        int s = (int)(radius * 0.924f); // side length projection
        int c = (int)(radius * 0.383f); // corner cut

        if (!outlineOnly)
        {
            r.DrawRect(col, (cx - s, cy - c, s * 2, c * 2 + 1), alpha: alpha);
            r.DrawRect(col, (cx - c, cy - s, c * 2, s * 2 + 1), alpha: alpha);
            // Fill in the 4 diagonal bands
            for (int row = 0; row < s - c; row++)
            {
                int w = c + row;
                r.DrawRect(col, (cx - w, cy - s + row, w * 2, 1), alpha: alpha);
                r.DrawRect(col, (cx - w, cy + s - row, w * 2, 1), alpha: alpha);
            }
        }
        else
        {
            // Draw outline only via 8 lines
            for (int i = 0; i < 8; i++)
            {
                double a1 = i * Math.PI * 2 / 8 - Math.PI / 8;
                double a2 = (i + 1) * Math.PI * 2 / 8 - Math.PI / 8;
                int x1 = cx + (int)(Math.Cos(a1) * radius);
                int y1 = cy + (int)(Math.Sin(a1) * radius);
                int x2 = cx + (int)(Math.Cos(a2) * radius);
                int y2 = cy + (int)(Math.Sin(a2) * radius);
                r.DrawLine(col, (x1, y1), (x2, y2), width: 2, alpha: alpha);
            }
        }
    }

    /// <summary>Draw simple hexagon outline.</summary>
    private static void DrawHexagon(Renderer r, int cx, int cy, int radius,
        (int R, int G, int B) col, int alpha)
    {
        for (int i = 0; i < 6; i++)
        {
            double a1 = i * Math.PI * 2 / 6;
            double a2 = (i + 1) * Math.PI * 2 / 6;
            int x1 = cx + (int)(Math.Cos(a1) * radius);
            int y1 = cy + (int)(Math.Sin(a1) * radius);
            int x2 = cx + (int)(Math.Cos(a2) * radius);
            int y2 = cy + (int)(Math.Sin(a2) * radius);
            r.DrawLine(col, (x1, y1), (x2, y2), width: 1, alpha: alpha);
        }
    }

    /// <summary>Draw a small mystical rune glyph (abstract symbol).</summary>
    private static void DrawRuneGlyph(Renderer r, int cx, int cy, int size,
        (int R, int G, int B) col, int alpha)
    {
        // Simple cross-like rune with decorative strokes
        r.DrawLine(col, (cx, cy - size), (cx, cy + size), width: 1, alpha: alpha);
        r.DrawLine(col, (cx - size * 6 / 10, cy - size / 2), (cx + size * 6 / 10, cy - size / 2), width: 1, alpha: alpha);
        r.DrawLine(col, (cx - size * 4 / 10, cy + size / 3), (cx + size * 4 / 10, cy + size / 3), width: 1, alpha: alpha * 7 / 10);
        // Diagonal accents
        r.DrawLine(col, (cx - size / 3, cy - size), (cx + size / 3, cy - size * 7 / 10), width: 1, alpha: alpha * 5 / 10);
        // Dot at center
        r.DrawCircle(col, (cx, cy), Math.Max(1, size / 4), alpha: alpha);
    }

    /// <summary>Draw a zigzag lightning bolt between two points.</summary>
    private static void DrawLightningBolt(Renderer r, int x1, int y1, int x2, int y2, int s,
        (int R, int G, int B) col, int alpha)
    {
        // 3-segment zigzag
        int mx1 = (x1 * 2 + x2) / 3 + s * 4 / 100;
        int my1 = (y1 * 2 + y2) / 3;
        int mx2 = (x1 + x2 * 2) / 3 - s * 3 / 100;
        int my2 = (y1 + y2 * 2) / 3;

        // Glow behind
        r.DrawLine(col, (x1, y1), (mx1, my1), width: 5, alpha: alpha / 3);
        r.DrawLine(col, (mx1, my1), (mx2, my2), width: 5, alpha: alpha / 3);
        r.DrawLine(col, (mx2, my2), (x2, y2), width: 5, alpha: alpha / 3);

        // Main bolt
        r.DrawLine(col, (x1, y1), (mx1, my1), width: 3, alpha: alpha);
        r.DrawLine(col, (mx1, my1), (mx2, my2), width: 3, alpha: alpha);
        r.DrawLine(col, (mx2, my2), (x2, y2), width: 3, alpha: alpha);

        // Bright core
        r.DrawLine((255, 255, 255), (x1, y1), (mx1, my1), width: 1, alpha: alpha * 6 / 10);
        r.DrawLine((255, 255, 255), (mx1, my1), (mx2, my2), width: 1, alpha: alpha * 6 / 10);
        r.DrawLine((255, 255, 255), (mx2, my2), (x2, y2), width: 1, alpha: alpha * 6 / 10);
    }

    /// <summary>Draw danger stripes (diagonal red/dark) in a rectangular region.</summary>
    private static void DrawDangerStripesUU(Renderer r, int x, int y, int w, int h, int alpha, int spacing = 10)
    {
        for (int i = -h; i < w + h; i += spacing)
        {
            bool isRed = ((i / spacing) % 2) == 0;
            var col = isRed ? (200, 60, 60) : (40, 20, 20);
            int x1 = x + i, y1 = y;
            int x2 = x + i + h, y2 = y + h;
            r.DrawLine(col, (Math.Max(x, Math.Min(x + w, x1)), y1),
                       (Math.Max(x, Math.Min(x + w, x2)), y2), width: spacing / 2, alpha: alpha);
        }
    }
}
