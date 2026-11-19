import { PerspectiveCamera } from "three";

/** A perspective camera with an off-centre (shifted) frustum, like an architect's shift lens.
 * The optical axis stays horizontal, so verticals stay vertical, and the horizon sits where
 * Raphael put it: tanUp / tanDown are the frustum's extents above and below the axis. */
export class ShiftCamera extends PerspectiveCamera {
  tanUp = 0.78;
  tanDown = 0.39;
  /** Where the optical axis lands horizontally, in NDC (Raphael's vanishing point is 13 px right of centre). */
  shiftX = 0;

  constructor() {
    super(60, 1, 0.05, 2000);
  }

  override updateProjectionMatrix() {
    const n = this.near;
    const top = n * this.tanUp;
    const bottom = -n * this.tanDown;
    const halfW = ((top - bottom) * this.aspect) / 2;
    const d = -this.shiftX * halfW;
    this.projectionMatrix.makePerspective(-halfW + d, halfW + d, top, bottom, n, this.far);
    this.projectionMatrixInverse.copy(this.projectionMatrix).invert();
  }
}
