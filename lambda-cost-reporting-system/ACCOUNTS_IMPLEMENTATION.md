# Accounts API - Real DynamoDB Implementation

## Overview

This implementation replaces the mock account management with real DynamoDB persistence, following the DEVELOPMENT_SPEC.md Phase 1 requirements.

## What Was Implemented

### ✅ Real DynamoDB Table
- **Table Name**: `costhub-accounts`
- **Partition Key**: `account_id` (String)
- **Billing Mode**: Pay-per-request
- **Features**: Point-in-time recovery enabled

### ✅ Real Handlers
- **File**: `src/handlers/accounts_handler.py`
- **GET /api/v1/accounts**: Retrieves all accounts from DynamoDB
- **POST /api/v1/accounts**: Creates new account with validation

### ✅ Updated API Integration
- **File**: `src/simple_handlers/api_gateway_handler_simple.py`
- **Change**: Now calls real handlers instead of mock responses
- **Permissions**: Lambda has DynamoDB read/write access

## Deployment Steps

### 1. Deploy Accounts Table
```bash
cd lambda-cost-reporting-system/infrastructure
./deploy-accounts-table.sh
```

### 2. Update API Lambda Function
```bash
# Deploy updated Lambda with DynamoDB permissions
./deploy-frontend-api.sh
```

### 3. Test Implementation
```bash
cd lambda-cost-reporting-system
python3 test_accounts_api.py
```

## API Schema

### POST /api/v1/accounts
**Request Body:**
```json
{
  "name": "My AWS Account",
  "provider_type": "aws",
  "credentials": {
    "access_key_id": "AKIA...",
    "secret_access_key": "***",
    "region": "us-east-1"
  }
}
```

**Response (201):**
```json
{
  "message": "Account created successfully",
  "account": {
    "account_id": "uuid-generated",
    "name": "My AWS Account",
    "provider_type": "aws",
    "credentials": {...},
    "status": "active",
    "created_at": "2025-11-03T00:00:00Z",
    "updated_at": "2025-11-03T00:00:00Z"
  }
}
```

### GET /api/v1/accounts
**Response (200):**
```json
{
  "message": "Accounts retrieved successfully",
  "accounts": [...],
  "count": 2
}
```

## Validation

### Required Fields
- `name`: Account display name
- `provider_type`: Provider type (aws, gcp, azure)

### Optional Fields
- `credentials`: Provider-specific credentials
- `status`: Defaults to "active"

## Next Steps (Phase 2)

1. **Cost Data Collection Table**
   - Create `costhub-cost-data` table
   - Implement AWS Cost Explorer integration
   - Add scheduled data collection

2. **Provider Credential Validation**
   - Test AWS credentials before saving
   - Encrypt sensitive credential data
   - Add credential rotation support

3. **Enhanced Security**
   - Implement field-level encryption
   - Add audit logging
   - Implement access controls

## Files Modified/Created

### New Files
- `src/handlers/accounts_handler.py` - Real DynamoDB handlers
- `infrastructure/stacks/accounts_table_stack.py` - Table definition
- `infrastructure/app_accounts.py` - CDK app for table
- `infrastructure/deploy-accounts-table.sh` - Deploy script
- `test_accounts_api.py` - API test script

### Modified Files
- `src/simple_handlers/api_gateway_handler_simple.py` - Use real handlers
- `infrastructure/stacks/frontend_api_stack.py` - Add DynamoDB permissions

## Troubleshooting

### Common Issues

1. **Permission Denied**
   - Ensure Lambda has DynamoDB permissions
   - Check table name matches in code

2. **Table Not Found**
   - Deploy accounts table first
   - Verify table name in AWS Console

3. **CORS Issues**
   - Check origin matches allowed origins
   - Verify headers are properly set

### Verification Commands

```bash
# Check if table exists
aws dynamodb describe-table --table-name costhub-accounts

# Check Lambda permissions
aws iam get-role-policy --role-name [lambda-role] --policy-name [policy-name]

# Test API directly
curl -X POST https://api-costhub.4bfast.com.br/api/v1/accounts \
  -H "Content-Type: application/json" \
  -H "Origin: https://costhub.4bfast.com.br" \
  -d '{"name":"Test","provider_type":"aws"}'
```
