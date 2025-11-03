#!/bin/bash
echo "🚀 Deploying Alarms DynamoDB Table..."
echo "📋 Account: 008195334540"
echo "📋 Region: us-east-1"

export CDK_DEFAULT_ACCOUNT=008195334540
export CDK_DEFAULT_REGION=us-east-1

cdk deploy costhub-alarms-table -a "python3 app_alarms.py" --require-approval never
