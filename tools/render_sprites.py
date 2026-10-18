"""Render the drone archetypes from every viewing angle into sprite tiles (run with a Blender Python).

    <python with bpy> tools/render_sprites.py <out_dir>

Models are built from primitives at true size (metres), nose along +Y, up +Z. The camera is orthographic
at a known scale, so the OASIS camera can resize each tile to the object's true pixel size. Tiles are
named <shape>/az{az:03d}_el{el:+03d}.png: az = aspect (camera bearing seen from the drone, clockwise from
the nose), el = camera elevation seen from the drone (negative = looking up at the belly).
"""
import json
import math
import sys
from pathlib import Path

import bpy  # noqa: I001 (bpy must load before bmesh)
import bmesh

OUT = Path(sys.argv[-1])
AZ = list(range(0, 360, 15))
EL = list(range(-60, 61, 15))
TILE, MARGIN = 128, 1.15


def material(name, rgb, rough=0.55, metal=0.1):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    return m


def prim(kind, size, loc=(0, 0, 0), rot=(0, 0, 0), mat=None, **kw):
    getattr(bpy.ops.mesh, f"primitive_{kind}_add")(location=loc, rotation=rot, **kw)
    ob = bpy.context.active_object
    ob.scale = size
    if mat:
        ob.data.materials.append(mat)
    return ob


def poly(verts, thickness, mat, z=0.0):
    """Flat planform (x, y) extruded to a thin slab: wings."""
    me = bpy.data.meshes.new("wing")
    bm = bmesh.new()
    face = bm.faces.new([bm.verts.new((x, y, z)) for x, y in verts])
    ext = bmesh.ops.extrude_face_region(bm, geom=[face])
    bmesh.ops.translate(bm, vec=(0, 0, thickness), verts=[v for v in ext["geom"] if isinstance(v, bmesh.types.BMVert)])
    bm.to_mesh(me)
    ob = bpy.data.objects.new("wing", me)
    bpy.context.collection.objects.link(ob)
    ob.data.materials.append(mat)
    return ob


def build(shape):
    body, dark, prop = material("body", (0.32, 0.33, 0.30)), material("dark", (0.06, 0.06, 0.07)), material("prop", (0.1, 0.1, 0.1))
    if shape == "quad":  # X-frame quadcopter, 0.38 m motor-to-motor class
        prim("cube", (0.07, 0.11, 0.035), mat=body)
        prim("cube", (0.03, 0.02, 0.02), loc=(0, 0.12, -0.01), mat=dark)  # camera gimbal
        for sx, sy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
            ang = math.atan2(sy, sx)
            prim("cube", (0.11, 0.012, 0.01), loc=(sx * 0.075, sy * 0.075, 0), rot=(0, 0, ang), mat=body)
            prim("cylinder", (0.02, 0.02, 0.025), loc=(sx * 0.135, sy * 0.135, 0.02), mat=dark)
            prim("cylinder", (0.085, 0.085, 0.002), loc=(sx * 0.135, sy * 0.135, 0.045), mat=prop)
        span = 0.38
    elif shape == "delta":  # one-way delta wing, 2.5 m span, 3.5 m long, pusher prop, winglet fins
        poly([(0, 1.6), (1.25, -1.2), (0.35, -1.0), (0, -1.1), (-0.35, -1.0), (-1.25, -1.2)], 0.08, body)
        prim("cylinder", (0.16, 0.16, 1.6), loc=(0, 0.05, 0.08), rot=(math.pi / 2, 0, 0), mat=body)
        prim("cone", (0.16, 0.16, 0.25), loc=(0, 1.8, 0.08), rot=(-math.pi / 2, 0, 0), mat=body)
        for sx in (1, -1):
            poly([(sx * 1.2, -1.2), (sx * 1.25, -0.75), (sx * 1.25, -1.2)], 0.0, dark, z=0.08)
            fin = prim("cube", (0.01, 0.22, 0.2), loc=(sx * 1.22, -1.0, 0.25), mat=dark)
        prim("cylinder", (0.38, 0.38, 0.01), loc=(0, -1.65, 0.08), rot=(math.pi / 2, 0, 0), mat=prop)
        span = 2.5
    else:  # fixed-wing reconnaissance: straight wing, boom, tail, pusher prop (3.1 m class)
        prim("cylinder", (0.12, 0.12, 0.9), loc=(0, 0.2, 0), rot=(math.pi / 2, 0, 0), mat=body)
        prim("cube", (1.55, 0.16, 0.02), loc=(0, 0.3, 0.06), mat=body)
        prim("cylinder", (0.025, 0.025, 0.7), loc=(0, -1.15, 0.03), rot=(math.pi / 2, 0, 0), mat=dark)
        prim("cube", (0.4, 0.09, 0.012), loc=(0, -1.8, 0.05), mat=body)
        prim("cube", (0.01, 0.1, 0.16), loc=(0, -1.8, 0.2), mat=body)
        prim("cylinder", (0.2, 0.2, 0.008), loc=(0, -0.72, 0.0), rot=(math.pi / 2, 0, 0), mat=prop)
        span = 3.1
    return span


def setup(span):
    scn = bpy.context.scene
    scn.render.engine = "CYCLES"
    scn.cycles.samples = 24
    try:  # GPU when there is one (Metal on Apple silicon, OptiX/CUDA on Linux), else CPU
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for kind in ("METAL", "OPTIX", "CUDA"):
            try:
                prefs.compute_device_type = kind
                prefs.get_devices()
                if any(d.type != "CPU" for d in prefs.devices):
                    for d in prefs.devices:
                        d.use = True
                    scn.cycles.device = "GPU"
                    break
            except TypeError:
                continue
    except Exception as exc:  # rendering still works on CPU; say so instead of hiding it
        print(f"GPU setup failed, rendering on CPU: {exc}", file=sys.stderr)
    scn.render.resolution_x = scn.render.resolution_y = TILE
    scn.render.film_transparent = True
    scn.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("sky")
    scn.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.55, 0.58, 0.62, 1)  # overcast sky
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0
    bpy.ops.object.light_add(type="SUN", rotation=(0.3, 0.2, 0))
    bpy.context.active_object.data.energy = 1.5
    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = span * MARGIN
    cam = bpy.data.objects.new("cam", cam_data)
    bpy.context.collection.objects.link(cam)
    scn.camera = cam
    target = bpy.data.objects.new("target", None)
    bpy.context.collection.objects.link(target)
    con = cam.constraints.new("TRACK_TO")
    con.target, con.track_axis, con.up_axis = target, "TRACK_NEGATIVE_Z", "UP_Y"
    return scn, cam


def main():
    index = {}
    for shape in ("quad", "delta", "fixed_wing"):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        span = build(shape)
        scn, cam = setup(span)
        folder = OUT / shape
        folder.mkdir(parents=True, exist_ok=True)
        dist = span * 6
        for el in EL:
            for az in AZ:
                a, e = math.radians(az), math.radians(el)
                cam.location = (dist * math.sin(a) * math.cos(e), dist * math.cos(a) * math.cos(e), dist * math.sin(e))
                scn.render.filepath = str(folder / f"az{az:03d}_el{el:+03d}.png")
                bpy.ops.render.render(write_still=True)
        index[shape] = {"span_m": span, "ortho_m": span * MARGIN, "tile_px": TILE, "az": AZ, "el": EL}
        print(f"{shape}: {len(AZ) * len(EL)} tiles", flush=True)
    (OUT / "index.json").write_text(json.dumps(index, indent=1))


main()
