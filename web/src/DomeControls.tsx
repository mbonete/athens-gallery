import { useThree } from "@react-three/fiber";
import { useEffect } from "react";
import { attachDomeKeys, attachDomePicking, lookDown } from "./dome";
import { useStore } from "./store";
import { BackArrow } from "./icons";
import { attachBannerKeys, leaveBanner } from "./banner";

/** Inside the canvas: gives the dome's picking pass the renderer and the scene. */
export function DomePicking() {
  const { gl, scene } = useThree();
  useEffect(() => attachDomePicking(gl, scene), [gl, scene]);
  return null;
}

/** The way back while looking up into the dome or reading an entrance banner. */
export function DomeBack() {
  const mode = useStore((s) => s.mode);
  const banner = mode === "banner-in" || mode === "banner";
  const shown = mode === "looking-up" || mode === "dome" || banner;
  useEffect(() => attachDomeKeys(), []);
  useEffect(() => attachBannerKeys(), []);
  return (
    <button
      className={`close dome-back ${shown ? "show" : ""}`}
      onClick={() => (banner ? leaveBanner() : lookDown())}
      aria-hidden={!shown}
      aria-label="Back to the walk"
      tabIndex={shown ? 0 : -1}
    >
      <BackArrow />Back to the walk
    </button>
  );
}
