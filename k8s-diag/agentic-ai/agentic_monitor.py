#!/usr/bin/env python3
"""
Agentic K8s Monitor - Autonomous Self-Healing System
Continuously monitors Kubernetes pods and autonomously remediates issues
"""

import asyncio
import subprocess
import json
import os
import sys
from datetime import datetime
from typing import List, Dict, Optional
import argparse

from memory import Memory, Issue, RemediationAttempt
from planner import Planner


def reset_memory_if_requested(args):
    """Reset memory on each run if --fresh flag is set"""
    memory_file = "agentic_memory.json"
    
    if args.fresh and os.path.exists(memory_file):
        print("\n" + "="*70)
        print("MEMORY RESET")
        print("="*70)
        print(f"Removing old memory file: {memory_file}")
        os.remove(memory_file)
        print("Starting with fresh memory")
        print("="*70 + "\n")
    elif os.path.exists(memory_file):
        try:
            with open(memory_file, 'r') as f:
                data = json.load(f)
                attempts = len(data.get("attempts", []))
                patterns = len(data.get("patterns", {}))
                print("\n" + "="*70)
                print("EXISTING MEMORY LOADED")
                print("="*70)
                print(f"Total attempts: {attempts}")
                print(f"Patterns learned: {patterns}")
                print("="*70 + "\n")
        except:
            pass


class KubernetesTools:
    """Kubernetes command execution tools"""
    
    @staticmethod
    def get_pods(namespace: str) -> List[Dict]:
        """Get all pods in namespace"""
        try:
            result = subprocess.run(
                ["kubectl", "get", "pods", "-n", namespace, "-o", "json"],
                capture_output=True,
                text=True,
                check=True
            )
            data = json.loads(result.stdout)
            return data.get("items", [])
        except Exception as e:
            print(f"ERROR: Failed to get pods - {e}")
            return []
    
    @staticmethod
    def get_pod_logs(pod_name: str, namespace: str, tail: int = 50) -> str:
        """Get pod logs"""
        try:
            result = subprocess.run(
                ["kubectl", "logs", pod_name, "-n", namespace, f"--tail={tail}"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.stdout
        except Exception as e:
            return f"Error getting logs: {e}"
    
    @staticmethod
    def get_pod_description(pod_name: str, namespace: str) -> str:
        """Get pod description"""
        try:
            result = subprocess.run(
                ["kubectl", "describe", "pod", pod_name, "-n", namespace],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except Exception as e:
            return f"Error describing pod: {e}"
    
    @staticmethod
    def get_pod_events(pod_name: str, namespace: str) -> str:
        """Get events for a pod"""
        try:
            result = subprocess.run(
                ["kubectl", "get", "events", "-n", namespace, 
                 "--field-selector", f"involvedObject.name={pod_name}",
                 "--sort-by=.lastTimestamp"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except Exception as e:
            return f"Error getting events: {e}"
    
    @staticmethod
    def restart_pod(pod_name: str, namespace: str) -> bool:
        """Restart a pod by deleting it"""
        try:
            result = subprocess.run(
                ["kubectl", "delete", "pod", pod_name, "-n", namespace],
                capture_output=True,
                text=True,
                check=True
            )
            print(f"   SUCCESS: Restarted pod {pod_name}")
            return True
        except Exception as e:
            print(f"   FAILED: Could not restart pod - {e}")
            return False
    
    @staticmethod
    def update_deployment_env(deployment_name: str, namespace: str, env_vars: Dict) -> bool:
        """Update deployment environment variables"""
        try:
            result = subprocess.run(
                ["kubectl", "get", "deployment", deployment_name, "-n", namespace, "-o", "json"],
                capture_output=True,
                text=True,
                check=True
            )
            deployment = json.loads(result.stdout)
            
            containers = deployment["spec"]["template"]["spec"]["containers"]
            for container in containers:
                if "env" not in container:
                    container["env"] = []
                
                for key, value in env_vars.items():
                    found = False
                    for env in container["env"]:
                        if env["name"] == key:
                            env["value"] = value
                            found = True
                            break
                    if not found:
                        container["env"].append({"name": key, "value": value})
            
            deployment_json = json.dumps(deployment)
            result = subprocess.run(
                ["kubectl", "apply", "-f", "-"],
                input=deployment_json,
                capture_output=True,
                text=True,
                check=True
            )
            print(f"   SUCCESS: Updated deployment {deployment_name}")
            print(f"   Added environment variables: {', '.join(env_vars.keys())}")
            return True
            
        except Exception as e:
            print(f"   FAILED: Could not update deployment - {e}")
            return False
    
    @staticmethod
    def increase_memory(deployment_name: str, namespace: str, new_limit: str) -> bool:
        """Increase memory limit for a deployment"""
        try:
            result = subprocess.run(
                ["kubectl", "get", "deployment", deployment_name, "-n", namespace, "-o", "json"],
                capture_output=True,
                text=True,
                check=True
            )
            deployment = json.loads(result.stdout)
            
            containers = deployment["spec"]["template"]["spec"]["containers"]
            for container in containers:
                if "resources" not in container:
                    container["resources"] = {"limits": {}, "requests": {}}
                if "limits" not in container["resources"]:
                    container["resources"]["limits"] = {}
                
                container["resources"]["limits"]["memory"] = new_limit
                
                if "requests" not in container["resources"]:
                    container["resources"]["requests"] = {}
                
                import re
                match = re.match(r'(\d+)(\w+)', new_limit)
                if match:
                    value, unit = match.groups()
                    request_value = int(int(value) * 0.8)
                    container["resources"]["requests"]["memory"] = f"{request_value}{unit}"
            
            deployment_json = json.dumps(deployment)
            result = subprocess.run(
                ["kubectl", "apply", "-f", "-"],
                input=deployment_json,
                capture_output=True,
                text=True,
                check=True
            )
            print(f"   SUCCESS: Increased memory for {deployment_name} to {new_limit}")
            return True
            
        except Exception as e:
            print(f"   FAILED: Could not increase memory - {e}")
            return False
    
    @staticmethod
    def fix_image_name(deployment_name: str, namespace: str, new_image: str) -> bool:
        """Fix image name in deployment"""
        try:
            result = subprocess.run(
                ["kubectl", "set", "image", f"deployment/{deployment_name}", 
                 f"*={new_image}", "-n", namespace],
                capture_output=True,
                text=True,
                check=True
            )
            print(f"   SUCCESS: Updated image for {deployment_name} to {new_image}")
            return True
        except Exception as e:
            print(f"   FAILED: Could not fix image - {e}")
            return False


class AgenticMonitor:
    """Autonomous Kubernetes monitoring and remediation agent"""
    
    def __init__(self, namespace: str, interval: int = 30, auto_remediate: bool = True):
        self.namespace = namespace
        self.interval = interval
        self.auto_remediate = auto_remediate
        self.tools = KubernetesTools()
        self.memory = Memory()
        self.planner = Planner(self.memory)
        self.running = True
        
        print("\n" + "="*70)
        print("AGENTIC K8S MONITOR - INITIALIZATION")
        print("="*70)
        print(f"Namespace:        {namespace}")
        print(f"Check interval:   {interval} seconds")
        print(f"Auto-remediate:   {'ENABLED' if auto_remediate else 'DISABLED'}")
        
        stats = self.memory.get_statistics()
        print(f"Memory attempts:  {stats['total_attempts']}")
        print(f"Patterns learned: {stats['patterns_learned']}")
        print("="*70 + "\n")
    
    async def run(self):
        """Main monitoring loop"""
        print("="*70)
        print("STARTING AUTONOMOUS MONITORING")
        print("="*70)
        print("Press Ctrl+C to stop\n")
        
        iteration = 0
        
        try:
            while self.running:
                iteration += 1
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                print("\n" + "="*70)
                print(f"ITERATION #{iteration} - {timestamp}")
                print("="*70)
                
                # OBSERVE
                print("\n[OBSERVE] Checking pod status...")
                issues = await self.observe()
                
                if not issues:
                    print("Result: No issues detected - all pods healthy")
                else:
                    print(f"Result: Found {len(issues)} issue(s)\n")
                    
                    for idx, issue in enumerate(issues, 1):
                        print("-" * 70)
                        print(f"ISSUE #{idx} of {len(issues)}")
                        print("-" * 70)
                        print(f"Pod name:    {issue.pod_name}")
                        print(f"Status:      {issue.status}")
                        print(f"Reason:      {issue.reason}")
                        if issue.message:
                            print(f"Message:     {issue.message[:100]}")
                        
                        # PLAN
                        print("\n[PLAN] Creating remediation plan...")
                        context = await self.gather_context(issue)
                        plan = self.planner.create_plan(issue, context)
                        
                        print(f"\nRemediation plan ({len(plan)} step(s)):")
                        for i, step in enumerate(plan, 1):
                            print(f"\n  Step {i}: {step['action'].upper()}")
                            print(f"  Reasoning: {step['reasoning'][:200]}")
                            if len(step['reasoning']) > 200:
                                print(f"             ...")
                        
                        # ACT
                        if self.auto_remediate:
                            print("\n[ACT] Executing remediation plan...")
                            success = await self.execute_plan(issue, plan)
                            
                            # LEARN
                            print("\n[LEARN] Storing results in memory...")
                            for step in plan:
                                attempt = RemediationAttempt(
                                    issue=issue,
                                    action=step['action'],
                                    action_details=step['details'],
                                    success=success,
                                    timestamp=datetime.now().isoformat(),
                                    reasoning=step['reasoning']
                                )
                                self.memory.store_attempt(attempt)
                            print(f"Stored: {step['action']} attempt (success={success})")
                        else:
                            print("\n[ACT] Skipped - auto-remediation is disabled")
                
                print("\n" + "="*70)
                print(f"Waiting {self.interval} seconds until next check...")
                print("="*70)
                await asyncio.sleep(self.interval)
                
        except KeyboardInterrupt:
            print("\n\n" + "="*70)
            print("MONITORING STOPPED BY USER")
            print("="*70)
            self.print_summary()
    
    async def observe(self) -> List[Issue]:
        """Observe cluster state and detect issues"""
        issues = []
        pods = self.tools.get_pods(self.namespace)
        
        for pod in pods:
            pod_name = pod["metadata"]["name"]
            status = pod["status"]["phase"]
            
            container_statuses = pod["status"].get("containerStatuses", [])
            for container_status in container_statuses:
                if not container_status.get("ready", False):
                    state = container_status.get("state", {})
                    
                    if "waiting" in state:
                        reason = state["waiting"].get("reason", "Unknown")
                        message = state["waiting"].get("message", "")
                        
                        issue = Issue(
                            pod_name=pod_name,
                            namespace=self.namespace,
                            status="Waiting",
                            reason=reason,
                            message=message,
                            timestamp=datetime.now().isoformat(),
                            container_name=container_status["name"]
                        )
                        issues.append(issue)
                    
                    elif "terminated" in state:
                        reason = state["terminated"].get("reason", "Unknown")
                        message = state["terminated"].get("message", "")
                        exit_code = state["terminated"].get("exitCode", 0)
                        
                        issue = Issue(
                            pod_name=pod_name,
                            namespace=self.namespace,
                            status="Terminated",
                            reason=reason,
                            message=f"Exit code: {exit_code}. {message}",
                            timestamp=datetime.now().isoformat(),
                            container_name=container_status["name"]
                        )
                        issues.append(issue)
        
        return issues
    
    async def gather_context(self, issue: Issue) -> Dict:
        """Gather context for an issue"""
        context = {}
        context["logs"] = self.tools.get_pod_logs(issue.pod_name, self.namespace)
        context["pod_description"] = self.tools.get_pod_description(issue.pod_name, self.namespace)
        context["events"] = self.tools.get_pod_events(issue.pod_name, self.namespace)
        return context
    
    async def execute_plan(self, issue: Issue, plan: List[Dict]) -> bool:
        """Execute remediation plan"""
        for i, step in enumerate(plan, 1):
            action = step["action"]
            details = step["details"]
            
            print(f"\n  Executing step {i}/{len(plan)}: {action.upper()}")
            
            success = False
            
            if action == "restart_pod":
                success = self.tools.restart_pod(issue.pod_name, self.namespace)
            
            elif action == "update_env":
                deployment_name = details.get("deployment_name", issue.pod_name.rsplit('-', 2)[0])
                env_vars = details.get("env_vars", {})
                success = self.tools.update_deployment_env(deployment_name, self.namespace, env_vars)
            
            elif action == "increase_memory":
                deployment_name = details.get("deployment_name", issue.pod_name.rsplit('-', 2)[0])
                new_limit = details.get("new_limit", "512Mi")
                success = self.tools.increase_memory(deployment_name, self.namespace, new_limit)
            
            elif action == "fix_image_name":
                deployment_name = details.get("deployment_name", issue.pod_name.rsplit('-', 2)[0])
                new_image = details.get("new_image")
                if new_image:
                    success = self.tools.fix_image_name(deployment_name, self.namespace, new_image)
            
            else:
                print(f"   ERROR: Unknown action '{action}'")
            
            if success:
                await asyncio.sleep(5)
                return True
            else:
                continue
        
        return False
    
    def print_summary(self):
        """Print session summary"""
        stats = self.memory.get_statistics()
        print("\n" + "="*70)
        print("SESSION SUMMARY")
        print("="*70)
        print(f"Total remediation attempts:  {stats['total_attempts']}")
        print(f"Successful attempts:         {stats['successful_attempts']}")
        print(f"Success rate:                {stats['success_rate']*100:.1f}%")
        print(f"Patterns learned:            {stats['patterns_learned']}")
        print("="*70 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Agentic K8s Monitor - Autonomous Self-Healing")
    parser.add_argument("--namespace", "-n", default="agentic-demo",
                       help="Kubernetes namespace to monitor")
    parser.add_argument("--interval", "-i", type=int, default=30,
                       help="Monitoring interval in seconds")
    parser.add_argument("--no-auto", action="store_true",
                       help="Disable auto-remediation (observe only)")
    parser.add_argument("--fresh", "-f", action="store_true",
                       help="Start with fresh memory (delete agentic_memory.json)")
    
    args = parser.parse_args()
    
    if not os.getenv("OPENAI_API_KEY"):
        print("\n" + "="*70)
        print("ERROR: OPENAI_API_KEY NOT SET")
        print("="*70)
        print("Please set your OpenAI API key:")
        print("  export OPENAI_API_KEY='your-key-here'")
        print("="*70 + "\n")
        sys.exit(1)
    
    reset_memory_if_requested(args)
    
    monitor = AgenticMonitor(
        namespace=args.namespace,
        interval=args.interval,
        auto_remediate=not args.no_auto
    )
    
    asyncio.run(monitor.run())


if __name__ == "__main__":
    main()
