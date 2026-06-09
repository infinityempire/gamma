import json
import os
import subprocess
from datetime import datetime

workspace = os.environ.get("GITHUB_WORKSPACE", ".")
state_file = os.path.join(workspace, "state.json")

with open(state_file, "r") as f:
    state = json.load(f)

task = state.get("task", "").lower()
print(f"=== GAMMA AGENT - DYNAMIC TOOL SELECTION ===", flush=True)
print(f"TASK: {task}", flush=True)

thoughts = []
tools_used = []
success = True

# Dynamic Tool Selection Logic
print("\n--- TOOL SELECTION PHASE ---", flush=True)

# Multi-step task detection
if "create" in task and ("file" in task or "status" in task):
    print("Detected: Multi-step file operation (Create + Write + Read)", flush=True)
    thoughts.append("נבחרה משימה מורכבת: יצירת קובץ + כתיבה + קריאה")
    thoughts.append("אבצע 3 פעולות ברצף")
    
    # Step 1: Create file with current time
    print("\n--- STEP 1: Create status.txt with timestamp ---", flush=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cmd1 = f'echo "Generated at: {timestamp}" > {workspace}/status.txt'
    print(f"CMD: {cmd1}", flush=True)
    
    try:
        r1 = subprocess.run(cmd1, shell=True, capture_output=True, text=True, timeout=30)
        print(f"Result: exit={r1.returncode}", flush=True)
        if r1.returncode != 0:
            print(f"Error: {r1.stderr}", flush=True)
            success = False
        else:
            tools_used.append("Create file: SUCCESS")
    except Exception as e:
        print(f"ERROR: {e}", flush=True)
        success = False
    
    # Step 2: Read the file content
    print("\n--- STEP 2: Read status.txt content ---", flush=True)
    cmd2 = f'cat {workspace}/status.txt'
    print(f"CMD: {cmd2}", flush=True)
    
    try:
        r2 = subprocess.run(cmd2, shell=True, capture_output=True, text=True, timeout=30)
        content = r2.stdout.strip()
        print(f"Content: {content}", flush=True)
        if r2.returncode == 0:
            tools_used.append(f"Read file: {content}")
            thoughts.append(f"נקרא התוכן: {content}")
        else:
            print(f"Error: {r2.stderr}", flush=True)
            success = False
    except Exception as e:
        print(f"ERROR: {e}", flush=True)
        success = False
    
    # Step 3: Log to console
    print("\n--- STEP 3: Log to console ---", flush=True)
    cmd3 = f'echo "=== FINAL OUTPUT ===" && cat {workspace}/status.txt && echo "=== END ==="'
    print(f"CMD: {cmd3}", flush=True)
    
    try:
        r3 = subprocess.run(cmd3, shell=True, capture_output=True, text=True, timeout=30)
        print(f"Console output:\n{r3.stdout}", flush=True)
        if r3.returncode == 0:
            tools_used.append("Log to console: SUCCESS")
            thoughts.append("הפלט הודפס לקונסול בהצלחה")
        else:
            print(f"Error: {r3.stderr}", flush=True)
    except Exception as e:
        print(f"ERROR: {e}", flush=True)

elif "echo" in task:
    cmd = "echo Hello from Gamma"
    print(f"Selected: terminal (echo)", flush=True)
    thoughts.append("נבחר terminal להדפסת הודעה")
    
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        success = r.returncode == 0
        print(f"Result: exit={r.returncode}", flush=True)
        tools_used.append(f"echo: {r.stdout.strip()}")
    except Exception as e:
        print(f"ERROR: {e}", flush=True)
        success = False

elif "npm" in task:
    cmd = "npm --version"
    print(f"Selected: terminal (npm check)", flush=True)
    thoughts.append("נבחר terminal לבדיקת npm")
    
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        success = r.returncode == 0
        print(f"Result: {r.stdout.strip()}", flush=True)
        tools_used.append(f"npm: {r.stdout.strip()}")
    except Exception as e:
        print(f"ERROR: {e}", flush=True)
        success = False

elif "python" in task:
    cmd = "python3 --version"
    print(f"Selected: terminal (python check)", flush=True)
    thoughts.append("נבחר terminal לבדיקת Python")
    
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        success = r.returncode == 0
        print(f"Result: {r.stdout.strip()}", flush=True)
        tools_used.append(f"python: {r.stdout.strip()}")
    except Exception as e:
        print(f"ERROR: {e}", flush=True)
        success = False

else:
    # Default: simple echo
    cmd = f'echo Gamma: {task[:50]}'
    print(f"Selected: terminal (default)", flush=True)
    thoughts.append("משימה כללית - ברירת מחדל")
    
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        success = r.returncode == 0
        print(f"Result: {r.stdout.strip()}", flush=True)
        tools_used.append(f"default: {r.stdout.strip()}")
    except Exception as e:
        print(f"ERROR: {e}", flush=True)
        success = False

# Update state
print("\n--- SUMMARY ---", flush=True)
print(f"Tools used: {len(tools_used)}", flush=True)
for t in tools_used:
    print(f"  - {t}", flush=True)
print(f"Status: {'SUCCESS' if success else 'FAILED'}", flush=True)

state["status"] = "completed" if success else "failed"
state["tool_history"] = [{"tool": "terminal", "steps": len(tools_used), "success": success}]
state["thought_process"] = thoughts
state["tools_used"] = tools_used

with open(state_file, "w") as f:
    json.dump(state, f, indent=2)

print(f"\nFinal status: {state['status']}", flush=True)
print("=== AGENT COMPLETE ===", flush=True)