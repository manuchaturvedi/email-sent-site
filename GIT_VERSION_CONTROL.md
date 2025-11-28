# Git Version Control on Raspberry Pi

## 📋 Overview
Version control is set up for JustMailIt production code on the Raspberry Pi.

## 🚀 Quick Commands

### Save Current Work
```bash
./git-save.sh "Your commit message here"
```
Or run interactively:
```bash
./git-save.sh
# Then enter your message when prompted
```

### Create Backup Checkpoint
```bash
./git-backup.sh
```
Creates a timestamped backup tag (e.g., `backup-20251123-143000`)

### Restore from Backup
```bash
# List all backups
./git-restore.sh

# Restore specific backup
./git-restore.sh backup-20251123-143000
```

### View History
```bash
cd /home/manu/justmailit
git log --oneline -10          # Last 10 commits
git log --graph --all          # Full tree view
```

### View Current Status
```bash
cd /home/manu/justmailit
git status                     # See changed files
git diff                       # See exact changes
```

### List All Backups
```bash
cd /home/manu/justmailit
git tag | grep backup          # All backup tags
```

## 📂 What's Tracked
- All Python files (`sendmail/*.py`)
- All HTML templates (`sendmail/templates/*.html`)
- Dockerfiles
- Requirements.txt
- Configuration examples

## 🚫 What's NOT Tracked (.gitignore)
- Database files (*.db)
- Virtual environments (.venv/)
- Firebase credentials
- Uploaded files (uploads/)
- Environment files (.env)
- Logs and cache (__pycache__/)

## 💾 Recommended Workflow

### Before Making Changes
```bash
cd /home/manu/justmailit
./git-backup.sh  # Create safety checkpoint
```

### After Testing Changes
```bash
./git-save.sh "Fixed email sending bug"
```

### Before Major Updates
```bash
./git-backup.sh  # Safety first!
# Make your changes...
# Test thoroughly...
./git-save.sh "Updated landing page messaging"
```

## 🔄 Typical Workflow Examples

### Example 1: Fix a Bug
```bash
# Create backup before fixing
./git-backup.sh

# Edit files on Pi or upload via SCP
nano sendmail/app.py

# Test the fix
docker restart justmailit-app

# Save the fix
./git-save.sh "Fixed promotional email SMTP credentials"
```

### Example 2: Update from Windows
```bash
# On Windows - upload files
scp app.py manu@192.168.31.36:/home/manu/justmailit/sendmail/

# On Pi - save changes
ssh manu@192.168.31.36
cd /home/manu/justmailit
./git-save.sh "Updated admin panel features"
```

### Example 3: Something Broke - Restore
```bash
# List available backups
./git-restore.sh

# Restore to last working version
./git-restore.sh backup-20251123-120000

# Restart app
docker restart justmailit-app

# If fix worked, go back to latest
git checkout master
```

## 🏷️ Version Tags
- `v1.0-production` - Initial production version
- `backup-YYYYMMDD-HHMMSS` - Automatic backup checkpoints

## 📞 Quick Reference
```bash
cd /home/manu/justmailit

# See what changed
git status

# Save changes
./git-save.sh "Description of changes"

# Create backup
./git-backup.sh

# View history
git log --oneline -10

# Undo local changes (before commit)
git restore <filename>

# See all backups
git tag | grep backup
```

## ⚠️ Important Notes
1. **Always create backup before major changes**: `./git-backup.sh`
2. **Database changes are NOT tracked** - backup database separately
3. **Environment variables NOT tracked** - keep .env file safe separately
4. **Restart Docker after code changes**: `docker restart justmailit-app`

## 🔒 Database Backups (Separate)
Git doesn't track database files. Backup database manually:
```bash
# Backup database
cp /home/manu/justmailit/sendmail/justmailit.db /home/manu/justmailit/sendmail/justmailit.db.backup-$(date +%Y%m%d)

# Restore database
cp /home/manu/justmailit/sendmail/justmailit.db.backup-20251123 /home/manu/justmailit/sendmail/justmailit.db
```
