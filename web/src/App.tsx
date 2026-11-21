import { Canvas } from "@react-three/fiber";
import { Suspense, useEffect, useRef } from "react";
import * as THREE from "three";
import { Detail } from "./Detail";
import { DomeBack } from "./DomeControls";
import { KeyRing, Keys } from "./Keys";
import { PAINTINGS } from "./paintings";
import { rig } from "./rig";
import { Scene } from "./Scene";
import { getState, setState, useStore } from "./store";
import { attachWalkInput } from "./input";
import { attachPicking } from "./pick";
import { enter, leave, loadZoom } from "./transition";
import { progressNear, STATIONS } from "./walk";

// Dev check: ?fresco frames the canvas at the fresco's proportions (3840 x 2661).
const FRESCO_FRAME = import.meta.env.DEV && new URLSearchParams(location.search).has("fresco");

const TOUCH = typeof matchMedia !== "undefined" && matchMedia("(pointer: coarse)").matches;

const CANVAS_LABEL = `The architecture of Raphael's School of Athens in 3D, with ${PAINTINGS.length} paintings`;

export function App() {
  const ready = useStore((s) => s.ready);
  const started = useStore((s) => s.started);
  const stage = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const offWalk = attachWalkInput(stage.current!);
    const offPick = attachPicking(stage.current!);
    return () => (offWalk(), offPick());
  }, []);

  useEffect(() => {
    const onPop = () => {
      const slug = location.hash.match(/^#painting\/(.+)$/)?.[1];
      if (!slug && getState().mode !== "walk") leave({ pop: true });
    };
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  // The zoom viewer's code, once the hall is up and the browser has a moment: the first walk-up
  // then finds it loaded.
  useEffect(() => {
    if (!ready) return;
    const load = () => void loadZoom().catch(() => {});
    if ("requestIdleCallback" in window) {
      const id = requestIdleCallback(load, { timeout: 2000 });
      return () => cancelIdleCallback(id);
    }
    const id = setTimeout(load, 300);
    return () => clearTimeout(id);
  }, [ready]);

  // A link to a painting starts at its stop and walks in.
  useEffect(() => {
    if (!ready) return;
    const slug = location.hash.match(/^#painting\/(.+)$/)?.[1];
    const p = PAINTINGS.find((x) => x.slug === slug);
    if (!p) return;
    const st = STATIONS.find((s) => s.painting === p)!;
    const prog = progressNear(st);
    rig.progress = rig.target = prog;
    setState({ started: true });
    setTimeout(() => enter(p, { push: false }), 600);
  }, [ready]);

  return (
    <>
      <div ref={stage} className={`stage ${FRESCO_FRAME ? "fresco-frame" : ""}`}>
        <Canvas
          dpr={[1, 2]}
          gl={{ antialias: true, toneMapping: THREE.AgXToneMapping, toneMappingExposure: 1.0 }}
          onCreated={({ gl }) => {
            gl.setClearColor("#c9d4e2");
            // Each painting and the dome also have a button (Keys.tsx); the canvas is the picture.
            gl.domElement.setAttribute("role", "img");
            gl.domElement.setAttribute("aria-label", CANVAS_LABEL);
          }}
        >
          <Suspense fallback={null}>
            <Scene />
            <KeyRing />
          </Suspense>
        </Canvas>
      </div>
      {!ready && <div className="loading">Loading the hall…</div>}
      <div className={`hint ${ready && !started ? "show" : ""}`}>
        {TOUCH ? "Spread two fingers to walk in" : "Pinch or scroll to walk in"}
      </div>
      <Keys stage={stage} />
      <Detail />
      <DomeBack />
    </>
  );
}
