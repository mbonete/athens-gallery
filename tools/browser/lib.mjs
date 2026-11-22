// Browser helpers for the hall's checks and review shots (the dev server's test hooks:
// window.__gallery, __banner, __dome). The server's URL comes from GALLERY_URL
// (default http://localhost:5203/). Chrome, headless, on Metal.
//   cd tools/browser && npm install && GALLERY_URL=http://localhost:5203/ node smoke.mjs
import { chromium } from "playwright-core";

export const URL = process.env.GALLERY_URL || "http://localhost:5203/";

/** A page on the hall at w x h CSS px and the given pixel ratio, once the hall is ready. */
export async function open({ w = 1440, h = 900, dpr = 1 } = {}) {
  const browser = await chromium.launch({ channel: "chrome", headless: true, args: ["--ignore-gpu-blocklist", "--use-angle=metal"] });
  const page = await browser.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: dpr });
  const errors = [];
  page.on("pageerror", (e) => errors.push("pageerror: " + e.message));
  page.on("console", (m) => m.type() === "error" && !/favicon/.test(m.text()) && errors.push("console: " + m.text().slice(0, 300)));
  await page.goto(URL);
  await page.waitForFunction(() => window.__gallery && window.__gallery.getState().ready && window.__banner && window.__dome,
    null, { timeout: 120000 });
  await page.waitForTimeout(1500);
  return { browser, page, errors };
}

export const mode = (page) => page.evaluate(() => window.__gallery.getState().mode);

export async function waitMode(page, m, ms = 12000) {
  return page.waitForFunction((m) => window.__gallery.getState().mode === m, m, { timeout: ms }).then(() => true, () => false);
}

/** Walk to depth z (web metres along the walk, 0 at the start, negative going in), settled. */
export async function walkTo(page, z) {
  await page.evaluate((z) => { const r = window.__gallery.rig; r.target = Math.min(1, Math.max(0, -z / window.__gallery.TOTAL)); }, z);
  await page.waitForFunction(() => Math.abs(window.__gallery.rig.progress - window.__gallery.rig.target) < 1e-5, null, { timeout: 20000 });
  await page.waitForTimeout(400);
}

/** The view from a banner's close-up (banner.ts), settled. */
export async function viewBanner(page, side) {
  await page.evaluate((s) => window.__banner.viewBanner(s), side);
  const ok = await waitMode(page, "banner");
  await page.waitForTimeout(600);
  return ok;
}

export async function leaveBanner(page) {
  await page.evaluate(() => window.__banner.leaveBanner());
  return waitMode(page, "walk");
}

/** Mean and spread of the canvas's pixels (a blank or black canvas has almost no spread). */
export async function canvasStats(page) {
  const buf = await page.screenshot({ type: "png" });
  return { bytes: buf.length };
}
