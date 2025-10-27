"""Shared OpenAI token estimation utilities.

This module provides reusable token estimation logic for OpenAI models,
enabling accurate token counting for both direct OpenAI API and OpenRouter-proxied calls.

The estimators follow official OpenAI API specifications:

- Text: tiktoken (o200k_base for GPT-4o/o3/o4, cl100k_base for GPT-3.5/4)

- Images: Uses openai-vision-cost library for accurate token calculation
  * Automatically handles tile-based vs patch-based formulas
  * Supports 34+ OpenAI vision models including:
    - GPT-4o family (tile-based with varying constants)
    - GPT-4.1/5 families (tile or patch depending on variant)
    - o-series models (tile or patch depending on variant)
  * Library maintained by community, tracks official OpenAI changes

- PDF: Total = Text tokens (extracted via tokenizer) + Image tokens per page (each page = one full-page image)
  * Requires proper PDF parsing for accurate estimation
  * Current implementation provides rough heuristic only (~500 tokens/page)

- Video: Not supported for token estimation
"""

import logging

import imagesize
import tiktoken
from openai_vision_cost import calculate_tokens_only
from pypdf import PdfReader

logger = logging.getLogger(__name__)

# Detail level mapping for OpenAI vision API (Gemini PR 302 pattern)
# Maps user-facing configuration values to openai-vision-cost library format
_DETAIL_MAP = {
    "LOW": "low",  # Fast, fixed ~85 tokens per image
    "HIGH": "high",  # Accurate, tile-based calculation
    "AUTO": "high",  # Phase 1: Treat AUTO as HIGH (conservative)
}


class UnsupportedContentTypeError(ValueError):
    """Raised when a model doesn't support a specific content type.

    This is a distinct error from other estimation failures, indicating
    that the model fundamentally cannot process this type of content.
    """

    def __init__(self, model_name: str, content_type: str, file_path: str = None):
        self.model_name = model_name
        self.content_type = content_type
        self.file_path = file_path
        message = f"Model {model_name} does not support {content_type}"
        if file_path:
            message += f": {file_path}"
        super().__init__(message)


# Fallback values for token estimation when metadata is unavailable
FALLBACK_IMAGE_TOKENS = 765  # Typical 1024×1024 image on gpt-4o


def is_openai_model(model_name: str) -> bool:
    """Check if a model name refers to an OpenAI model.

    Handles both direct OpenAI names (gpt-4o, gpt-5) and OpenRouter
    proxied names (openai/gpt-4o).

    Args:
        model_name: Model name to check

    Returns:
        True if model is OpenAI, False otherwise
    """
    model_lower = model_name.lower()

    # Direct OpenAI models
    if model_lower.startswith(("gpt-", "o3", "o4")):
        return True

    # OpenRouter's OpenAI models (openai/*)
    if model_lower.startswith("openai/"):
        return True

    return False


def calculate_text_tokens(model_name: str, content: str) -> int:
    """Calculate text token count using tiktoken.

    Uses OpenAI's official tokenizer with model-specific encodings:
    - o200k_base: GPT-4o, o3, o4 series
    - cl100k_base: GPT-3.5, GPT-4, GPT-4.1, GPT-5

    Args:
        model_name: The model to count tokens for
        content: Text content

    Returns:
        Token count
    """
    if not content:
        return 0

    clean_name = model_name.replace("openai/", "")

    try:
        # Try to get encoding for the specific model
        encoding = tiktoken.encoding_for_model(clean_name)
        return len(encoding.encode(content))
    except KeyError:
        # Model not found, try to infer encoding
        # GPT-4o/o3/o4 use o200k_base
        if any(x in clean_name.lower() for x in ["gpt-4o", "gpt4o", "o3", "o4"]):
            encoding = tiktoken.get_encoding("o200k_base")
        # Others use cl100k_base
        else:
            encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(content))


def estimate_image_tokens(file_path: str, model_name: str, detail: str) -> int:
    """Estimate image token count using openai-vision-cost library.

    Uses the community-maintained openai-vision-cost library which implements
    OpenAI's official token calculation formulas for 34+ vision models.

    Automatically handles:
    - Tile-based models (GPT-4o family, GPT-4.1, GPT-5, o3, o4 main models)
    - Patch-based models (mini/nano variants with multipliers)
    - Model-specific constants (e.g., gpt-4o-mini's higher tile costs)

    Args:
        file_path: Path to the image file
        model_name: Model name (supports OpenRouter prefixes like "openai/")
        detail: Detail level ("LOW", "HIGH", or "AUTO", case-insensitive).
                Must be provided by caller.

    Returns:
        Estimated token count

    Raises:
        ValueError: If file cannot be accessed or model is unsupported
    """
    # Normalize and map detail level (Gemini PR 302 pattern)
    detail_key = detail.upper()
    detail_value = _DETAIL_MAP.get(detail_key, "high")  # Default to high if invalid

    try:
        # Get image dimensions
        width, height = imagesize.get(file_path)

        # Clean model name (remove OpenRouter prefix)
        clean_model_name = model_name.replace("openai/", "")

        # Use openai-vision-cost library for calculation
        result = calculate_tokens_only(width, height, clean_model_name, detail_value)
        return result["text_tokens"]  # Final tokens after multiplier

    except (FileNotFoundError, PermissionError, OSError) as e:
        if isinstance(e, FileNotFoundError):
            raise ValueError(f"Image file not found for token estimation: {file_path}") from e
        elif isinstance(e, PermissionError):
            raise ValueError(f"Permission denied accessing image file: {file_path}") from e
        else:
            raise ValueError(f"Cannot access image file {file_path}: {e}") from e
    except Exception as e:
        logger.warning(
            "Image token estimation failed for %s with model %s: %s, using fallback",
            file_path,
            model_name,
            e,
        )
        # Conservative fallback
        return FALLBACK_IMAGE_TOKENS


def estimate_pdf_tokens(file_path: str, model_name: str, detail: str) -> int:
    """Estimate PDF token count using official OpenAI formula.

    Official OpenAI PDF token calculation:
    Total = Text tokens + Image tokens per page

    - Text: Extract text from PDF, count with tiktoken
    - Images: Each page rendered as one full-page image
      * Reads actual MediaBox dimensions per page (handles A4, Letter, Legal, etc.)
      * Handles page rotation (/Rotate)
      * Calculates image tokens based on aspect ratio and 512×512 tile formula
        - Token count depends ONLY on aspect ratio r = long_edge / short_edge
        - DPI/physical size does not affect calculation
        - Common sizes: A4≈6 tiles, Letter≈4 tiles, Legal≈6 tiles (HIGH/AUTO mode)
      * Uses openai-vision-cost library for automatic model-specific token calculation

    References:
    - OpenAI Platform PDF docs: https://platform.openai.com/docs/guides/pdf-files
    - Image token pricing: https://openai.com/api/pricing/
    - Vision API docs: https://platform.openai.com/docs/guides/images-vision

    Args:
        file_path: Path to the PDF file
        model_name: Model name for token calculation
        detail: Detail level ("LOW", "HIGH", or "AUTO", case-insensitive).
                Must be provided by caller.

    Returns:
        Estimated token count (text tokens + image tokens for all pages)

    Raises:
        ValueError: If file cannot be accessed or is invalid
    """
    # Normalize and map detail level (Gemini PR 302 pattern)
    detail_key = detail.upper()
    detail_value = _DETAIL_MAP.get(detail_key, "high")  # Default to high if invalid

    try:
        # Open PDF and extract text
        reader = PdfReader(file_path)
        num_pages = len(reader.pages)

        # Extract all text from PDF
        full_text = ""
        for page in reader.pages:
            try:
                full_text += page.extract_text() or ""
            except Exception as e:
                logger.warning(f"Failed to extract text from a page in {file_path}: {e}")

        # Calculate text tokens using tiktoken
        text_tokens = calculate_text_tokens(model_name, full_text)

        # Calculate image tokens per page
        # Each page is rendered as a full-page image, regardless of embedded images
        # Token calculation is based on aspect ratio and tile formula (not DPI)
        clean_model_name = model_name.replace("openai/", "")
        total_image_tokens = 0

        for page_num, page in enumerate(reader.pages, start=1):
            try:
                # Get page dimensions from MediaBox (in PDF points, 1/72 inch)
                mediabox = page.mediabox
                width_pt = float(mediabox.width)
                height_pt = float(mediabox.height)

                # Handle page rotation
                rotation = page.get("/Rotate", 0)
                if rotation in (90, 270):
                    # Swap width and height for rotated pages
                    width_pt, height_pt = height_pt, width_pt

                # Convert PDF points (1/72 inch) to "pixels" ONLY to preserve aspect ratio.
                # Vision pricing depends on the resize-then-512×512-tiling pipeline;
                # token count is driven by r = long_edge / short_edge, not DPI/physical size.
                # The (96/72) factor is a convenient mapping to keep r intact for the cost library;
                # absolute pixel values don't matter for token count—only the aspect ratio does.
                page_width_px = int(width_pt * 96 / 72)
                page_height_px = int(height_pt * 96 / 72)

                # Calculate per-page image tokens via openai-vision-cost.
                # The lib automatically:
                # - picks the right formula by model & detail (low/high);
                # - uses the common-paper approximation tiles ≈ 2 × ceil(1.5 × r) when r ≤ 2.667;
                # - falls back to tiles = ceil(W/512) × ceil(H/512) for extra-long pages (r > 2.667),
                #   where W/H follow the "cap longest side to 2048; set shortest to 768" resize;
                # - applies model-specific constants (base_tokens, per_tile_tokens).
                result = calculate_tokens_only(page_width_px, page_height_px, clean_model_name, detail_value)
                page_image_tokens = result["text_tokens"]
                total_image_tokens += page_image_tokens

                logger.debug(
                    f"Page {page_num}: {width_pt:.1f}×{height_pt:.1f} pt "
                    f"({page_width_px}×{page_height_px} px), "
                    f"rotation={rotation}°, tokens={page_image_tokens}"
                )

            except Exception as e:
                # Fallback for problematic pages: use common A4 size
                logger.warning(
                    f"Failed to get dimensions for page {page_num} in {file_path}: {e}. "
                    f"Using fallback A4 size (595×842 pt)."
                )
                # A4: 595×842 pt → 794×1123 px at 96 DPI
                fallback_result = calculate_tokens_only(794, 1123, clean_model_name, detail_value)
                total_image_tokens += fallback_result["text_tokens"]

        # Total tokens = text tokens + image tokens
        total_tokens = text_tokens + total_image_tokens

        logger.info(
            f"PDF token estimation for {file_path}: "
            f"{num_pages} pages, {text_tokens} text tokens, "
            f"{total_image_tokens} image tokens "
            f"(avg {total_image_tokens//num_pages if num_pages > 0 else 0}/page), "
            f"total: {total_tokens} tokens"
        )

        return total_tokens

    except (FileNotFoundError, PermissionError) as e:
        if isinstance(e, FileNotFoundError):
            raise ValueError(f"PDF file not found for token estimation: {file_path}") from e
        else:
            raise ValueError(f"Permission denied accessing PDF file: {file_path}") from e
    except Exception as e:
        logger.error(f"PDF token estimation failed for {file_path}: {e}")
        raise ValueError(f"Failed to estimate tokens for PDF {file_path}: {e}") from e


def estimate_tokens_for_files(
    model_name: str,
    files: list[dict],
    image_detail: str,
    use_responses_api: bool = False,
) -> int:
    """Estimate token count for files using OpenAI-specific formulas.

    Supports text, images, and (with Responses API) PDF/documents.

    Args:
        model_name: The OpenAI model to estimate tokens for
        files: List of file dicts with 'path' and 'mime_type' keys
        image_detail: Detail level for images ("LOW", "HIGH", or "AUTO", case-insensitive).
                      Must be provided by caller.
        use_responses_api: If True, enables PDF/document support via Responses API

    Returns:
        Total estimated token count

    Raises:
        ValueError: If a file cannot be accessed or has unsupported mime type
    """
    if not files:
        return 0

    total_tokens = 0
    for file_info in files:
        file_path = file_info.get("path", "")
        mime_type = file_info.get("mime_type", "")

        if not file_path:
            continue

        # Images: model-specific estimation
        if mime_type.startswith("image/"):
            total_tokens += estimate_image_tokens(file_path, model_name, image_detail)

        # Text/code files: use tiktoken
        elif (
            mime_type.startswith("text/")
            or mime_type
            in {
                "application/json",
                "application/xml",
                "application/javascript",
                "application/yaml",
                "text/yaml",
                "application/toml",
            }
            or mime_type.endswith(("+json", "+xml"))
        ):
            try:
                with open(file_path, encoding="utf-8") as f:
                    content = f.read()
                total_tokens += calculate_text_tokens(model_name, content)
            except (FileNotFoundError, PermissionError, OSError) as e:
                raise ValueError(f"Cannot access text file {file_path}: {e}") from e
            except UnicodeDecodeError as e:
                raise ValueError(f"Cannot decode text file {file_path}: {e}") from e
            except Exception as e:
                raise ValueError(f"Failed to process text file {file_path}: {e}") from e

        # PDF/Documents: Supported via Responses API
        elif mime_type == "application/pdf" or mime_type.startswith("application/vnd."):
            if use_responses_api:
                # Use accurate PDF token estimation (text + image tokens per page)
                # Pass image_detail to respect user's detail preference
                total_tokens += estimate_pdf_tokens(file_path, model_name, image_detail)
            else:
                raise UnsupportedContentTypeError(
                    model_name,
                    "PDF/document files (requires Responses API)",
                    file_path,
                )

        # Audio: Not supported
        elif mime_type.startswith("audio/"):
            raise UnsupportedContentTypeError(model_name, "audio files", file_path)

        # Video: Not supported
        elif mime_type.startswith("video/"):
            raise UnsupportedContentTypeError(model_name, "video files", file_path)

        # Unknown types: raise error with clear message
        else:
            raise UnsupportedContentTypeError(model_name, f"mime type '{mime_type}'", file_path)

    return total_tokens
