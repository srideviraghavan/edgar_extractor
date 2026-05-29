# Extraction Prompts Design Prompt

Design LLM prompts for extracting data from SEC filings:

## Prompt Types
1. **Table Extraction Prompt**: Extract structured data from HTML tables
2. **Prose Extraction Prompt**: Extract entities and figures from text
3. **Guidance Extraction Prompt**: Extract management guidance

## Requirements
- Clear instructions for JSON output format
- Handle different types of financial data
- Extract entities (companies, people, locations)
- Extract financial figures with context
- Extract dates and periods
- Provide confidence indicators

## Output Format
All prompts should return valid JSON with:
- Extracted data fields
- Entity information
- Financial figures with units
- Key topics or metrics
- Summary of content
