# Lambda Cost Reporting System - Deployment Guide

This guide provides step-by-step instructions for deploying the Lambda Cost Reporting System from scratch or migrating from the existing aws-cost-agent-framework.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [Infrastructure Deployment](#infrastructure-deployment)
4. [Configuration Management](#configuration-management)
5. [Migration from Framework](#migration-from-framework)
6. [Testing and Validation](#testing-and-validation)
7. [Production Deployment](#production-deployment)
8. [Troubleshooting](#troubleshooting)

## Prerequisites

### AWS Account Requirements

- AWS account with administrative access
- AWS CLI configured with appropriate credentials
- AWS CDK v2 installed and bootstrapped
- Python 3.9+ installed
- Node.js 16+ installed (for CDK)

### Required AWS Services

The system uses the following AWS services:
- **AWS Lambda** - Main execution environment
- **Amazon DynamoDB** - Client configuration storage
- **Amazon S3** - Report and asset storage
- **Amazon EventBridge** - Scheduling
- **AWS SES** - Email delivery
- **AWS KMS** - Encryption
- **Amazon CloudWatch** - Monitoring and logging
- **AWS SNS** - Alerting

### IAM Permissions

Your deployment user/role needs permissions for:
- Lambda function management
- DynamoDB table operations
- S3 bucket operations
- EventBridge rule management
- SES configuration
- KMS key operations
- CloudWatch operations
- SNS topic operations

## Initial Setup

### 1. Clone and Setup Repository

```bash
# Clone the repository
git clone <repository-url>
cd lambda-cost-reporting-system

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 2. Environment Configuration

Create environment-specific configuration files:

```bash
# Copy example environment file
cp .env.example .env

# Edit configuration
nano .env
```

Required environment variables:

```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=123456789012

# Application Configuration
ENVIRONMENT=dev  # dev, staging, prod
TABLE_NAME=cost-reporting-clients-dev
S3_BUCKET=cost-reporting-assets-dev
KMS_KEY_ALIAS=alias/cost-reporting-dev

# Email Configuration
SES_REGION=us-east-1
FROM_EMAIL=reports@yourcompany.com

# Monitoring Configuration
SNS_TOPIC_ARN=arn:aws:sns:us-east-1:123456789012:cost-reporting-alerts-dev
```

### 3. AWS CDK Bootstrap

If not already done, bootstrap CDK in your account:

```bash
# Bootstrap CDK (one-time per account/region)
cdk bootstrap aws://123456789012/us-east-1
```

## Infrastructure Deployment

### 1. Deploy Base Infrastructure

```bash
# Navigate to infrastructure directory
cd infrastructure

# Install CDK dependencies
npm install

# Review the deployment plan
cdk diff

# Deploy the infrastructure
cdk deploy --all
```

This will create:
- Lambda function with proper IAM roles
- DynamoDB table with indexes
- S3 bucket with lifecycle policies
- EventBridge rules for scheduling
- KMS key for encryption
- CloudWatch alarms and dashboards
- SNS topic for alerts

### 2. Verify Infrastructure Deployment

```bash
# Check Lambda function
aws lambda get-function --function-name cost-reporting-lambda-dev

# Check DynamoDB table
aws dynamodb describe-table --table-name cost-reporting-clients-dev

# Check S3 bucket
aws s3 ls s3://cost-reporting-assets-dev

# Check EventBridge rules
aws events list-rules --name-prefix cost-reporting
```

### 3. Configure SES (Email Service)

```bash
# Verify email addresses for SES
aws ses verify-email-identity --email-address reports@yourcompany.com

# Check verification status
aws ses get-identity-verification-attributes --identities reports@yourcompany.com

# For production, request SES production access
# https://docs.aws.amazon.com/ses/latest/dg/request-production-access.html
```

## Configuration Management

### 1. Client Configuration

Use the CLI tools to manage client configurations:

```bash
# Create sample configuration
python cli/client_manager.py sample-config --output sample-client.json

# Edit the configuration file
nano sample-client.json

# Add client to system
python cli/client_manager.py add --config sample-client.json

# List all clients
python cli/client_manager.py list

# Validate client configuration
python cli/client_manager.py validate --client-id <client-id>
```

### 2. Bulk Client Import

For multiple clients:

```bash
# Create clients configuration file
cat > clients.json << EOF
[
  {
    "client_name": "Company A",
    "aws_accounts": [
      {
        "account_id": "111111111111",
        "access_key_id": "AKIA...",
        "secret_access_key": "...",
        "region": "us-east-1",
        "account_name": "Production"
      }
    ],
    "report_config": {
      "recipients": ["admin@companya.com"],
      "weekly_enabled": true,
      "monthly_enabled": true
    },
    "branding": {
      "company_name": "Company A",
      "primary_color": "#1f2937"
    }
  }
]
EOF

# Import clients
python cli/client_manager.py import --input clients.json
```

## Migration from Framework

### 1. Prepare Migration

```bash
# Ensure aws-cost-agent-framework is accessible
ls ../aws-cost-agent-framework

# Create migration directory
mkdir migration_output
```

### 2. Run Migration

```bash
# Migrate configurations with backup
python scripts/migrate_from_framework.py migrate \
  --framework-path ../aws-cost-agent-framework \
  --output-dir migration_output

# Validate migrated configurations
python scripts/validate_migration.py \
  --config-dir migration_output \
  --check-aws \
  --report migration_validation.md
```

### 3. Review Migration Results

```bash
# Check migration report
cat migration_output/migration_report.json

# Review validation report
cat migration_validation.md

# Import migrated configurations
python cli/client_manager.py import \
  --input migration_output/*.json \
  --update-existing
```

### 4. Manual Configuration Updates

Review and update any configurations that need manual attention:

- Replace placeholder credentials
- Convert profile-based configurations to access keys
- Update email recipients
- Verify AWS account IDs
- Update branding information

## Testing and Validation

### 1. Unit Tests

```bash
# Run unit tests
python -m pytest tests/unit/ -v

# Run with coverage
python -m pytest tests/unit/ --cov=src --cov-report=html
```

### 2. Integration Tests

```bash
# Run integration tests (requires AWS access)
python -m pytest tests/integration/ -v

# Test specific components
python -m pytest tests/integration/test_client_config_manager.py -v
```

### 3. End-to-End Testing

```bash
# Test Lambda function locally
python -m pytest tests/e2e/ -v

# Test with sample data
python examples/main_handler_example.py
```

### 4. Manual Testing

```bash
# Test client configuration
python cli/client_manager.py validate --client-id <client-id>

# Test report generation
aws lambda invoke \
  --function-name cost-reporting-lambda-dev \
  --payload '{"test": true, "client_id": "<client-id>"}' \
  response.json

# Check logs
aws logs tail /aws/lambda/cost-reporting-lambda-dev --follow
```

## Production Deployment

### 1. Environment Preparation

```bash
# Create production environment file
cp .env .env.prod

# Update production settings
nano .env.prod
```

Production environment variables:

```bash
ENVIRONMENT=prod
TABLE_NAME=cost-reporting-clients
S3_BUCKET=cost-reporting-assets
KMS_KEY_ALIAS=alias/cost-reporting
SNS_TOPIC_ARN=arn:aws:sns:us-east-1:123456789012:cost-reporting-alerts
```

### 2. Production Infrastructure

```bash
# Deploy production infrastructure
export ENVIRONMENT=prod
cdk deploy --all --require-approval never

# Verify production deployment
aws lambda get-function --function-name cost-reporting-lambda
```

### 3. Production Configuration

```bash
# Set production table name
export TABLE_NAME=cost-reporting-clients

# Import production client configurations
python cli/client_manager.py import \
  --input production_clients.json \
  --table-name cost-reporting-clients
```

### 4. Monitoring Setup

```bash
# Create CloudWatch dashboard
aws cloudwatch put-dashboard \
  --dashboard-name "Cost-Reporting-System" \
  --dashboard-body file://infrastructure/monitoring/dashboard.json

# Test alerting
aws sns publish \
  --topic-arn arn:aws:sns:us-east-1:123456789012:cost-reporting-alerts \
  --message "Test alert from Cost Reporting System"
```

### 5. Schedule Activation

The EventBridge rules are automatically created and activated. Verify scheduling:

```bash
# Check EventBridge rules
aws events list-rules --name-prefix cost-reporting

# Check rule targets
aws events list-targets-by-rule --rule cost-reporting-weekly-schedule
aws events list-targets-by-rule --rule cost-reporting-monthly-schedule
```

## Post-Deployment Verification

### 1. System Health Check

```bash
# Check all components
python scripts/health_check.py --environment prod

# Verify Lambda function
aws lambda invoke \
  --function-name cost-reporting-lambda \
  --payload '{"health_check": true}' \
  health_response.json

cat health_response.json
```

### 2. Test Report Generation

```bash
# Trigger test report for a client
aws lambda invoke \
  --function-name cost-reporting-lambda \
  --payload '{"test_report": true, "client_id": "<client-id>"}' \
  test_response.json

# Check S3 for generated reports
aws s3 ls s3://cost-reporting-assets/reports/
```

### 3. Monitor First Scheduled Execution

```bash
# Monitor CloudWatch logs
aws logs tail /aws/lambda/cost-reporting-lambda --follow

# Check execution metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=cost-reporting-lambda \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 3600 \
  --statistics Sum
```

## Security Considerations

### 1. Credential Management

- Use KMS encryption for sensitive data
- Rotate AWS access keys regularly
- Use least privilege IAM policies
- Enable CloudTrail for audit logging

### 2. Network Security

- Lambda functions run in AWS managed VPC
- S3 bucket has restricted access policies
- DynamoDB uses encryption at rest
- SES uses TLS for email delivery

### 3. Data Protection

- All sensitive data encrypted with KMS
- S3 objects have lifecycle policies
- DynamoDB has point-in-time recovery enabled
- CloudWatch logs have retention policies

## Maintenance and Updates

### 1. Regular Maintenance

- Monitor CloudWatch alarms
- Review and rotate credentials
- Update Lambda function code
- Clean up old reports in S3

### 2. System Updates

```bash
# Update Lambda function code
cd infrastructure
cdk deploy LambdaCostReportingStack

# Update client configurations
python cli/client_manager.py update --client-id <id> --config updated-config.json

# Update infrastructure
cdk diff
cdk deploy --all
```

### 3. Backup and Recovery

- DynamoDB has point-in-time recovery enabled
- S3 has versioning enabled
- Lambda function code is in version control
- Infrastructure is defined as code

## Troubleshooting

See [troubleshooting-guide.md](troubleshooting-guide.md) for detailed troubleshooting procedures.

## Support and Documentation

- [API Documentation](api-documentation.md)
- [Operational Runbooks](operational-runbooks.md)
- [Monitoring Guide](monitoring-setup.md)
- [Client Onboarding Guide](client-onboarding-guide.md)

## Deployment Validation Checklist

After deployment, verify the following:

### Infrastructure Validation
- [ ] Lambda function deployed and accessible
- [ ] DynamoDB table created with proper indexes
- [ ] S3 bucket created with lifecycle policies
- [ ] EventBridge rules created and enabled
- [ ] KMS key created and accessible
- [ ] CloudWatch alarms configured
- [ ] SNS topic created for alerts
- [ ] IAM roles and policies properly configured

### Functional Validation
- [ ] CLI tools working correctly
- [ ] Client configuration validation working
- [ ] Test report generation successful
- [ ] Email delivery functional
- [ ] Monitoring and alerting operational
- [ ] Scheduled execution working

### Security Validation
- [ ] All credentials encrypted with KMS
- [ ] IAM policies follow least privilege
- [ ] S3 bucket policies restrictive
- [ ] CloudTrail logging enabled
- [ ] VPC configuration (if applicable)

## Environment-Specific Configurations

### Development Environment
```bash
# Development-specific settings
ENVIRONMENT=dev
LOG_LEVEL=DEBUG
ENABLE_DETAILED_MONITORING=true
RETENTION_DAYS=7
SCHEDULE_ENABLED=false  # Manual testing only
```

### Staging Environment
```bash
# Staging-specific settings
ENVIRONMENT=staging
LOG_LEVEL=INFO
ENABLE_DETAILED_MONITORING=true
RETENTION_DAYS=30
SCHEDULE_ENABLED=true
WEEKLY_SCHEDULE="cron(0 9 ? * MON *)"  # Every Monday at 9 AM
MONTHLY_SCHEDULE="cron(0 8 1 * ? *)"   # 1st of month at 8 AM
```

### Production Environment
```bash
# Production-specific settings
ENVIRONMENT=prod
LOG_LEVEL=WARN
ENABLE_DETAILED_MONITORING=true
RETENTION_DAYS=90
SCHEDULE_ENABLED=true
WEEKLY_SCHEDULE="cron(0 9 ? * MON *)"  # Every Monday at 9 AM
MONTHLY_SCHEDULE="cron(0 8 1 * ? *)"   # 1st of month at 8 AM
BACKUP_ENABLED=true
```

## Disaster Recovery Procedures

### Backup Strategy
1. **DynamoDB**: Point-in-time recovery enabled automatically
2. **S3**: Versioning and cross-region replication configured
3. **Lambda**: Code stored in version control and S3
4. **Infrastructure**: CDK code in version control

### Recovery Procedures

#### Complete System Recovery
```bash
# 1. Restore infrastructure
cd infrastructure
cdk deploy --all

# 2. Restore DynamoDB data (if needed)
aws dynamodb restore-table-from-backup \
  --target-table-name cost-reporting-clients \
  --backup-arn arn:aws:dynamodb:region:account:table/cost-reporting-clients/backup/backup-name

# 3. Restore S3 data (if needed)
aws s3 sync s3://backup-bucket/cost-reporting-assets/ s3://cost-reporting-assets/

# 4. Validate system health
python scripts/health_check.py --environment prod
```

#### Partial Recovery (Lambda Only)
```bash
# Redeploy Lambda function
cd infrastructure
cdk deploy LambdaCostReportingStack

# Verify function
aws lambda invoke \
  --function-name cost-reporting-lambda \
  --payload '{"health_check": true}' \
  response.json
```

## Performance Tuning

### Lambda Optimization
```bash
# Monitor and adjust based on metrics
aws lambda update-function-configuration \
  --function-name cost-reporting-lambda \
  --memory-size 1536 \
  --timeout 900 \
  --reserved-concurrent-executions 5
```

### DynamoDB Optimization
```bash
# Enable auto-scaling
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id table/cost-reporting-clients \
  --scalable-dimension dynamodb:table:ReadCapacityUnits \
  --min-capacity 5 \
  --max-capacity 100
```

### Cost Optimization
- Use S3 Intelligent Tiering for report storage
- Configure DynamoDB on-demand billing for variable workloads
- Set up S3 lifecycle policies to delete old reports
- Monitor and optimize Lambda memory allocation

## Next Steps

After successful deployment:

1. **Set up monitoring dashboards** - Follow [monitoring-setup.md](monitoring-setup.md)
2. **Configure alerting thresholds** - See [alerting-runbooks.md](alerting-runbooks.md)
3. **Train operations team** - Use [operational-runbooks.md](operational-runbooks.md)
4. **Document client onboarding process** - Follow [client-onboarding-guide.md](client-onboarding-guide.md)
5. **Plan regular maintenance schedule** - See maintenance section in operational runbooks
6. **Set up disaster recovery testing** - Schedule quarterly DR tests
7. **Implement security scanning** - Set up automated security scans
8. **Plan capacity scaling** - Monitor usage and plan for growth