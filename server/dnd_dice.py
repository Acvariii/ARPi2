from __future__ import annotations

import math
import time
from typing import List, Optional

from config import WINDOW_SIZE
from core.renderer import PygletRenderer


class CenterDiceRollDisplay:
    """Visible centered dice roll animation (2D polygons)."""

    _DICE_POLY_SIDES = {
        4: 3,  # triangle (d4)
        6: 4,  # square
        8: 8,  # octagon
        10: 10,  # decagon
        12: 12,  # dodecagon
        20: 20,  # icosagon-ish
    }

    def __init__(self):
        self._queue: List[dict] = []
        self._active: Optional[dict] = None

    def clear(self) -> None:
        self._queue.clear()
        self._active = None

    def enqueue(self, label: str, sides: int, result: int, color: tuple[int, int, int]) -> None:
        try:
            s = int(sides)
            r = int(result)
        except Exception:
            return
        if s not in self._DICE_POLY_SIDES:
            return
        r = max(1, min(s, r))
        self._queue.append(
            {
                "label": str(label or ""),
                "sides": s,
                "result": r,
                "color": tuple(int(c) for c in color),
            }
        )

    def update(self, dt: float) -> None:
        now = float(time.time())
        if self._active is None:
            if not self._queue:
                return
            item = self._queue.pop(0)
            item["start"] = now
            # Total animation duration, with most time in "rolling".
            item["duration"] = 1.8
            item["roll_phase"] = 1.15
            item["tick"] = 0.075
            self._active = item
            return

        start = float(self._active.get("start", now))
        dur = float(self._active.get("duration", 1.8))
        if now - start >= dur:
            self._active = None

    def _regular_polygon(self, cx: float, cy: float, radius: float, n: int, angle: float) -> List[tuple[int, int]]:
        pts: List[tuple[int, int]] = []
        for i in range(n):
            a = angle + (2.0 * math.pi * i / n)
            x = cx + radius * math.cos(a)
            y = cy + radius * math.sin(a)
            pts.append((int(x), int(y)))
        return pts

    def draw(self, renderer: PygletRenderer) -> None:
        active = self._active
        if not active:
            return

        w = int(getattr(renderer, "width", WINDOW_SIZE[0]))
        h = int(getattr(renderer, "height", WINDOW_SIZE[1]))
        cx = int(w // 2)
        cy = int(h // 2)

        now = float(time.time())
        start = float(active.get("start", now))
        elapsed = max(0.0, now - start)
        duration = float(active.get("duration", 1.8))
        roll_phase = float(active.get("roll_phase", 1.15))
        tick = float(active.get("tick", 0.075))

        sides = int(active["sides"])
        result = int(active["result"])
        color = tuple(active.get("color") or (220, 220, 220))
        label = str(active.get("label") or "")

        # While rolling, flip the shown face rapidly; then settle.
        if elapsed < roll_phase:
            step = int(elapsed / max(0.01, tick))
            shown = (step % sides) + 1
        else:
            shown = result

        # Simple bounce + slow rotate.
        t = min(1.0, elapsed / max(0.001, duration))
        scale = 1.0 + 0.18 * math.sin(math.pi * min(1.0, t))
        angle = (elapsed * 1.6) % (2.0 * math.pi)

        base_r = int(min(w, h) * 0.12)
        radius = max(46, int(base_r * scale))

        poly_n = self._DICE_POLY_SIDES.get(sides, 6)
        pts = self._regular_polygon(cx, cy, radius, poly_n, angle)
        shadow_pts = [(x + 5, y + 5) for (x, y) in pts]

        # Shadow + dice body (use shapes-based drawing so it works on core OpenGL).
        try:
            renderer.draw_polygon_immediate((0, 0, 0), shadow_pts, alpha=110)
        except Exception:
            pass

        # Dice body
        try:
            renderer.draw_polygon_immediate(color, pts, alpha=235)
        except Exception:
            pass

        # Subtle highlight to feel more "physical"
        try:
            hi = tuple(min(255, int(c + (255 - c) * 0.35)) for c in color)
            inner = self._regular_polygon(cx - radius * 0.10, cy + radius * 0.10, radius * 0.72, poly_n, angle)
            renderer.draw_polygon_immediate(hi, inner, alpha=170)
        except Exception:
            pass

        # Outline
        try:
            renderer.draw_polyline_immediate((20, 20, 20), pts, width=4, alpha=220, closed=True)
        except Exception:
            pass

        # Number + labels (immediate so it appears above everything).
        try:
            renderer.draw_text_immediate(
                str(shown),
                cx,
                cy + 4,
                font_size=max(44, int(radius * 0.85)),
                color=(245, 245, 245),
                bold=True,
                anchor_x="center",
                anchor_y="center",
                alpha=255,
            )
            renderer.draw_text_immediate(
                f"d{sides}",
                cx,
                cy + radius + 18,
                font_size=22,
                color=(235, 235, 235),
                anchor_x="center",
                anchor_y="center",
                alpha=230,
            )
            if label:
                renderer.draw_text_immediate(
                    label,
                    cx,
                    cy - radius - 18,
                    font_size=18,
                    color=(235, 235, 235),
                    anchor_x="center",
                    anchor_y="center",
                    alpha=220,
                )
        except Exception:
            pass
