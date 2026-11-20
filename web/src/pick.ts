// Choosing a painting by tapping or clicking. Picking happens on screen: each painting's
// outline (painting, frame and label) is projected with the current camera, grown to at
// least a fingertip, and the smallest outline that contains the tap wins. 3D hit areas
// can't do this: on the side walls, seen at a steep angle, a nearer piece hides the
// targets of the ones behind it.
import * as THREE from "three";
import { PAINTINGS } from "./paintings";
import { rig } from "./rig";
import { getState } from "./store";
import { enter } from "./transition";
import { hoverDome, lookDown, tapDome } from "./dome";

const MIN_PX = 48; // a target is never smaller than this on screen
const MARGIN_PX = 12;
const v = new THREE.Vector3();

type Rect = { x0: number; y0: number; x1: number; y1: number };

function screenRectOf(obj: THREE.Object3D, w: number, h: number, out: Rect, el: DOMRect): boolean {
  const cam = rig.camera!;
  obj.updateWorldMatrix(true, false);
  for (const [x, y] of [[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2]]) {
    v.set(x, y, 0).applyMatrix4(obj.matrixWorld).project(cam);
    if (v.z < -1 || v.z > 1) return false; // behind the camera or past the far plane
    const sx = el.left + ((v.x + 1) / 2) * el.width;
    const sy = el.top + ((1 - v.y) / 2) * el.height;
    out.x0 = Math.min(out.x0, sx); out.x1 = Math.max(out.x1, sx);
    out.y0 = Math.min(out.y0, sy); out.y1 = Math.max(out.y1, sy);
  }
  return true;
}

export function pickAt(clientX: number, clientY: number, el: HTMLElement) {
  if (!rig.camera || getState().mode !== "walk" || rig.drive !== "scroll") return null;
  const box = el.getBoundingClientRect();
  let best: { slug: string; area: number } | null = null;
  for (const [slug, mesh] of rig.paintingMeshes) {
    const r: Rect = { x0: Infinity, y0: Infinity, x1: -Infinity, y1: -Infinity };
    const { w, h } = mesh.userData as { w: number; h: number };
    if (!screenRectOf(mesh, w, h, r, box)) continue;
    const plaque = rig.plaques.get(slug);
    if (plaque) screenRectOf(plaque, 0.3, 0.2, r, box);
    // Grow to the minimum size around its centre, then add the margin.
    const cx = (r.x0 + r.x1) / 2, cy = (r.y0 + r.y1) / 2;
    const hw = Math.max(r.x1 - r.x0, MIN_PX) / 2 + MARGIN_PX;
    const hh = Math.max(r.y1 - r.y0, MIN_PX) / 2 + MARGIN_PX;
    if (Math.abs(clientX - cx) > hw || Math.abs(clientY - cy) > hh) continue;
    const area = hw * hh;
    if (!best || area < best.area) best = { slug, area };
  }
  return best ? PAINTINGS.find((p) => p.slug === best!.slug) ?? null : null;
}

export function attachPicking(el: HTMLElement) {
  let down: { x: number; y: number; t: number; up: boolean } | null = null;
  const lookingUp = () => getState().mode === "dome";
  const onDown = (e: PointerEvent) => {
    down = e.isPrimary ? { x: e.clientX, y: e.clientY, t: performance.now(), up: lookingUp() } : null;
  };
  const onUp = (e: PointerEvent) => {
    // A tap, not the end of a pinch or a drag.
    if (!down || !e.isPrimary || Math.hypot(e.clientX - down.x, e.clientY - down.y) > 10) return;
    // Looking up into the dome, a tap anywhere goes back (only one that starts and ends there:
    // taps during the tilts do nothing).
    if (down.up && lookingUp()) {
      down = null;
      lookDown();
      return;
    }
    const p = pickAt(e.clientX, e.clientY, el);
    if (p) enter(p);
    else tapDome(e.clientX, e.clientY, el);
    down = null;
  };
  const onCancel = () => (down = null);
  const onMove = (e: PointerEvent) => {
    if (e.pointerType !== "mouse") return;
    const up = lookingUp(); // a click anywhere goes back
    const p = up ? null : pickAt(e.clientX, e.clientY, el);
    el.style.cursor = p || up ? "pointer" : "";
    hoverDome(e.clientX, e.clientY, el, !!p || up);
  };
  // A second finger turns the gesture into a pinch.
  const onTouch = (e: TouchEvent) => e.touches.length > 1 && (down = null);
  el.addEventListener("pointerdown", onDown);
  el.addEventListener("pointerup", onUp);
  el.addEventListener("pointercancel", onCancel);
  el.addEventListener("pointermove", onMove);
  el.addEventListener("touchstart", onTouch);
  return () => {
    el.removeEventListener("pointerdown", onDown);
    el.removeEventListener("pointerup", onUp);
    el.removeEventListener("pointercancel", onCancel);
    el.removeEventListener("pointermove", onMove);
    el.removeEventListener("touchstart", onTouch);
  };
}
