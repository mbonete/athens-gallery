// Review shots of the entrance arch on a running dev server (GALLERY_URL) into <out_dir>:
// the start view (1440 x 900, 1512 x 982, and 1440 x 900 at 2x), both banners' close-ups
// (1512 x 982 at 2x, 3400 x 1117 at 1x), and walking in (1512 x 982 at 2x) from z 0 to
// through the arch (web metres along the walk; the arch's face is at z -3.33).
//   GALLERY_URL=http://localhost:5203/ node shots.mjs ../../renders/x/after
import fs from "node:fs";
import { leaveBanner, open, viewBanner, walkTo } from "./lib.mjs";

const out = process.argv[2] || "shots";
fs.mkdirSync(out, { recursive: true });
const WALK = [0, -0.3, -0.6, -0.9, -1.5, -2.5, -3.1, -3.4, -3.8];

async function session(w, h, dpr, fn) {
  const { browser, page, errors } = await open({ w, h, dpr });
  await fn(page);
  if (errors.length) console.log(`  errors at ${w}x${h}@${dpr}:`, errors.slice(0, 3).join(" | "));
  await browser.close();
}

await session(1440, 900, 1, async (page) => {
  await page.screenshot({ path: `${out}/start-1440.png` });
});
await session(1440, 900, 2, async (page) => {
  await page.screenshot({ path: `${out}/start-1440-2x.png` });
});
await session(1512, 982, 1, async (page) => {
  await page.screenshot({ path: `${out}/start-1512.png` });
});
await session(1512, 982, 2, async (page) => {
  for (const side of ["left", "right"]) {
    await viewBanner(page, side);
    await page.screenshot({ path: `${out}/banner-${side}-1512-2x.png` });
    await leaveBanner(page);
  }
  for (const z of WALK) {
    await walkTo(page, z);
    await page.screenshot({ path: `${out}/walk-z${z.toFixed(1)}-1512-2x.png` });
  }
});
await session(3400, 1117, 1, async (page) => {
  for (const side of ["left", "right"]) {
    await viewBanner(page, side);
    await page.screenshot({ path: `${out}/banner-${side}-3400.png` });
    await leaveBanner(page);
  }
});
console.log("shots in", out);
