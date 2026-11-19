"""Réglages de la langue FRANÇAISE (copier ce dossier pour une autre langue).

Tout ce qui n'est pas du texte de dialogue se règle ici. Les dialogues sont dans les *.txt.
"""

# Logo de l'écran titre : (texte, fichier de police, taille en px, y du haut).
# Le fichier de police n'est PAS fourni : mettez une police que vous avez le droit
# d'utiliser, soit dans ce dossier, soit dans les polices du système (cherchées automatiquement).
# La VF a été faite avec « Impact » (police système de Windows).
TITLE_LINES = [
    ('SHIGERU MIZUKI', 'impact.ttf', 11, 12),
    ('LE STUDIO PHOTO', 'impact.ttf', 17, 25),
    ('DES YÔKAI', 'impact.ttf', 22, 45),
]

# Menu de l'écran titre (image) : 4 entrées, largeur max en pixels = 8 x tuiles.
# Ordre : はじめる (nouvelle partie), つづきから (continuer), アルバム (album), フォトバトル (duel).
MENU = ['Début', 'Reprise', 'Album', 'Versus']

# Lettres en plus de la police latine de base (tools/font_latin.py) :
#   'caractère': (code, [8 lignes de 5 colonnes, '#' = encre])
# Codes libres sûrs : 0x2D-0x36, 0x5B-0x76, 0xB0-0xE4 (anciennes cases kana, plus utilisées
# une fois tout le texte traduit). Ne JAMAIS utiliser 0xF0-0xFF (codes de contrôle),
# 0xA0-0xA9 (chiffres), 0x79 (¥), 0x7A (・), 0x7D/0x7E (boutons A/B), 0x3A (espace).
EXTRA_GLYPHS = {}

# Noms de destination des tickets de train (tools/tarifs.py).
DESTINATIONS = {
    'なは': 'Naha', 'あきた': 'Akita', 'とやま': 'Toyama', 'ながの': 'Nagano', 'いずも': 'Izumo',
    'なごや': 'Nagoya', 'なりた': 'Narita', 'ちとせ': 'Chitose', 'くしろ': 'Kushiro', 'いとう': 'Itô',
    'こうち': 'Kôchi', 'やまがた': 'Yamagata', 'せんだい': 'Sendai', 'さっぽろ': 'Sapporo',
    'おおさか': 'Osaka', 'おかやま': 'Okayama', 'まつやま': 'Matsuyama', 'かごしま': 'Kagoshima',
    'かんさい': 'Kansai', 'みやざき': 'Miyazaki', 'にいがた': 'Niigata', 'ながさき': 'Nagasaki',
    'りょうつ': 'Ryôtsu', 'くしもと': 'Kushimoto', 'とうきょう': 'Tôkyô', 'しものせき': 'Shimonoseki',
    'みやけじま': 'Miyakejima',
}
