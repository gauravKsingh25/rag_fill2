#!/usr/bin/env python3

from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Check if Google API key is loaded
google_api_key = os.getenv("GOOGLE_API_KEY")
gemini_api_key = os.getenv("GEMINI_API_KEY")

print("Environment variable test:")
print(f"GOOGLE_API_KEY loaded: {bool(google_api_key)}")
if google_api_key:
    print(f"GOOGLE_API_KEY starts with: {google_api_key[:10]}...")
    print(f"GOOGLE_API_KEY length: {len(google_api_key)}")

print(f"GEMINI_API_KEY loaded: {bool(gemini_api_key)}")

# Test importing gemini service
try:
    from app.services.gemini_service import gemini_service
    print(f"GeminiService available: {gemini_service.available}")
    print(f"GeminiService API key loaded: {bool(gemini_service.api_key)}")
    if gemini_service.api_key:
        print(f"GeminiService API key starts with: {gemini_service.api_key[:10]}...")
except Exception as e:
    print(f"Error importing gemini_service: {e}")
