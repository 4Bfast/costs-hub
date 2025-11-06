#!/usr/bin/env python3
"""
Test newly implemented endpoints
"""
import boto3
import requests

def get_id_token():
    client = boto3.client('cognito-idp', region_name='us-east-1')
    response = client.initiate_auth(
        ClientId="23qrdk4pl1lidrhsflpsitl4u2",
        AuthFlow='USER_PASSWORD_AUTH',
        AuthParameters={
            'USERNAME': "admin@4bfast.com.br",
            'PASSWORD': "4BFast2025!"
        }
    )
    return response['AuthenticationResult']['IdToken']

def test_new_endpoints():
    print("🧪 TESTING NEWLY IMPLEMENTED ENDPOINTS")
    print("=" * 50)
    
    token = get_id_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    base_url = "https://api-costhub.4bfast.com.br/api/v1"
    
    # Test auth endpoints (these should work now)
    auth_tests = [
        ("POST", "/auth/login", {"email": "admin@4bfast.com.br", "password": "4BFast2025!"}),
        ("GET", "/auth/me", None),
    ]
    
    print("🔐 Testing Auth Endpoints:")
    for method, endpoint, data in auth_tests:
        try:
            url = f"{base_url}{endpoint}"
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=10)
            else:
                response = requests.post(url, json=data, headers=headers, timeout=10)
            
            print(f"  {method} {endpoint}: {response.status_code}", end="")
            if response.status_code in [200, 201]:
                print(" ✅")
            else:
                print(f" ❌ - {response.text[:100]}")
        except Exception as e:
            print(f"  {method} {endpoint}: ❌ Exception - {str(e)[:50]}")
    
    # Test account CRUD (create, then update, then delete)
    print("\n📁 Testing Account CRUD:")
    
    # Create account
    create_data = {"name": "Test Account", "provider_type": "aws"}
    response = requests.post(f"{base_url}/accounts", json=create_data, headers=headers)
    print(f"  POST /accounts: {response.status_code}", end="")
    
    if response.status_code == 201:
        print(" ✅")
        account_data = response.json()
        account_id = account_data.get('account', {}).get('account_id')
        
        if account_id:
            # Update account
            update_data = {"name": "Updated Test Account"}
            response = requests.put(f"{base_url}/accounts/{account_id}", json=update_data, headers=headers)
            print(f"  PUT /accounts/{account_id[:8]}...: {response.status_code}", end="")
            if response.status_code == 200:
                print(" ✅")
            else:
                print(f" ❌ - {response.text[:100]}")
            
            # Delete account
            response = requests.delete(f"{base_url}/accounts/{account_id}", headers=headers)
            print(f"  DELETE /accounts/{account_id[:8]}...: {response.status_code}", end="")
            if response.status_code == 200:
                print(" ✅")
            else:
                print(f" ❌ - {response.text[:100]}")
    else:
        print(f" ❌ - {response.text[:100]}")

if __name__ == "__main__":
    test_new_endpoints()
