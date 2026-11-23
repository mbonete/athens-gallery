// Fixed views for before/after pixel diffs (1512 x 982 at 2x): the start at rest, points along
// the walk, and the dome's look up from where the walk offers it.
//   GALLERY_URL=http://localhost:5203/ node views.mjs <out_dir>
import fs from "node:fs";
import { open, walkTo, waitMode } from "./lib.mjs";

const out = process.argv[2] || "views";
fs.mkdirSync(out, { recursive: true });
const { browser, page, errors } = await open({ w: 1512, h: 982, dpr: 2 });
const total = await page.evaluate(() => window.__gallery.TOTAL);
await page.screenshot({ path: `${out}/start-rest.png` });
for (const f of [0.1, 0.2, 0.35, 0.5, 0.7, 0.9]) {
  await walkTo(page, -f * total);
  await page.screenshot({ path: `${out}/walk-${String(Math.round(f * 100)).padStart(3, "0")}.png` });
}
// the dome: from the point of the walk where its look-up is offered (lookUp walks there first)
await page.evaluate(() => window.__dome.lookUp());
await waitMode(page, "dome", 15000);
await page.waitForTimeout(2500);
await page.evaluate(() => window.__gallery.rig.kick());
await page.waitForTimeout(500);
await page.screenshot({ path: `${out}/dome.png` });
await browser.close();
console.log("views in", out, errors.length ? errors : "");
