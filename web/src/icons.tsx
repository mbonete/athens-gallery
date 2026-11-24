/** Drawn icons, one stroke and weight (1.5 on a 16 grid), coloured by the text they sit with. */
export function BackArrow() {
  return (
    <svg className="icon" viewBox="0 0 16 16" aria-hidden="true">
      <path d="M13 8H3M7 4 3 8l4 4" />
    </svg>
  );
}

/** Fullscreen: four corners opening out. */
export function Expand() {
  return (
    <svg className="icon" viewBox="0 0 16 16" aria-hidden="true">
      <path d="M2.5 6V2.5H6M10 2.5h3.5V6M13.5 10v3.5H10M6 13.5H2.5V10" />
    </svg>
  );
}
