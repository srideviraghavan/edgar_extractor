"""Run evaluation comparing pipeline outputs against golden JSONs."""

import json
import sys
from pathlib import Path
from typing import Dict, Any
from rich.console import Console
from rich.table import Table

from metrics import calculate_f1, calculate_exact_match, compare_structures

console = Console()


def main():
    """Run evaluation on all outputs against golden files."""
    if len(sys.argv) < 2:
        console.print("[red]Error: Please specify outputs directory[/red]")
        console.print("Usage: python run_eval.py <outputs_dir>")
        sys.exit(1)
    
    outputs_dir = Path(sys.argv[1])
    golden_dir = Path("data/gitignored/golden")
    
    if not outputs_dir.exists():
        console.print(f"[red]Error: Outputs directory not found: {outputs_dir}[/red]")
        sys.exit(1)
    
    if not golden_dir.exists():
        console.print(f"[red]Error: Golden directory not found: {golden_dir}[/red]")
        console.print("[yellow]Please create golden JSONs for evaluation[/yellow]")
        sys.exit(1)
    
    console.print(f"[bold blue]Evaluating outputs from: {outputs_dir}[/bold blue]")
    console.print(f"[dim]Golden files in: {golden_dir}[/dim]\n")
    
    # Find all output files
    output_files = list(outputs_dir.glob("*.json"))
    
    if not output_files:
        console.print("[yellow]No output files found to evaluate[/yellow]")
        sys.exit(0)
    
    results = []
    
    for output_file in output_files:
        golden_file = golden_dir / output_file.name
        
        if not golden_file.exists():
            console.print(f"[yellow]Warning: No golden file for {output_file.name}[/yellow]")
            continue
        
        result = evaluate_file(output_file, golden_file)
        results.append(result)
    
    # Print summary table
    print_summary(results)


def evaluate_file(output_file: Path, golden_file: Path) -> Dict[str, Any]:
    """Evaluate a single output file against its golden counterpart."""
    with open(output_file, "r") as f:
        output = json.load(f)
    
    with open(golden_file, "r") as f:
        golden = json.load(f)
    
    # Calculate metrics
    f1_score = calculate_f1(output, golden)
    exact_match = calculate_exact_match(output, golden)
    structure_match = compare_structures(output, golden)
    
    result = {
        "file": output_file.name,
        "f1_score": f1_score,
        "exact_match": exact_match,
        "structure_match": structure_match,
    }
    
    console.print(f"[green]✓[/green] {output_file.name}")
    console.print(f"  F1: {f1_score:.3f} | Exact Match: {exact_match} | Structure: {structure_match:.3f}")
    
    return result


def print_summary(results: list[Dict[str, Any]]) -> None:
    """Print evaluation summary table."""
    if not results:
        console.print("[yellow]No results to display[/yellow]")
        return
    
    table = Table(title="Evaluation Summary")
    table.add_column("File", style="cyan")
    table.add_column("F1 Score", style="green")
    table.add_column("Exact Match", style="yellow")
    table.add_column("Structure", style="blue")
    
    avg_f1 = 0.0
    avg_structure = 0.0
    exact_matches = 0
    
    for result in results:
        table.add_row(
            result["file"],
            f"{result['f1_score']:.3f}",
            "✓" if result["exact_match"] else "✗",
            f"{result['structure_match']:.3f}",
        )
        avg_f1 += result["f1_score"]
        avg_structure += result["structure_match"]
        if result["exact_match"]:
            exact_matches += 1
    
    console.print(table)
    
    # Print averages
    n = len(results)
    console.print(f"\n[bold]Average F1 Score:[/bold] {avg_f1 / n:.3f}")
    console.print(f"[bold]Average Structure Match:[/bold] {avg_structure / n:.3f}")
    console.print(f"[bold]Exact Matches:[/bold] {exact_matches}/{n} ({exact_matches / n:.1%})")


if __name__ == "__main__":
    main()
