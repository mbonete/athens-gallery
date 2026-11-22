// Pack the baked hall for the web (stage 4: light x detail).
// Usage: node tools/pack_hall.mjs <bake_dir> <out.glb>
// <bake_dir> holds hall.gltf from blender/scripts/bake.py, materials.json, lightmap_<group>.png
// and detail/<key>.png (tools/make_detail.py). For every material "<group>|<key>|<tint>":
//   baseColorTexture = detail tile <key> (TEXCOORD_0, repeat), baseColorFactor = tint,
//   occlusionTexture = the group's lightmap (TEXCOORD_1, clamp) -- the web reads it as lightMap.
// Textures go to KTX2: detail tiles as Basis ETC1S (small download, noisy textures hide its
// blocks; DETAIL_CODEC=uastc for sharper), lightmaps as UASTC (smooth gradients); all mipmapped.
// A few detail tiles are stored smaller than make_detail.py makes them (DETAIL_MAX).
// Geometry: meshopt; the detail UVs (TEXCOORD_0) as 16-bit with KHR_texture_transform.
// Needs `basisu` (Homebrew basis_universal) and web/node_modules.
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(path.resolve("web/package.json"));
const { NodeIO, TextureInfo } = require("@gltf-transform/core");
const { ALL_EXTENSIONS, KHRTextureBasisu, KHRTextureTransform } = require("@gltf-transform/extensions");
const { dedup, prune, meshopt } = require("@gltf-transform/functions");
const { MeshoptEncoder } = require("meshoptimizer");

const [dir, output] = process.argv.slice(2);
const detailCodec = process.env.DETAIL_CODEC || "etc1s";
await MeshoptEncoder.ready;
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ "meshopt.encoder": MeshoptEncoder });
const doc = await io.read(path.join(dir, "hall.gltf"));
doc.createExtension(KHRTextureBasisu).setRequired(true);
const materials = JSON.parse(fs.readFileSync(path.join(dir, "materials.json"), "utf8"));
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "hall-ktx2-"));
const ARGS = {
  etc1s: ["-ktx2", "-q", "255", "-comp_level", "2", "-mipmap"],
  uastc: ["-ktx2", "-uastc", "-uastc_level", "2", "-uastc_rdo_l", "1.0", "-mipmap", "-ktx2_zstandard_level", "18"],
};
// Detail tiles whose full resolution no view shows, stored at most this many px wide (the height
// follows): basisu resamples the tile (box filter, 2:1) before making its mips, so the tile keeps
// its look and loses its top level. relief_scroll: the facade's panels are never seen closer than
// 4.4 texels per pixel at DPR 1, 2.2 at DPR 2 (the perf-audit branch: reports/perf/REPORT.md), so
// at 512 px they still get a texel or more per pixel; 143 to 44 KiB.
const DETAIL_MAX = { relief_scroll: 512 };
const pngSize = (png) => { const b = fs.readFileSync(png); return [b.readUInt32BE(16), b.readUInt32BE(20)]; };
function ktx2(png, name, codec, maxWidth = Infinity) {
  const src = path.join(tmp, `${name}.png`), dst = path.join(tmp, `${name}.ktx2`);
  fs.copyFileSync(png, src);
  const [w, h] = pngSize(png);
  const resample = w > maxWidth ? ["-resample", String(maxWidth), String(Math.round((h * maxWidth) / w))] : [];
  execFileSync("basisu", [...ARGS[codec], ...resample, src, "-output_file", dst], { stdio: "ignore" });
  const out = fs.readFileSync(dst);
  const size = resample.length ? ` at ${resample[1]}x${resample[2]} (from ${w}x${h})` : "";
  console.log(`${name}: ${(fs.statSync(png).size / 1e6).toFixed(2)} MB png -> ${(out.length / 1e6).toFixed(2)} MB ktx2 (${codec})${size}`);
  return out;
}
// Detail tiles: swap the exporter's 4x4 placeholders for the real tiles.
const detailTex = {};
for (const tex of doc.getRoot().listTextures()) {
  const key = path.basename(tex.getURI() || tex.getName(), ".png").replace(/^detail_/, "");
  const png = path.join(dir, "detail", `${key}.png`);
  if (!fs.existsSync(png)) throw new Error(`no detail tile for ${key}`);
  const codec = key === "flat" ? "uastc" : detailCodec;
  tex.setImage(ktx2(png, `detail_${key}`, codec, DETAIL_MAX[key])).setMimeType("image/ktx2").setURI(`detail_${key}.ktx2`).setName(`detail_${key}`);
  detailTex[key] = tex;
}
// Lightmaps, one per group, attached as occlusion on TEXCOORD_1.
const lightTex = {};
for (const mat of doc.getRoot().listMaterials()) {
  const info = materials[mat.getName()];
  if (!info) continue;
  const g = info.group;
  if (!lightTex[g]) {
    lightTex[g] = doc.createTexture(`lightmap_${g}`).setImage(ktx2(path.join(dir, `lightmap_${g}.png`), `lightmap_${g}`, "uastc"))
      .setMimeType("image/ktx2").setURI(`lightmap_${g}.ktx2`);
  }
  mat.setBaseColorFactor([...info.tint, 1]);
  mat.setOcclusionTexture(lightTex[g]);
  mat.getOcclusionTextureInfo().setTexCoord(1)
    .setWrapS(TextureInfo.WrapMode.CLAMP_TO_EDGE).setWrapT(TextureInfo.WrapMode.CLAMP_TO_EDGE);
  mat.getBaseColorTextureInfo()?.setWrapS(TextureInfo.WrapMode.REPEAT).setWrapT(TextureInfo.WrapMode.REPEAT);
  mat.setMetallicFactor(0).setRoughnessFactor(1);
}
// Detail UVs (TEXCOORD_0: world-scaled, so far outside [0,1], which quantize() skips and leaves as
// float32, 40 % of the geometry) as normalized 16-bit over each material's own range, with that
// range in KHR_texture_transform on the detail texture (offset = min, scale = max - min); three's
// GLTFLoader applies it to the map. One range per material, since the transform lives on the
// material. The largest step is under 0.8 texel of a 1024 px tile, so the rounding is under 0.4.
const uvTransform = doc.createExtension(KHRTextureTransform);
const uvRange = new Map();
const uvPrims = [];
for (const mesh of doc.getRoot().listMeshes()) {
  for (const prim of mesh.listPrimitives()) {
    const uv = prim.getAttribute("TEXCOORD_0");
    const mat = prim.getMaterial();
    if (!uv || !mat?.getBaseColorTexture() || uv.getNormalized()) continue;
    // Only the detail tile reads TEXCOORD_0 (the lightmap reads TEXCOORD_1, set above).
    if (mat.getNormalTexture() || mat.getEmissiveTexture() || mat.getMetallicRoughnessTexture() || mat.getOcclusionTextureInfo()?.getTexCoord() === 0)
      throw new Error(`${mat.getName()}: another texture reads TEXCOORD_0`);
    const r = uvRange.get(mat) ?? { min: [Infinity, Infinity], max: [-Infinity, -Infinity] };
    const a = uv.getArray();
    for (let i = 0; i < a.length; i++) { const k = i & 1; r.min[k] = Math.min(r.min[k], a[i]); r.max[k] = Math.max(r.max[k], a[i]); }
    uvRange.set(mat, r);
    uvPrims.push(prim);
  }
}
let worstStep = 0;
for (const [mat, r] of uvRange) {
  r.scale = [0, 1].map((k) => r.max[k] - r.min[k] || 1);
  mat.getBaseColorTextureInfo().setExtension("KHR_texture_transform", uvTransform.createTransform().setOffset(r.min).setScale(r.scale));
  const size = mat.getBaseColorTexture().getSize() ?? [1024, 1024];
  worstStep = Math.max(worstStep, ...[0, 1].map((k) => (r.scale[k] / 65535) * size[k]));
}
for (const prim of uvPrims) {
  const uv = prim.getAttribute("TEXCOORD_0");
  const r = uvRange.get(prim.getMaterial());
  const a = uv.getArray();
  const q = new Uint16Array(a.length);
  for (let i = 0; i < a.length; i++) { const k = i & 1; q[i] = Math.round(((a[i] - r.min[k]) / r.scale[k]) * 65535); }
  prim.setAttribute("TEXCOORD_0", doc.createAccessor().setType("VEC2").setArray(q).setNormalized(true).setBuffer(uv.getBuffer()));
}
console.log(`TEXCOORD_0: 16-bit on ${uvPrims.length} primitives, ${uvRange.size} materials; largest step ${worstStep.toFixed(3)} texel`);
// Positions on one grid for the whole hall (quantizationVolume "scene"): with a grid per mesh, an
// edge shared by two meshes (the nave wall and the crossing arch's leg, in one plane) rounded
// differently on each side and opened a sub-pixel slit that flickered as a 1 px line at grazing
// angles (Maria, 2026-11-21). 16 bits over the hall: about 0.6 mm (the ground beyond the door,
// 400 m long, is drawn by the web, not packed here: with it a step was 4.3 mm, bake.py).
await doc.transform(dedup(), prune(), meshopt({
  encoder: MeshoptEncoder, level: "medium", quantizeTexcoord: 16, quantizePosition: 16, quantizationVolume: "scene",
}));
await io.write(output, doc);
console.log(`wrote ${output}: ${(fs.statSync(output).size / 1e6).toFixed(2)} MB`);
