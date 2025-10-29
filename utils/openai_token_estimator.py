"""OpenAI token estimation utilities for text, images, and PDFs.

This module provides accurate token counting for OpenAI models, supporting both
direct OpenAI API calls and OpenRouter-proxied requests (openai/* prefix).

Implementation follows official OpenAI documentation and pricing specifications:

- Text: tiktoken with model-specific encodings (o200k_base for GPT-4o/o3/o4, cl100k_base for others)

- Images: Two-stage resize (cap to 2048x2048, then min-side to 768 if needed), followed by 512x512 tiling.
  * detail=low: Fixed base cost (~85 tokens per image)
  * detail=high: Base + per-tile cost (~170 tokens per 512x512 tile)
  * detail=auto: Adaptive based on image dimensions
  * Supports both tile-based (standard models) and patch-based (mini/nano variants)

- PDFs: Text tokens (extracted via tiktoken) + image tokens per page (each page treated as full-page image)
  * Uses MediaBox dimensions with proper rotation handling
  * Preserves aspect ratio when converting PDF points to pixel equivalents

Token constants are configurable per model family to accommodate OpenAI pricing updates.
Defaults based on OpenAI Pricing calculator and Azure OpenAI technical documentation.
"""

import logging

import imagesize
import tiktoken
from pypdf import PdfReader

logger = logging.getLogger(__name__)

# References (authoritative sources; keep links up to date):
# - OpenAI Pricing (interactive Pricing calculator):
#   https://openai.com/api/pricing/
# - OpenAI Images & Vision guide (detail modes, examples):
#   https://platform.openai.com/docs/guides/images-vision
# - OpenAI Vision fine-tuning (low-detail representation guidance):
#   https://platform.openai.com/docs/guides/vision-fine-tuning
# - Azure OpenAI – GPT with Vision (scaling/tiling engineering rules & examples):
#   https://learn.microsoft.com/azure/ai-services/openai/concepts/gpt-with-vision

# Detail normalization map (case-insensitive)
_DETAIL_MAP = {
    "LOW": "low",  # Fast, fixed base (~85 tokens/image)
    "HIGH": "high",  # High detail: scaling + 512x512 tiling
    "AUTO": "auto",  # Adaptive: if min-side ≤512 → low, else high
}

# Model-specific overrides for (base_tokens, per_tile_tokens). Defaults to (85, 170).
# Substring matching enables family-level configuration (e.g., "gpt-5" matches "gpt-5-pro")
_MODEL_TILE_CONST: dict[str, tuple[int, int]] = {
    # GPT-5 family uses different constants than GPT-4 series
    "gpt-5": (70, 140),
}

DEFAULT_BASE_TOKENS = 85
DEFAULT_PER_TILE_TOKENS = 170

# Patch-based defaults for mini/nano model variants
# These models use 32px patches with a cap at 1536 patches
DEFAULT_PATCH_SIZE = 32
DEFAULT_PATCH_CAP = 1536
DEFAULT_PATCH_MULTIPLIER = 1.0

# Model-specific overrides for patch-based calculations: (patch_size, patch_cap, multiplier)
# Multipliers determined from OpenAI Pricing calculator observations
_MODEL_PATCH_CONST: dict[str, tuple[int, int, float]] = {
    "gpt-5-mini": (32, 1536, 1.20),
    "gpt-5-nano": (32, 1536, 1.50),
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
FALLBACK_IMAGE_TOKENS = 765  # Fallback magnitude for typical 1024x1024 case when size reading fails


# ------------------------------
# Internals: image cost core
# ------------------------------


def _pick_tile_const(model_name: str) -> tuple[int, int]:
    """Return (base, per-tile) constants by model name; default to (85, 170).

    Substring matching enables family-level overrides (e.g., 'gpt-4o-mini').
    """
    m = (model_name or "").lower().replace("openai/", "")
    for key, pair in _MODEL_TILE_CONST.items():
        if key in m:
            return pair
    return (DEFAULT_BASE_TOKENS, DEFAULT_PER_TILE_TOKENS)


def _resize_for_vision(width: int, height: int) -> tuple[int, int]:
    """Logical resize (no resampling) per documented vision behavior.

    1) Cap to within 2048x2048 (preserve aspect ratio)
    2) If min-side remains >768, downscale so min-side becomes 768
    """
    import math

    if width <= 0 or height <= 0:
        return (0, 0)

    w, h = int(width), int(height)

    max_side = max(w, h)
    if max_side > 2048:
        scale = 2048.0 / max_side
        w = int(math.floor(w * scale))
        h = int(math.floor(h * scale))

    min_side = min(w, h)
    if min_side > 768:
        scale = 768.0 / min_side
        w = int(math.floor(w * scale))
        h = int(math.floor(h * scale))

    return (max(w, 1), max(h, 1))


def _count_tiles(width: int, height: int) -> int:
    """Return the number of 512x512 tiles (ceil partial blocks)."""
    import math

    return math.ceil(width / 512.0) * math.ceil(height / 512.0)


def _is_patch_based(model_name: str) -> bool:
    """Heuristic: treat mini/nano families as patch-based (32px patches).

    The exact accounting may evolve per model family. Calibrate constants
    (size/cap/multiplier) with the official Pricing page.
    """
    m = (model_name or "").lower()
    m = m.replace("openai/", "")
    return ("-mini" in m) or ("-nano" in m) or m.endswith("mini") or m.endswith("nano")


def _pick_patch_const(model_name: str) -> tuple[int, int, float]:
    """Return (patch_size, patch_cap, multiplier) for patch-based models.

    Defaults to (32, 1536, 1.0). Override per family where needed.
    """
    m = (model_name or "").lower().replace("openai/", "")
    for key, cfg in _MODEL_PATCH_CONST.items():
        if key in m:
            return cfg
    return (DEFAULT_PATCH_SIZE, DEFAULT_PATCH_CAP, DEFAULT_PATCH_MULTIPLIER)


def _estimate_tile_tokens_by_dims(width: int, height: int, detail: str, model_name: str) -> int:
    """Estimate tokens for tile-based accounting by dimensions.

    Logic per docs:
    1) logical resize to fit within 2048x2048; if min-side still >768, downscale so min-side=768
       (aspect ratio preserved).
    2) tiles = ceil(W/512) * ceil(H/512)
    3) tokens = base + per_tile * tiles
    Low detail returns base; AUTO uses low when min-side <= 512.
    See: OpenAI Images & Vision; Azure GPT-with-Vision examples.
    """
    mode = _DETAIL_MAP.get((detail or "high").upper(), "high")
    base, per_tile = _pick_tile_const(model_name)
    if mode == "low":
        return base
    if mode == "auto" and min(width, height) <= 512:
        return base
    rw, rh = _resize_for_vision(width, height)
    tiles = _count_tiles(rw, rh)
    return base + per_tile * tiles


def _estimate_patch_tokens_by_dims(width: int, height: int, detail: str, model_name: str) -> int:
    """Estimate tokens for patch-based accounting by dimensions (mini/nano families).

    Logic per common references:
    1) logical resize to fit within 2048x2048; if min-side still >768, downscale so min-side=768.
    2) patches = ceil(W/patch_size) * ceil(H/patch_size); cap at patch_cap (e.g., 1536).
    3) tokens = patches * multiplier (model-specific; calibrate with Pricing calculator).
    Low detail returns base; AUTO uses low when min-side <= 512.
    See: OpenAI Images & Vision; Azure GPT-with-Vision; Pricing calculator.
    """
    mode = _DETAIL_MAP.get((detail or "high").upper(), "high")
    base, _ = _pick_tile_const(model_name)
    if mode == "low":
        return base
    if mode == "auto" and min(width, height) <= 512:
        return base
    patch_size, patch_cap, multiplier = _pick_patch_const(model_name)
    import math

    rw, rh = _resize_for_vision(width, height)
    patches = math.ceil(rw / float(patch_size)) * math.ceil(rh / float(patch_size))
    patches = min(patches, patch_cap)
    return int(round(patches * float(multiplier)))


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
    """Estimate tokens for a single image based on documented scaling/tiling rules.

    - low: fixed base (default 85)
    - high: scale (≤2048, min-side ≤768) → 512x512 tiling → base + per-tile
    - auto: if min-side ≤512 treat as low, else high
    """
    try:
        width, height = imagesize.get(file_path)
        if not width or not height:
            return FALLBACK_IMAGE_TOKENS

        if _is_patch_based(model_name):
            return _estimate_patch_tokens_by_dims(width, height, detail, model_name)
        else:
            return _estimate_tile_tokens_by_dims(width, height, detail, model_name)

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
        return FALLBACK_IMAGE_TOKENS


def estimate_pdf_tokens(file_path: str, model_name: str, detail: str) -> int:
    """Estimate PDF tokens = text tokens + sum of per-page image tokens.

    Note: The 96/72 factor maps PDF points (1/72 inch) to a pixel-like space to
    preserve aspect ratio only. The eventual tile count is driven by the logical
    vision resize (≤2048, min-side ≤768), not physical DPI.
    """
    try:
        reader = PdfReader(file_path)
        num_pages = len(reader.pages)

        # Text side: extract all text across pages
        full_text = ""
        for page in reader.pages:
            try:
                full_text += page.extract_text() or ""
            except Exception as e:
                logger.warning(f"Failed to extract text from a page in {file_path}: {e}")

        text_tokens = calculate_text_tokens(model_name, full_text)

        # Image side: charge each page as a full-page image
        total_image_tokens = 0
        for page_num, page in enumerate(reader.pages, start=1):
            try:
                mediabox = page.mediabox
                width_pt = float(mediabox.width)
                height_pt = float(mediabox.height)

                rotation = int(page.get("/Rotate", 0) or 0) % 360
                if rotation in (90, 270):
                    width_pt, height_pt = height_pt, width_pt

                PX_PER_PT = 96.0 / 72.0
                w_px = max(1, int(width_pt * PX_PER_PT))
                h_px = max(1, int(height_pt * PX_PER_PT))

                # Reuse image cost logic (no real image decoding)
                if _is_patch_based(model_name):
                    page_tokens = _estimate_patch_tokens_by_dims(w_px, h_px, detail, model_name)
                else:
                    page_tokens = _estimate_tile_tokens_by_dims(w_px, h_px, detail, model_name)

                total_image_tokens += page_tokens

                logger.debug(
                    f"Page {page_num}: {width_pt:.1f}x{height_pt:.1f} pt -> {w_px}x{h_px} px, tokens={page_tokens}"
                )
            except Exception as e:
                logger.warning(
                    f"Failed to estimate image tokens for page {page_num} in {file_path}: {e}. Use A4 fallback."
                )
                # A4: 595x842 pt -> 794x1123 px @96DPI
                if _is_patch_based(model_name):
                    total_image_tokens += _estimate_patch_tokens_by_dims(794, 1123, detail, model_name)
                else:
                    total_image_tokens += _estimate_tile_tokens_by_dims(794, 1123, detail, model_name)

        total_tokens = text_tokens + total_image_tokens
        logger.info(
            f"PDF token estimation for {file_path}: {num_pages} pages, text={text_tokens}, images={total_image_tokens}, total={total_tokens}"
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
