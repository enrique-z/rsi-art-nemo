#!/usr/bin/env python
"""
run_llm_arm.py -- SECONDARY arm: same repair loop, LLM proposer (local Ollama).

The primary grid uses the deterministic search-based proposer, because the LLM
proposer failed the pre-declared throughput bar (see evidence/DESIGN_NOTES.md
Sec.1).  This reduced arm exists to answer one question: is the coverage effect
an artifact of the deterministic proposer?  It runs the cheapest domain only
(blocks) with fewer seeds, and is reported with its own, smaller N -- never
pooled with the primary grid.

Per-cell JSONL checkpoints; resumable.
"""

from __future__ import annotations

import argparse
import atexit
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_grid as G


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", default="blocks")
    ap.add_argument("--seeds", type=int, default=8)
    ap.add_argument("--llm-model", default="qwen3:8b")
    ap.add_argument("--n-corrupt", type=int, default=4)
    ap.add_argument("--out", default=str(Path(__file__).resolve().parents[1] / "evidence" / "runs_llm"))
    a = ap.parse_args()

    G.N_CORRUPT = a.n_corrupt
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    # Single-writer lock.  Two overlapping run_llm_arm processes once appended to
    # the same cell files, mixing rows produced under a since-fixed proposal
    # parser with rows produced after the fix.  That contaminated arm was
    # discarded; this lock makes the failure impossible to repeat.
    lock = out / ".writer.lock"
    try:
        fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        print(f"[llm] REFUSING TO START: {lock} exists -- another writer holds this "
              f"output dir. Remove the lock only if no run_llm_arm process is alive.",
              file=sys.stderr)
        return 2
    os.write(fd, str(os.getpid()).encode())
    os.close(fd)
    atexit.register(lambda: lock.unlink(missing_ok=True))
    prov = G.provenance()
    prov.update({"arm": "secondary_llm", "llm_model": a.llm_model,
                 "domain": a.domain, "seeds": a.seeds})
    (out / "provenance.json").write_text(json.dumps(prov, indent=2))

    sk, truth, tr, ev, cache = G.load_domain(a.domain)
    print(f"[llm] start domain={a.domain} model={a.llm_model} "
          f"n_corrupt={a.n_corrupt} seeds={a.seeds}", flush=True)
    for cov in G.COVERAGES:
        cell = out / f"cell_{a.domain}_c{cov:.1f}.jsonl"
        done = set()
        if cell.exists():
            for line in cell.read_text().splitlines():
                if line.strip():
                    done.add(json.loads(line)["seed"])
        t0 = time.time()
        with cell.open("a") as fh:
            for seed in range(a.seeds):
                if seed in done:
                    continue
                t1 = time.time()
                r = G.one(sk, truth, tr, ev, cache, a.domain, seed, cov, "llm", a.llm_model)
                fh.write(json.dumps(r, default=str) + "\n")
                fh.flush()
                print(f"[llm] c={cov} seed={seed} {time.time()-t1:.0f}s "
                      f"llm_calls={r['stats']['llm_calls']} "
                      f"errors={r['stats']['llm_errors']} "
                      f"parse_fail={r['stats']['parse_failures']}", flush=True)
        print(f"[llm-cell] {a.domain} c={cov} {time.time()-t0:.1f}s", flush=True)
    print("[llm] done", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
