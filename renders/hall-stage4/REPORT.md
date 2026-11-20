# Hall stage 4: light × detail, joints by rule, recesses in every bay

## Summary

Commits on hall-look: 03bf3c7, a9865b5, 69ef8cb, d65f4b5. Not pushed or merged; main is untouched. No final
bake.

Maria can walk the rough bake at http://10.1.1.4:5202/. It has:
- light × tiled detail;
- both colour fixes;
- the joint fixes;
- recesses in every bay, with the Mucha, Klimt, Waterhouse, Van Gogh, Hokusai and Hiroshige on recess back
  walls under empty niches.

Desktop Chrome:
- the walk from start to end door works;
- all 9 taps pass (walk-up, deep zoom, Back);
- 60 fps at the vsync cap, p95 17.6 ms; one 167 ms frame, probably the first texture upload.

The Raphael view still lands on the fresco: 66 % of Blender's edge pixels have a web edge within 1 px, 82 %
within 4 px.

GLB 8.5 MB (6.3 MB of it KTX2). GPU on the A55 about 22 MB in total (17 MB textures, about 5 MB geometry).

Joints: the audit covered Maria's four notes.
- note1, note2 and note3 are located and fixed at their cause.
- note4 is most likely a lightmap seam, not geometry.
- The automated audit went from 78 overlaps / 114 open ends / 2 skewed frames to 0 / 0 / 0.

## How to run it

- **Dev server:** on 5202, detached. To restart:
  `cd ~/code/athens-gallery-hall/web && npx vite --host 0.0.0.0 --port 5202 --strictPort`.
- **Bake:** `tools/bake_hall.sh rough|final`, about 9 min rough. Settings in `params.BAKE`:
  - rough: 128 samples, 16 px/m;
  - final: 1024 samples, 28 px/m.
- **Bake steps:**
  1. `build.py` (model and `hall.json`)
  2. `bake.py` (light-only lightmaps, per-face factors, UVs, export)
  3. `tools/make_detail.py` (detail tiles)
  4. `tools/denoise_lightmaps.py`
  5. `tools/pack_hall.mjs` (KTX2 and meshopt)
- **Joint audit:** `blender -b blender/athens-hall.blend -P tools/joint_audit.py -- out.json`.

## Part 1: light × detail

**Light only.** Cycles bakes diffuse direct + indirect with the colour pass off, so no albedo goes into the
lightmap. Every light-linking and shadow-linking set-up is active; bounces still use the real materials.
- Lightmaps go on TEXCOORD_1.
- Density is chosen for light: 16 px/m rough, 28 final; mouldings ×1.4–2, facade ×0.8.
- No island is thinner than 4 px.
- Stored as light / 4.0 through the sRGB curve. Nothing clipped.

**Where each convention lives now:**
- **Lightmap, as a per-face factor:**
  - the right-side shade, halved: 0.775 on the right walls' undersides; 0.775 / 0.75 / 0.69 on faces turned
    to −X;
  - new: every face inside a right-hand recess also gets that shade;
  - new: the side walls' buff tint (1.0, 0.99, 0.88).

  The factors are a face attribute, baked as an emission pass and multiplied into the light. A light-only
  bake divides the material's colour out, so they can't stay in the material.
- **Per-material tint (baseColorFactor):** the far-end, drum and facade factors.
- **Separate detail textures, assigned per face by normal:** riser versus tread.

**Detail on TEXCOORD_0.** World-scaled tiling:
- planar by each face's dominant axis;
- arc length on the vaults, soffits and drum;
- floors start from their pattern's origin.

`tools/make_detail.py` (NumPy/OpenCV) draws one seamless 1024 px tile per key:
- the CC0 scans (Poly Haven `white_plaster_02`; ambientCG `Travertine009`, `Marble009`, `Marble014`), ramped
  to the fresco's colours;
- the painted mottling and speckle as periodic noise, so they wrap;
- the lower floor's painted pattern;
- the nave's lozenge slabs with marble veining;
- no cracks.

Tiles are KTX2 ETC1S with mipmaps, repeat wrap.

**Web.** colour = detail(uv0) × tint × lightmap(uv1) × lightScale, as an unlit MeshBasicMaterial, not
tone-mapped, anisotropy up to 8. Dimming around a painting scales the tint.

**Stone.** The two blocks beside the steps are stone. The Bosch's base is built in stone and baked; the grey
box is gone and its label stays.

**Colour.** sRGB medians from the start view.

| Region | Fresco | Stage 3 web | Stage 4 web |
|---|---|---|---|
| Facade beside niche (L) | 180,159,147 | 178,158,139 | 182,160,142 |
| Frontal face, bay 1 (L) | 203,181,170 | 201,176,157 | 201,176,155 |
| End wall | 229,208,199 | 221,202,188 | 222,200,188 |
| Drum band | 197,172,150 | 189,165,141 | 191,167,142 |
| Step riser | 191,175,162 | 176,163,147 | 181,167,147 |
| Vault ribs | 124,102,85 | 128,103,82 | 122,98,82 |
| Coffer cores | 109,89,74 | 110,90,71 | 104,85,71 |
| Broad left nave walls | 192,166,136 (G−B +30) | 208,181,162 (+19) | 210,181,153 (**+28**) |
| Broad right nave walls | 127,103,76 (+27) | 176,151,134 (+17) | 175,149,121 (**+28**) |
| Platform floor, white / rose | 231,214,217 / 174,136,134 | 239,215,191 / 151,123,119 (salmon) | **228,214,216** / 201,153,146 |
| Lower floor, white / mauve | 169,164,189 / ~133,105,125 | 186,172,167 / 110,88,93 | **170,164,192 / 136,104,122** |
| Mean \|log ratio\|, 12 regions | | 0.235 | 0.225 |

- Where nothing was meant to change, stage 4 is within a few levels of stage 3, except the vault and coffers,
  which are 3–6 levels darker.
- Deliberate corrections:
  - side walls now G − B 28 (fresco 27–30);
  - floors no longer salmon. The rose is still lighter than painted.
- The right-hand bays stay lighter than the fresco: that is Maria's halved shade.

## Part 2: joint rules

1. **Moulding runs** (entablature, base, capital band, string course, imposts) turn every corner with a mitre
   and keep their profile.
2. **A run ends only:**
   - against a perpendicular wall, or a member at least as deep that it dies into;
   - with a return into the wall;
   - where nobody can see it (the facade's outer edges, the end wall's far face).

   Never in mid-air.
3. **Ressauts:** the entablature breaks forward over every pilaster. Base and capital bands run continuously
   and wrap each pilaster's three faces.
4. **Archivolt on its impost:**
   - the archivolt is no wider than the impost is long from the jamb, and no deeper than the impost's top;
   - its bands land flush;
   - the impost dies into a pilaster that projects further.
5. **Springings:** the curve and the jamb are one sweep of the same profile, tangent and coplanar.
6. **Frames:**
   - one mitred sweep along the opening's edge, in the wall plane;
   - plumb and level;
   - the inner edge is the opening's edge: no reveal, no second outline.

   Open frames stand on a ledge that projects further than the frame.
7. **Vaults:** a vault springs on the cornice top at the wall face, and nothing crosses its intrados. Members
   under a vault end before it, with returns. Recess ceilings sit flush at the springing.
8. **Pendentive zone:**
   - the lunette blind arches run inside the arch line, crown at the drum ring, feet on the entablature;
   - the tondi fit inside their pendentive, clear of both (size solved in code).
9. **Small members** (triglyphs, grooves, discs) sit flush on their member. A triglyph stands over each
   pilaster's axis.
10. **Bases** sit on the floor, sunk 1 cm. At corners they mitre as one run, never overlap.
11. **Step nosings** return along exposed step ends.
12. **Solid overlaps** are allowed only where hidden: inside walls, below the floor.

**Audit** (`tools/joint_audit.py`):
- collisions, measured by penetration depth (≥ 5 mm);
- moulding ends that are neither within 1 cm of a surface nor inside a solid;
- frames more than 0.5° off plumb or level.

Before: 78 overlaps, 114 open ends, 2 skewed frames. After, including the recesses: 0 / 0 / 0. The 63
remaining contacts are under 5 mm, by design. Results in `joints/audit-before.json` and
`joints/audit-final.json`.

**Violations fixed in the parametric scripts:**
1. **note1, facade relief-panel frames (both sides):**
   - skewed 1.95°: corner directions were averaged without a mitre;
   - the frame sat 8 cm outside a 15 cm sunk panel, which made the double outline and the dark slot;
   - it overlapped the niche sill.

   Now a three-sided frame on the panel edge, under the niche's ledge; the panel is 6 cm deep.
2. **note2, end door:** a 0.60 × 0.11 m archivolt sat on an impost 0.50 m long with a 0.06 m top, so the
   outer band floated. Now:
   - archivolt 0.42 × 0.055;
   - impost running from the jamb into pilasters 0.25 deep, 0.45 from the jamb, 0.8 wide;
   - the pilasters carry Doric capitals.
3. **note3, end Doric entablature:** it spanned the full 11.8 m and ran up to 0.4 m into the second arm's
   vault. Now:
   - it runs pilaster to pilaster, breaks forward and returns into the wall;
   - its clearance to the vault is checked in code;
   - triglyphs are re-spaced to 1.52 m, one over each pilaster's axis.
4. **note4, curve stepping at the springing:** not located with certainty. The step coincides with a tone
   change, which matches a stage-3 lightmap seam: islands were cut every 2.5 m, and one cut fell at z 7.5,
   near the facade niches' springing at 7.87.

   Fixed by class anyway: every niche frame is rebuilt as one mitred sweep standing on a ledge. The light-only
   bake also makes seams much fainter.
5. **Crossing blind arches:** they collided with all four tondi (about 6 cm) and the drum ring. Now inside the
   arch line, with the tondi resized.
6. **Bay 1:** the vestibule base and facade base overlapped, and 10 imposts, bases and string-course ends were
   open. Now one continuous base, capital band and string course per side.
7. **Returns added:** 8 niche-ledge ends and 6 step-nosing ends were open.
8. **Facade niche ledge:** it crossed the screen's corner. Shortened.
9. **Bay-1 recess ceiling:** it had a 5 cm lip into the vault. Now flush.
10. **Side cornice and the deeper end pilasters:** the pilasters are placed so the cornice clears them.
11. **Niche interiors:** they had no material and rendered default grey. Now stucco.

**Sheets:**
- `joints/maria-notes-before-after.jpg`: her four crops beside the same joints after the fixes;
- `joints/before-after-workbench.jpg`: six joint types, same cameras, before and after;
- `joints/after-workbench-more.jpg`: recesses, vestibule corner, capital band, end door, step ends;
- `joints/workbench-before.jpg`.

## Part 3: recesses

Built to the same rules:
- full height to the springing, back walls at |x| 6.5;
- ceilings flush with the vault;
- one empty round-headed niche each, its frame standing on a returned ledge.

Spans:
- nave bay 2: 23.4–26.8;
- nave bay 3: 27.8–32.6, leaving a 0.8 m pier before the crossing;
- second arm: 47.6–50.4 and 51.4–54.2.

**Runs per side:** one continuous base, capital band and entablature, which crosses bay 1's vestibule mouth as
a lintel. The string course runs only where no niche rises through it and stops against the recess back
walls.

**`hall.json`:**
- places 3–6 (Waterhouse, Van Gogh, Hokusai, Hiroshige) sit on the recess back walls under the niches, each
  with its own wallX (4.55);
- places 7–10 sit on the second arm's recesses (unused);
- the label rule is per place: Hylas label under, the other three beside.

**Overlay:** `web/start-edges.jpg`, `web/start-side-by-side.jpg`, `web/start-blend.jpg`. The main lines are
unchanged, and the recesses appear where Raphael paints them.

## Screenshots

- **Stage 3 vs stage 4** at the same views: `web/before-after-views.jpg` (start, mid-nave, under the dome, end
  door, bay 1 with the Mucha and Klimt). New recess: `web/recess-bay2.jpg`. Singles in `web/`.
- **Phone-sized viewport** (891 × 412 CSS px, DPR 2), at walk-up distance, in `phone/`:
  - `pilaster-and-base-left.jpg`
  - `recess-corner-capital-band.jpg`
  - `coffers-from-below.jpg`
  - `bay1-left-recess.jpg`
  - `pilaster-base-right.jpg`

  The detail tiles give 500–1460 texels per metre, so moulding edges and the plaster and marble grain stay
  crisp. The light is soft (16 px/m).

## Size, memory, fps

**GLB 8.54 MB:**
- textures 6.26 MB: 10 detail tiles in ETC1S (1.4 MB) and 5 lightmaps in UASTC (4.9 MB);
- geometry about 2.3 MB, meshopt; 158 k triangles, 6 meshes, about 40 draw calls.

Lightmaps total 7.5 Mpx: 576×512, 896×768, 1344×1152, 2240×1792, 1088×896. The crossing atlas is only 39 %
filled.

**A55 GPU (estimate):**
- lightmaps: UASTC transcodes to ASTC 4×4, 8 bpp, about 10 MB with mips;
- detail: ETC1S transcodes to ETC2, 4 bpp, about 7 MB;
- geometry about 5 MB;
- total about 22 MB. Upper bound if all textures transcode at 8 bpp: 24 MB of textures.

**Final bake (estimate, not run):** about 23 Mpx of lightmaps, about 31 MB GPU, about 15 MB lightmap download
(GLB about 18 MB). About 3.5 h at 1024 samples, or about 1.7 h at 512, which is probably enough for light-only
maps.

**Desktop Chrome (M3):**
- load 1.2 s;
- idle 60 fps, p95 17.6 ms;
- walk 58 fps mean, p95 17.6 / p99 17.7 ms, with one 167 ms frame;
- phone-sized viewport with 4× CPU throttle: 60 fps, p95 17.5 ms (the GPU is not throttled);
- taps 9/9.

## Every limit

**Rough-bake artefacts** (128 samples, denoise h 4, 16 px/m):
- soft contact shadows and slightly blotchy gradients;
- seams still visible as faint tonal steps: on long walls at the 2.5 m cuts, a dark line in a pilaster base
  profile, one tone change on a recess wall;
- the crossing atlas packs poorly.

The final settings fade the seams. Removing them would need seam-aware filtering or fewer cuts.

**Light is not physical:**
- shadow linking;
- no sun on the vaults;
- the sky lights in one colour and is seen in another;
- the bay-1 bounce card;
- the halved right-side shade, now including the right-hand recesses;
- the buff side-wall tint;
- the far, drum and facade tints.

**Colour still off:**
- right-hand bays much lighter than painted (Maria's choice);
- coffer highlights about 35 % dark;
- the platform's rose lozenge lighter than painted;
- bay 1's frontal faces yellower than painted (G − B 21 vs 11);
- no gloss anywhere.

**Detail textures:**
- planar mapping leaves pattern seams on curved members (dome, pendentives, curved moulding faces, arch
  intrados);
- ETC1S is slightly blocky at close range (`DETAIL_CODEC=uastc` is sharper but about +10 MB);
- the mottling repeats every 0.7–2 m and is faintly visible on large walls.

**Joints:**
- the audit skips a moulding embedded in its own support, so it can't tell a correct 3 cm embed from a
  moulding pushed too far in;
- springing continuity is guaranteed by construction, not measured;
- note4 is not located for certain;
- `wall_plan()` assumes crossing A; the gate2 crossing would lose its pier wraps;
- hidden moulding ends remain at x ±16 and on the end wall's far face.

**Recesses:**
- proportions copy bay 1's reading and were not measured per bay;
- bay 3 is longer (4.8 m) than bay 2 (3.4 m) because crossing A grew the crossing;
- the niches are empty, as agreed.

**Web:**
- no loading progress for 8.5 MB;
- favicon 404;
- KTX2Loader is never disposed;
- frames and labels are lit by the old real-time lights;
- sky and the ground past the door are unchanged, as asked.

**Not tested:** the A55 itself, iOS/Safari, GPUs without ASTC or ETC2, the final bake.

## Time

About 1 h 20 min for stage 4 (17:00–18:16):
- light × detail: about 30 min;
- joint audit and fixes: about 35 min;
- recesses: about 15 min;
- plus three rough bakes, about 9 min each.

## Review (main session, 2026-11-20)

Checked `joints/maria-notes-before-after.jpg`, `web/before-after-views.jpg`,
`phone/recess-corner-capital-band.jpg` and `phone/bay1-left-recess.jpg`. The four commits are on hall-look,
and the server answers on 5202 with an 8,535,748-byte `hall.glb`.

- **Joints:** in the workbench close-ups, note1 is a closed, level frame under its ledge, note2's archivolt
  lands on its impost, and note3's entablature clears the vault. note4's niche frame is one continuous sweep.
  The "after" crops are Blender workbench renders, not the web at Maria's exact viewpoints, so she should
  confirm them in the walk.
- **Whole views:** the walls are buff rather than pink, the step blocks and the Bosch's base are stone, and
  the recesses read in every bay.
- **The report understates the seams.** At walk-up distance on the phone viewport they are not faint. The
  walls show rectangular patches of different tone, with hard horizontal and vertical steps (both phone
  close-ups, beside the niche ledge and around the Mucha). Built geometry next to patchwork light reads as
  "badly constructed", which was Maria's complaint. Before the final bake, the lightmap should not cut flat
  walls into islands, or should stitch across the cuts. A phone close-up should show no tone step over
  a couple of levels on a flat wall.
