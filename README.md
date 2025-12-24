# MAAIS-Runtime: Agentic AI Security Runtime

A real-time security enforcement layer for agentic AI systems that intercepts and evaluates every action before execution.

## 🚀 Features

- **Real-time Action Interception**: Inline security evaluation before execution
- **Policy-based Enforcement**: YAML-defined security policies
- **CIAA Constraints**: Confidentiality, Integrity, Availability, Accountability
- **Immutable Audit Logs**: Hash-chained append-only logging
- **Fail-Closed Design**: No execution without security clearance

## 🏗️ Architecture
Agent → ActionRequest → MAAIS Runtime → Decision → Execute | Block
↳ Policy Engine
↳ CIAA Evaluator
↳ Accountability Resolver
↳ Audit Logger


## 📦 Installation

```bash
# Clone repository
git clone https://github.com/MasterCaleb254/maais-runtime.git
cd maais-runtime

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

🚀 Quick Start
python
from core.runtime import get_runtime
from core.models import ActionRequest, ActionType

# Get runtime instance
runtime = get_runtime()

# Create action request
action = ActionRequest(
    agent_id="data_processor",
    action_type=ActionType.TOOL_CALL,
    target="http_request",
    parameters={"url": "https://api.example.com/data"},
    declared_goal="Fetch external data"
)

# Intercept and evaluate
decision = runtime.intercept(action)

if decision.allow:
    print("Action allowed!")
else:
    print(f"Action blocked: {decision.explanation}")
📝 Policy Configuration
See policies/static/security_policies.yaml for examples:

yaml
- id: "deny_external_http"
  applies_to: ["tool_call"]
  condition:
    target: "http_request"
    parameters:
      url:
        pattern: "^(https?://)(?!localhost|127.0.0.1|internal\.).*"
  decision: "DENY"
  reason: "External HTTP requests forbidden"
🧪 Testing
bash
# Run unit tests
pytest tests/unit/

# Run integration tests  
pytest tests/integration/

# Test runtime directly
python test_runtime.py
📊 Dashboard
bash
# Launch Streamlit dashboard
streamlit run dashboard/audit_viewer.py
🔧 Components
ActionInterceptor: Main interception gateway

PolicyEngine: YAML policy evaluation

CIAAEvaluator: Confidentiality, Integrity, Availability checks

AccountabilityResolver: Responsibility assignment

AuditLogger: Immutable hash-chained logging

LangGraphAdapter: Framework integration

📈 Roadmap
Core models and runtime

Basic policy engine

CIAA evaluator

LangGraph integration

Streamlit dashboard

Advanced rate limiting

Machine learning policy suggestions

🤝 Contributing
Fork the repository

Create a feature branch

Add tests for new functionality

Submit a pull request

📄 License
MIT License - see LICENSE file

text

## **Step 14: Run Initial Tests**

```bash
# Activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run tests
python test_runtime.py