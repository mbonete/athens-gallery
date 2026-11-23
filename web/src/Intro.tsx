const TOUCH = typeof matchMedia !== "undefined" && matchMedia("(pointer: coarse)").matches;

/** How to visit, for the device in hand: the same words as the right banner (Banners.tsx). */
const HOW: [string, string][] = TOUCH
  ? [
      ["Walk", "Spread two fingers; pinch to walk back"],
      ["A painting", "Tap it to walk up; pinch to zoom"],
      ["The dome", "Tap it to look up"],
    ]
  : [
      ["Walk", "Scroll, or pinch on a trackpad"],
      ["Look around", "Drag with the right button, or hold Shift and drag"],
      ["A painting", "Click it to walk up, again to zoom; drag to move across it"],
      ["The dome", "Click it to look up"],
      ["Keys", "Arrows to walk; Tab and Enter open a painting"],
    ];

/** The exhibition's title and how to visit, as text for screen readers. Sighted visitors read
 * them on the two banners in the hall (Banners.tsx), which are drawn into the 3D scene; the old
 * bottom banner over the start view is gone (Maria, 2026-11-22: "drop the old bottom banner"). */
export function Intro() {
  return (
    <header className="visually-hidden">
      <h1>Studiolo</h1>
      <p>
        Nine favourite paintings, chosen by Maria Bonete, hung in the architecture of Raphael’s{" "}
        <cite>School of Athens</cite>.
      </p>
      <p>The hall is rebuilt in 3D from the fresco (Vatican, 1509–1511). Each painting hangs at its true size.</p>
      <h2>How to visit</h2>
      <dl>
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
