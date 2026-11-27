import { useEffect, useState } from "react";
import { fullscreenLandscape, useFullscreen } from "./fullscreen";
import { Expand } from "./icons";
import { useStore } from "./store";

const TOUCH = typeof matchMedia !== "undefined" && matchMedia("(pointer: coarse)").matches;
const PHONE_LANDSCAPE = typeof matchMedia !== "undefined" &&
  matchMedia("(pointer: coarse) and (orientation: landscape) and (max-height: 600px)").matches;

/** How to visit, for the device in hand: the same words as the right banner (Banners.tsx). */
const HOW: [string, string][] = TOUCH
  ? [
      ["Walk", "Spread two fingers; pinch to walk back"],
      ["Look around", "Touch the hall and slide one finger left, right, up or down"],
      ["A painting", "Tap it to walk up; pinch to zoom"],
      ["The dome", "Tap it to look up"],
    ]
  : [
      ["Walk", "Scroll, or pinch on a trackpad"],
      ["Look around", "Click and drag"],
      ["A painting", "Click it to walk up, again to zoom; drag to move across it"],
      ["The dome", "Click it to look up"],
      ["Keys", "Arrows to walk; Tab and Enter open a painting"],
    ];

/** The exhibition's title and how to visit. Desktop visitors read them on the two banners in the
 * hall. On a landscape phone those tall banners cannot make body text legible even when they fill
 * the screen vertically, so the same content is a crisp HTML welcome card; tapping either banner
 * opens it again (banner.ts). */
export function Intro() {
  const [open, setOpen] = useState(PHONE_LANDSCAPE);
  const full = useFullscreen();
  const walking = useStore((s) => s.mode === "walk");

  useEffect(() => {
    if (!PHONE_LANDSCAPE) return;
    const show = () => setOpen(true);
    window.addEventListener("phoneintro", show);
    return () => window.removeEventListener("phoneintro", show);
  }, []);

  // The welcome card shows once a visit; a visitor who leaves fullscreen (or rotates without
  // entering it) gets it back from this pill, while walking (Maria, 2026-11-24).
  if (PHONE_LANDSCAPE && !open) {
    if (full || !walking || !document.fullscreenEnabled) return null;
    return (
      <button type="button" className="close fullscreen-pill" onClick={() => void fullscreenLandscape()}>
        <Expand />Full screen
      </button>
    );
  }

  // A phone turned by hand shows the browser's bars; the tap that enters is the first moment the
  // browser allows fullscreen (fullscreen.ts). Not awaited: the card closes at once.
  const enter = () => {
    void fullscreenLandscape();
    setOpen(false);
  };

  return (
    <header className={PHONE_LANDSCAPE ? "phone-intro" : "visually-hidden"}
      aria-labelledby={PHONE_LANDSCAPE ? "phone-intro-title" : undefined}>
      <div className="phone-intro-about">
        <h1 id={PHONE_LANDSCAPE ? "phone-intro-title" : undefined}>Studiolo</h1>
        <p>
        Nine favourite paintings, chosen by Maria Bonete, hung in the architecture of Raphael’s{" "}
        <cite>School of Athens</cite>.
        </p>
        <p className="phone-intro-note">The hall is rebuilt in 3D from the fresco (Vatican, 1509–1511).</p>
      </div>
      <div className="phone-intro-how">
        <h2>How to visit</h2>
        <dl>
          {HOW.map(([k, v]) => (
            <div key={k}>
              <dt>{k}</dt>
              <dd>{v}</dd>
            </div>
          ))}
        </dl>
        {PHONE_LANDSCAPE ? <button type="button" onClick={enter}>Enter the gallery</button> : null}
      </div>
    </header>
  );
}
