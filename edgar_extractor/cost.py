"""Cost tracking - token counting and cost calculation."""

from typing import Dict, Any
from dataclasses import dataclass, field


@dataclass
class CostTracker:
    """Track token usage and costs per model."""
    
    model_costs: Dict[str, float] = field(default_factory=dict)
    token_counts: Dict[str, int] = field(default_factory=dict)
    
    # Default costs per 1K tokens (adjust based on actual pricing)
    DEFAULT_COSTS = {
        "gpt-4o": 0.005,  # $0.005 per 1K tokens
        "gpt-4": 0.03,
        "gpt-3.5-turbo": 0.0015,
    }
    
    def add_usage(self, model: str, tokens: int) -> None:
        """
        Add token usage for a model.
        
        Args:
            model: Model name
            tokens: Number of tokens used
        """
        if model not in self.token_counts:
            self.token_counts[model] = 0
        self.token_counts[model] += tokens
        
        # Calculate cost
        cost_per_1k = self.DEFAULT_COSTS.get(model, 0.01)
        cost = (tokens / 1000) * cost_per_1k
        
        if model not in self.model_costs:
            self.model_costs[model] = 0.0
        self.model_costs[model] += cost
    
    def get_total_cost(self) -> float:
        """Get total cost across all models."""
        return sum(self.model_costs.values())
    
    def get_total_tokens(self) -> int:
        """Get total tokens across all models."""
        return sum(self.token_counts.values())
    
    def get_report(self) -> str:
        """Generate a cost report."""
        lines = ["Cost Report:", "=" * 40]
        
        for model, cost in self.model_costs.items():
            tokens = self.token_counts.get(model, 0)
            lines.append(f"{model}:")
            lines.append(f"  Tokens: {tokens:,}")
            lines.append(f"  Cost: ${cost:.4f}")
        
        lines.append("=" * 40)
        lines.append(f"Total Tokens: {self.get_total_tokens():,}")
        lines.append(f"Total Cost: ${self.get_total_cost():.4f}")
        
        return "\n".join(lines)


def estimate_tokens(text: str) -> int:
    """
    Estimate token count for text.
    
    Args:
        text: Text to estimate tokens for
        
    Returns:
        Estimated token count
    """
    # Rough estimate: ~4 characters per token
    return len(text) // 4


def count_tokens_from_response(response: Any) -> int:
    """
    Count tokens from LLM response.
    
    Args:
        response: LLM response object
        
    Returns:
        Token count
    """
    # Placeholder - in production, use tiktoken or similar
    if hasattr(response, "usage"):
        return response.usage.total_tokens
    return estimate_tokens(str(response))
