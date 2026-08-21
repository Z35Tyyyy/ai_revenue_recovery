#!/usr/bin/env python3
"""Train the recovery-probability + optimal-timing models and save them to models/."""

from __future__ import annotations

import json

from rich.console import Console
from rich.table import Table

from recovery.config import get_settings
from recovery.ml.train import train_all

console = Console()


def main() -> None:
    settings = get_settings()
    settings.ensure_dirs()

    console.rule("[bold]AI Revenue Recovery · model training")
    metrics = train_all(settings.data_dir, settings.model_dir, seed=settings.seed)

    table = Table(title="Held-out validation metrics", show_lines=False)
    table.add_column("model", style="cyan")
    table.add_column("rows (train/val)")
    table.add_column("pos. rate")
    table.add_column("ROC AUC", style="green")
    table.add_column("avg precision", style="green")
    for name, m in metrics.items():
        table.add_row(
            name,
            f"{m['n_train']:,} / {m['n_val']:,}",
            f"{m['positive_rate']:.1%}",
            f"{m['roc_auc']:.3f}",
            f"{m['avg_precision']:.3f}",
        )
    console.print(table)

    (settings.model_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))
    console.print(f"  ✓ models + metrics → [green]{settings.model_dir}[/]")
    console.rule("[green]done")


if __name__ == "__main__":
    main()
