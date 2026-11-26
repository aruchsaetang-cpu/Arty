"""Street fashion of Sol, from the user's references (Korean street style and runway): outfits as style overrides
for character_mh.build. Colours are (base, shade). Used by the city crowd (city.extra_style) and the shop customers
(customers.py). Patterns (stripes, plaid) are carried by colour; wide=1 is a full wide-leg trouser."""

def _c(base, shade): return (base, shade)

BLACK = _c("#17181b", "#060708"); WHITE = _c("#f1eee8", "#a6a39c"); CREAM = _c("#ebe4d4", "#a59d8d")
BEIGE = _c("#cdbb98", "#857659"); KHAKI = _c("#bba57c", "#776647"); NAVY = _c("#1c2333", "#0a0d15")
TAN_LOAFER = (("#9c7650", "#5a4128"), dict(loafer=True, sneakers=False))
BLACK_LOAFER = (("#151416", "#2a2626"), dict(loafer=True, sneakers=False))
BROWN_SHOE = (("#4a2e1e", "#24150d"), dict(loafer=False, sneakers=False))
WHITE_SNEAKER = (("#f2f2f0", "#d9d7d0"), dict(sneakers=True, loafer=False))
TOTE_BLACK = ("#1a1a1c", "#080809")

def look(shoes, **kw):
    col, flags = shoes
    d = dict(shoes=col, **flags); d.update(kw); return d

MEN = [
    # all black: oversized blazer, black tee, wide black trousers
    look(BLACK_LOAFER, coat=_c("#1b1c1f", "#08090a"), hem=0.8, open_coat=True, lapels=True, open_skirt=False,
         top=BLACK, turtleneck=False, leg_col=BLACK, wide=1.0),
    # open overshirts over a white tee, wide trousers, suede loafers, a black tote
    look(TAN_LOAFER, coat=_c("#5f6a45", "#2e341f"), hem=0.92, open_coat=True, top=WHITE, turtleneck=False,
         leg_col=CREAM, wide=1.0, bag=TOTE_BLACK),
    look(TAN_LOAFER, coat=BLACK, hem=0.92, open_coat=True, top=WHITE, turtleneck=False, leg_col=BEIGE, wide=1.0, bag=TOTE_BLACK),
    look(TAN_LOAFER, coat=_c("#4f6fa3", "#24365a"), hem=0.92, open_coat=True, top=WHITE, turtleneck=False,
         leg_col=WHITE, wide=1.0, bag=TOTE_BLACK),
    look(BROWN_SHOE, coat=_c("#5a3a2a", "#2a1a12"), hem=0.92, open_coat=True, top=WHITE, turtleneck=False, leg_col=KHAKI, wide=1.0),
    look(TAN_LOAFER, coat=WHITE, hem=0.92, open_coat=True, top=WHITE, turtleneck=False, leg_col=WHITE, wide=1.0, bag=TOTE_BLACK),
    # runway: olive field jacket + slim black trousers + white sneakers; black leather jacket + camel trousers
    look(WHITE_SNEAKER, coat=_c("#7d8466", "#41463a"), hem=0.84, top=_c("#c7432e", "#6a2016"), turtleneck=True, leg_col=BLACK),
    look(BROWN_SHOE, coat=_c("#18181a", "#050506"), hem=0.95, top=BLACK, turtleneck=False, leg_col=_c("#b08a5c", "#6a5234"), wide=0.6),
    # long navy coat over a navy hoodie, quilted navy trousers
    look(BLACK_LOAFER, coat=NAVY, hem=0.36, open_coat=True, top=_c("#232b40", "#0e1220"), hood=True, turtleneck=False,
         leg_col=_c("#2b3858", "#121a2c")),
    # cream shearling coat over black, white trousers
    look(WHITE_SNEAKER, coat=_c("#e6dac2", "#a09379"), hem=0.66, open_coat=True, lapels=True, top=BLACK, turtleneck=False,
         leg_col=WHITE, wide=0.5),
    # black double-breasted suit
    look(BLACK_LOAFER, coat=_c("#16171a", "#060607"), hem=0.74, lapels=True, top=_c("#c9a873", "#7d6640"), turtleneck=False,
         leg_col=BLACK, wide=0.4),
    # raspberry suit under a long tweed coat, white shirt
    look(BROWN_SHOE, coat=_c("#b8676e", "#6e3238"), hem=0.32, open_coat=True, lapels=True, top=WHITE, turtleneck=False,
         leg_col=_c("#a2404c", "#5a1c24")),
]

WOMEN = [
    # taupe oversized blazer, black flares
    look(BLACK_LOAFER, coat=_c("#8d7658", "#4e402e"), hem=0.74, open_coat=True, lapels=True, top=BLACK, turtleneck=False,
         legs="trousers", leg_col=BLACK, wide=0.6, bag=TOTE_BLACK),
    # cream knit, dark jeans, white sneakers
    look(WHITE_SNEAKER, coat=None, top=_c("#e8e1d2", "#9e9786"), turtleneck=True, legs="trousers", leg_col=_c("#2e3138", "#121318")),
    # long beige trench, light jeans, white sneakers
    look(WHITE_SNEAKER, coat=_c("#c9b28d", "#80704f"), hem=0.42, open_coat=True, lapels=True, top=WHITE, turtleneck=False,
         legs="trousers", leg_col=_c("#8fa7c4", "#52657e"), wide=0.7, bag=_c("#1d2230", "#0a0c12")),
    # cream cardigan, khaki wide trousers
    look(WHITE_SNEAKER, coat=_c("#efe6d2", "#a59c88"), hem=0.84, open_coat=True, top=WHITE, turtleneck=False,
         legs="trousers", leg_col=_c("#c2ae84", "#7b6b4c"), wide=1.0, bag=_c("#b07a4a", "#6a4626")),
    # butter-yellow blazer, white crop, mid jeans
    look(WHITE_SNEAKER, coat=_c("#e9dca0", "#a09460"), hem=0.8, open_coat=True, lapels=True, top=WHITE, turtleneck=False,
         legs="trousers", leg_col=_c("#7f9bc0", "#48607e"), wide=0.8),
    # denim jacket over a long cream skirt
    look(WHITE_SNEAKER, coat=_c("#7f9cc4", "#48607e"), hem=0.88, open_coat=True, top=WHITE, turtleneck=False,
         legs="skirt", leg_col=CREAM, skirt_hem=0.14),
    # pink denim jacket, grey slit skirt, white socks and sneakers
    look(WHITE_SNEAKER, coat=_c("#c96a86", "#7a3248"), hem=0.86, open_coat=True, top=CREAM, turtleneck=False,
         legs="skirt", leg_col=_c("#6b6b6e", "#353537"), skirt_hem=0.3, socks="#f4f4f2"),
    # sweater vest over a shirt, brown wide trousers
    look(WHITE_SNEAKER, coat=None, top=_c("#d9c7a8", "#8e7f62"), turtleneck=False, legs="trousers",
         leg_col=_c("#6b5440", "#3a2c20"), wide=1.0, bag=_c("#ece6da", "#a39d90")),
    # grey cardigan, white top, black slim trousers
    look(BLACK_LOAFER, coat=_c("#6e6f72", "#38393b"), hem=0.8, open_coat=True, top=WHITE, turtleneck=False,
         legs="trousers", leg_col=BLACK),
    # white tee, light-wash wide jeans
    look(WHITE_SNEAKER, coat=None, top=_c("#f4f2ee", "#a9a69f"), turtleneck=False, sleeves="short", legs="trousers",
         leg_col=_c("#9fb6cf", "#5d7088"), wide=1.2, bag=_c("#8a5a32", "#4e321b")),
    # sea-green plaid shirt open over white, jeans
    look(WHITE_SNEAKER, coat=_c("#6f8f8a", "#3a504c"), hem=0.9, open_coat=True, top=WHITE, turtleneck=False,
         legs="trousers", leg_col=_c("#87a0c0", "#4d607c"), wide=0.9),
    # oatmeal sweatshirt, dark brown trousers
    look(WHITE_SNEAKER, coat=None, top=_c("#cfc6b6", "#8a8273"), turtleneck=False, legs="trousers",
         leg_col=_c("#4a3a2c", "#241b14"), wide=0.8, bag=_c("#d8cfbe", "#958c7b")),
]
