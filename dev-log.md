# Development Log

## Initial Setup
- Created project structure
- Set up pyproject.toml with dependencies
- Configured pytest
- Ran a basic extraction test

## Core Implementation (Completed)
- **schema.py**: Implemented Pydantic models (TableData, ProseChunk, GuidanceSection)
- **ingest.py**: HTML parsing layer with multiple extraction strategies
  - Table extraction with stable column keys
  - Prose extraction from headers, paragraphs, and divs
  - Boilerplate and junk content filtering
  - Prose deduplication
- **extract.py**: LLM extraction layer
  - Table extraction with batching for large tables
  - Prose extraction with chunking for long text
  - Guidance extraction for management guidance sections
  - Token counting and limit enforcement
  - Cost tracking integration
- **validate.py**: Validation logic for extracted data
- **serialize.py**: Serialization utilities
- **cost.py**: Token usage and cost tracking
- **pipeline.py**: End-to-end pipeline orchestration

## Data Setup (Completed)
- Added 20 HTML filings to data/raw/
- Created 20 golden JSON files in data/golden/ for validation
- Set up data/outputs/ for extraction results

## Prompt Engineering (Completed)
- Designed table extraction prompt (prompts/table.txt)
- Designed prose extraction prompt (prompts/prose.txt)
- Designed guidance extraction prompt (prompts/guidance.txt)
- Added more examples to improve extraction accuracy
- Parsed HTML tables to extract headers and rows
- Added filtering to remove boilerplate and junk content 
- Removed empty tables and rows
- Split tabes and prose sections to be sent to the LLM separately
- Added deduplication to remove duplicate prose chunks
- Added chunking to split long prose into manageable pieces
- Added validation to ensure extracted data matches expected schema

## Testing & Evaluation (Completed)
- Created comprehensive test suite in tests/
  - test_ingest.py: HTML parsing tests
  - test_serialize.py: Serialization tests
  - test_validate.py: Validation tests
  - test_eval.py: Evaluation framework tests
- Implemented evaluation framework in eval/
  - metrics.py: Evaluation metrics
  - fact_metrics.py: Fact-based metrics
  - build_golden.py: Golden data builder
  - run_eval.py: Evaluation runner
- **Evaluation approach**: Uses deterministic, rule-based metrics (F1, exact match, regex patterns, numerical comparison) rather than LLM as a judge. 

## Current Status
All core components are implemented and tested. The pipeline can:
1. Ingest HTML filings and extract tables/prose
2. Send chunks to LLM for structured extraction
3. Validate results against golden data
4. Track token usage and costs
5. Run comprehensive evaluations

## Issues
There were issues with the table extraction that needed to be fixed. Some of the issues were:
- Table rows were not being extracted correctly
- Table data was not being extracted correctly
This was caught during evaluation and fixed.