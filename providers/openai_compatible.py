"""Base class for OpenAI-compatible API providers."""

import logging
import os
from abc import abstractmethod
from typing import Optional
from urllib.parse import urlparse
import ipaddress
import socket

from openai import OpenAI

from .base import (
    ModelCapabilities,
    ModelProvider,
    ModelResponse,
    ProviderType,
    RangeTemperatureConstraint,
)


class OpenAICompatibleProvider(ModelProvider):
    """Base class for any provider using an OpenAI-compatible API.
    
    This includes:
    - Direct OpenAI API
    - OpenRouter
    - Any other OpenAI-compatible endpoint
    """
    
    DEFAULT_HEADERS = {}
    FRIENDLY_NAME = "OpenAI Compatible"
    
    def __init__(self, api_key: str, base_url: str = None, **kwargs):
        """Initialize the provider with API key and optional base URL.
        
        Args:
            api_key: API key for authentication
            base_url: Base URL for the API endpoint
            **kwargs: Additional configuration options
        """
        super().__init__(api_key, **kwargs)
        self._client = None
        self.base_url = base_url
        self.organization = kwargs.get("organization")
        self.allowed_models = self._parse_allowed_models()
        
        # Validate base URL for security
        if self.base_url:
            self._validate_base_url()
            
        # Warn if using external URL without authentication
        if self.base_url and not self._is_localhost_url() and not api_key:
            logging.warning(
                f"Using external URL '{self.base_url}' without API key. "
                "This may be insecure. Consider setting an API key for authentication."
            )
    
    def _parse_allowed_models(self) -> Optional[set[str]]:
        """Parse allowed models from environment variable.
        
        Returns:
            Set of allowed model names (lowercase) or None if not configured
        """
        # Get provider-specific allowed models
        provider_type = self.get_provider_type().value.upper()
        env_var = f"{provider_type}_ALLOWED_MODELS"
        models_str = os.getenv(env_var, "")
        
        if models_str:
            # Parse and normalize to lowercase for case-insensitive comparison
            models = set(m.strip().lower() for m in models_str.split(",") if m.strip())
            if models:
                logging.info(f"Configured allowed models for {self.FRIENDLY_NAME}: {sorted(models)}")
                return models
        
        # Log warning if no allow-list configured for proxy providers
        if self.get_provider_type() not in [ProviderType.GOOGLE, ProviderType.OPENAI]:
            logging.warning(
                f"No model allow-list configured for {self.FRIENDLY_NAME}. "
                f"Set {env_var} to restrict model access and control costs."
            )
        
        return None
    
    def _is_localhost_url(self) -> bool:
        """Check if the base URL points to localhost.
        
        Returns:
            True if URL is localhost, False otherwise
        """
        if not self.base_url:
            return False
        
        try:
            parsed = urlparse(self.base_url)
            hostname = parsed.hostname
            
            # Check for common localhost patterns
            if hostname in ['localhost', '127.0.0.1', '::1']:
                return True
            
            return False
        except Exception:
            return False
    
    def _validate_base_url(self) -> None:
        """Validate base URL for security (SSRF protection).
        
        Raises:
            ValueError: If URL is invalid or potentially unsafe
        """
        if not self.base_url:
            return
        
        try:
            parsed = urlparse(self.base_url)
            
            
            # Check URL scheme - only allow http/https
            if parsed.scheme not in ('http', 'https'):
                raise ValueError(f"Invalid URL scheme: {parsed.scheme}. Only http/https allowed.")
            
            # Check hostname exists
            if not parsed.hostname:
                raise ValueError("URL must include a hostname")
            
            # Check port - allow only standard HTTP/HTTPS ports
            port = parsed.port
            if port is None:
                port = 443 if parsed.scheme == 'https' else 80
            
            # Allow common HTTP ports and some alternative ports
            allowed_ports = {80, 443, 8080, 8443, 4000, 3000}  # Common API ports
            if port not in allowed_ports:
                raise ValueError(
                    f"Port {port} not allowed. Allowed ports: {sorted(allowed_ports)}"
                )
            
            # Check against allowed domains if configured
            allowed_domains = os.getenv("ALLOWED_BASE_DOMAINS", "").split(",")
            allowed_domains = [d.strip().lower() for d in allowed_domains if d.strip()]
            
            if allowed_domains:
                hostname_lower = parsed.hostname.lower()
                if not any(
                    hostname_lower == domain or 
                    hostname_lower.endswith('.' + domain) 
                    for domain in allowed_domains
                ):
                    raise ValueError(
                        f"Domain not in allow-list: {parsed.hostname}. "
                        f"Allowed domains: {allowed_domains}"
                    )
            
            # Try to resolve hostname and check if it's a private IP
            # Skip for localhost addresses which are commonly used for development
            if parsed.hostname not in ['localhost', '127.0.0.1', '::1']:
                try:
                    # Get all IP addresses for the hostname
                    addr_info = socket.getaddrinfo(parsed.hostname, port, proto=socket.IPPROTO_TCP)
                    
                    for family, _, _, _, sockaddr in addr_info:
                        ip_str = sockaddr[0]
                        try:
                            ip = ipaddress.ip_address(ip_str)
                            
                            # Check for dangerous IP ranges
                            if (ip.is_private or ip.is_loopback or ip.is_link_local or 
                                ip.is_multicast or ip.is_reserved or ip.is_unspecified):
                                raise ValueError(
                                    f"URL resolves to restricted IP address: {ip_str}. "
                                    "This could be a security risk (SSRF)."
                                )
                        except ValueError as ve:
                            # Invalid IP address format or restricted IP - re-raise if it's our security error
                            if "restricted IP address" in str(ve):
                                raise
                            continue
                            
                except socket.gaierror as e:
                    # If we can't resolve the hostname, it's suspicious
                    raise ValueError(f"Cannot resolve hostname '{parsed.hostname}': {e}")
            
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"Invalid base URL '{self.base_url}': {str(e)}")
    
    @property
    def client(self):
        """Lazy initialization of OpenAI client with security checks."""
        if self._client is None:
            client_kwargs = {
                "api_key": self.api_key,
            }
            
            if self.base_url:
                client_kwargs["base_url"] = self.base_url
            
            if self.organization:
                client_kwargs["organization"] = self.organization
            
            # Add default headers if any
            if self.DEFAULT_HEADERS:
                client_kwargs["default_headers"] = self.DEFAULT_HEADERS.copy()
            
            self._client = OpenAI(**client_kwargs)
        
        return self._client
    
    def generate_content(
        self,
        prompt: str,
        model_name: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_output_tokens: Optional[int] = None,
        **kwargs,
    ) -> ModelResponse:
        """Generate content using the OpenAI-compatible API.
        
        Args:
            prompt: User prompt to send to the model
            model_name: Name of the model to use
            system_prompt: Optional system prompt for model behavior
            temperature: Sampling temperature
            max_output_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters
            
        Returns:
            ModelResponse with generated content and metadata
        """
        # Validate model name against allow-list
        if not self.validate_model_name(model_name):
            raise ValueError(
                f"Model '{model_name}' not in allowed models list. "
                f"Allowed models: {self.allowed_models}"
            )
        
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
            if key in ["top_p", "frequency_penalty", "presence_penalty", "seed", "stop", "stream"]:
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
                friendly_name=self.FRIENDLY_NAME,
                provider=self.get_provider_type(),
                metadata={
                    "finish_reason": response.choices[0].finish_reason,
                    "model": response.model,  # Actual model used
                    "id": response.id,
                    "created": response.created,
                },
            )
            
        except Exception as e:
            # Log error and re-raise with more context
            error_msg = f"{self.FRIENDLY_NAME} API error for model {model_name}: {str(e)}"
            logging.error(error_msg)
            raise RuntimeError(error_msg) from e
    
    def count_tokens(self, text: str, model_name: str) -> int:
        """Count tokens for the given text.
        
        Uses a layered approach:
        1. Try provider-specific token counting endpoint
        2. Try tiktoken for known model families
        3. Fall back to character-based estimation
        
        Args:
            text: Text to count tokens for
            model_name: Model name for tokenizer selection
            
        Returns:
            Estimated token count
        """
        # 1. Check if provider has a remote token counting endpoint
        if hasattr(self, 'count_tokens_remote'):
            try:
                return self.count_tokens_remote(text, model_name)
            except Exception as e:
                logging.debug(f"Remote token counting failed: {e}")
        
        # 2. Try tiktoken for known models
        try:
            import tiktoken
            
            # Try to get encoding for the specific model
            try:
                encoding = tiktoken.encoding_for_model(model_name)
            except KeyError:
                # Try common encodings based on model patterns
                if "gpt-4" in model_name or "gpt-3.5" in model_name:
                    encoding = tiktoken.get_encoding("cl100k_base")
                else:
                    encoding = tiktoken.get_encoding("cl100k_base")  # Default
            
            return len(encoding.encode(text))
            
        except (ImportError, Exception) as e:
            logging.debug(f"Tiktoken not available or failed: {e}")
        
        # 3. Fall back to character-based estimation
        logging.warning(
            f"No specific tokenizer available for '{model_name}'. "
            "Using character-based estimation (~4 chars per token)."
        )
        return len(text) // 4
    
    def validate_parameters(self, model_name: str, temperature: float, **kwargs) -> None:
        """Validate model parameters.
        
        For proxy providers, this may use generic capabilities.
        
        Args:
            model_name: Model to validate for
            temperature: Temperature to validate
            **kwargs: Additional parameters to validate
        """
        try:
            capabilities = self.get_capabilities(model_name)
            
            # Check if we're using generic capabilities
            if hasattr(capabilities, '_is_generic'):
                logging.debug(
                    f"Using generic parameter validation for {model_name}. "
                    "Actual model constraints may differ."
                )
            
            # Validate temperature using parent class method
            super().validate_parameters(model_name, temperature, **kwargs)
            
        except Exception as e:
            # For proxy providers, we might not have accurate capabilities
            # Log warning but don't fail
            logging.warning(f"Parameter validation limited for {model_name}: {e}")
    
    def _extract_usage(self, response) -> dict[str, int]:
        """Extract token usage from OpenAI response.
        
        Args:
            response: OpenAI API response object
            
        Returns:
            Dictionary with usage statistics
        """
        usage = {}
        
        if hasattr(response, "usage") and response.usage:
            usage["input_tokens"] = getattr(response.usage, "prompt_tokens", 0)
            usage["output_tokens"] = getattr(response.usage, "completion_tokens", 0)
            usage["total_tokens"] = getattr(response.usage, "total_tokens", 0)
        
        return usage
    
    @abstractmethod
    def get_capabilities(self, model_name: str) -> ModelCapabilities:
        """Get capabilities for a specific model.
        
        Must be implemented by subclasses.
        """
        pass
    
    @abstractmethod
    def get_provider_type(self) -> ProviderType:
        """Get the provider type.
        
        Must be implemented by subclasses.
        """
        pass
    
    @abstractmethod
    def validate_model_name(self, model_name: str) -> bool:
        """Validate if the model name is supported.
        
        Must be implemented by subclasses.
        """
        pass
    
    def supports_thinking_mode(self, model_name: str) -> bool:
        """Check if the model supports extended thinking mode.
        
        Default is False for OpenAI-compatible providers.
        """
        return False