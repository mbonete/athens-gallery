// The paintings in the hall. Data comes from each museum's record; nothing is invented.
import { getLang } from "./i18n";

export type Hotspot = { x: number; y: number; text: string };

/** The words on a painting's label and panel. In Spanish (`es`), only the fields that change:
 * the established Spanish title (the Prado's own for the Bosch), the Spanish name of the artist
 * where there is one (Tiziano, el Bosco), technique, dates and credit lines translated, decimal
 * commas. Museums keep their own names; their cities take the Spanish spelling. */
type Words = { title: string; artist: string; date: string; medium: string; dimensions: string; museum: string; credit?: string; licence: string };

export type Painting = {
  slug: string;
  /** 1-10 on the side walls, numbered in walking order (see renders/grey/plan.png); "dome-left"
   * / "dome-right": the crossing's side walls under the dome; "end": standing in the far
   * doorway, under the last arch. */
  place: number | "end" | "dome-left" | "dome-right";
  title: string;
  artist: string;
  date: string;
  medium: string;
  dimensions: string;
  widthM: number; // real width; height follows the image's proportions
  imageW: number;
  imageH: number;
  museum: string;
  credit?: string;
  source: string;
  licence: string;
  dzi: string;
  texture: string;
  /** Smaller hall texture for coarse-pointer devices. Deep zoom still uses `dzi`. */
  mobileTexture: string;
  /** Deepest zoom, in screen pixels per image pixel (lower for weak reproductions). */
  maxZoom?: number;
  hotspots: Hotspot[];
  es: Partial<Words>;
};

/** The painting's words in the visitor's language (i18n.ts). */
export const words = (p: Painting): Words => (getLang() === "es" ? { ...p, ...p.es } : p);

const files = (slug: string) => ({
  dzi: `/paintings/${slug}.dzi`,
  texture: `/paintings/${slug}-texture.jpg`,
  mobileTexture: `/paintings/${slug}-mobile-texture.jpg`,
});

/** The hall needs only screen-sized reproductions on touch-first devices. The full-resolution
 * DZI remains available when a visitor opens a painting. Keeping this decision at module load
 * also gives R3F's loader cache one stable URL per painting and lets the banners share it. */
const MOBILE_HALL = typeof matchMedia !== "undefined" && matchMedia("(pointer: coarse)").matches;
export const hallTexture = (painting: Painting) => MOBILE_HALL ? painting.mobileTexture : painting.texture;

// Museum data only (reference/paintings/collection.md). Facts are Maria's to add as hotspots.
export const PAINTINGS: Painting[] = [
  {
    slug: "mucha-summer", place: 1,
    title: "Summer, from The Seasons", artist: "Alphonse Mucha", date: "1896",
    medium: "Colour lithograph, printed by F. Champenois", dimensions: "104 × 54 cm",
    widthM: 0.54, imageW: 6528, imageH: 12494,
    museum: "Bibliothèque nationale de France, Paris",
    source: "https://gallica.bnf.fr/ark:/12148/btv1b9005130b",
    licence: "Image: Source gallica.bnf.fr / BnF (public domain)",
    ...files("mucha-summer"), hotspots: [],
    es: {
      title: "El verano, de la serie Las estaciones", medium: "Litografía en color, impresa por F. Champenois",
      museum: "Bibliothèque nationale de France, París", licence: "Imagen: Source gallica.bnf.fr / BnF (dominio público)",
    },
  },
  {
    slug: "klimt-water-serpents-ii", place: 2,
    title: "Water Serpents II", artist: "Gustav Klimt", date: "1904–1907",
    medium: "Oil on canvas", dimensions: "80 × 145 cm",
    widthM: 1.45, imageW: 5796, imageH: 3204,
    museum: "Private collection",
    source: "https://commons.wikimedia.org/wiki/File:Gustav_Klimt_-_Water_Serpents_II.jpg",
    licence: "Image: reproduction from a printed book, via Wikimedia Commons (public domain)",
    maxZoom: 1, ...files("klimt-water-serpents-ii"), hotspots: [],
    es: {
      title: "Serpientes de agua II", medium: "Óleo sobre lienzo", museum: "Colección privada",
      licence: "Imagen: reproducción de un libro impreso, vía Wikimedia Commons (dominio público)",
    },
  },
  {
    slug: "waterhouse-hylas", place: 3,
    title: "Hylas and the Nymphs", artist: "John William Waterhouse", date: "1896",
    medium: "Oil on canvas", dimensions: "98.2 × 163.3 cm",
    widthM: 1.633, imageW: 8261, imageH: 4961,
    museum: "Manchester Art Gallery", credit: "Purchased from the artist, 1896",
    source: "https://artuk.org/discover/artworks/hylas-and-the-nymphs-206346",
    licence: "Image: via Wikimedia Commons (public domain)",
    ...files("waterhouse-hylas"), hotspots: [],
    es: {
      title: "Hilas y las ninfas", medium: "Óleo sobre lienzo", dimensions: "98,2 × 163,3 cm",
      credit: "Adquirido al artista, 1896", licence: "Imagen: vía Wikimedia Commons (dominio público)",
    },
  },
  {
    slug: "vangogh-almond-blossom", place: 4,
    title: "Almond Blossom", artist: "Vincent van Gogh", date: "February 1890",
    medium: "Oil on canvas", dimensions: "73.3 × 92.4 cm",
    widthM: 0.924, imageW: 7149, imageH: 5649,
    museum: "Van Gogh Museum, Amsterdam", credit: "Vincent van Gogh Foundation",
    source: "https://www.vangoghmuseum.nl/en/collection/s0176V1962",
    licence: "Image: Van Gogh Museum, Amsterdam (Vincent van Gogh Foundation), via Wikimedia Commons",
    ...files("vangogh-almond-blossom"), hotspots: [],
    es: {
      title: "Almendro en flor", date: "febrero de 1890", medium: "Óleo sobre lienzo", dimensions: "73,3 × 92,4 cm",
      museum: "Van Gogh Museum, Ámsterdam", credit: "Fundación Vincent van Gogh",
      licence: "Imagen: Van Gogh Museum, Ámsterdam (Fundación Vincent van Gogh), vía Wikimedia Commons",
    },
  },
  {
    slug: "hokusai-great-wave", place: 5,
    title: "Under the Wave off Kanagawa (The Great Wave)", artist: "Katsushika Hokusai", date: "c. 1830–32",
    medium: "Woodblock print; ink and colour on paper", dimensions: "25.7 × 37.9 cm",
    widthM: 0.379, imageW: 3859, imageH: 2594,
    museum: "The Metropolitan Museum of Art, New York",
    credit: "H. O. Havemeyer Collection, Bequest of Mrs. H. O. Havemeyer, 1929",
    source: "https://www.metmuseum.org/art/collection/search/45434",
    licence: "Image: The Met, Open Access (public domain)",
    ...files("hokusai-great-wave"), hotspots: [],
    es: {
      title: "Bajo la ola de Kanagawa (La gran ola)", date: "h. 1830–32",
      medium: "Xilografía; tinta y color sobre papel", dimensions: "25,7 × 37,9 cm",
      museum: "The Metropolitan Museum of Art, Nueva York",
      credit: "Colección H. O. Havemeyer, legado de la Sra. H. O. Havemeyer, 1929",
      licence: "Imagen: The Met, Open Access (dominio público)",
    },
  },
  {
    // Placed by Maria (2026-11-19): under the dome, right wall (swapped with Hiroshige).
    slug: "kandinsky-composition-8", place: "dome-right",
    title: "Composition 8", artist: "Vasily Kandinsky", date: "July 1923",
    medium: "Oil on canvas", dimensions: "140 × 201 cm",
    widthM: 2.01, imageW: 3825, imageH: 2655,
    museum: "Solomon R. Guggenheim Museum, New York",
    source: "https://www.guggenheim.org/artwork/1924",
    licence: "Image: visitor's photograph (CC0), via Wikimedia Commons",
    maxZoom: 1.5, ...files("kandinsky-composition-8"), hotspots: [],
    es: {
      title: "Composición 8", date: "julio de 1923", medium: "Óleo sobre lienzo",
      museum: "Solomon R. Guggenheim Museum, Nueva York",
      licence: "Imagen: fotografía de un visitante (CC0), vía Wikimedia Commons",
    },
  },
  {
    // Placed by Maria (2026-11-19): nave, third bay, right wall (swapped with Kandinsky).
    slug: "hiroshige-asakusa-torinomachi", place: 6,
    title: "Asakusa Ricefields and Torinomachi Festival, from One Hundred Famous Views of Edo",
    artist: "Utagawa Hiroshige", date: "1857",
    medium: "Woodblock print (nishiki-e); ink and colour on paper", dimensions: "33.2 × 22.1 cm",
    widthM: 0.221, imageW: 2627, imageH: 3905,
    museum: "The Metropolitan Museum of Art, New York", credit: "Rogers Fund, 1914",
    source: "https://www.metmuseum.org/art/collection/search/36539",
    licence: "Image: The Met, Open Access (public domain)",
    ...files("hiroshige-asakusa-torinomachi"), hotspots: [],
    es: {
      title: "Arrozales de Asakusa y festival Torinomachi, de la serie Cien famosas vistas de Edo",
      medium: "Xilografía (nishiki-e); tinta y color sobre papel", dimensions: "33,2 × 22,1 cm",
      museum: "The Metropolitan Museum of Art, Nueva York", credit: "Fondo Rogers, 1914",
      licence: "Imagen: The Met, Open Access (dominio público)",
    },
  },
  {
    // Placed by Maria (2026-11-19): under the dome, left wall.
    slug: "titian-rape-of-europa", place: "dome-left",
    title: "The Rape of Europa", artist: "Titian", date: "1559–1562",
    medium: "Oil on canvas", dimensions: "178 × 205 cm",
    widthM: 2.05, imageW: 2281, imageH: 2000,
    museum: "Isabella Stewart Gardner Museum, Boston",
    source: "https://www.gardnermuseum.org/experience/collection/10978",
    licence: "Image: Isabella Stewart Gardner Museum, Boston (CC BY-NC-ND 4.0)",
    maxZoom: 1.5, ...files("titian-rape-of-europa"), hotspots: [],
    es: {
      title: "El rapto de Europa", artist: "Tiziano", medium: "Óleo sobre lienzo",
      licence: "Imagen: Isabella Stewart Gardner Museum, Boston (CC BY-NC-ND 4.0)",
    },
  },
  {
    slug: "bosch-garden-of-earthly-delights", place: "end",
    title: "The Garden of Earthly Delights", artist: "Hieronymus Bosch", date: "1490–1500",
    medium: "Oil on oak panel (triptych)", dimensions: "185.8 × 325.5 cm open",
    widthM: 3.255, imageW: 12000, imageH: 6774,
    museum: "Museo Nacional del Prado, Madrid",
    source: "https://www.museodelprado.es/en/the-collection/art-work/the-garden-of-earthly-delights-triptych/02388242-6d6a-4e9e-a992-e1311eab3609",
    licence: "Image: Museo del Prado scan, via Wikimedia Commons (public domain)",
    ...files("bosch-garden-of-earthly-delights"), hotspots: [],
    es: {
      title: "El jardín de las delicias", artist: "El Bosco", medium: "Óleo sobre tabla de roble (tríptico)",
      dimensions: "185,8 × 325,5 cm abierto",
      licence: "Imagen: escaneado del Museo del Prado, vía Wikimedia Commons (dominio público)",
    },
  },
];

export const heightM = (p: Painting) => (p.widthM * p.imageH) / p.imageW;

/** Every piece hangs 20 % larger than its real size (Maria, 2026-11-19); labels and panels
 * keep the real dimensions. */
export const DISPLAY_SCALE = 1.2;
export const displayW = (p: Painting) => p.widthM * DISPLAY_SCALE;
export const displayH = (p: Painting) => heightM(p) * DISPLAY_SCALE;
