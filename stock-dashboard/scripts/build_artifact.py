#!/usr/bin/env python3
"""Build the static UI (snapshot mode) and assemble ONE self-contained page (CSS + JS inlined) for publishing.
Usage: python3 scripts/build_artifact.py OUT_DIR   -> OUT_DIR/index.html (+ OUT_DIR/data from export_snapshot.py)"""
import os, re, subprocess, sys, tempfile
OUT = sys.argv[1]
FE = os.path.join(os.path.dirname(__file__), "..", "frontend")
tmp = tempfile.mkdtemp()
subprocess.run(["npx", "vite", "build", "--base", "./", "--outDir", tmp, "--emptyOutDir"], cwd=FE, check=True,
               env={**os.environ, "VITE_STATIC": "1"}, stdout=subprocess.DEVNULL)
html = open(os.path.join(tmp, "index.html")).read()
css = "".join(open(os.path.join(tmp, p)).read() for p in re.findall(r'href="\./(assets/[^"]+\.css)"', html))
js = "".join(open(os.path.join(tmp, p)).read() for p in re.findall(r'src="\./(assets/[^"]+\.js)"', html))
js = js.replace("</script", "<\\/script")
fonts = re.search(r'<link rel="stylesheet" href="(https://fonts\.googleapis\.com[^"]+)"', html).group(1)
page = f"""<title>Margin of Safety</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{fonts}">
<style>{css}</style>
<div id="root"></div>
<script type="module">{js}</script>
"""
os.makedirs(OUT, exist_ok=True)
open(os.path.join(OUT, "index.html"), "w").write(page)
print(f"page {len(page)/1e6:.2f} MB -> {OUT}/index.html")
