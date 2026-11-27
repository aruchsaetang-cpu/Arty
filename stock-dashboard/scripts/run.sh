#!/usr/bin/env bash
# Launch the dashboard (API + built UI + background refresher) on http://localhost:8765
set -euo pipefail
cd "$(dirname "$0")/../backend"
exec python3 -m uvicorn dashboard.app:app --host 0.0.0.0 --port "${PORT:-8765}"
