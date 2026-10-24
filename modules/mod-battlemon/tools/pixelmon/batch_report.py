"""Create a compact review sheet and human-readable batch report from completed checkpoints."""
import argparse
from collections import Counter
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from batch import DEFAULT_OUTPUT


def summarize(output):
    report = json.loads((output/'report.json').read_text())
    records = report['records']
    rows = [r for r in records if not r['shiny']]
    columns, width, height = 5, 256, 290
    sheet = Image.new('RGB', (columns*width, ((len(rows)+columns-1)//columns)*height), '#18212d')
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 15)
    except OSError:
        font = ImageFont.load_default()
    for i, record in enumerate(rows):
        x, y = (i % columns)*width, (i//columns)*height
        path = output/'preview'/(str(record['form'])+'.png')
        if record['status'] == 'passed' and path.exists():
            sheet.paste(Image.open(path).convert('RGB').resize((width, 256)), (x, y))
        else:
            label = 'HELD BACK' if record['status'] != 'passed' else 'Preview not rendered'
            draw.text((x+20, y+100), label, fill='#eebd7c', font=font)
            reason = record.get('reason', '').split(':')[0]
            draw.text((x+12, y+126), reason[:30], fill='#eebd7c', font=font)
        draw.text((x+8, y+262), f"{record['form']}: {record['name']}", fill='white', font=font)
    (output/'preview').mkdir(exist_ok=True)
    sheet.save(output/'preview/contact-sheet.jpg', quality=92)
    failures = Counter(r['reason'] for r in records if r['status'] != 'passed')
    lines = ['# Pixelmon batch checkpoint', '',
             f"Completed {report['completed_forms']} / {len(report['selected_forms'])} selected forms.",
             f"Appearance counts: {report['counts']}.",
             f"Elapsed: {report['elapsed_seconds']:.1f} seconds; reused: {report['reused_appearances']} appearances.",
             '', 'These are offline conversion checks, not an in-game visual sign-off.', '',
             '## Held-back appearances', '', '| Count | Reason |', '| ---: | --- |']
    for reason, count in failures.most_common():
        lines.append(f'| {count} | {reason} |')
    lines.extend(['', '## Selected forms', '', '| ID | Form | Normal | Shiny |', '| ---: | --- | --- | --- |'])
    for record in rows:
        shiny = next(r for r in records if r['form'] == record['form'] and r['shiny'])
        lines.append(f"| {record['form']} | {record['name']} | {record['status']} | {shiny['status']} |")
    (output/'REPORT.md').write_text('\n'.join(lines)+'\n', encoding='utf8', newline='\n')
    print(json.dumps(dict(counts=report['counts'], elapsed_seconds=report['elapsed_seconds'],
                          reused=report['reused_appearances'], exceptions=dict(failures)), indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    summarize(parser.parse_args().output.resolve())
