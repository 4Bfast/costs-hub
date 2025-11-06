#!/usr/bin/env python3
"""
Fix Cognito permissions for user management endpoints
Adds missing permissions to the existing CognitoAccessPolicy
"""

import boto3
import json

def update_cognito_permissions():
    """Update IAM role with complete Cognito permissions"""
    
    # Configuration
    ROLE_NAME = "costhub-frontend-api-prod-APIHandlerServiceRole41BB-d1ua34rEqyZD"
    POLICY_NAME = "CognitoAccessPolicy"
    USER_POOL_ARN = "arn:aws:cognito-idp:us-east-1:008195334540:userpool/us-east-1_94OYkzcSO"
    
    # Complete policy with all required permissions
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    # Authentication actions
                    "cognito-idp:AdminInitiateAuth",
                    "cognito-idp:AdminCreateUser",
                    "cognito-idp:AdminSetUserPassword",
                    "cognito-idp:AdminConfirmSignUp",
                    
                    # User management actions
                    "cognito-idp:GetUser",
                    "cognito-idp:AdminGetUser",
                    "cognito-idp:AdminUpdateUserAttributes",
                    "cognito-idp:AdminDeleteUser",
                    
                    # List and describe actions
                    "cognito-idp:ListUsers",
                    "cognito-idp:DescribeUserPool",
                    "cognito-idp:AdminListGroupsForUser",
                    
                    # Token management
                    "cognito-idp:AdminRespondToAuthChallenge",
                    "cognito-idp:InitiateAuth",
                    "cognito-idp:RespondToAuthChallenge"
                ],
                "Resource": USER_POOL_ARN
            }
        ]
    }
    
    try:
        # Initialize IAM client
        iam = boto3.client('iam', region_name='us-east-1')
        
        print("🔧 Updating Cognito permissions...")
        print(f"   Role: {ROLE_NAME}")
        print(f"   Policy: {POLICY_NAME}")
        
        # Update the inline policy
        iam.put_role_policy(
            RoleName=ROLE_NAME,
            PolicyName=POLICY_NAME,
            PolicyDocument=json.dumps(policy_document)
        )
        
        print("✅ Successfully updated Cognito permissions!")
        print("\n📋 Added permissions:")
        for action in policy_document["Statement"][0]["Action"]:
            print(f"   • {action}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating permissions: {str(e)}")
        return False

if __name__ == "__main__":
    print("🔐 CostHub Cognito Permissions Fix")
    print("=" * 50)
    
    success = update_cognito_permissions()
    
    if success:
        print("\n🎉 Permissions updated successfully!")
        print("   You can now test user management endpoints")
    else:
        print("\n💥 Failed to update permissions")
        print("   Please check AWS credentials and permissions")
