# Hall round 10: the arch in cream and gold leaf, the floors in #754543, a photographed sky

Made by the main session after a grilling round with Maria (decisions in the vault journal, 2026-11-21). Rough bake.

## 1. Opening arch (Maria: "this pink is out of place, should be cream. the yellow should be gold leaf-like")
- **Pinks:** the inner band, middle band and egg ground take the wall's cream as it shows beside the arch, (218, 209, 183). The thin fillets are 10 % lighter, (227, 218, 191).
- **Gold leaf:** the meander, eggs and dotted lines are clean gold, (194, 150, 62), with shade (140, 102, 38).
  - **Mask:** the band tile's alpha marks the gold (P.ARCH_GOLD; ETC1S keeps it, 0.03 MB).
  - **Sheen:** in the web, a Blinn-Phong lobe from the bake's sun (hall.json `sun`), exponent 10, pale gold (0.48, 0.34, 0.1) linear at the peak.
  - **Normals:** the GLB has none (the hall is unlit), so the shader takes the face normal from dFdx/dFdy of the world position; the band is flat. The first version read the missing normal attribute as zero and showed no sheen.
  - **Result at the start view:** the gold measures (189, 151, 79) on the left and (226, 187, 104) on the right, where it turns the sun towards the eye. It brightens as you walk in (arch-gold-walking-in.jpg).
- **Unchanged:** the dark reds (outer band, meander ground, darts).

## 2. Floors (Maria: "try #754543 for the rombos and square floor patterns, and the purple straight lines ... the same color as the cream bg")
- **Target:** #754543 as seen on the sunlit floor (Maria, Q12).
- **Corridor lozenges:** albedo (0.164, 0.058, 0.059). They measure (118, 70, 68).
- **Lower floor's squares:** (0.155, 0.048, 0.046); more light reaches them, so they take a little less. They measure (120, 67, 67).
- **Cream:** the slab lines, the lower floor's bands and its rings are now the floor cream (0.584, 0.545, 0.4), so the slab joints no longer show.

## 3. Clouds (Maria: yes; type a, still, the whole photo)
- **Source:** Poly Haven, CC0, kloofendal_48d_partly_cloudy_puresky, 4k HDR (20.7 MB, in reference/download/hdri/, not committed).
- **Pipeline:** sky/make_sky.sh runs natural_sky.py (the physical model, for the sun's azimuth and the exposure), then photo_sky.py, then stereo.py.
- **photo_sky.py:**
  - finds the photo's sun (el 47.9°, az 34.2°) and turns it to the bake's azimuth, 129°;
  - fills the sun disc from its 4–6° ring (4762 px);
  - scales the clear blue to the model's at 2x the bake's exposure: median over cloud-free pixels 15–75° up, more than 60° from the sun, ×1.228;
  - rolls off above 0.8.
- **Below the horizon:** haze averaged from the lowest 3° and smoothed over 10° of azimuth. The horizon's clouds had streaked there.
- **Texture:** 303 KB (round 9 137 KB, Raphael 601 KB). Rebuilding with the script gives a byte-identical file.

## Tests (5202)
- **Desktop:** 17/17.
- **Touch-portrait:** 5/5.
- **Console:** only the favicon 404.
- **Frame rate:** Mac at 1600×1000, 60 fps, p95 17.6 ms.
- **GLB:** 4.70 MB.
- **Rough bake:** 26.5 min.

## Limits
- **Sun elevation:** the photo's sun is 13° higher than the bake's. The disc is removed, and the clouds' lighting doesn't show the difference.
- **Dome windows:** looking up, the sun-side drum windows show bright cloud and read nearly white.
- **Sheen:** the arch is seen from below and in front, so the lobe is broad. It doesn't follow the lightmap's shadows (the arch face is in full sun).
- **Not tested on the A55:** the sheen's cost, the 303 KB sky.
