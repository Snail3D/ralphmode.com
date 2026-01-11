#!/usr/bin/env bash
#
# Install git hooks for Ralph Mode
#
# This script installs the pre-commit hook that protects foundational files.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Git repo is at parent of ralph-starter/
HOOKS_DIR="${SCRIPT_DIR}/../../.git/hooks"

# Create hooks directory if it doesn't exist
mkdir -p "${HOOKS_DIR}"

# Copy pre-commit hook
cp "${SCRIPT_DIR}/pre-commit" "${HOOKS_DIR}/pre-commit"
chmod +x "${HOOKS_DIR}/pre-commit"

echo "✅ Git hooks installed successfully!"
echo ""
echo "The pre-commit hook will now protect foundational files from casual changes."
echo "Files protected: HARDCORE_RULES.md, WHO_WE_ARE.md, prompt.md, .env, etc."
echo ""
echo "To make approved changes to protected files:"
echo "  1. Run: python3 rule_manager.py <rule_number> \"<change>\" \"Your Name\""
echo "  2. Get approval from Mr. Worms"
echo "  3. Commit with: git commit --no-verify"
