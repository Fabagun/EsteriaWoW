"""Guarded installation of the consolidated skin-expansion / female Tuskarr package.

Backs up every file it replaces, installs the client files and server DBCs, then verifies the result by hash.
Refuses to run while the client is open or if any live file changed since the package was built.
Does not restart the server or apply SQL.
"""

from datetime import datetime
import json
from pathlib import Path
import shutil
import subprocess

import skin_expansion_pack as k

p = k.p
CLIENT = p.CLIENT_DEFAULT
SERVER = k.f.s.t.REPO / 'modules/mod-custom-server/data/dbc/retroported-races'


def main():
    report = json.loads((k.OUT / 'report.json').read_text(encoding='utf-8'))
    assert not report['installed'], 'Already installed'
    running = subprocess.check_output(['tasklist', '/FO', 'CSV', '/NH'], text=True).lower()
    assert not any('"' + name + '"' in running for name in ('wow.exe', 'eclipse.exe', 'mpqeditor.exe')), \
        'Close the client first'
    k.check_chain()
    archive = CLIENT / k.LOCALE
    assert p.sha256(archive) == report['archive']['baseline_sha256'], 'Live archive changed since packaging'
    backup = Path('G:/EsteriaBackups') / ('SkinsFemaleTuskarr-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    files = [(CLIENT / k.LOCALE, k.OUT / 'client' / k.LOCALE)]
    for name in report['loose_client_files']:
        files.append((CLIENT / name, k.OUT / 'client' / name))
    for name in report['server_dbcs']:
        files.append((SERVER / name, k.OUT / 'server' / name))
    for live, staged in files:
        assert staged.is_file(), staged
        if live.exists():
            target = backup / live.drive.replace(':', '') / Path(*live.parts[1:])
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(live, target)
            assert p.sha256(target) == p.sha256(live), 'Backup mismatch: ' + str(live)
    (backup / 'manifest.json').write_text(json.dumps({'files': [str(live) for live, _ in files]}, indent=2) + '\n')
    for live, staged in files:
        temporary = live.with_name(live.name + '.installing')
        shutil.copy2(staged, temporary)
        assert p.sha256(temporary) == p.sha256(staged)
        temporary.replace(live)
    for live, staged in files:
        assert p.sha256(live) == p.sha256(staged), 'Install verify failed: ' + str(live)
    report.update(installed=True, backup=str(backup))
    (k.OUT / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('Installed', len(files), 'files; backup:', backup)


if __name__ == '__main__':
    main()
