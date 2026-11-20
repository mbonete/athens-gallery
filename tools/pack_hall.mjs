// Pack the baked hall for the web: KTX2 (Basis UASTC, mipmapped, Zstandard) textures and
// meshopt-compressed geometry, in one GLB.
// Usage: node tools/pack_hall.mjs <in.gltf> <out.glb> [uastc|etc1s]
// Needs `basisu` (Homebrew: basis_universal) and web/node_modules (gltf-transform, meshoptimizer).
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(path.resolve("web/package.json"));
const { NodeIO } = require("@gltf-transform/core");
const { ALL_EXTENSIONS, KHRTextureBasisu } = require("@gltf-transform/extensions");
const { dedup, prune, meshopt } = require("@gltf-transform/functions");
const { MeshoptEncoder } = require("meshoptimizer");

const [input, output, mode = "uastc"] = process.argv.slice(2);
await MeshoptEncoder.ready;
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ "meshopt.encoder": MeshoptEncoder });
const doc = await io.read(input);
doc.createExtension(KHRTextureBasisu).setRequired(true);
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "hall-ktx2-"));
const args = mode === "etc1s"
  ? ["-ktx2", "-q", "200", "-comp_level", "2", "-mipmap"]
  : ["-ktx2", "-uastc", "-uastc_level", "2", "-uastc_rdo_l", "1.0", "-mipmap", "-ktx2_zstandard_level", "18"];
for (const tex of doc.getRoot().listTextures()) {
  const name = path.basename(tex.getURI() || tex.getName() || "tex", ".png");
  const src = path.join(tmp, `${name}.png`);
  const dst = path.join(tmp, `${name}.ktx2`);
  fs.writeFileSync(src, tex.getImage());
  execFileSync("basisu", [...args, src, "-output_file", dst], { stdio: "ignore" });
  tex.setImage(fs.readFileSync(dst)).setMimeType("image/ktx2").setURI(`${name}.ktx2`);
  console.log(`${name}: ${(fs.statSync(src).size / 1e6).toFixed(2)} MB png -> ${(fs.statSync(dst).size / 1e6).toFixed(2)} MB ktx2 (${mode})`);
}
await doc.transform(dedup(), prune(), meshopt({ encoder: MeshoptEncoder, level: "medium", quantizeTexcoord: 16 }));
await io.write(output, doc);
console.log(`wrote ${output}: ${(fs.statSync(output).size / 1e6).toFixed(2)} MB`);
