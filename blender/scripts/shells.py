"""Shell (conch) heads for the hall's niches (Maria, decoration round: idea 3 of
renders/deco-ideas on branch deco-ideas). Raphael's niches have plain round heads; the shell is
Bramante's (the Tempietto's niches) and a Roman form. Cream marble, the niche's own material.

A niche is cut as two solids, so the shell is the wall's own surface (no shell laid over a
hollow: nothing stacked, joint rule R13):
- a box from the sill to the springing, as deep as the niche;
- a fluted half-dome above it, hinged at the back of the springing line: its meridians, from the
  hinge out to the rim, are the flutes. The rim is the head's semicircle on the wall face (the
  frame's inner edge, R6); the flutes grow in from it and die out at the hinge.
The corners of the box's top outside the dome's foot stay as a flat ceiling at the springing.
split() then moves each head's faces into an object of its own ("facade_shell_<side>",
"shell_<tag>_<side>"), so the bake can give them a denser lightmap (params.BAKE_DENSITY_SCALE):
the flutes are read by their baked light.

Axes as build.py: X right, Y into the painting, Z up, metres at 100 %.
"""
import math

import bmesh
import bpy
from mathutils import Vector

import params as P

V = Vector((0, 0, 1))


def _link(name, bm):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def _boolean(target, cutter):
    mod = target.modifiers.new("bool", "BOOLEAN")
    mod.operation, mod.solver, mod.object = "DIFFERENCE", "EXACT", cutter
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(target.evaluated_get(dg))
    target.modifiers.clear()
    old = target.data
    target.data = me
    bpy.data.meshes.remove(old)
    bpy.data.objects.remove(cutter)


def _smooth(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def dome_point(c, U, O, a, d, flutes, th, t, groove=None):
    """A point of the fluted half-dome: th round the head (0 at one foot, pi at the other), t from
    the rim (0) to the hinge (pi/2). Channels (f = 0) lie on the smooth quarter-ellipsoid (semi-axes
    a, a, d); the ridges between them stand forward by `groove` of the radius, fading in from the
    rim and out towards the hinge. th = 0 and pi are channels, so the feet lie on the springing."""
    g = P.NICHE_SHELL["groove"] if groove is None else groove
    f = 0.5 - 0.5 * math.cos(2 * flutes * th)
    m = g * f * _smooth(t / (math.pi / 2) / 0.22) * math.cos(t) ** 0.6
    rho = 1.0 - m
    return (c + U * (rho * a * math.cos(th) * math.cos(t)) + V * (rho * a * math.sin(th) * math.cos(t))
            + O * (d * math.sin(t) * (1.0 - 0.5 * m)))


def dome_cutter(c, U, O, a, d, flutes, front=0.2, below=0.002):
    """Closed solid: the fluted half-dome, carried `front` m forward of the wall face, its foot
    `below` m under the springing (it overlaps the box: no coplanar faces between the two cuts)."""
    k = P.NICHE_SHELL["per_flute"]
    nt, nr = k * flutes, P.NICHE_SHELL["rows"]
    bm = bmesh.new()
    drop = lambda p: p - V * below if abs(p.z - c.z) < 1e-6 else p      # noqa: E731
    rows = []
    for j in range(nr):
        t = (math.pi / 2) * j / nr
        rows.append([bm.verts.new(drop(dome_point(c, U, O, a, d, flutes, math.pi * i / nt, t))) for i in range(nt + 1)])
    apex = bm.verts.new(c + O * d - V * below)
    fr = [bm.verts.new(drop(v.co.copy()) - O * front) for v in rows[0]]
    for j in range(nr - 1):
        for i in range(nt):
            bm.faces.new((rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]))
    for i in range(nt):
        bm.faces.new((rows[-1][i], rows[-1][i + 1], apex))
        bm.faces.new((fr[i], fr[i + 1], rows[0][i + 1], rows[0][i]))
    bm.faces.new(fr)                                              # front cap (arch and chord)
    foot = [fr[0]] + [r[0] for r in rows] + [apex] + [r[-1] for r in rows[::-1]] + [fr[-1]]
    bm.faces.new(foot)                                            # under the springing
    return _link("shell_cut", bm)


def box_cutter(c, U, O, a, d, z0, front=0.2):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        x, y, z = v.co
        v.co = c + U * (2 * x * a) + O * (-front + (y + 0.5) * (d + front)) + V * ((z + 0.5) * (c.z - z0) - (c.z - z0))
    return _link("niche_box_cut", bm)


def cut(target, c, U, O, a, d, z0, flutes):
    """Cut a shell-headed niche into `target`: c is the head's centre on the wall face at the
    springing, U along the wall, O into it, a the half width, d the depth, z0 the sill."""
    _boolean(target, box_cutter(c, U, O, a, d, z0))
    _boolean(target, dome_cutter(c, U, O, a, d, flutes))


def niches():
    """Every niche: (wall object, shell object name, head centre, U, O, half width, depth, sill, flutes)."""
    out = []
    a = (P.NICHE_X[1] - P.NICHE_X[0]) / 2
    for side in (-1, 1):
        xc = side * (P.NICHE_X[0] + P.NICHE_X[1]) / 2
        out.append(("facade", f"facade_shell_{side}", Vector((xc, P.FACADE_Y0, P.NICHE_Z[1] - a)), Vector((1, 0, 0)),
                    Vector((0, 1, 0)), a, P.NICHE_DEPTH, P.NICHE_Z[0], P.NICHE_SHELL["flutes_facade"]))
    a = P.BAY1_NICHE_W / 2
    spans = [("nave", "bay1", P.BAY1_NICHE_YC)]
    spans += [("nave", f"nave_r{i}", (r0 + r1) / 2) for i, (r0, r1) in enumerate(P.NAVE_RECESSES)]
    spans += [("arm2", f"arm2_r{i}", (r0 + r1) / 2) for i, (r0, r1) in enumerate(P.ARM2_RECESSES)]
    for side in (-1, 1):
        for wall, tag, yc in spans:
            out.append((f"{wall}_wall_{side}", f"shell_{tag}_{side}", Vector((side * P.RECESS_X, yc, P.BAY1_NICHE_Z[1] - a)),
                        Vector((0, -side, 0)), Vector((side, 0, 0)), a, P.BAY1_NICHE_DEPTH, P.BAY1_NICHE_Z[0],
                        P.NICHE_SHELL["flutes_recess"]))
    return out


def split():
    """Move each niche head's faces (inside the wall, above the springing) out of the wall into
    its own object, keeping materials and normals."""
    made = []
    for wall, name, c, U, O, a, d, z0, flutes in niches():
        ob = bpy.data.objects.get(wall)
        if ob is None:
            continue
        mw = ob.matrix_world
        bm = bmesh.new()
        bm.from_mesh(ob.data)

        def head(f):
            p = mw @ f.calc_center_median()
            r = p - c
            return (r.dot(O) > 5e-4 and p.z > c.z + 5e-4 and abs(r.dot(U)) < a + 0.01
                    and math.hypot(r.dot(U), p.z - c.z) < a + 0.01)
        faces = [f for f in bm.faces if head(f)]
        nb = bmesh.new()
        vmap = {}
        for f in faces:
            vs = []
            for v in f.verts:
                if v not in vmap:
                    vmap[v] = nb.verts.new(mw @ v.co)
                vs.append(vmap[v])
            nf = nb.faces.new(vs)
            nf.material_index = f.material_index
            nf.smooth = True
        bmesh.ops.delete(bm, geom=faces, context="FACES")
        bm.to_mesh(ob.data)
        bm.free()
        me = bpy.data.meshes.new(name)
        nb.to_mesh(me)
        nb.free()
        for m in ob.data.materials:
            me.materials.append(m)
        sh = bpy.data.objects.new(name, me)
        sh["kind"] = "stucco"
        sh["oriented"] = True          # an open surface: keep the wall's outward normals
        sh.color = ob.color
        bpy.context.scene.collection.objects.link(sh)
        made.append(sh)
    return made
