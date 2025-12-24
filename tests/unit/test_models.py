"""
Unit tests for core models
"""
import pytest
from datetime import datetime
from core.models import ActionRequest, ActionType, Decision


def test_action_request_creation():
    """Test ActionRequest creation and validation"""
    action = ActionRequest(
        agent_id="test_agent",
        action_type=ActionType.TOOL_CALL,
        target="http_request",
        parameters={"url": "https://api.example.com"},
        declared_goal="Fetch data from API"
    )
    
    assert action.agent_id == "test_agent"
    assert action.action_type == ActionType.TOOL_CALL
    assert action.target == "http_request"
    assert "url" in action.parameters
    assert action.action_id  # Should be auto-generated


def test_action_request_validation():
    """Test ActionRequest validation"""
    with pytest.raises(ValueError):
        ActionRequest(
            agent_id="",  # Empty agent_id
            action_type=ActionType.TOOL_CALL,
            target="test",
            parameters={},
            declared_goal="test"
        )
    
    with pytest.raises(ValueError):
        ActionRequest(
            agent_id="test",
            action_type=ActionType.TOOL_CALL,
            target="",  # Empty target
            parameters={},
            declared_goal="test"
        )


def test_decision_creation():
    """Test Decision creation"""
    decision = Decision(
        allow=False,
        policy_id="deny_external_http",
        explanation="External HTTP blocked",
        ciaa_violations={"C": "Sensitive data detected"}
    )
    
    assert decision.allow == False
    assert decision.policy_id == "deny_external_http"
    assert "C" in decision.ciaa_violations
    assert decision.timestamp  # Should be auto-generated


def test_decision_to_dict():
    """Test Decision serialization"""
    decision = Decision(
        allow=True,
        explanation="Allowed"
    )
    
    data = decision.to_dict()
    assert data["allow"] == True
    assert data["explanation"] == "Allowed"
    assert "timestamp" in data