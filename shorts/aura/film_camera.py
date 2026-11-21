# Camera for film.py (exec'd inside it): one rig, hard cuts, hand-held first person where the narrator is the camera.
cam, tgt, cd = C.make_camera()
focus = bpy.data.objects.new("focus", None); scn.collection.objects.link(focus); cd.dof.focus_object = focus
prefs.keyframe_new_interpolation_type = "LINEAR"
def key(f, loc, look, foc, lens, fstop):
    cam.location = loc; cam.keyframe_insert("location", frame=f)
    tgt.location = look; tgt.keyframe_insert("location", frame=f)
    focus.location = foc; focus.keyframe_insert("location", frame=f)
    cd.lens = lens; cd.keyframe_insert("lens", frame=f)
    cd.dof.aperture_fstop = fstop; cd.dof.keyframe_insert("aperture_fstop", frame=f)
head = V((0, 0, 1.72))
def flat(p): return V((p.x, p.y, 0))
def hs(f): return flat(hero_s_at(f)[0])
def ha(f): return flat(hero_a_at(min(f, TURN))[0])
def hp_(f): return flat(hero_p_at(f)[0]) + V((0.62, 0, 0))     # centre of the walking pair

def shot(sid, start, end, a=None, b=None):
    """Key a shot at its first and last frame: start/end(f) -> (cam, look, focus, lens, fstop)."""
    a = a or fr(sid); b = b or fr(sid, 1)
    key(a, *start(a)); key(b, *end(b))
def every(sid, fn, a=None, b=None):
    """Key every frame of a shot (hand-held / tracking moves)."""
    for f in range((a or fr(sid)), (b or fr(sid, 1)) + 1):
        key(f, *fn(f))
import cine_camera as CC
SMOOTH = os.environ.get("CAM_SMOOTH", "1") != "0"         # CAM_SMOOTH=0: the previous camera (for comparisons)
def every_smooth(sid, fn, sigma, a=None, b=None):
    """Evaluate a shot per frame, smooth camera / look / focus paths (zero-phase, ends kept), key every frame."""
    a = a or fr(sid); b = b or fr(sid, 1); F = list(range(a, b + 1)); S = [fn(f) for f in F]
    C_ = CC.smooth([x[0] for x in S], sigma); L_ = CC.smooth([x[1] for x in S], sigma); P_ = CC.smooth([x[2] for x in S], sigma)
    for i, f in enumerate(F): key(f, C_[i], L_[i], P_[i], S[i][3], S[i][4])
def track(of, cam_off, look_off, lens, fstop, foc=head):
    return lambda f: (of(f) + V(cam_off), of(f) + V(look_off), of(f) + foc, lens, fstop)
def fixed(cam_p, look_p, foc_p, lens, fstop):
    return lambda f: (V(cam_p), V(look_p), V(foc_p), lens, fstop)

def shake(f, walk=1.0, amp=1.0):
    """Hand-held: step bob + sway while walking, small jitter always. Returns (cam offset, look offset)."""
    u = 2 * math.pi * f / 15.0
    c = V((0.018 * walk * math.sin(u / 2) + amp * 0.006 * (math.sin(f * 0.71) + 0.6 * math.sin(f * 1.93 + 1)), 0,
           0.02 * walk * math.cos(u) + amp * 0.005 * (math.sin(f * 0.83 + 2) + 0.6 * math.sin(f * 2.11))))
    l = V((amp * (0.05 * math.sin(f * 0.37 + 0.5) + 0.025 * math.sin(f * 1.31)), 0,
           amp * (0.04 * math.sin(f * 0.43 + 2) + 0.02 * math.sin(f * 1.7)) + 0.012 * walk * math.cos(u + 0.6)))
    return c, l

# --- the street
shot("hook_wide", track(hs, (1.9, -17, 1.5), (-0.4, 10, 4.2), 36, 4.0), track(hs, (1.5, -12.5, 1.42), (-0.2, 8, 3.0), 38, 3.2))   # longer lens: he reads clearly in the first shot
shot("hook_feet", track(hs, (0.85, -1.25, 0.14), (0, 0, 0.13), 32, 2.2, V((0, 0, 0.1))),
     track(hs, (0.75, -1.1, 0.15), (0, 0, 0.14), 32, 2.2, V((0, 0, 0.1))))           # dry loafers, splashes all round
# "They called him Aura Monster": push in from his face to an extreme close-up of one eye (black sclera, white iris),
# locked to the eye itself so the walk's head bob never shakes the frame
_pb = hero_s.pose.bones["head"]
_eyes = sorted([o for o in hero_s.children_recursive if o.name.startswith("eye_")], key=lambda o: o.name)
scn.frame_set(1)
_rest = {o.name: _pb.bone.matrix_local.inverted() @ (hero_s.matrix_world.inverted() @ o.matrix_world.translation) for o in _eyes}
def eye_at(f, which):
    scn.frame_set(f)
    return hero_s.matrix_world @ _pb.matrix @ _rest[which]
_EL = next(o.name for o in _eyes if o.name.startswith("eye_l"))
_ER = next(o.name for o in _eyes if o.name.startswith("eye_r"))
def eye_push(f):
    a_, b_ = fr("name_close"), fr("name_close", 1)
    u = min(1.0, max(0.0, (f - a_) / max(1, b_ - a_ - 6))); u = u * u * (3 - 2 * u)          # ease in and out, then hold
    el = eye_at(f, _EL); mid = (el + eye_at(f, _ER)) / 2
    face = mid + V((0, 0, -0.035))                                      # ends on a close-up of the whole face
    tgt_p = mid.lerp(face, u)
    cam_p = (mid + V((0.55, -1.3, 0.0))).lerp(face + V((0.17, -0.64, 0.02)), u)
    foc = el + V((0, -0.012, 0))                                        # the near eye stays sharp
    return cam_p, tgt_p, foc, 55 + 5 * u, 2.0 + 0.8 * u
every("name_close", eye_push)
shot("name_med", track(hs, (1.7, -4.6, 1.2), (0, 0, 1.35), 30, 2.8), track(hs, (1.4, -4.2, 1.25), (0, 0, 1.4), 30, 2.8))
shot("shop", fixed((4.6, 51.5, 1.45), (6.9, 53.3, 1.62), (6.9, 53.0, 1.62), 45, 2.0),
     fixed((4.85, 51.75, 1.47), (6.9, 53.3, 1.62), (6.9, 53.0, 1.62), 45, 2.0))
shot("cop", fixed((-3.25, 47.5, 1.35), (-5.5, 49.2, 1.72), (-5.5, 49.0, 1.7), 45, 2.0),
     fixed((-3.5, 47.8, 1.38), (-5.5, 49.2, 1.72), (-5.5, 49.0, 1.7), 45, 2.0))
shot("kids", fixed((3.2, 42.7, 1.0), (5.75, 44.9, 1.15), (5.6, 44.7, 1.15), 32, 2.2),
     fixed((3.45, 42.95, 1.02), (5.75, 44.9, 1.15), (5.6, 44.7, 1.15), 32, 2.2))

# --- first person: following him off the street into the lantern alley (umbrella rim at the top of frame)
LAG = 3.4 / spd * 30.0
def pov_follow(f):
    c, l = shake(f)
    p_cam = flat(hero_s_at(f - LAG)[0]); p_h = hs(f)
    fwd = (p_h - p_cam).normalized() if (p_h - p_cam).length > 1e-3 else V((0, -1, 0))
    side = V((-fwd.y, fwd.x, 0))
    return (p_cam + side * (0.3 + c.x) + V((0, 0, 1.62 + c.z)), p_h + side * l.x + V((0, 0, 1.3 + l.z)), p_h + head, 24, 4.0)
def pov_follow_v2(f):
    c, l = CC.soft_handheld(f)
    p_cam = flat(hero_s_at(f - LAG)[0]); p_h = hs(f)
    fwd = (p_h - p_cam).normalized() if (p_h - p_cam).length > 1e-3 else V((0, -1, 0))
    side = V((-fwd.y, fwd.x, 0))
    return (p_cam + side * (0.3 + c.x) + V((0, 0, 1.62 + c.z)), p_h + side * l.x + V((0, 0, 1.3 + l.z)), p_h + head, 24, 4.0)
if SMOOTH: every_smooth("follow", pov_follow_v2, 6)       # rounds the corner into the alley, no direction snap
else: every("follow", pov_follow)
STOP_POV = fr("alley_pov") + 16                         # "Then I saw it": he stops dead; the storm slows
def pov_alley(f):
    walk = max(0.0, 1 - (f - fr("alley_pov")) / 16.0)
    c, l = shake(f, walk=walk, amp=0.8)
    xc = ha(min(f, STOP_POV)).x + 3.6
    p = V((xc, AL_Y + 0.25, 0))
    return (p + V((c.x * 0.3, c.x, 1.62 + c.z)), ha(f) + V((0, l.x, 1.35 + l.z)), ha(f) + head, 26, 4.0)
def pov_alley_v2(f):
    a_ = fr("alley_pov"); walk = 1 - CC.minjerk((f - a_) / 16.0)
    c, l = CC.soft_handheld(f, walk=walk, amp=0.8)
    xc = ha(min(f, STOP_POV)).x + 3.6
    p = V((xc, AL_Y + 0.25, 0))
    return (p + V((c.x * 0.3, c.x, 1.62 + c.z)), ha(f) + V((0, l.x, 1.35 + l.z)), ha(f) + head, 26, 4.0)
if SMOOTH: every_smooth("alley_pov", pov_alley_v2, 6)     # he stops dead: the camera decelerates over ~0.4 s, not 1 frame
else: every("alley_pov", pov_alley)

# --- the reveal, in slow motion: he is weaving between the drops
def reveal_low_v2(f):      # low-angle hero shot: a slow orbit round him (continuous angular speed) and a gentle push-in
    u = (f - fr("reveal_low")) / max(1, fr("reveal_low", 1) - fr("reveal_low"))
    off = CC.arc(V((-2.7, -0.55, 0.32)) * (1 - 0.12 * u), -16 * u)
    return (ha(f) + off, ha(f) + V((0, 0, 1.75)), ha(f) + head, 20, 5.6)
def reveal_close_v2(f):    # the close shot keeps creeping in, with a slight arc, as he weaves through the slowed drops
    u = (f - fr("reveal_close")) / max(1, fr("reveal_close", 1) - fr("reveal_close"))
    off = CC.arc(V((-0.55, -1.45, 1.6)), 7 * u) * 1.0; off = V((off.x, off.y, 0)) * (1 - 0.14 * CC.minjerk(u)) + V((0, 0, 1.6))
    return (ha(f) + off, ha(f) + V((-0.15, 0, 1.55)), ha(f) + V((0, 0, 1.6)), 45, 2.8)
if SMOOTH:
    every_smooth("reveal_low", reveal_low_v2, 4); every_smooth("reveal_close", reveal_close_v2, 4)
else:
    every("reveal_low", lambda f: (ha(f) + V((-2.7 + 0.004 * (f - fr("reveal_low")), -0.55, 0.32)), ha(f) + V((0, 0, 1.75)),
                                   ha(f) + head, 20, 5.6))
    every("reveal_close", lambda f: (ha(f) + V((-0.55, -1.45, 1.6)), ha(f) + V((-0.15, 0, 1.55)), ha(f) + V((0, 0, 1.6)), 45, 2.8))

# --- "He turned. You'll catch a cold, kid." (first person, standing still, the umbrella rim above)
def pov_turn(f):
    c, l = shake(f, walk=0.0, amp=0.7)
    return (STOP + V((3.2, 0.12, 1.6)) + c, STOP + V((0, l.x, 1.62 + l.z)), STOP + V((0, 0, 1.7)), 38, 2.8)
def pov_turn_v2(f):
    c, l = CC.soft_handheld(f, walk=0.0, amp=0.7)
    return (STOP + V((3.2, 0.12, 1.6)) + c, STOP + V((0, l.x, 1.62 + l.z)), STOP + V((0, 0, 1.7)), 38, 2.8)
if SMOOTH: every_smooth("turn", pov_turn_v2, 3)
else: every("turn", pov_turn)
mid = (STOP + NARR_T) / 2
# two-shot down the alley: the kid (umbrella) near and right, the hero beyond him, facing each other
shot("teach", fixed(mid + V((2.9, -1.55, 1.3)), mid + V((-0.25, 0, 1.5)), mid + V((0, 0, 1.55)), 24, 2.8),
     fixed(mid + V((2.6, -1.4, 1.32)), mid + V((-0.25, 0, 1.52)), mid + V((0, 0, 1.55)), 24, 2.8))

# --- training: the rooftop, the second alley, then a hundred nights in three cuts
rmid = (RT + RN) / 2
shot("train_roof", fixed(rmid + V((2.2, -3.6, 0.9)), rmid + V((0, 0.8, 1.45)), rmid + V((0, 0, 1.4)), 24, 4.0),
     fixed(rmid + V((1.9, -3.1, 0.95)), rmid + V((0, 0.8, 1.45)), rmid + V((0, 0, 1.4)), 24, 4.0))
shot("train_umb", fixed(UN + V((-2.2, -1.25, 1.35)), UN + V((0.5, 0.1, 1.42)), UN + V((0, 0, 1.45)), 40, 2.0),
     fixed(UN + V((-1.95, -1.1, 1.36)), UN + V((0.5, 0.1, 1.42)), UN + V((0, 0, 1.45)), 40, 2.0))
def mont(base, cam_off, look_off, lens, fstop):
    def fn(f):
        c, l = (CC.soft_handheld(f, walk=0.0, amp=0.9) if SMOOTH else shake(f, walk=0.0, amp=0.9))
        return (base + V(cam_off) + c, base + V(look_off) + V((l.x, 0, l.z)), base + V((0, 0, 1.4)), lens, fstop)
    return fn
every("train_mont", mont(RN, (-1.5, -1.7, 1.35), (0, 0, 1.3), 32, 2.8), *MONT[0])
every("train_mont", mont(UN, (1.3, -1.5, 0.55), (0, 0, 1.45), 26, 2.8), *MONT[1])
every("train_mont", mont(RN, (0.9, -1.8, 1.45), (0, 0, 1.25), 38, 2.4), *MONT[2])
shot("close", fixed(CLOSE_P + V((0.55, -2.3, 0.5)), CLOSE_P + V((0, 0, 1.8)), CLOSE_P + V((0, 0, 1.6)), 28, 2.8),
     fixed(CLOSE_P + V((0.45, -2.0, 0.55)), CLOSE_P + V((0, 0, 1.75)), CLOSE_P + V((0, 0, 1.6)), 28, 2.8))

# --- reference camera language (the user's "In this world..." Shorts): the camera never sits still - steady push-ins,
# slow orbits, punch-ins that settle on the face. Only for shots from "teach" on (the earlier shots are kept as rendered).
def push(sid, cam0, cam1, look0, look1, foc, lens, fstop, a=None, b=None, prof=lambda t: t, hand=0.0):
    a = a or fr(sid); b = b or fr(sid, 1)
    def fn(f):
        k = prof((f - a) / max(1, b - a)); c, l = CC.soft_handheld(f, walk=0.0, amp=hand) if hand else (V((0, 0, 0)), V((0, 0, 0)))
        return (V(cam0).lerp(V(cam1), k) + c, V(look0).lerp(V(look1), k) + V((l.x, 0, l.z)), V(foc), lens, fstop)
    every_smooth(sid, fn, 2, a, b)
def orbit(sid, centre, off, deg, look, foc, lens, fstop, pushk=0.0):
    a, b = fr(sid), fr(sid, 1)
    def fn(f):
        u = (f - a) / max(1, b - a); o = CC.arc(V(off), deg * u); o = V((o.x, o.y, 0)) * (1 - pushk * u) + V((0, 0, o.z))
        return (V(centre) + o, V(look), V(foc), lens, fstop)
    every_smooth(sid, fn, 2)
quad_out = lambda t: 1 - (1 - t) ** 2                     # starts moving at the cut, settles without a dead stop
if SMOOTH:
    # "Teach me": a steady push-in over the kid's shoulder toward the hero
    push("teach", mid + V((2.9, -1.55, 1.3)), mid + V((2.05, -1.1, 1.38)), mid + V((-0.25, 0, 1.5)), mid + V((-0.3, 0, 1.53)),
         mid + V((0, 0, 1.55)), 24, 2.8)
    # the rooftop: a slow orbit round the pair, constant angular speed
    orbit("train_roof", rmid, (2.2, -3.6, 0.9), 18, rmid + V((0, 0.8, 1.45)), rmid + V((0, 0, 1.4)), 24, 4.0, pushk=0.08)
    # the second alley: push in on the kid under the umbrella
    push("train_umb", UN + V((-2.2, -1.25, 1.35)), UN + V((-1.55, -0.88, 1.38)), UN + V((0.5, 0.1, 1.42)), UN + V((0.45, 0.08, 1.43)),
         UN + V((0, 0, 1.45)), 40, 2.0, prof=quad_out)
    # a hundred nights: each cut punches in and settles (handheld kept, low frequency only)
    for (base, co, lo, lens, fs), (a_, b_) in zip(((RN, (-1.5, -1.7, 1.35), (0, 0, 1.3), 32, 2.8), (UN, (1.3, -1.5, 0.55), (0, 0, 1.45), 26, 2.8),
                                                    (RN, (0.9, -1.8, 1.45), (0, 0, 1.25), 38, 2.4)), MONT):
        c0 = V(co); c1 = V((c0.x * 0.72, c0.y * 0.72, c0.z))
        push("train_mont", base + c0, base + c1, base + V(lo), base + V(lo), base + V((0, 0, 1.4)), lens, fs, a_, b_, quad_out, hand=0.9)
    # "Then one night, I closed it.": push in to his face as the umbrella closes
    push("close", CLOSE_P + V((0.55, -2.3, 0.5)), CLOSE_P + V((0.38, -1.45, 0.78)), CLOSE_P + V((0, 0, 1.8)), CLOSE_P + V((0, 0, 1.72)),
         CLOSE_P + V((0, 0, 1.6)), 28, 2.8, prof=quad_out)

# --- the payoff: two of them, dry, walking up the street
def payoff_two_v2(f):
    a_, b_ = fr("payoff_two"), fr("payoff_two", 1); u = (f - a_) / max(1, b_ - a_)
    o = CC.arc(V((0.25, -3.7, 1.15)).lerp(V((0.2, -3.3, 1.2)), u), -12 * u)
    return (hp_(f) + o, hp_(f) + V((0, 0, 1.4 + 0.05 * u)), hp_(f) + head, 30, 2.8)
if SMOOTH: every_smooth("payoff_two", payoff_two_v2, 2)
else: shot("payoff_two", track(hp_, (0.25, -3.7, 1.15), (0, 0, 1.4), 30, 2.8), track(hp_, (0.2, -3.3, 1.2), (0, 0, 1.45), 30, 2.8))
def payoff_wide_v2(f):     # the crane rises and settles on the last frame (ease-out), instead of stopping at full speed
    a_, b_ = fr("payoff_wide"), fr("payoff_wide", 1); t_ = (f - a_) / max(1, b_ - a_); k = 1 - (1 - t_) ** 2   # constant gentle deceleration
    co = V((0.4, 4.0, 1.4)).lerp(V((0.4, 7.5, 6.0)), k); lo = V((0, -9, 1.7)).lerp(V((0, -9, 1.4)), k)
    return (hp_(f) + co, hp_(f) + lo, hp_(f) + head, 26 - 2 * k, 3.5 + 0.5 * k)
if SMOOTH: every_smooth("payoff_wide", payoff_wide_v2, 2)
else: shot("payoff_wide", track(hp_, (0.4, 4.0, 1.4), (0, -9, 1.7), 26, 3.5), track(hp_, (0.4, 7.5, 6.0), (0, -9, 1.4), 24, 4.0))

for idb in (cam, tgt, focus, cd, cd.dof):
    ch.set_interp(idb, "LINEAR")

# the umbrella over the narrator's head in the first-person shots: its rim hangs across the top of frame
def pov_umbrella():
    bm_ = bmesh.new(); R = 0.55; ribs = 10
    apex = bm_.verts.new((0, 0.07, 0))
    rim = [bm_.verts.new((R * math.cos(2 * math.pi * i / ribs), -0.2, R * math.sin(2 * math.pi * i / ribs))) for i in range(ribs)]
    mid_ = [bm_.verts.new((0.8 * R * math.cos(2 * math.pi * (i + .5) / ribs), -0.12, 0.8 * R * math.sin(2 * math.pi * (i + .5) / ribs)))
            for i in range(ribs)]                                        # scalloped edge between the ribs
    for i in range(ribs):
        bm_.faces.new((apex, rim[i], mid_[i])); bm_.faces.new((apex, mid_[i], rim[(i + 1) % ribs]))
        bm_.faces.new((mid_[i], rim[i], rim[(i + 1) % ribs]))
    me = bpy.data.meshes.new("pov_umbrella"); bm_.to_mesh(me); bm_.free()
    ob = bpy.data.objects.new("pov_umbrella", me); C.FX.objects.link(ob)
    me.materials.append(ch.cel("#34405e", "#1a2134", rim="#9fc4ff", rim_amt=0.9, name="pov_umbrella"))
    sol = ob.modifiers.new("ink", "SOLIDIFY"); sol.thickness = 0.006
    ob.parent = cam; ob.location = (0.05, 0.55, -0.05); ob.rotation_euler = (math.radians(-10), 0, 0)   # rim: top ~15% of frame
    return ob
pov_umb = pov_umbrella()
visible(pov_umb, [(fr("follow"), fr("alley_pov", 1)), (fr("turn"), fr("turn", 1))])

# realistic look: a soft key that travels with the camera (like a bounce card), so faces always read
if ch.REAL:
    kl = bpy.data.lights.new("cam_key", "AREA"); kl.shape = "DISK"; kl.size = 1.6; kl.energy = 380
    kl.color = (1.0, 0.93, 0.86)
    ko = bpy.data.objects.new("cam_key", kl); scn.collection.objects.link(ko)
    ko.parent = cam; ko.location = (0.9, 0.6, 0.3); ko.rotation_euler = (math.radians(12), math.radians(20), 0)
    fl = bpy.data.lights.new("cam_fill", "AREA"); fl.size = 2.5; fl.energy = 120; fl.color = (0.75, 0.82, 1.0)
    fo = bpy.data.objects.new("cam_fill", fl); scn.collection.objects.link(fo)
    fo.parent = cam; fo.location = (-1.2, -0.3, 0.2); fo.rotation_euler = (0, math.radians(-25), 0)
    # same exposure on the faces in every shot: scale the key/fill with the camera-to-subject distance
    for sid in [b["id"] for b in BEATS["shots"]]:
        f0 = fr(sid); scn.frame_set(f0)
        d = (cam.matrix_world.translation - focus.matrix_world.translation).length
        k = max(0.12, min(1.6, (d / 3.6) ** 2))
        kl.energy = 380 * k; kl.keyframe_insert("energy", frame=f0)
        fl.energy = 120 * k; fl.keyframe_insert("energy", frame=f0)
    ch.set_interp(kl, "CONSTANT"); ch.set_interp(fl, "CONSTANT")
