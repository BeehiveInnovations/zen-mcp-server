"""Dynamic LLM factory for gateway vs direct provider mode.

Usage:
    from agent.llm_factory import get_llm
    llm = get_llm()  # honors env vars USE_GATEWAY, GATEWAY_URL, LLM_PROVIDER, LLM_MODEL

Environment Variables:
    USE_GATEWAY=true|false
    GATEWAY_URL=http://localhost:8080/langchain (Bifrost/LiteLLM base)
    LLM_PROVIDER=openai|anthropic|google|azure
    LLM_MODEL=gpt-4o-mini|claude-3-sonnet-20240229|gemini-1.5-flash|...

This implementation uses lazy imports so missing provider SDKs won't break startup.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Literal

ProviderType = Literal["openai", "anthropic", "google", "azure"]

logger = logging.getLogger(__name__)

DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-sonnet-20240229",
    "google": "gemini-1.5-flash",
    "azure": "gpt-4o-mini",  # deployment name placeholder
}


def _bool_env(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.lower() in {"1", "true", "yes", "on"}


def get_llm(
    provider: ProviderType | None = None,
    model: str | None = None,
    use_gateway: bool | None = None,
    **kwargs: Any,
):
    """Return a configured LangChain chat model based on env + args.

    Falls back gracefully if a provider library is missing.
    """
    provider = provider or os.getenv("LLM_PROVIDER", "openai").lower()
    if provider not in DEFAULT_MODELS:
        raise ValueError(f"Unsupported provider '{provider}'")

    model = model or os.getenv("LLM_MODEL") or DEFAULT_MODELS[provider]
    gateway_url = os.getenv("GATEWAY_URL", "http://localhost:8080/langchain")
    use_gateway = _bool_env("USE_GATEWAY", True) if use_gateway is None else use_gateway

    if use_gateway:
        # Gateway mode: treat all providers as OpenAI-compatible where possible
        if provider == "openai":
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                model=model,
                openai_api_base=gateway_url,
                openai_api_key=os.getenv("UNIFIED_LLM_API_KEY", "dummy-key"),
                **kwargs,
            )
        elif provider == "anthropic":
            try:
                from langchain_anthropic import ChatAnthropic
            except ImportError:
                logger.warning("langchain_anthropic not installed; falling back to OpenAI wrapper")
                from langchain_openai import ChatOpenAI

                return ChatOpenAI(
                    model=model,
                    openai_api_base=gateway_url,
                    openai_api_key="dummy-key",
                    **kwargs,
                )
            return ChatAnthropic(
                model=model,
                anthropic_api_url=gateway_url,
                anthropic_api_key="dummy-key",
                **kwargs,
            )
        elif provider == "google":
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
            except ImportError:
                logger.warning("langchain_google_genai not installed; falling back to OpenAI wrapper")
                from langchain_openai import ChatOpenAI

                return ChatOpenAI(
                    model=model,
                    openai_api_base=gateway_url,
                    openai_api_key="dummy-key",
                    **kwargs,
                )
            return ChatGoogleGenerativeAI(
                model=model,
                google_api_base=gateway_url,
                google_api_key="dummy-key",
                **kwargs,
            )
        elif provider == "azure":
            try:
                from langchain_openai import AzureChatOpenAI
            except ImportError:
                logger.warning("Azure chat model not available; ensure langchain_openai is installed.")
                from langchain_openai import ChatOpenAI

                return ChatOpenAI(
                    model=model,
                    openai_api_base=gateway_url,
                    openai_api_key="dummy-key",
                    **kwargs,
                )
            return AzureChatOpenAI(
                deployment_name=model,
                azure_endpoint=gateway_url,
                api_key="dummy-key",
                api_version=kwargs.pop("api_version", "2024-05-01-preview"),
                **kwargs,
            )
    else:
        # Direct mode: provider-specific API keys
        if provider == "openai":
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                model=model,
                openai_api_key=os.getenv("OPENAI_API_KEY"),
                **kwargs,
            )
        elif provider == "anthropic":
            try:
                from langchain_anthropic import ChatAnthropic
            except ImportError:
                raise RuntimeError("Anthropic provider requested but langchain_anthropic not installed")
            return ChatAnthropic(
                model=model,
                anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
                **kwargs,
            )
        elif provider == "google":
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
            except ImportError:
                raise RuntimeError("Google provider requested but langchain_google_genai not installed")
            return ChatGoogleGenerativeAI(
                model=model,
                google_api_key=os.getenv("GOOGLE_API_KEY"),
                **kwargs,
            )
        elif provider == "azure":
            try:
                from langchain_openai import AzureChatOpenAI
            except ImportError:
                raise RuntimeError("Azure provider requested but langchain_openai not installed")
            return AzureChatOpenAI(
                deployment_name=model,
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                api_key=os.getenv("AZURE_OPENAI_KEY"),
                api_version=kwargs.pop("api_version", "2024-05-01-preview"),
                **kwargs,
            )

    raise ValueError(f"Unsupported provider mode combination: provider={provider} use_gateway={use_gateway}")
