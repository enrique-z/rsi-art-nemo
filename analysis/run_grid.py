#!/usr/bin/env python
"""
run_grid.py -- driver for the verifier-coverage x repair-round grid.

Reproduces every run row in evidence/ from the PDDL sources plus a seed.
Per-cell JSONL checkpoints: a crash loses one cell, not the run.

Usage:
  python run_grid.py --pilot                       # 60s single-cell pilot
  python run_grid.py --throughput                  # timing probe
  python run_grid.py --full --out <dir> [--proposer llm|deterministic]
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from wm_repair import core, runner

REPO = Path(__file__).resolve().parents[3]
BENCH = REPO / "external" / "pyperplan-benchmarks"
DOMAINS = ("blocks", "gripper", "logistics")
TRAIN_IDX = (1, 3, 5, 7, 9)
EVAL_IDX = (2, 4, 6, 8, 10)
COVERAGES = (0.2, 0.4, 0.6, 0.8, 1.0)
SNAPSHOTS = (0, 1, 2, 4)
N_ROUNDS = 4
N_CORRUPT = 1
PLAN_BUDGET = 1200
PLAN_SECONDS = 5.0


def load_domain(name):
    dp = BENCH / name / "domain.pddl"
    sk = core.load_skeleton(dp, BENCH / name / "task01.pddl")
    truth = core.truth_model(sk)
    train = [core.load_instance(sk, dp, BENCH / name / f"task{i:02d}.pddl") for i in TRAIN_IDX]
    ev = [core.load_instance(sk, dp, BENCH / name / f"task{i:02d}.pddl") for i in EVAL_IDX]
    cache = {i.name: core.ground_model(sk, truth, i) for i in train + ev}
    return sk, truth, train, ev, cache


def provenance():
    return {
        "pyperplan_version": __import__("pyperplan").__dict__.get("__version__", "2.1"),
        "benchmarks_git_sha": (BENCH / "PROVENANCE.txt").read_text().split()[0],
        "python": platform.python_version(),
        "platform": platform.platform(),
        "plan_budget_expansions": PLAN_BUDGET,
        # A12: record the EFFECTIVE wallclock bound actually in force, not the
        # module default -- the deterministic replication grid runs with
        # NEMO_PLAN_MAX_SECONDS=inf and its provenance must say so.
        # inf is not strict JSON, so record it as a string when unbounded.
        "plan_budget_seconds": (core.PLAN_MAX_SECONDS
                                if core.PLAN_MAX_SECONDS != float("inf")
                                else "inf (wallclock bound disabled, A12)"),
        "plan_budget_seconds_module_default": PLAN_SECONDS,
        "n_corrupt": N_CORRUPT,
        "train_instances": list(TRAIN_IDX),
        "eval_instances": list(EVAL_IDX),
    }


def one(sk, truth, tr, ev, cache, dom, seed, cov, proposer, llm_model):
    t0 = time.time()
    r = runner.run_one(sk, truth, tr, ev, cache, seed, cov, N_ROUNDS, N_CORRUPT,
                       PLAN_BUDGET, proposer, llm_model, SNAPSHOTS)
    r.update({"domain": dom, "seed": seed, "coverage": cov,
              "proposer": proposer, "llm_model": llm_model if proposer == "llm" else None,
              "wallclock_s": round(time.time() - t0, 3),
              "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", action="store_true")
    ap.add_argument("--throughput", action="store_true")
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--proposer", default="deterministic", choices=["deterministic", "llm"])
    ap.add_argument("--llm-model", default="qwen2.5-coder:14b")
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--n-corrupt", type=int, default=None)
    ap.add_argument("--out", default=str(Path(__file__).resolve().parents[1] / "evidence" / "runs"))
    a = ap.parse_args()
    global N_CORRUPT
    if a.n_corrupt is not None:
        N_CORRUPT = a.n_corrupt

    if a.pilot:
        t0 = time.time()
        sk, truth, tr, ev, cache = load_domain("blocks")
        print(f"[pilot] skeleton loaded: |C|={len(sk.conditions)} "
              f"|C*|={sum(1 for c in sk.conditions if core.model_holds(truth, c))} "
              f"({time.time()-t0:.1f}s)", flush=True)
        r = runner.run_one(sk, truth, tr, ev, cache, seed=0, coverage=0.6,
                           n_rounds=1, n_corrupt=N_CORRUPT, budget=PLAN_BUDGET,
                           proposer=a.proposer, llm_model=a.llm_model, snapshots=(0, 1))
        print(json.dumps(r, indent=2, default=str))
        print(f"[pilot] TOTAL {time.time()-t0:.1f}s", flush=True)
        return

    if a.throughput:
        rows = []
        for dom in DOMAINS:
            t0 = time.time()
            sk, truth, tr, ev, cache = load_domain(dom)
            tload = time.time() - t0
            ts = []
            for seed in (0, 1):
                for cov in (0.2, 1.0):
                    t1 = time.time()
                    one(sk, truth, tr, ev, cache, dom, seed, cov, a.proposer, a.llm_model)
                    ts.append(time.time() - t1)
            rows.append({"domain": dom, "load_s": round(tload, 2),
                         "traj_s_mean": round(sum(ts) / len(ts), 2),
                         "traj_s_max": round(max(ts), 2)})
            print(json.dumps(rows[-1]), flush=True)
        per_traj = sum(r["traj_s_mean"] for r in rows)
        total = per_traj * a.seeds * len(COVERAGES)
        print(json.dumps({"proposer": a.proposer,
                          "sum_traj_s_over_domains": round(per_traj, 2),
                          "projected_full_grid_s": round(total, 1),
                          "projected_full_grid_h": round(total / 3600, 2),
                          "seeds": a.seeds}), flush=True)
        return

    if a.full:
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "provenance.json").write_text(json.dumps(provenance(), indent=2))
        for dom in DOMAINS:
            sk, truth, tr, ev, cache = load_domain(dom)
            for cov in COVERAGES:
                cell = out / f"cell_{dom}_c{cov:.1f}.jsonl"
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
                        r = one(sk, truth, tr, ev, cache, dom, seed, cov,
                                a.proposer, a.llm_model)
                        fh.write(json.dumps(r, default=str) + "\n")
                        fh.flush()
                print(f"[cell] {dom} c={cov} n={a.seeds} {time.time()-t0:.1f}s", flush=True)
        print("[full] done", flush=True)
        return

    ap.print_help()


if __name__ == "__main__":
    main()
