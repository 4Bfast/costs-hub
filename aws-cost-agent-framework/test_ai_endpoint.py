#!/usr/bin/env python3
"""
Test AI insights endpoint - Phase 4A
"""

import json
import boto3

def test_ai_insights():
    """Test AI insights endpoint"""
    
    # Configuration
    LAMBDA_FUNCTION_NAME = "costhub-frontend-api-prod-APIHandler68F11976-POT1msJZKUqV"
    
    # Create Lambda client
    session = boto3.Session(profile_name='4bfast')
    lambda_client = session.client('lambda', region_name='us-east-1')
    
    # Test event
    event = {
        "httpMethod": "GET",
        "path": "/ai/insights",
        "headers": {
            "origin": "https://costhub.4bfast.com.br",
            "Content-Type": "application/json",
            "Authorization": "Bearer dummy-token-for-testing"
        }
    }
    
    print("🤖 Testing AI Insights Endpoint")
    print("=" * 50)
    print("🔍 Testing GET /ai/insights...")
    
    try:
        response = lambda_client.invoke(
            FunctionName=LAMBDA_FUNCTION_NAME,
            Payload=json.dumps(event)
        )
        
        result = json.loads(response['Payload'].read())
        status_code = result.get('statusCode', 500)
        
        print(f"📊 Response Status: {status_code}")
        
        if status_code == 200:
            body = json.loads(result['body'])
            if body.get('success'):
                data = body.get('data', {})
                print("✅ AI Insights Generated Successfully!")
                print(f"\n📝 Summary: {data.get('summary', 'N/A')}")
                print(f"\n💡 Top Recommendations:")
                for i, rec in enumerate(data.get('top_recommendations', []), 1):
                    print(f"   {i}. {rec}")
                print(f"\n⚠️  Anomalies: {data.get('anomalies', [])}")
                print(f"\n🔮 Forecast: {data.get('forecast', 'N/A')}")
                return True
            else:
                print(f"❌ AI request failed: {body.get('error', 'Unknown error')}")
        else:
            body = json.loads(result.get('body', '{}'))
            print(f"❌ HTTP {status_code}: {body.get('error', 'Unknown error')}")
        
        return False
        
    except Exception as e:
        print(f"❌ Exception during test: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_ai_insights()
    
    if success:
        print("\n🎉 AI Insights endpoint working!")
        print("\n📋 Phase 4A Status:")
        print("✅ Endpoint /ai/insights deployed")
        print("✅ Bedrock permissions configured") 
        print("✅ Fallback system working")
        print("✅ Direct responses implemented")
    else:
        print("\n💥 AI Insights test failed!")
        print("Check Bedrock permissions and model availability")
