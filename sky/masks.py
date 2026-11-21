# Step 2: where the fresco shows sky.  sky-clean-2x.png  ->  openings.npy, clear.npy, haze.npy
# The three openings (1 the drum's windows, 2 over the crossing's far arch, 3 the far door above
# Plato's and Aristotle's heads) are the pixels bluer than green inside a box around each: the
# architecture is warm, the sky and its clouds lavender. clear.npy: the cloudless sky in them.
# haze.npy (measuring only): the door's haze between and beside the two heads, down to 3.6 deg.
# opening-overlay.png shows the masks over the fresco.
import numpy as np, cv2
from PIL import Image
X0, Y0, SC = 1690, 640, 2
img = np.asarray(Image.open("sky-clean-2x.png")).astype(np.int16)
H, W, _ = img.shape
r, g, b = img[..., 0], img[..., 1], img[..., 2]
def box(x0, y0, x1, y1):
    m = np.zeros((H, W), bool)
    m[(y0 - Y0) * SC:(y1 - Y0) * SC, (x0 - X0) * SC:(x1 - X0) * SC] = True
    return m
k5 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
k9 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
def clean(m, erode=k5, minarea=2000):
    m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, k5)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, k9)
    nlab, lab, st, _ = cv2.connectedComponentsWithStats(m)
    keep = np.zeros_like(m)
    for j in range(1, nlab):
        if st[j, cv2.CC_STAT_AREA] > minarea: keep[lab == j] = 1
    # fill holes
    ff = keep.copy(); hmask = np.zeros((H + 2, W + 2), np.uint8)
    cv2.floodFill(ff, hmask, (0, 0), 1)
    keep = keep | (1 - ff)
    return cv2.erode(keep, erode).astype(bool)
notwarm = (b >= g + 5) & (b >= r - 15)
clear = (b > r + 15) & (b > g + 12)
openings = {
    "drum": clean(box(1775, 680, 2075, 822) & notwarm),
    "crossing": clean(box(1712, 1112, 2132, 1251) & notwarm),
    # above Plato's and Aristotle's heads (y 1540, 5.8 deg); the haze below is uniform
    "door": clean(box(1768, 1383, 2082, 1541) & notwarm),
}
lab = np.zeros((H, W), np.uint8)
for i, m in enumerate(openings.values()): lab[m] = i + 1
np.save("openings.npy", lab)
np.save("clear.npy", clear & (lab > 0))
# For measuring only: the haze between and beside the two heads, down to y 1625 (3.6 deg).
cols_ = np.arange(W)[None, :]
def xs(x): return (x - X0) * SC
haze = box(1768, 1541, 2082, 1625) & notwarm & (b - r < 30)
heads = ((cols_ > xs(1806)) & (cols_ < xs(1933))) | ((cols_ > xs(1960)) & (cols_ < xs(2072)))
haze &= ~heads
np.save("haze.npy", clean(haze, minarea=300))
ov = img.astype(np.uint8).copy()
cols = [(255, 0, 0), (0, 200, 0), (255, 140, 0)]
for i in range(3):
    m = lab == i + 1
    ov[m] = (0.55 * ov[m] + 0.45 * np.array(cols[i])).astype(np.uint8)
Image.fromarray(ov).resize((W // 2, H // 2)).save("opening-overlay.png")
