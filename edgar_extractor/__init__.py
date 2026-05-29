"""EDGAR Extractor - Extract structured data from SEC filings."""

__version__ = "0.1.0"

from .schema import FilingExtraction, TableData, ProseChunk, GuidanceSection
from .pipeline import main

__all__ = [
    "FilingExtraction",
    "TableData",
    "ProseChunk",
    "GuidanceSection",
    "main",
]
