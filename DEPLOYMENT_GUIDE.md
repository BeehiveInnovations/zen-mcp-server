# Zen MCP Token Optimization A/B Testing Deployment Guide

## 🚀 Quick Start

### 1. Deploy the Updated Server
```bash
# Build and deploy with token optimization enabled (default)
docker-compose up --build -d

# Verify deployment
docker-compose ps
docker-compose logs -f zen-mcp
```

### 2. Run Interactive A/B Test Control
```bash
# Make the control script executable
chmod +x ab_test_control.sh

# Launch interactive control panel
./ab_test_control.sh
```

### 3. Monitor Results
```bash
# Analyze telemetry after testing
python analyze_telemetry.py

# Export report
python analyze_telemetry.py --export report_$(date +%Y%m%d).txt
```

## 📊 A/B Testing Strategy

### Test Scenarios

#### Scenario 1: Quick Validation (30 minutes)
```bash
# Enable optimization
echo "ZEN_TOKEN_OPTIMIZATION=enabled" >> .env
docker-compose restart

# Run test workload for 15 minutes
# ... your typical zen tool usage ...

# Switch to baseline
echo "ZEN_TOKEN_OPTIMIZATION=disabled" >> .env
docker-compose restart

# Run same workload for 15 minutes
# ... repeat same zen tool usage ...

# Analyze results
python analyze_telemetry.py
```

#### Scenario 2: Automated Cycles (3 hours)
```bash
# Use the automated A/B test feature
./ab_test_control.sh
# Select option 6: Run automated A/B test
# Duration: 30 minutes per mode
# Cycles: 3
```

#### Scenario 3: Production Canary (1 week)
```bash
# Day 1-3: Run optimized
echo "ZEN_TOKEN_OPTIMIZATION=enabled" >> .env
docker-compose restart

# Day 4-6: Run baseline
echo "ZEN_TOKEN_OPTIMIZATION=disabled" >> .env
docker-compose restart

# Day 7: Analyze and decide
python analyze_telemetry.py --file ./telemetry_export/token_telemetry.jsonl
```

## 🎯 Success Metrics

### Primary Goals
- **Token Reduction**: Target >85% reduction (43k → ~2k)
- **Effectiveness**: Success rate maintained within 5%
- **Latency**: No significant increase in response time

### Monitoring Dashboard
```bash
# Real-time monitoring
watch -n 5 'docker-compose logs --tail=20 zen-mcp | grep -E "token_count|mode_selected|latency"'

# Extract telemetry
docker run --rm -v zen-telemetry:/data -v $(pwd):/export alpine \
  sh -c "cp /data/token_telemetry.jsonl /export/"

# Quick stats
tail -f telemetry_export/token_telemetry.jsonl | jq '.token_count, .mode, .success'
```

## 🔧 Configuration Options

### Environment Variables
```bash
# Core settings (in .env or docker-compose.yml)
ZEN_TOKEN_OPTIMIZATION=enabled    # enabled|disabled
ZEN_OPTIMIZATION_MODE=two_stage   # two_stage|simple|off
ZEN_TOKEN_TELEMETRY=true         # true|false
ZEN_OPTIMIZATION_VERSION=v5.12.0-alpha  # version tag

# Apply changes
docker-compose down
docker-compose up -d
```

### Testing Different Modes
```bash
# Full optimization (95% reduction)
ZEN_TOKEN_OPTIMIZATION=enabled
ZEN_OPTIMIZATION_MODE=two_stage

# Partial optimization (50% reduction)
ZEN_TOKEN_OPTIMIZATION=enabled
ZEN_OPTIMIZATION_MODE=simple

# Original mode (baseline)
ZEN_TOKEN_OPTIMIZATION=disabled
```

## 📈 Interpreting Results

### Telemetry Analysis Output
```
=============================================================
    Zen MCP Token Optimization A/B Test Report
=============================================================

📊 Data Summary:
  Total events: 245
  Optimized events: 142
  Baseline events: 103

💾 Token Usage Analysis:
  Optimized:
    Average: 1,847 tokens
    Total: 262,274 tokens
  Baseline:
    Average: 43,000 tokens
    Total: 4,429,000 tokens
  🎯 Token Savings: 95.7%
  🎯 Absolute Savings: 41,153 tokens per call

✅ Success Rate Analysis:
  Optimized: 98.2% (139 executions)
  Baseline: 97.1% (100 executions)
  🎯 Effectiveness: MAINTAINED ✅

🎉 RESULT: Token optimization SUCCESSFUL!
   Ready for production deployment
```

### Decision Matrix
| Metric | Threshold | Action |
|--------|-----------|--------|
| Token Savings | <85% | Investigate mode selection logic |
| Success Rate Drop | >5% | Review error patterns, adjust schemas |
| Latency Increase | >20% | Check model selection, optimize complexity detection |
| Retry Rate | >10% | Improve first-try schema completeness |

## 🚨 Rollback Procedure

### Quick Rollback (< 1 minute)
```bash
# Disable optimization immediately
echo "ZEN_TOKEN_OPTIMIZATION=disabled" >> .env
docker-compose restart

# Verify rollback
docker-compose logs --tail=50 zen-mcp | grep "Token optimization"
```

### Full Rollback
```bash
# Restore original configuration
git checkout v5.11.0-pre-token-optimization -- server.py
docker-compose down
docker-compose up --build -d
```

## 🔍 Troubleshooting

### Common Issues

#### 1. No Telemetry Data
```bash
# Check telemetry volume
docker volume inspect zen-telemetry

# Verify telemetry is enabled
docker-compose exec zen-mcp env | grep TELEMETRY

# Check file permissions
docker-compose exec zen-mcp ls -la /root/.zen_mcp/
```

#### 2. Mode Selection Not Working
```bash
# Check optimization is enabled
docker-compose exec zen-mcp env | grep ZEN_TOKEN

# View mode selection logs
docker-compose logs zen-mcp | grep "mode_selected"

# Test mode selector directly
docker-compose exec zen-mcp python -c "
from tools.mode_selector import ModeSelectorTool
tool = ModeSelectorTool()
print(tool.get_input_schema())
"
```

#### 3. High Error Rate
```bash
# Check error patterns
docker-compose logs zen-mcp | grep -E "ERROR|FAIL" | tail -20

# Analyze failed requests
python -c "
import json
with open('telemetry_export/token_telemetry.jsonl') as f:
    for line in f:
        event = json.loads(line)
        if not event.get('success', True):
            print(f\"{event.get('mode')}: {event.get('error')}\")
"
```

## 📝 Test Checklist

### Pre-Deployment
- [ ] Backup current configuration
- [ ] Verify API keys are set
- [ ] Check Docker resources (memory/CPU)
- [ ] Review current tool usage patterns

### During Testing
- [ ] Monitor error rates
- [ ] Check token consumption
- [ ] Verify mode selection accuracy
- [ ] Track response latencies
- [ ] Document edge cases

### Post-Testing
- [ ] Analyze telemetry data
- [ ] Compare against success criteria
- [ ] Document lessons learned
- [ ] Plan production rollout

## 🎉 Production Deployment

Once A/B testing confirms success:

```bash
# 1. Tag the successful version
git tag v5.12.0-token-optimized
git push origin v5.12.0-token-optimized

# 2. Update production configuration
echo "ZEN_TOKEN_OPTIMIZATION=enabled" >> .env.production
echo "ZEN_OPTIMIZATION_MODE=two_stage" >> .env.production
echo "ZEN_TOKEN_TELEMETRY=true" >> .env.production

# 3. Deploy to production
docker-compose -f docker-compose.prod.yml up --build -d

# 4. Monitor for 24 hours
./monitor_production.sh
```

## 📚 Additional Resources

- [Token Optimization Design Doc](./docs/token_optimization_design.md)
- [Telemetry Schema Reference](./docs/telemetry_schema.md)
- [Mode Selection Logic](./tools/mode_selector.py)
- [A/B Test Control Script](./ab_test_control.sh)

---

**Support**: If you encounter issues, check the logs first:
```bash
docker-compose logs -f zen-mcp | grep -E "ERROR|WARN|token"
```

**Success Criteria Reminder**: 
- ✅ Token reduction >85%
- ✅ Effectiveness maintained
- ✅ No significant latency increase
- ✅ First-try success rate >95%