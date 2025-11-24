
from unittest.mock import MagicMock
from enum import Enum

class ProviderType(Enum):
    OPENAI = "openai"
    GOOGLE = "google"

class ModelProviderRegistry:
    _instance = None
    PROVIDER_PRIORITY_ORDER = [ProviderType.GOOGLE, ProviderType.OPENAI]
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._providers = {}
        return cls._instance

    @classmethod
    def get_preferred_fallback_model(cls, tool_category=None):
        for provider_type in cls.PROVIDER_PRIORITY_ORDER:
            if provider_type not in cls._instance._providers:
                continue
            
            # This is the line that failed
            val = cls._instance._providers[provider_type]
            print(f"Type of val: {type(val)}")
            print(f"Val: {val}")
            provider_count = len(val)
            print(f"Count: {provider_count}")

mock_openai = MagicMock()
mock_gemini = MagicMock()

registry = ModelProviderRegistry()
registry._providers = {
    ProviderType.OPENAI: [type(mock_openai)],
    ProviderType.GOOGLE: [type(mock_gemini)],
}

try:
    ModelProviderRegistry.get_preferred_fallback_model()
    print("Success")
except TypeError as e:
    print(f"Caught expected error: {e}")
except Exception as e:
    print(f"Caught unexpected error: {e}")
