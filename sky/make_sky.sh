#!/bin/sh
# Make web/public/sky/sky.jpg from the fresco scan (not committed: reference/download/).
#   sky/make_sky.sh [scan] [workdir]
# Needs Python with NumPy, OpenCV and Pillow (tools/.venv). Writes the intermediates to workdir,
# and copies gradient.json and sky-recipe.json (what went into the texture) next to this script.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
SCAN=${1:-$HERE/../reference/download/athens-original.jpg}
WORK=${2:-$(mktemp -d)}
PY=${PYTHON:-$HERE/../tools/.venv/bin/python}
mkdir -p "$WORK" && cd "$WORK"
"$PY" "$HERE/prep.py" "$SCAN"
"$PY" "$HERE/masks.py"
"$PY" "$HERE/gradient.py"
"$PY" "$HERE/gen_sky.py" 2048 sky.jpg
cp sky.jpg "$HERE/../web/public/sky/sky.jpg"
cp gradient.json sky-recipe.json "$HERE/"
echo "sky.jpg -> web/public/sky/ (work files in $WORK)"
