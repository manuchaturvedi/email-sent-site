# Database Backup & Sync Guide

## Overview
Your SQLite databases are now tracked in Git for automatic backup and synchronization between your local machine and Raspberry Pi.

## Database Files Tracked
- `sendmail/justmailit.db` - Main production database
- `justmailit.db` - Root level database
- `justmailit_production.db` - Production backup database

## Automatic Sync

### Quick Sync (Recommended)

**On Windows (PowerShell):**
```powershell
.\sync-database.ps1
```

**On Linux/Mac/Git Bash:**
```bash
./sync-database.sh
```

### What the sync script does:
1. ✅ Commits current database to Git
2. ✅ Pushes to GitHub
3. ✅ Creates backup on Raspberry Pi
4. ✅ Pulls latest database to Pi
5. ✅ Restarts Docker container

## Manual Sync

### Push from Local to GitHub:
```bash
git add sendmail/justmailit.db justmailit.db justmailit_production.db
git commit -m "Update database"
git push origin manu
```

### Pull to Raspberry Pi:
```bash
ssh -p 8888 manu@localhost
cd justmailit
git pull origin manu
docker restart justmailit-app
```

## Important Notes

### Database Backups
- Backups are automatically created on Pi before pulling: `justmailit.db.backup-YYYYMMDD-HHMMSS`
- Keep recent backups for safety

### When to Sync
- After running automation (new jobs/emails added)
- After user registrations
- After admin changes
- Before deploying updates
- Daily (recommended)

### Git Ignore Rules
The following DB-related files are **ignored** (temporary files):
- `*.db-journal`
- `*.db-shm`
- `*.db-wal`

Main `.db` files **are tracked** for backup.

## Conflict Resolution

If you get a merge conflict on the database:

```bash
# On Pi - keep Pi version (usually has latest data)
cd justmailit
git checkout --ours justmailit.db
git add justmailit.db

# Or keep GitHub version
git checkout --theirs justmailit.db
git add justmailit.db
```

## Best Practices

1. **Regular Syncs**: Run sync script daily or after significant changes
2. **Before Updates**: Always sync before deploying code updates
3. **Test Locally**: Test database changes locally before syncing to Pi
4. **Monitor Size**: SQLite databases can grow - monitor GitHub repo size
5. **Backup Strategy**: Keep local backups before major migrations

## Troubleshooting

### Database locked error:
```bash
# Stop the app first
docker stop justmailit-app
# Then sync
git pull origin manu
# Restart
docker restart justmailit-app
```

### Large database size:
```bash
# Vacuum database to optimize size
sqlite3 sendmail/justmailit.db "VACUUM;"
```

### Restore from backup:
```bash
# On Pi
cd justmailit/sendmail
cp justmailit.db.backup-YYYYMMDD-HHMMSS justmailit.db
docker restart justmailit-app
```

## Automated Backups (Optional)

Set up a cron job on Pi for daily backups:

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * cd /home/manu/justmailit && cp sendmail/justmailit.db sendmail/justmailit.db.backup-$(date +\%Y\%m\%d) && find sendmail/ -name "*.db.backup-*" -mtime +7 -delete
```

This creates daily backups and deletes backups older than 7 days.

## Security Note

⚠️ **Important**: Your database contains user data. Ensure your GitHub repository is **private** to protect user information.

Check repo privacy: https://github.com/manuchaturvedi/email-sent-site/settings

---

**Need help?** Check the main README.md or contact the admin.
