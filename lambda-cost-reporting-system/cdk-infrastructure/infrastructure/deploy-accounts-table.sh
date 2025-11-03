#!/bin/bash

# Deploy Accounts Table to AWS
# This creates the DynamoDB table for real account persistence

set -e

echo "🚀 Deploying Accounts Table..."

# Change to infrastructure directory
cd "$(dirname "$0")"

# Deploy the accounts table stack
cdk deploy costhub-accounts-table-prod \
    --app "python3 app_accounts.py" \
    --require-approval never \
    --outputs-file accounts-table-outputs.json

echo "✅ Accounts table deployed successfully!"
echo "📋 Check accounts-table-outputs.json for table details"
