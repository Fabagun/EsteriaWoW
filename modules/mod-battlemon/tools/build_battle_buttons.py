"""Extract the owner's supplied sprite sheets into WoW 3.3.5 power-of-two RGBA textures."""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'tools/battle-button-art'
OUT = ROOT / 'addon/BattlemonBattles/Textures/Buttons'
TYPES = 'NORMAL FIGHTING FLYING POISON GROUND ROCK BUG GHOST STEEL UNKNOWN FIRE WATER GRASS ELECTRIC PSYCHIC ICE DRAGON DARK FAIRY'.split()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sheet = Image.open(SOURCE / 'types.png').convert('RGBA')
    for row, name in enumerate(TYPES):
        for col, state in enumerate(('normal', 'hover')):
            tile = sheet.crop((col * 192, row * 46, (col + 1) * 192, (row + 1) * 46))
            tile.resize((256, 64), Image.Resampling.NEAREST).save(OUT / f'{name}_{state}.tga')
    # Keep the supplied red border and shading, but leave captions to the addon
    # so Run/Forfeit/Close and translated labels never show contradictory baked text.
    sheet = Image.open(SOURCE / 'actions.png').convert('RGBA')
    for col, state in enumerate(('normal', 'hover')):
        tile = sheet.crop((col * 130, 0, (col + 1) * 130, 46))
        tile.paste(tile.crop((16, 0, 17, 46)).resize((94, 46)), (24, 0))
        tile.resize((256, 64), Image.Resampling.NEAREST).save(OUT / f'action_{state}.tga')
    sheet = Image.open(SOURCE / 'balls.png').convert('RGBA')
    for name, box in {
        'POKEBALL': (0, 0, 352, 340), 'GREATBALL': (424, 0, 780, 340),
        'ULTRABALL': (860, 0, 1211, 340), 'MASTERBALL': (0, 360, 352, 710),
        'PREMIERBALL': (424, 360, 780, 710), 'LUXURYBALL': (860, 360, 1211, 710),
        'NETBALL': (0, 740, 362, 1090), 'QUICKBALL': (424, 740, 780, 1090),
        'TIMERBALL': (860, 740, 1211, 1090), 'DUSKBALL': (0, 1120, 362, 1481),
        'DIVEBALL': (424, 1120, 780, 1481), 'REPEATBALL': (860, 1120, 1211, 1481),
    }.items():
        tile = sheet.crop(box)
        tile = tile.crop(tile.getbbox())
        tile.thumbnail((120, 120), Image.Resampling.LANCZOS)
        icon = Image.new('RGBA', (128, 128))
        icon.paste(tile, ((128 - tile.width) // 2, (128 - tile.height) // 2))
        icon.save(OUT / f'{name}.tga')


if __name__ == '__main__':
    main()
