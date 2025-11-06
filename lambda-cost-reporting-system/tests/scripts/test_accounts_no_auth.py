#!/usr/bin/env python3
"""
Test Accounts Endpoints - Without Authentication (to test handler)
"""

import requests
import json

# API Configuration
API_BASE_URL = "https://api-costhub.4bfast.com.br/api/v1"

def test_accounts_endpoints():
    """Test accounts endpoints without auth to see handler response"""
    
    print("🧪 Testing Accounts Endpoints (No Auth)...")
    print("=" * 50)
    
    # Test 1: GET /accounts (should return 401 but show handler is working)
    print("\n1️⃣ Testing GET /accounts")
    response = requests.get(f"{API_BASE_URL}/accounts")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    # Test 2: POST /accounts (should return 401 but show handler is working)
    print("\n2️⃣ Testing POST /accounts")
    new_account = {
        "name": "Test AWS Account",
        "provider_type": "aws"
    }
    
    response = requests.post(f"{API_BASE_URL}/accounts", json=new_account)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    print("\n" + "=" * 50)
    print("🎯 Basic accounts endpoints testing completed!")

if __name__ == "__main__":
    test_accounts_endpoints()
