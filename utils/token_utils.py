"""
Token counting utilities for managing API context limits

This module provides functions for estimating token counts to ensure
requests stay within the Gemini API's context window limits.

Note: The estimation uses a simple character-to-token ratio which is
approximate. For production systems requiring precise token counts,
consider using the actual tokenizer for the specific model.
"""

# Default fallback for token limit (conservative estimate)
DEFAULT_CONTEXT_WINDOW = 200_000  # Conservative fallback for unknown models


def estimate_tokens(text: str) -> int:
    """
    Estimate token count using a character-based approximation.

    This uses a rough heuristic where 1 token ≈ 4 characters, which is
    a reasonable approximation for English text. The actual token count
    may vary based on:
    - Language (non-English text may have different ratios)
    - Code vs prose (code often has more tokens per character)
    - Special characters and formatting

    Args:
        text: The text to estimate tokens for

    Returns:
        int: Estimated number of tokens
    """
    return len(text) // 4


def check_token_limit(text: str, context_window: int = DEFAULT_CONTEXT_WINDOW) -> tuple[bool, int]:
    """
    Check if text exceeds the specified token limit.

    This function is used to validate that prepared prompts will fit
    within the model's context window, preventing API errors and ensuring
    reliable operation.

    Args:
        text: The text to check
        context_window: The model's context window size (defaults to conservative fallback)

    Returns:
        Tuple[bool, int]: (is_within_limit, estimated_tokens)
        - is_within_limit: True if the text fits within context_window
        - estimated_tokens: The estimated token count
    """
    estimated = estimate_tokens(text)
    return estimated <= context_window, estimated
