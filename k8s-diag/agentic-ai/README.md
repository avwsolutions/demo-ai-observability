# Agentic AI - Autonomous Kubernetes Self-Healing

Autonomous monitoring system that continuously observes Kubernetes pods, plans remediation strategies, executes fixes, and learns from successful patterns.

---

## Overview

This is **Part 2** of the Kubernetes AI Diagnostics project, demonstrating **Agentic AI** - an autonomous system that operates continuously without human intervention.

### Key Differences from Agent AI (Part 1)

| Aspect | Agent AI (Part 1) | Agentic AI (Part 2) |
|--------|-------------------|---------------------|
| Execution | On-demand (user-initiated) | Continuous autonomous loop |
| Decision Making | Provides recommendations | Plans and executes independently |
| Human Involvement | Required for each action | Optional monitoring only |
| Memory | Stateless | Learns from past successes |
| Planning | Single-step | Multi-step reasoning |
| Improvement | Static | Gets smarter over time |

---

## Quick Start

### Prerequisites

- Python 3.8+
- Kubernetes cluster with `kubectl` configured
- OpenAI API key

### Installation

```bash
# Navigate to agentic-ai directory
cd agentic-ai

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set API key
export OPENAI_API_KEY='your-openai-api-key'
```

### Deploy Test Scenarios

```bash
cd test-scenarios
./deploy-scenarios.sh
cd ..
```

This creates three broken deployments that demonstrate autonomous learning:

1. **mysql-client** - CrashLoopBackOff (missing environment variables)
2. **memory-hungry** - OOMKilled (insufficient memory)
3. **web-server & alpine-app** - ImagePullBackOff (image name typos)

### Run Autonomous Monitor

```bash
# Start with fresh memory
python3 agentic_monitor.py --namespace agentic-demo --interval 30 --fresh

# Or continue from previous learning
python3 agentic_monitor.py --namespace agentic-demo --interval 30
```

### Verify Autonomous Healing

In a separate terminal, watch pods healing in real-time:

```bash
watch -n 5 kubectl get pods -n agentic-demo
```

Or on macOS without `watch`:

```bash
while true; do clear; date; kubectl get pods -n agentic-demo; sleep 5; done
```

You should see pods transition from failing states to Running automatically.

---

## How It Works

### The Autonomous Loop

```
┌──────────┐
│ OBSERVE  │  Continuously scan namespace for unhealthy pods
└────┬─────┘
     │
     v
┌──────────┐
│  PLAN    │  Analyze issue and create remediation strategy
└────┬─────┘  - Check memory for learned solutions
     │         - Detect patterns (typos, missing env vars)
     │         - Consult GPT-4 for complex issues
     v
┌──────────┐
│   ACT    │  Execute remediation actions autonomously
└────┬─────┘  - Fix image names
     │         - Add environment variables
     │         - Increase memory limits
     v         - Restart pods
┌──────────┐
│  LEARN   │  Store successful patterns in memory
└────┬─────┘
     │
     └──> (Loop continues every N seconds)
```

### Pattern Detection

The system includes built-in pattern detection that doesn't require AI:

**1. Image Typo Detection**

Common typos automatically detected and fixed:
- `apline` → `alpine`
- `latst` → `latest`
- `lastest` → `latest`
- `ngnix` → `nginx`
- `ubunut` → `ubuntu`

**2. Missing Environment Variables**

Analyzes pod logs for patterns like:
```
MYSQL_HOST is: 
MYSQL_ROOT_PASSWORD is: 
ERROR: Missing required environment variables!
```

Automatically adds missing variables with sensible defaults:
- `*_HOST` → `localhost`
- `*_PASSWORD` → `password123`
- `*_PORT` → `3306`

**3. OOMKilled Progressive Learning**

First incident:
- Tries increasing memory incrementally
- Stores successful memory limit

Subsequent incidents:
- Applies learned optimal memory immediately
- No trial and error needed

---

## Command Line Options

### Basic Usage

```bash
python3 agentic_monitor.py [options]
```

### Options

| Flag | Description | Default |
|------|-------------|---------|
| `--namespace`, `-n` | Kubernetes namespace to monitor | `agentic-demo` |
| `--interval`, `-i` | Check interval in seconds | `30` |
| `--fresh`, `-f` | Start with fresh memory (delete learning history) | `False` |
| `--no-auto` | Observe only (no auto-remediation) | `False` |

### Examples

```bash
# Standard autonomous mode with 30-second checks
python3 agentic_monitor.py --namespace agentic-demo --interval 30

# Start fresh (no learning from previous runs)
python3 agentic_monitor.py --fresh

# Observe-only mode (see what would be fixed without executing)
python3 agentic_monitor.py --no-auto

# Monitor different namespace with 60-second interval
python3 agentic_monitor.py --namespace production --interval 60

# Combine options
python3 agentic_monitor.py -n my-namespace -i 45 -f
```

---

## Test Scenarios Explained

### Scenario 1: CrashLoopBackOff - Missing Environment Variables

**File:** `scenario-1-crashloop-missing-env.yaml`

**Issue:**
- mysql-client pod crashes immediately on startup
- Missing required environment variables: `MYSQL_HOST` and `MYSQL_ROOT_PASSWORD`

**Autonomous Detection:**
```
[OBSERVE] Found CrashLoopBackOff
[PLAN] Analyzed logs, detected pattern:
  MYSQL_HOST is: 
  MYSQL_ROOT_PASSWORD is: 
  ERROR: Missing required environment variables!
[ACT] Updated deployment with:
  MYSQL_HOST=localhost
  MYSQL_ROOT_PASSWORD=password123
[LEARN] Stored: CrashLoopBackOff + missing env vars → update_env
```

**Expected Outcome:** Pod becomes Running in 1-2 iterations

### Scenario 2: OOMKilled - Progressive Memory Increase

**File:** `scenario-2-oom-progressive.yaml`

**Issue:**
- Python script allocates 500MB of memory
- Initial limit: 128Mi (too low)

**Autonomous Detection:**
```
[OBSERVE] Found Terminated state with OOMKilled reason
[PLAN] Progressive increase strategy:
  Step 1: Try 256Mi
  Step 2: If fails, try 512Mi
  Step 3: If fails, try 1Gi
[ACT] Increased memory to 512Mi
[LEARN] Stored: memory-hungry app needs 512Mi
```

**Learning Benefit:** Next time same app deployed, directly sets 512Mi

**Expected Outcome:** Pod becomes Running after memory increase

### Scenario 3: ImagePullBackOff - Image Name Typos

**File:** `scenario-3-image-typo.yaml`

**Issues:**
- web-server: `nginx:latst` (should be `nginx:latest`)
- alpine-app: `apline:3.18` (should be `alpine:3.18`)

**Autonomous Detection:**
```
[OBSERVE] Found ImagePullBackOff
[PLAN] Pattern matching against common typos:
  Detected: "latst" → "latest"
  Detected: "apline" → "alpine"
[ACT] Updated deployment images:
  nginx:latst → nginx:latest
  apline:3.18 → alpine:3.18
[LEARN] Stored: ImagePullBackOff + typo pattern → fix_image_name
```

**Expected Outcome:** Both pods become Running in 1 iteration

---

## Output Format

### Clean, Structured Output

```
======================================================================
ITERATION #1 - 2025-10-16 10:30:37
======================================================================

[OBSERVE] Checking pod status...
Result: Found 3 issue(s)

----------------------------------------------------------------------
ISSUE #1 of 3
----------------------------------------------------------------------
Pod name:    mysql-client-759c547784-abc123
Status:      Waiting
Reason:      CrashLoopBackOff

[PLAN] Creating remediation plan...
Detection: Missing environment variables
  MYSQL_HOST = localhost
  MYSQL_ROOT_PASSWORD = password123

Remediation plan (1 step(s)):

  Step 1: UPDATE_ENV
  Reasoning: Pod logs indicate missing environment variables

[ACT] Executing remediation plan...

  Executing step 1/1: UPDATE_ENV
   SUCCESS: Updated deployment mysql-client
   Added environment variables: MYSQL_HOST, MYSQL_ROOT_PASSWORD

[LEARN] Storing results in memory...
Stored: update_env attempt (success=True)

======================================================================
Waiting 30 seconds until next check...
======================================================================
```

### Session Summary

When stopped (Ctrl+C):

```
======================================================================
SESSION SUMMARY
======================================================================
Total remediation attempts:  12
Successful attempts:         11
Success rate:                91.7%
Patterns learned:            3
======================================================================
```

---

## Memory and Learning

### Memory Storage

Learning data stored in `agentic_memory.json`:

```json
{
  "attempts": [
    {
      "issue": {
        "pod_name": "mysql-client-abc123",
        "status": "Waiting",
        "reason": "CrashLoopBackOff"
      },
      "action": "update_env",
      "success": true,
      "timestamp": "2025-10-16T10:30:45"
    }
  ],
  "patterns": {
    "Waiting_CrashLoopBackOff": {
      "successful_actions": [...],
      "success_count": 5,
      "total_count": 5
    }
  }
}
```

### Learning Behavior

**First Encounter:**
1. System detects new issue type
2. Uses pattern detection or consults GPT-4
3. Attempts remediation
4. Stores result if successful

**Subsequent Encounters:**
1. System detects similar issue
2. Recalls successful pattern from memory
3. Applies learned solution immediately
4. Skips GPT-4 consultation (faster, cheaper)

**Example:**

```
Iteration 1 (First OOMKilled):
  Time: 45 seconds
  API calls: 1
  Attempts: 2 (256Mi failed, 512Mi succeeded)

Iteration 50 (Similar OOMKilled):
  Time: 10 seconds
  API calls: 0
  Attempts: 1 (directly applied 512Mi)
```

### Managing Memory

```bash
# Start fresh (delete learning)
python3 agentic_monitor.py --fresh

# View current memory
cat agentic_memory.json

# Manual memory management
rm agentic_memory.json  # Complete reset
```

---

## Cleanup

### Remove Test Scenarios

```bash
cd test-scenarios
./cleanup-scenarios.sh
```

This deletes the `agentic-demo` namespace and all test deployments.

### Deactivate Virtual Environment

```bash
deactivate
```

---

## Architecture Details

### File Structure

```
agentic-ai/
├── agentic_monitor.py       # Main autonomous loop
├── planner.py               # Remediation planning logic
├── memory.py                # Learning and pattern storage
├── requirements.txt         # Python dependencies
├── agentic_memory.json      # Persistent learning data
└── test-scenarios/
    ├── deploy-scenarios.sh
    ├── cleanup-scenarios.sh
    ├── scenario-1-crashloop-missing-env.yaml
    ├── scenario-2-oom-progressive.yaml
    └── scenario-3-image-typo.yaml
```

### Core Components

**agentic_monitor.py:**
- Orchestrates the OBSERVE → PLAN → ACT → LEARN loop
- Manages Kubernetes API interactions
- Executes remediation actions

**planner.py:**
- Pattern detection (typos, missing env vars)
- Memory consultation for learned solutions
- GPT-4 integration for complex issues
- Multi-step plan creation

**memory.py:**
- Persistent storage of remediation attempts
- Pattern matching for similar issues
- Success rate tracking
- Learning optimization

---

## Troubleshooting

### Monitor Won't Start

```bash
# Check OpenAI API key
echo $OPENAI_API_KEY

# Verify namespace exists
kubectl get namespace agentic-demo

# Check Python dependencies
pip list | grep openai
```

### Pods Not Healing

```bash
# Check monitor output for errors
# Look for "ERROR:" or "FAILED:" messages

# Verify kubectl access
kubectl auth can-i update deployments --namespace agentic-demo

# Check pod logs for actual issues
kubectl logs <pod-name> -n agentic-demo
```

### Memory Issues

```bash
# Memory file corrupted
rm agentic_memory.json
python3 agentic_monitor.py --fresh

# Memory not loading
cat agentic_memory.json  # Check JSON validity
```

---

## Safety Considerations

### Built-in Safeguards

1. **Namespace Isolation:** Only monitors specified namespace
2. **Action Validation:** Only executes predefined actions
3. **Resource Limits:** Memory increases capped at reasonable limits
4. **Dry-run Mode:** `--no-auto` flag for observation without action
5. **Action Logging:** All actions logged with timestamps

### Production Recommendations

- Start with `--no-auto` to observe behavior
- Monitor in non-critical namespace first
- Review `agentic_memory.json` periodically
- Set appropriate check intervals (avoid overloading API)
- Implement alerting on remediation failures
- Consider resource quotas on monitored namespace

---

## Future Enhancements

Planned improvements:

- Multi-cluster support
- Integration with Prometheus/Grafana
- Slack/PagerDuty notifications
- Rollback on failed remediations
- Explainability reports for AI decisions
- Web dashboard for monitoring
- Advanced learning algorithms (reinforcement learning)
- Custom action plugins

---

## Contributing

Areas where contributions are welcome:

- Additional pattern detectors
- More test scenarios
- Integration with monitoring tools
- Performance optimizations
- Documentation improvements

---

## License

MIT License

---

## References

- [Main Repository README](../README.md)
- [Agent vs Agentic Comparison](../docs/agent-vs-agentic.md)
- [Kubernetes API Documentation](https://kubernetes.io/docs/reference/)
- [OpenAI API Documentation](https://platform.openai.com/docs/)