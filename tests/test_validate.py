"""Unit tests for validate.py - confidence scoring and deduplication."""

import pytest
from edgar_extractor.validate import (
    calculate_confidence,
    deduplicate_entities,
    cross_check_table_prose,
    validate_extraction,
)
from edgar_extractor.schema import FilingExtraction


def test_calculate_confidence_table():
    """Test confidence calculation for table data."""
    data = {"rows": [{"item": "Revenue", "value": "1000"}]}
    confidence = calculate_confidence(data, "table")
    
    assert 0 <= confidence <= 1
    assert confidence > 0.5  # Should have good confidence with rows


def test_calculate_confidence_empty():
    """Test confidence calculation for empty data."""
    data = {}
    confidence = calculate_confidence(data, "table")
    
    assert confidence == 0.0


def test_deduplicate_entities():
    """Test entity deduplication."""
    entities = [
        {"name": "Apple Inc.", "ticker": "AAPL"},
        {"name": "Apple Inc.", "ticker": "AAPL"},
        {"name": "Microsoft Corp.", "ticker": "MSFT"},
    ]
    
    deduplicated = deduplicate_entities(entities)
    
    assert len(deduplicated) == 2
    assert deduplicated[0]["name"] == "Apple Inc."
    assert deduplicated[1]["name"] == "Microsoft Corp."


def test_deduplicate_entities_different():
    """Test that different entities are not deduplicated."""
    entities = [
        {"name": "Apple Inc.", "ticker": "AAPL"},
        {"name": "Microsoft Corp.", "ticker": "MSFT"},
    ]
    
    deduplicated = deduplicate_entities(entities)
    
    assert len(deduplicated) == 2


def test_cross_check_table_prose():
    """Test cross-check between tables and prose."""
    from edgar_extractor.schema import TableData, ProseChunk
    
    tables = [
        TableData(
            table_id="table_1",
            headers=["Item", "Value"],
            rows=[{"Item": "Revenue", "Value": "1000"}],
        )
    ]
    
    prose = [
        ProseChunk(
            chunk_id="prose_1",
            text="Revenue was 1000",
            section_header="Overview",
        )
    ]
    
    result = cross_check_table_prose(tables, prose)
    
    assert "consistency_score" in result
    assert "issues" in result
    assert 0 <= result["consistency_score"] <= 1


def test_validate_extraction():
    """Test comprehensive extraction validation."""
    from edgar_extractor.schema import TableData, ProseChunk
    
    extraction = FilingExtraction(
        filing_id="test_filing",
        tables=[
            TableData(
                table_id="table_1",
                headers=["Item", "Value"],
                rows=[{"Item": "Revenue", "Value": "1000"}],
                confidence=0.9,
            )
        ],
        prose_chunks=[
            ProseChunk(
                chunk_id="prose_1",
                text="Test content",
                section_header="Overview",
                confidence=0.85,
            )
        ],
    )
    
    report = validate_extraction(extraction)
    
    assert "overall_confidence" in report
    assert "table_confidence" in report
    assert "prose_confidence" in report
    assert 0 <= report["overall_confidence"] <= 1


def test_validate_extraction_empty():
    """Test validation of empty extraction."""
    extraction = FilingExtraction(filing_id="test_filing")
    
    report = validate_extraction(extraction)
    
    assert report["overall_confidence"] == 0.0
    assert report["table_confidence"] == 0.0
    assert report["prose_confidence"] == 0.0
