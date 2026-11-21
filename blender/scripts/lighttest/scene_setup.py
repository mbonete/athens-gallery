"""Shared set-up for the decoration tests (branch deco-ideas): opens the finished hall
(blender/athens-hall.blend, as build.py saved it), gives the opening arch its band tile, hangs
the paintings where the web hangs them, and sets Cycles as build.py renders.

Renders only: nothing here is part of the web bake.
"""
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent
ROOT = SCRIPTS.parent.parent
sys.path.insert(0, str(SCRIPTS))
import params as P  # noqa: E402

PAINTINGS_DIR = Path("/Users/mbonete/code/athens-gallery-hall/web/public/paintings")   # read only
TEX = Path("/Users/mbonete/code/athens-gallery-deco/renders/deco-ideas/textures")   # read only
BUILD = ROOT / "blender" / "build"
EYE = P.PLATFORM_Z + 1.6


def lin(rgb):
    return tuple(((c / 255 + 0.055) / 1.055) ** 2.4 if c / 255 > 0.04045 else c / 255 / 12.92 for c in rgb)


def sock(node, ident, out=False):
    return next(s for s in (node.outputs if out else node.inputs) if s.identifier == ident)


# ---------------------------------------------------------------- materials
def flat(name, rgb_lin, rough=0.8, metallic=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*rgb_lin, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metallic
    return m


def gold():
    """Gold leaf as the opening arch has it: ARCH_COLOURS gold, a little sheen (the web adds a
    Blinn-Phong lobe on the arch's gold; here a rough metal)."""
    return flat("deco_gold", lin(P.ARCH_COLOURS["gold"]), rough=0.45, metallic=0.6)


def image_material(name, path, uv="UVMap", rough=0.75, alpha_gold=False):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    N, L = m.node_tree.nodes, m.node_tree.links
    b = N.get("Principled BSDF")
    t = N.new("ShaderNodeTexImage")
    t.image = bpy.data.images.load(str(path), check_existing=True)
    t.image.alpha_mode = "CHANNEL_PACKED"      # alpha is a gold mask, not coverage
    t.extension = "REPEAT"
    uvn = N.new("ShaderNodeUVMap")
    uvn.uv_map = uv
    L.new(uvn.outputs["UV"], t.inputs["Vector"])
    L.new(t.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    if alpha_gold:   # alpha marks gold leaf: a little metal there
        mr = N.new("ShaderNodeMapRange")
        mr.inputs["To Max"].default_value = 0.6
        L.new(t.outputs["Alpha"], mr.inputs["Value"])
        L.new(mr.outputs["Result"], b.inputs["Metallic"])
        r2 = N.new("ShaderNodeMapRange")
        r2.inputs["To Min"].default_value, r2.inputs["To Max"].default_value = rough, 0.45
        L.new(t.outputs["Alpha"], r2.inputs["Value"])
        L.new(r2.outputs["Result"], b.inputs["Roughness"])
    return m


# ---------------------------------------------------------------- the opening arch's band
def arch_band():
    """build.py's blend has the arch band as one flat colour (the web draws its tile). Give it the
    tile, with the UVs bake.arch_uvs computes (same formula), so the start view shows the gold
    meander the visitor sees. The tile is make_detail.arch_band rescaled to albedo (textures.py)."""
    path = TEX / "existing_arch_band_albedo.png"
    m = image_material("arch_band_tile", path, uv="arch", alpha_gold=True)
    cu, cv = P.ARCH_C
    r0, r1 = P.ARCH_R["inner"], P.ARCH_R["outer"]
    rm = sum(P.ARCH_R["pattern"]) / 2
    half = math.pi / 2 + math.asin((cv - P.ARCH_SPRING_V) / rm)
    period = half / P.ARCH_MEANDER["periods_half"]
    for name in ("opening_archivolt", "opening_archivolt_bands"):
        ob = bpy.data.objects[name]
        me, mw = ob.data, ob.matrix_world
        uv = me.uv_layers.get("arch") or me.uv_layers.new(name="arch")
        for li, loop in enumerate(me.loops):
            w = mw @ me.vertices[loop.vertex_index].co
            u = P.CX + P.F_PX * w.x / w.y
            v = P.CY - P.F_PX * (w.z - P.EYE_Z) / w.y
            r = math.hypot(u - cu, v - cv)
            t = math.atan2(cv - v, u - cu)
            uv.data[li].uv = (abs(t - math.pi / 2) / period, (r - r0) / (r1 - r0))
        me.materials.clear()
        me.materials.append(m)


# ---------------------------------------------------------------- paintings as the web hangs them
WEB = {   # slug: (place, widthM, imageW, imageH) from web/src/paintings.ts
    "mucha-summer": (1, 0.54, 6528, 12494),
    "klimt-water-serpents-ii": (2, 1.45, 5796, 3204),
    "waterhouse-hylas": (3, 1.633, 8261, 4961),
    "vangogh-almond-blossom": (4, 0.924, 7149, 5649),
    "hokusai-great-wave": (5, 0.379, 3859, 2594),
    "hiroshige-asakusa-torinomachi": (6, 0.221, 2627, 3905),
    "kandinsky-composition-8": ("dome-right", 2.01, 3825, 2655),
    "titian-rape-of-europa": ("dome-left", 2.05, 3544, 2946),
    "bosch-garden-of-earthly-delights": ("end", 3.255, 12000, 6774),
}


def _plane(name, path, w, h, centre, normal):
    img = bpy.data.images.load(str(path), check_existing=True)
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    N, L = m.node_tree.nodes, m.node_tree.links
    b = N.get("Principled BSDF")
    t = N.new("ShaderNodeTexImage")
    t.image = img
    L.new(t.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.6
    n = Vector(normal)
    up = Vector((0, 0, 1))
    right = up.cross(n).normalized()          # viewer's right when facing the painting
    c = Vector(centre)
    bm = bmesh.new()
    vs = [bm.verts.new(c + right * du * w / 2 + up * dv * h / 2) for du, dv in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    f = bm.faces.new(vs)
    uvl = bm.loops.layers.uv.new("UVMap")
    for loop, uvc in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
        loop[uvl].uv = uvc
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    ob["kind"] = "painting"
    bpy.context.scene.collection.objects.link(ob)
    # the web's dark frame, 6 cm (web) wide, behind the canvas
    fr = 0.06 / P.SCALE
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = c - n * 0.03 + right * v.co.x * (w + 2 * fr) + up * v.co.z * (h + 2 * fr) + n * v.co.y * 0.05
    me = bpy.data.meshes.new(name + "_frame")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(flat("frame", (0.1, 0.07, 0.04)))
    fo = bpy.data.objects.new(name + "_frame", me)
    bpy.context.scene.collection.objects.link(fo)
    return ob


def hang_paintings():
    for ob in [o for o in bpy.data.objects if o.name.startswith("painting_")]:
        bpy.data.objects.remove(ob)
    recs = [P.BAY1_SIDE_RECESS[:2]] + list(P.NAVE_RECESSES)
    zc = P.HANG_CENTRE_Z
    for slug, (place, wm, iw, ih) in WEB.items():
        path = PAINTINGS_DIR / f"{slug}-texture.jpg"
        if not path.exists():
            continue
        w = wm * 1.2 / P.SCALE
        h = w * ih / iw
        if isinstance(place, int):
            side = -1 if place % 2 else 1
            r0, r1 = recs[(place - 1) // 2]
            yc = P.BAY1_NICHE_YC if place in (1, 2) else (r0 + r1) / 2
            x = side * (P.RECESS_X - 0.06)
            _plane(f"art_{slug}", path, w, h, (x, yc, zc), (-side, 0, 0))
        elif place == "end":
            x0, x1, y0, y1, hb = P.BOSCH_BASE
            _plane(f"art_{slug}", path, w, h, (0, y0 + 0.2 / P.SCALE, P.PLATFORM_Z + hb + h / 2), (0, -1, 0))
        else:
            side = -1 if place == "dome-left" else 1
            yc = (P.CROSS_Y0 + P.CROSS_Y1) / 2
            _plane(f"art_{slug}", path, w, h, (side * (P.CROSS_HALF - 0.06), yc, zc), (-side, 0, 0))


# ---------------------------------------------------------------- light linking for new parts
def link_like_hall(objs, vault=False):
    """New parts follow finish.light's rules: on the right (x > 0.5) they don't block the sun;
    parts in the vaults neither block nor take it."""
    nb = bpy.data.collections["sun_not_blocking"]
    nr = bpy.data.collections["sun_not_received"]
    for ob in objs:
        xs = [(ob.matrix_world @ Vector(c)).x for c in ob.bound_box]
        if vault or min(xs) > 0.5:
            if ob.name not in nb.objects:
                nb.objects.link(ob)
        if vault and ob.name not in nr.objects:
            nr.objects.link(ob)
    # A new entry defaults to "Include", and one included entry turns the whole set into an
    # include list (the sun would then light, or be blocked by, those parts only).
    for c in (nb, nr):
        for co in c.collection_objects:
            co.light_linking.link_state = "EXCLUDE"


# ---------------------------------------------------------------- cameras
def camera(name, loc, target, lens):
    data = bpy.data.cameras.new(name)
    data.sensor_fit, data.sensor_width, data.lens = "AUTO", 36.0, lens
    data.clip_start, data.clip_end = 0.05, 2000
    ob = bpy.data.objects.new(name, data)
    ob.location = loc
    d = Vector(target) - Vector(loc)
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(ob)
    return ob


def cameras():
    fz0, fz1 = P.NICHE_Z
    fx = -(P.NICHE_X[0] + P.NICHE_X[1]) / 2
    r0, r1 = P.NAVE_RECESSES[0]
    yb2 = (r0 + r1) / 2
    return {
        # (a) the start view: Raphael's camera (build.py), the fresco's frame, 1/3 of the scan
        "start": (bpy.data.objects["raphael"], (1280, 887)),
        # (b) mid-nave, eye height, turned towards bay 2 on the lit left side (Waterhouse below
        #     its niche); bay 3 and the crossing beyond
        "midnave": (camera("deco_midnave", (2.2, 19.6, EYE), (-6.0, 27.5, EYE + 3.2), 18), (1280, 800)),
        # (c) close views
        "facade-niche": (camera("deco_facade_niche", (fx + 2.6, P.FACADE_Y0 - 6.2, 5.2),
                                (fx, P.FACADE_Y0, (P.RELIEF_Z[0] + fz1) / 2), 38), (900, 1100)),
        "recess-niche": (camera("deco_recess_niche", (-1.2, yb2 - 1.6, EYE + 1.0),
                                (-P.RECESS_X, yb2, 6.4), 30), (900, 1100)),
        "coffers": (camera("deco_coffers", (-1.5, 23.0, EYE + 3.0), (-0.5, 28.5, 17.0), 32), (1100, 800)),
        "crossing": (camera("deco_crossing", (0.0, 27.0, EYE), (0.0, 40.0, 16.5), 18), (1100, 1000)),
        # the front-left pendentive's tondo, from under the dome
        "tondo": (camera("deco_tondo", (1.0, 39.0, EYE), (-5.17, 34.93, 16.3), 85), (900, 900)),
    }


# ---------------------------------------------------------------- render
def setup_render(samples):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    try:
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        sc.cycles.device = "GPU"
    except Exception as exc:   # noqa: BLE001
        print("GPU unavailable:", exc)
    sc.cycles.samples = samples
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces, sc.cycles.diffuse_bounces, sc.cycles.glossy_bounces = 6, 4, 2
    sc.cycles.transmission_bounces = sc.cycles.transparent_max_bounces = 2
    sc.view_settings.view_transform, sc.view_settings.look = "Standard", "None"
    sc.view_settings.exposure = P.EXPOSURE
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_depth = "8"


def render(cam_ob, size, path, scale=1.0):
    sc = bpy.context.scene
    sc.camera = cam_ob
    sc.render.resolution_x, sc.render.resolution_y = size
    sc.render.resolution_percentage = int(100 * scale)
    sc.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    print("rendered", path)
