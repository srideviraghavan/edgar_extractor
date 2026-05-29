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

```bash
python main.py data/raw/filing.html
```

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
