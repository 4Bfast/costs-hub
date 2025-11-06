#!/usr/bin/env python3
"""
Create Alarms DynamoDB Table
"""

import boto3
import json

def create_alarms_table():
    """Create costhub-alarms DynamoDB table"""
    
    dynamodb = boto3.client('dynamodb', region_name='us-east-1')
    
    try:
        response = dynamodb.create_table(
            TableName='costhub-alarms',
            KeySchema=[
                {
                    'AttributeName': 'alarm_id',
                    'KeyType': 'HASH'
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'alarm_id',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        print(f"✅ Table created: {response['TableDescription']['TableName']}")
        print(f"Status: {response['TableDescription']['TableStatus']}")
        
    except Exception as e:
        if 'ResourceInUseException' in str(e):
            print("✅ Table already exists: costhub-alarms")
        else:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    create_alarms_table()
