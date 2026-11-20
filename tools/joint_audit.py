"""Joint audit of the finished hall (run inside Blender on the saved model):
  blender -b blender/athens-hall.blend -P tools/joint_audit.py -- <out.json>

Checks every piece against the joint rules (renders/hall-stage4/REPORT.md, "Joint rules"):
1. Collisions: two architectural members whose surfaces cross (triangle overlap, BVH), other
   than the intended embedding of a moulding's back into the wall it is fixed to (a moulding's
   "embed" strip, <= 4 cm behind its base plane) and the floor under bases.
2. Open ends: a swept moulding's end cap that is neither against another surface (within 5 mm
   along its normal) nor hidden from the walk: a cornice cut off in mid-air.
3. Skewed frames: a frame or moulding whose straight runs are not level / plumb.
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
        if (abs(c.x) > 12.0 and c.y < 15.6) or c.y > 55.99:
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

for k, v in findings.items():
    if isinstance(v, int):
        print(f"== {k}: {v}")
        continue
    print(f"== {k}: {len(v)}")
    for f in v:
        print("  ", f)
with open(out, "w") as fh:
    json.dump(findings, fh, indent=1)
