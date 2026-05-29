"""Validation layer - confidence scoring, deduplication, cross-checks."""

from typing import Any
from .schema import TableData, ProseChunk, GuidanceSection


def calculate_confidence(extracted_data: dict[str, Any], data_type: str) -> float:
    """
    Calculate confidence score for extracted data.
    
    Args:
        extracted_data: The data extracted by LLM
        data_type: Type of data (table, prose, guidance)
        
    Returns:
        Confidence score between 0 and 1
    """
    # Placeholder implementation
    # In production, this would analyze:
    # - Response structure validity
    # - Data completeness
    # - Consistency with source
    # - LLM confidence indicators
    
    if not extracted_data:
        return 0.0
    
    # Basic checks
    if data_type == "table":
        return 0.9 if "rows" in extracted_data else 0.5
    elif data_type == "prose":
        return 0.85 if "entities" in extracted_data else 0.6
    elif data_type == "guidance":
        return 0.9 if "guidance" in extracted_data else 0.5
    
    return 0.7


def deduplicate_entities(entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Remove duplicate entities based on key fields.
    
    Args:
        entities: List of extracted entities
        
    Returns:
        Deduplicated list
    """
    seen = set()
    deduplicated = []
    
    for entity in entities:
        # Create a signature based on key fields
        signature = _entity_signature(entity)
        
        if signature not in seen:
            seen.add(signature)
            deduplicated.append(entity)
    
    return deduplicated


def _entity_signature(entity: dict[str, Any]) -> str:
    """Create a unique signature for an entity."""
    key_fields = ["name", "ticker", "cik"]
    parts = []
    
    for field in key_fields:
        if field in entity:
            parts.append(str(entity[field]))
    
    return "|".join(parts) if parts else str(hash(str(entity)))


def cross_check_table_prose(tables: list[TableData], prose: list[ProseChunk]) -> dict[str, Any]:
    """
    Cross-check data between tables and prose for consistency.
    
    Args:
        tables: Extracted table data
        prose: Extracted prose chunks
        
    Returns:
        Dictionary with cross-check results and flags
    """
    issues = []
    
    # Placeholder implementation
    # In production, this would:
    # - Compare financial figures across sources
    # - Check for conflicting dates
    # - Verify entity names match
    
    return {
        "issues": issues,
        "consistency_score": 1.0 if not issues else 0.8,
    }


def validate_extraction(extraction: Any) -> dict[str, Any]:
    """
    Perform comprehensive validation on extraction results.
    
    Args:
        extraction: FilingExtraction object
        
    Returns:
        Validation report with scores and issues
    """
    validation_report = {
        "overall_confidence": 0.0,
        "table_confidence": 0.0,
        "prose_confidence": 0.0,
        "guidance_confidence": 0.0,
        "issues": [],
    }
    
    # Calculate average confidence per type
    if extraction.tables:
        validation_report["table_confidence"] = sum(
            t.confidence for t in extraction.tables
        ) / len(extraction.tables)
    
    if extraction.prose_chunks:
        validation_report["prose_confidence"] = sum(
            p.confidence for p in extraction.prose_chunks
        ) / len(extraction.prose_chunks)
    
    if extraction.guidance_sections:
        validation_report["guidance_confidence"] = sum(
            g.confidence for g in extraction.guidance_sections
        ) / len(extraction.guidance_sections)
    
    # Overall confidence
    confidences = [
        validation_report["table_confidence"],
        validation_report["prose_confidence"],
        validation_report["guidance_confidence"],
    ]
    validation_report["overall_confidence"] = sum(
        c for c in confidences if c > 0
    ) / len([c for c in confidences if c > 0]) if confidences else 0.0
    
    return validation_report
