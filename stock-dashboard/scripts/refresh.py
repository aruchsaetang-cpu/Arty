#!/usr/bin/env python3
"""Headless refresh - run from cron/systemd; needs no browser and no Claude session.
  python3 scripts/refresh.py            # membership + universe quotes + any stale/missing annual statements
  python3 scripts/refresh.py --force    # re-fetch every company's annual statements
  python3 scripts/refresh.py --quotes   # quotes only (cheap; every 10-15 min while the market is open)
Example crontab:  */15 13-21 * * 1-5  cd /path/stock-dashboard && python3 scripts/refresh.py --quotes
                  30 6 * * *          cd /path/stock-dashboard && python3 scripts/refresh.py"""
import argparse, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from dashboard import jobs, membership  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--force", action="store_true")
ap.add_argument("--quotes", action="store_true")
a = ap.parse_args()
m = membership.load_membership(refresh=True)
print(f"membership: {len(m['members'])} securities - {m['label']}")
jobs.reassess_cached()
jobs.refresh_quotes()
print("quotes:", jobs.status()["quotes"])
if not a.quotes:
    jobs.refresh_fundamentals(force=a.force)
    print("fundamentals:", jobs.status()["fundamentals"])
