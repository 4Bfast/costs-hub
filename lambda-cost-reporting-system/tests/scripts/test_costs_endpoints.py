#!/usr/bin/env python3
"""
Test costs endpoints with real AWS Cost Explorer data
"""
import boto3
import requests
import json

def test_costs_endpoints():
    print("🔍 TESTING COSTS ENDPOINTS WITH REAL AWS DATA")
    print("=" * 50)
    
    # Get fresh token
    client = boto3.client('cognito-idp', region_name='us-east-1')
    response = client.initiate_auth(
        ClientId="23qrdk4pl1lidrhsflpsitl4u2",
        AuthFlow='USER_PASSWORD_AUTH',
        AuthParameters={'USERNAME': 'admin@4bfast.com.br', 'PASSWORD': '4BFast2025!'}
    )
    token = response['AuthenticationResult']['IdToken']
    
    base_url = "https://api-costhub.4bfast.com.br/api/v1"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    endpoints = [
        '/costs',
        '/costs/summary', 
        '/costs/trends',
        '/costs/breakdown',
        '/costs/by-service',
        '/costs/by-region'
    ]
    
    for endpoint in endpoints:
        print(f"Testing {endpoint}...")
        try:
            response = requests.get(f"{base_url}{endpoint}", headers=headers)
            print(f"  Status: {response.status_code} {'✅' if response.status_code == 200 else '❌'}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"  Message: {data.get('message', 'No message')}")
                if 'data' in data:
                    if 'totalCost' in data['data']:
                        print(f"  Total Cost: ${data['data']['totalCost']}")
                    if 'services' in data['data']:
                        print(f"  Services: {len(data['data']['services'])}")
                    if 'trends' in data['data']:
                        print(f"  Trend points: {len(data['data']['trends'])}")
            else:
                error_text = response.text[:150]
                print(f"  Error: {error_text}")
                
        except Exception as e:
            print(f"  Exception: {str(e)}")
        
        print()

if __name__ == "__main__":
    test_costs_endpoints()
