"""Bake the finished hall's lighting (Cycles, light linking honoured) into lightmap atlases and
export it for the web as glTF with separate PNG textures.

Run on the saved finished hall (build.py writes it):
  blender -b blender/athens-hall.blend -P blender/scripts/bake.py -- <out_dir> [rough|final]
Usually through tools/bake_hall.sh, which then denoises the atlases and packs the GLB.

What it does:
- removes the painting placeholders (the web hangs the real paintings);
- groups the meshes by where they stand along the hall (params.BAKE_GROUPS); each group gets one
  lightmap UV layout (smart project per object; curved parts cut on a world grid, flat faces left
  whole; islands packed together) and one atlas, sized from the group's surface area and the
  texel density (params.BAKE[quality]["density"], px per metre);
- bakes the light alone (diffuse direct + indirect, every light-linking set-up of the scene in
  place), the per-face factor, and where each texel is (world position, normal, island, light
  class); saves them as bake_<group>.npz for tools/lightmap_post.py, which denoises, stitches the
  light across island cuts, multiplies the factor in and writes the atlases;
- joins each group into one mesh, keeps the detail and lightmap UVs, one material per detail key,
  scales to the web's 70 % and exports glTF (Y up).
"""
import json
import math
import os
import sys
import time
from pathlib import Path

import bmesh
import bpy
import numpy as np
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
# White balance (params.BOUNCE_CHROMA): the colours the bake's light bounces off, desaturated.
# The lightmaps hold light only; what the web shows of a surface's own colour comes from the
# materials' albedo_dark/albedo_light (detail tiles), which this leaves alone.
def _desat(c):
    y = 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    return [y + (v - y) * P.BOUNCE_CHROMA for v in c[:3]] + list(c[3:])


n_cols = n_imgs = 0
for mat in bpy.data.materials:
    if not mat.use_nodes:
        continue
    for node in mat.node_tree.nodes:
        if node.type == "RGB":
            node.outputs[0].default_value = _desat(node.outputs[0].default_value); n_cols += 1
        for sock in node.inputs:
            if sock.type == "RGBA" and not sock.is_linked:
                sock.default_value = _desat(sock.default_value); n_cols += 1
for im in bpy.data.images:
    if im.is_float and not im.filepath and im.size[0] > 0:      # the floors' designed tiles
        a = np.empty(im.size[0] * im.size[1] * 4, np.float32); im.pixels.foreach_get(a)
        a = a.reshape(-1, 4); y = a[:, :3] @ np.array([0.2126, 0.7152, 0.0722], np.float32)
        a[:, :3] = y[:, None] + (a[:, :3] - y[:, None]) * P.BOUNCE_CHROMA
        im.pixels.foreach_set(a.ravel()); im.pack(); n_imgs += 1
log(f"white balance: {n_cols} colours, {n_imgs} images at {P.BOUNCE_CHROMA} of their saturation")
scene.cycles.use_denoising = False          # denoised afterwards, with the stitch (tools/lightmap_post.py)
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
    - beyond the hall's side walls behind the facade (every vertex at |x| > HALL_X, y > facade front),
      except in the niches' shells: the facade niches' outer halves lie past HALL_X;
    - undersides of floors and steps;
    - the far side of the end wall;
    - the outer shells of the drum and dome;
    - the pendentives' box sides at x = +-CROSS_HALF (they face into the crossing's side walls);
    - the crossing walls' faces toward the crossing above the drum's base. The walls rise 1.5 m
      past it (their nave sides show there), and the drum's inside is tangent to those faces on
      the four axes: along each tangent line the two coincide and fight, a flickering black line
      looking up into the dome (Maria, 2026-11-21). Above the base they are behind the drum
      everywhere else, so they are cut at the base and dropped."""
    mw = ob.matrix_world
    rot = mw.to_3x3()
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    ycen = (P.CROSS_Y0 + P.CROSS_Y1) / 2
    crossing_wall = ob.name.startswith(("arch_front", "arch_back", "crossing_side"))
    shell = ob.name.startswith(("facade_shell", "shell_"))   # the facade niches reach past HALL_X (deco round)
    if crossing_wall:
        inv = mw.inverted()
        no = (mw.to_3x3().transposed() @ Vector((0, 0, 1))).normalized()
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
                               plane_co=inv @ Vector((0, 0, P.DRUM_Z0)), plane_no=no)
    gone = []
    for f in bm.faces:
        vs = [mw @ v.co for v in f.verts]
        n = (rot @ f.normal).normalized()
        c = sum(vs, Vector()) / len(vs)
        if all(abs(v.x) > P.BAKE_HALL_X and v.y > P.FACADE_Y0 + 0.05 for v in vs) and not shell:
            gone.append(f)
        elif n.z < -0.99 and c.z < P.PLATFORM_Z + 0.05:
            gone.append(f)
        elif all(v.y > P.ARM2_Y1 + P.END_T - 0.01 for v in vs) and n.y > 0.9:
            gone.append(f)
        elif crossing_wall and min(v.z for v in vs) > P.DRUM_Z0 - 1e-4 and (
                (abs(c.y - P.CROSS_Y1) < 0.02 and n.y < -0.98) or (abs(c.y - P.CROSS_Y0) < 0.02 and n.y > 0.98)
                or (abs(abs(c.x) - P.CROSS_HALF) < 0.02 and abs(n.x) > 0.98 and n.x * c.x < 0)):
            gone.append(f)
        elif ob.name == "pendentives" and abs(n.x) > 0.99:
            gone.append(f)       # the box's sides at x = +-CROSS_HALF, facing into the side walls
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
    return next((v for k, v in P.BAKE_DENSITY_SCALE.items() if ob.name.startswith(k)), 1.0)


# ---------------------------------------------------------------- lightmap UVs per group
def is_flat(f, rot):
    """A face whose normal is on a world axis: walls, floors, ceilings, the flat faces of
    mouldings. Stage 5: these stay whole in the lightmap (no grid cuts), so a flat wall is one
    island and its light has no seams to step at."""
    n = (rot @ f.normal).normalized()
    return max(abs(n.x), abs(n.y), abs(n.z)) > 0.999


def keeps_flat_whole(ob):
    """Walls, floors, ceilings: their flat faces stay one island each. Mouldings (whose flat
    faces follow a plan with breaks and returns, so one island's box would be mostly empty) are
    cut on the grid like curved parts; tools/lightmap_post.py stitches their cuts."""
    return not any(m in ob.name for m in P.BAKE_CUT_MEMBERS)


def split_long(ob, step):
    """Cut the mesh along a world grid (every `step` m in X, Y and Z) and split it there, so no UV
    island is longer than that: the coffers' rib lattice, the vaults and the mouldings would
    otherwise each be one island whose bounding box swallows the atlas. Walls, floors and
    ceilings keep their flat faces whole (keeps_flat_whole, is_flat): one island per flat face,
    so their light has no cut to step at."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    mw = ob.matrix_world
    inv = mw.inverted()
    rot = mw.to_3x3()
    whole = keeps_flat_whole(ob)
    grid = bm.faces.layers.int.get("lm_island")        # faces laid on the grid already: never cut
    planes = []
    for axis in range(3):
        lo = min((mw @ v.co)[axis] for v in bm.verts)
        hi = max((mw @ v.co)[axis] for v in bm.verts)
        if hi - lo <= step:
            continue
        k = math.floor(lo / step) + 1
        while k * step < hi - 1e-4:
            curved = [f for f in bm.faces if not (whole and is_flat(f, rot)) and not (grid and f[grid] >= 0)]
            if not curved:
                break
            geom = list({e for f in curved for e in f.edges}) + curved + list({v for f in curved for v in f.verts})
            no = Vector([1.0 if i == axis else 0.0 for i in range(3)])
            co = Vector([k * step if i == axis else 0.0 for i in range(3)])
            bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-5,
                                   plane_co=inv @ co, plane_no=(inv.to_3x3().transposed() @ no).normalized())
            planes.append((axis, k * step))
            k += 1
    # Split every edge of a curved face that lies in one of the cut planes (found after all
    # cuts: later cuts subdivide the edges of earlier ones).
    if planes:
        world = {v: mw @ v.co for v in bm.verts}
        cut = [e for e in bm.edges
               if any(not (whole and is_flat(f, rot)) for f in e.link_faces)
               and not (grid and any(f[grid] >= 0 for f in e.link_faces))
               and any(abs(world[e.verts[0]][ax] - val) < 1e-4 and abs(world[e.verts[1]][ax] - val) < 1e-4
                       for ax, val in planes)]
        if cut:
            bmesh.ops.split_edges(bm, edges=cut)
    bmesh.ops.dissolve_degenerate(bm, dist=1e-5, edges=bm.edges[:])
    bad = [f for f in bm.faces if f.calc_area() < 1e-7]
    if bad:
        bmesh.ops.delete(bm, geom=bad, context="FACES")
    bm.to_mesh(ob.data)
    bm.free()


def dome_unwrap(ob):
    """The coffered dome's lightmap UVs, its coffers laid on the texel grid (round 11).
    - Each ring of coffers is unrolled flat: round the ring R cos(phi_mid) theta (true to scale at
      the ring's middle, within 3 % on the lowest ring and 9 % on the top one), up the meridian
      R phi. Every coffer is then an upright rectangle in the atlas, its steps along the texel rows
      and columns, so all 28 coffers of a ring take the light alike. The azimuthal projection used
      before turned each column by its angle round the dome: the steps, a texel wide, crossed the
      grid at that angle and baked as dashed, stepped lines, different in every coffer (Maria saw
      them as dark wavy streaks along the lowest ring, 2026-11-22).
    - Each ring is cut in two halves (theta 0 and pi, on a rib's middle line), one island each, so
      no island is longer than half a ring; the plain band at the springing joins the lowest ring.
      tools/lightmap_post.py stitches the light across the cuts, which lie on the plain rib.
    - Inside a coffer every point is drawn in towards the coffer's middle by its depth (round 7:
      each sunk level shrinks round the middle), so a step wall opens into a band about as wide as
      it is deep between the levels it joins, and keeps its own texels.
    - The smooth band from the top ring to the oculus' ring keeps the azimuthal equidistant
      projection about the crown (no coffers there), as its own island.
    The density is params.BAKE_DENSITY_SCALE["dome_coffers"]: at 16 px/m the lowest ring's step
    walls (6.6 cm deep) and treads (6.5-14 cm) were one or two texels, so each texel mixed a
    step's faces, and the up-facing step walls, which no visitor sees, darkened the treads beside
    them. layout() leaves these islands unturned (GRID_ALIGNED)."""
    me = ob.data
    for uvl in [u for u in me.uv_layers if u.name not in ("detail", "lightmap")]:
        me.uv_layers.remove(uvl)
    if "detail" not in me.uv_layers:
        me.uv_layers.new(name="detail")
    uv = me.uv_layers.get("lightmap") or me.uv_layers.new(name="lightmap")
    mw = ob.matrix_world
    c0 = Vector((0, (P.CROSS_Y0 + P.CROSS_Y1) / 2, P.DRUM_Z1))
    R = P.CROSS_HALF
    cols, rings = P.DOME_COFFER_COUNT, P.DOME_COFFER_RINGS
    dth = 2 * math.pi / cols
    phis = [P.DOME_BASE_BAND]
    for _ in range(rings):
        a = phis[-1]
        phis.append(a + dth * math.cos(a + dth * math.cos(a) / 2))
    halves = 2
    per = cols // halves
    tau = 2 * math.pi
    for p in me.polygons:
        cw = mw @ p.center - c0
        ef = math.atan2(cw.z, math.hypot(cw.x, cw.y))
        tf = math.atan2(cw.y, cw.x) % tau
        loops = [(li, mw @ me.vertices[me.loops[li].vertex_index].co - c0) for li in p.loop_indices]
        if ef > phis[-1]:
            # the smooth band to the oculus: azimuthal equidistant about the crown, set apart
            for li, w in loops:
                rho = R * (math.pi / 2 - math.atan2(w.z, math.hypot(w.x, w.y)))
                t = math.atan2(w.y, w.x)
                uv.data[li].uv = (rho * math.cos(t), rho * math.sin(t) - 20.0)
            continue
        i = max((k for k in range(rings) if phis[k] <= ef), default=0)    # the springing's band: ring 0
        j = min(int(tf // dth), cols - 1)
        em = (phis[i] + phis[i + 1]) / 2
        sc = R * math.cos(em)                                             # m per radian round the ring
        s_mid, v_mid = sc * (j + 0.5) * dth, R * em
        half = 0.5 * min(sc * dth, R * (phis[i + 1] - phis[i]))
        lift = 10.0 * (i * halves + j // per)                            # each half ring its own island
        for li, w in loops:
            t = math.atan2(w.y, w.x)
            t = tf + (t - tf + math.pi) % tau - math.pi                  # on the face's side of the cut at 0
            s, v = sc * t, R * math.atan2(w.z, math.hypot(w.x, w.y))
            depth = w.length - R
            if depth > 1e-4:
                k = max(0.2, 1 - depth / half)
                s, v = s_mid + (s - s_mid) * k, v_mid + (v - v_mid) * k
            uv.data[li].uv = (s, v + lift)
    return max(uv_coverage([ob]), 1e-4)


# Objects whose lightmap islands are already laid along the texel grid (dome_unwrap): layout()
# does not turn them to their mean edge angle (the drawn-in step walls' slanted corner edges
# could tilt a half ring a little, and its rows would then cross the texel rows along its length).
GRID_ALIGNED = ("dome_coffers",)


def pendentive_uvs(ob):
    """Round 12: each pendentive one lightmap island. Its faces on the sphere (radius CROSS_HALF
    sqrt 2 about the crossing's middle at the springing) are mapped by an azimuthal equidistant
    projection about the direction of their quadrant's middle (true to scale along every great
    circle through it, within 4 % across the triangle), as "lightmap_grid" with "lm_island" the
    quadrant; any other face keeps the usual unwrap. Smart project and the grid cuts had broken the
    four triangles into hundreds of islands, their light stepping at every cut."""
    me = ob.data
    mw = ob.matrix_world
    C = Vector((0, (P.CROSS_Y0 + P.CROSS_Y1) / 2, P.SPRING_Z))
    Rs = P.CROSS_HALF * math.sqrt(2)
    me.uv_layers.new(name="lightmap_grid")
    me.attributes.new("lm_island", "INT", "FACE")
    me.attributes.new("lm_density", "FLOAT", "FACE")
    # fetched after all three exist: adding an attribute can leave earlier Python references stale
    uv, isl, den = me.uv_layers["lightmap_grid"], me.attributes["lm_island"], me.attributes["lm_density"]
    quad = {}
    for p in me.polygons:
        c = mw @ p.center - C
        if abs(c.length - Rs) > 0.03:
            isl.data[p.index].value, den.data[p.index].value = -1, 1.0
            continue
        quad.setdefault((c.x > 0, c.y > 0), []).append(p)
    for qi, (key, faces) in enumerate(sorted(quad.items())):
        mid = sum(((mw @ p.center - C) * p.area for p in faces), Vector()).normalized()
        e1 = Vector((0, 0, 1)).cross(mid).normalized()             # horizontal across the quadrant
        e2 = mid.cross(e1)
        for p in faces:
            isl.data[p.index].value, den.data[p.index].value = qi, 1.0
            for li in p.loop_indices:
                w = (mw @ me.vertices[me.loops[li].vertex_index].co - C).normalized()
                ang = math.acos(max(-1.0, min(1.0, w.dot(mid))))
                t = w - mid * w.dot(mid)
                t = t.normalized() if t.length > 1e-9 else e1
                uv.data[li].uv = (Rs * ang * t.dot(e1) + 100.0 * qi, Rs * ang * t.dot(e2))


def grid_unwrap(ob):
    """Objects whose faces carry their own lightmap UVs on the texel grid for some or all faces
    ("lightmap_grid", face attribute "lm_island" >= 0: finish.coffer_sheet's unrolled sheets,
    pendentive_uvs): those faces keep them, one island per "lm_island", set apart from each other;
    the other faces are cut and smart-projected as unwrap_one does. layout() leaves the grid
    islands unturned and scales each by its faces' "lm_density"."""
    me = ob.data
    grid_faces = [p.index for p in me.polygons if me.attributes["lm_island"].data[p.index].value >= 0]
    rest = len(grid_faces) < len(me.polygons)
    if rest:
        split_long(ob, P.BAKE_ISLAND_MAX)                 # cuts only the other faces
    me = ob.data
    # Read into lists first: adding UV layers below can leave attribute references stale.
    gl = [d.value for d in me.attributes["lm_island"].data]
    gdata = [d.uv.copy() for d in me.uv_layers["lightmap_grid"].data]
    for uvl in [u for u in me.uv_layers if u.name not in ("detail", "lightmap")]:
        me.uv_layers.remove(uvl)
    if "detail" not in me.uv_layers:            # created first: TEXCOORD_0 in the glTF
        me.uv_layers.new(name="detail")
    uv = me.uv_layers.get("lightmap") or me.uv_layers.new(name="lightmap")
    me.uv_layers.active = uv
    if rest:
        for p in me.polygons:
            p.select = gl[p.index] < 0
        bpy.ops.object.select_all(action="DESELECT")
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        bpy.context.tool_settings.mesh_select_mode = (False, False, True)     # the faces' own selection
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.0, area_weight=0.0,
                                 correct_aspect=True, scale_to_bounds=False)
        bpy.ops.uv.select_all(action="SELECT")
        bpy.ops.uv.pack_islands(udim_source="ACTIVE_UDIM", rotate=True, scale=True, margin_method="FRACTION",
                                margin=0.01, shape_method="AABB")
        bpy.ops.object.mode_set(mode="OBJECT")
    # The grid faces' own UVs (metres), well away from the smart-projected ones (0..1): islands()
    # joins faces by shared vertex and UV only, and layout() places every island on its own.
    me = ob.data
    uv = me.uv_layers["lightmap"]                     # fetched again after edit mode
    for p in me.polygons:
        if gl[p.index] >= 0:
            for li in p.loop_indices:
                uv.data[li].uv = gdata[li] + Vector((1000.0, 1000.0))
    return max(uv_coverage([ob]), 1e-4)


def unwrap_one(ob):
    """Smart-project one object on its own (multi-object packing is unreliable here: some groups
    came out collapsed or overlapping). Returns the share of the unit square its islands cover."""
    if ob.name == "dome_coffers":
        return dome_unwrap(ob)
    if ob.name == "pendentives":
        pendentive_uvs(ob)
    me = ob.data
    if "lightmap_grid" in me.uv_layers:
        return grid_unwrap(ob)
    if "lightmap_sweep" in me.uv_layers:
        # A swept moulding: its own UVs along the run (finish.sweep), facets along the texel rows.
        data = [d.uv.copy() for d in me.uv_layers["lightmap_sweep"].data]
        me.uv_layers.remove(me.uv_layers["lightmap_sweep"])
        if "detail" not in me.uv_layers:            # created first: TEXCOORD_0 in the glTF
            me.uv_layers.new(name="detail")
        uv = me.uv_layers.get("lightmap") or me.uv_layers.new(name="lightmap")
        for d, c in zip(uv.data, data):
            d.uv = c
        lo = Vector((min(c.x for c in data), min(c.y for c in data)))
        hi = Vector((max(c.x for c in data), max(c.y for c in data)))
        ext = max(hi.x - lo.x, hi.y - lo.y, 1e-6)
        for d in uv.data:
            d.uv = (d.uv - lo) / ext
        return max(uv_coverage([ob]), 1e-4)
    split_long(ob, P.BAKE_ISLAND_MAX)
    for uvl in [u for u in me.uv_layers if u.name not in ("detail", "lightmap")]:
        me.uv_layers.remove(uvl)
    if "detail" not in me.uv_layers:            # created first: TEXCOORD_0 in the glTF
        me.uv_layers.new(name="detail")
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
            # Round 7: turn the island so its edges run along the texel grid (smart project and
            # its packer leave islands at any angle: a straight shadow edge then becomes a
            # one-texel staircase). Angle: length-weighted mean of the edges' angles mod 90.
            faces = {loop_face[i].index: loop_face[i] for i in loops}.values()
            sx = sy = 0.0
            for p in faces:
                li = list(p.loop_indices)
                for a, b in zip(li, li[1:] + li[:1]):
                    d = uv[b].uv - uv[a].uv
                    w3 = (mw @ me.vertices[me.loops[b].vertex_index].co - mw @ me.vertices[me.loops[a].vertex_index].co).length
                    if d.length < 1e-9:
                        continue
                    t = 4 * math.atan2(d.y, d.x)
                    sx += w3 * math.cos(t)
                    sy += w3 * math.sin(t)
            ang = math.atan2(sy, sx) / 4
            gattr = me.attributes.get("lm_island")
            # Left as laid: islands on the texel grid already, and strips closed on themselves (ring
            # mouldings, the tondi's frames: "lm_grid_aligned"). Turned by a fraction of a degree, a
            # strip's rows drift across the texel rows along its length, and at its closing cut the two
            # ends sample a crease's two faces differently (a step of up to 40 levels on the drum's top
            # cornice, round 12).
            on_grid = (ob.name in GRID_ALIGNED or ob.get("lm_grid_aligned")
                       or (gattr is not None and all(gattr.data[p.index].value >= 0 for p in faces)))
            if abs(ang) > 1e-4 and not on_grid:
                ca, sa = math.cos(-ang), math.sin(-ang)
                cx = sum(uv[i].uv.x for i in loops) / len(loops)
                cy = sum(uv[i].uv.y for i in loops) / len(loops)
                for i in loops:
                    x, y = uv[i].uv.x - cx, uv[i].uv.y - cy
                    uv[i].uv = (cx + ca * x - sa * y, cy + sa * x + ca * y)
            # Scale each island on its own: its 3D area and UV area give px per UV unit.
            a3 = sum(p.area for p in faces) * (mw.to_scale().x ** 2)
            a2i = 0.0
            for p in faces:
                pts = [uv[i].uv for i in p.loop_indices]
                a2i += abs(sum(pts[j].x * pts[j - 1].y - pts[j - 1].x * pts[j].y for j in range(len(pts)))) / 2
            f = CFG["density"] * density_scale(ob) * math.sqrt(a3 / a2i) if a2i > 1e-12 else 1.0
            dattr = me.attributes.get("lm_density")     # per-face factor (finish.coffer_sheet lm_islands)
            if dattr is not None:
                f *= max(dattr.data[p.index].value for p in faces)
            xs = [uv[i].uv.x for i in loops]
            ys = [uv[i].uv.y for i in loops]
            lo = Vector((min(xs), min(ys)))
            w, h = (max(xs) - lo.x) * f, (max(ys) - lo.y) * f
            # Thin islands (a riser, a fillet) get at least MIN_PX texels across: below that,
            # filtering mixes their light with the neighbours'.
            MIN_PX = 6.0
            fx = MIN_PX / w if 0 < w < MIN_PX else 1.0
            fy = MIN_PX / h if 0 < h < MIN_PX else 1.0
            if fx != 1.0 or fy != 1.0:
                for i in loops:
                    d = uv[i].uv - lo
                    uv[i].uv = lo + Vector((d.x * fx, d.y * fy))
                w, h = w * fx, h * fy
            rot = h > w * 1.5                       # lay long islands flat (shelves are rows)
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
    page = max(256, int(math.ceil(math.sqrt(total / 0.8) / 64)) * 64,
               int(math.ceil(max(it[1] for it in items) / 64)) * 64)     # the longest island fits a row
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
    # Each island's index, per corner, for the stitch (tools/lightmap_post.py): integers < 1024
    # in two channels, exact through the float bake. The third channel is the object's light
    # class: surfaces lit by different light-linking conventions (the vaults take no sun; bay 1's
    # vault band takes the bounce card) meet at a deliberate step the stitch must keep.
    def light_class(ob):
        cls = 0
        for bit, cname in ((1, "sun_not_received"), (2, "front_bounce_receivers"), (4, "oculus_spill_receivers")):
            c = bpy.data.collections.get(cname)
            if c is not None and ob.name in c.objects:
                cls += bit
        return float(cls)
    for idx, it in enumerate(items):
        ob, loops = it[2], it[3]
        me = ob.data
        attr = me.color_attributes.get("bake_island") or me.color_attributes.new("bake_island", "FLOAT_COLOR", "CORNER")
        cls = light_class(ob)
        for i in loops:
            attr.data[i].color = (float(idx % 1024), float(idx // 1024), cls, 1.0)
    return page, page_h


def uv_coverage(objs):
    tot = 0.0
    for ob in objs:
        uv = ob.data.uv_layers["lightmap"].data
        for p in ob.data.polygons:
            pts = [uv[i].uv for i in p.loop_indices]
            tot += abs(sum(pts[i].x * pts[i - 1].y - pts[i - 1].x * pts[i].y for i in range(len(pts)))) / 2
    return tot


# ---------------------------------------------------------------- materials split for the web
# The web draws detail(uv0) x tint x lightmap(uv1). Every face gets a detail key (its material's
# shared texture; risers split off by normal), a detail UV in world metres / tile, and a per-face
# factor for what the lightmap must carry beyond the light (Raphael's right-side shade, the buff
# tint of side walls), since a light-only bake divides the material's colour out.
def detail_of(mat, normal):
    if mat is None:
        return "flat", (0.8, 0.8, 0.8)
    if mat.get("riser_detail") and abs(normal.z) < 0.5:
        return mat["riser_detail"], (1.0, 1.0, 1.0)
    return mat.get("detail", mat.name), tuple(mat.get("tint", (1.0, 1.0, 1.0)))


def underside_shade(x):
    """Raphael's right-side shade on downward faces, blended across the hall (round 8): 1 at the
    left wall, RIGHT_UNDERSIDE at the right one, smoothstep between. A hard step at x = 0.5 made
    the crown column of every vault and arch soffit read as a lighter stripe."""
    b = P.NAVE_HALF_W
    t = min(1.0, max(0.0, (x + b) / (2 * b)))
    return 1.0 - (1.0 - P.RIGHT_UNDERSIDE) * t * t * (3 - 2 * t)


def down_weight(nz):
    """How much of the underside shade a face takes, by how far it turns down: none at n.z -0.25,
    all at -0.75, smoothstep between, so on a curved underside the shade comes in over the curve.
    It was all-or-nothing at -0.5, a straight light step across every curved surface there; round
    12 ramped it over -0.45..-0.55 round the dome only, and Maria then saw the step on the end
    door's arch ("this shadow band looks out of place", 2026-11-23): now everywhere, and wider."""
    t = min(1.0, max(0.0, (-0.25 - nz) / 0.5))
    return t * t * (3 - 2 * t)



def side_weight(nx):
    """How much of the right wall's shade a face takes, by how far it turns to -X: none at n.x
    -0.25, all at -0.75, smoothstep between (as down_weight for the underside shade)."""
    t = min(1.0, max(0.0, (-0.25 - nx) / 0.5))
    return t * t * (3 - 2 * t)

def face_factor(c, n, ux=None, nz=None):
    """What the lightmap carries beyond the light, per face (nz: the corner's normal z smoothed
    over its neighbours, for the underside weight; the face's own by default):
    - Raphael's right side: downward faces x underside_shade(x) (down_weight); faces turned to -X, and every face
      inside a right-hand recess (Raphael paints the right bays' recesses in shade, though the
      convention sun is not blocked there), x RIGHT_WALL;
    - the side walls of the nave and the second arm (walls, pilasters, recesses, their mouldings,
      bay 1's vestibule excepted) x SIDE_TINT: the fresco's receding walls are buff."""
    f = Vector((1.0, 1.0, 1.0))
    if c.z > P.DRUM_Z1 + 0.005:          # the dome: lit all round by the drum's windows (round 6)
        return f
    w = down_weight(n.z if nz is None else nz)
    if w > 0:
        f *= 1.0 - (1.0 - underside_shade(c.x if ux is None else ux)) * w
    if c.x > 0.5 and c.y > P.FACADE_Y1 and c.z < P.SPRING_Z + 0.5:
        # faces turned to -X take the right wall's shade by how far they turn (side_weight), so a
        # curved face (an arch's soffit on the right) shades in over the curve; it was all-or-
        # nothing at n.x -0.5, a hard edge across the end door's soffit (Maria, 2026-11-23).
        w = 1.0 if c.x > P.NAVE_HALF_W + 0.05 else side_weight(n.x)
        if w > 0:
            f = Vector([a * (1.0 - (1.0 - b) * w) for a, b in zip(f, P.RIGHT_WALL)])
    if (abs(c.x) > P.NAVE_HALF_W - 0.9 and P.BAY1_SIDE_RECESS[0] - 0.05 < c.y < P.ARM2_Y1 and c.z < P.SPRING_Z + 0.5):
        f = Vector([a * b for a, b in zip(f, P.SIDE_TINT)])
    return f


CYL = {"_vault_coffers": ("y", P.NAVE_HALF_W), "_vault_band": ("y", P.NAVE_HALF_W),
       "_soffit": ("y", P.CROSS_HALF), "drum": ("z", P.CROSS_HALF)}


def arch_uvs(ob, uv):
    """The opening arch's band tile (make_detail.py, arch_band): u counts meander periods from the
    crown down either side (mirrored at the crown), v runs across the bands from the inner edge
    (0) to the outer (1). Both from the scan px Raphael's eye sees each vertex at."""
    me = ob.data
    mw = ob.matrix_world
    cu, cv = P.ARCH_C
    r0, r1 = P.ARCH_R["inner"], P.ARCH_R["outer"]
    rm = sum(P.ARCH_R["pattern"]) / 2
    half = math.pi / 2 + math.asin((cv - P.ARCH_SPRING_V) / rm)
    period = half / P.ARCH_MEANDER["periods_half"]
    for li, loop in enumerate(me.loops):
        w = mw @ me.vertices[loop.vertex_index].co
        u = P.CX + P.F_PX * w.x / w.y
        v = P.CY - P.F_PX * (w.z - P.EYE_Z) / w.y
        r = math.hypot(u - cu, v - cv)
        t = math.atan2(cv - v, u - cu)
        uv.data[li].uv = (abs(t - math.pi / 2) / period, (r - r0) / (r1 - r0))


def dome_uvs(ob, uv, tiles):
    """The dome's detail UVs in metres on the sphere: along the parallels R cos(phi) theta, up the
    meridians R phi (theta taken round each face's own centre, so no face spans the seam). The
    planar mapping stretched the tile on the steep lower rings (dome-tap report)."""
    me = ob.data
    mw = ob.matrix_world
    rot = mw.to_3x3()
    c0 = Vector((0, (P.CROSS_Y0 + P.CROSS_Y1) / 2, P.DRUM_Z1))
    R = P.CROSS_HALF
    for p in me.polygons:
        mat = me.materials[p.material_index] if p.material_index < len(me.materials) else None
        key, _ = detail_of(mat, (rot @ p.normal).normalized())
        tw, th = tiles.get(key, (1.0, 1.0))
        cc = mw @ p.center - c0
        tc = math.atan2(cc.y, cc.x)
        for li in p.loop_indices:
            w = mw @ me.vertices[me.loops[li].vertex_index].co - c0
            t = tc + (math.atan2(w.y, w.x) - tc + math.pi) % (2 * math.pi) - math.pi
            ph = math.atan2(w.z, math.hypot(w.x, w.y))
            uv.data[li].uv = (R * math.cos(ph) * t / tw, R * ph / th)


def detail_uvs(ob, tiles):
    """Detail UVs in metres / tile: planar by the face's dominant axis, cylindrical (arc length)
    on the vaults, soffits and the drum; floors start their pattern at the material's origin."""
    me = ob.data
    uv = me.uv_layers.get("detail") or me.uv_layers.new(name="detail")
    mw = ob.matrix_world
    rot = mw.to_3x3()
    cyl = next((v for k, v in CYL.items() if k in ob.name), None)
    if ob.name.startswith("opening_archivolt"):
        arch_uvs(ob, uv)     # the bands' fronts; their steps' sides are plain stone, mapped below
    if ob.name.startswith("dome"):
        dome_uvs(ob, uv, tiles)
        return
    ycen = (P.CROSS_Y0 + P.CROSS_Y1) / 2
    for p in me.polygons:
        mat = me.materials[p.material_index] if p.material_index < len(me.materials) else None
        n = (rot @ p.normal).normalized()
        key, _ = detail_of(mat, n)
        if key == "arch_band":
            continue                                   # arch_uvs
        tw, th = tiles.get(key, (1.0, 1.0))
        ox, oy = (mat.get("origin", (0.0, 0.0)) if mat else (0.0, 0.0)) if key.startswith("floor") else (0.0, 0.0)
        uo = mat.get("uv_origin") if mat else None     # a tile mapped once over a panel (deco round)
        ux0, uz0 = (uo[0], uo[1]) if uo else (0.0, 0.0)
        # Reliefs painted by a wall's tile (the vault ornament): faces not turned to the front
        # take one point of the tile (its plain strip) instead of a planar smear of it.
        side_uv = mat.get("side_uv") if mat else None
        if side_uv and not (abs(n.y) >= abs(n.x) and abs(n.y) >= abs(n.z)):
            for li in p.loop_indices:
                uv.data[li].uv = tuple(side_uv)
            continue
        c = mw @ p.center
        for li in p.loop_indices:
            w = mw @ me.vertices[me.loops[li].vertex_index].co
            if cyl and cyl[0] == "y" and abs(Vector((n.x, 0, n.z)).normalized().dot(Vector((-c.x, 0, P.SPRING_Z - c.z)).normalized())) > 0.6:
                s = cyl[1] * math.atan2(w.x, w.z - P.SPRING_Z)
                u, v = s / tw, w.y / th
            elif cyl and cyl[0] == "z" and abs(n.z) < 0.5:
                s = cyl[1] * math.atan2(w.x, w.y - ycen)
                u, v = s / tw, w.z / th
            elif abs(n.z) >= max(abs(n.x), abs(n.y)):
                u, v = (w.x - ox) / tw, (w.y - oy) / th
            elif abs(n.x) >= abs(n.y):
                u, v = (w.y - ux0) / tw, (w.z - uz0) / th
            else:
                u, v = (w.x - ux0) / tw, (w.z - uz0) / th
            uv.data[li].uv = (u, v)


def factor_attribute(ob):
    me = ob.data
    attr = me.color_attributes.get("bake_factor") or me.color_attributes.new("bake_factor", "FLOAT_COLOR", "CORNER")
    mw = ob.matrix_world
    rot = mw.to_3x3()
    fn = [(rot @ p.normal).normalized() for p in me.polygons]
    near = [i for i, n in enumerate(fn) if -0.75 < n.z < -0.25]     # faces near down_weight's ramp
    vf = {}
    for i in near:
        for v in me.polygons[i].vertices:
            vf.setdefault(v, [])
    for p in me.polygons:
        for v in p.vertices:
            if v in vf:
                vf[v].append(p.index)
    cos30 = math.cos(math.radians(30))
    for p in me.polygons:
        c, n = mw @ p.center, fn[p.index]
        smooth = -0.75 < n.z < -0.25
        for li in p.loop_indices:          # per corner: the underside shade varies across a face
            nz = None
            if smooth:                     # the corner's normal, smoothed over faces within 30 deg
                acc = Vector()
                for q in vf[me.loops[li].vertex_index]:
                    if fn[q].dot(n) > cos30:
                        acc += fn[q] * me.polygons[q].area
                nz = acc.normalized().z if acc.length > 1e-12 else n.z
            f = face_factor(c, n, ux=(mw @ me.vertices[me.loops[li].vertex_index].co).x, nz=nz)
            if ob.name.startswith(("vault_", "opening_archivolt_intrados")):   # the front wall's ornament, the soffit: the bake's light only
                f = Vector((1.0, 1.0, 1.0))
            attr.data[li].color = (f.x, f.y, f.z, 1.0)


factor_mat = bpy.data.materials.new("bake_factor")
factor_mat.use_nodes = True
_nt = factor_mat.node_tree
_nt.nodes.clear()
_attr, _emit, _out = _nt.nodes.new("ShaderNodeAttribute"), _nt.nodes.new("ShaderNodeEmission"), _nt.nodes.new("ShaderNodeOutputMaterial")
_attr.attribute_name = "bake_factor"
_nt.links.new(_attr.outputs["Color"], _emit.inputs["Color"])
_nt.links.new(_emit.outputs["Emission"], _out.inputs["Surface"])
_factor_node = _nt.nodes.new("ShaderNodeTexImage")


def emit_mat(name, build):
    """An emission material for a 1-sample EMIT bake of geometry data; `build(nt)` returns the
    socket to emit. Returns (material, its bake target node)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    emit, out = nt.nodes.new("ShaderNodeEmission"), nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(build(nt), emit.inputs["Color"])
    nt.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    target = nt.nodes.new("ShaderNodeTexImage")
    nt.nodes.active = target
    return m, target


def _position(nt):                                  # world position + 100 m (kept positive)
    g = nt.nodes.new("ShaderNodeNewGeometry")
    v = nt.nodes.new("ShaderNodeVectorMath")
    v.operation = "ADD"
    v.inputs[1].default_value = (100.0, 100.0, 100.0)
    nt.links.new(g.outputs["Position"], v.inputs[0])
    return v.outputs["Vector"]


def _normal(nt):                                    # true normal, as n / 2 + 0.5
    g = nt.nodes.new("ShaderNodeNewGeometry")
    v = nt.nodes.new("ShaderNodeVectorMath")
    v.operation = "MULTIPLY_ADD"
    v.inputs[1].default_value = (0.5, 0.5, 0.5)
    v.inputs[2].default_value = (0.5, 0.5, 0.5)
    nt.links.new(g.outputs["True Normal"], v.inputs[0])
    return v.outputs["Vector"]


def _island(nt):
    a = nt.nodes.new("ShaderNodeAttribute")
    a.attribute_name = "bake_island"
    return a.outputs["Color"]


GEOM_MATS = {k: emit_mat(f"bake_{k}", f) for k, f in (("position", _position), ("normal", _normal), ("island", _island))}


def bake_emit(objs, mat, node, img, margin):
    """Bake an emission material over objs (their own materials swapped out, then restored)."""
    saved = {ob: list(ob.data.materials) for ob in objs}
    for ob in objs:
        for i in range(len(ob.data.materials)):
            ob.data.materials[i] = mat
        if not ob.data.materials:
            ob.data.materials.append(mat)
    node.image = img
    mat.node_tree.nodes.active = node
    scene.cycles.samples = 1
    keep = bake.margin
    bake.margin = margin
    bpy.ops.object.select_all(action="DESELECT")
    for ob in objs:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.bake(type="EMIT")
    bake.margin = keep
    for ob, ms in saved.items():
        for i, m in enumerate(ms):
            ob.data.materials[i] = m
        if not ms:
            ob.data.materials.clear()


def pixels(img):
    a = np.empty(img.size[0] * img.size[1] * 4, np.float32)
    img.pixels.foreach_get(a)
    return a.reshape(img.size[1], img.size[0], 4)

# Tile sizes per detail key, from the materials (stored by finish.py).
tiles = {}
for m in bpy.data.materials:
    if m.get("tile"):
        tiles.setdefault(m.get("detail", m.name), tuple(m["tile"]))
tiles.setdefault("step_riser", tiles.get("step", (1.6, 1.6)))


def bake_into(objs, img, kind):
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
    bpy.ops.object.bake(type=kind)


# ---------------------------------------------------------------- bake each group
report = {"quality": QUALITY, "config": CFG, "light_scale": P.LIGHT_SCALE, "groups": {}}
ONLY = os.environ.get("BAKE_ONLY")
for name, objs in groups.items():
    if not objs or (ONLY and name != ONLY):
        continue
    size, size_h = layout(objs)
    for ob in objs:
        detail_uvs(ob, tiles)
        factor_attribute(ob)
        ob.data.uv_layers["lightmap"].active = True
    log(f"group {name}: {len(objs)} objects, {sum(area(o) for o in objs):.0f} m2, atlas {size} x {size_h}, "
        f"used {uv_coverage(objs):.0%}")
    if os.environ.get("BAKE_DRY"):
        continue
    t0 = time.time()
    # 1. Light only: diffuse direct + indirect without the surface colour (every light-linking
    #    set-up of the scene active). Glossy is left out: the web draws no highlights.
    bake.use_pass_direct, bake.use_pass_indirect, bake.use_pass_color = True, True, False
    light = bpy.data.images.new(f"light_{name}", size, size_h, alpha=True, float_buffer=True)
    scene.cycles.samples = int(CFG["samples"] * getattr(P, "BAKE_GROUP_SAMPLES", {}).get(name, 1.0))
    bake_into(objs, light, "DIFFUSE")
    # 2. The per-face factors, as an emission bake of the factor attribute (1 sample is enough).
    fimg = bpy.data.images.new(f"factor_{name}", size, size_h, alpha=True, float_buffer=True)
    bake_emit(objs, factor_mat, _factor_node, fimg, CFG["margin"])
    # 3. Where each texel is: world position, true normal and island, without margin (alpha 0
    #    marks texels no face covers). tools/lightmap_post.py denoises the light, stitches it
    #    across island cuts in world space, multiplies the factor in and writes the atlas.
    geo = {}
    for k, (mat, node) in GEOM_MATS.items():
        img = bpy.data.images.new(f"{k}_{name}", size, size_h, alpha=True, float_buffer=True)
        bake_emit(objs, mat, node, img, 0)
        geo[k] = pixels(img)
        bpy.data.images.remove(img)
    L, Fc = pixels(light), pixels(fimg)
    clipped = float(((L[..., :3] * Fc[..., :3]).max(-1)[L[..., 3] > 0] > P.LIGHT_SCALE).mean())
    isl = geo["island"]
    np.savez_compressed(OUT / f"bake_{name}.npz", light=L.astype(np.float16), factor=Fc[..., :3].astype(np.float16),
                        position=geo["position"][..., :3] - 100.0, normal=(geo["normal"][..., :3] * 2 - 1).astype(np.float16),
                        island=np.round(isl[..., 0] + 1024 * isl[..., 1]).astype(np.int32),
                        light_class=np.round(isl[..., 2]).astype(np.int8),
                        covered=geo["position"][..., 3] > 0.5)
    path = OUT / f"bake_{name}.npz"
    report["groups"][name] = {"objects": len(objs), "area_m2": round(sum(area(o) for o in objs), 1),
                              "atlas": [size, size_h], "density_px_per_m": CFG["density"],
                              "clipped_fraction": round(clipped, 5), "bake_s": round(time.time() - t0, 1)}
    log(f"baked {name} in {time.time() - t0:.0f}s -> {path.name} (clipped {clipped:.2%})")
    bpy.data.images.remove(light)
    bpy.data.images.remove(fimg)

# ---------------------------------------------------------------- export (70 %, one mesh per group)
# Each group: one mesh, one material per detail key (+ tint), named "<group>|<key>|<tint>"; the
# material shows a placeholder image "detail_<key>" on UV "detail" (TEXCOORD_0); the lightmap UV
# is TEXCOORD_1. tools/pack_hall.mjs swaps in the detail textures, attaches the group's lightmap
# and sets the tint (materials.json).
for ob in list(bpy.data.objects):
    if ob.type == "MESH" and (is_occluder_only(ob) or ob.get("kind") == "painting"):
        bpy.data.objects.remove(ob)
placeholder = {}


def export_material(group, key, tint):
    nm = f"{group}|{key}|{','.join(f'{t:.4f}' for t in tint)}"
    m = bpy.data.materials.get(nm)
    if m:
        return m
    m = bpy.data.materials.new(nm)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    if key not in placeholder:
        im = bpy.data.images.new(f"detail_{key}", 4, 4, alpha=False)
        im.filepath_raw = str(OUT / f"detail_{key}.png")
        im.file_format = "PNG"
        im.save()
        placeholder[key] = im
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = placeholder[key]
    uvn = nt.nodes.new("ShaderNodeUVMap")
    uvn.uv_map = "detail"
    nt.links.new(uvn.outputs["UV"], tex.inputs["Vector"])
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    return m


materials_json = {}
exported = []
for name, objs in groups.items():
    if not objs:
        continue
    for ob in objs:
        me = ob.data
        rot = ob.matrix_world.to_3x3()
        slots = {}
        new_index = []
        for p in me.polygons:
            mat = me.materials[p.material_index] if p.material_index < len(me.materials) else None
            key, tint = detail_of(mat, (rot @ p.normal).normalized())
            em = export_material(name, key, tint)
            materials_json[em.name] = {"group": name, "detail": key, "tint": list(tint)}
            if em.name not in slots:
                slots[em.name] = len(slots)
            new_index.append(slots[em.name])
        me.materials.clear()
        for nm in slots:
            me.materials.append(bpy.data.materials[nm])
        for p, i in zip(me.polygons, new_index):
            p.material_index = i
        for a in ("bake_factor", "bake_island"):
            if a in me.color_attributes:
                me.color_attributes.remove(me.color_attributes[a])
        for a in ("lm_island", "lm_density"):
            if a in me.attributes:
                me.attributes.remove(me.attributes[a])
        for uvl in [u for u in me.uv_layers if u.name not in ("detail", "lightmap")]:
            me.uv_layers.remove(uvl)
    bpy.ops.object.select_all(action="DESELECT")
    for ob in objs:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = ob.data.name = f"hall_{name}"
    me = ob.data
    # UV order: detail first (TEXCOORD_0), lightmap second (TEXCOORD_1).
    if me.uv_layers[0].name != "detail":
        raise RuntimeError(f"{ob.name}: UV layers {[u.name for u in me.uv_layers]}")
    me.uv_layers["detail"].active_render = True
    exported.append(ob)
# The flat ground beyond the end door is not exported: the web draws it (Scene.tsx, GroundBeyond,
# from hall.json "groundBeyond"). Its 400 m stretched the GLB's one quantization grid (pack_hall.mjs,
# quantizationVolume "scene") to 4.3 mm a step, and the opening arch's bands, 3.3 m from the eye,
# showed every vertex's rounding as a wavy, toothed edge; over the hall alone a step is ~0.6 mm.
for name in P.BAKE_SKIP:
    ob = bpy.data.objects.get(name)
    if ob:
        bpy.data.objects.remove(ob)
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
(OUT / "materials.json").write_text(json.dumps(materials_json, indent=1))
# What make_detail.py needs: per detail key, the scan, ramp, colours (untinted), tile, mottle.
specs = {}
for m in bpy.data.materials:
    key = m.get("detail")
    if key and key not in specs:
        specs[key] = {k: (list(m[k]) if not isinstance(m[k], (str, int, float)) else m[k])
                      for k in ("detail_tex", "lum_range", "tile", "albedo_dark", "albedo_light", "mottle", "origin")
                      if k in m}
(OUT / "detail-specs.json").write_text(json.dumps(specs, indent=1))
report["seconds"] = round(time.time() - t_start, 1)
(OUT / "bake-report.json").write_text(json.dumps(report, indent=2))
log("exported", OUT / "hall.gltf")
