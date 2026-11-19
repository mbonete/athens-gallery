// The paintings in the hall. Data comes from each museum's record; nothing is invented.
export type Hotspot = { x: number; y: number; text: string };

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
  /** Deepest zoom, in screen pixels per image pixel (lower for weak reproductions). */
  maxZoom?: number;
  hotspots: Hotspot[];
};

const files = (slug: string) => ({ dzi: `/paintings/${slug}.dzi`, texture: `/paintings/${slug}-texture.jpg` });

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
  },
  {
    // Placed by Maria (2026-11-19): under the dome, left wall.
    slug: "titian-rape-of-europa", place: "dome-left",
    title: "The Rape of Europa", artist: "Titian", date: "1559–1562",
    medium: "Oil on canvas", dimensions: "178 × 205 cm",
    widthM: 2.05, imageW: 3544, imageH: 2946,
    museum: "Isabella Stewart Gardner Museum, Boston",
    source: "https://gardnermuseum.emuseum.com/objects/236/the-rape-of-europa",
    licence: "Image: Google Art Project, via Wikimedia Commons (public domain)",
    maxZoom: 1.5, ...files("titian-rape-of-europa"), hotspots: [],
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
  },
];

export const heightM = (p: Painting) => (p.widthM * p.imageH) / p.imageW;

/** Every piece hangs 20 % larger than its real size (Maria, 2026-11-19); labels and panels
 * keep the real dimensions. */
export const DISPLAY_SCALE = 1.2;
export const displayW = (p: Painting) => p.widthM * DISPLAY_SCALE;
export const displayH = (p: Painting) => heightM(p) * DISPLAY_SCALE;
