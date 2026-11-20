"""Stage 1 finish of the hall (branch hall-look): the nave arm's coffered vault, mouldings,
materials and Raphael's light. build.py builds the grey hall and then calls apply().

Every dimension and colour comes from params.py (section "Stage 1 finish"), with the reading it
came from. renders/hall-stage1/REPORT.md says what is read from the fresco and what is designed.

Geometry conventions as in build.py: X right, Y into the painting, Z up, metres at 100 %.
The vault is built in its development (s = arc length from the crown, y, d = depth outwards) and
wrapped onto the cylinder at the end, so the coffer pattern is drawn flat, as a mason would set it out.
"""
import math
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector

import params as P

HERE = Path(__file__).resolve().parent
TEX = HERE.parent / "textures"

# Workbench / export colours for the new kinds (build.py's GREY covers the old ones).
GREY_FINISH = {
    "stone": (0.90, 0.88, 0.84, 1), "stucco": (0.82, 0.80, 0.76, 1),
    "vault_fine": (0.76, 0.74, 0.70, 1),
}


def _obj(name, bm, kind, mats=(), smooth_angle=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    if smooth_angle is not None:
        me.shade_smooth()
        me.set_sharp_from_angle(angle=math.radians(smooth_angle))
    ob = bpy.data.objects.new(name, me)
    ob.color = GREY_FINISH.get(kind, (0.8, 0.8, 0.8, 1))
    ob["kind"] = kind
    ob["oriented"] = True          # build.py must not recompute these normals
    bpy.context.scene.collection.objects.link(ob)
    return ob


def _remove(*names):
    for n in names:
        ob = bpy.data.objects.get(n)
        if ob is not None:
            bpy.data.objects.remove(ob)


# ================================================================ 2D polygons (development)
def _area(poly):
    return 0.5 * sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]))


def _clip(poly, axis, value, keep_above):
    out = []
    for i, a in enumerate(poly):
        b = poly[(i + 1) % len(poly)]
        ina = a[axis] >= value if keep_above else a[axis] <= value
        inb = b[axis] >= value if keep_above else b[axis] <= value
        if ina:
            out.append(a)
        if ina != inb:
            t = (value - a[axis]) / (b[axis] - a[axis])
            p = [a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])]
            p[axis] = value
            out.append(tuple(p))
    return out


def _dedupe(poly, eps=1e-6):
    out = []
    for p in poly:
        if not out or abs(p[0] - out[-1][0]) + abs(p[1] - out[-1][1]) > eps:
            out.append(p)
    while len(out) > 1 and abs(out[0][0] - out[-1][0]) + abs(out[0][1] - out[-1][1]) <= eps:
        out.pop()
    return out


def _clip_rect(poly, s0, s1, y0, y1):
    for axis, v, above in ((0, s0, True), (0, s1, False), (1, y0, True), (1, y1, False)):
        poly = _clip(poly, axis, v, above)
        if len(poly) < 3:
            return []
    poly = _dedupe(poly)
    return poly if len(poly) >= 3 and _area(poly) > 1e-6 else []


def _inset(poly, t):
    """Mitred inward offset of a convex counter-clockwise polygon; None if an edge would flip."""
    n = len(poly)
    out = []
    for i in range(n):
        (x0, y0), (x1, y1), (x2, y2) = poly[i - 1], poly[i], poly[(i + 1) % n]
        e1 = Vector((x1 - x0, y1 - y0)).normalized()
        e2 = Vector((x2 - x1, y2 - y1)).normalized()
        n1, n2 = Vector((-e1.y, e1.x)), Vector((-e2.y, e2.x))
        k = 1.0 + n1.dot(n2)
        if k < 1e-3:
            return None
        off = (n1 + n2) * (t / k)
        out.append((x1 + off.x, y1 + off.y))
    for i in range(n):
        a0, a1, b0, b1 = poly[i], poly[(i + 1) % n], out[i], out[(i + 1) % n]
        if (a1[0] - a0[0]) * (b1[0] - b0[0]) + (a1[1] - a0[1]) * (b1[1] - b0[1]) <= 1e-8:
            return None
    return out if _area(out) > 1e-4 else None


def tiles(pat, s_lo, s_hi, y_lo, y_hi):
    """Hexagons and lozenges tiled edge to edge (the fresco's vault): hexagon columns run along
    the vault (y) with their points across it (s); each lozenge sits between two columns, its long
    diagonal along y spanning one row. Yields counter-clockwise polygons in (s, y)."""
    D, Pr, b = pat["col"], pat["row"], pat["flat"] / 2
    a, h = D / 2, Pr / 2
    i0, i1 = math.floor((s_lo - pat["s0"]) / D) - 1, math.ceil((s_hi - pat["s0"]) / D) + 1
    j0, j1 = math.floor((y_lo - pat["y_ref"]) / Pr) - 1, math.ceil((y_hi - pat["y_ref"]) / Pr) + 1
    for i in range(i0, i1 + 1):
        for j in range(j0, j1 + 1):
            sc, yc = pat["s0"] + i * D, pat["y_ref"] + j * Pr
            yield [(sc + a, yc), (sc + b, yc + h), (sc - b, yc + h), (sc - a, yc), (sc - b, yc - h), (sc + b, yc - h)]
            yield [(sc + a, yc), (sc + D - b, yc + h), (sc + a, yc + Pr), (sc + b, yc + h)]


# ================================================================ coffered barrel vault
def coffer_sheet(name, radius, spring, y0, y1, field, pat, mats, cut=0.25):
    """Inner surface of a barrel vault (axis along y, springing at x = +-radius, z = spring):
    a field [s0, s1] x [fy0, fy1] of stepped coffers framed by plain bands up to the springing
    and the ends. Material 0 = ribs, bands and treads; 1 = coffer panels; 2 = coffer risers."""
    s_half = radius * math.pi / 2
    fs0, fs1, fy0, fy1 = field
    bm = bmesh.new()
    vmap = {}

    def V(s, y, d):
        key = (round(s, 6), round(y, 6), round(d, 6))
        if key not in vmap:
            vmap[key] = bm.verts.new((s, y, d))
        return vmap[key]

    def add(vs, mat):
        out = []
        for v in vs:
            if not out or v is not out[-1]:
                out.append(v)
        if len(out) > 1 and out[0] is out[-1]:
            out.pop()
        if len(set(out)) >= 3:
            bm.faces.new(out).material_index = mat

    def flat(ccw, d, mat):                     # faces the hall (normal -d)
        add([V(s, y, d) for s, y in reversed(ccw)], mat)

    def ring(outer, d_out, inner, d_in, mat):  # band between two rings of equal vertex count
        n = len(outer)
        for i in range(n):
            j = (i + 1) % n
            add([V(*outer[j], d_out), V(*outer[i], d_out), V(*inner[i], d_in), V(*inner[j], d_in)], mat)

    field_tiles = [c for c in (_clip_rect(t, fs0, fs1, fy0, fy1) for t in tiles(pat, fs0, fs1, fy0, fy1)) if c]
    steps = pat["steps"]
    for poly in field_tiles:
        r = _inset(poly, pat["rib"] / 2)
        if r is None:                          # sliver at the field edge: plain
            flat(poly, 0.0, 0)
            continue
        ring(poly, 0.0, r, 0.0, 0)
        d = 0.0
        for k, (depth, tread) in enumerate(steps):
            low = _inset(r, pat["splay"]) if pat["splay"] else r
            if low is None:
                break
            ring(r, d, low, d + depth, 2)
            d, r = d + depth, low
            if k < len(steps) - 1 and tread:
                nxt = _inset(r, tread)
                if nxt is None:
                    break
                ring(r, d, nxt, d, 3 if len(mats) > 3 else 0)
                r = nxt
        flat(r, d, 1 if d > 0 else 0)

    def on(axis, value):
        return {p for poly in field_tiles for p in poly if abs(p[axis] - value) < 1e-7}

    corners = {(fs0, fy0), (fs1, fy0), (fs0, fy1), (fs1, fy1)}
    if fy0 > y0 + 1e-6:      # near band (over bay 1: the fresco's plain soffit)
        flat(_dedupe([(fs0, y0), (fs1, y0)] + sorted(on(1, fy0) | {(fs0, fy0), (fs1, fy0)}, key=lambda p: -p[0])), 0.0, 0)
    if fy1 < y1 - 1e-6:      # far band
        flat(_dedupe(sorted(on(1, fy1) | {(fs0, fy1), (fs1, fy1)}, key=lambda p: p[0]) + [(fs1, y1), (fs0, y1)]), 0.0, 0)
    left = sorted(on(0, fs0) | {c for c in corners if c[0] == fs0} | {(fs0, y0), (fs0, y1)}, key=lambda p: p[1])
    flat(_dedupe([(-s_half, y0)] + left + [(-s_half, y1)]), 0.0, 0)
    right = sorted(on(0, fs1) | {c for c in corners if c[0] == fs1} | {(fs1, y0), (fs1, y1)}, key=lambda p: -p[1])
    flat(_dedupe([(s_half, y0), (s_half, y1)] + right), 0.0, 0)

    # Every flat face must face the hall (-d); flip the whole sheet if the winding came out reversed.
    bm.normal_update()
    up = sum(1 for f in bm.faces if f.normal.z > 0.5)
    down = sum(1 for f in bm.faces if f.normal.z < -0.5)
    if up > down:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])

    # Cut along constant s so every face stays within `cut` of arc: wraps onto the cylinder cleanly.
    k0, k1 = math.ceil(-s_half / cut), math.floor(s_half / cut)
    for k in range(k0, k1 + 1):
        s = k * cut
        if abs(abs(s) - s_half) > 1e-4:
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-6,
                                   plane_co=(s, 0, 0), plane_no=(1, 0, 0))
    for v in bm.verts:
        s, y, d = v.co
        rr, t = radius + d, s / radius
        v.co = (rr * math.sin(t), y, spring + rr * math.cos(t))
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
    n_coffers = sum(1 for p in field_tiles if _inset(p, pat["rib"] / 2) is not None)
    ob = _obj(name, bm, "vault_fine", mats, smooth_angle=20)
    ob["coffers"] = n_coffers
    return ob


# ================================================================ mouldings
class Profile:
    """A moulding profile drawn from the bottom up: p = projection from the base plane, q = height.
    Elements follow the classical vocabulary (fillet, fascia, ovolo, cavetto, cymas, torus, scotia)."""

    def __init__(self, q0, n=6):
        self.pts, self.n = [(0.0, q0)], n

    @property
    def p(self):
        return self.pts[-1][0]

    @property
    def q(self):
        return self.pts[-1][1]

    def to(self, p, q):
        self.pts.append((p, q))
        return self

    def h(self, dp):
        return self.to(self.p + dp, self.q)

    def v(self, dq):
        return self.to(self.p, self.q + dq)

    def _arc(self, cp, cq, rp, rq, t0, t1):
        for i in range(1, self.n + 1):
            t = t0 + (t1 - t0) * i / self.n
            self.pts.append((cp + rp * math.cos(t), cq + rq * math.sin(t)))
        return self

    def ovolo(self, dp, dq):      # convex quarter round growing outwards as it rises
        return self._arc(self.p, self.q + dq, dp, dq, -math.pi / 2, 0.0)

    def cavetto(self, dp, dq):    # concave quarter growing outwards as it rises
        return self._arc(self.p + dp, self.q, dp, dq, math.pi, math.pi / 2)

    def cyma_recta(self, dp, dq):
        return self.cavetto(dp / 2, dq / 2).ovolo(dp / 2, dq / 2)

    def cyma_reversa(self, dp, dq):
        return self.ovolo(dp / 2, dq / 2).cavetto(dp / 2, dq / 2)

    def torus(self, dq):
        r = dq / 2
        return self._arc(self.p, self.q + r, r, r, -math.pi / 2, math.pi / 2)

    def scotia(self, dq, depth):
        r = dq / 2
        return self._arc(self.p, self.q + r, depth, r, -math.pi / 2, -3 * math.pi / 2)

    def closed(self, embed=0.03):
        """Back to the base plane at the top, then down behind it (embedded in the wall)."""
        pts = list(self.pts)
        top = pts[-1][1]
        pts += [(0.0, top), (-embed, top), (-embed, pts[0][1])]
        out = []
        for p in pts:
            if not out or abs(p[0] - out[-1][0]) + abs(p[1] - out[-1][1]) > 1e-7:
                out.append(p)
        return out


def entablature(z0):
    """Architrave (two fasciae and a taenia), frieze, cornice (bed moulding, corona, cyma recta).
    Heights read on the first pier (fresco u 1265-1350, v 672-860: three nearly equal parts);
    the 0.5 m projection is build.py's cornice reading."""
    pr = Profile(z0)
    pr.h(0.10).v(0.18).h(0.03).v(0.22).cyma_reversa(0.04, 0.07).h(0.015).v(0.05)   # architrave
    pr.h(-0.085).v(0.56)                                                             # frieze
    pr.ovolo(0.07, 0.08).h(0.01).v(0.03).cyma_reversa(0.05, 0.07)                   # bed mouldings
    pr.h(0.19).v(0.24).h(0.01).v(0.02).cyma_recta(0.06, 0.20).h(0.01)               # corona, sima
    pr.v(P.SPRING_Z - pr.q)
    return pr.closed()


def capital(z_top):
    """Doric (Tuscan) pilaster capital, 0.5 m: astragal, necking, annulets, echinus, abacus.
    The fresco shows banded Doric capitals on the piers (u 2480-2600, v 680-850); profile designed."""
    pr = Profile(z_top - 0.50)   # top 3 mm under z_top: no face coplanar with the architrave soffit
    z_top -= 0.003
    pr.torus(0.05).h(0.004).v(0.17).h(0.011)     # necking 4 mm proud: not coplanar with the shaft.v(0.02).h(0.01).v(0.02).ovolo(0.07, 0.09)
    pr.h(0.025).v(0.11).cyma_reversa(0.02, 0.03)
    pr.v(z_top - pr.q)
    return pr.closed()


def attic_base(z0):
    """Attic base, 0.5 m (half the pilaster width): plinth, torus, scotia, torus, apophyge.
    Bramante's vocabulary; the fresco hides the bases behind the figures."""
    pr = Profile(z0 - 0.01)      # sunk 1 cm into the floor: no face coplanar with it
    pr.h(0.14).v(0.16).h(-0.055).torus(0.11).h(-0.01).v(0.015).scotia(0.07, 0.035)
    pr.v(0.015).h(-0.005).torus(0.08)
    pr._arc(pr.p, pr.q + 0.05, 0.06, 0.05, -math.pi / 2, -math.pi)                  # apophyge
    return pr.closed()


def string_course(z0, z1):
    """Small cornice at the facade's string-course height, continued along the nave walls
    (the fresco's recesses carry a lower entablature at the same level, v 668-800 at Y ~18)."""
    pr = Profile(z0)
    pr.h(0.03).v(0.08).cyma_reversa(0.04, 0.06).h(0.06).v(0.12).cyma_recta(0.04, 0.07)
    pr.v(z1 - pr.q)
    return pr.closed()


def archivolt():
    """Two fasciae and a crowning cyma reversa, 0.40 m wide, 0.11 m proud (p = projection off the
    face, q = radial from the intrados). Same scheme as the far door's archivolt in the fresco
    (u 1780-2100, v 1320-1400); widths fitted to the 0.425 m ring the model leaves."""
    pr = Profile(0.0)
    pr.h(0.04).v(0.15).h(0.025).v(0.16).cyma_reversa(0.03, 0.06).h(0.012).v(0.03)
    return pr.closed(embed=0.0)  # its back is the arch face; embedding it would overlap the soffit


def sweep(name, prof, path, outs, ups, kind, mats, closed=False):
    """Sweep a closed profile (p, q) along a path: point = c + out * p + up * q. outs/ups carry the
    mitre (see plan_path / plane_path). closed=True joins the last ring to the first (a frame
    round a rectangle); otherwise both ends are capped with the profile."""
    bm = bmesh.new()
    rings = [[bm.verts.new(c + o * p + u * q) for p, q in prof] for c, o, u in zip(path, outs, ups)]
    n = len(prof)
    pairs = list(zip(rings, rings[1:])) + ([(rings[-1], rings[0])] if closed else [])
    for a, b in pairs:
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i]))
    if not closed:
        bm.faces.new(rings[0])
        bm.faces.new(rings[-1][::-1])
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return _obj(name, bm, kind, mats, smooth_angle=35)


def plan_path(pts, side):
    """Mitred frames along a plan polyline; side = +1 profile on the right of the direction of
    travel, -1 on the left. Returns (points, outward vectors scaled for the mitre, up vectors)."""
    pts = [Vector((x, y, 0.0)) for x, y in pts]
    segs = [(b - a).normalized() for a, b in zip(pts, pts[1:])]
    nrm = [Vector((t.y, -t.x, 0.0)) * side for t in segs]
    outs = [nrm[0]]
    for n1, n2 in zip(nrm, nrm[1:]):
        outs.append((n1 + n2) / (1.0 + n1.dot(n2)))
    outs.append(nrm[-1])
    return pts, outs, [Vector((0, 0, 1))] * len(pts)


def plane_path(pts2d, origin, U, V, side, closed=False):
    """Mitred frame along a polyline drawn in a plane (origin + U*u + V*v): the in-plane offset
    direction ("up" of the profile) is mitred at every corner, as plan_path does for plan runs.
    side = +1: profile on the right of the direction of travel. closed: the polyline is a loop
    (no repeated last point); its first and last corners are mitred too."""
    pts = [Vector(p) for p in pts2d]
    m = len(pts)
    segs = [(pts[(i + 1) % m] - pts[i]).normalized() for i in range(m if closed else m - 1)]
    nrm = [Vector((t.y, -t.x)) * side for t in segs]
    offs = []
    for i in range(m):
        if closed:
            n1, n2 = nrm[i - 1], nrm[i]
        elif i == 0:
            n1 = n2 = nrm[0]
        elif i == m - 1:
            n1 = n2 = nrm[-1]
        else:
            n1, n2 = nrm[i - 1], nrm[i]
        offs.append((n1 + n2) / (1.0 + n1.dot(n2)))
    world = [origin + U * p.x + V * p.y for p in pts]
    ups = [U * o.x + V * o.y for o in offs]
    return world, ups


def arc_points(cu, cv, r, t0, t1, n):
    return [(cu + r * math.cos(t0 + (t1 - t0) * i / n), cv + r * math.sin(t0 + (t1 - t0) * i / n)) for i in range(n + 1)]


# ================================================================ materials
def _lin(rgb):
    return tuple(((c / 255 + 0.055) / 1.055) ** 2.4 if c / 255 > 0.04045 else c / 255 / 12.92 for c in rgb)


def _sock(node, ident, out=False):
    return next(s for s in (node.outputs if out else node.inputs) if s.identifier == ident)


def textured(name, tex, lum_range, c_dark, c_light, scale, rough=(0.55, 0.85), bump=0.15):
    """A CC0 scan used for its pattern only: its luminance blends two colours sampled from the
    fresco (c_dark, c_light; linear albedo). Box projection in object space (no UVs needed)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    N, L = m.node_tree.nodes, m.node_tree.links
    bsdf = N.get("Principled BSDF")
    tc, mp = N.new("ShaderNodeTexCoord"), N.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1 / scale,) * 3
    L.new(tc.outputs["Object"], mp.inputs["Vector"])

    def img(kind, data=False):
        t = N.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(str(TEX / tex / f"{kind}.jpg"), check_existing=True)
        if data:
            t.image.colorspace_settings.name = "Non-Color"
        t.projection, t.projection_blend = "BOX", 0.3
        L.new(mp.outputs["Vector"], t.inputs["Vector"])
        return t

    col, rgh = img("color"), img("rough", True)
    bw = N.new("ShaderNodeRGBToBW")
    L.new(col.outputs["Color"], bw.inputs["Color"])
    mr = N.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = lum_range
    L.new(bw.outputs["Val"], mr.inputs["Value"])
    mix = N.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    _sock(mix, "A_Color").default_value = (*c_dark, 1)
    _sock(mix, "B_Color").default_value = (*c_light, 1)
    L.new(mr.outputs["Result"], _sock(mix, "Factor_Float"))
    L.new(_sock(mix, "Result_Color", True), bsdf.inputs["Base Color"])
    rr = N.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value, rr.inputs["To Max"].default_value = rough
    L.new(rgh.outputs["Color"], rr.inputs["Value"])
    L.new(rr.outputs["Result"], bsdf.inputs["Roughness"])
    bp = N.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = bump
    bp.inputs["Distance"].default_value = 0.002
    L.new(mr.outputs["Result"], bp.inputs["Height"])
    L.new(bp.outputs["Normal"], bsdf.inputs["Normal"])
    m["albedo_dark"], m["albedo_light"] = c_dark, c_light
    # For the web's detail textures (tools/make_detail.py): the scan, its ramp and its tile size.
    m["detail_tex"], m["lum_range"], m["tile"] = tex, list(lum_range), [scale, scale]
    return m


def floor_image():
    """One slab of the hall's floor, designed in the fresco's floor vocabulary (white slabs, rose
    lozenges with a white core, mauve bands; colours sampled from the platform and the lower
    floor). Tiled over the whole platform: seven slabs across the nave, rows on the coffer rows."""
    mx, my = 2 * P.NAVE_HALF_W / P.FLOOR_SLABS_ACROSS, P.COFFER_ROW
    ppm = 120
    W, H = int(mx * ppm), int(my * ppm)
    X, Y = np.meshgrid((np.arange(W) + 0.5) / ppm, (np.arange(H) + 0.5) / ppm)
    du, dv = np.abs(X - mx / 2), np.abs(Y - my / 2)
    band = (mx / 2 - du < P.FLOOR_BAND / 2) | (my / 2 - dv < P.FLOOR_BAND / 2)
    k = P.FLOOR_BAND / 2 + P.FLOOR_MARGIN
    loz = du / (mx / 2 - k) + dv / (my / 2 - k)
    rose = (loz < 1.0) & (loz > P.FLOOR_LOZENGE_CORE)
    c = np.empty((H, W, 4), np.float32)
    c[...] = (*P.ALBEDO["floor_white"], 1)
    c[rose] = (*P.ALBEDO["floor_rose"], 1)
    c[band] = (*P.ALBEDO["floor_band"], 1)
    img = bpy.data.images.new("hall_floor_slab", W, H, alpha=False, float_buffer=True)
    img.colorspace_settings.name = "Linear Rec.709"
    img.pixels.foreach_set(c.ravel())
    img.pack()
    return img, -P.NAVE_HALF_W, P.COFFER_Y_REF - my / 2, mx, my


def floor_material(grey=None):
    img, x0, y0, w, h = floor_image()
    m = bpy.data.materials.new("floor_hall")
    m.use_nodes = True
    N, L = m.node_tree.nodes, m.node_tree.links
    bsdf = N.get("Principled BSDF")
    tc = N.new("ShaderNodeTexCoord")
    mp = N.new("ShaderNodeMapping")
    mp.inputs["Location"].default_value = (-x0 / w, -y0 / h, 0)
    mp.inputs["Scale"].default_value = (1 / w, 1 / h, 1)
    L.new(tc.outputs["Object"], mp.inputs["Vector"])
    t = N.new("ShaderNodeTexImage")
    t.image, t.extension, t.interpolation = img, "REPEAT", "Linear"
    L.new(mp.outputs["Vector"], t.inputs["Vector"])
    # Veining from a CC0 marble scan, +-12 % on the designed colours.
    vm = N.new("ShaderNodeMapping")
    vm.inputs["Scale"].default_value = (1 / 1.6,) * 3
    L.new(tc.outputs["Object"], vm.inputs["Vector"])
    vt = N.new("ShaderNodeTexImage")
    vt.image = bpy.data.images.load(str(TEX / "Marble014" / "color.jpg"), check_existing=True)
    L.new(vm.outputs["Vector"], vt.inputs["Vector"])
    bw = N.new("ShaderNodeRGBToBW")
    L.new(vt.outputs["Color"], bw.inputs["Color"])
    mr = N.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = 0.32, 0.65
    mr.inputs["To Min"].default_value, mr.inputs["To Max"].default_value = 0.88, 1.06
    L.new(bw.outputs["Val"], mr.inputs["Value"])
    mul = N.new("ShaderNodeMix")
    mul.data_type, mul.blend_type = "RGBA", "MULTIPLY"
    _sock(mul, "Factor_Float").default_value = 1.0
    L.new(t.outputs["Color"], _sock(mul, "A_Color"))
    L.new(mr.outputs["Result"], _sock(mul, "B_Color"))
    # Vertical faces (the platform's front = the top riser) take the steps' plain marble colour.
    geo, sep = N.new("ShaderNodeNewGeometry"), N.new("ShaderNodeSeparateXYZ")
    L.new(geo.outputs["Normal"], sep.inputs["Vector"])
    up = N.new("ShaderNodeMath"); up.operation = "GREATER_THAN"; up.inputs[1].default_value = 0.5
    L.new(sep.outputs["Z"], up.inputs[0])
    sel = N.new("ShaderNodeMix"); sel.data_type = "RGBA"
    _sock(sel, "A_Color").default_value = (*P.ALBEDO["step_riser"], 1)
    L.new(up.outputs[0], _sock(sel, "Factor_Float"))
    L.new(_sock(mul, "Result_Color", True), _sock(sel, "B_Color"))
    L.new(_sock(sel, "Result_Color", True), bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.35
    m["detail"], m["tile"], m["origin"] = "floor_hall", [w, h], [x0, y0]
    m["riser_detail"] = "step_riser"           # its vertical faces (the top riser)
    return m


def painted(m, scale, contrast, speckle=0.0):
    """Painted surface on top of a textured() material: large soft mottling (noise, +-contrast)
    and, if speckle > 0, fine dark specks as on the fresco's ribs. Cracks and stains of the
    fresco's surface are deliberately left out."""
    N, L = m.node_tree.nodes, m.node_tree.links
    bsdf = N.get("Principled BSDF")
    src = bsdf.inputs["Base Color"].links[0].from_socket
    tc = N.new("ShaderNodeTexCoord")
    nz = N.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = scale
    nz.inputs["Detail"].default_value = 6.0
    nz.inputs["Roughness"].default_value = 0.6
    L.new(tc.outputs["Object"], nz.inputs["Vector"])
    mr = N.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = 0.3, 0.7
    mr.inputs["To Min"].default_value, mr.inputs["To Max"].default_value = 1 - contrast, 1 + contrast
    L.new(nz.outputs["Fac"], mr.inputs["Value"])
    mul = N.new("ShaderNodeMix")
    mul.data_type, mul.blend_type = "RGBA", "MULTIPLY"
    _sock(mul, "Factor_Float").default_value = 1.0
    L.new(src, _sock(mul, "A_Color"))
    L.new(mr.outputs["Result"], _sock(mul, "B_Color"))
    out = _sock(mul, "Result_Color", True)
    if speckle > 0:
        sp = N.new("ShaderNodeTexNoise")
        sp.inputs["Scale"].default_value = 90.0
        sp.inputs["Detail"].default_value = 2.0
        L.new(tc.outputs["Object"], sp.inputs["Vector"])
        th = N.new("ShaderNodeMapRange")
        th.inputs["From Min"].default_value, th.inputs["From Max"].default_value = 0.62, 0.70
        th.inputs["To Min"].default_value, th.inputs["To Max"].default_value = 1.0, 1.0 - speckle
        L.new(sp.outputs["Fac"], th.inputs["Value"])
        mul2 = N.new("ShaderNodeMix")
        mul2.data_type, mul2.blend_type = "RGBA", "MULTIPLY"
        _sock(mul2, "Factor_Float").default_value = 1.0
        L.new(out, _sock(mul2, "A_Color"))
        L.new(th.outputs["Result"], _sock(mul2, "B_Color"))
        out = _sock(mul2, "Result_Color", True)
    L.new(out, bsdf.inputs["Base Color"])
    m["mottle"] = [scale, contrast, speckle]
    return m


def right_shade(m):
    """Raphael's convention for the right side: its downward faces (cornice soffits) are painted
    much darker than physics gives with the lit left wall bouncing onto them. Multiplies the
    colour of faces with normal Z < -0.5 at X > 0.5 by RIGHT_UNDERSIDE, and of faces turned to -X
    there (the right wall in shade) by RIGHT_WALL. Not physical: the convention sun lights the left
    wall, and its bounce would light the right side far more than Raphael paints it."""
    N, L = m.node_tree.nodes, m.node_tree.links
    bsdf = N.get("Principled BSDF")
    src = bsdf.inputs["Base Color"].links[0].from_socket
    geo = N.new("ShaderNodeNewGeometry")
    sn, sp = N.new("ShaderNodeSeparateXYZ"), N.new("ShaderNodeSeparateXYZ")
    L.new(geo.outputs["Normal"], sn.inputs["Vector"])
    L.new(geo.outputs["Position"], sp.inputs["Vector"])
    down, right, both = N.new("ShaderNodeMath"), N.new("ShaderNodeMath"), N.new("ShaderNodeMath")
    down.operation, right.operation, both.operation = "LESS_THAN", "GREATER_THAN", "MULTIPLY"
    down.inputs[1].default_value, right.inputs[1].default_value = -0.5, 0.5
    L.new(sn.outputs["Z"], down.inputs[0]); L.new(sp.outputs["X"], right.inputs[0])
    L.new(down.outputs[0], both.inputs[0]); L.new(right.outputs[0], both.inputs[1])
    mix = N.new("ShaderNodeMix")
    mix.data_type, mix.blend_type = "RGBA", "MULTIPLY"
    L.new(both.outputs[0], _sock(mix, "Factor_Float"))
    L.new(src, _sock(mix, "A_Color"))
    _sock(mix, "B_Color").default_value = (P.RIGHT_UNDERSIDE,) * 3 + (1,)
    # Faces turned to -X on the right (the right wall, its pilasters' sides): Raphael's shade.
    west, both2 = N.new("ShaderNodeMath"), N.new("ShaderNodeMath")
    west.operation, both2.operation = "LESS_THAN", "MULTIPLY"
    west.inputs[1].default_value = -0.5
    L.new(sn.outputs["X"], west.inputs[0])
    L.new(west.outputs[0], both2.inputs[0]); L.new(right.outputs[0], both2.inputs[1])
    mix2 = N.new("ShaderNodeMix")
    mix2.data_type, mix2.blend_type = "RGBA", "MULTIPLY"
    L.new(both2.outputs[0], _sock(mix2, "Factor_Float"))
    L.new(_sock(mix, "Result_Color", True), _sock(mix2, "A_Color"))
    _sock(mix2, "B_Color").default_value = (*P.RIGHT_WALL, 1)
    L.new(_sock(mix2, "Result_Color", True), bsdf.inputs["Base Color"])
    return m


def risers(m):
    """Steps: vertical faces take the painted riser colour (191,175,162), treads stay white."""
    N, L = m.node_tree.nodes, m.node_tree.links
    bsdf = N.get("Principled BSDF")
    src = bsdf.inputs["Base Color"].links[0].from_socket
    geo, sep = N.new("ShaderNodeNewGeometry"), N.new("ShaderNodeSeparateXYZ")
    L.new(geo.outputs["Normal"], sep.inputs["Vector"])
    up = N.new("ShaderNodeMath"); up.operation = "GREATER_THAN"; up.inputs[1].default_value = 0.5
    L.new(sep.outputs["Z"], up.inputs[0])
    sel = N.new("ShaderNodeMix"); sel.data_type = "RGBA"
    _sock(sel, "A_Color").default_value = (*P.ALBEDO["step_riser"], 1)
    L.new(up.outputs[0], _sock(sel, "Factor_Float"))
    L.new(src, _sock(sel, "B_Color"))
    L.new(_sock(sel, "Result_Color", True), bsdf.inputs["Base Color"])
    return m


def flat(name, rgb, rough=0.8):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    m["detail"], m["tint"] = "flat", list(rgb)
    return m


def materials():
    A = P.ALBEDO
    M = {
        "stucco": textured("stucco", "white_plaster_02", (0.15, 0.34), A["stucco_dark"], A["stucco"], 2.0,
                           rough=(0.75, 0.95), bump=0.10),
        "stone": textured("stone", "Travertine009", (0.51, 0.74), A["stone_dark"], A["stone"], 1.5,
                          rough=(0.55, 0.80), bump=0.12),
        "vault_rib": textured("vault_rib", "white_plaster_02", (0.15, 0.34), A["rib_dark"], A["rib"], 1.5,
                              rough=(0.75, 0.95), bump=0.08),
        "coffer": textured("coffer", "Marble009", (0.0, 0.012), A["coffer_dark"], A["coffer_light"], 0.7,
                           rough=(0.45, 0.75), bump=0.05),
        "coffer_riser": textured("coffer_riser", "Marble009", (0.0, 0.012), A["riser_dark"], A["riser_light"], 0.7,
                                 rough=(0.45, 0.75), bump=0.05),
        "step": textured("step", "Marble014", (0.32, 0.65), A["step_dark"], A["step"], 1.6,
                         rough=(0.35, 0.6), bump=0.05),
        "tondo": flat("tondo", A["stucco"]),
        "groove": flat("groove", tuple(c * 0.35 for c in A["stone"])),
    }
    def scaled(c, f):
        return tuple(min(0.9, a * b) for a, b in zip(c, f))
    M["stucco_far"] = textured("stucco_far", "white_plaster_02", (0.15, 0.34), scaled(A["stucco_dark"], P.FAR),
                               scaled(A["stucco"], P.FAR), 2.0, rough=(0.75, 0.95), bump=0.10)
    M["stone_far"] = textured("stone_far", "Travertine009", (0.51, 0.74), scaled(A["stone_dark"], P.FAR),
                              scaled(A["stone"], P.FAR), 1.5, rough=(0.55, 0.80), bump=0.12)
    M["stucco_drum"] = textured("stucco_drum", "white_plaster_02", (0.15, 0.34), scaled(A["stucco_dark"], P.DRUM),
                                scaled(A["stucco"], P.DRUM), 2.0, rough=(0.75, 0.95), bump=0.10)
    M["stone_facade"] = textured("stone_facade", "Travertine009", (0.51, 0.74), scaled(A["stone_dark"], P.FACADE),
                                 scaled(A["stone"], P.FACADE), 1.5, rough=(0.55, 0.80), bump=0.12)
    M["coffer_tread"] = textured("coffer_tread", "white_plaster_02", (0.15, 0.34), scaled(A["rib_dark"], (P.TREAD,) * 3),
                                 scaled(A["rib"], (P.TREAD,) * 3), 1.5, rough=(0.75, 0.95), bump=0.08)
    risers(M["step"])
    # Painted look (Maria, stage 2): the coffers' marble mottling and the ribs' fine speckle.
    painted(M["coffer"], *P.PAINTED["coffer"])
    painted(M["coffer_riser"], *P.PAINTED["coffer"])
    painted(M["vault_rib"], *P.PAINTED["rib"])
    for key in ("stone", "stone_far", "stone_facade"):
        painted(M[key], *P.PAINTED["stone"])
    for key in ("stucco", "stucco_far", "stucco_drum"):
        painted(M[key], *P.PAINTED["stucco"])
    for key in ("stone", "stucco", "stucco_far", "stone_far", "stucco_drum", "stone_facade"):
        right_shade(M[key])
    # The web (stage 4) draws detail texture x tint x lightmap: materials that differ from another
    # only by a colour factor share its detail texture and carry the factor as a tint.
    detail = {"stucco": ("stucco", None), "stucco_far": ("stucco", P.FAR), "stucco_drum": ("stucco", P.DRUM),
              "stone": ("stone", None), "stone_far": ("stone", P.FAR), "stone_facade": ("stone", P.FACADE),
              "vault_rib": ("rib", None), "coffer": ("coffer", None), "coffer_riser": ("coffer_riser", None),
              "coffer_tread": ("coffer_tread", None), "step": ("step", None)}
    for name, (key, tint) in detail.items():
        M[name]["detail"] = key
        M[name]["tint"] = list(tint) if tint else [1.0, 1.0, 1.0]
        if tint:                                 # the shared texture uses the untinted colours
            base = M[key if key in M else name]
            M[name]["albedo_dark"], M[name]["albedo_light"] = base["albedo_dark"], base["albedo_light"]
    M["step"]["riser_detail"] = "step_riser"
    return M


# ================================================================ build the finished parts
def vault(tag, y0, y1, field_y0, M):
    """Coffered barrel between y0 and y1 (field from field_y0) over a hidden backing shell."""
    NW, SZ = P.NAVE_HALF_W, P.SPRING_Z
    pat = dict(col=P.COFFER_COL, row=P.COFFER_ROW, flat=P.COFFER_FLAT, s0=0.0, y_ref=P.COFFER_Y_REF,
               rib=P.COFFER_RIB, steps=P.COFFER_STEPS, splay=P.COFFER_SPLAY)
    fs = P.COFFER_FIELD_S
    if field_y0 > y0 + 1e-6:                      # plain band before the field: its own object
        coffer_sheet(f"{tag}_vault_band", NW, SZ, y0, field_y0, (-fs, fs, field_y0, field_y0), pat,
                     [M["vault_rib"], M["coffer"], M["coffer_riser"], M["coffer_tread"]])
    coffer_sheet(f"{tag}_vault_coffers", NW, SZ, field_y0, y1, (-fs, fs, field_y0, y1), pat,
                 [M["vault_rib"], M["coffer"], M["coffer_riser"], M["coffer_tread"]])
    back = P.COFFER_BACK
    bm = bmesh.new()
    outer = [(math.cos(t) * (NW + 0.6), SZ + math.sin(t) * (NW + 0.6)) for t in np.linspace(0, math.pi, 73)]
    inner = [(math.cos(t) * (NW + back), SZ + math.sin(t) * (NW + back)) for t in np.linspace(math.pi, 0, 73)]
    f = bm.faces.new([bm.verts.new((x, y0, z)) for x, z in outer + inner])
    ext = bmesh.ops.extrude_face_region(bm, geom=[f])
    bmesh.ops.translate(bm, verts=[e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)], vec=(0, y1 - y0, 0))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    _obj(f"{tag}_vault_backing", bm, "stucco", [M["stucco"]])


def pilaster(tag, side, yc, M, rings=True):
    NW, PZ, SZ = P.NAVE_HALF_W, P.PLATFORM_Z, P.SPRING_Z
    W, D = P.PILASTER_W, P.PILASTER_D
    wx = side * NW
    hand = 1 if side < 0 else -1
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    x0, x1 = sorted((wx, wx - side * D))
    for v in bm.verts:
        v.co = Vector((x0 + (v.co.x + 0.5) * (x1 - x0), yc - W / 2 + (v.co.y + 0.5) * W,
                       PZ + (v.co.z + 0.5) * (SZ - 0.05 - PZ)))   # fills the ressaut behind the entablature
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    _obj(f"{tag}_pilaster_{side}_{yc}", bm, "stone", [M["stone"]])
    if not rings:                       # base and capital come from the continuous runs (wall_runs)
        return
    ring = [(wx + side * 0.03, yc - W / 2), (wx - side * D, yc - W / 2),
            (wx - side * D, yc + W / 2), (wx + side * 0.03, yc + W / 2)]
    for kind, prof in (("base", attic_base(P.PLATFORM_Z)), ("capital", capital(P.ENTABLATURE_Z0))):
        sweep(f"{tag}_pilaster_{kind}_{side}_{yc}", prof, *plan_path(ring, hand), "stone", [M["stone"]])


def _clean(path):
    out = []
    for p in path:
        if not out or abs(p[0] - out[-1][0]) + abs(p[1] - out[-1][1]) > 1e-6:
            out.append(p)
    # drop collinear middle points
    res = [out[0]]
    for i in range(1, len(out) - 1):
        a, b, c = res[-1], out[i], out[i + 1]
        if abs((b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])) > 1e-9:
            res.append(b)
    res.append(out[-1])
    return res


def apply():
    """Replace the grey hall with the finished one (stage 1 + 2). Returns the materials."""
    import finish2
    NW, CH, T = P.NAVE_HALF_W, P.CROSS_HALF, P.WALL_T
    PZ, SZ = P.PLATFORM_Z, P.SPRING_Z
    Y0, Y1 = P.FACADE_Y1, P.NAVE_Y1
    A0, A1 = P.CROSS_Y1 + P.TRANSVERSE_T, P.ARM2_Y1
    W, D = P.PILASTER_W, P.PILASTER_D
    M = materials()
    stone, stucco = [M["stone"]], [M["stucco"]]
    _remove("nave_vault", "arm2_vault", "arch_front",
            *[f"{t}_cornice_{s}" for t in ("nave", "arm2") for s in (-1, 1)],
            *[f"nave_pilaster_{s}_{y}" for s in (-1, 1) for y in P.PILASTERS_Y],
            *[f"arm2_pilaster_{s}_{y}" for s in (-1, 1) for y in P.ARM2_PILASTERS_Y])

    vault("nave", Y0, Y1, P.COFFER_FIELD_Y0, M)
    vault("arm2", A0, A1, A0, M)

    # Front transverse arch: opening enlarged above the springing to take the coffered soffit.
    top = P.DRUM_Z0 + 1.5
    rb = CH + P.COFFER_BACK
    pts = [(-(NW + T), PZ), (-CH, PZ), (-CH, SZ), (-rb, SZ)]
    pts += [(rb * math.cos(t), SZ + rb * math.sin(t)) for t in np.linspace(math.pi, 0, 97)[1:-1]]
    pts += [(rb, SZ), (CH, SZ), (CH, PZ), (NW + T, PZ), (NW + T, top), (-(NW + T), top)]
    bm = bmesh.new()
    f = bm.faces.new([bm.verts.new((x, Y1, z)) for x, z in pts])
    ext = bmesh.ops.extrude_face_region(bm, geom=[f])
    bmesh.ops.translate(bm, verts=[e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)],
                        vec=(0, P.CROSS_Y0 - Y1, 0))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    _obj("arch_front", bm, "stone", stone)
    k = CH / NW                                   # same pattern in angle, so the columns run on
    pat = dict(col=P.COFFER_COL * k, row=P.COFFER_ROW, flat=P.COFFER_FLAT * k, s0=0.0, y_ref=P.COFFER_Y_REF,
               rib=P.COFFER_RIB, steps=P.COFFER_STEPS, splay=P.COFFER_SPLAY)
    fs = P.COFFER_FIELD_S * k
    coffer_sheet("arch_front_soffit", CH, SZ, Y1, P.CROSS_Y0, (-fs, fs, Y1, P.CROSS_Y0), pat,
                 [M["vault_rib"], M["coffer"], M["coffer_riser"], M["coffer_tread"]])

    # Walls: stucco; pilasters; one entablature run per side from the facade front to the end
    # wall, breaking forward over every pilaster and wrapping the crossing piers.
    for name in ("nave_wall_-1", "nave_wall_1", "arm2_wall_-1", "arm2_wall_1"):
        ob = bpy.data.objects.get(name)
        if ob:
            ob.data.materials.clear()
            ob.data.materials.append(M["stucco"])
    for side in (-1, 1):
        for yc in P.PILASTERS_Y:
            pilaster("nave", side, yc, M, rings=False)
        for yc in P.ARM2_PILASTERS_Y:
            pilaster("arm2", side, yc, M, rings=False)

    finish2.bay1(M)
    finish2.recesses(M)
    finish2.facade(M)
    finish2.wall_runs(M)
    finish2.crossing(M)
    finish2.end_wall(M)
    finish2.bosch_base(M)
    finish2.fill_empty_slots(M)
    finish2.opening_arch(M)
    return M


def light(sun, world, raphael=True):
    """Sun where Raphael's light comes from: front right (evidence in params.py and REPORT.md).

    raphael=True reproduces the fresco's convention rather than a closed building's physics:
    Raphael lights the nave from the right as if the right-hand wall, the vault and the facade
    did not stand between it and the sun. The whole left wall is lit down to the crossing, every
    frontal face is lit, the right wall is in shade, and the floor is bright enough to light the
    vault from below. In Cycles that is shadow linking: those big occluders do not block the sun;
    everything else casts its shadows (pilasters, entablature, steps). The vault takes no sun (in
    the fresco it is in half-light, brightest at the crown): it is lit by what bounces into it.
    raphael=False is the physical sun, blocked by everything."""
    az, el = math.radians(P.SUN_AZIMUTH), math.radians(P.SUN_ELEVATION)
    travel = Vector((-math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), -math.sin(el)))
    sun.rotation_euler = travel.to_track_quat("-Z", "Y").to_euler()
    sun.data.energy = P.SUN_STRENGTH
    sun.data.angle = math.radians(P.SUN_ANGLE)
    sun.data.color = P.SUN_COLOR
    # The sky: the fresco's blue where it is seen (camera rays), and as light the warm colour of
    # the fresco's shade (its shaded walls are yellower than its lit ones: no blue skylight there).
    nt = world.node_tree
    bg = nt.nodes.get("Background")
    lp, mix = nt.nodes.new("ShaderNodeLightPath"), nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    _sock(mix, "A_Color").default_value = (*P.SKY_LIGHT, 1)
    _sock(mix, "B_Color").default_value = (*P.SKY, 1)
    nt.links.new(lp.outputs["Is Camera Ray"], _sock(mix, "Factor_Float"))
    nt.links.new(_sock(mix, "Result_Color", True), bg.inputs["Color"])
    bg.inputs["Strength"].default_value = P.SKY_STRENGTH
    world.color = P.SKY
    if not raphael:
        return travel

    def excluded(cname, names):
        c = bpy.data.collections.new(cname)
        for n in dict.fromkeys(names):
            ob = bpy.data.objects.get(n)
            if ob is not None:
                c.objects.link(ob)
        for co in c.collection_objects:
            co.light_linking.link_state = "EXCLUDE"
        return c

    meshes = [ob for ob in bpy.data.objects if ob.type == "MESH" and ob.get("kind") != "painting"]
    vault = [ob.name for ob in meshes if ob.name.startswith(
        ("nave_vault", "arm2_vault", "arch_front_soffit", "arch_back_soffit", "dome"))]
    upper = [ob.name for ob in meshes if ob.name.startswith(("pendentives", "drum", "tondo", "facade", "arch_front",
                                                               "arch_back", "crossing_blind"))]
    floors = ("floor", "platform", "step", "podium", "pedestal", "ground")
    right = [ob.name for ob in meshes if not ob.name.startswith(floors)
             and min((ob.matrix_world @ Vector(c)).x for c in ob.bound_box) > 0.5]
    sun.light_linking.blocker_collection = excluded("sun_not_blocking", vault + upper + right)
    # Nor do the vaults and the faces up under them take the sun; nor the facade's front (painted
    # at 147, darker than the frontal faces deeper in) and the drum (P.NO_SUN).
    no_sun = [ob.name for ob in meshes if ob.name.startswith(P.NO_SUN) and not ob.name.startswith("bay1")]
    sun.light_linking.receiver_collection = excluded(
        "sun_not_received", vault + no_sun + [n for n in upper if n.startswith(("arch_front", "arch_back"))])
    # The vault over bay 1 is painted as bright as a lit wall (191): a bounce card on bay 1's floor
    # standing for the sunlit pavement, lighting only that vault.
    card = bpy.data.lights.new("front_bounce", "AREA")
    card.shape, card.size, card.size_y = "RECTANGLE", 2 * P.NAVE_HALF_W, P.COFFER_FIELD_Y0 - P.FACADE_Y0
    card.energy, card.color = P.FRONT_BOUNCE, (1.0, 0.93, 0.85)
    cob = bpy.data.objects.new("front_bounce", card)
    cob.location = (0, (P.FACADE_Y0 + P.COFFER_FIELD_Y0) / 2, P.PLATFORM_Z + 0.3)
    cob.rotation_euler = (math.pi, 0, 0)          # pointing up
    cob.visible_camera = cob.visible_glossy = False
    bpy.context.scene.collection.objects.link(cob)
    rc = bpy.data.collections.new("front_bounce_receivers")
    rc.objects.link(bpy.data.objects["nave_vault_band"])
    cob.light_linking.receiver_collection = rc
    return travel
