# EDGAR Extractor

A Python tool for extracting structured data from SEC EDGAR HTML filings using LLMs.

## Features

- HTML parsing for tables and prose sections
- LLM-based extraction with confidence scoring
- Validation and deduplication
- Cost tracking per model
- JSON serialization of extracted data

## Installation

```bash
pip install -e .
```

## Usage

### Running Extraction

Extract data from a single filing:
```bash
python main.py data/raw/filing.html
```

Extract data from all filings in a directory:
```bash
python main.py data/raw
```

Outputs are saved to `data/outputs/` as JSON files.

### Running Evaluation

First, build golden reference files (if not already present):
```bash
python eval/build_golden.py
```

Then evaluate extraction outputs against golden files:
```bash
python eval/run_eval.py data/outputs
```

The evaluation compares outputs against golden files in `data/golden/` and reports:
- Fact F1 score
- Required metric recall
- Table extraction status
- Guidance extraction status
- Structure match score

## Configuration

Copy `.env.example` to `.env` and configure:
- `PORTKEY_API_KEY`: Your Portkey API key
- `MODEL`: The model to use for extraction

## Project Structure

- `edgar_extractor/`: Main package
  - `schema.py`: Data models
  - `ingest.py`: HTML parsing
  - `extract.py`: LLM extraction
  - `validate.py`: Validation logic
  - `serialize.py`: JSON serialization
  - `cost.py`: Cost tracking
  - `pipeline.py`: Orchestration
- `data/`: Input/output data
- `tests/`: Unit tests
- `eval/`: Evaluation scripts
