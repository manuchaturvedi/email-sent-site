param(
    [string]$RemotePath = "/home/manu/email-sent-site"
)

$Host.UI.RawUI.WindowTitle = "Transfer to Raspberry Pi"

# Colors for output
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

function Write-Success($text) { Write-ColorOutput Green $text }
function Write-Info($text) { Write-ColorOutput Cyan $text }
function Write-Warning($text) { Write-ColorOutput Yellow $text }
function Write-Error($text) { Write-ColorOutput Red $text }

Write-Info "Starting file transfer to Raspberry Pi..."

# Configuration for Porthole
$LocalPort = "8888"
$RemoteHost = "localhost"
$Username = "manu"

# Create tar.gz of the project
Write-Info "Creating project archive..."
tar -czf linkedin-app.tar.gz `
    --exclude='.git' `
    --exclude='.venv' `
    --exclude='__pycache__' `
    --exclude='*.pyc' `
    --exclude='chrome-profile/*' `
    --exclude='node_modules' `
    *

# Transfer the archive using scp through Porthole
Write-Info "Transferring files to Raspberry Pi..."
scp -P $LocalPort linkedin-app.tar.gz "${Username}@${RemoteHost}:${RemotePath}/"

if ($LASTEXITCODE -eq 0) {
    Write-Success "File transfer completed successfully!"
    
    # SSH commands to extract and set up
    Write-Info "Setting up project on Raspberry Pi..."
    $sshCommands = @"
cd ${RemotePath}
tar xzf linkedin-app.tar.gz
rm linkedin-app.tar.gz
chmod +x deploy-rpi.sh
"@
    
    $sshCommands | ssh -p $LocalPort "${Username}@${RemoteHost}"
    
    Write-Success "Setup completed!"
    Write-Info "`nNext steps:"
    Write-Host "1. Open VS Code SSH window"
    Write-Host "2. Navigate to: $RemotePath"
    Write-Host "3. Run: sudo ./deploy-rpi.sh"
} else {
    Write-Error "File transfer failed!"
    exit 1
}

# Cleanup local archive
Remove-Item linkedin-app.tar.gz -Force

Write-Success "`nTransfer process completed!"
