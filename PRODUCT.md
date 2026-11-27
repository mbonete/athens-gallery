# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Two audiences, served equally (Maria, 2026-11-21):

- People who enjoy paintings: they walk into the hall, look, open a painting and look closely.
- Visitors from Maria Bonete's portfolio, where Studiolo sits among her creative projects: recruiters and peers who judge her craft by the same experience, often within a minute or two.

Both arrive on phones (a mid-range Android such as the Galaxy A55 is the test device) and on desktops.

## Product Purpose

*Studiolo*: nine favourite paintings, chosen by Maria Bonete, hung in the architecture of Raphael's *School of Athens*, rebuilt in 3D. The visitor starts at Raphael's viewpoint, walks toward the vanishing point, walks up to a painting and zooms into a high-resolution scan of it. It is Maria's personal favourite collection. Success: a visitor walks in, opens paintings and looks closely.

## Positioning

The hall is the fresco's own architecture: the camera is solved from the fresco, the eye stays at Raphael's height, and the walk keeps his horizon. Architecture only: no philosophers, no statues. Every painting hangs at its true size and opens into a deep-zoom scan from its museum.

## Operating Context

- Walk: scroll or trackpad pinch, two-finger spread on touch, arrow and Page keys.
- A painting: click or tap walks up to it (on touch, so does a two-finger spread over it once the view is turned to face it); the wall label unfolds into an information panel; click to zoom, drag to pan, pinch and double-tap on touch.
- The dome: a tap walks under it and looks up (on touch, so does a two-finger spread over it once the view is turned up to it); another tap, or pinching the fingers together, comes back.
- Links open a painting directly (`#painting/<slug>`). Back, Escape and the browser's back button return to the walk.

## Capabilities and Constraints

- 60 fps on the Galaxy A55 is the bar; lighting is baked, the page is unlit.
- First load is heavy: the hall (~4.7 MB) and nine painting textures (~10 MB, to be reduced before publishing).
- Images are public-domain or open-access scans with their credit and record link.
- Facts per painting (the detail dots) are not written yet; Maria writes them. Nothing may be invented in their place.
- Not yet decided: where it is deployed.

## Brand Commitments

- Name: *Studiolo*. Line: "Nine favourite paintings, chosen by Maria Bonete, hung in the architecture of Raphael's *School of Athens*."
- Her name is written without an accent, so anyone can read it.
- Voice: a museum label, third person, plain and factual.
- The hall is clean and new, not aged: Maria rejected grime, dirt and an aged look on the architecture.
- She rejects interface that reads as generic or AI-generated.

## Evidence on Hand

- The nine works with titles, dates, media, sizes, collections and credits: `web/src/paintings.ts`; sources in `reference/paintings/collection.md`.
- The fresco scan used for the camera solve and colours (Wikimedia Commons, public domain).
- No facts per painting yet, no visitor testimonials, no press.

## Product Principles

- The paintings and the hall lead; the interface steps aside.
- Nothing is invented: every fact traces to a museum record or to the fresco.
- A mid-range phone gets the same visit as a desktop.
- The entrance is Raphael's view.

## Accessibility & Inclusion

Keyboard access for every painting and the dome, a dialog panel announced by its title, reduced motion turns movement into cuts, and the canvas carries a text label.
