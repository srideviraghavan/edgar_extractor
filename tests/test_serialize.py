"""Unit tests for serialize.py - JSON serialization/deserialization."""

import json
import pytest
from pathlib import Path
from datetime import datetime
from edgar_extractor.serialize import (
    to_json,
    from_json,
    _extraction_to_dict,
    _dict_to_extraction,
)
from edgar_extractor.schema import FilingExtraction, TableData, ProseChunk


def test_extraction_to_dict():
    """Test converting FilingExtraction to dictionary."""
    extraction = FilingExtraction(
        filing_id="test_filing",
        filing_type="10-K",
        company_name="Test Corp",
        filing_date=datetime(2024, 1, 1),
    )
    
    data = _extraction_to_dict(extraction)
    
    assert data["filing_id"] == "test_filing"
    assert data["filing_type"] == "10-K"
    assert data["company_name"] == "Test Corp"
    assert data["filing_date"] == "2024-01-01T00:00:00"


def test_dict_to_extraction():
    """Test converting dictionary to FilingExtraction."""
    data = {
        "filing_id": "test_filing",
        "filing_type": "10-K",
        "company_name": "Test Corp",
        "filing_date": "2024-01-01T00:00:00",
        "tables": [],
        "prose_chunks": [],
        "guidance_sections": [],
        "extraction_metadata": {},
    }
    
    extraction = _dict_to_extraction(data)
    
    assert extraction.filing_id == "test_filing"
    assert extraction.filing_type == "10-K"
    assert extraction.company_name == "Test Corp"
    assert extraction.filing_date.year == 2024


def test_round_trip_serialization(tmp_path):
    """Test round-trip serialization and deserialization."""
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
    
    output_path = tmp_path / "test_output.json"
    to_json(extraction, output_path)
    
    assert output_path.exists()
    
    loaded_extraction = from_json(output_path)
    
    assert loaded_extraction.filing_id == extraction.filing_id
    assert len(loaded_extraction.tables) == len(extraction.tables)
    assert len(loaded_extraction.prose_chunks) == len(extraction.prose_chunks)


def test_json_file_format(tmp_path):
    """Test that JSON file is properly formatted."""
    extraction = FilingExtraction(filing_id="test_filing")
    output_path = tmp_path / "test_output.json"
    
    to_json(extraction, output_path)
    
    with open(output_path, "r") as f:
        content = f.read()
    
    # Verify it's valid JSON
    data = json.loads(content)
    assert data["filing_id"] == "test_filing"
    
    # Verify it's pretty-printed (has indentation)
    assert "\n" in content


def test_serialize_with_datetime():
    """Test serialization with datetime fields."""
    extraction = FilingExtraction(
        filing_id="test_filing",
        filing_date=datetime(2024, 1, 15, 12, 30, 45),
    )
    
    data = _extraction_to_dict(extraction)
    
    assert data["filing_date"] == "2024-01-15T12:30:45"


def test_serialize_with_null_fields():
    """Test serialization with null/optional fields."""
    extraction = FilingExtraction(
        filing_id="test_filing",
        filing_type=None,
        company_name=None,
        filing_date=None,
    )
    
    data = _extraction_to_dict(extraction)
    
    assert data["filing_type"] is None
    assert data["company_name"] is None
    assert data["filing_date"] is None
