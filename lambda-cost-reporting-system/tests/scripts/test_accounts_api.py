#!/usr/bin/env python3
"""
Test script for Accounts API with real DynamoDB persistence
"""

import requests
import json

# API endpoint
API_BASE = "https://api-costhub.4bfast.com.br/api/v1"

def test_create_account():
    """Test creating a new account"""
    print("🧪 Testing account creation...")
    
    account_data = {
        "name": "Test AWS Account",
        "provider_type": "aws",
        "credentials": {
            "access_key_id": "AKIA...",
            "secret_access_key": "***",
            "region": "us-east-1"
        }
    }
    
    response = requests.post(
        f"{API_BASE}/accounts",
        json=account_data,
        headers={
            "Content-Type": "application/json",
            "Origin": "https://costhub.4bfast.com.br"
        }
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    return response.json() if response.status_code == 201 else None

def test_get_accounts():
    """Test retrieving accounts"""
    print("\n🧪 Testing account retrieval...")
    
    response = requests.get(
        f"{API_BASE}/accounts",
        headers={
            "Origin": "https://costhub.4bfast.com.br"
        }
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

if __name__ == "__main__":
    print("🚀 Testing Accounts API with Real DynamoDB Persistence")
    print("=" * 60)
    
    # Test account creation
    created_account = test_create_account()
    
    # Test account retrieval
    test_get_accounts()
    
    print("\n✅ Tests completed!")
