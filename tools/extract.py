"""Extrait le script japonais de VOTRE ROM : un bloc par cible de pointeur de table.

    python tools/extract.py --rom JEU.ngc --out script_ja.txt
    python tools/extract.py --rom JEU.ngc --out script_ja_fr.txt --ref fr   (+ la VF sous chaque bloc)

Le script japonais n'est pas distribué avec ce kit (texte du jeu, sous droits) : chacun
l'extrait de sa propre cartouche. Les en-têtes « @OFFSET » sont ceux des fichiers de traduction.
"""
import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build      # noqa: E402

H = 'あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん'
K = 'アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン'
JA = {i: c for i, c in enumerate(H)}
JA.update({0x40 + i: c for i, c in enumerate(K)})
JA.update({0xB0 + i: c for i, c in enumerate('がぎぐげござじずぜぞだぢづでど')})
JA.update({0xC0 + i: c for i, c in enumerate('ばびぶべぼぱぴぷぺぽ')})
JA.update({0xDA + i: c for i, c in enumerate('バビブベボ')})
JA.update({0xE0 + i: c for i, c in enumerate('パピプペポ')})
JA.update({0xCA + i: c for i, c in enumerate('ガギグゲゴ')})
JA.update({0xD0 + i: c for i, c in enumerate('ザジズゼゾダヂヅデド')})
JA.update({0x2E: 'ぁ', 0x2F: 'ぃ', 0x30: 'ぅ', 0x31: 'ぇ', 0x32: 'ぉ',
           0x33: 'っ', 0x34: 'ゃ', 0x35: 'ゅ', 0x36: 'ょ', 0x37: '、', 0x38: '。', 0x3A: '　',
           0x3B: '「', 0x3C: '」', 0x39: 'ー', 0x3D: '（', 0x3E: '）', 0x3F: '〜',
           0x77: '？', 0x78: '！', 0x79: '¥', 0x7A: '・', 0x7B: '／', 0x7C: '■',
           0x6E: 'ァ', 0x6F: 'ィ', 0x70: 'ゥ', 0x71: 'ェ', 0x72: 'ォ', 0x73: 'ッ', 0x74: 'ャ',
           0x75: 'ュ', 0x76: 'ョ'})
JA.update({0xA0 + i: str(i) for i in range(10)})


PARAM = {0xF5, 0xF8, 0xF9, 0xFA}     # terminateurs suivis d'un octet paramètre


def decode(b):
    out = []
    skip = False
    for i, x in enumerate(b):
        if skip:
            out.append('{%02X}' % x)
            skip = False
            continue
        skip = x in PARAM
        if x == 0xFE:
            out.append('\n')
        elif x in JA:
            out.append(JA[x])
        else:
            out.append('{%02X}' % x)
    return ''.join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rom', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--ref', help='code de langue dont la traduction est ajoutée sous chaque bloc')
    a = ap.parse_args()
    rom = open(a.rom, 'rb').read()
    build.check_rom(rom)
    ref = {}
    if a.ref:
        ref = build.load_units(build.lang_files(build.load_lang(a.ref)[0]))
    ptrs = build.pointer_tables(rom)
    refs = {}
    for p in ptrs:
        t = struct.unpack_from('<I', rom, p)[0] - build.CART
        refs.setdefault(t, []).append(p)
    starts = sorted(refs)
    lines = []
    for i, t in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else build.TEXT_HI
        body = rom[t:end]
        tag = ' '.join('%05X' % p for p in refs[t][:4]) + (' …' if len(refs[t]) > 4 else '')
        lines.append(f'@{t:05X}  ← {tag}')
        lines.append(decode(body).rstrip('\n'))
        if t in ref:
            lines += ['    %s| %s' % (a.ref, l) for l in ref[t]]
    tmp = a.out + '.tmp'
    open(tmp, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    os.replace(tmp, a.out)
    print(len(starts), 'blocs ->', a.out)


if __name__ == '__main__':
    main()
