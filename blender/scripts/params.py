"""Dimensions of the hall, in metres. Derived from the fresco (see reference/camera.json).

Axes: X right, Y into the painting, Z up. Raphael's eye is at (0, 0, EYE_Z); the picture
plane (the fresco's wall) is at Y = PICTURE_PLANE_Y. The lower floor is Z = 0.

Frontal elements were placed by choosing a depth Y and reading their outline from the
image: X = (u - CX) * Y / F_PX, Z = EYE_Z - (v - CY) * Y / F_PX (u, v on the 3840 px scan).
"""

# Overall size for the web export (Gate 2): 70 % makes Plato and Aristotle life-size,
# keeping Raphael's ratio between the figures and the hall. Renders stay at 100 %.
SCALE = 0.7

# Camera (3840 x 2661 scan).
IMG_W, IMG_H = 3840, 2661
F_PX = 2274.0            # square crossing reading (Gate 1, 5 m)
CX, CY = 1933.3, 1775.9  # vanishing point = principal point
EYE_Z = 1.85             # above the lower floor
PICTURE_PLANE_Y = F_PX / 435.0  # ~5.2 m

# Floors and steps. Each step: (front edge Y, top Z). Read from step edges at u ~2500.
STEPS = [(6.852, 0.271), (7.388, 0.456), (8.255, 0.6375), (8.923, 0.814)]
PLATFORM_Z = 0.814
STEP_HALF_W = 4.5     # central flight; podiums at platform height on either side
SIDE_HALF_W = 16.0
PODIUM_Y0 = 8.59
# Pedestal at the front corner of the left podium (the block the boy reads on):
# u 346-730, base v 2266 on the lower floor, top v 1786 -> X 4.54-6.0, Z 0-1.81.
PEDESTAL = (4.54, 6.0, 8.55, 10.1, 0.0, 1.81)   # front 4 cm proud of the podium face

# Facade with the front piers (Apollo and Athena niches). Its front face stands just
# behind the figures' feet (v ~1935 at the platform level gives Y ~14.8).
FACADE_Y0, FACADE_Y1 = 15.5, 18.5
FACADE_HALF_W = 16.0
FACADE_TOP = 24.0
STRING_COURSE = (9.0, 9.35)   # cornice above the niches (v 650-710 at Y 15.5)

# Nave: inner face of the piers at u ~1075 / ~2790 -> X = +-5.9 at Y 15.5.
NAVE_HALF_W = 5.9
WALL_T = 1.0
SPRING_Z = 12.3               # vault springing (crossing arches 12.1-12.5)
CORNICE = (11.3, 12.3, 0.5)   # z0, z1, projection
NAVE_Y1 = 31.7
PILASTERS_Y = [22.9, 27.3]    # three even bays on each nave wall (fresco: dark strips u 1345-1515)
PILASTER_W, PILASTER_D = 1.0, 0.35

# Niches on the facade piers (Apollo left, Athena right): X 6.37-8.07, Z 4.79-8.72.
NICHE_X = (6.37, 8.07)
NICHE_Z = (4.79, 8.72)
NICHE_DEPTH = 0.9
RELIEF_Z = (3.2, 4.6)

# Crossing: square, side = arch span. Front arch face at Y 32.5 (766 px), back at 43.45.
CROSS_HALF = 5.475
CROSS_Y0, CROSS_Y1 = 32.5, 43.45
TRANSVERSE_T = 0.8
DRUM_Z0 = SPRING_Z + CROSS_HALF       # 17.775, crown of the crossing arches
DRUM_WIN_Z = (19.6, 22.6)
DRUM_Z1 = 22.8
DRUM_WINDOWS = 18     # fresco: 3 windows at the back, ~72 px wide, piers ~28 px, one on the axis
DRUM_WINDOW_W = 1.4
OCULUS_R = 0.9

# Second arm and end wall.
ARM2_Y1 = 55.0
END_T = 1.0
END_ENTABLATURE = (12.3, 13.0)
END_ATTIC_TOP = 14.3
DOOR_HALF = 3.67
DOOR_SPRING = 7.56
ARM2_PILASTERS_Y = [49.6]

# Painting places (placeholders): bay centres on the side walls, 3 per nave wall and 2 per
# wall in the second arm. Real sizes come later; placeholders are 1.8 x 2.4 m.
PAINTING_W, PAINTING_H, PAINTING_BOTTOM = 1.8, 2.4, 1.3   # bottom above the platform
PAINTINGS_Y = [20.45, 25.1, 29.75, 46.7, 52.55]


# ---------------------------------------------------------------- Stage 1 finish (branch hall-look)
# finish.py builds these; renders/hall-stage1/REPORT.md has the readings, crops and limits.
FINISH = True                # build.py builds the finished nave arm unless "grey" is passed

# Coffered nave vault, read from the fresco unrolled onto the vault's development (s = arc length
# from the crown at radius NAVE_HALF_W, y = depth): hexagons and lozenges tiled edge to edge.
# Hexagon columns run along the vault with their points across it; a lozenge sits between two
# columns, its long diagonal along y spanning one row. All on the tiling's centre lines.
COFFER_COL = 2.62            # hexagon column spacing along s (crown hexagons 2.6-2.65 m apart)
COFFER_ROW = 1.62            # row spacing along y (crown hexagon tops at y 30.79, 29.17, 27.55)
COFFER_FLAT = 1.36           # hexagon flat edge (opening's flat top ~1.2 m, plus the rib)
COFFER_Y_REF = 30.07         # a hexagon row centre (crown column); rows every COFFER_ROW from it
COFFER_RIB = 0.20            # flat rib between coffers (0.1-0.25 m in the unroll; 0.20 fits)
# Steps from the rib inwards: (riser depth, tread width). The crown hexagons show two dark risers
# 0.23-0.25 m tall in the unroll (x 1/1.87 for the view angle -> ~0.13 m) and a 0.09 m light tread.
COFFER_STEPS = [(0.13, 0.09), (0.13, 0.0)]
COFFER_SPLAY = 0.015         # each riser leans out of the opening a little (designed)
COFFER_BACK = 0.30           # backing shell behind the coffers (hidden)
COFFER_FIELD_Y0 = 22.4       # field starts at the first pier: fresco field border at y 22.3-22.9;
                             # bay 1 (facade to here) is a plain soffit in the fresco (u 1250-1380, v 500-700)
COFFER_FIELD_S = 8.35        # field edge from the crown (borders at s -8.55 and +8.1, centred on the
                             # crown hexagons at s -0.15); the cornice hides the vault beyond s ~8.43

# Mouldings (finish.py). Entablature 10.5-12.3: architrave, frieze, cornice in nearly equal parts,
# as on the first left pier (u 1265-1350, v 672-860, ~1.8 m at Y ~22); its top and 0.5 m
# projection are the old CORNICE reading. Pilasters carry 0.5 m Doric capitals under it.
ENTABLATURE_Z0 = 10.5
# STRING_COURSE (above) is continued along the nave walls between the pilasters.

# Nave floor (designed in the fresco's floor vocabulary; the fresco shows the nave floor only in
# a ~20 px strip behind Plato's and Aristotle's feet).
FLOOR_SLABS_ACROSS = 7       # 1.69 m slabs, centre slab on the axis; rows follow COFFER_ROW
FLOOR_BAND = 0.12            # mauve band between slabs
FLOOR_MARGIN = 0.10          # white margin round the lozenge
FLOOR_LOZENGE_CORE = 0.45    # white core of the lozenge (fraction of its size)

# Colours: medians of fresco pixels (sRGB, full-resolution scan), see REPORT.md for the boxes.
# They are what the fresco shows under Raphael's light, so the albedos below start from them and
# were calibrated against a Cycles render of the same regions (REPORT.md, "Colour").
FRESCO_SRGB = {
    "wall_lit": (215, 190, 176), "wall_shaded": (153, 128, 98), "frontal_lit": (203, 181, 171),
    "soffit_bay1": (190, 169, 160), "frieze_lit": (200, 179, 174),
    "vault_rib": (124, 102, 85), "coffer_riser": (86, 71, 60), "coffer_panel": (141, 117, 98),
    "floor_white": (231, 214, 217), "floor_rose": (174, 135, 134), "floor_mauve": (143, 114, 135),
    "sky": (175, 175, 245),
}
ALBEDO = {   # linear; started from the fresco's lit colours, then calibrated (REPORT.md, "Colour")
    "stucco": (0.563, 0.462, 0.426), "stucco_dark": (0.507, 0.416, 0.383),
    "stone": (0.57, 0.468, 0.43), "stone_dark": (0.53, 0.435, 0.40),
    "rib": (0.58, 0.488, 0.389), "rib_dark": (0.51, 0.43, 0.342),
    "coffer_light": (0.68, 0.59, 0.48), "coffer_dark": (0.40, 0.345, 0.28),     # panels: mottled, ~0.8 x rib
    "riser_light": (0.41, 0.375, 0.34), "riser_dark": (0.25, 0.23, 0.205),      # risers: darker (see REPORT)
    "floor_white": (0.68, 0.57, 0.58), "floor_rose": (0.36, 0.21, 0.20), "floor_band": (0.23, 0.15, 0.20),
}

# Light. The fresco's shading: faces turned to +X (left nave wall) are lit (median 215,190,176),
# faces turned to -X (right nave wall) are in shade (153,128,98), frontal faces are lit equally on
# both sides (202-204), soffits get only bounce light. In linear terms the direct part on +X faces
# vs frontal faces is 0.32 : 0.26 -> light travels 39 deg off the -X axis towards +Y, i.e. the sun
# is to the front right. Cast shadows on the platform floor run at ~45 deg in plan the same way.
SUN_AZIMUTH = 39.0           # degrees from -X towards +Y (direction of travel)
SUN_ELEVATION = 35.0         # not measurable precisely: floor shadows ~1-1.5x the figures' height
                             # (45-55 deg), but the frieze under the cornice is lit (needs < ~30 deg)
SUN_ANGLE = 3.0
SUN_STRENGTH = 4.0
SUN_COLOR = (1.0, 0.97, 0.92)
SKY = (0.43, 0.43, 0.91)     # fresco sky in the far door, linear
SKY_LIGHT = (1.0, 0.85, 0.52)  # colour of the sky as light: fresco shade/lit ratio per channel, normalised
SKY_STRENGTH = 0.6
GREY_DIM = 0.6               # unfinished grey parts are dimmed in the finished renders so they do not clip
EXPOSURE = 0.0               # Standard view transform (no tone curve), stops
