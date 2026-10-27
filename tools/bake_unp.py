"""Runs inside Blender (background) on Grognak's StencilTool.blend: adds the BHUNP (UNP layout) body, hands and feet
read by tools/nif_geom.py, wraps each onto its CBBE counterpart so the two surfaces coincide while every vertex
keeps its UNP UVs, then bakes coordinate maps between the CBBE (3BA) and UNP layouts both ways.
blender -b StencilTool.blend --python bake_unp.py -- <res> <out_dir> <unp_npz_dir> <wrap: NEAREST_SURFACEPOINT|PROJECT> [single] [align]
The release maps use NEAREST_SURFACEPOINT single (round trip ~0.45 px at 4K, vs ~2 px median / 16 px tail with a wrap per direction).
UNP <-> UBE maps are composed from these and the 3BA <-> UBE ones in tools/pack_maps.py, so UBE needs no second fit."""
import math
import os
import sys

import bmesh
import bpy
import numpy as np

args = sys.argv[sys.argv.index('--') + 1:]
res, out_dir, npz_dir, wrap = int(args[0]), args[1], args[2], args[3]
align_only = 'align' in args[4:]
single = 'single' in args[4:]  # one wrap for both directions: the maps are exact inverses, like Grognak's pair
os.makedirs(out_dir, exist_ok=True)

PAIRS = {'body': 'Base_Mesh', 'hands': 'Base_Hands', 'feet': 'Base_Feet'}

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.render.bake.use_selected_to_active = True
scene.render.bake.target = 'IMAGE_TEXTURES'
scene.render.bake.cage_extrusion = 0.04
scene.render.bake.max_ray_distance = 0.04
scene.render.bake.margin = 1
scene.render.bake.margin_type = 'ADJACENT_FACES'
scene.render.bake.use_clear = False
scene.cycles.samples = 1
scene.display_settings.display_device = 'sRGB'
scene.view_settings.view_transform = 'Standard'
cprefs = bpy.context.preferences.addons['cycles'].preferences
for backend in ('OPTIX', 'CUDA'):
    try:
        cprefs.compute_device_type = backend
        cprefs.get_devices()
        if any(d.type == backend for d in cprefs.devices):
            for d in cprefs.devices:
                d.use = d.type == backend
            scene.cycles.device = 'GPU'
            break
    except Exception:
        pass


def add_unp(part):
    """NIF units -> the scene's (x0.1, turned 180 deg like Grognak's meshes); NIF v is top-down, Blender's bottom-up."""
    z = np.load(os.path.join(npz_dir, f'bhunp_{part}.npz'))
    verts, uvs, tris = z['verts'] * 0.1, z['uvs'], z['tris']
    me = bpy.data.meshes.new(f'UNP_{part}')
    me.from_pydata(verts.tolist(), [], tris.tolist())
    uv_layer = me.uv_layers.new(name='UVMap')
    loop_uv = uvs[tris.reshape(-1)]
    loop_uv[:, 1] = 1.0 - loop_uv[:, 1]
    uv_layer.data.foreach_set('uv', loop_uv.astype(np.float32).ravel())
    me.validate()
    obj = bpy.data.objects.new(f'UNP_{part}', me)
    obj.rotation_euler = bpy.data.objects[PAIRS[part]].rotation_euler.copy()
    bpy.context.scene.collection.objects.link(obj)
    # A copy of the CBBE counterpart's material: a fresh Principled BSDF bakes the ramp ~4 % darker (its default
    # specular takes energy from diffuse), which shifted every UNP-sourced coordinate by ~25 texels at 1K.
    mat = bpy.data.objects[PAIRS[part]].data.materials[0].copy()
    mat.name = f'UNP_{part}_Material'
    me.materials.append(mat)
    return obj


def world_bbox(obj):
    m = np.array(obj.matrix_world)
    co = np.empty(len(obj.data.vertices) * 3, np.float32)
    obj.data.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3) @ m[:3, :3].T + m[:3, 3]
    return co.min(0), co.max(0)


def wrap_onto(obj, target):
    mod = obj.modifiers.new('wrap', 'SHRINKWRAP')
    mod.target = target
    mod.wrap_method = wrap
    if wrap == 'PROJECT':
        mod.use_negative_direction = True
        mod.use_positive_direction = True
        mod.use_project_z = False
        mod.project_limit = 1.0
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=mod.name)


def duplicate(obj):
    """A copy with its own mesh and material, so wrapping and bake targets never touch the original."""
    dup = obj.copy()
    dup.data = obj.data.copy()
    dup.data.materials[0] = obj.data.materials[0].copy()
    dup.name = obj.name + '_wrapped'
    bpy.context.scene.collection.objects.link(dup)
    return dup


def image_node(obj):
    mat = obj.data.materials[0]
    return mat, next(n for n in mat.node_tree.nodes if n.type == 'TEX_IMAGE')


ramp_img = bpy.data.images.new('UVRamp', width=res, height=res, alpha=False, float_buffer=True)
ramp_img.colorspace_settings.name = 'Non-Color'
u = (np.arange(res, dtype=np.float32) + 0.5) / res
ramp = np.ones((res, res, 4), dtype=np.float32)
ramp[..., 0] = u[None, :]
ramp[..., 1] = u[:, None]
ramp_img.pixels.foreach_set(ramp.ravel())


def bake_once(src, dst):
    _m, src_node = image_node(src)
    dst_mat, dst_node = image_node(dst)
    src_node.image = ramp_img
    src_node.interpolation = 'Linear'
    bake = bpy.data.images.new('UVBake', width=res, height=res, alpha=True, float_buffer=True)
    bake.colorspace_settings.name = 'Non-Color'
    bake.generated_color = (0.0, 0.0, 0.0, 0.0)
    dst_node.image = bake
    for n in dst_mat.node_tree.nodes:  # Blender skips the bake silently unless the target node is selected
        n.select = n == dst_node
    dst_mat.node_tree.nodes.active = dst_node
    bpy.ops.object.select_all(action='DESELECT')
    src.select_set(True)
    dst.select_set(True)
    bpy.context.view_layer.objects.active = dst
    bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'}, use_selected_to_active=True, target='IMAGE_TEXTURES')
    px = np.empty(res * res * 4, dtype=np.float32)
    bake.pixels.foreach_get(px)
    bpy.data.images.remove(bake)
    px = px.reshape(res, res, 4)[::-1]
    return np.stack([px[..., 0], 1.0 - px[..., 1], px[..., 2]], axis=-1)


def flip_normals(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()


def bake_both_passes(src, dst):
    """Normal pass, then a pass with the target flipped to fill what inverted normals left empty."""
    m = bake_once(src, dst)
    flip_normals(dst)
    m2 = bake_once(src, dst)
    flip_normals(dst)
    hole = (m[..., 2] <= 0.5) & (m2[..., 2] > 0.5)
    m[hole] = m2[hole]
    return m


for part, cbbe_name in PAIRS.items():
    cbbe = bpy.data.objects[cbbe_name]
    unp = add_unp(part)
    bpy.context.view_layer.update()  # matrix_world of a new object is stale until the depsgraph updates
    lo_c, hi_c = world_bbox(cbbe)
    lo_u, hi_u = world_bbox(unp)
    print('ALIGN', part, 'cbbe', lo_c.round(2), hi_c.round(2), '| unp', lo_u.round(2), hi_u.round(2), flush=True)
    if align_only:
        continue
    # Nearest-surface wrapping is only well defined one way (larger UNP shapes fold when laid onto CBBE), so each
    # direction gets its own copy: the TARGET is wrapped onto the untouched source and keeps its own UVs.
    unp_on_cbbe = duplicate(unp)
    wrap_onto(unp_on_cbbe, cbbe)
    cbbe_on_unp = duplicate(cbbe)
    wrap_onto(cbbe_on_unp, unp)
    rev_pair = (unp_on_cbbe, cbbe) if single else (unp, cbbe_on_unp)
    for name, src, dst in ((f'3ba_{part}-unp_{part}', cbbe, unp_on_cbbe), (f'unp_{part}-3ba_{part}',) + rev_pair):
        m = bake_both_passes(src, dst)
        path = os.path.join(out_dir, f'{name}_{res}.npy')
        np.save(path, m)
        print('UVMAP', name, path, 'covered', float((m[..., 2] > 0.5).mean()), flush=True)
