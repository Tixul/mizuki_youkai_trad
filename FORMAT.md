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
  accents `0x1A-0x26`, ponctuation `0x27-0x2C`, A-Z `0x40-0x59`, Ç `0x5A`, É `0x2D`, `,` `0x37`, `.` `0x38`,
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

## Interface en fenêtres (`tools/interface.py`)

Tout ce qui n'est pas dans la boîte de dialogue. Le texte est hors de la zone `0x21000-0x32400`.

- **2e police** (fenêtres, saisie du nom, duels) : `0x1AA0D + 16 × code`, **copie identique** en
  `0x38DC9`. Mêmes codes que la police des dialogues ; style : lettre couleur 1, ombre couleur 3 à
  droite, fond 0. Boutons de la saisie du nom = glyphes `E5-EE`, `FB FC` (16×8, fond 2, bord 3).
- **Chaînes à position fixe** : `[adresse plan 2 octets][00 00] texte` puis `FE` (chaîne suivante
  du bloc) ou `FF` (fin). Adresse -> écran : `d = adr - 0x4DE7`, ligne `d // 40`, colonne
  `(d % 40) // 2`. `F1` = case vide ; le curseur s'affiche dans la case vide **avant** une option.
  42 blocs, référencés par `lda reg,(adr)` (`F2 lo mi hi 3x`) ou par un pointeur 32 bits ;
  un bloc trop long est relogé en `0x1F8000` et ses références réécrites.
- **Saisie du nom** : cases sélectionnables `0x10F16` (page 1) / `0x10F75` (page 2), 90 codes
  (6×15) + 5 boutons ; affichage `0x10FE6` / `0x1107D`. Nom en RAM `0x5C97` (6 octets, complété
  par `9A`), affiché tel quel dans les dialogues (`{F2}`). Case vide = `9A`.
- **Tables à largeur fixe**, passées de 6 à 8 caractères et relogées : régions `0x1118D` (11) et
  lieux `0x115CA` (44). Code modifié (multiplicateur, adresse, nombre de caractères) en
  `0x10C80/0x10C83/0x10C8F`, `0x11522/0x11525/0x1152D`, `0x11544/0x11547/0x1154F`.
- **Menus en cadre** (police des dialogues : menu B, boutique, auberge, sauvegarde…) : pas de
  chaîne, mais une **liste d'adresses de glyphes** (`0x21998D + 16 × code`, 32 bits chacune)
  chargée dans les tuiles `0x10…`, posées par un gabarit de cadre. Repère = `lda XIZ,(liste)` en
  `0xD99E, 0xDA9E, 0xDB66, 0xDC32, 0xDCF6, 0xDDC8, 0xDFBA, 0xE12E, 0xE1F2, 0xE2B6`. L'outil
  réécrit le gabarit et la liste (une tuile par lettre différente, 16 max ; 21 pour `0xDDC8` dont
  la liste se poursuit par les chiffres du prix). Menu `0x141AB` (duels) : liste + positions
  explicites, 10 lettres au total.
- **Duels photo** : module à part, messages en 2 copies (`0x374B4…`, contre l'ordinateur ;
  `0x3E725…`, par câble). Rendu propre : `FF` fin, `FE` ligne, `FD` somme, `FC` nombre,
  `F8` joueur, `F6` yôkai, `F4`/`F5` objet (sans octet paramètre), le reste dessiné tel quel.
  Texte en colonne 2, 3 lignes, pas de page suivante.

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
