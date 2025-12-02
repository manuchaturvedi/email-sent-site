#!/bin/bash
# Deploy LinkedIn Scraper to Raspberry Pi
# Run this script from Windows PowerShell or Git Bash

echo "=================================================="
echo "🚀 DEPLOYING LINKEDIN SCRAPER TO RASPBERRY PI"
echo "=================================================="

# Configuration
PI_USER="manu"
PI_HOST="localhost"
PI_PORT="8888"
PI_PATH="/home/manu/justmailit"

echo ""
echo "📦 Step 1: Transferring scraper files..."
scp -P $PI_PORT linkedin_job_scraper.py $PI_USER@$PI_HOST:$PI_PATH/
scp -P $PI_PORT merge_databases.py $PI_USER@$PI_HOST:$PI_PATH/
scp -P $PI_PORT SCRAPER_README.md $PI_USER@$PI_HOST:$PI_PATH/

echo ""
echo "✅ Files transferred"

echo ""
echo "📦 Step 2: Setting up scraper on Pi..."
ssh -p $PI_PORT $PI_USER@$PI_HOST << 'EOF'
cd /home/manu/justmailit

echo "🔧 Installing Python dependencies..."
pip3 install selenium --break-system-packages 2>/dev/null || pip3 install selenium

echo "🔧 Installing Chromium and ChromeDriver..."
sudo apt-get update -qq
sudo apt-get install -y chromium-browser chromium-chromedriver 2>/dev/null || \
sudo apt-get install -y chromium chromium-driver

echo "✅ Dependencies installed"

echo ""
echo "📊 Current database status:"
python3 -c "
import sqlite3
import os
if os.path.exists('justmailit.db'):
    conn = sqlite3.connect('justmailit.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM job_posts')
    print(f'  Total jobs: {cursor.fetchone()[0]}')
    cursor.execute('SELECT COUNT(*) FROM job_posts WHERE user_email=\"manuchaturvedi28mc@gmail.com\"')
    print(f'  Admin jobs: {cursor.fetchone()[0]}')
    conn.close()
else:
    print('  Database not found')
"

echo ""
echo "✅ Setup complete!"
EOF

echo ""
echo "=================================================="
echo "✅ DEPLOYMENT COMPLETE"
echo "=================================================="
echo ""
echo "📋 Next steps:"
echo "1. Test the scraper:"
echo "   ssh -p 8888 manu@localhost"
echo "   cd /home/manu/justmailit"
echo "   python3 linkedin_job_scraper.py --role 'Python Developer' --scrolls 10"
echo ""
echo "2. Check results:"
echo "   python3 linkedin_job_scraper.py --stats"
echo ""
echo "3. Restart app to see new jobs:"
echo "   docker restart justmailit-app"
echo ""
