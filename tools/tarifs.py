"""Génère lang/<code>/tarifs.txt : enregistrements de voyage (ROM 0x2372C-0x23E40).

    python tools/tarifs.py --rom JEU.ngc --lang es

Format mesuré d'un enregistrement (plusieurs à la suite dans un bloc) :
    [prix 2 octets LE][00 00][n° destination] NOM FE [9A]PRIX-AFFICHÉ FF
Tous les octets sont recopiés à l'identique ({XX}) sauf le NOM, pris dans
DESTINATIONS de lang/<code>/lang.py. Fichier GÉNÉRÉ : ne pas l'éditer à la main.
"""
import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build      # noqa: E402
import extract    # noqa: E402


def esc(bs):
    return ''.join('{%02X}' % x for x in bs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rom', required=True)
    ap.add_argument('--lang', required=True)
    a = ap.parse_args()
    rom = open(a.rom, 'rb').read()
    build.check_rom(rom)
    d, lang = build.load_lang(a.lang)
    names = lang.DESTINATIONS
    ptrs = build.pointer_tables(rom)
    targets = sorted({struct.unpack_from('<I', rom, p)[0] - build.CART for p in ptrs})
    nxt = {t: targets[i + 1] for i, t in enumerate(targets[:-1])}
    out = ['# Enregistrements de voyage (généré par tools/tarifs.py, NE PAS éditer à la main).']
    for t in targets:
        if not (0x2372C <= t < 0x23E41):
            continue
        b = rom[t:nxt[t]]
        if b[:2] == b'\x3a\xfe':                 # vrai message, pas un enregistrement
            continue
        text, p = '', 0
        while p < len(b):
            q, r = b.find(b'\xfe', p + 5), -1
            if q > 0:
                r = b.find(b'\xff', q)
            if q < 0 or r < 0:
                text += esc(b[p:])
                break
            jp = extract.decode(b[p + 5:q])
            if jp not in names:
                raise SystemExit(f'DESTINATIONS : il manque {jp!r}')
            text += esc(b[p:p + 5]) + names[jp] + '\n' + esc(b[q + 1:r + 1])
            p = r + 1
            while p < len(b) and b[p] == 0xFE:
                text += '\n'
                p += 1
        lines = text.split('\n')
        if lines and lines[-1] == '':
            lines.pop()
        out += ['@%05X' % t] + lines
    path = os.path.join(d, 'tarifs.txt')
    open(path + '.tmp', 'w', encoding='utf-8').write('\n'.join(out) + '\n')
    os.replace(path + '.tmp', path)
    print(path)


if __name__ == '__main__':
    main()
