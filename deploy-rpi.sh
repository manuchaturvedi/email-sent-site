#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${NC}$1${NC}"
}

print_step() {
    echo -e "${YELLOW}$1${NC}"
}

print_error() {
    echo -e "${RED}$1${NC}"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "Please run this script as root (using sudo)"
    exit 1
fi

print_step "1. Configuring SSH access..."
# Enable and start SSH
systemctl enable ssh
systemctl start ssh

# Regenerate SSH host keys if needed
systemctl enable regenerate_ssh_host_keys.service
systemctl start regenerate_ssh_host_keys.service

# Verify SSH is running
if systemctl is-active --quiet ssh; then
    print_status "✅ SSH service configured successfully"
else
    print_error "❌ SSH service failed to start"
    exit 1
fi

print_step "2. Setting up Docker..."
# Install Docker if not present
if ! command -v docker &> /dev/null; then
    print_status "Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    usermod -aG docker $USER
    systemctl enable docker
    systemctl start docker
else
    print_status "Docker already installed"
fi

print_step "3. Building Docker image..."
docker-compose -f docker-compose.rpi.yml build --no-cache

print_step "4. Starting services..."
docker-compose -f docker-compose.rpi.yml up -d

print_step "5. Verifying deployment..."
sleep 10

if docker-compose -f docker-compose.rpi.yml ps | grep -q "Up"; then
    print_status "✅ Deployment successful!"
    print_status ""
    print_status "🔐 SSH Access:"
    print_status "   - Local network: ssh pi@raspberrypi.local"
    print_status "   - Via Dataplicity: Use web terminal"
    print_status ""
    print_status "🌐 Application Access:"
    print_status "   - Local: http://localhost:5000"
    print_status "   - Via Dataplicity: Check your Dataplicity dashboard"
    print_status ""
    print_status "📊 Useful Commands:"
    print_status "   - View logs: docker-compose -f docker-compose.rpi.yml logs -f"
    print_status "   - Restart: docker-compose -f docker-compose.rpi.yml restart"
    print_status "   - Stop: docker-compose -f docker-compose.rpi.yml down"
else
    print_error "❌ Deployment failed. Check the logs:"
    docker-compose -f docker-compose.rpi.yml logs
    exit 1
fi
