"""Small CPU physics used by the combat solver: damped springs (hit reactions) and verlet chains (coat, cloak, hair).

No rigid-body or ragdoll: every reaction is a KEYED pose whose offsets come from these closed-form / stepped springs,
so it is deterministic, bounded and art-directable.
"""
import math
from mathutils import Vector as V


def spring_impulse(t, peak, freq, zeta):
    """Response of a damped spring kicked by an impulse at t=0, scaled so its first peak equals `peak`.
    x(t) = e^{-zeta w t} sin(wd t) (normalised); zeta < 1 overshoots back past zero once (a head snap that rebounds)."""
    if t <= 0: return 0.0
    w = 2 * math.pi * freq; z = min(zeta, 0.999); wd = w * math.sqrt(1 - z * z)
    tp = math.atan2(wd, z * w) / wd                       # time of the first peak
    norm = math.exp(-z * w * tp) * math.sin(wd * tp)
    return peak * math.exp(-z * w * t) * math.sin(wd * t) / norm


def spring_step(t, target, freq, zeta):
    """Response of a damped spring to a step to `target` (starts at 0, settles at target, overshoot if zeta < 1)."""
    if t <= 0: return 0.0
    w = 2 * math.pi * freq; z = min(zeta, 0.999); wd = w * math.sqrt(1 - z * z)
    return target * (1 - math.exp(-z * w * t) * (math.cos(wd * t) + z * w / wd * math.sin(wd * t)))


def knockback(t, v0, friction):
    """Distance travelled by a body launched at v0 (m/s) with linear friction c (1/s): v0/c (1 - e^{-ct})."""
    if t <= 0: return 0.0
    return v0 / friction * (1 - math.exp(-friction * t))


class VerletChain:
    """A hanging chain of particles pinned at an anchor that moves with a bone. Each particle is pulled back toward its
    rest position in the bone frame (stiffness, 1/s^2), damped, and kept at fixed segment lengths. The rest shape already
    hangs under gravity, so `gravity` is only an EXTRA droop while the chain is moving (0 = rest shape is the equilibrium;
    a full 9.81 against a 30/s^2 spring would sag 33 cm and saturate every chain).
        ch = VerletChain(rest_local=[(0,0,0), (0,0.04,-0.12), (0,0.07,-0.25)], stiffness=30, damping=0.1, gravity=9.81)
        for each frame: pts = ch.step(M_world_of_bone, dt)      # dt = 0 holds still (hit-stop)
    rest_local[0] is the pin. Positions are world-space Vectors."""
    def __init__(self, rest_local, stiffness=30.0, damping=0.1, gravity=9.81, substeps=4):
        self.rest = [V(p) for p in rest_local]
        self.L = [(b - a).length for a, b in zip(self.rest, self.rest[1:])]
        self.k, self.d, self.g, self.n = stiffness, damping, gravity, substeps
        self.x = None; self.xp = None
    def goal(self, M):
        return [M @ p for p in self.rest]
    def step(self, M, dt):
        goal = self.goal(M)
        if self.x is None:
            self.x = [p.copy() for p in goal]; self.xp = [p.copy() for p in goal]; return [p.copy() for p in self.x]
        if dt <= 0:
            return [p.copy() for p in self.x]
        h = dt / self.n
        for s in range(self.n):
            a = (s + 1) / self.n
            g_s = [gp for gp in goal]
            self.x[0] = g_s[0].copy(); self.xp[0] = g_s[0].copy()
            for i in range(1, len(self.x)):
                vel = (self.x[i] - self.xp[i]).length / max(1e-9, h)
                acc = (g_s[i] - self.x[i]) * self.k + V((0, 0, -self.g * min(1.0, vel / 1.5)))
                nx = self.x[i] + (self.x[i] - self.xp[i]) * (1 - self.d) + acc * h * h
                self.xp[i] = self.x[i]; self.x[i] = nx
            for _ in range(3):                         # segment lengths (inextensible cloth/hair)
                for i in range(1, len(self.x)):
                    a_, b_ = self.x[i - 1], self.x[i]; dv = b_ - a_; ln = dv.length
                    if ln < 1e-9: continue
                    corr = dv * ((ln - self.L[i - 1]) / ln)
                    if i - 1 == 0: self.x[i] = b_ - corr
                    else: self.x[i - 1] = a_ + corr * 0.5; self.x[i] = b_ - corr * 0.5
        return [p.copy() for p in self.x]
    def offsets(self, M):
        """world offset of each particle from its rest (goal) position"""
        return [x - g for x, g in zip(self.x, self.goal(M))]


def smooth(vals, radius=2):
    """gaussian-ish smoothing of a list of floats (used for balance corrections so they never jitter)."""
    if radius <= 0: return list(vals)
    w = [math.exp(-0.5 * (k / max(1e-6, radius * 0.6)) ** 2) for k in range(-radius, radius + 1)]
    out = []
    n = len(vals)
    for i in range(n):
        s = ws = 0.0
        for k, wk in zip(range(-radius, radius + 1), w):
            j = min(n - 1, max(0, i + k)); s += vals[j] * wk; ws += wk
        out.append(s / ws)
    return out


def hull2d(pts):
    """convex hull (monotone chain) of 2D points -> CCW list"""
    P = sorted(set((round(p[0], 6), round(p[1], 6)) for p in pts))
    if len(P) <= 2: return P
    def cross(o, a, b): return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in P:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0: lo.pop()
        lo.append(p)
    for p in reversed(P):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0: up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


def outside_dist(pt, hull):
    """distance (m) of a 2D point outside a CCW convex polygon; 0 if inside. Also returns the closest boundary point."""
    if len(hull) == 0: return float("inf"), pt
    if len(hull) == 1: q = hull[0]; return math.hypot(pt[0] - q[0], pt[1] - q[1]), q
    inside = True; best = (float("inf"), None)
    n = len(hull)
    for i in range(n):
        a, b = hull[i], hull[(i + 1) % n]
        ex, ey = b[0] - a[0], b[1] - a[1]
        if ex * (pt[1] - a[1]) - ey * (pt[0] - a[0]) < 0: inside = False
        L2 = ex * ex + ey * ey or 1e-12
        u = max(0.0, min(1.0, ((pt[0] - a[0]) * ex + (pt[1] - a[1]) * ey) / L2))
        q = (a[0] + ex * u, a[1] + ey * u); d = math.hypot(pt[0] - q[0], pt[1] - q[1])
        if d < best[0]: best = (d, q)
    if inside and n >= 3: return 0.0, pt
    return best
