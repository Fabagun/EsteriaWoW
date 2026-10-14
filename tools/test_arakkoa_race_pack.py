"""Check the staged Horde Arakkoa package against the live client without touching it."""

from collections import Counter

import arakkoa_race_pack as a
import retroported_race_pack as p

CLIENT_TABLES = ('Spell', 'SoundEntries', 'CreatureSoundData', 'EmotesTextSound', 'ChrRaces', 'CharSections',
                 'CharHairGeosets', 'BarberShopStyle', 'CharStartOutfit', 'NameGen', 'CreatureModelData',
                 'CreatureDisplayInfo')


def staged(name):
    return p.RawWdbc((a.STAGE / 'client-dbc' / (name + '.dbc')).read_bytes())


def baseline(name):
    return p.RawWdbc((a.STAGE / 'baseline' / (name + '.dbc')).read_bytes())


def check_no_overwrite():
    """Every id this race introduces is new, and every pre-existing row is byte-identical."""
    for name in CLIENT_TABLES:
        old, new = baseline(name), staged(name)
        assert not (Counter(old.records) - Counter(new.records)), name
        added = Counter(new.records) - Counter(old.records)
        old_ids = {p._value(row, 0) for row in old.records}
        assert added, name
        assert not {p._value(row, 0) for row in added} & old_ids, name


def check_spells():
    table = baseline('Spell')
    assert not {p._value(r, 0) for r in table.records} & set(a.SPELLS)
    icons = {p._value(r, 0) for r in baseline_icons().records}
    new = staged('Spell')
    for row in new.records:
        if p._value(row, 0) in a.SPELLS:
            assert p._value(row, 133 * 4) in icons, p._value(row, 0)
            name = p._string(new.strings, p._value(row, 136 * 4)).decode()
            assert name in dict(a.RACIALS).values(), name


def baseline_icons():
    files = p.ClientFiles(str(p.CLIENT_DEFAULT / 'Data'), 'enUS')
    try:
        return p.RawWdbc(files.find(p.DBC_ROOT + 'SpellIcon.dbc')[0])
    finally:
        files.close()


def check_race_slot():
    races = staged('ChrRaces')
    owners = [p._string(races.strings, p._value(r, 44)).decode() for r in races.records if p._value(r, 0) == a.RACE]
    assert owners == [a.TOKEN]
    assert not any(p._value(r, 0) == a.RACE for r in baseline('ChrRaces').records)
    other = [p._value(r, 4) for r in staged('CharSections').records if p._value(r, 4) == a.SOURCE_RACE]
    original = [p._value(r, 4) for r in baseline('CharSections').records if p._value(r, 4) == a.SOURCE_RACE]
    assert len(other) == len(original), 'Mag\'har (race 45) rows must be untouched'


def check_voices():
    assert {p._value(r, 0) for r in staged('SoundEntries').records} >= set(range(414401, 414407))
    csd = {p._value(r, 0) for r in staged('CreatureSoundData').records}
    assert 9045001 in csd and 2171 in csd


if __name__ == '__main__':
    for check in (check_no_overwrite, check_spells, check_race_slot, check_voices):
        check()
        print('PASS', check.__name__)
