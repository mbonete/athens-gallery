import { useEffect, useRef, useState } from "react";
import { focusHotspot, dom, leave, relayout, zoomStep } from "./transition";
import { useStore } from "./store";
import { t } from "./i18n";
import { words } from "./paintings";
import { BackArrow } from "./icons";

/** The zoomable painting (OpenSeadragon) and the label-turned-panel. */
export function Detail() {
  const osd = useRef<HTMLDivElement>(null);
  const panel = useRef<HTMLDivElement>(null);
  const zoomUi = useRef<HTMLDivElement>(null);
  const [zoom, setZoom] = useState({ canIn: true, canOut: false });
  const active = useStore((s) => s.active);
  const mode = useStore((s) => s.mode);
  const [hotspot, setHotspot] = useState(-1);
  const s = t();

  useEffect(() => {
    dom.osd = osd.current;
    dom.panel = panel.current;
    dom.zoomUi = zoomUi.current;
    const onHotspot = (e: Event) => setHotspot((e as CustomEvent<number>).detail);
    const onZoom = (e: Event) => setZoom((e as CustomEvent<{ canIn: boolean; canOut: boolean }>).detail);
    window.addEventListener("zoomstate", onZoom);
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && leave();
    window.addEventListener("hotspot", onHotspot);
    window.addEventListener("keydown", onKey);
    // The viewer, the panel and the pose are laid out for one window size.
    window.addEventListener("resize", relayout);
    return () => {
      window.removeEventListener("hotspot", onHotspot);
      window.removeEventListener("zoomstate", onZoom);
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("resize", relayout);
    };
  }, []);

  const p = active;
  const w = p && words(p);
  return (
    <>
      <div ref={osd} className="osd" style={{ pointerEvents: mode === "detail" ? "auto" : "none" }} />
      {/* Zoom in and out by a step, at the painting's lower right corner (placed by transition.ts). */}
      <div ref={zoomUi} className={`zoom-ui ${mode === "detail" ? "show" : ""}`} aria-hidden={mode !== "detail"}>
        <button type="button" aria-label={s.zoomOut} disabled={!zoom.canOut} onClick={() => zoomStep(-1)}>
          <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M3 8h10" /></svg>
        </button>
        <button type="button" aria-label={s.zoomIn} disabled={!zoom.canIn} onClick={() => zoomStep(1)}>
          <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M3 8h10M8 3v10" /></svg>
        </button>
      </div>
      {/* A dialog named by the title: opened from the keyboard, focus moves to Back (Keys.tsx), and
          a screen reader announces the painting's title. */}
      <div ref={panel} className="panel" aria-hidden={!p} role={p ? "dialog" : undefined}
        aria-labelledby={p ? "panel-title" : undefined}>
        {p && w && (
          <div className="content">
            <button className="close" onClick={() => leave()} aria-label={s.backToHall}>
              <BackArrow />{s.backToHall}
            </button>
            <h1 id="panel-title">{w.title}</h1>
            <p className="who">{w.artist}, {w.date}</p>
            <dl>
              <dt>{s.technique}</dt><dd>{w.medium}</dd>
              <dt>{s.size}</dt><dd>{w.dimensions}</dd>
              <dt>{s.collection}</dt><dd>{w.museum}</dd>
              {w.credit && <><dt>{s.credit}</dt><dd>{w.credit}</dd></>}
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
              {w.licence}. <a href={p.source} target="_blank" rel="noreferrer">{s.record}</a>
            </p>
          </div>
        )}
      </div>
    </>
  );
}
