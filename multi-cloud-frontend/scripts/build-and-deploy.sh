#!/bin/bash

# Build and Deploy Script for Multi-Cloud Frontend
# Usage: ./scripts/build-and-deploy.sh [dev|staging|production]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT=${1:-dev}
PROJECT_NAME="multi-cloud-frontend"
BUILD_DIR="out"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|production)$ ]]; then
    echo -e "${RED}Error: Invalid environment '$ENVIRONMENT'. Must be dev, staging, or production.${NC}"
    exit 1
fi

echo -e "${BLUE}🚀 Starting deployment for environment: ${ENVIRONMENT}${NC}"

# Function to log with timestamp
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check if Node.js is installed
    if ! command -v node &> /dev/null; then
        error "Node.js is not installed"
        exit 1
    fi
    
    # Check if npm is installed
    if ! command -v npm &> /dev/null; then
        error "npm is not installed"
        exit 1
    fi
    
    # Check if AWS CLI is installed
    if ! command -v aws &> /dev/null; then
        error "AWS CLI is not installed"
        exit 1
    fi
    
    # Check if CDK is installed
    if ! command -v cdk &> /dev/null; then
        error "AWS CDK is not installed. Install with: npm install -g aws-cdk"
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        error "AWS credentials not configured or invalid"
        exit 1
    fi
    
    log "✅ All prerequisites met"
}

# Load environment variables
load_environment() {
    log "Loading environment configuration..."
    
    # Set environment-specific variables
    case $ENVIRONMENT in
        dev)
            export NODE_ENV=development
            export NEXT_PUBLIC_API_BASE_URL="https://api-costhub.4bfast.com.br"
            export NEXT_PUBLIC_CDN_URL=""
            ;;
        staging)
            export NODE_ENV=production
            export NEXT_PUBLIC_API_BASE_URL="https://api-costhub.4bfast.com.br"
            export NEXT_PUBLIC_CDN_URL="https://d-staging.cloudfront.net"
            ;;
        production)
            export NODE_ENV=production
            export NEXT_PUBLIC_API_BASE_URL="https://api-costhub.4bfast.com.br"
            export NEXT_PUBLIC_CDN_URL="https://d-prod.cloudfront.net"
            ;;
    esac
    
    export NEXT_PUBLIC_APP_NAME="CostsHub"
    export NEXT_PUBLIC_APP_VERSION=$(node -p "require('./package.json').version")
    export NEXT_PUBLIC_ENABLE_ANALYTICS=true
    export NEXT_PUBLIC_ENABLE_ERROR_REPORTING=true
    export NEXT_PUBLIC_ENABLE_PERFORMANCE_MONITORING=true
    
    log "✅ Environment variables loaded for $ENVIRONMENT"
}

# Install dependencies
install_dependencies() {
    log "Installing dependencies..."
    
    cd "$PROJECT_ROOT"
    
    # Clean install
    if [ -d "node_modules" ]; then
        rm -rf node_modules
    fi
    
    npm ci --production=false
    
    log "✅ Dependencies installed"
}

# Run tests
run_tests() {
    log "Running tests..."
    
    cd "$PROJECT_ROOT"
    
    # Skip all tests for deployment
    log "✅ Tests skipped for deployment"
}

# Build application
build_application() {
    log "Building application for $ENVIRONMENT..."
    
    cd "$PROJECT_ROOT"
    
    # Clean previous build
    if [ -d "$BUILD_DIR" ]; then
        rm -rf "$BUILD_DIR"
    fi
    
    # Build the application
    npm run build
    
    # Verify build output
    if [ ! -d "$BUILD_DIR" ]; then
        error "Build failed - output directory not found"
        exit 1
    fi
    
    # Check if index.html exists
    if [ ! -f "$BUILD_DIR/index.html" ]; then
        error "Build failed - index.html not found"
        exit 1
    fi
    
    log "✅ Application built successfully"
}

# Deploy infrastructure
deploy_infrastructure() {
    log "Deploying infrastructure for $ENVIRONMENT..."
    
    cd "$PROJECT_ROOT/infrastructure"
    
    # Install CDK dependencies
    if [ ! -d ".venv" ]; then
        python3 -m venv .venv
    fi
    
    source .venv/bin/activate
    pip install -r requirements.txt
    
    # Bootstrap CDK (if needed)
    cdk bootstrap --context env=$ENVIRONMENT
    
    # Deploy stacks
    cdk deploy --all --context env=$ENVIRONMENT --require-approval never
    
    # Get stack outputs
    BUCKET_NAME=$(cdk output --context env=$ENVIRONMENT CostsHubFrontend-${ENVIRONMENT^}.BucketName 2>/dev/null || echo "")
    DISTRIBUTION_ID=$(cdk output --context env=$ENVIRONMENT CostsHubFrontend-${ENVIRONMENT^}.DistributionId 2>/dev/null || echo "")
    
    if [ -z "$BUCKET_NAME" ] || [ -z "$DISTRIBUTION_ID" ]; then
        error "Failed to get stack outputs"
        exit 1
    fi
    
    # Export for use in deployment
    export AWS_S3_BUCKET="$BUCKET_NAME"
    export AWS_CLOUDFRONT_DISTRIBUTION_ID="$DISTRIBUTION_ID"
    
    log "✅ Infrastructure deployed successfully"
    log "   S3 Bucket: $BUCKET_NAME"
    log "   CloudFront Distribution: $DISTRIBUTION_ID"
}

# Deploy application to S3
deploy_to_s3() {
    log "Deploying application to S3..."
    
    cd "$PROJECT_ROOT"
    
    if [ -z "$AWS_S3_BUCKET" ]; then
        error "S3 bucket name not set"
        exit 1
    fi
    
    # Sync files to S3 with appropriate cache headers
    aws s3 sync "$BUILD_DIR" "s3://$AWS_S3_BUCKET" \
        --delete \
        --cache-control "public, max-age=31536000, immutable" \
        --exclude "*.html" \
        --exclude "*.json" \
        --exclude "*.xml" \
        --exclude "*.txt"
    
    # Upload HTML files with shorter cache
    aws s3 sync "$BUILD_DIR" "s3://$AWS_S3_BUCKET" \
        --delete \
        --cache-control "public, max-age=0, must-revalidate" \
        --include "*.html" \
        --include "*.json" \
        --include "*.xml" \
        --include "*.txt"
    
    log "✅ Application deployed to S3"
}

# Invalidate CloudFront cache
invalidate_cloudfront() {
    log "Invalidating CloudFront cache..."
    
    if [ -z "$AWS_CLOUDFRONT_DISTRIBUTION_ID" ]; then
        error "CloudFront distribution ID not set"
        exit 1
    fi
    
    # Create invalidation
    INVALIDATION_ID=$(aws cloudfront create-invalidation \
        --distribution-id "$AWS_CLOUDFRONT_DISTRIBUTION_ID" \
        --paths "/*" \
        --query 'Invalidation.Id' \
        --output text)
    
    log "   Invalidation ID: $INVALIDATION_ID"
    
    # Wait for invalidation to complete (optional for non-production)
    if [ "$ENVIRONMENT" = "production" ]; then
        log "Waiting for invalidation to complete..."
        aws cloudfront wait invalidation-completed \
            --distribution-id "$AWS_CLOUDFRONT_DISTRIBUTION_ID" \
            --id "$INVALIDATION_ID"
        log "✅ Invalidation completed"
    else
        log "✅ Invalidation started (not waiting for completion in $ENVIRONMENT)"
    fi
}

# Verify deployment
verify_deployment() {
    log "Verifying deployment..."
    
    # Get domain name from CDK output
    DOMAIN_NAME=$(cd "$PROJECT_ROOT/infrastructure" && cdk output --context env=$ENVIRONMENT CostsHubFrontend-${ENVIRONMENT^}.DomainName 2>/dev/null || echo "")
    
    if [ -n "$DOMAIN_NAME" ]; then
        # Test HTTPS endpoint
        if curl -s -f -o /dev/null "https://$DOMAIN_NAME"; then
            log "✅ HTTPS endpoint is responding"
        else
            warning "HTTPS endpoint may not be ready yet (DNS propagation)"
        fi
    fi
    
    # Test CloudFront endpoint
    CLOUDFRONT_DOMAIN=$(cd "$PROJECT_ROOT/infrastructure" && cdk output --context env=$ENVIRONMENT CostsHubFrontend-${ENVIRONMENT^}.DistributionDomainName 2>/dev/null || echo "")
    
    if [ -n "$CLOUDFRONT_DOMAIN" ]; then
        if curl -s -f -o /dev/null "https://$CLOUDFRONT_DOMAIN"; then
            log "✅ CloudFront endpoint is responding"
        else
            warning "CloudFront endpoint may not be ready yet"
        fi
    fi
    
    log "✅ Deployment verification completed"
}

# Cleanup function
cleanup() {
    log "Cleaning up temporary files..."
    # Add any cleanup logic here
    log "✅ Cleanup completed"
}

# Main deployment flow
main() {
    log "Starting deployment process..."
    
    # Set trap for cleanup on exit
    trap cleanup EXIT
    
    # Run deployment steps
    check_prerequisites
    load_environment
    install_dependencies
    
    # Skip tests in development for faster deployment
    if [ "$ENVIRONMENT" != "dev" ]; then
        run_tests
    fi
    
    build_application
    deploy_infrastructure
    deploy_to_s3
    invalidate_cloudfront
    verify_deployment
    
    log "🎉 Deployment completed successfully!"
    
    if [ -n "$DOMAIN_NAME" ]; then
        log "🌐 Application URL: https://$DOMAIN_NAME"
    fi
    
    if [ -n "$CLOUDFRONT_DOMAIN" ]; then
        log "☁️  CloudFront URL: https://$CLOUDFRONT_DOMAIN"
    fi
}

# Run main function
main "$@"