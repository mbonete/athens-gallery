import { useFrame, useLoader, useThree } from "@react-three/fiber";
import { useEffect, useMemo } from "react";
import * as THREE from "three";
import { rig } from "./rig";

/** A photographed sky with scattered fair-weather clouds (Poly Haven, CC0; sky/make_sky.sh),
 * turned so its sun stands where the hall's bake puts the sun, its sun disc taken out, and its
 * clear blue matched to a physical model of the same sky (Blender's multiple-scattering sky) at
 * twice the bake's exposure, so the sky through the openings sits with the light on the marble.
 * It's drawn unlit around the camera, first and without depth, so the hall covers it everywhere
 * except through its openings.
 *
 * The texture is a stereographic projection centred on the zenith: no pole and no seam.
 * A direction d maps to p = (d.x, -d.z) / (1 + d.y), uv = 0.5 + 0.5 p / K, so the walk's
 * forward (-z) is the top of the image. The square's inscribed circle sits 2 deg below the
 * horizon; below the horizon the texture holds the horizon's haze, so uv simply clamps. */
const K = Math.tan((46 * Math.PI) / 180);

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
varying vec3 vDir;
void main() {
  vec3 d = normalize(vDir);
  vec2 p = vec2(d.x, -d.z) / max(1.0 + d.y, 1e-3);
  vec2 uv = clamp(0.5 + 0.5 * p / k, 0.0, 1.0);
  vec3 c = texture2D(map, uv).rgb;
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
    material.uniforms.light.value = rig.light;
  });
  return <primitive object={mesh} />;
}
