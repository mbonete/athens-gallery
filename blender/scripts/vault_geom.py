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
TEX_H = TEX_H_DRAW + STRIP

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
