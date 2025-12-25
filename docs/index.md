---
layout: default
title: MAAIS-Runtime
subtitle: Real-time Security for Autonomous AI Agents
hero_image: /maais-runtime/images/hero-bg.png
cta_text: Get Started
cta_link: /maais-runtime/getting-started
---

<div class="hero">
  <div class="hero-content">
    <h1>🛡️ MAAIS-Runtime</h1>
    <h2>Enterprise-grade security enforcement for LangGraph, CrewAI, and AutoGen</h2>
    <p>Stop AI agents from going rogue. Real-time interception, policy enforcement, and immutable audit trails for autonomous AI systems.</p>
    
    <div class="hero-buttons">
      <a href="/maais-runtime/getting-started" class="btn btn-primary">
        🚀 Get Started
      </a>
      <a href="/maais-runtime/demo" class="btn btn-secondary">
        🎯 Live Demo
      </a>
      <a href="{{ site.repo_url }}" class="btn btn-outline" target="_blank">
        ⭐ Star on GitHub
      </a>
    </div>
    
    <div class="badges">
      <img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+">
      <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="MIT License">
      <img src="https://img.shields.io/badge/spec-1.0-compliant-brightgreen" alt="SPEC-1 Compliant">
      <img src="https://img.shields.io/badge/security-production-red" alt="Production Ready">
    </div>
  </div>
</div>

## 🎯 Why MAAIS-Runtime?

Modern AI agents can autonomously call APIs, execute code, and access data. Without proper security, they can:
- **Exfiltrate sensitive data** via HTTP requests
- **Execute unauthorized commands** on your systems  
- **Bypass compliance requirements** and governance
- **Cause resource exhaustion** through abuse

MAAIS-Runtime provides **real-time, inline security enforcement** that intercepts every action before execution.

<div class="features-grid">
  <div class="feature-card">
    <div class="feature-icon">🔒</div>
    <h3>Real-time Interception</h3>
    <p>Intercept and evaluate every AI agent action before execution. No bypass possible.</p>
  </div>
  
  <div class="feature-card">
    <div class="feature-icon">⚡</div>
    <h3>CIAA Enforcement</h3>
    <p>Enforce Confidentiality, Integrity, Availability, and Accountability constraints.</p>
  </div>
  
  <div class="feature-card">
    <div class="feature-icon">📊</div>
    <h3>Immutable Audit Trails</h3>
    <p>Hash-chained, tamper-evident logs with MITRE ATLAS mapping.</p>
  </div>
  
  <div class="feature-card">
    <div class="feature-icon">🤖</div>
    <h3>Framework Agnostic</h3>
    <p>Works with LangGraph, CrewAI, AutoGen, and any Python-based agent framework.</p>
  </div>
</div>

## 🚀 Quick Start

```bash
# Install MAAIS-Runtime
pip install maais-runtime

# Secure your AI agents
from core.runtime import get_runtime
from core.models import ActionRequest, ActionType

runtime = get_runtime()

# All agent actions go through security
action = ActionRequest(
    agent_id="data_processor",
    action_type=ActionType.TOOL_CALL,
    target="http_request",
    parameters={"url": "https://api.example.com"},
    declared_goal="Fetch data"
)

decision = runtime.intercept(action)  # ✅ Security evaluation
```

<div class="cta-section">
  <h2>Ready to Secure Your AI Agents?</h2>
  <p>Join hundreds of developers who trust MAAIS-Runtime for their production AI systems.</p>
  <a href="/maais-runtime/installation" class="btn btn-large">
    📦 Install Now
  </a>
</div>

---

<div class="testimonial">
  <blockquote>
    "MAAIS-Runtime prevented a data exfiltration attempt by our AI agent that would have cost us millions in compliance fines. It's now mandatory for all our AI deployments."
    <cite>– Security Lead, Fortune 500 Company</cite>
  </blockquote>
</div>
