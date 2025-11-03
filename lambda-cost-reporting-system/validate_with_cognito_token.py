#!/usr/bin/env python3
"""
Backend Validation with Cognito Token
Gets token directly from Cognito and tests endpoints
"""

import boto3
import requests
import json
from typing import Dict, Tuple

# Cognito configuration (you'll need to get these from AWS Console)
COGNITO_CLIENT_ID = "your-client-id"  # Get from Cognito User Pool
COGNITO_REGION = "us-east-1"  # Your Cognito region

# Test credentials
EMAIL = "admin@4bfast.com.br"
PASSWORD = "4BFast2025!"
API_BASE = "https://api-costhub.4bfast.com.br/api/v1"

def get_cognito_token() -> str:
    """Get JWT token directly from Cognito"""
    try:
        # Initialize Cognito client
        client = boto3.client('cognito-idp', region_name=COGNITO_REGION)
        
        # Authenticate with Cognito
        response = client.admin_initiate_auth(
            UserPoolId='your-user-pool-id',  # Get from AWS Console
            ClientId=COGNITO_CLIENT_ID,
            AuthFlow='ADMIN_NO_SRP_AUTH',
            AuthParameters={
                'USERNAME': EMAIL,
                'PASSWORD': PASSWORD
            }
        )
        
        return response['AuthenticationResult']['AccessToken']
        
    except Exception as e:
        print(f"❌ Cognito auth error: {e}")
        return ""

def test_with_manual_token():
    """Test with manually provided token"""
    print("🔐 MANUAL TOKEN TEST")
    print("=" * 40)
    print("Since we need Cognito configuration, let's test with a manual approach:")
    print()
    print("1. Go to https://costhub.4bfast.com.br")
    print("2. Login with admin@4bfast.com.br / 4BFast2025!")
    print("3. Open browser DevTools > Network tab")
    print("4. Make any API call and copy the Authorization header")
    print("5. Paste the token below:")
    print()
    
    token = input("Enter JWT token (or press Enter to skip): ").strip()
    
    if not token:
        print("❌ No token provided")
        return
    
    # Remove 'Bearer ' prefix if present
    if token.startswith('Bearer '):
        token = token[7:]
    
    # Test endpoints
    endpoints = [
        ("GET", "/accounts", None),
        ("GET", "/dashboard/summary", None),
        ("GET", "/costs", None),
    ]
    
    results = {"✅ WORKING": [], "⚠️ NOT_IMPLEMENTED": [], "❌ ERROR": []}
    
    for method, endpoint, data in endpoints:
        print(f"{method} {endpoint}", end=" ... ")
        
        try:
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(f"{API_BASE}{endpoint}", headers=headers, timeout=10)
            status = response.status_code
            
            if status == 200 or status == 201:
                results["✅ WORKING"].append(f"{method} {endpoint}")
                print("✅ OK")
            elif status == 501:
                results["⚠️ NOT_IMPLEMENTED"].append(f"{method} {endpoint}")
                print("⚠️ 501")
            else:
                results["❌ ERROR"].append(f"{method} {endpoint} ({status})")
                print(f"❌ {status}")
                
        except Exception as e:
            results["❌ ERROR"].append(f"{method} {endpoint} (error)")
            print(f"❌ Error")
    
    # Results
    print("\n" + "=" * 40)
    for category, endpoints in results.items():
        print(f"\n{category} ({len(endpoints)}):")
        for endpoint in endpoints:
            print(f"  • {endpoint}")

def main():
    print("🔍 COGNITO TOKEN VALIDATION")
    print("=" * 40)
    
    # Try automatic Cognito auth (requires configuration)
    print("Attempting automatic Cognito authentication...")
    token = get_cognito_token()
    
    if token:
        print("✅ Got Cognito token automatically")
        # Test with token here
    else:
        print("⚠️ Automatic auth failed, trying manual approach...")
        test_with_manual_token()

if __name__ == "__main__":
    main()
