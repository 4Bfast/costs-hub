# AWS IAM Policy Templates

## Overview

This document provides AWS IAM policy templates that clients need to configure in their AWS accounts to enable the Lambda Cost Reporting System to access their cost data.

## Basic Cost Explorer Policy (Recommended)

This is the minimum required policy for basic cost reporting functionality:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "CostExplorerBasicAccess",
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

## Comprehensive Cost Explorer Policy (Full Features)

This policy provides access to all Cost Explorer features for enhanced reporting:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "CostExplorerFullAccess",
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
                "ce:ListCostCategoryDefinitions",
                "ce:GetRightsizingRecommendation"
            ],
            "Resource": "*"
        }
    ]
}
```

## Enhanced Policy with Billing Access

For clients who want detailed billing information in their reports:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "CostExplorerAccess",
            "Effect": "Allow",
            "Action": [
                "ce:GetCostAndUsage",
                "ce:GetCostForecast",
                "ce:GetUsageForecast",
                "ce:GetCostCategories",
                "ce:GetDimensionValues",
                "ce:GetReservationCoverage",
                "ce:GetReservationUtilization",
                "ce:GetSavingsPlansUtilization",
                "ce:GetSavingsPlansCoverage"
            ],
            "Resource": "*"
        },
        {
            "Sid": "BillingReadAccess",
            "Effect": "Allow",
            "Action": [
                "aws-portal:ViewBilling",
                "aws-portal:ViewUsage",
                "aws-portal:ViewAccount"
            ],
            "Resource": "*"
        }
    ]
}
```

## Cross-Account Role Policy (Advanced)

For enhanced security, clients can create a cross-account role instead of using access keys:

### Trust Policy for the Role

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::YOUR_LAMBDA_ACCOUNT_ID:role/lambda-cost-reporting-role"
            },
            "Action": "sts:AssumeRole",
            "Condition": {
                "StringEquals": {
                    "sts:ExternalId": "unique-external-id-for-client"
                }
            }
        }
    ]
}
```

### Permissions Policy for the Role

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "CostReportingAccess",
            "Effect": "Allow",
            "Action": [
                "ce:GetCostAndUsage",
                "ce:GetCostForecast",
                "ce:GetUsageForecast",
                "ce:GetCostCategories",
                "ce:GetDimensionValues"
            ],
            "Resource": "*"
        }
    ]
}
```

## Organization Master Account Policy

For clients using AWS Organizations who want to report on all member accounts:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "OrganizationCostAccess",
            "Effect": "Allow",
            "Action": [
                "ce:GetCostAndUsage",
                "ce:GetCostForecast",
                "ce:GetUsageForecast",
                "ce:GetCostCategories",
                "ce:GetDimensionValues",
                "organizations:ListAccounts",
                "organizations:DescribeOrganization",
                "organizations:ListRoots",
                "organizations:ListOrganizationalUnitsForParent",
                "organizations:ListAccountsForParent"
            ],
            "Resource": "*"
        }
    ]
}
```

## Restricted Policy with Resource Constraints

For clients who want to limit access to specific cost categories or time periods:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "RestrictedCostAccess",
            "Effect": "Allow",
            "Action": [
                "ce:GetCostAndUsage",
                "ce:GetCostForecast"
            ],
            "Resource": "*",
            "Condition": {
                "DateGreaterThan": {
                    "aws:RequestedRegion": "2023-01-01"
                },
                "StringLike": {
                    "ce:Service": [
                        "Amazon Elastic Compute Cloud - Compute",
                        "Amazon Simple Storage Service",
                        "Amazon Relational Database Service"
                    ]
                }
            }
        }
    ]
}
```

## Policy Implementation Instructions

### Method 1: IAM User with Programmatic Access

1. **Create IAM User**:
   ```bash
   aws iam create-user --user-name cost-reporting-user
   ```

2. **Create and Attach Policy**:
   ```bash
   # Create policy from JSON file
   aws iam create-policy \
     --policy-name CostReportingPolicy \
     --policy-document file://cost-reporting-policy.json
   
   # Attach policy to user
   aws iam attach-user-policy \
     --user-name cost-reporting-user \
     --policy-arn arn:aws:iam::ACCOUNT_ID:policy/CostReportingPolicy
   ```

3. **Create Access Keys**:
   ```bash
   aws iam create-access-key --user-name cost-reporting-user
   ```

### Method 2: IAM Role for Cross-Account Access

1. **Create Role**:
   ```bash
   aws iam create-role \
     --role-name cost-reporting-cross-account-role \
     --assume-role-policy-document file://trust-policy.json
   ```

2. **Attach Permissions Policy**:
   ```bash
   aws iam attach-role-policy \
     --role-name cost-reporting-cross-account-role \
     --policy-arn arn:aws:iam::ACCOUNT_ID:policy/CostReportingPolicy
   ```

### Method 3: Using AWS Console

1. Navigate to IAM in the AWS Console
2. Choose "Users" or "Roles" depending on your preferred method
3. Click "Create user" or "Create role"
4. For users: Select "Programmatic access"
5. For roles: Choose "Another AWS account" and enter the Lambda system account ID
6. Create a custom policy using one of the JSON templates above
7. Attach the policy to the user or role
8. For users: Save the Access Key ID and Secret Access Key
9. For roles: Note the Role ARN for configuration

## Policy Selection Guide

Choose the appropriate policy based on your requirements:

| Use Case | Recommended Policy | Notes |
|----------|-------------------|-------|
| Basic cost reporting | Basic Cost Explorer Policy | Minimal permissions, fastest setup |
| Comprehensive reporting | Comprehensive Cost Explorer Policy | Full Cost Explorer features |
| Detailed billing analysis | Enhanced Policy with Billing Access | Includes billing portal access |
| Multi-account organizations | Organization Master Account Policy | Requires master account setup |
| High security environments | Cross-Account Role Policy | Most secure, requires additional setup |
| Compliance/audit requirements | Restricted Policy with Resource Constraints | Customizable restrictions |

## Security Considerations

### Access Key Management
- **Rotation**: Rotate access keys every 90 days
- **Monitoring**: Enable CloudTrail to monitor API usage
- **Least Privilege**: Use the minimal policy that meets your needs
- **Separation**: Use dedicated users/roles only for cost reporting

### Role-Based Access (Recommended)
- **External ID**: Always use an external ID for cross-account roles
- **Time-based Access**: Consider adding time-based conditions
- **IP Restrictions**: Add IP address restrictions if possible
- **MFA**: Require MFA for sensitive operations

### Monitoring and Auditing
- **CloudTrail**: Enable CloudTrail logging for all Cost Explorer API calls
- **Access Logging**: Monitor who accesses cost data and when
- **Anomaly Detection**: Set up AWS Config rules to detect policy changes
- **Regular Reviews**: Review and audit permissions quarterly

## Troubleshooting Common Issues

### Permission Denied Errors
- Verify the policy is attached correctly
- Check for typos in action names
- Ensure the user/role has the necessary permissions
- Verify account ID in cross-account scenarios

### Access Key Issues
- Confirm access keys are active
- Check for key rotation requirements
- Verify keys haven't been accidentally deleted
- Test keys with AWS CLI before using in the system

### Cross-Account Role Issues
- Verify trust policy allows the correct account
- Check external ID matches configuration
- Ensure role ARN is correct in client configuration
- Test role assumption manually

## Policy Validation

Before implementing any policy, validate it using:

### AWS Policy Simulator
1. Go to the IAM Policy Simulator in AWS Console
2. Select the user/role
3. Test the specific Cost Explorer actions
4. Verify all required permissions work

### AWS CLI Testing
```bash
# Test basic cost access
aws ce get-cost-and-usage \
  --time-period Start=2023-01-01,End=2023-01-31 \
  --granularity MONTHLY \
  --metrics BlendedCost

# Test forecast access
aws ce get-cost-forecast \
  --time-period Start=2023-02-01,End=2023-02-28 \
  --metric BLENDED_COST \
  --granularity MONTHLY
```

### Integration Testing
Use the Lambda Cost Reporting System's validation tools:
```bash
# Validate client configuration
python cli/main.py validate single --config client-config.json

# Test report generation
python cli/main.py client validate --client-id CLIENT_ID
```

## Policy Updates and Maintenance

### Regular Maintenance
- Review policies quarterly for new AWS features
- Update policies when new Cost Explorer APIs are released
- Remove unused permissions to maintain least privilege
- Document any custom modifications

### Version Control
- Keep policy templates in version control
- Tag policy versions with dates and changes
- Maintain changelog for policy modifications
- Test policy changes in development environment first

### Client Communication
- Notify clients of required policy updates
- Provide migration guides for policy changes
- Offer assistance with policy implementation
- Document any breaking changes clearly