# Client Onboarding Guide

## Overview

This guide provides step-by-step instructions for onboarding new clients to the Lambda Cost Reporting System. The system automatically generates and sends AWS cost reports via email on a weekly and monthly basis.

## Prerequisites

Before onboarding a client, ensure you have:

- Administrative access to the Lambda Cost Reporting System
- Client's AWS account information and credentials
- Client's email addresses for report recipients
- Client's branding assets (optional)

## Onboarding Process

### Step 1: Gather Client Information

Collect the following information from the client:

#### Required Information
- **Company Name**: Full legal name of the organization
- **AWS Account Details**: For each AWS account to be monitored:
  - AWS Account ID (12-digit number)
  - Access Key ID
  - Secret Access Key
  - Primary AWS Region
  - Account Name/Description (optional)
- **Email Recipients**: List of email addresses to receive reports
- **Report Preferences**:
  - Weekly reports enabled (default: Yes)
  - Monthly reports enabled (default: Yes)
  - Cost threshold for alerts (default: $1,000)
  - Number of top services to include (default: 10)

#### Optional Information
- **CC Recipients**: Additional email addresses to CC on reports
- **Branding Assets**:
  - Company logo (PNG/JPG format, recommended size: 200x80px)
  - Primary brand color (hex format, e.g., #1f2937)
  - Secondary brand color (hex format, e.g., #f59e0b)
  - Custom email footer text
- **Alert Thresholds**: Custom cost alert configurations

### Step 2: Set Up AWS Access

The client needs to provide AWS credentials with the following permissions:

#### Required AWS Permissions
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
                "ce:GetSavingsPlansCoverage",
                "ce:ListCostCategoryDefinitions"
            ],
            "Resource": "*"
        }
    ]
}
```

#### Creating AWS Access Keys

**Option 1: IAM User (Recommended)**
1. Log into the AWS Console
2. Navigate to IAM → Users
3. Click "Create user"
4. Enter username: `cost-reporting-user`
5. Select "Programmatic access"
6. Attach the policy above (create as custom policy)
7. Complete user creation
8. Save the Access Key ID and Secret Access Key

**Option 2: IAM Role (Advanced)**
For enhanced security, clients can create an IAM role that the Lambda system can assume. This requires additional setup but provides better security isolation.

### Step 3: Create Client Configuration

Create a JSON configuration file with the client's information:

```json
{
  "client_name": "Example Company Inc.",
  "aws_accounts": [
    {
      "account_id": "123456789012",
      "access_key_id": "AKIAIOSFODNN7EXAMPLE",
      "secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
      "region": "us-east-1",
      "account_name": "Production Account"
    }
  ],
  "report_config": {
    "weekly_enabled": true,
    "monthly_enabled": true,
    "recipients": [
      "cfo@example.com",
      "devops@example.com"
    ],
    "cc_recipients": [
      "finance@example.com"
    ],
    "threshold": 1000.0,
    "top_services": 10,
    "include_accounts": true,
    "alert_thresholds": []
  },
  "branding": {
    "logo_s3_key": null,
    "primary_color": "#1f2937",
    "secondary_color": "#f59e0b",
    "company_name": "Example Company Inc.",
    "email_footer": "This automated report is provided by Example Company's FinOps team."
  },
  "status": "active"
}
```

### Step 4: Validate Configuration

Before adding the client, validate the configuration:

```bash
# Generate sample configuration
python cli/main.py client sample-config --output sample-client.json

# Validate AWS access (dry run)
python cli/main.py validate single --config client-config.json
```

### Step 5: Add Client to System

Add the client using the CLI:

```bash
# Add new client with validation
python cli/main.py client add --config client-config.json

# Add without AWS validation (if needed)
python cli/main.py client add --config client-config.json --no-validate
```

### Step 6: Upload Branding Assets (Optional)

If the client provided branding assets:

1. Upload logo to S3 bucket
2. Update client configuration with S3 key
3. Test report generation with branding

```bash
# Update client with branding
python cli/main.py client update --client-id <CLIENT_ID> --config updated-config.json
```

### Step 7: Test Report Generation

Generate a test report to verify everything is working:

```bash
# Validate client configuration and generate test report
python cli/main.py client validate --client-id <CLIENT_ID>
```

### Step 8: Schedule Monitoring

The system automatically schedules reports based on the client configuration:
- **Weekly Reports**: Every Monday at 9:00 AM UTC
- **Monthly Reports**: First day of each month at 8:00 AM UTC

No additional configuration is needed for scheduling.

## Post-Onboarding Tasks

### Verify First Reports

After onboarding:
1. Monitor the first scheduled report execution
2. Verify emails are delivered successfully
3. Check report content and formatting
4. Confirm branding is applied correctly

### Client Communication

Send the client:
1. Confirmation of successful onboarding
2. Sample report (if available)
3. Information about report schedule
4. Contact information for support
5. Instructions for updating preferences

### Documentation

Document the client onboarding:
1. Record client details in internal systems
2. Note any special configurations or requirements
3. Set up monitoring alerts for the client
4. Schedule periodic review of client needs

## Multiple AWS Accounts

For clients with multiple AWS accounts:

1. Collect credentials for each account
2. Add all accounts to the configuration file
3. The system will automatically aggregate costs across accounts
4. Reports will show both individual account and total costs

Example multi-account configuration:

```json
{
  "client_name": "Multi-Account Company",
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
    },
    {
      "account_id": "333333333333",
      "access_key_id": "AKIA...",
      "secret_access_key": "...",
      "region": "eu-west-1",
      "account_name": "Europe"
    }
  ],
  "report_config": {
    "include_accounts": true,
    "recipients": ["finance@company.com"],
    "threshold": 5000.0
  }
}
```

## Security Best Practices

### Credential Management
- Use dedicated IAM users for cost reporting
- Apply principle of least privilege
- Rotate access keys every 90 days
- Monitor access key usage

### Data Protection
- All credentials are encrypted at rest using AWS KMS
- Reports are transmitted via encrypted email
- Temporary report files are automatically deleted
- Access logs are maintained for audit purposes

### Access Control
- Limit who can add/modify client configurations
- Use separate environments for testing
- Implement approval workflows for production changes
- Regular security reviews of client access

## Common Issues and Solutions

See the [Troubleshooting Guide](troubleshooting-guide.md) for detailed solutions to common onboarding issues.

## Support and Maintenance

### Regular Maintenance Tasks
- Review client configurations quarterly
- Update AWS permissions as needed
- Monitor report delivery success rates
- Update branding assets when requested

### Client Support
- Provide monthly usage reports to clients
- Respond to configuration change requests
- Assist with AWS permission issues
- Help interpret cost reports and trends

### System Updates
- Notify clients of system maintenance windows
- Test new features with pilot clients
- Gradually roll out updates to all clients
- Maintain backward compatibility when possible

## Next Steps

After successful onboarding:
1. Review the [Troubleshooting Guide](troubleshooting-guide.md)
2. Set up monitoring dashboards
3. Configure alerting for client issues
4. Schedule regular client reviews