"""Blender: dump world-space vertices + per-vertex UV of Grognak's CBBE meshes, and of the BHUNP meshes as bake_unp.py
places them, to <out_dir>/<name>.npz (verts, uvs top-down) for numpy-side checks."""
import os
import sys

import bpy
import numpy as np

out_dir = sys.argv[sys.argv.index('--') + 1]
npz_dir = sys.argv[sys.argv.index('--') + 2]
os.makedirs(out_dir, exist_ok=True)


def dump(obj, name):
    bpy.context.view_layer.update()
    m = np.array(obj.matrix_world)
    me = obj.data
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3) @ m[:3, :3].T + m[:3, 3]
    vi = np.empty(len(me.loops), np.int32)
    me.loops.foreach_get('vertex_index', vi)
    uv = np.empty(len(me.loops) * 2, np.float32)
    me.uv_layers.active.data.foreach_get('uv', uv)
    uv = uv.reshape(-1, 2)
    per_v = np.zeros((len(me.vertices), 2), np.float32)
    per_v[vi] = uv
    per_v[:, 1] = 1.0 - per_v[:, 1]
    np.savez(os.path.join(out_dir, name + '.npz'), verts=co, uvs=per_v)
    print('DUMP', name, co.min(0).round(2), co.max(0).round(2))


for obj_name, name in (('Base_Mesh', 'cbbe_body'), ('Base_Hands', 'cbbe_hands'), ('Base_Feet', 'cbbe_feet')):
    dump(bpy.data.objects[obj_name], name)
rot = bpy.data.objects['Base_Mesh'].rotation_euler
for part in ('body', 'hands', 'feet'):
    z = np.load(os.path.join(npz_dir, f'bhunp_{part}.npz'))
    me = bpy.data.meshes.new(part)
    me.from_pydata((z['verts'] * 0.1).tolist(), [], z['tris'].tolist())
    lay = me.uv_layers.new(name='UVMap')
    luv = z['uvs'][z['tris'].reshape(-1)].copy()
    luv[:, 1] = 1.0 - luv[:, 1]
    lay.data.foreach_set('uv', luv.ravel())
    obj = bpy.data.objects.new('UNP_' + part, me)
    obj.rotation_euler = rot.copy()
    bpy.context.scene.collection.objects.link(obj)
    dump(obj, 'unp_' + part)
