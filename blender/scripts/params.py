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

