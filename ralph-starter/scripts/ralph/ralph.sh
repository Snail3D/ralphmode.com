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

# Change to project directory
cd "$PROJECT_DIR"

for i in $(seq 1 $MAX_ITERATIONS); do
  echo ""
  echo "═══════════════════════════════════════════════════════════"
  echo "  Ralph Iteration $i of $MAX_ITERATIONS - $(date '+%H:%M:%S')"
  echo "═══════════════════════════════════════════════════════════"
  echo ""

  # Run Claude Code with Sonnet 4.5 (fast, capable), auto-accepting all permissions
  OUTPUT=$(cat "$SCRIPT_DIR/prompt.md" | claude --model sonnet --dangerously-skip-permissions 2>&1 | tee /dev/stderr) || true

  # Check for completion signal
  if echo "$OUTPUT" | grep -q "<promise>COMPLETE</promise>"; then
    echo ""
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║  Ralph completed all tasks!                               ║"
    echo "║  Finished at iteration $i of $MAX_ITERATIONS                         ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
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
exit 1
