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


made = {}
for key, spec in specs.items():
    if key == "flat":
        lin = np.ones((4, 4, 3), np.float32)
    elif key == "floor_hall":
        lin = floor_hall(spec)
    elif key == "floor_lower":
        lin = floor_lower(spec)
    elif key == "step_riser":
        r = np.array(P.ALBEDO["step_riser"], np.float32)
        lin = textured(specs["step"], dark=r * 0.92, light=r)
    else:
        lin = textured(spec)
    path = out_dir / "detail" / f"{key}.png"
    cv2.imwrite(str(path), to_srgb8(lin)[..., ::-1])
    made[key] = [round(float(v), 4) for v in lin.reshape(-1, 3).mean(0)]
    print(f"{key:14s} {lin.shape[1]}x{lin.shape[0]} mean linear albedo {made[key]}")
if "step" in specs and "step_riser" not in specs:
    r = np.array(P.ALBEDO["step_riser"], np.float32)
    lin = textured(specs["step"], dark=r * 0.92, light=r)
    cv2.imwrite(str(out_dir / "detail" / "step_riser.png"), to_srgb8(lin)[..., ::-1])
    print(f"{'step_riser':14s} {N}x{N} mean linear albedo {[round(float(v), 4) for v in lin.reshape(-1, 3).mean(0)]}")
