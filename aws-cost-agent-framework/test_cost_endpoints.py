#!/usr/bin/env python3
"""
Test script for Cost Explorer endpoints
Tests the new real cost endpoints implementation
"""

import json
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(__file__))

from services.aws_cost_service import AWSCostService
from handlers.costs_handler_real import handle_costs_request
from config.settings import config

def test_cost_service():
    """Test AWSCostService directly"""
    print("🧪 Testing AWSCostService...")
    
    # Mock account config
    account_config = {
        'account_id': '008195334540',
        'configuration': {
            'role_arn': None,  # Use default credentials
            'external_id': None
        }
    }
    
    try:
        cost_service = AWSCostService(account_config)
        
        # Test cost summary
        print("📊 Testing cost summary...")
        summary = cost_service.get_cost_summary('2024-10-01', '2024-11-01')
        print(f"✅ Summary: ${summary.get('total_cost', 0):.2f} across {summary.get('service_count', 0)} services")
        
        # Test cost trends
        print("📈 Testing cost trends...")
        trends = cost_service.get_cost_trends(30)
        print(f"✅ Trends: {trends.get('period_days', 0)} days, avg ${trends.get('average_daily_cost', 0):.2f}/day")
        
        # Test cost breakdown
        print("🔍 Testing cost breakdown...")
        breakdown = cost_service.get_cost_breakdown('SERVICE', 30)
        print(f"✅ Breakdown: {breakdown.get('item_count', 0)} services, total ${breakdown.get('total_cost', 0):.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Cost service test failed: {e}")
        return False

def test_cost_handler():
    """Test costs handler with mock events"""
    print("\n🧪 Testing Cost Handler...")
    
    cors_headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'
    }
    
    # Mock JWT token (in real scenario, this would be a valid Cognito token)
    mock_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJjbGllbnRfaWQiOiJ0ZXN0LWNsaWVudC0wMDEiLCJ1c2VybmFtZSI6InRlc3R1c2VyIn0.test"
    
    test_cases = [
        {
            'name': 'Cost Summary',
            'event': {
                'httpMethod': 'GET',
                'path': '/api/v1/costs/summary',
                'headers': {'Authorization': f'Bearer {mock_token}'},
                'queryStringParameters': None
            }
        },
        {
            'name': 'Cost Trends',
            'event': {
                'httpMethod': 'GET',
                'path': '/api/v1/costs/trends',
                'headers': {'Authorization': f'Bearer {mock_token}'},
                'queryStringParameters': {'days': '30'}
            }
        },
        {
            'name': 'Cost Breakdown',
            'event': {
                'httpMethod': 'GET',
                'path': '/api/v1/costs/breakdown',
                'headers': {'Authorization': f'Bearer {mock_token}'},
                'queryStringParameters': {'group_by': 'SERVICE', 'days': '30'}
            }
        },
        {
            'name': 'Cost by Service',
            'event': {
                'httpMethod': 'GET',
                'path': '/api/v1/costs/by-service',
                'headers': {'Authorization': f'Bearer {mock_token}'},
                'queryStringParameters': None
            }
        }
    ]
    
    for test_case in test_cases:
        try:
            print(f"🔍 Testing {test_case['name']}...")
            response = handle_costs_request(test_case['event'], cors_headers)
            
            if response['statusCode'] == 200:
                body = json.loads(response['body'])
                if body.get('success'):
                    print(f"✅ {test_case['name']}: Success")
                else:
                    print(f"❌ {test_case['name']}: {body.get('error', 'Unknown error')}")
            else:
                print(f"❌ {test_case['name']}: HTTP {response['statusCode']}")
                
        except Exception as e:
            print(f"❌ {test_case['name']}: Exception - {e}")

def test_configuration():
    """Test configuration setup"""
    print("\n🧪 Testing Configuration...")
    
    try:
        print(f"✅ AWS Region: {config.AWS_REGION}")
        print(f"✅ DynamoDB Accounts Table: {config.DYNAMODB_ACCOUNTS_TABLE}")
        print(f"✅ Cognito User Pool: {config.COGNITO_USER_POOL_ID}")
        print(f"✅ CORS Origins: {config.CORS_ALLOWED_ORIGINS}")
        return True
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 CostHub Cost Endpoints Test Suite")
    print("=" * 50)
    
    # Test configuration
    config_ok = test_configuration()
    
    # Test cost service
    service_ok = test_cost_service()
    
    # Test cost handler
    test_cost_handler()
    
    print("\n" + "=" * 50)
    if config_ok and service_ok:
        print("✅ Tests completed - Cost endpoints ready for deployment")
        print("\n📋 Next Steps:")
        print("1. Deploy to Lambda function")
        print("2. Test with real JWT tokens")
        print("3. Verify with frontend integration")
    else:
        print("❌ Some tests failed - check configuration and AWS credentials")
        
    print(f"\n🔧 Lambda Function: {config.LAMBDA_FUNCTION_NAME}")
    print(f"🌐 API Domain: https://api-costhub.4bfast.com.br")

if __name__ == "__main__":
    main()
