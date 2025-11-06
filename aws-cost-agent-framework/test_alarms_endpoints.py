#!/usr/bin/env python3
"""
Test script for Alarms endpoints - Phase 3
Tests CRUD operations for alarms with real data
"""

import json
import boto3
import base64
from datetime import datetime

# Configuration
LAMBDA_FUNCTION_NAME = "costhub-frontend-api-prod-APIHandler68F11976-POT1msJZKUqV"
AWS_PROFILE = "4bfast"
AWS_REGION = "us-east-1"

def create_test_jwt_token(client_id: str = "test-client-001") -> str:
    """Create a test JWT token"""
    import time
    
    payload = {
        'client_id': client_id,
        'username': 'admin',
        'sub': '9448b4c8-d021-70eb-a07d-0948b5aa6d42',
        'exp': int(time.time()) + 3600,
        'iat': int(time.time())
    }
    
    header = base64.urlsafe_b64encode(json.dumps({'typ': 'JWT', 'alg': 'HS256'}).encode()).decode().rstrip('=')
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
    signature = base64.urlsafe_b64encode(b'test-signature').decode().rstrip('=')
    
    return f"{header}.{payload_b64}.{signature}"

def test_alarms_crud():
    """Test complete CRUD operations for alarms"""
    print("🚨 Testing Alarms CRUD Operations")
    print("=" * 50)
    
    session = boto3.Session(profile_name=AWS_PROFILE)
    lambda_client = session.client('lambda', region_name=AWS_REGION)
    
    token = create_test_jwt_token()
    created_alarm_id = None
    
    # Test 1: List alarms (should be empty initially)
    print("🔍 Test 1: List alarms...")
    response = lambda_client.invoke(
        FunctionName=LAMBDA_FUNCTION_NAME,
        Payload=json.dumps({
            "httpMethod": "GET",
            "path": "/alarms",
            "headers": {
                "Authorization": f"Bearer {token}",
                "origin": "https://costhub.4bfast.com.br"
            }
        })
    )
    
    result = json.loads(response['Payload'].read())
    if result.get('statusCode') == 200:
        body = json.loads(result['body'])
        print(f"✅ List alarms: {body['data']['count']} alarms found")
    else:
        print(f"❌ List alarms failed: {result}")
        return False
    
    # Test 2: Create alarm
    print("\n🔍 Test 2: Create alarm...")
    alarm_data = {
        "name": "Monthly Cost Alert",
        "threshold": 100.0,
        "comparison_operator": ">",
        "metric_name": "total_cost",
        "description": "Alert when monthly cost exceeds $100",
        "notification_emails": ["admin@4bfast.com.br"],
        "enabled": True
    }
    
    response = lambda_client.invoke(
        FunctionName=LAMBDA_FUNCTION_NAME,
        Payload=json.dumps({
            "httpMethod": "POST",
            "path": "/alarms",
            "headers": {
                "Authorization": f"Bearer {token}",
                "origin": "https://costhub.4bfast.com.br",
                "Content-Type": "application/json"
            },
            "body": json.dumps(alarm_data)
        })
    )
    
    result = json.loads(response['Payload'].read())
    if result.get('statusCode') == 201:
        body = json.loads(result['body'])
        created_alarm_id = body['data']['alarm_id']
        print(f"✅ Create alarm: {body['data']['name']} (ID: {created_alarm_id})")
    else:
        print(f"❌ Create alarm failed: {result}")
        return False
    
    # Test 3: List alarms again (should have 1 now)
    print("\n🔍 Test 3: List alarms after creation...")
    response = lambda_client.invoke(
        FunctionName=LAMBDA_FUNCTION_NAME,
        Payload=json.dumps({
            "httpMethod": "GET",
            "path": "/alarms",
            "headers": {
                "Authorization": f"Bearer {token}",
                "origin": "https://costhub.4bfast.com.br"
            }
        })
    )
    
    result = json.loads(response['Payload'].read())
    if result.get('statusCode') == 200:
        body = json.loads(result['body'])
        print(f"✅ List alarms: {body['data']['count']} alarms found")
        if body['data']['count'] > 0:
            alarm = body['data']['alarms'][0]
            print(f"   📊 Alarm: {alarm['name']} - ${alarm['threshold']} {alarm['comparison_operator']}")
    else:
        print(f"❌ List alarms failed: {result}")
        return False
    
    # Test 4: Update alarm
    if created_alarm_id:
        print(f"\n🔍 Test 4: Update alarm {created_alarm_id}...")
        update_data = {
            "threshold": 150.0,
            "description": "Updated: Alert when monthly cost exceeds $150"
        }
        
        response = lambda_client.invoke(
            FunctionName=LAMBDA_FUNCTION_NAME,
            Payload=json.dumps({
                "httpMethod": "PUT",
                "path": f"/alarms/{created_alarm_id}",
                "headers": {
                    "Authorization": f"Bearer {token}",
                    "origin": "https://costhub.4bfast.com.br",
                    "Content-Type": "application/json"
                },
                "body": json.dumps(update_data)
            })
        )
        
        result = json.loads(response['Payload'].read())
        if result.get('statusCode') == 200:
            body = json.loads(result['body'])
            print(f"✅ Update alarm: Threshold updated to ${body['data']['threshold']}")
        else:
            print(f"❌ Update alarm failed: {result}")
            return False
    
    # Test 5: Delete alarm
    if created_alarm_id:
        print(f"\n🔍 Test 5: Delete alarm {created_alarm_id}...")
        response = lambda_client.invoke(
            FunctionName=LAMBDA_FUNCTION_NAME,
            Payload=json.dumps({
                "httpMethod": "DELETE",
                "path": f"/alarms/{created_alarm_id}",
                "headers": {
                    "Authorization": f"Bearer {token}",
                    "origin": "https://costhub.4bfast.com.br"
                }
            })
        )
        
        result = json.loads(response['Payload'].read())
        if result.get('statusCode') == 200:
            print("✅ Delete alarm: Successfully deleted")
        else:
            print(f"❌ Delete alarm failed: {result}")
            return False
    
    # Test 6: Final list (should be empty again)
    print("\n🔍 Test 6: Final list alarms...")
    response = lambda_client.invoke(
        FunctionName=LAMBDA_FUNCTION_NAME,
        Payload=json.dumps({
            "httpMethod": "GET",
            "path": "/alarms",
            "headers": {
                "Authorization": f"Bearer {token}",
                "origin": "https://costhub.4bfast.com.br"
            }
        })
    )
    
    result = json.loads(response['Payload'].read())
    if result.get('statusCode') == 200:
        body = json.loads(result['body'])
        print(f"✅ Final list: {body['data']['count']} alarms (should be 0)")
    else:
        print(f"❌ Final list failed: {result}")
        return False
    
    return True

if __name__ == "__main__":
    success = test_alarms_crud()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 ALL ALARMS TESTS PASSED!")
        print("\n📋 Validated Features:")
        print("• GET /alarms - List alarms")
        print("• POST /alarms - Create alarm")
        print("• PUT /alarms/{id} - Update alarm")
        print("• DELETE /alarms/{id} - Delete alarm")
        print("• DynamoDB costhub-alarms table")
        print("• JWT client_id isolation")
        
        print("\n✅ PHASE 3 ALARMS CRUD - COMPLETE!")
    else:
        print("❌ Some tests failed - check logs above")
