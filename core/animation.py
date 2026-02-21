"""
Lightweight, frame-driven animation helpers for Pyglet games.
All objects expose:  .update(dt)  .draw(renderer)  .done (bool)
No Pyglet state is stored between frames; everything is re-submitted to the
renderer's batch on each call to .draw().
"""
from __future__ import annotations

import math
import random
import time
from typing import List, Tuple


# ---------------------------------------------------------------------------
# Palette helpers
# ---------------------------------------------------------------------------
_RAINBOW_PALETTE: List[Tuple[int, int, int]] = [
    (255, 60, 120),   # hot pink
    (200, 50, 255),   # violet
    (55, 170, 255),   # sky blue
    (55, 230, 130),   # lime green
    (255, 220, 50),   # gold
    (255, 110, 40),   # orange
]


# ---------------------------------------------------------------------------
# Particle / Firework system
# ---------------------------------------------------------------------------
class _Particle:
    __slots__ = ("x", "y", "vx", "vy", "color", "life", "max_life", "radius", "gravity")

    def __init__(
        self,
        x: float, y: float,
        vx: float, vy: float,
        color: Tuple[int, int, int],
        life: float,
        radius: float = 3.5,
        gravity: float = 340.0,
    ) -> None:
        self.x = x;   self.y = y
        self.vx = vx; self.vy = vy
        self.color = color
        self.life = life; self.max_life = life
        self.radius = radius; self.gravity = gravity

    def update(self, dt: float) -> None:
        self.x  += self.vx * dt
        self.y  += self.vy * dt
        self.vy -= self.gravity * dt          # gravity → lower y
        self.vx *= max(0.0, 1.0 - 1.6 * dt)  # horizontal drag
        self.life -= dt

    @property
    def alive(self) -> bool:
        return self.life > 0.0

    @property
    def alpha(self) -> int:
        return max(0, int(255 * (self.life / self.max_life) ** 0.55))

    @property
    def cur_radius(self) -> int:
        return max(1, int(self.radius * (0.35 + 0.65 * self.life / self.max_life)))


class ParticleSystem:
    """Manages a pool of particles; re-drawn into the batch each frame."""

    def __init__(self) -> None:
        self.particles: List[_Particle] = []

    # ---- emission ----

    def emit(
        self,
        x: float, y: float,
        color: Tuple[int, int, int],
        count: int = 28,
        speed: float = 290.0,
        gravity: float = 370.0,
        life: float = 1.15,
        radius: float = 3.5,
    ) -> None:
        for _ in range(count):
            angle = random.uniform(0.0, math.tau)
            spd = random.uniform(speed * 0.3, speed)
            lt  = random.uniform(life * 0.55, life * 1.1)
            self.particles.append(
                _Particle(x, y, math.cos(angle) * spd, math.sin(angle) * spd,
                          color, lt, radius=radius, gravity=gravity)
            )

    def emit_firework(
        self,
        x: float, y: float,
        colors: List[Tuple[int, int, int]],
        total: int = 80,
    ) -> None:
        """Balanced burst across multiple colours."""
        per = max(1, total // max(1, len(colors)))
        for col in colors:
            self.emit(x, y, col, count=per, speed=330, gravity=260, life=1.55, radius=3.5)

    def emit_sparkle(self, x: float, y: float, color: Tuple[int, int, int], count: int = 12) -> None:
        """Tight sparkle burst (short range, fast fade)."""
        self.emit(x, y, color, count=count, speed=130, gravity=200, life=0.7, radius=2.5)

    # ---- lifecycle ----

    def update(self, dt: float) -> None:
        live: List[_Particle] = []
        for p in self.particles:
            p.update(dt)
            if p.alive:
                live.append(p)
        self.particles = live

    def draw(self, renderer) -> None:
        for p in self.particles:
            renderer.draw_circle(
                p.color, (int(p.x), int(p.y)), p.cur_radius, alpha=p.alpha
            )

    @property
    def empty(self) -> bool:
        return not self.particles


# ---------------------------------------------------------------------------
# Card-fly / flip animation
# ---------------------------------------------------------------------------
class CardFlyAnim:
    """
    A card image that flies from *src* to *dst* with a horizontal squish
    simulating a 3D flip, plus an arc path so it sails through the air.
    """

    def __init__(
        self,
        src: Tuple[int, int],
        dst: Tuple[int, int],
        card_w: int = 90,
        card_h: int = 122,
        color: Tuple[int, int, int] = (160, 80, 200),
        duration: float = 0.52,
    ) -> None:
        self.src = src
        self.dst = dst
        self.card_w = card_w
        self.card_h = card_h
        self.color = color
        self.duration = float(duration)
        self.t = 0.0
        self.done = False

    def update(self, dt: float) -> None:
        self.t = min(self.t + dt, self.duration)
        if self.t >= self.duration:
            self.done = True

    def draw(self, renderer) -> None:
        p = self.t / self.duration
        # Ease-out cubic interpolation along the path
        ep = 1.0 - (1.0 - p) ** 3
        cx = self.src[0] + (self.dst[0] - self.src[0]) * ep
        cy = self.src[1] + (self.dst[1] - self.src[1]) * ep
        # Parabolic arc: card rises then falls
        cy -= math.sin(math.pi * p) * 70

        # Horizontal squish: cos(π·p) gives 1 → -1 → 1;  abs → 1 → 0 → 1
        sx = abs(math.cos(math.pi * p * 1.1))
        dw = max(4, int(self.card_w * sx))
        dh = self.card_h
        dx = int(cx - dw / 2)
        dy = int(cy - dh / 2)

        # Colour: front face = card colour, back face (mid-flip) = lighter
        if p < 0.48:
            border = self.color
            tint_alpha = 60
        else:
            border = tuple(min(255, int(c * 1.5)) for c in self.color)  # type: ignore[assignment]
            tint_alpha = 90

        # Trail glow while in flight
        if 0.05 < p < 0.92:
            trail_a = int(28 * math.sin(math.pi * p))
            renderer.draw_circle(self.color, (int(cx), int(cy)), max(8, int(self.card_w * 0.35)), alpha=trail_a)
        # Shadow
        renderer.draw_rect((0, 0, 0), (dx + 4, dy + 4, dw, dh), alpha=50)
        # Card body
        renderer.draw_rect((250, 250, 250), (dx, dy, dw, dh), alpha=225)
        renderer.draw_rect(self.color, (dx, dy, dw, dh), alpha=tint_alpha)
        # Top highlight
        if dw > 10:
            renderer.draw_rect((255, 255, 255), (dx + 2, dy + 2, dw - 4, 5), alpha=80)
        renderer.draw_rect(border, (dx, dy, dw, dh), width=3, alpha=245)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# In-place card flip
# ---------------------------------------------------------------------------
class CardFlipInPlace:
    """
    A card that flips in place, scaling horizontally through zero
    to simulate a 3D card-turn.  Draws a 'back' colour for the first
    half and a 'front' colour for the second.
    """

    def __init__(
        self,
        x: int, y: int,
        card_w: int = 90,
        card_h: int = 122,
        back_color: Tuple[int, int, int] = (60, 60, 130),
        front_color: Tuple[int, int, int] = (250, 250, 255),
        duration: float = 0.48,
    ) -> None:
        self.x = x; self.y = y
        self.card_w = card_w; self.card_h = card_h
        self.back_color = back_color
        self.front_color = front_color
        self.duration = float(duration)
        self.t = 0.0
        self.done = False

    def update(self, dt: float) -> None:
        self.t = min(self.t + dt, self.duration)
        if self.t >= self.duration:
            self.done = True

    def draw(self, renderer) -> None:
        p = self.t / self.duration
        sx = abs(math.cos(math.pi * p))
        dw = max(2, int(self.card_w * sx))
        dh = self.card_h
        dx = int(self.x - dw / 2)
        dy = int(self.y - dh / 2)

        is_front = p >= 0.5
        col = self.front_color if is_front else self.back_color

        # Shadow
        renderer.draw_rect((0, 0, 0), (dx + 3, dy + 3, dw, dh), alpha=55)
        # Card body
        renderer.draw_rect(col, (dx, dy, dw, dh), alpha=235)
        # Border
        renderer.draw_rect((70, 70, 80), (dx, dy, dw, dh), width=2, alpha=200)
        # Front highlight
        if is_front and dw > 10:
            renderer.draw_rect((255, 255, 255), (dx + 2, dy + 2, dw - 4, 5), alpha=100)


# ---------------------------------------------------------------------------
# Text pop-in / fade-out
# ---------------------------------------------------------------------------
class TextPopAnim:
    """
    A word or phrase that scales in from nothing, wobbles slightly while
    visible, then fades out.  Shadow drawn automatically for readability.
    """

    def __init__(
        self,
        text: str,
        x: int, y: int,
        color: Tuple[int, int, int] = (255, 230, 50),
        font_size: int = 42,
        duration: float = 2.0,
    ) -> None:
        self.text = text
        self.x = x; self.y = y
        self.color = color
        self.font_size = font_size
        self.duration = float(duration)
        self.t = 0.0
        self.done = False

    def update(self, dt: float) -> None:
        self.t = min(self.t + dt, self.duration)
        if self.t >= self.duration:
            self.done = True

    def draw(self, renderer) -> None:
        p = self.t / self.duration
        if p < 0.13:                        # scale in
            scale = p / 0.13
            alpha = 255
        elif p < 0.72:                      # hold + wobble
            scale = 1.0 + 0.06 * math.sin(math.pi * (p - 0.13) / 0.59 * 2)
            alpha = 255
        else:                               # fade out
            scale = 1.0
            alpha = int(255 * (1.0 - (p - 0.72) / 0.28))

        fs = max(8, int(self.font_size * scale))
        if alpha <= 0 or fs <= 0:
            return
        # Drop shadow
        renderer.draw_text(
            self.text, self.x + 3, self.y + 3,
            font_size=fs, color=(0, 0, 0), alpha=min(150, alpha),
            anchor_x="center", anchor_y="center",
        )
        # Main text
        renderer.draw_text(
            self.text, self.x, self.y,
            font_size=fs, color=self.color, alpha=alpha,
            anchor_x="center", anchor_y="center",
        )


# ---------------------------------------------------------------------------
# Expanding pulse ring
# ---------------------------------------------------------------------------
class PulseRing:
    """
    A ring that expands outward from a point and fades — like a sonar ping
    or a magical shockwave.  Multiple concentric arcs create apparent width.
    """

    def __init__(
        self,
        x: int, y: int,
        color: Tuple[int, int, int],
        max_radius: int = 110,
        duration: float = 0.72,
    ) -> None:
        self.x = x; self.y = y
        self.color = color
        self.max_radius = max_radius
        self.duration = float(duration)
        self.t = 0.0
        self.done = False

    def update(self, dt: float) -> None:
        self.t = min(self.t + dt, self.duration)
        if self.t >= self.duration:
            self.done = True

    def draw(self, renderer) -> None:
        p = self.t / self.duration
        r = max(3, int(self.max_radius * p))
        alpha = int(210 * (1.0 - p) ** 0.7)
        if alpha <= 0:
            return
        # Draw 5 concentric arcs to simulate ~4 px line width
        for dr in (-4, -2, 0, 2, 4):
            rr = r + dr
            if rr > 0:
                renderer.draw_circle(self.color, (self.x, self.y), rr, width=1, alpha=alpha)


# ---------------------------------------------------------------------------
# Full-screen flash overlay
# ---------------------------------------------------------------------------
class ScreenFlash:
    """
    A coloured overlay that fades to transparent, giving a 'hit flash'
    or winner glow effect.
    """

    def __init__(
        self,
        color: Tuple[int, int, int] = (255, 255, 255),
        peak_alpha: int = 120,
        duration: float = 0.38,
    ) -> None:
        self.color = color
        self.peak_alpha = peak_alpha
        self.duration = float(duration)
        self.t = 0.0
        self.done = False

    def update(self, dt: float) -> None:
        self.t = min(self.t + dt, self.duration)
        if self.t >= self.duration:
            self.done = True

    def draw(self, renderer, w: int, h: int) -> None:
        p = self.t / self.duration
        alpha = int(self.peak_alpha * (1.0 - p) ** 1.4)
        if alpha > 0:
            renderer.draw_rect(self.color, (0, 0, w, h), alpha=alpha)


# ---------------------------------------------------------------------------
# Shared die-pip renderer
# ---------------------------------------------------------------------------
def _draw_die_pips(renderer, cx: int, cy: int, size: int, value: int) -> None:
    """Draw standard die face pips with subtle 3D shadow/highlight."""
    r = max(3, size // 9)
    off = size // 4
    _PM = {
        1: [(0, 0)],
        2: [(-off, -off), (off, off)],
        3: [(-off, -off), (0, 0), (off, off)],
        4: [(-off, -off), (off, -off), (-off, off), (off, off)],
        5: [(-off, -off), (off, -off), (0, 0), (-off, off), (off, off)],
        6: [(-off, -off), (off, -off), (-off, 0), (off, 0), (-off, off), (off, off)],
    }
    for dx, dy in _PM.get(int(value), []):
        px, py = int(cx + dx), int(cy + dy)
        renderer.draw_circle((0, 0, 0), (px + 1, py + 1), r, alpha=45)
        renderer.draw_circle((15, 15, 22), (px, py), r, alpha=245)
        renderer.draw_circle((55, 55, 65), (px - 1, py - 1), max(1, r - 2), alpha=70)


# ---------------------------------------------------------------------------
# Animated dice roller
# ---------------------------------------------------------------------------
class DiceRollAnimation:
    """
    Time-based animated dice roller with stylish 3D rendering.
    No update() call needed -- uses wall-clock time internally.

    Usage::

        anim = DiceRollAnimation(die_size=64)
        anim.start([4, 2])            # begin rolling, final values 4 & 2
        # each frame:
        anim.draw(renderer, cx, cy)   # handles jitter / glow automatically
        if anim.just_resolved:        # one-shot after dice settle
            ...                       # apply game logic
    """

    def __init__(
        self,
        die_size: int = 68,
        gap: int = 20,
        duration: float = 1.2,
        show_duration: float = 3.0,
        accent: Tuple[int, int, int] = (255, 215, 0),
    ) -> None:
        self.die_size = die_size
        self.gap = gap
        self.duration = duration
        self.show_duration = show_duration
        self.accent = accent
        self.final_values: List[int] = []
        self._start: float = 0.0
        self._active: bool = False
        self._seed: float = 0.0

    @property
    def rolling(self) -> bool:
        return self._active and (time.time() - self._start) < self.duration

    @property
    def visible(self) -> bool:
        return self._active and (time.time() - self._start) < (self.duration + self.show_duration)

    @property
    def just_resolved(self) -> bool:
        if not self._active:
            return False
        e = time.time() - self._start
        return self.duration <= e < self.duration + 0.4

    def start(self, final_values: List[int]) -> None:
        self.final_values = list(final_values)
        self._start = time.time()
        self._active = True
        self._seed = random.random() * 100

    def hide(self) -> None:
        self._active = False

    def draw(self, renderer, cx: int, cy: int, *, total_text: str = "") -> None:
        if not self.visible or not self.final_values:
            return
        now = time.time()
        elapsed = now - self._start
        is_rolling = elapsed < self.duration
        glow = max(0.0, 1.0 - (elapsed - self.duration) / 0.55) if elapsed >= self.duration else 0.0

        n = len(self.final_values)
        ds = self.die_size
        tw = n * ds + (n - 1) * self.gap
        sx = cx - tw // 2

        for i in range(n):
            jx, jy, bounce = 0, 0, 0
            if is_rolling:
                ph = elapsed * 34 + i * 2.3 + self._seed
                jx = int(6 * math.sin(ph))
                jy = int(5 * math.cos(ph * 1.35 + 0.8))
            if 0.25 < glow <= 1.0:
                bounce = int(10 * math.sin(math.pi * (glow - 0.25) / 0.75))

            dcx = sx + i * (ds + self.gap) + ds // 2 + jx
            dcy = cy + jy - bounce
            hx = dcx - ds // 2
            hy = dcy - ds // 2
            val = random.randint(1, 6) if is_rolling else self.final_values[i]

            renderer.draw_rect((0, 0, 0), (hx + 6, hy + 6, ds, ds), alpha=45)
            renderer.draw_rect((0, 0, 0), (hx + 3, hy + 3, ds, ds), alpha=70)
            renderer.draw_rect((250, 250, 255), (hx, hy, ds, ds), alpha=255)
            renderer.draw_rect((210, 210, 220), (hx + 2, hy + ds * 2 // 3, ds - 4, ds // 3 - 2), alpha=35)
            renderer.draw_rect((255, 255, 255), (hx + 3, hy + 2, ds - 6, 7), alpha=140)
            renderer.draw_rect((40, 40, 48), (hx, hy, ds, ds), width=2, alpha=230)
            renderer.draw_rect((180, 180, 195), (hx + 4, hy + 4, ds - 8, ds - 8), width=1, alpha=55)
            if glow > 0:
                ga = int(90 * glow)
                renderer.draw_rect(self.accent, (hx - 4, hy - 4, ds + 8, ds + 8), width=3, alpha=ga)
            _draw_die_pips(renderer, dcx, dcy, ds, val)

        if total_text and not is_rolling:
            tx = cx + tw // 2 + 16
            renderer.draw_text(total_text, tx + 2, cy + 2, font_size=20,
                               color=(0, 0, 0), alpha=140,
                               anchor_x="left", anchor_y="center", bold=True)
            renderer.draw_text(total_text, tx, cy, font_size=20,
                               color=(255, 235, 80), alpha=255,
                               anchor_x="left", anchor_y="center", bold=True)


# ---------------------------------------------------------------------------
# Rainbow title helper
# ---------------------------------------------------------------------------
_TITLE_RAINBOW: List[Tuple[int, int, int]] = [
    (255, 55, 55), (255, 140, 0), (255, 220, 0),
    (55, 200, 55), (70, 130, 255), (200, 55, 255),
]


def draw_rainbow_title(
    renderer,
    title: str,
    w: int,
    y: int = 12,
    font_size: int = 22,
    char_width: int = 16,
) -> None:
    """Draw a title centred horizontally with each character in a cycling rainbow colour."""
    try:
        tx = w // 2 - (len(title) * char_width) // 2
        for i, ch in enumerate(title):
            col = _TITLE_RAINBOW[i % len(_TITLE_RAINBOW)]
            renderer.draw_text(
                ch, tx + i * char_width, y,
                font_size=font_size, color=col, bold=True,
                anchor_x="left", anchor_y="top",
            )
    except Exception:
        pass
