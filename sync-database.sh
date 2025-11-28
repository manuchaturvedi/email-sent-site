#!/bin/bash
# Database Sync Script for JustMailIt
# Syncs local database to GitHub and pulls to Raspberry Pi

set -e

echo "========================================"
echo "JustMailIt Database Sync"
echo "========================================"

# Step 1: Add and commit local database
echo "📦 Adding database files to Git..."
git add -f sendmail/justmailit.db justmailit.db justmailit_production.db 2>/dev/null || true

# Check if there are changes
if git diff --staged --quiet; then
    echo "✓ No database changes to commit"
else
    echo "💾 Committing database changes..."
    git commit -m "Sync database - $(date '+%Y-%m-%d %H:%M:%S')"
    
    echo "📤 Pushing to GitHub..."
    git push origin manu
    
    echo "✓ Local database synced to GitHub"
fi

# Step 2: Sync to Raspberry Pi
echo ""
echo "🔄 Syncing to Raspberry Pi..."

ssh -p 8888 manu@localhost << 'ENDSSH'
cd justmailit

# Create backup
echo "💾 Creating backup..."
cp sendmail/justmailit.db sendmail/justmailit.db.backup-$(date +%Y%m%d-%H%M%S) 2>/dev/null || true

# Pull changes
echo "📥 Pulling from GitHub..."
git stash
git pull origin manu
git stash drop 2>/dev/null || true

# Restart Docker container
echo "🔄 Restarting Docker container..."
docker restart justmailit-app

echo "✓ Pi database synced and app restarted"
ENDSSH

echo ""
echo "========================================"
echo "✅ Database sync complete!"
echo "========================================"
