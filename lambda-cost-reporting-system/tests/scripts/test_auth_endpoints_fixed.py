#!/usr/bin/env python3
"""
Test auth endpoints with correct tokens
"""
import boto3
import requests
import json

def get_tokens():
    client = boto3.client('cognito-idp', region_name='us-east-1')
    response = client.initiate_auth(
        ClientId="23qrdk4pl1lidrhsflpsitl4u2",
        AuthFlow='USER_PASSWORD_AUTH',
        AuthParameters={
            'USERNAME': "admin@4bfast.com.br",
            'PASSWORD': "4BFast2025!"
        }
    )
    return {
        'access_token': response['AuthenticationResult']['AccessToken'],
        'id_token': response['AuthenticationResult']['IdToken'],
        'refresh_token': response['AuthenticationResult']['RefreshToken']
    }

def test_auth_endpoints():
    print("🔍 TESTING AUTH ENDPOINTS WITH CORRECT TOKENS")
    print("=" * 50)
    
    tokens = get_tokens()
    base_url = "https://api-costhub.4bfast.com.br/api/v1"
    
    # Test 1: POST /auth/login (should work without token)
    print("1. Testing POST /auth/login...")
    response = requests.post(f"{base_url}/auth/login", 
                           json={"username": "admin@4bfast.com.br", "password": "4BFast2025!"})
    print(f"   Status: {response.status_code} {'✅' if response.status_code == 200 else '❌'}")
    
    # Test 2: GET /auth/me (needs Access Token)
    print("2. Testing GET /auth/me with Access Token...")
    response = requests.get(f"{base_url}/auth/me", 
                          headers={"Authorization": f"Bearer {tokens['access_token']}"})
    print(f"   Status: {response.status_code} {'✅' if response.status_code == 200 else '❌'}")
    if response.status_code == 200:
        print(f"   User: {response.json().get('attributes', {}).get('email', 'N/A')}")
    
    # Test 3: POST /auth/refresh (needs Refresh Token)
    print("3. Testing POST /auth/refresh...")
    response = requests.post(f"{base_url}/auth/refresh", 
                           json={"refresh_token": tokens['refresh_token']})
    print(f"   Status: {response.status_code} {'✅' if response.status_code == 200 else '❌'}")
    
    # Test 4: POST /auth/logout (needs Access Token)
    print("4. Testing POST /auth/logout with Access Token...")
    response = requests.post(f"{base_url}/auth/logout", 
                           json={"access_token": tokens['access_token']})
    print(f"   Status: {response.status_code} {'✅' if response.status_code == 200 else '❌'}")
    
    # Test 5: POST /auth/register (should work without token, but user might exist)
    print("5. Testing POST /auth/register...")
    import time
    unique_email = f"testuser{int(time.time())}@test.com"
    response = requests.post(f"{base_url}/auth/register", 
                           json={"username": unique_email, "password": "TestPass123!", "email": unique_email})
    print(f"   Status: {response.status_code} {'✅' if response.status_code in [200, 201] else '❌'}")
    if response.status_code not in [200, 201]:
        print(f"   Error: {response.text}")

if __name__ == "__main__":
    test_auth_endpoints()
