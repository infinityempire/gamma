import json
import os
import subprocess

workspace = "/home/ubuntu/gamma"
state_file = os.path.join(workspace, "state.json")
agent_py = os.path.join(workspace, "agent.py")
env = os.environ.copy()
env["GITHUB_WORKSPACE"] = workspace

def run_agent(task):
    with open(state_file, "w") as f:
        json.dump({"task": task, "status": "running"}, f)
    
    print(f"\n--- Running Agent Task: {task[:50]}... ---")
    result = subprocess.run(["python3", agent_py], env=env, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"FAILED: {result.stderr}")
        return False
    
    with open(os.path.join(workspace, "response.txt"), "r") as f:
        print(f"RESPONSE: {f.read()}")
    return True

# Step 1: Index Aliases
alias_prompt = """Gamma, from now on, recognize these command aliases for our daily operations:
'MORNING': Execute Daily Sync & Status Report.
'LEADS': Process Delta Agent leads and generate summary.
Confirm you have indexed these commands."""

if run_agent(alias_prompt):
    # Step 2: Execute Alias
    run_agent("MORNING")

# Step 3: Master Operational Directive
directive_prompt = """Master Operational Directive for Gamma Agent
"Gamma, your directive is to serve as the Operational Engine for the Tal HaTil Empire. You are to execute the following operational rhythm autonomously, ensuring stability, security, and task completion.
1. Daily Operational Rhythm:
Morning (Sync Phase): Execute Sync-State to pull the latest memory from state.json. Run Status-Report to summarize the progress of all pending empire tasks.
Execute your morning operational rhythm now." """

run_agent(directive_prompt)
