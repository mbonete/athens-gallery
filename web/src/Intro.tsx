import { useEffect, useState } from "react";
import { rig } from "./rig";
import { useStore } from "./store";

const TOUCH = typeof matchMedia !== "undefined" && matchMedia("(pointer: coarse)").matches;

/** How to visit, for the device in hand. No word on the detail dots until a painting has some. */
const HOW = TOUCH
  ? ["Spread two fingers to walk in, pinch to walk back", "Tap a painting to walk up to it, then pinch to zoom in", "Tap the dome to look up"]
  : ["Scroll to walk in", "Click a painting to walk up to it, then scroll to zoom in", "Click the dome to look up",
     "Keyboard: arrows, Tab, Enter"];

/** Walk progress beyond which the visitor has left the entrance (about 15 cm), and where they are
 * back at it. Two thresholds, so it doesn't flicker at the edge. */
const LEAVE = 0.004;
const BACK = 0.0005;

/** The exhibition's title at the entrance (Maria, 2026-11-21): what the site is and how to visit.
 * It stands over the start view, steps aside with the first step and is there again whenever the
 * visitor is back at the start. It never takes a click or a tap (the hall behind it does). */
export function Intro() {
  const ready = useStore((s) => s.ready);
  const mode = useStore((s) => s.mode);
  const [atStart, setAtStart] = useState(true);

  useEffect(() => {
    let id = 0;
    let at = true;
    const tick = () => {
      const p = rig.drive === "scroll" ? Math.max(rig.progress, rig.target) : 1;
      const next = at ? p < LEAVE : p < BACK;
      if (next !== at) setAtStart((at = next));
      id = requestAnimationFrame(tick);
    };
    id = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(id);
  }, []);

  return (
    <header className={`intro ${ready && mode === "walk" && atStart ? "show" : ""}`}>
      <div className="intro-title">
        <h1>Studiolo</h1>
        <p className="intro-sub">
          Nine favourite paintings, chosen by Maria Bonete, hung in the architecture of
          Raphael's <cite>School of Athens</cite>.
        </p>
        <p className="intro-note">
          The hall is rebuilt in 3D from the fresco (Vatican, 1509–1511). Each painting hangs at its true size.
        </p>
      </div>
      <ul className="intro-how" aria-label="How to visit">
        {HOW.map((t) => <li key={t}>{t}</li>)}
      </ul>
    </header>
  );
}
