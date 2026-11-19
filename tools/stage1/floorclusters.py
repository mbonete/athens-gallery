import json, cv2, numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
S = 20111 / 3840
im = Image.open(__import__('os').environ.get('FRESCO', 'reference/download/athens-original.jpg')).convert('RGB')
res = json.load(open('fresco_samples.json'))
for name, box, k in (("lower floor", (2000, 2400, 2400, 2600), 3), ("platform floor near the steps", (1560, 1995, 1760, 2028), 3)):
    x0, y0, x1, y1 = box
    a = np.asarray(im.crop((int(x0*S), int(y0*S), int(x1*S), int(y1*S))).resize((400, int(400*(y1-y0)/(x1-x0))))).reshape(-1, 3).astype(np.float32)
    _, lab, cen = cv2.kmeans(a, k, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 0.5), 5, cv2.KMEANS_PP_CENTERS)
    for c in range(k):
        m = [int(v) for v in np.median(a[lab.ravel() == c], 0)]; share = float((lab == c).mean())
        key = f"{name}, cluster {c} ({share:.0%})"
        res[key] = {"box_3840": list(box), "median_srgb": m, "hex": "#" + "".join(f"{v:02x}" for v in m), "source": "k-means"}
        print(f"{key:45s} {tuple(m)} {res[key]['hex']}")
for k in ["platform floor, white", "platform floor, mauve", "lower floor, mauve", "lower floor, white band"]:
    res.pop(k, None)
json.dump(res, open('fresco_samples.json', 'w'), indent=1)
