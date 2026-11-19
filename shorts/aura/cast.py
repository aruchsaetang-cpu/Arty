"""The cast of "Aura Monster" as style dicts for lookdev/character_mh.build (shared by film.py and lookdev/cast_v2.py).
Every face is different: the hero has the idol face and the only black-and-white eyes; everyone else gets their own
face sculpt (FACES in character_mh)."""

# the narrator before training: skinny kid, black hoodie with the hood down, grey joggers, pink sneakers, umbrella
NARR_A = dict(body="m_slim", height=1.78, skin=("#f1d3ba", "#b4876e"), face="boy", hair="bangs", hair_col="#15171c",
              locks=False, top=("#1f2026", "#08090c"), turtleneck=True, hood=True, coat=None, manhwa_head=True,
              legs="trousers", leg_col=("#7c7f88", "#3a3c42"), shoes=("#e8bdb6", "#f2efe9"), sneakers=True,
              brows="#16131a", iris="#2e2624", subsurf=1)
# the narrator after a hundred nights: lean and defined, a fitted white T-shirt that shows every muscle, black trousers
NARR_B = dict(NARR_A, body="m_fit", vtaper=True, crease=0.02, top=("#f4f4f2", "#a3a9b5"), turtleneck=False, hood=False,
              sleeves="short", leg_col=("#1c1d22", "#08090b"), shoes=("#ecebe7", "#d9d7d0"))

SHOP = dict(manhwa_head=True, body="m_heavy", height=1.72, face="round", skin=("#e3b894", "#a2734f"), hair="buzz",
            hair_col="#22201f", coat=None, top=("#e9e6df", "#9a978f"), turtleneck=False, leg_col=("#4a4a4d", "#1d1d1f"),
            head_yaw=28, subsurf=1)
# Korean street police: light-grey jacket, navy vest with reflective band, navy trousers, cap with gold braid
COP = dict(manhwa_head=True, body="m", height=1.82, face="square", skin=("#d9a982", "#9a6a4a"), hair="short", locks=False,
           coat=None, top=("#b4b8bd", "#6c7178"), turtleneck=False,     # long-sleeved grey shirt tucked in, no jacket
           vest="#1c2742", leg_col=("#151b2e", "#070a14"), shoes=("#111114", "#2a2a2e"), head_yaw=-24,
           brows="#0e0c0b", subsurf=1)
KID1 = dict(body="kid_f", height=1.28, face="soft_f", skin=("#f3d6bf", "#bf9274"), hair="bob", hair_col="#1a1414",
            coat=("#1f2a4a", "#0b1124"), hem=0.9, open_skirt=True, coat_flare=(0.02, 0.04), top=("#f4f4f0", "#b8bcc6"),
            turtleneck=False, legs="skirt", leg_col=("#1f2a4a", "#0b1124"), skirt_hem=0.6, socks="#f6f6f2",
            tie=("bow", "#22336a"), backpack=("#c9475a", "#7a2232"), shoes=("#141416", "#2a2a2e"), sneakers=False,
            head_yaw=30, subsurf=1)
KID2 = dict(KID1, body="kid_m", face="boy", height=1.34, hair="bangs", legs="shorts", tie=("tie", "#22336a"),
            backpack=("#2c4a8a", "#14244a"), head_yaw=0)

# women of Sol (webtoon city style): long or bobbed hair, coats, skirts, umbrellas
W1 = dict(body="f", height=1.66, face="sharp_f", skin=("#f2d5c0", "#c0927a"), hair="long", hair_len=0.34,
          hair_col="#0f1013", coat=("#1c1c1e", "#08080a"), hem=0.5, open_skirt=True, top=("#e9e6df", "#9a978f"),
          turtleneck=True, legs="skirt", leg_col=("#24272d", "#0c0e12"), skirt_hem=0.5, tights="#23222a",
          shoes=("#141416", "#2a2a2e"), manhwa_head=True, brows="#14110f", subsurf=1)
W2 = dict(body="f", height=1.62, face="soft_f", skin=("#f3d6bf", "#bf9274"), hair="long", hair_len=0.26,
          hair_col="#3b2a20", coat=("#c9b48f", "#7d6a4c"), hem=0.55, open_skirt=True, top=("#f0ece4", "#a9a49a"),
          turtleneck=False, legs="trousers", leg_col=("#2b2f3a", "#11131a"), shoes=("#e8e6e0", "#cfcac0"),
          sneakers=True, manhwa_head=True, subsurf=1)
W3 = dict(body="f", height=1.64, face="soft_f", skin=("#e8c2a2", "#a9775b"), hair="bob", hair_col="#16181d",
          coat=("#6b2a2e", "#331314"), hem=0.72, open_skirt=True, top=("#26292f", "#0e1013"), turtleneck=True,
          legs="skirt", leg_col=("#141416", "#060607"), skirt_hem=0.46, tights="#1c1b20", shoes=("#141416", "#2a2a2e"),
          manhwa_head=True, subsurf=1)
W4 = dict(body="f", height=1.68, face="sharp_f", skin=("#f0cfb3", "#b48466"), hair="long", hair_len=0.4,
          hair_col="#2a1d16", coat=("#c9c3b6", "#7f7a70"), hem=0.36, open_skirt=True, top=("#cfc4b2", "#7d7466"),
          turtleneck=True, legs="trousers", leg_col=("#24272d", "#0c0e12"), shoes=("#1b1a1c", "#3a2a22"),
          manhwa_head=True, subsurf=1)
# shop customers (no two faces alike)
MAN_LONG = dict(body="m", height=1.76, face="long", skin=("#e9c4a6", "#a8795d"), hair="short", locks=False, coat=None,
                top=("#56704f", "#26331f"), turtleneck=False, legs="trousers", leg_col=("#3a4a66", "#18202e"),
                shoes=("#1b1a1c", "#3a2a22"), manhwa_head=True, subsurf=1)
MAN_DIAMOND = dict(body="m_heavy", height=1.7, face="diamond", skin=("#c58f6a", "#86583d"), hair="buzz", hair_col="#2a2622",
                   coat=("#3b3f47", "#15171b"), hem=0.8, top=("#d9d4c8", "#8c877c"), legs="trousers",
                   leg_col=("#2a2c30", "#0f1012"), shoes=("#1b1a1c", "#3a2a22"), manhwa_head=True, subsurf=1)
