# LinkedIn Automation Docker Management Script (PowerShell)
# Usage: .\docker-manage.ps1 [command]

param(
    [Parameter(Position=0)]
    [string]$Command = "help",
    
    [Parameter(Position=1)]
    [string]$Argument
)

$ProjectName = "linkedin-automation"
$ErrorActionPreference = "Stop"

# Color functions
function Write-Success {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor Green
}

function WriteError {
    param([string]$Message)
    Write-Host "✗ $Message" -ForegroundColor Red
}

function Write-Info {
    param([string]$Message)
    Write-Host "ℹ $Message" -ForegroundColor Yellow
}

function Write-Header {
    Write-Host "================================" -ForegroundColor Blue
    Write-Host "  LinkedIn Automation Docker" -ForegroundColor Blue
    Write-Host "================================" -ForegroundColor Blue
    Write-Host ""
}

# Check if Docker is running
function Test-Docker {
    try {
        docker info | Out-Null
        Write-Success "Docker is running"
        return $true
    }
    catch {
        WriteError "Docker is not running. Please start Docker Desktop."
        exit 1
    }
}

# Build the container
function Build-Container {
    Write-Info "Building Docker image..."
    docker-compose build --no-cache
    Write-Success "Build completed"
}

# Start the container
function Start-Container {
    Write-Info "Starting container..."
    docker-compose up -d
    Write-Success "Container started"
    Write-Info "Application available at: http://localhost:5000"
}

# Stop the container
function Stop-Container {
    Write-Info "Stopping container..."
    docker-compose down
    Write-Success "Container stopped"
}

# Restart the container
function Restart-Container {
    Write-Info "Restarting container..."
    docker-compose restart
    Write-Success "Container restarted"
}

# View logs
function Show-Logs {
    Write-Info "Showing logs (Ctrl+C to exit)..."
    docker-compose logs -f
}

# Show status
function Show-Status {
    Write-Info "Container status:"
    docker-compose ps
    Write-Host ""
    Write-Info "Resource usage:"
    try {
        docker stats --no-stream $ProjectName
    }
    catch {
        Write-Host "Container not running"
    }
}

# Clean up
function Clean-Up {
    Write-Info "Cleaning up..."
    docker-compose down -v
    docker system prune -f
    Write-Success "Cleanup completed"
}

# Shell access
function Open-Shell {
    Write-Info "Opening shell in container..."
    docker exec -it $ProjectName /bin/bash
}

# Backup Chrome profile
function Backup-Profile {
    Write-Info "Backing up Chrome profile..."
    $BackupDir = "chrome-profile-backup-$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    Copy-Item -Path "chrome-profile" -Destination $BackupDir -Recurse
    Write-Success "Profile backed up to $BackupDir"
}

# Restore Chrome profile
function Restore-Profile {
    param([string]$BackupDir)
    
    if ([string]::IsNullOrEmpty($BackupDir)) {
        WriteError "Please specify backup directory"
        exit 1
    }
    
    Write-Info "Restoring Chrome profile from $BackupDir..."
    
    if (Test-Path "chrome-profile") {
        Remove-Item -Path "chrome-profile" -Recurse -Force
    }
    
    Copy-Item -Path $BackupDir -Destination "chrome-profile" -Recurse
    Write-Success "Profile restored"
}

# Rebuild (build + start)
function Rebuild-Container {
    Stop-Container
    Build-Container
    Start-Container
}

# Show help
function Show-Help {
    Write-Header
    Write-Host "Usage: .\docker-manage.ps1 [command]" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Commands:" -ForegroundColor Cyan
    Write-Host "  build          Build the Docker image"
    Write-Host "  start          Start the container"
    Write-Host "  stop           Stop the container"
    Write-Host "  restart        Restart the container"
    Write-Host "  logs           View container logs"
    Write-Host "  status         Show container status"
    Write-Host "  clean          Clean up containers and images"
    Write-Host "  shell          Open shell in container"
    Write-Host "  backup         Backup Chrome profile"
    Write-Host "  restore [dir]  Restore Chrome profile from backup"
    Write-Host "  rebuild        Rebuild and restart"
    Write-Host "  help           Show this help message"
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Cyan
    Write-Host "  .\docker-manage.ps1 build"
    Write-Host "  .\docker-manage.ps1 start"
    Write-Host "  .\docker-manage.ps1 logs"
    Write-Host "  .\docker-manage.ps1 restore chrome-profile-backup-20250106"
}

# Main script execution
Write-Header
Test-Docker

switch ($Command.ToLower()) {
    "build" {
        Build-Container
    }
    "start" {
        Start-Container
    }
    "stop" {
        Stop-Container
    }
    "restart" {
        Restart-Container
    }
    "logs" {
        Show-Logs
    }
    "status" {
        Show-Status
    }
    "clean" {
        Clean-Up
    }
    "shell" {
        Open-Shell
    }
    "backup" {
        Backup-Profile
    }
    "restore" {
        Restore-Profile -BackupDir $Argument
    }
    "rebuild" {
        Rebuild-Container
    }
    default {
        if ($Command -ne "help") {
            WriteError "Unknown command: $Command"
            Write-Host ""
        }
        Show-Help
    }
}
