# INSTRUCTIONS TO ENABLE LLM-BASED LOCATION EXTRACTION

## Option 1: Use OpenAI (Recommended - Most Accurate)

1. **Get an OpenAI API Key:**
   - Visit: https://platform.openai.com/api-keys
   - Sign up or log in
   - Create a new API key
   - Copy the key (starts with 'sk-...')

2. **Set the API Key:**
   
   **Windows PowerShell:**
   ```powershell
   $env:OPENAI_API_KEY = "sk-your-actual-key-here"
   cd "c:\Users\windows 10\Desktop\AI_support\sendmail"
   python app.py
   ```
   
   **Or create a .env file:**
   Create a file named `.env` in the AI_support folder:
   ```
   OPENAI_API_KEY=sk-your-actual-key-here
   ```
   
   Then install python-dotenv:
   ```powershell
   pip install python-dotenv
   ```

3. **Costs:**
   - GPT-3.5-turbo: ~$0.0015 per 1000 tokens
   - Each location extraction: ~100-200 tokens
   - Estimate: ~$0.0003 per job post
   - Free tier: $5 credit for new accounts

## Current Status

✅ OpenAI package installed
❌ API key not configured

**The system currently uses pattern-based extraction (free but less accurate)**

## To Enable LLM Now:

Run this in PowerShell before starting the server:
```powershell
$env:OPENAI_API_KEY = "sk-your-key-here"
cd "c:\Users\windows 10\Desktop\AI_support\sendmail"
& "C:/Users/windows 10/Desktop/AI_support/.venv/Scripts/python.exe" app.py
```

The server will automatically detect the API key and enable LLM extraction!
