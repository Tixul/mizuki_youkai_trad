"""Reprend une traduction déjà écrite pour les blocs japonais DOUBLONS.

Le jeu répète des villes entières (2e phase de l'histoire). Une fois les originaux traduits :

    python tools/doublons.py --rom JEU.ngc --lang es --range 2C800 2F000 --out doublons_2C800.txt

Pour chaque bloc NON traduit de la plage :
  * japonais identique octet pour octet à un bloc déjà traduit -> même traduction ;
  * japonais identique à la FIN d'un bloc traduit, à partir d'une ligne de nom
    (début ou ligne après {FC}) -> la traduction correspondante, à partir de la même ligne.
Les blocs sans équivalent sont listés (à traduire à la main). build.py revérifie tout.
"""
import argparse
import os
import struct
import sys
sys.dont_write_bytecode = True   # pas de __pycache__ (chemin complet du PC)

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build      # noqa: E402

sys.stdout.reconfigure(encoding='utf-8')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rom', required=True)
    ap.add_argument('--lang', required=True)
    ap.add_argument('--range', nargs=2, required=True, metavar=('DEBUT', 'FIN'))
    ap.add_argument('--out', required=True, help='nom du fichier créé dans lang/<code>/')
    a = ap.parse_args()
    lo, hi = (int(x, 16) for x in a.range)
    rom = open(a.rom, 'rb').read()
    build.check_rom(rom)
    d, _ = build.load_lang(a.lang)
    out = os.path.join(d, os.path.basename(a.out))
    done = build.load_units([p for p in build.lang_files(d) if os.path.abspath(p) != os.path.abspath(out)])
    ptrs = build.pointer_tables(rom)
    targets = sorted({struct.unpack_from('<I', rom, p)[0] - build.CART for p in ptrs})
    nxt = {t: (targets[i + 1] if i + 1 < len(targets) else build.TEXT_HI) for i, t in enumerate(targets)}
    ja = {t: bytes(rom[t:nxt[t]]) for t in targets}
    exact, suffix = {}, {}
    for off, lines in done.items():
        b = ja[off]
        exact.setdefault(b, lines)
        jl = b.split(b'\xfe')
        for i in range(1, len(lines)):
            if lines[i - 1].endswith('{FC}') and i < len(jl):
                suffix.setdefault(b'\xfe'.join(jl[i:]), lines[i:])
    found, missing = [], []
    for t in targets:
        if not (lo <= t < hi) or t in done or len(ja[t]) < 6:
            continue
        lines = exact.get(ja[t]) or suffix.get(ja[t])
        (found if lines else missing).append((t, lines))
    with open(out + '.tmp', 'w', encoding='utf-8') as f:
        f.write(f'# Repris automatiquement (tools/doublons.py) : doublons de {lo:05X}-{hi:05X}.\n')
        for t, lines in found:
            f.write(f'@{t:05X}\n' + '\n'.join(lines) + '\n')
    os.replace(out + '.tmp', out)
    print(f'{len(found)} doublons repris -> {out}')
    print(f'{len(missing)} sans équivalent :', ' '.join(f'{t:05X}' for t, _ in missing[:60]))


if __name__ == '__main__':
    main()
