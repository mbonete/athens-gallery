import { useFrame, useLoader, useThree } from "@react-three/fiber";
import { useEffect, useMemo } from "react";
import * as THREE from "three";
import plane from "./data/vaultOrnament.json";
import { GOLD_SHEEN, GOLD_SHININESS, SUN_DIR } from "./goldLeaf";
import { rig } from "./rig";

/** The painted vault round the opening arch (first-arch idea 1, Maria, 2026-11-22): the vault of
 * the Stanza della Segnatura as the fresco scan's margins show it, figure-free and redrawn as
 * vectors by tools/vault_ornament.py. A gold interlace band on blue follows the arch's dark red
 * band, a gilt rosette roundel sits at ±50°, a pale rib runs from each roundel to the edge of the
 * view, and under each rib a blue field holds a gold oak.
 *
 * It is paint on the front wall: one plane 2 cm before the wall's face, shaped in the fresco's px
 * through the camera solve (data/vaultOrnament.json). Its inner edge lies on the outer band's
 * edge along Raphael's sight lines, 1 mm behind the band's front, so walking in the band covers
 * it and no gap opens. The texture holds the left half; the right half mirrors it. */

/** Light on the front wall. The texture holds paint under the hall's nominal light (the arch's
 * own colours: params.ARCH_COLOURS). The lit front wall measures sRGB (190, 182, 159) on screen
 * where that light would show its paint, the hall's cream (218, 209, 183), so the wall's light
 * is (0.734, 0.734, 0.732) of it, linear. */
const WALL_LIGHT = new THREE.Color(0.734, 0.734, 0.732);
const ARC_STEPS = 192;
const noRaycast = () => {};

/** The gold is the arch's gold leaf, so it takes the arch's sheen (goldLeaf.ts) on top of the
 * wall's light. The texture has no gold mask: gold is its only saturated warm paint, so the mask
 * is the texel's warmth, (r - b) / r in linear light (gold 0.8-0.95, white 0.2, grey 0.4). */
function withSheen(mat: THREE.MeshBasicMaterial, sheenScale: { value: number }) {
  mat.onBeforeCompile = (shader) => {
    shader.uniforms.goldSun = { value: SUN_DIR };
    shader.uniforms.goldSheen = { value: GOLD_SHEEN };
    shader.uniforms.sheenScale = sheenScale;
    shader.vertexShader = shader.vertexShader
      .replace("#include <common>", "#include <common>\nvarying vec3 vGoldP;")
      .replace("#include <begin_vertex>", "#include <begin_vertex>\nvGoldP = (modelMatrix * vec4(transformed, 1.0)).xyz;");
    shader.fragmentShader = shader.fragmentShader
      .replace(
        "#include <common>",
        "#include <common>\nuniform vec3 goldSun;\nuniform vec3 goldSheen;\nuniform float sheenScale;\nvarying vec3 vGoldP;",
      )
      .replace(
        "#include <map_fragment>",
        "#include <map_fragment>\nfloat goldMask = smoothstep(0.55, 0.75, (sampledDiffuseColor.r - sampledDiffuseColor.b) / max(sampledDiffuseColor.r, 1e-3));",
      )
      .replace(
        "#include <opaque_fragment>",
        `{
  vec3 v = normalize(cameraPosition - vGoldP);
  float lobe = pow(max(dot(vec3(0.0, 0.0, 1.0), normalize(goldSun + v)), 0.0), ${GOLD_SHININESS.toFixed(1)});
  outgoingLight += goldMask * lobe * goldSheen * sheenScale;
}
#include <opaque_fragment>`,
      );
  };
  mat.customProgramCacheKey = () => "vault-ornament-sheen";
}

/** Half the wall round the arch: from the plane's outer edge in to the arch's axis, minus the
 * opening (side -1 the left half, +1 its mirror). UVs map the left half's texture, mirrored. */
function halfGeometry(side: -1 | 1) {
  const { xc, yc, rIn, y0, y1, halfWidth: hw } = plane;
  const mx = (x: number) => (side < 0 ? x : 2 * xc - x);
  const foot = Math.atan2(y0 - yc, -Math.sqrt(rIn * rIn - (y0 - yc) ** 2)); // where the arch meets y0
  const pts: THREE.Vector2[] = [new THREE.Vector2(mx(xc - hw), y0)];
  for (let i = 0; i <= ARC_STEPS; i++) {
    const a = foot + ((Math.PI / 2 - foot) * i) / ARC_STEPS;
    pts.push(new THREE.Vector2(mx(xc + rIn * Math.cos(a)), yc + rIn * Math.sin(a)));
  }
  pts.push(new THREE.Vector2(mx(xc), y1), new THREE.Vector2(mx(xc - hw), y1));
  const geom = new THREE.ShapeGeometry(new THREE.Shape(pts));
  const pos = geom.getAttribute("position");
  const uv = geom.getAttribute("uv");
  for (let i = 0; i < pos.count; i++) {
    const x = side < 0 ? pos.getX(i) : 2 * xc - pos.getX(i);
    uv.setXY(i, (x - (xc - hw)) / hw, (pos.getY(i) - y0) / (y1 - y0));
  }
  uv.needsUpdate = true;
  return geom;
}

export function VaultOrnament() {
  const tex = useLoader(THREE.TextureLoader, plane.texture);
  const { gl } = useThree();
  const sheenScale = useMemo(() => ({ value: 1 }), []);
  const mat = useMemo(() => {
    tex.colorSpace = THREE.SRGBColorSpace;
    tex.anisotropy = gl.capabilities.getMaxAnisotropy();
    tex.needsUpdate = true;
    // Straight alpha: the script bleeds the paint's colour into the clear texels, so filtering
    // and mipmaps keep clean edges; alphaTest drops the clear fragments.
    const m = new THREE.MeshBasicMaterial({
      map: tex, color: WALL_LIGHT, transparent: true, alphaTest: 0.004, depthWrite: false, toneMapped: false,
    });
    withSheen(m, sheenScale);
    return m;
  }, [tex, gl, sheenScale]);
  const geoms = useMemo(() => [halfGeometry(-1), halfGeometry(1)], []);
  useEffect(() => () => {
    mat.dispose();
    geoms.forEach((g) => g.dispose());
  }, [mat, geoms]);
  useFrame(() => {
    // Dim with the hall around an open painting, like the hall's own materials.
    mat.color.copy(WALL_LIGHT).multiplyScalar(rig.light);
    sheenScale.value = rig.light;
  });
  return (
    <>
      {geoms.map((g, i) => (
        <mesh key={i} geometry={g} material={mat} position={[0, 0, plane.z]} raycast={noRaycast} />
      ))}
    </>
  );
}
