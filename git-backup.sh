#!/bin/bash
# Create version backup with timestamp tag
cd /home/manu/justmailit
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
TAG="backup-$TIMESTAMP"

git add .
git commit -m "Backup checkpoint - $TIMESTAMP" || echo 'No changes to commit'
git tag -a "$TAG" -m "Automatic backup - $(date +'%Y-%m-%d %H:%M:%S')"

echo ''
echo "✅ Backup created with tag: $TAG"
echo ''
echo 'Recent backups:'
git tag | grep backup | tail -5
