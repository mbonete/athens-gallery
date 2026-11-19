"""Download the CC0 scanned textures used by the finished hall into blender/textures/ (git-ignored).

Sources (CC0, official sites only): Poly Haven (polyhaven.com) and ambientCG (ambientcg.com), 1K JPG.
Only colour, normal (OpenGL) and roughness maps are kept; everything else in the archives is skipped.

Usage: python -I tools/fetch_textures.py
"""
import io
import re
import sys
import urllib.request
import zipfile
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "blender" / "textures"
UA = {"User-Agent": "texture-fetch/1.0"}

POLYHAVEN = {
    # name: {map: url}
    "white_plaster_02": {
        "color": "https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/white_plaster_02/white_plaster_02_diff_1k.jpg",
        "normal": "https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/white_plaster_02/white_plaster_02_nor_gl_1k.jpg",
        "rough": "https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/white_plaster_02/white_plaster_02_rough_1k.jpg",
    },
}
AMBIENTCG = ["Travertine009", "Marble009", "Marble014"]
KEEP = {"Color": "color", "NormalGL": "normal", "Roughness": "rough"}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, maps in POLYHAVEN.items():
        d = OUT / name
        d.mkdir(exist_ok=True)
        for kind, url in maps.items():
            dst = d / f"{kind}.jpg"
            if not dst.exists():
                dst.write_bytes(get(url))
            print("ok", dst)
    for asset in AMBIENTCG:
        d = OUT / asset
        d.mkdir(exist_ok=True)
        if all((d / f"{k}.jpg").exists() for k in KEEP.values()):
            print("ok", d)
            continue
        z = zipfile.ZipFile(io.BytesIO(get(f"https://ambientcg.com/get?file={asset}_1K-JPG.zip")))
        for member in z.namelist():
            m = re.fullmatch(rf"{asset}_1K-JPG_(Color|NormalGL|Roughness)\.jpg", member)
            if m:
                (d / f"{KEEP[m.group(1)]}.jpg").write_bytes(z.read(member))
        print("ok", d, sorted(p.name for p in d.iterdir()))


if __name__ == "__main__":
    sys.exit(main())
