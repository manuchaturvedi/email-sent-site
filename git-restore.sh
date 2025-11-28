#!/bin/bash
# Restore from a backup tag
cd /home/manu/justmailit

if [ -z "$1" ]; then
  echo "📋 Available backups:"
  git tag | grep backup
  echo ""
  echo "Usage: ./git-restore.sh <backup-tag>"
  echo "Example: ./git-restore.sh backup-20251123-143000"
  exit 1
fi

TAG="$1"

echo "⚠️  WARNING: This will restore code to backup: $TAG"
echo "Current changes will be lost!"
read -p "Continue? (yes/no): " confirm

if [ "$confirm" = "yes" ]; then
  git checkout "$TAG"
  echo "✅ Restored to backup: $TAG"
  echo "To return to latest: git checkout master"
else
  echo "❌ Restore cancelled"
fi
