import * as THREE from "three";
import hall from "./data/hall.json";
import { SUN_DIR } from "./goldLeaf";

/** The entrance banners (Banners.tsx) in the bake's light. The hall is drawn unlit (detail x
 * lightmap x lightScale), so the banners are too, with the same light worked out per face: the
 * bake's sun (hall.json `sun`, goldLeaf.ts) and its sky, in lightmap units (the factor a colour is
 * multiplied by on screen). Both are read from the lightmap at load (measureLight), so the banners
 * follow every rebake:
 * - the floor round each base (light = sky + sun x sun.y where the bake has sun);
 * - the sky: faces near the banner turned away from the sun (the arch's back face and jamb), which
 *   only the sky and the bounce reach. One value for every direction: on the bake of cd75322 the
 *   floor in the parapet blocks' shadows read 0.36-0.43 and those faces 0.37-0.45.
 * - the sun at normal incidence: (floor - sky) / sun.y, 0 if the bake has the footprint in shade.
 * Until the hall is in, the values measured on cd75322: floor 1.127 (left), 1.096 (right), sky
 * 0.40 (the opening arch casts no shadow there, finish2.py, so both stood in the sun).
 * Stable across bakes as long as the bake settings are: the shadow softness below (a parapet's
 * baked shadow edge, 10 cm from 10 % to 90 %: Cycles' 3 deg sun, params.SUN_ANGLE, and the
 * lightmap's 16 px/m texels, bake.py). */
const SKY = 0.4;
const FLOOR_LIGHT = { left: 1.127, right: 1.096 } as const;
const sunFrom = (floor: number, sky: number) => Math.max(floor - sky, 0) / SUN_DIR.y;
/** The dimmest sky on the hall round the banners, as a share of the sky: the first riser's foot
 * (0.47-0.67 lit, of which the sun is 0.34; sky 0.40 on cd75322). */
const SKY_MIN = 0.625;

// Soft shadow edges, as smoothstep widths (10-90 % is 0.61 of one): width(t) = hypot(w0, k t) for a
// shadow cast t metres along the sun. k: the bake's 3 deg sun; w0: the lightmap's blur on the hall
// (the decal), a few mm on the banner itself (not lightmapped).
const K = (0.7 * THREE.MathUtils.degToRad(3)) / 0.61;
const W0_HALL = Math.sqrt(0.1 ** 2 - 0.045 ** 2) / 0.61;
const W0_SELF = 0.002;

/** Banner space: x along the base, y up from the floor, z towards the entrance, origin under the
 * cloth's centre. The occluders: the cloth (the rectangle z = 0) and the base (a box). */
const LIGHT_GLSL = /* glsl */ `
uniform vec3 bnSun;
uniform float bnSunE;
uniform float bnSky;
uniform vec3 bnAt;
uniform vec3 bnCloth; // half width, bottom, top
uniform vec3 bnBase;  // half length, height, half depth

float bnSoftRect(vec2 p, vec2 lo, vec2 hi, float w) {
  vec2 a = smoothstep(lo - 0.5 * w, lo + 0.5 * w, p) * (1.0 - smoothstep(hi - 0.5 * w, hi + 0.5 * w, p));
  return a.x * a.y;
}

// The share of the sun the banner hides from p: rays to the sun through the cloth's rectangle or
// the base's top (a ray that enters the base crosses its top), with soft edges.
float bnSunHidden(vec3 p, float w0, bool base) {
  float o = 0.0;
  float t = -p.z / bnSun.z;
  if (t > 0.0) {
    vec3 h = p + t * bnSun;
    o = bnSoftRect(h.xy, vec2(-bnCloth.x, bnCloth.y), bnCloth.xz, length(vec2(w0, ${K.toFixed(4)} * t)));
  }
  if (base) {
    t = (bnBase.y - p.y) / bnSun.y;
    if (t > 0.0) {
      vec3 h = p + t * bnSun;
      o = max(o, bnSoftRect(h.xz, -bnBase.xz, bnBase.xz, length(vec2(w0, ${K.toFixed(4)} * t))));
    }
  }
  return o;
}

// Lambert's formula: the share of the cosine-weighted hemisphere over (p, n) that the quad abcd
// covers, clipped to that hemisphere. Edge by edge, no arrays (they cost a lot per fragment): an
// edge that leaves the hemisphere ends at the horizon, and the horizon closes the polygon.
float bnEdge(vec3 A, vec3 B, vec3 n) {
  A = normalize(A);
  B = normalize(B);
  vec3 c = cross(A, B);
  float l = length(c);
  return l > 1e-6 ? atan(l, dot(A, B)) * dot(n, c) / l : 0.0;
}
float bnClipEdge(vec3 A, vec3 B, float ha, float hb, vec3 n, inout vec3 leave, inout vec3 enter) {
  if (ha >= 0.0 && hb >= 0.0) return bnEdge(A, B, n);
  if (ha < 0.0 && hb < 0.0) return 0.0;
  vec3 I = A + (B - A) * (ha / (ha - hb));
  if (ha >= 0.0) { leave = I; return bnEdge(A, I, n); }
  enter = I;
  return bnEdge(I, B, n);
}
float bnQuad(vec3 p, vec3 n, vec3 a, vec3 b, vec3 c, vec3 d) {
  a -= p; b -= p; c -= p; d -= p;
  float ha = dot(n, a) - 1e-4, hb = dot(n, b) - 1e-4, hc = dot(n, c) - 1e-4, hd = dot(n, d) - 1e-4;
  if (max(max(ha, hb), max(hc, hd)) < 0.0) return 0.0;
  vec3 leave = vec3(0.0), enter = vec3(0.0);
  float s = bnClipEdge(a, b, ha, hb, n, leave, enter) + bnClipEdge(b, c, hb, hc, n, leave, enter)
    + bnClipEdge(c, d, hc, hd, n, leave, enter) + bnClipEdge(d, a, hd, ha, n, leave, enter);
  if (min(min(ha, hb), min(hc, hd)) < 0.0) s += bnEdge(leave, enter, n);
  return abs(s) / (2.0 * PI);
}

// The share of the sky (and the floor's bounce) the banner hides from (p, n): the cloth from
// height clothFrom up (the base's top for the hall; down into the slot for the base itself), and
// the base's faces turned to p. Skipped where it is too far to matter (the cloth fades out from
// 1.2 to 1.6 m, where it hides under 2 % of the floor's light; the base beyond 0.5 m).
float bnSkyHidden(vec3 p, vec3 n, float clothFrom, bool base) {
  vec3 C = bnCloth;
  vec3 B = bnBase;
  float f = 0.0;
  float dc = length(vec3(max(abs(p.x) - C.x, 0.0), max(max(clothFrom - p.y, p.y - C.z), 0.0), p.z));
  if (clothFrom < C.z && dc < 1.6)
    f += bnQuad(p, n, vec3(-C.x, clothFrom, 0.0), vec3(C.x, clothFrom, 0.0), vec3(C.x, C.z, 0.0), vec3(-C.x, C.z, 0.0)) * smoothstep(1.6, 1.2, dc);
  if (base && length(max(abs(p) - vec3(B.x, 1e3, B.z), 0.0)) + max(p.y - B.y, 0.0) < 0.5) {
    if (p.y > B.y) f += bnQuad(p, n, vec3(-B.x, B.y, B.z), vec3(B.x, B.y, B.z), vec3(B.x, B.y, -B.z), vec3(-B.x, B.y, -B.z));
    if (p.z > B.z) f += bnQuad(p, n, vec3(-B.x, 0.0, B.z), vec3(B.x, 0.0, B.z), vec3(B.x, B.y, B.z), vec3(-B.x, B.y, B.z));
    if (p.z < -B.z) f += bnQuad(p, n, vec3(-B.x, 0.0, -B.z), vec3(B.x, 0.0, -B.z), vec3(B.x, B.y, -B.z), vec3(-B.x, B.y, -B.z));
    if (p.x > B.x) f += bnQuad(p, n, vec3(B.x, 0.0, -B.z), vec3(B.x, 0.0, B.z), vec3(B.x, B.y, B.z), vec3(B.x, B.y, -B.z));
    if (p.x < -B.x) f += bnQuad(p, n, vec3(-B.x, 0.0, -B.z), vec3(-B.x, 0.0, B.z), vec3(-B.x, B.y, B.z), vec3(-B.x, B.y, -B.z));
  }
  return min(f, 0.95);
}
`;

/** The light a banner shares with its materials and its shadow on the hall. */
export function bannerUniforms(at: THREE.Vector3, side: "left" | "right", cloth: THREE.Vector3, base: THREE.Vector3) {
  return {
    bnSun: { value: SUN_DIR },
    bnSunE: { value: sunFrom(FLOOR_LIGHT[side], SKY) },
    bnSky: { value: SKY },
    bnAt: { value: at },
    bnCloth: { value: cloth },
    bnBase: { value: base },
  };
}
export type BannerUniforms = ReturnType<typeof bannerUniforms>;

export type Part = "cloth" | "bronze" | "gilt";
const PART = { cloth: 0, bronze: 1, gilt: 2 } as const;
/** Metal: Schlick's Fresnel from f0, a reflection of the hall (floor below the horizon, walls and
 * vault above) and the sun's highlight. `dim` follows rig.light. */
export type Metal = { f0: THREE.Color; fresnel: number; shine: number };

/** An unlit material lit like the hall: sky + sun per face, the banner's own occlusion (the
 * cloth over the base's top, the base round the cloth's foot, the slot), and for the metals a
 * reflection and the sun's highlight. The colour stays the albedo, dimmed by the caller. */
export function litBanner(mat: THREE.MeshBasicMaterial, u: BannerUniforms, part: Part, metal?: Metal, slot = 0) {
  const own = {
    bnF0: { value: metal ? metal.f0.clone() : new THREE.Color(0, 0, 0) },
    bnFresnel: { value: metal?.fresnel ?? 0 },
    bnShine: { value: metal?.shine ?? 1 },
    bnDim: { value: 1 },
    bnSlot: { value: slot },
  };
  mat.defines = { ...mat.defines, BN_PART: PART[part] };
  mat.onBeforeCompile = (shader) => {
    Object.assign(shader.uniforms, u, own);
    shader.vertexShader = shader.vertexShader
      .replace("#include <common>", "#include <common>\nvarying vec3 vBnP;\nvarying vec3 vBnN;")
      .replace(
        "#include <begin_vertex>",
        "#include <begin_vertex>\nvBnP = (modelMatrix * vec4(transformed, 1.0)).xyz;\nvBnN = normalize(mat3(modelMatrix) * normal);",
      );
    shader.fragmentShader = shader.fragmentShader
      .replace(
        "#include <common>",
        `#include <common>
varying vec3 vBnP;
varying vec3 vBnN;
uniform vec3 bnF0;
uniform float bnFresnel;
uniform float bnShine;
uniform float bnDim;
uniform float bnSlot;
${LIGHT_GLSL}
// Value noise (hash: Inigo Quilez) for the bronze's mottled patina.
float bnHash(vec3 p) {
  p = fract(p * 0.3183099 + 0.1) * 17.0;
  return fract(p.x * p.y * p.z * (p.x + p.y + p.z));
}
float bnNoise(vec3 x) {
  vec3 i = floor(x);
  vec3 f = fract(x);
  f = f * f * (3.0 - 2.0 * f);
  return mix(mix(mix(bnHash(i), bnHash(i + vec3(1, 0, 0)), f.x), mix(bnHash(i + vec3(0, 1, 0)), bnHash(i + vec3(1, 1, 0)), f.x), f.y),
             mix(mix(bnHash(i + vec3(0, 0, 1)), bnHash(i + vec3(1, 0, 1)), f.x), mix(bnHash(i + vec3(0, 1, 1)), bnHash(i + vec3(1, 1, 1)), f.x), f.y), f.z);
}`,
      )
      .replace(
        "reflectedLight.indirectDiffuse += vec3( 1.0 );",
        `vec3 bnP = vBnP - bnAt;
vec3 bnN = normalize(vBnN);
float bnSunSeen = 1.0;
float bnPatina = 1.0;
#if BN_PART == 1
  bnPatina = 0.6 * bnNoise(bnP * 35.0) + 0.4 * bnNoise(bnP * 110.0 + 7.0);
#endif
#if BN_PART == 1
  bnSunSeen = 1.0 - bnSunHidden(bnP, ${W0_SELF.toFixed(4)}, false);
  float bnSkySeen = 1.0 - bnSkyHidden(bnP, bnN, 0.0, false);
  // The foot's rounded underside: the floor under it is in the base's own shade, so little of the
  // floor's bounce reaches it.
  float bnFoot = 1.0 - smoothstep(0.0, 0.012, bnP.y);
  bnSkySeen *= 1.0 - bnFoot * (0.3 + 0.5 * max(-bnN.y, 0.0));
#else
  float bnSkySeen = 1.0 - bnSkyHidden(bnP, bnN, 1e3, true);
#endif
// Down in the slot (half width bnSlot): the light falls off with depth like a narrow trench's.
if (bnSlot > 0.0 && abs(bnP.z) < bnSlot + 0.008 && abs(bnP.x) < bnCloth.x + 0.02) {
  float d = max(bnBase.y - 0.001 - bnP.y, 0.0);
  float open = 1.0 - d / sqrt(d * d + 4.0 * bnSlot * bnSlot);
  bnSkySeen *= open;
  bnSunSeen *= smoothstep(0.6, 0.95, open);
}
float bnE = bnSky * bnSkySeen + bnSunE * max(dot(bnN, bnSun), 0.0) * bnSunSeen;
#if BN_PART == 1
  bnE *= 0.8 + 0.4 * bnPatina;
#endif
reflectedLight.indirectDiffuse += vec3(bnE);`,
      )
      .replace(
        "#include <opaque_fragment>",
        `#if BN_PART > 0
{
  vec3 V = normalize(cameraPosition - vBnP);
  vec3 H = normalize(bnSun + V);
  float nv = max(dot(bnN, V), 0.0);
  vec3 F = (bnF0 + (1.0 - bnF0) * pow(1.0 - nv, 5.0) * bnFresnel) * (BN_PART == 1 ? 1.25 - 0.5 * bnPatina : 1.0);
  vec3 R = reflect(-V, bnN);
  float env = mix(0.33, 0.62, smoothstep(-0.3, 0.3, R.y)) * bnSkySeen;
  float lobe = pow(max(dot(bnN, H), 0.0), bnShine) * (bnShine + 2.0) / 8.0;
  outgoingLight += F * (env + bnSunE * max(dot(bnN, bnSun), 0.0) * bnSunSeen * lobe) * bnDim;
}
#endif
#include <opaque_fragment>`,
      );
  };
  mat.customProgramCacheKey = () => "banner-lit";
  return own;
}

/** The base: a bronze block with rounded edges (an extrusion bevelled 6 mm across, 8 mm down), top
 * and foot, standing on the floor, with a slot through it for the cloth's foot. */
export function baseGeometry(w: number, h: number, d: number, slotLen: number, slotW: number) {
  const bs = 0.006;
  const bt = 0.008;
  const sink = -bt; // the bottom cap on the floor
  const shape = new THREE.Shape();
  roundedRect(shape, w / 2 - bs, d / 2 - bs, 0.007);
  // The bevel narrows a hole by bs on each side: the slot's walls are slotW apart under its lips.
  const hole = new THREE.Path();
  roundedRect(hole, slotLen / 2 + bs, slotW / 2 + bs, slotW / 2 + bs - 0.0005);
  shape.holes.push(hole);
  const segs = 4;
  const g = new THREE.ExtrudeGeometry(shape, {
    depth: h + sink - bt, bevelEnabled: true, bevelSize: bs, bevelThickness: bt, bevelSegments: segs, curveSegments: 6, steps: 1,
  });
  smoothProfile(g, 1 + 2 * segs);
  g.rotateX(-Math.PI / 2);
  g.translate(0, -sink, 0);
  return g;
}

function roundedRect(p: THREE.Path, hw: number, hd: number, r: number) {
  p.moveTo(-hw + r, -hd);
  p.lineTo(hw - r, -hd);
  p.absarc(hw - r, -hd + r, r, -Math.PI / 2, 0, false);
  p.lineTo(hw, hd - r);
  p.absarc(hw - r, hd - r, r, 0, Math.PI / 2, false);
  p.lineTo(-hw + r, hd);
  p.absarc(-hw + r, hd - r, r, Math.PI / 2, Math.PI, false);
  p.lineTo(-hw, -hd + r);
  p.absarc(-hw + r, -hd + r, r, Math.PI, 1.5 * Math.PI, false);
}

/** ExtrudeGeometry's side faces come flat-shaded; smooth them along the bevel's profile only, so
 * the rounded edges shade round while the long flat walls stay flat. Side quads are stored per
 * contour edge, `layers` quads up the profile, 6 vertices each (a, b, d, b, c, d; a, b on the
 * lower layer). */
function smoothProfile(g: THREE.ExtrudeGeometry, layers: number) {
  const side = g.groups[1];
  const pos = g.getAttribute("position") as THREE.BufferAttribute;
  const nor = g.getAttribute("normal") as THREE.BufferAttribute;
  const a = new THREE.Vector3();
  const b = new THREE.Vector3();
  const c = new THREE.Vector3();
  const quads = side.count / 6;
  for (let e = 0; e < quads / layers; e++) {
    const n: THREE.Vector3[] = [];
    for (let s = 0; s < layers; s++) {
      const v = side.start + (e * layers + s) * 6;
      a.fromBufferAttribute(pos, v);
      b.fromBufferAttribute(pos, v + 1);
      c.fromBufferAttribute(pos, v + 2);
      n.push(b.sub(a).cross(c.sub(a)).normalize().clone());
    }
    for (let s = 0; s < layers; s++) {
      const lower = (s > 0 ? n[s - 1].clone().add(n[s]) : n[s].clone()).normalize();
      const upper = (s < layers - 1 ? n[s].clone().add(n[s + 1]) : n[s].clone()).normalize();
      const v = side.start + (e * layers + s) * 6;
      [lower, lower, upper, lower, upper, upper].forEach((m, i) => nor.setXYZ(v + i, m.x, m.y, m.z));
    }
  }
  nor.needsUpdate = true;
}

type HallVertex = { p: THREE.Vector3; uv: THREE.Vector2 };

/** The hall's lightmapped triangles inside `region` (world), clipped to it: each as a polygon of
 * world points with their lightmap uv, its face normal and its lightmap. */
function hallPolys(scene: THREE.Object3D, region: THREE.Box3, fn: (poly: HallVertex[], normal: THREE.Vector3, lm: THREE.Texture) => void) {
  const tri = [new THREE.Vector3(), new THREE.Vector3(), new THREE.Vector3()];
  const uvs = [new THREE.Vector2(), new THREE.Vector2(), new THREE.Vector2()];
  const tb = new THREE.Box3();
  const nrm = new THREE.Vector3();
  const e1 = new THREE.Vector3();
  scene.traverse((o) => {
    const mesh = o as THREE.Mesh;
    const lm = mesh.isMesh ? (mesh.material as THREE.MeshBasicMaterial).lightMap : null;
    const uv1 = mesh.isMesh ? mesh.geometry.getAttribute("uv1") : undefined;
    if (!lm || !uv1 || !mesh.name.startsWith("hall_")) return;
    mesh.updateWorldMatrix(true, false);
    const g = mesh.geometry;
    g.computeBoundingBox();
    if (!tb.copy(g.boundingBox!).applyMatrix4(mesh.matrixWorld).intersectsBox(region)) return;
    const pos = g.getAttribute("position");
    const index = g.index;
    const count = index ? index.count : pos.count;
    for (let i = 0; i < count; i += 3) {
      for (let k = 0; k < 3; k++) {
        const vi = index ? index.getX(i + k) : i + k;
        tri[k].fromBufferAttribute(pos, vi).applyMatrix4(mesh.matrixWorld);
        uvs[k].fromBufferAttribute(uv1 as THREE.BufferAttribute, vi);
      }
      if (!tb.setFromPoints(tri).intersectsBox(region)) continue;
      nrm.subVectors(tri[1], tri[0]).cross(e1.subVectors(tri[2], tri[0]));
      if (nrm.lengthSq() < 1e-14) continue;
      nrm.normalize();
      let poly: HallVertex[] = tri.map((p, k) => ({ p: p.clone(), uv: uvs[k].clone() }));
      for (const axis of ["x", "y", "z"] as const) {
        poly = clip(poly, axis, region.min[axis], 1);
        poly = clip(poly, axis, region.max[axis], -1);
      }
      if (poly.length >= 3) fn(poly, nrm, lm);
    }
  });
}

/** The bake's light round a banner, read from the hall's lightmap (the same lightmap x lightScale
 * the hall is drawn with), and the sky and sun it gives:
 * - floor: the floor round the base, 5 to 25 cm out, beside and in front of it (not the strip
 *   behind it, against the first riser, whose texels the riser's corner darkens); the mean of the
 *   middle 80 % of the samples, every 2.5 cm;
 * - sky: the median, by area, over faces within 1.5 m that the sun can't reach (turned more than
 *   6 deg from it, upright), five points on each, at the cloth's height (0.6 to 2.5 m: lower down, the
 *   stairs' end and the parapet's foot sit in corners the bounce hardly reaches, 0.3 where the
 *   open faces read 0.37-0.42).
 * `at`: the banner's centre on the floor; `base`: the base's half length, height, half depth.
 * Returns null if the floor isn't found (the defaults stay). */
export function measureLight(gl: THREE.WebGLRenderer, scene: THREE.Object3D, at: THREE.Vector3, base: THREE.Vector3) {
  type Sample = { lm: THREE.Texture; uv: THREE.Vector2 };
  const floor: Sample[] = [];
  const sky: Sample[] = [];
  // The floor: its upward triangles at the base's foot, and points of the ring found in them.
  const ring: THREE.Vector2[] = [];
  for (let x = -base.x - 0.25; x <= base.x + 0.25 + 1e-6; x += 0.025) {
    for (let z = -base.z; z <= base.z + 0.25 + 1e-6; z += 0.025) {
      const d = Math.hypot(Math.max(Math.abs(x) - base.x, 0), Math.max(Math.abs(z) - base.z, 0));
      if (d >= 0.05 && d <= 0.25) ring.push(new THREE.Vector2(at.x + x, at.z + z));
    }
  }
  const near = new THREE.Box3(at.clone().add(new THREE.Vector3(-base.x - 0.3, -0.05, -base.z - 0.3)), at.clone().add(new THREE.Vector3(base.x + 0.3, 0.05, base.z + 0.3)));
  hallPolys(scene, near, (poly, n, lm) => {
    if (n.y < 0.99 || Math.abs(poly[0].p.y - at.y) > 0.02) return;
    for (let k = 1; k < poly.length - 1; k++) {
      const [a, b, c] = [poly[0], poly[k], poly[k + 1]];
      for (const q of ring) {
        const w = barycentric(q, a.p, b.p, c.p);
        if (!w) continue;
        floor.push({ lm, uv: a.uv.clone().multiplyScalar(w.x).addScaledVector(b.uv, w.y).addScaledVector(c.uv, w.z) });
      }
    }
  });
  if (floor.length < 20) return null;
  // The sky: upright faces turned from the sun, near the banner.
  const around = new THREE.Box3(at.clone().add(new THREE.Vector3(-1.5, 0.6, -1.5)), at.clone().add(new THREE.Vector3(1.5, 2.5, 1.5)));
  const skyArea: number[] = [];
  const e = new THREE.Vector3();
  hallPolys(scene, around, (poly, n, lm) => {
    if (n.dot(SUN_DIR) > -0.1 || Math.abs(n.y) > 0.3) return;
    let area = 0;
    for (let k = 1; k < poly.length - 1; k++) area += e.subVectors(poly[k].p, poly[0].p).cross(poly[k + 1].p.clone().sub(poly[0].p)).length() / 2;
    const c = poly.reduce((s, v) => s.add(v.uv), new THREE.Vector2()).divideScalar(poly.length);
    const pts = [c, ...poly.slice(0, 4).map((v) => c.clone().lerp(v.uv, 0.5))];
    for (const uv of pts) {
      sky.push({ lm, uv });
      skyArea.push(area / pts.length);
    }
  });
  const lum = readLightmaps(gl, [...floor, ...sky]).map((v) => v * (hall.lightScale ?? 1));
  const f = lum.slice(0, floor.length).sort((x, y) => x - y);
  const cut = Math.floor(f.length * 0.1);
  const mid = f.slice(cut, f.length - cut);
  const floorLight = mid.reduce((s, v) => s + v, 0) / mid.length;
  // Weighted by area: the arch's finely cut strips must not outvote its plain walls.
  const s = lum.slice(floor.length).map((v, i) => [v, skyArea[i]] as const).sort((x, y) => x[0] - y[0]);
  const total = s.reduce((t, [, a]) => t + a, 0);
  let acc = 0;
  const skyLight = s.length >= 5 ? (s.find(([, a]) => (acc += a) >= total / 2) ?? s[s.length - 1])[0] : SKY;
  return { floor: floorLight, sky: skyLight, sun: sunFrom(floorLight, skyLight), samples: [floor.length, sky.length], area: +total.toFixed(2) };
}

function barycentric(q: THREE.Vector2, a: THREE.Vector3, b: THREE.Vector3, c: THREE.Vector3) {
  const v0x = b.x - a.x, v0z = b.z - a.z, v1x = c.x - a.x, v1z = c.z - a.z, v2x = q.x - a.x, v2z = q.y - a.z;
  const den = v0x * v1z - v1x * v0z;
  if (Math.abs(den) < 1e-12) return null;
  const v = (v2x * v1z - v1x * v2z) / den;
  const w = (v0x * v2z - v2x * v0z) / den;
  const u = 1 - v - w;
  return u >= -1e-6 && v >= -1e-6 && w >= -1e-6 ? new THREE.Vector3(u, v, w) : null;
}

/** Lightmap luminance (linear, as the hall's shader reads it) at each sample: one pixel each,
 * drawn on the GPU into a strip and read back, packed into two bytes so it needs no float target. */
function readLightmaps(gl: THREE.WebGLRenderer, samples: { lm: THREE.Texture; uv: THREE.Vector2 }[]) {
  const n = samples.length;
  const rt = new THREE.WebGLRenderTarget(n, 1, { depthBuffer: false });
  const cam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
  const prev = gl.getRenderTarget();
  const prevClear = gl.autoClear;
  gl.setRenderTarget(rt);
  gl.autoClear = false;
  const byLm = new Map<THREE.Texture, number[]>();
  samples.forEach((s, i) => byLm.set(s.lm, [...(byLm.get(s.lm) ?? []), i]));
  const made: { geo: THREE.BufferGeometry; mat: THREE.ShaderMaterial }[] = [];
  for (const [lm, idx] of byLm) {
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.Float32BufferAttribute(idx.flatMap((i) => [((i + 0.5) / n) * 2 - 1, 0, 0]), 3));
    geo.setAttribute("aLmUv", new THREE.Float32BufferAttribute(idx.flatMap((i) => [samples[i].uv.x, samples[i].uv.y]), 2));
    const mat = new THREE.ShaderMaterial({
      uniforms: { lm: { value: lm } },
      vertexShader: "attribute vec2 aLmUv; varying vec2 vUv; void main() { vUv = aLmUv; gl_Position = vec4(position.xy, 0.0, 1.0); gl_PointSize = 1.0; }",
      fragmentShader: "uniform sampler2D lm; varying vec2 vUv; void main() { float v = clamp(dot(texture2D(lm, vUv).rgb, vec3(0.2126, 0.7152, 0.0722)), 0.0, 0.999); gl_FragColor = vec4(floor(v * 255.0) / 255.0, fract(v * 255.0), 0.0, 1.0); }",
      depthTest: false, depthWrite: false, toneMapped: false,
    });
    const pts = new THREE.Points(geo, mat);
    pts.frustumCulled = false;
    gl.render(pts, cam);
    made.push({ geo, mat });
  }
  const buf = new Uint8Array(n * 4);
  gl.readRenderTargetPixels(rt, 0, 0, n, 1, buf);
  gl.setRenderTarget(prev);
  gl.autoClear = prevClear;
  rt.dispose();
  made.forEach(({ geo, mat }) => (geo.dispose(), mat.dispose()));
  return samples.map((_, i) => (buf[i * 4] + buf[i * 4 + 1] / 255) / 255);
}

/** The banner's shadow and occlusion on the hall: the hall's own triangles inside `region`
 * (world), clipped to it, drawn again over the hall and multiplied into it. Each fragment reads the
 * bake's light where it lies (the hall's lightmap) and takes away the sun the banner hides (if the
 * face is turned to the sun) and the sky it hides. Same triangles as the hall's, so no lift: the
 * polygon offset keeps it in front. */
export function shadowDecals(scene: THREE.Object3D, region: THREE.Box3, u: BannerUniforms) {
  const groups = new Map<THREE.Texture, { p: number[]; n: number[]; uv: number[] }>();
  hallPolys(scene, region, (poly, nrm, lm) => {
    let grp = groups.get(lm);
    if (!grp) groups.set(lm, (grp = { p: [], n: [], uv: [] }));
    for (let k = 1; k < poly.length - 1; k++) {
      for (const v of [poly[0], poly[k], poly[k + 1]]) {
        grp.p.push(v.p.x, v.p.y, v.p.z);
        grp.n.push(nrm.x, nrm.y, nrm.z);
        grp.uv.push(v.uv.x, v.uv.y);
      }
    }
  });
  const meshes: THREE.Mesh[] = [];
  for (const [lm, grp] of groups) {
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute(grp.p, 3));
    g.setAttribute("normal", new THREE.Float32BufferAttribute(grp.n, 3));
    g.setAttribute("aLmUv", new THREE.Float32BufferAttribute(grp.uv, 2));
    g.computeBoundingSphere();
    const mat = new THREE.ShaderMaterial({
      uniforms: { ...u, bnLightMap: { value: lm }, bnLightScale: { value: hall.lightScale ?? 1 } },
      vertexShader: /* glsl */ `
attribute vec2 aLmUv;
varying vec3 vP;
varying vec3 vN;
varying vec2 vLmUv;
void main() {
  vP = position;
  vN = normal;
  vLmUv = aLmUv;
  gl_Position = projectionMatrix * viewMatrix * vec4(position, 1.0);
}`,
      fragmentShader: /* glsl */ `
#include <common>
uniform sampler2D bnLightMap;
uniform float bnLightScale;
varying vec3 vP;
varying vec3 vN;
varying vec2 vLmUv;
${LIGHT_GLSL}
void main() {
  vec3 p = vP - bnAt;
  vec3 n = normalize(vN);
  // The bake's light here, split into sun and sky: the sun's share is what lies above the dimmest
  // sky a face gets here (a riser's foot, under the nosing), at most the full sun on this face. So
  // a corner the bake already shades loses nothing more, and the shadow reads even over the
  // lightmap's texel noise.
  float L = max(dot(texture2D(bnLightMap, vLmUv).rgb, vec3(0.2126, 0.7152, 0.0722)) * bnLightScale, 0.02);
  float sunPart = clamp(L - ${SKY_MIN.toFixed(3)} * bnSky, 0.0, bnSunE * max(dot(n, bnSun), 0.0));
  float skyPart = L - sunPart;
  float lost = bnSunHidden(p, ${W0_HALL.toFixed(4)}, true) * sunPart + bnSkyHidden(p, n, bnCloth.y, true) * skyPart;
  float f = 1.0 - lost / L;
  // The crease where the base's rounded foot meets the floor (under it, and a few mm out).
  if (abs(p.y) < 0.004) f *= 1.0 - 0.55 * exp(-length(max(abs(p.xz) - bnBase.xz, 0.0)) / 0.006);
  gl_FragColor = vec4(vec3(clamp(f, 0.0, 1.0)), 1.0);
  #include <colorspace_fragment>
}`,
      blending: THREE.CustomBlending,
      blendEquation: THREE.AddEquation,
      blendSrc: THREE.DstColorFactor,
      blendDst: THREE.ZeroFactor,
      transparent: true,
      depthWrite: false,
      polygonOffset: true,
      polygonOffsetFactor: -1,
      polygonOffsetUnits: -4,
      toneMapped: false,
    });
    const m = new THREE.Mesh(g, mat);
    m.name = "banner_shadow";
    m.renderOrder = 1;
    m.matrixAutoUpdate = false;
    m.raycast = () => {}; // not a surface: probes and picking see the hall under it
    meshes.push(m);
  }
  return meshes;
}

function clip<T extends { p: THREE.Vector3; uv: THREE.Vector2 }>(poly: T[], axis: "x" | "y" | "z", v: number, sign: 1 | -1): T[] {
  const out: T[] = [];
  for (let i = 0; i < poly.length; i++) {
    const a = poly[i];
    const b = poly[(i + 1) % poly.length];
    const da = (a.p[axis] - v) * sign;
    const db = (b.p[axis] - v) * sign;
    if (da >= 0) out.push(a);
    if (da >= 0 !== db >= 0) {
      const t = da / (da - db);
      out.push({ p: a.p.clone().lerp(b.p, t), uv: a.uv.clone().lerp(b.uv, t) } as T);
    }
  }
  return out;
}
