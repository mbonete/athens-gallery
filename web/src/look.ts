// Looking around while standing on the walk (a test, Maria 2026-11-23: "allow users to rotate the
// camera when they want"). Desktop: click and drag (Maria, 2026-11-27: the plain drag, no longer
// Shift + drag only); a press that moves less than SLOP_PX remains a click. The right button turns
// from the first pixel. Touch: drag one finger; a short touch remains a tap, and adding a second
// finger hands the gesture to the spread/pinch walk (input.ts).
//
// The turn is an offset on the walk's pose that the render loop adds every frame (Scene.tsx), so
// the walk, the walk-ups, the dome and the banners keep their own poses. Walking (scroll, pinch,
// keys) eases it back to straight ahead; Escape or a double right-click do the same; opening a
// painting, the dome or a banner takes it out over that walk-up. Raphael's shift lens is set for
// looking straight ahead: it blends out as the view turns and back in as it comes back, so at rest
// the view is the plain walk's, to the pixel.
import gsap from "gsap";
import { rig } from "./rig";
import { getState, subscribe } from "./store";
import type { Pose } from "./walk";

// ------------------------------------------------------------------------------------ tuning

const DEG = Math.PI / 180;
/** The furthest the view turns: left or right, and up or down. */
export const YAW_LIMIT = 70 * DEG;
export const PITCH_LIMIT = 35 * DEG;
/** Near the entrance the model ends just outside Raphael's frame: turned further than this, the
 * start view shows the sky beside the entrance wall and the end of the floor. There the turn is
 * held to these, widening to the full limits (with the square of the distance) over the first
 * TAPER_M metres of the walk. In development, ?look=wide turns the full limits on everywhere.
 * Phones share these limits (Maria, 2026-11-24): a landscape phone sees as wide as the desktop
 * (frustumFor caps both at 42 degrees each side) and less high, so it never shows more of the
 * building than the desktop does. */
export const ENTRANCE_YAW = 25 * DEG;
export const ENTRANCE_PITCH_UP = 15 * DEG;
export const TAPER_M = 14;
/** Drag gain. At 1 the spot under the pointer stays under it (exactly so on the horizon). */
export const SENSITIVITY = 1;
/** Touch drag gain: 1, the same grab as the mouse (the hall follows the finger). It was 3 while a
 * capture bug stopped every swipe after its first move (onLost), which made the turn feel stuck. */
export const TOUCH_SENSITIVITY = 1;
/** true: the hall moves with the pointer, as in a photo sphere. false: the view turns towards
 * the pointer, as in a game. */
export const GRAB = true;
/** On release the turn carries on at the pointer's speed and slows to a stop over this long (s). */
export const RELEASE_S = 0.3;
/** Walking, Escape or a double right-click bring the view back to straight ahead over this long (s). */
export const RECENTRE_S = 0.6;
export const RECENTRE_EASE = "sine.inOut";
/** Opening a painting, the dome or a banner while turned: the view comes round over the walk-up's
 * time and curve (transition.ts, dome.ts, banner.ts: 1.3 s, power2.inOut). */
export const HANDOFF_S = 1.3;
export const HANDOFF_EASE = "power2.inOut";
/** Under reduced motion every ease is a cut this long (s); the drag itself still follows the pointer. */
export const CUT_S = 0.01;
/** Mouse left button: a press that moves less than this (CSS px) is still a click. */
export const SLOP_PX = 4;
/** A finger naturally wanders more than a mouse: keep movement within this distance a tap. */
export const TOUCH_SLOP_PX = 10;
/** Turned at least this far from straight ahead, the view faces what it's turned to: a two-finger
 * spread over a painting opens it instead of walking (input.ts). Below it, a spread always walks,
 * so a stray few degrees left over from a tap that slid don't turn a walk into a walk-up. */
export const ASIDE = 10 * DEG;
/** Two right-clicks this close in time (ms, release to press) and place (CSS px) recentre. */
export const DOUBLE_MS = 400;
export const DOUBLE_PX = 8;
/** The lens shift is gone when the turn reaches this fraction of its limits (1: at the limits). */
export const LENS_GONE_AT = 1;
/** While the lens shift blends out, tilt the camera up by the angle it held, so the picture
 * doesn't slide up the screen as the view turns sideways (the horizon stays a third up). */
export const LENS_HOLD_PICTURE = true;

// ------------------------------------------------------------------------------------- state

/** The turn in radians, added to the walk's pose: yaw positive to the left, pitch positive up. */
export const look = { yaw: 0, pitch: 0 };

/** The release glide or a recentre. */
let ease: gsap.core.Tween | null = null;
let recentring = false;
type Sample = { t: number; yaw: number; pitch: number };
type Drag = { id: number; x: number; y: number; touch: boolean; right: boolean; turning: boolean; moved: number; samples: Sample[] };
let drag: Drag | null = null;
/** The press under way, or the one just released, turned the view: it isn't a click (pick.ts). */
let turned = false;
let lastRight: { t: number; x: number; y: number } | null = null;
let stage: HTMLElement | null = null;

const reduced = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const dur = (s: number) => (reduced() ? CUT_S : s);
const clamp = (v: number, lim: number, low = lim) => Math.min(lim, Math.max(-low, v));
const WIDE = import.meta.env.DEV && new URLSearchParams(window.location.search).get("look") === "wide";
const walking = () => getState().mode === "walk" && rig.drive === "scroll" && !!rig.camera;
const atRest = () => look.yaw === 0 && look.pitch === 0;
const MAC = typeof navigator !== "undefined" && /Mac/.test(navigator.platform);

/** A press that asks for the context menu: the right button, or Control + click on a Mac. */
export const secondary = (e: PointerEvent | MouseEvent) => e.button === 2 || (MAC && e.button === 0 && e.ctrlKey);
/** For pick.ts: the press just released turned the view, so it opens nothing. */
export const turnedThisPress = () => turned;
/** For pick.ts: a turn is being dragged (no hover picking meanwhile). */
export const turning = () => !!drag?.turning;
/** For input.ts: the view is turned aside (ASIDE or more) and not on its way back to straight
 * ahead, as it is just after walking. */
export const turnedAside = () => !recentring && Math.hypot(look.yaw, look.pitch) >= ASIDE;

// ---------------------------------------------------------------------------------- the view

/** The camera's turn and lens at `pose` with the look added (`f`: the walk's frustum,
 * walk.frustumFor). With no turn, exactly the pose's own values. */
export function looked(pose: Pose, f: { up: number; down: number }) {
  const yaw0 = pose.yaw, pitch0 = pose.pitch ?? 0, sym0 = pose.sym;
  if (atRest()) return { yaw: yaw0, pitch: pitch0, sym: sym0 };
  const k = Math.min(1, Math.hypot(look.yaw / YAW_LIMIT, look.pitch / PITCH_LIMIT) / LENS_GONE_AT);
  const sym = 1 - (1 - sym0) * (1 - k);
  // The shift lens points the middle of the frame atan(c) above the camera's axis, c = half the
  // difference of its extents; with less shift, the camera tilts up by the difference.
  const half = (f.up - f.down) / 2;
  const hold = LENS_HOLD_PICTURE ? Math.atan((1 - sym0) * half) - Math.atan((1 - sym) * half) : 0;
  return { yaw: yaw0 + look.yaw, pitch: Math.min(Math.PI / 2, pitch0 + look.pitch + hold), sym };
}

function stopEase() {
  ease?.kill();
  ease = null;
  recentring = false;
}

/** Bring the view back to straight ahead; nothing if it's there or already on its way. */
export function recentre(seconds = RECENTRE_S, curve = RECENTRE_EASE) {
  endDrag(false);
  if (recentring || atRest()) return;
  stopEase();
  recentring = true;
  ease = gsap.to(look, {
    yaw: 0, pitch: 0, duration: dur(seconds), ease: curve,
    onComplete: () => {
      look.yaw = look.pitch = 0;
      ease = null;
      recentring = false;
    },
  });
  rig.kick();
}

/** How far the view may turn where the visitor stands. */
function limits() {
  if (WIDE) return { yaw: YAW_LIMIT, up: PITCH_LIMIT };
  const t = Math.min(1, Math.max(0, -rig.pose.z / TAPER_M)) ** 2;
  return { yaw: ENTRANCE_YAW + (YAW_LIMIT - ENTRANCE_YAW) * t, up: ENTRANCE_PITCH_UP + (PITCH_LIMIT - ENTRANCE_PITCH_UP) * t };
}

/** Radians per CSS px of drag: what one pixel spans at the middle of the view. */
function radPerPx(touch: boolean) {
  const cam = rig.camera!;
  const h = stage?.clientHeight || window.innerHeight;
  return (SENSITIVITY * (touch ? TOUCH_SENSITIVITY : 1) * (cam.tanUp + cam.tanDown)) / h;
}

function endDrag(glide: boolean) {
  const d = drag;
  if (!d) return;
  drag = null;
  if (stage) {
    stage.style.cursor = "";
    if (stage.hasPointerCapture(d.id)) stage.releasePointerCapture(d.id);
  }
  if (!glide || !d.turning || reduced()) return;
  // The pointer's speed over its last ~80 ms; none if it had stopped before letting go.
  const now = performance.now();
  const s = d.samples.filter((x) => now - x.t < 100);
  if (s.length < 2 || now - s[s.length - 1].t > 60) return;
  const a = s[0], b = s[s.length - 1];
  const dt = (b.t - a.t) / 1000;
  if (dt <= 0) return;
  // power2.out leaves at 2 / duration of its distance per second: the distance that matches the
  // pointer's speed is speed x duration / 2.
  const reach = RELEASE_S / 2;
  const lim = limits();
  const to = {
    yaw: clamp(look.yaw + ((b.yaw - a.yaw) / dt) * reach, lim.yaw),
    pitch: clamp(look.pitch + ((b.pitch - a.pitch) / dt) * reach, lim.up, PITCH_LIMIT),
  };
  if (Math.hypot(to.yaw - look.yaw, to.pitch - look.pitch) < 0.002) return;
  ease = gsap.to(look, { ...to, duration: RELEASE_S, ease: "power2.out", onComplete: () => void (ease = null) });
  rig.kick();
}

function beginTurn(e: PointerEvent) {
  drag!.turning = true;
  turned = true;
  stopEase();
  stage!.setPointerCapture(e.pointerId);
  if (!drag!.touch) stage!.style.cursor = GRAB ? "grabbing" : "move";
}

export function attachLook(el: HTMLElement) {
  stage = el;

  const onDown = (e: PointerEvent) => {
    // A second touch must not reset `turned`: the primary finger may already have turned the view.
    // touchstart below ends that drag and pick.ts separately cancels its pending tap.
    if (!e.isPrimary) return;
    turned = false;
    if (ease && !recentring) stopEase(); // a press catches the release glide
    if (drag || !walking()) return;
    const touch = e.pointerType === "touch";
    if (touch) {
      if (e.button !== 0) return;
      drag = { id: e.pointerId, x: e.clientX, y: e.clientY, touch: true, right: false, turning: false, moved: 0, samples: [] };
      return;
    }
    if (e.pointerType !== "mouse") return;
    const right = secondary(e);
    if (!right && e.button !== 0) return;
    if (right) {
      const l = lastRight;
      lastRight = null;
      if (l && e.timeStamp - l.t < DOUBLE_MS && Math.hypot(e.clientX - l.x, e.clientY - l.y) < DOUBLE_PX) {
        recentre();
        return;
      }
    }
    drag = { id: e.pointerId, x: e.clientX, y: e.clientY, touch: false, right, turning: false, moved: 0, samples: [] };
    if (right) beginTurn(e); // the right button never clicks anything: it turns from the first pixel
  };

  const onMove = (e: PointerEvent) => {
    const d = drag;
    if (!d || e.pointerId !== d.id) return;
    if (!walking()) return endDrag(false);
    if (!d.turning) {
      const slop = d.touch ? TOUCH_SLOP_PX : SLOP_PX;
      if (Math.hypot(e.clientX - d.x, e.clientY - d.y) < slop) return;
      beginTurn(e); // and turn from the press, so the spot pressed stays under the pointer
    }
    const dx = e.clientX - d.x, dy = e.clientY - d.y;
    d.x = e.clientX;
    d.y = e.clientY;
    d.moved += Math.hypot(dx, dy);
    const k = radPerPx(d.touch) * (GRAB ? 1 : -1);
    const lim = limits();
    look.yaw = clamp(look.yaw + dx * k, lim.yaw);
    look.pitch = clamp(look.pitch + dy * k, lim.up, PITCH_LIMIT);
    const now = performance.now();
    d.samples.push({ t: now, yaw: look.yaw, pitch: look.pitch });
    while (d.samples.length > 2 && now - d.samples[0].t > 100) d.samples.shift();
    rig.kick();
  };

  const onUp = (e: PointerEvent) => {
    const d = drag;
    if (!d || e.pointerId !== d.id) return;
    if (d.right && d.moved < DOUBLE_PX) lastRight = { t: e.timeStamp, x: e.clientX, y: e.clientY };
    endDrag(true);
  };
  const onCancel = (e: PointerEvent) => drag && e.pointerId === drag.id && endDrag(false);
  // A touch is captured implicitly by the element it lands on (the canvas). When beginTurn moves
  // the capture to the stage, the canvas's lostpointercapture bubbles up here: only the stage's
  // own loss ends the drag (else every swipe stopped after its first move).
  const onLost = (e: PointerEvent) => e.target === el && onCancel(e);
  // Pointer events keep the primary finger captured after a turn. End it as soon as another
  // finger arrives so input.ts can own the two-finger spread/pinch without the view also turning.
  const onTouchStart = (e: TouchEvent) => {
    if (e.touches.length > 1 && drag?.touch) endDrag(false);
  };

  // The browser's menu would take the right button; on the canvas only (the stage holds nothing else).
  const onMenu = (e: MouseEvent) => e.preventDefault();
  const onKey = (e: KeyboardEvent) => {
    if (e.key === "Escape" && walking()) recentre();
  };
  // Leaving the walk (a painting, the dome, a banner): the view comes round with the walk-up.
  const offStore = subscribe(() => {
    if (getState().mode !== "walk") recentre(HANDOFF_S, HANDOFF_EASE);
  });

  el.addEventListener("pointerdown", onDown);
  el.addEventListener("pointermove", onMove);
  el.addEventListener("pointerup", onUp);
  el.addEventListener("pointercancel", onCancel);
  el.addEventListener("lostpointercapture", onLost);
  el.addEventListener("touchstart", onTouchStart);
  el.addEventListener("contextmenu", onMenu);
  window.addEventListener("keydown", onKey);
  return () => {
    endDrag(false);
    offStore();
    el.removeEventListener("pointerdown", onDown);
    el.removeEventListener("pointermove", onMove);
    el.removeEventListener("pointerup", onUp);
    el.removeEventListener("pointercancel", onCancel);
    el.removeEventListener("lostpointercapture", onLost);
    el.removeEventListener("touchstart", onTouchStart);
    el.removeEventListener("contextmenu", onMenu);
    window.removeEventListener("keydown", onKey);
    stage = null;
  };
}

if (import.meta.env.DEV) {
  // Test hook (dev only): scripted checks of the turn.
  (window as unknown as Record<string, unknown>).__look = { look, recentre, limits, get easing() { return !!ease; }, get dragging() { return !!drag; } };
}
