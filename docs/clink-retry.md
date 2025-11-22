# Clink Retry and Backoff

The `clink` tool now supports automatic retry with exponential backoff for handling transient errors, particularly rate limiting (HTTP 429).

## Configuration

Add retry settings to your CLI client configuration files in `conf/cli_clients/`:

```json
{
  "name": "gemini",
  "command": "gemini",
  "additional_args": ["--model", "gemini-3-pro-preview", "--yolo"],
  "max_retries": 5,
  "retry_delays": [3.0, 6.0, 12.0, 24.0, 48.0],
  "roles": {
    ...
  }
}
```

### Configuration Fields

- **`max_retries`** (optional, default: `3`): Maximum number of retry attempts on retryable errors. The total number of attempts will be `max_retries + 1` (initial attempt plus retries).

- **`retry_delays`** (optional, default: `[3.0, 6.0, 12.0]`): List of delay durations in seconds between retry attempts. If more retries are needed than delays provided, the last delay value is reused.

## Retryable Errors

The following error conditions trigger automatic retry:

- HTTP 429 status codes (rate limiting)
- Messages containing "rate limit"
- Messages containing "quota"
- Messages containing "too many requests"
- Messages containing "resource_exhausted"

All other errors will fail immediately without retry.

## Retry Behavior

When a retryable error occurs:

1. The agent checks if retries are remaining
2. Applies the configured delay (with exponential backoff if configured)
3. Logs the retry attempt with warning level
4. Retries the CLI command
5. If all retries are exhausted, the original error is raised

## Example Retry Flow

With `max_retries: 5` and `retry_delays: [3, 6, 12, 24, 48]`:

1. **Attempt 1** (initial): Fails with 429 error
2. **Wait 3 seconds**
3. **Attempt 2** (retry 1/5): Fails with 429 error
4. **Wait 6 seconds**
5. **Attempt 3** (retry 2/5): Fails with 429 error
6. **Wait 12 seconds**
7. **Attempt 4** (retry 3/5): Fails with 429 error
8. **Wait 24 seconds**
9. **Attempt 5** (retry 4/5): Fails with 429 error
10. **Wait 48 seconds**
11. **Attempt 6** (retry 5/5): Succeeds ✓

Total time: ~93 seconds of waiting plus execution time

## Logging

Retry attempts are logged at the WARNING level:

```
CLI 'gemini' attempt 2/6 failed with retryable error: Rate limit exceeded. Retrying in 6.0s...
```

## Best Practices

1. **Start conservative**: Use moderate retry counts (3-5) to avoid excessive wait times
2. **Exponential backoff**: Configure delays that increase exponentially (e.g., 3, 6, 12, 24, 48)
3. **Monitor logs**: Watch for frequent retries which may indicate quota issues
4. **Adjust per CLI**: Different CLI tools may have different rate limits - configure accordingly

## Disabling Retries

To disable retries completely, set `max_retries` to `0`:

```json
{
  "name": "gemini",
  "max_retries": 0,
  ...
}
```

This will cause immediate failure on any retryable error without attempting retries.
