using System;
using Microsoft.Xna.Framework;
using Microsoft.Xna.Framework.Graphics;
using SkiaSharp;

namespace ARPi2.Sharp.Core;

// ════════════════════════════════════════════════════════════════
//  EKCardArt — Procedural card illustrations for Exploding Kittens
//
//  Each card type has 4 distinct illustration variants drawn
//  entirely from layered 2D primitives (rects, circles, lines).
//  The visual density is ~40-80 draw calls per card for
//  production-quality procedural art.
// ════════════════════════════════════════════════════════════════

public static class EKCardArt
{
    /// <summary>Draw a rich illustration for the given card kind.</summary>
    /// <param name="variant">0-3 for the visual variant.</param>
    /// <param name="area">The inner drawable area for the illustration.</param>
    public static void DrawIllustration(Renderer r, string kind, int variant,
        (int x, int y, int w, int h) area)
    {
        int x = area.x, y = area.y, w = area.w, h = area.h;
        int cx = x + w / 2, cy = y + h / 2;
        int v = ((variant % 4) + 4) % 4;

        // ── SkiaSharp-rendered atmospheric background (anti-aliased, cached) ──
        DrawSkiaBackground(r, kind, v, x, y, w, h);

        switch (kind.ToUpperInvariant())
        {
            case "EK":   DrawEK(r, v, x, y, w, h, cx, cy); break;
            case "ATK":  DrawATK(r, v, x, y, w, h, cx, cy); break;
            case "DEF":  DrawDEF(r, v, x, y, w, h, cx, cy); break;
            case "SKIP": DrawSKIP(r, v, x, y, w, h, cx, cy); break;
            case "SHUF": DrawSHUF(r, v, x, y, w, h, cx, cy); break;
            case "FUT":  DrawFUT(r, v, x, y, w, h, cx, cy); break;
            case "FAV":  DrawFAV(r, v, x, y, w, h, cx, cy); break;
            case "NOPE": DrawNOPE(r, v, x, y, w, h, cx, cy); break;
            default:     DrawGeneric(r, x, y, w, h, cx, cy); break;
        }
    }

    // ════════════════════════════════════════════════════════════════
    //  SkiaSharp Rendered Backgrounds — smooth anti-aliased vector art
    // ════════════════════════════════════════════════════════════════

    private static void DrawSkiaBackground(Renderer r, string kind, int variant, int x, int y, int w, int h)
    {
        string key = $"ekart_{kind}_{variant}_{w}_{h}";
        var tex = r.GetOrCreateSkiaTexture(key, w, h, (canvas, cw, ch) =>
        {
            RenderSkiaIllustrationBg(canvas, kind, variant, cw, ch);
        });
        r.DrawTexture(tex, new Rectangle(x, y, w, h));
    }

    /// <summary>Render the full illustration background via SkiaSharp at native resolution.</summary>
    private static void RenderSkiaIllustrationBg(SKCanvas c, string kind, int variant, int w, int h)
    {
        float cx = w / 2f, cy = h / 2f;
        float s = MathF.Min(w, h);
        string k = kind.ToUpperInvariant();

        // Kind-specific color palette
        var (bgDark, bgMid, bgLight, glow, accent) = k switch
        {
            "EK"   => (new SKColor(40,  5,   0),   new SKColor(80,  20,  5),   new SKColor(140, 40,  10),  new SKColor(255, 80,  0),   new SKColor(255, 200, 50)),
            "ATK"  => (new SKColor(35,  5,   5),   new SKColor(70,  15,  10),  new SKColor(130, 30,  15),  new SKColor(255, 60,  30),  new SKColor(255, 180, 80)),
            "DEF"  => (new SKColor(4,   22,  12),  new SKColor(10,  45,  25),  new SKColor(20,  80,  45),  new SKColor(80,  255, 140), new SKColor(180, 255, 220)),
            "SKIP" => (new SKColor(28,  24,  4),   new SKColor(50,  44,  10),  new SKColor(90,  76,  20),  new SKColor(255, 220, 50),  new SKColor(255, 245, 160)),
            "SHUF" => (new SKColor(4,   12,  30),  new SKColor(10,  24,  55),  new SKColor(20,  48,  100), new SKColor(80,  160, 255), new SKColor(180, 220, 255)),
            "FUT"  => (new SKColor(18,  5,   32),  new SKColor(35,  12,  60),  new SKColor(65,  25,  110), new SKColor(160, 80,  255), new SKColor(220, 180, 255)),
            "FAV"  => (new SKColor(28,  8,   18),  new SKColor(50,  16,  35),  new SKColor(90,  30,  60),  new SKColor(255, 130, 200), new SKColor(255, 200, 230)),
            "NOPE" => (new SKColor(18,  8,   8),   new SKColor(35,  16,  16),  new SKColor(65,  28,  28),  new SKColor(200, 50,  50),  new SKColor(255, 140, 140)),
            _      => (new SKColor(10,  14,  22),  new SKColor(20,  28,  42),  new SKColor(40,  55,  80),  new SKColor(100, 160, 240), new SKColor(180, 210, 255)),
        };

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

        // 2. Central subject glow — soft radial
        using (var paint = new SKPaint { IsAntialias = true })
        {
            var glowFaded = glow.WithAlpha(40);
            paint.Shader = SKShader.CreateRadialGradient(
                new SKPoint(cx, cy * 0.9f), s * 0.4f,
                new[] { glowFaded, glow.WithAlpha(16), SKColors.Transparent },
                new float[] { 0f, 0.5f, 1f },
                SKShaderTileMode.Clamp);
            c.DrawRect(0, 0, w, h, paint);
        }

        // 3. Atmospheric energy lines — smooth anti-aliased curves
        using (var paint = new SKPaint { IsAntialias = true, Style = SKPaintStyle.Stroke, StrokeWidth = 1f })
        {
            int lineCount = Math.Max(5, w / 14);
            for (int i = 0; i < lineCount; i++)
            {
                float t = (float)i / lineCount;
                byte a = (byte)(6 + (i % 4) * 2);
                paint.Color = glow.WithAlpha(a);

                float x1 = w * t;
                float y1 = 0;
                float x2 = w;
                float y2 = h * (1f - t);

                using var path = new SKPath();
                path.MoveTo(x1, y1);
                // Smooth bezier curve — atmospheric swoosh
                float ctrlX = cx + (i % 2 == 0 ? 1 : -1) * s * 0.15f;
                float ctrlY = cy + (i % 3 - 1) * s * 0.1f;
                path.QuadTo(ctrlX, ctrlY, x2, y2);
                c.DrawPath(path, paint);
            }
        }

        // 4. Nebula clouds — scattered soft circles
        using (var paint = new SKPaint { IsAntialias = true, MaskFilter = SKMaskFilter.CreateBlur(SKBlurStyle.Normal, s * 0.02f) })
        {
            int cloudCount = 4 + variant;
            for (int i = 0; i < cloudCount; i++)
            {
                // Deterministic pseudo-random positions from variant + index
                float fx = cx + MathF.Cos(i * 2.1f + variant * 0.7f) * s * 0.32f;
                float fy = cy + MathF.Sin(i * 1.7f + variant * 1.3f) * s * 0.28f;
                float fr = s * (0.08f + (i % 3) * 0.04f);

                paint.Shader = SKShader.CreateRadialGradient(
                    new SKPoint(fx, fy), fr,
                    new[] { accent.WithAlpha(14), glow.WithAlpha(6), SKColors.Transparent },
                    new float[] { 0f, 0.6f, 1f },
                    SKShaderTileMode.Clamp);
                c.DrawCircle(fx, fy, fr, paint);
                paint.Shader = null;
            }
        }

        // 5. Spotlight cone from top — dramatic stage lighting
        using (var paint = new SKPaint { IsAntialias = true })
        {
            using var path = new SKPath();
            float spotCx = cx + (variant % 2 == 0 ? -1 : 1) * w * 0.1f;
            path.MoveTo(spotCx - w * 0.04f, 0);
            path.LineTo(spotCx - w * 0.25f, h);
            path.LineTo(spotCx + w * 0.25f, h);
            path.LineTo(spotCx + w * 0.04f, 0);
            path.Close();

            paint.Shader = SKShader.CreateLinearGradient(
                new SKPoint(spotCx, 0), new SKPoint(spotCx, h),
                new[] { accent.WithAlpha(12), glow.WithAlpha(5), SKColors.Transparent },
                new float[] { 0f, 0.6f, 1f },
                SKShaderTileMode.Clamp);
            c.DrawPath(path, paint);
        }

        // 6. Edge vignette — smooth darkening at borders
        using (var paint = new SKPaint { IsAntialias = true })
        {
            // Top edge
            paint.Shader = SKShader.CreateLinearGradient(
                new SKPoint(0, 0), new SKPoint(0, h * 0.25f),
                new[] { new SKColor(0, 0, 0, 40), SKColors.Transparent },
                SKShaderTileMode.Clamp);
            c.DrawRect(0, 0, w, h * 0.25f, paint);

            // Bottom edge
            paint.Shader = SKShader.CreateLinearGradient(
                new SKPoint(0, h * 0.75f), new SKPoint(0, h),
                new[] { SKColors.Transparent, new SKColor(0, 0, 0, 55) },
                SKShaderTileMode.Clamp);
            c.DrawRect(0, h * 0.75f, w, h * 0.25f, paint);

            // Left edge
            paint.Shader = SKShader.CreateLinearGradient(
                new SKPoint(0, 0), new SKPoint(w * 0.2f, 0),
                new[] { new SKColor(0, 0, 0, 30), SKColors.Transparent },
                SKShaderTileMode.Clamp);
            c.DrawRect(0, 0, w * 0.2f, h, paint);

            // Right edge
            paint.Shader = SKShader.CreateLinearGradient(
                new SKPoint(w * 0.8f, 0), new SKPoint(w, 0),
                new[] { SKColors.Transparent, new SKColor(0, 0, 0, 30) },
                SKShaderTileMode.Clamp);
            c.DrawRect(w * 0.8f, 0, w * 0.2f, h, paint);
        }

        // 7. Subtle noise grain — film texture
        using (var paint = new SKPaint { IsAntialias = false })
        {
            for (int tx = 0; tx < w; tx += 5)
            {
                for (int ty = 0; ty < h; ty += 5)
                {
                    int seed = ((tx * 31 + ty * 97 + variant * 13) & 0x3FF);
                    if (seed < 15)
                    {
                        paint.Color = new SKColor(255, 255, 255, (byte)(3 + (seed & 3)));
                        c.DrawPoint(tx, ty, paint);
                    }
                    else if (seed > 1010)
                    {
                        paint.Color = new SKColor(0, 0, 0, (byte)(4 + (seed & 3)));
                        c.DrawPoint(tx, ty, paint);
                    }
                }
            }
        }

        // 8. Particle dust motes — floating ambient specs
        using (var paint = new SKPaint { IsAntialias = true })
        {
            int moteCount = 8 + variant * 2;
            for (int i = 0; i < moteCount; i++)
            {
                float mx = (((i * 127 + variant * 31) % w) + w) % w;
                float my = (((i * 89 + variant * 43) % h) + h) % h;
                float mr = 0.5f + (i % 3) * 0.5f;
                byte ma = (byte)(8 + (i % 5) * 3);
                paint.Color = accent.WithAlpha(ma);
                c.DrawCircle(mx, my, mr, paint);
            }
        }
    }

    // ─── EXPLODING KITTEN ──────────────────────────────────────
    private static void DrawEK(Renderer r, int v, int x, int y, int w, int h, int cx, int cy)
    {
        switch (v)
        {
            case 0: DrawEK_MushroomCloud(r, x, y, w, h, cx, cy); break;
            case 1: DrawEK_BombFuse(r, x, y, w, h, cx, cy); break;
            case 2: DrawEK_NukeSymbol(r, x, y, w, h, cx, cy); break;
            case 3: DrawEK_CatExplosion(r, x, y, w, h, cx, cy); break;
        }
    }

    // Variant 0: Mushroom cloud with cat silhouette — enhanced with atmospheric layers
    private static void DrawEK_MushroomCloud(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Ground blast zone — wide radial flash
        r.DrawCircle((160, 40, 0), (cx, cy + s * 42 / 100), s * 50 / 100, alpha: 18);
        r.DrawCircle((200, 60, 0), (cx, cy + s * 38 / 100), s * 40 / 100, alpha: 25);
        r.DrawCircle((255, 120, 0), (cx, cy + s * 35 / 100), s * 28 / 100, alpha: 22);

        // Ground fire line
        for (int i = 0; i < 10; i++)
        {
            int fx = cx - s * 40 / 100 + i * s * 8 / 100;
            int fh = s * (4 + (i * 7 + 3) % 6) / 100;
            int fy = cy + s * 38 / 100 - fh;
            var fireCol = i % 3 == 0 ? (255, 80, 0) : i % 3 == 1 ? (255, 160, 0) : (255, 200, 40);
            r.DrawRect(fireCol, (fx, fy, s * 4 / 100, fh), alpha: 30 + (i % 4) * 5);
        }

        // Mushroom stem — gradient bands from bottom to cap
        int stemW = s * 18 / 100, stemH = s * 38 / 100;
        int stemX = cx - stemW / 2, stemY = cy - stemH / 6;
        for (int b = 0; b < 10; b++)
        {
            int bh = stemH / 10;
            int by = stemY + b * bh;
            float bt = (float)b / 10;
            int bw = stemW + (int)(stemW * 0.3f * MathF.Sin(bt * MathF.PI)); // slight bulge
            int bx = cx - bw / 2;
            int rr = (int)(180 + 60 * (1f - bt));
            int gg = (int)(80 + 40 * (1f - bt));
            int bb = (int)(20 + 20 * bt);
            r.DrawRect((rr, gg, bb), (bx, by, bw, bh + 1), alpha: 50 - b * 3);
        }

        // Mushroom cap — richly layered with depth
        int capR = s * 34 / 100;
        int capY = cy - s * 20 / 100;
        r.DrawCircle((120, 20, 0), (cx, capY + s * 2 / 100), capR + 4, alpha: 20); // shadow
        r.DrawCircle((160, 40, 0), (cx, capY), capR, alpha: 45);
        r.DrawCircle((200, 60, 0), (cx, capY - s * 2 / 100), capR * 85 / 100, alpha: 45);
        r.DrawCircle((230, 90, 10), (cx, capY - s * 4 / 100), capR * 68 / 100, alpha: 40);
        r.DrawCircle((245, 130, 20), (cx, capY - s * 5 / 100), capR * 50 / 100, alpha: 38);
        r.DrawCircle((255, 180, 50), (cx, capY - s * 7 / 100), capR * 32 / 100, alpha: 35);
        r.DrawCircle((255, 220, 100), (cx, capY - s * 8 / 100), capR * 18 / 100, alpha: 28);
        // Cap highlight
        r.DrawCircle((255, 240, 180), (cx - capR / 4, capY - capR / 3), capR / 5, alpha: 15);

        // Cat ears silhouette in smoke
        int earS = s * 10 / 100;
        DrawTriangle(r, cx - earS * 2, capY - earS - s * 2 / 100, earS, (0, 0, 0), 55);
        DrawTriangle(r, cx + earS, capY - earS - s * 2 / 100, earS, (0, 0, 0), 55);
        // Inner ears
        DrawTriangle(r, cx - earS * 2 + earS / 4, capY - earS * 3 / 4 - s * 2 / 100, earS * 60 / 100, (200, 60, 0), 25);
        DrawTriangle(r, cx + earS + earS / 4, capY - earS * 3 / 4 - s * 2 / 100, earS * 60 / 100, (200, 60, 0), 25);

        // Cat eyes in smoke — glowing
        int eyeR = Math.Max(3, s * 4 / 100);
        r.DrawCircle((255, 220, 0), (cx - s * 7 / 100, capY), eyeR + 2, alpha: 20);
        r.DrawCircle((255, 200, 0), (cx - s * 7 / 100, capY), eyeR, alpha: 65);
        r.DrawCircle((255, 220, 0), (cx + s * 7 / 100, capY), eyeR + 2, alpha: 20);
        r.DrawCircle((255, 200, 0), (cx + s * 7 / 100, capY), eyeR, alpha: 65);
        // Slit pupils
        r.DrawRect((0, 0, 0), (cx - s * 7 / 100 - 1, capY - eyeR + 1, 2, eyeR * 2 - 2), alpha: 55);
        r.DrawRect((0, 0, 0), (cx + s * 7 / 100 - 1, capY - eyeR + 1, 2, eyeR * 2 - 2), alpha: 55);
        // Eye specular
        r.DrawCircle((255, 255, 200), (cx - s * 8 / 100, capY - 1), 1, alpha: 50);
        r.DrawCircle((255, 255, 200), (cx + s * 6 / 100, capY - 1), 1, alpha: 50);

        // Shockwave rings
        r.DrawCircle((255, 80, 0), (cx, cy + s * 32 / 100), s * 44 / 100, width: 2, alpha: 22);
        r.DrawCircle((255, 140, 20), (cx, cy + s * 24 / 100), s * 50 / 100, width: 1, alpha: 16);
        r.DrawCircle((255, 200, 50), (cx, cy + s * 28 / 100), s * 55 / 100, width: 1, alpha: 10);

        // Debris chunks
        for (int i = 0; i < 7; i++)
        {
            double ang = 0.3 + i * 0.8;
            int dist = s * (20 + i * 5) / 100;
            int dx = cx + (int)(Math.Cos(ang) * dist);
            int dy = cy + (int)(Math.Sin(ang) * dist * 0.6);
            int ds = Math.Max(2, s * (2 + i % 3) / 100);
            r.DrawRect((120, 80, 30), (dx, dy, ds, ds), alpha: 30 + (i % 3) * 8);
        }
    }

    // Variant 1: Bomb with lit fuse — detailed cartoon style
    private static void DrawEK_BombFuse(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);
        int bombR = s * 28 / 100;
        int bombCy = cy + s * 5 / 100;

        // Heat distortion waves behind bomb
        for (int wave = 0; wave < 4; wave++)
        {
            int wr = bombR + s * (8 + wave * 6) / 100;
            r.DrawCircle((255, 80 + wave * 30, 0), (cx, bombCy), wr, width: 1, alpha: 10 - wave * 2);
        }

        // Bomb shadow — elongated
        r.DrawCircle((0, 0, 0), (cx + 4, bombCy + 5), bombR + 2, alpha: 35);
        r.DrawCircle((20, 5, 0), (cx + 3, bombCy + 4), bombR, alpha: 25);

        // Bomb body — rich metallic gradient
        for (int i = bombR; i >= 0; i -= 2)
        {
            float t = (float)i / bombR;
            int g = (int)(15 + 30 * t);
            int b = (int)(18 + 8 * t);
            r.DrawCircle((g + 5, g, b), (cx, bombCy), i, alpha: 200);
        }

        // Specular highlights — multiple for metallic sheen
        r.DrawCircle((80, 80, 90), (cx - bombR / 3, bombCy - bombR / 3), bombR / 3, alpha: 30);
        r.DrawCircle((120, 120, 135), (cx - bombR / 3, bombCy - bombR / 3), bombR / 5, alpha: 35);
        r.DrawCircle((180, 180, 200), (cx - bombR * 2 / 5, bombCy - bombR * 2 / 5), bombR / 8, alpha: 25);
        // Lower rim light
        r.DrawCircle((60, 50, 45), (cx + bombR / 4, bombCy + bombR / 3), bombR / 4, alpha: 18);

        // Rivets/bolts around equator
        for (int i = 0; i < 8; i++)
        {
            double ang = i * Math.PI / 4;
            int rx = cx + (int)(Math.Cos(ang) * bombR * 85 / 100);
            int ry = bombCy + (int)(Math.Sin(ang) * bombR * 85 / 100);
            r.DrawCircle((80, 80, 85), (rx, ry), Math.Max(1, s * 2 / 100), alpha: 60);
            r.DrawCircle((60, 55, 50), (rx + 1, ry + 1), Math.Max(1, s * 1 / 100), alpha: 30);
        }

        // Skull & crossbones marking on bomb
        int skullCy = bombCy - s * 1 / 100;
        // Skull circle
        r.DrawCircle((200, 180, 60), (cx, skullCy), Math.Max(4, s * 8 / 100), alpha: 35);
        // Skull eyes
        r.DrawCircle((0, 0, 0), (cx - s * 3 / 100, skullCy - s * 2 / 100), Math.Max(1, s * 2 / 100), alpha: 50);
        r.DrawCircle((0, 0, 0), (cx + s * 3 / 100, skullCy - s * 2 / 100), Math.Max(1, s * 2 / 100), alpha: 50);
        // Skull nose
        DrawTriangle(r, cx - s * 1 / 100, skullCy + s * 1 / 100, Math.Max(2, s * 2 / 100), (0, 0, 0), 40);
        // Crossbones below
        r.DrawLine((200, 180, 60), (cx - s * 8 / 100, bombCy + s * 8 / 100), (cx + s * 8 / 100, bombCy + s * 14 / 100), width: 2, alpha: 30);
        r.DrawLine((200, 180, 60), (cx + s * 8 / 100, bombCy + s * 8 / 100), (cx - s * 8 / 100, bombCy + s * 14 / 100), width: 2, alpha: 30);

        // Cat whiskers on skull
        r.DrawLine((200, 180, 60), (cx - s * 4 / 100, skullCy + s * 3 / 100), (cx - s * 10 / 100, skullCy + s * 1 / 100), width: 1, alpha: 28);
        r.DrawLine((200, 180, 60), (cx - s * 4 / 100, skullCy + s * 4 / 100), (cx - s * 10 / 100, skullCy + s * 4 / 100), width: 1, alpha: 28);
        r.DrawLine((200, 180, 60), (cx + s * 4 / 100, skullCy + s * 3 / 100), (cx + s * 10 / 100, skullCy + s * 1 / 100), width: 1, alpha: 28);
        r.DrawLine((200, 180, 60), (cx + s * 4 / 100, skullCy + s * 4 / 100), (cx + s * 10 / 100, skullCy + s * 4 / 100), width: 1, alpha: 28);

        // Fuse nozzle — metallic cylinder
        int nzW = s * 10 / 100, nzH = s * 7 / 100;
        r.DrawRect((100, 85, 50), (cx - nzW / 2, bombCy - bombR - nzH + 3, nzW, nzH), alpha: 80);
        r.DrawRect((140, 125, 80), (cx - nzW / 2 + 1, bombCy - bombR - nzH + 4, nzW - 2, 2), alpha: 40);
        r.DrawRect((80, 70, 45), (cx - nzW / 2 + 1, bombCy - bombR - 1, nzW - 2, 2), alpha: 40);

        // Fuse — thick braided rope with color gradient
        int fuseY = bombCy - bombR - nzH / 2 + 2;
        // Fuse path: nozzle → curve → tip
        (int, int)[] fusePts = [
            (cx, fuseY), (cx + s * 4 / 100, fuseY - s * 5 / 100),
            (cx + s * 8 / 100, fuseY - s * 9 / 100), (cx + s * 13 / 100, fuseY - s * 13 / 100)
        ];
        // Outer glow
        for (int i = 0; i < fusePts.Length - 1; i++)
            r.DrawLine((200, 120, 40), fusePts[i], fusePts[i + 1], width: 4, alpha: 25);
        // Main fuse
        for (int i = 0; i < fusePts.Length - 1; i++)
            r.DrawLine((160, 130, 70), fusePts[i], fusePts[i + 1], width: 3, alpha: 70);
        // Braid detail
        for (int i = 0; i < fusePts.Length - 1; i++)
            r.DrawLine((200, 170, 100), fusePts[i], fusePts[i + 1], width: 1, alpha: 35);

        // Fire along fuse — orange/yellow flames
        for (int i = 1; i < fusePts.Length; i++)
        {
            int flameH = s * (3 + i) / 100;
            var flCol = i % 2 == 0 ? (255, 180, 0) : (255, 100, 0);
            r.DrawCircle(flCol, (fusePts[i].Item1, fusePts[i].Item2 - flameH / 2), Math.Max(2, flameH), alpha: 25 + i * 5);
        }

        // Spark shower at fuse tip
        int sparkX = fusePts[^1].Item1, sparkY = fusePts[^1].Item2;
        r.DrawCircle((255, 255, 240), (sparkX, sparkY), Math.Max(3, s * 5 / 100), alpha: 55);
        r.DrawCircle((255, 240, 100), (sparkX, sparkY), Math.Max(4, s * 8 / 100), alpha: 30);
        r.DrawCircle((255, 160, 0), (sparkX, sparkY), Math.Max(5, s * 12 / 100), alpha: 16);
        // Spark rays — rainbow-tinted
        for (int i = 0; i < 10; i++)
        {
            double ang = i * Math.PI / 5 + 0.3;
            int len = s * (6 + (i % 3) * 3) / 100;
            int rx = sparkX + (int)(Math.Cos(ang) * len);
            int ry = sparkY + (int)(Math.Sin(ang) * len);
            var rayCol = i % 3 == 0 ? (255, 255, 180) : i % 3 == 1 ? (255, 200, 60) : (255, 140, 20);
            r.DrawLine(rayCol, (sparkX, sparkY), (rx, ry), width: 1, alpha: 35 + (i % 2) * 10);
        }
        // Spark particles flying off
        for (int i = 0; i < 6; i++)
        {
            double ang = i * 1.1 + 0.8;
            int dist = s * (10 + i * 3) / 100;
            int px = sparkX + (int)(Math.Cos(ang) * dist);
            int py = sparkY + (int)(Math.Sin(ang) * dist * 0.6) - s * 4 / 100;
            r.DrawCircle((255, 220, 80), (px, py), Math.Max(1, 2 - i / 3), alpha: 40 - i * 5);
        }

        // Ground cracks beneath bomb
        for (int i = 0; i < 5; i++)
        {
            double ang = Math.PI * 0.3 + i * Math.PI * 0.1;
            int crLen = s * (8 + i * 3) / 100;
            int crX = cx + (int)(Math.Cos(ang) * crLen);
            int crY = bombCy + bombR + (int)(Math.Sin(ang) * crLen / 3);
            r.DrawLine((60, 30, 10), (cx + (int)(Math.Cos(ang) * bombR * 80 / 100), bombCy + bombR - 2), (crX, crY), width: 1, alpha: 30);
        }
    }

    // Variant 2: Nuclear hazard symbol with cat ears — vivid warning style
    private static void DrawEK_NukeSymbol(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);
        int symR = s * 30 / 100;

        // Pulsing radiation rings — fading outward
        for (int ring = 0; ring < 5; ring++)
        {
            int rr = symR + s * (6 + ring * 5) / 100;
            var ringCol = ring % 2 == 0 ? (255, 220, 0) : (255, 140, 0);
            r.DrawCircle(ringCol, (cx, cy), rr, width: 1, alpha: 14 - ring * 2);
        }

        // Warning stripes ring — diagonal yellow/black
        int stripeR = symR + s * 4 / 100;
        for (int i = 0; i < 24; i++)
        {
            double ang = i * Math.PI / 12;
            int sx1 = cx + (int)(Math.Cos(ang) * symR);
            int sy1 = cy + (int)(Math.Sin(ang) * symR);
            int sx2 = cx + (int)(Math.Cos(ang) * stripeR);
            int sy2 = cy + (int)(Math.Sin(ang) * stripeR);
            var col = i % 2 == 0 ? (240, 200, 0) : (40, 30, 0);
            r.DrawLine(col, (sx1, sy1), (sx2, sy2), width: 3, alpha: 50);
        }

        // Hazard circle background — gradient fill
        r.DrawCircle((60, 50, 0), (cx, cy), symR, alpha: 80);
        for (int i = symR; i >= symR * 60 / 100; i -= 3)
        {
            float t = (float)(i - symR * 60 / 100) / (symR * 40 / 100);
            int yy = (int)(50 + 20 * t);
            r.DrawCircle((yy, yy - 10, 0), (cx, cy), i, alpha: 25);
        }

        // Trefoil sectors — gradient-filled wedges
        for (int i = 0; i < 3; i++)
        {
            double startAng = i * 2 * Math.PI / 3 - Math.PI / 2;
            double span = Math.PI / 2.5;
            for (double a = startAng - span / 2; a < startAng + span / 2; a += 0.04)
            {
                float at = (float)((a - startAng + span / 2) / span);
                int innerR = symR * 25 / 100;
                int outerR = symR * 85 / 100;
                int x1 = cx + (int)(Math.Cos(a) * innerR);
                int y1 = cy + (int)(Math.Sin(a) * innerR);
                int x2 = cx + (int)(Math.Cos(a) * outerR);
                int y2 = cy + (int)(Math.Sin(a) * outerR);
                int rr = (int)(200 + 55 * at);
                int gg = (int)(160 + 40 * at);
                r.DrawLine((rr, gg, 0), (x1, y1), (x2, y2), width: 2, alpha: 70);
            }
            // Sector outline
            double endAngL = startAng - span / 2, endAngR = startAng + span / 2;
            r.DrawLine((100, 80, 0), (cx + (int)(Math.Cos(endAngL) * symR * 25 / 100), cy + (int)(Math.Sin(endAngL) * symR * 25 / 100)),
                (cx + (int)(Math.Cos(endAngL) * symR * 85 / 100), cy + (int)(Math.Sin(endAngL) * symR * 85 / 100)), width: 1, alpha: 40);
            r.DrawLine((100, 80, 0), (cx + (int)(Math.Cos(endAngR) * symR * 25 / 100), cy + (int)(Math.Sin(endAngR) * symR * 25 / 100)),
                (cx + (int)(Math.Cos(endAngR) * symR * 85 / 100), cy + (int)(Math.Sin(endAngR) * symR * 85 / 100)), width: 1, alpha: 40);
        }

        // Center circle — layered with glow
        r.DrawCircle((30, 25, 0), (cx, cy), symR * 22 / 100, alpha: 80);
        r.DrawCircle((60, 50, 0), (cx, cy), symR * 18 / 100, alpha: 60);
        // Cat face in center
        r.DrawCircle((220, 200, 0), (cx - symR * 6 / 100, cy - symR * 4 / 100), Math.Max(1, symR * 5 / 100), alpha: 50);
        r.DrawCircle((220, 200, 0), (cx + symR * 6 / 100, cy - symR * 4 / 100), Math.Max(1, symR * 5 / 100), alpha: 50);
        r.DrawCircle((0, 0, 0), (cx - symR * 6 / 100, cy - symR * 4 / 100), Math.Max(1, symR * 2 / 100), alpha: 55);
        r.DrawCircle((0, 0, 0), (cx + symR * 6 / 100, cy - symR * 4 / 100), Math.Max(1, symR * 2 / 100), alpha: 55);
        // Cat nose + mouth
        DrawTriangle(r, cx - symR * 2 / 100, cy + symR * 2 / 100, Math.Max(2, symR * 4 / 100), (200, 100, 80), 40);
        r.DrawLine((200, 180, 0), (cx, cy + symR * 6 / 100), (cx - symR * 4 / 100, cy + symR * 10 / 100), width: 1, alpha: 30);
        r.DrawLine((200, 180, 0), (cx, cy + symR * 6 / 100), (cx + symR * 4 / 100, cy + symR * 10 / 100), width: 1, alpha: 30);

        // Cat ears on top — larger with inner detail
        int earH = s * 16 / 100;
        DrawTriangle(r, cx - symR * 60 / 100, cy - symR - earH / 3, earH, (240, 200, 0), 55);
        DrawTriangle(r, cx + symR * 20 / 100, cy - symR - earH / 3, earH, (240, 200, 0), 55);
        DrawTriangle(r, cx - symR * 54 / 100, cy - symR - earH / 5, earH * 55 / 100, (200, 100, 60), 38);
        DrawTriangle(r, cx + symR * 26 / 100, cy - symR - earH / 5, earH * 55 / 100, (200, 100, 60), 38);

        // Outer bold border
        r.DrawCircle((0, 0, 0), (cx, cy), symR + 1, width: 3, alpha: 60);

        // Corner hazard markers
        int hazFs = Math.Max(6, s * 7 / 100);
        r.DrawText("⚠", cx, cy + symR + s * 10 / 100, hazFs, (255, 200, 0), anchorX: "center", anchorY: "center", alpha: 40);
    }

    // Variant 3: Cat face splitting apart with explosion — dynamic & colorful
    private static void DrawEK_CatExplosion(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Shockwave rings emanating from center
        for (int ring = 0; ring < 4; ring++)
        {
            int rr = s * (35 + ring * 7) / 100;
            var col = ring % 2 == 0 ? (255, 100, 0) : (255, 180, 40);
            r.DrawCircle(col, (cx, cy), rr, width: 2, alpha: 12 - ring * 2);
        }

        // Explosion core — layered fiery gradient
        r.DrawCircle((255, 255, 220), (cx, cy), s * 6 / 100, alpha: 55);
        r.DrawCircle((255, 240, 100), (cx, cy), s * 10 / 100, alpha: 45);
        r.DrawCircle((255, 180, 40), (cx, cy), s * 16 / 100, alpha: 35);
        r.DrawCircle((255, 100, 0), (cx, cy), s * 22 / 100, alpha: 25);
        r.DrawCircle((200, 50, 0), (cx, cy), s * 28 / 100, alpha: 16);

        // Explosion rays from center — alternating colors
        for (int i = 0; i < 16; i++)
        {
            double ang = i * Math.PI / 8;
            int len = s * (22 + (i % 3) * 8) / 100;
            int ex = cx + (int)(Math.Cos(ang) * len);
            int ey = cy + (int)(Math.Sin(ang) * len);
            var rayCol = i % 4 == 0 ? (255, 255, 180) : i % 4 == 1 ? (255, 200, 50)
                       : i % 4 == 2 ? (255, 140, 0) : (255, 80, 0);
            int rw = i % 2 == 0 ? 3 : 2;
            r.DrawLine(rayCol, (cx, cy), (ex, ey), width: rw, alpha: 30 + (i % 3) * 5);
        }

        int shift = s * 12 / 100;

        // ── Left half of cat face ──
        // Face outline
        r.DrawCircle((200, 140, 80), (cx - shift, cy), s * 20 / 100, alpha: 35);
        r.DrawCircle((180, 120, 60), (cx - shift, cy), s * 18 / 100, alpha: 25);
        // Fur texture lines
        for (int i = 0; i < 4; i++)
        {
            double fa = -Math.PI * 0.6 + i * 0.35;
            int fx = cx - shift + (int)(Math.Cos(fa) * s * 16 / 100);
            int fy = cy + (int)(Math.Sin(fa) * s * 16 / 100);
            r.DrawLine((160, 100, 40), (cx - shift, cy), (fx, fy), width: 1, alpha: 18);
        }
        // Eye — large with detail
        int leyX = cx - shift - s * 6 / 100, leyY = cy - s * 4 / 100;
        r.DrawCircle((255, 255, 200), (leyX, leyY), Math.Max(3, s * 5 / 100), alpha: 55); // white
        r.DrawCircle((160, 200, 0), (leyX, leyY), Math.Max(2, s * 4 / 100), alpha: 50); // iris
        r.DrawCircle((0, 0, 0), (leyX, leyY), Math.Max(1, s * 2 / 100), alpha: 65); // pupil
        r.DrawCircle((255, 255, 255), (leyX - 1, leyY - 1), 1, alpha: 50); // highlight
        // Ear
        DrawTriangle(r, cx - shift - s * 16 / 100, cy - s * 28 / 100, s * 14 / 100, (200, 140, 80), 50);
        DrawTriangle(r, cx - shift - s * 14 / 100, cy - s * 24 / 100, s * 9 / 100, (220, 120, 100), 35);
        // Whiskers
        r.DrawLine((180, 160, 120), (cx - shift - s * 10 / 100, cy + s * 2 / 100),
            (cx - shift - s * 32 / 100, cy - s * 4 / 100), width: 1, alpha: 40);
        r.DrawLine((180, 160, 120), (cx - shift - s * 10 / 100, cy + s * 4 / 100),
            (cx - shift - s * 32 / 100, cy + s * 4 / 100), width: 1, alpha: 35);
        r.DrawLine((180, 160, 120), (cx - shift - s * 8 / 100, cy + s * 6 / 100),
            (cx - shift - s * 30 / 100, cy + s * 12 / 100), width: 1, alpha: 30);
        // Half nose
        DrawTriangle(r, cx - shift + s * 2 / 100, cy + s * 2 / 100, Math.Max(2, s * 4 / 100), (200, 100, 80), 40);

        // ── Right half of cat face ──
        r.DrawCircle((200, 140, 80), (cx + shift, cy), s * 20 / 100, alpha: 35);
        r.DrawCircle((180, 120, 60), (cx + shift, cy), s * 18 / 100, alpha: 25);
        // Fur texture
        for (int i = 0; i < 4; i++)
        {
            double fa = -Math.PI * 0.4 + i * 0.35;
            int fx = cx + shift + (int)(Math.Cos(fa) * s * 16 / 100);
            int fy = cy + (int)(Math.Sin(fa) * s * 16 / 100);
            r.DrawLine((160, 100, 40), (cx + shift, cy), (fx, fy), width: 1, alpha: 18);
        }
        // Eye
        int reyX = cx + shift + s * 6 / 100, reyY = cy - s * 4 / 100;
        r.DrawCircle((255, 255, 200), (reyX, reyY), Math.Max(3, s * 5 / 100), alpha: 55);
        r.DrawCircle((160, 200, 0), (reyX, reyY), Math.Max(2, s * 4 / 100), alpha: 50);
        r.DrawCircle((0, 0, 0), (reyX, reyY), Math.Max(1, s * 2 / 100), alpha: 65);
        r.DrawCircle((255, 255, 255), (reyX - 1, reyY - 1), 1, alpha: 50);
        // Ear
        DrawTriangle(r, cx + shift + s * 6 / 100, cy - s * 28 / 100, s * 14 / 100, (200, 140, 80), 50);
        DrawTriangle(r, cx + shift + s * 8 / 100, cy - s * 24 / 100, s * 9 / 100, (220, 120, 100), 35);
        // Whiskers
        r.DrawLine((180, 160, 120), (cx + shift + s * 10 / 100, cy + s * 2 / 100),
            (cx + shift + s * 32 / 100, cy - s * 4 / 100), width: 1, alpha: 40);
        r.DrawLine((180, 160, 120), (cx + shift + s * 10 / 100, cy + s * 4 / 100),
            (cx + shift + s * 32 / 100, cy + s * 4 / 100), width: 1, alpha: 35);
        r.DrawLine((180, 160, 120), (cx + shift + s * 8 / 100, cy + s * 6 / 100),
            (cx + shift + s * 30 / 100, cy + s * 12 / 100), width: 1, alpha: 30);
        // Half nose
        DrawTriangle(r, cx + shift - s * 5 / 100, cy + s * 2 / 100, Math.Max(2, s * 4 / 100), (200, 100, 80), 40);

        // Debris flying outward — fur tufts
        for (int i = 0; i < 10; i++)
        {
            double ang = 0.2 + i * 0.65;
            int dist = s * (22 + (i * 7) % 16) / 100;
            int dx = cx + (int)(Math.Cos(ang) * dist);
            int dy = cy + (int)(Math.Sin(ang) * dist * 0.7);
            int ds = Math.Max(2, s * (2 + i % 3) / 100);
            var debCol = i % 3 == 0 ? (200, 140, 80) : i % 3 == 1 ? (180, 120, 60) : (160, 100, 40);
            r.DrawRect(debCol, (dx, dy, ds, ds), alpha: 30 + (i % 3) * 5);
        }

        // Jagged split line down the center
        for (int seg = 0; seg < 8; seg++)
        {
            int sy1 = cy - s * 30 / 100 + seg * s * 8 / 100;
            int sy2 = sy1 + s * 8 / 100;
            int jag = (seg % 2 == 0 ? 1 : -1) * s * 3 / 100;
            r.DrawLine((255, 240, 160), (cx + jag, sy1), (cx - jag, sy2), width: 2, alpha: 35);
        }
    }

    // ─── ATTACK ────────────────────────────────────────────────
    private static void DrawATK(Renderer r, int v, int x, int y, int w, int h, int cx, int cy)
    {
        switch (v)
        {
            case 0: DrawATK_CrossedSwords(r, x, y, w, h, cx, cy); break;
            case 1: DrawATK_ClawMarks(r, x, y, w, h, cx, cy); break;
            case 2: DrawATK_LightningBolt(r, x, y, w, h, cx, cy); break;
            case 3: DrawATK_FistImpact(r, x, y, w, h, cx, cy); break;
        }
    }

    // Variant 0: Crossed swords — ornate fantasy weapons
    private static void DrawATK_CrossedSwords(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Impact flash — layered starburst at center
        r.DrawCircle((255, 255, 240), (cx, cy), s * 5 / 100, alpha: 50);
        r.DrawCircle((255, 240, 140), (cx, cy), s * 10 / 100, alpha: 30);
        r.DrawCircle((255, 180, 60), (cx, cy), s * 16 / 100, alpha: 18);

        // Starburst at cross point
        for (int i = 0; i < 12; i++)
        {
            double ang = i * Math.PI / 6;
            int len = s * (8 + (i % 2) * 5) / 100;
            int ex = cx + (int)(Math.Cos(ang) * len);
            int ey = cy + (int)(Math.Sin(ang) * len);
            r.DrawLine((255, 255, 200), (cx, cy), (ex, ey), width: 1, alpha: 35);
        }

        // Sword 1 (top-left to bottom-right) — detailed
        DrawDetailedSword(r, cx - s * 32 / 100, cy - s * 30 / 100, cx + s * 20 / 100, cy + s * 30 / 100, s, 0);
        // Sword 2 (top-right to bottom-left)
        DrawDetailedSword(r, cx + s * 32 / 100, cy - s * 30 / 100, cx - s * 20 / 100, cy + s * 30 / 100, s, 1);

        // Spark particles at intersection
        for (int i = 0; i < 8; i++)
        {
            double ang = i * Math.PI / 4 + 0.3;
            int dist = s * (12 + (i % 3) * 4) / 100;
            int px = cx + (int)(Math.Cos(ang) * dist);
            int py = cy + (int)(Math.Sin(ang) * dist);
            r.DrawCircle((255, 240, 120), (px, py), Math.Max(1, 2 - i / 4), alpha: 35 - i * 3);
        }

        // Battle ribbon banner below
        int banY = cy + s * 26 / 100;
        r.DrawRect((180, 40, 30), (cx - s * 20 / 100, banY, s * 40 / 100, s * 6 / 100), alpha: 40);
        r.DrawRect((200, 60, 40), (cx - s * 19 / 100, banY + 1, s * 38 / 100, 2), alpha: 22);
        // Banner folds at ends
        DrawTriangle(r, cx - s * 24 / 100, banY, s * 6 / 100, (140, 30, 20), 38);
        DrawTriangle(r, cx + s * 18 / 100, banY, s * 6 / 100, (140, 30, 20), 38);
    }

    // Variant 1: Claw scratch marks — fierce and vibrant
    private static void DrawATK_ClawMarks(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Torn material background — layered depth
        r.DrawCircle((100, 20, 10), (cx, cy), s * 38 / 100, alpha: 14);
        r.DrawCircle((140, 30, 15), (cx, cy), s * 28 / 100, alpha: 18);
        r.DrawCircle((180, 40, 20), (cx, cy), s * 18 / 100, alpha: 12);

        // Surface material — torn grey showing red beneath
        r.DrawRect((120, 120, 130), (x + s * 8 / 100, y + s * 5 / 100, w - s * 16 / 100, h - s * 10 / 100), alpha: 18);

        // Cat paw silhouette above scratches
        int pawCx = cx + s * 16 / 100, pawCy = cy - s * 22 / 100;
        r.DrawCircle((60, 20, 10), (pawCx, pawCy), Math.Max(4, s * 8 / 100), alpha: 35);
        // Toe beans
        for (int toe = 0; toe < 3; toe++)
        {
            int tx = pawCx - s * 4 / 100 + toe * s * 4 / 100;
            int ty = pawCy - s * 8 / 100;
            r.DrawCircle((80, 30, 15), (tx, ty), Math.Max(2, s * 3 / 100), alpha: 35);
        }

        // Five claw scratches — deep with multiple layers
        for (int c = 0; c < 5; c++)
        {
            int offsetX = (c - 2) * (s * 10 / 100);
            int topY = cy - s * 14 / 100;
            int botY = cy + s * 34 / 100;
            int curve = (c - 2) * s * 3 / 100;

            // Shadow layer
            r.DrawLine((0, 0, 0), (cx + offsetX + 3, topY + 3), (cx + offsetX - curve + 3, botY + 3), width: 5, alpha: 35);
            // Deep groove
            r.DrawLine((30, 8, 5), (cx + offsetX, topY), (cx + offsetX - curve, botY), width: 5, alpha: 65);
            // Red revealed flesh
            r.DrawLine((200, 40, 20), (cx + offsetX, topY + s * 3 / 100), (cx + offsetX - curve, botY - s * 3 / 100), width: 3, alpha: 55);
            // Inner bright red
            r.DrawLine((255, 80, 40), (cx + offsetX, topY + s * 5 / 100), (cx + offsetX - curve + 1, botY - s * 5 / 100), width: 2, alpha: 40);
            // Specular edge highlight
            r.DrawLine((255, 160, 100), (cx + offsetX + 2, topY + s * 6 / 100), (cx + offsetX - curve + 3, botY - s * 6 / 100), width: 1, alpha: 25);
        }

        // Torn material curls at scratch edges
        for (int i = 0; i < 6; i++)
        {
            int tx = cx + (i * 19 - 47) % (s * 30 / 100) - s * 15 / 100;
            int ty = cy + s * 8 / 100 + (i * 13) % (s * 16 / 100);
            int tsz = Math.Max(2, s * (2 + i % 2) / 100);
            r.DrawRect((140, 135, 130), (tx, ty, tsz, tsz / 2), alpha: 30);
        }

        // Blood/damage droplets
        for (int i = 0; i < 5; i++)
        {
            int dx = cx + (i * 31 - 62) % (s * 40 / 100) - s * 20 / 100;
            int dy = cy + s * 30 / 100 + (i * 17) % (s * 10 / 100);
            r.DrawCircle((180, 30, 20), (dx, dy), Math.Max(1, s * (1 + i % 2) / 100), alpha: 35);
        }

        // Anger marks
        int amX = cx - s * 22 / 100, amY = cy - s * 28 / 100;
        r.DrawLine((255, 60, 30), (amX, amY), (amX + s * 6 / 100, amY), width: 2, alpha: 40);
        r.DrawLine((255, 60, 30), (amX + s * 3 / 100, amY - s * 3 / 100), (amX + s * 3 / 100, amY + s * 3 / 100), width: 2, alpha: 40);
    }

    // Variant 2: Lightning bolt — electrifying storm
    private static void DrawATK_LightningBolt(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Storm clouds at top
        r.DrawCircle((50, 40, 60), (cx - s * 12 / 100, y + s * 10 / 100), Math.Max(5, s * 14 / 100), alpha: 30);
        r.DrawCircle((60, 50, 70), (cx + s * 8 / 100, y + s * 8 / 100), Math.Max(5, s * 12 / 100), alpha: 28);
        r.DrawCircle((45, 38, 55), (cx, y + s * 6 / 100), Math.Max(5, s * 16 / 100), alpha: 35);
        r.DrawCircle((70, 60, 80), (cx - s * 4 / 100, y + s * 12 / 100), Math.Max(4, s * 10 / 100), alpha: 22);
        // Cloud highlights
        r.DrawCircle((80, 70, 100), (cx - s * 6 / 100, y + s * 4 / 100), Math.Max(3, s * 6 / 100), alpha: 18);

        // Electric field glow
        r.DrawCircle((60, 40, 180), (cx, cy), s * 38 / 100, alpha: 10);
        r.DrawCircle((100, 70, 220), (cx, cy), s * 24 / 100, alpha: 14);

        // Main lightning bolt — thick zigzag
        int bw = s * 14 / 100;
        (int, int)[] bolt = [
            (cx + bw, cy - s * 34 / 100),
            (cx - bw / 2, cy - s * 10 / 100),
            (cx + bw * 3 / 4, cy - s * 7 / 100),
            (cx - bw / 3, cy + s * 16 / 100),
            (cx + bw / 2, cy + s * 14 / 100),
            (cx - bw, cy + s * 36 / 100),
        ];

        // Outer electric glow — purple
        for (int i = 0; i < bolt.Length - 1; i++)
            r.DrawLine((160, 120, 255), bolt[i], bolt[i + 1], width: 9, alpha: 12);
        // Mid glow — cyan
        for (int i = 0; i < bolt.Length - 1; i++)
            r.DrawLine((100, 200, 255), bolt[i], bolt[i + 1], width: 6, alpha: 22);
        // Bright core — blue
        for (int i = 0; i < bolt.Length - 1; i++)
            r.DrawLine((180, 220, 255), bolt[i], bolt[i + 1], width: 4, alpha: 40);
        // White hot core
        for (int i = 0; i < bolt.Length - 1; i++)
            r.DrawLine((255, 255, 250), bolt[i], bolt[i + 1], width: 2, alpha: 65);

        // Branch bolts — smaller forks
        r.DrawLine((140, 180, 255), bolt[1], (bolt[1].Item1 - s * 16 / 100, bolt[1].Item2 + s * 12 / 100), width: 2, alpha: 35);
        r.DrawLine((255, 255, 240), bolt[1], (bolt[1].Item1 - s * 16 / 100, bolt[1].Item2 + s * 12 / 100), width: 1, alpha: 25);
        r.DrawLine((140, 180, 255), bolt[3], (bolt[3].Item1 + s * 14 / 100, bolt[3].Item2 + s * 10 / 100), width: 2, alpha: 30);
        r.DrawLine((255, 255, 240), bolt[3], (bolt[3].Item1 + s * 14 / 100, bolt[3].Item2 + s * 10 / 100), width: 1, alpha: 22);
        // Additional sub-branches
        r.DrawLine((120, 160, 240), (bolt[1].Item1 - s * 16 / 100, bolt[1].Item2 + s * 12 / 100),
            (bolt[1].Item1 - s * 22 / 100, bolt[1].Item2 + s * 20 / 100), width: 1, alpha: 22);
        r.DrawLine((120, 160, 240), bolt[4], (bolt[4].Item1 + s * 10 / 100, bolt[4].Item2 - s * 6 / 100), width: 1, alpha: 22);

        // Impact burst at ground — bright flash
        r.DrawCircle((255, 255, 250), bolt[^1], s * 4 / 100, alpha: 50);
        r.DrawCircle((200, 220, 255), bolt[^1], s * 8 / 100, alpha: 30);
        r.DrawCircle((140, 160, 255), bolt[^1], s * 14 / 100, alpha: 15);
        // Ground crack lines from impact
        for (int i = 0; i < 5; i++)
        {
            double ang = Math.PI * 0.2 + i * Math.PI * 0.15;
            int len = s * (6 + i * 2) / 100;
            int gx = bolt[^1].Item1 + (int)(Math.Cos(ang) * len);
            int gy = bolt[^1].Item2 + (int)(Math.Sin(ang) * len / 3);
            r.DrawLine((160, 180, 255), bolt[^1], (gx, gy), width: 1, alpha: 25);
        }

        // Rain streaks
        for (int i = 0; i < 8; i++)
        {
            int rx = x + s * 8 / 100 + i * s * 10 / 100;
            int ry1 = y + s * 20 / 100 + (i * 17) % (s * 15 / 100);
            r.DrawLine((120, 140, 180), (rx, ry1), (rx - 2, ry1 + s * 6 / 100), width: 1, alpha: 16);
        }

        // Electric static sparks
        for (int i = 0; i < 6; i++)
        {
            double ang = i * 1.1 + 0.5;
            int dist = s * (16 + (i * 7) % 14) / 100;
            int px = cx + (int)(Math.Cos(ang) * dist);
            int py = cy + (int)(Math.Sin(ang) * dist);
            r.DrawCircle((180, 200, 255), (px, py), 1, alpha: 40);
            r.DrawRect((180, 200, 255), (px - 2, py, 5, 1), alpha: 22);
            r.DrawRect((180, 200, 255), (px, py - 2, 1, 5), alpha: 22);
        }
    }

    // Variant 3: Fist impact — comic book punch
    private static void DrawATK_FistImpact(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Impact starburst background — jagged rays
        for (int i = 0; i < 14; i++)
        {
            double ang = i * Math.PI / 7;
            int len = s * (28 + (i % 2) * 12) / 100;
            int ex = cx + (int)(Math.Cos(ang) * len);
            int ey = cy + (int)(Math.Sin(ang) * len);
            var col = i % 2 == 0 ? (255, 240, 80) : (255, 200, 40);
            r.DrawLine(col, (cx, cy), (ex, ey), width: i % 2 == 0 ? 4 : 2, alpha: 25);
        }

        // Impact rings — vibrant concentric
        r.DrawCircle((255, 50, 20), (cx, cy), s * 38 / 100, width: 3, alpha: 18);
        r.DrawCircle((255, 100, 40), (cx, cy), s * 30 / 100, width: 2, alpha: 25);
        r.DrawCircle((255, 160, 60), (cx, cy), s * 22 / 100, width: 2, alpha: 30);
        r.DrawCircle((255, 220, 100), (cx, cy), s * 14 / 100, alpha: 25);
        r.DrawCircle((255, 255, 180), (cx, cy), s * 6 / 100, alpha: 35);

        // Fist — detailed with proper shading
        int fistW = s * 30 / 100, fistH = s * 26 / 100;
        int fx = cx - fistW / 2 - s * 3 / 100;
        int fy = cy - fistH / 2 - s * 4 / 100;
        // Shadow
        r.DrawRect((0, 0, 0), (fx + 4, fy + 4, fistW, fistH), alpha: 45);
        // Fist base — warm skin tone
        r.DrawRect((230, 180, 130), (fx, fy, fistW, fistH), alpha: 70);
        // Shading gradient
        for (int b = 0; b < 4; b++)
        {
            int bh = fistH / 4;
            int da = b < 2 ? 20 - b * 8 : 5;
            r.DrawRect((250, 200, 150), (fx + 2, fy + b * bh, fistW - 4, bh), alpha: da);
        }
        // Dark outline
        r.DrawRect((120, 80, 50), (fx, fy, fistW, fistH), width: 2, alpha: 50);

        // Knuckles — four prominent bumps
        for (int k = 0; k < 4; k++)
        {
            int kx = fx + fistW * (k + 1) / 5;
            r.DrawCircle((240, 195, 140), (kx, fy - 1), Math.Max(3, fistW / 7), alpha: 55);
            r.DrawCircle((255, 220, 170), (kx - 1, fy - 2), Math.Max(2, fistW / 10), alpha: 30);
            // Knuckle highlight
            r.DrawCircle((255, 240, 200), (kx - 1, fy - 3), Math.Max(1, fistW / 14), alpha: 20);
        }

        // Thumb — rounded
        int thumbR = Math.Max(4, fistW / 5);
        r.DrawCircle((220, 170, 120), (fx + fistW + s * 2 / 100, fy + fistH / 2), thumbR, alpha: 55);
        r.DrawCircle((240, 190, 140), (fx + fistW + s * 1 / 100, fy + fistH / 2 - 1), thumbR * 2 / 3, alpha: 25);
        // Thumbnail
        r.DrawCircle((255, 230, 200), (fx + fistW + s * 3 / 100, fy + fistH / 2 - thumbR / 2), Math.Max(1, thumbR / 3), alpha: 30);

        // Wrist/arm behind
        r.DrawRect((220, 170, 120), (fx + fistW - 4, fy + 4, s * 12 / 100, fistH - 8), alpha: 45);
        r.DrawRect((200, 150, 100), (fx + fistW - 4, fy + 4, s * 12 / 100, fistH - 8), width: 1, alpha: 30);

        // Speed/motion lines — coming from behind fist
        for (int i = 0; i < 8; i++)
        {
            int ly = cy - s * 24 / 100 + i * s * 7 / 100;
            int lx = cx + s * 22 / 100 + i * s * 2 / 100;
            int ll = s * (10 + (i % 3) * 4) / 100;
            r.DrawLine((255, 200, 80), (lx, ly), (lx + ll, ly), width: 2, alpha: 28 - i * 2);
        }

        // "POW" text background — comic book style
        int powX = cx - s * 6 / 100, powY = cy + s * 22 / 100;
        // Starburst behind text
        for (int i = 0; i < 8; i++)
        {
            double ang = i * Math.PI / 4 + 0.2;
            int len = s * (6 + (i % 2) * 4) / 100;
            int ex = powX + (int)(Math.Cos(ang) * len);
            int ey = powY + (int)(Math.Sin(ang) * len);
            r.DrawLine((255, 255, 0), (powX, powY), (ex, ey), width: 2, alpha: 30);
        }
        int powFs = Math.Max(8, s * 12 / 100);
        r.DrawText("POW!", powX + 1, powY + 1, powFs, (0, 0, 0), bold: true, anchorX: "center", anchorY: "center", alpha: 55);
        r.DrawText("POW!", powX, powY, powFs, (255, 255, 0), bold: true, anchorX: "center", anchorY: "center", alpha: 70);

        // Debris chunks flying
        for (int i = 0; i < 6; i++)
        {
            double ang = i * 1.05 + 0.3;
            int dist = s * (20 + i * 4) / 100;
            int dx = cx + (int)(Math.Cos(ang) * dist);
            int dy = cy + (int)(Math.Sin(ang) * dist * 0.7);
            int ds = Math.Max(2, s * (2 + i % 2) / 100);
            r.DrawRect((200, 160, 100), (dx, dy, ds, ds), alpha: 25);
        }
    }

    // ─── DEFUSE ────────────────────────────────────────────────
    private static void DrawDEF(Renderer r, int v, int x, int y, int w, int h, int cx, int cy)
    {
        switch (v)
        {
            case 0: DrawDEF_WireCutters(r, x, y, w, h, cx, cy); break;
            case 1: DrawDEF_Shield(r, x, y, w, h, cx, cy); break;
            case 2: DrawDEF_LaserPointer(r, x, y, w, h, cx, cy); break;
            case 3: DrawDEF_Catnip(r, x, y, w, h, cx, cy); break;
        }
    }

    private static void DrawDEF_WireCutters(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Timer/bomb wire context — background wiring
        for (int i = 0; i < 4; i++)
        {
            int wy = cy - s * 6 / 100 + (i - 2) * s * 10 / 100;
            var wireCol = i == 1 ? (200, 40, 40) : i == 2 ? (40, 40, 200) : i == 0 ? (40, 180, 40) : (200, 200, 40);
            r.DrawLine(wireCol, (x + s * 5 / 100, wy), (x + w - s * 5 / 100, wy), width: 2, alpha: 22);
        }

        // Spark glow at cutting point — radiant
        r.DrawCircle((80, 255, 160), (cx, cy - s * 6 / 100), s * 14 / 100, alpha: 18);
        r.DrawCircle((140, 255, 200), (cx, cy - s * 6 / 100), s * 8 / 100, alpha: 30);
        r.DrawCircle((200, 255, 230), (cx, cy - s * 6 / 100), s * 4 / 100, alpha: 45);

        // THE red wire being cut — emphasized
        int wireY = cy - s * 6 / 100;
        r.DrawLine((200, 40, 40), (x + s * 8 / 100, wireY), (cx - s * 7 / 100, wireY), width: 3, alpha: 65);
        r.DrawLine((200, 40, 40), (cx + s * 7 / 100, wireY), (x + w - s * 8 / 100, wireY), width: 3, alpha: 65);
        // Wire break sparks — electric burst
        for (int i = 0; i < 8; i++)
        {
            double ang = i * Math.PI / 4 + 0.2;
            int len = s * (4 + (i % 3) * 2) / 100;
            int sx = cx + (int)(Math.Cos(ang) * len);
            int sy = wireY + (int)(Math.Sin(ang) * len);
            r.DrawLine((255, 255, 200), (cx, wireY), (sx, sy), width: 1, alpha: 40 - i * 3);
        }
        // Wire insulation at break point
        r.DrawCircle((200, 40, 40), (cx - s * 7 / 100, wireY), Math.Max(2, s * 2 / 100), alpha: 40);
        r.DrawCircle((200, 40, 40), (cx + s * 7 / 100, wireY), Math.Max(2, s * 2 / 100), alpha: 40);
        // Copper core visible
        r.DrawCircle((220, 160, 60), (cx - s * 6 / 100, wireY), Math.Max(1, s * 1 / 100), alpha: 45);
        r.DrawCircle((220, 160, 60), (cx + s * 6 / 100, wireY), Math.Max(1, s * 1 / 100), alpha: 45);

        // Pliers — two handles crossing in X shape
        // Handle 1 (lower-left) — rubber grip with detail
        r.DrawLine((70, 70, 80), (cx - s * 22 / 100, cy + s * 32 / 100), (cx - s * 3 / 100, cy - s * 4 / 100), width: 5, alpha: 65);
        r.DrawLine((100, 100, 115), (cx - s * 21 / 100, cy + s * 31 / 100), (cx - s * 2 / 100, cy - s * 3 / 100), width: 3, alpha: 25);
        r.DrawLine((40, 40, 48), (cx - s * 22 / 100, cy + s * 32 / 100), (cx - s * 3 / 100, cy - s * 4 / 100), width: 5, alpha: 15);
        // Handle 2 (lower-right)
        r.DrawLine((70, 70, 80), (cx + s * 22 / 100, cy + s * 32 / 100), (cx + s * 3 / 100, cy - s * 4 / 100), width: 5, alpha: 65);
        r.DrawLine((100, 100, 115), (cx + s * 21 / 100, cy + s * 31 / 100), (cx + s * 2 / 100, cy - s * 3 / 100), width: 3, alpha: 25);
        r.DrawLine((40, 40, 48), (cx + s * 22 / 100, cy + s * 32 / 100), (cx + s * 3 / 100, cy - s * 4 / 100), width: 5, alpha: 15);

        // Pivot point — detailed bolt
        int pivotR = Math.Max(4, s * 4 / 100);
        r.DrawCircle((90, 90, 100), (cx, cy + s * 4 / 100), pivotR + 1, alpha: 55);
        r.DrawCircle((130, 130, 145), (cx, cy + s * 4 / 100), pivotR, alpha: 70);
        r.DrawCircle((180, 180, 195), (cx - 1, cy + s * 4 / 100 - 1), pivotR / 2, alpha: 30);
        // Bolt slot
        r.DrawRect((80, 80, 90), (cx - pivotR / 3, cy + s * 4 / 100 - 1, pivotR * 2 / 3, 2), alpha: 30);

        // Jaw tips — cutting edges
        r.DrawCircle((100, 100, 115), (cx - s * 4 / 100, cy - s * 6 / 100), Math.Max(3, s * 3 / 100), alpha: 65);
        r.DrawCircle((100, 100, 115), (cx + s * 4 / 100, cy - s * 6 / 100), Math.Max(3, s * 3 / 100), alpha: 65);
        // Cutting edge highlight
        r.DrawLine((200, 200, 220), (cx - s * 3 / 100, cy - s * 8 / 100), (cx + s * 3 / 100, cy - s * 8 / 100), width: 1, alpha: 30);

        // Rubber grips — textured
        int gripW = s * 7 / 100, gripH = s * 16 / 100;
        r.DrawRect((40, 160, 80), (cx - s * 24 / 100, cy + s * 22 / 100, gripW, gripH), alpha: 50);
        r.DrawRect((40, 160, 80), (cx + s * 17 / 100, cy + s * 22 / 100, gripW, gripH), alpha: 50);
        // Grip ridges
        for (int grip = 0; grip < 4; grip++)
        {
            int gy = cy + s * 24 / 100 + grip * (gripH / 4);
            r.DrawLine((60, 200, 110), (cx - s * 24 / 100, gy), (cx - s * 17 / 100, gy), width: 1, alpha: 22);
            r.DrawLine((60, 200, 110), (cx + s * 17 / 100, gy), (cx + s * 24 / 100, gy), width: 1, alpha: 22);
        }

        // Timer display in corner — tense!
        int timerX = x + s * 6 / 100, timerY = y + h - s * 14 / 100;
        r.DrawRect((20, 20, 20), (timerX, timerY, s * 18 / 100, s * 8 / 100), alpha: 45);
        r.DrawRect((40, 40, 40), (timerX, timerY, s * 18 / 100, s * 8 / 100), width: 1, alpha: 35);
        int timerFs = Math.Max(6, s * 6 / 100);
        r.DrawText("0:03", timerX + s * 9 / 100, timerY + s * 4 / 100, timerFs, (255, 40, 40),
            anchorX: "center", anchorY: "center", alpha: 60);
    }

    private static void DrawDEF_Shield(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Protective barrier effect — concentric arcs
        for (int arc = 0; arc < 4; arc++)
        {
            int ar = s * (34 + arc * 5) / 100;
            var arcCol = arc % 2 == 0 ? (60, 220, 140) : (80, 240, 160);
            r.DrawCircle(arcCol, (cx, cy), ar, width: 2, alpha: 14 - arc * 2);
        }

        // Energy particles along barrier
        for (int i = 0; i < 8; i++)
        {
            double ang = i * Math.PI / 4 + 0.3;
            int dist = s * 35 / 100;
            int px = cx + (int)(Math.Cos(ang) * dist);
            int py = cy + (int)(Math.Sin(ang) * dist);
            r.DrawCircle((120, 255, 180), (px, py), 2, alpha: 30);
        }

        // Shield body — proper heraldic shape
        int shW = s * 44 / 100, shH = s * 54 / 100;
        int shX = cx - shW / 2, shY = cy - shH * 38 / 100;

        // Shadow
        r.DrawRect((0, 0, 0), (shX + 4, shY + 4, shW, shH * 65 / 100), alpha: 35);

        // Main shield — gradient fill with rows
        for (int row = 0; row < shH * 65 / 100; row++)
        {
            float t = (float)row / (shH * 65 / 100);
            int rr = (int)(30 + 30 * (1f - t));
            int gg = (int)(120 + 40 * (1f - t));
            int bb = (int)(60 + 30 * (1f - t));
            r.DrawRect((rr, gg, bb), (shX, shY + row, shW, 1), alpha: 65);
        }
        // Pointed bottom
        for (int p = 0; p < 12; p++)
        {
            int pw = shW * (12 - p) / 12;
            int py = shY + shH * 65 / 100 + p * (shH * 35 / 100) / 12;
            float t = (float)p / 12;
            int gg = (int)(130 - 30 * t);
            r.DrawRect((30 + (int)(20 * t), gg, 55), (cx - pw / 2, py, pw, shH * 35 / 100 / 12 + 1), alpha: 65 - p * 3);
        }

        // Shield border — metallic gold
        r.DrawRect((200, 170, 60), (shX, shY, shW, shH * 65 / 100), width: 3, alpha: 50);

        // Diagonal cross division — heraldic
        r.DrawLine((200, 170, 60), (shX, shY), (cx, cy + shH * 25 / 100), width: 2, alpha: 35);
        r.DrawLine((200, 170, 60), (shX + shW, shY), (cx, cy + shH * 25 / 100), width: 2, alpha: 35);

        // Cat paw emblem in center
        int emblCy = cy - s * 2 / 100;
        r.DrawCircle((200, 170, 60), (cx, emblCy + s * 3 / 100), Math.Max(4, s * 7 / 100), alpha: 40);
        // Toe beans
        r.DrawCircle((220, 190, 80), (cx - s * 4 / 100, emblCy - s * 2 / 100), Math.Max(2, s * 3 / 100), alpha: 38);
        r.DrawCircle((220, 190, 80), (cx + s * 4 / 100, emblCy - s * 2 / 100), Math.Max(2, s * 3 / 100), alpha: 38);
        r.DrawCircle((220, 190, 80), (cx, emblCy - s * 5 / 100), Math.Max(2, s * 3 / 100), alpha: 38);

        // Specular highlight — top left
        r.DrawCircle((180, 255, 220), (shX + shW / 5, shY + shH / 8), Math.Max(3, shW / 6), alpha: 18);

        // Sparkle accents at corners
        r.DrawCircle((200, 255, 220), (shX - 2, shY + 2), 3, alpha: 50);
        r.DrawCircle((200, 255, 220), (shX + shW + 2, shY + 2), 3, alpha: 45);
        r.DrawCircle((200, 255, 220), (cx, shY + shH * 90 / 100), 3, alpha: 40);

        // Rivets along top border
        for (int riv = 0; riv < 5; riv++)
        {
            int rivX = shX + shW * (riv + 1) / 6;
            r.DrawCircle((240, 210, 100), (rivX, shY + 2), Math.Max(1, s * 1 / 100), alpha: 40);
        }
    }

    private static void DrawDEF_LaserPointer(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Red laser dot — pulsing concentric glow
        int dotX = cx - s * 12 / 100, dotY = cy - s * 20 / 100;
        r.DrawCircle((255, 0, 0), (dotX, dotY), s * 16 / 100, alpha: 8);
        r.DrawCircle((255, 20, 20), (dotX, dotY), s * 10 / 100, alpha: 16);
        r.DrawCircle((255, 60, 60), (dotX, dotY), s * 6 / 100, alpha: 30);
        r.DrawCircle((255, 120, 120), (dotX, dotY), s * 3 / 100, alpha: 50);
        r.DrawCircle((255, 200, 200), (dotX, dotY), Math.Max(1, s * 1 / 100 + 1), alpha: 65);

        // Laser beam — from device to dot
        int lpX = cx + s * 12 / 100, lpY = cy + s * 24 / 100;
        // Beam outer glow
        r.DrawLine((255, 40, 40), (lpX, lpY), (dotX, dotY), width: 3, alpha: 18);
        // Beam core  
        r.DrawLine((255, 60, 60), (lpX, lpY), (dotX, dotY), width: 2, alpha: 35);
        r.DrawLine((255, 120, 120), (lpX, lpY), (dotX, dotY), width: 1, alpha: 50);

        // Laser pointer device — detailed cylinder
        int devW = s * 32 / 100, devH = s * 8 / 100;
        r.DrawRect((0, 0, 0), (lpX + 2, lpY + 2, devW, devH), alpha: 30);
        r.DrawRect((60, 60, 70), (lpX, lpY, devW, devH), alpha: 72);
        // Metallic band
        r.DrawRect((100, 100, 115), (lpX + 2, lpY + 2, devW - 4, 2), alpha: 35);
        r.DrawRect((80, 80, 90), (lpX + 2, lpY + devH - 3, devW - 4, 2), alpha: 22);
        // Clip
        r.DrawRect((90, 90, 100), (lpX + devW - s * 4 / 100, lpY - s * 4 / 100, s * 2 / 100, s * 4 / 100 + devH), alpha: 40);
        // Button
        r.DrawCircle((200, 50, 50), (lpX + devW * 35 / 100, lpY + devH / 2), Math.Max(2, devH / 3), alpha: 55);
        r.DrawCircle((255, 80, 80), (lpX + devW * 35 / 100 - 1, lpY + devH / 2 - 1), Math.Max(1, devH / 5), alpha: 25);
        // Lens opening
        r.DrawCircle((255, 100, 100), (lpX - 1, lpY + devH / 2), Math.Max(2, devH / 3), alpha: 45);

        // Cat silhouette chasing dot — detailed
        int catCx = cx + s * 2 / 100, catCy = cy + s * 2 / 100;
        // Body — crouched/pouncing
        r.DrawCircle((180, 140, 90), (catCx, catCy), Math.Max(5, s * 12 / 100), alpha: 40);
        r.DrawCircle((200, 160, 110), (catCx - s * 2 / 100, catCy - s * 2 / 100), Math.Max(4, s * 8 / 100), alpha: 22);
        // Head — looking up at dot
        int headCx = catCx - s * 10 / 100, headCy = catCy - s * 8 / 100;
        r.DrawCircle((190, 150, 100), (headCx, headCy), Math.Max(4, s * 8 / 100), alpha: 45);
        // Ears
        DrawTriangle(r, headCx - s * 8 / 100, headCy - s * 12 / 100, s * 6 / 100, (190, 150, 100), 42);
        DrawTriangle(r, headCx + s * 2 / 100, headCy - s * 12 / 100, s * 6 / 100, (190, 150, 100), 42);
        DrawTriangle(r, headCx - s * 7 / 100, headCy - s * 10 / 100, s * 4 / 100, (220, 150, 130), 28);
        DrawTriangle(r, headCx + s * 3 / 100, headCy - s * 10 / 100, s * 4 / 100, (220, 150, 130), 28);
        // Eyes — wide, fixated on dot
        r.DrawCircle((255, 255, 200), (headCx - s * 3 / 100, headCy - s * 2 / 100), Math.Max(2, s * 3 / 100), alpha: 55);
        r.DrawCircle((255, 255, 200), (headCx + s * 3 / 100, headCy - s * 2 / 100), Math.Max(2, s * 3 / 100), alpha: 55);
        r.DrawCircle((0, 0, 0), (headCx - s * 3 / 100, headCy - s * 2 / 100), Math.Max(1, s * 2 / 100), alpha: 60);
        r.DrawCircle((0, 0, 0), (headCx + s * 3 / 100, headCy - s * 2 / 100), Math.Max(1, s * 2 / 100), alpha: 60);
        // Nose
        DrawTriangle(r, headCx - s * 1 / 100, headCy + s * 2 / 100, Math.Max(2, s * 2 / 100), (200, 120, 100), 40);
        // Whiskers
        r.DrawLine((160, 120, 80), (headCx - s * 5 / 100, headCy + s * 2 / 100), (headCx - s * 14 / 100, headCy), width: 1, alpha: 30);
        r.DrawLine((160, 120, 80), (headCx - s * 5 / 100, headCy + s * 3 / 100), (headCx - s * 14 / 100, headCy + s * 4 / 100), width: 1, alpha: 28);

        // Front paw reaching toward dot
        r.DrawLine((180, 140, 90), (catCx - s * 8 / 100, catCy + s * 4 / 100), (dotX + s * 4 / 100, dotY + s * 6 / 100), width: 3, alpha: 35);
        // Paw pad
        r.DrawCircle((200, 160, 120), (dotX + s * 5 / 100, dotY + s * 7 / 100), Math.Max(2, s * 3 / 100), alpha: 40);
        // Toe beans
        r.DrawCircle((220, 180, 140), (dotX + s * 3 / 100, dotY + s * 5 / 100), Math.Max(1, s * 1 / 100), alpha: 35);
        r.DrawCircle((220, 180, 140), (dotX + s * 6 / 100, dotY + s * 5 / 100), Math.Max(1, s * 1 / 100), alpha: 35);

        // Tail — curved upward excitedly
        r.DrawLine((180, 140, 90), (catCx + s * 10 / 100, catCy), (catCx + s * 16 / 100, catCy - s * 12 / 100), width: 3, alpha: 38);
        r.DrawLine((180, 140, 90), (catCx + s * 16 / 100, catCy - s * 12 / 100), (catCx + s * 12 / 100, catCy - s * 16 / 100), width: 2, alpha: 32);

        // Floor reflection of laser
        r.DrawCircle((255, 40, 40), (dotX, dotY + s * 30 / 100), s * 4 / 100, alpha: 6);
    }

    private static void DrawDEF_Catnip(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Dreamy swirl aura — multiple color rings
        r.DrawCircle((80, 220, 120), (cx, cy), s * 38 / 100, alpha: 10);
        r.DrawCircle((120, 200, 160), (cx, cy), s * 30 / 100, alpha: 12);
        r.DrawCircle((160, 220, 180), (cx + s * 3 / 100, cy - s * 3 / 100), s * 20 / 100, alpha: 10);

        // Pot/container for the catnip
        int potW = s * 20 / 100, potH = s * 16 / 100;
        int potX = cx - s * 4 / 100 - potW / 2, potY = cy + s * 14 / 100;
        // Pot shadow
        r.DrawCircle((0, 0, 0), (potX + potW / 2 + 2, potY + potH + 2), Math.Max(3, potW / 2), alpha: 20);
        // Pot body — terracotta
        r.DrawRect((180, 100, 60), (potX, potY, potW, potH), alpha: 60);
        r.DrawRect((200, 120, 70), (potX + 1, potY + 1, potW - 2, 3), alpha: 25); // rim highlight
        r.DrawRect((160, 80, 50), (potX + 2, potY + potH - 3, potW - 4, 2), alpha: 20); // bottom shadow
        // Pot rim
        r.DrawRect((200, 110, 65), (potX - 2, potY - 2, potW + 4, 4), alpha: 55);
        // Soil visible
        r.DrawRect((80, 50, 30), (potX + 2, potY + 1, potW - 4, 4), alpha: 30);

        // Catnip plant — rich stem with branches
        int stemBase = potY;
        r.DrawLine((50, 130, 50), (cx - s * 4 / 100, stemBase), (cx - s * 4 / 100, cy - s * 14 / 100), width: 3, alpha: 60);
        // Side branches
        r.DrawLine((60, 140, 60), (cx - s * 4 / 100, cy - s * 2 / 100), (cx - s * 14 / 100, cy - s * 8 / 100), width: 2, alpha: 45);
        r.DrawLine((60, 140, 60), (cx - s * 4 / 100, cy + s * 4 / 100), (cx + s * 6 / 100, cy), width: 2, alpha: 45);
        r.DrawLine((60, 140, 60), (cx - s * 4 / 100, cy - s * 8 / 100), (cx + s * 8 / 100, cy - s * 12 / 100), width: 2, alpha: 42);

        // Leaves — detailed with veins (3 pairs + top)
        (int lx, int ly, int side)[] leaves = [
            (cx - s * 14 / 100, cy - s * 8 / 100, -1),
            (cx + s * 6 / 100, cy, 1),
            (cx + s * 8 / 100, cy - s * 12 / 100, 1),
            (cx - s * 10 / 100, cy + s * 2 / 100, -1),
        ];
        foreach (var (lx, ly, side) in leaves)
        {
            int leafR = Math.Max(4, s * 7 / 100);
            // Leaf body — two overlapping circles for leaf shape
            r.DrawCircle((60, 170, 60), (lx, ly), leafR, alpha: 40);
            r.DrawCircle((80, 200, 80), (lx + side * leafR / 3, ly - leafR / 4), leafR * 70 / 100, alpha: 28);
            // Leaf vein
            r.DrawLine((40, 120, 40), (lx - side * leafR * 60 / 100, ly), (lx + side * leafR * 60 / 100, ly), width: 1, alpha: 22);
            // Leaf highlights
            r.DrawCircle((100, 220, 100), (lx - side * leafR / 4, ly - leafR / 3), leafR / 3, alpha: 16);
        }

        // Flower clusters at top — purple/lavender
        int flowerCy = cy - s * 16 / 100;
        for (int f = 0; f < 5; f++)
        {
            double ang = f * Math.PI / 2.5 - Math.PI / 4;
            int fx = cx - s * 4 / 100 + (int)(Math.Cos(ang) * s * 4 / 100);
            int fy = flowerCy + (int)(Math.Sin(ang) * s * 3 / 100);
            r.DrawCircle((180, 120, 220), (fx, fy), Math.Max(2, s * 3 / 100), alpha: 42);
            r.DrawCircle((220, 160, 240), (fx, fy), Math.Max(1, s * 2 / 100), alpha: 28);
        }
        // Center of flower cluster
        r.DrawCircle((255, 220, 100), (cx - s * 4 / 100, flowerCy), Math.Max(1, s * 1 / 100 + 1), alpha: 40);

        // Happy cat — larger, more detailed
        int catCx = cx + s * 18 / 100, catCy = cy + s * 4 / 100;
        // Body
        r.DrawCircle((200, 165, 100), (catCx, catCy + s * 6 / 100), Math.Max(5, s * 10 / 100), alpha: 35);
        // Head — tilted happily
        r.DrawCircle((210, 175, 110), (catCx, catCy - s * 4 / 100), Math.Max(5, s * 9 / 100), alpha: 45);
        // Ears
        DrawTriangle(r, catCx - s * 8 / 100, catCy - s * 14 / 100, s * 6 / 100, (210, 175, 110), 42);
        DrawTriangle(r, catCx + s * 2 / 100, catCy - s * 14 / 100, s * 6 / 100, (210, 175, 110), 42);
        DrawTriangle(r, catCx - s * 7 / 100, catCy - s * 12 / 100, s * 4 / 100, (230, 150, 130), 28);
        DrawTriangle(r, catCx + s * 3 / 100, catCy - s * 12 / 100, s * 4 / 100, (230, 150, 130), 28);
        // Happy closed eyes (^ ^)
        r.DrawLine((80, 60, 40), (catCx - s * 5 / 100, catCy - s * 2 / 100),
            (catCx - s * 3 / 100, catCy - s * 5 / 100), width: 2, alpha: 55);
        r.DrawLine((80, 60, 40), (catCx - s * 3 / 100, catCy - s * 5 / 100),
            (catCx - s * 1 / 100, catCy - s * 2 / 100), width: 2, alpha: 55);
        r.DrawLine((80, 60, 40), (catCx + s * 1 / 100, catCy - s * 2 / 100),
            (catCx + s * 3 / 100, catCy - s * 5 / 100), width: 2, alpha: 55);
        r.DrawLine((80, 60, 40), (catCx + s * 3 / 100, catCy - s * 5 / 100),
            (catCx + s * 5 / 100, catCy - s * 2 / 100), width: 2, alpha: 55);
        // Wide smile
        r.DrawCircle((180, 100, 60), (catCx, catCy + s * 2 / 100), Math.Max(3, s * 4 / 100), width: 1, alpha: 40);
        // Blush marks
        r.DrawCircle((255, 150, 150), (catCx - s * 6 / 100, catCy + s * 1 / 100), Math.Max(2, s * 2 / 100), alpha: 20);
        r.DrawCircle((255, 150, 150), (catCx + s * 6 / 100, catCy + s * 1 / 100), Math.Max(2, s * 2 / 100), alpha: 20);
        // Tail curled happily
        r.DrawLine((200, 165, 100), (catCx + s * 8 / 100, catCy + s * 8 / 100), (catCx + s * 14 / 100, catCy + s * 4 / 100), width: 2, alpha: 35);
        r.DrawLine((200, 165, 100), (catCx + s * 14 / 100, catCy + s * 4 / 100), (catCx + s * 12 / 100, catCy), width: 2, alpha: 30);

        // Floating hearts
        r.DrawText("♥", cx - s * 24 / 100, cy - s * 28 / 100, Math.Max(8, s * 8 / 100), (255, 120, 160),
            anchorX: "center", anchorY: "center", alpha: 42);
        r.DrawText("♥", cx + s * 20 / 100, cy - s * 22 / 100, Math.Max(6, s * 6 / 100), (255, 140, 180),
            anchorX: "center", anchorY: "center", alpha: 35);

        // Sparkles
        for (int sp = 0; sp < 4; sp++)
        {
            int spx = cx + (sp * 37 - 55) % (s * 40 / 100) - s * 10 / 100;
            int spy = cy + (sp * 23 - 40) % (s * 30 / 100) - s * 18 / 100;
            r.DrawCircle((255, 255, 200), (spx, spy), 1, alpha: 40);
            r.DrawRect((255, 255, 200), (spx - 2, spy, 5, 1), alpha: 22);
            r.DrawRect((255, 255, 200), (spx, spy - 2, 1, 5), alpha: 22);
        }
    }

    // ─── SKIP ──────────────────────────────────────────────────
    private static void DrawSKIP(Renderer r, int v, int x, int y, int w, int h, int cx, int cy)
    {
        switch (v)
        {
            case 0: DrawSKIP_FastForward(r, x, y, w, h, cx, cy); break;
            case 1: DrawSKIP_RunningCat(r, x, y, w, h, cx, cy); break;
            case 2: DrawSKIP_Hourglass(r, x, y, w, h, cx, cy); break;
            case 3: DrawSKIP_SpringBoard(r, x, y, w, h, cx, cy); break;
        }
    }

    private static void DrawSKIP_FastForward(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Speed streak background
        for (int i = 0; i < 12; i++)
        {
            int ly = y + s * 6 / 100 + i * s * 7 / 100;
            int ll = s * (16 + (i * 7) % 20) / 100;
            int lx = x + s * 4 / 100 + (i * 11) % (s * 10 / 100);
            var col = i % 3 == 0 ? (255, 230, 60) : i % 3 == 1 ? (255, 200, 30) : (255, 180, 0);
            r.DrawLine(col, (lx, ly), (lx + ll, ly), width: 1, alpha: 14);
        }

        // Circular speed ring behind
        r.DrawCircle((255, 200, 40), (cx, cy), s * 30 / 100, alpha: 10);
        r.DrawCircle((255, 220, 60), (cx, cy), s * 24 / 100, alpha: 14);

        // Double chevron arrows — large and metallic gold
        for (int ch = 0; ch < 2; ch++)
        {
            int chOff = ch * s * 18 / 100 - s * 9 / 100;
            int ax = cx + chOff;

            // Arrow outer glow
            r.DrawLine((255, 180, 0), (ax - s * 14 / 100, cy - s * 24 / 100), (ax + s * 6 / 100, cy), width: 7, alpha: 16);
            r.DrawLine((255, 180, 0), (ax - s * 14 / 100, cy + s * 24 / 100), (ax + s * 6 / 100, cy), width: 7, alpha: 16);
            // Arrow body — filled with gradient
            for (int thick = 0; thick < 3; thick++)
            {
                int tw = 5 - thick;
                int ta = 30 + thick * 15;
                int tint = thick * 20;
                r.DrawLine((255, 220 + tint / 2, 60 + tint), (ax - s * 14 / 100, cy - s * 24 / 100), (ax + s * 6 / 100, cy), width: tw, alpha: ta);
                r.DrawLine((255, 220 + tint / 2, 60 + tint), (ax - s * 14 / 100, cy + s * 24 / 100), (ax + s * 6 / 100, cy), width: tw, alpha: ta);
            }
            // Bright edge highlight
            r.DrawLine((255, 255, 220), (ax - s * 13 / 100, cy - s * 22 / 100), (ax + s * 5 / 100, cy - 1), width: 1, alpha: 28);
        }

        // Speed text
        int speedFs = Math.Max(6, s * 6 / 100);
        r.DrawText("SKIP!", cx + 1, cy + s * 32 / 100 + 1, speedFs, (0, 0, 0), bold: true, anchorX: "center", anchorY: "center", alpha: 40);
        r.DrawText("SKIP!", cx, cy + s * 32 / 100, speedFs, (255, 220, 60), bold: true, anchorX: "center", anchorY: "center", alpha: 55);

        // Wind whoosh particles
        for (int i = 0; i < 6; i++)
        {
            int px = cx - s * 30 / 100 - i * s * 2 / 100;
            int py = cy - s * 14 / 100 + i * s * 6 / 100;
            r.DrawCircle((255, 240, 160), (px, py), Math.Max(1, 2 - i / 3), alpha: 30 - i * 4);
        }
    }

    private static void DrawSKIP_RunningCat(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Ground line
        int groundY = cy + s * 22 / 100;
        r.DrawLine((120, 100, 60), (x + s * 5 / 100, groundY), (x + w - s * 5 / 100, groundY), width: 2, alpha: 30);
        // Ground texture
        for (int i = 0; i < 6; i++)
        {
            int gx = x + s * 10 / 100 + i * s * 12 / 100;
            r.DrawRect((100, 80, 50), (gx, groundY + 2, s * 4 / 100, 2), alpha: 20);
        }

        // Dust cloud — large and billowing
        r.DrawCircle((200, 180, 140), (cx - s * 22 / 100, groundY - s * 6 / 100), Math.Max(5, s * 10 / 100), alpha: 22);
        r.DrawCircle((180, 160, 120), (cx - s * 30 / 100, groundY - s * 4 / 100), Math.Max(4, s * 8 / 100), alpha: 18);
        r.DrawCircle((190, 170, 130), (cx - s * 26 / 100, groundY - s * 10 / 100), Math.Max(4, s * 7 / 100), alpha: 16);
        r.DrawCircle((170, 150, 110), (cx - s * 34 / 100, groundY - s * 2 / 100), Math.Max(3, s * 6 / 100), alpha: 14);
        // Dust particles
        for (int i = 0; i < 5; i++)
        {
            int dx = cx - s * 18 / 100 - i * s * 5 / 100;
            int dy = groundY - s * (2 + i * 2) / 100;
            r.DrawCircle((190, 170, 130), (dx, dy), Math.Max(1, 3 - i / 2), alpha: 22 - i * 3);
        }

        // Cat body — elongated, running pose with fur detail
        int catCx = cx + s * 4 / 100, catCy = cy - s * 2 / 100;
        // Body — oval
        r.DrawCircle((200, 160, 80), (catCx, catCy), Math.Max(6, s * 14 / 100), alpha: 42);
        r.DrawCircle((220, 180, 100), (catCx - s * 2 / 100, catCy - s * 2 / 100), Math.Max(5, s * 10 / 100), alpha: 18);

        // Head — forward-facing
        int headX = catCx + s * 16 / 100, headY = catCy - s * 8 / 100;
        r.DrawCircle((215, 175, 95), (headX, headY), Math.Max(5, s * 10 / 100), alpha: 48);
        // Snout
        r.DrawCircle((225, 185, 105), (headX + s * 4 / 100, headY + s * 2 / 100), Math.Max(3, s * 5 / 100), alpha: 30);

        // Ears — alert, forward
        DrawTriangle(r, headX - s * 4 / 100, headY - s * 16 / 100, s * 7 / 100, (200, 160, 80), 45);
        DrawTriangle(r, headX + s * 4 / 100, headY - s * 16 / 100, s * 7 / 100, (200, 160, 80), 45);
        DrawTriangle(r, headX - s * 3 / 100, headY - s * 13 / 100, s * 4 / 100, (230, 160, 140), 30);
        DrawTriangle(r, headX + s * 5 / 100, headY - s * 13 / 100, s * 4 / 100, (230, 160, 140), 30);

        // Eyes — determined
        r.DrawCircle((255, 255, 200), (headX, headY - s * 2 / 100), Math.Max(2, s * 3 / 100), alpha: 50);
        r.DrawCircle((0, 0, 0), (headX + 1, headY - s * 2 / 100), Math.Max(1, s * 2 / 100), alpha: 55);
        // Eye shine
        r.DrawCircle((255, 255, 255), (headX - 1, headY - s * 3 / 100), 1, alpha: 45);

        // Nose
        DrawTriangle(r, headX + s * 5 / 100, headY + s * 1 / 100, Math.Max(2, s * 2 / 100), (180, 100, 80), 45);

        // Legs in running stride — front and back pairs
        // Front legs — stretched forward
        r.DrawLine((190, 150, 70), (catCx + s * 10 / 100, catCy + s * 4 / 100), (catCx + s * 22 / 100, groundY - 2), width: 3, alpha: 45);
        r.DrawLine((190, 150, 70), (catCx + s * 6 / 100, catCy + s * 2 / 100), (catCx + s * 14 / 100, groundY - 2), width: 3, alpha: 42);
        // Back legs — pushed back
        r.DrawLine((190, 150, 70), (catCx - s * 8 / 100, catCy + s * 4 / 100), (catCx - s * 16 / 100, groundY - 2), width: 3, alpha: 40);
        r.DrawLine((190, 150, 70), (catCx - s * 4 / 100, catCy + s * 6 / 100), (catCx - s * 10 / 100, groundY - 2), width: 3, alpha: 38);
        // Paws
        r.DrawCircle((200, 160, 80), (catCx + s * 22 / 100, groundY - 2), Math.Max(2, s * 2 / 100), alpha: 35);
        r.DrawCircle((200, 160, 80), (catCx - s * 16 / 100, groundY - 2), Math.Max(2, s * 2 / 100), alpha: 32);

        // Tail — streaming behind with curve
        r.DrawLine((200, 160, 80), (catCx - s * 12 / 100, catCy - s * 4 / 100),
            (catCx - s * 24 / 100, catCy - s * 14 / 100), width: 3, alpha: 40);
        r.DrawLine((200, 160, 80), (catCx - s * 24 / 100, catCy - s * 14 / 100),
            (catCx - s * 28 / 100, catCy - s * 18 / 100), width: 2, alpha: 32);

        // Motion blur lines — vibrant
        for (int i = 0; i < 6; i++)
        {
            int ly = catCy - s * 10 / 100 + i * s * 5 / 100;
            int ll = s * (8 + i * 2) / 100;
            int lx = catCx - s * 30 / 100 - i * s * 2 / 100;
            var col = i % 2 == 0 ? (255, 220, 60) : (255, 180, 30);
            r.DrawLine(col, (lx, ly), (lx + ll, ly), width: 2, alpha: 24 - i * 3);
        }

        // Speed exclamation
        r.DrawText("!", headX + s * 8 / 100, headY - s * 8 / 100, Math.Max(8, s * 10 / 100), (255, 240, 80),
            bold: true, anchorX: "center", anchorY: "center", alpha: 40);
    }

    private static void DrawSKIP_Hourglass(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);
        int glW = s * 24 / 100, glH = s * 36 / 100;

        // Time distortion rings around hourglass
        for (int ring = 0; ring < 3; ring++)
        {
            int rr = glW + s * (8 + ring * 6) / 100;
            r.DrawCircle((220, 200, 80), (cx, cy), rr, width: 1, alpha: 10 - ring * 2);
        }

        // Frame — ornate top and bottom bars
        int barH = s * 5 / 100;
        // Top bar
        r.DrawRect((200, 170, 80), (cx - glW / 2 - 6, cy - glH - 1, glW + 12, barH), alpha: 60);
        r.DrawRect((240, 210, 120), (cx - glW / 2 - 5, cy - glH, glW + 10, 2), alpha: 30);
        // Bottom bar
        r.DrawRect((200, 170, 80), (cx - glW / 2 - 6, cy + glH - barH + 1, glW + 12, barH), alpha: 60);
        r.DrawRect((240, 210, 120), (cx - glW / 2 - 5, cy + glH - barH + 2, glW + 10, 2), alpha: 30);
        // Decorative knobs at corners
        r.DrawCircle((220, 190, 100), (cx - glW / 2 - 6, cy - glH + barH / 2), Math.Max(2, barH / 2), alpha: 45);
        r.DrawCircle((220, 190, 100), (cx + glW / 2 + 6, cy - glH + barH / 2), Math.Max(2, barH / 2), alpha: 45);
        r.DrawCircle((220, 190, 100), (cx - glW / 2 - 6, cy + glH - barH / 2), Math.Max(2, barH / 2), alpha: 45);
        r.DrawCircle((220, 190, 100), (cx + glW / 2 + 6, cy + glH - barH / 2), Math.Max(2, barH / 2), alpha: 45);

        // Glass body — top half (wider at top, narrow at middle)
        for (int row = 0; row < glH; row++)
        {
            float t = (float)row / glH;
            int rowW = (int)(glW * (1f - t * 0.88f));
            int a = (int)(16 + 14 * (1f - t));
            r.DrawRect((200, 220, 240), (cx - rowW / 2, cy - glH + barH + row, rowW, 1), alpha: a);
        }
        // Glass body — bottom half (narrow at middle, wider at bottom)
        for (int row = 0; row < glH; row++)
        {
            float t = (float)row / glH;
            int rowW = (int)(glW * (0.12f + t * 0.88f));
            int a = (int)(16 + 12 * t);
            r.DrawRect((200, 220, 240), (cx - rowW / 2, cy + row, rowW, 1), alpha: a);
        }
        // Glass outline
        r.DrawLine((160, 180, 200), (cx - glW / 2, cy - glH + barH), (cx - glW * 6 / 100 / 2, cy), width: 1, alpha: 25);
        r.DrawLine((160, 180, 200), (cx + glW / 2, cy - glH + barH), (cx + glW * 6 / 100 / 2, cy), width: 1, alpha: 25);
        r.DrawLine((160, 180, 200), (cx - glW * 6 / 100 / 2, cy), (cx - glW / 2, cy + glH - barH), width: 1, alpha: 25);
        r.DrawLine((160, 180, 200), (cx + glW * 6 / 100 / 2, cy), (cx + glW / 2, cy + glH - barH), width: 1, alpha: 25);

        // Sand in bottom — already fallen
        int sandH = glH * 55 / 100;
        for (int row = 0; row < sandH; row++)
        {
            float t = (float)(glH - sandH + row) / glH;
            int rowW = (int)(glW * (0.12f + t * 0.88f)) - 4;
            float sandT = (float)row / sandH;
            int rr = (int)(230 + 20 * sandT);
            int gg = (int)(190 + 10 * sandT);
            r.DrawRect((rr, gg, 50), (cx - rowW / 2, cy + glH - barH - sandH + row, rowW, 1), alpha: 40);
        }
        // Sand surface — slight curve
        int surfW = (int)(glW * 0.5f);
        r.DrawLine((250, 210, 70), (cx - surfW / 2, cy + glH - barH - sandH), (cx + surfW / 2, cy + glH - barH - sandH), width: 1, alpha: 28);

        // Sand in top — remaining pile
        int topSandH = glH * 20 / 100;
        for (int row = 0; row < topSandH; row++)
        {
            float t = (float)row / topSandH;
            int rowW = (int)(glW * 0.8f * (1f - t * 0.6f)) - 2;
            r.DrawRect((240, 200, 60), (cx - rowW / 2, cy - glH + barH + (glH - topSandH) + row, rowW, 1), alpha: 35);
        }

        // Falling sand stream — with particles
        r.DrawLine((240, 200, 60), (cx, cy - s * 6 / 100), (cx, cy + s * 6 / 100), width: 2, alpha: 50);
        // Individual sand grains
        for (int g = 0; g < 4; g++)
        {
            int gy = cy - s * 4 / 100 + g * s * 3 / 100;
            int gx = cx + (g % 2 == 0 ? -1 : 1);
            r.DrawCircle((250, 210, 70), (gx, gy), 1, alpha: 40);
        }

        // Glass reflection highlight
        r.DrawLine((255, 255, 255), (cx - glW / 3, cy - glH * 80 / 100), (cx - glW * 10 / 100, cy - glH * 30 / 100), width: 1, alpha: 18);
        r.DrawLine((255, 255, 255), (cx + glW / 4, cy + glH * 30 / 100), (cx + glW * 8 / 100, cy + glH * 70 / 100), width: 1, alpha: 14);

        // Time symbols at sides
        r.DrawText("⏳", cx + s * 24 / 100, cy - s * 8 / 100, Math.Max(6, s * 6 / 100), (220, 200, 80),
            anchorX: "center", anchorY: "center", alpha: 25);
    }

    private static void DrawSKIP_SpringBoard(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Base platform (ground)
        int groundY = cy + s * 32 / 100;
        r.DrawRect((100, 90, 70), (cx - s * 28 / 100, groundY, s * 56 / 100, s * 6 / 100), alpha: 50);
        r.DrawRect((130, 115, 85), (cx - s * 27 / 100, groundY + 1, s * 54 / 100, 2), alpha: 25);
        // Ground texture lines
        for (int i = 0; i < 5; i++)
            r.DrawRect((80, 70, 55), (cx - s * 20 / 100 + i * s * 10 / 100, groundY + s * 3 / 100, s * 3 / 100, 1), alpha: 15);

        // Spring — detailed coils with metallic look
        int springX = cx - s * 4 / 100, springBot = groundY - 2;
        int coilCount = 6, coilSpacing = s * 6 / 100;
        for (int coil = 0; coil < coilCount; coil++)
        {
            int coilY = springBot - coil * coilSpacing;
            int coilR = Math.Max(3, s * 6 / 100);
            // Shadow coil
            r.DrawCircle((120, 120, 140), (springX + 1, coilY + 1), coilR, width: 2, alpha: 30);
            // Main coil
            int g = 170 + coil * 10;
            r.DrawCircle((g, g, g + 20), (springX, coilY), coilR, width: 2, alpha: 55);
            // Highlight
            r.DrawCircle((230, 230, 245), (springX - 2, coilY - 1), Math.Max(2, s * 3 / 100), width: 1, alpha: 22);
        }
        // Spring connector bolt at bottom
        r.DrawCircle((160, 150, 130), (springX, springBot), Math.Max(2, s * 2 / 100), alpha: 50);

        // Launch platform at top of spring
        int platY = springBot - coilCount * coilSpacing - s * 3 / 100;
        int platW = s * 40 / 100;
        r.DrawRect((160, 140, 90), (cx - platW / 2, platY, platW, s * 5 / 100), alpha: 55);
        // Platform wood grain
        for (int i = 0; i < 4; i++)
            r.DrawLine((140, 120, 70), (cx - platW / 2 + 3, platY + 1 + i * s / 100), (cx + platW / 2 - 3, platY + 1 + i * s / 100), width: 1, alpha: 15);
        // Platform highlight
        r.DrawRect((200, 180, 120), (cx - platW / 2 + 2, platY + 1, platW - 4, 2), alpha: 25);
        // Platform bolt at spring connection
        r.DrawCircle((180, 170, 140), (springX, platY + s * 4 / 100), Math.Max(2, s * 2 / 100), alpha: 45);

        // Cat being launched — flying above
        int catY = cy - s * 26 / 100;
        int catX = cx + s * 4 / 100;
        // Cat body arc
        r.DrawCircle((210, 170, 90), (catX, catY + s * 2 / 100), Math.Max(3, s * 6 / 100), alpha: 50);
        // Cat head
        int headR = Math.Max(4, s * 7 / 100);
        r.DrawCircle((200, 160, 80), (catX, catY - s * 2 / 100), headR, alpha: 55);
        // Ears (alert/scared)
        DrawTriangle(r, (180, 140, 60), catX - s * 5 / 100, catY - s * 10 / 100,
                     catX - s * 2 / 100, catY - s * 5 / 100, catX - s * 6 / 100, catY - s * 4 / 100, 50);
        DrawTriangle(r, (180, 140, 60), catX + s * 5 / 100, catY - s * 10 / 100,
                     catX + s * 2 / 100, catY - s * 5 / 100, catX + s * 6 / 100, catY - s * 4 / 100, 50);
        // Inner ears
        DrawTriangle(r, (230, 170, 130), catX - s * 4 / 100, catY - s * 9 / 100,
                     catX - s * 2 / 100, catY - s * 6 / 100, catX - s * 5 / 100, catY - s * 5 / 100, 35);
        DrawTriangle(r, (230, 170, 130), catX + s * 4 / 100, catY - s * 9 / 100,
                     catX + s * 2 / 100, catY - s * 6 / 100, catX + s * 5 / 100, catY - s * 5 / 100, 35);
        // Wide eyes (0_0 scared expression)
        r.DrawCircle((255, 255, 255), (catX - s * 3 / 100, catY - s * 3 / 100), Math.Max(2, s * 3 / 100), alpha: 60);
        r.DrawCircle((255, 255, 255), (catX + s * 3 / 100, catY - s * 3 / 100), Math.Max(2, s * 3 / 100), alpha: 60);
        r.DrawCircle((40, 40, 40), (catX - s * 3 / 100, catY - s * 3 / 100), Math.Max(1, s * 15 / 1000), alpha: 60);
        r.DrawCircle((40, 40, 40), (catX + s * 3 / 100, catY - s * 3 / 100), Math.Max(1, s * 15 / 1000), alpha: 60);
        // Open mouth (surprised)
        r.DrawCircle((180, 80, 80), (catX, catY + s * 1 / 100), Math.Max(1, s * 15 / 1000), alpha: 45);
        // Paws stretched out
        r.DrawLine((200, 160, 80), (catX - s * 8 / 100, catY - s * 6 / 100), (catX - s * 14 / 100, catY - s * 10 / 100), width: 2, alpha: 45);
        r.DrawLine((200, 160, 80), (catX + s * 8 / 100, catY - s * 6 / 100), (catX + s * 14 / 100, catY - s * 10 / 100), width: 2, alpha: 45);
        // Tail trailing
        r.DrawLine((190, 150, 70), (catX, catY + s * 6 / 100), (catX - s * 6 / 100, catY + s * 12 / 100), width: 2, alpha: 40);
        r.DrawLine((190, 150, 70), (catX - s * 6 / 100, catY + s * 12 / 100), (catX - s * 3 / 100, catY + s * 16 / 100), width: 2, alpha: 35);

        // Upward motion blur lines
        for (int i = 0; i < 5; i++)
        {
            int lx = catX + s * (-6 + i * 3) / 100;
            int len = s * (10 + i * 2) / 100;
            r.DrawLine((255, 230, 80), (lx, catY + s * 10 / 100), (lx, catY + s * 10 / 100 + len), width: 1, alpha: 28 - i * 4);
        }

        // Burst effect at launch point
        for (int ray = 0; ray < 8; ray++)
        {
            double angle = ray * Math.PI / 4;
            int rx = (int)(springX + Math.Cos(angle) * s * 10 / 100);
            int ry = (int)(platY + Math.Sin(angle) * s * 8 / 100);
            r.DrawLine((255, 255, 150), (springX, platY), (rx, ry), width: 1, alpha: 18);
        }

        // "BOING!" text
        r.DrawText("BOING!", cx + s * 16 / 100, cy + s * 4 / 100, Math.Max(6, s * 7 / 100), (255, 200, 40),
            anchorX: "center", anchorY: "center", alpha: 40);
    }

    // ─── SHUFFLE ───────────────────────────────────────────────
    private static void DrawSHUF(Renderer r, int v, int x, int y, int w, int h, int cx, int cy)
    {
        switch (v)
        {
            case 0: DrawSHUF_Tornado(r, x, y, w, h, cx, cy); break;
            case 1: DrawSHUF_CircularArrows(r, x, y, w, h, cx, cy); break;
            case 2: DrawSHUF_FlyingCards(r, x, y, w, h, cx, cy); break;
            case 3: DrawSHUF_ChaosDice(r, x, y, w, h, cx, cy); break;
        }
    }

    private static void DrawSHUF_Tornado(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Ground scatter — dust cloud at base
        r.DrawCircle((130, 110, 80), (cx, cy + s * 32 / 100), s * 28 / 100, alpha: 12);
        r.DrawCircle((150, 130, 100), (cx - s * 8 / 100, cy + s * 34 / 100), s * 16 / 100, alpha: 10);
        r.DrawCircle((150, 130, 100), (cx + s * 10 / 100, cy + s * 34 / 100), s * 14 / 100, alpha: 10);

        // Tornado funnel — layered ellipses widening toward bottom
        for (int row = 0; row < 16; row++)
        {
            float t = row / 15f;
            int rowR = (int)(s * 3 / 100 + t * s * 28 / 100);
            int rowY = cy - s * 34 / 100 + (int)(t * s * 62 / 100);
            float wobble = (float)Math.Sin(t * 8 + row * 0.7) * s * 3 / 100;
            int rowX = cx + (int)wobble;

            // Back layer — darker
            int bVal = (int)(70 + t * 30);
            r.DrawCircle((bVal, bVal + 40, bVal + 80), (rowX, rowY), rowR, width: 2, alpha: 40 - (int)(t * 18));
            // Front layer — lighter, offset slightly
            int fVal = (int)(100 + t * 20);
            r.DrawCircle((fVal, fVal + 50, fVal + 100), (rowX + 2, rowY), rowR - 2, width: 1, alpha: 32 - (int)(t * 14));
        }

        // Streaks inside funnel for rotation feel
        for (int streak = 0; streak < 6; streak++)
        {
            float st = streak / 5f;
            float angle = st * 3.14f * 1.5f;
            int sR = (int)(s * 6 / 100 + st * s * 18 / 100);
            int sx1 = cx + (int)(Math.Cos(angle) * sR * 0.6f);
            int sy1 = cy - s * 30 / 100 + (int)(st * s * 50 / 100);
            int sx2 = cx + (int)(Math.Cos(angle + 0.6) * sR);
            int sy2 = sy1 + s * 6 / 100;
            r.DrawLine((160, 200, 255), (sx1, sy1), (sx2, sy2), width: 1, alpha: 22 - streak * 2);
        }

        // Flying debris — cards, objects
        (int dx, int dy, int dw, int dh, (int, int, int) col)[] debris = [
            (-s * 22 / 100, -s * 8 / 100, s * 5 / 100, s * 7 / 100, (240, 200, 60)),   // card
            (s * 18 / 100, -s * 16 / 100, s * 4 / 100, s * 3 / 100, (200, 80, 80)),     // red object
            (-s * 10 / 100, s * 6 / 100, s * 3 / 100, s * 3 / 100, (80, 200, 120)),      // green object
            (s * 8 / 100, s * 18 / 100, s * 6 / 100, s * 4 / 100, (180, 100, 220)),       // purple object
            (-s * 28 / 100, s * 14 / 100, s * 4 / 100, s * 5 / 100, (240, 160, 40)),      // yellow card
        ];
        foreach (var (dx, dy, dw, dh, col) in debris)
        {
            r.DrawRect(col, (cx + dx, cy + dy, Math.Max(2, dw), Math.Max(2, dh)), alpha: 40);
            r.DrawRect((0, 0, 0), (cx + dx, cy + dy, Math.Max(2, dw), Math.Max(2, dh)), width: 1, alpha: 20);
        }

        // Small flying dots/particles
        for (int p = 0; p < 8; p++)
        {
            double ang = p * 0.85 + 0.3;
            float dist = 0.3f + p * 0.08f;
            int px = cx + (int)(Math.Cos(ang) * s * dist * 30 / 100);
            int py = cy - s * 6 / 100 + (int)(dist * s * 26 / 100);
            r.DrawCircle((180, 160, 120), (px, py), Math.Max(1, s * 1 / 100), alpha: 35);
        }

        // Vortex eye at top — small bright circle
        r.DrawCircle((200, 230, 255), (cx, cy - s * 32 / 100), Math.Max(2, s * 4 / 100), alpha: 20);
        r.DrawCircle((255, 255, 255), (cx, cy - s * 32 / 100), Math.Max(1, s * 2 / 100), alpha: 15);
    }

    private static void DrawSHUF_CircularArrows(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);
        int arrowR = s * 26 / 100;

        // Background energy ring
        r.DrawCircle((60, 130, 220), (cx, cy), arrowR + s * 6 / 100, width: 1, alpha: 10);
        r.DrawCircle((80, 150, 240), (cx, cy), arrowR + s * 3 / 100, width: 1, alpha: 8);

        // Two curved arrows forming a circle — thick and colorful
        for (int a = 0; a < 2; a++)
        {
            double offset = a * Math.PI;
            var mainCol = a == 0 ? (80, 180, 255) : (100, 220, 160);
            var darkCol = a == 0 ? (40, 120, 200) : (50, 160, 100);
            var lightCol = a == 0 ? (140, 210, 255) : (150, 240, 200);

            // Shadow arc
            for (double ang = 0; ang < Math.PI * 0.78; ang += 0.06)
            {
                double realAng = ang + offset;
                int ax = cx + (int)(Math.Cos(realAng) * arrowR) + 2;
                int ay = cy + (int)(Math.Sin(realAng) * arrowR) + 2;
                r.DrawCircle(darkCol, (ax, ay), Math.Max(3, s * 4 / 100), alpha: 20);
            }
            // Main arc — thick
            for (double ang = 0; ang < Math.PI * 0.78; ang += 0.06)
            {
                double realAng = ang + offset;
                int ax = cx + (int)(Math.Cos(realAng) * arrowR);
                int ay = cy + (int)(Math.Sin(realAng) * arrowR);
                r.DrawCircle(mainCol, (ax, ay), Math.Max(3, s * 4 / 100), alpha: 48);
            }
            // Highlight arc — inner edge
            for (double ang = 0.1; ang < Math.PI * 0.7; ang += 0.1)
            {
                double realAng = ang + offset;
                int ax = cx + (int)(Math.Cos(realAng) * (arrowR - s * 2 / 100));
                int ay = cy + (int)(Math.Sin(realAng) * (arrowR - s * 2 / 100));
                r.DrawCircle(lightCol, (ax, ay), Math.Max(1, s * 15 / 1000), alpha: 22);
            }

            // Arrow head at end — proper triangle
            double endAng = Math.PI * 0.78 + offset;
            int ex = cx + (int)(Math.Cos(endAng) * arrowR);
            int ey = cy + (int)(Math.Sin(endAng) * arrowR);
            // Find perpendicular direction for arrow width
            double tangent = endAng + Math.PI / 2;
            int tipX = ex + (int)(Math.Cos(endAng) * s * 8 / 100);
            int tipY = ey + (int)(Math.Sin(endAng) * s * 8 / 100);
            int baseAX = ex + (int)(Math.Cos(tangent) * s * 6 / 100);
            int baseAY = ey + (int)(Math.Sin(tangent) * s * 6 / 100);
            int baseBX = ex - (int)(Math.Cos(tangent) * s * 6 / 100);
            int baseBY = ey - (int)(Math.Sin(tangent) * s * 6 / 100);
            DrawTriangle(r, mainCol, tipX, tipY, baseAX, baseAY, baseBX, baseBY, 50);
            // Arrowhead outline
            r.DrawLine(darkCol, (tipX, tipY), (baseAX, baseAY), width: 1, alpha: 30);
            r.DrawLine(darkCol, (tipX, tipY), (baseBX, baseBY), width: 1, alpha: 30);
        }

        // Center — shuffle icon (two crossing lines)
        r.DrawCircle((100, 180, 255), (cx, cy), s * 8 / 100, alpha: 20);
        r.DrawLine((200, 220, 255), (cx - s * 4 / 100, cy - s * 3 / 100), (cx + s * 4 / 100, cy + s * 3 / 100), width: 2, alpha: 35);
        r.DrawLine((200, 220, 255), (cx - s * 4 / 100, cy + s * 3 / 100), (cx + s * 4 / 100, cy - s * 3 / 100), width: 2, alpha: 35);

        // Sparkle particles orbiting
        for (int sp = 0; sp < 5; sp++)
        {
            double spAng = sp * Math.PI * 2 / 5 + 0.3;
            int spX = cx + (int)(Math.Cos(spAng) * (arrowR + s * 8 / 100));
            int spY = cy + (int)(Math.Sin(spAng) * (arrowR + s * 8 / 100));
            r.DrawCircle((255, 255, 200), (spX, spY), Math.Max(1, s * 1 / 100), alpha: 30);
        }
    }

    private static void DrawSHUF_FlyingCards(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Wind swirl background effect
        for (int ring = 0; ring < 3; ring++)
        {
            int rr = s * (18 + ring * 10) / 100;
            r.DrawCircle((120, 180, 240), (cx + ring * 3, cy - ring * 2), rr, width: 1, alpha: 12 - ring * 3);
        }

        // Wind streak lines
        for (int wl = 0; wl < 6; wl++)
        {
            int wy = y + h * (15 + wl * 13) / 100;
            int wLen = s * (20 + wl * 4) / 100;
            int wx = cx - wLen / 2 + (wl % 2 == 0 ? -s * 6 / 100 : s * 4 / 100);
            r.DrawLine((160, 200, 240), (wx, wy), (wx + wLen, wy - 2), width: 1, alpha: 14 - wl);
        }

        // Multiple small cards scattered/flying around center
        (int ox, int oy, (int, int, int) face, (int, int, int) back)[] cards = [
            (-s * 20 / 100, -s * 16 / 100, (240, 60, 80), (30, 22, 50)),     // red card
            (s * 16 / 100,  -s * 10 / 100, (60, 180, 80), (30, 22, 50)),      // green card
            (-s * 10 / 100, s * 10 / 100,  (60, 120, 240), (30, 22, 50)),     // blue card
            (s * 22 / 100,  s * 14 / 100,  (240, 200, 60), (30, 22, 50)),     // yellow card
            (0,             -s * 24 / 100, (200, 100, 240), (30, 22, 50)),     // purple card
            (-s * 24 / 100, s * 4 / 100,   (240, 160, 40), (30, 22, 50)),     // orange card
        ];

        int cIdx = 0;
        foreach (var (ox, oy, face, back) in cards)
        {
            cIdx++;
            int crdW = Math.Max(4, s * 14 / 100), crdH = Math.Max(6, s * 19 / 100);
            int crdX = cx + ox - crdW / 2, crdY = cy + oy - crdH / 2;

            // Card shadow
            r.DrawRect((0, 0, 0), (crdX + 2, crdY + 2, crdW, crdH), alpha: 25);

            if (cIdx % 2 == 0)
            {
                // Show face side — colored face
                r.DrawRect(face, (crdX, crdY, crdW, crdH), alpha: 55);
                // White border
                r.DrawRect((255, 255, 255), (crdX, crdY, crdW, crdH), width: 1, alpha: 40);
                // Small EK symbol — circle on face
                r.DrawCircle((255, 255, 255), (crdX + crdW / 2, crdY + crdH / 2), Math.Max(1, crdW / 4), alpha: 30);
            }
            else
            {
                // Show back side — dark with cross pattern
                r.DrawRect(back, (crdX, crdY, crdW, crdH), alpha: 60);
                r.DrawRect((220, 160, 40), (crdX, crdY, crdW, crdH), width: 1, alpha: 50);
                r.DrawLine((200, 140, 30), (crdX + 2, crdY + 2), (crdX + crdW - 2, crdY + crdH - 2), width: 1, alpha: 25);
                r.DrawLine((200, 140, 30), (crdX + crdW - 2, crdY + 2), (crdX + 2, crdY + crdH - 2), width: 1, alpha: 25);
                // Diamond pattern at center
                int dmx = crdX + crdW / 2, dmy = crdY + crdH / 2;
                int dmr = Math.Max(1, crdW / 5);
                r.DrawLine((220, 180, 60), (dmx, dmy - dmr), (dmx + dmr, dmy), width: 1, alpha: 25);
                r.DrawLine((220, 180, 60), (dmx + dmr, dmy), (dmx, dmy + dmr), width: 1, alpha: 25);
                r.DrawLine((220, 180, 60), (dmx, dmy + dmr), (dmx - dmr, dmy), width: 1, alpha: 25);
                r.DrawLine((220, 180, 60), (dmx - dmr, dmy), (dmx, dmy - dmr), width: 1, alpha: 25);
            }

            // Motion trail behind each card
            r.DrawLine((200, 200, 220), (crdX + crdW, crdY + crdH / 2), (crdX + crdW + s * 5 / 100, crdY + crdH / 2 + 2), width: 1, alpha: 18);
        }

        // Center burst — where cards are exploding from
        for (int ray = 0; ray < 8; ray++)
        {
            double angle = ray * Math.PI / 4 + 0.2;
            int rx = cx + (int)(Math.Cos(angle) * s * 6 / 100);
            int ry = cy + (int)(Math.Sin(angle) * s * 6 / 100);
            r.DrawLine((255, 240, 180), (cx, cy), (rx, ry), width: 1, alpha: 16);
        }
        r.DrawCircle((255, 255, 200), (cx, cy), Math.Max(2, s * 3 / 100), alpha: 18);
    }

    private static void DrawSHUF_ChaosDice(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Background chaos — swirl lines
        for (int sw = 0; sw < 4; sw++)
        {
            double ang = sw * Math.PI / 2 + 0.5;
            int srr = s * (20 + sw * 5) / 100;
            int swx = cx + (int)(Math.Cos(ang) * srr / 3);
            int swy = cy + (int)(Math.Sin(ang) * srr / 3);
            r.DrawCircle((100, 80, 180), (swx, swy), srr, width: 1, alpha: 8);
        }

        // Multiple dice tumbling with 3D-ish faces
        (int ox, int oy, int sz, int face, (int, int, int) col)[] dice = [
            (-s * 16 / 100, -s * 12 / 100, s * 18 / 100, 6, (240, 60, 60)),    // Red die - 6
            (s * 12 / 100, s * 8 / 100, s * 16 / 100, 3, (60, 120, 240)),       // Blue die - 3
            (s * 4 / 100, -s * 22 / 100, s * 14 / 100, 1, (60, 200, 80)),        // Green die - 1
            (-s * 12 / 100, s * 16 / 100, s * 12 / 100, 5, (240, 200, 40)),      // Yellow die - 5
        ];

        foreach (var (ox, oy, sz, face, col) in dice)
        {
            int dx = cx + ox, dy = cy + oy;
            int halfSz = sz / 2;

            // Die shadow
            r.DrawRect((0, 0, 0), (dx - halfSz + 3, dy - halfSz + 3, sz, sz), alpha: 30);

            // Die body — colored
            r.DrawRect(col, (dx - halfSz, dy - halfSz, sz, sz), alpha: 55);

            // 3D edge — right side darker
            int edgeW = Math.Max(1, sz / 6);
            r.DrawRect((col.Item1 / 2, col.Item2 / 2, col.Item3 / 2), (dx + halfSz - edgeW, dy - halfSz, edgeW, sz), alpha: 30);
            // 3D edge — bottom darker
            r.DrawRect((col.Item1 / 2, col.Item2 / 2, col.Item3 / 2), (dx - halfSz, dy + halfSz - edgeW, sz, edgeW), alpha: 25);
            // Highlight — top left
            r.DrawRect((255, 255, 255), (dx - halfSz + 2, dy - halfSz + 2, sz - 4, 2), alpha: 22);

            // Border
            r.DrawRect((255, 255, 255), (dx - halfSz, dy - halfSz, sz, sz), width: 1, alpha: 35);

            // Rounded corners (small rects to round the look)
            int cornerR = Math.Max(1, sz / 10);
            r.DrawCircle(col, (dx - halfSz + cornerR, dy - halfSz + cornerR), cornerR, alpha: 55);
            r.DrawCircle(col, (dx + halfSz - cornerR, dy - halfSz + cornerR), cornerR, alpha: 55);
            r.DrawCircle(col, (dx - halfSz + cornerR, dy + halfSz - cornerR), cornerR, alpha: 55);
            r.DrawCircle(col, (dx + halfSz - cornerR, dy + halfSz - cornerR), cornerR, alpha: 55);

            // Pips — white dots
            int pip = Math.Max(2, sz / 7);
            int inset = sz / 4;
            if (face == 1 || face == 3 || face == 5) // center pip
                r.DrawCircle((255, 255, 255), (dx, dy), pip, alpha: 55);
            if (face >= 2) // top-right, bottom-left
            {
                r.DrawCircle((255, 255, 255), (dx + inset, dy - inset), pip, alpha: 55);
                r.DrawCircle((255, 255, 255), (dx - inset, dy + inset), pip, alpha: 55);
            }
            if (face >= 4) // top-left, bottom-right
            {
                r.DrawCircle((255, 255, 255), (dx - inset, dy - inset), pip, alpha: 55);
                r.DrawCircle((255, 255, 255), (dx + inset, dy + inset), pip, alpha: 55);
            }
            if (face == 6) // middle row
            {
                r.DrawCircle((255, 255, 255), (dx - inset, dy), pip, alpha: 55);
                r.DrawCircle((255, 255, 255), (dx + inset, dy), pip, alpha: 55);
            }
        }

        // Motion arcs between dice
        r.DrawLine((200, 180, 255), (cx - s * 16 / 100, cy - s * 12 / 100), (cx + s * 4 / 100, cy - s * 22 / 100), width: 1, alpha: 15);
        r.DrawLine((200, 180, 255), (cx + s * 4 / 100, cy - s * 22 / 100), (cx + s * 12 / 100, cy + s * 8 / 100), width: 1, alpha: 15);
        r.DrawLine((200, 180, 255), (cx + s * 12 / 100, cy + s * 8 / 100), (cx - s * 12 / 100, cy + s * 16 / 100), width: 1, alpha: 15);

        // "?" symbol at center
        r.DrawText("?", cx, cy, Math.Max(8, s * 12 / 100), (255, 255, 255),
            anchorX: "center", anchorY: "center", alpha: 25);
    }

    // ─── SEE THE FUTURE ────────────────────────────────────────
    private static void DrawFUT(Renderer r, int v, int x, int y, int w, int h, int cx, int cy)
    {
        switch (v)
        {
            case 0: DrawFUT_CrystalBall(r, x, y, w, h, cx, cy); break;
            case 1: DrawFUT_ThirdEye(r, x, y, w, h, cx, cy); break;
            case 2: DrawFUT_Telescope(r, x, y, w, h, cx, cy); break;
            case 3: DrawFUT_Constellation(r, x, y, w, h, cx, cy); break;
        }
    }

    private static void DrawFUT_CrystalBall(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);
        int ballR = s * 26 / 100;
        int ballCy = cy - s * 4 / 100;

        // Deep mystical aura — layered halos
        r.DrawCircle((80, 30, 180), (cx, ballCy), ballR + s * 18 / 100, alpha: 6);
        r.DrawCircle((100, 50, 200), (cx, ballCy), ballR + s * 12 / 100, alpha: 10);
        r.DrawCircle((130, 70, 220), (cx, ballCy), ballR + s * 6 / 100, alpha: 14);

        // Ball glass — rich metallic gradient layers
        for (int i = ballR; i >= 0; i -= 2)
        {
            float t = (float)i / ballR;
            int blue = (int)(50 + 90 * t);
            int green = (int)(20 + 50 * t);
            int red = (int)(15 + 25 * t);
            r.DrawCircle((red, green, blue), (cx, ballCy), i, alpha: 40);
        }

        // Glass refraction highlights
        r.DrawCircle((180, 160, 240), (cx - ballR / 3, ballCy - ballR / 3), ballR / 4, alpha: 40);
        r.DrawCircle((220, 200, 255), (cx - ballR / 3, ballCy - ballR / 3), ballR / 6, alpha: 30);
        // Secondary highlight
        r.DrawCircle((160, 140, 220), (cx + ballR / 4, ballCy + ballR / 4), ballR / 5, alpha: 15);

        // Inner swirl energy — mystical patterns
        r.DrawCircle((160, 100, 255), (cx + s * 4 / 100, ballCy - s * 1 / 100), ballR * 45 / 100, width: 1, alpha: 30);
        r.DrawCircle((200, 140, 255), (cx - s * 3 / 100, ballCy + s * 2 / 100), ballR * 35 / 100, width: 1, alpha: 25);
        r.DrawCircle((180, 120, 255), (cx - s * 1 / 100, ballCy - s * 4 / 100), ballR * 25 / 100, width: 1, alpha: 28);

        // Inner sparks — three tiny stars
        for (int i = 0; i < 3; i++)
        {
            int sx = cx + (int)(MathF.Cos(i * 2.1f) * ballR * 0.4f);
            int sy = ballCy + (int)(MathF.Sin(i * 2.1f) * ballR * 0.35f);
            r.DrawCircle((220, 200, 255), (sx, sy), 2, alpha: 45);
            // Tiny cross on each spark
            r.DrawRect((220, 200, 255), (sx - 3, sy, 7, 1), alpha: 25);
            r.DrawRect((220, 200, 255), (sx, sy - 3, 1, 7), alpha: 25);
        }

        // Base/stand — ornate metallic
        int baseW = ballR * 130 / 100, baseH = s * 10 / 100;
        int baseY = ballCy + ballR - 3;
        // Stand shadow
        r.DrawRect((0, 0, 0), (cx - baseW / 2 + 2, baseY + 2, baseW, baseH), alpha: 35);
        // Main base
        r.DrawRect((80, 60, 40), (cx - baseW / 2, baseY, baseW, baseH), alpha: 65);
        // Metallic bands
        r.DrawRect((120, 100, 60), (cx - baseW / 2 + 2, baseY + 2, baseW - 4, 2), alpha: 35);
        r.DrawRect((100, 80, 50), (cx - baseW / 2 + 3, baseY + baseH - 3, baseW - 6, 2), alpha: 25);
        // Rim at junction
        r.DrawRect((110, 90, 55), (cx - ballR * 55 / 100, baseY - 3, ballR * 110 / 100, 5), alpha: 55);

        // Floating rune symbols around ball
        for (int i = 0; i < 4; i++)
        {
            double ang = i * Math.PI / 2 + Math.PI / 4;
            int rx = cx + (int)(Math.Cos(ang) * (ballR + s * 8 / 100));
            int ry = ballCy + (int)(Math.Sin(ang) * (ballR + s * 6 / 100));
            r.DrawCircle((160, 100, 240), (rx, ry), 2, alpha: 30);
            r.DrawRect((160, 100, 240), (rx - 3, ry - 1, 7, 1), alpha: 18);
        }
    }

    private static void DrawFUT_ThirdEye(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Cosmic background — concentric mystical rings
        r.DrawCircle((80, 40, 160), (cx, cy), s * 40 / 100, alpha: 8);
        r.DrawCircle((100, 50, 180), (cx, cy), s * 34 / 100, alpha: 10);
        r.DrawCircle((120, 60, 200), (cx, cy), s * 28 / 100, alpha: 12);

        // Radiant lines from eye — longer, more colorful
        for (int i = 0; i < 12; i++)
        {
            double ang = i * Math.PI / 6;
            int innerR = s * 18 / 100;
            int outerR = s * 38 / 100;
            int ex1 = cx + (int)(Math.Cos(ang) * innerR);
            int ey1 = cy + (int)(Math.Sin(ang) * innerR);
            int ex2 = cx + (int)(Math.Cos(ang) * outerR);
            int ey2 = cy + (int)(Math.Sin(ang) * outerR);
            var rayCol = i % 3 == 0 ? (180, 120, 255) : i % 3 == 1 ? (120, 80, 220) : (200, 160, 255);
            r.DrawLine(rayCol, (ex1, ey1), (ex2, ey2), width: 1, alpha: 16 - i % 4);
        }

        // Eye shape — almond formed by converging curves
        int eyeW = s * 32 / 100, eyeH = s * 16 / 100;
        // Fill eye shape — row by row
        for (int row = -eyeH; row <= eyeH; row++)
        {
            float t = Math.Abs((float)row / eyeH);
            int rowW = (int)(eyeW * (1f - t * t));
            if (rowW < 1) continue;
            int rr = (int)(230 + 20 * (1 - t));
            int gg = (int)(220 + 30 * (1 - t));
            int bb = (int)(240 + 10 * (1 - t));
            r.DrawRect((rr, gg, bb), (cx - rowW, cy + row, rowW * 2, 1), alpha: 14);
        }

        // Eye outline — top and bottom lids
        // Upper lid
        for (double ang = -0.85; ang <= 0.85; ang += 0.04)
        {
            float norm = (float)Math.Abs(ang / 0.85);
            int px = cx + (int)(ang / 0.85 * eyeW);
            int py = cy - (int)((1 - norm * norm) * eyeH);
            r.DrawCircle((100, 50, 180), (px, py), 1, alpha: 40);
        }
        // Lower lid
        for (double ang = -0.85; ang <= 0.85; ang += 0.04)
        {
            float norm = (float)Math.Abs(ang / 0.85);
            int px = cx + (int)(ang / 0.85 * eyeW);
            int py = cy + (int)((1 - norm * norm) * eyeH);
            r.DrawCircle((100, 50, 180), (px, py), 1, alpha: 40);
        }

        // Eyelashes — top
        for (int el = 0; el < 5; el++)
        {
            float t = (el + 1) / 6f;
            int lx = cx + (int)((t * 2 - 1) * eyeW * 0.8f);
            float norm = Math.Abs(t * 2 - 1);
            int ly = cy - (int)((1 - norm * norm) * eyeH);
            int lLen = s * 4 / 100;
            r.DrawLine((80, 40, 160), (lx, ly), (lx + (int)((t - 0.5f) * lLen), ly - lLen), width: 1, alpha: 30);
        }

        // Iris — rich multi-layered
        int irisR = s * 12 / 100;
        r.DrawCircle((60, 20, 160), (cx, cy), irisR, alpha: 55);
        // Iris color rings
        r.DrawCircle((80, 40, 180), (cx, cy), irisR * 9 / 10, alpha: 20);
        r.DrawCircle((100, 60, 200), (cx, cy), irisR * 7 / 10, alpha: 22);
        r.DrawCircle((140, 80, 220), (cx, cy), irisR * 5 / 10, alpha: 25);
        // Iris texture — radial lines
        for (int il = 0; il < 12; il++)
        {
            double iang = il * Math.PI / 6;
            int ix = cx + (int)(Math.Cos(iang) * irisR * 4 / 10);
            int iy = cy + (int)(Math.Sin(iang) * irisR * 4 / 10);
            int ox = cx + (int)(Math.Cos(iang) * irisR * 9 / 10);
            int oy = cy + (int)(Math.Sin(iang) * irisR * 9 / 10);
            r.DrawLine((120, 70, 200), (ix, iy), (ox, oy), width: 1, alpha: 18);
        }

        // Pupil — deep black with cat slit
        r.DrawCircle((10, 5, 30), (cx, cy), s * 5 / 100, alpha: 60);
        // Cat-slit pupil (vertical line)
        r.DrawLine((5, 2, 20), (cx, cy - s * 6 / 100), (cx, cy + s * 6 / 100), width: 2, alpha: 55);

        // Pupil highlights
        r.DrawCircle((220, 200, 255), (cx - s * 2 / 100, cy - s * 3 / 100), Math.Max(1, s * 15 / 1000 + 1), alpha: 55);
        r.DrawCircle((200, 180, 240), (cx + s * 1 / 100, cy + s * 2 / 100), Math.Max(1, s * 1 / 100), alpha: 35);

        // Mystical floating symbols around the eye
        r.DrawText("✦", cx - s * 26 / 100, cy - s * 20 / 100, Math.Max(6, s * 5 / 100), (180, 140, 255),
            anchorX: "center", anchorY: "center", alpha: 25);
        r.DrawText("✧", cx + s * 28 / 100, cy + s * 14 / 100, Math.Max(6, s * 5 / 100), (180, 140, 255),
            anchorX: "center", anchorY: "center", alpha: 22);
    }

    private static void DrawFUT_Telescope(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Night sky background — dark gradient effect
        for (int band = 0; band < 5; band++)
        {
            int bandY = y + band * h / 5;
            int bv = 15 + band * 5;
            r.DrawRect((bv, bv / 2, bv * 2), (x, bandY, w, h / 5), alpha: 8);
        }

        // Stars in background — various sizes and colors
        (int ox, int oy, int sz, (int, int, int) col)[] stars = [
            (-s * 25 / 100, -s * 24 / 100, 3, (255, 255, 220)),
            (s * 20 / 100,  -s * 30 / 100, 2, (220, 220, 255)),
            (-s * 32 / 100, s * 2 / 100,   2, (255, 220, 200)),
            (s * 30 / 100,  -s * 10 / 100, 3, (200, 240, 255)),
            (0,             -s * 34 / 100, 2, (255, 255, 200)),
            (s * 16 / 100,  -s * 20 / 100, 2, (240, 220, 255)),
            (-s * 14 / 100, -s * 30 / 100, 2, (255, 240, 200)),
            (s * 26 / 100,  -s * 24 / 100, 1, (200, 220, 255)),
        ];
        foreach (var (ox, oy, sz, col) in stars)
        {
            r.DrawCircle(col, (cx + ox, cy + oy), sz, alpha: 45);
            // Star twinkle cross
            r.DrawLine(col, (cx + ox - sz - 1, cy + oy), (cx + ox + sz + 1, cy + oy), width: 1, alpha: 25);
            r.DrawLine(col, (cx + ox, cy + oy - sz - 1), (cx + ox, cy + oy + sz + 1), width: 1, alpha: 25);
        }

        // Moon — crescent in upper corner
        int moonX = cx + s * 24 / 100, moonY = cy - s * 26 / 100;
        int moonR = Math.Max(3, s * 7 / 100);
        r.DrawCircle((240, 230, 200), (moonX, moonY), moonR, alpha: 40);
        r.DrawCircle((240, 235, 210), (moonX - 1, moonY - 1), moonR - 1, alpha: 20);
        // Dark circle to create crescent effect
        r.DrawCircle((30, 20, 60), (moonX + moonR / 2, moonY - moonR / 3), moonR - 1, alpha: 35);

        // Telescope — more detailed
        int fromX = cx - s * 8 / 100, fromY = cy + s * 24 / 100;
        int toX = cx + s * 18 / 100, toY = cy - s * 16 / 100;

        // Tripod legs — three legs
        int legBot = cy + s * 36 / 100;
        r.DrawLine((90, 80, 65), (fromX, fromY), (fromX - s * 16 / 100, legBot), width: 2, alpha: 55);
        r.DrawLine((90, 80, 65), (fromX, fromY), (fromX + s * 16 / 100, legBot), width: 2, alpha: 55);
        r.DrawLine((90, 80, 65), (fromX, fromY), (fromX + s * 2 / 100, legBot + s * 2 / 100), width: 2, alpha: 45);
        // Tripod joint
        r.DrawCircle((120, 110, 90), (fromX, fromY), Math.Max(2, s * 3 / 100), alpha: 50);

        // Telescope body shadow
        r.DrawLine((0, 0, 0), (fromX + 3, fromY + 3), (toX + 3, toY + 3), width: 10, alpha: 25);
        // Telescope body — gradient tube
        r.DrawLine((120, 100, 85), (fromX, fromY), (toX, toY), width: 9, alpha: 60);
        r.DrawLine((150, 130, 110), (fromX, fromY), (toX, toY), width: 6, alpha: 35);
        r.DrawLine((180, 160, 140), (fromX + 1, fromY - 1), (toX + 1, toY - 1), width: 3, alpha: 22);

        // Metallic bands on tube
        for (int band = 1; band <= 3; band++)
        {
            float bt = band / 4f;
            int bx = fromX + (int)((toX - fromX) * bt);
            int by = fromY + (int)((toY - fromY) * bt);
            r.DrawCircle((200, 180, 140), (bx, by), Math.Max(2, s * 2 / 100), width: 2, alpha: 30);
        }

        // Lens at front — larger, more detail
        int lensR = Math.Max(4, s * 7 / 100);
        r.DrawCircle((80, 100, 160), (toX, toY), lensR, alpha: 50);
        r.DrawCircle((100, 130, 200), (toX, toY), lensR - 2, alpha: 30);
        r.DrawCircle((140, 170, 240), (toX - 2, toY - 2), lensR / 2, alpha: 25);
        // Lens ring
        r.DrawCircle((180, 170, 140), (toX, toY), lensR, width: 2, alpha: 40);
        // Lens flare — cross
        r.DrawLine((200, 210, 255), (toX - s * 5 / 100, toY - s * 5 / 100),
            (toX + s * 5 / 100, toY + s * 5 / 100), width: 1, alpha: 22);
        r.DrawLine((200, 210, 255), (toX + s * 5 / 100, toY - s * 5 / 100),
            (toX - s * 5 / 100, toY + s * 5 / 100), width: 1, alpha: 18);

        // Eyepiece at back
        int epR = Math.Max(2, s * 3 / 100);
        r.DrawCircle((100, 90, 80), (fromX - s * 2 / 100, fromY + s * 2 / 100), epR, alpha: 50);
        r.DrawCircle((140, 130, 110), (fromX - s * 2 / 100, fromY + s * 2 / 100), epR - 1, alpha: 25);
    }

    private static void DrawFUT_Constellation(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Deep space background glow
        r.DrawCircle((20, 10, 60), (cx, cy), s * 42 / 100, alpha: 12);
        r.DrawCircle((40, 20, 80), (cx, cy), s * 34 / 100, alpha: 14);

        // Tiny background stars (not part of constellation)
        (int ox, int oy)[] bgStars = [
            (-s * 34 / 100, -s * 28 / 100), (s * 32 / 100, -s * 32 / 100),
            (-s * 30 / 100, s * 22 / 100),  (s * 28 / 100, s * 26 / 100),
            (s * 36 / 100, s * 2 / 100),    (-s * 36 / 100, -s * 6 / 100),
            (s * 10 / 100, s * 32 / 100),   (-s * 18 / 100, s * 30 / 100),
        ];
        foreach (var (ox, oy) in bgStars)
            r.DrawCircle((180, 180, 220), (cx + ox, cy + oy), 1, alpha: 30);

        // Cat constellation star positions — proper cat face shape
        (int x, int y)[] starPos = [
            (cx - s * 24 / 100, cy - s * 20 / 100),     // 0: left ear tip
            (cx - s * 16 / 100, cy - s * 10 / 100),     // 1: left ear base
            (cx + s * 16 / 100, cy - s * 10 / 100),     // 2: right ear base
            (cx + s * 24 / 100, cy - s * 20 / 100),     // 3: right ear tip
            (cx - s * 20 / 100, cy + s * 4 / 100),      // 4: left cheek
            (cx + s * 20 / 100, cy + s * 4 / 100),      // 5: right cheek
            (cx, cy + s * 18 / 100),                      // 6: chin
            (cx - s * 8 / 100, cy - s * 2 / 100),       // 7: left eye
            (cx + s * 8 / 100, cy - s * 2 / 100),       // 8: right eye
            (cx, cy + s * 6 / 100),                       // 9: nose
        ];

        // Constellation lines — cat outline
        (int, int)[] connections = [
            (0, 1), (1, 4), (4, 6), (6, 5), (5, 2), (2, 3),  // outline
            (1, 2),   // forehead
            (1, 7), (2, 8),  // eyes connect to frame
            (7, 9), (8, 9),  // nose triangle
        ];
        foreach (var (a, b) in connections)
        {
            // Double line for glow effect
            r.DrawLine((80, 60, 180), starPos[a], starPos[b], width: 2, alpha: 14);
            r.DrawLine((140, 120, 220), starPos[a], starPos[b], width: 1, alpha: 25);
        }

        // Whisker lines from nose
        r.DrawLine((140, 120, 220), starPos[9], (cx + s * 30 / 100, cy + s * 2 / 100), width: 1, alpha: 16);
        r.DrawLine((140, 120, 220), starPos[9], (cx + s * 28 / 100, cy + s * 10 / 100), width: 1, alpha: 14);
        r.DrawLine((140, 120, 220), starPos[9], (cx - s * 30 / 100, cy + s * 2 / 100), width: 1, alpha: 16);
        r.DrawLine((140, 120, 220), starPos[9], (cx - s * 28 / 100, cy + s * 10 / 100), width: 1, alpha: 14);

        // Stars with multi-layer glow
        int sIdx = 0;
        foreach (var (sx, sy) in starPos)
        {
            // Outer glow
            int gr = sIdx < 4 || sIdx == 6 ? s * 5 / 100 : s * 4 / 100;
            r.DrawCircle((100, 80, 200), (sx, sy), Math.Max(3, gr), alpha: 16);
            // Mid glow
            r.DrawCircle((160, 140, 240), (sx, sy), Math.Max(2, gr * 6 / 10), alpha: 35);
            // Core star
            r.DrawCircle((240, 220, 255), (sx, sy), Math.Max(1, gr * 3 / 10), alpha: 55);
            // Twinkle cross on main stars
            if (sIdx < 4 || sIdx == 6 || sIdx == 9)
            {
                int tLen = gr + 2;
                r.DrawLine((200, 190, 255), (sx - tLen, sy), (sx + tLen, sy), width: 1, alpha: 22);
                r.DrawLine((200, 190, 255), (sx, sy - tLen), (sx, sy + tLen), width: 1, alpha: 22);
            }
            sIdx++;
        }

        // Eye stars — make them slightly blue/green for character
        r.DrawCircle((100, 220, 200), starPos[7], Math.Max(2, s * 3 / 100), alpha: 30);
        r.DrawCircle((100, 220, 200), starPos[8], Math.Max(2, s * 3 / 100), alpha: 30);

        // Nebula wisps
        r.DrawCircle((80, 40, 140), (cx - s * 10 / 100, cy + s * 24 / 100), s * 12 / 100, alpha: 6);
        r.DrawCircle((60, 30, 120), (cx + s * 16 / 100, cy - s * 28 / 100), s * 10 / 100, alpha: 5);
    }

    // ─── FAVOR ─────────────────────────────────────────────────
    private static void DrawFAV(Renderer r, int v, int x, int y, int w, int h, int cx, int cy)
    {
        switch (v)
        {
            case 0: DrawFAV_GiftBox(r, x, y, w, h, cx, cy); break;
            case 1: DrawFAV_Heart(r, x, y, w, h, cx, cy); break;
            case 2: DrawFAV_GoldCoin(r, x, y, w, h, cx, cy); break;
            case 3: DrawFAV_Handshake(r, x, y, w, h, cx, cy); break;
        }
    }

    private static void DrawFAV_GiftBox(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);
        int boxW = s * 44 / 100, boxH = s * 34 / 100;
        int bx = cx - boxW / 2, by = cy - boxH / 3;

        // Sparkles around box
        (int ox, int oy, int sz)[] sparkles = [
            (-s * 28 / 100, -s * 22 / 100, 2), (s * 30 / 100, -s * 18 / 100, 2),
            (-s * 24 / 100, s * 20 / 100, 2),  (s * 26 / 100, s * 22 / 100, 2),
            (s * 32 / 100, -s * 4 / 100, 1),   (-s * 30 / 100, s * 6 / 100, 1),
        ];
        foreach (var (ox, oy, sz) in sparkles)
        {
            int spx = cx + ox, spy = cy + oy;
            r.DrawCircle((255, 255, 200), (spx, spy), sz, alpha: 45);
            // Cross sparkle
            r.DrawLine((255, 255, 220), (spx - sz - 2, spy), (spx + sz + 2, spy), width: 1, alpha: 30);
            r.DrawLine((255, 255, 220), (spx, spy - sz - 2), (spx, spy + sz + 2), width: 1, alpha: 30);
        }

        // Box shadow
        r.DrawRect((0, 0, 0), (bx + 4, by + 4, boxW, boxH), alpha: 35);

        // Box body — rich red with gradient bands
        r.DrawRect((200, 60, 80), (bx, by, boxW, boxH), alpha: 65);
        for (int b = 0; b < 5; b++)
        {
            int bh = boxH / 5;
            int rr = 220 - b * 10;
            int gg = 80 - b * 8;
            r.DrawRect((rr, gg, 100), (bx + 2, by + b * bh, boxW - 4, bh), alpha: 18 - b * 2);
        }
        // Box outline
        r.DrawRect((160, 40, 60), (bx, by, boxW, boxH), width: 2, alpha: 50);

        // Lid (wider, gradient)
        int lidH = s * 9 / 100;
        r.DrawRect((220, 80, 110), (bx - 5, by - lidH, boxW + 10, lidH), alpha: 65);
        r.DrawRect((240, 110, 140), (bx - 4, by - lidH + 1, boxW + 8, 2), alpha: 30);
        r.DrawRect((180, 50, 80), (bx - 5, by - lidH, boxW + 10, lidH), width: 1, alpha: 50);

        // Ribbon — vertical and horizontal (golden)
        int ribW = Math.Max(3, s * 6 / 100);
        // Vertical ribbon
        r.DrawRect((255, 200, 60), (cx - ribW / 2, by - lidH, ribW, boxH + lidH), alpha: 42);
        r.DrawRect((255, 220, 100), (cx - ribW / 2 + 1, by - lidH, 2, boxH + lidH), alpha: 18);
        // Horizontal ribbon
        r.DrawRect((255, 200, 60), (bx, by + boxH / 2 - ribW / 2, boxW, ribW), alpha: 38);
        r.DrawRect((255, 220, 100), (bx, by + boxH / 2 - ribW / 2 + 1, boxW, 2), alpha: 15);

        // Bow at top — two loopy circles with center knot
        int bowR = Math.Max(4, s * 7 / 100);
        // Left loop
        r.DrawCircle((255, 180, 60), (cx - s * 7 / 100, by - lidH - s * 5 / 100), bowR, alpha: 48);
        r.DrawCircle((255, 210, 100), (cx - s * 7 / 100 - 1, by - lidH - s * 5 / 100 - 1), bowR - 2, alpha: 20);
        r.DrawCircle((200, 140, 30), (cx - s * 7 / 100, by - lidH - s * 5 / 100), bowR, width: 1, alpha: 30);
        // Right loop
        r.DrawCircle((255, 180, 60), (cx + s * 7 / 100, by - lidH - s * 5 / 100), bowR, alpha: 48);
        r.DrawCircle((255, 210, 100), (cx + s * 7 / 100 - 1, by - lidH - s * 5 / 100 - 1), bowR - 2, alpha: 20);
        r.DrawCircle((200, 140, 30), (cx + s * 7 / 100, by - lidH - s * 5 / 100), bowR, width: 1, alpha: 30);
        // Center knot
        r.DrawCircle((255, 200, 80), (cx, by - lidH - s * 3 / 100), Math.Max(2, s * 3 / 100), alpha: 45);
        // Ribbon tails hanging
        r.DrawLine((255, 190, 50), (cx - s * 2 / 100, by - lidH - s * 2 / 100), (cx - s * 8 / 100, by - lidH + s * 1 / 100), width: 2, alpha: 30);
        r.DrawLine((255, 190, 50), (cx + s * 2 / 100, by - lidH - s * 2 / 100), (cx + s * 8 / 100, by - lidH + s * 1 / 100), width: 2, alpha: 30);

        // Gift tag
        int tagX = bx + boxW - s * 4 / 100, tagY = by + s * 3 / 100;
        r.DrawRect((255, 255, 230), (tagX, tagY, s * 8 / 100, s * 5 / 100), alpha: 40);
        r.DrawCircle((255, 255, 230), (tagX + s * 4 / 100, tagY), Math.Max(1, s * 1 / 100), alpha: 35);
    }

    private static void DrawFAV_Heart(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Outer glow — multi-layer pink/red
        r.DrawCircle((255, 60, 100), (cx, cy), s * 38 / 100, alpha: 6);
        r.DrawCircle((255, 80, 140), (cx, cy), s * 34 / 100, alpha: 10);
        r.DrawCircle((255, 100, 160), (cx, cy), s * 28 / 100, alpha: 12);

        // Heart shape — bigger, more detailed
        int heartR = s * 17 / 100;
        // Left hump — gradient fill
        for (int layer = 0; layer < 3; layer++)
        {
            int lr = heartR - layer * 2;
            int rr = 240 - layer * 20;
            int gg = 40 + layer * 20;
            int bb = 100 + layer * 20;
            r.DrawCircle((rr, gg, bb), (cx - heartR * 68 / 100, cy - heartR * 28 / 100), lr, alpha: 48 - layer * 8);
        }
        // Right hump — gradient fill
        for (int layer = 0; layer < 3; layer++)
        {
            int lr = heartR - layer * 2;
            int rr = 240 - layer * 20;
            int gg = 40 + layer * 20;
            int bb = 100 + layer * 20;
            r.DrawCircle((rr, gg, bb), (cx + heartR * 68 / 100, cy - heartR * 28 / 100), lr, alpha: 48 - layer * 8);
        }
        // Center fill
        r.DrawCircle((230, 50, 110), (cx, cy - heartR * 18 / 100), heartR * 82 / 100, alpha: 50);

        // Bottom point — smooth narrowing
        for (int p = 0; p < 12; p++)
        {
            int pw = heartR * 2 * (12 - p) / 12;
            int py = cy + heartR * 18 / 100 + p * heartR * 10 / 100;
            int rr = 230 - p * 4;
            int gg = 50 + p * 2;
            r.DrawRect((rr, gg, 110), (cx - pw / 2, py, pw, heartR * 10 / 100 + 1), alpha: 48 - p * 3);
        }

        // Heart outline with darker border
        // Top curves
        r.DrawCircle((180, 20, 60), (cx - heartR * 68 / 100, cy - heartR * 28 / 100), heartR, width: 2, alpha: 30);
        r.DrawCircle((180, 20, 60), (cx + heartR * 68 / 100, cy - heartR * 28 / 100), heartR, width: 2, alpha: 30);

        // Specular highlight on left hump — larger, brighter
        r.DrawCircle((255, 180, 210), (cx - heartR, cy - heartR * 65 / 100), heartR / 3, alpha: 35);
        r.DrawCircle((255, 200, 230), (cx - heartR + 1, cy - heartR * 70 / 100), heartR / 5, alpha: 25);

        // Arrow through heart
        int arrowFromX = cx - s * 28 / 100, arrowFromY = cy + s * 8 / 100;
        int arrowToX = cx + s * 28 / 100, arrowToY = cy - s * 10 / 100;
        // Arrow shaft
        r.DrawLine((160, 120, 60), (arrowFromX, arrowFromY), (arrowToX, arrowToY), width: 2, alpha: 40);
        // Arrow head
        DrawTriangle(r, (120, 90, 40), arrowToX + s * 3 / 100, arrowToY - s * 2 / 100,
                     arrowToX, arrowToY, arrowToX, arrowToY - s * 3 / 100, 40);
        // Arrow fletching
        r.DrawLine((200, 60, 60), (arrowFromX, arrowFromY), (arrowFromX - s * 2 / 100, arrowFromY - s * 3 / 100), width: 1, alpha: 30);
        r.DrawLine((200, 60, 60), (arrowFromX, arrowFromY), (arrowFromX - s * 2 / 100, arrowFromY + s * 3 / 100), width: 1, alpha: 30);

        // Sparkle dots — more, various colors
        (int ox, int oy, (int, int, int) col)[] sparkDots = [
            (-s * 22 / 100, -s * 18 / 100, (255, 200, 230)),
            (s * 24 / 100, -s * 12 / 100, (255, 180, 220)),
            (s * 12 / 100, s * 24 / 100, (255, 220, 240)),
            (-s * 18 / 100, s * 18 / 100, (255, 200, 200)),
            (s * 28 / 100, s * 10 / 100, (255, 210, 230)),
        ];
        foreach (var (ox, oy, col) in sparkDots)
        {
            r.DrawCircle(col, (cx + ox, cy + oy), 2, alpha: 48);
            r.DrawLine(col, (cx + ox - 3, cy + oy), (cx + ox + 3, cy + oy), width: 1, alpha: 25);
            r.DrawLine(col, (cx + ox, cy + oy - 3), (cx + ox, cy + oy + 3), width: 1, alpha: 25);
        }
    }

    private static void DrawFAV_GoldCoin(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);
        int coinR = s * 28 / 100;

        // Glow behind coin
        r.DrawCircle((200, 160, 40), (cx, cy), coinR + s * 8 / 100, alpha: 8);

        // Shadow
        r.DrawCircle((0, 0, 0), (cx + 4, cy + 4), coinR, alpha: 30);

        // Coin body — rich metallic gold gradient
        for (int i = coinR; i >= 0; i -= 2)
        {
            float t = (float)i / coinR;
            int rr = (int)(170 + 70 * t);
            int g = (int)(130 + 60 * t);
            int b = (int)(15 + 35 * t);
            r.DrawCircle((rr, g, b), (cx, cy), i, alpha: 60);
        }

        // Edge ridge — thick outer ring with notches
        r.DrawCircle((180, 140, 30), (cx, cy), coinR, width: 3, alpha: 50);
        r.DrawCircle((240, 200, 60), (cx, cy), coinR - 1, width: 1, alpha: 28);
        // Edge notches (serrated edge)
        for (int notch = 0; notch < 24; notch++)
        {
            double na = notch * Math.PI / 12;
            int nx1 = cx + (int)(Math.Cos(na) * coinR);
            int ny1 = cy + (int)(Math.Sin(na) * coinR);
            int nx2 = cx + (int)(Math.Cos(na) * (coinR - 3));
            int ny2 = cy + (int)(Math.Sin(na) * (coinR - 3));
            r.DrawLine((160, 120, 20), (nx1, ny1), (nx2, ny2), width: 1, alpha: 20);
        }

        // Inner decorative ring
        r.DrawCircle((180, 140, 30), (cx, cy), coinR * 72 / 100, width: 2, alpha: 35);
        r.DrawCircle((200, 160, 40), (cx, cy), coinR * 68 / 100, width: 1, alpha: 20);

        // Cat face embossed in center
        int catR = coinR * 30 / 100;
        // Cat head circle
        r.DrawCircle((150, 110, 15), (cx, cy + catR / 5), catR, alpha: 28);
        r.DrawCircle((170, 130, 25), (cx, cy + catR / 5), catR - 1, width: 1, alpha: 18);
        // Left ear
        DrawTriangle(r, (150, 110, 15), cx - catR * 8 / 10, cy - catR * 6 / 10,
                     cx - catR * 4 / 10, cy + catR / 10, cx - catR * 11 / 10, cy + catR / 10, 28);
        // Right ear
        DrawTriangle(r, (150, 110, 15), cx + catR * 8 / 10, cy - catR * 6 / 10,
                     cx + catR * 4 / 10, cy + catR / 10, cx + catR * 11 / 10, cy + catR / 10, 28);
        // Eyes
        r.DrawCircle((130, 90, 10), (cx - catR * 4 / 10, cy), Math.Max(1, catR * 2 / 10), alpha: 30);
        r.DrawCircle((130, 90, 10), (cx + catR * 4 / 10, cy), Math.Max(1, catR * 2 / 10), alpha: 30);
        // Nose (small triangle)
        r.DrawCircle((140, 100, 15), (cx, cy + catR * 3 / 10), Math.Max(1, catR * 1 / 10), alpha: 25);
        // Whiskers
        r.DrawLine((150, 110, 15), (cx, cy + catR * 3 / 10), (cx + catR, cy + catR * 1 / 10), width: 1, alpha: 15);
        r.DrawLine((150, 110, 15), (cx, cy + catR * 3 / 10), (cx + catR, cy + catR * 5 / 10), width: 1, alpha: 15);
        r.DrawLine((150, 110, 15), (cx, cy + catR * 3 / 10), (cx - catR, cy + catR * 1 / 10), width: 1, alpha: 15);
        r.DrawLine((150, 110, 15), (cx, cy + catR * 3 / 10), (cx - catR, cy + catR * 5 / 10), width: 1, alpha: 15);

        // Specular highlight — bright spot upper left
        r.DrawCircle((255, 240, 160), (cx - coinR / 3, cy - coinR / 3), coinR / 4, alpha: 32);
        r.DrawCircle((255, 250, 200), (cx - coinR / 3 + 1, cy - coinR / 3 + 1), coinR / 6, alpha: 18);

        // Small sparkles
        r.DrawCircle((255, 255, 200), (cx + coinR * 80 / 100, cy - coinR * 70 / 100), 3, alpha: 55);
        r.DrawLine((255, 255, 200), (cx + coinR * 80 / 100 - 4, cy - coinR * 70 / 100),
            (cx + coinR * 80 / 100 + 4, cy - coinR * 70 / 100), width: 1, alpha: 35);
        r.DrawLine((255, 255, 200), (cx + coinR * 80 / 100, cy - coinR * 70 / 100 - 4),
            (cx + coinR * 80 / 100, cy - coinR * 70 / 100 + 4), width: 1, alpha: 35);
    }

    private static void DrawFAV_Handshake(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Warm friendship glow — concentric rings
        r.DrawCircle((255, 200, 160), (cx, cy), s * 36 / 100, alpha: 6);
        r.DrawCircle((255, 180, 140), (cx, cy), s * 30 / 100, alpha: 10);
        r.DrawCircle((255, 160, 120), (cx, cy), s * 22 / 100, alpha: 12);

        // Left sleeve/cuff
        r.DrawRect((60, 80, 160), (cx - s * 34 / 100, cy - s * 2 / 100, s * 14 / 100, s * 12 / 100), alpha: 45);
        r.DrawRect((80, 100, 180), (cx - s * 34 / 100, cy - s * 2 / 100, s * 14 / 100, 2), alpha: 25);
        r.DrawRect((40, 60, 140), (cx - s * 34 / 100, cy - s * 2 / 100, s * 14 / 100, s * 12 / 100), width: 1, alpha: 25);

        // Right sleeve/cuff
        r.DrawRect((160, 60, 60), (cx + s * 20 / 100, cy - s * 2 / 100, s * 14 / 100, s * 12 / 100), alpha: 45);
        r.DrawRect((180, 80, 80), (cx + s * 20 / 100, cy - s * 2 / 100, s * 14 / 100, 2), alpha: 25);
        r.DrawRect((140, 40, 40), (cx + s * 20 / 100, cy - s * 2 / 100, s * 14 / 100, s * 12 / 100), width: 1, alpha: 25);

        // Left arm — skin tone
        r.DrawLine((220, 180, 140), (cx - s * 20 / 100, cy + s * 4 / 100), (cx - s * 4 / 100, cy), width: 6, alpha: 50);
        r.DrawLine((240, 200, 160), (cx - s * 19 / 100, cy + s * 3 / 100), (cx - s * 3 / 100, cy - 1), width: 4, alpha: 22);

        // Right arm — slightly different skin tone
        r.DrawLine((200, 160, 120), (cx + s * 20 / 100, cy + s * 4 / 100), (cx + s * 4 / 100, cy), width: 6, alpha: 50);
        r.DrawLine((220, 180, 140), (cx + s * 19 / 100, cy + s * 3 / 100), (cx + s * 3 / 100, cy - 1), width: 4, alpha: 22);

        // Clasped hands at center — interlocking shape
        // Base hand shape
        r.DrawCircle((230, 190, 150), (cx, cy), Math.Max(5, s * 9 / 100), alpha: 48);
        r.DrawCircle((240, 200, 160), (cx - 1, cy - 1), Math.Max(4, s * 7 / 100), alpha: 22);

        // Fingers — alternating from each hand, interlocked
        for (int f = 0; f < 4; f++)
        {
            int fy = cy - s * 5 / 100 + f * s * 3 / 100;
            var col = f % 2 == 0 ? (220, 180, 140) : (200, 160, 120);
            r.DrawLine(col, (cx - s * 5 / 100, fy), (cx + s * 5 / 100, fy), width: 3, alpha: 38);
            // Knuckle bumps
            r.DrawCircle(col, (cx - s * 5 / 100, fy), Math.Max(1, s * 1 / 100), alpha: 25);
            r.DrawCircle(col, (cx + s * 5 / 100, fy), Math.Max(1, s * 1 / 100), alpha: 25);
        }

        // Thumb from left hand
        r.DrawLine((230, 190, 150), (cx - s * 3 / 100, cy + s * 6 / 100), (cx + s * 2 / 100, cy + s * 5 / 100), width: 3, alpha: 35);
        // Thumb from right hand
        r.DrawLine((210, 170, 130), (cx + s * 3 / 100, cy - s * 6 / 100), (cx - s * 2 / 100, cy - s * 7 / 100), width: 3, alpha: 35);

        // Friendship sparkles — stars around handshake
        (int ox, int oy, (int, int, int) col)[] sparkles = [
            (0, -s * 18 / 100, (255, 240, 180)),
            (-s * 14 / 100, -s * 12 / 100, (255, 220, 200)),
            (s * 14 / 100, -s * 12 / 100, (255, 230, 190)),
            (-s * 10 / 100, s * 16 / 100, (255, 200, 180)),
            (s * 10 / 100, s * 16 / 100, (255, 210, 190)),
        ];
        foreach (var (ox, oy, col) in sparkles)
        {
            int spx = cx + ox, spy = cy + oy;
            r.DrawCircle(col, (spx, spy), 2, alpha: 48);
            // Cross sparkle
            r.DrawLine(col, (spx - 3, spy), (spx + 3, spy), width: 1, alpha: 28);
            r.DrawLine(col, (spx, spy - 3), (spx, spy + 3), width: 1, alpha: 28);
        }

        // Small hearts floating
        r.DrawText("♥", cx - s * 20 / 100, cy - s * 20 / 100, Math.Max(6, s * 5 / 100), (255, 100, 120),
            anchorX: "center", anchorY: "center", alpha: 28);
        r.DrawText("♥", cx + s * 20 / 100, cy - s * 16 / 100, Math.Max(5, s * 4 / 100), (255, 120, 140),
            anchorX: "center", anchorY: "center", alpha: 22);
    }

    // ─── NOPE ──────────────────────────────────────────────────
    private static void DrawNOPE(Renderer r, int v, int x, int y, int w, int h, int cx, int cy)
    {
        switch (v)
        {
            case 0: DrawNOPE_StopSign(r, x, y, w, h, cx, cy); break;
            case 1: DrawNOPE_HandPalm(r, x, y, w, h, cx, cy); break;
            case 2: DrawNOPE_BrickWall(r, x, y, w, h, cx, cy); break;
            case 3: DrawNOPE_DeniedStamp(r, x, y, w, h, cx, cy); break;
        }
    }

    private static void DrawNOPE_StopSign(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);
        int signR = s * 28 / 100;

        // Red glow behind sign
        r.DrawCircle((200, 30, 20), (cx, cy), signR + s * 10 / 100, alpha: 10);
        r.DrawCircle((220, 40, 30), (cx, cy), signR + s * 5 / 100, alpha: 14);

        // Octagon shape — using polygon
        var oct = new (float X, float Y)[8];
        for (int i = 0; i < 8; i++)
        {
            double ang = i * Math.PI / 4 - Math.PI / 8;
            oct[i] = (cx + (float)(Math.Cos(ang) * signR), cy + (float)(Math.Sin(ang) * signR));
        }
        // Shadow
        var octSh = new (float X, float Y)[8];
        for (int i = 0; i < 8; i++) octSh[i] = (oct[i].X + 3, oct[i].Y + 3);
        r.DrawPolygon((0, 0, 0), octSh, alpha: 45);
        // Fill
        r.DrawPolygon((180, 30, 30), oct, alpha: 65);
        // Inner octagon highlight
        var octInner = new (float X, float Y)[8];
        for (int i = 0; i < 8; i++)
        {
            double ang = i * Math.PI / 4 - Math.PI / 8;
            octInner[i] = (cx + (float)(Math.Cos(ang) * signR * 0.88f), cy + (float)(Math.Sin(ang) * signR * 0.88f));
        }
        r.DrawPolygon((200, 40, 40), octInner, alpha: 30);
        // White border ring
        r.DrawPolygon((220, 200, 200), oct, width: 3, alpha: 45);

        // "STOP" text — bold centered
        int stopFs = Math.Max(8, signR * 50 / 100);
        r.DrawText("STOP", cx + 1, cy + 1, stopFs, (0, 0, 0), bold: true, anchorX: "center", anchorY: "center", alpha: 60);
        r.DrawText("STOP", cx, cy, stopFs, (255, 255, 255), bold: true, anchorX: "center", anchorY: "center", alpha: 75);

        // Post below
        r.DrawRect((70, 70, 70), (cx - s * 3 / 100, cy + signR + 2, s * 6 / 100, s * 14 / 100), alpha: 55);
        r.DrawRect((100, 100, 100), (cx - s * 3 / 100 + 1, cy + signR + 3, 2, s * 13 / 100), alpha: 20);

        // Reflection flare on sign
        r.DrawCircle((255, 200, 200), (cx - signR / 3, cy - signR / 3), signR / 5, alpha: 12);
    }

    private static void DrawNOPE_HandPalm(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Red prohibition aura — larger, more threatening
        r.DrawCircle((200, 30, 30), (cx, cy + s * 2 / 100), s * 38 / 100, alpha: 8);
        r.DrawCircle((220, 40, 40), (cx, cy + s * 4 / 100), s * 32 / 100, alpha: 14);

        // Prohibition circle behind hand
        r.DrawCircle((200, 40, 40), (cx, cy + s * 2 / 100), s * 28 / 100, width: 3, alpha: 25);

        // Wrist/arm coming from bottom
        r.DrawLine((200, 150, 110), (cx, cy + s * 30 / 100), (cx, cy + s * 16 / 100), width: Math.Max(6, s * 10 / 100), alpha: 45);
        // Sleeve cuff
        r.DrawRect((60, 80, 160), (cx - s * 8 / 100, cy + s * 24 / 100, s * 16 / 100, s * 6 / 100), alpha: 40);
        r.DrawRect((80, 100, 180), (cx - s * 7 / 100, cy + s * 24 / 100, s * 14 / 100, 2), alpha: 22);

        // Palm — large oval shape
        int palmR = s * 18 / 100;
        r.DrawCircle((210, 165, 125), (cx, cy + s * 6 / 100), palmR, alpha: 52);
        // Palm shadow
        r.DrawCircle((180, 130, 90), (cx + 2, cy + s * 8 / 100), palmR - 2, alpha: 15);
        // Palm highlight
        r.DrawCircle((240, 200, 160), (cx - palmR / 4, cy + s * 4 / 100), palmR / 2, alpha: 20);
        // Palm lines
        r.DrawLine((180, 130, 90), (cx - palmR * 6 / 10, cy + s * 4 / 100), (cx + palmR * 4 / 10, cy + s * 6 / 100), width: 1, alpha: 18);
        r.DrawLine((180, 130, 90), (cx - palmR * 5 / 10, cy + s * 8 / 100), (cx + palmR * 5 / 10, cy + s * 8 / 100), width: 1, alpha: 15);

        // Fingers — five detailed fingers extending up
        (int fx, int fLen, int fBot)[] fingers = [
            (cx - s * 12 / 100, s * 14 / 100, cy + s * 4 / 100),  // thumb (shorter, offset)
            (cx - s * 7 / 100, s * 20 / 100, cy - s * 2 / 100),   // index
            (cx - s * 1 / 100, s * 24 / 100, cy - s * 4 / 100),   // middle (longest)
            (cx + s * 5 / 100, s * 22 / 100, cy - s * 2 / 100),   // ring
            (cx + s * 11 / 100, s * 16 / 100, cy),                  // pinky (shortest)
        ];
        int fIdx = 0;
        foreach (var (fx, fLen, fBot) in fingers)
        {
            int fWidth = fIdx == 0 ? Math.Max(4, s * 5 / 100) : Math.Max(3, s * 4 / 100);
            // Finger shadow
            r.DrawLine((180, 130, 90), (fx + 1, fBot + 1), (fx + 1, fBot - fLen + 1), width: fWidth, alpha: 18);
            // Finger body
            r.DrawLine((210, 165, 125), (fx, fBot), (fx, fBot - fLen), width: fWidth, alpha: 52);
            // Finger highlight (left side)
            r.DrawLine((240, 200, 160), (fx - fWidth / 3, fBot), (fx - fWidth / 3, fBot - fLen), width: 1, alpha: 20);
            // Nail at tip
            r.DrawCircle((250, 220, 200), (fx, fBot - fLen), Math.Max(2, s * 2 / 100), alpha: 32);
            r.DrawCircle((255, 235, 220), (fx - 1, fBot - fLen - 1), Math.Max(1, s * 12 / 1000), alpha: 18);
            // Knuckle line (for non-thumb)
            if (fIdx > 0)
                r.DrawLine((190, 140, 100), (fx - fWidth / 2, fBot), (fx + fWidth / 2, fBot), width: 1, alpha: 18);
            fIdx++;
        }

        // Red prohibition slash — bold diagonal
        r.DrawLine((220, 40, 40), (cx - s * 26 / 100, cy + s * 22 / 100),
            (cx + s * 26 / 100, cy - s * 24 / 100), width: 5, alpha: 50);
        // Slash highlight
        r.DrawLine((255, 80, 80), (cx - s * 25 / 100, cy + s * 21 / 100),
            (cx + s * 25 / 100, cy - s * 23 / 100), width: 2, alpha: 18);

        // "NOPE" text below
        r.DrawText("NOPE", cx, cy + s * 34 / 100, Math.Max(6, s * 6 / 100), (220, 50, 50),
            anchorX: "center", anchorY: "center", alpha: 30);
    }

    private static void DrawNOPE_BrickWall(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);
        int wallW = s * 64 / 100, wallH = s * 54 / 100;
        int wx = cx - wallW / 2, wy = cy - wallH / 2;

        // Ground/floor
        r.DrawRect((90, 80, 65), (wx - s * 4 / 100, wy + wallH, wallW + s * 8 / 100, s * 6 / 100), alpha: 30);
        r.DrawRect((110, 100, 80), (wx - s * 3 / 100, wy + wallH, wallW + s * 6 / 100, 2), alpha: 18);

        // Wall shadow
        r.DrawRect((0, 0, 0), (wx + 4, wy + 4, wallW, wallH), alpha: 35);

        // Brick pattern — more colors, better detail
        int brickH = Math.Max(4, wallH / 7), brickW = Math.Max(8, wallW / 4);
        int mortarW = 2;
        (int, int, int)[] brickColors = [
            (180, 75, 55), (170, 70, 50), (190, 80, 60), (160, 65, 45),
            (175, 72, 52), (185, 78, 58), (165, 68, 48), (195, 85, 65),
        ];
        int brickIdx = 0;
        for (int row = 0; row < 7; row++)
        {
            int byy = wy + row * brickH;
            int offset = (row % 2) * (brickW / 2);
            for (int col = 0; col < 5; col++)
            {
                int bxx = wx + col * brickW + offset - brickW / 4;
                int clampX = Math.Max(wx, bxx);
                int clampW = Math.Min(wx + wallW, bxx + brickW - mortarW) - clampX;
                if (clampW > 0)
                {
                    var bc = brickColors[brickIdx % brickColors.Length];
                    brickIdx++;
                    // Brick body
                    r.DrawRect(bc, (clampX, byy, clampW, brickH - mortarW), alpha: 55);
                    // Top highlight
                    r.DrawRect((bc.Item1 + 30, bc.Item2 + 20, bc.Item3 + 15), (clampX + 1, byy, clampW - 2, 1), alpha: 18);
                    // Bottom shadow
                    r.DrawRect((bc.Item1 - 30, bc.Item2 - 20, bc.Item3 - 15), (clampX + 1, byy + brickH - mortarW - 1, clampW - 2, 1), alpha: 14);
                    // Surface texture — subtle spots
                    if (brickIdx % 3 == 0)
                        r.DrawCircle((bc.Item1 - 10, bc.Item2 - 8, bc.Item3 - 5), (clampX + clampW / 3, byy + brickH / 3), 1, alpha: 12);
                }
            }
        }

        // Mortar lines — cement colored
        for (int row = 1; row < 7; row++)
            r.DrawLine((120, 115, 100), (wx, wy + row * brickH), (wx + wallW, wy + row * brickH), width: mortarW, alpha: 25);
        // Wall border
        r.DrawRect((100, 90, 70), (wx, wy, wallW, wallH), width: 2, alpha: 35);

        // Crack — more realistic zigzag
        int crackX = cx + s * 4 / 100;
        r.DrawLine((30, 25, 22), (crackX, wy), (crackX - s * 3 / 100, wy + wallH * 15 / 100), width: 1, alpha: 45);
        r.DrawLine((30, 25, 22), (crackX - s * 3 / 100, wy + wallH * 15 / 100), (crackX + s * 1 / 100, wy + wallH * 30 / 100), width: 1, alpha: 42);
        r.DrawLine((30, 25, 22), (crackX + s * 1 / 100, wy + wallH * 30 / 100), (crackX - s * 2 / 100, wy + wallH * 50 / 100), width: 1, alpha: 38);
        r.DrawLine((30, 25, 22), (crackX - s * 2 / 100, wy + wallH * 50 / 100), (crackX + s * 3 / 100, wy + wallH * 70 / 100), width: 1, alpha: 35);
        // Branch cracks
        r.DrawLine((40, 35, 30), (crackX - s * 3 / 100, wy + wallH * 15 / 100), (crackX - s * 6 / 100, wy + wallH * 22 / 100), width: 1, alpha: 25);
        r.DrawLine((40, 35, 30), (crackX + s * 1 / 100, wy + wallH * 30 / 100), (crackX + s * 5 / 100, wy + wallH * 35 / 100), width: 1, alpha: 22);

        // Graffiti-style "NO" on wall
        r.DrawText("NO", cx - s * 10 / 100, cy + s * 2 / 100, Math.Max(8, s * 14 / 100), (220, 50, 50),
            anchorX: "center", anchorY: "center", alpha: 28);

        // Small moss/stain patches
        r.DrawCircle((80, 120, 60), (wx + wallW * 15 / 100, wy + wallH * 80 / 100), Math.Max(2, s * 2 / 100), alpha: 10);
        r.DrawCircle((70, 110, 50), (wx + wallW * 75 / 100, wy + wallH * 85 / 100), Math.Max(2, s * 3 / 100), alpha: 8);

        // Impact marks/scratches on wall
        r.DrawLine((140, 60, 45), (wx + wallW * 60 / 100, wy + wallH * 20 / 100), (wx + wallW * 65 / 100, wy + wallH * 25 / 100), width: 1, alpha: 18);
        r.DrawLine((140, 60, 45), (wx + wallW * 25 / 100, wy + wallH * 55 / 100), (wx + wallW * 30 / 100, wy + wallH * 52 / 100), width: 1, alpha: 16);
    }

    private static void DrawNOPE_DeniedStamp(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Stamp outline — double border with rotation feel
        int stW = s * 54 / 100, stH = s * 26 / 100;
        int stX = cx - stW / 2, stY = cy - stH / 2;

        // Ink shadow — offset like a physical stamp
        r.DrawRect((80, 15, 15), (stX + 4, stY + 4, stW, stH), alpha: 40);

        // Outer border
        r.DrawRect((200, 40, 40), (stX - 5, stY - 5, stW + 10, stH + 10), width: 3, alpha: 55);
        // Inner border
        r.DrawRect((200, 40, 40), (stX, stY, stW, stH), width: 2, alpha: 65);
        // Fill (slight tint)
        r.DrawRect((200, 40, 40), (stX + 2, stY + 2, stW - 4, stH - 4), alpha: 8);

        // "DENIED" text
        int stampFs = Math.Max(9, s * 16 / 100);
        r.DrawText("DENIED", cx + 2, cy + 2, stampFs, (0, 0, 0), bold: true, anchorX: "center", anchorY: "center", alpha: 50);
        r.DrawText("DENIED", cx, cy, stampFs, (200, 40, 40), bold: true, anchorX: "center", anchorY: "center", alpha: 75);

        // Diagonal slash through stamp
        r.DrawLine((180, 30, 30), (stX - s * 5 / 100, stY + stH + s * 5 / 100),
            (stX + stW + s * 5 / 100, stY - s * 5 / 100), width: 3, alpha: 45);

        // Ink splatter dots — more organic scatter
        var splatters = new[] {
            (stX - s * 3 / 100, stY + stH + s * 7 / 100, 3, 38),
            (stX + stW + s * 5 / 100, stY - s * 7 / 100, 2, 32),
            (stX + stW / 3, stY + stH + s * 4 / 100, 2, 28),
            (stX - s * 1 / 100, stY - s * 3 / 100, 2, 25),
            (stX + stW * 80 / 100, stY + stH + s * 2 / 100, 1, 22),
            (cx + s * 20 / 100, cy - s * 12 / 100, 2, 26),
        };
        foreach (var (sx, sy, sr, sa) in splatters)
            r.DrawCircle((200, 40, 40), (sx, sy), sr, alpha: sa);

        // Stamp pad ink smudge at bottom edge
        r.DrawRect((180, 30, 30), (stX + stW / 4, stY + stH + 1, stW / 2, 2), alpha: 18);
    }

    // ─── GENERIC (unknown card type) ───────────────────────────
    private static void DrawGeneric(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);
        // Question mark motif
        r.DrawCircle((100, 160, 220), (cx, cy - s * 6 / 100), s * 20 / 100, width: 3, alpha: 35);
        r.DrawRect((100, 160, 220), (cx - s * 2 / 100, cy + s * 6 / 100, s * 4 / 100, s * 8 / 100), alpha: 35);
        r.DrawCircle((100, 160, 220), (cx, cy + s * 20 / 100), Math.Max(2, s * 3 / 100), alpha: 40);
    }

    // ─── Helpers ───────────────────────────────────────────────
    /// <summary>Draw a filled triangle pointing up from (x,y) with given height.</summary>
    private static void DrawTriangle(Renderer r, int x, int y, int h, (int R, int G, int B) col, int alpha)
    {
        for (int row = 0; row < h; row++)
        {
            int rowW = Math.Max(1, row * 2 * h / h);
            int rx = x + h / 2 - rowW / 2;
            r.DrawRect(col, (rx, y + row, rowW, 1), alpha: alpha);
        }
    }

    /// <summary>Draw a filled triangle given three vertex points.</summary>
    private static void DrawTriangle(Renderer r, (int R, int G, int B) col,
        int x0, int y0, int x1, int y1, int x2, int y2, int alpha)
    {
        // Sort vertices by Y
        if (y0 > y1) { (x0, y0, x1, y1) = (x1, y1, x0, y0); }
        if (y0 > y2) { (x0, y0, x2, y2) = (x2, y2, x0, y0); }
        if (y1 > y2) { (x1, y1, x2, y2) = (x2, y2, x1, y1); }
        int totalH = y2 - y0;
        if (totalH == 0) { r.DrawLine(col, (x0, y0), (x2, y2), width: 1, alpha: alpha); return; }
        for (int row = y0; row <= y2; row++)
        {
            float tAll = (float)(row - y0) / totalH;
            int xAll = x0 + (int)((x2 - x0) * tAll);
            int xSeg;
            if (row < y1)
            {
                int segH = y1 - y0;
                float tSeg = segH == 0 ? 0 : (float)(row - y0) / segH;
                xSeg = x0 + (int)((x1 - x0) * tSeg);
            }
            else
            {
                int segH = y2 - y1;
                float tSeg = segH == 0 ? 1 : (float)(row - y1) / segH;
                xSeg = x1 + (int)((x2 - x1) * tSeg);
            }
            int left = Math.Min(xAll, xSeg);
            int right = Math.Max(xAll, xSeg);
            r.DrawRect(col, (left, row, right - left + 1, 1), alpha: alpha);
        }
    }

    /// <summary>Draw a detailed sword with gradient blade, ornate crossguard and grip.</summary>
    private static void DrawDetailedSword(Renderer r, int x1, int y1, int x2, int y2, int s, int variant)
    {
        // Calculate direction
        float dx = x2 - x1, dy = y2 - y1;
        float len = (float)Math.Sqrt(dx * dx + dy * dy);
        if (len < 1) return;
        float nx = dx / len, ny = dy / len;  // along blade
        float px = -ny, py = nx;              // perpendicular

        // Blade occupies first 65% of length
        float bladeLen = len * 0.65f;
        int bx2 = x1 + (int)(nx * bladeLen), by2 = y1 + (int)(ny * bladeLen);

        // Blade — multi-layer for gradient steel look
        // Outer blade (darker)
        r.DrawLine((160, 160, 180), (x1, y1), (bx2, by2), width: 5, alpha: 45);
        // Inner blade (lighter)
        r.DrawLine((200, 200, 220), (x1, y1), (bx2, by2), width: 3, alpha: 40);
        // Centre line / fuller (dark groove)
        r.DrawLine((120, 120, 140), (x1 + (int)(nx * len * 0.05f), y1 + (int)(ny * len * 0.05f)),
            (bx2 - (int)(nx * s * 2 / 100), by2 - (int)(ny * s * 2 / 100)), width: 1, alpha: 25);
        // Edge highlight
        r.DrawLine((240, 240, 255), (x1 + (int)(px * 2), y1 + (int)(py * 2)),
            (bx2 + (int)(px * 2), by2 + (int)(py * 2)), width: 1, alpha: 18);

        // Blade tip — pointed
        int tipX = x1 - (int)(px * 1), tipY = y1 - (int)(py * 1);
        r.DrawLine((220, 220, 240), (x1, y1), (tipX, tipY), width: 1, alpha: 35);

        // Crossguard at blade/grip junction
        int gx = bx2, gy = by2;
        int guardLen = s * 8 / 100;
        int g1x = gx + (int)(px * guardLen), g1y = gy + (int)(py * guardLen);
        int g2x = gx - (int)(px * guardLen), g2y = gy - (int)(py * guardLen);
        // Guard body
        r.DrawLine((160, 130, 50), (g1x, g1y), (g2x, g2y), width: 4, alpha: 50);
        r.DrawLine((200, 170, 80), (g1x, g1y), (g2x, g2y), width: 2, alpha: 28);
        // Guard ends — small decorative circles
        r.DrawCircle((180, 150, 60), (g1x, g1y), Math.Max(2, s * 2 / 100), alpha: 40);
        r.DrawCircle((180, 150, 60), (g2x, g2y), Math.Max(2, s * 2 / 100), alpha: 40);

        // Grip — wrapped leather look
        float gripLen = len * 0.25f;
        int grx1 = bx2 + (int)(nx * s * 1 / 100), gry1 = by2 + (int)(ny * s * 1 / 100);
        int grx2 = bx2 + (int)(nx * gripLen), gry2 = by2 + (int)(ny * gripLen);
        r.DrawLine((100, 60, 30), (grx1, gry1), (grx2, gry2), width: 4, alpha: 50);
        // Wrap lines on grip
        for (int wrap = 0; wrap < 5; wrap++)
        {
            float wt = (wrap + 1) / 6f;
            int wwx = grx1 + (int)((grx2 - grx1) * wt);
            int wwy = gry1 + (int)((gry2 - gry1) * wt);
            int w1x = wwx + (int)(px * 3), w1y = wwy + (int)(py * 3);
            int w2x = wwx - (int)(px * 3), w2y = wwy - (int)(py * 3);
            r.DrawLine((130, 90, 50), (w1x, w1y), (w2x, w2y), width: 1, alpha: 22);
        }

        // Pommel at end
        int pmx = grx2 + (int)(nx * s * 2 / 100), pmy = gry2 + (int)(ny * s * 2 / 100);
        r.DrawCircle((160, 130, 50), (pmx, pmy), Math.Max(3, s * 3 / 100), alpha: 50);
        r.DrawCircle((200, 170, 80), (pmx - 1, pmy - 1), Math.Max(2, s * 2 / 100), alpha: 22);
        // Gem in pommel
        var gemCol = variant == 0 ? (200, 40, 40) : (40, 80, 200);
        r.DrawCircle(gemCol, (pmx, pmy), Math.Max(1, s * 1 / 100), alpha: 45);
    }

    private static void DrawSword(Renderer r, int x1, int y1, int x2, int y2, int s)
    {
        // Blade
        r.DrawLine((180, 180, 200), (x1, y1), (x2, y2), width: 3, alpha: 50);
        // Edge highlight
        r.DrawLine((220, 220, 240), (x1 + 1, y1 + 1), (x2 + 1, y2 + 1), width: 1, alpha: 25);
        // Guard at center
        int gx = (x1 + x2) / 2, gy = (y1 + y2) / 2;
        r.DrawLine((140, 100, 50), (gx - s * 4 / 100, gy + s * 4 / 100),
            (gx + s * 4 / 100, gy - s * 4 / 100), width: 3, alpha: 50);
        // Pommel near start
        r.DrawCircle((120, 90, 40), (x2, y2), Math.Max(2, s * 3 / 100), alpha: 50);
    }
}
