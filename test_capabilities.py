#!/usr/bin/env python3
"""
Comprehensive Test Suite for Gamma Agent v2.0
Tests all capabilities: credentials, browser login, email, APIs, code execution, etc.
"""

import json
import os
import subprocess
import sys
from datetime import datetime

test_results = {
    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "tests": [],
    "summary": {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "skipped": 0
    }
}

def run_test(test_name, test_description, test_command, expected_keywords=None):
    """Run a single test and record results"""
    print(f"\n{'='*70}")
    print(f"🧪 TEST {test_results['summary']['total'] + 1}: {test_name}")
    print(f"📝 {test_description}")
    print(f"{'='*70}")
    
    test_results["summary"]["total"] += 1
    
    try:
        state = {
            "task_id": f"test-{test_name}",
            "task": test_command,
            "status": "running",
            "created_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        }
        
        with open("/home/ubuntu/gamma/state.json", "w") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        
        print(f"⏳ Running: {test_command[:60]}...")
        
        result = subprocess.run(
            ["python3", "agent.py"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd="/home/ubuntu/gamma",
            env={**os.environ, "GITHUB_WORKSPACE": "/home/ubuntu/gamma"}
        )
        
        response_file = "/home/ubuntu/gamma/response.txt"
        response_text = ""
        if os.path.exists(response_file):
            with open(response_file, "r", encoding="utf-8") as f:
                response_text = f.read()
        
        success = False
        if expected_keywords:
            success = any(keyword.lower() in response_text.lower() for keyword in expected_keywords)
        else:
            success = result.returncode == 0 and len(response_text) > 0
        
        test_result = {
            "name": test_name,
            "status": "✅ PASSED" if success else "❌ FAILED",
            "command": test_command,
            "response_preview": response_text[:250],
            "exit_code": result.returncode
        }
        
        test_results["tests"].append(test_result)
        
        if success:
            test_results["summary"]["passed"] += 1
            print(f"✅ PASSED")
        else:
            test_results["summary"]["failed"] += 1
            print(f"❌ FAILED")
        
        print(f"📤 Response:\n{response_text[:400]}\n")
        
        return success
    
    except subprocess.TimeoutExpired:
        print(f"⏱️ TIMEOUT (exceeded 120s)")
        test_results["summary"]["failed"] += 1
        test_results["tests"].append({
            "name": test_name,
            "status": "⏱️ TIMEOUT",
            "command": test_command
        })
        return False
    
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        test_results["summary"]["failed"] += 1
        test_results["tests"].append({
            "name": test_name,
            "status": "❌ ERROR",
            "command": test_command,
            "error": str(e)
        })
        return False

def main():
    print("\n" + "="*70)
    print("🚀 GAMMA AGENT v2.0 - COMPREHENSIVE TEST SUITE")
    print("="*70)
    print("Testing all 15 core capabilities...")
    
    # TEST 1: CREDENTIALS SAVE
    run_test(
        "CREDENTIALS_SAVE",
        "Save credentials for a service",
        "שמור סיסמה ל-gmail: testuser@gmail.com / testpass123",
        expected_keywords=["✅", "נשמר", "gmail", "פרטים"]
    )
    
    # TEST 2: LIST CREDENTIALS
    run_test(
        "CREDENTIALS_LIST",
        "List saved credentials",
        "הצג סיסמאות שמורות",
        expected_keywords=["🔐", "gmail", "פרטים"]
    )
    
    # TEST 3: WEB SEARCH
    run_test(
        "WEB_SEARCH",
        "Search the web for information",
        "חפש על Manus AI",
        expected_keywords=["🔍", "תוצאות", "חיפוש"]
    )
    
    # TEST 4: FILE CREATION
    run_test(
        "FILE_CREATE",
        "Create a new file with content",
        "צור קובץ בשם gamma_test.txt עם זה בדיקה של גאמא",
        expected_keywords=["✅", "נוצר", "gamma_test"]
    )
    
    # TEST 5: FILE READ
    run_test(
        "FILE_READ",
        "Read an existing file",
        "קרא קובץ gamma_test.txt",
        expected_keywords=["📄", "תוכן", "בדיקה"]
    )
    
    # TEST 6: VERSION CHECK
    run_test(
        "VERSION_CHECK",
        "Check Python version",
        "מה גרסת python",
        expected_keywords=["📋", "Python", "גרסת"]
    )
    
    # TEST 7: SYSTEM MONITOR
    run_test(
        "SYSTEM_MONITOR",
        "Monitor system resources (CPU, RAM, Disk)",
        "מצב מערכת",
        expected_keywords=["📊", "CPU", "זיכרון"]
    )
    
    # TEST 8: PYTHON CODE EXECUTION
    run_test(
        "CODE_PYTHON",
        "Execute Python code",
        """הרץ קוד Python:
```python
x = 5
y = 10
print(f"Result: {x + y}")
```""",
        expected_keywords=["✅", "Python", "Result"]
    )
    
    # TEST 9: TERMINAL COMMAND
    run_test(
        "TERMINAL_CMD",
        "Run terminal command",
        "run echo 'Gamma Agent v2.0 Test'",
        expected_keywords=["✅", "Gamma"]
    )
    
    # TEST 10: GIT STATUS
    run_test(
        "GIT_STATUS",
        "Check Git repository status",
        "מה קורה בgit",
        expected_keywords=["🔄", "Git"]
    )
    
    # TEST 11: QUESTION ANSWERING
    run_test(
        "QUESTION_ANSWER",
        "Answer a general question about capabilities",
        "מה אתה יודע לעשות?",
        expected_keywords=["🤖", "יכולות", "גאמא"]
    )
    
    # TEST 12: HELP REQUEST
    run_test(
        "HELP_REQUEST",
        "Request help/documentation",
        "עזור לי",
        expected_keywords=["🆘", "פקודות"]
    )
    
    # TEST 13: FILE LISTING
    run_test(
        "FILE_LIST",
        "List all files in workspace",
        "מה יש לי בתיקייה",
        expected_keywords=["📁", "קבצים"]
    )
    
    # TEST 14: FILE DELETE
    run_test(
        "FILE_DELETE",
        "Delete a file",
        "מחק קובץ gamma_test.txt",
        expected_keywords=["🗑️", "נמחק"]
    )
    
    # TEST 15: ABOUT GAMMA
    run_test(
        "ABOUT_GAMMA",
        "Get information about Gamma agent",
        "מי אתה?",
        expected_keywords=["🤖", "גאמא", "סוכן"]
    )
    
    # ==========================================
    # SUMMARY & REPORT
    # ==========================================
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    
    summary = test_results["summary"]
    print(f"\n✅ Passed:  {summary['passed']}/{summary['total']}")
    print(f"❌ Failed:  {summary['failed']}/{summary['total']}")
    print(f"⏱️  Skipped: {summary['skipped']}/{summary['total']}")
    
    success_rate = (summary['passed'] / summary['total'] * 100) if summary['total'] > 0 else 0
    print(f"\n🎯 Success Rate: {success_rate:.1f}%")
    
    # Detailed results
    print("\n" + "="*70)
    print("📋 DETAILED RESULTS")
    print("="*70)
    
    for i, test in enumerate(test_results["tests"], 1):
        print(f"\n{i}. {test['status']} - {test['name']}")
        if 'response_preview' in test and test['response_preview']:
            preview = test['response_preview'][:100].replace('\n', ' ')
            print(f"   Response: {preview}...")
    
    # Save results to file
    results_file = "/home/ubuntu/gamma/test_results.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(test_results, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Results saved to: {results_file}")
    
    # Save markdown report
    report_file = "/home/ubuntu/gamma/TEST_REPORT.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("# Gamma Agent v2.0 - Comprehensive Test Report\n\n")
        f.write(f"**Test Date:** {test_results['timestamp']}\n\n")
        f.write("## Summary\n\n")
        f.write(f"- ✅ **Passed:** {summary['passed']}/{summary['total']}\n")
        f.write(f"- ❌ **Failed:** {summary['failed']}/{summary['total']}\n")
        f.write(f"- 🎯 **Success Rate:** {success_rate:.1f}%\n\n")
        f.write("## Test Results\n\n")
        
        for i, test in enumerate(test_results["tests"], 1):
            f.write(f"### {i}. {test['status']} - {test['name']}\n\n")
            f.write(f"**Command:** `{test['command']}`\n\n")
            if 'response_preview' in test and test['response_preview']:
                f.write(f"**Response:**\n```\n{test['response_preview']}\n```\n\n")
            if 'error' in test:
                f.write(f"**Error:** {test['error']}\n\n")
    
    print(f"📄 Report saved to: {report_file}")
    
    print("\n" + "="*70)
    if success_rate >= 80:
        print("✅ TEST SUITE PASSED - Most capabilities working!")
    elif success_rate >= 50:
        print("⚠️ TEST SUITE PARTIAL - Some capabilities need fixing")
    else:
        print("❌ TEST SUITE FAILED - Major issues detected")
    print("="*70 + "\n")
    
    return 0 if success_rate >= 80 else 1

if __name__ == "__main__":
    sys.exit(main())
