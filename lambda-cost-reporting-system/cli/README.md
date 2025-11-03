# Lambda Cost Reporting System - CLI Tools

This directory contains command-line tools for managing and validating client configurations in the Lambda Cost Reporting System.

## Overview

The CLI tools provide comprehensive functionality for:

- **Client Management**: Add, update, remove, and list client configurations
- **Configuration Validation**: Validate AWS credentials, permissions, and configuration completeness
- **Bulk Operations**: Import/export multiple clients, bulk validation
- **Test Report Generation**: Generate test reports to validate the complete workflow

## Installation

The CLI tools require the Lambda Cost Reporting System dependencies. Make sure you have installed the requirements:

```bash
cd lambda-cost-reporting-system
pip install -r requirements.txt
```

## CLI Tools

### 1. Main CLI (`main.py`)

Unified entry point for all CLI operations.

```bash
# Client management
./cli/main.py client add --config client-config.json
./cli/main.py client list --status active

# Configuration validation
./cli/main.py validate single --config client-config.json
./cli/main.py validate bulk --configs config1.json config2.json
```

### 2. Client Manager (`client_manager.py`)

Comprehensive client configuration management.

#### Commands

**Create Sample Configuration**
```bash
./cli/client_manager.py sample-config --output sample-client.json
```

**Add New Client**
```bash
./cli/client_manager.py add --config client-config.json
./cli/client_manager.py add --config client-config.json --no-validate  # Skip AWS validation
```

**Update Existing Client**
```bash
./cli/client_manager.py update --client-id abc123 --config updated-config.json
```

**List Clients**
```bash
./cli/client_manager.py list                           # All clients
./cli/client_manager.py list --status active          # Active clients only
./cli/client_manager.py list --format json            # JSON output
./cli/client_manager.py list --format csv             # CSV output
```

**Remove Client**
```bash
./cli/client_manager.py remove --client-id abc123
./cli/client_manager.py remove --client-id abc123 --confirm  # Skip confirmation
```

**Export Clients**
```bash
./cli/client_manager.py export --output all-clients.json
./cli/client_manager.py export --output active-clients.json --status active
```

**Import Clients**
```bash
./cli/client_manager.py import --input clients-to-import.json
./cli/client_manager.py import --input clients.json --update-existing  # Update existing clients
./cli/client_manager.py import --input clients.json --no-validate      # Skip AWS validation
```

#### Configuration Options

- `--table-name`: DynamoDB table name (default: cost-reporting-clients)
- `--region`: AWS region (default: us-east-1)
- `--kms-key-id`: KMS key ID for encryption (optional)
- `--log-level`: Log level (DEBUG, INFO, WARNING, ERROR)

### 3. Configuration Validator (`validate_config.py`)

Comprehensive configuration validation and testing.

#### Commands

**Validate Single Configuration**
```bash
./cli/validate_config.py single --config client-config.json
./cli/validate_config.py single --config client-config.json --test-report  # Generate test report
./cli/validate_config.py single --config client-config.json --format json --output results.json
```

**Validate Multiple Configurations**
```bash
./cli/validate_config.py bulk --configs config1.json config2.json config3.json
./cli/validate_config.py bulk --configs *.json --output detailed-results.json
```

**Validate Directory**
```bash
./cli/validate_config.py directory --path ./configs
./cli/validate_config.py directory --path ./configs --pattern "client-*.json"
./cli/validate_config.py directory --path ./configs --output validation-results.json
```

**Create Validation Template**
```bash
./cli/validate_config.py template --output validation-checklist.json
```

## Configuration File Format

Client configurations are stored in JSON format. Use the sample-config command to generate a template:

```bash
./cli/client_manager.py sample-config --output sample-client.json
```

### Example Configuration

```json
{
  "client_name": "Example Company",
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
    "recipients": ["admin@example.com", "finance@example.com"],
    "cc_recipients": [],
    "threshold": 1000.0,
    "top_services": 10,
    "include_accounts": true,
    "alert_thresholds": []
  },
  "branding": {
    "logo_s3_key": null,
    "primary_color": "#1f2937",
    "secondary_color": "#f59e0b",
    "company_name": "Example Company",
    "email_footer": "This is an automated cost report from Example Company."
  },
  "status": "active"
}
```

## Validation Checks

The configuration validator performs comprehensive checks:

### Basic Configuration
- Client name is present and valid
- Client ID is present (auto-generated if missing)
- At least one AWS account is configured
- No duplicate AWS account IDs

### AWS Credentials
- Account IDs are 12-digit numbers
- Access keys have correct format (AKIA...)
- Secret access keys are present and valid
- Regions are specified
- Credentials can authenticate with AWS
- Account IDs match credential accounts

### AWS Permissions
- Cost Explorer access (`ce:GetCostAndUsage`)
- Cost forecasting access (`ce:GetUsageForecast`, `ce:GetCostForecast`)
- Cost data is available for accounts

### Report Configuration
- At least one report type enabled (weekly/monthly)
- At least one recipient email configured
- Email addresses have valid format
- Threshold is non-negative
- Top services count is reasonable (1-50)

### Branding Configuration
- Primary color has valid hex format (#RRGGBB)
- Secondary color has valid hex format (#RRGGBB)
- Logo S3 key is accessible (if configured)
- Company name is present (optional)

### Test Report Generation
- Cost data can be retrieved from AWS
- HTML report can be generated
- Email template can be created

## Required AWS Permissions

Client AWS accounts need the following IAM permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ce:GetCostAndUsage",
        "ce:GetUsageForecast",
        "ce:GetCostForecast"
      ],
      "Resource": "*"
    }
  ]
}
```

## Common Workflows

### Onboarding New Client

1. **Create configuration file**:
   ```bash
   ./cli/client_manager.py sample-config --output new-client.json
   # Edit new-client.json with client details
   ```

2. **Validate configuration**:
   ```bash
   ./cli/validate_config.py single --config new-client.json --test-report
   ```

3. **Add client if validation passes**:
   ```bash
   ./cli/client_manager.py add --config new-client.json
   ```

### Bulk Client Import

1. **Prepare configuration files**:
   ```bash
   # Create multiple JSON files or one file with array of configs
   ```

2. **Validate all configurations**:
   ```bash
   ./cli/validate_config.py directory --path ./client-configs --output validation-results.json
   ```

3. **Import valid configurations**:
   ```bash
   ./cli/client_manager.py import --input valid-clients.json
   ```

### Client Maintenance

1. **List all clients**:
   ```bash
   ./cli/client_manager.py list --format table
   ```

2. **Validate existing client**:
   ```bash
   ./cli/client_manager.py validate --client-id abc123
   ```

3. **Update client configuration**:
   ```bash
   ./cli/client_manager.py update --client-id abc123 --config updated-config.json
   ```

4. **Export client configurations for backup**:
   ```bash
   ./cli/client_manager.py export --output backup-$(date +%Y%m%d).json
   ```

## Error Handling

The CLI tools provide comprehensive error handling and reporting:

- **Configuration Errors**: Invalid JSON, missing required fields, validation failures
- **AWS Errors**: Invalid credentials, missing permissions, connectivity issues
- **System Errors**: File not found, permission denied, network timeouts

All errors are logged with appropriate detail levels and user-friendly messages.

## Environment Variables

You can set the following environment variables to avoid repeating common options:

```bash
export COST_REPORTING_TABLE_NAME="cost-reporting-clients"
export COST_REPORTING_REGION="us-east-1"
export COST_REPORTING_KMS_KEY_ID="arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012"
```

## Troubleshooting

### Common Issues

1. **"Module not found" errors**:
   - Ensure you're running from the lambda-cost-reporting-system directory
   - Check that all dependencies are installed: `pip install -r requirements.txt`

2. **AWS credential validation failures**:
   - Verify access key format (must start with AKIA)
   - Check that credentials belong to the specified account
   - Ensure Cost Explorer permissions are granted

3. **DynamoDB connection errors**:
   - Verify AWS credentials for CLI execution
   - Check that the DynamoDB table exists
   - Ensure proper IAM permissions for table access

4. **Test report generation failures**:
   - Check that accounts have cost data available
   - Verify Cost Explorer permissions
   - Ensure accounts are not brand new (may have no cost data)

### Debug Mode

Enable debug logging for detailed troubleshooting:

```bash
./cli/client_manager.py --log-level DEBUG list
./cli/validate_config.py --log-level DEBUG single --config client.json
```

## Security Considerations

- **Credential Storage**: AWS credentials are encrypted using KMS when stored in DynamoDB
- **Temporary Files**: Test reports are stored in temporary files that should be cleaned up
- **Logging**: Sensitive information (credentials) is masked in log output
- **File Permissions**: Configuration files may contain sensitive data - ensure proper file permissions

## Contributing

When adding new CLI functionality:

1. Follow the existing pattern of separate CLI modules
2. Add comprehensive help text and examples
3. Include proper error handling and logging
4. Add validation for all inputs
5. Update this README with new functionality