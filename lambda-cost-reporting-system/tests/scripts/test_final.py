#!/usr/bin/env python3
import requests

# Test without token first
print("🔍 FINAL BACKEND VALIDATION")
print("=" * 40)

# Test 1: Health endpoint (should work without auth)
print("1. Testing health endpoint (no auth)...")
try:
    response = requests.get("https://api-costhub.4bfast.com.br/health", timeout=10)
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.text[:100]}")
except Exception as e:
    print(f"   Error: {e}")

# Test 2: API endpoint without auth (should return 401)
print("\n2. Testing API endpoint without auth...")
try:
    response = requests.get("https://api-costhub.4bfast.com.br/api/v1/accounts", timeout=10)
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.text[:100]}")
except Exception as e:
    print(f"   Error: {e}")

print("\n📋 ANALYSIS:")
print("- Health endpoint should return 200 (no auth required)")
print("- API endpoints should return 401 (auth required)")
print("- If both return 401, Cognito is working but needs valid token")
print("- If health returns 200, infrastructure is working correctly")
