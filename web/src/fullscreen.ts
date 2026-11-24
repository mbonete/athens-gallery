import { useSyncExternalStore } from "react";

/** A phone visit in fullscreen, held in landscape: the browser's bars go and the screen stops
 * turning. Browsers grant both only during a tap (user activation), never on a rotation, so the
 * taps that start a visit call this: the rotate gate's button (main.tsx) and the welcome card's
 * "Enter the gallery" (Intro.tsx; Maria 2026-11-24: rotating should give the fuller view too), and
 * the "Full screen" pill shown while a phone in landscape is not fullscreen (Intro.tsx).
 * Both are optional: iPhone browsers have no page fullscreen, and turning the phone by hand
 * always works. Call it from the tap's handler before anything else is awaited. */
export async function fullscreenLandscape() {
  try {
    if (!document.fullscreenElement && document.documentElement.requestFullscreen) {
      await document.documentElement.requestFullscreen({ navigationUI: "hide" });
    }
  } catch {
    // Refused (no activation, or not allowed here): the visit carries on with the browser's bars.
  }
  try {
    const orientation = screen.orientation as ScreenOrientation & { lock?: (value: "landscape") => Promise<void> };
    await orientation?.lock?.("landscape");
  } catch {
    // Locking needs fullscreen (or an installed app) and is missing in some browsers.
  }
}

function subscribe(onChange: () => void) {
  document.addEventListener("fullscreenchange", onChange);
  return () => document.removeEventListener("fullscreenchange", onChange);
}

/** Whether the page is fullscreen now (the visitor can leave at any time: back, or a drag from the top). */
export const useFullscreen = () => useSyncExternalStore(subscribe, () => !!document.fullscreenElement, () => false);
