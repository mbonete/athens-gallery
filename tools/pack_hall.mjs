// Pack the baked hall for the web (stage 4: light x detail).
// Usage: node tools/pack_hall.mjs <bake_dir> <out.glb>
// <bake_dir> holds hall.gltf from blender/scripts/bake.py, materials.json, lightmap_<group>.png
// and detail/<key>.png (tools/make_detail.py). For every material "<group>|<key>|<tint>":
//   baseColorTexture = detail tile <key> (TEXCOORD_0, repeat), baseColorFactor = tint,
//   occlusionTexture = the group's lightmap (TEXCOORD_1, clamp) -- the web reads it as lightMap.
// Textures go to KTX2: detail tiles as Basis ETC1S (small download, noisy textures hide its
// blocks; DETAIL_CODEC=uastc for sharper), lightmaps as UASTC (smooth gradients); all mipmapped.
// Geometry: meshopt. Needs `basisu` (Homebrew basis_universal) and web/node_modules.
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(path.resolve("web/package.json"));
const { NodeIO, TextureInfo } = require("@gltf-transform/core");
const { ALL_EXTENSIONS, KHRTextureBasisu } = require("@gltf-transform/extensions");
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
function ktx2(png, name, codec) {
  const src = path.join(tmp, `${name}.png`), dst = path.join(tmp, `${name}.ktx2`);
  fs.copyFileSync(png, src);
  execFileSync("basisu", [...ARGS[codec], src, "-output_file", dst], { stdio: "ignore" });
  const out = fs.readFileSync(dst);
  console.log(`${name}: ${(fs.statSync(png).size / 1e6).toFixed(2)} MB png -> ${(out.length / 1e6).toFixed(2)} MB ktx2 (${codec})`);
  return out;
}
// Detail tiles: swap the exporter's 4x4 placeholders for the real tiles.
const detailTex = {};
for (const tex of doc.getRoot().listTextures()) {
  const key = path.basename(tex.getURI() || tex.getName(), ".png").replace(/^detail_/, "");
  const png = path.join(dir, "detail", `${key}.png`);
  if (!fs.existsSync(png)) throw new Error(`no detail tile for ${key}`);
  const codec = key === "flat" ? "uastc" : detailCodec;
  tex.setImage(ktx2(png, `detail_${key}`, codec)).setMimeType("image/ktx2").setURI(`detail_${key}.ktx2`).setName(`detail_${key}`);
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
