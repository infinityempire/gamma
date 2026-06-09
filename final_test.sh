#!/bin/bash

echo "=================================="
echo "🚀 GAMMA AGENT v2.0 - FINAL TEST"
echo "=================================="

# Test 1: Credentials
echo -e "\n1️⃣ Testing Credentials Management..."
echo '{"task_id":"test1","task":"שמור סיסמה ל-twitter: user123 / pass456","status":"running"}' > /home/ubuntu/gamma/state.json
cd /home/ubuntu/gamma && python3 agent.py > /dev/null 2>&1
if grep -q "✅" /home/ubuntu/gamma/response.txt; then echo "✅ Credentials Save: PASSED"; else echo "❌ Credentials Save: FAILED"; fi

# Test 2: Web Search
echo -e "\n2️⃣ Testing Web Search..."
echo '{"task_id":"test2","task":"חפש על artificial intelligence","status":"running"}' > /home/ubuntu/gamma/state.json
cd /home/ubuntu/gamma && python3 agent.py > /dev/null 2>&1
if grep -q "🔍" /home/ubuntu/gamma/response.txt; then echo "✅ Web Search: PASSED"; else echo "❌ Web Search: FAILED"; fi

# Test 3: File Operations
echo -e "\n3️⃣ Testing File Operations..."
echo '{"task_id":"test3","task":"צור קובץ בשם demo.txt עם demo content","status":"running"}' > /home/ubuntu/gamma/state.json
cd /home/ubuntu/gamma && python3 agent.py > /dev/null 2>&1
if grep -q "✅" /home/ubuntu/gamma/response.txt; then echo "✅ File Create: PASSED"; else echo "❌ File Create: FAILED"; fi

# Test 4: File Read
echo '{"task_id":"test4","task":"קרא קובץ demo.txt","status":"running"}' > /home/ubuntu/gamma/state.json
cd /home/ubuntu/gamma && python3 agent.py > /dev/null 2>&1
if grep -q "📄" /home/ubuntu/gamma/response.txt; then echo "✅ File Read: PASSED"; else echo "❌ File Read: FAILED"; fi

# Test 5: Version Check
echo -e "\n4️⃣ Testing Version Checks..."
echo '{"task_id":"test5","task":"מה גרסת python","status":"running"}' > /home/ubuntu/gamma/state.json
cd /home/ubuntu/gamma && python3 agent.py > /dev/null 2>&1
if grep -q "Python" /home/ubuntu/gamma/response.txt; then echo "✅ Version Check: PASSED"; else echo "❌ Version Check: FAILED"; fi

# Test 6: System Monitor
echo -e "\n5️⃣ Testing System Monitor..."
echo '{"task_id":"test6","task":"מצב מערכת","status":"running"}' > /home/ubuntu/gamma/state.json
cd /home/ubuntu/gamma && python3 agent.py > /dev/null 2>&1
if grep -q "📊" /home/ubuntu/gamma/response.txt; then echo "✅ System Monitor: PASSED"; else echo "❌ System Monitor: FAILED"; fi

# Test 7: Terminal Command
echo -e "\n6️⃣ Testing Terminal Commands..."
echo '{"task_id":"test7","task":"run echo test123","status":"running"}' > /home/ubuntu/gamma/state.json
cd /home/ubuntu/gamma && python3 agent.py > /dev/null 2>&1
if grep -q "test123" /home/ubuntu/gamma/response.txt; then echo "✅ Terminal Command: PASSED"; else echo "❌ Terminal Command: FAILED"; fi

# Test 8: Python Code
echo -e "\n7️⃣ Testing Code Execution..."
echo '{"task_id":"test8","task":"הרץ קוד Python: ```python\nprint(42)\n```","status":"running"}' > /home/ubuntu/gamma/state.json
cd /home/ubuntu/gamma && python3 agent.py > /dev/null 2>&1
if grep -q "Python" /home/ubuntu/gamma/response.txt; then echo "✅ Python Code: PASSED"; else echo "❌ Python Code: FAILED"; fi

# Test 9: Git Status
echo -e "\n8️⃣ Testing Git Operations..."
echo '{"task_id":"test9","task":"מה קורה בgit","status":"running"}' > /home/ubuntu/gamma/state.json
cd /home/ubuntu/gamma && python3 agent.py > /dev/null 2>&1
if grep -q "Git" /home/ubuntu/gamma/response.txt; then echo "✅ Git Status: PASSED"; else echo "❌ Git Status: FAILED"; fi

# Test 10: Questions
echo -e "\n9️⃣ Testing Question Answering..."
echo '{"task_id":"test10","task":"מה אתה יודע לעשות?","status":"running"}' > /home/ubuntu/gamma/state.json
cd /home/ubuntu/gamma && python3 agent.py > /dev/null 2>&1
if grep -q "יכולות" /home/ubuntu/gamma/response.txt; then echo "✅ Question Answer: PASSED"; else echo "❌ Question Answer: FAILED"; fi

# Test 11: Help
echo -e "\n🔟 Testing Help System..."
echo '{"task_id":"test11","task":"עזור לי","status":"running"}' > /home/ubuntu/gamma/state.json
cd /home/ubuntu/gamma && python3 agent.py > /dev/null 2>&1
if grep -q "פקודות" /home/ubuntu/gamma/response.txt; then echo "✅ Help System: PASSED"; else echo "❌ Help System: FAILED"; fi

echo -e "\n=================================="
echo "✅ ALL TESTS COMPLETED"
echo "=================================="
