"""
Enhanced Policy Engine with MITRE ATLAS integration
"""
import yaml
from typing import Dict, Any, Optional, List
from pathlib import Path

from core.engine.policy_engine import PolicyEngine
from core.models import ActionRequest, PolicyRule


class MITREPolicyEngine(PolicyEngine):
    """Policy engine with MITRE ATLAS integration"""
    
    def __init__(self, policy_file: str = "policies/static/mitre_policies.yaml"):
        super().__init__(policy_file)
        self.mitre_techniques = self._load_mitre_techniques()
    
    def _load_mitre_techniques(self) -> Dict[str, Dict]:
        """Load MITRE ATLAS techniques metadata"""
        # In production, this would load from MITRE API or local database
        return {
            "T1199": {
                "name": "Trusted Relationship",
                "tactic": "Initial Access",
                "description": "Adversary uses trusted third-party relationship for access"
            },
            "T1059": {
                "name": "Command and Scripting Interpreter",
                "tactic": "Execution",
                "description": "Adversary leverages command and scripting interpreters"
            },
            # Add more techniques as needed
        }
    
    def evaluate_with_mitre(self, action: ActionRequest) -> tuple[Optional[str], Optional[Dict]]:
        """
        Evaluate action and return MITRE metadata
        
        Returns:
            Tuple of (policy_id, mitre_metadata) if denied
        """
        denied_policy = self.evaluate(action)
        
        if denied_policy:
            # Find the policy and extract MITRE metadata
            for policy in self.policies:
                if policy.id == denied_policy:
                    mitre_data = policy.metadata.get('mitre', {}) if hasattr(policy, 'metadata') else {}
                    return denied_policy, mitre_data
        
        return denied_policy, None
    
    def get_mitre_summary(self) -> Dict[str, List]:
        """Get summary of MITRE techniques covered by policies"""
        summary = {
            "tactics": {},
            "techniques": [],
            "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0}
        }
        
        for policy in self.policies:
            if hasattr(policy, 'metadata'):
                metadata = policy.metadata
                
                # Count by tactic
                tactic = metadata.get('mitre_tactic')
                if tactic:
                    summary["tactics"][tactic] = summary["tactics"].get(tactic, 0) + 1
                
                # Collect techniques
                technique = metadata.get('mitre_technique')
                if technique:
                    summary["techniques"].append({
                        "id": technique,
                        "name": self.mitre_techniques.get(technique, {}).get('name', 'Unknown'),
                        "tactic": metadata.get('mitre_tactic'),
                        "severity": metadata.get('severity', 'medium'),
                        "policy_id": policy.id
                    })
                
                # Count by severity
                severity = metadata.get('severity')
                if severity in summary["severity_counts"]:
                    summary["severity_counts"][severity] += 1
        
        return summary