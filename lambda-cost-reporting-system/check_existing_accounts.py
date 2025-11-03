#!/usr/bin/env python3
"""
Check existing accounts in DynamoDB and validate cost data
"""

import boto3
import json
from datetime import datetime, timedelta

def check_accounts_and_costs():
    """Check existing accounts and their cost data"""
    
    print("🔍 Checking existing accounts in CostHub...")
    print("=" * 50)
    
    try:
        # Check DynamoDB accounts table (using 4bfast profile)
        session = boto3.Session(profile_name='4bfast')
        dynamodb = session.resource('dynamodb', region_name='us-east-1')
        accounts_table = dynamodb.Table('costhub-accounts')
        
        print("📋 Scanning accounts table...")
        response = accounts_table.scan()
        accounts = response.get('Items', [])
        
        print(f"Found {len(accounts)} accounts:")
        
        if not accounts:
            print("❌ No accounts found in database")
            print("\n💡 Creating a test account...")
            
            # Create a test account
            test_account = {
                'account_id': '008195334540',  # Current AWS account
                'name': 'Main AWS Account',
                'provider_type': 'aws',
                'status': 'active',
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            accounts_table.put_item(Item=test_account)
            print(f"✅ Created test account: {test_account['name']}")
            accounts = [test_account]
        
        # Display accounts
        for i, account in enumerate(accounts, 1):
            print(f"\n{i}. Account ID: {account['account_id']}")
            print(f"   Name: {account['name']}")
            print(f"   Provider: {account['provider_type']}")
            print(f"   Status: {account['status']}")
            print(f"   Created: {account.get('created_at', 'N/A')}")
        
        # Check cost data for the current AWS account
        print(f"\n💰 Checking cost data for current AWS account...")
        
        ce_client = session.client('ce', region_name='us-east-1')
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
        
        # Get current costs
        costs_response = ce_client.get_cost_and_usage(
            TimePeriod={
                'Start': start_date.strftime('%Y-%m-%d'),
                'End': end_date.strftime('%Y-%m-%d')
            },
            Granularity='MONTHLY',
            Metrics=['UnblendedCost']
        )
        
        if costs_response['ResultsByTime']:
            total_cost = float(costs_response['ResultsByTime'][0]['Total']['UnblendedCost']['Amount'])
            print(f"✅ Current month cost: ${total_cost:.2f}")
            
            # Get service breakdown
            services_response = ce_client.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Granularity='MONTHLY',
                Metrics=['UnblendedCost'],
                GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
            )
            
            if services_response['ResultsByTime']:
                groups = services_response['ResultsByTime'][0]['Groups']
                sorted_services = sorted(groups, key=lambda x: float(x['Metrics']['UnblendedCost']['Amount']), reverse=True)
                
                print(f"\n📊 Top 5 services by cost:")
                for i, service in enumerate(sorted_services[:5], 1):
                    service_name = service['Keys'][0]
                    service_cost = float(service['Metrics']['UnblendedCost']['Amount'])
                    print(f"   {i}. {service_name}: ${service_cost:.2f}")
        else:
            print("❌ No cost data found for current period")
        
        print(f"\n🎯 VALIDATION SUMMARY:")
        print(f"✅ Accounts in database: {len(accounts)}")
        print(f"✅ Cost data available: {'Yes' if costs_response['ResultsByTime'] else 'No'}")
        print(f"✅ Ready for testing: {'Yes' if accounts and costs_response['ResultsByTime'] else 'No'}")
        
        return len(accounts) > 0 and len(costs_response['ResultsByTime']) > 0
        
    except Exception as e:
        print(f"❌ Error checking accounts: {e}")
        return False

if __name__ == "__main__":
    success = check_accounts_and_costs()
    if success:
        print("\n🚀 Ready to run cost validation tests!")
    else:
        print("\n⚠️  Setup required before running tests")
