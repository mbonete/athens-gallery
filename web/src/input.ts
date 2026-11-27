// Walking input. The page doesn't scroll: one value, rig.target (0-1 along the corridor),
// is moved by gestures, and rig.progress glides toward it every frame.
//
// - Touch: spread two fingers to walk forward, pinch them together to walk back. One finger
//   taps a painting or drags to look around (look.ts). With the view turned aside to face a
//   painting, a spread that begins over it opens it, as a tap would (Maria, 2026-11-27: "when I
//   turn the camera to face a painting I get the urge to zoom in, but I am returned to the main
//   scrolling view"); a pinch there still walks back. The same goes for an entrance banner.
// - Trackpad pinch (Chrome/Edge/Firefox send it as ctrl + wheel; Safari as gesture events):
//   the same.
// - Mouse wheel / two-finger trackpad scroll: down walks forward (for mice without a pinch).
// - Keyboard: ArrowUp/ArrowDown, PageUp/PageDown, Space/Shift+Space, Home/End. Space is left to a
//   focused button (it opens the painting; see Keys.tsx).
import { viewBanner } from "./banner";
import { recentre, turnedAside } from "./look";
import { pickAt, pickBanner } from "./pick";
import { rig } from "./rig";
import { getState } from "./store";
import { enter } from "./transition";
import { TOTAL } from "./walk";

/** Metres walked per doubling of the finger spread. */
const M_PER_DOUBLING = 7;
const M_PER_LOG = M_PER_DOUBLING / Math.LN2;
/** Over a painting the view is turned to face: the fingers this much further apart than where
 * they began open it. Until then the hall holds still, so the view doesn't swing round first. */
const OPEN_SPREAD = 1.2;
/** Pinched this much closer instead, the gesture walks back as usual. */
const BACK_SPREAD = 1 / 1.1;
/** Metres per wheel pixel (a mouse notch is ~100 px -> 2 m). */
const M_PER_WHEEL_PX = 0.02;
const M_PER_KEY = 2;

const clamp01 = (t: number) => Math.min(1, Math.max(0, t));
const walking = () => getState().mode === "walk" && rig.drive === "scroll";
const reduced = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

function walk(metres: number) {
  if (!walking()) return;
  const t = clamp01(rig.target + metres / TOTAL);
  if (t !== rig.target) recentre(); // the walk goes along the hall: the view comes back to it (look.ts)
  rig.target = t;
  rig.kick(); // the glide keeps the frames coming until it settles (Scene.tsx)
}

/** Walk to a point of the walk on the visitor's behalf (a painting got keyboard focus): the
 * same glide as walking, or a cut under reduced motion. */
export function walkTo(progress: number) {
  if (!walking()) return;
  const t = clamp01(progress);
  if (t !== rig.target) recentre();
  rig.target = t;
  if (reduced()) rig.progress = rig.target;
  rig.kick();
}

/** Keys that a focused control handles itself. */
const control = (t: EventTarget | null) =>
  t instanceof Element && !!t.closest("button, a, input, select, textarea, [contenteditable]");

/** What a spread between fingers centred on (x, y) opens: the banner or painting there, the same
 * targets a tap uses (pick.ts), once the visitor has turned the view aside to face it. Looking
 * straight ahead a spread always walks, even over the paintings on the side walls. */
function facing(x: number, y: number, el: HTMLElement): (() => void) | null {
  if (!turnedAside()) return null;
  const b = pickBanner(x, y, el);
  if (b) return () => viewBanner(b);
  const p = pickAt(x, y, el);
  return p ? () => enter(p) : null;
}

export function attachWalkInput(el: HTMLElement) {
  let spread0 = 0;
  /** The pinch began over what the view faces: a spread opens it instead of walking. */
  let aim: (() => void) | null = null;
  /** How far the fingers have parted since then (log of the ratio). */
  let parted = 0;
  const spread = (t: TouchList) => Math.hypot(t[0].clientX - t[1].clientX, t[0].clientY - t[1].clientY);

  const onTouchStart = (e: TouchEvent) => {
    if (e.touches.length !== 2) return;
    const [a, b] = [e.touches[0], e.touches[1]];
    spread0 = spread(e.touches);
    parted = 0;
    aim = facing((a.clientX + b.clientX) / 2, (a.clientY + b.clientY) / 2, el);
  };
  const onTouchMove = (e: TouchEvent) => {
    if (e.touches.length !== 2) return;
    // No page zoom. A pinch that began as a one-finger look arrives uncancelable (the stage's
    // touch-action: none already stops the page zooming); preventing it then only logs an error.
    if (e.cancelable) e.preventDefault();
    const s = spread(e.touches);
    if (spread0 > 0 && s > 0) {
      const d = Math.log(s / spread0);
      if (!aim) walk(d * M_PER_LOG);
      else if ((parted += d) >= Math.log(OPEN_SPREAD)) {
        const open = aim;
        aim = null;
        open(); // the walk-up; the rest of this pinch walks nothing (walk() waits for the walk)
      } else if (parted <= Math.log(BACK_SPREAD)) aim = null; // pinching instead: walk back from here
    }
    spread0 = s;
  };
  const onTouchEnd = (e: TouchEvent) => {
    if (e.touches.length < 2) {
      spread0 = 0;
      aim = null;
    }
  };

  const onWheel = (e: WheelEvent) => {
    e.preventDefault();
    const px = e.deltaMode === 1 ? e.deltaY * 33 : e.deltaMode === 2 ? e.deltaY * innerHeight : e.deltaY;
    if (e.ctrlKey) {
      // Pinch: scale = exp(-deltaY / 100) in Chrome; spread (zoom in) walks forward.
      walk((-px / 100) * M_PER_LOG);
    } else {
      walk(px * M_PER_WHEEL_PX);
    }
  };

  // Safari (macOS trackpad, iOS): gesture events carry the pinch scale.
  let scale0 = 1;
  const onGestureStart = (e: Event) => {
    e.preventDefault();
    scale0 = (e as unknown as { scale: number }).scale || 1;
  };
  const onGestureChange = (e: Event) => {
    e.preventDefault();
    const s = (e as unknown as { scale: number }).scale || 1;
    // iOS also sends touch events for the same pinch; only use gestures where touch is absent.
    if (!("ontouchstart" in window)) walk(Math.log(s / scale0) * M_PER_LOG);
    scale0 = s;
  };

  const onKey = (e: KeyboardEvent) => {
    if (!walking()) return; // inside a painting, keys belong to the zoom viewer
    if (e.defaultPrevented || e.altKey || e.ctrlKey || e.metaKey) return;
    const k = e.key;
    if (k === "ArrowUp" || k === "PageDown") walk(k === "PageDown" ? M_PER_KEY * 4 : M_PER_KEY);
    else if (k === "ArrowDown" || k === "PageUp") walk(k === "PageUp" ? -M_PER_KEY * 4 : -M_PER_KEY);
    else if (k === " " && !control(e.target)) walk(e.shiftKey ? -M_PER_KEY * 4 : M_PER_KEY * 4);
    else if (k === "Home") walk(-TOTAL);
    else if (k === "End") walk(TOTAL);
    else return;
    e.preventDefault();
  };

  const opts = { passive: false } as const;
  el.addEventListener("touchstart", onTouchStart, opts);
  el.addEventListener("touchmove", onTouchMove, opts);
  el.addEventListener("touchend", onTouchEnd);
  el.addEventListener("touchcancel", onTouchEnd);
  el.addEventListener("wheel", onWheel, opts);
  el.addEventListener("gesturestart", onGestureStart, opts);
  el.addEventListener("gesturechange", onGestureChange, opts);
  window.addEventListener("keydown", onKey);
  return () => {
    el.removeEventListener("touchstart", onTouchStart);
    el.removeEventListener("touchmove", onTouchMove);
    el.removeEventListener("touchend", onTouchEnd);
    el.removeEventListener("touchcancel", onTouchEnd);
    el.removeEventListener("wheel", onWheel);
    el.removeEventListener("gesturestart", onGestureStart);
    el.removeEventListener("gesturechange", onGestureChange);
    window.removeEventListener("keydown", onKey);
  };
}

/** Glide rig.progress toward rig.target; call once per frame with the frame time. */
export function glide(dt: number) {
  if (rig.drive !== "scroll") return;
  const k = 1 - Math.exp(-dt * 6); // ~0.4 s to settle
  rig.progress += (rig.target - rig.progress) * k;
  if (Math.abs(rig.target - rig.progress) < 1e-5) rig.progress = rig.target;
}
