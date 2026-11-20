#!/bin/zsh
# Build the finished hall, bake its light, make the detail tiles, pack it for the web.
#   tools/bake_hall.sh [rough|final]      (default: rough; settings in params.py, BAKE)
# Writes web/public/models/hall.glb and web/src/data/hall.json; intermediates in blender/build/.
set -euo pipefail
cd "$(dirname "$0")/.."
Q=${1:-rough}
B=${BLENDER:-/opt/homebrew/bin/blender}
PY=${PYTHON:-python3}
OUT=blender/build/bake-$Q
rm -rf $OUT && mkdir -p $OUT
$B -b --factory-startup -P blender/scripts/build.py -- $OUT json 2>&1 | grep -E "Traceback|Error|exported" || true
BAKE=$Q $B -b blender/athens-hall.blend -P blender/scripts/bake.py -- $OUT $Q 2>&1 | grep -E "^\[bake|Traceback|Error" || true
test -f $OUT/hall.gltf
$PY -I tools/make_detail.py $OUT
H=$($PY -c "import sys; sys.path.insert(0, 'blender/scripts'); import params as P; print(4 if P.BAKE['$Q']['samples'] < 300 else 2)")
$PY -I tools/denoise_lightmaps.py $H $OUT/lightmap_*.png
node tools/pack_hall.mjs $OUT web/public/models/hall.glb
