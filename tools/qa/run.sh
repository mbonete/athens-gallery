#!/bin/zsh
# Runs a tools/qa script with web/'s packages (gltf-transform, meshoptimizer):
#   tools/qa/run.sh lightmap_islands.mjs web/public/models/hall.glb '{"label":[x0,x1,y0,y1,z0,z1]}'
#   tools/qa/run.sh lightmap_seams.mjs web/public/models/hall.glb out.json
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
script="$1"; shift
args=()
for a in "$@"; do [[ -e "$ROOT/$a" ]] && args+=("$ROOT/$a") || args+=("$a"); done
tmp="$ROOT/web/.qa-$$.mjs"
cp "$ROOT/tools/qa/$script" "$tmp"
trap 'rm -f "$tmp"' EXIT
(cd "$ROOT/web" && node "$tmp" "${args[@]}")
