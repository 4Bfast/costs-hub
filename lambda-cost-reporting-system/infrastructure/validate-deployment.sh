#!/bin/bash

# Validation script for Lambda Cost Reporting System deployment
# Usage: ./validate-deployment.sh [environment]

set -e

ENVIRONMENT="${1:-dev}"

echo "🔍 Validating deployment for $ENVIRONMENT environment..."

# Set environment variables
export ENVIRONMENT="$ENVIRONMENT"
STACK_NAME="lambda-cost-reporting-$ENVIRONMENT"

# Check if stack exists
echo "📋 Checking CloudFormation stack..."
if aws cloudformation describe-stacks --stack-name "$STACK_NAME" &> /dev/null; then
    echo "✅ Stack $STACK_NAME exists"
    
    # Get stack status
    STACK_STATUS=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --query 'Stacks[0].StackStatus' --output text)
    echo "   Status: $STACK_STATUS"
    
    if [[ "$STACK_STATUS" != "CREATE_COMPLETE" && "$STACK_STATUS" != "UPDATE_COMPLETE" ]]; then
        echo "❌ Stack is not in a healthy state"
        exit 1
    fi
else
    echo "❌ Stack $STACK_NAME does not exist"
    exit 1
fi

# Check Lambda function
echo ""
echo "🔧 Checking Lambda function..."
FUNCTION_NAME="cost-reporting-$ENVIRONMENT-handler"
if aws lambda get-function --function-name "$FUNCTION_NAME" &> /dev/null; then
    echo "✅ Lambda function $FUNCTION_NAME exists"
    
    # Check function configuration
    RUNTIME=$(aws lambda get-function --function-name "$FUNCTION_NAME" --query 'Configuration.Runtime' --output text)
    MEMORY=$(aws lambda get-function --function-name "$FUNCTION_NAME" --query 'Configuration.MemorySize' --output text)
    TIMEOUT=$(aws lambda get-function --function-name "$FUNCTION_NAME" --query 'Configuration.Timeout' --output text)
    
    echo "   Runtime: $RUNTIME"
    echo "   Memory: ${MEMORY}MB"
    echo "   Timeout: ${TIMEOUT}s"
else
    echo "❌ Lambda function $FUNCTION_NAME does not exist"
    exit 1
fi

# Check DynamoDB table
echo ""
echo "🗄️  Checking DynamoDB table..."
TABLE_NAME="cost-reporting-$ENVIRONMENT-clients"
if aws dynamodb describe-table --table-name "$TABLE_NAME" &> /dev/null; then
    echo "✅ DynamoDB table $TABLE_NAME exists"
    
    TABLE_STATUS=$(aws dynamodb describe-table --table-name "$TABLE_NAME" --query 'Table.TableStatus' --output text)
    echo "   Status: $TABLE_STATUS"
    
    if [[ "$TABLE_STATUS" != "ACTIVE" ]]; then
        echo "❌ Table is not active"
        exit 1
    fi
else
    echo "❌ DynamoDB table $TABLE_NAME does not exist"
    exit 1
fi

# Check S3 bucket
echo ""
echo "🪣 Checking S3 bucket..."
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BUCKET_NAME="cost-reporting-$ENVIRONMENT-reports-$ACCOUNT_ID"
if aws s3api head-bucket --bucket "$BUCKET_NAME" &> /dev/null; then
    echo "✅ S3 bucket $BUCKET_NAME exists"
else
    echo "❌ S3 bucket $BUCKET_NAME does not exist"
    exit 1
fi

# Check EventBridge rules
echo ""
echo "⏰ Checking EventBridge rules..."
WEEKLY_RULE="cost-reporting-$ENVIRONMENT-weekly"
MONTHLY_RULE="cost-reporting-$ENVIRONMENT-monthly"

if aws events describe-rule --name "$WEEKLY_RULE" &> /dev/null; then
    echo "✅ Weekly rule $WEEKLY_RULE exists"
    WEEKLY_STATE=$(aws events describe-rule --name "$WEEKLY_RULE" --query 'State' --output text)
    echo "   State: $WEEKLY_STATE"
else
    echo "❌ Weekly rule $WEEKLY_RULE does not exist"
    exit 1
fi

if aws events describe-rule --name "$MONTHLY_RULE" &> /dev/null; then
    echo "✅ Monthly rule $MONTHLY_RULE exists"
    MONTHLY_STATE=$(aws events describe-rule --name "$MONTHLY_RULE" --query 'State' --output text)
    echo "   State: $MONTHLY_STATE"
else
    echo "❌ Monthly rule $MONTHLY_RULE does not exist"
    exit 1
fi

# Check SNS topic
echo ""
echo "📧 Checking SNS topic..."
TOPIC_NAME="cost-reporting-$ENVIRONMENT-admin-alerts"
if aws sns list-topics --query "Topics[?contains(TopicArn, '$TOPIC_NAME')]" --output text | grep -q "$TOPIC_NAME"; then
    echo "✅ SNS topic $TOPIC_NAME exists"
else
    echo "❌ SNS topic $TOPIC_NAME does not exist"
    exit 1
fi

# Check CloudWatch alarms
echo ""
echo "🚨 Checking CloudWatch alarms..."
ALARM_PREFIX="cost-reporting-$ENVIRONMENT"
ALARM_COUNT=$(aws cloudwatch describe-alarms --alarm-name-prefix "$ALARM_PREFIX" --query 'length(MetricAlarms)')

if [[ "$ALARM_COUNT" -gt 0 ]]; then
    echo "✅ Found $ALARM_COUNT CloudWatch alarms"
else
    echo "❌ No CloudWatch alarms found"
    exit 1
fi

# Check CloudWatch dashboards
echo ""
echo "📊 Checking CloudWatch dashboards..."
DASHBOARD_PREFIX="cost-reporting-$ENVIRONMENT"
DASHBOARD_COUNT=$(aws cloudwatch list-dashboards --dashboard-name-prefix "$DASHBOARD_PREFIX" --query 'length(DashboardEntries)')

if [[ "$DASHBOARD_COUNT" -gt 0 ]]; then
    echo "✅ Found $DASHBOARD_COUNT CloudWatch dashboards"
else
    echo "❌ No CloudWatch dashboards found"
    exit 1
fi

echo ""
echo "🎉 All validation checks passed!"
echo ""
echo "📋 Deployment Summary:"
echo "Environment: $ENVIRONMENT"
echo "Stack: $STACK_NAME"
echo "Lambda Function: $FUNCTION_NAME"
echo "DynamoDB Table: $TABLE_NAME"
echo "S3 Bucket: $BUCKET_NAME"
echo "EventBridge Rules: $WEEKLY_RULE, $MONTHLY_RULE"
echo "SNS Topic: $TOPIC_NAME"
echo "CloudWatch Alarms: $ALARM_COUNT"
echo "CloudWatch Dashboards: $DASHBOARD_COUNT"
echo ""
echo "🚀 The system is ready for use!"