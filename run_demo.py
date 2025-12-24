#!/usr/bin/env python3
"""
MAAIS-Runtime Complete Demo
Runs all components and launches dashboard
"""
import sys
import subprocess
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def run_attack_scenarios():
    """Run attack scenarios in background"""
    print("🚀 Starting attack scenarios...")
    from demo.scenarios.attack_scenarios import main as run_scenarios
    run_scenarios()

def launch_dashboard():
    """Launch Streamlit dashboard"""
    print("📊 Launching security dashboard...")
    subprocess.run(["streamlit", "run", "dashboard/audit_viewer.py"])

def main():
    """Main demo orchestrator"""
    print("""
    🛡️ MAAIS-Runtime - Agentic AI Security Runtime
    ==============================================
    
    This demo will:
    1. Run attack scenarios to generate security events
    2. Launch the security dashboard for visualization
    3. Show real-time security enforcement
    
    Components:
    - LangGraph integration with secure tools
    - MITRE ATLAS policy mapping
    - Real-time interception and blocking
    - Immutable audit logging
    - Streamlit dashboard
    
    Press Ctrl+C to stop all components
    """)
    
    try:
        # Run attack scenarios in background thread
        attack_thread = threading.Thread(target=run_attack_scenarios, daemon=True)
        attack_thread.start()
        
        # Give scenarios time to generate events
        print("⏳ Waiting for scenarios to generate events...")
        time.sleep(5)
        
        # Launch dashboard (blocking)
        launch_dashboard()
        
    except KeyboardInterrupt:
        print("\n🛑 Demo stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()