#!/usr/bin/env python3
"""
Test Frontend Authentication Flow
Verifies how the frontend is handling auth
"""

import requests
import json

def test_frontend_endpoints():
    """Test frontend and API endpoints"""
    
    print("🌐 FRONTEND & API CONNECTIVITY TEST")
    print("=" * 50)
    
    # Test frontend
    print("1. Testing frontend...")
    try:
        response = requests.get("https://costhub.4bfast.com.br", timeout=10)
        print(f"   Frontend: {response.status_code} ✅")
    except Exception as e:
        print(f"   Frontend: Error ❌ - {e}")
    
    # Test API Gateway
    print("2. Testing API Gateway...")
    try:
        response = requests.get("https://api-costhub.4bfast.com.br", timeout=10)
        print(f"   API Gateway: {response.status_code}")
    except Exception as e:
        print(f"   API Gateway: Error ❌ - {e}")
    
    # Test API endpoints without auth
    print("3. Testing API endpoints (no auth)...")
    endpoints = [
        "/api/v1/health",
        "/api/v1/status", 
        "/api/v1/accounts",
        "/api/v1/auth/login"
    ]
    
    for endpoint in endpoints:
        try:
            url = f"https://api-costhub.4bfast.com.br{endpoint}"
            response = requests.get(url, timeout=5)
            print(f"   {endpoint}: {response.status_code}")
        except Exception as e:
            print(f"   {endpoint}: Error - {str(e)[:50]}")
    
    print("\n📋 ANALYSIS:")
    print("- If all endpoints return 401: Cognito is working, need auth")
    print("- If some return 404: Endpoints not implemented")
    print("- If some return 501: Endpoints implemented but not functional")
    
    print(f"\n🔑 TO TEST WITH AUTH:")
    print(f"1. Login at https://costhub.4bfast.com.br")
    print(f"2. Use browser DevTools to get JWT token")
    print(f"3. Test endpoints with Authorization header")

if __name__ == "__main__":
    test_frontend_endpoints()
