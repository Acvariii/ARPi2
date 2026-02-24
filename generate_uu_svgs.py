#!/usr/bin/env python3
"""Generate detailed SVG card illustrations for Unstable Unicorns.

Each SVG uses a 512x512 viewBox with transparent background.
Cards are composed from overlapping shapes, gradients, and per-card extras.
"""

import os, math, random

OUT_DIR = os.path.join(os.path.dirname(__file__),
    "ARPi2.Sharp", "ARPi2.Sharp", "Content", "uu_cards")
os.makedirs(OUT_DIR, exist_ok=True)


# ═══════════════════════════════════════════════════════════════
#  Color utilities
# ═══════════════════════════════════════════════════════════════

def hex2rgb(h):
    h = h.lstrip('#')
    return (int(h[0:2],16), int(h[2:4],16), int(h[4:6],16))

def rgb2hex(r,g,b):
    return f"#{max(0,min(255,int(r))):02x}{max(0,min(255,int(g))):02x}{max(0,min(255,int(b))):02x}"

def darken(c, f=0.7):
    r,g,b = hex2rgb(c)
    return rgb2hex(r*f, g*f, b*f)

def lighten(c, f=0.3):
    r,g,b = hex2rgb(c)
    return rgb2hex(r+(255-r)*f, g+(255-g)*f, b+(255-b)*f)

def blend(c1, c2, t=0.5):
    r1,g1,b1 = hex2rgb(c1)
    r2,g2,b2 = hex2rgb(c2)
    return rgb2hex(r1+(r2-r1)*t, g1+(g2-g1)*t, b1+(b2-b1)*t)


# ═══════════════════════════════════════════════════════════════
#  SVG Document Builder
# ═══════════════════════════════════════════════════════════════

class S:
    """SVG document builder."""
    def __init__(self, w=512, h=512):
        self.w, self.h = w, h
        self.defs = []
        self.els = []
        self._nid = 0

    def _id(self, p="e"):
        self._nid += 1
        return f"{p}{self._nid}"

    def lg(self, x1, y1, x2, y2, stops):
        """Linear gradient. stops = [(offset, color, opacity), ...]"""
        gid = self._id("lg")
        s = f'<linearGradient id="{gid}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" gradientUnits="userSpaceOnUse">\n'
        for o, c, a in stops:
            s += f'  <stop offset="{o}" stop-color="{c}" stop-opacity="{a}"/>\n'
        s += '</linearGradient>'
        self.defs.append(s)
        return gid

    def rg(self, cx, cy, r, stops, fx=None, fy=None):
        """Radial gradient."""
        gid = self._id("rg")
        fxa = f' fx="{fx}" fy="{fy}"' if fx is not None else ''
        s = f'<radialGradient id="{gid}" cx="{cx}" cy="{cy}" r="{r}"{fxa} gradientUnits="userSpaceOnUse">\n'
        for o, c, a in stops:
            s += f'  <stop offset="{o}" stop-color="{c}" stop-opacity="{a}"/>\n'
        s += '</radialGradient>'
        self.defs.append(s)
        return gid

    def fb(self, sd=3):
        """Blur filter."""
        fid = self._id("fb")
        self.defs.append(f'<filter id="{fid}"><feGaussianBlur stdDeviation="{sd}"/></filter>')
        return fid

    def fs(self, dx=2, dy=3, sd=3, op=0.3):
        """Drop shadow filter."""
        fid = self._id("fs")
        self.defs.append(f'<filter id="{fid}"><feDropShadow dx="{dx}" dy="{dy}" stdDeviation="{sd}" flood-opacity="{op}"/></filter>')
        return fid

    def cp(self, d):
        """Clip path from path data."""
        cid = self._id("cp")
        self.defs.append(f'<clipPath id="{cid}"><path d="{d}"/></clipPath>')
        return cid

    def _attrs(self, fill='none', stroke='none', sw=0, op=1, filt=None, clip=None, tx=''):
        a = ''
        a += f' fill="{fill}"'
        if stroke != 'none':
            a += f' stroke="{stroke}" stroke-width="{sw}"'
            a += ' stroke-linecap="round" stroke-linejoin="round"'
        if op < 1: a += f' opacity="{op:.2f}"'
        if filt: a += f' filter="url(#{filt})"'
        if clip: a += f' clip-path="url(#{clip})"'
        if tx: a += f' transform="{tx}"'
        return a

    def el(self, cx, cy, rx, ry, **kw):
        self.els.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}"{self._attrs(**kw)}/>')

    def ci(self, cx, cy, r, **kw):
        self.els.append(f'<circle cx="{cx}" cy="{cy}" r="{r}"{self._attrs(**kw)}/>')

    def pa(self, d, **kw):
        self.els.append(f'<path d="{d}"{self._attrs(**kw)}/>')

    def re(self, x, y, w, h, rx=0, **kw):
        rxs = f' rx="{rx}"' if rx else ''
        self.els.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}"{rxs}{self._attrs(**kw)}/>')

    def tx(self, x, y, text, fill='#000', fs=20, fw='normal', anchor='middle'):
        self.els.append(f'<text x="{x}" y="{y}" fill="{fill}" font-size="{fs}" font-weight="{fw}" text-anchor="{anchor}" font-family="Arial,sans-serif">{text}</text>')

    def gs(self, op=1, tx='', filt=None):
        a = ''
        if op < 1: a += f' opacity="{op:.2f}"'
        if tx: a += f' transform="{tx}"'
        if filt: a += f' filter="url(#{filt})"'
        self.els.append(f'<g{a}>')

    def ge(self):
        self.els.append('</g>')

    def render(self):
        lines = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}">']
        if self.defs:
            lines.append('<defs>')
            lines.extend(self.defs)
            lines.append('</defs>')
        lines.extend(self.els)
        lines.append('</svg>')
        return '\n'.join(lines)

    def save(self, name):
        path = os.path.join(OUT_DIR, name)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(self.render())
        print(f"  wrote {name} ({len(self.els)} elements, {len(self.defs)} defs)")


# ═══════════════════════════════════════════════════════════════
#  Base Unicorn Body
# ═══════════════════════════════════════════════════════════════

def unicorn_body(sv, p, include_horn=True, include_tail=True, include_mane=True):
    """Draw a detailed standing unicorn facing left in 512x512."""
    bd = p['body']
    bdk = darken(bd, 0.60)
    blt = lighten(bd, 0.35)
    bvl = lighten(bd, 0.55)
    mn = p.get('mane', '#8866bb')
    mndk = darken(mn, 0.55)
    mnlt = lighten(mn, 0.40)
    tl = p.get('tail', mn)
    tldk = darken(tl, 0.55)
    tllt = lighten(tl, 0.40)
    hr = p.get('horn', '#ffd700')
    hrdk = darken(hr, 0.45)
    hrlt = lighten(hr, 0.30)
    hf = p.get('hoof', '#2a2a2a')
    hflt = lighten(hf, 0.30)
    ey = p.get('eye', '#3344aa')
    ns = p.get('nose', darken(bd, 0.35))
    ck = p.get('cheek', '#ffb6c1')

    blur = sv.fb(6)
    sblur = sv.fb(3)

    # ── Ground shadow ──
    sv.el(270, 462, 140, 18, fill='#000000', op=0.13, filt=blur)

    # ── TAIL (behind body) ──
    if include_tail:
        tg1 = sv.lg(388, 220, 470, 400, [(0, tllt, 1), (0.4, tl, 1), (1, tldk, 0.9)])
        # Main tail flow — 5 overlapping strands
        tail_strands = [
            "M388,248 C418,225 465,248 458,310 C452,360 432,400 412,418 C402,405 425,350 430,305 C435,260 400,250 388,248Z",
            "M393,255 C428,238 472,268 465,325 C458,370 442,405 428,420 C418,405 440,358 442,318 C445,275 410,260 393,255Z",
            "M390,250 C415,232 455,248 450,298 C446,340 428,378 410,405 C400,390 420,342 425,300 C430,258 402,248 390,250Z",
            "M395,258 C430,245 468,275 460,330 C454,372 438,408 422,422 C414,408 436,365 438,325 C441,280 408,263 395,258Z",
            "M391,253 C420,237 458,255 452,308 C448,350 430,390 415,412 C406,398 426,352 428,310 C432,265 404,252 391,253Z",
        ]
        for i, td in enumerate(tail_strands):
            c = [tldk, tl, tllt, tl, mnlt][i % 5]
            o = [0.7, 0.8, 0.5, 0.6, 0.4][i % 5]
            sv.pa(td, fill=c, op=o)
        # Tail highlight lines
        for i in range(6):
            t = i / 5
            sx = 395 + t * 30
            sy = 255 + t * 5
            ex = 415 + t * 15
            ey2 = 410 + t * 10
            cx = sx + 40
            cy = (sy + ey2) / 2 - 20
            sv.pa(f"M{sx:.0f},{sy:.0f} Q{cx:.0f},{cy:.0f} {ex:.0f},{ey2:.0f}",
                   fill='none', stroke=tllt, sw=0.8, op=0.3)

    # ── BACK LEGS (far, behind body) ──
    # Far back leg
    blg1 = sv.lg(328, 310, 355, 455, [(0, bdk, 1), (0.5, darken(bd, 0.75), 1), (1, bdk, 1)])
    sv.pa("M338,312 C342,335 345,370 347,400 C349,422 346,438 340,448 L328,448 "
          "C330,438 334,422 333,400 C330,370 326,335 323,312Z", fill=f'url(#{blg1})')
    # Back leg muscle detail
    sv.pa("M330,325 C335,340 336,355 335,370", fill='none', stroke=blt, sw=1, op=0.2)
    sv.el(334, 448, 13, 7, fill=hf)
    sv.el(333, 446, 8, 3, fill=hflt, op=0.3)

    # Far front leg
    flg1 = sv.lg(200, 318, 222, 455, [(0, bdk, 1), (0.5, darken(bd, 0.75), 1), (1, bdk, 1)])
    sv.pa("M213,318 C216,342 218,378 216,408 C214,428 210,442 205,452 L193,452 "
          "C196,442 200,428 201,408 C203,378 201,342 198,318Z", fill=f'url(#{flg1})')
    sv.el(199, 452, 13, 7, fill=hf)
    sv.el(198, 450, 8, 3, fill=hflt, op=0.3)

    # ── TORSO ──
    bg = sv.rg(275, 278, 135, [(0, blt, 1), (0.45, bd, 1), (1, bdk, 1)], fx=255, fy=255)
    torso = ("M198,248 C215,222 265,210 320,215 C360,218 390,235 402,258 "
             "C415,282 410,310 395,330 C375,352 335,360 290,358 "
             "C245,356 210,345 195,330 C178,312 180,275 198,248Z")
    sv.pa(torso, fill=f'url(#{bg})')

    # Belly highlight
    belly = sv.rg(280, 335, 70, [(0, bvl, 0.45), (1, bvl, 0)])
    sv.el(280, 332, 65, 22, fill=f'url(#{belly})')

    # Spine shadow
    sv.pa("M218,242 C258,226 320,218 370,230 C385,234 396,244 402,255",
          fill='none', stroke=bdk, sw=2.5, op=0.25)

    # Chest highlight
    cst = sv.rg(208, 265, 45, [(0, blt, 0.5), (1, blt, 0)])
    sv.el(208, 265, 38, 42, fill=f'url(#{cst})')

    # Rib/muscle suggestion
    for i in range(3):
        x = 255 + i * 35
        sv.pa(f"M{x},268 C{x+8},285 {x+5},310 {x-2},330",
              fill='none', stroke=bdk, sw=0.8, op=0.12)

    # ── NEAR BACK LEG ──
    blg2 = sv.lg(345, 310, 375, 455, [(0, bd, 1), (0.45, bdk, 1), (1, darken(bd, 0.70), 1)])
    sv.pa("M355,312 C360,335 365,370 367,402 C369,425 365,440 358,450 L345,450 "
          "C348,440 352,425 351,402 C348,370 343,335 340,312Z", fill=f'url(#{blg2})')
    # Knee detail
    sv.el(352, 372, 7, 12, fill=blt, op=0.2)
    sv.el(352, 450, 14, 8, fill=hf)
    sv.el(350, 448, 9, 4, fill=hflt, op=0.35)
    # Hoof detail — small groove
    sv.pa("M345,448 L358,448", fill='none', stroke=darken(hf, 0.5), sw=0.8, op=0.4)

    # ── NEAR FRONT LEG ──
    flg2 = sv.lg(218, 318, 242, 455, [(0, bd, 1), (0.45, bd, 1), (1, bdk, 1)])
    sv.pa("M230,318 C233,342 235,378 233,408 C231,428 228,442 223,452 L210,452 "
          "C213,442 217,428 218,408 C220,378 218,342 215,318Z", fill=f'url(#{flg2})')
    sv.el(224, 375, 6, 11, fill=blt, op=0.22)
    sv.el(216, 452, 14, 8, fill=hf)
    sv.el(214, 450, 9, 4, fill=hflt, op=0.35)
    sv.pa("M210,450 L222,450", fill='none', stroke=darken(hf, 0.5), sw=0.8, op=0.4)

    # ── NECK ──
    ng = sv.lg(168, 180, 226, 260, [(0, blt, 1), (0.5, bd, 1), (1, bdk, 1)])
    sv.pa("M195,248 C185,228 175,202 170,182 C165,165 168,155 180,148 "
          "C195,140 208,145 213,158 C222,178 228,215 228,245Z", fill=f'url(#{ng})')
    # Neck front highlight
    sv.pa("M175,178 C172,198 182,228 198,250", fill='none', stroke=blt, sw=2, op=0.35)
    # Neck back shadow
    sv.pa("M210,160 C218,180 225,215 228,245", fill='none', stroke=bdk, sw=2, op=0.2)

    # ── HEAD ──
    hg = sv.rg(176, 148, 48, [(0, blt, 1), (0.35, bd, 1), (1, bdk, 1)], fx=165, fy=136)
    sv.pa("M138,158 C133,142 138,120 155,112 C170,105 192,108 202,120 "
          "C212,132 214,150 207,162 C200,174 182,178 167,175 C152,172 141,168 138,158Z",
          fill=f'url(#{hg})')

    # Jawline shadow
    sv.pa("M142,160 C150,170 164,175 178,174", fill='none', stroke=bdk, sw=1.2, op=0.25)

    # Snout / muzzle
    stg = sv.rg(143, 162, 30, [(0, lighten(bd, 0.42), 1), (1, bd, 1)])
    sv.pa("M132,150 C122,152 115,160 118,170 C120,178 130,183 145,180 "
          "C158,178 165,172 162,162 C160,154 148,149 132,150Z", fill=f'url(#{stg})')
    # Snout highlight
    sv.el(135, 160, 12, 6, fill=bvl, op=0.25)

    # Nostrils
    sv.el(128, 168, 3.5, 2.5, fill=ns, op=0.65)
    sv.el(137, 166, 3, 2, fill=ns, op=0.45)
    # Nostril inner detail
    sv.el(128, 168, 2, 1.2, fill=darken(ns, 0.5), op=0.4)

    # Mouth line
    sv.pa("M122,173 C130,177 142,178 154,173", fill='none', stroke=bdk, sw=1, op=0.35)

    # ── EARS ──
    # Far ear
    svg_ear(sv, 182, 115, 174, 80, 194, 105, bdk, ck, 0.7)
    # Near ear
    svg_ear(sv, 170, 112, 155, 76, 180, 102, bd, ck, 1.0)

    # ── HORN ──
    if include_horn:
        hg2 = sv.lg(152, 55, 178, 115, [(0, hrlt, 1), (0.3, hr, 1), (0.8, hrdk, 1), (1, darken(hr, 0.6), 1)])
        sv.pa("M166,114 L145,48 L178,110Z", fill=f'url(#{hg2})')
        # Horn spiral bands
        for i in range(7):
            y = 108 - i * 9
            frac = (108 - y) / 60
            x1 = 165 - frac * 14
            x2 = 172 - frac * 8
            sv.pa(f"M{x1:.1f},{y} L{x1+0.8:.1f},{y-3.5} L{x2+0.8:.1f},{y-2.8} L{x2:.1f},{y+0.7}Z",
                  fill=hrdk, op=0.28)
        # Horn highlight
        sv.pa("M163,105 L149,55", fill='none', stroke=hrlt, sw=1.8, op=0.55)
        # Horn tip glow
        hglow = sv.rg(146, 50, 12, [(0, hrlt, 0.6), (1, hrlt, 0)])
        sv.ci(146, 50, 12, fill=f'url(#{hglow})')

    # ── EYE ──
    svg_eye(sv, 180, 140, ey, 10, 7)

    # Cheek blush
    bg2 = sv.rg(165, 160, 14, [(0, ck, 0.30), (1, ck, 0)])
    sv.ci(165, 160, 14, fill=f'url(#{bg2})')

    # ── MANE ──
    if include_mane:
        svg_mane(sv, mn, mndk, mnlt)


def svg_ear(sv, bx, by, tx, ty, cx, cy, col, inner_col, op):
    """Draw a single ear as a triangle with inner detail."""
    sv.pa(f"M{bx},{by} L{tx},{ty} L{cx},{cy}Z", fill=col, op=op)
    # Inner ear
    ix = bx * 0.35 + tx * 0.35 + cx * 0.30
    iy = by * 0.35 + ty * 0.35 + cy * 0.30
    sv.pa(f"M{bx*0.6+tx*0.4:.0f},{by*0.6+ty*0.4:.0f} "
          f"L{tx*0.8+ix*0.2:.0f},{ty*0.8+iy*0.2:.0f} "
          f"L{cx*0.6+tx*0.4:.0f},{cy*0.6+ty*0.4:.0f}Z",
          fill=inner_col, op=0.45)


def svg_eye(sv, ex, ey, col, rx, ry):
    """Draw a detailed eye with iris, pupil, highlights, lashes."""
    # White
    sv.el(ex, ey, rx, ry, fill='#ffffff')
    # Iris gradient
    ig = sv.rg(ex, ey, rx - 2, [(0, lighten(col, 0.35), 1), (0.55, col, 1), (1, darken(col, 0.40), 1)])
    sv.el(ex, ey, rx - 3, ry - 0.5, fill=f'url(#{ig})')
    # Iris ring detail
    sv.el(ex, ey, rx - 3.5, ry - 1, fill='none', stroke=darken(col, 0.55), sw=0.5, op=0.3)
    # Pupil
    sv.el(ex, ey, rx * 0.35, ry * 0.72, fill='#050505')
    # Primary highlight
    sv.ci(ex - rx * 0.22, ey - ry * 0.28, rx * 0.26, fill='#ffffff', op=0.92)
    # Secondary highlight
    sv.ci(ex + rx * 0.18, ey + ry * 0.22, rx * 0.12, fill='#ffffff', op=0.50)
    # Upper lashes
    sv.pa(f"M{ex-rx},{ey-1} C{ex-rx*0.6},{ey-ry-2} {ex+rx*0.3},{ey-ry-3} {ex+rx},{ey-1}",
          fill='none', stroke='#1a1a1a', sw=1.3)
    # Lower lid
    sv.pa(f"M{ex-rx+1},{ey+1} C{ex-rx*0.3},{ey+ry} {ex+rx*0.3},{ey+ry} {ex+rx-1},{ey}",
          fill='none', stroke=darken(col, 0.6), sw=0.7, op=0.35)


def svg_mane(sv, mn, mndk, mnlt):
    """Draw a flowing mane along the unicorn's neck."""
    # Multiple strands, back to front (darkest to lightest)
    strands = [
        ("M177,108 C188,122 198,155 200,190 C202,218 197,242 192,258 "
         "C187,258 190,215 188,190 C185,158 177,128 172,112Z", mndk, 0.75),
        ("M172,105 C182,118 190,148 192,180 C194,208 190,238 185,255 "
         "C180,255 184,212 182,182 C179,152 170,122 166,108Z", mn, 0.85),
        ("M167,102 C176,114 182,143 184,172 C186,198 182,226 178,248 "
         "C173,248 178,202 176,174 C174,146 166,118 162,105Z", mn, 0.90),
        ("M163,100 C172,110 177,138 178,165 C179,188 175,218 172,242 "
         "C167,242 172,194 171,168 C169,140 162,115 158,103Z", lighten(mn, 0.2), 0.80),
        ("M160,98 C168,106 172,132 174,158 C175,180 172,212 170,238 "
         "C165,238 168,186 167,160 C165,134 159,112 155,101Z", mnlt, 0.65),
    ]
    for d, c, o in strands:
        sv.pa(d, fill=c, op=o)

    # Forelock tuft (on forehead between ears)
    sv.pa("M162,100 C155,88 146,83 138,86 C142,94 150,100 158,103Z", fill=mn)
    sv.pa("M158,96 C152,85 145,82 140,84 C143,90 148,96 155,100Z", fill=mnlt, op=0.5)

    # Hair strand detail lines
    for i in range(10):
        t = i / 9
        sx = 160 + t * 18
        sy = 100 + t * 6
        ex2 = 170 + t * 14
        ey2 = 238 + t * 8
        cx = sx + 16
        cy = (sy + ey2) / 2 - 15
        sv.pa(f"M{sx:.0f},{sy:.0f} Q{cx:.0f},{cy:.0f} {ex2:.0f},{ey2:.0f}",
              fill='none', stroke=mnlt, sw=0.5, op=0.22)


# ═══════════════════════════════════════════════════════════════
#  Wing Drawing
# ═══════════════════════════════════════════════════════════════

def draw_wings(sv, p, style='feathered'):
    wc = p.get('wing', lighten(p.get('body', '#ccccee'), 0.35))
    wdk = darken(wc, 0.45)
    wlt = lighten(wc, 0.30)

    wg = sv.lg(240, 230, 420, 75, [(0, wdk, 0.9), (0.4, wc, 1), (1, wlt, 1)])

    if style == 'bat':
        # Bat/dark wings
        sv.pa("M238,240 C255,185 295,125 355,80 C375,65 395,60 415,72 "
              "C430,82 432,100 420,115 C400,140 355,168 320,195 C295,215 260,240 238,240Z",
              fill=f'url(#{wg})')
        # Membrane spans
        for i in range(4):
            t = i / 3
            x1 = 250 + t * 40
            y1 = 220 - t * 30
            x2 = 340 + t * 50
            y2 = 90 + t * 15
            sv.pa(f"M{x1:.0f},{y1:.0f} L{x2:.0f},{y2:.0f}",
                  fill='none', stroke=wdk, sw=1.5, op=0.3)
        # Wing edge
        sv.pa("M238,240 C255,185 295,125 355,80 C375,65 395,60 415,72",
              fill='none', stroke=wdk, sw=1.5, op=0.4)
    else:
        # Feathered wings
        sv.pa("M238,240 C255,185 290,125 350,82 C378,65 408,68 420,88 "
              "C428,102 418,122 398,135 C368,155 328,178 305,205 C285,228 260,245 238,240Z",
              fill=f'url(#{wg})')
        # Flight feathers (overlapping, detailed)
        feathers = [
            (255, 210, 345, 90), (265, 200, 360, 85), (275, 192, 375, 82),
            (282, 188, 388, 84), (288, 185, 400, 90), (292, 184, 410, 98),
        ]
        for i, (x1, y1, x2, y2) in enumerate(feathers):
            cx = (x1 + x2) / 2 + 18
            cy = y1 - 22
            o = 0.18 + i * 0.06
            sv.pa(f"M{x1},{y1} C{cx:.0f},{cy:.0f} {x2-8},{y2+6} {x2},{y2} "
                  f"C{x2-6},{y2+16} {cx-12:.0f},{cy+22:.0f} {x1+6},{y1+10}Z",
                  fill=wlt, op=o)
        # Feather edge tips
        for i in range(8):
            t = i / 7
            x = 265 + t * 145
            y = 205 - t * 115
            sv.pa(f"M{x:.0f},{y:.0f} L{x+10:.0f},{y-7:.0f} L{x+14:.0f},{y+4:.0f}Z",
                  fill=wc, op=0.4)
        # Wing highlight
        sv.pa("M248,232 C262,190 295,140 345,100",
              fill='none', stroke=wlt, sw=2, op=0.5)


# ═══════════════════════════════════════════════════════════════
#  Narwhal Body
# ═══════════════════════════════════════════════════════════════

def narwhal_body(sv, p, include_horn=True):
    bd = p['body']
    bdk = darken(bd, 0.55)
    blt = lighten(bd, 0.35)
    belly = p.get('belly', '#d8dce8')
    hr = p.get('horn', '#ffd700')
    hrdk = darken(hr, 0.45)
    hrlt = lighten(hr, 0.30)
    ey = p.get('eye', '#1a1a3a')

    blur = sv.fb(6)
    sblur = sv.fb(3)

    # Water splash
    wg = sv.rg(256, 408, 140, [(0, '#7ecce8', 0.35), (1, '#7ecce8', 0)])
    sv.el(256, 408, 140, 35, fill=f'url(#{wg})')
    # Water ripples
    for i in range(5):
        t = i / 4
        y = 395 + t * 25
        w = 120 - t * 20
        sv.pa(f"M{256-w:.0f},{y:.0f} Q{256:.0f},{y-4:.0f} {256+w:.0f},{y:.0f}",
              fill='none', stroke='#99ddee', sw=0.8, op=0.3 - t * 0.05)

    # Body gradient
    bg = sv.lg(256, 150, 256, 360, [(0, bdk, 1), (0.35, bd, 1), (0.65, blt, 1), (1, belly, 1)])

    # Main body (whale shape)
    sv.pa("M95,282 C78,262 82,222 108,200 C138,178 200,158 280,162 "
          "C360,168 422,198 442,235 C458,262 450,295 428,315 "
          "C402,338 342,348 272,348 C200,345 138,335 118,318 C102,305 95,295 95,282Z",
          fill=f'url(#{bg})')

    # Belly highlight
    bg2 = sv.rg(272, 318, 95, [(0, belly, 0.55), (1, belly, 0)])
    sv.el(272, 318, 90, 25, fill=f'url(#{bg2})')

    # Dorsal ridge
    sv.pa("M195,165 C240,152 305,155 360,168 C390,175 415,188 430,205",
          fill='none', stroke=bdk, sw=2.5, op=0.3)

    # Speckles
    rng = random.Random(42)
    for _ in range(25):
        sx = 140 + rng.random() * 260
        sy = 185 + rng.random() * 110
        sr = 1.5 + rng.random() * 4
        sv.ci(sx, sy, sr, fill=blt, op=0.15 + rng.random() * 0.18)

    # Tail fin
    tg = sv.lg(420, 250, 495, 320, [(0, bd, 1), (0.5, bdk, 1), (1, darken(bd, 0.65), 1)])
    sv.pa("M432,268 C448,242 472,222 495,210 C482,232 468,252 448,268 "
          "C468,280 485,302 498,325 C475,315 455,295 432,280 "
          "C433,276 432,272 432,268Z", fill=f'url(#{tg})')
    # Tail fin detail
    sv.pa("M440,265 C455,248 470,232 485,220", fill='none', stroke=blt, sw=1, op=0.3)
    sv.pa("M440,280 C458,295 475,310 490,318", fill='none', stroke=blt, sw=1, op=0.3)

    # Flippers
    sv.pa("M175,305 C165,325 150,345 135,352 C140,340 152,322 162,305Z", fill=bdk, op=0.7)
    sv.pa("M195,310 C190,332 180,348 170,355 C173,342 182,325 188,310Z", fill=bd, op=0.6)
    # Flipper detail
    sv.pa("M170,315 C162,332 152,345 142,350", fill='none', stroke=blt, sw=0.8, op=0.3)

    # Head refined shape
    hdg = sv.rg(125, 232, 65, [(0, blt, 1), (0.6, bd, 1), (1, bdk, 1)])
    sv.pa("M85,262 C75,242 80,215 98,200 C118,182 150,175 172,180 "
          "C188,185 195,200 190,222 C185,250 165,270 132,275 C110,278 92,272 85,262Z",
          fill=f'url(#{hdg})')

    # Mouth
    sv.pa("M88,258 C105,268 132,272 160,262", fill='none', stroke=bdk, sw=1.2, op=0.4)
    # Smile detail
    sv.pa("M92,260 C108,265 128,267 148,262", fill='none', stroke=blt, sw=0.6, op=0.2)

    # Eye
    ex, ey2 = 138, 222
    sv.el(ex, ey2, 9, 7, fill='#ffffff')
    ig = sv.rg(ex, ey2, 6, [(0, lighten(ey, 0.3), 1), (0.6, ey, 1), (1, darken(ey, 0.4), 1)])
    sv.el(ex, ey2, 6, 6, fill=f'url(#{ig})')
    sv.el(ex, ey2, 3, 4.5, fill='#050505')
    sv.ci(ex - 2, ey2 - 2, 2.2, fill='#ffffff', op=0.9)
    sv.ci(ex + 1.2, ey2 + 1.5, 1, fill='#ffffff', op=0.45)

    # Horn/tusk
    if include_horn:
        hg = sv.lg(78, 195, 52, 55, [(0, hrdk, 1), (0.4, hr, 1), (1, hrlt, 1)])
        sv.pa("M92,198 L50,55 L105,195Z", fill=f'url(#{hg})')
        for i in range(8):
            y = 188 - i * 18
            frac = (188 - y) / 133
            x = 95 - frac * 35
            sv.pa(f"M{x:.1f},{y} L{x+0.8:.1f},{y-5} L{x+6:.1f},{y-4} L{x+5.2:.1f},{y+1}Z",
                  fill=hrdk, op=0.22)
        sv.pa("M94,192 L55,62", fill='none', stroke=hrlt, sw=1.5, op=0.45)
        # Tusk glow
        tglow = sv.rg(52, 58, 15, [(0, hrlt, 0.5), (1, hrlt, 0)])
        sv.ci(52, 58, 15, fill=f'url(#{tglow})')


# ═══════════════════════════════════════════════════════════════
#  Baby Unicorn Body
# ═══════════════════════════════════════════════════════════════

def baby_body(sv, p):
    bd = p['body']
    bdk = darken(bd, 0.55)
    blt = lighten(bd, 0.40)
    bvl = lighten(bd, 0.60)
    mn = p.get('mane', '#bb88dd')
    mnlt = lighten(mn, 0.40)
    hr = p.get('horn', '#ffd700')
    hrlt = lighten(hr, 0.30)
    hf = p.get('hoof', '#3a3a3a')
    ey = p.get('eye', '#5544cc')
    ck = p.get('cheek', '#ffb6c1')

    blur = sv.fb(5)

    # Ground shadow
    sv.el(256, 445, 95, 14, fill='#000000', op=0.10, filt=blur)

    # ── Back legs (behind body) ──
    for lx in [218, 295]:
        sv.pa(f"M{lx-9},358 L{lx-11},420 L{lx+11},420 L{lx+9},358Z", fill=bdk)
        sv.el(lx, 422, 13, 7, fill=hf)
        sv.el(lx, 420, 8, 3, fill=lighten(hf, 0.3), op=0.3)

    # ── Chubby body ──
    bg = sv.rg(256, 328, 92, [(0, blt, 1), (0.55, bd, 1), (1, bdk, 1)], fx=240, fy=308)
    sv.el(256, 330, 88, 62, fill=f'url(#{bg})')

    # Tummy highlight
    tg = sv.rg(256, 348, 52, [(0, bvl, 0.50), (1, bvl, 0)])
    sv.el(256, 348, 48, 32, fill=f'url(#{tg})')

    # ── Cute tail ──
    sv.pa("M342,318 C362,302 378,312 374,335 C370,352 358,358 348,348 C340,340 338,328 342,318Z", fill=mn)
    sv.pa("M345,322 C360,308 374,318 370,335 C367,348 358,352 350,345Z", fill=mnlt, op=0.5)

    # ── Front legs ──
    for lx in [233, 278]:
        sv.pa(f"M{lx-9},360 L{lx-11},422 L{lx+11},422 L{lx+9},360Z", fill=bd)
        sv.el(lx, 424, 13, 7, fill=hf)
        sv.el(lx, 422, 8, 3, fill=lighten(hf, 0.3), op=0.35)

    # ── Big head ──
    hg = sv.rg(256, 215, 88, [(0, blt, 1), (0.38, bd, 1), (1, bdk, 1)], fx=240, fy=195)
    sv.el(256, 218, 82, 72, fill=f'url(#{hg})')

    # Head highlight
    hhl = sv.rg(240, 195, 35, [(0, bvl, 0.4), (1, bvl, 0)])
    sv.ci(240, 195, 35, fill=f'url(#{hhl})')

    # Snout
    sg = sv.rg(238, 252, 32, [(0, lighten(bd, 0.45), 1), (1, bd, 1)])
    sv.el(238, 254, 32, 24, fill=f'url(#{sg})')
    # Nostrils
    sv.el(228, 255, 3, 2, fill=darken(bd, 0.35), op=0.45)
    sv.el(236, 253, 2.5, 1.5, fill=darken(bd, 0.35), op=0.35)
    # Smile
    sv.pa("M222,264 C234,272 250,272 262,264", fill='none', stroke=bdk, sw=1.2, op=0.35)

    # ── Ears ──
    svg_ear(sv, 218, 158, 198, 118, 230, 150, bd, ck, 1.0)
    svg_ear(sv, 290, 153, 312, 115, 298, 148, bd, ck, 1.0)

    # ── Small horn ──
    hg2 = sv.lg(253, 118, 260, 158, [(0, hrlt, 1), (1, hr, 1)])
    sv.pa("M248,158 L245,115 L268,158Z", fill=f'url(#{hg2})')
    for i in range(4):
        y = 152 - i * 10
        sv.pa(f"M{249},{y} L{249},{y-4} L{260},{y-3} L{260},{y+1}Z",
              fill=darken(hr, 0.4), op=0.28)

    # ── Big cute eyes ──
    for ex, ey2, mirror in [(232, 210, 1), (280, 210, -1)]:
        sv.el(ex, ey2, 17, 15, fill='#ffffff')
        ig = sv.rg(ex, ey2, 13, [(0, lighten(ey, 0.4), 1), (0.5, ey, 1), (1, darken(ey, 0.3), 1)])
        sv.el(ex, ey2 + 1, 12, 12, fill=f'url(#{ig})')
        sv.el(ex, ey2 + 2, 6.5, 9, fill='#050505')
        sv.ci(ex - 3.5 * mirror, ey2 - 3, 4.5, fill='#ffffff', op=0.95)
        sv.ci(ex + 2 * mirror, ey2 + 3, 2, fill='#ffffff', op=0.50)
        # Lashes
        sv.pa(f"M{ex-15},{ey2-2} C{ex-10},{ey2-14} {ex+8},{ey2-15} {ex+15},{ey2-3}",
              fill='none', stroke='#1a1a1a', sw=1.2)

    # Cheek blush
    for bx in [212, 298]:
        bg3 = sv.rg(bx, 240, 16, [(0, ck, 0.38), (1, ck, 0)])
        sv.ci(bx, 240, 16, fill=f'url(#{bg3})')

    # ── Cute mane tuft ──
    sv.pa("M238,158 C232,142 238,130 255,128 C268,127 282,133 285,148 "
          "C280,150 268,144 258,144 C248,144 240,150 238,158Z", fill=mn)
    sv.pa("M242,155 C238,142 244,133 258,131 C268,130 278,136 280,148 "
          "C276,149 266,144 258,144 C250,145 244,150 242,155Z", fill=mnlt, op=0.55)

    # Sparkle details around baby
    for (sx, sy, sr) in [(175, 175, 3), (340, 180, 2.5), (160, 300, 2), (350, 310, 3), (180, 400, 2)]:
        # 4-pointed star sparkle
        sv.pa(f"M{sx},{sy-sr*2} L{sx+sr*0.5},{sy-sr*0.5} L{sx+sr*2},{sy} L{sx+sr*0.5},{sy+sr*0.5} "
              f"L{sx},{sy+sr*2} L{sx-sr*0.5},{sy+sr*0.5} L{sx-sr*2},{sy} L{sx-sr*0.5},{sy-sr*0.5}Z",
              fill='#ffffff', op=0.35)


# ═══════════════════════════════════════════════════════════════
#  Card-Specific Decoration Functions
# ═══════════════════════════════════════════════════════════════

def deco_zombie(sv):
    """Green decay patches, stitches, drips."""
    for cx, cy, r in [(228, 272, 16), (305, 285, 13), (262, 315, 11), (195, 245, 9), (340, 260, 10)]:
        g = sv.rg(cx, cy, r, [(0, '#4a7a3f', 0.5), (1, '#4a7a3f', 0)])
        sv.ci(cx, cy, r, fill=f'url(#{g})')
    # Stitches (forehead)
    sv.pa("M155,132 L195,128", fill='none', stroke='#2a2a2a', sw=1.5)
    for i in range(5):
        x = 158 + i * 8
        sv.pa(f"M{x},126 L{x+2},133", fill='none', stroke='#2a2a2a', sw=0.8)
    # Stitches (body)
    sv.pa("M250,285 L308,278", fill='none', stroke='#2a2a2a', sw=1.5)
    for i in range(6):
        x = 254 + i * 10
        sv.pa(f"M{x},276 L{x+2},286", fill='none', stroke='#2a2a2a', sw=0.8)
    # Drips
    for dx, dy in [(232, 278), (300, 288), (265, 318)]:
        sv.pa(f"M{dx},{dy} C{dx-2},{dy+12} {dx-3},{dy+25} {dx},{dy+32} "
              f"C{dx+2},{dy+35} {dx+4},{dy+32} {dx+3},{dy+25} C{dx+2},{dy+15} {dx+1},{dy+5} {dx},{dy}Z",
              fill='#4a7a3f', op=0.4)
    # X eye
    sv.pa("M176,135 L184,145 M184,135 L176,145", fill='none', stroke='#cc3333', sw=2)


def deco_flames(sv):
    """Phoenix fire effects."""
    flame_data = [
        ("M200,225 C188,188 195,148 222,115 C230,132 215,168 210,205Z", "#ff4400", 0.55),
        ("M212,218 C205,178 218,135 245,105 C248,128 232,162 225,200Z", "#ff6600", 0.50),
        ("M385,240 C395,200 388,158 362,125 C355,148 368,180 372,215Z", "#ff4400", 0.48),
        ("M255,205 C248,165 260,118 290,85 C292,112 278,152 272,190Z", "#ffaa00", 0.42),
        ("M355,230 C362,192 355,148 332,120 C328,142 338,175 342,210Z", "#ff6600", 0.40),
        ("M230,210 C222,175 230,130 258,98 C260,120 248,158 242,195Z", "#ffe040", 0.30),
        ("M370,232 C378,195 372,155 348,128 C345,148 355,178 358,212Z", "#ffe040", 0.28),
    ]
    for d, c, o in flame_data:
        sv.pa(d, fill=c, op=o)
    for d, c, o in flame_data[:3]:
        sv.pa(d, fill='none', stroke=lighten(c, 0.4), sw=0.8, op=o * 0.6)
    # Embers
    rng = random.Random(99)
    for _ in range(20):
        px = 175 + rng.random() * 220
        py = 70 + rng.random() * 200
        pr = 0.8 + rng.random() * 2.5
        c = ['#ffcc00', '#ff8800', '#ffee44'][rng.randint(0, 2)]
        sv.ci(px, py, pr, fill=c, op=0.25 + rng.random() * 0.4)


def deco_shark_features(sv):
    """Shark-specific features: fin, teeth, gill slits."""
    # Dorsal fin
    sv.pa("M260,158 L280,80 L310,155Z", fill='#556677')
    sv.pa("M265,155 L282,90 L305,152Z", fill='#667788', op=0.6)
    # Gill slits
    for i in range(3):
        y = 225 + i * 15
        sv.pa(f"M155,{y} C160,{y+3} 165,{y+6} 168,{y+10}",
              fill='none', stroke='#3a4550', sw=1.5, op=0.5)
    # Teeth (along mouth)
    for i in range(8):
        x = 95 + i * 9
        sv.pa(f"M{x},258 L{x+3},268 L{x+6},258Z", fill='#ffffff', op=0.8)
    # Scar
    sv.pa("M150,200 L170,220", fill='none', stroke='#aabbcc', sw=1, op=0.3)


def deco_mermaid_tail(sv):
    """Replace back legs with a mermaid/fish tail, add shells."""
    # Fish tail (covers back legs)
    tg = sv.lg(310, 310, 420, 440, [(0, '#5ab8b8', 1), (0.5, '#3a9898', 1), (1, '#2a7878', 1)])
    sv.pa("M310,315 C320,350 340,390 380,410 C400,420 420,415 430,400 "
          "C425,390 410,385 395,395 L345,355 C330,340 320,325 310,315Z", fill=f'url(#{tg})')
    # Tail fin
    sv.pa("M380,410 C395,430 415,445 440,435 C430,425 415,420 405,415 "
          "C420,425 435,440 450,438 C440,430 425,420 410,415 L380,410Z",
          fill='#3a9898', op=0.7)
    # Scales
    rng = random.Random(55)
    for i in range(15):
        sx = 315 + rng.random() * 80
        sy = 325 + rng.random() * 70
        sv.pa(f"M{sx:.0f},{sy:.0f} C{sx+4:.0f},{sy-4:.0f} {sx+8:.0f},{sy-4:.0f} {sx+12:.0f},{sy:.0f} "
              f"C{sx+8:.0f},{sy+4:.0f} {sx+4:.0f},{sy+4:.0f} {sx:.0f},{sy:.0f}Z",
              fill='#4acaca', op=0.3)
    # Seashell accessory on body
    sv.pa("M230,260 C225,250 230,240 240,238 C248,240 252,248 248,258 C244,265 235,268 230,260Z",
          fill='#ffaacc', op=0.6)
    sv.pa("M233,258 L240,242 M236,256 L243,244 M240,255 L246,246",
          fill='none', stroke='#ff88aa', sw=0.6, op=0.4)


def deco_llama_wool(sv):
    """Fluffy wool texture on body."""
    rng = random.Random(33)
    for _ in range(40):
        cx = 200 + rng.random() * 180
        cy = 230 + rng.random() * 100
        r = 8 + rng.random() * 12
        sv.ci(cx, cy, r, fill=lighten('#d4a860', 0.3), op=0.25)
    for _ in range(25):
        cx = 210 + rng.random() * 160
        cy = 235 + rng.random() * 90
        r = 5 + rng.random() * 8
        sv.ci(cx, cy, r, fill='#e8c888', op=0.35)
    # Neck fluff
    for _ in range(15):
        cx = 170 + rng.random() * 50
        cy = 162 + rng.random() * 80
        r = 6 + rng.random() * 10
        sv.ci(cx, cy, r, fill=lighten('#d4a860', 0.25), op=0.3)


def deco_armor_plates(sv):
    """Rhino armor plates on body."""
    plates = [
        "M230,245 L260,238 L290,245 L285,270 L260,275 L235,270Z",
        "M295,240 L325,235 L350,242 L345,265 L320,270 L295,265Z",
        "M210,270 L240,268 L245,290 L235,305 L210,300Z",
        "M350,248 L375,250 L380,272 L370,290 L350,285Z",
    ]
    for pl in plates:
        sv.pa(pl, fill='#8a8a8a', op=0.4)
        sv.pa(pl, fill='none', stroke='#666666', sw=1.2, op=0.5)
    # Extra horn on nose
    sv.pa("M118,155 L108,125 L132,152Z", fill='#c0c0b0')
    sv.pa("M120,153 L112,128 L130,150Z", fill='#d0d0c0', op=0.5)


def deco_armor(sv):
    """Knight armor on body and head."""
    # Body armor plate
    sv.pa("M205,245 C220,230 310,225 375,240 C390,245 395,265 390,290 "
          "C385,310 350,330 290,335 C245,338 215,330 205,315 C195,300 195,260 205,245Z",
          fill='#555568', op=0.5)
    sv.pa("M205,245 C220,230 310,225 375,240", fill='none', stroke='#8888aa', sw=1.5, op=0.5)
    # Helmet visor
    sv.pa("M140,125 C145,115 165,108 185,112 C200,115 208,128 205,142 "
          "C202,152 190,160 175,158 C155,155 138,140 140,125Z",
          fill='#444458', op=0.5)
    # Visor slit
    sv.pa("M155,135 L195,132", fill='none', stroke='#222230', sw=2, op=0.6)
    # Sword
    sv.pa("M120,300 L115,180 M110,185 L120,180 L130,185", fill='none', stroke='#aaaacc', sw=2)
    sv.pa("M115,180 L117,165 L119,180Z", fill='#ccccdd')


def deco_knife(sv):
    """Cute knife accessory."""
    # Knife blade
    sv.pa("M135,280 L110,220 L120,215 L140,275Z", fill='#cccccc')
    sv.pa("M137,278 L115,222 L122,218 L140,275Z", fill='#e0e0e0', op=0.5)
    # Handle
    sv.pa("M132,282 L142,278 L148,298 L138,302Z", fill='#885533')
    sv.pa("M134,284 L140,280 L144,296 L138,300Z", fill='#aa7744', op=0.5)
    # Blood drips (cute pink)
    sv.pa("M115,225 C113,235 112,245 115,248 C117,245 116,235 115,225Z", fill='#ff6688', op=0.4)
    # Bandage on horn
    sv.pa("M158,90 L168,86 L172,96 L162,100Z", fill='#ffe0cc', op=0.7)
    sv.pa("M155,78 L165,74 L168,82 L158,86Z", fill='#ffe0cc', op=0.6)


def deco_chainsaw(sv):
    """Chainsaw accessory."""
    # Handle
    sv.re(118, 310, 35, 50, rx=4, fill='#cc4422')
    sv.re(122, 315, 27, 40, rx=3, fill='#dd5533', op=0.6)
    # Blade body
    sv.pa("M128,310 L122,200 L140,195 L148,305Z", fill='#888888')
    sv.pa("M130,308 L125,205 L138,200 L145,303Z", fill='#999999', op=0.5)
    # Chain teeth
    for i in range(10):
        y = 300 - i * 11
        sv.pa(f"M120,{y} L118,{y-4} L122,{y-5}Z", fill='#bbbbbb', op=0.6)
        sv.pa(f"M142,{y} L145,{y-4} L141,{y-5}Z", fill='#bbbbbb', op=0.6)
    # Chain top curve
    sv.pa("M122,200 C122,190 130,185 140,195", fill='none', stroke='#aaaaaa', sw=3)


def deco_dark_wings(sv):
    """Dark angel wings and halo."""
    draw_wings(sv, {'body': '#1a1030', 'wing': '#2a1a40'}, style='bat')
    # Dark halo
    sv.el(170, 72, 30, 8, fill='none', stroke='#8866aa', sw=3, op=0.6)
    sv.el(170, 72, 30, 8, fill='none', stroke=lighten('#8866aa', 0.4), sw=1, op=0.3)
    # Dark particles
    rng = random.Random(77)
    for _ in range(12):
        px = 170 + rng.random() * 200
        py = 80 + rng.random() * 150
        pr = 1 + rng.random() * 2
        sv.ci(px, py, pr, fill='#6633aa', op=0.3)


def deco_crown(sv, cx=168, cy=68):
    """Royal crown."""
    # Crown base
    sv.pa(f"M{cx-20},{cy+10} L{cx-22},{cy-5} L{cx-12},{cy+2} L{cx},{cy-12} "
          f"L{cx+12},{cy+2} L{cx+22},{cy-5} L{cx+20},{cy+10}Z", fill='#ffd700')
    sv.pa(f"M{cx-18},{cy+8} L{cx-20},{cy-2} L{cx-10},{cy+3} L{cx},{cy-8} "
          f"L{cx+10},{cy+3} L{cx+20},{cy-2} L{cx+18},{cy+8}Z", fill='#ffee55', op=0.6)
    # Crown jewels
    sv.ci(cx, cy - 8, 2.5, fill='#cc2244')
    sv.ci(cx - 14, cy + 1, 2, fill='#2244cc')
    sv.ci(cx + 14, cy + 1, 2, fill='#22cc44')
    # Crown base band
    sv.re(cx - 20, cy + 6, 40, 5, rx=1, fill='#ddaa00')


def deco_bee_stripes(sv):
    """Bee stripes and small wings."""
    # Black stripes on body
    stripes = [(240, 262), (270, 258), (300, 260), (330, 265), (355, 272)]
    for sx, sy in stripes:
        sv.pa(f"M{sx},{sy} C{sx+5},{sy-12} {sx+15},{sy-15} {sx+25},{sy-10} "
              f"C{sx+20},{sy+2} {sx+10},{sy+5} {sx},{sy}Z",
              fill='#1a1100', op=0.35)
    # Small bee wings
    sv.el(275, 218, 30, 15, fill='#ffffff', op=0.25)
    sv.el(305, 215, 25, 12, fill='#ffffff', op=0.20)
    # Antennae
    sv.pa("M160,105 C155,88 148,78 142,72", fill='none', stroke='#1a1100', sw=1.5)
    sv.ci(142, 72, 3, fill='#ffd700')
    sv.pa("M175,100 C172,82 168,72 164,66", fill='none', stroke='#1a1100', sw=1.5)
    sv.ci(164, 66, 3, fill='#ffd700')


def deco_corn_husk(sv):
    """Corn husk wrapper on body, corn kernel texture."""
    # Husk leaves wrapping the body
    husks = [
        ("M195,260 C180,235 178,295 185,340 C200,355 230,358 235,340 C240,310 212,280 195,260Z", '#7ab340', 0.35),
        ("M380,258 C398,235 400,295 395,338 C382,352 355,355 350,338 C345,310 368,278 380,258Z", '#6aa330', 0.3),
        ("M190,285 C175,265 172,310 178,345 C188,358 210,360 215,345Z", '#88c348', 0.25),
        ("M385,282 C402,262 405,308 400,342 C392,355 372,358 368,342Z", '#78b338', 0.25),
    ]
    for d, c, o in husks:
        sv.pa(d, fill=c, op=o)
    # Kernel dots
    rng = random.Random(88)
    for _ in range(30):
        kx = 220 + rng.random() * 140
        ky = 250 + rng.random() * 80
        sv.ci(kx, ky, 3, fill='#ffdd44', op=0.3)
        sv.ci(kx, ky, 1.5, fill='#ffee88', op=0.2)


def deco_hearts(sv):
    """Floating hearts for seductive unicorn."""
    hearts = [(140, 100, 12, 0.5), (380, 130, 15, 0.4), (120, 260, 10, 0.35),
              (410, 190, 8, 0.3), (350, 80, 11, 0.45), (160, 380, 9, 0.3)]
    for hx, hy, hs, ho in hearts:
        # Simple heart from two arcs
        sv.pa(f"M{hx},{hy+hs*0.3} "
              f"C{hx-hs},{hy-hs*0.5} {hx-hs*0.1},{hy-hs} {hx},{hy-hs*0.3} "
              f"C{hx+hs*0.1},{hy-hs} {hx+hs},{hy-hs*0.5} {hx},{hy+hs*0.3}Z",
              fill='#ff4488', op=ho)
    # Lipstick mark on cheek area
    sv.pa("M190,155 C185,150 188,148 192,152 C196,148 199,150 194,155 "
          "C192,157 190,157 190,155Z", fill='#ff2255', op=0.5)


def deco_stars_stripes(sv):
    """Patriotic stars and stripes for Americorn."""
    # Stripes on body (5 red+white)
    for i in range(5):
        y = 248 + i * 18
        c = '#cc2244' if i % 2 == 0 else '#ffffff'
        sv.pa(f"M210,{y} C250,{y-3} 320,{y-3} 380,{y}",
              fill='none', stroke=c, sw=6, op=0.25)
    # Stars
    star_pts = [(180, 200), (250, 190), (320, 195), (290, 230), (220, 228)]
    for sx, sy in star_pts:
        draw_star(sv, sx, sy, 6, '#ffffff', 0.35)
    # Blue field on shoulder
    sv.re(195, 240, 50, 40, rx=3, fill='#223388', op=0.3)
    for sy2 in range(245, 280, 10):
        for sx2 in range(200, 240, 12):
            draw_star(sv, sx2, sy2, 3, '#ffffff', 0.4)


def draw_star(sv, cx, cy, r, fill, op):
    """Draw a 5-pointed star."""
    pts = []
    for i in range(10):
        a = math.pi / 2 + i * math.pi / 5
        ri = r if i % 2 == 0 else r * 0.4
        pts.append(f"{cx + ri * math.cos(a):.1f},{cy - ri * math.sin(a):.1f}")
    sv.pa("M" + " L".join(pts) + "Z", fill=fill, op=op)


def deco_torpedo(sv):
    """Torpedo/missile styling for narwhal."""
    # Fins on body (missile stabilizer fins)
    sv.pa("M350,180 L380,140 L385,185Z", fill='#778899', op=0.5)
    sv.pa("M350,330 L380,370 L385,325Z", fill='#778899', op=0.5)
    # Red nose cone
    sv.pa("M82,220 C78,210 80,195 88,190 C85,200 83,210 82,220Z", fill='#cc3333', op=0.5)
    # Rivets along body
    for i in range(8):
        x = 140 + i * 35
        sv.ci(x, 175, 2, fill='#aabbcc', op=0.3)
        sv.ci(x, 335, 2, fill='#aabbcc', op=0.3)
    # Propeller at tail
    sv.pa("M460,260 L485,240 L490,260 L485,280Z", fill='#999999', op=0.5)
    sv.ci(462, 260, 5, fill='#888888', op=0.4)


def deco_monocle(sv):
    """Monocle and top hat for classy narwhal."""
    # Monocle
    sv.ci(138, 222, 12, fill='none', stroke='#ccbb88', sw=2, op=0.7)
    sv.ci(138, 222, 10, fill='#eeeedd', op=0.1)
    # Monocle chain
    sv.pa("M148, 228 C160,240 170,255 175,270", fill='none', stroke='#ccbb88', sw=0.8, op=0.5)
    # Monocle glint
    sv.ci(134, 218, 2, fill='#ffffff', op=0.5)
    # Top hat
    sv.re(55, 100, 55, 50, rx=3, fill='#1a1a2a', op=0.7)
    sv.re(45, 148, 75, 8, rx=3, fill='#1a1a2a', op=0.7)
    sv.re(48, 144, 69, 4, rx=2, fill='#333348', op=0.5)
    # Hat band
    sv.re(56, 138, 53, 6, rx=1, fill='#884422', op=0.5)


def deco_sparkles(sv, count=18, seed=44):
    """Sparkle/glitter effects."""
    rng = random.Random(seed)
    for _ in range(count):
        sx = 80 + rng.random() * 380
        sy = 60 + rng.random() * 380
        sr = 2 + rng.random() * 5
        sv.pa(f"M{sx},{sy-sr*2} L{sx+sr*0.4},{sy-sr*0.4} L{sx+sr*2},{sy} L{sx+sr*0.4},{sy+sr*0.4} "
              f"L{sx},{sy+sr*2} L{sx-sr*0.4},{sy+sr*0.4} L{sx-sr*2},{sy} L{sx-sr*0.4},{sy-sr*0.4}Z",
              fill='#ffffff', op=0.2 + rng.random() * 0.4)
        sv.ci(sx, sy, sr * 0.3, fill='#ffffff', op=0.5)


def deco_babies_around(sv):
    """Tiny baby unicorn silhouettes around the main unicorn."""
    babies = [(120, 400, 0.35, 0), (410, 380, 0.30, 1), (380, 430, 0.25, 1)]
    for bx, by, sc, flip in babies:
        tx = f'translate({bx},{by}) scale({"-" if flip else ""}{sc},{sc})'
        sv.gs(tx=tx)
        # Tiny unicorn body
        sv.el(0, 0, 40, 25, fill='#e8d0f0', op=0.6)
        # Head
        sv.ci(-28, -15, 18, fill='#eeddff', op=0.6)
        # Horn
        sv.pa("M-30,-30 L-35,-50 L-25,-32Z", fill='#ffd700', op=0.5)
        # Eye
        sv.ci(-30, -18, 4, fill='#000000', op=0.4)
        sv.ci(-31, -19, 1.5, fill='#ffffff', op=0.5)
        # Legs
        for lx in [-15, -5, 10, 20]:
            sv.re(lx, 18, 6, 20, fill='#ddc8e8', op=0.5)
        sv.ge()


def deco_gems(sv):
    """Scattered gems/coins for greedy unicorn."""
    gems = [(130, 420, '#ff4444', 8), (170, 440, '#44ff44', 7), (400, 410, '#4444ff', 9),
            (350, 445, '#ffcc00', 8), (420, 430, '#ff44ff', 6), (280, 455, '#ffcc00', 10)]
    for gx, gy, gc, gs in gems:
        # Diamond shape
        sv.pa(f"M{gx},{gy-gs} L{gx+gs*0.7},{gy} L{gx},{gy+gs} L{gx-gs*0.7},{gy}Z",
              fill=gc, op=0.5)
        sv.pa(f"M{gx},{gy-gs} L{gx+gs*0.3},{gy-gs*0.2} L{gx},{gy+gs*0.5}Z",
              fill=lighten(gc, 0.4), op=0.4)
        sv.ci(gx - gs * 0.15, gy - gs * 0.3, gs * 0.15, fill='#ffffff', op=0.4)


def deco_buzz_lines(sv):
    """Annoying buzz/vibration lines."""
    for i in range(8):
        y = 140 + i * 35
        x = 100 + (i % 3) * 15
        w = 30 + (i % 4) * 10
        sv.pa(f"M{x},{y} C{x+w*0.3},{y-5} {x+w*0.7},{y+5} {x+w},{y}",
              fill='none', stroke='#44aa44', sw=1.5, op=0.25)
    # Musical notes
    for nx, ny in [(130, 120), (400, 160), (140, 350)]:
        sv.ci(nx, ny, 4, fill='#33aa55', op=0.3)
        sv.pa(f"M{nx+4},{ny} L{nx+4},{ny-18} L{nx+12},{ny-15}",
              fill='none', stroke='#33aa55', sw=1.5, op=0.3)


def deco_speed_lines(sv):
    """Speed/motion lines for swift unicorn."""
    for i in range(12):
        y = 100 + i * 30
        x2 = 80 + (i % 3) * 20
        w = 60 + (i % 5) * 20
        sv.pa(f"M{x2},{y} L{x2+w},{y}", fill='none', stroke='#6688bb', sw=1.5, op=0.2)
    # Wind swoosh
    sv.pa("M90,200 C110,195 130,198 140,210", fill='none', stroke='#88aadd', sw=2, op=0.25)
    sv.pa("M85,260 C105,255 125,260 135,275", fill='none', stroke='#88aadd', sw=2, op=0.20)


def deco_magic_sparkles(sv):
    """Magic sparkle trail from horn."""
    rng = random.Random(66)
    # Trail from horn tip
    trail_x = [148, 130, 115, 95, 80, 70, 65, 70, 82, 100, 125]
    trail_y = [50, 45, 48, 58, 75, 98, 125, 155, 180, 195, 200]
    for i in range(len(trail_x)):
        t = i / (len(trail_x) - 1)
        sr = 3 + (1 - t) * 8
        op = 0.15 + (1 - t) * 0.35
        c = ['#cc88ff', '#ff88cc', '#88ccff', '#ffcc88'][i % 4]
        sv.ci(trail_x[i], trail_y[i], sr, fill=c, op=op)
    deco_sparkles(sv, count=12, seed=66)


def deco_rainbow_trail(sv):
    """Rainbow trail behind majestic flying unicorn."""
    colors = ['#ff0000', '#ff8800', '#ffff00', '#00cc00', '#0066ff', '#8800cc']
    for i, c in enumerate(colors):
        y = 355 + i * 8
        sv.pa(f"M80,{y} C150,{y-15} 250,{y-18} 380,{y-5} C420,{y} 450,{y+8} 470,{y+15}",
              fill='none', stroke=c, sw=5, op=0.3)
    # Rainbow sparkles
    rng = random.Random(77)
    for _ in range(10):
        rx = 100 + rng.random() * 350
        ry = 350 + rng.random() * 60
        c = colors[rng.randint(0, 5)]
        sv.ci(rx, ry, 2 + rng.random() * 3, fill=c, op=0.25)


# ═══════════════════════════════════════════════════════════════
#  Type Card Illustrations (non-creature)
# ═══════════════════════════════════════════════════════════════

def draw_upgrade_card(sv, variant):
    """Upward arrow with sparkles and green energy."""
    rng = random.Random(100 + variant)
    # Background glow
    glow = sv.rg(256, 256, 200, [(0, '#33cc66', 0.15), (1, '#33cc66', 0)])
    sv.ci(256, 256, 200, fill=f'url(#{glow})')

    # Large upward arrow
    ag = sv.lg(256, 100, 256, 420, [(0, '#44ff88', 1), (0.5, '#22cc55', 1), (1, '#118833', 1)])
    sv.pa("M256,80 L360,220 L310,220 L310,420 L202,420 L202,220 L152,220Z", fill=f'url(#{ag})')
    # Arrow highlight
    sv.pa("M256,95 L340,215 L300,215 L300,410 L256,410Z", fill='#55ffaa', op=0.3)
    # Arrow outline
    sv.pa("M256,80 L360,220 L310,220 L310,420 L202,420 L202,220 L152,220Z",
          fill='none', stroke='#118833', sw=2.5, op=0.5)

    # Stars around
    for _ in range(6):
        draw_star(sv, 100 + rng.random() * 312, 80 + rng.random() * 350, 8 + rng.random() * 8,
                  '#ffdd44', 0.3 + rng.random() * 0.3)

    # Energy particles
    for _ in range(15):
        px = 150 + rng.random() * 212
        py = 80 + rng.random() * 350
        pr = 2 + rng.random() * 4
        sv.ci(px, py, pr, fill='#88ffbb', op=0.2 + rng.random() * 0.3)

    # Plus symbols
    for _ in range(4):
        px = 100 + rng.random() * 312
        py = 100 + rng.random() * 300
        sz = 6 + rng.random() * 6
        sv.pa(f"M{px-sz},{py} L{px+sz},{py} M{px},{py-sz} L{px},{py+sz}",
              fill='none', stroke='#33cc66', sw=2, op=0.3)


def draw_downgrade_card(sv, variant):
    """Downward arrow with red danger effects."""
    rng = random.Random(200 + variant)
    # Background glow
    glow = sv.rg(256, 256, 200, [(0, '#cc3333', 0.15), (1, '#cc3333', 0)])
    sv.ci(256, 256, 200, fill=f'url(#{glow})')

    # Downward arrow
    ag = sv.lg(256, 80, 256, 420, [(0, '#881122', 1), (0.5, '#cc2233', 1), (1, '#ff4455', 1)])
    sv.pa("M256,432 L152,292 L202,292 L202,92 L310,92 L310,292 L360,292Z", fill=f'url(#{ag})')
    sv.pa("M256,418 L172,295 L212,295 L212,100 L256,100Z", fill='#ff6677', op=0.25)
    sv.pa("M256,432 L152,292 L202,292 L202,92 L310,92 L310,292 L360,292Z",
          fill='none', stroke='#881122', sw=2.5, op=0.5)

    # Warning symbols
    for _ in range(4):
        wx = 100 + rng.random() * 312
        wy = 100 + rng.random() * 300
        ws = 10 + rng.random() * 10
        sv.pa(f"M{wx},{wy-ws} L{wx+ws*0.87},{wy+ws*0.5} L{wx-ws*0.87},{wy+ws*0.5}Z",
              fill='none', stroke='#ffaa00', sw=2, op=0.3)
        sv.tx(wx, wy + ws * 0.3, '!', fill='#ffaa00', fs=int(ws), anchor='middle')

    # Crack lines
    for _ in range(5):
        cx = 150 + rng.random() * 212
        cy = 150 + rng.random() * 200
        sv.pa(f"M{cx},{cy} L{cx+15-rng.random()*30},{cy+20} L{cx+20-rng.random()*40},{cy+40}",
              fill='none', stroke='#aa2233', sw=1.5, op=0.3)


def draw_magic_card(sv, variant):
    """Magic wand with sparkle effects."""
    rng = random.Random(300 + variant)
    # Background magic glow
    glow = sv.rg(256, 230, 180, [(0, '#6644cc', 0.18), (1, '#6644cc', 0)])
    sv.ci(256, 230, 180, fill=f'url(#{glow})')

    # Wand
    wg = sv.lg(180, 380, 320, 120, [(0, '#553322', 1), (0.8, '#7a5533', 1), (1, '#aa8844', 1)])
    sv.pa("M185,400 L310,135 L318,140 L193,405Z", fill=f'url(#{wg})')
    # Wand highlight
    sv.pa("M188,398 L312,137", fill='none', stroke='#bb9955', sw=1.5, op=0.4)
    # Wand star tip
    draw_star(sv, 314, 132, 18, '#ffd700', 0.8)
    draw_star(sv, 314, 132, 12, '#ffee88', 0.5)
    # Tip glow
    tg = sv.rg(314, 132, 40, [(0, '#ffee88', 0.5), (1, '#ffee88', 0)])
    sv.ci(314, 132, 40, fill=f'url(#{tg})')

    # Sparkle trail from wand tip
    for i in range(20):
        t = i / 19
        angle = t * math.pi * 3 + variant * 0.5
        r = 30 + t * 100
        px = 314 + math.cos(angle) * r * 0.6
        py = 132 + math.sin(angle) * r * 0.4 + t * 80
        ps = 2 + (1 - t) * 6
        c = ['#cc88ff', '#ff88cc', '#88ccff', '#ffcc88'][i % 4]
        sv.ci(px, py, ps, fill=c, op=0.15 + (1 - t) * 0.35)

    # Magic swirls
    for j in range(3):
        pts = []
        for i in range(20):
            t = i / 19
            a = t * math.pi * 2 + j * math.pi * 2 / 3
            r = 60 + t * 80
            x = 280 + math.cos(a) * r
            y = 230 + math.sin(a) * r * 0.6
            pts.append(f"{x:.0f},{y:.0f}")
        sv.pa("M" + " L".join(pts), fill='none', stroke='#8866cc', sw=1.5, op=0.2)


def draw_instant_card(sv, variant):
    """Lightning bolt with speed effects."""
    rng = random.Random(400 + variant)
    # Background energy
    glow = sv.rg(256, 256, 200, [(0, '#ddaa22', 0.15), (1, '#ddaa22', 0)])
    sv.ci(256, 256, 200, fill=f'url(#{glow})')

    # Lightning bolt
    lg = sv.lg(256, 60, 256, 460, [(0, '#ffee55', 1), (0.5, '#ffcc22', 1), (1, '#cc8800', 1)])
    sv.pa("M290,60 L220,220 L280,215 L210,460 L340,245 L275,250 L350,60Z", fill=f'url(#{lg})')
    sv.pa("M288,70 L225,218 L278,213 L215,448 L330,248 L276,252 L345,70Z",
          fill='#ffff88', op=0.35)
    sv.pa("M290,60 L220,220 L280,215 L210,460 L340,245 L275,250 L350,60Z",
          fill='none', stroke='#cc8800', sw=2, op=0.5)

    # Electric arcs
    for _ in range(6):
        x1 = 200 + rng.random() * 112
        y1 = 100 + rng.random() * 300
        pts = [f"{x1:.0f},{y1:.0f}"]
        for _ in range(4):
            x1 += -15 + rng.random() * 30
            y1 += 5 + rng.random() * 15
            pts.append(f"{x1:.0f},{y1:.0f}")
        sv.pa("M" + " L".join(pts), fill='none', stroke='#ffdd44', sw=1.5, op=0.3)

    # Energy particles
    for _ in range(15):
        px = 100 + rng.random() * 312
        py = 60 + rng.random() * 400
        sv.ci(px, py, 1.5 + rng.random() * 3, fill='#ffee44', op=0.2 + rng.random() * 0.3)


def draw_neigh_card(sv, variant):
    """Horseshoe with NEIGH text and stop effect."""
    rng = random.Random(500 + variant)
    # Background
    glow = sv.rg(256, 256, 200, [(0, '#888888', 0.12), (1, '#888888', 0)])
    sv.ci(256, 256, 200, fill=f'url(#{glow})')

    # Large horseshoe
    hg = sv.lg(256, 100, 256, 380, [(0, '#aaaaaa', 1), (0.5, '#888888', 1), (1, '#555555', 1)])
    sv.pa("M180,350 C170,250 180,170 256,130 C332,170 342,250 332,350 "
          "L312,350 C318,260 310,190 256,160 C202,190 194,260 200,350Z", fill=f'url(#{hg})')
    # Horseshoe nail holes
    for (nx, ny) in [(195, 300), (195, 240), (220, 180), (292, 180), (317, 240), (317, 300)]:
        sv.ci(nx, ny, 5, fill='#444444', op=0.3)
        sv.ci(nx, ny, 3, fill='#666666', op=0.4)

    # Horseshoe shine
    sv.pa("M185,340 C178,260 188,180 256,142", fill='none', stroke='#cccccc', sw=2, op=0.3)

    # Stop/cancel effect (red X behind)
    sv.pa("M140,140 L372,372 M372,140 L140,372", fill='none', stroke='#cc3333', sw=8, op=0.15)

    # NEIGH text
    sv.tx(256, 430, "NEIGH!", fill='#555555', fs=42, fw='bold')

    # Dust clouds
    for _ in range(5):
        dx = 130 + rng.random() * 252
        dy = 380 + rng.random() * 60
        dr = 15 + rng.random() * 20
        dg = sv.rg(dx, dy, dr, [(0, '#999999', 0.15), (1, '#999999', 0)])
        sv.ci(dx, dy, dr, fill=f'url(#{dg})')


def draw_super_neigh_card(sv, variant):
    """Enhanced horseshoe with dramatic SUPER NEIGH effect."""
    rng = random.Random(600 + variant)
    # Background energy
    glow = sv.rg(256, 256, 220, [(0, '#8833cc', 0.18), (1, '#8833cc', 0)])
    sv.ci(256, 256, 220, fill=f'url(#{glow})')

    # Large dramatic horseshoe
    hg = sv.lg(256, 80, 256, 380, [(0, '#bb88ff', 1), (0.5, '#8855cc', 1), (1, '#553388', 1)])
    sv.pa("M170,350 C158,240 170,155 256,110 C342,155 354,240 342,350 "
          "L318,350 C326,250 316,175 256,142 C196,175 186,250 194,350Z", fill=f'url(#{hg})')

    # Energy aura
    for i in range(3):
        r = 160 + i * 25
        ag = sv.rg(256, 240, r, [(0.7, '#aa66ff', 0.08 - i * 0.02), (1, '#aa66ff', 0)])
        sv.ci(256, 240, r, fill=f'url(#{ag})')

    # Horseshoe glow/shine
    sv.pa("M175,340 C165,250 178,165 256,122", fill='none', stroke='#ddbbff', sw=2.5, op=0.4)

    # Nail holes with glow
    for (nx, ny) in [(190, 300), (190, 235), (215, 172), (297, 172), (322, 235), (322, 300)]:
        ng = sv.rg(nx, ny, 8, [(0, '#aa66ff', 0.4), (1, '#aa66ff', 0)])
        sv.ci(nx, ny, 8, fill=f'url(#{ng})')
        sv.ci(nx, ny, 4, fill='#553388', op=0.4)

    # Large X cancel
    sv.pa("M130,130 L382,382 M382,130 L130,382", fill='none', stroke='#cc2244', sw=10, op=0.2)

    # SUPER NEIGH text
    sv.tx(256, 410, "SUPER", fill='#8833cc', fs=32, fw='bold')
    sv.tx(256, 450, "NEIGH!", fill='#aa55ee', fs=38, fw='bold')

    # Dramatic sparkles
    deco_sparkles(sv, count=15, seed=600 + variant)

    # Lightning arcs from horseshoe
    for _ in range(4):
        x1 = 180 + rng.random() * 152
        y1 = 130 + rng.random() * 100
        pts = [f"{x1:.0f},{y1:.0f}"]
        for _ in range(3):
            x1 += -20 + rng.random() * 40
            y1 += -10 + rng.random() * 20
            pts.append(f"{x1:.0f},{y1:.0f}")
        sv.pa("M" + " L".join(pts), fill='none', stroke='#bb88ff', sw=1.5, op=0.3)


# ═══════════════════════════════════════════════════════════════
#  Card Definitions & Generation
# ═══════════════════════════════════════════════════════════════

CARDS = {
    # ── Unique Unicorns ──
    "zombie_unicorn": {
        "t": "unicorn",
        "p": {"body": "#6b8c5a", "mane": "#354525", "horn": "#a0a060", "hoof": "#3a3a2a",
              "eye": "#cc3333", "nose": "#3f5530", "cheek": "#8faa7f"},
        "x": ["zombie"],
    },
    "unicorn_phoenix": {
        "t": "unicorn",
        "p": {"body": "#cc4422", "mane": "#ff8800", "tail": "#ffaa00", "horn": "#ffe066",
              "hoof": "#442200", "eye": "#ff6600", "cheek": "#ff9966"},
        "x": ["flames"],
    },
    "shark_with_a_horn": {
        "t": "narwhal",
        "p": {"body": "#607080", "belly": "#c0c8d0", "horn": "#e0e0e0", "eye": "#1a1a2a"},
        "x": ["shark"],
    },
    "mermaid_unicorn": {
        "t": "unicorn",
        "p": {"body": "#7ec8c8", "mane": "#3a8888", "horn": "#ffd700", "hoof": "#338888",
              "eye": "#006666", "cheek": "#66cccc"},
        "x": ["mermaid"],
    },
    "llamacorn": {
        "t": "unicorn",
        "p": {"body": "#d4a860", "mane": "#8b6b3a", "horn": "#ffd700", "hoof": "#4a3a2a",
              "eye": "#4a3210", "cheek": "#e8c088"},
        "x": ["llama"],
    },
    "rhinocorn": {
        "t": "unicorn",
        "p": {"body": "#909090", "mane": "#555555", "horn": "#b0b0a0", "hoof": "#333333",
              "eye": "#3a3a3a", "cheek": "#aaaaaa"},
        "x": ["armor_plates"],
    },
    "black_knight_unicorn": {
        "t": "unicorn",
        "p": {"body": "#2a2a35", "mane": "#1a1a25", "horn": "#808090", "hoof": "#111115",
              "eye": "#cc0000", "cheek": "#3a3a45"},
        "x": ["armor"],
    },
    "stabby_the_unicorn": {
        "t": "unicorn",
        "p": {"body": "#e0c8e8", "mane": "#cc66dd", "horn": "#dda0dd", "hoof": "#555555",
              "eye": "#cc3366", "cheek": "#ffccdd"},
        "x": ["knife"],
    },
    "chainsaw_unicorn": {
        "t": "unicorn",
        "p": {"body": "#d0b888", "mane": "#aa7744", "horn": "#cc8833", "hoof": "#3a3022",
              "eye": "#884400", "cheek": "#e8cc99"},
        "x": ["chainsaw"],
    },
    "dark_angel_unicorn": {
        "t": "unicorn",
        "p": {"body": "#3a2a4a", "mane": "#1a1030", "horn": "#8866aa", "hoof": "#1a1020",
              "eye": "#9933cc", "cheek": "#5a4a6a"},
        "x": ["dark_wings"],
    },
    "queen_bee_unicorn": {
        "t": "unicorn",
        "p": {"body": "#ffcc33", "mane": "#332200", "horn": "#ffd700", "hoof": "#1a1100",
              "eye": "#664400", "cheek": "#ffdd66"},
        "x": ["crown_head", "bee_stripes"],
    },
    "unicorn_on_the_cob": {
        "t": "unicorn",
        "p": {"body": "#e8d44a", "mane": "#558833", "horn": "#ccaa22", "hoof": "#338822",
              "eye": "#446600", "cheek": "#eedd66"},
        "x": ["corn"],
    },
    "seductive_unicorn": {
        "t": "unicorn",
        "p": {"body": "#e8b8c8", "mane": "#cc3366", "horn": "#ff66aa", "hoof": "#663344",
              "eye": "#cc2255", "cheek": "#ff99bb"},
        "x": ["hearts"],
    },
    "americorn": {
        "t": "unicorn",
        "p": {"body": "#dde8f8", "mane": "#cc2244", "tail": "#2244aa", "horn": "#ffd700",
              "hoof": "#1a1a3a", "eye": "#2244aa", "cheek": "#ffccdd"},
        "x": ["stars_stripes"],
    },
    "narwhal_torpedo": {
        "t": "narwhal",
        "p": {"body": "#556677", "belly": "#aabbcc", "horn": "#cc3333", "eye": "#1a1a2a"},
        "x": ["torpedo"],
    },
    "the_great_narwhal": {
        "t": "narwhal",
        "p": {"body": "#4466aa", "belly": "#c8d8e8", "horn": "#ffd700", "eye": "#1a1a3a"},
        "x": ["crown_narwhal", "sparkles_few"],
    },
    "classy_narwhal": {
        "t": "narwhal",
        "p": {"body": "#445566", "belly": "#c0c8d8", "horn": "#ccbb88", "eye": "#1a1a2a"},
        "x": ["monocle"],
    },
    "alluring_narwhal": {
        "t": "narwhal",
        "p": {"body": "#6688aa", "belly": "#d0d8e8", "horn": "#ffd700", "eye": "#334466"},
        "x": ["sparkles_many"],
    },
    "extremely_fertile_unicorn": {
        "t": "unicorn",
        "p": {"body": "#e8c8d8", "mane": "#cc88aa", "horn": "#ffaacc", "hoof": "#884466",
              "eye": "#cc4488", "cheek": "#ffccdd"},
        "x": ["babies"],
    },
    "greedy_flying_unicorn": {
        "t": "unicorn",
        "p": {"body": "#ddc888", "mane": "#886622", "horn": "#ffd700", "hoof": "#443300",
              "eye": "#886622", "cheek": "#eedd99", "wing": "#e8ddb8"},
        "x": ["wings", "gems"],
    },
    "annoying_flying_unicorn": {
        "t": "unicorn",
        "p": {"body": "#88cc88", "mane": "#33aa55", "horn": "#88dd88", "hoof": "#225522",
              "eye": "#228833", "cheek": "#99dd99", "wing": "#aaddaa"},
        "x": ["wings", "buzz"],
    },
    "swift_flying_unicorn": {
        "t": "unicorn",
        "p": {"body": "#c8d8e8", "mane": "#6688bb", "horn": "#aaccee", "hoof": "#334466",
              "eye": "#3355aa", "cheek": "#ddeeff", "wing": "#dde8f8"},
        "x": ["wings", "speed"],
    },
    "magical_flying_unicorn": {
        "t": "unicorn",
        "p": {"body": "#c8b8e8", "mane": "#7744cc", "horn": "#cc88ff", "hoof": "#332266",
              "eye": "#6633cc", "cheek": "#ddccff", "wing": "#ddd0f0"},
        "x": ["wings", "magic_trail"],
    },
    "majestic_flying_unicorn": {
        "t": "unicorn",
        "p": {"body": "#e8e0f8", "mane": "#8866cc", "tail": "#aa88dd", "horn": "#ffd700",
              "hoof": "#443366", "eye": "#5533aa", "cheek": "#eeddff", "wing": "#f0e8ff"},
        "x": ["wings", "rainbow"],
    },

    # ── Generic Unicorns ──
    "unicorn_generic_0": {
        "t": "unicorn",
        "p": {"body": "#c8b8e8", "mane": "#8866bb", "horn": "#ffd700", "hoof": "#333355",
              "eye": "#4444aa", "cheek": "#ddccee"},
    },
    "unicorn_generic_1": {
        "t": "unicorn",
        "p": {"body": "#b8d8e8", "mane": "#5588aa", "horn": "#e8cc44", "hoof": "#334455",
              "eye": "#3366aa", "cheek": "#ccddee"},
    },
    "unicorn_generic_2": {
        "t": "unicorn",
        "p": {"body": "#e8c8d8", "mane": "#aa6688", "horn": "#ffcc55", "hoof": "#553344",
              "eye": "#aa4488", "cheek": "#eeddee"},
    },
    "unicorn_generic_3": {
        "t": "unicorn",
        "p": {"body": "#d8e8c8", "mane": "#668844", "horn": "#ddbb33", "hoof": "#334422",
              "eye": "#448833", "cheek": "#ddeedd"},
    },

    # ── Baby Unicorns ──
    "baby_unicorn_0": {
        "t": "baby",
        "p": {"body": "#e8d8f8", "mane": "#bb88dd", "horn": "#ffd700", "hoof": "#554466",
              "eye": "#7755cc", "cheek": "#ffccee"},
    },
    "baby_unicorn_1": {
        "t": "baby",
        "p": {"body": "#d8e8f8", "mane": "#88aadd", "horn": "#ffe066", "hoof": "#445566",
              "eye": "#5588cc", "cheek": "#ccddff"},
    },
    "baby_unicorn_2": {
        "t": "baby",
        "p": {"body": "#f8e8d8", "mane": "#dd9966", "horn": "#ffcc44", "hoof": "#665544",
              "eye": "#cc7744", "cheek": "#ffddcc"},
    },
    "baby_unicorn_3": {
        "t": "baby",
        "p": {"body": "#e8f8e8", "mane": "#66bb77", "horn": "#ddcc33", "hoof": "#335544",
              "eye": "#449955", "cheek": "#ccffcc"},
    },
}

# Type cards (4 variants each)
for kind in ['upgrade', 'downgrade', 'magic', 'instant', 'neigh', 'super_neigh']:
    for v in range(4):
        CARDS[f"{kind}_{v}"] = {"t": kind, "p": {}, "x": [], "v": v}


def apply_extras(sv, extras, pal):
    """Apply card-specific decoration functions."""
    for ex in extras:
        if ex == 'zombie': deco_zombie(sv)
        elif ex == 'flames': deco_flames(sv)
        elif ex == 'shark': deco_shark_features(sv)
        elif ex == 'mermaid': deco_mermaid_tail(sv)
        elif ex == 'llama': deco_llama_wool(sv)
        elif ex == 'armor_plates': deco_armor_plates(sv)
        elif ex == 'armor': deco_armor(sv)
        elif ex == 'knife': deco_knife(sv)
        elif ex == 'chainsaw': deco_chainsaw(sv)
        elif ex == 'dark_wings': deco_dark_wings(sv)
        elif ex == 'crown_head': deco_crown(sv, 168, 68)
        elif ex == 'bee_stripes': deco_bee_stripes(sv)
        elif ex == 'corn': deco_corn_husk(sv)
        elif ex == 'hearts': deco_hearts(sv)
        elif ex == 'stars_stripes': deco_stars_stripes(sv)
        elif ex == 'torpedo': deco_torpedo(sv)
        elif ex == 'crown_narwhal': deco_crown(sv, 110, 145)
        elif ex == 'monocle': deco_monocle(sv)
        elif ex == 'sparkles_few': deco_sparkles(sv, 10, 88)
        elif ex == 'sparkles_many': deco_sparkles(sv, 22, 55)
        elif ex == 'babies': deco_babies_around(sv)
        elif ex == 'wings': draw_wings(sv, pal)
        elif ex == 'gems': deco_gems(sv)
        elif ex == 'buzz': deco_buzz_lines(sv)
        elif ex == 'speed': deco_speed_lines(sv)
        elif ex == 'magic_trail': deco_magic_sparkles(sv)
        elif ex == 'rainbow': deco_rainbow_trail(sv)


def generate_card(name, cfg):
    """Generate a single card SVG."""
    sv = S(512, 512)
    t = cfg['t']
    pal = cfg.get('p', {})
    extras = cfg.get('x', [])
    variant = cfg.get('v', 0)

    if t == 'unicorn':
        # Draw wings BEFORE body if needed (behind the body)
        if 'wings' in extras:
            draw_wings(sv, pal)
        unicorn_body(sv, pal)
        apply_extras(sv, [e for e in extras if e != 'wings'], pal)
    elif t == 'narwhal':
        narwhal_body(sv, pal)
        apply_extras(sv, extras, pal)
    elif t == 'baby':
        baby_body(sv, pal)
    elif t == 'upgrade':
        draw_upgrade_card(sv, variant)
    elif t == 'downgrade':
        draw_downgrade_card(sv, variant)
    elif t == 'magic':
        draw_magic_card(sv, variant)
    elif t == 'instant':
        draw_instant_card(sv, variant)
    elif t == 'neigh':
        draw_neigh_card(sv, variant)
    elif t == 'super_neigh':
        draw_super_neigh_card(sv, variant)

    sv.save(f"{name}.svg")


# ═══════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print(f"Generating {len(CARDS)} SVG card illustrations...")
    print(f"Output: {OUT_DIR}\n")

    for name, cfg in sorted(CARDS.items()):
        generate_card(name, cfg)

    print(f"\nDone! Generated {len(CARDS)} SVGs.")
    # List files
    svgs = [f for f in os.listdir(OUT_DIR) if f.endswith('.svg') and f != 'basic_unicorn.svg']
    print(f"Files in output dir: {len(svgs)} SVGs (plus basic_unicorn.svg example)")
