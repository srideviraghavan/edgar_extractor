"""Scoring helpers for evaluation metrics."""

from typing import Any, Dict, Set


def calculate_f1(output: Dict[str, Any], golden: Dict[str, Any]) -> float:
    """
    Calculate F1 score between output and golden JSON.
    
    Args:
        output: Pipeline output JSON
        golden: Golden (expected) JSON
        
    Returns:
        F1 score between 0 and 1
    """
    # Extract entities from both
    output_entities = _extract_entities(output)
    golden_entities = _extract_entities(golden)
    
    if not golden_entities:
        return 1.0 if not output_entities else 0.0
    
    # Calculate precision, recall, F1
    true_positives = len(output_entities & golden_entities)
    false_positives = len(output_entities - golden_entities)
    false_negatives = len(golden_entities - output_entities)
    
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
    
    if precision + recall == 0:
        return 0.0
    
    f1 = 2 * (precision * recall) / (precision + recall)
    return f1


def calculate_exact_match(output: Dict[str, Any], golden: Dict[str, Any]) -> bool:
    """
    Check if output exactly matches golden JSON.
    
    Args:
        output: Pipeline output JSON
        golden: Golden (expected) JSON
        
    Returns:
        True if exact match, False otherwise
    """
    return output == golden


def compare_structures(output: Dict[str, Any], golden: Dict[str, Any]) -> float:
    """
    Compare structural similarity between output and golden.
    
    Args:
        output: Pipeline output JSON
        golden: Golden (expected) JSON
        
    Returns:
        Structure similarity score between 0 and 1
    """
    output_keys = set(output.keys())
    golden_keys = set(golden.keys())
    
    # Key overlap
    key_overlap = len(output_keys & golden_keys) / len(golden_keys) if golden_keys else 1.0
    
    # Nested structure comparison
    structure_score = 0.0
    total_nested = 0
    
    for key in golden_keys:
        if key in output:
            golden_val = golden[key]
            output_val = output[key]
            
            if isinstance(golden_val, list) and isinstance(output_val, list):
                # Compare list lengths
                if len(golden_val) > 0:
                    structure_score += min(len(output_val), len(golden_val)) / len(golden_val)
                    total_nested += 1
            elif isinstance(golden_val, dict) and isinstance(output_val, dict):
                # Compare dict keys
                golden_subkeys = set(golden_val.keys())
                output_subkeys = set(output_val.keys())
                if golden_subkeys:
                    structure_score += len(golden_subkeys & output_subkeys) / len(golden_subkeys)
                    total_nested += 1
    
    if total_nested > 0:
        structure_score /= total_nested
    
    # Combine key overlap and structure score
    return (key_overlap + structure_score) / 2


def _extract_entities(data: Dict[str, Any]) -> Set[str]:
    """
    Extract entities from JSON for comparison.
    
    Args:
        data: JSON data
        
    Returns:
        Set of entity signatures
    """
    entities = set()
    
    def extract_recursive(obj: Any, path: str = "") -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_path = f"{path}.{key}" if path else key
                if key in ["name", "ticker", "cik", "entity"]:
                    if isinstance(value, str):
                        entities.add(f"{new_path}:{value}")
                extract_recursive(value, new_path)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                extract_recursive(item, f"{path}[{i}]")
    
    extract_recursive(data)
    return entities


def calculate_field_coverage(output: Dict[str, Any], golden: Dict[str, Any]) -> Dict[str, float]:
    """
    Calculate coverage of expected fields in output.
    
    Args:
        output: Pipeline output JSON
        golden: Golden (expected) JSON
        
    Returns:
        Dictionary with coverage metrics per section
    """
    coverage = {}
    
    sections = ["tables", "prose_chunks", "guidance_sections"]
    
    for section in sections:
        if section in golden:
            golden_count = len(golden[section]) if isinstance(golden[section], list) else 1
            output_count = len(output.get(section, [])) if isinstance(output.get(section), list) else 0
            
            if golden_count > 0:
                coverage[section] = output_count / golden_count
            else:
                coverage[section] = 1.0
        else:
            coverage[section] = 1.0  # Section not expected
    
    return coverage
