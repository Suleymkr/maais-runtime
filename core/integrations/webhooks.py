"""
Webhook Integration for Real-time Alerts
"""
import json
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import aiohttp
import ssl
from enum import Enum
import logging

from core.models import ActionRequest, Decision


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertType(Enum):
    """Alert types"""
    POLICY_VIOLATION = "policy_violation"
    CIAA_VIOLATION = "ciaa_violation"
    ANOMALY_DETECTED = "anomaly_detected"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    ACCOUNTABILITY_FAILURE = "accountability_failure"
    AUDIT_TAMPERING = "audit_tampering"
    RUNTIME_ERROR = "runtime_error"


@dataclass
class Alert:
    """Security alert"""
    id: str
    type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    agent_id: str
    action_id: str
    timestamp: datetime
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data["type"] = self.type.value
        data["severity"] = self.severity.value
        data["timestamp"] = self.timestamp.isoformat()
        return data
    
    def to_slack(self) -> Dict:
        """Format for Slack webhook"""
        color_map = {
            AlertSeverity.INFO: "#36a64f",
            AlertSeverity.WARNING: "#ff9900",
            AlertSeverity.CRITICAL: "#ff0000",
            AlertSeverity.EMERGENCY: "#8b0000"
        }
        
        return {
            "attachments": [{
                "color": color_map[self.severity],
                "title": f"{self.severity.value.upper()}: {self.title}",
                "text": self.message,
                "fields": [
                    {
                        "title": "Agent ID",
                        "value": self.agent_id,
                        "short": True
                    },
                    {
                        "title": "Action ID",
                        "value": self.action_id,
                        "short": True
                    },
                    {
                        "title": "Alert Type",
                        "value": self.type.value,
                        "short": True
                    },
                    {
                        "title": "Timestamp",
                        "value": self.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
                        "short": True
                    }
                ],
                "footer": "MAAIS-Runtime Security Alert",
                "ts": self.timestamp.timestamp()
            }]
        }
    
    def to_discord(self) -> Dict:
        """Format for Discord webhook"""
        color_map = {
            AlertSeverity.INFO: 0x36a64f,
            AlertSeverity.WARNING: 0xff9900,
            AlertSeverity.CRITICAL: 0xff0000,
            AlertSeverity.EMERGENCY: 0x8b0000
        }
        
        return {
            "embeds": [{
                "title": f"{self.severity.value.upper()}: {self.title}",
                "description": self.message,
                "color": color_map[self.severity],
                "fields": [
                    {
                        "name": "Agent ID",
                        "value": self.agent_id,
                        "inline": True
                    },
                    {
                        "name": "Alert Type",
                        "value": self.type.value,
                        "inline": True
                    }
                ],
                "timestamp": self.timestamp.isoformat(),
                "footer": {
                    "text": "MAAIS-Runtime Security Alert"
                }
            }]
        }
    
    def to_teams(self) -> Dict:
        """Format for Microsoft Teams webhook"""
        return {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": "0076D7",
            "summary": f"{self.severity.value.upper()}: {self.title}",
            "sections": [{
                "activityTitle": f"{self.severity.value.upper()}: {self.title}",
                "activitySubtitle": self.message,
                "facts": [
                    {
                        "name": "Agent ID",
                        "value": self.agent_id
                    },
                    {
                        "name": "Action ID",
                        "value": self.action_id
                    },
                    {
                        "name": "Alert Type",
                        "value": self.type.value
                    },
                    {
                        "name": "Timestamp",
                        "value": self.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
                    }
                ],
                "markdown": True
            }]
        }


class WebhookConfig:
    """Webhook configuration"""
    
    def __init__(
        self,
        url: str,
        service: str = "custom",  # slack, discord, teams, custom
        enabled: bool = True,
        secret: Optional[str] = None,
        headers: Optional[Dict] = None,
        timeout: int = 5,
        retries: int = 3
    ):
        self.url = url
        self.service = service
        self.enabled = enabled
        self.secret = secret
        self.headers = headers or {"Content-Type": "application/json"}
        self.timeout = timeout
        self.retries = retries
        
        # Add auth headers if secret provided
        if secret:
            if service == "slack":
                self.headers["Authorization"] = f"Bearer {secret}"
            elif service == "custom":
                self.headers["X-API-Key"] = secret


class WebhookManager:
    """
    Manage webhook integrations for real-time alerts
    """
    
    def __init__(self):
        self.webhooks: Dict[str, WebhookConfig] = {}
        self.session: Optional[aiohttp.ClientSession] = None
        self.logger = logging.getLogger(__name__)
        
        # Alert templates
        self.templates = {
            AlertType.POLICY_VIOLATION: {
                "title": "Policy Violation Detected",
                "message": "Agent violated security policy: {policy_id}"
            },
            AlertType.CIAA_VIOLATION: {
                "title": "CIAA Violation Detected",
                "message": "Agent violated CIAA constraints: {violations}"
            },
            AlertType.ANOMALY_DETECTED: {
                "title": "Behavioral Anomaly Detected",
                "message": "Unusual agent behavior detected: {anomalies}"
            },
            AlertType.RATE_LIMIT_EXCEEDED: {
                "title": "Rate Limit Exceeded",
                "message": "Agent exceeded rate limits: {details}"
            }
        }
    
    def add_webhook(self, name: str, config: WebhookConfig):
        """Add a webhook configuration"""
        self.webhooks[name] = config
        self.logger.info(f"Added webhook: {name} -> {config.url}")
    
    def remove_webhook(self, name: str):
        """Remove a webhook"""
        if name in self.webhooks:
            del self.webhooks[name]
            self.logger.info(f"Removed webhook: {name}")
    
    def create_alert(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        agent_id: str,
        action_id: str,
        metadata: Dict[str, Any],
        custom_title: str = None,
        custom_message: str = None
    ) -> Alert:
        """Create an alert"""
        import uuid
        
        template = self.templates.get(alert_type, {"title": "Alert", "message": "Security event detected"})
        
        # Format message with metadata
        message = custom_message or template["message"]
        if metadata:
            try:
                message = message.format(**metadata)
            except KeyError:
                pass
        
        title = custom_title or template["title"]
        
        return Alert(
            id=str(uuid.uuid4()),
            type=alert_type,
            severity=severity,
            title=title,
            message=message,
            agent_id=agent_id,
            action_id=action_id,
            timestamp=datetime.utcnow(),
            metadata=metadata
        )
    
    async def send_alert(self, alert: Alert, webhook_name: str = None):
        """
        Send alert to webhooks
        
        Args:
            alert: Alert to send
            webhook_name: Specific webhook name, or None for all enabled
        """
        if not self.session:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            self.session = aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(ssl=ssl_context)
            )
        
        webhooks_to_send = []
        
        if webhook_name:
            if webhook_name in self.webhooks and self.webhooks[webhook_name].enabled:
                webhooks_to_send.append((webhook_name, self.webhooks[webhook_name]))
        else:
            # Send to all enabled webhooks
            webhooks_to_send = [
                (name, config) for name, config in self.webhooks.items()
                if config.enabled
            ]
        
        tasks = []
        for name, config in webhooks_to_send:
            tasks.append(self._send_to_webhook(alert, name, config))
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for name, success in results:
                if isinstance(success, Exception):
                    self.logger.error(f"Failed to send to webhook {name}: {success}")
                elif not success:
                    self.logger.warning(f"Webhook {name} returned non-2xx status")
                else:
                    self.logger.info(f"Alert sent to webhook {name}")
    
    async def _send_to_webhook(self, alert: Alert, name: str, config: WebhookConfig) -> tuple[str, bool]:
        """Send alert to a specific webhook"""
        try:
            # Format payload based on service
            if config.service == "slack":
                payload = alert.to_slack()
            elif config.service == "discord":
                payload = alert.to_discord()
            elif config.service == "teams":
                payload = alert.to_teams()
            else:
                payload = alert.to_dict()
            
            # Retry logic
            for attempt in range(config.retries):
                try:
                    async with self.session.post(
                        config.url,
                        json=payload,
                        headers=config.headers,
                        timeout=aiohttp.ClientTimeout(total=config.timeout)
                    ) as response:
                        if 200 <= response.status < 300:
                            return name, True
                        else:
                            self.logger.warning(
                                f"Webhook {name} returned {response.status} "
                                f"(attempt {attempt + 1}/{config.retries})"
                            )
                            
                            if attempt < config.retries - 1:
                                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                            else:
                                return name, False
                
                except asyncio.TimeoutError:
                    self.logger.warning(
                        f"Webhook {name} timeout (attempt {attempt + 1}/{config.retries})"
                    )
                    if attempt < config.retries - 1:
                        await asyncio.sleep(2 ** attempt)
                    else:
                        return name, False
                
                except Exception as e:
                    self.logger.error(f"Error sending to webhook {name}: {e}")
                    if attempt < config.retries - 1:
                        await asyncio.sleep(2 ** attempt)
                    else:
                        return name, False
        
        except Exception as e:
            self.logger.error(f"Unexpected error with webhook {name}: {e}")
            return name, False
    
    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None
    
    def get_webhook_status(self) -> Dict[str, Any]:
        """Get status of all webhooks"""
        status = {
            "total_webhooks": len(self.webhooks),
            "enabled_webhooks": sum(1 for w in self.webhooks.values() if w.enabled),
            "webhooks": {}
        }
        
        for name, config in self.webhooks.items():
            status["webhooks"][name] = {
                "url": config.url,
                "service": config.service,
                "enabled": config.enabled,
                "timeout": config.timeout,
                "retries": config.retries
            }
        
        return status


# Sync wrapper for async operations
class SyncWebhookManager(WebhookManager):
    """Synchronous wrapper for webhook manager"""
    
    def __init__(self):
        super().__init__()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    def send_alert_sync(self, alert: Alert, webhook_name: str = None):
        """Synchronous version of send_alert"""
        return self.loop.run_until_complete(self.send_alert(alert, webhook_name))
    
    def close_sync(self):
        """Synchronous close"""
        self.loop.run_until_complete(self.close())
        self.loop.close()