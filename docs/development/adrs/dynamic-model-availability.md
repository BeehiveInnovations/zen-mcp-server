# Dynamic Model Availability and Failover - Architecture Decision Record (ADR)

**Status**: ✅ REQUIRED - Critical Pattern for Free Tier Models
**Date**: 2025-11-09
**System**: Model Availability and Failover
**Related**: centralized-model-registry.md

---

## Context

### The Problem: Free Models Have Dynamic Availability

**CRITICAL DISTINCTION:**
- **Free models**: Transient availability (need failover)
- **Paid models**: Permanent availability (failures indicate removal needed)

Free-tier AI models are not permanently available or unavailable. Instead, they have **transient availability** based on several factors:

#### Availability Factors

1. **Privacy Settings**
   - Some free models restricted by data privacy policies
   - Varies by request content, user location, organization type
   - Can change dynamically based on policy updates

2. **Provider Requirements**
   - Providers may limit free tier access based on:
     - Time of day (peak hours vs off-peak)
     - Geographic region
     - API rate limits
     - Fair use policies
     - Model capacity/demand

3. **Transient Outages**
   - Model endpoints may return 404, 503, 429 errors
   - Not permanent failures - may work 5 minutes later
   - Infrastructure maintenance, capacity constraints, routing issues

4. **Policy Changes**
   - OpenRouter policy restricts certain models
   - Provider agreements change
   - Compliance requirements shift

**Real-World Example:**
```
Monday 9 AM EST:
  deepseek/deepseek-chat:free → 200 OK ✅

Monday 2 PM EST:
  deepseek/deepseek-chat:free → 429 Rate Limited ❌

Monday 8 PM EST:
  deepseek/deepseek-chat:free → 200 OK ✅

Tuesday 9 AM EST:
  deepseek/deepseek-chat:free → 404 Not Found (policy change) ❌
```

### Why This Matters

**Wrong Approach:** Mark model as "deprecated" when it returns 404
- Model may be available again later
- Loses cost savings when it's working
- Requires manual re-enablement

**Right Approach:** Automatic failover with retry logic
- Try free model 1
- If unavailable → Try free model 2
- If unavailable → Try free model 3
- If all free unavailable → Fallback to economy tier
- Next request tries free tier again

---

## Decision

**Implement multi-tier failover with graceful degradation for model availability.**

### Core Principle

> **Never Fail, Degrade Gracefully**: When preferred models are unavailable, automatically fall back to next-best alternatives within cost/quality constraints.

---

## Architecture

### 1. Failover Hierarchy

**Tier Structure (Additive):**
```
Priority 1: Free Tier (Cost = $0)
├── free_model_1 (deepseek/deepseek-chat:free)
├── free_model_2 (meta-llama/llama-3.3-70b-instruct:free)
├── free_model_3 (qwen/qwen-2.5-coder-32b-instruct:free)
├── free_model_4 (microsoft/phi-4-reasoning:free)
└── free_model_5 (meta-llama/llama-3.1-405b-instruct:free)

Priority 2: Economy Tier (Cost = $0.01-1.00 per million)
├── economy_model_1 (google/gemini-2.5-flash: $0.075-0.30)
├── economy_model_2 (openai/o4-mini: $0.15-0.60)
└── economy_model_3 (qwen/qwen3-coder: $0.20-0.80)

Priority 3: Value Tier (Cost = $1.01-10.00 per million)
├── value_model_1 (openai/gpt-5-nano: $0.10-0.40)
├── value_model_2 (microsoft/phi-4: $0.50-1.50)
└── value_model_3 (mistralai/mistral-large-2411: $2.00-6.00)
```

**Failover Logic:**
```python
def get_available_model(role: str, org_level: str) -> str:
    """
    Get first available model with automatic failover.

    Returns:
        Model name that successfully responds to health check
    """
    # Try free tier first (5 attempts)
    free_models = selector.get_models_by_cost_tier("free", limit=5)
    for model in free_models:
        if is_available(model):
            return model

    # Fallback to economy tier (3 attempts)
    economy_models = selector.get_models_by_cost_tier("economy", limit=3)
    for model in economy_models:
        if is_available(model):
            return model

    # Fallback to value tier (guaranteed availability)
    value_models = selector.get_models_by_cost_tier("value", limit=3)
    for model in value_models:
        if is_available(model):
            return model

    raise ModelUnavailableError("No models available across all tiers")
```

### 2. Availability Detection

**Health Check Strategy:**

```python
def is_available(model: str, timeout: int = 5) -> bool:
    """
    Quick health check for model availability.

    Args:
        model: Model identifier
        timeout: Max seconds to wait for response

    Returns:
        True if model responds successfully
    """
    try:
        # Lightweight test request
        response = call_model(
            model=model,
            prompt="test",  # Minimal prompt
            max_tokens=1,
            timeout=timeout
        )
        return response.status_code == 200

    except (HTTPError, Timeout, ConnectionError) as e:
        # Common transient failures
        if e.status_code in [404, 429, 503]:
            logger.warning(f"Model {model} temporarily unavailable: {e}")
            return False
        raise  # Unexpected error - re-raise
```

**Error Classifications:**

| Error Code | Meaning | Free Model Action | Paid Model Action |
|------------|---------|-------------------|-------------------|
| 404 Not Found | Model endpoint doesn't exist | Try next free model | **Mark as deprecated** |
| 429 Rate Limited | Too many requests | Try next free model | **Mark as deprecated** (shouldn't happen for paid) |
| 503 Service Unavailable | Temporary capacity issue | Try next free model | Retry same model |
| 401 Unauthorized | API key issue | Fail (don't failover) | Fail (don't failover) |
| 500 Internal Server Error | Provider issue | Try next free model | Retry same model (temp issue) |

**Key Insight:** Paid models should have 99.9%+ uptime. If a paid model consistently fails, it's a real problem requiring removal from the registry.

### 3. Caching and Retry Logic

**Availability Cache:**
```python
class AvailabilityCache:
    """
    Cache model availability to avoid repeated health checks.
    """
    def __init__(self, ttl: int = 300):  # 5 minute TTL
        self.cache = {}
        self.ttl = ttl

    def is_available(self, model: str) -> Optional[bool]:
        """Check cache for recent availability status."""
        if model in self.cache:
            timestamp, status = self.cache[model]
            if time.time() - timestamp < self.ttl:
                return status
        return None

    def set_available(self, model: str, available: bool):
        """Cache availability status."""
        self.cache[model] = (time.time(), available)
```

**Retry Strategy:**
```python
def call_model_with_retry(
    model: str,
    prompt: str,
    max_retries: int = 2,
    backoff: float = 1.0
) -> Response:
    """
    Call model with exponential backoff retry.

    Args:
        model: Model to call
        prompt: User prompt
        max_retries: Number of retry attempts
        backoff: Initial backoff delay in seconds

    Returns:
        Model response
    """
    for attempt in range(max_retries + 1):
        try:
            return call_model(model, prompt)
        except TransientError as e:
            if attempt < max_retries:
                delay = backoff * (2 ** attempt)  # Exponential backoff
                logger.info(f"Retry {attempt+1}/{max_retries} after {delay}s")
                time.sleep(delay)
            else:
                raise  # Max retries exceeded
```

### 4. Cost Tracking

**Track Failover Costs:**
```python
class FailoverMetrics:
    """Track failover statistics and cost impact."""

    def __init__(self):
        self.attempts = defaultdict(int)  # model → attempt count
        self.successes = defaultdict(int)  # model → success count
        self.failovers = defaultdict(int)  # tier → failover count
        self.cost_delta = 0.0  # Additional cost from failovers

    def record_attempt(self, model: str, tier: str, success: bool, cost: float):
        """Record a model attempt."""
        self.attempts[model] += 1
        if success:
            self.successes[model] += 1
        else:
            self.failovers[tier] += 1
            # Calculate cost delta if we failed over to higher tier
            if tier == "free" and cost > 0:
                self.cost_delta += cost

    def get_report(self) -> dict:
        """Generate failover report."""
        return {
            "total_attempts": sum(self.attempts.values()),
            "free_tier_failures": self.failovers["free"],
            "economy_tier_failures": self.failovers["economy"],
            "additional_cost": self.cost_delta,
            "model_success_rates": {
                model: self.successes[model] / self.attempts[model]
                for model in self.attempts
            }
        }
```

---

## Implementation

### Enhanced BandSelector with Failover

```python
class BandSelector:
    """Enhanced with availability-aware failover."""

    def __init__(self):
        self.availability_cache = AvailabilityCache(ttl=300)
        self.metrics = FailoverMetrics()

    def get_available_models_with_failover(
        self,
        tier: int,
        role: str,
        max_attempts: int = 10
    ) -> List[str]:
        """
        Get models for tier with automatic failover.

        Args:
            tier: Tier level (1=startup, 2=scaleup, 3=enterprise)
            role: Professional role
            max_attempts: Maximum models to try before giving up

        Returns:
            List of available models ordered by preference
        """
        candidates = []

        # Tier 1: Try free models first (MULTIPLE attempts - transient availability)
        if tier >= 1:
            free_models = self.get_models_by_cost_tier("free", limit=5)
            candidates.extend([(m, "free", 0.0, True) for m in free_models])
            # True = allow_failover within tier

        # Tier 2: Add economy models as fallback (SINGLE attempt - should be stable)
        if tier >= 2:
            economy_models = self.get_models_by_cost_tier("economy", limit=3)
            avg_cost = 0.5  # Rough average: $0.50 per million
            candidates.extend([(m, "economy", avg_cost, False) for m in economy_models])
            # False = no failover within tier (if economy fails, it's broken)

        # Tier 3: Add value models as final fallback (SINGLE attempt - should be stable)
        if tier >= 3:
            value_models = self.get_models_by_cost_tier("value", limit=3)
            avg_cost = 2.0  # Rough average: $2.00 per million
            candidates.extend([(m, "value", avg_cost, False) for m in value_models])
            # False = no failover within tier

        # Filter by role specialization if specified
        if role:
            candidates = self._filter_by_role(candidates, role)

        # Try candidates in order until one is available
        available = []
        for model, tier_name, cost, allow_tier_failover in candidates[:max_attempts]:
            # Check cache first
            cached_status = self.availability_cache.is_available(model)
            if cached_status is False:
                continue  # Skip known unavailable models

            # Health check
            is_avail = self._check_availability(model)
            self.availability_cache.set_available(model, is_avail)
            self.metrics.record_attempt(model, tier_name, is_avail, cost)

            if is_avail:
                available.append(model)

        return available

    def _check_availability(self, model: str) -> bool:
        """
        Check if model is currently available.

        Uses lightweight test request.

        Note: For paid models, failures indicate a permanent issue
              (not transient). Caller should mark as deprecated.
        """
        try:
            # Call model with minimal prompt
            response = call_model(
                model=model,
                prompt="test",
                max_tokens=1,
                timeout=5
            )
            return response.status_code == 200
        except HTTPError as e:
            # Check if this is a paid model
            is_paid = self._is_paid_model(model)

            if is_paid and e.status_code in [404, 429]:
                # Paid models shouldn't fail with these codes
                logger.error(
                    f"CRITICAL: Paid model {model} returned {e.status_code}. "
                    f"This indicates the model should be removed from registry."
                )
                # Alert for manual intervention
                self._alert_paid_model_failure(model, e.status_code)

            logger.debug(f"Model {model} unavailable: {e}")
            return False
        except Exception as e:
            logger.debug(f"Model {model} unavailable: {e}")
            return False

    def _is_paid_model(self, model: str) -> bool:
        """Check if model is in paid tier (not free)."""
        model_data = self.models_df[self.models_df['model'] == model]
        if model_data.empty:
            return False
        return model_data.iloc[0]['status'] != 'free'

    def _alert_paid_model_failure(self, model: str, error_code: int):
        """Alert about paid model failure requiring manual intervention."""
        alert_message = {
            "severity": "CRITICAL",
            "model": model,
            "error_code": error_code,
            "action_required": "Update models.csv status to 'deprecated'",
            "timestamp": time.time()
        }
        # Log to dedicated alert channel
        logger.critical(f"Paid model failure alert: {alert_message}")
        # Could also send to monitoring service, Slack, etc.
```

### Consensus Tool Integration

```python
class SmartConsensusTool(WorkflowTool):
    """Enhanced with failover support."""

    def __init__(self):
        super().__init__()
        self.band_selector = BandSelector()

    async def _create_role_assignments(self, request):
        """Create role assignments with failover."""
        tier = self._get_tier_from_org_level(request.org_level)
        roles = self._get_roles_for_tier(tier)

        # Get available models with automatic failover
        available_models = self.band_selector.get_available_models_with_failover(
            tier=tier,
            role=None,  # Get all models, assign to roles after
            max_attempts=15  # Try up to 15 models
        )

        if len(available_models) < len(roles):
            logger.warning(
                f"Only {len(available_models)} models available for {len(roles)} roles. "
                f"Some roles will share models."
            )

        # Assign models to roles (round-robin if needed)
        role_assignments = {}
        for i, role in enumerate(roles):
            model = available_models[i % len(available_models)]
            role_assignments[role] = model

        return role_assignments
```

---

## Consequences

### Benefits

#### 1. **Resilience to Free Model Volatility**

**Scenario:** deepseek/deepseek-chat:free returns 404

**Old Behavior:**
```
1. Call fails with 404
2. Tool execution fails
3. User sees error
4. Developer manually updates code
5. Deploy fix
```

**New Behavior:**
```
1. Call fails with 404
2. Automatic failover to llama-3.3-70b:free
3. Tool execution continues
4. User unaware of issue
5. Zero cost maintained (still free tier)
```

#### 2. **Cost Optimization with Graceful Fallback**

**Ideal Case (90% of time):**
```
Try: free_model_1 → Success → Cost: $0 ✅
```

**Degraded Case (8% of time):**
```
Try: free_model_1 → 404
Try: free_model_2 → Success → Cost: $0 ✅
```

**Fallback Case (2% of time):**
```
Try: free_model_1 → 404
Try: free_model_2 → 404
Try: free_model_3 → 404
Try: economy_model_1 → Success → Cost: $0.50 ⚠️
```

**Average Cost:** $0.01 per million tokens (vs $0 ideal, vs $0.50 fallback-only)

#### 3. **Transparency and Monitoring**

**Failover Report:**
```json
{
  "total_attempts": 1000,
  "free_tier_failures": 120,
  "economy_tier_failures": 5,
  "additional_cost": 62.50,
  "model_success_rates": {
    "deepseek/deepseek-chat:free": 0.65,
    "meta-llama/llama-3.3-70b-instruct:free": 0.88,
    "qwen/qwen-2.5-coder-32b-instruct:free": 0.92,
    "google/gemini-2.5-flash": 0.98
  }
}
```

**Insights:**
- deepseek has 65% availability → Consider removing
- qwen has 92% availability → Promote to first choice
- Economy tier rarely needed (0.5% of time)
- Additional cost minimal ($62.50 for 1000 requests)

#### 4. **Dynamic Adaptation**

**BandSelector learns from availability:**
```python
# Re-order models.csv based on success rates
def optimize_model_order():
    """Update model rankings based on availability."""
    metrics = band_selector.metrics.get_report()

    for model, success_rate in metrics["model_success_rates"].items():
        if success_rate < 0.7:
            # Lower rank for unreliable models
            update_model_rank(model, rank_delta=-5)
        elif success_rate > 0.95:
            # Boost rank for highly available models
            update_model_rank(model, rank_delta=+3)
```

### Challenges

#### 1. **Latency Impact**

**Issue:** Health checks add latency

**Mitigation:**
- **Aggressive caching** (5-minute TTL)
- **Parallel health checks** when possible
- **Background availability monitoring** (proactive cache warming)
- **Fast timeouts** (5 seconds max per check)

**Typical Latency:**
```
Best case (cached): +0ms
Health check (uncached): +100-500ms
Failover (1 model): +100-500ms
Failover (3 models): +300-1500ms
```

#### 2. **Cost Uncertainty**

**Issue:** Can't guarantee $0 cost with free tier fallback

**Mitigation:**
- **Set cost budgets** per request
- **Alert on excessive failovers**
- **Provide cost estimates** before execution
- **User configuration** (strict free-only mode vs cost-optimized mode)

```python
# User can enforce strict free-tier mode
config = {
    "allow_paid_fallback": False,  # Fail rather than use paid models
    "max_cost_per_request": 0.0
}
```

#### 3. **Complexity**

**Issue:** More complex than static model selection

**Mitigation:**
- **Encapsulate in BandSelector** (tools don't see complexity)
- **Comprehensive logging** for debugging
- **Metrics dashboard** for monitoring
- **Clear error messages** when all tiers fail

---

## Configuration

### User Controls

**Per-Request Configuration:**
```python
smart_consensus_v2(
    question="Should we use TypeScript?",
    org_level="startup",
    failover_config={
        "allow_paid_fallback": True,      # Allow fallback to economy tier
        "max_cost_per_request": 0.50,     # Budget constraint
        "retry_attempts": 2,               # Retries per model
        "prefer_reliability": False        # If True, favor high-success-rate models
    }
)
```

**Global Configuration (bands_config.json):**
```json
{
  "failover_policy": {
    "default_allow_paid_fallback": true,
    "default_max_cost": 1.0,
    "cache_ttl_seconds": 300,
    "health_check_timeout_seconds": 5,
    "max_failover_attempts": 10,
    "alert_threshold_failover_rate": 0.15
  }
}
```

---

## Monitoring and Alerting

### Key Metrics

1. **Failover Rate**: % of requests requiring fallback
2. **Tier Distribution**: % free vs economy vs value
3. **Cost Impact**: Additional cost from failovers
4. **Model Availability**: Success rate per model
5. **Latency Impact**: Average delay from health checks

### Alerts

**High Failover Rate:**
```
Alert: Free tier failover rate > 15%
Action: Investigate provider issues or update model pool
```

**Excessive Costs:**
```
Alert: Failover costs > $10/day
Action: Review model availability or adjust retry logic
```

**Model Degradation:**
```
Alert: Model X availability < 70%
Action: De-prioritize model or remove from pool
```

---

## Examples

### Example 1: Successful Free Tier Request

```python
# User request
smart_consensus_v2(question="Review this code", org_level="startup")

# Execution flow
[1] Try: deepseek/deepseek-chat:free
    → Check cache: No recent status
    → Health check: HTTP 200 ✅
    → Use model: deepseek/deepseek-chat:free
    → Cost: $0.00
    → Duration: 2.3s (includes 0.1s health check)
```

### Example 2: Single Failover

```python
# User request
smart_consensus_v2(question="Review this code", org_level="startup")

# Execution flow
[1] Try: deepseek/deepseek-chat:free
    → Check cache: No recent status
    → Health check: HTTP 404 ❌
    → Cache status: unavailable (5 min TTL)

[2] Try: meta-llama/llama-3.3-70b-instruct:free
    → Check cache: No recent status
    → Health check: HTTP 200 ✅
    → Use model: meta-llama/llama-3.3-70b-instruct:free
    → Cost: $0.00
    → Duration: 2.5s (includes 0.2s failover)
```

### Example 3: Tier Fallback (All Free Models Unavailable)

```python
# User request
smart_consensus_v2(question="Review this code", org_level="startup")

# Execution flow
[1-5] Try all 5 free models: All return 404 or 429 ❌

[6] Try: google/gemini-2.5-flash (economy tier)
    → Health check: HTTP 200 ✅
    → Use model: google/gemini-2.5-flash
    → Cost: $0.40 (input $0.075 + output $0.30 per M tokens)
    → Duration: 3.1s (includes 0.6s failover)
    → Log: WARNING - Fallback to economy tier, cost incurred

# Metrics updated
failover_metrics.record_failover(
    from_tier="free",
    to_tier="economy",
    cost_delta=0.40
)
```

### Example 4: Cost Budget Enforcement

```python
# User request with strict budget
smart_consensus_v2(
    question="Review this code",
    org_level="startup",
    failover_config={
        "allow_paid_fallback": False,  # Strict free-only
        "max_cost_per_request": 0.0
    }
)

# Execution flow
[1-5] Try all 5 free models: All unavailable ❌

[6] Check failover_config
    → allow_paid_fallback: False
    → Cannot proceed to economy tier

[7] Raise exception: NoFreeModelsAvailableError
    → Error message: "No free tier models currently available. "
                     "Enable paid fallback or try again later."
    → Suggested action: "Set allow_paid_fallback=True to use economy tier"
```

---

## Migration Plan

### Phase 1: Add Availability Checking (Week 1)

**Actions:**
1. Implement `AvailabilityCache` class
2. Implement `_check_availability()` method in BandSelector
3. Add health check before model calls
4. Log availability results

**Testing:**
```python
# Test availability detection
selector = BandSelector()
is_avail = selector._check_availability("deepseek/deepseek-chat:free")
assert is_avail in [True, False]  # Boolean result
```

### Phase 2: Implement Failover Logic (Week 2)

**Actions:**
1. Implement `get_available_models_with_failover()` method
2. Update consensus tools to use failover
3. Add failover metrics collection
4. Implement cost tracking

**Testing:**
```python
# Test failover
models = selector.get_available_models_with_failover(tier=1, role="code_reviewer")
assert len(models) > 0  # At least one model available
assert models[0].endswith(":free") or cost_acceptable  # Prefer free
```

### Phase 3: Add Retry Logic (Week 3)

**Actions:**
1. Implement exponential backoff retry
2. Add transient error detection
3. Configure retry parameters
4. Test retry scenarios

### Phase 4: Monitoring and Alerting (Week 4)

**Actions:**
1. Implement `FailoverMetrics` class
2. Create metrics dashboard
3. Configure alerts
4. Document user-facing failover behavior

---

## Related Decisions

### Relationship to Centralized Model Registry ADR

**This ADR extends centralized-model-registry.md with:**
- Dynamic availability handling
- Failover strategies
- Cost tracking for failovers
- User configuration options

**Key Difference:**
- **Model Registry**: Which models exist and their static properties
- **This ADR**: How to handle when models are temporarily unavailable

---

## References

### Code Files

- **BandSelector**: `tools/custom/band_selector.py`
- **Consensus Tools**: `tools/custom/smart_consensus_v2.py`, `layered_consensus.py`
- **Models Registry**: `docs/models/models.csv`
- **Band Config**: `docs/models/bands_config.json`

### Error Codes

- **404**: Model endpoint not found (temporary or permanent)
- **429**: Rate limit exceeded (temporary)
- **503**: Service unavailable (temporary)
- **500**: Internal server error (temporary)

---

## Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2025-11-09 | 1.0 | Byron W. + Claude Code | Initial documentation of dynamic availability pattern |

---

## Status Summary

**✅ Pattern: CRITICAL** - Essential for free tier reliability

**📋 Implementation: REQUIRED** - Must implement failover in consensus tools

**🎯 Goal:** Automatic failover with cost optimization and graceful degradation

---

*This ADR documents the dynamic model availability pattern that enables reliable free-tier usage with automatic failover to paid tiers when necessary. Free models are not "broken" - they have transient availability that requires sophisticated failover handling.*
