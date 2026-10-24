"""Generate index.html for AGAIN. (อีกครั้ง) — a 2:30 animated short.

The character, sets and timeline are built here so poses stay consistent across
scenes. Run:  python3 scripts/gen.py  (writes ../index.html)
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DUR = 150

# ---------- palette ----------
SKIN = "#ead9bf"
OUT = "#17151c"
HOOD = "#2c3654"
HOOD_D = "#1e2640"
PANTS = "#24252d"
STR = "#ff8a3d"
WHITE = "#f6f1e7"

# ============================================================
# character parts (unit: head radius 100, head centre at 0,0)
# ============================================================

def eye(cx, cy, kind, inner_sign):
    """inner_sign: +1 when the inner corner is toward +x (left eye), -1 for the right eye."""
    base = (f'<ellipse cx="{cx}" cy="{cy}" rx="21" ry="25" fill="#fff" stroke="{OUT}" stroke-width="5"/>'
            f'<circle cx="{cx + 3 * inner_sign}" cy="{cy + 3}" r="11" fill="{OUT}"/>'
            f'<circle cx="{cx + 6 * inner_sign}" cy="{cy - 1}" r="3.5" fill="#fff"/>')
    if kind == "open":
        return base
    if kind == "closed":
        return f'<path d="M{cx-21} {cy+2} Q{cx} {cy+16} {cx+21} {cy+2}" fill="none" stroke="{OUT}" stroke-width="6" stroke-linecap="round"/>'
    if kind == "tired":
        return (base + f'<path d="M{cx-23} {cy+1} Q{cx} {cy-34} {cx+23} {cy+1} Z" fill="{SKIN}" stroke="{OUT}" stroke-width="5"/>'
                f'<path d="M{cx-17} {cy+33} Q{cx} {cy+42} {cx+17} {cy+33}" fill="none" stroke="#8a6f86" stroke-width="5" stroke-linecap="round"/>')
    if kind == "det":
        hi, lo = (cy - 30, cy - 9)
        x_in, x_out = cx + 23 * inner_sign, cx - 23 * inner_sign
        return (base + f'<path d="M{x_out} {hi} L{x_out} {cy-15} L{x_in} {lo} L{x_in} {hi} Z" fill="{SKIN}"/>'
                f'<path d="M{x_out} {cy-15} L{x_in} {lo}" stroke="{OUT}" stroke-width="5" stroke-linecap="round"/>')
    raise ValueError(kind)


BROWS = {
    "neutral": ((60, -48), (18, -50)),
    "sad": ((62, -42), (18, -62)),
    "det": ((64, -64), (16, -42)),
    "sleepy": ((58, -44), (18, -46)),
}
MOUTHS = {
    "flat": f'<path d="M-18 52 H18" stroke="{OUT}" stroke-width="6" stroke-linecap="round"/>',
    "frown": f'<path d="M-22 60 Q0 42 22 60" fill="none" stroke="{OUT}" stroke-width="6" stroke-linecap="round"/>',
    "smile": f'<path d="M-28 44 Q0 74 28 44" fill="none" stroke="{OUT}" stroke-width="6" stroke-linecap="round"/>',
    "grit": f'<rect x="-24" y="44" width="48" height="16" rx="5" fill="#fff" stroke="{OUT}" stroke-width="5"/><path d="M-24 52 H24" stroke="{OUT}" stroke-width="3"/>',
}
MOODS = {
    "sleepy": ("closed", "sleepy", "flat"),
    "tired": ("tired", "sad", "frown"),
    "sad": ("open", "sad", "frown"),
    "det": ("det", "det", "flat"),
    "grit": ("det", "det", "grit"),
    "smile": ("open", "neutral", "smile"),
    "calm": ("open", "neutral", "flat"),
    "shock": ("open", "sad", "flat"),
}


def face(mood):
    e, b, m = MOODS[mood]
    (ox, oy), (ix, iy) = BROWS[b]
    brows = "".join(
        f'<path d="M{s*ox} {oy} L{s*ix} {iy}" stroke="{OUT}" stroke-width="11" stroke-linecap="round"/>' for s in (-1, 1))
    return eye(-36, -4, e, +1) + eye(36, -4, e, -1) + brows + MOUTHS[m]


def head(pfx, moods, side=False):
    """Front head with one face layer per mood (first visible). side=True draws a profile facing right."""
    if side:
        layers = ""
        for i, md in enumerate(moods):
            e, b, m = MOODS[md]
            (ox, oy), (ix, iy) = BROWS[b]
            mouth = {"smile": f'<path d="M40 48 Q60 62 78 46" fill="none" stroke="{OUT}" stroke-width="6" stroke-linecap="round"/>',
                     "grit": f'<path d="M44 52 H80" stroke="{OUT}" stroke-width="7" stroke-linecap="round"/>',
                     "frown": f'<path d="M44 58 Q60 46 78 56" fill="none" stroke="{OUT}" stroke-width="6" stroke-linecap="round"/>'}.get(
                m, f'<path d="M46 52 H78" stroke="{OUT}" stroke-width="6" stroke-linecap="round"/>')
            layers += (f'<g id="{pfx}-face-{md}" opacity="{1 if i == 0 else 0}">' + eye(48, -6, e, -1)
                       + f'<path d="M{20 + (ox - 18) * 0.6} {oy} L{70 - (ix - 16) * 0.2} {iy}" stroke="{OUT}" stroke-width="11" stroke-linecap="round"/>'
                       + mouth + '</g>')
        return (f'<g id="{pfx}-head">'
                f'<path d="M-6 -100 C-12 -136 20 -152 36 -141 C16 -136 9 -122 11 -99" fill="{SKIN}" stroke="{OUT}" stroke-width="6" stroke-linejoin="round"/>'
                f'<ellipse rx="94" ry="106" fill="{SKIN}" stroke="{OUT}" stroke-width="6"/>'
                + layers + '</g>')
    layers = "".join(
        f'<g id="{pfx}-face-{md}" opacity="{1 if i == 0 else 0}">{face(md)}</g>' for i, md in enumerate(moods))
    return (f'<g id="{pfx}-head">'
            f'<path d="M-6 -102 C-12 -138 20 -154 36 -143 C16 -138 9 -124 11 -101" fill="{SKIN}" stroke="{OUT}" stroke-width="6" stroke-linejoin="round"/>'
            f'<ellipse rx="100" ry="108" fill="{SKIN}" stroke="{OUT}" stroke-width="6"/>'
            f'<ellipse cy="46" rx="74" ry="42" fill="#000" opacity="0.05"/>'
            + layers + '</g>')


def torso_front():
    return (f'<path d="M-100 92 C-150 100 -162 160 -162 240 L-168 400 H168 L162 240 C162 160 150 100 100 92 Z" fill="{HOOD}" stroke="{OUT}" stroke-width="6"/>'
            f'<path d="M-72 92 Q0 152 72 92" fill="none" stroke="{HOOD_D}" stroke-width="16" stroke-linecap="round"/>'
            f'<path d="M-22 120 L-28 190 M22 120 L28 190" stroke="{STR}" stroke-width="7" stroke-linecap="round"/>'
            f'<path d="M-82 290 H82 L96 370 H-96 Z" fill="{HOOD_D}"/>')


def person_front(pfx, moods, arms=True):
    a = ""
    if arms:
        a = (f'<g id="{pfx}-armL"><path d="M-140 150 L-150 330" stroke="{HOOD}" stroke-width="56" stroke-linecap="round"/>'
             f'<path d="M-140 150 L-150 330" stroke="{OUT}" stroke-width="0"/><circle cx="-150" cy="352" r="26" fill="{SKIN}" stroke="{OUT}" stroke-width="5"/></g>'
             f'<g id="{pfx}-armR"><path d="M140 150 L150 330" stroke="{HOOD}" stroke-width="56" stroke-linecap="round"/>'
             f'<circle cx="150" cy="352" r="26" fill="{SKIN}" stroke="{OUT}" stroke-width="5"/></g>')
    return f'<g id="{pfx}-body">{torso_front()}{a}</g>' + head(pfx, moods)


def runner(pfx, moods):
    """Side-view runner facing right, hip at 0,0, feet near y=180."""
    def leg(n):
        return (f'<g id="{pfx}-leg{n}"><path d="M0 0 L0 150" stroke="{PANTS}" stroke-width="46" stroke-linecap="round"/>'
                f'<ellipse cx="16" cy="172" rx="36" ry="17" fill="#d9d4ca" stroke="{OUT}" stroke-width="5"/></g>')

    def arm(n):
        return (f'<g id="{pfx}-arm{n}"><path d="M0 -175 L0 -70" stroke="{HOOD}" stroke-width="38" stroke-linecap="round"/>'
                f'<circle cx="0" cy="-58" r="19" fill="{SKIN}" stroke="{OUT}" stroke-width="5"/></g>')
    return (f'<g id="{pfx}-runner">{leg("B")}{arm("B")}'
            f'<rect x="-48" y="-210" width="96" height="225" rx="44" fill="{HOOD}" stroke="{OUT}" stroke-width="6"/>'
            f'<path d="M-10 -190 L-14 -140" stroke="{STR}" stroke-width="6" stroke-linecap="round"/>'
            f'{leg("F")}<g transform="translate(12 -300) scale(0.8)">{head(pfx, moods, side=True)}</g>{arm("F")}</g>')


def pushup(pfx, moods):
    """Side view plank on floor y=0, feet at x=-280, facing right."""
    return (f'<g id="{pfx}-plank">'
            f'<path d="M-280 -40 L-40 -90" stroke="{PANTS}" stroke-width="46" stroke-linecap="round"/>'
            f'<ellipse cx="-292" cy="-22" rx="20" ry="30" fill="#d9d4ca" stroke="{OUT}" stroke-width="5"/>'
            f'<rect x="-70" y="-140" width="230" height="92" rx="44" fill="{HOOD}" stroke="{OUT}" stroke-width="6"/>'
            f'<g transform="translate(225 -150) scale(0.62)">{head(pfx, moods, side=True)}</g></g>'
            f'<g id="{pfx}-arms"><path d="M120 -96 L126 -12" stroke="{HOOD}" stroke-width="36" stroke-linecap="round"/>'
            f'<ellipse cx="134" cy="-6" rx="24" ry="12" fill="{SKIN}" stroke="{OUT}" stroke-width="5"/></g>')


# ============================================================
# sets
# ============================================================

def bedroom(pfx, moods, clock="5:00"):
    return f'''
  <rect width="1920" height="1080" fill="url(#g-night)"/>
  <rect y="830" width="1920" height="250" fill="#0a0b11"/>
  <polygon points="430,250 690,250 1100,1080 140,1080" fill="#8fa8e0" opacity="0.06"/>
  <rect x="300" y="190" width="260" height="320" rx="10" fill="#22304f" stroke="#3a4a6c" stroke-width="10"/>
  <path d="M430 190 V510 M300 350 H560" stroke="#3a4a6c" stroke-width="8"/>
  <circle cx="500" cy="250" r="26" fill="#dfe6f5" opacity="0.8"/>
  <rect x="540" y="500" width="44" height="330" rx="8" fill="#3b2c26"/>
  <rect x="560" y="720" width="900" height="70" rx="10" fill="#3b2c26"/>
  <rect x="580" y="660" width="860" height="80" rx="24" fill="#cfc9bd"/>
  <ellipse cx="700" cy="650" rx="110" ry="40" fill="#e3ded3" stroke="{OUT}" stroke-width="5"/>
  <g transform="translate(705 585) scale(0.62)">{head(pfx, moods)}</g>
  <g id="{pfx}-arm"><path d="M1240 660 L1500 610" stroke="{HOOD}" stroke-width="40" stroke-linecap="round"/>
    <circle cx="1514" cy="606" r="22" fill="{SKIN}" stroke="{OUT}" stroke-width="5"/></g>
  <path d="M770 640 C900 560 1200 590 1420 620 L1440 740 L760 740 Z" fill="#3d4766" stroke="{OUT}" stroke-width="5"/>
  <path d="M800 690 C950 650 1150 660 1400 680" fill="none" stroke="#2f3854" stroke-width="8"/>
  <rect x="1470" y="660" width="220" height="170" rx="8" fill="#2b211d"/>
  <rect x="1470" y="700" width="220" height="10" fill="#1d1613"/>
  <circle id="{pfx}-clockglow" cx="1580" cy="625" r="110" fill="url(#g-red)"/>
  <g id="{pfx}-clock"><rect x="1510" y="590" width="140" height="70" rx="12" fill="#0b0b0f" stroke="#38363f" stroke-width="5"/>
    <text id="{pfx}-clocktxt" x="1580" y="640" text-anchor="middle" font-family="Kanit" font-weight="700" font-size="44" fill="#ff3b3b">{clock}</text>
    <text id="{pfx}-clocktxt2" x="1580" y="640" text-anchor="middle" font-family="Kanit" font-weight="700" font-size="44" fill="#ff3b3b" opacity="0">{"5:09" if clock == "5:00" else "5:00"}</text></g>
  <g id="{pfx}-ring" opacity="0" stroke="#ff6b5b" stroke-width="7" stroke-linecap="round" fill="none">
    <path d="M1490 575 L1470 555 M1580 570 V545 M1670 575 L1690 555"/></g>'''


def phone_scene(pfx, mood):
    return f'''
  <rect width="1920" height="1080" fill="#06070c"/>
  <rect x="1380" y="130" width="230" height="96" rx="14" fill="#0b0b0f" stroke="#2a2930" stroke-width="5"/>
  <text id="{pfx}-t1" x="1495" y="198" text-anchor="middle" font-family="Kanit" font-weight="700" font-size="56" fill="#ff3b3b">23:47</text>
  <text id="{pfx}-t2" x="1495" y="198" text-anchor="middle" font-family="Kanit" font-weight="700" font-size="56" fill="#ff3b3b" opacity="0">01:12</text>
  <text id="{pfx}-t3" x="1495" y="198" text-anchor="middle" font-family="Kanit" font-weight="700" font-size="56" fill="#ff3b3b" opacity="0">03:26</text>
  <g transform="translate(960 400) scale(1.55)">{person_front(pfx, [mood], arms=False)}</g>
  <path d="M260 1080 C400 880 700 860 960 880 C1220 860 1520 880 1660 1080 Z" fill="#2a3150" stroke="{OUT}" stroke-width="6"/>
  <ellipse id="{pfx}-glow" cx="960" cy="560" rx="520" ry="460" fill="url(#g-blue)"/>
  <g transform="translate(960 800) rotate(-6)">
    <path d="M-190 120 C-180 40 -120 10 -80 30" stroke="{HOOD}" stroke-width="64" stroke-linecap="round" fill="none"/>
    <path d="M190 120 C180 40 120 10 80 30" stroke="{HOOD}" stroke-width="64" stroke-linecap="round" fill="none"/>
    <rect x="-80" y="-150" width="160" height="270" rx="22" fill="#0e0f14" stroke="{OUT}" stroke-width="6"/>
    <rect x="-68" y="-136" width="136" height="242" rx="12" fill="#a9c8ff"/>
    <g clip-path="url(#c-{pfx}-scr)"><g id="{pfx}-feed">
      {"".join(f'<rect x="-56" y="{-126 + k*62}" width="112" height="46" rx="8" fill="#{["6f8fd6","e7eefc","8aa8e8","c9d8f7"][k % 4]}"/>' for k in range(12))}
    </g></g>
    <circle cx="-80" cy="30" r="30" fill="{SKIN}" stroke="{OUT}" stroke-width="5"/>
    <circle cx="80" cy="30" r="30" fill="{SKIN}" stroke="{OUT}" stroke-width="5"/>
  </g>
  <defs><clipPath id="c-{pfx}-scr"><rect x="-68" y="-136" width="136" height="242" rx="12"/></clipPath></defs>'''


def mirror_scene(pfx, mood, warm=False):
    wall = "#1b2130" if not warm else "#2b2620"
    return f'''
  <rect width="1920" height="1080" fill="{wall}"/>
  <g opacity="0.25" stroke="#000" stroke-width="4">{"".join(f'<path d="M{x} 0 V1080"/>' for x in range(0, 1920, 120))}{"".join(f'<path d="M0 {y} H1920"/>' for y in range(0, 1080, 120))}</g>
  <rect x="640" y="90" width="640" height="800" rx="320" fill="#11151f" stroke="#7a7f8c" stroke-width="16"/>
  <g clip-path="url(#c-{pfx}-mir)">
    <rect x="640" y="90" width="640" height="800" fill="{'#2a3348' if not warm else '#4a3d30'}"/>
    <g transform="translate(960 470) scale(1.45)">{person_front(pfx, [mood], arms=False)}</g>
    <polygon points="700,90 820,90 700,330" fill="#fff" opacity="0.06"/>
  </g>
  <rect id="{pfx}-dim" x="640" y="90" width="640" height="800" rx="320" fill="#000" opacity="0.15"/>
  <rect x="560" y="900" width="800" height="70" rx="16" fill="#cfd3da"/>
  <rect x="600" y="970" width="720" height="110" fill="#9ea3ad"/>
  <defs><clipPath id="c-{pfx}-mir"><rect x="640" y="90" width="640" height="800" rx="320"/></clipPath></defs>'''


def street(pfx, moods, dawn=False):
    sky = "url(#g-dawn)" if dawn else "url(#g-rain)"
    sun = '<circle id="%s-sun" cx="1300" cy="640" r="150" fill="#ffd27a" opacity="0.9"/>' % pfx if dawn else ""
    bld = "#2a1f2a" if dawn else "#0f1422"
    lamps = "" if dawn else "".join(
        f'<rect x="{x}" y="380" width="14" height="420" fill="#2a2f3d"/><circle cx="{x+7}" cy="380" r="20" fill="#ffd98a"/><polygon points="{x+7},390 {x-110},800 {x+124},800" fill="#ffd98a" opacity="0.07"/>'
        for x in (300, 1000, 1700, 2400))
    rain = "" if dawn else (f'<g id="{pfx}-rain" stroke="#9fb3d9" stroke-width="3" opacity="0.45">'
                            + "".join(f'<path d="M{(i*137)%1960} {((i*251)%1300)-260} l-18 60"/>' for i in range(160)) + '</g>')
    return f'''
  <rect width="1920" height="1080" fill="{sky}"/>{sun}
  <g id="{pfx}-city" fill="{bld}">{"".join(f'<rect x="{x}" y="{360 + (x*37)%200}" width="{180 + (x*13)%90}" height="600"/>' for x in range(-100, 3800, 230))}</g>
  <g id="{pfx}-lamps">{lamps}</g>
  <rect y="800" width="1920" height="280" fill="{'#3a2a2c' if dawn else '#151a26'}"/>
  <g id="{pfx}-dash" fill="{'#d9a46a' if dawn else '#3a4256'}">{"".join(f'<rect x="{x}" y="930" width="120" height="14"/>' for x in range(0, 4000, 260))}</g>
  <g id="{pfx}-rw"><g transform="translate(900 620)">{runner(pfx, moods)}</g></g>{rain}'''


def floor_room(pfx, moods, strong=False):
    light = "url(#g-lamp)" if strong else "url(#g-night)"
    return f'''
  <rect width="1920" height="1080" fill="{light}"/>
  <rect y="780" width="1920" height="300" fill="{'#2a221d' if strong else '#0c0d14'}"/>
  <path d="M0 780 H1920" stroke="#000" stroke-width="6" opacity="0.4"/>
  <g id="{pfx}-shake"><g transform="translate(840 790) scale(1.55)">{pushup(pfx, moods)}</g></g>'''


def calendar(pfx, crossed, gap=(), title="เดือนแรก"):
    cells = ""
    for d in range(1, 15):
        c, r = (d - 1) % 7, (d - 1) // 7
        x, y = 580 + c * 110, 280 + r * 210
        stroke = "#c9c2b3"
        cells += (f'<g id="{pfx}-cell{d}"><rect x="{x}" y="{y}" width="100" height="190" rx="10" fill="#f6f1e7" stroke="{stroke}" stroke-width="4"/>'
                  f'<text x="{x+14}" y="{y+42}" font-family="Kanit" font-weight="700" font-size="34" fill="#4a4550">{d}</text></g>')
        if d in crossed:
            cells += (f'<path id="{pfx}-x{d}" d="M{x+20} {y+70} L{x+80} {y+160} M{x+80} {y+70} L{x+20} {y+160}" '
                      f'stroke="#d63b3b" stroke-width="12" stroke-linecap="round" fill="none" stroke-dasharray="230" stroke-dashoffset="230"/>')
        if d in gap:
            cells += f'<rect id="{pfx}-gap{d}" x="{x}" y="{y}" width="100" height="190" rx="10" fill="none" stroke="#ff4b4b" stroke-width="8" opacity="0"/>'
    return f'''
  <rect width="1920" height="1080" fill="#151824"/>
  <rect x="540" y="150" width="840" height="600" rx="24" fill="#e9e4d8"/>
  <rect x="540" y="150" width="840" height="110" rx="24" fill="#c0392b"/><rect x="540" y="220" width="840" height="40" fill="#c0392b"/>
  <text x="960" y="225" text-anchor="middle" font-family="Kanit" font-weight="900" font-size="56" fill="#fff">{title}</text>
  {cells}'''


def grid100(pfx):
    sq = "".join(
        f'<rect class="{pfx}-sq" x="{612 + (i % 10) * 70}" y="{250 + (i // 10) * 62}" width="56" height="50" rx="8" fill="#ffc94a"/>'
        for i in range(100))
    base = "".join(
        f'<rect x="{612 + (i % 10) * 70}" y="{250 + (i // 10) * 62}" width="56" height="50" rx="8" fill="#232838"/>'
        for i in range(100))
    return f'<rect width="1920" height="1080" fill="#11141d"/>{base}{sq}'


def reading(pfx):
    return f'''
  <rect width="1920" height="1080" fill="url(#g-lamp)"/>
  <polygon points="1260,250 1330,250 1560,760 1020,760" fill="#ffd98a" opacity="0.12"/>
  <path d="M1250 250 L1340 250 L1370 300 L1220 300 Z" fill="#c9a24a"/><path d="M1295 300 V740" stroke="#3a2c20" stroke-width="12"/>
  <g transform="translate(900 420) scale(1.0)">{person_front(pfx, ["calm"], arms=False)}</g>
  <rect x="300" y="740" width="1320" height="60" rx="10" fill="#5a3e2b"/>
  <rect x="340" y="800" width="40" height="280" fill="#4a3324"/><rect x="1540" y="800" width="40" height="280" fill="#4a3324"/>
  <g transform="translate(900 720)"><path d="M-170 10 L0 30 L170 10 L170 -40 L0 -20 L-170 -40 Z" fill="#f2ead8" stroke="{OUT}" stroke-width="5"/>
    <path d="M0 -20 V30" stroke="{OUT}" stroke-width="4"/>
    <path id="{pfx}-page" d="M0 -20 L170 -40 L170 10 L0 30 Z" fill="#fffaf0" stroke="{OUT}" stroke-width="4"/>
    <circle cx="-190" cy="0" r="28" fill="{SKIN}" stroke="{OUT}" stroke-width="5"/><circle cx="190" cy="0" r="28" fill="{SKIN}" stroke="{OUT}" stroke-width="5"/></g>'''


def note_scene(pfx):
    return f'''
  <rect width="1920" height="1080" fill="#191b25"/>
  <rect x="520" y="140" width="880" height="660" rx="16" fill="#8a6a48" stroke="#5a442e" stroke-width="16"/>
  <g transform="rotate(-3 960 470)">
    <rect x="720" y="290" width="480" height="340" fill="#f4e7a8"/>
    <rect x="900" y="270" width="120" height="40" fill="#e7d9c4" opacity="0.8"/>
    <g clip-path="url(#c-{pfx}-ink)"><text x="960" y="500" text-anchor="middle" font-family="Kanit" font-weight="900" font-size="128" fill="{OUT}">วันที่ 1</text>
    <path d="M770 560 Q960 590 1150 556" stroke="#d63b3b" stroke-width="12" fill="none" stroke-linecap="round"/></g>
  </g>
  <defs><clipPath id="c-{pfx}-ink"><rect id="{pfx}-ink" x="740" y="330" width="0" height="300"/></clipPath></defs>
  <g id="{pfx}-hand"><path d="M760 520 L1500 1120" stroke="{HOOD}" stroke-width="80" stroke-linecap="round"/>
    <circle cx="760" cy="520" r="36" fill="{SKIN}" stroke="{OUT}" stroke-width="6"/>
    <path d="M735 545 L705 470" stroke="#1d1d24" stroke-width="22" stroke-linecap="round"/></g>'''


def hill(pfx):
    return f'''
  <rect width="1920" height="1080" fill="url(#g-sunrise)"/>
  <circle id="{pfx}-sun" cx="1100" cy="900" r="170" fill="#ffe2a0"/>
  <circle cx="1100" cy="900" r="320" fill="url(#g-sunglow)" id="{pfx}-sunglow"/>
  <path d="M-50 1080 L-50 900 C300 820 600 760 900 740 C1200 730 1500 800 1970 880 L1970 1080 Z" fill="#1a1220"/>
  <g id="{pfx}-sil" transform="translate(900 640)" fill="#0d0a12">
    <path d="M-6 -150 C-12 -186 20 -202 36 -191 C16 -186 9 -172 11 -149" fill="#0d0a12"/>
    <ellipse cy="-50" rx="70" ry="76"/>
    <path d="M-80 20 C-110 30 -115 70 -118 110 L-122 110 L-118 104 L122 104 L118 110 C115 70 110 30 80 20 Z"/>
    <path d="M-60 104 L-55 120 L-20 120 L-15 104 Z M15 104 L20 120 L55 120 L60 104 Z"/>
  </g>'''


DEFS = '''
<defs>
  <linearGradient id="g-night" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#141829"/><stop offset="1" stop-color="#0b0d16"/></linearGradient>
  <linearGradient id="g-rain" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0b1020"/><stop offset="1" stop-color="#1a2338"/></linearGradient>
  <linearGradient id="g-dawn" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3b2a5a"/><stop offset="0.55" stop-color="#e2765a"/><stop offset="1" stop-color="#ffc27a"/></linearGradient>
  <linearGradient id="g-sunrise" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#25204a"/><stop offset="0.5" stop-color="#d4645a"/><stop offset="1" stop-color="#ffcf86"/></linearGradient>
  <linearGradient id="g-lamp" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2a2230"/><stop offset="1" stop-color="#3c2c22"/></linearGradient>
  <radialGradient id="g-red"><stop offset="0" stop-color="#ff3b3b" stop-opacity="0.35"/><stop offset="1" stop-color="#ff3b3b" stop-opacity="0"/></radialGradient>
  <radialGradient id="g-blue"><stop offset="0" stop-color="#7fb0ff" stop-opacity="0.38"/><stop offset="0.6" stop-color="#5a8cff" stop-opacity="0.1"/><stop offset="1" stop-color="#5a8cff" stop-opacity="0"/></radialGradient>
  <radialGradient id="g-sunglow"><stop offset="0" stop-color="#ffe2a0" stop-opacity="0.6"/><stop offset="1" stop-color="#ffe2a0" stop-opacity="0"/></radialGradient>
  <radialGradient id="g-door"><stop offset="0" stop-color="#fff6dc" stop-opacity="1"/><stop offset="1" stop-color="#fff6dc" stop-opacity="0"/></radialGradient>
</defs>'''

# ============================================================
# scenes: (id, start, end, svg, captions[(id, text, t_in, t_out, cls)])
# times are absolute seconds
# ============================================================
SCENES = []
JS = []


def scene(sid, a, b, svg, caps=()):
    SCENES.append((sid, a, b, svg, caps))


def js(s):
    JS.append(s)


def run_cycle(p, t, dur, period, amp_leg=34, amp_arm=40, bob=14):
    n = int(dur / period) - 1
    js(f"""
tl.fromTo("#{p}-legF", {{rotation: -{amp_leg}, svgOrigin: "0 0"}}, {{rotation: {amp_leg}, svgOrigin: "0 0", duration: {period}, yoyo: true, repeat: {n}, ease: "sine.inOut"}}, {t});
tl.fromTo("#{p}-legB", {{rotation: {amp_leg}, svgOrigin: "0 0"}}, {{rotation: -{amp_leg}, svgOrigin: "0 0", duration: {period}, yoyo: true, repeat: {n}, ease: "sine.inOut"}}, {t});
tl.fromTo("#{p}-armF", {{rotation: {amp_arm}, svgOrigin: "0 -175"}}, {{rotation: -{amp_arm}, svgOrigin: "0 -175", duration: {period}, yoyo: true, repeat: {n}, ease: "sine.inOut"}}, {t});
tl.fromTo("#{p}-armB", {{rotation: -{amp_arm}, svgOrigin: "0 -175"}}, {{rotation: {amp_arm}, svgOrigin: "0 -175", duration: {period}, yoyo: true, repeat: {n}, ease: "sine.inOut"}}, {t});
tl.fromTo("#{p}-runner", {{y: 0}}, {{y: -{bob}, duration: {period/2}, yoyo: true, repeat: {2*n+1}, ease: "sine.inOut"}}, {t});
""")


# A 0–13 snooze (music enters at 3s)
scene("a", 0, 13, bedroom("a", ["sleepy"]) + '<rect id="a-black0" width="1920" height="1080" fill="#000"/>', [("a-c1", "พรุ่งนี้ค่อยเริ่มก็ได้…", 6.4, 12.4, "")])
js("""
{ const S = 0;
tl.fromTo("#cam-a", {scale: 1.0}, {scale: 1.12, duration: 13, ease: "none"}, S);
tl.fromTo("#a-black0", {opacity: 1}, {opacity: 0, duration: 1.6, ease: "power1.inOut"}, S);
tl.fromTo("#a-clocktxt", {opacity: 1}, {opacity: 0.35, duration: 0.5, yoyo: true, repeat: 5, ease: "steps(1)"}, S + 0.4);
tl.fromTo("#a-ring", {opacity: 0}, {opacity: 1, duration: 0.12, yoyo: true, repeat: 9, ease: "none"}, S + 3.0);
tl.fromTo("#a-clock", {x: 0}, {x: 6, duration: 0.05, yoyo: true, repeat: 23, ease: "none"}, S + 3.0);
tl.fromTo("#a-arm", {rotation: 28, svgOrigin: "1240 660"}, {rotation: 0, svgOrigin: "1240 660", duration: 0.45, ease: "power3.in"}, S + 4.2);
tl.to("#a-clock", {y: 6, duration: 0.08, yoyo: true, repeat: 1}, S + 4.65);
tl.set("#a-clocktxt", {opacity: 0}, S + 4.7); tl.set("#a-clocktxt2", {opacity: 1}, S + 4.7);
tl.to("#a-clockglow", {opacity: 0.4, duration: 0.3}, S + 4.7);
tl.to("#a-arm", {rotation: 28, svgOrigin: "1240 660", duration: 0.8, ease: "power2.inOut"}, S + 5.4);
}
""")

# B 13–29 phone at night
scene("b", 13, 29, phone_scene("b", "tired"), [
    ("b-c1", "พรุ่งนี้…", 14.5, 18.0, "top"),
    ("b-c2", "พรุ่งนี้…", 18.5, 22.0, "top"),
    ("b-c3", "แต่ “พรุ่งนี้” ไม่เคยมาถึง", 23.0, 28.6, "big top")])
js("""
{ const S = 13;
tl.fromTo("#cam-b", {scale: 1.0}, {scale: 1.15, duration: 16, ease: "none"}, S);
tl.fromTo("#b-feed", {y: 0}, {y: -248, duration: 1.6, ease: "power1.inOut", repeat: 9}, S);
tl.fromTo("#b-glow", {opacity: 0.8}, {opacity: 1, duration: 0.8, yoyo: true, repeat: 19, ease: "sine.inOut"}, S);
tl.set("#b-t1", {opacity: 0}, S + 5.0); tl.set("#b-t2", {opacity: 1}, S + 5.0);
tl.set("#b-t2", {opacity: 0}, S + 9.5); tl.set("#b-t3", {opacity: 1}, S + 9.5);
tl.fromTo("#b-head", {rotation: 0, transformOrigin: "50% 100%"}, {rotation: -4, transformOrigin: "50% 100%", duration: 3, yoyo: true, repeat: 4, ease: "sine.inOut"}, S);
}
""")

# C 29–43 mirror
scene("c", 29, 43, mirror_scene("c", "tired"), [
    ("c-c1", "จนวันหนึ่ง", 30.5, 34.0, ""),
    ("c-c2", "เขาจำคนในกระจกไม่ได้", 34.5, 42.6, "big")])
js("""
{ const S = 29;
tl.fromTo("#cam-c", {scale: 1.0}, {scale: 1.2, duration: 14, ease: "power1.inOut"}, S);
tl.fromTo("#c-dim", {opacity: 0.6}, {opacity: 0.15, duration: 0.15, yoyo: true, repeat: 3, ease: "steps(1)"}, S + 0.2);
tl.fromTo("#c-head", {rotation: 0, transformOrigin: "50% 100%"}, {rotation: 5, transformOrigin: "50% 100%", duration: 4, ease: "sine.inOut"}, S + 6);
}
""")

# D 43–56 the note
scene("d", 43, 56, note_scene("d"), [
    ("d-c1", "เขาไม่รอแรงบันดาลใจอีกแล้ว", 47.5, 51.5, ""),
    ("d-c2", "เขาแค่… เริ่ม", 52.0, 55.8, "big")])
js("""
{ const S = 43;
tl.fromTo("#cam-d", {scale: 1.08}, {scale: 1.0, duration: 13, ease: "power1.out"}, S);
tl.fromTo("#d-ink", {attr: {width: 0}}, {attr: {width: 440}, duration: 2.6, ease: "none"}, S + 1.0);
tl.fromTo("#d-hand", {x: 0}, {x: 400, duration: 2.6, ease: "none"}, S + 1.0);
tl.fromTo("#d-hand", {y: 0}, {y: -14, duration: 0.13, yoyo: true, repeat: 19, ease: "sine.inOut"}, S + 1.0);
tl.to("#d-hand", {x: 900, y: 500, duration: 0.8, ease: "power2.in"}, S + 3.8);
}
""")

# E 56–64 rain run and fall
scene("e", 56, 64, street("e", ["tired", "shock"]), [("e-c1", "มันยากกว่าที่คิด", 58.0, 63.8, "")])
js("""
{ const S = 56;
tl.fromTo("#e-city", {x: 0}, {x: -700, duration: 6.2, ease: "none"}, S);
tl.fromTo("#e-lamps", {x: 0}, {x: -1100, duration: 6.2, ease: "none"}, S);
tl.fromTo("#e-dash", {x: 0}, {x: -1300, duration: 6.2, ease: "none"}, S);
tl.fromTo("#e-rain", {y: 0}, {y: 260, duration: 0.4, repeat: 19, ease: "none"}, S);
tl.to("#e-rw", {rotation: 72, svgOrigin: "960 800", y: 40, duration: 0.45, ease: "power3.in"}, S + 6.2);
tl.set("#e-face-tired", {opacity: 0}, S + 6.2); tl.set("#e-face-shock", {opacity: 1}, S + 6.2);
tl.fromTo("#cam-e", {x: 0}, {x: 10, duration: 0.05, yoyo: true, repeat: 5, ease: "none", immediateRender: false}, S + 6.65);
}
""")
run_cycle("e", 56, 6.2, 0.32, 32, 38, 14)

# F 64–70 pushups that collapse
scene("f", 64, 70, floor_room("f", ["grit", "tired"]), [("f-c1", "ร่างกายขอร้องให้หยุด", 64.5, 69.8, "")])
js("""
{ const S = 64;
tl.fromTo("#cam-f", {scale: 1.05}, {scale: 1.15, duration: 6, ease: "none"}, S);
tl.fromTo("#f-plank", {rotation: 0, svgOrigin: "-280 -40"}, {rotation: 9, svgOrigin: "-280 -40", duration: 0.7, yoyo: true, repeat: 5, ease: "sine.inOut"}, S);
tl.fromTo("#f-arms", {scaleY: 1, svgOrigin: "126 0"}, {scaleY: 0.55, svgOrigin: "126 0", duration: 0.7, yoyo: true, repeat: 5, ease: "sine.inOut"}, S);
tl.fromTo("#f-shake", {x: 0}, {x: 4, duration: 0.04, yoyo: true, repeat: 30, ease: "none"}, S + 2.5);
tl.to("#f-plank", {rotation: 13, svgOrigin: "-280 -40", duration: 0.25, ease: "power3.in"}, S + 4.4);
tl.to("#f-arms", {scaleY: 0.35, svgOrigin: "126 0", duration: 0.25, ease: "power3.in"}, S + 4.4);
tl.set("#f-face-grit", {opacity: 0}, S + 4.6); tl.set("#f-face-tired", {opacity: 1}, S + 4.6);
}
""")

# G 70–77 crossing days
scene("g", 70, 77, calendar("g", crossed=range(1, 9)), [("g-c1", "แต่เขาก็ยังทำต่อ", 71.0, 76.8, "")])
js("""
{ const S = 70;
tl.fromTo("#cam-g", {scale: 1.0}, {scale: 1.06, duration: 7, ease: "none"}, S);
for (let d = 1; d <= 8; d++) tl.to(`#g-x${d}`, {strokeDashoffset: 0, duration: 0.3, ease: "power2.out"}, S + 0.5 + (d - 1) * 0.65);
}
""")

# H 77–85 the gap
scene("h", 77, 85, calendar("h", crossed=range(1, 9), gap=(9, 10, 11)), [("h-c1", "แล้ววันหนึ่ง… เขาก็พลาด", 78.0, 84.8, "big")])
js("""
{ const S = 77;
for (let d = 1; d <= 8; d++) tl.set(`#h-x${d}`, {strokeDashoffset: 0}, S);
tl.fromTo("#cam-h", {scale: 1.0}, {scale: 1.45, duration: 8, ease: "power1.inOut", transformOrigin: "62% 72%"}, S);
[9, 10, 11].forEach((d, i) => tl.fromTo(`#h-gap${d}`, {opacity: 0}, {opacity: 1, duration: 0.2, ease: "none"}, S + 2.0 + i * 0.6));
}
""")

# I 85–100 relapse, inner voice
scene("i", 85, 100, phone_scene("i", "sad"), [
    ("i-c1", "“เห็นไหม… แกทำไม่ได้หรอก”", 86.5, 92.2, "voice top"),
    ("i-c2", "“ยอมแพ้ไปเถอะ”", 93.0, 99.4, "voice top")])
js("""
{ const S = 85;
tl.fromTo("#cam-i", {scale: 1.1}, {scale: 1.32, duration: 15, ease: "none"}, S);
tl.set("#i-t1", {opacity: 0}, S); tl.set("#i-t3", {opacity: 1}, S);
tl.fromTo("#i-feed", {y: 0}, {y: -248, duration: 2.2, ease: "power1.inOut", repeat: 5}, S);
tl.fromTo("#i-glow", {opacity: 1}, {opacity: 0.35, duration: 15, ease: "none"}, S);
tl.fromTo("#i-head", {rotation: 0, transformOrigin: "50% 100%"}, {rotation: -7, transformOrigin: "50% 100%", duration: 6, ease: "sine.inOut"}, S + 7);
}
""")

# J 100–123 the turn (music drops at ~107, climax hits at ~119)
scene("j", 100, 123, bedroom("j", ["sad", "sleepy", "det"], clock="4:59") + f"""
  <rect id="j-dark" width="1920" height="1080" fill="#000" opacity="0.45"/>
  <g id="j-sit" opacity="0">
    <rect width="1920" height="1080" fill="#0d0f18"/>
    <rect x="1440" y="140" width="320" height="700" fill="#1a1d29" stroke="#2c3040" stroke-width="10"/>
    <rect id="j-doorlight" x="1450" y="150" width="0" height="680" fill="#fff3cf"/>
    <ellipse id="j-flood" cx="1600" cy="490" rx="10" ry="10" fill="url(#g-door)"/>
    <rect y="840" width="1920" height="240" fill="#090a10"/>
    <g id="j-stand"><g transform="translate(820 470) scale(1.1)">{person_front("js", ["det"])}</g></g>
  </g>
  <rect id="j-black" width="1920" height="1080" fill="#000" opacity="0"/>
  <text id="j-blackclock" x="960" y="590" text-anchor="middle" font-family="Kanit" font-weight="700" font-size="170" fill="#ff3b3b" opacity="0">5:00</text>""",
      [("j-c0", "เขานอนมองเพดานทั้งคืน", 101.0, 106.4, ""),
       ("j-c1", "ทุกคนล้มได้", 113.5, 118.6, "huge"),
       ("j-c2", "แต่ห้ามล้มเลิก", 119.3, 122.8, "huge")])
js("""
{ const S = 100;
tl.fromTo("#cam-j", {scale: 1.0}, {scale: 1.1, duration: 7, ease: "none"}, S);
tl.set("#j-face-sad", {opacity: 0}, S + 4.5); tl.set("#j-face-sleepy", {opacity: 1}, S + 4.5);
tl.to("#j-black", {opacity: 1, duration: 0.8, ease: "power1.in"}, S + 6.2);
tl.to("#j-blackclock", {opacity: 1, duration: 0.6, ease: "power1.out"}, S + 7.2);
tl.to("#j-blackclock", {opacity: 0, duration: 0.2}, S + 8.8);
tl.to("#j-black", {opacity: 0, duration: 0.3}, S + 9.0);
tl.set("#j-clocktxt", {opacity: 0}, S + 9.0); tl.set("#j-clocktxt2", {opacity: 1}, S + 9.0);
tl.set("#j-dark", {opacity: 0.2}, S + 9.0);
tl.fromTo("#j-ring", {opacity: 0}, {opacity: 1, duration: 0.12, yoyo: true, repeat: 11, ease: "none"}, S + 9.0);
tl.fromTo("#j-clock", {x: 0}, {x: 6, duration: 0.05, yoyo: true, repeat: 27, ease: "none"}, S + 9.0);
tl.set("#j-face-sleepy", {opacity: 0}, S + 10.6); tl.set("#j-face-det", {opacity: 1}, S + 10.6);
tl.fromTo("#cam-j", {scale: 1.1}, {scale: 2.7, duration: 1.4, ease: "power3.inOut", transformOrigin: "36% 54%", immediateRender: false}, S + 10.4);
tl.set("#j-sit", {opacity: 1}, S + 13.0);
tl.set("#cam-j", {scale: 1.0, transformOrigin: "50% 50%"}, S + 13.0);
tl.fromTo("#j-stand", {y: 170, scale: 0.9, transformOrigin: "50% 100%"}, {y: 0, scale: 1, transformOrigin: "50% 100%", duration: 1.1, ease: "power3.out"}, S + 13.2);
tl.fromTo("#js-head", {rotation: -6, transformOrigin: "50% 100%"}, {rotation: 0, transformOrigin: "50% 100%", duration: 1.1, ease: "power2.out"}, S + 13.2);
tl.to("#j-doorlight", {attr: {width: 300}, duration: 1.0, ease: "power2.inOut"}, S + 19.2);
tl.to("#j-stand", {x: 560, y: -40, scale: 0.78, transformOrigin: "50% 100%", duration: 3.6, ease: "power1.in"}, S + 19.4);
tl.to("#j-flood", {attr: {rx: 1900, ry: 1500}, duration: 2.6, ease: "power2.in"}, S + 20.4);
}
""")

# K 123–127.5 dawn run
scene("k", 123, 127.5, street("k", ["det"], dawn=True), [("k-c1", "วันที่ 23", 123.3, 127.3, "day")])
js("""
{ const S = 123;
tl.fromTo("#k-sun", {attr: {cy: 700}}, {attr: {cy: 560}, duration: 4.5, ease: "none"}, S);
tl.fromTo("#k-city", {x: 0}, {x: -600, duration: 4.5, ease: "none"}, S);
tl.fromTo("#k-dash", {x: 0}, {x: -1300, duration: 4.5, ease: "none"}, S);
}
""")
run_cycle("k", 123, 4.5, 0.26, 38, 45, 16)

# L 127.5–131.5 strong pushups
scene("l", 127.5, 131.5, floor_room("l", ["grit"], strong=True), [("l-c1", "วันที่ 47", 127.8, 131.3, "day")])
js("""
{ const S = 127.5;
tl.fromTo("#l-plank", {rotation: 0, svgOrigin: "-280 -40"}, {rotation: 9, svgOrigin: "-280 -40", duration: 0.4, yoyo: true, repeat: 9, ease: "sine.inOut"}, S);
tl.fromTo("#l-arms", {scaleY: 1, svgOrigin: "126 0"}, {scaleY: 0.55, svgOrigin: "126 0", duration: 0.4, yoyo: true, repeat: 9, ease: "sine.inOut"}, S);
tl.fromTo("#cam-l", {scale: 1.0}, {scale: 1.08, duration: 4, ease: "none"}, S);
}
""")

# M 131.5–135.5 reading
scene("m", 131.5, 135.5, reading("m"), [("m-c1", "วันที่ 68", 131.8, 135.3, "day")])
js("""
{ const S = 131.5;
tl.fromTo("#cam-m", {scale: 1.0}, {scale: 1.08, duration: 4, ease: "none"}, S);
tl.fromTo("#m-page", {scaleX: 1, svgOrigin: "0 0"}, {scaleX: -1, svgOrigin: "0 0", duration: 0.6, ease: "power2.inOut", repeat: 1, repeatDelay: 1.0}, S + 0.6);
tl.fromTo("#m-head", {rotation: 0, transformOrigin: "50% 100%"}, {rotation: 3, transformOrigin: "50% 100%", duration: 1.0, yoyo: true, repeat: 3, ease: "sine.inOut"}, S);
}
""")

# N 135.5–140 a hundred days
scene("n", 135.5, 140, grid100("n"), [("n-c1", "วันที่ <span id=\"n-count\">68</span>", 135.7, 139.8, "day")])
js("""
{ const S = 135.5;
tl.fromTo(".n-sq", {opacity: 0, scale: 0.4, transformOrigin: "50% 50%"}, {opacity: 1, scale: 1, transformOrigin: "50% 50%", duration: 0.2, stagger: 0.025, ease: "back.out(2)"}, S + 0.2);
const nc = {v: 68};
tl.fromTo(nc, {v: 68}, {v: 100, duration: 2.6, ease: "power1.inOut", onUpdate: () => { document.getElementById("n-count").textContent = Math.round(nc.v); }}, S + 0.4);
tl.fromTo("#cam-n", {scale: 1.0}, {scale: 1.06, duration: 4.5, ease: "none"}, S);
}
""")

# O 140–144.5 mirror callback
scene("o", 140, 144.5, mirror_scene("o", "smile", warm=True), [("o-c1", "คนในกระจก… เริ่มคุ้นหน้าแล้ว", 140.4, 144.3, "big")])
js("""
{ const S = 140;
tl.fromTo("#cam-o", {scale: 1.2}, {scale: 1.0, duration: 4.5, ease: "power1.out"}, S);
tl.set("#o-dim", {opacity: 0}, S);
}
""")

# P 144.5–150 hill and title
scene("p", 144.5, 150, hill("p") + """
  <rect id="p-fade" width="1920" height="1080" fill="#000" opacity="0"/>""", [
    ("p-c1", "แค่ลุกขึ้นมา… อีกครั้ง", 144.8, 147.0, "big")])
js("""
{ const S = 144.5;
tl.fromTo("#p-sun", {attr: {cy: 860}}, {attr: {cy: 640}, duration: 5.5, ease: "power1.out"}, S);
tl.fromTo("#p-sunglow", {attr: {cy: 860}}, {attr: {cy: 640}, duration: 5.5, ease: "power1.out"}, S);
tl.fromTo("#cam-p", {scale: 1.12}, {scale: 1.0, duration: 5.5, ease: "power1.out"}, S);
tl.to("#p-fade", {opacity: 0.7, duration: 0.6, ease: "power1.inOut"}, S + 2.4);
tl.fromTo("#title", {opacity: 0, scale: 1.25}, {opacity: 1, scale: 1, duration: 0.9, ease: "power3.out"}, S + 2.6);
tl.fromTo("#title-sub", {opacity: 0, y: 30}, {opacity: 1, y: 0, duration: 0.6, ease: "power2.out"}, S + 3.1);
tl.fromTo("#title-tag", {opacity: 0}, {opacity: 1, duration: 0.6}, S + 3.5);
tl.to("#p-fade", {opacity: 1, duration: 0.8, ease: "power1.in"}, S + 4.7);
tl.to("#title-wrap", {opacity: 0, duration: 0.7}, S + 4.8);
}
""")

# ============================================================
# assemble
# ============================================================
sections = []
cap_js = []
for sid, a, b, svg, caps in SCENES:
    cap_html = "".join(f'<div class="cap {cls}" id="{cid}">{text}</div>' for cid, text, _, _, cls in caps)
    sections.append(
        f'<section id="s-{sid}" class="clip" data-start="{a}" data-duration="{b - a}" data-track-index="1">'
        f'<div class="cam" id="cam-{sid}"><svg viewBox="0 0 1920 1080" width="1920" height="1080">{svg}</svg></div>'
        f'<div class="vig"></div>{cap_html}</section>')
    for cid, text, t0, t1, cls in caps:
        cap_js.append(f'tl.fromTo("#{cid}", {{opacity: 0, y: 24}}, {{opacity: 1, y: 0, duration: 0.6, ease: "power2.out"}}, {t0});')
        cap_js.append(f'tl.to("#{cid}", {{opacity: 0, duration: 0.45, ease: "power1.in"}}, {t1 - 0.45});')

fonts = (ROOT.parent / "movie-trivia-short" / "index.html").read_text().split("<style>")[1].split(":root")[0]

html = f'''<!doctype html>
<html lang="th">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1920, height=1080" />
    <title>AGAIN. — อีกครั้ง</title>
    <script src="assets/vendor/gsap.min.js"></script>
    <style>{fonts}
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ width: 1920px; height: 1080px; overflow: hidden; background: #000; }}
      #root {{ position: relative; width: 100%; height: 100%; overflow: hidden; background: #000; font-family: "Kanit", sans-serif; color: {WHITE}; }}
      .clip {{ position: absolute; inset: 0; }}
      section.clip {{ overflow: hidden; }}
      .cam {{ position: absolute; inset: 0; transform-origin: 50% 50%; }}
      .cam svg {{ display: block; }}
      .vig {{ position: absolute; inset: 0; background: radial-gradient(ellipse at 50% 45%, rgba(0,0,0,0) 55%, rgba(0,0,0,0.55) 100%); }}
      .cap {{ position: absolute; left: 460px; right: 460px; top: 880px; text-align: center; font-weight: 700; font-size: 60px; line-height: 1.3;
              color: {WHITE}; text-shadow: 0 4px 24px rgba(0,0,0,0.9), 0 2px 4px rgba(0,0,0,0.9); opacity: 0; white-space: nowrap; }}
      .cap.big {{ font-weight: 900; font-size: 68px; }}
      .cap.top {{ top: 70px; }}
      .cap.huge {{ top: 90px; font-weight: 900; font-size: 104px; color: #ffd27a; }}
      .cap.voice {{ font-weight: 400; font-style: italic; color: #ff8b80; }}
      .cap.day {{ top: 70px; font-weight: 900; font-size: 84px; color: #ffd27a; letter-spacing: 0.02em; }}
      #titlecard {{ z-index: 5; }}
      #title-wrap {{ position: absolute; left: 0; right: 0; top: 330px; display: flex; flex-direction: column; align-items: center; gap: 10px; }}
      #title {{ display: block; font-weight: 900; font-size: 260px; line-height: 1.05; letter-spacing: -0.01em; color: {WHITE}; opacity: 0; }}
      #title-sub {{ display: block; font-weight: 700; font-size: 72px; color: #ffd27a; opacity: 0; }}
      #title-tag {{ display: block; font-weight: 400; font-size: 44px; color: #d8d2c6; margin-top: 18px; opacity: 0; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{DUR}" data-width="1920" data-height="1080">
      <svg width="0" height="0" style="position:absolute">{DEFS}</svg>
      {"".join(sections)}
      <div id="titlecard" class="clip" data-start="146.5" data-duration="3.5" data-track-index="2">
        <div id="title-wrap"><span id="title">AGAIN.</span><span id="title-sub">อีกครั้ง</span><span id="title-tag">วันนี้ อาจเป็น “วันที่ 1” ของคุณ</span></div>
      </div>
      <audio id="score" src="assets/audio/score.m4a" data-start="0" data-duration="{DUR}" data-track-index="3" data-volume="0.9"></audio>
      <audio id="sfx" src="assets/audio/sfx.m4a" data-start="0" data-duration="{DUR}" data-track-index="4" data-volume="0.8"></audio>
    </div>
    <script>
      const tl = gsap.timeline({{ paused: true }});
{"".join(JS)}
{chr(10).join(cap_js)}
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
'''
(ROOT / "index.html").write_text(html)
print("wrote", ROOT / "index.html", len(html), "bytes")
