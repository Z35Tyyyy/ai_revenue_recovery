#!/usr/bin/env python3
"""Generate the synthetic population + observational training logs.

Writes to ``data/``:
    population.json      the customer / subscription / failure population
    train_timing.csv     retry probes for the optimal-timing model
    train_cases.csv      per-case labels for the recovery-probability model

Runs with zero credentials. Fully seeded and reproducible.
"""

from __future__ import annotations

import argparse
import sys

from rich.console import Console

from recovery.config import get_settings
from recovery.simulation.generator import generate_population
from recovery.simulation.history import build_training_logs

# Windows legacy consoles are cp1252 and make rich crash on ✓/→/₹. Force UTF-8
# output (rich reads sys.stdout lazily), replacing anything unrenderable.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

console = Console()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--customers", type=int, default=4000)
    p.add_argument("--failures", type=int, default=12000)
    p.add_argument("--seed", type=int, default=None)
    args = p.parse_args()

    settings = get_settings()
    settings.ensure_dirs()
    seed = args.seed if args.seed is not None else settings.seed

    console.rule("[bold]AI Revenue Recovery · data generation")
    console.print(
        f"Population: [cyan]{args.customers}[/] customers · "
        f"[cyan]{args.failures}[/] failed charges · seed=[cyan]{seed}[/]"
    )

    pop = generate_population(
        n_customers=args.customers, n_failures=args.failures, seed=seed
    )
    pop_path = settings.data_dir / "population.json"
    pop.save(pop_path)
    console.print(f"  ✓ population → [green]{pop_path}[/]")

    console.print("Simulating historical recovery logs (randomised logging policy)…")
    timing, cases = build_training_logs(pop, seed=seed)

    timing_path = settings.data_dir / "train_timing.csv"
    cases_path = settings.data_dir / "train_cases.csv"
    timing.to_csv(timing_path, index=False)
    cases.to_csv(cases_path, index=False)

    console.print(
        f"  ✓ timing probes: [cyan]{len(timing):,}[/] rows "
        f"(retry-success rate {timing.label.mean():.1%}) → [green]{timing_path}[/]"
    )
    console.print(
        f"  ✓ case labels:   [cyan]{len(cases):,}[/] rows "
        f"(recovered rate {cases.label.mean():.1%}) → [green]{cases_path}[/]"
    )
    console.rule("[green]done")


if __name__ == "__main__":
    main()
