"""Build the grey model of the School of Athens hall and render it from Raphael's camera.

Run: blender -b --factory-startup -P blender/scripts/build.py -- <out_dir> [view ...]
Views: raphael (default), plus any defined in VIEWS below. The plan is drawn by tools/plan.py.
Writes <out_dir>/<view>.png and blender/athens-grey.blend.
"""
import math
import sys
from pathlib import Path

import bmesh
import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import params as P  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = Path(argv[0]) if argv else HERE.parent.parent / "renders" / "grey"
VIEW_NAMES = argv[1:] or ["raphael"]
OUT.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
coll = scene.collection

GREY = {
    "floor": (0.62, 0.60, 0.57, 1), "step": (0.70, 0.68, 0.65, 1),
    "facade": (0.86, 0.84, 0.80, 1), "wall": (0.80, 0.78, 0.74, 1),
    "trim": (0.92, 0.90, 0.86, 1), "vault": (0.74, 0.72, 0.69, 1),
    "crossing": (0.84, 0.82, 0.78, 1), "dome": (0.88, 0.86, 0.82, 1),
    "painting": (0.55, 0.12, 0.10, 1),
}


# ---------------------------------------------------------------- mesh helpers
def to_object(name, bm, kind):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    ob.color = GREY[kind]
    ob["kind"] = kind
    coll.objects.link(ob)
    return ob


def box(name, x0, x1, y0, y1, z0, z1, kind="wall"):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((x0 + (v.co.x + 0.5) * (x1 - x0),
                       y0 + (v.co.y + 0.5) * (y1 - y0),
                       z0 + (v.co.z + 0.5) * (z1 - z0)))
    return to_object(name, bm, kind)


def prism(name, pts_xz, y0, y1, kind="wall"):
    """Extrude a closed outline drawn in the XZ plane from y0 to y1."""
    bm = bmesh.new()
    verts = [bm.verts.new((x, y0, z)) for x, z in pts_xz]
    face = bm.faces.new(verts)
    ext = bmesh.ops.extrude_face_region(bm, geom=[face])
    moved = [e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=moved, vec=(0, y1 - y0, 0))
    return to_object(name, bm, kind)


def arc(xc, zc, r, t0, t1, n):
    return [(xc + r * math.cos(t0 + (t1 - t0) * i / n), zc + r * math.sin(t0 + (t1 - t0) * i / n))
            for i in range(n + 1)]


def arched_wall(name, x0, x1, y0, y1, z0, z1, half, spring, xc=0.0, kind="wall", n=64):
    """Wall with a round-arched opening rising from its base (z0)."""
    pts = [(x0, z0), (xc - half, z0)]
    pts += arc(xc, spring, half, math.pi, 0.0, n)
    pts += [(xc + half, z0), (x1, z0), (x1, z1), (x0, z1)]
    return prism(name, pts, y0, y1, kind)


def round_top(x0, x1, z0, z1, n=32):
    """Closed outline: rectangle with a semicircular top (for niches and cutters)."""
    half = (x1 - x0) / 2
    spring = z1 - half
    return [(x0, z0), (x1, z0)] + arc(x0 + half, spring, half, 0.0, math.pi, n)[:-1] + [(x0, spring)]


def half_ring(name, half, thick, spring, y0, y1, kind="vault", n=72):
    """Barrel vault: half annulus in XZ extruded along Y."""
    outer = arc(0, spring, half + thick, 0.0, math.pi, n)
    inner = arc(0, spring, half, math.pi, 0.0, n)
    return prism(name, outer + inner, y0, y1, kind)


def revolve(name, profile_rz, centre, kind, segments=96):
    """Revolve a closed (r, z) outline around the vertical axis through centre (x, y)."""
    bm = bmesh.new()
    cx, cy = centre
    rings = []
    for k in range(segments):
        a = 2 * math.pi * k / segments
        rings.append([bm.verts.new((cx + r * math.cos(a), cy + r * math.sin(a), z)) for r, z in profile_rz])
    n = len(profile_rz)
    for k in range(segments):
        a, b = rings[k], rings[(k + 1) % segments]
        for j in range(n):
            bm.faces.new((a[j], a[(j + 1) % n], b[(j + 1) % n], b[j]))
    return to_object(name, bm, kind)


def boolean(target, cutter, op="DIFFERENCE"):
    mod = target.modifiers.new("bool", "BOOLEAN")
    mod.operation = op
    mod.solver = "EXACT"
    mod.object = cutter
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(target.evaluated_get(dg))
    target.modifiers.clear()
    old = target.data
    target.data = me
    bpy.data.meshes.remove(old)
    bpy.data.objects.remove(cutter)


def mirror_x(pts):
    return [(-x, z) for x, z in pts][::-1]


# ---------------------------------------------------------------- the hall
PZ = P.PLATFORM_Z
NW = P.NAVE_HALF_W
T = P.WALL_T

# Floors, central steps, side podiums and corner pedestals.
SW = P.SIDE_HALF_W
box("floor_lower", -SW, SW, -2.0, P.STEPS[0][0], -0.3, 0.0, "floor")
box("floor_lower_sides_l", -SW, -P.STEP_HALF_W, P.STEPS[0][0], P.PODIUM_Y0, -0.3, 0.0, "floor")
box("floor_lower_sides_r", P.STEP_HALF_W, SW, P.STEPS[0][0], P.PODIUM_Y0, -0.3, 0.0, "floor")
for i, (y, z) in enumerate(P.STEPS[:-1]):
    box(f"step_{i + 1}", -P.STEP_HALF_W, P.STEP_HALF_W, y, P.STEPS[i + 1][0], -0.3, z, "step")
box("platform", -SW, SW, P.STEPS[-1][0], P.ARM2_Y1 + P.END_T, -0.3, PZ, "floor")
for side in (-1, 1):
    x0, x1 = sorted((side * P.STEP_HALF_W, side * SW))
    box(f"podium_{side}", x0, x1, P.PODIUM_Y0, P.STEPS[-1][0], -0.3, PZ, "step")
    a, b, y0, y1, z0, z1 = P.PEDESTAL
    px0, px1 = sorted((side * a, side * b))
    box(f"pedestal_{side}", px0, px1, y0, y1, z0, z1, "trim")
box("ground_beyond", -200, 200, P.ARM2_Y1 + P.END_T, 400, -0.3, PZ, "floor")

# Facade: front piers with the nave arch, niches and relief panels.
facade = arched_wall("facade", -P.FACADE_HALF_W, P.FACADE_HALF_W, P.FACADE_Y0, P.FACADE_Y1,
                     PZ, P.FACADE_TOP, NW, P.SPRING_Z, kind="facade")
for side in (-1, 1):
    x0, x1 = P.NICHE_X
    niche = round_top(x0, x1, P.NICHE_Z[0], P.NICHE_Z[1])
    if side < 0:
        niche = mirror_x(niche)
    boolean(facade, prism("niche_cut", niche, P.FACADE_Y0 - 0.2, P.FACADE_Y0 + P.NICHE_DEPTH))
    rx0, rx1 = sorted((side * x0, side * x1))
    boolean(facade, box("relief_cut", rx0, rx1, P.FACADE_Y0 - 0.2, P.FACADE_Y0 + 0.15,
                        P.RELIEF_Z[0], P.RELIEF_Z[1]))
    sx0, sx1 = sorted((side * NW, side * P.FACADE_HALF_W))
    box(f"string_course_{side}", sx0, sx1, P.FACADE_Y0 - 0.35, P.FACADE_Y0,
        P.STRING_COURSE[0], P.STRING_COURSE[1], "trim")


def arm(tag, y0, y1, pilasters):
    """Side walls, cornices, pilasters and barrel vault between y0 and y1."""
    c0, c1, proj = P.CORNICE
    for side in (-1, 1):
        wx0, wx1 = sorted((side * NW, side * (NW + T)))
        box(f"{tag}_wall_{side}", wx0, wx1, y0, y1, PZ, P.SPRING_Z, "wall")
        cx0, cx1 = sorted((side * NW, side * (NW - proj)))
        box(f"{tag}_cornice_{side}", cx0, cx1, y0, y1, c0, c1, "trim")
        for yc in pilasters:
            px0, px1 = sorted((side * NW, side * (NW - P.PILASTER_D)))
            box(f"{tag}_pilaster_{side}_{yc}", px0, px1, yc - P.PILASTER_W / 2, yc + P.PILASTER_W / 2,
                PZ, c0, "trim")
    half_ring(f"{tag}_vault", NW, 0.6, P.SPRING_Z, y0, y1)


# Starts behind the facade: its 3 m arch has its own soffit (overlapping surfaces render black).
arm("nave", P.FACADE_Y1, P.NAVE_Y1, P.PILASTERS_Y)

# Crossing: transverse arches, side walls, pendentives, drum, dome.
CH = P.CROSS_HALF
ycen = (P.CROSS_Y0 + P.CROSS_Y1) / 2
top = P.DRUM_Z0 + 1.5
arched_wall("arch_front", -(NW + T), NW + T, P.CROSS_Y0 - P.TRANSVERSE_T, P.CROSS_Y0, PZ, top,
            CH, P.SPRING_Z, kind="crossing")
arched_wall("arch_back", -(NW + T), NW + T, P.CROSS_Y1, P.CROSS_Y1 + P.TRANSVERSE_T, PZ, top,
            CH, P.SPRING_Z, kind="crossing")
for side in (-1, 1):
    x0, x1 = sorted((side * CH, side * (NW + T)))
    box(f"crossing_side_{side}", x0, x1, P.CROSS_Y0, P.CROSS_Y1, PZ, top, "crossing")
pend = box("pendentives", -CH, CH, P.CROSS_Y0, P.CROSS_Y1, P.SPRING_Z, P.DRUM_Z0, "crossing")
sph = bmesh.new()
bmesh.ops.create_uvsphere(sph, u_segments=128, v_segments=64, radius=CH * math.sqrt(2))
bmesh.ops.translate(sph, verts=sph.verts[:], vec=(0, ycen, P.SPRING_Z))
boolean(pend, to_object("sphere_cut", sph, "crossing"))

R_IN, R_OUT = CH, CH + 0.6
drum = revolve("drum", [(R_IN, P.DRUM_Z0), (R_OUT, P.DRUM_Z0), (R_OUT, P.DRUM_Z1), (R_IN, P.DRUM_Z1)],
               (0, ycen), "dome")
for k in range(P.DRUM_WINDOWS):
    a = math.pi / 2 + 2 * math.pi * k / P.DRUM_WINDOWS
    hw = P.DRUM_WINDOW_W / 2
    cut = box("win_cut", -hw, hw, R_IN - 0.4, R_OUT + 0.4, *P.DRUM_WIN_Z)
    cut.rotation_euler = (0, 0, a - math.pi / 2)
    cut.location = (0, ycen, 0)
    bpy.context.view_layer.update()
    cut.data.transform(cut.matrix_world)
    cut.matrix_world.identity()
    boolean(drum, cut)
revolve("drum_cornice_low", [(R_IN - 0.35, P.DRUM_Z0), (R_IN, P.DRUM_Z0), (R_IN, P.DRUM_WIN_Z[0] - 0.4),
                             (R_IN - 0.35, P.DRUM_WIN_Z[0] - 0.4)], (0, ycen), "trim")
revolve("drum_cornice_high", [(R_IN - 0.3, P.DRUM_Z1 - 0.2), (R_IN, P.DRUM_Z1 - 0.2), (R_IN, P.DRUM_Z1),
                              (R_IN - 0.3, P.DRUM_Z1)], (0, ycen), "trim")
phi = math.acos(P.OCULUS_R / R_IN)
inner = [(R_IN * math.cos(t), P.DRUM_Z1 + R_IN * math.sin(t)) for t in [phi * i / 24 for i in range(25)]]
outer = [(R_OUT * math.cos(t), P.DRUM_Z1 + R_OUT * math.sin(t)) for t in [phi * i / 24 for i in range(25)]][::-1]
revolve("dome", inner + outer, (0, ycen), "dome")

# Second arm and end wall with the door.
arm("arm2", P.CROSS_Y1 + P.TRANSVERSE_T, P.ARM2_Y1, P.ARM2_PILASTERS_Y)
arched_wall("end_wall", -(NW + T), NW + T, P.ARM2_Y1, P.ARM2_Y1 + P.END_T, PZ, P.END_ATTIC_TOP,
            P.DOOR_HALF, P.DOOR_SPRING, kind="facade")
box("end_entablature", -NW, NW, P.ARM2_Y1 - 0.4, P.ARM2_Y1, *P.END_ENTABLATURE, "trim")

# Painting places, numbered in walking order (left, then right).
PAINTINGS = []
for yc in P.PAINTINGS_Y:
    for side in (-1, 1):
        n = len(PAINTINGS) + 1
        x0, x1 = sorted((side * NW, side * (NW - 0.08)))
        z0 = PZ + P.PAINTING_BOTTOM
        box(f"painting_{n:02d}", x0, x1, yc - P.PAINTING_W / 2, yc + P.PAINTING_W / 2,
            z0, z0 + P.PAINTING_H, "painting")
        PAINTINGS.append((n, side * (NW - 0.04), yc, z0 + P.PAINTING_H / 2))

# ---------------------------------------------------------------- consistent outward normals
# Booleans can leave faces flipped; Cycles shades flipped faces black.
for ob in list(coll.objects):
    if ob.type == "MESH":
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        bm.to_mesh(ob.data)
        bm.free()

# ---------------------------------------------------------------- materials (Cycles uses object colour)
mat = bpy.data.materials.new("grey")
mat.use_nodes = True
nt = mat.node_tree
bsdf = nt.nodes.get("Principled BSDF")
info = nt.nodes.new("ShaderNodeObjectInfo")
nt.links.new(info.outputs["Color"], bsdf.inputs["Base Color"])
bsdf.inputs["Roughness"].default_value = 0.75
for ob in list(coll.objects):
    if ob.type == "MESH":
        ob.data.materials.append(mat)

# ---------------------------------------------------------------- light and world
sun_data = bpy.data.lights.new("sun", "SUN")
sun_data.energy = 3.5
sun_data.angle = math.radians(1.0)
sun = bpy.data.objects.new("sun", sun_data)
sun.rotation_euler = Vector((0.45, 0.55, -0.7)).normalized().to_track_quat("-Z", "Y").to_euler()
coll.objects.link(sun)

world = bpy.data.worlds.new("sky")
world.color = (0.55, 0.68, 0.86)
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
bg.inputs["Color"].default_value = (0.55, 0.68, 0.86, 1)
bg.inputs["Strength"].default_value = 1.2
scene.world = world


# ---------------------------------------------------------------- cameras
def make_camera(name, loc, rot_deg=None, target=None, lens=24.0, ortho=None):
    data = bpy.data.cameras.new(name)
    data.sensor_fit, data.sensor_width = "AUTO", 36.0
    data.lens = lens
    data.clip_start, data.clip_end = 0.1, 2000
    if ortho:
        data.type, data.ortho_scale = "ORTHO", ortho
    ob = bpy.data.objects.new(name, data)
    ob.location = loc
    if target is not None:
        d = Vector(target) - Vector(loc)
        ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    else:
        ob.rotation_euler = [math.radians(a) for a in rot_deg]
    coll.objects.link(ob)
    return ob


raphael = make_camera("raphael", (0, 0, P.EYE_Z), rot_deg=(90, 0, 0))
raphael.data.sensor_fit = "HORIZONTAL"
raphael.data.lens = P.F_PX / P.IMG_W * 36.0
raphael.data.shift_x = (P.IMG_W / 2 - P.CX) / P.IMG_W
raphael.data.shift_y = (P.CY - P.IMG_H / 2) / P.IMG_W

EYE = PZ + 1.6
VIEWS = {
    # name: (camera, engine, (width, height))
    "raphael": (raphael, "WORKBENCH", (P.IMG_W // 2, P.IMG_H // 2)),
    "eye-entrance": (make_camera("eye-entrance", (0, 3.0, 1.6), target=(0, 30, 7.5), lens=18),
                     "CYCLES", (1600, 900)),
    "raphael-lit": (raphael, "CYCLES", (P.IMG_W // 2, P.IMG_H // 2)),
    "eye-nave": (make_camera("eye-nave", (0, 21, EYE), target=(0, 45, EYE + 4.0), lens=20),
                 "CYCLES", (1600, 900)),
    "eye-station": (make_camera("eye-station", (-1.2, 23.2, EYE), target=(-5.9, 25.1, EYE + 0.5), lens=24),
                    "CYCLES", (1600, 900)),
    "eye-dome": (make_camera("eye-dome", (0, 35.5, EYE), target=(0, 39.5, 20.0), lens=16),
                 "CYCLES", (1600, 900)),
    "eye-end": (make_camera("eye-end", (0, 45.5, EYE), target=(0, 60, EYE + 2.5), lens=20),
                "CYCLES", (1600, 900)),
    "phone-nave": (make_camera("phone-nave", (0, 19.5, EYE), target=(0, 45, EYE + 6.0), lens=18),
                   "CYCLES", (720, 1560)),
}

# Projection check against the formula used to place the elements.
bpy.context.view_layer.update()
for pt in [(-NW, P.CROSS_Y0, P.SPRING_Z), (P.DOOR_HALF, P.ARM2_Y1, P.DOOR_SPRING)]:
    scene.render.resolution_x, scene.render.resolution_y = P.IMG_W, P.IMG_H
    ndc = world_to_camera_view(scene, raphael, Vector(pt))
    u_b, v_b = ndc.x * P.IMG_W, (1 - ndc.y) * P.IMG_H
    u_f = P.CX + P.F_PX * pt[0] / pt[1]
    v_f = P.CY - P.F_PX * (pt[2] - P.EYE_Z) / pt[1]
    print(f"projection check {pt}: blender ({u_b:.1f}, {v_b:.1f}) formula ({u_f:.1f}, {v_f:.1f})")


bpy.ops.wm.save_as_mainfile(filepath=str(HERE.parent / "athens-grey.blend"))

# ---------------------------------------------------------------- render
prefs = bpy.context.preferences.addons["cycles"].preferences
try:
    prefs.compute_device_type = "METAL"
    prefs.get_devices()
    for d in prefs.devices:
        d.use = True
    scene.cycles.device = "GPU"
except Exception as exc:  # fall back to CPU
    print("GPU unavailable:", exc)
scene.cycles.samples = 64
scene.cycles.use_denoising = True
scene.view_settings.exposure = -0.4
scene.view_settings.look = "AgX - Medium High Contrast"

sh = scene.display.shading
sh.light = "STUDIO"
sh.color_type = "OBJECT"
sh.show_cavity = True
sh.cavity_type = "WORLD"
sh.background_type = "WORLD"
scene.display.light_direction = (-0.45, -0.55, 0.7)
scene.display.render_aa = "16"

for name in [v for v in VIEW_NAMES if v != "export"]:
    cam_ob, engine, (w, h) = VIEWS[name]
    scene.camera = cam_ob
    scene.render.engine = "BLENDER_WORKBENCH" if engine == "WORKBENCH" else "CYCLES"
    scene.render.resolution_x, scene.render.resolution_y = w, h
    scene.render.resolution_percentage = 100
    sh.show_shadows = name != "raphael"   # shadow edges would muddle the overlay
    scene.render.filepath = str(OUT / f"{name}.png")
    bpy.ops.render.render(write_still=True)
    print("rendered", scene.render.filepath)


# ---------------------------------------------------------------- web export (70 %)
if "export" in VIEW_NAMES:
    import json
    from mathutils import Matrix

    WEB = HERE.parent.parent / "web"
    (WEB / "public" / "models").mkdir(parents=True, exist_ok=True)
    (WEB / "src" / "data").mkdir(parents=True, exist_ok=True)
    k = P.SCALE
    mats = {}
    for kind, col in GREY.items():
        m = bpy.data.materials.new(f"m_{kind}")
        m.use_nodes = True
        b = m.node_tree.nodes.get("Principled BSDF")
        b.inputs["Base Color"].default_value = col
        b.inputs["Roughness"].default_value = 0.85
        mats[kind] = m
    for ob in list(coll.objects):
        if ob.type != "MESH":
            continue
        if ob.get("kind") == "painting":
            bpy.data.objects.remove(ob)
            continue
        ob.data.transform(Matrix.Scale(k, 4))
        ob.location = ob.location * k
        ob.data.materials.clear()
        ob.data.materials.append(mats[ob.get("kind", "wall")])
    for ob in list(coll.objects):
        if ob.type != "MESH":
            ob.select_set(False)
        else:
            ob.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(WEB / "public" / "models" / "hall.glb"), export_format="GLB",
                              use_selection=True, export_apply=True, export_cameras=False,
                              export_lights=False, export_extras=False, export_yup=True)

    def three(x, y, z):
        """Blender (x right, y forward, z up) at 100 % -> three.js (x right, y up, -z forward) at k."""
        return [round(x * k, 4), round(z * k, 4), round(-y * k, 4)]

    tan_up = P.CY / P.F_PX               # fresco: from the horizon to the top edge
    tan_down = (P.IMG_H - P.CY) / P.F_PX  # from the horizon to the bottom edge
    data = {
        "scale": k,
        "eye": three(0, 0, P.EYE_Z),
        "standingEye": 1.6,
        "frustum": {"tanUp": round(tan_up, 5), "tanDown": round(tan_down, 5),
                    "aspect": round(P.IMG_W / P.IMG_H, 5)},
        # Floor height along the walk (three.js z, metres): lower floor, steps, platform.
        "floor": [[three(0, 0, 0)[2], 0.0]] + [[three(0, y, 0)[2], round(zt * k, 4)] for y, zt in P.STEPS],
        "walkEnd": three(0, P.ARM2_Y1 - 1.5, 0)[2],
        "wallX": round(P.NAVE_HALF_W * k, 4),
        "paintingBottom": round(P.PAINTING_BOTTOM * k + P.PLATFORM_Z * k, 4),
        "places": [],
    }
    n = 0
    # Bay edges along each wall: between the facade / transverse arches and the pilasters.
    def edges(y0, y1, pilasters):
        e = [y0]
        for yc in pilasters:
            e += [yc - P.PILASTER_W / 2, yc + P.PILASTER_W / 2]
        return e + [y1]
    walls = [edges(P.FACADE_Y1, P.NAVE_Y1, P.PILASTERS_Y),
             edges(P.CROSS_Y1 + P.TRANSVERSE_T, P.ARM2_Y1, P.ARM2_PILASTERS_Y)]
    bays = [(e[i], e[i + 1]) for e in walls for i in range(0, len(e), 2)]
    for yc in P.PAINTINGS_Y:
        b0, b1 = next(b for b in bays if b[0] <= yc <= b[1])
        for side in (-1, 1):
            n += 1
            data["places"].append({"n": n, "side": side, "z": three(0, yc, 0)[2],
                                   "bay": [three(0, b0, 0)[2], three(0, b1, 0)[2]],
                                   "bayWidth": round((b1 - b0) * k, 3)})
    # The crossing's closed side walls under the dome, and the far doorway.
    data["dome"] = {"wallX": round(P.CROSS_HALF * k, 4), "z": three(0, (P.CROSS_Y0 + P.CROSS_Y1) / 2, 0)[2],
                    "length": round((P.CROSS_Y1 - P.CROSS_Y0) * k, 3)}
    data["door"] = {"z": three(0, P.ARM2_Y1, 0)[2], "width": round(2 * P.DOOR_HALF * k, 3),
                    "springZ": round((P.DOOR_SPRING) * k, 3)}
    (WEB / "src" / "data" / "hall.json").write_text(json.dumps(data, indent=2))
    print("exported", WEB / "public" / "models" / "hall.glb")
