# Keyboard access, lighter first load, reduced motion

Report by the keyboard agent, saved by the main session.
- Branch keyboard-loading: 69faeee, 0bc9339, 2b0b5f7, 9cb170a.
- Merged into hall-look as b0019a9.

## Load
- **Main bundle:** 1,722 kB → 1,383 kB raw, and 482.7 → 399.7 kB gzip.
- **OpenSeadragon:** now its own chunk (348 kB, 87 kB gzip), fetched on idle once the hall is ready. The first walk-up finds it loaded, and the swap stays invisible (mean pixel difference 1.3–2.5 of 255).
- **Back fix:** Back from an unzoomed painting used to wait 1.1 s for an event that never fired. It now starts at once: 1.34 s back on the walk, was 2.48 s.
- **Still loaded up front (not fixed, 16.3 MB in all):**
  - the nine painting JPEGs, about 10.4 MB (the Bosch alone is 3.1 MB);
  - hall.glb;
  - the basis transcoder.

## Keyboard and screen readers
- **Keys.tsx:** one visually hidden button per painting, in walk order and named "Title, Artist", plus "Look up into the dome".
- **Focus:** focusing a painting walks it into view. The focus ring is drawn around the painting itself.
- **Opening and closing:** Enter or Space opens; Escape goes back; focus returns to the painting's button.
- **Walking:** arrows walk 2 m; PageUp/PageDown and Space/Shift+Space walk 8 m; Home and End go to the ends.
- **Screen readers:** the canvas is role="img" with a label; the panel is a dialog named by its title.
- **No new visible copy.**

## Reduced motion
These are now cuts:
- the walk-up: 0.36 s, including tile loading;
- Back: 0.10 s;
- the dome walk and tilt: 0.05 s;
- the tilt down: 0.03 s;
- the focus walk.

Walking the visitor drives still glides.

## Tests
- **On the branch, 5203:**
  - desktop 17/17;
  - touch, portrait and landscape, 5/5 each;
  - reduced motion 5/5;
  - load order 2/2.
- **Rerun by the main session on merged hall-look (5202):**
  - after the merge: desktop 17/17, touch-portrait 5/5, reduced 5/5;
  - after the sky merge too: desktop 17/17.
- Scripts are in the session scratchpad (pw5203/, with a 5202 copy in pw5202m/).

## Open (agent)
- **Screen-reader wording to confirm:** "The architecture of Raphael's School of Athens in 3D, with 9 paintings", "Look up into the dome".
- **Optional visible hint:** "Pinch, scroll or use the arrow keys to walk in". Not shipped; Maria chose to keep labels unchanged.
- **Not tested:** real screen readers; Safari and Firefox.
- **Deep links:** #painting/... doesn't move focus on load.
- **Small mismatch:** screenRect() ignores shiftX (about 5 px).

## Review (main session)
The diff is clean and contained. Input changes leave pinch and wheel untouched (verified 7.00 m per spread doubling). The largest remaining first-load cost is the painting textures, about 10 MB. That belongs to the ship round: KTX2 or smaller JPEGs, with care, since the walk-up's last frame shows that texture before the zoom viewer takes over.
