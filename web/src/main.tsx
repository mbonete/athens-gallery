import { lazy, Suspense, useEffect, useState, useSyncExternalStore } from "react";
import { createRoot } from "react-dom/client";
import { fullscreenLandscape } from "./fullscreen";
import { t } from "./i18n";
// Cardo (OFL), after Griffo's Aldine roman: the labels' face, served from the project (Latin only).
import "@fontsource/cardo/latin-400.css";
import "@fontsource/cardo/latin-400-italic.css";
import "./styles.css";

/** Keep the Three.js gallery out of the initial portrait-phone bundle. Its chunk is requested only
 * after the phone is landscape (or immediately on a device that does not need the gate). */
const Gallery = lazy(async () => {
  const app = await import("./App");
  // Dev only: inspect the camera from the console / automated checks. Loading it here preserves the
  // portrait gate's small initial bundle in production and keeps it in step with the gallery in dev.
  if (import.meta.env.DEV) {
    const { rig } = await import("./rig");
    Object.assign(window, { rig });
  }
  return { default: app.App };
});

// A width test alone would catch narrow desktop windows; a coarse primary pointer alone would catch
// portrait tablets. Together these describe the phone visit we want to hold for landscape.
const PHONE_PORTRAIT = "(pointer: coarse) and (orientation: portrait) and (max-width: 700px)";

function subscribePhonePortrait(onChange: () => void) {
  const query = window.matchMedia(PHONE_PORTRAIT);
  query.addEventListener("change", onChange);
  return () => query.removeEventListener("change", onChange);
}

const phonePortrait = () => window.matchMedia(PHONE_PORTRAIT).matches;

function RotatePhone() {
  const [trying, setTrying] = useState(false);
  const [failed, setFailed] = useState(false);
  const s = t();

  const tryLandscape = async () => {
    setTrying(true);
    setFailed(false);

    await fullscreenLandscape();

    if (phonePortrait()) setFailed(true);
    setTrying(false);
  };

  return (
    <div className="rotate-phone" role="dialog" aria-modal="true" aria-labelledby="rotate-title" aria-describedby="rotate-copy rotate-help">
      <div className="rotate-card">
        <div className="rotate-mark" aria-hidden="true">
          <span className="rotate-device" />
          <svg viewBox="0 0 48 48">
            <path d="M35.5 14.5A16 16 0 0 1 38 34" />
            <path d="m34 30 4 4 4-4" />
          </svg>
        </div>
        <p className="rotate-kicker">Studiolo</p>
        <h1 id="rotate-title">{s.rotateTitle}</h1>
        <p className="rotate-copy" id="rotate-copy">{s.rotateCopy}</p>
        <button className="rotate-button" type="button" onClick={tryLandscape} disabled={trying} autoFocus>
          {trying ? s.rotateTrying : s.rotateTry}
        </button>
        <p className="rotate-help" id="rotate-help">
          {s.rotateHelp}
        </p>
        <p className="rotate-status" role="status" aria-live="polite">{failed ? s.rotateFailed : ""}</p>
      </div>
    </div>
  );
}

function Entry() {
  const portraitPhone = useSyncExternalStore(subscribePhonePortrait, phonePortrait, () => false);
  // Once the gallery has started, keep it mounted behind the gate if the visitor turns the phone
  // upright. This preserves their place; the first portrait visit still downloads no gallery chunk.
  const [started, setStarted] = useState(() => !phonePortrait());
  const s = t();

  useEffect(() => {
    if (!portraitPhone) setStarted(true);
  }, [portraitPhone]);

  return (
    <>
      {started ? (
        <div className="gallery-shell" inert={portraitPhone} aria-hidden={portraitPhone || undefined}>
          <Suspense fallback={<div className="loading">{s.loadingGallery}</div>}>
            <Gallery />
          </Suspense>
        </div>
      ) : null}
      {portraitPhone ? <RotatePhone /> : null}
    </>
  );
}

createRoot(document.getElementById("root")!).render(<Entry />);
