"""Add two permanent native imports to the exact installed October15 Esteria client."""
import hashlib
import json
from pathlib import Path
import struct

from native_appearance_patch import align
from wow_xref import Pe

EXPECTED = 'b8d5b92d80ecf7044c07768d2df1171c345a34006c33afca7749247d63957e85'
EXPORTS = ('EsteriaSelfMounted', 'EsteriaSelfAnimation', 'EsteriaSelfMotion')


def patch(source, output):
    pe = Pe(source)
    assert hashlib.sha256(pe.data).hexdigest() == EXPECTED, 'Unexpected executable; no patch applied'
    assert pe.read_va(0xDFE000, 29).startswith(b'ESTERIA_CLIENT_FOUNDATION_V3\0')
    data = bytearray(pe.data)
    nt = struct.unpack_from('<I', data, 0x3C)[0]
    opt = nt + 24
    count = struct.unpack_from('<H', data, nt + 6)[0]
    new_header = opt + struct.unpack_from('<H', data, nt + 20)[0] + count * 40
    assert new_header + 40 <= min(s[4] for s in pe.sections), 'No spare section header'
    assert not struct.unpack_from('<H', data, opt + 70)[0] & 0x40, 'ASLR needs relocated thunks'
    section_align, file_align = struct.unpack_from('<2I', data, opt + 32)
    rva = align(max(va + max(vs, rs) for _, va, vs, rs, _ in pe.sections), section_align)
    base = pe.image_base + rva
    blob = bytearray()

    def add(payload, alignment=4):
        blob.extend(bytes(align(len(blob), alignment) - len(blob)))
        address = base + len(blob)
        blob.extend(payload)
        return address

    imports_rva, _ = struct.unpack_from('<2I', data, opt + 104)
    descriptors = bytearray()
    for offset in range(0, 8192, 20):
        record = pe.read_va(pe.image_base + imports_rva + offset, 20)
        if record == bytes(20):
            break
        descriptors.extend(record)
    else:
        raise ValueError('Unterminated import descriptors')
    names = [add(b'\0\0' + name.encode() + b'\0', 2) - pe.image_base for name in EXPORTS]
    lookup = add(struct.pack('<4I', *names, 0))
    iat = add(struct.pack('<4I', *names, 0))
    library = add(b'EsteriaAppearance.dll\0')
    descriptors.extend(struct.pack('<5I', lookup - pe.image_base, 0, 0,
                                   library - pe.image_base, iat - pe.image_base))
    descriptors.extend(bytes(20))
    import_table = add(descriptors)
    add(b'ESTERIA_TARASEK_RUNNING_WILD_V1\0')
    sites = []

    def raw_offset(va):
        for _, relative, _, size, raw in pe.sections:
            if relative <= va - pe.image_base < relative + size:
                return raw + va - pe.image_base - relative
        raise ValueError(f'Not file-backed: {va:x}')

    def jump(source_va, destination):
        return b'\xE9' + struct.pack('<i', destination - source_va - 5)

    def redirect(va, expected, generate):
        assert pe.read_va(va, len(expected)) == expected, f'Patch-site mismatch: {va:x}'
        destination = base + align(len(blob), 4)
        payload = generate(destination)
        add(payload)
        start = raw_offset(va)
        data[start:start + len(expected)] = jump(va, destination) + b'\x90' * (len(expected) - 5)
        sites.append({'va': hex(va), 'before': expected.hex(), 'thunk': hex(destination),
                      'bytes': payload.hex()})

    def mounted(destination):
        # EAX is the checked local player. Return to stock true on self-mount, stock compare otherwise.
        prefix = bytes.fromhex('9c6050ff15') + struct.pack('<I', iat)
        prefix += bytes.fromhex('83c40484c07407')
        true_path = bytes.fromhex('619d')
        true_path += jump(destination + len(prefix) + len(true_path), 0x6125D7)
        false_path = bytes.fromhex('619d83b8c009000000')
        false_path += jump(destination + len(prefix) + len(true_path) + len(false_path), 0x6125C9)
        return prefix + true_path + false_path

    redirect(0x6125C2, bytes.fromhex('83b8c009000000'), mounted)

    def animation(destination):
        # Establish EBP, preserve registers/flags, pass the actual argument block, replay stack allocation.
        code = bytes.fromhex('558bec9c608d45085051ff15') + struct.pack('<I', iat + 4)
        code += bytes.fromhex('83c408619d83ec24')
        return code + jump(destination + len(code), 0x735826)

    redirect(0x735820, bytes.fromhex('558bec83ec24'), animation)
    def motion(destination):
        code = bytes.fromhex('558bec9c60ff750851ff15') + struct.pack('<I', iat + 8)
        code += bytes.fromhex('83c408619d83ec40')
        return code + jump(destination + len(code), 0x737EF6)

    redirect(0x737EF0, bytes.fromhex('558bec83ec40'), motion)
    raw = align(len(data), file_align)
    data.extend(bytes(raw - len(data)))
    data.extend(blob)
    raw_size = align(len(blob), file_align)
    data.extend(bytes(raw_size - len(blob)))
    struct.pack_into('<8s8I', data, new_header, b'.erwild\0', len(blob), rva, raw_size, raw,
                     0, 0, 0, 0xE0000060)
    struct.pack_into('<H', data, nt + 6, count + 1)
    struct.pack_into('<I', data, opt + 56, align(rva + len(blob), section_align))
    struct.pack_into('<2I', data, opt + 104, import_table - pe.image_base, len(descriptors))
    struct.pack_into('<I', data, opt + 64, 0)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)
    result = {'before': EXPECTED, 'after': hashlib.sha256(data).hexdigest(), 'imports': list(EXPORTS),
              'sites': sites, 'section_va': hex(base)}
    (output.parent / 'self-mount-exe.json').write_text(json.dumps(result, indent=2) + '\n')
    return result
