import { useFrame, useLoader, useThree } from "@react-three/fiber";
import { useEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { KTX2Loader } from "three/examples/jsm/loaders/KTX2Loader.js";
import { MeshoptDecoder } from "three/examples/jsm/libs/meshopt_decoder.module.js";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";
import hall from "./data/hall.json";
import { displayH, displayW, type Painting } from "./paintings";
import { rig } from "./rig";
import { ShiftCamera } from "./ShiftCamera";
import { getState, setState } from "./store";
import { glide } from "./input";
import { DomePicking } from "./DomeControls";
import { frustumFor, poseAt, progressNear, SHIFT_X, STATIONS, TOTAL } from "./walk";

// The fresco's sky, as seen through the far door and the drum (sRGB 175, 175, 245).
const SKY = new THREE.Color().setRGB(175 / 255, 175 / 255, 245 / 255, THREE.SRGBColorSpace);
const SKY_DIM = new THREE.Color("#2a2826");

export function Scene() {
  const { gl, scene, set, size } = useThree();
  const camera = useMemo(() => new ShiftCamera(), []);
  const hemi = useRef<THREE.HemisphereLight>(null!);
  const sun = useRef<THREE.DirectionalLight>(null!);
  const sunTarget = useMemo(() => {
    const o = new THREE.Object3D();
    o.position.set(0, 4, -20);
    return o;
  }, []);
  useEffect(() => {
    sun.current.target = sunTarget;
  }, [sunTarget]);

  useEffect(() => {
    if (import.meta.env.DEV) {
      // Test hook (dev only): where a painting is on screen, for scripted taps.
      (window as unknown as Record<string, unknown>).__gallery = {
        rig,
        STATIONS,
        TOTAL,
        progressNear,
        getState,
        screenOf(slug: string) {
          const m = rig.paintingMeshes.get(slug);
          if (!m) return null;
          const p = m.getWorldPosition(new THREE.Vector3()).project(camera);
          const r = gl.domElement.getBoundingClientRect();
          return { x: r.left + ((p.x + 1) / 2) * r.width, y: r.top + ((1 - p.y) / 2) * r.height, z: p.z };
        },
      };
    }
    rig.camera = camera;
    set({ camera });
    const pmrem = new THREE.PMREMGenerator(gl);
    scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
    scene.background = SKY.clone();
    return () => pmrem.dispose();
  }, [camera, gl, scene, set]);

  useEffect(() => {
    camera.aspect = size.width / size.height;
  }, [camera, size]);

  useFrame((_, dt) => {
    glide(Math.min(dt, 0.1));
    const pose = rig.drive === "scroll" ? poseAt(rig.progress) : rig.pose;
    if (rig.drive === "scroll") rig.pose = { ...pose };
    camera.position.set(pose.x, pose.y, pose.z);
    camera.rotation.set(pose.pitch ?? 0, pose.yaw, 0, "YXZ");
    const f = frustumFor(camera.aspect);
    const mid = (f.up + f.down) / 2;
    camera.tanUp = f.up + (mid - f.up) * pose.sym;
    camera.tanDown = f.down + (mid - f.down) * pose.sym;
    camera.shiftX = SHIFT_X * (1 - pose.sym);
    camera.updateProjectionMatrix();
    // Hall light (the paintings are unlit, so they keep their colours while it dims).
    hemi.current.intensity = 0.9 * rig.light;
    sun.current.intensity = 2.8 * rig.light;
    scene.environmentIntensity = 0.35 * rig.light;
    (scene.background as THREE.Color).copy(SKY_DIM).lerp(SKY, rig.light);
  });

  return (
    <>
      <hemisphereLight ref={hemi} args={["#e6edf6", "#8f8576", 1.6]} />
      {/* Lights only for the frames and the doorway's base: the hall itself is baked. */}
      <directionalLight ref={sun} position={[-27, 46, 13]} intensity={1.8} />
      <primitive object={sunTarget} />
      <Hall />
      <DomePicking />
      {STATIONS.map((st) => (
        <HungPainting key={st.painting.slug} painting={st.painting} side={st.side} z={st.z} wallX={st.wallX} room={st.room} />
      ))}
    </>
  );
}

/** The hall, baked in Blender (tools/bake_hall.sh). Each surface is a seamless detail tile
 * (TEXCOORD_0, world-scaled, repeat) times its tint times its lightmap (TEXCOORD_1), drawn
 * unlit: the lightmap holds Cycles' light (and Raphael's shade conventions) as light /
 * lightScale. MeshBasicMaterial multiplies the lightmap by lightMapIntensity / PI. Dimming
 * around a painting scales the tint. */
const hallMaterials: { mat: THREE.MeshBasicMaterial; base: THREE.Color }[] = [];

function Hall() {
  const { gl } = useThree();
  const gltf = useLoader(GLTFLoader, "/models/hall.glb", (loader) => {
    const ktx2 = new KTX2Loader().setTranscoderPath("/basis/").detectSupport(gl);
    loader.setKTX2Loader(ktx2);
    loader.setMeshoptDecoder(MeshoptDecoder);
  });
  useEffect(() => {
    hallMaterials.length = 0;
    const aniso = Math.min(8, gl.capabilities.getMaxAnisotropy());
    gltf.scene.traverse((o) => {
      const mesh = o as THREE.Mesh;
      if (!mesh.isMesh) return;
      const old = mesh.material as THREE.MeshStandardMaterial;
      const map = old.map ?? null;
      const light = old.aoMap ?? null;
      if (map) {
        map.colorSpace = THREE.SRGBColorSpace;
        map.wrapS = map.wrapT = THREE.RepeatWrapping;
        map.anisotropy = aniso;
        map.needsUpdate = true;
      }
      if (light) {
        light.colorSpace = THREE.SRGBColorSpace;
        light.channel = 1;
        light.needsUpdate = true;
      }
      const mat = new THREE.MeshBasicMaterial({
        map,
        lightMap: light,
        lightMapIntensity: (hall.lightScale ?? 1) * Math.PI,
        color: old.color,
        toneMapped: false,
      });
      mesh.material = mat;
      old.dispose();
      hallMaterials.push({ mat, base: mat.color.clone() });
      mesh.castShadow = false;
      mesh.receiveShadow = false;
    });
    setState({ ready: true });
  }, [gltf, gl]);
  useFrame(() => {
    for (const { mat, base } of hallMaterials) mat.color.copy(base).multiplyScalar(rig.light);
  });
  return <primitive object={gltf.scene} />;
}

/** A painting at true size with a thin frame and a museum label: on a side wall (side ±1),
 * or standing on a low base in the far doorway, facing the walk (side 0). */
function HungPainting({ painting, side, z, wallX, room }: {
  painting: Painting; side: number; z: number; wallX: number; room: number;
}) {
  const tex = useLoader(THREE.TextureLoader, painting.texture);
  const { gl } = useThree();
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = gl.capabilities.getMaxAnisotropy();
  const w = displayW(painting);
  const h = displayH(painting);
  const floor = hall.floor[hall.floor.length - 1][1];
  const inDoor = side === 0;
  const BASE = 0.75; // the doorway piece stands on a base this high
  const cy = inDoor ? floor + BASE + h / 2 : floor + 1.55; // wall pieces: centre 1.55 m above the floor
  const x = inDoor ? 0 : side * (wallX - 0.03);
  const rotY = inDoor ? 0 : side < 0 ? Math.PI / 2 : -Math.PI / 2;
  const frame = 0.06;
  const label = useMemo(() => labelTexture(painting), [painting]);
  // Label: on the base's front face for the doorway piece; beside a wall piece when it fits
  // in the bay (5 cm clear of the pilaster), otherwise under its bottom-right corner.
  const besideFits = w / 2 + 0.47 <= room / 2 - 0.05;
  const labelPos: [number, number, number] = inDoor
    ? [w / 2 - 0.25, -h / 2 - BASE / 2, 0.2 + 0.005]
    : besideFits
      ? [w / 2 + 0.32, -0.12, 0.005]
      : [w / 2 + frame - 0.15, -h / 2 - frame - 0.14, 0.005];

  const ref = useRef<THREE.Group>(null!);
  const plaque = useRef<THREE.Mesh>(null!);
  const art = useRef<THREE.Mesh>(null!);
  useEffect(() => {
    // Picking is done on screen (pick.ts): it needs the sizes of the painting and its frame.
    art.current.userData = { w: w + 2 * frame, h: h + 2 * frame };
    rig.paintingMeshes.set(painting.slug, art.current);
    rig.plaques.set(painting.slug, plaque.current);
  }, [painting.slug, w, h]);
  return (
    // Facing into the hall: the left wall's pieces face +x, the right wall's -x, the doorway piece +z.
    <group ref={ref} position={[x, cy, z]} rotation={[0, rotY, 0]}>
      <mesh ref={art}>
        <planeGeometry args={[w, h]} />
        <meshBasicMaterial map={tex} toneMapped={false} />
      </mesh>
      {/* The doorway piece's stone base is part of the baked hall (params.BOSCH_BASE). */}
      {[
        [0, h / 2 + frame / 2, w + 2 * frame, frame],
        [0, -h / 2 - frame / 2, w + 2 * frame, frame],
        [-w / 2 - frame / 2, 0, frame, h],
        [w / 2 + frame / 2, 0, frame, h],
      ].map(([fx, fy, fw, fh], i) => (
        <mesh key={i} position={[fx, fy, 0.02]}>
          <boxGeometry args={[fw, fh, 0.04]} />
          <meshStandardMaterial color="#5a4630" roughness={0.6} />
        </mesh>
      ))}
      <mesh ref={plaque} position={labelPos}>
        <planeGeometry args={[0.3, 0.2]} />
        <meshBasicMaterial map={label} toneMapped={false} transparent />
      </mesh>
    </group>
  );
}

/** The wall label, drawn on a canvas (crisp under any camera projection). */
function labelTexture(p: Painting) {
  const c = document.createElement("canvas");
  c.width = 600;
  c.height = 400;
  const g = c.getContext("2d")!;
  g.fillStyle = "#f4f1ea";
  g.fillRect(0, 0, 600, 400);
  g.fillStyle = "#2a2724";
  g.font = "italic 38px Georgia, 'Times New Roman', serif";
  wrap(g, p.title, 36, 74, 528, 44);
  g.font = "28px Georgia, 'Times New Roman', serif";
  g.fillText(`${p.artist}, ${p.date}`, 36, 250);
  g.font = "22px Georgia, 'Times New Roman', serif";
  g.fillStyle = "#6b655d";
  g.fillText(`${p.medium}, ${p.dimensions}`, 36, 300);
  g.fillText("Tap to look closer", 36, 356);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 8;
  return t;
}

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
}
