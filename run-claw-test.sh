#!/bin/bash
# run-claw-test.sh - Chạy ClawTest bot (ShClawTestBot)
# HOME=/root (không đổi), dùng nanobot từ source repo này

GATEWAY_PORT=18792
CONFIG="/root/.claw-test/.nanobot/config.json"
WORKSPACE="/root/.claw-test/workspace"

# Kill existing on port
pkill -f "nanobot.*${GATEWAY_PORT}" 2>/dev/null
sleep 1

echo "🐈 Starting ClawTest gateway on port ${GATEWAY_PORT}..."
echo "Using config: ${CONFIG}"

cd /root/projects/nanobot

# Chạy trực tiếp từ source repo (không đổi HOME)
python3.11 -m nanobot gateway \
    -p ${GATEWAY_PORT} \
    -c "${CONFIG}" \
    -w "${WORKSPACE}"
