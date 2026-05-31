"""Scoring helpers for evaluation metrics."""

from __future__ import annotations

from typing import Any, Set, Tuple


LeafPair = Tuple[str, str]


def _serialize_value(value: Any) -> str:
    """Type-aware serialization for leaf comparison."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return f"int:{value}"
    if isinstance(value, float):
        return f"float:{value}"
    if isinstance(value, str):
        return f"str:{value}"
    return f"{type(value).__name__}:{value!r}"


def extract_leaf_pairs(data: Any, path: str = "") -> Set[LeafPair]:
    """
    Extract (field_path, value) pairs from nested JSON.

    Array indices are included as numeric path segments.
    """
    pairs: Set[LeafPair] = set()

    if isinstance(data, dict):
        for key, value in data.items():
            new_path = f"{path}.{key}" if path else str(key)
            if isinstance(value, (dict, list)):
                pairs.update(extract_leaf_pairs(value, new_path))
            else:
                pairs.add((new_path, _serialize_value(value)))
    elif isinstance(data, list):
        for index, item in enumerate(data):
            new_path = f"{path}.{index}" if path else str(index)
            if isinstance(item, (dict, list)):
                pairs.update(extract_leaf_pairs(item, new_path))
            else:
                pairs.add((new_path, _serialize_value(item)))
    else:
        pairs.add((path or "root", _serialize_value(data)))

    return pairs


def calculate_f1(output: dict[str, Any], golden: dict[str, Any]) -> float:
    """
    Calculate F1 score between output and golden JSON using leaf field paths.

    Each (field_path, value) pair is treated as an entity. Comparison is
    type-aware via serialized values.
    """
    output_entities = extract_leaf_pairs(output)
    golden_entities = extract_leaf_pairs(golden)

    if not golden_entities:
        return 1.0 if not output_entities else 0.0

    true_positives = len(output_entities & golden_entities)
    false_positives = len(output_entities - golden_entities)
    false_negatives = len(golden_entities - output_entities)

    precision = (
        true_positives / (true_positives + false_positives)
        if (true_positives + false_positives) > 0
        else 0.0
    )
    recall = (
        true_positives / (true_positives + false_negatives)
        if (true_positives + false_negatives) > 0
        else 0.0
    )

    if precision + recall == 0:
        return 0.0

    return 2 * (precision * recall) / (precision + recall)


def calculate_exact_match(output: dict[str, Any], golden: dict[str, Any]) -> bool:
    """Check if output exactly matches golden JSON."""
    return output == golden


def compare_structures(output: dict[str, Any], golden: dict[str, Any]) -> float:
    """
    Compare structural similarity between output and golden.

    Uses top-level keys and nested list/dict shapes.
    """
    output_keys = set(output.keys())
    golden_keys = set(golden.keys())

    key_overlap = len(output_keys & golden_keys) / len(golden_keys) if golden_keys else 1.0

    structure_score = 0.0
    total_nested = 0

    for key in golden_keys:
        if key not in output:
            continue

        golden_val = golden[key]
        output_val = output[key]

        if isinstance(golden_val, list) and isinstance(output_val, list):
            if len(golden_val) > 0:
                structure_score += min(len(output_val), len(golden_val)) / len(golden_val)
                total_nested += 1
        elif isinstance(golden_val, dict) and isinstance(output_val, dict):
            golden_subkeys = set(golden_val.keys())
            output_subkeys = set(output_val.keys())
            if golden_subkeys:
                structure_score += len(golden_subkeys & output_subkeys) / len(golden_subkeys)
                total_nested += 1

    if total_nested > 0:
        structure_score /= total_nested

    return (key_overlap + structure_score) / 2


def calculate_field_coverage(output: dict[str, Any], golden: dict[str, Any]) -> dict[str, float]:
    """Calculate coverage of expected list sections in output."""
    coverage: dict[str, float] = {}
    sections = ["tables", "prose_chunks", "guidance_sections"]

    for section in sections:
        if section in golden:
            golden_count = len(golden[section]) if isinstance(golden[section], list) else 1
            output_count = len(output.get(section, [])) if isinstance(output.get(section), list) else 0
            coverage[section] = output_count / golden_count if golden_count > 0 else 1.0
        else:
            coverage[section] = 1.0

    return coverage
