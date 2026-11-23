"""Finish the baked light for the web: denoise it, stitch it across island cuts, multiply the
per-face factor in, fill the space between islands and write the atlases.

Usage: python -I tools/lightmap_post.py <bake_dir> <h> [R]
Reads bake_<group>.npz (blender/scripts/bake.py: light, factor, and per texel its world position,
true normal, island and coverage). Writes lightmap_<group>.png: 8-bit sRGB of
light x factor / LIGHT_SCALE, the format tools/pack_hall.mjs reads, and stitch-report.json.

1. Denoise, per atlas: non-local means at strength h on the light alone, the same for every island.
2. Stitch, all atlases together, in world space. Where a surface is cut between two islands (or two
   atlases), each side was baked and denoised on its own, so its low frequencies differ and the
   tone steps at the cut. Near every cut, each texel's local mean over its own island is replaced
   by the mean over every texel on the same plane:
       out = L - G_island(L) + G_plane(L)
   with G a Gaussian (sigma R / 2, radius R) in world space over texels on the same plane (normals
   within 6 degrees, 1.5 cm apart at most) lit by the same light-linking set-up (bake.py's light
   class) and receiving light at all (texels inside another solid are left out). Both sides of a cut then meet at the
   same value; away from cuts G_island = G_plane and nothing changes. The factor is multiplied in
   afterwards, so its deliberate steps (Raphael's right-side shade, the buff side walls) stay sharp.
3. Fill: covered texels with almost no light (inside another solid) take the light of lit texels
   of their own island up to 8 texels away. Cycles' own margin round each island (bake.margin, "extend": each island's edge
   carried outward) stays as baked and denoised, so bilinear filtering at an island's edge reads
   that island; texels beyond it take the nearest baked texel's value, so mipmaps never pull in
   black. (Filling the margin from the nearest covered texel instead hands a texel between two
   islands to either one: on 4-texel-thin islands that showed as dark lines.)
"""
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "blender" / "scripts"))
import params as P  # noqa: E402

OUT = Path(sys.argv[1])
H_NLM = float(sys.argv[2])
R = float(sys.argv[3]) if len(sys.argv) > 3 else 0.3        # stitch radius, metres
SIGMA = R / 2
PLANE_TOL = 0.015                                            # same plane: within 1.5 cm
K = 64
DARK = 0.015                                                 # linear light: inside a solid
PARALLEL = 0.995                                             # same plane: normals within 6 degrees


def enc(lin):
    """Linear light / LIGHT_SCALE -> sRGB levels 0..255 (float)."""
    x = np.clip(lin / P.LIGHT_SCALE, 0.0, 1.0)
    return 255.0 * np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def dec(levels):
    x = np.clip(levels / 255.0, 0.0, 1.0)
    return P.LIGHT_SCALE * np.where(x <= 0.04045, x / 12.92, np.power((x + 0.055) / 1.055, 2.4))


def island_dilate(img, good, ids, todo, iters=8):
    """Fill the texels in todo from good neighbours of the same island, ring by ring (8 rings)."""
    img, good = img.copy(), good.copy()
    for _ in range(iters):
        acc = np.zeros_like(img)
        cnt = np.zeros(good.shape, np.float32)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            sg = np.roll(np.roll(good, dy, 0), dx, 1)
            si = np.roll(np.roll(ids, dy, 0), dx, 1)
            m = sg & (si == ids) & todo & ~good
            acc[m] += np.roll(np.roll(img, dy, 0), dx, 1)[m]
            cnt[m] += 1
        new = cnt > 0
        if not new.any():
            break
        img[new] = acc[new] / cnt[new][:, None]
        good |= new
    return img, good


def fill_nearest(img, covered):
    """Every uncovered texel takes the value of its nearest covered texel (labels of OpenCV's
    distance transform count the covered texels in raster order)."""
    _, lab = cv2.distanceTransformWithLabels((~covered).astype(np.uint8), cv2.DIST_L2, 5,
                                             labelType=cv2.DIST_LABEL_PIXEL)
    ys, xs = np.nonzero(covered)
    i = lab - 1
    return img[ys[i], xs[i]]


t0 = time.time()
groups = {}
for f in sorted(OUT.glob("bake_*.npz")):
    d = np.load(f)
    g = f.stem[len("bake_"):]
    cov = d["covered"]
    light = d["light"][..., :3].astype(np.float32)
    # Covered texels that get (almost) no light lie inside another solid (a wall under a frame, a
    # thin face's texels straddling its neighbour): they take the light of lit texels of the same
    # island nearby, so filtering at a junction reads lit texels and a thin face never reads black.
    # Cycles' margin round each island stays; empty texels take the nearest baked one (step 3).
    alpha = d["light"][..., 3] > 0
    dark = alpha & (light.max(-1) <= DARK)
    light, filled = island_dilate(light, alpha & ~dark, d["island"], dark & cov)
    # Dark margin texels (the margin carries the island's dark edge outward) count as empty: the
    # nearest baked texel is their own island's lit edge, two texels away at most.
    baked = (alpha & ~dark) | filled
    # 1. denoise (on the filled atlas, so the search windows never meet black)
    e8 = np.clip(np.round(enc(fill_nearest(light, baked))), 0, 255).astype(np.uint8)
    den = cv2.fastNlMeansDenoisingColored(e8, None, H_NLM, H_NLM, 5, 15) if H_NLM > 0 else e8
    if g == "front":
        # The opening arch's intrados (bake light class 1 in this group: no sun, finish.light) at
        # the arch face's light level: Raphael paints the soffit's meander as bright as the face's,
        # so the band tile (divided by the face's light, make_detail.arch_light) shows as painted
        # on both. Its own variation round the arch stays. Face: the archivolt's front.
        lit_now = dec(den.astype(np.float32))
        cls = d["light_class"] if "light_class" in d else np.zeros(cov.shape, np.int8)
        nrm_g = d["normal"].astype(np.float32)
        face = cov & (np.abs(d["position"][..., 1] - (P.ARCH_Y - P.ARCH_PROJ)) < 0.004) & (nrm_g[..., 1] < -0.99)
        soff = cov & ((cls & 1) > 0) & (lit_now.max(-1) > DARK)
        if face.sum() > 50 and soff.sum() > 50:
            ratio = np.median(lit_now[face], axis=0) / np.maximum(np.median(lit_now[soff], axis=0), 1e-4)
            lit_now[soff] *= ratio
            den = np.clip(np.round(enc(lit_now)), 0, 255).astype(np.uint8)
            print(f"[post] front: the intrados's light x {np.round(ratio, 3).tolist()} to the arch face's")
    factor = d["factor"].astype(np.float32)
    factor[d["position"][..., 2] > P.DRUM_Z1 + 0.005] = 1.0       # the dome takes no factor (bake.face_factor)
    groups[g] = dict(cov=cov, baked=baked, light=dec(den.astype(np.float32)), factor=factor,
                     pos=d["position"], nrm=d["normal"].astype(np.float32), isl=d["island"],
                     cls=d["light_class"] if "light_class" in d else np.zeros(cov.shape, np.int8))
    print(f"[post {time.time() - t0:5.1f}s] {g}: {cov.shape[1]}x{cov.shape[0]}, {cov.mean():.0%} covered, denoised (h {H_NLM})")

# 2. stitch: which texels lie within R of their island's edge (in atlas px, generous)
QUALITY = json.loads((OUT / "bake-report.json").read_text())["quality"] if (OUT / "bake-report.json").exists() else "rough"
CFG_DENSITY = P.BAKE[QUALITY]["density"]
density = max(c["density"] for c in P.BAKE.values()) * max(list(P.BAKE_DENSITY_SCALE.values()) + [1.0])
rpx = R * density + 2
pts, nrm, isl, val, where, near, cls = [], [], [], [], [], [], []
for gi, (g, a) in enumerate(groups.items()):
    cov, ids = a["cov"], a["isl"]
    edge = np.zeros_like(cov)
    for dy, dx in ((0, 1), (1, 0), (1, 1), (1, -1)):
        sh = np.roll(np.roll(ids, dy, 0), dx, 1)
        shc = np.roll(np.roll(cov, dy, 0), dx, 1)
        diff = cov & (~shc | (sh != ids))
        edge |= diff | np.roll(np.roll(diff, -dy, 0), -dx, 1) & cov
    dist = cv2.distanceTransform((~edge).astype(np.uint8), cv2.DIST_L2, 3)
    # Texels inside another solid (a wall's face behind a pilaster, a base sunk 1 cm) get no
    # light at all; they must not pull the visible surface beside them down.
    lit = cov & (a["light"].max(-1) > DARK)
    yy, xx = np.nonzero(lit)
    pts.append(a["pos"][yy, xx])
    nrm.append(a["nrm"][yy, xx])
    isl.append(ids[yy, xx].astype(np.int64) + gi * 10 ** 7)
    cls.append(a["cls"][yy, xx])
    val.append(a["light"][yy, xx])
    where.append(np.stack([np.full_like(yy, gi), yy, xx], 1))
    near.append(dist[yy, xx] <= rpx)
pts, nrm, isl, val, cls = (np.concatenate(v) for v in (pts, nrm, isl, val, cls))
where, near = np.concatenate(where), np.concatenate(near)
nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-6)
feat = np.hstack([pts, nrm]).astype(np.float32)
tree = cv2.flann_Index(feat, dict(algorithm=1, trees=4))
q = np.nonzero(near)[0]
print(f"[post {time.time() - t0:5.1f}s] {len(pts)} texels, {len(q)} within {R} m of an island edge")

out = val.copy()
steps_before, steps_after, seam_q = [], [], []
CH = 200_000


def means(qi, values):
    j, d2 = tree.knnSearch(feat[qi], K, params=dict(checks=128))
    ok = (j >= 0) & (d2 <= R * R)
    jj = np.where(ok, j, 0)
    dp = pts[jj] - pts[qi][:, None]
    plane = np.abs(np.einsum("nkc,nc->nk", dp, nrm[qi])) < PLANE_TOL
    para = (np.einsum("nkc,nc->nk", nrm[jj], nrm[qi]) > PARALLEL) & (cls[jj] == cls[qi][:, None])
    w = np.exp(-np.einsum("nkc,nkc->nk", dp, dp) / (2 * SIGMA ** 2)) * (ok & plane & para)
    same = isl[jj] == isl[qi][:, None]
    ws = w * same
    sw, sws = w.sum(1), ws.sum(1)
    gw = np.einsum("nk,nkc->nc", w, values[jj]) / np.maximum(sw, 1e-9)[:, None]
    gi = np.einsum("nk,nkc->nc", ws, values[jj]) / np.maximum(sws, 1e-9)[:, None]
    foreign = (w * ~same).sum(1) > 0.05 * np.maximum(sw, 1e-9)
    # the tone step across the cut: this texel against the nearest texel of another island
    # on its plane (within 1.5 texels)
    fd = np.where((ok & plane & para & ~same), np.einsum("nkc,nkc->nk", dp, dp), np.inf)
    jn = fd.argmin(1)
    close = fd[np.arange(len(qi)), jn] < (1.5 / CFG_DENSITY) ** 2
    step = np.full(len(qi), np.nan)
    vj = values[jj[np.arange(len(qi)), jn]]
    step[close] = np.abs(enc(values[qi][close]) - enc(vj[close])).max(1)
    return gw, gi, foreign & (sws > 1e-6), step


for c0 in range(0, len(q), CH):
    qi = q[c0:c0 + CH]
    gw, gi, seam, step = means(qi, val)
    qs = qi[seam]
    out[qs] = val[qs] - gi[seam] + gw[seam]
    steps_before.append(step[seam])
    seam_q.append(qs)
seam_q = np.concatenate(seam_q)
for c0 in range(0, len(seam_q), CH):
    *_, step = means(seam_q[c0:c0 + CH], out)
    steps_after.append(step)
sb, sa = np.concatenate(steps_before), np.concatenate(steps_after)
sb, sa = sb[~np.isnan(sb)], sa[~np.isnan(sa)]
pct = lambda a, p: round(float(np.percentile(a, p)), 2) if len(a) else 0.0   # noqa: E731
report = {"radius_m": R, "nlm_h": H_NLM, "texels": int(len(pts)), "seam_texels": int(len(seam_q)),
          "seam_step_levels_before": {"p50": pct(sb, 50), "p95": pct(sb, 95), "p99": pct(sb, 99), "max": pct(sb, 100)},
          "seam_step_levels_after": {"p50": pct(sa, 50), "p95": pct(sa, 95), "p99": pct(sa, 99), "max": pct(sa, 100)}}
print(f"[post {time.time() - t0:5.1f}s] stitched {len(seam_q)} seam texels; step across cuts (8-bit levels, "
      f"texel against its nearest neighbour in another island) before p50 {report['seam_step_levels_before']['p50']} p95 {report['seam_step_levels_before']['p95']} "
      f"max {report['seam_step_levels_before']['max']}, after p95 {report['seam_step_levels_after']['p95']} "
      f"max {report['seam_step_levels_after']['max']}")

def close_strips(lin, cov, isl, pos, K=6):
    """Strips closed on themselves round the dome (the drum's rings, the tondi's frames, the oculus'
    ring: one island laid along the texel rows, finish.sweep u_along_path, revolve_profile), whose
    first and last texels of every row meet in the world across the closing cut: both ends of each
    row are brought to their mean, tapering over K texels, so the light runs on across the cut
    exactly (round 12: the stitch treats an island's two ends as one side and leaves the cut as
    baked). Only in the crossing above the springing, the dome view's scope. Returns the rows closed."""
    ys, xs = np.nonzero(cov)
    ids = isl[ys, xs].astype(np.int64)
    key = ids * lin.shape[0] + ys
    order = np.lexsort((xs, key))
    key, ys, xs = key[order], ys[order], xs[order]
    first = np.r_[True, key[1:] != key[:-1]]
    last = np.r_[key[1:] != key[:-1], True]
    ra, xa, xb = ys[first], xs[first], xs[last]
    pa = pos[ra, xa]
    ok = (xb - xa >= 4 * K) & (pa[:, 1] > P.CROSS_Y0) & (pa[:, 1] < P.CROSS_Y1) & (pa[:, 2] > P.SPRING_Z)
    ra, xa, xb = ra[ok], xa[ok], xb[ok]
    step = np.linalg.norm(pos[ra, xa + 1] - pos[ra, xa], axis=1)          # one texel, in metres
    gap = np.linalg.norm(pos[ra, xb] - pos[ra, xa], axis=1)
    rowisl = isl[ra, xa]
    closed = gap <= 2.0 * np.maximum(step, 1e-4)
    # only islands closed along most of their rows (a strip, not a chance row of a flat panel)
    u, inv = np.unique(rowisl, return_inverse=True)
    share = np.bincount(inv, closed) / np.bincount(inv)
    closed &= share[inv] > 0.8
    for r, a0, b0 in zip(ra[closed], xa[closed], xb[closed]):
        mean = (lin[r, a0] + lin[r, b0]) / 2
        da, db = mean - lin[r, a0], mean - lin[r, b0]
        for k in range(K):
            w = 1.0 - k / K
            if cov[r, a0 + k]:
                lin[r, a0 + k] += da * w
            if cov[r, b0 - k]:
                lin[r, b0 - k] += db * w
    return int(closed.sum())


# 3. factor, fill, write
for gi, (g, a) in enumerate(groups.items()):
    m = where[:, 0] == gi
    lin = a["light"].copy()
    lin[where[m, 1], where[m, 2]] = out[m]
    before_close = lin.copy()
    nclosed = close_strips(lin, a["cov"] & (a["light"].max(-1) > DARK), a["isl"], a["pos"])
    print(f"[post {time.time() - t0:5.1f}s] {g}: {nclosed} rows of strips closed on themselves made continuous")
    # The margin round a closed strip's ends (Cycles' "extend", texels no face covers) takes the
    # change close_strips made to its nearest covered texel, so filtering at the cut reads the
    # joined light. Elsewhere the margins stay as baked, as before round 12.
    delta = lin - before_close
    margin = a["baked"] & ~a["cov"]
    dist, lab = cv2.distanceTransformWithLabels((~a["cov"]).astype(np.uint8), cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    ys, xs = np.nonzero(a["cov"])
    mm = margin & (dist <= P.BAKE[QUALITY]["margin"] + 1.5)
    k = lab[mm] - 1
    lin[mm] += delta[ys[k], xs[k]]
    e = enc(lin * a["factor"])
    e = fill_nearest(e, a["baked"])
    png = np.clip(np.round(e), 0, 255).astype(np.uint8)
    # Blender's pixel rows run bottom-up; PNG rows top-down.
    cv2.imwrite(str(OUT / f"lightmap_{g}.png"), cv2.cvtColor(png[::-1], cv2.COLOR_RGB2BGR), [cv2.IMWRITE_PNG_COMPRESSION, 3])
(OUT / "stitch-report.json").write_text(json.dumps(report, indent=1))
print(f"[post {time.time() - t0:5.1f}s] wrote {len(groups)} atlases")
