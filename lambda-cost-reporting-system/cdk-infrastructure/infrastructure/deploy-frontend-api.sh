#!/bin/bash

# Deploy Frontend API Stack
# This script deploys only the Frontend API Gateway Layer

set -e

echo "🚀 Deploying CostsHub Frontend API..."

# Set environment variables
export CDK_DEFAULT_ACCOUNT=$(aws sts get-caller-identity --profile 4bfast --query Account --output text)
export CDK_DEFAULT_REGION="us-east-1"
export ENVIRONMENT="dev"

echo "📋 Account: $CDK_DEFAULT_ACCOUNT"
echo "📋 Region: $CDK_DEFAULT_REGION"
echo "📋 Environment: $ENVIRONMENT"

# Create a minimal app just for frontend API
cat > app_frontend.py << 'EOF'
#!/usr/bin/env python3
import os
from aws_cdk import App, Environment
from stacks.frontend_api_stack import FrontendAPIStack

app = App()

account = os.environ.get('CDK_DEFAULT_ACCOUNT')
region = os.environ.get('CDK_DEFAULT_REGION', 'us-east-1')
env_name = os.environ.get('ENVIRONMENT', 'dev')

env = Environment(account=account, region=region)

frontend_api_stack = FrontendAPIStack(
    app,
    f"costshub-frontend-api-{env_name}",
    env=env,
    description=f"CostsHub Frontend API Gateway - {env_name.upper()} environment"
)

app.synth()
EOF

# Deploy the stack
echo "🔨 Synthesizing CDK app..."
cdk synth --app "python3 app_frontend.py" --profile 4bfast

echo "🚀 Deploying Frontend API stack..."
cdk deploy costshub-frontend-api-dev \
    --app "python3 app_frontend.py" \
    --profile 4bfast \
    --require-approval never \
    --outputs-file frontend-api-outputs.json

echo "✅ Frontend API deployed successfully!"

# Show outputs
if [ -f "frontend-api-outputs.json" ]; then
    echo "📋 Stack Outputs:"
    cat frontend-api-outputs.json | jq '.'
fi

# Cleanup
rm -f app_frontend.py

echo "🎉 Deployment complete!"
