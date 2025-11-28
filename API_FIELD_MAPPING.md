# API Field Name Mapping - Fixed

## Summary
All API endpoints now properly convert between database snake_case and frontend camelCase.

## Fixed Endpoints

### ✅ GET /get_profile
**Database (snake_case)** → **Frontend (camelCase)**
- `email_subject` → `emailSubject`
- `email_content` → `emailContent`
- `search_role` → `searchRole`
- `search_time_period` → `searchTimePeriod`
- `resume_filename` → `resumeFilename`
- `resume_data` (BLOB) → `hasResume` (boolean) + `resumeSize` (number)
- `display_name` → `displayName`
- `photo_url` → `photoUrl`
- `created_at` → `createdAt`
- `updated_at` → `updatedAt`

**Used by:**
- `/profile` page (profile.html)
- `/send` page (index_live.html)

### ✅ GET /preferences
**Database (snake_case)** → **Frontend (camelCase)**
- `email_subject` → `defaultSubject`
- `email_content` → `defaultTemplate`
- `search_role` → `searchRole`
- `search_time_period` → `searchTimePeriod`
- `resume_filename` → `resumeFilename`
- `updated_at` → `lastUpdated`

**Used by:**
- Legacy preference endpoints

## Endpoints Already Using Correct Format

### ✅ GET /api/sent_emails
Returns snake_case directly (matches template expectations):
- `recipient_email`
- `sent_at`
- `job_title`
- `status`

**Used by:** `/sent_emails` page (sent_emails.html uses snake_case)

### ✅ POST /save_profile
Accepts camelCase from form:
- `emailSubject` → stored as `email_subject`
- `emailContent` → stored as `email_content`
- `searchRole` → stored as `search_role`
- `searchTimePeriod` → stored as `search_time_period`
- `resumeFile` → stored as BLOB in `resume_data` + `resume_filename`

## Database Storage

All data stored in SQLite with snake_case:
- `user_profiles.email_subject` (TEXT)
- `user_profiles.email_content` (TEXT)
- `user_profiles.search_role` (TEXT)
- `user_profiles.search_time_period` (TEXT, default: 'past-week')
- `user_profiles.resume_data` (BLOB) - binary file data
- `user_profiles.resume_filename` (TEXT)

## Resume Storage Method

**Current Implementation:** BLOB in database
- Uploaded file → Binary data stored directly in `resume_data` column
- Benefits: No file system dependencies, works in Docker, automatic backup
- On retrieval: BLOB written to temp file for email attachment

## Testing Checklist

✅ Profile page loads saved data
✅ Profile page saves new data
✅ Send page loads profile defaults
✅ Resume uploads save to database
✅ Resume retrieves from database for automation
✅ Sent emails display correctly
✅ No 500 errors on profile endpoints
