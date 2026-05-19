"""
Memory System for Agentic AI
Stores past issues, remediation attempts, and success rates
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class Issue:
    """Represents a Kubernetes issue"""
    pod_name: str
    namespace: str
    status: str
    reason: str
    message: str
    timestamp: str
    container_name: Optional[str] = None


@dataclass
class RemediationAttempt:
    """Represents a remediation attempt and its outcome"""
    issue: Issue
    action: str
    action_details: Dict
    success: bool
    timestamp: str
    reasoning: str


class Memory:
    """Persistent memory for learning from past remediations"""
    
    def __init__(self, memory_file: str = "agentic_memory.json"):
        self.memory_file = memory_file
        self.memory = self._load_memory()
    
    def _load_memory(self) -> Dict:
        """Load memory from file"""
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print(f"WARNING: Could not parse {self.memory_file}, starting fresh")
                return {"attempts": [], "patterns": {}}
        return {"attempts": [], "patterns": {}}
    
    def _save_memory(self):
        """Save memory to file"""
        with open(self.memory_file, 'w') as f:
            json.dump(self.memory, f, indent=2)
    
    def store_attempt(self, attempt: RemediationAttempt):
        """Store a remediation attempt"""
        attempt_dict = {
            "issue": asdict(attempt.issue),
            "action": attempt.action,
            "action_details": attempt.action_details,
            "success": attempt.success,
            "timestamp": attempt.timestamp,
            "reasoning": attempt.reasoning
        }
        self.memory["attempts"].append(attempt_dict)
        
        if attempt.success:
            self._update_patterns(attempt)
        
        self._save_memory()
    
    def _update_patterns(self, attempt: RemediationAttempt):
        """Learn patterns from successful remediations"""
        if attempt.success:
            pattern_key = f"{attempt.issue.status}_{attempt.issue.reason}"
            
            if pattern_key not in self.memory["patterns"]:
                self.memory["patterns"][pattern_key] = {
                    "successful_actions": [],
                    "success_count": 0,
                    "total_count": 0
                }
            
            pattern = self.memory["patterns"][pattern_key]
            pattern["total_count"] += 1
            pattern["success_count"] += 1
            
            action_entry = {
                "action": attempt.action,
                "details": attempt.action_details,
                "reasoning": attempt.reasoning
            }
            pattern["successful_actions"].append(action_entry)
    
    def recall_similar(self, issue: Issue) -> Optional[Dict]:
        """Recall successful remediations for similar issues"""
        pattern_key = f"{issue.status}_{issue.reason}"
        
        if pattern_key in self.memory["patterns"]:
            pattern = self.memory["patterns"][pattern_key]
            if pattern["success_count"] > 0:
                # Return most recent successful action
                return pattern["successful_actions"][-1]
        
        return None
    
    def get_success_rate(self, pattern_key: str) -> float:
        """Get success rate for a pattern"""
        if pattern_key in self.memory["patterns"]:
            pattern = self.memory["patterns"][pattern_key]
            if pattern["total_count"] > 0:
                return pattern["success_count"] / pattern["total_count"]
        return 0.0
    
    def get_history(self, pod_name: str) -> List[Dict]:
        """Get remediation history for a specific pod"""
        return [
            attempt for attempt in self.memory["attempts"]
            if attempt["issue"]["pod_name"] == pod_name
        ]
    
    def get_statistics(self) -> Dict:
        """Get memory statistics"""
        total_attempts = len(self.memory["attempts"])
        successful_attempts = sum(1 for a in self.memory["attempts"] if a["success"])
        
        return {
            "total_attempts": total_attempts,
            "successful_attempts": successful_attempts,
            "success_rate": successful_attempts / total_attempts if total_attempts > 0 else 0,
            "patterns_learned": len(self.memory["patterns"])
        }
