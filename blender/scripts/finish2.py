"""Stage 2 finish of the hall (branch hall-look): bay 1's recesses and niches, the facade, floors
and steps, the crossing (transverse arches, pendentive tondi, drum, dome), the second arm and the
end wall. finish.apply() calls these after the nave arm; every number is in params.py ("Stage 2").

Conventions as in finish.py: X right, Y into the painting, Z up, metres at 100 %.
renders/hall-stage2/REPORT.md says what is read from the fresco and what is designed.
"""
import math

import bmesh
import bpy
import numpy as np
from mathutils import Vector

import params as P
from finish import (Profile, _obj, _remove, arc_points, attic_base, capital, coffer_sheet, plan_path,
                    plane_path, string_course, sweep)

NW, T, PZ, SZ = P.NAVE_HALF_W, P.WALL_T, P.PLATFORM_Z, P.SPRING_Z


# ================================================================ small mesh helpers
def _box_bm(x0, x1, y0, y1, z0, z1):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((x0 + (v.co.x + 0.5) * (x1 - x0), y0 + (v.co.y + 0.5) * (y1 - y0),
                       z0 + (v.co.z + 0.5) * (z1 - z0)))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def box(name, x0, x1, y0, y1, z0, z1, kind, mats):
    x0, x1 = sorted((x0, x1))
    y0, y1 = sorted((y0, y1))
    return _obj(name, _box_bm(x0, x1, y0, y1, z0, z1), kind, mats)


def cutter_box(x0, x1, y0, y1, z0, z1):
    x0, x1 = sorted((x0, x1))
    me = bpy.data.meshes.new("cut")
    _box_bm(x0, x1, y0, y1, z0, z1).to_mesh(me)
    ob = bpy.data.objects.new("cut", me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def cutter_prism(pts_a, pts_b):
    """Closed prism between two equal-length outlines (lists of 3D points)."""
    bm = bmesh.new()
    a = [bm.verts.new(p) for p in pts_a]
    b = [bm.verts.new(p) for p in pts_b]
    n = len(a)
    bm.faces.new(a)
    bm.faces.new(b[::-1])
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((a[i], b[i], b[j], a[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new("cut")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("cut", me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def boolean(target, cutter, op="DIFFERENCE"):
    mod = target.modifiers.new("bool", "BOOLEAN")
    mod.operation, mod.solver, mod.object = op, "EXACT", cutter
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(target.evaluated_get(dg))
    target.modifiers.clear()
    old = target.data
    target.data = me
    bpy.data.meshes.remove(old)
    bpy.data.objects.remove(cutter)


def reorient(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(ob.data)
    bm.free()


def set_material(name, mat):
    ob = bpy.data.objects.get(name)
    if ob is not None:
        ob.data.materials.clear()
        ob.data.materials.append(mat)
    return ob


def round_niche_cut(x_face, inward, yc, width, z0, z1, depth, n=24):
    """Cutter for a round-headed niche in a wall whose face is the plane x = x_face (the room on
    the side of -inward). Half-round plan for the head is simplified to a flat back."""
    half = width / 2
    spring = z1 - half
    outline = [(yc - half, z0), (yc + half, z0)]
    outline += [(yc + half * math.cos(t), spring + half * math.sin(t)) for t in np.linspace(0, math.pi, n)[1:-1]]
    outline += [(yc - half, spring)]
    a = [(x_face - inward * 0.2, y, z) for y, z in outline]
    b = [(x_face + inward * depth, y, z) for y, z in outline]
    return cutter_prism(a, b)


def frame_profile(width=None, proj=0.06, embed=0.02):
    """A flat moulded frame (fascia and a small cyma), for niches, panels and tondi."""
    width = width or P.FRAME_W
    pr = Profile(0.0, n=4)
    pr.h(proj * 0.5).v(width * 0.55).cyma_reversa(proj * 0.5, width * 0.35).v(width * 0.1)
    return pr.closed(embed=embed)


def sweep_curve(name, prof, pts, out_dir, ups, kind, mats):
    return sweep(name, prof, pts, [out_dir] * len(pts) if isinstance(out_dir, Vector) else out_dir, ups, kind, mats)


def _signed_area(pts):
    return 0.5 * sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pts, pts[1:] + pts[:1]))


def frame(name, origin, U, V, O, pts2d, mats, closed=False, prof=None):
    """Joint rule R6: a frame is one moulding swept along the opening's edge in the wall plane,
    mitred at every corner, its band running outward from the edge (the inner edge of the frame
    is the edge of the opening: no reveal, no double outline). origin + U*u + V*v spans the wall,
    O is the wall's normal into the room. An open path (round-headed frames, three-sided panels)
    ends on the member it stands on or under (sill, ledge)."""
    side = 1 if _signed_area(list(pts2d)) > 0 else -1
    world, ups = plane_path(pts2d, origin, U, V, side, closed)
    return sweep(name, prof or frame_profile(), world, [O] * len(world), ups, "stone", mats, closed=closed)


def arched_outline(uc, w, v0, v_top, n=40):
    """Left jamb up, semicircular head, right jamb down (u centre uc, width w, from v0 to the crown)."""
    hw = w / 2
    spring = v_top - hw
    return [(uc - hw, v0)] + arc_points(uc, spring, hw, math.pi, 0.0, n) + [(uc + hw, v0)]


def niche_frame(name, x_face, inward, yc, width, z0, z1, mats, n=40):
    """Frame round a round-headed niche on the wall x = x_face; it stands on the niche's sill."""
    return frame(name, Vector((x_face, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)), Vector((-inward, 0, 0)),
                 arched_outline(yc, width, z0, z1, n), mats)


def ledge(z0, z1):
    """A sill or ledge under a niche: its lowest fillet projects past any frame below (R6/R8)."""
    pr = Profile(z0, n=4)
    pr.h(0.09).v(0.04).cyma_reversa(0.04, 0.05).h(0.05).v(max(0.02, z1 - z0 - 0.17)).cyma_recta(0.04, 0.08)
    pr.v(z1 - pr.q)
    return pr.closed()


# ================================================================ bay 1: recesses and niches
def bay1(M):
    """The painted bay 1, on both sides:
    - behind the facade's thin front screen the space opens sideways (a vestibule); its back wall
      faces the visitor: the frontal face Raphael paints where the model had the facade's jamb;
    - after a short block, the wall between it and the first pier is set back the full height,
      cornice and all (the painted cornice in bay 1 recedes along X ~6.5, not 5.9): a recess;
    - an empty round-headed niche high on the recess's back wall (the painted statue niches).
    The base, the capital band and the string course of bay 1 are continuous runs built in
    facade() (joint rule R1: mouldings turn corners with mitres and never end in mid-air)."""
    fac = bpy.data.objects["facade"]
    y0, y1, xo, ztop = P.BAY1_RECESS_Y0, P.BAY1_RECESS_Y1, P.BAY1_RECESS_X, P.BAY1_RECESS_TOP
    r0, r1, rx = P.BAY1_SIDE_RECESS
    stone, stucco = [M["stone"]], [M["stucco"]]
    for side in (-1, 1):
        hand = 1 if side < 0 else -1
        boolean(fac, cutter_box(side * (NW - 0.01), side * xo, y0, y1, PZ - 0.1, ztop))
        wall = bpy.data.objects[f"nave_wall_{side}"]
        boolean(wall, cutter_box(side * (NW - 0.01), side * rx, r0, r1, PZ - 0.1, SZ))
        box(f"bay1_vestibule_back_{side}", side * NW, side * xo, y1 - 0.02, y1 + 0.001, PZ, ztop, "stucco", stucco)
        box(f"bay1_vestibule_side_{side}", side * xo, side * (xo - 0.02), y0, y1, PZ, ztop, "stucco", stucco)
        # Recess ceiling at the springing, between the vault's edge and the recess wall (the hidden
        # vault backing closed it in Blender renders; the web model has no backing). Flush with the
        # vault's springing line: nothing projects into the hall (R5).
        box(f"bay1_recess_ceiling_{side}", side * (NW + 0.005), side * (rx + 0.05), r0, r1, SZ, SZ + 0.35,
            "stucco", stucco)
        # The empty niche on the recess's back wall, its frame standing on a ledge (R6).
        yc, w = P.BAY1_NICHE_YC, P.BAY1_NICHE_W
        z0, z1 = P.BAY1_NICHE_Z
        boolean(wall, round_niche_cut(side * rx, side, yc, w, z0, z1, P.BAY1_NICHE_DEPTH))
        niche_frame(f"bay1_niche_frame_{side}", side * rx, side, yc, w, z0, z1, stone)
        fw = P.FRAME_W
        ya, yb = yc - w / 2 - fw - 0.12, yc + w / 2 + fw + 0.12
        sweep(f"bay1_niche_sill_{side}", ledge(z0 - 0.3, z0),               # returned ends (R1)
              *plan_path([(side * (rx + 0.3), ya), (side * rx, ya), (side * rx, yb), (side * (rx + 0.3), yb)], hand),
              "stone", stone)
        reorient(wall)
    reorient(fac)


# ================================================================ recesses in every bay
def niche_set(M, side, tag, yc, rx):
    """An empty round-headed niche on a recess back wall x = side*rx: cut, frame on its ledge."""
    stone = [M["stone"]]
    w = P.BAY1_NICHE_W
    z0, z1 = P.BAY1_NICHE_Z
    hand = 1 if side < 0 else -1
    wall = bpy.data.objects[f"{tag.split('_')[0]}_wall_{side}"]
    boolean(wall, round_niche_cut(side * rx, side, yc, w, z0, z1, P.BAY1_NICHE_DEPTH))
    niche_frame(f"{tag}_niche_frame_{side}", side * rx, side, yc, w, z0, z1, stone)
    fw = P.FRAME_W
    ya, yb = yc - w / 2 - fw - 0.12, yc + w / 2 + fw + 0.12
    sweep(f"{tag}_niche_sill_{side}", ledge(z0 - 0.3, z0),
          *plan_path([(side * (rx + 0.3), ya), (side * rx, ya), (side * rx, yb), (side * (rx + 0.3), yb)], hand),
          "stone", stone)


def recesses(M):
    """Bays 2-3 of the nave and both bays of the second arm, set back as in bay 1 (Raphael paints
    a recess with a statue niche in every bay; the niches stay empty): the wall between the
    pilasters (or a pier before the crossing and the end wall) is cut back to RECESS_X the full
    height, closed at the springing by a ceiling flush with the vault (R5), with a niche."""
    stucco = [M["stucco"]]
    rx = P.RECESS_X
    for side in (-1, 1):
        for tag, spans in (("nave", P.NAVE_RECESSES), ("arm2", P.ARM2_RECESSES)):
            wall = bpy.data.objects[f"{tag}_wall_{side}"]
            for i, (a, b) in enumerate(spans):
                boolean(wall, cutter_box(side * (NW - 0.01), side * rx, a, b, PZ - 0.1, SZ))
                box(f"{tag}_recess_ceiling_{side}_{i}", side * (NW + 0.005), side * (rx + 0.05), a, b, SZ, SZ + 0.35,
                    "stucco", stucco)
                niche_set(M, side, f"{tag}_r{i}", (a + b) / 2, rx)
            reorient(wall)


def wall_plan(side, around_vestibule=True):
    """The plan of one side wall's face from the facade's outer edge to the end wall: facade
    front, the screen's jamb, the vestibule (or straight across its mouth, for the entablature
    that spans it as a lintel), the block, every recess, every pilaster's front, the piers
    before the crossing and the end wall, the crossing's side. The continuous runs follow it."""
    X = lambda v: side * v                                       # noqa: E731
    y0, y1, xo = P.BAY1_RECESS_Y0, P.BAY1_RECESS_Y1, P.BAY1_RECESS_X
    r0, r1, rx = P.BAY1_SIDE_RECESS
    W, D = P.PILASTER_W, P.PILASTER_D
    pts = [(X(P.FACADE_HALF_W), P.FACADE_Y0), (X(NW), P.FACADE_Y0)]
    if around_vestibule:
        pts += [(X(NW), y0), (X(xo), y0), (X(xo), y1), (X(NW), y1)]
    pts += [(X(NW), r0), (X(rx), r0), (X(rx), r1)]
    recs = list(P.NAVE_RECESSES)
    for yc, (a, b) in zip(P.PILASTERS_Y, recs):
        pts += [(X(NW - D), yc - W / 2), (X(NW - D), yc + W / 2), (X(rx), a), (X(rx), b)]
    pts += [(X(NW), recs[-1][1]), (X(NW), P.ARM2_RECESSES[0][0])]          # pier, crossing, pier
    (a0, b0), (a1, b1) = P.ARM2_RECESSES
    yc = P.ARM2_PILASTERS_Y[0]
    pts += [(X(rx), a0), (X(rx), b0), (X(NW - D), yc - W / 2), (X(NW - D), yc + W / 2), (X(rx), a1), (X(rx), b1),
            (X(NW), b1), (X(NW), P.ARM2_Y1)]
    return pts


def wall_runs(M):
    """The side walls' continuous mouldings (joint rules R1, R2): one mitred run each per side.
    - base and capital band: along every face of the wall (vestibule, recesses, pilasters, piers);
      they are the pilasters' bases and capitals;
    - entablature: the same, but straight across the vestibule's mouth (its lintel), breaking
      forward over every pilaster;
    - string course: where no niche rises through its height: the facade front, the jamb, the
      vestibule and the block (ending against bay 1's recess back wall), the piers and the
      crossing between the nave's last recess and the second arm's first (each end returned
      into the recess's end wall and stopped against its back wall), and the last pier."""
    from finish import _clean, entablature
    stone = [M["stone"]]
    rx = P.RECESS_X
    _remove("string_course_-1", "string_course_1", "entablature_-1", "entablature_1")
    for side in (-1, 1):
        hand = 1 if side < 0 else -1
        X = lambda v: side * v                                       # noqa: E731
        full = _clean(wall_plan(side))
        lintel = _clean(wall_plan(side, around_vestibule=False))
        sweep(f"base_{side}", attic_base(PZ), *plan_path(full, hand), "stone", stone)
        sweep(f"capital_band_{side}", capital(P.ENTABLATURE_Z0), *plan_path(full, hand), "stone", stone)
        sweep(f"entablature_{side}", entablature(P.ENTABLATURE_Z0), *plan_path(lintel, hand), "stone", stone)
        sc = string_course(*P.STRING_COURSE)
        r0 = P.BAY1_SIDE_RECESS[0]
        i_front = full.index((X(NW), r0)) if (X(NW), r0) in full else None
        front = full[:i_front + 1] + [(X(rx), r0)]
        mid = [(X(rx), P.NAVE_RECESSES[-1][1]), (X(NW), P.NAVE_RECESSES[-1][1]),
               (X(NW), P.ARM2_RECESSES[0][0]), (X(rx), P.ARM2_RECESSES[0][0])]
        end = [(X(rx), P.ARM2_RECESSES[-1][1]), (X(NW), P.ARM2_RECESSES[-1][1]), (X(NW), P.ARM2_Y1)]
        for i, run in enumerate((front, mid, end)):
            sweep(f"string_course_{side}_{i}", sc, *plan_path(_clean(run), hand), "stone", stone)


# ================================================================ facade
def facade(M):
    """The facade's front: niche frames and relief-panel frames by rule R6; the panel frame is
    three-sided and ends under the niche's ledge, which is the panel's top member. (Its base,
    capital band, string course and entablature are the side walls' runs: wall_runs.)"""
    stone = [M["stone_facade"]]
    set_material("facade", M["stone_facade"])
    _remove("string_course_-1", "string_course_1")
    x_out = P.FACADE_HALF_W
    y = P.FACADE_Y0
    y0, y1, xo = P.BAY1_RECESS_Y0, P.BAY1_RECESS_Y1, P.BAY1_RECESS_X
    r0, r1, rx = P.BAY1_SIDE_RECESS
    W, D = P.PILASTER_W, P.PILASTER_D
    yc0 = P.PILASTERS_Y[0]
    for side in (-1, 1):
        X = lambda v: side * v                                       # noqa: E731
        # Frames on the front niche and the relief panel below it (facade plane y = front).
        x0, x1 = P.NICHE_X
        xc, w = X((x0 + x1) / 2), x1 - x0
        nz0, nz1 = P.NICHE_Z
        rz0, rz1 = P.RELIEF_Z
        org, U, V, O = Vector((0, y, 0)), Vector((1, 0, 0)), Vector((0, 0, 1)), Vector((0, -1, 0))
        frame(f"facade_niche_frame_{side}", org, U, V, O, arched_outline(xc, w, nz0, nz1), stone)
        frame(f"facade_panel_frame_{side}", org, U, V, O,
              [(xc + w / 2, rz1), (xc + w / 2, rz0), (xc - w / 2, rz0), (xc - w / 2, rz1)], stone)
        fw = P.FRAME_W
        # The ledge reaches 3 cm past the frame: further would cross the screen's corner (R1).
        xa, xb = xc - (w / 2 + fw + 0.03), xc + (w / 2 + fw + 0.03)
        sweep(f"facade_niche_sill_{side}", ledge(rz1, nz0),                  # returned ends (R1)
              *plan_path([(xa, y + 0.3), (xa, y), (xb, y), (xb, y + 0.3)], 1), "stone", stone)


# ================================================================ floors and steps
def floor_material_lower(M):
    """The lower floor as painted (u 1150-2700, v 2380-2661; plan unroll in REPORT.md): mauve
    squares holding a white square ring, set in white bands."""
    A = P.ALBEDO
    m = bpy.data.materials.new("floor_lower")
    m.use_nodes = True
    N, L = m.node_tree.nodes, m.node_tree.links
    bsdf = N.get("Principled BSDF")
    W, H, ppm = 400, 240, 100                           # one module (period) as a tiling image
    px, py = P.LOWER_FLOOR_MODULE
    xs = (np.arange(W) + 0.5) / W * px
    ys = (np.arange(H) + 0.5) / H * py
    X, Y = np.meshgrid(xs, ys)
    dx, dy = np.abs(X - px / 2), np.abs(Y - py / 2)
    b = P.LOWER_FLOOR_BAND
    field = (dx < px / 2 - b) & (dy < py / 2 - b)
    ro, rw = P.LOWER_FLOOR_RING
    ring = (np.maximum(dx / ro[0], dy / ro[1]) < 1.0) & (np.maximum(dx / (ro[0] - rw), dy / (ro[1] - rw)) >= 1.0)
    c = np.empty((H, W, 4), np.float32)
    c[...] = (*A["lower_white"], 1)
    c[field] = (*A["floor_mauve"], 1)
    c[field & ring] = (*A["lower_white"], 1)
    img = bpy.data.images.new("lower_floor_module", W, H, alpha=False, float_buffer=True)
    img.colorspace_settings.name = "Linear Rec.709"
    img.pixels.foreach_set(c.ravel())
    img.pack()
    tc, mp = N.new("ShaderNodeTexCoord"), N.new("ShaderNodeMapping")
    mp.inputs["Location"].default_value = (-P.LOWER_FLOOR_X0 / px, -P.LOWER_FLOOR_Y0 / py, 0)
    mp.inputs["Scale"].default_value = (1 / px, 1 / py, 1)
    L.new(tc.outputs["Object"], mp.inputs["Vector"])
    t = N.new("ShaderNodeTexImage")
    t.image, t.extension, t.interpolation = img, "REPEAT", "Linear"
    L.new(mp.outputs["Vector"], t.inputs["Vector"])
    L.new(t.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.4
    m["detail"], m["tile"], m["origin"] = "floor_lower", [px, py], [P.LOWER_FLOOR_X0, P.LOWER_FLOOR_Y0]
    m["riser_detail"] = "step_riser"
    return m


def floors(M, floor_mat):
    """Materials for the floors and steps; the nave's floor pattern covers the whole platform."""
    lower = floor_material_lower(M)
    for n in ("floor_lower", "floor_lower_sides_l", "floor_lower_sides_r"):
        set_material(n, lower)
    for n in ("platform",):
        ob = bpy.data.objects.get(n)
        if ob:
            ob.data.materials.clear()
            ob.data.materials.append(floor_mat)
    steps = [n for n in bpy.data.objects.keys() if n.startswith(("step_", "podium_"))]
    for n in steps:
        set_material(n, M["step"])
    for n in [n for n in bpy.data.objects.keys() if n.startswith("pedestal_")]:   # the blocks beside the steps
        set_material(n, M["stone"])
    # Nosings: a small round on every tread edge of the central flight (designed).
    stone = [M["step"]]
    hw = P.STEP_HALF_W
    for i, (y, z) in enumerate(P.STEPS):
        pr = Profile(z - 0.06, n=4)
        pr.h(0.025).torus(0.06)
        if i + 1 < len(P.STEPS):
            # R1: the step's ends are exposed, so the nosing returns along them to the next riser
            # (or the podium's face, for the top step).
            yb = min(P.STEPS[i + 1][0], P.PODIUM_Y0) if i + 2 == len(P.STEPS) else P.STEPS[i + 1][0]
            run = [(hw, yb), (hw, y), (-hw, y), (-hw, yb)]
        else:
            run = [(hw, y), (-hw, y)]
        sweep(f"step_nosing_{i + 1}", pr.closed(embed=0.03), *plan_path(run, 1), "stone", stone)


# ================================================================ crossing
def crossing(M):
    """Transverse arches with coffered soffits and a thin light edge at the crossing, the closed
    side walls with blind arches, pendentives with empty tondo frames, the drum and the dome."""
    CH = P.CROSS_HALF
    Y0, Y1 = P.CROSS_Y0, P.CROSS_Y1
    ycen = (Y0 + Y1) / 2
    stone, stucco = [M["stone"]], [M["stucco"]]
    _remove("arch_back")
    top = P.DRUM_Z0 + 1.5
    back = P.COFFER_BACK
    rb = CH + back
    ya, yb = Y1, Y1 + P.TRANSVERSE_T
    pts = [(-(NW + T), PZ), (-CH, PZ), (-CH, SZ), (-rb, SZ)]
    pts += [(rb * math.cos(t), SZ + rb * math.sin(t)) for t in np.linspace(math.pi, 0, 97)[1:-1]]
    pts += [(rb, SZ), (CH, SZ), (CH, PZ), (NW + T, PZ), (NW + T, top), (-(NW + T), top)]
    bm = bmesh.new()
    f = bm.faces.new([bm.verts.new((x, ya, z)) for x, z in pts])
    ext = bmesh.ops.extrude_face_region(bm, geom=[f])
    bmesh.ops.translate(bm, verts=[e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)], vec=(0, yb - ya, 0))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    _obj("arch_back", bm, "stone", stone)
    k = CH / NW
    pat = dict(col=P.COFFER_COL * k, row=P.COFFER_ROW, flat=P.COFFER_FLAT * k, s0=0.0, y_ref=P.COFFER_Y_REF,
               rib=P.COFFER_RIB, steps=P.COFFER_STEPS, splay=P.COFFER_SPLAY)
    fs = P.COFFER_FIELD_S * k
    coffer_sheet("arch_back_soffit", CH, SZ, ya, yb, (-fs, fs, ya, yb), pat,
                 [M["vault_rib"], M["coffer"], M["coffer_riser"], M["coffer_tread"]])
    # Thin light edge where the coffers meet the crossing (fresco: no archivolt, a light line).
    edge = Profile(0.0, n=4)
    edge.h(0.012).torus(0.07)
    ts = np.linspace(0, math.pi, 97)
    for tag, yy, sgn in (("front", Y0, 1), ("back", Y1, -1)):
        # On the arch's face towards the crossing (out = +-y), sitting just outside the intrados.
        sweep(f"arch_{tag}_edge", edge.closed(embed=0.02),
              [Vector((CH * math.cos(t), yy, SZ + CH * math.sin(t))) for t in ts],
              [Vector((0, sgn, 0))] * len(ts), [Vector((math.cos(t), 0, math.sin(t))) for t in ts], "stone", stone)
    # Side walls (closed): stucco, a blind-arch moulding along the lunette edge.
    for side in (-1, 1):
        set_material(f"crossing_side_{side}", M["stucco"])
        # R9: the lunette's blind arch runs inside the arch line (its band from the intrados
        # inwards), so its crown meets the drum's base ring and its feet stand on the entablature.
        pts = [Vector((side * CH, ycen + CH * math.cos(t), SZ + CH * math.sin(t))) for t in ts]
        sweep(f"crossing_blind_arch_{side}", frame_profile(0.22, 0.07), pts,
              [Vector((-side, 0, 0))] * len(ts), [Vector((0, -math.cos(t), -math.sin(t))) for t in ts],
              "stone", stone)
    set_material("pendentives", M["stucco"])
    # Tondo frames on the four pendentives: a moulded ring and a sunk plain disc (empty).
    Rs = CH * math.sqrt(2)
    h, rt = tondo_fit(CH, Rs)
    r_h = math.sqrt(Rs ** 2 - h ** 2)
    for sx in (-1, 1):
        for sy in (-1, 1):
            d = Vector((sx * r_h / math.sqrt(2), sy * r_h / math.sqrt(2), h))
            c = Vector((0, ycen, SZ)) + d
            nrm = -d.normalized()                          # into the crossing
            a = Vector((0, 0, 1)).cross(nrm).normalized()  # horizontal tangent
            bvec = nrm.cross(a).normalized()
            ring = [c + rt * (math.cos(t) * a + math.sin(t) * bvec) for t in np.linspace(0, 2 * math.pi, 65)]
            ups = [(math.cos(t) * a + math.sin(t) * bvec) for t in np.linspace(0, 2 * math.pi, 65)]
            sweep(f"tondo_frame_{sx}_{sy}", frame_profile(0.22, 0.10, embed=0.1), ring, [nrm] * len(ring), ups,
                  "stone", stone)
            # Plain disc slightly sunk behind the ring (the painted reliefs left out).
            bm = bmesh.new()
            disc = [bm.verts.new(c - nrm * 0.02 + (rt + 0.02) * (math.cos(t) * a + math.sin(t) * bvec))
                    for t in np.linspace(0, 2 * math.pi, 48, endpoint=False)]
            face = bm.faces.new(disc)
            bm.normal_update()
            if face.normal.dot(nrm) < 0:
                bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
            _obj(f"tondo_disc_{sx}_{sy}", bm, "stucco", [M["tondo"]])
    # Drum: materials, pilasters between the windows, base, sill and top cornices.
    for n in ("drum", "dome", "drum_cornice_low", "drum_cornice_high"):
        set_material(n, M["stucco_drum"] if n in ("drum", "dome") else M["stone"])
    R_IN = CH
    nwin = P.DRUM_WINDOWS
    pil_w = 2 * math.pi * R_IN / nwin - P.DRUM_WINDOW_W
    zp0, zp1 = P.DRUM_WIN_Z[0] - 0.4, P.DRUM_Z1 - 0.2
    for kk in range(nwin):
        a = math.pi / 2 + 2 * math.pi * (kk + 0.5) / nwin
        cx, cy = R_IN * math.cos(a), ycen + R_IN * math.sin(a)
        tvec = Vector((-math.sin(a), math.cos(a), 0))
        nvec = Vector((-math.cos(a), -math.sin(a), 0))
        hw = min(0.3, pil_w * 0.35)
        bm = bmesh.new()
        corners = [Vector((cx, cy, 0)) + tvec * s * hw + nvec * dd for s, dd in ((-1, -0.05), (1, -0.05), (1, 0.12), (-1, 0.12))]
        vb = [bm.verts.new((p.x, p.y, zp0)) for p in corners]
        vt = [bm.verts.new((p.x, p.y, zp1)) for p in corners]
        bm.faces.new(vb[::-1]); bm.faces.new(vt)
        for i in range(4):
            j = (i + 1) % 4
            bm.faces.new((vb[i], vb[j], vt[j], vt[i]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        _obj(f"drum_pilaster_{kk}", bm, "stone", stone)
    # Dome coffers (designed, Pantheon-like): rings of sunk square-ish panels on the inner shell.
    dome_coffers(M, ycen, R_IN)


def tondo_fit(CH, Rs, band=0.22, clear=0.3):
    """R9: the largest tondo (ring radius + band) that stays inside its pendentive: clear of the
    lunette arches' mouldings (|x|, |y| <= CH - clear) and below the drum's base ring. Searched
    over the height of its centre; returns (height above the springing, radius)."""
    best = (P.TONDO_H, 0.0)
    for h in np.linspace(0.45 * CH, 0.85 * CH, 41):
        r_h = math.sqrt(Rs ** 2 - h ** 2)
        d = Vector((r_h / math.sqrt(2), r_h / math.sqrt(2), h))
        nrm = -d.normalized()
        a = Vector((0, 0, 1)).cross(nrm).normalized()
        b = nrm.cross(a).normalized()
        lo, hi = 0.1, P.TONDO_R
        for _ in range(30):
            rt = (lo + hi) / 2
            ok = True
            for t in np.linspace(0, 2 * math.pi, 72, endpoint=False):
                q = d + (rt + band) * (math.cos(t) * a + math.sin(t) * b)
                if q.x > CH - clear or q.y > CH - clear or q.z > CH - 0.1 or q.z < 0.5:
                    ok = False
                    break
            lo, hi = (rt, hi) if ok else (lo, rt)
        if lo > best[1]:
            best = (h, lo)
    return best


def revolve_profile(name, prof_rz, centre, kind, mats, segments=144):
    bm = bmesh.new()
    cx, cy = centre
    rings = []
    for kk in range(segments):
        a = 2 * math.pi * kk / segments
        rings.append([bm.verts.new((cx + r * math.cos(a), cy + r * math.sin(a), z)) for r, z in prof_rz])
    n = len(prof_rz)
    for kk in range(segments):
        a, b = rings[kk], rings[(kk + 1) % segments]
        for j in range(n - 1):
            bm.faces.new((a[j], a[j + 1], b[j + 1], b[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return _obj(name, bm, kind, mats, smooth_angle=40)


def drum_cornices(M, ycen, R_IN):
    """Base ring on the pendentives, sill cornice under the windows, cornice under the dome."""
    stone = [M["stone"]]
    _remove("drum_cornice_low", "drum_cornice_high")
    for name, z0, prof_kind in (("drum_base_ring", P.DRUM_Z0, "base"), ("drum_sill", P.DRUM_WIN_Z[0] - 0.45, "sill"),
                                ("drum_top_cornice", P.DRUM_Z1 - 0.55, "top")):
        if prof_kind == "base":
            pr = Profile(z0, n=4)
            pr.h(0.05).v(0.25).cyma_reversa(0.06, 0.08).h(0.18).v(0.16).cyma_recta(0.08, 0.12)
        elif prof_kind == "sill":
            pr = Profile(z0, n=4)
            pr.cavetto(0.1, 0.1).h(0.02).v(0.12).ovolo(0.06, 0.06)
        else:
            pr = Profile(z0, n=4)
            pr.h(0.04).v(0.12).ovolo(0.08, 0.08).h(0.22).v(0.18).cyma_recta(0.08, 0.15)
        pts = pr.closed(embed=0.04)
        prof_rz = [(R_IN - p, q) for p, q in pts] + [(R_IN - pts[0][0], pts[0][1])]
        revolve_profile(name, prof_rz, (0, ycen), "stone", stone)


def dome_coffers(M, ycen, R_IN):
    """Designed (the fresco doesn't show the dome): a grid of ribs on the inner shell, reading as
    rings of sunk panels diminishing towards the oculus, as in the Pantheon."""
    drum_cornices(M, ycen, R_IN)
    zc = P.DRUM_Z1
    rings, per_ring = P.DOME_COFFER_RINGS, P.DOME_COFFER_COUNT
    phi_oc = math.acos(P.OCULUS_R / R_IN)
    phis = np.linspace(0.04, phi_oc - 0.08, rings + 1)
    dr, w = 0.2, 0.14                                   # rib depth, half-width (radians scaled below)

    def P3(a, ph, r):
        return Vector((r * math.cos(ph) * math.cos(a), ycen + r * math.cos(ph) * math.sin(a), zc + r * math.sin(ph)))
    bm = bmesh.new()

    def quad_strip(points_a, points_b):
        va = [bm.verts.new(p) for p in points_a]
        vb = [bm.verts.new(p) for p in points_b]
        for i in range(len(va) - 1):
            bm.faces.new((va[i], va[i + 1], vb[i + 1], vb[i]))
    # Parallels: a band at each ring boundary (front face and two flanks).
    for ph in phis:
        dph = w / R_IN
        A = [P3(a, ph - dph, R_IN - 0.01) for a in np.linspace(0, 2 * math.pi, 145)]
        B = [P3(a, ph - dph, R_IN - dr) for a in np.linspace(0, 2 * math.pi, 145)]
        C = [P3(a, ph + dph, R_IN - dr) for a in np.linspace(0, 2 * math.pi, 145)]
        D = [P3(a, ph + dph, R_IN - 0.01) for a in np.linspace(0, 2 * math.pi, 145)]
        quad_strip(A, B); quad_strip(B, C); quad_strip(C, D)
    # Meridians between the parallels.
    for kk in range(per_ring):
        a = 2 * math.pi * kk / per_ring
        for i in range(rings):
            ph = np.linspace(phis[i], phis[i + 1], 8)
            da = w / (R_IN * math.cos(phis[i + 1]))
            A = [P3(a - da, p, R_IN - 0.01) for p in ph]
            B = [P3(a - da, p, R_IN - dr) for p in ph]
            C = [P3(a + da, p, R_IN - dr) for p in ph]
            D = [P3(a + da, p, R_IN - 0.01) for p in ph]
            quad_strip(A, B); quad_strip(B, C); quad_strip(C, D)
    bm.normal_update()
    centre = Vector((0, ycen, zc))
    for f in bm.faces:                       # faces point into the dome's space
        if f.normal.dot(centre - f.calc_center_median()) < 0:
            f.normal_flip()
    _obj("dome_ribs", bm, "vault_fine", [M["vault_rib"]])
    set_material("dome", M["coffer"])


# ================================================================ end wall
def bosch_base(M):
    """The low stone base the Bosch stands on in the doorway (the web hung it on a grey box)."""
    x0, x1, y0, y1, h = P.BOSCH_BASE
    box("bosch_base", x0, x1, y0, y1, PZ, PZ + h, "stone", [M["stone_far"]])


def fill_empty_slots(M):
    """Faces cut by material-less booleans (the niches) have no material: stucco."""
    for ob in bpy.data.objects:
        if ob.type == "MESH" and any(m is None for m in ob.data.materials):
            for i, m in enumerate(ob.data.materials):
                if m is None:
                    ob.data.materials[i] = M["stucco"]


def end_wall(M):
    """Doric entablature on the end wall as painted (architrave, triglyph frieze, cornice), the
    door's archivolt and imposts, pilasters flanking the door. Joint rules:
    - R5: the entablature stays under the second arm's vault: it ends where the vault's intrados
      comes down to its top, with returns into the wall (R1), never passing through the vault;
    - R2: it breaks forward over the two pilasters, which carry Doric capitals; a triglyph stands
      over each pilaster's axis and the others are spaced evenly between;
    - R3: the archivolt's full width lands on the impost, which runs from the jamb to the
      pilaster's side and dies into it (the pilaster projects further than the impost)."""
    stone = [M["stone_far"]]
    set_material("end_wall", M["stucco_far"])
    _remove("end_entablature")
    y = P.ARM2_Y1
    a0, a1, f1, c1 = P.END_DORIC
    D, X0, PW = P.END_PILASTER_D, P.END_PILASTER_X0, P.END_PILASTER_W
    dh, ds = P.DOOR_HALF, P.DOOR_SPRING
    pi, po = dh + X0, dh + X0 + PW                     # pilaster's inner and outer edges
    pr = Profile(a0, n=5)
    pr.h(0.04).v(a1 - a0 - 0.12).h(0.05).v(0.12)                            # architrave + taenia
    pr.h(-0.05).v(f1 - a1)                                                   # frieze
    pr.h(0.08).v(0.06).h(0.25).v(c1 - f1 - 0.16).cyma_recta(0.06, 0.1)     # cornice
    prof = pr.closed()
    proj = max(p for p, q in prof)
    # It spans from one pilaster's outer face to the other's, breaking forward over both and
    # returning into the wall at its ends; its outer corners must clear the vault's intrados.
    xv = math.sqrt(NW ** 2 - (c1 - SZ) ** 2)
    if po + proj > xv - 0.05:
        raise ValueError(f"end entablature corner {po + proj:.2f} reaches the vault ({xv:.2f})")
    run = [(po, y + 0.5), (po, y - D), (pi, y - D), (pi, y),
           (-pi, y), (-pi, y - D), (-po, y - D), (-po, y + 0.5)]
    sweep("end_entablature", prof, *plan_path(run, -1), "stone", stone)
    # Triglyphs: one over each pilaster's axis, evenly spaced between (painted spacing ~1.64 m).
    axis = (pi + po) / 2
    n = max(1, round(axis / P.END_TRIGLYPH[0]))
    tw = P.END_TRIGLYPH[1]
    for i in range(-n, n + 1):
        x = i * axis / n
        face = y - 0.04 - (D if abs(i) == n else 0.0)    # frieze face (forward over the pilasters)
        box(f"triglyph_{i}", x - tw / 2, x + tw / 2, face - 0.07, face, a1 + 0.02, f1 - 0.02, "stone", stone)
        for g in (-1, 0, 1):   # the three bars' grooves, as thin dark slots
            box(f"triglyph_groove_{i}_{g}", x + g * tw / 3 - 0.018, x + g * tw / 3 + 0.018, face - 0.075, face - 0.065,
                a1 + 0.1, f1 - 0.1, "stone", [M["groove"]])
    # Door: archivolt (two fasciae and a cyma) no wider than the impost, imposts, pilasters.
    width = X0 - 0.03
    k = width / 0.42
    ar = Profile(0.0, n=4)
    # Projection no more than the impost's top (0.06 m), so the bands land on it (R3).
    ar.h(0.02).v(0.15 * k).h(0.012).v(0.17 * k).cyma_reversa(0.015, 0.06 * k).h(0.006).v(0.04 * k)
    ts = np.linspace(0, math.pi, 97)
    sweep("end_door_archivolt", ar.closed(embed=0.0),
          [Vector((dh * math.cos(t), y, ds + dh * math.sin(t))) for t in ts], [Vector((0, -1, 0))] * len(ts),
          [Vector((math.cos(t), 0, math.sin(t))) for t in ts], "stone", stone)
    for side in (-1, 1):
        sweep(f"end_door_impost_{side}", capital(ds), *plan_path(
            [(side * pi, y), (side * dh, y), (side * dh, y + T)], -side), "stone", stone)
        px0 = side * pi
        box(f"end_pilaster_{side}", px0, side * po, y - D, y, PZ, a0, "stone", stone)
        ring = [(px0, y + 0.03), (px0, y - D), (side * po, y - D), (side * po, y + 0.03)]
        sweep(f"end_pilaster_base_{side}", attic_base(PZ), *plan_path(ring, side), "stone", stone)
        sweep(f"end_pilaster_capital_{side}", capital(a0), *plan_path(ring, side), "stone", stone)


# ================================================================ bay 1 hanging options
def _image_plane(name, path, w, h, centre, normal_x):
    """A painting as an emissive-free textured plane on a side wall (normal along +-X)."""
    img = bpy.data.images.load(path, check_existing=True)
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    N, L = m.node_tree.nodes, m.node_tree.links
    b = N.get("Principled BSDF")
    t = N.new("ShaderNodeTexImage")
    t.image = img
    L.new(t.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.6
    bm = bmesh.new()
    x, y, z = centre
    s = -normal_x                                   # face the room
    vs = [bm.verts.new((x, y + s * dy, z + dz)) for dy, dz in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2))]
    f = bm.faces.new(vs)
    uv = bm.loops.layers.uv.new()
    for loop, c in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
        loop[uv].uv = c
    bm.normal_update()
    if f.normal.x * normal_x < 0:
        bmesh.ops.reverse_faces(bm, faces=[f])
        for loop, c in zip(f.loops, ((1, 0), (0, 0), (0, 1), (1, 1))):
            loop[uv].uv = c
    ob = _obj(name, bm, "painting", [m])
    # thin dark frame behind, 6 cm wide (web frame)
    fr = 0.06 / P.SCALE
    _obj(name + "_frame", _box_bm(*sorted((x - normal_x * 0.005, x - normal_x * 0.05)), y - w / 2 - fr, y + w / 2 + fr,
                                  z - h / 2 - fr, z + h / 2 + fr), "painting", [flat_mat("frame", (0.1, 0.07, 0.04))])
    return ob


def flat_mat(name, rgb):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes.get("Principled BSDF").inputs["Base Color"].default_value = (*rgb, 1)
    return m


def hang_bay1(option, paintings_dir):
    """Replace the placeholders of places 1-2 with the Mucha (left) and the Klimt (right) at their
    web sizes (100 % model units) on bay 1's recess wall. "below": both under the niches;
    "inside": the Mucha inside its niche (the Klimt, 2.5 m wide, cannot be)."""
    _remove("painting_01", "painting_02")
    zc = P.HANG_CENTRE_Z
    r0, r1, rx = P.BAY1_SIDE_RECESS
    yc = P.BAY1_NICHE_YC
    mw, mh = P.MUCHA_100
    kw, kh = P.KLIMT_100
    _image_plane("klimt", f"{paintings_dir}/klimt-water-serpents-ii-texture.jpg", kw, kh, (rx - 0.06, yc, zc), -1)
    if option == "inside":
        zn = (P.BAY1_NICHE_Z[0] + P.BAY1_NICHE_Z[1] - P.BAY1_NICHE_W / 2) / 2
        _image_plane("mucha", f"{paintings_dir}/mucha-summer-texture.jpg", mw, mh,
                     (-rx - P.BAY1_NICHE_DEPTH + 0.06, yc, zn), 1)
    else:
        _image_plane("mucha", f"{paintings_dir}/mucha-summer-texture.jpg", mw, mh, (-rx + 0.06, yc, zc), 1)
    return yc
