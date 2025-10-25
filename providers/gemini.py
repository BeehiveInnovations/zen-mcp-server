"""Gemini model provider implementation."""

import base64
import logging
import math
from typing import TYPE_CHECKING, ClassVar, Optional

if TYPE_CHECKING:
    from tools.models import ToolModelCategory

from google import genai
from google.genai import types

# LocalTokenizer is not exported in __all__, must import explicitly
# Requires google-genai[local-tokenizer]>=1.34.0
try:
    from google.genai.local_tokenizer import LocalTokenizer

    _HAS_LOCAL_TOKENIZER = True
except ImportError:
    _HAS_LOCAL_TOKENIZER = False

# Optional dependencies for token estimation
try:
    import imagesize

    _HAS_IMAGESIZE = True
except ImportError:
    _HAS_IMAGESIZE = False

try:
    import pypdf

    _HAS_PYPDF = True
except ImportError:
    _HAS_PYPDF = False

try:
    from tinytag import TinyTag

    _HAS_TINYTAG = True
except ImportError:
    _HAS_TINYTAG = False

from config import GEMINI_MEDIA_RESOLUTION
from utils.env import get_env
from utils.image_utils import validate_image

from .base import ModelProvider
from .registries.gemini import GeminiModelRegistry
from .registry_provider_mixin import RegistryBackedProviderMixin
from .shared import ModelCapabilities, ModelResponse, ProviderType

logger = logging.getLogger(__name__)


class GeminiModelProvider(RegistryBackedProviderMixin, ModelProvider):
    """First-party Gemini integration built on the official Google SDK.

    The provider advertises detailed thinking-mode budgets, handles optional
    custom endpoints, and performs image pre-processing before forwarding a
    request to the Gemini APIs.
    """

    REGISTRY_CLASS = GeminiModelRegistry
    MODEL_CAPABILITIES: ClassVar[dict[str, ModelCapabilities]] = {}

    # Media resolution mapping for video token estimation
    _RESOLUTION_MAP = {
        "LOW": types.MediaResolution.MEDIA_RESOLUTION_LOW,
        "MEDIUM": types.MediaResolution.MEDIA_RESOLUTION_MEDIUM,
        "HIGH": types.MediaResolution.MEDIA_RESOLUTION_HIGH,
    }

    # Pre-Gemini 2.0 models that use fixed 258 tokens for all images (no tiling)
    # These models should be explicitly listed to avoid version detection issues
    PRE_GEMINI_2_0_MODELS = {
        # Gemini 1.0 series
        "gemini-1.0-pro",
        "gemini-1.0-pro-latest",
        "gemini-1.0-pro-vision",
        "gemini-1.0-pro-vision-latest",
        "gemini-pro",
        "gemini-pro-vision",
        # Gemini 1.5 Pro series
        "gemini-1.5-pro",
        "gemini-1.5-pro-latest",
        "gemini-1.5-pro-001",
        "gemini-1.5-pro-002",
        "gemini-1.5-pro-preview",
        "gemini-1.5-pro-exp-0827",
        # Gemini 1.5 Flash series
        "gemini-1.5-flash",
        "gemini-1.5-flash-latest",
        "gemini-1.5-flash-001",
        "gemini-1.5-flash-002",
        "gemini-1.5-flash-preview",
        "gemini-1.5-flash-exp-0827",
    }

    # Thinking mode configurations - percentages of model's max_thinking_tokens
    # These percentages work across all models that support thinking
    THINKING_BUDGETS = {
        "minimal": 0.005,  # 0.5% of max - minimal thinking for fast responses
        "low": 0.08,  # 8% of max - light reasoning tasks
        "medium": 0.33,  # 33% of max - balanced reasoning (default)
        "high": 0.67,  # 67% of max - complex analysis
        "max": 1.0,  # 100% of max - full thinking budget
    }

    # Model-specific thinking token limits
    MAX_THINKING_TOKENS = {
        "gemini-2.0-flash": 24576,  # Same as 2.5 flash for consistency
        "gemini-2.0-flash-lite": 0,  # No thinking support
        "gemini-2.5-flash": 24576,  # Flash 2.5 thinking budget limit
        "gemini-2.5-pro": 32768,  # Pro 2.5 thinking budget limit
    }

    # Retry configuration for API calls
    MAX_RETRIES = 4
    RETRY_DELAYS = [1, 3, 5, 8]  # seconds

    def __init__(self, api_key: str, **kwargs):
        """Initialize Gemini provider with API key and optional base URL."""
        self._ensure_registry()
        super().__init__(api_key, **kwargs)
        self._client = None
        self._token_counters = {}  # Cache for token counting
        self._base_url = kwargs.get("base_url", None)  # Optional custom endpoint
        self._timeout_override = self._resolve_http_timeout()
        self._invalidate_capability_cache()

    # ------------------------------------------------------------------
    # Capability surface
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Client access
    # ------------------------------------------------------------------

    @property
    def client(self):
        """Lazy initialization of Gemini client."""
        if self._client is None:
            http_options_kwargs: dict[str, object] = {}
            if self._base_url:
                http_options_kwargs["base_url"] = self._base_url
            if self._timeout_override is not None:
                http_options_kwargs["timeout"] = self._timeout_override

            if http_options_kwargs:
                http_options = types.HttpOptions(**http_options_kwargs)
                logger.debug(
                    "Initializing Gemini client with options: base_url=%s timeout=%s",
                    http_options_kwargs.get("base_url"),
                    http_options_kwargs.get("timeout"),
                )
                self._client = genai.Client(api_key=self.api_key, http_options=http_options)
            else:
                self._client = genai.Client(api_key=self.api_key)
        return self._client

    def _resolve_http_timeout(self) -> Optional[float]:
        """Compute timeout override from shared custom timeout environment variables."""

        timeouts: list[float] = []
        for env_var in [
            "CUSTOM_CONNECT_TIMEOUT",
            "CUSTOM_READ_TIMEOUT",
            "CUSTOM_WRITE_TIMEOUT",
            "CUSTOM_POOL_TIMEOUT",
        ]:
            raw_value = get_env(env_var)
            if raw_value:
                try:
                    timeouts.append(float(raw_value))
                except (TypeError, ValueError):
                    logger.warning("Invalid %s value '%s'; ignoring.", env_var, raw_value)

        if timeouts:
            # Use the largest timeout to best approximate long-running requests
            resolved = max(timeouts)
            logger.debug("Using custom Gemini HTTP timeout: %ss", resolved)
            return resolved

        return None

    # ------------------------------------------------------------------
    # Request execution
    # ------------------------------------------------------------------

    def generate_content(
        self,
        prompt: str,
        model_name: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_output_tokens: Optional[int] = None,
        thinking_mode: str = "medium",
        images: Optional[list[str]] = None,
        **kwargs,
    ) -> ModelResponse:
        """
        Generate content using Gemini model.

        Args:
            prompt: The main user prompt/query to send to the model
            model_name: Canonical model name or its alias (e.g., "gemini-2.5-pro", "flash", "pro")
            system_prompt: Optional system instructions to prepend to the prompt for context/behavior
            temperature: Controls randomness in generation (0.0=deterministic, 1.0=creative), default 0.3
            max_output_tokens: Optional maximum number of tokens to generate in the response
            thinking_mode: Thinking budget level for models that support it ("minimal", "low", "medium", "high", "max"), default "medium"
            images: Optional list of image paths or data URLs to include with the prompt (for vision models)
            **kwargs: Additional keyword arguments (reserved for future use)

        Returns:
            ModelResponse: Contains the generated content, token usage stats, model metadata, and safety information
        """
        # Validate parameters and fetch capabilities
        self.validate_parameters(model_name, temperature)
        capabilities = self.get_capabilities(model_name)
        capability_map = self.get_all_model_capabilities()

        resolved_model_name = self._resolve_model_name(model_name)

        # Prepare content parts (text and potentially images)
        parts = []

        # Add system and user prompts as text
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        else:
            full_prompt = prompt

        parts.append({"text": full_prompt})

        # Add images if provided and model supports vision
        if images and capabilities.supports_images:
            for image_path in images:
                try:
                    image_part = self._process_image(image_path)
                    if image_part:
                        parts.append(image_part)
                except Exception as e:
                    logger.warning(f"Failed to process image {image_path}: {e}")
                    # Continue with other images and text
                    continue
        elif images and not capabilities.supports_images:
            logger.warning(f"Model {resolved_model_name} does not support images, ignoring {len(images)} image(s)")

        # Create contents structure
        contents = [{"parts": parts}]

        # Prepare generation config
        generation_config = types.GenerateContentConfig(
            temperature=temperature,
            candidate_count=1,
        )

        # Add max output tokens if specified
        if max_output_tokens:
            generation_config.max_output_tokens = max_output_tokens

        # Add thinking configuration for models that support it
        if capabilities.supports_extended_thinking and thinking_mode in self.THINKING_BUDGETS:
            # Get model's max thinking tokens and calculate actual budget
            model_config = capability_map.get(resolved_model_name)
            if model_config and model_config.max_thinking_tokens > 0:
                max_thinking_tokens = model_config.max_thinking_tokens
                actual_thinking_budget = int(max_thinking_tokens * self.THINKING_BUDGETS[thinking_mode])
                generation_config.thinking_config = types.ThinkingConfig(thinking_budget=actual_thinking_budget)

        # Add media resolution configuration
        # Supports LOW (saves 62-75% tokens), MEDIUM (default), HIGH (quality)
        media_resolution = kwargs.get("media_resolution") or GEMINI_MEDIA_RESOLUTION
        resolution_enum = self._RESOLUTION_MAP.get(media_resolution.upper())
        if resolution_enum:
            generation_config.media_resolution = resolution_enum

        # Retry logic with progressive delays
        attempt_counter = {"value": 0}

        def _attempt() -> ModelResponse:
            attempt_counter["value"] += 1
            response = self.client.models.generate_content(
                model=resolved_model_name,
                contents=contents,
                config=generation_config,
            )

            usage = self._extract_usage(response)

            finish_reason_str = "UNKNOWN"
            is_blocked_by_safety = False
            safety_feedback_details = None

            if response.candidates:
                candidate = response.candidates[0]

                try:
                    finish_reason_enum = candidate.finish_reason
                    if finish_reason_enum:
                        try:
                            finish_reason_str = finish_reason_enum.name
                        except AttributeError:
                            finish_reason_str = str(finish_reason_enum)
                    else:
                        finish_reason_str = "STOP"
                except AttributeError:
                    finish_reason_str = "STOP"

                if not response.text:
                    try:
                        safety_ratings = candidate.safety_ratings
                        if safety_ratings:
                            for rating in safety_ratings:
                                try:
                                    if rating.blocked:
                                        is_blocked_by_safety = True
                                        category_name = "UNKNOWN"
                                        probability_name = "UNKNOWN"

                                        try:
                                            category_name = rating.category.name
                                        except (AttributeError, TypeError):
                                            pass

                                        try:
                                            probability_name = rating.probability.name
                                        except (AttributeError, TypeError):
                                            pass

                                        safety_feedback_details = (
                                            f"Category: {category_name}, Probability: {probability_name}"
                                        )
                                        break
                                except (AttributeError, TypeError):
                                    continue
                    except (AttributeError, TypeError):
                        pass

            elif response.candidates is not None and len(response.candidates) == 0:
                is_blocked_by_safety = True
                finish_reason_str = "SAFETY"
                safety_feedback_details = "Prompt blocked, reason unavailable"

                try:
                    prompt_feedback = response.prompt_feedback
                    if prompt_feedback and prompt_feedback.block_reason:
                        try:
                            block_reason_name = prompt_feedback.block_reason.name
                        except AttributeError:
                            block_reason_name = str(prompt_feedback.block_reason)
                        safety_feedback_details = f"Prompt blocked, reason: {block_reason_name}"
                except (AttributeError, TypeError):
                    pass

            return ModelResponse(
                content=response.text,
                usage=usage,
                model_name=resolved_model_name,
                friendly_name="Gemini",
                provider=ProviderType.GOOGLE,
                metadata={
                    "thinking_mode": thinking_mode if capabilities.supports_extended_thinking else None,
                    "finish_reason": finish_reason_str,
                    "is_blocked_by_safety": is_blocked_by_safety,
                    "safety_feedback": safety_feedback_details,
                },
            )

        try:
            return self._run_with_retries(
                operation=_attempt,
                max_attempts=self.MAX_RETRIES,
                delays=self.RETRY_DELAYS,
                log_prefix=f"Gemini API ({resolved_model_name})",
            )
        except Exception as exc:
            attempts = max(attempt_counter["value"], 1)
            error_msg = (
                f"Gemini API error for model {resolved_model_name} after {attempts} attempt"
                f"{'s' if attempts > 1 else ''}: {exc}"
            )
            raise RuntimeError(error_msg) from exc

    def get_provider_type(self) -> ProviderType:
        """Get the provider type."""
        return ProviderType.GOOGLE

    def _extract_usage(self, response) -> dict[str, int]:
        """Extract token usage from Gemini response."""
        usage = {}

        # Try to extract usage metadata from response
        # Note: The actual structure depends on the SDK version and response format
        try:
            metadata = response.usage_metadata
            if metadata:
                # Extract token counts with explicit None checks
                input_tokens = None
                output_tokens = None

                try:
                    value = metadata.prompt_token_count
                    if value is not None:
                        input_tokens = value
                        usage["input_tokens"] = value
                except (AttributeError, TypeError):
                    pass

                try:
                    value = metadata.candidates_token_count
                    if value is not None:
                        output_tokens = value
                        usage["output_tokens"] = value
                except (AttributeError, TypeError):
                    pass

                # Calculate total only if both values are available and valid
                if input_tokens is not None and output_tokens is not None:
                    usage["total_tokens"] = input_tokens + output_tokens
        except (AttributeError, TypeError):
            # response doesn't have usage_metadata
            pass

        return usage

    def _is_error_retryable(self, error: Exception) -> bool:
        """Determine if an error should be retried based on structured error codes.

        Uses Gemini API error structure instead of text pattern matching for reliability.

        Args:
            error: Exception from Gemini API call

        Returns:
            True if error should be retried, False otherwise
        """
        error_str = str(error).lower()

        # Check for 429 errors first - these need special handling
        if "429" in error_str or "quota" in error_str or "resource_exhausted" in error_str:
            # For Gemini, check for specific non-retryable error indicators
            # These typically indicate permanent failures or quota/size limits
            non_retryable_indicators = [
                "quota exceeded",
                "resource exhausted",
                "context length",
                "token limit",
                "request too large",
                "invalid request",
                "quota_exceeded",
                "resource_exhausted",
            ]

            # Also check if this is a structured error from Gemini SDK
            try:
                # Try to access error details if available
                error_details = None
                try:
                    error_details = error.details
                except AttributeError:
                    try:
                        error_details = error.reason
                    except AttributeError:
                        pass

                if error_details:
                    error_details_str = str(error_details).lower()
                    # Check for non-retryable error codes/reasons
                    if any(indicator in error_details_str for indicator in non_retryable_indicators):
                        logger.debug(f"Non-retryable Gemini error: {error_details}")
                        return False
            except Exception:
                pass

            # Check main error string for non-retryable patterns
            if any(indicator in error_str for indicator in non_retryable_indicators):
                logger.debug(f"Non-retryable Gemini error based on message: {error_str[:200]}...")
                return False

            # If it's a 429/quota error but doesn't match non-retryable patterns, it might be retryable rate limiting
            logger.debug(f"Retryable Gemini rate limiting error: {error_str[:100]}...")
            return True

        # For non-429 errors, check if they're retryable
        retryable_indicators = [
            "timeout",
            "connection",
            "network",
            "temporary",
            "unavailable",
            "retry",
            "internal error",
            "408",  # Request timeout
            "500",  # Internal server error
            "502",  # Bad gateway
            "503",  # Service unavailable
            "504",  # Gateway timeout
            "ssl",  # SSL errors
            "handshake",  # Handshake failures
        ]

        return any(indicator in error_str for indicator in retryable_indicators)

    def _process_image(self, image_path: str) -> Optional[dict]:
        """Process an image for Gemini API."""
        try:
            # Use base class validation
            image_bytes, mime_type = validate_image(image_path)

            # For data URLs, extract the base64 data directly
            if image_path.startswith("data:"):
                # Extract base64 data from data URL
                _, data = image_path.split(",", 1)
                return {"inline_data": {"mime_type": mime_type, "data": data}}
            else:
                # For file paths, encode the bytes
                image_data = base64.b64encode(image_bytes).decode()
                return {"inline_data": {"mime_type": mime_type, "data": image_data}}

        except ValueError as e:
            logger.warning(str(e))
            return None
        except Exception as e:
            logger.error(f"Error processing image {image_path}: {e}")
            return None

    @staticmethod
    def _handle_file_access_error(file_path: str, error: Exception, file_type: str) -> None:
        """Handle file access errors with consistent error messages.

        Args:
            file_path: Path to the file
            error: The exception that was raised
            file_type: Type of file (e.g., 'Image', 'PDF', 'Video')

        Raises:
            ValueError: With descriptive error message
        """
        if isinstance(error, FileNotFoundError):
            raise ValueError(f"{file_type} file not found for token estimation: {file_path}")
        elif isinstance(error, PermissionError):
            raise ValueError(f"Permission denied accessing {file_type.lower()} file: {file_path}")
        elif isinstance(error, OSError):
            raise ValueError(f"Cannot access {file_type.lower()} file {file_path}: {error}")

    def _calculate_text_tokens(self, model_name: str, content: str) -> int:
        """Calculate text token count using LocalTokenizer.

        Reference: google-genai[local-tokenizer] using SentencePiece

        Uses Gemini's official offline tokenizer (same as Gemma models).

        Args:
            model_name: The model to count tokens for
            content: Text content

        Returns:
            Token count
        """
        if _HAS_LOCAL_TOKENIZER:
            try:
                tokenizer = LocalTokenizer(model_name=model_name)
                result = tokenizer.count_tokens(content)
                return result.total_tokens

            except Exception as e:
                logger.warning("LocalTokenizer failed: %s, using fallback", str(e))

        # Fallback: 1 token ≈ 4 characters
        return len(content) // 4

    def _calculate_image_tokens(self, file_path: str, model_name: str = "gemini-2.5-flash") -> int:
        """Calculate image token count per Google Developer API specification.

        Reference: https://ai.google.dev/gemini-api/docs/tokens

        Formula (Google Developer API, NOT Vertex AI):
        - Small images (width AND height ≤384px): 258 tokens
        - Gemini 1.5 and earlier: Fixed 258 tokens (no tiling)
        - Gemini 2.0+: Fixed 768×768 tiles, tiles=ceil(w/768)×ceil(h/768)

        Note: Vertex AI uses different crop_unit formula - not applicable here.

        Args:
            file_path: Path to the image file
            model_name: Model name for version detection

        Returns:
            Estimated token count

        Raises:
            ValueError: If file cannot be accessed (not found, permission denied, etc.)
        """
        if not _HAS_IMAGESIZE:
            logger.warning("imagesize library not available, using fallback")
            return 258

        try:
            width, height = imagesize.get(file_path)

            # Small images: BOTH dimensions must be ≤384
            if width <= 384 and height <= 384:
                return 258

            # Gemini 1.5 and earlier: Fixed 258 tokens (no tiling)
            # "Prior to Gemini 2.0, images used a fixed 258 tokens"
            if model_name in self.PRE_GEMINI_2_0_MODELS:
                return 258

            # Gemini 2.0+: Fixed 768×768 tiles
            tiles_x = math.ceil(width / 768)
            tiles_y = math.ceil(height / 768)
            tiles = tiles_x * tiles_y
            return 258 * tiles

        except (FileNotFoundError, PermissionError, OSError) as e:
            self._handle_file_access_error(file_path, e, "Image")
        except Exception as e:
            # Other errors (parsing issues, corrupted image, library errors) - use fallback
            logger.warning("Failed to calculate image tokens for %s: %s", file_path, e)
            return 258

    def _calculate_pdf_tokens(self, file_path: str) -> int:
        """Calculate PDF token count per Gemini API specification.

        Reference: https://ai.google.dev/gemini-api/docs/document-processing

        Formula: 258 tokens per page
        Maximum: 1,000 pages

        Args:
            file_path: Path to the PDF file

        Returns:
            Estimated token count

        Raises:
            ValueError: If file cannot be accessed (not found, permission denied, etc.)
        """
        if not _HAS_PYPDF:
            logger.warning("pypdf library not available, using fallback")
            return 258 * 10

        try:
            with open(file_path, "rb") as f:
                pdf = pypdf.PdfReader(f)
                num_pages = len(pdf.pages)

            return 258 * num_pages

        except (FileNotFoundError, PermissionError, OSError) as e:
            self._handle_file_access_error(file_path, e, "PDF")
        except Exception as e:
            # Other errors (parsing issues, corrupted PDF) - use fallback
            logger.warning("Failed to calculate PDF tokens for %s: %s", file_path, e)
            return 258 * 10

    def _calculate_video_tokens(self, file_path: str) -> int:
        """Calculate video token count per Gemini API specification.

        Reference: https://ai.google.dev/gemini-api/docs/video-understanding

        Official formula (sampled at 1 FPS):
        - If mediaResolution is set to low: 66 tokens/frame + 32 tokens/sec audio
          Total: Approximately 100 tokens per second
        - Otherwise (default): 258 tokens/frame + 32 tokens/sec audio + metadata
          Total: Approximately 300 tokens per second

        Args:
            file_path: Path to the video file

        Returns:
            Estimated token count

        Raises:
            ValueError: If file cannot be accessed (not found, permission denied, etc.)
        """
        if not _HAS_TINYTAG:
            logger.warning("tinytag library not available, using fallback")
            return 3000

        try:
            tag = TinyTag.get(file_path)
            duration_seconds = tag.duration

            if duration_seconds is None:
                logger.warning("Could not extract video duration from %s", file_path)
                # Fallback: assume 10 seconds
                duration_seconds = 10.0

            # Determine tokens per second based on media resolution
            if GEMINI_MEDIA_RESOLUTION.upper() == "LOW":
                # Low media resolution: approximately 100 tokens/sec
                tokens_per_second = 100
            else:
                # Default media resolution: approximately 300 tokens/sec
                tokens_per_second = 300

            return int(duration_seconds * tokens_per_second)

        except (FileNotFoundError, PermissionError, OSError) as e:
            self._handle_file_access_error(file_path, e, "Video")
        except Exception as e:
            # Other errors (corrupted video, unsupported codec) - use fallback
            logger.warning("Failed to calculate video tokens for %s: %s", file_path, e)
            return 3000

    def _calculate_audio_tokens(self, file_path: str) -> int:
        """Calculate audio token count per Gemini API specification.

        Reference: https://ai.google.dev/gemini-api/docs/video-understanding

        Formula: 32 tokens per second

        Args:
            file_path: Path to the audio file

        Returns:
            Estimated token count

        Raises:
            ValueError: If file cannot be accessed (not found, permission denied, etc.)
        """
        if not _HAS_TINYTAG:
            logger.warning("tinytag library not available, using fallback")
            return 320

        try:
            tag = TinyTag.get(file_path)
            duration_seconds = tag.duration

            if duration_seconds is None:
                logger.warning("Could not extract audio duration from %s", file_path)
                # Fallback: assume 10 seconds
                duration_seconds = 10.0

            return int(duration_seconds * 32)

        except (FileNotFoundError, PermissionError, OSError) as e:
            self._handle_file_access_error(file_path, e, "Audio")
        except Exception as e:
            # Other errors (corrupted audio, unsupported format) - use fallback
            logger.warning("Failed to calculate audio tokens for %s: %s", file_path, e)
            return 320

    def _calculate_text_file_tokens(self, model_name: str, file_path: str) -> int:
        """Calculate text file token count by reading file and using text tokenization.

        Args:
            model_name: The model to count tokens for
            file_path: Path to the text file

        Returns:
            Estimated token count

        Raises:
            ValueError: If file cannot be accessed (not found, permission denied, etc.)
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
                return self._calculate_text_tokens(model_name, content)

        except (FileNotFoundError, PermissionError, OSError) as e:
            self._handle_file_access_error(file_path, e, "Text")

    def estimate_tokens_for_files(self, model_name: str, files: list[dict]) -> Optional[int]:
        """Estimate token count for files using offline calculation.

        Uses local calculation based on official Gemini API formulas:
          - Text: LocalTokenizer (SentencePiece) or character-based fallback
          - Images: 258 tokens (small/old models) or 768×768 tiles (Gemini 2.0+)
          - PDFs: 258 tokens per page
          - Videos: ~300 tokens/sec (default) or ~100 tokens/sec (LOW mediaResolution)
          - Audio: 32 tokens per second

        Args:
            model_name: The model to estimate tokens for
            files: List of file dicts with 'path' and 'mime_type' keys

        Returns:
            Estimated token count, or None if estimation failed
        """
        if not files:
            return 0

        # Offline estimation: Local calculation using official formulas
        total_tokens = 0
        for file_info in files:
            file_path = file_info.get("path", "")
            mime_type = file_info.get("mime_type", "")

            # Images: use official formula (version-specific)
            if mime_type.startswith("image/"):
                total_tokens += self._calculate_image_tokens(file_path, model_name)

            # PDFs: 258 tokens per page
            elif mime_type == "application/pdf":
                total_tokens += self._calculate_pdf_tokens(file_path)

            # Text/code files: use LocalTokenizer (SentencePiece)
            elif mime_type.startswith("text/") or "json" in mime_type or "xml" in mime_type:
                total_tokens += self._calculate_text_file_tokens(model_name, file_path)

            # Videos: use tinytag to extract duration
            elif mime_type.startswith("video/"):
                total_tokens += self._calculate_video_tokens(file_path)

            # Audio: use tinytag to extract duration
            elif mime_type.startswith("audio/"):
                total_tokens += self._calculate_audio_tokens(file_path)

            # Unknown types: raise error with clear message
            else:
                raise ValueError(
                    f"Unsupported mime type '{mime_type}' for file: {file_path}. "
                    f"Supported types: text/*, image/*, video/*, audio/*, application/pdf"
                )

        logger.debug("Offline estimation (local calculation): %d tokens for %d files", total_tokens, len(files))
        return total_tokens

    def get_preferred_model(self, category: "ToolModelCategory", allowed_models: list[str]) -> Optional[str]:
        """Get Gemini's preferred model for a given category from allowed models.

        Args:
            category: The tool category requiring a model
            allowed_models: Pre-filtered list of models allowed by restrictions

        Returns:
            Preferred model name or None
        """
        from tools.models import ToolModelCategory

        if not allowed_models:
            return None

        capability_map = self.get_all_model_capabilities()

        # Helper to find best model from candidates
        def find_best(candidates: list[str]) -> Optional[str]:
            """Return best model from candidates (sorted for consistency)."""
            return sorted(candidates, reverse=True)[0] if candidates else None

        if category == ToolModelCategory.EXTENDED_REASONING:
            # For extended reasoning, prefer models with thinking support
            # First try Pro models that support thinking
            pro_thinking = [
                m
                for m in allowed_models
                if "pro" in m and m in capability_map and capability_map[m].supports_extended_thinking
            ]
            if pro_thinking:
                return find_best(pro_thinking)

            # Then any model that supports thinking
            any_thinking = [
                m for m in allowed_models if m in capability_map and capability_map[m].supports_extended_thinking
            ]
            if any_thinking:
                return find_best(any_thinking)

            # Finally, just prefer Pro models even without thinking
            pro_models = [m for m in allowed_models if "pro" in m]
            if pro_models:
                return find_best(pro_models)

        elif category == ToolModelCategory.FAST_RESPONSE:
            # Prefer Flash models for speed
            flash_models = [m for m in allowed_models if "flash" in m]
            if flash_models:
                return find_best(flash_models)

        # Default for BALANCED or as fallback
        # Prefer Flash for balanced use, then Pro, then anything
        flash_models = [m for m in allowed_models if "flash" in m]
        if flash_models:
            return find_best(flash_models)

        pro_models = [m for m in allowed_models if "pro" in m]
        if pro_models:
            return find_best(pro_models)

        # Ultimate fallback to best available model
        return find_best(allowed_models)


# Load registry data at import time for registry consumers
GeminiModelProvider._ensure_registry()
