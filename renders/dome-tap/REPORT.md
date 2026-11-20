# Dome tap and ghost glide

## Summary

Branch `dome-tap` in `~/code/athens-gallery-dome`, 5 commits on top of 06233e4 (hall stage 4). Not pushed or
merged.

Tapping the dome walks the visitor to the crossing and tilts the camera to look straight up. Back, Escape and
the browser's back tilt down again, and the walk carries on from the crossing. Maria's ghost walk is a separate
commit (33952ae).

The work went over its time budget, mostly on the test harness. The other worktree's Blender bake shared the
GPU, and one test call hung (see Tests).

## How to run it

- `cd ~/code/athens-gallery-dome/web`. Dependencies are installed (`npm ci`). `public/paintings` is a symlink to
  `~/code/athens-gallery/web/public/paintings` and is git-ignored.
- `npx vite --host 0.0.0.0 --port 5203 --strictPort`. LAN: http://10.1.1.4:5203/.
- `tsc -b` and `npm run build` pass.
- The test scripts were written to the session scratchpad (`pw/`), not to the repo, and may have been cleared:
  - `cdp.mjs`: a raw-CDP driver; Playwright is used only to launch Chrome;
  - suites: `s1`–`s3` (desktop flow), `d2.mjs [desktop|phone]` (paintings and positions), `d3` (phone flow
    and reduced motion), `d4` (ghost strip);
  - images: `plot.mjs` and `compose.mjs`.
- The dev-only hook `window.__dome` gives `domeAt`, `mask(step)`, `lookUp`, `lookDown` and `tl`.

## What changed, file by file

- **`web/src/data/dome.ts`** (new): the dome's numbers in web metres, each with a comment giving its source.
  - Centre z and half-width come from `hall.json` (`dome.z`, `dome.wallX`).
  - Heights come from `blender/scripts/params.py` (crossing A) and `build.py`, ×0.7: springing 8.61, drum
    base 12.74, windows 14.449–16.673, dome springing 16.821, crown/oculus rim 20.903, outer radius 4.55,
    oculus 0.63.
  - Checked against `hall.glb`: the dome shell's top is at 21.30 m, and the drum spans 12.76–16.82 m.
- **`web/src/dome.ts`** (new): picking, the look up and down, Escape, the `#dome` history entry, the dev hook.
- **`web/src/DomeControls.tsx`** (new):
  - `<DomePicking/>` sits inside the canvas and hands the renderer and scene to the picking;
  - `<DomeBack/>` is the Back button.
- **`web/src/walk.ts`**:
  - `Pose.pitch?`, and `progressAt(z)` (the walk's progress at a depth);
  - ghost commit: `eyeAt(z)`, `linkZ()`, `RISE_END_Z`. `floorAt`, `smooth` and `STAIR_Z0` are removed.
- **`web/src/store.ts`**: `Mode` gains `looking-up | dome | looking-down`.
- **`web/src/Scene.tsx`**: three lines. The rotation uses `pose.pitch ?? 0`, plus an import and
  `<DomePicking />`.
- **`web/src/App.tsx`**: an import and `<DomeBack />`.
- **`web/src/pick.ts`**:
  - a tap that hits no painting goes on to `tapDome()`;
  - hover: `hoverDome()` runs after `pickAt`.
- **`web/src/styles.css`**: `.dome-back` rules appended at the end.
- **`renders/dome-tap/`**: 11 images, listed under Screenshots.
- No changes to `hall.json`, `blender/` or `tools/`.

## The default behaviour, and the alternatives

**Tap target**
- What counts: the drum, its windows (including the sky seen through them), the dome, the oculus, and the
  pendentives with their tondi under the drum.
  - The pendentives are included because from the start view they read as part of the dome.
  - To drop them, change the `square` test's lower bound in the shader from `uSpring` to `uDrum`.
- A tap or hover counts within 16 CSS px of the visible dome. Paintings are tested first and always win.
- The pointer cursor shows over the dome, as over paintings.
- How it's picked: a 32×32 px patch around the pointer is drawn again with one marker material, using the real
  hall geometry and depth.
  - So the vault and arches hide the dome in the pick exactly as they do on screen.
  - Two invisible plugs on their own layer, behind the windows and above the oculus, make the sky seen through
    them count as dome.
  - The read-back is asynchronous: 6–33 ms measured, and the page never waits on the GPU.
  - It needs no new dependency.
- Rejected alternatives for picking:
  - screen-space outlines (as for the paintings) or an invisible proxy without occlusion: both would make the
    coffered nave vault in front of the dome tappable;
  - raycasting the GLB: 3–8 ms per ray on the M3 (measured), too slow for hover and for testing several points
    around a tap;
  - three-mesh-bvh: a new dependency plus a build cost at load;
  - testing visibility against the arch openings analytically: it would break with the new front arch.

**The move**
- Walk: from where the visitor is to the centre under the dome, along the walk path. 1.3 s, `power2.inOut`,
  the same as the painting walk-up.
- Tilt: pitch 0→90°, `power1.inOut` over 1.45 s starting at 0.15 s, so it ends at 1.6 s. The fastest turn
  is about 113°/s.
- `ShiftCamera`'s shift is blended out with the tilt. Looking up, `tanUp = tanDown` and `shiftX = 0`.
- The hall light is not dimmed. A `#dome` history entry is pushed, so the Android back gesture works.
- Tilts tried and rejected:
  - aiming the gaze at the oculus: the camera stayed nearly level for 0.5 s, then swept about 45° in 0.25 s
    near the crossing;
  - `power2` for the tilt: GSAP's power2 is cubic, so the peak is about 200°/s, a whip rather than a smooth
    tilt.

**Return**
- A Back pill, "← Back to the walk", at the top left.
  - Same `.close` style as the detail view's Back, on a paper background.
  - It has to be its own element, because the detail view's Back lives inside the painting panel.
- Escape and the browser's back do the same.
- It tilts down in place in 1.2 s (`power2.inOut`, the painting leave's duration). The walk then resumes at the
  crossing's progress (0.863).
- Back pressed during the look-up tilts down wherever the visitor is, and the walk resumes from there.

**Scroll, wheel, pinch and keys while looking up (and during both tilts): ignored.**
- `input.ts` already ignores input outside walk mode, so it needed no changes. Taps elsewhere do nothing
  either.
- Rejected: "a walk gesture returns to the walk".
  - On the phone, a spread over the dome reads as "zoom in".
  - Trackpad inertia after a flick would throw the visitor straight back out.

**Reduced motion:** both moves are cut to 0.01 s, the same `dur()` rule as `transition.ts`.

**Reload on `#dome`:** the hash is stripped and the start view loads.

## Ghost glide (Maria's extra, commit 33952ae)

- The eye height is `eyeAt(z)`: one straight line from Raphael's eye at z 0 (1.295 m, where the walk leaves the
  hold) to `PLATFORM + standingEye` (2.1698 m), then level.
  - It's a constant 0.1039 m of rise per metre walked.
  - It reaches standing height at the first link point to a wall painting, z −8.42 (bay 1, from
    `progressNear`), clamped so it never ends before the top of the stair.
  - Everything comes from `hall.json` (`eye`, `standingEye`, `floor`) and the stations. No new heights.
- The start view at progress 0, the hold and forward-only walking are unchanged.
- One function sets every walk height: the walk, Back from a painting, the dome walk and the dome's Back all go
  through `poseAt`.
  - The painting walk-up's end pose is still set by framing the painting. It eases from the walk pose to that
    pose.
- Clearance: the eye is never below 1.295 m above the floor (at z 0, as before).
  - Above each step's nosing it is 1.604, 1.513, 1.448 and 1.374 m. Before the change those were 1.41, 1.374,
    1.58 and 1.60 m.
  - It never comes near a tread or a step edge.
- Plot: `eye-height.png` (before dashed, after solid, treads filled).
- Scripted walk (`ghost-strip.jpg`, one frame per metre): the floor and stair slide under at an even rate with
  no lift at the risers, and the vanishing point stays put.
  - Over the stair the eye now rises 15 cm in 1.45 m; the old curve rose 57 cm there.
  - Walking over the stair runs at p95 16.8 ms.
  - Judged from frames only. Whether it's "less dizzy" is for Maria on the A55.
  - Forward motion still glides in z (the existing wheel/pinch smoothing). Only the height is linear now.

## Screenshots

- `1-start-hover.jpg`: the start view, with the tappable region outlined in red and the hover point marked.
  Headless screenshots have no cursor; the test checked the cursor style is `pointer` there, and empty on the
  vault and the far door.
- `2-mid-tilt.jpg`: 0.75 s into the move, z −19.6, pitch 31°.
- `tilt-sequence.jpg`: frames every 0.25 s.
- `3-looking-up.jpg`, `4-after-back.jpg`.
- `phone-1-start-region.jpg`, `phone-3-looking-up.jpg`, `phone-4-after-back.jpg`.
- `dome-head-on-crop.jpg`, `eye-height.png`, `ghost-strip.jpg`.

## Tests and fps

Headless Chrome 157 (ANGLE Metal, Apple M3) at 1440×900, and at 891×412 CSS with DPR 2 and touch.

**Looking up: exactly straight up and centred.**
- Camera direction (0, 1, 0), `tanUp = tanDown` (0.5628 on desktop, 0.4163 on the phone), `shiftX` 0.
- The oculus lands on the screen centre: (720, 450) on desktop, (445.5, 206) on the phone.
- The drum's base ring has the same radius in x and y, so the dome is round: 312.4 px on desktop, 193.3 px on
  the phone (fits the 412 px height).

**Where the dome can be tapped**

| Viewpoint | Desktop | Phone |
|---|---|---|
| Start view | region x 612–860, y 216–376 | region x 382–518, y 42–150 (CSS px) |
| Mid-nave (z −14) | tap → looking up | tap → looking up |
| Bay 3 (z −18) | tap → looking up | tap → looking up |
| Crossing front, under the crossing | dome not on screen, nothing to tap | dome not on screen, nothing to tap |
| Last point the dome is on screen | z −22.5 | z −18.7 |

The walk camera faces forward and level, so from the crossing itself there is no dome to tap.

**Paintings:** all 9 still open on tap or click, on desktop and phone. None of those tap points is within the
dome's reach.

**Input while looking up:** wheel, ctrl+wheel (trackpad pinch), ArrowUp, PageDown, a two-finger spread and
pinch, and a tap all leave the camera and the walk target unchanged.

**Return:**
- The Back button, Escape and the browser's back all return to the walk at progress 0.8631 with the hash
  cleared.
- Back during the look-up works. A double tap pushes one history entry.
- After Back, a wheel notch walks on (z −28.07 → −30.06), and a spread on the phone walks on as well.

**Timing:**
- A tap starts moving 61–83 ms later (including the test's 40 ms polling).
- Reduced motion: looking up within 52 ms, back within 42 ms.

**Frame times** (p95; all at Chrome's 60 Hz cap, so they show no dropped frames on an M3 and say nothing
about the A55):
- desktop: walk + tilt up 16.7 ms (101 frames, max 16.8); tilt down 16.8 ms;
- phone viewport: tilt up 16.7 ms, tilt down 16.7 ms;
- the hover pick costs about 1 ms of CPU per mouse move.

**Test environment:**
- The other worktree's rough bake (Blender `bake.py`, started about 19:41) shared the GPU and CPU. Some runs
  stalled for minutes on GPU read-backs and screenshots. The final runs went through between its GPU bursts.
- Separately, one test call hung: it asked Chrome to return the GSAP timeline by value. Fixed in the tests; not
  an app bug.

## Limits

- **How the dome looks when it fills the screen** (`dome-head-on-crop.jpg`). Nobody had seen it head-on
  before; it is the weakest view in the hall.
  - The "coffers" read as a flat grid of ribs over a mottled field, not as sunk panels: the ribs are 14 cm
    deep seen from 18 m below.
  - Every ring boundary has thin black slits, uneven in width, where the rib bands meet the shell: the rough
    bake (16 px/m) or unlit texels.
  - The innermost ring crowds 28 ribs into a sunburst of wedges with black slits between them.
  - The planar detail mapping stretches the mottled tile radially in the outer rings, where the shell is
    steep, and keeps it round near the top. At this resolution the scale change is more visible than the
    pattern seams.
  - The light is flat, with no fall-off from the windows. The dome is browner and darker than the drum and
    the pendentives.
  - The oculus is a hard-edged disc of flat sky colour.
  - The drum's windows, the piers and the empty tondi read well.
  - Left alone, as asked.
- The dome can't be tapped from the crossing itself, because it isn't on screen there.
- The heights in `data/dome.ts` come from params. If the re-bake changes the crossing or the drum, update
  them. Centre and half-width follow `hall.json` automatically.
- The pick draws front faces only, like the hall's materials. Double-sided geometry in the new front arch would
  occlude in the pick exactly as it does on screen; nothing else changes.
- The hover pick isn't throttled: one small extra render per mouse move.
- No keyboard way to look up (paintings have none either), and the Back button doesn't take focus.
- Already in the code, not fixed: on startup, `Scene.tsx`'s `useFrame` reads `scene.background` before its
  `useEffect` sets it. It threw "Cannot read properties of null (reading 'copy')" on the first frames in 3 of 4
  plain page loads. Harmless; a one-line guard fixes it.
- Not tested on a real phone (as instructed), on an iPhone, or in Safari.
- The red outline in the hover image can be off by up to 4 px (grid rounding). The ghost strip still shows the
  "walk in" hint because that test moves the camera directly.

## Likely merge conflicts with `hall-look`

These are predictions: `hall-look` had no commits past 06233e4 and no uncommitted `web/src` changes when this
branch started.
- **`walk.ts`**: the most likely conflict. `withHeight` and `floorAt` are replaced and `progressNear`'s body is
  changed. Any edit of theirs to those lines conflicts, and any new call to `floorAt` will fail to compile.
- **`hall.json`**: untouched here. A re-export flows through automatically: `eye`, `standingEye`, `floor`,
  `dome.z`, `dome.wallX` and `places` are what this code reads.
- **`Scene.tsx`**: three single-line edits (the import, the rotation line in `useFrame`, `<DomePicking />`
  after `<Hall />`). They conflict only if those lines change.
- **`styles.css`**: appended at the end. If they append too, keep both.
- **`App.tsx`, `pick.ts`, `store.ts`**: small edits that a bake change is unlikely to touch.
- **Not textual:** if the re-bake changes the crossing or drum, `data/dome.ts` goes stale. After the merge,
  check the tappable region with `window.__dome.mask(8)` or `s1.mjs`.

## Review (main session, 2026-11-20)

Checked `3-looking-up.jpg` and `eye-height.png`. The 5 commits are on `dome-tap`, and the server answers on
5203.

- **Looking up:** the view is centred and round. The drum's windows and the pendentive tondi read well. The
  dome's interior matches the report's description: flat coffers, black slits at the ring joins, a crowded
  sunburst around a flat lavender oculus.
- **Destination:** now that the dome is somewhere the visitor goes, its interior needs design work before the
  final bake. That goes to Maria as a decision.
- **Ghost line:** the plot shows the eye rising at a constant rate from 1.295 m to 2.17 m by z −8.42, well
  clear of every tread. The old curve rose 57 cm in a burst over the stair.
- **Merge into hall-look:** after hall stage 5 lands. Then check the tappable region, update `data/dome.ts` if
  the crossing changed, and add the `scene.background` guard.
