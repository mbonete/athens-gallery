import { useFrame, useLoader, useThree } from "@react-three/fiber";
import { useEffect, useLayoutEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { KTX2Loader } from "three/examples/jsm/loaders/KTX2Loader.js";
import { MeshoptDecoder } from "three/examples/jsm/libs/meshopt_decoder.module.js";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import { PaintingTextureLoader } from "./paintingTexture";
import hall from "./data/hall.json";
import { displayH, displayW, type Painting } from "./paintings";
import { moving, rig } from "./rig";
import { ShiftCamera } from "./ShiftCamera";
import { getState, setState } from "./store";
import { glide } from "./input";
import { looked } from "./look";
import { DomePicking } from "./DomeControls";
import { frustumFor, poseAt, progressNear, SHIFT_X, STATIONS, TOTAL } from "./walk";
import { Sky } from "./Sky";
import { Banners } from "./Banners";
import { GOLD_SHEEN, GOLD_SHININESS, SUN_DIR } from "./goldLeaf";

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
        /** What a screen pixel (CSS px) hits: every intersection along its ray, nearest first. */
        probe(x: number, y: number) {
          const r = gl.domElement.getBoundingClientRect();
          const ndc = new THREE.Vector2(((x - r.left) / r.width) * 2 - 1, -((y - r.top) / r.height) * 2 + 1);
          const ray = new THREE.Raycaster();
          ray.layers.enableAll();
          ray.setFromCamera(ndc, camera);
          return ray.intersectObjects(scene.children, true).slice(0, 4).map((h) => ({
            name: h.object.name, material: (h.object as THREE.Mesh).material && ((h.object as THREE.Mesh).material as THREE.Material).name,
            d: +h.distance.toFixed(4), p: h.point.toArray().map((v) => +v.toFixed(4)), face: h.face ? h.face.normal.toArray().map((v) => +v.toFixed(3)) : null,
            uv1: h.uv1 ? [+h.uv1.x.toFixed(5), +h.uv1.y.toFixed(5)] : null,
          }));
        },
      };
    }
    rig.camera = camera;
    set({ camera });
    const pmrem = new THREE.PMREMGenerator(gl);
    scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
    return () => pmrem.dispose();
  }, [camera, gl, scene, set]);

  useEffect(() => {
    camera.aspect = size.width / size.height;
    rig.kick();
  }, [camera, size]);

  const wasMoving = useRef(false);
  useFrame((_, dt) => {
    // After a rest, dt spans the whole rest: the glide starts with one frame's step.
    glide(Math.min(dt, wasMoving.current ? 0.1 : 1 / 60));
    const pose = rig.drive === "scroll" ? poseAt(rig.progress) : rig.pose;
    if (rig.drive === "scroll") rig.pose = { ...pose };
    camera.position.set(pose.x, pose.y, pose.z);
    // The visitor's turn (look.ts) on top of the pose; with none, the pose's own values.
    const f = frustumFor(camera.aspect);
    const view = looked(pose, f);
    camera.rotation.set(view.pitch, view.yaw, 0, "YXZ");
    const mid = (f.up + f.down) / 2;
    camera.tanUp = f.up + (mid - f.up) * view.sym;
    camera.tanDown = f.down + (mid - f.down) * view.sym;
    camera.shiftX = SHIFT_X * (1 - view.sym);
    camera.updateProjectionMatrix();
    // Hall light (the paintings are unlit, so they keep their colours while it dims).
    hemi.current.intensity = 0.9 * rig.light;
    sun.current.intensity = 2.8 * rig.light;
    scene.environmentIntensity = 0.35 * rig.light;
    // Demand rendering (App.tsx): the next frame while the view moves, and one more after it
    // stops, so the last frame drawn holds the end values.
    const now = moving();
    if (now || wasMoving.current) rig.kick();
    wasMoving.current = now;
  });

  return (
    <>
      <hemisphereLight ref={hemi} args={["#e6edf6", "#8f8576", 1.6]} />
      {/* Lights only for the frames and the doorway's base: the hall itself is baked. */}
      <directionalLight ref={sun} position={[-27, 46, 13]} intensity={1.8} />
      <primitive object={sunTarget} />
      <Sky />
      <Hall />
      <Banners />
      <GroundBeyond />
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

/** Lightmap lookup with a cubic B-spline filter (4 bilinear taps; Sigg & Hadwiger, GPU Gems 2,
 * ch. 20) instead of one bilinear tap: the light between texel centres is smooth, so edges that
 * cross the texel grid at an angle no longer read as one-texel steps. ?lmfilter=bilinear turns it
 * off (to compare frame times). */
const LM_BICUBIC = new URLSearchParams(window.location.search).get("lmfilter") !== "bilinear";
const LM_BICUBIC_GLSL = /* glsl */ `
vec4 lmCubicWeights(float v) {
  vec4 n = vec4(1.0, 2.0, 3.0, 4.0) - v;
  vec4 s = n * n * n;
  float x = s.x;
  float y = s.y - 4.0 * s.x;
  float z = s.z - 4.0 * s.y + 6.0 * s.x;
  return vec4(x, y, z, 6.0 - x - y - z) * (1.0 / 6.0);
}
vec4 lmBicubic(sampler2D tex, vec2 uv) {
  vec2 size = vec2(textureSize(tex, 0));
  vec2 px = uv * size - 0.5;
  vec2 f = fract(px);
  px -= f;
  vec4 xc = lmCubicWeights(f.x);
  vec4 yc = lmCubicWeights(f.y);
  vec4 c = px.xxyy + vec2(-0.5, 1.5).xyxy;
  vec4 s = vec4(xc.xz + xc.yw, yc.xz + yc.yw);
  vec4 o = (c + vec4(xc.yw, yc.yw) / s) / size.xxyy;
  vec4 s0 = texture2D(tex, o.xz), s1 = texture2D(tex, o.yz), s2 = texture2D(tex, o.xw), s3 = texture2D(tex, o.yw);
  float sx = s.x / (s.x + s.y), sy = s.z / (s.z + s.w);
  return mix(mix(s3, s2, sx), mix(s1, s0, sx), sy);
}
`;
function lightmapBicubic(mat: THREE.MeshBasicMaterial) {
  if (!LM_BICUBIC) return;
  mat.onBeforeCompile = (shader) => {
    shader.fragmentShader = shader.fragmentShader
      .replace("void main() {", `${LM_BICUBIC_GLSL}\nvoid main() {`)
      .replace("texture2D( lightMap, vLightMapUv )", "lmBicubic( lightMap, vLightMapUv )");
  };
  mat.customProgramCacheKey = () => "lm-bicubic";
}

/** The flat ground beyond the end door, seen through it (build.py's ground_beyond, hall.json):
 * drawn here rather than packed in the GLB, whose single quantization grid it would stretch to
 * 4.3 mm a step (bake.py). Flat and unlit, dimmed with the hall. */
function GroundBeyond() {
  const g = (hall as unknown as { groundBeyond?: { y: number; x: number[]; z: number[]; colour: number[] } }).groundBeyond;
  const base = useMemo(() => new THREE.Color().setRGB(...((g?.colour ?? [0.42, 0.42, 0.33]) as [number, number, number])), [g]);
  const mat = useMemo(() => new THREE.MeshBasicMaterial({ color: base.clone(), toneMapped: false }), [base]);
  useFrame(() => {
    mat.color.copy(base).multiplyScalar(rig.light);
  });
  if (!g) return null;
  const [x0, x1] = g.x;
  const [z0, z1] = g.z;
  return (
    <mesh position={[(x0 + x1) / 2, g.y, (z0 + z1) / 2]} rotation={[-Math.PI / 2, 0, 0]} material={mat}>
      <planeGeometry args={[x1 - x0, Math.abs(z1 - z0)]} />
    </mesh>
  );
}

/** The opening arch's gold leaf (Maria, round 10: clean, smooth, with a sheen). The band tile's
 * alpha marks the gold (tools/make_detail.py, params ARCH_GOLD). There the bake's sun adds a
 * soft view-dependent highlight: Blinn-Phong, pale gold, so the leaf brightens and warms where it
 * turns the sun towards the eye and changes as the visitor walks. The GLB carries no normals
 * (the hall is unlit), and the band is flat, so the normal comes from the position's derivatives.
 * The sun and the lobe: goldLeaf.ts. */
function goldLeaf(mat: THREE.MeshBasicMaterial) {
  const prev = mat.onBeforeCompile.bind(mat);
  mat.onBeforeCompile = (shader, renderer) => {
    prev(shader, renderer);
    shader.uniforms.goldSun = { value: SUN_DIR };
    shader.uniforms.goldSheen = { value: GOLD_SHEEN };
    shader.vertexShader = shader.vertexShader
      .replace("#include <common>", "#include <common>\nvarying vec3 vGoldP;")
      .replace("#include <begin_vertex>", "#include <begin_vertex>\nvGoldP = (modelMatrix * vec4(transformed, 1.0)).xyz;");
    shader.fragmentShader = shader.fragmentShader
      .replace(
        "#include <common>",
        "#include <common>\nuniform vec3 goldSun;\nuniform vec3 goldSheen;\nvarying vec3 vGoldP;",
      )
      .replace("#include <map_fragment>", "#include <map_fragment>\nfloat goldMask = sampledDiffuseColor.a;")
      .replace(
        "#include <opaque_fragment>",
        `{
  vec3 v = normalize(cameraPosition - vGoldP);
  vec3 n = normalize(cross(dFdx(vGoldP), dFdy(vGoldP)));
  n = dot(n, v) < 0.0 ? -n : n;
  float lobe = pow(max(dot(n, normalize(goldSun + v)), 0.0), ${GOLD_SHININESS.toFixed(1)});
  outgoingLight += goldMask * lobe * goldSheen * diffuse;
}
#include <opaque_fragment>`,
      );
  };
  mat.customProgramCacheKey = () => (LM_BICUBIC ? "lm-bicubic" : "lm") + "|gold-leaf";
}

/** Before the hall is first drawn: link every program the scene needs in the background
 * (KHR_parallel_shader_compile) and meanwhile upload the textures not on the GPU yet, so the first
 * frame waits for neither. The scene is hidden until then (Hall); compile() reads the lights of the
 * visible scene. */
async function warmUp(gl: THREE.WebGLRenderer, scene: THREE.Scene, camera: THREE.Camera) {
  scene.visible = true;
  const linked = gl.compileAsync(scene, camera);
  scene.visible = false;
  scene.traverse((o) => {
    const m = (o as THREE.Mesh).material;
    for (const mat of m ? [m].flat() : []) {
      const uniforms = Object.values((mat as THREE.ShaderMaterial).uniforms ?? {}).map((u) => u.value);
      for (const v of [...Object.values(mat), ...uniforms]) if (v instanceof THREE.Texture) gl.initTexture(v);
    }
  });
  await linked;
}

function Hall() {
  const { gl, scene, get } = useThree();
  const gltf = useLoader(GLTFLoader, "/models/hall.glb", (loader) => {
    const ktx2 = new KTX2Loader().setTranscoderPath("/basis/").detectSupport(gl);
    // Fetch the transcoder beside hall.glb, not once the GLB has arrived.
    ktx2.init().catch(() => {});
    loader.setKTX2Loader(ktx2);
    loader.setMeshoptDecoder(MeshoptDecoder);
  });
  // Hidden from this commit until warmUp is done, so no frame draws the hall before its materials,
  // the camera and the environment are set: the canvas stays as it was behind the loading line.
  useLayoutEffect(() => {
    scene.visible = false;
    return () => void (scene.visible = true);
  }, [scene]);
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
      lightmapBicubic(mat);
      // The gold leaf: the opening arch's bands and the vault ornament painted on the front wall
      // (detail tiles whose alpha marks the gold; no other wall carries the sheen).
      if (["arch_band", "vault_front"].includes(old.name.split("|")[1])) goldLeaf(mat);
      mesh.material = mat;
      old.dispose();
      hallMaterials.push({ mat, base: mat.color.clone() });
      mesh.castShadow = false;
      mesh.receiveShadow = false;
    });
    // After this commit's other effects: Scene's sets the camera and the environment the frames
    // reflect, which their programs depend on.
    let live = true;
    queueMicrotask(() => {
      if (!live) return;
      warmUp(gl, scene, rig.camera ?? get().camera).catch(() => {}).then(() => {
        if (!live) return;
        scene.visible = true;
        setState({ ready: true });
        rig.kick(); // the baked materials are on and compiled: draw them (frameloop "demand")
      });
    });
    return () => void (live = false);
  }, [gltf, gl, scene, get]);
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
  const { gl } = useThree();
  const tex = useLoader(PaintingTextureLoader, painting.texture, (l) => void (l.renderer = gl));
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
  // The frame's four sides as one geometry: one draw call instead of four.
  const frameGeo = useMemo(() => mergeGeometries([
    [0, h / 2 + frame / 2, w + 2 * frame, frame],
    [0, -h / 2 - frame / 2, w + 2 * frame, frame],
    [-w / 2 - frame / 2, 0, frame, h],
    [w / 2 + frame / 2, 0, frame, h],
  ].map(([fx, fy, fw, fh]) => new THREE.BoxGeometry(fw, fh, 0.04).translate(fx, fy, 0))), [w, h]);
  useEffect(() => () => frameGeo.dispose(), [frameGeo]);
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
      <mesh geometry={frameGeo} position={[0, 0, 0.02]}>
        <meshStandardMaterial color="#5a4630" roughness={0.6} />
      </mesh>
      <mesh ref={plaque} position={labelPos}>
        <planeGeometry args={[0.3, 0.2]} />
        <meshBasicMaterial map={label} toneMapped={false} transparent />
      </mesh>
    </group>
  );
}

/** The wall label, drawn on a canvas (crisp under any camera projection). */
/** The labels' face (main.tsx loads it); Georgia stands in until it has loaded. */
const LABEL_FONTS = ["italic 40px Cardo", "29px Cardo", "23px Cardo"];
const FACE = "Cardo, Georgia, 'Times New Roman', serif";

function labelTexture(p: Painting) {
  const c = document.createElement("canvas");
  c.width = 600;
  c.height = 400;
  const g = c.getContext("2d")!;
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 8;
  const draw = () => {
    g.fillStyle = "#f4f1ea";
    g.fillRect(0, 0, 600, 400);
    g.fillStyle = "#2a2724";
    g.font = `italic 40px ${FACE}`;
    wrap(g, p.title, 36, 74, 528, 46);
    g.font = `29px ${FACE}`;
    g.fillText(`${p.artist}, ${p.date}`, 36, 250);
    g.font = `23px ${FACE}`;
    g.fillStyle = "#6b655d";
    g.fillText(`${p.medium}, ${p.dimensions}`, 36, 300);
    g.fillText("Tap to look closer", 36, 356);
    t.needsUpdate = true;
    rig.kick();
  };
  draw();
  // A canvas can't wait for a web font: draw again once Cardo is in.
  Promise.all(LABEL_FONTS.map((f) => document.fonts.load(f))).then(draw, () => {});
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
