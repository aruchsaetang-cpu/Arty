"""Cinematic camera helpers (reusable, deterministic, frame-indexed; no real-time clocks).

The camera is evaluated per output frame from the animation timeline, then smoothed and keyed every frame:
  minjerk(t)            minimum-jerk ease (position, velocity and acceleration continuous; zero jerk spikes)
  ease_out(t)           starts moving, settles smoothly (for a move that ends a shot / the film)
  smooth(samples, s)    zero-phase Gaussian smoothing of a per-frame trajectory (sigma s frames); the ends are
                        extended by odd reflection, so the first and last positions AND their velocities are kept
  soft_handheld(f, ...) operator feel without jitter: only components at or below ~2 Hz (walking bob at step rate,
                        slow sway); the old high-frequency wobble (3-10 Hz) read as micro-jitter
  arc(centre, off, deg) rotate a camera offset around a subject (orbit / arc move), about the vertical axis
  report(frames, cam, look)   speed / acceleration / jerk and view-direction angular rate per frame (QA)
Orientation: the film camera aims with a Track-To constraint (no roll, horizon always level), so smooth
positions for the camera and its look target give smooth rotation without quaternion keys."""
import math
from mathutils import Vector as V

def minjerk(t):
    t = max(0.0, min(1.0, t)); return t * t * t * (10 - 15 * t + 6 * t * t)

def ease_out(t):
    t = max(0.0, min(1.0, t)); return 1 - (1 - t) ** 3

def smooth(samples, sigma):
    """samples: list of Vector (or float). Zero-phase Gaussian, ends extended by odd reflection (keeps end values
    and end slopes), so a shot still starts exactly where it started."""
    n = len(samples)
    if n < 3 or sigma <= 0: return list(samples)
    r = int(math.ceil(3 * sigma)); w = [math.exp(-0.5 * (k / sigma) ** 2) for k in range(-r, r + 1)]; ws = sum(w)
    is_vec = hasattr(samples[0], "copy")
    def at(i):
        if i < 0: return samples[0] * 2 - samples[-i]
        if i >= n: return samples[-1] * 2 - samples[2 * (n - 1) - i]
        return samples[i]
    out = []
    for i in range(n):
        acc = (V((0, 0, 0)) if is_vec else 0.0)
        for k, wk in zip(range(-r, r + 1), w): acc = acc + at(i + k) * wk
        out.append(acc / ws)
    return out

def soft_handheld(f, walk=1.0, amp=1.0, step_period=15.0):
    """(camera offset, look offset): walking bob at the step rate + slow sway; nothing above ~2 Hz at 30 fps."""
    u = 2 * math.pi * f / step_period
    c = V((0.012 * walk * math.sin(u / 2) + amp * 0.004 * (math.sin(f * 0.11) + 0.5 * math.sin(f * 0.23 + 1)), 0,
           0.012 * walk * math.cos(u) + amp * 0.003 * math.sin(f * 0.17 + 2)))
    l = V((amp * (0.035 * math.sin(f * 0.09 + 0.5) + 0.015 * math.sin(f * 0.21)), 0,
           amp * (0.025 * math.sin(f * 0.13 + 2) + 0.01 * math.sin(f * 0.27)) + 0.008 * walk * math.cos(u + 0.6)))
    return c, l

def arc(off, deg):
    """Rotate an offset vector about +Z by deg (orbit around the subject)."""
    a = math.radians(deg); c, s = math.cos(a), math.sin(a)
    return V((off.x * c - off.y * s, off.x * s + off.y * c, off.z))

def report(frames, cam, look):
    """Per-frame QA numbers: speed (m/s), acceleration (m/s^2), jerk (m/s^3), view angular rate (deg/s)."""
    fps = 30.0; out = []
    for i in range(len(frames)):
        row = dict(f=frames[i])
        if 0 < i < len(frames) - 1:
            v = (cam[i + 1] - cam[i - 1]) * (fps / 2); a = (cam[i + 1] - 2 * cam[i] + cam[i - 1]) * fps * fps
            d0 = (look[i - 1] - cam[i - 1]).normalized(); d1 = (look[i + 1] - cam[i + 1]).normalized()
            row.update(speed=v.length, acc=a.length, ang=math.degrees(d0.angle(d1, 0.0)) * fps / 2)
        out.append(row)
    for i in range(2, len(out) - 2):
        a0 = (cam[i] - 2 * cam[i - 1] + cam[i - 2]); a1 = (cam[i + 2] - 2 * cam[i + 1] + cam[i])
        out[i]["jerk"] = ((a1 - a0) * fps ** 3 / 2).length
    return out
