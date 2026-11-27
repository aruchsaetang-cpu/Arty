#!/usr/bin/env bash
# One-time setup: Python deps + build the UI. Then run scripts/run.sh
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m pip install -q -r backend/requirements.txt
(cd frontend && npm install --no-audit --no-fund && npm run build)
echo "Setup done. Launch with: scripts/run.sh   (open http://localhost:8765)"
