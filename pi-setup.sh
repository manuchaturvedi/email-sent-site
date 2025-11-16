#!/bin/bash
# JustMailIt Raspberry Pi Setup Script

echo "🚀 Setting up JustMailIt on Raspberry Pi..."

# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Docker
echo "🐳 Installing Docker..."
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
rm get-docker.sh

# Install Cloudflare Tunnel
echo "☁️ Installing Cloudflare Tunnel..."
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm.deb
sudo dpkg -i cloudflared-linux-arm.deb
rm cloudflared-linux-arm.deb

# Copy Cloudflare credentials from laptop
echo "🔑 Setting up Cloudflare credentials..."
mkdir -p ~/.cloudflared

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Copy Cloudflare credentials: scp from your laptop"
echo "2. Build Docker image: cd ~/justmailit && docker build -t justmailit -f Dockerfile.render ."
echo "3. Run container: docker run -d -p 5000:5000 --name justmailit justmailit"
echo "4. Run Cloudflare tunnel: cloudflared tunnel run justmailit"
echo ""
echo "To apply Docker group, logout and login again or run: newgrp docker"
