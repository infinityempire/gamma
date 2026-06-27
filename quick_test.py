#!/usr/bin/env python3
import json
import os
import subprocess
from datetime import datetime

results = {"tests": [], "passed": 0, "failed": 0}

def test_capability(name, command, check_keywords):
    """Test a single capability"""
    print(f"\n🧪 Testing: {name}...", end=" ", flush=True)
    
    try:
        state = {"task_id": f"test-{name}", "task": command, "status": "running"}
        with open("/home/ubuntu/gamma/state.json", "w") as f:
            json.dump(state, f)
        
        result = subprocess.run(
            ["python3", "agent.py"],
            capture_output=True, text=True, timeout=60,
            cwd="/home/ubuntu/gamma",
            env={**os.environ, "GITHUB_WORKSPACE": "/home/ubuntu/gamma"}
        )
        
        response = ""
        if os.path.exists("/home/ubuntu/gamma/response.txt"):
            with open("/home/ubuntu/gamma/response.txt", "r", encoding="utf-8") as f:
                response = f.read()
        
        passed = any(kw.lower() in response.lower() for kw in check_keywords)
        
        if passed:
            print("✅ PASSED")
            results["passed"] += 1
        else:
            print("❌ FAILED")
            results["failed"] += 1
        
        results["tests"].append({
            "name": name,
            "status": "✅" if passed else "❌",
            "response": response[:150]
        })
        
        return passed
    except Exception as e:
        print(f"❌ ERROR: {str(e)[:30]}")
        results["failed"] += 1
        results["tests"].append({"name": name, "status": "❌", "error": str(e)[:50]})
        return False

print("="*70)
print("🚀 GAMMA AGENT v2.0 - QUICK CAPABILITY TEST")
print("="*70)

# Test all capabilities
test_capability("1. Credentials Save", "שמור סיסמה ל-github: user / pass", ["✅", "נשמר"])
test_capability("2. Credentials List", "הצג סיסמאות שמורות", ["🔐", "github"])
test_capability("3. Web Search", "חפש על Python programming", ["🔍", "תוצאות"])
test_capability("4. File Create", "צור קובץ בשם test.txt עם hello", ["✅", "נוצר"])
test_capability("5. File Read", "קרא קובץ test.txt", ["📄", "תוכן"])
test_capability("6. File List", "מה יש לי בתיקייה", ["📁", "קבצים"])
test_capability("7. File Delete", "מחק קובץ test.txt", ["🗑️", "נמחק"])
test_capability("8. Version Check", "מה גרסת node", ["📋", "version"])
test_capability("9. System Monitor", "מצב מערכת", ["📊", "CPU"])
test_capability("10. Terminal Command", "run whoami", ["✅", "פקודה"])
test_capability("11. Python Code", "הרץ קוד: ```python\nprint('test')\n```", ["✅", "Python"])
test_capability("12. Git Status", "מה קורה בgit", ["🔄", "Git"])
test_capability("13. Question Answer", "מה אתה יודע לעשות?", ["🤖", "יכולות"])
test_capability("14. Help Request", "עזור לי", ["🆘", "פקודות"])
test_capability("15. About Gamma", "מי אתה?", ["🤖", "גאמא"])

# Summary
print("\n" + "="*70)
print("📊 RESULTS SUMMARY")
print("="*70)
total = results["passed"] + results["failed"]
rate = (results["passed"] / total * 100) if total > 0 else 0
print(f"\n✅ Passed: {results['passed']}/{total}")
print(f"❌ Failed: {results['failed']}/{total}")
print(f"🎯 Success Rate: {rate:.0f}%")

# Save results
with open("/home/ubuntu/gamma/quick_test_results.json", "w") as f:
    json.dump(results, f, indent=2)

print(f"\n💾 Results saved to: quick_test_results.json")
print("="*70)
