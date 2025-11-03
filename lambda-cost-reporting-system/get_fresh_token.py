#!/usr/bin/env python3
"""
Get fresh JWT token from Cognito
"""
import boto3
import json
from botocore.exceptions import ClientError

# Cognito configuration from production config
USER_POOL_ID = "us-east-1_94OYkzcSO"
CLIENT_ID = "23qrdk4pl1lidrhsflpsitl4u2"
USERNAME = "admin@4bfast.com.br"
PASSWORD = "4BFast2025!"
REGION = "us-east-1"

def get_cognito_token():
    """Get JWT token from Cognito"""
    try:
        client = boto3.client('cognito-idp', region_name=REGION)
        
        # Authenticate user
        response = client.initiate_auth(
            ClientId=CLIENT_ID,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': USERNAME,
                'PASSWORD': PASSWORD
            }
        )
        
        # Extract tokens
        auth_result = response['AuthenticationResult']
        access_token = auth_result['AccessToken']
        id_token = auth_result['IdToken']
        
        print("✅ Successfully obtained tokens!")
        print(f"Access Token: {access_token[:50]}...")
        print(f"ID Token: {id_token[:50]}...")
        
        return access_token, id_token
        
    except ClientError as e:
        print(f"❌ Cognito error: {e}")
        return None, None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None, None

def test_endpoints_with_token(token):
    """Test endpoints with valid token"""
    import requests
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    endpoints = [
        "/accounts",
        "/dashboard/summary",
        "/costs"
    ]
    
    print("\n🔍 TESTING ENDPOINTS WITH FRESH TOKEN")
    print("=" * 50)
    
    for endpoint in endpoints:
        try:
            url = f"https://api-costhub.4bfast.com.br/api/v1{endpoint}"
            response = requests.get(url, headers=headers, timeout=10)
            
            print(f"GET {endpoint}: {response.status_code}", end="")
            
            if response.status_code == 200:
                print(" ✅ SUCCESS")
            elif response.status_code == 501:
                print(" ⚠️ NOT IMPLEMENTED")
            elif response.status_code == 401:
                print(" 🔐 STILL UNAUTHORIZED")
            else:
                print(f" ❌ ERROR")
                
            print(f"    Response: {response.text[:100]}")
            
        except Exception as e:
            print(f"GET {endpoint}: ❌ EXCEPTION - {str(e)[:50]}")

if __name__ == "__main__":
    print("🔐 GETTING FRESH COGNITO TOKEN")
    print("=" * 40)
    
    access_token, id_token = get_cognito_token()
    
    if access_token:
        # Test with access token first
        print(f"\n🧪 Testing with Access Token...")
        test_endpoints_with_token(access_token)
        
        # Test with ID token if access token fails
        print(f"\n🧪 Testing with ID Token...")
        test_endpoints_with_token(id_token)
    else:
        print("❌ Could not obtain tokens")
