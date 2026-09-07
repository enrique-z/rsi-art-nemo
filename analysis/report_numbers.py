#!/usr/bin/env python3
"""
report_numbers.py -- emit the EXPERIMENT_REPORT numeric blocks straight from the
ledger, so no number in the report is hand-typed.

Usage: python report_numbers.py --tag primary [--claim-prefix ""]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVID = HERE.parent / "evidence"
PAPER = "nemo_plan_repair_coverage"


def fmt(r):
    v = r["value"]
    if isinstance(v, str):
        return v
    s = f"{v:+.4f}" if isinstance(v, float) else str(v)
    if r.get("ci_low") is not None:
        s += f" [{r['ci_low']:+.4f}, {r['ci_high']:+.4f}]"
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="primary")
    ap.add_argument("--claim-prefix", default="")
    a = ap.parse_args()
    P = a.claim_prefix

    led = {}
    for line in (EVID / f"{PAPER}_{a.tag}_ledger.jsonl").read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            led[r["claim_id"]] = r
    g = lambda k: led.get(P + k)

    print(f"### arm: {a.tag}   (claim prefix '{P}')\n")
    print("**Design**\n")
    for k in ("design::n_runs", "design::n_seeds", "design::n_domains",
              "design::runs_per_ck_cell", "design::proposer"):
        r = g(k)
        if r:
            print(f"- `{k}` = {fmt(r)}")

    print("\n**Held-out plan-execution success (mean, seed-clustered 95% CI)**\n")
    covs = sorted({float(k.split("::c")[1].split("_k")[0])
                   for k in led if "success::c" in k})
    ks = (0, 1, 2, 4)
    print("| coverage c | " + " | ".join(f"k={k}" for k in ks) + " |")
    print("|---" * (len(ks) + 1) + "|")
    for c in covs:
        cells = []
        for k in ks:
            r = g(f"success::c{c:.1f}_k{k}")
            cells.append(f"{r['value']:.3f} [{r['ci_low']:.3f}, {r['ci_high']:.3f}]" if r else "-")
        print(f"| {c:.1f} | " + " | ".join(cells) + " |")

    print("\n**Primary outcome — coverage x k interaction**\n")
    for k in ("primary::interaction_coverage_x_k", "primary::delta_k4_k1_high",
              "primary::delta_k4_k1_low"):
        r = g(k)
        if r:
            print(f"- `{k}` = {fmt(r)}")

    print("\n**Coverage main effect (high minus low) at each k**\n")
    for k in ks:
        r = g(f"maineffect::coverage_at_k{k}")
        if r:
            print(f"- k={k}: {fmt(r)}")
    r = g("success::k0_baseline_pooled")
    if r:
        print(f"- pooled k=0 baseline: {fmt(r)}")

    print("\n**Falsifier — divergence-event rate**\n")
    for k in ("falsifier::divergence_rate_low", "falsifier::divergence_rate_high",
              "falsifier::divergence_gap_high_minus_low"):
        r = g(k)
        if r:
            print(f"- `{k}` = {fmt(r)}")

    print("\n**Model-edit distance to ground truth**\n")
    print("| coverage band | " + " | ".join(f"k={k}" for k in ks) + " |")
    print("|---" * (len(ks) + 1) + "|")
    for lab in ("low", "high"):
        cells = []
        for k in ks:
            r = g(f"editdist::{lab}_k{k}")
            cells.append(f"{r['value']:.3f}" if r else "-")
        print(f"| c {'<=0.4' if lab=='low' else '>=0.8'} | " + " | ".join(cells) + " |")

    print("\n**Integrity counters (summed over all runs; never dropped)**\n")
    for k in ("integrity::plan_calls", "integrity::budget_exhausted_train",
              "integrity::budget_exhausted_eval", "integrity::no_plan_train",
              "integrity::no_plan_eval", "integrity::no_proposal_rounds",
              "integrity::no_accept_rounds", "integrity::llm_calls",
              "integrity::llm_errors", "integrity::parse_failures",
              "integrity::empty_proposals"):
        r = g(k)
        if r:
            print(f"- `{k.split('::')[1]}` = {r['value']}")


if __name__ == "__main__":
    main()
