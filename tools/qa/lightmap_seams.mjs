// Usage: tools/qa/run.sh lightmap_seams.mjs web/public/models/hall.glb out.json
// Every edge where two triangles meet at a smooth angle (< 35 deg) but the lightmap UVs (TEXCOORD_1)
// differ on the two sides: a place where the baked light can step. Positions in world metres.
import { NodeIO } from "@gltf-transform/core";
import { ALL_EXTENSIONS } from "@gltf-transform/extensions";
import { MeshoptDecoder } from "meshoptimizer";
import fs from "node:fs";
await MeshoptDecoder.ready;
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ "meshopt.decoder": MeshoptDecoder });
const doc = await io.read(process.argv[2]);
const out = [];
for (const node of doc.getRoot().listNodes()) {
  const mesh = node.getMesh(); if (!mesh) continue;
  const M = node.getWorldMatrix();
  for (const prim of mesh.listPrimitives()) {
    const P = prim.getAttribute("POSITION"), U = prim.getAttribute("TEXCOORD_1"), I = prim.getIndices();
    if (!P || !U || !I) continue;
    const mat = prim.getMaterial()?.getName() ?? "";
    const n = P.getCount(), pos = [], uv = [];
    const a = [0, 0, 0], b = [0, 0];
    for (let i = 0; i < n; i++) {
      P.getElement(i, a); const x = a[0], y = a[1], z = a[2];
      pos.push([M[0]*x+M[4]*y+M[8]*z+M[12], M[1]*x+M[5]*y+M[9]*z+M[13], M[2]*x+M[6]*y+M[10]*z+M[14]]);
      U.getElement(i, b); uv.push([b[0], b[1]]);
    }
    const key = (p) => p.map((v) => Math.round(v * 2000)).join(",");   // 0.5 mm
    const edges = new Map();
    const idx = I.getArray();
    for (let t = 0; t < idx.length; t += 3) {
      const v = [idx[t], idx[t + 1], idx[t + 2]];
      const [p0, p1, p2] = v.map((k) => pos[k]);
      const e1 = p1.map((q, i) => q - p0[i]), e2 = p2.map((q, i) => q - p0[i]);
      let nrm = [e1[1]*e2[2]-e1[2]*e2[1], e1[2]*e2[0]-e1[0]*e2[2], e1[0]*e2[1]-e1[1]*e2[0]];
      const L = Math.hypot(...nrm); if (L < 1e-12) continue; nrm = nrm.map((q) => q / L);
      for (const [i0, i1] of [[0, 1], [1, 2], [2, 0]]) {
        const ka = key(pos[v[i0]]), kb = key(pos[v[i1]]);
        const k = ka < kb ? ka + "|" + kb : kb + "|" + ka;
        const uvs = ka < kb ? [uv[v[i0]], uv[v[i1]]] : [uv[v[i1]], uv[v[i0]]];
        const rec = edges.get(k); if (!rec) edges.set(k, [{ uvs, nrm, p: [pos[v[i0]], pos[v[i1]]] }]); else rec.push({ uvs, nrm, p: [pos[v[i0]], pos[v[i1]]] });
      }
    }
    for (const [, r] of edges) {
      if (r.length !== 2) continue;
      const [A, B] = r;
      const cos = A.nrm[0]*B.nrm[0] + A.nrm[1]*B.nrm[1] + A.nrm[2]*B.nrm[2];
      if (cos < Math.cos(35 * Math.PI / 180)) continue;          // a real crease, not a smooth surface
      const d = Math.max(Math.abs(A.uvs[0][0]-B.uvs[0][0]), Math.abs(A.uvs[0][1]-B.uvs[0][1]), Math.abs(A.uvs[1][0]-B.uvs[1][0]), Math.abs(A.uvs[1][1]-B.uvs[1][1]));
      if (d < 1e-4) continue;
      const m = A.p[0].map((q, i) => (q + A.p[1][i]) / 2);
      const len = Math.hypot(...A.p[0].map((q, i) => q - A.p[1][i]));
      const mu = (s) => [(s.uvs[0][0]+s.uvs[1][0])/2, (s.uvs[0][1]+s.uvs[1][1])/2]; out.push({ mesh: node.getName(), mat, mid: m.map((q) => +q.toFixed(3)), len: +len.toFixed(4), ua: mu(A), ub: mu(B) });
    }
  }
}
fs.writeFileSync(process.argv[3], JSON.stringify(out));
console.log("smooth lightmap seams (edges):", out.length);
