"""Build golden evaluation files from raw1 HTML filings.

Run from repo root:
    python eval/build_golden.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

RAW_DIR = Path("data/raw1")
GOLDEN_DIR = Path("data/golden")

# Manually verified overrides for filings where heuristics are unreliable.
OVERRIDES: dict[str, dict] = {
    "API_2023_Q1": {
        "company_name": "Agora, Inc.",
        "currency": "USD",
        "value_scale": "thousands",
        "key_metrics": {
            "total_revenue": {"value": 36443, "required": True},
            "net_income": {"value": -16802, "required": True},
            "eps_diluted": {"value": -0.16, "required": False},
        },
        "has_guidance": True,
        "min_tables": 5,
        "tags": ["multi_period_tables", "non_gaap_reconciliation"],
    },
    "BLND_2025_Q4": {
        "company_name": "Blend Labs, Inc.",
        "currency": "USD",
        "value_scale": "thousands",
        "key_metrics": {
            "total_revenue": {"value": 32368, "required": True},
            "net_income": {"value": -2581, "required": True},
            "eps_diluted": {"value": -0.03, "required": False},
        },
        "has_guidance": True,
        "min_tables": 8,
        "tags": ["continuing_operations"],
    },
    "COHU_2025_Q4": {
        "company_name": "Cohu, Inc.",
        "currency": "USD",
        "value_scale": "millions",
        "key_metrics": {
            "total_revenue": {"value": 122.2, "required": True},
            "net_income": {"value": -22.5, "required": True},
        },
        "has_guidance": True,
        "min_tables": 10,
        "tags": ["prose_and_tables", "many_tables"],
    },
    "GFS_2025_Q4": {
        "company_name": "GLOBALFOUNDRIES Inc.",
        "currency": "USD",
        "value_scale": "millions",
        "key_metrics": {
            "total_revenue": {"value": 1830, "required": True},
            "net_income": {"value": 200, "required": True},
            "eps_diluted": {"value": 0.36, "required": False},
        },
        "has_guidance": True,
        "min_tables": 10,
        "tags": ["non_ifrs", "segment_tables"],
    },
    "INFA_2025_Q3": {
        "company_name": "Informatica Inc.",
        "currency": "USD",
        "value_scale": "thousands",
        "key_metrics": {
            "total_revenue": {"value": 439161, "required": True},
            "net_income": {"value": 3998, "required": False},
        },
        "has_guidance": True,
        "min_tables": 8,
        "tags": ["large_tables"],
    },
    "IS_2021_Q4": {
        "company_name": "ironSource Ltd.",
        "currency": "USD",
        "value_scale": "millions",
        "key_metrics": {
            "net_income": {"value": 20.805, "required": True},
        },
        "has_guidance": True,
        "min_tables": 10,
        "tags": ["full_year_and_quarter"],
    },
    "MXL_2025_Q4": {
        "company_name": "MaxLinear, Inc.",
        "currency": "USD",
        "value_scale": "thousands",
        "key_metrics": {
            "net_income": {"value": -14897, "required": True},
            "eps_diluted": {"value": 0.19, "required": False},
        },
        "has_guidance": True,
        "min_tables": 8,
        "tags": ["non_gaap_eps"],
    },
    "SIMO_2021_Q4": {
        "company_name": "Silicon Motion Technology Corporation",
        "currency": "USD",
        "value_scale": "millions",
        "key_metrics": {
            "net_income": {"value": 16.016, "required": True},
        },
        "has_guidance": False,
        "min_tables": 6,
        "tags": ["filename_period_mismatch"],
    },
    "SKLZ_2025_Q4": {
        "company_name": "Skillz Inc.",
        "currency": "USD",
        "value_scale": "thousands",
        "key_metrics": {
            "net_income": {"value": -17902, "required": True},
        },
        "has_guidance": True,
        "min_tables": 5,
        "tags": [],
    },
    "SLAB_2025_Q3": {
        "company_name": "Silicon Laboratories Inc.",
        "currency": "USD",
        "value_scale": "millions",
        "key_metrics": {
            "total_revenue": {"value": 206, "required": True},
            "net_income": {"value": -12, "required": False},
            "eps_diluted": {"value": -0.30, "required": False},
        },
        "segments": [
            {"name": "Industrial & Commercial", "value": 118},
            {"name": "Home & Life", "value": 88},
        ],
        "has_guidance": True,
        "min_tables": 6,
        "tags": ["prose_bullets", "forward_guidance"],
    },
    "SPOT_2023_Q1": {
        "company_name": "Spotify Technology S.A.",
        "currency": "USD",
        "value_scale": "millions",
        "key_metrics": {},
        "has_guidance": False,
        "min_tables": 0,
        "tags": ["no_financial_data", "prose_only"],
    },
    "TRIP_2025_Q4": {
        "company_name": "Tripadvisor, Inc.",
        "currency": "USD",
        "value_scale": "millions",
        "key_metrics": {
            "total_revenue": {"value": 371.5, "required": True},
        },
        "has_guidance": False,
        "min_tables": 2,
        "tags": ["decimal_millions"],
    },
    "TSEM_2022_Q2": {
        "company_name": "Tower Semiconductor Ltd.",
        "currency": "USD",
        "value_scale": "millions",
        "key_metrics": {
            "total_revenue": {"value": 426, "required": True},
            "net_income": {"value": 73, "required": False},
            "gross_profit": {"value": 112, "required": False},
        },
        "has_guidance": True,
        "min_tables": 4,
        "tags": ["prose_primary"],
    },
    "TSM_2024_Q2": {
        "company_name": "Taiwan Semiconductor Manufacturing Company Limited",
        "currency": "TWD",
        "value_scale": "thousands",
        "key_metrics": {
            "net_income": {"value": 247661438, "required": True},
            "eps_diluted": {"value": 9.56, "required": False},
        },
        "has_guidance": True,
        "min_tables": 50,
        "tags": ["very_large_filing", "scale_thousands"],
    },
    "UMC_2021_Q3": {
        "company_name": "United Microelectronics Corporation",
        "currency": "USD",
        "value_scale": "millions",
        "key_metrics": {
            "net_income": {"value": 17.460, "required": True},
        },
        "has_guidance": True,
        "min_tables": 15,
        "tags": [],
    },
    "VECO_2025_Q4": {
        "company_name": "Veeco Instruments Inc.",
        "currency": "USD",
        "value_scale": "millions",
        "key_metrics": {
            "net_income": {"value": 1.1, "required": True},
            "eps_diluted": {"value": 0.02, "required": False},
        },
        "has_guidance": True,
        "min_tables": 15,
        "tags": [],
    },
    "VRM_2024_Q3": {
        "company_name": "Vroom, Inc.",
        "currency": "USD",
        "value_scale": "millions",
        "key_metrics": {},
        "has_guidance": False,
        "min_tables": 5,
        "tags": ["bankruptcy_filing", "not_earnings_release"],
    },
    "WEAV_2025_Q4": {
        "company_name": "Weave Communications, Inc.",
        "currency": "USD",
        "value_scale": "millions",
        "key_metrics": {
            "total_revenue": {"value": 63.4, "required": True},
            "net_income": {"value": -1.8, "required": True},
            "eps_diluted": {"value": -0.02, "required": False},
        },
        "has_guidance": True,
        "min_tables": 6,
        "tags": ["prose_and_tables"],
    },
    "WISH_2024_Q1": {
        "company_name": "ContextLogic Inc.",
        "currency": "USD",
        "value_scale": "millions",
        "key_metrics": {
            "net_income": {"value": -59, "required": True},
        },
        "has_guidance": False,
        "min_tables": 4,
        "tags": ["short_filing"],
    },
    "ZIP_2023_Q4": {
        "company_name": "ZipRecruiter, Inc.",
        "currency": "USD",
        "value_scale": "thousands",
        "key_metrics": {
            "net_income": {"value": -32994, "required": True},
        },
        "has_guidance": True,
        "min_tables": 1,
        "tags": ["shareholder_letter_redirect", "minimal_tables"],
    },
}


def parse_filename(stem: str) -> tuple[str, int, str]:
    ticker, year, quarter = stem.split("_")
    return ticker, int(year), quarter


def build_golden(filing_id: str) -> dict:
    ticker, fiscal_year, fiscal_quarter = parse_filename(filing_id)
    base = {
        "filing_id": filing_id,
        "ticker": ticker,
        "fiscal_year": fiscal_year,
        "fiscal_quarter": fiscal_quarter,
        "company_name": None,
        "currency": "USD",
        "value_scale": "thousands",
        "key_metrics": {},
        "segments": [],
        "has_guidance": False,
        "min_tables": 1,
        "tags": [],
    }
    override = OVERRIDES.get(filing_id, {})
    base.update(override)
    return base


def main() -> None:
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    html_files = sorted(RAW_DIR.glob("*.html"))
    if not html_files:
        raise SystemExit(f"No HTML files found in {RAW_DIR}")

    for html_file in html_files:
        filing_id = html_file.stem
        golden = build_golden(filing_id)
        out_path = GOLDEN_DIR / f"{filing_id}.json"
        out_path.write_text(json.dumps(golden, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
