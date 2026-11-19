# Hall stage 1: the nave arm finished, beside the fresco

Branch `hall-look`. Blender 5.2, Cycles (Metal + CPU), 128 samples, OpenImageDenoise.
All numbers are at the 100 % reading; the web export would apply `SCALE = 0.7`.
Pixel coordinates (u, v) are on the 3840 × 2661 scan, as in `params.py`; crops were read on the
full 20111 px scan.

## Verdict

The vault is the closest part. Its coffers are the painted ones: the same hexagon-and-lozenge
pattern, rhythm and depth. Unrolled flat, the render's coffers fall where Raphael put them, and the
tones of ribs, risers and panel cores match the fresco's pixels within ~10 % (linear). The walls
and mouldings read as the right building: lit on the left, in shade on the right, entablature
breaking over the piers. But they are cleaner, pinker and flatter than the painting. The two
biggest departures are the flat nave walls (the fresco has recesses and niches) and the archivolt
on the crossing arch, which the fresco doesn't have (the model's narrower arch needed it). As a whole
image it doesn't yet look like the fresco, mostly because everything outside the nave is still
grey. The light matches the fresco only with a deliberate, non-physical convention (§4).

## What to look at

| | File | What it shows |
|---|---|---|
| a | `hall-raphael.jpg` | The finished nave arm from Raphael's camera. Grey and dimmed: not finished. |
| b | `raphael-side-by-side.jpg` | Fresco and render at the same framing. |
| b | `raphael-edges.jpg`, `raphael-blend.jpg` | Edges of the flat-shaded render on the fresco; 50/50 blend. |
| c | `bay-eye.jpg` | Eye level (1.6 m above the platform) in bay 1, towards the crossing. |
| d | `closeup-coffers-vs-fresco.jpg` | Fresco u 1650–2250, v 400–720 beside the render, same camera and pixels. |
| d | `closeup-capital-vs-fresco.jpg` | Fresco u 1140–1480, v 560–940 (first left pier) beside the render. |
| d | `coffer-close.jpg`, `capital-close.jpg` | The same parts from close by, to show the profiles. |
| + | `vault-unrolled-fresco-vs-render.jpg` | The vault unrolled flat (arc length × depth) from fresco and render. |
| + | `hall-raphael-physical.jpg` | The same view with a physical sun (64 samples, before the last junction fix). |
| + | `evidence/`, `fresco-samples.json` | The fresco crops the readings come from; every colour sample and its box. |

## Scope, and one change to it

Agreed: the first nave bay and the front crossing arch, the rest grey.

**Bay 1 has no coffers in the fresco.** Between the facade and the first pier the vault is a plain
soffit (`evidence/bay1-plain-soffit-and-first-pier.jpg`: u 1250–1380, v 500–700 left; u 2490–2580
right). The coffers start at the first pier, where the entablature breaks forward (corner at v 690,
i.e. y ≈ 21.9; in the unrolled vault the field border is at y 22.3–22.9). From there to the
crossing arch they are one field, with no transverse ribs over the model's pilasters at y 27.3.

A bay-1-only sample would have shown a plain soffit and no coffers. From Raphael's camera, almost
all of the painted vault (y 24–31.7) would have stayed grey. So the vault is built as the fresco
shows it: plain over bay 1, coffered from the first pilaster (y 22.4) to the crossing arch and on
through its soffit. Walls, mouldings and materials come from the same code for every bay, so bays 2
and 3 came finished too. **Everything beyond the nave arm is still grey**: facade, steps and
podiums, crossing, drum, dome, second arm, end wall. The extents are parameters
(`COFFER_FIELD_Y0`, `PILASTERS_Y`, the nave's y range) if you want the finish limited to bay 1.

## 1. The coffered vault

**How it was read.** The vault was unrolled onto the model's barrel (radius 5.9 m, springing
12.3 m). Every point of the development (s = arc length from the crown, y = depth) was projected
through Raphael's camera and sampled on the 20111 px scan (`tools/stage1/unroll2.py`). In the
development the coffers have their true shapes, as a mason would set them out, so they can be
measured in metres. A candidate tiling was drawn over the unroll and adjusted until its openings sat
on the painted coffers (`tools/stage1/tilefit.py`; `evidence/coffer-tiling-fitted-on-fresco-unroll.jpg`).

**The pattern.** Elongated hexagons and lozenges tiled edge to edge.
- Hexagon columns run along the vault, points across it. Column spacing 2.62 m of arc, rows every
  1.62 m along y.
- Hexagon flat edge 1.36 m (the painted opening's flat top is ~1.2 m, plus the rib). Slanted edges
  at 52° to the vault's axis.
- One lozenge between each pair of columns: long diagonal 1.62 m along y, short 1.26 m. Its top and
  bottom points meet the hexagons' points; its side points meet the corners where two hexagons of a
  column touch.
- A hexagon column on the crown. The painted one sits at s ≈ −0.15 m, which I read as misfit, not
  design. Row centres at y = 30.07 + k × 1.62.
- Flat ribs 0.20 m wide.
- Field border along the springing at s = ±8.35 m (painted at −8.55 and +8.1, centred on the crown
  column), then a plain band to the cornice. From Raphael's eye the cornice hides the vault beyond
  s ≈ 8.43 anyway. The field starts at y 22.4, the first pilaster's face.
- 78 coffers in the nave field (whole and cut). The crossing arch's soffit carries the same
  pattern scaled by angle (5.475 / 5.9) so the columns run on (7 coffers).

**Depth.** Each painted coffer shows, on its far side only, two dark risers and a light tread. At
the crown they are 0.23–0.25 m tall in the unroll, with a 0.09 m tread. A vertical face of depth d
at the crown appears 1.87 d long there (y / (z − eye) = 30.6 / 16.35). So each riser is ~0.13 m:
two steps of 0.13 m with a 0.09 m tread, 0.26 m in all. As in the painting, the near-side risers
are hidden from below.

**Check.** `vault-unrolled-fresco-vs-render.jpg` unrolls the render the same way. Columns, rows,
lozenges and far-side risers fall where they are painted.

**Where I interpreted.**
- Plain steps, as painted: no mouldings on the step edges, no rosettes (none are painted).
- A 1.5 cm splay on each riser.
- Coffers cut by the field edge get their own rib and riser along the cut. The painted ones may run
  under the border; at that size the fresco doesn't show.
- The bay-1 soffit is on the vault's cylinder. It could be a separate arch; the image doesn't settle it.
- The arch soffit is a separate, smaller-radius surface (§5).

## 2. Mouldings

The profiles are built from a small vocabulary (fillet, fascia, ovolo, cavetto, cyma recta, cyma
reversa, torus, scotia) and swept with mitred corners (`blender/scripts/finish.py`).

- **Entablature, z 10.5–12.3.** Read on the first left pier (`evidence/entablature-first-left-pier.jpg`,
  u 1265–1350, v 672–860): architrave, frieze and cornice in nearly equal thirds, ~1.8 m tall at
  y ≈ 22.
  - Top and 0.5 m projection keep the old cornice reading, so the overlay's main lines don't move.
  - Architrave: two fasciae and a taenia. Frieze: plain. Cornice: ovolo and cyma reversa bed
    mouldings, a 0.24 m corona, a cyma recta sima.
  - It breaks forward over every pilaster, as over the painted piers, and wraps the crossing pier
    as the arch's impost.
  - This replaces the 1 m box cornice (11.3–12.3); the pilasters now end at 10.5. The profile
    details are designed.
- **Capitals, 10.0–10.5.** The painted pier capitals are banded Doric
  (`evidence/capital-and-entablature-right-piers.jpg`, u 2480–2600, v 680–850). The profile is
  designed (Tuscan/Doric): astragal, necking, two annulets, echinus, abacus with a cyma.
- **Bases, 0.5 m.** Every base is hidden behind figures in the fresco. Attic base, designed; it is
  also run along the crossing pier.
- **String course, z 9.0–9.35.** The facade's reading, continued between the pilasters. In the
  fresco a lower entablature runs at that height inside the nave wall's recesses (frontal face at
  y ≈ 18, v 668–800); the model has no recesses. Profile designed.
- **Archivolt** on the crossing arch's nave face: two fasciae and a cyma reversa, 0.40 m wide and
  0.11 m proud. The scheme is the far door's (`evidence/far-door-archivolt.jpg`); the widths fit
  the 0.425 m ring between vault and arch. **The fresco has no archivolt here** (§5).

## 3. Materials and colour

**Samples** are medians of full-resolution pixels; boxes are on `evidence/colour-sample-boxes.jpg`.
They are colours under Raphael's light, not albedos.

| Sample | Box (u0, v0, u1, v1) | sRGB |
|---|---|---|
| Wall, lit (left nave, faces +X) | 1200, 1000, 1240, 1100 | 215, 190, 176 `#d7beb0` |
| Wall, shaded (right nave, faces −X) | 2600, 1000, 2650, 1100 | 153, 128, 98 `#998062` |
| Frontal face, left / right | 1060, 900, 1120, 1100 / 2720, 900, 2800, 1100 | 202, 179, 170 / 204, 183, 172 |
| Plain soffit, bay 1, left / right | 1270, 580, 1320, 660 / 2510, 560, 2560, 640 | 191, 170, 161 / 188, 168, 158 |
| Frieze, first left pier | 1285, 745, 1330, 790 | 200, 179, 174 |
| Cornice soffit, left / right | 1400, 860, 1440, 940 / 2440, 860, 2480, 940 | 150, 126, 99 / 105, 83, 65 |
| Pilaster, first right pier | 2525, 740, 2580, 790 | 152, 125, 94 |
| Vault ribs (unroll, outside the fitted openings) | s −7.5…7.5, y 24–31.4 | 124, 102, 85 `#7c6655` |
| Coffers, darkest 30 % (risers) | same area, inside openings | 86, 71, 60 `#56473c` |
| Coffers, lightest 40 % (treads, highlights) | same | 141, 117, 98 |
| Coffer panel cores (hexagons inset 0.4 m) | same | 108, 89, 74 |
| Platform floor near the steps (k-means) | 1560, 1995, 1760, 2028 | white 231, 214, 217; rose 174, 135, 134 |
| Lower floor (k-means) | 2000, 2400, 2400, 2600 | mauve 143, 114, 135; dark 123, 97, 116; white 169, 164, 188 (bluish photo) |
| Sky in the far door | 1880, 1395, 1940, 1420 | 175, 175, 245 |

**From samples to albedos.** Each material started from its lit sample (sRGB → linear). Then the
render was compared with the fresco region by region through the same camera
(`tools/stage1/calib.py`, `panelcore.py`), and the linear ratio fresco / render per channel set
the next albedo. Five passes. Final state:

| Region | Fresco | Render | Ratio (linear) |
|---|---|---|---|
| Wall, lit | 215, 190, 176 | 217, 190, 174 | 0.98, 1.00, 1.03 |
| Wall, shaded | 153, 128, 98 | 150, 123, 106 | 1.04, 1.09, 0.85 |
| Frieze, lit | 200, 179, 174 | 205, 179, 164 | 0.95, 1.00, 1.14 |
| Pilaster in shade | 152, 125, 94 | 144, 118, 102 | 1.12, 1.13, 0.84 |
| Vault ribs | 124, 102, 85 | 122, 99, 81 | 1.04, 1.06, 1.10 |
| Coffer risers | 86, 71, 60 | 87, 72, 58 | 0.98, 0.97, 1.07 |
| Coffer panel cores | 108, 89, 74 | 110, 89, 73 | ~1.0 |
| Coffers, lightest 40 % | 141, 117, 98 | 118, 96, 79 | 1.47, 1.52, 1.56 |
| Cornice soffit, left | 150, 126, 99 | 142, 113, 101 | 1.13, 1.26, 0.96 |
| Cornice soffit, right | 105, 83, 65 | 137, 111, 97 | 0.56, 0.54, 0.44 |
| Plain soffit bay 1, left | 191, 170, 161 | 160, 133, 117 | 1.48, 1.71, 1.99 |
| Plain soffit bay 1, right | 188, 168, 158 | 139, 114, 92 | 1.95, 2.33, 3.19 |

**Materials** (values in `params.py` → `ALBEDO`):

- **The textures.** Each CC0 scan is used for its pattern only: its luminance blends two
  fresco-derived colours. Projection is a box in object space (no UVs). No AI-generated images.
  `tools/fetch_textures.py` downloads the scans from the official sites into `blender/textures/`
  (git-ignored).
- **Stucco** (walls): Poly Haven `white_plaster_02`, ±10 %. Albedo 0.56, 0.46, 0.43.
- **Stone** (pilasters, entablature, string course, archivolt, crossing pier): ambientCG
  `Travertine009`, ±7 %. Albedo 0.57, 0.47, 0.43.
- **Vault ribs and plain bands**: `white_plaster_02`, albedo 0.58, 0.49, 0.39 (more olive, as painted).
- **Coffer panels and risers**: ambientCG `Marble009` for the mottling. Panels are ~0.8 × the rib.
  Risers are a darker stone (~0.55 × the rib), **chosen to reach the painted contrast** (§7).
- **Nave floor: designed.** The fresco shows it only in a ~20 px strip behind Plato's and
  Aristotle's feet.
  - Seven white slabs across (1.69 m), rows on the coffer rows (1.62 m).
  - 0.12 m mauve bands; a rose lozenge with a white core in each slab.
  - Colours from the platform and lower-floor samples; ambientCG `Marble014` veining, ±12 %.

## 4. Light

**Where Raphael's light comes from** (samples above):
- Faces turned to +X (left nave wall) are lit (215, 190, 176). Faces turned to −X (right nave
  wall) are in shade (153, 128, 98). Same stone, so the light comes from the right.
- Frontal faces are lit equally on both sides (202–204), so the light also comes from the front.
- In linear terms the direct part on +X faces vs frontal faces is 0.32 : 0.26, after subtracting
  the shade level. So the light travels 39° off the −X axis towards +Y: **the sun is to the front
  right**, behind the viewer's right shoulder.
- The figures' shadows on the platform floor run back and to the left at ~45° in plan
  (`evidence/platform-floor-plan-unroll.jpg`).
- In the vault, the left haunch is brighter than the right (grey medians 100 vs 85 at |s| 4.5–8;
  crown 119). The left haunch faces right.
- Apollo's niche is darker on its right, consistent with this. Athena's is darker on its left,
  which isn't; I weighted the large surfaces more.
- The old placeholder sun (and the web prototype's) is front-left.

**Elevation** can't be read well. The floor shadows look 1–1.5× the figures' height (45–55°),
but the frieze under the 0.42 m corona is lit, which needs the sun below ~30°. I chose 35°.

**In Cycles.** A sun in that direction outside a closed hall can't light the fresco's nave. The
right wall, the vault and the right facade pier shade almost all of the left wall
(`hall-raphael-physical.jpg`). Raphael lights each form from the right as if those occluders
weren't there, and the main render reproduces that convention:
- **Shadow linking:** the right-hand wall and its mouldings, the vault, the facade and the crossing
  arch don't block the sun. Everything else casts its shadows: pilasters, entablature, steps, crossing.
- The vault and the arch face take no direct sun, only bounce light.
- The sky lights in the warm colour of the fresco's shade (1.0, 0.85, 0.52): its shaded walls are
  yellower than the lit ones, so there is no blue skylight in them. Camera rays see the fresco's
  blue sky.
- Sun strength 4, angle 3°. Standard view transform with no tone curve, so rendered pixels can be
  compared with the fresco's.

## 5. Main lines, and two findings about the fresco

`raphael-edges.jpg`: facade, steps, podiums, crossing, drum and far door are unchanged. No main
dimension or camera parameter changed; the projection check prints the same values as before.

Detail changes to existing elements:
- The box cornice became a 1.8 m entablature with the same top and projection.
- Pilaster shafts end at 10.5.
- The entablature projects 0.85 m over each pilaster.
- The crossing arch's opening is 0.30 m larger above the springing, behind the coffered soffit.
  The visible intrados stays at 5.475 m.

Findings:
1. **The crossing arch.** In the fresco the coffers run straight into the opening, with a thin
   light edge and no ring, archivolt or soffit band (`evidence/crossing-arch-coffers-to-the-edge.jpg`).
   - The painted crown is at v ≈ 690; the model's arch crown is at v 662.
   - A barrel of the nave's own radius (5.9 m) ending at y ≈ 34.2 projects to the same width
     (392 px from the axis at the springing) and puts the crown at v 689.
   - So the painting reads as the nave vault running on to the crossing at the same radius. That
     would make the crossing 11.8 m square instead of 10.95 m, and the dome larger.
   - It touches the Gate 1 solve, so I didn't change it.
2. **Bay 1's wall.** The front pier's inner face runs to y ≈ 18, then steps out to a frontal face
   (x 5.9 → ~7.3). A recess with a niche follows, and the first pier stands at y ≈ 21.9 (the
   model's pilaster is at 22.4–23.4). The recess's own entablature is at string-course height.

## 6. Reconstructed vs designed

**Reconstructed from the fresco** (readings in `params.py`):
- The coffer tiling: column and row spacing, flat edge, rib width, row phase, crown column, field
  borders.
- The coffer depth: two steps and a tread.
- Bay 1's plain soffit; the coffers running on into the arch soffit.
- The entablature's three parts, its height and its breaks over the piers.
- The capital type (banded Doric).
- The archivolt scheme, from the far door (not from this arch).
- The string-course height.
- Every colour.
- The sun's azimuth; the vault in half-light.

**Designed:**
- Every moulding profile in detail: entablature fasciae, cymas, ovolos, corona and sima; the
  capital's parts; the Attic base; the string course; the archivolt's widths.
- The base and impost wrap on the crossing pier.
- Coffer step details: plain steps, splay, cut-coffer ends, no rosettes.
- The arch soffit's coffers.
- The whole floor pattern.
- Textures and their scales, roughness and bump; the darker riser stone.
- Sun elevation, strength and softness; the warm sky light; the shadow-linking convention; exposure.

## 7. Everything not real, simplified or untested

**Geometry**
- The whole nave arm is finished, not only bay 1 (see Scope).
- Flat nave walls; pilasters at the model's positions (22.9, 27.3). The fresco's recesses, niches
  and pier positions aren't modelled; the first painted pier is ~0.5–1 m nearer the facade.
- The archivolt doesn't exist in the fresco; it fills the model's 0.425 m ring. It shows in (b)
  and (d) as a light band the fresco hasn't. The model's arch is narrower and its crown ~0.36 m
  higher than the painted opening.
- The entablature starts with a cut end at y 18.5 (the facade's inner jamb has none) and stops
  with one at y 32.5, where the grey crossing begins.
- The field's frame is a half rib and a flat band (the fresco shows a thin light line). Shafts
  plain. The string course stops at the pilasters. No dentils, modillions, carving or rosettes.
- The vault is faceted every 0.25 m of arc (chord error ~1.3 mm) and smooth-shaded by angle.
- The arch soffit is 0.8 m deep, so it holds only half-hexagons and half-lozenges.

**Light and colour**
- The main render's light isn't physical: shadow linking, no sun on the vault or arch face, and a
  sky that lights in one colour and is seen in another. The physical sun is in
  `hall-raphael-physical.jpg`.
- Remaining mismatches (table in §3):
  - bay-1 soffit too dark (×1.5–3)
  - right cornice soffit too bright (the lit floor's bounce reaches it; the fresco keeps it dark)
  - step treads and highlights darker than painted (×1.5)
  - shade a little blue (B ×0.85)
- The darker risers are a different stone colour. In the painting they are shade.
- The photo is Wikimedia's "Chroma denoise version". Its colour balance, including the bluish
  bottom, is the photographer's and the restorers', not necessarily the wall's.
- Grey parts are dimmed to 0.6 so they don't clip. The platform outside the nave is plain white.
  Both affect the bounce into the nave.
- The sun's elevation is a choice. There is no tone mapping, so lit grey parts clip.

**Materials**
- Box projection, no UVs: fine for Cycles, not for baking or glTF as is.
- The travertine scan's banding shows on pilasters close up. The ribs lack the painted fine
  speckle. The coffer mottling is a recoloured black-and-green marble.
- The floor image (1180 × 1400, float) is generated at build time and packed in
  `athens-hall.blend` (git-ignored).

**Untested**
- No bake run; the web model not re-exported; nothing tried in three.js or on the A55.
- Whether Cycles baking honours light linking.
- Every junction from every angle. Coplanar faces at the capitals (necking in the shaft face,
  abacus in the architrave soffit) showed as a black slot and were fixed; others may remain.
- Noise: 128 samples + denoiser (the physical variant: 64).

## 8. Bake plan and web cost (Galaxy A55)

The walk only goes along the corridor and every material is rough, so a diffuse bake is enough;
specular can be dropped.

1. **UVs.** One unwrapped set per object for the lightmap, plus a world-scale set for the tiled
   CC0 detail (replacing the box projection).
2. **Bake in Cycles.** Either (A) diffuse direct + indirect without colour into lightmaps, or (B)
   combined (albedo × light) into atlases.
3. **three.js.** (A) `MeshLambertMaterial` with `map` on UV0 and `lightMap` on UV1, no dynamic
   lights. (B) `MeshBasicMaterial` with one atlas. Both are almost free to shade on the A55.
4. **Light linking.** If the bake ignores it, bake with the occluders' shadow-ray visibility
   switched off per object instead.

**Measured:**
- Finished parts: 25,022 triangles (the vault sheet is 11.8k), 1,464 m² of surface.
- Visible surface: about 1,060 m² at 100 % (vault field 319, walls 304, floor 165, entablatures
  151, arch 60, pilasters etc. 60), so about 520 m² at the web's 70 %.
- GLB of the finished parts: 0.77 MB (positions + normals, no UVs, uncompressed).

**Estimated** (70 % scale):
- **(A)** About 2 Mpx of lightmap (40 px/m, 80 on the vault): one 2048×1024 map, ~0.5–1 MB as
  KTX2 and ~2.7 MB of GPU memory with mipmaps. Plus four tiled 1K detail maps: ~1–1.5 MB download,
  ~5.6 MB GPU.
- **(B)** At 100 px/m, about 8 Mpx: two 2048² atlases, ~4–5 MB as KTX2 UASTC (~1.5 MB ETC1S) and
  ~11 MB GPU. As JPEG they'd be ~43 MB of GPU memory, too much for the whole hall.
- **Whole hall:** about 3× the nave arm: ~75k triangles, ~1 MB GLB with meshopt. (A) would need
  ~8 MB GPU, (B) ~32 MB with KTX2.
- **Bake time:** roughly 2–5 min per 2048² map at 256 samples on this Mac (untested).
- **Recommendation:** (A).

## 9. Time

About 1 h 20 min: fresco readings and colour sampling ~35 min, code ~25 min, renders and
calibration ~20 min (plus render time).

**Estimate for finishing the whole hall to this level:** 5–6 h.
- Crossing (pendentives with empty tondo frames, drum pilasters and cornices, dome): 1.5–2 h.
- Facade front: 1 h.
- Second arm (mostly reuse): 0.5 h.
- End wall with door archivolt and balustrade: 0.75 h.
- Floors and steps (the lower floor's pattern is readable): 0.75 h.
- Calibration: 0.5 h.
- If you want the wall recesses, or the crossing enlarged per finding 1: +1–1.5 h.
- Bake and web integration (UVs, bakes, KTX2, three.js materials, A55 test) is a separate 2.5–4 h.

## Reproduce

```sh
python -I tools/fetch_textures.py      # once
SAMPLES=128 blender -b --factory-startup -P blender/scripts/build.py -- renders/hall-stage1 \
    raphael hall-raphael bay-eye capital-close coffer-close crop-coffers crop-capital
blender -b --factory-startup -P blender/scripts/build.py -- <dir> hall-raphael physical
python -I tools/stage1_sheets.py <athens-original.jpg> renders/hall-stage1 renders/hall-stage1
python -I tools/overlay.py <athens-3840.jpg> renders/hall-stage1/raphael.png renders/hall-stage1/raphael
```

The reading scripts are in `tools/stage1/`. Run them with `FRESCO` / `FRESCO_3840` set to the scans:
- `unroll2.py` (vault development), `tilefit.py` (tiling fit)
- `vaultsample.py`, `samplesheet.py`, `floorclusters.py`, `drawboxes.py` (colours)
- `calib.py`, `panelcore.py` (render vs fresco)
- `halves.py` (vault brightness across the vault)
- `crop_orig.py` (full-resolution crops with a grid)

`grey` still builds the Gate 2 model.

## Review (main session, 2026-11-19)

Checked against the images and re-sampled: the colour table's fresco and render values reproduce
within 1–2 levels. One thing the table understates: in shade the render is less olive than the
fresco (G − B +17 vs +30 on the right wall and pilaster), which is what reads as pink-mauve beside
the painted stone in `closeup-capital-vs-fresco.jpg`. The painted stone also carries cracks,
stains and mottling everywhere; the render's surfaces are clean.
