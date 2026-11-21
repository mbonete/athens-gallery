#!/bin/sh
# Make web/public/sky/sky.jpg: a clear sky from Blender's physical (multiple-scattering) model,
# its sun where the hall's bake puts it (params.py SUN_AZIMUTH, SUN_ELEVATION), shown at the
# bake's exposure x EXPOSURE (1 = strictly the bake's: a white card facing the sun as bright as in
# the lightmaps).
#   sky/make_sky.sh [exposure] [aerosol] [workdir]
# Needs Blender (BLENDER) and Python with NumPy and Pillow (tools/.venv, or PYTHON).
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
EXPOSURE=${1:-2}
AEROSOL=${2:-1}
WORK=${3:-$(mktemp -d)}
B=${BLENDER:-/opt/homebrew/bin/blender}
PY=${PYTHON:-$HERE/../tools/.venv/bin/python}
mkdir -p "$WORK"
"$B" -b --factory-startup -P "$HERE/natural_sky.py" -- "$HERE/../blender/scripts" "$WORK" "$AEROSOL" 4096 2>&1 | grep -E "^\[sky\]|Traceback|Error" || true
"$B" -b --factory-startup -P "$HERE/readexr.py" -- "$WORK/sky.exr" "$WORK/sky.npy" 2>&1 | grep -E "Traceback|Error" || true
SCALE=$("$PY" -c "print($(head -1 "$WORK/scale.txt") * $EXPOSURE)")
"$PY" -I "$HERE/stereo.py" "$WORK/sky.npy" "$SCALE" "$WORK/sky.jpg" 2048
cp "$WORK/sky.jpg" "$HERE/../web/public/sky/sky.jpg"
echo "sky.jpg -> web/public/sky/ (exposure $EXPOSURE, aerosol $AEROSOL; work files in $WORK)"
