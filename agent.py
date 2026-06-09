import json
import os
import subprocess
from datetime import datetime

workspace = os.environ.get("GITHUB_WORKSPACE", ".")
state_file = os.path.join(workspace, "state.json")
response_file = os.path.join(workspace, "response.txt")
log_file = os.path.join(workspace, "chat.log")

with open(state_file, "r") as f:
    state = json.load(f)

original_task = state.get("task", "")
task = original_task.lower()

print("=== GAMMA AGENT - CONVERSATIONAL AI ===", flush=True)
print(f"USER: {original_task}", flush=True)

thoughts = []
tools_used = []
success = True
response_text = ""

# ==========================================
# INTELLIGENCE ENGINE
# ==========================================

def get_about_me():
    return """🤖 **אני גאמא - סוכן AI אוטונומי!**

מה אני יודע לעשות:

🔹 **להריץ פקודות** - `run git status`, `run npm --version`
🔹 **ליצור קבצים** - `create file test.txt with hello`
🔹 **לענות על שאלות** - שאל אותי הכל!
🔹 **לתקן בעיות** - ספר לי מה הבעיה ואנסה לעזור
🔹 **לתכנת** - אני יכול לכתוב קוד ב-Python, JavaScript ועוד

פשוט דבר איתי! 💬"""

def get_help():
    return """🆘 **פקודות שאני מבין:**

💬 **שאלות:**
• "מה אתה יודע לעשות?"
• "מי אתה?"
• "עזור לי"

⚡ **פקודות טכניות:**
• `run echo hello` - הרץ פקודה
• `create file X with Y` - צור קובץ
• `check npm version` - בדוק גרסה

🎯 **ספר לי מה אתה צריך ואעזור!**

דוגמא: "צור קובץ בשם hello.txt עם התוכן שלום עולם"
או: "מה גרסת ה-node שלי?" """

def get_greeting():
    return """👋 **שלום! אני גאמא!**

אני סוכן AI שרץ על שרתי GitHub Actions.

💬 אני יכול:
• לענות על שאלות
• להריץ פקודות
• ליצור ולערוך קבצים
• לעזור עם תכנות

🔹 נסה: "מה אתה יודע לעשות?"
🔹 או: "run git --version"
🔹 או: "צור קובץ בשם test.txt"

איך אני יכול לעזור לך? 🚀"""

def handle_question(text):
    """Handle question-type inputs"""
    if any(x in text for x in ["מה אתה", "who are you", "what are you", "מי אתה", "מה זה גאמא"]):
        return get_about_me()
    
    if any(x in text for x in ["יכול", "can you", "מה אתה יודע", "what can you"]):
        return get_about_me()
    
    if any(x in text for x in ["שלום", "hello", "hi", "היי"]):
        return get_greeting()
    
    if any(x in text for x in ["עזור", "help", "עזרה", "איך"]):
        return get_help()
    
    if any(x in text for x in ["ספר על עצמך", "tell me about yourself", "about you"]):
        return get_about_me()
    
    if "מזל" in text or "luck" in text.lower():
        return "🍀 בהצלחה! אם תצטרך עזרה, אני פה!"
    
    # Default question response
    return f"""🤔 שאלה מעניינת: "{text}"

אני יכול לעזור עם:
• פקודות טכניות - נסה: `run echo hello`
• יצירת קבצים - נסה: `create file X with Y`
• שאלות על מה שאני יודע - נסה: "מה אתה יודע לעשות?"

או ספר לי יותר ואנסה לעזור! 💡"""

def handle_command(text):
    """Handle command-type inputs - using NATURAL LANGUAGE"""
    
    text_lower = text.lower()
    
    # ==========================================
    # FILE OPERATIONS - Natural Language
    # ==========================================
    
    # Create file - many patterns
    file_patterns = ["צור קובץ", "צור file", "create file", "תיצור קובץ", "תיצור file", "צור טקסט", "תכתוב קובץ"]
    if any(p in text_lower for p in file_patterns):
        # Extract filename and content
        filename = "myfile.txt"
        content = "Hello from Gamma!"
        
        # Try to find filename
        name_patterns = ["בשם", "named", "שם", "file named", "filename"]
        for p in name_patterns:
            if p in text_lower:
                parts = text_lower.split(p)
                if len(parts) > 1:
                    remaining = parts[1].strip()
                    # Get filename until "with" or end
                    if "with" in remaining:
                        filename = remaining.split("with")[0].strip()
                        content = remaining.split("with")[1].strip()
                    else:
                        filename = remaining.split()[0] if remaining.split() else "myfile.txt"
        
        # Try to find content
        content_patterns = ["with", "תוכן", "content", "שכתוב", "write"]
        for p in content_patterns:
            if p in text_lower:
                parts = text_lower.split(p)
                if len(parts) > 1:
                    content = parts[1].strip().split()[0] if parts[1].strip().split() else "Hello!"
        
        # Clean filename
        filename = filename.replace(" ", "_").replace('"', '').replace("'", "")
        
        try:
            filepath = os.path.join(workspace, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            
            tools_used.append(f"Create file: {filename}")
            thoughts.append(f"יצרתי קובץ בשם {filename}")
            
            return f"""✅ **נוצר קובץ חדש!**

📄 **שם הקובץ:** `{filename}`
📝 **התוכן:** `{content}`

הקובץ נשמר בהצלחה! 🎉"""
        except Exception as e:
            return f"❌ שגיאה ביצירת הקובץ: {str(e)}"
    
    # ==========================================
    # VERSION CHECKS - Natural Language
    # ==========================================
    
    version_patterns = [
        ("מה גרסת", "npm"), ("npm version", "npm"), ("גרסת npm", "npm"),
        ("מה גרסת node", "node"), ("node version", "node"), ("גרסת node", "node"),
        ("מה גרסת python", "python"), ("python version", "python"), ("גרסת python", "python"),
        ("מה גרסת git", "git"), ("git version", "git"), ("גרסת git", "git"),
    ]
    
    for pattern, tool in version_patterns:
        if pattern in text_lower:
            cmd_map = {"npm": "npm --version", "node": "node --version", 
                      "python": "python3 --version", "git": "git --version"}
            cmd = cmd_map.get(tool)
            
            try:
                r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
                version = r.stdout.strip()
                tools_used.append(f"Version check: {tool}")
                thoughts.append(f"בדקתי גרסת {tool}")
                
                return f"""📋 **גרסת {tool}:**

```
{version}
```

✅ התוכנה מותקנת ועובדת!"""
            except:
                return f"❌ לא הצלחתי לבדוק את גרסת {tool}. אולי היא לא מותקנת?"
    
    # ==========================================
    # SYSTEM INFO - Natural Language
    # ==========================================
    
    if any(x in text_lower for x in ["מה יש לי", "מה יש פה", "מה יש בworkspace", "show files", "אילו קבצים"]):
        cmd = "ls -la"
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=workspace, timeout=15)
            files = r.stdout.strip()
            tools_used.append("List files")
            thoughts.append("הצגתי רשימת קבצים")
            
            file_list = "\n".join([f"📄 {f}" for f in files.split("\n") if f])
            
            return f"""📁 **קבצים בתיקייה:**

```
{files}
```

יש לך {len(files.split(chr(10)))} קבצים/תיקיות ב-workspace."""
        except Exception as e:
            return f"❌ שגיאה: {str(e)}"
    
    # ==========================================
    # GIT INFO
    # ==========================================
    
    if any(x in text_lower for x in ["מה קורה בgit", "git status", "status של", "commitים"]):
        cmd = "git status"
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=workspace, timeout=15)
            status = r.stdout.strip() if r.stdout else r.stderr.strip()
            tools_used.append("Git status")
            thoughts.append("בדקתי סטטוס Git")
            
            return f"""🔄 **סטטוס Git:**

```
{status if status else 'לא נמצא מידע'}
```

✅ הכל מעודכן! או שאין לך פרויקט Git כאן."""
        except:
            return "🔹 לא מצאתי פרויקט Git בתיקייה הזו."
    
    # ==========================================
    # DEFAULT - Natural command detection
    # ==========================================
    
    if "run" in text_lower:
        cmd = text_lower.replace("run", "").strip()
        if cmd:
            thoughts.append(f"מריץ פקודה: {cmd}")
            try:
                r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
                output = r.stdout.strip() if r.stdout else r.stderr.strip()
                if r.returncode == 0:
                    tools_used.append(f"Command: {cmd}")
                    return f"✅ **פקודה בוצעה!**

📤 **Output:**
```
{output if output else '(אין פלט)'}
```"
                else:
                    return f"❌ **שגיאה:**
```
{output}
```"
            except Exception as e:
                return f"❌ שגיאה: {str(e)}"
    
    # If nothing matched, ask what they need
    return """🤔 לא הבנתי בדיוק מה אתה צריך.

הנה כמה דברים שאני יכול לעשות:

📄 **ליצור קובץ:**
"צור קובץ בשם hello.txt עם שלום עולם"

📋 **לבדוק גרסאות:**
"מה גרסת npm שלי?" או "בדוק גרסת node"

📁 **להראות קבצים:**
"מה יש לי בתיקייה?" או "אילו קבצים יש"

💬 או פשוט תגיד לי מה אתה צריך ואנסה לעזור! 😊"""

def handle_general(text):
    """Handle general messages"""
    return f"""💬 קיבלתי: "{text[:50]}{'...' if len(text) > 50 else ''}"

🤖 אני גאמא - סוכן AI! 

נסה פקודות כמו:
• `run echo hello`
• `create file test.txt with hello`
• "מה אתה יודע לעשות?"

או פשוט שאל אותי שאלה! 😊"""

# ==========================================
# MAIN LOGIC
# ==========================================

print("\n--- THINKING ---", flush=True)

# Detect input type
question_words = ["מה", "איך", "למה", "מי", "היכן", "מתי", "האם", "כמה", "what", "how", "why", "who", "where", "when", "is", "are", "can", "do", "does", "?"]
command_words = ["run", "execute", "create", "write", "delete", "install", "build", "check", "list", "הרץ", "צור", "התקן", "בנה"]

is_question_input = any(q in task for q in question_words)
is_command_input = any(c in task for c in command_words)

if is_question_input:
    print("🎯 Detected: QUESTION", flush=True)
    thoughts.append("זו שאלה - מחפש תשובה מתאימה")
    response_text = handle_question(original_task)
    
elif is_command_input:
    print("⚡ Detected: COMMAND", flush=True)
    thoughts.append("זו פקודה - מבצע")
    response_text = handle_command(original_task)
    
else:
    print("💬 Detected: GENERAL", flush=True)
    thoughts.append("הודעה כללית - מגיב")
    response_text = handle_general(original_task)

# ==========================================
# SAVE EVERYTHING
# ==========================================

print("\n--- SAVING ---", flush=True)

# Save response
with open(response_file, "w", encoding="utf-8") as f:
    f.write(response_text)
print(f"Response saved: {response_text[:80]}...", flush=True)

# Log chat
with open(log_file, "a", encoding="utf-8") as f:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    f.write(f"[{timestamp}] USER: {original_task}\n")
    f.write(f"[{timestamp}] GAMMA: {response_text[:200]}...\n\n")

# ==========================================
# UPDATE STATE
# ==========================================

print("\n--- FINAL ---", flush=True)
print(f"Type: {'Question' if is_question_input else 'Command' if is_command_input else 'General'}", flush=True)
print(f"Tools: {len(tools_used)}", flush=True)
print(f"Status: SUCCESS", flush=True)

state["status"] = "completed"
state["response"] = response_text
state["task_type"] = "question" if is_question_input else "command" if is_command_input else "general"
state["tool_history"] = [{"tool": "chat", "count": len(tools_used)}]
state["thought_process"] = thoughts
state["tools_used"] = tools_used
state["completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

with open(state_file, "w", encoding="utf-8") as f:
    json.dump(state, f, ensure_ascii=False, indent=2)

print("\n=== DONE ===", flush=True)
print(f"Response: {response_text[:100]}...", flush=True)