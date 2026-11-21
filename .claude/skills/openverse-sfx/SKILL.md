---
name: openverse-sfx
description: Find and add openly licensed sound effects (rain, thunder, whoosh, umbrella, footsteps, crowd, city ambience...) from Openverse to a video, including HyperFrames compositions and the shorts/ pipelines. Use when the user asks for a sound effect, SFX, ambience or foley from Openverse, or wants real recorded sounds instead of synthesized ones. Searches only commercial-use licenses by default and writes a CREDITS.md entry for each sound.
---

# Openverse sound effects

`scripts/openverse.py` talks to the anonymous Openverse API (api.openverse.org). It needs no key and has no dependencies beyond Python 3 and ffmpeg.

```bash
python3 .claude/skills/openverse-sfx/scripts/openverse.py search "umbrella close" --n 8 --max-sec 10
python3 .claude/skills/openverse-sfx/scripts/openverse.py get <ID> --out <project>/audio/sfx --name umbrella_close
python3 .claude/skills/openverse-sfx/scripts/openverse.py add <ID> <downloaded file> --out <project>/audio/sfx --name umbrella_close
```

- **search** prints `id  seconds  license  source  title — creator`. By default only CC0, PDM, CC BY and CC BY-SA are shown, because those allow commercial use and modification. `--any-license` widens the search; NC and ND sounds must not go in a monetized or edited video.
- **get** downloads the sound, converts it to 48 kHz WAV `<out>/<name>.wav`, and appends its attribution to `<out>/CREDITS.md`.
- **add** registers a file the user downloaded themselves from openverse.org, using the same conversion and credit line. Use it when `get` cannot reach the source host.
- Openverse anonymous pages hold at most 20 results.
- Prefer CC0. Sounds under CC BY or CC BY-SA must be credited in the video description, so paste the CREDITS.md lines there.

## Network

Search works wherever `api.openverse.org` is allowed. The audio files themselves live on the source hosts:

- Freesound: `cdn.freesound.org`
- Wikimedia: `upload.wikimedia.org`
- Jamendo, ccMixter and others

These hosts must be allowed too, and some refuse cloud or datacenter IPs. Freesound's CDN answers a bare 403 and Wikimedia answers 429. When that happens, do not spoof a browser. Instead, ask the user to download the sound from the Openverse page (the `foreign_landing_url`) and upload it, then run `add`.

## Using the sounds

- **HyperFrames composition:** place the WAV with an `<audio id="sfx-umbrella" src="audio/sfx/umbrella_close.wav" data-start="34.9" data-duration="1.2" data-volume="0.6">`. Every `<audio>` needs an `id`. Mix and duck it with `/hyperframes-audio`.
- **numpy pipelines** (for example shorts/aura/audio.py): load the WAV and `place()` it at the event time, keeping SFX about half the voice level.
