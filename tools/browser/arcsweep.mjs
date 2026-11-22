// The opening arch's intrados, swept: shots from given poses with the screen position of given
// world points (web metres), so a script can crop along the arc; and a walk in small steps for
// frame-to-frame checks (flicker, sheen popping).
//   GALLERY_URL=http://localhost:5203/ node arcsweep.mjs <points.json> <out_dir>
// points.json: { "points": [[x, y, z], ...] }. Writes <out_dir>/<pose>.png and <out_dir>/points.json:
// { where: per pose, each point's [x, y] in image px (null when behind the camera); cams: per
// pose, the camera's view and projection matrices (column-major) and the image size }.
import fs from "node:fs";
import { open, viewBanner, leaveBanner, walkTo } from "./lib.mjs";

const [pointsFile, out] = process.argv.slice(2);
const { points } = JSON.parse(fs.readFileSync(pointsFile, "utf8"));
fs.mkdirSync(out, { recursive: true });
const DPR = 2;

/** Each point's position on the screenshot (image px), from the camera's own matrices. */
const project = (page, pts) => page.evaluate(([pts, dpr]) => {
  const cam = window.__gallery.rig.camera;
  cam.updateMatrixWorld();
  const V = cam.matrixWorldInverse.elements, Pm = cam.projectionMatrix.elements;
  const W = innerWidth, H = innerHeight;
  const mul = (m, v) => [0, 1, 2, 3].map((r) => m[r] * v[0] + m[4 + r] * v[1] + m[8 + r] * v[2] + m[12 + r] * v[3]);
  return pts.map((p) => {
    const c = mul(Pm, mul(V, [p[0], p[1], p[2], 1]));
    if (c[3] <= 0) return null;
    return [((c[0] / c[3] + 1) / 2) * W * dpr, ((1 - c[1] / c[3]) / 2) * H * dpr];
  });
}, [pts, DPR]);

const where = {}, cams = {};
const camera = (page) => page.evaluate((dpr) => {
  const cam = window.__gallery.rig.camera;
  cam.updateMatrixWorld();
  return { V: [...cam.matrixWorldInverse.elements], P: [...cam.projectionMatrix.elements], W: innerWidth * dpr, H: innerHeight * dpr };
}, DPR);
const shoot = async (page, name) => {
  await page.screenshot({ path: `${out}/${name}.png` });
  where[name] = await project(page, points);
  cams[name] = await camera(page);
};
const { browser, page } = await open({ w: 1512, h: 982, dpr: DPR });
for (const z of [0, -0.3, -0.6, -0.9]) {
  await walkTo(page, z);
  await shoot(page, `walk-z${z.toFixed(1)}`);
}
for (const side of ["left", "right"]) {
  await viewBanner(page, side);
  await shoot(page, `banner-${side}`);
  await leaveBanner(page);
}
// 21 frames from z 0 to -1.0 in 5 cm steps (walkTo kicks the on-demand canvas)
for (let i = 0; i <= 20; i++) {
  const z = -0.05 * i;
  await walkTo(page, z);
  await shoot(page, `step-${String(i).padStart(2, "0")}`);
}
fs.writeFileSync(`${out}/points.json`, JSON.stringify({ where, cams }));
await browser.close();
console.log("arc sweep in", out);
