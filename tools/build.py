"""Construit une ROM traduite de « Mizuki Shigeru no Youkai Shashinkan » (NGPC, 1999) + son patch IPS.

    python tools/build.py --rom "Mizuki Shigeru no Youkai Shashinkan (Japan).ngc" --lang fr --ips

Étapes : police latine -> écran titre -> texte (relogé en fin de ROM, pointeurs réécrits)
-> vérification en relisant la ROM construite -> (option) patch IPS.

La langue = un dossier lang/<code>/ : lang.py (réglages) + des fichiers *.txt (le texte).
Toutes les erreurs sont listées d'un coup ; rien n'est écrit tant qu'il en reste une.
"""
import argparse
import glob
import hashlib
import importlib.util
import os
import re
import struct
import sys
import zlib

sys.dont_write_bytecode = True   # pas de __pycache__ : il contiendrait le chemin complet du PC

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import font_latin as font    # noqa: E402
import gfx_title             # noqa: E402
import interface             # noqa: E402
import ips                   # noqa: E402

ROOT = os.path.dirname(HERE)

# ROM attendue (No-Intro « Mizuki Shigeru no Youkai Shashinkan (Japan) »)
ROM_SIZE = 2097152
ROM_CRC32 = 0xDDE08335
ROM_SHA1 = '8025d09368598951da94f8601729c16972b96830'

FONT = 0x1998D            # glyphe(code) = FONT + 16*code, lu tel quel par la file VBlank
TEXT_LO, TEXT_HI = 0x21000, 0x32400
FREE = 0x190000           # 0x188E08-0x1FFFFF = FF (vide)
CART = 0x200000
CTRL = set(range(0xF0, 0x100))
MAXCOL = 17               # caractères visibles par ligne de dialogue (mesuré)
NAME_MAX = 6              # nom du locuteur : au-delà, écrasé à la page suivante (mesuré)


def check_rom(rom):
    if len(rom) != ROM_SIZE or zlib.crc32(rom) != ROM_CRC32:
        raise SystemExit('ROM inattendue : il faut « Mizuki Shigeru no Youkai Shashinkan (Japan) », '
                         f'{ROM_SIZE} octets, CRC32 {ROM_CRC32:08X} (non modifiée, sans en-tête).')


def load_lang(code):
    d = os.path.join(ROOT, 'lang', code)
    spec = importlib.util.spec_from_file_location('lang_' + code, os.path.join(d, 'lang.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return d, mod


def lang_files(d):
    """Fichiers de dialogues (interface.txt = chaînes d'interface, lu par interface.py)."""
    return sorted(p for p in glob.glob(os.path.join(d, '*.txt'))
                  if os.path.basename(p) != 'interface.txt')


def pointer_tables(rom):
    """Tables de pointeurs 32 bits (>= 4 entrées consécutives) vers la zone de texte."""
    lo, hi = CART + TEXT_LO, CART + TEXT_HI
    runs, o = [], 0
    while o < 0x188000:
        n = 0
        while lo <= struct.unpack_from('<I', rom, o + 4 * n)[0] < hi:
            n += 1
        if n >= 4:
            runs.append((o, n))
            o += 4 * n
        else:
            o += 1
    return [o + 4 * i for o, n in runs for i in range(n)]


def parse_trad(path):
    units, cur = [], None
    for line in open(path, encoding='utf-8').read().split('\n'):
        if line.startswith('#'):
            continue
        if line.startswith('@'):
            cur = [int(line[1:], 16), []]
            units.append(cur)
        elif cur is not None:
            cur[1].append(line)
    out = []
    for off, lines in units:
        while lines and lines[-1] == '':
            lines.pop()
        out.append((off, lines))
    return out


ERRORS = []                 # toutes les erreurs d'un passage, affichées ensemble


def encode_line(s, where):
    b = bytearray()
    for tok in re.findall(r'\{[0-9A-Fa-f]{2}\}|.', s):
        if tok.startswith('{'):
            b.append(int(tok[1:3], 16))
        elif tok in font.CODE:
            b.append(font.CODE[tok])
        elif tok in font.DIGITS:
            b.append(font.DIGITS[tok])
        else:
            ERRORS.append(f'{where}: caractère sans glyphe {tok!r} (ajoutez-le dans EXTRA_GLYPHS)')
    return bytes(b)


def show(b):
    rev = {v: k for k, v in font.CODE.items()}
    rev.update({v: k for k, v in font.DIGITS.items()})
    return ''.join(rev.get(x, '{%02X}' % x) for x in b)


PARAM = {0xF5, 0xF8, 0xF9, 0xFA}     # terminateurs suivis d'un octet paramètre (à garder)


def skeleton(b):
    """Codes de contrôle + octets paramètres + nombre de FE : doit être identique au japonais."""
    out, skip = bytearray(), False
    for x in b:
        if skip:
            out.append(x)
            skip = False
        elif x in CTRL:
            out.append(x)
            skip = x in PARAM
    return bytes(out) + bytes([b.count(0xFE) & 0xFF, b.count(0xFE) >> 8])


def closed(ja):
    """Le message s'arrête-t-il de lui-même (sinon le jeu lit la suite en séquence) ?"""
    return ja.endswith((b'\xff\xfe', b'\xff')) or (len(ja) >= 2 and ja[-2] in PARAM)


def encode_unit(lines, where):
    """Chaque ligne + FE, SAUF une ligne finie par un terminateur à paramètre ({F5}{xx}…) :
    dans la ROM, celui-ci n'est suivi d'aucun FE."""
    out = bytearray()
    for l in lines:
        b = encode_line(l, where)
        out += b
        if not (len(b) >= 2 and b[-2] in PARAM):
            out.append(0xFE)
    return bytes(out)


def check_widths(b, where):
    # coupe aux terminateurs ; l'octet paramètre de F5/F8/F9/FA tombe seul en début de segment
    for seg in re.split(rb'[\xf5-\xfa\xfc\xfd\xff]', b):
        for ln in seg.split(b'\xfe'):
            if 0xF2 in ln:
                continue
            if len(ln) > MAXCOL:
                ERRORS.append(f'{where}: {len(ln)} car. > {MAXCOL} : « {show(ln)} »')


def apply_font(rom):
    for ch, code in font.CODE.items():
        rom[FONT + 16 * code: FONT + 16 * code + 16] = font.tile_2bpp(font.G[ch])


def load_units(paths):
    units = {}
    for path in paths:
        for off, lines in parse_trad(path):
            if off in units:
                raise SystemExit(f'@{off:05X} traduit deux fois ({os.path.basename(path)})')
            units[off] = lines
    return units


def apply_text(rom, paths):
    """Reloge les messages traduits en fin de ROM, par BLOCS contigus, et réécrit les pointeurs.

    Un message qui ne finit pas par un terminateur est lu EN SÉQUENCE avec le suivant :
    le suivant doit donc être traduit aussi, sinon refus.
    """
    units = load_units(paths)
    ptrs = pointer_tables(rom)
    targets = sorted({struct.unpack_from('<I', rom, p)[0] - CART for p in ptrs})
    tset = set(targets)
    for off in units:
        if off not in tset:
            raise SystemExit(f'@{off:05X} : pas une cible de pointeur')
    nxt = {t: (targets[i + 1] if i + 1 < len(targets) else TEXT_HI) for i, t in enumerate(targets)}
    new, where, encoded = bytearray(), {}, {}
    order = sorted(units)
    for k, off in enumerate(order):
        end = nxt[off]
        ja = bytes(rom[off:end])
        where_s = f'@{off:05X}'
        tr = encode_unit(units[off], where_s)
        if not ja.endswith(b'\xfe') and tr.endswith(b'\xfe'):
            tr = tr[:-1]               # fin EXACTE du japonais (certains FF n'ont pas de FE)
        encoded[off] = tr
        if skeleton(tr) != skeleton(ja):
            ERRORS.append(f'{where_s}: structure différente du japonais\n'
                          f'    ja {skeleton(ja).hex(" ")}\n    tr {skeleton(tr).hex(" ")}')
        if not closed(ja) and (k + 1 == len(order) or order[k + 1] != end):
            ERRORS.append(f'{where_s}: enchaîne sur @{end:05X} qui n\'est pas traduit')
        check_widths(tr, where_s)
        where[off] = FREE + len(new)
        new += tr
    if ERRORS:
        raise SystemExit('\n'.join(ERRORS) + f'\n{len(ERRORS)} erreur(s)')
    for off in order:            # nom du locuteur : avertissement seulement
        ls = units[off]
        jl = bytes(rom[off:nxt[off]]).split(b'\xfe')
        for i, l in enumerate(ls):
            is_name = i < len(jl) and 0 < len(jl[i]) <= 7 and (i == 0 or ls[i - 1].endswith('{FC}'))
            if is_name and '{' not in l and len(l) > NAME_MAX:
                print(f'  ! @{off:05X} nom de locuteur long « {l} » ({len(l)} > {NAME_MAX})')
    if FREE + len(new) > len(rom) or bytes(rom[FREE:FREE + len(new)]) != b'\xff' * len(new):
        raise SystemExit('zone libre insuffisante ou déjà occupée')
    rom[FREE:FREE + len(new)] = new
    n = 0
    for p in ptrs:               # SEULEMENT les entrées de tables, SEULEMENT vers un message traduit
        t = struct.unpack_from('<I', rom, p)[0] - CART
        if t in where:
            struct.pack_into('<I', rom, p, where[t] + CART)
            n += 1
    return len(units), len(new), n, where, encoded


def verify(rom, encoded, where):
    for off, tr in encoded.items():
        a = where[off]
        assert bytes(rom[a:a + len(tr)]) == tr, f'@{off:05X} absent de la ROM'
    for ch, code in font.CODE.items():
        assert rom[FONT + 16 * code: FONT + 16 * code + 16] == font.tile_2bpp(font.G[ch])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--rom', required=True, help='ROM japonaise d\'origine (.ngc)')
    ap.add_argument('--lang', default='fr', help='dossier lang/<code> (défaut : fr)')
    ap.add_argument('--out', help='ROM produite (défaut : out/<lang>.ngc)')
    ap.add_argument('--ips', action='store_true', help='écrire aussi out/<lang>.ips')
    a = ap.parse_args()
    rom = bytearray(open(a.rom, 'rb').read())
    check_rom(rom)
    original = bytes(rom)
    d, lang = load_lang(a.lang)
    font.add_glyphs(getattr(lang, 'EXTRA_GLYPHS', {}))
    gfx_title.FONT_DIRS.insert(0, d)

    apply_font(rom)
    new1, new2 = gfx_title.build_logo(rom, lang.TITLE_LINES)
    ntiles, nfresh = gfx_title.apply_logo(rom, new1, new2)
    gfx_title.apply_menu(rom, lang.MENU)
    gfx_title.apply_eyes(rom)
    nu, nb, np_, where, encoded = apply_text(rom, lang_files(d))
    verify(rom, encoded, where)
    ui_in, ui_moved, ui_bytes = interface.apply(rom, lang, d, ERRORS)
    if ERRORS:
        raise SystemExit('\n'.join(ERRORS) + f'\n{len(ERRORS)} erreur(s)')

    out = a.out or os.path.join(ROOT, 'out', a.lang + '.ngc')
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    gfx_title.preview(rom, os.path.splitext(out)[0] + '_titre.png')
    open(out + '.tmp', 'wb').write(rom)
    os.replace(out + '.tmp', out)
    print(f'logo : {ntiles}+{nfresh} tuiles | texte : {nu} messages, {nb} octets, {np_} pointeurs')
    print(f'interface : {ui_in} blocs sur place, {ui_moved} relogés, {ui_bytes} octets en 0x{interface.UI_FREE:X}')
    print('ROM :', out, '| CRC32 %08X' % zlib.crc32(rom), '| SHA-1', hashlib.sha1(rom).hexdigest())
    if a.ips:
        p = os.path.splitext(out)[0] + '.ips'
        data = ips.make(original, bytes(rom))
        open(p + '.tmp', 'wb').write(data)
        os.replace(p + '.tmp', p)
        assert ips.apply(original, data) == bytes(rom), 'patch IPS incohérent'
        print('IPS :', p, f'({len(data)} octets, vérifié par ré-application)')


if __name__ == '__main__':
    main()
