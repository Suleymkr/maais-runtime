// MAAIS-Runtime Interactive Features
document.addEventListener('DOMContentLoaded', function() {
  // Add copy buttons to code blocks
  document.querySelectorAll('pre code').forEach((block) => {
    const button = document.createElement('button');
    button.className = 'copy-btn';
    button.innerHTML = '📋';
    button.title = 'Copy to clipboard';
    
    button.addEventListener('click', () => {
      navigator.clipboard.writeText(block.textContent)
        .then(() => {
          button.innerHTML = '✅';
          setTimeout(() => {
            button.innerHTML = '📋';
          }, 2000);
        })
        .catch(err => {
          console.error('Failed to copy:', err);
          button.innerHTML = '❌';
        });
    });
    
    const pre = block.parentElement;
    if (pre) {
      pre.style.position = 'relative';
      button.style.position = 'absolute';
      button.style.top = '8px';
      button.style.right = '8px';
      button.style.background = 'transparent';
      button.style.border = 'none';
      button.style.cursor = 'pointer';
      button.style.fontSize = '16px';
      pre.appendChild(button);
    }
  });
  
  // Smooth scrolling for anchor links
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
      e.preventDefault();
      const targetId = this.getAttribute('href');
      if (targetId === '#') return;
      
      const targetElement = document.querySelector(targetId);
      if (targetElement) {
        window.scrollTo({ top: targetElement.offsetTop - 80, behavior: 'smooth' });
      }
    });
  });
  
  // Demo simulation data
  window.simulateSecurityCheck = function(agent, action, target, params) {
    const dangerousTargets = ['http_request', 'execute_command', 'write_file', 'system_call'];
    const safeAgents = ['data_processor', 'calculator', 'formatter', 'analytics_agent'];
    
    let isAllowed = true;
    let reason = '';
    let violations = [];
    let policy = '';
    
    if (dangerousTargets.includes(target)) {
      isAllowed = false;
      reason = `Dangerous target detected: ${target}`;
      violations.push('C: Potential data exfiltration');
      policy = 'deny_dangerous_operations';
    }
    
    if (agent === 'malicious_agent') {
      isAllowed = false;
      reason = 'Agent has malicious history';
      violations.push('A: Accountability failure');
      policy = 'block_malicious_agents';
    }
    
    try {
      const paramsObj = JSON.parse(params);
      if (paramsObj.url && !paramsObj.url.includes('localhost') && !paramsObj.url.includes('127.0.0.1') && paramsObj.url.includes('http')) {
        isAllowed = false;
        reason = 'External network access detected';
        violations.push('C: External data transfer');
        policy = 'deny_external_http';
      }
      const paramStr = JSON.stringify(paramsObj).toLowerCase();
      const sensitivePatterns = ['password', 'secret', 'token', 'key', 'credit', 'ssn'];
      if (sensitivePatterns.some(pattern => paramStr.includes(pattern))) {
        isAllowed = false;
        reason = 'Sensitive data detected in parameters';
        violations.push('C: Confidentiality breach');
        policy = 'block_sensitive_data';
      }
    } catch (e) {
      isAllowed = false;
      reason = 'Invalid parameter format';
      violations.push('I: Parameter validation failed');
      policy = 'block_invalid_parameters';
    }
    
    if (target === 'database_query') {
      const queryCount = Math.floor(Math.random() * 100);
      if (queryCount > 50) {
        isAllowed = false;
        reason = `Rate limit exceeded (${queryCount} queries in last minute)`;
        violations.push('A: Resource abuse');
        policy = 'limit_db_queries';
      }
    }
    
    if (isAllowed) {
      return `\n        <div class="result allowed">\n          <h4>✅ Action ALLOWED</h4>\n          <div class="result-details">\n            <p><strong>Agent:</strong> ${agent}</p>\n            <p><strong>Action:</strong> ${action}</p>\n            <p><strong>Target:</strong> ${target}</p>\n            <p><strong>Policy Applied:</strong> allow_safe_operations</p>\n            <p><strong>Accountability:</strong> ${agent.replace('_', ' ')}_team</p>\n            <p><strong>Audit Logged:</strong> Yes (Hash: ${generateHash()})</p>\n            <p><strong>Decision Time:</strong> 2.3ms</p>\n          </div>\n        </div>\n      `;
    } else {
      return `\n        <div class="result blocked">\n          <h4>❌ Action BLOCKED</h4>\n          <div class="result-details">\n            <p><strong>Agent:</strong> ${agent}</p>\n            <p><strong>Action:</strong> ${action}</p>\n            <p><strong>Target:</strong> ${target}</p>\n            <p><strong>Reason:</strong> ${reason}</p>\n            <p><strong>Policy Violated:</strong> ${policy}</p>\n            <p><strong>CIAA Violations:</strong> ${violations.join(', ')}</p>\n            <p><strong>MITRE ATLAS:</strong> ${getMitreTactic(policy)}</p>\n            <p><strong>Audit Logged:</strong> Yes (Hash: ${generateHash()})</p>\n            <p><strong>Alert Sent:</strong> Security team notified</p>\n          </div>\n        </div>\n      `;
    }
  };
  
  function generateHash() {
    return Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
  }
  
  function getMitreTactic(policy) {
    const mitreMap = {
      'deny_external_http': 'Initial Access (T1199)',
      'deny_dangerous_operations': 'Execution (T1059)',
      'block_malicious_agents': 'Defense Evasion (T1027)',
      'block_sensitive_data': 'Exfiltration (T1041)',
      'limit_db_queries': 'Impact (T1499)'
    };
    return mitreMap[policy] || 'Tactic mapping available';
  }
});
