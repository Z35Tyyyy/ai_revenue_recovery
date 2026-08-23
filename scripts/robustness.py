#!/usr/bin/env python3
"""Robustness check: is the engine's uplift a property of the method, or a rigged world?

Re-runs the held-out evaluation across many *independent* worlds — every Live failure
scenario (payday crunch, fraud spike, mandate lapses, expired-card wave, balanced) at
several seeds, so the customers, failures, hidden latents AND the failure-reason mix all
change in ways the policy never chose. It reports how many worlds the engine wins and the
uplift over the fixed-retry default as mean ± std, and writes reports/robustness.json for
the dashboard. A win in every world is the answer to "you tuned the simulator to win."
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys

from recovery.config import get_settings
from recovery.eval.harness import evaluate
from recovery.live import SCENARIOS
from recovery.ml.models import RecoveryModel, TimingModel
from recovery.simulation.generator import generate_population

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", default=[9999, 4242])
    ap.add_argument("--customers", type=int, default=1200)
    ap.add_argument("--failures", type=int, default=2400)
    args = ap.parse_args()

    settings = get_settings()
    rm = RecoveryModel.load(settings.model_dir)
    tm = TimingModel.load(settings.model_dir)

    worlds, eng_rates, uplifts = [], [], []
    for scenario, mix in SCENARIOS.items():
        for seed in args.seeds:
            pop = generate_population(
                n_customers=args.customers,
                n_failures=args.failures,
                seed=seed,
                reason_mix=mix,
            )
            res = evaluate(pop, rm, tm, seed=seed)
            eng = res.policies["engine"].recovery_rate
            fixed = res.policies["fixed_retry"].recovery_rate
            up = res.uplift_vs("fixed_retry", "engine")["recovery_rate_abs"]
            eng_rates.append(eng)
            uplifts.append(up)
            worlds.append(
                {
                    "world": scenario,
                    "seed": seed,
                    "engine_rate": round(eng, 4),
                    "fixed_rate": round(fixed, 4),
                    "uplift_pts": round(up * 100, 2),
                    "engine_wins": bool(up > 0),
                }
            )
            print(
                f"  {scenario:20} seed {seed}: engine {eng * 100:5.1f}%  "
                f"fixed {fixed * 100:5.1f}%  uplift +{up * 100:4.1f} pts"
            )

    wins = sum(1 for w in worlds if w["engine_wins"])
    summary = {
        "n_worlds": len(worlds),
        "engine_wins": wins,
        "uplift_mean_pts": round(statistics.mean(uplifts) * 100, 2),
        "uplift_std_pts": round(statistics.pstdev(uplifts) * 100, 2),
        "uplift_min_pts": round(min(uplifts) * 100, 2),
        "engine_rate_mean": round(statistics.mean(eng_rates), 4),
        "seeds": args.seeds,
    }
    out = {"summary": summary, "worlds": worlds}

    path = settings.report_dir / "robustness.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")

    print(
        f"\nEngine wins {wins}/{len(worlds)} worlds  |  "
        f"uplift +{summary['uplift_mean_pts']} ± {summary['uplift_std_pts']} pts "
        f"(min +{summary['uplift_min_pts']})  ->  {path}"
    )


if __name__ == "__main__":
    main()
