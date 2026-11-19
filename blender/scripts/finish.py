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
                ring(r, d, nxt, d, 0)
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
    pr = Profile(z_top - 0.50)
    pr.torus(0.05).v(0.17).h(0.015).v(0.02).h(0.01).v(0.02).ovolo(0.07, 0.09)
    pr.h(0.025).v(0.11).cyma_reversa(0.02, 0.03)
    pr.v(z_top - pr.q)
    return pr.closed()


def attic_base(z0):
    """Attic base, 0.5 m (half the pilaster width): plinth, torus, scotia, torus, apophyge.
    Bramante's vocabulary; the fresco hides the bases behind the figures."""
    pr = Profile(z0)
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
    return pr.closed()


def sweep(name, prof, path, outs, ups, kind, mats):
    bm = bmesh.new()
    rings = [[bm.verts.new(c + o * p + u * q) for p, q in prof] for c, o, u in zip(path, outs, ups)]
    n = len(prof)
    for a, b in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i]))
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
    return m


def floor_image():
    """The nave floor, designed in the fresco's floor vocabulary (white slabs, rose lozenges,
    mauve bands; colours sampled from the platform and the lower floor). Rows follow the coffer
    rows above, seven slabs across. Returns (image, x0, y0, width, height) in metres."""
    x0, x1 = -P.NAVE_HALF_W, P.NAVE_HALF_W
    y0, y1 = P.FACADE_Y1, P.CROSS_Y0
    ppm = 100
    W, H = int((x1 - x0) * ppm), int((y1 - y0) * ppm)
    xs = x0 + (np.arange(W) + 0.5) / ppm
    ys = y0 + (np.arange(H) + 0.5) / ppm
    X, Y = np.meshgrid(xs, ys)
    mx, my = (x1 - x0) / P.FLOOR_SLABS_ACROSS, P.COFFER_ROW
    u = (X - x0) / mx
    v = (Y - (P.COFFER_Y_REF - my / 2)) / my
    fu, fv = u - np.floor(u) - 0.5, v - np.floor(v) - 0.5            # -0.5..0.5 in the slab
    du, dv = np.abs(fu) * mx, np.abs(fv) * my                          # metres from the slab centre
    band = (mx / 2 - du < P.FLOOR_BAND / 2) | (my / 2 - dv < P.FLOOR_BAND / 2)
    k = P.FLOOR_BAND / 2 + P.FLOOR_MARGIN
    loz = du / (mx / 2 - k) + dv / (my / 2 - k)
    rose = (loz < 1.0) & (loz > P.FLOOR_LOZENGE_CORE)                 # rose lozenge, white core
    edge = (X - x0 < P.FLOOR_BAND) | (x1 - X < P.FLOOR_BAND)
    c = np.empty((H, W, 4), np.float32)
    c[...] = (*P.ALBEDO["floor_white"], 1)
    c[rose] = (*P.ALBEDO["floor_rose"], 1)
    c[band | edge] = (*P.ALBEDO["floor_band"], 1)
    img = bpy.data.images.new("nave_floor", W, H, alpha=False, float_buffer=True)
    img.colorspace_settings.name = "Linear Rec.709"
    img.pixels.foreach_set(c.ravel())
    img.pack()
    return img, x0, y0, x1 - x0, y1 - y0


def floor_material(grey):
    img, x0, y0, w, h = floor_image()
    m = bpy.data.materials.new("floor_nave")
    m.use_nodes = True
    N, L = m.node_tree.nodes, m.node_tree.links
    bsdf = N.get("Principled BSDF")
    tc = N.new("ShaderNodeTexCoord")
    mp = N.new("ShaderNodeMapping")
    mp.inputs["Location"].default_value = (-x0 / w, -y0 / h, 0)
    mp.inputs["Scale"].default_value = (1 / w, 1 / h, 1)
    L.new(tc.outputs["Object"], mp.inputs["Vector"])
    t = N.new("ShaderNodeTexImage")
    t.image, t.extension, t.interpolation = img, "EXTEND", "Linear"
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
    # Outside the nave the platform is plain (not finished): the colour passed in.
    sep = N.new("ShaderNodeSeparateXYZ")
    L.new(tc.outputs["Object"], sep.inputs["Vector"])
    inside = None
    for comp, lo, hi in (("X", x0, x0 + w), ("Y", y0, y0 + h)):
        a = N.new("ShaderNodeMath"); a.operation = "GREATER_THAN"; a.inputs[1].default_value = lo
        b = N.new("ShaderNodeMath"); b.operation = "LESS_THAN"; b.inputs[1].default_value = hi
        L.new(sep.outputs[comp], a.inputs[0]); L.new(sep.outputs[comp], b.inputs[0])
        ab = N.new("ShaderNodeMath"); ab.operation = "MULTIPLY"
        L.new(a.outputs[0], ab.inputs[0]); L.new(b.outputs[0], ab.inputs[1])
        if inside is None:
            inside = ab
        else:
            both = N.new("ShaderNodeMath"); both.operation = "MULTIPLY"
            L.new(inside.outputs[0], both.inputs[0]); L.new(ab.outputs[0], both.inputs[1])
            inside = both
    sel = N.new("ShaderNodeMix")
    sel.data_type = "RGBA"
    _sock(sel, "A_Color").default_value = grey
    L.new(inside.outputs[0], _sock(sel, "Factor_Float"))
    L.new(_sock(mul, "Result_Color", True), _sock(sel, "B_Color"))
    L.new(_sock(sel, "Result_Color", True), bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.35
    return m


def materials():
    A = P.ALBEDO
    return {
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
    }


# ================================================================ build the finished parts
def apply():
    """Replace the nave arm's grey parts with the finished ones. Returns the materials."""
    NW, CH, T = P.NAVE_HALF_W, P.CROSS_HALF, P.WALL_T
    PZ, SZ = P.PLATFORM_Z, P.SPRING_Z
    Y0, Y1 = P.FACADE_Y1, P.CROSS_Y0 - P.TRANSVERSE_T        # nave between facade and crossing arch
    M = materials()
    stone, stucco = [M["stone"]], [M["stucco"]]

    _remove("nave_vault", "nave_cornice_-1", "nave_cornice_1", "arch_front",
            *[f"nave_pilaster_{s}_{y}" for s in (-1, 1) for y in P.PILASTERS_Y])

    # Vault: coffered inner surface over a backing shell behind the coffers.
    pat = dict(col=P.COFFER_COL, row=P.COFFER_ROW, flat=P.COFFER_FLAT, s0=0.0, y_ref=P.COFFER_Y_REF,
               rib=P.COFFER_RIB, steps=P.COFFER_STEPS, splay=P.COFFER_SPLAY)
    fs = P.COFFER_FIELD_S
    coffer_sheet("nave_vault_coffers", NW, SZ, Y0, Y1, (-fs, fs, P.COFFER_FIELD_Y0, Y1), pat,
                 [M["vault_rib"], M["coffer"], M["coffer_riser"]])
    back = P.COFFER_BACK
    bm = bmesh.new()
    outer = [(math.cos(t) * (NW + 0.6), SZ + math.sin(t) * (NW + 0.6)) for t in np.linspace(0, math.pi, 73)]
    inner = [(math.cos(t) * (NW + back), SZ + math.sin(t) * (NW + back)) for t in np.linspace(math.pi, 0, 73)]
    vs = [bm.verts.new((x, Y0, z)) for x, z in outer + inner]
    f = bm.faces.new(vs)
    ext = bmesh.ops.extrude_face_region(bm, geom=[f])
    bmesh.ops.translate(bm, verts=[e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)], vec=(0, Y1 - Y0, 0))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    _obj("nave_vault_backing", bm, "stucco", stucco)

    # Crossing arch: same intrados, opening enlarged above the springing to take the coffered soffit.
    top = P.DRUM_Z0 + 1.5
    rb = CH + back
    pts = [(-(NW + T), PZ), (-CH, PZ), (-CH, SZ), (-rb, SZ)]
    pts += [(rb * math.cos(t), SZ + rb * math.sin(t)) for t in np.linspace(math.pi, 0, 97)[1:-1]]
    pts += [(rb, SZ), (CH, SZ), (CH, PZ), (NW + T, PZ), (NW + T, top), (-(NW + T), top)]
    bm = bmesh.new()
    vs = [bm.verts.new((x, Y1, z)) for x, z in pts]
    f = bm.faces.new(vs)
    ext = bmesh.ops.extrude_face_region(bm, geom=[f])
    bmesh.ops.translate(bm, verts=[e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)],
                        vec=(0, P.CROSS_Y0 - Y1, 0))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    _obj("arch_front", bm, "stone", stone)
    k = CH / NW                                   # same pattern in angle, so the columns run on
    apat = dict(pat, col=P.COFFER_COL * k, flat=P.COFFER_FLAT * k)
    coffer_sheet("arch_front_soffit", CH, SZ, Y1, P.CROSS_Y0, (-fs * k, fs * k, Y1, P.CROSS_Y0), apat,
                 [M["vault_rib"], M["coffer"], M["coffer_riser"]])
    # Archivolt on the nave face of the arch.
    prof = archivolt()
    ts = np.linspace(0, math.pi, 97)
    sweep("arch_front_archivolt", prof,
          [Vector((CH * math.cos(t), Y1, SZ + CH * math.sin(t))) for t in ts],
          [Vector((0, -1, 0))] * len(ts), [Vector((math.cos(t), 0, math.sin(t))) for t in ts], "stone", stone)

    # Walls: pilasters (shaft, base, capital), entablature with ressauts, string course.
    W, D = P.PILASTER_W, P.PILASTER_D
    z_arch = P.ENTABLATURE_Z0
    for side in (-1, 1):
        wx = side * NW
        ob = bpy.data.objects.get(f"nave_wall_{side}")
        if ob:
            ob.data.materials.clear()
            ob.data.materials.append(M["stucco"])
        # side = -1 is the left wall: travelling +y, the room is on the right.
        hand = 1 if side < 0 else -1
        for yc in P.PILASTERS_Y:
            bm = bmesh.new()
            bmesh.ops.create_cube(bm, size=1.0)
            x0, x1 = sorted((wx, wx - side * D))
            for v in bm.verts:
                v.co = Vector((x0 + (v.co.x + 0.5) * (x1 - x0), yc - W / 2 + (v.co.y + 0.5) * W,
                               PZ + (v.co.z + 0.5) * (SZ - 0.05 - PZ)))   # fills the ressaut behind the entablature
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
            _obj(f"nave_pilaster_{side}_{yc}", bm, "stone", stone)
            ring = [(wx + side * 0.03, yc - W / 2), (wx - side * D, yc - W / 2),
                    (wx - side * D, yc + W / 2), (wx + side * 0.03, yc + W / 2)]
            for tag, prof in (("base", attic_base(PZ)), ("capital", capital(z_arch))):
                sweep(f"nave_pilaster_{tag}_{side}_{yc}", prof, *plan_path(ring, hand), "stone", stone)
        # Entablature: along the wall, breaking forward over each pilaster, round the crossing pier.
        path = [(wx, Y0)]
        for yc in P.PILASTERS_Y:
            path += [(wx, yc - W / 2), (wx - side * D, yc - W / 2), (wx - side * D, yc + W / 2), (wx, yc + W / 2)]
        pier = [(wx, Y1), (side * CH, Y1), (side * CH, P.CROSS_Y0)]
        sweep(f"nave_entablature_{side}", entablature(z_arch), *plan_path(path + pier, hand), "stone", stone)
        # String course between the pilasters, and round the pier.
        edges = [Y0] + [y for yc in P.PILASTERS_Y for y in (yc - W / 2, yc + W / 2)] + [Y1]
        for i in range(0, len(edges), 2):
            a, b = edges[i], edges[i + 1]
            run = [(wx, a - (0.03 if i else 0.0)), (wx, b + 0.03)] if i + 2 < len(edges) else [(wx, a - 0.03)] + pier
            sweep(f"nave_string_course_{side}_{i // 2}", string_course(*P.STRING_COURSE), *plan_path(run, hand),
                  "stone", stone)
        # Base along the crossing pier (its jamb is a plain pier face).
        sweep(f"arch_front_base_{side}", attic_base(PZ),
              *plan_path([(wx + side * 0.03, Y1), (side * CH, Y1), (side * CH, P.CROSS_Y0)], hand), "stone", stone)
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

    vault = ["nave_vault_coffers", "nave_vault_backing", "arch_front_soffit"]
    right = [ob.name for ob in bpy.data.objects
             if ob.type == "MESH" and ob.name.startswith(("nave_", "arch_front_"))
             and min((ob.matrix_world @ Vector(c)).x for c in ob.bound_box) > 0.5]
    sun.light_linking.blocker_collection = excluded("sun_not_blocking", vault + right + ["facade", "arch_front"])
    # Nor do the faces up under the vault (the crossing arch's archivolt and face).
    sun.light_linking.receiver_collection = excluded("sun_not_received", vault + ["arch_front_archivolt", "arch_front"])
    return travel
