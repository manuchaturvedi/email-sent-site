# Database Persistence Guide

## Current Setup

Your database is **already persistent** because:
- The entire `/home/manu/justmailit` directory is mounted to the Docker container
- Database file: `/home/manu/justmailit/sendmail/justmailit.db`
- This file exists on the host machine, not inside the container
- When container rebuilds, the file is NOT deleted

## Database Location

```
Host: /home/manu/justmailit/sendmail/justmailit.db
Container: /app/sendmail/justmailit.db
```

## Why Database Was Lost Before

When you ran `git restore justmailit.db`, it replaced your database with the version from GitHub (which is older/empty).

## How to Prevent Data Loss

### 1. Database is now in .gitignore
The database files are excluded from Git, so `git pull` or `git restore` won't affect them.

### 2. Create backups before risky operations

```bash
# Backup database
/home/manu/justmailit/backup_db.sh

# This creates: /home/manu/justmailit/db_backups/justmailit_TIMESTAMP.db
```

### 3. Restore from backup if needed

```bash
# List backups
ls -lh /home/manu/justmailit/db_backups/

# Restore from backup
cp /home/manu/justmailit/db_backups/justmailit_TIMESTAMP.db /home/manu/justmailit/sendmail/justmailit.db

# Restart container
docker restart justmailit-app
```

## Container Operations

### Rebuilding Container (data is safe)
```bash
docker stop justmailit-app
docker rm justmailit-app
docker build -t justmailit-app .
docker run -d --name justmailit-app -p 5000:5000 -v /home/manu/justmailit:/app justmailit-app
```

### Restarting Container (data is safe)
```bash
docker restart justmailit-app
```

### Viewing Container (data is safe)
```bash
docker logs -f justmailit-app
```

## Data Persistence Verified

✅ Database files are on host filesystem
✅ Volume mount: `/home/manu/justmailit` → `/app`
✅ Automatic backups available
✅ Database excluded from Git
✅ Survives container rebuilds
✅ Survives container restarts
✅ Survives system reboots

## Current Backups

```bash
# View all backups
ls -lh /home/manu/justmailit/db_backups/

# Latest backup created: 20251129_010416
```

## Important

- ❌ DON'T run `git restore *.db` (will replace with old version)
- ✅ DO run `backup_db.sh` before major changes
- ✅ DO keep database files on host (already done)
- ✅ DO use volume mounts (already configured)
