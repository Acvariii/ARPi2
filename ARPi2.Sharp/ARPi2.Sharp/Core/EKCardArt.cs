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
            var glowFaded = glow.WithAlpha(255);
            paint.Shader = SKShader.CreateRadialGradient(
                new SKPoint(cx, cy * 0.9f), s * 0.4f,
                new[] { glowFaded, glow.WithAlpha(255), SKColors.Transparent },
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
                byte a = (byte)(80 + (i % 4) * 25);
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
                    new[] { accent.WithAlpha(245), glow.WithAlpha(235), SKColors.Transparent },
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
                new[] { accent.WithAlpha(210), glow.WithAlpha(196), SKColors.Transparent },
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
                        paint.Color = new SKColor(255, 255, 255, (byte)(40 + (seed & 3) * 15));
                        c.DrawPoint(tx, ty, paint);
                    }
                    else if (seed > 1010)
                    {
                        paint.Color = new SKColor(0, 0, 0, (byte)(50 + (seed & 3) * 15));
                        c.DrawPoint(tx, ty, paint);
                    }
                }
            }
        }

        // 8. Particle dust motes — subtle floating ambient specs (background layer only)
        using (var paint = new SKPaint { IsAntialias = true })
        {
            int moteCount = 6 + variant;
            for (int i = 0; i < moteCount; i++)
            {
                float mx = (((i * 127 + variant * 31) % w) + w) % w;
                float my = (((i * 89 + variant * 43) % h) + h) % h;
                float mr = 0.5f + (i % 3) * 0.3f;
                byte ma = (byte)(15 + (i % 5) * 6);
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
        r.DrawCircle((160, 40, 0), (cx, cy + s * 42 / 100), s * 50 / 100, alpha: 255);
        r.DrawCircle((200, 60, 0), (cx, cy + s * 38 / 100), s * 40 / 100, alpha: 255);
        r.DrawCircle((255, 120, 0), (cx, cy + s * 35 / 100), s * 28 / 100, alpha: 255);

        // Ground fire line
        for (int i = 0; i < 10; i++)
        {
            int fx = cx - s * 40 / 100 + i * s * 8 / 100;
            int fh = s * (4 + (i * 7 + 3) % 6) / 100;
            int fy = cy + s * 38 / 100 - fh;
            var fireCol = i % 3 == 0 ? (255, 80, 0) : i % 3 == 1 ? (255, 160, 0) : (255, 200, 40);
            r.DrawRect(fireCol, (fx, fy, s * 4 / 100, fh), alpha: 255 + (i % 4) * 5);
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
            r.DrawRect((rr, gg, bb), (bx, by, bw, bh + 1), alpha: 255 - b * 3);
        }

        // Mushroom cap — richly layered with depth
        int capR = s * 34 / 100;
        int capY = cy - s * 20 / 100;
        r.DrawCircle((120, 20, 0), (cx, capY + s * 2 / 100), capR + 4, alpha: 255); // shadow
        r.DrawCircle((160, 40, 0), (cx, capY), capR, alpha: 255);
        r.DrawCircle((200, 60, 0), (cx, capY - s * 2 / 100), capR * 85 / 100, alpha: 255);
        r.DrawCircle((230, 90, 10), (cx, capY - s * 4 / 100), capR * 68 / 100, alpha: 255);
        r.DrawCircle((245, 130, 20), (cx, capY - s * 5 / 100), capR * 50 / 100, alpha: 255);
        r.DrawCircle((255, 180, 50), (cx, capY - s * 7 / 100), capR * 32 / 100, alpha: 255);
        r.DrawCircle((255, 220, 100), (cx, capY - s * 8 / 100), capR * 18 / 100, alpha: 255);
        // Cap highlight
        r.DrawCircle((255, 240, 180), (cx - capR / 4, capY - capR / 3), capR / 5, alpha: 255);

        // Cat ears silhouette in smoke
        int earS = s * 10 / 100;
        DrawTriangle(r, cx - earS * 2, capY - earS - s * 2 / 100, earS, (0, 0, 0), 255);
        DrawTriangle(r, cx + earS, capY - earS - s * 2 / 100, earS, (0, 0, 0), 255);
        // Inner ears
        DrawTriangle(r, cx - earS * 2 + earS / 4, capY - earS * 3 / 4 - s * 2 / 100, earS * 60 / 100, (200, 60, 0), 200);
        DrawTriangle(r, cx + earS + earS / 4, capY - earS * 3 / 4 - s * 2 / 100, earS * 60 / 100, (200, 60, 0), 200);

        // Cat eyes in smoke — glowing
        int eyeR = Math.Max(3, s * 4 / 100);
        r.DrawCircle((255, 220, 0), (cx - s * 7 / 100, capY), eyeR + 2, alpha: 255);
        r.DrawCircle((255, 200, 0), (cx - s * 7 / 100, capY), eyeR, alpha: 255);
        r.DrawCircle((255, 220, 0), (cx + s * 7 / 100, capY), eyeR + 2, alpha: 255);
        r.DrawCircle((255, 200, 0), (cx + s * 7 / 100, capY), eyeR, alpha: 255);
        // Slit pupils
        r.DrawRect((0, 0, 0), (cx - s * 7 / 100 - 1, capY - eyeR + 1, 2, eyeR * 2 - 2), alpha: 255);
        r.DrawRect((0, 0, 0), (cx + s * 7 / 100 - 1, capY - eyeR + 1, 2, eyeR * 2 - 2), alpha: 255);
        // Eye specular
        r.DrawCircle((255, 255, 200), (cx - s * 8 / 100, capY - 1), 1, alpha: 255);
        r.DrawCircle((255, 255, 200), (cx + s * 6 / 100, capY - 1), 1, alpha: 255);

        // Shockwave rings
        r.DrawCircle((255, 80, 0), (cx, cy + s * 32 / 100), s * 44 / 100, width: 2, alpha: 255);
        r.DrawCircle((255, 140, 20), (cx, cy + s * 24 / 100), s * 50 / 100, width: 1, alpha: 255);
        r.DrawCircle((255, 200, 50), (cx, cy + s * 28 / 100), s * 55 / 100, width: 1, alpha: 255);

        // Debris chunks
        for (int i = 0; i < 7; i++)
        {
            double ang = 0.3 + i * 0.8;
            int dist = s * (20 + i * 5) / 100;
            int dx = cx + (int)(Math.Cos(ang) * dist);
            int dy = cy + (int)(Math.Sin(ang) * dist * 0.6);
            int ds = Math.Max(2, s * (2 + i % 3) / 100);
            r.DrawRect((120, 80, 30), (dx, dy, ds, ds), alpha: 255 + (i % 3) * 8);
        }

        // Danger stripes at bottom edge
        DrawDangerStripes(r, x + s * 5 / 100, y + h - s * 8 / 100, w - s * 10 / 100, s * 6 / 100, 200);

        // Bold black outlines on cat ears
        r.DrawLine((0, 0, 0), (cx - earS * 2, capY - s * 2 / 100), (cx - earS * 2 + earS / 2, capY - earS - s * 2 / 100), width: 2, alpha: 255);
        r.DrawLine((0, 0, 0), (cx + earS, capY - s * 2 / 100), (cx + earS + earS / 2, capY - earS - s * 2 / 100), width: 2, alpha: 255);

        // Fur texture on mushroom cap
        DrawFurTexture(r, cx, capY, capR * 60 / 100, 14, (160, 100, 40), 210);

        // Floating skull emoji doodles
        DrawMiniCatFace(r, cx + s * 30 / 100, cy - s * 16 / 100, Math.Max(3, s * 4 / 100), (80, 60, 40), 255);

        // Extra sparkle particles — white hot embers rising
        for (int i = 0; i < 5; i++)
        {
            int ex = cx + (i * 19 - 38) % (s * 30 / 100);
            int ey = cy - s * 30 / 100 - i * s * 4 / 100;
            DrawSparkle(r, ex, ey, Math.Max(2, s * 2 / 100), (255, 200, 80), 224 - i * 3);
        }

        // Zigzag energy crackle around stem
        for (int i = 0; i < 4; i++)
        {
            int zx = cx + (i % 2 == 0 ? -1 : 1) * s * 12 / 100;
            int zy = cy + i * s * 6 / 100 - s * 6 / 100;
            r.DrawLine((255, 100, 0), (zx, zy), (zx + (i % 2 == 0 ? s * 4 / 100 : -s * 4 / 100), zy + s * 3 / 100), width: 1, alpha: 255);
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
            r.DrawCircle((255, 80 + wave * 30, 0), (cx, bombCy), wr, width: 1, alpha: 255 - wave * 2);
        }

        // Bomb shadow — elongated
        r.DrawCircle((0, 0, 0), (cx + 4, bombCy + 5), bombR + 2, alpha: 255);
        r.DrawCircle((20, 5, 0), (cx + 3, bombCy + 4), bombR, alpha: 255);

        // Bomb body — rich metallic gradient
        for (int i = bombR; i >= 0; i -= 2)
        {
            float t = (float)i / bombR;
            int g = (int)(15 + 30 * t);
            int b = (int)(18 + 8 * t);
            r.DrawCircle((g + 5, g, b), (cx, bombCy), i, alpha: 255);
        }

        // Specular highlights — multiple for metallic sheen
        r.DrawCircle((80, 80, 90), (cx - bombR / 3, bombCy - bombR / 3), bombR / 3, alpha: 255);
        r.DrawCircle((120, 120, 135), (cx - bombR / 3, bombCy - bombR / 3), bombR / 5, alpha: 255);
        r.DrawCircle((180, 180, 200), (cx - bombR * 2 / 5, bombCy - bombR * 2 / 5), bombR / 8, alpha: 255);
        // Lower rim light
        r.DrawCircle((60, 50, 45), (cx + bombR / 4, bombCy + bombR / 3), bombR / 4, alpha: 255);

        // Rivets/bolts around equator
        for (int i = 0; i < 8; i++)
        {
            double ang = i * Math.PI / 4;
            int rx = cx + (int)(Math.Cos(ang) * bombR * 85 / 100);
            int ry = bombCy + (int)(Math.Sin(ang) * bombR * 85 / 100);
            r.DrawCircle((80, 80, 85), (rx, ry), Math.Max(1, s * 2 / 100), alpha: 255);
            r.DrawCircle((60, 55, 50), (rx + 1, ry + 1), Math.Max(1, s * 1 / 100), alpha: 255);
        }

        // Skull & crossbones marking on bomb
        int skullCy = bombCy - s * 1 / 100;
        // Skull circle
        r.DrawCircle((200, 180, 60), (cx, skullCy), Math.Max(4, s * 8 / 100), alpha: 255);
        // Skull eyes
        r.DrawCircle((0, 0, 0), (cx - s * 3 / 100, skullCy - s * 2 / 100), Math.Max(1, s * 2 / 100), alpha: 255);
        r.DrawCircle((0, 0, 0), (cx + s * 3 / 100, skullCy - s * 2 / 100), Math.Max(1, s * 2 / 100), alpha: 255);
        // Skull nose
        DrawTriangle(r, cx - s * 1 / 100, skullCy + s * 1 / 100, Math.Max(2, s * 2 / 100), (0, 0, 0), 200);
        // Crossbones below
        r.DrawLine((200, 180, 60), (cx - s * 8 / 100, bombCy + s * 8 / 100), (cx + s * 8 / 100, bombCy + s * 14 / 100), width: 2, alpha: 255);
        r.DrawLine((200, 180, 60), (cx + s * 8 / 100, bombCy + s * 8 / 100), (cx - s * 8 / 100, bombCy + s * 14 / 100), width: 2, alpha: 255);

        // Cat whiskers on skull
        r.DrawLine((200, 180, 60), (cx - s * 4 / 100, skullCy + s * 3 / 100), (cx - s * 10 / 100, skullCy + s * 1 / 100), width: 1, alpha: 255);
        r.DrawLine((200, 180, 60), (cx - s * 4 / 100, skullCy + s * 4 / 100), (cx - s * 10 / 100, skullCy + s * 4 / 100), width: 1, alpha: 255);
        r.DrawLine((200, 180, 60), (cx + s * 4 / 100, skullCy + s * 3 / 100), (cx + s * 10 / 100, skullCy + s * 1 / 100), width: 1, alpha: 255);
        r.DrawLine((200, 180, 60), (cx + s * 4 / 100, skullCy + s * 4 / 100), (cx + s * 10 / 100, skullCy + s * 4 / 100), width: 1, alpha: 255);

        // Fuse nozzle — metallic cylinder
        int nzW = s * 10 / 100, nzH = s * 7 / 100;
        r.DrawRect((100, 85, 50), (cx - nzW / 2, bombCy - bombR - nzH + 3, nzW, nzH), alpha: 255);
        r.DrawRect((140, 125, 80), (cx - nzW / 2 + 1, bombCy - bombR - nzH + 4, nzW - 2, 2), alpha: 255);
        r.DrawRect((80, 70, 45), (cx - nzW / 2 + 1, bombCy - bombR - 1, nzW - 2, 2), alpha: 255);

        // Fuse — thick braided rope with color gradient
        int fuseY = bombCy - bombR - nzH / 2 + 2;
        // Fuse path: nozzle → curve → tip
        (int, int)[] fusePts = [
            (cx, fuseY), (cx + s * 4 / 100, fuseY - s * 5 / 100),
            (cx + s * 8 / 100, fuseY - s * 9 / 100), (cx + s * 13 / 100, fuseY - s * 13 / 100)
        ];
        // Outer glow
        for (int i = 0; i < fusePts.Length - 1; i++)
            r.DrawLine((200, 120, 40), fusePts[i], fusePts[i + 1], width: 4, alpha: 255);
        // Main fuse
        for (int i = 0; i < fusePts.Length - 1; i++)
            r.DrawLine((160, 130, 70), fusePts[i], fusePts[i + 1], width: 3, alpha: 255);
        // Braid detail
        for (int i = 0; i < fusePts.Length - 1; i++)
            r.DrawLine((200, 170, 100), fusePts[i], fusePts[i + 1], width: 1, alpha: 255);

        // Fire along fuse — orange/yellow flames
        for (int i = 1; i < fusePts.Length; i++)
        {
            int flameH = s * (3 + i) / 100;
            var flCol = i % 2 == 0 ? (255, 180, 0) : (255, 100, 0);
            r.DrawCircle(flCol, (fusePts[i].Item1, fusePts[i].Item2 - flameH / 2), Math.Max(2, flameH), alpha: 255 + i * 5);
        }

        // Spark shower at fuse tip
        int sparkX = fusePts[^1].Item1, sparkY = fusePts[^1].Item2;
        r.DrawCircle((255, 255, 240), (sparkX, sparkY), Math.Max(3, s * 5 / 100), alpha: 255);
        r.DrawCircle((255, 240, 100), (sparkX, sparkY), Math.Max(4, s * 8 / 100), alpha: 255);
        r.DrawCircle((255, 160, 0), (sparkX, sparkY), Math.Max(5, s * 12 / 100), alpha: 255);
        // Spark rays — rainbow-tinted
        for (int i = 0; i < 10; i++)
        {
            double ang = i * Math.PI / 5 + 0.3;
            int len = s * (6 + (i % 3) * 3) / 100;
            int rx = sparkX + (int)(Math.Cos(ang) * len);
            int ry = sparkY + (int)(Math.Sin(ang) * len);
            var rayCol = i % 3 == 0 ? (255, 255, 180) : i % 3 == 1 ? (255, 200, 60) : (255, 140, 20);
            r.DrawLine(rayCol, (sparkX, sparkY), (rx, ry), width: 1, alpha: 255 + (i % 2) * 10);
        }
        // Spark particles flying off
        for (int i = 0; i < 6; i++)
        {
            double ang = i * 1.1 + 0.8;
            int dist = s * (10 + i * 3) / 100;
            int px = sparkX + (int)(Math.Cos(ang) * dist);
            int py = sparkY + (int)(Math.Sin(ang) * dist * 0.6) - s * 4 / 100;
            r.DrawCircle((255, 220, 80), (px, py), Math.Max(1, 2 - i / 3), alpha: 255 - i * 5);
        }

        // Ground cracks beneath bomb
        for (int i = 0; i < 5; i++)
        {
            double ang = Math.PI * 0.3 + i * Math.PI * 0.1;
            int crLen = s * (8 + i * 3) / 100;
            int crX = cx + (int)(Math.Cos(ang) * crLen);
            int crY = bombCy + bombR + (int)(Math.Sin(ang) * crLen / 3);
            r.DrawLine((60, 30, 10), (cx + (int)(Math.Cos(ang) * bombR * 80 / 100), bombCy + bombR - 2), (crX, crY), width: 1, alpha: 255);
        }

        // Bold cartoon outline on bomb
        DrawBoldCircleOutline(r, cx, bombCy, bombR, 240);

        // Polka dot pattern on bomb body — cartoon texture
        DrawDotPattern(r, cx - bombR * 6 / 10, bombCy - bombR * 6 / 10,
            bombR * 12 / 10, bombR * 12 / 10, (60, 60, 70), Math.Max(1, s / 100), 200, spacing: s * 6 / 100);

        // Zigzag danger border at top
        DrawZigzagPattern(r, x + s * 4 / 100, y + s * 2 / 100, w - s * 8 / 100, s * 5 / 100, (255, 160, 0), 200, spacing: s * 6 / 100);

        // Additional colorful sparks — cyan, magenta, green
        r.DrawCircle((0, 255, 255), (sparkX - s * 8 / 100, sparkY - s * 4 / 100), 2, alpha: 255);
        r.DrawCircle((255, 0, 255), (sparkX + s * 6 / 100, sparkY - s * 6 / 100), 2, alpha: 255);
        r.DrawCircle((0, 255, 0), (sparkX - s * 3 / 100, sparkY + s * 5 / 100), 2, alpha: 255);

        // Smoke wisps curling from fuse
        for (int i = 0; i < 3; i++)
        {
            int smokeX = sparkX + (i - 1) * s * 3 / 100;
            int smokeY = sparkY - s * (10 + i * 5) / 100;
            r.DrawCircle((140, 140, 150), (smokeX, smokeY), Math.Max(3, s * 4 / 100), alpha: 255 - i * 3);
            r.DrawCircle((160, 160, 170), (smokeX + 2, smokeY - 2), Math.Max(2, s * 3 / 100), alpha: 255 - i * 2);
        }

        // Sweat drops next to skull (tension!)
        DrawSweatDrops(r, cx + s * 12 / 100, bombCy - bombR, s, 2);

        // Tiny cat paw prints fleeing the bomb
        for (int i = 0; i < 3; i++)
        {
            int pawX = cx - s * 20 / 100 - i * s * 8 / 100;
            int pawY = bombCy + bombR + s * 8 / 100 + i * s * 2 / 100;
            r.DrawCircle((100, 80, 60), (pawX, pawY), Math.Max(2, s * 2 / 100), alpha: 255 - i * 4);
            r.DrawCircle((100, 80, 60), (pawX - s * 1 / 100, pawY - s * 2 / 100), 1, alpha: 255 - i * 3);
            r.DrawCircle((100, 80, 60), (pawX + s * 1 / 100, pawY - s * 2 / 100), 1, alpha: 255 - i * 3);
        }
    }

    // Variant 2: Nuclear hazard symbol with cat ears — vivid warning style
    private static void DrawEK_NukeSymbol(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);
        int symR = s * 30 / 100;

        // === Apocalyptic gradient background — deep red/orange sky ===
        for (int row = 0; row < h; row++)
        {
            float t = (float)row / h;
            int rv = (int)(30 + 60 * t);
            int gv = (int)(10 + 30 * t);
            int bv = (int)(5 + 10 * t);
            r.DrawRect((rv, gv, bv), (x, y + row, w, 1), alpha: 240);
        }
        // Radioactive glow — concentric circles
        for (int ring = 6; ring >= 0; ring--)
        {
            int rr = symR + s * (20 + ring * 5) / 100;
            int av = 60 + ring * 15;
            r.DrawCircle((av, av * 80 / 100, 0), (cx, cy), rr, alpha: 120 - ring * 12);
        }

        // Pulsing radiation rings with gradient
        for (int ring = 0; ring < 6; ring++)
        {
            int rr = symR + s * (6 + ring * 5) / 100;
            int rv2 = 255 - ring * 15;
            int gv2 = 200 - ring * 20;
            r.DrawCircle((rv2, gv2, 0), (cx, cy), rr, width: 2, alpha: 240 - ring * 20);
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
            r.DrawLine(col, (sx1, sy1), (sx2, sy2), width: 3, alpha: 255);
        }

        // Hazard circle — rich gradient fill
        for (int i = symR; i >= 0; i -= 1)
        {
            float t = (float)i / symR;
            int yy = (int)(70 + 30 * t);
            int gg = (int)(55 + 25 * t);
            r.DrawCircle((yy, gg, 0), (cx, cy), i, alpha: 255);
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
                int rr2 = (int)(200 + 55 * at);
                int gg2 = (int)(160 + 40 * at);
                r.DrawLine((rr2, gg2, 0), (x1, y1), (x2, y2), width: 2, alpha: 255);
            }
            double endAngL = startAng - span / 2, endAngR = startAng + span / 2;
            r.DrawLine((100, 80, 0), (cx + (int)(Math.Cos(endAngL) * symR * 25 / 100), cy + (int)(Math.Sin(endAngL) * symR * 25 / 100)),
                (cx + (int)(Math.Cos(endAngL) * symR * 85 / 100), cy + (int)(Math.Sin(endAngL) * symR * 85 / 100)), width: 1, alpha: 255);
            r.DrawLine((100, 80, 0), (cx + (int)(Math.Cos(endAngR) * symR * 25 / 100), cy + (int)(Math.Sin(endAngR) * symR * 25 / 100)),
                (cx + (int)(Math.Cos(endAngR) * symR * 85 / 100), cy + (int)(Math.Sin(endAngR) * symR * 85 / 100)), width: 1, alpha: 255);
        }

        // === Center — detailed terrified cat face ===
        int cfR = symR * 22 / 100;
        r.DrawCircle((30, 25, 0), (cx, cy), cfR + 2, alpha: 255);
        // Cat head gradient
        for (int i = cfR; i >= 0; i--)
        {
            float t = (float)i / cfR;
            r.DrawCircle(((int)(180 + 60 * t), (int)(160 + 40 * t), (int)(60 + 30 * t)), (cx, cy), i, alpha: 255);
        }
        // Eyes — wide with fear
        int eyeR = Math.Max(2, symR * 6 / 100);
        r.DrawCircle((255, 255, 220), (cx - symR * 7 / 100, cy - symR * 3 / 100), eyeR, alpha: 255);
        r.DrawCircle((255, 255, 220), (cx + symR * 7 / 100, cy - symR * 3 / 100), eyeR, alpha: 255);
        r.DrawCircle((0, 0, 0), (cx - symR * 7 / 100, cy - symR * 3 / 100), Math.Max(1, eyeR * 60 / 100), alpha: 255);
        r.DrawCircle((0, 0, 0), (cx + symR * 7 / 100, cy - symR * 3 / 100), Math.Max(1, eyeR * 60 / 100), alpha: 255);
        // Eye highlights
        r.DrawCircle((255, 255, 255), (cx - symR * 8 / 100, cy - symR * 4 / 100), Math.Max(1, eyeR / 3), alpha: 230);
        r.DrawCircle((255, 255, 255), (cx + symR * 6 / 100, cy - symR * 4 / 100), Math.Max(1, eyeR / 3), alpha: 230);
        // Nose
        DrawTriangle(r, cx - symR * 2 / 100, cy + symR * 2 / 100, Math.Max(2, symR * 4 / 100), (200, 100, 80), 240);
        // Mouth — open in shock
        r.DrawCircle((80, 30, 30), (cx, cy + symR * 8 / 100), Math.Max(2, symR * 5 / 100), alpha: 220);
        r.DrawCircle((180, 80, 60), (cx, cy + symR * 8 / 100), Math.Max(1, symR * 3 / 100), alpha: 200);
        // Whiskers
        int wLen = s * 14 / 100;
        r.DrawLine((240, 200, 0), (cx - symR * 7 / 100, cy + symR * 4 / 100), (cx - wLen, cy + symR * 1 / 100), width: 1, alpha: 240);
        r.DrawLine((240, 200, 0), (cx - symR * 7 / 100, cy + symR * 6 / 100), (cx - wLen, cy + symR * 6 / 100), width: 1, alpha: 240);
        r.DrawLine((240, 200, 0), (cx + symR * 7 / 100, cy + symR * 4 / 100), (cx + wLen, cy + symR * 1 / 100), width: 1, alpha: 240);
        r.DrawLine((240, 200, 0), (cx + symR * 7 / 100, cy + symR * 6 / 100), (cx + wLen, cy + symR * 6 / 100), width: 1, alpha: 240);

        // Cat ears with inner detail
        int earH = s * 16 / 100;
        DrawTriangle(r, cx - symR * 60 / 100, cy - symR - earH / 3, earH, (240, 200, 0), 255);
        DrawTriangle(r, cx + symR * 20 / 100, cy - symR - earH / 3, earH, (240, 200, 0), 255);
        DrawTriangle(r, cx - symR * 54 / 100, cy - symR - earH / 5, earH * 55 / 100, (200, 100, 60), 220);
        DrawTriangle(r, cx + symR * 26 / 100, cy - symR - earH / 5, earH * 55 / 100, (200, 100, 60), 220);

        // Outer bold border
        r.DrawCircle((0, 0, 0), (cx, cy), symR + 1, width: 3, alpha: 255);
        DrawBoldCircleOutline(r, cx, cy, symR + 2, 240);

        // Danger stripes on top and bottom borders
        DrawDangerStripes(r, x + s * 2 / 100, y + s * 2 / 100, w - s * 4 / 100, s * 4 / 100, 230);
        DrawDangerStripes(r, x + s * 2 / 100, y + h - s * 6 / 100, w - s * 4 / 100, s * 4 / 100, 230);

        // Geiger counter particles — glowing dots scattered
        for (int i = 0; i < 10; i++)
        {
            double ang = i * 0.63 + 0.4;
            int dist = symR + s * (8 + i * 3) / 100;
            int gx = cx + (int)(Math.Cos(ang) * dist);
            int gy = cy + (int)(Math.Sin(ang) * dist);
            r.DrawCircle((200, 255, 0), (gx, gy), Math.Max(1, 2 - i / 4), alpha: 240 - i * 15);
            r.DrawCircle((255, 255, 100), (gx, gy), 1, alpha: 200 - i * 15);
        }

        // Corner hazard icons
        int hazFs = Math.Max(6, s * 6 / 100);
        r.DrawText("☢", cx - s * 30 / 100, cy - s * 30 / 100, hazFs, (255, 220, 0), anchorX: "center", anchorY: "center", alpha: 240);
        r.DrawText("☢", cx + s * 30 / 100, cy + s * 26 / 100, hazFs, (255, 220, 0), anchorX: "center", anchorY: "center", alpha: 240);
        r.DrawText("⚠", cx, cy + symR + s * 10 / 100, Math.Max(7, s * 7 / 100), (255, 200, 0), anchorX: "center", anchorY: "center", alpha: 250);

        // Sparkle accents
        DrawSparkle(r, cx - s * 26 / 100, cy + s * 14 / 100, s * 2 / 100, (255, 255, 100), 220);
        DrawSparkle(r, cx + s * 24 / 100, cy - s * 18 / 100, s * 18 / 1000, (255, 200, 50), 210);

        // Embossed "BOOM" text
        int bFs = Math.Max(5, s * 4 / 100);
        r.DrawText("BOOM", cx + 1, cy + s * 40 / 100 + 1, bFs, (60, 30, 0), bold: true, anchorX: "center", anchorY: "center", alpha: 220);
        r.DrawText("BOOM", cx, cy + s * 40 / 100, bFs, (255, 200, 0), bold: true, anchorX: "center", anchorY: "center", alpha: 250);
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
            r.DrawCircle(col, (cx, cy), rr, width: 2, alpha: 255 - ring * 2);
        }

        // Explosion core — layered fiery gradient
        r.DrawCircle((255, 255, 220), (cx, cy), s * 6 / 100, alpha: 255);
        r.DrawCircle((255, 240, 100), (cx, cy), s * 10 / 100, alpha: 255);
        r.DrawCircle((255, 180, 40), (cx, cy), s * 16 / 100, alpha: 255);
        r.DrawCircle((255, 100, 0), (cx, cy), s * 22 / 100, alpha: 255);
        r.DrawCircle((200, 50, 0), (cx, cy), s * 28 / 100, alpha: 255);

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
            r.DrawLine(rayCol, (cx, cy), (ex, ey), width: rw, alpha: 255 + (i % 3) * 5);
        }

        int shift = s * 12 / 100;

        // ── Left half of cat face ──
        // Face outline
        r.DrawCircle((200, 140, 80), (cx - shift, cy), s * 20 / 100, alpha: 255);
        r.DrawCircle((180, 120, 60), (cx - shift, cy), s * 18 / 100, alpha: 255);
        // Fur texture lines
        for (int i = 0; i < 4; i++)
        {
            double fa = -Math.PI * 0.6 + i * 0.35;
            int fx = cx - shift + (int)(Math.Cos(fa) * s * 16 / 100);
            int fy = cy + (int)(Math.Sin(fa) * s * 16 / 100);
            r.DrawLine((160, 100, 40), (cx - shift, cy), (fx, fy), width: 1, alpha: 255);
        }
        // Eye — large with detail
        int leyX = cx - shift - s * 6 / 100, leyY = cy - s * 4 / 100;
        r.DrawCircle((255, 255, 200), (leyX, leyY), Math.Max(3, s * 5 / 100), alpha: 255); // white
        r.DrawCircle((160, 200, 0), (leyX, leyY), Math.Max(2, s * 4 / 100), alpha: 255); // iris
        r.DrawCircle((0, 0, 0), (leyX, leyY), Math.Max(1, s * 2 / 100), alpha: 255); // pupil
        r.DrawCircle((255, 255, 255), (leyX - 1, leyY - 1), 1, alpha: 255); // highlight
        // Ear
        DrawTriangle(r, cx - shift - s * 16 / 100, cy - s * 28 / 100, s * 14 / 100, (200, 140, 80), 250);
        DrawTriangle(r, cx - shift - s * 14 / 100, cy - s * 24 / 100, s * 9 / 100, (220, 120, 100), 200);
        // Whiskers
        r.DrawLine((180, 160, 120), (cx - shift - s * 10 / 100, cy + s * 2 / 100),
            (cx - shift - s * 32 / 100, cy - s * 4 / 100), width: 1, alpha: 255);
        r.DrawLine((180, 160, 120), (cx - shift - s * 10 / 100, cy + s * 4 / 100),
            (cx - shift - s * 32 / 100, cy + s * 4 / 100), width: 1, alpha: 255);
        r.DrawLine((180, 160, 120), (cx - shift - s * 8 / 100, cy + s * 6 / 100),
            (cx - shift - s * 30 / 100, cy + s * 12 / 100), width: 1, alpha: 255);
        // Half nose
        DrawTriangle(r, cx - shift + s * 2 / 100, cy + s * 2 / 100, Math.Max(2, s * 4 / 100), (200, 100, 80), 200);

        // ── Right half of cat face ──
        r.DrawCircle((200, 140, 80), (cx + shift, cy), s * 20 / 100, alpha: 255);
        r.DrawCircle((180, 120, 60), (cx + shift, cy), s * 18 / 100, alpha: 255);
        // Fur texture
        for (int i = 0; i < 4; i++)
        {
            double fa = -Math.PI * 0.4 + i * 0.35;
            int fx = cx + shift + (int)(Math.Cos(fa) * s * 16 / 100);
            int fy = cy + (int)(Math.Sin(fa) * s * 16 / 100);
            r.DrawLine((160, 100, 40), (cx + shift, cy), (fx, fy), width: 1, alpha: 255);
        }
        // Eye
        int reyX = cx + shift + s * 6 / 100, reyY = cy - s * 4 / 100;
        r.DrawCircle((255, 255, 200), (reyX, reyY), Math.Max(3, s * 5 / 100), alpha: 255);
        r.DrawCircle((160, 200, 0), (reyX, reyY), Math.Max(2, s * 4 / 100), alpha: 255);
        r.DrawCircle((0, 0, 0), (reyX, reyY), Math.Max(1, s * 2 / 100), alpha: 255);
        r.DrawCircle((255, 255, 255), (reyX - 1, reyY - 1), 1, alpha: 255);
        // Ear
        DrawTriangle(r, cx + shift + s * 6 / 100, cy - s * 28 / 100, s * 14 / 100, (200, 140, 80), 250);
        DrawTriangle(r, cx + shift + s * 8 / 100, cy - s * 24 / 100, s * 9 / 100, (220, 120, 100), 200);
        // Whiskers
        r.DrawLine((180, 160, 120), (cx + shift + s * 10 / 100, cy + s * 2 / 100),
            (cx + shift + s * 32 / 100, cy - s * 4 / 100), width: 1, alpha: 255);
        r.DrawLine((180, 160, 120), (cx + shift + s * 10 / 100, cy + s * 4 / 100),
            (cx + shift + s * 32 / 100, cy + s * 4 / 100), width: 1, alpha: 255);
        r.DrawLine((180, 160, 120), (cx + shift + s * 8 / 100, cy + s * 6 / 100),
            (cx + shift + s * 30 / 100, cy + s * 12 / 100), width: 1, alpha: 255);
        // Half nose
        DrawTriangle(r, cx + shift - s * 5 / 100, cy + s * 2 / 100, Math.Max(2, s * 4 / 100), (200, 100, 80), 200);

        // Debris flying outward — fur tufts
        for (int i = 0; i < 10; i++)
        {
            double ang = 0.2 + i * 0.65;
            int dist = s * (22 + (i * 7) % 16) / 100;
            int dx = cx + (int)(Math.Cos(ang) * dist);
            int dy = cy + (int)(Math.Sin(ang) * dist * 0.7);
            int ds = Math.Max(2, s * (2 + i % 3) / 100);
            var debCol = i % 3 == 0 ? (200, 140, 80) : i % 3 == 1 ? (180, 120, 60) : (160, 100, 40);
            r.DrawRect(debCol, (dx, dy, ds, ds), alpha: 255 + (i % 3) * 5);
        }

        // Jagged split line down the center
        for (int seg = 0; seg < 8; seg++)
        {
            int sy1 = cy - s * 30 / 100 + seg * s * 8 / 100;
            int sy2 = sy1 + s * 8 / 100;
            int jag = (seg % 2 == 0 ? 1 : -1) * s * 3 / 100;
            r.DrawLine((255, 240, 160), (cx + jag, sy1), (cx - jag, sy2), width: 2, alpha: 255);
        }

        // Fur texture on both halves — hair flying everywhere
        DrawFurTexture(r, cx - shift, cy, s * 16 / 100, 16, (180, 120, 50), 210);
        DrawFurTexture(r, cx + shift, cy, s * 16 / 100, 16, (180, 120, 50), 210);

        // More colorful fur tufts flying out — cyan, magenta, teal
        (int ox, int oy, (int, int, int) tuftCol)[] tufts = [
            (-s * 30 / 100, -s * 14 / 100, (0, 220, 220)),
            (s * 28 / 100, s * 6 / 100, (220, 80, 220)),
            (-s * 10 / 100, s * 28 / 100, (80, 200, 120)),
            (s * 34 / 100, -s * 10 / 100, (255, 180, 60)),
        ];
        foreach (var (ox, oy, tuftCol) in tufts)
        {
            int tx = cx + ox, ty = cy + oy;
            r.DrawCircle(tuftCol, (tx, ty), Math.Max(2, s * 2 / 100), alpha: 255);
            r.DrawLine(tuftCol, (tx, ty), (tx + s * 2 / 100, ty - s * 1 / 100), width: 1, alpha: 255);
        }

        // Bold outlines on cat face halves
        DrawBoldCircleOutline(r, cx - shift, cy, s * 18 / 100, 200);
        DrawBoldCircleOutline(r, cx + shift, cy, s * 18 / 100, 200);

        // Sweat drops on the cat
        DrawSweatDrops(r, cx - shift - s * 10 / 100, cy - s * 10 / 100, s, 2);
        DrawSweatDrops(r, cx + shift + s * 10 / 100, cy - s * 10 / 100, s, 2);

        // Action lines radiating — explosion feel (contained within subject)
        DrawActionLines(r, cx, cy, s, 10, (255, 200, 60), 180, s * 22 / 100);

        // Zigzag electric crack along split
        for (int i = 0; i < 6; i++)
        {
            int zy = cy - s * 28 / 100 + i * s * 10 / 100;
            int zx1 = cx + (i % 2 == 0 ? s * 5 / 100 : -s * 5 / 100);
            int zx2 = cx + (i % 2 == 0 ? -s * 4 / 100 : s * 4 / 100);
            r.DrawLine((255, 255, 100), (zx1, zy), (zx2, zy + s * 4 / 100), width: 1, alpha: 255);
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

        // === Arena coliseum background ===
        // Concentric stone rings
        for (int ring = 0; ring < 6; ring++)
        {
            int rr = s * (42 - ring * 6) / 100;
            int gv = 60 + ring * 12;
            r.DrawCircle((gv, gv - 10, gv - 20), (cx, cy), rr, width: 2, alpha: 220 - ring * 15);
        }
        // Stone pillar silhouettes on sides
        for (int p = 0; p < 2; p++)
        {
            int px2 = p == 0 ? x + s * 3 / 100 : x + w - s * 7 / 100;
            r.DrawRect((50, 45, 35), (px2, y + s * 4 / 100, s * 4 / 100, h - s * 8 / 100), alpha: 200);
            // Pillar capital
            r.DrawRect((70, 65, 50), (px2 - s * 1 / 100, y + s * 4 / 100, s * 6 / 100, s * 3 / 100), alpha: 200);
            // Column fluting
            for (int fl = 0; fl < 4; fl++)
            {
                int fy = y + s * 10 / 100 + fl * s * 12 / 100;
                r.DrawLine((60, 55, 45), (px2 + s * 2 / 100, fy), (px2 + s * 2 / 100, fy + s * 8 / 100), width: 1, alpha: 160);
            }
        }

        // === Impact energy at crossing point (contained) ===
        // Layered glow — warm to hot center
        r.DrawCircle((180, 100, 30), (cx, cy), s * 18 / 100, alpha: 200);
        r.DrawCircle((220, 150, 40), (cx, cy), s * 14 / 100, alpha: 230);
        r.DrawCircle((255, 200, 80), (cx, cy), s * 10 / 100, alpha: 250);
        r.DrawCircle((255, 240, 160), (cx, cy), s * 6 / 100, alpha: 255);
        r.DrawCircle((255, 255, 230), (cx, cy), s * 3 / 100, alpha: 255);
        // Energy ring around impact
        r.DrawCircle((255, 220, 120), (cx, cy), s * 12 / 100, width: 2, alpha: 220);
        r.DrawCircle((255, 180, 60), (cx, cy), s * 16 / 100, width: 1, alpha: 160);

        // === Swords — detailed with DrawDetailedSword ===
        DrawDetailedSword(r, cx - s * 32 / 100, cy - s * 30 / 100, cx + s * 20 / 100, cy + s * 30 / 100, s, 0);
        DrawDetailedSword(r, cx + s * 32 / 100, cy - s * 30 / 100, cx - s * 20 / 100, cy + s * 30 / 100, s, 1);

        // === Battle damage sparks — flying from impact in arc ===
        for (int sp = 0; sp < 12; sp++)
        {
            double ang = sp * Math.PI / 6 + 0.2;
            int dist = s * (14 + (sp * 5) % 12) / 100;
            int spx = cx + (int)(Math.Cos(ang) * dist);
            int spy = cy + (int)(Math.Sin(ang) * dist);
            int spr = Math.Max(1, 3 - sp / 4);
            // Hot white core
            r.DrawCircle((255, 255, 200), (spx, spy), spr, alpha: 240 - sp * 10);
            // Warm trail
            int tx = spx + (int)(Math.Cos(ang) * s * 2 / 100);
            int ty = spy + (int)(Math.Sin(ang) * s * 2 / 100);
            r.DrawLine((255, 200, 80), (spx, spy), (tx, ty), width: 1, alpha: 180 - sp * 8);
        }

        // === Shield emblem behind swords ===
        // Shield shape — pointed bottom
        var shield = new (float X, float Y)[] {
            (cx - s * 16 / 100, cy - s * 16 / 100),
            (cx + s * 16 / 100, cy - s * 16 / 100),
            (cx + s * 14 / 100, cy + s * 4 / 100),
            (cx, cy + s * 18 / 100),
            (cx - s * 14 / 100, cy + s * 4 / 100),
        };
        // Shield painted behind swords at low alpha
        r.DrawPolygon((120, 80, 40), shield, alpha: 140);
        r.DrawPolygon((160, 120, 60), shield, width: 2, alpha: 200);
        // Shield crest line
        r.DrawLine((180, 140, 70), (cx, cy - s * 16 / 100), (cx, cy + s * 18 / 100), width: 1, alpha: 180);

        // === Battle ribbon banner ===
        int banY = cy + s * 28 / 100;
        // Banner shadow
        r.DrawRect((60, 15, 10), (cx - s * 21 / 100 + 2, banY + 2, s * 42 / 100, s * 7 / 100), alpha: 180);
        // Banner body — gradient
        r.DrawRect((160, 30, 25), (cx - s * 21 / 100, banY, s * 42 / 100, s * 7 / 100), alpha: 255);
        r.DrawRect((190, 45, 35), (cx - s * 20 / 100, banY + 1, s * 40 / 100, 2), alpha: 240);
        r.DrawRect((140, 25, 20), (cx - s * 20 / 100, banY + s * 5 / 100, s * 40 / 100, 1), alpha: 200);
        // Banner fold triangles
        DrawTriangle(r, cx - s * 25 / 100, banY, s * 6 / 100, (120, 20, 15), 220);
        DrawTriangle(r, cx + s * 19 / 100, banY, s * 6 / 100, (120, 20, 15), 220);
        // Banner text — embossed
        int banFs = Math.Max(6, s * 6 / 100);
        r.DrawText("ATTACK!", cx + 1, banY + s * 35 / 1000 + 1, banFs, (80, 15, 10), bold: true, anchorX: "center", anchorY: "center", alpha: 220);
        r.DrawText("ATTACK!", cx, banY + s * 35 / 1000, banFs, (255, 230, 100), bold: true, anchorX: "center", anchorY: "center", alpha: 255);

        // === Warrior cat in corner ===
        DrawMiniCatFace(r, x + s * 10 / 100, y + s * 10 / 100, Math.Max(4, s * 5 / 100), (200, 140, 80), 250);
        // Tiny helmet on cat
        r.DrawCircle((140, 140, 150), (x + s * 10 / 100, y + s * 7 / 100), s * 4 / 100, alpha: 180);
        r.DrawLine((180, 180, 190), (x + s * 10 / 100, y + s * 3 / 100), (x + s * 10 / 100, y + s * 6 / 100), width: 1, alpha: 200);

        // === Battle symbols ===
        r.DrawText("⚔", x + w - s * 12 / 100, y + s * 10 / 100, Math.Max(6, s * 6 / 100), (200, 180, 100),
            anchorX: "center", anchorY: "center", alpha: 240);
        r.DrawText("★", cx - s * 26 / 100, cy - s * 24 / 100, Math.Max(5, s * 5 / 100), (255, 200, 60),
            anchorX: "center", anchorY: "center", alpha: 220);

        // Sparkle at impact
        DrawSparkle(r, cx, cy, s * 3 / 100, (255, 255, 200), 240);

        // Bold outline on intersection
        r.DrawCircle((0, 0, 0), (cx, cy), s * 4 / 100, width: 2, alpha: 255);
    }

    // Variant 1: Claw scratch marks — fierce and vibrant
    private static void DrawATK_ClawMarks(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // === Rich torn material background — gradient layers ===
        for (int row = 0; row < h; row++)
        {
            float t = (float)row / h;
            int rv = (int)(100 + 50 * t);
            int gv = (int)(15 + 20 * t);
            int bv = (int)(5 + 10 * t);
            r.DrawRect((rv, gv, bv), (x, y + row, w, 1), alpha: 240);
        }
        // Torn surface material — gradient grey overlay
        int surfX = x + s * 8 / 100, surfY = y + s * 5 / 100;
        int surfW = w - s * 16 / 100, surfH = h - s * 10 / 100;
        for (int row = 0; row < surfH; row++)
        {
            float t = (float)row / surfH;
            int gv = (int)(140 - 30 * t);
            r.DrawRect((gv, gv, gv + 10), (surfX, surfY + row, surfW, 1), alpha: 230);
        }

        // === Cat paw silhouette — gradient filled with detail ===
        int pawCx = cx + s * 16 / 100, pawCy = cy - s * 22 / 100;
        // Paw shadow
        r.DrawCircle((0, 0, 0), (pawCx + 3, pawCy + 3), Math.Max(4, s * 9 / 100), alpha: 180);
        // Paw gradient fill
        for (int i = s * 9 / 100; i >= 0; i--)
        {
            float t = (float)i / (s * 9 / 100);
            r.DrawCircle(((int)(40 + 30 * t), (int)(15 + 10 * t), (int)(5 + 5 * t)), (pawCx, pawCy), Math.Max(1, i), alpha: 255);
        }
        // Toe beans with gradient
        for (int toe = 0; toe < 4; toe++)
        {
            int tx = pawCx - s * 5 / 100 + toe * s * 35 / 1000;
            int ty = pawCy - s * 9 / 100;
            r.DrawCircle((0, 0, 0), (tx + 2, ty + 2), Math.Max(2, s * 3 / 100), alpha: 160);
            r.DrawCircle((80, 30, 15), (tx, ty), Math.Max(2, s * 3 / 100), alpha: 255);
            r.DrawCircle((120, 50, 30), (tx, ty), Math.Max(1, s * 18 / 1000), alpha: 220);
        }
        // Central pad
        r.DrawCircle((100, 40, 25), (pawCx, pawCy), Math.Max(2, s * 4 / 100), alpha: 255);
        r.DrawCircle((140, 70, 40), (pawCx, pawCy), Math.Max(1, s * 25 / 1000), alpha: 200);
        DrawBoldCircleOutline(r, pawCx, pawCy, Math.Max(4, s * 9 / 100), 220);

        // === Five claw scratches — deep with multiple layers ===
        for (int c = 0; c < 5; c++)
        {
            int offsetX = (c - 2) * (s * 10 / 100);
            int topY = cy - s * 14 / 100;
            int botY = cy + s * 34 / 100;
            int curve = (c - 2) * s * 3 / 100;

            // Shadow layer
            r.DrawLine((0, 0, 0), (cx + offsetX + 3, topY + 3), (cx + offsetX - curve + 3, botY + 3), width: 6, alpha: 200);
            // Deep groove
            r.DrawLine((30, 8, 5), (cx + offsetX, topY), (cx + offsetX - curve, botY), width: 5, alpha: 255);
            // Red revealed flesh
            r.DrawLine((200, 40, 20), (cx + offsetX, topY + s * 3 / 100), (cx + offsetX - curve, botY - s * 3 / 100), width: 3, alpha: 255);
            // Inner bright red
            r.DrawLine((255, 80, 40), (cx + offsetX, topY + s * 5 / 100), (cx + offsetX - curve + 1, botY - s * 5 / 100), width: 2, alpha: 255);
            // Specular edge highlight
            r.DrawLine((255, 160, 100), (cx + offsetX + 2, topY + s * 6 / 100), (cx + offsetX - curve + 3, botY - s * 6 / 100), width: 1, alpha: 240);
        }

        // Torn material fragments flying off
        for (int i = 0; i < 8; i++)
        {
            int tx = cx + (i * 19 - 47) % (s * 36 / 100) - s * 18 / 100;
            int ty = cy + s * 6 / 100 + (i * 13) % (s * 20 / 100);
            int tsz = Math.Max(2, s * (2 + i % 3) / 100);
            r.DrawRect((140 - i * 5, 135 - i * 5, 130 - i * 5), (tx, ty, tsz, tsz / 2), alpha: 220);
        }

        // Blood/damage droplets
        for (int i = 0; i < 6; i++)
        {
            int dx = cx + (i * 31 - 62) % (s * 40 / 100) - s * 20 / 100;
            int dy = cy + s * 30 / 100 + (i * 17) % (s * 10 / 100);
            int dr = Math.Max(1, s * (1 + i % 3) / 100);
            r.DrawCircle((180, 30, 20), (dx, dy), dr, alpha: 240);
            r.DrawCircle((220, 60, 40), (dx, dy), Math.Max(1, dr - 1), alpha: 200);
        }

        // Red drip lines from scratches
        for (int drip = 0; drip < 4; drip++)
        {
            int dripX = cx + (drip - 2) * s * 8 / 100 + s * 4 / 100;
            int dripTop = cy + s * 28 / 100;
            int dripLen = s * (5 + drip * 2) / 100;
            r.DrawLine((200, 30, 20), (dripX, dripTop), (dripX, dripTop + dripLen), width: 2, alpha: 240);
            r.DrawCircle((200, 30, 20), (dripX, dripTop + dripLen), 2, alpha: 240);
        }

        // Anger marks — enhanced with glow
        int amX = cx - s * 24 / 100, amY = cy - s * 28 / 100;
        r.DrawLine((255, 60, 30), (amX, amY), (amX + s * 6 / 100, amY), width: 3, alpha: 255);
        r.DrawLine((255, 60, 30), (amX + s * 3 / 100, amY - s * 3 / 100), (amX + s * 3 / 100, amY + s * 3 / 100), width: 3, alpha: 255);
        int am2X = cx + s * 22 / 100, am2Y = cy - s * 26 / 100;
        r.DrawLine((255, 60, 30), (am2X, am2Y), (am2X + s * 5 / 100, am2Y), width: 3, alpha: 255);
        r.DrawLine((255, 60, 30), (am2X + s * 25 / 1000, am2Y - s * 25 / 1000), (am2X + s * 25 / 1000, am2Y + s * 25 / 1000), width: 3, alpha: 255);

        // Fur scattered around the scratches
        DrawFurTexture(r, cx, cy + s * 10 / 100, s * 22 / 100, 12, (140, 100, 60), 220);

        // Shredded fabric triangles
        DrawTriangle(r, cx + s * 20 / 100, cy + s * 22 / 100, Math.Max(3, s * 5 / 100), (130, 130, 140), 220);
        DrawTriangle(r, cx - s * 24 / 100, cy + s * 18 / 100, Math.Max(3, s * 4 / 100), (140, 140, 150), 220);

        // Sparkle accents at claw tips
        DrawSparkle(r, cx - s * 20 / 100, cy - s * 14 / 100, s * 2 / 100, (255, 200, 100), 230);
        DrawSparkle(r, cx + s * 20 / 100, cy - s * 14 / 100, s * 18 / 1000, (255, 180, 80), 220);
        DrawSparkle(r, cx, cy + s * 34 / 100, s * 15 / 1000, (255, 100, 60), 210);

        // Warning symbol
        r.DrawText("⚡", cx - s * 30 / 100, cy + s * 32 / 100, Math.Max(5, s * 5 / 100), (255, 200, 60),
            anchorX: "center", anchorY: "center", alpha: 230);

        // Embossed "SLASH!" text
        int slFs = Math.Max(5, s * 4 / 100);
        r.DrawText("SLASH!", cx + 1, cy + s * 40 / 100 + 1, slFs, (60, 10, 5), bold: true, anchorX: "center", anchorY: "center", alpha: 220);
        r.DrawText("SLASH!", cx, cy + s * 40 / 100, slFs, (255, 80, 40), bold: true, anchorX: "center", anchorY: "center", alpha: 255);
    }

    // Variant 2: Lightning bolt — electrifying storm
    private static void DrawATK_LightningBolt(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // === Dark stormy sky gradient background ===
        for (int row = 0; row < h; row++)
        {
            float t = (float)row / h;
            int rv = (int)(20 + 30 * t);
            int gv = (int)(15 + 25 * t);
            int bv = (int)(40 + 50 * t);
            r.DrawRect((rv, gv, bv), (x, y + row, w, 1), alpha: 240);
        }

        // Storm clouds at top — multi-layered with gradient fills
        (int ox, int oy, int cr)[] clouds = [
            (-s * 15 / 100, s * 8 / 100, s * 15 / 100),
            (s * 10 / 100, s * 6 / 100, s * 13 / 100),
            (0, s * 4 / 100, s * 18 / 100),
            (-s * 6 / 100, s * 10 / 100, s * 11 / 100),
            (s * 18 / 100, s * 10 / 100, s * 10 / 100),
        ];
        foreach (var (ox, oy, cr) in clouds)
        {
            int ccx = cx + ox, ccy = y + oy;
            // Cloud body gradient
            for (int i = cr; i >= 0; i -= 2)
            {
                float t = (float)i / cr;
                r.DrawCircle(((int)(40 + 35 * t), (int)(35 + 30 * t), (int)(55 + 40 * t)), (ccx, ccy), Math.Max(1, i), alpha: 240);
            }
            // Cloud highlight
            r.DrawCircle((80, 70, 100), (ccx - cr / 4, ccy - cr / 4), Math.Max(2, cr / 3), alpha: 180);
        }

        // Electric field glow — radial purple
        for (int ring = 5; ring >= 0; ring--)
        {
            int rr = s * (40 - ring * 5) / 100;
            r.DrawCircle(((int)(50 + ring * 10), (int)(30 + ring * 8), (int)(140 + ring * 18)), (cx, cy), rr, alpha: 80 + ring * 15);
        }

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
            r.DrawLine((160, 120, 255), bolt[i], bolt[i + 1], width: 10, alpha: 200);
        // Mid glow — cyan
        for (int i = 0; i < bolt.Length - 1; i++)
            r.DrawLine((100, 200, 255), bolt[i], bolt[i + 1], width: 7, alpha: 230);
        // Bright core — blue
        for (int i = 0; i < bolt.Length - 1; i++)
            r.DrawLine((180, 220, 255), bolt[i], bolt[i + 1], width: 4, alpha: 250);
        // White hot core
        for (int i = 0; i < bolt.Length - 1; i++)
            r.DrawLine((255, 255, 250), bolt[i], bolt[i + 1], width: 2, alpha: 255);

        // Branch bolts
        r.DrawLine((140, 180, 255), bolt[1], (bolt[1].Item1 - s * 16 / 100, bolt[1].Item2 + s * 12 / 100), width: 3, alpha: 240);
        r.DrawLine((255, 255, 240), bolt[1], (bolt[1].Item1 - s * 16 / 100, bolt[1].Item2 + s * 12 / 100), width: 1, alpha: 240);
        r.DrawLine((140, 180, 255), bolt[3], (bolt[3].Item1 + s * 14 / 100, bolt[3].Item2 + s * 10 / 100), width: 3, alpha: 240);
        r.DrawLine((255, 255, 240), bolt[3], (bolt[3].Item1 + s * 14 / 100, bolt[3].Item2 + s * 10 / 100), width: 1, alpha: 240);
        // Sub-branches
        r.DrawLine((120, 160, 240), (bolt[1].Item1 - s * 16 / 100, bolt[1].Item2 + s * 12 / 100),
            (bolt[1].Item1 - s * 22 / 100, bolt[1].Item2 + s * 20 / 100), width: 2, alpha: 220);
        r.DrawLine((120, 160, 240), bolt[4], (bolt[4].Item1 + s * 10 / 100, bolt[4].Item2 - s * 6 / 100), width: 2, alpha: 220);
        r.DrawLine((0, 255, 200), bolt[2], (bolt[2].Item1 - s * 12 / 100, bolt[2].Item2 - s * 8 / 100), width: 2, alpha: 230);

        // Impact burst at ground — bright layered flash
        for (int glow = 4; glow >= 0; glow--)
        {
            int gr = s * (14 - glow * 2) / 100;
            int bri = 140 + glow * 28;
            r.DrawCircle((Math.Min(255, bri), Math.Min(255, bri + 20), 255), bolt[^1], Math.Max(2, gr), alpha: 180 + glow * 15);
        }
        // Ground crack lines
        for (int i = 0; i < 6; i++)
        {
            double ang = Math.PI * 0.15 + i * Math.PI * 0.13;
            int len = s * (6 + i * 2) / 100;
            int gx = bolt[^1].Item1 + (int)(Math.Cos(ang) * len);
            int gy = bolt[^1].Item2 + (int)(Math.Sin(ang) * len / 3);
            r.DrawLine((160, 180, 255), bolt[^1], (gx, gy), width: 2, alpha: 220);
        }

        // Rain streaks — varied
        for (int i = 0; i < 12; i++)
        {
            int rx = x + s * 6 / 100 + i * s * 7 / 100;
            int ry1 = y + s * 18 / 100 + (i * 17) % (s * 20 / 100);
            int rLen = s * (4 + i % 3 * 2) / 100;
            int rAlpha = 180 - i * 8;
            r.DrawLine((100, 130, 180), (rx, ry1), (rx - 2, ry1 + rLen), width: 1, alpha: rAlpha);
        }

        // Electric sparks scattered
        for (int i = 0; i < 8; i++)
        {
            double ang = i * 0.8 + 0.5;
            int dist = s * (16 + (i * 7) % 16) / 100;
            int px = cx + (int)(Math.Cos(ang) * dist);
            int py = cy + (int)(Math.Sin(ang) * dist);
            r.DrawCircle((180, 200, 255), (px, py), Math.Max(1, 2 - i / 4), alpha: 230 - i * 15);
            r.DrawRect((180, 200, 255), (px - 3, py, 7, 1), alpha: 200 - i * 15);
            r.DrawRect((180, 200, 255), (px, py - 3, 1, 7), alpha: 200 - i * 15);
        }

        // Scared mini cat cowering
        DrawMiniCatFace(r, cx - s * 24 / 100, cy + s * 26 / 100, Math.Max(3, s * 5 / 100), (120, 100, 80), 240);
        DrawSweatDrops(r, cx - s * 20 / 100, cy + s * 22 / 100, s, 3);

        // Sparkle accents
        DrawSparkle(r, cx + s * 26 / 100, cy - s * 20 / 100, s * 2 / 100, (200, 220, 255), 230);
        DrawSparkle(r, cx - s * 28 / 100, cy + s * 10 / 100, s * 18 / 1000, (180, 200, 255), 220);

        // Embossed "ZAP!" text
        int zFs = Math.Max(6, s * 5 / 100);
        r.DrawText("ZAP!", cx + 2, cy + s * 40 / 100 + 2, zFs, (30, 20, 60), bold: true, anchorX: "center", anchorY: "center", alpha: 220);
        r.DrawText("ZAP!", cx, cy + s * 40 / 100, zFs, (180, 220, 255), bold: true, anchorX: "center", anchorY: "center", alpha: 255);

        // Thunder symbol
        r.DrawText("⚡", cx + s * 28 / 100, cy + s * 30 / 100, Math.Max(6, s * 6 / 100), (255, 240, 100),
            anchorX: "center", anchorY: "center", alpha: 240);
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
            r.DrawLine(col, (cx, cy), (ex, ey), width: i % 2 == 0 ? 4 : 2, alpha: 255);
        }

        // Impact rings — vibrant concentric
        r.DrawCircle((255, 50, 20), (cx, cy), s * 38 / 100, width: 3, alpha: 255);
        r.DrawCircle((255, 100, 40), (cx, cy), s * 30 / 100, width: 2, alpha: 255);
        r.DrawCircle((255, 160, 60), (cx, cy), s * 22 / 100, width: 2, alpha: 255);
        r.DrawCircle((255, 220, 100), (cx, cy), s * 14 / 100, alpha: 255);
        r.DrawCircle((255, 255, 180), (cx, cy), s * 6 / 100, alpha: 255);

        // Fist — detailed with proper shading
        int fistW = s * 30 / 100, fistH = s * 26 / 100;
        int fx = cx - fistW / 2 - s * 3 / 100;
        int fy = cy - fistH / 2 - s * 4 / 100;
        // Shadow
        r.DrawRect((0, 0, 0), (fx + 4, fy + 4, fistW, fistH), alpha: 255);
        // Fist base — warm skin tone
        r.DrawRect((230, 180, 130), (fx, fy, fistW, fistH), alpha: 255);
        // Shading gradient
        for (int b = 0; b < 4; b++)
        {
            int bh = fistH / 4;
            int da = b < 2 ? 20 - b * 8 : 5;
            r.DrawRect((250, 200, 150), (fx + 2, fy + b * bh, fistW - 4, bh), alpha: da);
        }
        // Dark outline
        r.DrawRect((120, 80, 50), (fx, fy, fistW, fistH), width: 2, alpha: 255);

        // Knuckles — four prominent bumps
        for (int k = 0; k < 4; k++)
        {
            int kx = fx + fistW * (k + 1) / 5;
            r.DrawCircle((240, 195, 140), (kx, fy - 1), Math.Max(3, fistW / 7), alpha: 255);
            r.DrawCircle((255, 220, 170), (kx - 1, fy - 2), Math.Max(2, fistW / 10), alpha: 255);
            // Knuckle highlight
            r.DrawCircle((255, 240, 200), (kx - 1, fy - 3), Math.Max(1, fistW / 14), alpha: 255);
        }

        // Thumb — rounded
        int thumbR = Math.Max(4, fistW / 5);
        r.DrawCircle((220, 170, 120), (fx + fistW + s * 2 / 100, fy + fistH / 2), thumbR, alpha: 255);
        r.DrawCircle((240, 190, 140), (fx + fistW + s * 1 / 100, fy + fistH / 2 - 1), thumbR * 2 / 3, alpha: 255);
        // Thumbnail
        r.DrawCircle((255, 230, 200), (fx + fistW + s * 3 / 100, fy + fistH / 2 - thumbR / 2), Math.Max(1, thumbR / 3), alpha: 255);

        // Wrist/arm behind
        r.DrawRect((220, 170, 120), (fx + fistW - 4, fy + 4, s * 12 / 100, fistH - 8), alpha: 255);
        r.DrawRect((200, 150, 100), (fx + fistW - 4, fy + 4, s * 12 / 100, fistH - 8), width: 1, alpha: 255);

        // Speed/motion lines — coming from behind fist
        for (int i = 0; i < 8; i++)
        {
            int ly = cy - s * 24 / 100 + i * s * 7 / 100;
            int lx = cx + s * 22 / 100 + i * s * 2 / 100;
            int ll = s * (10 + (i % 3) * 4) / 100;
            r.DrawLine((255, 200, 80), (lx, ly), (lx + ll, ly), width: 2, alpha: 255 - i * 2);
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
            r.DrawLine((255, 255, 0), (powX, powY), (ex, ey), width: 2, alpha: 255);
        }
        int powFs = Math.Max(8, s * 12 / 100);
        r.DrawText("POW!", powX + 1, powY + 1, powFs, (0, 0, 0), bold: true, anchorX: "center", anchorY: "center", alpha: 255);
        r.DrawText("POW!", powX, powY, powFs, (255, 255, 0), bold: true, anchorX: "center", anchorY: "center", alpha: 255);

        // Debris chunks flying
        for (int i = 0; i < 6; i++)
        {
            double ang = i * 1.05 + 0.3;
            int dist = s * (20 + i * 4) / 100;
            int dx = cx + (int)(Math.Cos(ang) * dist);
            int dy = cy + (int)(Math.Sin(ang) * dist * 0.7);
            int ds = Math.Max(2, s * (2 + i % 2) / 100);
            r.DrawRect((200, 160, 100), (dx, dy, ds, ds), alpha: 255);
        }

        // Bold cartoon outline on fist
        DrawBoldRectOutline(r, fx, fy, fistW, fistH, 255);

        // Comic book halftone dots behind POW text
        DrawDotPattern(r, powX - s * 10 / 100, powY - s * 8 / 100, s * 20 / 100, s * 16 / 100,
            (255, 255, 0), 1, 255, spacing: s * 5 / 100);

        // More comic text — WHAM!
        int whamFs = Math.Max(6, s * 7 / 100);
        r.DrawText("WHAM!", cx - s * 20 / 100, cy - s * 24 / 100, whamFs, (0, 0, 0), bold: true, anchorX: "center", anchorY: "center", alpha: 255);
        r.DrawText("WHAM!", cx - s * 20 / 100 - 1, cy - s * 24 / 100 - 1, whamFs, (255, 100, 0), bold: true, anchorX: "center", anchorY: "center", alpha: 255);

        // Tooth flying out (cartoon violence)
        r.DrawCircle((255, 255, 240), (cx + s * 26 / 100, cy - s * 16 / 100), Math.Max(2, s * 2 / 100), alpha: 255);
        DrawTriangle(r, cx + s * 25 / 100, cy - s * 16 / 100, Math.Max(2, s * 2 / 100), (255, 255, 240), 200);

        // Sweat drops flying off fist
        DrawSweatDrops(r, cx + s * 14 / 100, cy - s * 18 / 100, s, 3);

        // Additional vibrant impact colors — concentric rings
        r.DrawCircle((0, 200, 255), (cx, cy), s * 36 / 100, width: 2, alpha: 255);
        r.DrawCircle((200, 0, 255), (cx, cy), s * 40 / 100, width: 1, alpha: 255);

        // Action speed lines — thick, radiating
        for (int i = 0; i < 6; i++)
        {
            int ly = cy - s * 20 / 100 + i * s * 8 / 100;
            r.DrawLine((255, 220, 100), (cx + s * 30 / 100, ly), (cx + s * 42 / 100, ly), width: 2, alpha: 255 - i * 2);
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

        // === Dark tech/industrial gradient background ===
        for (int row = 0; row < h; row++)
        {
            float t = (float)row / h;
            int rv = (int)(15 + 20 * t);
            int gv = (int)(20 + 25 * t);
            int bv = (int)(25 + 30 * t);
            r.DrawRect((rv, gv, bv), (x, y + row, w, 1), alpha: 240);
        }
        // Circuit board traces in background
        for (int trace = 0; trace < 6; trace++)
        {
            int ty = y + s * 6 / 100 + trace * s * 14 / 100;
            int tx1 = x + s * (3 + trace * 5 % 20) / 100;
            int tx2 = x + w - s * (5 + trace * 3 % 15) / 100;
            r.DrawLine((40, 80, 50), (tx1, ty), (tx2, ty), width: 1, alpha: 160 - trace * 12);
            // Trace corners
            r.DrawRect((40, 80, 50), (tx2 - 2, ty - 2, 4, 4), alpha: 140 - trace * 10);
        }

        // Colored wires — gradient filled
        for (int i = 0; i < 4; i++)
        {
            int wy = cy - s * 6 / 100 + (i - 2) * s * 10 / 100;
            var wireCol = i == 1 ? (200, 40, 40) : i == 2 ? (40, 40, 200) : i == 0 ? (40, 180, 40) : (200, 200, 40);
            // Wire shadow
            r.DrawLine((0, 0, 0), (x + s * 5 / 100, wy + 2), (x + w - s * 5 / 100, wy + 2), width: 3, alpha: 140);
            // Wire body
            r.DrawLine(wireCol, (x + s * 5 / 100, wy), (x + w - s * 5 / 100, wy), width: 3, alpha: 255);
            // Wire highlight
            r.DrawLine((Math.Min(255, wireCol.Item1 + 60), Math.Min(255, wireCol.Item2 + 60), Math.Min(255, wireCol.Item3 + 60)),
                (x + s * 5 / 100, wy - 1), (x + w - s * 5 / 100, wy - 1), width: 1, alpha: 180);
        }

        // Spark glow at cutting point — layered radiant burst
        int wireY = cy - s * 6 / 100;
        for (int glow = 4; glow >= 0; glow--)
        {
            int gr = s * (16 - glow * 3) / 100;
            r.DrawCircle(((int)(60 + glow * 35), (int)(200 + glow * 14), (int)(120 + glow * 28)), (cx, wireY), Math.Max(2, gr), alpha: 160 + glow * 20);
        }

        // THE red wire being cut
        r.DrawLine((200, 40, 40), (x + s * 8 / 100, wireY), (cx - s * 7 / 100, wireY), width: 3, alpha: 255);
        r.DrawLine((200, 40, 40), (cx + s * 7 / 100, wireY), (x + w - s * 8 / 100, wireY), width: 3, alpha: 255);
        // Wire break sparks
        for (int i = 0; i < 10; i++)
        {
            double ang = i * Math.PI / 5 + 0.15;
            int len = s * (3 + (i % 4) * 2) / 100;
            int sx0 = cx + (int)(Math.Cos(ang) * len);
            int sy0 = wireY + (int)(Math.Sin(ang) * len);
            r.DrawLine((255, 255, 180), (cx, wireY), (sx0, sy0), width: 1, alpha: 240 - i * 12);
        }
        // Wire insulation
        r.DrawCircle((200, 40, 40), (cx - s * 7 / 100, wireY), Math.Max(2, s * 2 / 100), alpha: 255);
        r.DrawCircle((200, 40, 40), (cx + s * 7 / 100, wireY), Math.Max(2, s * 2 / 100), alpha: 255);
        r.DrawCircle((220, 160, 60), (cx - s * 6 / 100, wireY), Math.Max(1, s * 1 / 100), alpha: 255);
        r.DrawCircle((220, 160, 60), (cx + s * 6 / 100, wireY), Math.Max(1, s * 1 / 100), alpha: 255);

        // Pliers — gradient filled handles
        // Handle 1 (lower-left)
        for (int lw = 5; lw >= 1; lw--)
        {
            int bri = 40 + lw * 12;
            r.DrawLine((bri, bri, bri + 10), (cx - s * 22 / 100, cy + s * 32 / 100), (cx - s * 3 / 100, cy - s * 4 / 100), width: lw, alpha: 255);
        }
        // Handle 2 (lower-right)
        for (int lw = 5; lw >= 1; lw--)
        {
            int bri = 40 + lw * 12;
            r.DrawLine((bri, bri, bri + 10), (cx + s * 22 / 100, cy + s * 32 / 100), (cx + s * 3 / 100, cy - s * 4 / 100), width: lw, alpha: 255);
        }

        // Pivot bolt — detailed
        int pivotR = Math.Max(4, s * 4 / 100);
        r.DrawCircle((60, 60, 70), (cx + 2, cy + s * 4 / 100 + 2), pivotR + 1, alpha: 180);
        for (int i = pivotR + 1; i >= 0; i--)
        {
            float t = (float)i / (pivotR + 1);
            r.DrawCircle(((int)(90 + 100 * t), (int)(90 + 100 * t), (int)(100 + 100 * t)), (cx, cy + s * 4 / 100), i, alpha: 255);
        }
        r.DrawRect((80, 80, 90), (cx - pivotR / 3, cy + s * 4 / 100 - 1, pivotR * 2 / 3, 2), alpha: 255);

        // Jaw tips with gradient
        for (int jaw = 0; jaw < 2; jaw++)
        {
            int jx = cx + (jaw == 0 ? -1 : 1) * s * 4 / 100;
            for (int i = s * 3 / 100; i >= 0; i--)
            {
                float t = (float)i / (s * 3 / 100);
                r.DrawCircle(((int)(80 + 40 * t), (int)(80 + 40 * t), (int)(95 + 30 * t)), (jx, cy - s * 6 / 100), Math.Max(1, i), alpha: 255);
            }
        }
        r.DrawLine((200, 200, 220), (cx - s * 3 / 100, cy - s * 8 / 100), (cx + s * 3 / 100, cy - s * 8 / 100), width: 1, alpha: 240);

        // Rubber grips — gradient filled
        int gripW = s * 7 / 100, gripH = s * 16 / 100;
        for (int grip = 0; grip < 2; grip++)
        {
            int gx = grip == 0 ? cx - s * 24 / 100 : cx + s * 17 / 100;
            for (int row = 0; row < gripH; row++)
            {
                float t = (float)row / gripH;
                int gv2 = (int)(140 + 50 * (1 - t));
                r.DrawRect((30, gv2, 60 + (int)(30 * t)), (gx, cy + s * 22 / 100 + row, gripW, 1), alpha: 255);
            }
            // Grip ridges
            for (int ridge = 0; ridge < 5; ridge++)
            {
                int gy = cy + s * 23 / 100 + ridge * (gripH / 5);
                r.DrawLine((60, 200, 110), (gx, gy), (gx + gripW, gy), width: 1, alpha: 220);
            }
        }

        // Timer display — bigger with gradient
        int timerX = x + s * 5 / 100, timerY = y + h - s * 16 / 100;
        int timerW = s * 22 / 100, timerH = s * 10 / 100;
        r.DrawRect((0, 0, 0), (timerX + 2, timerY + 2, timerW, timerH), alpha: 200);
        for (int row = 0; row < timerH; row++)
        {
            float t = (float)row / timerH;
            r.DrawRect(((int)(20 + 10 * t), (int)(20 + 10 * t), (int)(25 + 10 * t)), (timerX, timerY + row, timerW, 1), alpha: 255);
        }
        r.DrawRect((80, 80, 80), (timerX, timerY, timerW, timerH), width: 1, alpha: 255);
        int timerFs = Math.Max(7, s * 7 / 100);
        r.DrawText("0:03", timerX + timerW / 2, timerY + timerH / 2, timerFs, (255, 40, 40),
            bold: true, anchorX: "center", anchorY: "center", alpha: 255);
        // Blinking LED
        r.DrawCircle((255, 0, 0), (timerX + timerW - s * 2 / 100, timerY + s * 2 / 100), 3, alpha: 255);
        r.DrawCircle((255, 100, 100), (timerX + timerW - s * 2 / 100, timerY + s * 2 / 100), 5, alpha: 160);

        // Sweat drops — tense moment
        DrawSweatDrops(r, cx + s * 26 / 100, cy - s * 14 / 100, s, 3);

        // Sparkle at cut point
        DrawSparkle(r, cx, wireY, Math.Max(3, s * 4 / 100), (200, 255, 200), 240);
        DrawSparkle(r, cx - s * 8 / 100, wireY, s * 2 / 100, (255, 255, 150), 220);

        // Embossed "SNIP!" text
        int snFs = Math.Max(5, s * 4 / 100);
        r.DrawText("SNIP!", cx + 1, cy + s * 40 / 100 + 1, snFs, (10, 20, 15), bold: true, anchorX: "center", anchorY: "center", alpha: 220);
        r.DrawText("SNIP!", cx, cy + s * 40 / 100, snFs, (120, 255, 180), bold: true, anchorX: "center", anchorY: "center", alpha: 255);

        // Warning icon
        r.DrawText("⚠", x + w - s * 10 / 100, y + h - s * 10 / 100, Math.Max(6, s * 6 / 100), (255, 200, 60),
            anchorX: "center", anchorY: "center", alpha: 240);
    }

    private static void DrawDEF_Shield(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // === Noble stone hall gradient background ===
        for (int row = 0; row < h; row++)
        {
            float t = (float)row / h;
            int rv = (int)(30 + 40 * t);
            int gv = (int)(25 + 35 * t);
            int bv = (int)(45 + 50 * t);
            r.DrawRect((rv, gv, bv), (x, y + row, w, 1), alpha: 240);
        }

        // Protective energy barrier — glowing concentric arcs
        for (int arc = 5; arc >= 0; arc--)
        {
            int ar = s * (36 + arc * 4) / 100;
            int gv2 = 180 + arc * 15;
            r.DrawCircle(((int)(40 + arc * 8), Math.Min(255, gv2), (int)(120 + arc * 20)), (cx, cy), ar, width: 2, alpha: 200 - arc * 18);
        }

        // Energy particles along barrier
        for (int i = 0; i < 12; i++)
        {
            double ang = i * Math.PI / 6 + 0.3;
            int dist = s * (34 + i % 3 * 3) / 100;
            int px = cx + (int)(Math.Cos(ang) * dist);
            int py = cy + (int)(Math.Sin(ang) * dist);
            r.DrawCircle((120, 255, 180), (px, py), Math.Max(1, 3 - i / 4), alpha: 220 - i * 10);
        }

        // === Shield body — rich heraldic shape with gradient ===
        int shW = s * 44 / 100, shH = s * 54 / 100;
        int shX = cx - shW / 2, shY = cy - shH * 38 / 100;

        // Shadow
        r.DrawRect((0, 0, 0), (shX + 4, shY + 4, shW, shH * 65 / 100), alpha: 200);

        // Main shield — rich gradient fill
        for (int row = 0; row < shH * 65 / 100; row++)
        {
            float t = (float)row / (shH * 65 / 100);
            int rr = (int)(30 + 35 * (1f - t));
            int gg = (int)(110 + 50 * (1f - t));
            int bb = (int)(50 + 40 * (1f - t));
            r.DrawRect((rr, gg, bb), (shX, shY + row, shW, 1), alpha: 255);
        }
        // Pointed bottom with gradient
        for (int p = 0; p < 14; p++)
        {
            int pw = shW * (14 - p) / 14;
            int py = shY + shH * 65 / 100 + p * (shH * 35 / 100) / 14;
            float t = (float)p / 14;
            r.DrawRect(((int)(35 + 25 * t), (int)(125 - 35 * t), (int)(55 - 10 * t)),
                (cx - pw / 2, py, pw, shH * 35 / 100 / 14 + 1), alpha: 250 - p * 5);
        }

        // Shield border — metallic gold with depth
        r.DrawRect((160, 130, 40), (shX - 1, shY - 1, shW + 2, shH * 65 / 100 + 2), width: 1, alpha: 255);
        r.DrawRect((220, 190, 70), (shX, shY, shW, shH * 65 / 100), width: 2, alpha: 255);
        r.DrawRect((255, 220, 100), (shX + 1, shY + 1, shW - 2, shH * 65 / 100 - 2), width: 1, alpha: 200);

        // Diagonal cross division — heraldic gold
        r.DrawLine((220, 190, 70), (shX, shY), (cx, cy + shH * 25 / 100), width: 2, alpha: 255);
        r.DrawLine((220, 190, 70), (shX + shW, shY), (cx, cy + shH * 25 / 100), width: 2, alpha: 255);

        // Cat paw emblem in center — gradient filled
        int emblCy = cy - s * 2 / 100;
        for (int i = s * 8 / 100; i >= 0; i--)
        {
            float t = (float)i / (s * 8 / 100);
            r.DrawCircle(((int)(180 + 40 * t), (int)(150 + 40 * t), (int)(40 + 30 * t)), (cx, emblCy + s * 3 / 100), Math.Max(1, i), alpha: 255);
        }
        // Toe beans
        int beanR = Math.Max(2, s * 3 / 100);
        r.DrawCircle((240, 210, 100), (cx - s * 4 / 100, emblCy - s * 2 / 100), beanR, alpha: 255);
        r.DrawCircle((240, 210, 100), (cx + s * 4 / 100, emblCy - s * 2 / 100), beanR, alpha: 255);
        r.DrawCircle((240, 210, 100), (cx, emblCy - s * 5 / 100), beanR, alpha: 255);

        // Specular highlight — top left
        r.DrawCircle((180, 255, 220), (shX + shW / 5, shY + shH / 8), Math.Max(3, shW / 6), alpha: 180);

        // Rivets along top border
        for (int riv = 0; riv < 6; riv++)
        {
            int rivX = shX + shW * (riv + 1) / 7;
            r.DrawCircle((0, 0, 0), (rivX + 1, shY + 3), Math.Max(1, s * 12 / 1000), alpha: 160);
            r.DrawCircle((240, 210, 100), (rivX, shY + 2), Math.Max(1, s * 12 / 1000), alpha: 255);
            r.DrawCircle((255, 240, 140), (rivX - 1, shY + 1), 1, alpha: 200);
        }

        // Bold outlines
        DrawBoldRectOutline(r, shX, shY, shW, shH * 65 / 100, 240);

        // Laurel vine decorations with gradient leaves
        for (int side = -1; side <= 1; side += 2)
        {
            int vineX = cx + side * (shW / 2 + s * 8 / 100);
            r.DrawLine((40, 100, 40), (vineX, shY), (vineX, shY + shH * 80 / 100), width: 2, alpha: 220);
            for (int leaf = 0; leaf < 5; leaf++)
            {
                int ly = shY + leaf * shH / 5;
                int lSize = Math.Max(2, s * 3 / 100);
                r.DrawCircle((50, 140, 70), (vineX + side * 2, ly), lSize, alpha: 240);
                r.DrawCircle((70, 180, 90), (vineX + side * 3, ly - 1), Math.Max(1, lSize * 55 / 100), alpha: 220);
            }
        }

        // Filigree circles on shield
        r.DrawCircle((220, 190, 70), (cx, shY + shH / 4), shW / 5, width: 1, alpha: 200);
        r.DrawCircle((220, 190, 70), (cx, shY + shH * 60 / 100), shW / 6, width: 1, alpha: 200);

        // Energy particles on shield surface
        DrawDotPattern(r, shX + 4, shY + 4, shW - 8, shH * 60 / 100,
            (100, 255, 180), 1, 160, spacing: s * 6 / 100);

        // Sparkle accents
        DrawSparkle(r, shX - s * 2 / 100, shY + s * 2 / 100, s * 2 / 100, (200, 255, 220), 230);
        DrawSparkle(r, shX + shW + s * 2 / 100, shY + s * 2 / 100, s * 18 / 1000, (200, 255, 220), 220);
        DrawSparkle(r, cx, shY + shH * 92 / 100, Math.Max(3, s * 3 / 100), (180, 255, 200), 230);

        // Embossed "DEFEND" text
        int dfFs = Math.Max(5, s * 4 / 100);
        r.DrawText("DEFEND", cx + 1, cy + s * 40 / 100 + 1, dfFs, (20, 40, 25), bold: true, anchorX: "center", anchorY: "center", alpha: 220);
        r.DrawText("DEFEND", cx, cy + s * 40 / 100, dfFs, (120, 255, 160), bold: true, anchorX: "center", anchorY: "center", alpha: 255);

        // Shield icon
        r.DrawText("🛡", cx + s * 30 / 100, cy - s * 30 / 100, Math.Max(5, s * 5 / 100), (200, 220, 160),
            anchorX: "center", anchorY: "center", alpha: 230);
    }

    private static void DrawDEF_LaserPointer(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // === Dark room gradient background ===
        for (int row = 0; row < h; row++)
        {
            float t = (float)row / h;
            int rv = (int)(15 + 20 * t);
            int gv = (int)(12 + 18 * t);
            int bv = (int)(25 + 30 * t);
            r.DrawRect((rv, gv, bv), (x, y + row, w, 1), alpha: 240);
        }
        // Floor surface at bottom
        int floorY = cy + s * 20 / 100;
        for (int row = 0; row < s * 25 / 100; row++)
        {
            float t = (float)row / (s * 25 / 100);
            int bri = (int)(35 + 15 * t);
            r.DrawRect((bri, bri - 3, bri + 5), (x, floorY + row, w, 1), alpha: 230);
        }
        // Floor line
        r.DrawLine((60, 55, 70), (x + s * 3 / 100, floorY), (x + w - s * 3 / 100, floorY), width: 1, alpha: 200);

        // Moonlight glow from upper right
        for (int glow = 4; glow >= 0; glow--)
        {
            int gr = s * (20 - glow * 4) / 100;
            r.DrawCircle(((int)(30 + glow * 8), (int)(30 + glow * 10), (int)(50 + glow * 15)),
                (x + w - s * 10 / 100, y + s * 8 / 100), gr, alpha: 80 + glow * 15);
        }

        // Red laser dot — pulsing concentric glow
        int dotX = cx - s * 12 / 100, dotY = cy - s * 20 / 100;
        r.DrawCircle((255, 0, 0), (dotX, dotY), s * 16 / 100, alpha: 140);
        r.DrawCircle((255, 20, 20), (dotX, dotY), s * 10 / 100, alpha: 180);
        r.DrawCircle((255, 60, 60), (dotX, dotY), s * 6 / 100, alpha: 220);
        r.DrawCircle((255, 120, 120), (dotX, dotY), s * 3 / 100, alpha: 240);
        r.DrawCircle((255, 200, 200), (dotX, dotY), Math.Max(1, s * 1 / 100 + 1), alpha: 255);

        // Laser beam — from device to dot
        int lpX = cx + s * 12 / 100, lpY = cy + s * 24 / 100;
        r.DrawLine((255, 30, 30), (lpX, lpY), (dotX, dotY), width: 4, alpha: 180);
        r.DrawLine((255, 60, 60), (lpX, lpY), (dotX, dotY), width: 2, alpha: 220);
        r.DrawLine((255, 140, 140), (lpX, lpY), (dotX, dotY), width: 1, alpha: 255);

        // Laser pointer device — gradient cylinder
        int devW = s * 32 / 100, devH = s * 8 / 100;
        r.DrawRect((0, 0, 0), (lpX + 3, lpY + 3, devW, devH), alpha: 180);
        for (int row = 0; row < devH; row++)
        {
            float t = (float)row / devH;
            int bri = (int)(50 + 30 * (1 - Math.Abs(t - 0.3) * 2));
            r.DrawRect((bri, bri, bri + 10), (lpX, lpY + row, devW, 1), alpha: 255);
        }
        // Metallic bands
        r.DrawRect((110, 110, 125), (lpX + 2, lpY + 1, devW - 4, 1), alpha: 220);
        r.DrawRect((90, 90, 100), (lpX + 2, lpY + devH - 2, devW - 4, 1), alpha: 220);
        // Clip
        r.DrawRect((90, 90, 100), (lpX + devW - s * 4 / 100, lpY - s * 4 / 100, s * 2 / 100, s * 4 / 100 + devH), alpha: 255);
        // Button
        r.DrawCircle((200, 50, 50), (lpX + devW * 35 / 100, lpY + devH / 2), Math.Max(2, devH / 3), alpha: 255);
        r.DrawCircle((255, 80, 80), (lpX + devW * 35 / 100 - 1, lpY + devH / 2 - 1), Math.Max(1, devH / 5), alpha: 255);
        // Lens
        r.DrawCircle((255, 100, 100), (lpX - 1, lpY + devH / 2), Math.Max(2, devH / 3), alpha: 255);

        // Cat silhouette chasing dot — detailed
        int catCx = cx + s * 2 / 100, catCy = cy + s * 2 / 100;
        // Body — crouched/pouncing with gradient
        for (int i = s * 12 / 100; i >= 0; i--)
        {
            float t = (float)i / (s * 12 / 100);
            r.DrawCircle(((int)(160 + 30 * t), (int)(120 + 30 * t), (int)(70 + 25 * t)), (catCx, catCy), Math.Max(1, i), alpha: 255);
        }
        for (int i = s * 8 / 100; i >= 0; i--)
        {
            float t = (float)i / (s * 8 / 100);
            r.DrawCircle(((int)(180 + 25 * t), (int)(140 + 25 * t), (int)(90 + 20 * t)), (catCx - s * 2 / 100, catCy - s * 2 / 100), Math.Max(1, i), alpha: 255);
        }
        // Head
        int headCx = catCx - s * 10 / 100, headCy = catCy - s * 8 / 100;
        for (int i = s * 8 / 100; i >= 0; i--)
        {
            float t = (float)i / (s * 8 / 100);
            r.DrawCircle(((int)(170 + 25 * t), (int)(130 + 25 * t), (int)(80 + 25 * t)), (headCx, headCy), Math.Max(1, i), alpha: 255);
        }
        // Ears
        DrawTriangle(r, headCx - s * 8 / 100, headCy - s * 12 / 100, s * 6 / 100, (190, 150, 100), 230);
        DrawTriangle(r, headCx + s * 2 / 100, headCy - s * 12 / 100, s * 6 / 100, (190, 150, 100), 230);
        DrawTriangle(r, headCx - s * 7 / 100, headCy - s * 10 / 100, s * 4 / 100, (220, 150, 130), 210);
        DrawTriangle(r, headCx + s * 3 / 100, headCy - s * 10 / 100, s * 4 / 100, (220, 150, 130), 210);
        // Eyes — wide, fixated
        r.DrawCircle((255, 255, 200), (headCx - s * 3 / 100, headCy - s * 2 / 100), Math.Max(2, s * 3 / 100), alpha: 255);
        r.DrawCircle((255, 255, 200), (headCx + s * 3 / 100, headCy - s * 2 / 100), Math.Max(2, s * 3 / 100), alpha: 255);
        r.DrawCircle((0, 0, 0), (headCx - s * 3 / 100, headCy - s * 2 / 100), Math.Max(1, s * 2 / 100), alpha: 255);
        r.DrawCircle((0, 0, 0), (headCx + s * 3 / 100, headCy - s * 2 / 100), Math.Max(1, s * 2 / 100), alpha: 255);
        // Eye highlights
        r.DrawCircle((255, 255, 255), (headCx - s * 4 / 100, headCy - s * 3 / 100), 1, alpha: 240);
        r.DrawCircle((255, 255, 255), (headCx + s * 2 / 100, headCy - s * 3 / 100), 1, alpha: 240);
        // Nose
        DrawTriangle(r, headCx - s * 1 / 100, headCy + s * 2 / 100, Math.Max(2, s * 2 / 100), (200, 120, 100), 220);
        // Whiskers
        r.DrawLine((160, 120, 80), (headCx - s * 5 / 100, headCy + s * 2 / 100), (headCx - s * 14 / 100, headCy), width: 1, alpha: 240);
        r.DrawLine((160, 120, 80), (headCx - s * 5 / 100, headCy + s * 3 / 100), (headCx - s * 14 / 100, headCy + s * 4 / 100), width: 1, alpha: 240);

        // Front paw reaching
        r.DrawLine((180, 140, 90), (catCx - s * 8 / 100, catCy + s * 4 / 100), (dotX + s * 4 / 100, dotY + s * 6 / 100), width: 3, alpha: 255);
        r.DrawCircle((200, 160, 120), (dotX + s * 5 / 100, dotY + s * 7 / 100), Math.Max(2, s * 3 / 100), alpha: 255);
        r.DrawCircle((220, 180, 140), (dotX + s * 3 / 100, dotY + s * 5 / 100), Math.Max(1, s * 1 / 100), alpha: 240);
        r.DrawCircle((220, 180, 140), (dotX + s * 6 / 100, dotY + s * 5 / 100), Math.Max(1, s * 1 / 100), alpha: 240);

        // Tail — curved
        r.DrawLine((180, 140, 90), (catCx + s * 10 / 100, catCy), (catCx + s * 16 / 100, catCy - s * 12 / 100), width: 3, alpha: 255);
        r.DrawLine((180, 140, 90), (catCx + s * 16 / 100, catCy - s * 12 / 100), (catCx + s * 12 / 100, catCy - s * 16 / 100), width: 2, alpha: 255);

        // Cat outlines and fur
        DrawBoldCircleOutline(r, catCx, catCy, Math.Max(5, s * 12 / 100), 220);
        DrawBoldCircleOutline(r, headCx, headCy, Math.Max(4, s * 8 / 100), 220);
        DrawFurTexture(r, catCx, catCy, Math.Max(5, s * 12 / 100), 12, (160, 120, 70), 200);

        // Floor reflection of laser dot
        r.DrawCircle((255, 40, 40), (dotX, floorY + s * 4 / 100), s * 4 / 100, alpha: 120);
        r.DrawCircle((255, 80, 80), (dotX, floorY + s * 4 / 100), s * 2 / 100, alpha: 100);

        // Heart over cat
        r.DrawText("♥", catCx + s * 12 / 100, catCy - s * 16 / 100, Math.Max(5, s * 5 / 100), (255, 100, 150),
            anchorX: "center", anchorY: "center", alpha: 240);

        // Laser beam sparkle trail
        for (int i = 0; i < 5; i++)
        {
            float t = (i + 1) / 6f;
            int sx0 = (int)(lpX + (dotX - lpX) * t);
            int sy0 = (int)(lpY + (dotY - lpY) * t);
            DrawSparkle(r, sx0, sy0, Math.Max(2, s * 1 / 100 + 1), (255, 100, 100), 210 - i * 15);
        }

        // Paw print trail
        for (int i = 0; i < 3; i++)
        {
            int ppX = catCx + s * 18 / 100 + i * s * 6 / 100;
            int ppY = catCy + s * 12 / 100;
            r.DrawCircle((120, 90, 60), (ppX, ppY), 2, alpha: 180 - i * 30);
        }

        // Embossed "DISTRACT!" text
        int dFs = Math.Max(5, s * 35 / 1000);
        r.DrawText("DISTRACT!", cx + 1, cy + s * 40 / 100 + 1, dFs, (40, 10, 10), bold: true, anchorX: "center", anchorY: "center", alpha: 200);
        r.DrawText("DISTRACT!", cx, cy + s * 40 / 100, dFs, (255, 120, 120), bold: true, anchorX: "center", anchorY: "center", alpha: 250);
    }

    private static void DrawDEF_Catnip(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Dreamy swirl aura — multiple color rings
        r.DrawCircle((80, 220, 120), (cx, cy), s * 38 / 100, alpha: 255);
        r.DrawCircle((120, 200, 160), (cx, cy), s * 30 / 100, alpha: 255);
        r.DrawCircle((160, 220, 180), (cx + s * 3 / 100, cy - s * 3 / 100), s * 20 / 100, alpha: 255);

        // Pot/container for the catnip
        int potW = s * 20 / 100, potH = s * 16 / 100;
        int potX = cx - s * 4 / 100 - potW / 2, potY = cy + s * 14 / 100;
        // Pot shadow
        r.DrawCircle((0, 0, 0), (potX + potW / 2 + 2, potY + potH + 2), Math.Max(3, potW / 2), alpha: 255);
        // Pot body — terracotta
        r.DrawRect((180, 100, 60), (potX, potY, potW, potH), alpha: 255);
        r.DrawRect((200, 120, 70), (potX + 1, potY + 1, potW - 2, 3), alpha: 255); // rim highlight
        r.DrawRect((160, 80, 50), (potX + 2, potY + potH - 3, potW - 4, 2), alpha: 255); // bottom shadow
        // Pot rim
        r.DrawRect((200, 110, 65), (potX - 2, potY - 2, potW + 4, 4), alpha: 255);
        // Soil visible
        r.DrawRect((80, 50, 30), (potX + 2, potY + 1, potW - 4, 4), alpha: 255);

        // Catnip plant — rich stem with branches
        int stemBase = potY;
        r.DrawLine((50, 130, 50), (cx - s * 4 / 100, stemBase), (cx - s * 4 / 100, cy - s * 14 / 100), width: 3, alpha: 255);
        // Side branches
        r.DrawLine((60, 140, 60), (cx - s * 4 / 100, cy - s * 2 / 100), (cx - s * 14 / 100, cy - s * 8 / 100), width: 2, alpha: 255);
        r.DrawLine((60, 140, 60), (cx - s * 4 / 100, cy + s * 4 / 100), (cx + s * 6 / 100, cy), width: 2, alpha: 255);
        r.DrawLine((60, 140, 60), (cx - s * 4 / 100, cy - s * 8 / 100), (cx + s * 8 / 100, cy - s * 12 / 100), width: 2, alpha: 255);

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
            r.DrawCircle((60, 170, 60), (lx, ly), leafR, alpha: 255);
            r.DrawCircle((80, 200, 80), (lx + side * leafR / 3, ly - leafR / 4), leafR * 70 / 100, alpha: 255);
            // Leaf vein
            r.DrawLine((40, 120, 40), (lx - side * leafR * 60 / 100, ly), (lx + side * leafR * 60 / 100, ly), width: 1, alpha: 255);
            // Leaf highlights
            r.DrawCircle((100, 220, 100), (lx - side * leafR / 4, ly - leafR / 3), leafR / 3, alpha: 255);
        }

        // Flower clusters at top — purple/lavender
        int flowerCy = cy - s * 16 / 100;
        for (int f = 0; f < 5; f++)
        {
            double ang = f * Math.PI / 2.5 - Math.PI / 4;
            int fx = cx - s * 4 / 100 + (int)(Math.Cos(ang) * s * 4 / 100);
            int fy = flowerCy + (int)(Math.Sin(ang) * s * 3 / 100);
            r.DrawCircle((180, 120, 220), (fx, fy), Math.Max(2, s * 3 / 100), alpha: 255);
            r.DrawCircle((220, 160, 240), (fx, fy), Math.Max(1, s * 2 / 100), alpha: 255);
        }
        // Center of flower cluster
        r.DrawCircle((255, 220, 100), (cx - s * 4 / 100, flowerCy), Math.Max(1, s * 1 / 100 + 1), alpha: 255);

        // Happy cat — larger, more detailed
        int catCx = cx + s * 18 / 100, catCy = cy + s * 4 / 100;
        // Body
        r.DrawCircle((200, 165, 100), (catCx, catCy + s * 6 / 100), Math.Max(5, s * 10 / 100), alpha: 255);
        // Head — tilted happily
        r.DrawCircle((210, 175, 110), (catCx, catCy - s * 4 / 100), Math.Max(5, s * 9 / 100), alpha: 255);
        // Ears
        DrawTriangle(r, catCx - s * 8 / 100, catCy - s * 14 / 100, s * 6 / 100, (210, 175, 110), 210);
        DrawTriangle(r, catCx + s * 2 / 100, catCy - s * 14 / 100, s * 6 / 100, (210, 175, 110), 210);
        DrawTriangle(r, catCx - s * 7 / 100, catCy - s * 12 / 100, s * 4 / 100, (230, 150, 130), 200);
        DrawTriangle(r, catCx + s * 3 / 100, catCy - s * 12 / 100, s * 4 / 100, (230, 150, 130), 200);
        // Happy closed eyes (^ ^)
        r.DrawLine((80, 60, 40), (catCx - s * 5 / 100, catCy - s * 2 / 100),
            (catCx - s * 3 / 100, catCy - s * 5 / 100), width: 2, alpha: 255);
        r.DrawLine((80, 60, 40), (catCx - s * 3 / 100, catCy - s * 5 / 100),
            (catCx - s * 1 / 100, catCy - s * 2 / 100), width: 2, alpha: 255);
        r.DrawLine((80, 60, 40), (catCx + s * 1 / 100, catCy - s * 2 / 100),
            (catCx + s * 3 / 100, catCy - s * 5 / 100), width: 2, alpha: 255);
        r.DrawLine((80, 60, 40), (catCx + s * 3 / 100, catCy - s * 5 / 100),
            (catCx + s * 5 / 100, catCy - s * 2 / 100), width: 2, alpha: 255);
        // Wide smile
        r.DrawCircle((180, 100, 60), (catCx, catCy + s * 2 / 100), Math.Max(3, s * 4 / 100), width: 1, alpha: 255);
        // Blush marks
        r.DrawCircle((255, 150, 150), (catCx - s * 6 / 100, catCy + s * 1 / 100), Math.Max(2, s * 2 / 100), alpha: 255);
        r.DrawCircle((255, 150, 150), (catCx + s * 6 / 100, catCy + s * 1 / 100), Math.Max(2, s * 2 / 100), alpha: 255);
        // Tail curled happily
        r.DrawLine((200, 165, 100), (catCx + s * 8 / 100, catCy + s * 8 / 100), (catCx + s * 14 / 100, catCy + s * 4 / 100), width: 2, alpha: 255);
        r.DrawLine((200, 165, 100), (catCx + s * 14 / 100, catCy + s * 4 / 100), (catCx + s * 12 / 100, catCy), width: 2, alpha: 255);

        // Floating hearts
        r.DrawText("♥", cx - s * 24 / 100, cy - s * 28 / 100, Math.Max(8, s * 8 / 100), (255, 120, 160),
            anchorX: "center", anchorY: "center", alpha: 255);
        r.DrawText("♥", cx + s * 20 / 100, cy - s * 22 / 100, Math.Max(6, s * 6 / 100), (255, 140, 180),
            anchorX: "center", anchorY: "center", alpha: 255);

        // Sparkles
        for (int sp = 0; sp < 4; sp++)
        {
            int spx = cx + (sp * 37 - 55) % (s * 40 / 100) - s * 10 / 100;
            int spy = cy + (sp * 23 - 40) % (s * 30 / 100) - s * 18 / 100;
            r.DrawCircle((255, 255, 200), (spx, spy), 1, alpha: 255);
            r.DrawRect((255, 255, 200), (spx - 2, spy, 5, 1), alpha: 255);
            r.DrawRect((255, 255, 200), (spx, spy - 2, 1, 5), alpha: 255);
        }

        // Bold outlines on pot and cat
        DrawBoldRectOutline(r, potX, potY, potW, potH, 224);
        DrawBoldCircleOutline(r, catCx, catCy - s * 4 / 100, Math.Max(5, s * 9 / 100), 200);

        // Fur texture on happy cat
        DrawFurTexture(r, catCx, catCy, Math.Max(5, s * 10 / 100), 12, (180, 140, 70), 200);

        // Psychedelic swirl lines — cat is high on catnip
        for (int sw = 0; sw < 4; sw++)
        {
            double angle = sw * Math.PI / 2 + 0.5;
            int swr = s * (10 + sw * 4) / 100;
            int swx = catCx + (int)(Math.Cos(angle) * swr);
            int swy = catCy - s * 4 / 100 + (int)(Math.Sin(angle) * swr);
            r.DrawCircle((200, 150, 255), (swx, swy), Math.Max(2, s * 3 / 100), width: 1, alpha: 255 - sw * 2);
        }

        // Musical notes drifting (cat is purring)
        r.DrawText("♪", cx - s * 30 / 100, cy - s * 18 / 100, Math.Max(6, s * 6 / 100), (180, 120, 220),
            anchorX: "center", anchorY: "center", alpha: 255);
        r.DrawText("♫", cx + s * 26 / 100, cy - s * 26 / 100, Math.Max(5, s * 5 / 100), (200, 140, 240),
            anchorX: "center", anchorY: "center", alpha: 255);

        // Additional colorful flowers scattered
        (int fx, int fy, (int, int, int) fCol)[] extraFlowers = [
            (-s * 28 / 100, s * 16 / 100, (255, 180, 200)),
            (s * 28 / 100, -s * 14 / 100, (200, 200, 255)),
            (-s * 20 / 100, -s * 24 / 100, (255, 255, 150)),
        ];
        foreach (var (fx, fy, fCol) in extraFlowers)
        {
            int flx = cx + fx, fly = cy + fy;
            // Petals — 5 tiny circles around center
            for (int p = 0; p < 5; p++)
            {
                double pa = p * Math.PI * 2 / 5;
                int px = flx + (int)(Math.Cos(pa) * s * 2 / 100);
                int py = fly + (int)(Math.Sin(pa) * s * 2 / 100);
                r.DrawCircle(fCol, (px, py), Math.Max(1, s * 1 / 100 + 1), alpha: 255);
            }
            r.DrawCircle((255, 220, 80), (flx, fly), Math.Max(1, s / 100), alpha: 255);
        }

        // Butterfly near the plant
        int bfX = cx - s * 22 / 100, bfY = cy - s * 10 / 100;
        // Wings
        r.DrawCircle((100, 180, 255), (bfX - s * 2 / 100, bfY - s * 1 / 100), Math.Max(2, s * 2 / 100), alpha: 255);
        r.DrawCircle((255, 150, 200), (bfX + s * 2 / 100, bfY - s * 1 / 100), Math.Max(2, s * 2 / 100), alpha: 255);
        // Body
        r.DrawLine((60, 40, 30), (bfX, bfY - s * 2 / 100), (bfX, bfY + s * 2 / 100), width: 1, alpha: 255);
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

        // === Speed tunnel background — concentric rings converging to focal point ===
        int tunnelCx = cx + s * 8 / 100, tunnelCy = cy;
        for (int ring = 8; ring >= 0; ring--)
        {
            int rr = s * (42 - ring * 4) / 100;
            int rv = 20 + ring * 8;
            int gv = 15 + ring * 10;
            int bv = 40 + ring * 15;
            r.DrawCircle((rv, gv, bv), (tunnelCx, tunnelCy), rr, alpha: 220 - ring * 8);
        }
        // Radial speed streaks from focal point
        for (int ray = 0; ray < 16; ray++)
        {
            double ang = ray * Math.PI / 8;
            int innerR = s * 6 / 100;
            int outerR = s * (30 + (ray % 3) * 8) / 100;
            int rx1 = tunnelCx + (int)(Math.Cos(ang) * innerR);
            int ry1 = tunnelCy + (int)(Math.Sin(ang) * innerR);
            int rx2 = tunnelCx + (int)(Math.Cos(ang) * outerR);
            int ry2 = tunnelCy + (int)(Math.Sin(ang) * outerR);
            var rayCol = ray % 4 == 0 ? (80, 60, 140) : ray % 4 == 1 ? (60, 50, 120) : ray % 4 == 2 ? (100, 70, 160) : (50, 40, 110);
            r.DrawLine(rayCol, (rx1, ry1), (rx2, ry2), width: 1, alpha: 200 - ray * 5);
        }

        // === Speed streak particles — horizontal motion blur ===
        for (int st = 0; st < 14; st++)
        {
            int sy2 = y + s * 5 / 100 + st * s * 6 / 100;
            int sl = s * (12 + (st * 7) % 18) / 100;
            int sx2 = x + s * 2 / 100 + (st * 13) % (s * 8 / 100);
            // Color-banded streaks
            var sCol = st % 4 == 0 ? (255, 240, 60) : st % 4 == 1 ? (255, 180, 30) : st % 4 == 2 ? (255, 140, 0) : (255, 220, 100);
            r.DrawLine(sCol, (sx2, sy2), (sx2 + sl, sy2), width: 2, alpha: 220 - st * 5);
            // Thin highlight under each streak
            r.DrawLine((255, 255, 200), (sx2 + 2, sy2 + 1), (sx2 + sl - 2, sy2 + 1), width: 1, alpha: 120);
        }

        // === 3D beveled double chevron arrows ===
        for (int ch = 0; ch < 2; ch++)
        {
            int chOff = ch * s * 20 / 100 - s * 10 / 100;
            int ax = cx + chOff;

            // Shadow layer
            r.DrawLine((120, 80, 0), (ax - s * 14 / 100 + 3, cy - s * 24 / 100 + 3), (ax + s * 6 / 100 + 3, cy + 3), width: 8, alpha: 180);
            r.DrawLine((120, 80, 0), (ax - s * 14 / 100 + 3, cy + s * 24 / 100 + 3), (ax + s * 6 / 100 + 3, cy + 3), width: 8, alpha: 180);

            // Outer glow — warm orange
            r.DrawLine((255, 160, 0), (ax - s * 15 / 100, cy - s * 25 / 100), (ax + s * 7 / 100, cy), width: 9, alpha: 200);
            r.DrawLine((255, 160, 0), (ax - s * 15 / 100, cy + s * 25 / 100), (ax + s * 7 / 100, cy), width: 9, alpha: 200);

            // Main body — gradient layers (dark to light)
            for (int layer = 0; layer < 4; layer++)
            {
                int tw = 7 - layer;
                int tint = layer * 25;
                r.DrawLine((200 + tint / 4, 180 + tint / 2, 20 + tint), (ax - s * 14 / 100, cy - s * 24 / 100), (ax + s * 6 / 100, cy), width: tw, alpha: 255);
                r.DrawLine((200 + tint / 4, 180 + tint / 2, 20 + tint), (ax - s * 14 / 100, cy + s * 24 / 100), (ax + s * 6 / 100, cy), width: tw, alpha: 255);
            }

            // Bright highlight — top edge
            r.DrawLine((255, 255, 200), (ax - s * 13 / 100, cy - s * 22 / 100), (ax + s * 5 / 100, cy - 1), width: 1, alpha: 255);
            // Bottom dark edge
            r.DrawLine((180, 120, 0), (ax - s * 13 / 100, cy + s * 23 / 100), (ax + s * 5 / 100, cy + 1), width: 1, alpha: 200);

            // Bold black outline
            r.DrawLine((0, 0, 0), (ax - s * 14 / 100, cy - s * 24 / 100), (ax + s * 6 / 100, cy), width: 2, alpha: 255);
            r.DrawLine((0, 0, 0), (ax - s * 14 / 100, cy + s * 24 / 100), (ax + s * 6 / 100, cy), width: 2, alpha: 255);
        }

        // === Small clock face ===
        int clockR = s * 8 / 100;
        int clockX = x + w - s * 14 / 100, clockY = y + h - s * 14 / 100;
        // Clock body
        r.DrawCircle((240, 230, 210), (clockX, clockY), clockR, alpha: 240);
        r.DrawCircle((200, 190, 170), (clockX, clockY), clockR, width: 2, alpha: 255);
        // Clock face — hour markers
        for (int hr = 0; hr < 12; hr++)
        {
            double hAng = hr * Math.PI / 6 - Math.PI / 2;
            int hx = clockX + (int)(Math.Cos(hAng) * clockR * 8 / 10);
            int hy = clockY + (int)(Math.Sin(hAng) * clockR * 8 / 10);
            r.DrawCircle((80, 60, 40), (hx, hy), 1, alpha: 255);
        }
        // Clock hands — skewed fast
        r.DrawLine((40, 30, 20), (clockX, clockY), (clockX + clockR * 5 / 10, clockY - clockR * 3 / 10), width: 2, alpha: 255);
        r.DrawLine((40, 30, 20), (clockX, clockY), (clockX - clockR * 2 / 10, clockY - clockR * 6 / 10), width: 1, alpha: 255);
        // Center pin
        r.DrawCircle((200, 160, 40), (clockX, clockY), Math.Max(1, s * 1 / 100), alpha: 255);
        // Motion blur ring around clock
        r.DrawCircle((255, 200, 60), (clockX, clockY), clockR + s * 2 / 100, width: 1, alpha: 160);

        // === "SKIP!" text — bold embossed ===
        int speedFs = Math.Max(7, s * 7 / 100);
        r.DrawText("SKIP!", cx + 2, cy + s * 34 / 100 + 2, speedFs, (80, 50, 0), bold: true, anchorX: "center", anchorY: "center", alpha: 220);
        r.DrawText("SKIP!", cx, cy + s * 34 / 100, speedFs, (255, 230, 60), bold: true, anchorX: "center", anchorY: "center", alpha: 255);

        // === Wind whoosh particles with trails ===
        for (int wp = 0; wp < 8; wp++)
        {
            int wpx = cx - s * 34 / 100 - wp * s * 1 / 100 + (wp * 11 % 7) * s * 1 / 100;
            int wpy = cy - s * 20 / 100 + wp * s * 5 / 100;
            r.DrawCircle((255, 240, 160), (wpx, wpy), Math.Max(1, 3 - wp / 3), alpha: 240 - wp * 15);
            // Trail
            r.DrawLine((255, 220, 100), (wpx + s * 2 / 100, wpy), (wpx + s * 6 / 100, wpy), width: 1, alpha: 160 - wp * 10);
        }

        // === Excited cat face surfing the speed ===
        DrawMiniCatFace(r, x + w - s * 10 / 100, y + s * 10 / 100, Math.Max(4, s * 5 / 100), (220, 180, 100), 255);
        // Speed lines behind cat
        for (int sl = 0; sl < 3; sl++)
        {
            int sly = y + s * 8 / 100 + sl * s * 3 / 100;
            r.DrawLine((200, 160, 60), (x + w - s * 18 / 100, sly), (x + w - s * 14 / 100, sly), width: 1, alpha: 200);
        }

        // === Lightning bolt accent ===
        r.DrawText("⚡", cx - s * 28 / 100, cy - s * 22 / 100, Math.Max(7, s * 7 / 100), (255, 220, 40),
            anchorX: "center", anchorY: "center", alpha: 255);

        // Sparkles at arrow tips
        DrawSparkle(r, cx + s * 16 / 100, cy, s * 3 / 100, (255, 255, 200), 240);
        DrawSparkle(r, cx - s * 6 / 100, cy, s * 2 / 100, (255, 240, 160), 220);
    }

    private static void DrawSKIP_RunningCat(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // === GRADIENT SUNSET SKY BACKGROUND ===
        for (int row = 0; row < h; row++)
        {
            float t = (float)row / h;
            int rr = (int)(60 + 160 * t);   // deep blue → warm orange
            int gg = (int)(120 + 100 * t);
            int bb = (int)(200 - 140 * t);
            r.DrawRect((rr, gg, bb), (x, y + row, w, 1), alpha: 255);
        }

        // Distant hills silhouette
        for (int px = 0; px < w; px++)
        {
            double hillH = Math.Sin(px * 0.03) * s * 8 / 100 + Math.Sin(px * 0.07 + 1.5) * s * 4 / 100;
            int hillTop = cy + s * 10 / 100 - (int)hillH;
            int hillBot = cy + s * 22 / 100;
            if (hillTop < hillBot)
                r.DrawRect((70, 100, 60), (x + px, hillTop, 1, hillBot - hillTop), alpha: 200);
        }

        // Ground — rich gradient terrain
        int groundY = cy + s * 22 / 100;
        for (int row = 0; row < h - (groundY - y); row++)
        {
            float t = (float)row / (h - (groundY - y) + 1);
            int rr = (int)(100 - 30 * t);
            int gg = (int)(130 - 50 * t);
            int bb = (int)(60 - 20 * t);
            r.DrawRect((rr, gg, bb), (x, groundY + row, w, 1), alpha: 255);
        }
        // Ground surface line
        r.DrawLine((140, 120, 70), (x, groundY), (x + w, groundY), width: 2, alpha: 255);
        // Ground texture — grass tufts and pebbles
        for (int i = 0; i < 10; i++)
        {
            int gx = x + s * 5 / 100 + i * s * 9 / 100;
            r.DrawRect((80, 100, 40), (gx, groundY + 2, s * 3 / 100, 2), alpha: 220);
            r.DrawLine((90, 130, 50), (gx + s * 2 / 100, groundY), (gx + s * 1 / 100, groundY - s * 3 / 100), width: 1, alpha: 200);
        }

        // === DUST CLOUD — layered with gradient fills ===
        int[] dustX = { -22, -30, -26, -34, -38 };
        int[] dustY2 = { -6, -4, -10, -2, -8 };
        int[] dustR = { 10, 8, 7, 6, 5 };
        for (int d = 0; d < 5; d++)
        {
            int dcx = cx + s * dustX[d] / 100;
            int dcy = groundY + s * dustY2[d] / 100;
            int dr = Math.Max(3, s * dustR[d] / 100);
            // Gradient-filled dust puff
            for (int ring = dr; ring >= 1; ring--)
            {
                float t = (float)ring / dr;
                int c = (int)(160 + 60 * (1f - t));
                r.DrawCircle((c, c - 20, c - 40), (dcx, dcy), ring, alpha: (int)(200 * t + 55));
            }
        }
        // Dust particles rising
        for (int i = 0; i < 8; i++)
        {
            int dx = cx - s * 18 / 100 - i * s * 4 / 100;
            int dy = groundY - s * (2 + i * 3) / 100;
            r.DrawCircle((200, 180, 140), (dx, dy), Math.Max(1, 3 - i / 3), alpha: 240 - i * 20);
        }

        // === CAT BODY — gradient-filled, running pose ===
        int catCx = cx + s * 4 / 100, catCy = cy - s * 2 / 100;
        int bodyR = Math.Max(6, s * 14 / 100);
        // Gradient body fill
        for (int ring = bodyR; ring >= 1; ring--)
        {
            float t = (float)ring / bodyR;
            int rr = (int)(200 + 30 * (1f - t));
            int gg = (int)(160 + 30 * (1f - t));
            int bb = (int)(80 + 20 * (1f - t));
            r.DrawCircle((rr, gg, bb), (catCx, catCy), ring, alpha: 255);
        }
        // Body highlight
        r.DrawCircle((240, 210, 140), (catCx - s * 2 / 100, catCy - s * 3 / 100), Math.Max(3, s * 6 / 100), alpha: 120);

        // Head — gradient-filled
        int headX = catCx + s * 16 / 100, headY = catCy - s * 8 / 100;
        int headR = Math.Max(5, s * 10 / 100);
        for (int ring = headR; ring >= 1; ring--)
        {
            float t = (float)ring / headR;
            int rr = (int)(215 + 25 * (1f - t));
            int gg = (int)(175 + 25 * (1f - t));
            int bb = (int)(95 + 20 * (1f - t));
            r.DrawCircle((rr, gg, bb), (headX, headY), ring, alpha: 255);
        }
        // Snout
        r.DrawCircle((235, 200, 130), (headX + s * 4 / 100, headY + s * 2 / 100), Math.Max(3, s * 5 / 100), alpha: 255);

        // Ears — alert, with inner gradient
        DrawTriangle(r, headX - s * 4 / 100, headY - s * 16 / 100, s * 7 / 100, (200, 160, 80), 255);
        DrawTriangle(r, headX + s * 4 / 100, headY - s * 16 / 100, s * 7 / 100, (200, 160, 80), 255);
        DrawTriangle(r, headX - s * 3 / 100, headY - s * 13 / 100, s * 4 / 100, (240, 170, 140), 220);
        DrawTriangle(r, headX + s * 5 / 100, headY - s * 13 / 100, s * 4 / 100, (240, 170, 140), 220);

        // Eyes — determined, with highlights
        r.DrawCircle((255, 255, 220), (headX - s * 1 / 100, headY - s * 2 / 100), Math.Max(2, s * 3 / 100), alpha: 255);
        r.DrawCircle((255, 255, 220), (headX + s * 4 / 100, headY - s * 2 / 100), Math.Max(2, s * 3 / 100), alpha: 255);
        r.DrawCircle((20, 60, 20), (headX, headY - s * 2 / 100), Math.Max(1, s * 2 / 100), alpha: 255);
        r.DrawCircle((20, 60, 20), (headX + s * 5 / 100, headY - s * 2 / 100), Math.Max(1, s * 2 / 100), alpha: 255);
        // Eye shine
        r.DrawCircle((255, 255, 255), (headX - 2, headY - s * 3 / 100), 1, alpha: 255);
        r.DrawCircle((255, 255, 255), (headX + s * 3 / 100, headY - s * 3 / 100), 1, alpha: 255);
        // Nose
        DrawTriangle(r, headX + s * 6 / 100, headY + s * 1 / 100, Math.Max(2, s * 2 / 100), (180, 100, 80), 255);
        // Determined grin
        r.DrawLine((160, 100, 70), (headX + s * 2 / 100, headY + s * 3 / 100),
            (headX + s * 6 / 100, headY + s * 2 / 100), width: 1, alpha: 255);

        // Legs in running stride — thicker with gradient
        // Front legs — stretched forward
        r.DrawLine((180, 140, 60), (catCx + s * 10 / 100, catCy + s * 4 / 100), (catCx + s * 22 / 100, groundY - 2), width: 4, alpha: 255);
        r.DrawLine((200, 165, 80), (catCx + s * 10 / 100, catCy + s * 4 / 100), (catCx + s * 22 / 100, groundY - 2), width: 2, alpha: 255);
        r.DrawLine((180, 140, 60), (catCx + s * 6 / 100, catCy + s * 2 / 100), (catCx + s * 14 / 100, groundY - 2), width: 4, alpha: 255);
        r.DrawLine((200, 165, 80), (catCx + s * 6 / 100, catCy + s * 2 / 100), (catCx + s * 14 / 100, groundY - 2), width: 2, alpha: 255);
        // Back legs — pushed back
        r.DrawLine((180, 140, 60), (catCx - s * 8 / 100, catCy + s * 4 / 100), (catCx - s * 16 / 100, groundY - 2), width: 4, alpha: 255);
        r.DrawLine((200, 165, 80), (catCx - s * 8 / 100, catCy + s * 4 / 100), (catCx - s * 16 / 100, groundY - 2), width: 2, alpha: 255);
        r.DrawLine((180, 140, 60), (catCx - s * 4 / 100, catCy + s * 6 / 100), (catCx - s * 10 / 100, groundY - 2), width: 4, alpha: 255);
        r.DrawLine((200, 165, 80), (catCx - s * 4 / 100, catCy + s * 6 / 100), (catCx - s * 10 / 100, groundY - 2), width: 2, alpha: 255);
        // Paws with gradient fill
        for (int pr = Math.Max(2, s * 2 / 100); pr >= 1; pr--)
        {
            int c = 180 + (Math.Max(2, s * 2 / 100) - pr) * 15;
            r.DrawCircle((c, c - 20, c - 60), (catCx + s * 22 / 100, groundY - 2), pr, alpha: 255);
            r.DrawCircle((c, c - 20, c - 60), (catCx - s * 16 / 100, groundY - 2), pr, alpha: 255);
            r.DrawCircle((c, c - 20, c - 60), (catCx + s * 14 / 100, groundY - 2), pr, alpha: 255);
            r.DrawCircle((c, c - 20, c - 60), (catCx - s * 10 / 100, groundY - 2), pr, alpha: 255);
        }

        // Tail — streaming behind with curve, thicker
        r.DrawLine((190, 150, 70), (catCx - s * 12 / 100, catCy - s * 4 / 100),
            (catCx - s * 24 / 100, catCy - s * 14 / 100), width: 4, alpha: 255);
        r.DrawLine((210, 175, 90), (catCx - s * 12 / 100, catCy - s * 4 / 100),
            (catCx - s * 24 / 100, catCy - s * 14 / 100), width: 2, alpha: 255);
        r.DrawLine((190, 150, 70), (catCx - s * 24 / 100, catCy - s * 14 / 100),
            (catCx - s * 30 / 100, catCy - s * 20 / 100), width: 3, alpha: 255);

        // Cat whiskers — flying back from speed
        r.DrawLine((200, 170, 100), (headX + s * 5 / 100, headY + s * 1 / 100),
            (headX + s * 18 / 100, headY - s * 3 / 100), width: 1, alpha: 255);
        r.DrawLine((200, 170, 100), (headX + s * 5 / 100, headY + s * 3 / 100),
            (headX + s * 16 / 100, headY + s * 2 / 100), width: 1, alpha: 255);
        r.DrawLine((200, 170, 100), (headX + s * 5 / 100, headY + s * 5 / 100),
            (headX + s * 14 / 100, headY + s * 6 / 100), width: 1, alpha: 255);

        // === MOTION BLUR LINES — vibrant gradient ===
        for (int i = 0; i < 8; i++)
        {
            int ly = catCy - s * 14 / 100 + i * s * 4 / 100;
            int ll = s * (10 + i * 2) / 100;
            int lx = catCx - s * 32 / 100 - i * s * 2 / 100;
            int rr = 255;
            int gg = 220 - i * 10;
            int bb = 60 + i * 15;
            r.DrawLine((rr, gg, bb), (lx, ly), (lx + ll, ly), width: 2, alpha: 255 - i * 15);
        }

        // Speed wind streaks across full width
        for (int i = 0; i < 5; i++)
        {
            int sy = y + s * 10 / 100 + i * s * 15 / 100;
            int sx = x + s * 5 / 100 + i * s * 8 / 100;
            r.DrawLine((255, 255, 200), (sx, sy), (sx + s * 20 / 100, sy), width: 1, alpha: 150 - i * 20);
        }

        // Sweat drops flying off the cat
        DrawSweatDrops(r, headX + s * 4 / 100, headY - s * 6 / 100, s, 3);

        // Paw print trail on ground — fading
        for (int i = 0; i < 6; i++)
        {
            int ppX = catCx - s * 8 / 100 - i * s * 8 / 100;
            int ppR = Math.Max(1, s * 2 / 100);
            r.DrawCircle((130, 110, 70), (ppX, groundY - 1), ppR, alpha: 220 - i * 30);
            // Toe beans
            r.DrawCircle((120, 100, 60), (ppX - 1, groundY - ppR - 1), Math.Max(1, ppR / 2), alpha: 200 - i * 30);
            r.DrawCircle((120, 100, 60), (ppX + 1, groundY - ppR - 1), Math.Max(1, ppR / 2), alpha: 200 - i * 30);
        }

        // Grass tufts kicked up — more detail
        for (int i = 0; i < 5; i++)
        {
            int gx = catCx - s * 12 / 100 - i * s * 5 / 100;
            int gy = groundY;
            r.DrawLine((60, 130, 30), (gx, gy), (gx - s * 2 / 100, gy - s * 4 / 100), width: 2, alpha: 230 - i * 30);
            r.DrawLine((80, 150, 50), (gx + s * 1 / 100, gy), (gx + s * 2 / 100, gy - s * 3 / 100), width: 1, alpha: 220 - i * 30);
        }

        // Bold outlines on cat body and head
        DrawBoldCircleOutline(r, catCx, catCy, bodyR, 220);
        DrawBoldCircleOutline(r, headX, headY, headR, 220);

        // Fur texture on body
        DrawFurTexture(r, catCx, catCy, Math.Max(6, s * 12 / 100), 16, (180, 140, 60), 220);

        // Speed exclamation with glow
        r.DrawText("!", headX + s * 10 / 100, headY - s * 10 / 100, Math.Max(8, s * 12 / 100), (255, 200, 40),
            bold: true, anchorX: "center", anchorY: "center", alpha: 180);
        r.DrawText("!", headX + s * 10 / 100, headY - s * 10 / 100, Math.Max(8, s * 10 / 100), (255, 255, 80),
            bold: true, anchorX: "center", anchorY: "center", alpha: 255);

        // === SPARKLE ACCENTS ===
        DrawSparkle(r, cx - s * 36 / 100, cy - s * 20 / 100, s * 2 / 100, (255, 255, 150), 230);
        DrawSparkle(r, cx + s * 30 / 100, cy - s * 30 / 100, s * 15 / 1000, (255, 240, 180), 220);
        DrawSparkle(r, cx + s * 38 / 100, cy + s * 10 / 100, s * 18 / 1000, (255, 220, 100), 210);

        // Speed symbols — ≫ arrows
        r.DrawText("»", catCx - s * 28 / 100, catCy - s * 12 / 100, Math.Max(6, s * 7 / 100), (255, 220, 60),
            bold: true, anchorX: "center", anchorY: "center", alpha: 220);
        r.DrawText("»", catCx - s * 36 / 100, catCy + s * 2 / 100, Math.Max(5, s * 6 / 100), (255, 200, 40),
            bold: true, anchorX: "center", anchorY: "center", alpha: 190);

        // === EMBOSSED "ZOOM!" TEXT ===
        r.DrawText("ZOOM!", cx, cy + s * 36 / 100, Math.Max(8, s * 10 / 100), (100, 60, 20),
            bold: true, anchorX: "center", anchorY: "center", alpha: 200);
        r.DrawText("ZOOM!", cx - 1, cy + s * 36 / 100 - 1, Math.Max(8, s * 10 / 100), (255, 220, 60),
            bold: true, anchorX: "center", anchorY: "center", alpha: 255);
    }

    private static void DrawSKIP_Hourglass(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);
        int glW = s * 24 / 100, glH = s * 36 / 100;

        // === RICH MYSTICAL TIME-WARP BACKGROUND ===
        for (int row = 0; row < h; row++)
        {
            float t = (float)row / h;
            int rr = (int)(40 + 60 * t);      // deep indigo → warm amber
            int gg = (int)(30 + 80 * t);
            int bb = (int)(80 - 40 * t);
            r.DrawRect((rr, gg, bb), (x, y + row, w, 1), alpha: 255);
        }

        // Time warp concentric energy rings
        for (int ring = 0; ring < 6; ring++)
        {
            int rr = glW + s * (12 + ring * 7) / 100;
            float t = (float)ring / 6;
            int rc = (int)(180 + 60 * t);
            int gc = (int)(150 + 50 * t);
            int bc = (int)(40 + 30 * t);
            r.DrawCircle((rc, gc, bc), (cx, cy), rr, width: 2, alpha: 200 - ring * 25);
        }

        // Clockwork gear teeth around the outer ring
        for (int tooth = 0; tooth < 24; tooth++)
        {
            double angle = tooth * Math.PI / 12;
            int tR1 = glW + s * 38 / 100;
            int tR2 = glW + s * 42 / 100;
            int tw = tooth % 2 == 0 ? 2 : 1;
            r.DrawLine((160, 140, 60), 
                (cx + (int)(Math.Cos(angle) * tR1), cy + (int)(Math.Sin(angle) * tR1)),
                (cx + (int)(Math.Cos(angle) * tR2), cy + (int)(Math.Sin(angle) * tR2)),
                width: tw, alpha: 220);
        }

        // Floating time symbols in background
        string[] timeSyms = { "XII", "III", "VI", "IX" };
        int[] symAngles = { -90, 0, 90, 180 };
        for (int i = 0; i < 4; i++)
        {
            double ang = symAngles[i] * Math.PI / 180;
            int sx = cx + (int)(Math.Cos(ang) * (glW + s * 32 / 100));
            int sy = cy + (int)(Math.Sin(ang) * (glW + s * 32 / 100));
            r.DrawText(timeSyms[i], sx, sy, Math.Max(4, s * 4 / 100), (200, 180, 80),
                bold: true, anchorX: "center", anchorY: "center", alpha: 200);
        }

        // === ORNATE FRAME — gradient-filled bars ===
        int barH = s * 5 / 100;
        // Top bar — gradient fill
        for (int row = 0; row < barH; row++)
        {
            float t = (float)row / barH;
            int c = (int)(180 + 60 * (1f - t));
            r.DrawRect((c, c - 30, c - 100), (cx - glW / 2 - 6, cy - glH - 1 + row, glW + 12, 1), alpha: 255);
        }
        r.DrawRect((255, 230, 140), (cx - glW / 2 - 5, cy - glH, glW + 10, 1), alpha: 255); // highlight
        // Bottom bar — gradient fill
        for (int row = 0; row < barH; row++)
        {
            float t = (float)row / barH;
            int c = (int)(180 + 60 * t);
            r.DrawRect((c, c - 30, c - 100), (cx - glW / 2 - 6, cy + glH - barH + 1 + row, glW + 12, 1), alpha: 255);
        }
        r.DrawRect((255, 230, 140), (cx - glW / 2 - 5, cy + glH - 1, glW + 10, 1), alpha: 255); // highlight

        // Decorative knobs with gradient fills
        int knobR = Math.Max(2, barH / 2);
        int[] knobXs = { cx - glW / 2 - 6, cx + glW / 2 + 6 };
        int[] knobYs = { cy - glH + barH / 2, cy + glH - barH / 2 };
        foreach (int kx in knobXs)
            foreach (int ky in knobYs)
                for (int kr = knobR; kr >= 1; kr--)
                {
                    int c = 190 + (knobR - kr) * 15;
                    r.DrawCircle((c, c - 20, c - 80), (kx, ky), kr, alpha: 255);
                }

        // === GLASS BODY — enhanced with gradient tints ===
        // Top half
        for (int row = 0; row < glH; row++)
        {
            float t = (float)row / glH;
            int rowW = (int)(glW * (1f - t * 0.88f));
            int rr = (int)(180 + 40 * (1f - t));
            int gg = (int)(200 + 30 * (1f - t));
            int bb = (int)(230 + 20 * (1f - t));
            int a = (int)(25 + 20 * (1f - t));
            r.DrawRect((rr, gg, bb), (cx - rowW / 2, cy - glH + barH + row, rowW, 1), alpha: a);
        }
        // Bottom half
        for (int row = 0; row < glH; row++)
        {
            float t = (float)row / glH;
            int rowW = (int)(glW * (0.12f + t * 0.88f));
            int rr = (int)(180 + 40 * t);
            int gg = (int)(200 + 30 * t);
            int bb = (int)(230 + 20 * t);
            int a = (int)(20 + 18 * t);
            r.DrawRect((rr, gg, bb), (cx - rowW / 2, cy + row, rowW, 1), alpha: a);
        }
        // Glass outline — thicker
        r.DrawLine((140, 170, 210), (cx - glW / 2, cy - glH + barH), (cx - glW * 6 / 100 / 2, cy), width: 2, alpha: 255);
        r.DrawLine((140, 170, 210), (cx + glW / 2, cy - glH + barH), (cx + glW * 6 / 100 / 2, cy), width: 2, alpha: 255);
        r.DrawLine((140, 170, 210), (cx - glW * 6 / 100 / 2, cy), (cx - glW / 2, cy + glH - barH), width: 2, alpha: 255);
        r.DrawLine((140, 170, 210), (cx + glW * 6 / 100 / 2, cy), (cx + glW / 2, cy + glH - barH), width: 2, alpha: 255);

        // Sand in bottom — gradient-filled with layered color
        int sandH = glH * 55 / 100;
        for (int row = 0; row < sandH; row++)
        {
            float t = (float)(glH - sandH + row) / glH;
            int rowW = (int)(glW * (0.12f + t * 0.88f)) - 4;
            float sandT = (float)row / sandH;
            int rr = (int)(220 + 30 * sandT);
            int gg = (int)(180 + 25 * sandT);
            int bb = (int)(40 + 20 * sandT);
            r.DrawRect((rr, gg, bb), (cx - rowW / 2, cy + glH - barH - sandH + row, rowW, 1), alpha: 255);
        }
        // Sand surface highlight
        int surfW = (int)(glW * 0.5f);
        r.DrawLine((255, 230, 100), (cx - surfW / 2, cy + glH - barH - sandH), (cx + surfW / 2, cy + glH - barH - sandH), width: 2, alpha: 255);

        // Sand in top — remaining pile with gradient
        int topSandH = glH * 20 / 100;
        for (int row = 0; row < topSandH; row++)
        {
            float t = (float)row / topSandH;
            int rowW = (int)(glW * 0.8f * (1f - t * 0.6f)) - 2;
            int rr = (int)(230 + 20 * t);
            int gg = (int)(190 + 15 * t);
            r.DrawRect((rr, gg, 50), (cx - rowW / 2, cy - glH + barH + (glH - topSandH) + row, rowW, 1), alpha: 255);
        }

        // Falling sand stream — wider with glow
        r.DrawLine((240, 200, 60), (cx, cy - s * 6 / 100), (cx, cy + s * 6 / 100), width: 3, alpha: 255);
        r.DrawLine((255, 230, 100), (cx, cy - s * 5 / 100), (cx, cy + s * 5 / 100), width: 1, alpha: 200); // inner glow
        // Individual sand grains — more
        for (int g = 0; g < 6; g++)
        {
            int gy = cy - s * 5 / 100 + g * s * 2 / 100;
            int gx = cx + (g % 3 - 1) * 2;
            r.DrawCircle((255, 220, 80), (gx, gy), 1, alpha: 255);
        }

        // Glass reflection highlights — thicker
        r.DrawLine((255, 255, 255), (cx - glW / 3, cy - glH * 80 / 100), (cx - glW * 10 / 100, cy - glH * 30 / 100), width: 2, alpha: 240);
        r.DrawLine((255, 255, 255), (cx + glW / 4, cy + glH * 30 / 100), (cx + glW * 8 / 100, cy + glH * 70 / 100), width: 2, alpha: 220);

        // Bold outlines on frame bars
        DrawBoldRectOutline(r, cx - glW / 2 - 6, cy - glH - 1, glW + 12, barH, 220);
        DrawBoldRectOutline(r, cx - glW / 2 - 6, cy + glH - barH + 1, glW + 12, barH, 220);

        // Ornate scrollwork on frame — filigree curls
        for (int side = -1; side <= 1; side += 2)
        {
            int sx = cx + side * (glW / 2 + 10);
            r.DrawCircle((210, 190, 110), (sx, cy - glH - 6), Math.Max(2, s * 2 / 100), width: 1, alpha: 255);
            r.DrawCircle((210, 190, 110), (sx, cy + glH + 4), Math.Max(2, s * 2 / 100), width: 1, alpha: 255);
            // Filigree arcs
            r.DrawCircle((190, 170, 90), (sx + side * s * 2 / 100, cy - glH - 2), Math.Max(1, s * 1 / 100), width: 1, alpha: 200);
            r.DrawCircle((190, 170, 90), (sx + side * s * 2 / 100, cy + glH + 1), Math.Max(1, s * 1 / 100), width: 1, alpha: 200);
        }

        // === SPARKLE ACCENTS ===
        DrawSparkle(r, cx + s * 8 / 100, cy + s * 6 / 100, s * 2 / 100, (255, 240, 120), 240);
        DrawSparkle(r, cx - s * 7 / 100, cy - s * 5 / 100, s * 18 / 1000, (255, 250, 200), 230);
        DrawSparkle(r, cx + s * 28 / 100, cy - s * 20 / 100, s * 15 / 1000, (255, 230, 140), 210);
        DrawSparkle(r, cx - s * 26 / 100, cy + s * 18 / 100, s * 15 / 1000, (255, 220, 100), 200);

        // Clock tick marks — thicker, around hourglass
        for (int tick = 0; tick < 12; tick++)
        {
            double angle = tick * Math.PI / 6;
            int tR1 = glW + s * 22 / 100;
            int tR2 = glW + s * 26 / 100;
            int tw = tick % 3 == 0 ? 3 : 1; // major ticks at 12/3/6/9
            r.DrawLine((220, 200, 100), 
                (cx + (int)(Math.Cos(angle) * tR1), cy + (int)(Math.Sin(angle) * tR1)),
                (cx + (int)(Math.Cos(angle) * tR2), cy + (int)(Math.Sin(angle) * tR2)),
                width: tw, alpha: 255);
        }

        // Time symbol
        r.DrawText("⏳", cx + s * 30 / 100, cy - s * 12 / 100, Math.Max(6, s * 7 / 100), (230, 210, 100),
            anchorX: "center", anchorY: "center", alpha: 240);

        // Mini cat face hiding behind hourglass
        DrawMiniCatFace(r, cx + s * 32 / 100, cy + s * 26 / 100, s * 6 / 100, (200, 170, 100), 240);

        // === EMBOSSED "TICK TOCK" TEXT ===
        r.DrawText("TICK", cx - s * 30 / 100, cy - s * 30 / 100, Math.Max(6, s * 6 / 100), (80, 50, 20),
            bold: true, anchorX: "center", anchorY: "center", alpha: 200);
        r.DrawText("TICK", cx - s * 30 / 100 - 1, cy - s * 30 / 100 - 1, Math.Max(6, s * 6 / 100), (240, 210, 100),
            bold: true, anchorX: "center", anchorY: "center", alpha: 255);
        r.DrawText("TOCK", cx + s * 30 / 100, cy + s * 30 / 100, Math.Max(6, s * 6 / 100), (80, 50, 20),
            bold: true, anchorX: "center", anchorY: "center", alpha: 200);
        r.DrawText("TOCK", cx + s * 30 / 100 - 1, cy + s * 30 / 100 - 1, Math.Max(6, s * 6 / 100), (240, 210, 100),
            bold: true, anchorX: "center", anchorY: "center", alpha: 255);
    }

    private static void DrawSKIP_SpringBoard(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // === GRADIENT SKY BACKGROUND — bright day ===
        for (int row = 0; row < h; row++)
        {
            float t = (float)row / h;
            int rr = (int)(100 + 120 * t);   // light blue → warm ground
            int gg = (int)(180 - 60 * t);
            int bb = (int)(240 - 180 * t);
            r.DrawRect((rr, gg, bb), (x, y + row, w, 1), alpha: 255);
        }

        // Fluffy clouds
        int[] cloudXs = { cx - s * 30 / 100, cx + s * 20 / 100, cx - s * 8 / 100 };
        int[] cloudYs = { y + s * 8 / 100, y + s * 12 / 100, y + s * 5 / 100 };
        for (int c = 0; c < 3; c++)
        {
            r.DrawCircle((240, 245, 255), (cloudXs[c], cloudYs[c]), Math.Max(4, s * 8 / 100), alpha: 180);
            r.DrawCircle((250, 252, 255), (cloudXs[c] + s * 4 / 100, cloudYs[c] - s * 2 / 100), Math.Max(3, s * 6 / 100), alpha: 200);
            r.DrawCircle((235, 240, 250), (cloudXs[c] - s * 4 / 100, cloudYs[c] + s * 1 / 100), Math.Max(3, s * 5 / 100), alpha: 170);
        }

        // === GROUND — gradient terrain ===
        int groundY = cy + s * 32 / 100;
        for (int row = 0; row < h - (groundY - y); row++)
        {
            float t = (float)row / (h - (groundY - y) + 1);
            int rr = (int)(110 - 40 * t);
            int gg = (int)(140 - 50 * t);
            int bb = (int)(70 - 30 * t);
            r.DrawRect((rr, gg, bb), (x, groundY + row, w, 1), alpha: 255);
        }
        // Ground surface
        r.DrawLine((130, 120, 80), (x, groundY), (x + w, groundY), width: 2, alpha: 255);
        // Ground texture lines
        for (int i = 0; i < 8; i++)
        {
            int gx = x + s * 5 / 100 + i * s * 10 / 100;
            r.DrawRect((80, 100, 50), (gx, groundY + s * 2 / 100, s * 3 / 100, 1), alpha: 200);
        }

        // Base platform — gradient fill
        int platGY = groundY;
        for (int row = 0; row < s * 6 / 100; row++)
        {
            float t = (float)row / (s * 6 / 100);
            int c = (int)(120 - 40 * t);
            r.DrawRect((c, c - 10, c - 30), (cx - s * 28 / 100, platGY + row, s * 56 / 100, 1), alpha: 255);
        }
        r.DrawRect((150, 135, 100), (cx - s * 27 / 100, platGY + 1, s * 54 / 100, 2), alpha: 255); // highlight

        // === SPRING — detailed coils with gradient metallic look ===
        int springX = cx - s * 4 / 100, springBot = groundY - 2;
        int coilCount = 6, coilSpacing = s * 6 / 100;
        for (int coil = 0; coil < coilCount; coil++)
        {
            int coilY = springBot - coil * coilSpacing;
            int coilR = Math.Max(3, s * 6 / 100);
            // Shadow coil
            r.DrawCircle((100, 100, 120), (springX + 2, coilY + 2), coilR, width: 3, alpha: 200);
            // Main coil — gradient brightness
            int g = 160 + coil * 12;
            r.DrawCircle((g, g + 5, g + 25), (springX, coilY), coilR, width: 3, alpha: 255);
            // Specular highlight
            r.DrawCircle((240, 245, 255), (springX - 3, coilY - 2), Math.Max(2, s * 25 / 1000), width: 1, alpha: 220);
            // Inner highlight
            r.DrawCircle((255, 255, 255), (springX - 1, coilY - 1), 1, alpha: 180);
        }
        // Spring connector bolt — gradient
        for (int br = Math.Max(2, s * 2 / 100); br >= 1; br--)
        {
            int c = 140 + (Math.Max(2, s * 2 / 100) - br) * 20;
            r.DrawCircle((c, c - 10, c - 20), (springX, springBot), br, alpha: 255);
        }

        // === LAUNCH PLATFORM — wood grain with gradient ===
        int platY = springBot - coilCount * coilSpacing - s * 3 / 100;
        int platW = s * 40 / 100;
        for (int row = 0; row < s * 5 / 100; row++)
        {
            float t = (float)row / (s * 5 / 100);
            int rr = (int)(170 - 30 * t);
            int gg = (int)(150 - 30 * t);
            int bb = (int)(100 - 30 * t);
            r.DrawRect((rr, gg, bb), (cx - platW / 2, platY + row, platW, 1), alpha: 255);
        }
        // Wood grain
        for (int i = 0; i < 5; i++)
            r.DrawLine((130, 110, 60), (cx - platW / 2 + 3, platY + 1 + i * s / 100), (cx + platW / 2 - 3, platY + 1 + i * s / 100), width: 1, alpha: 180);
        // Platform highlight
        r.DrawRect((210, 195, 140), (cx - platW / 2 + 2, platY + 1, platW - 4, 2), alpha: 255);
        // Platform bolt — gradient
        for (int br = Math.Max(2, s * 2 / 100); br >= 1; br--)
        {
            int c = 160 + (Math.Max(2, s * 2 / 100) - br) * 20;
            r.DrawCircle((c, c - 10, c - 30), (springX, platY + s * 4 / 100), br, alpha: 255);
        }

        // === CAT BEING LAUNCHED — gradient-filled ===
        int catY = cy - s * 26 / 100;
        int catX = cx + s * 4 / 100;
        // Cat body — gradient fill
        int bodyR = Math.Max(3, s * 8 / 100);
        for (int ring = bodyR; ring >= 1; ring--)
        {
            float t = (float)ring / bodyR;
            int rr = (int)(200 + 30 * (1f - t));
            int gg = (int)(160 + 25 * (1f - t));
            int bb = (int)(80 + 20 * (1f - t));
            r.DrawCircle((rr, gg, bb), (catX, catY + s * 2 / 100), ring, alpha: 255);
        }
        // Cat head — gradient fill
        int headR = Math.Max(4, s * 7 / 100);
        for (int ring = headR; ring >= 1; ring--)
        {
            float t = (float)ring / headR;
            int rr = (int)(195 + 35 * (1f - t));
            int gg = (int)(155 + 30 * (1f - t));
            int bb = (int)(75 + 25 * (1f - t));
            r.DrawCircle((rr, gg, bb), (catX, catY - s * 2 / 100), ring, alpha: 255);
        }
        // Ears
        DrawTriangle(r, (190, 150, 70), catX - s * 5 / 100, catY - s * 10 / 100,
                     catX - s * 2 / 100, catY - s * 5 / 100, catX - s * 6 / 100, catY - s * 4 / 100, 50);
        DrawTriangle(r, (190, 150, 70), catX + s * 5 / 100, catY - s * 10 / 100,
                     catX + s * 2 / 100, catY - s * 5 / 100, catX + s * 6 / 100, catY - s * 4 / 100, 50);
        // Inner ears
        DrawTriangle(r, (240, 180, 140), catX - s * 4 / 100, catY - s * 9 / 100,
                     catX - s * 2 / 100, catY - s * 6 / 100, catX - s * 5 / 100, catY - s * 5 / 100, 35);
        DrawTriangle(r, (240, 180, 140), catX + s * 4 / 100, catY - s * 9 / 100,
                     catX + s * 2 / 100, catY - s * 6 / 100, catX + s * 5 / 100, catY - s * 5 / 100, 35);
        // Wide eyes — scared expression with highlights
        r.DrawCircle((255, 255, 255), (catX - s * 3 / 100, catY - s * 3 / 100), Math.Max(2, s * 3 / 100), alpha: 255);
        r.DrawCircle((255, 255, 255), (catX + s * 3 / 100, catY - s * 3 / 100), Math.Max(2, s * 3 / 100), alpha: 255);
        r.DrawCircle((40, 40, 40), (catX - s * 3 / 100, catY - s * 3 / 100), Math.Max(1, s * 15 / 1000), alpha: 255);
        r.DrawCircle((40, 40, 40), (catX + s * 3 / 100, catY - s * 3 / 100), Math.Max(1, s * 15 / 1000), alpha: 255);
        // Eye highlights
        r.DrawCircle((255, 255, 255), (catX - s * 3 / 100 - 1, catY - s * 4 / 100), 1, alpha: 255);
        r.DrawCircle((255, 255, 255), (catX + s * 3 / 100 - 1, catY - s * 4 / 100), 1, alpha: 255);
        // Open mouth
        r.DrawCircle((200, 80, 80), (catX, catY + s * 1 / 100), Math.Max(2, s * 2 / 100), alpha: 255);
        // Paws stretched out — thicker
        r.DrawLine((200, 160, 80), (catX - s * 8 / 100, catY - s * 4 / 100), (catX - s * 16 / 100, catY - s * 10 / 100), width: 3, alpha: 255);
        r.DrawLine((200, 160, 80), (catX + s * 8 / 100, catY - s * 4 / 100), (catX + s * 16 / 100, catY - s * 10 / 100), width: 3, alpha: 255);
        // Paw pads
        r.DrawCircle((230, 180, 140), (catX - s * 16 / 100, catY - s * 10 / 100), Math.Max(1, s * 15 / 1000), alpha: 255);
        r.DrawCircle((230, 180, 140), (catX + s * 16 / 100, catY - s * 10 / 100), Math.Max(1, s * 15 / 1000), alpha: 255);
        // Tail trailing — thicker
        r.DrawLine((190, 150, 70), (catX, catY + s * 6 / 100), (catX - s * 6 / 100, catY + s * 12 / 100), width: 3, alpha: 255);
        r.DrawLine((190, 150, 70), (catX - s * 6 / 100, catY + s * 12 / 100), (catX - s * 3 / 100, catY + s * 16 / 100), width: 3, alpha: 255);

        // === UPWARD MOTION BLUR LINES — gradient color ===
        for (int i = 0; i < 7; i++)
        {
            int lx = catX + s * (-8 + i * 3) / 100;
            int len = s * (12 + i * 3) / 100;
            int rr = 255;
            int gg = 240 - i * 12;
            int bb = 80 + i * 15;
            r.DrawLine((rr, gg, bb), (lx, catY + s * 10 / 100), (lx, catY + s * 10 / 100 + len), width: 2, alpha: 230 - i * 20);
        }

        // === BURST EFFECT at launch — layered glow ===
        for (int ring = 5; ring >= 1; ring--)
        {
            int rr2 = s * (6 + ring * 3) / 100;
            float t = (float)ring / 5;
            int c = (int)(200 + 55 * (1f - t));
            r.DrawCircle((c, c, (int)(c * 0.6f)), (springX, platY), rr2, width: 1, alpha: (int)(100 + 80 * (1f - t)));
        }
        // Burst rays
        for (int ray = 0; ray < 12; ray++)
        {
            double angle = ray * Math.PI / 6;
            int rx = (int)(springX + Math.Cos(angle) * s * 12 / 100);
            int ry = (int)(platY + Math.Sin(angle) * s * 10 / 100);
            r.DrawLine((255, 255, 160), (springX, platY), (rx, ry), width: 2, alpha: 220);
        }

        // Dust poof at launch point — gradient filled
        for (int d = 0; d < 7; d++)
        {
            double dAng = d * Math.PI / 3.5 + 0.3;
            int dx2 = springX + (int)(Math.Cos(dAng) * s * 8 / 100);
            int dy2 = platY + (int)(Math.Sin(dAng) * s * 5 / 100);
            int dr = Math.Max(2, s * 3 / 100);
            for (int ring = dr; ring >= 1; ring--)
            {
                float t = (float)ring / dr;
                int c = (int)(180 + 60 * (1f - t));
                r.DrawCircle((c, c - 10, c - 30), (dx2, dy2), ring, alpha: (int)(150 * t + 80));
            }
        }

        // Bold outlines
        DrawBoldCircleOutline(r, catX, catY + s * 2 / 100, bodyR, 220);
        DrawBoldCircleOutline(r, catX, catY - s * 2 / 100, headR, 220);
        DrawBoldRectOutline(r, cx - platW / 2, platY, platW, s * 5 / 100, 220);

        // Fur texture on flying cat
        DrawFurTexture(r, catX, catY + s * 2 / 100, Math.Max(3, s * 6 / 100), 12, (190, 150, 70), 220);

        // Sweat drops flying off scared cat
        DrawSweatDrops(r, catX + s * 10 / 100, catY - s * 8 / 100, s, 3);

        // Zigzag spring energy
        DrawZigzagPattern(r, cx - s * 6 / 100, platY + s * 2 / 100, s * 12 / 100, groundY - platY - s * 2 / 100, (180, 200, 255), 200, s * 3 / 100);

        // === SPARKLE ACCENTS ===
        DrawSparkle(r, catX - s * 18 / 100, catY - s * 8 / 100, s * 2 / 100, (255, 255, 120), 240);
        DrawSparkle(r, catX + s * 16 / 100, catY + s * 2 / 100, s * 18 / 1000, (255, 200, 255), 230);
        DrawSparkle(r, catX - s * 8 / 100, catY - s * 18 / 100, s * 2 / 100, (120, 255, 255), 220);
        DrawSparkle(r, cx - s * 36 / 100, cy + s * 20 / 100, s * 15 / 1000, (255, 240, 150), 200);

        // Danger stripes on platform edge
        DrawDangerStripes(r, cx - platW / 2, platY - s * 1 / 100, platW, s * 1 / 100, 220, s * 3 / 100);

        // Exclamation marks around cat
        r.DrawText("!!", catX - s * 16 / 100, catY - s * 14 / 100, Math.Max(6, s * 6 / 100), (255, 60, 60),
            bold: true, anchorX: "center", anchorY: "center", alpha: 255);

        // === EMBOSSED "BOING!" TEXT ===
        r.DrawText("BOING!", cx + s * 18 / 100, cy + s * 6 / 100, Math.Max(8, s * 10 / 100), (120, 80, 20),
            bold: true, anchorX: "center", anchorY: "center", alpha: 200);
        r.DrawText("BOING!", cx + s * 18 / 100 - 1, cy + s * 6 / 100 - 1, Math.Max(8, s * 10 / 100), (255, 220, 60),
            bold: true, anchorX: "center", anchorY: "center", alpha: 255);
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

        // === Stormy sky background — dark gradient bands ===
        for (int band = 0; band < 8; band++)
        {
            int bandY = y + band * h / 8;
            int bv = 40 + band * 6;
            r.DrawRect((bv, bv + 10, bv + 30), (x, bandY, w, h / 8 + 1), alpha: 240 - band * 8);
        }
        // Ominous storm clouds at top
        for (int cl = 0; cl < 5; cl++)
        {
            int clx = cx + (cl - 2) * s * 16 / 100;
            int cly = y + s * 6 / 100 + (cl % 2) * s * 4 / 100;
            int clr = s * (12 + cl % 3 * 3) / 100;
            r.DrawCircle((55 + cl * 5, 50 + cl * 4, 70 + cl * 6), (clx, cly), clr, alpha: 240);
            r.DrawCircle((70 + cl * 5, 65 + cl * 4, 85 + cl * 6), (clx - 2, cly - 2), clr * 6 / 10, alpha: 200);
        }

        // === Ground scatter — textured dust cloud ===
        for (int ring = 4; ring >= 0; ring--)
        {
            int rr = s * (28 - ring * 4) / 100;
            int gv = 130 + ring * 12;
            r.DrawCircle((gv, gv - 20, gv - 50), (cx, cy + s * 32 / 100), rr, alpha: 240 - ring * 15);
        }
        // Scattered ground debris
        for (int d = 0; d < 8; d++)
        {
            double dAng = d * 0.8 + 0.3;
            int dx = cx + (int)(Math.Cos(dAng) * s * (24 + d * 2) / 100);
            int dy = cy + s * 34 / 100 + (int)(Math.Sin(dAng) * s * 3 / 100);
            r.DrawCircle((150, 130, 90), (dx, dy), Math.Max(1, s * (1 + d % 2) / 100), alpha: 220);
        }

        // === Tornado funnel — gradient-filled layers with depth ===
        for (int row = 0; row < 20; row++)
        {
            float t = row / 19f;
            int rowR = (int)(s * 3 / 100 + t * s * 28 / 100);
            int rowY = cy - s * 32 / 100 + (int)(t * s * 60 / 100);
            float wobble = (float)Math.Sin(t * 8 + row * 0.7) * s * 3 / 100;
            int rowX = cx + (int)wobble;

            // Fill each row with gradient color
            int rv = (int)(90 + 40 * (1f - t));
            int gv = (int)(130 + 50 * (1f - t));
            int bv = (int)(180 + 60 * (1f - t));
            r.DrawCircle((rv - 30, gv - 20, bv - 10), (rowX, rowY), rowR, alpha: 240 - (int)(t * 20));
            r.DrawCircle((rv, gv, bv), (rowX, rowY), rowR - 2, alpha: 230 - (int)(t * 15));
            // Highlight crescent on left
            r.DrawCircle((rv + 30, gv + 30, bv + 20), (rowX - rowR / 3, rowY), rowR / 3, alpha: 180);
        }

        // Inner rotation streaks — spiral pattern
        for (int streak = 0; streak < 10; streak++)
        {
            float st = streak / 9f;
            double angle = st * Math.PI * 3;
            int sR = (int)(s * 2 / 100 + st * s * 20 / 100);
            int sx1 = cx + (int)(Math.Cos(angle) * sR * 0.5f);
            int sy1 = cy - s * 28 / 100 + (int)(st * s * 50 / 100);
            int sx2 = cx + (int)(Math.Cos(angle + 0.8) * sR);
            int sy2 = sy1 + s * 4 / 100;
            r.DrawLine((180 + streak * 5, 210, 255), (sx1, sy1), (sx2, sy2), width: 2, alpha: 230 - streak * 8);
        }

        // === Vortex eye at top — glowing portal ===
        int eyeY = cy - s * 32 / 100;
        for (int ring = 4; ring >= 0; ring--)
        {
            int er = s * (6 - ring) / 100;
            r.DrawCircle((150 + ring * 25, 200 + ring * 10, 255), (cx, eyeY), Math.Max(1, er), alpha: 230);
        }
        // Eye sparkle
        r.DrawCircle((255, 255, 255), (cx - 1, eyeY - 1), Math.Max(1, s * 1 / 100), alpha: 255);

        // === Flying debris — detailed cards and objects with shadows ===
        (int dx, int dy, int dw, int dh, (int, int, int) col, string label)[] debris = [
            (-s * 24 / 100, -s * 10 / 100, s * 6 / 100, s * 8 / 100, (240, 60, 60), "♠"),
            (s * 20 / 100, -s * 18 / 100, s * 5 / 100, s * 7 / 100, (60, 180, 60), "♦"),
            (-s * 12 / 100, s * 8 / 100, s * 5 / 100, s * 7 / 100, (60, 100, 240), "♥"),
            (s * 10 / 100, s * 20 / 100, s * 5 / 100, s * 7 / 100, (200, 60, 200), "♣"),
            (-s * 30 / 100, s * 14 / 100, s * 5 / 100, s * 7 / 100, (240, 180, 40), "★"),
        ];
        foreach (var (dx, dy, dw, dh, col, label) in debris)
        {
            int ddx = cx + dx, ddy = cy + dy;
            int dW = Math.Max(4, dw), dH = Math.Max(6, dh);
            // Shadow
            r.DrawRect((0, 0, 0), (ddx + 2, ddy + 2, dW, dH), alpha: 200);
            // Card body with gradient
            r.DrawRect(col, (ddx, ddy, dW, dH), alpha: 255);
            r.DrawRect((col.Item1 + 30, col.Item2 + 30, col.Item3 + 20), (ddx + 1, ddy + 1, dW - 2, 2), alpha: 230);
            // Card border
            r.DrawRect((255, 255, 255), (ddx, ddy, dW, dH), width: 1, alpha: 240);
            // Symbol on card
            r.DrawText(label, ddx + dW / 2, ddy + dH / 2, Math.Max(3, dW * 4 / 10), (255, 255, 255),
                anchorX: "center", anchorY: "center", alpha: 240);
            // Motion trail
            r.DrawLine((col.Item1, col.Item2, col.Item3), (ddx + dW, ddy + dH / 2), (ddx + dW + s * 4 / 100, ddy + dH / 2 + 2), width: 1, alpha: 180);
        }

        // === Cat being sucked in — detailed panicked pose ===
        int catX = cx + s * 16 / 100, catY = cy - s * 12 / 100;
        // Body stretching toward funnel
        r.DrawCircle((200, 160, 80), (catX, catY), Math.Max(4, s * 6 / 100), alpha: 255);
        r.DrawCircle((220, 180, 100), (catX - 1, catY - 1), Math.Max(3, s * 4 / 100), alpha: 230);
        // Head
        r.DrawCircle((210, 170, 90), (catX + s * 4 / 100, catY - s * 4 / 100), Math.Max(3, s * 5 / 100), alpha: 255);
        // Scared wide eyes
        r.DrawCircle((255, 255, 255), (catX + s * 2 / 100, catY - s * 5 / 100), Math.Max(1, s * 2 / 100), alpha: 255);
        r.DrawCircle((255, 255, 255), (catX + s * 6 / 100, catY - s * 5 / 100), Math.Max(1, s * 2 / 100), alpha: 255);
        r.DrawCircle((0, 0, 0), (catX + s * 2 / 100, catY - s * 5 / 100), Math.Max(1, s * 1 / 100), alpha: 255);
        r.DrawCircle((0, 0, 0), (catX + s * 6 / 100, catY - s * 5 / 100), Math.Max(1, s * 1 / 100), alpha: 255);
        // Paws reaching out
        r.DrawLine((200, 160, 80), (catX - s * 5 / 100, catY + s * 2 / 100), (catX - s * 12 / 100, catY - s * 2 / 100), width: 2, alpha: 255);
        r.DrawLine((200, 160, 80), (catX + s * 8 / 100, catY + s * 2 / 100), (catX + s * 14 / 100, catY - s * 4 / 100), width: 2, alpha: 255);
        // Tail being pulled
        r.DrawLine((190, 150, 70), (catX - s * 4 / 100, catY + s * 4 / 100), (catX - s * 10 / 100, catY + s * 8 / 100), width: 2, alpha: 255);
        DrawSweatDrops(r, catX + s * 8 / 100, catY - s * 8 / 100, s, 3);

        // === Lightning in clouds ===
        r.DrawLine((200, 220, 255), (cx - s * 20 / 100, y + s * 12 / 100), (cx - s * 16 / 100, y + s * 18 / 100), width: 2, alpha: 240);
        r.DrawLine((200, 220, 255), (cx - s * 16 / 100, y + s * 18 / 100), (cx - s * 20 / 100, y + s * 24 / 100), width: 1, alpha: 200);
        r.DrawLine((220, 230, 255), (cx + s * 22 / 100, y + s * 10 / 100), (cx + s * 18 / 100, y + s * 16 / 100), width: 2, alpha: 220);

        // === Embossed "WHOOSH!" text ===
        int wFs = Math.Max(6, s * 6 / 100);
        r.DrawText("WHOOSH!", cx + 2, cy + s * 38 / 100 + 2, wFs, (40, 50, 80), bold: true, anchorX: "center", anchorY: "center", alpha: 220);
        r.DrawText("WHOOSH!", cx, cy + s * 38 / 100, wFs, (180, 220, 255), bold: true, anchorX: "center", anchorY: "center", alpha: 255);

        // Sparkles around vortex
        DrawSparkle(r, cx - s * 14 / 100, eyeY + s * 4 / 100, s * 2 / 100, (180, 220, 255), 230);
        DrawSparkle(r, cx + s * 12 / 100, eyeY + s * 6 / 100, s * 18 / 1000, (200, 240, 255), 220);
        DrawSparkle(r, cx, cy + s * 26 / 100, s * 15 / 1000, (160, 200, 240), 210);

        // Warning symbols
        r.DrawText("⚠", cx - s * 32 / 100, cy + s * 30 / 100, Math.Max(5, s * 5 / 100), (255, 200, 80),
            anchorX: "center", anchorY: "center", alpha: 230);
        r.DrawText("🌀", cx + s * 30 / 100, cy - s * 28 / 100, Math.Max(5, s * 5 / 100), (160, 200, 255),
            anchorX: "center", anchorY: "center", alpha: 220);
    }

    private static void DrawSHUF_CircularArrows(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);
        int arrowR = s * 26 / 100;

        // === Vortex swirl background ===
        // Spiral energy rings — 3D depth
        for (int ring = 7; ring >= 0; ring--)
        {
            int rr = s * (6 + ring * 5) / 100;
            int rv = 30 + ring * 10;
            int gv = 60 + ring * 18;
            int bv = 120 + ring * 16;
            r.DrawCircle((rv, gv, Math.Min(255, bv)), (cx, cy), rr, width: 2, alpha: 200 - ring * 15);
        }
        // Radial swirl lines — curved motion
        for (int sw = 0; sw < 12; sw++)
        {
            double ang = sw * Math.PI / 6;
            int innerR = s * 3 / 100;
            int outerR = s * (32 + (sw % 3) * 5) / 100;
            // Curved: offset end angle slightly for swirl
            double endAng = ang + 0.3;
            int x1 = cx + (int)(Math.Cos(ang) * innerR);
            int y1 = cy + (int)(Math.Sin(ang) * innerR);
            int x2 = cx + (int)(Math.Cos(endAng) * outerR);
            int y2 = cy + (int)(Math.Sin(endAng) * outerR);
            var sCol = sw % 3 == 0 ? (60, 140, 220) : sw % 3 == 1 ? (80, 200, 160) : (50, 120, 200);
            r.DrawLine(sCol, (x1, y1), (x2, y2), width: 1, alpha: 180 - sw * 6);
        }

        // === Scattered flying cards in background ===
        (int ox, int oy, double rot)[] bgCards = [
            (-s * 28 / 100, -s * 18 / 100, -0.4),
            (s * 24 / 100, -s * 22 / 100, 0.3),
            (-s * 22 / 100, s * 20 / 100, 0.5),
            (s * 26 / 100, s * 16 / 100, -0.2),
        ];
        foreach (var (ox, oy, rot) in bgCards)
        {
            int cardW = s * 8 / 100, cardH = s * 12 / 100;
            int ccx = cx + ox, ccy = cy + oy;
            // Card shadow
            r.DrawRect((20, 20, 30), (ccx + 2, ccy + 2, cardW, cardH), alpha: 160);
            // Card back — colorful
            r.DrawRect((220, 220, 240), (ccx, ccy, cardW, cardH), alpha: 230);
            r.DrawRect((100, 140, 220), (ccx + 2, ccy + 2, cardW - 4, cardH - 4), alpha: 220);
            // Mini pattern
            r.DrawCircle((140, 180, 240), (ccx + cardW / 2, ccy + cardH / 2), cardW / 4, alpha: 200);
            // Card edge
            r.DrawRect((180, 180, 200), (ccx, ccy, cardW, cardH), width: 1, alpha: 240);
        }

        // === Two curved gradient arrows forming circle ===
        for (int a = 0; a < 2; a++)
        {
            double offset = a * Math.PI;
            var mainCol = a == 0 ? (80, 180, 255) : (100, 220, 160);
            var darkCol = a == 0 ? (30, 100, 180) : (40, 140, 80);
            var lightCol = a == 0 ? (150, 220, 255) : (160, 245, 210);
            var glowCol = a == 0 ? (60, 140, 220) : (70, 180, 130);

            // Outer glow arc
            for (double ang = 0; ang < Math.PI * 0.82; ang += 0.04)
            {
                double realAng = ang + offset;
                int ax = cx + (int)(Math.Cos(realAng) * arrowR);
                int ay = cy + (int)(Math.Sin(realAng) * arrowR);
                r.DrawCircle(glowCol, (ax, ay), Math.Max(4, s * 5 / 100), alpha: 160);
            }
            // Shadow arc
            for (double ang = 0; ang < Math.PI * 0.8; ang += 0.04)
            {
                double realAng = ang + offset;
                int ax = cx + (int)(Math.Cos(realAng) * arrowR) + 2;
                int ay = cy + (int)(Math.Sin(realAng) * arrowR) + 2;
                r.DrawCircle(darkCol, (ax, ay), Math.Max(3, s * 4 / 100), alpha: 230);
            }
            // Main arc — thick with gradient
            for (double ang = 0; ang < Math.PI * 0.8; ang += 0.04)
            {
                double realAng = ang + offset;
                float t = (float)(ang / (Math.PI * 0.8));
                int ax = cx + (int)(Math.Cos(realAng) * arrowR);
                int ay = cy + (int)(Math.Sin(realAng) * arrowR);
                // Color shifts along arc
                int rr = (int)(mainCol.Item1 + (lightCol.Item1 - mainCol.Item1) * t);
                int gg = (int)(mainCol.Item2 + (lightCol.Item2 - mainCol.Item2) * t);
                int bb = (int)(mainCol.Item3 + (lightCol.Item3 - mainCol.Item3) * t);
                r.DrawCircle((rr, gg, bb), (ax, ay), Math.Max(3, s * 4 / 100), alpha: 255);
            }
            // Inner highlight arc
            for (double ang = 0.1; ang < Math.PI * 0.72; ang += 0.06)
            {
                double realAng = ang + offset;
                int ax = cx + (int)(Math.Cos(realAng) * (arrowR - s * 2 / 100));
                int ay = cy + (int)(Math.Sin(realAng) * (arrowR - s * 2 / 100));
                r.DrawCircle(lightCol, (ax, ay), Math.Max(1, s * 15 / 1000), alpha: 220);
            }

            // Arrow head — larger, 3D
            double eAng = Math.PI * 0.8 + offset;
            int ex = cx + (int)(Math.Cos(eAng) * arrowR);
            int ey = cy + (int)(Math.Sin(eAng) * arrowR);
            double tangent = eAng + Math.PI / 2;
            int tipX = ex + (int)(Math.Cos(eAng) * s * 10 / 100);
            int tipY = ey + (int)(Math.Sin(eAng) * s * 10 / 100);
            int baseAX = ex + (int)(Math.Cos(tangent) * s * 7 / 100);
            int baseAY = ey + (int)(Math.Sin(tangent) * s * 7 / 100);
            int baseBX = ex - (int)(Math.Cos(tangent) * s * 7 / 100);
            int baseBY = ey - (int)(Math.Sin(tangent) * s * 7 / 100);
            // Arrow shadow
            DrawTriangle(r, darkCol, tipX + 2, tipY + 2, baseAX + 2, baseAY + 2, baseBX + 2, baseBY + 2, 200);
            // Arrow fill
            DrawTriangle(r, mainCol, tipX, tipY, baseAX, baseAY, baseBX, baseBY, 255);
            // Arrow outline
            r.DrawLine(darkCol, (tipX, tipY), (baseAX, baseAY), width: 2, alpha: 255);
            r.DrawLine(darkCol, (tipX, tipY), (baseBX, baseBY), width: 2, alpha: 255);
            r.DrawLine(darkCol, (baseAX, baseAY), (baseBX, baseBY), width: 1, alpha: 200);
        }

        // === Deck of cards at center ===
        int deckW = s * 10 / 100, deckH = s * 14 / 100;
        // Stack of 3 cards fanned
        for (int cd = 0; cd < 3; cd++)
        {
            int cdx = cx - deckW / 2 + (cd - 1) * s * 2 / 100;
            int cdy = cy - deckH / 2 + (cd - 1) * 1;
            r.DrawRect((240, 235, 225), (cdx, cdy, deckW, deckH), alpha: 240 - cd * 20);
            r.DrawRect((80, 80, 100), (cdx, cdy, deckW, deckH), width: 1, alpha: 220);
            // Card back pattern
            r.DrawRect((80 + cd * 20, 130 + cd * 15, 200 - cd * 10), (cdx + 2, cdy + 2, deckW - 4, deckH - 4), alpha: 200 - cd * 25);
        }
        // Question mark on top card
        r.DrawText("?", cx, cy, Math.Max(5, s * 5 / 100), (255, 255, 240),
            bold: true, anchorX: "center", anchorY: "center", alpha: 240);

        // === Energy particles along arrow path ===
        for (int sp = 0; sp < 8; sp++)
        {
            double spAng = sp * Math.PI * 2 / 8 + 0.5;
            int spDist = arrowR + s * (6 + (sp % 3) * 2) / 100;
            int spX = cx + (int)(Math.Cos(spAng) * spDist);
            int spY = cy + (int)(Math.Sin(spAng) * spDist);
            var spCol = sp % 2 == 0 ? (120, 200, 255) : (140, 240, 180);
            r.DrawCircle(spCol, (spX, spY), Math.Max(1, s * 12 / 1000 + 1), alpha: 220 - sp * 10);
            // Tiny trail
            int tLen = s * 3 / 100;
            int tx = spX + (int)(Math.Cos(spAng + 0.5) * tLen);
            int ty = spY + (int)(Math.Sin(spAng + 0.5) * tLen);
            r.DrawLine(spCol, (spX, spY), (tx, ty), width: 1, alpha: 160 - sp * 8);
        }

        // === "SHUFFLE!" text — embossed ===
        int shufFs = Math.Max(6, s * 6 / 100);
        r.DrawText("SHUFFLE!", cx + 1, cy + arrowR + s * 13 / 100 + 1, shufFs, (20, 60, 120), bold: true, anchorX: "center", anchorY: "center", alpha: 220);
        r.DrawText("SHUFFLE!", cx, cy + arrowR + s * 13 / 100, shufFs, (100, 210, 255), bold: true, anchorX: "center", anchorY: "center", alpha: 255);

        // === Shuffle symbols ===
        r.DrawText("🔀", cx - s * 30 / 100, cy - s * 26 / 100, Math.Max(5, s * 5 / 100), (120, 200, 255),
            anchorX: "center", anchorY: "center", alpha: 220);

        // Sparkles at key points
        DrawSparkle(r, cx + arrowR + s * 4 / 100, cy - s * 10 / 100, s * 2 / 100, (120, 220, 255), 230);
        DrawSparkle(r, cx - arrowR - s * 3 / 100, cy + s * 8 / 100, s * 18 / 1000, (160, 255, 190), 220);

        // Bold outline on deck
        DrawBoldRectOutline(r, cx - deckW / 2, cy - deckH / 2, deckW, deckH, 220);
    }

    private static void DrawSHUF_FlyingCards(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // === Magical wind vortex background — radial gradient ===
        for (int ring = 8; ring >= 0; ring--)
        {
            int rr = s * (42 - ring * 4) / 100;
            int rv = 60 + ring * 10;
            int gv = 80 + ring * 12;
            int bv = 160 + ring * 10;
            r.DrawCircle((rv, gv, bv), (cx, cy), rr, alpha: 220 - ring * 12);
        }
        // Spiral wind streaks
        for (int streak = 0; streak < 12; streak++)
        {
            double ang = streak * Math.PI / 6 + 0.3;
            int innerR = s * 8 / 100;
            int outerR = s * (28 + streak % 3 * 5) / 100;
            int sx1 = cx + (int)(Math.Cos(ang) * innerR);
            int sy1 = cy + (int)(Math.Sin(ang) * innerR);
            int sx2 = cx + (int)(Math.Cos(ang + 0.4) * outerR);
            int sy2 = cy + (int)(Math.Sin(ang + 0.4) * outerR);
            r.DrawLine((140 + streak * 5, 180, 240), (sx1, sy1), (sx2, sy2), width: 1, alpha: 180 - streak * 6);
        }

        // === Center energy burst — where cards erupt from ===
        for (int glow = 3; glow >= 0; glow--)
        {
            int gr = s * (8 - glow * 2) / 100;
            r.DrawCircle((220 + glow * 10, 200 + glow * 10, 120 + glow * 30), (cx, cy), Math.Max(2, gr), alpha: 220);
        }

        // === Six detailed flying cards — each with rich rendering ===
        (int ox, int oy, (int, int, int) face, string suit, bool showFace)[] cards = [
            (-s * 22 / 100, -s * 18 / 100, (220, 50, 60), "♠", true),
            (s * 18 / 100, -s * 12 / 100, (50, 160, 60), "♦", false),
            (-s * 12 / 100, s * 12 / 100, (50, 100, 220), "♥", true),
            (s * 24 / 100, s * 16 / 100, (220, 180, 40), "♣", false),
            (0, -s * 26 / 100, (180, 60, 200), "A", true),
            (-s * 26 / 100, s * 2 / 100, (220, 130, 30), "K", false),
        ];
        int cIdx = 0;
        foreach (var (ox, oy, face, suit, showFace) in cards)
        {
            cIdx++;
            int cW = Math.Max(6, s * 14 / 100), cH = Math.Max(8, s * 20 / 100);
            int cX = cx + ox - cW / 2, cY = cy + oy - cH / 2;

            // Card shadow
            r.DrawRect((0, 0, 0), (cX + 3, cY + 3, cW, cH), alpha: 200);

            if (showFace)
            {
                // Face side — rich gradient body
                for (int row = 0; row < cH; row++)
                {
                    float t = (float)row / cH;
                    int rv = face.Item1 + (int)(20 * t);
                    int gv = face.Item2 + (int)(15 * t);
                    int bv = face.Item3 + (int)(10 * t);
                    r.DrawRect((Math.Min(255, rv), Math.Min(255, gv), Math.Min(255, bv)), (cX, cY + row, cW, 1), alpha: 255);
                }
                // White border
                r.DrawRect((255, 255, 255), (cX, cY, cW, cH), width: 1, alpha: 255);
                // Suit symbol centered
                int symFs = Math.Max(4, cW * 5 / 10);
                r.DrawText(suit, cX + cW / 2, cY + cH / 2, symFs, (255, 255, 255),
                    anchorX: "center", anchorY: "center", alpha: 250);
                // Corner suit small
                r.DrawText(suit, cX + s * 2 / 100, cY + s * 2 / 100, Math.Max(3, cW / 4), (255, 255, 255),
                    anchorX: "center", anchorY: "center", alpha: 220);
                // Specular highlight
                r.DrawRect((255, 255, 255), (cX + 2, cY + 2, cW / 3, 2), alpha: 200);
            }
            else
            {
                // Back side — ornate dark design
                r.DrawRect((30, 22, 50), (cX, cY, cW, cH), alpha: 255);
                // Gold border
                r.DrawRect((220, 170, 50), (cX, cY, cW, cH), width: 1, alpha: 255);
                r.DrawRect((200, 150, 40), (cX + 2, cY + 2, cW - 4, cH - 4), width: 1, alpha: 220);
                // Diamond pattern
                int dmx = cX + cW / 2, dmy = cY + cH / 2;
                int dmr = Math.Max(2, cW / 4);
                r.DrawLine((220, 180, 60), (dmx, dmy - dmr), (dmx + dmr, dmy), width: 1, alpha: 240);
                r.DrawLine((220, 180, 60), (dmx + dmr, dmy), (dmx, dmy + dmr), width: 1, alpha: 240);
                r.DrawLine((220, 180, 60), (dmx, dmy + dmr), (dmx - dmr, dmy), width: 1, alpha: 240);
                r.DrawLine((220, 180, 60), (dmx - dmr, dmy), (dmx, dmy - dmr), width: 1, alpha: 240);
                // Inner oval
                r.DrawCircle((200, 160, 50), (dmx, dmy), Math.Max(1, cW / 5), width: 1, alpha: 200);
            }

            // Motion trail streaks behind each card
            double trailAng = Math.Atan2(oy, ox) + Math.PI;
            for (int tr = 0; tr < 3; tr++)
            {
                int tx = cX + cW / 2 + (int)(Math.Cos(trailAng) * (s * 3 / 100 + tr * s * 2 / 100));
                int ty = cY + cH / 2 + (int)(Math.Sin(trailAng) * (s * 3 / 100 + tr * s * 2 / 100));
                r.DrawLine((200, 200, 255), (cX + cW / 2, cY + cH / 2), (tx, ty), width: 1, alpha: 180 - tr * 40);
            }

            // Bold outline
            DrawBoldRectOutline(r, cX, cY, cW, cH, 220);
        }

        // === Card suit symbols scattered in background ===
        r.DrawText("♠", cx + s * 32 / 100, cy - s * 32 / 100, Math.Max(6, s * 5 / 100), (180, 180, 220),
            anchorX: "center", anchorY: "center", alpha: 240);
        r.DrawText("♥", cx - s * 32 / 100, cy + s * 32 / 100, Math.Max(6, s * 5 / 100), (220, 100, 100),
            anchorX: "center", anchorY: "center", alpha: 240);
        r.DrawText("♦", cx + s * 30 / 100, cy + s * 30 / 100, Math.Max(5, s * 4 / 100), (220, 160, 60),
            anchorX: "center", anchorY: "center", alpha: 220);
        r.DrawText("♣", cx - s * 30 / 100, cy - s * 30 / 100, Math.Max(5, s * 4 / 100), (100, 200, 100),
            anchorX: "center", anchorY: "center", alpha: 220);

        // === Embossed "SHUFFLE!" text ===
        int shFs = Math.Max(6, s * 5 / 100);
        r.DrawText("SHUFFLE!", cx + 2, cy + s * 38 / 100 + 2, shFs, (40, 40, 80), bold: true, anchorX: "center", anchorY: "center", alpha: 220);
        r.DrawText("SHUFFLE!", cx, cy + s * 38 / 100, shFs, (200, 180, 255), bold: true, anchorX: "center", anchorY: "center", alpha: 255);

        // Energy sparkles
        DrawSparkle(r, cx - s * 24 / 100, cy - s * 24 / 100, s * 2 / 100, (255, 255, 150), 230);
        DrawSparkle(r, cx + s * 26 / 100, cy + s * 22 / 100, s * 18 / 1000, (255, 200, 100), 220);
        DrawSparkle(r, cx - s * 8 / 100, cy + s * 26 / 100, s * 15 / 1000, (200, 255, 200), 210);
        DrawSparkle(r, cx + s * 10 / 100, cy - s * 28 / 100, s * 2 / 100, (180, 200, 255), 220);

        // Dizzy cat in the chaos
        DrawMiniCatFace(r, cx - s * 30 / 100, cy - s * 26 / 100, s * 5 / 100, (200, 170, 100), 240);
        DrawSweatDrops(r, cx - s * 26 / 100, cy - s * 30 / 100, s, 2);
    }

    private static void DrawSHUF_ChaosDice(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // === Chaos vortex background — deep purple-violet radial gradient ===
        for (int ring = 10; ring >= 0; ring--)
        {
            int rr = s * (44 - ring * 3) / 100;
            int rv = 40 + ring * 8;
            int gv = 20 + ring * 5;
            int bv = 80 + ring * 14;
            r.DrawCircle((rv, gv, bv), (cx, cy), rr, alpha: 220 - ring * 10);
        }

        // Felt table surface at bottom — gradient green
        int tableTop = cy + s * 10 / 100;
        for (int row = 0; row < s * 32 / 100; row++)
        {
            float t = (float)row / (s * 32 / 100);
            int gv2 = (int)(120 - 40 * t);
            r.DrawRect((20, gv2, 30), (x, tableTop + row, w, 1), alpha: 240);
        }
        // Table edge highlight
        r.DrawLine((80, 180, 60), (x + s * 4 / 100, tableTop), (x + w - s * 4 / 100, tableTop), width: 2, alpha: 220);

        // Chaos spiral energy rings behind dice
        for (int sp = 0; sp < 8; sp++)
        {
            double spAng = sp * Math.PI / 4;
            int spR = s * (16 + sp * 3) / 100;
            int spx = cx + (int)(Math.Cos(spAng) * s * 5 / 100);
            int spy = cy + (int)(Math.Sin(spAng) * s * 5 / 100);
            r.DrawCircle((120 + sp * 10, 80 + sp * 5, 200 - sp * 5), (spx, spy), spR, width: 1, alpha: 160 - sp * 10);
        }

        // === Five detailed dice tumbling with gradient fills ===
        (int ox, int oy, int sz, int face, (int, int, int) col)[] dice = [
            (-s * 18 / 100, -s * 14 / 100, s * 18 / 100, 6, (230, 50, 50)),
            (s * 14 / 100, s * 6 / 100, s * 16 / 100, 3, (50, 100, 230)),
            (s * 5 / 100, -s * 24 / 100, s * 14 / 100, 1, (50, 190, 70)),
            (-s * 14 / 100, s * 14 / 100, s * 13 / 100, 5, (230, 190, 30)),
            (s * 22 / 100, -s * 10 / 100, s * 11 / 100, 4, (200, 80, 220)),
        ];

        foreach (var (ox, oy, sz, face, col) in dice)
        {
            int dx = cx + ox, dy = cy + oy;
            int hs = sz / 2;

            // Deep shadow
            r.DrawRect((0, 0, 0), (dx - hs + 4, dy - hs + 4, sz, sz), alpha: 200);

            // Die body — row-by-row gradient fill for richness
            for (int row = 0; row < sz; row++)
            {
                float t = (float)row / sz;
                int rv = Math.Min(255, col.Item1 + (int)(30 * t));
                int gv = Math.Min(255, col.Item2 + (int)(20 * t));
                int bv = Math.Min(255, col.Item3 + (int)(15 * t));
                r.DrawRect((rv, gv, bv), (dx - hs, dy - hs + row, sz, 1), alpha: 255);
            }

            // 3D right edge — darker
            int edgeW = Math.Max(2, sz / 5);
            r.DrawRect((col.Item1 / 3, col.Item2 / 3, col.Item3 / 3), (dx + hs - edgeW, dy - hs, edgeW, sz), alpha: 220);
            // 3D bottom edge — darker
            r.DrawRect((col.Item1 / 3, col.Item2 / 3, col.Item3 / 3), (dx - hs, dy + hs - edgeW, sz, edgeW), alpha: 220);
            // Specular highlight — top-left
            r.DrawRect((255, 255, 255), (dx - hs + 2, dy - hs + 2, sz / 2, 2), alpha: 200);
            r.DrawRect((255, 255, 255), (dx - hs + 2, dy - hs + 2, 2, sz / 3), alpha: 180);

            // White border
            r.DrawRect((255, 255, 255), (dx - hs, dy - hs, sz, sz), width: 1, alpha: 255);

            // Rounded corners
            int cr = Math.Max(1, sz / 8);
            r.DrawCircle(col, (dx - hs + cr, dy - hs + cr), cr, alpha: 255);
            r.DrawCircle(col, (dx + hs - cr, dy - hs + cr), cr, alpha: 255);
            r.DrawCircle(col, (dx - hs + cr, dy + hs - cr), cr, alpha: 255);
            r.DrawCircle(col, (dx + hs - cr, dy + hs - cr), cr, alpha: 255);

            // Pips — white with shadow
            int pip = Math.Max(2, sz / 7);
            int inset = sz / 4;
            void DrawPip(int px, int py)
            {
                r.DrawCircle((0, 0, 0), (px + 1, py + 1), pip, alpha: 160); // shadow
                r.DrawCircle((255, 255, 255), (px, py), pip, alpha: 255);
                r.DrawCircle((220, 220, 220), (px, py), Math.Max(1, pip - 1), alpha: 180); // inner depth
            }
            if (face == 1 || face == 3 || face == 5) DrawPip(dx, dy);
            if (face >= 2) { DrawPip(dx + inset, dy - inset); DrawPip(dx - inset, dy + inset); }
            if (face >= 4) { DrawPip(dx - inset, dy - inset); DrawPip(dx + inset, dy + inset); }
            if (face == 6) { DrawPip(dx - inset, dy); DrawPip(dx + inset, dy); }

            // Bold outline
            DrawBoldRectOutline(r, dx - hs, dy - hs, sz, sz, 220);

            // Motion arcs trailing behind
            double moveAng = Math.Atan2(oy, ox) + Math.PI;
            for (int ma = 0; ma < 3; ma++)
            {
                int mx1 = dx + (int)(Math.Cos(moveAng + 0.2 * ma) * (sz / 2 + ma * s * 3 / 100));
                int my1 = dy + (int)(Math.Sin(moveAng + 0.2 * ma) * (sz / 2 + ma * s * 3 / 100));
                int mx2 = dx + (int)(Math.Cos(moveAng - 0.2 * ma) * (sz / 2 + ma * s * 3 / 100));
                int my2 = dy + (int)(Math.Sin(moveAng - 0.2 * ma) * (sz / 2 + ma * s * 3 / 100));
                r.DrawLine((200, 180, 255), (mx1, my1), (mx2, my2), width: 1, alpha: 160 - ma * 40);
            }
        }

        // === Center chaos burst — glowing "?" ===
        for (int glow = 4; glow >= 0; glow--)
        {
            int gr = s * (7 - glow) / 100;
            r.DrawCircle((220 + glow * 8, 180 + glow * 15, 60 + glow * 20), (cx, cy), Math.Max(2, gr), alpha: 200 - glow * 20);
        }
        int qFs = Math.Max(8, s * 10 / 100);
        r.DrawText("?", cx + 2, cy + 2, qFs, (60, 20, 80), bold: true, anchorX: "center", anchorY: "center", alpha: 220);
        r.DrawText("?", cx, cy, qFs, (255, 255, 200), bold: true, anchorX: "center", anchorY: "center", alpha: 255);

        // Scattered number symbols showing randomness
        r.DrawText("7", cx + s * 28 / 100, cy - s * 30 / 100, Math.Max(5, s * 5 / 100), (255, 200, 80),
            bold: true, anchorX: "center", anchorY: "center", alpha: 220);
        r.DrawText("13", cx - s * 30 / 100, cy + s * 28 / 100, Math.Max(5, s * 4 / 100), (200, 100, 100),
            bold: true, anchorX: "center", anchorY: "center", alpha: 200);
        r.DrawText("!", cx + s * 30 / 100, cy + s * 28 / 100, Math.Max(5, s * 5 / 100), (255, 150, 80),
            bold: true, anchorX: "center", anchorY: "center", alpha: 220);

        // Embossed "CHAOS!" text
        int chFs = Math.Max(6, s * 5 / 100);
        r.DrawText("CHAOS!", cx + 2, cy + s * 38 / 100 + 2, chFs, (40, 20, 60), bold: true, anchorX: "center", anchorY: "center", alpha: 220);
        r.DrawText("CHAOS!", cx, cy + s * 38 / 100, chFs, (255, 180, 80), bold: true, anchorX: "center", anchorY: "center", alpha: 255);

        // Energy sparkles
        DrawSparkle(r, cx - s * 30 / 100, cy - s * 6 / 100, s * 2 / 100, (255, 220, 100), 230);
        DrawSparkle(r, cx + s * 28 / 100, cy - s * 20 / 100, s * 18 / 1000, (100, 255, 200), 220);
        DrawSparkle(r, cx - s * 10 / 100, cy - s * 32 / 100, s * 15 / 1000, (255, 180, 255), 210);
        DrawSparkle(r, cx + s * 8 / 100, cy + s * 28 / 100, s * 2 / 100, (200, 255, 150), 220);

        // Cat being tossed in chaos
        DrawMiniCatFace(r, cx + s * 4 / 100, cy + s * 26 / 100, s * 5 / 100, (180, 150, 90), 240);
        DrawSweatDrops(r, cx + s * 8 / 100, cy + s * 22 / 100, s, 3);
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

        // === DEEP MYSTICAL GRADIENT BACKGROUND ===
        for (int row = 0; row < h; row++)
        {
            float t = (float)row / h;
            int rr = (int)(20 + 50 * t);      // deep indigo → dark purple
            int gg = (int)(10 + 20 * t);
            int bb = (int)(60 + 80 * (1f - t * 0.5f));
            r.DrawRect((rr, gg, bb), (x, y + row, w, 1), alpha: 255);
        }

        // Mystical energy nebula clouds in background
        r.DrawCircle((60, 20, 120), (cx - s * 25 / 100, cy - s * 20 / 100), s * 15 / 100, alpha: 120);
        r.DrawCircle((80, 30, 100), (cx + s * 28 / 100, cy + s * 15 / 100), s * 12 / 100, alpha: 100);
        r.DrawCircle((50, 15, 90), (cx + s * 10 / 100, cy - s * 30 / 100), s * 10 / 100, alpha: 80);

        // Background stars
        for (int i = 0; i < 12; i++)
        {
            int sx = cx + (int)((i * 5839 % 71 - 35) * s / 100.0);
            int sy = cy + (int)((i * 4271 % 61 - 30) * s / 100.0);
            r.DrawCircle((180, 170, 240), (sx, sy), 1, alpha: 200 - i * 10);
        }

        // Deep mystical aura — multi-layered halos with gradient
        for (int ring = 8; ring >= 1; ring--)
        {
            int rr2 = ballR + s * (4 + ring * 3) / 100;
            float t = (float)ring / 8;
            int c1 = (int)(60 + 100 * (1f - t));
            int c2 = (int)(20 + 50 * (1f - t));
            int c3 = (int)(140 + 80 * (1f - t));
            r.DrawCircle((c1, c2, c3), (cx, ballCy), rr2, width: 2, alpha: (int)(80 + 120 * (1f - t)));
        }

        // Ball glass — rich metallic gradient layers (finer grain)
        for (int i = ballR; i >= 0; i--)
        {
            float t = (float)i / ballR;
            int blue = (int)(80 + 120 * t);
            int green = (int)(30 + 60 * t);
            int red = (int)(20 + 35 * t);
            r.DrawCircle((red, green, blue), (cx, ballCy), i, alpha: 255);
        }

        // Glass refraction highlights — more layers
        r.DrawCircle((160, 140, 230), (cx - ballR / 3, ballCy - ballR / 3), ballR / 3, alpha: 180);
        r.DrawCircle((200, 180, 255), (cx - ballR / 3, ballCy - ballR / 3), ballR / 5, alpha: 220);
        r.DrawCircle((255, 240, 255), (cx - ballR / 4, ballCy - ballR / 4), ballR / 8, alpha: 200);
        // Secondary highlight
        r.DrawCircle((140, 120, 210), (cx + ballR / 4, ballCy + ballR / 4), ballR / 5, alpha: 160);

        // Inner swirl energy — mystical vortex patterns
        r.DrawCircle((160, 100, 255), (cx + s * 5 / 100, ballCy - s * 1 / 100), ballR * 45 / 100, width: 2, alpha: 200);
        r.DrawCircle((200, 140, 255), (cx - s * 4 / 100, ballCy + s * 3 / 100), ballR * 35 / 100, width: 2, alpha: 200);
        r.DrawCircle((180, 120, 255), (cx - s * 1 / 100, ballCy - s * 5 / 100), ballR * 25 / 100, width: 1, alpha: 220);
        r.DrawCircle((220, 160, 255), (cx + s * 2 / 100, ballCy + s * 5 / 100), ballR * 20 / 100, width: 1, alpha: 180);

        // Inner sparks — five tiny stars with enhanced glow
        for (int i = 0; i < 5; i++)
        {
            int sx = cx + (int)(MathF.Cos(i * 1.26f) * ballR * 0.42f);
            int sy = ballCy + (int)(MathF.Sin(i * 1.26f) * ballR * 0.38f);
            r.DrawCircle((180, 160, 255), (sx, sy), 3, alpha: 200); // glow
            r.DrawCircle((240, 220, 255), (sx, sy), 2, alpha: 255);
            // Cross on each spark
            r.DrawRect((240, 220, 255), (sx - 4, sy, 9, 1), alpha: 255);
            r.DrawRect((240, 220, 255), (sx, sy - 4, 1, 9), alpha: 255);
        }

        // Swirling mist inside ball — gradient-filled wisps
        for (int mist = 0; mist < 5; mist++)
        {
            double mAng = mist * Math.PI / 2.5 + 0.6;
            int mR = ballR * 55 / 100;
            int mx = cx + (int)(Math.Cos(mAng) * mR);
            int my = ballCy + (int)(Math.Sin(mAng) * mR * 7 / 10);
            int wr = Math.Max(3, s * 4 / 100);
            for (int ring = wr; ring >= 1; ring--)
            {
                float t = (float)ring / wr;
                r.DrawCircle(((int)(80 + 40 * (1f - t)), (int)(40 + 30 * (1f - t)), (int)(180 + 50 * (1f - t))), (mx, my), ring, alpha: (int)(120 * t + 60));
            }
        }

        // === BASE/STAND — ornate with gradient fill ===
        int baseW = ballR * 130 / 100, baseH = s * 10 / 100;
        int baseY = ballCy + ballR - 3;
        // Stand shadow
        r.DrawRect((0, 0, 0), (cx - baseW / 2 + 3, baseY + 3, baseW, baseH), alpha: 200);
        // Main base — gradient fill
        for (int row = 0; row < baseH; row++)
        {
            float t = (float)row / baseH;
            int c = (int)(100 - 40 * t);
            r.DrawRect((c, c - 20, c - 50), (cx - baseW / 2, baseY + row, baseW, 1), alpha: 255);
        }
        // Metallic highlight bands
        r.DrawRect((160, 140, 100), (cx - baseW / 2 + 2, baseY + 1, baseW - 4, 2), alpha: 255);
        r.DrawRect((130, 110, 80), (cx - baseW / 2 + 3, baseY + baseH - 3, baseW - 6, 2), alpha: 255);
        // Rim at junction — gradient
        for (int row = 0; row < 5; row++)
        {
            int c = 90 + row * 8;
            r.DrawRect((c, c - 10, c - 30), (cx - ballR * 55 / 100, baseY - 3 + row, ballR * 110 / 100, 1), alpha: 255);
        }
        // Decorative gems on base
        r.DrawCircle((160, 80, 220), (cx - baseW / 4, baseY + baseH / 2), Math.Max(1, s * 1 / 100), alpha: 255);
        r.DrawCircle((220, 80, 160), (cx + baseW / 4, baseY + baseH / 2), Math.Max(1, s * 1 / 100), alpha: 255);
        r.DrawCircle((80, 180, 200), (cx, baseY + baseH / 2), Math.Max(1, s * 12 / 1000), alpha: 255);

        // Floating rune symbols around ball — more
        string[] runes = { "✦", "✧", "⟡", "◇" };
        for (int i = 0; i < 4; i++)
        {
            double ang = i * Math.PI / 2 + Math.PI / 4;
            int rx = cx + (int)(Math.Cos(ang) * (ballR + s * 10 / 100));
            int ry = ballCy + (int)(Math.Sin(ang) * (ballR + s * 8 / 100));
            r.DrawText(runes[i], rx, ry, Math.Max(5, s * 5 / 100), (180, 140, 255),
                anchorX: "center", anchorY: "center", alpha: 220);
        }

        // Bold outlines
        DrawBoldCircleOutline(r, cx, ballCy, ballR, 220);
        DrawBoldRectOutline(r, cx - baseW / 2, baseY, baseW, baseH, 220);

        // === SPARKLE ACCENTS ===
        DrawSparkle(r, cx - s * 30 / 100, ballCy - s * 18 / 100, s * 2 / 100, (200, 160, 255), 240);
        DrawSparkle(r, cx + s * 28 / 100, ballCy + s * 6 / 100, s * 2 / 100, (140, 220, 255), 230);
        DrawSparkle(r, cx - s * 6 / 100, ballCy - s * 30 / 100, s * 18 / 1000, (220, 200, 255), 220);
        DrawSparkle(r, cx + s * 20 / 100, ballCy - s * 22 / 100, s * 15 / 1000, (255, 200, 255), 210);

        // Mini cat face peeking from behind ball
        DrawMiniCatFace(r, cx + s * 24 / 100, ballCy + ballR - s * 2 / 100, s * 5 / 100, (180, 140, 80), 240);

        // === EMBOSSED "FUTURE?" TEXT ===
        r.DrawText("FUTURE?", cx, cy + s * 38 / 100, Math.Max(6, s * 7 / 100), (40, 20, 80),
            bold: true, anchorX: "center", anchorY: "center", alpha: 200);
        r.DrawText("FUTURE?", cx - 1, cy + s * 38 / 100 - 1, Math.Max(6, s * 7 / 100), (180, 140, 255),
            bold: true, anchorX: "center", anchorY: "center", alpha: 255);
    }

    private static void DrawFUT_ThirdEye(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // Cosmic background — concentric mystical rings
        r.DrawCircle((80, 40, 160), (cx, cy), s * 40 / 100, alpha: 255);
        r.DrawCircle((100, 50, 180), (cx, cy), s * 34 / 100, alpha: 255);
        r.DrawCircle((120, 60, 200), (cx, cy), s * 28 / 100, alpha: 255);

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
            r.DrawLine(rayCol, (ex1, ey1), (ex2, ey2), width: 1, alpha: 255 - i % 4);
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
            r.DrawRect((rr, gg, bb), (cx - rowW, cy + row, rowW * 2, 1), alpha: 255);
        }

        // Eye outline — top and bottom lids
        // Upper lid
        for (double ang = -0.85; ang <= 0.85; ang += 0.04)
        {
            float norm = (float)Math.Abs(ang / 0.85);
            int px = cx + (int)(ang / 0.85 * eyeW);
            int py = cy - (int)((1 - norm * norm) * eyeH);
            r.DrawCircle((100, 50, 180), (px, py), 1, alpha: 255);
        }
        // Lower lid
        for (double ang = -0.85; ang <= 0.85; ang += 0.04)
        {
            float norm = (float)Math.Abs(ang / 0.85);
            int px = cx + (int)(ang / 0.85 * eyeW);
            int py = cy + (int)((1 - norm * norm) * eyeH);
            r.DrawCircle((100, 50, 180), (px, py), 1, alpha: 255);
        }

        // Eyelashes — top
        for (int el = 0; el < 5; el++)
        {
            float t = (el + 1) / 6f;
            int lx = cx + (int)((t * 2 - 1) * eyeW * 0.8f);
            float norm = Math.Abs(t * 2 - 1);
            int ly = cy - (int)((1 - norm * norm) * eyeH);
            int lLen = s * 4 / 100;
            r.DrawLine((80, 40, 160), (lx, ly), (lx + (int)((t - 0.5f) * lLen), ly - lLen), width: 1, alpha: 255);
        }

        // Iris — rich multi-layered
        int irisR = s * 12 / 100;
        r.DrawCircle((60, 20, 160), (cx, cy), irisR, alpha: 255);
        // Iris color rings
        r.DrawCircle((80, 40, 180), (cx, cy), irisR * 9 / 10, alpha: 255);
        r.DrawCircle((100, 60, 200), (cx, cy), irisR * 7 / 10, alpha: 255);
        r.DrawCircle((140, 80, 220), (cx, cy), irisR * 5 / 10, alpha: 255);
        // Iris texture — radial lines
        for (int il = 0; il < 12; il++)
        {
            double iang = il * Math.PI / 6;
            int ix = cx + (int)(Math.Cos(iang) * irisR * 4 / 10);
            int iy = cy + (int)(Math.Sin(iang) * irisR * 4 / 10);
            int ox = cx + (int)(Math.Cos(iang) * irisR * 9 / 10);
            int oy = cy + (int)(Math.Sin(iang) * irisR * 9 / 10);
            r.DrawLine((120, 70, 200), (ix, iy), (ox, oy), width: 1, alpha: 255);
        }

        // Pupil — deep black with cat slit
        r.DrawCircle((10, 5, 30), (cx, cy), s * 5 / 100, alpha: 255);
        // Cat-slit pupil (vertical line)
        r.DrawLine((5, 2, 20), (cx, cy - s * 6 / 100), (cx, cy + s * 6 / 100), width: 2, alpha: 255);

        // Pupil highlights
        r.DrawCircle((220, 200, 255), (cx - s * 2 / 100, cy - s * 3 / 100), Math.Max(1, s * 15 / 1000 + 1), alpha: 255);
        r.DrawCircle((200, 180, 240), (cx + s * 1 / 100, cy + s * 2 / 100), Math.Max(1, s * 1 / 100), alpha: 255);

        // Mystical floating symbols around the eye
        r.DrawText("✦", cx - s * 26 / 100, cy - s * 20 / 100, Math.Max(6, s * 5 / 100), (180, 140, 255),
            anchorX: "center", anchorY: "center", alpha: 255);
        r.DrawText("✧", cx + s * 28 / 100, cy + s * 14 / 100, Math.Max(6, s * 5 / 100), (180, 140, 255),
            anchorX: "center", anchorY: "center", alpha: 255);

        // Bold circle outline on iris
        DrawBoldCircleOutline(r, cx, cy, irisR, 200);

        // Action lines radiating from eye — mystical beams
        DrawActionLines(r, cx, cy, s, 16, (160, 120, 240), 200, s * 36 / 100);

        // Sparkles at beam ends
        DrawSparkle(r, cx - s * 30 / 100, cy - s * 14 / 100, s * 2 / 100, (220, 180, 255), 210);
        DrawSparkle(r, cx + s * 28 / 100, cy + s * 8 / 100, s * 18 / 1000, (180, 220, 255), 210);
        DrawSparkle(r, cx + s * 6 / 100, cy - s * 28 / 100, s * 15 / 1000, (255, 200, 255), 210);

        // Zodiac-like symbols in corners
        r.DrawText("☽", cx - s * 32 / 100, cy + s * 28 / 100, Math.Max(5, s * 5 / 100), (180, 160, 240),
            anchorX: "center", anchorY: "center", alpha: 255);
        r.DrawText("☆", cx + s * 32 / 100, cy - s * 28 / 100, Math.Max(5, s * 5 / 100), (200, 180, 255),
            anchorX: "center", anchorY: "center", alpha: 255);

        // Dot pattern in background corners
        DrawDotPattern(r, x + s * 2 / 100, y + s * 2 / 100, s * 12 / 100, s * 12 / 100, (140, 100, 220), Math.Max(1, s * 1 / 100), 180, s * 5 / 100);
    }

    private static void DrawFUT_Telescope(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // === RICH NIGHT SKY — row-by-row gradient ===
        for (int row = 0; row < h; row++)
        {
            float t = (float)row / h;
            int rr = (int)(8 + 30 * t);        // deep midnight → dark horizon
            int gg = (int)(5 + 20 * t);
            int bb = (int)(30 + 40 * (1f - t * 0.3f));
            r.DrawRect((rr, gg, bb), (x, y + row, w, 1), alpha: 255);
        }

        // Nebula clouds in sky
        r.DrawCircle((40, 20, 80), (cx - s * 20 / 100, cy - s * 24 / 100), s * 14 / 100, alpha: 120);
        r.DrawCircle((60, 15, 70), (cx + s * 15 / 100, cy - s * 30 / 100), s * 10 / 100, alpha: 100);
        r.DrawCircle((30, 25, 60), (cx + s * 30 / 100, cy - s * 15 / 100), s * 12 / 100, alpha: 80);

        // Milky Way band — diagonal streak
        for (int i = 0; i < 20; i++)
        {
            int mx = x + s * 5 / 100 + i * s * 4 / 100;
            int my = y + h - s * 5 / 100 - i * s * 3 / 100;
            r.DrawCircle((25, 20, 50), (mx, my), Math.Max(2, s * 3 / 100), alpha: 80 - i * 2);
        }

        // Stars in background — with glow halos
        (int ox, int oy, int sz, (int, int, int) col)[] stars = [
            (-s * 25 / 100, -s * 24 / 100, 3, (255, 255, 220)),
            (s * 20 / 100,  -s * 30 / 100, 2, (220, 220, 255)),
            (-s * 32 / 100, s * 2 / 100,   2, (255, 220, 200)),
            (s * 30 / 100,  -s * 10 / 100, 3, (200, 240, 255)),
            (0,             -s * 34 / 100, 2, (255, 255, 200)),
            (s * 16 / 100,  -s * 20 / 100, 2, (240, 220, 255)),
            (-s * 14 / 100, -s * 30 / 100, 2, (255, 240, 200)),
            (s * 26 / 100,  -s * 24 / 100, 1, (200, 220, 255)),
            (-s * 36 / 100, -s * 16 / 100, 1, (255, 255, 240)),
            (s * 8 / 100,   -s * 36 / 100, 2, (220, 240, 255)),
        ];
        foreach (var (ox, oy, sz, col) in stars)
        {
            // Glow halo
            r.DrawCircle((col.Item1 / 3, col.Item2 / 3, col.Item3 / 3), (cx + ox, cy + oy), sz + 3, alpha: 100);
            r.DrawCircle(col, (cx + ox, cy + oy), sz, alpha: 255);
            // Twinkle cross
            r.DrawLine(col, (cx + ox - sz - 2, cy + oy), (cx + ox + sz + 2, cy + oy), width: 1, alpha: 255);
            r.DrawLine(col, (cx + ox, cy + oy - sz - 2), (cx + ox, cy + oy + sz + 2), width: 1, alpha: 255);
        }

        // Moon — crescent with gradient
        int moonX = cx + s * 26 / 100, moonY = cy - s * 28 / 100;
        int moonR = Math.Max(3, s * 8 / 100);
        for (int ring = moonR; ring >= 1; ring--)
        {
            float t = (float)ring / moonR;
            int c = (int)(220 + 30 * (1f - t));
            r.DrawCircle((c, c - 10, c - 40), (moonX, moonY), ring, alpha: 255);
        }
        // Dark circle for crescent
        r.DrawCircle((12, 8, 35), (moonX + moonR / 2, moonY - moonR / 3), moonR - 1, alpha: 255);
        // Moon glow
        r.DrawCircle((240, 230, 180), (moonX, moonY), moonR + 3, width: 1, alpha: 120);

        // === GROUND — gradient terrain with grass ===
        int groundLine = cy + s * 30 / 100;
        for (int row = 0; row < h - (groundLine - y); row++)
        {
            float t = (float)row / (h - (groundLine - y) + 1);
            int rr = (int)(30 + 20 * t);
            int gg = (int)(40 + 15 * t);
            int bb = (int)(20 + 10 * t);
            r.DrawRect((rr, gg, bb), (x, groundLine + row, w, 1), alpha: 255);
        }
        r.DrawLine((50, 60, 35), (x, groundLine), (x + w, groundLine), width: 1, alpha: 200);

        // === TELESCOPE — enhanced detail ===
        int fromX = cx - s * 8 / 100, fromY = cy + s * 24 / 100;
        int toX = cx + s * 18 / 100, toY = cy - s * 16 / 100;
        int legBot = cy + s * 36 / 100;

        // Tripod legs — gradient, thicker
        r.DrawLine((70, 60, 45), (fromX, fromY), (fromX - s * 16 / 100, legBot), width: 3, alpha: 255);
        r.DrawLine((90, 80, 60), (fromX, fromY), (fromX - s * 16 / 100, legBot), width: 1, alpha: 255);
        r.DrawLine((70, 60, 45), (fromX, fromY), (fromX + s * 16 / 100, legBot), width: 3, alpha: 255);
        r.DrawLine((90, 80, 60), (fromX, fromY), (fromX + s * 16 / 100, legBot), width: 1, alpha: 255);
        r.DrawLine((70, 60, 45), (fromX, fromY), (fromX + s * 2 / 100, legBot + s * 2 / 100), width: 3, alpha: 255);
        r.DrawLine((90, 80, 60), (fromX, fromY), (fromX + s * 2 / 100, legBot + s * 2 / 100), width: 1, alpha: 255);
        // Tripod joint — gradient fill
        for (int jr = Math.Max(2, s * 3 / 100); jr >= 1; jr--)
        {
            int c = 100 + (Math.Max(2, s * 3 / 100) - jr) * 12;
            r.DrawCircle((c, c - 10, c - 20), (fromX, fromY), jr, alpha: 255);
        }

        // Telescope body shadow
        r.DrawLine((0, 0, 0), (fromX + 3, fromY + 3), (toX + 3, toY + 3), width: 12, alpha: 200);
        // Telescope body — 4-layer gradient tube
        r.DrawLine((100, 85, 70), (fromX, fromY), (toX, toY), width: 11, alpha: 255);
        r.DrawLine((130, 110, 90), (fromX, fromY), (toX, toY), width: 8, alpha: 255);
        r.DrawLine((160, 140, 120), (fromX, fromY), (toX, toY), width: 5, alpha: 255);
        r.DrawLine((190, 170, 150), (fromX + 1, fromY - 1), (toX + 1, toY - 1), width: 2, alpha: 255);

        // Metallic bands on tube — gradient rings
        for (int band = 1; band <= 3; band++)
        {
            float bt = band / 4f;
            int bx = fromX + (int)((toX - fromX) * bt);
            int by = fromY + (int)((toY - fromY) * bt);
            int br = Math.Max(2, s * 2 / 100);
            r.DrawCircle((180, 160, 120), (bx, by), br, width: 3, alpha: 255);
            r.DrawCircle((220, 200, 160), (bx - 1, by - 1), br, width: 1, alpha: 200); // highlight
        }

        // Lens — gradient fill with glow
        int lensR = Math.Max(4, s * 8 / 100);
        for (int ring = lensR; ring >= 1; ring--)
        {
            float t = (float)ring / lensR;
            int rr = (int)(60 + 100 * (1f - t));
            int gg = (int)(80 + 120 * (1f - t));
            int bb = (int)(140 + 100 * (1f - t));
            r.DrawCircle((rr, gg, bb), (toX, toY), ring, alpha: 255);
        }
        // Lens ring
        r.DrawCircle((200, 190, 150), (toX, toY), lensR, width: 2, alpha: 255);
        // Lens flare — enhanced cross
        r.DrawLine((200, 220, 255), (toX - s * 7 / 100, toY - s * 7 / 100),
            (toX + s * 7 / 100, toY + s * 7 / 100), width: 2, alpha: 220);
        r.DrawLine((200, 220, 255), (toX + s * 7 / 100, toY - s * 7 / 100),
            (toX - s * 7 / 100, toY + s * 7 / 100), width: 2, alpha: 220);
        r.DrawLine((255, 255, 255), (toX - s * 4 / 100, toY), (toX + s * 4 / 100, toY), width: 1, alpha: 180);
        r.DrawLine((255, 255, 255), (toX, toY - s * 4 / 100), (toX, toY + s * 4 / 100), width: 1, alpha: 180);

        // Eyepiece at back — gradient
        int epR = Math.Max(2, s * 3 / 100);
        for (int ring = epR; ring >= 1; ring--)
        {
            int c = 80 + (epR - ring) * 15;
            r.DrawCircle((c, c - 10, c - 20), (fromX - s * 2 / 100, fromY + s * 2 / 100), ring, alpha: 255);
        }

        // Bold circle outline on lens
        DrawBoldCircleOutline(r, toX, toY, lensR, 220);

        // === SPARKLE ACCENTS ===
        DrawSparkle(r, toX + s * 12 / 100, toY - s * 12 / 100, s * 2 / 100, (200, 230, 255), 240);
        DrawSparkle(r, toX - s * 10 / 100, toY + s * 8 / 100, s * 18 / 1000, (180, 210, 255), 220);
        DrawSparkle(r, cx - s * 30 / 100, cy - s * 10 / 100, s * 15 / 1000, (255, 220, 180), 200);

        // Mini cat silhouette looking through telescope
        DrawMiniCatFace(r, fromX - s * 8 / 100, fromY + s * 6 / 100, s * 5 / 100, (160, 130, 80), 240);

        // === EMBOSSED "LOOK!" TEXT ===
        r.DrawText("LOOK!", toX + s * 14 / 100, toY - s * 14 / 100, Math.Max(6, s * 7 / 100), (20, 15, 50),
            bold: true, anchorX: "center", anchorY: "center", alpha: 200);
        r.DrawText("LOOK!", toX + s * 14 / 100 - 1, toY - s * 14 / 100 - 1, Math.Max(6, s * 7 / 100), (200, 230, 255),
            bold: true, anchorX: "center", anchorY: "center", alpha: 255);
    }

    private static void DrawFUT_Constellation(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // === DEEP SPACE GRADIENT BACKGROUND ===
        for (int row = 0; row < h; row++)
        {
            float t = (float)row / h;
            int rr = (int)(6 + 20 * t);
            int gg = (int)(4 + 12 * t);
            int bb = (int)(25 + 45 * (1f - t * 0.4f));
            r.DrawRect((rr, gg, bb), (x, y + row, w, 1), alpha: 255);
        }

        // Rich nebula clouds — gradient-filled
        int[][] nebulae = {
            new[] { cx - s * 12 / 100, cy + s * 24 / 100, s * 14 / 100, 80, 35, 140 },
            new[] { cx + s * 18 / 100, cy - s * 28 / 100, s * 12 / 100, 55, 25, 120 },
            new[] { cx + s * 26 / 100, cy + s * 18 / 100, s * 10 / 100, 130, 35, 90 },
            new[] { cx - s * 28 / 100, cy - s * 14 / 100, s * 12 / 100, 35, 70, 130 },
            new[] { cx + s * 5 / 100, cy + s * 32 / 100, s * 8 / 100, 60, 40, 100 },
        };
        foreach (var n in nebulae)
        {
            for (int ring = n[2]; ring >= 1; ring--)
            {
                float t = (float)ring / n[2];
                r.DrawCircle(((int)(n[3] * t), (int)(n[4] * t), (int)(n[5] * t)), (n[0], n[1]), ring, alpha: (int)(80 * t + 30));
            }
        }

        // Tiny background stars (not part of constellation) — more, with variety
        for (int i = 0; i < 20; i++)
        {
            int sx = cx + (int)((i * 7919 % 71 - 35) * s / 100.0);
            int sy = cy + (int)((i * 6271 % 61 - 30) * s / 100.0);
            int sz = i % 4 == 0 ? 2 : 1;
            int brightness = 150 + (i * 31 % 80);
            r.DrawCircle((brightness, brightness - 10, brightness + 20), (sx, sy), sz, alpha: 200);
        }

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

        // Constellation lines — cat outline with triple glow
        (int, int)[] connections = [
            (0, 1), (1, 4), (4, 6), (6, 5), (5, 2), (2, 3),  // outline
            (1, 2),   // forehead
            (1, 7), (2, 8),  // eyes connect to frame
            (7, 9), (8, 9),  // nose triangle
        ];
        foreach (var (a, b) in connections)
        {
            r.DrawLine((50, 40, 140), starPos[a], starPos[b], width: 4, alpha: 150);  // outer glow
            r.DrawLine((80, 60, 180), starPos[a], starPos[b], width: 2, alpha: 230);
            r.DrawLine((160, 140, 240), starPos[a], starPos[b], width: 1, alpha: 255);
        }

        // Whisker lines from nose — with glow
        (int wx, int wy)[] whiskerEnds = [
            (cx + s * 32 / 100, cy + s * 2 / 100), (cx + s * 30 / 100, cy + s * 10 / 100),
            (cx - s * 32 / 100, cy + s * 2 / 100), (cx - s * 30 / 100, cy + s * 10 / 100),
        ];
        foreach (var (wx, wy) in whiskerEnds)
        {
            r.DrawLine((60, 50, 150), starPos[9], (wx, wy), width: 2, alpha: 150);
            r.DrawLine((140, 120, 220), starPos[9], (wx, wy), width: 1, alpha: 230);
        }

        // Stars with multi-layer gradient glow
        int sIdx = 0;
        foreach (var (sx, sy) in starPos)
        {
            int gr = sIdx < 4 || sIdx == 6 ? s * 6 / 100 : s * 5 / 100;
            // Gradient glow rings
            for (int ring = Math.Max(3, gr); ring >= 1; ring--)
            {
                float t = (float)ring / Math.Max(3, gr);
                int rc = (int)(80 + 160 * (1f - t));
                int gc = (int)(60 + 160 * (1f - t));
                int bc = (int)(180 + 75 * (1f - t));
                r.DrawCircle((rc, gc, bc), (sx, sy), ring, alpha: (int)(200 * (1f - t) + 55));
            }
            // Twinkle cross on main stars
            if (sIdx < 4 || sIdx == 6 || sIdx == 9)
            {
                int tLen = gr + 3;
                r.DrawLine((220, 210, 255), (sx - tLen, sy), (sx + tLen, sy), width: 1, alpha: 255);
                r.DrawLine((220, 210, 255), (sx, sy - tLen), (sx, sy + tLen), width: 1, alpha: 255);
            }
            sIdx++;
        }

        // Eye stars — colored blue/green for character
        r.DrawCircle((80, 220, 200), starPos[7], Math.Max(2, s * 3 / 100), alpha: 255);
        r.DrawCircle((80, 220, 200), starPos[8], Math.Max(2, s * 3 / 100), alpha: 255);

        // Sparkles on brightest stars
        DrawSparkle(r, starPos[0].x, starPos[0].y, s * 3 / 100, (220, 200, 255), 240);
        DrawSparkle(r, starPos[3].x, starPos[3].y, s * 3 / 100, (220, 200, 255), 240);
        DrawSparkle(r, starPos[6].x, starPos[6].y, s * 25 / 1000, (200, 220, 255), 230);
        DrawSparkle(r, starPos[9].x, starPos[9].y, s * 25 / 1000, (240, 220, 255), 230);

        // Shooting star — with gradient trail
        r.DrawLine((255, 255, 220), (x + s * 6 / 100, y + s * 8 / 100), (x + s * 26 / 100, y + s * 15 / 100), width: 3, alpha: 255);
        r.DrawLine((255, 255, 180), (x + s * 6 / 100, y + s * 8 / 100), (x + s * 18 / 100, y + s * 12 / 100), width: 2, alpha: 200);
        r.DrawLine((255, 255, 150), (x + s * 3 / 100, y + s * 6 / 100), (x + s * 6 / 100, y + s * 8 / 100), width: 1, alpha: 180);
        r.DrawLine((255, 255, 150), (x + s * 4 / 100, y + s * 10 / 100), (x + s * 6 / 100, y + s * 8 / 100), width: 1, alpha: 180);

        // Moon crescent — gradient filled
        int moonX2 = x + w - s * 10 / 100, moonY2 = y + s * 10 / 100;
        int moonR2 = Math.Max(3, s * 6 / 100);
        for (int ring = moonR2; ring >= 1; ring--)
        {
            float t = (float)ring / moonR2;
            int c = (int)(200 + 40 * (1f - t));
            r.DrawCircle((c, c - 10, c - 40), (moonX2, moonY2), ring, alpha: 255);
        }
        r.DrawCircle((8, 5, 30), (moonX2 + moonR2 / 2, moonY2 - moonR2 / 3), moonR2 - 1, alpha: 255);

        // Cosmic dust dots — brighter
        for (int cd = 0; cd < 15; cd++)
        {
            int cdx = cx + (int)((cd * 7919 % 61 - 30) * s / 100.0);
            int cdy = cy + (int)((cd * 6271 % 53 - 26) * s / 100.0);
            r.DrawCircle((180, 160, 240), (cdx, cdy), 1, alpha: 200 - cd * 8);
        }

        // === EMBOSSED "MEOW" TEXT ===
        r.DrawText("MEOW", cx, cy + s * 34 / 100, Math.Max(6, s * 7 / 100), (20, 15, 50),
            bold: true, anchorX: "center", anchorY: "center", alpha: 200);
        r.DrawText("MEOW", cx - 1, cy + s * 34 / 100 - 1, Math.Max(6, s * 7 / 100), (180, 160, 255),
            bold: true, anchorX: "center", anchorY: "center", alpha: 255);
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

        // === FESTIVE GRADIENT BACKGROUND ===
        for (int row = 0; row < h; row++)
        {
            float t = (float)row / h;
            int rr = (int)(50 + 40 * t);
            int gg = (int)(25 + 55 * (1f - t * 0.3f));
            int bb = (int)(80 + 60 * (1f - t));
            r.DrawRect((rr, gg, bb), (x, y + row, w, 1), alpha: 255);
        }

        // Gradient radial warm spotlight behind gift
        for (int ring = s * 36 / 100; ring >= 1; ring--)
        {
            float t = (float)ring / (s * 36 / 100);
            r.DrawCircle(((int)(120 + 80 * (1f - t)), (int)(60 + 80 * (1f - t)), (int)(30 + 60 * (1f - t))), (cx, cy), ring, alpha: (int)(120 * (1f - t) + 30));
        }

        // Floating confetti pieces — gradient filled, more variety
        (int ox, int oy, (int, int, int) col, int sz)[] confetti = [
            (-s * 22 / 100, -s * 28 / 100, (255, 100, 100), 3),
            (s * 20 / 100, -s * 26 / 100, (100, 255, 100), 3),
            (-s * 28 / 100, -s * 12 / 100, (100, 200, 255), 2),
            (s * 26 / 100, -s * 8 / 100, (255, 200, 100), 3),
            (0, -s * 32 / 100, (255, 150, 255), 2),
            (-s * 14 / 100, -s * 30 / 100, (255, 255, 100), 2),
            (s * 30 / 100, -s * 20 / 100, (100, 255, 200), 2),
            (-s * 32 / 100, s * 6 / 100, (255, 180, 120), 2),
        ];
        foreach (var (ox, oy, col, sz) in confetti)
            r.DrawRect(col, (cx + ox, cy + oy, Math.Max(2, sz), Math.Max(1, sz - 1)), alpha: 255);

        int boxW = s * 46 / 100, boxH = s * 36 / 100;
        int bx = cx - boxW / 2, by = cy - boxH / 3;

        // Box shadow — gradient
        for (int sh = 5; sh >= 1; sh--)
            r.DrawRect((0, 0, 0), (bx + sh, by + sh, boxW, boxH), alpha: 60 + sh * 20);

        // Box body — rich red row-by-row gradient
        for (int row = 0; row < boxH; row++)
        {
            float t = (float)row / boxH;
            int rr = (int)(225 - 40 * t);
            int gg = (int)(70 - 15 * t);
            int bb = (int)(90 + 20 * t);
            r.DrawRect((rr, gg, bb), (bx, by + row, boxW, 1), alpha: 255);
        }
        // Box outline
        r.DrawRect((160, 40, 60), (bx, by, boxW, boxH), width: 2, alpha: 255);

        // Polka dot pattern on box
        DrawDotPattern(r, bx + s * 2 / 100, by + s * 3 / 100, boxW - s * 4 / 100, boxH - s * 4 / 100, (255, 180, 200), Math.Max(1, s * 1 / 100), 180, s * 6 / 100);

        // Lid (wider, gradient filled row by row)
        int lidH = s * 10 / 100;
        int lidX = bx - 6, lidW = boxW + 12;
        for (int row = 0; row < lidH; row++)
        {
            float t = (float)row / lidH;
            int rr = (int)(240 - 30 * t);
            int gg = (int)(100 - 25 * t);
            int bb = (int)(130 - 20 * t);
            r.DrawRect((rr, gg, bb), (lidX, by - lidH + row, lidW, 1), alpha: 255);
        }
        // Lid highlight along top edge
        r.DrawRect((255, 140, 160), (lidX + 1, by - lidH, lidW - 2, 2), alpha: 255);
        r.DrawRect((180, 50, 80), (lidX, by - lidH, lidW, lidH), width: 1, alpha: 255);

        // Ribbon — vertical and horizontal (golden, gradient)
        int ribW = Math.Max(4, s * 7 / 100);
        // Vertical ribbon with gradient
        for (int col = 0; col < ribW; col++)
        {
            float t = (float)col / ribW;
            int rv = (int)(220 + 35 * (1f - Math.Abs(t - 0.5f) * 2));
            int gv = (int)(170 + 50 * (1f - Math.Abs(t - 0.5f) * 2));
            r.DrawRect((rv, gv, 40), (cx - ribW / 2 + col, by - lidH, 1, boxH + lidH), alpha: 255);
        }
        // Horizontal ribbon with gradient
        for (int row = 0; row < ribW; row++)
        {
            float t = (float)row / ribW;
            int rv = (int)(220 + 35 * (1f - Math.Abs(t - 0.5f) * 2));
            int gv = (int)(170 + 50 * (1f - Math.Abs(t - 0.5f) * 2));
            r.DrawRect((rv, gv, 40), (bx, by + boxH / 2 - ribW / 2 + row, boxW, 1), alpha: 255);
        }

        // Bow at top — gradient-filled loops with highlight
        int bowR = Math.Max(5, s * 8 / 100);
        int bowCY = by - lidH - s * 6 / 100;
        // Left loop gradient
        for (int ring = bowR; ring >= 1; ring--)
        {
            float t = (float)ring / bowR;
            r.DrawCircle(((int)(220 + 35 * (1f - t)), (int)(160 + 50 * (1f - t)), (int)(30 + 70 * (1f - t))), (cx - s * 8 / 100, bowCY), ring, alpha: 255);
        }
        r.DrawCircle((200, 140, 30), (cx - s * 8 / 100, bowCY), bowR, width: 1, alpha: 255);
        // Right loop gradient
        for (int ring = bowR; ring >= 1; ring--)
        {
            float t = (float)ring / bowR;
            r.DrawCircle(((int)(220 + 35 * (1f - t)), (int)(160 + 50 * (1f - t)), (int)(30 + 70 * (1f - t))), (cx + s * 8 / 100, bowCY), ring, alpha: 255);
        }
        r.DrawCircle((200, 140, 30), (cx + s * 8 / 100, bowCY), bowR, width: 1, alpha: 255);
        // Center knot — gradient
        int knotR = Math.Max(3, s * 35 / 1000);
        for (int ring = knotR; ring >= 1; ring--)
        {
            float t = (float)ring / knotR;
            r.DrawCircle(((int)(240 + 15 * (1f - t)), (int)(190 + 40 * (1f - t)), (int)(50 + 60 * (1f - t))), (cx, bowCY + s * 2 / 100), ring, alpha: 255);
        }
        // Ribbon tails
        r.DrawLine((255, 200, 60), (cx - s * 2 / 100, bowCY + s * 2 / 100), (cx - s * 10 / 100, bowCY + s * 8 / 100), width: 3, alpha: 255);
        r.DrawLine((255, 220, 80), (cx - s * 2 / 100, bowCY + s * 2 / 100), (cx - s * 10 / 100, bowCY + s * 8 / 100), width: 1, alpha: 255);
        r.DrawLine((255, 200, 60), (cx + s * 2 / 100, bowCY + s * 2 / 100), (cx + s * 10 / 100, bowCY + s * 8 / 100), width: 3, alpha: 255);
        r.DrawLine((255, 220, 80), (cx + s * 2 / 100, bowCY + s * 2 / 100), (cx + s * 10 / 100, bowCY + s * 8 / 100), width: 1, alpha: 255);

        // Gift tag — gradient
        int tagX = bx + boxW - s * 3 / 100, tagY = by + s * 2 / 100;
        int tagW = s * 9 / 100, tagH = s * 6 / 100;
        for (int row = 0; row < tagH; row++)
        {
            float t = (float)row / tagH;
            r.DrawRect(((int)(255 - 10 * t), (int)(255 - 10 * t), (int)(220 + 15 * t)), (tagX, tagY + row, tagW, 1), alpha: 255);
        }
        r.DrawRect((180, 160, 120), (tagX, tagY, tagW, tagH), width: 1, alpha: 200);
        r.DrawCircle((180, 160, 120), (tagX + tagW / 2, tagY + 2), Math.Max(1, s * 1 / 100), width: 1, alpha: 200);

        // Bold outlines on box and lid
        DrawBoldRectOutline(r, bx, by, boxW, boxH, 220);
        DrawBoldRectOutline(r, lidX, by - lidH, lidW, lidH, 220);

        // Sparkle bursts around gift — brighter
        DrawSparkle(r, cx - s * 30 / 100, cy - s * 22 / 100, s * 25 / 1000, (255, 240, 100), 240);
        DrawSparkle(r, cx + s * 32 / 100, cy - s * 18 / 100, s * 22 / 1000, (255, 200, 180), 240);
        DrawSparkle(r, cx - s * 26 / 100, cy + s * 26 / 100, s * 2 / 100, (200, 255, 200), 240);
        DrawSparkle(r, cx + s * 28 / 100, cy + s * 24 / 100, s * 18 / 1000, (200, 220, 255), 240);

        // Star sparkles in background
        for (int i = 0; i < 8; i++)
        {
            int sx = cx + (int)((i * 7919 % 65 - 32) * s / 100.0);
            int sy = cy + (int)((i * 6271 % 55 - 27) * s / 100.0);
            r.DrawCircle((255, 255, 220), (sx, sy), 1, alpha: 200);
            r.DrawLine((255, 255, 200), (sx - 3, sy), (sx + 3, sy), width: 1, alpha: 180);
            r.DrawLine((255, 255, 200), (sx, sy - 3), (sx, sy + 3), width: 1, alpha: 180);
        }

        // Mini cat face peeking from behind box
        DrawMiniCatFace(r, bx - s * 5 / 100, by + boxH - s * 7 / 100, s * 6 / 100, (200, 170, 100), 230);

        // === EMBOSSED "FOR YOU!" TEXT ===
        r.DrawText("FOR YOU!", cx, cy + s * 35 / 100, Math.Max(6, s * 5 / 100), (40, 20, 50),
            bold: true, anchorX: "center", anchorY: "center", alpha: 200);
        r.DrawText("FOR YOU!", cx - 1, cy + s * 35 / 100 - 1, Math.Max(6, s * 5 / 100), (255, 220, 100),
            bold: true, anchorX: "center", anchorY: "center", alpha: 255);
    }

    private static void DrawFAV_Heart(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // === WARM ROMANTIC GRADIENT BACKGROUND ===
        for (int row = 0; row < h; row++)
        {
            float t = (float)row / h;
            int rr = (int)(80 + 60 * (1f - t * 0.5f));
            int gg = (int)(20 + 30 * t);
            int bb = (int)(50 + 40 * (1f - t));
            r.DrawRect((rr, gg, bb), (x, y + row, w, 1), alpha: 255);
        }

        // Radial love glow — gradient rings
        for (int ring = s * 40 / 100; ring >= 1; ring--)
        {
            float t = (float)ring / (s * 40 / 100);
            int rr = (int)(180 + 75 * (1f - t));
            int gg = (int)(40 + 60 * (1f - t));
            int bb = (int)(80 + 80 * (1f - t));
            r.DrawCircle((rr, gg, bb), (cx, cy), ring, alpha: (int)(140 * (1f - t) + 40));
        }

        // Floating mini hearts in background
        (int ox, int oy, int sz)[] floatingHearts = [
            (-s * 30 / 100, -s * 28 / 100, 5), (s * 28 / 100, -s * 26 / 100, 4),
            (-s * 8 / 100, -s * 32 / 100, 6), (s * 32 / 100, s * 10 / 100, 3),
            (-s * 34 / 100, s * 16 / 100, 4), (s * 20 / 100, s * 28 / 100, 3),
        ];
        foreach (var (ox, oy, sz) in floatingHearts)
        {
            int hx = cx + ox, hy = cy + oy;
            int alpha = 140 + sz * 15;
            r.DrawText("♥", hx, hy, Math.Max(3, sz), (255, 150 + sz * 10, 180 + sz * 5),
                anchorX: "center", anchorY: "center", alpha: Math.Min(255, alpha));
        }

        // Heart shape — gradient filled properly
        int heartR = s * 19 / 100;
        int heartCY = cy - heartR * 5 / 100;

        // Left hump — ring-by-ring gradient
        for (int ring = heartR; ring >= 1; ring--)
        {
            float t = (float)ring / heartR;
            int rr = (int)(200 + 55 * (1f - t));
            int gg = (int)(30 + 50 * (1f - t));
            int bb = (int)(70 + 60 * (1f - t));
            r.DrawCircle((rr, gg, bb), (cx - heartR * 66 / 100, heartCY - heartR * 26 / 100), ring, alpha: 255);
        }
        // Right hump — ring-by-ring gradient
        for (int ring = heartR; ring >= 1; ring--)
        {
            float t = (float)ring / heartR;
            int rr = (int)(200 + 55 * (1f - t));
            int gg = (int)(30 + 50 * (1f - t));
            int bb = (int)(70 + 60 * (1f - t));
            r.DrawCircle((rr, gg, bb), (cx + heartR * 66 / 100, heartCY - heartR * 26 / 100), ring, alpha: 255);
        }
        // Center fill — smooth bridge
        for (int ring = (int)(heartR * 0.8); ring >= 1; ring--)
        {
            float t = (float)ring / (int)(heartR * 0.8);
            r.DrawCircle(((int)(210 + 45 * (1f - t)), (int)(35 + 45 * (1f - t)), (int)(80 + 50 * (1f - t))), (cx, heartCY - heartR * 16 / 100), ring, alpha: 255);
        }

        // Bottom point — smooth gradient narrowing
        for (int p = 0; p < 14; p++)
        {
            int pw = heartR * 2 * (14 - p) / 14;
            int py = heartCY + heartR * 16 / 100 + p * heartR * 9 / 100;
            float t = (float)p / 14;
            int rr = (int)(240 - 50 * t);
            int gg = (int)(50 - 15 * t);
            int bb = (int)(100 + 20 * t);
            r.DrawRect((rr, gg, bb), (cx - pw / 2, py, pw, heartR * 9 / 100 + 1), alpha: 255);
        }

        // Heart outline — darker border
        r.DrawCircle((160, 20, 50), (cx - heartR * 66 / 100, heartCY - heartR * 26 / 100), heartR, width: 2, alpha: 255);
        r.DrawCircle((160, 20, 50), (cx + heartR * 66 / 100, heartCY - heartR * 26 / 100), heartR, width: 2, alpha: 255);

        // Specular highlight on left hump — bright
        int specR = heartR / 3;
        for (int ring = specR; ring >= 1; ring--)
        {
            float t = (float)ring / specR;
            r.DrawCircle(((int)(255), (int)(180 + 50 * (1f - t)), (int)(210 + 30 * (1f - t))), (cx - heartR, heartCY - heartR * 60 / 100), ring, alpha: (int)(220 * (1f - t) + 35));
        }

        // Arrow through heart — gradient shaft
        int arrowFromX = cx - s * 30 / 100, arrowFromY = cy + s * 8 / 100;
        int arrowToX = cx + s * 30 / 100, arrowToY = cy - s * 10 / 100;
        r.DrawLine((120, 90, 40), (arrowFromX, arrowFromY), (arrowToX, arrowToY), width: 3, alpha: 255);
        r.DrawLine((180, 150, 70), (arrowFromX, arrowFromY), (arrowToX, arrowToY), width: 1, alpha: 255);
        // Arrow head — gradient filled
        DrawTriangle(r, (140, 110, 50), arrowToX + s * 4 / 100, arrowToY - s * 2 / 100,
                     arrowToX, arrowToY, arrowToX, arrowToY - s * 4 / 100, 50);
        DrawTriangle(r, (180, 150, 80), arrowToX + s * 3 / 100, arrowToY - s * 15 / 1000,
                     arrowToX + s * 1 / 100, arrowToY - s * 1 / 100, arrowToX + s * 1 / 100, arrowToY - s * 3 / 100, 30);
        // Arrow fletching
        r.DrawLine((220, 60, 60), (arrowFromX, arrowFromY), (arrowFromX - s * 3 / 100, arrowFromY - s * 4 / 100), width: 2, alpha: 255);
        r.DrawLine((220, 60, 60), (arrowFromX, arrowFromY), (arrowFromX - s * 3 / 100, arrowFromY + s * 4 / 100), width: 2, alpha: 255);

        // Sparkle accents
        DrawSparkle(r, cx - s * 24 / 100, cy - s * 20 / 100, s * 25 / 1000, (255, 200, 230), 240);
        DrawSparkle(r, cx + s * 26 / 100, cy - s * 14 / 100, s * 22 / 1000, (255, 180, 220), 240);
        DrawSparkle(r, cx + s * 14 / 100, cy + s * 26 / 100, s * 2 / 100, (255, 220, 240), 240);
        DrawSparkle(r, cx - s * 20 / 100, cy + s * 20 / 100, s * 18 / 1000, (255, 200, 200), 240);

        // Zigzag love energy at bottom border
        DrawZigzagPattern(r, x + s * 4 / 100, y + h - s * 10 / 100, w - s * 8 / 100, s * 6 / 100, (255, 150, 180), 200, s * 5 / 100);

        // Cat face in love
        DrawMiniCatFace(r, cx + s * 26 / 100, cy + s * 22 / 100, s * 6 / 100, (200, 160, 100), 230);

        // === EMBOSSED "LOVE!" TEXT ===
        r.DrawText("LOVE!", cx, cy + s * 35 / 100, Math.Max(6, s * 6 / 100), (80, 10, 30),
            bold: true, anchorX: "center", anchorY: "center", alpha: 200);
        r.DrawText("LOVE!", cx - 1, cy + s * 35 / 100 - 1, Math.Max(6, s * 6 / 100), (255, 140, 180),
            bold: true, anchorX: "center", anchorY: "center", alpha: 255);
    }

    private static void DrawFAV_GoldCoin(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);
        int coinR = s * 28 / 100;

        // === RICH TREASURE GRADIENT BACKGROUND ===
        for (int row = 0; row < h; row++)
        {
            float t = (float)row / h;
            int rr = (int)(35 + 50 * t);
            int gg = (int)(20 + 40 * t);
            int bb = (int)(15 + 25 * t);
            r.DrawRect((rr, gg, bb), (x, y + row, w, 1), alpha: 255);
        }

        // Radial golden glow behind coin — gradient
        for (int ring = coinR + s * 10 / 100; ring >= 1; ring--)
        {
            float t = (float)ring / (coinR + s * 10 / 100);
            int rr = (int)(140 + 80 * (1f - t));
            int gg = (int)(100 + 70 * (1f - t));
            int bb = (int)(15 + 40 * (1f - t));
            r.DrawCircle((rr, gg, bb), (cx, cy), ring, alpha: (int)(120 * (1f - t) + 30));
        }

        // Stack of coins behind (depth effect) — gradient filled
        for (int stack = 3; stack >= 1; stack--)
        {
            int sx = cx + s * 14 / 100 + stack * s * 2 / 100;
            int sy = cy + s * 12 / 100 + stack * s * 3 / 100;
            int sr = coinR * 7 / 10;
            for (int ring = sr; ring >= sr - 3; ring--)
            {
                float t = (float)(ring - sr + 3) / 3;
                r.DrawCircle(((int)(160 + 40 * t), (int)(120 + 30 * t), (int)(20 + 20 * t)), (sx, sy), ring, alpha: 200);
            }
            r.DrawCircle((140, 100, 20), (sx, sy), sr, width: 2, alpha: 230);
        }

        // Shadow — gradient
        for (int sh = 6; sh >= 1; sh--)
            r.DrawCircle((0, 0, 0), (cx + sh, cy + sh), coinR, alpha: 40 + sh * 15);

        // Coin body — fine-grain ring-by-ring gradient
        for (int i = coinR; i >= 0; i--)
        {
            float t = (float)i / coinR;
            int rr = (int)(170 + 70 * t);
            int g = (int)(130 + 60 * t);
            int b = (int)(15 + 40 * t);
            r.DrawCircle((rr, g, b), (cx, cy), i, alpha: 255);
        }

        // Edge ridge — thick outer ring with notches
        r.DrawCircle((160, 120, 20), (cx, cy), coinR, width: 3, alpha: 255);
        r.DrawCircle((240, 200, 60), (cx, cy), coinR - 1, width: 1, alpha: 255);
        // Edge notches (serrated edge)
        for (int notch = 0; notch < 28; notch++)
        {
            double na = notch * Math.PI * 2 / 28;
            int nx1 = cx + (int)(Math.Cos(na) * coinR);
            int ny1 = cy + (int)(Math.Sin(na) * coinR);
            int nx2 = cx + (int)(Math.Cos(na) * (coinR - 4));
            int ny2 = cy + (int)(Math.Sin(na) * (coinR - 4));
            r.DrawLine((140, 100, 15), (nx1, ny1), (nx2, ny2), width: 1, alpha: 255);
        }

        // Inner decorative ring — double
        r.DrawCircle((160, 120, 20), (cx, cy), coinR * 74 / 100, width: 2, alpha: 255);
        r.DrawCircle((220, 180, 50), (cx, cy), coinR * 72 / 100, width: 1, alpha: 255);
        r.DrawCircle((160, 120, 20), (cx, cy), coinR * 68 / 100, width: 1, alpha: 200);

        // Cat face embossed in center — thicker lines
        int catR = coinR * 32 / 100;
        // Cat head circle
        r.DrawCircle((140, 100, 10), (cx, cy + catR / 5), catR, alpha: 255);
        r.DrawCircle((170, 130, 25), (cx, cy + catR / 5), catR, width: 2, alpha: 255);
        // Left ear
        DrawTriangle(r, (140, 100, 10), cx - catR * 8 / 10, cy - catR * 6 / 10,
                     cx - catR * 4 / 10, cy + catR / 10, cx - catR * 11 / 10, cy + catR / 10, 35);
        // Right ear
        DrawTriangle(r, (140, 100, 10), cx + catR * 8 / 10, cy - catR * 6 / 10,
                     cx + catR * 4 / 10, cy + catR / 10, cx + catR * 11 / 10, cy + catR / 10, 35);
        // Eyes — gradient filled
        for (int ring = Math.Max(1, catR * 2 / 10); ring >= 1; ring--)
        {
            float t = (float)ring / Math.Max(1, catR * 2 / 10);
            r.DrawCircle(((int)(120 + 30 * (1f - t)), (int)(80 + 20 * (1f - t)), (int)(5 + 15 * (1f - t))), (cx - catR * 4 / 10, cy), ring, alpha: 255);
            r.DrawCircle(((int)(120 + 30 * (1f - t)), (int)(80 + 20 * (1f - t)), (int)(5 + 15 * (1f - t))), (cx + catR * 4 / 10, cy), ring, alpha: 255);
        }
        // Nose
        r.DrawCircle((130, 90, 10), (cx, cy + catR * 3 / 10), Math.Max(1, catR * 12 / 100), alpha: 255);
        // Whiskers — bolder
        r.DrawLine((145, 105, 12), (cx, cy + catR * 3 / 10), (cx + catR, cy + catR * 1 / 10), width: 1, alpha: 255);
        r.DrawLine((145, 105, 12), (cx, cy + catR * 3 / 10), (cx + catR, cy + catR * 5 / 10), width: 1, alpha: 255);
        r.DrawLine((145, 105, 12), (cx, cy + catR * 3 / 10), (cx - catR, cy + catR * 1 / 10), width: 1, alpha: 255);
        r.DrawLine((145, 105, 12), (cx, cy + catR * 3 / 10), (cx - catR, cy + catR * 5 / 10), width: 1, alpha: 255);

        // Specular highlight — gradient filled bright spot upper left
        int specR = coinR / 4;
        for (int ring = specR; ring >= 1; ring--)
        {
            float t = (float)ring / specR;
            r.DrawCircle(((int)(240 + 15 * (1f - t)), (int)(220 + 30 * (1f - t)), (int)(120 + 80 * (1f - t))), (cx - coinR / 3, cy - coinR / 3), ring, alpha: (int)(220 * (1f - t) + 35));
        }
        // Secondary specular
        r.DrawCircle((255, 250, 200), (cx - coinR / 3 + 1, cy - coinR / 3 + 1), specR / 2, alpha: 200);

        // Bold circle outline on coin
        DrawBoldCircleOutline(r, cx, cy, coinR, 220);

        // Money sparkle accents
        DrawSparkle(r, cx - s * 30 / 100, cy - s * 22 / 100, s * 22 / 1000, (255, 240, 150), 240);
        DrawSparkle(r, cx + s * 28 / 100, cy + s * 20 / 100, s * 2 / 100, (255, 220, 100), 240);
        DrawSparkle(r, cx - s * 24 / 100, cy + s * 24 / 100, s * 18 / 1000, (255, 255, 180), 240);
        DrawSparkle(r, cx + s * 30 / 100, cy - s * 18 / 100, s * 15 / 1000, (255, 230, 120), 240);

        // Extra sparkle dots scattered
        for (int i = 0; i < 10; i++)
        {
            int sx = cx + (int)((i * 7919 % 65 - 32) * s / 100.0);
            int sy = cy + (int)((i * 6271 % 55 - 27) * s / 100.0);
            r.DrawCircle((255, 255, 200), (sx, sy), 1, alpha: 180);
            r.DrawLine((255, 255, 200), (sx - 2, sy), (sx + 2, sy), width: 1, alpha: 160);
        }

        // Gradient ground texture
        for (int row = 0; row < s * 8 / 100; row++)
        {
            float t = (float)row / (s * 8 / 100);
            int rr = (int)(100 + 40 * t);
            int gg = (int)(80 + 30 * t);
            int bb = (int)(35 + 25 * t);
            r.DrawRect((rr, gg, bb), (x + s * 4 / 100, y + h - s * 10 / 100 + row, w - s * 8 / 100, 1), alpha: 200);
        }

        // Mini cat face being greedy
        DrawMiniCatFace(r, cx - s * 30 / 100, cy + s * 22 / 100, s * 6 / 100, (200, 170, 100), 230);

        // === EMBOSSED "$" TEXT ===
        r.DrawText("$", cx, cy + s * 35 / 100, Math.Max(6, s * 6 / 100), (80, 60, 10),
            bold: true, anchorX: "center", anchorY: "center", alpha: 200);
        r.DrawText("$", cx - 1, cy + s * 35 / 100 - 1, Math.Max(6, s * 6 / 100), (255, 220, 80),
            bold: true, anchorX: "center", anchorY: "center", alpha: 255);
    }

    private static void DrawFAV_Handshake(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // === Warm golden background — radial gradient ===
        for (int ring = 8; ring >= 0; ring--)
        {
            int rr = s * (42 - ring * 4) / 100;
            int rv = 200 + ring * 6;
            int gv = 140 + ring * 10;
            int bv = 80 + ring * 8;
            r.DrawCircle((Math.Min(255, rv), gv, bv), (cx, cy), rr, alpha: 220 - ring * 12);
        }
        // Radial glow lines — warm celebration
        for (int ray = 0; ray < 12; ray++)
        {
            double ang = ray * Math.PI / 6;
            int innerR = s * 16 / 100;
            int outerR = s * (30 + (ray % 3) * 5) / 100;
            int rx1 = cx + (int)(Math.Cos(ang) * innerR);
            int ry1 = cy + (int)(Math.Sin(ang) * innerR);
            int rx2 = cx + (int)(Math.Cos(ang) * outerR);
            int ry2 = cy + (int)(Math.Sin(ang) * outerR);
            var rayCol = ray % 3 == 0 ? (255, 220, 140) : ray % 3 == 1 ? (255, 200, 120) : (255, 240, 160);
            r.DrawLine(rayCol, (rx1, ry1), (rx2, ry2), width: 1, alpha: 160 - ray * 5);
        }

        // === Contract/document below handshake ===
        int docW = s * 50 / 100, docH = s * 18 / 100;
        int docX = cx - docW / 2, docY = cy + s * 14 / 100;
        // Paper shadow
        r.DrawRect((120, 100, 60), (docX + 3, docY + 3, docW, docH), alpha: 180);
        // Paper
        r.DrawRect((240, 235, 220), (docX, docY, docW, docH), alpha: 250);
        // Paper lines
        for (int ln = 0; ln < 4; ln++)
        {
            int ly = docY + s * 3 / 100 + ln * s * 3 / 100;
            int lineLen = docW - s * 8 / 100 - (ln == 3 ? s * 12 / 100 : 0);
            r.DrawLine((160, 160, 180), (docX + s * 4 / 100, ly), (docX + s * 4 / 100 + lineLen, ly), width: 1, alpha: 180);
        }
        // Signature scrawl
        for (double t = 0; t < 3; t += 0.1)
        {
            int sigX = docX + docW - s * 16 / 100 + (int)(t * s * 3 / 100);
            int sigY = docY + docH - s * 4 / 100 + (int)(Math.Sin(t * 3) * s * 1 / 100);
            r.DrawCircle((40, 40, 100), (sigX, sigY), 1, alpha: 200);
        }
        // Wax seal
        int sealX = docX + docW - s * 6 / 100, sealY = docY + docH - s * 4 / 100;
        r.DrawCircle((180, 30, 30), (sealX, sealY), Math.Max(3, s * 3 / 100), alpha: 240);
        r.DrawCircle((220, 50, 40), (sealX - 1, sealY - 1), Math.Max(2, s * 2 / 100), alpha: 200);
        r.DrawCircle((255, 100, 80), (sealX - 1, sealY - 1), Math.Max(1, s * 1 / 100), alpha: 180);
        // Paper edge
        r.DrawRect((180, 170, 150), (docX, docY, docW, docH), width: 1, alpha: 220);

        // === Left sleeve — business suit (blue) ===
        int sleeveW = s * 16 / 100, sleeveH = s * 14 / 100;
        int lsx = cx - s * 36 / 100, lsy = cy - s * 4 / 100;
        // Jacket fabric
        r.DrawRect((50, 65, 140), (lsx, lsy, sleeveW, sleeveH), alpha: 255);
        // Fabric shading
        for (int fs = 0; fs < sleeveH; fs += 2)
        {
            int fv = (int)(50 + 20 * Math.Sin(fs * 0.5));
            r.DrawLine((fv, fv + 15, fv + 90), (lsx, lsy + fs), (lsx + sleeveW, lsy + fs), width: 1, alpha: 200);
        }
        // Cuff stripe
        r.DrawRect((80, 95, 170), (lsx, lsy, sleeveW, 2), alpha: 240);
        // Button
        r.DrawCircle((200, 200, 210), (lsx + sleeveW - s * 3 / 100, lsy + sleeveH / 2), Math.Max(1, s * 1 / 100), alpha: 220);
        r.DrawRect((35, 45, 120), (lsx, lsy, sleeveW, sleeveH), width: 1, alpha: 240);

        // === Right sleeve — business suit (burgundy) ===
        int rsx = cx + s * 20 / 100;
        r.DrawRect((140, 45, 45), (rsx, lsy, sleeveW, sleeveH), alpha: 255);
        for (int fs = 0; fs < sleeveH; fs += 2)
        {
            int fv = (int)(140 + 20 * Math.Sin(fs * 0.5));
            r.DrawLine((fv, fv / 3, fv / 3), (rsx, lsy + fs), (rsx + sleeveW, lsy + fs), width: 1, alpha: 200);
        }
        r.DrawRect((160, 65, 65), (rsx, lsy, sleeveW, 2), alpha: 240);
        r.DrawCircle((200, 200, 210), (rsx + s * 3 / 100, lsy + sleeveH / 2), Math.Max(1, s * 1 / 100), alpha: 220);
        r.DrawRect((120, 35, 35), (rsx, lsy, sleeveW, sleeveH), width: 1, alpha: 240);

        // === Arms — gradient skin tones ===
        // Left arm
        for (int seg = 0; seg < 8; seg++)
        {
            float t = seg / 8f;
            int ax1 = lsx + sleeveW + (int)(t * (cx - s * 5 / 100 - lsx - sleeveW));
            int ay1 = lsy + sleeveH / 2 + (int)(t * (cy - lsy - sleeveH / 2));
            int rr = (int)(210 + 25 * t);
            int gg = (int)(170 + 20 * t);
            int bb = (int)(130 + 15 * t);
            r.DrawCircle((rr, gg, bb), (ax1, ay1), Math.Max(3, s * 3 / 100), alpha: 255);
        }
        // Right arm
        for (int seg = 0; seg < 8; seg++)
        {
            float t = seg / 8f;
            int ax1 = rsx - (int)(t * (rsx - cx - s * 5 / 100));
            int ay1 = lsy + sleeveH / 2 + (int)(t * (cy - lsy - sleeveH / 2));
            int rr = (int)(195 + 20 * t);
            int gg = (int)(155 + 15 * t);
            int bb = (int)(115 + 10 * t);
            r.DrawCircle((rr, gg, bb), (ax1, ay1), Math.Max(3, s * 3 / 100), alpha: 255);
        }

        // === Clasped hands — detailed interlocking ===
        int handR = Math.Max(6, s * 10 / 100);
        // Hand shadow
        r.DrawCircle((160, 120, 80), (cx + 2, cy + 2), handR, alpha: 200);
        // Base hand
        r.DrawCircle((220, 180, 140), (cx, cy), handR, alpha: 255);
        // Highlight
        r.DrawCircle((240, 205, 165), (cx - handR / 4, cy - handR / 4), handR * 6 / 10, alpha: 230);

        // Interlocking fingers — detailed
        for (int f = 0; f < 5; f++)
        {
            int fy = cy - handR + f * handR * 2 / 5;
            int fWidth = Math.Max(2, s * 3 / 100);
            var col1 = (225, 185, 145); // left hand
            var col2 = (205, 165, 125); // right hand
            var usedCol = f % 2 == 0 ? col1 : col2;

            // Finger segment
            r.DrawLine(usedCol, (cx - handR * 6 / 10, fy), (cx + handR * 6 / 10, fy), width: fWidth, alpha: 255);
            // Finger shadow underneath
            r.DrawLine((usedCol.Item1 - 30, usedCol.Item2 - 30, usedCol.Item3 - 30),
                (cx - handR * 5 / 10, fy + 1), (cx + handR * 5 / 10, fy + 1), width: 1, alpha: 180);
            // Knuckle highlights
            r.DrawCircle((240, 210, 170), (cx - handR * 5 / 10, fy), Math.Max(1, s * 1 / 100), alpha: 220);
            r.DrawCircle((240, 210, 170), (cx + handR * 5 / 10, fy), Math.Max(1, s * 1 / 100), alpha: 220);
        }
        // Thumbs
        r.DrawLine((225, 185, 145), (cx - handR / 3, cy + handR * 7 / 10), (cx + handR / 6, cy + handR * 6 / 10), width: 3, alpha: 255);
        r.DrawLine((205, 165, 125), (cx + handR / 3, cy - handR * 7 / 10), (cx - handR / 6, cy - handR * 8 / 10), width: 3, alpha: 255);

        // Bold outline on hands
        DrawBoldCircleOutline(r, cx, cy, handR, 240);

        // === Floating hearts — different sizes ===
        r.DrawText("♥", cx - s * 22 / 100, cy - s * 22 / 100, Math.Max(7, s * 7 / 100), (255, 80, 100),
            anchorX: "center", anchorY: "center", alpha: 255);
        r.DrawText("♥", cx + s * 24 / 100, cy - s * 18 / 100, Math.Max(5, s * 5 / 100), (255, 120, 140),
            anchorX: "center", anchorY: "center", alpha: 230);
        r.DrawText("♥", cx - s * 10 / 100, cy - s * 28 / 100, Math.Max(4, s * 3 / 100), (255, 150, 160),
            anchorX: "center", anchorY: "center", alpha: 200);
        r.DrawText("♥", cx + s * 12 / 100, cy - s * 26 / 100, Math.Max(3, s * 3 / 100), (255, 160, 170),
            anchorX: "center", anchorY: "center", alpha: 180);

        // === Trust/friendship symbols ===
        r.DrawText("✦", cx - s * 30 / 100, cy + s * 8 / 100, Math.Max(5, s * 5 / 100), (255, 220, 140),
            anchorX: "center", anchorY: "center", alpha: 230);
        r.DrawText("✧", cx + s * 32 / 100, cy + s * 6 / 100, Math.Max(5, s * 5 / 100), (255, 210, 130),
            anchorX: "center", anchorY: "center", alpha: 210);

        // === "DEAL!" text — warm embossed ===
        int dealFs = Math.Max(6, s * 6 / 100);
        r.DrawText("DEAL!", cx + 2, cy + s * 36 / 100 + 2, dealFs, (120, 60, 20), bold: true, anchorX: "center", anchorY: "center", alpha: 220);
        r.DrawText("DEAL!", cx, cy + s * 36 / 100, dealFs, (255, 210, 100), bold: true, anchorX: "center", anchorY: "center", alpha: 255);

        // === Friendly cat faces on both sides ===
        DrawMiniCatFace(r, cx - s * 32 / 100, cy - s * 18 / 100, s * 5 / 100, (200, 160, 90), 240);
        DrawMiniCatFace(r, cx + s * 32 / 100, cy - s * 18 / 100, s * 5 / 100, (220, 180, 110), 240);

        // Sparkles at handshake
        DrawSparkle(r, cx, cy - s * 14 / 100, s * 25 / 1000, (255, 240, 180), 240);
        DrawSparkle(r, cx - s * 16 / 100, cy + s * 10 / 100, s * 2 / 100, (255, 220, 160), 220);
        DrawSparkle(r, cx + s * 18 / 100, cy + s * 8 / 100, s * 18 / 1000, (200, 255, 200), 210);

        // Bold outline on sleeves
        DrawBoldRectOutline(r, lsx, lsy, sleeveW, sleeveH, 220);
        DrawBoldRectOutline(r, rsx, lsy, sleeveW, sleeveH, 220);
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
        int signR = s * 26 / 100;
        int postTop = cy + signR + 3;

        // === Road/asphalt background ===
        // Dark asphalt gradient bands
        for (int band = 0; band < h; band += 2)
        {
            float t = (float)band / h;
            int gv = (int)(50 + 15 * Math.Sin(band * 0.8));
            r.DrawRect((gv, gv - 5, gv - 10), (x, y + band, w, 2), alpha: 255);
        }
        // White road shoulder line (left)
        r.DrawRect((220, 220, 200), (x + s * 3 / 100, y + h - s * 8 / 100, s * 28 / 100, 2), alpha: 200);
        // Dashed center line
        for (int dl = 0; dl < 4; dl++)
        {
            int dlx = x + s * 6 / 100 + dl * s * 14 / 100;
            r.DrawRect((240, 200, 40), (dlx, y + h - s * 4 / 100, s * 8 / 100, 2), alpha: 180);
        }

        // === Metallic post — detailed with bolts and reflections ===
        int postW = s * 5 / 100, postH = s * 28 / 100;
        int postX = cx - postW / 2;
        // Post shadow
        r.DrawRect((20, 20, 25), (postX + 3, postTop + 3, postW, postH), alpha: 180);
        // Post body — gradient steel
        for (int py2 = 0; py2 < postH; py2++)
        {
            float pt = (float)py2 / postH;
            int gv = (int)(90 + 50 * Math.Sin(pt * 3.14));
            r.DrawRect((gv, gv, gv + 10), (postX, postTop + py2, postW, 1), alpha: 255);
        }
        // Left highlight on post
        r.DrawLine((160, 160, 170), (postX + 1, postTop), (postX + 1, postTop + postH), width: 1, alpha: 200);
        // Bolts on post
        for (int bolt = 0; bolt < 3; bolt++)
        {
            int by = postTop + s * 4 / 100 + bolt * s * 8 / 100;
            r.DrawCircle((130, 130, 140), (cx, by), Math.Max(2, s * 15 / 1000), alpha: 255);
            r.DrawCircle((170, 170, 180), (cx - 1, by - 1), Math.Max(1, s * 8 / 1000), alpha: 220);
        }
        // Danger stripes on lower post
        DrawDangerStripes(r, postX, postTop + postH - s * 6 / 100, postW, s * 6 / 100, 220, s * 2 / 100);
        // Post base/ground plate
        r.DrawRect((80, 80, 90), (cx - s * 6 / 100, postTop + postH, s * 12 / 100, s * 3 / 100), alpha: 255);
        r.DrawRect((110, 110, 120), (cx - s * 5 / 100, postTop + postH, s * 10 / 100, 1), alpha: 200);

        // === Red glow behind sign — multiple layers ===
        r.DrawCircle((160, 20, 15), (cx, cy), signR + s * 14 / 100, alpha: 200);
        r.DrawCircle((190, 30, 20), (cx, cy), signR + s * 10 / 100, alpha: 230);
        r.DrawCircle((210, 40, 25), (cx, cy), signR + s * 6 / 100, alpha: 255);

        // === Octagon — multi-layer with 3D bevel ===
        var oct = new (float X, float Y)[8];
        var octOuter = new (float X, float Y)[8];
        var octInner = new (float X, float Y)[8];
        var octHighlight = new (float X, float Y)[8];
        for (int i = 0; i < 8; i++)
        {
            double ang = i * Math.PI / 4 - Math.PI / 8;
            float cos = (float)Math.Cos(ang), sin = (float)Math.Sin(ang);
            oct[i] = (cx + cos * signR, cy + sin * signR);
            octOuter[i] = (cx + cos * (signR + 3), cy + sin * (signR + 3));
            octInner[i] = (cx + cos * signR * 0.84f, cy + sin * signR * 0.84f);
            octHighlight[i] = (cx + cos * signR * 0.92f - 1, cy + sin * signR * 0.92f - 1);
        }
        // Shadow behind sign
        var octSh = new (float X, float Y)[8];
        for (int i = 0; i < 8; i++) octSh[i] = (oct[i].X + 4, oct[i].Y + 4);
        r.DrawPolygon((0, 0, 0), octSh, alpha: 200);
        // Black outer rim
        r.DrawPolygon((30, 30, 30), octOuter, alpha: 255);
        // Main red fill — gradient from top to bottom via overlapping halves
        r.DrawPolygon((180, 28, 28), oct, alpha: 255);
        // Lighter inner fill (simulates top-lit surface)
        r.DrawPolygon((200, 40, 35), octHighlight, alpha: 240);
        // White border band
        r.DrawPolygon((240, 230, 220), oct, width: 3, alpha: 255);
        r.DrawPolygon((255, 245, 235), octInner, width: 1, alpha: 200);

        // Reflective sheen — crescent highlight on upper-left
        r.DrawCircle((255, 160, 140), (cx - signR * 3 / 10, cy - signR * 3 / 10), signR / 4, alpha: 180);
        r.DrawCircle((255, 200, 180), (cx - signR * 3 / 10 - 1, cy - signR * 3 / 10 - 1), signR / 6, alpha: 140);

        // Scratches/weathering on sign face
        r.DrawLine((160, 35, 30), (cx - signR / 2, cy + signR / 5), (cx - signR / 4, cy + signR / 3), width: 1, alpha: 180);
        r.DrawLine((160, 35, 30), (cx + signR / 3, cy - signR / 4), (cx + signR / 6, cy), width: 1, alpha: 160);

        // === "STOP" text — multi-layer embossed ===
        int stopFs = Math.Max(9, signR * 55 / 100);
        r.DrawText("STOP", cx + 2, cy + 2, stopFs, (80, 10, 10), bold: true, anchorX: "center", anchorY: "center", alpha: 220);
        r.DrawText("STOP", cx, cy, stopFs, (255, 255, 255), bold: true, anchorX: "center", anchorY: "center", alpha: 255);
        // Thin shadow on letters
        r.DrawText("STOP", cx + 1, cy + 1, stopFs, (200, 200, 200), bold: true, anchorX: "center", anchorY: "center", alpha: 160);

        // === Cat peeking from behind sign ===
        // Cat body partially visible behind post
        int catX = cx + signR + s * 4 / 100, catY = cy + s * 6 / 100;
        DrawMiniCatFace(r, catX, catY, s * 6 / 100, (200, 160, 90), 250);
        // Scared expression — wide eyes already from helper, add sweat
        DrawSweatDrops(r, catX + s * 4 / 100, catY - s * 4 / 100, s, 2);
        // Cat's paw gripping sign edge
        r.DrawCircle((200, 160, 90), (cx + signR - s * 2 / 100, cy + signR / 3), Math.Max(2, s * 2 / 100), alpha: 240);
        r.DrawLine((200, 160, 90), (cx + signR - s * 2 / 100, cy + signR / 3 - s * 2 / 100),
            (cx + signR - s * 2 / 100, cy + signR / 3 + s * 2 / 100), width: 2, alpha: 240);

        // === Warning symbols ===
        r.DrawText("⚠", cx - s * 30 / 100, cy - s * 26 / 100, Math.Max(7, s * 7 / 100), (255, 200, 40),
            anchorX: "center", anchorY: "center", alpha: 255);
        r.DrawText("!!", cx - s * 26 / 100, cy + s * 20 / 100, Math.Max(5, s * 5 / 100), (255, 80, 60),
            bold: true, anchorX: "center", anchorY: "center", alpha: 240);

        // Sparkles on reflective surface
        DrawSparkle(r, cx + signR / 3, cy - signR / 4, s * 2 / 100, (255, 220, 200), 220);
        DrawSparkle(r, cx - signR / 5, cy + signR / 5, s * 15 / 1000, (255, 180, 160), 180);
    }

    private static void DrawNOPE_HandPalm(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // === Energy force-field background ===
        // Concentric energy rings from palm center
        for (int ring = 0; ring < 8; ring++)
        {
            int rr = s * (8 + ring * 5) / 100;
            int rv = 180 + ring * 8;
            int gv = 30 + ring * 3;
            int bv = 30 + ring * 3;
            r.DrawCircle((Math.Min(255, rv), gv, bv), (cx, cy + s * 4 / 100), rr, width: 1, alpha: 220 - ring * 20);
        }
        // Background shatter cracks radiating from palm
        for (int crack = 0; crack < 8; crack++)
        {
            double ang = crack * Math.PI / 4 + 0.3;
            int innerR = s * 28 / 100;
            int outerR = s * (34 + (crack % 3) * 4) / 100;
            int c1x = cx + (int)(Math.Cos(ang) * innerR);
            int c1y = cy + s * 4 / 100 + (int)(Math.Sin(ang) * innerR);
            int c2x = cx + (int)(Math.Cos(ang) * outerR);
            int c2y = cy + s * 4 / 100 + (int)(Math.Sin(ang) * outerR);
            r.DrawLine((160, 40, 40), (c1x, c1y), (c2x, c2y), width: 1, alpha: 180 - crack * 10);
            // Branch crack
            double brAng = ang + 0.4;
            int bx = c2x + (int)(Math.Cos(brAng) * s * 4 / 100);
            int by = c2y + (int)(Math.Sin(brAng) * s * 4 / 100);
            r.DrawLine((140, 35, 35), (c2x, c2y), (bx, by), width: 1, alpha: 140);
        }

        // === Prohibition circle — thick multi-layer ===
        r.DrawCircle((160, 25, 25), (cx, cy + s * 2 / 100), s * 30 / 100, width: 5, alpha: 220);
        r.DrawCircle((200, 40, 40), (cx, cy + s * 2 / 100), s * 28 / 100, width: 3, alpha: 255);
        r.DrawCircle((255, 80, 70), (cx, cy + s * 2 / 100), s * 27 / 100, width: 1, alpha: 180);

        // === Detailed arm with skin gradient ===
        // Arm — wider at shoulder, narrower at wrist
        int armW = Math.Max(8, s * 12 / 100);
        for (int ay = cy + s * 30 / 100; ay > cy + s * 14 / 100; ay -= 2)
        {
            float t = (float)(cy + s * 30 / 100 - ay) / (s * 16 / 100);
            int aw = (int)(armW * (1f - t * 0.2f));
            int rr = (int)(190 + 30 * t);
            int gg = (int)(140 + 20 * t);
            int bb = (int)(100 + 15 * t);
            r.DrawRect((rr, gg, bb), (cx - aw / 2, ay, aw, 2), alpha: 255);
        }

        // === Sleeve cuff — detailed fabric ===
        int cuffY = cy + s * 24 / 100;
        r.DrawRect((50, 70, 150), (cx - s * 9 / 100, cuffY, s * 18 / 100, s * 7 / 100), alpha: 255);
        // Cuff highlight
        r.DrawRect((70, 90, 170), (cx - s * 8 / 100, cuffY, s * 16 / 100, 2), alpha: 240);
        // Cuff fold shadow
        r.DrawRect((35, 50, 120), (cx - s * 8 / 100, cuffY + s * 5 / 100, s * 16 / 100, 2), alpha: 200);
        // Button on cuff
        r.DrawCircle((200, 200, 210), (cx + s * 6 / 100, cuffY + s * 3 / 100), Math.Max(1, s * 1 / 100), alpha: 240);

        // === Palm — detailed with skin gradient ===
        int palmR = s * 18 / 100;
        int palmCy = cy + s * 6 / 100;
        // Palm base — gradient from dark edge to light center
        r.DrawCircle((180, 130, 90), (cx + 2, palmCy + 2), palmR, alpha: 240); // shadow
        r.DrawCircle((200, 155, 115), (cx, palmCy), palmR, alpha: 255);
        // Lighter center highlight
        r.DrawCircle((230, 195, 155), (cx - palmR / 5, palmCy - palmR / 6), palmR * 6 / 10, alpha: 240);
        r.DrawCircle((245, 210, 170), (cx - palmR / 4, palmCy - palmR / 5), palmR * 4 / 10, alpha: 200);

        // Palm crease lines — life, heart, head lines
        // Heart line (top curve)
        for (double t = -0.7; t < 0.5; t += 0.05)
        {
            int lx = cx + (int)(t * palmR);
            int ly = palmCy - palmR / 4 + (int)(Math.Sin(t * 2) * palmR / 8);
            r.DrawCircle((170, 120, 80), (lx, ly), 1, alpha: 200);
        }
        // Head line (middle)
        for (double t = -0.6; t < 0.4; t += 0.05)
        {
            int lx = cx + (int)(t * palmR);
            int ly = palmCy + (int)(Math.Sin(t * 1.5 + 1) * palmR / 10);
            r.DrawCircle((170, 120, 80), (lx, ly), 1, alpha: 180);
        }
        // Life line (curved)
        for (double t = 0; t < 1.2; t += 0.05)
        {
            int lx = cx - palmR / 3 + (int)(Math.Sin(t) * palmR / 4);
            int ly = palmCy - palmR / 4 + (int)(t * palmR / 2);
            r.DrawCircle((170, 120, 80), (lx, ly), 1, alpha: 160);
        }

        // === Five detailed fingers ===
        (int fx, int fLen, int fBot)[] fingers = [
            (cx - s * 13 / 100, s * 14 / 100, palmCy - palmR / 3),   // thumb
            (cx - s * 7 / 100, s * 20 / 100, palmCy - palmR * 7 / 10), // index
            (cx - s * 1 / 100, s * 24 / 100, palmCy - palmR * 8 / 10), // middle
            (cx + s * 5 / 100, s * 22 / 100, palmCy - palmR * 7 / 10), // ring
            (cx + s * 11 / 100, s * 16 / 100, palmCy - palmR / 2),     // pinky
        ];
        int fIdx = 0;
        foreach (var (fx, fLen, fBot) in fingers)
        {
            int fWidth = fIdx == 0 ? Math.Max(5, s * 6 / 100) : Math.Max(4, s * 5 / 100);
            // Finger shadow
            r.DrawLine((170, 120, 80), (fx + 2, fBot + 2), (fx + 2, fBot - fLen + 2), width: fWidth, alpha: 200);
            // Finger body — skin gradient
            for (int stripe = 0; stripe < fWidth; stripe++)
            {
                float ft = (float)stripe / fWidth;
                int rr = (int)(195 + 35 * (1 - Math.Abs(ft - 0.3f) * 2));
                int gg = (int)(150 + 30 * (1 - Math.Abs(ft - 0.3f) * 2));
                int bb = (int)(110 + 25 * (1 - Math.Abs(ft - 0.3f) * 2));
                r.DrawLine((rr, gg, bb), (fx - fWidth / 2 + stripe, fBot), (fx - fWidth / 2 + stripe, fBot - fLen), width: 1, alpha: 255);
            }
            // Fingernail at tip
            r.DrawCircle((245, 220, 200), (fx, fBot - fLen), Math.Max(2, s * 25 / 1000), alpha: 255);
            r.DrawCircle((255, 240, 225), (fx - 1, fBot - fLen - 1), Math.Max(1, s * 15 / 1000), alpha: 230);
            // Nail half-moon
            r.DrawCircle((255, 245, 235), (fx, fBot - fLen + Math.Max(1, s * 1 / 100)), Math.Max(1, s * 12 / 1000), alpha: 180);
            // Knuckle creases
            if (fIdx > 0)
            {
                int kn1 = fBot - fLen / 3;
                int kn2 = fBot - fLen * 2 / 3;
                r.DrawLine((175, 125, 85), (fx - fWidth / 3, kn1), (fx + fWidth / 3, kn1), width: 1, alpha: 200);
                r.DrawLine((175, 125, 85), (fx - fWidth / 3, kn2), (fx + fWidth / 3, kn2), width: 1, alpha: 180);
            }
            // Energy crackle at fingertip
            for (int ec = 0; ec < 3; ec++)
            {
                double eAng = (ec - 1) * 0.4 - Math.PI / 2;
                int ecLen = s * (3 + ec % 2 * 2) / 100;
                int ex2 = fx + (int)(Math.Cos(eAng) * ecLen);
                int ey2 = (fBot - fLen) + (int)(Math.Sin(eAng) * ecLen);
                r.DrawLine((255, 200, 100), (fx, fBot - fLen - 2), (ex2, ey2), width: 1, alpha: 200 - ec * 30);
            }
            fIdx++;
        }

        // === Red prohibition slash — bold with glow ===
        r.DrawLine((160, 30, 30), (cx - s * 28 / 100, cy + s * 24 / 100),
            (cx + s * 28 / 100, cy - s * 26 / 100), width: 7, alpha: 180);
        r.DrawLine((220, 40, 40), (cx - s * 26 / 100, cy + s * 22 / 100),
            (cx + s * 26 / 100, cy - s * 24 / 100), width: 5, alpha: 255);
        r.DrawLine((255, 100, 80), (cx - s * 25 / 100, cy + s * 21 / 100),
            (cx + s * 25 / 100, cy - s * 23 / 100), width: 1, alpha: 200);

        // === "NOPE" text — large embossed ===
        int nopeFs = Math.Max(7, s * 7 / 100);
        r.DrawText("NOPE", cx + 2, cy + s * 36 / 100 + 2, nopeFs, (80, 15, 15), bold: true, anchorX: "center", anchorY: "center", alpha: 220);
        r.DrawText("NOPE", cx, cy + s * 36 / 100, nopeFs, (240, 60, 50), bold: true, anchorX: "center", anchorY: "center", alpha: 255);

        // === Angry cat peeking from corner ===
        DrawMiniCatFace(r, x + s * 8 / 100, y + s * 8 / 100, s * 5 / 100, (200, 160, 100), 240);
        // Angry eyebrows on cat (two diagonal lines above eyes)
        r.DrawLine((60, 30, 20), (x + s * 5 / 100, y + s * 5 / 100), (x + s * 8 / 100, y + s * 6 / 100), width: 1, alpha: 240);
        r.DrawLine((60, 30, 20), (x + s * 13 / 100, y + s * 5 / 100), (x + s * 10 / 100, y + s * 6 / 100), width: 1, alpha: 240);

        // Rejection symbols
        r.DrawText("✗", cx + s * 30 / 100, cy - s * 28 / 100, Math.Max(6, s * 6 / 100), (200, 50, 50),
            bold: true, anchorX: "center", anchorY: "center", alpha: 240);
        r.DrawText("🚫", x + w - s * 10 / 100, y + h - s * 10 / 100, Math.Max(5, s * 4 / 100), (200, 40, 40),
            anchorX: "center", anchorY: "center", alpha: 200);

        // Sparkle at prohibition slash crossing
        DrawSparkle(r, cx, cy, s * 2 / 100, (255, 200, 120), 220);

        // Bold prohibition circle outline
        DrawBoldCircleOutline(r, cx, cy + s * 2 / 100, s * 28 / 100, 240);
    }

    private static void DrawNOPE_BrickWall(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // === DRAMATIC GRADIENT SKY BACKGROUND ===
        for (int row = 0; row < h; row++)
        {
            float t = (float)row / h;
            int rr = (int)(60 + 80 * (1f - t * 0.6f));
            int gg = (int)(40 + 50 * (1f - t * 0.4f));
            int bb = (int)(50 + 70 * (1f - t));
            r.DrawRect((rr, gg, bb), (x, y + row, w, 1), alpha: 255);
        }

        // Storm clouds in background
        int[][] clouds = {
            new[] { cx - s * 24 / 100, y + s * 8 / 100, s * 14 / 100, 70, 55, 65 },
            new[] { cx + s * 18 / 100, y + s * 6 / 100, s * 12 / 100, 65, 50, 60 },
            new[] { cx + s * 4 / 100, y + s * 4 / 100, s * 10 / 100, 55, 45, 55 },
        };
        foreach (var c in clouds)
        {
            for (int ring = c[2]; ring >= 1; ring--)
            {
                float t = (float)ring / c[2];
                r.DrawCircle(((int)(c[3] + 40 * (1f - t)), (int)(c[4] + 30 * (1f - t)), (int)(c[5] + 35 * (1f - t))), (c[0], c[1]), ring, alpha: (int)(160 * t + 40));
            }
        }

        int wallW = s * 66 / 100, wallH = s * 56 / 100;
        int wx = cx - wallW / 2, wy = cy - wallH / 2;

        // Gradient ground/floor
        for (int row = 0; row < s * 8 / 100; row++)
        {
            float t = (float)row / (s * 8 / 100);
            int rr = (int)(70 + 40 * t);
            int gg = (int)(60 + 30 * t);
            int bb = (int)(45 + 25 * t);
            r.DrawRect((rr, gg, bb), (wx - s * 5 / 100, wy + wallH + row, wallW + s * 10 / 100, 1), alpha: 255);
        }
        // Ground highlight line
        r.DrawRect((120, 110, 90), (wx - s * 4 / 100, wy + wallH, wallW + s * 8 / 100, 2), alpha: 255);

        // Wall shadow — gradient
        for (int sh = 6; sh >= 1; sh--)
            r.DrawRect((0, 0, 0), (wx + sh, wy + sh, wallW, wallH), alpha: 40 + sh * 18);

        // Brick pattern — gradient-filled bricks, more colors
        int brickH = Math.Max(4, wallH / 8), brickW = Math.Max(8, wallW / 4);
        int mortarW = 2;
        (int, int, int)[] brickColors = [
            (185, 78, 58), (175, 72, 52), (195, 82, 62), (165, 68, 48),
            (180, 75, 55), (190, 80, 60), (170, 70, 50), (200, 88, 68),
        ];
        int brickIdx = 0;
        for (int row = 0; row < 8; row++)
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
                    // Brick body with gradient rows
                    for (int br = 0; br < brickH - mortarW; br++)
                    {
                        float t = (float)br / (brickH - mortarW);
                        int rr = (int)(bc.Item1 + 15 * (1f - t));
                        int gg = (int)(bc.Item2 + 10 * (1f - t));
                        int bb = (int)(bc.Item3 + 8 * (1f - t));
                        r.DrawRect((rr, gg, bb), (clampX, byy + br, clampW, 1), alpha: 255);
                    }
                    // Top highlight
                    r.DrawRect((bc.Item1 + 35, bc.Item2 + 25, bc.Item3 + 18), (clampX + 1, byy, clampW - 2, 1), alpha: 255);
                    // Bottom shadow
                    r.DrawRect((Math.Max(0, bc.Item1 - 35), Math.Max(0, bc.Item2 - 25), Math.Max(0, bc.Item3 - 18)), (clampX + 1, byy + brickH - mortarW - 1, clampW - 2, 1), alpha: 255);
                    // Surface texture — subtle spots
                    if (brickIdx % 3 == 0)
                        r.DrawCircle((Math.Max(0, bc.Item1 - 15), Math.Max(0, bc.Item2 - 12), Math.Max(0, bc.Item3 - 8)), (clampX + clampW / 3, byy + brickH / 3), 1, alpha: 230);
                    if (brickIdx % 5 == 0)
                        r.DrawCircle((Math.Max(0, bc.Item1 - 10), Math.Max(0, bc.Item2 - 8), Math.Max(0, bc.Item3 - 5)), (clampX + clampW * 2 / 3, byy + brickH * 2 / 3), 1, alpha: 200);
                }
            }
        }

        // Mortar lines — cement colored
        for (int row = 1; row < 8; row++)
            r.DrawLine((110, 105, 90), (wx, wy + row * brickH), (wx + wallW, wy + row * brickH), width: mortarW, alpha: 255);
        // Wall border
        r.DrawRect((90, 80, 60), (wx, wy, wallW, wallH), width: 2, alpha: 255);

        // Crack — more realistic multi-branch zigzag
        int crackX = cx + s * 4 / 100;
        r.DrawLine((25, 20, 18), (crackX, wy), (crackX - s * 3 / 100, wy + wallH * 15 / 100), width: 2, alpha: 255);
        r.DrawLine((30, 25, 20), (crackX, wy), (crackX - s * 3 / 100, wy + wallH * 15 / 100), width: 1, alpha: 130);
        r.DrawLine((25, 20, 18), (crackX - s * 3 / 100, wy + wallH * 15 / 100), (crackX + s * 1 / 100, wy + wallH * 30 / 100), width: 2, alpha: 255);
        r.DrawLine((25, 20, 18), (crackX + s * 1 / 100, wy + wallH * 30 / 100), (crackX - s * 2 / 100, wy + wallH * 50 / 100), width: 2, alpha: 255);
        r.DrawLine((25, 20, 18), (crackX - s * 2 / 100, wy + wallH * 50 / 100), (crackX + s * 3 / 100, wy + wallH * 70 / 100), width: 2, alpha: 255);
        r.DrawLine((25, 20, 18), (crackX + s * 3 / 100, wy + wallH * 70 / 100), (crackX, wy + wallH * 85 / 100), width: 1, alpha: 200);
        // Branch cracks
        r.DrawLine((35, 30, 25), (crackX - s * 3 / 100, wy + wallH * 15 / 100), (crackX - s * 7 / 100, wy + wallH * 22 / 100), width: 1, alpha: 255);
        r.DrawLine((35, 30, 25), (crackX + s * 1 / 100, wy + wallH * 30 / 100), (crackX + s * 6 / 100, wy + wallH * 35 / 100), width: 1, alpha: 255);
        r.DrawLine((35, 30, 25), (crackX - s * 2 / 100, wy + wallH * 50 / 100), (crackX - s * 5 / 100, wy + wallH * 55 / 100), width: 1, alpha: 200);

        // Graffiti-style "NO" on wall — embossed
        r.DrawText("NO", cx - s * 10 / 100, cy + s * 2 / 100, Math.Max(8, s * 14 / 100), (120, 25, 25),
            anchorX: "center", anchorY: "center", alpha: 200);
        r.DrawText("NO", cx - s * 10 / 100 - 1, cy + s * 2 / 100 - 1, Math.Max(8, s * 14 / 100), (240, 55, 55),
            anchorX: "center", anchorY: "center", alpha: 255);

        // Moss/stain patches — gradient filled
        int[][] mossPatches = {
            new[] { wx + wallW * 15 / 100, wy + wallH * 78 / 100, s * 3 / 100, 60, 100, 45 },
            new[] { wx + wallW * 78 / 100, wy + wallH * 82 / 100, s * 4 / 100, 50, 90, 38 },
            new[] { wx + wallW * 6 / 100, wy + wallH * 92 / 100, s * 2 / 100, 55, 95, 40 },
        };
        foreach (var m in mossPatches)
        {
            for (int ring = m[2]; ring >= 1; ring--)
            {
                float t = (float)ring / m[2];
                r.DrawCircle(((int)(m[3] + 30 * (1f - t)), (int)(m[4] + 30 * (1f - t)), (int)(m[5] + 20 * (1f - t))), (m[0], m[1]), ring, alpha: (int)(200 * t + 55));
            }
        }

        // Impact marks/scratches
        r.DrawLine((140, 60, 45), (wx + wallW * 58 / 100, wy + wallH * 18 / 100), (wx + wallW * 64 / 100, wy + wallH * 23 / 100), width: 2, alpha: 255);
        r.DrawLine((140, 60, 45), (wx + wallW * 23 / 100, wy + wallH * 52 / 100), (wx + wallW * 28 / 100, wy + wallH * 49 / 100), width: 2, alpha: 255);

        // Bold outline on wall
        DrawBoldRectOutline(r, wx, wy, wallW, wallH, 220);

        // Danger stripes on top of wall
        DrawDangerStripes(r, wx, wy - s * 4 / 100, wallW, s * 4 / 100, 220, s * 3 / 100);

        // Barbed wire on top — enhanced with gradient coils
        r.DrawLine((100, 100, 100), (wx - s * 2 / 100, wy - s * 15 / 1000), (wx + wallW + s * 2 / 100, wy - s * 15 / 1000), width: 2, alpha: 255);
        r.DrawLine((130, 130, 130), (wx - s * 2 / 100, wy - s * 15 / 1000), (wx + wallW + s * 2 / 100, wy - s * 15 / 1000), width: 1, alpha: 200);
        for (int bw = 0; bw < 8; bw++)
        {
            int bwx = wx + bw * wallW / 8 + wallW / 16;
            int bwy = wy - s * 15 / 1000;
            r.DrawCircle((90, 90, 90), (bwx, bwy), Math.Max(2, s * 12 / 1000), width: 1, alpha: 255);
            // Barb spikes — thicker, more visible
            r.DrawLine((120, 120, 120), (bwx - 3, bwy - 4), (bwx + 3, bwy + 4), width: 1, alpha: 255);
            r.DrawLine((120, 120, 120), (bwx + 3, bwy - 4), (bwx - 3, bwy + 4), width: 1, alpha: 255);
        }

        // Cat silhouette peeking over wall
        DrawMiniCatFace(r, cx - s * 12 / 100, wy - s * 7 / 100, s * 6 / 100, (140, 110, 70), 230);

        // Dust poofs at base — gradient filled
        int[][] dusts = {
            new[] { wx + wallW / 4, wy + wallH + s * 4 / 100, s * 4 / 100 },
            new[] { wx + wallW * 3 / 4, wy + wallH + s * 3 / 100, s * 3 / 100 },
            new[] { wx + wallW / 2, wy + wallH + s * 5 / 100, s * 3 / 100 },
        };
        foreach (var d in dusts)
        {
            for (int ring = d[2]; ring >= 1; ring--)
            {
                float t = (float)ring / d[2];
                r.DrawCircle(((int)(120 + 40 * (1f - t)), (int)(110 + 35 * (1f - t)), (int)(90 + 30 * (1f - t))), (d[0], d[1]), ring, alpha: (int)(180 * t + 40));
            }
        }

        // Sparkle accents
        DrawSparkle(r, cx - s * 32 / 100, cy - s * 24 / 100, s * 2 / 100, (200, 180, 150), 220);
        DrawSparkle(r, cx + s * 30 / 100, cy - s * 20 / 100, s * 18 / 1000, (180, 170, 140), 220);

        // === EMBOSSED "BLOCKED!" TEXT ===
        r.DrawText("BLOCKED!", cx, cy + s * 37 / 100, Math.Max(6, s * 5 / 100), (60, 25, 20),
            bold: true, anchorX: "center", anchorY: "center", alpha: 200);
        r.DrawText("BLOCKED!", cx - 1, cy + s * 37 / 100 - 1, Math.Max(6, s * 5 / 100), (200, 80, 60),
            bold: true, anchorX: "center", anchorY: "center", alpha: 255);
    }

    private static void DrawNOPE_DeniedStamp(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);

        // === Crumpled paper background ===
        // Aged parchment base with row-by-row color variation
        for (int row = 0; row < h; row += 2)
        {
            float t = (float)row / h;
            int rr = (int)(220 + 20 * Math.Sin(t * 12));
            int gg = (int)(200 + 15 * Math.Sin(t * 8 + 1));
            int bb = (int)(160 + 10 * Math.Sin(t * 10 + 2));
            r.DrawRect((rr, gg, bb), (x, y + row, w, 2), alpha: 255);
        }
        // Paper fold creases — diagonal shadow lines
        for (int cr = 0; cr < 4; cr++)
        {
            int crX = x + w * (cr + 1) / 5;
            r.DrawLine((180, 160, 120), (crX, y), (crX - s * 6 / 100, y + h), width: 1, alpha: 180);
            r.DrawLine((240, 225, 190), (crX + 1, y), (crX - s * 6 / 100 + 1, y + h), width: 1, alpha: 120);
        }
        // Coffee ring stain in top corner
        r.DrawCircle((190, 170, 130), (x + w - s * 12 / 100, y + s * 10 / 100), s * 6 / 100, width: 2, alpha: 200);
        r.DrawCircle((200, 180, 140), (x + w - s * 12 / 100, y + s * 10 / 100), s * 5 / 100, width: 1, alpha: 140);

        // === Stamp handle above stamp (3D wood grain) ===
        int handleW = s * 12 / 100, handleH = s * 16 / 100;
        int hx = cx - handleW / 2, hy = cy - s * 26 / 100;
        // Handle shadow
        r.DrawRect((60, 30, 15), (hx + 3, hy + 3, handleW, handleH), alpha: 200);
        // Wood body
        r.DrawRect((140, 80, 35), (hx, hy, handleW, handleH), alpha: 255);
        // Wood grain lines
        for (int gr = 0; gr < handleH; gr += 3)
        {
            int gShift = (int)(Math.Sin(gr * 0.4) * 2);
            r.DrawLine((120, 65, 25), (hx + 2 + gShift, hy + gr), (hx + handleW - 2 + gShift, hy + gr), width: 1, alpha: 180);
        }
        // Side highlight (left)
        r.DrawLine((180, 120, 60), (hx + 1, hy), (hx + 1, hy + handleH), width: 1, alpha: 200);
        // Metal band connecting handle to stamp face
        r.DrawRect((160, 160, 170), (hx - 1, hy + handleH - 2, handleW + 2, 4), alpha: 255);
        r.DrawRect((200, 200, 210), (hx, hy + handleH - 1, handleW, 1), alpha: 200);

        // === Stamp face — tilted slightly for organic feel ===
        int stW = s * 56 / 100, stH = s * 28 / 100;
        int stX = cx - stW / 2 - s * 1 / 100, stY = cy - stH / 2 + s * 2 / 100;
        // Ink bleed shadow — soft offset
        r.DrawRect((120, 20, 20), (stX + 3, stY + 3, stW, stH), alpha: 180);
        r.DrawRect((100, 15, 15), (stX + 5, stY + 5, stW, stH), alpha: 100);
        // Stamp face background — deep red with ink texture
        r.DrawRect((160, 25, 25), (stX, stY, stW, stH), alpha: 255);
        // Ink texture — horizontal streaks across stamp for realism
        for (int ink = 0; ink < stH; ink += 2)
        {
            int inkAlpha = 180 + (int)(40 * Math.Sin(ink * 1.5));
            int spread = (int)(Math.Sin(ink * 0.7) * s * 1 / 100);
            r.DrawLine((180, 30, 30), (stX + 3 + spread, stY + ink), (stX + stW - 3 + spread, stY + ink), width: 1, alpha: inkAlpha);
        }
        // Outer border — thick with wear marks
        r.DrawRect((200, 35, 35), (stX - 4, stY - 4, stW + 8, stH + 8), width: 3, alpha: 255);
        r.DrawRect((220, 45, 45), (stX - 2, stY - 2, stW + 4, stH + 4), width: 1, alpha: 220);
        // Inner border
        r.DrawRect((140, 20, 20), (stX + 4, stY + 4, stW - 8, stH - 8), width: 2, alpha: 240);

        // === "DENIED" text — embossed look with multiple layers ===
        int stampFs = Math.Max(10, s * 17 / 100);
        // Deep shadow
        r.DrawText("DENIED", cx + 3, cy + 5, stampFs, (60, 5, 5), bold: true, anchorX: "center", anchorY: "center", alpha: 200);
        // Mid shadow
        r.DrawText("DENIED", cx + 1, cy + 3, stampFs, (100, 10, 10), bold: true, anchorX: "center", anchorY: "center", alpha: 230);
        // Main text — bright white on red
        r.DrawText("DENIED", cx, cy + 2, stampFs, (255, 240, 230), bold: true, anchorX: "center", anchorY: "center", alpha: 255);

        // === Bold diagonal slash through stamp ===
        r.DrawLine((120, 15, 15), (stX - s * 6 / 100, stY + stH + s * 3 / 100),
            (stX + stW + s * 6 / 100, stY - s * 3 / 100), width: 5, alpha: 240);
        r.DrawLine((200, 40, 40), (stX - s * 5 / 100, stY + stH + s * 2 / 100),
            (stX + stW + s * 5 / 100, stY - s * 2 / 100), width: 3, alpha: 255);
        // Slash edge highlight
        r.DrawLine((255, 100, 80), (stX - s * 4 / 100, stY + stH + s * 1 / 100),
            (stX + stW + s * 4 / 100, stY - s * 1 / 100), width: 1, alpha: 180);

        // === Radial ink splatter spray ===
        for (int sp = 0; sp < 16; sp++)
        {
            double ang = sp * Math.PI * 2 / 16 + sp * 0.3;
            int dist = s * (22 + (sp * 7) % 14) / 100;
            int spx = cx + (int)(Math.Cos(ang) * dist);
            int spy = cy + (int)(Math.Sin(ang) * dist);
            int spr = Math.Max(1, 1 + sp % 3);
            r.DrawCircle((180 + sp % 3 * 15, 20 + sp % 4 * 5, 20 + sp % 5 * 5), (spx, spy), spr, alpha: 200 - sp * 5);
        }

        // === Fingerprint smudge near edge ===
        int fpx = stX + stW - s * 5 / 100, fpy = stY + stH - s * 2 / 100;
        for (int ring = 0; ring < 5; ring++)
        {
            int rr = s * (2 + ring) / 100;
            r.DrawCircle((140, 25, 25), (fpx, fpy), rr, width: 1, alpha: 160 - ring * 25);
        }

        // === Scattered document elements ===
        // Lined paper lines in background corners
        for (int ln = 0; ln < 5; ln++)
        {
            int ly = y + s * 6 / 100 + ln * s * 4 / 100;
            r.DrawLine((180, 180, 200), (x + s * 3 / 100, ly), (x + s * 18 / 100, ly), width: 1, alpha: 140);
        }
        // Red margin line
        r.DrawLine((200, 60, 60), (x + s * 6 / 100, y + s * 4 / 100), (x + s * 6 / 100, y + s * 26 / 100), width: 1, alpha: 180);

        // === Angry rejection symbols ===
        r.DrawText("✗", cx - s * 28 / 100, cy + s * 20 / 100, Math.Max(8, s * 8 / 100), (200, 40, 40),
            bold: true, anchorX: "center", anchorY: "center", alpha: 255);
        r.DrawText("✗", cx + s * 30 / 100, cy - s * 22 / 100, Math.Max(6, s * 6 / 100), (180, 35, 35),
            anchorX: "center", anchorY: "center", alpha: 220);

        // === Mini cat face looking dismayed ===
        DrawMiniCatFace(r, x + s * 10 / 100, y + h - s * 14 / 100, s * 5 / 100, (200, 160, 100), 240);
        DrawSweatDrops(r, x + s * 14 / 100, y + h - s * 18 / 100, s, 2);

        // "REJECTED" small text at bottom
        r.DrawText("REJECTED", cx, cy + s * 34 / 100, Math.Max(4, s * 4 / 100), (160, 30, 30),
            bold: true, anchorX: "center", anchorY: "center", alpha: 200);

        // Dot pattern in untouched corners
        DrawDotPattern(r, x + w - s * 12 / 100, y + h - s * 12 / 100, s * 10 / 100, s * 10 / 100,
            (200, 40, 40), Math.Max(1, s * 1 / 100), 140, s * 4 / 100);
    }

    // ─── GENERIC (unknown card type) ───────────────────────────
    private static void DrawGeneric(Renderer r, int x, int y, int w, int h, int cx, int cy)
    {
        int s = Math.Min(w, h);
        // Question mark motif
        r.DrawCircle((100, 160, 220), (cx, cy - s * 6 / 100), s * 20 / 100, width: 3, alpha: 255);
        r.DrawRect((100, 160, 220), (cx - s * 2 / 100, cy + s * 6 / 100, s * 4 / 100, s * 8 / 100), alpha: 255);
        r.DrawCircle((100, 160, 220), (cx, cy + s * 20 / 100), Math.Max(2, s * 3 / 100), alpha: 255);
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
        r.DrawLine((160, 160, 180), (x1, y1), (bx2, by2), width: 5, alpha: 255);
        // Inner blade (lighter)
        r.DrawLine((200, 200, 220), (x1, y1), (bx2, by2), width: 3, alpha: 255);
        // Centre line / fuller (dark groove)
        r.DrawLine((120, 120, 140), (x1 + (int)(nx * len * 0.05f), y1 + (int)(ny * len * 0.05f)),
            (bx2 - (int)(nx * s * 2 / 100), by2 - (int)(ny * s * 2 / 100)), width: 1, alpha: 255);
        // Edge highlight
        r.DrawLine((240, 240, 255), (x1 + (int)(px * 2), y1 + (int)(py * 2)),
            (bx2 + (int)(px * 2), by2 + (int)(py * 2)), width: 1, alpha: 255);

        // Blade tip — pointed
        int tipX = x1 - (int)(px * 1), tipY = y1 - (int)(py * 1);
        r.DrawLine((220, 220, 240), (x1, y1), (tipX, tipY), width: 1, alpha: 255);

        // Crossguard at blade/grip junction
        int gx = bx2, gy = by2;
        int guardLen = s * 8 / 100;
        int g1x = gx + (int)(px * guardLen), g1y = gy + (int)(py * guardLen);
        int g2x = gx - (int)(px * guardLen), g2y = gy - (int)(py * guardLen);
        // Guard body
        r.DrawLine((160, 130, 50), (g1x, g1y), (g2x, g2y), width: 4, alpha: 255);
        r.DrawLine((200, 170, 80), (g1x, g1y), (g2x, g2y), width: 2, alpha: 255);
        // Guard ends — small decorative circles
        r.DrawCircle((180, 150, 60), (g1x, g1y), Math.Max(2, s * 2 / 100), alpha: 255);
        r.DrawCircle((180, 150, 60), (g2x, g2y), Math.Max(2, s * 2 / 100), alpha: 255);

        // Grip — wrapped leather look
        float gripLen = len * 0.25f;
        int grx1 = bx2 + (int)(nx * s * 1 / 100), gry1 = by2 + (int)(ny * s * 1 / 100);
        int grx2 = bx2 + (int)(nx * gripLen), gry2 = by2 + (int)(ny * gripLen);
        r.DrawLine((100, 60, 30), (grx1, gry1), (grx2, gry2), width: 4, alpha: 255);
        // Wrap lines on grip
        for (int wrap = 0; wrap < 5; wrap++)
        {
            float wt = (wrap + 1) / 6f;
            int wwx = grx1 + (int)((grx2 - grx1) * wt);
            int wwy = gry1 + (int)((gry2 - gry1) * wt);
            int w1x = wwx + (int)(px * 3), w1y = wwy + (int)(py * 3);
            int w2x = wwx - (int)(px * 3), w2y = wwy - (int)(py * 3);
            r.DrawLine((130, 90, 50), (w1x, w1y), (w2x, w2y), width: 1, alpha: 255);
        }

        // Pommel at end
        int pmx = grx2 + (int)(nx * s * 2 / 100), pmy = gry2 + (int)(ny * s * 2 / 100);
        r.DrawCircle((160, 130, 50), (pmx, pmy), Math.Max(3, s * 3 / 100), alpha: 255);
        r.DrawCircle((200, 170, 80), (pmx - 1, pmy - 1), Math.Max(2, s * 2 / 100), alpha: 255);
        // Gem in pommel
        var gemCol = variant == 0 ? (200, 40, 40) : (40, 80, 200);
        r.DrawCircle(gemCol, (pmx, pmy), Math.Max(1, s * 1 / 100), alpha: 255);
    }

    private static void DrawSword(Renderer r, int x1, int y1, int x2, int y2, int s)
    {
        // Blade
        r.DrawLine((180, 180, 200), (x1, y1), (x2, y2), width: 3, alpha: 255);
        // Edge highlight
        r.DrawLine((220, 220, 240), (x1 + 1, y1 + 1), (x2 + 1, y2 + 1), width: 1, alpha: 255);
        // Guard at center
        int gx = (x1 + x2) / 2, gy = (y1 + y2) / 2;
        r.DrawLine((140, 100, 50), (gx - s * 4 / 100, gy + s * 4 / 100),
            (gx + s * 4 / 100, gy - s * 4 / 100), width: 3, alpha: 255);
        // Pommel near start
        r.DrawCircle((120, 90, 40), (x2, y2), Math.Max(2, s * 3 / 100), alpha: 255);
    }

    // ─── Enhanced Visual Helpers ───────────────────────────────

    /// <summary>Draw fur/hair texture lines radiating outward from a center point.</summary>
    private static void DrawFurTexture(Renderer r, int cx, int cy, int radius, int count,
        (int R, int G, int B) col, int alpha)
    {
        for (int i = 0; i < count; i++)
        {
            double ang = i * Math.PI * 2 / count + (i * 0.3);
            int innerR = radius * 70 / 100;
            int outerR = radius + (i % 3) * (radius / 8);
            int x1 = cx + (int)(Math.Cos(ang) * innerR);
            int y1 = cy + (int)(Math.Sin(ang) * innerR);
            int x2 = cx + (int)(Math.Cos(ang) * outerR);
            int y2 = cy + (int)(Math.Sin(ang) * outerR);
            r.DrawLine(col, (x1, y1), (x2, y2), width: 1, alpha: alpha - (i % 4) * 2);
        }
    }

    /// <summary>Draw zigzag background pattern in a rectangular region.</summary>
    private static void DrawZigzagPattern(Renderer r, int x, int y, int w, int h,
        (int R, int G, int B) col, int alpha, int spacing = 12)
    {
        for (int row = 0; row < h; row += spacing)
        {
            for (int seg = 0; seg < w; seg += spacing)
            {
                int sx = x + seg;
                int sy = y + row;
                int ex = sx + spacing / 2;
                int ey = sy + ((seg / spacing) % 2 == 0 ? spacing / 2 : -spacing / 2);
                ey = Math.Max(y, Math.Min(y + h, ey));
                r.DrawLine(col, (sx, sy), (ex, ey), width: 1, alpha: alpha);
            }
        }
    }

    /// <summary>Draw polka dot pattern in a region.</summary>
    private static void DrawDotPattern(Renderer r, int x, int y, int w, int h,
        (int R, int G, int B) col, int dotR, int alpha, int spacing = 16)
    {
        for (int row = 0; row < h; row += spacing)
        {
            int offset = (row / spacing) % 2 == 0 ? 0 : spacing / 2;
            for (int col2 = offset; col2 < w; col2 += spacing)
            {
                r.DrawCircle(col, (x + col2, y + row), dotR, alpha: alpha);
            }
        }
    }

    /// <summary>Draw cartoon sweat drops near a character.</summary>
    private static void DrawSweatDrops(Renderer r, int cx, int cy, int s, int count = 3)
    {
        for (int i = 0; i < count; i++)
        {
            double ang = -Math.PI / 3 + i * Math.PI / (count + 1);
            int dist = s * (12 + i * 4) / 100;
            int dx = cx + (int)(Math.Cos(ang) * dist);
            int dy = cy + (int)(Math.Sin(ang) * dist) - s * 8 / 100;
            int dropH = Math.Max(3, s * 3 / 100);
            // Droplet shape: small circle + triangle pointing down
            r.DrawCircle((180, 220, 255), (dx, dy), Math.Max(1, dropH / 2), alpha: 255);
            DrawTriangle(r, dx - dropH / 3, dy - dropH, dropH, (180, 220, 255), 200);
        }
    }

    /// <summary>Draw comic-style action/speed lines from a focal point.</summary>
    private static void DrawActionLines(Renderer r, int cx, int cy, int s, int count,
        (int R, int G, int B) col, int alpha, float spread = 0.4f)
    {
        for (int i = 0; i < count; i++)
        {
            double ang = -Math.PI * spread + i * Math.PI * spread * 2 / (count - 1);
            int innerR = s * 28 / 100;
            int outerR = s * (38 + (i % 3) * 4) / 100;
            int x1 = cx + (int)(Math.Cos(ang) * innerR);
            int y1 = cy + (int)(Math.Sin(ang) * innerR);
            int x2 = cx + (int)(Math.Cos(ang) * outerR);
            int y2 = cy + (int)(Math.Sin(ang) * outerR);
            r.DrawLine(col, (x1, y1), (x2, y2), width: (i % 2 == 0 ? 2 : 1), alpha: alpha);
        }
    }

    /// <summary>Draw small decorative starburst sparkle.</summary>
    private static void DrawSparkle(Renderer r, int cx, int cy, int size, (int R, int G, int B) col, int alpha)
    {
        // 4-pointed star
        r.DrawLine(col, (cx - size, cy), (cx + size, cy), width: 1, alpha: alpha);
        r.DrawLine(col, (cx, cy - size), (cx, cy + size), width: 1, alpha: alpha);
        // Diagonal rays (shorter)
        int ds = size * 6 / 10;
        r.DrawLine(col, (cx - ds, cy - ds), (cx + ds, cy + ds), width: 1, alpha: alpha * 6 / 10);
        r.DrawLine(col, (cx + ds, cy - ds), (cx - ds, cy + ds), width: 1, alpha: alpha * 6 / 10);
        // Center dot
        r.DrawCircle(col, (cx, cy), Math.Max(1, size / 3), alpha: alpha);
    }

    /// <summary>Draw bold cartoon outline around a circle.</summary>
    private static void DrawBoldCircleOutline(Renderer r, int cx, int cy, int radius, int alpha = 220)
    {
        r.DrawCircle((0, 0, 0), (cx, cy), radius + 2, width: 3, alpha: alpha);
        r.DrawCircle((0, 0, 0), (cx, cy), radius + 1, width: 2, alpha: alpha * 7 / 10);
    }

    /// <summary>Draw bold cartoon outline around a rectangle.</summary>
    private static void DrawBoldRectOutline(Renderer r, int x, int y, int w, int h, int alpha = 220)
    {
        r.DrawRect((0, 0, 0), (x - 1, y - 1, w + 2, h + 2), width: 3, alpha: alpha);
    }

    /// <summary>Draw cross-hatching pattern inside a region for texture.</summary>
    private static void DrawCrossHatch(Renderer r, int x, int y, int w, int h,
        (int R, int G, int B) col, int alpha, int spacing = 8)
    {
        for (int i = -h; i < w + h; i += spacing)
        {
            int x1 = x + i, y1 = y;
            int x2 = x + i - h, y2 = y + h;
            r.DrawLine(col, (Math.Max(x, x1), Math.Max(y, y1)), (Math.Max(x, x2), Math.Min(y + h, y2)), width: 1, alpha: alpha);
        }
    }

    /// <summary>Draw a small cartoon cat face.</summary>
    private static void DrawMiniCatFace(Renderer r, int cx, int cy, int size,
        (int R, int G, int B) bodyCol, int alpha)
    {
        // Head
        r.DrawCircle(bodyCol, (cx, cy), size, alpha: alpha);
        // Ears
        DrawTriangle(r, cx - size, cy - size * 3 / 2, size * 7 / 10, bodyCol, alpha);
        DrawTriangle(r, cx + size * 3 / 10, cy - size * 3 / 2, size * 7 / 10, bodyCol, alpha);
        // Inner ears
        int earInner = (bodyCol.R + 40, bodyCol.G - 20, bodyCol.B - 10) switch { var c => c.Item1 };
        DrawTriangle(r, cx - size + size / 4, cy - size * 12 / 10, size * 4 / 10,
            (Math.Min(255, bodyCol.R + 40), Math.Max(0, bodyCol.G - 20), Math.Max(0, bodyCol.B + 20)), alpha * 6 / 10);
        DrawTriangle(r, cx + size * 4 / 10, cy - size * 12 / 10, size * 4 / 10,
            (Math.Min(255, bodyCol.R + 40), Math.Max(0, bodyCol.G - 20), Math.Max(0, bodyCol.B + 20)), alpha * 6 / 10);
        // Eyes
        r.DrawCircle((255, 255, 200), (cx - size * 4 / 10, cy - size / 5), Math.Max(1, size * 3 / 10), alpha: alpha);
        r.DrawCircle((255, 255, 200), (cx + size * 4 / 10, cy - size / 5), Math.Max(1, size * 3 / 10), alpha: alpha);
        r.DrawCircle((0, 0, 0), (cx - size * 4 / 10, cy - size / 5), Math.Max(1, size * 15 / 100), alpha: alpha);
        r.DrawCircle((0, 0, 0), (cx + size * 4 / 10, cy - size / 5), Math.Max(1, size * 15 / 100), alpha: alpha);
        // Nose
        DrawTriangle(r, cx - size / 8, cy + size / 6, Math.Max(2, size / 4), (200, 120, 100), alpha * 8 / 10);
        // Whiskers
        r.DrawLine(bodyCol, (cx - size / 3, cy + size / 4), (cx - size, cy + size / 8), width: 1, alpha: alpha * 6 / 10);
        r.DrawLine(bodyCol, (cx + size / 3, cy + size / 4), (cx + size, cy + size / 8), width: 1, alpha: alpha * 6 / 10);
    }

    /// <summary>Draw danger stripes (diagonal yellow/black) in a rectangular region.</summary>
    private static void DrawDangerStripes(Renderer r, int x, int y, int w, int h, int alpha, int spacing = 10)
    {
        for (int i = -h; i < w + h; i += spacing)
        {
            bool isYellow = ((i / spacing) % 2) == 0;
            var col = isYellow ? (240, 200, 0) : (40, 30, 0);
            int x1 = x + i, y1 = y;
            int x2 = x + i + h, y2 = y + h;
            r.DrawLine(col, (Math.Max(x, Math.Min(x + w, x1)), y1),
                       (Math.Max(x, Math.Min(x + w, x2)), y2), width: spacing / 2, alpha: alpha);
        }
    }
}
