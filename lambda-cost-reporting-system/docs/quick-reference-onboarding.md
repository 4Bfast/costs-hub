# Quick Reference: Client Onboarding

## Essential Commands

### Generate Sample Configuration
```bash
python cli/main.py client sample-config --output sample-client.json
```

### Add New Client
```bash
# With validation (recommended)
python cli/main.py client add --config client-config.json

# Without AWS validation (faster, for testing)
python cli/main.py client add --config client-config.json --no-validate
```

### List Clients
```bash
# All clients
python cli/main.py client list

# Active clients only
python cli/main.py client list --status active

# JSON format
python cli/main.py client list --format json
```

### Validate Client
```bash
python cli/main.py client validate --client-id CLIENT_ID
```

### Update Client
```bash
python cli/main.py client update --client-id CLIENT_ID --config updated-config.json
```

### Remove Client
```bash
python cli/main.py client remove --client-id CLIENT_ID
```

## Minimum Required IAM Policy

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ce:GetCostAndUsage",
                "ce:GetCostForecast",
                "ce:GetUsageForecast"
            ],
            "Resource": "*"
        }
    ]
}
```

## Sample Client Configuration

```json
{
  "client_name": "Example Company",
  "aws_accounts": [
    {
      "account_id": "123456789012",
      "access_key_id": "AKIAIOSFODNN7EXAMPLE",
      "secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
      "region": "us-east-1",
      "account_name": "Production"
    }
  ],
  "report_config": {
    "weekly_enabled": true,
    "monthly_enabled": true,
    "recipients": ["admin@example.com"],
    "threshold": 1000.0,
    "top_services": 10,
    "include_accounts": true
  },
  "branding": {
    "primary_color": "#1f2937",
    "secondary_color": "#f59e0b",
    "company_name": "Example Company"
  },
  "status": "active"
}
```

## Common Validation Errors

| Error | Solution |
|-------|----------|
| Invalid JSON format | Use `jq . config.json` to validate |
| Invalid email address | Check format: `user@domain.com` |
| Invalid AWS account ID | Must be 12 digits: `123456789012` |
| Invalid color code | Use hex format: `#1f2937` |
| Access denied | Check IAM policy and permissions |

## Testing AWS Access

```bash
# Test Cost Explorer access
aws ce get-cost-and-usage \
  --time-period Start=2023-01-01,End=2023-01-31 \
  --granularity MONTHLY \
  --metrics BlendedCost

# Test credentials
aws sts get-caller-identity
```

## Report Schedule

- **Weekly Reports**: Every Monday at 9:00 AM UTC
- **Monthly Reports**: First day of each month at 8:00 AM UTC

## Support Contacts

For issues during onboarding:
1. Check [Troubleshooting Guide](troubleshooting-guide.md)
2. Review CloudWatch logs: `/aws/lambda/cost-reporting-function`
3. Contact system administrator with error details