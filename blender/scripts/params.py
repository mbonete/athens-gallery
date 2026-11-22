"""Dimensions of the hall, in metres. Derived from the fresco (see reference/camera.json).

Axes: X right, Y into the painting, Z up. Raphael's eye is at (0, 0, EYE_Z); the picture
plane (the fresco's wall) is at Y = PICTURE_PLANE_Y. The lower floor is Z = 0.

Frontal elements were placed by choosing a depth Y and reading their outline from the
image: X = (u - CX) * Y / F_PX, Z = EYE_Z - (v - CY) * Y / F_PX (u, v on the 3840 px scan).
"""
import os

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
PILASTERS_Y = [22.9, 27.3]    # three even bays on each nave wall (fresco: dark strips u 1345-1515)
PILASTER_W, PILASTER_D = 1.0, 0.35

# Niches on the facade piers (Apollo left, Athena right): X 6.37-8.07, Z 4.79-8.72.
NICHE_X = (6.37, 8.07)
NICHE_Z = (4.79, 8.72)
NICHE_DEPTH = 0.5             # stage 2: was 0.9; the screen in front of bay 1's recesses is 0.7 m
RELIEF_Z = (3.2, 4.6)

# Crossing: square, side = arch span. Gate 2: front arch face at Y 32.5 (766 px), back at 43.45.
# Stage 2 options (CROSSING env var; renders/hall-stage2/REPORT.md, "Crossing"):
#   gate2: the approved Gate 2 crossing, 10.95 m. Painted front opening's crown at v 686, the
#          model's at 662 (24 px high); back arch crown 937 painted, 942.5 model.
#   A:     square 11.8 m: the nave barrel runs on at its own radius to the painted opening
#          (crown v 689) and the back arch is 11.8 m behind it (crown v 968, 31 px low).
#   A2:    square 11.8 m, shifted so both arches miss equally (front v 669, back v 957).
CROSSINGS = {"gate2": (32.5, 5.475), "A": (34.2, 5.9), "A2": (33.6, 5.9)}
CROSSING = os.environ.get("CROSSING", "A")   # Maria, stage 2 gate: option A
CROSS_Y0, CROSS_HALF = CROSSINGS[CROSSING]
CROSS_Y1 = round(CROSS_Y0 + 2 * CROSS_HALF, 3)
TRANSVERSE_T = 0.8
NAVE_Y1 = round(CROSS_Y0 - TRANSVERSE_T, 3)
DRUM_Z0 = round(SPRING_Z + CROSS_HALF, 3)   # crown of the crossing arches (17.775 in gate2)
# The drum's visible back half keeps its painted heights: scale them about the eye with the
# depth of the crossing's back (43.45 in gate2).
_K = CROSS_Y1 / 43.45
DRUM_WIN_Z = tuple(round(EYE_Z + (z - EYE_Z) * _K, 3) for z in (19.6, 22.6))
DRUM_Z1 = round(EYE_Z + (22.8 - EYE_Z) * _K, 3)
DRUM_WINDOWS = 18     # fresco: 3 windows at the back, ~72 px wide, piers ~28 px, one on the axis
DRUM_WINDOW_W = 1.4 * _K
OCULUS_R = 0.9

# Second arm and end wall.
ARM2_Y1 = 55.0
END_T = 1.0
END_ENTABLATURE = (12.3, 13.0)
END_ATTIC_TOP = 14.57         # stage 2: top of the painted Doric cornice (v 1250 at Y 55); was 14.3
DOOR_HALF = 3.67
DOOR_SPRING = 7.56
# One pilaster mid-arm (gate2 keeps its approved 49.6).
ARM2_PILASTERS_Y = [49.6] if CROSSING == "gate2" else [round((CROSS_Y1 + TRANSVERSE_T + ARM2_Y1) / 2, 2)]

# Painting places (placeholders): bay centres on the side walls, 3 per nave wall and 2 per
# wall in the second arm. Real sizes come later; placeholders are 1.8 x 2.4 m.
PAINTING_W, PAINTING_H, PAINTING_BOTTOM = 1.8, 2.4, 1.3   # bottom above the platform
_A2 = (CROSS_Y1 + TRANSVERSE_T, ARM2_PILASTERS_Y[0] - PILASTER_W / 2, ARM2_PILASTERS_Y[0] + PILASTER_W / 2, ARM2_Y1)
PAINTINGS_Y = [20.45, 25.1, 29.75] + ([46.7, 52.55] if CROSSING == "gate2" else
                                      [round((_A2[0] + _A2[1]) / 2, 2), round((_A2[2] + _A2[3]) / 2, 2)])


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
    # Round 9 (Maria, "now is too white", her swatch sRGB 212,203,171 "or a tad lighter"): cream
    # marble, the round-8 whites x (0.835, 0.795, 0.61), aiming the lit nave wall at ~(216, 207, 175).
    # Round 8 (Maria): white marble, not the fresco's buff. Warm white, veins (the _dark ends of
    # the Marble014 ramp) a cool grey. Was stucco (0.563, 0.462, 0.426), stone (0.57, 0.468, 0.43),
    # rib (0.58, 0.49, 0.39).
    "stucco": (0.584, 0.549, 0.406), "stucco_dark": (0.558, 0.524, 0.389),
    "stone": (0.584, 0.549, 0.406), "stone_dark": (0.558, 0.524, 0.389),
    "rib": (0.584, 0.549, 0.406), "rib_dark": (0.564, 0.53, 0.393),
    "coffer_light": (0.64, 0.56, 0.45), "coffer_dark": (0.38, 0.33, 0.27),     # panels: mottled, ~0.8 x rib
    "riser_light": (0.41, 0.375, 0.34), "riser_dark": (0.25, 0.23, 0.205),      # risers: darker (see REPORT)
    # Stage 4: floors recalibrated against the fresco under the warm light (the web read them salmon).
    # Round 10 (Maria): the floors' patterns #754543 as seen on the sunlit floor (lozenges and the
    # lower floor's squares; were rose (0.47, 0.26, 0.29) and mauve (0.18, 0.116, 0.22)), and
    # everything else the floor cream: the corridor's slab lines (were purple (0.23, 0.15, 0.24))
    # and the lower floor's bands and rings (were (0.568, 0.529, 0.39)).
    "floor_white": (0.584, 0.545, 0.4), "floor_rose": (0.164, 0.058, 0.059), "floor_band": (0.584, 0.545, 0.4),
    "floor_mauve": (0.155, 0.048, 0.046),                                     # lower floor's squares (more light reaches them: (120, 76, 76) at 0.164, 0.058, 0.059)
    "lower_white": (0.584, 0.545, 0.4),                                       # lower floor's bands and rings
    "step": (0.601, 0.564, 0.418), "step_dark": (0.559, 0.525, 0.39),              # treads, white marble (were 0.68, 0.60, 0.58)
    "step_riser": (0.534, 0.501, 0.372),                                         # risers (191,175,162)
}

# Light. The fresco's shading: faces turned to +X (left nave wall) are lit (median 215,190,176),
# faces turned to -X (right nave wall) are in shade (153,128,98), frontal faces are lit equally on
# both sides (202-204), soffits get only bounce light. In linear terms the direct part on +X faces
# vs frontal faces is 0.32 : 0.26 -> light travels 39 deg off the -X axis towards +Y, i.e. the sun
# is to the front right. Cast shadows on the platform floor run at ~45 deg in plan the same way.
SUN_AZIMUTH = float(os.environ.get('SUN_AZIMUTH', 20.0))  # Maria 2026-11-21: a raking sun along the left wall, so its pilasters read (was 39, the fresco's +X:frontal 0.32:0.26; frontal faces now take less)
SUN_ELEVATION = 35.0         # not measurable precisely: floor shadows ~1-1.5x the figures' height
                             # (45-55 deg), but the frieze under the cornice is lit (needs < ~30 deg)
SUN_ANGLE = 3.0
SUN_STRENGTH = 4.0
SUN_COLOR = (1.0, 0.985, 0.955)    # round 8: warm-white daylight (was (1.0, 0.98, 0.9))
SKY = (0.43, 0.43, 0.91)     # fresco sky in the far door, linear
SKY_LIGHT = (0.88, 0.93, 1.0)   # round 8: the sky as light, cool, so shade reads cool-neutral grey (was (0.95, 0.93, 0.45): the fresco's yellow shade)
SKY_STRENGTH = 0.6
# Round 9: the bake sees every material colour at this fraction of its saturation (luminance kept;
# bake.py, "white balance"). Light bouncing between cream walls otherwise compounds the cream at
# each bounce and the shade turns khaki ((129, 116, 87) on the right wall at 1.0); the eye's colour
# constancy would not see that. The colours on screen (detail tiles) keep their full saturation.
BOUNCE_CHROMA = 0.4
GREY_DIM = 0.6               # unfinished grey parts are dimmed in the finished renders so they do not clip
EXPOSURE = 0.0               # Standard view transform (no tone curve), stops

# ---------------------------------------------------------------- Stage 2 finish (finish2.py)
# Bay 1 (renders/hall-stage2/REPORT.md, "Bay 1"). Where the model had the facade's 3 m jamb
# Raphael paints a frontal face (horizontal mouldings at u 1050-1168 left, 2652-2800 right):
# behind a thin front screen the space opens sideways into a recess, whose back wall faces the
# visitor. Its inner edge reads at Y 17.5 (left) and 18.66 (right); the model takes 18.1.
BAY1_RECESS_Y0 = 16.2        # front screen 0.7 m (facade niches made 0.5 m deep to fit)
BAY1_RECESS_Y1 = 18.1        # the frontal back wall
BAY1_RECESS_X = 7.3          # outer wall; hidden from Raphael's eye (needs > 5.9 * 18.1 / 15.5 = 6.9)
BAY1_RECESS_TOP = 10.5       # painted band at v 700-770 -> Z 9.9-10.4; stage 4: the architrave's soffit (R1)
# Recess between the short block behind the vestibule and the first pilaster, full height to the
# springing: the painted cornice in bay 1 recedes along a line through the vanishing point with
# X / (Z - EYE) = 0.61-0.62 on both sides (u 1180-1265 / 2590-2670, v 580-690), i.e. X ~6.4 at
# Z 12.3; it ends at the first pier's ressaut (frontal, v 680-690 -> Y ~21.7).
BAY1_SIDE_RECESS = (18.9, 22.4, 6.5)   # y0, y1 (the first pilaster's face), |x| of its back wall
# The empty niche on the recess's back wall (statue niches at u 1170-1206 left, 2606-2647 right
# -> Y 20.1 and 21.7 on X 6.5): head at v ~835 (Z 9.6-9.8), sill at v ~1350 (Z 5.3).
BAY1_NICHE_YC, BAY1_NICHE_W = 20.6, 1.2   # left reads 19.9, right 21.3: the painting isn't symmetric
BAY1_NICHE_Z = (5.3, 9.6)
BAY1_NICHE_DEPTH = 0.35

# Lower floor (u 1150-2700, v 2380-2661, plan unroll): mauve fields with a white square ring,
# set in white bands; module 1.68 x 0.95 m, rings centred at X 0.65 + k * 1.68, Y ~5.95.
LOWER_FLOOR_MODULE = (1.68, 0.95)
LOWER_FLOOR_BAND = 0.07                  # half the white band between fields
LOWER_FLOOR_RING = ((0.42, 0.36), 0.10)  # ring outer half-sizes (x, y), band width
LOWER_FLOOR_X0, LOWER_FLOOR_Y0 = -0.19, 5.475

# Crossing (designed where the fresco shows nothing): tondo frames on the pendentives, centred
# on the diagonals; the drum's pilasters; ribs on the dome.
TONDO_H = round(0.68 * CROSS_HALF, 3)   # height of the tondo's centre above the springing
TONDO_R = 0.7
DOME_COFFER_RINGS, DOME_COFFER_COUNT = 5, 28
# Round 6: the dome's inside on the Pantheon's model (finish2.dome_coffers, designed).
DOME_BASE_BAND = 0.035              # rad: plain band at the springing (0.2 m)
DOME_RIB = 0.2                      # rib width, fraction of a cell
DOME_STEP_INSETS = (0.08, 0.05, 0.11)   # per step: each side, upper, lower (fractions of the cell)
DOME_STEP_DEPTH = 0.05              # per step, fraction of the cell's width (5 cm in the first ring)
OCULUS_RIM_R = 1.3                  # the smooth band ends here; the oculus' ring runs to OCULUS_R
OCULUS_SPILL_W = 120.0              # round 7: point light under the oculus, lighting the dome sheet only (finish.light)

# End wall: the painted Doric entablature (u 1700-2170, v 1250-1330 at Y 55): architrave
# Z 12.64-13.36, triglyph frieze 13.36-14.28, cornice 14.28-14.57. Triglyphs every 68 px
# (1.64 m), 15 px wide (0.36 m). The coordinator's brief said "balustrade": the pixels show a
# triglyph frieze, so that is what is built. Pilasters beside the door at u 1720-1760 / 2110-2150.
END_DORIC = (12.64, 13.36, 14.28, 14.57)
END_TRIGLYPH = (1.64, 0.36)
# Stage 4 (joint rules): pilasters 0.45 from the jamb, 0.85 wide, 0.25 deep so the side walls'
# cornice (0.85 proud) clears them and the door's impost (0.18 proud) dies into their sides.
END_PILASTER_X0, END_PILASTER_W, END_PILASTER_D = 0.45, 0.8, 0.25

# Painted surfaces (Maria, stage 2): (noise scale per m, contrast, speckle darkness). The
# fresco's cracks and stains are left out on purpose (its age, not the building).
PAINTED = {"coffer": (1.0, 0.04, 0.0), "rib": (1.0, 0.04, 0.0), "stone": (1.5, 0.05, 0.0),
           "stucco": (1.0, 0.04, 0.0)}
# Round 7 (Maria): coffers and ribs clean, at the walls' grain (were (6.0, 0.6) mottle and a 0.35 speckle).

# Raphael's light, beyond one sun (finish.light; REPORT.md "Light"):
# Maria, stage 2 gate: halve the darkening, f -> 1 - (1 - f) / 2 (was 0.55 and (0.55, 0.5, 0.38)).
RIGHT_UNDERSIDE = 0.775      # downward faces on the right side painted darker (cornice soffit)
RIGHT_WALL = (0.74, 0.75, 0.78)  # faces turned to -X on the right: darker, a neutral grey (round 8; was olive (0.775, 0.75, 0.69))
FRONT_BOUNCE = float(os.environ.get("FRONT_BOUNCE", 4000.0))        # W, area light on bay 1's floor lighting only the vault over it (soffit 191)
NO_SUN = ()                  # stage 2 tried the facade here (a mis-sampled box); it is lit
FAR = (1.03, 1.03, 1.05)     # the end wall a touch lighter and cooler (round 8, white marble; was (1.3, 1.43, 1.56))
DRUM = (0.96, 0.96, 0.96)    # round 8: no olive (was (0.75, 0.74, 0.65))
FACADE = (0.95, 0.95, 0.96)  # the facade's front a little darker than the hall's lit marble (was (0.7, 0.68, 0.72))
TREAD = 1.5                  # coffer treads painted lighter than the ribs (light lines between the risers)    # the drum is painted darker and more olive than lit stucco (197,172,150)

# Bay 1 hanging options for the Mucha (left) and the Klimt (right), web size / 0.7 (REPORT.md):
# "below": both on the recess's back wall under the niches; "inside": the Mucha in its niche.
MUCHA_100 = (0.65 / SCALE, 1.25 / SCALE)    # w, h at 100 %
KLIMT_100 = (1.74 / SCALE, 0.96 / SCALE)
HANG_CENTRE_Z = PLATFORM_Z + 1.55 / SCALE  # web: centre 1.55 m above the floor

# ---------------------------------------------------------------- Stage 3: bake for the web
# blender/scripts/bake.py. Texel density in pixels per metre at 100 % (the web shows 70 %, so
# 1 px covers 0.7/density m there). "rough" trades quality for speed only.
BAKE = {
    # Stage 4: the atlases hold light only (detail comes from tiled textures), so the density is
    # chosen for light: 16 px/m rough, 28 final, mouldings denser (BAKE_DENSITY_SCALE).
    # Stage 6: margin <= gap, so two islands' margins never meet; a thin island's edge texels
    # were taken by its neighbour's margin (dark lines on the facade panel frame).
    "rough": dict(samples=128, density=16.0, max_size=4096, margin=2, gap=2.0, denoise=True),
    "final": dict(samples=1024, density=28.0, max_size=4096, margin=3, gap=3.0, denoise=True),
}
BAKE_QUALITY = os.environ.get("BAKE", "rough")
# Samples per group, a multiple of the quality's: the front wall's small reliefs (the vault
# ornament) in a rough bake were noisy enough for the denoiser to blotch them.
BAKE_GROUP_SAMPLES = {"front": 2.0}
# Groups baked into one atlas each, by the object's centre along Y (metres, 100 %).
BAKE_GROUPS = [("front", -999, 15.0), ("facade", 15.0, 19.0), ("nave", 19.0, 33.0),
               ("crossing", 33.0, 46.9), ("arm2", 46.9, 999)]
# Density factors by object name prefix (first match): mouldings change light across a few cm.
BAKE_DENSITY_SCALE = {"vault_wall": 4.0, "vault_": 8.0,        # the vault ornament: the wall round it and its reliefs
                      "opening_archivolt_intrados": 8.0,      # the meander's soffit: one strip along the arc, 10.3 m x 0.29 m (1310 x 37 px rough, 2300 x 64 final)
                      "opening_archivolt": 12.0,              # the opening arch's bands: their 2 cm steps were a third of a texel at 16 px/m (Maria's smeared strip, 2026-11-22)
                      "opening_reveal": 8.0, "opening_impost": 6.0,   # arch piers: the thin wall's square sides and underside, the cornice
                      "opening_pilaster": 4.0,                        # the pilasters and their plinths
                      "facade_shell": 4.0, "shell_": 4.0,     # deco round: the shells' flutes (first: prefix match)
                      "floor_lower_sides": 0.6, "facade": 0.8, "entablature": 1.6, "string_course": 1.6,
                      "nave_pilaster_capital": 2.0, "arm2_pilaster_capital": 2.0, "nave_pilaster_base": 1.6,
                      "arm2_pilaster_base": 1.6, "crossing_base": 1.6, "end_entablature": 1.6, "end_door": 1.6,
                      "end_pilaster_base": 1.6, "arch_front_edge": 1.6, "arch_back_edge": 1.6, "bay1_": 1.4,
                      "facade_": 1.4, "drum_base_ring": 1.4, "drum_sill": 1.4, "drum_top_cornice": 1.4,
                      "step_nosing": 2.0, "tondo_frame": 1.4, "crossing_blind_arch": 1.4,
                      # Round 11: the dome's coffers. At 1.0 the lowest ring's step walls (6.6 cm)
                      # and treads (6.5-14 cm) were one or two texels (bake.dome_unwrap); at 3.0
                      # a step wall gets 2-3 texels on every ring.
                      "dome_coffers": 3.0}
BAKE_HALL_X = 7.4                         # m: nothing beyond this behind the facade is seen
BAKE_ISLAND_MAX = 2.5                     # m: longer surfaces are cut into islands this long
BAKE_SKIP = ("ground_beyond",)            # not baked or exported: the web draws it (hall.json "groundBeyond")
GROUND_BEYOND_COLOUR = (0.42, 0.42, 0.33)   # linear, flat and unlit in the web
# Members cut on the lightmap grid even where flat (bake.keeps_flat_whole): their flat faces
# follow plans with breaks and returns, so whole islands would leave the atlas mostly empty.
BAKE_CUT_MEMBERS = ("entablature", "string_course", "capital", "base", "frame", "sill", "impost", "archivolt",
                    "nosing", "edge", "cornice", "ring", "ledge", "triglyph", "blind_arch", "tondo")
BAKE_OCCLUDERS_ONLY = ("_vault_backing",)  # take part in the light, not exported

# ---------------------------------------------------------------- Stage 4: light x detail for the web
# The Bosch's base in the doorway, as the web drew it (Scene.tsx: Bosch 3.255 m x 1.2, base 0.3 m
# wider, 0.75 m tall, 0.6 m deep, front 0.2 m before the painting at END_Z): at 100 %.
BOSCH_BASE = (-3.005, 3.005, 54.6, 55.457, 1.071)   # x0, x1, y0, y1, height
LIGHT_SCALE = 4.0             # the lightmaps store light / LIGHT_SCALE (sRGB-encoded); the web multiplies back
# Detail textures (tools/make_detail.py): px per tile side, and the tint for faces turned to +-X
# (the nave's side walls read buff in the fresco: G-B 27-30, render 17-19).
DETAIL_PX = 1024
SIDE_TINT = (1.0, 1.0, 1.0)   # round 8: white marble (was (1.0, 0.99, 0.88), the fresco's buff side walls)
FRAME_W = 0.16                # width of niche and panel frames (R6)
RELIEF_DEPTH = 0.06           # the facade's relief panels: sunk panels (stage 4: was 0.15)

# Decoration round (Maria, renders/deco-ideas on branch deco-ideas: ideas 3 and 5).
# Shell heads in every niche (blender/scripts/shells.py): flutes across the head, segments per
# flute, rows from rim to hinge, and how far the ridges stand forward (fraction of the radius).
NICHE_SHELL = dict(flutes_facade=11, flutes_recess=9, per_flute=4, rows=8, groove=0.10)
# The facade's sunk panels carry an acanthus scroll in grisaille: detail tile "relief_scroll"
# (tools/relief_scroll.py, through make_detail.py), mapped once over each panel.
RELIEF_SCROLL = True

# Stage 4: the recesses Raphael paints in every bay (as built in bay 1), with empty niches: the
# side walls between the pilasters are set back to RECESS_X the full height; a pier of
# RECESS_PIER stays before the crossing's arches and the end wall.
RECESS_X = BAY1_SIDE_RECESS[2]
RECESS_PIER = 0.8
_W2 = PILASTER_W / 2
NAVE_RECESSES = [(PILASTERS_Y[0] + _W2, PILASTERS_Y[1] - _W2), (PILASTERS_Y[1] + _W2, round(NAVE_Y1 - RECESS_PIER, 3))]
ARM2_RECESSES = [(round(CROSS_Y1 + TRANSVERSE_T + RECESS_PIER, 3), ARM2_PILASTERS_Y[0] - _W2),
                 (ARM2_PILASTERS_Y[0] + _W2, round(ARM2_Y1 - RECESS_PIER, 3))]

# ---------------------------------------------------------------- stage 5: the opening arch
# The fresco's lunette frame (a gold meander on a dark ground) built as the hall's opening arch.
# It is front-parallel, so it projects as a circle. Radii are scan px (3840 wide) round the circle
# fitted to the meander band's edges (15 radial cuts, 8-172 degrees; rms 6 px outer, 5 px inner).
# Every member is placed from those px at its own depth through the camera solve, so its edges
# land on the painted ones and its sides run along Raphael's sight lines (none is painted).
ARCH_Y = round(EYE_Z * F_PX / (IMG_H - CY), 3)   # 4.753: where the fresco's bottom edge meets the floor
ARCH_C = (1915.5, 2021.0)       # circle centre: below the horizon (v 1776), so the arch is segmental
ARCH_SPRING_V = 1771.0          # impost top (painted at v 1765-1775)
ARCH_R = dict(inner=1619.0, meander=(1631.0, 1717.0), pattern=(1638.0, 1711.0), fillet=1733.0,
              beads=(1765.0, 1797.0), egg=(1826.0, 1868.0), outer=1925.0)
ARCH_PROJ = 0.05                # the archivolt (inner band, meander, fillet) stands proud of the wall
ARCH_BAND_PROJ = 0.03           # the outer bands (grey with beads, egg-and-dart, red); R13: >= 2 cm (web)
# The opening arch's intrados (Maria: "the gold-leaf border on the intrados, as in the painting"):
# the meander is the soffit seen in perspective. At the wall's face the opening takes the meander's
# outer edge (ARCH_R meander[1]); the soffit runs back ARCH_DEPTH, so its back edge lands, seen from
# Raphael's eye, on the band's inner edge (ARCH_R inner): D = ARCH_Y (1717 / 1619 - 1). Its axis is
# the sight line through the arch's centre (6.2 deg down, ARCH_INTRADOS_TILT): the back circle then
# projects concentric with the front, and the band keeps its painted width all round.
ARCH_DEPTH = round(ARCH_Y * (ARCH_R["meander"][1] / ARCH_R["inner"] - 1), 4)   # 0.2877: also the front wall's thickness
ARCH_PILASTER_W = 0.255         # painted pilasters: u 165-300 and 3510-3620 (0.28 and 0.23 m), mean
ARCH_PILASTER_D = 0.05
ARCH_IMPOST_H = 0.12            # painted impost and the block under it: v 1770-1830 at the face
ARCH_WALL = (12.0, 9.0)         # front wall: half-width and height (designed; covers the start view on portrait phones, to 8.3 m)
ARCH_MEANDER = dict(periods_half=15, cols=7, rows=7, gold=0.6)   # 7 strips a period (pitch 26.5 px), 7 levels
ARCH_COLOURS = {                # sRGB as seen; started from medians of k-means clusters over each band
    # Round 10 (Maria): the pinks are the wall's cream as it shows beside the arch (218, 209, 183),
    # the thin fillets 10 % lighter (were inner (160, 136, 130), grey (155, 127, 120), egg ground
    # (140, 110, 97), fillet (177, 151, 148)); the yellows clean gold leaf (were gold
    # (172, 122, 64), shade (142, 97, 52), beads (147, 103, 65)), with a sheen in the web
    # (Scene.tsx, ARCH_GOLD). The dark reds stay as painted.
    "inner": (218, 209, 183), "ground": (78, 50, 47), "gold": (194, 150, 62), "gold_shade": (140, 102, 38),
    "fillet": (227, 218, 191), "grey": (218, 209, 183), "bead": (194, 150, 62),
    "egg_ground": (218, 209, 183), "dart": (106, 59, 43), "red": (93, 49, 37)}
ARCH_GOLD = ("gold", "gold_shade", "bead")   # the band tile's alpha marks these (the web's sheen)
