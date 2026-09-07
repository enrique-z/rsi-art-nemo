#!/usr/bin/env python3
"""
verify_independent.py -- recompute the headline numbers with DELIBERATELY separate
code and compare against the ledger.

Lesson 01: "A stamped-cell guard PASSING is NOT proof the number is right. The guard
confirms the tex matches the manifest -- not that the manifest matches reality.
Recompute independently."

This file shares NO functions with aggregate.py: it re-reads the raw per-run JSONL,
re-derives every quantity from first principles with its own loops, and re-runs its
own bootstrap with a different RNG seed.  Point estimates must match exactly (they
are deterministic functions of the data); CIs must merely be close, since they come
from an independent resampling stream.

Exit 0 = agreement, 1 = drift.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVID = HERE.parent / "evidence"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default=str(EVID / "runs"))
    ap.add_argument("--tag", default="primary")
    ap.add_argument("--claim-prefix", default="")
    ap.add_argument("--boot", type=int, default=10000)
    ap.add_argument("--ci-tol", type=float, default=0.05)
    a = ap.parse_args()

    # ---- independent load: flat list of (seed, domain, coverage, [s0,s1,s2,s4], [e0..]) ----
    recs = []
    for f in sorted(Path(a.runs).glob("cell_*.jsonl")):
        with open(f) as fh:
            for line in fh:
                if not line.strip():
                    continue
                d = json.loads(line)
                sn = d["snapshots"]
                recs.append((
                    d["seed"], d["domain"], round(d["coverage"], 1),
                    [sn[x]["heldout_success"] for x in ("0", "1", "2", "4")],
                    [sn[x]["edit_distance"] for x in ("0", "1", "2", "4")],
                ))
    if not recs:
        print("no records"); return 1
    seed_list = sorted({r[0] for r in recs})

    LOWC, HIGHC = {0.2, 0.4}, {0.8, 1.0}

    def inter_of(seed_multiset):
        """interaction = mean(s4-s1 | c high) - mean(s4-s1 | c low), over given seeds."""
        hi, lo = [], []
        cnt = {}
        for s in seed_multiset:
            cnt[s] = cnt.get(s, 0) + 1
        for (sd, dom, cov, ss, _ee) in recs:
            m = cnt.get(sd, 0)
            if not m:
                continue
            d = ss[3] - ss[1]
            if cov in HIGHC:
                hi.extend([d] * m)
            elif cov in LOWC:
                lo.extend([d] * m)
        if not hi or not lo:
            return None
        return sum(hi) / len(hi) - sum(lo) / len(lo)

    def divrate_of(seed_multiset, covset):
        cnt = {}
        for s in seed_multiset:
            cnt[s] = cnt.get(s, 0) + 1
        dec = tot = 0
        for (sd, dom, cov, ss, _ee) in recs:
            m = cnt.get(sd, 0)
            if not m or cov not in covset:
                continue
            for i in range(3):
                tot += m
                if ss[i + 1] < ss[i]:
                    dec += m
        return dec / tot if tot else None

    def cellmean_of(seed_multiset, cov, ki):
        cnt = {}
        for s in seed_multiset:
            cnt[s] = cnt.get(s, 0) + 1
        vals = []
        for (sd, dom, c, ss, _ee) in recs:
            m = cnt.get(sd, 0)
            if m and c == cov:
                vals.extend([ss[ki]] * m)
        return sum(vals) / len(vals) if vals else None

    def boot(fn):
        rng = random.Random(987654321)          # different stream from aggregate.py
        pt = fn(seed_list)
        reps = []
        n = len(seed_list)
        for _ in range(a.boot):
            draw = [seed_list[rng.randrange(n)] for _ in range(n)]
            v = fn(draw)
            if v is not None:
                reps.append(v)
        reps.sort()
        return pt, reps[int(0.025 * len(reps))], reps[int(0.975 * len(reps)) - 1]

    led = {}
    for l in (EVID / f"nemo_plan_repair_coverage_{a.tag}_ledger.jsonl").read_text().splitlines():
        if l.strip():
            r = json.loads(l)
            led[r["claim_id"]] = r

    P = a.claim_prefix
    checks, bad = [], 0

    def cmp(key, pt, lo=None, hi=None):
        nonlocal bad
        row = led.get(P + key)
        if row is None:
            print(f"  MISSING  {P+key}"); bad += 1; return
        dp = abs(float(row["value"]) - round(pt, 4))
        ok = dp <= 1e-4
        line = f"  {'OK ' if ok else 'DRIFT'}  {P+key:46s} ledger={row['value']:+.4f} indep={pt:+.4f}"
        if lo is not None and row["ci_low"] is not None:
            dci = max(abs(row["ci_low"] - lo), abs(row["ci_high"] - hi))
            cok = dci <= a.ci_tol
            ok = ok and cok
            line += (f"  CI ledger=[{row['ci_low']:+.3f},{row['ci_high']:+.3f}] "
                     f"indep=[{lo:+.3f},{hi:+.3f}] {'ok' if cok else 'WIDE'}")
        if not ok:
            bad += 1
        checks.append(line)
        print(line)

    print(f"[verify] {len(recs)} run records, {len(seed_list)} seeds, tag={a.tag}")
    pt, lo, hi = boot(inter_of)
    cmp("primary::interaction_coverage_x_k", pt, lo, hi)
    for lab, cs in (("low", LOWC), ("high", HIGHC)):
        pt, lo, hi = boot(lambda ss, cs=cs: divrate_of(ss, cs))
        cmp(f"falsifier::divergence_rate_{lab}", pt, lo, hi)
    pt, lo, hi = boot(lambda ss: (divrate_of(ss, HIGHC) - divrate_of(ss, LOWC))
                      if (divrate_of(ss, HIGHC) is not None and divrate_of(ss, LOWC) is not None) else None)
    cmp("falsifier::divergence_gap_high_minus_low", pt, lo, hi)
    for cov in sorted({r[2] for r in recs}):
        for ki, k in enumerate((0, 1, 2, 4)):
            cmp(f"success::c{cov:.1f}_k{k}", cellmean_of(seed_list, cov, ki))

    print(f"[verify] {len(checks)} comparisons, {bad} disagreements")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
