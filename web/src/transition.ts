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
  zoomUi: null as HTMLDivElement | null,
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
/** Durations and start times: under reduced motion every move is a cut, all at once. */
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

type Rect = { x: number; y: number; w: number; h: number };

function placePanel(r: Rect) {
  const el = dom.panel!;
  Object.assign(el.style, { left: `${r.x}px`, top: `${r.y}px`, width: `${r.w}px`, height: `${r.h}px` });
}

/** The panel unfolds out of the wall label (Maria: the card must not cover the walk-up). It sits
 * at its resting place the whole time and is revealed by a clip: from the label's spot on screen
 * (kept inside the panel, at least a small card's size) to the whole panel, and back. */
const clipNow: Rect = { x: 0, y: 0, w: 0, h: 0 };
let clipFrame: Rect = { x: 0, y: 0, w: 0, h: 0 };
function labelInPanel(plaque: THREE.Object3D, pose: Pose, P: Rect): Rect {
  const r = screenRect(plaque, 0.3, 0.2, pose);
  const w = Math.min(P.w, Math.max(r.w, 56));
  const h = Math.min(P.h, Math.max(r.h, 36));
  const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));
  return { x: clamp(r.x + r.w / 2 - w / 2, P.x, P.x + P.w - w), y: clamp(r.y + r.h / 2 - h / 2, P.y, P.y + P.h - h), w, h };
}
function clipPanel() {
  const P = clipFrame;
  const c = clipNow;
  dom.panel!.style.clipPath =
    `inset(${c.y - P.y}px ${P.x + P.w - c.x - c.w}px ${P.y + P.h - c.y - c.h}px ${c.x - P.x}px)`;
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

  // The wall label stays on the wall and comes forward with the painting. Once the camera has
  // (nearly) arrived, the panel unfolds out of it. Until then the panel is in place but
  // transparent and lets clicks through: it can still take focus (Keys.tsx moves it to Back).
  const plaque = rig.plaques.get(p.slug)!;
  const panel = dom.panel!;
  const end = panelRect();
  placePanel(end);
  clipFrame = end;
  Object.assign(clipNow, labelInPanel(plaque, to, end));
  clipPanel();
  gsap.set(panel, { opacity: 0, visibility: "visible", pointerEvents: "none", "--content": 1 });

  const myVisit = ++visit;
  const tl = gsap.timeline();
  enterTl = tl;
  tl.to(rig.pose, { ...to, duration: dur(1.3), ease: "power2.inOut" }, 0);
  tl.to(rig, { light: 0.12, duration: dur(1.1), ease: "power1.inOut" }, dur(0.1));
  tl.call(() => {
    (plaque as THREE.Mesh).visible = false;
    gsap.set(panel, { opacity: 1, pointerEvents: "auto" });
  }, [], dur(1.1));
  tl.to(clipNow, { ...end, duration: dur(0.4), ease: "power3.out", onUpdate: clipPanel }, dur(1.1));
  tl.call(() => myVisit === visit && openZoom(p, rect, myVisit), [], dur(1.3));
}

/** The painting's own rect on screen at the end of the walk-up: walkUpPose fits it into `rect`
 * ("contain"), centred. */
function paintingRect(p: Painting, rect: Rect): Rect {
  const pw = displayW(p);
  const ph = displayH(p);
  const s = Math.min(rect.w / pw, rect.h / ph);
  const w = Math.round(pw * s);
  const h = Math.round(ph * s);
  return { x: Math.round(rect.x + (rect.w - w) / 2), y: Math.round(rect.y + (rect.h - h) / 2), w, h };
}

/** Zoom state for the + and - buttons and the cursor (Detail.tsx listens to "zoomstate"). */
function zoomState() {
  if (!viewer) return;
  const vp = viewer.viewport;
  const z = vp.getZoom(false);
  const canIn = z < vp.getMaxZoom() * 0.98;
  const canOut = z > vp.getHomeZoom() * 1.02;
  dom.osd!.dataset.zoom = canIn ? "in" : "out";
  window.dispatchEvent(new CustomEvent("zoomstate", { detail: { canIn, canOut } }));
}

/** The + and - buttons: one click step (x2) about the middle of the view. */
export function zoomStep(dir: 1 | -1) {
  if (!viewer || getState().mode !== "detail") return;
  viewer.viewport.zoomBy(dir > 0 ? 2 : 0.5, undefined, reduced());
  viewer.viewport.applyConstraints(reduced());
}

async function openZoom(p: Painting, rect: ReturnType<typeof targetRect>, myVisit: number) {
  const current = () => myVisit === visit && getState().mode === "entering";
  if (!current()) return;
  // Normally loaded long before; if the fetch failed, the 3D painting stays and Back still works.
  const OpenSeadragon = await loadZoom().catch(() => null);
  if (!OpenSeadragon || !current()) return;
  // Click to zoom, drag to pan (Maria, 2026-11-21): the viewer is exactly the painting's rect, and
  // the image always fills it (visibilityRatio 1), so the painting never leaves its frame and the
  // 3D one behind it never shows. Mouse: a click zooms x2 on that spot, at full zoom a click goes
  // back to the whole painting; drag pans; the wheel zooms. Touch: pinch, double-tap, one-finger drag.
  const el = dom.osd!;
  const pr = paintingRect(p, rect);
  Object.assign(el.style, { left: `${pr.x}px`, top: `${pr.y}px`, width: `${pr.w}px`, height: `${pr.h}px` });
  const ui = dom.zoomUi!;
  Object.assign(ui.style, { left: `${pr.x + pr.w}px`, top: `${pr.y + pr.h}px` });
  gsap.set(el, { opacity: 0, visibility: "visible" });
  viewer?.destroy();
  viewer = OpenSeadragon({
    element: el,
    tileSources: p.dzi,
    showNavigationControl: false,
    visibilityRatio: 1,
    constrainDuringPan: true,
    minZoomImageRatio: 1,
    maxZoomPixelRatio: p.maxZoom ?? 2.5,
    zoomPerClick: 2,
    zoomPerScroll: 1.25,
    animationTime: reduced() ? 0 : 0.6,
    springStiffness: 8,
    blendTime: 0,
    immediateRender: false,
    gestureSettingsMouse: { clickToZoom: false, dblClickToZoom: false, scrollToZoom: true, flickEnabled: false },
    gestureSettingsPen: { clickToZoom: false, dblClickToZoom: false },
    gestureSettingsTouch: { clickToZoom: false, dblClickToZoom: true, pinchToZoom: true, pinchRotate: false, flickEnabled: true },
  });
  viewer.addHandler("canvas-click", (e) => {
    const oe = e.originalEvent as Event & { pointerType?: string };
    const touch = oe?.pointerType === "touch" || oe?.type?.startsWith("touch");
    if (!viewer || !e.quick || touch) return; // a drag, or a tap (double-tap zooms)
    e.preventDefaultAction = true;
    const vp = viewer.viewport;
    if (vp.getZoom(false) >= vp.getMaxZoom() * 0.98) vp.goHome(reduced());
    else vp.zoomBy(2, vp.pointFromPixel(e.position), reduced());
    vp.applyConstraints(reduced());
  });
  viewer.addHandler("canvas-press", () => {
    if (viewer && viewer.viewport.getZoom(false) > viewer.viewport.getHomeZoom() * 1.02) el.dataset.drag = "";
  });
  viewer.addHandler("canvas-release", () => delete el.dataset.drag);
  viewer.addHandler("zoom", zoomState);
  let shown = false;
  const show = () => {
    if (shown || !current()) return;
    shown = true;
    gsap.to(el, { opacity: 1, duration: dur(0.15), onComplete: () => setState({ mode: "detail" }) });
  };
  viewer.addHandler("open", () => {
    if (!current() || !viewer) return;
    viewer.viewport.goHome(true);
    zoomState();
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
  viewer.viewport.fitBounds(new OSD!.Rect(pt.x - span / 2, pt.y - span / 2 * 0.75, span, span * 0.75), reduced());
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
    // The panel folds back into the label first (from wherever its unfolding got to), the label
    // is on the wall again, and then the walk back starts.
    const fold = labelInPanel(plaque, rig.pose, clipFrame);
    const tl = gsap.timeline({
      onComplete: () => {
        (plaque as THREE.Mesh).visible = true;
        gsap.set(panel, { visibility: "hidden", opacity: 0 });
        rig.progress = rig.target = prog;
        rig.drive = "scroll";
        setState({ mode: "walk", active: null });
      },
    });
    tl.to(clipNow, { ...fold, duration: dur(0.25), ease: "power2.in", onUpdate: clipPanel }, 0);
    tl.call(() => {
      gsap.set(panel, { opacity: 0, pointerEvents: "none" });
      (plaque as THREE.Mesh).visible = true;
    }, [], dur(0.25));
    tl.to(rig.pose, { ...back, duration: dur(1.2), ease: "power2.inOut" }, dur(0.2));
    tl.to(rig, { light: 1, duration: dur(1.0), ease: "power1.inOut" }, dur(0.25));
  };

  if (viewer && mode === "detail") {
    // Zoom back out to the painting's place, then hand over to the 3D painting. Under reduced
    // motion the zoom out is a cut (one frame for the viewer to draw it, then the swap).
    const vp = viewer.viewport;
    vp.goHome(false);
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
    const zoomed = Math.abs(vp.getZoom(true) / vp.getZoom(false) - 1) > 1e-4 ||
      vp.getCenter(true).distanceTo(vp.getCenter(false)) > 1e-5;
    if (!zoomed) {
      // Already home: no zoom-out animation runs, so animation-finish would never come.
      swapBack();
    } else if (reduced()) {
      vp.goHome(true);
      requestAnimationFrame(() => requestAnimationFrame(swapBack));
    } else {
      viewer.addOnceHandler("animation-finish", swapBack);
      setTimeout(swapBack, 1100);
    }
  } else {
    // Left during the walk-up: drop any zoom viewer it may have started.
    gsap.killTweensOf([rig.pose, rig, el]);
    gsap.set(el, { opacity: 0, visibility: "hidden" });
    viewer?.destroy();
    viewer = null;
    walkBack();
  }
}

if (import.meta.env.DEV) {
  // Test hook (dev only): scripted checks of the zoom viewer.
  (window as unknown as Record<string, unknown>).__zoom = { get viewer() { return viewer; } };
}
