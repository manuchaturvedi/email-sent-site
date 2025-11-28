# Deployment Guide for justmailit.in on Raspberry Pi

## 1. Initial Setup

### On your Raspberry Pi:
```bash
# Clone your repository (if not already done)
git clone https://github.com/manuchaturvedi/email-sent-site.git
cd email-sent-site

# Make deployment script executable
chmod +x deploy-rpi.sh
```

## 2. Dataplicity Wormhole Setup

1. Log into your Dataplicity dashboard
2. Select your device
3. Go to "Wormhole" tab
4. Enable Wormhole
5. Note down your Wormhole URL (e.g., your-device.dataplicity.io)

## 3. GoDaddy Domain Configuration

1. Log into your GoDaddy account
2. Go to Domain Manager
3. Select justmailit.in
4. Go to DNS Management
5. Add/Update these DNS records:

   | Type  | Name | Value                      | TTL    |
   |-------|------|----------------------------|--------|
   | CNAME | @    | your-device.dataplicity.io | 600    |
   | CNAME | www  | your-device.dataplicity.io | 600    |

   Note: Replace "your-device.dataplicity.io" with your actual Dataplicity Wormhole URL

## 4. Deploy Application

```bash
# Run deployment script
sudo ./deploy-rpi.sh
```

## 5. Verify Deployment

1. Check local access: http://localhost
2. Check Dataplicity Wormhole: https://your-device.dataplicity.io
3. Check your domain: https://justmailit.in

## 6. Troubleshooting

### Check application status:
```bash
docker-compose -f docker-compose.rpi.yml ps
```

### View logs:
```bash
docker-compose -f docker-compose.rpi.yml logs -f
```

### Restart services:
```bash
docker-compose -f docker-compose.rpi.yml restart
```

### Check Dataplicity connection:
```bash
sudo systemctl status dataplicity
```

## Important Notes

1. **SSL Certificates**: Dataplicity Wormhole provides SSL automatically
2. **Domain Propagation**: DNS changes may take up to 48 hours to propagate
3. **Port Forwarding**: Not needed with Dataplicity Wormhole
4. **Persistence**: Data is stored in mounted volumes

## Monitoring

1. **Application Status**:
   ```bash
   ./check-dataplicity.sh
   ```

2. **Resource Usage**:
   ```bash
   htop
   ```

## Backup

Regular backups of these directories are recommended:
- /app/chrome-profile
- /app/uploads
- /app/job_posts.json
- /app/sent_emails.json

## Security Recommendations

1. Keep Raspberry Pi updated:
   ```bash
   sudo apt update
   sudo apt upgrade
   ```

2. Enable UFW firewall:
   ```bash
   sudo ufw enable
   sudo ufw allow 80
   sudo ufw allow 443
   sudo ufw allow 22
   ```

3. Set up automatic security updates:
   ```bash
   sudo apt install unattended-upgrades
   sudo dpkg-reconfigure unattended-upgrades
   ```