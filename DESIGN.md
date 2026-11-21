---
name: Studiolo
description: Nine favourite paintings hung in the architecture of Raphael's School of Athens; the interface is the exhibition's own wall labels.
colors:
  paper: "#f4f1ea"
  ink: "#2a2724"
  muted: "#6b655d"
  arch-red: "#5d3125"
  sky-clear: "#c9d4e2"
typography:
  display:
    fontFamily: "Cardo, Georgia, 'Times New Roman', serif"
    fontSize: "44px"
    fontWeight: 400
    lineHeight: 1
    letterSpacing: "-0.012em"
  title:
    fontFamily: "Cardo, Georgia, 'Times New Roman', serif"
    fontSize: "27px"
    fontWeight: 400
    lineHeight: 1.2
  body-lead:
    fontFamily: "Cardo, Georgia, 'Times New Roman', serif"
    fontSize: "18px"
    fontWeight: 400
    lineHeight: 1.38
  body:
    fontFamily: "Cardo, Georgia, 'Times New Roman', serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.4
  label:
    fontFamily: "Cardo, Georgia, 'Times New Roman', serif"
    fontSize: "14px"
    fontWeight: 400
  caption:
    fontFamily: "Cardo, Georgia, 'Times New Roman', serif"
    fontSize: "13px"
    fontWeight: 400
rounded:
  plaque: "0px"
  sm: "8px"
  pill: "999px"
  circle: "50%"
spacing:
  edge: "24px"
  edge-compact: "16px"
  list-row: "5px"
  list-column: "16px"
components:
  wall-label:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    typography: "{typography.body-lead}"
    rounded: "{rounded.plaque}"
    padding: "22px 24px 20px"
    width: "412px"
  info-panel:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.plaque}"
    padding: "20px 22px"
  button-back:
    backgroundColor: "transparent"
    textColor: "{colors.muted}"
    typography: "{typography.label}"
    rounded: "{rounded.pill}"
    padding: "6px 12px"
    height: "44px"
  button-back-floating:
    backgroundColor: "rgb(244 241 234 / 0.9)"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    rounded: "{rounded.pill}"
    padding: "6px 16px"
    height: "44px"
  button-zoom:
    backgroundColor: "rgb(244 241 234 / 0.94)"
    textColor: "{colors.ink}"
    rounded: "{rounded.circle}"
    size: "40px"
---

# Design System: Studiolo

## Overview

**Creative North Star: "The Exhibition's Own Labels"**

The hall is the exhibit: Raphael's architecture rebuilt in 3D, cream marble, a gold-leaf opening arch with a view-dependent sheen, floor patterns in a deep madder (#754543, baked into the model) and a photographed sky through the far doors. None of those colours come from CSS; they live in the baked model and the Blender albedos (`blender/scripts/params.py`, `Scene.tsx` gold-leaf shader). The interface does not compete with them. Every piece of UI is a museum wall label: a paper plaque set in ink in one Aldine face, mounted on the wall or unfolding from it.

The same label exists in three forms that share one vocabulary: the label beside each painting (drawn on canvas in the 3D scene), the entrance label for the exhibition itself, and the information panel a painting's label unfolds into. Paper, ink, a muted grey for field names and notes, one hairline, Cardo. Controls are few and quiet: a back pill, two round zoom buttons, invisible keyboard targets that appear only under focus.

Density is low and the voice is a catalogue entry: field names on the left in muted, values on the right in ink. The UI steps aside: the entrance label hides with the first step, takes no pointer events, and sits at the lower left so the centre axis (vanishing point, door, dome windows) stays clear.

**Key Characteristics:**
- Paper plaques, square-cornered, with ink text in Cardo only.
- Catalogue grammar: two-column definition lists (muted term, ink value).
- The arch's dark red appears in the UI only as focus and selection.
- The hall's colours come from the model; the UI adds no decorative colour.
- Drawn line icons at one stroke weight, coloured by their text.

## Colors

A restrained label palette, warm paper and warm near-black, set against a hall whose colour is all in its materials.

### Primary
- **Arch Red** (arch-red): the dark red of the opening arch's outer band, used in the UI only for the keyboard focus ring and, at 22% alpha, text selection. It is a signal, never fill or decoration.

### Neutral
- **Label Paper** (paper): every plaque and panel surface; the canvas wall labels use the same value. Translucent at 0.9-0.94 alpha on floating controls (back pill, zoom buttons) and as the paper halo around focus rings.
- **Label Ink** (ink): all primary text, titles and values; also the tint of every shadow and hairline (`rgb(42 39 36 / a)`).
- **Field Grey** (muted): definition-list terms, the entrance note, the source line, the back control's text, and the bottom lines of the canvas labels.
- **Sky Clear** (sky-clear): the page background and the WebGL clear colour, seen only before the hall loads or past the model's edge.

### Named Rules
**The Red Is a Signal Rule.** Arch Red marks focus and selection. It does not fill buttons, colour headings or decorate plaques.

**The Hall Owns Colour Rule.** Marble cream, gold leaf, the #754543 floor patterns and the sky are materials of the 3D world, tuned in the bake. UI surfaces do not borrow them as accents.

## Typography

**Display Font:** Cardo (with Georgia, "Times New Roman", serif)
**Body Font:** Cardo
**Label Font:** Cardo

**Character:** One face throughout: Cardo, after Griffo's Aldine roman (Venice, 1495), self-hosted via @fontsource (Latin 400, 400 italic). Hierarchy comes from size, italic and the muted colour, never from weight or tracked capitals.

### Hierarchy
- **Display** (400, 44px, line-height 1, -0.012em): the exhibition title on the entrance label. 30px in short landscape, 28px in portrait.
- **Title** (400 italic, 27px, 1.2): a painting's title at the head of the info panel. Titles of works are always italic, as `<cite>` is in running text.
- **Body Lead** (400, 18px, 1.38): the entrance line and the panel's artist-and-date line. 15px in portrait and short landscape.
- **Body** (400, 15px, 1.4): the entrance note and the definition lists. 13px in compact layouts.
- **Label** (400, 14px): the back control and detail-fact buttons.
- **Caption** (400, 13px, muted): licence and record link.

Canvas wall labels (600x400 texture) use the same scale proportionally: title italic 40px, artist 29px, medium/size and the action line 23px in Field Grey.

### Named Rules
**The One Face Rule.** Cardo for every label, panel, title and control. No second family, no bold, no uppercase tracking.

**The Catalogue Rule.** Facts about a work or a visit are set as a two-column list: term in Field Grey, value in Ink, gap 5px by 16px.

## Layout

The canvas is fixed full-viewport; all UI floats over it in fixed position and respects safe-area insets. The entrance label mounts at the lower left at 24px from the edges, width `min(412px, 50vw - 120px)`, so the vanishing point stays clear. In portrait it spans the top (16px side insets, 12px from the top) over the bare wall above the arch, and drops its note; at max-height 500px it shrinks padding and type and also drops the note. The info panel occupies one side of the viewport beside the painting, with its own scroll; its geometry and unfold are driven by `transition.ts`. The dome's back pill sits at the top left (14px insets). Zoom buttons sit at the painting's lower right corner, offset 10px inside it.

Spacing is set per component rather than from a scale; recurring values are the 24px/16px edge insets and the 5px by 16px list gap.

## Elevation & Depth

Depth belongs to the 3D hall. The UI is nearly flat: one mounting shadow for the entrance plaque, a small lift for the floating zoom buttons, a 1px ring at the panel's edge. All shadows are ink-tinted and soft; none are hard or offset.

### Shadow Vocabulary
- **Mounting** (`box-shadow: 0 1px 2px rgb(42 39 36 / 0.16), 0 8px 24px rgb(42 39 36 / 0.14)`): the entrance plaque, as if hung on the wall.
- **Control lift** (`box-shadow: 0 1px 2px rgb(42 39 36 / 0.2), 0 4px 12px rgb(42 39 36 / 0.16)`): round zoom buttons over the painting.
- **Panel edge** (`box-shadow: 0 0 0 1px rgb(0 0 0 / 0.06)`): the info panel's seam against the dimmed hall.

### Named Rules
**The Hung, Not Floating Rule.** A plaque gets a close contact shadow plus a soft spread, the way a label sits on a wall. No glows, no hard offsets.

## Shapes

Plaques and the panel are square-cornered, like printed labels. Controls are round: pills (999px) for text controls, full circles for icon buttons and detail dots. The only small radius is the 8px detail-fact button. A single 1px hairline in ink at 16% alpha divides the entrance label's text from its list.

## Components

### Buttons
- **Back (in panel):** text plus a drawn back arrow, Field Grey, no fill, pill radius, min-height 44px; it reads as a line of the label.
- **Back (floating, the dome):** the same control on a 90% paper pill so it reads over the vault.
- **Zoom:** 40px paper circles (94%) with a 16px line icon, control-lift shadow; disabled at 40% opacity.
- **Focus:** 2px Arch Red outline, 2px offset, inside a 6px paper halo so it reads on paper, marble or the dimmed hall.

### Cards / Containers
- **Entrance label:** paper plaque, square, mounting shadow, padding 22px 24px 20px; title, line, muted note, hairline, catalogue list. Fades and rises 6px in over 0.5s on `cubic-bezier(0.16, 1, 0.3, 1)`; no motion under reduced-motion. Takes no pointer events.
- **Info panel:** paper, square, panel-edge ring; back control, italic title, artist and date, catalogue list (Technique, Size, Collection, Credit), source line with an underlined Record link in inherited colour.

### Signature: the painting wall label
Drawn on a canvas texture in the 3D scene beside each painting: paper ground, italic title, artist and date, medium and size, an action line in Field Grey. It is the origin of the system; clicking it unfolds into the info panel.

### Icons
Drawn inline SVG on a 16px grid, stroke 1.5, round caps and joins, no fill, `currentColor`.

## Do's and Don'ts

### Do:
- **Do** set every piece of UI as a wall label: paper (#f4f1ea), ink (#2a2724), Cardo, square corners.
- **Do** put facts in the catalogue list: muted term, ink value.
- **Do** keep the centre axis of the start view clear of UI.
- **Do** use Arch Red only for focus and selection, with the paper halo around the ring.
- **Do** draw icons at stroke 1.5 on a 16px grid, coloured by their text.

### Don't:
- **Don't** use a second typeface, bold weights or tracked uppercase labels.
- **Don't** centre a hero stack over a wash or fog layer on the start view.
- **Don't** tint UI with the hall's materials (gold, marble cream, #754543).
- **Don't** use hard offset shadows or glows; plaques are hung, not floating.
- **Don't** let UI take the hall's clicks where it doesn't need to; the entrance label is pointer-transparent.
