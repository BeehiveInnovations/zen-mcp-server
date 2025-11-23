"""Tests for clink retry and backoff logic."""

from pathlib import Path

import pytest

from clink.agents.base import AgentOutput, BaseCLIAgent, CLIAgentError
from clink.models import ResolvedCLIClient, ResolvedCLIRole
from clink.parsers.base import ParsedCLIResponse


@pytest.fixture
def mock_client():
    """Create a mock CLI client with retry configuration."""
    return ResolvedCLIClient(
        name="test-cli",
        executable=["test-command"],
        internal_args=[],
        config_args=[],
        env={},
        timeout_seconds=60,
        max_retries=3,
        retry_delays=[1.0, 2.0, 3.0],
        parser="gemini_json",
        runner=None,
        roles={
            "default": ResolvedCLIRole(
                name="default",
                prompt_path=Path("/fake/prompt.txt"),
                role_args=[],
            )
        },
        output_to_file=None,
        working_dir=None,
    )


@pytest.fixture
def mock_role():
    """Create a mock CLI role."""
    return ResolvedCLIRole(
        name="default",
        prompt_path=Path("/fake/prompt.txt"),
        role_args=[],
    )


@pytest.mark.asyncio
async def test_retry_on_rate_limit_error(mock_client, mock_role):
    """Test that agent retries on rate limit errors."""
    agent = BaseCLIAgent(mock_client)

    # Mock _execute_once to fail twice with rate limit, then succeed
    call_count = 0

    async def mock_execute(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            # First two calls fail with rate limit error
            raise CLIAgentError(
                "Rate limit exceeded",
                returncode=1,
                stdout="",
                stderr="429 rate limit exceeded",
            )
        # Third call succeeds
        return AgentOutput(
            parsed=ParsedCLIResponse(content="Success", metadata={}),
            sanitized_command=["test"],
            returncode=0,
            stdout="Success",
            stderr="",
            duration_seconds=1.0,
            parser_name="test_parser",
        )

    agent._execute_once = mock_execute

    # Run the agent
    result = await agent.run(
        role=mock_role,
        prompt="test prompt",
        files=[],
        images=[],
    )

    # Verify it eventually succeeded after retries
    assert result.parsed.content == "Success"
    assert call_count == 3


@pytest.mark.asyncio
async def test_no_retry_on_non_retryable_error(mock_client, mock_role):
    """Test that agent does not retry on non-retryable errors."""
    agent = BaseCLIAgent(mock_client)

    call_count = 0

    async def mock_execute(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        # Always fail with a non-retryable error
        raise CLIAgentError(
            "Command not found",
            returncode=127,
            stdout="",
            stderr="command not found: test-command",
        )

    agent._execute_once = mock_execute

    # Run the agent and expect it to fail immediately
    with pytest.raises(CLIAgentError, match="Command not found"):
        await agent.run(
            role=mock_role,
            prompt="test prompt",
            files=[],
            images=[],
        )

    # Verify it only tried once (no retries)
    assert call_count == 1


@pytest.mark.asyncio
async def test_max_retries_exhausted(mock_client, mock_role):
    """Test that agent stops retrying after max_retries is exhausted."""
    agent = BaseCLIAgent(mock_client)

    call_count = 0

    async def mock_execute(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        # Always fail with rate limit error
        raise CLIAgentError(
            "Rate limit exceeded",
            returncode=1,
            stdout="",
            stderr="429 rate limit exceeded",
        )

    agent._execute_once = mock_execute

    # Run the agent and expect it to fail after all retries
    with pytest.raises(CLIAgentError, match="Rate limit exceeded"):
        await agent.run(
            role=mock_role,
            prompt="test prompt",
            files=[],
            images=[],
        )

    # Verify it tried max_retries + 1 times (initial attempt + 3 retries)
    assert call_count == mock_client.max_retries + 1


@pytest.mark.asyncio
async def test_retry_delay_applied(mock_client, mock_role):
    """Test that retry delays are properly applied between attempts."""
    agent = BaseCLIAgent(mock_client)

    call_times = []

    async def mock_execute(*args, **kwargs):
        import time

        call_times.append(time.monotonic())
        if len(call_times) < 3:
            raise CLIAgentError(
                "Rate limit exceeded",
                returncode=1,
                stdout="",
                stderr="429 rate limit exceeded",
            )
        return AgentOutput(
            parsed=ParsedCLIResponse(content="Success", metadata={}),
            sanitized_command=["test"],
            returncode=0,
            stdout="Success",
            stderr="",
            duration_seconds=1.0,
            parser_name="test_parser",
        )

    agent._execute_once = mock_execute

    # Run the agent
    await agent.run(
        role=mock_role,
        prompt="test prompt",
        files=[],
        images=[],
    )

    # Verify delays were applied (allow 20% jitter + execution time margin)
    assert len(call_times) == 3
    # First retry delay should be ~1.0s (0.8 to 1.2 with jitter)
    assert 0.7 <= (call_times[1] - call_times[0]) <= 1.5
    # Second retry delay should be ~2.0s (1.6 to 2.4 with jitter)
    assert 1.5 <= (call_times[2] - call_times[1]) <= 2.6


def test_is_retryable_error():
    """Test the _is_retryable_error method."""
    agent = BaseCLIAgent(
        ResolvedCLIClient(
            name="test",
            executable=["test"],
            internal_args=[],
            config_args=[],
            env={},
            timeout_seconds=60,
            max_retries=3,
            retry_delays=[1.0],
            parser="gemini_json",
            runner=None,
            roles={},
            output_to_file=None,
            working_dir=None,
        )
    )

    # Test rate limit errors are retryable
    rate_limit_error = CLIAgentError("Error", returncode=1, stdout="", stderr="429 rate limit exceeded")
    assert agent._is_retryable_error(rate_limit_error)

    # Test non-retryable quota errors (permanent failures)
    quota_error = CLIAgentError("Error", returncode=1, stdout="quota exceeded", stderr="")
    assert not agent._is_retryable_error(quota_error)

    # Test resource exhausted errors are retryable
    resource_error = CLIAgentError("Error", returncode=1, stdout="", stderr="resource_exhausted")
    assert agent._is_retryable_error(resource_error)

    # Test non-retryable errors
    normal_error = CLIAgentError("Error", returncode=1, stdout="", stderr="command not found")
    assert not agent._is_retryable_error(normal_error)


@pytest.mark.asyncio
async def test_retry_on_quota_error(mock_client, mock_role):
    """Test that agent uses quota retry strategy for quota errors."""
    # Configure mock client with distinct quota settings
    mock_client.quota_max_retries = 3
    mock_client.quota_retry_delays = [0.1, 0.2, 0.3]  # Short delays for test
    mock_client.max_retries = 1  # Different from quota retries

    agent = BaseCLIAgent(mock_client)

    call_count = 0

    async def mock_execute(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 4:
            # First three calls fail with quota error
            # "quota" must be in stderr/stdout and NOT "quota exceeded"
            raise CLIAgentError(
                "Quota error",
                returncode=1,
                stdout="",
                stderr="429 Quota error",
            )
        return AgentOutput(
            parsed=ParsedCLIResponse(content="Success", metadata={}),
            sanitized_command=["test"],
            returncode=0,
            stdout="Success",
            stderr="",
            duration_seconds=1.0,
            parser_name="test_parser",
        )

    agent._execute_once = mock_execute

    result = await agent.run(
        role=mock_role,
        prompt="test prompt",
        files=[],
        images=[],
    )

    assert result.parsed.content == "Success"
    assert call_count == 4  # Initial + 3 retries
