"""Pipeline orchestration - ingest → extract → validate → serialize."""

import os
import sys
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .schema import FilingExtraction
from .ingest import parse_html
from .extract import extract_from_table, extract_from_prose, extract_from_guidance
from .validate import validate_extraction, calculate_confidence
from .serialize import to_json
from .cost import CostTracker

console = Console()


def main():
    """CLI entry point for the extraction pipeline."""
    load_dotenv()
    
    if len(sys.argv) < 2:
        console.print("[red]Error: Please provide a filing HTML file path[/red]")
        console.print("Usage: python main.py <filing.html>")
        sys.exit(1)
    
    filing_path = Path(sys.argv[1])
    
    if not filing_path.exists():
        console.print(f"[red]Error: File not found: {filing_path}[/red]")
        sys.exit(1)
    
    model = os.getenv("MODEL", "gpt-5.4-mini")
    
    console.print(f"[bold blue]Processing: {filing_path}[/bold blue]")
    console.print(f"[dim]Model: {model}[/dim]")
    
    try:
        extraction = run_pipeline(filing_path, model)
        
        # Write output
        output_dir = Path("data/gitignored/outputs")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = output_dir / f"{filing_path.stem}.json"
        to_json(extraction, output_path)
        
        console.print(f"[green]✓ Output written to: {output_path}[/green]")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        console.print(traceback.format_exc())
        sys.exit(1)


def run_pipeline(filing_path: Path, model: str) -> FilingExtraction:
    """
    Run the complete extraction pipeline.
    
    Args:
        filing_path: Path to HTML filing
        model: Model name for extraction
        
    Returns:
        FilingExtraction object with all extracted data
    """
    cost_tracker = CostTracker()
    
    # Step 1: Ingest
    with console.status("[bold green]Parsing HTML..."):
        html_content = filing_path.read_text(encoding="utf-8")
        tables, prose_chunks = parse_html(html_content)
    
    console.print(f"[green]✓ Found {len(tables)} tables, {len(prose_chunks)} prose chunks[/green]")
    
    # Step 2: Extract from tables
    extraction = FilingExtraction(
        filing_id=filing_path.stem,
        extraction_metadata={"model": model, "source_file": str(filing_path)}
    )
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        
        # Extract tables
        table_task = progress.add_task("Extracting tables...", total=len(tables))
        for table in tables:
            result = extract_from_table(table, model)
            table.extracted_data = result["extracted_data"]
            table.confidence = calculate_confidence(result["extracted_data"], "table")
            extraction.tables.append(table)
            progress.update(table_task, advance=1)
        
        # Extract prose
        prose_task = progress.add_task("Extracting prose...", total=len(prose_chunks))
        for prose in prose_chunks:
            result = extract_from_prose(prose, model)
            prose.extracted_data = result["extracted_data"]
            prose.confidence = calculate_confidence(result["extracted_data"], "prose")
            extraction.prose_chunks.append(prose)
            progress.update(prose_task, advance=1)
    
    # Step 3: Validate
    with console.status("[bold green]Validating extraction..."):
        validation_report = validate_extraction(extraction)
    
    extraction.extraction_metadata["validation"] = validation_report
    
    console.print(f"[green]✓ Overall confidence: {validation_report['overall_confidence']:.2%}[/green]")
    
    # Step 4: Cost report
    console.print(f"\n[yellow]{cost_tracker.get_report()}[/yellow]")
    
    return extraction


if __name__ == "__main__":
    main()
