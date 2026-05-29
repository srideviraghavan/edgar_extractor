"""LLM extraction layer - call LLM for each chunk type."""

import os
from pathlib import Path
from typing import Any
from portkey_ai import Portkey
from .schema import TableData, ProseChunk, GuidanceSection


def extract_from_table(table: TableData, model: str) -> dict[str, Any]:
    """
    Extract structured data from a table using LLM.
    
    Args:
        table: TableData object with HTML table content
        model: Model name to use for extraction
        
    Returns:
        Dictionary with extracted data and metadata
    """
    prompt_template = _load_prompt("table.txt")
    
    # Format table data for prompt
    table_str = f"Headers: {table.headers}\n"
    table_str += f"Rows: {table.rows}"
    
    prompt = prompt_template.format(table_data=table_str)
    
    response = _call_llm(prompt, model)
    
    return {
        "extracted_data": response,
        "confidence": 0.8,  # Placeholder - should be calculated from response
        "model_used": model,
    }


def extract_from_prose(prose: ProseChunk, model: str) -> dict[str, Any]:
    """
    Extract structured data from prose using LLM.
    
    Args:
        prose: ProseChunk object with text content
        model: Model name to use for extraction
        
    Returns:
        Dictionary with extracted data and metadata
    """
    prompt_template = _load_prompt("prose.txt")
    
    prompt = prompt_template.format(
        section_header=prose.section_header or "Unknown",
        text=prose.text
    )
    
    response = _call_llm(prompt, model)
    
    return {
        "extracted_data": response,
        "confidence": 0.8,  # Placeholder
        "model_used": model,
    }


def extract_from_guidance(guidance: GuidanceSection, model: str) -> dict[str, Any]:
    """
    Extract guidance from management guidance sections.
    
    Args:
        guidance: GuidanceSection object
        model: Model name to use for extraction
        
    Returns:
        Dictionary with extracted guidance and metadata
    """
    prompt_template = _load_prompt("guidance.txt")
    
    prompt = prompt_template.format(
        title=guidance.title,
        content=guidance.content
    )
    
    response = _call_llm(prompt, model)
    
    return {
        "extracted_guidance": response,
        "confidence": 0.8,  # Placeholder
        "model_used": model,
    }


def _load_prompt(template_name: str) -> str:
    """Load prompt template from file."""
    prompt_dir = Path(__file__).parent / "prompts"
    prompt_file = prompt_dir / template_name
    
    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt template not found: {prompt_file}")
    
    return prompt_file.read_text()


def _call_llm(prompt: str, model: str) -> dict[str, Any]:
    """
    Call LLM via Portkey API.
    
    Args:
        prompt: The prompt to send
        model: Model name
        
    Returns:
        Parsed JSON response
    """
    # api_key = os.getenv("PORTKEY_API_KEY")
    api_key = "zegUWxApwnf7Xl4JUZj3qEsdmdoc"
    if not api_key:
        raise ValueError("PORTKEY_API_KEY environment variable not set")
    
    client = Portkey(api_key=api_key)
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a financial data extraction assistant."},
            {"role": "user", "content": prompt},
        ],
        temperature=float(os.getenv("TEMPERATURE", "0.1")),
        max_completion_tokens=int(os.getenv("MAX_COMPLETION_TOKENS", "4096")),
    )
    
    # Parse response as JSON
    content = response.choices[0].message.content
    
    try:
        import json
        return json.loads(content)
    except json.JSONDecodeError:
        return {"raw_response": content}
