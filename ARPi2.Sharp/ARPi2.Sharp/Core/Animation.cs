using System;
using System.Collections.Generic;

namespace ARPi2.Sharp.Core;

/// <summary>
/// Particle system, card-fly, card-flip, text-pop, pulse-ring, screen-flash,
/// dice-roll, and rainbow-title — ported from Python core/animation.py.
/// All times are in seconds; all positions in screen pixels.
/// </summary>
/// 
// ═══════════════════════════════════════════════════════════════════════════
//  Palette helpers
// ═══════════════════════════════════════════════════════════════════════════
public static class AnimPalette
{
    public static readonly (int R, int G, int B)[] Rainbow =
    {
        (255,  60, 120), (200,  50, 255), ( 55, 170, 255),
        ( 55, 230, 130), (255, 220,  50), (255, 110,  40),
    };

    public static readonly (int R, int G, int B)[] TitleRainbow =
    {
        (255,  55,  55), (255, 140,   0), (255, 220,   0),
        ( 55, 200,  55), ( 70, 130, 255), (200,  55, 255),
    };
}

// ═══════════════════════════════════════════════════════════════════════════
//  Particle
// ═══════════════════════════════════════════════════════════════════════════
public struct Particle
{
    public float X, Y, VX, VY;
    public (int R, int G, int B) Color;
    public float Life, MaxLife, Radius, Gravity;

    public bool Alive => Life > 0f;
    public int Alpha => Math.Max(0, (int)(255 * MathF.Pow(Life / MaxLife, 0.55f)));
    public int CurRadius => Math.Max(1, (int)(Radius * (0.35f + 0.65f * Life / MaxLife)));

    public void Update(float dt)
    {
        X += VX * dt;
        Y += VY * dt;
        VY += Gravity * dt; // positive = downward in screen coords
        VX *= MathF.Max(0f, 1f - 1.6f * dt);
        Life -= dt;
    }
}

public class ParticleSystem
{
    private readonly List<Particle> _particles = new();
    private static readonly Random _rng = new();

    public bool Empty => _particles.Count == 0;

    public void Emit(float x, float y, (int R, int G, int B) color,
                     int count = 28, float speed = 290f, float gravity = 370f,
                     float life = 1.15f, float radius = 3.5f)
    {
        for (int i = 0; i < count; i++)
        {
            float angle = (float)(_rng.NextDouble() * Math.Tau);
            float spd   = (float)(_rng.NextDouble() * 0.7 + 0.3) * speed;
            float lt    = (float)(_rng.NextDouble() * 0.55 + 0.55) * life;
            _particles.Add(new Particle
            {
                X = x, Y = y,
                VX = MathF.Cos(angle) * spd,
                VY = MathF.Sin(angle) * spd,
                Color = color, Life = lt, MaxLife = lt,
                Radius = radius, Gravity = gravity,
            });
        }
    }

    public void EmitFirework(float x, float y, (int R, int G, int B)[] colors,
                             int total = 80)
    {
        int per = Math.Max(1, total / Math.Max(1, colors.Length));
        foreach (var c in colors)
            Emit(x, y, c, per, 330, 260, 1.55f, 3.5f);
    }

    public void EmitSparkle(float x, float y, (int R, int G, int B) color, int count = 12)
        => Emit(x, y, color, count, 130, 200, 0.7f, 2.5f);

    public void Update(float dt)
    {
        for (int i = _particles.Count - 1; i >= 0; i--)
        {
            var p = _particles[i];
            p.Update(dt);
            if (!p.Alive) { _particles.RemoveAt(i); continue; }
            _particles[i] = p;
        }
    }

    public void Draw(Renderer renderer)
    {
        foreach (ref readonly var p in System.Runtime.InteropServices.CollectionsMarshal.AsSpan(_particles))
            renderer.DrawCircle(p.Color, ((int)p.X, (int)p.Y), p.CurRadius, alpha: p.Alpha);
    }
}

// ═══════════════════════════════════════════════════════════════════════════
//  Card fly animation
// ═══════════════════════════════════════════════════════════════════════════
public class CardFlyAnim
{
    public (int X, int Y) Src, Dst;
    public int CardW, CardH;
    public (int R, int G, int B) Color;
    public float Duration, T;
    public bool Done;

    public CardFlyAnim((int, int) src, (int, int) dst, int cardW = 90, int cardH = 122,
                       (int, int, int)? color = null, float duration = 0.52f)
    {
        Src = src; Dst = dst; CardW = cardW; CardH = cardH;
        Color = color ?? (160, 80, 200); Duration = duration;
    }

    public void Update(float dt) { T = MathF.Min(T + dt, Duration); if (T >= Duration) Done = true; }

    public void Draw(Renderer r)
    {
        float p = T / Duration;
        float ep = 1f - MathF.Pow(1f - p, 3f);
        float cx = Src.X + (Dst.X - Src.X) * ep;
        float cy = Src.Y + (Dst.Y - Src.Y) * ep;
        cy -= MathF.Sin(MathF.PI * p) * 70;

        float sx = MathF.Abs(MathF.Cos(MathF.PI * p * 1.1f));
        int dw = Math.Max(4, (int)(CardW * sx));
        int dh = CardH;
        int dx = (int)(cx - dw / 2f);
        int dy = (int)(cy - dh / 2f);

        var border = p < 0.48f ? Color
            : (Math.Min(255, (int)(Color.R * 1.5)), Math.Min(255, (int)(Color.G * 1.5)), Math.Min(255, (int)(Color.B * 1.5)));
        int tintA = p < 0.48f ? 60 : 90;

        if (p > 0.05f && p < 0.92f)
        {
            int trailA = (int)(28 * MathF.Sin(MathF.PI * p));
            r.DrawCircle(Color, ((int)cx, (int)cy), Math.Max(8, CardW * 35 / 100), alpha: trailA);
        }
        r.DrawRect((0, 0, 0), (dx + 4, dy + 4, dw, dh), alpha: 50);
        r.DrawRect((250, 250, 250), (dx, dy, dw, dh), alpha: 225);
        r.DrawRect(Color, (dx, dy, dw, dh), alpha: tintA);
        if (dw > 10) r.DrawRect((255, 255, 255), (dx + 2, dy + 2, dw - 4, 5), alpha: 80);
        r.DrawRect(border, (dx, dy, dw, dh), width: 3, alpha: 245);
    }
}

// ═══════════════════════════════════════════════════════════════════════════
//  Card flip in place
// ═══════════════════════════════════════════════════════════════════════════
public class CardFlipInPlace
{
    public int X, Y, CardW, CardH;
    public (int R, int G, int B) BackColor, FrontColor;
    public float Duration, T;
    public bool Done;

    public CardFlipInPlace(int x, int y, int cardW = 90, int cardH = 122,
                           (int, int, int)? backColor = null, (int, int, int)? frontColor = null,
                           float duration = 0.48f)
    {
        X = x; Y = y; CardW = cardW; CardH = cardH;
        BackColor = backColor ?? (60, 60, 130);
        FrontColor = frontColor ?? (250, 250, 255);
        Duration = duration;
    }

    public void Update(float dt) { T = MathF.Min(T + dt, Duration); if (T >= Duration) Done = true; }

    public void Draw(Renderer r)
    {
        float p = T / Duration;
        float sx = MathF.Abs(MathF.Cos(MathF.PI * p));
        int dw = Math.Max(2, (int)(CardW * sx));
        int dh = CardH;
        int dx = X - dw / 2, dy = Y - dh / 2;
        bool isFront = p >= 0.5f;
        var col = isFront ? FrontColor : BackColor;

        r.DrawRect((0, 0, 0), (dx + 3, dy + 3, dw, dh), alpha: 55);
        r.DrawRect(col, (dx, dy, dw, dh), alpha: 235);
        r.DrawRect((70, 70, 80), (dx, dy, dw, dh), width: 2, alpha: 200);
        if (isFront && dw > 10) r.DrawRect((255, 255, 255), (dx + 2, dy + 2, dw - 4, 5), alpha: 100);
    }
}

// ═══════════════════════════════════════════════════════════════════════════
//  Card showcase — hold card face-up at center with sparkles, then fade out
// ═══════════════════════════════════════════════════════════════════════════
public class CardShowcaseAnim
{
    public int X, Y, CardW, CardH;
    public string Emoji, Label, Corner;
    public (int R, int G, int B) AccentColor;
    public float FlyDuration, HoldDuration, FadeDuration;
    public float T;
    public bool Done;

    // Sparkle timer
    private float _sparkleTimer;
    private const float SparkleInterval = 0.08f;
    private static readonly Random _rng = new();

    // Source position for fly-in
    public (int X, int Y) Src;

    public CardShowcaseAnim(int x, int y, string emoji, string label,
        (int, int, int)? accentColor = null, string corner = "",
        int cardW = 140, int cardH = 195,
        float flyDuration = 0.35f, float holdDuration = 1.8f, float fadeDuration = 0.4f,
        (int, int)? src = null)
    {
        X = x; Y = y; CardW = cardW; CardH = cardH;
        Emoji = emoji; Label = label; Corner = corner;
        AccentColor = accentColor ?? (160, 80, 200);
        FlyDuration = flyDuration; HoldDuration = holdDuration; FadeDuration = fadeDuration;
        Src = src ?? (x, y + 300);
    }

    public float TotalDuration => FlyDuration + HoldDuration + FadeDuration;

    public void Update(float dt, ParticleSystem particles)
    {
        T = MathF.Min(T + dt, TotalDuration);
        if (T >= TotalDuration) { Done = true; return; }

        // Emit sparkles during hold phase
        if (T > FlyDuration && T < FlyDuration + HoldDuration)
        {
            _sparkleTimer += dt;
            while (_sparkleTimer >= SparkleInterval)
            {
                _sparkleTimer -= SparkleInterval;
                float angle = (float)(_rng.NextDouble() * Math.PI * 2);
                float dist = CardW * 0.5f + (float)_rng.NextDouble() * CardW * 0.3f;
                float sx = X + MathF.Cos(angle) * dist;
                float sy = Y + MathF.Sin(angle) * dist;
                var sparkCol = _rng.Next(3) switch
                {
                    0 => (255, 255, 180),
                    1 => (255, 220, 100),
                    _ => (Math.Min(255, AccentColor.R + 80),
                          Math.Min(255, AccentColor.G + 80),
                          Math.Min(255, AccentColor.B + 80))
                };
                particles.EmitSparkle(sx, sy, sparkCol, 3);
            }
        }
    }

    public void Draw(Renderer r)
    {
        if (Done) return;
        float totalDur = TotalDuration;

        // Phase calculations
        float alpha = 1f;
        float scale = 1f;
        float cx = X, cy = Y;

        if (T < FlyDuration)
        {
            // Fly-in phase: ease-out cubic from src to center
            float p = T / FlyDuration;
            float ep = 1f - MathF.Pow(1f - p, 3f);
            cx = Src.X + (X - Src.X) * ep;
            cy = Src.Y + (Y - Src.Y) * ep;
            scale = 0.5f + 0.5f * ep;
            // Slight bounce at end
            if (p > 0.85f)
            {
                float bp = (p - 0.85f) / 0.15f;
                scale += 0.08f * MathF.Sin(MathF.PI * bp);
            }
        }
        else if (T > FlyDuration + HoldDuration)
        {
            // Fade-out phase
            float fadeP = (T - FlyDuration - HoldDuration) / FadeDuration;
            alpha = 1f - fadeP * fadeP;
            scale = 1f - 0.15f * fadeP;
        }
        else
        {
            // Hold phase — gentle breathing
            float holdP = (T - FlyDuration) / HoldDuration;
            scale = 1f + 0.02f * MathF.Sin(holdP * MathF.PI * 2f * 1.5f);
        }

        int w = (int)(CardW * scale);
        int h = (int)(CardH * scale);
        int dx = (int)(cx - w / 2f);
        int dy = (int)(cy - h / 2f);
        int a = Math.Clamp((int)(alpha * 255), 0, 255);

        if (a <= 0) return;

        // Glow behind card during hold/fade
        if (T >= FlyDuration)
        {
            int glowA = (int)(60 * alpha);
            int glowR = w * 3 / 4;
            r.DrawCircle(AccentColor, ((int)cx, (int)cy), glowR, alpha: glowA);
            r.DrawCircle((255, 255, 200), ((int)cx, (int)cy), glowR / 2, alpha: glowA / 2);
        }

        // Shadow
        r.DrawRect((0, 0, 0), (dx + 6, dy + 6, w, h), alpha: (int)(60 * alpha));

        // Draw the card using CardRendering
        CardRendering.DrawEmojiCard(r, (dx, dy, w, h), Emoji, "",
            accentRgb: AccentColor, corner: Corner, maxTitleFontSize: 14);

        // Alpha overlay for fade-out
        if (alpha < 1f)
        {
            int fadeA = 255 - a;
            // We can't directly set alpha on DrawEmojiCard, so we don't dim further
            // The glow and sparkles fading is sufficient
        }
    }
}

// ═══════════════════════════════════════════════════════════════════════════
//  Text pop-in / fade-out
// ═══════════════════════════════════════════════════════════════════════════
public class TextPopAnim
{
    public string Text;
    public int X, Y, FontSize;
    public (int R, int G, int B) Color;
    public float Duration, T;
    public bool Done;

    public TextPopAnim(string text, int x, int y, (int, int, int)? color = null,
                       int fontSize = 42, float duration = 2.0f)
    {
        Text = text; X = x; Y = y; Color = color ?? (255, 230, 50);
        FontSize = fontSize; Duration = duration;
    }

    public void Update(float dt) { T = MathF.Min(T + dt, Duration); if (T >= Duration) Done = true; }

    public void Draw(Renderer r)
    {
        float p = T / Duration;
        float scale; int alpha;
        if (p < 0.10f)
        {
            // Elastic scale-in (snappy pop)
            float t = p / 0.10f;
            float overshoot = 1f + 0.25f * MathF.Sin(MathF.PI * t) * (1f - t);
            scale = t * overshoot;
            alpha = 255;
        }
        else if (p < 0.72f)
        {
            // Gentle breathing wobble
            scale = 1f + 0.03f * MathF.Sin(MathF.PI * (p - 0.10f) / 0.62f * 2);
            alpha = 255;
        }
        else
        {
            // Smooth fade-out with slight shrink
            float fadeP = (p - 0.72f) / 0.28f;
            scale = 1f - 0.08f * fadeP;
            alpha = (int)(255 * (1f - fadeP * fadeP)); // quadratic fade for smoothness
        }

        if (alpha <= 0 || scale <= 0.01f) return;

        // Render at FULL font size and use GPU scale — avoids integer font-size stepping
        r.DrawText(Text, X + 2, Y + 2, fontSize: FontSize, color: (0, 0, 0), alpha: Math.Min(120, alpha),
                   anchorX: "center", anchorY: "center", scale: scale);
        r.DrawText(Text, X, Y, fontSize: FontSize, color: Color, alpha: alpha,
                   anchorX: "center", anchorY: "center", scale: scale);
    }
}

// ═══════════════════════════════════════════════════════════════════════════
//  Pulse ring
// ═══════════════════════════════════════════════════════════════════════════
public class PulseRing
{
    public int X, Y, MaxRadius;
    public (int R, int G, int B) Color;
    public float Duration, T;
    public bool Done;

    public PulseRing(int x, int y, (int, int, int) color, int maxRadius = 110, float duration = 0.72f)
    {
        X = x; Y = y; Color = color; MaxRadius = maxRadius; Duration = duration;
    }

    public void Update(float dt) { T = MathF.Min(T + dt, Duration); if (T >= Duration) Done = true; }

    public void Draw(Renderer r)
    {
        float p = T / Duration;
        int rad = Math.Max(3, (int)(MaxRadius * p));
        int alpha = (int)(210 * MathF.Pow(1f - p, 0.7f));
        if (alpha <= 0) return;
        for (int dr = -4; dr <= 4; dr += 2)
        {
            int rr = rad + dr;
            if (rr > 0) r.DrawCircle(Color, (X, Y), rr, width: 1, alpha: alpha);
        }
    }
}

// ═══════════════════════════════════════════════════════════════════════════
//  Screen flash
// ═══════════════════════════════════════════════════════════════════════════
public class ScreenFlash
{
    public (int R, int G, int B) Color;
    public int PeakAlpha;
    public float Duration, T;
    public bool Done;

    public ScreenFlash((int, int, int)? color = null, int peakAlpha = 120, float duration = 0.38f)
    {
        Color = color ?? (255, 255, 255); PeakAlpha = peakAlpha; Duration = duration;
    }

    public void Update(float dt) { T = MathF.Min(T + dt, Duration); if (T >= Duration) Done = true; }

    public void Draw(Renderer r, int w, int h)
    {
        float p = T / Duration;
        int alpha = (int)(PeakAlpha * MathF.Pow(1f - p, 1.4f));
        if (alpha > 0) r.DrawRect(Color, (0, 0, w, h), alpha: alpha);
    }
}

// ═══════════════════════════════════════════════════════════════════════════
//  Die pips helper
// ═══════════════════════════════════════════════════════════════════════════
public static class DiePips
{
    private static readonly (int, int)[][] PipPositions =
    {
        Array.Empty<(int,int)>(),                                           // 0 (unused)
        new[] { (0, 0) },                                                   // 1
        new[] { (-1, -1), (1, 1) },                                         // 2
        new[] { (-1, -1), (0, 0), (1, 1) },                                 // 3
        new[] { (-1, -1), (1, -1), (-1, 1), (1, 1) },                       // 4
        new[] { (-1, -1), (1, -1), (0, 0), (-1, 1), (1, 1) },               // 5
        new[] { (-1, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (1, 1) },      // 6
    };

    public static void Draw(Renderer r, int cx, int cy, int size, int value)
    {
        int pipR  = Math.Max(3, size / 9);
        int off   = size / 4;
        if (value < 1 || value > 6) return;
        foreach (var (dx, dy) in PipPositions[value])
        {
            int px = cx + dx * off, py = cy + dy * off;
            r.DrawCircle((0, 0, 0), (px + 1, py + 1), pipR, alpha: 45);
            r.DrawCircle((15, 15, 22), (px, py), pipR, alpha: 245);
            r.DrawCircle((55, 55, 65), (px - 1, py - 1), Math.Max(1, pipR - 2), alpha: 70);
        }
    }
}

// ═══════════════════════════════════════════════════════════════════════════
//  Dice roll animation
// ═══════════════════════════════════════════════════════════════════════════
public class DiceRollAnimation
{
    public int DieSize, Gap;
    public float RollDuration, ShowDuration;
    public (int R, int G, int B) Accent;
    public int[] FinalValues = Array.Empty<int>();

    private float _start;
    private bool _active;
    private float _seed;
    private float _clock;
    private static readonly Random _rng = new();

    public bool Rolling  => _active && _clock - _start < RollDuration;
    public bool Visible  => _active && _clock - _start < RollDuration + ShowDuration;
    public bool JustResolved => _active && (_clock - _start) is >= 0 and < 0.4f
        ? (_clock - _start >= RollDuration) : false;

    public DiceRollAnimation(int dieSize = 68, int gap = 20, float rollDuration = 1.2f,
                             float showDuration = 3f, (int, int, int)? accent = null)
    {
        DieSize = dieSize; Gap = gap; RollDuration = rollDuration;
        ShowDuration = showDuration; Accent = accent ?? (255, 215, 0);
    }

    public void Start(int[] values) { FinalValues = values; _start = _clock; _active = true; _seed = (float)_rng.NextDouble() * 100; }
    public void Hide() => _active = false;

    public void Update(float totalSeconds) => _clock = totalSeconds;

    public void Draw(Renderer r, int cx, int cy, string totalText = "")
    {
        if (!Visible || FinalValues.Length == 0) return;
        float elapsed = _clock - _start;
        bool isRolling = elapsed < RollDuration;
        float glow = elapsed >= RollDuration ? MathF.Max(0f, 1f - (elapsed - RollDuration) / 0.55f) : 0f;

        int n = FinalValues.Length;
        int tw = n * DieSize + (n - 1) * Gap;
        int sx = cx - tw / 2;

        for (int i = 0; i < n; i++)
        {
            int jx = 0, jy = 0, bounce = 0;
            if (isRolling)
            {
                float ph = elapsed * 34 + i * 2.3f + _seed;
                jx = (int)(6 * MathF.Sin(ph));
                jy = (int)(5 * MathF.Cos(ph * 1.35f + 0.8f));
            }
            if (glow is > 0.25f and <= 1f)
                bounce = (int)(10 * MathF.Sin(MathF.PI * (glow - 0.25f) / 0.75f));

            int dcx = sx + i * (DieSize + Gap) + DieSize / 2 + jx;
            int dcy = cy + jy - bounce;
            int hx = dcx - DieSize / 2, hy = dcy - DieSize / 2;
            int val = isRolling ? _rng.Next(1, 7) : FinalValues[i];

            r.DrawRect((0, 0, 0), (hx + 6, hy + 6, DieSize, DieSize), alpha: 45);
            r.DrawRect((0, 0, 0), (hx + 3, hy + 3, DieSize, DieSize), alpha: 70);
            r.DrawRect((250, 250, 255), (hx, hy, DieSize, DieSize));
            r.DrawRect((210, 210, 220), (hx + 2, hy + DieSize * 2 / 3, DieSize - 4, DieSize / 3 - 2), alpha: 35);
            r.DrawRect((255, 255, 255), (hx + 3, hy + 2, DieSize - 6, 7), alpha: 140);
            r.DrawRect((40, 40, 48), (hx, hy, DieSize, DieSize), width: 2, alpha: 230);
            r.DrawRect((180, 180, 195), (hx + 4, hy + 4, DieSize - 8, DieSize - 8), width: 1, alpha: 55);
            if (glow > 0)
            {
                int ga = (int)(90 * glow);
                r.DrawRect(Accent, (hx - 4, hy - 4, DieSize + 8, DieSize + 8), width: 3, alpha: ga);
            }
            DiePips.Draw(r, dcx, dcy, DieSize, val);
        }

        if (!string.IsNullOrEmpty(totalText) && !isRolling)
        {
            int tx = cx + tw / 2 + 16;
            r.DrawText(totalText, tx + 2, cy + 2, fontSize: 20, color: (0, 0, 0), alpha: 140,
                       anchorX: "left", anchorY: "center", bold: true);
            r.DrawText(totalText, tx, cy, fontSize: 20, color: (255, 235, 80),
                       anchorX: "left", anchorY: "center", bold: true);
        }
    }
}

// ═══════════════════════════════════════════════════════════════════════════
//  Rainbow title
// ═══════════════════════════════════════════════════════════════════════════
public static class RainbowTitle
{
    public static void Draw(Renderer r, string title, int w, int y = 12,
                            int fontSize = 22, int charWidth = 16)
    {
        // Calculate proportional widths for each character
        int totalWidth = 0;
        for (int i = 0; i < title.Length; i++)
            totalWidth += ProportionalWidth(title[i], charWidth);

        int tx = w / 2 - totalWidth / 2;
        int cx = tx;
        for (int i = 0; i < title.Length; i++)
        {
            int cw = ProportionalWidth(title[i], charWidth);
            var col = AnimPalette.TitleRainbow[i % AnimPalette.TitleRainbow.Length];
            r.DrawText(title[i].ToString(), cx + cw / 2, y, fontSize: fontSize,
                       color: col, bold: true, anchorX: "center", anchorY: "top");
            cx += cw;
        }
    }

    private static int ProportionalWidth(char c, int baseWidth) => c switch
    {
        'I' or 'i' or 'l' or '!' or '|' or ':' or ';' or '.' or ',' or '\'' => baseWidth * 5 / 10,
        '1' => baseWidth * 6 / 10,
        'M' or 'W' or 'm' or 'w' => baseWidth * 12 / 10,
        ' ' => baseWidth * 6 / 10,
        _ => baseWidth,
    };
}

// ═══════════════════════════════════════════════════════════════════════════
//  Ambient background animation system — looping, low-key visual effects
// ═══════════════════════════════════════════════════════════════════════════

/// <summary>A single floating ambient element (mote, star, bubble, etc.).</summary>
public struct AmbientMote
{
    public float X, Y, VX, VY, Life, MaxLife, Radius, Phase;
    public (int R, int G, int B) Color;
    public byte Kind; // 0=circle, 1=diamond, 2=star-cross, 3=line-dash

    public bool Alive => Life > 0f;
    public float Alpha01 => MathF.Min(Life / MaxLife, MathF.Min(1f, (MaxLife - Life) / 0.6f));
}

/// <summary>
/// Constantly emits and ticks ambient background motes. Each game creates one
/// with its own theme. Call Update every frame, Draw after the background but
/// before game content.
/// </summary>
public class AmbientSystem
{
    private readonly List<AmbientMote> _motes = new();
    private readonly Random _rng = new();
    private float _timer;

    // Config — set once at construction
    public float EmitInterval = 0.18f;
    public int MaxMotes = 70;
    public float MinLife = 3f, MaxLifeVal = 7f;
    public float MinRadius = 1.5f, MaxRadius = 4f;
    public float MinSpeed = 8f, MaxSpeed = 30f;
    public float Gravity;   // positive = down
    public float Drift;     // horizontal oscillation strength
    public int BaseAlpha = 35;
    public (int R, int G, int B)[] Palette = { (255, 255, 255) };
    public byte[] AllowedKinds = { 0 };
    public bool EmitFromTop, EmitFromBottom = true, EmitFromSides;
    public bool RisingOnly;

    /// <summary>Pre-made theme presets.</summary>
    public static AmbientSystem ForTheme(string theme, int w, int h) => theme switch
    {
        "blackjack" or "texas_holdem" => new AmbientSystem
        {
            EmitInterval = 0.28f, MaxMotes = 50, MinLife = 4f, MaxLifeVal = 8f,
            MinRadius = 1f, MaxRadius = 3f, MinSpeed = 6f, MaxSpeed = 18f,
            Gravity = -4f, Drift = 12f, BaseAlpha = 22,
            Palette = new[] { (255, 215, 80), (220, 180, 60), (180, 140, 50), (255, 240, 160) },
            AllowedKinds = new byte[] { 0, 1 }, EmitFromBottom = true, RisingOnly = true,
        },
        "catan" => new AmbientSystem
        {
            EmitInterval = 0.32f, MaxMotes = 45, MinLife = 5f, MaxLifeVal = 9f,
            MinRadius = 1.5f, MaxRadius = 3.5f, MinSpeed = 10f, MaxSpeed = 25f,
            Gravity = 0f, Drift = 18f, BaseAlpha = 20,
            Palette = new[] { (200, 160, 80), (180, 220, 100), (120, 180, 220), (240, 200, 120) },
            AllowedKinds = new byte[] { 0, 3 }, EmitFromSides = true,
        },
        "cluedo" => new AmbientSystem
        {
            EmitInterval = 0.4f, MaxMotes = 35, MinLife = 5f, MaxLifeVal = 10f,
            MinRadius = 1f, MaxRadius = 2.5f, MinSpeed = 4f, MaxSpeed = 12f,
            Gravity = -2f, Drift = 6f, BaseAlpha = 18,
            Palette = new[] { (160, 140, 180), (120, 100, 160), (200, 180, 220), (100, 80, 140) },
            AllowedKinds = new byte[] { 0 }, EmitFromBottom = true, RisingOnly = true,
        },
        "monopoly" => new AmbientSystem
        {
            EmitInterval = 0.25f, MaxMotes = 55, MinLife = 3.5f, MaxLifeVal = 7f,
            MinRadius = 1.5f, MaxRadius = 3f, MinSpeed = 8f, MaxSpeed = 22f,
            Gravity = 5f, Drift = 15f, BaseAlpha = 18,
            Palette = new[] { (120, 200, 120), (255, 215, 0), (200, 200, 200), (100, 180, 255) },
            AllowedKinds = new byte[] { 0, 1 }, EmitFromTop = true,
        },
        "risk" => new AmbientSystem
        {
            EmitInterval = 0.35f, MaxMotes = 40, MinLife = 4f, MaxLifeVal = 8f,
            MinRadius = 1f, MaxRadius = 2.5f, MinSpeed = 12f, MaxSpeed = 30f,
            Gravity = 0f, Drift = 10f, BaseAlpha = 16,
            Palette = new[] { (200, 80, 80), (80, 120, 200), (200, 200, 80), (180, 180, 180) },
            AllowedKinds = new byte[] { 0, 2 }, EmitFromSides = true,
        },
        "dnd" => new AmbientSystem
        {
            EmitInterval = 0.22f, MaxMotes = 55, MinLife = 4f, MaxLifeVal = 8f,
            MinRadius = 1f, MaxRadius = 3.5f, MinSpeed = 5f, MaxSpeed = 15f,
            Gravity = -6f, Drift = 8f, BaseAlpha = 25,
            Palette = new[] { (255, 160, 40), (255, 120, 20), (255, 200, 80), (200, 80, 20) },
            AllowedKinds = new byte[] { 0, 1 }, EmitFromBottom = true, RisingOnly = true,
        },
        "exploding_kittens" => new AmbientSystem
        {
            EmitInterval = 0.3f, MaxMotes = 45, MinLife = 3f, MaxLifeVal = 6f,
            MinRadius = 1.5f, MaxRadius = 3f, MinSpeed = 8f, MaxSpeed = 20f,
            Gravity = -8f, Drift = 10f, BaseAlpha = 20,
            Palette = new[] { (255, 100, 40), (255, 160, 20), (255, 60, 20), (200, 50, 10) },
            AllowedKinds = new byte[] { 0 }, EmitFromBottom = true, RisingOnly = true,
        },
        "unstable_unicorns" => new AmbientSystem
        {
            EmitInterval = 0.2f, MaxMotes = 60, MinLife = 4f, MaxLifeVal = 8f,
            MinRadius = 1f, MaxRadius = 3f, MinSpeed = 5f, MaxSpeed = 14f,
            Gravity = -3f, Drift = 12f, BaseAlpha = 22,
            Palette = new[] { (200, 150, 255), (255, 180, 220), (150, 200, 255), (255, 255, 180) },
            AllowedKinds = new byte[] { 0, 1, 2 }, EmitFromBottom = true, RisingOnly = true,
        },
        "uno" => new AmbientSystem
        {
            EmitInterval = 0.22f, MaxMotes = 55, MinLife = 3f, MaxLifeVal = 7f,
            MinRadius = 1.5f, MaxRadius = 3.5f, MinSpeed = 10f, MaxSpeed = 28f,
            Gravity = 0f, Drift = 20f, BaseAlpha = 18,
            Palette = new[] { (255, 55, 55), (55, 120, 255), (55, 200, 55), (255, 220, 50) },
            AllowedKinds = new byte[] { 0, 1 }, EmitFromSides = true,
        },
        _ => new AmbientSystem(),
    };

    private int _screenW, _screenH;

    public void Update(float dt, int screenW, int screenH)
    {
        _screenW = screenW; _screenH = screenH;
        _timer += dt;

        // Emit new motes
        while (_timer >= EmitInterval && _motes.Count < MaxMotes)
        {
            _timer -= EmitInterval;
            EmitOne(screenW, screenH);
        }
        if (_timer >= EmitInterval) _timer = 0; // cap

        // Tick existing
        for (int i = _motes.Count - 1; i >= 0; i--)
        {
            var m = _motes[i];
            m.X += m.VX * dt + Drift * MathF.Sin(m.Phase + m.Life * 0.7f) * dt;
            m.Y += m.VY * dt;
            m.VY += Gravity * dt;
            m.Life -= dt;
            if (!m.Alive || m.X < -20 || m.X > screenW + 20 || m.Y < -20 || m.Y > screenH + 20)
                _motes.RemoveAt(i);
            else
                _motes[i] = m;
        }
    }

    private void EmitOne(int w, int h)
    {
        float x, y;
        if (EmitFromSides && _rng.Next(3) == 0)
        {
            x = _rng.Next(2) == 0 ? -5f : w + 5f;
            y = (float)(_rng.NextDouble() * h);
        }
        else if (EmitFromTop && (!EmitFromBottom || _rng.Next(2) == 0))
        {
            x = (float)(_rng.NextDouble() * w);
            y = -5f;
        }
        else
        {
            x = (float)(_rng.NextDouble() * w);
            y = h + 5f;
        }

        float angle = (float)(_rng.NextDouble() * MathF.PI * 2);
        float spd = MinSpeed + (float)_rng.NextDouble() * (MaxSpeed - MinSpeed);
        float vx = MathF.Cos(angle) * spd;
        float vy = MathF.Sin(angle) * spd;
        if (RisingOnly) vy = -MathF.Abs(vy);

        float life = MinLife + (float)_rng.NextDouble() * (MaxLifeVal - MinLife);
        float rad = MinRadius + (float)_rng.NextDouble() * (MaxRadius - MinRadius);
        var col = Palette[_rng.Next(Palette.Length)];
        byte kind = AllowedKinds[_rng.Next(AllowedKinds.Length)];

        _motes.Add(new AmbientMote
        {
            X = x, Y = y, VX = vx, VY = vy,
            Life = life, MaxLife = life, Radius = rad,
            Color = col, Kind = kind,
            Phase = (float)(_rng.NextDouble() * MathF.PI * 2),
        });
    }

    public void Draw(Renderer r)
    {
        foreach (ref readonly var m in System.Runtime.InteropServices.CollectionsMarshal.AsSpan(_motes))
        {
            int a = Math.Clamp((int)(BaseAlpha * m.Alpha01), 0, 255);
            if (a <= 0) continue;
            int ix = (int)m.X, iy = (int)m.Y;
            int ir = Math.Max(1, (int)(m.Radius * (0.5f + 0.5f * m.Alpha01)));

            switch (m.Kind)
            {
                case 0: // circle
                    r.DrawCircle(m.Color, (ix, iy), ir, alpha: a);
                    break;
                case 1: // diamond (4 lines)
                    r.DrawLine(m.Color, (ix, iy - ir), (ix + ir, iy), alpha: a);
                    r.DrawLine(m.Color, (ix + ir, iy), (ix, iy + ir), alpha: a);
                    r.DrawLine(m.Color, (ix, iy + ir), (ix - ir, iy), alpha: a);
                    r.DrawLine(m.Color, (ix - ir, iy), (ix, iy - ir), alpha: a);
                    break;
                case 2: // star-cross
                    r.DrawLine(m.Color, (ix - ir, iy), (ix + ir, iy), alpha: a);
                    r.DrawLine(m.Color, (ix, iy - ir), (ix, iy + ir), alpha: a);
                    break;
                case 3: // horizontal dash
                    r.DrawLine(m.Color, (ix - ir, iy), (ix + ir, iy), alpha: a);
                    break;
            }
        }
    }
}

/// <summary>
/// Slowly drifting light beams that sweep across the background.
/// Creates a subtle god-ray / spotlight effect.
/// </summary>
public class LightBeamSystem
{
    public struct Beam
    {
        public float X, Angle, Width, Speed, Alpha, Life, MaxLife;
        public (int R, int G, int B) Color;
    }

    private readonly List<Beam> _beams = new();
    private readonly Random _rng = new();
    private float _timer;

    public float EmitInterval = 2.5f;
    public int MaxBeams = 4;
    public int BaseAlpha = 12;
    public (int R, int G, int B)[] Palette = { (255, 255, 200) };

    public static LightBeamSystem ForTheme(string theme) => theme switch
    {
        "blackjack" or "texas_holdem" => new LightBeamSystem
        {
            EmitInterval = 3f, MaxBeams = 3, BaseAlpha = 10,
            Palette = new[] { (255, 230, 150), (200, 180, 100) },
        },
        "catan" => new LightBeamSystem
        {
            EmitInterval = 4f, MaxBeams = 2, BaseAlpha = 8,
            Palette = new[] { (255, 240, 180), (220, 200, 140) },
        },
        "cluedo" => new LightBeamSystem
        {
            EmitInterval = 5f, MaxBeams = 2, BaseAlpha = 6,
            Palette = new[] { (180, 160, 220), (140, 120, 200) },
        },
        "monopoly" => new LightBeamSystem
        {
            EmitInterval = 3.5f, MaxBeams = 3, BaseAlpha = 8,
            Palette = new[] { (200, 255, 200), (180, 220, 180) },
        },
        "risk" => new LightBeamSystem
        {
            EmitInterval = 4f, MaxBeams = 2, BaseAlpha = 7,
            Palette = new[] { (200, 180, 160), (180, 160, 140) },
        },
        "dnd" => new LightBeamSystem
        {
            EmitInterval = 2f, MaxBeams = 4, BaseAlpha = 12,
            Palette = new[] { (255, 180, 60), (255, 140, 40), (200, 100, 20) },
        },
        "exploding_kittens" => new LightBeamSystem
        {
            EmitInterval = 2.5f, MaxBeams = 3, BaseAlpha = 10,
            Palette = new[] { (255, 120, 40), (255, 80, 20) },
        },
        "unstable_unicorns" => new LightBeamSystem
        {
            EmitInterval = 2f, MaxBeams = 3, BaseAlpha = 10,
            Palette = new[] { (200, 160, 255), (180, 140, 240), (255, 200, 255) },
        },
        "uno" => new LightBeamSystem
        {
            EmitInterval = 2.5f, MaxBeams = 3, BaseAlpha = 9,
            Palette = new[] { (255, 255, 200), (200, 200, 255) },
        },
        _ => new LightBeamSystem(),
    };

    public void Update(float dt, int screenW, int screenH)
    {
        _timer += dt;
        while (_timer >= EmitInterval && _beams.Count < MaxBeams)
        {
            _timer -= EmitInterval;
            float x = (float)(_rng.NextDouble() * screenW);
            float angle = -0.3f + (float)_rng.NextDouble() * 0.6f; // near vertical
            float w = 40 + (float)_rng.NextDouble() * 80;
            float spd = 15 + (float)_rng.NextDouble() * 25;
            float life = 4f + (float)_rng.NextDouble() * 5f;
            _beams.Add(new Beam
            {
                X = x, Angle = angle, Width = w, Speed = spd,
                Alpha = 0, Life = life, MaxLife = life,
                Color = Palette[_rng.Next(Palette.Length)],
            });
        }
        if (_timer >= EmitInterval) _timer = 0;

        for (int i = _beams.Count - 1; i >= 0; i--)
        {
            var b = _beams[i];
            b.X += b.Speed * dt;
            b.Life -= dt;
            // Fade in first 20%, fade out last 30%
            float p = 1f - b.Life / b.MaxLife; // 0→1 over lifetime
            b.Alpha = p < 0.2f ? p / 0.2f : (p > 0.7f ? (1f - p) / 0.3f : 1f);
            if (b.Life <= 0) _beams.RemoveAt(i);
            else _beams[i] = b;
        }
    }

    public void Draw(Renderer r, int screenW, int screenH)
    {
        foreach (ref readonly var b in System.Runtime.InteropServices.CollectionsMarshal.AsSpan(_beams))
        {
            int a = Math.Clamp((int)(BaseAlpha * b.Alpha), 0, 255);
            if (a <= 0) continue;

            // Draw as a series of translucent vertical strips
            int hw = (int)(b.Width / 2);
            int bx = (int)b.X;
            for (int dx = -hw; dx <= hw; dx += 3)
            {
                float dist = MathF.Abs(dx) / (float)hw;
                int stripA = (int)(a * (1f - dist * dist));
                if (stripA <= 0) continue;
                int sx = bx + dx;
                r.DrawLine(b.Color, (sx, 0), (sx + (int)(b.Angle * screenH), screenH), alpha: stripA);
            }
        }
    }
}

/// <summary>
/// Periodically spawning vignette pulse — a subtle radial darkening/brightening
/// that breathes at the screen edges.
/// </summary>
public class VignettePulse
{
    private float _phase;
    public float Speed = 0.3f;
    public int DarkAlpha = 30;
    public (int R, int G, int B) TintColor = (0, 0, 0);

    public void Update(float dt) => _phase += dt * Speed;

    public void Draw(Renderer r, int w, int h)
    {
        // Breathing alpha at corners
        float breath = 0.6f + 0.4f * MathF.Sin(_phase);
        int a = (int)(DarkAlpha * breath);
        if (a <= 0) return;
        int edgeW = w / 5, edgeH = h / 5;

        // Top/bottom edge darkening
        r.DrawRect(TintColor, (0, 0, w, edgeH), alpha: a);
        r.DrawRect(TintColor, (0, h - edgeH, w, edgeH), alpha: a);
        // Left/right edge darkening (narrower)
        r.DrawRect(TintColor, (0, edgeH, edgeW / 2, h - edgeH * 2), alpha: a * 2 / 3);
        r.DrawRect(TintColor, (w - edgeW / 2, edgeH, edgeW / 2, h - edgeH * 2), alpha: a * 2 / 3);
    }
}

// ═══════════════════════════════════════════════════════════════
// Starfield — twinkling background dots that fade in and out
// ═══════════════════════════════════════════════════════════════

public class Starfield
{
    private struct Star
    {
        public float X, Y, Phase, Speed, Radius;
        public (int R, int G, int B) Color;
    }

    private readonly Star[] _stars;

    public Starfield(int count, int w, int h, (int R, int G, int B)[]? palette = null)
    {
        var rng = new Random(42);
        palette ??= new[] { (255, 255, 255), (200, 220, 255), (255, 230, 200) };
        _stars = new Star[count];
        for (int i = 0; i < count; i++)
        {
            _stars[i] = new Star
            {
                X = rng.Next(w),
                Y = rng.Next(h),
                Phase = (float)(rng.NextDouble() * MathF.Tau),
                Speed = 0.4f + (float)rng.NextDouble() * 1.2f,
                Radius = 1f + (float)rng.NextDouble() * 1.8f,
                Color = palette[rng.Next(palette.Length)],
            };
        }
    }

    public void Update(float dt)
    {
        for (int i = 0; i < _stars.Length; i++)
            _stars[i].Phase += dt * _stars[i].Speed;
    }

    public void Draw(Renderer r)
    {
        for (int i = 0; i < _stars.Length; i++)
        {
            ref readonly var s = ref _stars[i];
            float a01 = 0.3f + 0.7f * (0.5f + 0.5f * MathF.Sin(s.Phase));
            int alpha = (int)(a01 * 120);
            if (alpha < 6) continue;
            r.DrawCircle(s.Color, ((int)s.X, (int)s.Y), (int)s.Radius, alpha: alpha);
        }
    }

    public static Starfield ForTheme(string theme, int w, int h) => theme switch
    {
        "blackjack" or "texas_holdem" => new Starfield(50, w, h, new[] { (255, 215, 0), (255, 255, 200), (200, 200, 255) }),
        "catan" => new Starfield(35, w, h, new[] { (255, 220, 150), (200, 180, 120), (255, 255, 200) }),
        "cluedo" => new Starfield(40, w, h, new[] { (180, 160, 255), (255, 200, 200), (200, 255, 220) }),
        "monopoly" => new Starfield(45, w, h, new[] { (200, 255, 200), (255, 255, 200), (200, 220, 255) }),
        "risk" => new Starfield(55, w, h, new[] { (255, 180, 180), (200, 200, 255), (255, 255, 200) }),
        "dnd" => new Starfield(65, w, h, new[] { (180, 130, 255), (255, 200, 100), (100, 200, 255) }),
        "exploding_kittens" => new Starfield(40, w, h, new[] { (255, 160, 80), (255, 255, 150), (255, 200, 200) }),
        "unstable_unicorns" => new Starfield(55, w, h, new[] { (220, 180, 255), (255, 180, 220), (180, 220, 255) }),
        "uno" => new Starfield(45, w, h, new[] { (255, 80, 80), (80, 180, 255), (80, 255, 80), (255, 255, 80) }),
        _ => new Starfield(40, w, h),
    };
}

// ═══════════════════════════════════════════════════════════════
// FloatingIconSystem — themed text/emoji icons that float upward
// ═══════════════════════════════════════════════════════════════

public class FloatingIconSystem
{
    private struct Icon
    {
        public float X, Y, VY, Life, MaxLife, Phase;
        public int FontSize;
        public string Text;
        public (int R, int G, int B) Color;
    }

    private readonly List<Icon> _icons = new();
    private float _emitTimer;
    private readonly Random _rng = new();

    public float EmitInterval = 2.5f;
    public int MaxIcons = 12;
    public string[] Symbols = { "✦" };
    public (int R, int G, int B)[] Palette = { (255, 255, 255) };
    public float LifeMin = 6f, LifeMax = 10f;
    public float SpeedMin = 12f, SpeedMax = 25f;
    public int FontMin = 10, FontMax = 18;
    public float Drift = 8f;

    public void Update(float dt, int w, int h)
    {
        _emitTimer += dt;
        while (_emitTimer >= EmitInterval && _icons.Count < MaxIcons)
        {
            _emitTimer -= EmitInterval;
            float life = LifeMin + (float)_rng.NextDouble() * (LifeMax - LifeMin);
            _icons.Add(new Icon
            {
                X = _rng.Next(40, w - 40),
                Y = h + 10,
                VY = -(SpeedMin + (float)_rng.NextDouble() * (SpeedMax - SpeedMin)),
                Life = life,
                MaxLife = life,
                Phase = (float)(_rng.NextDouble() * MathF.Tau),
                FontSize = _rng.Next(FontMin, FontMax + 1),
                Text = Symbols[_rng.Next(Symbols.Length)],
                Color = Palette[_rng.Next(Palette.Length)],
            });
        }

        for (int i = _icons.Count - 1; i >= 0; i--)
        {
            var ic = _icons[i];
            ic.Y += ic.VY * dt;
            ic.X += MathF.Sin(ic.Phase + ic.Life * 0.7f) * Drift * dt;
            ic.Life -= dt;
            ic.Phase += dt;
            _icons[i] = ic;
            if (ic.Life <= 0) _icons.RemoveAt(i);
        }
    }

    public void Draw(Renderer r)
    {
        foreach (var ic in _icons)
        {
            float t = ic.Life / ic.MaxLife;
            float fade = t < 0.15f ? t / 0.15f : t > 0.8f ? (1f - t) / 0.2f : 1f;
            int alpha = (int)(fade * 100);
            if (alpha < 4) continue;
            r.DrawText(ic.Text, (int)ic.X, (int)ic.Y, ic.FontSize, ic.Color, alpha: alpha, anchorX: "center", anchorY: "center");
        }
    }

    public static FloatingIconSystem ForTheme(string theme) => theme switch
    {
        "blackjack" or "texas_holdem" => new FloatingIconSystem
        {
            Symbols = new[] { "♠", "♥", "♦", "♣", "🂡" },
            Palette = new[] { (255, 215, 0), (220, 50, 50), (255, 255, 255) },
            EmitInterval = 3f, MaxIcons = 8, Drift = 6f,
        },
        "catan" => new FloatingIconSystem
        {
            Symbols = new[] { "🌾", "🪵", "🧱", "🐑", "⛏" },
            Palette = new[] { (210, 180, 100), (160, 120, 60), (200, 200, 200) },
            EmitInterval = 3.5f, MaxIcons = 8,
        },
        "cluedo" => new FloatingIconSystem
        {
            Symbols = new[] { "🔍", "🕵", "❓", "🗡", "💀" },
            Palette = new[] { (180, 160, 255), (255, 200, 200), (200, 255, 220) },
            EmitInterval = 3.5f, MaxIcons = 7,
        },
        "monopoly" => new FloatingIconSystem
        {
            Symbols = new[] { "💰", "🏠", "🎩", "💵", "🏢" },
            Palette = new[] { (100, 200, 100), (255, 215, 0), (200, 200, 255) },
            EmitInterval = 3f, MaxIcons = 8,
        },
        "risk" => new FloatingIconSystem
        {
            Symbols = new[] { "⚔", "🛡", "🏴", "🌍", "⭐" },
            Palette = new[] { (255, 120, 120), (120, 160, 255), (255, 220, 100) },
            EmitInterval = 2.5f, MaxIcons = 10,
        },
        "dnd" => new FloatingIconSystem
        {
            Symbols = new[] { "⚔", "🐉", "✨", "🏰", "🧙", "💎" },
            Palette = new[] { (180, 130, 255), (255, 200, 100), (100, 200, 255) },
            EmitInterval = 2f, MaxIcons = 12, Drift = 10f,
        },
        "exploding_kittens" => new FloatingIconSystem
        {
            Symbols = new[] { "🐱", "💣", "🙀", "😼", "🔥" },
            Palette = new[] { (255, 160, 80), (255, 80, 60), (255, 255, 150) },
            EmitInterval = 2.5f, MaxIcons = 9,
        },
        "unstable_unicorns" => new FloatingIconSystem
        {
            Symbols = new[] { "🦄", "✨", "🌈", "⭐", "🔮" },
            Palette = new[] { (220, 180, 255), (255, 180, 220), (180, 220, 255) },
            EmitInterval = 2f, MaxIcons = 10, Drift = 12f,
        },
        "uno" => new FloatingIconSystem
        {
            Symbols = new[] { "🔴", "🔵", "🟢", "🟡", "⊘" },
            Palette = new[] { (255, 80, 80), (80, 180, 255), (80, 255, 80), (255, 255, 80) },
            EmitInterval = 2.5f, MaxIcons = 9,
        },
        _ => new FloatingIconSystem(),
    };
}

// ═══════════════════════════════════════════════════════════════
// WaveBand — flowing horizontal colour-wave bands at the bottom
// ═══════════════════════════════════════════════════════════════

public class WaveBand
{
    private float _phase;
    public float Speed = 0.35f;
    public int BandCount = 3;
    public int BandHeight = 6;
    public float Wavelength = 120f;
    public float Amplitude = 8f;
    public int Alpha = 35;
    public (int R, int G, int B)[] Colors = { (100, 150, 255), (80, 200, 180), (150, 120, 255) };

    public void Update(float dt) => _phase += dt * Speed;

    public void Draw(Renderer r, int w, int h)
    {
        int baseY = h - 30;
        for (int band = 0; band < BandCount && band < Colors.Length; band++)
        {
            var c = Colors[band];
            float bandPhase = _phase + band * 1.3f;
            int segW = 4;
            for (int x = 0; x < w; x += segW)
            {
                float wave = MathF.Sin(bandPhase + x / Wavelength * MathF.Tau) * Amplitude;
                int y = baseY - band * (BandHeight + 4) + (int)wave;
                r.DrawRect(c, (x, y, segW, BandHeight), alpha: Alpha);
            }
        }
    }

    public static WaveBand ForTheme(string theme) => theme switch
    {
        "blackjack" or "texas_holdem" => new WaveBand
        {
            Colors = new[] { (0, 80, 0), (0, 100, 20), (0, 60, 0) },
            Alpha = 25, Speed = 0.25f,
        },
        "catan" => new WaveBand
        {
            Colors = new[] { (60, 120, 200), (80, 160, 220), (40, 100, 180) },
            Alpha = 30, Speed = 0.3f, BandCount = 3, Amplitude = 10f,
        },
        "cluedo" => new WaveBand
        {
            Colors = new[] { (100, 60, 120), (80, 50, 100), (120, 80, 140) },
            Alpha = 20, Speed = 0.2f,
        },
        "monopoly" => new WaveBand
        {
            Colors = new[] { (40, 120, 60), (60, 140, 80), (30, 100, 50) },
            Alpha = 25, Speed = 0.3f,
        },
        "risk" => new WaveBand
        {
            Colors = new[] { (140, 60, 60), (100, 80, 160), (160, 140, 60) },
            Alpha = 22, Speed = 0.35f,
        },
        "dnd" => new WaveBand
        {
            Colors = new[] { (100, 60, 180), (60, 40, 140), (140, 80, 200) },
            Alpha = 30, Speed = 0.25f, Amplitude = 12f,
        },
        "exploding_kittens" => new WaveBand
        {
            Colors = new[] { (200, 100, 40), (180, 60, 30), (220, 140, 60) },
            Alpha = 28, Speed = 0.45f, Amplitude = 10f,
        },
        "unstable_unicorns" => new WaveBand
        {
            Colors = new[] { (160, 100, 220), (220, 120, 180), (100, 160, 220) },
            Alpha = 25, Speed = 0.3f, Amplitude = 10f,
        },
        "uno" => new WaveBand
        {
            Colors = new[] { (200, 40, 40), (40, 100, 200), (40, 200, 40) },
            Alpha = 22, Speed = 0.4f,
        },
        _ => new WaveBand(),
    };
}

// ═══════════════════════════════════════════════════════════════
// HeatShimmer — subtle rising heat distortion lines
// ═══════════════════════════════════════════════════════════════

public class HeatShimmer
{
    private float _phase;
    public float Speed = 0.5f;
    public int LineCount = 5;
    public int Alpha = 18;
    public (int R, int G, int B) Color = (255, 255, 255);
    public float Wavelength = 200f;
    public float RiseSpeed = 15f;
    private readonly float[] _offsets;

    public HeatShimmer(int lines = 5)
    {
        LineCount = lines;
        _offsets = new float[lines];
        var rng = new Random(7);
        for (int i = 0; i < lines; i++)
            _offsets[i] = (float)(rng.NextDouble() * MathF.Tau);
    }

    public void Update(float dt)
    {
        _phase += dt * Speed;
        for (int i = 0; i < _offsets.Length; i++)
            _offsets[i] += dt * RiseSpeed * 0.02f;
    }

    public void Draw(Renderer r, int w, int h)
    {
        int spacing = h / (LineCount + 1);
        for (int i = 0; i < LineCount; i++)
        {
            int baseY = spacing * (i + 1) + (int)(MathF.Sin(_offsets[i] * 3f) * 20);
            float linePhase = _phase + _offsets[i];
            int segLen = 6;
            for (int x = 0; x < w; x += segLen)
            {
                float wave = MathF.Sin(linePhase + x / Wavelength * MathF.Tau) * 3f;
                int y1 = baseY + (int)wave;
                int y2 = baseY + (int)(MathF.Sin(linePhase + (x + segLen) / Wavelength * MathF.Tau) * 3f);
                r.DrawLine(Color, (x, y1), (x + segLen, y2), alpha: Alpha);
            }
        }
    }

    public static HeatShimmer ForTheme(string theme) => theme switch
    {
        "blackjack" or "texas_holdem" => new HeatShimmer(4) { Color = (0, 60, 0), Alpha = 14, Speed = 0.3f },
        "catan" => new HeatShimmer(5) { Color = (200, 160, 80), Alpha = 12, Speed = 0.35f },
        "cluedo" => new HeatShimmer(3) { Color = (100, 80, 130), Alpha = 12, Speed = 0.25f },
        "monopoly" => new HeatShimmer(4) { Color = (60, 120, 80), Alpha = 12 },
        "risk" => new HeatShimmer(5) { Color = (160, 120, 80), Alpha = 14, Speed = 0.4f },
        "dnd" => new HeatShimmer(6) { Color = (120, 80, 200), Alpha = 16, Speed = 0.35f },
        "exploding_kittens" => new HeatShimmer(5) { Color = (220, 120, 40), Alpha = 18, Speed = 0.6f },
        "unstable_unicorns" => new HeatShimmer(4) { Color = (180, 140, 255), Alpha = 14, Speed = 0.3f },
        "uno" => new HeatShimmer(4) { Color = (200, 200, 200), Alpha = 12, Speed = 0.4f },
        _ => new HeatShimmer(),
    };
}

// ═══════════════════════════════════════════════════════════════
// ExplosionBurst — dramatic multi-ring explosion (EK card drawn)
// ═══════════════════════════════════════════════════════════════

public class ExplosionBurst
{
    public int X, Y;
    public float Duration, T;
    public bool Done;
    public int MaxRadius;
    public (int R, int G, int B) CoreColor, RingColor, SmokeColor;
    private static readonly Random _rng = new();

    public ExplosionBurst(int x, int y, int maxRadius = 200, float duration = 1.2f)
    {
        X = x; Y = y; MaxRadius = maxRadius; Duration = duration;
        CoreColor = (255, 200, 40);
        RingColor = (255, 80, 20);
        SmokeColor = (60, 40, 30);
    }

    public void Update(float dt) { T = MathF.Min(T + dt, Duration); if (T >= Duration) Done = true; }

    public void Draw(Renderer r)
    {
        if (Done) return;
        float p = T / Duration;

        // Phase 1: bright core flash (0-20%)
        if (p < 0.2f)
        {
            float fp = p / 0.2f;
            int coreR = (int)(MaxRadius * 0.6f * fp);
            int coreA = (int)(200 * (1f - fp));
            r.DrawCircle((255, 255, 200), (X, Y), coreR, alpha: coreA);
            r.DrawCircle(CoreColor, (X, Y), coreR * 2 / 3, alpha: (int)(255 * (1f - fp)));
        }

        // Phase 2: expanding rings (10-80%)
        if (p > 0.1f && p < 0.8f)
        {
            float rp = (p - 0.1f) / 0.7f;
            for (int ring = 0; ring < 4; ring++)
            {
                float rOffset = ring * 0.12f;
                float ringP = MathF.Max(0, rp - rOffset);
                if (ringP <= 0 || ringP > 1) continue;
                int rad = (int)(MaxRadius * ringP);
                int ringA = (int)(120 * (1f - ringP) * (1f - ringP));
                int thickness = Math.Max(2, (int)(8 * (1f - ringP)));
                var col = ring % 2 == 0 ? RingColor : CoreColor;
                r.DrawCircle(col, (X, Y), rad, width: thickness, alpha: ringA);
            }
        }

        // Phase 3: smoke wisps (30-100%)
        if (p > 0.3f)
        {
            float sp = (p - 0.3f) / 0.7f;
            int smokeA = (int)(40 * (1f - sp));
            for (int i = 0; i < 6; i++)
            {
                float angle = i * MathF.PI / 3f + p * 2f;
                float dist = MaxRadius * 0.5f * sp;
                int sx = X + (int)(MathF.Cos(angle) * dist);
                int sy = Y + (int)(MathF.Sin(angle) * dist);
                int sr = (int)(MaxRadius * 0.15f * (1f - sp * 0.5f));
                r.DrawCircle(SmokeColor, (sx, sy), sr, alpha: smokeA);
            }
        }

        // Debris lines radiating outward
        if (p > 0.05f && p < 0.6f)
        {
            float dp = (p - 0.05f) / 0.55f;
            int debrisA = (int)(80 * (1f - dp));
            for (int i = 0; i < 12; i++)
            {
                float angle = i * MathF.PI / 6f + 0.3f;
                float innerDist = MaxRadius * 0.2f * dp;
                float outerDist = MaxRadius * 0.7f * dp;
                int x1 = X + (int)(MathF.Cos(angle) * innerDist);
                int y1 = Y + (int)(MathF.Sin(angle) * innerDist);
                int x2 = X + (int)(MathF.Cos(angle) * outerDist);
                int y2 = Y + (int)(MathF.Sin(angle) * outerDist);
                r.DrawLine(RingColor, (x1, y1), (x2, y2), width: 2, alpha: debrisA);
            }
        }
    }
}

// ═══════════════════════════════════════════════════════════════
// SpotlightCone — directed light cone highlighting active player
// ═══════════════════════════════════════════════════════════════

public class SpotlightCone
{
    private float _phase;
    private float _currentX, _currentY;
    private float _targetX, _targetY;
    private bool _initialized;
    public float Speed = 0.5f;
    public (int R, int G, int B) Color = (255, 200, 80);

    public void Update(float dt)
    {
        _phase += dt * Speed;
        if (_initialized)
        {
            // Smooth exponential lerp for fluid transition
            float t = 1f - MathF.Pow(0.02f, dt); // ~frame-rate independent lerp
            _currentX += (_targetX - _currentX) * t;
            _currentY += (_targetY - _currentY) * t;
        }
    }

    /// <summary>Draw a smooth spotlight glow at (tx,ty).</summary>
    public void DrawAt(Renderer r, int tx, int ty, int w, int h, int radius = 80)
    {
        _targetX = tx; _targetY = ty;
        if (!_initialized) { _currentX = tx; _currentY = ty; _initialized = true; }

        int cx = (int)_currentX, cy = (int)_currentY;
        float breath = 0.85f + 0.15f * MathF.Sin(_phase * 1.4f);

        // Simple layered glow — only 6 circles for performance, no per-pixel beam
        // Each layer is slightly smaller/brighter for a soft radial gradient effect
        int baseA = (int)(10 * breath);
        r.DrawCircle(Color, (cx, cy), (int)(radius * 1.3f), alpha: Math.Max(1, baseA / 2));
        r.DrawCircle(Color, (cx, cy), radius, alpha: baseA);
        r.DrawCircle(Color, (cx, cy), radius * 75 / 100, alpha: (int)(baseA * 1.2f));
        r.DrawCircle(Color, (cx, cy), radius * 50 / 100, alpha: (int)(baseA * 1.4f));
        r.DrawCircle((255, 220, 120), (cx, cy), radius * 30 / 100, alpha: (int)(baseA * 1.0f));
        r.DrawCircle((255, 240, 160), (cx, cy), radius * 15 / 100, alpha: (int)(baseA * 0.7f));

        // Soft vertical beam — only 10-12 horizontal bands total (not per-pixel)
        int beamW = radius / 3;
        int bandCount = Math.Min(12, Math.Max(6, cy / 60));
        for (int i = 0; i < bandCount; i++)
        {
            float t2 = (float)i / bandCount;
            int bandY = (int)(t2 * cy);
            int bandH = Math.Max(4, cy / bandCount);
            float ramp = t2 * t2; // quadratic ramp: faint at top, visible near player
            int bw = (int)(beamW * (0.3f + 0.7f * ramp));
            int ba = (int)(6 * ramp * breath);
            if (ba > 0)
                r.DrawRect(Color, (cx - bw, bandY, bw * 2, bandH), alpha: ba);
        }
    }
}

// ═══════════════════════════════════════════════════════════════
// FireEdge — animated fire licking along screen edges
// ═══════════════════════════════════════════════════════════════

public class FireEdge
{
    private float _phase;
    private readonly Random _rng = new(99);
    public float Speed = 1.5f;
    public int FlameCount = 30;
    public int MaxFlameH = 35;
    public int Alpha = 50;

    public void Update(float dt) => _phase += dt * Speed;

    public void Draw(Renderer r, int w, int h)
    {
        // Bottom edge flames
        for (int i = 0; i < FlameCount; i++)
        {
            float fx = (float)i / FlameCount * w;
            float wave = MathF.Sin(_phase * 3f + i * 0.7f) * 0.5f + 0.5f;
            float wave2 = MathF.Sin(_phase * 4.3f + i * 1.1f) * 0.3f + 0.7f;
            int flameH = (int)(MaxFlameH * wave * wave2);
            if (flameH < 3) continue;

            int flameW = w / FlameCount + 4;
            int flameX = (int)fx - flameW / 2;

            // Multi-layer flame: outer (red) → mid (orange) → core (yellow)
            int outerA = (int)(Alpha * 0.6f * wave);
            int midA = (int)(Alpha * 0.8f * wave);
            int coreA = (int)(Alpha * wave);

            r.DrawRect((180, 30, 10), (flameX, h - flameH, flameW, flameH), alpha: outerA);
            r.DrawRect((240, 100, 10), (flameX + 2, h - flameH * 3 / 4, flameW - 4, flameH * 3 / 4), alpha: midA);
            r.DrawRect((255, 200, 40), (flameX + 4, h - flameH / 2, flameW - 8, flameH / 2), alpha: coreA);
        }

        // Left edge (rotated flames going up-right)
        for (int i = 0; i < FlameCount / 2; i++)
        {
            float fy = (float)i / (FlameCount / 2) * h;
            float wave = MathF.Sin(_phase * 2.5f + i * 0.9f) * 0.5f + 0.5f;
            int flameW2 = (int)(MaxFlameH * 0.6f * wave);
            if (flameW2 < 2) continue;
            int flameH2 = h / (FlameCount / 2) + 2;
            int a2 = (int)(Alpha * 0.4f * wave);
            r.DrawRect((200, 60, 10), (0, (int)fy, flameW2, flameH2), alpha: a2);
            r.DrawRect((255, 140, 20), (0, (int)fy + 1, flameW2 * 2 / 3, flameH2 - 2), alpha: a2);
        }

        // Right edge
        for (int i = 0; i < FlameCount / 2; i++)
        {
            float fy = (float)i / (FlameCount / 2) * h;
            float wave = MathF.Sin(_phase * 2.8f + i * 1.1f + 1f) * 0.5f + 0.5f;
            int flameW2 = (int)(MaxFlameH * 0.6f * wave);
            if (flameW2 < 2) continue;
            int flameH2 = h / (FlameCount / 2) + 2;
            int a2 = (int)(Alpha * 0.4f * wave);
            r.DrawRect((200, 60, 10), (w - flameW2, (int)fy, flameW2, flameH2), alpha: a2);
            r.DrawRect((255, 140, 20), (w - flameW2 * 2 / 3, (int)fy + 1, flameW2 * 2 / 3, flameH2 - 2), alpha: a2);
        }
    }
}

// ═══════════════════════════════════════════════════════════════
// CardBreathEffect — subtle breathing scale on draw pile
// ═══════════════════════════════════════════════════════════════

public class CardBreathEffect
{
    private float _phase;
    public float Speed = 1.2f;
    public float Amplitude = 0.015f; // ±1.5% size change

    public void Update(float dt) => _phase += dt * Speed;

    /// <summary>Returns a multiplier near 1.0 for creating breathing scale.</summary>
    public float Scale => 1f + Amplitude * MathF.Sin(_phase);

    /// <summary>Offset to keep card centred while breathing.</summary>
    public (int dx, int dy) Offset(int w, int h)
    {
        float s = Scale;
        int dw = (int)(w * (s - 1f) * 0.5f);
        int dh = (int)(h * (s - 1f) * 0.5f);
        return (-dw, -dh);
    }
}

// ═══════════════════════════════════════════════════════════════
// GlossyReflection — static helper for drawing a 3D glossy stripe
// ═══════════════════════════════════════════════════════════════

public static class GlossyReflection
{
    /// <summary>Draw a diagonal glossy reflection stripe across a rectangle.</summary>
    public static void Draw(Renderer r, int x, int y, int w, int h, int alpha = 30, float phase = 0f)
    {
        // Diagonal highlight stripe from top-left to ~60% across
        int stripeW = Math.Max(4, w / 4);
        int offset = (int)(phase * w) % (w + stripeW);
        for (int i = 0; i < stripeW; i++)
        {
            float blend = 1f - MathF.Abs(i - stripeW / 2f) / (stripeW / 2f);
            int a = (int)(alpha * blend * blend);
            if (a < 1) continue;
            // Diagonal line from (x+offset+i, y) to (x+offset+i-h/3, y+h)
            int x1 = x + offset + i;
            int x2 = x1 - h / 3;
            r.DrawLine((255, 255, 255), (x1, y), (x2, y + h), alpha: a);
        }
    }
}

// ═══════════════════════════════════════════════════════════════
// BeveledRect — helper for drawing a 3D beveled rectangle
// ═══════════════════════════════════════════════════════════════

public static class BeveledRect
{
    /// <summary>Draw a rectangle with beveled edges giving a 3D raised look.</summary>
    public static void Draw(Renderer r, int x, int y, int w, int h,
        (int R, int G, int B) faceColor, int bevelSize = 3, int alpha = 255)
    {
        // Face
        r.DrawRect(faceColor, (x, y, w, h), alpha: alpha);

        // Top highlight (lighter)
        var hi = (Math.Min(255, faceColor.R + 60), Math.Min(255, faceColor.G + 60), Math.Min(255, faceColor.B + 60));
        r.DrawRect(hi, (x, y, w, bevelSize), alpha: alpha * 70 / 100);
        r.DrawRect(hi, (x, y, bevelSize, h), alpha: alpha * 50 / 100);

        // Bottom/right shadow (darker)
        var sh = (Math.Max(0, faceColor.R - 40), Math.Max(0, faceColor.G - 40), Math.Max(0, faceColor.B - 40));
        r.DrawRect(sh, (x, y + h - bevelSize, w, bevelSize), alpha: alpha * 80 / 100);
        r.DrawRect(sh, (x + w - bevelSize, y, bevelSize, h), alpha: alpha * 60 / 100);

        // Inner highlight line
        r.DrawRect((255, 255, 255), (x + 1, y + 1, w - 2, 1), alpha: alpha * 25 / 100);
    }
}

// ═══════════════════════════════════════════════════════════════
// SoftShadow — multi-layer graduated shadow for 3D depth
// ═══════════════════════════════════════════════════════════════

public static class SoftShadow
{
    /// <summary>Draw a soft multi-layer shadow behind a rectangle.</summary>
    public static void Draw(Renderer r, int x, int y, int w, int h, int layers = 4, int maxAlpha = 80)
    {
        for (int i = layers; i >= 1; i--)
        {
            int offset = i * 2;
            int expand = i;
            int a = maxAlpha * (layers + 1 - i) / (layers + 1);
            r.DrawRect((0, 0, 0), (x + offset - expand, y + offset - expand, w + expand * 2, h + expand * 2), alpha: a);
        }
    }
}
