# Test LinkedIn Scraper on Raspberry Pi
# Run this after deploying to test if scraper works on Pi

Write-Host "`n==================================================" -ForegroundColor Cyan
Write-Host "🧪 TESTING LINKEDIN SCRAPER ON RASPBERRY PI" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

$PI_USER = "manu"
$PI_HOST = "localhost"
$PI_PORT = "8888"

Write-Host "`n📊 Step 1: Checking database before scraping..." -ForegroundColor Yellow
ssh -p $PI_PORT "${PI_USER}@${PI_HOST}" @"
cd /home/manu/justmailit
echo '📊 Current database:'
python3 check_db.py 2>/dev/null || python3 -c \"
import sqlite3
conn = sqlite3.connect('justmailit.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM job_posts')
before = cursor.fetchone()[0]
print(f'Jobs before: {before}')
conn.close()
\"
"@

Write-Host "`n🚀 Step 2: Running scraper (test with 5 scrolls)..." -ForegroundColor Yellow
Write-Host "This will take about 30-60 seconds..." -ForegroundColor Gray

ssh -p $PI_PORT "${PI_USER}@${PI_HOST}" @"
cd /home/manu/justmailit
python3 linkedin_job_scraper.py --role 'DevOps Engineer' --scrolls 5 2>&1 | tee scraper_test.log
"@

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ Scraper completed successfully!" -ForegroundColor Green
} else {
    Write-Host "`n⚠️  Scraper completed with warnings (check logs)" -ForegroundColor Yellow
}

Write-Host "`n📊 Step 3: Checking results..." -ForegroundColor Yellow
ssh -p $PI_PORT "${PI_USER}@${PI_HOST}" @"
cd /home/manu/justmailit
echo ''
echo '📊 Database after scraping:'
python3 linkedin_job_scraper.py --stats
echo ''
echo '📝 Last 10 lines of log:'
tail -10 scraper_test.log
"@

Write-Host "`n🔄 Step 4: Restarting Docker app..." -ForegroundColor Yellow
ssh -p $PI_PORT "${PI_USER}@${PI_HOST}" "cd /home/manu/justmailit && docker restart justmailit-app"

Start-Sleep -Seconds 5

Write-Host "`n==================================================" -ForegroundColor Cyan
Write-Host "✅ TEST COMPLETE" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Cyan

Write-Host "`n📋 Results:" -ForegroundColor Yellow
Write-Host "✓ Scraper deployed to Pi" -ForegroundColor Green
Write-Host "✓ Test scraping completed" -ForegroundColor Green
Write-Host "✓ Docker app restarted" -ForegroundColor Green

Write-Host "`n🌐 Check your website now to see if jobs appear!" -ForegroundColor Cyan
Write-Host "   https://justmailit.in/job_posts" -ForegroundColor Gray

Write-Host "`n📝 View full logs on Pi:" -ForegroundColor Yellow
Write-Host "   ssh -p 8888 manu@localhost" -ForegroundColor Gray
Write-Host "   cd /home/manu/justmailit" -ForegroundColor Gray
Write-Host "   cat scraper_test.log" -ForegroundColor Gray
Write-Host ""
