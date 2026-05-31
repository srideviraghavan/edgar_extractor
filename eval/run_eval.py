"""Run evaluation comparing pipeline outputs against golden JSONs."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

from fact_metrics import compare_facts
from metrics import calculate_exact_match, calculate_f1, compare_structures

console = Console()
err_console = Console(stderr=True)
REPO_ROOT = Path(__file__).resolve().parent.parent
FACT_F1_THRESHOLD = 0.7


def main() -> None:
    """Run evaluation on all outputs against golden files."""
    if len(sys.argv) < 2:
        err_console.print("[red]Error: Please specify outputs directory[/red]")
        err_console.print("Usage: python run_eval.py <outputs_dir>")
        sys.exit(1)

    outputs_dir = Path(sys.argv[1])
    if not outputs_dir.is_absolute():
        outputs_dir = (Path.cwd() / outputs_dir).resolve()

    golden_dir = REPO_ROOT / "data" / "golden"

    if not outputs_dir.exists():
        err_console.print(f"[red]Error: Outputs directory not found: {outputs_dir}[/red]")
        sys.exit(1)

    if not golden_dir.exists():
        err_console.print(f"[red]Error: Golden directory not found: {golden_dir}[/red]")
        err_console.print("[yellow]Run: python eval/build_golden.py[/yellow]")
        sys.exit(1)

    console.print(f"[bold blue]Evaluating outputs from: {outputs_dir}[/bold blue]")
    console.print(f"[dim]Golden files in: {golden_dir}[/dim]\n")

    output_files = list(outputs_dir.glob("*.json"))
    if not output_files:
        err_console.print("[yellow]No output files found to evaluate[/yellow]")
        sys.exit(1)

    results: list[dict[str, Any]] = []
    for output_file in output_files:
        golden_file = golden_dir / output_file.name
        if not golden_file.exists():
            err_console.print(f"[yellow]Warning: No golden file for {output_file.name}[/yellow]")
            continue
        results.append(evaluate_file(output_file, golden_file))

    if not results:
        err_console.print("[yellow]No files evaluated (no golden matches)[/yellow]")
        print_summary([])
        sys.exit(1)

    print_summary(results)

    avg_fact_f1 = sum(r["fact_f1"] for r in results) / len(results)
    if avg_fact_f1 < FACT_F1_THRESHOLD:
        err_console.print(
            f"\n[red]Average fact F1 {avg_fact_f1:.3f} is below threshold {FACT_F1_THRESHOLD}[/red]"
        )
        sys.exit(1)


def evaluate_file(output_file: Path, golden_file: Path) -> dict[str, Any]:
    """Evaluate a single output file against its golden counterpart."""
    with open(output_file, "r", encoding="utf-8") as f:
        output = json.load(f)
    with open(golden_file, "r", encoding="utf-8") as f:
        golden = json.load(f)

    fact_scores = compare_facts(output, golden)
    is_golden_facts = "key_metrics" in golden and "tables" not in golden

    f1_score = fact_scores["fact_f1"] if is_golden_facts else calculate_f1(output, golden)
    exact_match = calculate_exact_match(output, golden) if not is_golden_facts else False
    structure_match = (
        _structure_from_facts(fact_scores)
        if is_golden_facts
        else compare_structures(output, golden)
    )

    result = {
        "file": output_file.name,
        "f1_score": f1_score,
        "fact_f1": fact_scores["fact_f1"],
        "required_metric_recall": fact_scores["required_metric_recall"],
        "exact_match": exact_match,
        "structure_match": structure_match,
        "tables_ok": fact_scores["tables_ok"],
        "guidance_ok": fact_scores["guidance_ok"],
        "metric_details": fact_scores["metrics"],
    }

    console.print(f"[green]OK[/green] {output_file.name}")
    console.print(
        f"  Fact F1: {fact_scores['fact_f1']:.3f} | "
        f"Required recall: {fact_scores['required_metric_recall']:.3f} | "
        f"Tables: {'OK' if fact_scores['tables_ok'] else 'MISS'} | "
        f"Guidance: {'OK' if fact_scores['guidance_ok'] else 'MISS'}"
    )
    for metric_name, detail in fact_scores["metrics"].items():
        status = "OK" if detail["matched"] else "MISS"
        found = detail["found"] if detail["found"] is not None else "n/a"
        console.print(
            f"    {status} {metric_name}: expected {detail['expected']}, found {found}"
        )

    return result


def _structure_from_facts(fact_scores: dict[str, Any]) -> float:
    """Derive a structure score from fact-based structural checks."""
    checks = [
        1.0 if fact_scores["tables_ok"] else 0.0,
        1.0 if fact_scores["guidance_ok"] else 0.0,
        fact_scores["segment_recall"],
    ]
    return sum(checks) / len(checks)


def print_summary(results: list[dict[str, Any]]) -> None:
    """Print evaluation summary table."""
    if not results:
        console.print("[yellow]No results to display[/yellow]")
        return

    table = Table(title="Evaluation Summary")
    table.add_column("File", style="cyan")
    table.add_column("Fact F1", style="green")
    table.add_column("Req Recall", style="green")
    table.add_column("Tables", style="blue")
    table.add_column("Guidance", style="blue")
    table.add_column("Structure", style="magenta")

    for result in results:
        table.add_row(
            result["file"],
            f"{result['fact_f1']:.3f}",
            f"{result['required_metric_recall']:.3f}",
            "OK" if result["tables_ok"] else "MISS",
            "OK" if result["guidance_ok"] else "MISS",
            f"{result['structure_match']:.3f}",
        )

    n = len(results)
    table.add_row(
        "[bold]AVERAGE[/bold]",
        f"[bold]{sum(r['fact_f1'] for r in results) / n:.3f}[/bold]",
        f"[bold]{sum(r['required_metric_recall'] for r in results) / n:.3f}[/bold]",
        f"{sum(1 for r in results if r['tables_ok'])}/{n}",
        f"{sum(1 for r in results if r['guidance_ok'])}/{n}",
        f"[bold]{sum(r['structure_match'] for r in results) / n:.3f}[/bold]",
    )

    console.print(table)
    exact_matches = sum(1 for r in results if r["exact_match"])
    console.print(f"\n[bold]Exact Matches:[/bold] {exact_matches}/{n}")


if __name__ == "__main__":
    main()
