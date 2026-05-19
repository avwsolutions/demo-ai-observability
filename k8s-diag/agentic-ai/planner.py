"""
Planner for Agentic AI
Creates multi-step remediation plans using LLM reasoning
"""

import os
import re
from typing import List, Dict, Optional
from memory import Issue, Memory

# ---------------------------------------------------------------------------
# Langfuse — import before the OpenAI client so the instrumentation patch
# is applied in time.
# ---------------------------------------------------------------------------
from langfuse import get_client, propagate_attributes
from langfuse.openai import OpenAI as LangfuseOpenAI   # drop-in; auto-traces completions

# Module-level Langfuse client (reads LANGFUSE_PUBLIC_KEY / SECRET_KEY / BASE_URL)
langfuse = get_client()

DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434/v1"
DEFAULT_MODEL = "gpt-oss:latest"


IMAGE_TYPO_MAP = {
    "apline": "alpine",
    "latst": "latest",
    "lastest": "latest",
    "ubunut": "ubuntu",
    "ngnix": "nginx",
    "postgress": "postgres",
    "rediss": "redis",
}


class Planner:
    """Creates and manages remediation plans"""
    
    def __init__(
        self,
        memory: Memory,
        model: str = None,
        ollama_base_url: str = None,
    ):
        self.memory = memory
        self.model = model or os.getenv("OLLAMA_MODEL", DEFAULT_MODEL)
        base_url = ollama_base_url or os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL)

        # LangfuseOpenAI is a transparent drop-in for openai.OpenAI.
        # Every chat.completions.create() call is auto-captured as a
        # Langfuse generation span — no extra instrumentation needed per call.
        self.client = LangfuseOpenAI(
            base_url=base_url,
            api_key=os.getenv("OLLAMA_API_KEY", "ollama"),  # Ollama ignores the key
        )
    
    def create_plan(self, issue: Issue, context: Dict) -> List[Dict]:
        """Create a multi-step remediation plan"""
        
        # Special handling for ImagePullBackOff
        if issue.reason == "ImagePullBackOff" or issue.reason == "ErrImagePull":
            typo_fix = self._detect_image_typo(context)
            if typo_fix:
                print(f"Detection: Image typo found")
                print(f"  Original: {typo_fix['original']}")
                print(f"  Corrected: {typo_fix['corrected']}")
                return [{
                    "action": "fix_image_name",
                    "details": {
                        "deployment_name": issue.pod_name.rsplit('-', 2)[0],
                        "new_image": typo_fix['corrected']
                    },
                    "reasoning": f"Detected typo in image name: '{typo_fix['original']}' should be '{typo_fix['corrected']}'",
                    "confidence": "high"
                }]
        
        # Special handling for CrashLoopBackOff
        if issue.reason == "CrashLoopBackOff":
            missing_env = self._detect_missing_env_vars(context)
            if missing_env:
                print(f"Detection: Missing environment variables")
                for key, value in missing_env.items():
                    print(f"  {key} = {value}")
                return [{
                    "action": "update_env",
                    "details": {
                        "deployment_name": issue.pod_name.rsplit('-', 2)[0],
                        "env_vars": missing_env
                    },
                    "reasoning": f"Pod logs indicate missing environment variables: {', '.join(missing_env.keys())}",
                    "confidence": "high"
                }]
        
        # Check memory for learned solutions
        similar_solution = self.memory.recall_similar(issue)
        
        if similar_solution:
            valid_actions = ["restart_pod", "update_env", "increase_memory", "fix_image_name"]
            if similar_solution["action"] in valid_actions:
                print(f"Detection: Found learned solution from memory")
                print(f"  Action: {similar_solution['action']}")
                return [{
                    "action": similar_solution["action"],
                    "details": similar_solution["details"],
                    "reasoning": f"Using learned solution: {similar_solution['action']}",
                    "confidence": "high"
                }]
        
        # New issue - ask LLM
        print(f"Detection: New issue type, consulting AI for plan")
        
        prompt = self._build_planning_prompt(issue, context)
        
        try:
            # Open a root span for this planning operation → one trace per issue in Langfuse.
            with langfuse.start_as_current_observation(
                as_type="span",
                name="k8s-planner",
                input={"pod": issue.pod_name, "namespace": issue.namespace, "reason": issue.reason},
            ) as span:
                with propagate_attributes(
                    metadata={"pod": issue.pod_name, "namespace": issue.namespace, "model": self.model},
                    tags=["k8s", "planner"],
                ):
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": self._get_system_prompt()},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.3
                    )

                plan_text = response.choices[0].message.content
                plan = self._parse_plan(plan_text, issue)
                span.update(output={"plan": plan})

            return plan
            
        except Exception as e:
            print(f"ERROR: AI planning failed - {e}")
            return [{
                "action": "restart_pod",
                "details": {"pod_name": issue.pod_name, "namespace": issue.namespace},
                "reasoning": "Fallback action due to planning error",
                "confidence": "low"
            }]
    
    def _detect_image_typo(self, context: Dict) -> Optional[Dict]:
        """Detect common typos in image names"""
        pod_desc = context.get("pod_description", "")
        
        image_match = re.search(r'Image:\s+(.+?)(?:\n|$)', pod_desc)
        if not image_match:
            return None
        
        original_image = image_match.group(1).strip()
        
        for typo, correct in IMAGE_TYPO_MAP.items():
            if typo in original_image.lower():
                corrected_image = original_image.lower().replace(typo, correct)
                return {
                    "original": original_image,
                    "corrected": corrected_image
                }
        
        return None
    
    def _detect_missing_env_vars(self, context: Dict) -> Optional[Dict]:
        """Detect missing environment variables from logs"""
        logs = context.get("logs", "")
        env_vars = {}
        
        # Pattern: "VARIABLE_NAME is: " with empty value
        matches = re.findall(r'([A-Z][A-Z_]+) is:\s*$', logs, re.MULTILINE)
        for var_name in matches:
            # Skip common log words
            if var_name in ['ERROR', 'WARNING', 'INFO', 'DEBUG']:
                continue
                
            if "PASSWORD" in var_name:
                env_vars[var_name] = "password123"
            elif "HOST" in var_name:
                env_vars[var_name] = "localhost"
            elif "PORT" in var_name:
                env_vars[var_name] = "3306"
            else:
                env_vars[var_name] = "default"
        
        return env_vars if env_vars else None
    
    def _get_system_prompt(self) -> str:
        return """You are an expert Kubernetes SRE creating autonomous remediation plans.

Create a multi-step plan with:
1. Primary action to try first
2. Fallback actions if primary fails
3. Clear reasoning for each step

Format your response as a JSON array of actions:
[
  {
    "action": "action_name",
    "details": {"key": "value"},
    "reasoning": "why this action",
    "confidence": "high|medium|low"
  }
]

Available actions:
- restart_pod: Delete pod to trigger restart
- update_env: Add/update environment variables (provide env_vars dict)
- increase_memory: Increase memory limits (provide new_limit)
- fix_image_name: Correct image name typos (provide new_image)

IMPORTANT: Only use these 4 actions. Be specific and actionable."""
    
    def _build_planning_prompt(self, issue: Issue, context: Dict) -> str:
        history = self.memory.get_history(issue.pod_name)
        
        prompt = f"""
Issue Details:
- Pod: {issue.pod_name}
- Namespace: {issue.namespace}
- Status: {issue.status}
- Reason: {issue.reason}
- Message: {issue.message}

Context:
{self._format_context(context)}

Past Attempts:
{self._format_history(history)}

Create a remediation plan. Only use: restart_pod, update_env, increase_memory, fix_image_name
"""
        return prompt
    
    def _format_context(self, context: Dict) -> str:
        """Format context information"""
        lines = []
        if "logs" in context:
            lines.append(f"Recent Logs:\n{context['logs'][:800]}")
        if "pod_description" in context:
            lines.append(f"Pod Description:\n{context['pod_description'][:500]}")
        if "events" in context:
            lines.append(f"Events:\n{context['events'][:300]}")
        return "\n\n".join(lines)
    
    def _format_history(self, history: List[Dict]) -> str:
        """Format remediation history"""
        if not history:
            return "No past attempts"
        
        lines = []
        for attempt in history[-3:]:
            status = "SUCCESS" if attempt["success"] else "FAILED"
            action = attempt['action']
            reasoning = attempt.get('reasoning', '')[:100]
            lines.append(f"{status}: {action} - {reasoning}")
        return "\n".join(lines)
    
    def _parse_plan(self, plan_text: str, issue: Issue) -> List[Dict]:
        """Parse LLM response into structured plan"""
        import json
        
        json_match = re.search(r'\[.*\]', plan_text, re.DOTALL)
        if json_match:
            try:
                plan = json.loads(json_match.group())
                valid_actions = ["restart_pod", "update_env", "increase_memory", "fix_image_name"]
                validated_plan = []
                for step in plan:
                    if step.get("action") in valid_actions:
                        validated_plan.append(step)
                if validated_plan:
                    return validated_plan
            except json.JSONDecodeError:
                pass
        
        return [{
            "action": "restart_pod",
            "details": {"pod_name": issue.pod_name, "namespace": issue.namespace},
            "reasoning": "Could not parse AI plan, using fallback",
            "confidence": "low"
        }]
