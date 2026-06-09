import json
import os
import subprocess

workspace = "/home/ubuntu/gamma"
state_file = os.path.join(workspace, "state.json")

# Specific prompt from user
task = """Gamma, from now on, recognize these command aliases for our daily operations:
'MORNING': Execute Daily Sync & Status Report.
'LEADS': Process Delta Agent leads and generate summary.
'MAINTAIN': Perform system cleanup, security audit, and state archive.
'STATUS': Display phase, current task, and thought process.
'EMERGENCY': Secure state, archive progress, and halt all tasks.
Confirm you have indexed these commands."""

# Setup state
with open(state_file, "w") as f:
    json.dump({"task": task, "status": "running"}, f)

# Run agent
print("Running agent with specific prompt...")
env = os.environ.copy()
env["GITHUB_WORKSPACE"] = workspace
result = subprocess.run(["python3", os.path.join(workspace, "agent.py")], 
                        env=env, capture_output=True, text=True)

print("--- STDOUT ---")
print(result.stdout)
print("--- STDERR ---")
print(result.stderr)

if result.returncode != 0:
    print(f"Agent failed with return code {result.returncode}")
else:
    print("Agent finished successfully.")
