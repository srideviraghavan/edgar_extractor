# EDGAR Extractor Specification

## Overview
Extract structured financial data from SEC EDGAR HTML filings using LLMs.

## Data Model (schema.py)
- `FilingExtraction`: Root container with all extracted data
- `TableData`: Structured table data with headers and rows
- `ProseChunk`: Text segments with metadata
- `GuidanceSection`: Management guidance sections
- All fields use Pydantic for validation

## Ingestion Layer (ingest.py)
- Parse HTML with BeautifulSoup
- Extract tables: identify table tags, parse headers/rows
- Extract prose: split text into chunks by section headers
- Return structured data for extraction

## Extraction Layer (extract.py)
- Use Portkey API for LLM calls
- Separate prompts for tables vs prose vs guidance
- Return structured JSON responses
- Handle errors and retries

## Validation Layer (validate.py)
- Confidence scoring based on LLM response quality
- Deduplication of extracted entities
- Cross-checks between table and prose data
- Flag low-confidence extractions

## Serialization (serialize.py)
- Convert FilingExtraction to JSON
- Ensure all datetime fields are ISO formatted
- Handle nested data structures

## Cost Tracking (cost.py)
- Count tokens per request
- Calculate cost per model
- Aggregate costs per filing

## Pipeline (pipeline.py)
- Orchestrate: ingest → extract → validate → serialize
- CLI entry point
- Progress reporting with rich
