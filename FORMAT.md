# Format de la ROM — notes techniques

ROM : *Mizuki Shigeru no Youkai Shashinkan (Japan)*, 2 Mio, en-tête `YOUKAISYASIN`, ID 0x0062.
Offsets = offsets **fichier** (adresse CPU = offset + 0x200000). Tout ce qui suit a été mesuré.

## Texte
- Zone de texte : `0x21000-0x32400`, non compressée, **1 octet = 1 caractère**.
- Table d'origine (gojûon) :
  - あ..ん `0x00-0x2D` ; ぁぃぅぇぉ `0x2E-0x32` ; っゃゅょ `0x33-0x36` ; 、。 `0x37 0x38` ; ー `0x39` ;
    espace `0x3A` ; 「」 `0x3B 0x3C` ; （） `0x3D 0x3E` ; 〜 `0x3F`
  - ア..ン `0x40-0x6D` ; petits katakana `0x6E-0x76` ; ？！ `0x77 0x78` ; ¥ `0x79` ; ・ `0x7A` ;
    ／ `0x7B` ; ■ `0x7C` ; boutons A B `0x7D 0x7E`
  - 〇一..九 `0x90-0x99` ; chiffres `0xA0-0xA9`
  - が..ご `0xB0`, ざ..ぞ `0xB5`, だぢづでど `0xBA-0xBE`, ば..ぼ `0xC0`, ぱ..ぽ `0xC5` ;
    ガ..ゴ `0xCA`, ザ..ド `0xD0-0xD9`, バ..ボ `0xDA`, パ..ポ `0xE0-0xE4`
- Codes de contrôle :

  | Code | Rôle |
  |---|---|
  | `FE` | retour à la ligne (présent aussi après `FF`/`FD`/`F7`, sauf exceptions) |
  | `FF` | fin du message |
  | `FD` | attente ▼ puis page suivante |
  | `FC` | attente puis changement de locuteur (ligne suivante = nom) |
  | `F7` `F6` | attentes (intro, narration) |
  | `F2` | nom du joueur |
  | `F3` `F4` | nombre inséré |
  | `F5` `F8` `F9` `FA` + 1 octet | fin de message avec action (objet, info…), **sans FE derrière** |
  | `F1…` | structures de données (pas du texte) |

- Un message qui ne finit pas par un terminateur **enchaîne** sur le suivant (lu en séquence).
- Certains messages finissent par `FF` sans `FE` : `build.py` recopie la fin exacte du japonais.

## Pointeurs
- 32 bits little-endian, valeur = offset + 0x200000.
- 22 tables (séquences d'au moins 4 pointeurs vers la zone de texte), dont la table principale
  des messages en `0x1670D` (~3 200 entrées), les noms de yôkai en `0x10291` (120) et leurs fiches
  en `0x1175F` (120). `build.pointer_tables()` les trouve.
- Des valeurs parasites ressemblent à des pointeurs au milieu des graphismes : on ne réécrit
  **que** les entrées de tables, et seulement vers un début de message traduit.
- Le texte traduit est relogé à partir de `0x190000` (zone libre `0x188E08-0x1FFFFF`, ~480 Kio).
  Le japonais d'origine reste en place, inutilisé.

## Police
- Glyphe(code) = 16 octets 2bpp bruts à `0x1998D + 16 × code` ; fond = couleur 1, encre = couleur 3.
- Chaque caractère affiché utilise une tuile neuve.
- La police latine du kit (`tools/font_latin.py`) remplace les cases kana : a-z `0x00`,
  accents `0x1A-0x26`, ponctuation `0x27-0x2C`, A-Z `0x40-0x59`, Ç `0x5A`, `,` `0x37`, `.` `0x38`,
  « » `0x3B 0x3C`, `-` `0x3F`, `?` `0x77`, `!` `0x78`. Chiffres, ¥, ・ et boutons gardés.
- Chasse fixe de 8 px.

## Affichage (mesuré dans un émulateur)
- Boîte de dialogue : **17 caractères** par ligne, 3 lignes sous l'onglet du nom.
- **Onglet du nom : 6 caractères** conservés d'une page à l'autre (le 7e et les suivants sont
  réutilisés par la page suivante).
- Menus à curseur : les espaces (`3A` ou `9A`) sont les cases du curseur, à colonnes fixes.

## Écran titre (`tools/gfx_title.py`)
- 480 tuiles 2bpp brutes en `0x100AAE`. Tilemaps 20×20 mots : SCR1 `0x1003BE`, SCR2 `0x100736`.
  Palettes : SCR1 `0x1006B6`, SCR2 `0x100A2E`.
- Le logo est sur deux plans : panneau de bois + ombre (SCR2), lettres orange (SCR1, palette 1).
  Six tuiles du panneau servent aussi au bois du bas de l'écran : elles reçoivent des tuiles neuves.
- Menu titre = image : tuiles SCR1 `0x83-0x95` (4/5/4/6 tuiles par entrée), palette 5.
- Yeux rouges du logo = sprites (tuiles `0x1E5-0x1E7`), liste de sprites en `0x82CB` (entrées 4-6).
- Non traduit : la mention de copyright en image (tuiles `0x96-0xA8`).

## Voyages (`tools/tarifs.py`)
- `0x2372C-0x23E40` : enregistrements `[prix 2 octets][00 00][n°] NOM FE [9A]PRIX FF`, plusieurs
  par bloc. Seul le nom est traduit, le reste est recopié à l'identique.

## Glossaire de la VF (pour garder la cohérence entre langues)

| Japonais | Français |
|---|---|
| ようかい | yôkai |
| みずきせんせい | Mizuki (nom) ; « le maître » dans le texte |
| おさ | roi (du Feu / de l'Eau / du Vent) / reine de la Terre |
| ふういん / おふだ | sceau / talisman |
| けっかい / もん / かぎ | barrière / portail / clé |
| こもんじょ | les vieux écrits |
| うんがい | l'Ungai (l'appareil photo) |
| ようりょく / ようき | yôryoku / aura |
| れいりょく / さつえいのうりょく / ようかいかんど | Esprit / Technique / Flair |
| ようかいしゃしんかん | le Studio Photo (la boutique, et le nom du jeu) |
| フォトバトル | duel photo (« Versus » au menu titre) |
| えつこ / げっこう / にっこう | Etsuko (fille de Mizuki) / Gekkô / Nikkô |
| ねずみおとこ / ぬらりひょん | Nezumi / Nurarihyon (« Nurari » dans l'onglet) |
