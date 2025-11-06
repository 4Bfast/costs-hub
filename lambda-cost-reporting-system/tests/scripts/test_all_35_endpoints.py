#!/usr/bin/env python3
"""
Test all 35 endpoints with valid Cognito ID token
"""
import boto3
import requests
import json

# Get fresh ID token
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
        'id_token': response['AuthenticationResult']['IdToken'],
        'access_token': response['AuthenticationResult']['AccessToken'],
        'refresh_token': response['AuthenticationResult']['RefreshToken']
    }

def test_endpoint(method, endpoint, tokens, data=None):
    # Use Access Token for /auth/me and /auth/logout, ID Token for everything else
    if endpoint in ['/auth/me', '/auth/logout']:
        token = tokens['access_token']
    else:
        token = tokens['id_token']
        
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    url = f"https://api-costhub.4bfast.com.br/api/v1{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, headers=headers, timeout=10)
        elif method == "PUT":
            response = requests.put(url, json=data, headers=headers, timeout=10)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, timeout=10)
        
        return response.status_code, response.text[:150]
    except Exception as e:
        return 0, str(e)[:150]

def main():
    print("🔍 TESTING ALL 35 ENDPOINTS WITH VALID TOKEN")
    print("=" * 60)
    
    # Get fresh tokens
    tokens = get_tokens()
    print("✅ Got fresh tokens")
    
    # All 35 endpoints
    endpoints = [
        # Authentication
        ("POST", "/auth/login", {"username": "admin@4bfast.com.br", "password": "4BFast2025!"}),
        ("POST", "/auth/register", {"username": "test@test.com", "password": "test123", "email": "test@test.com"}),
        ("POST", "/auth/logout", {"access_token": tokens['access_token']}),
        ("GET", "/auth/me", None),
        ("POST", "/auth/refresh", {"refresh_token": tokens['refresh_token']}),
        
        # Dashboard
        ("GET", "/dashboard/summary", None),
        ("GET", "/dashboard/cost-trends", None),
        ("GET", "/dashboard", None),
        ("GET", "/dashboard/overview", None),
        
        # Costs
        ("GET", "/costs", None),
        ("GET", "/costs/summary", None),
        ("GET", "/costs/trends", None),
        ("GET", "/costs/breakdown", None),
        ("GET", "/costs/by-service", None),
        ("GET", "/costs/by-region", None),
        
        # Accounts
        ("GET", "/accounts", None),
        ("POST", "/accounts", {"name": "Test Account", "provider_type": "aws"}),
        ("PUT", "/accounts/test-id", {"name": "Updated Account"}),
        ("DELETE", "/accounts/test-id", None),
        
        # Alarms
        ("GET", "/alarms", None),
        ("POST", "/alarms", {"name": "Test Alarm", "threshold": 100}),
        ("PUT", "/alarms/test-id", {"threshold": 200}),
        ("DELETE", "/alarms/test-id", None),
        
        # Insights
        ("GET", "/insights", None),
        ("GET", "/insights/recommendations", None),
        ("POST", "/insights/generate", {}),
        
        # Users
        ("GET", "/users", None),
        ("GET", "/users/profile", None),
        ("PUT", "/users/profile", {"name": "Updated Name"}),
        
        # Organizations
        ("GET", "/organizations", None),
        ("POST", "/organizations", {"name": "Test Org"}),
        
        # Reports
        ("GET", "/reports", None),
        ("POST", "/reports/generate", {"type": "cost", "period": "monthly"}),
        
        # Health & System
        ("GET", "/health", None),
        ("GET", "/status", None),
    ]
    
    results = {
        "✅ WORKING": [],
        "⚠️ NOT_IMPLEMENTED": [],
        "❌ ERROR": [],
        "🔌 NOT_FOUND": []
    }
    
    print(f"\nTesting {len(endpoints)} endpoints...\n")
    
    for i, (method, endpoint, data) in enumerate(endpoints, 1):
        print(f"[{i:2d}/35] {method} {endpoint}", end=" ... ")
        
        status, response = test_endpoint(method, endpoint, tokens, data)
        endpoint_desc = f"{method} {endpoint}"
        
        if status == 200 or status == 201:
            results["✅ WORKING"].append(endpoint_desc)
            print("✅ WORKING")
        elif status == 501:
            results["⚠️ NOT_IMPLEMENTED"].append(endpoint_desc)
            print("⚠️ NOT_IMPLEMENTED")
        elif status == 404 or status == 405:
            results["🔌 NOT_FOUND"].append(endpoint_desc)
            print("🔌 NOT_FOUND")
        else:
            results["❌ ERROR"].append(f"{endpoint_desc} ({status})")
            print(f"❌ ERROR ({status})")
    
    # Summary
    print("\n" + "=" * 60)
    for category, endpoints in results.items():
        print(f"\n{category} ({len(endpoints)} endpoints):")
        for endpoint in endpoints:
            print(f"  • {endpoint}")
    
    total = 35  # Fixed total count
    working = len(results["✅ WORKING"])
    not_implemented = len(results["⚠️ NOT_IMPLEMENTED"])
    
    print(f"\n📊 FINAL RESULTS:")
    print(f"Total Endpoints: {total}")
    print(f"✅ Working: {working} ({working/total*100:.1f}%)")
    print(f"⚠️ Not Implemented: {not_implemented} ({not_implemented/total*100:.1f}%)")
    print(f"❌ Issues: {total-working-not_implemented} ({(total-working-not_implemented)/total*100:.1f}%)")

if __name__ == "__main__":
    main()
