"""Pixelmon ModelData transforms expressed in the converter's Z-up source space."""
import math

import numpy as np


def source_matrix(definition):
    # ModelData default: RX(-pi/2). SMDEntityRenderer applies T * RY * RZ * RX * S.
    # Our existing source coordinates are Z-up, so undo the default Minecraft Y-up
    # conversion before applying the normal source-to-WoW conversion.
    angles = np.asarray(definition.get('rotate_angle', [-math.pi/2, 0, 0]), dtype=float)
    offset = np.asarray(definition.get('offsets', [0, 0, 0]), dtype=float)
    scale = np.asarray(definition.get('scale', 1), dtype=float)
    if scale.shape == ():
        scale = np.repeat(scale, 3)
    if (angles.shape != (3,) or offset.shape != (3,) or scale.shape != (3,)
            or not all(np.isfinite(v).all() for v in [angles, offset, scale])):
        raise ValueError('Invalid model transform')
    if np.any(scale <= 0) or not np.allclose(scale, scale[0], atol=0, rtol=1e-7):
        raise ValueError('Nonuniform or reflected model scale requires affine animation support')
    cx, cy, cz = np.cos(angles)
    sx, sy, sz = np.sin(angles)
    rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    undo_default = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]])
    matrix = np.eye(4)
    matrix[:3, :3] = undo_default @ ry @ rz @ rx * scale[0]
    matrix[:3, 3] = undo_default @ offset
    return matrix
