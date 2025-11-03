#!/bin/bash

# Deployment script for Lambda Cost Reporting System
# Usage: ./deploy.sh [environment] [options]

set -e

# Default values
ENVIRONMENT="dev"
REQUIRE_APPROVAL="never"
VERBOSE=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --require-approval)
            REQUIRE_APPROVAL="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE="--verbose"
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  -e, --environment ENV    Environment to deploy (dev, staging, prod) [default: dev]"
            echo "  --require-approval TYPE  Approval type (never, any-change, broadening) [default: never]"
            echo "  -v, --verbose           Enable verbose output"
            echo "  -h, --help              Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|prod)$ ]]; then
    echo "Error: Environment must be one of: dev, staging, prod"
    exit 1
fi

echo "🚀 Deploying Lambda Cost Reporting System to $ENVIRONMENT environment..."

# Set environment variables
export ENVIRONMENT="$ENVIRONMENT"
export JSII_SILENCE_WARNING_UNTESTED_NODE_VERSION=1

# Check if CDK is installed
if ! command -v cdk &> /dev/null; then
    echo "Error: AWS CDK CLI is not installed. Please install it first:"
    echo "npm install -g aws-cdk"
    exit 1
fi

# Check if Python dependencies are installed
if ! python3 -c "import aws_cdk_lib" &> /dev/null; then
    echo "Installing Python dependencies..."
    python3 -m pip install -r requirements.txt
fi

# Bootstrap CDK if needed (only for first deployment)
echo "📦 Checking CDK bootstrap status..."
if ! cdk bootstrap --show-template &> /dev/null; then
    echo "Bootstrapping CDK..."
    cdk bootstrap
fi

# Synthesize the stack
echo "🔨 Synthesizing CDK stack..."
cdk synth $VERBOSE

# Deploy the stack
echo "🚀 Deploying stack..."
cdk deploy \
    --require-approval "$REQUIRE_APPROVAL" \
    $VERBOSE

echo "✅ Deployment completed successfully!"

# Show stack outputs
echo ""
echo "📋 Stack Information:"
echo "Environment: $ENVIRONMENT"
echo "Stack Name: lambda-cost-reporting-$ENVIRONMENT"
echo "Region: ${CDK_DEFAULT_REGION:-us-east-1}"
echo "Account: ${CDK_DEFAULT_ACCOUNT:-$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo 'Unknown')}"

echo ""
echo "🎯 Next Steps:"
echo "1. Configure client settings in DynamoDB table: cost-reporting-$ENVIRONMENT-clients"
echo "2. Set up SES email sending (verify sender email address)"
echo "3. Test the Lambda function with a manual invocation"
echo "4. Monitor CloudWatch dashboards and alarms"