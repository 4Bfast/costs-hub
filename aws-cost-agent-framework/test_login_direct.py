#!/usr/bin/env python3
"""
Direct test of login functionality
"""

import json
import boto3

def test_login_direct():
    """Test login directly with Lambda"""
    
    # Configuration
    LAMBDA_FUNCTION_NAME = "costhub-frontend-api-prod-APIHandler68F11976-POT1msJZKUqV"
    
    # Create Lambda client
    session = boto3.Session(profile_name='4bfast')
    lambda_client = session.client('lambda', region_name='us-east-1')
    
    # Test event
    event = {
        "httpMethod": "POST",
        "path": "/auth/login",
        "headers": {
            "origin": "https://costhub.4bfast.com.br",
            "Content-Type": "application/json"
        },
        "body": json.dumps({
            "email": "test@4bfast.com.br",
            "password": "TestPassword123!"
        })
    }
    
    print("🔍 Testing direct Lambda invocation for login...")
    print(f"📧 Email: test@4bfast.com.br")
    print(f"🔑 Password: TestPassword123!")
    
    try:
        response = lambda_client.invoke(
            FunctionName=LAMBDA_FUNCTION_NAME,
            Payload=json.dumps(event)
        )
        
        result = json.loads(response['Payload'].read())
        status_code = result.get('statusCode', 500)
        
        print(f"\n📊 Response Status: {status_code}")
        
        if 'body' in result:
            body = json.loads(result['body']) if isinstance(result['body'], str) else result['body']
            print(f"📝 Response Body: {json.dumps(body, indent=2)}")
        
        if 'errorMessage' in result:
            print(f"❌ Error: {result['errorMessage']}")
            if 'errorType' in result:
                print(f"🔍 Error Type: {result['errorType']}")
            if 'stackTrace' in result:
                print(f"📚 Stack Trace: {result['stackTrace']}")
        
        return status_code == 200
        
    except Exception as e:
        print(f"❌ Exception during test: {str(e)}")
        return False

if __name__ == "__main__":
    print("🔐 Direct Login Test")
    print("=" * 50)
    
    success = test_login_direct()
    
    if success:
        print("\n✅ Login test successful!")
    else:
        print("\n❌ Login test failed!")
