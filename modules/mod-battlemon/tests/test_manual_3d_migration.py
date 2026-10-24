"""The one-time transition must never return to the automatic updater."""
from pathlib import Path
import ast
M = Path(__file__).resolve().parents[1]
R = M.parents[1]
for db in ['world', 'characters']:
    assert (M/'migrations/manual/2d-to-3d'/(db+'.sql')).is_file()
    assert not (R/f'data/sql/updates/pending_db_{db}/rev_1790798400.sql').exists()
s = (M/'tools/emit_3d_catalog.py').read_text()
ast.parse(s)
assert 'data/sql/updates/pending_db_' not in s
assert s.count('migrations/manual/2d-to-3d/') == 2
assert not list((M/'data/sql').rglob('rev_1790798400.sql'))
print('PASS: transition SQL and generator are manual-only, outside updater discovery.')
