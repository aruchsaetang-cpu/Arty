"""The cast of "Aura Monster" as style dicts for lookdev/character_mh.build (shared by film.py and lookdev/cast_v2.py).
Every face is different: the hero has the idol face and the only black-and-white eyes; everyone else gets their own
face sculpt (FACES in character_mh)."""

import os
_BRAND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "brand", "")
# the narrator before training: skinny kid, black hoodie with the hood down, grey joggers, pink sneakers, umbrella
NARR_A = dict(body="m_slim", height=1.78, skin=("#f1d3ba", "#b4876e"), face="boy", hair="bangs", hair_col="#15171c",
              locks=False, top=("#1f2026", "#08090c"), turtleneck=True, hood=True, coat=None, manhwa_head=True,
              legs="trousers", leg_col=("#7c7f88", "#3a3c42"), shoes=("#e8bdb6", "#f2efe9"), sneakers=True,
              brows="#16131a", iris="#6e4a32", subsurf=1, prints=[       # the channel's merch: white prints
                  dict(img=_BRAND + "print_chest.png", side="front", x=0.165, dz=0.07, w=0.14),  # "A" badge, left chest
                  dict(img=_BRAND + "print_back.png", side="back", dz=0.40, w=0.48)])          # ARTY CLIPS across the back
# the narrator after a hundred nights: leaner, same clothes (black hoodie, grey joggers, pink sneakers)
NARR_B = dict(NARR_A, body="m_lean")

SHOP = dict(vary=101, manhwa_head=True, body="m_heavy", height=1.72, face="round", skin=("#e3b894", "#a2734f"), hair="buzz",
            hair_col="#22201f", coat=None, top=("#e9e6df", "#9a978f"), turtleneck=False, leg_col=("#4a4a4d", "#1d1d1f"),
            head_yaw=28, subsurf=1)
# Korean street police: light-grey jacket, navy vest with reflective band, navy trousers, cap with gold braid
COP = dict(vary=102, manhwa_head=True, body="m", height=1.82, face="square", skin=("#d9a982", "#9a6a4a"), hair="short", locks=False,
           coat=("#1f2a3d", "#0c1220"), hem=0.62, top=("#8a9bb0", "#4b5868"), turtleneck=False,   # first-version uniform:
           leg_col=("#1f2a3d", "#0c1220"), shoes=("#111114", "#2a2a2e"), head_yaw=-24,             # long navy coat, blue shirt
           brows="#0e0c0b", subsurf=1)
KID1 = dict(vary=103, body="kid_f", height=1.28, face="soft_f", skin=("#f3d6bf", "#bf9274"), hair="bob", hair_col="#1a1414",
            coat=("#1f2a4a", "#0b1124"), hem=0.9, open_skirt=True, coat_flare=(0.02, 0.04), top=("#f4f4f0", "#b8bcc6"),
            turtleneck=False, legs="skirt", leg_col=("#1f2a4a", "#0b1124"), skirt_hem=0.6, socks="#f6f6f2",
            tie=("bow", "#22336a"), backpack=("#c9475a", "#7a2232"), shoes=("#141416", "#2a2a2e"), sneakers=False,
            head_yaw=30, subsurf=1)
KID2 = dict(KID1, vary=104, body="kid_m", face="boy", height=1.34, hair="bangs", legs="shorts", tie=("tie", "#22336a"),
            backpack=("#2c4a8a", "#14244a"), head_yaw=0)

# women of Sol, dressed from the user's references: oversized blazers, a wrap suit, a cropped blazer with a slit
# midi skirt, a long mustard coat; long wavy hair, crossbody bags, face masks
BAG = ("#8a5a32", "#4e321b")
# long mustard double-breasted coat, grey turtleneck, wide beige trousers (the mom waiting with the kids)
W1 = dict(vary=105, body="f", height=1.69, face="kstar_f", jaw_v=0.3, lips="#c25a62", skin=("#f2d5c0", "#c0927a"), hair="long", hair_len=0.3,
          hair_col="#2a1c15", coat=("#d9a51b", "#8a6608"), hem=0.3, open_skirt=True, open_coat=True, lapels=True,
          coat_flare=(0.04, 0.1), top=("#a29a90", "#5f5a53"),
          turtleneck=True, legs="trousers", leg_col=("#c4b9a6", "#7c7364"), shoes=("#141416", "#2a2a2e"), bag=BAG,
          manhwa_head=True, brows="#14110f", subsurf=1)
# cream oversized blazer, white shirt, camel knit, brown pleated mini skirt, crossbody bag (in the shop, on her phone)
W2 = dict(vary=106, body="f", height=1.63, face="kstar_f", jaw_v=0.3, lips="#d27a7a", skin=("#f3d6bf", "#bf9274"), hair="long", hair_len=0.32,
          hair_col="#4a3022", coat=("#ece3d2", "#a49a88"), hem=0.66, open_skirt=True, open_coat=True, lapels=True,
          coat_flare=(0.1, 0.22), top=("#c09f74", "#7a6345"),
          turtleneck=False, legs="skirt", leg_col=("#7a5a3c", "#45321f"), skirt_hem=0.56, tights="#e9c9b2",
          shoes=("#1b1a1c", "#3a2a22"), bag=BAG, manhwa_head=True, subsurf=1)
# sage cropped blazer + slit midi skirt, black socks, black-and-white sneakers, white mask (walking past the hero)
W3 = dict(vary=107, body="f", height=1.58, face="kstar_f", jaw_v=0.3, lips="#d27a7a", skin=("#f0cfb3", "#b48466"), hair="long", hair_len=0.28,
          hair_col="#5a3a26", coat=("#8f9a82", "#566050"), hem=0.88, open_skirt=False, coat_flare=(0.02, 0.04),
          top=("#8f9a82", "#566050"), turtleneck=False, legs="skirt", leg_col=("#8f9a82", "#566050"), skirt_hem=0.3,
          socks="#141416", shoes=("#f2f2f0", "#141416"), sneakers=True, bag=BAG, mask="#f4f4f2", manhwa_head=True, subsurf=1)
# taupe wrap blazer and wide-leg trousers, black mask (under the awning in the alley)
W4 = dict(vary=108, body="f", height=1.72, face="kstar_f", jaw_v=0.3, lips="#b84a55", skin=("#f2d5c0", "#c0927a"), hair="long", hair_len=0.4,
          hair_col="#14110f", coat=("#9b8468", "#5e4d3a"), hem=0.78, open_skirt=False, coat_flare=(0.03, 0.06),
          top=("#9b8468", "#5e4d3a"), turtleneck=False, legs="trousers", leg_col=("#9b8468", "#5e4d3a"),
          shoes=("#141416", "#2a2a2e"), mask="#111114", manhwa_head=True, subsurf=1)
W_LOOKS = [W1, W2, W3, W4]
# shop customers (no two faces alike)
MAN_LONG = dict(vary=109, body="m", height=1.77, face="long", skin=("#e9c4a6", "#a8795d"), hair="short", locks=False, coat=None,
                top=("#56704f", "#26331f"), turtleneck=False, legs="trousers", leg_col=("#3a4a66", "#18202e"),
                shoes=("#1b1a1c", "#3a2a22"), manhwa_head=True, subsurf=1)
MAN_DIAMOND = dict(vary=110, body="m_heavy", height=1.68, face="diamond", skin=("#c58f6a", "#86583d"), hair="buzz", hair_col="#2a2622",
                   coat=("#3b3f47", "#15171b"), hem=0.8, top=("#d9d4c8", "#8c877c"), legs="trousers",
                   leg_col=("#2a2c30", "#0f1012"), shoes=("#1b1a1c", "#3a2a22"), manhwa_head=True, subsurf=1)

# first-version designs (body, face, hair and outfit exactly as in the first-half preview), built with ch.build_v1
HERO_V1 = dict(body="m", height=1.86, skin=("#e8c2a2", "#a9775b"), hair="short", hair_col="#16181d", locks=True,
               top=("#cfc4b2", "#7d7466"), coat=("#2f343c", "#11141a"), hem=0.36, open_skirt=True,
               legs="trousers", leg_col=("#24272d", "#0c0e12"), shoes=("#1b1a1c", "#3a2a22"), brows="#1a1714")
COP_V1 = dict(body="m", height=1.82, skin=("#f0cfb3", "#b48466"), hair="short", locks=False, coat=("#1f2a3d", "#0c1220"),
              hem=0.62, top=("#8a9bb0", "#4b5868"), turtleneck=False, leg_col=("#1f2a3d", "#0c1220"), head_yaw=-24, subsurf=1)
