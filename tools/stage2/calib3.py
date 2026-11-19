"""Broad-region calibration (fresco vs render), regions where both show the same building parts."""
import sys, os, cv2, numpy as np
S = 20111 / 3840
f = cv2.imread(os.environ['FRESCO']); r = cv2.imread(sys.argv[1]); k = r.shape[1] / 3840
lin = lambda c: np.where(np.array(c)/255 <= 0.04045, np.array(c)/255/12.92, ((np.array(c)/255 + 0.055)/1.055)**2.4)
R = {'facade L beside niche': (640, 900, 730, 1250), 'facade R beside niche': (3160, 900, 3250, 1250),
     'facade L pier strip': (1005, 800, 1055, 1300), 'frontal L (recess back)': (1110, 900, 1160, 1100),
     'frontal R (recess back)': (2690, 900, 2750, 1100), 'left nave walls': (1300, 950, 1500, 1400),
     'right nave walls': (2380, 950, 2560, 1400), 'left wall upper (entabl.)': (1380, 800, 1480, 950),
     'right wall upper (entabl.)': (2400, 800, 2500, 950), 'end wall': (1745, 1340, 1775, 1450),
     'drum band': (1700, 840, 1800, 870), 'step riser': (1560, 2050, 1640, 2085)}
tot = []
for name, (x0, y0, x1, y1) in R.items():
    a = np.median(f[int(y0*S):int(y1*S), int(x0*S):int(x1*S)].reshape(-1, 3)[:, ::-1], 0)
    b = np.median(r[int(y0*k):int(y1*k), int(x0*k):int(x1*k)].reshape(-1, 3)[:, ::-1], 0)
    rat = lin(a) / np.maximum(lin(b), 1e-4); tot.append(np.abs(np.log(rat)).mean())
    print(f"{name:28s} fresco {tuple(int(v) for v in a)} render {tuple(int(v) for v in b)} lin ratio {np.round(rat, 2)} G-B {int(a[1]-a[2]):+d}/{int(b[1]-b[2]):+d}")
print("mean |log ratio|", round(float(np.mean(tot)), 3))
