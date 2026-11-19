# Hall stage 2: the whole hall finished, beside the fresco

Branch `hall-look`, commits `520508a` (code) and `411d519` (renders). Blender 5.2 Cycles, 128 samples
with denoising. Option A and the physical-sun variant were rendered at 96 and 64 samples. Everything
is at the 100 % reading.

Pixel coordinates (u, v) are on the 3840 × 2661 scan; crops were read on the full 20111 px scan.

## Verdict

From Raphael's camera the finished hall reads as the painted building:
- the coffered barrels and the arch soffits carry the painted pattern;
- bay 1 has its frontal face, full-height recess and niche on both sides;
- the end wall has the painted triglyph frieze;
- the drum, pendentives with tondo frames and dome are complete;
- the right side is in shade and the left is lit, as Raphael paints them.

Across twelve broad regions where both images show the same building parts, render and fresco differ
by a mean of about 20 % in linear light. The vault ribs, coffer panels, drum, end wall, steps and
frontal faces are within 0–15 %.

It does not yet look like the fresco:
- The surfaces are clean and slightly pink where the fresco is buff and olive.
- Bays 2–3 and the second arm have flat walls. Raphael paints deep recesses there with statues, which
  is why the fresco's right side is darker (127, 103, 76) than the render's (179, 156, 136).
- The crossing size is still the approved one (see "Crossing").

## What to look at

| File | What it shows |
|---|---|
| `raphael-side-by-side.jpg`, `hall-raphael.jpg` | The whole hall from Raphael's camera beside the fresco (approved crossing). |
| `raphael-edges.jpg`, `raphael-blend.jpg` | Edge overlay and 50/50 blend. |
| `crossing-options.jpg` | The front and back arch of each crossing option, drawn on the fresco. |
| `raphael-side-by-side-crossingA.jpg`, `raphael-crossingA-edges.jpg`, `s2-dome-crossingA.jpg`, `s2-midnave-crossingA.jpg` | Option A (square 11.8 m), finished. |
| `eye-level-sheet.jpg`, plus `s2-entrance.jpg`, `s2-midnave.jpg`, `s2-dome.jpg`, `s2-door.jpg`, `s2-dome-up.jpg` | Eye level (1.6 m above the platform) at the entrance, mid-nave, under the dome and at the end door; the dome from below. |
| `bay1-options.jpg`, `bay1-{below,inside}-{left,right}.jpg` | The Mucha (left) and the Klimt (right) in bay 1. |
| `closeup-coffers-vs-fresco.jpg`, `closeup-capital-vs-fresco.jpg` | Render crops beside the same fresco crops. |
| `hall-raphael-physical.jpg` | The same view with a physical sun (no shadow linking, no shade factors; 64 samples). |
| `evidence/` | The fresco crops the new readings come from. |

## 1. Crossing: checked, not enlarged — Maria's call

**Readings.** I fitted circles to the painted edges (`evidence/crossing-front-opening-*`,
`crossing-back-arch-*`):
- **Front opening:** centre v 1087.7, radius 401.8 px, crown v 686.
- **Back arch:** crown v ≈ 937; impost at v 1217–1230; half-width 293 px at the impost.

| Option | Front arch (y, R) | Front crown | Back arch | Back crown / springing | Crossing |
|---|---|---|---|---|---|
| gate2 (approved, default) | 32.5, 5.475 | v 662 (24 px high) | 43.45 | 942.5 (+5) / 1229 (≈0) | 10.95 m square |
| A (Maria's decision) | 34.2, 5.9 (the nave barrel runs on) | v 689 (+3) | 46.0 | 967.6 (+31 px = 0.6 m) / 1259 (+29) | 11.8 m square |
| A2 (shifted) | 33.6, 5.9 | v 669 (−17) | 45.4 | 957 (+20) | 11.8 m square |

**What lands in option A:**
- The far door: unchanged (y 55).
- The second arm's barrel and its far end: unchanged.
- The drum: its heights are scaled with the crossing's depth (window band 20.6–23.8, top 24.0), so its
  visible back half stays on the painting.

**What doesn't:** the back arch, i.e. the start of the second arm. Its crown and impost sit 0.6 m
lower than painted.

**Why.** Read by heights (springing 12.3), the painted arches give a front arch of R 6.1 at y 34.5 and
a back arch of R 5.6 at y 43.5. That is about 9 m deep against 11–12 m wide. Read by widths, an
11.8 m square fits, but then the back arch springs about 0.9 m higher than the front one. A square
crossing with equal arches can't land both arches at this camera. The painting isn't consistent on
this point.

**Options for Maria:**
- **gate2:** keep the approved crossing.
- **A:** enlarge; the back arch lands 0.6 m low.
- **A2:** split the error between the two arches.
- **B (not built):** 11.8 × 10.1 m. Both arches land, but the crossing isn't square, so the drum and
  dome would have to be oval.

**What is already built.** All three square options are built and switchable with `CROSSING=…`. In
options A and A2 the coffers run through the front arch's soffit to a thin light edge. In gate2, where
the arch is narrower than the vault, the 0.43 m ring between them is now a plain face, still with the
thin light edge. The stage-1 archivolt is gone in every option.

**What would change in hall.json with A:**
- dome: `wallX` 3.8325 → 4.13, `z` −26.5825 → −28.07, `length` 7.665 → 8.26.
- places 5–6: bay width 2.73 → 3.92.
- places 7–10 (unused): move and narrow to 2.52.

## 2. Bay 1 as painted (both sides)

The pixels correct my stage-1 description: there is no visible jamb at |x| = 5.9 behind the facade.
Both sides show the same three things (`evidence/bay1-top-both-sides-recess-cornice.jpg`,
`bay1-walls-both-sides.jpg`):

1. **A frontal face** where the model had the facade's 3 m jamb. It has horizontal mouldings at
   u 1040–1160 (left) and 2652–2800 (right). Its inner edge reads at y 17.5 (left) and 18.66 (right).
2. **A full-height recess.** The cornice in bay 1 recedes along a line through the vanishing point,
   with x/(z − eye) = 0.61–0.62 on both sides. That puts it at |x| ≈ 6.4 at z 12.3, so the bay-1 wall
   is set back the full height. The recess ends at the first pier's ressaut (frontal, v 680–690,
   y ≈ 21.7). That fits the pilaster at 22.4 with its cornice projecting, and the coffer field starting
   at 22.3–22.9. The "first pier at 21.9" from stage 1 was this cornice corner. The pilaster stays at
   22.4.
3. **Statue niches** at u 1170–1206 (left) and 2606–2647 (right). On the recess wall these read at
   y ≈ 19.9 and 21.3: the painting isn't symmetric.

**The model, symmetric:**
- front screen 15.5–16.2;
- vestibule 16.2–18.1, |x| ≤ 7.3, z to 10.45. Its back wall is the frontal face. It is hidden from
  Raphael's eye except that face;
- short block 18.1–18.9;
- recess 18.9–22.4, back wall at |x| 6.5, full height to the springing. The entablature runs into it
  and round the first pilaster; there is no string course in bay 1;
- empty niche 1.2 × 4.3 m (z 5.3–9.6), 0.35 m deep, centred y 20.6, with a moulded frame and sill.

**Mucha and Klimt** (`bay1-options.jpg`). The niche is high: its sill moulding is 2.93 m above the
floor at web scale. The paintings' tops are at 2.24 m (Mucha) and 2.09 m (Klimt). So the niche is not
where a painting hangs, and both hang on the recess's back wall under the niches.

The recess wall is 3.5 m (2.45 m at web scale):
- **Mucha** 0.65 m: label beside fits (needs 1.69).
- **Klimt** 1.74 m (1.86 with frame): fits, but the label goes under (beside would need 2.78).

The alternative "Mucha inside its niche" is rendered: its centre would be 4.4 m above the floor at
web scale, too high to look at. The Klimt can't go inside a 1.2 m niche. The vestibule's back wall
(1.9 m, 1.33 at web) takes the Mucha with the label under, but not the Klimt; this wasn't rendered.

**hall.json, places 1–2 (any crossing option):**
- `z` −14.315 → −14.42;
- `bay` [−12.95, −15.68] → [−13.23, −15.68];
- `bayWidth` 2.73 → 2.45;
- **new per-place `wallX` 4.55** (the recess wall). `Scene.tsx` uses one `wallX` for every place, so
  this needs a web change.

Unchanged in gate2: `door` (z −38.5, width 5.138, springZ 5.292), `walkEnd` (−37.45), the dome walls
(wallX 3.8325, z −26.5825, length 7.665), places 3–10, and the global `wallX` 4.13.
`tools/stage2/hall_json_diff.py` prints all of this; nothing was written.

## 3. Surface

- **Coffers:** the painted marble mottling is noise at about 16 cm over the CC0 marble scan, ±60 % on
  the panels and risers.
- **Ribs:** fine painted speckle (dark specks 35 % darker, about 1 cm) over a faint mottle.
- **Stone and stucco:** ±4–5 % mottle.
- **Left out on purpose:** the fresco's cracks and stains.

## 4. The rest of the hall

**Crossing:**
- Both transverse arches have coffered soffits (painted on the back arch; designed on the front in
  gate2).
- Thin light edge on the faces towards the crossing.
- The closed side walls are stucco, with a blind-arch moulding round each lunette.
- Empty tondo frames on all four pendentives: moulded ring with a plain disc, r 0.7 m, on the
  diagonals at 0.68 × the half-span above the springing. The painted tondi sit further out than the
  pendentives allow, so the positions are designed.
- Drum: base ring on the pendentives, sill cornice, top cornice, and 18 pilasters between the windows.
- Dome (not shown in the fresco, so designed): a rib grid of 5 rings × 28 on the shell.

**Facade:**
- the string course is a moulding now, returning onto the screen's jamb;
- moulded frames on the niches and relief panels, which stay empty;
- niche sills and a base along the front;
- the entablature crosses the facade front at 10.5–12.3. The fresco's frame hides that height, so this
  is designed.

**Second arm:** coffered barrel (the field starts at the back arch), a pilaster mid-arm, entablature
and string course continuous with the nave.

**End wall:** the painted Doric entablature: architrave 12.64–13.36, triglyph frieze 13.36–14.28 with
triglyphs every 1.64 m (0.36 m wide), cornice to 14.57. **The brief said "balustrade"; the pixels show
a triglyph frieze (`evidence/end-wall-triglyph-frieze.jpg`), so that is what I built.** Also: a door
archivolt (two fasciae and a cyma), imposts, and pilasters beside the door (painted at u 1720–1760 and
2110–2150).

**Floors and steps:**
- Lower floor as painted (`evidence/lower-floor-plan-unroll.jpg`): mauve fields holding a white square
  ring, set in white bands. The module is 1.68 × 0.95 m and the colours are darkened to the painted
  foreground.
- The platform has the hall's slab pattern everywhere (designed).
- Steps: white marble treads, risers in the painted colour (191, 175, 162), small round nosings
  (designed).

**Entablature:** one continuous run per side, from the facade front at x ±16 round the jamb, into
bay 1's recess, over every pilaster, round the crossing piers and into the end wall. It no longer has
cut ends anywhere inside the hall.

## 5. Light and colour

The base is unchanged: a sun from the front right, shadow-linked so that the big occluders don't block
it, as in stage 1. Added in stage 2:
- **Shadow linking extended:** every right-side object, all vaults and soffits, the facade, the
  transverse arches, the pendentives, drum and dome are non-blockers. The vaults and arch faces take
  no sun.
- **Sky:** light colour (0.95, 0.93, 0.45), more olive than before. Sun colour (1.0, 0.98, 0.9).
- **Bay-1 soffit:** a 4 kW area light on bay 1's floor, linked to the bay-1 vault band only.
- **Raphael's right side** (material factors): faces turned to −X on the right × (0.55, 0.5, 0.38);
  downward faces on the right × 0.55.
- **Far end:** end-wall materials lighter and cooler × (1.3, 1.43, 1.56).
- **Drum:** × (0.75, 0.74, 0.65).
- **Facade front:** × (0.7, 0.68, 0.72).
- **Coffer treads:** 1.5 × the ribs.
- **Sun azimuth:** I tried 50° (from frontal versus left-wall ratios of broad regions). It made the
  result no better (mean error 0.214 against 0.207) and darkened the first pier's frieze, so I kept 39°.

**Final comparison** (sRGB medians; ratio = fresco ÷ render, linear):

| Region | Fresco | Render | Ratio |
|---|---|---|---|
| Facade L beside niche | 180, 159, 147 | 184, 164, 142 | 0.95, 0.93, 1.08 |
| Facade R beside niche | 161, 140, 130 | 195, 177, 155 | 0.65, 0.60, 0.68 |
| Frontal face L / R (bay 1) | 203, 181, 170 / 205, 184, 172 | 204, 180, 159 / 191, 170, 150 | 0.99–1.16 / 1.17–1.35 |
| Left nave walls (broad) | 192, 166, 136 | 208, 183, 163 | 0.84, 0.81, 0.67 |
| Right nave walls (broad) | 127, 103, 76 | 179, 156, 136 | 0.47, 0.41, 0.29 |
| Left wall, entablature zone | 141, 117, 95 | 143, 116, 100 | 0.97, 1.02, 0.89 |
| Right wall, entablature zone | 100, 79, 62 | 109, 86, 68 | 0.83, 0.84, 0.83 |
| End wall | 229, 208, 199 | 223, 203, 192 | 1.06, 1.06, 1.08 |
| Drum band | 197, 172, 150 | 194, 172, 148 | 1.03, 1.00, 1.03 |
| Step riser | 191, 175, 162 | 191, 176, 159 | 1.00, 0.99, 1.04 |
| Vault ribs | 124, 102, 85 | 126, 101, 81 | 0.97, 1.02, 1.10 |
| Coffer cores / darkest 30 % | 109, 89, 74 / 86, 71, 60 | 109, 88, 70 / 85, 70, 55 | ≈1.0–1.2 |
| Coffers, lightest 40 % | 141, 117, 98 | 123, 100, 80 | 1.34, 1.40, 1.52 |

**Stage-1 fixes:**

| Fix | Result |
|---|---|
| Shade too mauve | Right side in the entablature zone: G − B +18 against +17 painted. The old pilaster box (now on the first right pier's cornice front) is still +16 against +31. |
| Bay-1 soffit too dark | Now 207, 179, 149 against 188, 168, 158: slightly bright and too yellow. |
| Right cornice soffit too bright | 108 against 105. |
| Treads and highlights too dark | Step risers match. The coffers' lightest 40 % are still too dark (×1.3–1.5). The painted step nosings can't be compared: the model's nosing lands 5 px off. |
| Cut entablature ends | Fixed. |

**Bake check.** Bakes respect light linking, so the main light can be baked as it is. I baked a floor
under a box with a sun straight down (`tools/stage2/bake_linking_test.py`, CPU and Metal):

| Setup | Floor under the box |
|---|---|
| Plain sun | 0.000 |
| Box excluded from the sun's blockers | 0.955 |
| Floor excluded from receiving | 0 |

## 6. Main dimensions

The camera and the main dimensions are unchanged; the projection checks print the same values as
before. Detail-level changes:
- End wall top 14.3 → 14.57 (painted cornice).
- Facade niches 0.9 → 0.5 m deep, to fit the 0.7 m front screen.
- The facade block is cut by the bay-1 vestibules, and the nave walls by the bay-1 recesses.
- The facade-front entablature is new.

In gate2 nothing that hall.json carries moves, except places 1–2.

## 7. Reconstructed vs designed

**Reconstructed from the fresco:**
- the crossing measurements;
- bay 1's frontal faces, full-height recess and cornice line, niche height and approximate position;
- the end wall's Doric entablature and triglyph spacing, the door archivolt and pilasters;
- the lower floor's pattern and colours;
- the back arch's coffered soffit;
- the drum's banded cornices;
- the steps' riser colour;
- all calibration colours;
- plus everything listed as reconstructed in the stage-1 report.

**Designed by me:**
- the vestibule's depth (16.2–18.1) and height;
- the recess depth (|x| 6.5, painted 6.4–7.0) and the niche's width and depth;
- every new moulding profile;
- the tondo positions and frames, the drum pilasters, the dome ribs, the blind arches;
- the facade-front entablature and base;
- the platform's floor pattern;
- the step nosings;
- the second arm's pilaster position (mid-arm; 49.6 in gate2);
- the light conventions and material factors in §5.

## 8. Everything not real, simplified or untested

**Geometry**
- The crossing is the approved size. Maria's enlargement is built but not the default (§1).
- Bays 2–3 and the second arm: flat walls with pilasters. The fresco's recesses, niches and statues
  there aren't modelled; this is the main reason the right side reads lighter than painted.
- Bay 1 is symmetric. The painting isn't: the frontal faces differ by about 1.2 m in depth between
  sides, the niches by about 1.4 m.
- The vestibule's interior (hidden from Raphael's eye) is designed. Its recess walls behind the frontal
  face are a 1.9 m bay.
- Tondi: plain discs in moulded rings, placed on the diagonals. The painted ones lie further out.
- The dome isn't in the fresco; the rib grid is designed.
- The pendentives are a sphere cut, as before.
- Drum pilasters: plain boxes, no capitals.
- Triglyphs: boxes with three dark slots, no guttae.
- No balustrade (the brief asked for one; the fresco shows a triglyph frieze).
- The relief panels are empty frames.
- The facade's pilaster strips beside the niches aren't modelled.
- The facade-front entablature is invented (the fresco's frame hides that height).
- The first left pier's entablature ressaut renders darker (134) than painted (200), and I haven't
  found why.
- Outside the walls there is still a flat ground and the flat painted-blue sky. Through the end door
  the visitor sees a bare plane.
- A recess impost and base stop with exposed profile ends at the vestibule mouth.

**Light and colour**
- **Not physical:**
  - shadow linking;
  - no sun on the vaults;
  - the sky lights one colour and shows another;
  - the bounce card over bay 1;
  - the right-side shade factors;
  - the far, drum and facade tints.
- All of these are painterly corrections, listed in `params.py`. The physical sun is in
  `hall-raphael-physical.jpg`.
- Remaining mismatches:
  - right nave walls ×0.4 (geometry, see above);
  - right facade ×0.6;
  - left walls too blue (B ×0.67);
  - coffer highlights ×1.4;
  - bay-1 soffit slightly bright and yellow;
  - the first left pier's ressaut ×2.4.
- In eye-level views the right walls are a strong brown. That is Raphael's convention applied to a
  walk.
- The colour reference is still the Wikimedia "Chroma denoise" photo.
- Sun elevation 35° is a choice.
- The calibration boxes were partly mis-placed in stage 1:
  - the "lit wall" and "shaded wall" boxes fell on the painted statue niches;
  - the "bay-1 soffit" box falls on the model's entablature on the left.

  Stage 2 replaced them with broad regions and with boxes I checked by ray-casting.

**Materials**
- Box projection, no UVs: not bakeable as is.
- The painted mottling and speckle are procedural noise, not read from the fresco's patterns.
- The shade factors depend on position and normal. For a bake they must go into baked albedo, or a
  per-orientation tint in three.js.

**Untested**
- No bake of the hall (only the linking test).
- No export: the per-place `wallX` field doesn't exist in the web code.
- Nothing seen in three.js or on the A55.
- Not every junction checked from every angle.
- The bay-1 cameras sit near the facade and partly look back out of the opening, so some sky shows at
  the frame edge.

## 9. Bake and web cost (estimates)

**Size of the finished hall:**
- 99.7 k triangles over 3,871 m², hidden faces included.
- 3.06 MB as GLB with positions and normals only, uncompressed; about 0.8–1 MB with meshopt.

**Recommended route** (stage 1's option A): tiled detail textures plus baked lightmaps on UV1, with
the shade and far tints baked into per-object albedo.
- About 6 Mpx of lightmap at 40 px/m (80 on the vaults), at 70 %: two to three 2048² maps.
- About 2–3 MB as KTX2, about 8–10 MB of GPU memory, plus about 6 MB for the detail textures.

The bake itself is untested beyond the linking test.

## 10. Time and what's next

**Time:** about 1 h 30 min of work (23:05–00:37). Renders took about 25 min of that.

**Waiting on Maria:**
- the crossing size (gate2, A, A2 or B);
- the hanging (Mucha label beside, Klimt label under);
- the balustrade question.

**Estimates:**
- After her choice: about 30 min to switch and re-render.
- Bays 2–3 and the second arm's recesses with niches, as painted: 1.5–2.5 h. This is the biggest
  remaining gap to the fresco's look.
- Bake and web integration (UVs, lightmaps, shade tints, per-place `wallX`, hall.json, A55 test):
  3–4 h, as estimated before.

## Review (main session, 2026-11-20)

Checked `raphael-side-by-side.jpg`, `crossing-options.jpg`, `eye-level-sheet.jpg` and
`bay1-options.jpg`.
- From Raphael's camera the hall now reads as the painted building. The arcs in `crossing-options.jpg`
  sit where the table says: in A the front arch is on the painted opening and the back arch visibly
  inside the painted one.
- At eye level the right-hand walls are a flat, muddy brown along the whole walk. That is the shade
  factors (× 0.55, 0.5, 0.38) applied outside the one viewpoint they were set for. It's the most
  visible problem in the walk.
- Through the end door the visitor sees a flat green plane under a flat blue sky.
- The "balustrade" in the brief came from the stage-1 estimate's wording, not from Maria. The triglyph
  frieze is right; there is nothing to decide.
