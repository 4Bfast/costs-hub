#!/usr/bin/env python3
"""
Backend Validation Script - No Auth Version
Tests endpoints directly without Cognito authentication
"""

import requests
import json
from typing import Dict, List, Tuple

# Test directly against Lambda function URL (if available) or bypass auth
API_BASE = "https://api-costhub.4bfast.com.br/api/v1"
HEADERS = {
    "Content-Type": "application/json",
    "Origin": "https://costhub.4bfast.com.br",
    # Add a test authorization header to bypass Cognito for testing
    "Authorization": "Bearer test-token-for-validation"
}

def test_endpoint(method: str, endpoint: str, data: Dict = None) -> Tuple[int, str]:
    """Test a single endpoint"""
    try:
        url = f"{API_BASE}{endpoint}"
        
        if method == "GET":
            response = requests.get(url, headers=HEADERS, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, headers=HEADERS, timeout=10)
        elif method == "PUT":
            response = requests.put(url, json=data, headers=HEADERS, timeout=10)
        elif method == "DELETE":
            response = requests.delete(url, headers=HEADERS, timeout=10)
        else:
            return 0, "Invalid method"
            
        return response.status_code, response.text[:200]
        
    except requests.exceptions.RequestException as e:
        return 0, str(e)[:200]

def main():
    """Test core endpoints that should work"""
    
    print("🔍 BACKEND VALIDATION - Core Endpoints (No Auth)")
    print("=" * 60)
    
    # Focus on core endpoints that should be implemented
    endpoints = [
        # Health checks (should work without auth)
        ("GET", "/health", None),
        ("GET", "/status", None),
        
        # Accounts (implemented according to summary)
        ("GET", "/accounts", None),
        ("POST", "/accounts", {"name": "Test Account", "provider_type": "aws"}),
        
        # Core functionality tests
        ("GET", "/dashboard/summary", None),
        ("GET", "/costs", None),
        ("GET", "/alarms", None),
        ("GET", "/insights", None),
        ("GET", "/users", None),
    ]
    
    results = {
        "✅ WORKING": [],
        "⚠️ NOT_IMPLEMENTED": [],
        "❌ ERROR": [],
        "🔐 AUTH_REQUIRED": []
    }
    
    print(f"Testing {len(endpoints)} core endpoints...")
    
    for i, (method, endpoint, data) in enumerate(endpoints, 1):
        print(f"[{i:2d}/{len(endpoints)}] {method} {endpoint}", end=" ... ")
        
        status, response = test_endpoint(method, endpoint, data)
        endpoint_desc = f"{method} {endpoint}"
        
        if status == 200 or status == 201:
            results["✅ WORKING"].append(endpoint_desc)
            print("✅ OK")
        elif status == 501:
            results["⚠️ NOT_IMPLEMENTED"].append(endpoint_desc)
            print("⚠️ 501")
        elif status == 401 or status == 403:
            results["🔐 AUTH_REQUIRED"].append(endpoint_desc)
            print("🔐 AUTH")
        else:
            results["❌ ERROR"].append(f"{endpoint_desc} ({status})")
            print(f"❌ {status}")
    
    # Print results
    print("\n" + "=" * 60)
    for category, endpoints in results.items():
        print(f"\n{category} ({len(endpoints)} endpoints):")
        for endpoint in endpoints:
            print(f"  • {endpoint}")
    
    # Analysis
    total = sum(len(endpoints) for endpoints in results.values())
    working = len(results["✅ WORKING"])
    not_implemented = len(results["⚠️ NOT_IMPLEMENTED"])
    auth_required = len(results["🔐 AUTH_REQUIRED"])
    
    print(f"\n📊 CORE ENDPOINT STATUS:")
    print(f"Total Tested: {total}")
    print(f"✅ Working: {working}")
    print(f"⚠️ Not Implemented: {not_implemented}")
    print(f"🔐 Auth Required: {auth_required}")
    
    if auth_required == total:
        print(f"\n⚠️ ALL ENDPOINTS REQUIRE AUTHENTICATION")
        print(f"This means Cognito is properly configured but we need:")
        print(f"1. Valid JWT token for testing")
        print(f"2. Health endpoints that bypass auth")
        print(f"3. Test endpoints for validation")

if __name__ == "__main__":
    main()
