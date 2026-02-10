#!/usr/bin/env python
"""
Simple Gemini API Test Script
Run: python test_gemini.py
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'investigator.settings')
django.setup()

from django.conf import settings
import google.generativeai as genai

print("=" * 60)
print("GEMINI API TEST")
print("=" * 60)

# Check API key
print(f"\n1. API Key Check:")
print(f"   - Set: {'✅ YES' if settings.GEMINI_API_KEY else '❌ NO'}")
if settings.GEMINI_API_KEY:
    print(f"   - First 10 chars: {settings.GEMINI_API_KEY[:10]}")
    print(f"   - Length: {len(settings.GEMINI_API_KEY)} chars")
else:
    print("   ❌ GEMINI_API_KEY not set in environment!")
    sys.exit(1)

# Check model
print(f"\n2. Model Configuration:")
print(f"   - Model: {settings.GEMINI_MODEL_DEFAULT}")

# Configure Gemini
print(f"\n3. Configuring Gemini...")
try:
    genai.configure(api_key=settings.GEMINI_API_KEY)
    print("   ✅ API configured successfully")
except Exception as e:
    print(f"   ❌ Configuration failed: {e}")
    sys.exit(1)

# Test with simple prompt
print(f"\n4. Testing API call...")
print(f"   Prompt: 'Hi, how are you?'")
print(f"   Timeout: 10 seconds")

try:
    model = genai.GenerativeModel(settings.GEMINI_MODEL_DEFAULT)
    print(f"   ✅ Model loaded: {settings.GEMINI_MODEL_DEFAULT}")
    
    print(f"\n   📤 Sending request...")
    response = model.generate_content(
        "Hi, how are you?",
        request_options={'timeout': 10}
    )
    
    print(f"   ✅ Got response!")
    print(f"\n" + "=" * 60)
    print("RESPONSE:")
    print("=" * 60)
    print(response.text)
    print("=" * 60)
    
    print(f"\n✅ SUCCESS! Gemini API is working!")
    
except Exception as e:
    print(f"\n   ❌ API call failed!")
    print(f"   Error: {e}")
    print(f"\n   This could mean:")
    print(f"   - Invalid API key")
    print(f"   - Model '{settings.GEMINI_MODEL_DEFAULT}' doesn't exist")
    print(f"   - Network connectivity issue")
    print(f"   - API quota exceeded")
    
    print(f"\n   Try these models:")
    print(f"   - gemini-1.5-flash (fastest)")
    print(f"   - gemini-1.5-pro (slower but smarter)")
    print(f"   - gemini-2.0-flash-exp (experimental)")
    
    sys.exit(1)

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)