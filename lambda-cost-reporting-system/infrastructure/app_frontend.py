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
