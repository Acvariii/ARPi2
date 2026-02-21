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
        int tx = w / 2 - title.Length * charWidth / 2;
        for (int i = 0; i < title.Length; i++)
        {
            var col = AnimPalette.TitleRainbow[i % AnimPalette.TitleRainbow.Length];
            r.DrawText(title[i].ToString(), tx + i * charWidth, y, fontSize: fontSize,
                       color: col, bold: true, anchorX: "left", anchorY: "top");
        }
    }
}
