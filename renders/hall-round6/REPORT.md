# Hall round 6: Maria's flicker, the panel-frame line, the Pantheon dome

Report by the hall agent, saved by the main session. Commits on hall-look:
- 5874fcf R13
- f6ad362 Pantheon dome
- a2efb07 dome lightmap
- 3d02716, 3d50b20 lightmap edges
- e06f19e rough bake
- a39855c renders

The tap to leave the dome came from dome-tap (c353cdc) and was merged as 244e5e5.

## Maria's flicker: z-fighting between stacked faces
Her recording (2026-11-20 21:38) showed black bars flickering on the end wall's left door pier. The cause:
- capital() built the necking as a skin 4 mm (2.8 mm web) in front of the shaft or wall face.
- The covered face behind that skin was baked black.
- Her depth buffer couldn't separate the two faces at that distance.

The fault reproduces in Chrome with camera.near forced to 0.002.

New rule R13: no visible face may sit less than 2 cm (web) in front of a covered face of another piece that faces the same way, coplanar faces included. The audit checks it over all pieces and bake groups. A finding counts as visible when a walk or walk-up eye position has a clear sight line to it.

| | Visible findings | Piece pairs | Unseen |
|---|---|---|---|
| Stage-5 geometry | 690 | 168 | 249 |
| Round 6 | 0 | 0 | 51 |

The rest of the joint audit is unchanged: 0 collisions, 0 open ends, 0 skewed, 70 contacts. Files: audit/joint-audit-stage5-geometry.json, audit/joint-audit-round6.json.

Fixes, in order of preference:
- **(a) Remove the hidden part:**
  - drum pilasters stand on the sill and stop under the cornice;
  - the opening arch's pilasters run from plinth to impost;
  - the drum's underside and the pendentive tops are removed;
  - triglyph grooves are cut slots;
  - bay 1's 2 cm liners are gone.
- **(b) The shaft or wall is the flush band:**
  - capital() runs 3 cm inside the shaft at the necking;
  - mouldings no longer embed a back strip in the wall.
- **(c) A projection of 3 cm or more:**
  - astragal 3 cm, abacus 4 cm;
  - the end door's first fascia;
  - the opening arch: archivolt 5 cm, bands 3 cm;
  - tondo frames;
  - the drum sill and cornice;
  - the drum base ring;
  - recess ceilings.
- **Bug found:** the step nosings were built inside the steps. They now project over the riser below.

Black pixels on the end-wall approach at 512×662 (flicker/black-pixels.json):

| Progress | Before, near 0.002 | Before, normal near | After, near 0.002 | After, normal near |
|---|---|---|---|---|
| 0.80 | 1117 | 624 | 453 | 450 |
| 0.85 | 953 | 270 | 264 | 260 |
| 0.90 | 1018 | 69 | 110 | 107 |

## Panel-frame dark line (stage 5)
It is not a stacked pair. The cause was dark edge texels on a thin face. Fixes:
- island margin no wider than the gap between islands (2/2 rough, 3/3 final);
- thin islands at least 6 texels across;
- dark covered texels take light from lit texels of their own island, up to 8 texels away;
- dark margin texels take their island's lit edge.

Dark pixels in that view went from 533 to 93.

## Pantheon dome
- **Coffers:** 28 × 5 rings of real sunken coffers above a 0.2 m plain band. Each ring is as tall as its coffers are wide, so they shrink and stay square.
- **Steps:** each coffer steps back three times, cut wider on its lower side (0.11 against 0.05 of the coffer per step) so the steps read from below.
- **Oculus:** a plain band runs up to a moulded ring round the oculus: fascia, soffit, and a torus rolling into the opening.
- **One sheet:** the coffered sheet replaces the shell's inner face, so the black slits are gone.
- **Light:** the dome is lit by the drum windows and the oculus. The right-side shade is removed on the dome.
- **Lightmap:** one azimuthal island. Smart project had collapsed the faces to slivers.
- **Web data:** springing, radius and oculus are unchanged, so web/src/data/dome.ts needs no edit.

## Sizes and checks
- **Lightmaps:** 8.53 Mpx (stage 5: 8.16):
  - front 1152×448;
  - facade 832×832;
  - nave 1280×1280;
  - crossing 2304×1984;
  - arm2 1088×1024.
- **GLB:** 8.01 MB.
- **Rough bake:** 17.5 min.
- **5202:**
  - the walk reaches the end door;
  - 9/9 taps;
  - 58.3 fps, p95 frame 17.1 ms, longest frame 150 ms;
  - console shows only the favicon 404.

## Limits (agent)
- **Crossing arch:** at near=0.002 from mid-nave, a 1-px shimmer on the edge of the soffit. The faces meet at an angle, so it is not a stacked pair, and it doesn't appear at normal near.
- **Dome step walls:** they take the light of the faces beside them, because they project to lines in the dome's island.
- **Look changes from R13:**
  - the astragal is fuller;
  - the nosings now show;
  - the opening arch's bands stand out more;
  - the tondo frames are thicker.
- **R13 leftovers:** 51 pairs remain on faces no eye position can see.

## Review (main session)
- **Flicker: fixed.** The left capital's black bar is gone at normal near and at near=0.002 in every crop. Nobody captured her impost bar on our side, before or after. It uses the same capital() profile, so the fix applies, but that rests on the code, not on a capture.
- **New, small:** the 3 cm astragal's top now catches light as a thin bright line where the capital meets the shaft (0.90 crops). It is physically right, but it is worth a look at phone distance.
- **Panel frame:** much better. What is left reads as the moulding's own shadow line.
- **Dome: the geometry is right, but the bake undersells it.** In the workbench render the stepped coffers read deep. In the baked web view looking up (dome-tap-close-before-after.jpg) they read flatter, because the step walls share the light of their neighbours (the agent's limit above). The plain band up to the oculus reads as a flat brown disc. The coffers' depth is the point of the Pantheon model, and the dome-tap view looks straight at it. Before the final bake:
  - give the step walls their own lightmap texels so the steps shade;
  - check that the plain band gets a gradient from the oculus.
- **dome-tap merged** (244e5e5); tsc passes.
