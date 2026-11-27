// Phone regression check on a running dev server (GALLERY_URL): portrait stays on the lightweight
// rotate gate, landscape starts the gallery, one finger looks, and a two-finger spread walks without
// also turning the view.
//   GALLERY_URL=http://127.0.0.1:5199/ node phone.mjs
import { chromium } from "playwright-core";
import { URL } from "./lib.mjs";

const results = [];
const ok = (name, pass, detail = "") => {
  results.push(pass);
  console.log(`${pass ? "PASS" : "FAIL"}  ${name}${detail ? "  - " + detail : ""}`);
};

const browser = await chromium.launch({
  channel: "chrome",
  headless: true,
  args: ["--ignore-gpu-blocklist", "--use-angle=metal"],
});
const context = await browser.newContext({
  viewport: { width: 390, height: 844 },
  deviceScaleFactor: 2,
  hasTouch: true,
  isMobile: true,
  // The gallery follows the browser's language (web/src/i18n.ts); the checks below use the English names.
  locale: "en-US",
});
const page = await context.newPage();
const errors = [];
const requests = [];
page.on("pageerror", (e) => errors.push("pageerror: " + e.message));
page.on("console", (m) => m.type() === "error" && !/favicon/.test(m.text()) && errors.push("console: " + m.text().slice(0, 300)));
page.on("request", (r) => requests.push(r.url()));

await page.goto(URL);
await page.locator(".rotate-phone").waitFor({ state: "visible" });
ok("portrait shows the landscape gate", await page.locator(".rotate-phone").isVisible());
ok("portrait does not mount the gallery", (await page.locator(".stage").count()) === 0);
ok("portrait does not request the hall", !requests.some((u) => /\/models\/hall\.glb(?:\?|$)/.test(u)));

await page.setViewportSize({ width: 844, height: 390 });
await page.waitForFunction(() => window.__gallery?.getState().ready && window.__look);
await page.locator(".rotate-phone").waitFor({ state: "detached" });
ok("rotation starts the gallery", (await page.locator(".stage canvas").count()) === 1);
// The phone's welcome card (Intro.tsx) opens over the hall at the start; enter as a visitor would.
const intro = page.locator(".phone-intro");
ok("landscape opens the welcome card", await intro.isVisible());
await intro.getByRole("button", { name: "Enter the gallery" }).tap();
await intro.waitFor({ state: "detached" });

const cdp = await context.newCDPSession(page);
const touch = (type, points = []) => cdp.send("Input.dispatchTouchEvent", {
  type,
  touchPoints: points.map(({ id, x, y }) => ({ id, x, y, radiusX: 1, radiusY: 1, force: 1 })),
});

// A real swipe is many small moves. The first one past the slop starts the turn; every later one
// must keep turning (the turn once stopped after its first move: Maria, "I have to tap and drag
// 10 times to move to one side").
await touch("touchStart", [{ id: 1, x: 300, y: 210 }]);
const yaws = [];
for (let x = 312; x <= 420; x += 12) {
  await touch("touchMove", [{ id: 1, x, y: 210 }]);
  yaws.push(await page.evaluate(() => window.__look.look.yaw));
}
await touch("touchEnd");
const firstYaw = yaws[0], dragYaw = yaws[yaws.length - 1];
ok("one-finger drag looks around", Math.abs(firstYaw) > 0.02, `yaw ${firstYaw.toFixed(3)} after the first move`);
ok("one-finger drag keeps turning to the end of the swipe", Math.abs(dragYaw) > Math.abs(firstYaw) * 4,
  `yaw ${firstYaw.toFixed(3)} -> ${dragYaw.toFixed(3)} over ${yaws.length} moves`);

await page.evaluate(() => window.__look.recentre(0.01));
await page.waitForFunction(() => Math.abs(window.__look.look.yaw) < 1e-4 && Math.abs(window.__look.look.pitch) < 1e-4);
const beforeWalk = await page.evaluate(() => window.__gallery.rig.target);
// Begin as a one-finger look, then add a finger: this is the important handoff, not merely a pinch
// that starts with two fingers already down.
await touch("touchStart", [{ id: 2, x: 370, y: 210 }]);
await touch("touchMove", [{ id: 2, x: 400, y: 210 }]);
const lookBeforeHandoff = await page.evaluate(() => Math.hypot(window.__look.look.yaw, window.__look.look.pitch));
await touch("touchStart", [{ id: 2, x: 400, y: 210 }, { id: 3, x: 474, y: 210 }]);
const handedOff = await page.evaluate(() => !window.__look.dragging);
await touch("touchMove", [{ id: 2, x: 320, y: 210 }, { id: 3, x: 524, y: 210 }]);
await page.waitForTimeout(80);
const afterPinch = await page.evaluate(() => ({
  target: window.__gallery.rig.target,
  yaw: window.__look.look.yaw,
  pitch: window.__look.look.pitch,
}));
await touch("touchEnd");
ok("second finger cancels one-finger look", handedOff);
ok("two-finger spread walks", afterPinch.target > beforeWalk, `${beforeWalk.toFixed(3)} -> ${afterPinch.target.toFixed(3)}`);
ok("two-finger spread recentres instead of looking", Math.hypot(afterPinch.yaw, afterPinch.pitch) <= lookBeforeHandoff);

// A short touch still reaches picking after the one-finger drag behavior was added.
const tap = await page.evaluate(() => {
  const station = window.__gallery.STATIONS.find((s) => s.side !== 0);
  const progress = window.__gallery.progressNear(station);
  const r = window.__gallery.rig;
  r.progress = r.target = progress;
  r.kick();
  return station.painting.slug;
});
await page.evaluate(() => window.__look.recentre(0.01));
await page.waitForTimeout(100);
const at = await page.evaluate((slug) => window.__gallery.screenOf(slug), tap);
let opened = false, closed = false;
if (at && at.z > -1 && at.z < 1 && at.x >= 0 && at.x <= 844 && at.y >= 0 && at.y <= 390) {
  await touch("touchStart", [{ id: 4, x: at.x, y: at.y }]);
  await touch("touchEnd");
  opened = await page.waitForFunction(() => window.__gallery.getState().mode === "detail", null, { timeout: 15000 }).then(() => true, () => false);
  await page.keyboard.press("Escape");
  closed = await page.waitForFunction(() => window.__gallery.getState().mode === "walk", null, { timeout: 15000 }).then(() => true, () => false);
}
ok("short touch opens and closes a painting", opened && closed, at ? tap : "painting not on screen");

// Zooming in on a painting the view is turned to face opens it (Maria, 2026-11-27); looking straight
// ahead, the same spread over it walks. A deeper side painting, so the turn isn't held to the entrance's.
const aside = await page.evaluate(() => {
  const g = window.__gallery;
  const station = g.STATIONS.filter((s) => s.side !== 0)[2];
  g.rig.progress = g.rig.target = g.progressNear(station);
  g.rig.kick();
  return station.painting.slug;
});
/** Turn the view to face the painting (as far as the limits allow); the turn in degrees. */
const faceIt = (slug) => page.evaluate((slug) => {
  const { rig } = window.__gallery, L = window.__look;
  const m = rig.paintingMeshes.get(slug);
  m.updateWorldMatrix(true, false);
  const e = m.matrixWorld.elements;
  const yaw = Math.atan2(-(e[12] - rig.pose.x), -(e[14] - rig.pose.z)) - rig.pose.yaw;
  const lim = L.limits().yaw;
  L.look.yaw = Math.max(-lim, Math.min(lim, yaw));
  L.look.pitch = 0;
  rig.kick();
  return (L.look.yaw * 180) / Math.PI;
}, slug);
/** Straight ahead and standing still: the turn recentred, the walk's glide arrived. */
const settle = async () => {
  await page.evaluate(() => window.__look.recentre(0.01));
  await page.waitForFunction(() => !window.__look.easing && Math.abs(window.__look.look.yaw) < 1e-4 &&
    window.__gallery.rig.progress === window.__gallery.rig.target);
  await page.waitForTimeout(100);
};
const toStation = (slug) => page.evaluate((slug) => {
  const g = window.__gallery;
  const station = g.STATIONS.find((s) => s.painting.slug === slug);
  g.rig.progress = g.rig.target = g.progressNear(station);
  g.rig.kick();
}, slug);
/** Two fingers centred on (x, y), from `from` px apart to `to` px apart in small moves. */
const pinch = async (x, y, from, to, id = 10) => {
  await touch("touchStart", [{ id, x: x - from / 2, y }, { id: id + 1, x: x + from / 2, y }]);
  for (let i = 1; i <= 8; i++) {
    const w = from + ((to - from) * i) / 8;
    await touch("touchMove", [{ id, x: x - w / 2, y }, { id: id + 1, x: x + w / 2, y }]);
  }
  await touch("touchEnd");
};
const onScreen = (p) => p && p.z > -1 && p.z < 1 && p.x >= 60 && p.x <= 784 && p.y >= 20 && p.y <= 370;

await settle();
const ahead = await page.evaluate((slug) => window.__gallery.screenOf(slug), aside);
const aheadFrom = await page.evaluate(() => window.__gallery.rig.target);
if (onScreen(ahead)) await pinch(ahead.x, ahead.y, 80, 140);
await page.waitForTimeout(80);
const aheadAfter = await page.evaluate(() => ({ target: window.__gallery.rig.target, mode: window.__gallery.getState().mode }));
ok("straight ahead, a spread over a painting walks", aheadAfter.mode === "walk" && aheadAfter.target > aheadFrom,
  onScreen(ahead) ? `${aheadFrom.toFixed(3)} -> ${aheadAfter.target.toFixed(3)}, ${aheadAfter.mode}` : "painting not on screen");

await toStation(aside);
await settle();
const turnBack = await faceIt(aside);
await page.waitForTimeout(100);
const facedBack = await page.evaluate((slug) => window.__gallery.screenOf(slug), aside);
const backFrom = await page.evaluate(() => window.__gallery.rig.target);
if (onScreen(facedBack)) await pinch(facedBack.x, facedBack.y, 140, 70);
await page.waitForTimeout(80);
const backAfter = await page.evaluate(() => ({ target: window.__gallery.rig.target, mode: window.__gallery.getState().mode }));
ok("turned to a painting, a pinch still walks back", backAfter.mode === "walk" && backAfter.target < backFrom,
  `turned ${turnBack.toFixed(0)} deg, ${backFrom.toFixed(3)} -> ${backAfter.target.toFixed(3)}, ${backAfter.mode}`);

await toStation(aside);
await settle();
const turn = await faceIt(aside);
await page.waitForTimeout(100);
const faced = await page.evaluate((slug) => window.__gallery.screenOf(slug), aside);
const facedFrom = await page.evaluate(() => window.__gallery.rig.target);
let walkedUp = false, zoomOpened = false, zoomClosed = false;
if (onScreen(faced)) {
  await pinch(faced.x, faced.y, 80, 140);
  walkedUp = await page.evaluate((slug) => {
    const s = window.__gallery.getState();
    return s.mode !== "walk" && s.active?.slug === slug;
  }, aside);
  zoomOpened = await page.waitForFunction(() => window.__gallery.getState().mode === "detail", null, { timeout: 15000 }).then(() => true, () => false);
  await page.keyboard.press("Escape");
  zoomClosed = await page.waitForFunction(() => window.__gallery.getState().mode === "walk", null, { timeout: 15000 }).then(() => true, () => false);
}
const facedAfter = await page.evaluate(() => window.__gallery.rig.target);
ok("turned to a painting, a spread over it opens it", walkedUp && zoomOpened && zoomClosed,
  onScreen(faced) ? `${aside}, turned ${turn.toFixed(0)} deg` : `painting not on screen after turning ${turn.toFixed(0)} deg`);
ok("opening it by spreading walks nothing first", Math.abs(facedAfter - facedFrom) < 1e-6, `${facedFrom.toFixed(4)} -> ${facedAfter.toFixed(4)}`);

const place = await page.evaluate(() => window.__gallery.rig.target);
await page.setViewportSize({ width: 390, height: 844 });
await page.locator(".rotate-phone").waitFor({ state: "visible" });
const preserved = await page.evaluate(() => ({
  target: window.__gallery.rig.target,
  inert: document.querySelector(".gallery-shell")?.inert,
  hidden: document.querySelector(".gallery-shell")?.getAttribute("aria-hidden"),
}));
ok("portrait gate preserves a started visit", (await page.locator(".stage").count()) === 1 && Math.abs(preserved.target - place) < 1e-6);
ok("portrait gate makes the retained gallery inaccessible", preserved.inert && preserved.hidden === "true");
ok("no page or console errors", errors.length === 0, errors.slice(0, 3).join(" | "));

await browser.close();
console.log(`phone: ${results.filter(Boolean).length}/${results.length} passed`);
process.exit(results.every(Boolean) ? 0 : 1);
