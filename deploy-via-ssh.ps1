# PowerShell script to deploy to Raspberry Pi via SSH
# Usage: .\deploy-via-ssh.ps1

Write-Host "🚀 Deploying to Raspberry Pi..." -ForegroundColor Cyan
Write-Host ""

# SSH connection details
$sshHost = "manu@localhost"
$sshPort = "8888"

Write-Host "📡 Connecting to Raspberry Pi via Dataplicity tunnel..." -ForegroundColor Yellow
Write-Host "   Host: $sshHost" -ForegroundColor Gray
Write-Host "   Port: $sshPort" -ForegroundColor Gray
Write-Host ""

# Try different command formats
Write-Host "🔄 Attempting deployment..." -ForegroundColor Yellow

# Option 1: Try with bash -c
Write-Host "Trying method 1: bash -c..." -ForegroundColor Gray
ssh -p $sshPort $sshHost "bash -c 'cd /home/pi/justmailit && git pull origin manu && docker restart justmailit-app'"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Deployment successful!" -ForegroundColor Green
    exit 0
}

# Option 2: Try without bash wrapper
Write-Host "Trying method 2: direct commands..." -ForegroundColor Gray
ssh -p $sshPort $sshHost "cd /home/pi/justmailit; git pull origin manu; docker restart justmailit-app"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Deployment successful!" -ForegroundColor Green
    exit 0
}

# Option 3: Interactive SSH
Write-Host ""
Write-Host "⚠️ Automatic deployment failed. Starting interactive SSH session..." -ForegroundColor Yellow
Write-Host ""
Write-Host "Please run these commands manually:" -ForegroundColor Cyan
Write-Host "  cd /home/pi/justmailit" -ForegroundColor White
Write-Host "  git pull origin manu" -ForegroundColor White
Write-Host "  docker restart justmailit-app" -ForegroundColor White
Write-Host ""
Write-Host "Type 'exit' when done." -ForegroundColor Gray
Write-Host ""

ssh -p $sshPort $sshHost

Write-Host ""
Write-Host "📋 After deployment, you can check logs with:" -ForegroundColor Cyan
Write-Host "  docker logs -f justmailit-app" -ForegroundColor White
Write-Host ""
