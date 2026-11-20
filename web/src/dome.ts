// Looking up into the dome: tapping the drum or the dome (or the pendentives under it) walks
// the visitor to the centre of the crossing and tilts the camera until it looks straight up.
// Back, Escape or the browser's back tilts down again and the walk carries on from there.
//
// Picking: the dome is often seen only in part, through the nave vault and the crossing's front
// arch, and through its windows you see sky. So the test is done on the GPU: a small patch of
// the screen around the pointer is drawn again with one material that marks every surface of
// the dome's zone (DOME) in white, using the real hall geometry and depth, so whatever hides the
// dome on screen hides it here too. Two invisible plugs, behind the drum's windows and above the
// oculus, make the sky seen through them count as dome.
import gsap from "gsap";
import * as THREE from "three";
import { DOME } from "./data/dome";
import { rig } from "./rig";
import { getState, setState } from "./store";
import { poseAt, progressAt } from "./walk";

/** Drawn only by the picking pass (the main camera sees layer 0 only). */
const PICK_LAYER = 7;
/** A tap or hover counts if dome shows within this many CSS pixels of it. */
export const PICK_RADIUS_PX = 16;
const PICK_TEXELS = 16; // the patch is drawn at 2 CSS px per texel

const reduced = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const dur = (s: number) => (reduced() ? 0.01 : s);

// ------------------------------------------------------------------------------------ picking

let renderer: THREE.WebGLRenderer | null = null;
let scene: THREE.Scene | null = null;
const pickCam = new THREE.Camera();
pickCam.matrixAutoUpdate = false;
pickCam.matrixWorldAutoUpdate = false;
pickCam.layers.set(0);
pickCam.layers.enable(PICK_LAYER);

const mark = new THREE.ShaderMaterial({
  uniforms: {
    uZ: { value: DOME.z }, uHalf: { value: DOME.half }, uSpring: { value: DOME.spring },
    uDrum: { value: DOME.drumBase }, uWin: { value: DOME.windows[0] }, uOuter: { value: DOME.outer },
  },
  vertexShader: /* glsl */ `
    varying vec3 vW;
    void main() {
      vec4 w = modelMatrix * vec4(position, 1.0);
      vW = w.xyz;
      gl_Position = projectionMatrix * viewMatrix * w;
    }`,
  fragmentShader: /* glsl */ `
    uniform float uZ, uHalf, uSpring, uDrum, uWin, uOuter;
    varying vec3 vW;
    void main() {
      vec2 d = vec2(vW.x, vW.z - uZ);
      // Inside the square crossing above the springing: pendentives, tondi, drum, dome. The arches'
      // faces and soffits sit on or outside the square's edge, so they stay out.
      bool square = vW.y > uSpring + 0.05 && abs(d.x) < uHalf - 0.03 && abs(d.y) < uHalf - 0.03;
      // The drum's inner wall, which touches the square's edges on the axes.
      bool wall = vW.y > uDrum - 0.05 && length(d) < uHalf + 0.03;
      // From the windows up, within the drum's outer wall: window reveals, the plugs, the dome.
      bool drum = vW.y > uWin - 0.3 && length(d) < uOuter + 0.15;
      gl_FragColor = (square || wall || drum) ? vec4(1.0) : vec4(0.0, 0.0, 0.0, 1.0);
    }`,
});
const crop = new THREE.Matrix4();
const clear = new THREE.Color();
const targets = new Map<string, THREE.WebGLRenderTarget>();

/** The invisible plugs behind the windows and above the oculus; returns the cleanup. */
export function attachDomePicking(gl: THREE.WebGLRenderer, sc: THREE.Scene) {
  renderer = gl;
  scene = sc;
  const material = new THREE.MeshBasicMaterial();
  // Just outside the drum's outer face, over the window band, facing the axis.
  const ring = new THREE.CylinderGeometry(DOME.outer + 0.05, DOME.outer + 0.05,
    DOME.windows[1] - DOME.windows[0] + 0.3, 48, 1, true);
  ring.scale(-1, 1, 1); // flip the winding so the faces look inwards
  const plugs = new THREE.Group();
  const wall = new THREE.Mesh(ring, material);
  wall.position.set(0, (DOME.windows[0] + DOME.windows[1]) / 2, DOME.z);
  const cap = new THREE.Mesh(new THREE.CircleGeometry(DOME.oculus + 0.6, 32), material);
  cap.rotation.x = Math.PI / 2; // facing down
  cap.position.set(0, DOME.crown + 0.6, DOME.z);
  for (const m of [wall, cap]) {
    m.layers.set(PICK_LAYER);
    plugs.add(m);
  }
  plugs.name = "dome-pick-plugs";
  sc.add(plugs);
  return () => {
    sc.remove(plugs);
    ring.dispose();
    cap.geometry.dispose();
    material.dispose();
    renderer = scene = null;
  };
}

/** Draw the screen rectangle centred on (x, y) client px, (halfW, halfH) CSS px each way, at
 * nx x ny texels, and read it back without stalling the page (the GPU answers a frame or two
 * later). Resolves to the marked texels, row 0 at the bottom, or null if the scene is gone. */
async function drawPatch(x: number, y: number, halfW: number, halfH: number, nx: number, ny: number, el: HTMLElement) {
  const cam = rig.camera;
  const gl = renderer;
  const sc = scene;
  if (!cam || !gl || !sc) return null;
  const key = `${nx}x${ny}`;
  let target = targets.get(key);
  if (!target) targets.set(key, (target = new THREE.WebGLRenderTarget(nx, ny, { depthBuffer: true })));
  const box = el.getBoundingClientRect();
  const cx = ((x - box.left) / box.width) * 2 - 1;
  const cy = 1 - ((y - box.top) / box.height) * 2;
  const hx = (halfW / box.width) * 2;
  const hy = (halfH / box.height) * 2;
  // Crop the camera's projection to the patch (works for the shift lens too).
  crop.set(1 / hx, 0, 0, -cx / hx, 0, 1 / hy, 0, -cy / hy, 0, 0, 1, 0, 0, 0, 0, 1);
  pickCam.projectionMatrix.multiplyMatrices(crop, cam.projectionMatrix);
  pickCam.projectionMatrixInverse.copy(pickCam.projectionMatrix).invert();
  pickCam.matrixWorld.copy(cam.matrixWorld);
  pickCam.matrixWorldInverse.copy(cam.matrixWorldInverse);

  const prevTarget = gl.getRenderTarget();
  const prevAlpha = gl.getClearAlpha();
  gl.getClearColor(clear);
  const bg = sc.background;
  try {
    sc.background = null;
    sc.overrideMaterial = mark;
    gl.setRenderTarget(target);
    gl.setClearColor(0x000000, 0);
    gl.clear();
    gl.render(sc, pickCam);
  } finally {
    sc.overrideMaterial = null;
    sc.background = bg;
    gl.setRenderTarget(prevTarget);
    gl.setClearColor(clear, prevAlpha);
  }
  return gl.readRenderTargetPixelsAsync(target, 0, 0, nx, ny, new Uint8Array(nx * ny * 4));
}

const walking = () => getState().mode === "walk" && rig.drive === "scroll";

/** Is the dome on screen at (x, y), or within `radius` CSS px of it? False unless walking. */
export async function domeAt(x: number, y: number, el: HTMLElement, radius = PICK_RADIUS_PX) {
  if (!walking()) return false;
  const n = PICK_TEXELS;
  const px = await drawPatch(x, y, Math.max(radius, 1), Math.max(radius, 1), n, n, el);
  if (!px) return false;
  for (let j = 0; j < n; j++) {
    for (let i = 0; i < n; i++) {
      const u = ((i + 0.5) / n) * 2 - 1;
      const v = ((j + 0.5) / n) * 2 - 1;
      if (u * u + v * v <= 1 && px[(j * n + i) * 4] > 127) return true;
    }
  }
  return false;
}

/** A tap that missed the paintings: look up if it was on the dome. */
export function tapDome(x: number, y: number, el: HTMLElement) {
  domeAt(x, y, el).then((hit) => hit && lookUp(), () => {});
}

let hoverId = 0;
/** Mouse hover: the pointer cursor over the dome (skip: a painting already has the pointer). */
export function hoverDome(x: number, y: number, el: HTMLElement, skip: boolean) {
  const id = ++hoverId;
  if (skip) return;
  domeAt(x, y, el).then((hit) => {
    if (id === hoverId) el.style.cursor = hit ? "pointer" : "";
  }, () => {});
}

// ---------------------------------------------------------------------------- the look up

let tl: gsap.core.Timeline | gsap.core.Tween | null = null;

/** Walk to the centre of the crossing along the walk and tilt up until looking straight up.
 * The tilt follows the dome while walking (the gaze is aimed at the oculus, more so as it goes),
 * so it stays on screen. The shift lens blends out with the tilt: straight up, the frustum is
 * centred and the dome is round and in the middle. */
export function lookUp(opts: { push?: boolean } = {}) {
  if (getState().mode !== "walk" || rig.drive !== "scroll" || !rig.camera) return;
  setState({ mode: "looking-up", started: true });
  if (opts.push !== false) history.pushState({ dome: true }, "", "#dome");

  const from = { ...rig.pose, pitch: rig.pose.pitch ?? 0 };
  const z0 = from.z;
  rig.drive = "manual";
  rig.pose = { ...from };
  const go = { walk: 0, gaze: 0 };
  const update = () => {
    const z = z0 + (DOME.z - z0) * go.walk;
    const p = poseAt(progressAt(z));
    // Elevation of the oculus from here: 90 degrees once under it.
    const aim = Math.atan2(DOME.crown - p.y, Math.abs(z - DOME.z));
    rig.pose.x = p.x;
    rig.pose.y = p.y;
    rig.pose.z = z;
    rig.pose.yaw = 0;
    rig.pose.pitch = from.pitch + (aim - from.pitch) * go.gaze;
    rig.pose.sym = from.sym + (1 - from.sym) * go.gaze;
  };
  const t = gsap.timeline({ onUpdate: update, onComplete: () => {
    update();
    if (getState().mode === "looking-up") setState({ mode: "dome" });
  } });
  // Same family and pace as the walk-up to a painting (1.3 s, power2.inOut); the gaze starts a
  // moment later and settles a moment after arriving.
  t.to(go, { walk: 1, duration: dur(1.3), ease: "power2.inOut" }, 0);
  t.to(go, { gaze: 1, duration: dur(1.35), ease: "power2.inOut" }, dur(0.15));
  tl = t;
}

/** Tilt back down to the walk's view where the visitor stands, then hand back to the walk. */
export function lookDown(opts: { pop?: boolean } = {}) {
  const mode = getState().mode;
  if (mode !== "looking-up" && mode !== "dome") return;
  tl?.kill();
  setState({ mode: "looking-down" });
  if (!opts.pop && location.hash === "#dome") history.back();
  const prog = progressAt(rig.pose.z);
  const back = { ...poseAt(prog), pitch: 0 };
  tl = gsap.to(rig.pose, {
    ...back, duration: dur(1.2), ease: "power2.inOut",
    onComplete: () => {
      rig.progress = rig.target = prog;
      rig.drive = "scroll";
      setState({ mode: "walk" });
    },
  });
}

/** Escape and the browser's back button; a reload on #dome starts on the plain walk. */
export function attachDomeKeys() {
  if (location.hash === "#dome") history.replaceState(null, "", location.pathname + location.search);
  const onKey = (e: KeyboardEvent) => {
    if (e.key === "Escape") lookDown();
  };
  const onPop = () => {
    if (location.hash !== "#dome") lookDown({ pop: true });
  };
  window.addEventListener("keydown", onKey);
  window.addEventListener("popstate", onPop);
  return () => {
    window.removeEventListener("keydown", onKey);
    window.removeEventListener("popstate", onPop);
  };
}

if (import.meta.env.DEV) {
  // Test hook (dev only): scripted checks of the picking and the look up.
  (window as unknown as Record<string, unknown>).__dome = {
    DOME, domeAt, lookUp, lookDown, PICK_RADIUS_PX,
    get tl() { return tl; },
    /** The exact dome mask of the whole screen, one texel per `step` CSS px: [x, y] centres. */
    async mask(step: number) {
      const el = document.querySelector(".stage") as HTMLElement;
      const W = el.clientWidth, H = el.clientHeight;
      const nx = Math.round(W / step), ny = Math.round(H / step);
      const px = await drawPatch(W / 2, H / 2, W / 2, H / 2, nx, ny, el);
      const pts: [number, number][] = [];
      for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++)
        if (px && px[(j * nx + i) * 4] > 127) pts.push([(i + 0.5) * step, H - (j + 0.5) * step]);
      return pts;
    },
  };
}
