import * as THREE from "three";
import hall from "./data/hall.json";

/** The gold leaf's sheen (Maria, round 10: clean, smooth, with a sheen), shared by the opening
 * arch's bands (Scene.tsx) and the vault ornament round them (VaultOrnament.tsx): the bake's sun
 * as a soft Blinn-Phong lobe in pale gold, so the leaf brightens and warms where it turns the sun
 * towards the eye and changes as the visitor walks. */
export const SUN_DIR = new THREE.Vector3(...((hall as { sun?: number[] }).sun ?? [0.637, 0.574, 0.515])).normalize();
export const GOLD_SHEEN = new THREE.Color(0.48, 0.34, 0.1); // linear, added at the lobe's peak
export const GOLD_SHININESS = 10;
