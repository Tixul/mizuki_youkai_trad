"""Écran titre en français : panneau de bois (SCR2), titre (SCR1), menu en image.

Tout est en clair dans la ROM (mesuré le 18/11/2026) :
  * tuiles du titre : 480 tuiles brutes 2bpp à 0x100AAE (copiées telles quelles en 0xA000) ;
  * tilemap SCR1 : 20x20 mots à 0x1003BE ; tilemap SCR2 : 20x20 mots à 0x100736 ;
  * palettes : SCR1 à 0x1006B6, SCR2 à 0x100A2E (8 x 4 couleurs, 0x0BGR).
Le logo d'origine est réparti sur les DEUX plans : corps clair + ombre dans le bois (SCR2,
une tuile unique par case), reflets orange par-dessus (SCR1, palette 1). On refait les deux.
Le menu (はじめる…) est lui aussi une image : tuiles 0x83-0x95 de SCR1, palette 5.
"""
import math
import random

from PIL import Image, ImageDraw, ImageFont

import glob
import os

import font_latin as font_fr

CHR = 0x100AAE
MAP1 = 0x1003BE
MAP2 = 0x100736
PAL1 = 0x1006B6
PAL2 = 0x100A2E

# Logo : cases lignes 1-8, colonnes 1-18 des deux plans.
ROWS = range(1, 9)
COLS = range(1, 19)
SCR1_FREE = list(range(0x01, 0x81))       # 0x81/0x82 = « TM », gardées
MENU_SLOTS = [(0x83, 4), (0x87, 5), (0x8C, 4), (0x90, 6)]   # (1re tuile, nb de tuiles) par entrée
FONT_DIRS = []            # dossier de la langue, ajouté par build.py ; puis polices système :
SYSTEM_FONT_DIRS = ['C:/Windows/Fonts', '/usr/share/fonts', '/usr/local/share/fonts',
                    os.path.expanduser('~/.fonts'), os.path.expanduser('~/.local/share/fonts'),
                    '/Library/Fonts', '/System/Library/Fonts', os.path.expanduser('~/Library/Fonts')]


def find_font(fname):
    """Cherche le fichier de police (non fourni) : dossier de la langue, puis système."""
    for d in FONT_DIRS + SYSTEM_FONT_DIRS:
        hits = [p for p in glob.glob(os.path.join(d, '**', '*'), recursive=True)
                if os.path.basename(p).lower() == fname.lower()]
        if hits:
            return hits[0]
    raise SystemExit(f'police « {fname} » introuvable : copiez-la dans le dossier de la langue')

# Yeux rouges du logo = 3 SPRITES (tuiles 0x1E5-0x1E7, pixels utiles x 5..17, y 2..6).
# Liste de sprites du titre à 0x82CB : en-tête 4 octets puis (tuile, attr, dx, dy) relatifs
# à l'objet posé en (80, 0) ; entrées 4-6 = les yeux (avant : coin haut-gauche (24, 32)).
SPRITES = 0x82CB
OBJ_X, OBJ_Y = 80, 0
EYES = (125, 51)          # coin haut-gauche de la 1re tuile des yeux, à l'écran


def apply_eyes(rom):
    x, y = EYES
    for k in range(3):
        o = SPRITES + 4 + 4 * (4 + k)
        assert rom[o] == 0xE5 + k, 'liste de sprites inattendue'
        rom[o + 2] = (x + 8 * k - OBJ_X) & 0xFF
        rom[o + 3] = (y - OBJ_Y) & 0xFF


def get_tile(rom, t):
    b = rom[CHR + 16 * t: CHR + 16 * t + 16]
    return [[((b[2 * y] | b[2 * y + 1] << 8) >> (14 - 2 * x)) & 3 for x in range(8)] for y in range(8)]


def put_tile(rom, t, px):
    out = bytearray()
    for y in range(8):
        w = 0
        for x in range(8):
            w |= (px[y][x] & 3) << (14 - 2 * x)
        out += bytes((w & 0xFF, w >> 8))
    rom[CHR + 16 * t: CHR + 16 * t + 16] = out


def read_map(rom, base):
    return [[rom[base + 2 * (r * 20 + c)] | rom[base + 2 * (r * 20 + c) + 1] << 8
             for c in range(20)] for r in range(20)]


def write_map_cell(rom, base, r, c, word):
    o = base + 2 * (r * 20 + c)
    rom[o], rom[o + 1] = word & 0xFF, word >> 8


def palettes(rom, base):
    out = []
    for p in range(16):                        # 0x40 mots copiés = 16 palettes
        cols = []
        for k in range(4):
            v = rom[base + p * 8 + 2 * k] | rom[base + p * 8 + 2 * k + 1] << 8
            cols.append(((v & 15) * 17, (v >> 4 & 15) * 17, (v >> 8 & 15) * 17))
        out.append(cols)
    return out


def plane_indices(rom, base, h=10):
    """Image d'indices 0-3 (160 x 8h) d'un plan, + palette de chaque pixel."""
    m = read_map(rom, base)
    idx = [[0] * 160 for _ in range(8 * h)]
    pal = [[0] * 160 for _ in range(8 * h)]
    for r in range(h):
        for c in range(20):
            w = m[r][c]
            px = get_tile(rom, (w & 0xFF) | (w >> 8 & 1) << 8)
            for y in range(8):
                for x in range(8):
                    idx[r * 8 + y][c * 8 + x] = px[y][x]
                    pal[r * 8 + y][c * 8 + x] = w >> 9 & 15
    return idx, pal


# ---------------------------------------------------------------- dessin du logo
def text_mask(lines):
    """lines = [(texte, police, taille, y_haut)] -> masque 160x80 (pixels nets, centrés)."""
    W, H = 160, 80
    mask = [[False] * W for _ in range(H)]
    for text, fname, size, ytop in lines:
        f = ImageFont.truetype(find_font(fname), size)
        im = Image.new('1', (W * 2, H), 0)
        dr = ImageDraw.Draw(im)
        dr.fontmode = '1'                               # pas d'anticrénelage
        dr.text((0, 0), text, font=f, fill=1)
        bb = im.getbbox()
        im = im.crop(bb)
        x0 = (W - im.width) // 2
        for y in range(im.height):
            for x in range(im.width):
                if im.getpixel((x, y)) and 0 <= ytop + y < H and 0 <= x0 + x < W:
                    mask[ytop + y][x0 + x] = True
    return mask


def wood(x, y, rnd):
    """Bois sombre procédural, dans l'esprit du panneau d'origine (0 noir, 1 brun, 2 brun clair)."""
    v = math.sin((y * 1.7 + 4 * math.sin(x / 11.0) + 2.5 * math.sin(x / 5.3 + y / 9.0)) / 2.1)
    v += 0.6 * math.sin(x / 17.0 + y / 4.0) + rnd.uniform(-0.45, 0.45)
    if v < -1.05:
        return 0
    if v < -0.25:
        return 1 if (x + y) % 2 else 2          # trame brun/brun clair
    if v < 0.35:
        return 2 if (x * 3 + y) % 5 else 1
    return 2


def build_logo(rom, lines, inner=(10, 10, 150, 70), rivet=6):
    mask = text_mask(lines)
    scr2, _ = plane_indices(rom, MAP2)
    rnd = random.Random(1999)
    x0, y0, x1, y1 = inner

    def is_rivet(x, y):
        return ((x < x0 + rivet or x >= x1 - rivet) and (y < y0 + rivet or y >= y1 - rivet))

    # 1) SCR2 : bois propre + contour et ombre noirs du texte
    new2 = [row[:] for row in scr2]
    for y in range(y0, y1):
        for x in range(x0, x1):
            if not is_rivet(x, y):
                new2[y][x] = wood(x, y, rnd)
    M = lambda x, y: 0 <= y < 80 and 0 <= x < 160 and mask[y][x]
    for y in range(y0, y1):
        for x in range(x0, x1):
            if M(x, y):
                continue
            near = any(M(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1))
            shadow = M(x - 1, y - 1) or M(x - 2, y - 2)
            if near or shadow:
                new2[y][x] = 0
    # 1b) tache d'ombre où se posent les yeux (sprites), cf. EYES
    ex, ey = EYES
    cx, cy = ex + 11, ey + 4                     # centre des pixels des yeux
    for y in range(y0, y1):
        for x in range(x0, x1):
            d = ((x - cx) / 11.0) ** 2 + ((y - cy) / 6.0) ** 2
            if d < 1.0 or (d < 1.4 and (x + y) % 2):
                new2[y][x] = 0
    # 2) SCR1 : lettres orange, reflet crème en haut, orange sombre en bas
    new1 = [[0] * 160 for _ in range(80)]
    for y in range(80):
        for x in range(160):
            if M(x, y):
                new1[y][x] = 3 if not M(x, y - 1) else (1 if not M(x, y + 1) else 2)
    return new1, new2


def apply_logo(rom, new1, new2):
    m2 = read_map(rom, MAP2)
    pool = iter(SCR1_FREE)
    seen = {}
    for r in ROWS:
        for c in COLS:
            px = [new1[r * 8 + y][c * 8:c * 8 + 8] for y in range(8)]
            key = tuple(map(tuple, px))
            if not any(any(row) for row in px):
                write_map_cell(rom, MAP1, r, c, 0)
                continue
            if key not in seen:
                t = next(pool)          # StopIteration = trop de tuiles : on le saura
                put_tile(rom, t, px)
                seen[key] = t
            write_map_cell(rom, MAP1, r, c, seen[key] | 1 << 9)    # palette 1
    for r in ROWS:
        for c in (0, 19):
            write_map_cell(rom, MAP1, r, c, 0)
    # SCR2 : la plupart des cases du panneau ont leur propre tuile -> réécrite sur place.
    # ⚠️ Certaines servent AUSSI au bois du bas de l'écran (mesuré : 0x111, 0x122, 0x124,
    # 0x134, 0x13B, 0x148) : celles-là reçoivent une tuile NEUVE du reste du pool.
    used = {}
    for r in range(20):
        for c in range(20):
            t = (m2[r][c] & 0xFF) | (m2[r][c] >> 8 & 1) << 8
            used[t] = used.get(t, 0) + 1
    fresh = 0
    for r in ROWS:
        for c in COLS:
            w = m2[r][c]
            t = (w & 0xFF) | (w >> 8 & 1) << 8
            px = [new2[r * 8 + y][c * 8:c * 8 + 8] for y in range(8)]
            if used[t] == 1:
                put_tile(rom, t, px)
            else:
                nt = next(pool)
                put_tile(rom, nt, px)
                write_map_cell(rom, MAP2, r, c, (w & 0xFE00) | nt)
                fresh += 1
    return len(seen), fresh


# ---------------------------------------------------------------- menu en image
def apply_menu(rom, words):
    """words = 4 entrées du menu titre (voir lang.py MENU)."""
    if len(words) != 4:
        raise SystemExit('MENU : il faut exactement 4 entrées')
    for (first, n), text in zip(MENU_SLOTS, words):
        W = 8 * n
        ink = [[0] * W for _ in range(8)]
        x = 0
        for ch in text:
            a, b = font_fr.width(ch)
            for y in range(8):
                for gx in range(a, b):
                    if font_fr.G[ch][y][gx] == '#':
                        if x + gx - a < W:
                            ink[y][x + gx - a] = 1
            x += (b - a) + 1
        if x - 1 > W:
            raise SystemExit(f'menu « {text} » : {x - 1} px pour {W}')
        px = [[0] * W for _ in range(8)]
        for y in range(8):
            for xx in range(W):
                if ink[y][xx]:
                    px[y][xx] = 3
                elif y and xx and ink[y - 1][xx - 1]:
                    px[y][xx] = 1           # ombre grise en bas à droite
        for k in range(n):
            put_tile(rom, first + k, [px[y][8 * k:8 * k + 8] for y in range(8)])


def preview(rom, path):
    """Rendu des deux plans du titre (sans le menu), pour contrôle visuel."""
    p1, p2 = palettes(rom, PAL1), palettes(rom, PAL2)
    i1, q1 = plane_indices(rom, MAP1, 20)
    i2, q2 = plane_indices(rom, MAP2, 20)
    im = Image.new('RGB', (160, 152))
    for y in range(152):
        for x in range(160):
            if i1[y][x]:
                im.putpixel((x, y), p1[q1[y][x]][i1[y][x]])
            elif i2[y][x]:
                im.putpixel((x, y), p2[q2[y][x]][i2[y][x]])
            else:
                im.putpixel((x, y), (17, 17, 17))
    im.resize((480, 456), Image.NEAREST).save(path)
