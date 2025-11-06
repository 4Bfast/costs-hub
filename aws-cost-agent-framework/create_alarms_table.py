#!/usr/bin/env python3
"""
Create costhub-alarms DynamoDB table
"""

import boto3
from config.settings import config

def create_alarms_table():
    """Create costhub-alarms DynamoDB table"""
    print("🔧 Creating costhub-alarms DynamoDB table...")
    
    session = boto3.Session(profile_name='4bfast')  # Use profile directly
    dynamodb = session.resource('dynamodb', region_name=config.AWS_REGION)
    
    try:
        table = dynamodb.create_table(
            TableName='costhub-alarms',
            KeySchema=[
                {'AttributeName': 'alarm_id', 'KeyType': 'HASH'},
                {'AttributeName': 'client_id', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'alarm_id', 'AttributeType': 'S'},
                {'AttributeName': 'client_id', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        print("⏳ Waiting for table to be created...")
        table.wait_until_exists()
        
        print("✅ Table costhub-alarms created successfully")
        print(f"📊 Table ARN: {table.table_arn}")
        
        return True
        
    except Exception as e:
        if 'ResourceInUseException' in str(e):
            print("⚠️  Table costhub-alarms already exists")
            return True
        else:
            print(f"❌ Failed to create table: {e}")
            return False

if __name__ == "__main__":
    create_alarms_table()
