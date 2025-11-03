#!/usr/bin/env python3
"""
Backend Validation with Real Authentication
Uses admin@4bfast.com.br credentials to test endpoints
"""

import requests
import json
from typing import Dict, Tuple

# Test credentials
EMAIL = "admin@4bfast.com.br"
PASSWORD = "4BFast2025!"
API_BASE = "https://api-costhub.4bfast.com.br/api/v1"

def get_auth_token() -> str:
    """Get JWT token from Cognito"""
    try:
        # Try to login and get token
        login_data = {"email": EMAIL, "password": PASSWORD}
        response = requests.post(f"{API_BASE}/auth/login", json=login_data)
        
        if response.status_code == 200:
            data = response.json()
            return data.get('token', '')
        else:
            print(f"❌ Login failed: {response.status_code}")
            return ""
    except Exception as e:
        print(f"❌ Auth error: {e}")
        return ""

def test_endpoint(method: str, endpoint: str, token: str, data: Dict = None) -> Tuple[int, str]:
    """Test endpoint with auth token"""
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "Origin": "https://costhub.4bfast.com.br"
        }
        
        url = f"{API_BASE}{endpoint}"
        
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, headers=headers, timeout=10)
        else:
            return 0, "Method not supported"
            
        return response.status_code, response.text[:200]
        
    except Exception as e:
        return 0, str(e)[:200]

def main():
    print("🔐 BACKEND VALIDATION - With Authentication")
    print("=" * 50)
    
    # Get auth token
    print("Getting auth token...", end=" ")
    token = get_auth_token()
    
    if not token:
        print("❌ Failed to get token")
        return
    
    print("✅ Token obtained")
    
    # Test core endpoints
    endpoints = [
        ("GET", "/accounts", None),
        ("POST", "/accounts", {"name": "Test Account", "provider_type": "aws"}),
        ("GET", "/dashboard/summary", None),
        ("GET", "/costs", None),
        ("GET", "/alarms", None),
        ("GET", "/insights", None),
    ]
    
    results = {"✅ WORKING": [], "⚠️ NOT_IMPLEMENTED": [], "❌ ERROR": []}
    
    for method, endpoint, data in endpoints:
        print(f"{method} {endpoint}", end=" ... ")
        
        status, response = test_endpoint(method, endpoint, token, data)
        endpoint_desc = f"{method} {endpoint}"
        
        if status == 200 or status == 201:
            results["✅ WORKING"].append(endpoint_desc)
            print("✅ OK")
        elif status == 501:
            results["⚠️ NOT_IMPLEMENTED"].append(endpoint_desc)
            print("⚠️ 501")
        else:
            results["❌ ERROR"].append(f"{endpoint_desc} ({status})")
            print(f"❌ {status}")
    
    # Results
    print("\n" + "=" * 50)
    for category, endpoints in results.items():
        print(f"\n{category} ({len(endpoints)}):")
        for endpoint in endpoints:
            print(f"  • {endpoint}")
    
    total = sum(len(endpoints) for endpoints in results.values())
    working = len(results["✅ WORKING"])
    
    print(f"\n📊 STATUS: {working}/{total} working ({working/total*100:.1f}%)")

if __name__ == "__main__":
    main()
