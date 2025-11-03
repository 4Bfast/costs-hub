#!/usr/bin/env python3
"""
AWS CDK app for Multi-Cloud AI Cost Analytics System
"""

import os
from aws_cdk import App, Environment
from stacks.multi_cloud_stack import MultiCloudAnalyticsStack
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

# Deploy multi-cloud analytics stack
stack_name = f"multi-cloud-analytics-{env_name}"
multi_cloud_stack = MultiCloudAnalyticsStack(
    app, 
    stack_name,
    env=env,
    env_config=env_config,
    description=f"Multi-Cloud AI Cost Analytics System - {env_name.upper()} environment"
)

app.synth()