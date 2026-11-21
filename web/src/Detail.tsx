import { useEffect, useRef, useState } from "react";
import { focusHotspot, dom, leave } from "./transition";
import { useStore } from "./store";

/** The zoomable painting (OpenSeadragon) and the label-turned-panel. */
export function Detail() {
  const osd = useRef<HTMLDivElement>(null);
  const panel = useRef<HTMLDivElement>(null);
  const active = useStore((s) => s.active);
  const mode = useStore((s) => s.mode);
  const [hotspot, setHotspot] = useState(-1);

  useEffect(() => {
    dom.osd = osd.current;
    dom.panel = panel.current;
    const onHotspot = (e: Event) => setHotspot((e as CustomEvent<number>).detail);
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && leave();
    window.addEventListener("hotspot", onHotspot);
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("hotspot", onHotspot);
      window.removeEventListener("keydown", onKey);
    };
  }, []);

  const p = active;
  return (
    <>
      <div ref={osd} className="osd" style={{ pointerEvents: mode === "detail" ? "auto" : "none" }} />
      {/* A dialog named by the title: opened from the keyboard, focus moves to Back (Keys.tsx), and
          a screen reader announces the painting's title. */}
      <div ref={panel} className="panel" aria-hidden={!p} role={p ? "dialog" : undefined}
        aria-labelledby={p ? "panel-title" : undefined}>
        {p && (
          <div className="content">
            <button className="close" onClick={() => leave()} aria-label="Back to the hall">
              ← Back to the hall
            </button>
            <h1 id="panel-title">{p.title}</h1>
            <p className="who">{p.artist}, {p.date}</p>
            <dl>
              <dt>Technique</dt><dd>{p.medium}</dd>
              <dt>Size</dt><dd>{p.dimensions}</dd>
              <dt>Collection</dt><dd>{p.museum}</dd>
              {p.credit && <><dt>Credit</dt><dd>{p.credit}</dd></>}
            </dl>
            {p.hotspots.length > 0 && (
              <div className="facts">
                {p.hotspots.map((h, i) => (
                  <button key={i} className={`fact ${hotspot === i ? "on" : ""}`} onClick={() => focusHotspot(p, i)}>
                    <span className="dot" />{h.text}
                  </button>
                ))}
              </div>
            )}
            <p className="source">
              {p.licence}. <a href={p.source} target="_blank" rel="noreferrer">Record</a>
            </p>
          </div>
        )}
      </div>
    </>
  );
}
