# HTTP Recording/Replay Testing with HTTP Transport Recorder

This project uses a custom HTTP Transport Recorder for testing expensive API integrations (like o3-pro) with real recorded responses.

## What is HTTP Transport Recorder?

The HTTP Transport Recorder is a custom httpx transport implementation that intercepts HTTP requests/responses at the transport layer. This approach provides:

- **Real API structure**: Tests use actual API responses, not guessed mocks
- **Cost efficiency**: Only pay for API calls once during recording
- **Deterministic tests**: Same response every time, no API variability
- **Transport-level interception**: Works seamlessly with httpx and OpenAI SDK
- **Full response capture**: Captures complete HTTP responses including headers and gzipped content

## Directory Structure

```
tests/
├── openai_cassettes/         # Recorded HTTP interactions
│   ├── o3_pro_basic_math.json
│   └── o3_pro_content_capture.json
├── http_transport_recorder.py  # Transport recorder implementation
├── test_content_capture.py     # Example recording test
└── test_replay.py             # Example replay test
```

## Key Components

### RecordingTransport
- Wraps httpx's default transport
- Makes real HTTP calls and captures responses
- Handles gzip compression/decompression properly
- Saves interactions to JSON cassettes

### ReplayTransport
- Serves saved responses from cassettes
- No real HTTP calls made
- Matches requests by method, path, and content hash
- Re-applies gzip compression when needed

### TransportFactory
- Auto-selects record vs replay mode based on cassette existence
- Simplifies test setup

## Workflow

### 1. Use Transport Recorder in Tests

```python
from tests.http_transport_recorder import TransportFactory

# Create transport based on cassette existence
cassette_path = "tests/openai_cassettes/my_test.json"
transport = TransportFactory.create_transport(cassette_path)

# Inject into OpenAI provider
provider = ModelProviderRegistry.get_provider_for_model("o3-pro")
provider._test_transport = transport

# Make API calls - will be recorded/replayed automatically
```

### 2. Initial Recording (Expensive)

```bash
# With real API key, cassette doesn't exist -> records
python test_content_capture.py

# ⚠️ This will cost money! O3-Pro is $15-60 per 1K tokens
# But only needs to be done once
```

### 3. Subsequent Runs (Free)

```bash
# Cassette exists -> replays
python test_replay.py

# Can even use fake API key to prove no real calls
OPENAI_API_KEY="sk-fake-key" python test_replay.py

# Fast, free, deterministic
```

### 4. Re-recording (When API Changes)

```bash
# Delete cassette to force re-recording
rm tests/openai_cassettes/my_test.json

# Run test again with real API key
python test_content_capture.py
```

## How It Works

1. **Transport Injection**: Custom transport injected into httpx client
2. **Request Interception**: All HTTP requests go through custom transport
3. **Mode Detection**: Checks if cassette exists (replay) or needs creation (record)
4. **Content Capture**: Properly handles streaming responses and gzip encoding
5. **Request Matching**: Uses method + path + content hash for deterministic matching

## Cassette Format

```json
{
  "interactions": [
    {
      "request": {
        "method": "POST",
        "url": "https://api.openai.com/v1/responses",
        "path": "/v1/responses",
        "headers": {
          "content-type": "application/json",
          "accept-encoding": "gzip, deflate"
        },
        "content": {
          "model": "o3-pro-2025-06-10",
          "input": [...],
          "reasoning": {"effort": "medium"}
        }
      },
      "response": {
        "status_code": 200,
        "headers": {
          "content-type": "application/json",
          "content-encoding": "gzip"
        },
        "content": {
          "data": "base64_encoded_response_body",
          "encoding": "base64",
          "size": 1413
        },
        "reason_phrase": "OK"
      }
    }
  ]
}
```

Key features:
- Complete request/response capture
- Base64 encoding for binary content
- Preserves gzip compression
- Sanitizes sensitive data (API keys removed)

## Benefits Over Previous Approaches

1. **Works with any HTTP client**: Not tied to OpenAI SDK specifically
2. **Handles compression**: Properly manages gzipped responses
3. **Full HTTP fidelity**: Captures headers, status codes, etc.
4. **Simpler than VCR.py**: No sync/async conflicts or monkey patching
5. **Better than respx**: No streaming response issues

## Example Test

```python
#!/usr/bin/env python3
import asyncio
from pathlib import Path
from tests.http_transport_recorder import TransportFactory
from providers import ModelProviderRegistry
from tools.chat import ChatTool

async def test_with_recording():
    cassette_path = "tests/openai_cassettes/test_example.json"
    
    # Setup transport
    transport = TransportFactory.create_transport(cassette_path)
    provider = ModelProviderRegistry.get_provider_for_model("o3-pro")
    provider._test_transport = transport
    
    # Use ChatTool normally
    chat_tool = ChatTool()
    result = await chat_tool.execute({
        "prompt": "What is 2+2?",
        "model": "o3-pro",
        "temperature": 1.0
    })
    
    print(f"Response: {result[0].text}")

if __name__ == "__main__":
    asyncio.run(test_with_recording())
```

## Timeout Protection

Tests can use GNU timeout to prevent hanging:

```bash
# Install GNU coreutils if needed
brew install coreutils

# Run with 30 second timeout
gtimeout 30s python test_content_capture.py
```

## CI/CD Integration

```yaml
# In CI, tests use existing cassettes (no API keys needed)
- name: Run OpenAI tests
  run: |
    # Tests will use replay mode with existing cassettes
    python -m pytest tests/test_o3_pro.py
```

## Cost Management

- **One-time cost**: Initial recording per test scenario
- **Zero ongoing cost**: Replays are free
- **Controlled re-recording**: Manual cassette deletion required
- **CI-friendly**: No accidental API calls in automation

This HTTP transport recorder approach provides accurate API testing with cost efficiency, specifically optimized for expensive endpoints like o3-pro while being flexible enough for any HTTP-based API.