# Step 1: the fresco around its painted sky, without the craquelure.
#   python prep.py <athens-original.jpg>  ->  sky-clean-2x.png
# Crops the 20111 px scan to the box around every patch of painted sky (3840 px scale, as in
# camera.json: x 1690-2150, y 640-1680), replaces the cracks (dark thin lines more than 22 levels
# below a 9 px grey closing) with the closing, and downsamples to 2x the 3840 scale (79 px/deg).
import sys
import numpy as np, cv2
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
im = Image.open(sys.argv[1])
S = im.size[0] / 3840
X0, Y0, X1, Y1 = 1690, 640, 2150, 1680          # 3840-scale box around all the painted sky
c = np.asarray(im.crop((round(X0*S), round(Y0*S), round(X1*S), round(Y1*S))))
k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
closed = cv2.morphologyEx(c, cv2.MORPH_CLOSE, k)
# Only the cracks: dark thin lines well below their surroundings (black-hat > 22 levels).
lum = lambda a: a.astype(np.float32) @ np.array([0.2126, 0.7152, 0.0722], np.float32)
crack = (lum(closed) - lum(c)) > 22
crack = cv2.dilate(crack.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))) > 0
print("crack fraction", crack.mean())
closed = np.where(crack[..., None], closed, c)
w, h = round((X1 - X0) * 2), round((Y1 - Y0) * 2)  # keep 2x the 3840 scale (79 px per degree)
small = cv2.resize(closed, (w, h), interpolation=cv2.INTER_AREA)
Image.fromarray(small).save("sky-clean-2x.png")
print(small.shape)
