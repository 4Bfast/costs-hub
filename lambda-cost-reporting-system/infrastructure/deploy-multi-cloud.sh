#!/bin/bash

# Multi-Cloud AI Cost Analytics Deployment Script
# This script deploys the enhanced multi-cloud infrastructure

set -e

# Configuration
ENVIRONMENT=${1:-dev}
REGION=${2:-us-east-1}
ACCOUNT=${3:-$(aws sts get-caller-identity --query Account --output text)}

echo "🚀 Deploying Multi-Cloud AI Cost Analytics System"
echo "Environment: $ENVIRONMENT"
echo "Region: $REGION"
echo "Account: $ACCOUNT"

# Set environment variables
export CDK_DEFAULT_ACCOUNT=$ACCOUNT
export CDK_DEFAULT_REGION=$REGION
export ENVIRONMENT=$ENVIRONMENT

# Check if CDK is installed
if ! command -v cdk &> /dev/null; then
    echo "❌ AWS CDK is not installed. Please install it first:"
    echo "npm install -g aws-cdk"
    exit 1
fi

# Check if Python dependencies are installed
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
fi

echo "📦 Installing Python dependencies..."
source venv/bin/activate
pip install -r requirements.txt

# Bootstrap CDK if needed
echo "🔧 Bootstrapping CDK..."
cdk bootstrap aws://$ACCOUNT/$REGION

# Synthesize the stack
echo "🔨 Synthesizing CDK stack..."
cdk synth -a "python multi_cloud_app.py"

# Deploy the stack
echo "🚀 Deploying stack..."
cdk deploy -a "python multi_cloud_app.py" \
    --require-approval never \
    --outputs-file outputs.json \
    --progress events

echo "✅ Deployment completed successfully!"

# Display outputs
if [ -f "outputs.json" ]; then
    echo "📋 Stack Outputs:"
    cat outputs.json | jq '.'
fi

echo ""
echo "🎉 Multi-Cloud AI Cost Analytics System deployed!"
echo "Environment: $ENVIRONMENT"
echo "Stack Name: multi-cloud-analytics-$ENVIRONMENT"
echo ""
echo "Next steps:"
echo "1. Configure provider credentials in AWS Secrets Manager"
echo "2. Set up client configurations"
echo "3. Test the API endpoints"
echo "4. Monitor the CloudWatch dashboards"