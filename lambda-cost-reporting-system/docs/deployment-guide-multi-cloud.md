# Multi-Cloud AI Cost Analytics - Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying the Multi-Cloud AI Cost Analytics system across different environments (development, staging, production). The deployment uses AWS CDK (Cloud Development Kit) for infrastructure as code.

## Prerequisites

### System Requirements
- **AWS CLI**: Version 2.x or later
- **AWS CDK**: Version 2.x or later
- **Python**: Version 3.11 or later
- **Node.js**: Version 18.x or later (for CDK)
- **Git**: For version control
- **Docker**: For local development and testing

### AWS Account Setup
- AWS account with administrative privileges
- AWS CLI configured with appropriate credentials
- CDK bootstrapped in target regions
- Sufficient service quotas for Lambda, DynamoDB, and other services

### Required Permissions
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudformation:*",
        "lambda:*",
        "dynamodb:*",
        "s3:*",
        "iam:*",
        "kms:*",
        "sns:*",
        "sqs:*",
        "events:*",
        "apigateway:*",
        "secretsmanager:*",
        "cloudwatch:*",
        "logs:*",
        "xray:*"
      ],
      "Resource": "*"
    }
  ]
}
```

## Environment Configuration

### Environment Types

#### Development Environment
- **Purpose**: Feature development and testing
- **Resources**: Minimal resource allocation
- **Data**: Synthetic or anonymized data
- **Monitoring**: Basic monitoring and alerting

#### Staging Environment
- **Purpose**: Pre-production testing and validation
- **Resources**: Production-like resource allocation
- **Data**: Production-like data (anonymized)
- **Monitoring**: Full monitoring and alerting

#### Production Environment
- **Purpose**: Live customer-facing system
- **Resources**: Full resource allocation with auto-scaling
- **Data**: Live customer data
- **Monitoring**: Comprehensive monitoring, alerting, and observability

### Environment Configuration Files

#### Development Configuration
```yaml
# infrastructure/config/dev.yaml
name: dev
account: "123456789012"
region: us-east-1
lambda_memory: 512
lambda_timeout_minutes: 5
log_retention_days: 7
enable_point_in_time_recovery: false
removal_policy: DESTROY
api_throttle_rate_limit: 100
api_throttle_burst_limit: 200
cors_allowed_origins:
  - "*"
restrict_api_access: false
enable_waf: false
jwt_secret: "dev-jwt-secret-change-me"
```

#### Staging Configuration
```yaml
# infrastructure/config/staging.yaml
name: staging
account: "123456789012"
region: us-east-1
lambda_memory: 1024
lambda_timeout_minutes: 10
log_retention_days: 30
enable_point_in_time_recovery: true
removal_policy: RETAIN
api_throttle_rate_limit: 500
api_throttle_burst_limit: 1000
cors_allowed_origins:
  - "https://staging.multicloudsanalytics.com"
restrict_api_access: true
allowed_ip_ranges:
  - "10.0.0.0/8"
  - "172.16.0.0/12"
enable_waf: true
jwt_secret: "staging-jwt-secret-from-secrets-manager"
```

#### Production Configuration
```yaml
# infrastructure/config/prod.yaml
name: prod
account: "123456789012"
region: us-east-1
lambda_memory: 1024
lambda_timeout_minutes: 15
log_retention_days: 90
enable_point_in_time_recovery: true
removal_policy: RETAIN
api_domain_name: "api.multicloudsanalytics.com"
certificate_arn: "arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012"
hosted_zone_id: "Z1234567890ABC"
cors_allowed_origins:
  - "https://app.multicloudsanalytics.com"
restrict_api_access: true
allowed_ip_ranges:
  - "10.0.0.0/8"
  - "172.16.0.0/12"
enable_waf: true
api_throttle_rate_limit: 1000
api_throttle_burst_limit: 2000
jwt_secret: "prod-jwt-secret-from-secrets-manager"
```

## Pre-Deployment Setup

### 1. Repository Setup

```bash
# Clone the repository
git clone https://github.com/company/multi-cloud-analytics.git
cd multi-cloud-analytics/lambda-cost-reporting-system

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r infrastructure/requirements.txt
```

### 2. AWS CLI Configuration

```bash
# Configure AWS CLI
aws configure
# Enter your AWS Access Key ID, Secret Access Key, Region, and Output format

# Verify configuration
aws sts get-caller-identity
```

### 3. CDK Bootstrap

```bash
# Bootstrap CDK in your account and region
cdk bootstrap aws://ACCOUNT-NUMBER/REGION

# For multiple regions (if needed)
cdk bootstrap aws://ACCOUNT-NUMBER/us-east-1
cdk bootstrap aws://ACCOUNT-NUMBER/us-west-2
```

### 4. Environment Variables

```bash
# Set environment variables
export CDK_DEFAULT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
export CDK_DEFAULT_REGION=us-east-1
export ENVIRONMENT=dev  # or staging, prod
```

## Deployment Process

### 1. Development Environment Deployment

```bash
# Navigate to infrastructure directory
cd infrastructure

# Set environment
export ENVIRONMENT=dev

# Synthesize the stack (optional - for validation)
cdk synth -a "python multi_cloud_app.py"

# Deploy the stack
cdk deploy -a "python multi_cloud_app.py" \
  --require-approval never \
  --outputs-file outputs-dev.json

# Verify deployment
aws cloudformation describe-stacks \
  --stack-name multi-cloud-analytics-dev \
  --query 'Stacks[0].StackStatus'
```

### 2. Staging Environment Deployment

```bash
# Set environment
export ENVIRONMENT=staging

# Deploy with additional validation
cdk deploy -a "python multi_cloud_app.py" \
  --require-approval never \
  --outputs-file outputs-staging.json \
  --progress events

# Run post-deployment tests
python ../tests/integration/test_staging_deployment.py
```

### 3. Production Environment Deployment

```bash
# Set environment
export ENVIRONMENT=prod

# Deploy with manual approval for safety
cdk deploy -a "python multi_cloud_app.py" \
  --require-approval broadening \
  --outputs-file outputs-prod.json \
  --progress events

# Verify critical components
./scripts/verify-production-deployment.sh
```

## Post-Deployment Configuration

### 1. Provider Credentials Setup

#### AWS Credentials
```bash
# Store AWS cross-account role information
aws secretsmanager create-secret \
  --name "multi-cloud-analytics-prod-aws-credentials" \
  --description "AWS provider credentials" \
  --secret-string '{
    "provider": "aws",
    "role_arn": "arn:aws:iam::CLIENT-ACCOUNT:role/MultiCloudAnalyticsRole",
    "external_id": "unique-external-id"
  }'
```

#### GCP Credentials
```bash
# Store GCP service account key
aws secretsmanager create-secret \
  --name "multi-cloud-analytics-prod-gcp-credentials" \
  --description "GCP provider credentials" \
  --secret-string '{
    "provider": "gcp",
    "service_account_key": "base64-encoded-key",
    "project_id": "client-project-id"
  }'
```

#### Azure Credentials
```bash
# Store Azure service principal credentials
aws secretsmanager create-secret \
  --name "multi-cloud-analytics-prod-azure-credentials" \
  --description "Azure provider credentials" \
  --secret-string '{
    "provider": "azure",
    "client_id": "azure-client-id",
    "client_secret": "azure-client-secret",
    "tenant_id": "azure-tenant-id",
    "subscription_id": "azure-subscription-id"
  }'
```

### 2. Initial Data Setup

```bash
# Create initial client configuration
python scripts/create-initial-client.py \
  --client-id "demo-client" \
  --organization-name "Demo Organization" \
  --providers "aws,gcp,azure"

# Trigger initial data collection
aws lambda invoke \
  --function-name multi-cloud-analytics-prod-cost-orchestrator \
  --payload '{"collection_type": "initial", "client_id": "demo-client"}' \
  response.json
```

### 3. Monitoring Setup

```bash
# Create SNS subscriptions for alerts
aws sns subscribe \
  --topic-arn "arn:aws:sns:us-east-1:123456789012:multi-cloud-analytics-prod-alerts" \
  --protocol email \
  --notification-endpoint ops-team@company.com

# Set up CloudWatch dashboard URLs
echo "Executive Dashboard: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=multi-cloud-analytics-prod-executive"
echo "Technical Dashboard: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=multi-cloud-analytics-prod-technical-ops"
```

## Deployment Validation

### 1. Infrastructure Validation

```bash
#!/bin/bash
# scripts/validate-deployment.sh

set -e

ENVIRONMENT=${1:-dev}
STACK_NAME="multi-cloud-analytics-${ENVIRONMENT}"

echo "Validating deployment for environment: $ENVIRONMENT"

# Check stack status
STACK_STATUS=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --query 'Stacks[0].StackStatus' \
  --output text)

if [ "$STACK_STATUS" != "CREATE_COMPLETE" ] && [ "$STACK_STATUS" != "UPDATE_COMPLETE" ]; then
  echo "ERROR: Stack status is $STACK_STATUS"
  exit 1
fi

echo "✓ CloudFormation stack is healthy"

# Check Lambda functions
FUNCTIONS=(
  "${STACK_NAME}-cost-orchestrator"
  "${STACK_NAME}-ai-insights"
  "${STACK_NAME}-api-handler"
  "${STACK_NAME}-webhook-handler"
)

for FUNCTION in "${FUNCTIONS[@]}"; do
  STATUS=$(aws lambda get-function \
    --function-name $FUNCTION \
    --query 'Configuration.State' \
    --output text 2>/dev/null || echo "NOT_FOUND")
  
  if [ "$STATUS" != "Active" ]; then
    echo "ERROR: Function $FUNCTION status is $STATUS"
    exit 1
  fi
  echo "✓ Lambda function $FUNCTION is active"
done

# Check DynamoDB tables
TABLES=(
  "${STACK_NAME}-cost-data"
  "${STACK_NAME}-timeseries"
  "${STACK_NAME}-clients"
)

for TABLE in "${TABLES[@]}"; do
  STATUS=$(aws dynamodb describe-table \
    --table-name $TABLE \
    --query 'Table.TableStatus' \
    --output text 2>/dev/null || echo "NOT_FOUND")
  
  if [ "$STATUS" != "ACTIVE" ]; then
    echo "ERROR: Table $TABLE status is $STATUS"
    exit 1
  fi
  echo "✓ DynamoDB table $TABLE is active"
done

# Check API Gateway
API_ID=$(aws apigateway get-rest-apis \
  --query "items[?name=='${STACK_NAME}-api'].id" \
  --output text)

if [ -z "$API_ID" ] || [ "$API_ID" == "None" ]; then
  echo "ERROR: API Gateway not found"
  exit 1
fi

echo "✓ API Gateway is deployed (ID: $API_ID)"

echo "All infrastructure components are healthy!"
```

### 2. Functional Validation

```python
# tests/integration/test_deployment.py
import boto3
import json
import requests
import pytest
from datetime import datetime, timedelta

class TestDeploymentValidation:
    
    def setup_method(self):
        self.lambda_client = boto3.client('lambda')
        self.dynamodb = boto3.resource('dynamodb')
        self.environment = os.environ.get('ENVIRONMENT', 'dev')
        self.stack_prefix = f"multi-cloud-analytics-{self.environment}"
    
    def test_cost_orchestrator_function(self):
        """Test cost orchestrator Lambda function"""
        function_name = f"{self.stack_prefix}-cost-orchestrator"
        
        # Test function invocation
        response = self.lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps({
                'collection_type': 'test',
                'providers': ['aws']
            })
        )
        
        assert response['StatusCode'] == 200
        
        # Parse response
        payload = json.loads(response['Payload'].read())
        assert 'statusCode' in payload
        assert payload['statusCode'] in [200, 202]
    
    def test_ai_insights_function(self):
        """Test AI insights Lambda function"""
        function_name = f"{self.stack_prefix}-ai-insights"
        
        response = self.lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps({
                'analysis_type': 'test',
                'client_id': 'test-client'
            })
        )
        
        assert response['StatusCode'] == 200
    
    def test_api_gateway_health(self):
        """Test API Gateway health endpoint"""
        # Get API Gateway URL from CloudFormation outputs
        cf_client = boto3.client('cloudformation')
        
        response = cf_client.describe_stacks(
            StackName=self.stack_prefix
        )
        
        outputs = response['Stacks'][0]['Outputs']
        api_url = next(
            output['OutputValue'] for output in outputs 
            if output['OutputKey'] == 'APIGatewayURL'
        )
        
        # Test health endpoint
        health_response = requests.get(f"{api_url}/v1/health")
        assert health_response.status_code == 200
    
    def test_dynamodb_tables(self):
        """Test DynamoDB table accessibility"""
        tables = [
            f"{self.stack_prefix}-cost-data",
            f"{self.stack_prefix}-timeseries",
            f"{self.stack_prefix}-clients"
        ]
        
        for table_name in tables:
            table = self.dynamodb.Table(table_name)
            
            # Test table scan (should not error)
            response = table.scan(Limit=1)
            assert 'Items' in response
    
    def test_monitoring_setup(self):
        """Test monitoring and alerting setup"""
        cloudwatch = boto3.client('cloudwatch')
        
        # Check for key alarms
        response = cloudwatch.describe_alarms(
            AlarmNamePrefix=self.stack_prefix
        )
        
        alarms = response['MetricAlarms']
        assert len(alarms) > 0
        
        # Check alarm states
        for alarm in alarms:
            assert alarm['StateValue'] in ['OK', 'INSUFFICIENT_DATA']
```

### 3. Performance Validation

```python
# tests/performance/test_load.py
import boto3
import json
import time
import concurrent.futures
from statistics import mean, median

def test_api_performance():
    """Test API performance under load"""
    api_url = get_api_url()
    
    def make_request():
        start_time = time.time()
        response = requests.get(f"{api_url}/v1/health")
        end_time = time.time()
        
        return {
            'status_code': response.status_code,
            'response_time': end_time - start_time
        }
    
    # Run concurrent requests
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(make_request) for _ in range(100)]
        results = [future.result() for future in futures]
    
    # Analyze results
    response_times = [r['response_time'] for r in results]
    success_rate = sum(1 for r in results if r['status_code'] == 200) / len(results)
    
    assert success_rate >= 0.95  # 95% success rate
    assert mean(response_times) < 2.0  # Average response time < 2s
    assert max(response_times) < 5.0  # Max response time < 5s
    
    print(f"Success rate: {success_rate:.2%}")
    print(f"Average response time: {mean(response_times):.3f}s")
    print(f"Median response time: {median(response_times):.3f}s")
    print(f"Max response time: {max(response_times):.3f}s")
```

## Rollback Procedures

### 1. Automated Rollback

```bash
#!/bin/bash
# scripts/rollback-deployment.sh

set -e

ENVIRONMENT=${1:-dev}
STACK_NAME="multi-cloud-analytics-${ENVIRONMENT}"

echo "Rolling back deployment for environment: $ENVIRONMENT"

# Get previous stack template
aws cloudformation get-template \
  --stack-name $STACK_NAME \
  --template-stage Processed \
  > previous-template.json

# Rollback using CloudFormation
aws cloudformation cancel-update-stack \
  --stack-name $STACK_NAME || true

# Wait for rollback to complete
aws cloudformation wait stack-update-complete \
  --stack-name $STACK_NAME

echo "Rollback completed successfully"
```

### 2. Manual Rollback Steps

1. **Identify Issues**
   - Check CloudWatch logs
   - Review error metrics
   - Identify failing components

2. **Stop Traffic**
   - Update Route 53 to redirect traffic
   - Disable API Gateway endpoints
   - Pause scheduled jobs

3. **Restore Previous Version**
   - Deploy previous CDK version
   - Restore database from backup
   - Update configuration

4. **Validate Rollback**
   - Run deployment validation tests
   - Check system health
   - Resume traffic gradually

## Monitoring and Alerting

### 1. Deployment Monitoring

```python
# scripts/monitor-deployment.py
import boto3
import time
from datetime import datetime, timedelta

def monitor_deployment(stack_name, timeout_minutes=30):
    """Monitor deployment progress and health"""
    cf_client = boto3.client('cloudformation')
    cw_client = boto3.client('cloudwatch')
    
    start_time = datetime.utcnow()
    timeout = start_time + timedelta(minutes=timeout_minutes)
    
    while datetime.utcnow() < timeout:
        # Check stack status
        response = cf_client.describe_stacks(StackName=stack_name)
        stack_status = response['Stacks'][0]['StackStatus']
        
        print(f"Stack status: {stack_status}")
        
        if stack_status in ['CREATE_COMPLETE', 'UPDATE_COMPLETE']:
            print("Deployment completed successfully!")
            break
        elif stack_status in ['CREATE_FAILED', 'UPDATE_FAILED', 'ROLLBACK_COMPLETE']:
            print(f"Deployment failed with status: {stack_status}")
            return False
        
        # Check for errors in CloudWatch
        error_count = get_error_count(cw_client, stack_name)
        if error_count > 10:
            print(f"High error count detected: {error_count}")
            return False
        
        time.sleep(30)
    
    return True

def get_error_count(cw_client, stack_name):
    """Get error count from CloudWatch metrics"""
    try:
        response = cw_client.get_metric_statistics(
            Namespace=f'MultiCloudAnalytics/{stack_name.split("-")[-1].title()}',
            MetricName='SystemErrors',
            StartTime=datetime.utcnow() - timedelta(minutes=10),
            EndTime=datetime.utcnow(),
            Period=300,
            Statistics=['Sum']
        )
        
        if response['Datapoints']:
            return sum(dp['Sum'] for dp in response['Datapoints'])
        return 0
    except Exception:
        return 0
```

### 2. Health Checks

```bash
#!/bin/bash
# scripts/health-check.sh

ENVIRONMENT=${1:-dev}
STACK_NAME="multi-cloud-analytics-${ENVIRONMENT}"

echo "Running health checks for $ENVIRONMENT environment..."

# Check Lambda function health
FUNCTIONS=(
  "${STACK_NAME}-cost-orchestrator"
  "${STACK_NAME}-ai-insights"
  "${STACK_NAME}-api-handler"
)

for FUNCTION in "${FUNCTIONS[@]}"; do
  echo "Testing $FUNCTION..."
  
  aws lambda invoke \
    --function-name $FUNCTION \
    --payload '{"test": true}' \
    --cli-read-timeout 30 \
    /tmp/response.json
  
  if [ $? -eq 0 ]; then
    echo "✓ $FUNCTION is healthy"
  else
    echo "✗ $FUNCTION failed health check"
    exit 1
  fi
done

# Check API Gateway
API_URL=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --query 'Stacks[0].Outputs[?OutputKey==`APIGatewayURL`].OutputValue' \
  --output text)

if [ -n "$API_URL" ]; then
  HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/v1/health")
  
  if [ "$HTTP_STATUS" -eq 200 ]; then
    echo "✓ API Gateway is healthy"
  else
    echo "✗ API Gateway health check failed (HTTP $HTTP_STATUS)"
    exit 1
  fi
fi

echo "All health checks passed!"
```

## Troubleshooting

### Common Deployment Issues

#### 1. CDK Bootstrap Issues
```bash
# Error: Need to perform AWS CDK bootstrap
cdk bootstrap aws://ACCOUNT/REGION

# Error: CDK version mismatch
npm install -g aws-cdk@latest
```

#### 2. Permission Issues
```bash
# Check current permissions
aws sts get-caller-identity
aws iam get-user

# Verify required permissions
aws iam simulate-principal-policy \
  --policy-source-arn $(aws sts get-caller-identity --query Arn --output text) \
  --action-names cloudformation:CreateStack \
  --resource-arns "*"
```

#### 3. Resource Limit Issues
```bash
# Check service quotas
aws service-quotas get-service-quota \
  --service-code lambda \
  --quota-code L-B99A9384  # Concurrent executions

# Request quota increase if needed
aws service-quotas request-service-quota-increase \
  --service-code lambda \
  --quota-code L-B99A9384 \
  --desired-value 1000
```

#### 4. Stack Update Issues
```bash
# Check stack events for errors
aws cloudformation describe-stack-events \
  --stack-name multi-cloud-analytics-prod \
  --query 'StackEvents[?ResourceStatus==`CREATE_FAILED`]'

# Cancel stuck update
aws cloudformation cancel-update-stack \
  --stack-name multi-cloud-analytics-prod
```

### Debugging Tools

#### 1. CloudFormation Drift Detection
```bash
# Detect configuration drift
aws cloudformation detect-stack-drift \
  --stack-name multi-cloud-analytics-prod

# Get drift results
aws cloudformation describe-stack-resource-drifts \
  --stack-name multi-cloud-analytics-prod
```

#### 2. Lambda Function Debugging
```bash
# Get function logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/multi-cloud-analytics-prod-cost-orchestrator \
  --start-time $(date -d '1 hour ago' +%s)000

# Test function locally
sam local invoke CostOrchestratorFunction \
  --event test-events/cost-collection.json
```

## Security Considerations

### 1. Secrets Management
- Use AWS Secrets Manager for sensitive data
- Rotate secrets regularly
- Implement least privilege access
- Encrypt secrets at rest and in transit

### 2. Network Security
- Use VPC endpoints where possible
- Implement security groups and NACLs
- Enable VPC Flow Logs
- Use WAF for API protection

### 3. Data Protection
- Encrypt all data at rest using KMS
- Use TLS 1.2+ for data in transit
- Implement field-level encryption
- Regular security audits

## Maintenance and Updates

### 1. Regular Updates
- Monthly security patches
- Quarterly feature updates
- Annual major version upgrades
- Continuous dependency updates

### 2. Backup and Recovery
- Daily automated backups
- Cross-region replication
- Disaster recovery testing
- Recovery time objectives (RTO < 4 hours)

### 3. Performance Optimization
- Monthly performance reviews
- Resource right-sizing
- Cost optimization
- Capacity planning

## Conclusion

This deployment guide provides comprehensive instructions for deploying the Multi-Cloud AI Cost Analytics system. Following these procedures ensures a secure, reliable, and scalable deployment across all environments.

For additional support or questions about the deployment process, please contact the platform engineering team at platform-eng@company.com.

Last updated: [Current Date]
Version: 1.0