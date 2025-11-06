#!/usr/bin/env python3
"""
Create test user in Cognito using 4bfast profile
"""

import boto3

USER_POOL_ID = "us-east-1_94OYkzcSO"
REGION = "us-east-1"

def create_test_user():
    """Create a test user in Cognito"""
    
    session = boto3.Session(profile_name='4bfast')
    cognito = session.client('cognito-idp', region_name=REGION)
    
    try:
        # Create user
        response = cognito.admin_create_user(
            UserPoolId=USER_POOL_ID,
            Username='test@4bfast.com.br',
            UserAttributes=[
                {'Name': 'email', 'Value': 'test@4bfast.com.br'},
                {'Name': 'email_verified', 'Value': 'true'}
            ],
            TemporaryPassword='TempPassword123!',
            MessageAction='SUPPRESS'
        )
        
        print(f"✅ User created: {response['User']['Username']}")
        
        # Set permanent password
        cognito.admin_set_user_password(
            UserPoolId=USER_POOL_ID,
            Username='test@4bfast.com.br',
            Password='TestPassword123!',
            Permanent=True
        )
        
        print("✅ Password set to permanent")
        print("Username: test@4bfast.com.br")
        print("Password: TestPassword123!")
        
        return True
        
    except Exception as e:
        if 'UsernameExistsException' in str(e):
            print("✅ User already exists: test@4bfast.com.br")
            print("Username: test@4bfast.com.br")
            print("Password: TestPassword123!")
            return True
        else:
            print(f"❌ Error: {e}")
            return False

if __name__ == "__main__":
    success = create_test_user()
    if success:
        print("\n🚀 Ready to run tests with testuser credentials!")
    else:
        print("\n❌ Failed to create test user")
