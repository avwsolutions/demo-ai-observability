# Kubernetes AI Diagnostics

AI-powered Kubernetes troubleshooting that demonstrates two distinct approaches:

**Part 1: Agent AI** - On-demand diagnostics with human approval  
**Part 2: Agentic AI** - Autonomous self-healing with continuous monitoring

This project showcases the practical difference between Agent AI (reactive, single-shot) and Agentic AI (proactive, autonomous, self-learning).

---

## Quick Start

### Part 1: Agent AI (On-Demand Diagnostics)

Interactive diagnostics requiring human approval for each action.

```bash
# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY='your-key'

# Deploy test scenarios
kubectl create namespace ai-apps
sh k8s-manifests/deploy.sh

# Run agent
python3 k8s_ai_agent.py
```

### Part 2: Agentic AI (Autonomous Self-Healing)

Continuous monitoring with autonomous remediation and learning.

```bash
# Navigate to agentic-ai directory
cd agentic-ai

# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY='your-key'

# Deploy test scenarios
cd test-scenarios
./deploy-scenarios.sh

# Run autonomous monitor
cd ..
python3 agentic_monitor.py --namespace agentic-demo --interval 30
```

---

## Agent AI vs Agentic AI

### Agent AI (Part 1)

**Characteristics:**
- Reactive: Runs when explicitly invoked
- Single-shot: Analyzes once, provides recommendations
- Human-in-the-loop: Requires approval for each action
- Stateless: No memory between runs

**Use Cases:**
- Interactive troubleshooting sessions
- Learning and exploration
- Manual approval workflows
- One-time diagnostics

**Example Flow:**
```
1. User runs: python3 k8s_ai_agent.py
2. Agent detects issues
3. Agent provides diagnosis and recommendations
4. User approves/rejects each action
5. Agent executes approved actions
6. Process ends
```

### Agentic AI (Part 2)

**Characteristics:**
- Proactive: Continuously monitors cluster
- Multi-step reasoning: Plans complex remediation sequences
- Autonomous: Executes without human approval
- Learning: Stores successful patterns for future use

**Use Cases:**
- Production self-healing systems
- 24/7 autonomous operations
- Pattern-based optimization
- Reducing on-call burden

**Example Flow:**
```
1. Monitor runs continuously
2. OBSERVE: Detects pod failures
3. PLAN: Creates multi-step remediation plan
4. ACT: Executes remediation autonomously
5. LEARN: Stores successful patterns
6. Next issue: Applies learned solutions immediately
7. Loop continues indefinitely
```

**Key Difference:** Agentic AI learns from experience. First OOMKilled issue might try 256Mi then 512Mi. Second identical issue goes directly to 512Mi.

See [docs/agent-vs-agentic.md](docs/agent-vs-agentic.md) for detailed comparison.

---

## Part 1: Agent AI Features

### Current Capabilities

- Namespace validation
- Unhealthy pod detection (CrashLoopBackOff, ImagePullBackOff, OOMKilled, probe failures)
- AI-powered root cause analysis using GPT-4
- Human-approved remediation with dry-run mode
- Action logging with timestamps

### Supported Remediation Types

| Issue | Diagnosis | Action |
|-------|-----------|--------|
| ImagePullBackOff | Image issue | Manual reminder |
| CrashLoopBackOff | Container crash | Pod restart |
| OOMKilled | Memory overuse | Memory limit increase |
| Probe failure | Misconfigured probes | Manual suggestion |

### Setup Instructions

#### Prerequisites

- Python 3.8+
- Kubernetes cluster with `kubectl` configured
- OpenAI API key

#### Installation

```bash
git clone https://github.com/opscart/k8s-ai-diagnostics.git
cd k8s-ai-diagnostics
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Deploy Test Scenarios

```bash
kubectl create namespace ai-apps
sh k8s-manifests/deploy.sh
```

#### Run Agent

```bash
export OPENAI_API_KEY='your-key'
python3 k8s_ai_agent.py
```

**Expected Output:**

```
Enter the namespace to scan: ai-apps
Found 4 unhealthy pod(s): ['broken-nginx', 'oom-test', 'crashy', 'unhealthy-probe']

Analyzing pod: crashy...
Detected CrashLoopBackOff. Suggest restarting the pod.
Do you want to apply the above remediation? (yes/no): yes
Deployment crashy is now healthy.
```

#### Verify Deployment

```bash
kubectl get pods -n ai-apps
```

Expected statuses:
```
NAME                               READY   STATUS             RESTARTS   AGE
broken-nginx-5f6cdfb774-m7kw7      0/1     ImagePullBackOff   0          7m
crashy-77747bbb47-mr75j            0/1     CrashLoopBackOff   6          7m
oom-test-5fd8f6b8d9-c9p52          1/1     Running            0          2m
unhealthy-probe-78d9b76567-5x8h6   0/1     Running            1          1m
```

### Limitations

- No automated probe logic remediation
- Assumes single-container deployments for memory patching
- Only first container considered for resource checks
- CLI-only interface (no web UI)

---

## Part 2: Agentic AI Features

### Current Capabilities

- Continuous autonomous monitoring
- Multi-step remediation planning with LLM reasoning
- Pattern detection (image typos, missing env vars, OOM patterns)
- Memory-based learning from successful remediations
- Autonomous execution with safety guardrails

### Autonomous Remediation Loop

```
OBSERVE → PLAN → ACT → LEARN → (repeat)
```

**OBSERVE:**
- Continuously scans namespace for pod failures
- Detects: CrashLoopBackOff, ImagePullBackOff, OOMKilled, probe failures

**PLAN:**
- Analyzes logs and pod descriptions
- Detects patterns (typos, missing env vars)
- Consults memory for learned solutions
- Creates multi-step remediation plan using GPT-4

**ACT:**
- Executes remediation actions:
  - Fix image name typos
  - Add missing environment variables
  - Increase memory limits
  - Restart pods

**LEARN:**
- Stores successful remediation patterns
- Applies learned solutions to similar future issues
- Improves efficiency over time

### Setup Instructions

See [agentic-ai/README.md](agentic-ai/README.md) for detailed setup and usage.

#### Quick Start

```bash
cd agentic-ai

# Setup environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY='your-key'

# Deploy test scenarios
cd test-scenarios
./deploy-scenarios.sh

# Run autonomous monitor
cd ..
python3 agentic_monitor.py --namespace agentic-demo --interval 30 --fresh
```

#### Test Scenarios

Three scenarios demonstrate autonomous learning:

1. **Image Typo Detection**
   - Pods: web-server (nginx:latst), alpine-app (apline:3.18)
   - Detection: Automatic typo correction from common patterns
   - Fix: Update deployment with corrected image names

2. **Missing Environment Variables**
   - Pod: mysql-client (missing MYSQL_HOST, MYSQL_ROOT_PASSWORD)
   - Detection: Parse logs for "variable is: " patterns
   - Fix: Add required environment variables with sensible defaults

3. **OOMKilled Progressive Learning**
   - Pod: memory-hungry (exceeds 128Mi limit)
   - Detection: Terminated state with OOMKilled reason
   - Fix: Progressively increase memory (256Mi → 512Mi)
   - Learning: Future identical apps get optimal memory immediately

### Command Line Options

```bash
# Standard autonomous mode
python3 agentic_monitor.py --namespace agentic-demo --interval 30

# Start with fresh memory (no learning from previous runs)
python3 agentic_monitor.py --namespace agentic-demo --interval 30 --fresh

# Observe-only mode (no auto-remediation)
python3 agentic_monitor.py --namespace agentic-demo --no-auto

# Custom check interval
python3 agentic_monitor.py --namespace agentic-demo --interval 60
```

### Learning Example

**First OOMKilled Incident:**
```
Iteration 1: Detect OOMKilled at 128Mi
Iteration 2: Increase to 256Mi → Still OOMKilled
Iteration 3: Increase to 512Mi → Success
LEARN: Store pattern "memory-hungry app needs 512Mi"
```

**Second Identical App:**
```
Iteration 1: Detect OOMKilled at 128Mi
PLAN: Memory recalls "similar app needs 512Mi"
ACT: Directly apply 512Mi → Success
Result: Fixed in one iteration (no trial and error)
```

---

## Architecture

### Agent AI Architecture (Part 1)

```
┌─────────────┐
│   Human     │
│  Initiates  │
└──────┬──────┘
       │
       v
┌─────────────────────────────┐
│     k8s_ai_agent.py         │
│  - Namespace validation     │
│  - Pod health detection     │
│  - OpenAI GPT-4 analysis    │
│  - Remediation suggestions  │
└──────┬──────────────────────┘
       │
       v
┌─────────────┐     ┌──────────────┐
│   Kubectl   │────>│  Kubernetes  │
│  Commands   │<────│   Cluster    │
└─────────────┘     └──────────────┘
       │
       v
┌─────────────┐
│   Human     │
│  Approves   │
└─────────────┘
```

### Agentic AI Architecture (Part 2)

```
┌───────────────────────────────────────┐
│      Autonomous Monitor Loop          │
│                                       │
│  ┌─────────┐    ┌─────────┐           │
│  │ OBSERVE │───>│  PLAN   │           │
│  └─────────┘    └────┬────┘           │
│       ^               │               │
│       │               v               │
│  ┌─────────┐    ┌─────────┐           │
│  │  LEARN  │<───│   ACT   │           │
│  └─────────┘    └─────────┘           │
│                                       │
└───────────────────────────────────────┘
         │                    │
         v                    v
    ┌─────────┐         ┌──────────┐
    │ Memory  │         │ Kubectl  │
    │  Store  │         │ Actions  │
    └─────────┘         └────┬─────┘
                             │
                             v
                      ┌──────────────┐
                      │  Kubernetes  │
                      │   Cluster    │
                      └──────────────┘
```

**Key Components:**

- **agentic_monitor.py**: Main autonomous loop orchestrator
- **planner.py**: Multi-step remediation planning with pattern detection
- **memory.py**: Persistent learning storage
- **KubernetesTools**: kubectl command abstractions

---

## Repository Structure

```
k8s-ai-diagnostics/
├── k8s_ai_agent.py              # Part 1: Agent AI (interactive)
├── remediation.py               # Part 1: Remediation logic
├── k8s-manifests/              # Part 1: Test scenarios
│   ├── deploy.sh
│   ├── broken-nginx-deployment.yaml
│   ├── crashy-deployment.yaml
│   ├── oom-test-deployment.yaml
│   └── unhealthy-probe-deployment.yaml
├── agentic-ai/                 # Part 2: Agentic AI
│   ├── agentic_monitor.py     # Autonomous monitor
│   ├── planner.py             # AI planning engine
│   ├── memory.py              # Learning system
│   ├── requirements.txt
│   ├── README.md              # Detailed agentic AI docs
│   └── test-scenarios/        # Autonomous test scenarios
│       ├── deploy-scenarios.sh
│       ├── cleanup-scenarios.sh
│       ├── scenario-1-crashloop-missing-env.yaml
│       ├── scenario-2-oom-progressive.yaml
│       └── scenario-3-image-typo.yaml
├── docs/
│   └── agent-vs-agentic.md    # Detailed comparison
└── README.md                   # This file
```

---

## Documentation

- [Agent vs Agentic AI Comparison](docs/agent-vs-agentic.md) - Detailed theoretical and practical comparison
- [Agentic AI README](agentic-ai/README.md) - Comprehensive usage guide for Part 2
- [DZone Article - Part 1](https://dzone.com/articles/ai-driven-kubernetes-diagnostics) - Featured article on Agent AI

---

## Contributing

Contributions welcome! Areas of interest:

**Part 1 (Agent AI):**
- Web UI for interactive diagnostics
- Additional failure scenarios
- Multi-container pod support

**Part 2 (Agentic AI):**
- Advanced learning algorithms
- Multi-cluster support
- Integration with monitoring tools (Prometheus, Grafana)
- Automated rollback on failed remediations
- Explainability for AI decisions

---

## License

MIT License

---

## References

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [OpenAI API Documentation](https://platform.openai.com/docs/)
- [kubectl Reference](https://kubernetes.io/docs/reference/kubectl/)

---

## Acknowledgments

Built to demonstrate the practical difference between Agent AI and Agentic AI in production Kubernetes environments.