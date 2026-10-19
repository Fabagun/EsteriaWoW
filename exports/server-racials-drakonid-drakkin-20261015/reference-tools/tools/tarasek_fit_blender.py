"""Fit donor garment surfaces against bare Tarasek anatomy in a fresh headless Blender scene."""
import json
from pathlib import Path
import sys

from mathutils import Vector
from mathutils.bvhtree import BVHTree

root = Path(sys.argv[sys.argv.index('--') + 1])
work = json.loads((root / 'fit-work.json').read_text())
body = BVHTree.FromPolygons([Vector(v['position']) for v in work['target']], work['body'], all_triangles=True)
vertices = work['donor']

def raw_envelope(z):
    hits = []
    for tri in work['robe_body']:
        points = [work['target'][v]['position'] for v in tri]
        for a, b in zip(points, points[1:] + points[:1]):
            if (a[2] - z) * (b[2] - z) <= 0 and abs(a[2] - b[2]) > 1e-6:
                t = (z - a[2]) / (b[2] - a[2])
                hits.append([a[i] + t * (b[i] - a[i]) for i in (0, 1)])
    if not hits:
        return None
    return (min(p[0] for p in hits), max(p[0] for p in hits), max(abs(p[1]) for p in hits))


_levels = None


def envelope(z):
    """Smooth skirt envelope: windowed max over height, never narrowing toward the hem, with a gentle flare."""
    global _levels
    if _levels is None:
        top, step = work['waist'] - .15, .04
        zs = [top - step * i for i in range(int((top - .2) / step) + 1)]
        raw = []
        for level in zs:
            samples = [raw_envelope(level + d * .03) for d in range(-4, 5)]
            samples = [s for s in samples if s]
            raw.append((min(s[0] for s in samples), max(s[1] for s in samples),
                        max(s[2] for s in samples)) if samples else None)
        out, last = [], None
        for row in raw:
            if row is None:
                row = last
            elif last:
                row = (min(row[0], last[0]), max(row[1], last[1]), max(row[2], last[2]))
            out.append(row)
            last = row
        smooth = []
        for i, row in enumerate(out):
            near = [out[j] for j in range(max(0, i - 2), min(len(out), i + 3)) if out[j]]
            smooth.append(tuple(sum(r[k] for r in near) / len(near) for k in range(3)) if near else None)
        # smoothing may shrink below the monotone bound; re-clamp
        final, last = [], None
        for row in smooth:
            if row and last:
                row = (min(row[0], last[0]), max(row[1], last[1]), max(row[2], last[2]))
            final.append(row)
            last = row or last
        _levels = (zs, final)
    zs, rows = _levels
    z = max(zs[-1], min(zs[0], z))
    for i in range(len(zs) - 1):
        if zs[i] >= z >= zs[i + 1]:
            t = (zs[i] - z) / (zs[i] - zs[i + 1])
            a, b = rows[i], rows[i + 1]
            lo, hi, ry = (a[k] + t * (b[k] - a[k]) for k in range(3))
            return ((lo + hi) / 2, (hi - lo) / 2 + .07, ry + .07)
    a = rows[0]
    return ((a[0] + a[1]) / 2, (a[1] - a[0]) / 2 + .07, a[2] + .07)

fitted, loose = {}, set()
for mesh in work['equipment']:
    if mesh['geoset'] in (1202, 1302):
        loose.update(v for tri in mesh['triangles'] for v in tri)
for mesh in work['equipment']:
    for index in {v for tri in mesh['triangles'] for v in tri}:
        point = Vector(vertices[index]['position'])
        hit, normal, _, distance = body.find_nearest(point)
        assert hit is not None
        if index in loose and point.z < work['waist'] - .15:
            # Loose skirts retain their vertical drape; expand only enough to enclose the bare legs.
            cx, rx, ry = envelope(point.z)
            direction = Vector(((point.x - cx) / rx, point.y / ry))
            if direction.length < 1e-6:
                direction = Vector((1, 0))
            direction.normalize()
            result = [cx + direction.x * rx, direction.y * ry, point.z]
        else:
            result = list(hit + normal.normalized() * .025)
        fitted[str(index)] = result
(root / 'donor-fit.json').write_text(json.dumps(fitted) + '\n', encoding='utf-8')
print('FITTED', len(fitted), 'garment vertices to bare Tarasek; loose skirt heights retained', flush=True)
