"""Light tests for Maria (2026-11-21): the left wall's volumes read flat. Renders only.
  blender -b blender/athens-hall.blend -P blender/scripts/lighttest/render_light.py -- <variant> <out_dir> [samples]
  variant: base | A (Raphael's tones per face, measured on the fresco) | B (a raking sun, azimuth 20)
"""
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import scene_setup as S  # noqa: E402
P = S.P

variant, out = sys.argv[sys.argv.index("--") + 1:][:2]
samples = int(sys.argv[sys.argv.index("--") + 3]) if len(sys.argv) > sys.argv.index("--") + 3 else 48
out = Path(out)
out.mkdir(parents=True, exist_ok=True)

S.arch_band()
S.hang_paintings()


def raphael_tones():
    """A: on the lit left side, each face its tone, as Raphael paints the left nave wall (fresco
    u 1000-1560, v 1000-1060, linear light): faces turned to the entrance x0.75, faces turned away
    x0.6, recess backs (set back from the wall) x0.82; inner corners a little darker (AO)."""
    wall_x = P.NAVE_HALF_W
    for m in bpy.data.materials:
        if not m.use_nodes or m.get("kind") == "painting" or m.name.startswith(("art_", "frame")):
            continue
        N, L = m.node_tree.nodes, m.node_tree.links
        b = next((n for n in N if n.type == "BSDF_PRINCIPLED"), None)
        if b is None:
            continue
        geo, sn, sp = N.new("ShaderNodeNewGeometry"), N.new("ShaderNodeSeparateXYZ"), N.new("ShaderNodeSeparateXYZ")
        L.new(geo.outputs["Normal"], sn.inputs["Vector"])
        L.new(geo.outputs["Position"], sp.inputs["Vector"])

        def math_node(op, a, bval=None):
            n = N.new("ShaderNodeMath"); n.operation = op
            L.new(a, n.inputs[0]) if not isinstance(a, float) else None
            if isinstance(a, float): n.inputs[0].default_value = a
            if bval is not None:
                if isinstance(bval, float): n.inputs[1].default_value = bval
                else: L.new(bval, n.inputs[1])
            return n.outputs[0]

        # the left nave wall only: within 1.2 m of its plane, past the facade, above the floor
        left = math_node("MULTIPLY", math_node("LESS_THAN", sp.outputs["X"], -(wall_x - 1.2)),
                         math_node("MULTIPLY", math_node("GREATER_THAN", sp.outputs["Y"], P.FACADE_Y1),
                                   math_node("GREATER_THAN", sp.outputs["Z"], P.PLATFORM_Z + 0.05)))
        toward = math_node("LESS_THAN", sn.outputs["Y"], -0.7)          # turned to the entrance
        away = math_node("GREATER_THAN", sn.outputs["Y"], 0.7)
        back = math_node("MULTIPLY", math_node("GREATER_THAN", sn.outputs["X"], 0.7),
                         math_node("LESS_THAN", sp.outputs["X"], -(wall_x + 0.1)))
        # f = 1 - left * (0.25 toward + 0.4 away + 0.18 back)
        s = math_node("ADD", math_node("MULTIPLY", toward, 0.25), math_node("MULTIPLY", away, 0.4))
        s = math_node("ADD", s, math_node("MULTIPLY", back, 0.18))
        f = math_node("SUBTRACT", 1.0, math_node("MULTIPLY", left, s))
        ao = N.new("ShaderNodeAmbientOcclusion"); ao.inputs["Distance"].default_value = 0.6; ao.samples = 8
        aof = math_node("ADD", 0.82, math_node("MULTIPLY", ao.outputs["AO"], 0.18))
        f = math_node("MULTIPLY", f, aof)
        mix = N.new("ShaderNodeMix"); mix.data_type, mix.blend_type = "RGBA", "MULTIPLY"
        mix.inputs[0].default_value = 1.0
        src = b.inputs["Base Color"].links[0].from_socket if b.inputs["Base Color"].links else None
        if src is not None:
            L.new(src, mix.inputs[6])
        else:
            mix.inputs[6].default_value = b.inputs["Base Color"].default_value
        comb = N.new("ShaderNodeCombineColor")
        for k in ("Red", "Green", "Blue"):
            L.new(f, comb.inputs[k])
        L.new(comb.outputs["Color"], mix.inputs[7])
        L.new(mix.outputs[2], b.inputs["Base Color"])


def raking_sun(az_deg=20.0):
    """B: the sun swung towards the left wall (azimuth 39 -> 20 deg; elevation kept)."""
    sun = next(o for o in bpy.data.objects if o.type == "LIGHT" and o.data.type == "SUN")
    az, el = math.radians(az_deg), math.radians(P.SUN_ELEVATION)
    travel = Vector((-math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), -math.sin(el)))
    sun.rotation_euler = travel.to_track_quat("-Z", "Y").to_euler()


if variant == "A":
    raphael_tones()
elif variant == "B":
    raking_sun()

S.setup_render(samples)
cams = S.cameras()
leftwall = S.camera("lt_leftwall", (1.6, 19.0, S.EYE), (-5.9, 29.5, S.EYE + 2.6), 22)
S.render(leftwall, (900, 1200), out / f"{variant}-leftwall.png")
S.render(cams["start"][0], cams["start"][1], out / f"{variant}-start.png")
