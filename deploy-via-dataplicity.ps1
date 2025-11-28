# Deploy to Raspberry Pi via Dataplicity (Docker with Volume Mount)
# Make sure Dataplicity port forwarding is active (localhost:8888 -> Pi:22)

Write-Host "🚀 Deploying to Raspberry Pi via Dataplicity (Docker)..." -ForegroundColor Green

# Configuration
$PI_USER = "manu"
$PI_PORT = "8888"
$PI_HOST = "localhost"
$PROJECT_PATH = "/home/manu/AI_support"  # Adjust this path if needed
$CONTAINER_NAME = "justmailit"  # Adjust if different

# Test connection
Write-Host "`n📡 Testing connection to Pi..." -ForegroundColor Cyan
ssh -p $PI_PORT "${PI_USER}@${PI_HOST}" "echo 'Connection successful'"
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Cannot connect to Pi. Make sure:" -ForegroundColor Red
    Write-Host "   1. Dataplicity port forwarding is active"
    Write-Host "   2. SSH keys are set up or you have the password"
    Write-Host "   3. The Pi is online and connected to Dataplicity"
    exit 1
}

Write-Host "✅ Connection successful!" -ForegroundColor Green

# Pull latest changes from GitHub on the Pi
Write-Host "`n📥 Pulling latest changes from GitHub on Pi..." -ForegroundColor Cyan
ssh -p $PI_PORT "${PI_USER}@${PI_HOST}" @"
    cd $PROJECT_PATH
    echo '🔄 Fetching from GitHub...'
    git fetch origin
    git checkout manu
    git pull origin manu
    echo '✅ Code updated successfully'
"@

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to pull changes" -ForegroundColor Red
    exit 1
}

# Restart Docker container (files are volume-mounted, no rebuild needed)
Write-Host "`n🐳 Restarting Docker container..." -ForegroundColor Cyan
ssh -p $PI_PORT "${PI_USER}@${PI_HOST}" @"
    echo '🔄 Restarting container: $CONTAINER_NAME'
    docker restart $CONTAINER_NAME || {
        echo '⚠️ Container not found or restart failed'
        echo '📋 Checking running containers...'
        docker ps -a
    }
    echo '✅ Container restarted'
"@

if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️ Container restart had issues, but continuing..." -ForegroundColor Yellow
}

# Show container status
Write-Host "`n📊 Checking container status..." -ForegroundColor Cyan
ssh -p $PI_PORT "${PI_USER}@${PI_HOST}" @"
    docker ps --filter name=$CONTAINER_NAME --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
"@

# Show recent logs
Write-Host "`n📜 Recent container logs:" -ForegroundColor Cyan
ssh -p $PI_PORT "${PI_USER}@${PI_HOST}" @"
    docker logs --tail 20 $CONTAINER_NAME
"@

Write-Host "`n✅ Deployment complete!" -ForegroundColor Green
Write-Host "🌐 Your app should now be running with the latest changes" -ForegroundColor Cyan
Write-Host "📝 The files are volume-mounted, so changes are immediately available" -ForegroundColor Cyan
