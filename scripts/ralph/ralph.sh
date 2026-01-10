#!/bin/bash
# Ralph Mode - Autonomous AI Agent Loop
# Based on https://github.com/snarktank/ralph by Ryan Carson
#
# Usage: ./ralph.sh [max_iterations]
#
# This script runs Claude Code in a loop, implementing one user story
# per iteration until all stories in prd.json have passes: true

set -e

MAX_ITERATIONS=${1:-10}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
PRD_FILE="$SCRIPT_DIR/prd.json"
PROGRESS_FILE="$SCRIPT_DIR/progress.txt"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Initialize progress file if it doesn't exist
if [ ! -f "$PROGRESS_FILE" ]; then
  echo "# Ralph Progress Log" > "$PROGRESS_FILE"
  echo "Started: $(date)" >> "$PROGRESS_FILE"
  echo "---" >> "$PROGRESS_FILE"
  echo "" >> "$PROGRESS_FILE"
fi

echo ""
echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║${NC}  🤖 ${GREEN}Ralph Mode${NC} - Autonomous AI Agent Loop                 ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}  Max Iterations: $MAX_ITERATIONS                                        ${BLUE}║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Change to project directory
cd "$PROJECT_DIR"

for i in $(seq 1 $MAX_ITERATIONS); do
  echo ""
  echo -e "${YELLOW}═══════════════════════════════════════════════════════════${NC}"
  echo -e "  Ralph Iteration ${GREEN}$i${NC} of $MAX_ITERATIONS - $(date '+%H:%M:%S')"
  echo -e "${YELLOW}═══════════════════════════════════════════════════════════${NC}"
  echo ""

  # Run Claude Code with the prompt, auto-accepting all permissions
  OUTPUT=$(cat "$SCRIPT_DIR/prompt.md" | claude --dangerously-skip-permissions 2>&1 | tee /dev/stderr) || true

  # Check for completion signal
  if echo "$OUTPUT" | grep -q "<promise>COMPLETE</promise>"; then
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✅ Ralph completed all tasks!                            ║${NC}"
    echo -e "${GREEN}║  Finished at iteration $i of $MAX_ITERATIONS                          ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
    exit 0
  fi

  echo ""
  echo "Iteration $i complete. Pausing 2 seconds..."
  sleep 2
done

echo ""
echo -e "${YELLOW}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}║  ⚠️  Ralph reached max iterations ($MAX_ITERATIONS)                     ║${NC}"
echo -e "${YELLOW}║  Check progress.txt for status                            ║${NC}"
echo -e "${YELLOW}╚═══════════════════════════════════════════════════════════╝${NC}"
exit 1
