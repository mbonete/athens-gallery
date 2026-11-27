// The visitor's language (Maria, 2026-11-27: "put the language of the readers"): English or
// Spanish, from the browser's preferred languages: the first of them that is English or Spanish;
// anything else gets English. There is no switch on screen (Maria, 2026-11-27: a language button
// "breaks immersion"), so nothing is stored either: the browser decides on every visit. Every word
// the gallery shows comes from here, or from a painting's own `es` fields (paintings.ts). Kept
// small: the portrait phone gate (main.tsx) loads it before the gallery's chunk.

export type Lang = "en" | "es";

function fromBrowser(): Lang {
  const prefs = typeof navigator === "undefined" ? [] : navigator.languages?.length ? navigator.languages : [navigator.language];
  for (const l of prefs) {
    const base = l?.toLowerCase().split("-")[0];
    if (base === "es" || base === "en") return base;
  }
  return "en";
}

const lang: Lang = fromBrowser();

const en = {
  description: "Nine favourite paintings, chosen by Maria Bonete, hung in the architecture of Raphael's School of Athens, rebuilt in 3D.",
  loadingGallery: "Loading the gallery…",
  loadingHall: "Loading the hall…",
  canvas: (n: number) => `The architecture of Raphael's School of Athens in 3D, with ${n} paintings`,
  // The line about the exhibition, around the fresco's title (set in italic).
  lead: ["Nine favourite paintings, chosen by Maria Bonete, hung in the architecture of Raphael’s", "School of Athens", "."],
  note: "The hall is rebuilt in 3D from the fresco (Vatican, 1509–1511).",
  noteBanner: "The hall is rebuilt in 3D from the fresco (Vatican, 1509–1511). Each painting hangs at its true size.",
  howTitle: "How to visit",
  howTouch: [
    ["Walk", "Spread two fingers; pinch to walk back"],
    ["Look around", "Touch the hall and slide one finger left, right, up or down"],
    ["A painting", "Tap it to walk up; pinch to zoom"],
    ["The dome", "Tap it to look up"],
  ],
  howMouse: [
    ["Walk", "Scroll, or pinch on a trackpad"],
    ["Look around", "Click and drag"],
    ["A painting", "Click it to walk up, again to zoom; drag to move across it"],
    ["The dome", "Click it to look up"],
    ["Keys", "Arrows to walk; Tab and Enter open a painting"],
  ],
  enter: "Enter the gallery",
  fullScreen: "Full screen",
  detail: "detail",
  labelAction: "Tap to look closer",
  backToHall: "Back to the hall",
  backToWalk: "Back to the walk",
  zoomIn: "Zoom in",
  zoomOut: "Zoom out",
  technique: "Technique",
  size: "Size",
  collection: "Collection",
  credit: "Credit",
  record: "Record",
  lookUpDome: "Look up into the dome",
  rotateTitle: "Turn your phone sideways",
  rotateCopy: "The gallery is designed to be visited in landscape.",
  rotateTrying: "Requesting landscape…",
  rotateTry: "Try landscape automatically",
  rotateHelp: "If the screen does not turn, switch off rotation lock or open Studiolo on a computer.",
  rotateFailed: "Your browser could not rotate automatically. Please turn your phone sideways.",
};
export type Strings = typeof en;

const es: Strings = {
  description: "Nueve cuadros favoritos, elegidos por Maria Bonete, colgados en la arquitectura de La escuela de Atenas de Rafael, reconstruida en 3D.",
  loadingGallery: "Cargando la galería…",
  loadingHall: "Cargando la sala…",
  canvas: (n: number) => `La arquitectura de La escuela de Atenas de Rafael en 3D, con ${n} cuadros`,
  lead: ["Nueve cuadros favoritos, elegidos por Maria Bonete, colgados en la arquitectura de", "La escuela de Atenas", " de Rafael."],
  note: "La sala está reconstruida en 3D a partir del fresco (Vaticano, 1509–1511).",
  noteBanner: "La sala está reconstruida en 3D a partir del fresco (Vaticano, 1509–1511). Cada cuadro cuelga a su tamaño real.",
  howTitle: "Cómo se visita",
  howTouch: [
    ["Caminar", "Separa dos dedos; júntalos para retroceder"],
    ["Mirar alrededor", "Toca la sala y desliza un dedo a izquierda, derecha, arriba o abajo"],
    ["Un cuadro", "Tócalo para acercarte; pellizca para ampliar"],
    ["La cúpula", "Tócala para mirar arriba"],
  ],
  howMouse: [
    ["Caminar", "Gira la rueda del ratón, o pellizca en el trackpad"],
    ["Mirar alrededor", "Haz clic y arrastra"],
    ["Un cuadro", "Haz clic para acercarte y otra vez para ampliar; arrastra para recorrerlo"],
    ["La cúpula", "Haz clic para mirar arriba"],
    ["Teclado", "Flechas para caminar; Tabulador e Intro abren un cuadro"],
  ],
  enter: "Entrar en la galería",
  fullScreen: "Pantalla completa",
  detail: "detalle",
  labelAction: "Pulsa para verlo de cerca",
  backToHall: "Volver a la sala",
  backToWalk: "Volver al recorrido",
  zoomIn: "Ampliar",
  zoomOut: "Reducir",
  technique: "Técnica",
  size: "Medidas",
  collection: "Colección",
  credit: "Procedencia",
  record: "Ficha",
  lookUpDome: "Mirar la cúpula",
  rotateTitle: "Pon el móvil en horizontal",
  rotateCopy: "La galería está pensada para visitarse en horizontal.",
  rotateTrying: "Girando la pantalla…",
  rotateTry: "Girar la pantalla automáticamente",
  rotateHelp: "Si la pantalla no gira, desactiva el bloqueo de rotación o abre Studiolo en un ordenador.",
  rotateFailed: "Tu navegador no ha podido girar la pantalla. Pon el móvil en horizontal.",
};
const STRINGS: Record<Lang, Strings> = { en, es };

// The page itself: its language (screen readers, hyphenation) and its description.
if (typeof document !== "undefined") {
  document.documentElement.lang = lang;
  document.querySelector('meta[name="description"]')?.setAttribute("content", STRINGS[lang].description);
}

export const getLang = () => lang;
/** The words in the visitor's language. */
export const t = (): Strings => STRINGS[lang];
