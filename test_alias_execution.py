import json
import os
import subprocess

workspace = "/home/ubuntu/gamma"
state_file = os.path.join(workspace, "state.json")

# Call one of the indexed aliases
task = "MORNING"

# Ensure state has the aliases
with open(state_file, "r") as f:
    state = json.load(f)
    state["task"] = task
    state["status"] = "running"

with open(state_file, "w") as f:
    json.dump(state, f)

# Run agent
print(f"Running agent with alias: {task}")
env = os.environ.copy()
env["GITHUB_WORKSPACE"] = workspace
result = subprocess.run(["python3", os.path.join(workspace, "agent.py")], 
                        env=env, capture_output=True, text=True)

print("--- STDOUT ---")
print(result.stdout)
if result.returncode != 0:
    print(f"Agent failed with return code {result.returncode}")
    print(result.stderr)
else:
    with open(os.path.join(workspace, "response.txt"), "r") as f:
        print("--- RESPONSE ---")
        print(f.read())
