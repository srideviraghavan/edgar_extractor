"""CLI entry point for EDGAR extractor."""

import sys
from pathlib import Path

from edgar_extractor.pipeline import main as pipeline_main


def main():
    """Entry point for the CLI."""
    if len(sys.argv) < 2:
        print("Usage: python main.py <filing.html>")
        print("Example: python main.py data/raw/filing.html")
        sys.exit(1)
    
    filing_path = Path(sys.argv[1])
    
    if not filing_path.exists():
        print(f"Error: File not found: {filing_path}")
        sys.exit(1)
    
    # Run the pipeline
    pipeline_main()


if __name__ == "__main__":
    main()
