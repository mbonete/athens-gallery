// Walking up to an entrance banner (Banners.tsx) to read it, and back: the dome's look up, for a
// banner. A tap anywhere, Escape, the back pill or the browser's back button return to the walk.
import gsap from "gsap";
import * as THREE from "three";
import { rig } from "./rig";
import { getState, setState } from "./store";
import { frustumFor, poseAt, type Pose } from "./walk";

let tl: gsap.core.Tween | null = null;
let returnProgress = 0;
const reduced = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const dur = (s: number) => (reduced() ? 0.01 : s);

/** Seen from the axis side: the camera turns 12 deg about the banner towards the axis. The close
 * view stands about 2.1 m back, outside the entrance arch; straight on, the arch's jamb would hide
 * the banner's outer edge. */
const OFF_AXIS = (12 * Math.PI) / 180;

/** In front of the banner, its height (or width) filling 88 % of the view, centred. */
function closePose(mesh: THREE.Mesh): Pose {
  mesh.updateWorldMatrix(true, false);
  const c = new THREE.Vector3().setFromMatrixPosition(mesh.matrixWorld);
  const n = new THREE.Vector3(0, 0, 1).transformDirection(mesh.matrixWorld);
  n.applyAxisAngle(new THREE.Vector3(0, 1, 0), c.x < 0 ? OFF_AXIS : -OFF_AXIS);
  const { w, h } = mesh.userData as { w: number; h: number };
  const f = frustumFor(rig.camera!.aspect);
  const tanV = (f.up + f.down) / 2;
  const tanH = tanV * rig.camera!.aspect;
  const d = Math.max(h / (2 * tanV * 0.88), w / (2 * tanH * 0.88));
  const p = c.clone().addScaledVector(n, d);
  const forward = n.clone().negate();
  return { x: p.x, y: p.y, z: p.z, yaw: Math.atan2(-forward.x, -forward.z), sym: 1, pitch: 0 };
}

export function viewBanner(side: string, opts: { push?: boolean } = {}) {
  const mesh = rig.banners.get(side);
  if (!mesh || getState().mode !== "walk" || rig.drive !== "scroll" || !rig.camera) return;
  setState({ mode: "banner-in" });
  if (opts.push !== false) history.pushState({ banner: side }, "", "#banner");
  returnProgress = rig.progress;
  rig.drive = "manual";
  rig.pose = { ...rig.pose, pitch: rig.pose.pitch ?? 0 };
  tl = gsap.to(rig.pose, {
    ...closePose(mesh), duration: dur(1.3), ease: "power2.inOut",
    onComplete: () => void (getState().mode === "banner-in" && setState({ mode: "banner" })),
  });
}

export function leaveBanner(opts: { pop?: boolean } = {}) {
  const mode = getState().mode;
  if (mode !== "banner-in" && mode !== "banner") return;
  tl?.kill();
  setState({ mode: "banner-out" });
  if (!opts.pop && location.hash === "#banner") history.back();
  const prog = returnProgress;
  tl = gsap.to(rig.pose, {
    ...poseAt(prog), pitch: 0, duration: dur(1.2), ease: "power2.inOut",
    onComplete: () => {
      rig.progress = rig.target = prog;
      rig.drive = "scroll";
      setState({ mode: "walk" });
    },
  });
}

/** Escape and the browser's back button; a reload on #banner starts on the plain walk. */
export function attachBannerKeys() {
  if (location.hash === "#banner") history.replaceState(null, "", location.pathname + location.search);
  const onKey = (e: KeyboardEvent) => e.key === "Escape" && leaveBanner();
  const onPop = () => location.hash !== "#banner" && leaveBanner({ pop: true });
  window.addEventListener("keydown", onKey);
  window.addEventListener("popstate", onPop);
  return () => {
    window.removeEventListener("keydown", onKey);
    window.removeEventListener("popstate", onPop);
  };
}

if (import.meta.env.DEV) (window as unknown as Record<string, unknown>).__banner = { viewBanner, leaveBanner };
