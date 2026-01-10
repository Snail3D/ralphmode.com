#!/bin/bash
# Ralph Wiggum - Long-running AI agent loop for Ralph Mode
# Based on https://github.com/snarktank/ralph
# Usage: ./ralph.sh [max_iterations]

set -e

MAX_ITERATIONS=${1:-20}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
PRD_FILE="$SCRIPT_DIR/prd.json"
PROGRESS_FILE="$SCRIPT_DIR/progress.txt"
ARCHIVE_DIR="$SCRIPT_DIR/archive"

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
echo "║  Max Iterations: $MAX_ITERATIONS                                      ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Send startup message to Telegram
send_telegram "🏢 *Ralph Mode Build Loop Started*

_The office lights flicker on..._

*Ralph shuffles to his desk with a crayon*
\"Oh boy! Time to build stuff! I have $MAX_ITERATIONS things to do today!\"

📋 PRD: 212 tasks
🤖 Model: Sonnet 4.5
⏰ Started: $(date '+%H:%M:%S')"

# Change to project directory
cd "$PROJECT_DIR"

for i in $(seq 1 $MAX_ITERATIONS); do
  echo ""
  echo "═══════════════════════════════════════════════════════════"
  echo "  Ralph Iteration $i of $MAX_ITERATIONS - $(date '+%H:%M:%S')"
  echo "═══════════════════════════════════════════════════════════"
  echo ""

  # Notify Telegram of iteration start
  send_telegram "🔨 *Iteration $i of $MAX_ITERATIONS*
_Ralph picks up his crayon..._
\"Let me see what's next on the list!\""

  # Run Claude Code with Sonnet 4.5 (fast, capable), auto-accepting all permissions
  OUTPUT=$(cat "$SCRIPT_DIR/prompt.md" | claude --model sonnet --dangerously-skip-permissions 2>&1 | tee /dev/stderr) || true

  # Extract summary from output (last 500 chars or so)
  SUMMARY=$(echo "$OUTPUT" | tail -c 800 | head -c 500)

  # Send iteration complete to Telegram
  send_telegram "✅ *Iteration $i Complete*

\`\`\`
${SUMMARY}
\`\`\`"

  # Check for completion signal
  if echo "$OUTPUT" | grep -q "<promise>COMPLETE</promise>"; then
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
    exit 0
  fi

  echo ""
  echo "Iteration $i complete. Pausing 2 seconds before next iteration..."
  sleep 2
done

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
