"""Crop, resize and tile the collection for the web app.

Usage: python prepare_collection.py <originals_dir> <work_dir> <web_public_paintings_dir>
       [--mobile-only] [slug ...]
Crops are in each original's pixels, measured from brightness profiles of its edges
(see reference/paintings/collection.md). Writes <slug>.dzi, <slug>_files/ and
<slug>-texture.jpg per work via tools/dzi.py, plus a <=1024 px
<slug>-mobile-texture.jpg for the hall on coarse-pointer devices. The DZI tiles
stay at their original resolution.
"""
import subprocess
import sys
from pathlib import Path

from PIL import Image

Image.MAX_IMAGE_PIXELS = None
src, work, out = (Path(a) for a in sys.argv[1:4])
work.mkdir(parents=True, exist_ok=True)
DZI = Path(__file__).resolve().parent / "dzi.py"
MOBILE_MAX = 1024

# slug: (file, crop box or None, max tile width, texture width)
WORKS = {
    "mucha-summer": ("mucha-summer.jpg", (268, 442, 6796, 12936), None, 1600),  # the paper sheet
    "waterhouse-hylas": ("waterhouse-hylas.jpg", None, None, 2048),
    "hokusai-great-wave": ("hokusai-wave-met.jpg", None, None, 2048),
    "klimt-water-serpents-ii": ("klimt-serpents2.jpg", (90, 174, 5886, 3378), None, 2048),  # inside the book page
    "vangogh-almond-blossom": ("vangogh-almond.jpg", None, None, 2048),
    "kandinsky-composition-8": ("kandinsky-comp8.jpg", (47, 110, 3872, 2765), None, 2048),  # inside the frame
    "hiroshige-asakusa-torinomachi": ("hiroshige-asakusa.jpg", None, None, 1400),
    "titian-rape-of-europa": ("titian-europa-gardner.jpg", None, None, 2048),  # the Gardner's own photograph (CC BY-NC-ND 4.0)
    "bosch-garden-of-earthly-delights": ("bosch-garden.jpg", (150, 150, 29790, 16883), 12000, 4096),
}

rest = set(sys.argv[4:])
mobile_only = "--mobile-only" in rest
only = rest - {"--mobile-only"}  # optional: slugs to (re)build
for slug, (name, box, max_w, tex_w) in WORKS.items():
    if only and slug not in only:
        continue
    im = Image.open(src / name).convert("RGB")
    if box:
        im = im.crop(box)
    if max_w and im.width > max_w:
        im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
    path = work / f"{slug}.jpg"
    im.save(path, quality=93)
    print(slug, im.size, flush=True)
    if not mobile_only:
        subprocess.run([sys.executable, "-I", str(DZI), str(path), str(out), slug, str(tex_w)], check=True)
    else:
        out.mkdir(parents=True, exist_ok=True)
    mobile = im.copy()
    mobile.thumbnail((MOBILE_MAX, MOBILE_MAX), Image.LANCZOS)
    mobile.save(out / f"{slug}-mobile-texture.jpg", quality=88, optimize=True, progressive=True)
    print(f"{slug}: mobile texture {mobile.width}x{mobile.height}", flush=True)
