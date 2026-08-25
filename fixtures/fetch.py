#!/usr/bin/env python3
"""Fetch the gold-standard calibration corpus into fixtures/gold/ (gitignored).

Third-party CLAUDE.md/AGENTS.md files stay under their repos' licenses, so we
download them on demand instead of committing them. Network required.

Usage: python3 fixtures/fetch.py
"""

import json
import os
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    with open(os.path.join(HERE, "MANIFEST.json")) as f:
        manifest = json.load(f)
    out_dir = os.path.join(HERE, "gold")
    os.makedirs(out_dir, exist_ok=True)
    for entry in manifest["gold"]:
        dest = os.path.join(out_dir, entry["name"] + ".md")
        try:
            req = urllib.request.Request(
                entry["url"], headers={"User-Agent": "claude-md-doctor-fixtures"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                text = resp.read().decode("utf-8", "replace")
        except Exception as exc:  # noqa: BLE001 — report and continue
            print("FAIL  %-20s %s" % (entry["name"], exc))
            continue
        with open(dest, "w", encoding="utf-8") as f:
            f.write(text)
        lines = text.count("\n") + 1
        approx = entry["expect"].get("approx_lines", 0)
        drift = "" if approx and abs(lines - approx) <= max(10, approx // 2) \
            else "  (drifted from expected ~%d)" % approx
        print("ok    %-20s %4d lines%s" % (entry["name"], lines, drift))
    print("fetched into", out_dir, "— gitignored; do not commit.")


if __name__ == "__main__":
    main()
