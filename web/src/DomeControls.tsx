import { useThree } from "@react-three/fiber";
import { useEffect } from "react";
import { attachDomeKeys, attachDomePicking, lookDown } from "./dome";
import { useStore } from "./store";

/** Inside the canvas: gives the dome's picking pass the renderer and the scene. */
export function DomePicking() {
  const { gl, scene } = useThree();
  useEffect(() => attachDomePicking(gl, scene), [gl, scene]);
  return null;
}

/** The way back while looking up into the dome (the detail view's Back, on its own). */
export function DomeBack() {
  const mode = useStore((s) => s.mode);
  const shown = mode === "looking-up" || mode === "dome";
  useEffect(() => attachDomeKeys(), []);
  return (
    <button
      className={`close dome-back ${shown ? "show" : ""}`}
      onClick={() => lookDown()}
      aria-hidden={!shown}
      tabIndex={shown ? 0 : -1}
    >
      ← Back to the walk
    </button>
  );
}
