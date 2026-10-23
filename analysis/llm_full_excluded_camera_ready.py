#!/usr/bin/env python3
"""
llm_full_excluded_camera_ready.py -- descriptive results of the EXCLUDED
full-parity LLM-proposer arm (A11, evidence/runs_llm_full/, qwen3:8b), for the
camera-ready appendix.

The arm was excluded by its pre-committed contamination stop-rule
(evidence/DESIGN_NOTES.md Sec.6, reporting rule 2). These numbers are reported
as DESCRIPTIVE ONLY; they are not banked as claims and are never pooled with
the primary grid or with the 8-seed `llm::` arm.

Every outcome uses the pure functions of analysis/aggregate.py (identical
definitions, identical seed-clustered bootstrap: 10000 resamples,
seed=20260907, unit = seed, all domains/coverages/k carried together) and the
same rounding (round(x, 4)). aggregate.main() is NOT called; this script writes
exactly one file: evidence/llm_full_excluded_camera_ready.json (refuses to
overwrite it).

Stop-rule check, as pre-committed: per-run rates of parse_failures, llm_errors
and empty_proposals in the first half vs the second half of the completed runs
in job order. Job order = the row `timestamp` (the runner writes one row per
run as it completes; run_llm_arm.py is invoked once per domain and iterates
coverage ascending, then seed ascending). The script asserts that timestamp
order equals that domain-sequential schedule. Within-domain version: the same
split applied to each domain's 100 runs separately.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import aggregate as A  # noqa: E402  (pure functions only; main() is never called)

EVID = HERE.parent / "evidence"
RUN_DIR = EVID / "runs_llm_full"
OUT = EVID / "llm_full_excluded_camera_ready.json"
DOMAIN_ORDER = ("blocks", "gripper", "logistics")  # schedule actually executed
STOP_FIELDS = ("parse_failures", "llm_errors", "empty_proposals")
R4 = lambda x: None if x is None else round(x, 4)  # same rounding as aggregate.py


def ci_entry(boot_result):
    p, lo, hi, nb = boot_result
    return {"value": R4(p), "ci_low": R4(lo), "ci_high": R4(hi), "valid_resamples": nb}


def main_effect(idx, ss, k):
    """Copy of the closure inside aggregate.main() (not importable)."""
    h = A.mean([A.snap(r, k) for s in ss for (d, c), r in idx[s].items() if c in A.HIGH])
    l = A.mean([A.snap(r, k) for s in ss for (d, c), r in idx[s].items() if c in A.LOW])
    return None if (h is None or l is None) else h - l


def half_rates(runs):
    """First half vs second half of `runs` (already in job order)."""
    n = len(runs)
    h = n // 2
    halves = {"first": runs[:h], "second": runs[h:]}
    out = {"n_first": h, "n_second": n - h}
    for f in STOP_FIELDS:
        e = {}
        for name, part in halves.items():
            tot = sum(r["stats"][f] for r in part)
            calls = sum(r["stats"]["llm_calls"] for r in part)
            e[f"{name}_count"] = tot
            e[f"{name}_per_run"] = R4(tot / len(part))
            e[f"{name}_runs_with_any"] = sum(1 for r in part if r["stats"][f] > 0)
            e[f"{name}_per_llm_call"] = R4(tot / calls) if calls else None
        e["rose_per_run"] = e["second_per_run"] > e["first_per_run"]
        e["rose_per_llm_call"] = (e["second_per_llm_call"] or 0) > (e["first_per_llm_call"] or 0)
        out[f] = e
    out["any_field_rose_per_run"] = any(out[f]["rose_per_run"] for f in STOP_FIELDS)
    return out


def main():
    if OUT.exists():
        raise SystemExit(f"refusing to overwrite {OUT}")
    rows = A.load(RUN_DIR)
    idx = A.build_index(rows)
    seeds = sorted(idx)
    domains = sorted({r["domain"] for r in rows})
    covs = sorted({round(r["coverage"], 1) for r in rows})
    res = {
        "arm": "llmfull (A11) -- EXCLUDED by pre-committed contamination stop-rule; descriptive only",
        "source": str(RUN_DIR.relative_to(HERE.parent)),
        "proposer": sorted({r["proposer"] for r in rows}),
        "llm_model": sorted({r["llm_model"] for r in rows if r.get("llm_model")}),
        "definitions": "analysis/aggregate.py pure functions; seed-clustered bootstrap "
                       f"n_boot={A.N_BOOT}, rng seed=20260907, unit=seed; HIGH={A.HIGH}, "
                       f"LOW={A.LOW}; values round(x,4)",
        "n_runs": len(rows),
        "n_seeds": len(seeds), "seeds": [min(seeds), max(seeds)],
        "domains": domains, "coverages": covs,
        "runs_per_ck_cell": {f"c{c:.1f}": sum(1 for r in rows if round(r["coverage"], 1) == c)
                             for c in covs},
        "expected_runs": len(domains) * len(covs) * len(seeds),
    }
    keys = {(r["domain"], round(r["coverage"], 1), r["seed"]) for r in rows}
    res["duplicate_or_missing_rows"] = len(rows) != len(keys) or len(keys) != res["expected_runs"]

    # ---------------- success by (c, k) ----------------
    res["success"] = {}
    for cov in covs:
        for k in A.KS:
            res["success"][f"c{cov:.1f}_k{k}"] = ci_entry(
                A.bootstrap(seeds, lambda ss, cov=cov, k=k: A.cell_mean(idx, ss, cov, k)))
    res["success_k0_baseline_pooled"] = ci_entry(A.bootstrap(
        seeds, lambda ss: A.mean([A.snap(r, 0) for s in ss for r in idx[s].values()])))

    # ---------------- interaction, deltas, main effects ----------------
    res["interaction_coverage_x_k"] = ci_entry(A.bootstrap(seeds, lambda ss: A.interaction(idx, ss)))
    for label, cs in (("high", A.HIGH), ("low", A.LOW)):
        res[f"delta_k4_k1_{label}"] = ci_entry(
            A.bootstrap(seeds, lambda ss, cs=cs: A.delta_41(idx, ss, cs)))
    res["maineffect_coverage"] = {
        f"k{k}": ci_entry(A.bootstrap(seeds, lambda ss, k=k: main_effect(idx, ss, k)))
        for k in A.KS}

    # ---------------- per-domain ----------------
    res["per_domain"] = {}
    for d in domains:
        sub = A.build_index([r for r in rows if r["domain"] == d])
        ss_d = sorted(sub)
        res["per_domain"][d] = {
            "interaction": ci_entry(A.bootstrap(ss_d, lambda s2, sub=sub: A.interaction(sub, s2))),
            "divergence_low": R4(A.divergence_rate(sub, ss_d, A.LOW)),
            "divergence_high": R4(A.divergence_rate(sub, ss_d, A.HIGH)),
        }

    # ---------------- edit distance ----------------
    res["editdist"] = {}
    for label, cs in (("high", A.HIGH), ("low", A.LOW)):
        for k in (0, 4):
            res["editdist"][f"{label}_k{k}"] = ci_entry(
                A.bootstrap(seeds, lambda ss, cs=cs, k=k: A.edit_mean(idx, ss, cs, k)))

    # ---------------- divergence ----------------
    res["divergence"] = {}
    for label, cs in (("low", A.LOW), ("high", A.HIGH)):
        dec = tot = 0
        for r in rows:
            if round(r["coverage"], 1) not in cs:
                continue
            sv = [A.snap(r, k) for k in A.KS]
            for i in range(len(A.KS) - 1):
                tot += 1
                dec += (sv[i + 1] < sv[i])
        res["divergence"][f"events_{label}"] = dec
        res["divergence"][f"transitions_{label}"] = tot
        res["divergence"][f"rate_{label}"] = ci_entry(
            A.bootstrap(seeds, lambda ss, cs=cs: A.divergence_rate(idx, ss, cs)))
    res["divergence"]["gap_high_minus_low"] = ci_entry(
        A.bootstrap(seeds, lambda ss: A.divergence_gap(idx, ss)))

    # ---------------- stall ----------------
    res["stall"] = {}
    for label, cs in (("low", A.LOW), ("high", A.HIGH)):
        for field, short in (("no_accept_rounds", "no_accept"), ("no_proposal_rounds", "no_proposal")):
            res["stall"][f"{short}_rate_{label}"] = ci_entry(
                A.bootstrap(seeds, lambda ss, cs=cs, f=field: A._stall_counts(idx, ss, cs, f)))
    res["stall"]["no_accept_gap_low_minus_high"] = ci_entry(
        A.bootstrap(seeds, lambda ss: A.stall_gap(idx, ss)))

    # ---------------- integrity totals ----------------
    C = defaultdict(int)
    for r in rows:
        for kk, vv in r["stats"].items():
            if isinstance(vv, (int, float)):
                C[kk] += vv
    res["integrity"] = {k: C.get(k, 0) for k in (
        "llm_calls", "llm_errors", "parse_failures", "empty_proposals",
        "no_proposal_rounds", "no_accept_rounds", "budget_exhausted_train",
        "budget_exhausted_eval", "no_plan_train", "no_plan_eval", "plan_calls")}
    res["integrity"]["llm_seconds"] = R4(C.get("llm_seconds", 0))
    msgs = defaultdict(int)
    for r in rows:
        for m in r.get("llm_error_msgs", []):
            msgs[m] += 1
    res["integrity"]["llm_error_msgs"] = dict(msgs)

    # ---------------- stop-rule check ----------------
    job = sorted(rows, key=lambda r: r["timestamp"])
    sched = sorted(rows, key=lambda r: (DOMAIN_ORDER.index(r["domain"]),
                                        round(r["coverage"], 1), r["seed"]))
    same = [id(a) for a in job] == [id(b) for b in sched]
    ts_unique = len({r["timestamp"] for r in rows}) == len(rows)
    res["stop_rule"] = {
        "job_order_definition": "rows sorted by per-row completion `timestamp` (UTC, 1 s); "
                                "equals the domain-sequential schedule blocks->gripper->logistics, "
                                "coverage ascending, seed 0..19 ascending",
        "timestamp_order_equals_domain_sequential_schedule": same,
        "timestamps_unique": ts_unique,
        "first_timestamp": job[0]["timestamp"], "last_timestamp": job[-1]["timestamp"],
        "rate_denominators": "per_run = field count summed over the half / number of runs in "
                             "that half (pre-committed 'per run' rate); per_llm_call = same "
                             "count / llm_calls in that half (secondary view); runs_with_any = "
                             "number of runs with count > 0",
        "pooled_first_vs_second_half": half_rates(job),
        "within_domain": {d: half_rates([r for r in job if r["domain"] == d]) for d in DOMAIN_ORDER},
    }
    OUT.write_text(json.dumps(res, indent=2) + "\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
