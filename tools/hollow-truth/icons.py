"""Drawn evidence prints for the case board. Each returns SVG markup for a 440x420 box."""
import math

INK = "#cfc8b4"      # pale print ink
DIM = "#8d8775"
DARK = "#1b1f24"


def _gear(cx, cy, r, teeth, fill):
    pts = []
    for i in range(teeth * 2):
        a = math.pi * 2 * i / (teeth * 2)
        rr = r if i % 2 == 0 else r * 0.82
        a2 = a + math.pi * 2 / (teeth * 4)
        pts.append(f"{cx + rr * math.cos(a):.1f},{cy + rr * math.sin(a):.1f}")
        pts.append(f"{cx + rr * math.cos(a2):.1f},{cy + rr * math.sin(a2):.1f}")
    return (f'<polygon points="{" ".join(pts)}" fill="{fill}"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r * 0.55:.1f}" fill="{DARK}"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r * 0.18:.1f}" fill="{fill}"/>')


def _disc():
    out = [f'<circle cx="220" cy="210" r="175" fill="#b49a6c"/>',
           f'<circle cx="220" cy="210" r="175" fill="none" stroke="#7a6542" stroke-width="5"/>']
    d = "M 220 210"
    pts = []
    for i in range(400):
        a = i * 0.075
        r = 8 + a * 9.5
        if r > 168:
            break
        pts.append((220 + r * math.cos(a), 210 + r * math.sin(a)))
    d += " " + " ".join(f"L {x:.1f} {y:.1f}" for x, y in pts)
    out.append(f'<path d="{d}" fill="none" stroke="#5e4c31" stroke-width="3"/>')
    for i in range(0, len(pts) - 6, 6):
        x, y = pts[i + 3]
        out.append(f'<rect x="{x - 4:.1f}" y="{y - 4:.1f}" width="8" height="8" fill="#5e4c31" transform="rotate({i * 7} {x:.1f} {y:.1f})"/>')
    return "".join(out)


ICONS = {
    "lighthouse": f'''
      <path d="M 0 360 C 80 330 140 345 220 330 C 300 318 360 340 440 330 L 440 420 L 0 420 Z" fill="#2b3036"/>
      <polygon points="190,140 250,140 268,335 172,335" fill="{INK}"/>
      <rect x="183" y="190" width="74" height="18" fill="{DIM}"/>
      <rect x="179" y="260" width="82" height="18" fill="{DIM}"/>
      <rect x="182" y="96" width="76" height="46" fill="{DARK}" stroke="{INK}" stroke-width="5"/>
      <polygon points="176,96 264,96 220,62" fill="{INK}"/>
      <rect x="164" y="138" width="112" height="8" fill="{INK}"/>
      <rect x="290" y="300" width="70" height="40" fill="{DIM}"/>
      <polygon points="285,300 365,300 325,278" fill="{INK}"/>''',
    "post": f'''
      <rect x="140" y="30" width="160" height="380" fill="#6d5a40"/>
      <path d="M 160 40 L 160 400 M 210 40 L 210 400 M 262 40 L 262 400" stroke="#4e3f2c" stroke-width="3"/>
      <text x="220" y="230" fill="#e2d6b8" font-family="Oswald, sans-serif" font-weight="600" font-size="52" text-anchor="middle" transform="rotate(-90 220 230)" letter-spacing="6">CROATOAN</text>''',
    "jet": f'''
      <path d="M 40 210 C 60 186 110 180 160 180 L 340 180 L 395 120 L 418 120 L 400 190 C 405 205 395 222 370 224 L 90 226 C 60 226 44 220 40 210 Z" fill="{INK}"/>
      <path d="M 190 205 L 280 205 L 230 275 L 205 275 Z" fill="{DIM}"/>
      <path d="M 365 224 L 405 290" stroke="{INK}" stroke-width="7"/>
      <g fill="{DARK}">{"".join(f'<rect x="{110 + i * 22}" y="190" width="10" height="9" rx="2"/>' for i in range(10))}</g>''',
    "parachute": f'''
      <path d="M 90 170 C 110 70 330 70 350 170 C 320 150 290 150 270 172 C 245 150 195 150 170 172 C 150 150 120 150 90 170 Z" fill="{INK}"/>
      <g stroke="{DIM}" stroke-width="3"><path d="M 92 170 L 220 330"/><path d="M 170 172 L 220 330"/><path d="M 270 172 L 220 330"/><path d="M 348 170 L 220 330"/></g>
      <circle cx="220" cy="336" r="11" fill="{INK}"/><path d="M 220 345 L 220 380 M 220 380 L 205 410 M 220 380 L 235 410 M 220 355 L 200 370 M 220 355 L 240 370" stroke="{INK}" stroke-width="7" stroke-linecap="round"/>''',
    "book": f'''
      <path d="M 30 90 C 110 70 180 80 218 100 L 218 370 C 180 350 110 342 30 360 Z" fill="#c4b48c"/>
      <path d="M 410 90 C 330 70 260 80 222 100 L 222 370 C 260 350 330 342 410 360 Z" fill="#cdbf98"/>
      <g fill="none" stroke="#5c6a3a" stroke-width="4"><path d="M 120 330 C 118 260 130 200 120 140"/><path d="M 122 240 C 90 220 70 230 64 200 C 92 196 110 210 122 240"/><path d="M 124 200 C 160 180 176 190 186 160 C 156 156 136 170 124 200"/><path d="M 120 140 C 100 120 112 100 130 104 C 140 116 132 130 120 140"/></g>
      <g stroke="#4c3d28" stroke-width="3">{"".join(f'<path d="M 250 {120 + i * 22} L {380 - (i % 3) * 18} {116 + i * 22}"/>' for i in range(10))}</g>''',
    "bomber": f'''
      <g fill="{INK}">
        <path d="M 30 200 C 50 182 90 176 130 178 L 330 186 C 360 188 370 196 372 206 C 370 214 350 220 320 220 L 120 222 C 80 222 46 216 30 200 Z"/>
        <path d="M 150 196 L 300 196 L 245 112 L 222 112 Z"/>
        <path d="M 330 192 L 380 150 L 396 150 L 380 205 Z"/>
        <ellipse cx="128" cy="180" rx="34" ry="14" fill="{DIM}"/>
        <circle cx="34" cy="200" r="16" fill="{DIM}"/>
      </g>
      <g fill="{DIM}" opacity="0.7"><path d="M 60 300 L 120 296 L 102 270 Z"/><path d="M 280 310 L 340 306 L 322 280 Z"/></g>''',
    "electra": f'''
      <g fill="{INK}">
        <path d="M 210 60 C 222 60 228 80 228 110 L 230 330 C 230 350 222 360 220 360 C 218 360 210 350 210 330 L 212 110 C 212 80 198 60 210 60 Z" transform="translate(0 0)"/>
        <path d="M 40 190 L 400 190 L 400 214 L 40 214 Z"/>
        <path d="M 150 340 L 290 340 L 290 356 L 150 356 Z"/>
        <ellipse cx="140" cy="200" rx="18" ry="40" fill="{DIM}"/>
        <ellipse cx="300" cy="200" rx="18" ry="40" fill="{DIM}"/>
      </g>''',
    "tv": f'''
      <rect x="60" y="70" width="320" height="250" rx="26" fill="#3b3a36"/>
      <rect x="86" y="94" width="230" height="200" rx="18" fill="#9fa7a8"/>
      <g stroke="#6f7778" stroke-width="3">{"".join(f'<path d="M 90 {104 + i * 12} L 312 {104 + i * 12}"/>' for i in range(16))}</g>
      <ellipse cx="201" cy="192" rx="52" ry="66" fill="#d6d2c4"/>
      <rect x="160" y="168" width="82" height="20" rx="8" fill="#1d1d1d"/>
      <path d="M 176 228 C 195 240 210 240 228 228" stroke="#1d1d1d" stroke-width="6" fill="none"/>
      <circle cx="350" cy="150" r="12" fill="#6d6b64"/><circle cx="350" cy="200" r="12" fill="#6d6b64"/>
      <path d="M 150 320 L 120 380 M 290 320 L 320 380" stroke="#3b3a36" stroke-width="10"/>''',
    "house": f'''
      <path d="M 70 380 L 70 210 L 220 100 L 370 210 L 370 380 Z" fill="#2c2a28"/>
      <rect x="120" y="240" width="60" height="60" fill="#e48a3a"/><rect x="260" y="240" width="60" height="60" fill="#e48a3a"/>
      <rect x="196" y="300" width="50" height="80" fill="#e8a24a"/>
      <path d="M 150 210 C 140 160 175 150 170 100 C 200 140 215 120 222 80 C 240 120 270 130 262 170 C 290 150 300 120 300 100 C 330 150 320 190 296 214 Z" fill="#e0742e" opacity="0.9"/>
      <path d="M 190 200 C 190 170 205 160 208 130 C 225 160 236 170 232 200 Z" fill="#f2c060"/>''',
    "billboard": f'''
      <rect x="40" y="70" width="360" height="190" fill="#d8d0b8"/>
      <rect x="40" y="70" width="360" height="190" fill="none" stroke="#6d5a40" stroke-width="8"/>
      <g fill="#3a2f22"><rect x="70" y="100" width="300" height="20"/><rect x="70" y="140" width="250" height="14"/><rect x="70" y="170" width="280" height="14"/></g>
      <g fill="#7d7768">{"".join(f'<rect x="{80 + i * 58}" y="200" width="40" height="44"/>' for i in range(5))}</g>
      <path d="M 110 260 L 110 400 M 330 260 L 330 400" stroke="#6d5a40" stroke-width="14"/>''',
    "dancer": f'''
      <g fill="{INK}" stroke="{INK}" stroke-linecap="round">
        <circle cx="220" cy="90" r="26"/>
        <path d="M 220 118 L 214 230" stroke-width="22"/>
        <path d="M 218 140 L 160 84 M 218 140 L 288 96" stroke-width="12" fill="none"/>
        <path d="M 214 228 L 170 330 L 136 360 M 214 228 L 262 310 L 300 300" stroke-width="13" fill="none"/>
        <path d="M 214 160 C 180 220 170 260 160 290 L 270 290 C 260 250 250 210 220 160 Z" stroke="none" fill="{DIM}"/>
      </g>
      <g fill="{DIM}" opacity="0.6"><circle cx="70" cy="250" r="14"/><path d="M 70 266 L 66 330" stroke="{DIM}" stroke-width="10"/><circle cx="380" cy="240" r="14"/><path d="M 380 256 L 384 320" stroke="{DIM}" stroke-width="10"/></g>''',
    "forest": f'''
      <circle cx="220" cy="210" r="30" fill="#4a4136"/>
      <g stroke="{INK}" stroke-width="5" stroke-linecap="round">{"".join(f'<path d="M {220 + 50 * math.cos(a):.0f} {210 + 50 * math.sin(a):.0f} L {220 + (110 + (i % 3) * 30) * math.cos(a):.0f} {210 + (110 + (i % 3) * 30) * math.sin(a):.0f}"/>' for i, a in enumerate([k * math.pi / 14 for k in range(28)]))}</g>
      <g stroke="{DIM}" stroke-width="3" stroke-linecap="round">{"".join(f'<path d="M {220 + 180 * math.cos(a):.0f} {210 + 180 * math.sin(a):.0f} L {220 + 205 * math.cos(a):.0f} {210 + 205 * math.sin(a):.0f}"/>' for a in [k * math.pi / 20 + 0.07 for k in range(40)])}</g>''',
    "gears": _gear(150, 180, 90, 18, "#8f7a4a") + _gear(290, 230, 64, 13, "#a08a58") + _gear(250, 90, 40, 9, "#7c6a40"),
    "mask": f'''
      <path d="M 70 170 C 70 130 140 120 220 120 C 300 120 370 130 370 170 C 370 220 320 250 280 250 C 250 250 240 225 220 225 C 200 225 190 250 160 250 C 120 250 70 220 70 170 Z" fill="#8a8c8e"/>
      <path d="M 70 170 C 70 130 140 120 220 120 C 300 120 370 130 370 170" fill="none" stroke="#b8babc" stroke-width="5"/>
      <path d="M 70 175 L 20 160 M 370 175 L 420 160" stroke="#5d5f61" stroke-width="5"/>
      <g fill="#6c6e70"><circle cx="150" cy="185" r="6"/><circle cx="290" cy="185" r="6"/></g>''',
    "lights": f'''
      <path d="M 0 330 L 90 240 L 160 300 L 250 210 L 330 290 L 440 220 L 440 420 L 0 420 Z" fill="#2a3138"/>
      <path d="M 0 380 L 120 330 L 220 370 L 330 320 L 440 360 L 440 420 L 0 420 Z" fill="#1f252b"/>
      <circle cx="140" cy="120" r="16" fill="#f3e9c6"/><circle cx="140" cy="120" r="34" fill="#f3e9c6" opacity="0.18"/>
      <circle cx="300" cy="90" r="10" fill="#f3e9c6"/><circle cx="300" cy="90" r="24" fill="#f3e9c6" opacity="0.18"/>
      <path d="M 330 160 L 400 140" stroke="#f3e9c6" stroke-width="4" stroke-linecap="round" opacity="0.7"/><circle cx="400" cy="140" r="8" fill="#f3e9c6"/>''',
    "cloud": f'''
      <path d="M 90 150 C 80 110 130 90 160 110 C 175 70 250 70 268 110 C 300 90 350 110 345 150 C 375 160 370 200 340 200 L 100 200 C 70 200 62 160 90 150 Z" fill="{INK}"/>
      <g fill="#8e2f2a">{"".join(f'<path d="M {x} {y} l 14 -6 l 10 10 l -6 14 l -14 -2 Z" transform="rotate({x % 50} {x} {y})"/>' for x, y in [(120, 250), (180, 300), (240, 240), (300, 320), (150, 360), (270, 380), (210, 350), (330, 260)])}</g>''',
    "pillar": f'''
      <rect x="180" y="150" width="80" height="250" fill="#a39780"/>
      <rect x="110" y="90" width="220" height="70" fill="#b0a48c"/>
      <g fill="none" stroke="#5f5644" stroke-width="5" stroke-linecap="round"><path d="M 200 230 C 215 210 235 215 242 235 L 236 270 L 205 268 Z"/><path d="M 236 238 L 252 224"/><path d="M 208 268 L 204 290 M 232 270 L 236 292"/><path d="M 196 320 C 210 310 230 312 244 322"/></g>
      <path d="M 0 400 L 440 400 L 440 420 L 0 420 Z" fill="#3a352b"/>''',
    "hummingbird": f'''
      <rect x="0" y="0" width="440" height="420" fill="#8b7558"/>
      <g fill="none" stroke="#e3d7bb" stroke-width="5" stroke-linejoin="round" stroke-linecap="round">
        <path d="M 60 120 L 190 170"/>
        <path d="M 190 170 C 200 150 225 148 236 166 C 250 190 240 220 226 240 L 210 330 L 196 380 M 210 330 L 224 380 M 205 335 L 210 395"/>
        <path d="M 230 190 L 330 110 L 350 130 L 260 205 L 380 160 L 392 182 L 262 226 Z"/>
        <path d="M 200 200 L 120 230 L 112 212 L 196 186"/>
      </g>''',
    "ear": f'''
      <path d="M 210 90 C 140 90 110 150 120 200 C 128 240 160 250 160 290 C 160 330 190 350 215 335 C 230 325 228 300 245 290 C 280 270 300 230 296 180 C 290 120 260 90 210 90 Z" fill="{INK}"/>
      <path d="M 180 170 C 180 140 230 130 245 165 C 255 190 230 205 220 225 C 212 240 225 255 215 265" fill="none" stroke="{DARK}" stroke-width="10" stroke-linecap="round"/>
      <g fill="none" stroke="{DIM}" stroke-width="5" stroke-linecap="round"><path d="M 330 160 C 345 190 345 220 330 250"/><path d="M 360 140 C 382 185 382 225 360 270"/><path d="M 390 120 C 420 180 420 230 390 290"/></g>''',
    "disc": _disc(),
    "children": f'''
      <g fill="#8fb07a">
        <circle cx="160" cy="130" r="30"/><path d="M 130 170 L 190 170 L 205 320 L 115 320 Z"/>
        <circle cx="285" cy="150" r="26"/><path d="M 258 186 L 312 186 L 324 320 L 246 320 Z"/>
      </g>
      <g stroke="#8fb07a" stroke-width="12" stroke-linecap="round"><path d="M 140 320 L 140 390 M 180 320 L 180 390 M 268 320 L 268 390 M 302 320 L 302 390"/><path d="M 195 200 C 220 230 240 230 258 210"/></g>''',
}


def icon(name):
    return ICONS[name]
