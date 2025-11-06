#!/usr/bin/env python3
"""
Test Accounts Endpoints - Real API Testing
"""

import requests
import json
import sys

# API Configuration
API_BASE_URL = "https://api-costhub.4bfast.com.br/api/v1"

def get_auth_token():
    """Get authentication token"""
    login_data = {
        "email": "test@4bfast.com.br",
        "password": "TempPassword123!"
    }
    
    response = requests.post(f"{API_BASE_URL}/auth/login", json=login_data)
    if response.status_code == 200:
        tokens = response.json()['tokens']
        return tokens['IdToken']
    else:
        print(f"❌ Login failed: {response.status_code} - {response.text}")
        return None

def test_accounts_endpoints():
    """Test all accounts endpoints"""
    
    # Get auth token
    token = get_auth_token()
    if not token:
        return
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    print("🧪 Testing Accounts Endpoints...")
    print("=" * 50)
    
    # Test 1: GET /accounts (list all accounts)
    print("\n1️⃣ Testing GET /accounts")
    response = requests.get(f"{API_BASE_URL}/accounts", headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success: Found {data.get('data', {}).get('count', 0)} accounts")
        print(f"Response: {json.dumps(data, indent=2)}")
    else:
        print(f"❌ Failed: {response.text}")
    
    # Test 2: POST /accounts (create new account)
    print("\n2️⃣ Testing POST /accounts")
    new_account = {
        "name": "Test AWS Account",
        "provider_type": "aws",
        "status": "active",
        "credentials": {
            "access_key": "AKIA...",
            "secret_key": "***",
            "region": "us-east-1"
        }
    }
    
    response = requests.post(f"{API_BASE_URL}/accounts", json=new_account, headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 201:
        data = response.json()
        account_id = data['data']['account_id']
        print(f"✅ Success: Created account {account_id}")
        print(f"Response: {json.dumps(data, indent=2)}")
        
        # Test 3: PUT /accounts/{id} (update account)
        print(f"\n3️⃣ Testing PUT /accounts/{account_id}")
        update_data = {
            "name": "Updated Test AWS Account",
            "status": "inactive"
        }
        
        response = requests.put(f"{API_BASE_URL}/accounts/{account_id}", json=update_data, headers=headers)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success: Updated account {account_id}")
            print(f"Response: {json.dumps(data, indent=2)}")
        else:
            print(f"❌ Failed: {response.text}")
        
        # Test 4: DELETE /accounts/{id} (delete account)
        print(f"\n4️⃣ Testing DELETE /accounts/{account_id}")
        response = requests.delete(f"{API_BASE_URL}/accounts/{account_id}", headers=headers)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success: Deleted account {account_id}")
            print(f"Response: {json.dumps(data, indent=2)}")
        else:
            print(f"❌ Failed: {response.text}")
            
    else:
        print(f"❌ Failed to create account: {response.text}")
    
    print("\n" + "=" * 50)
    print("🎯 Accounts endpoints testing completed!")

if __name__ == "__main__":
    test_accounts_endpoints()
