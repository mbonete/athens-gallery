// The walk: scroll progress (0-1) -> camera pose. Pure functions, no three.js state.
import hall from "./data/hall.json";
import { PAINTINGS, type Painting } from "./paintings";

/** pitch: radians up from horizontal (only the dome look sets it; the walk keeps 0). */
export type Pose = { x: number; y: number; z: number; yaw: number; sym: number; pitch?: number };

const EYE0 = hall.eye[1]; // Raphael's eye above the lower floor (1.295 m at 70 %)
/** Raphael's vanishing point sits at u = 1933.3 of 3840 px: 13.3 px right of centre. */
export const SHIFT_X = (1933.3 - 1920) / 1920;

const clamp01 = (t: number) => Math.min(1, Math.max(0, t));

/** room: free wall length around the piece (its bay, the dome wall, or the doorway's width). */
export type Station = { painting: Painting; side: number; z: number; wallX: number; room: number };

/** The far doorway (end wall's front face, 70 %): the end painting stands just inside it. */
export const END_Z = hall.walkEnd - 1.05 + 0.08;

export const STATIONS: Station[] = PAINTINGS.map((painting) => {
  const { dome, door } = hall;
  if (painting.place === "end") return { painting, side: 0, z: END_Z, wallX: 0, room: door.width };
  if (painting.place === "dome-left") return { painting, side: -1, z: dome.z, wallX: dome.wallX, room: dome.length };
  if (painting.place === "dome-right") return { painting, side: 1, z: dome.z, wallX: dome.wallX, room: dome.length };
  const place = hall.places.find((p) => p.n === painting.place)!;
  // Each place has its own wall plane (bay 1's paintings hang in the recess, further out).
  return { painting, side: place.side, z: place.z, wallX: place.wallX ?? hall.wallX, room: place.bayWidth };
}).sort((a, b) => b.z - a.z);

/** The walk stops where a painting in the doorway is seen whole (5.5 m before it). */
const WALK_END = STATIONS.some((s) => s.side === 0) ? Math.max(hall.walkEnd, END_Z + 5.5) : hall.walkEnd;

// Scroll only walks the corridor, facing forward. Lengths in metres of walk. No hold at the start
// (was 2.5 m: 125 px of wheel, more than a light trackpad scroll, moved nothing; Maria: "a user
// lightly beginning a mouse scroll movement would see nothing happening"): the first pixel walks.
const HOLD = 0;
export const TOTAL = HOLD + Math.abs(WALK_END);

export function poseAt(progress: number): Pose {
  const u = clamp01(progress) * TOTAL;
  const z = u <= HOLD ? 0 : -(u - HOLD);
  return withHeight({ x: 0, z: Math.max(z, WALK_END), yaw: 0, sym: 0 });
}

/** Scroll progress for the point of the walk at depth z. */
export function progressAt(z: number) {
  return (HOLD - Math.min(0, Math.max(z, WALK_END))) / TOTAL;
}

/** Scroll progress for a point a few metres before a painting, where it's in view on the
 * side (used to open a link to a painting). */
export function progressNear(st: Station) {
  if (st.side === 0) return 1;
  return (HOLD - linkZ(st)) / TOTAL;
}

/** Where a link to a wall painting starts the walk: 6 m before it. */
function linkZ(st: Station) {
  return Math.min(0, st.z + 6);
}

/** Eye height for everything that moves along the walk (the walk, Back from a painting, the
 * dome). It never changes (Maria: "point of view should be at same height from beginning to
 * end"): the visitor glides over the stair at Raphael's eye, so the whole walk keeps the fresco's
 * horizon, which on the platform sits about hip-high on his figures. */
export function eyeAt() {
  return EYE0;
}

function withHeight(p: Omit<Pose, "y">): Pose {
  return { ...p, y: eyeAt() };
}

/** Frustum for a screen: Raphael's vertical extents where the screen allows, widened on
 * narrow (portrait) screens so the horizontal view stays at least ~50 degrees, narrowed on
 * very wide screens. The horizon stays at Raphael's height (one third from the bottom). */
export function frustumFor(aspect: number) {
  const { tanUp, tanDown } = hall.frustum;
  let total = tanUp + tanDown;
  const minHalfW = Math.tan((25 * Math.PI) / 180);
  const maxHalfW = Math.tan((42 * Math.PI) / 180);
  if ((aspect * total) / 2 < minHalfW) total = (2 * minHalfW) / aspect;
  if ((aspect * total) / 2 > maxHalfW) total = (2 * maxHalfW) / aspect;
  const up = (total * tanUp) / (tanUp + tanDown);
  return { up, down: total - up };
}
