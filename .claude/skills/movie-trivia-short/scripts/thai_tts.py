"""usage: phrases.py spec.json out.wav captions.json  -- spec: {"speed":1.1,"gap":0.12,"phrases":[[speak, display, extra_gap], ...]}"""
# Offline Thai TTS (Meta MMS-TTS via sherpa-onnx). Setup: pip install sherpa-onnx soundfile; download
# https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-mms-tha.tar.bz2 and extract to /opt/tts/.
# Speak text must be Thai script only (no Latin letters, no ๆ): write "เพื่อนเพื่อน", "ทอยสตอรี่"; the display text can differ.
import sys, json, numpy as np, sherpa_onnx, soundfile as sf
spec = json.load(open(sys.argv[1]))
cfg = sherpa_onnx.OfflineTtsConfig(model=sherpa_onnx.OfflineTtsModelConfig(
    vits=sherpa_onnx.OfflineTtsVitsModelConfig(model="/opt/tts/vits-mms-tha/model.onnx", tokens="/opt/tts/vits-mms-tha/tokens.txt"), num_threads=4))
tts = sherpa_onnx.OfflineTts(cfg)
sr = None; out = []; caps = []; t = 0.0
for p in spec["phrases"]:
    speak, disp = p[0], p[1]; extra = p[2] if len(p) > 2 else 0
    a = tts.generate(speak, sid=0, speed=spec.get("speed", 1.0)); sr = a.sample_rate
    x = np.array(a.samples, dtype=np.float32)
    # trim leading/trailing silence
    idx = np.where(np.abs(x) > 0.02)[0]
    if len(idx): x = x[max(0, idx[0]-int(0.02*sr)): idx[-1]+int(0.04*sr)]
    caps.append({"start": round(t, 2), "text": disp})
    out.append(x); t += len(x)/sr
    g = spec.get("gap", 0.12) + extra
    out.append(np.zeros(int(g*sr), np.float32)); t += g
for i, c in enumerate(caps):
    c["end"] = caps[i+1]["start"] if i+1 < len(caps) else round(t, 2)
sf.write(sys.argv[2], np.concatenate(out), sr)
json.dump(caps, open(sys.argv[3], "w"), ensure_ascii=False, indent=1)
print("total", round(t, 2))
