# Opening a painting: the card unfolds out of the label after the walk-up

Maria: "I dont like the motion of the cards when opening a closeup painting view. they block most of the zoom animation." She picked option D of five.

- **Before:** the wall label grew into a blank paper panel across the screen during 0.9 s of the 1.3 s walk-up. On desktop it crossed the painting; on the phone it rose as a sheet over 36 % of the screen.
- **Now (transition.ts):**
  - **Walk-up:** the 3D label stays on the wall and comes forward with the painting. Nothing covers the walk-up.
  - **Unfold:** at 1.1 s (the camera at ~95 % of its way) the panel unfolds out of the label's spot on screen over 0.4 s. It is a clip on the panel at its resting place, so the text never reflows.
  - **Back:** the panel folds back into the label in 0.25 s, then the walk back starts at 0.2 s.
  - **Before it unfolds:** the panel is transparent and lets clicks through. It still takes focus, so the keyboard opener lands on "Back to the hall" at once.
- **Frames** (10 fps, from video): desk-open.jpg, desk-back.jpg, phone-open.jpg, phone-back.jpg. Video: desktop-open-back.webm.
- **Tests:** desktop 17/17, touch-portrait 5/5, touch-landscape 5/5, reduced motion 5/5 (everything is a cut).
- **Limit:** the label sits at the painting's lower right, and the text at the top of the panel. So the first ~0.1 s of the unfold shows plain paper before the text comes into the clip.
