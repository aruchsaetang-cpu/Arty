"""Proportion / face consistency across clips: builds every clip on its own and the sequence (separate processes, the
same way they are rendered), fingerprints each actor (rest bone lengths, posed bone stretch, eye/brow/lash/skin
geometry in head space, eye materials, shape keys, head scale) and asserts they are identical per character style.

    python shorts/kuro_oni/combat/consistency.py [combat_test]      # -> combat/out/consistency_report.json, exit 1 on mismatch
"""
import json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import schema as S
OUT = os.path.join(HERE, "out")


def main(seq_id):
    seq = S.load_sequence(seq_id); ids = list(seq["clips"]) + ([seq_id] if len(seq["clips"]) > 1 else [])
    for i in ids:
        r = subprocess.run([S.__dict__.get("BPY", "/root/.venvs/bpy/bin/python"), os.path.join(HERE, "render_seq.py"), i, "--check-only"],
                           capture_output=True, text=True)
        print(i, "checks", "PASS" if r.returncode == 0 else "FAIL", flush=True)
    fps = {i: json.load(open(os.path.join(OUT, "consistency", f"{i}.json"))) for i in ids}
    by_style = {}
    for i, fp in fps.items():
        for actor, d in fp.items(): by_style.setdefault(d["style"], []).append((i, actor, d))
    rep = dict(seq=seq_id, builds=ids, styles={}, mismatches=[])
    for style, rows in by_style.items():
        ref_i, ref_a, ref = rows[0]
        row = dict(builds=len(rows), bones=ref["bones"], bone_hash=ref["bone_hash"], height_m=ref["height_m"],
                   max_bone_len_diff_mm=0.0, face_parts=sorted(ref["face"]), max_posed_stretch_mm=max(r[2]["max_posed_bone_stretch_mm"] for r in rows),
                   max_head_scale_dev=max(r[2]["max_head_scale_dev"] for r in rows))
        for i, a, d in rows[1:]:
            diff = max(abs(d["bone_lengths"][k] - ref["bone_lengths"][k]) for k in ref["bone_lengths"]) * 1000
            row["max_bone_len_diff_mm"] = max(row["max_bone_len_diff_mm"], round(diff, 4))
            if diff > 0.01: rep["mismatches"].append(f"{style}: bone lengths differ by {diff:.4f} mm in {i} vs {ref_i}")
            for part, f in ref["face"].items():
                g = d["face"].get(part)
                if g is None or g["verts"] != f["verts"] or g["mats"] != f["mats"] or g["shape_keys"] != f["shape_keys"] or len(g["coords"]) != len(f["coords"]):
                    rep["mismatches"].append(f"{style}: face part {part} topology/material/shape keys differ in {i} vs {ref_i}"); continue
                dev = max((abs(x - y) for x, y in zip(g["coords"], f["coords"])), default=0.0) * 1000
                row["max_face_vertex_dev_mm"] = round(max(row.get("max_face_vertex_dev_mm", 0.0), dev), 5)
                if dev > 0.05: rep["mismatches"].append(f"{style}: face part {part} moved {dev:.3f} mm in {i} vs {ref_i}")
        rep["styles"][style] = row
    rep["pass"] = not rep["mismatches"]
    os.makedirs(OUT, exist_ok=True); json.dump(rep, open(os.path.join(OUT, "consistency_report.json"), "w"), indent=1)
    print(json.dumps(rep, indent=1)); return 0 if rep["pass"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "combat_test"))
