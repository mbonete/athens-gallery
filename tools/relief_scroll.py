"""The acanthus scroll in grisaille for the facade's two sunk panels (deco round, idea 5).

Raphael painted grisaille reliefs with figures in these panels; the hall has no figures, so the
panels take the figure-free Roman panel ornament instead: a rinceau. Drawn here as vectors (in
metres on the panel, 1 mm a pixel, antialiased), modelled as a height field, and shaded with the
hall's sun (params SUN_AZIMUTH, SUN_ELEVATION: from the upper right, in front of the facade) into
the colour, as a painter shades grisaille: the web draws the panel unlit (detail x lightmap).

The design, symmetric about the panel's axis:
- an acanthus calyx at the foot; a stalk rises from it to a rosette;
- from the calyx two stems rise and roll outward over the top into a spiral each, sheathed in
  acanthus leaves along the outer turn, ending in a rosette;
- from each spiral two tendrils branch, each wrapped in an acanthus sheath at the branching:
  one curls down into the lower corner, one up into the upper corner, each ending in a flower.
No animals, no faces.

make_detail.py calls tile(spec, ground); run alone for a preview:
  python -I tools/relief_scroll.py <out.png>
"""
import math
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "blender" / "scripts"))
import params as P  # noqa: E402

PX = 1000.0            # pixels per metre while drawing
RELIEF_M = 0.010       # height of one unit of the height field, metres (the relief's depth)


class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.W, self.H = int(round(w * PX)), int(round(h * PX))
        self.hgt = np.zeros((self.H, self.W), np.float32)

    def px(self, p):
        return (p[0] * PX, (self.h - p[1]) * PX)          # y up (metres) -> rows down

    def _put(self, mask_fn, profile, lift=0.0, pad=0.06):
        """Draw a mask into a crop, turn its distance-to-edge into heights, keep the max."""
        mask = np.zeros((self.H, self.W), np.uint8)
        mask_fn(mask)
        ys, xs = np.nonzero(mask)
        if len(xs) == 0:
            return
        p = int(pad * PX)
        y0, y1 = max(0, ys.min() - p), min(self.H, ys.max() + p + 1)
        x0, x1 = max(0, xs.min() - p), min(self.W, xs.max() + p + 1)
        m = mask[y0:y1, x0:x1]
        d = cv2.distanceTransform((m > 127).astype(np.uint8), cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
        cov = m.astype(np.float32) / 255.0                 # antialiased edge
        h = profile(d) * np.maximum(cov, (d > 0.5)) + lift * (cov > 0.5)
        sub = self.hgt[y0:y1, x0:x1]
        np.maximum(sub, h * np.clip(cov * 1.5, 0, 1), out=sub)

    # ---------------------------------------------------------------- elements
    def stem(self, pts, w0, w1, lift=0.0):
        """A round stem along pts (metres), tapering from width w0 to w1: one outline (offset
        curves and round ends), so its edges are smooth."""
        r_max = max(w0, w1) / 2 * PX
        pts = np.array(pts, np.float64)
        d = np.gradient(pts, axis=0)
        d /= np.linalg.norm(d, axis=1, keepdims=True) + 1e-12
        nrm = np.stack([-d[:, 1], d[:, 0]], 1)
        w = np.linspace(w0, w1, len(pts))[:, None] / 2
        outline = [tuple(q) for q in pts + nrm * w] + [tuple(q) for q in (pts - nrm * w)[::-1]]

        def mask(img):
            q = np.array([[x * 16, y * 16] for x, y in (self.px(p) for p in outline)], np.int32)
            cv2.fillPoly(img, [q], 255, cv2.LINE_AA, shift=4)
            for p, r in ((pts[0], w0 / 2), (pts[-1], w1 / 2)):
                c = self.px(p)
                cv2.circle(img, (int(c[0] * 16), int(c[1] * 16)), int(r * PX * 16), 255, -1, cv2.LINE_AA, shift=4)
        self._put(mask, lambda d: np.sqrt(np.clip(1 - (1 - np.minimum(d / r_max, 1)) ** 2, 0, 1)), lift)

    def poly(self, pts_m, profile, lift=0.0):
        def mask(img):
            q = np.array([[x * 16, y * 16] for x, y in (self.px(p) for p in pts_m)], np.int32)
            cv2.fillPoly(img, [q], 255, cv2.LINE_AA, shift=4)
        self._put(mask, profile, lift)

    def groove(self, pts_m, width, depth):
        """A cut line (leaf veins, lobe divisions): lowers the height along it."""
        g = np.zeros((self.H, self.W), np.float32)
        q = np.array([[x * 16, y * 16] for x, y in (self.px(p) for p in pts_m)], np.int32)
        cv2.polylines(g, [q], False, 1.0, max(1, int(width * PX)), cv2.LINE_AA, shift=4)
        g = cv2.GaussianBlur(g, (0, 0), 1.2)
        self.hgt -= depth * g * (self.hgt > 0.05)

    def leaf(self, base, ang, length, width, curl=0.0, lobes=3, lift=0.35):
        """An acanthus leaf from base along ang (radians, y up), its axis bending by `curl`
        (radians over the length): lobes along each edge, each lobe with pointed fingers; a
        raised midrib between two veins, cuts between the lobes."""
        n = 60
        t = np.linspace(0, 1, n)
        axis, normals = [], []
        x, y, a = base[0], base[1], ang
        for i in range(n):
            axis.append((x, y))
            normals.append((-math.sin(a), math.cos(a)))
            x += math.cos(a) * length / (n - 1)
            y += math.sin(a) * length / (n - 1)
            a += curl / (n - 1)
        env = np.sin(np.pi * np.clip(t, 0, 1) ** 0.75) ** 0.9          # broad near the base, pointed tip
        lobe = 0.72 + 0.28 * np.abs(np.sin(lobes * np.pi * t)) ** 0.6   # lobes
        fingers = 0.10 * np.abs(np.sin(lobes * 3 * np.pi * t))          # fingers on each lobe
        half = width / 2 * env * (lobe - fingers)
        left = [(ax + nx * hw, ay + ny * hw) for (ax, ay), (nx, ny), hw in zip(axis, normals, half)]
        right = [(ax - nx * hw, ay - ny * hw) for (ax, ay), (nx, ny), hw in zip(axis, normals, half)]
        wpx = width / 2 * PX
        self.poly(left + right[::-1], lambda d: 0.55 + 0.45 * np.sqrt(np.clip(d / (0.55 * wpx), 0, 1)), lift)
        self.groove(axis[3:-4], 0.004, 0.18)                            # midrib edges
        for k in range(1, lobes):                                       # cuts between lobes
            i = int(k / lobes * (n - 1))
            for sgn in (1, -1):
                (ax, ay), (nx, ny) = axis[max(0, i - 6)], normals[max(0, i - 6)]
                ex, ey = axis[i][0] + sgn * nx * half[i] * 0.85, axis[i][1] + sgn * ny * half[i] * 0.85
                self.groove([(ax, ay), (ex, ey)], 0.003, 0.22)

    def rosette(self, c, r, petals=8, rings=2, lift=0.3):
        for ring in range(rings):
            rr = r * (1 - 0.38 * ring)
            for i in range(petals):
                a = 2 * math.pi * (i + 0.5 * ring) / petals
                pc = (c[0] + 0.52 * rr * math.cos(a), c[1] + 0.52 * rr * math.sin(a))
                L, Wd = 0.50 * rr, 0.25 * rr * (8 / petals) ** 0.5
                pts = [(pc[0] + L * math.cos(s) * math.cos(a) - Wd * math.sin(s) * math.sin(a),
                        pc[1] + L * math.cos(s) * math.sin(a) + Wd * math.sin(s) * math.cos(a))
                       for s in np.linspace(0, 2 * math.pi, 40)]
                wpx = Wd * PX
                self.poly(pts, lambda d, w=wpx: np.sqrt(np.clip(1 - (1 - np.minimum(d / w, 1)) ** 2, 0, 1)),
                          lift + 0.25 * ring)
        bpx = 0.24 * r * PX
        self.poly([(c[0] + 0.24 * r * math.cos(s), c[1] + 0.24 * r * math.sin(s)) for s in np.linspace(0, 2 * math.pi, 40)],
                  lambda d: np.sqrt(np.clip(1 - (1 - np.minimum(d / bpx, 1)) ** 2, 0, 1)), lift + 0.6)


def spiral(c, r0, r1, a0, turns, cw, n=240):
    """Points of a spiral round c from angle a0 (radians), radius r0 -> r1 over `turns`."""
    s = np.linspace(0, 1, n)
    a = a0 + (-1 if cw else 1) * s * turns * 2 * math.pi
    r = r0 + (r1 - r0) * s
    return [(c[0] + ri * math.cos(ai), c[1] + ri * math.sin(ai)) for ri, ai in zip(r, a)], a


def bezier(p0, p1, p2, n=40):
    t = np.linspace(0, 1, n)[:, None]
    p0, p1, p2 = (np.array(p) for p in (p0, p1, p2))
    return [tuple(q) for q in (1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t ** 2 * p2]


def _heading(pts, i):
    (x0, y0), (x1, y1) = pts[max(0, i - 1)], pts[min(len(pts) - 1, i + 1)]
    return math.atan2(y1 - y0, x1 - x0)


def draw(w, h):
    """Height field of the design on a w x h m panel (1 mm a pixel)."""
    cv = Canvas(w, h)
    ax = w / 2
    for s in (1, -1):                       # right half, then mirrored
        X = lambda x: ax + s * (x - ax)     # noqa: E731
        # main spiral: from the axis side over the top, out, down and in
        C = (X(ax + 0.45), 0.76)
        sp, ang = spiral(C, 0.32, 0.065, math.pi if s > 0 else 0.0, 1.55, cw=s > 0)
        stem = bezier((X(ax + 0.03), 0.25), (X(ax + 0.13), 0.45), sp[0])
        path = stem + sp[1:]
        cv.stem(path, 0.042, 0.022)
        # tendrils, branching from the spiral's outer turn
        # find branch points by position rather than angle (robust for both sides)
        def near(pt):
            d = [(px - pt[0]) ** 2 + (py - pt[1]) ** 2 for px, py in sp[:150]]
            return int(np.argmin(d))
        ib = near((X(ax + 0.40), 0.53))                       # lower turn
        it = near((X(ax + 0.58), 1.02))                       # upper turn
        B, T = sp[ib], sp[it]
        # lower tendril: down and out into a coil in the lower corner
        lc = (X(ax + 0.65), 0.28)
        lsp, _ = spiral(lc, 0.15, 0.035, math.radians(160) if s > 0 else math.radians(20), 1.35, cw=s < 0)
        low = bezier(B, (X(ax + 0.47), 0.40), lsp[0]) + lsp[1:]
        cv.stem(low, 0.026, 0.014)
        # upper tendril: up and out into a coil in the upper corner
        uc = (X(ax + 0.68), 1.20)
        usp, _ = spiral(uc, 0.10, 0.03, math.radians(200) if s > 0 else math.radians(-20), 1.3, cw=s > 0)
        up = bezier(T, (X(ax + 0.62), 1.12), usp[0]) + usp[1:]
        cv.stem(up, 0.022, 0.012)
        # acanthus leaves along the main stem's outer turn, pointing the way it grows
        for k, i in enumerate(range(len(stem) + 6, len(stem) + 160, 17)):
            hd = _heading(path, i)
            sc = 1 - k * 0.07
            cv.leaf(path[i], hd + s * 0.30, 0.20 * sc, 0.095 * sc, curl=s * -0.55)
        # sheaths at the branchings, along the tendrils' first stretch
        for p, br in ((B, low), (T, up)):
            hd = _heading(br, 4)
            cv.leaf(p, hd, 0.17, 0.11, curl=0.0, lobes=3, lift=0.45)
        # leaves along the stem's rise out of the calyx
        cv.leaf(stem[12], _heading(stem, 12) - s * 0.45, 0.17, 0.08, curl=s * 0.5, lift=0.4)
        cv.rosette(sp[-1], 0.095)
        cv.rosette(lsp[-1], 0.06, petals=6, rings=1)
        cv.rosette(usp[-1], 0.05, petals=5, rings=1)
    # central stalk with collars of leaves and a rosette
    cv.stem([(ax, 0.26), (ax, 1.14)], 0.030, 0.024)
    for yy, L in ((0.60, 0.10), (0.90, 0.08)):
        for s in (1, -1):
            cv.leaf((ax, yy), math.pi / 2 - s * 0.75, L, 0.04, curl=-s * 0.5, lobes=2, lift=0.4)
    cv.rosette((ax, 1.21), 0.105)
    # the calyx: five acanthus leaves fanning from the foot, the outer ones curling out
    # broad leaves, the outer pair lying low and curling down, the inner pair turning out, one
    # upright behind the stalk: a cup, not a fan
    cv.leaf((ax, 0.10), math.pi / 2, 0.19, 0.12, curl=0.0, lobes=3, lift=0.45)
    for s in (1, -1):
        cv.leaf((ax + s * 0.02, 0.09), math.pi / 2 - s * 0.62, 0.23, 0.12, curl=-s * 0.7, lobes=3, lift=0.55)
        cv.leaf((ax + s * 0.04, 0.08), math.pi / 2 - s * 1.12, 0.22, 0.11, curl=-s * 0.95, lobes=3, lift=0.6)
    return cv


def shade(cv):
    """Grisaille: the height field lit by the hall's sun, as a factor (1 on the open ground)."""
    el, az = math.radians(P.SUN_ELEVATION), math.radians(P.SUN_AZIMUTH)
    # Towards the sun in the panel's frame (u right = +X, v up = +Z, out of the facade = -Y).
    L = np.array([math.cos(el) * math.cos(az), math.sin(el), math.cos(el) * math.sin(az)], np.float32)
    hm = cv2.GaussianBlur(cv.hgt, (0, 0), 2.6) * RELIEF_M         # metres (rounded edges, no pixel steps)
    gy, gx = np.gradient(hm * PX)                                # per metre (rows down)
    n = np.dstack([-gx, gy, np.ones_like(hm)])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    F = (n @ L) / L[2]
    F = np.where(F > 1, 1 + 0.5 * (F - 1), np.clip(F, 0, None))
    # cast shadows: march towards the sun across the panel
    du, dv = L[0], L[1]
    lh = math.hypot(du, dv)
    step = np.array([du / lh, -dv / lh])                         # in (col, row)
    rise = L[2] / lh / PX                                        # metres of height per pixel travelled
    sh = np.zeros_like(hm)
    for k in range(1, 46):
        M = np.float32([[1, 0, step[0] * k], [0, 1, step[1] * k]])
        ahead = cv2.warpAffine(hm, M, (cv.W, cv.H), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
                               borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        sh = np.maximum(sh, np.clip((ahead - hm - rise * k - 0.0012) / 0.0015, 0, 1))   # 1.2 mm bias: no acne on the tubes
    sh = cv2.GaussianBlur(sh, (0, 0), 1.2)
    ao = 1 - 0.30 * np.clip((cv2.GaussianBlur(cv.hgt, (0, 0), 7) - cv.hgt) * 1.5, 0, 1)
    A = 0.40                                                     # sky and bounce on the facade
    return (A + (1 - A) * F * (1 - 0.9 * sh)) * ao


def tile(spec, ground, n=None):
    """The detail tile: the panel's stone ground (make_detail's tile for the material, linear)
    darkened a little where it is the sunk ground, the relief a touch lighter, times the shading."""
    w, h = spec["tile"]
    cv = draw(w, h)
    f = shade(cv)
    relief = np.clip(cv.hgt * 4, 0, 1)
    tone = 0.95 + 0.05 * relief                                  # light on light; the ground stays cream
    N = n or ground.shape[0]
    f = cv2.resize((f * tone).astype(np.float32), (N, N), interpolation=cv2.INTER_AREA)
    g = cv2.resize(ground, (N, N), interpolation=cv2.INTER_AREA)
    return g * f[..., None]


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "relief_scroll_preview.png")
    w, h = P.NICHE_X[1] - P.NICHE_X[0], P.RELIEF_Z[1] - P.RELIEF_Z[0]
    ground = np.ones((1024, 1024, 3), np.float32) * np.array(P.ALBEDO["stone"], np.float32)
    lin = tile({"tile": [w, h]}, ground)
    lin = cv2.resize(lin, (int(w * 600), int(h * 600)), interpolation=cv2.INTER_AREA)   # true proportions
    s = np.where(lin > 0.0031308, 1.055 * np.clip(lin, 0, 1) ** (1 / 2.4) - 0.055, lin * 12.92)
    cv2.imwrite(str(out), np.clip(s * 255 + 0.5, 0, 255).astype(np.uint8)[..., ::-1])
    print("wrote", out)
