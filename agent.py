import json
import os
import subprocess
import re
from datetime import datetime

# Try to import Tavily for web search
try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False

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

def handle_command(text, text_lower=None, thoughts=None, tools_used=None):
    """Handle command-type inputs - using NATURAL LANGUAGE"""
    
    if thoughts is None:
        thoughts = []
    if tools_used is None:
        tools_used = []
    
    if text_lower is None:
        text_lower = text.lower()
    
    # ==========================================
    # WEB SEARCH - FULL CAPABILITY
    # ==========================================
    
    search_patterns = ["חפש", "search", "google", "גוגל", "מצא", "find on web", "סרוק", "research", "who is", "מי זה", "what is", "מה זה", "5 הכי", "top 5", "הכי פופולרי", "popular"]
    if any(p in text_lower for p in search_patterns) or ("מה ה" in text_lower and any(x in text_lower for x in ["כלי", "tool", "אפליקציה", "app", "software", "platform"])):
        
        query = text
        for p in ["חפש", "search for", "find on", "google", "מצא", "סרוק", "research", "מה ה", "who is", "מי זה", "what is", "מה זה"]:
            query = query.replace(p, "")
        query = query.strip()
        
        if not query:
            return "❌ לא הבנתי מה לחפש. תגיד לי מה לחפש."
        
        thoughts.append("מחפש באינטרנט: " + query)
        
        # Try Tavily if available
        if TAVILY_AVAILABLE:
            try:
                tavily = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY", ""))
                result = tavily.search(query=query, max_results=10, include_answer=True)
                
                answer = result.get("answer", "")
                results = result.get("results", [])
                
                output = "🔍 **תוצאות חיפוש עבור:** " + query + "\n\n"
                
                if answer:
                    output += "📝 **תשובה:**\n" + answer + "\n\n"
                
                output += "📋 **מקורות:**\n"
                for i, r in enumerate(results[:5], 1):
                    title = r.get("title", "ללא כותרת")
                    url = r.get("url", "")
                    content = r.get("content", "")[:200]
                    output += f"{i}. [{title}]({url})\n"
                    if content:
                        output += f"   └ {content}...\n"
                
                tools_used.append("Web search (Tavily)")
                return output
            except Exception as e:
                print(f"Tavily error: {e}", flush=True)
        
        # Fallback: use DuckDuckGo API (JSON)
        try:
            import urllib.parse
            encoded_query = urllib.parse.quote(query)
            api_url = f"https://api.duckduckgo.com/?q={encoded_query}&format=json&no_html=1"
            
            r = subprocess.run(
                f"curl -sL --max-time 10 '{api_url}'",
                shell=True, capture_output=True, text=True, timeout=15
            )
            
            if r.stdout:
                import json
                data = json.loads(r.stdout)
                
                heading = data.get("Heading", "")
                abstract = data.get("AbstractText", "")
                abstract_url = data.get("AbstractURL", "")
                results = data.get("RelatedTopics", [])
                
                output = "🔍 **תוצאות חיפוש עבור:** " + query + "\n\n"
                
                if heading or abstract:
                    output += f"📝 **{heading or 'מידע'}:**\n"
                    if abstract:
                        output += abstract[:500] + ("..." if len(abstract) > 500 else "") + "\n"
                    if abstract_url:
                        output += f"\n📎 [קישור]({abstract_url})\n"
                
                if results:
                    output += "\n📋 **תוצאות נוספות:**\n"
                    for i, r in enumerate(results[:5], 1):
                        text = r.get("Text", "")
                        if text:
                            # Clean HTML from text
                            clean_text = re.sub(r'<[^>]+>', '', text)
                            output += f"{i}. {clean_text[:150]}...\n"
                
                if not heading and not abstract and not results:
                    output += "לא מצאתי מידע מובהק. נסה ניסוח אחר."
                
                tools_used.append("Web search (DuckDuckGo)")
                return output
        except Exception as e:
            print(f"Search error: {e}", flush=True)
        
        return "🔍 מצטער, לא הצלחתי לחפש באינטרנט. נסה שאלה אחרת."
    
    # ==========================================
    # FILE OPERATIONS - Natural Language
    # ==========================================
    
    # Create file - many patterns
    file_patterns = ["צור קובץ", "צור file", "create file", "תיצור קובץ", "תיצור file", "צור טקסט", "תכתוב קובץ"]
    if any(p in text_lower for p in file_patterns):
        # Extract filename and content
        filename = "myfile.txt"
        content = "Hello from Gamma!"
        
        # Try to find filename - check for "בשם" or "named" pattern
        name_found = False
        for p in ["בשם", "named", "שם", "file named", "filename"]:
            if p in text_lower:
                idx = text_lower.find(p)
                remaining = text_lower[idx + len(p):].strip()
                # Find where content starts
                for sep in ["with", "עם", "תוכן", "שכתוב"]:
                    if sep in remaining:
                        filename = remaining.split(sep)[0].strip()
                        content = remaining.split(sep)[1].strip()
                        name_found = True
                        break
                if not name_found:
                    # Get just the filename (first word)
                    words = remaining.split()
                    if words:
                        filename = words[0]
                break
        
        # Clean filename - keep dots but remove bad chars
        filename = filename.replace(" ", "_").replace('"', '').replace("'", "").replace(",", "")
        # Ensure .txt extension if missing
        if not filename.endswith(".txt"):
            filename = filename + ".txt"
        
        # If content wasn't extracted, try to find "עם" in original text
        if content == "Hello from Gamma!" and "עם" in original_task:
            parts = original_task.split("עם")
            if len(parts) > 1:
                content = parts[1].strip()
                # Clean content - remove trailing punctuation
                content = content.rstrip(".,!?")
        
        try:
            filepath = os.path.join(workspace, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            
            tools_used.append("Create file: " + filename)
            thoughts.append("יצרתי קובץ בשם " + filename)
            
            return "✅ נוצר קובץ חדש!\n\n📄 שם: " + filename + "\n📝 תוכן: " + content + "\n\nהקובץ נשמר בהצלחה! 🎉"
        except Exception as e:
            return "❌ שגיאה ביצירת הקובץ: " + str(e)
    
    # ==========================================
    # VERSION CHECKS - Natural Language
    # ==========================================
    
    # Order matters: check SPECIFIC patterns BEFORE generic "מה גרסת"
    version_patterns = [
        ("גרסת npm", "npm"), ("npm version", "npm"),
        ("גרסת node", "node"), ("node version", "node"),
        ("גרסת python", "python"), ("python version", "python"),
        ("גרסת git", "git"), ("git version", "git"),
        # Generic "what version" - check LAST, default to npm
        ("מה גרסת", "npm"),
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
            thoughts.append("מריץ פקודה: " + cmd)
            try:
                r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
                output = r.stdout.strip() if r.stdout else r.stderr.strip()
                if r.returncode == 0:
                    tools_used.append("Command: " + cmd)
                    return "✅ פקודה בוצעה!\n\n📤 Output:\n" + (output if output else "(אין פלט)")
                else:
                    return "❌ שגיאה:\n" + output
            except Exception as e:
                return "❌ שגיאה: " + str(e)
    
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
# MAIN LOGIC - ORDER MATTERS!
# ==========================================

print("\n--- THINKING ---", flush=True)

# Define text_lower for use in main logic
text_lower = original_task.lower()

# DETECT INPUT TYPE - Check commands BEFORE questions!
version_patterns = ["מה גרסת", "npm version", "גרסת npm", "גרסת node", "node version", "גרסת python", "python version", "גרסת git", "git version"]
command_patterns = ["צור קובץ", "create file", "תיצור", "צור טקסט", "list files", "מה יש", "אילו קבצים", "git status"]

# Check for version request FIRST
if any(p in text_lower for p in version_patterns):
    print("📋 Detected: VERSION CHECK", flush=True)
    thoughts.append("זו בקשת גרסה - אבדוק את הגרסה")
    response_text = handle_command(original_task, text_lower, thoughts, tools_used)
    
# Check for file/command operations SECOND
elif any(p in text_lower for p in command_patterns):
    print("⚡ Detected: COMMAND", flush=True)
    thoughts.append("זו פקודה - מבצע")
    response_text = handle_command(original_task, text_lower, thoughts, tools_used)

# THEN check for simple "run" command
elif "run " in text_lower:
    print("⚡ Detected: RUN COMMAND", flush=True)
    thoughts.append("פקודת run - מבצע")
    response_text = handle_command(original_task, text_lower, thoughts, tools_used)

# Check for WEB SEARCH before questions (things like "who is", "what is", "מי זה", etc.)
elif any(p in text_lower for p in ["who is", "what is", "מי זה", "מה זה", "חפש", "search", "google", "גוגל", "top", "2026", "פופולרי", "popular ai tools", "list of"]):
    print("🔍 Detected: WEB SEARCH", flush=True)
    thoughts.append("זה חיפוש באינטרנט - אחפש עבורו")
    response_text = handle_command(original_task, text_lower, thoughts, tools_used)
    
# FINALLY check for questions
elif any(q in original_task.lower() for q in ["מה", "איך", "למה", "היכן", "?", "what", "how", "why"]):
    print("🎯 Detected: QUESTION", flush=True)
    thoughts.append("זו שאלה - מחפש תשובה")
    response_text = handle_question(original_task)
    
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

# Detect task type for state
is_version = any(p in text_lower for p in version_patterns)
is_command_task = any(p in text_lower for p in command_patterns) or "run " in text_lower
is_question_task = any(q in original_task.lower() for q in ["מה", "איך", "למה", "מי", "היכן", "?", "what", "how", "why", "who"])

task_type = "version" if is_version else "command" if is_command_task else "question" if is_question_task else "general"

print("\n--- FINAL ---", flush=True)
print(f"Type: {task_type}", flush=True)
print(f"Tools: {len(tools_used)}", flush=True)
print(f"Status: SUCCESS", flush=True)

state["status"] = "completed"
state["response"] = response_text
state["task_type"] = task_type
state["tool_history"] = [{"tool": "chat", "count": len(tools_used)}]
state["thought_process"] = thoughts
state["tools_used"] = tools_used
state["completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

with open(state_file, "w", encoding="utf-8") as f:
    json.dump(state, f, ensure_ascii=False, indent=2)

print("\n=== DONE ===", flush=True)
print(f"Response: {response_text[:100]}...", flush=True)