#!/bin/bash
# Quick save current work
cd /home/manu/justmailit

echo "📝 Current changes:"
git status --short
echo ""

if [ -z "$1" ]; then
  echo "Enter commit message (or Ctrl+C to cancel):"
  read -r message
else
  message="$1"
fi

git add .
git commit -m "$message"

echo ""
echo "✅ Changes saved!"
echo ""
echo "Recent commits:"
git log --oneline -5
