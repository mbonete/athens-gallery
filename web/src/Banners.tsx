import { useFrame, useLoader, useThree } from "@react-three/fiber";
import { useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { PAINTINGS } from "./paintings";
import { rig } from "./rig";
import { useStore } from "./store";
import { bannerUniforms, baseGeometry, litBanner, measureLight, shadowDecals, type Metal } from "./bannerLight";
import { PaintingTextureLoader } from "./paintingTexture";

/** The exhibition's banners (Maria, 2026-11-21: exhibition banners at the entrance, as in
 * museums; then "move the banners closer to the user, next to the first step of stairs
 * (downstairs)"): on the lower floor just past the entrance arch, one each side, in front of the
 * first step. They carry what the bottom banner carried: the title, the line and the note on the
 * left, how to visit on the right, each under a detail of one of the nine paintings (Klimt's gold,
 * Hokusai's wave). They stand on a low bronze base, facing the entrance. From the start they are
 * seen whole through the arch, outside the first bay's paintings and clear of the axis (the far
 * door, the Bosch). A click or a tap walks up to one to read it (banner.ts).
 * Maria, 2026-11-22: "more realistic ... its foot has a 2D feeling, no shadows or dimensions". Each
 * is built as an object: a cloth 3 mm thick whose foot goes down into a slot in a cast bronze base
 * with rounded edges, and whose hem wraps a gilt rod with ball ends. It takes the bake's sun and
 * sky face by face and casts its shadow and occlusion on the floor and the steps (bannerLight.ts). */
const TOUCH = typeof matchMedia !== "undefined" && matchMedia("(pointer: coarse)").matches;
const W = 0.85; // metres (web): the cloth
const H = 2.1;
const PX = 1000; // canvas px per metre
// From the start (eye at z 0), x / |z| of the cloth's edges is 0.40 to 0.58: outside the first
// bay's paintings (0.29 to 0.34) and inside the arch, whose jamb is at 0.70 and whose curve
// clears the cloth's top corners.
const X = 2.25; // centre of each banner from the axis
const Z = -4.6; // on the lower floor; the base's back edge is 8 cm before the first step (z -4.80)
const BASE_H = 0.09; // the stand's base under the cloth
const GROUND = "#24201c";
const CREAM = "#f4f1ea";
const MUTED = "#b9b1a3";
const FACE = "Cardo, Georgia, 'Times New Roman', serif";
const FONTS = ["150px Cardo", "italic 46px Cardo", "46px Cardo", "34px Cardo", "italic 26px Cardo"];

type Detail = { slug: string; crop: [number, number, number, number] }; // x, y, w, h in texture px
const LEFT: Detail = { slug: "klimt-water-serpents-ii", crop: [980, 0, 770, 1132] };
const RIGHT: Detail = { slug: "hokusai-great-wave", crop: [120, 0, 936, 1377] };

function wrap(g: CanvasRenderingContext2D, text: string, x: number, y: number, max: number, lh: number) {
  let line = "";
  for (const word of text.split(" ")) {
    const test = line ? `${line} ${word}` : word;
    if (g.measureText(test).width > max && line) {
      g.fillText(line, x, y);
      line = word;
      y += lh;
    } else line = test;
  }
  g.fillText(line, x, y);
  return y + lh;
}

/** A banner's canvas: the painting detail on top, the words below on a dark ground. */
function drawBanner(g: CanvasRenderingContext2D, img: ImageBitmap, d: Detail, side: "left" | "right") {
  const cw = W * PX;
  const ch = H * PX;
  const pad = 70;
  g.fillStyle = GROUND;
  g.fillRect(0, 0, cw, ch);
  const [sx, sy, sw, sh] = d.crop;
  const iw = cw - 2 * pad;
  const ih = Math.round((iw * sh) / sw);
  // The bitmap's rows run bottom-up (PaintingTextureLoader): take the crop from there and draw it
  // flipped back.
  g.save();
  g.setTransform(1, 0, 0, -1, 0, 2 * pad + ih);
  g.drawImage(img, sx, img.height - sy - sh, sw, sh, pad, pad, iw, ih);
  g.restore();
  const p = PAINTINGS.find((q) => q.slug === d.slug)!;
  g.fillStyle = MUTED;
  g.font = `italic 26px ${FACE}`;
  let y = wrap(g, `${p.artist}, ${p.title}, ${p.date} (detail)`, pad, pad + ih + 44, iw, 32);
  g.fillStyle = CREAM;
  if (side === "left") {
    g.font = `150px ${FACE}`;
    y += 130;
    g.fillText("Studiolo", pad - 6, y);
    y += 80;
    g.font = `46px ${FACE}`;
    y = wrap(g, "Nine favourite paintings, chosen by Maria Bonete, hung in the architecture of Raphael’s", pad, y, iw, 60);
    g.font = `italic 46px ${FACE}`;
    g.fillText("School of Athens.", pad, y);
    y += 80;
    g.fillStyle = MUTED;
    g.font = `34px ${FACE}`;
    wrap(g, "The hall is rebuilt in 3D from the fresco (Vatican, 1509–1511). Each painting hangs at its true size.", pad, y, iw, 46);
  } else {
    g.font = `92px ${FACE}`;
    y += 110;
    g.fillText("How to visit", pad - 3, y);
    y += 90;
    const how: [string, string][] = TOUCH
      ? [["Walk", "Spread two fingers; pinch to walk back"], ["A painting", "Tap it to walk up; pinch to zoom"], ["The dome", "Tap it to look up"]]
      : [["Walk", "Scroll, or pinch on a trackpad"], ["A painting", "Click it to walk up, again to zoom; drag to look around"],
         ["The dome", "Click it to look up"], ["Keys", "Arrows to walk; Tab and Enter open a painting"]];
    for (const [k, v] of how) {
      g.fillStyle = MUTED;
      g.font = `34px ${FACE}`;
      g.fillText(k, pad, y);
      g.fillStyle = CREAM;
      g.font = `40px ${FACE}`;
      y = wrap(g, v, pad, y + 50, iw, 50) + 22;
    }
  }
}

function useBannerTexture(d: Detail, side: "left" | "right") {
  const p = PAINTINGS.find((q) => q.slug === d.slug)!;
  const gl = useThree((s) => s.gl);
  const art = useLoader(PaintingTextureLoader, p.texture, (l) => void (l.renderer = gl));
  return useMemo(() => {
    const c = document.createElement("canvas");
    c.width = W * PX;
    c.height = H * PX;
    const g = c.getContext("2d")!;
    const t = new THREE.CanvasTexture(c);
    t.colorSpace = THREE.SRGBColorSpace;
    t.anisotropy = 8;
    const draw = () => {
      drawBanner(g, art.image as ImageBitmap, d, side);
      t.needsUpdate = true;
      rig.kick();
    };
    draw();
    // A canvas can't wait for a web font: draw again once Cardo is in.
    Promise.all(FONTS.map((f) => document.fonts.load(f))).then(draw, () => {});
    return t;
  }, [art, d, side]);
}

const T = 0.003; // the cloth's thickness
const BASE_W = W + 0.08;
const BASE_D = 0.24;
const SLOT = 0.012; // the slot's width under its rounded lips
const FOOT = 0.08; // how far the cloth goes down into the base
const R_SLEEVE = 0.0135; // the cloth's hem, wrapped round the rod
const R_ROD = 0.0075;
const R_KNOB = 0.013;
const Y_ROD = BASE_H + H - 0.002;
// Albedos (sRGB); the light is the bake's (bannerLight.ts).
const BRONZE = "#3b2e22"; // patinated bronze: dark, with a warm reflection
const GILT = "#8e6e30";
const BRONZE_METAL: Metal = { f0: new THREE.Color(0.16, 0.105, 0.055), fresnel: 0.12, shine: 48 };
const GILT_METAL: Metal = { f0: new THREE.Color(0.5, 0.36, 0.12), fresnel: 0.3, shine: 30 };

function Banner({ side }: { side: "left" | "right" }) {
  const tex = useBannerTexture(side === "left" ? LEFT : RIGHT, side);
  const cloth = useRef<THREE.Mesh>(null!);
  const x = side === "left" ? -X : X;
  const light = useMemo(() => bannerUniforms(
    new THREE.Vector3(x, 0, Z), side,
    new THREE.Vector3(W / 2, BASE_H, Y_ROD + R_SLEEVE), new THREE.Vector3(BASE_W / 2, BASE_H, BASE_D / 2),
  ), [x, side]);
  const { mats, dims } = useMemo(() => {
    const mats = {
      front: new THREE.MeshBasicMaterial({ map: tex, toneMapped: false }),
      back: new THREE.MeshBasicMaterial({ color: GROUND, toneMapped: false }),
      bronze: new THREE.MeshBasicMaterial({ color: BRONZE, toneMapped: false }),
      gilt: new THREE.MeshBasicMaterial({ color: GILT, toneMapped: false }),
    };
    const dims = [
      litBanner(mats.front, light, "cloth", undefined, SLOT / 2),
      litBanner(mats.back, light, "cloth", undefined, SLOT / 2),
      litBanner(mats.bronze, light, "bronze", BRONZE_METAL, SLOT / 2),
      litBanner(mats.gilt, light, "gilt", GILT_METAL),
    ].map((u) => u.bnDim);
    return { mats, dims };
  }, [tex, light]);
  useEffect(() => () => Object.values(mats).forEach((m) => m.dispose()), [mats]);
  const geo = useMemo(() => ({
    cloth: new THREE.BoxGeometry(W, H, T),
    foot: new THREE.BoxGeometry(W, FOOT, T * 0.9),
    sleeve: new THREE.CylinderGeometry(R_SLEEVE, R_SLEEVE, W, 32).rotateZ(Math.PI / 2),
    rod: new THREE.CylinderGeometry(R_ROD, R_ROD, W + 0.04, 16).rotateZ(Math.PI / 2),
    knob: new THREE.SphereGeometry(R_KNOB, 20, 14),
    base: baseGeometry(BASE_W, BASE_H, BASE_D, W + 0.01, SLOT),
  }), []);
  useEffect(() => () => Object.values(geo).forEach((g) => g.dispose()), [geo]);
  useEffect(() => {
    cloth.current.userData = { w: W, h: H };
    rig.banners.set(side, cloth.current);
    return () => void rig.banners.delete(side);
  }, [side]);
  // Its shadow and occlusion on the hall, once the hall's lightmaps are on (Scene.tsx). The region
  // holds the cloth's shadow (the sun is low and to the right: its top lands 2.5 m to the left and
  // 0.9 m back, on the second tread) and the occlusion round the base.
  const { gl, scene } = useThree();
  const ready = useStore((s) => s.ready);
  const [decals, setDecals] = useState<THREE.Mesh[]>([]);
  useEffect(() => {
    if (!ready) return;
    // The bake's light here, read from its lightmap (bannerLight.ts): it follows every rebake.
    const m = measureLight(gl, scene, light.bnAt.value, light.bnBase.value);
    if (m) {
      light.bnSky.value = m.sky;
      light.bnSunE.value = m.sun;
      rig.kick();
    }
    if (import.meta.env.DEV) ((window as unknown as { __bannerLight?: Record<string, unknown> }).__bannerLight ??= {})[side] = m;
    const region = new THREE.Box3(new THREE.Vector3(x - 3.45, -0.02, Z - 1.45), new THREE.Vector3(x + 0.85, 0.75, Z + 0.55));
    const made = shadowDecals(scene, region, light);
    setDecals(made);
    return () => made.forEach((m) => (m.geometry.dispose(), (m.material as THREE.Material).dispose()));
  }, [ready, gl, scene, light, x, side]);
  const base = useMemo(() => Object.values(mats).map((m) => [m, m.color.clone()] as const), [mats]);
  useFrame(() => {
    // Dim with the hall around an open painting: copy the base colours and scale them, like the
    // hall's own materials (the metals' reflections too).
    for (const [m, c] of base) m.color.copy(c).multiplyScalar(rig.light);
    for (const d of dims) d.value = rig.light;
  });
  // Box faces: +x, -x, +y, -y, +z (the canvas), -z.
  const clothMats = [mats.back, mats.back, mats.back, mats.back, mats.front, mats.back];
  return (
    <>
      <group position={[x, 0, Z]}>
        <mesh ref={cloth} position={[0, BASE_H + H / 2, 0]} geometry={geo.cloth} material={clothMats} />
        <mesh position={[0, BASE_H - FOOT / 2, 0]} geometry={geo.foot} material={mats.back} />
        <mesh position={[0, Y_ROD, 0]} geometry={geo.sleeve} material={mats.back} />
        <mesh position={[0, Y_ROD, 0]} geometry={geo.rod} material={mats.gilt} />
        {[-1, 1].map((s) => (
          <mesh key={s} position={[s * (W / 2 + 0.028), Y_ROD, 0]} geometry={geo.knob} material={mats.gilt} />
        ))}
        <mesh geometry={geo.base} material={mats.bronze} />
      </group>
      {decals.map((m) => <primitive key={m.uuid} object={m} />)}
    </>
  );
}

export function Banners() {
  return (
    <>
      <Banner side="left" />
      <Banner side="right" />
    </>
  );
}
