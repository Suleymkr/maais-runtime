---
layout: default
title: Getting Started
nav_order: 2
---

# Getting Started with MAAIS-Runtime

Welcome to MAAIS-Runtime! This guide will help you understand the core concepts and get your first AI agents secured in minutes.

## 📚 What is MAAIS-Runtime?

MAAIS-Runtime is a **security enforcement layer** that sits between your AI agents and their actions. Think of it as a **security bouncer** that:

1. **Intercepts** every action your AI agent tries to perform
2. **Evaluates** it against security policies
3. **Enforces** decisions before execution
4. **Logs** everything immutably for audit

### How It Works

```
┌─────────────┐    ┌─────────────────┐    ┌─────────────┐
│    AI Agent │────▶ ActionRequest   │────▶ MAAIS       │
│             │    │                 │    │ Runtime     │
└─────────────┘    └─────────────────┘    └──────┬──────┘
                                                  │
           ┌──────────────────────────────────────┘
           ▼
┌─────────────────────────────────┐
│        Security Evaluation      │
│  • Policy Engine (YAML rules)   │
│  • CIAA Constraints             │
│  • Accountability Resolution    │
└─────────────────┬───────────────┘
                  │
           ┌──────▼──────┐    ┌─────────────┐
           │   Decision  │────▶ Execute or  │
           │             │    │   Block     │
           └─────────────┘    └─────────────┘
```

## 🎯 Key Concepts

### 1. Action Interception
Every agent action (tool calls, API calls, memory access) is converted into an `ActionRequest` object and passed through the security runtime.

### 2. Policy-Based Evaluation
Security policies are defined in YAML and evaluated deterministically:
```yaml
- id: "deny_external_http"
  applies_to: ["tool_call"]
  condition:
    target: "http_request"
    parameters:
      url:
        pattern: "^(https?://)(?!localhost|127.0.0.1|internal\.).*"
  decision: "DENY"
  reason: "External HTTP requests forbidden"
```

### 3. CIAA Constraints
Each action is evaluated against:
- **Confidentiality**: Prevent data exfiltration
- **Integrity**: Block unauthorized modifications  
- **Availability**: Prevent resource abuse
- **Accountability**: Ensure responsibility assignment

### 4. Immutable Audit Logging
All decisions are logged in a hash-chained, tamper-evident audit trail.

## 🚀 Quick Installation

```bash
# Basic
pip install maais-runtime

# From source
git clone https://github.com/MasterCaleb254/maais-runtime.git
cd maais-runtime
pip install -e .
```

## 📝 Your First Secured Agent

```python
from langgraph.graph import StateGraph
from core.adapters.langgraph_adapter import secure_tool

@secure_tool(agent_id="calculator", goal="Perform calculations")
def calculator_tool(operation: str, a: float, b: float) -> float:
    if operation == "add":
        return a + b
    elif operation == "subtract":
        return a - b

# All calls to calculator_tool go through the security runtime
```

## 🧪 Test Your Setup

Run the security demo to verify everything works:

```bash
python -m demo.scenarios.attack_scenarios
```
