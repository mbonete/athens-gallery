"""Detail textures for the web's light x detail split: one seamless tile per detail key.

Usage: python -I tools/make_detail.py <bake_dir>
Reads <bake_dir>/detail-specs.json (written by blender/scripts/bake.py from the materials) and
writes <bake_dir>/detail/<key>.png (sRGB albedo, DETAIL_PX square).

Each tile reproduces the Blender material's albedo, but seamless for UV tiling:
- the CC0 scan (already seamless) -> linear -> luminance -> mapped through the material's range
  -> blend of its two fresco colours (as finish.textured() does);
- the painted mottling and the ribs' speckle (finish.painted()) as periodic noise, built in the
  frequency domain so it wraps at the tile's edges (Blender's 3D noise doesn't);
- the floors: the nave's slab with its lozenge (+ marble veining) and the lower floor's module,
  from the same parameters as finish.floor_image() / finish2.floor_material_lower();
- no cracks or stains (the fresco's age, not the building).
"""
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "blender" / "scripts"))
import params as P  # noqa: E402

TEX = ROOT / "blender" / "textures"
out_dir = Path(sys.argv[1])
specs = json.loads((out_dir / "detail-specs.json").read_text())
N = P.DETAIL_PX
(out_dir / "detail").mkdir(exist_ok=True)
rng = np.random.default_rng(7)


def to_lin(srgb):
    c = srgb.astype(np.float32) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def to_srgb8(lin):
    c = np.clip(lin, 0, 1)
    s = np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)
    return np.clip(np.round(s * 255), 0, 255).astype(np.uint8)


def periodic_fbm(n, cycles, octaves=6, rough=0.6, std=0.085):
    """Periodic fBm on an n x n tile: octave i is band-limited noise at `cycles * 2^i` cycles per
    tile (rounded, so it wraps), amplitude rough^i. Mean 0.5, standard deviation `std`
    (Blender's noise texture Fac sits around 0.5 with roughly that spread)."""
    fy = np.fft.fftfreq(n)[:, None] * n
    fx = np.fft.fftfreq(n)[None, :] * n
    r = np.sqrt(fx ** 2 + fy ** 2)
    total = np.zeros((n, n), np.float32)
    for i in range(octaves):
        k = max(1.0, round(cycles * 2 ** i))
        if k > n / 3:
            break
        band = np.exp(-((r - k) / (0.5 * k)) ** 2)
        noise = np.fft.ifft2(np.fft.fft2(rng.standard_normal((n, n))) * band).real
        total += (rough ** i) * noise / (noise.std() + 1e-9)
    total = (total - total.mean()) / (total.std() + 1e-9)
    return 0.5 + std * total


def map_range(v, a0, a1, b0, b1):
    t = np.clip((v - a0) / (a1 - a0), 0.0, 1.0)
    return b0 + t * (b1 - b0)


def scan_luminance(name):
    img = cv2.imread(str(TEX / name / "color.jpg"), cv2.IMREAD_COLOR)[..., ::-1]
    img = cv2.resize(img, (N, N), interpolation=cv2.INTER_AREA)
    lin = to_lin(img)
    return lin @ np.array([0.2126, 0.7152, 0.0722], np.float32)


def textured(spec, dark=None, light=None):
    lum = scan_luminance(spec["detail_tex"])
    f = map_range(lum, *spec["lum_range"], 0.0, 1.0)[..., None]
    dark = np.array(dark if dark is not None else spec["albedo_dark"], np.float32)
    light = np.array(light if light is not None else spec["albedo_light"], np.float32)
    albedo = dark + f * (light - dark)
    if "mottle" in spec:
        scale, contrast, speckle = spec["mottle"]
        tile = spec["tile"][0]
        albedo *= map_range(periodic_fbm(N, scale * tile), 0.3, 0.7, 1 - contrast, 1 + contrast)[..., None]
        if speckle > 0:
            sp = periodic_fbm(N, 90.0 * tile, octaves=2, rough=0.5)
            albedo *= map_range(sp, 0.62, 0.70, 1.0, 1.0 - speckle)[..., None]
    return albedo


def floor_hall(spec):
    """The nave's slab (finish.floor_image), drawn at 2x and reduced for clean edges, with the
    marble veining of finish.floor_material (Marble014, mapped to 0.88-1.06)."""
    mx, my = spec["tile"]
    M = 2 * N
    X, Y = np.meshgrid((np.arange(M) + 0.5) / M * mx, (np.arange(M) + 0.5) / M * my)
    du, dv = np.abs(X - mx / 2), np.abs(Y - my / 2)
    band = (mx / 2 - du < P.FLOOR_BAND / 2) | (my / 2 - dv < P.FLOOR_BAND / 2)
    k = P.FLOOR_BAND / 2 + P.FLOOR_MARGIN
    loz = du / (mx / 2 - k) + dv / (my / 2 - k)
    rose = (loz < 1.0) & (loz > P.FLOOR_LOZENGE_CORE)
    c = np.empty((M, M, 3), np.float32)
    c[...] = P.ALBEDO["floor_white"]
    c[rose] = P.ALBEDO["floor_rose"]
    c[band] = P.ALBEDO["floor_band"]
    c = cv2.resize(c, (N, N), interpolation=cv2.INTER_AREA)
    vein = map_range(scan_luminance("Marble014"), 0.32, 0.65, 0.88, 1.06)
    return c * vein[..., None]


def floor_lower(spec):
    px, py = spec["tile"]
    M = 2 * N
    X, Y = np.meshgrid((np.arange(M) + 0.5) / M * px, (np.arange(M) + 0.5) / M * py)
    dx, dy = np.abs(X - px / 2), np.abs(Y - py / 2)
    b = P.LOWER_FLOOR_BAND
    field = (dx < px / 2 - b) & (dy < py / 2 - b)
    ro, rw = P.LOWER_FLOOR_RING
    ring = (np.maximum(dx / ro[0], dy / ro[1]) < 1.0) & (np.maximum(dx / (ro[0] - rw), dy / (ro[1] - rw)) >= 1.0)
    c = np.empty((M, M, 3), np.float32)
    c[...] = P.ALBEDO["lower_white"]
    c[field] = P.ALBEDO["floor_mauve"]
    c[field & ring] = P.ALBEDO["lower_white"]
    return cv2.resize(c, (N, N), interpolation=cv2.INTER_AREA)


def arch_light():
    """Median light on the opening arch's face (bake_front.npz): the band tile carries the fresco's
    colours divided by it, so the web shows them as painted."""
    f = out_dir / "bake_front.npz"
    if not f.exists():
        return np.ones(3, np.float32)
    d = np.load(f)
    pos, nrm, L = d["position"], d["normal"].astype(np.float32), d["light"][..., :3].astype(np.float32)
    on = d["covered"] & (np.abs(pos[..., 1] - (P.ARCH_Y - P.ARCH_PROJ)) < 0.004) & (nrm[..., 1] < -0.99)
    if on.sum() < 50:
        return np.ones(3, np.float32)
    return np.median(L[on], axis=0)              # per channel: the frame is painted in its own light


def arch_band(light):
    """The opening arch's bands as painted, drawn as vectors: u = one meander period along the
    arc, v = across the bands from the inner edge (row 0 at the bottom of the image is the inner
    edge after the flip below). Sizes in scan px from params.ARCH_R; colours ARCH_COLOURS."""
    R, Cc, Mq = P.ARCH_R, P.ARCH_COLOURS, P.ARCH_MEANDER
    W, H, ss = 512, 1024, 3                        # tile, supersampling
    x = (np.arange(W * ss) + 0.5) / (W * ss)       # fraction of a period
    y = (np.arange(H * ss) + 0.5) / (H * ss)       # 0 inner edge .. 1 outer
    X, Yv = np.meshgrid(x, y)
    r = R["inner"] + Yv * (R["outer"] - R["inner"])
    col = lambda k: np.array(to_lin(np.array(Cc[k], np.float32)), np.float32)   # noqa: E731
    img = np.empty((H * ss, W * ss, 3), np.float32)
    gold_mask = np.zeros((H * ss, W * ss), np.float32)   # 1 where gold leaf (P.ARCH_GOLD)

    def paint(mask, k):
        img[mask] = col(k)
        gold_mask[mask] = 1.0 if k in P.ARCH_GOLD else 0.0
    paint(np.ones_like(r, bool), "red")
    paint(r < R["egg"][1], "egg_ground")
    paint(r < R["egg"][0], "grey")
    paint(r < R["fillet"], "fillet")
    paint(r < R["meander"][1], "ground")
    paint(r < R["meander"][0], "inner")
    # arc length (px) of one period at each radius: the tile is a wedge of the arch
    rm = sum(R["pattern"]) / 2
    half = math.pi / 2 + math.asin((P.ARCH_C[1] - P.ARCH_SPRING_V) / rm)
    dth = half / Mq["periods_half"]
    # bead strings: beads 9 px long, 5 px wide, every 12 px
    for rb in R["beads"]:
        nb = round(dth * rb / 12.0)                 # a whole number of beads a period
        ph = ((X * nb) % 1.0 - 0.5) * dth * rb / nb
        paint(((ph / 4.5) ** 2 + ((r - rb) / 2.5) ** 2) < 1.0, "bead")
    # egg-and-dart: 9 eggs a period, light rim, dark darts between
    re0, re1 = R["egg"]
    rc, hr = (re0 + re1) / 2, (re1 - re0) / 2
    e = (X * 9) % 1.0 - 0.5
    ex = e * dth * rc / 9                           # px from the egg's axis
    egg = (ex / 8.5) ** 2 + ((r - rc) / (hr * 0.82)) ** 2
    paint((egg < 1.0) & (egg >= 0.62), "fillet")
    paint(egg < 0.62, "gold")
    paint((np.abs(np.abs(e) - 0.5) * dth * rc / 9 < 1.3) & (r > re0 + 4) & (r < re1 - 3), "dart")
    # meander: one square spiral a period hung from a continuous outer border; 7 columns (gold
    # strips 0.6 of the pitch, the shaded 30 % on the inner/right side) and 7 levels
    p0, p1 = R["pattern"]
    a = X * Mq["cols"]                              # columns 0..7
    b = (p1 - r) / (p1 - p0) * Mq["rows"]           # levels 0 (outer) .. 7 (inner)
    g = Mq["gold"] / 2
    segs = [("h", 0, -1.0, 8.0)]                    # outer border, continuous
    path = [(0, 0), (0, 6), (6, 6), (6, 1), (1, 1), (1, 5), (5, 5), (5, 2), (2, 2), (2, 4), (4, 4), (4, 3), (3, 3)]
    for (c0, r0_), (c1, r1_) in zip(path, path[1:]):
        if c0 == c1:
            segs.append(("v", c0, min(r0_, r1_), max(r0_, r1_)))
        else:
            segs.append(("h", r0_, min(c0, c1), max(c0, c1)))
    zone = (r >= p0) & (r < p1)
    gold = np.zeros_like(zone)
    shade = np.zeros_like(zone)
    core = np.zeros_like(zone)                      # a strip's lit part wins over a neighbour's shade
    for kind, c, lo, hi in segs:
        if kind == "v":
            d = a - (c + 0.5)
            m = (np.abs(d) < g) & (b > lo + 0.5 - g) & (b < hi + 0.5 + g)
            gold |= m
            shade |= m & (d > g * 0.4)
            core |= m & (d <= g * 0.4)
        else:
            d = b - (c + 0.5)
            m = (np.abs(d) < g) & (a > lo + 0.5 - g) & (a < hi + 0.5 + g)
            gold |= m
            shade |= m & (d > g * 0.4)
            core |= m & (d <= g * 0.4)
    paint(zone & gold, "gold")
    paint(zone & shade & ~core, "gold_shade")
    img = cv2.resize(img, (W, H), interpolation=cv2.INTER_AREA)[::-1]   # v up -> image rows down
    gold_mask = cv2.resize(gold_mask, (W, H), interpolation=cv2.INTER_AREA)[::-1]
    return img / light, gold_mask


def wall_light():
    """Median light on the front wall's face round the arch, outside its bands, inside the vault
    ornament's tile (bake_front.npz): the ornament's gold is divided by it, so it shows as the
    arch's gold does."""
    import vault_geom as G
    f = out_dir / "bake_front.npz"
    if not f.exists():
        return np.full(3, 0.734, np.float32)
    d = np.load(f)
    pos, nrm, L = d["position"], d["normal"].astype(np.float32), d["light"][..., :3].astype(np.float32)
    x, z = pos[..., 0] * P.SCALE, pos[..., 2] * P.SCALE                  # web metres on the wall
    rho = np.hypot(x - G.XC, z - G.YC)
    on = (d["covered"] & (np.abs(pos[..., 1] - P.ARCH_Y) < 0.004) & (nrm[..., 1] < -0.99)
          & (np.abs(x - G.XC) < G.HW) & (z > G.YS) & (z < G.Y1) & (rho > G.RB))
    if on.sum() < 50:
        return np.full(3, 0.734, np.float32)
    return np.median(L[on], axis=0)


_tiles = {}


def textured_once(key, spec):
    """One tile per key (its mottle is random): the wall and the ornament painted on it share it."""
    if key not in _tiles:
        _tiles[key] = textured(spec)
    return _tiles[key]


def stone_sampler(spec):
    """The wall's stone tile as a function of Blender metres on a wall facing -Y (its detail UVs:
    u = x / tile, v = z / tile; image rows run down from v = 1), so a tile painted over the stone
    stays in phase with the wall round it."""
    img = textured_once("stone", spec).astype(np.float32)
    tw, th = spec["tile"]

    def sample(X, Z):
        mx = ((X / tw) % 1.0) * N - 0.5
        my = (1.0 - (Z / th) % 1.0) * N - 0.5
        return cv2.remap(img, mx.astype(np.float32), my.astype(np.float32), cv2.INTER_LINEAR,
                         borderMode=cv2.BORDER_WRAP).astype(np.float64)
    return sample


made = {}
for key, spec in specs.items():
    if key == "flat":
        lin = np.ones((4, 4, 3), np.float32)
    elif key == "floor_hall":
        lin = floor_hall(spec)
    elif key == "floor_lower":
        lin = floor_lower(spec)
    elif key == "arch_band":
        al = arch_light()
        lin, alpha = arch_band(al)
        print(f"arch_band: light on the arch face (median, linear RGB) {np.round(al, 3).tolist()}")
    elif key == "relief_scroll":   # deco round: the facade panels' acanthus scroll (tools/relief_scroll.py)
        sys.path.insert(0, str(ROOT / "tools"))
        import relief_scroll
        lin = relief_scroll.tile(spec, textured(spec))
    elif key == "vault_front":     # the vault ornament painted on the front wall (tools/vault_ornament.py)
        sys.path.insert(0, str(ROOT / "tools"))
        import vault_ornament
        wl = wall_light()
        lin, alpha = vault_ornament.tile(stone_sampler(specs["stone"]), wl)
        print(f"vault_front: light on the front wall round the arch (median, linear RGB) {np.round(wl, 3).tolist()}")
    elif key == "vault_rib":       # the ribs' paint continued past the tile (vault_ornament.rib_strip)
        sys.path.insert(0, str(ROOT / "tools"))
        import vault_ornament
        lin = vault_ornament.rib_strip(stone_sampler(specs["stone"]), wall_light())
    elif key == "step_riser":
        r = np.array(P.ALBEDO["step_riser"], np.float32)
        lin = textured(specs["step"], dark=r * 0.92, light=r)
    else:
        lin = textured_once(key, spec)
    path = out_dir / "detail" / f"{key}.png"
    if key in ("arch_band", "vault_front"):   # alpha: the gold-leaf mask (Scene.tsx adds the sheen there)
        a8 = np.clip(alpha * 255 + 0.5, 0, 255).astype(np.uint8)[..., None]
        cv2.imwrite(str(path), np.concatenate([to_srgb8(lin)[..., ::-1], a8], -1))
    else:
        cv2.imwrite(str(path), to_srgb8(lin)[..., ::-1])
    made[key] = [round(float(v), 4) for v in lin.reshape(-1, 3).mean(0)]
    print(f"{key:14s} {lin.shape[1]}x{lin.shape[0]} mean linear albedo {made[key]}")
if "step" in specs and "step_riser" not in specs:
    r = np.array(P.ALBEDO["step_riser"], np.float32)
    lin = textured(specs["step"], dark=r * 0.92, light=r)
    cv2.imwrite(str(out_dir / "detail" / "step_riser.png"), to_srgb8(lin)[..., ::-1])
    print(f"{'step_riser':14s} {N}x{N} mean linear albedo {[round(float(v), 4) for v in lin.reshape(-1, 3).mean(0)]}")
