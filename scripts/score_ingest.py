"""Re-parse raw HTML with updated ingest and score against golden files."""
from __future__ import annotations

import json
from pathlib import Path

from edgar_extractor.ingest import parse_html
from eval.fact_metrics import compare_facts

RAW_DIR = Path("data/raw")
GOLDEN_DIR = Path("data/golden")


def main() -> None:
    results = []
    for golden_path in sorted(GOLDEN_DIR.glob("*.json")):
        raw_path = RAW_DIR / f"{golden_path.stem}.html"
        if not raw_path.exists():
            continue
        golden = json.loads(golden_path.read_text(encoding="utf-8"))
        html = raw_path.read_text(encoding="utf-8", errors="replace")
        tables, prose = parse_html(html)
        output = {
            "tables": [{"rows": table.rows} for table in tables],
            "prose_chunks": [{"text": chunk.text} for chunk in prose],
            "guidance_sections": [],
        }
        result = compare_facts(output, golden)
        results.append((golden_path.name, result))

    print(f"{'File':20} {'FactF1':>7} {'Recall':>7} {'Tables':>7} {'Guidance':>9}")
    for name, result in results:
        print(
            f"{name:20} "
            f"{result['fact_f1']:7.3f} "
            f"{result['required_metric_recall']:7.3f} "
            f"{'OK' if result['tables_ok'] else 'MISS':>7} "
            f"{'OK' if result['guidance_ok'] else 'MISS':>9}"
        )

    n = len(results)
    avg_f1 = sum(r[1]["fact_f1"] for r in results) / n
    avg_recall = sum(r[1]["required_metric_recall"] for r in results) / n
    print(f"\nAverage fact F1: {avg_f1:.3f}, required recall: {avg_recall:.3f}")


if __name__ == "__main__":
    main()
