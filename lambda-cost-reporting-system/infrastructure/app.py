#!/usr/bin/env python3
"""
AWS CDK app for Lambda Cost Reporting System
"""

import os
from aws_cdk import App, Environment
from stacks.cost_reporting_stack import CostReportingStack
from stacks.api_gateway_stack import APIGatewayStack
from stacks.frontend_api_stack import FrontendAPIStack
from config.environments import get_environment_config

app = App()

# Get environment configuration
account = os.environ.get('CDK_DEFAULT_ACCOUNT')
region = os.environ.get('CDK_DEFAULT_REGION', 'us-east-1')
env_name = os.environ.get('ENVIRONMENT', 'dev')

# Get environment-specific configuration
env_config = get_environment_config(env_name)
env_config.account = account
env_config.region = region

# Create environment
env = Environment(account=account, region=region)

# Deploy main cost reporting stack
main_stack_name = f"lambda-cost-reporting-{env_name}"
main_stack = CostReportingStack(
    app, 
    main_stack_name,
    env=env,
    env_config=env_config,
    description=f"Lambda Cost Reporting System - {env_name.upper()} environment"
)

# Deploy API Gateway stack
api_stack_name = f"cost-analytics-api-{env_name}"
api_stack = APIGatewayStack(
    app,
    api_stack_name,
    env=env,
    env_config=env_config,
    lambda_function=main_stack.lambda_function,
    description=f"Multi-Cloud Cost Analytics API - {env_name.upper()} environment"
)

# Add dependency
api_stack.add_dependency(main_stack)

# Deploy Frontend API stack
frontend_api_stack_name = f"costshub-frontend-api-{env_name}"
frontend_api_stack = FrontendAPIStack(
    app,
    frontend_api_stack_name,
    env=env,
    description=f"CostsHub Frontend API Gateway - {env_name.upper()} environment"
)

app.synth()