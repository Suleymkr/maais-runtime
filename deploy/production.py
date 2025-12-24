"""
Production Deployment Script for MAAIS-Runtime
"""
import os
import sys
import json
import yaml
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.runtime_enhanced import get_enhanced_runtime


def setup_logging(log_dir: str = "logs"):
    """Setup production logging"""
    log_dir = Path(log_dir)
    log_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # File handler (rotating, 10MB max, keep 5 files)
    file_handler = RotatingFileHandler(
        log_dir / "maais_runtime.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def load_config(config_file: str = "config/production.yaml") -> dict:
    """Load production configuration"""
    config_path = Path(config_file)
    
    if not config_path.exists():
        # Create default config
        default_config = {
            "runtime": {
                "max_cache_size": 10000,
                "enable_ml": True,
                "enable_gitops": True,
                "webhooks": [
                    {
                        "name": "security_alerts",
                        "url": os.getenv("WEBHOOK_URL", ""),
                        "service": "slack",
                        "secret": os.getenv("WEBHOOK_SECRET", "")
                    }
                ]
            },
            "tenants": {
                "default": {
                    "name": "Default Tenant",
                    "policy_files": ["policies/static/security_policies.yaml"],
                    "rate_limits": {
                        "global": {"requests_per_second": 1000, "burst_size": 5000},
                        "per_agent": {"requests_per_second": 100, "burst_size": 500}
                    }
                }
            },
            "gitops": {
                "enabled": True,
                "repositories": [
                    {
                        "name": "security_policies",
                        "repo_url": os.getenv("POLICIES_REPO", ""),
                        "branch": "main",
                        "path": "policies/",
                        "sync_interval": 300
                    }
                ]
            },
            "monitoring": {
                "prometheus_enabled": True,
                "metrics_port": 9090,
                "health_check_interval": 30
            }
        }
        
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False)
        
        print(f"Created default config at {config_path}")
        return default_config
    
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def setup_tenants(runtime, config: dict):
    """Setup tenants from config"""
    for tenant_id, tenant_config in config.get("tenants", {}).items():
        if tenant_id == "default":
            # Update default tenant
            runtime.tenant_manager.update_tenant(
                tenant_id="default",
                name=tenant_config.get("name", "Default Tenant"),
                policy_files=tenant_config.get("policy_files", []),
                metadata={"rate_limits": tenant_config.get("rate_limits", {})}
            )
        else:
            # Create new tenant
            runtime.tenant_manager.create_tenant(
                name=tenant_config["name"],
                description=tenant_config.get("description", ""),
                policy_files=tenant_config.get("policy_files", []),
                rate_limits=tenant_config.get("rate_limits", {}),
                metadata=tenant_config.get("metadata", {})
            )
    
    print(f"Setup {len(config.get('tenants', {}))} tenants")


def setup_gitops(runtime, config: dict):
    """Setup GitOps from config"""
    gitops_config = config.get("gitops", {})
    
    if not gitops_config.get("enabled", True):
        print("GitOps disabled")
        return
    
    # Clear existing repos
    for repo_name in list(runtime.gitops_manager.repos.keys()):
        if repo_name != "default_policies":
            runtime.gitops_manager.remove_repository(repo_name)
    
    # Add repos from config
    for repo_config in gitops_config.get("repositories", []):
        from core.integrations.gitops import GitConfig
        
        config = GitConfig(
            name=repo_config["name"],
            repo_url=repo_config["repo_url"],
            branch=repo_config.get("branch", "main"),
            path=repo_config.get("path", "policies/"),
            sync_interval=repo_config.get("sync_interval", 300),
            auth_token=os.getenv(f"GIT_TOKEN_{repo_config['name'].upper()}", None)
        )
        
        runtime.gitops_manager.add_repository(config)
    
    # Initial sync
    print("Performing initial GitOps sync...")
    results = runtime.sync_git_repositories(force=True)
    
    for repo_name, result in results.items():
        if result.get("success"):
            print(f"  {repo_name}: Synced {len(result.get('policy_files', []))} policy files")
        else:
            print(f"  {repo_name}: Failed - {result.get('error', 'Unknown error')}")


def setup_webhooks(runtime, config: dict):
    """Setup webhooks from config"""
    webhooks = config.get("runtime", {}).get("webhooks", [])
    
    for webhook_config in webhooks:
        from core.integrations.webhooks import WebhookConfig
        
        config = WebhookConfig(
            url=webhook_config["url"],
            service=webhook_config.get("service", "custom"),
            secret=webhook_config.get("secret"),
            timeout=webhook_config.get("timeout", 5),
            retries=webhook_config.get("retries", 3),
            enabled=webhook_config.get("enabled", True)
        )
        
        runtime.webhook_manager.add_webhook(webhook_config["name"], config)
    
    print(f"Setup {len(webhooks)} webhooks")


def start_metrics_server(port: int = 9090):
    """Start Prometheus metrics server (optional)"""
    try:
        from prometheus_client import start_http_server, Counter, Gauge, Histogram
        import threading
        
        # Define metrics
        ACTIONS_TOTAL = Counter(
            'maais_actions_total',
            'Total number of actions processed',
            ['agent_id', 'action_type', 'decision']
        )
        
        ACTION_DURATION = Histogram(
            'maais_action_duration_seconds',
            'Duration of action processing',
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
        )
        
        AGENTS_ACTIVE = Gauge(
            'maais_agents_active',
            'Number of active agents'
        )
        
        def metrics_middleware(action, decision, duration):
            """Update metrics"""
            ACTIONS_TOTAL.labels(
                agent_id=action.agent_id,
                action_type=action.action_type.value,
                decision='allowed' if decision.allow else 'blocked'
            ).inc()
            
            ACTION_DURATION.observe(duration)
        
        # Start metrics server
        start_http_server(port)
        print(f"Metrics server started on port {port}")
        
        return metrics_middleware
    
    except ImportError:
        print("Prometheus client not installed, metrics disabled")
        return None


def main():
    """Main deployment entry point"""
    print("""
    🚀 MAAIS-Runtime Production Deployment
    ======================================
    """)
    
    # Setup logging
    logger = setup_logging()
    logger.info("Starting MAAIS-Runtime production deployment")
    
    # Load configuration
    config = load_config()
    logger.info(f"Loaded configuration from {config.get('__file__', 'config/production.yaml')}")
    
    # Initialize enhanced runtime
    runtime = get_enhanced_runtime(config)
    
    # Setup components
    setup_tenants(runtime, config)
    setup_gitops(runtime, config)
    setup_webhooks(runtime, config)
    
    # Start metrics server if enabled
    metrics_middleware = None
    if config.get("monitoring", {}).get("prometheus_enabled", False):
        metrics_port = config["monitoring"].get("metrics_port", 9090)
        metrics_middleware = start_metrics_server(metrics_port)
    
    # Health check
    health = runtime.health_check()
    logger.info(f"Runtime health: {health['status']}")
    logger.info(f"Active tenants: {health['active_tenants']}")
    
    # Get insights
    insights = runtime.get_insights()
    logger.info(f"Initial insights: {insights.get('policy_learning', {}).get('patterns_learned', 0)} patterns learned")
    
    print("""
    ✅ MAAIS-Runtime Production Deployment Complete!
    
    Components Running:
    - Multi-tenant security runtime
    - ML anomaly detection
    - Advanced rate limiting
    - Webhook integrations
    - Policy learning engine
    - GitOps policy management
    
    Next Steps:
    1. Register agents with runtime.register_agent()
    2. Monitor dashboard at http://localhost:8501
    3. Check metrics at http://localhost:9090
    4. View logs in logs/ directory
    
    Press Ctrl+C to shutdown gracefully.
    """)
    
    # Keep running
    try:
        import time
        while True:
            # Periodic health check
            if hasattr(runtime, 'health_check'):
                health = runtime.health_check()
                if health.get('status') != 'healthy':
                    logger.error(f"Runtime health degraded: {health}")
            
            time.sleep(60)  # Check every minute
    
    except KeyboardInterrupt:
        print("\n🛑 Received shutdown signal")
    
    finally:
        # Graceful shutdown
        runtime.shutdown()
        logger.info("MAAIS-Runtime shutdown complete")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())