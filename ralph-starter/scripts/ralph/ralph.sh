#!/bin/bash
# Ralph Wiggum - Long-running AI agent loop for Ralph Mode
# Based on https://github.com/snarktank/ralph
# Usage: ./ralph.sh [max_iterations] [start_iteration]

# NO set -e - we handle errors gracefully

MAX_ITERATIONS=${1:-20}
START_ITERATION=${2:-1}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
PRD_FILE="$SCRIPT_DIR/prd.json"
PROGRESS_FILE="$SCRIPT_DIR/progress.txt"
ARCHIVE_DIR="$SCRIPT_DIR/archive"
STATE_FILE="$SCRIPT_DIR/.ralph_state"

# Load saved state if exists and no start iteration specified
IS_FRESH_START=true
if [ "$START_ITERATION" -eq 1 ] && [ -f "$STATE_FILE" ]; then
  SAVED_ITERATION=$(cat "$STATE_FILE" 2>/dev/null)
  if [ -n "$SAVED_ITERATION" ] && [ "$SAVED_ITERATION" -ge 1 ]; then
    START_ITERATION=$SAVED_ITERATION
    IS_FRESH_START=false
    echo "Resuming from iteration $START_ITERATION (saved state)"
  fi
fi

# Telegram streaming config
TELEGRAM_BOT_TOKEN="8318741949:AAF__w86T8qgiv7YFZ8-wcHNkbrT1ngbPaM"
TELEGRAM_CHAT_ID="7340030703"

# Function to send message to Telegram
send_telegram() {
  local message="$1"
  curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -d "chat_id=${TELEGRAM_CHAT_ID}" \
    -d "text=${message}" \
    -d "parse_mode=Markdown" > /dev/null 2>&1 || true
}

# Auto-deploy config
SERVER_IP="69.164.201.191"
SERVER_PASS="Y2xQkkH01puXGlOzuOdQ"

# Function to deploy to server and restart bot (with timeouts to prevent hanging)
deploy_to_server() {
  send_telegram "🚀 *Deploying to server...*"

  # Rsync code to server with 60s timeout
  timeout 60 sshpass -p "$SERVER_PASS" rsync -avz --quiet \
    --exclude='.git' --exclude='venv' --exclude='__pycache__' --exclude='*.pyc' \
    -e "ssh -o StrictHostKeyChecking=no -o ConnectTimeout=15" \
    "$PROJECT_DIR/" "root@${SERVER_IP}:/root/ralph-starter/" 2>/dev/null || true

  # Restart the bot with 30s timeout
  timeout 30 sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=15 "root@${SERVER_IP}" \
    'cd /root/ralph-starter && pkill -9 python 2>/dev/null; sleep 2 && ./venv/bin/python ralph_bot.py > /tmp/ralph.log 2>&1 &' 2>/dev/null || true

  send_telegram "✅ *Deployed & bot restarted!*
_New features are now LIVE_"
}

# Initialize progress file if it doesn't exist
if [ ! -f "$PROGRESS_FILE" ]; then
  echo "# Ralph Progress Log - Ralph Mode Bot" > "$PROGRESS_FILE"
  echo "Started: $(date)" >> "$PROGRESS_FILE"
  echo "---" >> "$PROGRESS_FILE"
  echo "" >> "$PROGRESS_FILE"
fi

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║  Ralph Wiggum - Autonomous AI Agent Loop                  ║"
echo "║  Project: Ralph Mode Bot                                  ║"
echo "║  Max Iterations: $MAX_ITERATIONS (starting at $START_ITERATION)                 ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Only send startup message on fresh start (no saved state)
if [ "$IS_FRESH_START" = true ]; then
  send_telegram "🏢 *Ralph Mode Build Loop Started*

_The office lights flicker on..._

*Ralph shuffles to his desk with a crayon*
\"Oh boy! Time to build stuff! I have $MAX_ITERATIONS things to do today!\"

📋 PRD: 212 tasks (34 done, 178 remaining)
🤖 Model: Sonnet 4.5
⏰ Started: $(date '+%H:%M:%S')"
fi
# No message on resume - Telegram will just see completions

# Change to project directory
cd "$PROJECT_DIR"

for i in $(seq $START_ITERATION $MAX_ITERATIONS); do
  echo ""
  echo "═══════════════════════════════════════════════════════════"
  echo "  Ralph Iteration $i of $MAX_ITERATIONS - $(date '+%H:%M:%S')"
  echo "═══════════════════════════════════════════════════════════"
  echo ""

  # Save state BEFORE running (so we can resume this iteration if crashed)
  echo "$i" > "$STATE_FILE"

  # Run Claude Code with Sonnet 4.5 (fast, capable), auto-accepting all permissions
  # No Telegram message here - only notify on COMPLETION to avoid spam on restarts
  OUTPUT=$(cat "$SCRIPT_DIR/prompt.md" | claude --model sonnet --dangerously-skip-permissions 2>&1 | tee /dev/stderr) || true

  # Extract summary from output (last 500 chars or so)
  SUMMARY=$(echo "$OUTPUT" | tail -c 800 | head -c 500)

  # Send iteration complete to Telegram
  send_telegram "✅ *Iteration $i Complete*

\`\`\`
${SUMMARY}
\`\`\`"

  # Auto-deploy to server so YouTube audience sees changes live
  deploy_to_server

  # Check for completion signal (must be on its own line, not just mentioned in text)
  if echo "$OUTPUT" | grep -q "^<promise>COMPLETE</promise>$"; then
    echo ""
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║  Ralph completed all tasks!                               ║"
    echo "║  Finished at iteration $i of $MAX_ITERATIONS                         ║"
    echo "╚═══════════════════════════════════════════════════════════╝"

    send_telegram "🎉 *ALL TASKS COMPLETE!*

_Ralph puts down his crayon triumphantly_
\"I did it! I did all $i things!\"

🏆 Finished at iteration $i of $MAX_ITERATIONS
⏰ Completed: $(date '+%H:%M:%S')"
    rm -f "$STATE_FILE"  # Clear state on completion
    exit 0
  fi

  echo ""
  echo "Iteration $i complete. Pausing 2 seconds before next iteration..."
  sleep 2
done

# Clear state file on successful completion
rm -f "$STATE_FILE"

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║  Ralph reached max iterations ($MAX_ITERATIONS)                        ║"
echo "║  Check progress.txt for status                            ║"
echo "╚═══════════════════════════════════════════════════════════╝"

send_telegram "⏸️ *Ralph reached max iterations*

_Ralph looks tired but happy_
\"I did $MAX_ITERATIONS things today! My brain is full.\"

Check progress.txt for status.
Restart with: ./ralph.sh 50"

exit 1
