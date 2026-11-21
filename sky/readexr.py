# Blender-side: load an EXR and save it as a .npy (float32, H x W x 3, row 0 = top).
import bpy, numpy as np, sys
a = sys.argv[sys.argv.index("--") + 1:]
im = bpy.data.images.load(a[0]); W, H = im.size
px = np.empty(W * H * 4, np.float32); im.pixels.foreach_get(px)
np.save(a[1], px.reshape(H, W, 4)[::-1, :, :3].copy())
