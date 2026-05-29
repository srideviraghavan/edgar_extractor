# Schema Design Prompt

Design the data model for EDGAR extraction with the following requirements:

## Core Data Classes
- `FilingExtraction`: Root container for all extracted data
- `TableData`: Structured table data with headers and rows
- `ProseChunk`: Text segments with metadata
- `GuidanceSection`: Management guidance sections

## Requirements
- Use Pydantic for validation
- Include confidence scores for each extraction
- Support nested data structures
- Handle datetime fields properly
- Include metadata about extraction process

## Fields to Include
- Filing metadata (ID, type, company, date)
- Table data (headers, rows, source section)
- Prose data (text, section header, extracted entities)
- Guidance data (title, content, fiscal year, extracted guidance)
- Extraction metadata (model used, validation results)
