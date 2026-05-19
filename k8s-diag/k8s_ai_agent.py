import os
import json
import argparse
import subprocess
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Langfuse — import before the OpenAI client so the instrumentation patch
# is applied in time.
# ---------------------------------------------------------------------------
from langfuse import get_client, propagate_attributes
from langfuse.openai import OpenAI          # drop-in replacement; auto-traces all calls

from remediation import remediate_pod

# Load environment variables from .env (including LANGFUSE_* and OLLAMA_*)
load_dotenv()

# ---------------------------------------------------------------------------
# Langfuse requires these three env vars (loaded above from .env or the shell).
# ---------------------------------------------------------------------------
# LANGFUSE_PUBLIC_KEY  = "pk-..."
# LANGFUSE_SECRET_KEY  = "sk-..."
# LANGFUSE_BASE_URL    = "https://cloud.langfuse.com"  # or self-hosted URL

langfuse = get_client()

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434/v1"
DEFAULT_MODEL = "gpt-oss:latest"


def build_client(base_url: str) -> OpenAI:
    """Return a Langfuse-instrumented OpenAI-compatible client for Ollama.

    langfuse.openai.OpenAI is a transparent drop-in for openai.OpenAI.
    Every chat.completions.create() call is automatically captured as a
    Langfuse generation span — no manual instrumentation needed per call.
    """
    return OpenAI(
        base_url=base_url,
        api_key=os.getenv("OLLAMA_API_KEY", "ollama"),  # Ollama ignores the key
    )


# ---------------------------------------------------------------------------
# Kubernetes helpers
# ---------------------------------------------------------------------------

def namespace_exists(namespace: str) -> bool:
    result = subprocess.run(
        ["kubectl", "get", "namespace", namespace],
        capture_output=True, text=True,
    )
    return result.returncode == 0


def suggest_namespace(namespace: str) -> None:
    result = subprocess.run(["kubectl", "get", "ns", "-o", "json"], capture_output=True, text=True)
    ns_data = json.loads(result.stdout)
    all_namespaces = [ns["metadata"]["name"] for ns in ns_data["items"]]

    from difflib import get_close_matches
    suggestions = get_close_matches(namespace, all_namespaces, n=3)

    if suggestions:
        print(f"🔍 Did you mean: {', '.join(suggestions)}?")


def get_unhealthy_pods(namespace: str):
    try:
        result = subprocess.run(
            ["kubectl", "get", "pods", "-n", namespace, "-o", "json"],
            capture_output=True, text=True, check=False,
        )

        if result.returncode != 0:
            print(f"Error: Namespace '{namespace}' does not exist or cannot be accessed.")
            print(f"🔍 kubectl says: {result.stderr.strip()}")
            return None

        data = json.loads(result.stdout)
        unhealthy_pods = []

        for pod in data["items"]:
            name = pod["metadata"]["name"]
            status = pod["status"].get("phase", "")
            container_statuses = pod["status"].get("containerStatuses", [])

            pod_unhealthy = False

            if status != "Running":
                pod_unhealthy = True

            for cs in container_statuses:
                waiting_state = cs.get("state", {}).get("waiting")
                if waiting_state and waiting_state.get("reason"):
                    pod_unhealthy = True
                    break

                if cs.get("restartCount", 0) > 3:
                    pod_unhealthy = True
                    break

                if not cs.get("ready", True):
                    pod_unhealthy = True
                    break

                last_terminated = cs.get("lastState", {}).get("terminated")
                if last_terminated and last_terminated.get("exitCode", 0) != 0:
                    pod_unhealthy = True
                    break

            if pod_unhealthy:
                unhealthy_pods.append(name)

        return unhealthy_pods

    except Exception as e:
        print(f"Unexpected error while checking pods: {e}")
        return None


def get_pod_info(pod_name: str, namespace: str):
    describe = subprocess.run(
        ["kubectl", "describe", "pod", pod_name, "-n", namespace],
        capture_output=True, text=True,
    )
    logs = subprocess.run(
        ["kubectl", "logs", pod_name, "-n", namespace],
        capture_output=True, text=True,
    )
    logs_output = logs.stdout if logs.returncode == 0 else "No logs available."
    return describe.stdout, logs_output


# ---------------------------------------------------------------------------
# LLM analysis — with Langfuse tracing per pod
# ---------------------------------------------------------------------------

def analyze_with_llm(
    client: OpenAI,
    model: str,
    pod_name: str,
    namespace: str,
    describe: str,
    logs: str,
) -> str:
    """Diagnose a single unhealthy pod via the LLM.

    Uses start_as_current_observation() to open a root span for each pod
    (which implicitly creates a new Langfuse trace). propagate_attributes()
    attaches pod/namespace/tags to the span and all its children — including
    the OpenAI generation span created automatically by langfuse.openai.
    """
    print(f"\n🤖 Analyzing pod '{pod_name}' with model '{model}'...\n")

    prompt = f"""You are a Kubernetes expert. Diagnose the following pod issue.

Namespace: {namespace}
Pod Name: {pod_name}

--- kubectl describe pod ---
{describe}

--- kubectl logs ---
{logs}

Please provide:
1. Root cause
2. Possible reasons
3. Suggested fixes
4. Any supporting evidence from logs/events
"""

    # Each pod gets its own root span → its own trace in Langfuse.
    # start_as_current_observation sets the OTel active context so that the
    # auto-instrumented OpenAI call below is automatically nested as a child.
    with langfuse.start_as_current_observation(
        as_type="span",
        name="k8s-pod-diagnosis",
        input={"pod": pod_name, "namespace": namespace},
    ) as span:
        # Propagate pod/namespace/tags to this span and all child observations
        # (i.e. the OpenAI generation span created by langfuse.openai).
        with propagate_attributes(
            metadata={"pod": pod_name, "namespace": namespace, "model": model},
            tags=["k8s", "diagnosis"],
        ):
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a Kubernetes SRE expert."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
            )

        analysis = response.choices[0].message.content.strip()

        # Surface the diagnosis as the span output in Langfuse.
        span.update(output={"diagnosis": analysis})

    return analysis


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="K8s AI Agent — diagnose unhealthy pods using a local Ollama model."
    )
    parser.add_argument(
        "--model",
        default=os.getenv("OLLAMA_MODEL", DEFAULT_MODEL),
        help=f"Ollama model to use for analysis (default: '{DEFAULT_MODEL}', "
             "or set OLLAMA_MODEL env var).",
    )
    parser.add_argument(
        "--ollama-url",
        default=os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL),
        help=f"Base URL of the Ollama server (default: '{DEFAULT_OLLAMA_BASE_URL}', "
             "or set OLLAMA_BASE_URL env var).",
    )
    parser.add_argument(
        "--namespace",
        default=None,
        help="Kubernetes namespace to scan (prompted interactively if omitted).",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    client = build_client(args.ollama_url)
    print(f"🔗 Using Ollama at {args.ollama_url}  |  model: {args.model}")
    print(f"📡 Langfuse tracing active  |  endpoint: {os.getenv('LANGFUSE_BASE_URL', 'https://cloud.langfuse.com')}")

    namespace = args.namespace or input("Enter the namespace to scan: ").strip()

    if not namespace_exists(namespace):
        print(f"Error: Namespace '{namespace}' does not exist.")
        suggest_namespace(namespace)
        return

    unhealthy_pods = get_unhealthy_pods(namespace)
    if unhealthy_pods is None:
        return

    if not unhealthy_pods:
        print("✅ All pods are healthy in this namespace.")
        return

    print(f"🔍 Found {len(unhealthy_pods)} unhealthy pod(s): {unhealthy_pods}")

    for pod in unhealthy_pods:
        describe, logs = get_pod_info(pod, namespace)
        result = analyze_with_llm(client, args.model, pod, namespace, describe, logs)

        print(f"\nDiagnosis for pod '{pod}':\n{result}")
        print("=" * 80)

        # 🔧 Dry-run remediation
        remediate_pod(pod, namespace, result, dry_run=True)

    # Flush all buffered Langfuse events before the process exits.
    # Without this, spans still in the async queue may be lost on fast exit.
    langfuse.flush()
    print("\n📡 Langfuse traces flushed.")


if __name__ == "__main__":
    main()
