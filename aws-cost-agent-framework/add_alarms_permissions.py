#!/usr/bin/env python3
"""
Add DynamoDB permissions for costhub-alarms table to Lambda role
"""

import boto3
import json

# Configuration
LAMBDA_ROLE_NAME = "costhub-frontend-api-prod-APIHandlerServiceRole41BB-d1ua34rEqyZD"
AWS_PROFILE = "4bfast"
AWS_REGION = "us-east-1"

def add_alarms_permissions():
    """Add DynamoDB permissions for alarms table"""
    print("🔧 Adding DynamoDB permissions for costhub-alarms table...")
    
    session = boto3.Session(profile_name=AWS_PROFILE)
    iam = session.client('iam')
    
    # Policy document for alarms table
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "dynamodb:GetItem",
                    "dynamodb:PutItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:DeleteItem",
                    "dynamodb:Scan",
                    "dynamodb:Query"
                ],
                "Resource": [
                    f"arn:aws:dynamodb:{AWS_REGION}:008195334540:table/costhub-alarms",
                    f"arn:aws:dynamodb:{AWS_REGION}:008195334540:table/costhub-alarms/*"
                ]
            }
        ]
    }
    
    try:
        # Create or update inline policy
        iam.put_role_policy(
            RoleName=LAMBDA_ROLE_NAME,
            PolicyName='CostHubAlarmsTableAccess',
            PolicyDocument=json.dumps(policy_document)
        )
        
        print("✅ DynamoDB permissions added successfully")
        print("📊 Permissions granted:")
        print("   • GetItem, PutItem, UpdateItem, DeleteItem")
        print("   • Scan, Query")
        print("   • Resource: costhub-alarms table")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to add permissions: {e}")
        return False

if __name__ == "__main__":
    add_alarms_permissions()
