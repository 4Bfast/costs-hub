#!/bin/bash

# Setup script for local development environment

set -e

echo "Setting up Lambda Cost Reporting System - Local Development"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if docker compose is available
if ! command -v docker compose &> /dev/null; then
    echo "Error: docker compose is not installed. Please install docker compose and try again."
    exit 1
fi

# Start LocalStack services
echo "Starting LocalStack services..."
docker compose up -d

# Wait for LocalStack to be ready
# echo "Waiting for LocalStack to be ready..."
# sleep 10

# Check if LocalStack is ready
max_attempts=30
attempt=1
# while [ $attempt -le $max_attempts ]; do
#     if curl -s http://localhost:4566/_localstack/health | grep -q '"dynamodb": "available"'; then
#         echo "LocalStack is ready!"
#         break
#     fi
#     echo "Attempt $attempt/$max_attempts: LocalStack not ready yet, waiting..."
#     sleep 2
#     attempt=$((attempt + 1))
# done

if [ $attempt -gt $max_attempts ]; then
    echo "Error: LocalStack failed to start within expected time"
    exit 1
fi

# Load environment variables
export $(grep -v '^#' config/local.env | grep -v '^$' | xargs)

# Create local AWS resources
echo "Creating local AWS resources..."

# Create DynamoDB table
# aws --endpoint-url=http://localhost:4566 dynamodb create-table \
#     --table-name $DYNAMODB_TABLE_NAME \
#     --attribute-definitions '[{"AttributeName":"client_id","AttributeType":"S"},{"AttributeName":"status","AttributeType":"S"}]' \
#     --key-schema '[{"AttributeName":"client_id","KeyType":"HASH"}]' \
#     --global-secondary-indexes '[{"IndexName":"status-index","KeySchema":[{"AttributeName":"status","KeyType":"HASH"}],"Projection":{"ProjectionType":"ALL"},"ProvisionedThroughput":{"ReadCapacityUnits":5,"WriteCapacityUnits":5}}]' \
#     --provisioned-throughput '{"ReadCapacityUnits":5,"WriteCapacityUnits":5}' \
#     --region us-east-1

# Create S3 bucket
# aws --endpoint-url=http://localhost:4566 s3 mb s3://$S3_BUCKET_NAME --region us-east-1

# # Create KMS key
# KMS_KEY_OUTPUT=$(aws --endpoint-url=http://localhost:4566 kms create-key \
#     --description "Cost Reporting Local Key" \
#     --region us-east-1)

# KMS_KEY_ID=$(echo $KMS_KEY_OUTPUT | python3 -c "import sys, json; print(json.load(sys.stdin)['KeyMetadata']['KeyId'])")

# # Create KMS alias
# aws --endpoint-url=http://localhost:4566 kms create-alias \
#     --alias-name alias/cost-reporting-local-key \
#     --target-key-id $KMS_KEY_ID \
#     --region us-east-1

# Create SNS topic
# aws --endpoint-url=http://localhost:4566 sns create-topic \
#     --name cost-reporting-local-admin-alerts \
#     --region us-east-1

echo ""
echo "Local development environment setup complete!"
echo ""
echo "Services available:"
echo "- LocalStack: http://localhost:4566"
echo "- DynamoDB Admin: http://localhost:8001"
echo ""
echo "To stop the environment, run: docker compose down"
echo "To view logs, run: docker compose logs -f"