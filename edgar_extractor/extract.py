"""LLM extraction layer - call LLM for each chunk type."""

import os
import tiktoken
from pathlib import Path
from typing import Any
from openai import OpenAI
from .schema import TableData, ProseChunk, GuidanceSection


# Token limits
MAX_INPUT_TOKENS = int(os.getenv("MAX_INPUT_TOKENS", "50000"))


def _count_tokens(text: str) -> int:
    """Count tokens in text using GPT-4 tokenizer."""
    enc = tiktoken.encoding_for_model("gpt-4")
    return len(enc.encode(text))


def extract_from_table(table: TableData, model: str, cost_tracker=None) -> dict[str, Any]:
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
    
    # Check token count and batch if needed
    token_count = _count_tokens(table_str)
    print(f"\n=== TABLE EXTRACTION ===")
    print(f"Token count: {token_count}")
    print(f"Max input tokens: {MAX_INPUT_TOKENS}")
    print(f"Input to model (table_str):\n{table_str[:500]}...")
    
    if token_count > MAX_INPUT_TOKENS:
        print(f"⚠ Token count exceeds limit, batching...")
        return _extract_table_batched(table, model, prompt_template, cost_tracker)
    
    prompt = prompt_template.format(table_data=table_str)
    print(f"Full prompt being sent to model:\n{prompt[:1000]}...")
    response = _call_llm(prompt, model, cost_tracker)
    
    return {
        "extracted_data": response,
        "confidence": 0.8,  # Placeholder - should be calculated from response
        "model_used": model,
        "token_count": token_count,
    }


def extract_from_prose(prose: ProseChunk, model: str, cost_tracker=None) -> dict[str, Any]:
    """
    Extract structured data from prose using LLM.
    
    Args:
        prose: ProseChunk object with text content
        model: Model name to use for extraction
        
    Returns:
        Dictionary with extracted data and metadata
    """
    prompt_template = _load_prompt("prose.txt")
    
    # Check token count and split if needed
    token_count = _count_tokens(prose.text)
    print(f"\n=== PROSE EXTRACTION ===")
    print(f"Section header: {prose.section_header}")
    print(f"Token count: {token_count}")
    print(f"Max input tokens: {MAX_INPUT_TOKENS}")
    print(f"Input to model (prose.text):\n{prose.text[:500]}...")
    
    if token_count > MAX_INPUT_TOKENS:
        print(f"⚠ Token count exceeds limit, splitting...")
        return _extract_prose_split(prose, model, prompt_template, cost_tracker)
    
    prompt = prompt_template.format(
        section_header=prose.section_header or "Unknown",
        text=prose.text
    )
    print(f"Full prompt being sent to model:\n{prompt[:1000]}...")
    
    response = _call_llm(prompt, model, cost_tracker)
    
    return {
        "extracted_data": response,
        "confidence": 0.8,  # Placeholder
        "model_used": model,
        "token_count": token_count,
    }


def extract_from_guidance(guidance: GuidanceSection, model: str, cost_tracker=None) -> dict[str, Any]:
    """
    Extract guidance from management guidance sections.
    
    Args:
        guidance: GuidanceSection object
        model: Model name to use for extraction
        
    Returns:
        Dictionary with extracted guidance and metadata
    """
    prompt_template = _load_prompt("guidance.txt")
    
    token_count = _count_tokens(guidance.content)
    print(f"\n=== GUIDANCE EXTRACTION ===")
    print(f"Title: {guidance.title}")
    print(f"Token count: {token_count}")
    print(f"Input to model (content):\n{guidance.content[:500]}...")
    
    prompt = prompt_template.format(
        title=guidance.title,
        content=guidance.content
    )
    print(f"Full prompt being sent to model:\n{prompt[:1000]}...")
    
    response = _call_llm(prompt, model, cost_tracker)
    
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


def _extract_table_batched(table: TableData, model: str, prompt_template: str, cost_tracker=None) -> dict[str, Any]:
    """Extract from table in batches if it exceeds token limit."""
    batch_size = max(1, len(table.rows) // 3)  # Split into ~3 batches
    results = []
    
    print(f"Total rows: {len(table.rows)}")
    print(f"Batch size: {batch_size}")
    print(f"Number of batches: {(len(table.rows) + batch_size - 1) // batch_size}")
    
    for i in range(0, len(table.rows), batch_size):
        batch_rows = table.rows[i:i + batch_size]
        table_str = f"Headers: {table.headers}\n"
        table_str += f"Rows: {batch_rows}"
        
        batch_token_count = _count_tokens(table_str)
        print(f"\n--- Batch {i // batch_size + 1} ---")
        print(f"Rows in batch: {len(batch_rows)}")
        print(f"Token count for batch: {batch_token_count}")
        print(f"Input to model (batch):\n{table_str[:500]}...")
        
        prompt = prompt_template.format(table_data=table_str)
        response = _call_llm(prompt, model, cost_tracker)
        results.append(response)
    
    # Merge results
    merged = {"batch_results": results}
    return {
        "extracted_data": merged,
        "confidence": 0.7,  # Lower confidence for batched results
        "model_used": model,
        "batched": True,
    }


def _extract_prose_split(prose: ProseChunk, model: str, prompt_template: str, cost_tracker=None) -> dict[str, Any]:
    """Extract from prose in chunks if it exceeds token limit."""
    enc = tiktoken.encoding_for_model("gpt-4")
    tokens = enc.encode(prose.text)
    
    print(f"Total tokens in original text: {len(tokens)}")
    
    # Split into chunks
    chunk_size = MAX_INPUT_TOKENS
    chunks = []
    for i in range(0, len(tokens), chunk_size):
        chunk_tokens = tokens[i:i + chunk_size]
        chunk_text = enc.decode(chunk_tokens)
        chunks.append(chunk_text)
    
    print(f"Number of chunks: {len(chunks)}")
    print(f"Chunk size (tokens): {chunk_size}")
    
    results = []
    for idx, chunk_text in enumerate(chunks):
        chunk_token_count = _count_tokens(chunk_text)
        print(f"\n--- Chunk {idx + 1}/{len(chunks)} ---")
        print(f"Token count for chunk: {chunk_token_count}")
        print(f"Input to model (chunk):\n{chunk_text[:500]}...")
        
        prompt = prompt_template.format(
            section_header=f"{prose.section_header or 'Unknown'} (Part {idx + 1}/{len(chunks)})",
            text=chunk_text
        )
        response = _call_llm(prompt, model, cost_tracker)
        results.append(response)
    
    # Merge results
    merged = {"chunk_results": results}
    return {
        "extracted_data": merged,
        "confidence": 0.7,  # Lower confidence for split results
        "model_used": model,
        "split": True,
    }


def _call_llm(prompt: str, model: str, cost_tracker=None) -> dict[str, Any]:
    """
    Call LLM via OpenAI-compatible API (Portkey or local LM Studio).

    Args:
        prompt: The prompt to send
        model: Model name

    Returns:
        Parsed JSON response
    """
    base_url = os.getenv("BASE_URL", "https://api.portkey.ai/v1/")
    api_key = os.getenv("PORTKEY_API_KEY") or os.getenv("API_KEY")
    if not api_key:
        raise ValueError("PORTKEY_API_KEY environment variable not set")

    print(f"\n=== LLM API CALL ===")
    print(f"Model: {model}")
    print(f"Base URL: {base_url}")
    print(f"Temperature: {os.getenv('TEMPERATURE', '0.1')}")
    max_completion_tokens = os.getenv("MAX_COMPLETION_TOKENS", "4096")
    if max_completion_tokens.lower() == "none":
        max_completion_tokens = None
    print(
        f"Max completion tokens: {max_completion_tokens if max_completion_tokens else 'None (use model default)'}"
    )

    client = OpenAI(base_url=base_url, api_key=api_key)
    
    # Build API parameters
    api_params = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a financial data extraction assistant."},
            {"role": "user", "content": prompt},
        ],
        "temperature": float(os.getenv("TEMPERATURE", "0.1")),
    }
    
    if max_completion_tokens is not None:
        api_params["max_completion_tokens"] = int(max_completion_tokens)
    
    response = client.chat.completions.create(**api_params)
    
    # Track token usage if cost_tracker is provided
    if cost_tracker and hasattr(response, 'usage') and response.usage:
        total_tokens = response.usage.total_tokens
        cost_tracker.add_usage(model, total_tokens)
        print(f"\n=== TOKEN USAGE ===")
        print(f"Prompt tokens: {response.usage.prompt_tokens}")
        print(f"Completion tokens: {response.usage.completion_tokens}")
        print(f"Total tokens: {total_tokens}")
    
    # Parse response as JSON
    content = response.choices[0].message.content
    print(f"\n=== LLM RESPONSE ===")
    print(f"Response content:\n{content[:1000]}...")
    
    try:
        import json
        parsed = json.loads(content)
        print(f"Parsed JSON successfully")
        return parsed
    except json.JSONDecodeError:
        print(f"Failed to parse as JSON, returning raw response")
        return {"raw_response": content}
