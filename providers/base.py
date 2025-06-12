"""Base model provider interface and data classes."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum


class ProviderType(Enum):
    """Supported model provider types."""
    GOOGLE = "google"
    OPENAI = "openai"


@dataclass
class ModelCapabilities:
    """Capabilities and constraints for a specific model."""
    provider: ProviderType
    model_name: str
    friendly_name: str  # Human-friendly name like "Gemini" or "OpenAI"
    max_tokens: int
    supports_extended_thinking: bool = False
    supports_system_prompts: bool = True
    supports_streaming: bool = True
    supports_function_calling: bool = False
    temperature_range: Tuple[float, float] = (0.0, 2.0)


@dataclass
class ModelResponse:
    """Response from a model provider."""
    content: str
    usage: Dict[str, int] = field(default_factory=dict)  # input_tokens, output_tokens, total_tokens
    model_name: str = ""
    friendly_name: str = ""  # Human-friendly name like "Gemini" or "OpenAI"
    provider: ProviderType = ProviderType.GOOGLE
    metadata: Dict[str, Any] = field(default_factory=dict)  # Provider-specific metadata
    
    @property
    def total_tokens(self) -> int:
        """Get total tokens used."""
        return self.usage.get("total_tokens", 0)


class ModelProvider(ABC):
    """Abstract base class for model providers."""
    
    def __init__(self, api_key: str, **kwargs):
        """Initialize the provider with API key and optional configuration."""
        self.api_key = api_key
        self.config = kwargs
    
    @abstractmethod
    def get_capabilities(self, model_name: str) -> ModelCapabilities:
        """Get capabilities for a specific model."""
        pass
    
    @abstractmethod
    def generate_content(
        self,
        prompt: str,
        model_name: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_output_tokens: Optional[int] = None,
        **kwargs
    ) -> ModelResponse:
        """Generate content using the model.
        
        Args:
            prompt: User prompt to send to the model
            model_name: Name of the model to use
            system_prompt: Optional system prompt for model behavior
            temperature: Sampling temperature (0-2)
            max_output_tokens: Maximum tokens to generate
            **kwargs: Provider-specific parameters
            
        Returns:
            ModelResponse with generated content and metadata
        """
        pass
    
    @abstractmethod
    def count_tokens(self, text: str, model_name: str) -> int:
        """Count tokens for the given text using the specified model's tokenizer."""
        pass
    
    @abstractmethod
    def get_provider_type(self) -> ProviderType:
        """Get the provider type."""
        pass
    
    @abstractmethod
    def validate_model_name(self, model_name: str) -> bool:
        """Validate if the model name is supported by this provider."""
        pass
    
    def validate_parameters(
        self, 
        model_name: str,
        temperature: float,
        **kwargs
    ) -> None:
        """Validate model parameters against capabilities.
        
        Raises:
            ValueError: If parameters are invalid
        """
        capabilities = self.get_capabilities(model_name)
        
        # Validate temperature
        min_temp, max_temp = capabilities.temperature_range
        if not min_temp <= temperature <= max_temp:
            raise ValueError(
                f"Temperature {temperature} out of range [{min_temp}, {max_temp}] "
                f"for model {model_name}"
            )
    
    @abstractmethod
    def supports_thinking_mode(self, model_name: str) -> bool:
        """Check if the model supports extended thinking mode."""
        pass