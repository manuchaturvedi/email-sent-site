# JustMailIt - Automated Deployment to Raspberry Pi
# Usage: .\deploy-to-pi.ps1

param(
    [switch]$FullDeploy,  # Deploy entire sendmail directory
    [switch]$TemplatesOnly,  # Deploy only templates
    [switch]$StaticOnly,  # Deploy only static files
    [switch]$SkipRebuild  # Transfer files but don't rebuild Docker
)

$PI_USER = "manu"
$PI_HOST = "192.168.31.36"
$LOCAL_BASE = "C:\Users\windows 10\Desktop\AI_support"
$REMOTE_BASE = "~/justmailit"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "   JustMailIt Deployment Tool v1.0    " -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Function to test Pi connection
function Test-PiConnection {
    Write-Host "🔍 Testing connection to Raspberry Pi..." -ForegroundColor Yellow
    $pingResult = Test-Connection -ComputerName $PI_HOST -Count 1 -Quiet
    
    if (-not $pingResult) {
        Write-Host "❌ Cannot reach Raspberry Pi at $PI_HOST" -ForegroundColor Red
        Write-Host "   Please check:" -ForegroundColor Yellow
        Write-Host "   - Pi is powered on" -ForegroundColor Yellow
        Write-Host "   - Pi is connected to network" -ForegroundColor Yellow
        Write-Host "   - IP address is correct" -ForegroundColor Yellow
        exit 1
    }
    
    Write-Host "✅ Pi is reachable" -ForegroundColor Green
}

# Function to transfer files
function Copy-FilesToPi {
    param([string]$LocalPath, [string]$RemotePath, [string]$Description)
    
    Write-Host "📦 Transferring $Description..." -ForegroundColor Yellow
    
    scp -r $LocalPath "${PI_USER}@${PI_HOST}:${RemotePath}"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ $Description transferred successfully" -ForegroundColor Green
        return $true
    } else {
        Write-Host "❌ Failed to transfer $Description" -ForegroundColor Red
        return $false
    }
}

# Function to rebuild and restart on Pi
function Deploy-ToPi {
    Write-Host "`n🔄 Rebuilding Docker image on Pi..." -ForegroundColor Yellow
    
    $deployScript = @"
cd ~/justmailit
echo '🛑 Stopping old container...'
docker stop justmailit-app 2>/dev/null
docker rm justmailit-app 2>/dev/null
echo '🔨 Building new Docker image...'
sudo docker build -t justmailit -f Dockerfile.pi .
if [ `$? -eq 0 ]; then
    echo '🚀 Starting new container...'
    docker run -d -p 5000:5000 --name justmailit-app \
      -e UPI_ID='7987633729@ybl' \
      -e UPI_NAME='JustMailIt' \
      --restart unless-stopped \
      justmailit
    if [ `$? -eq 0 ]; then
        echo '✅ Deployment successful!'
        echo ''
        echo '📊 Container Status:'
        docker ps | grep justmailit-app
        echo ''
        echo '📝 Recent Logs:'
        docker logs justmailit-app --tail 10
        exit 0
    else
        echo '❌ Failed to start container'
        exit 1
    fi
else
    echo '❌ Docker build failed'
    exit 1
fi
"@
    
    ssh "${PI_USER}@${PI_HOST}" $deployScript
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n✅ Deployment complete!" -ForegroundColor Green
        Write-Host "🌐 Website live at: " -NoNewline -ForegroundColor Green
        Write-Host "https://justmailit.in" -ForegroundColor Cyan
        return $true
    } else {
        Write-Host "`n❌ Deployment failed" -ForegroundColor Red
        return $false
    }
}

# Main execution
try {
    Test-PiConnection
    
    $transferSuccess = $false
    
    if ($TemplatesOnly) {
        Write-Host "`n📋 Mode: Templates Only" -ForegroundColor Cyan
        $transferSuccess = Copy-FilesToPi `
            "$LOCAL_BASE\sendmail\templates\" `
            "$REMOTE_BASE/sendmail/templates/" `
            "templates"
    }
    elseif ($StaticOnly) {
        Write-Host "`n🎨 Mode: Static Files Only" -ForegroundColor Cyan
        $transferSuccess = Copy-FilesToPi `
            "$LOCAL_BASE\sendmail\static\" `
            "$REMOTE_BASE/sendmail/static/" `
            "static files"
    }
    else {
        Write-Host "`n📦 Mode: Full Deployment" -ForegroundColor Cyan
        $transferSuccess = Copy-FilesToPi `
            "$LOCAL_BASE\sendmail\" `
            "$REMOTE_BASE/sendmail/" `
            "all application files"
    }
    
    if ($transferSuccess -and -not $SkipRebuild) {
        Deploy-ToPi
    }
    elseif ($transferSuccess -and $SkipRebuild) {
        Write-Host "`n⏭️  Skipping Docker rebuild (files transferred only)" -ForegroundColor Yellow
        Write-Host "   Run without -SkipRebuild flag to rebuild container" -ForegroundColor Yellow
    }
    
} catch {
    Write-Host "`n❌ Deployment error: $_" -ForegroundColor Red
    exit 1
}

Write-Host "`n" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "       Deployment Complete!            " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "`n" -ForegroundColor Cyan
