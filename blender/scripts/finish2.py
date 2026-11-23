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


def niche_cut(wall, side, x_face, yc, width, z0, z1, depth):
    """A niche in a side wall: shell-headed (shells.py, deco round) or the plain round head."""
    if getattr(P, "NICHE_SHELL", None):
        import shells
        a = width / 2
        shells.cut(wall, Vector((x_face, yc, z1 - a)), Vector((0, -side, 0)), Vector((side, 0, 0)), a, depth, z0,
                   P.NICHE_SHELL["flutes_recess"])
    else:
        boolean(wall, round_niche_cut(x_face, side, yc, width, z0, z1, depth))


def frame_profile(width=None, proj=0.06, embed=0.0):
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
        # The vestibule's walls are the facade's own cut faces, in stucco (stage 5 had 2 cm stucco
        # liners in front of them: R13).
        if M["stucco"].name not in fac.data.materials:
            fac.data.materials.append(M["stucco"])
        mi = list(fac.data.materials).index(M["stucco"])
        for poly in fac.data.polygons:
            c = fac.matrix_world @ poly.center
            if (NW - 0.02 < side * c.x < xo + 0.001 and y0 - 0.001 < c.y < y1 + 0.001 and c.z < ztop - 0.001
                    and abs(poly.normal.z) < 0.5 and not (abs(c.y - y0) < 0.002 and poly.normal.y < -0.5)):
                poly.material_index = mi
        # Recess ceiling at the springing, between the vault's edge and the recess wall (the hidden
        # vault backing closed it in Blender renders; the web model has no backing). Flush with the
        # vault's springing line: nothing projects into the hall (R5).
        box(f"bay1_recess_ceiling_{side}", side * (NW + 0.03), side * (rx + 0.05), r0, r1, SZ, SZ + 0.35,
            "stucco", stucco)
        # The empty niche on the recess's back wall, its frame standing on a ledge (R6).
        yc, w = P.BAY1_NICHE_YC, P.BAY1_NICHE_W
        z0, z1 = P.BAY1_NICHE_Z
        niche_cut(wall, side, side * rx, yc, w, z0, z1, P.BAY1_NICHE_DEPTH)
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
    niche_cut(wall, side, side * rx, yc, w, z0, z1, P.BAY1_NICHE_DEPTH)
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
                box(f"{tag}_recess_ceiling_{side}_{i}", side * (NW + 0.03), side * (rx + 0.05), a, b, SZ, SZ + 0.35,
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
        if getattr(P, "RELIEF_SCROLL", False):
            relief_scroll(M, side, xc - w / 2, rz0, w, rz1 - rz0)


def relief_scroll(M, side, x0, z0, w, h):
    """Deco round (idea 5): the sunk panel's back face takes the acanthus scroll in grisaille, a
    detail tile mapped once over the panel (bake.detail_uvs: "uv_origin"). The scroll's relief is
    painted, as Raphael's grisaille is: tools/relief_scroll.py draws it, make_detail.py ships it."""
    fac = bpy.data.objects["facade"]
    m = M["stone_facade"].copy()
    m.name = f"relief_scroll_{side}"
    m["detail"], m["tile"], m["uv_origin"] = "relief_scroll", [w, h], [x0, z0]
    if m.name not in fac.data.materials:
        fac.data.materials.append(m)
    mi = list(fac.data.materials).index(m)
    mw = fac.matrix_world
    yb = P.FACADE_Y0 + P.RELIEF_DEPTH
    n = 0
    for poly in fac.data.polygons:
        c = mw @ poly.center
        if (abs(c.y - yb) < 0.002 and (mw.to_3x3() @ poly.normal).y < -0.9
                and x0 - 0.001 < c.x < x0 + w + 0.001 and z0 - 0.001 < c.z < z0 + h + 0.001):
            poly.material_index = mi
            n += 1
    if n == 0:
        raise RuntimeError(f"relief panel {side}: no back face found")


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
        # Profile on the left of the run: forward over the riser below, outward at the returns.
        # (Stage 4 had it on the right: the nosings lay inside the steps, their backs on the risers.)
        sweep(f"step_nosing_{i + 1}", pr.closed(), *plan_path(run, -1), "stone", stone)


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
                 [M["vault_rib"], M["coffer"], M["coffer_riser"], M["coffer_tread"]],
                 lm_islands=lambda s, y: (0, 1.0))          # one lightmap sheet on the texel grid
    # Thin light edge where the coffers meet the crossing (fresco: no archivolt, a light line).
    # Round 8: its underside 6 mm inside the opening. The pendentives' facets dip up to 2.5 mm
    # below the arch's line right at its face, and that sliver, baked dark, showed as a black
    # line looking up at the dome. The edge now covers it.
    edge = Profile(-0.006, n=4)
    edge.h(0.012).torus(0.07)
    ts = np.linspace(0, math.pi, 97)
    for tag, yy, sgn in (("front", Y0, 1), ("back", Y1, -1)):
        # On the arch's face towards the crossing (out = +-y), sitting just outside the intrados.
        sweep(f"arch_{tag}_edge", edge.closed(),
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
    # R13: where the pendentives' mesh lies on the arches' faces (the planes y = Y0, Y1), the arch
    # face is the surface; the pendentives' coplanar faces there go.
    pen = bpy.data.objects["pendentives"]
    bm = bmesh.new()
    bm.from_mesh(pen.data)
    mw = pen.matrix_world
    on = [f for f in bm.faces if abs((mw.to_3x3() @ f.normal).y) > 0.999
          and min(abs((mw @ f.calc_center_median()).y - yy) for yy in (Y0, Y1)) < 0.002]
    # ... and their top, under the drum (its triangulation leaves slivers on the arches' faces).
    on += [f for f in bm.faces if (mw.to_3x3() @ f.normal).z > 0.99
           and abs((mw @ f.calc_center_median()).z - P.DRUM_Z0) < 0.02]
    bmesh.ops.delete(bm, geom=on, context="FACES")
    bm.to_mesh(pen.data)
    bm.free()
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
            # The ring starts at its top (towards the drum: bvec points up), where the lightmap strip
            # along it (finish.sweep) has its one closing cut; the same 64 points as from t = 0.
            ts64 = np.linspace(math.pi / 2, math.pi / 2 + 2 * math.pi, 64, endpoint=False)
            ring = [c + rt * (math.cos(t) * a + math.sin(t) * bvec) for t in ts64]
            ups = [(math.cos(t) * a + math.sin(t) * bvec) for t in ts64]
            fr = sweep(f"tondo_frame_{sx}_{sy}", frame_profile(0.22, 0.14, embed=0.1), ring, [nrm] * len(ring), ups,
                       "stone", stone, closed=True, u_along_path=True)
            fr["lm_grid_aligned"] = True   # bake.layout: the strip unturned, so both ends of its closing cut sample alike
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
    # R13: the pilasters stand on the sill cornice and stop under the top cornice (stage 5: they
    # ran through both, their faces a centimetre or two behind the cornices' faces).
    zp0, zp1 = P.DRUM_WIN_Z[0] - 0.45 + 0.28, P.DRUM_Z1 - 0.55
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
    # R13: the drum's underside lies on the arches' crowns and the pendentives' tops, a few mm
    # above their faces: hidden, it would flicker through them. Removed.
    drum = bpy.data.objects["drum"]
    bm = bmesh.new()
    bm.from_mesh(drum.data)
    mw = drum.matrix_world
    low = [f for f in bm.faces if (mw.to_3x3() @ f.normal).z < -0.99 and abs((mw @ f.calc_center_median()).z - P.DRUM_Z0) < 0.02]
    bmesh.ops.delete(bm, geom=low, context="FACES")
    bm.to_mesh(drum.data)
    bm.free()
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
    """A ring moulding: the profile (r, z) turned round a vertical axis. Round 12: its lightmap is
    one strip along the ring, as finish.sweep's ("lightmap_sweep": u the length round the ring at
    the profile's outer radius, the same for every profile point, so the strip is a rectangle and
    its closing cut at angle 0 a straight column; v the length along the profile). bake.py's grid
    cuts and smart project had broken the drum's rings into short islands whose light stepped at
    every cut."""
    bm = bmesh.new()
    cx, cy = centre
    rings = []
    for kk in range(segments):
        a = 2 * math.pi * kk / segments
        rings.append([bm.verts.new((cx + r * math.cos(a), cy + r * math.sin(a), z)) for r, z in prof_rz])
    n = len(prof_rz)
    uvl = bm.loops.layers.uv.new("lightmap_sweep")
    vs = [0.0]
    for j in range(1, n):
        vs.append(vs[-1] + math.hypot(prof_rz[j][0] - prof_rz[j - 1][0], prof_rz[j][1] - prof_rz[j - 1][1]))
    r_ref = max(r for r, z in prof_rz)

    def u(kk, j):
        return r_ref * 2 * math.pi * kk / segments
    for kk in range(segments):
        a, b = rings[kk], rings[(kk + 1) % segments]
        for j in range(n - 1):
            f = bm.faces.new((a[j], a[j + 1], b[j + 1], b[j]))
            for loop, (k_, j_) in zip(f.loops, ((kk, j), (kk, j + 1), (kk + 1, j + 1), (kk + 1, j))):
                loop[uvl].uv = (u(k_, j_), vs[j_])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ob = _obj(name, bm, kind, mats, smooth_angle=40)
    ob["lm_grid_aligned"] = True       # bake.layout: its strip stays as laid, along the texel rows
    return ob


def drum_cornices(M, ycen, R_IN):
    """Base ring on the pendentives, sill cornice under the windows, cornice under the dome."""
    stone = [M["stone"]]
    _remove("drum_cornice_low", "drum_cornice_high")
    for name, z0, prof_kind in (("drum_base_ring", P.DRUM_Z0, "base"), ("drum_sill", P.DRUM_WIN_Z[0] - 0.45, "sill"),
                                ("drum_top_cornice", P.DRUM_Z1 - 0.55, "top")):
        if prof_kind == "base":
            # R13: no flat underside lying on the arches' crowns (they reach z0). Round 8: a
            # chamfered foot from the drum's face, so no slot under the ring shows the drum's
            # wall in shadow (a dark line looking up).
            pr = Profile(z0, n=4)
            pr.to(0.05, z0 + 0.03).v(0.22).cyma_reversa(0.06, 0.08).h(0.18).v(0.16).cyma_recta(0.08, 0.12)
        elif prof_kind == "sill":
            pr = Profile(z0, n=4)
            pr.cavetto(0.1, 0.1).h(0.06).v(0.12).ovolo(0.06, 0.06)     # R13: 4 cm before the pilasters
        else:
            pr = Profile(z0, n=4)
            pr.h(0.09).v(0.12).ovolo(0.08, 0.08).h(0.17).v(0.18).cyma_recta(0.08, 0.15)   # R13: fillet 9 cm proud
        pts = pr.closed(embed=0.0 if prof_kind == "base" else 0.04)     # the base: no flat foot (R13)
        prof_rz = [(R_IN - p, q) for p, q in pts] + [(R_IN - pts[0][0], pts[0][1])]
        revolve_profile(name, prof_rz, (0, ycen), "stone", stone)


def dome_coffers(M, ycen, R_IN):
    """The dome's inside on the Pantheon's model (designed: the fresco doesn't show it).
    - 28 columns x 5 rings of sunk coffers from a plain band at the springing; each ring is as
      tall as its coffers are wide, so they diminish upwards and stay square (the Pantheon's
      5 x 28 lands at 55 degrees on this dome too).
    - Every coffer steps back three times (two stepped frames and the panel). Its lower side is
      cut wider than its upper side, so the sunk panel rides up and the steps read from below.
    - A plain smooth band from the top ring to a moulded ring round the oculus.
    - One sheet replaces the shell's inner surface (the shell keeps only its outside): nothing
      lies behind the coffers (R13), and the ribs are the shell itself, with no slits.
    The oculus, the springing and the radii are unchanged (web/src/data/dome.ts)."""
    drum_cornices(M, ycen, R_IN)
    zc = P.DRUM_Z1
    cols, rings = P.DOME_COFFER_COUNT, P.DOME_COFFER_RINGS
    R = R_IN
    centre = Vector((0, ycen, zc))

    def S(th, ph, r=R):
        return centre + Vector((r * math.cos(ph) * math.cos(th), r * math.cos(ph) * math.sin(th), r * math.sin(ph)))
    # Ring boundaries: square cells (ring height = column width at the ring's middle).
    dth = 2 * math.pi / cols
    phis = [P.DOME_BASE_BAND]
    for _ in range(rings):
        a = phis[-1]
        h = dth * math.cos(a + dth * math.cos(a) / 2)
        phis.append(a + h)
    ph_rim = math.acos(P.OCULUS_RIM_R / R)
    rib = P.DOME_RIB                                   # rib width, fraction of a cell
    side_s, up_s, low_s = P.DOME_STEP_INSETS           # per step, fractions of the cell
    sub = 4                                            # segments along each cell edge
    bm = bmesh.new()
    kinds = []                                         # material slot per face
    vcache = {}

    def V(th, ph, r):
        key = (round(th, 7), round(ph, 7), round(r, 6))
        v = vcache.get(key)
        if v is None:
            v = vcache[key] = bm.verts.new(S(th, ph, r))
        return v

    def loop(t0, t1, p0, p1, r):
        """Closed loop round a (theta, phi) rectangle at radius r: sub points per side."""
        pts = []
        for i in range(sub):
            pts.append((t0 + (t1 - t0) * i / sub, p0))
        for i in range(sub):
            pts.append((t1, p0 + (p1 - p0) * i / sub))
        for i in range(sub):
            pts.append((t1 - (t1 - t0) * i / sub, p1))
        for i in range(sub):
            pts.append((t0, p1 - (p1 - p0) * i / sub))
        return [V(t, p, r) for t, p in pts]

    def strip(la, lb, kind, cc=None):
        n = len(la)
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((la[i], la[j], lb[j], lb[i]))
            kinds.append((kind, cc))

    def grid(t0, t1, p0, p1, r, kind):
        for i in range(sub):
            for j in range(sub):
                ta, tb = t0 + (t1 - t0) * i / sub, t0 + (t1 - t0) * (i + 1) / sub
                pa, pb = p0 + (p1 - p0) * j / sub, p0 + (p1 - p0) * (j + 1) / sub
                bm.faces.new((V(ta, pa, r), V(tb, pa, r), V(tb, pb, r), V(ta, pb, r)))
                kinds.append((kind, None))
    RIB, RISER, TREAD, PANEL, BAND = range(5)
    for i in range(rings):
        p0, p1 = phis[i], phis[i + 1]
        hp = p1 - p0
        depth = P.DOME_STEP_DEPTH * (R * math.cos(p0) * dth)    # per step, scaled with the cell
        for j in range(cols):
            t0 = j * dth
            t1 = t0 + dth
            outer = loop(t0, t1, p0, p1, R)
            # the cell's opening: half a rib in from each side
            c = [(t0 + rib * dth / 2, t1 - rib * dth / 2, p0 + rib * hp / 2, p1 - rib * hp / 2)]
            for k in range(1, 3):
                a0, a1, b0, b1 = c[-1]
                c.append((a0 + side_s * dth, a1 - side_s * dth, b0 + low_s * hp, b1 - up_s * hp))
            strip(outer, loop(*c[0], R), RIB)
            r_prev = R
            for k in range(3):
                r_k = R + depth * (k + 1)
                a0, a1, b0, b1 = c[k]
                strip(loop(*c[k], r_prev), loop(*c[k], r_k), RISER, S((a0 + a1) / 2, (b0 + b1) / 2, (r_prev + r_k) / 2))
                if k < 2:
                    strip(loop(*c[k], r_k), loop(*c[k + 1], r_k), TREAD)
                r_prev = r_k
            grid(*c[2], R + depth * 3, PANEL)
    # Plain bands: from the springing to the first ring, from the top ring to the oculus' ring.
    for pa, pb, nseg in ((0.0, phis[0], 1), (phis[-1], ph_rim, 8)):
        for j in range(cols * sub):
            ta, tb = j * dth / sub, (j + 1) * dth / sub
            for q in range(nseg):
                qa, qb = pa + (pb - pa) * q / nseg, pa + (pb - pa) * (q + 1) / nseg
                bm.faces.new((V(ta, qa, R), V(tb, qa, R), V(tb, qb, R), V(ta, qb, R)))
                kinds.append((BAND, None))
    bm.faces.index_update()
    bm.normal_update()
    for f in bm.faces:
        kind, cc = kinds[f.index]
        # risers look towards their cell's middle; everything else into the dome
        target = (cc if kind == RISER else centre) - f.calc_center_median()
        if f.normal.dot(target) < 0:
            f.normal_flip()
        f.material_index = kind
    ob = _obj("dome_coffers", bm, "vault_fine",
              [M["vault_rib"], M["coffer_riser"], M["coffer_tread"], M["coffer"], M["stucco_drum"]])
    # The shell keeps only its outside: its inner surface is the sheet above.
    dome = bpy.data.objects["dome"]
    bm = bmesh.new()
    bm.from_mesh(dome.data)
    inner = [f for f in bm.faces if (f.calc_center_median() - centre).length < R + 0.3]
    bmesh.ops.delete(bm, geom=inner, context="FACES")
    bm.to_mesh(dome.data)
    bm.free()
    set_material("dome", M["stucco_drum"])
    # The oculus' ring: a fascia hanging from the smooth band, a flat soffit and a torus rolling
    # into the opening; the opening's reveal goes up to the shell's outside.
    r_oc, r_rim = P.OCULUS_R, P.OCULUS_RIM_R
    z_rim = zc + math.sqrt(R ** 2 - r_rim ** 2)
    R_OUT = R + 0.6
    phi_oc = math.acos(r_oc / R)
    z_top = zc + R_OUT * math.sin(phi_oc)
    r_top = R_OUT * math.cos(phi_oc)
    zb = z_rim - 0.07
    prof = [(r_rim, z_rim), (r_rim, zb), (r_oc + 0.05, zb)]
    for t in np.linspace(-math.pi / 2, -math.pi, 7)[1:]:
        prof.append((r_oc + 0.05 + 0.05 * math.cos(t), zb + 0.05 + 0.05 * math.sin(t)))
    prof += [(r_oc, z_top), (r_top, z_top)]
    revolve_profile("dome_oculus_rim", prof + [prof[0]], (0, ycen), "stone", [M["stone"]], segments=cols * sub)
    return ob


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
        tg = box(f"triglyph_{i}", x - tw / 2, x + tw / 2, face - 0.07, face, a1 + 0.02, f1 - 0.02, "stone", stone)
        tg.data.materials.append(M["groove"])
        for g in (-1, 0, 1):   # the three bars' grooves: slots 1 cm deep cut into it (R13), dark faces
            cut = cutter_box(x + g * tw / 3 - 0.018, x + g * tw / 3 + 0.018, face - 0.08, face - 0.06, a1 + 0.1, f1 - 0.1)
            cut.data.materials.append(M["groove"])
            boolean(tg, cut)
    # Door: archivolt (two fasciae and a cyma) no wider than the impost, imposts, pilasters.
    width = X0 - 0.03
    k = width / 0.42
    ar = Profile(0.0, n=4)
    # Projection no more than the impost's top (0.06 m), so the bands land on it (R3).
    ar.h(0.03).v(0.15 * k).h(0.008).v(0.17 * k).cyma_reversa(0.012, 0.06 * k).h(0.004).v(0.04 * k)
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


# ================================================================ stage 5: the opening arch
def eye_point(u, v, y):
    """The point at depth y that Raphael's eye sees at scan px (u, v)."""
    k = y / P.F_PX
    return Vector(((u - P.CX) * k, y, P.EYE_Z - (v - P.CY) * k))


def _eye_strip(name, outer, inner, y0, y1, kind, mats, side_mat=None, inner_side=True):
    """A solid between two px polylines (outer and inner edge, same length), from depth y0 to y1:
    every edge runs along a sight line, so from Raphael's eye only its front shows. With side_mat,
    every face but the front takes it (the steps' sides read as plain stone edges as the visitor
    walks in, instead of one row of the front's tile stretched across them)."""
    bm = bmesh.new()
    fo = [bm.verts.new(eye_point(u, v, y0)) for u, v in outer]
    fi = [bm.verts.new(eye_point(u, v, y0)) for u, v in inner]
    bo = [bm.verts.new(eye_point(u, v, y1)) for u, v in outer]
    bi = [bm.verts.new(eye_point(u, v, y1)) for u, v in inner]
    n = len(outer)
    for i in range(n - 1):
        j = i + 1
        bm.faces.new((fo[i], fo[j], fi[j], fi[i]))     # front
        bm.faces.new((bo[i], bi[i], bi[j], bo[j]))     # back
        bm.faces.new((fo[i], bo[i], bo[j], fo[j]))     # outer side
        if inner_side:
            bm.faces.new((fi[i], fi[j], bi[j], bi[i]))     # inner side
    bm.faces.new((fo[0], fi[0], bi[0], bo[0]))
    bm.faces.new((fo[-1], bo[-1], bi[-1], fi[-1]))
    if not inner_side:                                 # open: wind it so the front faces -y
        bm.normal_update()
        bm.faces.ensure_lookup_table()
        if bm.faces[0].normal.y > 0:
            bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
        bm.normal_update()
    if side_mat is not None:
        front = set(fo + fi)
        for f in bm.faces:
            f.material_index = 0 if all(v in front for v in f.verts) else 1
        mats = list(mats) + [side_mat]
    if inner_side:
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return _obj(name, bm, kind, mats)


def _arc_px(r, v_end, n):
    """n points (n odd: one on the crown) on the arch circle of radius r px, from the left end at
    height v_end to the right one."""
    cu, cv = P.ARCH_C
    t0 = math.asin((cv - v_end) / r)
    ts = np.linspace(math.pi - t0, t0, n)
    return [(cu + r * math.cos(t), cv - r * math.sin(t)) for t in ts]


def _band_material():
    m = bpy.data.materials.get("arch_band") or bpy.data.materials.new("arch_band")
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    lin = [((c / 255 + 0.055) / 1.055) ** 2.4 for c in P.ARCH_COLOURS["gold"]]
    dark = [((c / 255 + 0.055) / 1.055) ** 2.4 for c in P.ARCH_COLOURS["ground"]]
    bsdf.inputs["Base Color"].default_value = (*[(a + b) / 2 for a, b in zip(lin, dark)], 1)
    bsdf.inputs["Roughness"].default_value = 0.8
    m["detail"], m["tile"] = "arch_band", [1.0, 1.0]
    return m


def plan_loop(pts):
    """Mitred outward frame round a closed plan polygon (x, y): points, outward vectors scaled for
    the mitre at every corner, up vectors (finish.plan_path for a closed run)."""
    P2 = [Vector((x, y, 0.0)) for x, y in pts]
    n = len(P2)
    area = sum(P2[i].x * P2[(i + 1) % n].y - P2[(i + 1) % n].x * P2[i].y for i in range(n))
    sgn = 1 if area > 0 else -1                 # counter-clockwise: the outside is on the right
    segs = [(P2[(i + 1) % n] - P2[i]).normalized() for i in range(n)]
    nrm = [Vector((t.y, -t.x, 0.0)) * sgn for t in segs]
    outs = [(nrm[i - 1] + nrm[i]) / (1.0 + nrm[i - 1].dot(nrm[i])) for i in range(n)]
    return P2, outs, [Vector((0, 0, 1))] * n


def opening_arch(M):
    """The fresco's lunette frame as the hall's opening arch, in front of Raphael's eye.
    - Face plane y = ARCH_Y (4.75 m), where the fresco's bottom edge meets the floor; every member
      is placed from scan px at its own depth (eye_point), so its edges land on the painted ones.
    - The meander (inner plain band, dark lines, meander) is on the intrados, the soffit seen in
      perspective as in the fresco (ARCH_DEPTH); the archivolt's light fillet 5 cm proud; the outer
      bands (grey with two bead strings, egg-and-dart, red) 3 cm proud. All are textured by the
      vector-drawn band tile (make_detail.py: arch_band, and arch_soffit on the intrados).
    - Arch piers (Maria, from the banners' close views): a thin front wall (ARCH_DEPTH), its
      opening cut square through it on the old face outline; one cornice at the springing with
      the impost's profile, round each half of the wall; square pilasters on plinths.
    - Joint rules: archivolt, bands, the vault ornament's band and borders land on the cornice
      (R4); the cornice is a closed loop, mitred at every corner (R1, R2); pilasters stand on
      plinths under it (R10).
    - Plain stone pilasters where the painted ones stand (no grotesques); the wall round the arch
      is plain stone (designed). None of it casts shadows: in the fresco the light still comes in."""
    stone = [M["stone"]]
    band = [_band_material()]
    Y, D = P.ARCH_Y, P.ARCH_DEPTH
    R = P.ARCH_R
    cu, cv = P.ARCH_C
    vs = P.ARCH_SPRING_V
    n = 193
    objs = []
    # Archivolt and outer bands: their ends go 1.5 px (3 mm) below the springing into the impost.
    ve = vs + 1.5
    # Their backs lie on the wall's face, not inside it: an embedded strip would lie on the
    # soffit's plane, coplanar with it (R13).
    # The archivolt's front keeps the fillet only (1717-1733); the meander is on the intrados.
    objs.append(_eye_strip("opening_archivolt", _arc_px(R["fillet"], ve, n), _arc_px(R["meander"][1], ve, n),
                           Y - P.ARCH_PROJ, Y, "stone", band, side_mat=M["stone"]))
    # (the bands' inner side lies on the fillet's outer side, inside it: not built, R13)
    objs.append(_eye_strip("opening_archivolt_bands", _arc_px(R["outer"], ve, n), _arc_px(R["fillet"], ve, n),
                           Y - P.ARCH_BAND_PROJ, Y, "stone", band, side_mat=M["stone"], inner_side=False))
    # The front wall, D thick, and the opening (Maria: the meander on the intrados, resting on the
    # piers as in the fresco). The intrados: a cylinder of the meander's outer radius at the face
    # (1717 px), its axis the sight line through the arch's centre, D deep: seen from Raphael's eye
    # its back edge lands on the band's inner edge (1619 px) all round, so the soffit shows exactly
    # the painted band. It ends on the cornice's top (the springing, zs); below, the jambs go
    # straight down from where it meets zs at each depth (they splay < 1 deg; square in practice),
    # one surface with it along the springing line. The cut is the wall's own: no stacked faces.
    W, H = P.ARCH_WALL
    wall = box("opening_wall", -W, W, Y, Y + D, 0.0, H, "stone", stone)
    zs = eye_point(cu, vs, Y).z
    Rw = R["meander"][1] * Y / P.F_PX                                  # world radius of the intrados
    centre = lambda y: eye_point(cu, cv, y)                            # noqa: E731  (on the sight line)
    z_low = -0.5

    def outline(y):
        c = centre(y)
        half = math.sqrt(Rw ** 2 - (zs - c.z) ** 2)                    # where the circle meets zs
        t0 = math.atan2(zs - c.z, half)
        ts = np.linspace(math.pi - t0, t0, n)
        pts = [Vector((c.x - half, y, z_low))]
        pts += [Vector((c.x + Rw * math.cos(t), y, c.z + Rw * math.sin(t))) for t in ts]
        pts += [Vector((c.x + half, y, z_low))]
        return pts
    boolean(wall, cutter_prism(outline(Y - 0.3), outline(Y + D + 0.3)))
    # Split the opening's faces off the wall: the intrados (above zs) takes the band tile, mapped
    # from Raphael's eye so it lands on the fresco's band (bake.arch_uvs); its light is the face's
    # (finish.light, tools/lightmap_post.py); the jambs are plain stone, opening_reveal.
    bm = bmesh.new()
    bm.from_mesh(wall.data)
    xa = centre(Y).x
    cut = [f for f in bm.faces if abs(f.normal.y) < 0.5 and Y - 1e-4 < f.calc_center_median().y < Y + D + 1e-4
           and abs(f.calc_center_median().x - xa) < Rw + 0.02 and f.calc_center_median().z < centre(Y).z + Rw + 0.02
           and f.calc_center_median().z > -0.4]
    soffit = [f for f in cut if f.calc_center_median().z > zs + 1e-4]
    jambs = [f for f in cut if f.calc_center_median().z <= zs + 1e-4]

    def split(faces, name, mats):
        nb = bmesh.new()
        vmap = {}
        for f in faces:
            vv = []
            for v in f.verts:
                if v not in vmap:
                    vmap[v] = nb.verts.new(v.co)
                vv.append(vmap[v])
            nb.faces.new(vv)
        nb.normal_update()
        for f in nb.faces:                     # they face the opening's axis
            c = f.calc_center_median()
            ax = centre(c.y)
            if f.normal.x * (ax.x - c.x) + f.normal.z * (ax.z - c.z) < 0:
                f.normal_flip()
        return _obj(name, nb, "stone", mats)
    intrados = split(soffit, "opening_archivolt_intrados", band)   # the band tile, mapped from the eye (bake.arch_uvs)
    reveal = split(jambs, "opening_reveal", stone)
    # One continuous surface for the paint and the light (Maria's "joining edges"): the cut's
    # faces each ran the full depth, so the band, mapped from the eye per vertex, was bent
    # differently on the two triangles of each (v is projective in depth), and the bake's grid
    # cut (split_long) broke it into islands whose light and pattern stepped at the cut. Here:
    # - every front-to-back edge of the intrados and the jambs is divided into 8 (the same
    #   points on both, so no T-junction at the springing): the paint follows the eye's mapping
    #   to within a fraction of a scan px;
    # - the intrados's lightmap is one strip along the whole arc ("lightmap_sweep": u the arc
    #   length, v the depth; bake.unwrap_one lays it out as is, uncut).
    rows = 8
    for ob in (intrados, reveal):
        gb = bmesh.new()
        gb.from_mesh(ob.data)
        long = [e for e in gb.edges if abs(e.verts[0].co.y - e.verts[1].co.y) > D * 0.5]
        bmesh.ops.subdivide_edges(gb, edges=long, cuts=rows - 1, use_grid_fill=True)
        gb.to_mesh(ob.data)
        gb.free()
    me = intrados.data
    uvl = me.uv_layers.new(name="lightmap_sweep")
    for loop in me.loops:
        q = me.vertices[loop.vertex_index].co
        c = centre(q.y)
        th = math.atan2(q.z - c.z, q.x - c.x)
        uvl.data[loop.index].uv = (Rw * (math.pi - th), q.y - Y)
    bmesh.ops.delete(bm, geom=cut, context="FACES")
    bm.to_mesh(wall.data)
    bm.free()
    objs += [wall, intrados, reveal]
    arc = _arc_px(R["meander"][1], vs, n)
    # Pilasters on the pier's front, as the fresco's wide panel (their front inner edge projects on
    # the meander's outer edge: 1.8 cm proud of the jamb face, which is the fresco's narrow panel),
    # plinths (3 cm on the front, 2 cm each side), and one cornice at the springing, round the pier
    # at the new depth: front, the D-deep jamb, back; the intrados lands on its top.
    k = Y / P.F_PX
    pw_px = P.ARCH_PILASTER_W / k
    zi = zs - P.ARCH_IMPOST_H
    imp = Profile(zi, n=4)
    imp.h(P.ARCH_PILASTER_D + 0.012).v(0.05).cyma_reversa(0.025, 0.035).h(0.012)
    imp.v(zs - imp.q)
    imp = imp.closed()
    yf = Y - P.ARCH_PILASTER_D
    yp = yf - 0.03
    for side in (-1, 1):
        uj = arc[0][0] if side < 0 else arc[-1][0]                  # jamb, px
        uo = uj + side * pw_px
        xi, xo_ = eye_point(uj, vs, yf).x, eye_point(uo, vs, yf).x
        objs.append(box(f"opening_pilaster_{side}", xi, xo_, yf, Y, 0.15, zi, "stone", stone))
        pi_, po_ = xi - side * 0.02, xo_ + side * 0.02
        objs.append(box(f"opening_pilaster_base_{side}", pi_, po_, yp, Y, -0.01, 0.15, "stone", stone))
        # A. The cornice: the impost's profile run round this half of the thin wall at the
        # springing, front, the opening's square side, back and the wall's far end: one closed,
        # mitred loop, no ends (R1); everything at the springing lands on it (R4).
        def jamb_x(y):
            c = centre(y)
            return c.x + side * math.sqrt(Rw ** 2 - (zs - c.z) ** 2)
        loop = [(side * W, Y), (jamb_x(Y), Y), (jamb_x(Y + D), Y + D), (side * W, Y + D)]
        objs.append(sweep(f"opening_impost_{side}", imp, *plan_loop(loop), "stone", stone, closed=True))
    for ob in objs:
        ob.visible_shadow = False
    # The wall above 9 m, to the nave's crown (Maria, 2026-11-23: "taller"): an open box standing
    # on the wall's top face, which closes it (no face on that face, R13). It is seen by the camera
    # only: no shadow, and no sky hidden from the hall's surfaces nor light bounced into them, so
    # the hall keeps the light it was baked with under the 9 m wall. It takes the sun as the wall
    # below does, and bakes in its own group ("walltop": the front group's atlas keeps its layout).
    top = _box_bm(-W, W, Y, Y + D, H, P.ARCH_WALL_TOP)
    bmesh.ops.delete(top, geom=[f for f in top.faces if f.normal.z < -0.99], context="FACES_ONLY")
    upper = _obj("opening_wall_top", top, "stone", stone)
    _camera_only(upper)
    objs.append(upper)
    # A moulded band across the whole wall at the old top (Maria's choice, 2026-11-23): the
    # springing cornice's profile, its 12 cm centred on 9 m, so it covers the joint between the
    # wall and the wall top (their lightmaps meet there); the ribs land on its soffit (R4). It
    # runs round both ends of the wall, mitred, and stops square on the wall's back plane: the
    # ends at the turn limits read as returns. Like the arch's members it casts no shadow.
    zb = H - P.ARCH_IMPOST_H / 2
    band_prof = Profile(zb, n=4)
    band_prof.h(P.ARCH_PILASTER_D + 0.012).v(0.05).cyma_reversa(0.025, 0.035).h(0.012)
    band_prof.v(zb + P.ARCH_IMPOST_H - band_prof.q)
    run = [(-W, Y + D), (-W, Y), (W, Y), (W, Y + D)]
    band_ob = sweep("opening_string_course", band_prof.closed(), *plan_path(run, 1), "stone", stone)
    band_ob.visible_shadow = False
    objs.append(band_ob)
    # The vault ornament round the arch, on the wall and in relief (these cast their shadows).
    objs += vault_relief(M, wall)
    return objs


def _camera_only(ob):
    """Seen by the camera, invisible to every other ray; baked in the wall top's own group."""
    ob.visible_shadow = ob.visible_diffuse = ob.visible_glossy = False
    ob.visible_transmission = ob.visible_volume_scatter = False
    ob["bake_group"] = "walltop"


# ================================================================ the vault ornament in relief
def _wall_pt(x, z, h):
    """Blender point on the front wall's plane (y = ARCH_Y) at (x, z), h metres proud of it."""
    return Vector((x, P.ARCH_Y - h, z))


def _offset_lines(path, profile, side_ref):
    """For a 2D path in the wall plane (x, z) and a closed profile [(t, h)], one polyline per
    profile point: the path offset by t along its mitred normal (the normal that points like
    side_ref(p) at the first vertex)."""
    path = np.asarray(path, float)
    d = np.diff(path, axis=0)
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    nseg = np.stack([-d[:, 1], d[:, 0]], 1)
    if np.dot(nseg[0], side_ref(path[0])) < 0:
        nseg = -nseg
    nv = np.empty_like(path)
    nv[0], nv[-1] = nseg[0], nseg[-1]
    for i in range(1, len(path) - 1):                     # mitre
        m = nseg[i - 1] + nseg[i]
        m /= np.linalg.norm(m)
        nv[i] = m / max(0.2, float(np.dot(m, nseg[i])))
    return [(path + nv * t, h) for t, h in profile]


def _trimmed(line, start=None, end=None, corner=None, n=(40, 40)):
    """A polyline cut where it first satisfies start(p) and where it then first fails end(p)
    (crossings found by bisection), resampled by length into n[0] points, or, with a corner
    vertex index, n[0] up to the corner and n[1] after it: every line of a ribbon gets the same
    count and its corner at the same index, so the quads stay whole."""
    line = [np.asarray(q, float) for q in line]

    def cross(a, b, f):
        lo, hi = 0.0, 1.0
        for _ in range(40):
            mid = (lo + hi) / 2
            if f(a + (b - a) * mid) == f(a):
                lo = mid
            else:
                hi = mid
        return a + (b - a) * hi
    i0 = 0
    pts = []
    if start is not None:
        i0 = next(k for k in range(len(line)) if start(line[k]))
        if i0 > 0:
            pts.append(cross(line[i0 - 1], line[i0], start))
    i1 = len(line)
    if end is not None:
        k = next((k for k in range(i0, len(line)) if not end(line[k])), None)
        if k is not None:
            i1 = k
    body = list(range(i0, i1))
    pts += [line[k] for k in body]
    if i1 < len(line):
        pts.append(cross(line[i1 - 1], line[i1], end))
    pts = np.array(pts)

    def resample(q, m):
        seg = np.linalg.norm(np.diff(q, axis=0), axis=1)
        s = np.concatenate([[0.0], np.cumsum(seg)])
        t = np.linspace(0, s[-1], m)
        return np.stack([np.interp(t, s, q[:, 0]), np.interp(t, s, q[:, 1])], 1)
    if corner is None or corner not in body:
        return resample(pts, n[0])
    c = (1 if (start is not None and i0 > 0) else 0) + body.index(corner)
    return np.concatenate([resample(pts[:c + 1], n[0]), resample(pts[c:], n[1])[1:]])


def _face_out(bm):
    """Wind every face of an open surface standing on the wall so the surface faces out of it:
    one winding throughout (as built), reversed if its frontmost face looks into the wall."""
    front = max(bm.faces, key=lambda f: (-f.calc_center_median().y, f.calc_area()))
    bm.normal_update()
    if front.normal.y > 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
        bm.normal_update()


def _ribbon(name, path, profile, side_ref, mat, start=None, end=None, corner=None, n=(40, 40)):
    """A moulding on the front wall: the open profile [(t, h)] (from the wall, over, back to the
    wall: no face on or in the wall) swept along the 2D path (mitred), each of its lines trimmed
    at the start/end conditions, capped at both ends."""
    lines = [(_trimmed(q, start, end, corner, n), h) for q, h in _offset_lines(path, profile, side_ref)]
    bm = bmesh.new()
    vs = [[bm.verts.new(_wall_pt(x, z, h)) for x, z in q] for q, h in lines]
    nj, ni = len(vs), len(vs[0])
    for j in range(nj - 1):
        a, c = vs[j], vs[j + 1]
        for i in range(ni - 1):
            bm.faces.new((a[i], a[i + 1], c[i + 1], c[i]))
    _face_out(bm)
    mid = np.mean([q for q, h in lines], axis=0)                  # the ribbon's middle line
    for idx, sgn in ((0, -1), (ni - 1, 1)):
        cap = bm.faces.new([vs[j][idx] for j in range(nj)])
        cap.normal_update()
        k = min(max(idx, 1), ni - 1)
        tang = mid[k] - mid[k - 1]
        if (cap.normal.x * tang[0] + cap.normal.z * tang[1]) * sgn < 0:
            cap.normal_flip()
    return _obj(name, bm, "stone", [mat])


def _revolve_on_wall(name, centre, prof, mat, outline=None, n=96):
    """A body of revolution about the axis through centre (x, z) normal to the wall: the open
    profile [(r, h)] from the axis out to the wall (or to the face it stands on); outline(phi)
    scales r round it (1 = round)."""
    bm = bmesh.new()
    rings = []
    for k in range(n):
        phi = 2 * math.pi * k / n
        s = outline(phi) if outline else 1.0
        rings.append([bm.verts.new(_wall_pt(centre[0] + r * s * math.sin(phi), centre[1] + r * s * math.cos(phi), h))
                      for r, h in prof])
    m = len(prof)
    for k in range(n):
        a, c = rings[k], rings[(k + 1) % n]
        for j in range(m - 1):
            bm.faces.new((a[j], a[j + 1], c[j + 1], c[j]))
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-7)    # the axis: one vertex
    bmesh.ops.dissolve_degenerate(bm, dist=1e-7, edges=bm.edges[:])
    _face_out(bm)
    return _obj(name, bm, "stone", [mat])


def vault_relief(M, wall):
    """The vault ornament made part of the front wall (first-arch idea 1, Maria: "too 2D"):
    - the wall's face round the arch takes the ornament as its detail tile ("vault_front",
      tools/vault_ornament.py via make_detail.py), mapped once over it (bake "uv_origin"), so the
      bake's light falls across the paint and the marble's grain runs through it;
    - in relief, stucco on the wall (painted by the same tile on their fronts; their sides take
      the tile's top strip, white, or gold for the rosettes, through bake "side_uv"):
      the pale ribs, 4.6 cm proud with a cable torus on the axis; the roundels, a disc 4.5 cm
      proud under a rounded rim, each with a raised gilded rosette 4.7 cm proud of it; a thin
      frame round each blue field, 3.6 cm proud. Every front face stands >= 3 cm before the face
      it covers (R13: 2 cm in the web); they stand on the wall with no face of their own on or in
      it; ribs and borders stop 1 mm off the roundels' sides and run out at the wall's top and
      end (R1). The borders along the ribs
      rake with them (not "frames": the audit wants frames level or plumb).
    The wall's face round the arch is its own object, "vault_wall", and every relief starts
    "vault_": params.BAKE_DENSITY_SCALE gives them a denser lightmap, and bake.face_factor leaves
    Raphael's right-side shade off them (it is for the hall's soffits, not the front wall).
    Design numbers: vault_geom.py (web metres; / SCALE for Blender)."""
    import vault_geom as G
    white = M["stone"].copy()
    white.name = "vault_front"
    white["detail"], white["tile"], white["uv_origin"] = "vault_front", list(G.TILE_B), list(G.ORIGIN_B)
    white["tint"] = [1.0, 1.0, 1.0]
    white["side_uv"] = list(G.side_uv()[0])
    gold = white.copy()
    gold.name = "vault_front_gold"
    gold["side_uv"] = list(G.side_uv()[1])
    b = G.b
    xc, zc = b(G.XC), b(G.YC)
    x0, x1 = b(G.XC - G.HW), b(G.XC + G.HW)
    z0, z1 = b(G.Y0), b(G.Y1)
    # 1. The wall's face round the ornament: cut on the tile's edges (the paint's extent) and on
    # lines that every relief covers, given the ornament where the tile reaches.
    # "vault_wall" (the face with the denser lightmap) is bounded by reliefs all round, so no edge
    # of it shows on bare wall (Maria, 2026-11-23: "these short out-of-the-blue lines have to
    # disappear": the tile's rectangle ended on the plain wall above each field, beside the rib,
    # and the two lightmaps met there along a soft line). It takes the fields up to their
    # vertical frames (cut along the frame's middle) and the whole wall between the ribs (cut
    # along each rib's axis) up to the band at 9 m; the plain wall outside the ribs and the
    # fields stays the wall's. Inside the tile it is painted ("vault_front"); between the ribs
    # past the tile it is plain stone, the tile's ground being that stone in phase, so the grain
    # runs on and only the paint stops where the tile does.
    fw = b(G.FRAME_W)
    xcut = {side: b(G.XC + side * G.FIELD_EDGE) - side * fw / 2 for side in (-1, 1)}
    cuts = [((x0, 0, 0), (1, 0, 0)), ((x1, 0, 0), (1, 0, 0)), ((0, 0, z0), (0, 0, 1)), ((0, 0, z1), (0, 0, 1)),
            ((xcut[-1], 0, 0), (1, 0, 0)), ((xcut[1], 0, 0), (1, 0, 0))]
    for side in (-1, 1):
        _, n_up = G.rib_axes(side)
        cuts.append(((xc, 0, zc), (n_up[0], 0, n_up[1])))
    bm = bmesh.new()
    bm.from_mesh(wall.data)
    for co, no in cuts:
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no)
    bm.to_mesh(wall.data)
    bm.free()

    def ornament_face(c):
        """The wall face's polygon centre c (Blender) lies in vault_wall's outline."""
        if c.z <= z0:
            return False
        t = {side: G.rib_strip_st(side, c.x * G.S, c.z * G.S)[1] for side in (-1, 1)}
        if t[-1] > 0 and t[1] > 0:
            return True                                                    # between the ribs
        return (t[-1] < 0 and c.x > xcut[-1]) or (t[1] < 0 and c.x < xcut[1])   # a field
    stone_mat = M["stone"]
    # That face becomes an object of its own, "vault_wall", so the bake gives it a denser lightmap
    # (params.BAKE_DENSITY_SCALE): the reliefs' contact shade and cast shadows on it are a few cm
    # wide, and at the wall's 16 px/m (rough) they smeared into dark stains (Maria: "mold").
    bm = bmesh.new()
    bm.from_mesh(wall.data)
    faces = [f for f in bm.faces if f.normal.y < -0.99 and abs(f.calc_center_median().y - P.ARCH_Y) < 1e-3
             and ornament_face(f.calc_center_median())]
    nb = bmesh.new()
    vmap = {}
    for f in faces:
        vs = []
        for v in f.verts:
            if v not in vmap:
                vmap[v] = nb.verts.new(v.co)
            vs.append(vmap[v])
        nf = nb.faces.new(vs)
        c = f.calc_center_median()
        nf.material_index = 0 if (x0 < c.x < x1 and z0 < c.z < z1) else 1
    bmesh.ops.delete(bm, geom=faces, context="FACES")
    bm.to_mesh(wall.data)
    bm.free()
    vw = _obj("vault_wall", nb, "stone", [white, stone_mat])
    vw.visible_shadow = False                      # as the wall it was cut from
    objs = [vw]
    WALL_TOP = P.ARCH_WALL[1] - P.ARCH_IMPOST_H / 2 - 1e-4   # the band's soffit (finish2.opening_arch), 0.1 mm under it
    rr = b(G.ROUNDEL_R) - 0.005                     # the roundel's disc (5 mm inside the painted ring)
    rib_w, fw = b(G.RIB_W), b(G.FRAME_W)
    for side in (-1, 1):
        e_s, n_up = (np.array(v) for v in G.rib_axes(side))
        rc = np.array([b(c) for c in G.roundel_centre(side)])
        into = lambda p, r=rr + 0.001: np.hypot(*(p - rc)) > r       # noqa: E731  (stops 1 mm off the roundel)
        below_top = lambda p: p[1] < WALL_TOP                         # noqa: E731
        # ribs: a fascia with a chamfer each side and a cable torus on the axis
        hw = rib_w / 2
        tor = [(0.034 * math.cos(a), 0.034 + 0.012 * math.sin(a)) for a in np.linspace(math.pi, 0, 13)]
        prof = [(-hw, 0.0), (-hw, 0.030), (-hw + 0.012, 0.034), (-0.034, 0.034)] + tor[1:-1] + \
               [(0.034, 0.034), (hw - 0.012, 0.034), (hw, 0.030), (hw, 0.0)]
        far = rc + e_s * 12.0
        rib = _ribbon(f"vault_rib_{side}", [rc, far], prof, lambda p: n_up, white, into, below_top)
        # The rib's front past the tile's edge (the paint stops there, and its UVs wrapped round
        # the tile: a white or gold patch where they crossed its top strip, Maria's pale patch):
        # from RIB_SWITCH on, the fronts take the rib's own painted strip ("vault_rib", the same
        # paint and grain as the tile's, continued along the rib; vault_geom.RIB_S0).
        strip = white.copy()
        strip.name = f"vault_rib_strip_{side}"
        for k in ("uv_origin", "side_uv"):
            if k in strip:
                del strip[k]
        strip["detail"], strip["tile"], strip["rib_strip"] = "vault_rib", list(G.RIB_TILE_B), side
        _strip_fronts(rib, side, strip)
        objs.append(rib)
        # the field's frame: a fillet and an ovolo, on the field's side of its edge
        fprof = [(0.0, 0.0), (0.0, 0.030), (0.010, 0.036), (0.022, 0.036),
                 (0.032, 0.034), (fw - 0.004, 0.031), (fw, 0.030), (fw, 0.0)]
        # (a) along the rib's lower edge from the roundel to the field's vertical edge, mitred, and
        # down that edge (fix B: the field closed, 1 cm inside the tile's painted extent) to the
        # cornice at the springing, on which it stands (R4)
        R, ys = b(G.RB), b(G.YS)
        on_cornice = lambda p: p[1] > ys                              # noqa: E731
        xe = b(G.XC + side * G.FIELD_EDGE)
        e0 = rc - n_up * hw
        corner = e0 + e_s * ((xe - e0[0]) / e_s[0])
        edge = [e0, corner, np.array([xe, ys - 0.5])]
        objs.append(_ribbon(f"vault_field_border_rib_{side}", edge, fprof, lambda p: -n_up, white, into, on_cornice,
                            corner=1, n=(24, 24)))
        # (b) along the band's outer edge, down to the cornice
        th_end = math.acos((ys - zc) / R)                              # where the arc meets the springing
        ths = np.linspace(math.radians(G.RIB_DEG), th_end + 0.02, 90)  # from inside the roundel to below it
        arc = [np.array([xc + side * R * math.sin(t), zc + R * math.cos(t)]) for t in ths]
        outward = lambda p: (p - np.array([xc, zc])) / np.hypot(*(p - np.array([xc, zc])))   # noqa: E731
        objs.append(_ribbon(f"vault_field_border_arc_{side}", arc, fprof, outward, white, into, on_cornice, n=(90, 1)))
        # the roundel: disc under a rounded rim
        rim = [(rr - 0.015 + 0.015 * math.cos(a), 0.045 + 0.015 * math.sin(a)) for a in np.linspace(0, math.pi, 10)]
        rprof = ([(0.0, 0.045), (rr - 0.034, 0.045)] + rim[::-1][:-1] + [(rr, 0.045), (rr, 0.0)])
        objs.append(_revolve_on_wall(f"vault_roundel_{side}", rc, rprof, white))
        # the rosette: a gilded boss, its outline the painted rosette's eight petals, domed
        rb = b(G.ROSETTE_R)
        bprof = [(0.0, 0.093), (0.3, 0.092), (0.6, 0.089), (0.85, 0.083), (1.0, 0.075), (1.0, 0.045)]
        bprof = [(r * rb, h) for r, h in bprof]
        bc = np.array([b(c) for c in G.boss_centre(side)])     # on the sight line through the ring's centre
        objs.append(_revolve_on_wall(f"vault_boss_{side}", bc, bprof, gold, outline=G.boss_outline))
    for ob in objs:
        ob["oriented"] = True
    return objs


def _strip_fronts(ob, side, mat):
    """The rib's front faces (those the bake maps flat on the wall: bake.detail_uvs) lying wholly
    past S_SWITCH along the rib take the strip's material; the others keep the tile."""
    import vault_geom as G
    me = ob.data
    me.materials.append(mat)
    mi = len(me.materials) - 1
    e_s, _ = G.rib_axes(side)
    for p in me.polygons:
        n = p.normal
        if not (abs(n.y) >= abs(n.x) and abs(n.y) >= abs(n.z)):
            continue
        s_min = min((me.vertices[v].co.x * G.S - G.XC) * e_s[0] + (me.vertices[v].co.z * G.S - G.YC) * e_s[1]
                    for v in p.vertices)
        if s_min >= G.RIB_SWITCH:
            p.material_index = mi
