"""HTML ingestion layer - parse HTML into tables and prose chunks."""

import re
from bs4 import BeautifulSoup
from typing import Optional
from .schema import TableData, ProseChunk


LABEL_COLUMN = ""
MIN_PROSE_LENGTH = 80
MAX_PROSE_LENGTH = 12_000

# Boilerplate patterns to filter out
BOILERPLATE_PATTERNS = [
    r"safe harbor",
    r"forward[- ]looking statements?",
    r"private securities litigation reform act",
    r"cautionary statement",
    r"share repurchase program",
    r"stock repurchase",
    r"buyback program",
    r"legal disclaimer",
    r"confidential information",
    r"material non[- ]public information",
    r"this report contains",
    r"we undertake no obligation",
    r"actual results may differ",
    r"risks and uncertainties",
]

JUNK_PROSE_PATTERNS = [
    r"\bcookie",
    r"javascript",
    r"social media services",
    r"privacy (?:policy|notice)",
    r"sec\.gov/akam",
]


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


def _table_column_count(table) -> int:
    """Return the widest row in a table."""
    return max((len(row.find_all(["td", "th"])) for row in table.find_all("tr")), default=0)


def _column_keys(raw_headers: list[str], column_count: int) -> list[str]:
    """
    Build stable, unique column keys for a table.

    The first column is always the label column (empty string key). Later
    columns reuse non-empty header text when available; duplicate or blank
    headers fall back to positional names like col_1.
    """
    keys = [LABEL_COLUMN]
    seen: dict[str, int] = {}

    for index in range(1, column_count):
        header = raw_headers[index].strip() if index < len(raw_headers) else ""
        key = header or f"col_{index}"
        if key in seen:
            seen[key] += 1
            key = f"{key}_{seen[key]}"
        else:
            seen[key] = 0
        keys.append(key)

    return keys


def _extract_tables(soup: BeautifulSoup) -> list[TableData]:
    """Extract all tables from HTML."""
    tables = []

    for idx, table in enumerate(soup.find_all("table")):
        header_row = table.find("tr")
        raw_headers = (
            [cell.get_text(strip=True) for cell in header_row.find_all(["th", "td"])]
            if header_row
            else []
        )
        column_count = _table_column_count(table)
        if column_count == 0:
            continue

        keys = _column_keys(raw_headers, column_count)
        rows = []

        for row in table.find_all("tr")[1:]:
            cells = row.find_all(["td", "th"])
            if not cells:
                continue

            row_data = {}
            for cell_index, cell in enumerate(cells):
                if cell_index >= len(keys):
                    break
                row_data[keys[cell_index]] = cell.get_text(strip=True)

            if row_data:
                rows.append(row_data)

        if rows:
            tables.append(
                TableData(
                    table_id=f"table_{idx}",
                    headers=keys,
                    rows=rows,
                    source_section=_find_section_context(table),
                )
            )

    return tables


def _is_boilerplate(text: str) -> bool:
    """Check if text matches boilerplate patterns."""
    text_lower = text.lower()
    for pattern in BOILERPLATE_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True
    return False


def _is_junk_prose(text: str) -> bool:
    """Filter cookie banners, scripts, and other non-filing content."""
    text_lower = text.lower()
    return any(re.search(pattern, text_lower, re.I) for pattern in JUNK_PROSE_PATTERNS)


def _is_usable_prose(text: str) -> bool:
    """Return True for narrative blocks worth sending to the extractor."""
    cleaned = re.sub(r"\s+", " ", text).strip()
    if len(cleaned) < MIN_PROSE_LENGTH or len(cleaned) > MAX_PROSE_LENGTH:
        return False
    if _is_boilerplate(cleaned) or _is_junk_prose(cleaned):
        return False
    return True


def _dedupe_prose_chunks(chunks: list[ProseChunk]) -> list[ProseChunk]:
    """Drop chunks that are strict substrings of another chunk."""
    kept: list[ProseChunk] = []
    for chunk in sorted(chunks, key=lambda item: len(item.text), reverse=True):
        if any(chunk.text in other.text for other in kept):
            continue
        kept.append(chunk)
    kept.reverse()
    return kept


def _extract_prose_from_headers(soup: BeautifulSoup) -> list[ProseChunk]:
    """Extract prose grouped under h1-h4 section headers."""
    chunks = []
    headers = soup.find_all(["h1", "h2", "h3", "h4"])

    for idx, header in enumerate(headers):
        header_text = header.get_text(strip=True)
        text_content = []
        next_element = header.find_next_sibling()

        while next_element and next_element.name not in ["h1", "h2", "h3", "h4"]:
            if next_element.name == "p":
                paragraph_text = next_element.get_text(strip=True)
                if _is_usable_prose(paragraph_text):
                    text_content.append(paragraph_text)
            next_element = next_element.find_next_sibling()

        if text_content:
            chunks.append(
                ProseChunk(
                    chunk_id=f"prose_{idx}",
                    text=" ".join(text_content),
                    section_header=header_text,
                )
            )

    return chunks


def _extract_prose_from_paragraphs(soup: BeautifulSoup) -> list[ProseChunk]:
    """Extract standalone press-release paragraphs."""
    chunks = []
    for idx, paragraph in enumerate(soup.find_all("p")):
        text = paragraph.get_text(" ", strip=True)
        if not _is_usable_prose(text):
            continue
        chunks.append(
            ProseChunk(
                chunk_id=f"prose_p_{idx}",
                text=text,
                section_header=None,
            )
        )
    return _dedupe_prose_chunks(chunks)


def _extract_prose_from_divs(soup: BeautifulSoup) -> list[ProseChunk]:
    """Extract narrative div blocks used by many inline-XBRL filings."""
    chunks = []
    for idx, div in enumerate(soup.find_all("div")):
        if div.find("table"):
            continue
        if div.find("div"):
            continue

        text = div.get_text(" ", strip=True)
        if not _is_usable_prose(text):
            continue

        chunks.append(
            ProseChunk(
                chunk_id=f"prose_d_{idx}",
                text=text,
                section_header=None,
            )
        )

    return _dedupe_prose_chunks(chunks)


def _extract_prose(soup: BeautifulSoup) -> list[ProseChunk]:
    """Extract prose chunks from HTML using multiple layout strategies."""
    for extractor in (
        _extract_prose_from_headers,
        _extract_prose_from_paragraphs,
        _extract_prose_from_divs,
    ):
        chunks = extractor(soup)
        if chunks:
            return chunks
    return []


def _find_section_context(element) -> Optional[str]:
    """Find the section header for a given element."""
    prev = element.find_previous(["h1", "h2", "h3", "h4"])
    if prev:
        return prev.get_text(strip=True)
    return None
