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
  # Calculate actual PRD stats dynamically
  TOTAL_TASKS=$(grep -c '"id":' "$PRD_FILE" 2>/dev/null || echo "?")
  DONE_TASKS=$(grep -c '"passes": true' "$PRD_FILE" 2>/dev/null || echo "?")
  REMAINING_TASKS=$(grep -c '"passes": false' "$PRD_FILE" 2>/dev/null || echo "?")

  send_telegram "🏢 *Ralph Mode Build Loop Started*

_The office lights flicker on..._

*Ralph shuffles to his desk with a crayon*
\"Oh boy! Time to build stuff! I have $MAX_ITERATIONS things to do today!\"

📋 PRD: $TOTAL_TASKS tasks ($DONE_TASKS done, $REMAINING_TASKS remaining)
🤖 Model: Sonnet 4.5
⏰ Started: $(date '+%H:%M:%S')"
fi
# No message on resume - Telegram will just see completions

# Change to project directory
cd "$PROJECT_DIR"

# TC-008: Auto-cluster PRD on startup for optimal task order
if [ "$IS_FRESH_START" = true ]; then
  echo "🔄 Running PRD auto-clustering..."
  python3 -c "
from prd_organizer import cluster_tasks
import json
import os
import hashlib
from datetime import datetime
import time

prd_path = 'scripts/ralph/prd.json'
progress_path = 'scripts/ralph/progress.txt'
checksum_path = 'scripts/ralph/.prd_checksum'

# Check if clustering needed (detect changes via checksum)
try:
    # Calculate current checksum of PRD
    with open(prd_path, 'rb') as f:
        prd_content = f.read()
        current_checksum = hashlib.md5(prd_content).hexdigest()

    with open(prd_path, 'r') as f:
        prd = json.load(f)

    needs_clustering = False
    reason = ''

    # Check if priority_order is missing
    if 'priority_order' not in prd or not prd.get('priority_order'):
        needs_clustering = True
        reason = 'Missing priority_order'
    # Check if checksum has changed
    elif os.path.exists(checksum_path):
        with open(checksum_path, 'r') as f:
            last_checksum = f.read().strip()

        if current_checksum != last_checksum:
            needs_clustering = True
            reason = 'PRD content changed since last cluster'
        else:
            reason = 'No changes detected since last cluster'
    else:
        # No checksum file exists - first run
        needs_clustering = True
        reason = 'First clustering run'

    if needs_clustering:
        print(f'  Clustering needed: {reason}')
        start_time = time.time()

        result = cluster_tasks(prd_path)

        elapsed = time.time() - start_time
        print(f'  ✅ Clustered {result[\"total_tasks\"]} tasks into {result[\"num_clusters\"]} clusters in {elapsed:.1f}s')

        # Save checksum
        with open(checksum_path, 'w') as f:
            f.write(current_checksum)

        # Log to progress.txt
        with open(progress_path, 'a') as f:
            f.write(f'\n## Auto-Cluster - {datetime.now().strftime(\"%Y-%m-%d %H:%M:%S\")}\n')
            f.write(f'**Reason**: {reason}\n')
            f.write(f'**Duration**: {elapsed:.1f}s\n')
            f.write(f'**Total Tasks**: {result[\"total_tasks\"]}\n')
            f.write(f'**Clusters Created**: {result[\"num_clusters\"]}\n')
            f.write(f'**Cluster Summary**:\n')
            for name, count in list(result[\"cluster_summary\"].items())[:10]:
                f.write(f'  - {name}: {count} tasks\n')
            if len(result[\"cluster_summary\"]) > 10:
                f.write(f'  - ... and {len(result[\"cluster_summary\"]) - 10} more\n')
            f.write(f'\n---\n')
    else:
        print(f'  ⏭️  Skipping clustering: {reason}')

except Exception as e:
    import traceback
    print(f'  ⚠️  Clustering failed: {e}')
    print('  Continuing with existing task order...')
    traceback.print_exc()
" 2>&1 | tee -a "$SCRIPT_DIR/cluster.log"
  echo ""
fi

for i in $(seq $START_ITERATION $MAX_ITERATIONS); do
  echo ""
  echo "═══════════════════════════════════════════════════════════"
  echo "  Ralph Iteration $i of $MAX_ITERATIONS - $(date '+%H:%M:%S')"
  echo "═══════════════════════════════════════════════════════════"
  echo ""

  # Security checkpoint every 5 iterations (Mr. Worms is particular about security)
  if [ $((i % 5)) -eq 0 ]; then
    echo "🔒 Running security checkpoint (iteration $i)..."
    # Quick scan for hardcoded secrets in tracked files
    SECRETS_FOUND=$(grep -rn --include="*.py" --include="*.js" --include="*.json" \
      -E "(api_key|password|secret|token)\s*[:=]\s*['\"][^'\"]{10,}" "$PROJECT_DIR" 2>/dev/null | \
      grep -v ".env" | grep -v "node_modules" | grep -v "__pycache__" | head -5)

    if [ -n "$SECRETS_FOUND" ]; then
      send_telegram "⚠️ *Security Checkpoint - Iteration $i*

🔍 Potential hardcoded secrets detected:
\`\`\`
$(echo "$SECRETS_FOUND" | head -3)
\`\`\`
_Mr. Worms says: Move these to .env!_"
      echo "  ⚠️  Potential secrets found - check Telegram"
    else
      echo "  ✅ Security check passed - no hardcoded secrets"
    fi

    # Verify .gitignore has .env
    if ! grep -q "^\.env$" "$PROJECT_DIR/.gitignore" 2>/dev/null; then
      echo "  ⚠️  Warning: .env not in .gitignore!"
    fi
  fi

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

  # NOTE: Auto-stop disabled - Claude keeps hallucinating completion
  # Just run all iterations and let the PRD track what's actually done

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
