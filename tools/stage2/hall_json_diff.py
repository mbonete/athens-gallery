"""What build.py's export would write to hall.json for each crossing / bay-1 option (nothing is written)."""
import json, os, sys, importlib
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[2] / 'blender' / 'scripts'))
cur = json.load(open(str(__import__('pathlib').Path(__file__).resolve().parents[2] / 'web' / 'src' / 'data' / 'hall.json')))
def compute(crossing, hang):
    os.environ['CROSSING'] = crossing
    import params as P; importlib.reload(P)
    k = P.SCALE
    z3 = lambda y: round(-y * k, 4)
    def edges(y0, y1, pil):
        e = [y0]
        for yc in pil: e += [yc - P.PILASTER_W / 2, yc + P.PILASTER_W / 2]
        return e + [y1]
    walls = [edges(P.FACADE_Y1, P.NAVE_Y1, P.PILASTERS_Y), edges(P.CROSS_Y1 + P.TRANSVERSE_T, P.ARM2_Y1, P.ARM2_PILASTERS_Y)]
    bays = [(e[i], e[i + 1]) for e in walls for i in range(0, len(e), 2)]
    places, n = [], 0
    free0 = P.BAY1_NICHE_YC + P.BAY1_NICHE_W / 2 + 0.16; free1 = P.PILASTERS_Y[0] - P.PILASTER_W / 2
    for yc in P.PAINTINGS_Y:
        b0, b1 = next(b for b in bays if b[0] <= yc <= b[1])
        for side in (-1, 1):
            n += 1; wallx = round(P.NAVE_HALF_W * k, 4); y, bb = yc, (b0, b1)
            if n in (1, 2):                                   # bay 1: the recess wall under the niche
                r0, r1, rx = P.BAY1_SIDE_RECESS
                bb = (r0, r1); y = P.BAY1_NICHE_YC; wallx = round(rx * k, 4)
            places.append({"n": n, "side": side, "z": z3(y), "bay": [z3(bb[0]), z3(bb[1])],
                           "bayWidth": round((bb[1] - bb[0]) * k, 3), "wallX": wallx})
    return {"walkEnd": z3(P.ARM2_Y1 - 1.5), "wallX": round(P.NAVE_HALF_W * k, 4),
            "dome": {"wallX": round(P.CROSS_HALF * k, 4), "z": z3((P.CROSS_Y0 + P.CROSS_Y1) / 2), "length": round((P.CROSS_Y1 - P.CROSS_Y0) * k, 3)},
            "door": {"z": z3(P.ARM2_Y1), "width": round(2 * P.DOOR_HALF * k, 3), "springZ": round(P.DOOR_SPRING * k, 3)},
            "places": places}
out = {}
for c in ("gate2", "A"):
    for h in ("below",):
        out[f"{c}/{h}"] = compute(c, h)
print("CURRENT:", json.dumps({k: cur[k] for k in ("walkEnd", "wallX", "dome", "door")}))
for key, d in out.items():
    print(f"\n== {key}")
    for f in ("walkEnd", "wallX", "dome", "door"):
        if d[f] != cur[f]: print(f"  {f}: {cur[f]} -> {d[f]}")
    for p, q in zip(cur["places"], d["places"]):
        ch = {f: (p.get(f), q[f]) for f in ("z", "bay", "bayWidth") if p.get(f) != q[f]}
        if q["wallX"] != cur["wallX"]: ch["wallX (new field)"] = (cur["wallX"], q["wallX"])
        if ch: print(f"  place {q['n']}: " + "; ".join(f"{f} {a} -> {b}" for f, (a, b) in ch.items()))
json.dump(out, open(os.environ.get('OUT', 'hall-json-options.json'), 'w'), indent=1)
# label fits (Scene.tsx rule: beside if w/2 + 0.47 <= room/2 - 0.05), web sizes
for name, w in (("Mucha", 0.65), ("Klimt", 1.74)):
    for key, d in out.items():
        pl = d["places"][0 if name == "Mucha" else 1]
        room = pl["bayWidth"]
        print(f"{name:6s} {key:14s} room {room:.3f} m (web): fits {'yes' if w <= room - 0.1 else 'NO'}; label {'beside' if w / 2 + 0.47 <= room / 2 - 0.05 else 'under'}")
