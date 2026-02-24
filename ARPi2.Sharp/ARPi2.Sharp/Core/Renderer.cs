using Microsoft.Xna.Framework;
using Microsoft.Xna.Framework.Graphics;
using FontStashSharp;
using SkiaSharp;
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;

namespace ARPi2.Sharp.Core;

/// <summary>
/// Hardware-accelerated 2D renderer using MonoGame SpriteBatch.
/// Mirrors the Python PygletRenderer API but runs on GPU via DirectX/OpenGL.
/// All coordinates use top-left origin (no Y-flip needed unlike Pyglet).
/// </summary>
public sealed class Renderer : IDisposable
{
    public int Width  { get; private set; }
    public int Height { get; private set; }

    public GraphicsDevice GraphicsDevice => _gd;

    private readonly GraphicsDevice _gd;
    private readonly SpriteBatch    _sb;
    private Texture2D?              _pixel; // 1x1 white texture for primitives
    private FontSystem?             _fontSystem;

    // SkiaSharp color emoji rendering
    private SKTypeface? _emojiTypeface;
    private readonly Dictionary<(string text, int size), Texture2D> _emojiCache = new();

    // Begin/End state
    private bool _batchOpen;

    // Scissor clipping stack
    private readonly Stack<Rectangle> _clipStack = new();
    private static readonly RasterizerState _scissorRaster = new() { ScissorTestEnable = true };

    public Renderer(GraphicsDevice gd, int width, int height)
    {
        _gd     = gd;
        Width   = width;
        Height  = height;
        _sb     = new SpriteBatch(gd);
        _pixel  = new Texture2D(gd, 1, 1);
        _pixel.SetData(new[] { Color.White });
    }

    /// <summary>Set the FontSystem used by DrawText (loaded from a TTF at runtime).</summary>
    public void SetFontSystem(FontSystem fontSystem) => _fontSystem = fontSystem;

    /// <summary>Load an emoji typeface for SkiaSharp color emoji rendering.</summary>
    public void LoadEmojiTypeface()
    {
        string[] candidates =
        {
            @"C:\Windows\Fonts\seguiemj.ttf",                           // Windows
            "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",         // Ubuntu/Debian
            "/usr/share/fonts/noto/NotoColorEmoji.ttf",                  // Fedora
            "/System/Library/Fonts/Apple Color Emoji.ttc",               // macOS
        };
        foreach (var path in candidates)
        {
            if (File.Exists(path))
            {
                _emojiTypeface = SKTypeface.FromFile(path);
                if (_emojiTypeface != null)
                {
                    System.Diagnostics.Debug.WriteLine($"[Emoji] SkiaSharp typeface loaded: {path}");
                    return;
                }
            }
        }
        System.Diagnostics.Debug.WriteLine("[Emoji] No color emoji font found for SkiaSharp");
    }

    /// <summary>Render an emoji string to a cached Texture2D via SkiaSharp (full color).</summary>
    private Texture2D? GetEmojiTexture(string emoji, int fontSize)
    {
        if (_emojiTypeface == null) return null;

        var key = (emoji, fontSize);
        if (_emojiCache.TryGetValue(key, out var cached)) return cached;

        using var paint = new SKPaint
        {
            Typeface = _emojiTypeface,
            TextSize = fontSize,
            IsAntialias = true,
            Style = SKPaintStyle.Fill,
            SubpixelText = true,
        };

        var bounds = new SKRect();
        paint.MeasureText(emoji, ref bounds);

        int w = Math.Max(1, (int)MathF.Ceiling(bounds.Width) + 2);
        int h = Math.Max(1, (int)MathF.Ceiling(bounds.Height) + 2);

        using var bitmap = new SKBitmap(new SKImageInfo(w, h, SKColorType.Rgba8888, SKAlphaType.Unpremul));
        using var canvas = new SKCanvas(bitmap);
        canvas.Clear(SKColors.Transparent);
        canvas.DrawText(emoji, -bounds.Left + 1, -bounds.Top + 1, paint);
        canvas.Flush();

        var tex = new Texture2D(_gd, w, h, false, SurfaceFormat.Color);
        tex.SetData(bitmap.GetPixelSpan().ToArray());
        _emojiCache[key] = tex;
        return tex;
    }

    /// <summary>Get a DynamicSpriteFont at the requested pixel size.</summary>
    private DynamicSpriteFont GetFont(int size)
    {
        return _fontSystem!.GetFont(size);
    }

    public void Resize(int w, int h) { Width = w; Height = h; }

    // ─── Frame lifecycle ───────────────────────────────────────────────
    public void BeginFrame()
    {
        if (_batchOpen) return;
        _sb.Begin(SpriteSortMode.Deferred, BlendState.NonPremultiplied,
                  SamplerState.LinearClamp, null, null);
        _batchOpen = true;
    }

    public void EndFrame()
    {
        if (!_batchOpen) return;
        _sb.End();
        _batchOpen = false;
    }

    /// <summary>Flush current batch and restart – use when you need to change
    /// draw ordering (e.g. overlay on top of everything).</summary>
    public void Flush()
    {
        EndFrame();
        BeginFrame();
    }

    /// <summary>Enable scissor-rectangle clipping. All draws will be clipped to the rect.</summary>
    public void PushClip(Rectangle clip)
    {
        // End the current non-scissor batch
        if (_batchOpen) { _sb.End(); _batchOpen = false; }

        _clipStack.Push(_gd.ScissorRectangle);
        _gd.ScissorRectangle = clip;

        // Restart batch with scissor test enabled
        _sb.Begin(SpriteSortMode.Deferred, BlendState.NonPremultiplied,
                  SamplerState.LinearClamp, null, _scissorRaster);
        _batchOpen = true;
    }

    /// <summary>Restore previous scissor state (or disable scissor test).</summary>
    public void PopClip()
    {
        if (_batchOpen) { _sb.End(); _batchOpen = false; }

        if (_clipStack.Count > 0)
            _gd.ScissorRectangle = _clipStack.Pop();

        // Restart normal batch (no scissor if stack is empty, otherwise caller
        // still has an outer clip active — but we always start a fresh batch here)
        if (_clipStack.Count > 0)
        {
            _sb.Begin(SpriteSortMode.Deferred, BlendState.NonPremultiplied,
                      SamplerState.LinearClamp, null, _scissorRaster);
        }
        else
        {
            _sb.Begin(SpriteSortMode.Deferred, BlendState.NonPremultiplied,
                      SamplerState.LinearClamp, null, null);
        }
        _batchOpen = true;
    }

    // ─── Primitives ────────────────────────────────────────────────────
    public void DrawRect((int R, int G, int B) color, (int X, int Y, int W, int H) rect,
                         int width = 0, int alpha = 255)
    {
        EnsureBatch();
        var c = new Color(color.R, color.G, color.B, alpha);
        var r = new Rectangle(rect.X, rect.Y, rect.W, rect.H);
        if (width == 0)
        {
            _sb.Draw(_pixel!, r, c);
        }
        else
        {
            // Outlined: 4 thin rects
            _sb.Draw(_pixel!, new Rectangle(r.X, r.Y, r.Width, width), c);                 // top
            _sb.Draw(_pixel!, new Rectangle(r.X, r.Y + r.Height - width, r.Width, width), c); // bottom
            _sb.Draw(_pixel!, new Rectangle(r.X, r.Y, width, r.Height), c);                // left
            _sb.Draw(_pixel!, new Rectangle(r.X + r.Width - width, r.Y, width, r.Height), c); // right
        }
    }

    public void DrawCircle((int R, int G, int B) color, (int X, int Y) center,
                           int radius, int width = 0, int alpha = 255)
    {
        EnsureBatch();
        if (radius <= 0) return;
        var c = new Color(color.R, color.G, color.B, alpha);

        if (width == 0)
        {
            // Filled circle via horizontal scan lines (fast enough for small radii)
            DrawFilledCircle(center.X, center.Y, radius, c);
        }
        else
        {
            // Ring: draw filled circle minus inner filled circle
            DrawRing(center.X, center.Y, radius, width, c);
        }
    }

    private void DrawFilledCircle(int cx, int cy, int r, Color c)
    {
        // Scanline approach — perfectly fine for radii < ~200 at 144fps
        int r2 = r * r;
        for (int dy = -r; dy <= r; dy++)
        {
            int halfW = (int)MathF.Sqrt(r2 - dy * dy);
            _sb.Draw(_pixel!, new Rectangle(cx - halfW, cy + dy, halfW * 2, 1), c);
        }
    }

    private void DrawRing(int cx, int cy, int outerR, int thickness, Color c)
    {
        int innerR = Math.Max(0, outerR - thickness);
        int or2 = outerR * outerR;
        int ir2 = innerR * innerR;
        for (int dy = -outerR; dy <= outerR; dy++)
        {
            int outerHalf = (int)MathF.Sqrt(Math.Max(0, or2 - dy * dy));
            int innerHalf = (dy >= -innerR && dy <= innerR)
                ? (int)MathF.Sqrt(Math.Max(0, ir2 - dy * dy))
                : 0;
            if (innerHalf > 0)
            {
                // Left arc
                _sb.Draw(_pixel!, new Rectangle(cx - outerHalf, cy + dy, outerHalf - innerHalf, 1), c);
                // Right arc
                _sb.Draw(_pixel!, new Rectangle(cx + innerHalf, cy + dy, outerHalf - innerHalf, 1), c);
            }
            else
            {
                _sb.Draw(_pixel!, new Rectangle(cx - outerHalf, cy + dy, outerHalf * 2, 1), c);
            }
        }
    }

    public void DrawLine((int R, int G, int B) color, (int X, int Y) start, (int X, int Y) end,
                         int width = 1, int alpha = 255)
    {
        EnsureBatch();
        var c = new Color(color.R, color.G, color.B, alpha);
        float dx = end.X - start.X;
        float dy = end.Y - start.Y;
        float len = MathF.Sqrt(dx * dx + dy * dy);
        if (len < 0.001f) return;
        float angle = MathF.Atan2(dy, dx);
        _sb.Draw(_pixel!, new Vector2(start.X, start.Y), null, c,
                 angle, Vector2.Zero, new Vector2(len, width), SpriteEffects.None, 0);
    }

    public void DrawText(string text, int x, int y, int fontSize = 16,
                         (int R, int G, int B)? color = null,
                         bool bold = false, string anchorX = "left", string anchorY = "top",
                         int alpha = 255, float rotation = 0f, float scale = 1f)
    {
        EnsureBatch();
        if (_fontSystem == null || string.IsNullOrEmpty(text)) return;

        var col = color ?? (255, 255, 255);
        var c = new Color(col.R, col.G, col.B, alpha);
        // Pyglet uses point sizes (1pt ≈ 1.33px at 96 DPI); FontStashSharp uses pixel sizes.
        int scaledSize = Math.Max(8, (int)(fontSize * 1.33f));
        var font = GetFont(scaledSize);

        // FontStashSharp gives us exact-size fonts — no manual scaling needed
        var measured = font.MeasureString(text);

        float ox = anchorX switch
        {
            "center" => measured.X / 2f,
            "right"  => measured.X,
            _        => 0f,
        };
        float oy = anchorY switch
        {
            "center" => measured.Y / 2f,
            "bottom" => measured.Y,
            _        => 0f,
        };

        // If text contains emoji, use segmented colored rendering (supports scale & rotation)
        if (ContainsEmoji(text))
        {
            // Measure actual emoji render width for correct centering
            float emojiWidth = MeasureTextColoredWidth(font, text, scaledSize);
            float eox = anchorX switch
            {
                "center" => emojiWidth / 2f,
                "right"  => emojiWidth,
                _        => 0f,
            };
            float eoy = anchorY switch
            {
                "center" => measured.Y / 2f,
                "bottom" => measured.Y,
                _        => 0f,
            };
            // Apply scale and rotation around the anchor point
            if (Math.Abs(rotation) < 0.001f && Math.Abs(scale - 1f) < 0.001f)
            {
                // Fast path: no transform needed
                DrawTextColored(font, text, x - eox, y - eoy, col, alpha, 1f);
            }
            else
            {
                // Transform: flush batch, apply matrix, draw, restore
                EndFrame();
                var mat = Matrix.CreateTranslation(-eox, -eoy, 0)
                        * Matrix.CreateScale(scale)
                        * Matrix.CreateRotationZ(rotation * MathF.PI / 180f)
                        * Matrix.CreateTranslation(x, y, 0);
                _sb.Begin(SpriteSortMode.Deferred, BlendState.NonPremultiplied,
                          SamplerState.LinearClamp, null, null, null, mat);
                _batchOpen = true;
                DrawTextColored(font, text, 0, 0, col, alpha, 1f);
                EndFrame();
                BeginFrame();
            }
            return;
        }

        float rad = rotation * MathF.PI / 180f;
        _sb.DrawString(font, text, new Vector2(x, y), c,
                       scale: new Vector2(scale, scale), rotation: rad,
                       origin: new Vector2(ox, oy), layerDepth: 0f);
    }

    // ─── Colored Emoji Support ─────────────────────────────────────
    // When SkiaSharp emoji typeface is loaded, emoji segments are rendered
    // as full-color sprites via SkiaSharp. Otherwise, falls back to
    // per-codepoint tinting from s_emojiColorMap.

    private static bool ContainsEmoji(string text)
    {
        foreach (char ch in text)
            if (ch > 0x2000 || char.IsHighSurrogate(ch)) return true;
        return false;
    }

    private static int GetCodepoint(string text, int index, out int charLen)
    {
        if (char.IsHighSurrogate(text[index]) && index + 1 < text.Length && char.IsLowSurrogate(text[index + 1]))
        {
            charLen = 2;
            return char.ConvertToUtf32(text[index], text[index + 1]);
        }
        charLen = 1;
        return text[index];
    }

    private static bool IsEmojiCodepoint(int cp)
    {
        // Covers common emoji ranges; deliberately broad to catch symbols+emoji
        return cp >= 0x2600 ||                    // Misc symbols and beyond
               (cp >= 0x2000 && cp <= 0x27FF) ||  // General punctuation + symbols
               s_emojiCodepoints.Contains(cp);
    }

    private static readonly HashSet<int> s_emojiCodepoints = new()
    {
        0x203C, 0x2049, 0x2139, 0x2194, 0x2195, 0x2196, 0x2197, 0x2198, 0x2199,
        0x21A9, 0x21AA, 0x231A, 0x231B, 0x2328, 0x23CF, 0x23E9, 0x23EA, 0x23EB,
        0x23EC, 0x23ED, 0x23EE, 0x23EF, 0x23F0, 0x23F1, 0x23F2, 0x23F3, 0x23F8,
        0x23F9, 0x23FA, 0x25AA, 0x25AB, 0x25B6, 0x25C0, 0x25FB, 0x25FC, 0x25FD, 0x25FE,
    };

    private void DrawTextColored(DynamicSpriteFont font, string text, float startX, float startY,
                                  (int R, int G, int B) baseCol, int alpha, float scale = 1f)
    {
        float curX = startX;
        int i = 0;

        while (i < text.Length)
        {
            int runStart = i;

            // Get first codepoint of this run
            int cp = GetCodepoint(text, i, out int cpLen);

            // Skip zero-width characters
            if (cp == 0xFE0F || cp == 0x200D)
            {
                i += cpLen;
                continue;
            }

            bool cpIsEmoji = IsEmojiCodepoint(cp);
            i += cpLen;

            // Extend run while next characters share the same emoji/non-emoji classification
            while (i < text.Length)
            {
                int nextCp = GetCodepoint(text, i, out int nextLen);

                // ZWJ and variation selectors stay with current run
                if (nextCp == 0xFE0F || nextCp == 0x200D) { i += nextLen; continue; }

                bool nextIsEmoji = IsEmojiCodepoint(nextCp);
                if (nextIsEmoji != cpIsEmoji) break;

                i += nextLen;
            }

            string segment = text[runStart..i];

            if (cpIsEmoji && _emojiTypeface != null)
            {
                // Render via SkiaSharp for full-color emoji
                int fontSize = (int)font.FontSize;
                var tex = GetEmojiTexture(segment, fontSize);
                if (tex != null)
                {
                    var tint = new Color(255, 255, 255, alpha);
                    _sb.Draw(tex, new Vector2(curX, startY), null, tint,
                             0f, Vector2.Zero, 1f, SpriteEffects.None, 0f);
                    curX += tex.Width;
                    continue;
                }
            }

            if (cpIsEmoji)
            {
                // Fallback: tint with s_emojiColorMap if SkiaSharp not available
                var tintCol = s_emojiColorMap.TryGetValue(cp, out var ec)
                    ? new Color(ec.R, ec.G, ec.B, alpha)
                    : new Color(baseCol.R, baseCol.G, baseCol.B, alpha);
                var segMeasure = font.MeasureString(segment);
                _sb.DrawString(font, segment, new Vector2(curX, startY), tintCol);
                curX += segMeasure.X;
            }
            else
            {
                // Regular text
                var segColor = new Color(baseCol.R, baseCol.G, baseCol.B, alpha);
                var segMeasure = font.MeasureString(segment);
                _sb.DrawString(font, segment, new Vector2(curX, startY), segColor);
                curX += segMeasure.X;
            }
        }
    }

    /// <summary>Measure the total width of text rendered via DrawTextColored (accounts for SkiaSharp emoji widths).</summary>
    private float MeasureTextColoredWidth(DynamicSpriteFont font, string text, int fontSizePx)
    {
        float totalW = 0;
        int i = 0;
        while (i < text.Length)
        {
            int runStart = i;
            int cp = GetCodepoint(text, i, out int cpLen);
            if (cp == 0xFE0F || cp == 0x200D) { i += cpLen; continue; }
            bool cpIsEmoji = IsEmojiCodepoint(cp);
            i += cpLen;
            while (i < text.Length)
            {
                int nextCp = GetCodepoint(text, i, out int nextLen);
                if (nextCp == 0xFE0F || nextCp == 0x200D) { i += nextLen; continue; }
                if (IsEmojiCodepoint(nextCp) != cpIsEmoji) break;
                i += nextLen;
            }
            string segment = text[runStart..i];
            if (cpIsEmoji && _emojiTypeface != null)
            {
                var tex = GetEmojiTexture(segment, fontSizePx);
                if (tex != null) { totalW += tex.Width; continue; }
            }
            totalW += font.MeasureString(segment).X;
        }
        return totalW;
    }

    /// <summary>Emoji codepoint → approximate natural colour.</summary>
    private static readonly Dictionary<int, (int R, int G, int B)> s_emojiColorMap = new()
    {
        // Card suits
        [0x2660] = (50, 50, 60),         // ♠ spade
        [0x2665] = (220, 40, 40),        // ♥ heart
        [0x2666] = (220, 40, 40),        // ♦ diamond
        [0x2663] = (50, 50, 60),         // ♣ club
        // Catan resources
        [0x1F33E] = (218, 165, 32),      // 🌾 wheat
        [0x1FAB5] = (139, 90, 43),       // 🪵 wood
        [0x1F9F1] = (178, 34, 34),       // 🧱 brick
        [0x1F411] = (240, 235, 220),     // 🐑 sheep
        [0x26CF]  = (128, 128, 140),     // ⛏ pickaxe (ore)
        [0x26F0]  = (128, 128, 140),     // ⛰ mountain
        [0x1F30A] = (30, 144, 255),      // 🌊 water
        [0x1F332] = (34, 139, 34),       // 🌲 evergreen
        [0x1F3DC] = (210, 180, 120),     // 🏜 desert
        [0x1F30B] = (200, 60, 30),       // 🌋 volcano
        [0x2B50]  = (255, 215, 0),       // ⭐ star
        [0x1FA99] = (255, 215, 0),       // 🪙 coin (gold)
        [0x2693]  = (100, 120, 140),     // ⚓ anchor
        // Unstable Unicorns
        [0x1F984] = (200, 120, 220),     // 🦄 unicorn
        [0x1F6E1] = (70, 130, 180),      // 🛡 shield
        [0x2728]  = (255, 215, 0),       // ✨ sparkles
        [0x1F525] = (255, 69, 0),        // 🔥 fire
        [0x1F4A5] = (255, 140, 0),       // 💥 explosion
        [0x2764]  = (220, 20, 60),       // ❤ heart
        [0x1F48E] = (0, 206, 209),       // 💎 gem
        [0x1F31F] = (255, 215, 0),       // 🌟 glowing star
        [0x1F308] = (255, 127, 80),      // 🌈 rainbow
        [0x1F916] = (128, 128, 128),     // 🤖 robot
        [0x1F47B] = (200, 200, 220),     // 👻 ghost
        [0x1F40D] = (50, 160, 50),       // 🐍 snake
        [0x2699]  = (160, 160, 170),     // ⚙ gear
        [0x1F52E] = (148, 103, 189),     // 🔮 crystal ball
        // Exploding Kittens
        [0x1F431] = (255, 165, 0),       // 🐱 cat
        [0x1F63A] = (255, 165, 0),       // 😺 smiley cat
        [0x1F4A3] = (60, 60, 60),        // 💣 bomb
        [0x1F640] = (255, 165, 0),       // 🙀 weary cat
        [0x1F638] = (255, 165, 0),       // 😸 grinning cat
        [0x1F639] = (255, 165, 0),       // 😹 joy cat
        // DnD
        [0x1F5E1] = (192, 192, 200),     // 🗡 dagger
        [0x1F3F9] = (139, 90, 43),       // 🏹 bow
        [0x1F9D9] = (148, 103, 189),     // 🧙 mage
        [0x1F9DD] = (144, 238, 144),     // 🧝 elf
        [0x1F480] = (245, 240, 220),     // 💀 skull
        [0x1F409] = (34, 139, 34),       // 🐉 dragon
        [0x1FA84] = (148, 103, 189),     // 🪄 wand
        // Monopoly
        [0x1F3E0] = (139, 90, 43),       // 🏠 house
        [0x1F3E8] = (70, 130, 180),      // 🏨 hotel
        [0x1F3E2] = (119, 136, 153),     // 🏢 building
        [0x1F682] = (100, 100, 110),     // 🚂 train
        [0x26A1]  = (255, 215, 0),       // ⚡ lightning
        [0x1F4B0] = (50, 205, 50),       // 💰 money bag
        [0x1F4B5] = (50, 180, 50),       // 💵 dollar
        // General
        [0x1F3B2] = (230, 230, 240),     // 🎲 dice
        [0x1F3B5] = (186, 85, 211),      // 🎵 music note
        [0x1F3C6] = (255, 215, 0),       // 🏆 trophy
        [0x2694]  = (192, 192, 200),     // ⚔ swords
        [0x1F6E3] = (139, 119, 101),     // 🛣 road
        [0x1F3F0] = (169, 169, 180),     // 🏰 castle
        [0x1F389] = (255, 140, 0),       // 🎉 party popper
        [0x1F451] = (255, 215, 0),       // 👑 crown
        [0x1F48A] = (255, 69, 0),        // 💊 pill
        [0x1F9EA] = (0, 180, 180),       // 🧪 test tube
        [0x1F52B] = (100, 100, 110),     // 🔫 pistol
        [0x1F50D] = (100, 149, 237),     // 🔍 magnifying glass
        [0x1F3AF] = (220, 40, 40),       // 🎯 bullseye
        [0x1F4DC] = (210, 180, 120),     // 📜 scroll
        [0x1F9ED] = (139, 90, 43),       // 🧭 compass
        [0x2618]  = (34, 139, 34),       // ☘ shamrock
        [0x1F340] = (34, 180, 34),       // 🍀 four leaf clover
        [0x1F381] = (220, 40, 40),       // 🎁 gift
        [0x1F6A8] = (220, 40, 40),       // 🚨 siren
        [0x1F46E] = (70, 130, 180),      // 👮 police officer
        [0x1F3E5] = (220, 20, 60),       // 🏥 hospital
        [0x1F512] = (200, 170, 50),      // 🔒 locked
        [0x1F513] = (200, 170, 50),      // 🔓 unlocked
        [0x274C]  = (220, 40, 40),       // ❌ cross
        [0x2705]  = (50, 180, 50),       // ✅ check
        [0x26D4]  = (220, 40, 40),       // ⛔ no entry
        [0x1F4CE] = (160, 160, 170),     // 📎 paperclip
        [0x2618]  = (34, 139, 34),       // ☘ shamrock
    };

    public void DrawCircularProgress((int X, int Y) center, int radius, float progress,
                                     (int R, int G, int B) color, int thickness = 4, int alpha = 255)
    {
        // Background ring
        DrawCircle((50, 50, 50), center, radius, width: thickness, alpha: alpha);
        // Progress — approximate with filled arc segments
        if (progress <= 0) return;
        int segments = Math.Max(4, (int)(progress * 64));
        var c = new Color(color.R, color.G, color.B, alpha);
        EnsureBatch();
        float startAngle = -MathF.PI / 2f; // top
        for (int i = 0; i < segments; i++)
        {
            float a = startAngle + (i / (float)segments) * progress * MathF.Tau;
            int px = center.X + (int)(MathF.Cos(a) * radius);
            int py = center.Y + (int)(MathF.Sin(a) * radius);
            _sb.Draw(_pixel!, new Rectangle(px - thickness / 2, py - thickness / 2, thickness, thickness), c);
        }
    }

    // ─── Texture helpers ───────────────────────────────────────────────
    public void DrawTexture(Texture2D tex, Rectangle dest, int alpha = 255)
    {
        EnsureBatch();
        _sb.Draw(tex, dest, new Color(255, 255, 255, alpha));
    }

    /// <summary>Draw a filled or outlined polygon given a list of (x,y) vertices.</summary>
    public void DrawPolygon((int R, int G, int B) color, (float X, float Y)[] points,
                            int width = 0, int alpha = 255)
    {
        if (points.Length < 3) return;
        EnsureBatch();

        if (width > 0)
        {
            // Outlined: draw line segments for each edge
            for (int i = 0; i < points.Length; i++)
            {
                var a = points[i];
                var b = points[(i + 1) % points.Length];
                DrawLine(color, ((int)a.X, (int)a.Y), ((int)b.X, (int)b.Y), width: width, alpha: alpha);
            }
            return;
        }

        // Filled polygon via triangle fan from centroid using scanline approach
        var c = new Color(color.R, color.G, color.B, alpha);

        // Find bounding box
        float minY = points[0].Y, maxY = points[0].Y;
        for (int i = 1; i < points.Length; i++)
        {
            if (points[i].Y < minY) minY = points[i].Y;
            if (points[i].Y > maxY) maxY = points[i].Y;
        }

        int iy0 = (int)MathF.Floor(minY);
        int iy1 = (int)MathF.Ceiling(maxY);

        // Scanline fill
        var xIntersections = new List<float>();
        for (int y = iy0; y <= iy1; y++)
        {
            xIntersections.Clear();
            float yf = y + 0.5f;
            for (int i = 0; i < points.Length; i++)
            {
                var p0 = points[i];
                var p1 = points[(i + 1) % points.Length];
                if ((p0.Y <= yf && p1.Y > yf) || (p1.Y <= yf && p0.Y > yf))
                {
                    float t = (yf - p0.Y) / (p1.Y - p0.Y);
                    xIntersections.Add(p0.X + t * (p1.X - p0.X));
                }
            }
            xIntersections.Sort();
            for (int i = 0; i + 1 < xIntersections.Count; i += 2)
            {
                int x0 = (int)MathF.Floor(xIntersections[i]);
                int x1 = (int)MathF.Ceiling(xIntersections[i + 1]);
                if (x1 > x0)
                    _sb.Draw(_pixel!, new Rectangle(x0, y, x1 - x0, 1), c);
            }
        }
    }

    public void Clear((int R, int G, int B) color)
    {
        _gd.Clear(new Color(color.R, color.G, color.B));
    }

    // ─── SkiaSharp → MonoGame texture conversion ────────────────────────
    private readonly Dictionary<string, Texture2D> _skiaTextureCache = new();

    /// <summary>Create a MonoGame Texture2D from a SkiaSharp bitmap. Caller must dispose the bitmap.</summary>
    public Texture2D TextureFromSkia(SKBitmap bitmap)
    {
        int w = bitmap.Width, h = bitmap.Height;
        var tex = new Texture2D(_gd, w, h, false, SurfaceFormat.Color);
        tex.SetData(bitmap.GetPixelSpan().ToArray());
        return tex;
    }

    /// <summary>Get or create a cached texture rendered via SkiaSharp.</summary>
    public Texture2D GetOrCreateSkiaTexture(string cacheKey, int w, int h, Action<SKCanvas, int, int> drawAction)
    {
        if (_skiaTextureCache.TryGetValue(cacheKey, out var cached))
            return cached;

        using var bitmap = new SKBitmap(new SKImageInfo(w, h, SKColorType.Rgba8888, SKAlphaType.Unpremul));
        using var canvas = new SKCanvas(bitmap);
        canvas.Clear(SKColors.Transparent);
        drawAction(canvas, w, h);
        canvas.Flush();

        var tex = TextureFromSkia(bitmap);
        _skiaTextureCache[cacheKey] = tex;
        return tex;
    }

    // ─── Internals ─────────────────────────────────────────────────────
    private void EnsureBatch()
    {
        if (!_batchOpen) BeginFrame();
    }

    public void Dispose()
    {
        foreach (var tex in _emojiCache.Values) tex.Dispose();
        _emojiCache.Clear();
        foreach (var tex in _skiaTextureCache.Values) tex.Dispose();
        _skiaTextureCache.Clear();
        _emojiTypeface?.Dispose();
        _pixel?.Dispose();
        _sb.Dispose();
    }
}
