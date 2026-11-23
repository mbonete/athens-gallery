"""Where the vault ornament lies on the front wall (first-arch idea 1, made part of the wall):
the numbers tools/vault_ornament.py paints with and finish2.vault_relief() builds with.

The design was drawn in web metres on the front wall's plane, through the camera solve like the
opening arch (a point Raphael's eye sees at scan px (u, v) lies at x = (u - CX) K,
y = EYE - (v - CY) K, K = wall distance / F_PX). Here the plane is the wall's face itself
(y = ARCH_Y in Blender): web metres / SCALE = Blender metres, x on x, the web's height on z.
Pure Python (no numpy): Blender imports it too.
"""
import math

import params as P

S = P.SCALE
EYE = P.EYE_Z * S                 # web metres
PLANE = P.ARCH_Y * S              # the front wall's face, from the eye at the start
K = PLANE / P.F_PX                # web metres a scan px, on the wall


def scan_to_plane(u, v):
    return (u - P.CX) * K, EYE - (v - P.CY) * K


XC, YC = scan_to_plane(*P.ARCH_C)              # the arch's centre (below the springing)
R0 = P.ARCH_R["outer"] * K                     # outer edge of the arch's dark red band
YS = scan_to_plane(P.CX, P.ARCH_SPRING_V)[1]   # the springing: the impost's top

# The tile: the whole width round the arch (both halves, so its painted light can come from the
# sun's side), from just below the springing to past the top of a desktop start view.
HW = 3.10                          # half width, web metres (a desktop start view shows 2.97)
Y0 = YS - 0.012
Y1 = Y0 + 1760 / (2048 / HW)       # the decal's height (2.663 m)
PPM = 495.5                        # tile px a web metre: 3072 px across
TEX_W = int(round(2 * HW * PPM / 4)) * 4
TEX_H_DRAW = int(round((Y1 - Y0) * PPM / 4)) * 4
STRIP = 64                         # px over the top: plain white and gold for the reliefs' sides
# Between the drawing and the strip, the wall's stone continued (in phase with the wall above):
# the wall face's top edge (Y1) was the drawing's top row, so filtering and the mipmaps read the
# strip's white and gold (and its gold-leaf alpha) along it, a hairline across the bare wall seen
# when the view turns up (Maria's "taller" round, 2026-11-23). 64 rows: clear to mip level 6.
PAD = 64
TEX_H = TEX_H_DRAW + PAD + STRIP

# The design, web metres (tools/vault_ornament.py draws it; see there)
BAND = dict(fil_in=0.012, line=0.0025, blue=0.110, fil_out=0.012)
RB_BLUE0 = R0 + BAND["fil_in"] + BAND["line"]
RB_BLUE1 = RB_BLUE0 + BAND["blue"]
RB = RB_BLUE1 + BAND["line"] + BAND["fil_out"]
RIB_DEG = 50.0
RIB_W = 0.10
ROUNDEL_R = 0.135
FRAME_W = 0.032
FILLET = (0.020, 0.0055)
RC = R0 + ROUNDEL_R
# Each blue field is closed on its outer side by a vertical framed edge (arch piers, fix B): its
# outer edge 1 cm inside the tile's painted extent (HW), outside a 16:10 start view (2.97).
FIELD_EDGE = HW - 0.010
ROSETTE_R = 0.0755


def rib_axes(side):
    """Unit vectors (x, y) along the rib outwards and across it towards the crown, for side -1
    (left) or +1 (right), in the wall plane."""
    th = side * math.radians(RIB_DEG)
    e_s = (math.sin(th), math.cos(th))
    n_up = (-side * e_s[1], side * e_s[0])
    return e_s, n_up


def roundel_centre(side):
    e_s, _ = rib_axes(side)
    return XC + RC * e_s[0], YC + RC * e_s[1]


# ------------------------------------------------------------------ Blender metres on the wall
def b(v):
    return v / S


def side_uv():
    """Detail UVs (Blender convention, v up) of the strip's white and gold patches."""
    v = 1.0 - (STRIP / 2) / TEX_H
    return (0.25, v), (0.75, v)


TILE_B = (b(2 * HW), b(TEX_H / PPM))                # detail tile size, Blender metres
ORIGIN_B = (b(XC - HW), b(Y0))                      # its lower left corner on the wall


# The gilded rosette's boss stands 4.5-9.3 cm proud (finish2.vault_relief), its painted ring on the
# roundel's face at 4.5 cm. Seen from Raphael's eye a boss on the roundel's axis sits 3-4 cm off
# that ring's centre (parallax), so the boss stands on the sight line through the ring's centre:
# its petals' middle height (h) lands on the ring's centre at the start.
BOSS_H, RING_H = 0.083, 0.045          # Blender metres proud of the wall


def boss_centre(side):
    """The boss's (and its painted rosette's) centre on the wall plane, web metres."""
    cx, cy = roundel_centre(side)
    k = (PLANE - BOSS_H * S) / (PLANE - RING_H * S)
    return cx * k, EYE + (cy - EYE) * k            # the eye is at x = 0, height EYE


def boss_outline(phi):
    """The boss's radius round its centre, a fraction of ROSETTE_R: eight petal lobes."""
    return 0.80 + 0.20 * abs(math.cos(4 * phi)) ** 0.6


# The ribs' painted strip ("vault_rib" detail tile, tools/vault_ornament.rib_strip): the rib runs
# on past the tile's edge to the band at 9 m (finish2.vault_relief), so its front takes the same
# paint and grain from a strip laid along it, from inside the tile (where the two show the same
# texels' worth of paint, so the change of texture can't be seen) to past its end. One row
# per rib (left below, right above), at the tile's own texel density.
RIB_S0 = 3.40                      # web metres along the rib from the arch's centre (the roundel ends at 3.09)
RIB_SWITCH = 3.60                  # rib fronts wholly past this take the strip; the rest stay in the tile (to 4.0)
RIB_TEX_W, RIB_ROW_PX = 2560, 64   # px along the strip; px across each row
RIB_TEX_H = 2 * RIB_ROW_PX
RIB_L = RIB_TEX_W / PPM            # 5.17 m: to s 8.57, past the ribs' ends on the band at 8.94 m (8.34 at most)
RIB_ROW = RIB_ROW_PX / PPM         # 0.129 m across a row: the rib (0.10) and 1.5 cm of wall each side
RIB_TILE_B = (b(RIB_L), b(2 * RIB_ROW))


def rib_strip_st(side, x, z):
    """(s, t) of a point (x, z) on the wall, web metres: along the rib from the arch's centre, and
    across it (> 0 on the crown's side)."""
    e_s, n_up = rib_axes(side)
    return (x - XC) * e_s[0] + (z - YC) * e_s[1], (x - XC) * n_up[0] + (z - YC) * n_up[1]


def rib_strip_uv(side, xb, zb):
    """Detail UV (Blender convention, v up) of a point on the wall, Blender metres, in side's row."""
    s, t = rib_strip_st(side, xb * S, zb * S)
    return (s - RIB_S0) / RIB_L, (0.5 if side > 0 else 0.0) + (t + RIB_ROW / 2) / (2 * RIB_ROW)
