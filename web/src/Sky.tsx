import { useFrame, useLoader, useThree } from "@react-three/fiber";
import { useEffect, useMemo } from "react";
import * as THREE from "three";
import { rig } from "./rig";

/** The sky after the one Raphael painted through the openings of the School of Athens
 * (sky/gen_sky.py makes the texture from the scan). It's drawn unlit around the camera,
 * first and without depth, so the hall covers it everywhere except through its openings.
 *
 * The texture is a stereographic projection centred on the zenith: no pole and no seam.
 * A direction d maps to p = (d.x, -d.z) / (1 + d.y), uv = 0.5 + 0.5 p / K, so the walk's
 * forward (-z) is the top of the image. The square's inscribed circle sits 2 deg below the
 * horizon; below 5.5 deg the sky is one even haze, so uv simply clamps further down. */
const K = Math.tan((46 * Math.PI) / 180);

/** The drum's windows cut Raphael's clouds square. Seen from anywhere but his viewpoint those
 * squares would float in the sky, so the texture holds plain sky there (texels x 968, y 352,
 * 104 x 64, from the top left) and keeps the fresco's version in its top-left corner
 * (directions 15-21 deg below the horizon, which the floor always hides). The shader swaps it in
 * at the start of the walk and lets it go over the next few metres, while the drum's windows
 * move off that patch of sky. Numbers from sky/gen_sky.py (sky-recipe.json). */
const TEX = 2048;
const DRUM_RECT = new THREE.Vector4(968 / TEX, 1 - (352 + 64) / TEX, 104 / TEX, 64 / TEX);
const DRUM_STORE = new THREE.Vector2(0, 1 - 64 / TEX);
/** Camera z where the fresco's drum sky is fully in (the start, up to 2.5 m in) and fully out. */
const DRUM_IN_Z = -2.5;
const DRUM_OUT_Z = -7;

/** What the sky dims to around an open painting (the hall's old flat background did the same). */
const SKY_DIM = new THREE.Color("#2a2826");

/** Its own layer: the dome's picking pass (dome.ts) draws layers 0 and 7 only. */
export const SKY_LAYER = 1;

const vertexShader = /* glsl */ `
varying vec3 vDir;
void main() {
  vDir = position;
  // Centred on the camera wherever it goes: the sky is infinitely far.
  gl_Position = projectionMatrix * viewMatrix * vec4(position + cameraPosition, 1.0);
}`;

const fragmentShader = /* glsl */ `
uniform sampler2D map;
uniform vec3 dim;
uniform float light;
uniform float k;
uniform float atRaphael;
uniform vec4 drumRect;
uniform vec2 drumStore;
varying vec3 vDir;
void main() {
  vec3 d = normalize(vDir);
  vec2 p = vec2(d.x, -d.z) / max(1.0 + d.y, 1e-3);
  vec2 uv = clamp(0.5 + 0.5 * p / k, 0.0, 1.0);
  vec3 c = texture2D(map, uv).rgb;
  if (atRaphael > 0.0) { // a uniform: no divergence
    vec2 q = uv - drumRect.xy;
    float inside = step(0.0, q.x) * step(0.0, q.y) * step(q.x, drumRect.z) * step(q.y, drumRect.w);
    vec3 a = texture2D(map, drumStore + clamp(q, vec2(0.0), drumRect.zw)).rgb;
    c = mix(c, a, inside * atRaphael);
  }
  gl_FragColor = vec4(mix(dim, c, light), 1.0);
  #include <colorspace_fragment>
  // Up to half a level of noise either way: no banding in the gradient once it is 8 bits again.
  gl_FragColor.rgb += (fract(sin(dot(gl_FragCoord.xy, vec2(12.9898, 78.233))) * 43758.5453) - 0.5) / 255.0;
}`;

export function Sky() {
  const map = useLoader(THREE.TextureLoader, "/sky/sky.jpg");
  const camera = useThree((s) => s.camera);
  const material = useMemo(() => {
    map.colorSpace = THREE.SRGBColorSpace;
    return new THREE.ShaderMaterial({
      uniforms: {
        map: { value: map },
        dim: { value: SKY_DIM },
        light: { value: 1 },
        k: { value: K },
        atRaphael: { value: 1 },
        drumRect: { value: DRUM_RECT },
        drumStore: { value: DRUM_STORE },
      },
      vertexShader,
      fragmentShader,
      side: THREE.BackSide,
      depthTest: false,
      depthWrite: false,
      toneMapped: false,
    });
  }, [map]);
  const mesh = useMemo(() => {
    const m = new THREE.Mesh(new THREE.SphereGeometry(100, 32, 16), material);
    m.renderOrder = -1; // before the hall
    m.frustumCulled = false; // it moves with the camera in the shader
    m.layers.set(SKY_LAYER);
    m.name = "sky";
    return m;
  }, [material]);
  useEffect(() => () => (material.dispose(), mesh.geometry.dispose()), [material, mesh]);
  useEffect(() => {
    camera.layers.enable(SKY_LAYER);
  }, [camera]);
  useEffect(() => {
    // Test hook (dev only): swap the texture's image to compare skies.
    if (import.meta.env.DEV) (window as unknown as Record<string, unknown>).__sky = { material, mesh };
  }, [material, mesh]);
  useFrame(() => {
    const u = material.uniforms;
    u.light.value = rig.light;
    u.atRaphael.value = THREE.MathUtils.smoothstep(camera.position.z, DRUM_OUT_Z, DRUM_IN_Z);
  });
  return <primitive object={mesh} />;
}
