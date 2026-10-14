"""Regression check for race-scoped Ogre texture selection and WotLK section types."""
import struct
import ogre_furbolg_race_pack as o


def check():
    assert o.SECTION_TYPES['hair'] == 3
    assert o.SECTION_TYPES['facial'] == 2
    rows = [struct.pack('<10I',1,1,0,0,0,0,0,1,0,0),
            struct.pack('<10I',2,25,0,0,0,0,0,1,0,0)]
    payload = b'WDBC'+struct.pack('<4I',2,10,40,1)+b''.join(rows)+b'\0'
    _, selected = o._donor_section_rows(payload,25)
    assert all(o.p._value(row,4) == 25 for row in selected.values())
    assert o.p._value(selected[(0,0,0,0)],0) == 2
    print('Ogre donor race and section type checks passed')


if __name__ == '__main__':
    check()
