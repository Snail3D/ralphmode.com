#!/bin/bash
# Ralph Mode - Quick Setup
# Run this in your project root to set up Ralph

echo "🤖 Setting up Ralph Mode..."

# Create directory structure
mkdir -p scripts/ralph

# Copy files
cp -r "$(dirname "$0")/scripts/ralph/"* scripts/ralph/

# Copy AGENTS.md if it doesn't exist
if [ ! -f "AGENTS.md" ]; then
  cp "$(dirname "$0")/AGENTS.md" .
fi

# Make ralph.sh executable
chmod +x scripts/ralph/ralph.sh

echo ""
echo "✅ Ralph Mode is ready!"
echo ""
echo "Next steps:"
echo "1. Edit scripts/ralph/prd.json with your user stories"
echo "2. Run: ./scripts/ralph/ralph.sh"
echo ""
echo "Ralph will implement your stories while you sleep! 🌙"
