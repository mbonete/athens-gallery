#!/bin/sh
# Make web/public/sky/sky.jpg: a photographed sky (Poly Haven, CC0: kloofendal_48d_partly_cloudy_puresky,
# 4k HDR, in reference/download/hdri/, not committed), turned so its sun stands where the hall's
# bake puts it, its sun disc taken out, and its clear blue matched to Blender's physical sky
# (multiple scattering, same sun) at the bake's exposure x EXPOSURE (2: a photo's exposure; 1 is
# strictly the bake's, which reads dusky next to the marble).
#   sky/make_sky.sh [photo.hdr] [exposure] [workdir]
# Needs Blender (BLENDER) and Python with NumPy, OpenCV and Pillow (tools/.venv, or PYTHON).
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
PHOTO=${1:-$HERE/../reference/download/hdri/kloofendal_48d_partly_cloudy_puresky_4k.hdr}
EXPOSURE=${2:-2}
WORK=${3:-$(mktemp -d)}
B=${BLENDER:-/opt/homebrew/bin/blender}
PY=${PYTHON:-$HERE/../tools/.venv/bin/python}
mkdir -p "$WORK"
"$B" -b --factory-startup -P "$HERE/natural_sky.py" -- "$HERE/../blender/scripts" "$WORK" 1 4096 2>&1 | grep -E "^\[sky\]|Traceback|Error" || true
"$B" -b --factory-startup -P "$HERE/readexr.py" -- "$WORK/sky.exr" "$WORK/model.npy" 2>&1 | grep -E "Traceback|Error" || true
"$B" -b --factory-startup -P "$HERE/readexr.py" -- "$PHOTO" "$WORK/photo-in.npy" 2>&1 | grep -E "Traceback|Error" || true
# Blender's errors are filtered above; a missing output means a step failed (seen once while a bake ran).
for f in scale.txt model.npy photo-in.npy; do
  test -s "$WORK/$f" || { echo "make_sky: $f was not written (a Blender step failed); rerun" >&2; exit 1; }
done
SCALE=$("$PY" -c "print($(head -1 "$WORK/scale.txt") * $EXPOSURE)")
ROT=$(awk '/^rot_deg/ {print $2}' "$WORK/scale.txt")
"$PY" -I "$HERE/photo_sky.py" "$WORK/photo-in.npy" "$WORK/model.npy" "$SCALE" "$ROT" "$WORK/photo.npy"
"$PY" -I "$HERE/stereo.py" "$WORK/photo.npy" 1 "$WORK/sky.jpg" 2048
cp "$WORK/sky.jpg" "$HERE/../web/public/sky/sky.jpg"
echo "sky.jpg -> web/public/sky/ (exposure $EXPOSURE; work files in $WORK)"
