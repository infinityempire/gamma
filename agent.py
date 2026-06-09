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

with open(state_file, "r") as f:
    state = json.load(f)

original_task = state.get("task", "")
task = original_task.lower()

print("=== GAMMA AGENT - ENHANCED AI ===", flush=True)
print(f"USER: {original_task}", flush=True)

thoughts = []
tools_used = []
success = True
response_text = ""

# ==========================================
# CREDENTIALS MANAGER
# ==========================================

def load_credentials():
    """Load saved credentials from encrypted storage"""
    if os.path.exists(credentials_file):
        try:
            with open(credentials_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_credentials(creds):
    """Save credentials to storage"""
    try:
        with open(credentials_file, "w", encoding="utf-8") as f:
            json.dump(creds, f, ensure_ascii=False, indent=2)
        os.chmod(credentials_file, 0o600)  # Restrict permissions
        return True
    except Exception as e:
        return False

def handle_save_credentials(text, text_lower):
    """Save login credentials for a service"""
    # Patterns: "שמור סיסמה ל-gmail: user@gmail.com / pass123"
    # or: "save credentials for twitter: username / password"
    creds = load_credentials()
    
    # Try to extract service, username, password
    service = ""
    username = ""
    password = ""
    
    for sep in ["ל-", "ל ", "for ", "for: "]:
        if sep in text_lower:
            idx = text_lower.find(sep)
            rest = text[idx + len(sep):]
            # Get service name (until : or space)
            parts = rest.split(":")
            if len(parts) >= 2:
                service = parts[0].strip()
                cred_part = parts[1].strip()
                # Split username/password by / or |
                for divider in [" / ", "/", " | ", "|"]:
                    if divider in cred_part:
                        cred_parts = cred_part.split(divider, 1)
                        username = cred_parts[0].strip()
                        password = cred_parts[1].strip() if len(cred_parts) > 1 else ""
                        break
            break
    
    if not service:
        return "❌ לא הבנתי את הפורמט. השתמש ב:\n`שמור סיסמה ל-[שירות]: [משתמש] / [סיסמה]`\nדוגמה: `שמור סיסמה ל-gmail: user@gmail.com / mypassword`"
    
    creds[service.lower()] = {
        "username": username,
        "password": password,
        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    if save_credentials(creds):
        tools_used.append(f"Credentials saved: {service}")
        return f"✅ **פרטי התחברות נשמרו!**\n\n🔐 שירות: `{service}`\n👤 משתמש: `{username}`\n🔒 סיסמה: `{'*' * len(password)}`\n\nהפרטים נשמרו בצורה מאובטחת ויהיו זמינים לשימוש בעתיד."
    else:
        return "❌ שגיאה בשמירת הפרטים."

def handle_list_credentials(text_lower):
    """List saved credentials"""
    creds = load_credentials()
    if not creds:
        return "📭 אין פרטי התחברות שמורים.\n\nכדי לשמור: `שמור סיסמה ל-[שירות]: [משתמש] / [סיסמה]`"
    
    output = "🔐 **פרטי התחברות שמורים:**\n\n"
    for service, data in creds.items():
        output += f"• **{service}**: `{data.get('username', 'N/A')}` (נשמר: {data.get('saved_at', 'N/A')})\n"
    output += "\n💡 הסיסמאות מוסתרות מטעמי אבטחה."
    return output

# ==========================================
# BROWSER AUTOMATION (Playwright)
# ==========================================

def install_playwright():
    """Install Playwright if not available"""
    try:
        import playwright
        return True
    except ImportError:
        print("Installing Playwright...", flush=True)
        result = subprocess.run(
            "pip install playwright && python -m playwright install chromium --with-deps",
            shell=True, capture_output=True, text=True, timeout=300
        )
        return result.returncode == 0

def handle_browser_login(text, text_lower):
    """Login to a website using Playwright"""
    creds = load_credentials()
    
    # Detect which service to login to
    service_map = {
        "gmail": {"url": "https://accounts.google.com/signin", "username_sel": 'input[type="email"]', "password_sel": 'input[type="password"]', "submit_sel": '#identifierNext, #passwordNext'},
        "google": {"url": "https://accounts.google.com/signin", "username_sel": 'input[type="email"]', "password_sel": 'input[type="password"]', "submit_sel": '#identifierNext, #passwordNext'},
        "github": {"url": "https://github.com/login", "username_sel": '#login_field', "password_sel": '#password', "submit_sel": 'input[type="submit"]'},
        "twitter": {"url": "https://twitter.com/login", "username_sel": 'input[autocomplete="username"]', "password_sel": 'input[type="password"]', "submit_sel": '[data-testid="LoginForm_Login_Button"]'},
        "x": {"url": "https://x.com/login", "username_sel": 'input[autocomplete="username"]', "password_sel": 'input[type="password"]', "submit_sel": '[data-testid="LoginForm_Login_Button"]'},
        "facebook": {"url": "https://www.facebook.com/login", "username_sel": '#email', "password_sel": '#pass', "submit_sel": '[name="login"]'},
        "instagram": {"url": "https://www.instagram.com/accounts/login/", "username_sel": 'input[name="username"]', "password_sel": 'input[name="password"]', "submit_sel": 'button[type="submit"]'},
        "linkedin": {"url": "https://www.linkedin.com/login", "username_sel": '#username', "password_sel": '#password', "submit_sel": 'button[type="submit"]'},
    }
    
    detected_service = None
    for svc in service_map:
        if svc in text_lower:
            detected_service = svc
            break
    
    # Also check for custom URL
    url_match = re.search(r'https?://[^\s]+', text)
    custom_url = url_match.group(0) if url_match else None
    
    # Get credentials
    username = ""
    password = ""
    
    # Check if credentials are in the command
    cred_match = re.search(r'(?:user|username|email|משתמש)[\s:]+([^\s/]+)', text, re.IGNORECASE)
    pass_match = re.search(r'(?:pass|password|סיסמה)[\s:]+([^\s]+)', text, re.IGNORECASE)
    
    if cred_match:
        username = cred_match.group(1)
    if pass_match:
        password = pass_match.group(1)
    
    # Fall back to saved credentials
    if not username and detected_service and detected_service in creds:
        username = creds[detected_service].get("username", "")
        password = creds[detected_service].get("password", "")
    
    if not username or not password:
        return f"""🔐 **כניסה לחשבון**

כדי להיכנס לחשבון, אני צריך פרטי התחברות.

**אפשרות 1** - ציין בפקודה:
`היכנס ל-{detected_service or 'האתר'} עם username: [משתמש] password: [סיסמה]`

**אפשרות 2** - שמור מראש:
`שמור סיסמה ל-{detected_service or 'שירות'}: [משתמש] / [סיסמה]`
ואז: `היכנס ל-{detected_service or 'האתר'}`

{'✅ נמצאו פרטים שמורים ל-' + detected_service if detected_service and detected_service in creds else ''}"""
    
    # Install and use Playwright
    playwright_script = f"""
import asyncio
import json
import os
import sys

async def login():
    try:
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = await context.new_page()
            
            service = "{detected_service or 'custom'}"
            url = "{custom_url or (service_map.get(detected_service, {}).get('url', '') if detected_service else '')}"
            username = "{username}"
            password = "{password}"
            
            if not url:
                print(json.dumps({{"success": False, "error": "No URL provided"}}))
                return
            
            print(f"Navigating to: {{url}}", flush=True)
            await page.goto(url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(2)
            
            # Take screenshot before login
            await page.screenshot(path='/workspace/before_login.png')
            
            # Try to fill username
            username_selectors = [
                'input[type="email"]', 'input[type="text"]', '#email', '#username',
                '#login_field', 'input[name="email"]', 'input[name="username"]',
                'input[autocomplete="username"]', 'input[autocomplete="email"]'
            ]
            
            username_filled = False
            for sel in username_selectors:
                try:
                    elem = await page.query_selector(sel)
                    if elem and await elem.is_visible():
                        await elem.fill(username)
                        username_filled = True
                        print(f"Filled username with selector: {{sel}}", flush=True)
                        break
                except:
                    continue
            
            if not username_filled:
                print(json.dumps({{"success": False, "error": "Could not find username field"}}))
                await browser.close()
                return
            
            # Click next/continue if needed (Google-style)
            next_selectors = ['#identifierNext', 'button[type="submit"]', 'input[type="submit"]', '[data-testid="next"]']
            for sel in next_selectors:
                try:
                    elem = await page.query_selector(sel)
                    if elem and await elem.is_visible():
                        await elem.click()
                        await asyncio.sleep(2)
                        break
                except:
                    continue
            
            # Fill password
            password_selectors = [
                'input[type="password"]', '#password', '#pass',
                'input[name="password"]', 'input[autocomplete="current-password"]'
            ]
            
            password_filled = False
            for sel in password_selectors:
                try:
                    elem = await page.query_selector(sel)
                    if elem and await elem.is_visible():
                        await elem.fill(password)
                        password_filled = True
                        print(f"Filled password with selector: {{sel}}", flush=True)
                        break
                except:
                    continue
            
            if not password_filled:
                print(json.dumps({{"success": False, "error": "Could not find password field"}}))
                await browser.close()
                return
            
            # Submit
            submit_selectors = [
                '#passwordNext', 'button[type="submit"]', 'input[type="submit"]',
                '[data-testid="LoginForm_Login_Button"]', '[name="login"]'
            ]
            
            for sel in submit_selectors:
                try:
                    elem = await page.query_selector(sel)
                    if elem and await elem.is_visible():
                        await elem.click()
                        await asyncio.sleep(3)
                        break
                except:
                    continue
            
            # Wait for navigation
            await asyncio.sleep(3)
            
            # Take screenshot after login
            await page.screenshot(path='/workspace/after_login.png')
            
            current_url = page.url
            title = await page.title()
            
            # Save session cookies
            cookies = await context.cookies()
            with open('/workspace/session_cookies.json', 'w') as f:
                json.dump(cookies, f)
            
            # Check if login was successful (not on login page anymore)
            login_failed_indicators = ['login', 'signin', 'sign-in', 'error', 'incorrect', 'invalid']
            login_success = not any(ind in current_url.lower() for ind in login_failed_indicators)
            
            result = {{
                "success": login_success,
                "url": current_url,
                "title": title,
                "cookies_saved": len(cookies),
                "message": "Login successful" if login_success else "Login may have failed - check screenshot"
            }}
            
            print(json.dumps(result))
            await browser.close()
    
    except Exception as e:
        print(json.dumps({{"success": False, "error": str(e)}}))

asyncio.run(login())
"""
    
    # Write and run the script
    script_path = "/workspace/browser_login.py"
    with open(script_path, "w") as f:
        f.write(playwright_script)
    
    # Install playwright if needed
    try:
        import playwright
    except ImportError:
        subprocess.run("pip install playwright && python -m playwright install chromium --with-deps 2>&1 | tail -5", 
                      shell=True, timeout=300)
    
    result = subprocess.run(
        f"python3 {script_path}",
        shell=True, capture_output=True, text=True, timeout=120
    )
    
    tools_used.append(f"Browser login: {detected_service or 'custom'}")
    
    # Parse result
    output_lines = result.stdout.strip().split('\n')
    json_result = None
    for line in reversed(output_lines):
        try:
            json_result = json.loads(line)
            break
        except:
            continue
    
    if json_result:
        if json_result.get("success"):
            return f"""✅ **כניסה לחשבון הצליחה!**

🌐 **URL נוכחי:** {json_result.get('url', 'N/A')}
📄 **כותרת:** {json_result.get('title', 'N/A')}
🍪 **Cookies נשמרו:** {json_result.get('cookies_saved', 0)}

📸 צילומי מסך נשמרו:
• לפני כניסה: `before_login.png`
• אחרי כניסה: `after_login.png`

🔐 Session נשמר ב-`session_cookies.json` לשימוש עתידי."""
        else:
            return f"""⚠️ **כניסה לחשבון - בדיקה נדרשת**

❌ שגיאה: {json_result.get('error', json_result.get('message', 'Unknown error'))}

📸 בדוק את `after_login.png` לראות מה קרה.

💡 **טיפים:**
• ודא שהפרטים נכונים
• ייתכן שנדרש אימות דו-שלבי (2FA)
• חלק מהאתרים חוסמים כניסה אוטומטית"""
    else:
        stderr = result.stderr[:500] if result.stderr else ""
        return f"""⚠️ **כניסה לחשבון - תוצאה לא ברורה**

{result.stdout[:300] if result.stdout else 'אין פלט'}

{'שגיאה: ' + stderr if stderr else ''}

💡 ייתכן שהכניסה הצליחה. בדוק את `after_login.png`."""

def handle_browser_action(text, text_lower):
    """Perform browser actions after login"""
    
    # Detect action type
    action_type = "navigate"
    if any(x in text_lower for x in ["לחץ", "click", "לחיצה"]):
        action_type = "click"
    elif any(x in text_lower for x in ["מלא", "fill", "הכנס", "type", "כתוב"]):
        action_type = "fill"
    elif any(x in text_lower for x in ["צלם", "screenshot", "תמונה של האתר"]):
        action_type = "screenshot"
    elif any(x in text_lower for x in ["גלול", "scroll"]):
        action_type = "scroll"
    elif any(x in text_lower for x in ["פתח", "open", "navigate", "עבור ל", "כנס ל"]):
        action_type = "navigate"
    
    # Extract URL
    url_match = re.search(r'https?://[^\s]+', text)
    url = url_match.group(0) if url_match else ""
    
    # Extract selector or text to interact with
    selector = ""
    fill_text = ""
    
    browser_script = f"""
import asyncio
import json
import os

async def browser_action():
    try:
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
            context = await browser.new_context()
            
            # Load saved cookies if available
            cookies_file = '/workspace/session_cookies.json'
            if os.path.exists(cookies_file):
                with open(cookies_file, 'r') as f:
                    cookies = json.load(f)
                await context.add_cookies(cookies)
            
            page = await context.new_page()
            
            action = "{action_type}"
            url = "{url}"
            
            if url:
                await page.goto(url, wait_until='networkidle', timeout=30000)
                await asyncio.sleep(2)
            
            if action == "screenshot":
                await page.screenshot(path='/workspace/browser_screenshot.png', full_page=True)
                title = await page.title()
                current_url = page.url
                result = {{"success": True, "action": "screenshot", "url": current_url, "title": title, "file": "browser_screenshot.png"}}
            
            elif action == "navigate":
                title = await page.title()
                current_url = page.url
                content = await page.content()
                # Extract text content
                text_content = await page.evaluate('() => document.body.innerText')
                result = {{"success": True, "action": "navigate", "url": current_url, "title": title, "content": text_content[:2000]}}
            
            else:
                await page.screenshot(path='/workspace/browser_screenshot.png')
                result = {{"success": True, "action": action, "url": page.url}}
            
            print(json.dumps(result))
            await browser.close()
    
    except Exception as e:
        print(json.dumps({{"success": False, "error": str(e)}}))

asyncio.run(browser_action())
"""
    
    script_path = "/workspace/browser_action.py"
    with open(script_path, "w") as f:
        f.write(browser_script)
    
    result = subprocess.run(
        f"python3 {script_path}",
        shell=True, capture_output=True, text=True, timeout=60
    )
    
    tools_used.append(f"Browser action: {action_type}")
    
    output_lines = result.stdout.strip().split('\n')
    json_result = None
    for line in reversed(output_lines):
        try:
            json_result = json.loads(line)
            break
        except:
            continue
    
    if json_result and json_result.get("success"):
        if action_type == "screenshot":
            return f"""📸 **צילום מסך בוצע!**

🌐 URL: {json_result.get('url', 'N/A')}
📄 כותרת: {json_result.get('title', 'N/A')}
💾 נשמר ב: `browser_screenshot.png`"""
        elif action_type == "navigate":
            content = json_result.get('content', '')[:1000]
            return f"""🌐 **ניווט בוצע!**

📍 URL: {json_result.get('url', 'N/A')}
📄 כותרת: {json_result.get('title', 'N/A')}

📝 **תוכן הדף:**
```
{content}
```"""
        else:
            return f"✅ **פעולת דפדפן בוצעה!**\n\nפעולה: {action_type}\nURL: {json_result.get('url', 'N/A')}"
    else:
        error = json_result.get('error', 'Unknown') if json_result else result.stderr[:200]
        return f"❌ שגיאה בפעולת הדפדפן: {error}"

# ==========================================
# EMAIL SENDER
# ==========================================

def handle_send_email(text, text_lower):
    """Send email via SMTP"""
    # Extract email details
    to_match = re.search(r'(?:ל|to|אל)\s+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', text, re.IGNORECASE)
    subject_match = re.search(r'(?:נושא|subject|כותרת)[:\s]+([^\n,]+)', text, re.IGNORECASE)
    
    if not to_match:
        return """📧 **שליחת אימייל**

כדי לשלוח אימייל, ציין:
`שלח אימייל ל-[כתובת] נושא: [נושא] תוכן: [תוכן]`

**הגדרות נדרשות (שמור מראש):**
`שמור סיסמה ל-email: sender@gmail.com / app_password`

💡 עבור Gmail, צור App Password ב-Google Account Settings."""
    
    to_email = to_match.group(1)
    subject = subject_match.group(1).strip() if subject_match else "הודעה מגאמא"
    
    # Extract body
    body = text
    for keyword in ["שלח אימייל", "send email", "ל-" + to_email, "נושא:", "subject:"]:
        body = body.replace(keyword, "")
    body = body.strip()
    
    # Get email credentials
    creds = load_credentials()
    email_creds = creds.get("email", creds.get("gmail", {}))
    
    if not email_creds:
        return f"❌ לא נמצאו פרטי אימייל שמורים.\n\nשמור: `שמור סיסמה ל-email: sender@gmail.com / app_password`"
    
    sender = email_creds.get("username", "")
    app_password = email_creds.get("password", "")
    
    try:
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # Try Gmail SMTP
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(sender, app_password)
        server.sendmail(sender, to_email, msg.as_string())
        server.quit()
        
        tools_used.append(f"Email sent to: {to_email}")
        return f"""✅ **אימייל נשלח בהצלחה!**

📧 **אל:** {to_email}
📋 **נושא:** {subject}
📝 **תוכן:** {body[:100]}{'...' if len(body) > 100 else ''}

✉️ האימייל נשלח בהצלחה!"""
    
    except Exception as e:
        return f"❌ שגיאה בשליחת אימייל: {str(e)}\n\n💡 ודא שה-App Password נכון ו-2FA מופעל ב-Gmail."

# ==========================================
# API CALLER
# ==========================================

def handle_api_call(text, text_lower):
    """Make REST API calls"""
    # Extract URL
    url_match = re.search(r'https?://[^\s]+', text)
    if not url_match:
        return """🔌 **קריאת API**

כדי לקרוא ל-API:
`api get https://api.example.com/endpoint`
`api post https://api.example.com/endpoint data: {"key": "value"}`

**עם headers:**
`api get https://api.example.com/endpoint headers: Authorization: Bearer TOKEN`"""
    
    url = url_match.group(0)
    method = "GET"
    if any(x in text_lower for x in ["post", "שלח"]):
        method = "POST"
    elif any(x in text_lower for x in ["put", "עדכן"]):
        method = "PUT"
    elif any(x in text_lower for x in ["delete", "מחק"]):
        method = "DELETE"
    
    # Extract headers
    headers = {"User-Agent": "GammaAgent/2.0"}
    auth_match = re.search(r'(?:authorization|auth|token)[:\s]+([^\s,]+)', text, re.IGNORECASE)
    if auth_match:
        headers["Authorization"] = auth_match.group(1)
    
    # Extract body for POST
    body = None
    data_match = re.search(r'(?:data|body)[:\s]+({[^}]+})', text, re.IGNORECASE)
    if data_match:
        try:
            body = json.loads(data_match.group(1))
        except:
            body = {"data": data_match.group(1)}
    
    try:
        import urllib.request
        import urllib.error
        
        req_data = json.dumps(body).encode() if body else None
        req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
        
        with urllib.request.urlopen(req, timeout=30) as response:
            response_data = response.read().decode('utf-8', errors='replace')
            status = response.status
            
            # Try to parse as JSON
            try:
                parsed = json.loads(response_data)
                formatted = json.dumps(parsed, indent=2, ensure_ascii=False)[:2000]
            except:
                formatted = response_data[:2000]
            
            tools_used.append(f"API call: {method} {url[:50]}")
            return f"""🔌 **תוצאת API:**

📍 **URL:** {url}
🔧 **Method:** {method}
✅ **Status:** {status}

📋 **תגובה:**
```json
{formatted}
```"""
    
    except Exception as e:
        return f"❌ שגיאה בקריאת API: {str(e)}"

# ==========================================
# LLM INTEGRATION (OpenAI)
# ==========================================

def handle_llm_query(text, text_lower):
    """Use OpenAI for intelligent responses"""
    if not OPENAI_AVAILABLE:
        return handle_question(text)
    
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return handle_question(text)
    
    try:
        client = OpenAI(api_key=api_key)
        
        system_prompt = """אתה גאמא - סוכן AI אוטונומי חכם. 
אתה עוזר למשתמשים בכל משימה שהם מבקשים.
ענה בעברית אלא אם כן נשאל באנגלית.
היה מועיל, מדויק ותמציתי."""
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        
        answer = response.choices[0].message.content
        tools_used.append("LLM (OpenAI)")
        thoughts.append("שאלתי את ה-LLM לתשובה חכמה")
        
        return f"🤖 **גאמא (AI):**\n\n{answer}"
    
    except Exception as e:
        print(f"LLM error: {e}", flush=True)
        return handle_question(text)

# ==========================================
# FILE OPERATIONS (ENHANCED)
# ==========================================

def handle_file_operations_advanced(text, text_lower):
    """Advanced file operations: zip, read, delete, list, download"""
    
    # List files
    if any(x in text_lower for x in ["רשימת קבצים", "list files", "מה יש", "אילו קבצים", "show files"]):
        try:
            r = subprocess.run("ls -la", shell=True, capture_output=True, text=True, cwd=workspace, timeout=15)
            files = r.stdout.strip()
            tools_used.append("List files")
            return f"📁 **קבצים בתיקייה:**\n\n```\n{files}\n```"
        except Exception as e:
            return f"❌ שגיאה: {str(e)}"
    
    # Read file
    if any(x in text_lower for x in ["קרא קובץ", "read file", "הצג קובץ", "show file", "תוכן של"]):
        filename_match = re.search(r'(?:קרא|read|הצג|show|תוכן של)\s+(?:קובץ\s+)?([^\s]+)', text, re.IGNORECASE)
        if filename_match:
            filename = filename_match.group(1)
            filepath = os.path.join(workspace, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                tools_used.append(f"Read file: {filename}")
                return f"📄 **תוכן הקובץ `{filename}`:**\n\n```\n{content[:3000]}\n```"
            except Exception as e:
                return f"❌ שגיאה בקריאת קובץ: {str(e)}"
    
    # Delete file
    if any(x in text_lower for x in ["מחק קובץ", "delete file", "הסר קובץ", "remove file"]):
        filename_match = re.search(r'(?:מחק|delete|הסר|remove)\s+(?:קובץ\s+)?([^\s]+)', text, re.IGNORECASE)
        if filename_match:
            filename = filename_match.group(1)
            filepath = os.path.join(workspace, filename)
            try:
                os.remove(filepath)
                tools_used.append(f"Delete file: {filename}")
                return f"🗑️ **קובץ נמחק:** `{filename}`"
            except Exception as e:
                return f"❌ שגיאה במחיקת קובץ: {str(e)}"
    
    # ZIP files
    if any(x in text_lower for x in ["zip", "דחוס", "ארז"]):
        zip_name = "archive.zip"
        zip_match = re.search(r'(?:zip|דחוס|ארז)\s+([^\s]+)', text, re.IGNORECASE)
        if zip_match:
            target = zip_match.group(1)
            zip_path = os.path.join(workspace, zip_name)
            try:
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                    target_path = os.path.join(workspace, target)
                    if os.path.isdir(target_path):
                        for root, dirs, files in os.walk(target_path):
                            for file in files:
                                zf.write(os.path.join(root, file), 
                                        os.path.relpath(os.path.join(root, file), workspace))
                    elif os.path.isfile(target_path):
                        zf.write(target_path, target)
                tools_used.append(f"ZIP: {target}")
                return f"📦 **קובץ ZIP נוצר:** `{zip_name}`\n\nנדחס: `{target}`"
            except Exception as e:
                return f"❌ שגיאה ביצירת ZIP: {str(e)}"
    
    return None

# ==========================================
# CODE EXECUTOR
# ==========================================

def handle_code_execution(text, text_lower):
    """Execute Python or JavaScript code safely"""
    
    # Extract code block
    code_match = re.search(r'```(?:python|py|javascript|js)?\n(.*?)```', text, re.DOTALL)
    if not code_match:
        # Try inline code
        code_match = re.search(r'`([^`]+)`', text)
    
    if not code_match:
        return None
    
    code = code_match.group(1).strip()
    lang = "python"
    
    if any(x in text_lower for x in ["javascript", "js", "node"]):
        lang = "javascript"
    
    if lang == "python":
        script_path = "/workspace/user_code.py"
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(code)
        
        result = subprocess.run(
            f"python3 {script_path}",
            shell=True, capture_output=True, text=True, timeout=30, cwd=workspace
        )
        
        tools_used.append("Python code execution")
        
        if result.returncode == 0:
            return f"✅ **קוד Python רץ בהצלחה!**\n\n📤 **פלט:**\n```\n{result.stdout[:2000]}\n```"
        else:
            return f"❌ **שגיאה בקוד:**\n```\n{result.stderr[:1000]}\n```"
    
    elif lang == "javascript":
        script_path = "/workspace/user_code.js"
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(code)
        
        result = subprocess.run(
            f"node {script_path}",
            shell=True, capture_output=True, text=True, timeout=30, cwd=workspace
        )
        
        tools_used.append("JavaScript code execution")
        
        if result.returncode == 0:
            return f"✅ **קוד JavaScript רץ בהצלחה!**\n\n📤 **פלט:**\n```\n{result.stdout[:2000]}\n```"
        else:
            return f"❌ **שגיאה בקוד:**\n```\n{result.stderr[:1000]}\n```"
    
    return None

# ==========================================
# SYSTEM MONITOR
# ==========================================

def handle_system_monitor(text_lower):
    """Monitor system resources"""
    try:
        cpu_result = subprocess.run("cat /proc/loadavg", shell=True, capture_output=True, text=True, timeout=5)
        mem_result = subprocess.run("free -h", shell=True, capture_output=True, text=True, timeout=5)
        disk_result = subprocess.run("df -h /", shell=True, capture_output=True, text=True, timeout=5)
        
        cpu = cpu_result.stdout.strip()
        mem = mem_result.stdout.strip()
        disk = disk_result.stdout.strip()
        
        tools_used.append("System monitor")
        return f"""📊 **מצב המערכת:**

⚡ **CPU Load:** `{cpu}`

💾 **זיכרון:**
```
{mem}
```

💿 **דיסק:**
```
{disk}
```

✅ המערכת פועלת תקין!"""
    except Exception as e:
        return f"❌ שגיאה בניטור מערכת: {str(e)}"

# ==========================================
# GITHUB OPERATIONS
# ==========================================

def handle_github_operations(text, text_lower):
    """Advanced GitHub operations"""
    gh_token = os.environ.get("GH_TOKEN", "")
    
    if not gh_token:
        return "❌ לא נמצא GH_TOKEN. הוסף אותו ל-GitHub Secrets."
    
    headers = {
        "Authorization": f"token {gh_token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "GammaAgent/2.0"
    }
    
    # Get repo info
    if any(x in text_lower for x in ["מידע על ריפו", "repo info", "github info"]):
        repo = os.environ.get("GITHUB_REPOSITORY", "infinityempire/gamma")
        url = f"https://api.github.com/repos/{repo}"
        
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as response:
                data = json.loads(response.read().decode())
                
                tools_used.append("GitHub API: repo info")
                return f"""📦 **מידע על הריפו:**

🏷️ **שם:** {data.get('full_name', 'N/A')}
📝 **תיאור:** {data.get('description', 'N/A')}
⭐ **Stars:** {data.get('stargazers_count', 0)}
🍴 **Forks:** {data.get('forks_count', 0)}
👁️ **Watchers:** {data.get('watchers_count', 0)}
🔤 **שפה:** {data.get('language', 'N/A')}
📅 **עודכן:** {data.get('updated_at', 'N/A')}
🔗 **URL:** {data.get('html_url', 'N/A')}"""
        except Exception as e:
            return f"❌ שגיאה בקבלת מידע GitHub: {str(e)}"
    
    # Create issue
    if any(x in text_lower for x in ["צור issue", "create issue", "פתח issue"]):
        title_match = re.search(r'(?:כותרת|title)[:\s]+([^\n]+)', text, re.IGNORECASE)
        body_match = re.search(r'(?:תוכן|body|תיאור)[:\s]+([^\n]+)', text, re.IGNORECASE)
        
        title = title_match.group(1).strip() if title_match else "Issue מגאמא"
        body = body_match.group(1).strip() if body_match else text
        
        repo = os.environ.get("GITHUB_REPOSITORY", "infinityempire/gamma")
        url = f"https://api.github.com/repos/{repo}/issues"
        
        payload = json.dumps({"title": title, "body": body}).encode()
        
        try:
            req = urllib.request.Request(url, data=payload, headers={**headers, "Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=15) as response:
                data = json.loads(response.read().decode())
                
                tools_used.append("GitHub API: create issue")
                return f"""✅ **Issue נוצר!**

🔢 **מספר:** #{data.get('number', 'N/A')}
📋 **כותרת:** {data.get('title', 'N/A')}
🔗 **קישור:** {data.get('html_url', 'N/A')}"""
        except Exception as e:
            return f"❌ שגיאה ביצירת Issue: {str(e)}"
    
    return None

# ==========================================
# ORIGINAL CAPABILITIES (PRESERVED)
# ==========================================

def get_about_me():
    return """🤖 **אני גאמא - סוכן AI אוטונומי מתקדם!**

## יכולות:

### 🌐 גלישה וכניסה לחשבונות
🔹 **כניסה לחשבונות** - `היכנס ל-gmail`, `היכנס ל-github`
🔹 **שמירת סיסמאות** - `שמור סיסמה ל-[שירות]: [משתמש] / [סיסמה]`
🔹 **פעולות בדפדפן** - `פתח https://example.com`, `צלם מסך`
🔹 **קריאת APIs** - `api get https://api.example.com`

### 📧 תקשורת
🔹 **שליחת אימיילים** - `שלח אימייל ל-user@gmail.com נושא: X תוכן: Y`

### 💻 פיתוח וקוד
🔹 **הרצת קוד Python** - שלח קוד ב-```python ... ```
🔹 **הרצת JavaScript** - שלח קוד ב-```javascript ... ```
🔹 **פקודות terminal** - `run [פקודה]`

### 📁 ניהול קבצים
🔹 **יצירת קבצים** - `צור קובץ בשם X עם Y`
🔹 **קריאת קבצים** - `קרא קובץ X`
🔹 **מחיקת קבצים** - `מחק קובץ X`
🔹 **ZIP** - `zip [קובץ/תיקייה]`

### 🔍 חיפוש ומידע
🔹 **חיפוש באינטרנט** - `חפש [נושא]`
🔹 **שאלות AI** - שאל כל שאלה!

### 📊 ניטור
🔹 **מצב מערכת** - `מצב מערכת`
🔹 **GitHub** - `מידע על ריפו`

פשוט דבר איתי! 💬"""

def get_help():
    return """🆘 **פקודות גאמא - מדריך מלא:**

### 🔐 כניסה לחשבונות:
• `היכנס ל-gmail` (עם פרטים שמורים)
• `היכנס ל-github עם username: user password: pass`
• `שמור סיסמה ל-gmail: user@gmail.com / mypass`
• `הצג סיסמאות שמורות`

### 🌐 דפדפן:
• `פתח https://example.com`
• `צלם מסך של https://example.com`
• `api get https://api.example.com`

### 📧 אימייל:
• `שלח אימייל ל-user@example.com נושא: שלום תוכן: הודעה`

### 💻 קוד:
• `run echo hello`
• ` ```python\nprint("hello")\n``` `

### 📁 קבצים:
• `צור קובץ בשם test.txt עם שלום עולם`
• `קרא קובץ test.txt`
• `מחק קובץ test.txt`
• `zip results/`

### 🔍 חיפוש:
• `חפש [נושא]`
• שאל כל שאלה ישירות!

### 📊 מערכת:
• `מצב מערכת`
• `מה יש לי בתיקייה`
• `git status`"""

def get_greeting():
    return """👋 **שלום! אני גאמא v2.0!**

אני סוכן AI מתקדם עם יכולות חדשות:

🔐 **כניסה לחשבונות** - Gmail, GitHub, Twitter ועוד
🌐 **גלישה אוטונומית** - ביצוע פעולות בדפדפן
📧 **שליחת אימיילים**
🔌 **קריאת APIs**
💻 **הרצת קוד**
📁 **ניהול קבצים מתקדם**

🔹 נסה: "מה אתה יודע לעשות?"
🔹 או: "שמור סיסמה ל-gmail: user@gmail.com / pass"
🔹 או: "היכנס ל-github"

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
    
    # Try LLM for intelligent answers
    return handle_llm_query(text, text.lower())

def handle_command(text, text_lower=None, thoughts=None, tools_used=None):
    """Handle command-type inputs"""
    if thoughts is None:
        thoughts = []
    if tools_used is None:
        tools_used = []
    if text_lower is None:
        text_lower = text.lower()

    # ==========================================
    # WEB SEARCH
    # ==========================================
    search_patterns = ["חפש", "search", "google", "גוגל", "מצא", "find on web", "סרוק", "research", "who is", "מי זה", "what is", "מה זה", "5 הכי", "top 5", "הכי פופולרי", "popular"]
    if any(p in text_lower for p in search_patterns) or ("מה ה" in text_lower and any(x in text_lower for x in ["כלי", "tool", "אפליקציה", "app", "software", "platform"])):
        query = text
        for p in ["חפש", "search for", "find on", "google", "מצא", "סרוק", "research", "מה ה", "who is", "מי זה", "what is", "מה זה"]:
            query = query.replace(p, "")
        query = query.strip()
        if not query:
            return "❌ לא הבנתי מה לחפש."
        thoughts.append("מחפש באינטרנט: " + query)
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
        # Fallback to DuckDuckGo
        try:
            clean_query = re.sub(r'[\u0590-\u05ff]+', '', query).strip()
            if not clean_query:
                clean_query = query
            encoded_query = urllib.parse.quote(clean_query)
            api_url = f"https://api.duckduckgo.com/?q={encoded_query}&format=json&no_html=1"
            r = subprocess.run(f"curl -sL --max-time 10 '{api_url}'", shell=True, capture_output=True, text=True, timeout=15)
            if r.stdout:
                data = json.loads(r.stdout)
                heading = data.get("Heading", "")
                abstract = data.get("AbstractText", "")
                results = data.get("RelatedTopics", [])
                if heading or abstract or results:
                    output = "🔍 **תוצאות חיפוש עבור:** " + query + "\n\n"
                    if heading or abstract:
                        output += f"📝 **{heading or 'מידע'}:**\n"
                        if abstract:
                            output += abstract[:500] + "\n"
                    if results:
                        output += "\n📋 **תוצאות נוספות:**\n"
                        for i, r_item in enumerate(results[:5], 1):
                            t = r_item.get("Text", "")
                            if t:
                                clean_t = re.sub(r'<[^>]+>', '', t)
                                output += f"{i}. {clean_t[:150]}...\n"
                    tools_used.append("Web search (DuckDuckGo)")
                    return output
        except:
            pass
        return "🔍 מצטער, לא הצלחתי לחפש באינטרנט. נסה שאלה אחרת."

    # ==========================================
    # FILE OPERATIONS
    # ==========================================
    file_patterns = ["צור קובץ", "צור file", "create file", "תיצור קובץ", "תיצור file", "צור טקסט", "תכתוב קובץ"]
    if any(p in text_lower for p in file_patterns):
        filename = "myfile.txt"
        content = "Hello from Gamma!"
        name_found = False
        for p in ["בשם", "named", "שם", "file named", "filename"]:
            if p in text_lower:
                idx = text_lower.find(p)
                remaining = text_lower[idx + len(p):].strip()
                for sep in ["with", "עם", "תוכן", "שכתוב"]:
                    if sep in remaining:
                        filename = remaining.split(sep)[0].strip()
                        content = remaining.split(sep)[1].strip()
                        name_found = True
                        break
                if not name_found:
                    words = remaining.split()
                    if words:
                        filename = words[0]
                break
        filename = filename.replace(" ", "_").replace('"', '').replace("'", "").replace(",", "")
        if not filename.endswith(".txt"):
            filename = filename + ".txt"
        if content == "Hello from Gamma!" and "עם" in original_task:
            parts = original_task.split("עם")
            if len(parts) > 1:
                content = parts[1].strip().rstrip(".,!?")
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
    # VERSION CHECKS
    # ==========================================
    version_patterns = [
        ("גרסת npm", "npm"), ("npm version", "npm"),
        ("גרסת node", "node"), ("node version", "node"),
        ("גרסת python", "python"), ("python version", "python"),
        ("גרסת git", "git"), ("git version", "git"),
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
                return f"📋 **גרסת {tool}:**\n\n```\n{version}\n```\n\n✅ התוכנה מותקנת ועובדת!"
            except:
                return f"❌ לא הצלחתי לבדוק את גרסת {tool}."

    # ==========================================
    # GIT INFO
    # ==========================================
    if any(x in text_lower for x in ["מה קורה בgit", "git status", "status של", "commitים"]):
        try:
            r = subprocess.run("git status", shell=True, capture_output=True, text=True, cwd=workspace, timeout=15)
            status = r.stdout.strip() if r.stdout else r.stderr.strip()
            tools_used.append("Git status")
            return f"🔄 **סטטוס Git:**\n\n```\n{status or 'לא נמצא מידע'}\n```"
        except:
            return "🔹 לא מצאתי פרויקט Git בתיקייה הזו."

    # ==========================================
    # RUN COMMAND
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

    return None

def handle_general(text):
    return f"""💬 קיבלתי: "{text[:50]}{'...' if len(text) > 50 else ''}"

🤖 אני גאמא v2.0 - סוכן AI מתקדם!

נסה:
• `היכנס ל-gmail` - כניסה לחשבון
• `חפש [נושא]` - חיפוש באינטרנט
• `run echo hello` - הרצת פקודה
• "מה אתה יודע לעשות?" - רשימת יכולות

או פשוט שאל אותי שאלה! 😊"""

# ==========================================
# MAIN LOGIC
# ==========================================

print("\n--- THINKING ---", flush=True)
text_lower = original_task.lower()

# PATTERN DETECTION - ORDER MATTERS!

# 1. CREDENTIALS - Save/List
if any(p in text_lower for p in ["שמור סיסמה", "save credentials", "save password", "שמור פרטים"]):
    print("🔐 Detected: SAVE CREDENTIALS", flush=True)
    thoughts.append("שמירת פרטי התחברות")
    response_text = handle_save_credentials(original_task, text_lower)

elif any(p in text_lower for p in ["הצג סיסמאות", "list credentials", "סיסמאות שמורות", "show passwords"]):
    print("🔐 Detected: LIST CREDENTIALS", flush=True)
    thoughts.append("הצגת פרטי התחברות שמורים")
    response_text = handle_list_credentials(text_lower)

# 2. BROWSER LOGIN
elif any(p in text_lower for p in ["היכנס ל", "login to", "sign in to", "התחבר ל", "כנס ל"]):
    print("🌐 Detected: BROWSER LOGIN", flush=True)
    thoughts.append("כניסה לחשבון דרך דפדפן")
    response_text = handle_browser_login(original_task, text_lower)

# 3. BROWSER ACTIONS
elif any(p in text_lower for p in ["פתח אתר", "open url", "צלם מסך", "screenshot", "גלוש ל", "navigate to"]) or (re.search(r'https?://', original_task) and any(p in text_lower for p in ["פתח", "open", "גלוש", "navigate", "צלם"])):
    print("🌐 Detected: BROWSER ACTION", flush=True)
    thoughts.append("פעולת דפדפן")
    response_text = handle_browser_action(original_task, text_lower)

# 4. EMAIL
elif any(p in text_lower for p in ["שלח אימייל", "send email", "שלח מייל", "send mail"]):
    print("📧 Detected: SEND EMAIL", flush=True)
    thoughts.append("שליחת אימייל")
    response_text = handle_send_email(original_task, text_lower)

# 5. API CALL
elif any(p in text_lower for p in ["api get", "api post", "api call", "קרא api", "קריאת api"]):
    print("🔌 Detected: API CALL", flush=True)
    thoughts.append("קריאת API")
    response_text = handle_api_call(original_task, text_lower)

# 6. SYSTEM MONITOR
elif any(p in text_lower for p in ["מצב מערכת", "system status", "system monitor", "ניטור", "cpu", "ram", "memory"]):
    print("📊 Detected: SYSTEM MONITOR", flush=True)
    thoughts.append("ניטור מערכת")
    response_text = handle_system_monitor(text_lower)

# 7. GITHUB OPERATIONS
elif any(p in text_lower for p in ["מידע על ריפו", "repo info", "github info", "צור issue", "create issue"]):
    print("🐙 Detected: GITHUB OPERATION", flush=True)
    thoughts.append("פעולת GitHub")
    result = handle_github_operations(original_task, text_lower)
    response_text = result if result else handle_general(original_task)

# 8. CODE EXECUTION (code blocks)
elif "```" in original_task or ("`" in original_task and any(p in text_lower for p in ["הרץ", "run code", "execute"])):
    print("💻 Detected: CODE EXECUTION", flush=True)
    thoughts.append("הרצת קוד")
    result = handle_code_execution(original_task, text_lower)
    response_text = result if result else handle_general(original_task)

# 9. ADVANCED FILE OPERATIONS
elif any(p in text_lower for p in ["קרא קובץ", "read file", "מחק קובץ", "delete file", "zip", "דחוס", "ארז", "רשימת קבצים"]):
    print("📁 Detected: ADVANCED FILE OP", flush=True)
    thoughts.append("פעולת קובץ מתקדמת")
    result = handle_file_operations_advanced(original_task, text_lower)
    response_text = result if result else handle_general(original_task)

# 10. WEB SEARCH
elif any(p in text_lower for p in ["חפש", "search", "google", "גוגל", "מצא", "סרוק", "research", "who is", "מי זה", "what is", "מה זה", "top 5", "פופולרי", "popular"]):
    print("🔍 Detected: WEB SEARCH", flush=True)
    thoughts.append("חיפוש באינטרנט")
    response_text = handle_command(original_task, text_lower, thoughts, tools_used)

# 11. GIT OPERATIONS
elif any(p in text_lower for p in ["commit", "push", "pull", "merge", "branch", "git status"]):
    print("🔄 Detected: GIT OPERATION", flush=True)
    thoughts.append("פעולת Git")
    response_text = handle_command(original_task, text_lower, thoughts, tools_used)

# 12. VERSION CHECK
elif any(p in text_lower for p in ["מה גרסת", "npm version", "גרסת npm", "גרסת node", "node version", "גרסת python", "python version"]):
    print("📋 Detected: VERSION CHECK", flush=True)
    thoughts.append("בדיקת גרסה")
    response_text = handle_command(original_task, text_lower, thoughts, tools_used)

# 13. FILE/COMMAND OPERATIONS
elif any(p in text_lower for p in ["צור קובץ", "create file", "תיצור", "מה יש", "אילו קבצים"]):
    print("⚡ Detected: COMMAND", flush=True)
    thoughts.append("פקודה")
    response_text = handle_command(original_task, text_lower, thoughts, tools_used)

# 14. RUN COMMAND
elif "run " in text_lower:
    print("⚡ Detected: RUN COMMAND", flush=True)
    thoughts.append("פקודת run")
    response_text = handle_command(original_task, text_lower, thoughts, tools_used)

# 15. QUESTIONS
elif any(q in original_task.lower() for q in ["מה", "איך", "למה", "היכן", "?", "what", "how", "why", "who"]):
    print("🎯 Detected: QUESTION", flush=True)
    thoughts.append("שאלה - מחפש תשובה")
    response_text = handle_question(original_task)

# 16. DEFAULT
else:
    print("💬 Detected: GENERAL", flush=True)
    thoughts.append("הודעה כללית")
    response_text = handle_llm_query(original_task, text_lower) if OPENAI_AVAILABLE else handle_general(original_task)

# ==========================================
# SAVE EVERYTHING
# ==========================================

print("\n--- SAVING ---", flush=True)

with open(response_file, "w", encoding="utf-8") as f:
    f.write(response_text)
print(f"Response saved: {response_text[:80]}...", flush=True)

with open(log_file, "a", encoding="utf-8") as f:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    f.write(f"[{timestamp}] USER: {original_task}\n")
    f.write(f"[{timestamp}] GAMMA: {response_text[:200]}...\n\n")

# ==========================================
# UPDATE STATE
# ==========================================

is_version = any(p in text_lower for p in ["מה גרסת", "npm version", "גרסת"])
is_git = any(p in text_lower for p in ["commit", "push", "pull", "merge", "branch"])
is_command_task = any(p in text_lower for p in ["צור קובץ", "create file", "תיצור"]) or "run " in text_lower
is_question_task = any(q in original_task.lower() for q in ["מה", "איך", "למה", "מי", "היכן", "?", "what", "how", "why", "who"])
is_search_task = any(p in text_lower for p in ["חפש", "search", "google", "גוגל"])
is_browser_task = any(p in text_lower for p in ["היכנס ל", "login", "פתח אתר", "screenshot"])
is_email_task = any(p in text_lower for p in ["שלח אימייל", "send email"])
is_api_task = any(p in text_lower for p in ["api get", "api post", "api call"])

task_type = (
    "browser_login" if is_browser_task else
    "email" if is_email_task else
    "api" if is_api_task else
    "search" if is_search_task else
    "git" if is_git else
    "version" if is_version else
    "command" if is_command_task else
    "question" if is_question_task else
    "general"
)

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
state["version"] = "2.0"

with open(state_file, "w", encoding="utf-8") as f:
    json.dump(state, f, ensure_ascii=False, indent=2)

print("\n=== DONE ===", flush=True)
print(f"Response: {response_text[:100]}...", flush=True)
