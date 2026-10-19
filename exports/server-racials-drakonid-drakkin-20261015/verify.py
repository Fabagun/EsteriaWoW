from pathlib import Path
import hashlib
import json
import sys

root = Path(__file__).resolve().parent
manifest = json.loads((root / 'metadata/manifest.json').read_text(encoding='utf-8'))
failures = []
for entry in manifest['files']:
    path = root / entry['path']
    if not path.is_file():
        failures.append(entry['path'] + ': missing')
    elif path.stat().st_size != entry['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
        failures.append(entry['path'] + ': content differs')
if failures:
    print('FAILED\n' + '\n'.join(failures))
    sys.exit(1)
print('Verified', len(manifest['files']), 'files;', manifest['total_bytes'], 'bytes')
