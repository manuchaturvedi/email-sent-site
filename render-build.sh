#!/bin/bash
# render-build.sh - Install Chrome and dependencies for Render deployment

echo "🚀 Starting Render build with Chrome installation..."

# Install Python dependencies
echo "📦 Installing Python packages..."
pip install -r requirements.txt

# Install Chrome and ChromeDriver
echo "🌐 Installing Google Chrome..."

# Add Google's signing key
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add -

# Add Chrome repository
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list

# Update package list
apt-get update

# Install Chrome
apt-get install -y google-chrome-stable

# Install ChromeDriver
echo "🔧 Installing ChromeDriver..."
CHROMEDRIVER_VERSION=$(curl -sS chromedriver.chromium.org/version)
wget -q -O /tmp/chromedriver.zip "https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip"
unzip /tmp/chromedriver.zip -d /tmp
mv /tmp/chromedriver /usr/local/bin/chromedriver
chmod +x /usr/local/bin/chromedriver

# Verify installations
echo "✅ Chrome version:"
google-chrome --version

echo "✅ ChromeDriver version:"
chromedriver --version

echo "🎉 Build complete with Chrome support!"