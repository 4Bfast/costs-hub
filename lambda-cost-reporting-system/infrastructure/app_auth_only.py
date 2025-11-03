#!/usr/bin/env python3

import aws_cdk as cdk
from stacks.auth_stack import AuthStack

app = cdk.App()

# Authentication Stack
auth_stack = AuthStack(
    app, "costhub-auth-prod",
    env=cdk.Environment(account="008195334540", region="us-east-1")
)

app.synth()
