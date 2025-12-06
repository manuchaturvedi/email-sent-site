#!/bin/bash
# Quick deployment script for Raspberry Pi
# Run this on your Raspberry Pi

set -e  # Exit on error

echo "🚀 Starting deployment to Raspberry Pi..."
echo ""

# Navigate to project directory
cd /home/pi/email-sent-site || cd ~/email-sent-site || cd /app

echo "📥 Pulling latest code from git..."
git pull origin manu

echo ""
echo "🛑 Stopping existing containers..."
docker-compose down

echo ""
echo "🔨 Rebuilding Docker images..."
docker-compose build --no-cache

echo ""
echo "🚀 Starting containers..."
docker-compose up -d

echo ""
echo "⏳ Waiting for services to start..."
sleep 10

echo ""
echo "📊 Checking container status..."
docker-compose ps

echo ""
echo "📝 Viewing recent logs..."
docker-compose logs --tail=50

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🌐 Your app should be available at:"
echo "   http://localhost:5000 (or your Pi's IP address)"
echo ""
echo "📋 Useful commands:"
echo "   docker-compose logs -f          # Follow logs"
echo "   docker-compose restart          # Restart services"
echo "   docker-compose down            # Stop all services"
echo "   docker-compose ps              # Check status"
