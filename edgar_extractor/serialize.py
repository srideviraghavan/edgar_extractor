"""Serialization layer - convert FilingExtraction to JSON."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from .schema import FilingExtraction


def to_json(extraction: FilingExtraction, output_path: Path) -> None:
    """
    Serialize FilingExtraction to JSON file.
    
    Args:
        extraction: FilingExtraction object to serialize
        output_path: Path to write JSON file
    """
    json_data = _extraction_to_dict(extraction)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, default=_json_serializer)


def _extraction_to_dict(extraction: FilingExtraction) -> dict[str, Any]:
    """Convert FilingExtraction to dictionary."""
    return {
        "filing_id": extraction.filing_id,
        "filing_type": extraction.filing_type,
        "company_name": extraction.company_name,
        "filing_date": extraction.filing_date.isoformat() if extraction.filing_date else None,
        "tables": [_table_to_dict(t) for t in extraction.tables],
        "prose_chunks": [_prose_to_dict(p) for p in extraction.prose_chunks],
        "guidance_sections": [_guidance_to_dict(g) for g in extraction.guidance_sections],
        "extraction_metadata": extraction.extraction_metadata,
    }


def _table_to_dict(table: Any) -> dict[str, Any]:
    """Convert TableData to dictionary."""
    return {
        "table_id": table.table_id,
        "headers": table.headers,
        "rows": table.rows,
        "confidence": table.confidence,
        "source_section": table.source_section,
    }


def _prose_to_dict(prose: Any) -> dict[str, Any]:
    """Convert ProseChunk to dictionary."""
    return {
        "chunk_id": prose.chunk_id,
        "text": prose.text,
        "section_header": prose.section_header,
        "confidence": prose.confidence,
        "extracted_data": prose.extracted_data,
    }


def _guidance_to_dict(guidance: Any) -> dict[str, Any]:
    """Convert GuidanceSection to dictionary."""
    return {
        "section_id": guidance.section_id,
        "title": guidance.title,
        "content": guidance.content,
        "fiscal_year": guidance.fiscal_year,
        "confidence": guidance.confidence,
        "extracted_guidance": guidance.extracted_guidance,
    }


def _json_serializer(obj: Any) -> Any:
    """Custom JSON serializer for non-serializable objects."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def from_json(json_path: Path) -> FilingExtraction:
    """
    Deserialize JSON file to FilingExtraction.
    
    Args:
        json_path: Path to JSON file
        
    Returns:
        FilingExtraction object
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    return _dict_to_extraction(data)


def _dict_to_extraction(data: dict[str, Any]) -> FilingExtraction:
    """Convert dictionary to FilingExtraction."""
    return FilingExtraction(
        filing_id=data["filing_id"],
        filing_type=data.get("filing_type"),
        company_name=data.get("company_name"),
        filing_date=datetime.fromisoformat(data["filing_date"]) if data.get("filing_date") else None,
        tables=[_dict_to_table(t) for t in data.get("tables", [])],
        prose_chunks=[_dict_to_prose(p) for p in data.get("prose_chunks", [])],
        guidance_sections=[_dict_to_guidance(g) for g in data.get("guidance_sections", [])],
        extraction_metadata=data.get("extraction_metadata", {}),
    )


def _dict_to_table(data: dict[str, Any]) -> Any:
    """Convert dictionary to TableData."""
    from .schema import TableData
    return TableData(
        table_id=data["table_id"],
        headers=data["headers"],
        rows=data["rows"],
        confidence=data.get("confidence", 1.0),
        source_section=data.get("source_section"),
    )


def _dict_to_prose(data: dict[str, Any]) -> Any:
    """Convert dictionary to ProseChunk."""
    from .schema import ProseChunk
    return ProseChunk(
        chunk_id=data["chunk_id"],
        text=data["text"],
        section_header=data.get("section_header"),
        confidence=data.get("confidence", 1.0),
        extracted_data=data.get("extracted_data"),
    )


def _dict_to_guidance(data: dict[str, Any]) -> Any:
    """Convert dictionary to GuidanceSection."""
    from .schema import GuidanceSection
    return GuidanceSection(
        section_id=data["section_id"],
        title=data["title"],
        content=data["content"],
        fiscal_year=data.get("fiscal_year"),
        confidence=data.get("confidence", 1.0),
        extracted_guidance=data.get("extracted_guidance"),
    )
