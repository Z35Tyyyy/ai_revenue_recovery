#!/usr/bin/env python3
"""Live recovery demo: diagnose a failed payment, decide, and create a REAL
Razorpay test-mode payment link with a personalised, localised dunning message.

With Razorpay test keys in .env this creates an actual payable test Payment Link.
Without keys it uses a faithful mock link. With an Anthropic key the message is
Claude-authored; otherwise a quality multilingual template is used. Either way the
agent's full reasoning trace is printed.

    python scripts/demo_live.py --reason insufficient_funds
"""

from __future__ import annotations

import argparse
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from recovery.config import get_settings
from recovery.domain.models import format_inr
from recovery.eval.harness import build_case
from recovery.llm.dunning import DunningGenerator
from recovery.ml.models import RecoveryModel, TimingModel
from recovery.policy.bandit import ContextualBandit
from recovery.policy.engine import RecoveryEngine
from recovery.razorpay.client import get_gateway
from recovery.razorpay.executor import RazorpayExecutor
from recovery.simulation.generator import Population, generate_population

# Force UTF-8 output so rich never crashes on ✓/→/₹ on a legacy Windows console.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

console = Console()


def _load_population(settings) -> Population:
    path = settings.data_dir / "population.json"
    if path.exists():
        return Population.load(path)
    return generate_population(n_customers=500, n_failures=1500, seed=7)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--reason", default="insufficient_funds")
    args = p.parse_args()

    settings = get_settings()
    rm = RecoveryModel.load(settings.model_dir)
    tm = TimingModel.load(settings.model_dir)
    pop = _load_population(settings)

    try:
        failure = next(f for f in pop.failures if f.reason_code == args.reason)
    except StopIteration:
        console.print(f"[red]No failure with reason '{args.reason}'.[/]")
        return
    # Treat the failure as if it just happened, so the recommended retry slot is in
    # the future (reads naturally in a live demo).
    from datetime import datetime, timezone

    failure = failure.model_copy(update={"occurred_at": datetime.now(timezone.utc)})
    case = build_case(failure, pop.customers, pop.subscriptions)

    console.rule("[bold]AI Revenue Recovery · live demo")
    cust = case.customer
    console.print(
        Panel(
            f"[bold]{format_inr(failure.amount_paise)}[/] failed on "
            f"[cyan]{case.subscription.plan_name}[/] · reason [yellow]{failure.reason_code}[/]\n"
            f"Customer {cust.id} · {cust.city} · lang [cyan]{cust.language.value}[/] · "
            f"prefers [cyan]{cust.preferred_channel.value}[/] · "
            f"tenure {cust.tenure_months}mo · salary day {cust.salary_day}",
            title="Failed recurring charge",
        )
    )

    engine = RecoveryEngine(rm, tm, bandit=ContextualBandit(seed=settings.seed))
    decision = engine.plan(case)

    # ranked candidate actions
    table = Table(title="Agent's candidate actions (by expected recovered ₹)")
    table.add_column("action", style="cyan")
    table.add_column("P(success)", justify="right")
    table.add_column("expected ₹", justify="right", style="green")
    table.add_column("when", justify="right")
    for c in decision.candidates:
        table.add_row(
            c.action_type.value,
            f"{c.prob:.2f}",
            format_inr(int(c.ev_paise)),
            c.label,
        )
    console.print(table)

    console.print(Panel("\n".join(f"• {line}" for line in case.trace), title="Reasoning trace"))
    console.print(
        f"[bold green]Decision:[/] {decision.action_type.value} "
        f"(P={decision.prob:.2f}, expected {format_inr(int(decision.ev_paise))})"
    )

    # create a real (or mock) test-mode payment link + personalised message
    gateway = get_gateway(settings)
    executor = RazorpayExecutor(gateway)
    link = executor.create_recovery_link(case)
    generator = DunningGenerator()
    message = generator.generate(case, cust.preferred_channel, cust.language, link.short_url)

    console.print(
        Panel(
            message.text,
            title=(
                f"Dunning message · {cust.language.value} · via {message.channel.value} · "
                f"authored by {message.authored_by}"
            ),
        )
    )
    kind = "LIVE Razorpay test-mode" if not link.is_mock else "MOCK (no keys configured)"
    console.print(
        Panel(
            f"[bold]{link.short_url}[/]\n"
            f"link id: {link.id} · amount {format_inr(link.amount_paise)} · {kind}\n"
            "Recovery is confirmed asynchronously by the payment.captured webhook.",
            title="Payment link",
        )
    )
    console.rule("[green]done")


if __name__ == "__main__":
    main()
