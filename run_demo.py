#!/usr/bin/env python3
"""
MAAIS-Runtime Complete Demo
Runs all components and launches dashboard
"""
import sys
import subprocess
import threading
import time
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def run_attack_scenarios():
    """Run attack scenarios (safely imported when invoked)."""
    print("🚀 Starting attack scenarios...")
    # Import inside function to avoid pulling demo deps unless used
    from demo.scenarios.attack_scenarios import main as run_scenarios
    run_scenarios()

def launch_dashboard():
    """Launch Streamlit dashboard"""
    print("📊 Launching security dashboard...")
    try:
        # Prefer launching via python -m streamlit for environments where `streamlit` is not on PATH
        subprocess.run([sys.executable, "-m", "streamlit", "run", "dashboard/audit_viewer.py"], check=True)
    except FileNotFoundError:
        print("Streamlit not found: please install with `pip install streamlit` or run with --no-dashboard")
        raise
    except subprocess.CalledProcessError as e:
        print(f"Failed to launch dashboard: {e}")
        raise

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
    
    parser = argparse.ArgumentParser(description="Run the MAAIS-Runtime demo")
    parser.add_argument("--no-dashboard", action="store_true", help="Run demo without launching Streamlit dashboard")
    args = parser.parse_args()

    try:
        if args.no_dashboard:
            # Run scenarios directly (blocking) and then print audit logs
            run_attack_scenarios()
            print("\n✅ Scenarios completed (no dashboard). Check audit logs in tenants/policies/default or use the audit logger API.")
            return

        # Run attack scenarios in background thread
        attack_thread = threading.Thread(target=run_attack_scenarios, daemon=True)
        attack_thread.start()

        # Give scenarios time to generate events
        print("⏳ Waiting for scenarios to generate events...")
        time.sleep(5)

        # Launch dashboard (blocking)
        try:
            launch_dashboard()
        except Exception:
            print("⚠️ Dashboard launch failed; running scenarios completed. You can retry with `python run_demo.py --no-dashboard`.")

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