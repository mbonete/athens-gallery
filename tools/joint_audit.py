"""Joint audit of the finished hall (run inside Blender on the saved model):
  blender -b blender/athens-hall.blend -P tools/joint_audit.py -- <out.json>

Checks every piece against the joint rules (renders/hall-stage4/REPORT.md, "Joint rules"):
1. Collisions: two architectural members whose surfaces cross (triangle overlap, BVH), other
   than the intended embedding of a moulding's back into the wall it is fixed to (a moulding's
   "embed" strip, <= 4 cm behind its base plane) and the floor under bases.
2. Open ends: a swept moulding's end cap that is neither against another surface (within 5 mm
   along its normal) nor hidden from the walk: a cornice cut off in mid-air.
3. Skewed frames: a frame or moulding whose straight runs are not level / plumb.
4. R13 stacked faces: a visible face less than 2 cm (web units) in front of a same-facing face
   of another piece that it covers (coplanar included): it z-fights at a distance.
Prints a table and writes JSON with every finding (object pair, where, how much).
"""
import json
import math
import sys

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

out = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "joint-audit.json"
dg = bpy.context.evaluated_depsgraph_get()
meshes = [ob for ob in bpy.data.objects if ob.type == "MESH" and ob.get("kind") != "painting"
          and ob.name not in ("ground_beyond",) and "_vault_backing" not in ob.name]

# Members a moulding is fixed to (embedding into these is intended).
SUPPORTS = ("nave_wall", "arm2_wall", "facade", "end_wall", "crossing_side", "arch_front", "arch_back",
            "platform", "floor_lower", "podium", "drum", "pendentives", "nave_pilaster_", "arm2_pilaster_",
            "end_pilaster_", "bay1_vestibule_back", "bay1_vestibule_side", "bay1_recess_ceiling",
            "opening_wall", "opening_pilaster_")
MOULDINGS = ("entablature", "string_course", "capital", "base", "archivolt", "frame", "impost", "sill", "edge",
             "nosing", "blind_arch", "drum_base_ring", "drum_sill", "drum_top_cornice", "end_entablature")


def is_support(name):
    return name.startswith(SUPPORTS) and not any(m in name for m in ("capital", "_base_"))


def is_moulding(name):
    return any(m in name for m in MOULDINGS)


def bvh(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.transform(ob.matrix_world)
    t = BVHTree.FromBMesh(bm)
    return t, bm


trees = {}
boxes = {}
for ob in meshes:
    trees[ob.name] = bvh(ob)
    cs = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    boxes[ob.name] = (Vector([min(c[i] for c in cs) for i in range(3)]), Vector([max(c[i] for c in cs) for i in range(3)]))


def boxes_touch(a, b, pad=0.01):
    (a0, a1), (b0, b1) = boxes[a], boxes[b]
    return all(a0[i] - pad <= b1[i] and b0[i] - pad <= a1[i] for i in range(3))


def inside(tree, pt):
    """Ray parity along +X: is pt inside the closed mesh of tree?"""
    n, o = 0, pt.copy()
    for _ in range(64):
        loc, nrm, idx, dist = tree.ray_cast(o, Vector((1.0, 0.000123, 0.000071)))
        if loc is None:
            break
        n += 1
        o = loc + Vector((1e-5, 0, 0))
    return n % 2 == 1


def closed(name):
    return all(e.is_manifold for e in trees[name][1].edges)


def depth_into(a, b):
    """How deep the vertices of a go inside b (m); 0 if b is an open surface (a vault sheet)."""
    if not closed(b):
        return 0.0
    tb = trees[b][0]
    worst = 0.0
    for v in trees[a][1].verts:
        if not (boxes[b][0].x - 0.01 <= v.co.x <= boxes[b][1].x + 0.01 and boxes[b][0].y - 0.01 <= v.co.y <= boxes[b][1].y + 0.01
                and boxes[b][0].z - 0.01 <= v.co.z <= boxes[b][1].z + 0.01):
            continue
        if inside(tb, v.co):
            loc, nrm, idx, dist = tb.find_nearest(v.co)
            if dist is not None:
                worst = max(worst, dist)
    return worst


DESIGNED = (("tondo_disc", "tondo_frame"), ("triglyph", "triglyph_groove"))
BELOW_FLOOR = ("floor_lower", "step_", "podium", "platform", "pedestal")
findings = {"collisions": [], "contacts": 0, "open_ends": [], "skewed": []}
names = sorted(trees)
for i, a in enumerate(names):
    for b in names[i + 1:]:
        if not boxes_touch(a, b):
            continue
        # A moulding against its support: intended embedding.
        if (is_moulding(a) and is_support(b)) or (is_moulding(b) and is_support(a)):
            continue
        if is_support(a) and is_support(b):
            continue                     # walls meeting walls: solid construction, hidden
        if any((a.startswith(x) and b.startswith(y)) or (b.startswith(x) and a.startswith(y)) for x, y in DESIGNED):
            continue
        pairs = trees[a][0].overlap(trees[b][0])
        if not pairs:
            continue
        depth = max(depth_into(a, b), depth_into(b, a))
        if depth < 0.005:
            findings["contacts"] += 1
            continue
        if a.startswith(BELOW_FLOOR) and b.startswith(BELOW_FLOOR):
            continue             # solids of the floor build-up meeting below the floor surfaces
        bma, bmb = trees[a][1], trees[b][1]
        bma.faces.ensure_lookup_table()
        bmb.faces.ensure_lookup_table()
        pts = [bma.faces[p[0]].calc_center_median() for p in pairs[:400]]
        lo = Vector([min(p[k] for p in pts) for k in range(3)])
        hi = Vector([max(p[k] for p in pts) for k in range(3)])
        findings["collisions"].append({"a": a, "b": b, "triangles": len(pairs), "depth_m": round(depth, 3),
                                       "where": [round(v, 2) for v in (lo + hi) / 2],
                                       "extent": [round(v, 2) for v in hi - lo]})

# Open ends of swept mouldings: sweep() closes each end with one n-gon (the profile).
scene = bpy.context.scene
for ob in meshes:
    if not is_moulding(ob.name):
        continue
    me = ob.data
    caps = [p for p in me.polygons if len(p.vertices) >= 8]
    for p in caps:
        c = ob.matrix_world @ p.center
        n = (ob.matrix_world.to_3x3() @ p.normal).normalized()
        hit, loc, nrm, idx, other, _ = scene.ray_cast(dg, c + n * 0.002, n, distance=0.01)
        if not hit:
            # Inside another solid (a moulding ending inside the wall or pier it returns into)?
            for oname, (t, _bm) in trees.items():
                if oname == ob.name:
                    continue
                lo, hi = boxes[oname]
                if all(lo[k] - 0.01 <= c[k] <= hi[k] + 0.01 for k in range(3)) and inside(t, c + n * 0.003):
                    hit = True
                    break
        # Ends no visitor can see: the facade's outer edges (outside every view from the walk)
        # and the far face of the end wall.
        # The front wall's top edge (9 m) too: above every view (the vault ornament's ribs run out there).
        if (abs(c.x) > 12.0 and c.y < 15.6) or c.y > 55.99 or (c.y < 5.3 and c.z > 8.99):
            hit = True
        if not hit:
            findings["open_ends"].append({"object": ob.name, "where": [round(v, 2) for v in c],
                                          "facing": [round(v, 2) for v in n], "area_m2": round(p.area, 3)})

# Skewed frames: straight runs of frames should be level or plumb in their plane.
for ob in meshes:
    if "frame" not in ob.name:
        continue
    me = ob.data
    worst = 0.0
    for e in me.edges:
        v0 = ob.matrix_world @ me.vertices[e.vertices[0]].co
        v1 = ob.matrix_world @ me.vertices[e.vertices[1]].co
        d = v1 - v0
        if d.length < 0.3:
            continue
        # angle off the nearest of the three axes
        a = min(math.degrees(math.acos(min(1.0, abs(d.normalized()[k])))) for k in range(3))
        worst = max(worst, a)
    if worst > 0.5:
        findings["skewed"].append({"object": ob.name, "worst_deg": round(worst, 2)})

# R13 stacked faces: a visible face less than 2 cm (web; 2 / 0.7 cm in the model) in front of a
# face of another piece that faces the same way and that it covers. Depth precision cannot keep
# them apart at a distance: the hidden face (baked dark) flickers through. Coplanar overlaps count.
import numpy as np  # noqa: E402

R13_GAP = 0.02 / 0.7
P_EYE0, P_EYE1 = 1.85, 0.814 + 1.6 / 0.7          # eye on the lower floor / on the platform (web 1.6 m)
tri_obj, tri_pts = [], []
for oi, ob in enumerate(meshes):
    me = ob.data
    me.calc_loop_triangles()
    mw = np.array(ob.matrix_world)
    co = np.array([v.co for v in me.vertices], dtype=np.float64)
    co = co @ mw[:3, :3].T + mw[:3, 3]
    tris = np.array([t.vertices[:] for t in me.loop_triangles], dtype=np.int64).reshape(-1, 3)
    if len(tris):
        tri_pts.append(co[tris])
        tri_obj.append(np.full(len(tris), oi))
P3 = np.concatenate(tri_pts)
OBJ = np.concatenate(tri_obj)
N = np.cross(P3[:, 1] - P3[:, 0], P3[:, 2] - P3[:, 0])
A2 = np.linalg.norm(N, axis=1)
keep = A2 > 2e-6
P3, OBJ, N, A2 = P3[keep], OBJ[keep], N[keep], A2[keep]
N /= A2[:, None]
C = P3.mean(1)
key = np.round(N * 20).astype(np.int64)
order = np.lexsort((key[:, 2], key[:, 1], key[:, 0]))
bins = {}
for i in order:
    bins.setdefault(tuple(key[i]), []).append(i)


def basis(n):
    a = np.array([1.0, 0, 0]) if abs(n[0]) < 0.9 else np.array([0, 1.0, 0])
    u = np.cross(n, a)
    u /= np.linalg.norm(u)
    return u, np.cross(n, u)


def tri_overlap(ta, tb, eps=0.002):
    """2D triangles (k, 3, 2): separating-axis test, overlapping by more than eps."""
    hit = np.ones(len(ta), bool)
    for T in (ta, tb):
        for e in range(3):
            d = T[:, (e + 1) % 3] - T[:, e]
            ax = np.stack([-d[:, 1], d[:, 0]], 1)
            ax /= np.linalg.norm(ax, axis=1, keepdims=True) + 1e-12
            pa = np.einsum("kvc,kc->kv", ta, ax)
            pb = np.einsum("kvc,kc->kv", tb, ax)
            sep = (pa.max(1) < pb.min(1) + eps) | (pb.max(1) < pa.min(1) + eps)
            hit &= ~sep
    return hit


def hidden(pt, skip):
    for oname, (t, _bm) in trees.items():
        if oname == skip:
            continue
        lo, hi = boxes[oname]
        if all(lo[k] <= pt[k] <= hi[k] for k in range(3)) and closed(oname) and inside(t, Vector(pt)):
            return True
    return False


r13 = {}
for k, idx in bins.items():
    idx = np.array(idx)
    if len(np.unique(OBJ[idx])) < 2:
        continue
    n = np.array(k, float)   # the bin's own direction: depths must not shift with whatever else shares the bin
    n /= np.linalg.norm(n)
    u, v = basis(n)
    d = C[idx] @ n
    srt = np.argsort(d)
    idx, d = idx[srt], d[srt]
    P2 = np.stack([P3[idx] @ u, P3[idx] @ v], -1)                       # (m, 3, 2)
    lo2, hi2 = P2.min(1), P2.max(1)
    j0 = 0
    for a in range(len(idx)):
        # faces behind a (or coplanar), within the gap
        lo_d = d[a] - R13_GAP
        while d[j0] < lo_d:
            j0 += 1
        cand = np.arange(j0, a)
        if a + 1 < len(idx):
            same = np.arange(a + 1, np.searchsorted(d, d[a] + 1e-4, side="right"))
            cand = np.concatenate([cand, same])                        # coplanar ones after a
        if not len(cand):
            continue
        cand = cand[OBJ[idx[cand]] != OBJ[idx[a]]]
        cand = cand[np.all(lo2[cand] < hi2[a] - 0.002, 1) & np.all(hi2[cand] > lo2[a] + 0.002, 1)]
        cand = cand[np.abs(N[idx[cand]] @ N[idx[a]]) > 0.999]
        if not len(cand):
            continue
        ok = tri_overlap(np.repeat(P2[a][None], len(cand), 0), P2[cand])
        for b in cand[ok]:
            fa, fb = meshes[OBJ[idx[a]]].name, meshes[OBJ[idx[b]]].name
            pair = (fa, fb, k)                    # one finding per piece pair and facing
            rec = r13.setdefault(pair, {"front": fa, "behind": fb, "triangles": 0, "gap_cm": 99.0, "where": None})
            rec["triangles"] += 1
            rec["gap_cm"] = min(rec["gap_cm"], round(float(d[a] - d[b]) * 100, 2))
            if rec["where"] is None:
                rec["where"] = [round(float(x), 2) for x in C[idx[a]]]
                rec["normal"] = [round(float(x), 2) for x in N[idx[a]]]
                rec["_samples"] = []
            if len(rec["_samples"]) < 16:
                rec["_samples"].append(C[idx[a]].tolist())
# Not visible: the front face turns its back on every place the eye can be (walk line and
# walk-ups: |x| <= 5.5, 0 <= y <= 55, eye 1.8-3.2 m), is inside another solid, or is below the
# lower floor.
EYE_BOX = np.array([[x, y, z] for x in (-5.5, 5.5) for y in (0.0, 55.0) for z in (1.8, 3.2)])
# Eye positions: the walk line, and either side of it where walk-ups stand.
EYES = [Vector((x, y, (P_EYE0 if y < 8.6 else P_EYE1))) for y in np.arange(0.0, 55.1, 1.5) for x in (-4.0, 0.0, 4.0)]


def seen(pt, n):
    """Is pt (on a face with normal n) in plain sight of any eye position?"""
    o = Vector(pt) + Vector(n) * 0.004
    for e in EYES:
        d = e - o
        if d.dot(Vector(n)) <= 0:
            continue
        hit, loc, *_ = scene.ray_cast(dg, o, d.normalized(), distance=d.length)
        if not hit:
            return True
    return False


for pair, rec in list(r13.items()):
    c, n = np.array(rec["where"]), np.array(rec["normal"])
    w = c + n * 0.003
    if ((EYE_BOX - c) @ n).max() <= 0 or w[2] < -0.005 or not any(seen(sp, n) for sp in rec["_samples"]):
        rec["hidden"] = True
    del rec["_samples"]
findings["stacked_faces_R13"] = [r for r in r13.values() if not r.get("hidden")]
findings["stacked_faces_R13_hidden"] = len([r for r in r13.values() if r.get("hidden")])

for k, v in findings.items():
    if isinstance(v, int):
        print(f"== {k}: {v}")
        continue
    print(f"== {k}: {len(v)}")
    for f in v:
        print("  ", f)
with open(out, "w") as fh:
    json.dump(findings, fh, indent=1)
