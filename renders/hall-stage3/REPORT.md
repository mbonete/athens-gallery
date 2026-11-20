# Hall stage 3: the baked hall, walkable in the gallery

## Summary

The baked hall is walkable in the web app in this worktree (branch `hall-look`). The dev server is on
port 5202 (Mac: http://localhost:5202/; phone on the same Wi-Fi: http://10.1.1.4:5202/).

Desktop Chrome passed everything tested:
- the walk from Raphael's view to the end door;
- a tap on each of the 9 paintings: walk-up, deep-zoom swap, Back;
- the labels;
- 60 fps (vsync cap), p95 frame time 17.6 ms.

The start view lands on the fresco as Blender's render does: a 50/50 blend of web and Blender shows no
doubling.

GLB: 7.2 MB. GPU texture memory: 11.2 MB. This is the **rough** bake. It is soft up close and shows faint
seams. The final bake needs a decision on sharpness first (see the end).

Commits:
- `1b8f8ed` Maria's decisions
- `deaa2ea` bake pipeline
- `7ce43d0` bake fixes
- `a1d2493` web integration
- `bbdf5f9` renders

## How to run it

- **Running already:** Vite on port 5202, started detached with `--host 0.0.0.0` (log in
  `blender/build/vite-5202.log`).
- **Restart:** `cd web && npx vite --host 0.0.0.0 --port 5202 --strictPort`.
- **Painting assets:** `web/public/paintings` is a symlink to `~/code/athens-gallery/web/public/paintings`
  (git-ignored). Main is only read through it.
- **Re-bake** (e.g. after the recesses): `tools/bake_hall.sh rough` or `tools/bake_hall.sh final`.
  - It rebuilds the hall, bakes it, fills and denoises the atlases, then writes `web/public/models/hall.glb`
    and `web/src/data/hall.json`.
  - Needs `basisu`: Homebrew's `basis_universal` was installed for this. Also needs `web/node_modules`,
    which now include `@gltf-transform` and `meshoptimizer` as devDependencies.
  - Settings live in `params.BAKE`:
    - rough: 96 samples, 22 px/m, margin 3 px, gap 1.5 px;
    - final: 1024 samples, 40 px/m.
- **Opening-view check:** `?fresco` frames the canvas at the fresco's proportions. `tools/web_overlay.py`
  overlays a screenshot of it on the fresco and on Blender's render.

## What changed

**Maria's decisions**
- **Crossing A is the default** (`params.CROSSING`). Changes in `hall.json`:
  - dome: wallX 4.13, z −28.07, length 8.26;
  - places 5–6: bayWidth 3.92;
  - places 7–10 also moved with the larger crossing: 7–8 at z −34.02, 9–10 at z −37.24, width 2.52 each.
    They hold no paintings.
  - unchanged: door z −38.5, walkEnd −37.45.
- **Right-side shade halved:**
  - downward faces 0.55 → 0.775;
  - faces turned to −X (0.55, 0.5, 0.38) → (0.775, 0.75, 0.69).
- **Mucha and Klimt on bay 1's recess back wall, below the niches.** Places 1–2: z −14.42,
  bay [−13.23, −15.68], bayWidth 2.45, wallX 4.55.
  - `hall.json` now has a `wallX` per place (4.13 for places 3–10). `walk.ts` uses it and falls back to the
    hall's.
  - The label rule (`besideFits`) already used each place's own width. At 2.45 m the Mucha's label goes
    beside it and the Klimt's under it; the screenshots confirm both.

**Bake** (`blender/scripts/bake.py`)
- Meshes are grouped by where they stand along the hall: front, facade, nave, crossing, second arm.
- Hidden faces (765) are deleted first, so they take no atlas space:
  - everything beyond the side walls behind the facade;
  - floor undersides;
  - the end wall's far face;
  - the drum's and dome's outer shells.
- Each object is unwrapped on its own. Surfaces are cut into islands at most 2.5 m long, each island is
  scaled to the texel density, and all islands are shelf-packed into one atlas per group. Atlases are
  trimmed to the rows they use, so they aren't square.
- **Cycles bakes Combined** (diffuse direct + indirect) with every light-linking set-up of the scene active.
  A test confirmed that bakes honour light linking.
- Glossy is off. The world's camera-ray switch is pinned to the light colour.
- The atlases are saved through the Standard view transform, so they hold the calibrated colours.
- Each group is joined into one mesh with only the lightmap UV, and exported at 70 %.

**Post-processing**
- `tools/denoise_lightmaps.py` fills the unbaked space from the islands (push-pull, so mipmaps never pull in
  black), then denoises (non-local means).
- `tools/pack_hall.mjs` (gltf-transform):
  - textures: KTX2, Basis UASTC with mipmaps and Zstandard;
  - geometry: meshopt.

**Web** (`Scene.tsx`, `App.tsx`)
- GLTFLoader with KTX2Loader (transcoder in `public/basis/`) and the meshopt decoder.
- Every hall mesh is a `MeshBasicMaterial` with its atlas, not tone-mapped.
- Dimming around a painting scales the colour.
- No shadow maps. The remaining lights only shade the frames and the doorway's base.
- The background is the fresco's sky (175, 175, 245).
- A dev-only `window.__gallery` hook drives the scripted tests.

**Geometry fix:** bay 1's recess now has a ceiling at the springing. In Blender the hidden vault backing
closed that gap; the web model has no backing, so the sky showed through a slot.

## Colour numbers (sRGB medians; ratio = fresco ÷ render, linear)

| Region | Fresco | Blender, stage-2 shade | Blender, shade halved | Web, rough bake |
|---|---|---|---|---|
| Right wall, entablature zone | 100, 79, 62 | 110, 86, 68 (0.83) | 126, 101, 83 (0.60) | 118, 95, 78 (0.70) |
| Right cornice soffit | 105, 83, 65 | 108, 85, 67 (0.94) | 126, 100, 83 (0.68) | 118, 93, 77 (0.78) |
| Right pilaster in shade | 152, 125, 94 | 152, 132, 117 | 163, 140, 123 | 163, 141, 123 |
| Right nave walls (broad) | 127, 103, 76 | 180, 157, 137 | 185, 161, 141 | 176, 151, 134 |
| Left nave walls (broad) | 192, 166, 136 | 209, 183, 163 | 210, 184, 164 | 208, 181, 162 |
| Frontal face R (bay 1) | 205, 184, 172 | 191, 170, 150 | 192, 171, 151 | 188, 167, 148 |
| Facade L beside niche | 180, 159, 147 | 184, 164, 142 | 184, 164, 142 | 178, 158, 139 |
| End wall | 229, 208, 199 | 224, 204, 192 | 225, 205, 193 | 221, 202, 188 |
| Drum band | 197, 172, 150 | 191, 170, 146 | 193, 171, 147 | 189, 165, 141 |
| Step riser | 191, 175, 162 | 192, 176, 159 | 191, 176, 159 | 176, 163, 147 |
| Vault ribs | 124, 102, 85 | 127, 102, 82 | 130, 104, 83 | 128, 103, 82 |
| Coffer cores | 109, 89, 74 | 109, 89, 70 | 111, 90, 71 | 110, 90, 71 |
| Mean \|log ratio\|, 12 broad regions | | 0.210 | 0.243 | 0.235 |

- **G − B on the right side** (entablature zone): fresco +17, before +18, after +18. The pilaster box stays
  at +17 against +31 painted.
- **Effect of halving:** the right side is lighter, so it moves away from the fresco's darker shade (mean
  0.210 → 0.243). That was Maria's decision.
- **Web against Blender:** within a few levels on most regions. The step risers are 8 % darker in the web:
  the rough bake is darker there than Cycles' camera render.

Sheets: `blender-shade-before-after.jpg`, `blender-raphael-side-by-side.jpg`, `blender-eye-level-sheet.jpg`,
`web-vs-blender-start.jpg`.

## Sizes and memory

**`hall.glb` (rough):**
- 7.17 MB in total: 6.04 MB of KTX2 UASTC textures and about 1.1 MB of meshopt geometry.
- 137,450 triangles, 147 k vertices, 6 meshes (6 draw calls for the hall).

| Atlas | Size (px) |
|---|---|
| front | 704 × 576 |
| facade | 1088 × 960 |
| nave | 1664 × 1408 |
| crossing | 2112 × 1664 |
| arm2 | 1152 × 960 |
| **Total** | **8.2 Mpx** |

**GPU memory:**
- The A55 (Mali-G68) transcodes the textures to ASTC 4×4; the Mac to BC7. Both are 8 bpp, giving
  **11.2 MB with mipmaps**.
- Geometry adds about 3–4 MB (positions, UVs, indices; no normals).
- Worst case, a device with no compressed format: about 45 MB as RGBA32.

**Final bake (estimated, not run):** 40 px/m gives about 27 Mpx.

| Option | Download | GPU memory | Notes |
|---|---|---|---|
| UASTC | about 20 MB | about 36 MB | fits the phone |
| ETC1S | about 6 MB | about 36 MB | lower quality |

Bake time at 512–1024 samples: about 2–4 h.

## Frame rate (desktop Chrome, M3, scripted test)

| Case | Result |
|---|---|
| Load to ready, localhost | 1.2 s |
| Idle at the start | 60 fps, p95 17.6 ms |
| Walk start → end door (keyboard) | 59.3 fps, p95 17.6 ms, p99 17.7 ms; one 83 ms frame (likely a texture upload) |
| Phone-sized viewport (891 × 412 CSS, DPR capped at 2), CPU throttled 4× | 60 fps, p95 17.4 ms |

60 fps is the vsync cap, so these numbers don't show the headroom. The throttling only slows the CPU; it
says nothing about the A55's GPU.

**Taps:** all 9 paintings (Mucha, Klimt, Hylas, Van Gogh, Hokusai, Hiroshige, Kandinsky, Titian, Bosch)
passed walk-up → detail → Back to walking. The walk ends 5.5 m before the Bosch, as before.

## Raphael view self-check

- `web-start-side-by-side.jpg`: the fresco and the web start view side by side.
- `web-start-edges.jpg`: edges over the fresco (Blender's in cyan, the web's in red).
- `web-start-blend.jpg`: web and fresco 50/50.
- 65 % of Blender's edge pixels have a web edge within 1 px, 71 % within 2 px, 79 % within 4 px. The ones
  missing are low-contrast edges that the softer web image doesn't produce.
- A 50/50 blend of web and Blender shows no doubling.

## Screenshots

- `web-sheet.jpg`: all of the views below in one sheet.
- `web-start.jpg`: start view.
- `web-midnave.jpg`: mid-nave, bay 2.
- `web-dome.jpg`: under the dome, facing down the walk.
- `web-end-door.jpg`: end door.
- `web-bay1-mucha.jpg`, `web-bay1-klimt.jpg`: bay 1, both paintings in the recess, from the app's link point
  6 m before them.
- `web-detail-mucha.jpg`, `web-detail-klimt.jpg`: the deep zoom after a tap.

## Every limit

**What the rough bake does that the final one won't**
- **Noise:** 96 samples plus non-local-means denoising leave soft, slightly blotchy light. Contact shadows
  are smeared, and the coffers' mottling and the ribs' speckle are mostly lost.
- **Blur:** at 22 px/m one texel covers 4.5 cm (3.2 cm at web scale). Floor-pattern edges, the travertine
  and the thin mouldings are blurry, the lower floor in the foreground most of all. 40 px/m halves this.
- **Seams:** each 2.5 m island cut shows as a faint change of tone, visible on the steps and long
  mouldings. With a 3 px margin and 1.5 px gap there is some bleed at small mip levels. The final settings
  (4 px / 2 px) and more samples reduce the seams but won't remove them; that would need seam-aware
  filtering.
- **Final settings not run.** 40 px/m may still look soft at arm's length on a phone. Every surface's detail
  is baked into one unique texture, so sharpness costs memory. If that's not enough, the alternative is the
  stage-1 plan: lightmap × tiled CC0 detail textures. That is a pipeline change.

**Web rendering**
- Unlit and static: no specular or gloss on the marble, no change of light.
- Frames, labels and the Bosch's base are lit by the old real-time lights (hemisphere plus a sun from the
  front left), not the baked light. The paintings cast no shadows.
- Beyond the end door: a flat olive ground and a flat sky colour.
- Culled faces assume the visitor never leaves the walk or the walk-up path. They can't today; a free
  camera would show holes.
- Not tested: the phone, Safari/iOS, and the KTX2 fallback on devices without ASTC/BC7/ETC2.
- No loading progress for the 7.2 MB GLB over Wi-Fi.
- favicon 404.
- The KTX2Loader is never disposed.

**Geometry and look** (carried over from stage 2)
- Places 3–6 hang on flat walls; the recesses for bays 2–3 and the second arm come next.
- The crossing's back arch is 0.6 m low.
- Raphael's light uses non-physical conventions, now baked in. Changing a convention means re-baking.
- The red placeholders still appear in the Blender renders (`blender-*`); the web hangs the real paintings.

**Pipeline**
- Bake time: about 7 min rough on this Mac, shared with the Bosch agent.
- Atlas packing is a custom shelf packer: Blender's multi-object packing collapsed or overlapped islands.
  Packing fills 45–65 % of each atlas.
- `BAKE_GROUPS` is a fixed split along the hall. New geometry (the recesses) lands in a group automatically
  by its position.

## Time

About 1 h 15 min (09:44–10:58).

## Decision needed for the final bake

- **Final as configured** (40 px/m, 512–1024 samples): 2–4 h of baking; about 20 MB download and 36 MB GPU.
- **Lightmap plus tiled detail textures**, for walls that stay sharp on the phone: about 3 h of pipeline
  work.

## Review (main session, 2026-11-20)

Checked `web-sheet.jpg` and `web-start-side-by-side.jpg`. The five commits are on `hall-look`, and the
server answers on 5202 with a 7,174,344-byte `hall.glb`. The walk reads as the hall: bay 1's recess holds the
Mucha and the Klimt below the niches, with the labels as specified.

Not called out in the report:
- The stone reads pinker than the fresco's buff, in the web more than in Blender's renders. On the broad
  nave walls G − B is 17–19 against the fresco's 27–30 (table above), and the nave floor reads salmon.
- The two blocks beside the front steps and the Bosch's base render as flat grey boxes, not stone.
- Every opening shows the same flat lavender sky (175, 175, 245); the fresco's sky is blue with clouds.

Sharpness: at the walk-up distance a phone screen shows a few hundred pixels per metre of wall, roughly
ten times the final bake's 40 px/m (57 px/m at web scale). The unique-texture bake will stay soft there
whatever the sample count. The lightmap × tiled detail route is the one that can stay sharp, so that is the
recommendation to Maria.
