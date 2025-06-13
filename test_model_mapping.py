#!/usr/bin/env python3
"""
Simple test script to demonstrate model mapping through the MCP server.
Tests how model aliases (flash, pro, o3) are mapped to OpenRouter models.
"""

import subprocess
import json
import sys
from typing import Dict, Any

def call_mcp_server(model: str, message: str = "Hello, which model are you?") -> Dict[str, Any]:
    """Call the MCP server with a specific model and return the response."""
    
    # Prepare the request
    request = {
        "jsonrpc": "2.0",
        "method": "completion",
        "params": {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": message
                }
            ],
            "max_tokens": 100
        },
        "id": 1
    }
    
    # Call the server
    cmd = [sys.executable, "server.py"]
    
    try:
        # Send request to stdin and capture output
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = process.communicate(input=json.dumps(request))
        
        if process.returncode != 0:
            return {
                "error": f"Server returned non-zero exit code: {process.returncode}",
                "stderr": stderr
            }
        
        # Parse the response
        try:
            response = json.loads(stdout)
            return response
        except json.JSONDecodeError:
            return {
                "error": "Failed to parse JSON response",
                "stdout": stdout,
                "stderr": stderr
            }
            
    except Exception as e:
        return {
            "error": f"Failed to call server: {str(e)}"
        }

def extract_model_info(response: Dict[str, Any]) -> Dict[str, str]:
    """Extract model information from the response."""
    
    if "error" in response:
        return {
            "status": "error",
            "message": response.get("error", "Unknown error")
        }
    
    # Look for result in the response
    result = response.get("result", {})
    
    # Extract relevant information
    info = {
        "status": "success",
        "provider": "unknown",
        "model": "unknown"
    }
    
    # Try to find provider and model info in the response
    # This might be in metadata or debug info depending on server implementation
    if "metadata" in result:
        metadata = result["metadata"]
        info["provider"] = metadata.get("provider", "unknown")
        info["model"] = metadata.get("model", "unknown")
    
    # Also check if the model info is in the response content itself
    if "content" in result:
        content = result["content"]
        # Simple heuristic to detect OpenRouter models
        if "openrouter" in content.lower() or any(x in content.lower() for x in ["claude", "gpt", "gemini"]):
            info["provider"] = "openrouter"
    
    return info

def main():
    """Test model mapping for different aliases."""
    
    print("Model Mapping Test for MCP Server")
    print("=" * 50)
    print()
    
    # Test models
    test_models = ["flash", "pro", "o3"]
    
    for model in test_models:
        print(f"Testing model: '{model}'")
        print("-" * 30)
        
        response = call_mcp_server(model)
        model_info = extract_model_info(response)
        
        if model_info["status"] == "error":
            print(f"  ❌ Error: {model_info['message']}")
        else:
            print(f"  ✓ Provider: {model_info['provider']}")
            print(f"  ✓ Model: {model_info['model']}")
        
        # Print raw response for debugging
        if "--debug" in sys.argv:
            print("\nDebug - Raw Response:")
            print(json.dumps(response, indent=2))
        
        print()
    
    print("\nNote: This test assumes the MCP server is configured with OpenRouter.")
    print("The actual model mappings depend on the server configuration.")

if __name__ == "__main__":
    main()