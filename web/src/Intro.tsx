import { useEffect, useState } from "react";
import { rig } from "./rig";
import { useStore } from "./store";

const TOUCH = typeof matchMedia !== "undefined" && matchMedia("(pointer: coarse)").matches;

/** How to visit, for the device in hand, set like a painting's panel (Technique, Size, ...).
 * No word on the detail dots until a painting has some. */
const HOW: [string, string][] = TOUCH
  ? [
      ["Walk", "Spread two fingers; pinch to walk back"],
      ["A painting", "Tap it to walk up; pinch to zoom"],
      ["The dome", "Tap it to look up"],
    ]
  : [
      ["Walk", "Scroll, or pinch on a trackpad"],
      ["A painting", "Click it to walk up, again to zoom; drag to look around"],
      ["The dome", "Click it to look up"],
      ["Keys", "Arrows to walk; Tab and Enter open a painting"],
    ];

/** Walk progress beyond which the visitor has left the entrance (about 15 cm), and where they are
 * back at it. Two thresholds, so it doesn't flicker at the edge. */
const LEAVE = 0.004;
const BACK = 0.0005;

/** The exhibition's title at the entrance, as a banner across the bottom of the start view (Maria,
 * 2026-11-21: this distribution, without tracked capitals or a fog; portrait: the title on the
 * wall above the arch, how to visit at the bottom). It steps aside with the first step and is
 * there again whenever the visitor is back at the start. It never takes a click or a tap. */
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
        <p className="intro-line">
          Nine favourite paintings, chosen by Maria Bonete, hung in the architecture of
          Raphael’s <cite>School of Athens</cite>.
        </p>
        <p className="intro-note">
          The hall is rebuilt in 3D from the fresco (<span className="nowrap">Vatican, 1509–1511</span>). Each painting hangs at its true size.
        </p>
      </div>
      <h2 className="visually-hidden">How to visit</h2>
      <dl className="intro-how">
        {HOW.map(([k, v]) => (
          <div key={k}>
            <dt>{k}</dt>
            <dd>{v}</dd>
          </div>
        ))}
      </dl>
    </header>
  );
}
