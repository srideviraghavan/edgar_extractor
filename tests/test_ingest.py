"""Unit tests for ingest.py - HTML parsing and chunking."""

import pytest
from bs4 import BeautifulSoup
from edgar_extractor.ingest import parse_html, _extract_tables, _extract_prose


def test_parse_html_basic():
    """Test basic HTML parsing."""
    html = """
    <html>
        <body>
            <h1>Financial Statements</h1>
            <table>
                <tr><th>Item</th><th>Value</th></tr>
                <tr><td>Revenue</td><td>1000</td></tr>
            </table>
            <p>This is prose content.</p>
        </body>
    </html>
    """
    tables, prose = parse_html(html)
    
    assert len(tables) == 1
    assert len(prose) >= 0


def test_extract_tables():
    """Test table extraction from HTML."""
    html = """
    <table>
        <tr><th>Item</th><th>Value</th></tr>
        <tr><td>Revenue</td><td>1000</td></tr>
        <tr><td>Expense</td><td>500</td></tr>
    </table>
    """
    soup = BeautifulSoup(html, "lxml")
    tables = _extract_tables(soup)
    
    assert len(tables) == 1
    assert tables[0].headers == ["Item", "Value"]
    assert len(tables[0].rows) == 2
    assert tables[0].rows[0]["Item"] == "Revenue"
    assert tables[0].rows[0]["Value"] == "1000"


def test_extract_prose():
    """Test prose chunking by section headers."""
    html = """
    <h1>Overview</h1>
    <p>This is the overview section.</p>
    <p>More overview content.</p>
    <h2>Risk Factors</h2>
    <p>Risk factor one.</p>
    <p>Risk factor two.</p>
    """
    soup = BeautifulSoup(html, "lxml")
    prose = _extract_prose(soup)
    
    assert len(prose) >= 1
    assert any("Overview" in p.section_header for p in prose)


def test_empty_html():
    """Test parsing empty HTML."""
    html = "<html><body></body></html>"
    tables, prose = parse_html(html)
    
    assert len(tables) == 0
    assert len(prose) == 0


def test_table_with_empty_rows():
    """Test table extraction with empty rows."""
    html = """
    <table>
        <tr><th>Item</th><th>Value</th></tr>
        <tr><td></td><td></td></tr>
        <tr><td>Revenue</td><td>1000</td></tr>
    </table>
    """
    soup = BeautifulSoup(html, "lxml")
    tables = _extract_tables(soup)
    
    # Should skip empty rows
    assert len(tables[0].rows) >= 1


def test_prose_without_headers():
    """Test prose extraction without section headers."""
    html = """
    <p>Just some text without headers.</p>
    <p>More text.</p>
    """
    soup = BeautifulSoup(html, "lxml")
    prose = _extract_prose(soup)
    
    # Should return empty list if no headers found
    assert len(prose) == 0
