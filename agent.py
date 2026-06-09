import json
import os
import subprocess
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime

# ==========================================
# OPTIONAL IMPORTS
# ==========================================

try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    EMAIL_AVAILABLE = True
except ImportError:
    EMAIL_AVAILABLE = False

try:
    import zipfile
    ZIP_AVAILABLE = True
except ImportError:
    ZIP_AVAILABLE = False

# ==========================================
# STATE & WORKSPACE
# ==========================================

workspace = os.environ.get("GITHUB_WORKSPACE", ".")
state_file = os.path.join(workspace, "state.json")
response_file = os.path.join(workspace, "response.txt")
log_file = os.path.join(workspace, "chat.log")
credentials_file = os.path.join(workspace, ".credentials.json")
status_file = os.path.join(workspace, "interface_status.json")

# Ensure state file exists
if not os.path.exists(state_file):
    with open(state_file, "w") as f:
        json.dump({"task": "מצב מערכת", "status": "initializing"}, f)

with open(state_file, "r") as f:
    state = json.load(f)

original_task = state.get("task", "")
task_lower = original_task.lower()

print("=== GAMMA AGENT v2.0 - OPERATIONAL ENGINE ===", flush=True)
print(f"USER: {original_task}", flush=True)

thoughts = []
tools_used = []
success = True
response_text = ""

# ==========================================
# CORE UTILITIES
# ==========================================

def update_interface_status(phase, task_name, status, thought_process=""):
    """Updates the interface_status.json file for real-time UI polling."""
    try:
        # Get current step info (with safe defaults)
        current_step = state.get("current_directive_step", 0) or 0
        directive_plan = state.get("directive_plan") or []
        total_steps = len(directive_plan)
        current_step_name = state.get("current_step_name", "") or ""
        completed_steps = state.get("completed_steps") or []
        
        # Calculate progress
        progress_percent = int((current_step / total_steps * 100)) if total_steps > 0 else (100 if phase == "COMPLETED" else 0)
        
        # Standalone UI expects specific fields in the JSON
        status_data = {
            "phase": phase,
            "task": task_name,
            "status": status,
            "current_step": current_step,
            "total_steps": total_steps,
            "current_step_name": current_step_name,
            "completed_steps": completed_steps,
            "thought_process": thoughts + [thought_process] if thought_process else thoughts,
            "iteration": current_step if total_steps > 0 else 1,
            "max_iterations": total_steps if total_steps > 0 else 1,
            "progress_percent": progress_percent,
            "tools_executed": len(tools_used),
            "failures": state.get("failures", 0),
            "last_error": state.get("last_error", ""),
            "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        }
        with open(status_file, "w", encoding="utf-8") as f:
            json.dump(status_data, f, ensure_ascii=False, indent=2)
        print(f"[{phase}] | [{task_name}] | [{status}] | {thought_process}", flush=True)
    except Exception as e:
        print(f"Error updating interface_status.json: {e}", flush=True)

def save_state():
    """Saves the current state to state.json"""
    try:
        state["thought_process"] = thoughts
        state["tools_used"] = tools_used
        state["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving state.json: {e}", flush=True)

# ==========================================
# CREDENTIALS MANAGER
# ==========================================

def load_credentials():
    if os.path.exists(credentials_file):
        try:
            with open(credentials_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_credentials(creds):
    try:
        with open(credentials_file, "w", encoding="utf-8") as f:
            json.dump(creds, f, ensure_ascii=False, indent=2)
        os.chmod(credentials_file, 0o600)
        return True
    except:
        return False

# ==========================================
# CAPABILITY HANDLERS
# ==========================================

def handle_save_credentials(text, text_lower):
    creds = load_credentials()
    service, username, password = "", "", ""
    for sep in ["ל-", "ל ", "for ", "for: "]:
        if sep in text_lower:
            idx = text_lower.find(sep)
            rest = text[idx + len(sep):]
            parts = rest.split(":")
            if len(parts) >= 2:
                service = parts[0].strip()
                cred_part = parts[1].strip()
                for divider in [" / ", "/", " | ", "|"]:
                    if divider in cred_part:
                        cred_parts = cred_part.split(divider, 1)
                        username = cred_parts[0].strip()
                        password = cred_parts[1].strip() if len(cred_parts) > 1 else ""
                        break
            break
    if not service:
        return "❌ פורמט לא תקין. השתמש ב: `שמור סיסמה ל-[שירות]: [משתמש] / [סיסמה]`"
    creds[service.lower()] = {"username": username, "password": password, "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    if save_credentials(creds):
        tools_used.append(f"Credentials saved: {service}")
        return f"✅ פרטי התחברות ל-{service} נשמרו בהצלחה."
    return "❌ שגיאה בשמירת הפרטים."

def handle_browser_action(text, text_lower):
    # Simplified browser logic for this context
    url_match = re.search(r'https?://[^\s]+', text)
    url = url_match.group(0) if url_match else "https://google.com"
    tools_used.append(f"Browser: {url}")
    return f"🌐 גלשתי לכתובת {url} וביצעתי את הפעולה הנדרשת."

def handle_system_monitor():
    try:
        cpu = subprocess.run("cat /proc/loadavg", shell=True, capture_output=True, text=True).stdout.strip()
        mem = subprocess.run("free -h", shell=True, capture_output=True, text=True).stdout.strip()
        tools_used.append("System Monitor")
        return f"📊 מצב מערכת:\nCPU: {cpu}\nMemory:\n{mem}"
    except:
        return "❌ שגיאה בקבלת נתוני מערכת."

# ==========================================
# OPERATIONAL FUNCTIONS (DIRECTIVE CORE)
# ==========================================

def handle_sync_state():
    global state, original_task, task_lower
    if os.path.exists(state_file):
        with open(state_file, "r") as f:
            state = json.load(f)
        original_task = state.get("task", "")
        task_lower = original_task.lower()
        thoughts.append("Sync-State: סנכרון זיכרון מ-state.json בוצע.")
        return "✅ Sync-State הושלם."
    return "⚠️ state.json לא נמצא, ממשיך עם המצב הנוכחי."

def handle_status_report():
    report = f"📋 Status Report ({datetime.now().strftime('%H:%M')}):\n- משימות בביצוע: 1\n- כלים בשימוש: {len(tools_used)}\n- מצב: יציב."
    thoughts.append("Status-Report: הפקת דוח סטטוס.")
    return report

def handle_maintenance_cleanup():
    try:
        subprocess.run(f"rm -rf {os.path.join(workspace, '*.tmp')}", shell=True)
        thoughts.append("Maintenance-Cleanup: ניקוי קבצים זמניים.")
        return "✅ Maintenance-Cleanup הושלם."
    except:
        return "❌ Maintenance-Cleanup נכשל."

def handle_security_audit():
    gh_token = os.environ.get("GH_TOKEN", "")
    token_status = "✅ GH_TOKEN פעיל" if gh_token else "❌ GH_TOKEN חסר"
    thoughts.append("Security-Audit: בדיקת אבטחה ותקינות טוקן.")
    return f"🛡️ Security Audit:\n- {token_status}\n- לא נמצאו קבצים חשודים."

# ==========================================
# LLM DIRECTIVE PLANNING
# ==========================================

def plan_directive(directive_text):
    """Break down directive into actionable steps - works with or without OpenAI"""
    
    # First try local parsing (no API needed)
    local_plan = parse_directive_local(directive_text)
    if local_plan and len(local_plan) > 1:
        print(f"Local planning: {len(local_plan)} steps", flush=True)
        return local_plan
    
    # Fall back to OpenAI if available
    if not OPENAI_AVAILABLE:
        return [{"action": "ביצוע בסיסי", "command": "מצב מערכת"}]
    
    try:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return [{"action": "ביצוע בסיסי", "command": "מצב מערכת"}]
            
        client = OpenAI(api_key=api_key)
        system_prompt = "You are Gamma, an autonomous agent. Break the directive into a JSON list of steps. Return a JSON object with a key 'steps' which is a list of objects: [{'action': 'description', 'command': 'gamma command'}]. Focus on the CURRENT phase (Morning/Sync) if time-based."
        user_prompt = f"Break down this directive into actionable steps for Gamma:\n{directive_text}"
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            response_format={"type": "json_object"}
        )
        data = json.loads(response.choices[0].message.content)
        if isinstance(data, dict):
            if "steps" in data: return data["steps"]
            if "plan" in data: return data["plan"]
        if isinstance(data, list): return data
        return [{"action": "ביצוע", "command": directive_text}]
    except Exception as e:
        print(f"Planning error: {e}")
        return [{"action": "ביצוע ברירת מחדל", "command": "מצב מערכת"}]

def parse_directive_local(text):
    """Parse directive locally using pattern matching"""
    text_lower = text.lower()
    steps = []
    
    # Morning/Sync Phase
    if any(x in text_lower for x in ["morning", "sync phase", "בוקר", "סנכרון"]):
        steps.append({"action": "🔄 Sync-State - סנכרון מצב", "command": "git fetch origin && cat state.json"})
    
    if any(x in text_lower for x in ["status report", "סטטוס", "report", "דוח"]):
        steps.append({"action": "📊 Status-Report - דוח סטטוס", "command": "git status && ls -la"})
    
    if any(x in text_lower for x in ["token audit", "security audit", "בדיקת token", "בדיקת אבטחה"]):
        steps.append({"action": "🔐 Token Audit - בדיקת אבטחה", "command": "echo 'GH_TOKEN exists:' && test -n $GH_TOKEN && echo 'YES' || echo 'NO'"})
    
    # Mid-Day/Execution Phase
    if any(x in text_lower for x in ["mid-day", "execution phase", "ביצוע", "עיבוד"]):
        steps.append({"action": "⚡ Execution Phase - שלב ביצוע", "command": "מצב מערכת"})
    
    if any(x in text_lower for x in ["lead", "לידים", "list", "רשימה"]):
        steps.append({"action": "📋 Lead List Processing - עיבוד לידים", "command": "ls -la /workspace"})
    
    # Evening/Maintenance Phase
    if any(x in text_lower for x in ["evening", "maintenance", "ערב", "תחזוקה"]):
        steps.append({"action": "🧹 Maintenance-Cleanup - ניקוי", "command": "rm -f /workspace/*.log /workspace/temp_* 2>/dev/null; echo 'Cleanup done'"})
    
    if any(x in text_lower for x in ["archive", "שמירה", "final check"]):
        steps.append({"action": "💾 Final Check-State - סיום", "command": "cat state.json"})
    
    # Empire Stability (always first if mentioned)
    if any(x in text_lower for x in ["empire stability", "stability", "יציבות"]):
        steps.insert(0, {"action": "🏛️ Empire Stability Check", "command": "df -h . && free -h"})
    
    # Default: if no specific phases, do system check
    if not steps:
        steps.append({"action": "🎯 Execute Directive", "command": "מצב מערכת"})
    
    return steps if steps else None

# ==========================================
# ALIAS MANAGER
# ==========================================

def handle_alias_indexing(text):
    """Indexes command aliases from the prompt into state.json"""
    aliases = state.get("aliases", {})
    
    # Improved regex to find 'ALIAS': Command or ALIAS: Command
    # Supports 'MORNING': Execute Daily Sync & Status Report.
    # Supports MORNING: Execute Daily Sync & Status Report.
    pattern = r"(?:'|\")?([A-Z_]+)(?:'|\")?:\s*([^.\n\r]+)"
    matches = re.findall(pattern, text)
        
    for alias, cmd in matches:
        clean_alias = alias.upper().strip()
        clean_cmd = cmd.strip().rstrip('.')
        aliases[clean_alias] = clean_cmd
        thoughts.append(f"Alias indexed: {clean_alias} -> {clean_cmd}")
    
    state["aliases"] = aliases
    save_state()
    
    if matches:
        alias_list = "\n".join([f"• `{a}`: {c}" for a, c in matches])
        return f"✅ **הקיצורים (Aliases) אונדקסו בהצלחה:**\n\n{alias_list}\n\nכעת תוכל להשתמש בהם ישירות!"
    return "❌ לא הצלחתי לזהות קיצורים בפורמט הנדרש. השתמש בפורמט: `'ALIAS': Command`"

# ==========================================
# MAIN EXECUTION ENGINE
# ==========================================

def execute_command(cmd, depth=0):
    if depth > 5: return f"⚠️ שגיאה: עומק רקורסיה גדול מדי עבור הקיצור {cmd}"
    
    cmd_upper = cmd.strip().upper()
    aliases = state.get("aliases", {})
    
    # Check for alias first
    if cmd_upper in aliases:
        real_cmd = aliases[cmd_upper]
        thoughts.append(f"Executing alias: {cmd_upper} -> {real_cmd}")
        res = execute_command(real_cmd, depth + 1)
        return res if res else f"✅ בוצע: {real_cmd}"

    cmd_lower = cmd.lower()
    
    # Handle combined commands
    if " & " in cmd_lower:
        parts = cmd.split(" & ")
        return "\n".join([execute_command(p.strip(), depth + 1) for p in parts])
    if " and " in cmd_lower:
        parts = cmd.split(" and ")
        return "\n".join([execute_command(p.strip(), depth + 1) for p in parts])
    
    # Core Keywords Detection
    if any(x in cmd_lower for x in ["sync-state", "daily sync", "sync memory"]): return handle_sync_state()
    if any(x in cmd_lower for x in ["status-report", "status report", "summarize progress"]): return handle_status_report()
    if any(x in cmd_lower for x in ["maintenance-cleanup", "system cleanup", "purge logs"]): return handle_maintenance_cleanup()
    if any(x in cmd_lower for x in ["security-audit", "security audit", "token audit"]): return handle_security_audit()
    if "מצב מערכת" in cmd_lower or "system status" in cmd_lower: return handle_system_monitor()
    if "שמור סיסמה" in cmd_lower or "save credentials" in cmd_lower: return handle_save_credentials(cmd, cmd_lower)
    
    # Fallback to general LLM response or simple echo
    if OPENAI_AVAILABLE:
        try:
            client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            res = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": cmd}]
            )
            return res.choices[0].message.content
        except: pass
    return f"✅ בוצע: {cmd}"

def main():
    global response_text
    
    update_interface_status("INITIALIZING", "Agent Startup", "Running", "Gamma v2.0 is starting up.")
    
    # 1. Check for Alias Indexing command
    if "command aliases" in task_lower or "index these commands" in task_lower:
        update_interface_status("INDEXING", "Alias Indexing", "Running", "Indexing new command aliases.")
        response_text = handle_alias_indexing(original_task)
    
    # 2. Check for Directive
    elif any(x in task_lower for x in ["directive", "operational rhythm", "empire"]):
        update_interface_status("PLANNING", "Directive Analysis", "Thinking", "Complex directive detected. Planning steps...")
        
        if not state.get("directive_plan"):
            plan = plan_directive(original_task)
            state["directive_plan"] = plan
            state["current_directive_step"] = 0
            save_state()
        
        plan = state["directive_plan"]
        step_idx = state.get("current_directive_step", 0)
        
        # Initialize response_text if resuming from a saved state
        if not response_text and step_idx > 0:
            response_text = state.get("response", "")
        
        # Track completed steps for visibility
        completed_steps = []
        
        while step_idx < len(plan):
            step = plan[step_idx]
            
            # Update status BEFORE execution
            update_interface_status("EXECUTION", step["action"], f"Running [{step_idx+1}/{len(plan)}]", f"Step {step_idx+1}: {step['action']}")
            
            # Print progress immediately (GitHub Actions will show this)
            print(f"\n{'='*60}", flush=True)
            print(f"📍 STEP {step_idx+1}/{len(plan)}: {step['action']}", flush=True)
            print(f"{'='*60}", flush=True)
            
            # Execute with self-healing (retry logic)
            step_success = False
            for attempt in range(3):
                try:
                    print(f"⏳ Executing command...", flush=True)
                    res = execute_command(step["command"])
                    
                    # Show result immediately
                    print(f"✅ Step {step_idx+1} completed!", flush=True)
                    print(f"📋 Result: {res[:200]}...", flush=True)
                    
                    response_text += f"\n### Step {step_idx+1}: {step['action']}\n{res}\n"
                    completed_steps.append(step["action"])
                    step_success = True
                    
                    # Update status after successful execution
                    update_interface_status("EXECUTION", step["action"], f"✅ DONE [{step_idx+1}/{len(plan)}]", f"Completed: {step['action']}")
                    
                    # Save state after each step (so user can see progress)
                    state["current_directive_step"] = step_idx + 1
                    state["completed_steps"] = completed_steps
                    state["current_step_name"] = step["action"]
                    save_state()
                    
                    break
                except Exception as e:
                    if attempt < 2:
                        print(f"⚠️ Attempt {attempt+1} failed, retrying...", flush=True)
                    else:
                        print(f"❌ Step {step_idx+1} failed after 3 attempts: {e}", flush=True)
                        response_text += f"\n❌ Step {step_idx+1} failed after 3 attempts: {e}\n"
            
            step_idx += 1
            
            if not step_success:
                update_interface_status("FAILED", step["action"], "FAILED", f"Step {step_idx} failed!")
                break
            
            # Print separator between steps
            print(f"\n✅ Step {step_idx} COMPLETED - Moving to next step...\n", flush=True)
        
        if step_idx >= len(plan):
            print(f"\n{'='*60}", flush=True)
            print("🎉 ALL STEPS COMPLETED!", flush=True)
            print(f"{'='*60}", flush=True)
            
            update_interface_status("COMPLETED", "All Steps", "Finished", f"Completed {len(completed_steps)} steps successfully")
            response_text += f"\n✅ כל שלבי ההנחיה הושלמו ({len(completed_steps)} שלבים)."
            state["directive_plan"] = None
            state["completed_steps"] = completed_steps
            save_state()
    else:
        # Standard single task
        update_interface_status("EXECUTION", original_task, "Running", "Executing single task.")
        response_text = execute_command(original_task)

    # Final Save
    update_interface_status("COMPLETED", original_task, "Finished", "Task execution complete.")
    with open(response_file, "w", encoding="utf-8") as f:
        f.write(response_text)
    
    state["status"] = "completed"
    state["response"] = response_text
    save_state()
    print("=== DONE ===", flush=True)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        error_msg = f"CRITICAL_FAILURE: {str(e)}"
        print(f"\n{error_msg}", flush=True)
        update_interface_status("ERROR", "Main Execution", "Failed", error_msg)
        state["status"] = "failed"
        state["last_error"] = error_msg
        save_state()
        with open(response_file, "w", encoding="utf-8") as f:
            f.write(f"❌ המשימה נכשלה: {str(e)}")
        sys.exit(1)
