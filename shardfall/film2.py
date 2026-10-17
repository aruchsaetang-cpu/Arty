"""SHARDFALL v2 — the same 180 s cut and score, re-shot on the 14 detailed keyframes (src/v2/n01..n14).

World coordinates are 1280x720 (each picture scaled to that space); plates are 2560x1440.
Usage: python3 film2.py prep | render <a> <b> <out.mp4> | still <sec> <out.png>
"""
import math, os, sys
import cv2, numpy as np

import film as F
from film import (Cam, cam_with_shake, render_mb, add_light, light_from_u8, _u8, col8, blank, flash, tint,
                  chroma, zoom_blur, two_tone, shockwave, speed_lines, parallel_lines, motes, draw_birds, ribbons,
                  bezier, haze, smooth, ease_io, ease_out, ease_out_expo, ease_in, lerp, clamp01, pulse, twos, threes,
                  CYAN, GOLD, WHITE, W, H, FPS, VIGNETTE, _yy, CrackTree, Shards, SH_FALL, SH_FALL2, SH_SNOW,
                  SH_SNOW_FG, SH_BURST, SH_DRIFT, CRK_TITLE)

HERE = os.path.dirname(os.path.abspath(__file__))
_PL = {}


def plate(k):
    if k not in _PL:
        _PL[k] = cv2.cvtColor(cv2.imread(os.path.join(HERE, "plates2", k + ".png")), cv2.COLOR_BGR2RGB)
    return _PL[k]


F.plate = plate  # film.render_plate / render_mb look the plate up through this name


def prep():
    os.makedirs(os.path.join(HERE, "plates2"), exist_ok=True)
    for i in range(1, 15):
        k = f"n{i:02d}"
        im = cv2.imread(os.path.join(HERE, "src/v2", k + ".jpg"))
        up = cv2.resize(im, (2560, 1440), interpolation=cv2.INTER_LANCZOS4)
        blur = cv2.GaussianBlur(up, (0, 0), 1.6)
        up = cv2.addWeighted(up, 1.35, blur, -0.35, 0)  # gentle unsharp: keep the fine line art crisp
        cv2.imwrite(os.path.join(HERE, "plates2", k + ".png"), up)
        print("plate", k)


def rp(key, cam, t=0.0, sway=None, warp=None):
    return F.render_plate(key, cam, t, sway, warp)


def sw(cx, cy, rx, ry, amp, axis="y", k=.03, spd=4, grow=False):
    return (cx, cy, rx, ry, amp, k, spd, axis, grow)


# gentle secondary motion on hair ends, ribbons and scarves only (the faces stay still)
SWAY = {
    "n01": [sw(500, 330, 250, 120, 2.0), sw(950, 500, 260, 120, 3.0)],
    "n02": [sw(900, 470, 330, 110, 2.5), sw(1000, 570, 330, 100, 3.0)],
    "n03": [sw(200, 320, 210, 80, 4.0, spd=6), sw(220, 520, 230, 220, 2.5, "x", grow=True)],
    "n04": [sw(860, 110, 150, 110, 3.0, spd=7)],
    "n05": [sw(830, 230, 200, 90, 3.0, spd=9)],
    "n06": [sw(1150, 450, 200, 120, 3.0, spd=9)],
    "n07": [sw(700, 410, 180, 90, 4.0), sw(300, 530, 110, 110, 2.0), sw(820, 600, 150, 150, 2.0, "x", grow=True)],
    "n08": [sw(1050, 280, 260, 90, 4.0), sw(160, 450, 150, 60, 3.0), sw(1010, 470, 130, 200, 2.0, "x", grow=True)],
    "n09": [sw(240, 300, 230, 240, 2.5, "x", grow=True), sw(230, 140, 220, 80, 4.0, spd=6)],
    "n10": [sw(1000, 300, 330, 120, 2.5), sw(900, 440, 260, 70, 3.0)],
    "n11": [sw(800, 370, 230, 120, 3.0, spd=8), sw(1000, 290, 260, 110, 3.5, spd=8)],
    "n12": [sw(1020, 460, 120, 200, 2.5, "x", grow=True), sw(1100, 330, 190, 60, 4.0, spd=6), sw(307, 110, 120, 80, 1.2, "x")],
    "n13": [sw(900, 500, 160, 60, 3.0, spd=6), sw(900, 580, 110, 80, 2.0, "x")],
    "n14": [sw(640, 110, 340, 120, 1.8, "x"), sw(1150, 420, 190, 100, 3.0, spd=6)],
}


def scaled(key, a=1.0, s=1.0):
    return [(cx, cy, rx, ry, amp * a, k, spd * s, axis, g) for cx, cy, rx, ry, amp, k, spd, axis, g in SWAY[key]]


SHOTS = []


def shot(dur):
    def deco(fn):
        SHOTS.append((dur, fn, fn.__name__))
        return fn
    return deco


FLOCK = [(-60 - i * 28, 120 + (i % 3) * 14 + i * 3, 70, -6, 5, i) for i in range(7)]
CRK_SKY = CrackTree(827, 127, seed=5, n_main=10, length=900)
CRK_BEAST = CrackTree(700, 300, seed=21, n_main=9, length=380, step=16, jag=.5)

# ---- ACT 0 -------------------------------------------------------------------
shot(1.5)(F.s_black)


@shot(1.5)
def s_cold_clash(t, T):
    cam = cam_with_shake(lerp(360, 340, t / T), 380, 900 - 90 * twos(t), 0, t, 14, 30)
    img = rp("n05", cam, twos(t), SWAY["n05"])
    sc = cam.scr([(330, 360)])[0]
    img = speed_lines(img, sc[0], sc[1], t, 110, (.14, .36), (0, 0, 0), .7, seed=11)
    ph = int(t * 12) % 4
    if ph == 0: img = two_tone(img, invert=True, th=.5)
    elif ph == 2: img = two_tone(img, dark=(.03, 0, 0), light=(.95, .12, .1), th=.5)
    return chroma(img, .012)


@shot(0.75)
def s_cold_ren(t, T):
    cam = cam_with_shake(520, 200, 620 - 120 * t, -.04, t, 6, 25)
    img = rp("n11", cam)
    img = parallel_lines(img, t, -0.5, 50, (1, 1, 1), .5, seed=3)
    return two_tone(img, dark=(.02, .02, .05), light=(.85, 1, 1), th=.42) if int(t * 12) % 3 == 0 else img


@shot(0.75)
def s_cold_beast(t, T):
    cam = cam_with_shake(1045, 225, 300 - 60 * t, 0, t, 5, 30)
    img = rp("n13", cam)
    lt = _u8()
    e = cam.scr([(1053, 213)])[0]
    cv2.circle(lt, (int(e[0]), int(e[1])), 34, col8(WHITE, .9), -1, cv2.LINE_AA)
    img = add_light(img, light_from_u8(lt), 2, 2)
    return flash(img, smooth((t - .45) / .3))


shot(7.0)(F.s_title)

# ---- ACT 1: dusk ----------------------------------------------------------------


@shot(10.0)
def s_city_pan(t, T):
    p = ease_io(t / T)
    cam = Cam(lerp(560, 720, p), lerp(400, 360, p), lerp(1050, 980, p))
    img = rp("n10", cam, twos(t), SWAY["n10"])
    img = draw_birds(img, cam, t, FLOCK, col=(.15, .1, .2))
    img = haze(img, t, (1, .6, .4), .04, 10)
    lt = _u8()
    motes(lt, t, 4, 50, (1, .75, .45), (1, 3), (8, -6), .4)
    img = add_light(img, light_from_u8(lt))
    return img * smooth(t / 1.2)


@shot(5.0)
def s_city_detail(t, T):
    cam = Cam(lerp(1100, 1150, t / T), lerp(250, 230, t / T), lerp(520, 440, ease_io(t / T)))
    img = rp("n02", cam, twos(t), SWAY["n02"])
    lt = _u8()
    tw = cam.scr([(1215, 60)])[0]
    k = .5 + .5 * math.sin(t * 6)
    cv2.circle(lt, (int(tw[0]), int(tw[1])), 8, col8((1, .5, .4), k), -1, cv2.LINE_AA)  # tower beacon
    motes(lt, t, 5, 40, (1, .8, .5), (1, 3), (12, -10), .4)
    img = add_light(img, light_from_u8(lt), 1.5, 1.2)
    return haze(img, t, (1, .55, .35), .04, 14)


@shot(8.0)
def s_rooftop(t, T):
    cam = Cam(640 + 5 * math.sin(t * .4), 360 + 3 * math.sin(t * .3), 1240 - 40 * t / T)
    img = rp("n12", cam, twos(t), SWAY["n12"])
    img = haze(img, t, (1, .6, .35), .04, 12, 1)
    lt = _u8()
    sun = cam.scr([(640, 387)])[0]
    cv2.circle(lt, (int(sun[0]), int(sun[1])), int(40 + 6 * math.sin(t)), col8((1, .8, .5), .5), -1, cv2.LINE_AA)
    motes(lt, t, 7, 60, (1, .8, .5), (1, 3), (40, -6), .45)
    return add_light(img, light_from_u8(lt), 1.2, 1.4)


@shot(4.0)
def s_rooftop_heads(t, T):
    cam = Cam(lerp(560, 580, t / T), lerp(250, 240, t / T), lerp(820, 740, ease_io(t / T)))
    img = rp("n12", cam, twos(t), SWAY["n12"])
    return haze(img, t, (1, .6, .35), .04, 12, 2)


@shot(6.0)
def s_ren_push(t, T):
    p = ease_in(t / T) * .6 + (t / T) * .4
    cam = Cam(lerp(640, 637, p), lerp(380, 310, p), lerp(1280, 760, p))
    img = rp("n14", cam, twos(t), scaled("n14", 1 + 1.5 * t / T))
    lt = _u8()
    motes(lt, t, 9, 40, (1, .85, .5), (2, 6), (0, -10), .3)
    img = add_light(img, light_from_u8(lt), 1.5, 1.5)
    k = pulse(t, 4.6, .12, .5)
    if k > 0:
        lt = _u8()
        for e in cam.scr([(540, 300), (733, 300)]):
            cv2.line(lt, (int(e[0] - 70 * k), int(e[1])), (int(e[0] + 70 * k), int(e[1])), col8(WHITE, k), 2, cv2.LINE_AA)
            cv2.circle(lt, (int(e[0]), int(e[1])), 6, col8((1, .85, .5), k), -1, cv2.LINE_AA)
        img = add_light(img, light_from_u8(lt), 2, 2)
    return img


@shot(2.0)
def s_ren_eyes(t, T):
    cam = cam_with_shake(637, 300, lerp(500, 420, ease_out(t / T)), 0, t, 1.2, 9)
    img = rp("n14", cam, twos(t), scaled("n14", 2.5, 2))
    img = parallel_lines(img, t, 0.08, 24, (1, .9, .8), .2, seed=8, length=(300, 900))
    lt = _u8()
    for e in cam.scr([(540, 300), (733, 300)]):
        cv2.circle(lt, (int(e[0]), int(e[1])), 30, col8((1, .7, .25), .10 + .06 * math.sin(t * 20)), -1, cv2.LINE_AA)
    return add_light(img, light_from_u8(lt), 1.2, 1.4)


@shot(4.0)
def s_hana_flash(t, T):
    cam = Cam(lerp(640, 660, t / T), lerp(380, 370, t / T), lerp(1280, 1100, ease_io(t / T)))
    img = rp("n09", cam, twos(t), SWAY["n09"])
    soft = cv2.GaussianBlur(img, (0, 0), 6)
    img = img * .82 + soft * .25 + (1 - VIGNETTE) * .8
    lt = _u8()
    motes(lt, t, 12, 50, (1, 1, .9), (2, 5), (14, -16), .35)
    img = add_light(img, light_from_u8(lt))
    return flash(img, 1 - smooth(t / .5))


@shot(4.0)
def s_hana_smile(t, T):
    cam = Cam(lerp(735, 745, t / T), lerp(350, 345, t / T), lerp(720, 620, ease_io(t / T)))
    img = rp("n09", cam, twos(t), SWAY["n09"])
    soft = cv2.GaussianBlur(img, (0, 0), 6)
    img = img * .84 + soft * .22 + (1 - VIGNETTE) * .8
    lt = _u8()
    motes(lt, t, 13, 40, (1, 1, .85), (2, 6), (18, -12), .4)
    img = add_light(img, light_from_u8(lt))
    return flash(img, smooth((t - (T - .4)) / .4))


@shot(3.0)
def s_ren_back(t, T):
    cam = Cam(640, 360, 1180 - 40 * t)
    img = rp("n14", cam, twos(t), SWAY["n14"])
    k = pulse(t, 2.0, .05, .5)
    img = tint(img, (.6, 1.3, 1.4), k * .7)
    img = flash(img, k * .2, CYAN)
    return flash(img, 1 - smooth(t / .3))

# ---- ACT 2: crack + beast ---------------------------------------------------------


@shot(2.5)
def s_point(t, T):
    cam = cam_with_shake(lerp(900, 880, t / T), 230, 900, 0, t, 2 * smooth(t / T), 20)
    img = rp("n02", cam, twos(t), SWAY["n02"])
    img = tint(img, (.55, .65, 1.0), smooth(t / T) * .55)
    lt = _u8()
    p = cam.scr([(830, 110)])[0]
    k = smooth(t / T)
    cv2.circle(lt, (int(p[0]), int(p[1])), int(3 + 10 * k), col8(WHITE, .5 + .5 * k), -1, cv2.LINE_AA)
    cv2.line(lt, (int(p[0] - 220 * k), int(p[1])), (int(p[0] + 220 * k), int(p[1])), col8(CYAN, k), 2, cv2.LINE_AA)
    img = add_light(img, light_from_u8(lt), 2, 2)
    return flash(img, smooth((t - 2.2) / .3))


@shot(6.0)
def s_sky_cracks(t, T):
    cam = cam_with_shake(lerp(760, 680, ease_out(t / T)), lerp(260, 330, ease_out(t / T)), lerp(900, 1240, ease_out(t / T)), 0, t,
                         8 * pulse(t, 0, .05, .8) + 2, 22)
    img = rp("n01", cam, twos(t), SWAY["n01"])
    lt = _u8()
    CRK_SKY.draw(lt, cam, ease_out_expo(t / 2.5), CYAN, 0.8, .16, flicker=.3, t=t)
    SH_FALL.draw(lt, cam, t, smooth((t - .4) / 1.2) * .8)
    SH_FALL2.draw(lt, cam, t * .8, smooth((t - 1.0) / 1.2) * .6)
    c = cam.scr([(827, 127)])[0]
    cv2.circle(lt, (int(c[0]), int(c[1])), int(50 + 25 * math.sin(t * 9)), col8(WHITE, .6), -1, cv2.LINE_AA)
    img = add_light(img, light_from_u8(lt), 1.2, 1.2)
    img = zoom_blur(img, c[0], c[1], .06 * pulse(t, 0, .05, .6))
    img = flash(img, (1 - smooth(t / .5)) * .95)
    return chroma(img, .006 * pulse(t, 0, .05, 1))


@shot(3.5)
def s_city_rain(t, T):
    cam = cam_with_shake(lerp(940, 960, t / T), 560, 640, 0, t, 3, 20)
    img = rp("n01", cam, twos(t), SWAY["n01"])
    lt = _u8()
    SH_FALL.draw(lt, cam, t + 6)
    SH_FALL2.draw(lt, cam, t * .9 + 5)
    img = add_light(img, light_from_u8(lt), 1.1, 1.0)
    for k, tt in ((.25, .8), (.35, 2.4)):
        img = flash(img, pulse(t, tt, .03, .2) * k, CYAN)
    return img


@shot(2.0)
def s_heads_wind(t, T):
    cam = cam_with_shake(560, 250, 760, 0, t, 3, 14)
    img = rp("n12", cam, twos(t), scaled("n12", 3, 2.5))
    img = tint(img, (.45, .75, 1.1), .7)
    img = img + np.float32(CYAN) * .1 * (.5 + .5 * math.sin(t * 30))
    img = parallel_lines(img, t, 3.0, 40, (.8, 1, 1), .3, seed=6)
    lt = _u8()
    SH_FALL2.draw(lt, cam, t + 2)
    return add_light(img, light_from_u8(lt))


@shot(8.0)
def s_beast_reveal(t, T):
    p = ease_io(t / 6.0)
    cam = cam_with_shake(lerp(620, 680, p), lerp(560, 330, p), lerp(620, 1240, p), 0, t, 1.5 + 6 * pulse(t, 6.2, .05, .6), 16)
    img = rp("n13", cam, twos(t), SWAY["n13"])
    lt = _u8()
    r = np.random.default_rng(2)
    pts = np.stack([r.uniform(250, 1100, 80), r.uniform(60, 450, 80)], 1)
    for i, s in enumerate(cam.scr(pts)):
        k = max(0, math.sin(t * 2.5 + i * 1.7)) ** 12
        if k > .05:
            L = int(16 * k / cam.s)
            cv2.line(lt, (int(s[0] - L), int(s[1])), (int(s[0] + L), int(s[1])), col8(WHITE, k), 1, cv2.LINE_AA)
            cv2.line(lt, (int(s[0]), int(s[1] - L)), (int(s[0]), int(s[1] + L)), col8(WHITE, k), 1, cv2.LINE_AA)
    SH_FALL.draw(lt, cam, t + 10, .6)
    e = cam.scr([(1053, 213)])[0]
    ek = .3 + .7 * smooth((t - 5.5) / .6)
    cv2.circle(lt, (int(e[0]), int(e[1])), int(12 / cam.s * ek), col8(WHITE, ek), -1, cv2.LINE_AA)
    img = add_light(img, light_from_u8(lt), 1.4, 1.4)
    return flash(img, (.5 + .5 * math.sin(t * 37)) * .08 * pulse(t, 6.2, .05, .8), CYAN)


@shot(3.0)
def s_beast_roar(t, T):
    cam = cam_with_shake(1030, 240, lerp(440, 360, ease_out(t / T)), 0, t, 4 + 10 * pulse(t, .4, .05, 1.2), 34)
    x, y = cam.maps()
    if t > .4:
        x, y = shockwave(x, y, 1060, 260, (t - .4) * 900, 40, 25)
    img = cv2.remap(plate("n13"), x * 2, y * 2, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT).astype(np.float32) / 255
    lt = _u8()
    e = cam.scr([(1053, 213)])[0]
    cv2.circle(lt, (int(e[0]), int(e[1])), 40, col8(WHITE, 1), -1, cv2.LINE_AA)
    cv2.line(lt, (int(e[0] - 700), int(e[1])), (int(e[0] + 700), int(e[1])), col8(CYAN, .8), 3, cv2.LINE_AA)
    img = add_light(img, light_from_u8(lt), 2, 2)
    m = cam.scr([(1060, 290)])[0]
    img = zoom_blur(img, m[0], m[1], .12 * pulse(t, .4, .05, 1), 7)
    if int(t * 12) % 5 == 1 and t > .4:
        img = two_tone(img, dark=(0, .02, .05), light=(.6, 1, 1), th=.4)
    return chroma(img, .015 * pulse(t, .4, .05, 1))


@shot(3.0)
def s_beast_wide_roar(t, T):
    cam = cam_with_shake(660, 380, 1220, 0, t, 5 * (1 - t / T) + 1, 26)
    x, y = cam.maps()
    x, y = shockwave(x, y, 1060, 260, t * 700, 50, 18)
    img = cv2.remap(plate("n13"), x * 2, y * 2, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT).astype(np.float32) / 255
    lt = _u8()
    c = cam.scr([(1060, 260)])[0]
    cv2.ellipse(lt, (int(c[0]), int(c[1])), (int(t * 700 / cam.s), int(t * 700 / cam.s * .6)), 0, 0, 360,
                col8(CYAN, (1 - t / T) * .8), 3, cv2.LINE_AA)
    SH_FALL2.draw(lt, cam, t + 9)
    return add_light(img, light_from_u8(lt))


@shot(4.0)
def s_ren_resolve(t, T):
    cam = cam_with_shake(637, 310, lerp(800, 560, ease_in(t / T)), 0, t, 1.5, 12)
    img = rp("n14", cam, twos(t), scaled("n14", 3, 2.5))
    img = tint(img, (.6, .9, 1.15), .45)
    img = img + np.float32(CYAN) * .06 * (.5 + .5 * math.sin(t * 9))
    img = parallel_lines(img, t, -2.6, 30, (.8, 1, 1), .25, seed=14)
    lt = _u8()
    SH_FALL.draw(lt, cam, t + 4, .6)
    img = add_light(img, light_from_u8(lt))
    if t > 2.4:
        img = speed_lines(img, W / 2, H / 2 - 40, t, 70, (.3, .5), (1, 1, 1), .45 * smooth((t - 2.4) / .3), seed=15)
    return img


@shot(3.0)
def s_hana_ready(t, T):
    cam = cam_with_shake(lerp(640, 660, t / T), lerp(420, 400, t / T), lerp(900, 820, t / T), 0, t, 1, 10)
    img = rp("n03", cam, twos(t), SWAY["n03"])
    lt = _u8()
    k = smooth(t / T)
    c = cam.scr([(960, 60)])[0]
    cv2.circle(lt, (int(c[0]), int(c[1])), int(30 + 40 * k), col8(CYAN, .25 + .4 * k), -1, cv2.LINE_AA)
    motes(lt, t, 21, 40, GOLD, (1, 3), (0, -60), .5)
    return add_light(img, light_from_u8(lt), 1.4, 1.2)

# ---- ACT 3: fight ---------------------------------------------------------------------


@shot(5.0)
def s_ren_leap(t, T):
    p = t / T
    cams = [cam_with_shake(lerp(420, 640, ease_out(clamp01(p + d))), lerp(480, 340, ease_out(clamp01(p + d))),
                           lerp(700, 1200, ease_out(clamp01(p + d))), lerp(.06, -.02, ease_out(clamp01(p + d))), t + d, 3, 16)
            for d in (-.02, 0, .02)]
    img = render_mb("n11", cams, twos(t), SWAY["n11"])
    img = parallel_lines(img, t, -0.45, 50, (1, 1, 1), .35, seed=17, length=(300, 1100))
    lt = _u8()
    SH_DRIFT.draw(lt, cams[1], t * 3, .7)
    return add_light(img, light_from_u8(lt))


@shot(2.0)
def s_blade(t, T):
    cam = cam_with_shake(1020, 90, 560 - 60 * t, -.04, t, 2, 20)
    img = rp("n11", cam, twos(t), SWAY["n11"])
    lt = _u8()
    k = ease_out(t / 1.0)
    a, b = np.array([880., 80.]), np.array([1240., 0.])
    tip = a + (b - a) * k
    sa, sb = cam.scr([a, tip])
    cv2.line(lt, tuple(sa.astype(int)), tuple(sb.astype(int)), col8(CYAN, .8), 14, cv2.LINE_AA)
    cv2.line(lt, tuple(sa.astype(int)), tuple(sb.astype(int)), col8(WHITE, .9), 4, cv2.LINE_AA)
    cv2.circle(lt, tuple(sb.astype(int)), int(26 + 16 * math.sin(t * 30)), col8(WHITE, .9), -1, cv2.LINE_AA)
    img = add_light(img, light_from_u8(lt), 1.5, 1.5)
    return flash(img, pulse(t, 1.0, .03, .25) * .5)


@shot(6.0)
def s_hana_barrier(t, T):
    rot = .025 * math.sin(t * .6)
    cam = cam_with_shake(lerp(660, 700, t / T), lerp(380, 330, t / T), lerp(1200, 1000, ease_io(t / T)), rot, t, 1.5, 12)
    img = rp("n03", cam, twos(t), scaled("n03", 1.6, 1.5))
    lt = _u8()
    ribbons(lt, cam, twos(t), 960, 80, n=4, r0=40, r1=170 + 40 * smooth(t / 2), height=200, growth=ease_out(t / 1.5), alpha=.45)
    motes(lt, t, 22, 70, GOLD, (1, 3), (0, -90), .55)
    img = add_light(img, light_from_u8(lt), 1.2, 1.1)
    return img + np.float32(CYAN) * .04 * smooth(t / 2)


@shot(2.0)
def s_threads_burst(t, T):
    cam = cam_with_shake(960, 110, 560, 0, t, 3, 22)
    img = rp("n03", cam, twos(t), SWAY["n03"])
    lt = _u8()
    ribbons(lt, cam, twos(t) + 3, 960, 80, n=4, r0=40, r1=190, height=200, alpha=.45)
    r = np.random.default_rng(31)
    c = np.array([960, 60.])
    for i in range(16):
        a = r.uniform(-2.8, -.3)
        L = ease_out((t - .3 - i * .03) / .5) * 900
        if L <= 0: continue
        e = c + np.array([math.cos(a), math.sin(a)]) * L
        s0, s1 = cam.scr([c, e]).astype(int)
        cv2.line(lt, tuple(s0), tuple(s1), col8(GOLD if i % 2 else CYAN, 1), 4, cv2.LINE_AA)
    img = add_light(img, light_from_u8(lt), 1.6, 1.4)
    return flash(img, pulse(t, .3, .03, .3) * .5, GOLD)


@shot(4.0)
def s_bind_beast(t, T):
    cam = cam_with_shake(680, 330, 1150, 0, t, 2 + 4 * pulse(t, 2.6, .05, .8), 20)
    img = rp("n13", cam, twos(t), SWAY["n13"])
    lt = _u8()
    r = np.random.default_rng(41)
    for i in range(9):
        p0, p2 = np.array([180., r.uniform(120, 460)]), np.array([1180., r.uniform(80, 420)])
        p1 = np.array([680, r.uniform(0, 600)])
        curve = bezier(p0, p1, p2, 60)
        n = int(len(curve) * ease_out((t - i * .14) / 1.2))
        if n < 2: continue
        cv2.polylines(lt, [cam.scr(curve[:n]).astype(np.int32)], False, col8(GOLD if i % 2 else CYAN, 1), 3, cv2.LINE_AA)
    e = cam.scr([(1053, 213)])[0]
    cv2.circle(lt, (int(e[0]), int(e[1])), int(16 + 10 * pulse(t, 2.6, .05, .5)), col8(WHITE, 1), -1, cv2.LINE_AA)
    return add_light(img, light_from_u8(lt), 1.3, 1.3)


@shot(2.0)
def s_ren_charge(t, T):
    cams = [cam_with_shake(440, 230, lerp(900, 360, ease_in(clamp01((t + d) / T))), -.04, t, 4, 30) for d in (-.03, 0, .03)]
    img = render_mb("n11", cams, twos(t), SWAY["n11"])
    img = speed_lines(img, W / 2, H / 2, t, 110, (.22, .45), (1, 1, 1), .7, seed=19, thick=(2, 6))
    return chroma(img, .01 * t / T)


shot(1.0)(F.s_ma)


@shot(6.0)
def s_clash(t, T):
    # 0-.25 white | .25-1 two-tone stutter | 1-3 impact n05 | 3-4 slow push | 4-6 second hit n06
    if t < .25:
        return blank() + 1
    second = t >= 4
    key, (cx, cy) = ("n06", (393, 473)) if second else ("n05", (330, 360))
    amp = 16 * pulse(t, .25, .02, 1.0) + 18 * pulse(t, 4.0, .02, 1.2) + 2
    if second:
        w, ccx, ccy = 1280 - 200 * ease_out((t - 4) / 2), 600, 380
    elif t < 3:
        w, ccx, ccy = 1280, 640, 360
    else:
        q = ease_io(t - 3)
        w, ccx, ccy = lerp(1280, 560, q), lerp(640, cx, q), lerp(360, cy, q)
    cam = cam_with_shake(ccx, ccy, w, 0, t, amp, 32)
    x, y = cam.maps()
    if second:
        x, y = shockwave(x, y, cx, cy, (t - 4) * 1200, 50, 30)
    img = cv2.remap(plate(key), x * 2, y * 2, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT).astype(np.float32) / 255
    sc = cam.scr([(cx, cy)])[0]
    img = speed_lines(img, sc[0], sc[1], t, 100, (.14, .34), (0, 0, 0), .55, seed=29)
    lt = _u8()
    tb = t - .25 if not second else t - 4
    SH_BURST.draw(lt, cam, tb * (0.25 if 3 < t < 4 else 1), .9, CYAN, origin=np.array([cx, cy]), burst=1.2)
    cv2.circle(lt, (int(sc[0]), int(sc[1])), int(70 + 60 * pulse(t, 4, .03, .4)), col8(WHITE, .9), -1, cv2.LINE_AA)
    img = add_light(img, light_from_u8(lt), 1.3, 1.3)
    img = zoom_blur(img, sc[0], sc[1], .1 * pulse(t, .25, .02, .5) + .14 * pulse(t, 4, .02, .6), 7)
    if .25 <= t < 1.0 or 4.0 <= t < 4.6:
        mode = int(t * 12) % 3
        if mode == 0: img = two_tone(img, invert=True, th=.55)
        elif mode == 1: img = two_tone(img, dark=(.03, 0, 0), light=(.95, .1, .1), th=.5)
    img = flash(img, pulse(t, 4.0, .02, .2))
    return chroma(img, .02 * pulse(t, .25, .02, .8) + .025 * pulse(t, 4, .02, .8))


@shot(3.0)
def s_beast_fracture(t, T):
    cam = cam_with_shake(680, 320, 1050, 0, t, 6 + 8 * pulse(t, 2.2, .03, .4), 28)
    img = rp("n13", cam, twos(t), SWAY["n13"])
    lt = _u8()
    CRK_BEAST.draw(lt, cam, ease_out(t / 2.0), WHITE, 2.4, 1.0, flicker=.3, t=t)
    SH_FALL2.draw(lt, cam, t + 3)
    img = add_light(img, light_from_u8(lt), 1.6, 1.6)
    return flash(img, smooth((t - 2.3) / .5))


@shot(1.0)
def s_hana_shout(t, T):
    cam = cam_with_shake(620, 440, 720, 0, t, 3, 22)
    img = rp("n03", cam, twos(t), scaled("n03", 2, 2))
    img = flash(img, 1 - smooth(t / .3))
    return parallel_lines(img, t, -1.57, 50, (1, .9, .6), .4, seed=31)


@shot(6.0)
def s_mirror_dive(t, T):
    p = ease_io(t / T)
    cams = [cam_with_shake(lerp(640, 620, p), lerp(250, 420, ease_io((t + d) / T)), lerp(820, 1150, p), 0, t,
                           1.5 + 6 * pulse(t, 2.5, .05, .6), 18) for d in (-.03, 0, .03)]
    tr = max(0, t - 2.5)

    def warp(x, y):
        below = (y > 480).astype(np.float32)
        x = x + below * 1.4 * np.sin(y * .35 + t * 6)
        if tr > 0:
            dx, dy = x - 613, (y - 480) * 3.2
            d = np.sqrt(dx * dx + dy * dy)
            env = np.exp(-((d - tr * 260) / 160) ** 2) * math.exp(-tr * .5)
            x = x + env * 6 * np.sin(d * .08 - tr * 14)
            y = y + env * 2 * np.sin(d * .08 - tr * 14)
        return x, y
    img = render_mb("n04", cams, twos(t), SWAY["n04"], warp)
    lt = _u8()
    cam = cams[1]
    c = cam.scr([(613, 480)])[0]
    for i in range(5):
        rr = tr * 260 - i * 70
        if rr > 0:
            cv2.ellipse(lt, (int(c[0]), int(c[1])), (int(rr / cam.s), int(rr / cam.s / 3.2)), 0, 0, 360,
                        col8(CYAN, math.exp(-tr * .7) * (1 - i * .15)), 2, cv2.LINE_AA)
    SH_DRIFT.draw(lt, cam, t, .7)
    img = add_light(img, light_from_u8(lt), 1.3, 1.2)
    return flash(img, pulse(t, 2.5, .04, .4) * .6)


@shot(2.0)
def s_mirror_contact(t, T):
    cam = cam_with_shake(613, 470, lerp(560, 320, ease_in(t / T)), 0, t, 2, 20)
    x, y = cam.maps()
    dx, dy = x - 613, (y - 480) * 3.2
    d = np.sqrt(dx * dx + dy * dy)
    x = x + 7 * np.sin(d * .1 - t * 18) * np.exp(-d / 300)
    img = cv2.remap(plate("n04"), x * 2, y * 2, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT).astype(np.float32) / 255
    lt = _u8()
    c = cam.scr([(613, 480)])[0]
    for i in range(8):
        rr = (t * 300 + i * 60) % 500
        cv2.ellipse(lt, (int(c[0]), int(c[1])), (int(rr / cam.s), int(rr / cam.s / 3.2)), 0, 0, 360, col8(CYAN, 1 - rr / 500), 2, cv2.LINE_AA)
    img = add_light(img, light_from_u8(lt), 1.5, 1.5)
    return flash(img, smooth((t - 1.2) / .8))


@shot(4.0)
def s_shatter(t, T):
    cam = cam_with_shake(680, 330, 1150, 0, t, 4 * (1 - t / T), 20)
    base = rp("n13", cam)
    bg = blank() + np.float32([.02, .05, .09]) + (np.float32([.05, .12, .16]) * (1 - _yy / H)[..., None])
    hide = smooth((t - .15) / .5)
    img = base * (1 - hide) + bg * hide
    lt = _u8()
    SH_BURST.draw(lt, cam, t * .6, 1 - smooth((t - 2.5) / 1.5), CYAN, origin=np.array([700, 300]), burst=1.0)
    SH_SNOW.draw(lt, cam, t, smooth((t - 1) / 2))
    img = add_light(img, light_from_u8(lt), 1.4, 1.4)
    return flash(img, 1 - smooth(t / .9))


MEM = [("n14", 637, 300, 300), ("n09", 745, 345, 360), ("n12", 560, 250, 560), ("n07", 560, 330, 620), ("n03", 620, 440, 380)]


@shot(4.0)
def s_memories(t, T):
    img = blank() + np.float32([.02, .04, .07])
    lt = _u8()
    SH_SNOW.draw(lt, Cam(640, 360, 1280), t + 4, .5)
    img = add_light(img, light_from_u8(lt))
    for i, (k, cx, cy, w) in enumerate(MEM):
        tt = t - i * .35
        if tt < 0: continue
        a = smooth(tt / .6) * smooth((T - t) / .6)
        ang = tt * .5 + i * 1.3
        sx = W * (.18 + .16 * i) + 30 * math.sin(tt)
        sy = H * (.5 + .22 * math.sin(i * 2.1)) - tt * 25
        R = 180 + 30 * (i % 2)
        tri = np.float32([[sx + R * math.cos(ang + j * 2.09), sy + R * .85 * math.sin(ang + j * 2.09)] for j in range(3)])
        src = np.float32([[cx - w / 2, cy - w / 2], [cx + w / 2, cy - w / 2], [cx, cy + w / 2]]) * 2
        tex = cv2.warpAffine(plate(k), cv2.getAffineTransform(src, tri), (W, H)).astype(np.float32) / 255
        m = np.zeros((H, W), np.uint8)
        cv2.fillConvexPoly(m, tri.astype(np.int32), 255, cv2.LINE_AA)
        mf = (m.astype(np.float32) / 255 * a)[..., None]
        img = img * (1 - mf) + (tex * 1.05 + np.float32(CYAN) * .06) * mf
        edge = _u8()
        cv2.polylines(edge, [tri.astype(np.int32)], True, col8(WHITE, a), 2, cv2.LINE_AA)
        img = add_light(img, light_from_u8(edge), .8, .6)
    return img

# ---- ACT 4: aftermath --------------------------------------------------------------------


@shot(9.0)
def s_shard_snow(t, T):
    cam = Cam(640, lerp(380, 400, t / T), lerp(1280, 1060, ease_io(t / T)))
    img = rp("n08", cam, twos(t), SWAY["n08"])
    lt = _u8()
    SH_SNOW.draw(lt, cam, t, .7)
    img = add_light(img, light_from_u8(lt), 1.0, 1.0)
    fg = _u8()
    SH_SNOW_FG.draw(fg, Cam(640, 360, 1280), t)
    img = img + cv2.GaussianBlur(light_from_u8(fg), (0, 0), 7) * 1.8
    return img * smooth(t / 1.0)


@shot(5.0)
def s_snow_close(t, T):
    cam = Cam(lerp(640, 650, t / T), lerp(300, 290, t / T), lerp(820, 740, t / T))
    img = rp("n08", cam, twos(t), SWAY["n08"])
    lt = _u8()
    SH_SNOW.draw(lt, cam, t + 9, .7)
    img = add_light(img, light_from_u8(lt))
    fg = _u8()
    SH_SNOW_FG.draw(fg, Cam(640, 360, 1280), t + 9)
    img = img + cv2.GaussianBlur(light_from_u8(fg), (0, 0), 9) * 2.0
    return flash(img, smooth((t - 3.6) / 1.4))


@shot(13.5)
def s_morning(t, T):
    p = ease_io(t / T)
    cam = Cam(lerp(560, 640, p), lerp(380, 360, p), lerp(820, 1280, p))
    img = rp("n07", cam, twos(t), SWAY["n07"])
    img = haze(img, t, (1, 1, 1), .03, 6, 4)
    lt = _u8()
    sun = cam.scr([(1240, 53)])[0]
    cv2.circle(lt, (int(sun[0]), int(sun[1])), int(70 / cam.s), col8((1, .95, .85), .5), -1, cv2.LINE_AA)
    motes(lt, t, 31, 30, (1, 1, .9), (1, 3), (10, -8), .35)
    img = add_light(img, light_from_u8(lt), 1.1, 1.3)
    hk = pulse(t, 10.2, .1, .6)
    if hk > 0:
        g = _u8()
        q = cam.scr([(960, 150)])[0].astype(int)
        cv2.line(g, (q[0] - 40, q[1]), (q[0] + 40, q[1]), col8(CYAN, hk), 2, cv2.LINE_AA)
        cv2.line(g, (q[0], q[1] - 40), (q[0], q[1] + 40), col8(CYAN, hk), 2, cv2.LINE_AA)
        img = add_light(img, light_from_u8(g), 1.5, 1.5)
    img = flash(img, 1 - smooth(t / 1.2))
    return img * smooth((T - t) / .8)


shot(12.0)(F.s_end)

# same names and durations as v1, so the score and subtitles stay in sync
assert [(d, n) for d, _, n in SHOTS] == [(d, n) for d, _, n in F.SHOTS], "timeline drifted from v1"
F.SHOTS[:] = SHOTS


if __name__ == "__main__":
    if sys.argv[1] == "prep":
        prep()
    elif sys.argv[1] == "render":
        F.render(int(sys.argv[2]), int(sys.argv[3]), sys.argv[4])
    elif sys.argv[1] == "still":
        cv2.imwrite(sys.argv[3], cv2.cvtColor(F.frame(int(float(sys.argv[2]) * FPS)), cv2.COLOR_RGB2BGR))
