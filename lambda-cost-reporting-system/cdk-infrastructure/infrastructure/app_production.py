#!/usr/bin/env python3

import aws_cdk as cdk
from stacks.auth_stack import AuthStack
from stacks.frontend_api_stack import FrontendAPIStack
from stacks.frontend_stack import FrontendStack
from config.production import config

app = cdk.App()

# Authentication Stack
auth_stack = AuthStack(
    app, "costhub-auth-prod",
    env=cdk.Environment(account=config.AWS_ACCOUNT_ID, region=config.AWS_REGION)
)

# Frontend API Stack with Centralized Config
frontend_api_stack = FrontendAPIStack(
    app, "costhub-frontend-api-prod",
    env=cdk.Environment(account=config.AWS_ACCOUNT_ID, region=config.AWS_REGION)
)

# Frontend Stack (S3 + CloudFront)
frontend_stack = FrontendStack(
    app, "costhub-frontend-prod",
    env=cdk.Environment(account=config.AWS_ACCOUNT_ID, region=config.AWS_REGION)
)

app.synth()
