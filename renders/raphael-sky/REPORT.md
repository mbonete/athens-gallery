# Raphael's sky

Report by the sky agent, saved by the main session.
- Branch raphael-sky: 8eb507f, 6dbb4a3.
- Merged into hall-look as e211836.
- Images: renders/raphael-sky/ (all made on the round-7 buff hall, before white marble).

## Measured on the 20111 px scan
Sky directions from Raphael's eye:
- far door 3.6–9.7° up;
- over the crossing arch 13.0–16.1° up;
- drum windows 22.9–25.6° up.

They lie on one gradient, from a near-white lavender haze at the horizon (241, 227, 246) to deep blue from 25° up (81, 85, 166).

The clouds are:
- flat-bottomed banks at the door (6.5–8.7°);
- a crisp cumulus and a flat cloud over the crossing;
- soft cumulus tops in the drum, cut square by the windows.

The brushwork is horizontal, at 3.5–8 levels of contrast.

## Built
- **Sky.tsx:**
  - an unlit inverted sphere centred on the camera, drawn first with no depth, on its own layer so the dome picking never sees it;
  - it dims toward #2a2826 like the old background;
  - ±½ level of dither.
- **web/public/sky/sky.jpg:** 2048 px, 601 KB, a stereographic projection from the zenith, so there is no pole and no seam.
  - It holds the fresco's own sky at the directions it has from Raphael's eye.
  - His clouds repeat round the horizon, and nothing sits above 26°.
- **The drum's square-cut clouds** show only near the start and fade out between z −2.5 and −7.
- **sky/make_sky.sh** rebuilds the texture from the scan.
- **Scene.tsx:** +2/−7 lines.
- **Checks:**
  - 9/9 paintings and the dimming;
  - the dome tap;
  - tsc and the build;
  - 60 fps (sky on or off within 0.1 ms);
  - A55 not measured.

## Landscape past the far door: not built, Maria picks
The Bosch on its base fills the door down to the horizon, because the base top (1.32 m) is at eye height (1.295 m). Any landscape shows only in slits of 7–14 cm beside it. Options:
- **A:** pale distant hills in the fresco's sky colours.
- **B:** an open plain fading into the haze.
- **C:** haze down to the threshold.

## Review (main session)
- **Sky:** a strong match. Side by side with the fresco at the same framing (start-fresco-before-after.jpg), the three openings read as Raphael's sky.
- **Watch:** near the far door the sky is large on screen, and the quilted brushwork reads as a paper grain. Ask Maria whether that is welcome as "painted" or should be softer.
- **Landscape:** barely visible with the Bosch in the door. C (haze) invents nothing, and B/A only matter if the doorway piece changes.
