"""Draw a measured floor plan of the hall from blender/scripts/params.py.

Usage: python plan.py <out.png>
Walls cut at ~4 m are filled; vaults, crossing and dome are dashed above; painting places
are numbered in walking order; Raphael's eye and the fresco's wall are marked.
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "blender" / "scripts"))
import params as P  # noqa: E402

out = sys.argv[1]
S = 16                        # pixels per metre
X0, X1, Y0, Y1 = -18, 18, -3, 60
W, H = int((X1 - X0) * S) + 260, int((Y1 - Y0) * S) + 80
img = Image.new("RGB", (W, H), (250, 248, 244))
d = ImageDraw.Draw(img)
try:
    font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 15)
    small = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 12)
    big = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 15)
except OSError:
    font = small = big = ImageFont.load_default()


def px(x, y):
    return (40 + (x - X0) * S, H - 40 - (y - Y0) * S)


def rect(x0, x1, y0, y1, fill=None, outline=None, width=1):
    a, b = px(x0, y1), px(x1, y0)
    d.rectangle([a, b], fill=fill, outline=outline, width=width)


def dashed_rect(x0, x1, y0, y1, col=(120, 120, 120)):
    pts = [px(x0, y0), px(x1, y0), px(x1, y1), px(x0, y1), px(x0, y0)]
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        n = int(max(abs(bx - ax), abs(by - ay)) / 8)
        for i in range(0, n, 2):
            t0, t1 = i / n, min(1, (i + 1) / n)
            d.line([(ax + (bx - ax) * t0, ay + (by - ay) * t0), (ax + (bx - ax) * t1, ay + (by - ay) * t1)],
                   fill=col, width=1)


WALL = (40, 38, 36)
NW, T = P.NAVE_HALF_W, P.WALL_T
# Platform and steps.
rect(-P.SIDE_HALF_W, P.SIDE_HALF_W, P.STEPS[-1][0], P.ARM2_Y1, fill=(232, 228, 220))
for (y, _), (y_next, _) in zip(P.STEPS, P.STEPS[1:] + [(P.STEPS[-1][0], 0)]):
    rect(-P.STEP_HALF_W, P.STEP_HALF_W, y, max(y_next, y + 0.05), outline=(150, 145, 138))
for s in (-1, 1):
    a, b, y0, y1, *_ = P.PEDESTAL
    rect(*sorted((s * a, s * b)), y0, y1, fill=(170, 165, 158))
# Facade with niches.
rect(-P.FACADE_HALF_W, -NW, P.FACADE_Y0, P.FACADE_Y1, fill=WALL)
rect(NW, P.FACADE_HALF_W, P.FACADE_Y0, P.FACADE_Y1, fill=WALL)
for s in (-1, 1):
    rect(*sorted((s * P.NICHE_X[0], s * P.NICHE_X[1])), P.FACADE_Y0, P.FACADE_Y0 + P.NICHE_DEPTH,
         fill=(232, 228, 220))
# Nave and second arm walls, pilasters.
for y0, y1, pil in [(P.FACADE_Y1, P.CROSS_Y0 - P.TRANSVERSE_T, P.PILASTERS_Y),
                    (P.CROSS_Y1 + P.TRANSVERSE_T, P.ARM2_Y1, P.ARM2_PILASTERS_Y)]:
    for s in (-1, 1):
        rect(*sorted((s * NW, s * (NW + T))), y0, y1, fill=WALL)
        for yc in pil:
            rect(*sorted((s * NW, s * (NW - P.PILASTER_D))), yc - P.PILASTER_W / 2, yc + P.PILASTER_W / 2,
                 fill=WALL)
# Crossing: piers (transverse arch walls beyond the opening) and closed sides.
for yy0, yy1 in [(P.CROSS_Y0 - P.TRANSVERSE_T, P.CROSS_Y0), (P.CROSS_Y1, P.CROSS_Y1 + P.TRANSVERSE_T)]:
    for s in (-1, 1):
        rect(*sorted((s * P.CROSS_HALF, s * (NW + T))), yy0, yy1, fill=WALL)
for s in (-1, 1):
    rect(*sorted((s * P.CROSS_HALF, s * (NW + T))), P.CROSS_Y0, P.CROSS_Y1, fill=WALL)
# End wall with the door.
for s in (-1, 1):
    rect(*sorted((s * P.DOOR_HALF, s * (NW + T))), P.ARM2_Y1, P.ARM2_Y1 + P.END_T, fill=WALL)
# Above: vaults, dome (dashed).
dashed_rect(-NW, NW, P.FACADE_Y0, P.CROSS_Y0 - P.TRANSVERSE_T)
dashed_rect(-NW, NW, P.CROSS_Y1 + P.TRANSVERSE_T, P.ARM2_Y1)
cy = (P.CROSS_Y0 + P.CROSS_Y1) / 2
c0, c1 = px(-P.CROSS_HALF, cy + P.CROSS_HALF), px(P.CROSS_HALF, cy - P.CROSS_HALF)
d.ellipse([c0, c1], outline=(120, 120, 120), width=1)
o0, o1 = px(-P.OCULUS_R, cy + P.OCULUS_R), px(P.OCULUS_R, cy - P.OCULUS_R)
d.ellipse([o0, o1], outline=(120, 120, 120), width=1)

# Painting places.
n = 0
for yc in P.PAINTINGS_Y:
    for s in (-1, 1):
        n += 1
        x = s * (NW - 0.1)
        a, b = px(x, yc - P.PAINTING_W / 2), px(x, yc + P.PAINTING_W / 2)
        d.line([a, b], fill=(190, 30, 25), width=7)
        lx = px(s * (NW - 1.6), yc)
        d.ellipse([lx[0] - 12, lx[1] - 12, lx[0] + 12, lx[1] + 12], fill=(190, 30, 25))
        d.text(lx, str(n), fill="white", font=big, anchor="mm")

# Raphael's eye, the fresco's wall and the walking line.
e = px(0, 0)
d.ellipse([e[0] - 6, e[1] - 6, e[0] + 6, e[1] + 6], fill=(30, 90, 200))
d.text((e[0] + 10, e[1] - 2), "Raphael's eye (1.85 m high)", fill=(30, 90, 200), font=font, anchor="lm")
pp = P.PICTURE_PLANE_Y
d.line([px(X0, pp), px(X1, pp)], fill=(30, 90, 200), width=1)
d.text(px(X1, pp + 0.4), "  fresco wall (picture plane)", fill=(30, 90, 200), font=small, anchor="ld")
for t in range(0, 56, 2):
    d.line([px(0, t + 3), px(0, t + 4)], fill=(30, 90, 200), width=2)
d.text(px(0.6, 57), "walk", fill=(30, 90, 200), font=small, anchor="lm")

# Labels and scale bar.
for label, y in [("steps", 7.6), ("platform", 12), ("facade", 17), ("nave", 25), ("crossing + dome", cy),
                 ("second arm", 50), ("door to the sky", P.ARM2_Y1 + 0.5)]:
    d.text(px(X1 - 0.2, y), "  " + label, fill=(60, 58, 55), font=font, anchor="lm")
sb = px(X0 + 1, Y0 + 1)
d.line([sb, (sb[0] + 10 * S, sb[1])], fill=WALL, width=3)
d.text((sb[0], sb[1] - 6), "10 m", fill=WALL, font=font, anchor="ld")
d.text((20, 14), "Plan at ~4 m; dashed = vaults and dome above. Red = painting places (placeholders).",
       fill=WALL, font=font)
img.save(out)
print("saved", out, img.size)
