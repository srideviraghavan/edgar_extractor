"""Tests for evaluation metrics."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "eval"))

from edgar_extractor.ingest import parse_html
from fact_metrics import compare_facts, normalize_number
from metrics import calculate_f1, extract_leaf_pairs


def test_extract_leaf_pairs_nested():
    data = {
        "filing_id": "API_2023_Q1",
        "tables": [{"table_id": "table_0", "confidence": 0.5}],
        "counts": [1, 2],
    }
    pairs = extract_leaf_pairs(data)
    assert ("filing_id", "str:API_2023_Q1") in pairs
    assert ("tables.0.table_id", "str:table_0") in pairs
    assert ("tables.0.confidence", "float:0.5") in pairs
    assert ("counts.0", "int:1") in pairs


def test_calculate_f1_type_aware():
    golden = {"value": 100, "label": "100"}
    output_match = {"value": 100, "label": "100"}
    output_mismatch = {"value": "100", "label": "100"}

    assert calculate_f1(output_match, golden) == 1.0
    assert calculate_f1(output_mismatch, golden) < 1.0


def test_normalize_number_formats():
    assert normalize_number("(16,802)") == -16802
    assert normalize_number("$206 million") == 206_000_000
    assert normalize_number("0.36") == 0.36


def test_compare_facts_finds_table_metrics():
    golden = {
        "value_scale": "thousands",
        "key_metrics": {
            "total_revenue": {"value": 36443, "required": True},
            "net_income": {"value": -16802, "required": True},
        },
        "has_guidance": False,
        "min_tables": 1,
    }
    output = {
        "tables": [
            {
                "rows": [
                    {"": "Total revenues", "Q1 2023": "36,443"},
                    {"": "Net loss", "Q1 2023": "(16,802)"},
                ]
            }
        ],
        "prose_chunks": [],
        "guidance_sections": [],
    }
    result = compare_facts(output, golden)
    assert result["required_metric_recall"] == 1.0
    assert result["metrics"]["total_revenue"]["matched"]
    assert result["metrics"]["net_income"]["matched"]


def test_compare_facts_scales_thousands_to_millions():
    golden = {
        "value_scale": "millions",
        "key_metrics": {
            "net_income": {"value": 16.016, "required": True},
        },
        "has_guidance": False,
        "min_tables": 1,
    }
    output = {
        "tables": [
            {
                "rows": [
                    {"": "(in thousands, except per ADS data, unaudited)"},
                    {"": "Net income", "For Three Months Ended": "16,016"},
                ]
            }
        ],
        "prose_chunks": [],
        "guidance_sections": [],
    }
    result = compare_facts(output, golden)
    assert result["metrics"]["net_income"]["matched"]


def test_compare_facts_detects_guidance_in_tables():
    golden = {
        "value_scale": "millions",
        "key_metrics": {},
        "has_guidance": True,
        "min_tables": 1,
    }
    output = {
        "tables": [{"rows": [{"": "Q1 2026 Guidance"}, {"": "Total Revenue", "col_1": "$28.5M"}]}],
        "prose_chunks": [],
        "guidance_sections": [],
    }
    result = compare_facts(output, golden)
    assert result["guidance_ok"]


def test_compare_facts_no_metrics_filing():
    golden = {
        "value_scale": "millions",
        "key_metrics": {},
        "has_guidance": False,
        "min_tables": 0,
    }
    output = {"tables": [], "prose_chunks": [{"text": "Investor website update"}], "guidance_sections": []}
    result = compare_facts(output, golden)
    assert result["required_metric_recall"] == 1.0
    assert result["tables_ok"]


def test_golden_files_exist_for_raw1():
    raw_files = {p.stem for p in Path("data/raw1").glob("*.html")}
    golden_files = {p.stem for p in Path("data/golden").glob("*.json")}
    assert raw_files == golden_files


def test_golden_files_are_valid_json():
    for path in Path("data/golden").glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "filing_id" in data
        assert "ticker" in data
        assert "key_metrics" in data


def test_blnd_ingest_matches_golden_metrics():
    html = Path("data/raw/BLND_2025_Q4.html").read_text(encoding="utf-8", errors="replace")
    golden = json.loads(Path("data/golden/BLND_2025_Q4.json").read_text(encoding="utf-8"))
    tables, prose = parse_html(html)
    output = {
        "tables": [{"rows": table.rows} for table in tables],
        "prose_chunks": [{"text": chunk.text} for chunk in prose],
        "guidance_sections": [],
    }
    result = compare_facts(output, golden)
    assert result["metrics"]["total_revenue"]["matched"]
    assert result["metrics"]["net_income"]["matched"]
    assert result["guidance_ok"]
