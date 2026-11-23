// Usage: tools/qa/run.sh lightmap_overlaps.mjs web/public/models/hall.glb
// Rasterises every triangle's light-map UVs (TEXCOORD_1) into its group's atlas grid and counts
// texels claimed by two or more triangles that are not neighbours: two surfaces baked into the
// same texels, so one shows the other's light.
import { NodeIO } from "@gltf-transform/core";
import { ALL_EXTENSIONS } from "@gltf-transform/extensions";
import { MeshoptDecoder } from "meshoptimizer";
await MeshoptDecoder.ready;
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ "meshopt.decoder": MeshoptDecoder });
const doc = await io.read(process.argv[2]);
const size = {};
for (const t of doc.getRoot().listTextures()) { const n = t.getName() || t.getURI(); const m = /lightmap_(\w+)/.exec(n); if (m) { const s = t.getSize(); if (s) size[m[1]] = s; } }
const groups = {};
for (const node of doc.getRoot().listNodes()) {
  const mesh = node.getMesh(); if (!mesh) continue;
  const g = node.getName().split("_")[1]; const [W, H] = size[g] || [1024, 1024];
  const grid = groups[g] ??= { W, H, owner: new Int32Array(W * H).fill(-1), clash: new Uint8Array(W * H), tri: 0, pos: [] };
  const M = node.getWorldMatrix();
  for (const prim of mesh.listPrimitives()) {
    const P = prim.getAttribute("POSITION"), U = prim.getAttribute("TEXCOORD_1"), I = prim.getIndices(); if (!P || !U || !I) continue;
    const idx = I.getArray(), b = [0, 0], a = [0, 0, 0];
    for (let t = 0; t < idx.length; t += 3) {
      const id = grid.tri++;
      const uv = [0, 1, 2].map((k) => { U.getElement(idx[t + k], b); return [b[0] * W, b[1] * H]; });
      P.getElement(idx[t], a); grid.pos[id] = [M[0]*a[0]+M[4]*a[1]+M[8]*a[2]+M[12], M[1]*a[0]+M[5]*a[1]+M[9]*a[2]+M[13], M[2]*a[0]+M[6]*a[1]+M[10]*a[2]+M[14]];
      const xs = uv.map((p) => p[0]), ys = uv.map((p) => p[1]);
      const x0 = Math.max(0, Math.floor(Math.min(...xs))), x1 = Math.min(W - 1, Math.ceil(Math.max(...xs)));
      const y0 = Math.max(0, Math.floor(Math.min(...ys))), y1 = Math.min(H - 1, Math.ceil(Math.max(...ys)));
      const [p0, p1, p2] = uv;
      const area = (p1[0]-p0[0])*(p2[1]-p0[1]) - (p2[0]-p0[0])*(p1[1]-p0[1]); if (Math.abs(area) < 1e-9) continue;
      for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) {
        const px = x + 0.5, py = y + 0.5;
        const w0 = ((p1[0]-px)*(p2[1]-py) - (p2[0]-px)*(p1[1]-py)) / area, w1 = ((p2[0]-px)*(p0[1]-py) - (p0[0]-px)*(p2[1]-py)) / area, w2 = 1 - w0 - w1;
        if (w0 < 0.02 || w1 < 0.02 || w2 < 0.02) continue;          // texel centre well inside the triangle
        const k = y * W + x;
        if (grid.owner[k] === -1) grid.owner[k] = id;
        else if (grid.owner[k] !== id) {
          const q = grid.pos[grid.owner[k]], r = grid.pos[id];
          if (Math.hypot(q[0]-r[0], q[1]-r[1], q[2]-r[2]) > 0.5) grid.clash[k] = 1;   // not a neighbour sharing an edge
        }
      }
    }
  }
}
for (const [g, d] of Object.entries(groups)) {
  let n = 0; for (const c of d.clash) n += c;
  console.log(g.padEnd(9), `${d.W}x${d.H}`, "texels claimed by two distant surfaces:", n);
}
