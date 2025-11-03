# Frequently Asked Questions (FAQ)

## Table of Contents

1. [General Questions](#general-questions)
2. [Client Onboarding](#client-onboarding)
3. [AWS Configuration](#aws-configuration)
4. [Report Generation](#report-generation)
5. [Email Delivery](#email-delivery)
6. [System Administration](#system-administration)
7. [Troubleshooting](#troubleshooting)
8. [Security](#security)
9. [Performance](#performance)
10. [Billing and Costs](#billing-and-costs)

## General Questions

### Q: What is the Lambda Cost Reporting System?
**A:** The Lambda Cost Reporting System is a serverless AWS solution that automatically generates and emails cost reports for multiple clients. It replaces the previous aws-cost-agent-framework with a more scalable, cost-effective serverless architecture.

### Q: What are the main benefits over the previous framework?
**A:** 
- **Serverless**: No infrastructure to manage, automatic scaling
- **Cost-effective**: Pay only for execution time, no idle costs
- **Reliable**: Built-in retry logic and error handling
- **Scalable**: Handles multiple clients efficiently
- **Secure**: Encrypted credentials and least-privilege access
- **Monitored**: Comprehensive logging and alerting

### Q: What AWS services does the system use?
**A:** 
- **AWS Lambda**: Main execution environment
- **Amazon DynamoDB**: Client configuration storage
- **Amazon S3**: Report and asset storage
- **Amazon EventBridge**: Scheduling
- **AWS SES**: Email delivery
- **AWS KMS**: Encryption
- **Amazon CloudWatch**: Monitoring and logging
- **AWS SNS**: Alerting

### Q: How much does it cost to run?
**A:** Costs depend on usage, but typically:
- Lambda: $0.20-$2.00 per month per client
- DynamoDB: $0.25-$1.00 per month
- S3: $0.10-$0.50 per month
- SES: $0.10 per 1,000 emails
- Other services: <$1.00 per month
- **Total**: Usually $1-5 per month for typical usage

## Client Onboarding

### Q: How do I add a new client?
**A:** Use the CLI tool:
```bash
# Generate sample configuration
python cli/main.py client sample-config --output new-client.json

# Edit the configuration file
nano new-client.json

# Add client to system
python cli/main.py client add --config new-client.json
```

### Q: What information do I need from the client?
**A:**
- AWS account ID(s)
- AWS access keys with Cost Explorer permissions
- Email addresses for report recipients
- Company name and branding preferences (optional)
- Report frequency preferences (weekly/monthly)
- Cost threshold preferences

### Q: Can a client have multiple AWS accounts?
**A:** Yes, configure multiple accounts in the `aws_accounts` array:
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

### Q: How do I update a client's configuration?
**A:**
```bash
# Export current configuration
python cli/main.py client export --client-id CLIENT_ID --output current-config.json

# Edit the configuration
nano current-config.json

# Update client
python cli/main.py client update --client-id CLIENT_ID --config current-config.json
```

### Q: How do I remove a client?
**A:**
```bash
# Remove client (with confirmation prompt)
python cli/main.py client remove --client-id CLIENT_ID

# Or skip confirmation
python cli/main.py client remove --client-id CLIENT_ID --confirm
```

## AWS Configuration

### Q: What AWS permissions does the client need to provide?
**A:** The client needs to create an IAM user with these permissions:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ce:GetCostAndUsage",
        "ce:GetCostForecast",
        "ce:GetUsageForecast",
        "ce:GetCostCategories",
        "ce:GetDimensionValues",
        "ce:GetReservationCoverage",
        "ce:GetReservationPurchaseRecommendation",
        "ce:GetReservationUtilization",
        "ce:GetSavingsPlansUtilization",
        "ce:GetSavingsPlansCoverage"
      ],
      "Resource": "*"
    }
  ]
}
```

### Q: Can I use IAM roles instead of access keys?
**A:** Currently, the system uses access keys for simplicity. IAM role support is planned for a future version. For now, use dedicated IAM users with minimal permissions.

### Q: How often should AWS credentials be rotated?
**A:** We recommend rotating credentials every 90 days. The system will alert you when credentials are approaching expiration.

### Q: What regions are supported?
**A:** The system can collect cost data from any AWS region. The Lambda function should be deployed in your primary region (typically us-east-1 for global services).

### Q: How do I handle AWS Organizations with multiple accounts?
**A:** You have two options:
1. **Individual Access Keys**: Create access keys for each account
2. **Cross-Account Roles**: Set up assume role access (requires custom configuration)

## Report Generation

### Q: When are reports generated?
**A:** By default:
- **Weekly reports**: Every Monday at 9:00 AM UTC
- **Monthly reports**: First day of each month at 8:00 AM UTC

You can customize schedules per client.

### Q: What data is included in reports?
**A:**
- Total costs for the reporting period
- Cost breakdown by AWS service
- Cost breakdown by AWS account (if multiple)
- Cost trends and comparisons
- Cost alerts (if thresholds exceeded)
- Forecasting (if enabled)

### Q: How far back does cost data go?
**A:** AWS Cost Explorer provides up to 13 months of historical data. The system can generate reports for any period within this range.

### Q: Can I customize report content?
**A:** Yes, you can configure:
- Which services to include/exclude
- Number of top services to show
- Cost thresholds for alerts
- Report branding (logo, colors)
- Email recipients

### Q: Why is my report missing recent data?
**A:** AWS cost data has a 24-48 hour delay. Reports for the current day will be incomplete. Always generate reports for completed days.

### Q: Can I generate reports manually?
**A:** Yes:
```bash
# Generate test report for a client
aws lambda invoke \
  --function-name cost-reporting-lambda \
  --payload '{"test_report": true, "client_id": "CLIENT_ID"}' \
  response.json
```

## Email Delivery

### Q: Why aren't emails being delivered?
**A:** Common causes:
1. **SES Sandbox**: If in sandbox mode, you can only send to verified addresses
2. **Bounce/Complaint Rate**: High rates can affect delivery
3. **Spam Filters**: Recipients may need to whitelist the sender
4. **SES Limits**: Check sending quota and rate limits

### Q: How do I move out of SES sandbox?
**A:** Submit a request through the AWS Console:
1. Go to SES Console
2. Click "Request production access"
3. Fill out the form with your use case
4. Wait for approval (usually 24-48 hours)

### Q: Can I customize email templates?
**A:** Yes, you can customize:
- Company logo and branding
- Email subject lines
- Header and footer content
- Color scheme
- Report layout

### Q: How do I handle email bounces?
**A:** The system automatically:
1. Logs bounce notifications
2. Removes hard bounces from future sends
3. Alerts administrators about high bounce rates

You should regularly review and clean recipient lists.

### Q: Can I send reports to multiple recipients?
**A:** Yes, configure multiple recipients in the client configuration:
```json
{
  "report_config": {
    "recipients": ["admin@client.com", "finance@client.com"],
    "cc_recipients": ["manager@client.com"]
  }
}
```

## System Administration

### Q: How do I monitor system health?
**A:** Use these methods:
1. **CloudWatch Dashboards**: Visual monitoring
2. **CloudWatch Alarms**: Automated alerts
3. **CLI Health Check**: `python cli/main.py system health-check`
4. **Log Analysis**: Review CloudWatch logs

### Q: How do I update the system?
**A:**
```bash
# Update Lambda function code
cd infrastructure
cdk deploy LambdaCostReportingStack

# Update infrastructure
cdk deploy --all
```

### Q: How do I backup client configurations?
**A:**
```bash
# Export all clients
python cli/main.py client export-all --output backup-$(date +%Y%m%d).json

# Export specific client
python cli/main.py client export --client-id CLIENT_ID --output client-backup.json
```

### Q: How do I restore from backup?
**A:**
```bash
# Restore all clients
python cli/main.py client import --input backup-20231201.json

# Restore specific client
python cli/main.py client add --config client-backup.json
```

### Q: How do I scale the system for more clients?
**A:** The system auto-scales, but you may need to:
1. Increase Lambda reserved concurrency
2. Adjust DynamoDB capacity
3. Increase SES sending limits
4. Monitor and optimize performance

## Troubleshooting

### Q: Lambda function is timing out. What should I do?
**A:**
1. **Increase timeout**: Maximum is 15 minutes
2. **Increase memory**: More memory = more CPU
3. **Optimize code**: Process clients in batches
4. **Check logs**: Look for bottlenecks

```bash
# Increase timeout and memory
aws lambda update-function-configuration \
  --function-name cost-reporting-lambda \
  --timeout 900 \
  --memory-size 1536
```

### Q: Client configuration validation is failing. Why?
**A:** Common issues:
1. **Invalid JSON format**: Use `jq . config.json` to validate
2. **Missing required fields**: Compare with sample configuration
3. **Invalid email addresses**: Check format and domains
4. **Invalid AWS credentials**: Test with AWS CLI
5. **Invalid color codes**: Must be hex format (#RRGGBB)

### Q: Reports show incorrect cost data. What's wrong?
**A:** Check:
1. **Time zones**: Ensure consistent UTC usage
2. **Date ranges**: Don't request current day data
3. **Account access**: Verify all accounts are accessible
4. **Permissions**: Ensure Cost Explorer access
5. **Filters**: Remove filters to test

### Q: How do I debug email delivery issues?
**A:**
1. **Check SES status**: `aws ses get-send-statistics`
2. **Verify email addresses**: `aws ses list-verified-email-addresses`
3. **Review bounce logs**: Check CloudWatch logs
4. **Test with simple email**: Send test message
5. **Check spam folders**: Ask recipients to check

### Q: DynamoDB is being throttled. How do I fix this?
**A:**
```bash
# Switch to on-demand billing
aws dynamodb modify-table \
  --table-name cost-reporting-clients \
  --billing-mode PAY_PER_REQUEST

# Or enable auto-scaling
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id table/cost-reporting-clients \
  --scalable-dimension dynamodb:table:ReadCapacityUnits \
  --min-capacity 5 \
  --max-capacity 100
```

## Security

### Q: How are AWS credentials stored securely?
**A:** 
- All credentials are encrypted using AWS KMS
- Stored in DynamoDB with encryption at rest
- Never logged in plain text
- Access controlled via IAM policies

### Q: What security best practices should I follow?
**A:**
1. **Rotate credentials regularly** (every 90 days)
2. **Use least privilege IAM policies**
3. **Enable CloudTrail logging**
4. **Monitor access patterns**
5. **Keep system updated**
6. **Use strong encryption keys**

### Q: How do I audit system access?
**A:**
1. **CloudTrail logs**: All API calls logged
2. **CloudWatch logs**: Application-level logging
3. **DynamoDB access logs**: Data access patterns
4. **SES sending logs**: Email delivery tracking

### Q: What happens if credentials are compromised?
**A:**
1. **Immediately rotate** affected credentials
2. **Review access logs** for unauthorized activity
3. **Update client configurations** with new credentials
4. **Monitor for unusual activity**
5. **Consider additional security measures**

## Performance

### Q: How many clients can the system handle?
**A:** The system can handle hundreds of clients. Practical limits:
- **Lambda concurrency**: 1000 concurrent executions (default)
- **DynamoDB**: Virtually unlimited with on-demand billing
- **SES**: 200 emails/second (can be increased)
- **Processing time**: ~30 seconds per client

### Q: How can I optimize performance?
**A:**
1. **Increase Lambda memory**: More memory = faster execution
2. **Use connection pooling**: Reuse AWS client connections
3. **Batch processing**: Process multiple clients together
4. **Optimize queries**: Reduce Cost Explorer API calls
5. **Cache data**: Store frequently accessed data

### Q: What are the system limits?
**A:**
- **Lambda timeout**: 15 minutes maximum
- **Lambda memory**: 10,240 MB maximum
- **DynamoDB item size**: 400 KB maximum
- **SES daily sending quota**: Varies by account
- **S3 object size**: 5 TB maximum

## Billing and Costs

### Q: How much will this cost to run?
**A:** Typical monthly costs:
- **Lambda**: $0.20-$2.00 per client
- **DynamoDB**: $0.25-$1.00 total
- **S3**: $0.10-$0.50 total
- **SES**: $0.10 per 1,000 emails
- **CloudWatch**: $0.50-$2.00 total
- **Other services**: <$1.00 total

**Total**: Usually $1-5 per month for typical usage

### Q: How can I reduce costs?
**A:**
1. **Optimize Lambda memory**: Don't over-provision
2. **Use S3 lifecycle policies**: Delete old reports
3. **DynamoDB on-demand**: Pay only for usage
4. **Reduce log retention**: Shorter retention periods
5. **Optimize report frequency**: Weekly vs daily

### Q: How do I monitor costs?
**A:**
1. **AWS Cost Explorer**: Track service costs
2. **CloudWatch billing alarms**: Set cost alerts
3. **AWS Budgets**: Set spending limits
4. **Cost allocation tags**: Track costs by client

### Q: Can I charge clients for usage?
**A:** Yes, you can:
1. **Track costs per client**: Use CloudWatch metrics
2. **Generate usage reports**: Monthly cost summaries
3. **Implement billing logic**: Charge based on usage
4. **Use AWS Cost Categories**: Organize costs by client

## Migration and Upgrades

### Q: How do I migrate from the old aws-cost-agent-framework?
**A:** Use the migration script:
```bash
# Run migration
python scripts/migrate_from_framework.py migrate \
  --framework-path ../aws-cost-agent-framework \
  --output-dir migration_output

# Validate migration
python scripts/validate_migration.py \
  --config-dir migration_output \
  --check-aws

# Import migrated configurations
python cli/main.py client import --input migration_output/*.json
```

### Q: How do I upgrade to a new version?
**A:**
1. **Backup configurations**: Export all clients
2. **Update code**: Pull latest version
3. **Run tests**: Ensure everything works
4. **Deploy updates**: Use CDK to deploy
5. **Validate**: Test with sample clients

### Q: What if the upgrade fails?
**A:**
1. **Rollback Lambda**: Deploy previous version
2. **Restore configurations**: Import from backup
3. **Check logs**: Identify the issue
4. **Contact support**: If needed

## Support and Resources

### Q: Where can I find more documentation?
**A:**
- **Deployment Guide**: [deployment-guide.md](deployment-guide.md)
- **Operational Runbooks**: [operational-runbooks.md](operational-runbooks.md)
- **Troubleshooting Guide**: [troubleshooting-guide.md](troubleshooting-guide.md)
- **Client Onboarding**: [client-onboarding-guide.md](client-onboarding-guide.md)
- **Monitoring Setup**: [monitoring-setup.md](monitoring-setup.md)

### Q: How do I get support?
**A:**
1. **Check documentation**: Start with troubleshooting guide
2. **Review logs**: CloudWatch logs often have answers
3. **Use CLI diagnostics**: `python cli/main.py system diagnose`
4. **Contact team**: operations-team@company.com

### Q: How do I report bugs or request features?
**A:**
1. **Check existing issues**: Review known issues
2. **Gather information**: Logs, configuration, steps to reproduce
3. **Submit request**: Use internal ticketing system
4. **Provide details**: The more information, the better

### Q: Is there a test environment?
**A:** Yes, deploy to a staging environment:
```bash
# Deploy to staging
export ENVIRONMENT=staging
cdk deploy --all

# Test with sample data
python cli/main.py client add --config test-client.json
```

### Q: How do I contribute to the project?
**A:**
1. **Follow coding standards**: Use existing patterns
2. **Write tests**: Unit and integration tests
3. **Update documentation**: Keep docs current
4. **Submit pull request**: Follow review process

---

*Last Updated: [Current Date]*  
*Version: 1.0*  
*Maintained by: Operations Team*