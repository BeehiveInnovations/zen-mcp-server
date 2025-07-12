"""Secure HTTP utilities for preventing credential leakage in logs."""

import logging
from contextlib import contextmanager
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class SecureHTTPClient:
    """HTTP client wrapper that prevents sensitive data from being logged."""

    SENSITIVE_HEADERS = {
        "authorization",
        "x-api-key",
        "api-key",
        "x-auth-token",
        "cookie",
        "set-cookie",
        "x-goog-iam-authorization-token",
    }

    def __init__(self, timeout: Optional[httpx.Timeout] = None, **kwargs):
        """Initialize secure HTTP client.

        Args:
            timeout: Request timeout configuration
            **kwargs: Additional httpx.Client arguments
        """
        self._client = httpx.Client(timeout=timeout or httpx.Timeout(30.0, read=60.0), **kwargs)

    def post(self, url: str, headers: Optional[dict[str, str]] = None, **kwargs) -> httpx.Response:
        """Make POST request with secure header logging.

        Args:
            url: Target URL
            headers: Request headers (sensitive ones will be masked in logs)
            **kwargs: Additional request arguments

        Returns:
            HTTP response
        """
        # Log request with masked headers
        if logger.isEnabledFor(logging.DEBUG):
            safe_headers = self._mask_sensitive_headers(headers or {})
            logger.debug(f"POST {url} with headers: {safe_headers}")

        return self._client.post(url, headers=headers, **kwargs)

    def _mask_sensitive_headers(self, headers: dict[str, str]) -> dict[str, str]:
        """Mask sensitive header values for logging.

        Args:
            headers: Original headers

        Returns:
            Headers with sensitive values masked
        """
        masked = {}
        for key, value in headers.items():
            if key.lower() in self.SENSITIVE_HEADERS:
                # Show first 4 chars and mask the rest
                if len(value) > 8:
                    masked[key] = f"{value[:4]}...{value[-4:]}"
                else:
                    masked[key] = "***MASKED***"
            else:
                masked[key] = value
        return masked

    def close(self):
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


@contextmanager
def secure_http_client(**kwargs):
    """Context manager for secure HTTP client.

    Args:
        **kwargs: Arguments passed to SecureHTTPClient

    Yields:
        Configured SecureHTTPClient instance
    """
    client = SecureHTTPClient(**kwargs)
    try:
        yield client
    finally:
        client.close()
