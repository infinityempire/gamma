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
    
    print(f"\n--- Running Agent Task: {task[:100]}... ---")
    result = subprocess.run(["python3", agent_py], env=env, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"FAILED: {result.stderr}")
        return False
    
    with open(os.path.join(workspace, "response.txt"), "r") as f:
        print(f"RESPONSE:\n{f.read()}")
    return True

audit_prompt = """Gamma, execute the 'Empire Efficiency Audit' sequence:
Repository Analysis: Scan the entire infinityempire/gamma and delta-agent repositories. Identify all static tasks (scripts that run every day without changing their logic) and refactor them into a single, modular Python service within the /workspace folder.
Dependency Mapping: Create a requirements.txt file that consolidates all dependencies for every agent in my empire. Ensure there are no version conflicts between the Gamma agent and the Delta agent.
Operational Hardening: Identify the 3 most frequent failure points in your own gamma-main.yml logs from the last 5 days. For each failure point, write a dedicated 'Diagnostic & Patch' script and save it in a new directory named /workspace/healing_scripts.
Final Output: Generate a MANIFEST.md file in the root of the repository that lists every autonomous service running in the empire, its current status, and the last time it successfully performed an operation."""

run_agent(audit_prompt)
