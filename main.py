"""CLI entry point for EDGAR extractor."""

import sys
from pathlib import Path

from edgar_extractor.pipeline import main as pipeline_main


def main():
    """Entry point for the CLI."""
    # Default to data/raw/ if no argument provided
    if len(sys.argv) < 2:
        input_path = Path("data/raw")
    else:
        input_path = Path(sys.argv[1])
    
    if not input_path.exists():
        print(f"Error: Path not found: {input_path}")
        sys.exit(1)
    
    # Run the pipeline
    pipeline_main(input_path)


if __name__ == "__main__":
    main()
