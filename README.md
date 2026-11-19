# athens-gallery (prototype)

A web gallery of up to 10 paintings inside the architecture of Raphael's *School of
Athens*, rebuilt in 3D. The visitor walks toward the vanishing point and enters each
painting. Architecture only: no figures, no statues.

## Gates

| Gate | Before | What you see | Status |
|---|---|---|---|
| 1 | 3–4 h of modelling | Camera solve and depth choice: `renders/checkpoint-a/checkpoint-a.jpg`, `reference/camera.json` | approved: ~5 m depth |
| 2 | 4–6 h of web work | Grey model: `renders/grey/gate-2-sheet.jpg` (overlay, lit views, phone view, plan) | approved, at 70 % size |
| Hall stage 1 | 4–6 h on the rest of the hall | The nave arm finished in Blender (coffers, mouldings, materials, Cycles light) beside the fresco: `renders/hall-stage1/REPORT.md` | waiting for review (branch `hall-look`) |
| Final | — | The prototype on the Galaxy A55 | landscape tested on the A55 (60 fps, pinch walk, tap, Back); portrait pending |

## Web prototype (`web/`)

Run: `cd web && npm install && npm run dev` (Vite on 127.0.0.1:5199). The painting tiles in
`web/public/paintings/` aren't committed: download the originals listed in
`reference/paintings/collection.md` and run `tools/prepare_collection.py` first. `?fresco` (dev only)
frames the canvas at the fresco's proportions to check the opening view.

- The hall is exported from Blender at 70 % (`blender ... -- renders/grey export` writes
  `web/public/models/hall.glb` and `web/src/data/hall.json`).
- The camera is a shift-lens camera: horizontal axis, horizon one third up, as in the
  fresco. In the browser the opening view lands on Raphael's lines (checked with an overlay,
  `renders/web/opening-edges.jpg`).
- The page doesn't scroll. Walking only goes along the corridor, facing forward, from
  Raphael's eye (1.3 m) up to standing height: spread two fingers to walk forward (doubling
  the spread = 7 m), pinch to walk back; on a Mac, trackpad pinch the same way, or the mouse
  wheel (~2 m per notch); arrow keys too. One finger only taps. No pull-to-refresh, no
  browser zoom (`src/input.ts`). The camera turns only when the visitor taps a painting
  (painting, frame and label share one generous target).
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
  resizes and tiles them (`tools/dzi.py`, same layout as `vips dzsave`); 123 MB of tiles.
- Tapping picks on screen (`src/pick.ts`): each piece's outline with its label, grown to at
  least 48 px, smallest match wins. 3D hit boxes failed: on the side walls a nearer piece
  hid the targets behind it.

## What is not real yet

- **Phone view, flagged for later (2026-11-19):**
  - Walking with a spread keeps the camera facing down the corridor, so a side-wall painting
    slides off the screen as you approach: in portrait (about 50° wide) it leaves the frame
    within about 9 m. You can't get next to a painting and see it without tapping it.
  - People spread their fingers *over* the painting they want, expecting to approach it
    (like maps). Proposed fix: a spread that starts over a painting drives that painting's
    walk-up (and carries on into the zoom); over the corridor it walks. Not built yet.
  - Tap picking (`src/pick.ts`) and the portrait walk-up / bottom-sheet panel haven't been
    tested on the phone.

- **Web:** no facts yet (Maria writes them); the panel shows museum data only.
  The hall's light is real-time (sun shadows drawn once, hemisphere and environment light),
  not baked. No reduced-motion walk yet (transitions just get very short). Not tested on an
  iPhone. The JavaScript is 451 KB gzipped and the model 856 KB uncompressed (neither split
  nor compressed yet).

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
- **The nave walls are simplified.** The fresco shows niches, statues and deep recesses
  along them; the model has flat walls with two pilasters per side to hang paintings. In
  the overlay its pilasters don't fall exactly on the fresco's.
- **Detail only in the nave arm, and only in Blender** (hall stage 1, `blender/scripts/finish.py`):
  coffered vault, entablature, pilaster bases and capitals, string course, archivolt, materials
  and floor, with the sun where Raphael's light comes from. Its limits are listed in
  `renders/hall-stage1/REPORT.md`. The crossing, dome, second arm, end wall and facade are
  still grey; the web model hasn't been re-exported or baked.
- **Lighting in the web prototype is a placeholder:** one sun from the front left plus a
  uniform sky. (Raphael's light comes from the front right; the stage 1 renders use that.)
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
- `blender/scripts/finish.py` — the finished nave arm (stage 1); its numbers live in `params.py`.
- `tools/` — measurement, overlay and plan scripts (`.venv` holds OpenCV, NumPy, Pillow).
- `renders/` — gate images and measurement crops.
