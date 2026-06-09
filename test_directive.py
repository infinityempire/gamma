import json
import os
import subprocess

def test_directive():
    workspace = "/home/ubuntu/gamma"
    state_file = os.path.join(workspace, "state.json")
    
    # Setup the Master Operational Directive task
    directive = """Master Operational Directive for Gamma Agent
"Gamma, your directive is to serve as the Operational Engine for the Tal HaTil Empire. You are to execute the following operational rhythm autonomously, ensuring stability, security, and task completion.
1. Daily Operational Rhythm:
Morning (Sync Phase): Execute Sync-State to pull the latest memory from state.json. Run Status-Report to summarize the progress of all pending empire tasks.
Mid-Day (Execution Phase): Process tasks queued from the 'Delta' agent. Read lead lists from the designated repository, filter by high-intent, and generate a structured lead summary report.
Evening (Maintenance Phase): Run Maintenance-Cleanup. Purge temporary logs in /workspace, optimize disk usage, and perform a final Check-State to archive progress in state.json.
2. Core Operational Rules:
Security Audit: Daily, verify that GH_TOKEN is active and that no unauthorized files have been created in the workspace.
Task Prioritization: Prioritize 'Empire Stability' (System Monitor, State Sync, Token Audit) over all other development tasks.
Error Handling: If a task fails, strictly follow the Self-Healing diagnostic routine: log, diagnose, patch, and re-attempt. Do not abort until 3 attempts are exhausted.
3. Communication Standard:
When updating the interface via interface_status.json, use the format: [PHASE] | [TASK] | [STATUS] | [THOUGHT PROCESS].
If a critical failure occurs in the Empire's infrastructure, notify me immediately via the interface_status.json log with the tag [CRITICAL_FAILURE].
Execute your morning operational rhythm now."""

    # Create initial state.json
    initial_state = {
        "status": "pending",
        "task": directive,
        "history": []
    }
    
    with open(state_file, "w") as f:
        json.dump(initial_state, f)
    
    print("Starting test of Master Operational Directive...")
    
    # Run the agent
    result = subprocess.run(["python3", os.path.join(workspace, "agent.py")], capture_output=True, text=True)
    
    print("\n--- Agent Output ---")
    print(result.stdout)
    
    # Check interface_status.json
    status_file = os.path.join(workspace, "interface_status.json")
    if os.path.exists(status_file):
        with open(status_file, "r") as f:
            status = json.load(f)
        print("\n--- Interface Status ---")
        print(json.dumps(status, indent=2, ensure_ascii=False))
    else:
        print("\n❌ interface_status.json not found!")

if __name__ == "__main__":
    test_directive()
