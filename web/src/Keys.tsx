// Keyboard and screen-reader access to what a tap does. Each painting (in walk order) and the
// dome get a real button, visually hidden: Tab reaches them, Enter or Space opens them as a tap
// would (enter / lookUp), and a painting's button is named after its title and artist. Focusing
// a button walks the visitor to where its painting (or the dome) is in view. While a button has
// keyboard focus it sits over its painting or the dome on screen, so the focus ring is drawn
// around the thing itself. Buttons never take pointer events: taps still go to the canvas.
import { useFrame, useThree } from "@react-three/fiber";
import { useEffect, useRef, type RefObject } from "react";
import { DOME } from "./data/dome";
import { domeBox, lookUp } from "./dome";
import { walkTo } from "./input";
import { recentre } from "./look";
import { rig } from "./rig";
import { getState, useStore } from "./store";
import { enter } from "./transition";
import { t } from "./i18n";
import { words } from "./paintings";
import { cameraAt, inside, paintingAndLabelBox, paintingBox, type Box } from "./view";
import { poseAt, progressAt, STATIONS, type Station } from "./walk";

const DOME_KEY = "dome";

/** Walk order: nearest first, the left wall before the right one. The dome comes before the two
 * paintings under it, so that after looking up, Tab carries on to them. */
const STOPS: (Station | typeof DOME_KEY)[] = (() => {
  const st: (Station | typeof DOME_KEY)[] = [...STATIONS].sort((a, b) => b.z - a.z || a.side - b.side);
  const i = st.findIndex((s) => s !== DOME_KEY && s.z <= DOME.z);
  st.splice(i < 0 ? st.length : i, 0, DOME_KEY);
  return st;
})();
const keyOf = (s: Station | typeof DOME_KEY) => (s === DOME_KEY ? DOME_KEY : s.painting.slug);
const stationOf = (key: string) => STATIONS.find((s) => s.painting.slug === key);

/** How far the focus ring (outline and halo, styles.css) reaches outside its box, px. */
const RING = 8;
/** The dome counts as in view when this much of it shows (px each way). */
const DOME_MIN = 64;

const walking = () => getState().mode === "walk" && rig.drive === "scroll";
const margin = (r: DOMRect) => RING + Math.max(12, 0.04 * Math.min(r.width, r.height));

/** The point of the walk nearest the painting from which it's still whole on screen with its
 * label: as close as the walk gets with the painting in view. On screens too narrow for that,
 * the same for the painting alone, then for its centre. */
function paintingSpot(st: Station, r: DOMRect) {
  const slug = st.painting.slug;
  const m = margin(r);
  const at = (p: number) => cameraAt(poseAt(p));
  const tests = [
    (p: number) => { const b = paintingAndLabelBox(slug, at(p), r); return !!b && inside(b, r, m); },
    (p: number) => { const b = paintingBox(slug, at(p), r); return !!b && inside(b, r, m); },
    (p: number) => {
      const b = paintingBox(slug, at(p), r);
      if (!b) return false;
      const c = { x0: (b.x0 + b.x1) / 2, x1: (b.x0 + b.x1) / 2, y0: (b.y0 + b.y1) / 2, y1: (b.y0 + b.y1) / 2 };
      return inside(c, r, m);
    },
  ];
  const end = st.side === 0 ? 1 : progressAt(st.z);
  for (const fits of tests) {
    if (fits(end)) return end;
    if (!fits(0)) continue;
    let lo = 0, hi = end;
    for (let i = 0; i < 24; i++) {
      const mid = (lo + hi) / 2;
      if (fits(mid)) lo = mid;
      else hi = mid;
    }
    return lo;
  }
  return null;
}

/** Walk to the painting's spot, unless it's already whole on screen at 3/4 of the size it has there. */
function bringPainting(st: Station, r: DOMRect) {
  const spot = paintingSpot(st, r);
  if (spot === null) return;
  const slug = st.painting.slug;
  const height = (p: number) => {
    const b = paintingBox(slug, cameraAt(poseAt(p)), r);
    return b ? b.y1 - b.y0 : 0;
  };
  const now = rig.target;
  const whole = paintingAndLabelBox(slug, cameraAt(poseAt(now)), r);
  if (whole && inside(whole, r, margin(r)) && height(now) >= 0.75 * height(spot)) return;
  walkTo(spot);
}

let focusId = 0;
const domeSpots = new Map<string, number | null>();

/** The point of the walk nearest the crossing from which the drum and the dome are whole on
 * screen (from further in, the top of the screen cuts them; past the middle of the nave they
 * drop out of sight). Where they're never whole, the nearest point where enough of them shows.
 * The test draws the dome's picking mask, so the hall's real occlusion counts: a GPU read per
 * step, so the answer is kept for each screen size. */
async function domeSpot(el: HTMLElement, id: number) {
  const r = el.getBoundingClientRect();
  const size = `${r.width}x${r.height}`;
  if (domeSpots.has(size)) return domeSpots.get(size)!;
  const m = margin(r);
  const box = (p: number) => domeBox(el, cameraAt(poseAt(p)), true);
  const tests = [
    async (p: number) => { const b = await box(p); return domeShows(b) && inside(b!, r, m); },
    async (p: number) => domeShows(await box(p)),
  ];
  const end = progressAt(DOME.z);
  let spot: number | null = null;
  for (const fits of tests) {
    if (!(await fits(0))) continue;
    let lo = 0, hi = end;
    for (let i = 0; i < 10; i++) {
      if (id !== focusId) return undefined; // focus moved on: don't keep a half search
      const mid = (lo + hi) / 2;
      if (await fits(mid)) lo = mid;
      else hi = mid;
    }
    spot = lo;
    break;
  }
  domeSpots.set(size, spot);
  return spot;
}

const domeShows = (b: Box | null) => !!b && b.x1 - b.x0 >= DOME_MIN && b.y1 - b.y0 >= DOME_MIN;
const domeHeight = (b: Box | null) => (b ? b.y1 - b.y0 : 0);

/** Walk to the dome's spot, unless the drum and the dome are already whole on screen at 3/4 of
 * the size they have there. */
async function bringDome(el: HTMLElement, id: number) {
  const spot = await domeSpot(el, id);
  if (spot === undefined || spot === null || id !== focusId) return;
  const r = el.getBoundingClientRect();
  const now = rig.target;
  const [here, there] = [await domeBox(el, cameraAt(poseAt(now)), true), await domeBox(el, cameraAt(poseAt(spot)), true)];
  if (id !== focusId) return;
  if (domeShows(here) && inside(here!, r, margin(r)) && domeHeight(here) >= 0.75 * domeHeight(there)) return;
  walkTo(spot);
}

/** Is any of the painting on screen now, with its label in front of the camera? */
function onScreen(st: Station, r: DOMRect) {
  if (!rig.camera) return false;
  rig.camera.updateMatrixWorld();
  const b = paintingAndLabelBox(st.painting.slug, rig.camera, r);
  return !!b && b.x1 > r.left && b.x0 < r.right && b.y1 > r.top && b.y0 < r.bottom;
}

/** Set while focus is handed back after closing: that focus doesn't walk anywhere. */
let restoring = false;
let pendingOpen = 0;

export function Keys({ stage }: { stage: RefObject<HTMLDivElement | null> }) {
  const mode = useStore((s) => s.mode);
  const say = t();
  const active = useStore((s) => s.active);
  const ready = useStore((s) => s.ready);
  const wrap = useRef<HTMLDivElement>(null);
  /** The button that opened what's open now. Opened from one of these buttons (keyboard or
   * screen reader), focus moves into the panel or to the dome's Back pill, and comes back to the
   * button afterwards. A tap or click on the canvas leaves focus alone. */
  const opener = useRef<string | null>(null);

  useEffect(() => {
    const to = (el: HTMLElement | null | undefined) => {
      restoring = true;
      el?.focus({ preventScroll: true });
      restoring = false;
    };
    if (mode === "entering") {
      if (opener.current !== active?.slug) opener.current = null;
      // The panel is a dialog named by the title: a screen reader announces it.
      else to(document.querySelector<HTMLElement>(".panel .close"));
    } else if (mode === "looking-up") {
      if (opener.current !== DOME_KEY) opener.current = null;
      else to(document.querySelector<HTMLElement>(".dome-back"));
    } else if (mode === "walk" && opener.current) {
      const key = opener.current;
      opener.current = null;
      // Unless the visitor already moved focus back into the walk.
      if (wrap.current!.contains(document.activeElement)) return;
      to(wrap.current!.querySelector<HTMLElement>(`[data-key="${key}"]`));
    }
  }, [mode, active]);

  const onFocus = (key: string) => {
    rig.kick(); // a frame for KeyRing to put the button over its painting
    if (restoring || !walking() || !stage.current) return;
    recentre(); // where to walk is judged looking straight ahead (look.ts)
    const id = ++focusId;
    if (key === DOME_KEY) bringDome(stage.current, id).catch(() => {});
    else bringPainting(stationOf(key)!, stage.current.getBoundingClientRect());
  };

  const open = (key: string) => {
    if (!walking() || !stage.current) return;
    opener.current = key;
    if (key === DOME_KEY) return lookUp();
    const st = stationOf(key)!;
    const el = stage.current;
    if (onScreen(st, el.getBoundingClientRect())) return enter(st.painting);
    // Activated while out of view (a screen reader can click without focusing first, or Enter
    // came before the walk got there): walk to it first, then open it.
    const spot = paintingSpot(st, el.getBoundingClientRect());
    if (spot !== null) walkTo(spot);
    const id = ++pendingOpen;
    const t0 = performance.now();
    const tick = () => {
      if (id !== pendingOpen || !walking() || performance.now() - t0 > 4000) return;
      const settled = Math.abs(rig.target - rig.progress) < 0.01;
      if (settled && onScreen(st, el.getBoundingClientRect())) enter(st.painting);
      else requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  };

  return (
    <div ref={wrap} className="keys" inert={!ready || mode !== "walk"}>
      {STOPS.map((s) => {
        const key = keyOf(s);
        const w = s === DOME_KEY ? null : words(s.painting);
        const name = w ? `${w.title}, ${w.artist}` : say.lookUpDome;
        return (
          <button key={key} data-key={key} aria-label={name} onFocus={() => onFocus(key)} onClick={() => open(key)} />
        );
      })}
    </div>
  );
}

/** Inside the canvas, after the scene (its frame callback runs after the camera has moved):
 * keeps the keyboard-focused button over its painting or the dome. */
export function KeyRing() {
  const canvas = useThree((s) => s.gl.domElement);
  const placed = useRef<HTMLElement | null>(null);
  const dome = useRef<{ box: Box | null; busy: boolean }>({ box: null, busy: false });

  useFrame(() => {
    const el = document.activeElement;
    const key = el instanceof HTMLElement && el.closest(".keys") ? el.dataset.key : undefined;
    const shown = !!key && el!.matches(":focus-visible") && walking() && !!rig.camera;
    if (placed.current && (!shown || placed.current !== el)) {
      unplace(placed.current);
      placed.current = null;
    }
    if (!shown) {
      dome.current.box = null;
      return;
    }
    const target = el as HTMLElement;
    const r = canvas.getBoundingClientRect();
    rig.camera!.updateMatrixWorld();
    let box: Box | null;
    if (key === DOME_KEY) {
      // The dome's mask comes back from the GPU a frame or two later: one read at a time.
      const d = dome.current;
      if (!d.busy) {
        d.busy = true;
        domeBox(canvas, rig.camera, true).then(
          (b) => {
            // A frame to place it, when it moved (not for every read: the view may be at rest).
            if (JSON.stringify(b) !== JSON.stringify(d.box)) rig.kick();
            d.box = b;
            d.busy = false;
          },
          () => { d.busy = false; },
        );
      }
      box = d.box;
    } else {
      box = paintingBox(key!, rig.camera!, r);
    }
    placed.current = target;
    place(target, box, r);
  });
  return null;
}

function place(el: HTMLElement, b: Box | null, r: DOMRect) {
  // Kept on screen, so a painting partly out of view still shows its ring.
  const x0 = b && Math.max(b.x0, r.left + RING), x1 = b && Math.min(b.x1, r.right - RING);
  const y0 = b && Math.max(b.y0, r.top + RING), y1 = b && Math.min(b.y1, r.bottom - RING);
  if (!b || x1! - x0! < 4 || y1! - y0! < 4) return unplace(el);
  el.classList.add("at");
  el.style.left = `${x0}px`;
  el.style.top = `${y0}px`;
  el.style.width = `${x1! - x0!}px`;
  el.style.height = `${y1! - y0!}px`;
}

function unplace(el: HTMLElement) {
  el.classList.remove("at");
  el.style.removeProperty("left");
  el.style.removeProperty("top");
  el.style.removeProperty("width");
  el.style.removeProperty("height");
}
