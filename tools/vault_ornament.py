"""The vault ornament round the opening arch (first-arch idea 1, chosen by Maria): the painted
vault of the Stanza della Segnatura as it shows in the fresco scan's margins, figure-free and
redrawn clean as vectors, painted on the front wall itself.

On the front wall, outside the arch's dark red outer band:
- a band of gold interlace on blue following the arch (a chain of endless knots linked by
  figure-of-eight twists, the vault's knotwork borders);
- a gilt rosette in a white roundel at +-50 degrees, where the vault's ribs meet the lunette frame;
- a pale rib from each roundel out to the top of the wall (white, with a cable moulding);
- under each rib a blue field framed in white with a gold fillet, holding a gold oak with acorns
  (the della Rovere oak of the vault's triangles) on a branching trunk.
No figures, no faces, no animals. Nothing is copied from the scan: it was studied for the motifs,
their proportions and the colours (the blue below is the scan's ultramarine).

It is the front wall's own detail tile ("vault_front", make_detail.py calls tile()), mapped once
over the wall round the arch (bake.detail_uvs, "uv_origin"), so the baked light falls across it
and the wall's marble grain runs through the paint. The ribs, the roundels, the rosettes and the
fields' frames are also built in relief (finish2.vault_relief, from blender/scripts/vault_geom.py,
where the design's numbers live): the tile paints their fronts, its top strip their sides.
The gold is modelled in paint, lit from the sun's side, as the meander's depth and the scroll's
grisaille are; the tile's alpha marks the gold for the web's gold-leaf sheen (Scene.tsx).

Geometry: drawn in web metres on the wall's plane through the camera solve, like the arch
(finish2.opening_arch): a point seen at scan px (u, v) lies at x = (u - CX) K,
y = EYE - (v - CY) K, K = wall distance / F_PX. The design is symmetric about the arch's axis:
the left half is drawn and mirrored; the painted light is not mirrored.

Colours are paint (sRGB as under the hall's nominal light, the convention of
params.ARCH_COLOURS): the gold is matched to the arch's (divided by the wall's baked light, as the
arch's band tile is by the arch's); the white and the blue keep the look Maria chose (the decal
showed them at the wall's light, 0.734).

Usage: python -I tools/vault_ornament.py <preview.png>   (make_detail.py ships the real tile)
"""
import math
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "blender" / "scripts"))
import params as P  # noqa: E402
import vault_geom as G  # noqa: E402

XC, YC, R0, YS, EYE = G.XC, G.YC, G.R0, G.YS, G.EYE
R_IN = R0 - 0.002                  # the paint runs on 2 mm under the band
HALF_TAN = math.tan(math.radians(42))
SHIFT = (1933.3 - 1920) / 1920
VIEW_LEFT = -(HALF_TAN + SHIFT * HALF_TAN) * G.PLANE - XC   # < 0, from the axis
VIEW_TOP_169 = EYE + 0.676 * G.PLANE                        # top of a 16:9 view

# The canvas: the left half, axis at the right edge.
HW = G.HW
PPM = G.PPM
TEX_W, TEX_H = G.TEX_W // 2, G.TEX_H_DRAW
Y0, Y1 = G.Y0, G.Y1
XL = XC - HW
SS = 4                             # supersampling for the drawn motifs

BAND = G.BAND
RB_BLUE0, RB_BLUE1, RB = G.RB_BLUE0, G.RB_BLUE1, G.RB
RIB_DEG, RIB_W, ROUNDEL_R, FRAME_W, FILLET = G.RIB_DEG, G.RIB_W, G.ROUNDEL_R, G.FRAME_W, G.FILLET
LINE_W = 0.0025                    # grey drawing lines
KNOT_STROKE = 0.0064               # gold interlace

# Paint, sRGB under the nominal light (ARCH_COLOURS convention).
WHITE = (235, 229, 210)            # ribs, frames, fillets: a little whiter than the hall's cream
LINE = (148, 136, 116)             # grey drawing lines on the white
# Ultramarine of the vault's blue fields, from the scan: the median of the field round the oak in
# the right-hand triangle (athens-original.jpg at half size, box 9400-10056 x 1150-1950) is
# (29, 47, 91), and the vault's white stucco in the same box (186, 167, 169). The blue keeps its
# ratio to that white's luminance (the white read as neutral: its pink is the fresco's age),
# set against WHITE: (42, 66, 124).
SCAN_BLUE, SCAN_WHITE = (29, 47, 91), (186, 167, 169)
GOLD = tuple(P.ARCH_COLOURS["gold"])          # (194, 150, 62), the arch's gold leaf
GOLD_SHADE = tuple(P.ARCH_COLOURS["gold_shade"])
GOLD_LIGHT = (228, 192, 112)
GOLD_CUP = (166, 124, 48)            # the acorns' cups, between the gold and its shade
GOLDS = {GOLD, GOLD_SHADE, GOLD_LIGHT, GOLD_CUP}

# ------------------------------------------------------------------ rasterising
ix = (np.arange(TEX_W) + 0.5) / PPM + XL
iy = Y1 - (np.arange(TEX_H) + 0.5) / PPM
X, Y = np.meshgrid(ix, iy)
RHO = np.hypot(X - XC, Y - YC)


def cov(d):
    """Coverage of the region d > 0 (d a signed distance in metres), box-filtered over a pixel."""
    return np.clip(d * PPM + 0.5, 0.0, 1.0)


def ring(d, a, b):
    """Coverage of a < d < b."""
    return np.clip(cov(d - a) - cov(d - b), 0.0, 1.0)


def lin(c):
    c = np.asarray(c, np.float64) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def srgb8(x):
    x = np.clip(x, 0, 1)
    s = np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)
    return np.clip(np.round(s * 255), 0, 255).astype(np.uint8)


LUMA = np.array([0.2126, 0.7152, 0.0722])
BLUE = tuple(int(c) for c in srgb8(lin(SCAN_BLUE) * (lin(WHITE) @ LUMA) / (lin(SCAN_WHITE) @ LUMA)))


# Premultiplied, linear accumulation; GOLDM: where the paint is gold leaf.
ACC = np.zeros((TEX_H, TEX_W, 3))
ALPHA = np.zeros((TEX_H, TEX_W))
GOLDM = np.zeros((TEX_H, TEX_W))


def over(colour, c):
    global ACC, ALPHA, GOLDM
    c = np.clip(c, 0, 1)
    ACC = ACC * (1 - c[..., None]) + lin(colour) * c[..., None]
    ALPHA = ALPHA * (1 - c) + c
    GOLDM = GOLDM * (1 - c) + c * (1.0 if tuple(colour) in GOLDS else 0.0)


class Pen:
    """A supersampled mask: shapes in metres on the plane, read back as pixel coverage."""

    def __init__(self):
        self.im = Image.new("L", (TEX_W * SS, TEX_H * SS), 0)
        self.d = ImageDraw.Draw(self.im)

    @staticmethod
    def xy(p):
        return ((p[0] - XL) * PPM * SS, (Y1 - p[1]) * PPM * SS)

    def poly(self, pts, fill=255):
        if len(pts) >= 3:
            self.d.polygon([self.xy(p) for p in pts], fill=fill)

    def line(self, pts, w, fill=255, caps=True):
        q = [self.xy(p) for p in pts]
        wpx = max(1, round(w * PPM * SS))
        self.d.line(q, fill=fill, width=wpx, joint="curve")
        if caps:
            r = wpx / 2
            for x, y in (q[0], q[-1]):
                self.d.ellipse((x - r, y - r, x + r, y + r), fill=fill)

    def disc(self, c, r, fill=255):
        x, y = self.xy(c)
        rp = r * PPM * SS
        self.d.ellipse((x - rp, y - rp, x + rp, y + rp), fill=fill)

    def cov(self):
        return np.asarray(self.im.reduce(SS), np.float64) / 255.0


class Painter:
    """Opaque shapes in painter's order (later ones cover earlier ones) in a local box, in metres
    on the plane; supersampled, averaged in linear light, then laid over the texture."""

    def __init__(self, x0, y0, x1, y1, ss=6):
        self.i0 = max(0, int((x0 - XL) * PPM) - 2)
        self.i1 = min(TEX_W, int((x1 - XL) * PPM) + 3)
        self.j0 = max(0, int((Y1 - y1) * PPM) - 2)
        self.j1 = min(TEX_H, int((Y1 - y0) * PPM) + 3)
        self.ss = ss
        size = ((self.i1 - self.i0) * ss, (self.j1 - self.j0) * ss)
        self.rgb = Image.new("RGB", size, (0, 0, 0))
        self.a = Image.new("L", size, 0)
        self.dr, self.da = ImageDraw.Draw(self.rgb), ImageDraw.Draw(self.a)

    def xy(self, p):
        return (((p[0] - XL) * PPM - self.i0) * self.ss, ((Y1 - p[1]) * PPM - self.j0) * self.ss)

    def w(self, metres):
        return max(1, round(metres * PPM * self.ss))

    def poly(self, pts, col, grow=0.0):
        q = [self.xy(p) for p in pts]
        if grow > 0:
            self.dr.polygon(q, fill=col, outline=col, width=self.w(2 * grow))
            self.da.polygon(q, fill=255, outline=255, width=self.w(2 * grow))
        else:
            self.dr.polygon(q, fill=col)
            self.da.polygon(q, fill=255)

    def line(self, pts, width, col, caps=True):
        q = [self.xy(p) for p in pts]
        wp = self.w(width)
        self.dr.line(q, fill=col, width=wp, joint="curve")
        self.da.line(q, fill=255, width=wp, joint="curve")
        if caps:
            r = wp / 2
            for x, y in (q[0], q[-1]):
                self.dr.ellipse((x - r, y - r, x + r, y + r), fill=col)
                self.da.ellipse((x - r, y - r, x + r, y + r), fill=255)

    def disc(self, c, r, col):
        x, y = self.xy(c)
        rp = r * PPM * self.ss
        self.dr.ellipse((x - rp, y - rp, x + rp, y + rp), fill=col)
        self.da.ellipse((x - rp, y - rp, x + rp, y + rp), fill=255)

    def lay(self, clip=None, gold=True):
        global ACC, ALPHA, GOLDM
        ss = self.ss
        a = np.asarray(self.a, np.float64) / 255.0
        rgb = lin(np.asarray(self.rgb)) * a[..., None]
        h, w = a.shape[0] // ss, a.shape[1] // ss
        pre = rgb.reshape(h, ss, w, ss, 3).mean((1, 3))
        al = a.reshape(h, ss, w, ss).mean((1, 3))
        sl = (slice(self.j0, self.j1), slice(self.i0, self.i1))
        if clip is not None:
            pre = pre * clip[sl][..., None]
            al = al * clip[sl]
        ACC[sl] = ACC[sl] * (1 - al[..., None]) + pre
        ALPHA[sl] = ALPHA[sl] * (1 - al) + al
        GOLDM[sl] = GOLDM[sl] * (1 - al) + al * (1.0 if gold else 0.0)


def bezier(p0, p1, p2, p3, n=24):
    t = np.linspace(0, 1, n)[:, None]
    p0, p1, p2, p3 = (np.asarray(p, float) for p in (p0, p1, p2, p3))
    return ((1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3)


def taper(path, w0, w1):
    """Outline of a stroke along `path` (n x 2) whose width runs from w0 to w1."""
    path = np.asarray(path, float)
    d = np.gradient(path, axis=0)
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    n = np.stack([-d[:, 1], d[:, 0]], 1)
    w = np.linspace(w0, w1, len(path))[:, None] / 2
    return np.concatenate([path + n * w, (path - n * w)[::-1]])


# ------------------------------------------------------------------ geometry of the parts
TH_RIB = -math.radians(RIB_DEG)                      # left half
E_S = np.array([math.sin(TH_RIB), math.cos(TH_RIB)])  # along the rib, outwards
N_UP = np.array([E_S[1], -E_S[0]])                   # across it, towards the crown
RC = R0 + ROUNDEL_R
ROUNDEL_C = np.array([XC, YC]) + RC * E_S
T_RIB = (X - XC) * N_UP[0] + (Y - YC) * N_UP[1]      # across the rib (> 0 crown side)
S_RIB = (X - XC) * E_S[0] + (Y - YC) * E_S[1]        # along it from the arch's centre

# The field under the rib: outside the band, below the rib, above the springing.
D_FIELD = np.minimum.reduce([RHO - RB, -T_RIB - RIB_W / 2, Y - YS])


def band():
    d = RHO - R0
    over(WHITE, ring(RHO, R_IN - 0.010, RB))   # runs on under the band: no clear texel at R0 in any mip
    over(LINE, ring(d, BAND["fil_in"], BAND["fil_in"] + BAND["line"]))
    over(BLUE, ring(RHO, RB_BLUE0, RB_BLUE1))
    over(LINE, ring(RHO, RB_BLUE1, RB_BLUE1 + BAND["line"]))
    over(LINE, ring(RHO, RB - BAND["line"], RB))


def knot_chain():
    """Endless knots linked by figure-of-eight twists, in band coordinates (u along the arc from
    the crown, v across from the blue's centre line), mapped onto the arc. Each knot: two strands
    each way on a diamond's diagonals (four crossings) and a round lobe over its top and bottom
    corners (a 270-degree arc centred on the corner, which joins the strands tangentially); its
    left and right ends run on into the next knot, crossing on the axis. A knot sits on the crown,
    so the mirrored right half continues it."""
    rm = (RB_BLUE0 + RB_BLUE1) / 2
    half = BAND["blue"] / 2
    a = (half - 0.0085) / (1 + math.sqrt(2) / 3)       # diamond half-diagonal
    e = a * math.sqrt(2) / 6                           # strands at 1/3 and 2/3 of each side
    pitch = 3.55 * a
    lobe = a * math.sqrt(2) / 3
    d1 = np.array([1.0, 1.0]) / math.sqrt(2)
    d2 = np.array([1.0, -1.0]) / math.sqrt(2)
    n1 = np.array([-1.0, 1.0]) / math.sqrt(2)
    n2 = np.array([1.0, 1.0]) / math.sqrt(2)
    t = np.linspace(-a / math.sqrt(2), a / math.sqrt(2), 12)[:, None]
    unit = []
    for dd, nn in ((d1, n1), (d2, n2)):
        for c in (e, -e):
            unit.append(t * dd + c * nn)
    for cy, a0 in ((a, -45.0), (-a, 135.0)):
        ang = np.radians(np.linspace(a0, a0 + 270.0, 60))[:, None]
        unit.append(np.hstack([lobe * np.cos(ang), cy + lobe * np.sin(ang)]))
    L = 0.62 * a
    p1, q1 = np.array([2 * a / 3, a / 3]), np.array([pitch - 2 * a / 3, -a / 3])
    p2, q2 = np.array([2 * a / 3, -a / 3]), np.array([pitch - 2 * a / 3, a / 3])
    unit.append(bezier(p1, p1 + L * d1, q1 - L * d1, q1, 40))
    unit.append(bezier(p2, p2 + L * d2, q2 - L * d2, q2, 40))
    arc_len = rm * (math.acos((YS - YC) / rm) + 0.05)
    pen = Pen()
    for k in range(-math.ceil(arc_len / pitch) - 1, 1):
        for seg in unit:
            u = seg[:, 0] + k * pitch
            v = seg[:, 1]
            th = u / rm
            r = rm + v
            pts = np.stack([XC + r * np.sin(th), YC + r * np.cos(th)], 1)
            pen.line(pts, KNOT_STROKE)
    over(GOLD, pen.cov() * ring(RHO, RB_BLUE0, RB_BLUE1))
    return dict(a=a, pitch=pitch)


def field():
    over(WHITE, cov(D_FIELD))
    over(LINE, ring(D_FIELD, FRAME_W - LINE_W, FRAME_W))
    over(BLUE, cov(D_FIELD - FRAME_W))
    f0 = FRAME_W + FILLET[0]
    over(GOLD, ring(D_FIELD, f0, f0 + FILLET[1]))


def rib():
    """The rib: white, outlined, with a cable moulding between two fillets (the twisted torus that
    frames the vault's fields): slanting strands, each shaded towards the next as it turns away."""
    beyond = cov(S_RIB - RC)
    t = np.abs(T_RIB)
    over(WHITE, cov(RIB_W / 2 - t) * beyond)
    over(LINE, ring(t, RIB_W / 2 - LINE_W, RIB_W / 2) * beyond)
    cw = 0.024                                           # the cable's half width
    over(LINE, ring(t, cw, cw + 0.0018) * beyond)
    pitch = 0.030
    ph = (S_RIB - RC) / pitch
    tt = np.clip(T_RIB / cw, -1, 1)
    q = ph - 0.85 * np.sin(np.pi / 2 * tt)               # strand edges: s = s_k + 0.85 pitch sin(pi/2 t/cw)
    frac = q - np.floor(q)
    slope = np.hypot(1.0, 0.85 * pitch * np.pi / 2 / cw * np.cos(np.pi / 2 * tt))
    dist = np.minimum(frac, 1 - frac) * pitch / slope    # to the nearest strand edge, across it
    inside = cov(cw - t) * beyond
    roll = 0.55 + 0.45 * np.cos(np.pi / 2 * tt)          # the torus turns away at its sides
    over(LINE, (0.30 * frac ** 2 + 0.12 * (1 - roll)) * inside)
    over(LINE, cov(0.0009 - dist) * inside * 0.9)


def roundel():
    """White ring with a leaf-and-tongue moulding, gold fillet, blue ground, gilt rosette."""
    cx, cy = ROUNDEL_C
    rr = np.hypot(X - cx, Y - cy)
    ang = np.arctan2(X - cx, Y - cy)
    R = ROUNDEL_R
    r_blue = 0.083
    over(WHITE, cov(R - rr))
    over(LINE, ring(rr, R - LINE_W, R))
    over(LINE, ring(rr, r_blue + 0.0055, r_blue + 0.0055 + LINE_W))
    over(GOLD, ring(rr, r_blue, r_blue + 0.0055))
    over(BLUE, cov(r_blue - rr))
    # leaf-and-tongue: 24 leaves (U outlines, tips inwards) with a dart between each pair
    n = 24
    pen = Pen()
    r_in, r_out = r_blue + 0.0115, R - 0.0065
    for k in range(n):
        phi = (k + 0.5) * 2 * math.pi / n
        e_r = np.array([math.sin(phi), math.cos(phi)])
        e_t = np.array([math.cos(phi), -math.sin(phi)])
        rho = 0.34 * 2 * math.pi * (r_in + r_out) / 2 / n          # the leaf's half width
        tip = r_in + rho
        side = np.linspace(r_out, tip, 8)[:, None]
        b = np.linspace(0, math.pi, 16)[:, None]
        u = np.concatenate([c0 + side * e_r - rho * e_t for c0 in [np.array([cx, cy])]] +
                           [np.array([cx, cy]) + tip * e_r - rho * np.cos(b) * e_t - rho * np.sin(b) * e_r] +
                           [np.array([cx, cy]) + side[::-1] * e_r + rho * e_t])
        pen.line(u, 0.0019, caps=False)
        dphi = phi + math.pi / n
        d_r = np.array([math.sin(dphi), math.cos(dphi)])
        pen.line(np.array([cx, cy]) + np.array([[r_out], [r_out - 0.015]]) * d_r, 0.0016)
    over(LINE, pen.cov() * ring(rr, r_blue + 0.0055 + LINE_W, R - LINE_W) * 0.8)
    # The rosette on its raised boss, centred on the ring as Raphael's eye sees it (vault_geom.
    # boss_centre), on a ground the boss's own outline in shaded gold: the boss is gold to its edge.
    bc = np.array(G.boss_centre(-1))
    rb = np.hypot(X - bc[0], Y - bc[1])
    phi = np.arctan2(X - bc[0], Y - bc[1])
    outline = np.vectorize(G.boss_outline)(phi) * G.ROSETTE_R
    over(GOLD_SHADE, cov(outline - rb))
    rosette(bc, G.ROSETTE_R)


def rosette(c, R):
    """A gilt rosette after the vault's bosses: eight lobed outer petals, eight inner ones between
    them, a boss; each part outlined in dark gold, petals with a dark midrib."""
    pt = Painter(c[0] - R, c[1] - R, c[0] + R, c[1] + R, ss=8)
    ow = 0.0012

    def petal(phi, r0, r1, wmax, lobes, phase=0.0):
        rs = np.linspace(r0, r1, 70)
        t = (rs - r0) / (r1 - r0)
        w = wmax * np.sin(np.pi * np.clip(t, 0, 1) ** 0.7) ** 0.75
        w = w * (0.62 + 0.38 * np.abs(np.cos(np.pi * (lobes * t + phase))) ** 0.6)
        al = phi - w / np.maximum(rs, 1e-6)
        ar = phi + w / np.maximum(rs, 1e-6)
        left = np.stack([c[0] + rs * np.sin(al), c[1] + rs * np.cos(al)], 1)
        right = np.stack([c[0] + rs * np.sin(ar), c[1] + rs * np.cos(ar)], 1)[::-1]
        mid = np.stack([c[0] + rs[6:55] * np.sin(phi), c[1] + rs[6:55] * np.cos(phi)], 1)
        return np.concatenate([left, right]), mid

    for k in range(8):
        o, m = petal(k * math.pi / 4, 0.18 * R, R, 0.30 * R, 2.5, 0.25)
        pt.poly(o, GOLD_SHADE, grow=ow)
        pt.poly(o, GOLD)
        pt.line(m, 0.0013, GOLD_SHADE)
    for k in range(8):
        o, m = petal((k + 0.5) * math.pi / 4, 0.16 * R, 0.68 * R, 0.21 * R, 1.5, 0.25)
        pt.poly(o, GOLD_SHADE, grow=ow)
        pt.poly(o, GOLD)
        pt.line(m, 0.0016, GOLD_LIGHT)
    pt.disc(c, 0.25 * R + ow, GOLD_SHADE)
    pt.disc(c, 0.25 * R, GOLD)
    pt.disc((c[0] - 0.05 * R, c[1] + 0.07 * R), 0.10 * R, GOLD_LIGHT)
    pt.lay()


# ------------------------------------------------------------------ the oak
def _rot(ang):
    return np.array([[math.cos(ang), -math.sin(ang)], [math.sin(ang), math.cos(ang)]])


def _leaf(base, ang, L, W):
    """An oak leaf (tree units): short stalk, obovate, four rounded lobes a side, deep sinuses.
    Returns the outline, the midrib and a vein to each lobe."""
    t = np.linspace(0, 1, 90)
    env = W * np.sin(np.pi * t ** 0.72) ** 0.7
    up = env * (0.5 + 0.5 * np.abs(np.cos(np.pi * (4 * t + 0.25))) ** 0.55)
    dn = env * (0.5 + 0.5 * np.abs(np.cos(np.pi * (4 * t + 0.42))) ** 0.55)
    stalk = 0.10
    xs = L * (stalk + (1 - stalk) * t)
    out = np.concatenate([[[0.0, 0.007]], np.stack([xs, up], 1), np.stack([xs, -dn], 1)[::-1], [[0.0, -0.007]]])
    rot = _rot(ang)
    f = lambda q: np.asarray(q) @ rot.T + base  # noqa: E731
    mid = np.stack([np.linspace(0.0, 0.9 * L, 20), np.zeros(20)], 1)
    veins = []
    for m in range(1, 4):
        for sgn, ph in ((1, 0.25), (-1, 0.42)):
            tk = (m - ph) / 4
            xk = L * (stalk + (1 - stalk) * tk)
            wk = W * math.sin(math.pi * tk ** 0.72) ** 0.7
            veins.append(np.array([[xk - 0.18 * W, 0.0], [xk, sgn * 0.72 * wk]]))
    return f(out), f(mid), [f(v) for v in veins]


def _acorn(base, ang, s):
    """An acorn (tree units) on a short stalk: nut, scaly cup over its base, a highlight."""
    rot = _rot(ang)
    f = lambda q: np.asarray(q) @ rot.T + base  # noqa: E731
    tt = np.linspace(0, 2 * math.pi, 48)
    nut = np.stack([0.066 * s + 0.034 * s * np.cos(tt), 0.022 * s * np.sin(tt)], 1)
    ct = np.linspace(math.pi / 2, 3 * math.pi / 2, 30)
    cup = np.stack([0.046 * s + 0.026 * s * np.cos(ct), 0.0245 * s * np.sin(ct)], 1)
    cup = np.concatenate([cup, [[0.047 * s, -0.0245 * s], [0.049 * s, 0.0], [0.047 * s, 0.0245 * s]]])
    hatch = []
    for k in np.linspace(-0.75, 0.75, 4):
        hatch.append(np.array([[0.026 * s, (k - 0.45) * 0.022 * s], [0.047 * s, (k + 0.45) * 0.022 * s]]))
        hatch.append(np.array([[0.026 * s, (k + 0.45) * 0.022 * s], [0.047 * s, (k - 0.45) * 0.022 * s]]))
    hl = np.stack([0.070 * s + 0.024 * s * np.cos(tt[6:16]), 0.013 * s * np.sin(tt[6:16])], 1)
    stalk = np.array([[0.0, 0.0], [0.02 * s, 0.0]])
    return f(nut), f(cup), [f(h) for h in hatch], f(hl), f(stalk)


def oak_design():
    """The della Rovere oak of the vault's triangles, redrawn: a trunk on clawed roots that divides
    as a tree does, into a leader and two limbs, which divide again into seven boughs fanning into
    an oval crown, each with lobed leaves along it and three at its tip, acorns between. The field
    under the rib is tall and narrow, so the crown is taller than the painted ones. Tree units:
    about 1 high, root crown at the origin."""
    wood, bark, shine, leaves, acorns = [], [], [], [], []
    trunk = bezier((0.0, 0.02), (0.018, 0.11), (-0.016, 0.20), (0.0, 0.30), 40)
    wood.append(taper(trunk, 0.092, 0.066))
    bark.append(bezier((-0.014, 0.05), (0.004, 0.12), (-0.022, 0.19), (-0.010, 0.27), 30))
    shine.append(bezier((0.020, 0.05), (0.032, 0.11), (0.006, 0.19), (0.016, 0.27), 30))
    for p0, p1, p2, p3, w in [((-0.026, 0.05), (-0.07, 0.025), (-0.11, 0.005), (-0.17, -0.04), 0.044),
                              ((-0.018, 0.03), (-0.045, -0.015), (-0.06, -0.04), (-0.095, -0.08), 0.036),
                              ((0.0, 0.03), (0.005, -0.02), (-0.004, -0.055), (0.007, -0.095), 0.032),
                              ((0.018, 0.03), (0.045, -0.015), (0.062, -0.038), (0.10, -0.075), 0.036),
                              ((0.026, 0.05), (0.07, 0.028), (0.11, 0.01), (0.17, -0.035), 0.044)]:
        wood.append(taper(bezier(p0, p1, p2, p3, 30), w, 0.006))
    # the fork: a leader straight on, a limb to each side, each starting inside the trunk's top
    leader = bezier((0.0, 0.27), (0.008, 0.38), (-0.010, 0.48), (0.0, 0.60), 40)
    limbL = bezier((-0.008, 0.27), (-0.05, 0.34), (-0.095, 0.39), (-0.135, 0.47), 40)
    limbR = bezier((0.008, 0.27), (0.05, 0.35), (0.10, 0.41), (0.135, 0.50), 40)
    wood.append(taper(leader, 0.050, 0.030))
    wood.append(taper(limbL, 0.044, 0.026))
    wood.append(taper(limbR, 0.044, 0.026))
    bark.append(leader[4:30] + np.array([-0.007, 0.0]))
    shine.append(limbL[4:26] + np.array([0.0, 0.009]))
    shine.append(limbR[4:26] + np.array([0.0, 0.009]))
    shine.append(leader[4:30] + np.array([0.009, 0.0]))
    # seven boughs, each growing out of the leader or a limb (their starts lie on them)
    boughs = [(tuple(leader[-2]), (0.012, 0.69), (-0.012, 0.77), (0.0, 0.85), 0.030, 0.011),
              (tuple(leader[22]), (-0.05, 0.58), (-0.10, 0.69), (-0.15, 0.80), 0.028, 0.010),
              (tuple(leader[26]), (0.05, 0.61), (0.10, 0.71), (0.15, 0.82), 0.028, 0.010),
              (tuple(limbL[-2]), (-0.17, 0.52), (-0.20, 0.58), (-0.23, 0.65), 0.026, 0.010),
              (tuple(limbR[-2]), (0.17, 0.55), (0.20, 0.60), (0.23, 0.67), 0.026, 0.010),
              (tuple(limbL[22]), (-0.13, 0.40), (-0.19, 0.41), (-0.24, 0.45), 0.024, 0.009),
              (tuple(limbR[22]), (0.13, 0.42), (0.19, 0.43), (0.24, 0.47), 0.024, 0.009)]
    rng = np.random.default_rng(11)
    for bi, (p0, p1, p2, p3, w0, w1) in enumerate(boughs):
        path = bezier(p0, p1, p2, p3, 40)
        wood.append(taper(path, w0, w1))
        tang = lambda i: path[min(i + 1, 39)] - path[max(i - 1, 0)]  # noqa: E731
        out = 1 if bi % 2 else -1          # turning this way points away from the tree's axis
        ang = lambda i: math.atan2(*tang(i)[::-1])  # noqa: E731
        if bi in (0, 5, 6):
            sides = ((0.40, out), (0.70, -out)) if bi else ((0.45, -1), (0.72, 1))
        else:                            # leaves inwards, acorns outwards into the gaps
            sides = ((0.70, -out),)
            for frac in (0.38, 0.62):
                acorns.append(_acorn(path[int(frac * 39)], ang(int(frac * 39)) + out * math.radians(66), 1.2))
        for frac, sd in sides:
            i = int(frac * 39)
            L = 0.12 if frac < 0.5 else 0.13
            leaves.append(_leaf(path[i], ang(i) + sd * math.radians(50) + rng.uniform(-0.1, 0.1), L, 0.05 * L / 0.14))
        a0 = ang(39)
        for da, L in ((-0.72, 0.115), (0.72, 0.115), (0.0, 0.15)):
            leaves.append(_leaf(path[-1], a0 + da + rng.uniform(-0.06, 0.06), L, 0.05 * L / 0.14))
    return dict(wood=wood, bark=bark, shine=shine, leaves=leaves, acorns=acorns)


def oak_outlines(design):
    out = list(design["wood"]) + [lf[0] for lf in design["leaves"]]
    for nut, cup, *_ in design["acorns"]:
        out += [nut, cup]
    return out


def place_oak(design):
    """The largest oak that fits the field's blue inside the gold fillet, with a margin, in the
    part of the field a desktop start view shows (16:9 and wider screens: below VIEW_TOP_169)."""
    res = 0.005
    w, h = int(TEX_W / PPM / res) + 1, int(TEX_H / PPM / res) + 1
    gx = XL + (np.arange(w) + 0.5) * res
    gy = Y1 - (np.arange(h) + 0.5) * res
    GX, GY = np.meshgrid(gx, gy)
    rho = np.hypot(GX - XC, GY - YC)
    t = (GX - XC) * N_UP[0] + (GY - YC) * N_UP[1]
    d = np.minimum.reduce([rho - RB, -t - RIB_W / 2, GY - YS])
    margin = FRAME_W + FILLET[0] + FILLET[1] + 0.014
    ok = (d > margin) & (GX - XC > VIEW_LEFT + 0.04) & (GY < VIEW_TOP_169 - 0.05)
    ok &= np.hypot(GX - ROUNDEL_C[0], GY - ROUNDEL_C[1]) > ROUNDEL_R + 0.03
    bad = (~ok).astype(np.float32)
    ref = np.array([XC - 1.6, YS + 0.6])                 # where the trial oak is drawn
    shapes = oak_outlines(design)
    for scale in np.arange(1.20, 0.30, -0.01):
        im = Image.new("L", (w, h), 0)
        dr = ImageDraw.Draw(im)
        for q in shapes:
            q = np.asarray(q) * scale + ref
            dr.polygon([((x - XL) / res, (Y1 - y) / res) for x, y in q], fill=255)
        m = (np.asarray(im) > 0).astype(np.float32)
        ys, xs = np.nonzero(m)
        k = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        hits = cv2.filter2D(bad, -1, k, anchor=(0, 0), borderType=cv2.BORDER_CONSTANT)
        valid = hits < 0.5
        valid[:, w - k.shape[1]:] = False
        valid[h - k.shape[0]:, :] = False
        if valid.any():
            vy, vx = np.nonzero(valid)
            i = np.argmin((vy - vy.mean()) ** 2 + (vx - vx.mean()) ** 2)   # the middle of the places that fit
            return ref + np.array([(vx[i] - xs.min()) * res, -(vy[i] - ys.min()) * res]), scale
    raise SystemExit("the oak does not fit")


def oak():
    design = oak_design()
    origin, scale = place_oak(design)
    tr = lambda q: np.asarray(q) * scale + origin  # noqa: E731
    pts = np.concatenate([tr(q) for q in oak_outlines(design)])
    (x0, y0), (x1, y1) = pts.min(0) - 0.01, pts.max(0) + 0.01
    pt = Painter(x0, y0, x1, y1, ss=6)
    ow = 0.0014                                     # dark gold outline
    for q in design["wood"]:
        pt.poly(tr(q), GOLD_SHADE, grow=ow)
    for q in design["wood"]:
        pt.poly(tr(q), GOLD)
    for q in design["bark"]:
        pt.line(tr(q), 0.0016, GOLD_SHADE)
    for q in design["shine"]:
        pt.line(tr(q), 0.0028, GOLD_LIGHT)
    for out, mid, veins in design["leaves"]:
        pt.poly(tr(out), GOLD_SHADE, grow=ow)
        pt.poly(tr(out), GOLD)
        pt.line(tr(mid), 0.0015, GOLD_SHADE)
        for v in veins:
            pt.line(tr(v), 0.0010, GOLD_SHADE)
    for nut, cup, hatch, hl, stalk in design["acorns"]:
        pt.line(tr(stalk), 0.0035, GOLD_SHADE)
        pt.poly(tr(nut), GOLD_SHADE, grow=ow)
        pt.poly(tr(nut), GOLD)
        pt.line(tr(hl), 0.0018, GOLD_LIGHT)
        pt.poly(tr(cup), GOLD_SHADE, grow=ow)
        pt.poly(tr(cup), GOLD_CUP)
        for h in hatch:
            pt.line(tr(h), 0.0010, GOLD_SHADE, caps=False)
        pt.line(tr(cup)[[0, -1]], 0.0013, GOLD_SHADE)
    pt.lay(clip=cov(D_FIELD - FRAME_W))
    return origin, scale


# ------------------------------------------------------------------ output
def paint():
    """Draw the left half; return the full width (mirrored): linear paint colour, its coverage,
    the gold mask. Nothing below the springing (the impost stands there)."""
    band()
    knot_chain()
    field()
    oak()
    rib()
    roundel()
    keep = cov(Y - YS)
    a = np.clip(ALPHA * keep, 0, 1)
    rgb = ACC * keep[..., None] / np.maximum(a, 1e-8)[..., None]
    gm = np.clip(GOLDM * keep / np.maximum(ALPHA, 1e-8), 0, 1) * (a > 1e-4)
    full = lambda x: np.concatenate([x, x[:, ::-1]], axis=1)  # noqa: E731
    return full(rgb), full(a), full(gm)


def gold_modelling(gm):
    """The gold's painted relief: a height field from the gold's shapes (rounded over 6 mm in from
    their edges), lit from the hall's sun (params SUN_AZIMUTH, SUN_ELEVATION): on the front wall
    it comes from the right, above, and grazing. Returns a factor, 1 on the flat."""
    el, az = math.radians(P.SUN_ELEVATION), math.radians(P.SUN_AZIMUTH)
    L = np.array([math.cos(el) * math.cos(az), math.sin(el), math.cos(el) * math.sin(az)])  # u, v, out
    L /= np.linalg.norm(L)
    m = (gm > 0.5).astype(np.uint8)
    d = cv2.distanceTransform(m, cv2.DIST_L2, cv2.DIST_MASK_PRECISE) / PPM     # metres to the edge
    h = 0.004 * np.sqrt(np.clip(d / 0.006, 0, 1))                             # up to 4 mm of relief
    h = cv2.GaussianBlur(h, (0, 0), 0.9)
    gy, gx = np.gradient(h * PPM)                  # per metre; rows run down
    n = np.dstack([-gx, gy, np.ones_like(h)])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    f = 1.0 + 1.1 * (n @ L - L[2])
    return np.clip(f, 0.62, 1.35)


DECAL_LIGHT = 0.734    # the light the decal showed its white and blue at (VaultOrnament.tsx, WALL_LIGHT)


def tile(stone, wall_light, grain_gain=1.6):
    """The detail tile (linear RGB, alpha = gold leaf), TEX_W x (STRIP + drawing):
    - stone(x, z): the wall's own stone tile sampled at Blender metres on the wall (in phase with
      the wall round it), shown where nothing is painted and multiplied into the paint;
    - wall_light: the front wall's baked light (linear RGB, median round the arch).
    The top STRIP rows: plain white (left half) and gold (right half) for the reliefs' sides."""
    rgb, a, gm = paint()
    H, W = a.shape
    shade = gold_modelling(gm)
    wl = np.asarray(wall_light, np.float64)
    k = gm[..., None] / wl + (1 - gm[..., None]) * DECAL_LIGHT / wl
    paint_alb = rgb * k * (1 + (shade[..., None] - 1) * gm[..., None])
    # Blender metres of every texel on the wall
    xs = G.b(XC - HW + (np.arange(W) + 0.5) / PPM)
    zs = G.b(Y1 - (np.arange(H) + 0.5) / PPM)
    X, Z = np.meshgrid(xs, zs)
    ground = stone(X, Z)
    lum = ground @ LUMA
    grain = 1 + grain_gain * (lum / lum.mean() - 1)
    out = a[..., None] * paint_alb * grain[..., None] + (1 - a[..., None]) * ground
    alpha = gm * a
    white = lin(WHITE) * DECAL_LIGHT / wl
    gold = lin(GOLD) / wl
    strip = np.zeros((G.STRIP, W, 3))
    strip[:, : W // 2] = white
    strip[:, W // 2:] = gold
    salpha = np.zeros((G.STRIP, W))
    salpha[:, W // 2:] = 1.0
    return np.clip(np.concatenate([strip, out]), 0, 1), np.concatenate([salpha, alpha])


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "vault_front_preview.png")
    alb = np.array(P.ALBEDO["stone"])
    rgb, al = tile(lambda X, Z: np.broadcast_to(alb, X.shape + (3,)), np.array([DECAL_LIGHT] * 3))
    cv2.imwrite(str(out), srgb8(rgb * DECAL_LIGHT)[..., ::-1])
    print(f"wrote {out} {rgb.shape[1]}x{rgb.shape[0]} (shown at the wall's light {DECAL_LIGHT}); "
          f"gold {al.mean():.3f} of the tile")
