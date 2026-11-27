import { useEffect, useState } from "react";
import { fullscreenLandscape, useFullscreen } from "./fullscreen";
import { Expand } from "./icons";
import { useStore } from "./store";
import { t } from "./i18n";

const TOUCH = typeof matchMedia !== "undefined" && matchMedia("(pointer: coarse)").matches;
const PHONE_LANDSCAPE = typeof matchMedia !== "undefined" &&
  matchMedia("(pointer: coarse) and (orientation: landscape) and (max-height: 600px)").matches;

/** The exhibition's title and how to visit. Desktop visitors read them on the two banners in the
 * hall. On a landscape phone those tall banners cannot make body text legible even when they fill
 * the screen vertically, so the same content is a crisp HTML welcome card; tapping either banner
 * opens it again (banner.ts). */
export function Intro() {
  const [open, setOpen] = useState(PHONE_LANDSCAPE);
  const full = useFullscreen();
  const walking = useStore((s) => s.mode === "walk");
  const s = t();
  // How to visit, for the device in hand: the same words as the right banner (Banners.tsx).
  const how = TOUCH ? s.howTouch : s.howMouse;
  const [before, fresco, after] = s.lead;

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
        <Expand />{s.fullScreen}
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
        {before} <cite>{fresco}</cite>{after}
        </p>
        <p className="phone-intro-note">{s.note}</p>
      </div>
      <div className="phone-intro-how">
        <h2>{s.howTitle}</h2>
        <dl>
          {how.map(([k, v]) => (
            <div key={k}>
              <dt>{k}</dt>
              <dd>{v}</dd>
            </div>
          ))}
        </dl>
        {PHONE_LANDSCAPE ? <button type="button" onClick={enter}>{s.enter}</button> : null}
      </div>
    </header>
  );
}
