#!/usr/bin/env python
"""Test script to check if LLM is configured and working"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("=" * 60)
print("LLM Configuration Test")
print("=" * 60)

# Check for OpenAI
api_key = os.getenv('OPENAI_API_KEY')
if api_key:
    print(f"✓ OPENAI_API_KEY found: {api_key[:8]}...{api_key[-4:]}")
    
    # Try to import openai
    try:
        import openai
        print("✓ OpenAI package installed")
        
        # Test the API key
        print("\nTesting API connection...")
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "user", "content": "Say 'API key working!' if you can read this."}
                ],
                max_tokens=10
            )
            print(f"✓ API Response: {response.choices[0].message.content}")
            print("\n🎉 LLM is FULLY CONFIGURED and WORKING!")
            
        except Exception as e:
            print(f"✗ API Error: {e}")
            print("\n⚠️ API key may be invalid or API quota exceeded")
            
    except ImportError:
        print("✗ OpenAI package not installed")
        print("Run: pip install openai")
else:
    print("✗ OPENAI_API_KEY not found")
    print("\nTo configure:")
    print("1. Create a .env file in AI_support folder with:")
    print("   OPENAI_API_KEY=sk-your-key-here")
    print("\n2. Or set in PowerShell before running:")
    print("   $env:OPENAI_API_KEY = 'sk-your-key-here'")
    print("\nGet your key from: https://platform.openai.com/api-keys")

print("=" * 60)

# Now test the JobAnalyzer
print("\nTesting JobAnalyzer...")
try:
    from job_analyzer import JobAnalyzer
    analyzer = JobAnalyzer()
    
    # Test location extraction
    test_post = {
        'title': 'Java Developer - Bangalore',
        'description': 'We are hiring a Java Developer in Bangalore. Location: Bangalore, Karnataka'
    }
    
    result = analyzer._extract_location(test_post)
    print(f"Test extraction result: {result}")
    
except Exception as e:
    print(f"Error testing JobAnalyzer: {e}")
    import traceback
    traceback.print_exc()
