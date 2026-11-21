import { useFrame, useLoader } from "@react-three/fiber";
import { useEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import hall from "./data/hall.json";
import { PAINTINGS } from "./paintings";
import { rig } from "./rig";

/** The exhibition's banners (Maria, 2026-11-21: exhibition banners at the entrance, as in
 * museums; now standing on the upper floor at the top of the steps, one each side). They carry
 * what the bottom banner carried: the title, the line and the note on the left, how to visit on
 * the right, each under a detail of one of the nine paintings (Klimt's gold, Hokusai's wave).
 * They stand on a low bronze base, facing the entrance, clear of the axis (the far door, the
 * Bosch) and of the first bay's paintings as seen from the start. A click or a tap walks up to
 * one to read it (banner.ts). */
export const BANNERS = new URLSearchParams(window.location.search).get("intro") !== "bottom";

const TOUCH = typeof matchMedia !== "undefined" && matchMedia("(pointer: coarse)").matches;
const W = 0.85; // metres (web): a roll-up banner's cloth
const H = 2.1;
const PX = 1000; // canvas px per metre
const X = 3.0; // centre of each banner from the axis
const Z = -8.0; // on the upper floor, 1.75 m past the top step
const FLOOR = hall.floor[hall.floor.length - 1][1]; // the upper floor's height
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
function drawBanner(g: CanvasRenderingContext2D, img: HTMLImageElement, d: Detail, side: "left" | "right") {
  const cw = W * PX;
  const ch = H * PX;
  const pad = 70;
  g.fillStyle = GROUND;
  g.fillRect(0, 0, cw, ch);
  const [sx, sy, sw, sh] = d.crop;
  const iw = cw - 2 * pad;
  const ih = Math.round((iw * sh) / sw);
  g.drawImage(img, sx, sy, sw, sh, pad, pad, iw, ih);
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
  const art = useLoader(THREE.TextureLoader, p.texture);
  return useMemo(() => {
    const c = document.createElement("canvas");
    c.width = W * PX;
    c.height = H * PX;
    const g = c.getContext("2d")!;
    const t = new THREE.CanvasTexture(c);
    t.colorSpace = THREE.SRGBColorSpace;
    t.anisotropy = 8;
    const draw = () => {
      drawBanner(g, art.image as HTMLImageElement, d, side);
      t.needsUpdate = true;
    };
    draw();
    // A canvas can't wait for a web font: draw again once Cardo is in.
    Promise.all(FONTS.map((f) => document.fonts.load(f))).then(draw, () => {});
    return t;
  }, [art, d, side]);
}

function Banner({ side }: { side: "left" | "right" }) {
  const tex = useBannerTexture(side === "left" ? LEFT : RIGHT, side);
  const cloth = useRef<THREE.Mesh>(null!);
  const mats = useMemo(() => ({
    cloth: new THREE.MeshBasicMaterial({ map: tex, toneMapped: false }),
    gold: new THREE.MeshBasicMaterial({ color: "#a8823a", toneMapped: false }),
    bronze: new THREE.MeshBasicMaterial({ color: "#4a3e30", toneMapped: false }),
  }), [tex]);
  useEffect(() => () => Object.values(mats).forEach((m) => m.dispose()), [mats]);
  useEffect(() => {
    cloth.current.userData = { w: W, h: H };
    rig.banners.set(side, cloth.current);
    return () => void rig.banners.delete(side);
  }, [side]);
  const base = useMemo(() => Object.values(mats).map((m) => [m, m.color.clone()] as const), [mats]);
  useFrame(() => {
    // Dim with the hall around an open painting, like the hall's own materials.
    for (const [m, c] of base) m.color.copy(c).multiplyScalar(rig.light);
  });
  const x = side === "left" ? -X : X;
  const yc = FLOOR + BASE_H + H / 2;
  return (
    <group position={[x, yc, Z]}>
      <mesh ref={cloth} material={mats.cloth}>
        <planeGeometry args={[W, H]} />
      </mesh>
      <mesh position={[0, H / 2 + 0.012, 0.012]} rotation={[0, 0, Math.PI / 2]} material={mats.gold}>
        <cylinderGeometry args={[0.014, 0.014, W + 0.04, 12]} />
      </mesh>
      <mesh position={[0, -H / 2 - BASE_H / 2, 0]} material={mats.bronze}>
        <boxGeometry args={[W + 0.08, BASE_H, 0.24]} />
      </mesh>
    </group>
  );
}

export function Banners() {
  if (!BANNERS) return null;
  return (
    <>
      <Banner side="left" />
      <Banner side="right" />
    </>
  );
}
