"""OpenAI model provider implementation."""

import os
from typing import Dict, Optional, List, Any
import logging

from openai import OpenAI

from .base import (
    ModelProvider, 
    ModelResponse, 
    ModelCapabilities, 
    ProviderType,
    FixedTemperatureConstraint,
    RangeTemperatureConstraint
)


class OpenAIModelProvider(ModelProvider):
    """OpenAI model provider implementation."""
    
    # Model configurations
    SUPPORTED_MODELS = {
        "o3": {
            "max_tokens": 200_000,  # 200K tokens
            "supports_extended_thinking": False,
        },
        "o3-mini": {
            "max_tokens": 200_000,  # 200K tokens
            "supports_extended_thinking": False,
        },
    }
    
    def __init__(self, api_key: str, **kwargs):
        """Initialize OpenAI provider with API key."""
        super().__init__(api_key, **kwargs)
        self._client = None
        self.base_url = kwargs.get("base_url")  # Support custom endpoints
        self.organization = kwargs.get("organization")
    
    @property
    def client(self):
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            client_kwargs = {"api_key": self.api_key}
            if self.base_url:
                client_kwargs["base_url"] = self.base_url
            if self.organization:
                client_kwargs["organization"] = self.organization
            
            self._client = OpenAI(**client_kwargs)
        return self._client
    
    def get_capabilities(self, model_name: str) -> ModelCapabilities:
        """Get capabilities for a specific OpenAI model."""
        if model_name not in self.SUPPORTED_MODELS:
            raise ValueError(f"Unsupported OpenAI model: {model_name}")
        
        config = self.SUPPORTED_MODELS[model_name]
        
        # Define temperature constraints per model
        if model_name in ["o3", "o3-mini"]:
            # O3 models only support temperature=1.0
            temp_constraint = FixedTemperatureConstraint(1.0)
        else:
            # Other OpenAI models support 0.0-2.0 range
            temp_constraint = RangeTemperatureConstraint(0.0, 2.0, 0.7)
        
        return ModelCapabilities(
            provider=ProviderType.OPENAI,
            model_name=model_name,
            friendly_name="OpenAI",
            max_tokens=config["max_tokens"],
            supports_extended_thinking=config["supports_extended_thinking"],
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=True,
            temperature_constraint=temp_constraint,
        )
    
    def generate_content(
        self,
        prompt: str,
        model_name: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_output_tokens: Optional[int] = None,
        **kwargs
    ) -> ModelResponse:
        """Generate content using OpenAI model."""
        # Validate parameters
        self.validate_parameters(model_name, temperature)
        
        # Prepare messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Prepare completion parameters
        completion_params = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
        }
        
        # Add max tokens if specified
        if max_output_tokens:
            completion_params["max_tokens"] = max_output_tokens
        
        # Add any additional OpenAI-specific parameters
        for key, value in kwargs.items():
            if key in ["top_p", "frequency_penalty", "presence_penalty", "seed", "stop"]:
                completion_params[key] = value
        
        try:
            # Generate completion
            response = self.client.chat.completions.create(**completion_params)
            
            # Extract content and usage
            content = response.choices[0].message.content
            usage = self._extract_usage(response)
            
            return ModelResponse(
                content=content,
                usage=usage,
                model_name=model_name,
                friendly_name="OpenAI",
                provider=ProviderType.OPENAI,
                metadata={
                    "finish_reason": response.choices[0].finish_reason,
                    "model": response.model,  # Actual model used (in case of fallbacks)
                    "id": response.id,
                    "created": response.created,
                }
            )
            
        except Exception as e:
            # Log error and re-raise with more context
            error_msg = f"OpenAI API error for model {model_name}: {str(e)}"
            logging.error(error_msg)
            raise RuntimeError(error_msg) from e
    
    def count_tokens(self, text: str, model_name: str) -> int:
        """Count tokens for the given text.
        
        Note: For accurate token counting, we should use tiktoken library.
        This is a simplified estimation.
        """
        # TODO: Implement proper token counting with tiktoken
        # For now, use rough estimation
        # O3 models ~4 chars per token
        return len(text) // 4
    
    def get_provider_type(self) -> ProviderType:
        """Get the provider type."""
        return ProviderType.OPENAI
    
    def validate_model_name(self, model_name: str) -> bool:
        """Validate if the model name is supported."""
        return model_name in self.SUPPORTED_MODELS
    
    def supports_thinking_mode(self, model_name: str) -> bool:
        """Check if the model supports extended thinking mode."""
        # Currently no OpenAI models support extended thinking
        # This may change with future O3 models
        return False
    
    def _extract_usage(self, response) -> Dict[str, int]:
        """Extract token usage from OpenAI response."""
        usage = {}
        
        if hasattr(response, "usage") and response.usage:
            usage["input_tokens"] = response.usage.prompt_tokens
            usage["output_tokens"] = response.usage.completion_tokens
            usage["total_tokens"] = response.usage.total_tokens
        
        return usage