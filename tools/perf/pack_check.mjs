// Pixel check of a repacked hall.glb against another (tools/pack_hall.mjs changes): the same views
// drawn with each GLB, swapped in by request interception, then diffed with ImageMagick. Views: the
// start, mid-walk, the end of the walk, both entrance banners close up, and the walk's closest view
// of the facade's relief-scroll panels (found by their size on screen). A first GLB loaded twice
// gives the noise floor.
// Needs the dev server (its test hooks) and `npm i --no-save playwright-core` in web/.
// Usage: node tools/perf/pack_check.mjs <before.glb> <after.glb> <out dir>   (GALLERY_URL, default :5209)
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { createRequire } from "node:module";

const here = path.dirname(new globalThis.URL(import.meta.url).pathname);
const { chromium } = createRequire(path.resolve(here, "../../web/package.json"))("playwright-core");
const [before, after, out] = process.argv.slice(2);
const URL = process.env.GALLERY_URL || "http://127.0.0.1:5209/";
const W = 1600, H = 1000;
fs.mkdirSync(out, { recursive: true });
// The relief-scroll panels (facade|relief_scroll in the GLB), left one: world corners.
const PANEL = [[-5.65, 2.24, -10.89], [-4.46, 2.24, -10.89], [-4.46, 3.22, -10.89], [-5.65, 3.22, -10.89]];

const browser = await chromium.launch({ channel: "chrome", headless: true, args: ["--ignore-gpu-blocklist", "--use-angle=metal"] });
const shots = {};
for (const [variant, glb] of [["before", before], ["before-again", before], ["after", after]]) {
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
  page.on("pageerror", (e) => console.error(variant, "pageerror", e.message));
  const body = fs.readFileSync(glb);
  await page.route("**/models/hall.glb", (r) => r.fulfill({ body, contentType: "model/gltf-binary" }));
  await page.goto(URL);
  await page.waitForFunction(() => window.__gallery?.getState().ready && window.__banner, null, { timeout: 120000 });
  await page.waitForTimeout(2500);
  const mode = (m) => page.waitForFunction((m) => window.__gallery.getState().mode === m, m, { timeout: 20000 });
  const at = async (p) => {
    await page.evaluate((p) => { const r = window.__gallery.rig; r.progress = r.target = p; }, p);
    await page.waitForTimeout(700);
  };
  // The walk position where the left panel is largest on screen (all corners in front of the camera).
  const relief = await page.evaluate(async (panel) => {
    const { rig } = window.__gallery;
    const V = rig.camera.position.constructor;
    let best = { p: 0, area: 0 };
    for (let i = 0; i <= 100; i++) {
      const p = i / 250;
      rig.progress = rig.target = p;
      await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
      rig.camera.updateMatrixWorld();
      const s = panel.map(([x, y, z]) => new V(x, y, z).project(rig.camera));
      if (s.some((v) => v.z < -1 || v.z > 1 || Math.abs(v.x) > 1 || Math.abs(v.y) > 1)) continue;
      let a = 0;
      for (let k = 0; k < 4; k++) { const u = s[k], v = s[(k + 1) % 4]; a += u.x * v.y - v.x * u.y; }
      a = Math.abs(a) / 2;
      if (a > best.area) best = { p, area: a };
    }
    return best;
  }, PANEL);
  const views = [["start", () => at(0)], ["mid", () => at(0.5)], ["end", () => at(1)], ["relief", () => at(relief.p)]];
  for (const side of ["left", "right"]) views.push([`banner-${side}`, async () => {
    await at(0);
    await page.evaluate((s) => window.__banner.viewBanner(s), side);
    await mode("banner");
    await page.waitForTimeout(600);
  }]);
  for (const [name, go] of views) {
    await go();
    const f = path.join(out, `${variant}-${name}.png`);
    await page.screenshot({ path: f });
    (shots[name] ??= {})[variant] = f;
    if (name.startsWith("banner")) { await page.evaluate(() => window.__banner.leaveBanner()); await mode("walk"); }
  }
  if (variant === "before") console.log(`relief panel largest at walk ${relief.p.toFixed(3)}: ${((relief.area / 4) * W * H).toFixed(0)} px`);
  await page.close();
}
await browser.close();

// compare writes its metric to stderr (and exits 1 when the images differ).
const magick = (args) => { const r = spawnSync("magick", args, { encoding: "utf8" }); return `${r.stdout}${r.stderr}`; };
const num = (s) => s.trim().split(/\s+/)[0];
console.log(`view        pair                    PSNR dB   peak error   px > 1 %   px > 5 %   (of ${W * H})`);
for (const [name, v] of Object.entries(shots)) {
  for (const [a, b] of [["before", "before-again"], ["before", "after"]]) {
    const psnr = num(magick(["compare", "-metric", "PSNR", v[a], v[b], "null:"]));
    const pae = magick(["compare", "-metric", "PAE", v[a], v[b], "null:"]).trim();
    const ae1 = num(magick(["compare", "-metric", "AE", "-fuzz", "1%", v[a], v[b], "null:"]));
    const ae5 = num(magick(["compare", "-metric", "AE", "-fuzz", "5%", v[a], v[b], "null:"]));
    if (b === "after") magick(["compare", "-fuzz", "1%", v[a], v[b], path.join(out, `diff-${name}.png`)]);
    console.log(`${name.padEnd(12)}${`${a} / ${b}`.padEnd(24)}${psnr.padStart(8)}   ${pae.padEnd(22)} ${ae1.padStart(8)}   ${ae5.padStart(8)}`);
  }
}
