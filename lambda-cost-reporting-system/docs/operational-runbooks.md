# Operational Runbooks

This document provides step-by-step procedures for common operational tasks in the Lambda Cost Reporting System.

## Table of Contents

1. [Daily Operations](#daily-operations)
2. [Client Management](#client-management)
3. [Incident Response](#incident-response)
4. [Monitoring and Alerting](#monitoring-and-alerting)
5. [Maintenance Tasks](#maintenance-tasks)
6. [Troubleshooting Procedures](#troubleshooting-procedures)

## Daily Operations

### Morning Health Check

**Frequency:** Daily (weekdays)  
**Duration:** 5-10 minutes  
**Owner:** Operations Team

#### Procedure

1. **Check System Status**
   ```bash
   # Check Lambda function health
   aws lambda get-function --function-name cost-reporting-lambda
   
   # Check recent executions
   aws logs filter-log-events \
     --log-group-name /aws/lambda/cost-reporting-lambda \
     --start-time $(date -d "yesterday" +%s)000 \
     --filter-pattern "ERROR"
   ```

2. **Review CloudWatch Alarms**
   ```bash
   # Check alarm status
   aws cloudwatch describe-alarms \
     --alarm-names "CostReporting-ExecutionFailures" \
       "CostReporting-HighDuration" \
       "CostReporting-EmailFailures"
   ```

3. **Verify Recent Reports**
   ```bash
   # Check S3 for recent reports
   aws s3 ls s3://cost-reporting-assets/reports/ \
     --recursive --human-readable | tail -20
   ```

4. **Check Client Status**
   ```bash
   # List active clients
   python cli/client_manager.py list --status active --format table
   ```

#### Success Criteria
- No critical alarms in ALARM state
- Recent reports generated successfully
- All active clients have valid configurations

#### Escalation
If any issues found, follow [Incident Response](#incident-response) procedures.

---

### Weekly Report Review

**Frequency:** Weekly (Mondays)  
**Duration:** 15-30 minutes  
**Owner:** Operations Team

#### Procedure

1. **Review Weekly Execution Summary**
   ```bash
   # Get execution metrics for past week
   aws cloudwatch get-metric-statistics \
     --namespace "CostReporting" \
     --metric-name "ExecutionsSuccessful" \
     --start-time $(date -d "7 days ago" +%s) \
     --end-time $(date +%s) \
     --period 86400 \
     --statistics Sum
   ```

2. **Check Email Delivery Rates**
   ```bash
   # Check SES sending statistics
   aws ses get-send-statistics
   ```

3. **Review Error Patterns**
   ```bash
   # Analyze error logs
   aws logs insights start-query \
     --log-group-name /aws/lambda/cost-reporting-lambda \
     --start-time $(date -d "7 days ago" +%s) \
     --end-time $(date +%s) \
     --query-string 'fields @timestamp, @message | filter @message like /ERROR/ | stats count() by bin(5m)'
   ```

4. **Generate Operations Report**
   ```bash
   # Run weekly operations report
   python scripts/generate_ops_report.py --period weekly --output weekly_ops_report.json
   ```

#### Actions
- Document any recurring issues
- Update monitoring thresholds if needed
- Plan maintenance activities

---

## Client Management

### Adding New Client

**Duration:** 10-15 minutes  
**Prerequisites:** Client AWS credentials and configuration details

#### Procedure

1. **Create Client Configuration**
   ```bash
   # Generate sample configuration
   python cli/client_manager.py sample-config --output new-client.json
   
   # Edit configuration with client details
   nano new-client.json
   ```

2. **Validate Configuration**
   ```bash
   # Validate configuration format
   python scripts/validate_migration.py --config-file new-client.json
   
   # Test AWS access
   python scripts/validate_migration.py --config-file new-client.json --check-aws
   ```

3. **Add Client to System**
   ```bash
   # Add client
   python cli/client_manager.py add --config new-client.json
   
   # Verify addition
   python cli/client_manager.py list --format table
   ```

4. **Test Report Generation**
   ```bash
   # Get client ID from previous step
   CLIENT_ID="<client-id>"
   
   # Trigger test report
   aws lambda invoke \
     --function-name cost-reporting-lambda \
     --payload "{\"test_report\": true, \"client_id\": \"$CLIENT_ID\"}" \
     test_response.json
   
   # Check response
   cat test_response.json
   ```

5. **Verify Email Delivery**
   - Check client's email for test report
   - Verify report formatting and branding
   - Confirm all recipients received the email

#### Success Criteria
- Client configuration validated successfully
- Test report generated and delivered
- No errors in CloudWatch logs

#### Documentation
- Update client inventory
- Record client-specific configurations
- Note any special requirements

---

### Updating Client Configuration

**Duration:** 5-10 minutes  
**Prerequisites:** Updated client configuration details

#### Procedure

1. **Export Current Configuration**
   ```bash
   # Get current configuration
   CLIENT_ID="<client-id>"
   python cli/client_manager.py export \
     --output current-config.json \
     --client-id $CLIENT_ID
   ```

2. **Modify Configuration**
   ```bash
   # Edit configuration
   nano current-config.json
   
   # Validate changes
   python scripts/validate_migration.py --config-file current-config.json --check-aws
   ```

3. **Update Client**
   ```bash
   # Apply updates
   python cli/client_manager.py update \
     --client-id $CLIENT_ID \
     --config current-config.json
   
   # Verify update
   python cli/client_manager.py validate --client-id $CLIENT_ID
   ```

4. **Test Updated Configuration**
   ```bash
   # Generate test report with new configuration
   aws lambda invoke \
     --function-name cost-reporting-lambda \
     --payload "{\"test_report\": true, \"client_id\": \"$CLIENT_ID\"}" \
     test_response.json
   ```

#### Rollback Procedure
If update fails:
```bash
# Restore from backup (if available)
python cli/client_manager.py update \
  --client-id $CLIENT_ID \
  --config backup-config.json
```

---

### Removing Client

**Duration:** 5 minutes  
**Prerequisites:** Client removal approval

#### Procedure

1. **Backup Client Configuration**
   ```bash
   CLIENT_ID="<client-id>"
   python cli/client_manager.py export \
     --output "backup-${CLIENT_ID}.json" \
     --client-id $CLIENT_ID
   ```

2. **Remove Client**
   ```bash
   # Remove client (with confirmation)
   python cli/client_manager.py remove --client-id $CLIENT_ID
   
   # Or skip confirmation
   python cli/client_manager.py remove --client-id $CLIENT_ID --confirm
   ```

3. **Clean Up Assets**
   ```bash
   # Remove client assets from S3
   aws s3 rm s3://cost-reporting-assets/clients/$CLIENT_ID/ --recursive
   
   # Remove old reports
   aws s3 rm s3://cost-reporting-assets/reports/ \
     --recursive --exclude "*" --include "*$CLIENT_ID*"
   ```

4. **Verify Removal**
   ```bash
   # Confirm client is removed
   python cli/client_manager.py list --format table
   ```

#### Documentation
- Record removal date and reason
- Archive client configuration backup
- Update client inventory

---

## Incident Response

### Lambda Function Failures

**Severity:** High  
**Response Time:** 15 minutes

#### Symptoms
- CloudWatch alarm: "CostReporting-ExecutionFailures"
- Multiple failed Lambda executions
- Clients not receiving reports

#### Investigation Steps

1. **Check Recent Executions**
   ```bash
   # Get recent execution logs
   aws logs filter-log-events \
     --log-group-name /aws/lambda/cost-reporting-lambda \
     --start-time $(date -d "1 hour ago" +%s)000 \
     --filter-pattern "ERROR"
   ```

2. **Identify Error Patterns**
   ```bash
   # Analyze error types
   aws logs insights start-query \
     --log-group-name /aws/lambda/cost-reporting-lambda \
     --start-time $(date -d "1 hour ago" +%s) \
     --end-time $(date +%s) \
     --query-string 'fields @timestamp, @message | filter @message like /ERROR/ | stats count() by @message'
   ```

3. **Check System Resources**
   ```bash
   # Check Lambda metrics
   aws cloudwatch get-metric-statistics \
     --namespace AWS/Lambda \
     --metric-name Duration \
     --dimensions Name=FunctionName,Value=cost-reporting-lambda \
     --start-time $(date -d "1 hour ago" +%s) \
     --end-time $(date +%s) \
     --period 300 \
     --statistics Average,Maximum
   ```

#### Common Resolutions

**Timeout Issues:**
```bash
# Increase Lambda timeout
aws lambda update-function-configuration \
  --function-name cost-reporting-lambda \
  --timeout 900
```

**Memory Issues:**
```bash
# Increase Lambda memory
aws lambda update-function-configuration \
  --function-name cost-reporting-lambda \
  --memory-size 1024
```

**Permission Issues:**
```bash
# Check IAM role permissions
aws iam get-role-policy \
  --role-name cost-reporting-lambda-role \
  --policy-name cost-reporting-policy
```

#### Escalation
If issue persists after 30 minutes, escalate to development team.

---

### Email Delivery Failures

**Severity:** Medium  
**Response Time:** 30 minutes

#### Symptoms
- CloudWatch alarm: "CostReporting-EmailFailures"
- Clients reporting missing reports
- SES bounce/complaint notifications

#### Investigation Steps

1. **Check SES Status**
   ```bash
   # Check SES sending quota and statistics
   aws ses get-send-quota
   aws ses get-send-statistics
   
   # Check reputation
   aws ses get-reputation
   ```

2. **Review Bounce/Complaint Rates**
   ```bash
   # Check recent bounces
   aws logs filter-log-events \
     --log-group-name /aws/ses \
     --start-time $(date -d "1 hour ago" +%s)000 \
     --filter-pattern "bounce"
   ```

3. **Verify Email Addresses**
   ```bash
   # Check verified identities
   aws ses list-verified-email-addresses
   
   # Check identity verification status
   aws ses get-identity-verification-attributes \
     --identities reports@yourcompany.com
   ```

#### Common Resolutions

**Quota Exceeded:**
```bash
# Request quota increase through AWS Support
# Temporary: Reduce sending frequency
```

**Reputation Issues:**
```bash
# Review and clean recipient lists
# Remove bounced/complained addresses
python scripts/clean_recipient_lists.py
```

**Verification Issues:**
```bash
# Re-verify email identity
aws ses verify-email-identity --email-address reports@yourcompany.com
```

---

### DynamoDB Access Issues

**Severity:** High  
**Response Time:** 15 minutes

#### Symptoms
- Lambda function cannot read/write client configurations
- "AccessDenied" errors in logs
- Client management CLI failures

#### Investigation Steps

1. **Check Table Status**
   ```bash
   # Verify table exists and is active
   aws dynamodb describe-table --table-name cost-reporting-clients
   ```

2. **Test Access**
   ```bash
   # Test read access
   aws dynamodb scan --table-name cost-reporting-clients --limit 1
   
   # Test write access
   aws dynamodb put-item \
     --table-name cost-reporting-clients \
     --item '{"client_id":{"S":"test"},"client_name":{"S":"test"}}'
   ```

3. **Check IAM Permissions**
   ```bash
   # Review Lambda execution role
   aws iam get-role-policy \
     --role-name cost-reporting-lambda-role \
     --policy-name dynamodb-access-policy
   ```

#### Common Resolutions

**Permission Issues:**
```bash
# Update IAM policy
aws iam put-role-policy \
  --role-name cost-reporting-lambda-role \
  --policy-name dynamodb-access-policy \
  --policy-document file://policies/dynamodb-policy.json
```

**Table Issues:**
```bash
# Check table capacity
aws dynamodb describe-table --table-name cost-reporting-clients

# Update capacity if needed
aws dynamodb update-table \
  --table-name cost-reporting-clients \
  --billing-mode PAY_PER_REQUEST
```

---

## Monitoring and Alerting

### Setting Up Custom Alarms

#### High Error Rate Alarm
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "CostReporting-HighErrorRate" \
  --alarm-description "High error rate in cost reporting" \
  --metric-name "Errors" \
  --namespace "AWS/Lambda" \
  --statistic "Sum" \
  --period 300 \
  --threshold 5 \
  --comparison-operator "GreaterThanThreshold" \
  --dimensions Name=FunctionName,Value=cost-reporting-lambda \
  --evaluation-periods 2 \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:cost-reporting-alerts"
```

#### Long Execution Time Alarm
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "CostReporting-LongExecution" \
  --alarm-description "Lambda execution taking too long" \
  --metric-name "Duration" \
  --namespace "AWS/Lambda" \
  --statistic "Average" \
  --period 300 \
  --threshold 600000 \
  --comparison-operator "GreaterThanThreshold" \
  --dimensions Name=FunctionName,Value=cost-reporting-lambda \
  --evaluation-periods 1 \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:cost-reporting-alerts"
```

### Custom Metrics

#### Creating Custom Metrics
```python
# In Lambda function code
import boto3

cloudwatch = boto3.client('cloudwatch')

# Report successful client processing
cloudwatch.put_metric_data(
    Namespace='CostReporting',
    MetricData=[
        {
            'MetricName': 'ClientsProcessed',
            'Value': client_count,
            'Unit': 'Count'
        }
    ]
)
```

#### Querying Custom Metrics
```bash
# Get custom metrics
aws cloudwatch get-metric-statistics \
  --namespace "CostReporting" \
  --metric-name "ClientsProcessed" \
  --start-time $(date -d "1 day ago" +%s) \
  --end-time $(date +%s) \
  --period 3600 \
  --statistics Sum
```

---

## Maintenance Tasks

### Weekly Maintenance

**Schedule:** Every Sunday at 2 AM UTC  
**Duration:** 30-60 minutes

#### Tasks

1. **Clean Up Old Reports**
   ```bash
   # Remove reports older than 90 days
   aws s3api list-objects-v2 \
     --bucket cost-reporting-assets \
     --prefix reports/ \
     --query "Contents[?LastModified<'$(date -d '90 days ago' --iso-8601)'].Key" \
     --output text | xargs -I {} aws s3 rm s3://cost-reporting-assets/{}
   ```

2. **Update Lambda Function**
   ```bash
   # Deploy latest code
   cd infrastructure
   cdk deploy LambdaCostReportingStack
   ```

3. **Rotate Credentials**
   ```bash
   # Check credential age
   python scripts/check_credential_age.py
   
   # Rotate old credentials
   python scripts/rotate_credentials.py --dry-run
   ```

4. **Database Maintenance**
   ```bash
   # Check table metrics
   aws dynamodb describe-table --table-name cost-reporting-clients
   
   # Backup table
   aws dynamodb create-backup \
     --table-name cost-reporting-clients \
     --backup-name "weekly-backup-$(date +%Y%m%d)"
   ```

### Monthly Maintenance

**Schedule:** First Sunday of each month  
**Duration:** 1-2 hours

#### Tasks

1. **Security Review**
   ```bash
   # Review IAM policies
   python scripts/security_audit.py --output security_report.json
   
   # Check for unused permissions
   aws iam generate-service-last-accessed-details \
     --arn arn:aws:iam::123456789012:role/cost-reporting-lambda-role
   ```

2. **Performance Review**
   ```bash
   # Generate performance report
   python scripts/performance_report.py --period monthly
   
   # Review Lambda metrics
   aws cloudwatch get-metric-statistics \
     --namespace AWS/Lambda \
     --metric-name Duration \
     --dimensions Name=FunctionName,Value=cost-reporting-lambda \
     --start-time $(date -d "30 days ago" +%s) \
     --end-time $(date +%s) \
     --period 86400 \
     --statistics Average,Maximum
   ```

3. **Cost Analysis**
   ```bash
   # Review AWS costs for the system
   aws ce get-cost-and-usage \
     --time-period Start=$(date -d "30 days ago" +%Y-%m-%d),End=$(date +%Y-%m-%d) \
     --granularity MONTHLY \
     --metrics BlendedCost \
     --group-by Type=DIMENSION,Key=SERVICE
   ```

4. **Documentation Updates**
   - Review and update operational procedures
   - Update client contact information
   - Review and update monitoring thresholds

---

## Troubleshooting Procedures

### Lambda Function Not Executing

#### Symptoms
- No recent executions in CloudWatch logs
- EventBridge rules not triggering
- Scheduled reports not being sent

#### Diagnosis Steps

1. **Check EventBridge Rules**
   ```bash
   # List rules
   aws events list-rules --name-prefix cost-reporting
   
   # Check rule details
   aws events describe-rule --name cost-reporting-weekly-schedule
   
   # Check rule targets
   aws events list-targets-by-rule --rule cost-reporting-weekly-schedule
   ```

2. **Check Lambda Permissions**
   ```bash
   # Check resource-based policy
   aws lambda get-policy --function-name cost-reporting-lambda
   
   # Check execution role
   aws lambda get-function --function-name cost-reporting-lambda
   ```

3. **Test Manual Execution**
   ```bash
   # Manually invoke function
   aws lambda invoke \
     --function-name cost-reporting-lambda \
     --payload '{"test": true}' \
     response.json
   
   cat response.json
   ```

#### Resolution Steps

1. **Fix EventBridge Rule**
   ```bash
   # Enable rule if disabled
   aws events enable-rule --name cost-reporting-weekly-schedule
   
   # Update rule target if needed
   aws events put-targets \
     --rule cost-reporting-weekly-schedule \
     --targets Id=1,Arn=arn:aws:lambda:us-east-1:123456789012:function:cost-reporting-lambda
   ```

2. **Fix Lambda Permissions**
   ```bash
   # Add EventBridge permission
   aws lambda add-permission \
     --function-name cost-reporting-lambda \
     --statement-id allow-eventbridge \
     --action lambda:InvokeFunction \
     --principal events.amazonaws.com \
     --source-arn arn:aws:events:us-east-1:123456789012:rule/cost-reporting-weekly-schedule
   ```

### Client Configuration Issues

#### Symptoms
- Specific clients not receiving reports
- AWS access errors for certain accounts
- Configuration validation failures

#### Diagnosis Steps

1. **Validate Client Configuration**
   ```bash
   CLIENT_ID="<client-id>"
   python cli/client_manager.py validate --client-id $CLIENT_ID
   ```

2. **Test AWS Access**
   ```bash
   # Test with validation script
   python scripts/validate_migration.py \
     --config-file client-config.json \
     --check-aws
   ```

3. **Check Recent Executions**
   ```bash
   # Filter logs for specific client
   aws logs filter-log-events \
     --log-group-name /aws/lambda/cost-reporting-lambda \
     --start-time $(date -d "1 day ago" +%s)000 \
     --filter-pattern "$CLIENT_ID"
   ```

#### Resolution Steps

1. **Update Client Configuration**
   ```bash
   # Export current config
   python cli/client_manager.py export \
     --client-id $CLIENT_ID \
     --output current-config.json
   
   # Edit and update
   nano current-config.json
   python cli/client_manager.py update \
     --client-id $CLIENT_ID \
     --config current-config.json
   ```

2. **Rotate AWS Credentials**
   ```bash
   # Update with new credentials
   python scripts/rotate_client_credentials.py --client-id $CLIENT_ID
   ```

### Performance Issues

#### Symptoms
- Lambda function timeouts
- High execution duration
- Memory limit exceeded errors

#### Diagnosis Steps

1. **Check Lambda Metrics**
   ```bash
   # Check duration metrics
   aws cloudwatch get-metric-statistics \
     --namespace AWS/Lambda \
     --metric-name Duration \
     --dimensions Name=FunctionName,Value=cost-reporting-lambda \
     --start-time $(date -d "1 day ago" +%s) \
     --end-time $(date +%s) \
     --period 300 \
     --statistics Average,Maximum
   
   # Check memory usage
   aws cloudwatch get-metric-statistics \
     --namespace AWS/Lambda \
     --metric-name MemoryUtilization \
     --dimensions Name=FunctionName,Value=cost-reporting-lambda \
     --start-time $(date -d "1 day ago" +%s) \
     --end-time $(date +%s) \
     --period 300 \
     --statistics Average,Maximum
   ```

2. **Analyze Execution Logs**
   ```bash
   # Look for performance indicators
   aws logs filter-log-events \
     --log-group-name /aws/lambda/cost-reporting-lambda \
     --start-time $(date -d "1 hour ago" +%s)000 \
     --filter-pattern "REPORT"
   ```

#### Resolution Steps

1. **Increase Lambda Resources**
   ```bash
   # Increase memory (also increases CPU)
   aws lambda update-function-configuration \
     --function-name cost-reporting-lambda \
     --memory-size 1536
   
   # Increase timeout
   aws lambda update-function-configuration \
     --function-name cost-reporting-lambda \
     --timeout 900
   ```

2. **Optimize Code**
   - Review and optimize data processing logic
   - Implement connection pooling
   - Add caching where appropriate
   - Consider breaking large operations into smaller chunks

---

## Emergency Procedures

### System-Wide Outage

1. **Immediate Actions**
   - Check AWS service health dashboard
   - Verify all AWS services are operational
   - Check for any ongoing AWS maintenance

2. **Communication**
   - Notify stakeholders of the outage
   - Provide estimated resolution time
   - Send regular updates

3. **Recovery**
   - Follow incident response procedures
   - Implement temporary workarounds if needed
   - Document lessons learned

### Data Loss Prevention

1. **Regular Backups**
   - DynamoDB point-in-time recovery enabled
   - S3 versioning enabled
   - Code in version control

2. **Recovery Procedures**
   - Restore from DynamoDB backup
   - Recover S3 objects from versions
   - Redeploy infrastructure from code

### Security Incident

1. **Immediate Response**
   - Isolate affected systems
   - Revoke compromised credentials
   - Enable additional logging

2. **Investigation**
   - Review CloudTrail logs
   - Check for unauthorized access
   - Assess data exposure

3. **Recovery**
   - Rotate all credentials
   - Update security policies
   - Implement additional controls

---

## Contact Information

### Escalation Contacts

- **Primary On-Call:** operations-team@company.com
- **Development Team:** dev-team@company.com
- **Security Team:** security@company.com
- **AWS Support:** [AWS Support Case]

### External Resources

- **AWS Documentation:** https://docs.aws.amazon.com/
- **AWS Support:** https://console.aws.amazon.com/support/
- **System Status Page:** https://status.company.com/

---

*Last Updated: [Current Date]*  
*Version: 1.0*  
*Owner: Operations Team*