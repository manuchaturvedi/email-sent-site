# Database Sync Script for JustMailIt (PowerShell version)
# Syncs local database to GitHub and pulls to Raspberry Pi

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "JustMailIt Database Sync" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Step 1: Add and commit local database
Write-Host "`n📦 Adding database files to Git..." -ForegroundColor Yellow
git add -f sendmail/justmailit.db justmailit.db justmailit_production.db 2>$null

# Check if there are changes
$changes = git diff --staged --quiet
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ No database changes to commit" -ForegroundColor Green
} else {
    Write-Host "💾 Committing database changes..." -ForegroundColor Yellow
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    git commit -m "Sync database - $timestamp"
    
    Write-Host "📤 Pushing to GitHub..." -ForegroundColor Yellow
    git push origin manu
    
    Write-Host "✓ Local database synced to GitHub" -ForegroundColor Green
}

# Step 2: Sync to Raspberry Pi
Write-Host "`n🔄 Syncing to Raspberry Pi..." -ForegroundColor Yellow

$sshScript = @"
cd justmailit
echo '💾 Creating backup...'
cp sendmail/justmailit.db sendmail/justmailit.db.backup-`$(date +%Y%m%d-%H%M%S) 2>/dev/null || true
echo '📥 Pulling from GitHub...'
git stash
git pull origin manu
git stash drop 2>/dev/null || true
echo '🔄 Restarting Docker container...'
docker restart justmailit-app
echo '✓ Pi database synced and app restarted'
"@

ssh -p 8888 manu@localhost $sshScript

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "✅ Database sync complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
