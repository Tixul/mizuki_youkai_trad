"""Avancement d'une langue : blocs traduits / restants, par zone de 4 Kio de la ROM.

    python tools/etat.py --rom JEU.ngc --lang es            résumé par zone
    python tools/etat.py --rom JEU.ngc --lang es --from 24A00   40 prochains blocs NON traduits
"""
import argparse
import os
import struct
import sys
sys.dont_write_bytecode = True   # pas de __pycache__ (chemin complet du PC)

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build      # noqa: E402
import extract    # noqa: E402

sys.stdout.reconfigure(encoding='utf-8')


def is_empty(b):
    return all(x in (0x3A, 0x9A, 0xFE, 0xFF) for x in b)


def is_data(b):
    return b.count(0xF1) > 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rom', required=True)
    ap.add_argument('--lang', required=True)
    ap.add_argument('--from', dest='start')
    a = ap.parse_args()
    rom = open(a.rom, 'rb').read()
    build.check_rom(rom)
    d, _ = build.load_lang(a.lang)
    done = build.load_units(build.lang_files(d))
    ptrs = build.pointer_tables(rom)
    targets = sorted({struct.unpack_from('<I', rom, p)[0] - build.CART for p in ptrs})
    nxt = {t: (targets[i + 1] if i + 1 < len(targets) else build.TEXT_HI) for i, t in enumerate(targets)}
    if a.start:
        start, n = int(a.start, 16), 0
        for t in targets:
            b = rom[t:nxt[t]]
            if t >= start and t not in done and not is_empty(b) and not is_data(b):
                print(f'@{t:05X}  ' + extract.decode(b).strip().replace('\n', ' / ')[:70])
                n += 1
                if n == 40:
                    break
        return
    zones = {}
    for t in targets:
        b = rom[t:nxt[t]]
        z = zones.setdefault(t & ~0xFFF, [0, 0, 0])
        if t in done:
            z[0] += 1
        elif is_empty(b) or is_data(b):
            z[2] += 1
        else:
            z[1] += 1
    print('zone    traduits  restants  vides/données')
    for k in sorted(zones):
        print(f'{k:05X}   {zones[k][0]:8d}  {zones[k][1]:8d}  {zones[k][2]:8d}')
    tot = [sum(z[i] for z in zones.values()) for i in range(3)]
    print(f'TOTAL   {tot[0]:8d}  {tot[1]:8d}  {tot[2]:8d}')


if __name__ == '__main__':
    main()
