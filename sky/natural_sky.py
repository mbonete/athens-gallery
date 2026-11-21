"""Render a physical clear sky (Blender's multiple-scattering model) with its sun where the hall's
bake puts the sun, and measure how much light that sun gives a white card compared with the bake's
own sun lamp, so the sky can be shown at the bake's exposure.
  blender -b --factory-startup -P natural_sky.py -- <params_dir> <out_dir> <aerosol> [width]
Writes <out_dir>/sky.exr (equirect, centre = +Y forward, +X right) and <out_dir>/scale.txt."""
import bpy, math, sys
from mathutils import Vector
a = sys.argv[sys.argv.index("--") + 1:]
sys.path.insert(0, a[0]); import params as P
out, aerosol = a[1], float(a[2]); W = int(a[3]) if len(a) > 3 else 4096
sc = bpy.context.scene
for ob in list(bpy.data.objects): bpy.data.objects.remove(ob)
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.use_denoising = False
sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"
sc.render.image_settings.file_format = "OPEN_EXR"; sc.render.image_settings.color_depth = "32"
az, el = math.radians(P.SUN_AZIMUTH), math.radians(P.SUN_ELEVATION)
to_sun = Vector((math.cos(el) * math.cos(az), -math.cos(el) * math.sin(az), math.sin(el)))
rot = math.atan2(to_sun.x, to_sun.y)            # the sky node turns its sun from +Y towards +X
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
nt = w.node_tree; bg = nt.nodes["Background"]
sky = nt.nodes.new("ShaderNodeTexSky"); sky.sky_type = "MULTIPLE_SCATTERING"
sky.sun_elevation, sky.sun_rotation = el, rot
sky.altitude = 30.0; sky.air_density = 1.0; sky.aerosol_density = aerosol; sky.ozone_density = 1.0
sky.sun_size = math.radians(0.545); sky.sun_intensity = 1.0
nt.links.new(sky.outputs[0], bg.inputs[0])
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam

def card_value():
    """Mean value of a white diffuse card facing the sun, seen head-on."""
    sc.render.resolution_x = sc.render.resolution_y = 32; sc.cycles.samples = 2048
    cam.data.type = "ORTHO"; cam.data.ortho_scale = 0.5
    cam.location = to_sun * 5; cam.rotation_euler = (-to_sun).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = out + "/card.exr"; bpy.ops.render.render(write_still=True)
    im = bpy.data.images.load(out + "/card.exr", check_existing=False); px = list(im.pixels)
    n = len(px) // 4; v = [sum(px[i * 4 + c] for i in range(n)) / n for c in range(3)]
    bpy.data.images.remove(im); return v

bpy.ops.mesh.primitive_plane_add(size=4, location=(0, 0, 0))
card = bpy.context.object; card.rotation_euler = to_sun.to_track_quat("Z", "Y").to_euler()
m = bpy.data.materials.new("white"); m.use_nodes = True
m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (1, 1, 1, 1)
m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 1.0
card.data.materials.append(m)
sky.sun_disc = True; with_sun = card_value()
sky.sun_disc = False; no_sun = card_value()
model_sun = [x - y for x, y in zip(with_sun, no_sun)]
# The bake's sun lamp alone, black world.
nt.links.remove(bg.inputs[0].links[0]); bg.inputs[0].default_value = (0, 0, 0, 1)
lamp = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sc.collection.objects.link(lamp)
lamp.rotation_euler = (-to_sun).to_track_quat("-Z", "Y").to_euler()
lamp.data.energy = P.SUN_STRENGTH; lamp.data.angle = math.radians(P.SUN_ANGLE); lamp.data.color = P.SUN_COLOR
bake_sun = card_value()
scale = sum(bake_sun) / sum(model_sun)
open(out + "/scale.txt", "w").write(f"{scale}\nmodel_sun {model_sun}\nbake_sun {bake_sun}\nrot_deg {math.degrees(rot)}\n")
print("[sky] scale", scale, "model_sun", model_sun, "bake_sun", bake_sun)
# The sky itself, no sun disc, equirect.
bpy.data.objects.remove(lamp); bpy.data.objects.remove(card)
nt.links.new(sky.outputs[0], bg.inputs[0]); sky.sun_disc = False
cam.data.type = "PANO"; cam.data.panorama_type = "EQUIRECTANGULAR"
cam.location = (0, 0, 0); cam.rotation_euler = (math.radians(90), 0, 0)
sc.render.resolution_x, sc.render.resolution_y = W, W // 2; sc.cycles.samples = 16
sc.render.filepath = out + "/sky.exr"; bpy.ops.render.render(write_still=True)
