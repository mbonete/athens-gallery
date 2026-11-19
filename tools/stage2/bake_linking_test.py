"""Bake check (stage 2): does a Cycles bake honour light linking? Run: blender -b -P bake_linking_test.py -- x"""
"""Does a Cycles bake honour light linking (shadow linking)? A floor plane under a box, a sun straight down.
Bake the floor's diffuse direct light twice: box blocks the sun / box is excluded from the sun's blockers.
Also a receiver-linking test: a second sun linked to receive only on the box."""
import bpy, bmesh, sys
from mathutils import Vector
out = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.samples = 16; sc.cycles.device = "CPU"
def mesh(name, verts, faces, uv=True):
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
    if uv:
        me.uv_layers.new(name="uv")
        for loop in me.loops:
            co = me.vertices[loop.vertex_index].co
            me.uv_layers[0].data[loop.index].uv = ((co.x + 2) / 4, (co.y + 2) / 4)
    ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob)
    m = bpy.data.materials.new(name); m.use_nodes = True; me.materials.append(m)
    return ob
floor = mesh("floor", [(-2, -2, 0), (2, -2, 0), (2, 2, 0), (-2, 2, 0)], [(0, 1, 2, 3)])
bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0); bmesh.ops.translate(bm, verts=bm.verts[:], vec=(0, 0, 1.0))
me = bpy.data.meshes.new("box"); bm.to_mesh(me); bm.free(); box = bpy.data.objects.new("box", me); sc.collection.objects.link(box)
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sun.data.energy = 3; sc.collection.objects.link(sun)
sc.world = bpy.data.worlds.new("w"); sc.world.use_nodes = True; sc.world.node_tree.nodes["Background"].inputs[1].default_value = 0.0
img = bpy.data.images.new("bake", 64, 64, float_buffer=True)
nt = floor.data.materials[0].node_tree; tn = nt.nodes.new("ShaderNodeTexImage"); tn.image = img; nt.nodes.active = tn
for o in sc.objects: o.select_set(o is floor)
bpy.context.view_layer.objects.active = floor
sc.render.bake.use_pass_direct, sc.render.bake.use_pass_indirect, sc.render.bake.use_pass_color = True, False, False
def bake(tag):
    bpy.ops.object.bake(type="DIFFUSE")
    px = list(img.pixels)
    c = (32 * 64 + 32) * 4; e = (4 * 64 + 4) * 4
    print(f"{tag}: centre (under the box) {px[c]:.3f}  corner (open) {px[e]:.3f}")
bake("plain sun")
col = bpy.data.collections.new("not_blocking"); col.objects.link(box)
for co in col.collection_objects: co.light_linking.link_state = "EXCLUDE"
sun.light_linking.blocker_collection = col
bake("shadow-linked sun (box excluded from blockers)")
rc = bpy.data.collections.new("receivers"); rc.objects.link(box)
for co in rc.collection_objects: co.light_linking.link_state = "EXCLUDE"
sun.light_linking.blocker_collection = None
sun.light_linking.receiver_collection = None
rc2 = bpy.data.collections.new("recv_floor_excluded"); rc2.objects.link(floor)
for co in rc2.collection_objects: co.light_linking.link_state = "EXCLUDE"
sun.light_linking.receiver_collection = rc2
bake("receiver-linked sun (floor excluded)")
