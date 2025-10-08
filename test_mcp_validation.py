#!/usr/bin/env python3
"""Test script to debug MCP tools/list validation issue."""

import json
from typing import Any, Literal

from pydantic import BaseModel, ValidationError


# Recreate the relevant types locally to avoid import issues
class RequestParams(BaseModel):
    class Meta(BaseModel):
        progressToken: str | int | None = None

    meta: Meta | None = None


class JSONRPCRequest(BaseModel):
    jsonrpc: Literal["2.0"]
    id: str | int
    method: str
    params: dict[str, Any] | None = None


class ListToolsRequest(BaseModel):
    method: Literal["tools/list"]
    params: RequestParams | None = None


def test_tools_list_validation():
    """Test validation of tools/list request."""

    # Simulate incoming JSON-RPC request for tools/list
    raw_request = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}  # Empty params that Claude sends

    print("Testing tools/list validation...")
    print(f"Raw request: {json.dumps(raw_request, indent=2)}")

    # Step 1: Parse as JSONRPCRequest
    try:
        jsonrpc_req = JSONRPCRequest(**raw_request)
        print("✅ JSONRPCRequest parsed successfully")
        print(f"   jsonrpc_req.params type: {type(jsonrpc_req.params)}")
        print(f"   jsonrpc_req.params value: {jsonrpc_req.params}")
    except ValidationError as e:
        print(f"❌ Failed to parse JSONRPCRequest: {e}")
        return

    # Step 2: Dump and try to validate as ListToolsRequest
    try:
        dumped = jsonrpc_req.model_dump(by_alias=True, mode="json", exclude_none=True)
        print(f"\nDumped JSONRPCRequest: {json.dumps(dumped, indent=2)}")

        # Try to validate the dumped data as ListToolsRequest
        tools_req = ListToolsRequest.model_validate(dumped)
        print("✅ ListToolsRequest validated from dumped data")
    except ValidationError as e:
        print("❌ Failed to validate ListToolsRequest from dumped data:")
        print("\nValidation errors:")
        for error in e.errors():
            print(f"  - {error['loc']}: {error['msg']}")

    # Step 3: Try direct ListToolsRequest validation
    print("\n--- Direct ListToolsRequest validation ---")
    try:
        # Try with empty params dict
        tools_req = ListToolsRequest(method="tools/list", params={})
        print("❌ ListToolsRequest with params={} should fail but didn't!")
    except ValidationError as e:
        print(f"✅ ListToolsRequest with params={{}} correctly failed: {e.errors()[0]['msg']}")

    try:
        # Try with None params
        tools_req = ListToolsRequest(method="tools/list", params=None)
        print("✅ ListToolsRequest with params=None succeeded")
    except ValidationError as e:
        print(f"❌ ListToolsRequest with params=None failed: {e}")

    try:
        # Try with proper RequestParams
        params = RequestParams()
        tools_req = ListToolsRequest(method="tools/list", params=params)
        print("✅ ListToolsRequest with RequestParams() succeeded")
    except ValidationError as e:
        print(f"❌ ListToolsRequest with RequestParams() failed: {e}")

    # Step 4: Test the actual problem - empty dict to RequestParams
    print("\n--- Testing dict to RequestParams conversion ---")
    try:
        # This is what happens when params={} comes in
        params = RequestParams(**{})
        print("✅ RequestParams from empty dict succeeded")
    except ValidationError as e:
        print(f"❌ RequestParams from empty dict failed: {e}")


if __name__ == "__main__":
    test_tools_list_validation()
