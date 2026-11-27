# athens-gallery (prototype)

A web gallery of up to 10 paintings inside the architecture of Raphael's *School of
Athens*, rebuilt in 3D. The visitor walks toward the vanishing point and enters each
painting. Architecture only: no figures, no statues.

Visitors see it as **Studiolo**: "Nine favourite paintings, chosen by Maria Bonete, hung in
the architecture of Raphael's *School of Athens*." The title stands over the start view with
how to visit (`web/src/Intro.tsx`) and steps aside with the first step.

## Gates

| Gate | Before | What you see | Status |
|---|---|---|---|
| 1 | 3–4 h of modelling | Camera solve and depth choice: `renders/checkpoint-a/checkpoint-a.jpg`, `reference/camera.json` | approved: ~5 m depth |
| 2 | 4–6 h of web work | Grey model: `renders/grey/gate-2-sheet.jpg` (overlay, lit views, phone view, plan) | approved, at 70 % size |
| Hall stage 1 | 4–6 h on the rest of the hall | The nave arm finished in Blender (coffers, mouldings, materials, Cycles light) beside the fresco: `renders/hall-stage1/REPORT.md` | approved with changes |
| Hall stage 2 | The bake for the web | The whole hall finished in Blender beside the fresco, eye-level views, bay 1's hanging options, crossing options: `renders/hall-stage2/` | approved: crossing A, shade halved, paintings below the niches |
| Hall stage 3 | The recesses in bays 2-3 and the second arm | The baked hall walkable in the web (port 5202 on the worktree): `renders/hall-stage3/` | waiting for review on the Mac and the A55 |
| Final | — | The prototype on the Galaxy A55 | landscape tested on the A55 (60 fps, pinch walk, tap, Back); portrait pending |

## Web prototype (`web/`)

Run: `cd web && npm install && npm run dev` (Vite on 127.0.0.1:5199). The painting tiles in
`web/public/paintings/` aren't committed: download the originals listed in
`reference/paintings/collection.md` and run `tools/prepare_collection.py` first. `?fresco` (dev only)
frames the canvas at the fresco's proportions to check the opening view.

- The hall is the finished Blender model, baked (hall stage 3): `tools/bake_hall.sh [rough|final]`
  rebuilds it, bakes Cycles' light into lightmap atlases (`blender/scripts/bake.py`), fills and
  denoises them, and packs `web/public/models/hall.glb` (KTX2 textures, meshopt geometry, 70 %)
  plus `web/src/data/hall.json`. Needs `basisu` (Homebrew `basis_universal`) and `web/node_modules`.
  The web draws it unlit; `web/public/basis/` holds the KTX2 transcoder.
- The camera is a shift-lens camera: horizontal axis, horizon one third up, as in the
  fresco. In the browser the opening view lands on Raphael's lines (checked with an overlay,
  `renders/web/opening-edges.jpg`).
- The page doesn't scroll. Walking only goes along the corridor, facing forward, from
  Raphael's eye (1.3 m) up to standing height: spread two fingers to walk forward (doubling
  the spread = 7 m), pinch to walk back; on a Mac, trackpad pinch the same way, or the mouse
  wheel (~2 m per notch); arrow keys too. On touch, one-finger drag looks around and a short
  contact remains a tap; adding a second finger hands the gesture to the walk. With the view turned
  at least 10° to face a painting (or an entrance banner, or the dome, which it looks up into), a
  spread that begins over it opens it as a tap does, and a pinch there still walks back (`ASIDE`, `OPEN_SPREAD`). Looking up into the dome or at a
  banner, pinching the fingers together comes back to the walk, as a tap does. No pull-to-refresh
  or browser zoom (`src/input.ts`, `src/look.ts`). A painting, frame and label share one generous
  tap target.
- Tapping the painting or its label walks up until it fills the screen next to the panel;
  the hall dims; OpenSeadragon takes over on the same pixels (checked by toggling it: same
  edges and colours, only sharper). The label becomes the panel. Back (button, Esc or
  browser back) zooms out, swaps back and returns to the spot the visitor tapped from.
- Maria's nine works hang at 120 % of their real size (`DISPLAY_SCALE` in `src/paintings.ts`;
  labels and panels keep the real dimensions). Each label sits beside its piece when it fits
  in the bay, otherwise under it (Klimt, Hylas). Bay edges come from the Blender
  export (`hall.json`).
- Data and image sources for each work: `reference/paintings/collection.md`. Placement: six in the nave's bays, Titian (left) and Kandinsky (right) on the
  crossing's side walls, the Bosch standing open in the far doorway; the walk stops 5.5 m before it. `tools/prepare_collection.py` crops,
  resizes and tiles them (`tools/dzi.py`, same layout as `vips dzsave`); 123 MB of tiles. It also
  writes <=1024 px hall textures for touch-first devices; pass `--mobile-only` to rebuild just those
  nine files without regenerating the deep-zoom tiles.
- Tapping picks on screen (`src/pick.ts`): each piece's outline with its label, grown to at
  least 48 px, smallest match wins. 3D hit boxes failed: on the side walls a nearer piece
  hid the targets behind it.
- Keyboard and screen readers (`src/Keys.tsx`): each painting, in walk order, and the dome
  (before the two paintings under it) has a visually hidden button; a painting's is named
  after its title and artist. Focusing one walks to the point nearest it where it's whole on
  screen (a painting with its label), and the focus ring is drawn around it there. Enter or Space opens
  it as a tap does; focus moves to Back in the panel (a dialog named by the title, so a
  screen reader announces it) and returns to the button on the way out. Escape leaves a
  painting or the dome. Up/Down arrows, PageUp/PageDown, Space/Shift+Space and Home/End
  walk. A tap or click on the canvas doesn't move focus. The canvas is an image with a label.
- The 3D gallery is a separate chunk from its phone entry screen, so a portrait phone does not
  fetch Three.js, the hall or the paintings. OpenSeadragon is another separate chunk, fetched once
  the hall is ready and the browser is idle (or when a walk-up starts, if that comes first); the
  1.3 s walk-up is longer than the fetch.

## What is not real yet

- **Phone visit:** portrait phones get a lightweight request to rotate. The gallery starts in
  landscape, with a 1.5 DPR cap and the nine smaller hall textures (1.7 MB on the wire and about
  32 MiB decoded, instead of 10.95 MB and about 176 MiB). The full DZI is still used inside a
  painting. Browsers allow fullscreen only on a tap, never on a rotation, so the taps that start
  a visit ask for fullscreen held in landscape (`src/fullscreen.ts`): the rotate screen's button,
  the welcome card's "Enter the gallery", and a "Full screen" pill shown while walking outside
  fullscreen. iPhone browsers have no page fullscreen. Phones turn within the desktop's limits
  (`src/look.ts`): as wide a view, less high, so never more of the building. Past the facade's
  corners, flat ground runs round the building (`hall.json` groundAround). Tested on the A55 (look, fullscreen, the ground); `tools/browser/phone.mjs`
  checks the gate, look, walk, tap, the turned spread that opens a painting, and focus. Still to
  check on an iPhone.

- **Web:** no facts yet (Maria writes them); the panel shows museum data only.
  The hall's light is baked (rough bake so far: see `renders/hall-stage3/`). Under reduced motion the walk-up, Back, the dome and the keyboard's walk to a painting are cuts; the visitor's own walking still glides. Not tested on an
  iPhone.

- **Depth is a choice, not a measurement.** One image fixes the view, not the depth. The
  model assumes the domed crossing is square (Gate 1).
- **Overall size is a choice too: 70 %** (Gate 2). Scaling the whole model doesn't change
  Raphael's view. At 70 % Plato and Aristotle would be life-size, so a visitor meets the
  hall as Raphael's figures do (vault about 7× a standing figure): nave 8.3 m wide, vault
  crown 12.7 m, about 33 m from the steps to the far door. The Blender renders and
  `params.py` stay at the 100 % reading (from the fresco's 7.7 m width); the web export
  applies the factor. Raphael's foreground figures would point to a larger hall.
- **Parts the fresco doesn't show are designed, not reconstructed:** the facade above the
  lunette frame, the dome above the drum, the crossing's side walls (closed), the sides of
  the second arm, the outside of the building. Nothing exists outside the walls; it's only
  visible if the camera turns sideways on the platform.
- **The nave walls are simplified past bay 1.** The fresco shows niches, statues and deep
  recesses along them; bays 2-3 and the second arm have flat walls with pilasters to hang
  paintings. In the overlay their pilasters don't fall exactly on the fresco's.
- **The finished hall exists only in Blender** (hall stages 1-2, `blender/scripts/finish.py`,
  `finish2.py`): coffered vaults, mouldings, bay 1's recesses and niches, facade, floors and steps,
  crossing with tondo frames, drum and dome, end wall, materials, Raphael's light. Its limits are
  listed in `renders/hall-stage1/REPORT.md`, `renders/hall-stage2/REPORT.md` and
  `renders/hall-stage3/REPORT.md`. The crossing is option A (Maria, stage 2 gate).
- **Paintings are 1.8 × 2.4 m red placeholders,** all the same size and hung at the same
  height.
- **The steps don't follow equal risers.** Read off the fresco they come out 27, 19, 18 and
  18 cm, with treads of 54 to 87 cm.
- The fresco width used to convert pixels to metres (7.7 m) is the published size; which
  part of the photo it spans is uncertain by about ±7%.

## Layout

- `reference/download/` — the fresco scan from Wikimedia Commons, public domain
  ("The School of Athens by Raffaello Sanzio da Urbino in Vatican-Chroma denoise
  version.jpg", 20111×13936). Not committed (size).
- `reference/camera.json` — camera solve results.
- `blender/scripts/params.py` — every dimension, with the image reading it came from.
- `blender/scripts/build.py` — builds the model, saves `blender/athens-hall.blend`, renders
  views: `blender -b --factory-startup -P blender/scripts/build.py -- renders/hall-stage1 hall-raphael`.
  Add `grey` for the Gate 2 grey model (`athens-grey.blend`), `physical` for an unlinked sun.
  `SAMPLES=128` sets Cycles samples. The finished parts need the CC0 scans: run
  `tools/fetch_textures.py` once (Poly Haven and ambientCG, into `blender/textures/`, not committed).
- `blender/scripts/finish.py` — materials, the coffered vaults, walls and mouldings, Raphael's light;
  `finish2.py` — bay 1, facade, floors and steps, crossing, end wall (stage 2). Numbers in `params.py`.
  `CROSSING=A` (or `A2`) builds a crossing option; `BAY1_HANG=below|inside` hangs the Mucha and the
  Klimt in bay 1 (`PAINTINGS_DIR` = the `*-texture.jpg` files).
- `tools/` — measurement, overlay and plan scripts (`.venv` holds OpenCV, NumPy, Pillow).
- `renders/` — gate images and measurement crops.
