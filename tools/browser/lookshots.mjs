// Shots of the walk turned (look.ts) to its limits, with the camera's matrices, so a script can
// say what the frame reaches: the front wall's top edge, the highest elevation in view.
//   GALLERY_URL=http://localhost:5203/ node lookshots.mjs <out_dir> [wide] [z,z,...]
// Without "wide": the default limits at each z. With "wide" (dev, ?look=wide): the full limits.
// For each z (web metres along the walk, 0 the start) it shoots at rest, then up, up-left and
// up-right at the limits. Writes <out>/<name>.png and <out>/cams.json ({name: {V, P, W, H, z,
// yaw, pitch}}, angles in degrees, yaw positive to the left).
import fs from "node:fs";
import { open, walkTo, URL } from "./lib.mjs";

const [out, wideArg, zArg] = process.argv.slice(2);
const wide = wideArg === "wide";
const zs = (zArg || "0").split(",").map(Number);
fs.mkdirSync(out, { recursive: true });
const DPR = 2;
const { browser, page, errors } = await open({ w: 1512, h: 982, dpr: DPR });
if (wide) {
  await page.goto(URL + "?look=wide");
  await page.waitForFunction(() => window.__gallery && window.__gallery.getState().ready, null, { timeout: 120000 });
  await page.waitForTimeout(1500);
}

const cams = {};
async function turnTo(yaw, pitch) {
  await page.evaluate(([y, p]) => {
    const L = window.__look;
    L.look.yaw = y;
    L.look.pitch = p;
    window.__gallery.rig.kick();
  }, [yaw, pitch]);
  await page.waitForTimeout(500);
  await page.evaluate(() => window.__gallery.rig.kick());
  await page.waitForTimeout(300);
}
async function shoot(name, z, yaw, pitch) {
  await turnTo(yaw, pitch);
  await page.screenshot({ path: `${out}/${name}.png` });
  cams[name] = await page.evaluate(([dpr, z, yaw, pitch]) => {
    const cam = window.__gallery.rig.camera;
    cam.updateMatrixWorld();
    return { V: [...cam.matrixWorldInverse.elements], P: [...cam.projectionMatrix.elements], W: innerWidth * dpr, H: innerHeight * dpr,
      z, yaw: (yaw * 180) / Math.PI, pitch: (pitch * 180) / Math.PI };
  }, [DPR, z, yaw, pitch]);
}

for (const z of zs) {
  await turnTo(0, 0);
  await walkTo(page, z);
  const lim = await page.evaluate(() => window.__look.limits());
  const tag = `z${z.toFixed(2)}${wide ? "-wide" : ""}`;
  await shoot(`${tag}-rest`, z, 0, 0);
  await shoot(`${tag}-up`, z, 0, lim.up);
  await shoot(`${tag}-upleft`, z, lim.yaw, lim.up);
  await shoot(`${tag}-upright`, z, -lim.yaw, lim.up);
  await turnTo(0, 0);
}
fs.writeFileSync(`${out}/cams.json`, JSON.stringify(cams));
await browser.close();
console.log("look shots in", out, errors.length ? errors : "");
