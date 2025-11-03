# Troubleshooting Guide

## Overview

This guide provides solutions to common issues encountered during client onboarding and system operation of the Lambda Cost Reporting System.

## Table of Contents

1. [Client Onboarding Issues](#client-onboarding-issues)
2. [AWS Access and Permission Issues](#aws-access-and-permission-issues)
3. [Configuration Validation Errors](#configuration-validation-errors)
4. [Report Generation Issues](#report-generation-issues)
5. [Email Delivery Problems](#email-delivery-problems)
6. [System Performance Issues](#system-performance-issues)
7. [Data Accuracy Issues](#data-accuracy-issues)
8. [CLI Tool Issues](#cli-tool-issues)
9. [Infrastructure Issues](#infrastructure-issues)
10. [Monitoring and Alerting Issues](#monitoring-and-alerting-issues)

## Client Onboarding Issues

### Issue: Client Configuration Validation Fails

**Symptoms:**
- CLI returns validation errors when adding a client
- Configuration file appears correct but validation fails

**Common Causes:**
1. Invalid JSON format
2. Missing required fields
3. Invalid email addresses
4. Invalid AWS account ID format
5. Invalid color codes in branding

**Solutions:**

1. **Validate JSON Format:**
   ```bash
   # Use jq to validate JSON syntax
   jq . client-config.json
   
   # Or use Python
   python -m json.tool client-config.json
   ```

2. **Check Required Fields:**
   ```bash
   # Generate sample config for reference
   python cli/main.py client sample-config --output sample.json
   ```

3. **Validate Email Addresses:**
   ```python
   import re
   email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
   print(email_pattern.match("test@example.com"))  # Should return match object
   ```

4. **Validate AWS Account ID:**
   - Must be exactly 12 digits
   - No spaces or special characters
   - Example: `123456789012`

5. **Validate Color Codes:**
   - Must be hex format: `#RRGGBB`
   - Example: `#1f2937`, `#f59e0b`

### Issue: Client Already Exists Error

**Symptoms:**
- Error message: "Client with ID already exists"
- Cannot add client with specific ID

**Solutions:**

1. **Check Existing Clients:**
   ```bash
   python cli/main.py client list
   ```

2. **Use Update Instead of Add:**
   ```bash
   python cli/main.py client update --client-id CLIENT_ID --config updated-config.json
   ```

3. **Generate New Client ID:**
   - Remove `client_id` field from config file
   - System will auto-generate a new UUID

### Issue: Multiple AWS Accounts Configuration

**Symptoms:**
- Confusion about how to configure multiple AWS accounts
- Reports not showing all accounts

**Solutions:**

1. **Correct Multi-Account Format:**
   ```json
   {
     "aws_accounts": [
       {
         "account_id": "111111111111",
         "access_key_id": "AKIA...",
         "secret_access_key": "...",
         "region": "us-east-1",
         "account_name": "Production"
       },
       {
         "account_id": "222222222222",
         "access_key_id": "AKIA...",
         "secret_access_key": "...",
         "region": "us-west-2",
         "account_name": "Development"
       }
     ]
   }
   ```

2. **Verify Each Account Separately:**
   ```bash
   # Test each account's credentials individually
   aws configure set aws_access_key_id AKIA...
   aws configure set aws_secret_access_key ...
   aws ce get-cost-and-usage --time-period Start=2023-01-01,End=2023-01-31 --granularity MONTHLY --metrics BlendedCost
   ```

## AWS Access and Permission Issues

### Issue: Access Denied Errors

**Symptoms:**
- Error: "User is not authorized to perform: ce:GetCostAndUsage"
- AWS API calls fail with 403 Forbidden

**Solutions:**

1. **Verify IAM Policy:**
   ```bash
   # Check attached policies
   aws iam list-attached-user-policies --user-name cost-reporting-user
   
   # Get policy document
   aws iam get-policy-version --policy-arn POLICY_ARN --version-id v1
   ```

2. **Test Permissions:**
   ```bash
   # Test Cost Explorer access
   aws ce get-cost-and-usage \
     --time-period Start=2023-01-01,End=2023-01-31 \
     --granularity MONTHLY \
     --metrics BlendedCost
   ```

3. **Apply Correct Policy:**
   - Use policies from [AWS IAM Policy Templates](aws-iam-policy-templates.md)
   - Ensure policy is attached to the correct user/role

### Issue: Invalid Access Keys

**Symptoms:**
- Error: "The AWS Access Key Id you provided does not exist in our records"
- Authentication failures

**Solutions:**

1. **Verify Access Keys:**
   ```bash
   # Test with AWS CLI
   aws sts get-caller-identity
   ```

2. **Check Key Status:**
   ```bash
   # List access keys for user
   aws iam list-access-keys --user-name cost-reporting-user
   ```

3. **Rotate Keys if Needed:**
   ```bash
   # Create new access key
   aws iam create-access-key --user-name cost-reporting-user
   
   # Delete old access key (after updating configuration)
   aws iam delete-access-key --user-name cost-reporting-user --access-key-id OLD_KEY_ID
   ```

### Issue: Cross-Account Role Assumption Fails

**Symptoms:**
- Error: "User is not authorized to perform: sts:AssumeRole"
- Cross-account access not working

**Solutions:**

1. **Verify Trust Policy:**
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Principal": {
           "AWS": "arn:aws:iam::LAMBDA_ACCOUNT_ID:role/lambda-cost-reporting-role"
         },
         "Action": "sts:AssumeRole",
         "Condition": {
           "StringEquals": {
             "sts:ExternalId": "unique-external-id"
           }
         }
       }
     ]
   }
   ```

2. **Test Role Assumption:**
   ```bash
   aws sts assume-role \
     --role-arn arn:aws:iam::CLIENT_ACCOUNT:role/cost-reporting-role \
     --role-session-name test-session \
     --external-id unique-external-id
   ```

3. **Check External ID:**
   - Ensure external ID in trust policy matches configuration
   - External ID should be unique per client

## Configuration Validation Errors

### Issue: Email Validation Fails

**Symptoms:**
- Error: "Invalid email address format"
- Email addresses appear correct

**Solutions:**

1. **Check Email Format:**
   - Must follow standard email format: `user@domain.com`
   - No spaces or special characters except allowed ones
   - Domain must have valid TLD

2. **Common Email Issues:**
   ```bash
   # Invalid examples:
   "user@domain"           # Missing TLD
   "user @domain.com"      # Space in email
   "user@domain..com"      # Double dots
   
   # Valid examples:
   "user@domain.com"
   "user.name@domain.co.uk"
   "user+tag@domain.org"
   ```

### Issue: Threshold Configuration Errors

**Symptoms:**
- Error: "threshold must be non-negative"
- Threshold values not working as expected

**Solutions:**

1. **Validate Threshold Values:**
   ```json
   {
     "report_config": {
       "threshold": 1000.0,  // Must be positive number
       "alert_thresholds": [
         {
           "name": "High Cost Alert",
           "threshold_type": "absolute",
           "value": 5000.0,
           "severity": "high"
         }
       ]
     }
   }
   ```

2. **Check Threshold Types:**
   - `absolute`: Dollar amount (e.g., 1000.0)
   - `percentage`: Percentage increase (e.g., 20.0 for 20%)

### Issue: Branding Configuration Problems

**Symptoms:**
- Error: "Invalid color format"
- Logo not appearing in reports

**Solutions:**

1. **Validate Color Codes:**
   ```json
   {
     "branding": {
       "primary_color": "#1f2937",    // Must start with # and be 6 hex digits
       "secondary_color": "#f59e0b"   // Case insensitive
     }
   }
   ```

2. **Logo Upload Issues:**
   ```bash
   # Upload logo to S3 first
   aws s3 cp logo.png s3://cost-reporting-assets/client-logos/CLIENT_ID/logo.png
   
   # Then reference in config
   "logo_s3_key": "client-logos/CLIENT_ID/logo.png"
   ```

## Report Generation Issues

### Issue: Reports Not Generated

**Symptoms:**
- No reports received by email
- Lambda function executes but no output

**Solutions:**

1. **Check Lambda Logs:**
   ```bash
   # View recent logs
   aws logs describe-log-groups --log-group-name-prefix /aws/lambda/cost-reporting
   
   # Get specific log stream
   aws logs get-log-events --log-group-name LOG_GROUP --log-stream-name LOG_STREAM
   ```

2. **Verify Client Status:**
   ```bash
   python cli/main.py client list --status active
   ```

3. **Test Manual Execution:**
   ```bash
   # Validate specific client
   python cli/main.py client validate --client-id CLIENT_ID
   ```

### Issue: Incomplete Cost Data

**Symptoms:**
- Reports show partial data
- Some AWS services missing from reports

**Solutions:**

1. **Check Cost Explorer Permissions:**
   - Ensure all required Cost Explorer permissions are granted
   - Verify access to all AWS services

2. **Verify Date Ranges:**
   - Cost data may have delays (up to 24 hours)
   - Check if requesting data for current day

3. **Check Account Access:**
   ```bash
   # Test cost data retrieval
   aws ce get-cost-and-usage \
     --time-period Start=2023-01-01,End=2023-01-31 \
     --granularity MONTHLY \
     --metrics BlendedCost \
     --group-by Type=DIMENSION,Key=SERVICE
   ```

### Issue: Report Formatting Problems

**Symptoms:**
- HTML reports look broken
- Branding not applied correctly

**Solutions:**

1. **Check S3 Asset Access:**
   ```bash
   # Verify logo exists and is accessible
   aws s3 ls s3://cost-reporting-assets/client-logos/CLIENT_ID/
   ```

2. **Validate HTML Generation:**
   - Check Lambda logs for HTML generation errors
   - Verify template files are present

3. **Test Email Template:**
   - Generate test report manually
   - Check email HTML rendering

## Email Delivery Problems

### Issue: Emails Not Delivered

**Symptoms:**
- Reports generated but emails not received
- No delivery errors in logs

**Solutions:**

1. **Check SES Configuration:**
   ```bash
   # Verify SES sending statistics
   aws ses get-send-statistics
   
   # Check sending quota
   aws ses get-send-quota
   ```

2. **Verify Email Addresses:**
   ```bash
   # Check if email addresses are verified (for sandbox)
   aws ses list-verified-email-addresses
   ```

3. **Check Spam Filters:**
   - Ask recipients to check spam/junk folders
   - Verify sender reputation
   - Consider SPF/DKIM configuration

### Issue: SES Sandbox Limitations

**Symptoms:**
- Can only send to verified email addresses
- Limited sending quota

**Solutions:**

1. **Request Production Access:**
   ```bash
   # Submit request to move out of sandbox
   aws ses put-account-sending-enabled --enabled
   ```

2. **Verify Email Addresses (Temporary):**
   ```bash
   # Verify recipient email addresses
   aws ses verify-email-identity --email-address recipient@example.com
   ```

### Issue: Email Bounces or Complaints

**Symptoms:**
- High bounce rate
- Complaint notifications

**Solutions:**

1. **Monitor Bounce/Complaint Rates:**
   ```bash
   # Check reputation metrics
   aws ses get-reputation --identity sender@yourdomain.com
   ```

2. **Clean Email Lists:**
   - Remove invalid email addresses
   - Implement bounce handling
   - Use double opt-in for new recipients

## System Performance Issues

### Issue: Lambda Timeout Errors

**Symptoms:**
- Error: "Task timed out after X seconds"
- Incomplete report generation

**Solutions:**

1. **Increase Lambda Timeout:**
   ```bash
   # Update Lambda configuration
   aws lambda update-function-configuration \
     --function-name cost-reporting-function \
     --timeout 900  # 15 minutes (maximum)
   ```

2. **Optimize Processing:**
   - Process clients in smaller batches
   - Implement parallel processing
   - Cache frequently accessed data

3. **Monitor Memory Usage:**
   ```bash
   # Increase memory if needed
   aws lambda update-function-configuration \
     --function-name cost-reporting-function \
     --memory-size 1024  # MB
   ```

### Issue: DynamoDB Throttling

**Symptoms:**
- Error: "ProvisionedThroughputExceededException"
- Slow client configuration access

**Solutions:**

1. **Enable Auto Scaling:**
   ```bash
   # Enable auto scaling for table
   aws application-autoscaling register-scalable-target \
     --service-namespace dynamodb \
     --resource-id table/cost-reporting-clients \
     --scalable-dimension dynamodb:table:ReadCapacityUnits \
     --min-capacity 5 \
     --max-capacity 100
   ```

2. **Use On-Demand Billing:**
   ```bash
   # Switch to on-demand billing
   aws dynamodb modify-table \
     --table-name cost-reporting-clients \
     --billing-mode PAY_PER_REQUEST
   ```

### Issue: S3 Access Errors

**Symptoms:**
- Error: "Access Denied" when accessing S3
- Reports not stored properly

**Solutions:**

1. **Check S3 Permissions:**
   ```bash
   # Verify bucket policy
   aws s3api get-bucket-policy --bucket cost-reporting-assets
   ```

2. **Test S3 Access:**
   ```bash
   # Test upload
   echo "test" | aws s3 cp - s3://cost-reporting-assets/test.txt
   
   # Test download
   aws s3 cp s3://cost-reporting-assets/test.txt -
   ```

## Data Accuracy Issues

### Issue: Cost Data Discrepancies

**Symptoms:**
- Reports show different costs than AWS Console
- Missing cost data for some services

**Solutions:**

1. **Verify Time Zones:**
   - Ensure consistent time zone usage (UTC recommended)
   - Check for daylight saving time issues

2. **Check Data Freshness:**
   - Cost data has 24-48 hour delay
   - Don't request current day data

3. **Validate Filters:**
   ```bash
   # Test without filters first
   aws ce get-cost-and-usage \
     --time-period Start=2023-01-01,End=2023-01-31 \
     --granularity MONTHLY \
     --metrics BlendedCost
   ```

### Issue: Multi-Account Aggregation Problems

**Symptoms:**
- Total costs don't match sum of individual accounts
- Some accounts missing from aggregated data

**Solutions:**

1. **Verify All Account Access:**
   ```bash
   # Test each account individually
   for account in account1 account2 account3; do
     echo "Testing $account"
     # Test with specific account credentials
   done
   ```

2. **Check Account Permissions:**
   - Ensure all accounts have proper Cost Explorer access
   - Verify credentials are valid for each account

## CLI Tool Issues

### Issue: CLI Command Not Found

**Symptoms:**
- Error: "command not found"
- Python import errors

**Solutions:**

1. **Check Python Path:**
   ```bash
   # Ensure src directory is in Python path
   export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
   ```

2. **Install Dependencies:**
   ```bash
   # Install required packages
   pip install -r requirements.txt
   ```

3. **Use Full Path:**
   ```bash
   # Use full path to CLI
   python /full/path/to/cli/main.py client list
   ```

### Issue: AWS Credentials Not Found

**Symptoms:**
- Error: "Unable to locate credentials"
- AWS API calls fail

**Solutions:**

1. **Configure AWS Credentials:**
   ```bash
   # Set up AWS credentials
   aws configure
   
   # Or use environment variables
   export AWS_ACCESS_KEY_ID=your_key
   export AWS_SECRET_ACCESS_KEY=your_secret
   export AWS_DEFAULT_REGION=us-east-1
   ```

2. **Use IAM Role:**
   ```bash
   # If running on EC2, ensure IAM role is attached
   aws sts get-caller-identity
   ```

## Infrastructure Issues

### Issue: CloudFormation/CDK Deployment Fails

**Symptoms:**
- Stack creation fails
- Resource creation errors

**Solutions:**

1. **Check IAM Permissions:**
   - Ensure deployment role has necessary permissions
   - Verify CloudFormation permissions

2. **Review Stack Events:**
   ```bash
   # Check stack events for errors
   aws cloudformation describe-stack-events --stack-name cost-reporting-stack
   ```

3. **Validate Template:**
   ```bash
   # Validate CloudFormation template
   aws cloudformation validate-template --template-body file://template.yaml
   ```

### Issue: EventBridge Rules Not Triggering

**Symptoms:**
- Scheduled reports not running
- Lambda not invoked on schedule

**Solutions:**

1. **Check EventBridge Rules:**
   ```bash
   # List rules
   aws events list-rules --name-prefix cost-reporting
   
   # Check rule details
   aws events describe-rule --name cost-reporting-weekly
   ```

2. **Verify Lambda Permissions:**
   ```bash
   # Check if EventBridge can invoke Lambda
   aws lambda get-policy --function-name cost-reporting-function
   ```

3. **Test Manual Invocation:**
   ```bash
   # Manually invoke Lambda
   aws lambda invoke \
     --function-name cost-reporting-function \
     --payload '{"source": "manual-test"}' \
     response.json
   ```

## Monitoring and Alerting Issues

### Issue: CloudWatch Alarms Not Triggering

**Symptoms:**
- No alerts received despite issues
- Alarms in "INSUFFICIENT_DATA" state

**Solutions:**

1. **Check Alarm Configuration:**
   ```bash
   # Describe alarm
   aws cloudwatch describe-alarms --alarm-names cost-reporting-failures
   ```

2. **Verify Metrics:**
   ```bash
   # Check if metrics are being published
   aws cloudwatch get-metric-statistics \
     --namespace AWS/Lambda \
     --metric-name Errors \
     --dimensions Name=FunctionName,Value=cost-reporting-function \
     --start-time 2023-01-01T00:00:00Z \
     --end-time 2023-01-02T00:00:00Z \
     --period 3600 \
     --statistics Sum
   ```

3. **Test SNS Notifications:**
   ```bash
   # Test SNS topic
   aws sns publish \
     --topic-arn arn:aws:sns:region:account:cost-reporting-alerts \
     --message "Test notification"
   ```

### Issue: Log Analysis Problems

**Symptoms:**
- Cannot find relevant logs
- Log retention issues

**Solutions:**

1. **Check Log Groups:**
   ```bash
   # List log groups
   aws logs describe-log-groups --log-group-name-prefix /aws/lambda/cost-reporting
   ```

2. **Set Log Retention:**
   ```bash
   # Set retention period
   aws logs put-retention-policy \
     --log-group-name /aws/lambda/cost-reporting-function \
     --retention-in-days 30
   ```

3. **Use CloudWatch Insights:**
   ```bash
   # Query logs with CloudWatch Insights
   aws logs start-query \
     --log-group-name /aws/lambda/cost-reporting-function \
     --start-time 1609459200 \
     --end-time 1609545600 \
     --query-string 'fields @timestamp, @message | filter @message like /ERROR/'
   ```

## Advanced Troubleshooting

### Lambda Runtime Issues

#### Issue: Import Module Errors
**Symptoms:**
- Error: "Unable to import module 'handlers.main': No module named 'module_name'"
- Lambda function fails to start

**Solutions:**

1. **Check Dependencies:**
   ```bash
   # Verify requirements.txt includes all dependencies
   cd lambda-cost-reporting-system
   cat requirements.txt
   
   # Check if dependencies are installed in deployment package
   aws lambda get-function --function-name cost-reporting-dev-handler --query 'Code.Location'
   ```

2. **Redeploy with Dependencies:**
   ```bash
   # Redeploy Lambda function
   cd infrastructure
   cdk deploy LambdaCostReportingStack
   ```

3. **Check Layer Configuration:**
   ```bash
   # Verify Lambda layers
   aws lambda get-function-configuration --function-name cost-reporting-dev-handler --query 'Layers'
   ```

#### Issue: Lambda Cold Start Performance
**Symptoms:**
- First execution takes significantly longer
- Timeout errors on initial invocations

**Solutions:**

1. **Increase Memory:**
   ```bash
   aws lambda update-function-configuration \
     --function-name cost-reporting-dev-handler \
     --memory-size 1024
   ```

2. **Implement Provisioned Concurrency:**
   ```bash
   aws lambda put-provisioned-concurrency-config \
     --function-name cost-reporting-dev-handler \
     --provisioned-concurrent-executions 2
   ```

### Infrastructure Troubleshooting

#### Issue: CDK Deployment Failures
**Symptoms:**
- Stack deployment fails
- Resource creation errors

**Solutions:**

1. **Check CDK Version:**
   ```bash
   cdk --version
   npm list -g aws-cdk
   ```

2. **Bootstrap CDK (if needed):**
   ```bash
   cdk bootstrap aws://008195334540/us-east-1
   ```

3. **Check IAM Permissions:**
   ```bash
   aws sts get-caller-identity
   aws iam get-user
   ```

4. **Clean and Redeploy:**
   ```bash
   cd infrastructure
   rm -rf node_modules cdk.out
   npm install
   cdk synth
   cdk deploy --all
   ```

### Data and Configuration Issues

#### Issue: Client Configuration Corruption
**Symptoms:**
- Clients not processing correctly
- Configuration validation errors

**Solutions:**

1. **Backup Current Configuration:**
   ```bash
   aws dynamodb scan --table-name cost-reporting-dev-clients > backup.json
   ```

2. **Validate Configuration:**
   ```bash
   python cli/main.py client validate --client-id CLIENT_ID
   ```

3. **Restore from Backup:**
   ```bash
   python cli/main.py client import --input backup.json
   ```

#### Issue: DynamoDB Table Issues
**Symptoms:**
- Cannot read/write client configurations
- Table not found errors

**Solutions:**

1. **Check Table Status:**
   ```bash
   aws dynamodb describe-table --table-name cost-reporting-dev-clients
   ```

2. **Restore Table (if deleted):**
   ```bash
   # List available backups
   aws dynamodb list-backups --table-name cost-reporting-dev-clients
   
   # Restore from backup
   aws dynamodb restore-table-from-backup \
     --target-table-name cost-reporting-dev-clients \
     --backup-arn BACKUP_ARN
   ```

### Network and Connectivity Issues

#### Issue: AWS API Rate Limiting
**Symptoms:**
- ThrottlingException errors
- API calls failing intermittently

**Solutions:**

1. **Implement Exponential Backoff:**
   ```python
   import time
   import random
   
   def retry_with_backoff(func, max_retries=3):
       for attempt in range(max_retries):
           try:
               return func()
           except ClientError as e:
               if e.response['Error']['Code'] == 'ThrottlingException':
                   wait_time = (2 ** attempt) + random.uniform(0, 1)
                   time.sleep(wait_time)
               else:
                   raise
   ```

2. **Reduce API Call Frequency:**
   - Batch requests where possible
   - Implement caching
   - Use pagination efficiently

### Performance Optimization

#### Issue: Slow Report Generation
**Symptoms:**
- Reports taking longer than expected
- Lambda approaching timeout

**Solutions:**

1. **Profile Performance:**
   ```bash
   # Enable X-Ray tracing
   aws lambda update-function-configuration \
     --function-name cost-reporting-dev-handler \
     --tracing-config Mode=Active
   ```

2. **Optimize Data Processing:**
   - Process accounts in parallel
   - Implement data caching
   - Reduce API calls

3. **Increase Resources:**
   ```bash
   # Increase memory and timeout
   aws lambda update-function-configuration \
     --function-name cost-reporting-dev-handler \
     --memory-size 1536 \
     --timeout 900
   ```

## Getting Additional Help

### Log Analysis Commands

```bash
# View recent Lambda logs
aws logs tail /aws/lambda/cost-reporting-dev-handler --follow

# Search for specific errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/cost-reporting-dev-handler \
  --filter-pattern "ERROR"

# Export logs for analysis
aws logs create-export-task \
  --log-group-name /aws/lambda/cost-reporting-dev-handler \
  --from $(date -d "1 day ago" +%s)000 \
  --to $(date +%s)000 \
  --destination cost-reporting-logs-bucket
```

### System Health Checks

```bash
# Check overall system health
python cli/main.py system health-check

# Validate all client configurations
python cli/main.py client list --validate

# Test Lambda function
aws lambda invoke \
  --function-name cost-reporting-dev-handler \
  --cli-binary-format raw-in-base64-out \
  --payload '{"health_check": true}' \
  /tmp/health-response.json
```

### Diagnostic Commands

```bash
# Check infrastructure status
aws cloudformation describe-stacks --stack-name lambda-cost-reporting-dev

# Check EventBridge rules
aws events list-rules --name-prefix cost-reporting-dev

# Check S3 bucket
aws s3 ls s3://cost-reporting-dev-reports-008195334540/

# Check DynamoDB table
aws dynamodb describe-table --table-name cost-reporting-dev-clients
```

### Support Information

When contacting support, please provide:

1. **Error Messages**: Full error messages and stack traces
2. **Configuration**: Sanitized client configuration (remove credentials)
3. **Logs**: Relevant CloudWatch logs with timestamps
4. **Environment**: AWS region, Lambda version, deployment method
5. **Timeline**: When the issue started and any recent changes
6. **AWS Account**: Account ID and region
7. **Function Name**: Exact Lambda function name

### Emergency Procedures

For critical issues:

1. **Disable Problematic Clients:**
   ```bash
   python cli/main.py client update --client-id CLIENT_ID --status inactive
   ```

2. **Stop Scheduled Executions:**
   ```bash
   aws events disable-rule --name cost-reporting-dev-weekly
   aws events disable-rule --name cost-reporting-dev-monthly
   ```

3. **Check System Resources:**
   ```bash
   # Monitor Lambda metrics
   aws cloudwatch get-metric-statistics \
     --namespace AWS/Lambda \
     --metric-name Duration \
     --dimensions Name=FunctionName,Value=cost-reporting-dev-handler \
     --start-time $(date -d "1 hour ago" +%s) \
     --end-time $(date +%s) \
     --period 300 \
     --statistics Average,Maximum
   ```

4. **Emergency Rollback:**
   ```bash
   # Rollback to previous CDK deployment
   cd infrastructure
   git checkout HEAD~1
   cdk deploy --all
   ```

### System Status Check Script

Create a comprehensive health check script:

```bash
#!/bin/bash
# system-health-check.sh

echo "=== Lambda Cost Reporting System Health Check ==="
echo "Date: $(date)"
echo

# Check Lambda function
echo "1. Checking Lambda function..."
aws lambda get-function --function-name cost-reporting-dev-handler > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✓ Lambda function exists"
else
    echo "✗ Lambda function not found"
fi

# Check DynamoDB table
echo "2. Checking DynamoDB table..."
aws dynamodb describe-table --table-name cost-reporting-dev-clients > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✓ DynamoDB table exists"
else
    echo "✗ DynamoDB table not found"
fi

# Check S3 bucket
echo "3. Checking S3 bucket..."
aws s3 ls s3://cost-reporting-dev-reports-008195334540/ > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✓ S3 bucket accessible"
else
    echo "✗ S3 bucket not accessible"
fi

# Check EventBridge rules
echo "4. Checking EventBridge rules..."
RULES=$(aws events list-rules --name-prefix cost-reporting-dev --query 'length(Rules)')
if [ "$RULES" -gt 0 ]; then
    echo "✓ EventBridge rules configured ($RULES rules)"
else
    echo "✗ No EventBridge rules found"
fi

# Test Lambda function
echo "5. Testing Lambda function..."
aws lambda invoke \
  --function-name cost-reporting-dev-handler \
  --cli-binary-format raw-in-base64-out \
  --payload '{"health_check": true}' \
  /tmp/health-test.json > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "✓ Lambda function invocation successful"
else
    echo "✗ Lambda function invocation failed"
fi

echo
echo "=== Health Check Complete ==="
```