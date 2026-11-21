// Walking up to a painting, swapping to the zoomable image, and walking back.
import gsap from "gsap";
import type OpenSeadragon from "openseadragon";
import * as THREE from "three";
import { displayH, displayW, type Painting } from "./paintings";
import { rig } from "./rig";
import { getState, setState } from "./store";
import { frustumFor, poseAt, type Pose } from "./walk";

/** DOM pieces owned by <Detail/>, registered on mount. */
export const dom = {
  osd: null as HTMLDivElement | null,
  panel: null as HTMLDivElement | null,
};

/** OpenSeadragon is fetched on its own, after the hall (App.tsx asks for it once the browser is
 * idle) or at the latest when a walk-up starts; the walk-up takes longer than the fetch. */
let zoomLib: Promise<typeof OpenSeadragon> | null = null;
let OSD: typeof OpenSeadragon | null = null;
export function loadZoom() {
  zoomLib ??= import("openseadragon").then(
    (m) => (OSD = m.default),
    (e) => {
      zoomLib = null; // let the next walk-up try again
      throw e;
    },
  );
  return zoomLib;
}

let viewer: OpenSeadragon.Viewer | null = null;
/** The running walk-up, so going back can cancel it. */
let enterTl: gsap.core.Timeline | null = null;
/** Bumped on every enter and leave: late callbacks from an earlier visit see a stale value and do nothing. */
let visit = 0;
/** Where in the corridor the visitor clicked from: Back returns there. */
let returnProgress = 0;
const reduced = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const dur = (s: number) => (reduced() ? 0.01 : s);

/** Where the painting sits on screen once the walk-up ends, leaving room for the panel. */
function targetRect() {
  const W = window.innerWidth;
  const H = window.innerHeight;
  if (W < H) {
    const panelH = Math.round(H * 0.36);
    return { x: 12, y: 60, w: W - 24, h: H - panelH - 60 - 16 };
  }
  const panelW = Math.min(400, Math.round(W * 0.32));
  return { x: 40, y: 40, w: W - panelW - 80, h: H - 80 };
}

/** Panel's resting place (bottom sheet on portrait screens, right column otherwise). */
function panelRect() {
  const W = window.innerWidth;
  const H = window.innerHeight;
  if (W < H) {
    const h = Math.round(H * 0.36);
    return { x: 0, y: H - h, w: W, h };
  }
  const w = Math.min(400, Math.round(W * 0.32));
  return { x: W - w, y: 0, w, h: H };
}

/** Camera pose in front of the painting so it fills `rect` exactly ("contain"), with a
 * symmetric frustum. Solved from the same frustum the render loop will use. */
function walkUpPose(p: Painting, rect: ReturnType<typeof targetRect>): Pose {
  const mesh = rig.paintingMeshes.get(p.slug)!;
  mesh.updateWorldMatrix(true, false);
  const centre = new THREE.Vector3().setFromMatrixPosition(mesh.matrixWorld);
  const normal = new THREE.Vector3(0, 0, 1).transformDirection(mesh.matrixWorld); // into the hall
  const W = window.innerWidth;
  const H = window.innerHeight;
  const aspect = W / H;
  const f = frustumFor(aspect);
  const tanV = (f.up + f.down) / 2;
  const tanH = tanV * aspect;
  const pw = displayW(p);
  const ph = displayH(p);
  const d = Math.max(pw / (2 * tanH * (rect.w / W)), ph / (2 * tanV * (rect.h / H)));
  // Offset the camera so the painting's centre lands on the rect's centre.
  const cxn = ((rect.x + rect.w / 2) / W) * 2 - 1;
  const cyn = 1 - ((rect.y + rect.h / 2) / H) * 2;
  const forward = normal.clone().negate();
  const up = new THREE.Vector3(0, 1, 0);
  const right = new THREE.Vector3().crossVectors(forward, up).normalize();
  const pos = centre
    .clone()
    .addScaledVector(normal, d)
    .addScaledVector(right, -cxn * d * tanH)
    .addScaledVector(up, -cyn * d * tanV);
  const yaw = Math.atan2(-forward.x, -forward.z);
  return { x: pos.x, y: pos.y, z: pos.z, yaw, sym: 1 };
}

/** Screen rect of an object's local-space rectangle under a given pose. */
function screenRect(obj: THREE.Object3D, w: number, h: number, pose: Pose) {
  const cam = rig.camera!.clone() as typeof rig.camera & THREE.PerspectiveCamera;
  const f = frustumFor(cam.aspect);
  const mid = (f.up + f.down) / 2;
  cam.tanUp = f.up + (mid - f.up) * pose.sym;
  cam.tanDown = f.down + (mid - f.down) * pose.sym;
  cam.position.set(pose.x, pose.y, pose.z);
  cam.rotation.set(0, pose.yaw, 0, "YXZ");
  cam.updateMatrixWorld(true);
  cam.updateProjectionMatrix();
  obj.updateWorldMatrix(true, false);
  const W = window.innerWidth;
  const H = window.innerHeight;
  const pts = [[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2]].map(([x, y]) => {
    const v = new THREE.Vector3(x, y, 0).applyMatrix4(obj.matrixWorld).project(cam);
    return { x: ((v.x + 1) / 2) * W, y: ((1 - v.y) / 2) * H };
  });
  const xs = pts.map((p) => p.x);
  const ys = pts.map((p) => p.y);
  return { x: Math.min(...xs), y: Math.min(...ys), w: Math.max(...xs) - Math.min(...xs), h: Math.max(...ys) - Math.min(...ys) };
}

function placePanel(r: { x: number; y: number; w: number; h: number }) {
  const el = dom.panel!;
  Object.assign(el.style, { left: `${r.x}px`, top: `${r.y}px`, width: `${r.w}px`, height: `${r.h}px` });
}

export function enter(p: Painting, opts: { push?: boolean } = {}) {
  if (getState().mode !== "walk" || !rig.camera) return;
  loadZoom().catch(() => {});
  setState({ mode: "entering", active: p });
  if (opts.push !== false) history.pushState({ painting: p.slug }, "", `#painting/${p.slug}`);

  returnProgress = rig.drive === "scroll" ? rig.progress : returnProgress;
  const rect = targetRect();
  const from = { ...rig.pose };
  const to = walkUpPose(p, rect);
  rig.drive = "manual";
  rig.pose = { ...from };

  // The wall label becomes the panel: start the panel on the label's screen rect.
  const plaque = rig.plaques.get(p.slug)!;
  const start = screenRect(plaque, 0.3, 0.2, from);
  placePanel(start);
  const panel = dom.panel!;
  gsap.set(panel, { opacity: 1, visibility: "visible", "--content": 0 });
  (plaque as THREE.Mesh).visible = false;
  const end = panelRect();

  const myVisit = ++visit;
  const tl = gsap.timeline({ onComplete: () => myVisit === visit && openZoom(p, rect, myVisit) });
  enterTl = tl;
  tl.to(rig.pose, { ...to, duration: dur(1.3), ease: "power2.inOut" }, 0);
  tl.to(rig, { light: 0.12, duration: dur(1.1), ease: "power1.inOut" }, 0.1);
  tl.to(start, {
    ...end, duration: dur(0.9), ease: "power3.inOut",
    onUpdate: () => placePanel(start),
  }, 0.15);
  tl.to(panel, { "--content": 1, duration: dur(0.35) }, 0.85);
}

async function openZoom(p: Painting, rect: ReturnType<typeof targetRect>, myVisit: number) {
  const current = () => myVisit === visit && getState().mode === "entering";
  if (!current()) return;
  // Normally loaded long before; if the fetch failed, the 3D painting stays and Back still works.
  const OpenSeadragon = await loadZoom().catch(() => null);
  if (!OpenSeadragon || !current()) return;
  const W = window.innerWidth;
  const H = window.innerHeight;
  const el = dom.osd!;
  gsap.set(el, { opacity: 0, visibility: "visible" });
  viewer?.destroy();
  viewer = OpenSeadragon({
    element: el,
    tileSources: p.dzi,
    showNavigationControl: false,
    viewportMargins: { left: rect.x, top: rect.y, right: W - rect.x - rect.w, bottom: H - rect.y - rect.h },
    visibilityRatio: 0.6,
    minZoomImageRatio: 1,
    maxZoomPixelRatio: p.maxZoom ?? 2.5,
    animationTime: 0.9,
    blendTime: 0,
    immediateRender: false,
    gestureSettingsTouch: { pinchRotate: false, flickEnabled: true },
    gestureSettingsMouse: { clickToZoom: false },
  });
  let shown = false;
  const show = () => {
    if (shown || !current()) return;
    shown = true;
    gsap.to(el, { opacity: 1, duration: dur(0.15), onComplete: () => setState({ mode: "detail" }) });
  };
  viewer.addHandler("open", () => {
    if (!current() || !viewer) return;
    viewer.viewport.goHome(true);
    const item = viewer!.world.getItemAt(0);
    item.addHandler("fully-loaded-change", (e: { fullyLoaded: boolean }) => e.fullyLoaded && show());
    p.hotspots.forEach((hs, i) => {
      const mark = document.createElement("button");
      mark.className = "hotspot";
      mark.setAttribute("aria-label", `Detail ${i + 1}`);
      mark.addEventListener("click", (ev) => {
        ev.stopPropagation();
        focusHotspot(p, i);
      });
      viewer!.addOverlay({
        element: mark,
        location: viewer!.viewport.imageToViewportCoordinates(hs.x * p.imageW, hs.y * p.imageH),
        placement: OpenSeadragon.Placement.CENTER,
      });
    });
    setTimeout(show, 2500); // never hang on a slow tile
  });
}

export function focusHotspot(p: Painting, i: number) {
  if (!viewer) return;
  const hs = p.hotspots[i];
  const pt = viewer.viewport.imageToViewportCoordinates(hs.x * p.imageW, hs.y * p.imageH);
  const span = 0.18;
  viewer.viewport.fitBounds(new OSD!.Rect(pt.x - span / 2, pt.y - span / 2 * 0.75, span, span * 0.75));
  window.dispatchEvent(new CustomEvent("hotspot", { detail: i }));
}

export function leave(opts: { pop?: boolean } = {}) {
  const { mode, active: p } = getState();
  if (!p || (mode !== "detail" && mode !== "entering")) return;
  setState({ mode: "leaving" });
  visit++;
  enterTl?.kill();
  enterTl = null;
  if (!opts.pop && location.hash) history.back();
  window.dispatchEvent(new CustomEvent("hotspot", { detail: -1 }));

  const prog = returnProgress;
  const back = poseAt(prog);
  const plaque = rig.plaques.get(p.slug)!;
  const panel = dom.panel!;
  const el = dom.osd!;

  const walkBack = () => {
    const now = { ...panelRect() };
    const end = screenRect(plaque, 0.3, 0.2, back);
    const tl = gsap.timeline({
      onComplete: () => {
        (plaque as THREE.Mesh).visible = true;
        gsap.set(panel, { visibility: "hidden", opacity: 0 });
        rig.progress = rig.target = prog;
        rig.drive = "scroll";
        setState({ mode: "walk", active: null });
      },
    });
    tl.to(panel, { "--content": 0, duration: dur(0.2) }, 0);
    tl.to(now, { ...end, duration: dur(0.9), ease: "power3.inOut", onUpdate: () => placePanel(now) }, 0.1);
    tl.to(rig.pose, { ...back, duration: dur(1.2), ease: "power2.inOut" }, 0);
    tl.to(rig, { light: 1, duration: dur(1.0), ease: "power1.inOut" }, 0.1);
  };

  if (viewer && mode === "detail") {
    // Zoom back out to the painting's place, then hand over to the 3D painting.
    viewer.viewport.goHome(false);
    let done = false;
    const swapBack = () => {
      if (done) return;
      done = true;
      gsap.to(el, {
        opacity: 0, duration: dur(0.15),
        onComplete: () => {
          gsap.set(el, { visibility: "hidden" });
          viewer?.destroy();
          viewer = null;
          walkBack();
        },
      });
    };
    viewer.addOnceHandler("animation-finish", swapBack);
    setTimeout(swapBack, 1100);
  } else {
    // Left during the walk-up: drop any zoom viewer it may have started.
    gsap.killTweensOf([rig.pose, rig, el]);
    gsap.set(el, { opacity: 0, visibility: "hidden" });
    viewer?.destroy();
    viewer = null;
    walkBack();
  }
}
