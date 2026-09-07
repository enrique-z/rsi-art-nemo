#!/usr/bin/env python3
"""
build_manifest.py -- merge the per-arm manifests into the ONE stamp manifest
that analysis/guard.py consumes.

`guard.load_manifest()` globs `evidence/*_stamp_manifest.json` and silently uses
the alphabetically first match if several exist.  Because each experimental arm
emits its own manifest, more than one file matching that glob would make the
guard check the paper against the WRONG arm.  Per-arm manifests are therefore
written to `evidence/manifests/<tag>.json` (which does not match the glob) and
merged here into the single canonical file, aborting on any key collision.

Claim-id namespacing keeps arms disjoint:
  primary grid (deterministic proposer, n_corrupt=4) : no prefix
  supplementary single-error arm (n_corrupt=1)       : "n1::"
  secondary LLM-proposer arm                         : "llm::"
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVID = HERE.parent / "evidence"
PAPER = "nemo_plan_repair_coverage"


def main() -> int:
    src = sorted((EVID / "manifests").glob("*.json"))
    if not src:
        print("[manifest] no per-arm manifests in evidence/manifests/", file=sys.stderr)
        return 2

    merged, origin = {}, {}
    for f in src:
        rows = json.loads(f.read_text())["ledger_rows"]
        for k, v in rows.items():
            if k in merged:
                print(f"[manifest] FATAL: claim_id collision '{k}' between "
                      f"{origin[k]} and {f.name} -- namespace one of the arms "
                      f"with --claim-prefix", file=sys.stderr)
                return 1
            merged[k] = v
            origin[k] = f.name

    out = EVID / f"{PAPER}_stamp_manifest.json"
    out.write_text(json.dumps({"ledger_rows": merged}, indent=2))

    stale = [p for p in EVID.glob("*_stamp_manifest.json") if p != out]
    for p in stale:
        print(f"[manifest] WARNING: stale manifest {p.name} also matches the "
              f"guard glob -- remove it", file=sys.stderr)

    print(json.dumps({
        "manifest": str(out),
        "arms": [f.name for f in src],
        "keys": len(merged),
        "per_arm": {f.name: sum(1 for k in merged if origin[k] == f.name) for f in src},
        "stale_matching_guard_glob": [p.name for p in stale],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
