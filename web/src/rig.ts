// Shared, mutable state the render loop reads every frame. GSAP animates these values.
import { invalidate } from "@react-three/fiber";
import gsap from "gsap";
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
  /** Ask for a frame. The canvas draws only when asked (App.tsx, frameloop "demand"), so whatever
   * changes what it shows outside React's props calls this, and so does every move as it starts
   * (under reduced motion a move is a 0.01 s cut, over before gsap's next update). While the walk
   * glides or a tween runs, the render loop keeps asking (Scene.tsx). */
  kick: () => invalidate(),
};

/** A gsap tween or timeline is running or waiting to start (the global timeline drops each one
 * when it ends or is killed): the walk-ups, the panel, the dome, the banners, the dimming. */
const tweening = () => gsap.globalTimeline.getChildren(false, true, true).length > 0;

/** Is the view still changing: the walk gliding to its target, or a tween. */
export const moving = () => (rig.drive === "scroll" && rig.progress !== rig.target) || tweening();

// Any other tween that starts while the canvas rests asks for its first frame here; from then on
// the render loop asks for each next one (Scene.tsx). The global timeline's update, not a ticker
// listener: an extra listener would stop gsap's ticker from going to sleep when nothing animates.
gsap.globalTimeline.eventCallback("onUpdate", () => void (tweening() && invalidate()));
