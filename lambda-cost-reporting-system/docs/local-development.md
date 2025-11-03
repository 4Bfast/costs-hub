# Local Development Setup

This guide explains how to set up the Lambda Cost Reporting System for local development.

## Prerequisites

- Python 3.9+
- Docker and Docker Compose
- AWS CLI (for LocalStack interaction)
- Make (optional, for using Makefile commands)

## Quick Start

1. **Set up the development environment:**
   ```bash
   make dev-setup
   ```
   
   Or manually:
   ```bash
   pip install -r requirements-dev.txt
   ./scripts/setup-local.sh
   ```

2. **Test the setup:**
   ```bash
   make dev-test
   ```
   
   Or manually:
   ```bash
   ./scripts/test-local.sh
   pytest
   ```

3. **Start developing:**
   - LocalStack services are running at http://localhost:4566
   - DynamoDB Admin UI is available at http://localhost:8001
   - All AWS services are mocked locally

## Local Services

### LocalStack
- **URL:** http://localhost:4566
- **Services:** Lambda, DynamoDB, S3, SES, EventBridge, SNS, CloudWatch, KMS
- **Admin UI:** Use AWS CLI with `--endpoint-url=http://localhost:4566`

### DynamoDB Admin
- **URL:** http://localhost:8001
- **Purpose:** Visual interface for DynamoDB tables
- **Tables:** `cost-reporting-local-clients`

## Environment Variables

Local development uses environment variables from `config/local.env`:

```bash
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_DEFAULT_REGION=us-east-1
AWS_ENDPOINT_URL=http://localhost:4566
ENVIRONMENT=local
DYNAMODB_TABLE_NAME=cost-reporting-local-clients
S3_BUCKET_NAME=cost-reporting-local-reports
KMS_KEY_ID=alias/cost-reporting-local-key
```

## Testing

### Unit Tests
```bash
pytest tests/unit -v
```

### Integration Tests (requires LocalStack)
```bash
# Start LocalStack first
make setup-local

# Run integration tests
pytest tests/integration -v
```

### All Tests
```bash
make test
```

## Development Workflow

1. **Start local services:**
   ```bash
   make setup-local
   ```

2. **Make code changes in `src/`**

3. **Run tests:**
   ```bash
   make test
   ```

4. **Test locally:**
   ```bash
   make test-local
   ```

5. **Clean up when done:**
   ```bash
   make cleanup-local
   ```

## Troubleshooting

### LocalStack not starting
- Ensure Docker is running
- Check if ports 4566 and 8001 are available
- Try: `docker-compose down -v && docker-compose up -d`

### Tests failing
- Ensure LocalStack is running: `make test-local`
- Check environment variables are set correctly
- Verify AWS CLI can connect: `aws --endpoint-url=http://localhost:4566 s3 ls`

### Permission errors
- Ensure scripts are executable: `chmod +x scripts/*.sh`
- Check Docker permissions for your user

## Useful Commands

```bash
# View LocalStack logs
docker-compose logs -f localstack

# Reset LocalStack data
docker-compose down -v && docker-compose up -d

# Test AWS services manually
aws --endpoint-url=http://localhost:4566 dynamodb list-tables
aws --endpoint-url=http://localhost:4566 s3 ls
aws --endpoint-url=http://localhost:4566 kms list-keys

# Run specific test files
pytest tests/test_setup.py -v
pytest tests/unit/test_models.py -v
```