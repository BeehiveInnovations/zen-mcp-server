#!/usr/bin/env python3
"""
PII (Personally Identifiable Information) Sanitizer for HTTP recordings.

This module provides comprehensive sanitization of sensitive data in HTTP
request/response recordings to prevent accidental exposure of API keys,
tokens, personal information, and other sensitive data.
"""

import re
import base64
import json
from typing import Any, Dict, List, Optional, Pattern, Tuple
from dataclasses import dataclass
from copy import deepcopy
import logging

logger = logging.getLogger(__name__)


@dataclass
class PIIPattern:
    """Defines a pattern for detecting and sanitizing PII."""
    name: str
    pattern: Pattern[str]
    replacement: str
    description: str
    
    @classmethod
    def create(cls, name: str, pattern: str, replacement: str, description: str) -> 'PIIPattern':
        """Create a PIIPattern with compiled regex."""
        return cls(
            name=name,
            pattern=re.compile(pattern),
            replacement=replacement,
            description=description
        )


class PIISanitizer:
    """Sanitizes PII from various data structures while preserving format."""
    
    def __init__(self, patterns: Optional[List[PIIPattern]] = None):
        """Initialize with optional custom patterns."""
        self.patterns: List[PIIPattern] = patterns or []
        self.sanitize_enabled = True
        
        # Add default patterns if none provided
        if not patterns:
            self._add_default_patterns()
    
    def _add_default_patterns(self):
        """Add comprehensive default PII patterns."""
        default_patterns = [
            # API Keys and Tokens
            PIIPattern.create(
                name="openai_api_key_proj",
                pattern=r'sk-proj-[A-Za-z0-9\-_]{48,}',
                replacement="sk-proj-SANITIZED",
                description="OpenAI project API keys"
            ),
            PIIPattern.create(
                name="openai_api_key",
                pattern=r'sk-[A-Za-z0-9]{48,}',
                replacement="sk-SANITIZED",
                description="OpenAI API keys"
            ),
            PIIPattern.create(
                name="anthropic_api_key",
                pattern=r'sk-ant-[A-Za-z0-9\-_]{48,}',
                replacement="sk-ant-SANITIZED",
                description="Anthropic API keys"
            ),
            PIIPattern.create(
                name="google_api_key",
                pattern=r'AIza[A-Za-z0-9\-_]{35,}',
                replacement="AIza-SANITIZED",
                description="Google API keys"
            ),
            PIIPattern.create(
                name="github_token_personal",
                pattern=r'ghp_[A-Za-z0-9]{36}',
                replacement="ghp_SANITIZED",
                description="GitHub personal access tokens"
            ),
            PIIPattern.create(
                name="github_token_server",
                pattern=r'ghs_[A-Za-z0-9]{36}',
                replacement="ghs_SANITIZED",
                description="GitHub server tokens"
            ),
            PIIPattern.create(
                name="github_token_refresh",
                pattern=r'ghr_[A-Za-z0-9]{36}',
                replacement="ghr_SANITIZED",
                description="GitHub refresh tokens"
            ),
            
            # Bearer tokens with specific API keys (must come before generic patterns)
            PIIPattern.create(
                name="bearer_openai_proj",
                pattern=r'Bearer\s+sk-proj-[A-Za-z0-9\-_]{48,}',
                replacement="Bearer sk-proj-SANITIZED",
                description="Bearer with OpenAI project key"
            ),
            PIIPattern.create(
                name="bearer_openai",
                pattern=r'Bearer\s+sk-[A-Za-z0-9]{48,}',
                replacement="Bearer sk-SANITIZED",
                description="Bearer with OpenAI key"
            ),
            PIIPattern.create(
                name="bearer_anthropic",
                pattern=r'Bearer\s+sk-ant-[A-Za-z0-9\-_]{48,}',
                replacement="Bearer sk-ant-SANITIZED",
                description="Bearer with Anthropic key"
            ),
            
            # JWT tokens
            PIIPattern.create(
                name="jwt_token",
                pattern=r'eyJ[A-Za-z0-9\-_]+\.eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+',
                replacement="eyJ-SANITIZED.eyJ-SANITIZED.SANITIZED",
                description="JSON Web Tokens"
            ),
            
            # Personal Information
            PIIPattern.create(
                name="email_address",
                pattern=r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}',
                replacement="user@example.com",
                description="Email addresses"
            ),
            PIIPattern.create(
                name="ipv4_address",
                pattern=r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b',
                replacement="0.0.0.0",
                description="IPv4 addresses"
            ),
            PIIPattern.create(
                name="ipv6_address",
                pattern=r'(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}',
                replacement="::1",
                description="IPv6 addresses"
            ),
            PIIPattern.create(
                name="ssn",
                pattern=r'\b\d{3}-\d{2}-\d{4}\b',
                replacement="XXX-XX-XXXX",
                description="Social Security Numbers"
            ),
            PIIPattern.create(
                name="credit_card",
                pattern=r'\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b',
                replacement="XXXX-XXXX-XXXX-XXXX",
                description="Credit card numbers"
            ),
            # Phone patterns - international first to avoid partial matches
            PIIPattern.create(
                name="phone_intl",
                pattern=r'\+\d{1,3}[\s\-]?\d{3}[\s\-]?\d{3}[\s\-]?\d{4}',
                replacement="+X-XXX-XXX-XXXX",
                description="International phone numbers"
            ),
            PIIPattern.create(
                name="phone_us",
                pattern=r'\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4}',
                replacement="(XXX) XXX-XXXX",
                description="US phone numbers"
            ),
            
            # AWS
            PIIPattern.create(
                name="aws_access_key",
                pattern=r'AKIA[0-9A-Z]{16}',
                replacement="AKIA-SANITIZED",
                description="AWS access keys"
            ),
            PIIPattern.create(
                name="aws_secret_key",
                pattern=r'(?i)aws[_\s]*secret[_\s]*access[_\s]*key["\s]*[:=]["\s]*[A-Za-z0-9/+=]{40}',
                replacement="aws_secret_access_key=SANITIZED",
                description="AWS secret keys"
            ),
            
            # Other common patterns
            PIIPattern.create(
                name="slack_token",
                pattern=r'xox[baprs]-[0-9]{10,13}-[0-9]{10,13}-[a-zA-Z0-9]{24,34}',
                replacement="xox-SANITIZED",
                description="Slack tokens"
            ),
            PIIPattern.create(
                name="stripe_key",
                pattern=r'(?:sk|pk)_(?:test|live)_[0-9a-zA-Z]{24,99}',
                replacement="sk_SANITIZED",
                description="Stripe API keys"
            ),
        ]
        
        self.patterns.extend(default_patterns)
    
    def add_pattern(self, pattern: PIIPattern):
        """Add a custom PII pattern."""
        self.patterns.append(pattern)
        logger.info(f"Added PII pattern: {pattern.name}")
    
    def sanitize_string(self, text: str) -> str:
        """Apply all patterns to sanitize a string."""
        if not self.sanitize_enabled or not isinstance(text, str):
            return text
        
        sanitized = text
        for pattern in self.patterns:
            if pattern.pattern.search(sanitized):
                sanitized = pattern.pattern.sub(pattern.replacement, sanitized)
                logger.debug(f"Applied {pattern.name} sanitization")
        
        return sanitized
    
    def sanitize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Special handling for HTTP headers."""
        if not self.sanitize_enabled:
            return headers
        
        sanitized_headers = {}
        sensitive_headers = {
            'authorization', 'api-key', 'x-api-key', 'cookie', 
            'set-cookie', 'x-auth-token', 'x-access-token'
        }
        
        for key, value in headers.items():
            lower_key = key.lower()
            
            if lower_key in sensitive_headers:
                # Special handling for authorization headers
                if lower_key == 'authorization':
                    if value.startswith('Bearer '):
                        sanitized_headers[key] = 'Bearer SANITIZED'
                    elif value.startswith('Basic '):
                        sanitized_headers[key] = 'Basic SANITIZED'
                    else:
                        sanitized_headers[key] = 'SANITIZED'
                else:
                    # For other sensitive headers, sanitize the value
                    sanitized_headers[key] = self.sanitize_string(value)
            else:
                # For non-sensitive headers, still check for PII patterns
                sanitized_headers[key] = self.sanitize_string(value)
        
        return sanitized_headers
    
    def sanitize_value(self, value: Any) -> Any:
        """Recursively sanitize any value (string, dict, list, etc)."""
        if not self.sanitize_enabled:
            return value
        
        if isinstance(value, str):
            # Check if it might be base64 encoded
            if self._is_base64(value) and len(value) > 20:
                try:
                    decoded = base64.b64decode(value).decode('utf-8')
                    if self._contains_pii(decoded):
                        sanitized = self.sanitize_string(decoded)
                        return base64.b64encode(sanitized.encode()).decode()
                except:
                    pass  # Not valid base64 or not UTF-8
            
            return self.sanitize_string(value)
        
        elif isinstance(value, dict):
            return {k: self.sanitize_value(v) for k, v in value.items()}
        
        elif isinstance(value, list):
            return [self.sanitize_value(item) for item in value]
        
        elif isinstance(value, tuple):
            return tuple(self.sanitize_value(item) for item in value)
        
        else:
            # For other types (int, float, bool, None), return as-is
            return value
    
    def sanitize_url(self, url: str) -> str:
        """Sanitize sensitive data from URLs (query params, etc)."""
        if not self.sanitize_enabled:
            return url
        
        # First apply general string sanitization
        url = self.sanitize_string(url)
        
        # Parse and sanitize query parameters
        if '?' in url:
            base, query = url.split('?', 1)
            params = []
            
            for param in query.split('&'):
                if '=' in param:
                    key, value = param.split('=', 1)
                    # Sanitize common sensitive parameter names
                    sensitive_params = {'key', 'token', 'api_key', 'secret', 'password'}
                    if key.lower() in sensitive_params:
                        params.append(f"{key}=SANITIZED")
                    else:
                        # Still sanitize the value for PII
                        params.append(f"{key}={self.sanitize_string(value)}")
                else:
                    params.append(param)
            
            return f"{base}?{'&'.join(params)}"
        
        return url
    
    def _is_base64(self, s: str) -> bool:
        """Check if a string might be base64 encoded."""
        try:
            if len(s) % 4 != 0:
                return False
            return re.match(r'^[A-Za-z0-9+/]*={0,2}$', s) is not None
        except:
            return False
    
    def _contains_pii(self, text: str) -> bool:
        """Quick check if text contains any PII patterns."""
        for pattern in self.patterns:
            if pattern.pattern.search(text):
                return True
        return False
    
    def sanitize_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize a complete request dictionary."""
        sanitized = deepcopy(request_data)
        
        # Sanitize headers
        if 'headers' in sanitized:
            sanitized['headers'] = self.sanitize_headers(sanitized['headers'])
        
        # Sanitize URL
        if 'url' in sanitized:
            sanitized['url'] = self.sanitize_url(sanitized['url'])
        
        # Sanitize content
        if 'content' in sanitized:
            sanitized['content'] = self.sanitize_value(sanitized['content'])
        
        return sanitized
    
    def sanitize_response(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize a complete response dictionary."""
        sanitized = deepcopy(response_data)
        
        # Sanitize headers
        if 'headers' in sanitized:
            sanitized['headers'] = self.sanitize_headers(sanitized['headers'])
        
        # Sanitize content
        if 'content' in sanitized:
            # Handle base64 encoded content specially
            if isinstance(sanitized['content'], dict) and sanitized['content'].get('encoding') == 'base64':
                # Don't decode/re-encode the actual response body
                # but sanitize any metadata
                if 'data' in sanitized['content']:
                    # Keep the data as-is but sanitize other fields
                    for key, value in sanitized['content'].items():
                        if key != 'data':
                            sanitized['content'][key] = self.sanitize_value(value)
            else:
                sanitized['content'] = self.sanitize_value(sanitized['content'])
        
        return sanitized


# Global instance for convenience
default_sanitizer = PIISanitizer()