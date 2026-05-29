# Ingest Layer Design Prompt

Design the HTML ingestion layer with the following requirements:

## Core Functions
- `parse_html()`: Main entry point for HTML parsing
- `_extract_tables()`: Extract all tables from HTML
- `_extract_prose()`: Extract prose chunks by section headers
- `_find_section_context()`: Find section context for elements

## Requirements
- Use BeautifulSoup for HTML parsing
- Parse table headers and rows correctly
- Split text into logical chunks by section headers
- Handle various HTML structures from SEC filings
- Return structured data ready for extraction

## Implementation Details
- Use lxml parser for better performance
- Handle nested tables if present
- Preserve section context for each extraction
- Clean whitespace from extracted text
