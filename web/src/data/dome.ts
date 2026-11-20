// The crossing's drum and dome, in web metres (70 %, y up, the walk runs along -z).
// Centre and half-width come from hall.json (the Blender export); the heights aren't exported,
// so they are worked out here from blender/scripts/params.py (crossing option A) and the
// geometry in blender/scripts/build.py, times SCALE = 0.7. If the hall is rebuilt with other
// crossing dimensions, update these. Checked against hall.glb: the dome shell's top is at
// 21.30 m and the drum spans 12.76-16.82 m.
import hall from "./hall.json";

export const DOME = {
  /** Dome axis: hall.json dome.z, the crossing's centre ((CROSS_Y0 + CROSS_Y1) / 2 = 40.1 x 0.7). */
  z: hall.dome.z,
  /** Half the square crossing = the drum's and dome's inner radius (CROSS_HALF 5.9 x 0.7). */
  half: hall.dome.wallX,
  /** Springing of the crossing's arches and pendentives (SPRING_Z 12.3 x 0.7). */
  spring: 8.61,
  /** Base of the drum, the crown of the crossing's arches (DRUM_Z0 = SPRING_Z + CROSS_HALF = 18.2 x 0.7). */
  drumBase: 12.74,
  /** Bottom and top of the drum's 18 windows (DRUM_WIN_Z 20.642, 23.818 x 0.7). */
  windows: [14.449, 16.673] as const,
  /** Top of the drum = springing of the dome's inner hemisphere (DRUM_Z1 24.03 x 0.7). */
  domeSpring: 16.821,
  /** Outer radius of the drum and dome shell (R_OUT = CROSS_HALF + 0.6 = 6.5 x 0.7). */
  outer: 4.55,
  /** Radius of the oculus (OCULUS_R 0.9 x 0.7). */
  oculus: 0.63,
  /** Inner crown, the oculus' rim: DRUM_Z1 + sqrt(R_IN^2 - OCULUS_R^2) = 29.861 x 0.7. */
  crown: 20.903,
};
