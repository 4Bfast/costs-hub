#!/usr/bin/env python3
"""
Create test user in Cognito
"""

import boto3
import json

USER_POOL_ID = "us-east-1_94OYkzcSO"
REGION = "us-east-1"

def create_test_user():
    """Create a test user in Cognito"""
    
    cognito = boto3.client('cognito-idp', region_name=REGION)
    
    try:
        # Create user
        response = cognito.admin_create_user(
            UserPoolId=USER_POOL_ID,
            Username='testuser',
            UserAttributes=[
                {'Name': 'email', 'Value': 'test@example.com'},
                {'Name': 'email_verified', 'Value': 'true'}
            ],
            TemporaryPassword='TempPassword123!',
            MessageAction='SUPPRESS'  # Don't send welcome email
        )
        
        print(f"✅ User created: {response['User']['Username']}")
        
        # Set permanent password
        cognito.admin_set_user_password(
            UserPoolId=USER_POOL_ID,
            Username='testuser',
            Password='TestPassword123!',
            Permanent=True
        )
        
        print("✅ Password set to permanent")
        print("Username: testuser")
        print("Password: TestPassword123!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    create_test_user()
