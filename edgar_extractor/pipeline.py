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


def reconcile_extraction(extraction: FilingExtraction, model: str) -> FilingExtraction:
    """
    Final reconciliation pass - merge batched/split results and resolve conflicts.
    
    Args:
        extraction: FilingExtraction with potentially batched/split results
        model: Model name for reconciliation
        
    Returns:
        Reconciled FilingExtraction
    """
    # Reconcile table batch results
    for table in extraction.tables:
        if table.extracted_data and isinstance(table.extracted_data, dict):
            if "batch_results" in table.extracted_data:
                # Merge batched table results
                merged = _merge_table_batches(table.extracted_data["batch_results"])
                table.extracted_data = merged
                table.confidence = 0.75  # Adjusted confidence for merged results
    
    # Reconcile prose chunk results
    for prose in extraction.prose_chunks:
        if prose.extracted_data and isinstance(prose.extracted_data, dict):
            if "chunk_results" in prose.extracted_data:
                # Merge split prose results
                merged = _merge_prose_chunks(prose.extracted_data["chunk_results"])
                prose.extracted_data = merged
                prose.confidence = 0.75  # Adjusted confidence for merged results
    
    return extraction


def _merge_table_batches(batch_results: list) -> dict:
    """Merge results from table batch extraction."""
    merged = {}
    for batch in batch_results:
        if isinstance(batch, dict):
            merged.update(batch)
    return merged


def _merge_prose_chunks(chunk_results: list) -> dict:
    """Merge results from prose chunk extraction."""
    merged = {}
    for chunk in chunk_results:
        if isinstance(chunk, dict):
            merged.update(chunk)
    return merged


def _load_env() -> None:
    """Load LLM config from .env."""
    load_dotenv(".env")


def main(input_path: Path = None):
    """CLI entry point for the extraction pipeline."""
    _load_env()
    
    if input_path is None:
        if len(sys.argv) < 2:
            console.print("[red]Error: Please provide a filing HTML file path or directory[/red]")
            console.print("Usage: python main.py <filing.html or directory>")
            sys.exit(1)
        input_path = Path(sys.argv[1])
    
    if not input_path.exists():
        console.print(f"[red]Error: Path not found: {input_path}[/red]")
        sys.exit(1)
    
    model = os.getenv("MODEL", "gpt-5.4-mini")
    
    # Collect files to process
    if input_path.is_file():
        filing_paths = [input_path]
    elif input_path.is_dir():
        filing_paths = sorted(input_path.glob("*.html"))
        console.print(f"[bold blue]Found {len(filing_paths)} HTML files in {input_path}[/bold blue]")
    else:
        console.print(f"[red]Error: Path is neither a file nor a directory: {input_path}[/red]")
        sys.exit(1)
    
    if not filing_paths:
        console.print("[red]Error: No HTML files found[/red]")
        sys.exit(1)
    
    # Process each filing
    output_dir = Path("data/outputs")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    console.print(f"[dim]Model: {model}[/dim]\n")
    
    for filing_path in filing_paths:
        console.print(f"[bold blue]Processing: {filing_path.name}[/bold blue]")
        
        try:
            extraction = run_pipeline(filing_path, model)
            
            # Write output
            output_path = output_dir / f"{filing_path.stem}.json"
            to_json(extraction, output_path)
            
            console.print(f"[green]✓ Output written to: {output_path}[/green]\n")
            
        except Exception as e:
            console.print(f"[red]Error processing {filing_path.name}: {e}[/red]")
            import traceback
            console.print(traceback.format_exc())
            console.print()
            continue


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
            result = extract_from_table(table, model, cost_tracker)
            table.extracted_data = result["extracted_data"]
            table.confidence = calculate_confidence(result["extracted_data"], "table")
            extraction.tables.append(table)
            progress.update(table_task, advance=1)
        
        # Extract prose
        prose_task = progress.add_task("Extracting prose...", total=len(prose_chunks))
        for prose in prose_chunks:
            result = extract_from_prose(prose, model, cost_tracker)
            prose.extracted_data = result["extracted_data"]
            prose.confidence = calculate_confidence(result["extracted_data"], "prose")
            extraction.prose_chunks.append(prose)
            progress.update(prose_task, advance=1)
    
    # Step 3: Validate
    with console.status("[bold green]Validating extraction..."):
        validation_report = validate_extraction(extraction)
    
    extraction.extraction_metadata["validation"] = validation_report
    
    console.print(f"[green]✓ Overall confidence: {validation_report['overall_confidence']:.2%}[/green]")
    
    # Step 4: Reconcile batched/split results
    with console.status("[bold green]Reconciling extraction results..."):
        extraction = reconcile_extraction(extraction, model)
    
    console.print(f"[green]✓ Reconciliation complete[/green]")
    
    # Step 5: Cost report
    console.print(f"\n[yellow]{cost_tracker.get_report()}[/yellow]")
    
    return extraction


if __name__ == "__main__":
    main()
