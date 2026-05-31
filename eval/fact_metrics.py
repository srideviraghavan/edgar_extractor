"""Compare pipeline outputs against golden key-metric expectations."""

from __future__ import annotations

import re
from typing import Any


METRIC_LABELS: dict[str, list[str]] = {
    "total_revenue": [
        r"^total\s+reven",
        r"^reven(?:ue)?\s*$",
        r"revenue\s+was",
    ],
    "net_income": [
        r"^net\s+(?:income|loss|earnings)\s*$",
        r"^net\s+(?:income|loss)\s+attributable",
        r"gaap\s+net\s+(?:income|loss)",
        r"gaap\s+net\s+loss",
    ],
    "eps_diluted": [
        r"diluted.*(?:eps|earnings per share|net.*per share)",
        r"(?:eps|earnings per share).*(?:diluted|basic)",
        r"loss per share",
        r"earnings per share",
    ],
    "gross_profit": [
        r"^gross\s+profit",
    ],
}

SCALE_MULTIPLIERS = {
    "units": 1,
    "thousands": 1_000,
    "millions": 1_000_000,
    "billions": 1_000_000_000,
}


def normalize_number(raw: str) -> float | None:
    """Parse a financial number from table cell or prose text."""
    if not raw or raw.strip() in {"-", "—", "N/A", ""}:
        return None

    text = raw.strip()
    negative = text.startswith("(") and text.endswith(")")
    text = text.strip("()")
    text = text.replace("$", "").replace(",", "").replace("\xa0", " ").strip()

    multiplier = 1.0
    lower = text.lower()
    if lower.endswith("billion") or lower.endswith("billions"):
        multiplier = 1_000_000_000
        text = re.sub(r"\s*(?:billion|billions)\s*$", "", text, flags=re.I)
    elif lower.endswith("million") or lower.endswith("millions"):
        multiplier = 1_000_000
        text = re.sub(r"\s*(?:million|millions)\s*$", "", text, flags=re.I)
    elif lower.endswith("thousand") or lower.endswith("thousands"):
        multiplier = 1_000
        text = re.sub(r"\s*(?:thousand|thousands)\s*$", "", text, flags=re.I)

    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None

    value = float(match.group()) * multiplier
    if negative and value > 0:
        value = -value
    return value


def _label_matches(metric_name: str, label: str) -> bool:
    label_lower = re.sub(r"\s+", " ", label).strip().lower()
    for pattern in METRIC_LABELS.get(metric_name, []):
        if re.search(pattern, label_lower, re.I):
            if metric_name == "eps_diluted" and re.search(r"shares used|weighted|margin", label_lower):
                continue
            return True
    return False


def _parse_table_value(raw: str) -> float | None:
    """Parse a table cell without prose unit suffixes."""
    if not raw or raw.strip() in {"-", "—", "N/A", ""}:
        return None
    text = raw.strip()
    negative = text.startswith("(")
    text = text.strip("()").replace("$", "").replace(",", "").replace("\xa0", " ").strip()
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    value = float(match.group())
    if negative and value > 0:
        value = -value
    return value


def _row_label(row: dict[str, Any]) -> str:
    """Extract the row label from a table row dict."""
    if "" in row and isinstance(row[""], str) and row[""].strip():
        return row[""].strip()
    for key, value in row.items():
        if isinstance(value, str) and value.strip() and not _parse_table_value(value):
            return value.strip()
    return ""


def _detect_scale_from_text(text: str) -> str | None:
    """Detect thousands/millions scale hints from a text blob."""
    lower = text.lower()
    if "in thousands" in lower or "(in thousands" in lower:
        return "thousands"
    if "in millions" in lower or "$ in millions" in lower:
        return "millions"
    if "in billions" in lower:
        return "billions"
    return None


def _detect_table_scale(table: dict[str, Any], fallback_scale: str | None = None) -> str | None:
    """Detect scale for a single table from its first rows."""
    for row in table.get("rows", [])[:15]:
        if not isinstance(row, dict):
            continue
        row_text = " ".join(str(value) for value in row.values())
        scale = _detect_scale_from_text(row_text)
        if scale:
            return scale
    return fallback_scale


def _detect_output_scale(output: dict[str, Any]) -> str | None:
    """Detect a filing-wide scale hint from prose when tables omit it."""
    prose_text = " ".join(chunk.get("text", "") for chunk in output.get("prose_chunks", []))
    return _detect_scale_from_text(prose_text)


def _collect_table_candidates(
    output: dict[str, Any],
) -> list[tuple[str, float, str | None]]:
    candidates: list[tuple[str, float, str | None]] = []
    fallback_scale = _detect_output_scale(output)

    for table in output.get("tables", []):
        table_scale = _detect_table_scale(table, fallback_scale)
        for row in table.get("rows", []):
            if not isinstance(row, dict):
                continue
            label = _row_label(row)
            for value in row.values():
                if isinstance(value, str):
                    parsed = _parse_table_value(value)
                    if parsed is not None:
                        candidates.append((label, parsed, table_scale))
    return candidates


def _scale_table_value(value: float, table_scale: str | None, golden_scale: str) -> float:
    """Convert a table cell value into the golden filing scale."""
    if table_scale is None or table_scale == golden_scale:
        return value
    return _to_display_scale(value, table_scale, golden_scale)


def _collect_prose_candidates(output: dict[str, Any]) -> list[tuple[str, float]]:
    candidates: list[tuple[str, float]] = []
    prose_patterns = [
        (r"revenue\s+was\s+\$?\s*([\d,\.]+\s*(?:million|billion)?)", "total_revenue"),
        (r"total\s+revenue\s+of\s+\$?\s*([\d,\.]+\s*(?:million|billion)?)", "total_revenue"),
        (r"(?:net sales|revenue)\s+of\s+\$?\s*([\d,\.]+\s*(?:million|billion)?)", "total_revenue"),
        (r"(?:fourth|first|second|third)\s+quarter\s+revenue\s+of\s+\$?\s*([\d,\.]+\s*(?:million|billion)?)", "total_revenue"),
        (r"net\s+(?:income|loss)\s+was\s+\$?\s*\(?([\d,\.]+\s*(?:million|billion)?)\)?", "net_income"),
        (r"gaap\s+net\s+loss\s+was\s+\$?\s*([\d,\.]+\s*(?:million|billion)?)", "net_income"),
        (r"gaap\s+(?:loss|income)\s+of\s+\$?\s*([\d,\.]+\s*(?:million|billion)?)", "net_income"),
        (r"(?:diluted|basic)\s+(?:loss|earnings)\s+per\s+share\s+was\s+\$?\s*\(?([\d,\.]+)\)?", "eps_diluted"),
        (r"gross\s+profit\s+(?:for|was).*?\$?\s*([\d,\.]+\s*(?:million|billion)?)", "gross_profit"),
    ]

    for chunk in output.get("prose_chunks", []):
        text = chunk.get("text", "")
        for pattern, metric_name in prose_patterns:
            for match in re.finditer(pattern, text, re.I):
                parsed = normalize_number(match.group(1))
                if parsed is None:
                    continue
                window = text[max(0, match.start() - 30) : match.end() + 30].lower()
                if metric_name == "net_income" and "loss" in window and parsed > 0:
                    parsed = -parsed
                candidates.append((metric_name, parsed))

        extracted = chunk.get("extracted_data") or {}
        raw = extracted.get("raw_response", "")
        for figure in re.findall(r'"value"\s*:\s*"?\$?([\d,\.\(\)]+)"?', raw):
            parsed = normalize_number(figure)
            if parsed is not None:
                candidates.append(("extracted", parsed))
    return candidates


def _to_display_scale(value: float, from_scale: str, to_scale: str) -> float:
    """Convert a numeric value between filing display scales."""
    from_mult = SCALE_MULTIPLIERS.get(from_scale, 1)
    to_mult = SCALE_MULTIPLIERS.get(to_scale, 1)
    return value * from_mult / to_mult


def _values_match(expected: float, found: float, tolerance_pct: float = 0.02) -> bool:
    if expected == 0:
        return abs(found) < 1.0
    relative_error = abs(found - expected) / max(abs(expected), 1.0)
    if relative_error <= tolerance_pct:
        return True
    if (expected < 0 < found) or (expected > 0 > found):
        return abs(found + expected) / max(abs(expected), 1.0) <= tolerance_pct
    return False


def find_metric_value(
    output: dict[str, Any],
    metric_name: str,
    golden: dict[str, Any],
) -> float | None:
    """Find the best matching metric value in pipeline output."""
    scale = golden.get("value_scale", "thousands")
    expected = golden.get("key_metrics", {}).get(metric_name, {}).get("value")
    if expected is None:
        return None

    best: float | None = None
    best_delta = float("inf")

    for label, value, table_scale in _collect_table_candidates(output):
        if _label_matches(metric_name, label):
            scaled_value = (
                value if metric_name == "eps_diluted" else _scale_table_value(value, table_scale, scale)
            )
            if _values_match(expected, scaled_value):
                return scaled_value
            delta = abs(scaled_value - expected) / max(abs(expected), 1.0)
            if delta < best_delta:
                best_delta = delta
                best = scaled_value

    for label, value in _collect_prose_candidates(output):
        if label == metric_name or _label_matches(metric_name, label):
            prose_value = value if metric_name == "eps_diluted" else _to_display_scale(value, "units", scale)
            if _values_match(expected, prose_value):
                return prose_value
            delta = abs(prose_value - expected) / max(abs(expected), 1.0)
            if delta < best_delta:
                best_delta = delta
                best = prose_value

    return best


def compare_facts(output: dict[str, Any], golden: dict[str, Any]) -> dict[str, Any]:
    """Score pipeline output against golden key metrics and structural checks."""
    key_metrics = golden.get("key_metrics", {})
    metric_results: dict[str, dict[str, Any]] = {}

    for metric_name, spec in key_metrics.items():
        expected = spec["value"]
        required = spec.get("required", True)
        found = find_metric_value(output, metric_name, golden)
        metric_results[metric_name] = {
            "expected": expected,
            "found": found,
            "required": required,
            "matched": found is not None and _values_match(expected, found),
        }

    required_metrics = [m for m, s in key_metrics.items() if s.get("required", True)]
    matched_required = sum(1 for m in required_metrics if metric_results[m]["matched"])
    required_recall = (
        matched_required / len(required_metrics) if required_metrics else 1.0
    )

    all_metrics = list(key_metrics.keys())
    matched_all = sum(1 for m in all_metrics if metric_results[m]["matched"])
    metric_precision = matched_all / len(all_metrics) if all_metrics else 1.0

    table_count = len(output.get("tables", []))
    min_tables = golden.get("min_tables", 0)
    tables_ok = table_count >= min_tables

    guidance_sections = output.get("guidance_sections", [])
    has_guidance_output = len(guidance_sections) > 0 or any(
        re.search(r"\b(?:guidance|outlook|forecast)\b", chunk.get("text", ""), re.I)
        for chunk in output.get("prose_chunks", [])
    ) or any(
        re.search(r"\b(?:guidance|outlook|forecast)\b", cell, re.I)
        for table in output.get("tables", [])
        for row in table.get("rows", [])
        for cell in row.values()
        if isinstance(cell, str)
    )
    guidance_expected = golden.get("has_guidance", False)
    guidance_ok = has_guidance_output == guidance_expected if not guidance_expected else has_guidance_output

    segment_results = []
    for segment in golden.get("segments", []):
        name = segment["name"]
        expected = segment["value"]
        found = None
        for chunk in output.get("prose_chunks", []):
            pattern = rf"{re.escape(name.split('&')[0].strip())}.*?(\$?\s*[\d,\.]+\s*(?:million|billion)?)"
            match = re.search(pattern, chunk.get("text", ""), re.I)
            if match:
                found = normalize_number(match.group(1))
                break
        segment_results.append(
            {
                "name": name,
                "expected": expected,
                "found": found,
                "matched": found is not None and _values_match(expected, found),
            }
        )

    segment_recall = (
        sum(1 for s in segment_results if s["matched"]) / len(segment_results)
        if segment_results
        else 1.0
    )

    fact_f1 = (
        2 * required_recall * metric_precision / (required_recall + metric_precision)
        if (required_recall + metric_precision) > 0
        else 0.0
    )

    return {
        "fact_f1": fact_f1,
        "required_metric_recall": required_recall,
        "metric_precision": metric_precision,
        "tables_ok": tables_ok,
        "table_count": table_count,
        "min_tables": min_tables,
        "guidance_ok": guidance_ok,
        "guidance_expected": guidance_expected,
        "segment_recall": segment_recall,
        "metrics": metric_results,
        "segments": segment_results,
    }
