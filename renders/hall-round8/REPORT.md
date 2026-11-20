# Hall round 8: white marble, the dome's black line, the crown column

Report by the hall agent, saved by the main session.
- Commits on hall-look: a3f89a0, 38121a3, c80d4d6.
- The constant eye height (1.295 m, Raphael's) was db1d154, made by the main session.

## 1. White marble (Maria: "closer to terracota than to white marble. i want white marble")
sRGB means, mid-nave view at 1600×1000, round 7 → round 8:

| Surface | Round 7 | Round 8 |
|---|---|---|
| Lit nave wall | 206, 180, 160 | 239, 235, 226 |
| Shaded right-side wall | 126, 96, 79 | 154, 148, 143 |
| Vault (crossing arch coffers) | 117, 93, 78 | 145, 139, 130 |
| Floor light tile | 219, 200, 211 | 241, 236, 225 |

Sources of the warmth, each fixed (the bake was redone, so the bounce light changes too):
- **Albedos:** walls, stone, ribs, coffers, steps and risers are one warm white (0.70, 0.69, 0.665). The floor white is (0.70, 0.685, 0.655).
- **Lights:**
  - sky light: was the fresco's yellow (0.95, 0.93, 0.45), now cool (0.88, 0.93, 1.0);
  - sun: warm-white (1.0, 0.985, 0.955);
  - bay-1 bounce card: neutral;
  - oculus light: follows the sky.
- **Right-side shade:** grey (0.74, 0.75, 0.78), was olive (0.775, 0.75, 0.69).
- **Tints:** the side-wall buff and the drum olive are gone. The FAR and facade tints are near-neutral.
- **Detail tiles:** grey veining from CC0 Marble014, 4.5% darker than the marble, replaces Travertine and plaster.
- **Unchanged:**
  - the opening arch's meander and red band;
  - the lavender sky (a separate agent is working on the sky);
  - the lower floor's mauve fields with white bands, as painted.

## 2. Black line on the dome (Maria: "on zooming the dome there is a random black line glitch")
- **Cause:** the pendentives are cut by a faceted sphere. Its facets dip up to 2.5 mm below each crossing arch's line, at the arch face. That sliver of pendentive, baked dark behind the arch, showed as a thin black line between the arch's coffered soffit and its edge moulding. Whether it filled a pixel depended on the angle and zoom, so it flickered. Found by ray scans across the junction.
- **Fix:**
  - the arch's edge moulding reaches 6 mm into the opening;
  - the drum base ring has a chamfered foot, which closes a second slot (round 6's flat underside showed the drum wall in shadow).

  The ray scans are clean.
- **Ruled out:** the bicubic lookup (taps reach 1.5 texels, inside the 2-texel margin), lightmap mips, stacked pairs.

## 3. Lighter crown column (main-session review, round 7)
- **Cause:** the right-side-shade convention stepped from 1 to 0.775 at x = 0.5.
- **Fix:** it is now blended per vertex with a smoothstep from the left wall to the right. Across the front crossing arch's crown it runs 0.95 → 0.82 with no step.

## 4. Tests at the constant eye height (5202)
- **Walk:** works start to end.
- **Paintings:** taps open 9/9; walk-up and Back work on each.
- **Dome tap:** in, and tap-anywhere out, from the start, mid-nave and bay 3. From bay 3 the dome is a 7 px sliver at the top edge, and the tap still lands.
- **Frame rate:** 57.7–60 fps, p95 18.6 ms (bicubic on).
- **Audit:** R1–R12 0/0/0; R13 0 visible (65 unseen).
- **Console:** only the favicon 404.
- **Sizes:** lightmaps 5.8 Mpx; GLB 4.94 MB.
  - atlases: front 1152×448, facade 704×704, nave 1280×1152, crossing 1664×1472, arm2 960×896.
- **Rough bake:** 13.5 min.

## Limits (agent)
- Shade reads neutral grey with a slight warmth (R−B 11). A bluer right-side factor (about 0.72, 0.745, 0.80) needs a rebake.
- The last albedo nudge touched only the detail tiles. The lightmaps used (0.70, 0.68, 0.64), about 1% difference in bounce light.
- The lower floor is still mauve with white bands.

## Review (main session)
- **White marble:** achieved. Lit walls measure warm white, the shade is grey, and the hall no longer reads terracotta (marble/start-before-after.jpg, marble/midnave-before-after.jpg). The paintings' dark frames sit well on white.
- **Watch: the veining.** On large surfaces seen close, the front wall around the opening arch in the start view, the Marble014 veining reads as soft grey clouds. Maria rejected the grime look on the coffers, so this should be her call: subtler or finer veining, or none on the big flat walls.
- **Ask Maria: the lower floor.** The start view's lower floor is now the most saturated colour on screen (mauve fields with white bands, as painted).
- **Dome:** the black-line cause is credible (the sliver plus the slot) and fixed in geometry. Nobody captured her exact glitch, so her own check is the real test.
- **Before the final bake:** decide the shade's coolness (it needs a rebake), the veining strength and the lower floor.
