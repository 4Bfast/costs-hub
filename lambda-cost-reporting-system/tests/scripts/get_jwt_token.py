#!/usr/bin/env python3
"""
Get JWT Token from Login Endpoint
"""

import requests
import json

def get_jwt_token():
    """Get JWT token from login endpoint"""
    
    login_url = "https://api-costhub.4bfast.com.br/api/v1/auth/login"
    
    credentials = {
        "email": "admin@4bfast.com.br",
        "password": "4BFast2025!"
    }
    
    headers = {
        "Content-Type": "application/json",
        "Origin": "https://costhub.4bfast.com.br"
    }
    
    print("🔐 Attempting login...")
    print(f"URL: {login_url}")
    print(f"Email: {credentials['email']}")
    
    try:
        response = requests.post(login_url, json=credentials, headers=headers, timeout=10)
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            token = data.get('token') or data.get('access_token') or data.get('accessToken')
            if token:
                print(f"✅ Token obtained: {token[:50]}...")
                return token
            else:
                print("❌ No token in response")
                print(f"Response keys: {list(data.keys())}")
        
        return None
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    token = get_jwt_token()
    if token:
        print(f"\n🎯 Use this token for testing:")
        print(f"Authorization: Bearer {token}")
    else:
        print(f"\n❌ Could not obtain token")
