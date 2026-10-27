"""Runs inside Blender (background) on Grognak's StencilTool.blend and bakes coordinate maps in both directions:
for every texel of the target UV layout, which position of the source UV layout lands there.
blender -b StencilTool.blend --python bake_maps.py -- <res> <out_dir> [name ...]
Output per map: <out_dir>/<name>_<res>.npy, float32 [res, res, 3] top-down rows: (src_u, src_v_top, covered).
Generalised from the one-way 3BA -> UBE bake so UBE -> 3BA works too."""
import os
import sys

import bmesh
import bpy
import numpy as np

# name: (source object, target object). 3BA = CBBE UVs; vanilla head UVs for the face.
MAPS = {
    '3ba_body-ube': ('Base_Mesh', 'New_Mesh'),
    '3ba_hands-ube': ('Base_Hands', 'New_Mesh'),
    '3ba_feet-ube': ('Base_Feet', 'New_Mesh'),
    '3ba_head-ube_head': ('Base_Head', 'New_Head'),
    'ube-3ba_body': ('New_Mesh', 'Base_Mesh'),
    'ube-3ba_hands': ('New_Mesh', 'Base_Hands'),
    'ube-3ba_feet': ('New_Mesh', 'Base_Feet'),
    'ube_head-3ba_head': ('New_Head', 'Base_Head'),
}

args = sys.argv[sys.argv.index('--') + 1:]
res, out_dir, names = int(args[0]), args[1], args[2:] or list(MAPS)
os.makedirs(out_dir, exist_ok=True)

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
device = 'CPU'
for backend in ('OPTIX', 'CUDA'):
    try:
        cprefs.compute_device_type = backend
        cprefs.get_devices()
        if any(d.type == backend for d in cprefs.devices):
            for d in cprefs.devices:
                d.use = d.type == backend
            device = 'GPU'
            break
    except Exception:
        pass
scene.cycles.device = device
print('BAKE device', device)


def image_node(obj):
    mat = obj.data.materials[0]
    return mat, next(n for n in mat.node_tree.nodes if n.type == 'TEX_IMAGE')


# source: a linear ramp, R = u, G = v (Blender rows, bottom-up), B = 1 marks "something was hit"
ramp_img = bpy.data.images.new('UVRamp', width=res, height=res, alpha=False, float_buffer=True)
ramp_img.colorspace_settings.name = 'Non-Color'
u = (np.arange(res, dtype=np.float32) + 0.5) / res
ramp = np.ones((res, res, 4), dtype=np.float32)
ramp[..., 0] = u[None, :]
ramp[..., 1] = u[:, None]
ramp_img.pixels.foreach_set(ramp.ravel())

def bake_once(src, dst):
    _src_mat, src_node = image_node(src)
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
    px = px.reshape(res, res, 4)[::-1]  # bottom-up -> top-down rows
    return np.stack([px[..., 0], 1.0 - px[..., 1], px[..., 2]], axis=-1)  # src v converted to top-down too


def flip_normals(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()


for name in names:
    src_name, dst_name = MAPS[name]
    src, dst = bpy.data.objects[src_name], bpy.data.objects[dst_name]
    m = bake_once(src, dst)
    if name.startswith('ube'):
        # the CBBE feet (and patches elsewhere) have inverted normals, so their rays start inside and miss:
        # a second pass with the target flipped fills only what the first one left empty
        flip_normals(dst)
        m2 = bake_once(src, dst)
        flip_normals(dst)
        hole = (m[..., 2] <= 0.5) & (m2[..., 2] > 0.5)
        m[hole] = m2[hole]
    path = os.path.join(out_dir, f'{name}_{res}.npy')
    np.save(path, m)
    print('UVMAP', name, path, 'covered', float((m[..., 2] > 0.5).mean()), flush=True)
