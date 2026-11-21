// Where things land on screen: under the live camera, or under a camera standing at some other
// pose (to ask "would this painting be in view from there?" before walking anywhere).
import * as THREE from "three";
import { rig } from "./rig";
import { ShiftCamera } from "./ShiftCamera";
import { frustumFor, SHIFT_X, type Pose } from "./walk";

/** A screen rectangle in client px. */
export type Box = { x0: number; y0: number; x1: number; y1: number };

const probe = new ShiftCamera();
const v = new THREE.Vector3();

/** A camera set up the way the render loop sets up the real one (Scene.tsx) at `pose`. */
export function cameraAt(pose: Pose) {
  const cam = rig.camera!;
  probe.aspect = cam.aspect;
  probe.near = cam.near;
  probe.far = cam.far;
  probe.position.set(pose.x, pose.y, pose.z);
  probe.rotation.set(pose.pitch ?? 0, pose.yaw, 0, "YXZ");
  const f = frustumFor(probe.aspect);
  const mid = (f.up + f.down) / 2;
  probe.tanUp = f.up + (mid - f.up) * pose.sym;
  probe.tanDown = f.down + (mid - f.down) * pose.sym;
  probe.shiftX = SHIFT_X * (1 - pose.sym);
  probe.updateProjectionMatrix();
  probe.updateMatrixWorld(true);
  return probe;
}

/** Screen box of an object's local w x h rectangle (centred on its origin) seen by `cam`, on a
 * canvas at `el`; null when a corner is behind the camera. Grows `out` when given. */
export function boxOf(obj: THREE.Object3D, w: number, h: number, cam: THREE.Camera, el: DOMRect, out?: Box): Box | null {
  const b = out ?? { x0: Infinity, y0: Infinity, x1: -Infinity, y1: -Infinity };
  obj.updateWorldMatrix(true, false);
  for (const [x, y] of [[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2]]) {
    v.set(x, y, 0).applyMatrix4(obj.matrixWorld).project(cam);
    if (v.z < -1 || v.z > 1) return null;
    const sx = el.left + ((v.x + 1) / 2) * el.width;
    const sy = el.top + ((1 - v.y) / 2) * el.height;
    b.x0 = Math.min(b.x0, sx); b.x1 = Math.max(b.x1, sx);
    b.y0 = Math.min(b.y0, sy); b.y1 = Math.max(b.y1, sy);
  }
  return b;
}

/** The painting with its frame (the sizes pick.ts uses). */
export function paintingBox(slug: string, cam: THREE.Camera, el: DOMRect) {
  const mesh = rig.paintingMeshes.get(slug);
  if (!mesh) return null;
  const { w, h } = mesh.userData as { w: number; h: number };
  return boxOf(mesh, w, h, cam, el);
}

/** The painting, its frame and its wall label together. */
export function paintingAndLabelBox(slug: string, cam: THREE.Camera, el: DOMRect) {
  const b = paintingBox(slug, cam, el);
  const plaque = rig.plaques.get(slug);
  return b && plaque ? boxOf(plaque, 0.3, 0.2, cam, el, b) : b;
}

/** Is `b` inside `el`, `inset` px clear of every edge? */
export const inside = (b: Box, el: DOMRect, inset: number) =>
  b.x0 >= el.left + inset && b.x1 <= el.right - inset && b.y0 >= el.top + inset && b.y1 <= el.bottom - inset;
