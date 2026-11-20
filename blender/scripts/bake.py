"""Bake the finished hall's lighting (Cycles, light linking honoured) into lightmap atlases and
export it for the web as glTF with separate PNG textures.

Run on the saved finished hall (build.py writes it):
  blender -b blender/athens-hall.blend -P blender/scripts/bake.py -- <out_dir> [rough|final]
Usually through tools/bake_hall.sh, which then denoises the atlases and packs the GLB.

What it does:
- removes the painting placeholders (the web hangs the real paintings);
- groups the meshes by where they stand along the hall (params.BAKE_GROUPS); each group gets one
  shared lightmap UV layout (smart project, then packed together) and one atlas, sized from the
  group's surface area and the texel density (params.BAKE[quality]["density"], px per metre);
- bakes Cycles "Combined" (albedo x direct + indirect light, no glossy) into each atlas, with
  every light-linking set-up of the scene in place (the bake honours it: tools/stage2/);
- joins each group into one mesh, keeps only the lightmap UV, gives it the atlas as its only
  texture, scales to the web's 70 % and exports glTF (Y up) + PNG atlases.
"""
import json
import math
import os
import sys
import time
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import params as P  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = Path(argv[0]) if argv else HERE.parent / "build" / "bake"
QUALITY = argv[1] if len(argv) > 1 else P.BAKE_QUALITY
CFG = P.BAKE[QUALITY]
OUT.mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene
t_start = time.time()


def log(*a):
    print(f"[bake {time.time() - t_start:7.1f}s]", *a, flush=True)


# ---------------------------------------------------------------- scene set-up
for ob in list(bpy.data.objects):
    if ob.type == "MESH" and ob.get("kind") == "painting":
        bpy.data.objects.remove(ob)

scene.render.engine = "CYCLES"
prefs = bpy.context.preferences.addons["cycles"].preferences
try:
    prefs.compute_device_type = "METAL"
    prefs.get_devices()
    for d in prefs.devices:
        d.use = True
    scene.cycles.device = "GPU"
except Exception as exc:  # fall back to CPU
    log("GPU unavailable:", exc)
scene.cycles.samples = CFG["samples"]
# Same colour pipeline as build.py's renders (the .blend is saved before build.py sets it):
# Standard view transform, no look, so the atlases hold the colours calibrated on the fresco.
scene.view_settings.view_transform, scene.view_settings.look = "Standard", "None"
scene.view_settings.exposure, scene.view_settings.gamma = P.EXPOSURE, 1.0
# The world shows the fresco's blue to camera rays and lights with a warmer colour (finish.light).
# Bake rays start as camera rays, so pin the switch to the light colour: the visible sky is the
# web page's background, not part of the bake.
for link in list(scene.world.node_tree.links):
    if link.from_node.type == "LIGHT_PATH":
        to = link.to_socket
        scene.world.node_tree.links.remove(link)
        to.default_value = 0.0
scene.cycles.use_denoising = False          # bakes are denoised afterwards (tools/denoise_lightmaps.py)
bake = scene.render.bake
bake.use_pass_direct = bake.use_pass_indirect = True
bake.use_pass_diffuse = bake.use_pass_emit = True
bake.use_pass_glossy = bake.use_pass_transmission = False
bake.margin, bake.margin_type = CFG["margin"], "EXTEND"
bake.use_clear = True
bake.target = "IMAGE_TEXTURES"


def is_occluder_only(ob):
    return any(tag in ob.name for tag in P.BAKE_OCCLUDERS_ONLY)


meshes = [ob for ob in bpy.data.objects if ob.type == "MESH" and ob.name not in P.BAKE_SKIP
          and not is_occluder_only(ob)]
# Degenerate faces (zero area, from sweeps and booleans) make the UV packer collapse a whole group.
for ob in meshes:
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.dissolve_degenerate(bm, dist=1e-5, edges=bm.edges[:])
    bad = [f for f in bm.faces if f.calc_area() < 1e-8]
    if bad:
        bmesh.ops.delete(bm, geom=bad, context="FACES")
    bm.to_mesh(ob.data)
    bm.free()


def cull_hidden(ob):
    """Delete faces no visitor can see, so they take no atlas space:
    - beyond the hall's side walls behind the facade (every vertex at |x| > HALL_X, y > facade front);
    - undersides of floors and steps;
    - the far side of the end wall;
    - the outer shells of the drum and dome."""
    mw = ob.matrix_world
    rot = mw.to_3x3()
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    ycen = (P.CROSS_Y0 + P.CROSS_Y1) / 2
    gone = []
    for f in bm.faces:
        vs = [mw @ v.co for v in f.verts]
        n = (rot @ f.normal).normalized()
        c = sum(vs, Vector()) / len(vs)
        if all(abs(v.x) > P.BAKE_HALL_X and v.y > P.FACADE_Y0 + 0.05 for v in vs):
            gone.append(f)
        elif n.z < -0.99 and c.z < P.PLATFORM_Z + 0.05:
            gone.append(f)
        elif all(v.y > P.ARM2_Y1 + P.END_T - 0.01 for v in vs) and n.y > 0.9:
            gone.append(f)
        elif ob.name.startswith(("drum", "dome")) and c.z > P.DRUM_Z0 + 0.5:
            radial = Vector((c.x, c.y - ycen, 0))
            out = Vector((c.x, c.y - ycen, c.z - P.DRUM_Z1 if c.z > P.DRUM_Z1 else 0.0))
            if radial.length > P.CROSS_HALF + 0.35 and n.dot(out) > 0.2:
                gone.append(f)
    if gone:
        bmesh.ops.delete(bm, geom=gone, context="FACES")
    bm.to_mesh(ob.data)
    bm.free()
    return len(gone)


culled = sum(cull_hidden(ob) for ob in meshes)
log(f"culled {culled} hidden faces")
meshes = [ob for ob in meshes if ob.data.polygons]


def centre_y(ob):
    cs = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return sum(c.y for c in cs) / 8


groups = {name: [] for name, _, _ in P.BAKE_GROUPS}
for ob in meshes:
    y = centre_y(ob)
    name = next(n for n, y0, y1 in P.BAKE_GROUPS if y0 <= y < y1)
    groups[name].append(ob)


def area(ob):
    return sum(p.area for p in ob.data.polygons) * (ob.matrix_world.to_scale().x ** 2)


def density_scale(ob):
    return P.BAKE_DENSITY_SCALE.get(ob.name, 1.0)


# ---------------------------------------------------------------- lightmap UVs per group
def split_long(ob, step):
    """Cut the mesh along a world grid (every `step` m in X, Y and Z) and split it there, so no UV
    island is longer than that: long mouldings, floors and the coffers' rib lattice would
    otherwise each be one island whose bounding box swallows the atlas."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    mw = ob.matrix_world
    inv = mw.inverted()
    planes = []
    for axis in range(3):
        lo = min((mw @ v.co)[axis] for v in bm.verts)
        hi = max((mw @ v.co)[axis] for v in bm.verts)
        if hi - lo <= step:
            continue
        k = math.floor(lo / step) + 1
        while k * step < hi - 1e-4:
            no = Vector([1.0 if i == axis else 0.0 for i in range(3)])
            co = Vector([k * step if i == axis else 0.0 for i in range(3)])
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-5,
                                   plane_co=inv @ co, plane_no=(inv.to_3x3().transposed() @ no).normalized())
            planes.append((axis, k * step))
            k += 1
    # Split every edge that lies in one of the cut planes (found after all cuts: later cuts
    # subdivide the edges of earlier ones).
    if planes:
        world = {v: mw @ v.co for v in bm.verts}
        cut = [e for e in bm.edges
               if any(abs(world[e.verts[0]][ax] - val) < 1e-4 and abs(world[e.verts[1]][ax] - val) < 1e-4
                      for ax, val in planes)]
        if cut:
            bmesh.ops.split_edges(bm, edges=cut)
    bmesh.ops.dissolve_degenerate(bm, dist=1e-5, edges=bm.edges[:])
    bad = [f for f in bm.faces if f.calc_area() < 1e-7]
    if bad:
        bmesh.ops.delete(bm, geom=bad, context="FACES")
    bm.to_mesh(ob.data)
    bm.free()


def unwrap_one(ob):
    """Smart-project one object on its own (multi-object packing is unreliable here: some groups
    came out collapsed or overlapping). Returns the share of the unit square its islands cover."""
    split_long(ob, P.BAKE_ISLAND_MAX)
    me = ob.data
    uv = me.uv_layers.get("lightmap") or me.uv_layers.new(name="lightmap")
    me.uv_layers.active = uv
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.0, area_weight=0.0,
                             correct_aspect=True, scale_to_bounds=False)
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.pack_islands(udim_source="ACTIVE_UDIM", rotate=True, scale=True, margin_method="FRACTION",
                            margin=0.01, shape_method="AABB")
    bpy.ops.object.mode_set(mode="OBJECT")
    d = me.uv_layers["lightmap"].data
    if d:
        lo = Vector((min(x.uv.x for x in d), min(x.uv.y for x in d)))
        hi = Vector((max(x.uv.x for x in d), max(x.uv.y for x in d)))
        ext = max(hi.x - lo.x, hi.y - lo.y, 1e-6)
        for x in d:
            x.uv = (x.uv - lo) / ext
    return max(uv_coverage([ob]), 1e-4)


def islands(ob):
    """UV islands of ob's lightmap layer: lists of loop indices, joined where faces share a
    vertex with the same UV."""
    me = ob.data
    uv = me.uv_layers["lightmap"].data
    parent = list(range(len(me.polygons)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    seen = {}
    for p in me.polygons:
        for li in p.loop_indices:
            key = (me.loops[li].vertex_index, round(uv[li].uv.x, 5), round(uv[li].uv.y, 5))
            q = seen.setdefault(key, p.index)
            if q != p.index:
                ra, rb = find(q), find(p.index)
                if ra != rb:
                    parent[ra] = rb
    out = {}
    for p in me.polygons:
        out.setdefault(find(p.index), []).extend(p.loop_indices)
    return list(out.values())


def layout(objs):
    """Unwrap each object on its own, then pack every island of every object into one page with
    a shelf packer, each island scaled to the texel density (px per metre) of its object."""
    m = CFG["gap"]                              # px of empty space round each island
    items = []                                  # (h_px, w_px, ob, loops, lo, scale)
    for ob in objs:
        t0 = time.time()
        unwrap_one(ob)
        a2 = uv_coverage([ob])
        uv = ob.data.uv_layers["lightmap"].data
        me = ob.data
        mw = ob.matrix_world
        loop_face = {}
        for p in me.polygons:
            for li in p.loop_indices:
                loop_face[li] = p
        for loops in islands(ob):
            # Scale each island on its own: its 3D area and UV area give px per UV unit.
            faces = {loop_face[i].index: loop_face[i] for i in loops}.values()
            a3 = sum(p.area for p in faces) * (mw.to_scale().x ** 2)
            a2i = 0.0
            for p in faces:
                pts = [uv[i].uv for i in p.loop_indices]
                a2i += abs(sum(pts[j].x * pts[j - 1].y - pts[j - 1].x * pts[j].y for j in range(len(pts)))) / 2
            f = CFG["density"] * density_scale(ob) * math.sqrt(a3 / a2i) if a2i > 1e-12 else 1.0
            xs = [uv[i].uv.x for i in loops]
            ys = [uv[i].uv.y for i in loops]
            lo = Vector((min(xs), min(ys)))
            w, h = (max(xs) - lo.x) * f, (max(ys) - lo.y) * f
            rot = w > h * 1.5                       # lay long islands flat
            if rot:
                w, h = h, w
            items.append([h + 2 * m + 1, w + 2 * m + 1, ob, loops, lo, f, rot])
        if time.time() - t0 > 5:
            log(f"  slow unwrap: {ob.name} {time.time() - t0:.0f}s")
    items.sort(key=lambda it: -it[0])
    if os.environ.get("BAKE_DEBUG"):
        log("  largest islands (h, w px):", [(round(it[0]), round(it[1]), it[2].name) for it in items[:6]])
        it = items[0]
        vs = [it[2].matrix_world @ it[2].data.vertices[it[2].data.loops[i].vertex_index].co for i in it[3]]
        log("  largest island 3D bbox:", [round(min(v[k] for v in vs), 2) for k in range(3)],
            [round(max(v[k] for v in vs), 2) for k in range(3)], len(it[3]), "loops")
        log(f"  {len(items)} islands, {sum(it[0] * it[1] for it in items) / 1e6:.2f} Mpx")
    total = sum(it[0] * it[1] for it in items)
    page = max(256, int(math.ceil(math.sqrt(total / 0.8) / 64)) * 64)
    shrink = 1.0
    while True:
        x = y = shelf = 0.0
        pos = []
        for it in items:
            h, w = it[0] * shrink, it[1] * shrink
            if x + w > page:
                x, y, shelf = 0.0, y + shelf, 0.0
            pos.append((x, y))
            x += w
            shelf = max(shelf, h)
        if y + shelf <= page:
            break
        if page < CFG["max_size"]:
            page = min(CFG["max_size"], page + 64)
        else:
            shrink *= 0.97
    page_h = int(math.ceil((y + shelf) / 64)) * 64        # trim the unused rows: atlases need not be square
    for it, (x0, y0) in zip(items, pos):
        h, w, ob, loops, lo, f, rot = it
        uv = ob.data.uv_layers["lightmap"].data
        k = f * shrink
        for i in loops:
            d = (uv[i].uv - lo) * k
            if rot:
                d = Vector((d.y, d.x))
            uv[i].uv = Vector(((x0 + m * shrink + d.x) / page, (y0 + m * shrink + d.y) / page_h))
    if shrink < 1.0:
        log(f"  atlas capped at {page}: density x{shrink:.2f}")
    return page, page_h


def uv_coverage(objs):
    tot = 0.0
    for ob in objs:
        uv = ob.data.uv_layers["lightmap"].data
        for p in ob.data.polygons:
            pts = [uv[i].uv for i in p.loop_indices]
            tot += abs(sum(pts[i].x * pts[i - 1].y - pts[i - 1].x * pts[i].y for i in range(len(pts)))) / 2
    return tot


# ---------------------------------------------------------------- bake each group
report = {"quality": QUALITY, "config": CFG, "groups": {}}
targets = {}
ONLY = os.environ.get("BAKE_ONLY")
for name, objs in groups.items():
    if not objs or (ONLY and name != ONLY):
        continue
    size, size_h = layout(objs)
    eff = CFG["density"]
    log(f"group {name}: {len(objs)} objects, {sum(area(o) for o in objs):.0f} m2, atlas {size} x {size_h}")
    lo, hi = [9.0, 9.0], [-9.0, -9.0]
    for ob in objs:
        for d in ob.data.uv_layers["lightmap"].data:
            lo = [min(lo[0], d.uv.x), min(lo[1], d.uv.y)]
            hi = [max(hi[0], d.uv.x), max(hi[1], d.uv.y)]
    cov = uv_coverage(objs)
    log(f"  lightmap UV bounds {lo[0]:.3f},{lo[1]:.3f} .. {hi[0]:.3f},{hi[1]:.3f}, atlas used {cov:.0%}")
    if os.environ.get("BAKE_DRY"):
        continue
    img = bpy.data.images.new(f"lightmap_{name}", size, size_h, alpha=True, float_buffer=True)  # alpha 0 = unbaked
    targets[name] = img
    mats = {m for ob in objs for m in ob.data.materials if m}
    for m in mats:
        nt = m.node_tree
        node = nt.nodes.get("bake_target") or nt.nodes.new("ShaderNodeTexImage")
        node.name = "bake_target"
        node.image = img
        nt.nodes.active = node
    bpy.ops.object.select_all(action="DESELECT")
    for ob in objs:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    t0 = time.time()
    bpy.ops.object.bake(type="COMBINED")
    path = OUT / f"lightmap_{name}.png"
    img.save_render(str(path), scene=scene)     # view transform (Standard) -> sRGB PNG, like the renders
    report["groups"][name] = {"objects": len(objs), "area_m2": round(sum(area(o) for o in objs), 1),
                              "atlas": [size, size_h], "density_px_per_m": round(eff, 1),
                              "bake_s": round(time.time() - t0, 1)}
    log(f"baked {name} in {time.time() - t0:.0f}s -> {path.name}")

# ---------------------------------------------------------------- export (70 %, one mesh per group)
for ob in list(bpy.data.objects):
    if ob.type == "MESH" and (is_occluder_only(ob) or ob.get("kind") == "painting"):
        bpy.data.objects.remove(ob)
exported = []
for name, objs in groups.items():
    if not objs:
        continue
    bpy.ops.object.select_all(action="DESELECT")
    for ob in objs:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = ob.data.name = f"hall_{name}"
    me = ob.data
    for uv in [u for u in me.uv_layers if u.name != "lightmap"]:
        me.uv_layers.remove(uv)
    m = bpy.data.materials.new(f"baked_{name}")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(OUT / f"lightmap_{name}.png"))
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    me.materials.clear()
    me.materials.append(m)
    exported.append(ob)
for name in P.BAKE_SKIP:                       # flat colour, unlit in the web
    ob = bpy.data.objects.get(name)
    if ob:
        m = bpy.data.materials.new(f"flat_{name}")
        m.use_nodes = True
        m.node_tree.nodes.get("Principled BSDF").inputs["Base Color"].default_value = (0.42, 0.42, 0.33, 1)
        ob.data.materials.clear()
        ob.data.materials.append(m)
        exported.append(ob)
k = P.SCALE
for ob in exported:
    ob.data.transform(ob.matrix_world)
    ob.matrix_world = Matrix.Identity(4)
    ob.data.transform(Matrix.Scale(k, 4))
bpy.ops.object.select_all(action="DESELECT")
for ob in exported:
    ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT / "hall.gltf"), export_format="GLTF_SEPARATE", use_selection=True,
                          export_apply=True, export_cameras=False, export_lights=False, export_extras=False,
                          export_yup=True, export_normals=False, export_tangents=False,
                          export_image_format="AUTO")
report["seconds"] = round(time.time() - t_start, 1)
(OUT / "bake-report.json").write_text(json.dumps(report, indent=2))
log("exported", OUT / "hall.gltf")
