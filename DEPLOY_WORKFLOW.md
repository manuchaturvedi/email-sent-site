# Development to Deployment Workflow

## Overview
Develop on Windows laptop, deploy to Raspberry Pi for 24/7 hosting.

## Local Development (Windows Laptop)

### 1. File Location
```
C:\Users\windows 10\Desktop\AI_support\
```

### 2. Edit Files
- **Templates**: `sendmail/templates/`
- **Styles**: `sendmail/static/css/`
- **Images**: `sendmail/static/images/`
- **Backend**: `sendmail/app.py`, `sendmail/firestore_ops.py`, etc.

### 3. Test Locally (Optional)
```powershell
# Option A: Run Flask directly
cd "C:\Users\windows 10\Desktop\AI_support"
python sendmail/app.py

# Option B: Test with Docker
docker build -t justmailit-test -f Dockerfile.render .
docker run -p 5000:5000 justmailit-test
```
Access at: http://localhost:5000

---

## Deploy to Raspberry Pi

### Method 1: Quick SCP Transfer (Recommended)

**Step 1: Transfer updated files**
```powershell
# Transfer entire sendmail directory
scp -r "C:\Users\windows 10\Desktop\AI_support\sendmail\" manu@192.168.31.36:~/justmailit/

# Or transfer specific files only
scp "C:\Users\windows 10\Desktop\AI_support\sendmail\templates\index_mobile.html" manu@192.168.31.36:~/justmailit/sendmail/templates/
scp "C:\Users\windows 10\Desktop\AI_support\sendmail\static\css\mobile-app.css" manu@192.168.31.36:~/justmailit/sendmail/static/css/
```
Password: `manu`

**Step 2: Rebuild & Restart on Pi**
```powershell
ssh manu@192.168.31.36
```
Then on Pi:
```bash
cd ~/justmailit

# Stop existing container
docker stop justmailit-app
docker rm justmailit-app

# Rebuild image with new code
sudo docker build -t justmailit -f Dockerfile.pi .

# Start new container
docker run -d -p 5000:5000 --name justmailit-app \
  -e UPI_ID='7987633729@ybl' \
  -e UPI_NAME='JustMailIt' \
  --restart unless-stopped \
  justmailit

# Verify it's running
docker ps
docker logs justmailit-app
```

**Step 3: Test**
Visit: https://justmailit.in

---

### Method 2: Automated Deployment Script

**Create deploy script on laptop:**

`deploy-to-pi.ps1`:
```powershell
# JustMailIt Deployment Script
$PI_USER = "manu"
$PI_HOST = "192.168.31.36"
$LOCAL_PATH = "C:\Users\windows 10\Desktop\AI_support\sendmail\"
$REMOTE_PATH = "~/justmailit/sendmail/"

Write-Host "🚀 Deploying JustMailIt to Raspberry Pi..." -ForegroundColor Cyan

# Transfer files
Write-Host "📦 Transferring files..." -ForegroundColor Yellow
scp -r $LOCAL_PATH "${PI_USER}@${PI_HOST}:${REMOTE_PATH}"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Files transferred successfully" -ForegroundColor Green
    
    # Rebuild and restart on Pi
    Write-Host "🔄 Rebuilding Docker image..." -ForegroundColor Yellow
    ssh "${PI_USER}@${PI_HOST}" @"
        cd ~/justmailit && \
        docker stop justmailit-app && \
        docker rm justmailit-app && \
        sudo docker build -t justmailit -f Dockerfile.pi . && \
        docker run -d -p 5000:5000 --name justmailit-app \
          -e UPI_ID='7987633729@ybl' \
          -e UPI_NAME='JustMailIt' \
          --restart unless-stopped \
          justmailit && \
        echo '✅ Deployment complete!' && \
        docker ps | grep justmailit-app
"@
    
    Write-Host "`n🌐 Website live at: https://justmailit.in" -ForegroundColor Green
} else {
    Write-Host "❌ File transfer failed" -ForegroundColor Red
}
```

**Usage:**
```powershell
.\deploy-to-pi.ps1
```

---

## Quick Reference Commands

### Check Pi Status
```powershell
# System resources
ssh manu@192.168.31.36 "free -h && df -h | grep root && docker ps"

# View logs
ssh manu@192.168.31.36 "docker logs justmailit-app --tail 50"

# Restart services
ssh manu@192.168.31.36 "sudo systemctl restart cloudflared && docker restart justmailit-app"
```

### Emergency Rollback
```powershell
# If new deployment breaks, restore previous container
ssh manu@192.168.31.36 "docker start justmailit-app"
```

### Update Environment Variables
```bash
# Stop container
docker stop justmailit-app
docker rm justmailit-app

# Start with new variables
docker run -d -p 5000:5000 --name justmailit-app \
  -e UPI_ID='NEW_VALUE' \
  -e UPI_NAME='NEW_NAME' \
  -e NEW_VAR='value' \
  --restart unless-stopped \
  justmailit
```

---

## Network Considerations

### WiFi Changes
**No action needed!** Cloudflare Tunnel uses outbound connections, so:
- ✅ Works with different WiFi networks
- ✅ No port forwarding required
- ✅ No static IP needed
- ✅ Pi just needs internet connection

If WiFi changes:
1. Reconnect Pi to new WiFi
2. Cloudflare Tunnel auto-reconnects
3. Site remains accessible at justmailit.in

### Verify Tunnel Status
```bash
sudo systemctl status cloudflared
# Should show: Active: active (running)
```

---

## Troubleshooting

### Issue: Website not loading
```bash
# Check container
docker ps | grep justmailit-app

# Check logs
docker logs justmailit-app

# Check tunnel
sudo systemctl status cloudflared

# Restart everything
docker restart justmailit-app
sudo systemctl restart cloudflared
```

### Issue: Build fails
```bash
# Check disk space
df -h

# Clean Docker cache if needed
docker system prune -a
```

### Issue: File transfer fails
```powershell
# Test Pi connection
ping 192.168.31.36
ssh manu@192.168.31.36 "echo 'Connection OK'"

# Check file paths
ls "C:\Users\windows 10\Desktop\AI_support\sendmail\"
```

---

## Best Practices

1. **Test Locally First**: Run on laptop before deploying to Pi
2. **Check Logs**: Always check `docker logs` after deployment
3. **Backup**: Keep backups of working versions
4. **Incremental Changes**: Deploy small changes frequently rather than large batches
5. **Monitor Resources**: Check Pi memory/CPU if experiencing issues

---

## File Structure Reference

```
Laptop: C:\Users\windows 10\Desktop\AI_support\
├── sendmail/
│   ├── app.py                    # Main Flask app
│   ├── firestore_ops.py         # Database operations
│   ├── job_analyzer.py          # Email automation
│   ├── requirements.txt         # Python dependencies
│   ├── templates/
│   │   ├── index_mobile.html    # New mobile-first UI
│   │   ├── index_live.html      # Original UI
│   │   └── ...
│   └── static/
│       ├── css/
│       │   └── mobile-app.css   # New mobile styles
│       └── images/
│           ├── logo.svg
│           └── justmailit-logo.png

Pi: /home/manu/justmailit/
├── Dockerfile.pi                # ARM64 Docker config
├── requirements.txt
└── sendmail/                    # Same structure as laptop
```

---

## Quick Deploy Checklist

- [ ] Edit files on laptop
- [ ] Test locally (optional)
- [ ] Transfer files to Pi via SCP
- [ ] SSH to Pi
- [ ] Stop and remove old container
- [ ] Rebuild Docker image
- [ ] Start new container
- [ ] Check logs for errors
- [ ] Test website at justmailit.in
- [ ] Verify container auto-restart enabled

---

## Contact & Support

**Raspberry Pi Access:**
- IP: 192.168.31.36
- User: manu
- Password: manu

**Domain:** justmailit.in
**Cloudflare Tunnel:** justmailit (ID: 8c5eb7e8-dddc-4613-8d09-409631db0731)
