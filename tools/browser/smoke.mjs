// Smoke check of the hall on a running dev server (GALLERY_URL), desktop 1440 x 900:
// no page errors, the start view renders, the walk reaches the end, a painting opens and
// closes, the dome's look up and back, both banner close-ups and back.
//   GALLERY_URL=http://localhost:5203/ node smoke.mjs
import { canvasStats, leaveBanner, mode, open, viewBanner, waitMode, walkTo } from "./lib.mjs";

const results = [];
const ok = (name, pass, detail = "") => {
  results.push(pass);
  console.log(`${pass ? "PASS" : "FAIL"}  ${name}${detail ? "  - " + detail : ""}`);
};

const { browser, page, errors } = await open({ w: 1440, h: 900 });

// The start view renders: a full-screen shot of the hall compresses to far more than a blank one.
const start = await canvasStats(page);
ok("start view renders", start.bytes > 300000, `${(start.bytes / 1e6).toFixed(2)} MB png`);
ok("starts on the walk", (await mode(page)) === "walk");

// Both banner close-ups and back.
for (const side of ["left", "right"]) {
  const inView = await viewBanner(page, side);
  const back = inView && (await leaveBanner(page));
  ok(`banner close-up ${side} and back`, inView && back);
}

// A painting: walk near it, click it, back with Escape.
const st = await page.evaluate(() => {
  const s = window.__gallery.STATIONS.find((x) => x.side !== 0);
  return { slug: s.painting.slug, prog: window.__gallery.progressNear(s) };
});
await walkTo(page, -st.prog * (await page.evaluate(() => window.__gallery.TOTAL)));
const at = await page.evaluate((slug) => window.__gallery.screenOf(slug), st.slug);
let opened = false, closed = false;
if (at && at.z < 1) {
  await page.mouse.click(at.x, at.y);
  opened = await waitMode(page, "detail", 15000);
  await page.waitForTimeout(800);
  await page.keyboard.press("Escape");
  closed = await waitMode(page, "walk", 15000);
}
ok(`painting ${st.slug} opens and closes`, opened && closed, at ? `tap at ${Math.round(at.x)},${Math.round(at.y)}` : "not on screen");

// The dome: look up and back down.
await page.evaluate(() => window.__dome.lookUp());
const up = await waitMode(page, "dome", 15000);
await page.evaluate(() => window.__dome.lookDown());
const down = await waitMode(page, "walk", 15000);
ok("dome look up and down", up && down);

// The walk reaches its end.
await walkTo(page, -1000);
const prog = await page.evaluate(() => window.__gallery.rig.progress);
ok("walk to the end", Math.abs(prog - 1) < 1e-4, `progress ${prog.toFixed(5)}`);

ok("no page or console errors", errors.length === 0, errors.slice(0, 3).join(" | "));
await browser.close();
const n = results.filter(Boolean).length;
console.log(`smoke: ${n}/${results.length} passed`);
process.exit(n === results.length ? 0 : 1);
