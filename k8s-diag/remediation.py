import json
import subprocess
import datetime
import traceback


def remediate_pod(pod_name, namespace, diagnosis, dry_run=True):
    """Analyse the LLM diagnosis and run (or preview) the appropriate fix.

    All kubectl commands are built as *lists* and executed with shell=False so
    that Python hands arguments directly to the process — no cmd.exe / sh
    quoting issues on any platform.
    """
    actions = []          # list[list[str]]  — each entry is an argv list
    remediation_type = None

    def infer_deployment_name(pod_name):
        # Assumes pod name is: <deployment>-<replicaSet-hash>-<pod-hash>
        return "-".join(pod_name.split("-")[:-2])

    deployment_name = infer_deployment_name(pod_name)

    # ------------------------------------------------------------------
    # Detect issue type and build the remediation command list
    # ------------------------------------------------------------------

    if "OOMKilled" in diagnosis:
        remediation_type = "memory_patch"
        recommended_mem = "400Mi"
        print(f"🔧 Detected OOMKilled. Suggest increasing memory limits to {recommended_mem}.")

        patch_payload = json.dumps([{
            "op": "replace",
            "path": "/spec/template/spec/containers/0/resources/limits/memory",
            "value": recommended_mem,
        }])

        patch_cmd = [
            "kubectl", "patch", "deployment", deployment_name,
            "-n", namespace,
            "--type", "json",
            "-p", patch_payload,
        ]

        print(f"Dry run: Would patch deployment memory limit to {recommended_mem}")
        print(f"Patch command: {' '.join(patch_cmd)}")
        actions.append(patch_cmd)

        # Pre-flight check: show current memory limit
        verify_cmd = [
            "kubectl", "get", "deployment", deployment_name,
            "-n", namespace,
            "-o", r"jsonpath={.spec.template.spec.containers[0].resources.limits.memory}",
        ]
        res = subprocess.run(verify_cmd, capture_output=True, text=True)
        print(f"Current memory limit: {res.stdout.strip() or '(not set)'}")

    elif "CrashLoopBackOff" in diagnosis:
        remediation_type = "restart_pod"
        print(f"🔧 Detected CrashLoopBackOff. Suggest restarting the pod.")

        restart_cmd = ["kubectl", "delete", "pod", pod_name, "-n", namespace]
        print(f"Dry run: Would restart pod {pod_name}")
        print(f"Restart command: {' '.join(restart_cmd)}")
        actions.append(restart_cmd)

    elif "probe" in diagnosis.lower() or "Liveness probe failed" in diagnosis:
        remediation_type = "manual_probe_fix"
        print(f"🔧 Detected probe failure. You may need to patch or remove the liveness/readiness probe.")
        print(f"💡 Dry run: Probe-related remediation would be required.")
        print(f"🔍 Suggest editing the deployment manually or updating the YAML.")
        actions.append(["#", f"Manual probe fix needed for pod {pod_name}"])

    elif "ImagePullBackOff" in diagnosis:
        print(f"🔧 ImagePullBackOff detected — likely an image or pull-secret issue.")
        print(f"Please check the image name or pull secrets. No safe automated remediation.")
        actions.append(["#", "Manual remediation recommended for image issues."])

    else:
        print("No automatic remediation available.")
        return

    # ------------------------------------------------------------------
    # Execute or skip
    # ------------------------------------------------------------------

    if dry_run:
        confirm = input("Do you want to apply the above remediation? (yes/no): ").strip().lower()
        if confirm != "yes":
            print("Skipping remediation.")
            return

        for cmd in actions:
            if cmd[0] == "#":
                print(f"Skipping comment/reminder: {' '.join(cmd[1:])}")
                continue
            run_and_log(cmd)

        # Verify deployment health for actions that touch deployments
        if remediation_type in ["memory_patch", "restart_pod"]:
            print("🔍 Verifying deployment health...")
            wait_cmd = [
                "kubectl", "wait",
                f"--for=condition=Available",
                f"deployment/{deployment_name}",
                "-n", namespace,
                "--timeout=30s",
            ]
            wait_result = subprocess.run(wait_cmd, capture_output=True, text=True)

            if wait_result.returncode == 0:
                print(f"✅ Deployment {deployment_name} is now healthy.")
            else:
                print(f"⚠️  Deployment {deployment_name} is still not healthy.\n   {wait_result.stderr.strip()}")

            with open("remediation.log", "a") as log_file:
                log_file.write(
                    f"{datetime.datetime.now()} | {' '.join(wait_cmd)} | "
                    f"ReturnCode: {wait_result.returncode} | "
                    f"Output: {wait_result.stdout.strip()} | "
                    f"Error: {wait_result.stderr.strip()}\n"
                )
    else:
        for cmd in actions:
            if cmd[0] != "#":
                run_and_log(cmd)


def run_and_log(cmd: list[str]):
    """Execute a command (as an argv list) and append the result to remediation.log."""
    display = " ".join(cmd)
    try:
        print(f"🔧 Executing: {display}")
        res = subprocess.run(cmd, capture_output=True, text=True)

        with open("remediation.log", "a") as log_file:
            log_file.write(
                f"{datetime.datetime.now()} | {display} | "
                f"ReturnCode: {res.returncode} | "
                f"Output: {res.stdout.strip()} | "
                f"Error: {res.stderr.strip()}\n"
            )

        if res.returncode != 0:
            print(f"Command failed with return code {res.returncode}")
            print(f"STDERR: {res.stderr.strip()}")

    except Exception:
        print("Exception occurred while executing remediation command:")
        traceback.print_exc()
