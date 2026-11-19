"""Interface en fenêtres : 2e police, saisie du nom, régions/lieux, menus des objets, fiches, boutiques.

Ces écrans n'utilisent PAS la police des dialogues mais une 2e police (lettre blanche + ombre),
et leurs textes sont des chaînes à position fixe (hors de la zone des dialogues).

    python tools/interface.py --rom JEU.ngc --out interface_ja.txt            (liste japonaise)
    python tools/interface.py --rom JEU.ngc --out interface_ja.txt --ref fr   (+ la VF sous chaque ligne)

build.py appelle apply() : rien à lancer à la main pour construire.

Format d'une chaîne : [adresse dans le plan, 2 octets][00 00] texte, puis FE (chaîne suivante
du même bloc) ou FF (fin du bloc). Adresse -> ligne/colonne à l'écran (voir col_row).
Dans lang/<code>/interface.txt : « @BLOC » puis une ligne par chaîne, « _ » = case vide.
"""
import argparse
import os
import re
import struct
import sys
sys.dont_write_bytecode = True   # pas de __pycache__ (chemin complet du PC)

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import font_latin as font    # noqa: E402

CART = 0x200000
FONT2 = (0x1AA0D, 0x38DC9)   # 2e police (2 copies identiques), glyphe = base + 16*code
BLANK = 0xF1                 # case vide (aussi la case du curseur devant une option)
YEN = 0x79
MAP0 = 0x4DE7                # adresse de la ligne 0, colonne 0 ; 40 octets par ligne
UI_FREE = 0x1F8000           # zone libre pour les blocs relogés (0x188E08-0x1FFFFF = FF)
UI_END = 0x200000

# Blocs de chaînes (début de bloc = cible d'un pointeur du code). Les grilles de la saisie du
# nom (0x10FE6, 0x1107D) sont gérées à part (NAME_GRID).
BLOCKS = [0x0F5E6, 0x0F609, 0x0F630, 0x0F653, 0x0F670, 0x100F6, 0x1012F, 0x1015C, 0x10189,
          0x101B6, 0x101F0, 0x10260, 0x10751, 0x10FD4, 0x11114, 0x11165, 0x1170F, 0x11E39,
          0x11E50, 0x11E65, 0x11E76, 0x11E85, 0x1226E, 0x12840, 0x12D6B, 0x12D85, 0x12D9B,
          0x14953, 0x1495D, 0x14FB7, 0x15066, 0x1507C, 0x1547C, 0x154F7, 0x15507, 0x1551D,
          0x1552C, 0x1553F, 0x15CEA, 0x15CFF, 0x15D0E, 0x3FA6B]

# Saisie du nom : codes des cases (90 = 6 lignes x 15) + 5 boutons, une table par page.
GRID_SEL = (0x10F17, 0x10F75)
GRID_SHOW = (0x10FE6, 0x1107D)      # mêmes cases, affichées (6 lignes « 5 _ 5 _ 5 »)
GRID_EMPTY = 0x9A                   # case vide (le jeu remplit aussi le nom avec 0x9A)
TOGGLE_TILES = ((0xE7, 0xE8), (0xFB, 0xFC))   # bouton « changer de page » de chaque page

# Tables à largeur fixe (n° x 6 octets) : régions (« adresse » du joueur, album) et lieux (album).
# Passées à 8 caractères : table relogée + code modifié (multiplicateur, adresse, nb de car.).
REGION_TABLE, REGION_N = 0x1118D, 11
PLACE_TABLE, PLACE_N = 0x115CA, 44
WIDE = 8
TABLE_CODE = [   # (offset du multiplicateur, de l'adresse 32 bits, du nb de caractères, table)
    (0x10C80, 0x10C83, 0x10C8F, REGION_TABLE),
    (0x11522, 0x11525, 0x1152D, REGION_TABLE),
    (0x11544, 0x11547, 0x1154F, PLACE_TABLE),
]


# Menus en cadre (police des DIALOGUES) : le texte n'est pas une chaîne mais une liste d'adresses
# de glyphes (police + 16 x code) chargée dans les tuiles 0x10.., posées par un gabarit de cadre.
# Repère = offset de l'adresse de la liste dans « lda XIZ, (liste) » (F2 xx xx xx 36).
FONT1 = 0x1998D
GLYPH_MENUS = [0xD99E, 0xDA9E, 0xDB66, 0xDC32, 0xDCF6, 0xDDC8, 0xDFBA, 0xE12E, 0xE1F2, 0xE2B6]
MENU_MAX_TILES = 16          # tuiles 0x10-0x1F (le menu B d'origine en utilise 16)
# Chaînes brutes (texte, FE = ligne suivante, FF = fin) pointées par le code : « rien », état des
# pellicules, et les messages des DUELS PHOTO (2 copies : contre l'ordinateur / par câble).
# Dans les duels : F6 = nom du yôkai, F8 = joueur, F4/F5 = objet, FC = nombre, FD = somme, F1 = case
# vide ; texte à partir de la colonne 2 (17 car. par ligne, 3 lignes, pas de page suivante).
RAW = [0x0F42C, 0x0F472, 0x10471, 0x10474, 0x1047B]
DUEL_A = [0x374B4, 0x374CE, 0x374F8, 0x37547, 0x37566, 0x37573, 0x3757F, 0x37588, 0x37597,
          0x375A8, 0x375B0, 0x375BE, 0x375C6, 0x375D2, 0x375E2, 0x375F2, 0x375FD, 0x37608]
DUEL_B = [0x3E725, 0x3E73F, 0x3E769, 0x3E7B8, 0x3E7D7, 0x3E7E4, 0x3E7F0, 0x3E7F9, 0x3E808,
          0x3E819, 0x3E821, 0x3E82F, 0x3E837, 0x3E843, 0x3E863, 0x3E86E, 0x3E879, 0x3E893,
          0x3E8AD, 0x3E8C7, 0x3E8D8, 0x3E8F5, 0x3E904]
RAW += DUEL_A + DUEL_B
DUEL_COLS = 17
# Menu « もどる アイテム やめる » (duels) : liste + positions explicites (1 tuile par lettre).
POS_MENU = dict(list_ref=0x141AB, cnt=0x141A5, pos=0x14266, pos_cnt=0x141D1, n=10)


def col_row(hdr):
    d = hdr - MAP0
    return (d % 40) // 2, d // 40


def tile_shadow(rows, x0=1):
    """Glyphe 5x8 -> tuile 2e police : encre = couleur 1, ombre à droite = couleur 3, fond 0."""
    out = bytearray()
    for r in rows:
        ink = [0 <= x - x0 < 5 and r[x - x0] == '#' for x in range(8)]
        w = 0
        for x in range(8):
            c = 1 if ink[x] else (3 if x and ink[x - 1] else 0)
            w |= c << (14 - 2 * x)
        out += bytes((w & 0xFF, w >> 8))
    return bytes(out)


def button(text):
    """Bouton 16x8 (2 tuiles) : fond 2, texte 1, bord 3 à droite et en bas. Texte centré."""
    cols = []
    for gap in (1, 0):
        cols = []
        for i, ch in enumerate(text):
            a, b = font.width(ch)
            if i:
                cols += [None] * gap
            cols += [(ch, x) for x in range(a, b)]
        if len(cols) <= 15:
            break
    if len(cols) > 15:
        raise SystemExit(f'bouton {text!r} : trop large (15 pixels max)')
    left = (15 - len(cols)) // 2
    px = [[2] * 16 for _ in range(8)]
    for y in range(8):
        px[y][15] = 3
    px[7] = [3] * 16
    for i, c in enumerate(cols):
        if c:
            ch, x = c
            for y in range(7):
                if font.G[ch][y][x] == '#':
                    px[y][left + i] = 1
    tiles = []
    for t in range(2):
        b = bytearray()
        for y in range(8):
            w = 0
            for x in range(8):
                w |= px[y][8 * t + x] << (14 - 2 * x)
            b += bytes((w & 0xFF, w >> 8))
        tiles.append(bytes(b))
    return tiles


def parse_block(rom, start):
    """-> [(hdr, texte, terminateur)], taille totale."""
    out, e = [], start
    while True:
        hdr = rom[e] | rom[e + 1] << 8
        assert rom[e + 2] == 0 and rom[e + 3] == 0 and 0x4D <= rom[e + 1] <= 0x51, hex(e)
        j = e + 4
        while rom[j] not in (0xFE, 0xFF):
            j += 1
        out.append((hdr, bytes(rom[e + 4:j]), rom[j]))
        if rom[j] == 0xFF:
            return out, j + 1 - start
        e = j + 1


def find_refs(rom, targets):
    """Références du code : « lda reg, (adr) » = F2 lo mi hi 3x, et pointeurs 32 bits (lo mi hi 00)."""
    want = {t + CART: t for t in targets}
    refs = {t: [] for t in targets}
    for p in range(0x80000 - 5):
        a = rom[p + 1] | rom[p + 2] << 8 | rom[p + 3] << 16
        if rom[p] == 0xF2 and 0x30 <= rom[p + 4] <= 0x37 and a in want:
            refs[want[a]].append(p + 1)
        a = rom[p] | rom[p + 1] << 8 | rom[p + 2] << 16
        if rom[p + 3] == 0 and a in want and not (p and rom[p - 1] == 0xF2):
            refs[want[a]].append(p)
    return refs


# --- menus en cadre (police des dialogues, listes de glyphes) -----------------------------------

def glyph_code(rom, p):
    v = struct.unpack_from('<I', rom, p)[0] - CART - FONT1
    return v // 16 if 0 <= v < 16 * 256 and v % 16 == 0 else None


def parse_menu(rom, r):
    """Lit le code qui affiche le menu : liste, nb de glyphes, gabarit (adresse, colonnes, lignes)."""
    assert rom[r - 1] == 0xF2 and rom[r + 3] == 0x36, f'menu {r:X} : code inattendu'
    lst = (rom[r] | rom[r + 1] << 8 | rom[r + 2] << 16) - CART
    p = r - 5                                  # lda XDE, (0xA1xx)
    assert rom[p] == 0xF1 and rom[p + 3] == 0x32 and rom[p - 2] == 0x23, f'menu {r:X}'
    base = ((rom[p + 1] | rom[p + 2] << 8) - 0xA000) // 16
    q = r - 8
    while not (rom[q] == 0xF2 and rom[q + 4] == 0x36 and rom[q + 3] in (0x20, 0x21)
               and rom[q + 5] == 0x31):
        q -= 1
    tmpl = (rom[q + 1] | rom[q + 2] << 8 | rom[q + 3] << 16) - CART
    cnt = rom[p - 1]
    return dict(ref=r, list=lst, cnt_off=p - 1, cnt=cnt, base=base, tmpl=tmpl,
                cols=rom[q + 6], rows=rom[q + 7],
                trailing=glyph_code(rom, lst + 4 * cnt) is not None)


def menu_fields(rom, m):
    """Champs de texte du gabarit : [(ligne, col, longueur japonaise, place max, codes JP)]."""
    cols, rows, base, cnt = m['cols'], m['rows'], m['base'], m['cnt']

    def tile(y, x):
        return struct.unpack_from('<H', rom, m['tmpl'] + 2 * (y * cols + x))[0] & 0x1FF

    def is_text(y, x):
        return base <= tile(y, x) < base + cnt

    out = []
    for y in range(rows):
        x = 0
        while x < cols:
            if not is_text(y, x):
                x += 1
                continue
            s = x
            while x < cols and is_text(y, x):
                x += 1
            jp = [glyph_code(rom, m['list'] + 4 * (tile(y, k) - base)) for k in range(s, x)]
            e = x                               # étendre sur les cases vides…
            while e < cols and tile(y, e) == 1:
                e += 1
            if e < cols and is_text(y, e):      # …en gardant la case du curseur avant le champ suivant
                e -= 1
            out.append((y, s, x - s, e - s, jp))
    return out


def apply_menu(rom, m, texts, free, errors):
    where = f'interface @MENU {m["ref"]:X}'
    fields = menu_fields(rom, m)
    if len(texts) != len(fields):
        errors.append(f'{where}: {len(texts)} lignes, il en faut {len(fields)}')
        return free
    enc = []
    for (y, x, n, room, _), t in zip(fields, texts):
        b = encode(t.replace('_', ' '), where, errors)
        if len(b) > room:
            errors.append(f'{where}: « {t} » : {len(b)} car. > {room} (ligne {y}, colonne {x})')
        enc.append(b)
    letters = []
    for b in enc:
        for c in b:
            if c != font.CODE[' '] and c not in letters:
                letters.append(c)
    limit = m['cnt'] if m['trailing'] else max(m['cnt'], MENU_MAX_TILES)
    if len(letters) > limit:
        errors.append(f'{where}: {len(letters)} lettres différentes > {limit} tuiles disponibles')
        return free
    cnt = max(len(letters), m['cnt']) if m['trailing'] else len(letters)
    glyphs = letters + [font.CODE[' ']] * (cnt - len(letters))
    y0, x0 = fields[0][0], fields[0][1]
    attr = struct.unpack_from('<H', rom, m['tmpl'] + 2 * (y0 * m['cols'] + x0))[0] & 0xFE00
    for (y, x, n, room, _), b in zip(fields, enc):
        for k in range(room):
            p = m['tmpl'] + 2 * (y * m['cols'] + x + k)
            c = b[k] if k < len(b) else font.CODE[' ']
            word = 0x0001 if c == font.CODE[' '] else attr | (m['base'] + letters.index(c))
            struct.pack_into('<H', rom, p, word)
    blob = b''.join(struct.pack('<I', CART + FONT1 + 16 * c) for c in glyphs)
    if cnt <= m['cnt']:
        rom[m['list']:m['list'] + len(blob)] = blob
    else:
        rom[free:free + len(blob)] = blob
        rom[m['ref']:m['ref'] + 3] = (free + CART).to_bytes(3, 'little')
        free += len(blob)
    rom[m['cnt_off']] = cnt
    return free


def pos_menu_fields(rom):
    pm = POS_MENU
    lst = (rom[pm['list_ref']] | rom[pm['list_ref'] + 1] << 8 | rom[pm['list_ref'] + 2] << 16) - CART
    cells = [struct.unpack_from('<H', rom, pm['pos'] + 2 * k)[0] for k in range(pm['n'])]
    codes = [glyph_code(rom, lst + 4 * k) for k in range(pm['n'])]
    fields = []
    for c, a in zip(codes, cells):
        if fields and a == fields[-1][1] + 2 * len(fields[-1][2]):
            fields[-1][2].append(c)
        else:
            fields.append([lst, a, [c]])
    return lst, [(a, cs) for _, a, cs in fields]


def apply_pos_menu(rom, texts, errors):
    pm = POS_MENU
    where = 'interface @MENU 141AB'
    lst, fields = pos_menu_fields(rom)
    if len(texts) != len(fields):
        errors.append(f'{where}: {len(texts)} lignes, il en faut {len(fields)}')
        return
    glyphs, cells = [], []
    for (a, _), t in zip(fields, texts):
        b = encode(t, where, errors)
        if len(b) > 5:
            errors.append(f'{where}: « {t} » : 5 car. max')
        for k, c in enumerate(b):
            glyphs.append(c)
            cells.append(a + 2 * k)
    if len(glyphs) > pm['n']:
        errors.append(f'{where}: {len(glyphs)} lettres au total > {pm["n"]}')
        return
    for k, (c, a) in enumerate(zip(glyphs, cells)):
        struct.pack_into('<I', rom, lst + 4 * k, CART + FONT1 + 16 * c)
        struct.pack_into('<H', rom, pm['pos'] + 2 * k, a)
    rom[pm['cnt']] = len(glyphs)
    rom[pm['pos_cnt']] = len(glyphs)


# --- langue ---------------------------------------------------------------------------------

def encode(s, where, errors):
    b = bytearray()
    for tok in re.findall(r'\{[0-9A-Fa-f]{2}\}|.', s):
        if tok.startswith('{'):
            b.append(int(tok[1:3], 16))
        elif tok == '_':
            b.append(BLANK)
        elif tok == '¥':
            b.append(YEN)
        elif tok in font.CODE:
            b.append(font.CODE[tok])
        elif tok in font.DIGITS:
            b.append(font.DIGITS[tok])
        else:
            errors.append(f'{where}: caractère sans glyphe {tok!r}')
    return bytes(b)


def load_file(path):
    blocks, cur = {}, None
    for n, line in enumerate(open(path, encoding='utf-8'), 1):
        line = line.rstrip('\n')
        if line.startswith('#') or not line.strip():
            continue
        if line.startswith('@MENU') or line.startswith('@RAW'):
            kind = line[1:].split()[0]
            cur = (kind, int(line[1 + len(kind):].split()[0], 16))
            blocks[cur] = []
        elif line.startswith('@'):
            cur = int(line[1:].split()[0], 16)
            blocks[cur] = []
        elif cur is None:
            raise SystemExit(f'{path}:{n}: texte avant le premier @BLOC')
        else:
            blocks[cur].append(line.rstrip())
    return blocks


def starts(ja):
    """Colonnes où commence une option (le curseur s'affiche dans la case juste avant)."""
    menu = b'\x19\x01' in ja or (ja[:1] == bytes([BLANK])) or 0xF8 in ja
    out = []
    for i in range(1, len(ja)):
        if ja[i] != BLANK and ja[i - 1] == BLANK and (menu or (i >= 2 and ja[i - 2] == BLANK)):
            out.append(i)
    return out


def check_entry(ja, fr, hdr, where, errors):
    col, _ = col_row(hdr)
    if col + len(fr) > 19:
        errors.append(f'{where}: {len(fr)} car. à partir de la colonne {col} : déborde de l\'écran')
    for i in starts(ja):
        if i >= len(fr) or fr[i] == BLANK or fr[i - 1] != BLANK:
            errors.append(f'{where}: une option commence en position {i} dans l\'original '
                          f'(curseur en {i - 1}) : garder « _ » en {i - 1} et le texte en {i}')


def build_block(rom, start, lines, errors):
    entries, size = parse_block(rom, start)
    where = f'interface @{start:05X}'
    if len(lines) != len(entries):
        errors.append(f'{where}: {len(lines)} lignes, il en faut {len(entries)}')
        return None, size
    out = bytearray()
    for k, ((hdr, ja, term), line) in enumerate(zip(entries, lines)):
        fr = encode(line, f'{where} ligne {k + 1}', errors)
        fr += bytes([BLANK]) * (len(ja) - len(fr))       # efface la fin de l'original
        check_entry(ja, fr, hdr, f'{where} ligne {k + 1}', errors)
        out += struct.pack('<H', hdr) + b'\0\0' + fr + bytes([term])
    return bytes(out), size


def apply(rom, lang, lang_dir, errors):
    """Applique toute l'interface de la langue. Renvoie un résumé."""
    if bytes(rom[UI_FREE:UI_END]) != b'\xff' * (UI_END - UI_FREE):
        raise SystemExit(f'interface : la zone 0x{UI_FREE:X}-0x{UI_END:X} n\'est pas libre '
                         '(texte des dialogues trop long ?)')
    # 1. 2e police + boutons
    for ch, code in font.CODE.items():
        for base in FONT2:
            rom[base + 16 * code: base + 16 * code + 16] = tile_shadow(font.G[ch])
    for (a, b), text in zip(TOGGLE_TILES, lang.NAME_BUTTONS):
        ta, tb = button(text)
        for base in FONT2:
            rom[base + 16 * a: base + 16 * a + 16] = ta
            rom[base + 16 * b: base + 16 * b + 16] = tb

    # 2. grille de saisie du nom
    for page, (sel, show) in enumerate(zip(GRID_SEL, GRID_SHOW)):
        rows = lang.NAME_GRID[page]
        if len(rows) != 6 or any(len(r) != 15 for r in rows):
            errors.append(f'NAME_GRID page {page + 1} : il faut 6 lignes de 15 caractères')
            continue
        codes = []
        for r in rows:
            for ch in r:
                codes.append(GRID_EMPTY if ch == ' ' else
                             (encode(ch, f'NAME_GRID page {page + 1}', errors) or b'\0')[0])
        rom[sel:sel + 90] = bytes(codes)
        e = show
        for y in range(6):
            assert rom[e + 1] in (0x4F, 0x50) and rom[e + 2] == 0, hex(e)
            row = codes[15 * y:15 * y + 15]
            rom[e + 4:e + 21] = bytes(row[0:5] + [BLANK] + row[5:10] + [BLANK] + row[10:15])
            assert rom[e + 21] == 0xFE
            e += 22

    # 3. tables régions / lieux à 8 caractères (relogées)
    free = UI_FREE
    for table, n, names, label in ((REGION_TABLE, REGION_N, lang.REGION_TABLE, 'REGION_TABLE'),
                                   (PLACE_TABLE, PLACE_N, lang.PLACE_TABLE, 'PLACE_TABLE')):
        if len(names) != n:
            errors.append(f'{label} : {len(names)} noms, il en faut {n}')
            continue
        blob = bytearray()
        for name in names:
            b = encode(name, f'{label} {name!r}', errors)
            if len(b) > WIDE:
                errors.append(f'{label} {name!r} : {len(b)} car. > {WIDE}')
            blob += (b + bytes([BLANK]) * WIDE)[:WIDE]
        rom[free:free + len(blob)] = blob
        for mul, adr, cnt, t in TABLE_CODE:
            if t != table:
                continue
            assert rom[mul] == 6 and rom[cnt] == 6, 'code inattendu'
            assert struct.unpack_from('<I', rom, adr)[0] == table + CART, 'code inattendu'
            rom[mul] = WIDE
            rom[cnt] = WIDE
            struct.pack_into('<I', rom, adr, free + CART)
        free += len(blob)

    # 4. menus en cadre (police des dialogues)
    texts = load_file(os.path.join(lang_dir, 'interface.txt'))
    for r in GLYPH_MENUS:
        if ('MENU', r) not in texts:
            errors.append(f'interface @MENU {r:X} : menu non traduit')
            continue
        free = apply_menu(rom, parse_menu(rom, r), texts[('MENU', r)], free, errors)
    if ('MENU', POS_MENU['list_ref']) in texts:
        apply_pos_menu(rom, texts[('MENU', POS_MENU['list_ref'])], errors)
    else:
        errors.append(f'interface @MENU {POS_MENU["list_ref"]:X} : menu non traduit')
    menus = {('MENU', r) for r in GLYPH_MENUS + [POS_MENU['list_ref']]}

    # 4b. chaînes brutes
    raw_refs = find_refs(rom, RAW)
    for off in RAW:
        where = f'interface @RAW {off:05X}'
        if ('RAW', off) not in texts:
            errors.append(f'{where} : non traduit')
            continue
        lines = [b'' if t == '~' else encode(t, where, errors) for t in texts[('RAW', off)]]
        if off in DUEL_A + DUEL_B:
            if len(lines) > 3:
                errors.append(f'{where} : {len(lines)} lignes > 3')
            for t, b in zip(texts[('RAW', off)], lines):
                if len(b) > DUEL_COLS and not any(0xF4 <= c <= 0xFD for c in b):
                    errors.append(f'{where} : « {t} » : {len(b)} car. > {DUEL_COLS}')
        new = b'\xfe'.join(lines) + b'\xff'
        old = rom.index(0xFF, off) + 1 - off
        if len(new) <= old:
            rom[off:off + len(new)] = new
        elif raw_refs[off]:
            rom[free:free + len(new)] = new
            for p in raw_refs[off]:
                rom[p:p + 3] = (free + CART).to_bytes(3, 'little')
            free += len(new)
        else:
            errors.append(f'interface @RAW {off:05X} : trop long et pas de pointeur')
        menus.add(('RAW', off))

    # 5. blocs de chaînes
    unknown = set(texts) - set(BLOCKS) - menus
    for u in sorted(unknown, key=str):
        errors.append(f'interface {u} : bloc inconnu')
    texts = {k: v for k, v in texts.items() if k not in menus}
    for u in sorted(unknown):
        errors.append(f'interface @{u:05X} : bloc inconnu')
    refs = find_refs(rom, BLOCKS)
    moved = inplace = 0
    for start in BLOCKS:
        if start not in texts:
            errors.append(f'interface @{start:05X} : bloc non traduit')
            continue
        new, size = build_block(rom, start, texts[start], errors)
        if new is None:
            continue
        if len(new) <= size:
            rom[start:start + len(new)] = new
            inplace += 1
        elif refs[start]:
            if free + len(new) > UI_END:
                errors.append('interface : plus de place pour reloger')
                continue
            rom[free:free + len(new)] = new
            for p in refs[start]:
                rom[p:p + 3] = (free + CART).to_bytes(3, 'little')
            free += len(new)
            moved += 1
        else:
            errors.append(f'interface @{start:05X} : {len(new) - size} octet(s) de trop et pas de '
                          'pointeur pour le reloger : raccourcir')
    return inplace, moved, free - UI_FREE


# --- extraction (pour les traducteurs) -------------------------------------------------------

def main():
    import build
    import extract
    ap = argparse.ArgumentParser()
    ap.add_argument('--rom', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--ref', help='code de langue dont la traduction est ajoutée sous chaque ligne')
    a = ap.parse_args()
    rom = open(a.rom, 'rb').read()
    build.check_rom(rom)
    ref = {}
    if a.ref:
        ref = load_file(os.path.join(build.ROOT, 'lang', a.ref, 'interface.txt'))
    out = ['# Chaînes d\'interface (2e police). « _ » = case vide. (col, ligne) = position à l\'écran.',
           '# Une option commence là où l\'original a « _ » puis du texte : le curseur va dans le « _ ».']
    for start in BLOCKS:
        entries, _ = parse_block(rom, start)
        out.append(f'@{start:05X}')
        for k, (hdr, ja, term) in enumerate(entries):
            c, r = col_row(hdr)
            txt = ''.join('_' if x == BLANK else extract.JA.get(x, '{%02X}' % x) for x in ja)
            out.append(f'{txt:<24} # col {c}, ligne {r}, {len(ja)} cases')
            if start in ref and k < len(ref[start]):
                out.append(f'    {a.ref}| {ref[start][k]}')
    out.append('')
    out.append('# Menus en cadre (police des dialogues) : une ligne par mot, « place » = longueur max.')
    out.append('# Chaque lettre DIFFÉRENTE prend une tuile : 16 au plus par menu (21 pour @MENU DDC8).')

    def jp(codes):
        return ''.join(extract.JA.get(c, '{%02X}' % c) for c in codes)
    for r in GLYPH_MENUS:
        m = parse_menu(rom, r)
        out.append(f'@MENU {r:X}')
        fields = menu_fields(rom, m)
        for k, (y, x, n, room, codes) in enumerate(fields):
            out.append(f'{jp(codes):<24} # ligne {y}, colonne {x}, place {room}')
            key = ('MENU', r)
            if key in ref and k < len(ref[key]):
                out.append(f'    {a.ref}| {ref[key][k]}')
    out.append('')
    out.append('# Chaînes brutes (une ligne chacune ; plus longue que l\'original = relogée).')
    for off in RAW:
        j = rom.index(0xFF, off)
        out.append(f'@RAW {off:05X}')
        for line in rom[off:j].split(b'\xfe'):
            out.append(''.join('_' if c == BLANK else extract.JA.get(c, '{%02X}' % c) for c in line)
                       or '~')
        for t in ref.get(('RAW', off), []):
            out.append(f'    {a.ref}| {t}')
    out.append('')
    out.append(f'@MENU {POS_MENU["list_ref"]:X}')
    _, fields = pos_menu_fields(rom)
    for k, (cell, codes) in enumerate(fields):
        out.append(f'{jp(codes):<24} # place 5 ; 10 lettres au total pour ce menu')
        key = ('MENU', POS_MENU['list_ref'])
        if key in ref and k < len(ref[key]):
            out.append(f'    {a.ref}| {ref[key][k]}')
    tmp = a.out + '.tmp'
    open(tmp, 'w', encoding='utf-8').write('\n'.join(out) + '\n')
    os.replace(tmp, a.out)
    print(len(BLOCKS), 'blocs ->', a.out)


if __name__ == '__main__':
    main()
