// Usage: tools/qa/run.sh lightmap_islands.mjs web/public/models/hall.glb '{"label":[x0,x1,y0,y1,z0,z1]}' (web metres)
// Lightmap islands of the triangles inside a world box: union-find over edges whose two ends share
// TEXCOORD_1, across all the materials of a group's mesh (one island may span a coffer's rib, riser,
// tread and panel materials). Prints island count and sizes (in atlas texels) per box.
import { NodeIO } from "@gltf-transform/core";
import { ALL_EXTENSIONS } from "@gltf-transform/extensions";
import { MeshoptDecoder } from "meshoptimizer";
await MeshoptDecoder.ready;
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ "meshopt.decoder": MeshoptDecoder });
const doc = await io.read(process.argv[2]);
const boxes = JSON.parse(process.argv[3]);
// Each group's atlas size, from its lightmap's KTX2 header (pixelWidth, pixelHeight at bytes 20, 24),
// so the sizes follow any rebake (a fixed table went stale whenever an atlas grew).
const atlas = {};
for (const mat of doc.getRoot().listMaterials()) {
  const tex = mat.getOcclusionTexture(); const img = tex?.getImage(); if (!img) continue;
  const g = (tex.getName() || tex.getURI()).replace(/^lightmap_/, "").replace(/\.ktx2$/, "");
  const dv = new DataView(img.buffer, img.byteOffset, img.byteLength);
  atlas[g] = dv.getUint32(20, true) * dv.getUint32(24, true);
}
for (const [label, bx] of Object.entries(boxes)) {
  let tris = 0, comps = 0; const sizes = [];
  for (const node of doc.getRoot().listNodes()) {
    const mesh = node.getMesh(); if (!mesh) continue;
    const g = node.getName().split("_")[1]; const A2 = atlas[g] || 1024 * 1024;
    const M = node.getWorldMatrix();
    const parent = new Map(); const find = (k) => { while (parent.get(k) !== k) { parent.set(k, parent.get(parent.get(k))); k = parent.get(k); } return k; };
    const uni = (p, q) => { p = find(p); q = find(q); if (p !== q) parent.set(p, q); };
    const triList = [];
    for (const prim of mesh.listPrimitives()) {
      const P = prim.getAttribute("POSITION"), U = prim.getAttribute("TEXCOORD_1"), I = prim.getIndices(); if (!P || !U || !I) continue;
      const idx = I.getArray(), a = [0,0,0], b = [0,0];
      const wp = (i) => { P.getElement(i, a); const [x,y,z] = a; return [M[0]*x+M[4]*y+M[8]*z+M[12], M[1]*x+M[5]*y+M[9]*z+M[13], M[2]*x+M[6]*y+M[10]*z+M[14]]; };
      const uvk = (i) => { U.getElement(i, b); return Math.round(b[0]*1e5)+","+Math.round(b[1]*1e5); };
      for (let t = 0; t < idx.length; t += 3) {
        const v = [idx[t], idx[t+1], idx[t+2]]; const ps = v.map(wp);
        const c = [0,1,2].map((k) => (ps[0][k]+ps[1][k]+ps[2][k])/3);
        if (c[0] < bx[0] || c[0] > bx[1] || c[1] < bx[2] || c[1] > bx[3] || c[2] < bx[4] || c[2] > bx[5]) continue;
        const ks = v.map(uvk); ks.forEach((k) => { if (!parent.has(k)) parent.set(k, k); });
        uni(ks[0], ks[1]); uni(ks[1], ks[2]);
        U.getElement(v[0], b); const u0 = [...b]; U.getElement(v[1], b); const u1 = [...b]; U.getElement(v[2], b); const u2 = [...b];
        const area = Math.abs((u1[0]-u0[0])*(u2[1]-u0[1]) - (u2[0]-u0[0])*(u1[1]-u0[1])) / 2 * A2;
        triList.push([ks[0], area]);
      }
    }
    const comp = new Map();
    for (const [k, area] of triList) { const r = find(k); comp.set(r, (comp.get(r) || 0) + area); }
    tris += triList.length; comps += comp.size; sizes.push(...comp.values());
  }
  sizes.sort((p, q) => p - q);
  const q = (f) => sizes.length ? sizes[Math.floor(f * (sizes.length - 1))].toFixed(0) : "-";
  console.log(label.padEnd(28), "triangles", String(tris).padStart(6), "islands", String(comps).padStart(5), "texels per island: median", q(0.5), " 10%", q(0.1), " 90%", q(0.9), " under 50 texels:", sizes.filter((s) => s < 50).length);
}
