"""Unit tests for the pure parts (no scene): schema validation, hit-stop time map, springs, verlet chain, support hull.
    /root/.venvs/bpy/bin/python shorts/kuro_oni/combat/tests/test_core.py
"""
import copy, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bpy  # noqa: F401  (bpy provides mathutils)
import schema as S, physics as PH
from mathutils import Matrix, Vector as V

def test_clips_valid():
    seq = S.load_sequence("combat_test"); assert S.validate_sequence(seq) == [], S.validate_sequence(seq)
    assert seq["timemap"].n_out == 150 and seq["story_frames"] == 140

def test_validator_catches():
    c = S.load_clip("ct_slip_punch_a"); bad = copy.deepcopy(c)
    bad["duration"] = 99; bad["moves"][0]["move"] = "flying_kick"; bad["hits"][0]["part"] = "elbow"
    bad["moves"][2]["end"] = 31; bad["camera"]["cuts"][0]["keys"][0]["roll"] = 5
    e = " | ".join(S.validate_clip(bad))
    for frag in ("duration", "unknown move", "part elbow", "must end on its hit frame", "roll must be 0"): assert frag in e, (frag, e)

def test_timemap_hitstop():
    tm = S.TimeMap(10, [(4, 3)])
    assert tm.n_out == 13 and [tm.story(f) for f in range(1, 14)] == [0, 1, 2, 3, 4, 4, 4, 4, 5, 6, 7, 8, 9]
    assert tm.out_of(4) == 5 and tm.out_last(4) == 8 and tm.frozen(6) and not tm.frozen(5)

def test_springs():
    w = 2.6; ts = [i / 1000 for i in range(1, 3000)]; xs = [PH.spring_impulse(t, 50.0, w, 0.3) for t in ts]
    assert abs(max(xs) - 50.0) < 0.05 and min(xs) < 0                 # peak = 50 deg, rebounds once (underdamped)
    assert abs(PH.spring_step(5.0, 1.0, 1.0, 0.8) - 1.0) < 1e-3
    assert abs(PH.knockback(10.0, 1.0, 5.0) - 0.2) < 1e-6

def test_verlet_freeze_and_follow():
    ch = PH.VerletChain([(0, 0, 0), (0, 0, -0.2), (0, 0, -0.4)], stiffness=60, damping=0.1, gravity=0.0)
    M = Matrix.Identity(4); ch.step(M, 1 / 30)
    M2 = Matrix.Translation((0.3, 0, 0)); p = ch.step(M2, 1 / 30); assert p[-1].x < 0.3 - 0.01       # tip lags (follow-through)
    q = ch.step(M2, 0.0); assert all((a - b).length < 1e-9 for a, b in zip(p, q))                    # hit-stop: frozen
    for _ in range(120): r = ch.step(M2, 1 / 30)
    assert (r[-1] - V((0.3, 0, -0.4))).length < 0.01                                                 # settles on its rest shape

def test_support():
    hull = PH.hull2d([(0, 0), (1, 0), (1, 1), (0, 1), (0.5, 0.5)]); assert len(hull) == 4
    assert PH.outside_dist((0.5, 0.5), hull)[0] == 0.0 and abs(PH.outside_dist((1.5, 0.5), hull)[0] - 0.5) < 1e-9

if __name__ == "__main__":
    n = 0
    for k, f in list(globals().items()):
        if k.startswith("test_"): f(); n += 1; print("ok", k)
    print(n, "tests passed")
