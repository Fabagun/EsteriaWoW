"""Preserve authored alpha for blended materials and verify every pixel/mip against its source."""
import hashlib
from pathlib import Path
import struct
import numpy as np
from PIL import Image

POLICY = 'source_alpha_blend'


def write_alpha_blp(path, source):
    image = Image.open(source).convert('RGBA')
    size = tuple(1 << (n-1).bit_length() for n in image.size)
    if max(size) > 4096:
        raise ValueError('Alpha texture exceeds export size limit')
    if image.size != size:
        image = image.resize(size, Image.Resampling.LANCZOS)
    offsets, lengths, chunks = [0]*16, [0]*16, []
    position = 148+1024
    # Raw BGRA avoids block-compression damage to authored holes and fractional alpha.
    # No alpha dilation is allowed on this path.
    while True:
        raw = image.tobytes('raw', 'BGRA')
        i = len(chunks); offsets[i], lengths[i] = position, len(raw)
        chunks.append(raw); position += len(raw)
        if image.size == (1, 1):
            break
        image = image.resize((max(1, image.width//2), max(1, image.height//2)), Image.Resampling.BOX)
    Path(path).write_bytes(b'BLP2'+struct.pack('<I4B2I', 1, 3, 8, 0, 1, *size)
                          +struct.pack('<16I', *offsets)+struct.pack('<16I', *lengths)
                          +bytes(1024)+b''.join(chunks))


def source_digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_alpha_texture(path, source, expected_hash, uv, triangles):
    if source_digest(source) != expected_hash:
        raise ValueError('Alpha source checksum mismatch')
    image = Image.open(source).convert('RGBA')
    dimensions = tuple(1 << (n-1).bit_length() for n in image.size)
    if image.size != dimensions:
        image = image.resize(dimensions, Image.Resampling.LANCZOS)
    reference_alpha = image.getchannel('A')
    data = Path(path).read_bytes()
    if data[:12] != b'BLP2'+struct.pack('<I4B', 1, 3, 8, 0, 1):
        raise ValueError('Expected lossless BGRA alpha texture')
    if struct.unpack_from('<2I', data, 12) != dimensions:
        raise ValueError('Alpha texture dimensions changed')
    offsets = struct.unpack_from('<16I', data, 20)
    lengths = struct.unpack_from('<16I', data, 84)
    samples = np.concatenate([((1-t)*uv[triangles[:, i]]+t*uv[triangles[:, (i+1)%3]])
                              for i in range(3) for t in np.linspace(0, 1, 17)])
    statistics = []
    for mip in range(max(dimensions).bit_length()):
        w, h = max(1, dimensions[0] >> mip), max(1, dimensions[1] >> mip)
        if lengths[mip] != w*h*4 or offsets[mip] < 1172 or offsets[mip]+lengths[mip] > len(data):
            raise ValueError('Invalid alpha mip payload')
        # Independent raw decoder: writer uses Pillow BGRA serialization.
        actual = np.frombuffer(data, dtype=np.uint8, count=w*h*4, offset=offsets[mip]).reshape(h,w,4)[:,:,[2,1,0,3]]
        wanted_alpha = np.array(reference_alpha)
        if not np.array_equal(actual[:, :, 3], wanted_alpha):
            raise ValueError('Authored alpha changed (hole fill, opacity loss or mip corruption)')
        if not np.array_equal(actual[:, :, :3], np.array(image)[:, :, :3]):
            raise ValueError('Alpha material RGB changed')
        # Source-relative seam check: transparent edges are allowed only where the
        # reference also has them. Opaque edges cannot acquire new transparency.
        xy = samples*np.array([w, h])-.5
        lo = np.floor(xy).astype(int); f = xy-lo
        x0,y0 = np.clip(lo[:,0],0,w-1),np.clip(lo[:,1],0,h-1)
        x1,y1 = np.clip(lo[:,0]+1,0,w-1),np.clip(lo[:,1]+1,0,h-1)
        def filtered(a):
            return ((1-f[:,1])*((1-f[:,0])*a[y0,x0]+f[:,0]*a[y0,x1])
                    +f[:,1]*((1-f[:,0])*a[y1,x0]+f[:,0]*a[y1,x1]))
        error = float(np.max(np.abs(filtered(actual[:,:,3].astype(float))
                                        -filtered(wanted_alpha.astype(float)))))
        if error != 0:
            raise ValueError('Unexpected alpha discontinuity on UV edge')
        statistics.append(dict(mip=mip, max_edge_error=error,
                               transparent_pixels=int(np.count_nonzero(wanted_alpha==0)),
                               fractional_pixels=int(np.count_nonzero((wanted_alpha>0)&(wanted_alpha<255)))))
        next_size = (max(1,w//2),max(1,h//2))
        reference_alpha = reference_alpha.resize(next_size, Image.Resampling.BOX)
        image = image.resize(next_size, Image.Resampling.BOX)
    if any(offsets[len(statistics):]) or any(lengths[len(statistics):]):
        raise ValueError('Unexpected extra alpha mips')
    return statistics
