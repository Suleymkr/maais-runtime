"""
Enhanced MAAIS-Runtime with all advanced features
"""
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from core.models import ActionRequest, Decision
from core.multitenant.tenant_manager import MultiTenantRuntime, TenantManager
from core.engine.anomaly_detector import AnomalyDetector
from core.engine.advanced_rate_limiter import AdvancedRateLimiter
from core.integrations.webhooks import SyncWebhookManager
from core.learning.policy_learner import PolicyLearner
from core.optimization.cache import PolicyCache
from core.integrations.gitops import GitOpsManager


class EnhancedMAAISRuntime(MultiTenantRuntime):
    """
    Enhanced runtime with all advanced features:
    - Multi-tenant support
    - Machine learning anomaly detection
    - Advanced rate limiting
    - Webhook integrations
    - Policy learning
    - Performance caching
    - GitOps integration
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize enhanced runtime"""
        super().__init__()
        
        self.config = config or {}
        
        # Initialize advanced components
        self.anomaly_detector = AnomalyDetector()
        self.rate_limiter = AdvancedRateLimiter()
        self.webhook_manager = SyncWebhookManager()
        self.policy_learner = PolicyLearner()
        self.policy_cache = PolicyCache()
        self.gitops_manager = GitOpsManager()
        
        # Configure webhooks from config
        self._configure_webhooks()
        
        # Start GitOps watcher
        self.gitops_manager.start_watcher(interval=300)
        
        # Set components on parent
        self.set_anomaly_detector(self.anomaly_detector)
        self.set_webhook_manager(self.webhook_manager)
        
        print("Enhanced MAAIS-Runtime initialized with all features")
    
    def _configure_webhooks(self):
        """Configure webhooks from config"""
        webhooks_config = self.config.get("webhooks", [])
        
        for webhook_config in webhooks_config:
            from core.integrations.webhooks import WebhookConfig
            
            config = WebhookConfig(
                url=webhook_config["url"],
                service=webhook_config.get("service", "custom"),
                secret=webhook_config.get("secret"),
                timeout=webhook_config.get("timeout", 5),
                retries=webhook_config.get("retries", 3)
            )
            
            self.webhook_manager.add_webhook(webhook_config["name"], config)
    
    def intercept(self, action: ActionRequest) -> Decision:
        """Enhanced interception with all features"""
        # Check cache first
        action_hash = self._hash_action(action)
        cached_result = self.policy_cache.get_action_decision(
            action_hash, action.agent_id, action.action_type.value, action.target
        )
        
        if cached_result:
            allowed, reason = cached_result
            return Decision(
                allow=allowed,
                explanation=f"Cached: {reason}",
                timestamp=datetime.utcnow()
            )
        
        # Check rate limits
        allowed, rate_details = self.rate_limiter.check_rate_limit(
            action.agent_id, action.action_type.value, action.target
        )
        
        if not allowed:
            decision = Decision(
                allow=False,
                explanation=f"Rate limit exceeded: {rate_details.get('max_wait_time', 0):.1f}s wait",
                ciaa_violations={"A": "Rate limiting"},
                timestamp=datetime.utcnow()
            )
            
            # Cache the decision
            self.policy_cache.set_action_decision(
                action_hash, action.agent_id, action.action_type.value, action.target,
                False, decision.explanation
            )
            
            # Send alert
            self._send_rate_limit_alert(action, rate_details)
            
            return decision
        
        # Call parent implementation (multi-tenant evaluation)
        decision = super().intercept(action)
        
        # Cache the decision
        self.policy_cache.set_action_decision(
            action_hash, action.agent_id, action.action_type.value, action.target,
            decision.allow, decision.explanation
        )
        
        # Learn from blocked actions
        if not decision.allow:
            self.policy_learner.add_blocked_action(action, decision)
        
        # Update anomaly detector
        self.anomaly_detector.update_profile(
            action.agent_id, action, is_anomaly=not decision.allow
        )
        
        return decision
    
    def _hash_action(self, action: ActionRequest) -> str:
        """Create hash of action for caching"""
        import hashlib
        import json
        
        action_str = json.dumps({
            "agent_id": action.agent_id,
            "action_type": action.action_type.value,
            "target": action.target,
            "parameters": action.parameters,
            "goal": action.declared_goal
        }, sort_keys=True)
        
        return hashlib.sha256(action_str.encode()).hexdigest()
    
    def _send_rate_limit_alert(self, action: ActionRequest, rate_details: Dict):
        """Send rate limit alert"""
        from core.integrations.webhooks import AlertType, AlertSeverity
        
        alert = self.webhook_manager.create_alert(
            alert_type=AlertType.RATE_LIMIT_EXCEEDED,
            severity=AlertSeverity.WARNING,
            agent_id=action.agent_id,
            action_id=action.action_id,
            metadata={
                "action_type": action.action_type.value,
                "target": action.target,
                "rate_details": rate_details,
                "wait_time": rate_details.get("max_wait_time", 0)
            }
        )
        
        self.webhook_manager.send_alert_sync(alert)
    
    def get_insights(self, agent_id: str = None) -> Dict[str, Any]:
        """Get comprehensive insights"""
        insights = {
            "runtime": self.health_check(),
            "anomaly_detection": {},
            "rate_limiting": {},
            "policy_learning": {},
            "caching": {},
            "gitops": {}
        }
        
        # Agent-specific insights
        if agent_id:
            insights["agent"] = {
                "id": agent_id,
                "tenant": self.tenant_manager.get_tenant_for_agent(agent_id),
                "anomaly_profile": self.anomaly_detector.get_agent_insights(agent_id),
                "rate_stats": self.rate_limiter.get_agent_rate_stats(agent_id)
            }
        
        # Anomaly detection insights
        insights["anomaly_detection"] = {
            "profiles_count": len(self.anomaly_detector.profiles),
            "training_samples": len(self.anomaly_detector.training_window),
            "model_loaded": self.anomaly_detector.model is not None
        }
        
        # Rate limiting insights
        insights["rate_limiting"] = self.rate_limiter.get_limits_summary()
        
        # Policy learning insights
        insights["policy_learning"] = self.policy_learner.get_learning_stats()
        insights["policy_learning"]["suggestions"] = [
            s.to_dict() for s in self.policy_learner.get_suggestions(min_confidence=0.3)[:5]
        ]
        
        # Caching insights
        insights["caching"] = self.policy_cache.get_stats()
        
        # GitOps insights
        insights["gitops"] = self.gitops_manager.get_status()
        
        return insights
    
    def export_learned_policies(self, filepath: str = "learned_policies.yaml"):
        """Export learned policies as YAML"""
        self.policy_learner.export_suggestions(filepath)
    
    def sync_git_repositories(self, force: bool = False) -> Dict[str, Any]:
        """Sync all Git repositories"""
        results = {}
        
        for repo_name in list(self.gitops_manager.repos.keys()):
            result = self.gitops_manager.sync_repository(repo_name, force)
            results[repo_name] = result
        
        return results
    
    def shutdown(self):
        """Clean shutdown of all components"""
        print("Shutting down Enhanced MAAIS-Runtime...")
        
        # Stop GitOps watcher
        self.gitops_manager.stop_watcher()
        
        # Close webhook manager
        self.webhook_manager.close_sync()
        
        # Save anomaly detector profiles
        self.anomaly_detector.save_profiles()
        
        # Export learned policies
        self.export_learned_policies()
        
        print("Enhanced MAAIS-Runtime shutdown complete")


# Singleton instance
_enhanced_runtime_instance = None

def get_enhanced_runtime(config: Dict = None) -> EnhancedMAAISRuntime:
    """Get or create enhanced runtime instance"""
    global _enhanced_runtime_instance
    if _enhanced_runtime_instance is None:
        _enhanced_runtime_instance = EnhancedMAAISRuntime(config)
    return _enhanced_runtime_instance