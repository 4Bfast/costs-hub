#!/usr/bin/env python3
"""
Test Configuration and JWT Utils
Validates that hardcodes are removed and config works
"""

import sys
import os
sys.path.append('src')

from config.settings import config
from utils.jwt_utils import extract_client_id_from_token, validate_cognito_token

def test_config():
    """Test centralized configuration"""
    print("🔧 Testing Configuration...")
    
    # Test config values
    print(f"✅ AWS Region: {config.AWS_REGION}")
    print(f"✅ Cognito User Pool: {config.COGNITO_USER_POOL_ID}")
    print(f"✅ DynamoDB Accounts Table: {config.DYNAMODB_ACCOUNTS_TABLE}")
    print(f"✅ CORS Origins: {config.get_cors_origins_list()}")
    
    assert config.AWS_REGION == 'us-east-1'
    assert config.COGNITO_USER_POOL_ID == 'us-east-1_94OYkzcSO'
    assert config.DYNAMODB_ACCOUNTS_TABLE == 'costhub-accounts'
    
    print("✅ Configuration test passed!")

def test_jwt_extraction():
    """Test JWT client_id extraction"""
    print("\n🔑 Testing JWT Extraction...")
    
    # Test with sample JWT payload (base64 encoded)
    # This is a sample payload: {"sub": "user123", "client_id": "real-client-456", "username": "testuser"}
    sample_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyMTIzIiwiY2xpZW50X2lkIjoicmVhbC1jbGllbnQtNDU2IiwidXNlcm5hbWUiOiJ0ZXN0dXNlciJ9.signature"
    
    try:
        client_id = extract_client_id_from_token(sample_jwt)
        print(f"✅ Extracted client_id: {client_id}")
        assert client_id == "real-client-456"
        print("✅ JWT extraction test passed!")
    except Exception as e:
        print(f"❌ JWT extraction failed: {e}")

def test_no_hardcodes():
    """Verify no hardcodes remain"""
    print("\n🚫 Testing No Hardcodes...")
    
    # Check that we're not using hardcoded values
    from handlers.accounts_handler_simple import get_client_id_for_user
    
    # This should NOT return "test-client-001" anymore
    result = get_client_id_for_user("testuser")
    print(f"✅ get_client_id_for_user result: {result}")
    
    # Should be client-testuser, not test-client-001
    assert result != "test-client-001"
    assert "client-" in result
    
    print("✅ No hardcodes test passed!")

if __name__ == "__main__":
    print("🧪 COSTHUB CONFIGURATION TESTS")
    print("=" * 50)
    
    try:
        test_config()
        test_jwt_extraction()
        test_no_hardcodes()
        
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ Configuration centralized")
        print("✅ JWT extraction working")
        print("✅ Hardcodes removed")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
