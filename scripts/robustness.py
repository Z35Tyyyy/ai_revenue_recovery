#!/usr/bin/env python3
"""Robustness check: is the engine's uplift a property of the method, or a lucky seed?

Re-runs the held-out evaluation across several *independent* holdout populations
(different seeds → different customers, failures, and hidden latents) and reports the
engine's recovery rate and its uplift over the fixed-retry default as mean ± std.
A tight spread is evidence the lift transfers, not overfits to one simulated world.
"""

from __future__ import annotations

import argparse
import statistics
import sys

from rich.console import Console
from rich.table import Table

from recovery.config import get_settings
from recovery.eval.harness import evaluate
from recovery.ml.models import RecoveryModel, TimingModel
from recovery.simulation.generator import generate_population

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

console = Console()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", default=[9999, 1234, 4242, 8080])
    ap.add_argument("--customers", type=int, default=1500)
    ap.add_argument("--failures", type=int, default=3000)
    args = ap.parse_args()

    settings = get_settings()
    rm = RecoveryModel.load(settings.model_dir)
    tm = TimingModel.load(settings.model_dir)

    rows, eng_rates, uplifts = [], [], []
    for seed in args.seeds:
        pop = generate_population(
            n_customers=args.customers, n_failures=args.failures, seed=seed
        )
        res = evaluate(pop, rm, tm, seed=seed)
        eng = res.policies["engine"].recovery_rate
        fixed = res.policies["fixed_retry"].recovery_rate
        up = res.uplift_vs("fixed_retry", "engine")["recovery_rate_abs"]
        eng_rates.append(eng)
        uplifts.append(up)
        rows.append((seed, eng, fixed, up))
        console.print(
            f"  seed {seed}: engine {eng * 100:.1f}%  fixed {fixed * 100:.1f}%  "
            f"uplift +{up * 100:.1f} pts"
        )

    table = Table(title="Robustness across independent holdout worlds")
    table.add_column("seed")
    table.add_column("engine", justify="right")
    table.add_column("fixed retry", justify="right")
    table.add_column("uplift", justify="right")
    for seed, eng, fixed, up in rows:
        table.add_row(str(seed), f"{eng * 100:.1f}%", f"{fixed * 100:.1f}%", f"+{up * 100:.1f} pts")
    console.print(table)

    console.print(
        f"[bold]Engine recovery[/]: {statistics.mean(eng_rates) * 100:.1f}% "
        f"± {statistics.pstdev(eng_rates) * 100:.1f}  |  "
        f"[bold]Uplift[/]: +{statistics.mean(uplifts) * 100:.1f} "
        f"± {statistics.pstdev(uplifts) * 100:.1f} pts "
        f"across {len(args.seeds)} worlds"
    )


if __name__ == "__main__":
    main()
