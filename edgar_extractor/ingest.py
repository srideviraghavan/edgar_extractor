"""HTML ingestion layer - parse HTML into tables and prose chunks."""

from bs4 import BeautifulSoup
from typing import Optional
from .schema import TableData, ProseChunk


def parse_html(html_content: str) -> tuple[list[TableData], list[ProseChunk]]:
    """
    Parse HTML content and extract tables and prose chunks.
    
    Args:
        html_content: Raw HTML string from SEC filing
        
    Returns:
        Tuple of (tables, prose_chunks)
    """
    soup = BeautifulSoup(html_content, "lxml")
    
    tables = _extract_tables(soup)
    prose_chunks = _extract_prose(soup)
    
    return tables, prose_chunks


def _extract_tables(soup: BeautifulSoup) -> list[TableData]:
    """Extract all tables from HTML."""
    tables = []
    
    for idx, table in enumerate(soup.find_all("table")):
        headers = []
        rows = []
        
        # Extract headers
        header_row = table.find("tr")
        if header_row:
            headers = [th.get_text(strip=True) for th in header_row.find_all(["th", "td"])]
        
        # Extract data rows
        for row in table.find_all("tr")[1:]:  # Skip header row
            cells = row.find_all(["td", "th"])
            if cells:
                row_data = {}
                for i, cell in enumerate(cells):
                    if i < len(headers):
                        row_data[headers[i]] = cell.get_text(strip=True)
                if row_data:
                    rows.append(row_data)
        
        if headers and rows:
            tables.append(
                TableData(
                    table_id=f"table_{idx}",
                    headers=headers,
                    rows=rows,
                    source_section=_find_section_context(table)
                )
            )
    
    return tables


def _extract_prose(soup: BeautifulSoup) -> list[ProseChunk]:
    """Extract prose chunks from HTML by section headers."""
    chunks = []
    
    # Find all potential section headers
    headers = soup.find_all(["h1", "h2", "h3", "h4"])
    
    for idx, header in enumerate(headers):
        header_text = header.get_text(strip=True)
        
        # Collect text until next header
        text_content = []
        next_element = header.find_next_sibling()
        
        while next_element and next_element.name not in ["h1", "h2", "h3", "h4"]:
            if next_element.name == "p":
                text_content.append(next_element.get_text(strip=True))
            next_element = next_element.find_next_sibling()
        
        if text_content:
            chunks.append(
                ProseChunk(
                    chunk_id=f"prose_{idx}",
                    text=" ".join(text_content),
                    section_header=header_text
                )
            )
    
    return chunks


def _find_section_context(element) -> Optional[str]:
    """Find the section header for a given element."""
    prev = element.find_previous(["h1", "h2", "h3", "h4"])
    if prev:
        return prev.get_text(strip=True)
    return None
