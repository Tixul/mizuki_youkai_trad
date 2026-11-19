"""Patch IPS : création et application (format standard « PATCH » ... « EOF »).

    python tools/ips.py make  ORIGINE.ngc TRADUITE.ngc  patch.ips
    python tools/ips.py apply ORIGINE.ngc patch.ips     SORTIE.ngc

Le patch ne contient QUE les octets modifiés (aucune plage d'octets d'origine n'y est recopiée :
les zones identiques ne sont jamais fusionnées dans un enregistrement).
"""
import sys
sys.dont_write_bytecode = True   # pas de __pycache__ (chemin complet du PC)

MAX = 0xFFFF


def make(src, dst):
    if len(src) != len(dst):
        raise SystemExit('les deux ROM doivent avoir la même taille')
    out = bytearray(b'PATCH')
    i, n = 0, len(src)
    while i < n:
        if src[i] == dst[i]:
            i += 1
            continue
        j = i
        while j < n and src[j] != dst[j] and j - i < MAX:
            j += 1
        if i == 0x454F46:                      # offset « EOF » : ambigu en IPS
            raise SystemExit('offset 0x454F46 non représentable')
        if i > 0xFFFFFF:
            raise SystemExit('ROM trop grande pour IPS')
        out += i.to_bytes(3, 'big') + (j - i).to_bytes(2, 'big') + dst[i:j]
        i = j
    out += b'EOF'
    return bytes(out)


def apply(src, patch):
    if patch[:5] != b'PATCH':
        raise SystemExit('pas un patch IPS')
    rom, p = bytearray(src), 5
    while patch[p:p + 3] != b'EOF':
        off = int.from_bytes(patch[p:p + 3], 'big')
        size = int.from_bytes(patch[p + 3:p + 5], 'big')
        p += 5
        if size:
            data = patch[p:p + size]
            p += size
        else:                                  # enregistrement RLE
            count = int.from_bytes(patch[p:p + 2], 'big')
            data = patch[p + 2:p + 3] * count
            p += 3
        if off + len(data) > len(rom):
            rom += b'\x00' * (off + len(data) - len(rom))
        rom[off:off + len(data)] = data
    return bytes(rom)


def main():
    if len(sys.argv) != 5 or sys.argv[1] not in ('make', 'apply'):
        raise SystemExit(__doc__)
    if sys.argv[1] == 'make':
        data = make(open(sys.argv[2], 'rb').read(), open(sys.argv[3], 'rb').read())
    else:
        data = apply(open(sys.argv[2], 'rb').read(), open(sys.argv[3], 'rb').read())
    open(sys.argv[4], 'wb').write(data)
    print(sys.argv[4], len(data), 'octets')


if __name__ == '__main__':
    main()
