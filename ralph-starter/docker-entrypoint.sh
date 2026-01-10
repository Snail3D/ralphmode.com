#!/bin/bash
# BO-002: Docker Entrypoint for Isolated Build Environment
#
# This script runs inside the Docker container and:
# 1. Clones the repository
# 2. Creates a feedback-specific branch
# 3. Loads the task context
# 4. Runs Ralph to implement the feedback
# 5. Reports results back
#
# Environment variables:
#   REPO_URL - Git repository URL
#   FEEDBACK_ID - Feedback item ID
#   TASK_FILE - Path to task JSON file
#   BRANCH_NAME - Branch name (default: feedback/FB-{FEEDBACK_ID})

set -e  # Exit on error

echo "========================================"
echo "Ralph Build Environment (Isolated)"
echo "========================================"
echo "Feedback ID: ${FEEDBACK_ID}"
echo "Repository: ${REPO_URL}"
echo "Branch: ${BRANCH_NAME:-feedback/FB-${FEEDBACK_ID}}"
echo "========================================"

# Validate required environment variables
if [ -z "$REPO_URL" ]; then
    echo "ERROR: REPO_URL environment variable not set"
    exit 1
fi

if [ -z "$FEEDBACK_ID" ]; then
    echo "ERROR: FEEDBACK_ID environment variable not set"
    exit 1
fi

if [ -z "$TASK_FILE" ]; then
    echo "ERROR: TASK_FILE environment variable not set"
    exit 1
fi

# Set default branch name
BRANCH_NAME=${BRANCH_NAME:-feedback/FB-${FEEDBACK_ID}}

# Clone repository
echo "Cloning repository..."
git clone "$REPO_URL" /home/builder/repo
cd /home/builder/repo

# Create and checkout feedback branch
echo "Creating branch: ${BRANCH_NAME}"
git checkout -b "$BRANCH_NAME"

# Copy task file into repo
echo "Loading task context..."
cp "$TASK_FILE" /home/builder/repo/task.json

# Install dependencies if requirements.txt exists
if [ -f "requirements.txt" ]; then
    echo "Installing Python dependencies..."
    pip install -r requirements.txt
fi

# Run Ralph
echo "Starting Ralph build process..."
echo "========================================"

# Check if ralph.sh exists in the repo
if [ -f "scripts/ralph/ralph.sh" ]; then
    # Use repo's Ralph script
    bash scripts/ralph/ralph.sh
else
    # Fallback: Run Claude Code directly with task context
    echo "No Ralph script found, running Claude Code directly..."

    # Load task from JSON
    TASK_CONTENT=$(jq -r '.content' task.json)
    TASK_TYPE=$(jq -r '.type' task.json)

    # Create a simple prompt for Claude Code
    cat > PROMPT.md << EOF
# Feedback Task: ${TASK_TYPE}

Feedback ID: ${FEEDBACK_ID}

## Request

${TASK_CONTENT}

## Instructions

Please implement this ${TASK_TYPE} request. Follow these steps:

1. Read and understand the existing codebase
2. Implement the requested changes
3. Test your implementation
4. Commit your changes with a descriptive message
5. Report completion

When you're done, create a commit with message:
"feat(feedback): FB-${FEEDBACK_ID} - ${TASK_TYPE}"
EOF

    # Run Claude Code
    claude-code PROMPT.md
fi

echo "========================================"
echo "Build process completed"
echo "========================================"

# Output git status
echo "Git status:"
git status

# Output last commit
echo "Last commit:"
git log -1 --oneline

# Success
exit 0
