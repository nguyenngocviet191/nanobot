#!/bin/bash
# Kill ONLY processes started via nanobot-sh
# Detects by HOME routing to ~/.nanobot-sh/

echo "🔍 Scanning nanobot-sh processes..."
killed=0

# Find python processes with nanobot gateway
for pid in $(ps aux | grep 'nanobot.*gateway' | grep -v grep | awk '{print $2}'); do
    # Check if this process uses HOME routing (nanobot-sh style)
    if ps -p $pid -o args= | grep -qE '\-\-home|\.nanobot-sh|DefaultPath_home|PYTHONSTARTUP'; then
        cmd=$(ps -p $pid -o args= | head -1)
        echo "🛑 Killing nanobot-sh process PID=$pid: $cmd"
        kill $pid 2>/dev/null && killed=$((killed+1))
    fi
done

# Also kill by known test ports
for port in 18791 18792 18793; do
    pid=$(lsof -ti:$port 2>/dev/null)
    if [ -n "$pid" ]; then
        cmd=$(ps -p $pid -o args= | grep -v grep | head -1)
        if echo "$cmd" | grep -qE 'nanobot.*gateway'; then
            echo "🛑 Killing on port $port PID=$pid"
            kill $pid 2>/dev/null && killed=$((killed+1))
        fi
    fi
done

echo "✅ Killed $killed process(es)"
