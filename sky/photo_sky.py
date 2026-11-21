"""A photographed sky (an equirect HDRI) prepared for the web's sky texture:
- turned about the zenith so its sun stands at the bake's sun azimuth (natural_sky.py's layout:
  centre +Y = the walk's forward, +X right; the photo's own elevation is kept);
- its sun disc taken out (the hall is lit by a sun at another elevation; the disc would also clip);
- scaled so its clear blue matches the physical model's (natural_sky.py) at the given exposure,
  over the same directions;
- highlights rolled off above 0.8 instead of clipping.
  photo_sky.py <photo.npy> <model.npy> <model_scale> <sun_rotation_deg> <out.npy>"""
import sys, numpy as np, cv2
photo, model, mscale, rot, out = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), sys.argv[5]
a = np.load(photo).astype(np.float32); H, W = a.shape[:2]
Y = np.array([0.2126, 0.7152, 0.0722], np.float32)
lum = cv2.GaussianBlur(a @ Y, (0, 0), 3)
r0, c0 = np.unravel_index(np.argmax(lum), lum.shape)
sun_az = (c0 + 0.5 - W / 2) / W * 360; sun_el = 90 - (r0 + 0.5) / H * 180
shift = int(round((rot - sun_az) / 360 * W))
a = np.roll(a, shift, axis=1); c0 = (c0 + shift) % W
# Directions of every pixel.
el = np.radians(90 - (np.arange(H) + 0.5) / H * 180)[:, None] * np.ones((1, W))
az = np.radians((np.arange(W) + 0.5 - W / 2) / W * 360)[None, :] * np.ones((H, 1))
d = np.stack([np.cos(el) * np.sin(az), np.cos(el) * np.cos(az), np.sin(el)], -1)
se, sa = np.radians(sun_el), np.radians(rot)
sun = np.array([np.cos(se) * np.sin(sa), np.cos(se) * np.cos(sa), np.sin(se)])
ang = np.degrees(np.arccos(np.clip(d @ sun, -1, 1)))
# The disc: everything far brighter than the sky round it, within 4 deg, filled from its ring.
ring = (ang > 4) & (ang < 6)
hot = (ang < 4) & ((a @ Y) > 3 * np.median((a @ Y)[ring]))
k = (0, 0)
wgt = cv2.GaussianBlur((~hot).astype(np.float32), k, 12)
fill = cv2.GaussianBlur(a * (~hot)[..., None], k, 12) / np.maximum(wgt, 1e-6)[..., None]
a[hot] = fill[hot]
# Exposure: clear blue only (no cloud), 15-75 deg up, away from the sun, in both skies.
m = np.load(model).astype(np.float32) * mscale
if m.shape != a.shape:
    m = cv2.resize(m, (W, H), interpolation=cv2.INTER_AREA)
blue = (a[..., 2] > 1.5 * a[..., 0]) & (ang > 60) & (np.degrees(el) > 15) & (np.degrees(el) < 75)
scale = float(np.median(m[blue] @ Y) / np.median(a[blue] @ Y))
a *= scale
# Roll off above 0.8 (clouds lit by the sun), per channel.
t = 0.8
a = np.where(a > t, t + (1 - t) * (1 - np.exp(-(a - t) / (1 - t))), a)
np.save(out, a.astype(np.float32))
print(f"[photo] sun at az {sun_az:.1f} el {sun_el:.1f} -> az {rot:.1f}; disc px {int(hot.sum())}; "
      f"blue px {int(blue.sum())}; scale {scale:.4g}; zenith {np.median(a[:8], (0, 1)).round(3).tolist()}")
