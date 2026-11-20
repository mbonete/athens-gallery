# Hall round 7: clean coffers, straight shadow edges, shaded dome steps

Report by the hall agent, saved by the main session. Commits on hall-look: 67c96ab (code), 019b800 (bake), 845defc (renders). Maria's screenshots: maria-notes/.

## 1. Coffer texture (note 1: "the texture of the casetone ... wrong because of the dirt and old time of the paint")
- **Cause:** the material, not the light.
  - The panels used Marble009's narrow luminance band (0–0.012) stretched over a wide albedo range (0.38–0.64), with ±60% mottle.
  - The risers were painted darker (0.25–0.41), and the ribs had a dark speckle.
- **Fix:** ribs, panels, risers and treads share one tone, the ribs' buff (linear 0.58, 0.49, 0.39).
  - The only texture is the walls' fine plaster grain (±4%).
  - The steps differ by light only.
  - This applies to the barrel vaults, the crossing arches and the dome.

## 2. Jagged shadows (notes 2 and 3)
- **Note 2, the end door's archivolt dashes:** they are in the lightmap (diagnosis: notes/note2-diagnosis-lightmap-off-detail-off.png).
  - Cause: the moulding's facets are narrower than a texel, and the islands crossed them at an angle round the arch. That archivolt has no beads.
  - Fix: every swept moulding gets lightmap UVs along its own run, so its facets lie along the texel rows.
- **Soffit blotches:** rough-bake noise on a sky-and-bounce surface. They are smoother now, and the final bake's samples remove the rest.
- **Note 3, the sawtooth edge:** a shading edge on the door pier.
  - Cause: about 30% of vertical edges ran off the texel grid, because the unwrap left islands at arbitrary angles.
  - Fix: islands are rotated to the grid, which brings off-grid edges down to 20%. The rest are in islands mixing sloped or curved faces.
- **Bicubic lightmap filter:** the web now samples the lightmap with a B-spline bicubic lookup (4 bilinear taps). `?lmfilter=bilinear` compares. Desktop: 60 fps, p95 17.6 ms with either filter, at 1600×1000 and at 5120×2880. A55: not measured.
- **Final bake alone would not have fixed these.** The cause was island orientation and the material, not texel density.

## 3. Dome coffer steps
- **Step walls:** they get their own texels. Each sunk level is inset in the dome's island by its depth: 5th percentile 10.6 px/m, median 14.9 px/m.
- **The plain band to the oculus:** it was flat at 0.27. A 120 W point light under the oculus now lights only the coffered surface (a convention, since the oculus is open sky), and the band runs from 0.40 at the top ring to 0.60 at the oculus.

## Sizes and checks
| | Round 7 | Round 6 |
|---|---|---|
| Lightmaps | 5.9 Mpx | 8.53 Mpx |
| Crossing atlas | 1664×1536 | 2304×1984 |
| GLB | 5.19 MB | 8.01 MB |

- **Atlas sizes:** front 1152×448, facade 704×704, nave 1280×1152, arm2 960×896. The atlases shrank because the swept mouldings are no longer cut into pieces.
- **Rough bake:** 11 min.
- **Audit:** R1–R12 at 0/0/0. R13: 0 visible, 51 unseen.
- **5202:** the walk works, taps open 9/9, 58.2 fps, p95 17.6 ms. The console shows only the favicon 404.

## Limits (agent)
- 20% of vertical edges are still off-grid; the bicubic filter hides their steps.
- The vault and the dome are one even tone now and read by light alone.
- The oculus light is a convention.
- The bicubic filter's cost on the A55 is unmeasured.

## Review (main session)
- **Note 1:** fixed. The coffers are clean and even (notes/note1-coffers-before-after.jpg). They now read by light alone, which is what she asked for. Whether it reads too plain is for her to judge.
- **Note 2:** fixed. The dashes are gone with the bake alone. The archivolt's outer edge now carries a thin bright line, which is a lit facet and plausible.
- **Note 3:** fixed in every crop and in the phone-size walk-up shots of both door piers and a bay-2 pilaster.
- **Dome:** the steps now shade, and the band has a gradient toward the oculus (dome/dome-coffers-close-before-after.jpg). Some blotchy light remains inside the coffers: 128-sample noise that the final bake should clear.
- **New, small:** in the crossing arch's coffered soffit, the crown column of coffers reads lighter than its neighbours, with soft vertical edges either side. Either the drum light falls there, or it is the right-side shade convention meeting at the crown. Check it before the final bake. If it is the convention, blend it across the vault instead of splitting at the crown, as was done for the dome.
- **Before the final bake:** measure the bicubic filter's cost on the A55 with Maria.
- **Eye height:** still waiting on Maria (renders/hall-round7/eye-height-options.jpg). walk.ts is untouched.
