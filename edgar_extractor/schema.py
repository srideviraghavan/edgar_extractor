"""Data models for EDGAR extraction."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


@dataclass
class TableData:
    """Structured table data extracted from HTML."""
    
    table_id: str
    headers: list[str]
    rows: list[dict[str, Any]]
    confidence: float = 1.0
    source_section: Optional[str] = None


@dataclass
class ProseChunk:
    """Text segment with metadata."""
    
    chunk_id: str
    text: str
    section_header: Optional[str] = None
    confidence: float = 1.0
    extracted_data: Optional[dict[str, Any]] = None


@dataclass
class GuidanceSection:
    """Management guidance section."""
    
    section_id: str
    title: str
    content: str
    fiscal_year: Optional[str] = None
    confidence: float = 1.0
    extracted_guidance: Optional[dict[str, Any]] = None


class FilingExtraction(BaseModel):
    """Root container for all extracted filing data."""
    
    filing_id: str = Field(..., description="Unique identifier for the filing")
    filing_type: Optional[str] = Field(None, description="Type of filing (10-K, 10-Q, etc.)")
    company_name: Optional[str] = Field(None, description="Name of the company")
    filing_date: Optional[datetime] = Field(None, description="Date of the filing")
    
    tables: list[TableData] = Field(default_factory=list, description="Extracted tables")
    prose_chunks: list[ProseChunk] = Field(default_factory=list, description="Extracted prose segments")
    guidance_sections: list[GuidanceSection] = Field(default_factory=list, description="Management guidance")
    
    extraction_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata about the extraction process"
    )
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
        }
