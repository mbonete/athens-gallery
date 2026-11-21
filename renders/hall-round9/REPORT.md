# Hall round 9: cream marble, a natural sky

Made by the main session (no agent). Rough bake.

## 1. Cream marble (Maria: "now is too white. i want this [swatch] or a tad lighter")
- **Target:** her swatch measures sRGB (212, 203, 171) (mean of the screenshot, p10–p90 ±7).
- **Albedos:** every round-8 white (walls, stone, ribs and coffers, steps and risers, floor whites) × (0.835, 0.795, 0.61) per channel. The factor is the ratio of the target to round 8's lit wall, corrected for the bounce light that changes with it. Walls are now (0.584, 0.549, 0.406).
- **First bake:**
  - the lit wall was (217, 202, 168);
  - but the shade turned khaki: right wall (129, 116, 87), vault (119, 106, 77). Light bouncing between cream walls compounds the cream at each bounce.
- **White balance:** the bake now sees every material colour at 40 % of its saturation, luminance kept (params.BOUNCE_CHROMA, applied in bake.py: 108 colours and the 2 floor images). The lightmaps hold light only. The colours on screen still come from the detail tiles at full saturation, so only the bounce light's colour changes.
- **sRGB means, mid-nave 1600×1000** (tests/colours-*.json):

| Surface | Round 8 (white) | Round 9 |
|---|---|---|
| Lit nave wall | 239, 235, 226 | 214, 203, 170 |
| Shaded right wall | 154, 148, 143 | 125, 116, 96 |
| Vault (crossing arch coffers) | 145, 139, 130 | 115, 107, 85 |
| Floor light tile | 241, 236, 225 | 214, 203, 170 |

- Images: swatch-vs-wall.jpg, start-white-cream-balanced.jpg, midnave-white-cream-balanced.jpg.

## 2. A natural sky (Maria: "sky looks like a painting, it should look natural to be cohesive with the architecture")
- **Model:** Blender 5.2's physical multiple-scattering sky, clear air (aerosol 1; 3 turned the horizon grey). Sun at the bake's position: azimuth 39°, elevation 35°, behind-right of the walk; sun disc off. Pipeline: sky/make_sky.sh, natural_sky.py, readexr.py, stereo.py. It replaces the fresco-derived scripts (still in git at e211836).
- **Exposure:** the sky's sun and the bake's sun lamp are each measured on a white card facing the sun (model 40.2, bake 1.25 = 4/π). Scaling by their ratio shows the sky at the bake's exposure (x1). x1 reads dusky next to the marble: zenith (51, 73, 103). The shipped texture is x2, a photographic exposure: zenith (73, 102, 142), 20° above the far door (108, 146, 191), door horizon (218, 234, 236).
- **Below the horizon:** the horizon's haze (landscape option C), so the slits beside the Bosch show haze.
- **Sky.tsx:** the drum-window patch for Raphael's square-cut clouds is gone. Same projection and layer.
- **Texture:** 137 KB (was 601 KB). Rebuilding with the script gives a byte-identical file.
- Images: far-door-skies.jpg (Raphael / x1 / x2, on the unbalanced cream), dome-up.jpg.

## Tests (5202)
- **Desktop:** 17/17.
- **Touch-portrait:** 5/5.
- **Console:** only the favicon 404.
- **GLB:** 4.71 MB.
- **Rough bake:** 41 min. It shared the machine with sky renders and screenshots; the earlier cream bake took 18 min.

## Limits
- **Dome:** under the dome, lit only by bounce and the oculus, the cream still reads a little olive.
- **Veining:** her swatch has finer, more visible veining than the walls' Marble014. Same mean colour, smoother surface.
- **Sky:** clear, with no clouds. Natural clouds would need a photographed sky (a CC0 HDRI download).
- **Not checked:** the frame rate on the A55.
