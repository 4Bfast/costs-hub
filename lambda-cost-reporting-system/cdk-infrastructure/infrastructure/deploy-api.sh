#!/bin/bash

# Deploy API Gateway for Multi-Cloud Cost Analytics
# Usage: ./deploy-api.sh [environment] [options]

set -e

# Default values
ENVIRONMENT=${1:-dev}
PROFILE=${AWS_PROFILE:-default}
REGION=${AWS_DEFAULT_REGION:-us-east-1}
ACCOUNT=${CDK_DEFAULT_ACCOUNT}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if AWS CLI is installed
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi
    
    # Check if CDK is installed
    if ! command -v cdk &> /dev/null; then
        print_error "AWS CDK is not installed. Please install it first."
        exit 1
    fi
    
    # Check if Python is installed
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed. Please install it first."
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity --profile $PROFILE &> /dev/null; then
        print_error "AWS credentials not configured or invalid for profile: $PROFILE"
        exit 1
    fi
    
    # Get account ID if not set
    if [ -z "$ACCOUNT" ]; then
        ACCOUNT=$(aws sts get-caller-identity --profile $PROFILE --query Account --output text)
        export CDK_DEFAULT_ACCOUNT=$ACCOUNT
    fi
    
    print_success "Prerequisites check passed"
}

# Function to install dependencies
install_dependencies() {
    print_status "Installing Python dependencies..."
    
    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi
    
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    
    print_success "Dependencies installed"
}

# Function to validate environment configuration
validate_environment() {
    print_status "Validating environment configuration for: $ENVIRONMENT"
    
    case $ENVIRONMENT in
        dev|staging|prod)
            print_success "Valid environment: $ENVIRONMENT"
            ;;
        *)
            print_error "Invalid environment: $ENVIRONMENT. Must be one of: dev, staging, prod"
            exit 1
            ;;
    esac
    
    # Check if JWT secret is set for production
    if [ "$ENVIRONMENT" = "prod" ] && [ -z "$JWT_SECRET" ]; then
        print_warning "JWT_SECRET not set for production environment"
        print_warning "Using default secret - CHANGE THIS IN PRODUCTION!"
    fi
}

# Function to bootstrap CDK (if needed)
bootstrap_cdk() {
    print_status "Checking CDK bootstrap status..."
    
    # Check if CDK is already bootstrapped
    if aws cloudformation describe-stacks --stack-name CDKToolkit --profile $PROFILE --region $REGION &> /dev/null; then
        print_success "CDK already bootstrapped"
    else
        print_status "Bootstrapping CDK..."
        cdk bootstrap aws://$ACCOUNT/$REGION --profile $PROFILE
        print_success "CDK bootstrapped successfully"
    fi
}

# Function to synthesize CDK templates
synthesize_templates() {
    print_status "Synthesizing CDK templates..."
    
    export ENVIRONMENT=$ENVIRONMENT
    export CDK_DEFAULT_ACCOUNT=$ACCOUNT
    export CDK_DEFAULT_REGION=$REGION
    
    cdk synth --profile $PROFILE
    
    print_success "CDK templates synthesized"
}

# Function to deploy stacks
deploy_stacks() {
    print_status "Deploying stacks for environment: $ENVIRONMENT"
    
    export ENVIRONMENT=$ENVIRONMENT
    export CDK_DEFAULT_ACCOUNT=$ACCOUNT
    export CDK_DEFAULT_REGION=$REGION
    
    # Deploy main stack first
    print_status "Deploying main cost reporting stack..."
    cdk deploy lambda-cost-reporting-$ENVIRONMENT \
        --profile $PROFILE \
        --require-approval never \
        --outputs-file outputs-main-$ENVIRONMENT.json
    
    # Deploy API Gateway stack
    print_status "Deploying API Gateway stack..."
    cdk deploy cost-analytics-api-$ENVIRONMENT \
        --profile $PROFILE \
        --require-approval never \
        --outputs-file outputs-api-$ENVIRONMENT.json
    
    print_success "All stacks deployed successfully"
}

# Function to display deployment outputs
display_outputs() {
    print_status "Deployment outputs:"
    
    if [ -f "outputs-api-$ENVIRONMENT.json" ]; then
        echo ""
        echo "API Gateway Information:"
        echo "======================="
        
        # Extract API Gateway URL
        API_URL=$(jq -r ".\"cost-analytics-api-$ENVIRONMENT\".APIGatewayStageURL // empty" outputs-api-$ENVIRONMENT.json 2>/dev/null || echo "")
        if [ -n "$API_URL" ]; then
            echo "API URL: $API_URL"
        fi
        
        # Extract custom domain URL if available
        CUSTOM_URL=$(jq -r ".\"cost-analytics-api-$ENVIRONMENT\".CustomDomainURL // empty" outputs-api-$ENVIRONMENT.json 2>/dev/null || echo "")
        if [ -n "$CUSTOM_URL" ]; then
            echo "Custom Domain URL: $CUSTOM_URL"
        fi
        
        # Extract API Gateway ID
        API_ID=$(jq -r ".\"cost-analytics-api-$ENVIRONMENT\".APIGatewayId // empty" outputs-api-$ENVIRONMENT.json 2>/dev/null || echo "")
        if [ -n "$API_ID" ]; then
            echo "API Gateway ID: $API_ID"
        fi
        
        echo ""
        echo "Health Check:"
        echo "============="
        if [ -n "$API_URL" ]; then
            echo "Test with: curl $API_URL/health"
        fi
        
        echo ""
        echo "Documentation:"
        echo "=============="
        echo "API Specification: docs/api-specification.yaml"
        echo "Implementation Guide: docs/API_IMPLEMENTATION.md"
        
    else
        print_warning "No API outputs file found"
    fi
}

# Function to run post-deployment tests
run_tests() {
    print_status "Running post-deployment tests..."
    
    if [ -f "outputs-api-$ENVIRONMENT.json" ]; then
        API_URL=$(jq -r ".\"cost-analytics-api-$ENVIRONMENT\".APIGatewayStageURL // empty" outputs-api-$ENVIRONMENT.json 2>/dev/null || echo "")
        
        if [ -n "$API_URL" ]; then
            # Test health endpoint
            print_status "Testing health endpoint..."
            if curl -s -f "$API_URL/health" > /dev/null; then
                print_success "Health endpoint test passed"
            else
                print_warning "Health endpoint test failed"
            fi
        fi
    fi
}

# Function to clean up on error
cleanup_on_error() {
    print_error "Deployment failed. Cleaning up..."
    
    # Optionally destroy stacks on failure (uncomment if desired)
    # cdk destroy cost-analytics-api-$ENVIRONMENT --profile $PROFILE --force
    # cdk destroy lambda-cost-reporting-$ENVIRONMENT --profile $PROFILE --force
    
    exit 1
}

# Main deployment function
main() {
    echo "=========================================="
    echo "Multi-Cloud Cost Analytics API Deployment"
    echo "=========================================="
    echo "Environment: $ENVIRONMENT"
    echo "AWS Account: $ACCOUNT"
    echo "AWS Region: $REGION"
    echo "AWS Profile: $PROFILE"
    echo "=========================================="
    echo ""
    
    # Set up error handling
    trap cleanup_on_error ERR
    
    # Run deployment steps
    check_prerequisites
    validate_environment
    install_dependencies
    bootstrap_cdk
    synthesize_templates
    deploy_stacks
    display_outputs
    run_tests
    
    print_success "Deployment completed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Test the API endpoints using the provided URLs"
    echo "2. Configure your application to use the API"
    echo "3. Set up monitoring and alerting"
    echo "4. Review security settings for production use"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --profile)
            PROFILE="$2"
            shift 2
            ;;
        --region)
            REGION="$2"
            export AWS_DEFAULT_REGION="$2"
            shift 2
            ;;
        --account)
            ACCOUNT="$2"
            export CDK_DEFAULT_ACCOUNT="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [environment] [options]"
            echo ""
            echo "Arguments:"
            echo "  environment    Target environment (dev, staging, prod) [default: dev]"
            echo ""
            echo "Options:"
            echo "  --profile      AWS profile to use [default: default]"
            echo "  --region       AWS region [default: us-east-1]"
            echo "  --account      AWS account ID [default: auto-detect]"
            echo "  --help, -h     Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  AWS_PROFILE           AWS profile to use"
            echo "  AWS_DEFAULT_REGION    AWS region"
            echo "  CDK_DEFAULT_ACCOUNT   AWS account ID"
            echo "  JWT_SECRET           JWT secret for authentication"
            echo ""
            echo "Examples:"
            echo "  $0 dev"
            echo "  $0 prod --profile production --region us-west-2"
            exit 0
            ;;
        *)
            if [ -z "$ENVIRONMENT" ] || [ "$ENVIRONMENT" = "dev" ]; then
                ENVIRONMENT="$1"
            else
                print_error "Unknown option: $1"
                exit 1
            fi
            shift
            ;;
    esac
done

# Run main function
main