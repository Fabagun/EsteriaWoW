"""Texture atlas padding and filtered-edge checks for the four solid pilot meshes."""
from io import BytesIO
from pathlib import Path
import struct

import numpy as np
from PIL import Image


def pad_islands(image, radius):
    """Extend opaque edge colors and alpha into unused atlas gutters, without wrapping.

    The pilot textures use transparency around UV islands, not as body cutouts.
    Padding alpha as well as RGB prevents alpha-test pinholes along shared mesh edges.
    """
    pixels = np.array(image.convert('RGBA'))
    pixels[pixels[:, :, 3] >= 254, 3] = 255
    height, width = pixels.shape[:2]
    for _ in range(radius):
        previous = np.pad(pixels, ((1, 1), (1, 1), (0, 0)), mode='constant')
        missing = pixels[:, :, 3] < 255
        changed = False
        for dy, dx in [(0, -1), (0, 1), (-1, 0), (1, 0), (-1, -1), (-1, 1), (1, -1), (1, 1)]:
            neighbor = previous[1+dy:1+dy+height, 1+dx:1+dx+width]
            fill = missing & (neighbor[:, :, 3] == 255)
            if np.any(fill):
                pixels[fill] = neighbor[fill]
                missing[fill] = False
                changed = True
        if not changed:
            break
    return Image.fromarray(pixels)


def decode_blp(path, mip=0):
    data = Path(path).read_bytes()
    w, h = struct.unpack_from('<2I', data, 12)
    w, h = max(1,w >> mip), max(1,h >> mip)
    offset = struct.unpack_from('<I',data,20+4*mip)[0]
    size = struct.unpack_from('<I',data,84+4*mip)[0]
    if data[:4] != b'BLP2' or offset < 148 or offset+size > len(data):
        raise ValueError('Invalid BLP mip')
    if data[8] == 3:
        if size != w*h*4 or data[9] != 8:
            raise ValueError('Invalid raw BGRA mip')
        return Image.frombytes('RGBA',(w,h),data[offset:offset+size],'raw','BGRA')
    selected = bytearray(data)
    struct.pack_into('<2I',selected,12,w,h)
    struct.pack_into('<I',selected,20,offset)
    struct.pack_into('<I',selected,84,size)
    return Image.open(BytesIO(selected)).convert('RGBA')


def filtered_edge_alpha(path, uv, triangles):
    """Sample exported UV edges with bilinear filtering at every stored BLP mip."""
    data = Path(path).read_bytes()
    width, height = struct.unpack_from('<2I', data, 12)
    offsets = struct.unpack_from('<16I', data, 20)
    sizes = struct.unpack_from('<16I', data, 84)
    tri_uv = uv[triangles]
    # Include vertices and intermediate edge points, where the reported dots occur.
    times = np.linspace(0, 1, 17)
    samples = np.concatenate([
        ((1-times[None, :, None])*tri_uv[:, i, None, :]
         + times[None, :, None]*tri_uv[:, (i+1) % 3, None, :]).reshape(-1, 2)
        for i in range(3)
    ])
    results = []
    for mip, offset in enumerate(offsets):
        if not offset:
            break
        w, h = max(1, width >> mip), max(1, height >> mip)
        selected = bytearray(data)
        struct.pack_into('<2I', selected, 12, w, h)
        struct.pack_into('<I', selected, 20, offset)
        struct.pack_into('<I', selected, 84, sizes[mip])
        alpha = np.array(decode_blp(path, mip))[:, :, 3].astype(float)
        xy = samples*np.array([w, h])-0.5
        lower = np.floor(xy).astype(int)
        fraction = xy-lower
        x0, y0 = np.clip(lower[:, 0], 0, w-1), np.clip(lower[:, 1], 0, h-1)
        x1, y1 = np.clip(lower[:, 0]+1, 0, w-1), np.clip(lower[:, 1]+1, 0, h-1)
        fx, fy = fraction.T
        filtered = ((1-fy)*((1-fx)*alpha[y0, x0]+fx*alpha[y0, x1])
                    + fy*((1-fx)*alpha[y1, x0]+fx*alpha[y1, x1]))
        # WotLK CM2SceneRender::SetupMaterial uses 224/255 for alpha-key.
        # Keep 16/255 headroom; still report nonopaque samples as diagnostics.
        results.append(dict(mip=mip, minimum_alpha=float(filtered.min()),
                            unsafe_alpha_key_samples=int(np.count_nonzero(filtered < 240)),
                            nonopaque_samples=int(np.count_nonzero(filtered < 254.99))))
    return results
