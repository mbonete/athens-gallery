# Hall stage 5: the opening arch, whole lightmaps, Maria's notes in the web

## Summary

- The opening arch is built from the fresco.
- The lightmap patches on flat walls are gone in all five phone close-ups.
- One new defect needs fixing before the final bake: a dark line on the facade panel frame's right edge (section 2).

The rough bake is on 5202 and committed on hall-look. Not pushed; no final bake. It took about 4 h against a
2–2.5 h budget.

Commits:
- eb5a2fb Lightmaps: flat walls whole, stitched across cuts
- bde60b0 Opening arch: the fresco's lunette frame, built as painted
- 2335cc1 Rough bake of stage 5
- 8f18766 Stage 5 renders (renders/hall-stage5/, 5.3 MB)

## 1. Opening arch

**Measurement**
- Radial cuts every 4 degrees (8–172) through the meander band, with circles fitted to its edges:
  - outer edge: r 1705.5 px, rms 6 px;
  - inner edge: r 1624.7 px, rms 5 px.
- Shared centre: u 1915.5, v 2021 (3840 px scan).
- The centre is 245 px below the horizon, so the arch is segmental. It springs at v 1771 on the painted impost,
  8.9 degrees above its centre line (the vanishing point is at v 1776).
- Images: `arch/fresco-frame-unrolled.jpg`, `arch/fresco-meander-straightened.jpg`.

**Plane and sizes**
- The face is at y = 4.753 m, where the fresco's bottom edge (v 2661) meets the floor: 1.85 × 2274 / 885.
- Each member is placed from scan px at its own depth (`finish2.eye_point`), so its edges land on the painted
  ones and its sides follow Raphael's sight lines.

| Member | Full scale | Web (70 %) |
|---|---|---|
| Springing height | 1.86 m | 1.30 m |
| Crown of the opening | 4.72 m | 3.30 m |
| Opening at the springing | 6.69 m | |
| Face width | 0.64 m | |

- The centre is 3.7 cm left of the hall's axis, as painted.

**Bands, inside out (radii in px)**

| Band | Radii (px) |
|---|---|
| Plain inner band | 1619–1631 |
| Meander between dark lines | 1631–1717 |
| Light fillet | 1717–1733 |
| Grey band with two bead strings | 1733–1826 |
| Egg-and-dart | 1826–1868 |
| Red | 1868–1925 |

The archivolt (inner band to fillet) stands 3 cm proud; the outer bands 1 cm.

**Texture.** A vector-drawn tile (`make_detail.py`, key `arch_band`), mapped along the arc.
- Module, measured by autocorrelation on both halves: a period of 186 px at mid-band, made of 7 strip pitches
  of 26.5 px, with 7 levels across 73 px. Gold strips are 0.6 of the pitch.
- The pattern is one square spiral per period (2.5 turns), hung from a continuous outer border. 15 periods a
  side, mirrored at the crown.
- Colours are medians of k-means clusters (sRGB):

| Element | Colour |
|---|---|
| Gold | 172,122,64 |
| Gold shade | 142,97,52 |
| Ground | 78,50,47 |
| Inner band | 160,136,130 |
| Fillet | 177,151,148 |
| Grey | 155,127,120 |
| Beads | 147,103,65 |
| Egg band | 140,110,97 |
| Darts | 106,59,43 |
| Red | 93,49,37 |

- The tile is divided per channel by the baked light on the face (1.17, 1.14, 0.88, read from the bake), so the
  web shows the painted colours.
- Images: `arch/band-tile.jpg`, `arch/band-fresco-vs-web-straightened.jpg`.

**Soffit.** None is painted: the scene starts right at the inner band's edge. The soffit and the jambs splay
along the sight lines through a 0.40 m wall. Raphael's eye can't see them. Plain stone (designed).

**Supports**
- Plain stone pilasters, 0.255 m wide (the mean of the painted 0.28 and 0.23 m), 5 cm proud, inner face flush
  with the jamb. At u 315 and 3516; the painted ones are at about 300 and 3510.
- Plinths 0.15 m high, 2 cm proud, sunk 1 cm.
- Impost 0.12 m high (painted v 1770–1830), projecting 0.099 m against the archivolt's 0.03 (R4).
  - It runs from 6 cm beyond the outer band across the pier, back along the splayed jamb and round the back of
    the pier.
  - It returns into the wall at both ends (R1, R2).

**Front wall.** Plain stone, 24 × 9 m, 0.40 m thick (designed). The 9 m height covers the start view on
portrait phones, whose frustum reaches 8.3 m.

**Light.** None of the arch casts shadows (visible_shadow off), so the sun and sky still enter the hall as
painted. It still takes part in bounce light.

**Overlay** (`tools/arch_check.py` on the web's `?fresco` framing)
- 23 usable cuts out of 27. Four detections failed: the crown medallion at 92 degrees, and 160–168 degrees.
- Outer edge: 19 of 23 within 6 px, median |d| 4.5 px.
- Inner edge: 16 of 23 within 6 px, median |d| 5.5 px.
- The misses:
  - the right shoulder at 64–100 degrees is off by +10 to +22 px, where the painted band runs inside the
    circle;
  - the inner edge at 148–156 degrees is off by +13 and +15 px.

  The painted frame is not a perfect circle, and one circle can't follow both.
- Edge agreement between the web and Blender over the whole view: 64.7 / 72.6 / 81.7 % within 1 / 2 / 4 px
  (stage 4: 66 / – / 82).
- Images: `arch/overlay-*.jpg`, `arch/web-start*.jpg`, `arch/arch-check.json`.

**Walk.** On the walk line the eye (1.60 m web) passes 1.7 m under the crown and 2.3 m from each jamb. Bay 1's
paintings are off screen at the start, so they can't be tapped there and no walk-up crosses the wall. All 9
walk-ups start inside the hall and work.

**Joint audit: 0 collisions, 0 open ends, 0 skewed, 68 contacts.** In `tools/joint_audit.py`,
`opening_wall` and `opening_pilaster_` count as supports; the archivolt, impost and base count as mouldings.

**Limits of the arch**
- The outer bands (grey with beads, egg-and-dart, red) are not concentric with the meander in the fresco: they
  follow the room's real lunette rim and wander by about ±20 px. They are built concentric, so they are off by
  that much.
- Not built: the crown medallion (a rosette in a ring on the meander) and the volute above it. The meander
  simply continues, mirrored.
- The spiral is a standard square spiral at the measured module, not a trace of the painted unit's exact path.
- The meander ground is one brown. The painted ground is brown on the left and bluish on the right.
- The egg-and-dart and beads are simplified to ellipses and dashes.
- The painted pilasters carry grotesques and stand on a dado (v 2290–2380). They are built plain, from the
  floor, on plinths.
- Looking back from inside, the arch opens onto the open forecourt and sky, as before.

## 2. Lightmap patches

**Cause.** The 2.5 m grid cut every flat wall into separate islands, each baked and denoised on its own, so
their tones stepped at the cuts.

**Fix**
- Walls, floors and ceilings now keep each flat face as one island.
- Curved parts and mouldings are still cut on the grid (`BAKE_CUT_MEMBERS`). Keeping mouldings whole made
  comb-shaped islands and pushed the crossing atlas to 3648², so that first bake was stopped.
- Long islands are now laid along the shelves, and each page is at least as wide as the longest island. That
  fixed an overflow bug.
- `bake.py` now saves the light, the per-face factor and, per texel, the world position, normal, island and
  light class.
- `tools/lightmap_post.py` replaces `denoise_lightmaps.py`:
  - non-local means at the same strength everywhere;
  - then a stitch in world space across all atlases. Near each cut, every texel's local mean over its own
    island is replaced by the mean over its plane: same normal within 6 degrees, within 1.5 cm, same
    light-linking class. Texels inside solids are left out;
  - then the factor is multiplied in. Its deliberate steps (Raphael's right-side shade, the buff side walls)
    stay sharp;
  - Cycles' margins round each island are kept.

**Criterion: the largest tone step on a flat lit wall in the phone close-ups**, in 8-bit luma over 24 px
windows. Regions avoid real edges, frames and the hint pill (`lightmap/phone-steps.json`).

| Spot | Before | After |
|---|---|---|
| recess-corner-capital-band | 3.5 | 2.9 |
| bay1-left-recess | 1.9 | 1.6 |
| facade-front-left | 1.0 | 1.4 |
| arm2-right-wall | 1.0 | 0.5 |
| nave-left-bay3 | 3.5 | 1.1 |

- The 2.9 is the soft end of the ledge's real shadow; the patch edge that gave 3.5 is gone.
- In `lightmap/phone-before-after.jpg` the rectangular patches are gone at the same two cameras and at the
  three extra spots.
- In the lightmaps themselves, the remaining large steps across cuts are real shading on separate coplanar
  pieces, such as niche floors against ledges and shadow ends. The nearest-texel metric is noisy (p95
  37 levels before, 23.6 after) and is not a clean criterion; the phone measure is the one to judge by.
- Atlases: 8.16 Mpx (stage 4: 7.5).

**Defect introduced by this stage (not fixed): a dark line on the facade panel frame's right edge**
(`lightmap/regression-facade-panel-frame-dark-line.jpg`).
- It is in the lightmap: it disappears with lightmaps off. It also shows in the note-1 stage-5 view.
- Only one texel row covers the frame's front fascia. Anisotropic lightmap filtering didn't remove it and was
  reverted.
- Proposed fix before the final bake: a density scale for "frame" (as entablatures already have), or a larger
  minimum island thickness for mouldings, so each face gets 3 or more covered rows. Then check the other thin
  mouldings.

**Bake time.** The rough bake now takes 26 min (stage 4: 8.6). Each of the three extra one-sample bakes per
group re-syncs the whole scene; the crossing group took 933 s. That adds about 10 min to the final bake.
Drawing these maps in numpy instead would remove the cost.

## 3. Maria's notes in the web

- `maria-notes/notes-web-stage3-4-5.jpg`: stage 3 (the build she saw), 4 and 5 at her four joints, 1280×800.
- The cameras stand on the walk line, eye 1.6 m above the platform, aimed at each joint:
  - note 1: x −2.2, z −6.0;
  - note 2: x 0.9, z −30;
  - note 3: x −0.6, z −26.5;
  - note 4: x 0.6, z −9.4.
- A desktop viewport was used because the pose has no pitch: on a phone frame the springing and entablature
  fall outside.

## 4. Checks on 5202

- Walk to the end door: OK.
- Taps: 9 of 9, in each of the three runs.
- Frame rate:

| | Stage 5 | Stage 4 |
|---|---|---|
| Idle | 60 fps | – |
| Walk, mean | 58.4 fps | 58.2 fps |
| p95 frame | 17.6 ms | 17.6 ms |
| Longest frame | 133 ms | 167 ms |

- Size: GLB 7.82 MB (stage 4: 8.54), 158.6k triangles.
- Memory on the A55, estimated: about 23 MB (stage 4: 22).
- Console:
  - the usual favicon 404;
  - an intermittent "Cannot read properties of null (reading 'copy')", in 2 of 3 walk-test runs. Probably a
    startup race in `Scene.tsx`: the frame loop reads `scene.background` before the effect sets it. The walk and
    taps are unaffected.
- No web code changed this stage.

**Other renders.** `web/` has the mid-nave, dome, end-door and bay 1 views. `arch/` also has `web-approach`,
`web-at-the-arch` and `web-looking-back`.

## Review (main session, 2026-11-20)

Checked `arch/web-start-fresco-framing.jpg`, `maria-notes/notes-web-stage3-4-5.jpg` and
`lightmap/phone-before-after.jpg`. The four commits are on hall-look.

- **Arch:** from the start view it frames the hall as the fresco does. The meander, beads, egg-and-dart and red
  band read. The hall's lines inside it are unchanged.
- **Maria's notes, now in the web:**
  - note 1's frame is closed and level in stage 4, but stage 5 adds the dark right edge;
  - note 2's archivolt sits on its impost;
  - note 3's entablature clears the vault;
  - note 4's niche is continuous.
- **Patches:** the rectangular patches are gone at all five cameras. The remaining vertical changes follow real
  planes (pilaster faces, recess corners).
- **Before the final bake:**
  - fix the frame's dark line and check the other thin mouldings for the same one-row problem;
  - fix the `scene.background` race;
  - the dome interior, if Maria approves the redesign.
