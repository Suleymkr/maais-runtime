"""
Accountability Resolver
Ensures every action has responsible ownership
"""
from typing import Optional
from core.models import ActionRequest


class AccountabilityResolver:
    """Resolves responsibility for actions"""
    
    def __init__(self):
        # In production, load from configuration/database
        self.agent_owners = {
            "data_processor": "data_team",
            "report_generator": "analytics_team",
            "api_client": "integration_team",
            "*": "system_admin"  # Default owner
        }
    
    def resolve(self, action: ActionRequest, policy_id: Optional[str]) -> Optional[str]:
        """
        Resolve responsibility owner for action.
        Returns owner string or None if unresolvable.
        """
        # Check for specific agent owner
        owner = self.agent_owners.get(action.agent_id)
        
        # Fall back to default owner
        if owner is None:
            owner = self.agent_owners.get("*")
        
        # Special case: if policy denied and no explicit owner, still deny
        if policy_id and owner == "system_admin":
            # System admin takes responsibility for policy violations
            return owner
        
        return owner
    
    def register_agent_owner(self, agent_id: str, owner: str) -> None:
        """Register ownership for an agent"""
        self.agent_owners[agent_id] = owner