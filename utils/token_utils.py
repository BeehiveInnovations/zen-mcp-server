"""
Token counting utilities for managing API context limits

This module provides functions for estimating token counts to ensure
requests stay within the Gemini API's context window limits.

Note: The estimation uses a simple character-to-token ratio which is
approximate. For production systems requiring precise token counts,
consider using the actual tokenizer for the specific model.
"""

from config import MAX_CONTEXT_TOKENS


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


def check_token_limit(text: str) -> tuple[bool, int]:
    """
    Check if text exceeds the maximum token limit for Gemini models.

    This function is used to validate that prepared prompts will fit
    within the model's context window, preventing API errors and ensuring
    reliable operation.

    Args:
        text: The text to check

    Returns:
        Tuple[bool, int]: (is_within_limit, estimated_tokens)
        - is_within_limit: True if the text fits within MAX_CONTEXT_TOKENS
        - estimated_tokens: The estimated token count
    """
    estimated = estimate_tokens(text)
    return estimated <= MAX_CONTEXT_TOKENS, estimated
