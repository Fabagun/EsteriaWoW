"""Read Pixelmon BMD v1 and XZ-compressed v2 (big-endian SMD data)."""
from pathlib import Path
import lzma
import struct

import numpy as np


class Reader:
    def __init__(self, data):
        self.data = data
        self.pos = 0

    def unpack(self, fmt):
        size = struct.calcsize('>' + fmt)
        if self.pos + size > len(self.data):
            raise ValueError('Truncated BMD')
        result = struct.unpack_from('>' + fmt, self.data, self.pos)
        self.pos += size
        return result[0] if len(result) == 1 else result

    def string(self):
        chars = []
        while True:
            c = self.unpack('H')
            if not c:
                return ''.join(chars)
            chars.append(chr(c))


def read_bmd(path):
    data = Path(path).read_bytes()
    if not data:
        raise ValueError('Empty BMD')
    if data[0] == 2:
        # Pixelmon consumes declared BMD records without reading XZ through EOF.
        # Some shipped files contain the complete payload but no stream footer.
        # Decode available bytes, then require the entire BMD structure below.
        decoder = lzma.LZMADecompressor()
        data = decoder.decompress(data[1:], max_length=64*1024*1024)
        if not decoder.needs_input and not decoder.eof:
            raise ValueError('BMD decompression limit exceeded')
        if decoder.unused_data:
            raise ValueError('Unexpected data after BMD compressed stream')
    elif data[0] == 1:
        data = data[1:]
    else:
        raise ValueError(f'Unsupported BMD version: {path}')
    r = Reader(data)
    count = r.unpack('H')
    bones = [None] * count
    for _ in range(count):
        index, parent = r.unpack('hh')
        name = r.string()
        if not 0 <= index < count or bones[index] is not None or not -1 <= parent < count:
            raise ValueError('Invalid bone index')
        bones[index] = (name, parent)
    frames = []
    previous = np.full((count, 6), np.nan)
    for _ in range(r.unpack('H')):
        frame = previous.copy()
        for _ in range(r.unpack('H')):
            index = r.unpack('H')
            if index >= count:
                raise ValueError('Invalid animation bone index')
            frame[index] = r.unpack('6f')
        if not np.isfinite(frame).all():
            raise ValueError('Missing initial bone transform')
        frames.append(frame)
        previous = frame
    materials = [r.string() for _ in range(r.unpack('H'))]
    vertices, faces, weights = [], [], []
    for _ in range(r.unpack('H')):
        material = r.unpack('B')
        if material >= len(materials):
            raise ValueError('Invalid material')
        triangle = []
        for _ in range(3):
            parent = r.unpack('h')
            vertex = r.unpack('8f')
            if not np.isfinite(vertex).all():
                raise ValueError('Non-finite vertex')
            links = [r.unpack('hf') for _ in range(r.unpack('B'))]
            if not links:
                links = [(parent, 1.0)]
            if any(b < 0 or b >= count or not np.isfinite(w) or w < 0 for b, w in links):
                raise ValueError('Invalid vertex weight')
            triangle.append(len(vertices))
            vertices.append(vertex)
            weights.append(links)
        faces.append((material, triangle))
    if r.pos != len(data):
        raise ValueError(f'Unexpected BMD trailing bytes: {len(data) - r.pos}')
    return dict(bones=bones, frames=np.array(frames), vertices=np.array(vertices), weights=weights,
                faces=faces, materials=materials)


if __name__ == '__main__':
    import sys
    for filename in sys.argv[1:]:
        model = read_bmd(filename)
        print(Path(filename).name, 'bones', len(model['bones']), 'frames', len(model['frames']),
              'triangles', len(model['faces']), 'materials', model['materials'])
        if len(model['vertices']):
            print('bounds', model['vertices'][:, :3].min(axis=0), model['vertices'][:, :3].max(axis=0))
        print('root transforms', model['frames'][0, :2])
