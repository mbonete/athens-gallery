// Shared, mutable state the render loop reads every frame. GSAP animates these values.
import type { ShiftCamera } from "./ShiftCamera";
import type { Pose } from "./walk";
import type { Mesh, Object3D } from "three";

export const rig = {
  /** "scroll": pose follows scroll progress. "manual": pose is animated directly. */
  drive: "scroll" as "scroll" | "manual",
  progress: 0,
  /** Where the walk is heading (0-1); progress glides toward it. */
  target: 0,
  pose: { x: 0, y: 1.3, z: 0, yaw: 0, sym: 0 } as Pose,
  /** Hall light, 1 = normal, ~0.1 = dimmed around a painting. */
  light: 1,
  camera: null as ShiftCamera | null,
  paintingMeshes: new Map<string, Mesh>(),
  plaques: new Map<string, Object3D>(),
  /** The entrance banners (Banners.tsx), by side; userData holds their w and h. */
  banners: new Map<string, Mesh>(),
};
