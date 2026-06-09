import json
import os
import subprocess

workspace = os.environ.get("GITHUB_WORKSPACE", ".")
state_file = os.path.join(workspace, "state.json")

with open(state_file, "r") as f:
    state = json.load(f)

task = state.get("task", "").lower()
print(f"TASK: {task}", flush=True)

if "echo" in task:
    cmd = "echo Hello from Gamma"
elif "npm" in task:
    cmd = "npm --version"
elif "python" in task:
    cmd = "python3 --version"
else:
    cmd = f"echo Gamma: {task[:30]}"

print(f"CMD: {cmd}", flush=True)

try:
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
    success = r.returncode == 0
    print(f"RESULT: exit={r.returncode}", flush=True)
except Exception as e:
    print(f"ERROR: {e}", flush=True)
    success = False

state["status"] = "completed" if success else "failed"
state["tool_history"] = [{"tool": "terminal", "success": success}]

with open(state_file, "w") as f:
    json.dump(state, f)

print(f"Final: {state['status']}", flush=True)