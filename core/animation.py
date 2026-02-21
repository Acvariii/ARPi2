"""
Lightweight, frame-driven animation helpers for Pyglet games.
All objects expose:  .update(dt)  .draw(renderer)  .done (bool)
No Pyglet state is stored between frames; everything is re-submitted to the
renderer's batch on each call to .draw().
"""
from __future__ import annotations

import math
import random
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

        renderer.draw_rect((250, 250, 250), (dx, dy, dw, dh), alpha=225)
        renderer.draw_rect(self.color, (dx, dy, dw, dh), alpha=tint_alpha)
        renderer.draw_rect(border, (dx, dy, dw, dh), width=3, alpha=245)  # type: ignore[arg-type]


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
