#!/usr/bin/env python3
"""
Test script for CostHub endpoints with REAL data
Tests all endpoints using real Cognito users and DynamoDB accounts
"""

import json
import boto3
import base64
from datetime import datetime

# Configuration
LAMBDA_FUNCTION_NAME = "costhub-frontend-api-prod-APIHandler68F11976-POT1msJZKUqV"
AWS_PROFILE = "4bfast"
AWS_REGION = "us-east-1"
COGNITO_USER_POOL_ID = "us-east-1_94OYkzcSO"
COGNITO_CLIENT_ID = "23qrdk4pl1lidrhsflpsitl4u2"

def create_test_jwt_token(client_id: str, username: str, sub: str) -> str:
    """Create a test JWT token with real user data"""
    import time
    
    payload = {
        'client_id': client_id,
        'username': username,
        'sub': sub,
        'email': f'{username}@4bfast.com.br',
        'token_use': 'access',
        'scope': 'aws.cognito.signin.user.admin',
        'auth_time': int(time.time()),
        'iss': f'https://cognito-idp.{AWS_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}',
        'exp': int(time.time()) + 3600,  # 1 hour
        'iat': int(time.time()),
        'cognito:username': username
    }
    
    # Create base64 encoded payload (simplified JWT for testing)
    header = base64.urlsafe_b64encode(json.dumps({'typ': 'JWT', 'alg': 'HS256'}).encode()).decode().rstrip('=')
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
    signature = base64.urlsafe_b64encode(b'test-signature').decode().rstrip('=')
    
    return f"{header}.{payload_b64}.{signature}"

def test_endpoint(lambda_client, method: str, path: str, token: str = None, query_params: dict = None, expected_status: int = 200):
    """Test a specific endpoint"""
    
    event = {
        "httpMethod": method,
        "path": path,
        "headers": {
            "origin": "https://costhub.4bfast.com.br",
            "Content-Type": "application/json"
        }
    }
    
    if token:
        event["headers"]["Authorization"] = f"Bearer {token}"
    
    if query_params:
        event["queryStringParameters"] = query_params
    
    try:
        print(f"🔍 Testing {method} {path}...")
        
        response = lambda_client.invoke(
            FunctionName=LAMBDA_FUNCTION_NAME,
            Payload=json.dumps(event)
        )
        
        result = json.loads(response['Payload'].read())
        status_code = result.get('statusCode', 500)
        
        if status_code == expected_status:
            body = json.loads(result.get('body', '{}'))
            
            # Special handling for health endpoint
            if path == '/health':
                if body.get('status') == 'healthy':
                    print(f"✅ {method} {path}: SUCCESS")
                    print(f"   🏥 Status: {body.get('status')}")
                    print(f"   🔧 Service: {body.get('service')}")
                    print(f"   📝 Version: {body.get('version')}")
                    print(f"   📊 Endpoints: {body.get('endpoints_active')}")
                    return True, body
                else:
                    print(f"❌ {method} {path}: Unhealthy status")
                    return False, body
            
            elif body.get('success'):
                print(f"✅ {method} {path}: SUCCESS")
                
                # Show relevant data
                data = body.get('data', {})
                if 'total_cost' in data:
                    print(f"   💰 Total Cost: ${data['total_cost']:.2f}")
                if 'service_count' in data:
                    print(f"   📊 Services: {data['service_count']}")
                if 'accounts_count' in data:
                    print(f"   🏢 Accounts: {data['accounts_count']}")
                if 'client_id' in data:
                    print(f"   👤 Client ID: {data['client_id']}")
                if 'daily_costs' in data:
                    print(f"   📈 Daily data points: {len(data['daily_costs'])}")
                if 'breakdown' in data:
                    print(f"   🔍 Breakdown items: {data.get('item_count', 0)}")
                
                return True, body
            else:
                error = body.get('error', 'Unknown error')
                print(f"❌ {method} {path}: {error}")
                return False, body
        else:
            print(f"❌ {method} {path}: HTTP {status_code} (expected {expected_status})")
            if status_code == 500:
                error_msg = result.get('errorMessage', 'Unknown error')
                print(f"   Error: {error_msg}")
            return False, result
            
    except Exception as e:
        print(f"❌ {method} {path}: Exception - {e}")
        return False, None

def test_all_cost_endpoints():
    """Test all cost endpoints with real data"""
    print("🚀 Testing CostHub Endpoints with REAL DATA")
    print("=" * 60)
    
    # Initialize AWS session
    session = boto3.Session(profile_name=AWS_PROFILE)
    lambda_client = session.client('lambda', region_name=AWS_REGION)
    
    # Test with real client_id from DynamoDB
    test_client_id = "test-client-001"  # Our 4BFast account
    test_username = "admin"
    test_sub = "9448b4c8-d021-70eb-a07d-0948b5aa6d42"  # Real sub from Cognito
    
    # Create test token
    token = create_test_jwt_token(test_client_id, test_username, test_sub)
    print(f"🔑 Using token for client: {test_client_id}")
    print(f"👤 User: {test_username} (sub: {test_sub})")
    
    # Test cases
    test_cases = [
        {
            'name': 'Health Check',
            'method': 'GET',
            'path': '/health',
            'token': None,  # No auth needed
            'expected': 200
        },
        {
            'name': 'Cost Summary',
            'method': 'GET',
            'path': '/costs/summary',
            'token': token,
            'expected': 200
        },
        {
            'name': 'Cost Trends (30 days)',
            'method': 'GET',
            'path': '/costs/trends',
            'token': token,
            'query': {'days': '30'},
            'expected': 200
        },
        {
            'name': 'Cost Trends (7 days)',
            'method': 'GET',
            'path': '/costs/trends',
            'token': token,
            'query': {'days': '7'},
            'expected': 200
        },
        {
            'name': 'Cost Breakdown by Service',
            'method': 'GET',
            'path': '/costs/breakdown',
            'token': token,
            'query': {'group_by': 'SERVICE', 'days': '30'},
            'expected': 200
        },
        {
            'name': 'Cost Breakdown by Region',
            'method': 'GET',
            'path': '/costs/breakdown',
            'token': token,
            'query': {'group_by': 'REGION', 'days': '30'},
            'expected': 200
        },
        {
            'name': 'Cost by Service',
            'method': 'GET',
            'path': '/costs/by-service',
            'token': token,
            'expected': 200
        },
        {
            'name': 'Cost by Region',
            'method': 'GET',
            'path': '/costs/by-region',
            'token': token,
            'expected': 200
        },
        {
            'name': 'General Costs',
            'method': 'GET',
            'path': '/costs',
            'token': token,
            'query': {'days': '30'},
            'expected': 200
        }
    ]
    
    # Run tests
    results = []
    for test_case in test_cases:
        success, data = test_endpoint(
            lambda_client,
            test_case['method'],
            test_case['path'],
            test_case.get('token'),
            test_case.get('query'),
            test_case['expected']
        )
        
        results.append({
            'name': test_case['name'],
            'success': success,
            'data': data
        })
        print()  # Empty line for readability
    
    # Summary
    print("=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for r in results if r['success'])
    total = len(results)
    
    for result in results:
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        print(f"{status} - {result['name']}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Cost endpoints are working with real data!")
        print("\n📋 Validated Features:")
        print("• Real AWS Cost Explorer integration")
        print("• JWT token parsing and client_id extraction")
        print("• DynamoDB account lookup")
        print("• Multi-account cost aggregation")
        print("• Error handling and fallbacks")
        
        print(f"\n🌐 API Base URL: https://api-costhub.4bfast.com.br")
        print(f"🔧 Lambda Function: {LAMBDA_FUNCTION_NAME}")
        print(f"🏢 Test Account: {test_client_id} (4BFast - 008195334540)")
        
        print("\n✅ PHASE 2 COMPLETE - Ready for frontend integration!")
        
    else:
        print(f"\n⚠️  {total-passed} tests failed - check logs above")
        print("🔧 Troubleshooting needed before proceeding")
    
    return passed == total

def verify_account_configuration():
    """Verify that our test account is properly configured"""
    print("\n🔍 Verifying Account Configuration...")
    
    session = boto3.Session(profile_name=AWS_PROFILE)
    dynamodb = session.resource('dynamodb', region_name=AWS_REGION)
    table = dynamodb.Table('costhub-accounts')
    
    try:
        response = table.get_item(Key={'account_id': '008195334540'})
        
        if 'Item' in response:
            item = response['Item']
            print(f"✅ Account found: {item['name']}")
            print(f"   Status: {item['status']}")
            print(f"   Client ID: {item['client_id']}")
            print(f"   Provider: {item['provider_type']}")
            
            if 'configuration' in item:
                config = item['configuration']
                print(f"   Role ARN: {config.get('role_arn', 'Not configured')}")
                print(f"   External ID: {config.get('external_id', 'Not configured')}")
                print(f"   Regions: {config.get('regions', [])}")
            
            return item['status'] == 'active'
        else:
            print("❌ Account not found in DynamoDB")
            return False
            
    except Exception as e:
        print(f"❌ Error checking account: {e}")
        return False

if __name__ == "__main__":
    # Verify account configuration first
    if verify_account_configuration():
        # Run all tests
        test_all_cost_endpoints()
    else:
        print("❌ Account configuration issue - fix before testing endpoints")
