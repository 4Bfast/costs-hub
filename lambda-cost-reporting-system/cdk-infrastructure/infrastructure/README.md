# Infrastructure

This directory contains AWS CDK infrastructure code for the Lambda Cost Reporting System.

## Prerequisites

- AWS CLI configured with appropriate permissions
- Python 3.9+
- Node.js 18+ (for CDK CLI)

## Setup

1. Install CDK CLI:
```bash
npm install -g aws-cdk
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Bootstrap CDK (first time only):
```bash
cdk bootstrap
```

## Deployment

### Development Environment
```bash
export ENVIRONMENT=dev
cdk deploy
```

### Staging Environment
```bash
export ENVIRONMENT=staging
cdk deploy
```

### Production Environment
```bash
export ENVIRONMENT=prod
cdk deploy
```

## Environment Variables

- `ENVIRONMENT`: Environment name (dev, staging, prod)
- `CDK_DEFAULT_ACCOUNT`: AWS account ID
- `CDK_DEFAULT_REGION`: AWS region (defaults to us-east-1)

## Resources Created

- **Lambda Function**: Main cost reporting handler
- **DynamoDB Table**: Client configurations storage
- **S3 Bucket**: Reports and assets storage
- **EventBridge Rules**: Scheduled execution triggers
- **KMS Key**: Encryption for sensitive data
- **SNS Topic**: Admin alerts and notifications
- **CloudWatch Alarms**: Monitoring and alerting
- **IAM Roles**: Least privilege access policies

## Useful Commands

- `cdk ls` - List all stacks
- `cdk synth` - Synthesize CloudFormation template
- `cdk diff` - Compare deployed stack with current state
- `cdk deploy` - Deploy stack
- `cdk destroy` - Delete stack