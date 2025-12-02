# Deploy LinkedIn Scraper to Raspberry Pi (PowerShell)
# Run this script from PowerShell on Windows

Write-Host "`n==================================================" -ForegroundColor Cyan
Write-Host "🚀 DEPLOYING LINKEDIN SCRAPER TO RASPBERRY PI" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# Configuration
$PI_USER = "manu"
$PI_HOST = "localhost"
$PI_PORT = "8888"
$PI_PATH = "/home/manu/justmailit"

Write-Host "`n📦 Step 1: Transferring scraper files..." -ForegroundColor Yellow
scp -P $PI_PORT linkedin_job_scraper.py "${PI_USER}@${PI_HOST}:${PI_PATH}/"
scp -P $PI_PORT merge_databases.py "${PI_USER}@${PI_HOST}:${PI_PATH}/"
scp -P $PI_PORT SCRAPER_README.md "${PI_USER}@${PI_HOST}:${PI_PATH}/"
scp -P $PI_PORT check_db.py "${PI_USER}@${PI_HOST}:${PI_PATH}/"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Files transferred successfully" -ForegroundColor Green
} else {
    Write-Host "❌ File transfer failed" -ForegroundColor Red
    exit 1
}

Write-Host "`n📦 Step 2: Setting up scraper on Pi..." -ForegroundColor Yellow
ssh -p $PI_PORT "${PI_USER}@${PI_HOST}" @"
cd /home/manu/justmailit

echo '🔧 Installing Python dependencies...'
pip3 install selenium --break-system-packages 2>/dev/null || pip3 install selenium

echo '🔧 Installing Chromium and ChromeDriver...'
sudo apt-get update -qq
sudo apt-get install -y chromium-browser chromium-chromedriver 2>/dev/null || sudo apt-get install -y chromium chromium-driver

echo '✅ Dependencies installed'

echo ''
echo '📊 Current database status:'
python3 -c \"
import sqlite3
import os
if os.path.exists('justmailit.db'):
    conn = sqlite3.connect('justmailit.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM job_posts')
    print(f'  Total jobs: {cursor.fetchone()[0]}')
    cursor.execute('SELECT COUNT(*) FROM job_posts WHERE user_email=\\\"manuchaturvedi28mc@gmail.com\\\"')
    print(f'  Admin jobs: {cursor.fetchone()[0]}')
    conn.close()
else:
    print('  Database not found')
\"

echo ''
echo '✅ Setup complete!'
"@

Write-Host "`n==================================================" -ForegroundColor Cyan
Write-Host "✅ DEPLOYMENT COMPLETE" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Cyan

Write-Host "`n📋 Next steps:" -ForegroundColor Yellow
Write-Host "1. Test the scraper:" -ForegroundColor White
Write-Host "   ssh -p 8888 manu@localhost" -ForegroundColor Gray
Write-Host "   cd /home/manu/justmailit" -ForegroundColor Gray
Write-Host "   python3 linkedin_job_scraper.py --role 'Python Developer' --scrolls 10" -ForegroundColor Gray

Write-Host "`n2. Check results:" -ForegroundColor White
Write-Host "   python3 linkedin_job_scraper.py --stats" -ForegroundColor Gray

Write-Host "`n3. Restart app to see new jobs:" -ForegroundColor White
Write-Host "   docker restart justmailit-app" -ForegroundColor Gray

Write-Host "`n4. Or run test script:" -ForegroundColor White
Write-Host "   ./test-pi-scraper.ps1" -ForegroundColor Gray
Write-Host ""
